"""Tier coat colour maps v2 (docs/114 s8.6, docs/115 "fused tier look", approach C). Headless Blender:

  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b -P tools/blender/bake_tier_coat_v2.py -- [obj] [out_dir]

Reads the raptor OBJ (assets/blender/creatures/lowpoly/raptor.obj, the ORIGINAL Roblox UVs), and for every part and tier (gold, emerald,
diamond) bakes resources/effects/tiers/raptor-<part>-<tier>-v2-color.png, 512 x 512 straight RGBA, in that part's own UV space.

LEAD / OWNER 2026-10-17 (Studio): the v1 maps (random facet patches, ~18% alpha) read as yellow blotches and washed the stripes. So v2 is a
SMOOTH GRADIENT ONLY, no per-facet colour at all (the crystal facets live in the normal map, tier-crystal-normal.png, never in colour):
  alpha  ~0.88 at silhouette edges and thin parts, a soft band about 2-3x wider than round 1 (round 2, owner: 'bleed more in'), fading smoothly to ~0.05 in the middle of a part (stripes keep their true colours),
  colour a smooth ramp: the tier core colour in the middle, the tier edge colour (gold warm light, emerald mint, diamond white) at the edge.
The edge field is view independent and computed per texel in 3D: the distance to the nearest sharp crease or open mesh edge (the places a
low-poly dino's silhouette runs along), scaled by the crease sharpness, with an ABSOLUTE reach so thin parts (arms, toes, tail) get more
coat than fat ones. Texels outside the UV islands are filled by bleed (dilation) so mip-maps and filtering never show a seam.
Also writes tier-crystal-roughness-gem.png: the shared Blender-baked roughness map scaled down for the non-metallic Emerald / Diamond.
Prints the mean alpha of the whole image and of the UV-covered texels per part and tier.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OBJ = ARGS[0] if len(ARGS) > 0 else os.path.join(ROOT, "assets/blender/creatures/lowpoly/raptor.obj")
OUT = ARGS[1] if len(ARGS) > 1 else os.path.join(ROOT, "resources/effects/tiers")
SIZE = 512
PARTS = ("body", "head", "tail", "leftarm", "rightarm", "leftleg", "rightleg")

ALPHA_MIN = 0.05      # the middle of a part: the stripes keep their true colours
ALPHA_MAX = 0.88      # silhouette edges and thin parts
TARGET_MEAN = 0.42    # mean alpha over the UV-covered texels of EACH part (lead 2026-10-17 round 2: wide soft band, ~0.40-0.45)
MIN_REACH = 0.14      # world units
CREASE_FROM, CREASE_FULL = 6.0, 45.0  # dihedral angle (degrees) where a crease starts to count / counts fully

# straight-alpha sRGB colours: (core in the middle, edge at the silhouette)
TIERS = {
    "gold": ((250, 186, 38), (255, 228, 128)),        # rich warm gold, light gold edge
    "emerald": ((20, 190, 100), (150, 255, 200)),     # jewel green, mint edge
    "diamond": ((176, 218, 248), (246, 252, 255)),    # icy blue, white edge
}


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def import_parts():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=OBJ)
    objs = {o.name.replace("_geom", ""): o for o in bpy.data.objects if o.type == "MESH"}
    missing = [p for p in PARTS if p not in objs]
    if missing:
        raise SystemExit("OBJ is missing parts: %s" % missing)
    return objs


def crease_edges(me):
    """Segments (a, b, weight): open mesh edges weight 1, interior edges by dihedral angle."""
    bm = bmesh.new()
    bm.from_mesh(me)
    segs = []
    for e in bm.edges:
        if e.is_boundary or len(e.link_faces) == 1:
            w = 1.0
        elif len(e.link_faces) == 2:
            ang = math.degrees(e.calc_face_angle(0.0))
            w = float(np.clip((ang - CREASE_FROM) / (CREASE_FULL - CREASE_FROM), 0.0, 1.0))
        else:
            w = 1.0
        if w > 0.02:
            segs.append((np.array(e.verts[0].co), np.array(e.verts[1].co), w))
    bm.free()
    return segs


def rasterize(me):
    """Per texel of the part's UV space: covered mask and 3D position (barycentric over the loop triangles)."""
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    co = np.array([v.co[:] for v in me.vertices], dtype=np.float64)
    pos = np.zeros((SIZE, SIZE, 3))
    cov = np.zeros((SIZE, SIZE), bool)
    for tri in me.loop_triangles:
        uv = np.array([uvl[l].uv[:] for l in tri.loops], dtype=np.float64) * SIZE
        p3 = co[list(tri.vertices)]
        x0, y0 = np.floor(uv.min(0)).astype(int) - 1
        x1, y1 = np.ceil(uv.max(0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, SIZE - 1), min(y1, SIZE - 1)
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (uv[1, 1] - uv[2, 1]) * (uv[0, 0] - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (uv[0, 1] - uv[2, 1])
        if abs(d) < 1e-12:
            continue
        l0 = ((uv[1, 1] - uv[2, 1]) * (xs - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (ys - uv[2, 1])) / d
        l1 = ((uv[2, 1] - uv[0, 1]) * (xs - uv[2, 0]) + (uv[0, 0] - uv[2, 0]) * (ys - uv[2, 1])) / d
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -0.02) & (l1 >= -0.02) & (l2 >= -0.02)
        if not inside.any():
            continue
        pp = l0[..., None] * p3[0] + l1[..., None] * p3[1] + l2[..., None] * p3[2]
        sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        pos[sl][inside] = pp[inside]
        cov[sl] |= inside
    return cov, pos


def effective_distance(cov, pos, segs):
    """Per covered texel: min over creases of (distance / sharpness): an edge of weight w reaches REACH * w^1.6."""
    pts = pos[cov]
    best = np.full(len(pts), 1e9)
    for a, b, w in segs:
        ab = b - a
        t = np.clip(((pts - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
        d = np.linalg.norm(pts - (a + t[:, None] * ab), axis=1) / (w ** 1.6)   # shallow creases barely count, sharp ones reach far
        np.minimum(best, d, out=best)
    return best


def bleed(img, cov, iterations=24):
    """Fill texels outside the UV islands from the nearest covered texel (dilation), so filtering never shows a seam."""
    img = img.copy()
    have = cov.copy()
    for _ in range(iterations):
        if have.all():
            break
        acc = np.zeros_like(img)
        cnt = np.zeros(have.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            h = np.roll(np.roll(have, dy, 0), dx, 1)
            v = np.roll(np.roll(img, dy, 0), dx, 1)
            acc += v * h[..., None]
            cnt += h
        fill = (~have) & (cnt > 0)
        img[fill] = acc[fill] / cnt[fill][..., None]
        have |= fill
    return img, have


def blur(img, cov, sigma=1.6):
    """Smooth the edge field a little (separable gaussian) but only mix covered texels, so islands do not leak into the gutter."""
    r = int(math.ceil(sigma * 3))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    m = cov.astype(np.float64)
    a = img * m
    for axis in (0, 1):
        a = sum(k[i] * np.roll(a, i - r, axis) for i in range(len(k)))
        m = sum(k[i] * np.roll(m, i - r, axis) for i in range(len(k)))
    return a / np.maximum(m, 1e-9)


def field_for(reach, cov, deff):
    f = np.zeros((SIZE, SIZE))
    f[cov] = 1.0 - smooth(deff / reach)   # 1 at a sharp crease, 0 far from any
    return f


def save_png(path, rgba):
    img = bpy.data.images.new("tmp", SIZE, SIZE, alpha=True)
    img.colorspace_settings.name = "Non-Color"   # the values below ARE the sRGB bytes
    img.alpha_mode = "STRAIGHT"
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def main():
    os.makedirs(OUT, exist_ok=True)
    objs = import_parts()
    data = {}
    for part in PARTS:
        me = objs[part].data
        cov, pos = rasterize(me)
        deff = effective_distance(cov, pos, crease_edges(me))
        data[part] = (cov, deff)
        print("%-9s uv coverage %.2f, creases %d" % (part, cov.mean(), len(crease_edges(me))))
    # one reach PER PART, tuned so every part's mean alpha over its UV-covered texels lands on TARGET_MEAN: the band then scales with the
    # part (a soft gradient covering roughly the outer 25-35% of its silhouette width, strongest at the crease, fading out smoothly)
    def part_mean(reach, cov, deff):
        f = blur(field_for(reach, cov, deff), cov)
        return (ALPHA_MIN + (ALPHA_MAX - ALPHA_MIN) * np.clip(f, 0, 1))[cov].mean()
    reaches = {}
    for part, (cov, deff) in data.items():
        lo, hi = 0.03, 6.0
        for _ in range(20):
            mid = (lo + hi) / 2
            if part_mean(mid, cov, deff) < TARGET_MEAN:
                lo = mid
            else:
                hi = mid
        reaches[part] = max((lo + hi) / 2, MIN_REACH)   # thin parts (arms) get a band of at least MIN_REACH, so they are strong, never a net of fine lines
        print("REACH %-9s %.3f -> covered mean alpha %.3f" % (part, reaches[part], part_mean(reaches[part], cov, deff)))

    report = {}
    for part in PARTS:
        cov, deff = data[part]
        f = blur(field_for(reaches[part], cov, deff), cov)
        f, _ = bleed(f[..., None], cov)
        f = np.clip(f[..., 0], 0.0, 1.0)
        f[~np.isfinite(f)] = 0.0
        alpha = ALPHA_MIN + (ALPHA_MAX - ALPHA_MIN) * f
        for tier, (core, edge) in TIERS.items():
            core = np.array(core, dtype=np.float64) / 255.0
            edge = np.array(edge, dtype=np.float64) / 255.0
            t = smooth(f)[..., None]
            rgb = core * (1.0 - t) + edge * t        # smooth ramp, no per-facet colour
            rgba = np.concatenate([rgb, alpha[..., None]], axis=2)
            save_png(os.path.join(OUT, "raptor-%s-%s-v2-color.png" % (part, tier)), rgba)
            report[(part, tier)] = (alpha.mean(), alpha[cov].mean(), (alpha[cov] <= 0.10).mean())
    for tier in TIERS:
        full = np.mean([report[(p, tier)][0] for p in PARTS])
        covd = np.mean([report[(p, tier)][1] for p in PARTS])
        print("TIER %-8s mean alpha: whole image %.3f, UV-covered %.3f" % (tier, full, covd))
        for p in PARTS:
            print("   %-9s whole %.3f covered %.3f, share of covered texels with alpha <= 0.10: %.2f" % (p, *report[(p, tier)]))

    # lower roughness for the non-metallic gems: the shared Blender-baked roughness map, scaled down (gold keeps the original)
    src = bpy.data.images.load(os.path.join(OUT, "tier-crystal-roughness.png"))
    px = np.array(src.pixels[:], dtype=np.float32).reshape(-1, 4)
    px[:, :3] *= 0.5
    img = bpy.data.images.new("gem_rough", src.size[0], src.size[1], alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(OUT, "tier-crystal-roughness-gem.png")
    img.file_format = "PNG"
    img.save()
    print("gem roughness mean %.3f (was %.3f)" % (px[:, 0].mean(), px[:, 0].mean() * 2))


main()
