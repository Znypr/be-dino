"""Be Dino! FX mutation motif sheets (BD-189). Real Blender renders, headless.

Regenerate everything (renders the frames, then Pillow only pastes the finished frames into 4 x 4 grids):

    python tools/render_fx_sheets.py            # runs Blender for smoke + motifs, then tools/assemble_fx_sheets.py

or just this part by hand:

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup \
        --python tools/blender/build_fx_motifs.py -- --frames build/fx-frames --blend tools/blender/fx_motifs_v1.blend

Seven Blender scenes, one per mutation (docs/92). Each is a 16-frame animation, 128 px per frame (4 x 4 = 512 px sheet).
The motif shapes are real modelled or particle objects (script-placed primitives are fine for particles: they are not
world models): a lathe-turned teardrop and spheres with a bubble shader (droplets), beveled curves (soft zigzag sparks,
snow crystals), noise-displaced pebbles plus a small volume dust puff (pebbles), emissive spheres and a curled flame
curve (embers), flowing ribbon meshes (aurora), soft spheres plus a Boolean crescent (crimson motes). Frames come from
keyframed transforms or keyed visibility of per-frame shapes, never from drawing pixels. Glow comes from the Blender
compositor (a wide Gaussian halo under a tight one, same recipe as BD-186). Everything is white on alpha so MutationLook
tints it at runtime, except the aurora ribbons which are coloured (green, blue, violet, magenta).
"""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
import mathutils
import mathutils.noise

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fx_common import (Nodes, all_fcurves, area_light, key_value, link, new_scene, parse_args, render_frames,  # noqa: E402
                       set_interpolation, world_light)

CELL = 128
FRAMES = 16


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def envelope(u, up=0.30, down=0.70, floor=0.0):
    """0 -> 1 -> 0 over the animation: the sprite grows, rests and shrinks; `floor` keeps frame 1 and 16 from being empty."""
    e = ease(u / up) * (1.0 - ease((u - down) / (1.0 - down)))
    return floor + (1.0 - floor) * e


def U(f):
    return (f - 1) / (FRAMES - 1)


# ------------------------------------------------------------------------------------------------ materials
def emission_alpha(name, alpha=1.0):
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


def alpha_material(name, build, color=(1, 1, 1, 1), emit_color=None):
    """Emission material whose alpha comes from build(N) -> node (output 0 = alpha 0..1)."""
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    alpha = build(N)
    clamp = N.math("MINIMUM", N.math("MAXIMUM", alpha, 0.0), 1.0)
    emis = N.n("ShaderNodeEmission")
    emis.inputs["Color"].default_value = color
    if emit_color is not None:
        N.link(emit_color, emis, 0, "Color")
    clear = N.n("ShaderNodeBsdfTransparent")
    mix = N.n("ShaderNodeMixShader")
    N.link(clamp, mix, 0, "Fac")
    N.link(clear, mix, 0, 1)
    N.link(emis, mix, 0, 2)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(mix, out, 0, 0)
    return mat


def facing_scalar(N):
    """Scalar |N . I| node (the DOT_PRODUCT result is output 1)."""
    geo = N.n("ShaderNodeNewGeometry")
    dot = N.n("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    N.link(geo, dot, "Normal", 0)
    N.link(geo, dot, "Incoming", 1)
    ab = N.n("ShaderNodeMath", operation="ABSOLUTE")
    N.t.links.new(dot.outputs[1], ab.inputs[0])
    return ab, geo


def normal_dot(N, geo, direction):
    d = math.sqrt(sum(c * c for c in direction))
    dot = N.n("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    dot.inputs[1].default_value = tuple(c / d for c in direction)
    N.link(geo, dot, "Normal", 0)
    sc = N.n("ShaderNodeMath", operation="MULTIPLY")
    N.t.links.new(dot.outputs[1], sc.inputs[0])
    sc.inputs[1].default_value = 1.0
    return sc


def bubble_material(name):
    """Dewdrop bubble: faint body, brighter rim, a specular glint top-left and a faint bounce light bottom-right.
    White emission with that alpha: neutral, so the tint is applied at runtime."""
    def build(N):
        nv, geo = facing_scalar(N)
        body = N.n("ShaderNodeValue")
        body.outputs[0].default_value = 0.26
        rim = N.math("MULTIPLY", N.mapr(nv, 0.62, 0.05), 0.62)
        glint = N.math("MULTIPLY", N.mapr(normal_dot(N, geo, (-0.5, 0.6, 0.62)), 0.90, 0.975), 0.95)
        bounce = N.math("MULTIPLY", N.mapr(normal_dot(N, geo, (0.55, -0.6, 0.55)), 0.80, 0.97), 0.30)
        acc = N.math("ADD", N.math("ADD", body, rim), N.math("ADD", glint, bounce))
        return acc
    return alpha_material(name, build)


def soft_ball_material(name, power=1.1, gain=1.0):
    """Soft glowing ball: alpha fades from the centre to the rim (a mote), never a hard disc."""
    def build(N):
        nv, _ = facing_scalar(N)
        return N.math("MULTIPLY", N.math("POWER", nv, power), gain)
    return alpha_material(name, build)


def shaded_material(name, albedo=0.96):
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    d = N.n("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (albedo, albedo, albedo, 1)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(d, out, 0, 0)
    return mat


# ------------------------------------------------------------------------------------------------ compositor glow
def glow_compositor(sc, halo_px, core_px, core_mix):
    """Render Layers -> wide Gaussian halo under a tighter Gaussian core (Alpha Over) -> output. Runs on the premultiplied
    render, so RGB stays the emitted colour wherever alpha > 0 (no dark fringes)."""
    ng = bpy.data.node_groups.new(sc.name + "_comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = sc
    rl.location = (-600, 0)

    def blur(px, y):
        b = ng.nodes.new("CompositorNodeBlur")
        b.location = (-300, y)
        size = b.inputs["Size"]
        size.default_value = (px, px, 0.0) if len(size.default_value) == 3 else (px, px)
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


def soft_compositor(sc, px):
    """One small Gaussian to soften hard silhouettes (bubbly, not crisp)."""
    ng = bpy.data.node_groups.new(sc.name + "_comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = sc
    b = ng.nodes.new("CompositorNodeBlur")
    size = b.inputs["Size"]
    size.default_value = (px, px, 0.0) if len(size.default_value) == 3 else (px, px)
    b.inputs["Extend Bounds"].default_value = False
    ng.links.new(rl.outputs["Image"], b.inputs["Image"])
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(b.outputs[0], out.inputs[0])


# ------------------------------------------------------------------------------------------------ geometry helpers
def mesh_obj(sc, name, me, mat, smooth=True):
    me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return link(sc, bpy.data.objects.new(name, me))


def uv_sphere(name, r=1.0, seg=32, rings=16):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bm.to_mesh(me)
    bm.free()
    return me


def teardrop(name, a=0.5, b=0.8, m=1.0, seg=40, ring=48):
    """Lathe-turned teardrop, tip up: profile x = a sin(t) sin(t/2)^m, y = b cos(t), spun around the Y axis."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = []
    for i in range(seg + 1):
        t = math.pi * i / seg
        x = a * math.sin(t) * math.sin(t / 2) ** m
        y = b * math.cos(t)
        verts.append(bm.verts.new((x, y, 0.0)))
    for i in range(seg):
        bm.edges.new((verts[i], verts[i + 1]))
    bmesh.ops.spin(bm, geom=list(bm.verts) + list(bm.edges), cent=(0, 0, 0), axis=(0, 1, 0), angle=math.tau, steps=ring,
                   use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    return me


def pebble_mesh(name, rng, r=1.0, squash=(1.0, 0.8, 0.7)):
    """Rounded pebble: icosphere, noise-displaced a little, squashed. Smooth shaded."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    seed = rng.uniform(0, 100)
    for v in bm.verts:
        n = mathutils.noise.noise(v.co * 1.7 + mathutils.Vector((seed, seed, seed)))
        v.co *= 1.0 + 0.16 * n
        v.co.x *= squash[0]
        v.co.y *= squash[1]
        v.co.z *= squash[2]
    bm.to_mesh(me)
    bm.free()
    return me


def curve_obj(sc, name, splines, mat, bevel, kind="POLY", resolution=4, cyclic=False, fill=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = resolution
    cu.use_fill_caps = True
    cu.resolution_u = 16
    for pts in splines:
        sp = cu.splines.new(kind)
        sp.use_cyclic_u = cyclic
        if kind == "POLY":
            sp.points.add(len(pts) - 1)
            for p, co in zip(sp.points, pts):
                p.co = (co[0], co[1], 0.0, 1.0)
        else:
            sp.bezier_points.add(len(pts) - 1)
            for bp, co in zip(sp.bezier_points, pts):
                bp.co = (co[0], co[1], 0.0)
                bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.materials.append(mat)
    return link(sc, bpy.data.objects.new(name, cu))


def key_xform(ob, f, loc=None, rot=None, scale=None):
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if rot is not None:
        ob.rotation_euler = rot
        ob.keyframe_insert("rotation_euler", frame=f)
    if scale is not None:
        ob.scale = scale if hasattr(scale, "__len__") else (scale, scale, scale)
        ob.keyframe_insert("scale", frame=f)


def show_only(variants, f):
    """variants: list of lists of objects; keyed so variant (f-1) is the one rendered at frame f."""
    for k, objs in enumerate(variants):
        for ob in objs:
            ob.hide_render = (k != f - 1)
            ob.keyframe_insert("hide_render", frame=f)


def finish_anim(objs):
    for ob in objs:
        set_interpolation(ob, "LINEAR")
        ad = ob.animation_data
        if ad and ad.action:
            for fc in all_fcurves(ob):
                if fc.data_path == "hide_render":
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"


# ------------------------------------------------------------------------------------------------ the seven scenes
def scene_droplets():
    sc = new_scene("motifDroplets", CELL, FRAMES, samples=256)
    world_light(sc, 0.0)
    mat = bubble_material("dewdrop_bubble")
    main = mesh_obj(sc, "drop_main", teardrop("drop_main", 0.50, 0.80), mat)
    beads = [mesh_obj(sc, f"bead_{i}", uv_sphere(f"bead_{i}", 0.5), mat) for i in range(3)]
    spec = [  # centre x, y, size, delay, drift
        (0.52, 0.30, 0.20, 0.10, 0.10),
        (-0.50, -0.30, 0.16, 0.22, 0.08),
        (0.40, -0.52, 0.10, 0.34, 0.06),
    ]
    for f in range(1, FRAMES + 1):
        u = U(f)
        e = envelope(u, 0.30, 0.72, 0.10)
        wob = math.sin(math.tau * u * 2.0)
        key_xform(main, f, loc=(0.0, -0.02 + 0.05 * math.sin(math.tau * u), 0.0), rot=(0, 0, 0.10 * math.sin(math.tau * u)),
                  scale=(0.86 * e * (1 + 0.05 * wob), 0.86 * e * (1 - 0.05 * wob), 0.5 * e))
        for ob, (x, y, s, delay, drift) in zip(beads, spec):
            eb = envelope(max(0.0, u - delay) / (1 - delay), 0.30, 0.65, 0.0)
            key_xform(ob, f, loc=(x, y + drift * u, 0), scale=(s * eb, s * eb, s * eb * 0.7))
    finish_anim([main] + beads)
    soft_compositor(sc, 0.6)
    return sc


def scene_sparks():
    sc = new_scene("motifSoftSparks", CELL, FRAMES, samples=256)
    world_light(sc, 0.0)
    mat = emission_alpha("spark_emit", 0.92)
    puff_mat = soft_ball_material("spark_puff", 0.9, 1.0)
    rng = random.Random(7)
    variants = []
    bolts = []
    for k in range(FRAMES):
        # soft zigzag: 6 control points, alternating sides, auto-smoothed so it is a rounded zigzag, never a sharp bolt
        pts = []
        n = 6
        for i in range(n):
            y = 0.58 - 1.16 * i / (n - 1)
            x = (0.20 if i % 2 else -0.20) * rng.uniform(0.75, 1.15) + rng.uniform(-0.04, 0.04)
            pts.append((x, y))
        ob = curve_obj(sc, f"bolt_{k}", [pts], mat, 0.062, kind="BEZIER", resolution=5)
        bolts.append(ob)
        variants.append([ob])
    show_only(variants, 1)
    puffs = [mesh_obj(sc, f"puff_{i}", uv_sphere(f"puff_{i}", 0.5), puff_mat) for i in range(3)]
    spec = [(0.45, 0.35, 0.34, 0.0), (-0.46, -0.30, 0.28, 0.15), (0.40, -0.50, 0.18, 0.28)]
    for f in range(1, FRAMES + 1):
        show_only(variants, f)
        u = U(f)
        e = envelope(u, 0.25, 0.70, 0.12)
        for ob in bolts:
            key_xform(ob, f, rot=(0, 0, 0.06 * math.sin(math.tau * u)), scale=(0.9 * e, 0.9 * e, 0.9 * e))
        for ob, (x, y, s, delay) in zip(puffs, spec):
            ep = envelope(max(0.0, u - delay) / (1 - delay), 0.30, 0.66, 0.0)
            key_xform(ob, f, loc=(x, y + 0.06 * u, 0), scale=(s * ep, s * ep, s * ep))
    finish_anim(bolts + puffs)
    glow_compositor(sc, 6.0, 2.2, 0.55)
    return sc


def snow_crystal(sc, name, mat, bevel, tip_mat=None):
    """Six-point snow crystal: 6 spokes, each with two pairs of side branches, plus round tips and a small hub."""
    splines = []
    tips = []
    for k in range(6):
        a = math.tau * k / 6
        d = (math.cos(a), math.sin(a))
        nrm = (-d[1], d[0])

        def at(r, off=0.0):
            return (d[0] * r + nrm[0] * off, d[1] * r + nrm[1] * off)
        splines.append([at(0.10), at(0.66)])
        for r, ln in ((0.30, 0.20), (0.48, 0.14)):
            for sgn in (-1, 1):
                base = at(r)
                ang = a + sgn * math.radians(58)
                splines.append([base, (base[0] + math.cos(ang) * ln, base[1] + math.sin(ang) * ln)])
                tips.append((base[0] + math.cos(ang) * ln, base[1] + math.sin(ang) * ln, 0.055))
        tips.append((*at(0.66), 0.085))
    tips.append((0.0, 0.0, 0.12))
    root = curve_obj(sc, name, splines, mat, bevel, kind="POLY", resolution=4)
    for i, (x, y, r) in enumerate(tips):
        s = mesh_obj(sc, f"{name}_tip{i}", uv_sphere(f"{name}_tip{i}", r, 16, 8), tip_mat or mat)
        s.parent = root
        s.location = (x, y, 0.0)
    return root


def scene_crystals():
    sc = new_scene("motifSnowCrystals", CELL, FRAMES, samples=256)
    world_light(sc, 0.0)
    mat = emission_alpha("crystal_emit", 0.96)
    big = snow_crystal(sc, "crystal_big", mat, 0.045)
    small1 = snow_crystal(sc, "crystal_s1", mat, 0.06)
    small2 = snow_crystal(sc, "crystal_s2", mat, 0.07)
    for f in range(1, FRAMES + 1):
        u = U(f)
        e = envelope(u, 0.28, 0.72, 0.10)
        key_xform(big, f, loc=(0.0, 0.0, 0.0), rot=(0, 0, math.radians(60.0 * u)), scale=0.92 * e)   # 60 deg = one hex turn
        e1 = envelope(max(0.0, u - 0.12) / 0.88, 0.30, 0.66, 0.0)
        e2 = envelope(max(0.0, u - 0.25) / 0.75, 0.30, 0.62, 0.0)
        key_xform(small1, f, loc=(0.60, 0.50 + 0.05 * u, 0), rot=(0, 0, math.radians(-40.0 * u + 12)), scale=0.26 * e1)
        key_xform(small2, f, loc=(-0.58, -0.52 + 0.05 * u, 0), rot=(0, 0, math.radians(50.0 * u)), scale=0.20 * e2)
    finish_anim([big, small1, small2])
    glow_compositor(sc, 5.0, 1.4, 0.65)
    return sc


def scene_pebbles():
    sc = new_scene("motifPebbles", CELL, FRAMES, samples=384, bounces_volume=4)
    world_light(sc, 0.40)
    area_light(sc, "key", (-3.6, 3.4, 2.2), 420, 2.6)
    mat = shaded_material("pebble_mat")
    rng = random.Random(5)
    pebbles = []
    spec = [  # x0, apex y, size, delay, squash, tumble speed
        (-0.34, 0.34, 0.30, 0.00, (1.0, 0.82, 0.72), 3.2),
        (0.30, 0.50, 0.24, 0.10, (1.0, 0.90, 0.80), -2.6),
        (0.02, 0.14, 0.17, 0.20, (1.0, 0.75, 0.70), 4.0),
        (0.52, -0.18, 0.12, 0.30, (1.0, 0.85, 0.75), -3.4),
        (-0.56, -0.20, 0.11, 0.34, (1.0, 0.80, 0.70), 3.0),
    ]
    for i, (x0, apex, size, delay, sq, tum) in enumerate(spec):
        ob = mesh_obj(sc, f"pebble_{i}", pebble_mesh(f"pebble_{i}", rng, 1.0, sq), mat)
        pebbles.append(ob)
    # dust puff: a small sphere used as a volume domain (soft noisy density)
    dust_mat = bpy.data.materials.new("dust_vol")
    N = Nodes(dust_mat)
    tc = N.n("ShaderNodeTexCoord")
    nz = N.n("ShaderNodeTexNoise", noise_dimensions="4D", noise_type="FBM")
    nz.inputs["Scale"].default_value = 3.2
    nz.inputs["Detail"].default_value = 4.0
    N.link(tc, nz, "Object", "Vector")
    ln = N.length(tc, "Object")
    rad = N.mapr(ln, 1.0, 0.1)
    shaped = N.mapr(nz, 0.30, 0.70)
    env = N.math("MULTIPLY", N.math("MULTIPLY", rad, shaped), 1.0)
    dens = N.math("MULTIPLY", env, 5.0)
    pv = N.n("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (1, 1, 1, 1)
    N.link(dens, pv, 0, "Density")
    out = N.n("ShaderNodeOutputMaterial")
    N.link(pv, out, 0, "Volume")
    dust = link(sc, bpy.data.objects.new("dust", uv_sphere("dust", 1.0, 24, 12)))
    dust.data.materials.append(dust_mat)
    for f in range(1, FRAMES + 1):
        u = U(f)
        for ob, (x0, apex, size, delay, sq, tum) in zip(pebbles, spec):
            lu = max(0.0, min(1.0, (u - delay) / (1 - delay)))
            # thrown up from the ground at the bottom and settling back: parabola, appears and vanishes softly
            y = -0.50 + (apex + 0.50) * 4 * lu * (1 - lu)
            x = x0 * (0.55 + 0.45 * lu)
            e = ease(lu / 0.12) * (1 - ease((lu - 0.86) / 0.14))
            key_xform(ob, f, loc=(x, y, 0.0), rot=(lu * tum, lu * tum * 0.6, lu * tum * 0.8), scale=size * (0.25 + 0.75 * e) * e ** 0.2)
        de = ease(u / 0.35) * (1 - ease((u - 0.55) / 0.45))
        key_xform(dust, f, loc=(0.0, -0.46, 0.0), scale=(0.34 + 0.46 * u, 0.20 + 0.24 * u, 0.3))
        key_value(N.t.nodes[dens.name].inputs[1], f, 5.0 * de)
    finish_anim(pebbles + [dust])
    set_interpolation(dust_mat.node_tree, "LINEAR")
    soft_compositor(sc, 0.5)
    return sc


def scene_embers():
    sc = new_scene("motifEmbers", CELL, FRAMES, samples=256)
    world_light(sc, 0.0)
    glow_mat = soft_ball_material("ember_ball", 0.8, 1.15)
    flame_mat = emission_alpha("flame_emit", 0.95)
    rng = random.Random(3)
    embers = [mesh_obj(sc, f"ember_{i}", uv_sphere(f"ember_{i}", 0.5), glow_mat) for i in range(7)]
    spec = [  # x, y0, rise, size, phase, sway
        (-0.46, -0.50, 0.85, 0.24, 0.00, 0.10),
        (0.42, -0.60, 1.00, 0.19, 0.22, 0.12),
        (0.10, -0.30, 0.75, 0.15, 0.40, 0.08),
        (-0.20, -0.65, 0.95, 0.13, 0.58, 0.14),
        (0.60, -0.35, 0.70, 0.12, 0.10, 0.10),
        (-0.62, -0.10, 0.60, 0.11, 0.72, 0.09),
        (0.24, -0.70, 0.90, 0.10, 0.85, 0.11),
    ]
    # flame wisp: two nested closed, curl-tipped teardrop curves (a soft outer flame and a brighter inner one), flickering
    # slightly from frame to frame
    flame_outer = emission_alpha("flame_outer", 0.42)
    flame_inner = emission_alpha("flame_inner", 0.95)

    def flame_curve(name, mat, lean, k_scale):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "2D"
        cu.fill_mode = "BOTH"
        cu.resolution_u = 32
        sp = cu.splines.new("BEZIER")
        sp.use_cyclic_u = True
        sp.bezier_points.add(3)
        r, cy = 0.30 * k_scale, -0.34 + 0.06 * (1 - k_scale)
        top = 0.66 * (0.62 + 0.38 * k_scale)
        pts = [
            ((0.12 * k_scale + lean * 2.4, top), (0.06 * k_scale + lean * 2, top - 0.30), (0.18 * k_scale + lean * 2, top - 0.26)),
            ((r, cy + 0.02), (r, cy + 0.26), (r, cy - r * 0.55)),
            ((0.0, cy - r), (r * 0.55, cy - r), (-r * 0.55, cy - r)),
            ((-r, cy + 0.02), (-r, cy - r * 0.55), (-r * 0.9, cy + 0.30)),
        ]
        for bp, (co, hl, hr) in zip(sp.bezier_points, pts):
            bp.handle_left_type = bp.handle_right_type = "FREE"
            bp.co = (co[0], co[1], 0)
            bp.handle_left = (hl[0], hl[1], 0)
            bp.handle_right = (hr[0], hr[1], 0)
        cu.materials.append(mat)
        return link(sc, bpy.data.objects.new(name, cu))

    variants = []
    flames = []
    for k in range(FRAMES):
        lean = 0.10 * math.sin(math.tau * k / FRAMES) + rng.uniform(-0.02, 0.02)
        outer = flame_curve(f"flame_outer_{k}", flame_outer, lean, 1.0)
        inner = flame_curve(f"flame_inner_{k}", flame_inner, lean * 0.8, 0.40)
        flames += [outer, inner]
        variants.append([outer, inner])
    for f in range(1, FRAMES + 1):
        show_only(variants, f)
        u = U(f)
        for ob, (x, y0, rise, size, ph, sway) in zip(embers, spec):
            lu = (u + ph) % 1.0                         # staggered: each ember rises and fades, then restarts
            e = ease(lu / 0.20) * (1 - ease((lu - 0.55) / 0.45))
            key_xform(ob, f, loc=(x + sway * math.sin(math.tau * (lu * 1.3 + ph)), y0 + rise * lu * 0.75, 0),
                      scale=size * (0.3 + 0.7 * e) * e ** 0.3)
        fe = envelope(u, 0.28, 0.70, 0.10)
        for ob in flames:
            key_xform(ob, f, loc=(0.0, -0.08, 0.0), scale=(0.50 * fe * (1 + 0.05 * math.sin(math.tau * u * 3)),
                                                          0.60 * fe * (1 + 0.07 * math.sin(math.tau * u * 3 + 1.2)), 1.0))
    finish_anim(embers + flames)
    glow_compositor(sc, 7.0, 1.8, 0.7)
    return sc


def ribbon_mesh(name, phase, amp, freq, length, width, nu=72, nv=7, tilt=0.0, second=0.0):
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    for i in range(nu):
        t = i / (nu - 1)
        cx = (t - 0.5) * length
        cy = amp * math.sin(math.tau * (freq * t + phase)) + second * math.sin(math.tau * (2 * freq * t + 2 * phase + 0.3))
        cy += tilt * (t - 0.5)
        # tangent for a width direction normal to the path
        dt = 1e-3
        cy2 = amp * math.sin(math.tau * (freq * (t + dt) + phase)) + second * math.sin(math.tau * (2 * freq * (t + dt) + 2 * phase + 0.3)) + tilt * (t + dt - 0.5)
        dx, dy = length * dt, cy2 - cy
        nrm = math.hypot(dx, dy)
        nx, ny = -dy / nrm, dx / nrm
        w = width * math.sin(math.pi * t) ** 0.7
        for j in range(nv):
            v = j / (nv - 1) - 0.5
            verts.append((cx + nx * w * v, cy + ny * w * v, 0.0))
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j
            faces.append((a, a + nv, a + nv + 1, a + 1))
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = ((vi // nv) / (nu - 1), (vi % nv) / (nv - 1))
    for p in me.polygons:
        p.use_smooth = True
    return me


def aurora_material(name, stops):
    """Ribbon colour: a ramp along the length through `stops` (RGB), soft alpha across the width and at both ends."""
    mat = bpy.data.materials.new(name)
    N = Nodes(mat)
    uv = N.n("ShaderNodeTexCoord")
    sep = N.n("ShaderNodeSeparateXYZ")
    N.link(uv, sep, "UV", 0)
    ramp = N.n("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    cr = ramp.color_ramp
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for i, (el, c) in enumerate(zip(cr.elements, stops)):
        el.position = i / (len(stops) - 1)
        el.color = (*c, 1.0)
    N.t.links.new(sep.outputs[0], ramp.inputs["Fac"])
    # alpha across the width: 1 at the middle line, falling to 0 at the ribbon edges
    sub = N.n("ShaderNodeMath", operation="SUBTRACT")
    N.t.links.new(sep.outputs[1], sub.inputs[0])
    sub.inputs[1].default_value = 0.5
    ab = N.n("ShaderNodeMath", operation="ABSOLUTE")
    N.t.links.new(sub.outputs[0], ab.inputs[0])
    prof = N.mapr(ab, 0.5, 0.0)
    ends = N.math("MINIMUM", N.mapr(sep, 0.0, 0.18, "SMOOTHSTEP"), N.mapr(sep, 1.0, 0.82, "SMOOTHSTEP"))
    alpha = N.math("MULTIPLY", N.math("POWER", prof, 0.9), ends)
    clamp = N.math("MINIMUM", N.math("MULTIPLY", alpha, 0.92), 1.0)
    emis = N.n("ShaderNodeEmission")
    N.link(ramp, emis, 0, "Color")
    clear = N.n("ShaderNodeBsdfTransparent")
    mix = N.n("ShaderNodeMixShader")
    N.link(clamp, mix, 0, "Fac")
    N.link(clear, mix, 0, 1)
    N.link(emis, mix, 0, 2)
    out = N.n("ShaderNodeOutputMaterial")
    N.link(mix, out, 0, 0)
    return mat


def scene_aurora():
    sc = new_scene("motifAurora", CELL, FRAMES, samples=256)
    world_light(sc, 0.0)
    green, blue, violet, magenta = (0.28, 1.0, 0.68), (0.26, 0.58, 1.0), (0.62, 0.40, 1.0), (1.0, 0.36, 0.78)
    mats = [aurora_material("aur_a", [green, blue, violet]),
            aurora_material("aur_b", [blue, violet, magenta]),
            aurora_material("aur_c", [violet, magenta, green])]
    layout = [  # amp, freq, length, width, y offset, phase offset, second harmonic
        (0.22, 1.0, 1.70, 0.50, 0.08, 0.00, 0.05),
        (0.18, 1.0, 1.55, 0.40, -0.22, 0.31, 0.04),
        (0.13, 2.0, 1.40, 0.28, 0.46, 0.62, 0.03),
    ]
    variants = [[] for _ in range(FRAMES)]
    allobs = []
    for r, (amp, freq, length, width, yoff, ph0, second) in enumerate(layout):
        for k in range(FRAMES):
            me = ribbon_mesh(f"aur{r}_{k}", ph0 + k / FRAMES, amp, freq, length, width, second=second)
            ob = mesh_obj(sc, f"aurora{r}_{k}", me, mats[r], smooth=True)
            ob.location = (0.0, yoff, 0.0 + 0.01 * r)
            variants[k].append(ob)
            allobs.append(ob)
    for f in range(1, FRAMES + 1):
        show_only(variants, f)
    finish_anim(allobs)
    glow_compositor(sc, 4.5, 1.2, 0.6)
    return sc


def scene_crimson():
    sc = new_scene("motifCrimson", CELL, FRAMES, samples=256)
    world_light(sc, 0.0)
    mote_mat = soft_ball_material("mote_ball", 0.7, 1.1)
    moon_mat = emission_alpha("moon_emit", 0.95)
    motes = [mesh_obj(sc, f"mote_{i}", uv_sphere(f"mote_{i}", 0.5), mote_mat) for i in range(6)]
    spec = [  # x, y, size, delay, drift x, drift y
        (-0.45, -0.25, 0.30, 0.00, 0.06, 0.18),
        (0.38, 0.05, 0.22, 0.08, -0.05, 0.20),
        (0.05, 0.42, 0.17, 0.16, 0.04, 0.12),
        (-0.15, -0.55, 0.13, 0.24, 0.05, 0.22),
        (0.55, -0.40, 0.11, 0.30, -0.03, 0.15),
        (-0.55, 0.38, 0.10, 0.36, 0.03, 0.14),
    ]
    # crescent shimmer: a big disc minus an offset disc (Boolean on two real meshes), small, pulsing in the middle frames
    def disc(name, r, x):
        me = bpy.data.meshes.new(name)
        n = 96
        me.from_pydata([(x + r * math.cos(math.tau * i / n), r * math.sin(math.tau * i / n), 0.0) for i in range(n)], [], [tuple(range(n))])
        me.materials.append(moon_mat)
        return link(sc, bpy.data.objects.new(name, me))
    outer, cutter = disc("moon_outer", 0.5, 0.0), disc("moon_cutter", 0.42, 0.20)
    for ob in (outer, cutter):
        sol = ob.modifiers.new("thick", "SOLIDIFY")
        sol.thickness = 0.2
        sol.offset = 0.0
    bo = outer.modifiers.new("cut", "BOOLEAN")
    bo.operation, bo.solver, bo.object = "DIFFERENCE", "EXACT", cutter
    cutter.hide_render = cutter.hide_viewport = True
    cutter.parent = outer          # the cut follows the crescent when it scales and turns
    for f in range(1, FRAMES + 1):
        u = U(f)
        for ob, (x, y, s, delay, dx, dy) in zip(motes, spec):
            lu = max(0.0, min(1.0, (u - delay) / (1 - delay)))
            e = envelope(lu, 0.35, 0.60, 0.0)
            pulse = 1.0 + 0.10 * math.sin(math.tau * (u * 2 + x))
            key_xform(ob, f, loc=(x + dx * lu, y + dy * lu, 0), scale=s * e * pulse)
        me_ = envelope(max(0.0, min(1.0, (u - 0.18) / 0.62)), 0.35, 0.60, 0.0)
        key_xform(outer, f, loc=(0.04, 0.02, 0.0), rot=(0, 0, math.radians(28 + 22 * math.sin(math.tau * u * 0.5))), scale=0.62 * me_)
    finish_anim(motes + [outer])
    glow_compositor(sc, 6.5, 2.0, 0.6)
    return sc


SCENES = {
    "motifDroplets": scene_droplets,
    "motifSoftSparks": scene_sparks,
    "motifSnowCrystals": scene_crystals,
    "motifPebbles": scene_pebbles,
    "motifEmbers": scene_embers,
    "motifAurora": scene_aurora,
    "motifCrimson": scene_crimson,
}


def main():
    opts = parse_args()
    scenes = {}
    for name, fn in SCENES.items():
        if opts["only"] and name != opts["only"]:
            continue
        scenes[name] = fn()
    for name, sc in scenes.items():
        if opts["samples"]:
            sc.cycles.samples = opts["samples"]
        render_frames(sc, (opts["frames"] / name).resolve(), opts["step"])
        print("rendered", name)
    if opts["blend"]:
        opts["blend"].parent.mkdir(parents=True, exist_ok=True)
        old = bpy.data.scenes.get("Scene")
        if old is not None and len(bpy.data.scenes) > 1:
            bpy.data.scenes.remove(old)
        bpy.ops.wm.save_as_mainfile(filepath=str(opts["blend"].resolve()), compress=True)
        print("saved", opts["blend"])


main()
