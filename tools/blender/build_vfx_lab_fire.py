"""Be Dino! VFX lab: stylised anime FIRE texture renders (docs/143). Real Blender renders (Cycles, headless), full colour on straight alpha.

    python tools/render_vfx_lab_fire.py          # renders everything, then Pillow only pastes finished frames into sheets

or by hand:

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup \
        --python tools/blender/build_vfx_lab_fire.py -- --frames build/vfx-lab-frames --out resources/effects/vfx-lab \
        --blend tools/blender/vfx_lab_fire_v1.blend [--only fireTongueSheet] [--samples 64]

Look: bold anime fire like the owner references (docs/reference/vfx-fire-*-ref.webp): cel-banded colour (deep red-orange edge, orange body,
yellow, pale-yellow hot core), curled tapering tongues, hard clean silhouettes. Everything is modelled geometry (tapered ribbons and fans)
with an emission shader that bands a heat value, nothing is code-drawn pixels. Nothing here is a final shipped asset: lab textures.

  texture            size / layout           what
  fireTongueSheet    4x4 of 256, 16 frames   one curled tongue with a small sibling, sways and flickers, loops (aura tongues, flame wisps)
  fireClusterSheet   4x4 of 256, 16 frames   three-tongue bonfire cluster, loops (footprint flames, ground fire)
  fireSparkSheet     4x4 of 128, 16 shapes   4-point sparks, curved embers, round glows, slim streaks (random frame)
  firePuffSheet      4x4 of 256, 16 shapes   cartoon cloud puffs in NEUTRAL light grey (tint at runtime: warm smoke or tan dust)
  fireStreakStrip    1024x256 tile in U      thin curved swirl streaks, head right, tail left (Beam scroll)
  fireFlameStrip     1024x256 tile in U      a hot base band with tongues rising (Beam scroll / flame wall)
  fireTrailFlame     512x128                 one long horizontal flame, wide hot head on the left, tapering wavy tail on the right (Trail)
  fireRingGround     1024x1024 top-down      concentric spiral flame rings with little outward tongues, empty middle (ground ring)
  fireFootprintL/R   256x256                 glowing raptor footprint (3 toes + heel pad), left and right
"""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fx_common import Graph, link, new_scene, parse_args  # noqa: E402


def lin(c):
    """sRGB 0..255 -> Blender linear RGBA."""
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)


FIRE = [(0.00, (200, 40, 18)), (0.22, (246, 86, 22)), (0.42, (255, 150, 32)), (0.62, (255, 214, 70)), (0.80, (255, 246, 190))]
FIRE_HOT = [(0.00, (214, 52, 20)), (0.18, (255, 104, 24)), (0.36, (255, 168, 38)), (0.55, (255, 224, 84)), (0.74, (255, 250, 205))]
PUFF = [(0.00, (150, 150, 162)), (0.40, (208, 208, 216)), (0.68, (255, 255, 255))]


def ramp_node(G, sock, stops, soft=0.025):
    """ColorRamp with cel bands: each band starts at its threshold and blends over `soft`."""
    n = G.N.n("ShaderNodeValToRGB")
    cr = n.color_ramp
    cr.interpolation = "LINEAR"
    # points: first stop at 0 with first colour, then (thr-soft -> previous colour) , (thr -> this colour)
    pts = [(0.0, stops[0][1])]
    for i in range(1, len(stops)):
        pts.append((max(stops[i][0] - soft, pts[-1][0] + 1e-3), stops[i - 1][1]))
        pts.append((stops[i][0], stops[i][1]))
    pts.append((1.0, stops[-1][1]))
    while len(cr.elements) < len(pts):
        cr.elements.new(0.5)
    for el, (p, col) in zip(cr.elements, pts):
        el.position = min(max(p, 0.0), 1.0)
        el.color = lin(col)
    G.t.links.new(sock, n.inputs[0])
    return n.outputs[0]


def emit_color(G, color_sock, alpha=None):
    emis = G.N.n("ShaderNodeEmission")
    emis.inputs["Strength"].default_value = 1.0
    G.t.links.new(color_sock, emis.inputs["Color"])
    out = G.N.n("ShaderNodeOutputMaterial")
    if alpha is None:
        G.t.links.new(emis.outputs[0], out.inputs[0])
        return
    a = alpha if not isinstance(alpha, (int, float)) else G.val(alpha)
    clear = G.N.n("ShaderNodeBsdfTransparent")
    mix = G.N.n("ShaderNodeMixShader")
    G.t.links.new(a, mix.inputs["Fac"])
    G.t.links.new(clear.outputs[0], mix.inputs[1])
    G.t.links.new(emis.outputs[0], mix.inputs[2])
    G.t.links.new(mix.outputs[0], out.inputs[0])


def uvmat(name, heat_fn, stops, alpha_fn=None):
    """Material whose heat comes from the UV (u across a ribbon, v along it)."""
    m = bpy.data.materials.new(name)
    G = Graph(m)
    u, v = G.uv()
    d = G.op("ABSOLUTE", G.op("SUBTRACT", G.op("MULTIPLY", u, 2.0), 1.0))   # 0 centre, 1 edge
    heat = heat_fn(G, d, v)
    emit_color(G, ramp_node(G, G.op("MINIMUM", G.op("MAXIMUM", heat, 0.0), 1.0), stops), alpha_fn(G, d, v) if alpha_fn else None)
    return m


def radmat(name, radius, stops, power=1.0, edge=0.0):
    """Material whose heat falls with the OBJECT-space distance from the origin (stars, dots, pads)."""
    m = bpy.data.materials.new(name)
    G = Graph(m)
    tc = G.N.n("ShaderNodeTexCoord")
    ln = G.N.n("ShaderNodeVectorMath", operation="LENGTH")
    G.t.links.new(tc.outputs["Object"], ln.inputs[0])
    r = G.op("DIVIDE", ln.outputs[1], radius)
    heat = G.op("SUBTRACT", 1.0, G.op("POWER", G.op("MINIMUM", r, 1.0), power))
    emit_color(G, ramp_node(G, G.op("MINIMUM", G.op("MAXIMUM", G.op("SUBTRACT", heat, edge), 0.0), 1.0), stops))
    return m


def flame_mat(name, stops=FIRE, dpow=0.85, dk=1.0, vk=0.5, bias=0.02, vstart=0.0):
    def heat(G, d, v):
        a = G.op("MULTIPLY", G.op("POWER", d, dpow), dk)
        b = G.op("MULTIPLY", G.op("MAXIMUM", G.op("SUBTRACT", v, vstart), 0.0), vk)
        return G.op("SUBTRACT", G.op("ADD", G.op("SUBTRACT", 1.0, a), bias), b)
    return uvmat(name, heat, stops)


def halo_mat(name, color=(255, 120, 30), peak=0.6, power=1.6):
    def heat(G, d, v):
        return G.val(0.5)

    def alpha(G, d, v):
        return G.op("MULTIPLY", G.op("POWER", G.op("SUBTRACT", 1.0, d), power), peak)
    return uvmat(name, heat, [(0.0, color)], alpha)


def ribbon(sc, name, pts, widths, mat, z=0.0):
    """Flat ribbon along a 2D centre line: u (0..1) across, v (0..1) along. Camera looks down -Z so XY is the image."""
    n = len(pts)
    verts, uvs, faces = [], [], []
    for i, (p, w) in enumerate(zip(pts, widths)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        verts.append((p[0] + nx * w, p[1] + ny * w, z))
        verts.append((p[0] - nx * w, p[1] - ny * w, z))
        uvs.append((0.0, i / (n - 1)))
        uvs.append((1.0, i / (n - 1)))
    for i in range(n - 1):
        k = i * 2
        faces.append((k, k + 1, k + 3, k + 2))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    return link(sc, ob)


def fan(sc, name, pts, mat, z=0.0):
    """Closed polygon fanned around its centroid (origin of the object = the centroid, so radial materials work)."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    verts = [(0.0, 0.0, 0.0)] + [(p[0] - cx, p[1] - cy, 0.0) for p in pts]
    faces = [(0, 1 + i, 1 + (i + 1) % len(pts)) for i in range(len(pts))]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = (cx, cy, z)
    return link(sc, ob)


def tongue_line(base, height, lean, bend, curl, n=44):
    """Centre line of a flame tongue: start pointing up (+lean), bend along its length, hook at the tip (curl)."""
    x, y = base
    th0 = math.pi / 2 + lean
    ds = height / n
    pts = [(x, y)]
    for i in range(1, n + 1):
        t = i / n
        th = th0 + bend * t + curl * t ** 3
        x += math.cos(th) * ds
        y += math.sin(th) * ds
        pts.append((x, y))
    return pts


def tongue_w(width, n=44, wob=0.0, ph=0.0, round_base=0.0, taper=0.8):
    out = []
    for i in range(n + 1):
        t = i / n
        base = round_base + (1.0 - round_base) * math.sin(min(t / 0.24, 1.0) * math.pi / 2) ** 0.55
        w = width * base * (1.0 - t) ** taper * (1.0 + wob * math.sin(t * 9.0 + ph))
        out.append(max(w, 0.0))
    return out


def add_tongue(sc, nm, base, height, width, lean, bend, curl, z, mat, halo=None, wob=0.0, ph=0.0):
    pts = tongue_line(base, height, lean, bend, curl)
    if halo is not None:
        ribbon(sc, nm + "_halo", pts, [w * 1.55 + 0.02 for w in tongue_w(width, wob=wob, ph=ph)], halo, z - 0.02)
    ribbon(sc, nm, pts, tongue_w(width, wob=wob, ph=ph), mat, z)


def line_theta(base, th0, height, bend, curl, n=44):
    """Like tongue_line but starts at an absolute angle th0 (radians); also returns the tangent angle at every point."""
    x, y = base
    ds = height / n
    pts, ths = [(x, y)], [th0]
    for i in range(1, n + 1):
        t = i / n
        th = th0 + bend * t + curl * t ** 3
        x += math.cos(th) * ds
        y += math.sin(th) * ds
        pts.append((x, y))
        ths.append(th)
    return pts, ths


CORE = [(0.00, (255, 190, 56)), (0.45, (255, 226, 120)), (0.80, (255, 250, 214))]


def flame_design(sc, tag, base, H, W, lean, bend, curl, z0, licks, core=True, stops=FIRE_HOT, n=44):
    """A hand-drawn style flame: side licks that branch off the main tongue and curl back, the main tongue (banded
    red rim, orange body, yellow), a hot inner core tongue on top, and a soft outer glow under everything."""
    pts, ths = line_theta(base, math.pi / 2 + lean, H, bend, curl, n)
    for k, (t, dth, ln, wf, cu) in enumerate(licks):
        i = min(int(t * n), n - 2)
        lp, _ = line_theta(pts[i], ths[i] + dth, ln * H, -0.35 * dth + 0.0, cu, 30)
        ribbon(sc, f"{tag}_lick{k}", lp, tongue_w(W * wf * 1.45, n=30, round_base=0.5, taper=0.7),
               flame_mat(f"{tag}_lm{k}", stops=stops, dpow=0.85, dk=1.0, vk=0.5), z0 - 0.03 * (k + 1))
    ribbon(sc, f"{tag}_glow", pts, [w * 1.5 + 0.03 for w in tongue_w(W, n=n)], halo_mat(f"{tag}_hm", peak=0.5), z0 - 0.5)
    ribbon(sc, f"{tag}_main", pts, tongue_w(W, n=n, wob=0.05, ph=base[0] * 7), flame_mat(f"{tag}_mm", stops=stops, dpow=0.85, dk=1.0, vk=0.45), z0)
    if core:
        m = int(n * 0.74)
        cp = pts[:m + 1]
        ribbon(sc, f"{tag}_core", cp, tongue_w(W * 0.5, n=m, round_base=0.1, taper=0.9),
               flame_mat(f"{tag}_cm", stops=CORE, dpow=0.8, dk=0.9, vk=0.3, bias=0.12), z0 + 0.03)


# ----------------------------------------------------------------------------------------------------------------------- scenes
CELL_T = 256
FRAMES = 16


def tongue_frame(sc, f, cluster):
    ph = 2 * math.pi * f / FRAMES
    sw = math.sin(ph)
    sw2 = math.sin(ph * 2 + 0.5)
    if not cluster:
        flame_design(sc, "m", (-0.05, -0.88), 1.62 + 0.07 * sw2, 0.34, 0.10 * sw, -0.55 + 0.35 * math.sin(ph + 1.0), 1.8 + 0.4 * sw2, 0.0,
                     [(0.30, 0.75, 0.45, 0.42, 1.4 + 0.3 * sw), (0.18, -0.8, 0.38, 0.38, -1.2 - 0.3 * sw), (0.58, 0.6, 0.3, 0.3, 1.0)])
    else:
        flame_design(sc, "c", (0.0, -0.86), 1.45 + 0.06 * sw2, 0.26, 0.06 * sw, 0.3 * math.sin(ph + 0.6), 1.2, 0.0,
                     [(0.3, 0.7, 0.3, 0.4, 1.0), (0.2, -0.7, 0.28, 0.4, -1.0)])
        flame_design(sc, "l", (-0.3, -0.86), 0.95 + 0.06 * math.sin(ph * 2 + 1), 0.17, 0.4 + 0.08 * sw, -0.3 * math.sin(ph + 2), 1.4, 0.2,
                     [], core=False)
        flame_design(sc, "r", (0.3, -0.86), 0.85 + 0.06 * math.sin(ph * 2 + 2), 0.16, -0.45 + 0.08 * sw, 0.3 * math.sin(ph + 4), -1.4, 0.4,
                     [], core=False)


BIG_DESIGNS = [
    # (base, H, W, lean, bend, curl, licks)
    ((-0.05, -0.88), 1.72, 0.36, 0.10, -0.55, 2.0, [(0.30, 0.75, 0.45, 0.42, 1.4), (0.18, -0.8, 0.38, 0.38, -1.2), (0.58, 0.6, 0.3, 0.3, 1.0)]),
    ((0.05, -0.88), 1.72, 0.36, -0.10, 0.55, -2.0, [(0.30, -0.75, 0.45, 0.42, -1.4), (0.18, 0.8, 0.38, 0.38, 1.2), (0.58, -0.6, 0.3, 0.3, -1.0)]),
    ((0.0, -0.88), 1.78, 0.30, 0.0, 0.9, -1.4, [(0.22, 0.9, 0.5, 0.4, 1.3), (0.4, -0.7, 0.34, 0.3, -1.0), (0.62, 0.7, 0.25, 0.25, 1.2), (0.12, -1.0, 0.3, 0.35, -1.0)]),
    ((-0.02, -0.88), 1.6, 0.4, 0.2, -1.0, 1.0, [(0.28, -0.7, 0.55, 0.5, -1.0), (0.45, 0.8, 0.38, 0.32, 1.5), (0.15, 0.9, 0.35, 0.35, 1.2)]),
]


SWIRL_DESIGNS = [
    ((-0.05, -0.88), 1.6, 0.32, 0.30, -0.95, 2.4, [(0.30, 0.8, 0.5, 0.4, 1.6), (0.52, -0.6, 0.32, 0.3, -1.0)]),
    ((0.05, -0.88), 1.6, 0.32, -0.30, 0.95, -2.4, [(0.30, -0.8, 0.5, 0.4, -1.6), (0.52, 0.6, 0.32, 0.3, 1.0)]),
    ((0.1, -0.85), 1.5, 0.3, 0.45, -0.5, 2.9, [(0.35, 0.9, 0.5, 0.4, 1.8), (0.2, -0.8, 0.3, 0.3, -1.0)]),
    ((-0.1, -0.85), 1.5, 0.3, -0.45, 0.5, -2.9, [(0.35, -0.9, 0.5, 0.4, -1.8), (0.2, 0.8, 0.3, 0.3, 1.0)]),
]


def swirl_frame(sc, k):
    base, H, W, lean, bend, curl, licks = SWIRL_DESIGNS[k]
    flame_design(sc, "s", base, H, W, lean, bend, curl, 0.0, licks, n=60)


def big_frame(sc, k):
    base, H, W, lean, bend, curl, licks = BIG_DESIGNS[k]
    flame_design(sc, "b", base, H, W, lean, bend, curl, 0.0, licks, n=60)


def scene_for_frames(name, size=CELL_T, samples=96):
    return new_scene(name, size, frames=1, samples=samples, ortho=2.0)


def star_poly(L, n=0.55, count=64, rot=0.0):
    """Concave superellipse four-point star, long axis L."""
    pts = []
    for i in range(count):
        a = 2 * math.pi * i / count
        c, s = math.cos(a), math.sin(a)
        r = L * (abs(c) ** (2 / n) + abs(s) ** (2 / n)) ** (-n / 2) if False else None
        x = L * (1 if c >= 0 else -1) * abs(c) ** (2.0 / n * 1.0) if False else None
        # astroid-like star: x = L cos^3, y = L sin^3 gives a sharp four-point star; blend toward a circle for a fat core
        px = L * math.copysign(abs(c) ** 3, c)
        py = L * math.copysign(abs(s) ** 3, s)
        k = 0.08
        px = px * (1 - k) + k * L * 0.35 * c
        py = py * (1 - k) + k * L * 0.35 * s
        pts.append((px * math.cos(rot) - py * math.sin(rot), px * math.sin(rot) + py * math.cos(rot)))
    return pts


def circle_pts(r, count=40, sx=1.0, sy=1.0):
    return [(math.cos(2 * math.pi * i / count) * r * sx, math.sin(2 * math.pi * i / count) * r * sy) for i in range(count)]


def spark_frame(sc, k):
    rnd = random.Random(1000 + k)
    kind = ["star"] * 6 + ["ember"] * 5 + ["dot"] * 3 + ["streak"] * 2
    kind = kind[k]
    if kind == "star":
        L = 0.78 - 0.04 * (k % 3)
        fan(sc, "star", star_poly(L, rot=(k % 2) * math.radians(18)), radmat("starm%d" % k, L * 0.75, FIRE_HOT, power=0.7))
        fan(sc, "starcore", circle_pts(0.13), radmat("starc%d" % k, 0.13, [(0.0, (255, 250, 220))], power=1), z=0.02)
    elif kind == "ember":
        lean = rnd.uniform(-0.5, 0.5)
        pts = tongue_line((-0.05, -0.6), 1.2, lean, rnd.uniform(-0.9, 0.9), rnd.uniform(-1.2, 1.2), n=30)
        w = [0.2 * math.sin(math.pi * min(i / 30 * 1.35, 1.0)) ** 0.7 * (1 - i / 30) ** 0.5 for i in range(31)]
        ribbon(sc, "ember", pts, w, flame_mat("embm%d" % k, stops=FIRE_HOT, dpow=1.2, dk=0.5, vk=0.55))
    elif kind == "dot":
        R = 0.3 + 0.08 * (k % 3)
        fan(sc, "dot", circle_pts(R), radmat("dotm%d" % k, R, FIRE_HOT, power=1.1))
    else:
        pts = [(-0.75 + 1.5 * i / 20, 0.12 * math.sin(i / 20 * math.pi * 1.2 + k)) for i in range(21)]
        w = [0.11 * math.sin(math.pi * min(i / 20 * 0.85 + 0.15, 1.0)) ** 0.6 * (i / 20) ** 0.6 for i in range(21)]
        ribbon(sc, "streak", pts, w, flame_mat("strm%d" % k, stops=FIRE_HOT, dpow=1.3, dk=0.55, vk=0.0, bias=0.1))


def puff_frame(sc, k):
    """Cartoon cloud: a cluster of spheres with banded neutral toon shading (lit top-left, soft shadow bottom-right)."""
    rnd = random.Random(77 + k * 13)
    m = bpy.data.materials.new("puff%d" % k)
    G = Graph(m)
    geo = G.N.n("ShaderNodeNewGeometry")
    dot = G.N.n("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    dot.inputs[1].default_value = Vector((-0.45, 0.55, 0.7)).normalized()
    G.t.links.new(geo.outputs["Normal"], dot.inputs[0])
    lit = G.op("MULTIPLY", G.op("ADD", dot.outputs["Value"], 1.0), 0.5)
    emit_color(G, ramp_node(G, lit, PUFF, soft=0.08))
    count = 7 + rnd.randint(0, 2)
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.0, 0.5) if i else 0.0
        rad = rnd.uniform(0.34, 0.5) if i else 0.55
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=rad, location=(math.cos(a) * r, math.sin(a) * r * 0.75 - 0.08, 0.0))
        ob = bpy.context.active_object
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        ob.data.materials.append(m)
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
        link(sc, ob)
    # a flat tuft (curl) on the lit side: tiny extra sphere row to give the classic anime bumpy top
    for i in range(3):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=rnd.uniform(0.18, 0.26), location=(rnd.uniform(-0.55, 0.55), rnd.uniform(0.25, 0.5), 0.0))
        ob = bpy.context.active_object
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        ob.data.materials.append(m)
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
        link(sc, ob)


def strip_scene(name, w, h, samples, builder):
    sc = new_scene(name, (w, h), frames=1, samples=samples, ortho=4.0)  # ortho_scale = largest side (width 4 -> height 1)
    builder(sc)
    return sc


def streak_builder(sc):
    rnd = random.Random(5)
    spec = [(0.2, 0.075, 1.7, 0.0), (0.36, 0.05, 1.3, 0.9), (0.52, 0.085, 1.9, 1.8), (0.68, 0.045, 1.2, 2.5), (0.84, 0.06, 1.5, 3.3)]
    # rows (y fractions of the 1 stud tall strip), each streak: length L, width w; copies at +-4 so the strip tiles in u
    for i, (yf, w, L, ph) in enumerate(spec):
        x0 = (i * 1.37) % 4.0 - 2.0
        for off in (-4.0, 0.0, 4.0):
            pts = []
            n = 40
            for j in range(n + 1):
                t = j / n
                x = x0 + off - L * (1 - t)  # head at x0+off (right), tail trails left
                y = (yf - 0.5) + 0.07 * math.sin(t * 5.5 + ph) * (1 - t * 0.3) + 0.04 * t
                pts.append((x, y))
            wid = [w * math.sin(math.pi * min(0.5 + (j / n) * 0.5, 1.0)) ** 0.5 * (j / n) ** 0.55 for j in range(n + 1)]
            wid = [w * (j / n) ** 0.65 * (1 - 0.65 * (j / n) ** 6) for j in range(n + 1)]
            ribbon(sc, "streak%d_%d" % (i, off), pts, wid, flame_mat("sk%d_%d" % (i, off), stops=FIRE_HOT, dpow=0.7, dk=1.0, vk=0.0, bias=-0.04))


def flamestrip_builder(sc):
    rnd = random.Random(9)
    # a hot base band along the bottom, tongues rising; copies at +-4 so it tiles
    n_t = 11
    for k in range(n_t):
        xc = -2.0 + 4.0 * (k + 0.5) / n_t
        H = rnd.uniform(0.45, 0.8)
        for off in (-4.0, 0.0, 4.0):
            pts = tongue_line((xc + off, -0.5), H, rnd.uniform(-0.25, 0.25), rnd.uniform(-0.8, 0.8), rnd.uniform(-1.4, 1.4), n=30)
            ribbon(sc, "t%d_%d" % (k, off), pts, tongue_w(0.17, n=30), flame_mat("fs%d_%d" % (k, off), dk=0.6, vk=0.5), 0.0 + 0.001 * k)
    for off in (-4.0, 0.0, 4.0):
        pts = [(-2.2 + off + 4.4 * i / 20, -0.47) for i in range(21)]
        ribbon(sc, "base%d" % off, pts, [0.07] * 21, uvmat("basem%d" % off, lambda G, d, v: G.op("SUBTRACT", 0.62, G.op("MULTIPLY", d, 0.45)), FIRE_HOT), 0.01)


def trail_scene():
    """Thick flame ribbon (1024x512): a wide hot head on the left tapering to the right, with flame tongues peeling off the top
    and bottom edges and curling back, like the owner's trail reference."""
    sc = new_scene("fireTrailFlame", (1024, 512), frames=1, samples=96, ortho=4.0)
    n = 60
    pts, wid = [], []
    for j in range(n + 1):
        t = j / n
        pts.append((-1.85 + 3.7 * t, 0.05 * math.sin(t * 6.0)))
        head = 0.25 + 0.75 * math.sin(min(t / 0.14, 1.0) * math.pi / 2) ** 0.6
        wid.append(0.56 * head * (1 - t) ** 0.75 * (1 + 0.05 * math.sin(t * 17)))
    top = [(0.10, -0.95, 0.9, 0.16, -1.0), (0.28, -0.8, 1.0, 0.15, -1.2), (0.46, -0.7, 0.9, 0.13, -1.0), (0.64, -0.6, 0.7, 0.1, -0.8)]
    bot = [(0.18, -2.2, 0.8, 0.12, 1.0), (0.38, -2.3, 0.75, 0.11, 1.0), (0.58, -2.3, 0.6, 0.09, 1.0)]
    k = 0
    for t, lean, ln, w, cu in top + bot:
        i = int(t * n)
        px, py = pts[i]
        sgn = 1 if lean > -1.5 else -1
        e = wid[i] * 0.55 * sgn
        flame_design(sc, "pl%d" % k, (px, py + e), ln, w, lean, 0.0, cu * (1 if sgn > 0 else -1), -0.08 - 0.02 * k, [], core=False, n=32)
        k += 1
    ribbon(sc, "glow", pts, [w * 1.25 + 0.02 for w in wid], halo_mat("trailglow", peak=0.45), -0.5)
    ribbon(sc, "body", pts, wid, flame_mat("trbody", stops=FIRE_HOT, dpow=0.8, dk=1.0, vk=0.5, bias=0.02), 0.0)
    cp = pts[:int(n * 0.7)]
    ribbon(sc, "core", cp, [w * 0.45 * (1 - (j / len(cp)) ** 2.2) for j, w in enumerate(wid[:int(n * 0.7)])], flame_mat("trcore", stops=CORE, dpow=0.8, dk=0.9, vk=0.4, bias=0.1), 0.05)
    return sc


def ring_scene():
    sc = new_scene("fireRingGround", 1024, frames=1, samples=96, ortho=4.0)
    rnd = random.Random(33)
    zc = [0.0]

    def circle(R, w0, w1, spin, turns, nm, stops, phase=0.0, n=160):
        pts, wid = [], []
        for i in range(n + 1):
            t = i / n
            a = phase + spin * 2 * math.pi * turns * t
            rr = R * (1 + 0.018 * math.sin(a * 5 + phase))
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
            wid.append((w0 + (w1 - w0) * math.sin(math.pi * t) ** 0.8) * (0.85 + 0.15 * math.sin(a * 7)))
        zc[0] += 0.01
        ribbon(sc, nm, pts, wid, flame_mat(nm + "m", stops=stops, dpow=0.7, dk=1.0, vk=0.0, bias=-0.02), zc[0])
    # thick outer ring: two overlapping crescents so the width swells and thins like a hand-drawn swoosh
    circle(1.62, 0.02, 0.13, 1, 1.0, "outerA", FIRE_HOT, 0.0)
    circle(1.62, 0.02, 0.11, 1, 1.0, "outerB", FIRE, math.pi)
    circle(1.34, 0.015, 0.09, -1, 0.9, "midA", FIRE_HOT, 1.0)
    circle(1.34, 0.015, 0.08, -1, 0.9, "midB", FIRE, 1.0 + math.pi)
    circle(1.06, 0.012, 0.07, 1, 0.9, "innerA", FIRE_HOT, 2.3)
    circle(0.80, 0.01, 0.05, -1, 0.8, "coreA", FIRE, 0.4)
    # little outward flame ticks around the outer ring
    for k in range(18):
        a = 2 * math.pi * k / 18 + rnd.uniform(-0.1, 0.1)
        R = 1.62
        bx, by = math.cos(a) * R, math.sin(a) * R
        lean = a - math.pi / 2 + rnd.uniform(-0.35, 0.2)   # tongue_line points "up" at lean 0 -> rotate to point outward with a swirl
        pts = tongue_line((bx, by), rnd.uniform(0.3, 0.55), lean, rnd.uniform(0.5, 1.1), rnd.uniform(0.3, 1.0), n=18)
        ribbon(sc, "tick%d" % k, pts, tongue_w(0.08, n=18), flame_mat("tickm%d" % k, dk=1.0, vk=0.45), 0.2 + 0.001 * k)
    return sc


def ellipse_pts(rx, ry, rot=0.0, count=48):
    out = []
    for i in range(count):
        t = 2 * math.pi * i / count
        x, y = math.cos(t) * rx, math.sin(t) * ry
        out.append((x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)))
    return out


def footprint_scene(mirror):
    """Raptor print: solid glowing pads (heel + three toes with claw tips, banded rim / body / hot core) with a small flame
    tongue curling up off every pad, so a stamped print reads as burning ground."""
    nm = "fireFootprint" + ("R" if mirror else "L")
    sc = new_scene(nm, 256, frames=1, samples=128, ortho=2.0)
    s = -1.0 if mirror else 1.0
    z = [0.0]

    def pad(pts, radius, cx, cy, stops=FIRE_HOT, power=0.9):
        z[0] += 0.01
        ob = fan(sc, "pad", pts, radmat("pm%d%s" % (int(z[0] * 100), nm), radius, stops, power=power), z=z[0])
        if cx is not None:
            ob.location = (cx, cy, z[0])
        return ob
    hub = (0.04, -0.3)
    toes = [(math.radians(90 + 52), 0.62, 0.34), (math.radians(90 + 4), 0.8, 0.4), (math.radians(90 - 44), 0.64, 0.34)]
    for ang, dist, ln in toes:
        cx, cy = hub[0] + math.cos(ang) * dist * 0.6, hub[1] + math.sin(ang) * dist * 0.6
        pad(ellipse_pts(0.17, ln * 0.66, ang - math.pi / 2), ln * 0.66, cx, cy)
        tx, ty = hub[0] + math.cos(ang) * (dist * 0.6 + ln * 0.66 + 0.02), hub[1] + math.sin(ang) * (dist * 0.6 + ln * 0.66 + 0.02)
        side = (-math.sin(ang), math.cos(ang))
        pad([(tx + side[0] * 0.08, ty + side[1] * 0.08), (tx + math.cos(ang) * 0.22, ty + math.sin(ang) * 0.22), (tx - side[0] * 0.08, ty - side[1] * 0.08)], 0.22, None, None, stops=FIRE, power=0.6)
        flame_design(sc, "tf%d" % int(ang * 10), (cx, cy - 0.05), 0.55, 0.13, 0.0, 0.0, 0.8 * (1 if ang > math.pi / 2 else -1), 0.5 + z[0], [], core=False, n=24)
    pad(ellipse_pts(0.36, 0.28, 0.0), 0.36, hub[0], -0.74)
    flame_design(sc, "hf", (hub[0] + 0.1, -0.7), 0.6, 0.16, 0.0, 0.0, 0.9, 0.9, [], core=False, n=24)
    for ob in sc.objects:
        if ob.type == "MESH":
            ob.location.x *= s
            ob.scale.x = s
    return sc


def main():
    opts = parse_args()
    out = (opts["out"] or Path("resources/effects/vfx-lab")).resolve()
    frames_dir = (opts["frames"]).resolve()
    only = opts["only"]
    samples = opts["samples"]
    out.mkdir(parents=True, exist_ok=True)

    def render_still(sc, path):
        sc.render.filepath = str(path)
        bpy.ops.render.render(write_still=True, scene=sc.name)

    def sheet(name, builder, size, n=16, smp=96):
        d = frames_dir / name
        d.mkdir(parents=True, exist_ok=True)
        for f in range(n):
            sc = new_scene(f"{name}_{f}", size, frames=1, samples=samples or smp, ortho=2.0)
            builder(sc, f)
            render_still(sc, d / f"f_{f + 1:04d}.png")
        print("rendered", name)

    def want(name):
        return not only or only == name

    if want("fireTongueSheet"):
        sheet("fireTongueSheet", lambda sc, f: tongue_frame(sc, f, False), 256)
    if want("fireTongueBig"):
        sheet("fireTongueBig", big_frame, 512, n=4, smp=128)
    if want("fireTongueSwirl"):
        sheet("fireTongueSwirl", swirl_frame, 512, n=4, smp=128)
    if want("fireClusterSheet"):
        sheet("fireClusterSheet", lambda sc, f: tongue_frame(sc, f, True), 256)
    if want("fireSparkSheet"):
        sheet("fireSparkSheet", spark_frame, 128, smp=128)
    if want("firePuffSheet"):
        sheet("firePuffSheet", puff_frame, 256, smp=96)
    if want("fireStreakStrip"):
        render_still(strip_scene("fireStreakStrip", 1024, 256, samples or 96, streak_builder), out / "fireStreakStrip.png")
    if want("fireFlameStrip"):
        render_still(strip_scene("fireFlameStrip", 1024, 256, samples or 96, flamestrip_builder), out / "fireFlameStrip.png")
    if want("fireTrailFlame"):
        render_still(trail_scene(), out / "fireTrailFlame.png")
    if want("fireRingGround"):
        render_still(ring_scene(), out / "fireRingGround.png")
    if want("fireFootprintL"):
        render_still(footprint_scene(False), out / "fireFootprintL.png")
    if want("fireFootprintR"):
        render_still(footprint_scene(True), out / "fireFootprintR.png")
    if opts["blend"]:
        opts["blend"].parent.mkdir(parents=True, exist_ok=True)
        old = bpy.data.scenes.get("Scene")
        if old is not None and len(bpy.data.scenes) > 1:
            bpy.data.scenes.remove(old)
        bpy.ops.wm.save_as_mainfile(filepath=str(opts["blend"].resolve()), compress=True)
        print("saved", opts["blend"])


main()
