#!/usr/bin/env python3
"""Judge an animation without watching it (BD-641, docs/163): a contact sheet of key frames plus numeric checks in plain words.

    python tools/animation_strip.py assets/blender/fusion/walk.blend --out build/anim --count 8
    python tools/animation_strip.py creature.fbx --action walk
    python tools/animation_strip.py clip.mp4            # or .gif, or a folder of numbered images (use --fps for those)

Input kinds
  .blend / .fbx / .obj / .glb  Blender runs in a SEPARATE headless process (tools/blender_animation_probe.py, never the live MCP
                               session). All checks below are available, the sheet is rendered from the side (Workbench).
  video / GIF / image folder   ffmpeg (C:/ffmpeg/bin) cuts the frames. Only the checks that pixels can answer are run
                               (loop seam, pops, held frames, frame rate, duration); the others print "n/a".
Output: <out>/<name>_strip.png, <out>/<name>_report.txt, and the same report on screen. Exit code 0; with --strict, 1 if any check is
"check". The verdict limits live in ONE table, THRESHOLDS below, each with its reason. They are judgement calls, not laws: a "check"
means "look at this", not "this is wrong". Nothing here can judge feel, weight or appeal; the owner still looks at the picture.
"""
import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_headless  # noqa: E402

def _find_tool(name, env):
    """$FFMPEG / $FFPROBE, then C:/ffmpeg/bin (the owner PC), then PATH. Falls back to the C: path so the error message names it."""
    import shutil
    for cand in (os.environ.get(env), 'C:/ffmpeg/bin/%s.exe' % name):
        if cand and Path(cand).exists():
            return cand
    return shutil.which(name) or 'C:/ffmpeg/bin/%s.exe' % name


FFMPEG = _find_tool('ffmpeg', 'FFMPEG')
FFPROBE = _find_tool('ffprobe', 'FFPROBE')
PROBE = Path(__file__).resolve().parent / 'blender_animation_probe.py'

# ONE table of limits: name -> (value, plain reason). Heights are measured in body heights (the standing model height) so that a
# tiny Compy and a big Brachiosaurus are judged alike.
THRESHOLDS = {
    'seam_dup_below': (0.1, 'the last-to-first step is under a tenth of what the frames either side of the seam would give: the last frame repeats the first, so a loop plays one pose twice (a small hitch)'),
    'seam_pop_above': (2.0, 'the last-to-first step is more than twice what the frames either side of the seam would give: the eye sees a jump at the loop point'),
    'angle_range_max': (170.0, 'a joint turns more than 170 degrees from its rest pose: probably flipped or wound the wrong way round'),
    'angle_speed_max': (1200.0, 'a joint turns faster than 1200 degrees per second (50 degrees per frame at 24 fps): reads as a one-frame pop'),
    'spike_ratio': (8.0, 'one frame accelerates 8 times more than the bone does on average: a sudden jerk, not a smooth curve (linear keys every 6 frames give about 6)'),
    'spike_floor': (0.02, 'ignore jerks smaller than 2 percent of body height per frame squared: too small to see'),
    'stance_height': (0.03, 'a foot counts as planted while it is within 3 percent of body height of the lowest foot point (the first and last such frame are ignored: the foot is still arriving or leaving)'),
    'slide_ratio_max': (0.15, 'planted foot moves in the world at more than 15 percent of the body speed: visible skating'),
    'slide_cv_max': (0.25, 'in-place cycle: planted foot speed varies by more than 25 percent over the stance (it should be one steady backward speed)'),
    'walk_planted_min': (0.25, 'a foot planted less than a quarter of the clip means jump, flight or swim: the walk rules (sliding, left/right timing) are skipped'),
    'walk_move_min': (0.03, 'feet that move less than 3 percent of body height all clip long are a standing pose: the walk rules are skipped'),
    'inplace_speed': (0.05, 'body slower than 0.05 body heights per second counts as an in-place cycle (no root motion)'),
    'penetration_max': (0.02, 'lowest point sinks more than 2 percent of body height below the standing ground: feet dip into the floor'),
    'float_max': (0.03, 'lowest point stays more than 3 percent of body height above the ground in every frame (ignore for flyers and swimmers)'),
    'phase_tol': (0.07, 'left and right feet should be in step (0) or half a cycle apart (0.5); more than 0.07 of a cycle off (or 1.5 frames) is uneven'),
    'amp_ratio': ((0.85, 1.15), 'left and right bone tips should travel about the same distance (within 15 percent)'),
    'amp_floor': (0.02, 'bones whose tip travels less than 2 percent of body height are left out of the left/right size check'),
    'duty_diff_max': (0.10, 'left and right feet should be on the ground for the same share of the cycle (within 10 points)'),
    'ease_linear_max': (1.15, 'peak speed over average speed under 1.15 inside a move means even speed: mechanical, robotic'),
    'ease_snappy_min': (2.2, 'peak over average speed above 2.2 means a slow hold then a sudden fast move: snappy'),
    'fps_ok': ((24, 25, 30, 48, 50, 60), 'common frame rates; others get resampled on export'),
    'duration_range': ((0.2, 5.0), 'seconds: shorter than 0.2 is a blink, longer than 5 is probably the wrong range selected'),
    'video_spike_ratio': (5.0, 'video: one frame changes more than 5 times the typical change: a pop or a cut'),
    'video_hold_ratio': (0.1, 'video: a frame that changes less than a tenth of the typical change in the middle of motion is a held (duplicate) frame'),
}
FOOT_RE = re.compile(r'(foot|toe|paw|ankle|heel|claw|hoof)', re.I)


# ----------------------------------------------------------------------------------------------------------------------------------
# helpers
def tokens_side(name):
    """'L' or 'R' when the bone name says left or right (foot.L, foot_r, LeftFoot, footL), else None."""
    parts = re.split(r'[._\-\s]+', name)
    for p in parts:
        if p.lower() in ('l', 'left'):
            return 'L'
        if p.lower() in ('r', 'right'):
            return 'R'
    m = re.search(r'[a-z]([LR])$', name)
    if m:
        return m.group(1)
    m = re.match(r'(Left|Right)[A-Z]', name)
    if m:
        return 'L' if m.group(1) == 'Left' else 'R'
    return None


def mirror_name(name):
    swap = {'l': 'r', 'r': 'l', 'left': 'right', 'right': 'left'}
    parts = re.split(r'([._\-\s]+)', name)
    out, changed = [], False
    for p in parts:
        if p.lower() in swap and not changed:
            q = swap[p.lower()]
            out.append(q.upper() if p.isupper() else (q.capitalize() if p[0].isupper() else q))
            changed = True
        else:
            out.append(p)
    if changed:
        return ''.join(out)
    m = re.search(r'([a-z])([LR])$', name)
    if m:
        return name[:-1] + ('R' if m.group(2) == 'L' else 'L')
    m = re.match(r'(Left|Right)([A-Z].*)', name)
    if m:
        return ('Right' if m.group(1) == 'Left' else 'Left') + m.group(2)
    return None


def euler_to_quat(rot_deg):
    """Euler XYZ degrees [N,3] -> quaternions [N,4] (w, x, y, z)."""
    r = np.radians(np.asarray(rot_deg, dtype=float)) / 2
    cx, cy, cz = np.cos(r[:, 0]), np.cos(r[:, 1]), np.cos(r[:, 2])
    sx, sy, sz = np.sin(r[:, 0]), np.sin(r[:, 1]), np.sin(r[:, 2])
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz
    return np.stack([w, x, y, z], axis=1)


def quat_angle_deg(q):
    return np.degrees(2 * np.arccos(np.clip(np.abs(q[..., 0]), 0, 1)))


def quat_between_deg(q1, q2):
    dot = np.abs(np.sum(q1 * q2, axis=-1))
    return np.degrees(2 * np.arccos(np.clip(dot, 0, 1)))


def segment_ratios(series):
    """Speed shape of every move between two turning points: peak speed / average speed. Linear 1.0, sine 1.57, smoothstep 1.5."""
    s = np.asarray(series, dtype=float)
    n = len(s)
    s3 = np.concatenate([s, s, s])
    d = np.diff(s3)
    span = float(np.ptp(s)) or 1.0
    sign = np.sign(np.where(np.abs(d) < 1e-6 * span, 0, d))
    last = 0
    for i in range(len(sign)):
        if sign[i] == 0:
            sign[i] = last
        else:
            last = sign[i]
    turns = [i + 1 for i in range(len(sign) - 1) if sign[i] != 0 and sign[i + 1] != 0 and sign[i] != sign[i + 1]]
    out = []
    for a, b in zip(turns[:-1], turns[1:]):
        if a < n or a >= 2 * n or b - a < 2:
            continue
        delta = abs(s3[b] - s3[a])
        if delta < 0.05 * span:
            continue
        mean_speed = delta / (b - a)
        out.append((float(np.max(np.abs(d[a:b])) / mean_speed), float(delta)))
    return out


def weighted_median(pairs):
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= total / 2:
            return v
    return pairs[-1][0]


class Row:
    """One line of the verdict table: result is ok / check / n/a."""

    def __init__(self, name, result, measured, limit):
        self.name, self.result, self.measured, self.limit = name, result, measured, limit


# ----------------------------------------------------------------------------------------------------------------------------------
# analysis of the Blender probe data
def analyse_probe(d, one_shot=False):
    """Return (rows, tables, notes) for a probe dictionary. tables is a list of (title, header, rows of strings)."""
    rows, tables, notes = [], [], []
    frames = d['frames']
    n = len(frames)
    fps = float(d['fps'])
    keys = d.get('keys', {})
    bones = d['bones']
    objects = d['objects']
    if not bones and not objects:
        paths = keys.get('data_paths') or []
        what = ('the action "%s" has %d curve(s) but none move a bone or an object (they change: %s), so there is no motion to measure here'
                % (d.get('action'), keys.get('curve_count', 0), ', '.join(paths[:3]))) if keys.get('curve_count') else 'no armature, no animated object and no keyframes in the file'
        rows.append(Row('animation found', 'check', what, 'bone or object motion to judge'))
        return rows, tables, notes
    if d.get('action') is None:
        notes.append('The file has %d bone(s) but no action (no keyframes): it is a rig with a static pose, so there is no motion to judge. '
                     'The picture shows that one pose.' % len(bones))
        rows.append(Row('animation found', 'check', 'no action in the file (%s)' % ('armature ' + ', '.join(d['armatures']) if d.get('armatures') else 'no armature'),
                        'export the clip together with the rig'))
        return rows, tables, notes
    names = list(bones.keys())
    pseudo = False
    if bones:
        head = np.array([bones[k]['head'] for k in names], dtype=float)
        tail = np.array([bones[k]['tail'] for k in names], dtype=float)
        quat = np.array([bones[k]['quat'] for k in names], dtype=float)
    else:
        pseudo = True
        names = list(objects.keys())
        head = np.array([objects[k]['loc'] for k in names], dtype=float)
        tail = head.copy()
        quat = np.array([euler_to_quat(objects[k]['rot']) for k in names])
    nb = len(names)
    parents = {k: bones[k]['parent'] for k in bones} if bones else {}
    children = set(p for p in parents.values() if p)

    # model height and ground: from the standing (rest) pose
    ground, height, source = None, None, ''
    rb = d.get('rest_box') or (d['mesh_box'][0] if d.get('mesh_box') else None)
    if rb:
        ground, height, source = rb[2], rb[5] - rb[2], 'standing mesh box'
    elif d.get('rest_bones'):
        zs = [p[2] for v in d['rest_bones'].values() for p in (v['head'], v['tail'])]
        ground, height, source = min(zs), max(zs) - min(zs), 'standing bone positions'
    else:
        zs = np.concatenate([head[:, 0, 2], tail[:, 0, 2]])
        ground, height, source = float(zs.min()), float(zs.max() - zs.min()), 'first-frame positions'
    if not height or height < 1e-6:
        height = max(float(np.ptp(np.concatenate([head, tail]))), 1e-6)
        source = 'overall extent'
    H = float(height)
    notes.append('Body height %.3f units (from the %s); ground at z = %.3f.' % (H, source, ground))

    pts = np.concatenate([head, tail], axis=0)                       # [2B, N, 3]
    cxy = pts[:, :, :2].mean(axis=0)                                 # body centre on the floor plane, per frame
    rel = pts.copy()
    rel[:, :, :2] -= cxy[None]
    if n < 3:
        rows.append(Row('enough frames', 'check', '%d frames' % n, 'need at least 3'))
        return rows, tables, notes
    step = np.sqrt(np.mean(np.sum((rel[:, 1:] - rel[:, :-1]) ** 2, axis=-1), axis=0)) / H      # [N-1]
    med = float(np.median(step))
    seam = float(np.sqrt(np.mean(np.sum((rel[:, 0] - rel[:, -1]) ** 2, axis=-1)))) / H
    moves = med > 1e-6
    notes.append('Typical frame-to-frame pose change %.4f body heights.' % med)

    # --- frame rate and duration
    expected = (float(step[-2]) + float(step[0])) / 2 if len(step) >= 3 else med      # what the seam step would be if the loop were seamless
    ratio = seam / max(expected, 1e-9)
    dup = moves and ratio < THRESHOLDS['seam_dup_below'][0]
    cycle_frames = (n - 1) if dup else n
    seconds = cycle_frames / fps
    lo, hi = THRESHOLDS['duration_range'][0]
    rows.append(Row('frame rate', 'ok' if round(fps) in THRESHOLDS['fps_ok'][0] and abs(fps - round(fps)) < 0.01 else 'check',
                    '%.2f frames per second' % fps, THRESHOLDS['fps_ok'][1]))
    rows.append(Row('duration', 'ok' if lo <= seconds <= hi else 'check',
                    '%d frames = %.2f s per loop (frames %d to %d)' % (cycle_frames, seconds, frames[0], frames[-1]), THRESHOLDS['duration_range'][1]))
    if not moves:
        rows.append(Row('anything moves', 'check', 'the pose never changes', 'an animation needs movement'))
        return rows, tables, notes

    # --- loop continuity
    worst_bone, worst_deg = None, 0.0
    qd = quat_between_deg(quat[:, -1], quat[:, 0])
    qstep = quat_between_deg(quat[:, 1:], quat[:, :-1])
    for i in range(nb):
        typical = float(np.median(qstep[i]))
        pop = float(qd[i]) - typical
        if float(qd[i]) > 5 and float(qd[i]) > 3 * max(typical, 1.0) and pop > worst_deg:
            worst_bone, worst_deg = names[i], float(qd[i])
    if one_shot:
        res, why = 'n/a', 'one-shot clip (--one-shot): it does not loop, so the seam is not judged (seam step %.2fx its neighbours)' % ratio
    elif dup:
        res, why = 'check', 'last frame repeats the first (seam step is %.2fx what its neighbours give): looping plays that pose twice' % ratio
    elif ratio > THRESHOLDS['seam_pop_above'][0] or worst_bone:
        extra = ('; %s turns %.0f degrees at the seam' % (worst_bone, worst_deg)) if worst_bone else ''
        res, why = 'check', 'POP at the loop point: the last-to-first step is %.1fx what its neighbours give%s' % (ratio, extra)
    else:
        res, why = 'ok', 'the last-to-first step is %.2fx what the frames either side give (1.0 = seamless)' % ratio
    rows.append(Row('loop continuity', res, why, 'seam step between %.0f%% and %.0fx of its neighbours, no joint jumping' % (
        100 * THRESHOLDS['seam_dup_below'][0], THRESHOLDS['seam_pop_above'][0])))

    # --- per-bone angle range and speed
    ang = quat_angle_deg(quat)                                      # [B, N] degrees away from the rest pose
    rng = ang.max(axis=1) - ang.min(axis=1)
    qs = quat_between_deg(quat[:, 1:], quat[:, :-1]) * fps          # degrees per second [B, N-1]
    peak, mean_sp = qs.max(axis=1), qs.mean(axis=1)
    order = np.argsort(-rng)
    trows = []
    for i in order[:12]:
        if rng[i] < 0.5 and i != order[0]:
            continue
        trows.append([names[i], '%.0f' % ang[i].min(), '%.0f' % ang[i].max(), '%.0f' % rng[i], '%.0f' % peak[i], '%.0f' % mean_sp[i]])
    tables.append(('Joint angles (degrees away from the rest pose; speed in degrees per second), biggest movers first',
                   ['bone', 'min', 'max', 'range', 'peak speed', 'average speed'], trows))
    over_range = [names[i] for i in range(nb) if ang[i].max() > THRESHOLDS['angle_range_max'][0]]
    over_speed = [(names[i], peak[i]) for i in range(nb) if peak[i] > THRESHOLDS['angle_speed_max'][0]]
    rows.append(Row('joint angle range', 'check' if over_range else 'ok',
                    ('over 170 degrees: ' + ', '.join(over_range[:4])) if over_range else 'biggest turn %.0f degrees (%s)' % (ang.max(), names[int(np.argmax(ang.max(axis=1)))]),
                    'under %.0f degrees' % THRESHOLDS['angle_range_max'][0]))
    rows.append(Row('joint speed', 'check' if over_speed else 'ok',
                    ('too fast: ' + ', '.join('%s %.0f/s' % x for x in over_speed[:3])) if over_speed else 'fastest %.0f degrees per second (%s)' % (peak.max(), names[int(np.argmax(peak))]),
                    'under %.0f degrees per second' % THRESHOLDS['angle_speed_max'][0]))

    # --- jerkiness (acceleration spikes) on the bone tips, body centre removed
    spikes = []
    if n >= 4:
        tip = rel[nb:]                                              # tails relative to the body centre [B, N, 3]
        acc = np.linalg.norm(tip[:, 2:] - 2 * tip[:, 1:-1] + tip[:, :-2], axis=-1) / H     # [B, N-2]
        for i in range(nb):
            mx = float(acc[i].max())
            sc = mx / (float(acc[i].mean()) + 1e-9)
            if sc > THRESHOLDS['spike_ratio'][0] and mx > THRESHOLDS['spike_floor'][0]:
                spikes.append((names[i], frames[int(np.argmax(acc[i])) + 1], sc, mx))
    spikes.sort(key=lambda x: -x[3])
    rows.append(Row('jerkiness', 'check' if spikes else 'ok',
                    ('%d bone(s) jerk, worst %s at frame %d (%.0fx its average, %.0f%% of body height per frame squared)' % (
                        len(spikes), spikes[0][0], spikes[0][1], spikes[0][2], 100 * spikes[0][3])) if spikes else 'no sudden acceleration spikes',
                    'spike over %.0fx average and over %.0f%% of body height' % (THRESHOLDS['spike_ratio'][0], 100 * THRESHOLDS['spike_floor'][0])))

    # --- feet
    if bones:
        feet = [k for k in names if FOOT_RE.search(k)]
        guessed = False
        if not feet:
            leaves = [k for k in names if k not in children]
            tz = {k: float(tail[names.index(k)].min()) for k in leaves}
            if tz:
                low = min(tz.values())
                feet = [k for k in leaves if tz[k] - low < 0.15 * H]
                guessed = True
    else:
        feet, guessed = [], False
    contact, stance, foot_rows = {}, {}, []
    feet_valid, walk_like = True, True
    if feet:
        for k in feet:
            i = names.index(k)
            use_head = head[i, :, 2] < tail[i, :, 2]
            contact[k] = np.where(use_head[:, None], head[i], tail[i])
        gfoot = min(float(contact[k][:, 2].min()) for k in feet)
        tol = THRESHOLDS['stance_height'][0] * H
        for k in feet:
            stance[k] = contact[k][:, 2] - gfoot <= tol
        planted_min = min(float(stance[k].mean()) for k in feet)
        foot_move = max(float(np.ptp(contact[k], axis=0).max()) for k in feet) / H
        if planted_min < THRESHOLDS['walk_planted_min'][0] or foot_move < THRESHOLDS['walk_move_min'][0]:
            walk_like = False
            if foot_move < THRESHOLDS['walk_move_min'][0]:
                why = 'the feet hardly move (%.1f%% of body height): a standing clip' % (100 * foot_move)
            else:
                why = 'a foot is planted only %.0f%% of the clip: it jumps, flies or swims rather than walks' % (100 * planted_min)
            rows.append(Row('foot sliding', 'n/a', why, 'walk and run cycles only'))
            tables.append(('Feet (bones named like a foot): share of the cycle planted, lowest point above ground',
                           ['foot', 'planted', 'lowest'], [[k, '%.0f%%' % (100 * stance[k].mean()), '%.1f%%' % (100 * (contact[k][:, 2].min() - ground) / H)] for k in feet]))
            feet_valid = False
    if feet and feet_valid:
        disp = cxy[-1] - cxy[0]
        body_speed = float(np.linalg.norm(disp)) / ((n - 1) / fps)
        inplace = body_speed < THRESHOLDS['inplace_speed'][0] * H
        speeds_all, per = [], {}
        for k in feet:
            c = contact[k][:, :2]
            v = np.linalg.norm(c[1:] - c[:-1], axis=-1) * fps
            core = stance[k] & np.roll(stance[k], 1) & np.roll(stance[k], -1)     # drop the arriving and leaving frame
            if core.sum() < 2:
                core = stance[k]
            both = core[1:] & core[:-1]
            per[k] = v[both]
            speeds_all.extend(list(v[both]))
        if not speeds_all:
            rows.append(Row('foot sliding', 'check', 'no frame found where a foot is planted' + (' (feet guessed from the bone shape)' if guessed else ''),
                            'a walk needs planted feet'))
        else:
            if inplace:
                mean_v = float(np.mean(speeds_all))
                cv = float(np.std(speeds_all) / mean_v) if mean_v > 1e-9 else 0.0
                res = 'ok' if cv <= THRESHOLDS['slide_cv_max'][0] else 'check'
                rows.append(Row('foot sliding', res, 'in place: planted feet move backwards at %.2f units/s on average, varying by %.0f%%' % (mean_v, 100 * cv),
                                'speed varies under %.0f%%' % (100 * THRESHOLDS['slide_cv_max'][0])))
                implied = mean_v
            else:
                mean_v = float(np.median(speeds_all))
                r = mean_v / body_speed
                res = 'ok' if r <= THRESHOLDS['slide_ratio_max'][0] else 'check'
                rows.append(Row('foot sliding', res, 'planted feet move at %.0f%% of the body speed (body %.2f units/s, typical planted foot %.2f)' % (100 * r, body_speed, mean_v),
                                'under %.0f%% of body speed' % (100 * THRESHOLDS['slide_ratio_max'][0])))
                implied = body_speed
            notes.append('This cycle matches a travel speed of about %.2f units per second (%.2f body heights per second); 1 unit = 1 stud for the creature exports.'
                         % (implied, implied / H))
        for k in feet:
            sp = per[k]
            foot_rows.append([k, '%.0f%%' % (100 * stance[k].mean()),
                              ('%.2f' % sp.mean()) if len(sp) else '-', '%.1f%%' % (100 * (contact[k][:, 2].min() - ground) / H)])
        tables.append(('Feet (%s): share of the cycle planted, speed while planted (units/s), lowest point above ground' % ('guessed from bone shape' if guessed else 'bones named like a foot'),
                       ['foot', 'planted', 'planted speed', 'lowest'], foot_rows))
    elif not feet:
        rows.append(Row('foot sliding', 'n/a', 'no foot bones found', 'only meaningful for walk cycles'))

    # --- ground
    if d.get('mesh_box'):
        lows = np.array([b[2] for b in d['mesh_box'] if b])
        src = 'mesh'
    else:
        lows = pts[:, :, 2].min(axis=0)
        src = 'bone'
    pen = (ground - float(lows.min())) / H
    above = (float(lows.min()) - ground) / H
    rows.append(Row('ground penetration', 'check' if pen > THRESHOLDS['penetration_max'][0] else 'ok',
                    ('lowest %s point sinks %.1f%% of body height below the ground (frame %d)' % (src, 100 * pen, frames[int(np.argmin(lows))]))
                    if pen > 0.0005 else 'nothing goes below the ground (lowest %s point %.1f%% above it)' % (src, 100 * max(above, 0)),
                    'under %.0f%% of body height' % (100 * THRESHOLDS['penetration_max'][0])))
    rows.append(Row('floating', 'check' if above > THRESHOLDS['float_max'][0] else 'ok',
                    'the lowest point is %.1f%% of body height above the ground at its closest' % (100 * max(above, 0)),
                    'under %.0f%% (flyers and swimmers can ignore this)' % (100 * THRESHOLDS['float_max'][0])))

    # --- left/right symmetry
    pair_rows, phase_bad, amp_bad, duty_bad = [], [], [], []
    seen = set()
    for k in names:
        m = mirror_name(k)
        if not m or m not in names or (m, k) in seen or tokens_side(k) != 'L':
            continue
        seen.add((k, m))
        i, j = names.index(k), names.index(m)
        # size of the swing = how far the bone tip travels (body centre removed); this does not depend on how the rest pose was oriented
        a, b = float(np.linalg.norm(np.ptp(rel[nb + i], axis=0))) / H, float(np.linalg.norm(np.ptp(rel[nb + j], axis=0))) / H
        small = THRESHOLDS['amp_floor'][0]
        amp = (a / b) if b > small else (1.0 if a < small else 99.0)
        if a >= small or b >= small:
            if not (THRESHOLDS['amp_ratio'][0][0] <= amp <= THRESHOLDS['amp_ratio'][0][1]):
                amp_bad.append('%s/%s %.2f' % (k, m, amp))
        pair_rows.append([k + ' / ' + m, '%.0f%% / %.0f%%' % (100 * a, 100 * b), '%.2f' % amp])
    foot_pairs = []
    for k in (feet if feet_valid else []):
        m = mirror_name(k)
        if tokens_side(k) == 'L' and m in contact:
            foot_pairs.append((k, m))
    tolp = max(THRESHOLDS['phase_tol'][0], 1.5 / max(cycle_frames, 1))
    for k, m in foot_pairs:
        za, zb = contact[k][:cycle_frames, 2], contact[m][:cycle_frames, 2]
        if np.ptp(za) < 1e-6 or np.ptp(zb) < 1e-6:
            continue
        fa, fb = np.fft.rfft(za - za.mean()), np.fft.rfft(zb - zb.mean())
        corr = np.fft.irfft(np.conj(fa) * fb, n=len(za))
        lag = int(np.argmax(corr))
        ph = lag / len(za)
        off = min(abs(ph), abs(ph - 0.5), abs(ph - 1.0))
        duty = abs(float(stance[k].mean()) - float(stance[m].mean()))
        if off > tolp:
            phase_bad.append('%s/%s %.2f of a cycle apart' % (k, m, ph))
        if duty > THRESHOLDS['duty_diff_max'][0]:
            duty_bad.append('%s/%s planted %.0f%% vs %.0f%%' % (k, m, 100 * stance[k].mean(), 100 * stance[m].mean()))
        pair_rows.append([k + ' / ' + m + ' (timing)', 'offset %.2f cycle' % ph, 'planted %.0f%% / %.0f%%' % (100 * stance[k].mean(), 100 * stance[m].mean())])
    if pair_rows:
        tables.append(('Left / right pairs (how far the bone tip travels, as a share of body height; foot timing offset as a share of the cycle)', ['pair', 'left / right', 'ratio'], pair_rows))
    if foot_pairs:
        bad = phase_bad + duty_bad
        rows.append(Row('left/right foot timing', 'check' if bad else 'ok',
                        '; '.join(bad) if bad else 'feet are in step or exactly half a cycle apart, planted for the same share',
                        'offset within %.2f of 0 or 0.5, planted shares within %.0f points' % (tolp, 100 * THRESHOLDS['duty_diff_max'][0])))
    else:
        rows.append(Row('left/right foot timing', 'n/a', 'not a walk or run cycle' if not feet_valid else 'no left/right foot pair found',
                        'walk and run cycles only' if not feet_valid else 'name bones like foot.L / foot.R'))
    if pair_rows:
        rows.append(Row('left/right swing size', 'check' if amp_bad else 'ok', ('uneven: ' + '; '.join(amp_bad[:3])) if amp_bad else 'paired bones swing within 15% of each other',
                        'ratio %.2f to %.2f' % THRESHOLDS['amp_ratio'][0]))

    # --- easing
    pairs = []
    for i in range(nb):
        s = rel[nb + i]
        if np.ptp(s, axis=0).max() < 0.01 * H:
            continue
        c = s - s.mean(axis=0)
        _, _, vt = np.linalg.svd(c, full_matrices=False)
        pairs.extend(segment_ratios(c @ vt[0]))
    inter = keys.get('interpolation', {})
    total = sum(inter.values()) or 0
    inter_txt = ', '.join('%s %.0f%%' % (k.lower(), 100 * v / total) for k, v in sorted(inter.items(), key=lambda x: -x[1])) if total else 'no keyframes in the file'
    if pairs:
        e = weighted_median(pairs)
        if e < THRESHOLDS['ease_linear_max'][0]:
            word = 'linear (even speed, mechanical)'
            res = 'check'
        elif e > THRESHOLDS['ease_snappy_min'][0]:
            word = 'very snappy (slow then sudden)'
            res = 'check'
        else:
            word = 'eased (starts and stops softly)'
            res = 'ok'
        rows.append(Row('easing', res, '%s: peak speed is %.2fx the average inside a move; key interpolation: %s' % (word, e, inter_txt),
                        'between %.2f and %.1f (linear is 1.0, a sine is 1.57)' % (THRESHOLDS['ease_linear_max'][0], THRESHOLDS['ease_snappy_min'][0])))
    else:
        rows.append(Row('easing', 'n/a', 'no full back-and-forth move found to measure; key interpolation: ' + inter_txt, 'needs at least one full move'))
    if 'CONSTANT' in inter:
        rows.append(Row('stepped keys', 'check', '%d key(s) use constant (stepped) interpolation' % inter['CONSTANT'], 'final animation should be smooth'))
    return rows, tables, notes


# ----------------------------------------------------------------------------------------------------------------------------------
# contact sheets
def _font(size):
    for name in ('arial.ttf', 'DejaVuSans.ttf', 'segoeui.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def label(img, text):
    dr = ImageDraw.Draw(img)
    f = _font(max(12, img.width // 14))
    box = dr.textbbox((4, 4), text, font=f)
    dr.rectangle((box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2), fill=(20, 20, 30))
    dr.text((4, 4), text, fill=(255, 255, 255), font=f)
    return img


def sheet_from_images(items, cols, size):
    """items = [(label text, PIL image)]; returns one PNG-ready image."""
    rows_n = math.ceil(len(items) / cols)
    sheet = Image.new('RGB', (cols * size, rows_n * size), (200, 205, 210))
    for idx, (text, im) in enumerate(items):
        im = im.convert('RGB').resize((size, size), Image.LANCZOS) if im.size != (size, size) else im.convert('RGB')
        label(im, text)
        sheet.paste(im, ((idx % cols) * size, (idx // cols) * size))
    return sheet


def stick_sheet(d, count, size):
    """Fallback when there is no mesh to render: side view (x right, z up) of the bones."""
    frames = d['frames']
    picks = sorted(set(int(round(i * (len(frames) - 1) / max(count - 1, 1))) for i in range(count)))
    names = list(d['bones'].keys())
    allp = np.array([d['bones'][k][p] for k in names for p in ('head', 'tail')], dtype=float).reshape(-1, 3)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    span = max(hi[0] - lo[0], hi[2] - lo[2], 1e-6) * 1.1
    items = []
    for idx in picks:
        im = Image.new('RGB', (size, size), (219, 229, 237))
        dr = ImageDraw.Draw(im)
        def proj(p):
            return ((p[0] - lo[0]) / span * size * 0.9 + size * 0.05, size * 0.95 - (p[2] - lo[2]) / span * size * 0.9)
        gy = proj((0, 0, lo[2]))[1]
        dr.line((0, gy, size, gy), fill=(70, 75, 80), width=2)
        for k in names:
            a, b = proj(d['bones'][k]['head'][idx]), proj(d['bones'][k]['tail'][idx])
            dr.line((a, b), fill=(30, 90, 190) if (tokens_side(k) or 'L') == 'L' else (30, 150, 70), width=3)
        items.append(('f %d' % frames[idx], im))
    return sheet_from_images(items, 4 if len(items) > 4 else len(items), size)


# ----------------------------------------------------------------------------------------------------------------------------------
# Blender input
def run_blend(path, out_dir, args):
    blender = args.blender or blender_headless.find_blender()
    if not blender:
        raise SystemExit('Blender was not found (install it, put it on PATH or set BLENDER). Video, GIF and image folders work without it.')
    tmp = Path(tempfile.mkdtemp(prefix='animstrip_'))
    jpath = tmp / 'probe.json'
    probe_args = [path, jpath, '--count', args.count, '--size', args.size]
    if not args.no_render:
        probe_args += ['--frames-dir', tmp / 'frames']
    probe_args += ['--view', args.view]
    if args.action:
        probe_args += ['--action', args.action]
    code, text = blender_headless.run_script(PROBE, probe_args, blender)
    if code != 0 or not jpath.exists():
        raise SystemExit('Blender probe failed:\n' + text[-1500:])
    d = json.loads(jpath.read_text())
    if args.keep_json:
        (out_dir / (Path(path).stem + '_probe.json')).write_text(json.dumps(d))
    rows, tables, notes = analyse_probe(d, one_shot=args.one_shot)
    if d.get('rendered'):
        items = [('f %d' % f, Image.open(p)) for f, p in d['rendered']]
        sheet = sheet_from_images(items, 4 if len(items) > 4 else len(items), args.size)
        how = 'Blender Workbench renders, side view'
    elif d['bones']:
        sheet = stick_sheet(d, args.count, args.size)
        how = 'bone stick figure, side view (no mesh to render)'
    else:
        sheet = None
        how = 'no picture (no mesh and no bones)'
    head = ['Action "%s" in %s (Blender %s)' % (d.get('action'), Path(path).name, d.get('blender', '?')),
            'Contact sheet: %s, %d frames' % (how, len(d.get('rendered') or [])) if sheet is not None else how]
    return rows, tables, notes, sheet, head


# ----------------------------------------------------------------------------------------------------------------------------------
# video / GIF / image folder input
def ffprobe_info(path):
    cmd = [FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
           'stream=avg_frame_rate,r_frame_rate,nb_read_frames,width,height,duration', '-of', 'json', str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300).stdout
    s = json.loads(out)['streams'][0]
    def fr(x):
        a, b = x.split('/')
        return float(a) / float(b) if float(b) else 0.0
    fps = fr(s.get('avg_frame_rate', '0/1')) or fr(s.get('r_frame_rate', '0/1'))
    return {'fps': fps, 'frames': int(s.get('nb_read_frames') or 0), 'w': int(s['width']), 'h': int(s['height'])}


def video_gray_frames(path, cap=1500):
    cmd = [FFMPEG, '-v', 'error', '-i', str(path), '-vf', 'scale=96:-2,format=gray', '-frames:v', str(cap), '-f', 'rawvideo', '-']
    raw = subprocess.run(cmd, capture_output=True, timeout=600).stdout
    info = ffprobe_info(path)
    w = 96
    h = max(2, int(round(info['h'] * 96 / info['w'] / 2)) * 2)
    arr = np.frombuffer(raw, dtype=np.uint8)
    nfr = len(arr) // (w * h)
    return arr[:nfr * w * h].reshape(nfr, h, w).astype(np.float32), info


def analyse_pixels(gray, fps):
    """Checks that pixels can answer. gray: [N, H, W] float."""
    rows = []
    n = len(gray)
    lo, hi = THRESHOLDS['duration_range'][0]
    if n < 4:
        return [Row('enough frames', 'check', '%d frames' % n, 'need at least 4')]
    diff = np.mean(np.abs(gray[1:] - gray[:-1]), axis=(1, 2))         # change per frame step
    med = float(np.median(diff))
    seam = float(np.mean(np.abs(gray[0] - gray[-1])))
    expected = (float(diff[-2]) + float(diff[0])) / 2 if len(diff) >= 3 else med
    ratio = seam / max(expected, 1e-9)
    dup = med > 1e-6 and ratio < THRESHOLDS['seam_dup_below'][0]
    seconds = ((n - 1) if dup else n) / fps if fps else 0
    rows.append(Row('frame rate', 'ok' if round(fps) in THRESHOLDS['fps_ok'][0] and abs(fps - round(fps)) < 0.01 else 'check', '%.2f frames per second' % fps, THRESHOLDS['fps_ok'][1]))
    rows.append(Row('duration', 'ok' if lo <= seconds <= hi else 'check', '%d frames = %.2f s' % (n, seconds), THRESHOLDS['duration_range'][1]))
    if med <= 1e-6:
        rows.append(Row('anything moves', 'check', 'consecutive frames are identical', 'an animation needs movement'))
        return rows
    if dup:
        res, txt = 'check', 'last frame repeats the first (seam change %.2fx what its neighbours give)' % ratio
    elif ratio > THRESHOLDS['seam_pop_above'][0]:
        res, txt = 'check', 'POP at the loop point: last to first change is %.1fx what its neighbours give' % ratio
    else:
        res, txt = 'ok', 'last to first change is %.2fx what its neighbours give (1.0 = seamless)' % ratio
    rows.append(Row('loop continuity', res, txt, 'seam change between %.0f%% and %.0fx of its neighbours' % (100 * THRESHOLDS['seam_dup_below'][0], THRESHOLDS['seam_pop_above'][0])))
    spikes = np.where(diff > THRESHOLDS['video_spike_ratio'][0] * med)[0]
    rows.append(Row('pops', 'check' if len(spikes) else 'ok',
                    ('%d sudden change(s), first at frame %d (%.1fx typical)' % (len(spikes), spikes[0] + 1, diff[spikes[0]] / med)) if len(spikes) else 'no frame changes more than %.0fx the typical amount' % THRESHOLDS['video_spike_ratio'][0],
                    'under %.0fx the typical change' % THRESHOLDS['video_spike_ratio'][0]))
    mid = diff[1:-1]
    holds = np.where(mid < THRESHOLDS['video_hold_ratio'][0] * med)[0]
    rows.append(Row('held frames', 'check' if len(holds) else 'ok',
                    ('%d frame(s) barely change while the rest moves, first at frame %d' % (len(holds), holds[0] + 2)) if len(holds) else 'no stutter frames',
                    'none under %.0f%% of the typical change' % (100 * THRESHOLDS['video_hold_ratio'][0])))
    for name in ('joint angle range', 'joint speed', 'foot sliding', 'ground penetration', 'left/right foot timing', 'easing'):
        rows.append(Row(name, 'n/a', 'needs bone data: use the .blend or .fbx', '-'))
    return rows


def run_video(path, out_dir, args):
    p = Path(path)
    is_dir = p.is_dir() or '%' in str(path) or '*' in str(path)
    count = args.count
    if is_dir:
        files = sorted(glob.glob(str(p / '*.png')) + glob.glob(str(p / '*.jpg')) + glob.glob(str(p / '*.jpeg'))) if p.is_dir() else sorted(glob.glob(re.sub(r'%0?\d*d', '*', str(path))))
        if len(files) < 2:
            raise SystemExit('need at least 2 images in ' + str(path))
        ims = [Image.open(f).convert('RGB') for f in files]
        fps = args.fps
        gray = np.array([np.asarray(im.convert('L').resize((96, max(2, int(96 * im.height / im.width))))) for im in ims], dtype=np.float32)
        picks = sorted(set(int(round(i * (len(ims) - 1) / max(count - 1, 1))) for i in range(count)))
        w = args.size
        items = []
        for i in picks:
            im = ims[i].copy()
            im.thumbnail((w, w))
            canvas = Image.new('RGB', (w, w), (200, 205, 210))
            canvas.paste(im, ((w - im.width) // 2, (w - im.height) // 2))
            items.append(('f %d' % (i + 1), canvas))
        sheet = sheet_from_images(items, 4 if len(items) > 4 else len(items), w)
        head = ['Image sequence %s: %d images' % (p.name, len(ims))]
    else:
        gray, info = video_gray_frames(path)
        fps = info['fps']
        total = info['frames'] or len(gray)
        picks = sorted(set(int(round(i * (total - 1) / max(count - 1, 1))) for i in range(count)))
        sel = '+'.join('eq(n\\,%d)' % i for i in picks)
        cols = 4 if len(picks) > 4 else len(picks)
        rws = math.ceil(len(picks) / cols)
        tmp = Path(tempfile.mkdtemp(prefix='animstrip_')) / 'tile.png'
        vf = "select='%s',scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0xC8CDD2,tile=%dx%d:padding=0" % (sel, args.size, args.size, args.size, args.size, cols, rws)
        subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', str(path), '-vf', vf, '-vsync', '0', '-frames:v', '1', str(tmp)], timeout=300, check=True)
        sheet = Image.open(tmp).convert('RGB')
        for idx, fno in enumerate(picks):
            cell = sheet.crop(((idx % cols) * args.size, (idx // cols) * args.size, (idx % cols + 1) * args.size, (idx // cols + 1) * args.size))
            label(cell, 'f %d' % (fno + 1))
            sheet.paste(cell, ((idx % cols) * args.size, (idx // cols) * args.size))
        head = ['Video %s: %.2f fps, %d frames, %dx%d (ffmpeg tile filter)' % (p.name, fps, total, info['w'], info['h'])]
    rows = analyse_pixels(gray, fps)
    return rows, [], ['Pixel checks only: motion is judged from how much each frame differs from the last, not from joints.'], sheet, head


# ----------------------------------------------------------------------------------------------------------------------------------
def render_report(title_lines, rows, tables, notes):
    out = list(title_lines) + ['']
    out += ['Verdicts (ok = fine, check = look at this, n/a = cannot be measured from this input)', '']
    w = max(len(r.name) for r in rows)
    for r in rows:
        out.append('  %-*s  %-5s  %s' % (w, r.name, r.result.upper(), r.measured))
    out.append('')
    for t, hdr, trs in tables:
        out.append(t)
        widths = [max(len(str(x)) for x in [hdr[i]] + [rw[i] for rw in trs]) for i in range(len(hdr))]
        out.append('  ' + '  '.join(str(h).ljust(widths[i]) for i, h in enumerate(hdr)))
        for rw in trs:
            out.append('  ' + '  '.join(str(c).ljust(widths[i]) for i, c in enumerate(rw)))
        out.append('')
    if notes:
        out += ['Notes'] + ['  - ' + x for x in notes] + ['']
    out += ['Limits used (the THRESHOLDS table in tools/animation_strip.py; judgement calls, each with its reason)', '']
    for r in rows:
        out.append('  %-*s  %s' % (w, r.name, r.limit))
    out += ['', 'Not judged here: feel, weight, appeal, character. Measured, not watched.']
    return '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('input', help='.blend/.fbx/.obj/.glb, a video or GIF, or a folder of numbered images')
    ap.add_argument('--out', default='animation_strip_out', help='output folder (default ./animation_strip_out)')
    ap.add_argument('--count', type=int, default=8, help='number of key frames in the sheet (default 8)')
    ap.add_argument('--size', type=int, default=256, help='pixels per frame (default 256)')
    ap.add_argument('--view', default='auto', choices=['auto', 'x', '-x', 'y', '-y'],
                    help='which way is right on the picture: auto = the way the body travels, else -Y (creatures face -Y, so they face right)')
    ap.add_argument('--action', help='name of the action to judge (default: the one playing, or the one with most curves)')
    ap.add_argument('--fps', type=float, default=24.0, help='frame rate for image folders (videos and files carry their own)')
    ap.add_argument('--blender', help='path to blender.exe (default: auto-find)')
    ap.add_argument('--one-shot', action='store_true', help='the clip does not loop (a jump, an attack): skip the loop-point check')
    ap.add_argument('--no-render', action='store_true', help='skip the Blender renders (faster); the sheet then shows a bone stick figure')
    ap.add_argument('--keep-json', action='store_true', help='also save the raw probe numbers')
    ap.add_argument('--strict', action='store_true', help='exit 1 if any check says "check"')
    args = ap.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = args.input
    low = src.lower()
    if low.endswith(('.blend', '.fbx', '.obj', '.glb', '.gltf')):
        rows, tables, notes, sheet, head = run_blend(src, out_dir, args)
    else:
        rows, tables, notes, sheet, head = run_video(src, out_dir, args)
    stem = Path(src).stem if not Path(src).is_dir() else Path(src).name
    if sheet is not None:
        sheet.save(out_dir / (stem + '_strip.png'))
        head.append('Picture: %s' % (out_dir / (stem + '_strip.png')))
    text = render_report(head, rows, tables, notes)
    (out_dir / (stem + '_report.txt')).write_text(text, encoding='utf-8')
    print(text)
    return 1 if args.strict and any(r.result == 'check' for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
