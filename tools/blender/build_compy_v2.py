"""Compy V2 game model builder (BD-1291 step 3). Headless Blender only (never the MCP or a GUI Blender).

  python tools/blender/build_compy_v2.py                 # launches headless Blender at below-normal priority with this file
  python tools/blender/build_compy_v2.py --no-render     # model + textures + .blend only
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python tools/blender/build_compy_v2.py -- [--no-render]

Source: the owner-approved ChatGPT sheet docs/evidence/2026-11-22-dino-ranking/compy-sheet-v1.jpg (front, 3/4, side, back) and the style
rules in docs/249 section 3. Dimensions were read off the side and front views (about 253 px per stud on the 2x crop, ground = 0, total
height 3.0 studs, so the existing LowPolyDinoAssets scale 2.2 still gives the tier-1 height 6.6).

Creature faces +Y, Z up, 1 Blender unit = 1 stud (export with tools/blender_export_roblox.py --faces +Y). Seven parts named for
LowPolyPose.roleOf: Body (torso + neck), Head, Tail, ArmL, ArmR, LegL, LegR. Each part's origin is put exactly where
LowPolyAnimator.pivotFor puts the joint for its role (it works from the part's bounding box): Body = box centre, Head = bottom back,
Tail = front end centre, arms/legs = top centre. Flat shaded, per-face colours (vertex colours, corner domain) AND a baked texture per
part (Body/Head 256 px, others 128 px, Cycles CPU emit bake) so the game's LowPolyTexture/LowPolyRecolor pass sees a real TextureID:
lime is the only "body colour" pixel (LowPolyRecolor.bodyWeight 1), cream belly, near-black eyes, white highlight and dark grey claws
all have weight 0 and survive the gene recolour.
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
    from mathutils import Vector  # type: ignore
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
BLEND_OUT = os.path.join(ROOT, "assets", "blender", "creatures", "Compy_V2.blend")
TEX_DIR = os.path.join(ROOT, "assets", "blender", "creatures", "textures", "compy_v2")
RENDER_DIR = os.path.join(ROOT, "docs", "evidence", "2026-11-22-compy-v2")
V = Vector


def hexcol(h):
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)) + (1.0,)


LIME = hexcol("#72D85F")
CREAM = hexcol("#F5EDD8")
EYE = hexcol("#10151A")
WHITE = hexcol("#FFFFFF")
CLAW = hexcol("#3C3C3C")
TAG_COL = {1: EYE, 2: WHITE, 3: CLAW, 4: EYE, 5: LIME, 6: CREAM}  # face tags: 1 eye, 2 highlight, 3 claw, 4 nostril, 5 force lime, 6 force cream
TEX_SIZE = {"Body": 256, "Head": 256}

# ------------------------------------------------------------------ geometry helpers


class Part:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.tag = self.bm.faces.layers.int.new("tag")

    def shell(self, rings, cap0=True, cap1=True, tag=0, closed=True, apex=None):
        """Loft through rings (lists of Vector, same count); apex closes the last ring with a point. Returns the faces made."""
        bm = self.bm
        vr = [[bm.verts.new(p) for p in ring] for ring in rings]
        faces = []
        n = len(rings[0])
        for a, b in zip(vr, vr[1:]):
            for j in range(n if closed else n - 1):
                k = (j + 1) % n
                faces.append(bm.faces.new((a[j], a[k], b[k], b[j])))
        if cap0:
            faces.append(bm.faces.new(vr[0][::-1]))
        if apex is not None:
            ap = bm.verts.new(apex)
            last = vr[-1]
            for j in range(n):
                faces.append(bm.faces.new((last[j], last[(j + 1) % n], ap)))
        elif cap1:
            faces.append(bm.faces.new(vr[-1]))
        for f in faces:
            f[self.tag] = tag
        return faces

    def cone(self, ring, apex, tag=0):
        bm = self.bm
        vs = [bm.verts.new(p) for p in ring]
        ap = bm.verts.new(apex)
        faces = [bm.faces.new(vs[::-1])]
        n = len(vs)
        for j in range(n):
            faces.append(bm.faces.new((vs[j], vs[(j + 1) % n], ap)))
        for f in faces:
            f[self.tag] = tag
        return faces


def octo(w, h, tw=0.55, ct=0.4, bw=0.6, cb=0.35):
    """Chamfered box section (8 points, 2D (a, b)) half-width w, half-height h; tw/bw = top/bottom flat share, ct/cb = chamfer share."""
    return [(w * tw, h), (w, h * (1 - ct)), (w, -h * (1 - cb)), (w * bw, -h), (-w * bw, -h), (-w, -h * (1 - cb)), (-w, h * (1 - ct)), (-w * tw, h)]


def ring_y(y, cx, cz, w, h, **kw):
    """Section in the XZ plane at depth y (loft along +Y)."""
    return [V((cx + a, y, cz + b)) for a, b in octo(w, h, **kw)]


def ring_z(z, cx, cy, w, d, **kw):
    """Section in the XY plane at height z (loft along +Z); 'top' of the octagon = +Y (front)."""
    return [V((cx + a, cy + b, z)) for a, b in octo(w, d, **kw)][::-1]


def ring_axis(c, axis, up, w, h, segs=8, **kw):
    axis = axis.normalized()
    side = up.cross(axis).normalized()
    upv = axis.cross(side).normalized()
    return [c + side * a + upv * b for a, b in octo(w, h, **kw)]


def disc(c, axis, r, segs, roll=0.0):
    axis = axis.normalized()
    ref = V((0, 0, 1)) if abs(axis.z) < 0.9 else V((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    return [c + (u * math.cos(roll + 2 * math.pi * i / segs) + v * math.sin(roll + 2 * math.pi * i / segs)) * r for i in range(segs)]


def spike(p, centre, y0, y1, z, h, wx=0.07, tag=0):
    """Small back spike: triangle base on the top line between y0 and y1 (y0 > y1, tail runs to -Y), apex leaning back."""
    base = [V((0, y0, z - 0.03)), V((wx, (y0 + y1) / 2, z - 0.03)), V((0, y1, z - 0.03)), V((-wx, (y0 + y1) / 2, z - 0.03))]
    apex = V((0, y1 + (y0 - y1) * 0.15, z + h))
    p.cone(base, apex, tag)


# ------------------------------------------------------------------ parts (model space, studs; faces +Y)


def build_body():
    p = Part("Body")
    kw = dict(tw=0.5, ct=0.45, bw=0.55, cb=0.45)
    torso = [
        ring_y(-0.86, 0, 1.24, 0.26, 0.30, **kw),
        ring_y(-0.56, 0, 1.17, 0.39, 0.42, **kw),
        ring_y(-0.18, 0, 1.11, 0.44, 0.46, **kw),
        ring_y(0.22, 0, 1.13, 0.41, 0.44, **kw),
        ring_y(0.50, 0, 1.22, 0.31, 0.34, **kw),
    ]
    p.shell(torso)
    neck = [
        ring_z(1.20, 0, 0.20, 0.33, 0.30, tw=0.62, ct=0.4, bw=0.5, cb=0.45),
        ring_z(1.62, 0, 0.30, 0.26, 0.22, tw=0.62, ct=0.4, bw=0.5, cb=0.45),
        ring_z(2.08, 0, 0.30, 0.25, 0.22, tw=0.62, ct=0.4, bw=0.5, cb=0.45),
    ]
    p.shell(neck)
    for y0, h, z in ((-0.22, 0.07, 1.57), (-0.46, 0.07, 1.57)):
        spike(p, None, y0, y0 - 0.18, z, h)
    return p


def build_head():
    p = Part("Head")
    kw = dict(tw=0.45, ct=0.55, bw=0.55, cb=0.42)
    rings = [
        ring_y(-0.19, 0, 2.47, 0.26, 0.22, **kw),
        ring_y(-0.03, 0, 2.47, 0.48, 0.46, **kw),
        ring_y(0.24, 0, 2.43, 0.59, 0.575, **kw),
        ring_y(0.70, 0, 2.43, 0.58, 0.54, **kw),
        ring_y(1.12, 0, 2.36, 0.46, 0.42, **kw),
        ring_y(1.45, 0, 2.33, 0.37, 0.32, **kw),
    ]
    p.shell(rings)
    # eyes: domes on the flat side faces, facing out and a little forward
    for s in (1, -1):
        c = V((s * 0.575, 0.68, 2.53))
        ax = V((s * 1.0, 0.42, 0.08)).normalized()
        r = EYE_R
        rings = [disc(c - ax * 0.04, ax, r, 12), disc(c + ax * 0.05, ax, r * 0.85, 12), disc(c + ax * 0.10, ax, r * 0.5, 12)]
        p.shell(rings, cap0=True, tag=1, apex=c + ax * 0.12)
        # highlight: up and toward the front of the eye
        up = V((0, 0, 1))
        side = ax.cross(up).normalized()
        upv = side.cross(ax).normalized() * -1 if side.cross(ax).z < 0 else side.cross(ax).normalized()
        fwd = V((0, 1, 0)) - ax * ax.y
        fwd.normalize()
        hc = c + ax * 0.095 + upv * (r * 0.4) + fwd * (r * 0.28)
        hr = disc(hc, ax, EYE_R * 0.26, 6)
        p.cone(hr, hc + ax * 0.035, tag=2)
    # nostrils: small dark hexagons just in front of the snout cap
    for s in (1, -1):
        c = V((s * 0.14, 1.452, 2.30))
        ring = disc(c, V((0, 1, 0)), 0.035, 6)
        p.shell([ring, [q + V((0, 0.006, 0)) for q in ring]], tag=4)
    return p


def build_tail():
    p = Part("Tail")
    rings = [
        ring_y(-0.50, 0, 1.22, 0.31, 0.38, tw=0.5, ct=0.45, bw=0.55, cb=0.45),
        ring_y(-0.92, 0, 1.19, 0.21, 0.25, tw=0.5, ct=0.45, bw=0.55, cb=0.45),
        ring_y(-1.30, 0, 1.31, 0.11, 0.13, tw=0.5, ct=0.45, bw=0.55, cb=0.45),
    ]
    p.shell(rings, cap0=True, apex=V((0, -1.68, 1.45)))
    for y0, h, z in ((-0.70, 0.07, 1.52), (-0.94, 0.06, 1.45), (-1.16, 0.05, 1.42)):
        spike(p, None, y0, y0 - 0.17, z, h, wx=0.06)
    return p


def build_leg(s):
    p = Part("LegR" if s > 0 else "LegL")
    x = s * 0.40
    thigh = [
        ring_z(0.46, x, -0.33, 0.17, 0.20, **LEGKW),
        ring_z(0.60, x, -0.38, 0.24, 0.32, **LEGKW),
        ring_z(0.86, x, -0.43, 0.27, 0.37, **LEGKW),
        ring_z(1.08, x, -0.43, 0.24, 0.32, **LEGKW),
        ring_z(1.22, x, -0.42, 0.16, 0.20, **LEGKW),
    ]
    p.shell(thigh)
    shin = [ring_z(0.12, x + s * 0.03, -0.24, 0.18, 0.21, **LEGKW), ring_z(0.56, x, -0.31, 0.16, 0.19, **LEGKW)]
    p.shell(shin)
    foot = [
        ring_y(-0.46, x + s * 0.04, 0.10, 0.19, 0.10, ct=0.5),
        ring_y(-0.05, x + s * 0.04, 0.10, 0.23, 0.10, ct=0.5),
        ring_y(0.13, x + s * 0.04, 0.08, 0.22, 0.08, ct=0.5),
    ]
    p.shell(foot)
    for dx in (-0.14, 0.0, 0.14):
        cx = x + s * 0.04 + dx
        base = [V((cx - 0.055, 0.11, 0.0)), V((cx + 0.055, 0.11, 0.0)), V((cx + 0.05, 0.11, 0.11)), V((cx - 0.05, 0.11, 0.11))]
        p.shell([base, [q + V((0, 0.06, 0)) for q in base]], cap0=True, tag=3, apex=V((cx, 0.26, 0.03)))
    return p


def build_arm(s):
    p = Part("ArmR" if s > 0 else "ArmL")
    x = s * 0.42
    up = [ring_axis(V((x, 0.16, 1.36)), V((0, 0.45, -1)), V((1, 0, 0)), 0.11, 0.12), ring_axis(V((x, 0.30, 1.02)), V((0, 0.45, -1)), V((1, 0, 0)), 0.11, 0.11)]
    # loft along the arm (rings were built facing along the axis, so they line up)
    p.shell(up)
    hand = [ring_axis(V((x, 0.24, 1.01)), V((0, 1, -0.15)), V((0, 0, 1)), 0.12, 0.10), ring_axis(V((x, 0.50, 0.97)), V((0, 1, -0.15)), V((0, 0, 1)), 0.12, 0.09)]
    p.shell(hand)
    return p


EYE_R = 0.19
LEGKW = dict(tw=0.5, ct=0.45, bw=0.5, cb=0.45)


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


def colour_for(name, c, n, tag):
    if tag in TAG_COL:
        return TAG_COL[tag]
    if name == "Body":
        if c.z > 1.15 and abs(c.x) < 0.26 and n.y > 0.3:   # neck front strip (front + front chamfers: visible from the side too)
            return CREAM
        if c.z <= 1.15 + 0.4 and n.y > 0.2 and abs(c.x) < 0.34:   # chest front
            return CREAM
        if n.z < -0.6 and c.y > -0.5:                     # belly underside
            return CREAM
    if name == "Tail" and n.z < -0.6:
        return CREAM
    return LIME


def finish(p):
    bm = p.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    me = bpy.data.meshes.new(p.name)
    cols = []
    for f in bm.faces:
        cols.append(colour_for(p.name, f.calc_center_median(), f.normal, f[p.tag]))
    bm.to_mesh(me)
    lo = [min(v.co[i] for v in me.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in me.vertices) for i in range(3)]
    piv = pivot_for(p.name, lo, hi)
    for v in me.vertices:
        v.co -= piv
    attr = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for poly, col in zip(me.polygons, cols):
        for li in poly.loop_indices:
            attr.data[li].color_srgb = col
    for poly in me.polygons:
        poly.use_smooth = False
    ob = bpy.data.objects.new(p.name, me)
    ob.location = piv
    bpy.context.scene.collection.objects.link(ob)
    bm.free()
    return ob


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def uv_and_bake(ob):
    size = TEX_SIZE.get(ob.name, 128)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.04, area_weight=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new("Compy_V2_" + ob.name, size, size, alpha=False)
    mat = bpy.data.materials.new("Compy_V2_" + ob.name)
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
    bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
    os.makedirs(TEX_DIR, exist_ok=True)
    path = os.path.join(TEX_DIR, "Compy_V2_%s.png" % ob.name)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    # final material: texture -> Principled base colour (what the FBX carries and the Roblox importer reads)
    for n in (vc, em):
        nt.nodes.remove(n)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.8
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    img.pack()
    img.filepath_raw = "//textures/compy_v2/Compy_V2_%s.png" % ob.name  # relative to the .blend (public repo: no local paths)
    return path


# ------------------------------------------------------------------ render


def setup_render():
    """Cycles CPU (no EEVEE / GPU), small and few samples: white ambient world + one sun, transparent film (the crop tool adds the grey)."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = False
    sc.view_settings.view_transform = "Standard"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 0.30
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.5
    sun.data.angle = math.radians(20)
    sun.rotation_euler = (math.radians(-45), 0, math.radians(-30))  # comes from the front, right, above
    sc.collection.objects.link(sun)
    sc.render.resolution_x = 420
    sc.render.resolution_y = 420
    sc.render.film_transparent = True


def render(name, direction, scale=3.9, target=(0, -0.05, 1.5), elev=0.06):
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
    sc.render.filepath = os.path.join(RENDER_DIR, "render-%s.png" % name)
    bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    builders = [build_body, build_head, build_tail, lambda: build_arm(1), lambda: build_arm(-1), lambda: build_leg(1), lambda: build_leg(-1)]
    objs = [finish(b()) for b in builders]
    for ob in objs:
        uv_and_bake(ob)
    lo = [min((ob.matrix_world @ V(c))[i] for ob in objs for c in ob.bound_box) for i in range(3)]
    hi = [max((ob.matrix_world @ V(c))[i] for ob in objs for c in ob.bound_box) for i in range(3)]
    for ob in objs:
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        print("COMPY part %-5s tris %4d origin %s" % (ob.name, tris, tuple(round(x, 3) for x in ob.location)))
    print("COMPY size studs x %.2f y(depth) %.2f z(height) %.2f; total tris %d" % (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2],
          sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in objs)))
    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT, compress=True)
    print("COMPY saved", BLEND_OUT)
    if "--no-render" not in ARGS:
        setup_render()
        render("front", (0, 1, 0))
        render("side", (1, 0, 0))
        render("back", (0, -1, 0))
        render("q34", (math.sin(math.radians(38)), math.cos(math.radians(38)), 0))
        print("COMPY renders in", RENDER_DIR)


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("ERROR build failed")
    sys.exit(1)
