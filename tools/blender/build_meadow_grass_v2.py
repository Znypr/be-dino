"""Be Dino! matte meadow grass terrain set (BD-461): seamless 1024 px colour, normal and roughness maps. Real Blender, headless.

Regenerate (the geometry is scattered in Blender and every pixel comes from a Cycles render; Python only builds the scenes
and, at the end, MEASURES the result, it never writes a pixel):

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup \
        --python tools/blender/build_meadow_grass_v2.py -- \
        --out resources/materials/meadow-grass-v2 \
        --evidence docs/evidence/2026-10-16-env \
        --blend tools/blender/meadow_grass_v2.blend

What it builds (1 Blender unit = 1 stud, the tile is 12 x 12 studs, rendered 1024 x 1024 px):
  * a small-blade grass bed: ~1300 jittered-Poisson clumps (blue-noise spacing, so no blotches), 5-9 short leaning blades each
    (V-folded, tapered, slightly drooping), plus ~9 percent clover leaflet triples. Blade length 0.2-0.45 stud, width 0.05+:
    short and broad on purpose, nothing is hair-like. Per-blade colour jitter is small and uncorrelated.
  * SEAMLESS by construction: clump positions are sampled on a torus (wrap-around distance) and every clump that comes within
    one stud of an edge is also instanced at the +-12 stud offsets, then an orthographic camera crops exactly one tile. The same
    lattice surrounds the tile in the render, so light, ambient occlusion and geometry all wrap. No pixel is blended or shifted.
  * three renders of the same scene with swapped shaders (Blender's own shading, no Python pixels):
      colour    Cycles, diffuse-led Principled BSDF, soft top light + uniform sky (so shading is mostly gentle occlusion), Standard view
      normal    Emission of the geometry normal. An orthographic top-down camera makes world space equal tangent space
                (x right, y up, z out of the screen, green = +Y, the OpenGL convention); xy is scaled by NORMAL_STRENGTH, so it is subtle
      roughness Emission of a per-vertex roughness (0.84-0.95), mostly matte. No metalness map (Roblox keeps its default of 0).
    Data maps use the Raw view transform so the PNG holds the value as is.
  * the .blend keeps the tile scene plus the preview scenes; --evidence also renders the 3x3 tiled preview and the
    gameplay-distance comparison (ground plane at 25 and 40 studs, left = this texture, right = a flat built-in-like reference
    colour 132,166,68 = BiomeMap.Colors.Grass, orange sphere = a 3.5 stud start-size dino stand-in, pink spheres = food).
    The preview is Cycles with sun + sky, NOT Roblox Future lighting: it judges the texture structure, the Studio A/B decides.
  * stats (low-frequency variance, seam test, mean colour) are measured on the written PNGs with numpy INSIDE Blender and saved
    to <evidence>/meadow-grass-v2-stats.json.
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

TILE = 12.0          # studs per tile (matches the BD-461 brief and the MaterialVariant StudsPerTile)
RES = 1024
SEED = 461
SAMPLES = 160
NORMAL_STRENGTH = 0.40   # scales the xy of the geometry normal before it is written (smaller = subtler)
COLOR_EXPOSURE = 0.0     # stops, tuned so the mean lands near the built-in-like reference green
REFERENCE_SRGB = (132, 166, 68)   # BiomeMap.Colors.Grass (docs/138 candidate C)


def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(rgb):
    return tuple(srgb_to_lin(v) for v in rgb)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out, evidence, blend = Path("resources/materials/meadow-grass-v2"), None, None
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = Path(argv[i + 1]); i += 2
        elif argv[i] == "--evidence":
            evidence = Path(argv[i + 1]); i += 2
        elif argv[i] == "--blend":
            blend = Path(argv[i + 1]); i += 2
        else:
            i += 1
    return out, evidence, blend


# --------------------------------------------------------------------------- scattering (blue noise on a torus)
def poisson_torus(rng, size, radius, k=30):
    """Bridson dart throwing with wrap-around distance, so the pattern is periodic over `size`."""
    cell = radius / math.sqrt(2)
    n = int(math.ceil(size / cell))
    cell = size / n
    grid = {}
    pts = []

    def gi(p):
        return (int(p[0] / cell) % n, int(p[1] / cell) % n)

    def ok(p):
        gx, gy = gi(p)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                q = grid.get(((gx + dx) % n, (gy + dy) % n))
                if q is None:
                    continue
                ddx = abs(p[0] - q[0]); ddx = min(ddx, size - ddx)
                ddy = abs(p[1] - q[1]); ddy = min(ddy, size - ddy)
                if ddx * ddx + ddy * ddy < radius * radius:
                    return False
        return True

    first = (rng.random() * size, rng.random() * size)
    pts.append(first); grid[gi(first)] = first
    active = [first]
    while active:
        idx = rng.randrange(len(active))
        base = active[idx]
        for _ in range(k):
            a = rng.random() * math.tau
            d = radius * (1 + rng.random())
            p = ((base[0] + math.cos(a) * d) % size, (base[1] + math.sin(a) * d) % size)
            if ok(p):
                pts.append(p); grid[gi(p)] = p; active.append(p)
                break
        else:
            active.pop(idx)
    return pts


def wrapped_copies(p, margin):
    """The point plus its +-TILE copies that fall within `margin` of the tile square [0, TILE]^2."""
    out = []
    for ox in (-TILE, 0.0, TILE):
        for oy in (-TILE, 0.0, TILE):
            x, y = p[0] + ox, p[1] + oy
            if -margin <= x <= TILE + margin and -margin <= y <= TILE + margin:
                out.append((x, y))
    return out


# --------------------------------------------------------------------------- geometry
class Builder:
    def __init__(self):
        self.verts, self.faces = [], []
        self.col, self.rgh = [], []   # per-vertex linear colour (r,g,b,1) and roughness

    def add_strip(self, rings, colors, roughs):
        """rings: list of (left, mid, right) Vector triples, root first. Two quads per segment (a V-fold)."""
        base = len(self.verts)
        for ring, c, r in zip(rings, colors, roughs):
            for v in ring:
                self.verts.append(tuple(v))
                self.col.append(c)
                self.rgh.append(r)
        for i in range(len(rings) - 1):
            a, b = base + i * 3, base + (i + 1) * 3
            self.faces.append((a, a + 1, b + 1, b))
            self.faces.append((a + 1, a + 2, b + 2, b + 1))

    def add_fan(self, centre, rim, c, r):
        base = len(self.verts)
        self.verts.append(tuple(centre)); self.col.append((*c[0], 1.0)); self.rgh.append(r)
        for v, cc in zip(rim, c[1:]):
            self.verts.append(tuple(v)); self.col.append((*cc, 1.0)); self.rgh.append(r)
        n = len(rim)
        for i in range(n):
            self.faces.append((base, base + 1 + i, base + 1 + (i + 1) % n))

    def to_object(self, name, collection):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.update()
        for p in mesh.polygons:
            p.use_smooth = True
        ca = mesh.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set("color", [x for c in self.col for x in c])
        rg = mesh.color_attributes.new("Rgh", 'FLOAT_COLOR', 'POINT')
        rg.data.foreach_set("color", [x for r in self.rgh for x in (r, r, r, 1.0)])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj


def mix3(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def build_blade(bld, rng, root, clump_var):
    phi = rng.random() * math.tau
    L = rng.uniform(0.15, 0.32)
    w0 = rng.uniform(0.065, 0.095)
    alpha0 = math.radians(rng.uniform(22, 62))     # lean angle above the ground: top view sees a short stroke, not a sliver
    bend = math.radians(rng.uniform(8, 30))        # droops toward horizontal along the blade
    r_hat = Vector((math.cos(phi), math.sin(phi), 0.0))
    s_hat = Vector((-math.sin(phi), math.cos(phi), 0.0))
    segs = 3
    ring_pts, cols, roughs = [], [], []
    pos = Vector((root[0] + r_hat.x * rng.uniform(0, 0.05), root[1] + r_hat.y * rng.uniform(0, 0.05), 0.0))
    # per-blade tone (small, uncorrelated): a yellow-green / blue-green mix and a value jitter
    u = rng.random()
    tip = mix3(lin((164, 188, 80)), lin((142, 180, 84)), u)
    rootc = mix3(lin((126, 154, 58)), lin((114, 150, 60)), u)
    v = max(0.88, min(1.12, rng.gauss(1.0, 0.045) * clump_var))
    for i in range(segs + 1):
        t = i / segs
        w = w0 * (1.0 - 0.80 * t ** 2.0)
        if i > 0:
            a = alpha0 - bend * ((i - 0.5) / segs)
            d = L / segs
            pos = pos + r_hat * (math.cos(a) * d) + Vector((0, 0, math.sin(a) * d))
        fold = w * 0.22
        tangent = (r_hat * math.cos(alpha0 - bend * t) + Vector((0, 0, math.sin(alpha0 - bend * t)))).normalized()
        n_hat = s_hat.cross(tangent).normalized()
        if n_hat.z < 0:
            n_hat = -n_hat
        mid = pos + n_hat * fold
        ring_pts.append((pos - s_hat * (w / 2), mid, pos + s_hat * (w / 2)))
        c = mix3(rootc, tip, min(1.0, t * 1.15))
        cols.append((c[0] * v, c[1] * v, c[2] * v, 1.0))
        roughs.append(0.94 - 0.08 * t + rng.uniform(-0.01, 0.01))
    bld.add_strip(ring_pts, cols, roughs)


def build_clover(bld, rng, centre):
    base_phi = rng.random() * math.tau
    tone = rng.random()
    cdark = mix3(lin((108, 150, 60)), lin((120, 160, 64)), tone)
    clight = mix3(lin((134, 174, 74)), lin((148, 184, 78)), tone)
    for k in range(3):
        phi = base_phi + k * math.tau / 3 + rng.uniform(-0.2, 0.2)
        dist = rng.uniform(0.07, 0.10)
        rad = rng.uniform(0.075, 0.105)
        h = rng.uniform(0.10, 0.18)
        tilt = math.radians(rng.uniform(8, 24))
        cx, cy = centre[0] + math.cos(phi) * dist, centre[1] + math.sin(phi) * dist
        out = Vector((math.cos(phi), math.sin(phi), 0.0))
        side = Vector((-math.sin(phi), math.cos(phi), 0.0))
        rim = []
        cols = [clight]
        n = 10
        for j in range(n):
            ang = j * math.tau / n
            # slightly heart-shaped / wider than long outline
            px = math.cos(ang) * rad * 0.92
            py = math.sin(ang) * rad * (1.0 + 0.08 * math.cos(ang))
            # tilt: rise with distance from the stem along `out`
            lift = px * math.sin(tilt)
            rim.append(Vector((cx, cy, h)) + out * (px * math.cos(tilt)) + side * py + Vector((0, 0, lift)))
            cols.append(cdark)
        bld.add_fan(Vector((cx, cy, h + 0.012)), rim, cols, 0.82 + rng.uniform(-0.02, 0.02))


# --------------------------------------------------------------------------- shaders
def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt


def attr_color(nt, layer):
    n = nt.nodes.new("ShaderNodeVertexColor")
    n.layer_name = layer
    return n


def mat_colour(name, vertex_layer="Col", flat=None, rough=0.92):
    m, nt = new_mat(name)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Specular IOR Level"].default_value = 0.12
    if flat is not None:
        bsdf.inputs["Base Color"].default_value = (*flat, 1.0)
    else:
        vc = attr_color(nt, vertex_layer)
        nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_emit_attr(name, layer):
    m, nt = new_mat(name)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    vc = attr_color(nt, layer)
    nt.links.new(vc.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


def mat_emit_const(name, rgb):
    m, nt = new_mat(name)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


def mat_emit_normal(name, strength):
    """Geometry normal -> (xy * strength, z) -> normalize -> *0.5+0.5 -> emission. World == tangent space for the top-down camera."""
    m, nt = new_mat(name)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'MULTIPLY'; mx.inputs[1].default_value = strength
    my = nt.nodes.new("ShaderNodeMath"); my.operation = 'MULTIPLY'; my.inputs[1].default_value = strength
    mz = nt.nodes.new("ShaderNodeMath"); mz.operation = 'MAXIMUM'; mz.inputs[1].default_value = 0.30
    nt.links.new(sep.outputs["X"], mx.inputs[0])
    nt.links.new(sep.outputs["Y"], my.inputs[0])
    nt.links.new(sep.outputs["Z"], mz.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mx.outputs[0], comb.inputs["X"]); nt.links.new(my.outputs[0], comb.inputs["Y"]); nt.links.new(mz.outputs[0], comb.inputs["Z"])
    norm = nt.nodes.new("ShaderNodeVectorMath"); norm.operation = 'NORMALIZE'
    nt.links.new(comb.outputs["Vector"], norm.inputs[0])
    enc = nt.nodes.new("ShaderNodeVectorMath"); enc.operation = 'MULTIPLY_ADD'
    enc.inputs[1].default_value = (0.5, 0.5, 0.5); enc.inputs[2].default_value = (0.5, 0.5, 0.5)
    nt.links.new(norm.outputs["Vector"], enc.inputs[0])
    nt.links.new(enc.outputs["Vector"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


# --------------------------------------------------------------------------- scene helpers
def setup_scene(name, res_x, res_y, samples=SAMPLES):
    sc = bpy.data.scenes.new(name)
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y, r.resolution_percentage = res_x, res_y, 100
    r.film_transparent = False
    r.dither_intensity = 0.0
    c = sc.cycles
    c.device = "CPU"
    c.filter_width = 1.2
    c.samples = samples
    c.use_denoising = False
    c.max_bounces = 4
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.display_settings.display_device = "sRGB"
    return sc


def set_world(sc, colour, strength):
    w = bpy.data.worlds.new(sc.name + "_world")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*colour, 1.0)
    bg.inputs["Strength"].default_value = strength
    sc.world = w


def add_sun(sc, rot_deg, energy, angle_deg, colour=(1, 1, 1)):
    ld = bpy.data.lights.new(sc.name + "_sun", "SUN")
    ld.energy, ld.angle, ld.color = energy, math.radians(angle_deg), colour
    o = bpy.data.objects.new(ld.name, ld)
    o.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    sc.collection.objects.link(o)
    return o


def add_camera(sc, loc, rot_deg=None, ortho=None, fov_deg=None, look_at=None):
    cd = bpy.data.cameras.new(sc.name + "_cam")
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", ortho
    else:
        cd.type, cd.sensor_fit = "PERSP", "VERTICAL"
        cd.sensor_height = 24.0
        cd.lens = 12.0 / math.tan(math.radians(fov_deg) / 2)   # vertical FOV = fov_deg (Roblox default 70)
    cd.clip_start, cd.clip_end = 0.05, 600
    o = bpy.data.objects.new(cd.name, cd)
    o.location = loc
    if look_at is not None:
        d = Vector(look_at) - Vector(loc)
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    else:
        o.rotation_euler = tuple(math.radians(a) for a in (rot_deg or (0, 0, 0)))
    sc.collection.objects.link(o)
    sc.camera = o
    return o


def add_plane(sc, name, size_x, size_y, loc, uv_scale=None):
    mesh = bpy.data.meshes.new(name)
    hx, hy = size_x / 2, size_y / 2
    mesh.from_pydata([(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0)], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    sx, sy = uv_scale if uv_scale else (1, 1)
    for loop, (u, v) in zip(mesh.loops, ((0, 0), (sx, 0), (sx, sy), (0, sy))):
        uv.data[loop.index].uv = (u, v)
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    o.location = loc
    sc.collection.objects.link(o)
    return o


def render_to(sc, path, fmt="PNG", color_mode="RGB", quality=92, view="Standard"):
    sc.view_settings.view_transform = view
    s = sc.render.image_settings
    s.file_format = fmt
    s.color_mode = color_mode
    if fmt == "PNG":
        s.color_depth = "8"
        s.compression = 15
    else:
        s.quality = quality
    sc.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True, scene=sc.name)


# --------------------------------------------------------------------------- the tile
def build_tile_scene():
    sc = setup_scene("tile", RES, RES)
    coll = sc.collection
    rng = random.Random(SEED)
    centres = poisson_torus(rng, TILE, 0.20)
    clover_pts = poisson_torus(rng, TILE, 0.95)
    bld = Builder()
    n_clumps = 0
    for p in centres:
        clump_var = rng.gauss(1.0, 0.025)
        nb = rng.randint(5, 8)
        # draw the blade RNG state once per clump so wrapped copies of one clump are IDENTICAL
        state = rng.getstate()
        for q in wrapped_copies(p, 1.0):
            rng.setstate(state)
            for _ in range(nb):
                build_blade(bld, rng, q, clump_var)
        n_clumps += 1
    for p in clover_pts:
        state = rng.getstate()
        for q in wrapped_copies(p, 1.0):
            rng.setstate(state)
            build_clover(bld, rng, q)
    grass = bld.to_object("grass_blades", coll)
    # ground: dense dark-green soil under the blades (3x3 tiles so the lighting wraps)
    g = add_plane(sc, "ground", TILE * 3, TILE * 3, (TILE / 2, TILE / 2, 0.0))
    g.data.materials.append(mat_colour("ground_col", flat=lin((118, 148, 56)), rough=0.95))
    grass.data.materials.append(mat_colour("blades_col"))
    set_world(sc, (0.9, 0.95, 1.0), 1.3)
    add_sun(sc, (14, 0, 35), 1.0, 40.0, colour=(1.0, 0.97, 0.9))
    add_camera(sc, (TILE / 2, TILE / 2, 30.0), rot_deg=(0, 0, 0), ortho=TILE)
    return sc, grass, g, len(bld.faces) // 1, n_clumps


def swap_materials(grass, ground, mats):
    grass.data.materials.clear(); grass.data.materials.append(mats[0])
    ground.data.materials.clear(); ground.data.materials.append(mats[1])


# --------------------------------------------------------------------------- measuring (numpy on the written PNGs, nothing is written back)
def load_rgb(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"      # raw encoded 0..1 values, exactly what is in the file
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float64).reshape(h, w, 4)[:, :, :3]
    bpy.data.images.remove(img)
    return a


def gauss_lowpass_wrap(a, sigma_px):
    """Wrap-around Gaussian blur through the FFT (periodic, so the tile edge is not a boundary)."""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    k = np.exp(-2 * (math.pi * sigma_px) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * k))


def measure(color_png, normal_png, rough_png):
    c = load_rgb(color_png) * 255.0
    luma = 0.2126 * c[:, :, 0] + 0.7152 * c[:, :, 1] + 0.0722 * c[:, :, 2]
    mean_l = float(luma.mean())
    stats = {
        "size": list(luma.shape[::-1]),
        "tile_studs": TILE,
        "mean_rgb": [round(float(c[:, :, i].mean()), 1) for i in range(3)],
        "mean_luma": round(mean_l, 2),
        "luma_std_total": round(float(luma.std()), 2),
        "luma_std_total_pct_of_mean": round(float(luma.std()) / mean_l * 100, 2),
    }
    px_per_stud = luma.shape[1] / TILE
    bands = {}
    for label, sigma_studs in (("lowfreq_gt_1.5_studs", 0.75), ("lowfreq_gt_3_studs", 1.5), ("lowfreq_gt_6_studs", 3.0)):
        lp = gauss_lowpass_wrap(luma, sigma_studs * px_per_stud)
        bands[label] = {
            "gaussian_sigma_studs": sigma_studs,
            "std_levels_of_255": round(float(lp.std()), 3),
            "std_pct_of_mean": round(float(lp.std()) / mean_l * 100, 3),
            "peak_to_peak_levels": round(float(lp.max() - lp.min()), 3),
            "peak_to_peak_pct_of_mean": round(float(lp.max() - lp.min()) / mean_l * 100, 3),
        }
    stats["low_frequency"] = bands
    # block means: 8x8 grid (1.5 stud cells) and 4x4 grid (3 stud cells)
    for n in (8, 4):
        b = luma.reshape(n, luma.shape[0] // n, n, luma.shape[1] // n).mean(axis=(1, 3))
        stats[f"block_means_{n}x{n}"] = {"std_pct_of_mean": round(float(b.std()) / mean_l * 100, 3),
                                         "peak_to_peak_pct_of_mean": round(float(b.max() - b.min()) / mean_l * 100, 3)}
    # variance share: how much of the total luma variance sits below the 1.5 stud scale
    lp = gauss_lowpass_wrap(luma, 0.75 * px_per_stud)
    stats["variance_share_gt_1.5_studs_pct"] = round(float(lp.var() / luma.var() * 100), 3)
    # seam test: the wrap step (last column -> first column) against the ordinary pixel-to-pixel step. ~1 means invisible.
    cstep = np.abs(np.diff(luma, axis=1)).mean()
    rstep = np.abs(np.diff(luma, axis=0)).mean()
    cseam = np.abs(luma[:, 0] - luma[:, -1]).mean()
    rseam = np.abs(luma[0, :] - luma[-1, :]).mean()
    stats["seam"] = {"ordinary_step_x": round(float(cstep), 3), "wrap_step_x": round(float(cseam), 3), "ratio_x": round(float(cseam / cstep), 3),
                     "ordinary_step_y": round(float(rstep), 3), "wrap_step_y": round(float(rseam), 3), "ratio_y": round(float(rseam / rstep), 3)}
    n_ = load_rgb(normal_png)
    stats["normal"] = {"mean_rgb": [round(float(n_[:, :, i].mean() * 255), 1) for i in range(3)],
                       "min_rgb": [round(float(n_[:, :, i].min() * 255), 1) for i in range(3)],
                       "max_rgb": [round(float(n_[:, :, i].max() * 255), 1) for i in range(3)]}
    nv = n_ * 2 - 1
    tilt = np.degrees(np.arccos(np.clip(nv[:, :, 2] / np.maximum(np.linalg.norm(nv, axis=2), 1e-6), -1, 1)))
    stats["normal"]["mean_tilt_deg"] = round(float(tilt.mean()), 2)
    stats["normal"]["p95_tilt_deg"] = round(float(np.percentile(tilt, 95)), 2)
    r_ = load_rgb(rough_png)[:, :, 0]
    stats["roughness"] = {"mean": round(float(r_.mean()), 3), "min": round(float(r_.min()), 3), "max": round(float(r_.max()), 3)}
    return stats


# --------------------------------------------------------------------------- previews
def tex_node(nt, path, colorspace, scale_xy, offset=(0, 0)):
    img = bpy.data.images.load(str(path.resolve()), check_existing=True)
    img.colorspace_settings.name = colorspace
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = img
    tn.interpolation = "Linear"
    tn.extension = "REPEAT"
    uv = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale_xy[0], scale_xy[1], 1)
    mp.inputs["Location"].default_value = (offset[0], offset[1], 0)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tn.inputs["Vector"])
    return tn


def mat_textured(name, out_dir, uv_scale):
    m, nt = new_mat(name)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Specular IOR Level"].default_value = 0.12
    col = tex_node(nt, out_dir / "meadow-grass-v2-color.png", "sRGB", uv_scale)
    nrm = tex_node(nt, out_dir / "meadow-grass-v2-normal.png", "Non-Color", uv_scale)
    rgh = tex_node(nt, out_dir / "meadow-grass-v2-roughness.png", "Non-Color", uv_scale)
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.space = "TANGENT"
    nt.links.new(nrm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(rgh.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def build_tiled_scene(out_dir, n, px):
    """n x n tiles seen from straight above, colour map only (emission, so it is the pure map)."""
    sc = setup_scene(f"tiled_{n}x{n}", px, px, samples=16)
    size = TILE * n
    p = add_plane(sc, "tiles", size, size, (0, 0, 0), uv_scale=(n, n))
    m, nt = new_mat("tiles_col")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tn = tex_node(nt, out_dir / "meadow-grass-v2-color.png", "sRGB", (1, 1))
    nt.links.new(tn.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], o.inputs["Surface"])
    p.data.materials.append(m)
    set_world(sc, (0, 0, 0), 0.0)
    add_camera(sc, (0, 0, 40.0), rot_deg=(0, 0, 0), ortho=size)
    return sc


def build_gameplay_scene(out_dir, name, dist, pitch_deg, res=(1600, 900)):
    sc = setup_scene(name, res[0], res[1], samples=192)
    size = 260.0
    # left half = this texture (12 stud tiles), right half = a flat built-in-like reference colour
    left = add_plane(sc, "left_texture", size / 2, size, (-size / 4, 0, 0), uv_scale=(size / 2 / TILE, size / TILE))
    left.data.materials.append(mat_textured("left_mat", out_dir, (1, 1)))
    right = add_plane(sc, "right_flat_reference", size / 2, size, (size / 4, 0, 0))
    right.data.materials.append(mat_colour("right_mat", flat=lin(REFERENCE_SRGB), rough=0.92))
    # stand-ins for scale: a 3.5 stud dino body (orange) and two food pellets (pink) on each side, mirrored
    prop = mat_colour("prop_dino", flat=lin((214, 118, 54)), rough=0.7)
    food = mat_colour("prop_food", flat=lin((226, 96, 150)), rough=0.5)
    for sx in (-1, 1):
        for (px_, py_, r, mat) in ((5.0, 0.0, 1.75, prop), (9.5, 4.5, 0.55, food), (2.4, -4.6, 0.55, food)):
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r)
            me = bpy.data.meshes.new("prop")
            bm.to_mesh(me); bm.free()
            for poly in me.polygons:
                poly.use_smooth = True
            ob = bpy.data.objects.new("prop", me)
            ob.location = (sx * px_, py_, r)
            sc.collection.objects.link(ob)
            me.materials.append(mat)
    pitch = math.radians(pitch_deg)
    target = Vector((0.0, 0.0, 1.0))
    cam_loc = (0.0, -dist * math.cos(pitch), 1.0 + dist * math.sin(pitch))
    add_camera(sc, cam_loc, fov_deg=70.0, look_at=target)
    set_world(sc, (0.78, 0.88, 1.0), 0.9)
    add_sun(sc, (48, 8, 24), 3.2, 8.0, colour=(1.0, 0.96, 0.88))
    return sc


# --------------------------------------------------------------------------- main
def main():
    out_dir, evidence, blend = parse_args()
    out_dir = out_dir.resolve()
    evidence = evidence.resolve() if evidence else None
    out_dir.mkdir(parents=True, exist_ok=True)
    default = bpy.data.scenes[0]
    sc, grass, ground, nfaces, nclumps = build_tile_scene()
    bpy.data.scenes.remove(default)
    print(f"tile scene: {nclumps} clumps, {nfaces} quads/tris")

    paths = {k: out_dir / f"meadow-grass-v2-{k}.png" for k in ("color", "normal", "roughness")}

    # colour
    sc.view_settings.exposure = COLOR_EXPOSURE
    render_to(sc, paths["color"], view="Standard")
    sc.view_settings.exposure = 0.0
    # normal (emission, Raw view = value as is)
    swap_materials(grass, ground, (mat_emit_normal("blades_nrm", NORMAL_STRENGTH), mat_emit_const("ground_nrm", (0.5, 0.5, 1.0))))
    sc.cycles.samples = 96
    render_to(sc, paths["normal"], view="Raw")
    # roughness (emission of the per-vertex roughness; the ground is the same matte value)
    swap_materials(grass, ground, (mat_emit_attr("blades_rgh", "Rgh"), mat_emit_const("ground_rgh", (0.95, 0.95, 0.95))))
    render_to(sc, paths["roughness"], color_mode="BW", view="Raw")
    # restore the colour shaders so the saved .blend opens as the colour tile
    swap_materials(grass, ground, (bpy.data.materials["blades_col"], bpy.data.materials["ground_col"]))
    sc.cycles.samples = SAMPLES

    stats = measure(paths["color"], paths["normal"], paths["roughness"])
    stats["seed"], stats["samples"], stats["normal_strength"] = SEED, SAMPLES, NORMAL_STRENGTH
    ref_l = 0.2126 * REFERENCE_SRGB[0] + 0.7152 * REFERENCE_SRGB[1] + 0.0722 * REFERENCE_SRGB[2]
    stats["reference_flat_rgb"], stats["reference_flat_luma"] = list(REFERENCE_SRGB), round(ref_l, 2)
    print(json.dumps(stats, indent=1))

    if evidence:
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "meadow-grass-v2-stats.json").write_text(json.dumps(stats, indent=1) + "\n", encoding="utf-8")
        t3 = build_tiled_scene(out_dir, 3, 2304)
        render_to(t3, evidence / "meadow-grass-v2-tiled-3x3.jpg", fmt="JPEG", quality=92)
        for name, dist, pitch in (("gameplay-25", 25.0, 30.0), ("gameplay-40", 40.0, 24.0)):
            gs = build_gameplay_scene(out_dir, name, dist, pitch)
            render_to(gs, evidence / f"meadow-grass-v2-{name}-vs-flat.jpg", fmt="JPEG", quality=90)

    if blend:
        blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()), compress=True)


if __name__ == "__main__":
    main()
