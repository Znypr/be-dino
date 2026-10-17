"""Shared Blender helpers for the Be Dino! FX flipbook and motif renders (BD-187, BD-189).

Imported by tools/blender/build_fx_smoke.py and tools/blender/build_fx_motifs.py (run inside headless Blender).
Nothing here draws pixels: it builds Blender scenes (camera, world, materials, compositor) and parses arguments.
"""
import sys
from pathlib import Path

import bpy


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"frames": Path("build/fx-frames"), "blend": None, "only": None, "samples": None, "step": 1, "out": None, "meshes": None, "shots": None}
    i = 0
    while i < len(argv):
        key = argv[i].lstrip("-")
        if key in opts and i + 1 < len(argv):
            opts[key] = argv[i + 1] if key in ("only",) else (int(argv[i + 1]) if key in ("samples", "step") else Path(argv[i + 1]))
            i += 2
        else:
            i += 1
    return opts


def new_scene(name, size, frames=16, samples=256, ortho=2.0, bounces_volume=0):
    sc = bpy.data.scenes.new(name)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = size if isinstance(size, tuple) else (size, size)   # a size, or (width, height)
    r.resolution_percentage = 100
    r.film_transparent = True
    r.filter_size = 1.5
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
    c.volume_bounces = bounces_volume
    c.film_exposure = 1.0
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = "sRGB"
    sc.sequencer_colorspace_settings.name = "sRGB"
    sc.frame_start, sc.frame_end = 1, frames
    w = bpy.data.worlds.new(name + "_world")
    w.use_nodes = True
    sc.world = w
    cam = bpy.data.cameras.new(name + "_cam")
    cam.type = "ORTHO"
    cam.ortho_scale = ortho
    cam.clip_start, cam.clip_end = 0.1, 40.0
    cobj = bpy.data.objects.new(name + "_cam", cam)
    cobj.location = (0, 0, 8)
    sc.collection.objects.link(cobj)
    sc.camera = cobj
    return sc


def world_light(sc, strength, color=(1, 1, 1, 1)):
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = strength
    bg.inputs["Color"].default_value = color


def link(sc, obj):
    sc.collection.objects.link(obj)
    return obj


def area_light(sc, name, loc, energy, size, color=(1, 1, 1), target=(0.0, 0.0, 0.0)):
    """Area light at `loc` aimed at `target` (so the key light really comes from a side, not from the camera)."""
    import mathutils
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size, ld.color = energy, size, color
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    direction = mathutils.Vector(target) - mathutils.Vector(loc)
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return link(sc, ob)


class Nodes:
    """Tiny helper to keep shader node graphs readable."""

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

    def length(self, vec_node, socket=0):
        """Vector Math LENGTH of a vector output; the scalar result lives on output 1."""
        ln = self.n("ShaderNodeVectorMath", operation="LENGTH")
        self.t.links.new(vec_node.outputs[socket], ln.inputs[0])
        return ln

    def mapr(self, val, lo, hi, kind="SMOOTHERSTEP", out_lo=0.0, out_hi=1.0):
        m = self.n("ShaderNodeMapRange", interpolation_type=kind, clamp=True)
        self.t.links.new(val.outputs[1 if getattr(val, "operation", "") == "LENGTH" else 0], m.inputs["Value"])
        m.inputs["From Min"].default_value = lo
        m.inputs["From Max"].default_value = hi
        m.inputs["To Min"].default_value = out_lo
        m.inputs["To Max"].default_value = out_hi
        return m


def key_value(socket, frame, value):
    socket.default_value = value
    socket.keyframe_insert("default_value", frame=frame)


def key_hide(obj, frame, hidden):
    obj.hide_render = hidden
    obj.keyframe_insert("hide_render", frame=frame)


def all_fcurves(idb):
    """Every F-curve of a datablock's action (Blender 5 layered actions or the older flat list)."""
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


def set_interpolation(idb, kind):
    for fc in all_fcurves(idb):
        for kp in fc.keyframe_points:
            kp.interpolation = kind


def render_frames(sc, out_dir, step=1):
    """Render the scene's animation into out_dir/f_0001.png ... (step > 1 = quick preview of every Nth frame)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sc.frame_step = step
    sc.render.filepath = str(out_dir / "f_")
    bpy.ops.render.render(animation=True, scene=sc.name)


# --------------------------------------------------------------------------- BD-430 / BD-431 helpers (white-on-alpha FX renders)
class Graph:
    """Socket-level shader graph builder on top of Nodes: every call returns an OUTPUT SOCKET (or takes sockets / floats), so
    a gradient reads like a formula. Used by tools/blender/build_fx_anime.py."""

    def __init__(self, mat):
        self.N = Nodes(mat)
        self.t = self.N.t

    def val(self, x):
        n = self.N.n("ShaderNodeValue")
        n.outputs[0].default_value = x
        return n.outputs[0]

    def op(self, name, a, b=None, clamp=False):
        m = self.N.n("ShaderNodeMath", operation=name)
        m.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.t.links.new(v, m.inputs[i])
        return m.outputs[0]

    def ramp(self, sock, lo, hi, kind="SMOOTHERSTEP", out_lo=0.0, out_hi=1.0):
        m = self.N.n("ShaderNodeMapRange", interpolation_type=kind, clamp=True)
        self.t.links.new(sock, m.inputs["Value"])
        m.inputs["From Min"].default_value = lo
        m.inputs["From Max"].default_value = hi
        m.inputs["To Min"].default_value = out_lo
        m.inputs["To Max"].default_value = out_hi
        return m.outputs[0]

    def uv(self):
        tc = self.N.n("ShaderNodeTexCoord")
        sep = self.N.n("ShaderNodeSeparateXYZ")
        self.t.links.new(tc.outputs["UV"], sep.inputs[0])
        return sep.outputs[0], sep.outputs[1]

    def uv_radius(self):
        """Distance from the UV centre, 0 in the middle and 1 at the edge of a plane that spans the whole UV square."""
        tc = self.N.n("ShaderNodeTexCoord")
        off = self.N.n("ShaderNodeVectorMath", operation="SUBTRACT")
        off.inputs[1].default_value = (0.5, 0.5, 0.0)
        self.t.links.new(tc.outputs["UV"], off.inputs[0])
        ln = self.N.n("ShaderNodeVectorMath", operation="LENGTH")
        self.t.links.new(off.outputs[0], ln.inputs[0])
        return self.op("MULTIPLY", ln.outputs[1], 2.0)

    def facing(self, power=1.0):
        """|N . view|: 1 where the surface faces the camera, 0 at the silhouette (soft rounded edges on real 3D forms)."""
        g = self.N.n("ShaderNodeNewGeometry")
        d = self.N.n("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        self.t.links.new(g.outputs["Normal"], d.inputs[0])
        self.t.links.new(g.outputs["Incoming"], d.inputs[1])
        a = self.op("ABSOLUTE", d.outputs["Value"])
        return self.op("POWER", a, power) if power != 1.0 else a

    def emit(self, alpha, strength=1.0):
        """Output = white emission with the given alpha (a socket or a float, clamped to 0..1)."""
        a = alpha if not isinstance(alpha, (int, float)) else self.val(alpha)
        c = self.op("MAXIMUM", self.op("MINIMUM", a, 1.0), 0.0)
        emis = self.N.n("ShaderNodeEmission")
        emis.inputs["Color"].default_value = (1, 1, 1, 1)
        emis.inputs["Strength"].default_value = strength
        clear = self.N.n("ShaderNodeBsdfTransparent")
        mix = self.N.n("ShaderNodeMixShader")
        self.t.links.new(c, mix.inputs["Fac"])
        self.t.links.new(clear.outputs[0], mix.inputs[1])
        self.t.links.new(emis.outputs[0], mix.inputs[2])
        out = self.N.n("ShaderNodeOutputMaterial")
        self.t.links.new(mix.outputs[0], out.inputs[0])


def blur_compositor(sc, layers):
    """Render Layers -> Gaussian blurs (px radius each) stacked with Alpha Over -> output. layers = [(blur_px, factor), ...],
    widest first: the widest is the background and each next layer is laid over it with its factor (0 px = unblurred).
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
    # force RGB to pure white where alpha > 0 (a blurred 1/255 alpha edge would otherwise round to a grey fringe in 8-bit PNG)
    sep = ng.nodes.new("CompositorNodeSeparateColor")
    sep.location = (300, 200)
    ng.links.new(acc.outputs[0], sep.inputs[0])
    white = ng.nodes.new("CompositorNodeRGB")
    white.outputs[0].default_value = (1, 1, 1, 1)
    white.location = (300, -100)
    sa = ng.nodes.new("CompositorNodeSetAlpha")
    sa.inputs["Type"].default_value = "Replace Alpha"
    sa.location = (450, 0)
    ng.links.new(white.outputs[0], sa.inputs["Image"])
    ng.links.new(sep.outputs["Alpha"], sa.inputs["Alpha"])
    out = ng.nodes.new("NodeGroupOutput")
    out.location = (600, 0)
    ng.links.new(sa.outputs[0], out.inputs[0])


def hide_except(obj, frame, frames):
    """Show `obj` in render only on `frame` (constant keys), so one scene holds a whole flipbook."""
    for f, hidden in ((1, frame != 1), (frame, False), (frame + 1, True)):
        if f < 1 or f > frames + 1:
            continue
        obj.hide_render = hidden
        obj.keyframe_insert("hide_render", frame=f)
    for fc in all_fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"
