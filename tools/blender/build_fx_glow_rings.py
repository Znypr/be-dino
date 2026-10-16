"""Be Dino! FX textures: soft glow plates (BD-186) and rings (BD-188). Real Blender renders, headless.

Regenerate (nothing is drawn pixel by pixel in Python; Python only builds the Blender scenes):

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup \
        --python tools/blender/build_fx_glow_rings.py -- --out resources/effects/fx-v2 \
        --blend tools/blender/fx_glow_rings_v3.blend

One Blender scene per texture (so the .blend opens as a small catalogue). All are 256 x 256, white on alpha, straight
alpha, rendered with Cycles on an orthographic camera and a transparent film:
  * radial shapes (glowPlate, glowPlate-round, ringSoft, ringShock, ringSeismic): an emission plane whose alpha comes
    from shader nodes (radius from UV -> smooth Map Range falloffs), so edges are analytic and band-free;
  * droplet and crescent: real modelled silhouettes (Bezier curve; two cylinders with a Boolean difference), then the
    compositor Gaussian blur gives the soft glow (wide halo under a tighter core). The blur runs on the premultiplied
    render, so there are no dark fringes: RGB stays pure white wherever alpha > 0.
Runtime tint comes from MutationLook (docs/92), so the RGB must stay white; tools/verify_fx_textures.py checks that.
"""
import math
import sys
from pathlib import Path

import bpy

SIZE = 256


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out, blend = Path("resources/effects/fx-v2"), None
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = Path(argv[i + 1]); i += 2
        elif argv[i] == "--blend":
            blend = Path(argv[i + 1]); i += 2
        else:
            i += 1
    return out, blend


# --------------------------------------------------------------------------- scene helpers
def new_scene(name):
    sc = bpy.data.scenes.new(name)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x = r.resolution_y = SIZE
    r.resolution_percentage = 100
    r.film_transparent = True
    r.filter_size = 1.5
    r.dither_intensity = 0.0   # no noise added to the 8-bit PNG: RGB stays exactly white
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    r.image_settings.compression = 15
    c = sc.cycles
    c.device = "CPU"
    c.samples = 256
    c.use_denoising = False
    c.transparent_max_bounces = 16
    c.film_exposure = 1.0
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = "sRGB"
    sc.sequencer_colorspace_settings.name = "sRGB"
    # empty black world: nothing but the emission shows
    w = bpy.data.worlds.new(name + "_world")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = 0.0
    sc.world = w
    cam = bpy.data.cameras.new(name + "_cam")
    cam.type = "ORTHO"
    cam.ortho_scale = 2.0
    cam.clip_start, cam.clip_end = 0.1, 20.0
    cobj = bpy.data.objects.new(name + "_cam", cam)
    cobj.location = (0, 0, 5)
    sc.collection.objects.link(cobj)
    sc.camera = cobj
    return sc


def link(sc, obj):
    sc.collection.objects.link(obj)
    return obj


def plane(sc, name, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, co in zip(me.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop.index].uv = co
    me.materials.append(mat)
    return link(sc, bpy.data.objects.new(name, me))


# --------------------------------------------------------------------------- shader node helpers
class Nodes:
    """Tiny helper to keep the node graphs readable."""

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
        self.t.links.new(a.outputs[sa] if isinstance(sa, int) else a.outputs[sa],
                         b.inputs[sb] if isinstance(sb, int) else b.inputs[sb])

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
        """Map Range with clamp: lo -> out_lo, hi -> out_hi; smoothstep/smootherstep makes the falloff soft."""
        m = self.n("ShaderNodeMapRange", interpolation_type=kind, clamp=True)
        self.t.links.new(val.outputs[0], m.inputs["Value"])
        m.inputs["From Min"].default_value = lo
        m.inputs["From Max"].default_value = hi
        m.inputs["To Min"].default_value = out_lo
        m.inputs["To Max"].default_value = out_hi
        return m


def radial_material(name, alpha_builder):
    """Emission plane material. alpha_builder(N, r) returns the node whose output 0 is the alpha (0..1).
    r = distance from the plate centre, 0 at the middle and 1 at the middle of the frame edge."""
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    tc = N.n("ShaderNodeTexCoord")
    sub = N.n("ShaderNodeVectorMath", operation="SUBTRACT")
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    N.link(tc, sub, "UV", 0)
    ln = N.n("ShaderNodeVectorMath", operation="LENGTH")
    N.link(sub, ln, 0, 0)
    r = N.math("MULTIPLY", 0.0, 2.0)
    N.link(ln, r, 1, 0)      # Vector Math LENGTH: the scalar result is output 1
    alpha = alpha_builder(N, r)
    clipped = N.math("MINIMUM", alpha, 1.0)
    clipped2 = N.math("MAXIMUM", clipped, 0.0)
    emis = N.n("ShaderNodeEmission")
    emis.inputs["Color"].default_value = (1, 1, 1, 1)
    emis.inputs["Strength"].default_value = 1.0
    clear = N.n("ShaderNodeBsdfTransparent")
    mix = N.n("ShaderNodeMixShader")
    N.link(clipped2, mix, 0, "Fac")
    N.link(clear, mix, 0, 1)
    N.link(emis, mix, 0, 2)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(mix, out, 0, 0)
    return mat


def add(N, *parts):
    acc = parts[0]
    for p in parts[1:]:
        acc = N.math("ADD", acc, p)
    return acc


def band(N, r, centre, half_width, kind="SMOOTHERSTEP"):
    """1 at `centre`, falling smoothly to 0 at +/- half_width (a soft ring profile)."""
    d = N.math("ABSOLUTE", N.math("SUBTRACT", r, centre))
    return N.mapr(d, half_width, 0.0, kind)


# --------------------------------------------------------------------------- radial textures
def glow_plate(N, r):
    # neutral radial glow: soft smootherstep falloff to a 0.94 radius (never touches the frame edge),
    # slightly plump (power 1.35) and a faint rim light bump at 0.72
    body = N.math("POWER", N.mapr(r, 0.94, 0.0), 1.35)
    body = N.math("MULTIPLY", body, 0.92)
    rim = N.math("MULTIPLY", band(N, r, 0.70, 0.24), 0.075)
    return add(N, body, rim)


def glow_round(N, r):
    # rounder, flatter and bubblier: soft disc with a gentle plateau, a faint inner glow and a bubble rim
    disc = N.math("MULTIPLY", N.mapr(r, 0.94, 0.50), 0.66)
    inner = N.math("MULTIPLY", N.mapr(r, 0.62, 0.0), 0.24)
    rim = N.math("MULTIPLY", band(N, r, 0.79, 0.17), 0.10)
    return add(N, disc, inner, rim)


def ring_soft(N, r):
    # soft rim ring at 0.72: wide gentle body, a faint inner gradient and a slight bevel highlight on the outer shoulder
    body = N.math("MULTIPLY", N.math("POWER", band(N, r, 0.72, 0.24), 1.2), 0.82)
    inner = N.math("MULTIPLY", N.mapr(r, 0.72, 0.08), 0.13)
    bevel = N.math("MULTIPLY", band(N, r, 0.77, 0.05), 0.20)
    return add(N, body, inner, bevel)


def ring_shock(N, r):
    # thin shock ring at 0.80: a feathered bright core line over a faint halo and a barely-there inner gradient
    core = band(N, r, 0.80, 0.04)
    halo = N.math("MULTIPLY", N.math("POWER", band(N, r, 0.80, 0.17), 2.0), 0.26)
    inner = N.math("MULTIPLY", N.mapr(r, 0.80, 0.30), 0.06)
    return add(N, core, halo, inner)


def ring_seismic(N, r):
    # thicker, rounder ring at 0.64: a plump tube profile (like a rolled rubber band) with a soft shoulder highlight
    tube = N.math("MULTIPLY", N.math("POWER", band(N, r, 0.64, 0.28), 0.62), 0.88)
    inner = N.math("MULTIPLY", N.mapr(r, 0.64, 0.10), 0.10)
    bevel = N.math("MULTIPLY", band(N, r, 0.72, 0.07), 0.14)
    return add(N, tube, inner, bevel)


RADIAL = {
    "glowPlate": glow_plate,
    "glowPlate-round": glow_round,
    "ringSoft": ring_soft,
    "ringShock": ring_shock,
    "ringSeismic": ring_seismic,
}


# --------------------------------------------------------------------------- blurred silhouettes (droplet, crescent)
def silhouette_material(name, strength):
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    emis = N.n("ShaderNodeEmission")
    emis.inputs["Color"].default_value = (1, 1, 1, 1)
    emis.inputs["Strength"].default_value = 1.0
    clear = N.n("ShaderNodeBsdfTransparent")
    mix = N.n("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = strength   # alpha of the silhouette
    N.link(clear, mix, 0, 1)
    N.link(emis, mix, 0, 2)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(mix, out, 0, 0)
    return mat


def droplet_object(sc, mat):
    """Teardrop modelled as a closed Bezier curve: pointed tip up, round belly, symmetrical."""
    cu = bpy.data.curves.new("droplet", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    sp = cu.splines.new("BEZIER")
    sp.use_cyclic_u = True
    sp.bezier_points.add(3)
    k = 0.5523
    rad, cy = 0.36, -0.12          # belly circle
    pts = [
        # (co, handle_left, handle_right)
        ((0.0, 0.64), (-0.03, 0.34), (0.03, 0.34)),                              # tip
        ((rad, cy), (rad, cy + 0.20), (rad, cy - rad * k)),                      # right
        ((0.0, cy - rad), (rad * k, cy - rad), (-rad * k, cy - rad)),            # bottom
        ((-rad, cy), (-rad, cy - rad * k), (-rad, cy + 0.20)),                   # left
    ]
    for bp, (co, hl, hr) in zip(sp.bezier_points, pts):
        bp.handle_left_type = bp.handle_right_type = "FREE"
        bp.co = (co[0], co[1], 0)
        bp.handle_left = (hl[0], hl[1], 0)
        bp.handle_right = (hr[0], hr[1], 0)
    cu.resolution_u = 48
    cu.materials.append(mat)
    ob = bpy.data.objects.new("droplet", cu)
    link(sc, ob)
    ob.scale = (1.14, 1.14, 1.14)
    ob.location = (0.0, -0.05, 0.0)
    return ob


def crescent_object(sc, mat):
    """Crescent = big disc minus an offset disc (Boolean difference on two real meshes), tilted."""
    def disc(name, r, x):
        me = bpy.data.meshes.new(name)
        n = 192
        verts = [(x + r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), 0.0) for i in range(n)]
        me.from_pydata(verts, [], [tuple(range(n))])
        me.materials.append(mat)
        return link(sc, bpy.data.objects.new(name, me))
    outer = disc("moon_outer", 0.64, 0.0)
    cutter = disc("moon_cutter", 0.52, 0.27)
    # Boolean works on solids: give both discs a little thickness
    for ob in (outer, cutter):
        sol = ob.modifiers.new("thick", "SOLIDIFY")
        sol.thickness = 0.2
        sol.offset = 0.0
    bo = outer.modifiers.new("cut", "BOOLEAN")
    bo.operation = "DIFFERENCE"
    bo.solver = "EXACT"
    bo.object = cutter
    cutter.hide_render = True
    cutter.hide_viewport = True
    outer.rotation_euler = (0, 0, math.radians(18))
    return outer


def blurred_compositor(sc, halo_px, core_px, core_mix):
    """Render Layers -> wide Gaussian halo under a tighter Gaussian core (Alpha Over) -> output."""
    ng = bpy.data.node_groups.new(sc.name + "_comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = sc
    rl.location = (-600, 0)

    def blur(px, y):
        b = ng.nodes.new("CompositorNodeBlur")
        b.location = (-300, y)
        b.inputs["Size"].default_value = (px, px, 0.0) if len(b.inputs["Size"].default_value) == 3 else (px, px)
        b.inputs["Extend Bounds"].default_value = False
        ng.links.new(rl.outputs["Image"], b.inputs["Image"])
        return b
    halo, core = blur(halo_px, 150), blur(core_px, -150)
    over = ng.nodes.new("CompositorNodeAlphaOver")
    over.location = (0, 0)
    over.inputs["Factor"].default_value = core_mix
    ng.links.new(halo.outputs[0], over.inputs["Background"])
    ng.links.new(core.outputs[0], over.inputs["Foreground"])
    out = ng.nodes.new("NodeGroupOutput")
    out.location = (300, 0)
    ng.links.new(over.outputs[0], out.inputs[0])


# --------------------------------------------------------------------------- build + render
def build_all():
    scenes = {}
    for name, fn in RADIAL.items():
        sc = new_scene(name)
        mat = radial_material(name + "_mat", fn)
        plane(sc, name + "_plane", mat)
        scenes[name] = sc

    sc = new_scene("glowPlate-droplet")
    droplet_object(sc, silhouette_material("droplet_mat", 0.85))
    blurred_compositor(sc, 52.0, 22.0, 0.5)
    scenes[sc.name] = sc

    sc = new_scene("glowPlate-crescent")
    crescent_object(sc, silhouette_material("crescent_mat", 0.85))
    blurred_compositor(sc, 48.0, 20.0, 0.5)
    scenes[sc.name] = sc
    return scenes


def main():
    out, blend = parse_args()
    out.mkdir(parents=True, exist_ok=True)
    # drop the default startup scene's content so the .blend only holds our catalogue
    scenes = build_all()
    for name, sc in scenes.items():
        sc.render.filepath = str((out / f"{name}.png").resolve())
        bpy.ops.render.render(write_still=True, scene=name)
        print("rendered", sc.render.filepath)
    if blend:
        blend.parent.mkdir(parents=True, exist_ok=True)
        old = bpy.data.scenes.get("Scene")
        if old is not None and len(bpy.data.scenes) > 1:
            bpy.data.scenes.remove(old)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()), compress=True)
        print("saved", blend)


main()
