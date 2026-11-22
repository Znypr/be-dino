"""Compy fitted to the owner-approved sheet's silhouettes (BD-1291 "Try silhouette rebuild"). Headless Blender, CPU only.

  python tools/blender/build_compy_silhouette.py --round R1 --note "first fit"     # build + silhouette gate (IoU logged)
  python tools/blender/build_compy_silhouette.py --round R6 --final                # + compare renders, overlays, .blend saved

Method (visual hull per part, then controlled low poly):
  1. the sheet (docs/evidence/2026-11-22-dino-ranking/compy-sheet-v1.jpg) is segmented per view (non-grey = dino) and shrunk by its
     black outline (6 px of ~395); front and side views are calibrated to 3.0 studs tall (feet z 0, model faces +Y, +X = right).
  2. every part is a LOFT of cross-section rings (10-16 verts): WIDTH (x) at a ring comes from the front-view mask, DEPTH / HEIGHT from
     the side-view mask, inside a hand-set window per part (the views overlap: arm over chest, thigh over belly, tail behind the hips);
     torso / legs / tail / arms rings are superellipses, the head rings follow the front view's head outline (top and jaw chamfered) so
     each ring band is a broad flat plane; near-coplanar faces are then merged (planes, not noise) and 1-segment bevels soften the
     main silhouette edges.
  3. gate: black silhouettes of the model from front / side / 3/4 (3/4 yaw and tilt swept, best kept) against the sheet masks, IoU at
     120 and 512 px, written to docs/evidence/2026-11-22-compy-silhouette/iou.json per round.
Rigid parts for LowPolyAnimator (pivot from each part's bounding box): joints are buried, flat joint caps tagged 5 (the preview's
cut-face metric), hidden pivot anchors (tag 6) put the limb boxes' top centre on the shoulder / hip, the tail box's front centre on
the tail root. Untextured: flat materials (lime, cream belly, dark claws, black glossy eyes) for the owner's shape OK.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
SHEET = os.path.join(ROOT, "docs", "evidence", "2026-11-22-dino-ranking", "compy-sheet-v1.jpg")
EVID = os.path.join(ROOT, "docs", "evidence", "2026-11-22-compy-silhouette")
BLEND_OUT = os.path.join(ROOT, "assets", "blender", "creatures", "Compy_Silhouette.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


WORK = os.path.abspath(arg("--work", os.path.join(tempfile.gettempdir(), "compy-silhouette")))
VIEWS = {"front": (121, 313), "q34": (390, 710), "side": (758, 1157), "back": (1242, 1424)}   # sheet x ranges, top row
OUTLINE_PX = 6
Q34_YAWS = (25, 30, 35, 40, 45, 50, 55)      # degrees from the front toward the right side
Q34_TILTS = (0, 8, 15)                   # camera elevation, degrees

try:
    import bpy  # type: ignore
    INSIDE = True
except ImportError:
    INSIDE = False


# ====================================================================================================== outside Blender
if not INSIDE:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from scipy import ndimage as nd

    def sheet_masks():
        """Per view: the dino's mask (outline shrunk), cropped to its box."""
        a = np.asarray(Image.open(arg("--sheet", SHEET)).convert("RGB")).astype(int)
        sat = a.max(-1) - a.min(-1)
        lum = a.mean(-1)
        fg = ~((sat < 18) & (lum > 110) & (lum < 215))
        fg[445:] = False                                   # top row only (labels below)
        fg = nd.binary_opening(fg, iterations=1)
        lab, _ = nd.label(fg)
        out = {}
        for v, (x0, x1) in VIEWS.items():
            ids, counts = np.unique(lab[:, x0:x1], return_counts=True)
            keep = max((c, i) for c, i in zip(counts, ids) if i)[1]
            m = lab == keep
            holes = nd.binary_fill_holes(m) & ~m           # small holes = the eyes' white highlights; big ones = real gaps
            hl, nh = nd.label(holes)
            if nh:
                area = nd.sum(holes, hl, range(1, nh + 1))
                m |= np.isin(hl, 1 + np.flatnonzero(area < 600))
            m = nd.binary_erosion(m, iterations=OUTLINE_PX)
            ys, xs = np.nonzero(m)
            out[v] = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        return out

    def font(sz, bold=False):
        try:
            return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", sz)
        except OSError:
            return ImageFont.load_default()

    def crop(m):
        ys, xs = np.nonzero(m)
        return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

    def at_height(m, h):
        w = max(1, int(round(m.shape[1] * h / m.shape[0])))
        im = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        return np.asarray(im) >= 128

    def iou_pair(sheet, ours, h):
        """Both masks to height h, bottoms aligned, ours slid sideways (+-6 % of the width) to the best fit."""
        a, b = at_height(sheet, h), at_height(ours, h)
        pad = int(0.1 * max(a.shape[1], b.shape[1])) + 2
        W = max(a.shape[1], b.shape[1]) + 2 * pad
        A = np.zeros((h, W), bool)
        ax = (W - a.shape[1]) // 2
        A[:, ax:ax + a.shape[1]] = a
        best = (-1, 0, None)
        rng = int(0.06 * a.shape[1]) + 1
        for s in range(-rng, rng + 1):
            B = np.zeros((h, W), bool)
            bx = (W - b.shape[1]) // 2 + s
            B[:, bx:bx + b.shape[1]] = b
            i = (A & B).sum() / max(1, (A | B).sum())
            if i > best[0]:
                best = (i, s, B)
        return best[0], A, best[2]

    def gate(masks, round_name, note):
        res = {}
        sil = os.path.join(WORK, "sil")
        load = lambda n: crop(np.asarray(Image.open(os.path.join(sil, n + ".png")).convert("RGBA"))[..., 3] > 127)  # noqa: E731
        for v in ("front", "side"):
            ours = load(v)
            res[v] = {"iou120": round(iou_pair(masks[v], ours, 120)[0], 4), "iou512": round(iou_pair(masks[v], ours, 512)[0], 4)}
        best = None
        for yaw in Q34_YAWS:
            for tilt in Q34_TILTS:
                i = iou_pair(masks["q34"], load("q34_%d_%d" % (yaw, tilt)), 120)[0]
                if best is None or i > best[0]:
                    best = (i, yaw, tilt)
        ours = load("q34_%d_%d" % best[1:])
        res["q34"] = {"iou120": round(best[0], 4), "iou512": round(iou_pair(masks["q34"], ours, 512)[0], 4), "yaw": best[1], "tilt": best[2]}
        tris = json.load(open(os.path.join(WORK, "build.json")))
        entry = {"round": round_name, "note": note, "iou": res, "tris": tris["tris"], "total_tris": sum(tris["tris"].values()),
                 "head_to_torso_width": tris.get("head_to_torso_width")}
        os.makedirs(EVID, exist_ok=True)
        path = os.path.join(EVID, "iou.json")
        log = json.load(open(path)) if os.path.exists(path) else {"method": __doc__.split("Method")[1].split("Rigid")[0].strip(), "rounds": []}
        log["rounds"] = [r for r in log["rounds"] if r["round"] != round_name] + [entry]
        json.dump(log, open(path, "w"), indent=1)
        print("SIL round %s  front %.3f/%.3f  side %.3f/%.3f  q34 %.3f/%.3f (yaw %d tilt %d)  tris %d" % (
            round_name, res["front"]["iou120"], res["front"]["iou512"], res["side"]["iou120"], res["side"]["iou512"],
            res["q34"]["iou120"], res["q34"]["iou512"], best[1], best[2], entry["total_tris"]))
        return res

    def overlays(masks, res, out_png):
        sil = os.path.join(WORK, "sil")
        tiles = []
        for v in ("front", "q34", "side"):
            n = v if v != "q34" else "q34_%d_%d" % (res["q34"]["yaw"], res["q34"]["tilt"])
            ours = crop(np.asarray(Image.open(os.path.join(sil, n + ".png")).convert("RGBA"))[..., 3] > 127)
            i, A, B = iou_pair(masks[v], ours, 400)
            img = np.full(A.shape + (3,), 236, np.uint8)
            img[A & B] = (120, 190, 110)
            img[A & ~B] = (225, 70, 70)
            img[~A & B] = (70, 120, 235)
            t = Image.fromarray(img)
            d = ImageDraw.Draw(t)
            d.text((6, 4), "%s  IoU %.3f" % (v, i), fill=(20, 20, 20), font=font(16, True))
            tiles.append(t)
        W = sum(t.size[0] for t in tiles) + 10 * (len(tiles) + 1)
        sheet = Image.new("RGB", (W, 400 + 50), (250, 250, 250))
        x = 10
        for t in tiles:
            sheet.paste(t, (x, 10))
            x += t.size[0] + 10
        d = ImageDraw.Draw(sheet)
        d.text((10, 418), "green = sheet and model   red = sheet only (model too small)   blue = model only (too big)   (400 px tall)",
               fill=(40, 40, 40), font=font(14))
        sheet.save(out_png, optimize=True)
        print("SIL overlays", os.path.relpath(out_png, ROOT))

    def compare(res, out_png):
        """Sheet view | our studio render, front / 3/4 / side."""
        src = Image.open(arg("--sheet", SHEET)).convert("RGB")
        rows = []
        for v in ("front", "q34", "side"):
            x0, x1 = VIEWS[v]
            s = src.crop((x0 - 12, 25, x1 + 12, 445))
            n = v if v != "q34" else "q34"
            r = Image.open(os.path.join(WORK, "look", n + ".png")).convert("RGBA")
            bb = r.getbbox()
            r = r.crop(bb)
            h = 396
            r = r.resize((int(r.size[0] * h / r.size[1]), h), Image.LANCZOS)
            bg = Image.new("RGB", (r.size[0] + 24, 420), (171, 171, 171))
            al = np.zeros((420, r.size[0] + 24), bool)
            al[12:12 + h, 12:12 + r.size[0]] = np.asarray(r)[..., 3] > 100
            ring = nd.binary_dilation(al, iterations=int(round(0.017 * h)))   # outline like the sheet's (~7 px on 400)
            bg.paste((0, 0, 0), mask=Image.fromarray((ring * 255).astype(np.uint8)))
            bg.paste(r, (12, 12), r)
            rows.append((s, bg, v))
        W = max(a.size[0] + b.size[0] for a, b, _ in rows) + 30
        H = sum(420 + 30 for _ in rows)
        img = Image.new("RGB", (W, H), (60, 64, 70))
        d = ImageDraw.Draw(img)
        y = 0
        for s, b, v in rows:
            d.text((8, y + 6), "sheet (%s)" % v, fill=(255, 255, 255), font=font(15, True))
            d.text((s.size[0] + 20, y + 6), "silhouette rebuild (%s)" % v, fill=(255, 255, 255), font=font(15, True))
            img.paste(s, (0, y + 28))
            img.paste(b, (s.size[0] + 20, y + 28))
            y += 450
        img = img.crop((0, 0, W, y))
        img.save(out_png, optimize=True)
        print("SIL compare", os.path.relpath(out_png, ROOT))

    if __name__ == "__main__":
        os.makedirs(WORK, exist_ok=True)
        masks = sheet_masks()
        np.savez_compressed(os.path.join(WORK, "masks.npz"), **masks)
        for v, m in masks.items():
            print("SIL mask %-5s %dx%d px" % (v, m.shape[1], m.shape[0]))
        cmd = [os.environ.get("BLENDER_EXE", BLENDER), "-b", "--factory-startup", "--python", os.path.abspath(__file__), "--",
               "--work", WORK] + (["--final", "--q34", arg("--q34", "q34_50_8")] if "--final" in ARGS else [])
        r = subprocess.run(cmd, creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0), capture_output=True, text=True)
        for line in (r.stdout or "").splitlines():
            if line.startswith(("SIL", "ERROR", "Traceback", "  File")) or "Error" in line:
                print(line)
        if r.returncode:
            print((r.stderr or "")[-2000:])
            sys.exit(r.returncode)
        res = gate(masks, arg("--round", "dev"), arg("--note", ""))
        os.makedirs(EVID, exist_ok=True)
        sfx = arg("--suffix", "")          # r2 outputs: --suffix -r2 (keeps the first round's pictures)
        overlays(masks, res, os.path.join(EVID if "--final" in ARGS else WORK, "silhouette-overlays%s.png" % sfx))
        if "--final" in ARGS:
            compare(res, os.path.join(EVID, "compare-sheet%s.png" % sfx))
    raise SystemExit(0)


# ====================================================================================================== inside Blender
import bmesh  # type: ignore  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, Matrix  # type: ignore  # noqa: E402
from mathutils.bvhtree import BVHTree  # type: ignore  # noqa: E402

sys.path.insert(0, HERE)
import build_compy_v3 as v3  # noqa: E402  (disc, shell, finish_shells, pivot_for, set_origin, tris_of, activate)

V = Vector
PARTS = ("Body", "Head", "Tail", "ArmL", "ArmR", "LegL", "LegR")
CAP_TAG, ANCHOR_TAG = 5, 6
TAG_EYE, TAG_WHITE, TAG_CLAW, TAG_NOSTRIL = 1, 2, 3, 4


def hexlin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


PALETTE = {"lime": "#72DF18", "cream": "#F3E8BB", "claw": "#4F5148", "eye": "#080A0B", "white": "#FFFFFF"}


# ------------------------------------------------------------------ the sheet masks in model units
class View:
    """A view mask: rows top -> bottom = z 3.0 -> 0.0; columns = h (x for the front, y for the side), origin at `c0` px."""

    def __init__(self, m, c0=None):
        self.m = m
        self.H, self.W = m.shape
        self.s = (self.H - 1) / 3.0
        if c0 is None:   # front: the mask's own centre line (column centroid of the head + legs)
            xs = np.nonzero(m)[1]
            c0 = float(xs.mean())
        self.c0 = c0

    def runs(self, line):
        idx = np.flatnonzero(np.diff(np.concatenate(([0], line.astype(np.int8), [0]))))
        return [(idx[i], idx[i + 1] - 1) for i in range(0, len(idx), 2)]

    def row_run(self, z, ref, lo=-9.0, hi=9.0):
        """(h0, h1) of the run in the row at height z that holds `ref` (else the nearest), clipped to [lo, hi]; median of 5 rows."""
        got = []
        for dr in (-4, -2, 0, 2, 4):
            r = int(round((self.H - 1) - z * self.s)) + dr
            if not 0 <= r < self.H:
                continue
            rr = [((a - self.c0) / self.s, (b + 1 - self.c0) / self.s) for a, b in self.runs(self.m[r])]
            rr = [(max(a, lo), min(b, hi)) for a, b in rr if min(b, hi) > max(a, lo)]
            if rr:
                got.append(min(rr, key=lambda ab: 0 if ab[0] <= ref <= ab[1] else min(abs(ab[0] - ref), abs(ab[1] - ref))))
        if not got:
            return None
        return float(np.median([g[0] for g in got])), float(np.median([g[1] for g in got]))

    def col_run(self, h, ref, lo=-9.0, hi=9.0):
        """(z0, z1) of the run in the column at h that holds height `ref`, clipped to [lo, hi]; median of 5 columns."""
        got = []
        for dc in (-4, -2, 0, 2, 4):
            c = int(round(self.c0 + h * self.s)) + dc
            if not 0 <= c < self.W:
                continue
            rr = [((self.H - 1 - b) / self.s, (self.H - a) / self.s) for a, b in self.runs(self.m[:, c])]
            rr = [(max(a, lo), min(b, hi)) for a, b in rr if min(b, hi) > max(a, lo)]
            if rr:
                got.append(min(rr, key=lambda ab: 0 if ab[0] <= ref <= ab[1] else min(abs(ab[0] - ref), abs(ab[1] - ref))))
        if not got:
            return None
        return float(np.median([g[0] for g in got])), float(np.median([g[1] for g in got]))

    def extent(self, zlo, zhi):
        """Min and max h of the mask between two heights."""
        r0, r1 = int((self.H - 1) - zhi * self.s), int((self.H - 1) - zlo * self.s)
        cols = np.flatnonzero(self.m[max(0, r0):r1 + 1].any(0))
        return (cols[0] - self.c0) / self.s, (cols[-1] + 1 - self.c0) / self.s


def lerp_table(tab, t):
    """Piecewise linear over [(t, value), ...]."""
    if t <= tab[0][0]:
        return tab[0][1]
    for (a, va), (b, vb) in zip(tab, tab[1:]):
        if t <= b:
            return va + (vb - va) * (t - a) / (b - a)
    return tab[-1][1]


# ------------------------------------------------------------------ ring / loft kit
def superellipse_ring(c, u, v, a, b, n=2.5, N=16, phase=None):
    """Ring in the plane (u, v) round c: half sizes a (along u), b (along v), exponent n (2 = ellipse, > 2 = rounder box)."""
    phase = math.pi / N if phase is None else phase
    pts = []
    for k in range(N):
        t = phase + 2 * math.pi * k / N
        ct, st = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(ct) ** (2 / n), ct)
        y = b * math.copysign(abs(st) ** (2 / n), st)
        pts.append(c + u * x + v * y)
    return pts


def loft(bm, tag, rings, start_tag=0, end_tag=0, end_apex=None):
    """Quads between consecutive rings; the first ring capped flat (start_tag), the last capped flat (end_tag) or closed on an apex."""
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vr, vr[1:]):
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((a[j], a[k], b[k], b[j]))[tag] = 0
    f = bm.faces.new(vr[0][::-1])
    f[tag] = start_tag
    if end_apex is not None:
        ap = bm.verts.new(end_apex)
        for j in range(n):
            bm.faces.new((vr[-1][j], vr[-1][(j + 1) % n], ap))[tag] = 0
    else:
        bm.faces.new(vr[-1])[tag] = end_tag


def new_bm():
    bm = bmesh.new()
    return bm, bm.faces.layers.int.new("tag")


def finish(name, bm, dissolve_deg=4.0, bevel=0.0):
    """Normals out, merge near-coplanar faces into planes (caps keep their tag), triangulate, optional 1-segment bevel."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    tag = bm.faces.layers.int.get("tag")
    if dissolve_deg > 0:
        soft = [e for e in bm.edges if all(f[tag] == 0 for f in e.link_faces)]
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(dissolve_deg), use_dissolve_boundaries=False,
                                 verts=list({v for e in soft for v in e.verts}), edges=soft)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if bevel > 0:
        v3.activate(ob)
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = 1
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(35)
        m.harden_normals = False
        bpy.ops.object.modifier_apply(modifier=m.name)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3], quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(ob.data)
        bm.free()
    return ob


# ------------------------------------------------------------------ fit parameters (hand-set windows, studs; tuned per round)
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))

# Body (torso + neck), loft up z. Windows keep the tail (behind), arms (in front of the chest) and thighs (beside the belly) out.
BODY_Z = (0.50, 0.64, 0.82, 1.02, 1.22, 1.40, 1.56, 1.72, 1.90, 2.12)
BODY_BACK = ((0.5, -0.44), (0.8, -0.56), (1.2, -0.58), (1.5, -0.56), (1.56, -9))     # y clip behind (tail root)
BODY_FRONT = ((0.5, 0.02), (0.64, 0.24), (0.82, 0.42), (1.02, 0.50), (1.22, 0.55), (1.40, 0.58), (1.5, 9))  # y clip in front (arms)
BODY_HALFX = ((0.5, 0.22), (0.64, 0.36), (0.82, 0.43), (1.02, 0.45), (1.22, 0.43), (1.40, 0.39), (1.56, 9))  # x clip (thighs, arms)
NECK_LEAN = 22.0     # degrees forward, the neck above the head's underside (hidden in the skull)
HEAD_LO = 1.86       # head underside (neck below)

# Head: loft forward along y; z range from the side mask, width from the front view's head outline x taper(y).
HEAD_TAPER = ((0.0, 0.62), (0.08, 0.86), (0.25, 0.97), (0.55, 1.0), (0.74, 0.94), (0.86, 0.87), (0.92, 0.82), (0.965, 0.76), (1.0, 0.66))
HEAD_F = (0.0, 0.26, 0.48, 0.68, 0.87, 1.0)           # ring heights (fraction of the z range): jaw, cheek, eye, brow, crown
HEAD_CHAMFER = {0: 0.70, 5: 0.66}                      # jaw (one broad lower bevel, r2) and crown plane width share
MUZZLE_ROUND = {0: 0.22, 1: 0.08, 4: 0.06, 5: 0.18}    # r2: extra corner rounding toward the snout tip (jaw / crown corners)
EYE_C = (0.80, 2.46)                                   # eye centre (y, z); r2: +6 % of head length forward
EYE_SHARE, EYE_PROTRUDE, HILITE = 0.36, 0.25, 0.20      # r2: +12 % diameter
EYE_AIM, EYE_FWD = 36.0, 0.80                           # r2: placed from 36 deg toward the front, axis turned ~12 deg more forward
NOSTRIL = (0.17, 2.30)

# Tail: loft back along -y; z range from the side mask (below the hip line the thigh is cut off), width from the hip width share.
TAIL_ROOT_Z = 1.13   # the root ring's centre = the tail box's z centre (the game's pivot), so no anchor is needed above the back
TAIL_Y = (-0.26, -0.58, -0.78, -0.98, -1.16, -1.32)
TAIL_HALFX = ((-1.32, 0.06), (-1.16, 0.095), (-0.98, 0.14), (-0.78, 0.18), (-0.58, 0.215), (-0.40, 0.215), (-0.26, 0.18))  # ascending y; r2 root -10 %
TAIL_DROP = 0.115    # r2: tip lowered ~10 % of the head height (droop concentrated near the tip)
TAIL_ZLO = ((-0.78, 0.0), (-0.74, 0.88), (-0.40, 0.92))

# Leg (right, +x), loft up z. Below the crotch both masks are the leg; above it the thigh is a hand window inside the hip block.
LEG_Z = (0.0, 0.09, 0.20, 0.34, 0.50, 0.66, 0.82, 0.96, 1.10)
LEG_XIN = ((0.0, 0.10), (0.45, 0.10), (0.66, 0.12), (0.82, 0.14), (0.96, 0.17), (1.10, 0.19))
LEG_XOUT = ((0.0, 9), (0.55, 9), (0.66, 0.70), (0.82, 0.70), (0.96, 0.60), (1.10, 0.38))
LEG_Y = ((0.55, None), (0.66, (-0.70, 0.04)), (0.82, (-0.69, 0.02)), (0.96, (-0.60, -0.04)), (1.10, (-0.39, -0.11)))
CLAW_ROOM = 0.075    # the foot stops this far behind the sheet's toe tip (the claws reach it)

# Arm (right): path shoulder -> elbow -> wrist -> hand tip, ring radii (x half, other half)
ARM_PATH = (V((0.26, 0.20, 1.36)), V((0.42, 0.27, 1.20)), V((0.44, 0.38, 1.03)), V((0.42, 0.52, 0.96)), V((0.40, 0.62, 0.92)))
ARM_R = ((0.105, 0.105), (0.16, 0.14), (0.13, 0.12), (0.12, 0.115), (0.10, 0.09))

SPIKES_BODY = (-0.18, -0.40)                    # r2: 6 instead of 9, spacing varied
SPIKES_TAIL = (-0.70, -0.90, -1.06, -1.25)


# ------------------------------------------------------------------ parts
def build_body(F, S):
    bm, tag = new_bm()
    rings = []
    last = None
    for z in BODY_Z:
        if z <= HEAD_LO - 0.08:
            yr = S.row_run(z, 0.1 if z < 1.45 else 0.3, lerp_table(BODY_BACK, z), lerp_table(BODY_FRONT, z))
            xr = F.row_run(z, 0.0)
            hx = min((xr[1] - xr[0]) / 2, lerp_table(BODY_HALFX, z))
            c, a, b = V((0, (yr[0] + yr[1]) / 2, z)), hx, (yr[1] - yr[0]) / 2
            last = (c, a, b)
        else:   # inside the skull: keep leaning forward, slightly thinner
            c0, a0, b0 = last
            dz = z - c0.z
            c, a, b = V((0, c0.y + dz * math.tan(math.radians(NECK_LEAN)), z)), a0 * 0.92, b0 * 0.92
        n = 2.7 if z < 1.45 else 2.3
        rings.append(superellipse_ring(c, X, Y, a, b, n, 16))
    loft(bm, tag, rings, start_tag=0, end_tag=CAP_TAG)
    return finish("Body", bm, bevel=0.018)


def head_width(F):
    """Half width of the head at height z from the front view (eye bulges taken off: the eyes are their own geometry)."""
    def w(z):
        r = F.row_run(z, 0.0)
        hw = (r[1] - r[0]) / 2 if r else 0.3
        return hw - 0.06 * max(0.0, 1 - abs(z - EYE_C[1]) / 0.24)
    return w


def build_head(F, S):
    bm, tag = new_bm()
    yb = S.extent(2.05, 2.85)[0]       # back of the skull
    yf = S.extent(1.95, 2.70)[1]       # snout front
    ys = [yb + 0.03, yb + 0.12, yb + 0.30] + [yb + (yf - yb) * t for t in (0.42, 0.60, 0.76, 0.86, 0.92, 0.965, 0.99)] + [yf]
    w = head_width(F)
    rings = []
    for y in ys:
        zr = S.col_run(y, 2.45, HEAD_LO, 9)
        t = (y - yb) / (yf - yb)
        tp = lerp_table(HEAD_TAPER, t)
        m = max(0.0, (t - 0.74) / 0.26)          # 0 behind the muzzle -> 1 at the snout tip: corners round off (r2)
        side = []
        for i, f in enumerate(HEAD_F):
            z = zr[0] + f * (zr[1] - zr[0])
            ch = HEAD_CHAMFER.get(i, 1.0) * (1 - m * MUZZLE_ROUND.get(i, 0.0))
            side.append((w(z) * tp * ch, z))
        ring = [V((x, y, z)) for x, z in side] + [V((-x, y, z)) for x, z in reversed(side)]
        rings.append(ring)
    loft(bm, tag, rings)
    ob = finish("Head", bm, dissolve_deg=5.0, bevel=0.02)
    return ob


def build_tail(F, S):
    bm, tag = new_bm()
    rings = []
    tip_y = S.extent(1.25, 1.6)[0]
    for y in TAIL_Y:
        zref = 1.18 + (-0.40 - y) * 0.2
        zr = S.col_run(min(y, -0.58), zref, lerp_table(TAIL_ZLO, y), 9)
        a = lerp_table(TAIL_HALFX, y)
        u = max(0.0, (-0.58 - y) / (-0.58 - tip_y))                 # r2: gentle droop toward the tip
        c = V((0, y, ((zr[0] + zr[1]) / 2 - TAIL_DROP * u ** 2.6) if y < -0.5 else TAIL_ROOT_Z))
        rings.append(superellipse_ring(c, X, Z, a, (zr[1] - zr[0]) / 2 * (0.70 if y > -0.5 else 1.0), 2.2, 12))
    zr = S.col_run(tip_y + 0.05, 1.4, 1.0, 9)
    loft(bm, tag, rings, start_tag=CAP_TAG, end_apex=V((0, tip_y, (zr[0] + zr[1]) / 2 - TAIL_DROP)))
    return finish("Tail", bm, bevel=0.012)


def build_leg(F, S):
    bm, tag = new_bm()
    rings = []
    for z in LEG_Z:
        zq = max(z, 0.02)
        xr = F.row_run(zq, 0.45, lerp_table(LEG_XIN, z), lerp_table(LEG_XOUT, z))
        win = next((w for zz, w in LEG_Y if abs(zz - z) < 1e-6), "mask") if z > 0.55 else "mask"
        if win == "mask":
            yr = S.row_run(zq, -0.30, -0.80, 0.30)
            yr = (yr[0], yr[1] - (CLAW_ROOM if z < 0.17 else 0.0))
        else:
            yr = win
        c = V(((xr[0] + xr[1]) / 2, (yr[0] + yr[1]) / 2, z))
        n = 2.6 if z < 0.15 else 2.15 if z < 0.6 else 2.4   # r2: rounder shin
        rings.append(superellipse_ring(c, X, Y, (xr[1] - xr[0]) / 2, (yr[1] - yr[0]) / 2, n, 12))
    loft(bm, tag, rings, start_tag=0, end_tag=CAP_TAG)
    return finish("LegR", bm, bevel=0.015)


def build_arm():
    bm, tag = new_bm()
    rings = []
    P = ARM_PATH
    for i, (p, (a, b)) in enumerate(zip(P, ARM_R)):
        if i == 0:
            t = Z.copy()       # shoulder ring flat (horizontal): its centre is the box's top centre = the game's arm pivot
            u, v = X, Y
        else:
            d0 = (p - P[i - 1]).normalized()
            d1 = (P[i + 1] - p).normalized() if i + 1 < len(P) else d0
            t = (d0 + d1).normalized()
            u = X - t * X.dot(t)
            u.normalize()
            v = t.cross(u).normalized()
        rings.append(superellipse_ring(p, u, v, a, b, 2.3, 10))
    loft(bm, tag, rings, start_tag=CAP_TAG, end_tag=0)
    return finish("ArmR", bm, bevel=0.012)


# ------------------------------------------------------------------ details
def add_eyes_and_nostrils(head, head_h):
    me = head.data
    bvh = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag")
    r = head_h * EYE_SHARE / 2
    cy, cz = EYE_C
    for s in (1, -1):
        # r2: aimed from EYE_AIM degrees toward the front (the eye sits on the cheek corner, so the front view shows it inside the head)
        a = math.radians(EYE_AIM)
        d = V((-s * math.cos(a), -math.sin(a), 0.0))
        hit = bvh.ray_cast(V((0, cy, cz)) - d * 3.0, d)
        c, n = hit[0], hit[1].normalized()
        if n.x * s < 0:
            n = -n
        ax = (n + V((0.0, EYE_FWD, 0.0))).normalized()   # looks forward and out, like the sheet
        tip = 2 * r * EYE_PROTRUDE
        Rs = (r * r + tip * tip) / (2 * tip)                 # the eye is a spherical cap: base radius r, height tip
        O = c + ax * (tip - Rs)
        u = ax.cross(V((0, 0, 1))).normalized()
        v = ax.cross(u).normalized()
        pmax = math.asin(min(1.0, r / Rs))

        def on_sphere(phi, th):
            return O + (ax * math.cos(phi) + (u * math.cos(th) + v * math.sin(th)) * math.sin(phi)) * Rs
        N = 18
        rings = [[c - ax * 0.06 + (u * math.cos(2 * math.pi * k / N) + v * math.sin(2 * math.pi * k / N)) * r for k in range(N)]]
        for f in (1.0, 0.8, 0.6, 0.4, 0.2):
            rings.append([on_sphere(pmax * f, 2 * math.pi * k / N) for k in range(N)])
        v3.shell(bm, tag, rings, TAG_EYE, apex=c + ax * tip)
        upv = (V((0, 0, 1)) - ax * ax.z).normalized()
        fwd = (V((0, 1, 0)) - ax * ax.y).normalized()
        dh = (ax * math.cos(pmax * 0.55) + (upv * 0.78 + fwd * 0.62).normalized() * math.sin(pmax * 0.55)).normalized()
        hc = O + dh * (Rs + 0.004)
        hr = r * HILITE                                      # highlight radius share = diameter share
        v3.shell(bm, tag, [v3.disc(hc - dh * 0.012, dh, hr, 12), v3.disc(hc + dh * 0.004, dh, hr * 0.92, 12)], TAG_WHITE,
                 apex=hc + dh * 0.008)
        print("SIL eye %s diameter %.3f = %.0f %% of head height, highlight %.0f %% of the eye" % ("R" if s > 0 else "L", 2 * r,
              100 * 2 * r / head_h, 100 * HILITE))
    for s in (1, -1):
        hit = bvh.ray_cast(V((s * NOSTRIL[0], 3.0, NOSTRIL[1])), V((0, -1, 0)))
        c, n = hit[0], hit[1].normalized()
        if n.y < 0:
            n = -n
        u = n.cross(V((0, 0, 1))).normalized()
        v = n.cross(u).normalized()
        ring = [c - n * 0.01 + u * 0.034 * math.cos(2 * math.pi * k / 8) + v * 0.022 * math.sin(2 * math.pi * k / 8) for k in range(8)]
        v3.shell(bm, tag, [ring, [q + n * 0.016 for q in ring]], TAG_NOSTRIL)
    v3.finish_shells(bm)
    bm.to_mesh(me)
    bm.free()


def add_spikes(ob, ys, height, base):
    """Small soft dorsal spikes on the top centre line (ray cast down), leaning back."""
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    tag = bm.faces.layers.int.get("tag")
    for i, y in enumerate(ys):
        hit = bvh.ray_cast(V((0, y, 4.0)), V((0, 0, -1)))
        if hit[0] is None:
            continue
        c, n = hit[0], hit[1].normalized()
        if n.z < 0:
            n = -n
        h = height[i] if isinstance(height, (list, tuple)) else height
        b = base[i] if isinstance(base, (list, tuple)) else base
        ring = v3.disc(c - n * 0.03, n, b, 6, roll=math.pi / 2)
        mid = [c + n * h * 0.55 + (q - c) * 0.62 + V((0, -0.2 * h, 0)) for q in ring]
        v3.shell(bm, tag, [ring, mid], 0, apex=c + n * h + V((0, -0.35 * h, 0)))
    v3.finish_shells(bm)
    bm.to_mesh(ob.data)
    bm.free()


def add_claws(leg):
    """Three rounded dark claws on the toe front (ray cast from the front), pointing forward and down."""
    me = leg.data
    bvh = BVHTree.FromObject(leg, bpy.context.evaluated_depsgraph_get())
    feet = [v.co for v in me.vertices if v.co.z < 0.2]
    fx = (min(p.x for p in feet) + max(p.x for p in feet)) / 2
    half = (max(p.x for p in feet) - min(p.x for p in feet)) / 2
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag")
    for dx in (-0.62, 0.0, 0.62):
        hit = bvh.ray_cast(V((fx + dx * half, 3.0, 0.085)), V((0, -1, 0)))
        if hit[0] is None:
            continue
        c = hit[0]
        f = V((0, 1, 0))
        r = half * 0.31
        # r2: a separate rounded lime toe (8-sided, 3 rings) per claw, the dark claw on its tip
        toe = [superellipse_ring(c + f * dy, X, Z, r * k, r * 0.82 * k, 2.2, 8) for dy, k in ((-0.07, 1.0), (0.0, 1.04), (0.03, 0.86))]
        v3.shell(bm, tag, toe, 0, apex=c + f * 0.045)
        rings = [v3.disc(c + f * 0.012 + V((0, 0, 0.004)), f, r * 0.95, 8), v3.disc(c + f * 0.05, f, r * 0.82, 8),
                 [q + V((0, 0, -0.008)) for q in v3.disc(c + f * 0.075, f, r * 0.62, 8)]]
        v3.shell(bm, tag, rings, TAG_CLAW, apex=c + f * 0.095 + V((0, 0, -0.02)))
    v3.finish_shells(bm)
    bm.to_mesh(me)
    bm.free()


def add_anchor(ob, p, size=0.012):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    tag = bm.faces.layers.int.get("tag")
    vs = [bm.verts.new(p + V(d) * size) for d in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))]
    for f in ((0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)):
        bm.faces.new([vs[i] for i in f])[tag] = ANCHOR_TAG
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[-4:])
    bm.to_mesh(ob.data)
    bm.free()


def box(ob):
    ws = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return V([min(w[i] for w in ws) for i in range(3)]), V([max(w[i] for w in ws) for i in range(3)])


def center_on_joint(ob, joint, axes):
    """One hidden anchor (tetra, buried in the body) that moves the box centre on `axes` onto the joint."""
    lo, hi = box(ob)
    p = joint.copy()
    need = False
    for ax in axes:
        want = joint[ax]
        if abs((lo[ax] + hi[ax]) / 2 - want) < 0.004:
            continue
        need = True
        if hi[ax] - want > want - lo[ax]:
            p[ax] = 2 * want - hi[ax] + 0.012
        else:
            p[ax] = 2 * want - lo[ax] - 0.012
    if not need:
        return None
    if ob.name.startswith(("Leg", "Arm")):
        p.z = joint.z - 0.03
    else:
        p.y = joint.y - 0.03
    add_anchor(ob, p)
    return p


def inside(tree, p):
    hits = 0
    for d in (V((0.31, 0.52, 0.80)).normalized(), V((-0.71, 0.13, -0.69)).normalized(), V((0.22, -0.95, 0.21)).normalized()):
        n, o = 0, p.copy()
        for _ in range(64):
            h = tree.ray_cast(o, d)
            if h[0] is None:
                break
            n += 1
            o = h[0] + d * 1e-4
        hits += n % 2
    return hits >= 2


def mirror_x(ob, name):
    me = ob.data.copy()
    me.transform(Matrix.Scale(-1, 4, V((1, 0, 0))))
    me.flip_normals()
    new = bpy.data.objects.new(name, me)
    me.name = name
    bpy.context.scene.collection.objects.link(new)
    return new


def cap_joint(ob):
    """Centre of the faces tagged CAP (the flat joint face)."""
    me = ob.data
    t = me.attributes["tag"]
    pts = [ob.matrix_world @ me.polygons[i].center for i in range(len(me.polygons)) if t.data[i].value == CAP_TAG]
    return sum(pts, V()) / len(pts)


# ------------------------------------------------------------------ colour and shading
SHARP_DEG = {"Head": 14, "Body": 30, "Tail": 30, "LegR": 30, "LegL": 30, "ArmR": 35, "ArmL": 35}  # hard edge above this
CREAM_W = ((0.46, 0.05), (0.54, 0.12), (0.68, 0.18), (0.95, 0.28), (1.20, 0.33), (1.45, 0.34), (1.95, 0.34))  # r2: lower, rounded point


def material_index(name, c, n, tg):
    if tg == TAG_EYE or tg == TAG_NOSTRIL:
        return 3
    if tg == TAG_WHITE:
        return 4
    if tg == TAG_CLAW:
        return 2
    if tg in (CAP_TAG, ANCHOR_TAG):
        return 0
    ny = -0.85 if c.z < 0.70 else 0.12 if c.z < 1.45 else -0.15     # r2: the crotch faces (down-front) join the band
    if name == "Body" and 0.44 < c.z < 1.95 and n.y > ny and c.y > (-0.40 if c.z < 0.70 else -0.15) and abs(c.x) < lerp_table(CREAM_W, c.z):
        return 1
    if name == "Tail" and n.z < -0.25 and c.y > -1.30:
        return 1
    return 0


def make_materials():
    mats = []
    for key in ("lime", "cream", "claw", "eye", "white"):
        m = bpy.data.materials.new("CompySil_" + key)
        m.use_nodes = True
        bs = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
        col = hexlin(PALETTE[key])
        bs.inputs["Base Color"].default_value = col
        bs.inputs["Roughness"].default_value = 0.12 if key in ("eye", "white") else 0.38
        m.diffuse_color = col
        mats.append(m)
    return mats


def colour_and_shade(ob, mats):
    me = ob.data
    for m in mats:
        me.materials.append(m)
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag")
    bm.normal_update()
    idx = [material_index(ob.name, f.calc_center_median(), f.normal, f[tag]) for f in bm.faces]
    bm.faces.ensure_lookup_table()
    for _ in range(2):   # tidy the lime / cream border (no lone triangles)
        nxt = list(idx)
        for f in bm.faces:
            if idx[f.index] not in (0, 1) or f[tag]:
                continue
            votes = [0.0, 0.0]
            for g in [f] + [g for e in f.edges for g in e.link_faces if g is not f]:
                if idx[g.index] in (0, 1) and not g[tag]:
                    votes[idx[g.index]] += g.calc_area()
            nxt[f.index] = 0 if votes[0] >= votes[1] else 1
        idx = nxt
    lim = math.radians(SHARP_DEG.get(ob.name[:4], 45))
    for f in bm.faces:
        f.material_index = idx[f.index]
        f.smooth = True
    for e in bm.edges:   # smooth by angle 45; sharp where two colours or a detail meets the skin
        lf = e.link_faces
        sharp = len(lf) != 2 or e.calc_face_angle(0) > lim or lf[0].material_index != lf[1].material_index or lf[0][tag] != lf[1][tag]
        e.smooth = not sharp
    bm.to_mesh(me)
    bm.free()


# ------------------------------------------------------------------ renders
def camera(name, d, scale, target):
    cd = bpy.data.cameras.new(name)
    cd.type = "ORTHO"
    cd.ortho_scale = scale
    cam = bpy.data.objects.new("cam_" + name, cd)
    bpy.context.scene.collection.objects.link(cam)
    d = V(d).normalized()
    cam.location = V(target) + d * 20
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return cam


def view_dir(name):
    if name == "front":
        return (0, 1, 0)
    if name == "side":
        return (1, 0, 0)
    if name == "back":
        return (0, -1, 0)
    _, yaw, tilt = name.split("_")
    a, e = math.radians(float(yaw)), math.radians(float(tilt))
    return (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))


def render_silhouettes(objs, out):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (0, 0, 0)
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 640
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    os.makedirs(out, exist_ok=True)
    names = ["front", "side"] + ["q34_%d_%d" % (y, t) for y in Q34_YAWS for t in Q34_TILTS]
    for n in names:
        sc.camera = camera(n, view_dir(n), 4.0, (0, 0, 1.5))
        sc.render.filepath = os.path.join(out, n + ".png")
        bpy.ops.render.render(write_still=True)


def render_look(objs, out, q34):
    """Studio look: soft key / fill / rim area lights, roughness 0.38, transparent film. The black outline is added in 2D from the alpha
    (compare(): ~1.7 % of the height, like the sheet): Freestyle drew a broken, dashed contour where the rigid parts intersect."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 640
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.42, 0.42, 1)
    bg.inputs["Strength"].default_value = 0.45
    for name, loc, energy, size in (("key", (4.5, 4.0, 4.5), 650, 3.5), ("fill", (-5.0, 3.5, 2.0), 260, 4.0),
                                    ("rim", (-2.0, -5.0, 5.0), 700, 2.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.shape = "DISK"   # round reflections in the glossy eyes (r2)
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = (V((0, 0, 1.5)) - V(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(lo)
    os.makedirs(out, exist_ok=True)
    for n in ("front", q34, "side", "back"):
        sc.camera = camera("look_" + n, view_dir(n), 4.0, (0, 0, 1.5))
        sc.render.filepath = os.path.join(out, ("q34" if n.startswith("q34") else n) + ".png")
        bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------ main
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    masks = np.load(os.path.join(WORK, "masks.npz"))
    S = View(masks["side"], c0=(masks["side"].shape[1] - 1) / 2)
    F = View(masks["front"])
    print("SIL side %.1f px/stud, front %.1f px/stud" % (S.s, F.s))
    body, head, tail = build_body(F, S), build_head(F, S), build_tail(F, S)
    leg_r, arm_r = build_leg(F, S), build_arm()
    head_lo, head_hi = box(head)
    add_eyes_and_nostrils(head, head_hi.z - head_lo.z)
    add_spikes(body, SPIKES_BODY, 0.038, 0.06)          # r2: ~30 % lower, wider base = soft bumps
    add_spikes(tail, SPIKES_TAIL, [0.04, 0.037, 0.033, 0.028], [0.056, 0.052, 0.046, 0.04])
    add_claws(leg_r)
    leg_l, arm_l = mirror_x(leg_r, "LegL"), mirror_x(arm_r, "ArmL")
    objs = {o.name: o for o in (body, head, tail, arm_l, arm_r, leg_l, leg_r)}
    # joints: cap centres; anchors so the game's box pivots land on them
    body_tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    for name, axes in (("LegR", (0, 1)), ("LegL", (0, 1)), ("ArmR", (0, 1)), ("ArmL", (0, 1)), ("Tail", (0, 2))):
        j = cap_joint(objs[name])
        p = center_on_joint(objs[name], j, axes)
        lo, hi = box(objs[name])
        piv = v3.pivot_for(name, lo, hi)
        print("SIL joint %-4s cap centre (%.3f %.3f %.3f) box pivot (%.3f %.3f %.3f) off %.3f  anchor %s inside body %s" % (
            name, j.x, j.y, j.z, piv.x, piv.y, piv.z, (piv - j).length, None if p is None else tuple(round(c, 3) for c in p),
            None if p is None else inside(body_tree, p)))
    neck_cap = cap_joint(body)
    head_tree = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())
    print("SIL neck top inside head: %s" % inside(head_tree, neck_cap))
    # widths (head vs torso)
    hw = 2 * max(abs(v.co.x) for v in head.data.vertices if v.co.z > HEAD_LO + 0.05 and v.co.y < EYE_C[0] - 0.25)   # skull, no eyes
    tw = max(abs(v.co.x) for v in body.data.vertices if 1.0 < v.co.z < 1.4) * 2
    mats = make_materials()
    tris = {}
    for name in PARTS:
        ob = objs[name]
        colour_and_shade(ob, mats)
        v3.set_origin(ob)
        tris[name] = v3.tris_of(ob.data)
    lo = [min((ob.matrix_world @ V(c))[i] for ob in objs.values() for c in ob.bound_box) for i in range(3)]
    hi = [max((ob.matrix_world @ V(c))[i] for ob in objs.values() for c in ob.bound_box) for i in range(3)]
    print("SIL tris %s total %d; size x %.2f y %.2f z %.2f; head width %.2f = %.0f %% of torso %.2f" % (
        tris, sum(tris.values()), hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], hw, 100 * hw / tw, tw))
    json.dump({"tris": tris, "head_to_torso_width": round(hw / tw, 3), "size": [hi[i] - lo[i] for i in range(3)]},
              open(os.path.join(WORK, "build.json"), "w"))
    if "--final" in ARGS:
        os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT, compress=True, relative_remap=True)
        print("SIL saved", os.path.relpath(BLEND_OUT, ROOT))
    render_silhouettes(objs, os.path.join(WORK, "sil"))
    if "--final" in ARGS:
        q = arg("--q34", "q34_50_8")
        render_look(objs, os.path.join(WORK, "look"), q)


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("ERROR build failed")
    sys.exit(1)
