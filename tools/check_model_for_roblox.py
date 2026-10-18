#!/usr/bin/env python3
"""Pre-upload check for a 3D model (BD-642, docs/163): will Roblox take it, and is it the size and shape the game expects?

    python tools/check_model_for_roblox.py assets/blender/creatures/fbx/creature_pteranodon.fbx
    python tools/check_model_for_roblox.py model.blend other.obj --out report.txt
    python tools/check_model_for_roblox.py model.fbx --strict          # warnings also make the exit code 1

Blender runs in a SEPARATE headless process (tools/blender_model_probe.py, never the live MCP session) and measures the file; this script
turns the numbers into a plain list of PASS / WARN / FAIL lines. Exit code 0 = no FAIL (with --strict: no WARN either), 1 = at least one
FAIL, 2 = Blender not found or the file could not be read. All limits live in ONE table, LIMITS below, each with its reason; the ones
that are Roblox's own numbers say so, the rest are this project's judgement.
Checks: triangles per part and total, size in studs against the Compy, pivot per part, unapplied scale and rotation, flipped or
inconsistent faces, loose and doubled vertices, n-gons, zero-area faces, materials, UV map and UV overlap, vertex colours, bone
influences, file size, part names, armature and animation presence.
It cannot judge: whether the model is nice to look at, whether the pivot is where the animator wants it, or how it looks lit in Studio.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_headless  # noqa: E402

PROBE = Path(__file__).resolve().parent / 'blender_model_probe.py'

# ONE table of limits: name -> (value, source, plain reason). "Roblox" = a number Roblox publishes; "project" = our own judgement.
LIMITS = {
    'max_tris_per_part': (21844, 'Roblox', 'the most triangles one MeshPart may have; over this the upload is refused'),
    'warn_tris_fraction': (0.8, 'project', 'above 80 percent of the part limit: heavy for phones when many are on screen; split or simplify'),
    'max_stud_size': (2048, 'Roblox', 'the biggest size of a part in studs along one side'),
    'ratio_far_from_compy': ((0.02, 100.0), 'project', 'longest side is under 2 percent or over 100 times a Compy: almost always a unit mistake (centimetres or metres)'),
    'scale_tolerance': (0.001, 'project', 'object scale further than 0.1 percent from 1 is "not applied"'),
    'rotation_tolerance_deg': (0.01, 'project', 'object rotation over 0.01 degrees is "not applied"'),
    'inside_out_fraction': (0.05, 'project', 'a closed piece whose signed volume is more than 5 percent of its own box volume negative is inside out (Roblox draws one side only); built into tools/blender_model_probe.py'),
    'duplicate_vert_fraction': (0.01, 'project', 'more than 1 percent of vertices doubled in place: merge them (Mesh, Clean Up, Merge by Distance)'),
    'uv_overlap_fraction': (0.05, 'project', 'more than 5 percent of the painted UV area lies on top of other UV faces (fine for mirrored halves on purpose)'),
    'uv_outside_fraction': (0.01, 'project', 'more than 1 percent of UV faces lie outside the 0..1 square: the texture tiles or smears'),
    'max_influences': (4, 'Roblox', 'a skinned vertex follows at most 4 bones; more are dropped'),
    'pivot_outside_margin': (0.05, 'project', 'the origin lies outside the part box by more than 5 percent of the part size: it swings around a far point when rotated'),
    'pivot_bottom_tolerance': (0.05, 'project', 'bottom-centre pivot: origin within 5 percent of the box size from the middle of the feet (docs/56)'),
    'file_warn_mb': (10, 'project', 'bigger files than this are heavy to upload and to keep in git'),
    'file_fail_mb': (20, 'project', 'conservative guard for the upload size limit; check create.roblox.com/docs for the current number'),
    'name_max_chars': (100, 'Roblox', 'an Instance name is at most 100 characters'),
}
# The size of a Compy at spawn (studs). Read from src/shared/ScaleLadder.luau at run time; these are the fallback if the file moves.
COMPY_FALLBACK = {'width': 3.49, 'height': 6.60, 'length': 7.69}
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
DUP_SUFFIX = re.compile(r'\.\d{3,}$')


def reference_compy():
    """(width, height, length, source) of the Compy from the game's own size table."""
    src = ROOT / 'src/shared/ScaleLadder.luau'
    try:
        text = src.read_text(encoding='utf-8')
        m = re.search(r'compy\s*=\s*\{[^}]*?width\s*=\s*([\d.]+)[^}]*?height\s*=\s*([\d.]+)[^}]*?length\s*=\s*([\d.]+)', text)
        if m:
            return float(m.group(1)), float(m.group(2)), float(m.group(3)), 'src/shared/ScaleLadder.luau, species.compy (measured in Studio at spawn)'
    except OSError:
        pass
    c = COMPY_FALLBACK
    return c['width'], c['height'], c['length'], 'built-in copy of the same numbers (ScaleLadder.luau not found)'


class Finding:
    def __init__(self, status, name, detail):
        self.status, self.name, self.detail = status, name, detail   # status: PASS / WARN / FAIL


def classify_origin(m):
    """Where the part's origin sits relative to its own box: 'bottom centre', 'centre', 'outside' or 'other'."""
    lo, hi, o = m['box_min'], m['box_max'], m['origin']
    size = [max(hi[i] - lo[i], 1e-9) for i in range(3)]
    margin = LIMITS['pivot_outside_margin'][0]
    for i in range(3):
        if o[i] < lo[i] - margin * max(size) or o[i] > hi[i] + margin * max(size):
            return 'outside'
    tol = LIMITS['pivot_bottom_tolerance'][0]
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    mid = ((lo[2] + hi[2]) / 2)
    near_xy = abs(o[0] - cx) <= tol * size[0] + 1e-6 and abs(o[1] - cy) <= tol * size[1] + 1e-6
    if near_xy and abs(o[2] - lo[2]) <= tol * size[2] + 1e-6:
        return 'bottom centre'
    if near_xy and abs(o[2] - mid) <= tol * size[2] + 1e-6:
        return 'centre'
    return 'other'


def fmt_list(items, limit=4):
    items = list(items)
    s = ', '.join(items[:limit])
    return s + (' and %d more' % (len(items) - limit) if len(items) > limit else '')


def evaluate(d, compy=None):
    """Turn the probe numbers into a list of Finding. Pure function (tested without Blender)."""
    cw, ch, cl, csrc = compy or reference_compy()
    out = []
    meshes = [m for m in d['meshes'] if not m.get('empty')]
    out_names = [m['name'] for m in d['meshes']]

    def add(status, name, detail):
        out.append(Finding(status, name, detail))

    if not meshes:
        add('FAIL', 'meshes', 'the file has no mesh with any geometry')
        return out

    # --- triangles
    limit = LIMITS['max_tris_per_part'][0]
    over = [m for m in meshes if m['tris'] > limit]
    heavy = [m for m in meshes if limit * LIMITS['warn_tris_fraction'][0] < m['tris'] <= limit]
    total = sum(m['tris'] for m in meshes)
    worst = max(meshes, key=lambda m: m['tris'])
    if over:
        add('FAIL', 'triangles per part', '%s over the %s limit (%s)' % (fmt_list('%s %s' % (m['name'], format(m['tris'], ',')) for m in over), format(limit, ','), 'split the part'))
    elif heavy:
        add('WARN', 'triangles per part', '%s is close to the %s limit' % (fmt_list('%s %s' % (m['name'], format(m['tris'], ',')) for m in heavy), format(limit, ',')))
    else:
        add('PASS', 'triangles per part', 'biggest part %s has %s of %s allowed' % (worst['name'], format(worst['tris'], ','), format(limit, ',')))
    add('PASS', 'triangles in total', '%s triangles in %d part(s), %s vertices' % (format(total, ','), len(meshes), format(sum(m['verts'] for m in meshes), ',')))

    # --- size against the Compy
    lo = [min(m['box_min'][i] for m in meshes) for i in range(3)]
    hi = [max(m['box_max'][i] for m in meshes) for i in range(3)]
    size = [hi[i] - lo[i] for i in range(3)]               # X width, Y length, Z height (Blender); Roblox: X, Z, Y up
    w, ln, h = size[0], size[1], size[2]
    txt = '%swidth %.2f, height %.2f, length %.2f studs (Blender X, Z, Y; 1 unit = 1 stud)' % ('all %d parts together: ' % len(meshes) if len(meshes) > 1 else '', w, h, ln)
    biggest = max(size)
    ratio = biggest / max(cw, ch, cl)
    if biggest > LIMITS['max_stud_size'][0]:
        add('FAIL', 'size in studs', txt + ': longer than the %d stud limit' % LIMITS['max_stud_size'][0])
    elif ratio < LIMITS['ratio_far_from_compy'][0][0] or ratio > LIMITS['ratio_far_from_compy'][0][1]:
        add('WARN', 'size in studs', txt + ': %.3gx the Compy\'s longest side, probably the wrong unit' % ratio)
    else:
        add('PASS', 'size in studs', txt + '. Compy for comparison: width %.2f, height %.2f, length %.2f (%s). This is %.2fx the Compy\'s height, %.2fx its length.'
            % (cw, ch, cl, csrc, h / ch, ln / cl))
    if d.get('unit_scale', 1.0) not in (1.0,) and abs(d.get('unit_scale', 1.0) - 1.0) > 1e-6:
        add('WARN', 'scene units', 'the scene unit scale is %.4g, not 1: exports may come out %.4gx the size you see' % (d['unit_scale'], d['unit_scale']))

    # --- pivots
    kinds = {m['name']: classify_origin(m) for m in meshes}
    outside = [n for n, k in kinds.items() if k == 'outside']
    if outside:
        add('WARN', 'pivot (origin) per part', 'origin lies outside the part: %s (it will swing around a far point when rotated)' % fmt_list(outside))
    elif len(meshes) == 1:
        k = kinds[meshes[0]['name']]
        if k == 'bottom centre':
            add('PASS', 'pivot (origin) per part', 'origin at the bottom centre, the project convention (docs/56)')
        else:
            where = {'centre': 'in the middle of the model', 'other': 'somewhere inside the model box (not at the feet, not in the middle)'}[k]
            add('WARN', 'pivot (origin) per part', 'origin is %s, not at the bottom centre the world kit uses (docs/56); box z runs %.2f to %.2f' % (where, lo[2], hi[2]))
    else:
        counts = {}
        for k in kinds.values():
            counts[k] = counts.get(k, 0) + 1
        add('PASS', 'pivot (origin) per part', 'every origin is inside its part (%s); whole model box z runs %.2f to %.2f' % (', '.join('%d %s' % (v, k) for k, v in counts.items()), lo[2], hi[2]))

    # --- unapplied scale and rotation
    bad = []
    mirrored = []
    for m in meshes:
        ls, lr = m.get('local_scale', [1, 1, 1]), m.get('local_rotation_deg', [0, 0, 0])
        scale_off = any(abs(abs(x) - 1) > LIMITS['scale_tolerance'][0] for x in ls)
        rot_off = any(abs(x) > LIMITS['rotation_tolerance_deg'][0] for x in lr)
        if scale_off or rot_off:
            bad.append('%s (%s)' % (m['name'], ' and '.join(x for x, on in (('scale %.3g x %.3g x %.3g' % tuple(ls), scale_off), ('turned %.0f, %.0f, %.0f degrees' % tuple(lr), rot_off)) if on)))
        if any(x < 0 for x in ls):
            mirrored.append(m['name'])
    if bad:
        hint = ' In an FBX the turns often come from the importer axis change or from the pose at frame 1: check the .blend.' if d.get('kind') == 'fbx' else ''
        add('WARN', 'scale and rotation applied', 'not applied: %s (Object, Apply, Rotation and Scale).%s' % (fmt_list(bad, 3), hint))
    else:
        add('PASS', 'scale and rotation applied', 'every part has scale 1 and no turn on the object')
    if mirrored:
        add('WARN', 'mirrored parts', 'negative scale on %s: faces may come out inside out' % fmt_list(mirrored))

    # --- faces: inside out, inconsistent
    inside_out, mixed = [], []
    for m in meshes:
        if m.get('inside_out_shells', 0) > 0:
            inside_out.append('%s (%d of %d closed piece(s), %s triangles)' % (m['name'], m['inside_out_shells'], m['shells'], format(m['inside_out_tris'], ',')))
        elif m['inconsistent_edges'] > 0:
            mixed.append('%s (%d edges)' % (m['name'], m['inconsistent_edges']))
    if inside_out:
        add('FAIL', 'face direction', 'inside out (normals point in): %s. Roblox draws one side only, so these pieces look hollow or vanish. Mesh, Normals, Recalculate Outside' % fmt_list(inside_out, 3))
    if mixed:
        add('WARN', 'face direction', 'neighbouring faces disagree about which side is out on %s: some faces are flipped and will vanish from one side' % fmt_list(mixed, 3))
    if not inside_out and not mixed:
        add('PASS', 'face direction', 'all faces agree on which side is out')

    # --- vertices and faces
    loose = ['%s (%d)' % (m['name'], m['loose_verts']) for m in meshes if m['loose_verts'] > 0]
    loose += ['%s (%d loose edges)' % (m['name'], m['loose_edges']) for m in meshes if m['loose_edges'] > 0]
    dups = ['%s (%d)' % (m['name'], m['duplicate_verts']) for m in meshes if m['duplicate_verts'] > LIMITS['duplicate_vert_fraction'][0] * max(m['verts'], 1)]
    zero = ['%s (%d)' % (m['name'], m['zero_area_faces']) for m in meshes if m['zero_area_faces'] > 0]
    ngons = ['%s (%d)' % (m['name'], m['ngons']) for m in meshes if m['ngons'] > 0]
    add('WARN' if loose else 'PASS', 'loose vertices and edges', ('stray geometry on ' + fmt_list(loose)) if loose else 'none')
    add('WARN' if dups else 'PASS', 'doubled vertices', ('vertices doubled in place on ' + fmt_list(dups)) if dups else 'none to speak of')
    add('WARN' if zero else 'PASS', 'zero-area faces', ('faces with no area on ' + fmt_list(zero)) if zero else 'none')
    add('WARN' if ngons else 'PASS', 'n-gons (faces with more than 4 corners)', ('on %s: Roblox cuts them into triangles its own way; triangulate first' % fmt_list(ngons)) if ngons else 'none')
    openm = [m['name'] for m in meshes if not m.get('closed')]
    add('PASS', 'open edges', ('%d of %d part(s) are open shells (fine for leaves and wings, not for solid bodies): %s' % (len(openm), len(meshes), fmt_list(openm, 3))) if openm else 'every part is a closed shell')

    # --- materials
    nomat = [m['name'] for m in meshes if m['material_slots'] == 0]
    empty = [m['name'] for m in meshes if m['empty_slots'] > 0 or (m['material_slots'] > 0 and m['faces_on_empty_slot'] > 0)]
    missing = sorted(set(i for m in meshes for i in m['missing_images']))
    if missing:
        add('FAIL', 'materials and textures', 'texture file(s) not found on disk and not packed: %s' % fmt_list(missing))
    elif nomat or empty:
        bits = []
        if nomat:
            bits.append('no material on ' + fmt_list(nomat))
        if empty:
            bits.append('empty material slot on ' + fmt_list(empty))
        add('WARN', 'materials and textures', '; '.join(bits) + ' (Roblox uses its default grey)')
    else:
        add('PASS', 'materials and textures', '%d material(s), no empty slots, no missing images' % len(set(x for m in meshes for x in m['materials'])))

    # --- UVs and vertex colours
    ov = ['%s (%.0f%%)' % (m['name'], 100 * m['uv_overlap']) for m in meshes if m['uv_overlap'] is not None and m['uv_overlap'] > LIMITS['uv_overlap_fraction'][0]]
    out_uv = ['%s (%.0f%%)' % (m['name'], 100 * m['uv_outside']) for m in meshes if m['uv_outside'] is not None and m['uv_outside'] > LIMITS['uv_outside_fraction'][0]]
    nouv_plain = [m['name'] for m in meshes if not m['uv_layers'] and not m['color_attributes']]
    nouv_vc = [m['name'] for m in meshes if not m['uv_layers'] and m['color_attributes']]
    if nouv_plain:
        add('WARN', 'UV map', 'no UV map (and no vertex colours) on %s: textures and patterns cannot be put on it' % fmt_list(nouv_plain))
    elif nouv_vc:
        add('PASS', 'UV map', 'no UV map on %s, but they carry vertex colours, so colour comes from those (no textures possible)' % fmt_list(nouv_vc))
    else:
        add('PASS', 'UV map', 'every part has a UV map')
    add('WARN' if ov else 'PASS', 'overlapping UVs', ('UV faces lie on top of each other on %s (fine if the halves are mirrored on purpose)' % fmt_list(ov)) if ov else 'no meaningful overlap')
    add('WARN' if out_uv else 'PASS', 'UVs outside 0..1', ('on ' + fmt_list(out_uv)) if out_uv else 'all UVs inside the square')
    vc = [m['name'] for m in meshes if m['color_attributes']]
    add('PASS', 'vertex colours', ('present on %d of %d part(s) (%s)' % (len(vc), len(meshes), fmt_list(sorted(set(c for m in meshes for c in m['color_attributes'])), 3))) if vc else 'none (flat material colours only)')

    # --- armature and animation
    arms, acts = d.get('armatures', []), d.get('actions', [])
    infl = [m for m in meshes if m.get('max_influences', 0) > LIMITS['max_influences'][0]]
    if arms:
        add('PASS', 'armature', '%d armature(s), %d bone(s); %d action(s)%s' % (len(arms), sum(a['bones'] for a in arms), len(acts), (': ' + fmt_list(a['name'] for a in acts)) if acts else ' (no animation in the file)'))
    else:
        add('PASS', 'armature', 'none (a plain static model)' + ('; the file still holds %d action(s)' % len(acts) if acts else ''))
    if infl:
        add('WARN', 'bone influences', '%s: more than %d bones per vertex (%s)' % (fmt_list(m['name'] for m in infl), LIMITS['max_influences'][0], fmt_list('%s %d' % (m['name'], m['max_influences']) for m in infl)))
    elif any(m.get('vertex_groups') for m in meshes):
        add('PASS', 'bone influences', 'at most %d bone(s) per vertex' % max(m.get('max_influences', 0) for m in meshes))
    rigged_meshes = [m for m in meshes if m.get('armature_modifier')]
    if arms and not rigged_meshes and len(meshes) > 0 and not any(m.get('parent_type') == 'BONE' for m in meshes) and any(a['bones'] > 0 for a in arms):
        add('WARN', 'armature follows mesh', 'the file has bones but no mesh follows them (no armature modifier, no bone parent)')

    # --- file size
    mb = d['file_bytes'] / 1048576.0
    if mb > LIMITS['file_fail_mb'][0]:
        add('FAIL', 'file size', '%.1f MB is over the %d MB guard' % (mb, LIMITS['file_fail_mb'][0]))
    elif mb > LIMITS['file_warn_mb'][0]:
        add('WARN', 'file size', '%.1f MB (over %d MB)' % (mb, LIMITS['file_warn_mb'][0]))
    else:
        add('PASS', 'file size', '%.2f MB' % mb)

    # --- names
    names = out_names
    fail_names, warn_names = [], []
    seen = {}
    for n in names:
        seen.setdefault(n, 0)
        seen[n] += 1
    dups_n = [n for n, c in seen.items() if c > 1]
    for n in names:
        if not n or len(n) > LIMITS['name_max_chars'][0]:
            fail_names.append('"%s..." (%d characters)' % (n[:12], len(n)))
        elif DUP_SUFFIX.search(n):
            fail_names.append('%s (Blender renamed a duplicate; give each part its own real name)' % n)
        elif not IDENT.match(n):
            warn_names.append(n)
    lower = {}
    for n in names:
        lower.setdefault(n.lower(), []).append(n)
    case_clash = [v for v in lower.values() if len(set(v)) > 1]
    if dups_n:
        fail_names.append('used twice: ' + fmt_list(dups_n))
    if fail_names:
        add('FAIL', 'part names', fmt_list(fail_names, 3))
    if warn_names or case_clash:
        bits = []
        if warn_names:
            bits.append('%s cannot be written as part.Name in a script (spaces, dots, dashes or a leading digit)' % fmt_list('"%s"' % n for n in warn_names))
        if case_clash:
            bits.append('names that differ only by capitals: ' + fmt_list(' / '.join(sorted(set(v))) for v in case_clash))
        add('WARN', 'part names in scripts', '; '.join(bits))
    if not fail_names and not warn_names and not case_clash:
        add('PASS', 'part names', '%d name(s), all unique and usable in scripts' % len(names))
    return out


def part_table(d, limit=25):
    meshes = sorted((m for m in d['meshes'] if not m.get('empty')), key=lambda m: -m['tris'])
    rows = [['part', 'triangles', 'W x H x L (studs)', 'origin', 'material slots', 'UV', 'flags']]
    for m in meshes[:limit]:
        flags = []
        if m['ngons']:
            flags.append('%d n-gon' % m['ngons'])
        if m['loose_verts']:
            flags.append('loose')
        if m['inconsistent_edges']:
            flags.append('mixed faces')
        if m['hidden']:
            flags.append('hidden')
        rows.append([m['name'][:30], format(m['tris'], ','), '%.2f x %.2f x %.2f' % (m['size'][0], m['size'][2], m['size'][1]), classify_origin(m),
                     str(m['material_slots']), 'yes' if m['uv_layers'] else 'no', ', '.join(flags) or '-'])
    more = len(meshes) - limit
    return rows, more


def render(d, findings, path):
    lines = []
    nf = sum(1 for f in findings if f.status == 'FAIL')
    nw = sum(1 for f in findings if f.status == 'WARN')
    npass = sum(1 for f in findings if f.status == 'PASS')
    lines.append('Model check: %s (%s, %.1f KB, Blender %s)' % (Path(path).name, d['kind'], d['file_bytes'] / 1024.0, d.get('blender', '?')))
    lines.append('RESULT: %s   (%d fail, %d warn, %d pass)' % ('FAIL' if nf else ('WARN' if nw else 'PASS'), nf, nw, npass))
    lines.append('')
    w = max(len(f.name) for f in findings)
    for status in ('FAIL', 'WARN', 'PASS'):
        for f in findings:
            if f.status == status:
                lines.append('  %-4s  %-*s  %s' % (status, w, f.name, f.detail))
    lines.append('')
    rows, more = part_table(d)
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines.append('Parts (largest first)')
    for i, r in enumerate(rows):
        lines.append('  ' + '  '.join(c.ljust(widths[k]) for k, c in enumerate(r)))
        if i == 0:
            lines.append('  ' + '  '.join('-' * widths[k] for k in range(len(widths))))
    if more > 0:
        lines.append('  ... and %d more part(s)' % more)
    lines.append('')
    lines.append('Limits used: see LIMITS in tools/check_model_for_roblox.py (each has its source, Roblox or project, and a plain reason).')
    lines.append('Not judged here: looks, taste, whether the pivot is where the animator wants it, how it reads lit in Studio.')
    return '\n'.join(lines)


def probe_many(paths, blender=None):
    """One Blender start for all files. Returns a list of probe dictionaries in the same order."""
    exe = blender or blender_headless.find_blender()
    if not exe:
        raise FileNotFoundError('Blender was not found (install it, put it on PATH or set BLENDER)')
    for p in paths:
        if not Path(p).is_file():
            raise FileNotFoundError('input file not found: %s' % p)
    tmp = Path(tempfile.mkdtemp(prefix='modelcheck_'))
    code, text = blender_headless.run_script(PROBE, ['--batch', tmp] + [str(Path(p).resolve()) for p in paths], exe, timeout=1800)
    out = []
    for i, p in enumerate(paths):
        f = tmp / ('%d.json' % i)
        if code != 0 or not f.exists():
            raise RuntimeError('Blender probe failed on %s:\n%s' % (p, text[-1500:]))
        out.append(json.loads(f.read_text()))
    return out


def probe(path, blender=None):
    return probe_many([path], blender)[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('files', nargs='+', help='.fbx / .obj / .blend / .glb files')
    ap.add_argument('--out', help='also write the report to this text file')
    ap.add_argument('--json', help='also write the raw numbers (one file only)')
    ap.add_argument('--blender', help='path to blender.exe (default: auto-find)')
    ap.add_argument('--strict', action='store_true', help='exit 1 on WARN as well')
    args = ap.parse_args(argv)
    worst = 0
    texts = []
    try:
        probes = probe_many(args.files, args.blender)
    except (FileNotFoundError, RuntimeError) as e:
        print('ERROR: %s' % e, file=sys.stderr)
        return 2
    for f, d in zip(args.files, probes):
        findings = evaluate(d)
        text = render(d, findings, f)
        texts.append(text)
        print(text)
        print()
        if args.json and len(args.files) == 1:
            Path(args.json).write_text(json.dumps(d, indent=1), encoding='utf-8')
        if any(x.status == 'FAIL' for x in findings):
            worst = max(worst, 1)
        elif args.strict and any(x.status == 'WARN' for x in findings):
            worst = max(worst, 1)
    if args.out:
        Path(args.out).write_text('\n\n'.join(texts) + '\n', encoding='utf-8')
    return worst


if __name__ == '__main__':
    sys.exit(main())
