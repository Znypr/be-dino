"""Blender side of the sheet -> Hunyuan3D -> game dino route (BD-1304). Run through tools/hy_dino.py, which passes:

  blender -b --factory-startup --python tools/blender/hy_dino_blender.py -- --stage measure --src shape.glb --dir D
  ... --stage parts  --src shape.glb --dir D --config cfg.py   -> D/parts.blend (cut, capped, decimated, model space) + D/tips.json
  ... --stage colour --dir D --config cfg.py [--preview]        -> D/<NAME>.blend + D/textures + D/render-*.png
  ... --stage anim   --dir D --config cfg.py [--armored]        -> D/<NAME>_rigged.blend + D/frames/<clip>/*.png

Stages are split so a colour tweak reruns only 'colour' (seconds) instead of import, cut and decimate.
Colours: the sheet's side/front/back drawings (D/proj-<view>.png from tools/hy_dino.py sheet) are projected onto each part, weighted by
which way each face points, and baked (Cycles EMIT) into one texture per part. No vertex colours anywhere (Roblox multiplies them with
the texture, BD-1297). Optional per species: TOP (flat colour for up-facing faces no drawing shows), SPIKES (faceted cones at the
strongest stand-out points of the detailed mesh), REGIONS (forced colour by part and y range).
Animation: one bone per part at its pivot; actions from the game's own keys (src/shared/LowPolyClips.luau) with LowPolyGait's phase
rules, rendered to frames for GIFs.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector as V, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import hy_dino_lib as lib  # noqa: E402

A = sys.argv[sys.argv.index("--") + 1:]


def arg(name, default=None):
    return A[A.index(name) + 1] if name in A else default


STAGE, D = arg("--stage"), os.path.abspath(arg("--dir"))
SIZE = float(arg("--size", "3.0"))
cfg = {}
if arg("--config"):
    exec(open(arg("--config"), encoding="utf-8").read(), cfg)
os.makedirs(D, exist_ok=True)


def activate(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def hexlin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def load_hi(src):
    """Hunyuan mesh as one object, turned to face +Y, SIZE studs tall, feet on 0, centred on X."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    activate(meshes[0])
    for o in meshes:
        o.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    hi = bpy.context.active_object
    m = hi.matrix_world.copy()
    hi.parent = None
    hi.matrix_world = m
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in list(bpy.context.scene.objects):
        if o is not hi:
            bpy.data.objects.remove(o)
    hi.data.transform(Matrix.Rotation(math.radians(float(arg("--rot", cfg.get("ROT_DEG", 180)))), 4, "Z"))
    lo = [min(v.co[i] for v in hi.data.vertices) for i in range(3)]
    up = [max(v.co[i] for v in hi.data.vertices) for i in range(3)]
    s = SIZE / (up[2] - lo[2])
    hi.data.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(V((-(lo[0] + up[0]) / 2, 0, -lo[2]))))
    hi.data.update()
    hi.name = "HI"
    return hi


def smoothed_displacement(me, iters):
    bmx = bmesh.new()
    bmx.from_mesh(me)
    bmesh.ops.remove_doubles(bmx, verts=bmx.verts[:], dist=1e-5)
    bmx.verts.ensure_lookup_table()
    bmx.normal_update()
    co = [v.co.copy() for v in bmx.verts]
    sm = list(co)
    for _ in range(iters):
        sm = [(sm[v.index] + sum((sm[e.other_vert(v).index] for e in v.link_edges), V())) / (len(v.link_edges) + 1) for v in bmx.verts]
    out = [((co[v.index] - sm[v.index]).dot(v.normal), co[v.index].copy(), v.normal.copy()) for v in bmx.verts]
    bmx.free()
    return out


# ================================================================ measure
def stage_measure():
    import numpy as np
    hi = load_hi(arg("--src"))
    P = np.array([v.co[:] for v in hi.data.vertices])
    H = P[:, 2].max()
    ymin, ymax = float(P[:, 1].min()), float(P[:, 1].max())

    def yruns(z0, z1):
        Q = P[(P[:, 2] >= z0) & (P[:, 2] < z1)]
        if not len(Q):
            return []
        b = np.zeros(int((ymax - ymin) / 0.05) + 2, bool)
        b[((Q[:, 1] - ymin) / 0.05).astype(int)] = True
        return [(ymin + a * 0.05, ymin + e * 0.05) for a, e in lib.runs(list(b), min_len=2, gap=2)]
    feet = yruns(0, 0.25 * H / 3)
    legs = sorted(feet, key=lambda r: -r[0])            # front to back
    leg_top = 0.2 * H
    z = 0.1
    while z < 0.6 * H:                                   # first height where one run spans most of the length = the belly
        r = yruns(z, z + 0.08)
        if len(r) == 1 and (r[0][1] - r[0][0]) > 0.7 * (ymax - ymin):
            leg_top = z - 0.04
            break
        z += 0.04
    low = P[P[:, 2] < 0.15 * H]
    leg_inner = max(0.1, float(np.percentile(np.abs(low[:, 0]), 3)) - 0.05)
    # biped head: the narrowest cross-section between 45 % and 75 % of the height (the neck), head starts just above it
    widths = []
    for zz in np.arange(0.45 * H, 0.75 * H, 0.04):
        Q = P[(P[:, 2] >= zz) & (P[:, 2] < zz + 0.04)]
        if len(Q):
            widths.append((float(np.abs(Q[:, 0]).max()), float(zz)))
    head_z = (min(widths)[1] + 0.06) if widths else 0.6 * H
    a = {"size": [float(np.ptp(P[:, 0])), float(ymax - ymin), float(H)], "y": [ymin, ymax], "legs": [[round(x, 2) for x in r] for r in legs],
         "leg_top": round(float(leg_top), 2), "leg_inner": round(leg_inner, 2), "head_z": round(head_z, 2),
         "head_y": round((legs[0][1] + 0.1) if legs else ymax - 0.3 * (ymax - ymin), 2),
         "tail_y": round((legs[-1][0] - 0.4) if len(legs) > 1 else ((legs[0][0] - 0.05) if legs else ymin + 0.3 * (ymax - ymin)), 2)}
    json.dump(a, open(os.path.join(D, "anatomy.json"), "w"), indent=1)
    print("HY anatomy", json.dumps(a))


# ================================================================ parts
def stage_parts():
    hi = load_hi(arg("--src"))
    NAME, PARTS, BUDGET, CUTS, label = cfg["NAME"], cfg["PARTS"], cfg["BUDGET"], cfg["CUTS"], cfg["label"]
    detail = float(cfg.get("DETAIL", 4))
    # spike candidates from the detailed mesh (one side), saved for the colour stage
    sp = cfg.get("SPIKES")
    if sp:
        cands = [(d, tuple(c), tuple(n)) for d, c, n in smoothed_displacement(hi.data, sp.get("iters", 25))
                 if c.x >= 0 and c.z > sp.get("zmin", -99) and d > sp.get("floor", 0.05)]
        best = lib.select_tips(cands, sp.get("merge", 0.2), count=200)
        json.dump([[list(p), list(n)] for p, n in best], open(os.path.join(D, "tips.json"), "w"))
        print("HY spike candidates", len(best))
    bm = bmesh.new()
    bm.from_mesh(hi.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V(), plane_no=V((1, 0, 0)), clear_inner=True)
    for v in bm.verts:
        if abs(v.co.x) < 1e-4:
            v.co.x = 0.0
    bmesh.ops.mirror(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], axis="X", merge_dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for co, no, box in CUTS:
        for sgn in ((1, -1) if co[0] != 0 or (box and box[0][0] >= 0) else (1,)):
            pc = V((co[0] * sgn, co[1], co[2]))
            if box is None:
                faces = bm.faces[:]
            else:
                (x0, y0, z0), (x1, y1, z1) = box
                faces = [f for f in bm.faces if (lambda c: x0 <= (c.x * sgn if x0 >= 0 else c.x) <= x1 and y0 <= c.y <= y1 and z0 <= c.z <= z1)(f.calc_center_median())]
            if faces:
                bmesh.ops.bisect_plane(bm, geom=list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces,
                                       plane_co=pc, plane_no=V(no), dist=1e-5)
    bm.faces.ensure_lookup_table()
    labels = [label(f.calc_center_median()) for f in bm.faces]
    sc = bpy.context.scene
    for name in PARTS:
        pb = bm.copy()
        pb.faces.ensure_lookup_table()
        bmesh.ops.delete(pb, geom=[f for f, l in zip(pb.faces, labels) if l != name], context="FACES")
        bmesh.ops.delete(pb, geom=[v for v in pb.verts if not v.link_faces], context="VERTS")
        pb.faces.ensure_lookup_table()
        seen, islands = set(), []
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
        if not islands:
            print("HY ERROR part %s is empty: check the cut planes" % name)
            continue
        big = max(len(i) for i in islands)
        stray = [f for isl in islands if len(isl) < big * 0.05 for f in isl]
        if stray:
            bmesh.ops.delete(pb, geom=stray, context="FACES")
            bmesh.ops.delete(pb, geom=[v for v in pb.verts if not v.link_faces], context="VERTS")
        bnd = [e for e in pb.edges if e.is_boundary]
        if bnd:
            res = bmesh.ops.holes_fill(pb, edges=bnd, sides=0)
            bmesh.ops.triangulate(pb, faces=res["faces"])
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces[:])
        me = bpy.data.meshes.new(name)
        pb.to_mesh(me)
        pb.free()
        ob = bpy.data.objects.new(name, me)
        sc.collection.objects.link(ob)
        activate(ob)
        n = tris(me)
        target = BUDGET.get(name, 300) * detail
        if n > target:
            mod = ob.modifiers.new("dec", "DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = target / n
            mod.use_collapse_triangulate = True
            if abs(sum(v.co.x for v in me.vertices) / max(1, len(me.vertices))) < 0.05:
                mod.use_symmetry, mod.symmetry_axis = True, "X"
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bmd = bmesh.new()
        bmd.from_mesh(ob.data)
        bmesh.ops.triangulate(bmd, faces=[f for f in bmd.faces if len(f.verts) > 3])
        limit = math.radians(float(cfg.get("SMOOTH", 75)))
        for f in bmd.faces:
            f.smooth = True
        for e in bmd.edges:
            e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0) > limit)
        bmd.to_mesh(ob.data)
        bmd.free()
        print("HY part %-6s islands %d tris %d" % (name, len(islands), tris(ob.data)))
    bm.free()
    bpy.data.objects.remove(hi)
    bpy.context.scene.render.filepath = "//"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(D, "parts.blend"), compress=True)
    print("HY parts saved")


# ================================================================ colour
def math_node(nt, op, a=None, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def flat_material(name, colour, img):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = hexlin(colour)
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.nodes.active = t
    return m


def projection_material(name, imgs, img):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emis = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    acc_c = acc_w = None
    for view, image in imgs.items():
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "proj_" + view
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = image
        tn.extension = "EXTEND"
        nt.links.new(uvn.outputs["UV"], tn.inputs["Vector"])
        if view == "side":
            w = math_node(nt, "ABSOLUTE", sep.outputs["X"])
        else:
            w = math_node(nt, "MAXIMUM", math_node(nt, "MULTIPLY", sep.outputs["Y"], 1.0 if view == "front" else -1.0), 0.0)
        w = math_node(nt, "ADD", math_node(nt, "POWER", w, 3.0), {"side": 0.06, "front": 0.02, "back": 0.01}[view])
        cw = nt.nodes.new("ShaderNodeVectorMath")
        cw.operation = "SCALE"
        nt.links.new(tn.outputs["Color"], cw.inputs[0])
        nt.links.new(w, cw.inputs["Scale"])
        if acc_c is None:
            acc_c, acc_w = cw.outputs[0], w
        else:
            ac = nt.nodes.new("ShaderNodeVectorMath")
            ac.operation = "ADD"
            nt.links.new(acc_c, ac.inputs[0])
            nt.links.new(cw.outputs[0], ac.inputs[1])
            acc_c, acc_w = ac.outputs[0], math_node(nt, "ADD", acc_w, w)
    norm = nt.nodes.new("ShaderNodeVectorMath")
    norm.operation = "SCALE"
    nt.links.new(acc_c, norm.inputs[0])
    nt.links.new(math_node(nt, "DIVIDE", 1.0, acc_w), norm.inputs["Scale"])
    nt.links.new(norm.outputs[0], emis.inputs["Color"])
    nt.links.new(emis.outputs[0], out.inputs["Surface"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.nodes.active = t
    return m


def add_cones(me, tips, height, radius, sink, segs=5):
    bmx = bmesh.new()
    bmx.from_mesh(me)
    for c, n in tips:
        c, n = V(c), V(n).normalized()
        ref = V((0, 0, 1)) if abs(n.z) < 0.9 else V((1, 0, 0))
        u = n.cross(ref).normalized()
        w = n.cross(u).normalized()
        base = c - n * sink
        ring = [bmx.verts.new(base + (u * math.cos(2 * math.pi * i / segs) + w * math.sin(2 * math.pi * i / segs)) * radius) for i in range(segs)]
        apex = bmx.verts.new(c + n * height)
        for i in range(segs):
            f = bmx.faces.new((ring[i], ring[(i + 1) % segs], apex))
            f.smooth = False
        bmx.faces.new(list(reversed(ring))).smooth = False
    bmx.normal_update()
    bmx.to_mesh(me)
    bmx.free()


def uv_for(view, co, bmin, bmax):
    nx, ny, nz = [(co[i] - bmin[i]) / (bmax[i] - bmin[i]) for i in range(3)]
    if view == "side":
        return (ny, nz)
    if view == "front":
        return (1 - nx, nz)
    return (nx, nz)


def pivot_of(name, me):
    lo = [min(v.co[i] for v in me.vertices) for i in range(3)]
    up = [max(v.co[i] for v in me.vertices) for i in range(3)]
    cx, cy, cz = [(a + b) / 2 for a, b in zip(lo, up)]
    n = name.lower()
    if "head" in n:
        return V((cx, lo[1], lo[2]))
    if "tail" in n:
        return V((cx, up[1], cz))
    if any(k in n for k in ("arm", "leg", "wing")):
        return V((cx, cy, up[2]))
    return V((cx, cy, cz))


def render_views(parts, preview):
    sc = bpy.context.scene
    if preview:
        try:
            sc.render.engine = "BLENDER_EEVEE"
        except TypeError:
            pass
        sc.render.resolution_x = sc.render.resolution_y = 300
    else:
        sc.render.engine = "CYCLES"
        sc.cycles.samples = 48
        sc.render.resolution_x = sc.render.resolution_y = 420
    sc.view_settings.view_transform = "Standard"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 0.5
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.4
    sun.rotation_euler = (math.radians(-45), 0, math.radians(-30))
    sc.collection.objects.link(sun)
    sc.render.film_transparent = True
    lo = [min((o.matrix_world @ V(c))[i] for o in parts for c in o.bound_box) for i in range(3)]
    up = [max((o.matrix_world @ V(c))[i] for o in parts for c in o.bound_box) for i in range(3)]
    tgt = V([(a + b) / 2 for a, b in zip(lo, up)])
    span = max(up[i] - lo[i] for i in range(3)) * 1.15
    for nm, d in (("front", (0, 1, 0)), ("q34", (math.sin(math.radians(38)), math.cos(math.radians(38)), 0)), ("side", (1, 0, 0)), ("back", (0, -1, 0))):
        cd = bpy.data.cameras.new(nm)
        cd.type = "ORTHO"
        cd.ortho_scale = span
        cam = bpy.data.objects.new("cam_" + nm, cd)
        sc.collection.objects.link(cam)
        dv = V(d).normalized()
        dv.z += 0.08
        dv.normalize()
        cam.location = tgt + dv * 20
        cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
        sc.camera = cam
        sc.render.filepath = os.path.join(D, "render-%s.png" % nm)
        bpy.ops.render.render(write_still=True)



def find_eye(bmin, bmax):
    """Eye centre (y, z) and radius in model space from the side drawing: the dark pixels in the head's upper front corner."""
    import numpy as np
    path = os.path.join(D, "proj-side.png")
    if not os.path.exists(path):
        return None
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]   # row 0 = bottom
    bpy.data.images.remove(im)
    lum = px.mean(axis=2)
    vv, uu = np.mgrid[0:h, 0:w]
    u, v = uu / (w - 1), vv / (h - 1)
    dark = lum < 0.1
    # the eye = a white highlight with black all round it, in the head's upper half (the drawing's catchlight)
    white = (lum > 0.85) & (u > 0.4) & (v > 0.45)
    best, bestscore = None, 0
    k = max(4, int(min(w, h) * 0.03))
    for y0, x0 in zip(*np.where(white)):
        win = dark[max(0, y0 - k):y0 + k + 1, max(0, x0 - k):x0 + k + 1]
        score = win.mean()
        if score > bestscore:
            best, bestscore = (y0, x0), score
    if best is None or bestscore < 0.35:
        return None
    y0, x0 = best
    R = int(min(w, h) * 0.12)
    win = dark[max(0, y0 - R):y0 + R + 1, max(0, x0 - R):x0 + R + 1]
    ys, xs = np.where(win)
    ys, xs = ys + max(0, y0 - R), xs + max(0, x0 - R)
    cu, cv = xs.mean() / (w - 1), ys.mean() / (h - 1)
    ry = (np.percentile(xs, 95) - np.percentile(xs, 5)) / 2 / (w - 1) * (bmax[1] - bmin[1])
    rz = (np.percentile(ys, 95) - np.percentile(ys, 5)) / 2 / (h - 1) * (bmax[2] - bmin[2])
    return (float(bmin[1] + cu * (bmax[1] - bmin[1])), float(bmin[2] + cv * (bmax[2] - bmin[2])), float(max(0.06, 0.9 * min(ry, rz) + 0.1 * max(ry, rz))))


def add_eye_pieces(ob, y, z, r):
    """Glossy eye on both sides of the head: a flat black dome on the surface plus a white highlight up-front. Returns
    (first eye face, first highlight face, end) so the caller can colour them."""
    from mathutils.bvhtree import BVHTree
    me = ob.data
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    hits = []
    for s in (1, -1):
        hit = bvh.ray_cast(V((s * 5.0, y, z)), V((-s, 0, 0)))
        if hit[0] is not None:
            n = hit[1].normalized()
            if n.x * s < 0:
                n = -n
            hits.append((hit[0], n))
    bmx = bmesh.new()
    bmx.from_mesh(me)
    n0 = len(bmx.faces)

    def dome(c, n, rad, h, segs):
        ref = V((0, 0, 1)) if abs(n.z) < 0.9 else V((1, 0, 0))
        a = n.cross(ref).normalized()
        b = n.cross(a).normalized()
        ring0 = [bmx.verts.new(c - n * 0.02 + (a * math.cos(2 * math.pi * i / segs) + b * math.sin(2 * math.pi * i / segs)) * rad) for i in range(segs)]
        ring1 = [bmx.verts.new(c + n * h * 0.6 + (a * math.cos(2 * math.pi * i / segs) + b * math.sin(2 * math.pi * i / segs)) * rad * 0.75) for i in range(segs)]
        apex = bmx.verts.new(c + n * h)
        for i in range(segs):
            j = (i + 1) % segs
            bmx.faces.new((ring0[i], ring0[j], ring1[j], ring1[i])).smooth = True
            bmx.faces.new((ring1[i], ring1[j], apex)).smooth = True
        mid = bmx.verts.new(c - n * 0.02)
        for i in range(segs):
            bmx.faces.new((ring0[(i + 1) % segs], ring0[i], mid))
    for c, n in hits:
        dome(c, n, r, r * 0.35, 14)
    n1 = len(bmx.faces)
    for c, n in hits:
        up = (V((0, 0, 1)) - n * n.z).normalized()
        fwd = (V((0, 1, 0)) - n * n.y).normalized()
        dome(c + n * r * 0.33 + up * r * 0.38 + fwd * r * 0.2, n, r * 0.24, r * 0.08, 8)
    n2 = len(bmx.faces)
    bmx.to_mesh(me)
    bmx.free()
    return n0, n1, n2


def stage_colour():
    NAME = cfg["NAME"]
    bpy.ops.wm.open_mainfile(filepath=os.path.join(D, "parts.blend"))
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    sc.render.bake.use_selected_to_active = False
    sc.render.bake.margin = 6
    parts = [o for o in sc.objects if o.type == "MESH"]
    tex_dir = os.path.join(D, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    allv = [v.co for o in parts for v in o.data.vertices]
    bmin = [min(c[i] for c in allv) for i in range(3)]
    bmax = [max(c[i] for c in allv) for i in range(3)]
    views = cfg.get("PROJECT", {}).get("views", ["front", "side", "back"])
    imgs = {v: bpy.data.images.load(os.path.join(D, "proj-%s.png" % v)) for v in views}
    sp = cfg.get("SPIKES")
    tips = []
    if sp and os.path.exists(os.path.join(D, "tips.json")):
        raw = [(1.0, tuple(p), tuple(n)) for p, n in json.load(open(os.path.join(D, "tips.json")))]   # already strongest first
        chosen = []
        for _, p, n in raw:
            if any(lib._dist(p, q) <= sp.get("merge", 0.2) for q, _ in chosen):
                continue
            part = cfg["label"](V(p))
            if part in sp.get("exclude_parts", []):
                continue
            ex = sp.get("exclude_box")
            if ex and all(ex[0][i] <= p[i] <= ex[1][i] for i in range(3)):
                continue
            chosen.append((p, n))
            if len(chosen) >= sp.get("count", 14):
                break
        tips = lib.mirror_tips(chosen)
        print("HY spikes chosen %d (both sides)" % len(tips))
    bump_colour = cfg.get("BUMP_COLOUR", "#E6CFA0")
    top = cfg.get("TOP")
    eyes = cfg.get("EYES", "auto")
    eye = find_eye(bmin, bmax) if eyes == "auto" else (tuple(eyes) if eyes else None)
    print("HY eye", None if eye is None else tuple(round(x, 3) for x in eye))
    for ob in parts:
        name, me = ob.name, ob.data
        n_before = len(me.polygons)
        mine = [(p, n) for p, n in tips if cfg["label"](V(p)) == name]
        if mine:
            add_cones(me, mine, sp["height"], sp["radius"], sp.get("sink", 0.08))
        eye_faces = None
        if eye and name == "Head":
            bpy.context.view_layer.update()
            eye_faces = add_eye_pieces(ob, *eye)
        activate(ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")
        bake_uv = me.uv_layers[0].name
        for view in imgs:
            layer = me.uv_layers.new(name="proj_" + view)
            for poly in me.polygons:
                for li in poly.loop_indices:
                    layer.data[li].uv = uv_for(view, me.vertices[me.loops[li].vertex_index].co, bmin, bmax)
        me.uv_layers.active = me.uv_layers[bake_uv]
        size = 512 if name in ("Body", "Head") else 256
        img = bpy.data.images.new("%s_%s" % (NAME, name), size, size, alpha=False)
        me.materials.clear()
        me.materials.append(projection_material("%s_%s_proj" % (NAME, name), imgs, img))
        me.materials.append(flat_material("%s_%s_bump" % (NAME, name), bump_colour, img))
        for p_ in list(me.polygons)[n_before:(eye_faces[0] if eye_faces else len(me.polygons))]:
            p_.material_index = 1
        for reg in cfg.get("REGIONS", []):
            if reg["part"] == name:
                for p_ in me.polygons:
                    if reg.get("y_min", -99) < p_.center.y < reg.get("y_max", 99):
                        p_.material_index = 1
        if top and name in top.get("parts", ()):
            me.materials.append(flat_material("%s_%s_top" % (NAME, name), top["colour"], img))
            for p_ in me.polygons:
                if p_.material_index == 0 and p_.normal.z > top.get("min_nz", -1.0) and p_.center.z > top.get("zmin", -99):
                    p_.material_index = 2
        if eye_faces:
            e0, e1, e2 = eye_faces
            me.materials.append(flat_material("%s_eye" % NAME, cfg.get("EYE_COLOUR", "#10151A"), img))
            me.materials.append(flat_material("%s_glint" % NAME, "#FFFFFF", img))
            ki = len(me.materials) - 2
            for p_ in list(me.polygons)[e0:e1]:
                p_.material_index = ki
            for p_ in list(me.polygons)[e1:e2]:
                p_.material_index = ki + 1
        activate(ob)
        bpy.ops.object.bake(type="EMIT")
        img.filepath_raw = os.path.join(tex_dir, "%s_%s.png" % (NAME, name))
        img.file_format = "PNG"
        img.save()
        fm = bpy.data.materials.new("%s_%s" % (NAME, name))
        fm.use_nodes = True
        bsdf = next(n for n in fm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        t2 = fm.node_tree.nodes.new("ShaderNodeTexImage")
        t2.image = img
        fm.node_tree.links.new(t2.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.8
        me.materials.clear()
        me.materials.append(fm)
        for view in imgs:
            me.uv_layers.remove(me.uv_layers["proj_" + view])
        for a in list(me.color_attributes):
            me.color_attributes.remove(a)
        img.pack()
        img.filepath_raw = "//textures/%s_%s.png" % (NAME, name)
        piv = pivot_of(name, me)
        me.transform(Matrix.Translation(-piv))
        ob.location = piv
    for im in imgs.values():
        bpy.data.images.remove(im)
    print("HY parts %s total tris %d" % ({o.name: tris(o.data) for o in parts}, sum(tris(o.data) for o in parts)))
    sc.render.filepath = "//"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(D, "%s.blend" % NAME), compress=True)
    render_views(parts, "--preview" in A)
    print("HY colour done")


# ================================================================ anim (rig + game clips -> frames)
CLIPS = {
    "eat": (1.4, {"head": {"pitch": [(0, 0), (0.3, -26), (0.5, -17), (0.65, -26), (0.82, -17), (0.98, -24), (1.4, 0)], "roll": [(0, 0), (0.5, 4), (0.82, -4), (1.15, 0), (1.4, 0)], "fwd": [(0, 0), (0.3, 0.05), (0.98, 0.05), (1.4, 0)]},
                  "tail": {"yaw": [(0, 0), (0.4, 9), (0.7, -9), (1, 7), (1.4, 0)]}, "wing": {"roll": [(0, 0), (0.5, 8), (0.9, 0), (1.4, 0)]}}),
    "happy": (1.6, {"root": {"bob": [(0, 0), (0.3, 0.07), (0.48, 0), (0.74, 0.05), (0.9, 0), (1.6, 0)]},
                    "head": {"pitch": [(0, 0), (0.3, 12), (0.9, 8), (1.2, 10), (1.6, 0)], "roll": [(0, 0), (0.9, 0), (1.08, 9), (1.32, -6), (1.6, 0)]},
                    "tail": {"pitch": [(0, 0), (0.3, 10), (0.9, 6), (1.6, 0)], "yaw": [(0, 0), (0.15, 18), (0.3, -18), (0.45, 18), (0.6, -18), (0.75, 16), (0.9, -14), (1.1, 10), (1.3, -6), (1.6, 0)]},
                    "arm": {"pitch": [(0, 0), (0.3, -22), (0.9, -18), (1.3, 0), (1.6, 0)]},
                    "leg": {"pitch": [(0, 0), (0.3, 8), (0.48, 0), (0.74, 6), (0.9, 0), (1.6, 0)]},
                    "wing": {"roll": [(0, 0), (0.2, 40), (0.35, 15), (0.5, 40), (0.65, 15), (0.8, 34), (1.1, 0), (1.6, 0)]}}),
    "look": (3.0, {"head": {"pitch": [(0, 0), (0.6, 4), (1.8, 2), (3, 0)], "yaw": [(0, 0), (0.7, 18), (1.2, 21), (1.9, -14), (2.4, -17), (3, 0)], "roll": [(0, 0), (0.7, 4), (1.2, 5), (1.9, -3), (2.4, -4), (3, 0)]},
                   "tail": {"yaw": [(0, 0), (0.8, -8), (1.6, 8), (2.4, -6), (3, 0)]}}),
    "jump": (0.6, {"head": {"pitch": [(0, 0), (0.15, 9), (0.35, 6), (0.6, 0)]}, "tail": {"pitch": [(0, 0), (0.18, 12), (0.6, 0)]},
                   "arm": {"pitch": [(0, 0), (0.15, -12), (0.6, 0)]}}),
    "land": (0.6, {"head": {"pitch": [(0, 0), (0.18, -6), (0.38, 2), (0.6, 0)]}, "tail": {"pitch": [(0, 0), (0.18, 7), (0.38, -3), (0.6, 0)], "yaw": [(0, 0), (0.22, 4), (0.42, -2), (0.6, 0)]},
                   "arm": {"pitch": [(0, 0), (0.18, 5), (0.6, 0)]}}),
}
GAITS = {
    "idle": (4.0, 4.0, {"root": {"bob": [(0, 0), (2, 0.01), (4, 0)]},
                        "head": {"pitch": [(0, 0), (1.2, 2.5), (2.6, -1.5), (4, 0)], "yaw": [(0, 0), (1, 2), (3, -2), (4, 0)], "roll": [(0, -2), (2, 2), (4, -2)]},
                        "tail": {"pitch": [(0, 0), (2, 2.5), (4, 0)], "yaw": [(0, -7), (2, 7), (4, -7)]}, "arm": {"pitch": [(0, 0), (2, -3), (4, 0)]}}),
    "walk": (1.0, 0.9, {"root": {"bob": [(0, 0), (0.28, 0.02), (0.5, 0), (0.78, 0.02), (1, 0)]},
                        "head": {"pitch": [(0, -2), (0.28, 1.5), (0.5, -2), (0.78, 1.5), (1, -2)], "roll": [(0, -2.5), (0.5, 2.5), (1, -2.5)], "fwd": [(0, 0), (0.15, 0.025), (0.4, 0), (0.65, 0.025), (0.9, 0), (1, 0)]},
                        "tail": {"pitch": [(0, 2), (0.35, 4), (0.5, 2), (0.85, 4), (1, 2)], "yaw": [(0, -9), (0.1, -11), (0.6, 11), (1, -9)]},
                        "arm": {"pitch": [(0, -12), (0.5, 12), (1, -12)]}, "leg": {"pitch": [(0, 24), (0.3, 2), (0.6, -24), (0.8, 6), (1, 24)]}}),
    "run": (1.0, 0.55, {"root": {"bob": [(0, 0), (0.22, 0.035), (0.5, 0), (0.72, 0.035), (1, 0)]},
                        "head": {"pitch": [(0, -7), (0.25, -3), (0.5, -7), (0.75, -3), (1, -7)], "roll": [(0, -3), (0.5, 3), (1, -3)], "fwd": [(0, 0.03), (0.25, 0.045), (0.5, 0.03), (0.75, 0.045), (1, 0.03)]},
                        "tail": {"pitch": [(0, -6), (0.3, -9), (0.5, -6), (0.8, -9), (1, -6)], "yaw": [(0, -12), (0.1, -14), (0.6, 14), (1, -12)]},
                        "arm": {"pitch": [(0, -26), (0.5, -2), (1, -26)]}, "leg": {"pitch": [(0, 28), (0.45, -28), (0.6, -16), (0.8, 16), (1, 28)]}}),
}
SIDE_ROLL = {"wing", "flipper", "arm"}


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
        (ta, va), (tb, vb), (tc, vc) = keys[j - 1], keys[j], keys[j + 1]
        if (vb - va) * (vc - vb) <= 0:
            return 0.0
        cap = 3 * min(abs((vb - va) / (tb - ta)), abs((vc - vb) / (tc - tb)))
        return max(-cap, min(cap, (vc - va) / (tc - ta)))
    (t0, v0), (t1, v1) = keys[i], keys[i + 1]
    h = t1 - t0
    m0, m1, u = slope(i), slope(i + 1), (t - t0) / h
    return (2 * u ** 3 - 3 * u ** 2 + 1) * v0 + (u ** 3 - 2 * u ** 2 + u) * h * m0 + (-2 * u ** 3 + 3 * u ** 2) * v1 + (u ** 3 - u ** 2) * h * m1


def cyclic(keys, length, t):
    n = len(keys)
    t = t % length
    i = 0
    while i < n - 2 and keys[i + 1][0] <= t:
        i += 1

    def at(j):
        if j < 0:
            return keys[n - 1 + j][0] - length, keys[n - 1 + j][1]
        if j > n - 1:
            return keys[j - n + 1][0] + length, keys[j - n + 1][1]
        return keys[j]

    def slope(j):
        (ta, va), (tb, vb), (tc, vc) = at(j - 1), at(j), at(j + 1)
        if (vb - va) * (vc - vb) <= 0:
            return 0.0
        cap = 3 * min(abs((vb - va) / (tb - ta)), abs((vc - vb) / (tc - tb)))
        return max(-cap, min(cap, (vc - va) / (tc - ta)))
    (t0, v0), (t1, v1) = keys[i], keys[i + 1]
    h = t1 - t0
    if h <= 0:
        return v0
    m0, m1, u = slope(i), slope(i + 1), (t - t0) / h
    return (2 * u ** 3 - 3 * u ** 2 + 1) * v0 + (u ** 3 - 2 * u ** 2 + u) * h * m0 + (-2 * u ** 3 + 3 * u ** 2) * v1 + (u ** 3 - u ** 2) * h * m1


def role_of(name):
    n = name.lower()
    for key, role in (("head", "head"), ("tail", "tail"), ("wing", "wing"), ("neck", "neck"), ("arm", "arm"), ("leg", "leg"), ("body", "body")):
        if key in n:
            return role
    return None


def stage_anim():
    NAME = cfg["NAME"]
    armored = "--armored" in A or cfg.get("CLASS") == "Armored"
    fps, step = 24, int(arg("--step", "2"))
    bpy.ops.wm.open_mainfile(filepath=os.path.join(D, "%s.blend" % NAME))
    sc = bpy.context.scene
    parts = [o for o in sc.objects if o.type == "MESH"]
    for o in list(sc.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
    lo = [min((o.matrix_world @ V(c))[i] for o in parts for c in o.bound_box) for i in range(3)]
    up = [max((o.matrix_world @ V(c))[i] for o in parts for c in o.bound_box) for i in range(3)]
    height = up[2] - lo[2]
    centre = V([(a + b) / 2 for a, b in zip(lo, up)])
    ad = bpy.data.armatures.new("DinoRig")
    rig = bpy.data.objects.new("DinoRig", ad)
    sc.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    root = ad.edit_bones.new("root")
    root.head, root.tail = V((centre.x, centre.y, 0)), V((centre.x, centre.y + 0.6, 0))
    info = {}
    for o in parts:
        b = ad.edit_bones.new(o.name)
        b.head, b.tail, b.parent = o.location.copy(), o.location + V((0, 0.4, 0)), root
        side = -1 if (o.name.endswith("L") or o.location.x < -0.05) else 1
        lead = not (o.name.startswith("Leg") and len(o.name) == 5 and o.name[3] == "B")
        info[o.name] = (role_of(o.name), side, lead)
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in parts:
        mw = o.matrix_world.copy()
        o.parent, o.parent_type, o.parent_bone = rig, "BONE", o.name
        o.matrix_world = mw
    rig.animation_data_create()
    acts = {}
    for clip, cyc in [(c, False) for c in CLIPS] + [(g, True) for g in GAITS]:
        act = bpy.data.actions.new(clip)
        act.use_fake_user = True
        rig.animation_data.action = act
        length, secs, tracks = (GAITS[clip] if cyc else (CLIPS[clip][0], CLIPS[clip][0], CLIPS[clip][1]))
        frames = int(round(secs * fps))
        f = (lambda k, tt: cyclic(k, length, tt)) if cyc else hermite
        for fr in range(frames + 1):
            t = fr / frames * length
            bob = f(tracks["root"]["bob"], t) if "root" in tracks else 0.0
            if cyc:
                bob = max(0.0, min(0.04, bob))
            for name, (role, side, lead) in info.items():
                u = t
                if cyc and clip != "idle":
                    u = t + ((((0 if side < 0 else 0.5) + (0 if lead else 0.5)) % 1) if role == "leg" else ((0 if side < 0 else 0.5) if role == "arm" else 0))
                tr = tracks.get(role) or {}
                d = math.pi / 180
                pitch = f(tr["pitch"], u) * d if "pitch" in tr else 0.0
                yaw = f(tr["yaw"], u) * d if "yaw" in tr else 0.0
                roll = f(tr["roll"], u) * d if "roll" in tr else 0.0
                if role in SIDE_ROLL and side < 0:
                    roll = -roll
                fwd = f(tr["fwd"], u) if ("fwd" in tr and role == "head") else 0.0
                if role == "leg" and armored:
                    pitch *= 0.8
                c9 = lambda x: max(-0.9, min(0.9, x))
                pb = rig.pose.bones[name]
                pb.rotation_mode = "XYZ"
                pb.rotation_euler = Euler((c9(pitch), c9(roll), c9(yaw)), "XYZ")
                pb.location = V((0, fwd * height, 0))
                pb.keyframe_insert("rotation_euler", frame=fr + 1)
                pb.keyframe_insert("location", frame=fr + 1)
            rb = rig.pose.bones["root"]
            rb.location = V((0, 0, bob * height))
            rb.keyframe_insert("location", frame=fr + 1)
        acts[clip] = (act, frames + 1)
    rig.animation_data.action = None
    sc.render.filepath = "//"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(D, "%s_rigged.blend" % NAME), compress=True)
    # frames: EEVEE, 3/4 view, camera fitted to the whole body plus the swing room of every clip
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    sc.render.resolution_x = sc.render.resolution_y = 400
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value, bg.inputs[1].default_value = (0.62, 0.66, 0.70, 1), 0.8
    sc.view_settings.view_transform = "Standard"
    for nm, rot, e in (("Key", (48, 8, 30), 3.4), ("Fill", (65, 0, -115), 0.8), ("Rim", (105, 0, 175), 2.0)):
        ld = bpy.data.lights.new(nm, "SUN")
        ld.energy = e
        lo_ = bpy.data.objects.new(nm, ld)
        sc.collection.objects.link(lo_)
        lo_.rotation_euler = [math.radians(a) for a in rot]
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    gm = bpy.data.materials.new("Ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.36, 0.55, 0.25, 1)
    bpy.context.active_object.data.materials.append(gm)
    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO"
    cd.ortho_scale = max(up[1] - lo[1], up[2] - lo[2]) * 1.6
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    dv = V((math.sin(math.radians(40)), math.cos(math.radians(40)), 0.32)).normalized()
    tgt = V((centre.x, centre.y, height * 0.55))
    cam.location = tgt + dv * 40
    cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
    for clip, (act, n) in acts.items():
        rig.animation_data.action = act
        fd = os.path.join(D, "frames", clip)
        os.makedirs(fd, exist_ok=True)
        for k, fr in enumerate(range(1, n + 1, step)):
            sc.frame_set(fr)
            sc.render.filepath = os.path.join(fd, "f%03d.png" % k)
            bpy.ops.render.render(write_still=True)
    print("HY anim done", {k: v[1] for k, v in acts.items()})


{"measure": stage_measure, "parts": stage_parts, "colour": stage_colour, "anim": stage_anim}[STAGE]()
