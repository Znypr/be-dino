"""Compy, modelled in Blender for the game's rigid-part animator (BD-1291 compare to the Hunyuan V3). Headless Blender only, CPU.

  python tools/blender/build_compy_blender.py               # model + textures + .blend + Cycles CPU renders (render-<view>.png)
  python tools/blender/build_compy_blender.py --no-render

Same sheet as V3 (docs/evidence/2026-11-22-dino-ranking/compy-sheet-v1.jpg; proportions read off a 0.25-stud grid laid over its side and
front views, V3's part boxes as a size check), same 7 part names, colours, eyes, nostrils, claws, texture bake and 3.0 studs height.
Not a Hunyuan cleanup: every shape is placed here (rounded-box / ellipsoid "superellipsoid" blobs, convex hulls for tapered limbs),
fused per part with a voxel remesh, softened, decimated to a faceted-soft low-poly look.

Built FOR LowPolyAnimator (rigid parts welded to the root, each turned about LowPolyAnimator.pivotFor of its BOUNDING BOX):
  * every joint is a ball-in-socket: the child's root end is a half ball whose FLAT face centre is the joint, buried inside the body
    (shoulders, hips, tail root), so the game's pivot (arm / leg top centre, tail front end) is the centre of that ball and the visible
    surface of the limb turns about the real joint; the head is a closed skull sitting on a neck that rises well inside it (the head's
    box bottom-back corner, the game's head pivot, is on the back of the neck where it enters the skull);
  * no flat cut between neighbours shows: parts overlap generously, so turning a part shows more of its own or its neighbour's skin,
    never a hole or a cut face;
  * where the limb's own shape would put the box centre off the joint (feet and hands reach forward), a tiny hidden "pivot anchor"
    (a 1 cm tetrahedron buried inside the body) extends the box so its top centre lands exactly on the joint. Printed and checked.
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

sys.path.insert(0, HERE)
import build_compy_v3 as v3  # noqa: E402  (helpers: disc, shell, eyes / nostrils, claws, render, bodyWeight)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
V = Vector
NAME = "Compy_Blender"
BLEND_OUT = os.path.join(ROOT, "assets", "blender", "creatures", NAME + ".blend")
TEX_REL = "textures/compy_blender"
TEX_DIR = os.path.join(ROOT, "assets", "blender", "creatures", *TEX_REL.split("/"))
RENDER_DIR = os.path.join(ROOT, "docs", "evidence", "2026-11-22-compy-blender-compare", "blender")
PARTS = v3.PARTS
LIME, CREAM, CLAW = v3.LIME, v3.CREAM, v3.CLAW
CAP_TAG = v3.CAP_TAG
ANCHOR_TAG = 6        # the hidden pivot anchors (lime, buried); tools/blender/preview_lowpoly_anim.py skips them
TEX_SIZE = {"Body": 256, "Head": 256}
BUDGET = {"Body": 480, "Head": 300, "Tail": 140, "ArmL": 90, "ArmR": 90, "LegL": 200, "LegR": 200}
SMOOTH_DEG = 15.0     # smooth shading inside a facet group, hard edges where facets meet at more than this (faceted-soft, like the sheet)
VOXEL = 0.022
DISSOLVE_DEG = 6.0    # near-flat neighbours merge into one facet (bold planes like the sheet, not a dense smooth blob)

# ------------------------------------------------------------------ joints (model space: faces +Y, feet on z 0, 3.0 tall; +X = right)
HIP = V((0.36, -0.20, 1.17))       # right hip (mirrored for the left): top centre of the leg box
SHOULDER = V((0.24, 0.28, 1.33))   # right shoulder: top centre of the arm box
TAIL_ROOT = V((0.0, -0.36, 1.22))  # tail joint: front-end centre of the tail box
HIP_R, SHOULDER_R, TAIL_R = 0.18, 0.10, 0.30   # half-ball radii (buried in the body)


# ------------------------------------------------------------------ shape kit


def superellipsoid(c, half, e=1.0, seg=20, rings=12):
    """Points of a superellipsoid: e = 1 ellipsoid, e < 1 rounder box. c centre, half = half sizes."""
    pts = []
    f = lambda w: math.copysign(abs(w) ** e, w)  # noqa: E731
    for i in range(1, rings):
        v = -math.pi / 2 + math.pi * i / rings
        for j in range(seg):
            u = 2 * math.pi * j / seg
            pts.append(V((c[0] + half[0] * f(math.cos(v)) * f(math.cos(u)), c[1] + half[1] * f(math.cos(v)) * f(math.sin(u)),
                          c[2] + half[2] * f(math.sin(v)))))
    pts.append(V((c[0], c[1], c[2] - half[2])))
    pts.append(V((c[0], c[1], c[2] + half[2])))
    return pts


def blob(bm, c, half, e=1.0):
    """A closed superellipsoid solid (convex: built as the hull of its points)."""
    hull(bm, superellipsoid(c, half, e))


def ball(c, r, seg=16, rings=10):
    return superellipsoid(c, (r, r, r), 1.0, seg, rings)


def hull(bm, pts):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs)
    drop = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
    bmesh.ops.delete(bm, geom=list(drop), context="VERTS")


def obj_from(name, bm):
    ob = v3.mesh_object(name, bm)
    bm.free()
    return ob


def fuse(ob, budget, smooth_iter=6):
    """Voxel remesh (union of the overlapping blobs), soften the creases, decimate to the budget, merge near-flat facets."""
    v3.activate(ob)
    m = ob.modifiers.new("remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = VOXEL
    m.adaptivity = 0.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    m = ob.modifiers.new("smooth", "SMOOTH")
    m.factor = 0.6
    m.iterations = smooth_iter
    bpy.ops.object.modifier_apply(modifier=m.name)
    m = ob.modifiers.new("dec", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = min(1.0, budget / max(1, v3.tris_of(ob.data)))
    m.use_collapse_triangulate = True
    if ob.name in ("Body", "Head", "Tail"):
        m.use_symmetry = True
        m.symmetry_axis = "X"
    bpy.ops.object.modifier_apply(modifier=m.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(DISSOLVE_DEG), use_dissolve_boundaries=False, verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()


def cut(ob, co, no):
    """Cut the part with a plane and keep the side behind the normal; cap the opening flat (the buried half-ball face)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    tag = bm.faces.layers.int.get("tag") or bm.faces.layers.int.new("tag")
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True, dist=1e-5)
    bnd = [e for e in bm.edges if e.is_boundary]
    res = bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
    tri = bmesh.ops.triangulate(bm, faces=res["faces"])
    for f in tri["faces"]:
        f[tag] = CAP_TAG
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def mirror_x(ob, name):
    me = ob.data.copy()
    me.transform(Matrix.Scale(-1, 4, V((1, 0, 0))))
    me.flip_normals()
    new = bpy.data.objects.new(name, me)
    me.name = name
    bpy.context.scene.collection.objects.link(new)
    return new


# ------------------------------------------------------------------ parts


def build_body():
    bm = bmesh.new()
    blob(bm, (0, -0.14, 1.15), (0.47, 0.60, 0.50), 0.85)    # torso
    blob(bm, (0, -0.06, 0.86), (0.36, 0.42, 0.32), 0.9)     # belly (narrow: the thighs show beside it)
    blob(bm, (0, 0.17, 1.31), (0.40, 0.30, 0.38), 0.85)     # chest
    for s in (1, -1):                                       # hip sockets: flanks the thigh tops sit in
        blob(bm, (s * 0.31, -0.20, 1.18), (0.29, 0.33, 0.25), 0.9)
    blob(bm, (0, -0.66, 1.24), (0.32, 0.26, 0.28), 1.0)     # tail base taper
    blob(bm, (0, 0.02, 1.60), (0.36, 0.38, 0.24), 0.9)      # neck base: thick, the back slopes into the shoulders
    hull(bm, superellipsoid((0, 0.13, 1.55), (0.34, 0.31, 0.20), 0.9) + superellipsoid((0, 0.20, 2.12), (0.29, 0.26, 0.20), 0.9))  # neck
    ob = obj_from("Body", bm)
    fuse(ob, BUDGET["Body"])
    return ob


def build_head():
    bm = bmesh.new()
    # one convex block like the sheet: wide skull at eye height, narrower crown, snout lower and narrower with a flat front
    hull(bm, superellipsoid((0, 0.40, 2.50), (0.62, 0.46, 0.40), 0.7) + superellipsoid((0, 0.40, 2.86), (0.46, 0.44, 0.14), 0.8)
         + superellipsoid((0, 1.10, 2.36), (0.42, 0.36, 0.29), 0.55) + superellipsoid((0, 0.62, 2.06), (0.50, 0.58, 0.20), 0.7)
         + superellipsoid((0, 0.16, 2.05), (0.40, 0.22, 0.20), 0.8))
    ob = obj_from("Head", bm)
    fuse(ob, BUDGET["Head"])
    return ob


def build_tail():
    bm = bmesh.new()
    hull(bm, superellipsoid(TAIL_ROOT, (TAIL_R, TAIL_R, TAIL_R), 1.0) + superellipsoid((0, -0.88, 1.22), (0.27, 0.25, 0.31), 0.9)
         + ball((0, -1.58, 1.47), 0.04, 8, 5))
    ob = obj_from("Tail", bm)
    fuse(ob, BUDGET["Tail"], smooth_iter=3)
    cut(ob, TAIL_ROOT, V((0, 1, 0)))                         # keep the back half of the root ball: flat face centre = joint
    return ob


def build_leg():
    bm = bmesh.new()
    h = HIP
    # drumstick thigh flaring out below the buried hip ball, shin down the back, long foot forward
    hull(bm, superellipsoid(h, (HIP_R, HIP_R, HIP_R), 1.0) + superellipsoid((h.x + 0.06, h.y - 0.08, 0.88), (0.25, 0.32, 0.30), 0.75))
    hull(bm, ball((h.x + 0.05, h.y - 0.15, 0.64), 0.21) + ball((h.x + 0.04, h.y - 0.18, 0.24), 0.185))
    blob(bm, (h.x + 0.04, h.y + 0.0, 0.125), (0.20, 0.40, 0.125), 0.55)
    ob = obj_from("LegR", bm)
    fuse(ob, BUDGET["LegR"], smooth_iter=4)
    cut(ob, h, V((0, 0, 1)))                                 # keep below the hip: flat top centre = joint
    return ob


def build_arm():
    bm = bmesh.new()
    s = SHOULDER
    elbow = V((s.x + 0.19, s.y + 0.14, s.z - 0.23))
    hand = V((s.x + 0.12, s.y + 0.36, s.z - 0.27))
    hull(bm, ball(s, SHOULDER_R) + ball(elbow, 0.12))        # upper arm
    hull(bm, ball(elbow, 0.115) + superellipsoid(hand, (0.115, 0.12, 0.13), 0.8))  # forearm and stubby hand
    ob = obj_from("ArmR", bm)
    fuse(ob, BUDGET["ArmR"], smooth_iter=3)
    cut(ob, s, V((0, 0, 1)))
    return ob


# ------------------------------------------------------------------ details


def add_spikes(ob, ys, height, base, lean=0.35):
    """Small dorsal spikes along the top centre line (ray cast down onto this part), leaning back like the sheet's crest."""
    me = ob.data
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag") or bm.faces.layers.int.new("tag")
    for y in ys:
        hit = bvh.ray_cast(V((0, y, 4.0)), V((0, 0, -1)))
        if hit[0] is None:
            continue
        c, n = hit[0], hit[1].normalized()
        if n.z < 0:
            n = -n
        ring = v3.disc(c - n * 0.03, n, base, 4, roll=math.pi / 4)
        apex = c + n * height + V((0, -lean * height, 0))
        v3.shell(bm, tag, [ring], 0, apex=apex)
    v3.finish_shells(bm)
    bm.to_mesh(me)
    bm.free()


def add_anchor(ob, p, size=0.012):
    """Hidden pivot anchor: a tiny closed tetrahedron (lime) at p, buried in the body."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    tag = bm.faces.layers.int.get("tag") or bm.faces.layers.int.new("tag")
    vs = [bm.verts.new(p + V(d) * size) for d in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))]
    for f in ((0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)):
        bm.faces.new([vs[i] for i in f])[tag] = ANCHOR_TAG
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[-4:])
    bm.to_mesh(ob.data)
    bm.free()


def box(ob):
    ws = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return V([min(w[i] for w in ws) for i in range(3)]), V([max(w[i] for w in ws) for i in range(3)])


def center_on_joint(ob, joint, axis):
    """Add an anchor (just inside the top / front face, buried in the body) so the box centre on `axis` (1 = y, 2 = z) equals the joint."""
    lo, hi = box(ob)
    want = joint[axis]
    if abs((lo[axis] + hi[axis]) / 2 - want) < 0.004:
        return None
    p = joint.copy()
    p[axis] = 2 * want - hi[axis] if hi[axis] - want > want - lo[axis] else 2 * want - lo[axis]
    if ob.name.startswith(("Leg", "Arm")):
        p.z = joint.z - 0.02
        p.x = joint.x - math.copysign(0.14, joint.x)   # toward the body centre (still inside the limb's x range)
    else:
        p.y = joint.y - 0.02
    p[axis] += 0.012 if p[axis] < want else -0.012   # the tetra's own size
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


def colour_for(name, c, n, tag):
    if tag in v3.TAG_COL:
        return v3.TAG_COL[tag]
    if tag in (CAP_TAG, ANCHOR_TAG):
        return LIME
    if name == "Body":
        ny = 0.40 if c.z < 1.45 else 0.10
        w = 0.08 + (c.z - 0.55) / 0.45 * 0.18 if c.z < 1.0 else 0.27
        if n.y > ny and abs(c.x) < w and c.z > 0.55 and c.y > -0.05 and c.z < 2.0:
            return CREAM
    if name == "Tail" and n.z < -0.30 and c.y > -1.45:
        return CREAM
    return LIME


def apply_colours(ob):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    tag = bm.faces.layers.int.get("tag")
    bm.normal_update()
    cols = [colour_for(ob.name, f.calc_center_median(), f.normal, f[tag] if tag else 0) for f in bm.faces]
    bm.faces.ensure_lookup_table()
    soft = [not (tag and (f[tag] in v3.TAG_COL or f[tag] in (CAP_TAG, ANCHOR_TAG))) for f in bm.faces]
    area = [f.calc_area() for f in bm.faces]
    for _ in range(3):   # majority vote along the lime / cream border (no lone triangles)
        nxt = list(cols)
        for f in bm.faces:
            if not soft[f.index]:
                continue
            votes = {LIME: 0.0, CREAM: 0.0}
            for g in [f] + [g for e in f.edges for g in e.link_faces if g is not f]:
                if soft[g.index] and cols[g.index] in votes:
                    votes[cols[g.index]] += area[g.index]
            nxt[f.index] = LIME if votes[LIME] >= votes[CREAM] else CREAM
        cols = nxt
    bm.free()
    attr = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for poly, col in zip(me.polygons, cols):
        for li in poly.loop_indices:
            attr.data[li].color_srgb = col


def apply_shading(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lim = math.radians(SMOOTH_DEG)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0) > lim)
    bm.to_mesh(ob.data)
    bm.free()


def uv_and_bake(ob):
    size = TEX_SIZE.get(ob.name, 128)
    v3.activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(80), island_margin=0.03, area_weight=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new("%s_%s" % (NAME, ob.name), size, size, alpha=False)
    mat = bpy.data.materials.new("%s_%s" % (NAME, ob.name))
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
    bpy.ops.object.bake(type="EMIT", margin=8, use_clear=True)
    os.makedirs(TEX_DIR, exist_ok=True)
    path = os.path.join(TEX_DIR, "%s_%s.png" % (NAME, ob.name))
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
    img.filepath_raw = "//%s/%s_%s.png" % (TEX_REL, NAME, ob.name)  # relative to the .blend (public repo: no local paths)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    body, head, tail = build_body(), build_head(), build_tail()
    leg_r, arm_r = build_leg(), build_arm()
    global HIP, SHOULDER, TAIL_ROOT
    zs = [v.co.z for o in (body, head, tail, leg_r, arm_r) for v in o.data.vertices]
    k = 3.0 / (max(zs) - min(zs))
    for o in (body, head, tail, leg_r, arm_r):
        o.data.transform(Matrix.Translation(V((0, 0, -min(zs) * k))) @ Matrix.Scale(k, 4))
    HIP, SHOULDER, TAIL_ROOT = [V((p.x * k, p.y * k, (p.z - min(zs)) * k)) for p in (HIP, SHOULDER, TAIL_ROOT)]
    print("COMPY scaled by %.4f to 3.0 studs" % k)
    head_h = box(head)[1].z - box(head)[0].z
    v3.EYE_H_SHARE = 0.33
    v3.NOSTRIL_X, v3.NOSTRIL_Z = 0.17, 2.40
    v3.add_eyes_and_nostrils(head, (0.68, 2.52), head_h)
    add_spikes(body, [-0.12, -0.28, -0.44, -0.60], 0.085, 0.06)
    add_spikes(tail, [-0.80, -1.00, -1.20, -1.38], 0.08, 0.055)
    v3.add_claws(leg_r)
    leg_l, arm_l = mirror_x(leg_r, "LegL"), mirror_x(arm_r, "ArmL")
    objs = {o.name: o for o in (body, head, tail, arm_l, arm_r, leg_l, leg_r)}
    # pivot anchors (feet and hands reach forward, tail spikes raise the top) + check the box joints land on the designed joints
    body_tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    for name, joint, axis in (("LegR", HIP, 1), ("LegL", V((-HIP.x, HIP.y, HIP.z)), 1), ("ArmR", SHOULDER, 1),
                              ("ArmL", V((-SHOULDER.x, SHOULDER.y, SHOULDER.z)), 1), ("Tail", TAIL_ROOT, 2)):
        p = center_on_joint(objs[name], joint, axis)
        if p is not None:
            print("COMPY anchor %-4s at (%.3f %.3f %.3f) inside body: %s" % (name, p.x, p.y, p.z, inside(body_tree, p)))
    for name, ob in objs.items():
        lo, hi = box(ob)
        piv = v3.pivot_for(name, lo, hi)
        print("COMPY joint %-4s box pivot (%.3f %.3f %.3f)" % (name, piv.x, piv.y, piv.z))
    for ob in objs.values():
        apply_colours(ob)
        v3.set_origin(ob)
    total = 0
    for name in PARTS:
        ob = objs[name]
        apply_shading(ob)
        uv_and_bake(ob)
        t = v3.tris_of(ob.data)
        total += t
        print("COMPY part %-4s tris %4d origin %s" % (name, t, tuple(round(x, 3) for x in ob.location)))
    lo = [min((ob.matrix_world @ V(c))[i] for ob in objs.values() for c in ob.bound_box) for i in range(3)]
    hi = [max((ob.matrix_world @ V(c))[i] for ob in objs.values() for c in ob.bound_box) for i in range(3)]
    print("COMPY size studs x %.2f y(depth) %.2f z(height) %.2f; total tris %d" % (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], total))
    for nm, col in (("lime", LIME), ("cream", CREAM), ("claw", CLAW)):
        print("COMPY bodyWeight %-5s %.3f" % (nm, v3.body_weight(*col[:3])))
    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT, compress=True)
    print("COMPY saved", os.path.relpath(BLEND_OUT, ROOT))
    if "--no-render" not in ARGS:
        v3.RENDER_DIR = RENDER_DIR
        v3.setup_render()
        v3.render_all()
        print("COMPY renders in", os.path.relpath(RENDER_DIR, ROOT))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("ERROR build failed")
    sys.exit(1)
