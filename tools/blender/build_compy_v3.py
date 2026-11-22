"""Compy V3 game model builder (BD-1291 step 3, Hunyuan3D-2 route). Headless Blender only (never the MCP or a GUI Blender).

  python tools/blender/build_compy_v3.py --src <q34_shape.glb>               # headless Blender, below-normal priority, CPU only
  python tools/blender/build_compy_v3.py --src <q34_shape.glb> --no-render   # model + textures + .blend only
  python tools/blender/build_compy_v3.py --src <q34_shape.glb> --labels      # debug: renders the part split in flat colours

Source: a local Hunyuan3D-2 image-to-3D mesh (40k faces, untextured; NOT committed) made from the owner-approved ChatGPT sheet
docs/evidence/2026-11-22-dino-ranking/compy-sheet-v1.jpg. Default --src is build/hy3d-compy/out/q34_shape.glb (ignored build folder).
V3 supersedes the script-built V2 (tools/blender/build_compy_v2.py), whose part/pivot/bake/render pipeline this file reuses.

Steps: import (Blender's glTF importer already stands it up, Z up) -> turn 180 degrees so it faces +Y -> 3.0 studs tall, feet on 0,
centred on X -> mirror the +X half (exact symmetry) -> flatten the mesh's eye bumps -> cut into seven parts named for
LowPolyPose.roleOf (Body = torso + neck, Head, Tail, ArmL, ArmR, LegL, LegR) along planes (bisected first so the cuts are straight),
cap every cut opening -> decimate each part (collapse, symmetric for the centre parts) to the low-poly budget -> flush glossy eye
discs (about 32 % of head height, protruding under 25 % of their diameter) with a white highlight, two nostril dots -> per-face
colours (lime body, cream throat-to-belly band, dark toe claws) as vertex colours AND a baked texture per part -> origins at the joints
where LowPolyAnimator.pivotFor puts them (same rule as V2) -> .blend (packed, relative paths) -> Cycles CPU renders for the crop pairs.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"

try:
    import bpy  # type: ignore
    import bmesh  # type: ignore
    from mathutils import Vector, Matrix  # type: ignore
    from mathutils.bvhtree import BVHTree  # type: ignore
    INSIDE = True
except ImportError:
    INSIDE = False

if not INSIDE:
    import subprocess
    if __name__ == "__main__":
        exe = os.environ.get("BLENDER_EXE", BLENDER)
        cmd = [exe, "-b", "--factory-startup", "--python", os.path.abspath(__file__), "--"] + sys.argv[1:]
        flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        res = subprocess.run(cmd, creationflags=flags, capture_output=True, text=True)
        lines = (res.stdout or "").splitlines()
        print("\n".join(l for l in lines if l.startswith(("COMPY", "ERROR", "Traceback", "  File")) or "Error" in l))
        if res.returncode:
            print((res.stderr or "")[-2000:])
        sys.exit(res.returncode)
    raise SystemExit(0)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


SRC = arg("--src", os.path.join(ROOT, "build", "hy3d-compy", "out", "q34_shape.glb"))
BLEND_OUT = os.path.join(ROOT, "assets", "blender", "creatures", "Compy_V3.blend")
TEX_DIR = os.path.join(ROOT, "assets", "blender", "creatures", "textures", "compy_v3")
RENDER_DIR = os.path.join(ROOT, "docs", "evidence", "2026-11-22-compy-v3")
# Owner 2026-11-22 "can there not be less low poly?": --detail multiplies the triangle budget, --smooth ANGLE shades smooth with hard
# edges only above ANGLE degrees, --tag NAME writes the .blend, textures and renders to build/compy-variants/NAME (try-outs, not committed).
DETAIL = float(arg("--detail", "1"))
SMOOTH = arg("--smooth")
TAG = arg("--tag")
if TAG:
    _VAR = os.path.join(ROOT, "build", "compy-variants", TAG)
    BLEND_OUT, TEX_DIR, RENDER_DIR = os.path.join(_VAR, "Compy_V3.blend"), os.path.join(_VAR, "textures"), _VAR
V = Vector


def hexcol(h):
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)) + (1.0,)


LIME = hexcol("#79DC21")   # the approved sheet's body colour (wins over V2's #72D85F)
CREAM = hexcol("#F5EDD8")
EYE = hexcol("#10151A")
WHITE = hexcol("#FFFFFF")
CLAW = hexcol("#3C3C3C")
TAG_COL = {1: EYE, 2: WHITE, 3: CLAW, 4: EYE}  # face tags: 1 eye, 2 highlight, 3 claw, 4 nostril
TEX_SIZE = {"Body": 256, "Head": 256}
PARTS = ("Body", "Head", "Tail", "ArmL", "ArmR", "LegL", "LegR")
# Triangle budget per part (total about 2.6k before the eye/nostril shells).
# (A Laplacian pre-smooth of the source was tried in iteration 2: it made MORE small facets and bent the arms; dropped.)
BUDGET = {"Body": 520, "Head": 480, "Tail": 150, "ArmL": 80, "ArmR": 80, "LegL": 220, "LegR": 220}
DISSOLVE_DEG = 12.0

# ------------------------------------------------------------------ part split (model space, studs; faces +Y, X = creature's left is -X)
HEAD_Z = 1.78            # head = everything above this plane (neck top stays on the head's bottom back, like V2)
TAIL_Y, TAIL_Z = -0.50, 0.70
ARM_X, ARM_Y, ARM_Z0, ARM_Z1 = 0.30, 0.50, 0.75, 1.38   # iteration 2: tighter, the chest sides stay on the Body
LEG_X, LEG_Z, LEG_Y0, LEG_Y1, FOOT_Z = 0.24, 1.22, -0.50, 0.15, 0.45


def label(c):
    """Part for a face centre c (first match wins)."""
    ax = abs(c.x)
    side = "L" if c.x < 0 else "R"   # creature faces +Y, so its right hand is +X... see note below
    if c.z > HEAD_Z:
        return "Head"
    if c.y < TAIL_Y and c.z > TAIL_Z:
        return "Tail"
    if ax > ARM_X and c.y > ARM_Y and ARM_Z0 < c.z < ARM_Z1:
        return "Arm" + side
    if c.z < FOOT_Z or (ax > LEG_X and c.z < LEG_Z and LEG_Y0 < c.y < LEG_Y1):
        return "Leg" + side
    return "Body"


# Note on sides: V2 put ArmR/LegR at +X (build_arm(1) -> "ArmR"); V3 keeps that convention so both candidates map the same way.

# Cut planes, each with the box of faces it may cut (lo, hi corners; |x| boxes are mirrored).
CUTS = [
    ((0, 0, HEAD_Z), (0, 0, 1), None),
    ((0, TAIL_Y, 0), (0, 1, 0), ((-2, -2, TAIL_Z - 0.05), (2, 2, 3))),
    ((0, 0, TAIL_Z), (0, 0, 1), ((-2, -2, 0), (2, TAIL_Y + 0.05, 3))),
    ((ARM_X, 0, 0), (1, 0, 0), ((0, ARM_Y - 0.05, ARM_Z0 - 0.05), (2, 2, ARM_Z1 + 0.05))),
    ((0, ARM_Y, 0), (0, 1, 0), ((ARM_X - 0.05, -2, ARM_Z0 - 0.05), (2, 2, ARM_Z1 + 0.05))),
    ((0, 0, ARM_Z0), (0, 0, 1), ((ARM_X - 0.05, ARM_Y - 0.05, 0), (2, 2, 3))),
    ((0, 0, ARM_Z1), (0, 0, 1), ((ARM_X - 0.05, ARM_Y - 0.05, 0), (2, 2, 3))),
    ((0, 0, FOOT_Z), (0, 0, 1), ((0, -2, 0), (LEG_X + 0.05, 2, 3))),
    ((LEG_X, 0, 0), (1, 0, 0), ((0, LEG_Y0 - 0.05, FOOT_Z - 0.05), (2, LEG_Y1 + 0.05, LEG_Z + 0.05))),
    ((0, 0, LEG_Z), (0, 0, 1), ((LEG_X - 0.05, LEG_Y0 - 0.05, 0), (2, LEG_Y1 + 0.05, 3))),
    ((0, LEG_Y1, 0), (0, 1, 0), ((LEG_X - 0.05, -2, FOOT_Z - 0.05), (2, 2, LEG_Z + 0.05))),
    ((0, LEG_Y0, 0), (0, 1, 0), ((LEG_X - 0.05, -2, FOOT_Z - 0.05), (2, 2, LEG_Z + 0.05))),
]

# Eye bump on the Hunyuan head (side view, +X side): first guess, refined from the bump itself.
EYE_GUESS = (0.75, 2.45)   # (y, z)
EYE_H_SHARE = 0.32         # eye diameter / head height
EYE_PROTRUDE = 0.24        # protrusion / eye diameter (<= 0.25)

# ------------------------------------------------------------------ helpers


def disc(c, axis, r, segs, roll=0.0):
    axis = axis.normalized()
    ref = V((0, 0, 1)) if abs(axis.z) < 0.9 else V((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    return [c + (u * math.cos(roll + 2 * math.pi * i / segs) + v * math.sin(roll + 2 * math.pi * i / segs)) * r for i in range(segs)]


def shell(bm, tag_layer, rings, tag, apex=None, cap0=True):
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    faces = []
    n = len(rings[0])
    for a, b in zip(vr, vr[1:]):
        for j in range(n):
            k = (j + 1) % n
            faces.append(bm.faces.new((a[j], a[k], b[k], b[j])))
    if cap0:
        faces.append(bm.faces.new(vr[0][::-1]))
    if apex is not None:
        ap = bm.verts.new(apex)
        for j in range(n):
            faces.append(bm.faces.new((vr[-1][j], vr[-1][(j + 1) % n], ap)))
    else:
        faces.append(bm.faces.new(vr[-1]))
    for f in faces:
        f[tag_layer] = tag
    return faces


def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def activate(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


# ------------------------------------------------------------------ source mesh


def load_source():
    bpy.ops.import_scene.gltf(filepath=SRC)
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bm = bmesh.new()
    for o in obs:
        tmp = o.data.copy()
        tmp.transform(o.matrix_world)
        bm.from_mesh(tmp)
    for o in list(bpy.context.scene.objects):
        bpy.data.objects.remove(o)
    # face +Y (the import has the snout at -Y), then 3.0 studs tall, feet on 0, centred on X
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=V(), matrix=Matrix.Rotation(math.pi, 3, "Z"))
    lo = [min(v.co[i] for v in bm.verts) for i in range(3)]
    hi = [max(v.co[i] for v in bm.verts) for i in range(3)]
    s = 3.0 / (hi[2] - lo[2])
    for v in bm.verts:
        v.co = V(((v.co.x - (lo[0] + hi[0]) / 2) * s, v.co.y * s, (v.co.z - lo[2]) * s))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    # exact symmetry: keep +X, mirror it
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V(), plane_no=V((1, 0, 0)), clear_inner=True)
    for v in bm.verts:
        if abs(v.co.x) < 1e-4:
            v.co.x = 0.0
    bmesh.ops.mirror(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], axis="X", merge_dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def plane_fit_x(pts):
    """Least squares x = a + b*y + c*z through pts."""
    import numpy as np
    A = np.array([[1.0, p.y, p.z] for p in pts])
    b = np.array([p.x for p in pts])
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    return sol


def flatten_eye_bumps(bm):
    """Push the mesh's eye bumps back into the head's side plane; returns the bump centre (y, z) on the +X side and the plane."""
    gy, gz = EYE_GUESS
    head = [v for v in bm.verts if v.co.z > HEAD_Z + 0.1 and v.co.x > 0.3]
    ringv = [v for v in head if 0.30 ** 2 < (v.co.y - gy) ** 2 + (v.co.z - gz) ** 2 < 0.42 ** 2 and v.co.x > 0.45]
    a, b, c = plane_fit_x([v.co for v in ringv])
    inner = [v for v in head if (v.co.y - gy) ** 2 + (v.co.z - gz) ** 2 < 0.32 ** 2]
    bump = [v for v in inner if v.co.x - (a + b * v.co.y + c * v.co.z) > 0.015]
    cy = sum(v.co.y for v in bump) / len(bump)
    cz = sum(v.co.z for v in bump) / len(bump)
    moved = 0
    for v in bm.verts:
        if v.co.z > HEAD_Z and (v.co.y - gy) ** 2 + (v.co.z - gz) ** 2 < 0.34 ** 2 and abs(v.co.x) > 0.3:
            px = a + b * v.co.y + c * v.co.z
            if abs(v.co.x) > px:
                v.co.x = math.copysign(px, v.co.x)
                moved += 1
    print("COMPY eye bump centre y %.3f z %.3f (%d bump verts, %d flattened), side plane x = %.3f %+.3fy %+.3fz" % (cy, cz, len(bump), moved, a, b, c))
    return (cy, cz), (a, b, c)


def cut_and_label(bm):
    for co, no, box in CUTS:
        co, no = V(co), V(no)
        for sgn in ((1, -1) if (box is not None and box[0][0] >= 0) or co.x > 0 else (1,)):
            pc = V((co.x * sgn, co.y, co.z))
            if box is None:
                faces = bm.faces[:]
            else:
                (x0, y0, z0), (x1, y1, z1) = box
                faces = []
                for f in bm.faces:
                    c = f.calc_center_median()
                    x = c.x * sgn if box[0][0] >= 0 else c.x
                    if x0 <= x <= x1 and y0 <= c.y <= y1 and z0 <= c.z <= z1:
                        faces.append(f)
            if not faces:
                continue
            edges = list({e for f in faces for e in f.edges})
            verts = list({v for f in faces for v in f.verts})
            bmesh.ops.bisect_plane(bm, geom=verts + edges + faces, plane_co=pc, plane_no=no, dist=1e-5)
    return {f.index: label(f.calc_center_median()) for f in bm.faces}


def split_parts(bm):
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    labels = cut_and_label(bm)
    bm.faces.index_update()
    labels = [label(f.calc_center_median()) for f in bm.faces]
    parts = {}
    for name in PARTS:
        pb = bm.copy()
        pb.faces.ensure_lookup_table()
        kill = [f for f, l in zip(pb.faces, labels) if l != name]
        bmesh.ops.delete(pb, geom=kill, context="FACES")
        loose = [v for v in pb.verts if not v.link_faces]
        bmesh.ops.delete(pb, geom=loose, context="VERTS")
        pb.faces.index_update()
        # drop tiny stray islands (a few faces caught across a cut), keep the big one(s)
        islands = []
        seen = set()
        for f in pb.faces:
            if f.index in seen:
                continue
            stack, isl = [f], []
            seen.add(f.index)
            while stack:
                g = stack.pop()
                isl.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen:
                            seen.add(h.index)
                            stack.append(h)
            islands.append(isl)
        pb.faces.index_update()
        big = max(len(i) for i in islands)
        stray = [f for isl in islands if len(isl) < big * 0.05 for f in isl]
        if stray:
            bmesh.ops.delete(pb, geom=stray, context="FACES")
            bmesh.ops.delete(pb, geom=[v for v in pb.verts if not v.link_faces], context="VERTS")
        # cap the cut openings
        bnd = [e for e in pb.edges if e.is_boundary]
        if bnd:
            caps = pb.faces.layers.int.get("tag") or pb.faces.layers.int.new("tag")
            bnd = [e for e in pb.edges if e.is_boundary]  # a new layer invalidates element references: collect again
            res = bmesh.ops.holes_fill(pb, edges=bnd, sides=0)
            tri = bmesh.ops.triangulate(pb, faces=res["faces"])
            for f in tri["faces"]:
                f[caps] = CAP_TAG  # inside faces: always lime, never part of the cream band
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces[:])
        print("COMPY split %-5s faces %6d islands %d (stray dropped %d) open edges after cap %d" % (
            name, len(pb.faces), len(islands), len(stray), sum(1 for e in pb.edges if e.is_boundary)))
        parts[name] = pb
    return parts


def decimate(ob, target):
    activate(ob)
    n = tris_of(ob.data)
    if n > target * DETAIL:
        mod = ob.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = min(1.0, target * DETAIL / n)
        mod.use_collapse_triangulate = True
        if ob.name in ("Body", "Head", "Tail"):
            mod.use_symmetry = True
            mod.symmetry_axis = "X"
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # merge the near-coplanar triangles the collapse leaves into big flat planes (no lumpy noise), then triangulate them again
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(DISSOLVE_DEG / max(1.0, DETAIL)), use_dissolve_boundaries=False,
                             verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    print("COMPY decimated %-5s tris %d" % (ob.name, tris_of(ob.data)))
    for p in ob.data.polygons:
        p.use_smooth = False


def apply_shading(ob):
    """--smooth ANGLE (owner 2026-11-22 'less low poly'): smooth shading, hard edges only where the surface bends more than ANGLE."""
    if SMOOTH is None:
        return
    limit = math.radians(float(SMOOTH))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0) > limit)
    bm.to_mesh(ob.data)
    bm.free()


# ------------------------------------------------------------------ face details


def finish_shells(bm):
    """Triangulate the eye/nostril/claw caps (no n-gons for Roblox) and make every shell face point outward."""
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def add_eyes_and_nostrils(ob, eye_c, head_h):
    me = ob.data
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag") or bm.faces.layers.int.new("tag")
    r = head_h * EYE_H_SHARE / 2
    cy, cz = eye_c
    for s in (1, -1):
        hit = bvh.ray_cast(V((s * 3.0, cy, cz)), V((-s, 0, 0)))
        c, n = hit[0], hit[1].normalized()
        if n.x * s < 0:
            n = -n
        ax = n
        tip = 2 * r * EYE_PROTRUDE
        er = [disc(c - ax * 0.05, ax, r, 14), disc(c + ax * tip * 0.5, ax, r * 0.9, 14), disc(c + ax * tip * 0.86, ax, r * 0.55, 14)]
        shell(bm, tag, er, 1, apex=c + ax * tip)
        upv = (V((0, 0, 1)) - ax * ax.z).normalized()
        fwd = (V((0, 1, 0)) - ax * ax.y).normalized()
        hc = c + ax * tip * 0.86 + upv * (r * 0.38) + fwd * (r * 0.22)
        hr = disc(hc, ax, r * 0.26, 8)
        shell(bm, tag, [disc(hc - ax * 0.02, ax, r * 0.26, 8), hr], 2, apex=hc + ax * 0.03)
        print("COMPY eye %s centre (%.3f %.3f %.3f) normal (%.2f %.2f %.2f) diameter %.3f (%.0f %% of head height) protrudes %.3f (%.0f %%)" % (
            "R" if s > 0 else "L", c.x, c.y, c.z, n.x, n.y, n.z, 2 * r, 100 * 2 * r / head_h, tip, 100 * tip / (2 * r)))
    # nostrils: two dots on the snout's front face
    for s in (1, -1):
        hit = bvh.ray_cast(V((s * NOSTRIL_X, 3.0, NOSTRIL_Z)), V((0, -1, 0)))
        c, n = hit[0], hit[1].normalized()
        if n.y < 0:
            n = -n
        rr = disc(c - n * 0.01, n, 0.036, 8)
        shell(bm, tag, [rr, [q + n * 0.018 for q in rr]], 4)
        print("COMPY nostril at (%.3f %.3f %.3f)" % (c.x, c.y, c.z))
    finish_shells(bm)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False


NOSTRIL_X, NOSTRIL_Z = 0.13, 2.42
CLAW_SPREAD, CLAW_Z, CLAW_R, CLAW_LEN = 0.15, 0.075, 0.072, 0.11


def add_claws(ob):
    """Three dark claws on the front of each foot (like the sheet), placed on the toe surface by ray cast from the front."""
    me = ob.data
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    feet = [v.co for v in me.vertices if v.co.z < 0.25]
    fx = (min(p.x for p in feet) + max(p.x for p in feet)) / 2
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag") or bm.faces.layers.int.new("tag")
    fwd = V((0, 1, 0))
    for dx in (-CLAW_SPREAD, 0.0, CLAW_SPREAD):
        hit = bvh.ray_cast(V((fx + dx, 3.0, CLAW_Z)), V((0, -1, 0)))
        if hit[0] is None:
            continue
        c = hit[0]
        base = disc(c - fwd * 0.03, fwd, CLAW_R, 6)
        mid = [q + fwd * 0.03 for q in disc(c, fwd, CLAW_R * 0.85, 6)]
        shell(bm, tag, [base, mid], 3, apex=c + fwd * CLAW_LEN + V((0, 0, -0.035)))
    finish_shells(bm)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False


CAP_TAG = 5


def colour_for(name, c, n, tag, info):
    if tag in TAG_COL:
        return TAG_COL[tag]
    if tag == CAP_TAG:
        return LIME
    ny = CREAM_NY if c.z < 1.35 else 0.05   # iteration 3: the neck band wraps further round so the side view shows it like the sheet
    if name == "Body" and n.y > ny and abs(c.x) < CREAM_HALF_W(c.z) and c.z > CREAM_Z0 and c.y > -0.1:
        return CREAM
    if name == "Head" and c.z < HEAD_Z + 0.2 and n.y > 0.0 and n.z < 0.5 and 0.0 < c.y < 0.6 and abs(c.x) < 0.32:  # front half only
        return CREAM
    return LIME


CREAM_NY, CREAM_Z0 = 0.25, 0.62


def CREAM_HALF_W(z):
    # V-shaped band: narrow between the legs, widest on the chest, neck width at the throat
    if z < 0.95:
        return 0.10 + (z - CREAM_Z0) / (0.95 - CREAM_Z0) * 0.20
    if z < 1.35:
        return 0.30
    return 0.30


def apply_colours(ob):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag")
    bm.normal_update()
    info = {"toe_y": max(v.co.y for v in bm.verts)}
    cols = [colour_for(ob.name, f.calc_center_median(), f.normal, f[tag] if tag else 0, info) for f in bm.faces]
    # clean the lime/cream border: a denser mesh (--detail) leaves single cream triangles by the arms; each lime/cream face takes the
    # area-weighted majority of itself and its edge neighbours (3 passes, 6 with --detail); eye, highlight, claw and nostril faces never change
    bm.faces.ensure_lookup_table()
    soft = [not (tag and (f[tag] in TAG_COL or f[tag] == CAP_TAG)) for f in bm.faces]
    area = [f.calc_area() for f in bm.faces]
    for _ in range(3 + 3 * int(DETAIL > 1)):
        nxt = list(cols)
        for f in bm.faces:
            i = f.index
            if not soft[i]:
                continue
            votes = {LIME: 0.0, CREAM: 0.0}
            for g in [f] + [g for e in f.edges for g in e.link_faces if g is not f]:
                if soft[g.index] and cols[g.index] in votes:
                    votes[cols[g.index]] += area[g.index]
            nxt[i] = LIME if votes[LIME] >= votes[CREAM] else CREAM
        cols = nxt
    bm.free()
    attr = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for poly, col in zip(me.polygons, cols):
        for li in poly.loop_indices:
            attr.data[li].color_srgb = col


def pivot_for(name, lo, hi):
    """Blender-space joint where LowPolyAnimator.pivotFor puts it (Roblox +Z = Blender -Y, so the Roblox 'back' (+Z) is Blender min Y)."""
    cx, cy, cz = [(a + b) / 2 for a, b in zip(lo, hi)]
    if name == "Head":
        return V((cx, lo[1], lo[2]))      # bottom back
    if name == "Tail":
        return V((cx, hi[1], cz))         # front end (-Z Roblox = +Y Blender)
    if name.startswith(("Arm", "Leg")):
        return V((cx, cy, hi[2]))         # top centre
    return V((cx, cy, cz))


def set_origin(ob):
    me = ob.data
    lo = [min(v.co[i] for v in me.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in me.vertices) for i in range(3)]
    piv = pivot_for(ob.name, lo, hi)
    me.transform(Matrix.Translation(-piv))
    ob.location = piv


def uv_and_bake(ob):
    size = TEX_SIZE.get(ob.name, 128) * (2 if DETAIL > 1 else 1)
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # --detail: a dense smooth mesh cut at 50 degrees makes many tiny islands that bleed at the game's 256 px re-bake; 80 keeps them big
    bpy.ops.uv.smart_project(angle_limit=math.radians(80 if DETAIL > 1 else 50), island_margin=0.03, area_weight=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new("Compy_V3_" + ob.name, size, size, alpha=False)
    mat = bpy.data.materials.new("Compy_V3_" + ob.name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(vc.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    nt.nodes.active = tex
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    bpy.ops.object.bake(type="EMIT", margin=12 if DETAIL > 1 else 6, use_clear=True)
    os.makedirs(TEX_DIR, exist_ok=True)
    path = os.path.join(TEX_DIR, "Compy_V3_%s.png" % ob.name)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    for n in (vc, em):
        nt.nodes.remove(n)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 1.0
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.0
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    img.pack()
    img.filepath_raw = "//textures/compy_v3/Compy_V3_%s.png" % ob.name  # relative to the .blend (public repo: no local paths)
    return path


# ------------------------------------------------------------------ render (same set-up as V2)


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 0.45
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.2
    sun.data.angle = math.radians(20)
    sun.rotation_euler = (math.radians(-45), 0, math.radians(-30))
    sc.collection.objects.link(sun)
    sc.render.resolution_x = 420
    sc.render.resolution_y = 420
    sc.render.film_transparent = True


def render(name, direction, scale=3.5, target=(0, -0.05, 1.5), elev=0.06, prefix="render"):
    sc = bpy.context.scene
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = scale
    cam = bpy.data.objects.new("cam_" + name, cam_data)
    sc.collection.objects.link(cam)
    d = V(direction).normalized()
    d.z += elev
    d.normalize()
    t = V(target)
    cam.location = t + d * 20
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    os.makedirs(RENDER_DIR, exist_ok=True)
    sc.render.filepath = os.path.join(RENDER_DIR, "%s-%s.png" % (prefix, name))
    bpy.ops.render.render(write_still=True)


def render_all(prefix="render"):
    render("front", (0, 1, 0), prefix=prefix)
    render("side", (1, 0, 0), prefix=prefix)
    render("back", (0, -1, 0), prefix=prefix)
    render("q34", (math.sin(math.radians(38)), math.cos(math.radians(38)), 0), prefix=prefix)


def body_weight(r, g, b):
    """Python copy of LowPolyRecolor.bodyWeight."""
    def smooth(x, a, b_):
        t = min(max((x - a) / (b_ - a), 0.0), 1.0)
        return t * t * (3 - 2 * t)
    mx, mn = max(r, g, b), min(r, g, b)
    if mx <= 0:
        return 0.0
    return smooth(mx, 0.2, 0.3) * smooth((mx - mn) / mx, 0.34, 0.44)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    bm = load_source()
    print("COMPY source faces %d (symmetric)" % len(bm.faces))
    eye_c, _ = flatten_eye_bumps(bm)
    parts = split_parts(bm)
    bm.free()
    objs = []
    for name in PARTS:
        ob = mesh_object(name, parts[name])
        parts[name].free()
        decimate(ob, BUDGET[name])
        objs.append(ob)
    head = next(o for o in objs if o.name == "Head")
    head_h = max(v.co.z for v in head.data.vertices) - min(v.co.z for v in head.data.vertices)
    add_eyes_and_nostrils(head, eye_c, head_h)
    for ob in objs:
        if ob.name.startswith("Leg"):
            add_claws(ob)
    for ob in objs:
        apply_colours(ob)
        set_origin(ob)
    if "--labels" in ARGS:
        setup_render()
        for ob in objs:
            mat = bpy.data.materials.new(ob.name)
            mat.use_nodes = True
            nt = mat.node_tree
            bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.layer_name = "Col"
            nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
            ob.data.materials.append(mat)
            ob.location += (ob.location - V((0, 0, 1.4))) * 0.25   # exploded view
        render_all(prefix="labels")
        render("feet", (0.35, 1, 0), scale=1.7, target=(0, 0, 0.35), prefix="labels")
        return
    for ob in objs:
        apply_shading(ob)
        uv_and_bake(ob)
    lo = [min((ob.matrix_world @ V(c))[i] for ob in objs for c in ob.bound_box) for i in range(3)]
    hi = [max((ob.matrix_world @ V(c))[i] for ob in objs for c in ob.bound_box) for i in range(3)]
    total = 0
    for ob in objs:
        t = tris_of(ob.data)
        total += t
        print("COMPY part %-5s tris %4d origin %s" % (ob.name, t, tuple(round(x, 3) for x in ob.location)))
    print("COMPY size studs x %.2f y(depth) %.2f z(height) %.2f; total tris %d" % (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], total))
    for nm, col in (("lime", LIME), ("cream", CREAM), ("eye", EYE), ("white", WHITE), ("claw", CLAW)):
        print("COMPY bodyWeight %-5s %.3f" % (nm, body_weight(*col[:3])))
    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT, compress=True)
    print("COMPY saved", os.path.relpath(BLEND_OUT, ROOT))
    if "--no-render" not in ARGS:
        setup_render()
        render_all()
        print("COMPY renders in", os.path.relpath(RENDER_DIR, ROOT))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("ERROR build failed")
    sys.exit(1)
