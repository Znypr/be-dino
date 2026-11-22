"""Offline preview of the game's low-poly dino animation on a Blender model (BD-1291 Compy compare). Headless Blender, CPU, Workbench.

  python tools/blender/preview_lowpoly_anim.py --blend A.blend --label "Hunyuan V3" [--blend B.blend --label "Blender"] --out DIR
         [--mp4 OUT.mp4] [--sheet OUT.png] [--size 400] [--frames N]

What it reproduces (ported line by line, game files in brackets):
  * the part joints: LowPolyAnimator.pivotFor from each part's BOUNDING BOX (head = bottom back, tail = front end, arm / leg = top centre,
    body = centre), in Roblox axes (front -Z, Blender +Y faces front: Roblox X = Blender x, Y = z, Z = -y; docs/169 "Facing, settled");
  * the part offset C1 = (shift * pivot * CFrame.Angles(pitch, yaw, roll) * -pivot * (0, dy, dz)) [LowPolyAnimator.apply];
  * DinoRigClipsEnabled = true (the playtest profile): idle / walk / run loops [LowPolyGait.sample, Gait.bob, LowPolyClips.Gait], the step
    phase and eased speed [apply, LowPolyPose.stepRate], the airborne tuck and landing squash [LowPolyPose.sampleAction, airWeight,
    landWeight], the jump / land hop clips and the eat / happy clips [LowPolyClips.Data], the head / tail follow-through springs
    [Gait.stepFollow / addFollow]. Clip keys come from tools/blender/dino_clips.py (the source LowPolyClips.luau is generated from).
  * game scale: the parts are posed in model units, translations (bob, peck, jump) are converted from game studs with --game-height
    (Compy: 3.0 model studs x LowPolyDinoAssets scale 2.2 = 6.6).
Not reproduced: DinoMotion's whole-model C0 squash / stretch / turn poses (they rescale part sizes, so the game's pivots move with them), the
hip-dip floor lift (needs the physics ray), the humanoid's real speed curve and turning (turn rate is 0 here), remote 20 Hz stepping. The
jump arc is drawn at --jump-scale (default 0.3) of the real 6.4 stud arc so the dino stays in frame; the poses use the real vertical speed.

Per frame it also measures, per joint (Head, Tail, arms, legs against the Body), in GAME studs:
  gap     how much further than at rest a CUT FACE (faces tagged 5 = cap by the builders: where a part was cut flat) sticks out of
          every other part, i.e. an opening you can see into / a flat cut showing; exposed cut area (studs^2) in metrics.json cut_area;
  drift   how far the real joint (centre of the child's cut face, or of its seam on the body when it has none) moves against the body:
          a pivot off that joint swings the part in a wrong arc and slides it at the join. It also holds the clips' own translations
          (head peck, the landing squash moves body and legs apart by up to 0.4 stud), so the static "pivot -> joint" distance is printed too;
  floor   how deep any part goes below the floor it stood on at rest.
Writes DIR/<label>/<view>/f0001.png..., DIR/<label>/metrics.json, and with --mp4 / --sheet a side-by-side video and contact sheet.
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
PARTS = ("Body", "Head", "Tail", "ArmL", "ArmR", "LegL", "LegR")
JOINTS = ("Head", "Tail", "ArmL", "ArmR", "LegL", "LegR")

try:
    import bpy  # type: ignore
    INSIDE = True
except ImportError:
    INSIDE = False

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


def args_all(name):
    return [ARGS[i + 1] for i, a in enumerate(ARGS) if a == name]


FPS = 30
GAME_HEIGHT = float(arg("--game-height", "6.6"))
JUMP_SCALE = float(arg("--jump-scale", "0.3"))
SIZE = int(arg("--size", "400"))

# ------------------------------------------------------------------ the scripted session (seconds): what the player does
# idle -> walk -> run -> slow down -> standing jump -> idle -> eat -> happy (growth) -> idle
T_WALK, T_RUN, T_STOP, T_JUMP, T_EAT, T_HAPPY, T_END = 1.6, 3.6, 5.4, 6.4, 8.0, 9.6, 11.4
SPEED_WALK, SPEED_RUN = 0.35, 1.0
JUMP_V, GRAVITY = 50.0, 196.2  # Roblox defaults (JumpPower 50, workspace.Gravity 196.2)


def segment(t):
    if t < T_WALK:
        return "idle"
    if t < T_RUN:
        return "walk"
    if t < T_STOP:
        return "run"
    if t < T_JUMP:
        return "stop"
    if t < T_EAT:
        return "jump"
    if t < T_HAPPY:
        return "eat"
    return "happy"


# ------------------------------------------------------------------ pure ports of the Luau (no bpy)
sys.path.insert(0, HERE)
import dino_clips  # noqa: E402

D2R = math.pi / 180
NECK_SHARE = dino_clips.NECK_SHARE
SIDE_ROLL = {"wing", "flipper", "arm"}


def clamp(x, a, b):
    return a if x < a else b if x > b else x


def ease(u):
    u = clamp(u, 0, 1)
    return u * u * (3 - 2 * u)


def hermite(keys, t):
    n = len(keys)
    if n == 0 or t <= keys[0][0] or t >= keys[-1][0]:
        return 0.0
    i = 0
    while i < n - 2 and keys[i + 1][0] <= t:
        i += 1

    def slope(j):
        if j <= 0 or j >= n - 1:
            return 0.0
        ta, va = keys[j - 1]
        tb, vb = keys[j]
        tc, vc = keys[j + 1]
        if (vb - va) * (vc - vb) <= 0:
            return 0.0
        cap = 3 * min(abs((vb - va) / (tb - ta)), abs((vc - vb) / (tc - tb)))
        return clamp((vc - va) / (tc - ta), -cap, cap)
    t0, v0 = keys[i]
    t1, v1 = keys[i + 1]
    h = t1 - t0
    if h <= 0:
        return v0
    m0, m1 = slope(i), slope(i + 1)
    u = (t - t0) / h
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * h * m0 + (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * h * m1


def cyclic(keys, length, t):
    n = len(keys)
    if n == 0 or length <= 0:
        return 0.0
    t = t % length
    i = 0
    while i < n - 2 and keys[i + 1][0] <= t:
        i += 1

    def at(j):  # 0-based with wrap (key n-1 is key 0 one loop later)
        if j < 0:
            return keys[n - 1 + j][0] - length, keys[n - 1 + j][1]
        if j > n - 1:
            return keys[j - n + 1][0] + length, keys[j - n + 1][1]
        return keys[j]

    def slope(j):
        ta, va = at(j - 1)
        tb, vb = at(j)
        tc, vc = at(j + 1)
        if (vb - va) * (vc - vb) <= 0:
            return 0.0
        cap = 3 * min(abs((vb - va) / (tb - ta)), abs((vc - vb) / (tc - tb)))
        return clamp((vc - va) / (tc - ta), -cap, cap)
    t0, v0 = keys[i]
    t1, v1 = keys[i + 1]
    h = t1 - t0
    if h <= 0:
        return v0
    m0, m1 = slope(i), slope(i + 1)
    u = (t - t0) / h
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * h * m0 + (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * h * m1


def sample_tracks(tracks, role, side, t, fn):
    """Clips.sample / sampleCycle: returns pitch, yaw, roll (rad), bob, fwd (fractions)."""
    o = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "bob": 0.0, "fwd": 0.0}
    if "root" in tracks and "bob" in tracks["root"]:
        o["bob"] = fn(tracks["root"]["bob"], t)
    tr, k = tracks.get(role), 1.0
    if tr is None and role == "neck":
        tr, k = tracks.get("head"), NECK_SHARE
    if tr is None or role == "root":
        return o
    d = D2R * k
    for ch in ("pitch", "yaw"):
        if ch in tr:
            o[ch] = fn(tr[ch], t) * d
    if "roll" in tr:
        o["roll"] = fn(tr["roll"], t) * d * (-1 if role in SIDE_ROLL and side < 0 else 1)
    if "fwd" in tr and role == "head":
        o["fwd"] = fn(tr["fwd"], t)
    return o


def clip_sample(name, role, side, t):
    c = dino_clips.CLIPS[name]
    return sample_tracks(c["tracks"], role, side, t, hermite)


def cycle_sample(name, role, side, t):
    c = dino_clips.GAIT[name]
    return sample_tracks(c["tracks"], role, side, t, lambda keys, tt: cyclic(keys, c["length"], tt))


GAIT_ROLES = {"head", "neck", "tail", "arm", "leg"}
WALK_FROM, RUN_FROM, RUN_FULL = 0.25, 0.45, 0.8
MAX_ANGLE, MAX_BOB, PECK = 0.9, 0.04, 0.4


def weights(s):
    w = clamp(s, 0, 1)
    g = ease(w / WALK_FROM)
    r = ease((w - RUN_FROM) / (RUN_FULL - RUN_FROM))
    return 1 - g, g * (1 - r), g * r


def gait_offset(role, side, lead):
    if role == "leg":
        return ((0 if side < 0 else 0.5) + (0 if lead else 0.5)) % 1
    if role == "arm":
        return 0 if side < 0 else 0.5
    return 0


def gait_sample(role, side, lead, t, phase, speed, height):
    out = {"pitch": 0.0, "roll": 0.0, "yaw": 0.0, "dy": 0.0, "dz": 0.0, "fwd": 0.0}
    if role not in GAIT_ROLES:
        return out
    wi, ww, wr = weights(speed)
    u = phase / (2 * math.pi) + gait_offset(role, side, lead)
    p = r = y = f = 0.0
    for name, tt, k in (("idle", t, wi), ("walk", u, ww), ("run", u, wr)):
        if k > 1e-4:
            s = cycle_sample(name, role, side, tt)
            p += s["pitch"] * k
            r += s["roll"] * k
            y += s["yaw"] * k
            f += s["fwd"] * k
    out["pitch"] = clamp(p, -MAX_ANGLE, MAX_ANGLE)
    out["roll"] = clamp(r, -MAX_ANGLE, MAX_ANGLE)
    out["yaw"] = clamp(y, -MAX_ANGLE, MAX_ANGLE)
    out["fwd"] = clamp(f * height, 0, PECK)
    return out


def gait_bob(t, phase, speed):
    wi, ww, wr = weights(speed)
    u = phase / (2 * math.pi)
    b = cycle_sample("idle", "root", 1, t)["bob"] * wi + cycle_sample("walk", "root", 1, u)["bob"] * ww + \
        cycle_sample("run", "root", 1, u)["bob"] * wr
    return clamp(b, 0, MAX_BOB)


def step_rate(s):
    return 5 + 7 * clamp(s, 0, 1)


def air_weight(t):
    return ease(max(0.0, t) / 0.4)


def action_weight(phase, p):
    p = clamp(p, 0, 1)
    if phase == "land":
        return 1 - ease(clamp((p - 0.5) / 0.5, 0, 1))
    return 1.0


def sample_action(role, ctx):
    """LowPolyPose.sampleAction for a Ground dino, phases air (direct) and land."""
    ph, p = ctx["phase"], clamp(ctx["p"], 0, 1)
    q = st = tk = 0.0
    if ph == "air":
        tk = 1.0
    elif ph == "land":
        d = ease(p / 0.25)
        tk = ctx["carry"] * (1 - d)
        q = d * (1 - ease((p - 0.25) / 0.75))
    aggr = 0.0
    L = 1 + aggr
    o = {"pitch": 0.0, "roll": 0.0, "yaw": 0.0, "dy": 0.0, "dz": 0.0, "fwd": 0.0}
    if role == "body":
        o["dy"] = -0.05 * q + 0.03 * st
        o["pitch"] = -0.05 * q + 0.10 * st + 0.02 * tk
        o["dz"] = -0.02 * st * L
    elif role in ("head", "neck"):
        o["dy"] = -0.02 * q
        o["pitch"] = 0.18 * st - 0.08 * tk
        o["dz"] = -0.03 * st * L
    elif role == "tail":
        o["pitch"] = 0.15 * q - 0.20 * st + 0.12 * tk
    elif role == "leg":
        o["pitch"] = 0.55 * q - 0.45 * st + 0.70 * tk
        o["dy"] = 0.01 * q
    elif role == "arm":
        o["pitch"] = 0.20 * q - 0.50 * st + 0.50 * tk
    for k in ("pitch", "roll", "yaw"):
        o[k] = clamp(o[k], -MAX_ANGLE, MAX_ANGLE)
    for k in ("dy", "dz"):
        o[k] = clamp(o[k], -0.08, 0.08)
    return o


FOLLOW = dict(stiffness=11, damping=0.45, tailYawPerTurn=0.06, headYawPerTurn=0.035, tailPitchPerRise=0.006,
              headPitchPerRise=-0.003, tailLandKick=0.03, headLandKick=-0.02, max=0.4)


def step_follow(f, dt, turn, vy, land):
    F = FOLLOW
    target = {"tailYaw": clamp(turn * F["tailYawPerTurn"], -F["max"], F["max"]),
              "headYaw": clamp(turn * F["headYawPerTurn"], -F["max"], F["max"]),
              "tailPitch": clamp(vy * F["tailPitchPerRise"], -F["max"], F["max"]),
              "headPitch": clamp(vy * F["headPitchPerRise"], -F["max"], F["max"])}
    if land > 0:
        f["tailPitchV"] += land * F["tailLandKick"]
        f["headPitchV"] += land * F["headLandKick"]
    left = clamp(dt, 0, 0.25)
    k, c = F["stiffness"] ** 2, 2 * F["damping"] * F["stiffness"]
    while left > 1e-6:
        h = min(left, 1 / 60)
        left -= h
        for ch in ("tailYaw", "tailPitch", "headYaw", "headPitch"):
            v = f[ch + "V"] + (k * (target[ch] - f[ch]) - c * f[ch + "V"]) * h
            f[ch + "V"] = v
            f[ch] = clamp(f[ch] + v * h, -F["max"], F["max"])


def role_of(name):
    n = name.lower()
    for key, role in (("head", "head"), ("tail", "tail"), ("arm", "arm"), ("leg", "leg"), ("body", "body")):
        if key in n:
            return role
    return "body"


def simulate(parts_info, n_frames):
    """parts_info: {name: (role, side, lead)}. Returns per frame: {"t", "seg", "bob" (game studs), "lift" (game studs), name: pose}."""
    H = GAME_HEIGHT
    sim_dt = 1 / 60
    st = dict(speed=0.0, phase=0.0, act=None, actAt=0.0, carry=0.0, landFrom=1.0, clip=None, clipAt=0.0, hops={},
              follow={k: 0.0 for k in ("tailYaw", "tailYawV", "tailPitch", "tailPitchV", "headYaw", "headYawV", "headPitch", "headPitchV")},
              inAir=False, fallVy=0.0, wasAir=False)
    frames = []
    t = 0.0
    t_land = T_JUMP + 2 * JUMP_V / GRAVITY
    total_steps = n_frames * 2
    for step in range(total_steps + 1):
        seg = segment(t)
        target = SPEED_WALK if seg == "walk" else SPEED_RUN if seg == "run" else 0.0
        s01 = 0.0 if target < 0.06 else target
        st["speed"] += (s01 - st["speed"]) * min(1, sim_dt * 8)
        st["phase"] = (st["phase"] + sim_dt * step_rate(st["speed"]) * (1 if st["speed"] > 0.01 else 0)) % (2 * math.pi * 8)
        # humanoid state: a standing jump at T_JUMP, touch-down at t_land
        in_air = T_JUMP <= t < t_land
        vy = JUMP_V - GRAVITY * (t - T_JUMP) if in_air else 0.0
        height_up = (JUMP_V * (t - T_JUMP) - 0.5 * GRAVITY * (t - T_JUMP) ** 2) if in_air else 0.0
        if in_air and st["act"] is None:
            st["act"], st["actAt"] = "air", t
            st["hops"]["jump"] = t
        elif not in_air and st["act"] == "air":
            st["carry"] = 1.0
            st["landFrom"] = air_weight(t - st["actAt"])
            st["act"], st["actAt"] = "land", t
            st["hops"]["land"] = t
        elif st["act"] == "land" and t - st["actAt"] >= 0.30:
            st["act"] = None
        # clips (eat, happy) at their segment starts
        if seg == "eat" and st["clip"] is None and abs(t - T_EAT) < sim_dt:
            st["clip"], st["clipAt"] = "eat", t
        if seg == "happy" and abs(t - T_HAPPY) < sim_dt:
            st["clip"], st["clipAt"] = "happy", t
        if st["clip"] and t - st["clipAt"] >= dino_clips.CLIPS[st["clip"]]["length"]:
            st["clip"] = None
        for name in list(st["hops"]):
            if t - st["hops"][name] >= dino_clips.CLIPS[name]["length"]:
                del st["hops"][name]
        land_speed = max(0.0, -st["fallVy"]) if st["wasAir"] and not in_air else 0.0
        if in_air:
            st["fallVy"] = vy
        st["wasAir"] = in_air
        step_follow(st["follow"], sim_dt, 0.0, vy if in_air else 0.0, land_speed)
        if step % 2 == 0:
            frames.append(pose_frame(st, t, seg, parts_info, H, height_up))
        t += sim_dt
    return frames[:n_frames]


def pose_frame(st, t, seg, parts_info, H, height_up):
    phase = st["act"]
    k, ctx = 0.0, None
    if phase:
        el = t - st["actAt"]
        dur = 0.30 if phase == "land" else 0.0
        p = clamp(el / dur, 0, 1) if dur > 0 else 0.0
        ctx = {"phase": phase, "p": p, "carry": st["carry"]}
        k = air_weight(el) if phase == "air" else st["landFrom"] * action_weight("land", p)
    bob = gait_bob(t, st["phase"], st["speed"]) * H
    cw = 1.0 if st["clip"] else 0.0
    clip_t = t - st["clipAt"] if cw else 0.0
    if cw:
        bob += clip_sample(st["clip"], "root", 1, clip_t)["bob"] * H * cw
    fr = {"t": round(t, 4), "seg": seg, "bob": bob, "lift": height_up * JUMP_SCALE, "speed": st["speed"],
          "clip": st["clip"], "act": phase}
    for name, (role, side, lead) in parts_info.items():
        out = gait_sample(role, side, lead, t, st["phase"], st["speed"], H) if role in GAIT_ROLES else \
            {"pitch": 0.0, "roll": 0.0, "yaw": 0.0, "dy": 0.0, "dz": 0.0, "fwd": 0.0}
        if phase:
            a = sample_action(role, ctx)
            for key in out:
                out[key] += (a[key] - out[key]) * k
        if cw:
            c = clip_sample(st["clip"], role, side, clip_t)
            out["pitch"] += c["pitch"] * cw
            out["yaw"] += c["yaw"] * cw
            out["roll"] += c["roll"] * cw
            out["fwd"] += c["fwd"] * H * cw
        for hop, at in st["hops"].items():
            c = clip_sample(hop, role, side, t - at)
            out["pitch"] += c["pitch"]
            out["yaw"] += c["yaw"]
            out["roll"] += c["roll"]
        f = st["follow"]
        if role == "tail":
            out["yaw"] += f["tailYaw"]
            out["pitch"] += f["tailPitch"]
        elif role in ("head", "neck"):
            out["yaw"] += f["headYaw"]
            out["pitch"] += f["headPitch"]
        fr[name] = out
    return fr


# ------------------------------------------------------------------ outer: run Blender per model, then compose
if not INSIDE:
    def run_blender(blend, label, out_dir, n_frames):
        cmd = [os.environ.get("BLENDER_EXE", BLENDER), "-b", "--factory-startup", "--python", os.path.abspath(__file__), "--",
               "--inside", "--model", os.path.abspath(blend), "--label", label, "--out", os.path.abspath(out_dir), "--frames", str(n_frames),
               "--size", str(SIZE), "--game-height", str(GAME_HEIGHT), "--jump-scale", str(JUMP_SCALE)]
        flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        res = subprocess.run(cmd, creationflags=flags, capture_output=True, text=True)
        for line in (res.stdout or "").splitlines():
            if line.startswith(("PREVIEW", "ERROR", "Traceback", "  File")) or "Error" in line:
                print(line)
        if res.returncode:
            print((res.stderr or "")[-2000:])
            sys.exit(res.returncode)

    def slug(label):
        return "".join(c if c.isalnum() else "-" for c in label.lower()).strip("-")

    def compose(out_dir, labels, n_frames, mp4, sheet):
        from PIL import Image, ImageDraw, ImageFont
        metrics = [json.load(open(os.path.join(out_dir, slug(l), "metrics.json"))) for l in labels]
        views = metrics[0]["views"]
        try:
            font = ImageFont.truetype("arial.ttf", 15)
            big = ImageFont.truetype("arialbd.ttf", 17)
        except OSError:
            font = big = ImageFont.load_default()
        W, Hh, top = SIZE, SIZE, 26
        comp_dir = os.path.join(out_dir, "compose")
        os.makedirs(comp_dir, exist_ok=True)
        for i in range(n_frames):
            img = Image.new("RGB", (W * len(labels), top + Hh * len(views) + 22), (40, 44, 52))
            d = ImageDraw.Draw(img)
            for c, (label, m) in enumerate(zip(labels, metrics)):
                d.text((c * W + 8, 4), label, fill=(255, 255, 255), font=big)
                for r, view in enumerate(views):
                    fr = Image.open(os.path.join(out_dir, slug(label), view, "f%04d.png" % (i + 1))).convert("RGB")
                    img.paste(fr, (c * W, top + r * Hh))
                f = m["frames"][i]
                worst = max(f["reveal"].values())
                col = (255, 120, 120) if worst > 0.10 else (255, 220, 120) if worst > 0.04 else (170, 230, 170)
                d.text((c * W + 8, top + Hh * len(views) + 3), "gap %.2f  drift %.2f  floor %.2f studs" % (
                    worst, max(f["drift"].values()), f["floor"]), fill=col, font=font)
            f0 = metrics[0]["frames"][i]
            tag = "%s%s  t=%.2fs  frame %d" % (f0["seg"], (" +" + f0["clip"]) if f0["clip"] else (" (" + f0["act"] + ")" if f0["act"] else ""),
                                              f0["t"], i + 1)
            d.text((W * len(labels) - 8 - d.textlength(tag, font=font), 6), tag, fill=(200, 200, 200), font=font)
            img.save(os.path.join(comp_dir, "c%04d.png" % (i + 1)))
        if mp4:
            os.makedirs(os.path.dirname(os.path.abspath(mp4)), exist_ok=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(comp_dir, "c%04d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30", "-preset", "slow", "-movflags", "+faststart", mp4],
                           check=True, creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
            print("PREVIEW mp4 %s (%.2f MB)" % (mp4, os.path.getsize(mp4) / 1e6))
        if sheet:
            picks = pick_frames(metrics, n_frames)
            thumbs = [Image.open(os.path.join(comp_dir, "c%04d.png" % (i + 1))) for i in picks]
            tw, th = thumbs[0].size
            scale = 0.5
            cols = 4
            rows = (len(thumbs) + cols - 1) // cols
            sh = Image.new("RGB", (int(tw * scale) * cols, int(th * scale) * rows), (30, 30, 30))
            for j, im in enumerate(thumbs):
                sh.paste(im.resize((int(tw * scale), int(th * scale)), Image.LANCZOS), ((j % cols) * int(tw * scale), (j // cols) * int(th * scale)))
            os.makedirs(os.path.dirname(os.path.abspath(sheet)), exist_ok=True)
            sh.save(sheet, optimize=True)
            print("PREVIEW contact sheet %s frames %s" % (sheet, [p + 1 for p in picks]))
        for label, m in zip(labels, metrics):
            summarize(label, m)

    def pick_frames(metrics, n):
        """One frame per segment where the first model's worst gap peaks, plus the worst frame of each model overall."""
        picks = []
        for seg in ("idle", "walk", "run", "stop", "jump", "eat", "happy"):
            idx = [i for i, f in enumerate(metrics[0]["frames"]) if f["seg"] == seg]
            if idx:
                picks.append(max(idx, key=lambda i: max(max(m["frames"][i]["reveal"].values()) for m in metrics)))
        for m in metrics:
            w = max(range(n), key=lambda i: max(m["frames"][i]["reveal"].values()))
            if w not in picks:
                picks.append(w)
        return sorted(picks)[:8]

    def summarize(label, m):
        print("PREVIEW === %s (pivots in Blender coords: %s)" % (label, {k: [round(x, 3) for x in v] for k, v in m["pivots"].items()}))
        for j in JOINTS:
            rv = [(f["reveal"][j], i + 1) for i, f in enumerate(m["frames"])]
            dr = [(f["drift"][j], i + 1) for i, f in enumerate(m["frames"])]
            r, ri = max(rv)
            dmax, di = max(dr)
            over = [i for v, i in rv if v > 0.05]
            print("PREVIEW %-5s gap max %.3f (frame %d)  drift max %.3f (frame %d)  frames with gap > 0.05: %d%s" % (
                j, r, ri, dmax, di, len(over), (" (%d-%d)" % (over[0], over[-1])) if over else ""))
        fl = [(f["floor"], i + 1) for i, f in enumerate(m["frames"])]
        print("PREVIEW floor max %.3f studs (frame %d)" % max(fl))

    if __name__ == "__main__":
        blends, labels = args_all("--blend"), args_all("--label")
        out_dir = os.path.abspath(arg("--out", os.path.join(ROOT, "build", "anim-preview")))
        n_frames = int(arg("--frames", str(int(T_END * FPS))))
        if "--compose-only" not in ARGS:
            for b, l in zip(blends, labels):
                run_blender(b, l, os.path.join(out_dir, slug(l)), n_frames)
        compose(out_dir, labels, n_frames, arg("--mp4"), arg("--sheet"))
    raise SystemExit(0)

# ------------------------------------------------------------------ inside Blender
from mathutils import Vector, Matrix  # type: ignore  # noqa: E402
from mathutils.bvhtree import BVHTree  # type: ignore  # noqa: E402

C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # Roblox vector -> Blender vector


def r2b(v):
    return C @ Vector(v)


def pivot_roblox(role, size):
    """LowPolyAnimator.pivotFor (Roblox part frame, relative to the box centre)."""
    sx, sy, sz = size
    if role == "head" or role == "neck":
        return (0, -sy / 2, sz / 2)
    if role == "tail":
        return (0, 0, -sz / 2)
    if role in ("arm", "leg"):
        return (0, sy / 2, 0)
    return (0, 0, 0)


def angles_matrix(pitch, yaw, roll):
    """CFrame.Angles(pitch, yaw, roll) = Rx * Ry * Rz in Roblox axes, as a Blender 4x4."""
    R = Matrix.Rotation(pitch, 3, "X") @ Matrix.Rotation(yaw, 3, "Y") @ Matrix.Rotation(roll, 3, "Z")
    return (C @ R @ C.transposed()).to_4x4()


def main():
    model = arg("--model")
    label = arg("--label")
    out = arg("--out")
    n_frames = int(arg("--frames"))
    bpy.ops.wm.open_mainfile(filepath=model)
    sc = bpy.context.scene
    for ob in list(sc.objects):
        if ob.name not in PARTS:
            bpy.data.objects.remove(ob)
    obs = {n: sc.objects[n] for n in PARTS}
    for ob in obs.values():
        ob.animation_data_clear()
    rest = {n: ob.matrix_world.copy() for n, ob in obs.items()}
    world = {n: [rest[n] @ v.co for v in ob.data.vertices] for n, ob in obs.items()}
    lo_all = [min(w[i] for n in PARTS for w in world[n]) for i in range(3)]
    hi_all = [max(w[i] for n in PARTS for w in world[n]) for i in range(3)]
    model_h = hi_all[2] - lo_all[2]
    k = GAME_HEIGHT / model_h  # game studs per model unit
    box_c = Vector([(a + b) / 2 for a, b in zip(lo_all, hi_all)])
    info, piv = {}, {}
    for n in PARTS:
        lo = Vector([min(w[i] for w in world[n]) for i in range(3)])
        hi = Vector([max(w[i] for w in world[n]) for i in range(3)])
        c = (lo + hi) / 2
        size_r = (hi.x - lo.x, hi.z - lo.z, hi.y - lo.y)  # Roblox X, Y, Z extents
        role = role_of(n)
        side = -1 if c.x < box_c.x else 1          # LPSide: part.Position.X < box.X
        lead = c.y > box_c.y                       # LPLead: part Z < body Z (Roblox -Z = Blender +Y)
        info[n] = (role, side, lead)
        piv[n] = c + r2b(pivot_roblox(role, size_r))
        print("PREVIEW %s %-5s role %-4s side %+d lead %-5s box lo %s hi %s pivot %s" % (label, n, role, side, lead, tuple(round(x, 3) for x in lo),
              tuple(round(x, 3) for x in hi), tuple(round(x, 3) for x in piv[n])))
    frames = simulate(info, n_frames)

    # ---- metric set-up: surface samples hidden inside / on the neighbour at rest
    def bvh_of(n):
        return BVHTree.FromPolygons([tuple(w) for w in world[n]], [tuple(p.vertices) for p in obs[n].data.polygons])
    bvh = {n: bvh_of(n) for n in PARTS}

    def samples(n):
        pts = list(world[n])
        for p in obs[n].data.polygons:
            pts.append(sum((world[n][i] for i in p.vertices), Vector()) / len(p.vertices))
        return pts

    RAYS = (Vector((0.31, 0.52, 0.80)).normalized(), Vector((-0.71, 0.13, -0.69)).normalized(), Vector((0.22, -0.95, 0.21)).normalized())

    def crossings(tree, p, d):
        n, o = 0, p.copy()
        for _ in range(64):
            hit = tree.ray_cast(o, d)
            if hit[0] is None:
                return n
            n += 1
            o = hit[0] + d * 1e-4
        return n

    def outside(tree, p):
        """Signed distance to a closed part: > 0 outside, < 0 inside (ray parity, majority of three rays)."""
        loc, _, _, dist = tree.find_nearest(p)
        if loc is None:
            return 1e9
        ins = sum(crossings(tree, p, d) % 2 for d in RAYS) >= 2
        return -dist if ins else dist

    TOL = 0.012  # model units: "on the surface"

    def gap(tree, p):
        """How far p sticks out of a closed part (0 when inside or on its surface)."""
        loc, _, _, dist = tree.find_nearest(p)
        if loc is None or dist <= TOL:
            return 0.0
        return 0.0 if sum(crossings(tree, p, d) % 2 for d in RAYS) >= 2 else dist
    # cut faces: faces tagged CAP (5) by the builders (the flat caps that close a part where it was cut / where it joins); tag 6 = the
    # Blender model's 1 cm pivot anchors (buried, skipped). Seam = surface of the child on / in the body at rest (the visible join line).
    caps = {}
    for n in PARTS:
        me = obs[n].data
        attr = me.attributes.get("tag")
        lst = []
        if attr is not None and attr.domain == "FACE":
            for poly in me.polygons:
                if attr.data[poly.index].value == 5:
                    cen = sum((world[n][i] for i in poly.vertices), Vector()) / len(poly.vertices)
                    lst.append((cen, poly.area * (rest[n].to_scale()[0] ** 2)))
        caps[n] = lst
    seam = {}
    for j in JOINTS:
        seam[j] = [p for p in samples(j) if abs(outside(bvh["Body"], p)) < TOL]
    owner = {}
    for n in PARTS:   # which joint a cap belongs to: a child's own caps -> its joint; a body cap -> the nearest child at rest
        for i, (c, _) in enumerate(caps[n]):
            owner[(n, i)] = n if n != "Body" else min(JOINTS, key=lambda j: bvh[j].find_nearest(c)[3])
    for n in PARTS:
        print("PREVIEW %s %-5s cut-face samples %d (area %.3f)  seam samples %d" % (label, n, len(caps[n]), sum(a for _, a in caps[n]),
              len(seam.get(n, []))))
    joint_pt = {}
    for j in JOINTS:   # the real joint: centre of the child's cut face if it has one, else of its seam on the body
        pts = [c for c, _ in caps[j]] or seam[j]
        joint_pt[j] = sum(pts, Vector()) / max(1, len(pts))
    pivot_err = {j: round((piv[j] - joint_pt[j]).length * k, 3) for j in JOINTS}
    print("PREVIEW %s game pivot -> real joint distance (studs): %s" % (label, pivot_err))
    floor_rest = lo_all[2]

    def part_matrix(n, fr):
        o = fr[n]
        bob_m = (fr["bob"]) / k + fr["lift"] / k
        shift = Vector((0, o["fwd"] / k, bob_m))     # Roblox (0, bob, -fwd) -> Blender (0, fwd, bob)
        d = r2b((0, o["dy"] * model_h, o["dz"] * model_h))
        P = piv[n]
        return Matrix.Translation(shift) @ Matrix.Translation(P) @ angles_matrix(o["pitch"], o["yaw"], o["roll"]) @ \
            Matrix.Translation(-P) @ Matrix.Translation(d)

    # a cut face that already shows at rest (a decimation crack, or a mislabelled face) is not the animation's fault: measure the change
    rest_gap = {(n, i): min(gap(bvh[m], c) for m in PARTS if m != n) for n in PARTS for i, (c, _) in enumerate(caps[n])}
    rest_show = {j: 0.0 for j in JOINTS}
    for (n, i), g in rest_gap.items():
        rest_show[owner[(n, i)]] = max(rest_show[owner[(n, i)]], g * k)
    print("PREVIEW %s cut faces already showing at rest (studs): %s" % (label, {j: round(v, 3) for j, v in rest_show.items()}))
    mframes = []
    for fr in frames:
        M = {n: part_matrix(n, fr) for n in PARTS}
        inv = {n: M[n].inverted() for n in PARTS}
        cut, area, drift = {j: 0.0 for j in JOINTS}, {j: 0.0 for j in JOINTS}, {}
        for n in PARTS:
            for i, (c, ar) in enumerate(caps[n]):
                w = M[n] @ c
                g = min(gap(bvh[m], inv[m] @ w) for m in PARTS if m != n)   # sticks out of every other part = this cut face shows
                g = g - rest_gap[(n, i)] if g > rest_gap[(n, i)] + 1e-4 else 0.0
                j = owner[(n, i)]
                if g > 0:
                    cut[j] = max(cut[j], g)
                    area[j] += ar
        for j in JOINTS:
            rel = inv["Body"] @ M[j]
            drift[j] = round(((rel @ joint_pt[j]) - joint_pt[j]).length * k, 4)
        low = min((M[n] @ w).z for n in PARTS for w in world[n]) - fr["lift"] / k
        mframes.append({"t": fr["t"], "seg": fr["seg"], "clip": fr["clip"], "act": fr["act"],
                        "reveal": {j: round(cut[j] * k, 4) for j in JOINTS}, "cut_area": {j: round(area[j] * k * k, 4) for j in JOINTS},
                        "drift": drift, "floor": round(max(0.0, floor_rest - low) * k, 4)})

    # ---- render: Workbench, textured, studio light, ground plane
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "TEXTURE"
    sh.show_cavity = False
    sh.show_shadows = True
    sh.shadow_intensity = 0.35
    sc.render.resolution_x = SIZE
    sc.render.resolution_y = SIZE
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.color = (0.62, 0.68, 0.76)
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, floor_rest - 0.002))
    ground = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.diffuse_color = (0.80, 0.80, 0.78, 1)
    ground.data.materials.append(gm)
    cams = {}
    for view, direction in (("side", (1, 0, 0)), ("q34", (math.sin(math.radians(38)), math.cos(math.radians(38)), 0))):
        cd = bpy.data.cameras.new(view)
        cd.type = "ORTHO"
        cd.ortho_scale = 4.3
        cam = bpy.data.objects.new("cam_" + view, cd)
        sc.collection.objects.link(cam)
        dvec = Vector(direction).normalized()
        dvec.z += 0.12
        dvec.normalize()
        target = Vector((0, 0.0, 1.95))
        cam.location = target + dvec * 20
        cam.rotation_euler = (-dvec).to_track_quat("-Z", "Y").to_euler()
        cams[view] = cam
    for i, fr in enumerate(frames):
        for n in PARTS:
            obs[n].matrix_world = part_matrix(n, fr) @ rest[n]
        for view, cam in cams.items():
            sc.camera = cam
            d = os.path.join(out, view)
            os.makedirs(d, exist_ok=True)
            sc.render.filepath = os.path.join(d, "f%04d.png" % (i + 1))
            bpy.ops.render.render(write_still=True)
    json.dump({"label": label, "views": list(cams), "k": k, "pivots": {n: list(piv[n]) for n in PARTS}, "pivot_err": pivot_err,
               "frames": mframes}, open(os.path.join(out, "metrics.json"), "w"), indent=0)
    print("PREVIEW %s rendered %d frames x %d views" % (label, len(frames), len(cams)))


if "--inside" in ARGS:
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        print("ERROR preview failed")
        sys.exit(1)
