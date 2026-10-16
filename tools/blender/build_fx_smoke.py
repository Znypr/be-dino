"""Be Dino! FX smoke puff flipbooks (BD-187). Real Blender volume renders, headless.

Regenerate everything (renders the frames, then Pillow only pastes the finished frames into 4 x 4 grids):

    python tools/render_fx_sheets.py            # runs Blender for smoke + motifs, then tools/assemble_fx_sheets.py

or just this part by hand:

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup \
        --python tools/blender/build_fx_smoke.py -- --frames build/fx-frames --blend tools/blender/fx_smoke_v1.blend

Three Blender scenes, one per sheet, 16 animated frames each, 128 px per frame (4 x 4 = 512 px sheet):
  * smokeSoft   layered soft smoke: a puff of billowing lobes that swells, curls gently and thins out;
  * smokeDense  denser, rounder, chunkier billows for ember / seismic dust, higher opacity core;
  * smokeWispy  a stretched, wispy breath that streams to the right and thins (Frost).

Every frame is a Cycles render of a real volume: a Principled Volume (white scatter) inside a cube domain whose density is
a procedural field built from shader nodes: script-placed soft lobes (they are particles of the puff, not world models,
keyframed to swell and drift) eroded by a domain-warped 4D fbm noise whose W axis animates, times a fade-in/fade-out
envelope and a frame-edge mask so the border of every cell is empty. Lit by a soft white world plus one large area light,
with volume bounces, so the lit side is white and the core carries a little soft self-shadow. No pixel is drawn by Python.
"""
import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fx_common import (Nodes, all_fcurves, area_light, key_value, link, new_scene, parse_args, render_frames, world_light)  # noqa: E402

CELL = 128
FRAMES = 16


# ---------------------------------------------------------------------------------------------------------- style table
# lobes: how many soft balls make the puff; spread: how far they drift from the centre; size: radius range at full growth
STYLES = {
    "smokeSoft": dict(
        seed=11, lobes=8, satellites=2, scale=1.3, spread=0.46, size=(0.32, 0.44), start=0.5, rise=0.08, swirl=0.55,
        lobe_core=0.45, noise_scale=3.0, detail=5.0, rough=0.55, warp=0.20, th=(0.36, 0.66), erosion=0.50,
        sigma=5.5, fade_in=(0.0, 0.22), fade_out=(0.62, 1.0), anis=0.35, stretch=(1, 1, 1), stream=0.0,
        light=0.62, key=1000, noise_w=0.10),
    "smokeDense": dict(
        seed=23, lobes=6, satellites=3, scale=1.25, spread=0.40, size=(0.40, 0.52), start=0.6, rise=0.06, swirl=0.40,
        lobe_core=0.5, noise_scale=2.2, detail=3.0, rough=0.5, warp=0.14, th=(0.20, 0.52), erosion=0.35,
        sigma=12.0, fade_in=(0.0, 0.16), fade_out=(0.68, 1.0), anis=0.25, stretch=(1, 1, 1), stream=0.0,
        light=0.26, key=760, noise_w=0.07),
    "smokeWispy": dict(
        seed=37, lobes=8, satellites=1, scale=1.2, spread=0.64, size=(0.30, 0.42), start=0.35, rise=0.18, swirl=0.30,
        lobe_core=0.15, noise_scale=2.6, detail=6.0, rough=0.62, warp=0.55, th=(0.28, 0.80), erosion=0.80,
        sigma=8.5, fade_in=(0.0, 0.20), fade_out=(0.45, 1.0), anis=0.45, stretch=(0.7, 1.3, 1), stream=0.95,
        light=0.75, key=800, noise_w=0.16),
}


def ease(u):
    return u * u * (3 - 2 * u)


def build_smoke(name, st):
    sc = new_scene(name, CELL, frames=FRAMES, samples=512, bounces_volume=6)
    world_light(sc, st["light"])
    area_light(sc, "key", (-3.5, 3.8, 3.2), st["key"], 3.2)
    area_light(sc, "rim", (3.6, -2.4, 2.4), st["key"] * 0.22, 2.5)

    mat = bpy.data.materials.new(name + "_vol")
    N = Nodes(mat)
    tc = N.n("ShaderNodeTexCoord")
    stretch = N.n("ShaderNodeVectorMath", operation="MULTIPLY")
    stretch.inputs[1].default_value = st["stretch"]
    N.link(tc, stretch, "Object", 0)

    # domain warp: p_w = p + (noise.color - 0.5) * warp   (4D noise, W is animated for the slow swirl)
    wn = N.n("ShaderNodeTexNoise", noise_dimensions="4D", noise_type="FBM")
    wn.inputs["Scale"].default_value = st["noise_scale"] * 0.7
    wn.inputs["Detail"].default_value = 2.0
    N.link(stretch, wn, 0, "Vector")
    off = N.n("ShaderNodeVectorMath", operation="SUBTRACT")
    off.inputs[1].default_value = (0.5, 0.5, 0.5)
    N.link(wn, off, "Color", 0)
    sc_off = N.n("ShaderNodeVectorMath", operation="SCALE")
    sc_off.inputs["Scale"].default_value = st["warp"]
    N.link(off, sc_off, 0, 0)
    pw = N.n("ShaderNodeVectorMath", operation="ADD")
    N.link(stretch, pw, 0, 0)
    N.link(sc_off, pw, 0, 1)

    # lobes: soft balls. centre and radius are keyframed per frame.
    rng = random.Random(st["seed"])
    lobes = []
    for i in range(st["lobes"]):
        ang = rng.uniform(0, 2 * math.pi)
        rad = st["spread"] * rng.uniform(0.35, 1.0)
        size = rng.uniform(*st["size"])
        lag = rng.uniform(0.0, 0.18)           # some lobes start swelling a little later: layered look
        lobes.append((ang, rad, size, lag, None))
        for j in range(st.get("satellites", 2)):
            # small satellite billows riding on the rim of the lobe: the cauliflower detail
            lobes.append((ang, rad, size * rng.uniform(0.38, 0.55), lag, (i, rng.uniform(0, 2 * math.pi), rng.uniform(0.72, 0.95))))
    acc = None
    c_inputs, r_inputs = [], []
    for i, (ang, rad, size, lag, sat) in enumerate(lobes):
        sub = N.n("ShaderNodeVectorMath", operation="SUBTRACT")
        N.link(pw, sub, 0, 0)
        ln = N.length(sub)
        div = N.n("ShaderNodeMath", operation="DIVIDE")
        N.t.links.new(ln.outputs[1], div.inputs[0])
        div.inputs[1].default_value = 1.0
        lobe = N.mapr(div, 1.0, st['lobe_core'])
        c_inputs.append(sub.inputs[1])
        r_inputs.append(div.inputs[1])
        acc = lobe if acc is None else N.math("ADD", acc, lobe)
    total = N.math("MINIMUM", N.math("MULTIPLY", acc, 0.85), 1.0)

    # erosion noise: billowy bites at the edge, so the puff is not a clean ball
    en = N.n("ShaderNodeTexNoise", noise_dimensions="4D", noise_type="FBM")
    en.inputs["Scale"].default_value = st["noise_scale"]
    en.inputs["Detail"].default_value = st["detail"]
    en.inputs["Roughness"].default_value = st["rough"]
    N.link(pw, en, 0, "Vector")
    shaped = N.mapr(en, st["th"][0], st["th"][1])
    k = st["erosion"]
    mixed = N.math("ADD", N.math("MULTIPLY", shaped, k), 1.0 - k)
    d = N.math("MULTIPLY", total, mixed)

    # empty cell border: radial mask in the picture plane (x, y), so no smoke reaches the cell edge
    flat = N.n("ShaderNodeVectorMath", operation="MULTIPLY")
    flat.inputs[1].default_value = (1, 1, 0)
    N.link(tc, flat, "Object", 0)
    r_xy = N.length(flat)
    edge = N.mapr(r_xy, 0.98, 0.74)
    d = N.math("MULTIPLY", d, edge)
    env_val = N.math("MULTIPLY", d, 1.0)       # input 1 = fade envelope (keyframed)
    dens = N.math("MULTIPLY", env_val, st["sigma"])
    pv = N.n("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (1, 1, 1, 1)
    pv.inputs["Anisotropy"].default_value = st["anis"]
    N.link(dens, pv, 0, "Density")
    out = N.n("ShaderNodeOutputMaterial")
    N.link(pv, out, 0, "Volume")

    # ---- animation (16 frames, u = 0..1)
    for f in range(1, FRAMES + 1):
        u = (f - 1) / (FRAMES - 1)
        centres, sizes = {}, {}
        for i, (ang, rad, size, lag, sat) in enumerate(lobes):
            lu = max(0.0, min(1.0, (u - lag) / (1.0 - lag)))
            e = ease(lu)
            base_i = sat[0] if sat else i
            bang, brad, bsize, blag, _ = lobes[base_i]
            a = bang + st["swirl"] * u * (1.0 + 0.3 * math.sin(base_i))
            r = brad * (st["start"] * 0.35 + (1 - st["start"] * 0.35) * e)
            cx, cy = r * math.cos(a), r * math.sin(a) + st["rise"] * u
            cx += st["stream"] * (u * 0.95 - 0.38) * (0.6 + 0.8 * (base_i / max(1, len(lobes) - 1)))
            grown = bsize * (st["start"] + (1 - st["start"]) * e)
            if sat:
                sa = sat[1] + st["swirl"] * u * 1.4
                cx += math.cos(sa) * grown * sat[2]
                cy += math.sin(sa) * grown * sat[2]
                grown = size * (st["start"] + (1 - st["start"]) * e)
            else:
                grown = size * (st["start"] + (1 - st["start"]) * e)
            key_value(c_inputs[i], f, (cx * st["scale"], cy * st["scale"], 0.0))
            key_value(r_inputs[i], f, grown * st["scale"])
        fi = max(0.0, min(1.0, (u - st["fade_in"][0]) / (st["fade_in"][1] - st["fade_in"][0])))
        fo = max(0.0, min(1.0, (u - st["fade_out"][0]) / (st["fade_out"][1] - st["fade_out"][0])))
        env = (0.16 + 0.84 * ease(fi)) * (1.0 - ease(fo))
        key_value(env_val.inputs[1], f, env)
        key_value(wn.inputs["W"], f, st["noise_w"] * (f - 1))
        key_value(en.inputs["W"], f, st["noise_w"] * (f - 1) * 1.3 + 4.0)
    for fc in all_fcurves(mat.node_tree):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    bpy.ops.mesh.primitive_cube_add(size=2.0)
    cube = bpy.context.active_object
    bpy.context.collection.objects.unlink(cube)
    cube.name = name + "_domain"
    cube.data.materials.append(mat)
    link(sc, cube)
    return sc


def main():
    opts = parse_args()
    scenes = {}
    for name, st in STYLES.items():
        if opts["only"] and name != opts["only"]:
            continue
        scenes[name] = build_smoke(name, st)
    for name, sc in scenes.items():
        if opts["samples"]:
            sc.cycles.samples = opts["samples"]
        d = (opts["frames"] / name).resolve()
        d.mkdir(parents=True, exist_ok=True)
        render_frames(sc, d, opts["step"])
        print("rendered", name, d)
    if opts["blend"]:
        opts["blend"].parent.mkdir(parents=True, exist_ok=True)
        old = bpy.data.scenes.get("Scene")
        if old is not None and len(bpy.data.scenes) > 1:
            bpy.data.scenes.remove(old)
        bpy.ops.wm.save_as_mainfile(filepath=str(opts["blend"].resolve()), compress=True)
        print("saved", opts["blend"])


main()
