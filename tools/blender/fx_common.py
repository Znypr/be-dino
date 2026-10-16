"""Shared Blender helpers for the Be Dino! FX flipbook and motif renders (BD-187, BD-189).

Imported by tools/blender/build_fx_smoke.py and tools/blender/build_fx_motifs.py (run inside headless Blender).
Nothing here draws pixels: it builds Blender scenes (camera, world, materials, compositor) and parses arguments.
"""
import sys
from pathlib import Path

import bpy


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"frames": Path("build/fx-frames"), "blend": None, "only": None, "samples": None, "step": 1}
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
    r.resolution_x = r.resolution_y = size
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
