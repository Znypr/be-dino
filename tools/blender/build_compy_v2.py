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


def disc(c, axis, r, segs, roll=0.0):
    axis = axis.normalized()
    ref = V((0, 0, 1)) if abs(axis.z) < 0.9 else V((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    return [c + (u * math.cos(roll + 2 * math.pi * i / segs) + v * math.sin(roll + 2 * math.pi * i / segs)) * r for i in range(segs)]


X = V((1, 0, 0))
# Round decagon: flat face centred on 'front' (v = +1), vertices at the sides (u = +-1). Smooth enough to read as a toy, still faceted.
ROUND = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 360, 36)]
# Head section: flat top, wider at the cheeks than at the top, flat jaw (u = side, v = up)
HEADSEC = [(0.42, 1.0), (0.80, 0.70), (1.0, 0.18), (0.95, -0.48), (0.62, -1.0), (-0.62, -1.0), (-0.95, -0.48), (-1.0, 0.18), (-0.80, 0.70), (-0.42, 1.0)]


def frame(axis):
    """Ring frame for a loft along `axis`: side = X, front = axis x X (= +Y for an upward axis, = +Z (up) for a backward axis)."""
    a = axis.normalized()
    front = a.cross(X).normalized()
    side = front.cross(a).normalized()
    return side, front


def ring(c, axis, w, d, shape=ROUND, dx=0.0):
    side, front = frame(axis)
    return [c + side * (u * w + dx) + front * (v * d) for u, v in shape]


def spike_at(p, base, out, back, h, wb=0.055):
    """Small back spike on the surface point `base`: square-ish base across X, apex out along `out`, leaning toward `back`."""
    out = out.normalized()
    along = (back - out * back.dot(out)).normalized()
    pts = [base - out * 0.04 + along * wb, base - out * 0.04 + X * wb, base - out * 0.04 - along * wb, base - out * 0.04 - X * wb]
    p.cone(pts, base + out * h + along * (h * 0.6))


# ------------------------------------------------------------------ parts (model space, studs; faces +Y)
LEAN_BODY = math.radians(12)
LEAN_NECK = math.radians(20)
EYE_R = 0.19


def body_rings():
    """(centre, axis, w, d) of the pear body: axis leans forward 12 degrees, belly widest low."""
    ax = V((0, math.sin(LEAN_BODY), math.cos(LEAN_BODY)))
    out = []
    for t, w, d, fy in ((0.0, 0.26, 0.26, 0.0), (0.16, 0.42, 0.44, 0.03), (0.42, 0.45, 0.47, 0.04), (0.68, 0.38, 0.39, 0.02), (0.92, 0.27, 0.28, 0.0)):
        c = V((0, -0.24, 0.66)) + ax * t + V((0, fy, 0))
        out.append((c, ax, w, d))
    return out


def neck_rings():
    ax = V((0, math.sin(LEAN_NECK), math.cos(LEAN_NECK)))
    base = V((0, -0.02, 1.38))
    return [(base + ax * t, ax, w, d) for t, w, d in ((0.0, 0.29, 0.29), (0.34, 0.26, 0.26), (0.72, 0.26, 0.255))]


def back_point(spec, k=1.0):
    c, ax, w, d = spec
    _, front = frame(ax)
    return c - front * d * k, -front


def build_body():
    p = Part("Body")
    br = body_rings()
    p.shell([ring(c, a, w, d) for c, a, w, d in br])
    nr = neck_rings()
    p.shell([ring(c, a, w, d) for c, a, w, d in nr])
    # back spikes: down the back of the neck and the body (the tail continues the row)
    for spec_a, spec_b, f, h in ((nr[1], nr[2], 0.1, 0.07), (nr[0], nr[1], 0.3, 0.075), (br[4], br[3], 0.25, 0.08), (br[3], br[2], 0.5, 0.08)):
        pa, na = back_point(spec_a)
        pb, nb = back_point(spec_b)
        q = pa.lerp(pb, f)
        n = (na.lerp(nb, f) + V((0, 0, 0.5))).normalized()
        spike_at(p, q, n, V((0, -1, -0.6)), h)
    return p


def build_head():
    p = Part("Head")
    # side profile (y, top, bottom, half-width): tall round cranium, wedge snout (tip about 65 % of the cranium height), flat jaw rising to the throat
    prof = [(-0.22, 2.64, 2.34, 0.22), (-0.13, 2.80, 2.14, 0.40), (0.02, 2.95, 1.99, 0.52), (0.22, 3.00, 1.90, 0.57), (0.52, 2.98, 1.86, 0.58),
            (0.86, 2.86, 1.87, 0.51), (1.14, 2.73, 1.90, 0.43), (1.33, 2.65, 1.93, 0.36)]
    rings = []
    for y, top, bot, w in prof:
        mid, h = (top + bot) / 2, (top - bot) / 2
        rings.append([V((u * w, y, mid + v * h)) for u, v in HEADSEC])
    p.shell(rings)
    # eyes sit IN the upper side plane (protrude about 0.09 = 24 % of the 0.38 diameter), looking out and a little forward
    for s in (1, -1):
        c = V((s * 0.50, 0.62, 2.56))
        ax = V((s * 0.88, 0.42, 0.20)).normalized()
        r = EYE_R
        er = [disc(c - ax * 0.05, ax, r, 12), disc(c + ax * 0.045, ax, r * 0.88, 12), disc(c + ax * 0.08, ax, r * 0.52, 12)]
        p.shell(er, cap0=True, tag=1, apex=c + ax * 0.093)
        upv = (V((0, 0, 1)) - ax * ax.z).normalized()
        fwd = (V((0, 1, 0)) - ax * ax.y).normalized()
        hc = c + ax * 0.08 + upv * (r * 0.38) + fwd * (r * 0.22)
        p.cone(disc(hc, ax, r * 0.27, 6), hc + ax * 0.03, tag=2)
    # nostrils: dots on the snout's top-front
    for s in (1, -1):
        c = V((s * 0.12, 1.335, 2.55))
        nax = V((0, 1, 0.35)).normalized()
        rr = disc(c, nax, 0.034, 6)
        p.shell([rr, [q + nax * 0.008 for q in rr]], tag=4)
    return p


def build_tail():
    p = Part("Tail")
    # spine with a slight upward curve; base about the thigh width
    spine = [V((0, -0.40, 1.00)), V((0, -0.72, 1.02)), V((0, -1.04, 1.10)), V((0, -1.34, 1.23))]
    sizes = [(0.27, 0.28), (0.21, 0.22), (0.14, 0.145), (0.075, 0.08)]
    specs = []
    for i, (c, (w, d)) in enumerate(zip(spine, sizes)):
        nxt = spine[min(i + 1, len(spine) - 1)]
        prv = spine[max(i - 1, 0)]
        ax = (nxt - prv).normalized()
        specs.append((c, ax, w, d))
    # axis runs to -Y, so frame 'front' = up; ROUND's flat face is on top
    p.shell([ring(c, a, w, d) for c, a, w, d in specs], cap0=True, apex=V((0, -1.68, 1.44)))
    for i, (f, h) in enumerate(((0.2, 0.075), (0.7, 0.07), (0.25, 0.06), (0.7, 0.05), (0.3, 0.04))):
        k = min(i // 2, 2)
        a, b = specs[k], specs[k + 1]
        pa = a[0] + frame(a[1])[1] * a[3]
        pb = b[0] + frame(b[1])[1] * b[3]
        q = pa.lerp(pb, f)
        n = frame(a[1])[1].lerp(frame(b[1])[1], f)
        spike_at(p, q, n, V((0, -1, 0)), h)
    return p


def build_leg(s):
    p = Part("LegR" if s > 0 else "LegL")
    x = s * 0.39
    up = V((0, 0, 1))
    # drumstick thigh: rounded out to the side (dx) and back (cy)
    thigh = [(1.20, 0.17, 0.19, -0.38, 0.00), (1.06, 0.27, 0.31, -0.42, 0.02), (0.84, 0.29, 0.34, -0.45, 0.04),
             (0.62, 0.22, 0.25, -0.40, 0.03), (0.48, 0.15, 0.16, -0.34, 0.01)]
    p.shell([ring(V((x, cy, z)), up, w, d, dx=s * dx) for z, w, d, cy, dx in thigh])
    # short narrower shin, slightly back-slanted down to the ankle
    p.shell([ring(V((x + s * 0.01, -0.33, 0.52)), up, 0.15, 0.15), ring(V((x + s * 0.02, -0.26, 0.13)), up, 0.15, 0.16)])
    # foot with three dark claws pointing forward
    fwd = V((0, 1, 0))
    fx = x + s * 0.03
    foot = [(-0.42, 0.17, 0.09), (-0.10, 0.21, 0.10), (0.10, 0.21, 0.085)]
    p.shell([ring(V((fx, y, 0.095)), fwd, w, h) for y, w, h in foot])
    for dx in (-0.13, 0.0, 0.13):
        c = V((fx + dx, 0.12, 0.06))
        base = ring(c, fwd, 0.07, 0.065, shape=ROUND[::2])
        p.shell([base, [q + fwd * 0.05 for q in base]], cap0=True, tag=3, apex=c + V((0, 0.17, -0.04)))
    return p


def build_arm(s):
    p = Part("ArmR" if s > 0 else "ArmL")
    x = s * 0.34
    sh, el, wr, hd = V((x, 0.20, 1.36)), V((x + s * 0.03, 0.24, 1.16)), V((x + s * 0.02, 0.42, 1.09)), V((x + s * 0.01, 0.52, 0.99))
    # stubby upper arm down to the elbow, forearm forward, hand forward and down
    p.shell([ring(sh, el - sh, 0.115, 0.115), ring(el, el - sh, 0.105, 0.105)])
    p.shell([ring(el - (wr - el).normalized() * 0.07, wr - el, 0.10, 0.10), ring(wr, wr - el, 0.095, 0.095)])
    p.shell([ring(wr - (hd - wr).normalized() * 0.04, hd - wr, 0.11, 0.085), ring(hd, hd - wr, 0.09, 0.07)])
    return p


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
    """Lime everywhere except: the cream band from the throat down the front of the neck and the belly (faces looking forward,
    3 of the 10 ring faces = about 25 % of the depth in the side view). Back, tail and underside stay lime."""
    if tag in TAG_COL:
        return TAG_COL[tag]
    if name == "Body" and n.y > 0.5 and abs(c.x) < 0.36 and c.z > 0.72:
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
    bsdf.inputs["Roughness"].default_value = 1.0
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.0
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
