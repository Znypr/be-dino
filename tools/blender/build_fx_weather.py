"""Be Dino! weather particle textures (BD-131). Real Blender renders, headless, Cycles. Nothing is drawn pixel by pixel in Python.

Regenerate everything (renders the frames, then Pillow only pastes the finished 128 px frames into 4 x 4 sheets):

    python tools/render_weather_textures.py

or by hand:

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup \
        --python tools/blender/build_fx_weather.py -- --frames build/fx-weather-frames --out resources/effects/fx-v2 \
        --blend tools/blender/fx_weather_v1.blend [--only snowFlakeSheet] [--samples 64]

One Blender scene per texture, so the .blend opens as a small catalogue. Flipbook scenes hold 16 collections (one per frame,
shown by animated visibility) and are rendered frame by frame. White on straight alpha everywhere (the runtime tints them
with Color / Color3); nothing here is coloured.

  slot (EffectAssets key)  scene             size        what is rendered
  rainStreak               rainStreak        64x256      modelled stretched ellipsoid, facing-soft emission, bright head, long fading tail
  lightningBolt            lightningBolt     512x128     tileable jagged strip: bell-profile strokes (core, glow) + forks, geometry wraps
  snowFlakeSheet           snowFlakeSheet    4x4 of 128  16 modelled flakes (dendrites, plates, needles, pellets), compositor glow
  ashFlake                 ashFlake          4x4 of 128  16 noisy charred flakes, mottled alpha
  emberSpark               emberSpark        4x4 of 128  16 glowing sparks: beads, streaks, twins, crackles
  dustSand                 dustSand          4x4 of 128  16 grain sprays over a faint haze
  auroraCurtain            auroraCurtain     4x4 of 128  16-frame LOOP of a folded curtain; folds read bright where they turn edge-on
  bloodMoonMotes           bloodMoonMotes    4x4 of 128  16 soft orbs, bubble rings, twins and wisps
  bloodMoonDisc            bloodMoonDisc     512x512     lit sphere with craters; luminance becomes alpha, RGB white
"""
import math
import random
import sys
from pathlib import Path

import bpy

CELL = 128


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"frames": Path("build/fx-weather-frames"), "out": Path("resources/effects/fx-v2"), "blend": None, "only": None, "samples": None}
    i = 0
    while i < len(argv):
        key = argv[i].lstrip("-")
        if key in opts and i + 1 < len(argv):
            v = argv[i + 1]
            opts[key] = v if key == "only" else (int(v) if key == "samples" else Path(v))
            i += 2
        else:
            i += 1
    return opts


# --------------------------------------------------------------------------- scene helpers
def new_scene(name, w, h, ortho, frames=1, samples=96):
    sc = bpy.data.scenes.new(name)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = w, h
    r.resolution_percentage = 100
    r.film_transparent = True
    r.filter_size = 1.3
    r.dither_intensity = 0.0
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    r.image_settings.compression = 15
    c = sc.cycles
    c.device = "CPU"
    c.samples = samples
    c.use_denoising = False
    c.transparent_max_bounces = 16
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = "sRGB"
    sc.sequencer_colorspace_settings.name = "sRGB"
    sc.frame_start, sc.frame_end = 1, frames
    wd = bpy.data.worlds.new(name + "_world")
    wd.use_nodes = True
    bg = next(n for n in wd.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = 0.0
    sc.world = wd
    cam = bpy.data.cameras.new(name + "_cam")
    cam.type = "ORTHO"
    cam.ortho_scale = ortho   # applies to the longer side
    cam.clip_start, cam.clip_end = 0.1, 200.0
    cobj = bpy.data.objects.new(name + "_cam", cam)
    cobj.location = (0, 0, 60)
    sc.collection.objects.link(cobj)
    sc.camera = cobj
    return sc


class Nodes:
    def __init__(self, mat):
        mat.use_nodes = True
        self.t = mat.node_tree
        self.t.nodes.clear()
        self.x = -1400

    def n(self, kind, **props):
        node = self.t.nodes.new(kind)
        node.location = (self.x, 0)
        self.x += 220
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def link(self, a, b, sa=0, sb=0):
        self.t.links.new(a.outputs[sa], b.inputs[sb])

    def math(self, op, a, b=None, clamp=False):
        m = self.n("ShaderNodeMath", operation=op)
        m.use_clamp = clamp
        for idx, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[idx].default_value = v
            else:
                self.t.links.new(v.outputs[0], m.inputs[idx])
        return m

    def mapr(self, val, lo, hi, kind="SMOOTHERSTEP", out_lo=0.0, out_hi=1.0):
        m = self.n("ShaderNodeMapRange", interpolation_type=kind, clamp=True)
        self.t.links.new(val.outputs[0], m.inputs["Value"])
        m.inputs["From Min"].default_value = lo
        m.inputs["From Max"].default_value = hi
        m.inputs["To Min"].default_value = out_lo
        m.inputs["To Max"].default_value = out_hi
        return m

    def separate(self, vec_node, socket=0):
        s = self.n("ShaderNodeSeparateXYZ")
        self.t.links.new(vec_node.outputs[socket], s.inputs[0])
        return s

    def facing(self, power=1.0):
        """|N . view| (1 facing the camera, 0 at the silhouette), raised to `power`: soft rounded edges on real 3D forms."""
        g = self.n("ShaderNodeNewGeometry")
        d = self.n("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        self.t.links.new(g.outputs["Normal"], d.inputs[0])
        self.t.links.new(g.outputs["Incoming"], d.inputs[1])
        a = self.math("ABSOLUTE", None)
        self.t.links.new(d.outputs["Value"], a.inputs[0])
        return self.math("POWER", a, power) if power != 1.0 else a


def finish_emission(N, alpha_node, strength=1.0):
    """Output = white emission with the given alpha node (output 0, 0..1)."""
    c = N.math("MAXIMUM", N.math("MINIMUM", alpha_node, 1.0), 0.0)
    emis = N.n("ShaderNodeEmission")
    emis.inputs["Color"].default_value = (1, 1, 1, 1)
    emis.inputs["Strength"].default_value = strength
    clear = N.n("ShaderNodeBsdfTransparent")
    mix = N.n("ShaderNodeMixShader")
    N.link(c, mix, 0, "Fac")
    N.link(clear, mix, 0, 1)
    N.link(emis, mix, 0, 2)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(mix, out, 0, 0)


def solid_mat(name, alpha=1.0):
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    emis = N.n("ShaderNodeEmission")
    emis.inputs["Color"].default_value = (1, 1, 1, 1)
    clear = N.n("ShaderNodeBsdfTransparent")
    mix = N.n("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = alpha
    N.link(clear, mix, 0, 1)
    N.link(emis, mix, 0, 2)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(mix, out, 0, 0)
    return mat


def soft_orb_mat(name, power=1.2, strength=1.0):
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    finish_emission(N, N.facing(power), strength)
    return mat


def link(coll_or_sc, obj):
    (coll_or_sc.collection if hasattr(coll_or_sc, "collection") else coll_or_sc).objects.link(obj)
    return obj


# --------------------------------------------------------------------------- tiny 2D geometry kit (flat meshes in the XY plane)
class Geo:
    def __init__(self, zstep=0.0, z0=0.0):
        """zstep > 0 lifts every new face a little: Cycles skips coplanar hits, so stacked soft layers need distinct depths."""
        self.v, self.f, self.uv = [], [], []
        self.zstep, self.z = zstep, z0

    def _add(self, pts, uvs=None):
        base = len(self.v)
        self.v += [(x, y, self.z) for x, y in pts]
        self.z += self.zstep
        self.f.append(tuple(range(base, base + len(pts))))
        self.uv.append(uvs or [(0, 0)] * len(pts))

    def tri(self, a, b, c):
        self._add([a, b, c])

    def quad(self, a, b, c, d, uvs=None):
        self._add([a, b, c, d], uvs)

    def poly(self, pts):
        """Star-shaped polygon as a fan around its centroid."""
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        for i in range(len(pts)):
            self.tri((cx, cy), pts[i], pts[(i + 1) % len(pts)])

    def disc(self, c, r, n=28):
        self.poly([(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)])

    def ellipse(self, c, rx, ry, rot=0.0, n=28):
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = rx * math.cos(a), ry * math.sin(a)
            pts.append((c[0] + x * math.cos(rot) - y * math.sin(rot), c[1] + x * math.sin(rot) + y * math.cos(rot)))
        self.poly(pts)

    def stroke(self, pts, widths, uv=False):
        """Polyline with a width per point (half widths = widths/2). uv=True writes u along the line, v across (0..1)."""
        left, right = [], []
        for i, p in enumerate(pts):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, len(pts) - 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            hw = widths[i] / 2.0
            left.append((p[0] + nx * hw, p[1] + ny * hw))
            right.append((p[0] - nx * hw, p[1] - ny * hw))
        total = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)) or 1.0
        run = 0.0
        for i in range(len(pts) - 1):
            u0 = run / total
            run += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            u1 = run / total
            self.quad(left[i], left[i + 1], right[i + 1], right[i], [(u0, 1), (u1, 1), (u1, 0), (u0, 0)] if uv else None)

    def transformed(self, rot=0.0, scale=1.0, offset=(0.0, 0.0)):
        g = Geo()
        c, s = math.cos(rot), math.sin(rot)
        g.v = [((x * c - y * s) * scale + offset[0], (x * s + y * c) * scale + offset[1], z) for x, y, z in self.v]
        g.f, g.uv = list(self.f), list(self.uv)
        return g

    def obj(self, name, mat, with_uv=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        if with_uv:
            layer = me.uv_layers.new(name="UVMap")
            i = 0
            for fi, face in enumerate(self.f):
                for k in range(len(face)):
                    layer.data[i].uv = self.uv[fi][k]
                    i += 1
        me.materials.append(mat)
        return bpy.data.objects.new(name, me)


def rot_pt(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


# --------------------------------------------------------------------------- flipbook plumbing
class FrameSet:
    """Objects of one flipbook frame: linked to the scene and visible in render only on frame i (animated hide_render, constant)."""

    def __init__(self, sc, i, frames):
        self.sc, self.i, self.frames = sc, i, frames
        self.collection = self
        self.objects = self

    def link(self, obj):
        self.sc.collection.objects.link(obj)
        for f, hidden in ((1, self.i != 1), (self.i, False), (self.i + 1, True)):
            if f < 1 or f > self.frames + 1:
                continue
            obj.hide_render = hidden
            obj.keyframe_insert("hide_render", frame=f)
        for fc in all_fcurves(obj):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def frame_collection(sc, name, i, frames=16):
    return FrameSet(sc, i, frames)


def all_fcurves(idb):
    ad = idb.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def white_from_alpha(sc):
    """Compositor: keep the render's alpha, force RGB to pure white (layered transparent beads leave RGB slightly under white)."""
    ng = bpy.data.node_groups.new(sc.name + "_comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = sc
    white = ng.nodes.new("CompositorNodeRGB")
    white.outputs[0].default_value = (1, 1, 1, 1)
    sa = ng.nodes.new("CompositorNodeSetAlpha")
    sa.inputs["Type"].default_value = "Replace Alpha"
    ng.links.new(white.outputs[0], sa.inputs["Image"])
    ng.links.new(rl.outputs["Alpha"], sa.inputs["Alpha"])
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(sa.outputs[0], out.inputs[0])


def glow_compositor(sc, layers):
    """Render Layers -> Gaussian blurs (px radius each) stacked with Alpha Over -> output.
    layers = [(blur_px, factor), ...] widest first; the widest is the background, each next one is laid over it with `factor`.
    The blur runs on the premultiplied render, so RGB stays white wherever alpha > 0."""
    ng = bpy.data.node_groups.new(sc.name + "_comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = sc
    rl.location = (-600, 0)

    def blur(px, y):
        if px <= 0:
            return rl
        b = ng.nodes.new("CompositorNodeBlur")
        b.location = (-300, y)
        size = b.inputs["Size"]
        size.default_value = (px, px, 0.0) if len(size.default_value) == 3 else (px, px)
        b.inputs["Extend Bounds"].default_value = False
        ng.links.new(rl.outputs["Image"], b.inputs["Image"])
        return b
    acc = blur(layers[0][0], 300)
    for k, (px, factor) in enumerate(layers[1:], start=1):
        over = ng.nodes.new("CompositorNodeAlphaOver")
        over.location = (-100 + 200 * k, 0)
        over.inputs["Factor"].default_value = factor
        ng.links.new(acc.outputs[0], over.inputs["Background"])
        ng.links.new(blur(px, 300 - 200 * k).outputs[0], over.inputs["Foreground"])
        acc = over
    out = ng.nodes.new("NodeGroupOutput")
    out.location = (600, 0)
    ng.links.new(acc.outputs[0], out.inputs[0])


# --------------------------------------------------------------------------- RAIN STREAK 64 x 256
def build_rain(opts):
    sc = new_scene("rainStreak", 64, 256, 4.0, samples=opts["samples"] or 128)
    mat = bpy.data.materials.new("rain_mat")
    N = Nodes(mat)
    # real 3D form: a long ellipsoid (rounded head at the bottom). Alpha = soft facing profile x a tail fade along the length.
    pos = N.n("ShaderNodeTexCoord")
    sep = N.separate(pos, "Object")
    # object y runs -1 (head, bottom) .. +1 (tail tip); the head stays solid and the tail dissolves
    ycoord = N.n("ShaderNodeMath", operation="ADD")
    N.t.links.new(sep.outputs[1], ycoord.inputs[0])
    ycoord.inputs[1].default_value = 0.0
    fade = N.mapr(ycoord, 1.0, -0.55, "SMOOTHERSTEP")          # 0 at the tail tip, 1 from -0.55 down to the head
    body = N.facing(0.9)
    alpha = N.math("MULTIPLY", body, N.math("MULTIPLY", fade, 0.92))
    finish_emission(N, alpha)
    me = bpy.data.meshes.new("rain_ellipsoid")
    bpy.context.view_layer.update()
    ob = bpy.data.objects.new("rain_streak", me)
    link(sc, ob)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=64, radius=1.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob.scale = (0.085, 1.72, 0.085)   # 5.4 px wide, ~220 px long (the frame is +-0.5 x +-2)
    ob.location = (0, -0.1, 0)
    return {"rainStreak": sc}


# --------------------------------------------------------------------------- LIGHTNING BOLT STRIP 512 x 128 (tileable)
def build_bolt(opts):
    W, H = 512, 128
    unit = H  # 1 world unit = 128 px
    sc = new_scene("lightningBolt", W, H, W / unit, samples=opts["samples"] or 128)   # ortho_scale covers the long side: 4 units
    sc.cycles.transparent_max_bounces = 128   # dozens of coplanar glow beads overlap per pixel
    rnd = random.Random(1311)

    def bell_mat(name, power, strength=1.0):
        mat = bpy.data.materials.new(name)
        N = Nodes(mat)
        uvn = N.n("ShaderNodeTexCoord")
        sep = N.separate(uvn, "UV")
        # v across the stroke: 0.5 is the centre line
        vsub = N.n("ShaderNodeMath", operation="SUBTRACT")
        N.t.links.new(sep.outputs[1], vsub.inputs[0])
        vsub.inputs[1].default_value = 0.5
        vabs = N.n("ShaderNodeMath", operation="ABSOLUTE")
        N.t.links.new(vsub.outputs[0], vabs.inputs[0])
        v2 = N.math("MULTIPLY", vabs, 2.0)                     # 0 on the line, 1 at the stroke edge
        prof = N.math("POWER", N.mapr(v2, 1.0, 0.0), power)    # smooth bell
        finish_emission(N, prof, strength)
        return mat
    core_mat = bell_mat("bolt_core", 0.45)
    # soft radial bead used for the glow: dozens of overlapping beads along the path give an even glow with no fold-over at corners
    bead_mat = bpy.data.materials.new("bolt_bead")
    BN = Nodes(bead_mat)
    btc = BN.n("ShaderNodeTexCoord")
    bsub = BN.n("ShaderNodeVectorMath", operation="SUBTRACT")
    bsub.inputs[1].default_value = (0.5, 0.5, 0.0)
    BN.link(btc, bsub, "UV", 0)
    bln = BN.n("ShaderNodeVectorMath", operation="LENGTH")
    BN.link(bsub, bln, 0, 0)
    br = BN.math("MULTIPLY", 0.0, 2.0)
    BN.link(bln, br, 1, 0)
    finish_emission(BN, BN.math("MULTIPLY", BN.mapr(br, 1.0, 0.0, "SMOOTHERSTEP"), 0.13))
    # periodic main path: points every ~30 px, first == last in y so the strip tiles; a few bigger jogs, mostly gentle
    pts = [(0.0, 0.0)]
    x, y, sgn = 0.0, 0.0, 1
    while True:
        x += rnd.uniform(16, 44)
        if x > W - 26:
            break
        if rnd.random() < 0.55:
            sgn = -sgn
        y = max(-38.0, min(38.0, y + sgn * rnd.uniform(9, 30)))
        pts.append((x, y))
    pts.append((W - 12.0, y * 0.4))
    pts.append((W, 0.0))
    n = len(pts)
    forks = []
    for _ in range(4):
        i = rnd.randrange(2, n - 2)
        sgn = rnd.choice((-1, 1))
        ang = math.radians(rnd.uniform(25, 50)) * sgn
        length = rnd.uniform(70, 110)
        segs = 4
        fp = [pts[i]]
        a = ang
        for k in range(segs):
            a += math.radians(rnd.uniform(-30, 30))
            step = length / segs
            fp.append((fp[-1][0] + step * math.cos(a), max(-44, min(44, fp[-1][1] + step * math.sin(a)))))
        forks.append(fp)

    def px(p, dx=0):
        return ((p[0] + dx) / unit - W / unit / 2, p[1] / unit)

    def along(poly, spacing):
        out = []
        for k in range(len(poly) - 1):
            (x0, y0), (x1, y1) = poly[k], poly[k + 1]
            ln = math.hypot(x1 - x0, y1 - y0)
            m = max(1, int(ln / spacing))
            for j in range(m):
                out.append((x0 + (x1 - x0) * j / m, y0 + (y1 - y0) * j / m))
        out.append(poly[-1])
        return out

    zc = 0.0
    for dx in (-W, 0, W):
        for tag, poly, taper in [("main", pts, 1.0)] + [(f"fork{k}", fp, 0.55) for k, fp in enumerate(forks)]:
            dense = along(poly, 3.0 if tag == "main" else 1.6)
            g = Geo(0.0012, zc)
            for j, p in enumerate(dense):
                f = 1.0 - (j / len(dense)) * 0.85 if tag != "main" else 1.0
                for rad in (17 * f * (1.0 if tag == "main" else 0.8), 8 * f * (1.0 if tag == "main" else 0.8)):     # wide glow and a tighter halo, in px
                    cx, cy = px(p, dx)
                    r = rad / unit
                    g.quad((cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r), [(0, 0), (1, 0), (1, 1), (0, 1)])
            zc = g.z + 0.01
            link(sc, g.obj(f"bolt_glow_{tag}_{dx}", bead_mat, True))
            cp = [px(p, dx) for p in poly]
            m = len(cp)
            g = Geo(0.0012, zc + 1.0)
            if tag == "main":
                g.stroke(cp, [0.055] * m, uv=True)
            else:
                g.stroke(cp, [0.045 * (1 - k / m) + 0.005 for k in range(m)], uv=True)
            link(sc, g.obj(f"bolt_core_{tag}_{dx}", core_mat, True))
    white_from_alpha(sc)
    return {"lightningBolt": sc}


# --------------------------------------------------------------------------- shared flipbook scene
def flipbook_scene(name, opts, samples=64):
    return new_scene(name, CELL, CELL, 2.0, frames=16, samples=opts["samples"] or samples)


# --------------------------------------------------------------------------- SNOW FLAKES (16 modelled flakes)
def arm_branches(g, ang, length, w, pairs, blen, bang=60.0, taper=True):
    """One crystal arm along angle `ang` with `pairs` of side branches; arm and branches taper to a point."""
    d = (math.cos(ang), math.sin(ang))
    tip = (d[0] * length, d[1] * length)
    g.stroke([(0, 0), tip], [w, 0.0 if taper else w * 0.7])
    for k in range(1, pairs + 1):
        t = k / (pairs + 1)
        base = (d[0] * length * t, d[1] * length * t)
        bl = blen * (1.0 - 0.55 * t)
        for s in (-1, 1):
            a2 = ang + math.radians(bang) * s
            end = (base[0] + bl * math.cos(a2), base[1] + bl * math.sin(a2))
            g.stroke([base, end], [w * 0.75, 0.0])


def hexagon(g, r, rot=0.0, hole=0.0):
    outer = [(r * math.cos(rot + i * math.pi / 3), r * math.sin(rot + i * math.pi / 3)) for i in range(6)]
    if hole <= 0:
        g.poly(outer)
        return
    inner = [(hole * math.cos(rot + i * math.pi / 3), hole * math.sin(rot + i * math.pi / 3)) for i in range(6)]
    for i in range(6):
        g.quad(outer[i], outer[(i + 1) % 6], inner[(i + 1) % 6], inner[i])


def snow_variant(i, rnd):
    g = Geo()
    L = 0.66
    if i == 0:      # classic dendrite
        for k in range(6): arm_branches(g, k * math.pi / 3, L, 0.115, 2, 0.28)
        g.disc((0, 0), 0.09, 6)
    elif i == 1:    # fern dendrite, many fine branches
        for k in range(6): arm_branches(g, k * math.pi / 3, L, 0.085, 3, 0.22, 52)
        hexagon(g, 0.10)
    elif i == 2:    # chunky star
        for k in range(6): arm_branches(g, k * math.pi / 3, L, 0.17, 0, 0.0)
        hexagon(g, 0.17)
    elif i == 3:    # plate with a hole
        hexagon(g, 0.58, math.pi / 6, 0.3)
        g.disc((0, 0), 0.1, 6)
    elif i == 4:    # plate with short arms
        hexagon(g, 0.34, 0.0)
        for k in range(6): arm_branches(g, k * math.pi / 3 + math.pi / 6, 0.66, 0.1, 1, 0.2, 55)
    elif i == 5:    # stellar plate, 12 points
        pts = []
        for k in range(12):
            r = 0.64 if k % 2 == 0 else 0.34
            pts.append((r * math.cos(k * math.pi / 6), r * math.sin(k * math.pi / 6)))
        g.poly(pts)
    elif i == 6:    # two crossing needles
        for a in (0.2, 0.2 + math.pi / 2.4):
            d = (math.cos(a), math.sin(a))
            g.stroke([(-d[0] * 0.66, -d[1] * 0.66), (0, 0), (d[0] * 0.66, d[1] * 0.66)], [0.0, 0.1, 0.0])
    elif i == 7:    # three needles at 60 degrees
        for k in range(3):
            a = k * math.pi / 3
            d = (math.cos(a), math.sin(a))
            g.stroke([(-d[0] * 0.64, -d[1] * 0.64), (0, 0), (d[0] * 0.64, d[1] * 0.64)], [0.0, 0.085, 0.0])
    elif i == 8:    # round snow pellet (graupel)
        g.disc((0, 0), 0.3, 32)
    elif i == 9:    # fluffy aggregate of 5 pellets
        for (x, y, r) in ((0, 0, .24), (.27, .1, .19), (-.25, .12, .2), (.04, -.28, .2), (-.12, .3, .15)):
            g.disc((x, y), r, 24)
    elif i == 10:   # small simple dendrite
        for k in range(6): arm_branches(g, k * math.pi / 3, 0.5, 0.11, 1, 0.22)
        g.disc((0, 0), 0.08, 6)
    elif i == 11:   # leaf branches (diamonds)
        for k in range(6):
            a = k * math.pi / 3
            d = (math.cos(a), math.sin(a))
            g.stroke([(0, 0), (d[0] * 0.66, d[1] * 0.66)], [0.07, 0.0])
            for t in (0.3, 0.55):
                c = (d[0] * 0.66 * t, d[1] * 0.66 * t)
                n = (-d[1], d[0])
                g.quad((c[0] + d[0] * .13, c[1] + d[1] * .13), (c[0] + n[0] * .1, c[1] + n[1] * .1),
                       (c[0] - d[0] * .1, c[1] - d[1] * .1), (c[0] - n[0] * .1, c[1] - n[1] * .1))
        g.disc((0, 0), 0.1, 6)
    elif i == 12:   # double star: long and short sets turned 30 degrees
        for k in range(6): arm_branches(g, k * math.pi / 3, 0.66, 0.1, 1, 0.24)
        for k in range(6): arm_branches(g, k * math.pi / 3 + math.pi / 6, 0.4, 0.07, 0, 0.0)
        g.disc((0, 0), 0.1, 6)
    elif i == 13:   # hex ring plate with centre dot
        hexagon(g, 0.55, 0.0, 0.4)
        g.disc((0, 0), 0.13, 20)
    elif i == 14:   # speck trio
        for (x, y, r) in ((-.25, -.1, .12), (.2, .15, .1), (.0, -.32, .08)):
            g.disc((x, y), r, 16)
    else:           # out-of-focus big soft flake (blurred more below)
        for k in range(6): arm_branches(g, k * math.pi / 3, 0.6, 0.2, 0, 0.0)
        hexagon(g, 0.25)
    rot = rnd.uniform(0, math.pi / 3)
    return g.transformed(rot=rot)


def build_snow(opts):
    sc = flipbook_scene("snowFlakeSheet", opts)
    rnd = random.Random(2026)
    mat = solid_mat("snow_mat", 1.0)
    for i in range(16):
        coll = frame_collection(sc, "snow", i + 1)
        ob = snow_variant(i, rnd).obj(f"flake{i + 1}", mat)
        link(coll, ob)
    glow_compositor(sc, [(6.5, 1.0), (1.6, 0.8)])
    return {"snowFlakeSheet": sc}


# --------------------------------------------------------------------------- ASH FLAKES (16 charred flakes)
def ash_poly(rnd, rx, ry, rough, n=11):
    pts = []
    rot = rnd.uniform(0, math.pi)
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.12, 0.12)
        r = 1.0 + rnd.uniform(-rough, rough)
        x, y = rx * r * math.cos(a), ry * r * math.sin(a)
        pts.append((x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)))
    return pts


def build_ash(opts):
    sc = flipbook_scene("ashFlake", opts)
    rnd = random.Random(777)
    mat = bpy.data.materials.new("ash_mat")
    N = Nodes(mat)
    tc = N.n("ShaderNodeTexCoord")
    nz = N.n("ShaderNodeTexNoise", noise_dimensions="3D")
    nz.inputs["Scale"].default_value = 5.5
    nz.inputs["Detail"].default_value = 4.0
    nz.inputs["Roughness"].default_value = 0.6
    N.link(tc, nz, "Object", "Vector")
    m = N.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
    N.t.links.new(nz.outputs["Fac"], m.inputs["Value"])
    m.inputs["From Min"].default_value, m.inputs["From Max"].default_value = 0.3, 0.7
    m.inputs["To Min"].default_value, m.inputs["To Max"].default_value = 0.55, 1.0
    finish_emission(N, m)
    for i in range(16):
        coll = frame_collection(sc, "ash", i + 1)
        g = Geo()
        elong = [1.0, 1.4, 1.9, 2.3, 1.2, 1.6, 1.0, 2.0][i % 8]
        size = [0.5, 0.42, 0.38, 0.33, 0.55, 0.3, 0.46, 0.36][(i * 3) % 8]
        g.poly(ash_poly(rnd, size * elong * 0.72, size / elong ** 0.35 * 0.72, 0.26 + 0.05 * (i % 3)))
        if i % 4 == 1:      # curled edge: a second smaller flake overlapping
            off = (rnd.uniform(-.1, .1), rnd.uniform(-.1, .1))
            g2 = Geo()
            g2.poly(ash_poly(rnd, size * 0.5, size * 0.4, 0.3))
            g.v += [(x + off[0], y + off[1], 0.0) for x, y, _ in g2.v]
            base = len(g.v) - len(g2.v)
            g.f += [tuple(k + base for k in f) for f in g2.f]
            g.uv += g2.uv
        elif i % 4 == 3:    # a tiny crumb beside the flake
            g.disc((0.4 * (1 if i % 2 else -1), 0.32), 0.07, 12)
        link(coll, g.obj(f"ash{i + 1}", mat))
    glow_compositor(sc, [(2.6, 1.0), (0.9, 0.85)])
    return {"ashFlake": sc}


# --------------------------------------------------------------------------- EMBER / LAVA SPARKS (16)
def spark_variant(i, rnd):
    g = Geo()
    g.heads = []
    ang = rnd.uniform(0, 2 * math.pi)
    d = (math.cos(ang), math.sin(ang))
    _disc = g.disc

    def disc(c, r, n=28):
        g.heads.append((c, r))
        _disc(c, r, n)
    g.disc = disc

    def streak(origin, direction, r, length):
        n = 7
        pts = [(origin[0] - direction[0] * length * k / n, origin[1] - direction[1] * length * k / n) for k in range(n + 1)]
        w = [2 * r * (1 - k / n) ** 0.8 for k in range(n + 1)]
        g.stroke(pts, w)
        g.disc(origin, r, 20)
    if i < 4:           # beads of growing size
        g.disc((0, 0), [0.11, 0.15, 0.2, 0.27][i], 24)
    elif i < 8:         # beads with a short tail
        r = [0.1, 0.13, 0.16, 0.19][i - 4]
        o = (d[0] * 0.18, d[1] * 0.18)
        streak(o, d, r, 0.45)
    elif i < 12:        # long streaks
        r = [0.07, 0.09, 0.11, 0.08][i - 8]
        o = (d[0] * 0.38, d[1] * 0.38)
        streak(o, d, r, [0.8, 0.95, 1.0, 0.7][i - 8])
    elif i == 12:       # twin sparks
        for s, off in ((1, 0.28), (-1, 0.22)):
            o = (d[0] * off * s + 0.0, d[1] * off * s)
            streak(o, (d[0] * s, d[1] * s), 0.1, 0.4)
    elif i == 13:       # three small beads flying together
        for k, ln in enumerate((0.55, 0.32, 0.42)):
            a = ang + (k - 1) * 0.9
            dk = (math.cos(a), math.sin(a))
            streak((dk[0] * (0.3 + 0.12 * k) + 0.14 * math.cos(ang + 1.6), dk[1] * (0.3 + 0.12 * k) + 0.14 * math.sin(ang + 1.6)), dk, 0.06, ln)
    elif i == 14:       # crackle: bead with four short tapered rays
        g.disc((0, 0), 0.13, 20)
        for k in range(4):
            a = ang + k * math.pi / 2
            g.stroke([(0, 0), (0.5 * math.cos(a), 0.5 * math.sin(a))], [0.12, 0.0])
    else:               # big soft orb
        g.disc((0, 0), 0.3, 28)
    return g


def radial_bead_mat(name, peak):
    """Soft radial glow disc (smootherstep falloff) used behind bright shapes."""
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    tc = N.n("ShaderNodeTexCoord")
    sub = N.n("ShaderNodeVectorMath", operation="SUBTRACT")
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    N.link(tc, sub, "UV", 0)
    ln = N.n("ShaderNodeVectorMath", operation="LENGTH")
    N.link(sub, ln, 0, 0)
    r = N.math("MULTIPLY", 0.0, 2.0)
    N.link(ln, r, 1, 0)
    finish_emission(N, N.math("MULTIPLY", N.mapr(r, 1.0, 0.0, "SMOOTHERSTEP"), peak))
    return mat


def build_ember(opts):
    sc = flipbook_scene("emberSpark", opts)
    rnd = random.Random(404)
    mat = solid_mat("ember_mat", 1.0)
    bead = radial_bead_mat("ember_bead", 0.5)
    for i in range(16):
        coll = frame_collection(sc, "ember", i + 1)
        g = spark_variant(i, rnd)
        glow = Geo(0.0, -0.05)
        for (c, r) in g.heads:
            rr = min(r * 3.4, 0.74 - math.hypot(*c) * 0.0)
            glow.quad((c[0] - rr, c[1] - rr), (c[0] + rr, c[1] - rr), (c[0] + rr, c[1] + rr), (c[0] - rr, c[1] + rr), [(0, 0), (1, 0), (1, 1), (0, 1)])
            glow.z -= 0.01
        if glow.v:
            link(coll, glow.obj(f"glow{i + 1}", bead, True))
        link(coll, g.obj(f"spark{i + 1}", mat))
    glow_compositor(sc, [(7.0, 1.0), (1.3, 0.9)])
    return {"emberSpark": sc}


# --------------------------------------------------------------------------- DUST / SAND (16 sprays)
def build_dust(opts):
    sc = flipbook_scene("dustSand", opts)
    rnd = random.Random(909)
    grain = solid_mat("grain_mat", 1.0)
    haze = bpy.data.materials.new("haze_mat")
    N = Nodes(haze)
    tc = N.n("ShaderNodeTexCoord")
    sub = N.n("ShaderNodeVectorMath", operation="SUBTRACT")
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    N.link(tc, sub, "UV", 0)
    ln = N.n("ShaderNodeVectorMath", operation="LENGTH")
    N.link(sub, ln, 0, 0)
    r = N.math("MULTIPLY", 0.0, 2.0)
    N.link(ln, r, 1, 0)
    nz = N.n("ShaderNodeTexNoise", noise_dimensions="3D")
    nz.inputs["Scale"].default_value = 3.5
    nz.inputs["Detail"].default_value = 3.0
    N.link(tc, nz, "Generated", "Vector")
    falloff = N.mapr(r, 0.95, 0.15, "SMOOTHERSTEP")
    nzm = N.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
    N.t.links.new(nz.outputs["Fac"], nzm.inputs["Value"])
    nzm.inputs["From Min"].default_value, nzm.inputs["From Max"].default_value = 0.35, 0.7
    nzm.inputs["To Min"].default_value, nzm.inputs["To Max"].default_value = 0.35, 1.0
    finish_emission(N, N.math("MULTIPLY", falloff, nzm), 1.0)
    for i in range(16):
        coll = frame_collection(sc, "dust", i + 1)
        n = [20, 34, 52, 70, 28, 44, 62, 84, 16, 38, 56, 24, 42, 60, 76, 34][i]
        spread = [0.30, 0.36, 0.42, 0.5, 0.3, 0.4, 0.48, 0.56, 0.22, 0.34, 0.45, 0.28, 0.38, 0.5, 0.58, 0.44][i]
        sx, sy = (spread, spread * 0.62) if i % 3 == 1 else ((spread * 1.35, spread * 0.45) if i % 3 == 2 else (spread, spread))
        tilt = rnd.uniform(0, math.pi)
        g = Geo()
        for _ in range(n):
            x, y = rnd.gauss(0, sx * 0.55), rnd.gauss(0, sy * 0.55)
            x, y = rot_pt((x, y), tilt)
            if math.hypot(x, y) > 0.72:
                continue
            rr = rnd.choice((0.016, 0.02, 0.026, 0.034, 0.045))
            g.ellipse((x, y), rr * rnd.uniform(0.8, 1.4), rr * rnd.uniform(0.7, 1.1), rnd.uniform(0, 3), n=10)
        link(coll, g.obj(f"grains{i + 1}", grain))
        if i % 2 == 0 or i > 10:
            plane = Geo()
            hs = [0.55, 0.62, 0.7, 0.78][(i // 2) % 4] * (0.82 if i < 8 else 1.0)
            plane.quad((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs), [(0, 0), (1, 0), (1, 1), (0, 1)])
            ob = plane.obj(f"haze{i + 1}", haze, True)
            ob.location = (rnd.uniform(-.08, .08), rnd.uniform(-.08, .08), -0.01)
            link(coll, ob)
    glow_compositor(sc, [(2.2, 1.0), (0.8, 0.8)])
    return {"dustSand": sc}


# --------------------------------------------------------------------------- AURORA CURTAIN (16-frame loop)
def build_aurora(opts):
    sc = flipbook_scene("auroraCurtain", opts, samples=48)
    mat = bpy.data.materials.new("aurora_mat")
    N = Nodes(mat)
    # The profile reads the mesh UV (the un-waved grid position) so the hem waves with the geometry while the glow follows it:
    # a crisp bright lower hem, a long soft fade up, and a smooth fade to nothing before the cell edge.
    uvn = N.n("ShaderNodeTexCoord")
    sep = N.separate(uvn, "UV")
    vv = N.n("ShaderNodeMath", operation="ADD")
    N.t.links.new(sep.outputs[1], vv.inputs[0])
    vv.inputs[1].default_value = 0.0
    hem = N.mapr(vv, 0.0, 0.16, "SMOOTHERSTEP")                  # 0 at the lower edge, 1 just above the hem
    glowhem = N.math("ADD", N.math("MULTIPLY", N.mapr(vv, 0.3, 0.1, "SMOOTHSTEP"), 0.9), 0.35)   # brighter near the hem
    top = N.mapr(vv, 1.0, 0.25, "SMOOTHERSTEP")                  # long soft fade towards the top
    uu = N.n("ShaderNodeMath", operation="SUBTRACT")
    N.t.links.new(sep.outputs[0], uu.inputs[0])
    uu.inputs[1].default_value = 0.5
    ua = N.n("ShaderNodeMath", operation="ABSOLUTE")
    N.t.links.new(uu.outputs[0], ua.inputs[0])
    side = N.mapr(ua, 0.5, 0.2, "SMOOTHERSTEP")
    prof = N.math("MULTIPLY", N.math("MULTIPLY", hem, top), side)
    fold = N.facing(1.0)                                         # 1 where the fold faces us, 0 where it turns edge-on
    rays = N.math("POWER", N.math("SUBTRACT", 1.0, fold), 2.2)   # only folds turning edge-on light up: bright vertical rays
    bright = N.math("ADD", N.math("MULTIPLY", rays, 1.5), 0.12)  # plus a faint veil between the rays
    finish_emission(N, N.math("MULTIPLY", N.math("MULTIPLY", prof, glowhem), bright), 1.0)
    nx, nz_ = 150, 60
    for i in range(16):
        t = i / 16.0
        coll = frame_collection(sc, "aurora", i + 1)
        verts, faces, uvs = [], [], []
        for jz in range(nz_ + 1):
            vn = jz / nz_
            for jx in range(nx + 1):
                un = jx / nx
                u = -0.86 + 1.72 * un
                v = -0.62 + 1.24 * vn
                # whole hem waves with x and time, the curtain also sways sideways more towards the top
                wave = 0.15 * math.sin(2 * math.pi * (0.9 * u + t)) + 0.05 * math.sin(2 * math.pi * (2.3 * u - 2 * t))
                sway = 0.06 * math.sin(2 * math.pi * (0.8 * vn + t)) * vn
                xx = u + sway
                zz = (0.42 * math.sin(2 * math.pi * (1.45 * xx + t))
                      + 0.24 * math.sin(2 * math.pi * (2.9 * xx - 2 * t + 0.2 * vn))
                      + 0.1 * math.sin(2 * math.pi * (5.6 * xx + 3 * t + 0.4 * vn)))
                verts.append((xx, v + wave, zz))
                uvs.append((un, vn))
        for jz in range(nz_):
            for jx in range(nx):
                a = jz * (nx + 1) + jx
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
        me = bpy.data.meshes.new(f"curtain{i + 1}")
        me.from_pydata(verts, [], faces)
        layer = me.uv_layers.new(name="UVMap")
        for li, loop in enumerate(me.loops):
            layer.data[li].uv = uvs[loop.vertex_index]
        me.materials.append(mat)
        link(coll, bpy.data.objects.new(f"curtain{i + 1}", me))
    glow_compositor(sc, [(4.5, 1.0), (1.2, 0.75)])
    return {"auroraCurtain": sc}


# --------------------------------------------------------------------------- BLOOD MOON MOTES (16 soft orbs)
def build_motes(opts):
    sc = flipbook_scene("bloodMoonMotes", opts)
    rnd = random.Random(1616)
    orb = soft_orb_mat("orb_mat", 1.7)
    flat = solid_mat("ring_mat", 1.0)
    import bmesh

    def sphere(name, r, at=(0, 0), squash=1.0):
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=r)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(orb)
        ob = bpy.data.objects.new(name, me)
        ob.location = (at[0], at[1], 0)
        ob.scale = (1, squash, 1)
        return ob
    spec = [
        ("o", .16), ("o", .22), ("o", .3), ("o", .4), ("o", .52), ("o", .66),   # single orbs, growing
        ("ring", .3), ("ring", .4), ("ring", .5),                              # orb inside a bubble ring
        ("twin", .2), ("twin", .26),
        ("drop", .3), ("drop", .4),                                           # teardrop motes drifting up
        ("trio", .16), ("crescent", .34), ("halo", .45),
    ]
    for i, (kind, r) in enumerate(spec):
        coll = frame_collection(sc, "mote", i + 1)
        if kind == "o":
            link(coll, sphere(f"mote{i + 1}", r))
        elif kind == "ring":
            link(coll, sphere(f"mote{i + 1}", r * 0.55))
            g = Geo()
            pts = [(r * 1.55 * math.cos(a), r * 1.55 * math.sin(a)) for a in [2 * math.pi * k / 64 for k in range(65)]]
            g.stroke(pts, [0.035] * len(pts))
            link(coll, g.obj(f"ring{i + 1}", flat))
        elif kind == "twin":
            link(coll, sphere(f"mote{i + 1}a", r, (-0.28, 0.1)))
            link(coll, sphere(f"mote{i + 1}b", r * 0.62, (0.3, -0.16)))
        elif kind == "drop":
            link(coll, sphere(f"mote{i + 1}", r * 0.8, (0, -0.1), 1.0))
            g = Geo()
            g.stroke([(0, -0.1 + r * 0.55), (0, 0.55)], [r * 0.8, 0.0])
            link(coll, g.obj(f"tail{i + 1}", flat))
        elif kind == "trio":
            for k, (x, y, rr) in enumerate(((-0.3, -0.12, r), (0.12, 0.28, r * 0.75), (0.34, -0.2, r * 0.55))):
                link(coll, sphere(f"mote{i + 1}_{k}", rr, (x, y)))
        elif kind == "crescent":
            g = Geo()
            n = 48
            angs = [math.radians(40 + 280 * k / n) for k in range(n + 1)]
            outer = [(0.5 * math.cos(a), 0.5 * math.sin(a)) for a in angs]
            inner = [(0.3 * math.cos(a) + 0.16, 0.3 * math.sin(a)) for a in angs]
            for k in range(n):
                g.quad(outer[k], outer[k + 1], inner[k + 1], inner[k])
            link(coll, g.transformed(rot=rnd.uniform(0, 6.28)).obj(f"crescent{i + 1}", flat))
        else:   # big diffuse halo orb
            link(coll, sphere(f"mote{i + 1}", r * 1.2))
    glow_compositor(sc, [(7.0, 1.0), (2.2, 0.6)])
    return {"bloodMoonMotes": sc}


# --------------------------------------------------------------------------- BLOOD MOON DISC 512 (lit craters, luminance -> alpha)
def build_moon(opts):
    sc = new_scene("bloodMoonDisc", 512, 512, 2.0, samples=opts["samples"] or 96)
    mat = bpy.data.materials.new("moon_mat")
    N = Nodes(mat)
    tc = N.n("ShaderNodeTexCoord")
    vor = N.n("ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="F1")
    vor.inputs["Scale"].default_value = 4.2
    N.link(tc, vor, "Object", "Vector")
    vor2 = N.n("ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="F1")
    vor2.inputs["Scale"].default_value = 9.5
    N.link(tc, vor2, "Object", "Vector")
    nz = N.n("ShaderNodeTexNoise", noise_dimensions="3D")
    nz.inputs["Scale"].default_value = 2.2
    nz.inputs["Detail"].default_value = 5.0
    N.link(tc, nz, "Object", "Vector")

    def crater(vnode, rad):
        m = N.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
        N.t.links.new(vnode.outputs["Distance"], m.inputs["Value"])
        m.inputs["From Min"].default_value, m.inputs["From Max"].default_value = 0.0, rad
        m.inputs["To Min"].default_value, m.inputs["To Max"].default_value = 1.0, 0.0
        return m
    big = crater(vor, 0.3)
    small = crater(vor2, 0.2)
    maria = N.mapr(nz, 0.35, 0.65, "SMOOTHSTEP", 0.0, 1.0)
    shade = N.math("SUBTRACT", 0.95, N.math("ADD", N.math("ADD", N.math("MULTIPLY", big, 0.42), N.math("MULTIPLY", small, 0.24)), N.math("MULTIPLY", maria, 0.3)))
    limb = N.math("ADD", 0.62, N.math("MULTIPLY", N.facing(0.6), 0.38))
    lum = N.math("MULTIPLY", shade, limb)
    emis = N.n("ShaderNodeEmission")
    N.t.links.new(lum.outputs[0], emis.inputs["Strength"])
    emis.inputs["Color"].default_value = (1, 1, 1, 1)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(emis, out, 0, 0)
    import bmesh
    me = bpy.data.meshes.new("moon")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=64, radius=0.78)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    link(sc, bpy.data.objects.new("moon", me))
    # compositor: luminance -> alpha, RGB white; then a soft halo around the limb
    ng = bpy.data.node_groups.new("moon_comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = sc
    bw = ng.nodes.new("CompositorNodeRGBToBW")
    ng.links.new(rl.outputs["Image"], bw.inputs[0])
    mul = ng.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    ng.links.new(bw.outputs["Val"], mul.inputs[0])
    ng.links.new(rl.outputs["Alpha"], mul.inputs[1])
    white = ng.nodes.new("CompositorNodeRGB")
    white.outputs[0].default_value = (1, 1, 1, 1)
    sa = ng.nodes.new("CompositorNodeSetAlpha")
    sa.inputs["Type"].default_value = "Replace Alpha"
    ng.links.new(white.outputs[0], sa.inputs["Image"])
    ng.links.new(mul.outputs[0], sa.inputs["Alpha"])
    halo = ng.nodes.new("CompositorNodeBlur")
    halo.inputs["Size"].default_value = (34, 34, 0.0) if len(halo.inputs["Size"].default_value) == 3 else (34, 34)
    halo.inputs["Extend Bounds"].default_value = False
    ng.links.new(sa.outputs[0], halo.inputs["Image"])
    soft = ng.nodes.new("CompositorNodeBlur")
    soft.inputs["Size"].default_value = (2.2, 2.2, 0.0) if len(soft.inputs["Size"].default_value) == 3 else (2.2, 2.2)
    soft.inputs["Extend Bounds"].default_value = False
    ng.links.new(sa.outputs[0], soft.inputs["Image"])
    over = ng.nodes.new("CompositorNodeAlphaOver")
    over.inputs["Factor"].default_value = 1.0
    ng.links.new(halo.outputs[0], over.inputs["Background"])
    ng.links.new(soft.outputs[0], over.inputs["Foreground"])
    gout = ng.nodes.new("NodeGroupOutput")
    ng.links.new(over.outputs[0], gout.inputs[0])
    return {"bloodMoonDisc": sc}


BUILDERS = [build_rain, build_bolt, build_snow, build_ash, build_ember, build_dust, build_aurora, build_motes, build_moon]
FLIPBOOKS = {"snowFlakeSheet", "ashFlake", "emberSpark", "dustSand", "auroraCurtain", "bloodMoonMotes"}


def main():
    opts = parse_args()
    scenes = {}
    for b in BUILDERS:
        key = b.__name__.replace("build_", "")
        scenes.update(b(opts))
    if opts["blend"]:
        pass
    only = opts["only"]
    for name, sc in scenes.items():
        if only and name != only:
            continue
        if name in FLIPBOOKS:
            d = opts["frames"] / name
            d.mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str(d.resolve()) + "/f_"
            bpy.ops.render.render(animation=True, scene=name)
        else:
            opts["out"].mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str((opts["out"] / f"{name}.png").resolve())
            bpy.ops.render.render(write_still=True, scene=name)
        print("rendered", name)
    if opts["blend"]:
        opts["blend"].parent.mkdir(parents=True, exist_ok=True)
        old = bpy.data.scenes.get("Scene")
        if old is not None and len(bpy.data.scenes) > 1:
            bpy.data.scenes.remove(old)
        bpy.ops.wm.save_as_mainfile(filepath=str(opts["blend"].resolve()), compress=True)
        print("saved", opts["blend"])


main()
