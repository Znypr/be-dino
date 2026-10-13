"""Build the BD-049 world-prop kit and BD-050 food-pickup kit from code.

Run with Blender 5.x (headless):
  blender --background --python tools/blender/build_world_kit.py
  blender --background --python tools/blender/build_world_kit.py -- --no-render

Everything is original, low-poly geometry generated from primitives with a
fixed seed, so a rerun reproduces identical OBJ exports. Outputs:

- assets/blender/world/BD049_WorldKit.blend and BD050_FoodKit.blend: editable
  masters (one object per logical asset, collider proxies in a hidden
  "Colliders" collection, shared BD049_ palette materials).
- resources/models/world/<id>.obj/.mtl: Roblox-space (Y up, studs) closed
  triangle meshes in the repository's existing OBJ/MTL format. These feed
  tools/bake_world_kit.py (native WedgePart fallback, no uploads).
- assets/blender/world/fbx/<id>.fbx: single-mesh exports with per-face vertex
  colors for an owner-bound MeshPart upload (optional, never uploaded here).
- assets/blender/world/world-kit-manifest.json: triangles, bounds, pivot,
  collider proxies, budgets and palette for every asset.
- docs/evidence/2026-10-13-bd049-050-world-art/*.png review renders.

Pivot convention: bounding-box bottom centre (matches ResourceModels.clone).
Front of directional props faces Roblox -Z (Blender +Y). 1 Blender unit = 1 stud.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "blender" / "world"
FBX_OUT = OUT / "fbx"
OBJ_OUT = ROOT / "resources" / "models" / "world"
EVIDENCE = ROOT / "docs" / "evidence" / "2026-10-13-bd049-050-world-art"
SEED = 4950

# Shared palette (sRGB hex). Every asset in both kits uses only these swatches.
PALETTE = {
    "bark_dark": "5A3E2E", "bark": "7A563C", "bark_light": "9B7650", "deadwood": "A89A86",
    "leaf_deep": "2F6B4A", "leaf": "3F8A57", "leaf_light": "66A85E",
    "conifer": "2E5E48", "conifer_light": "417A55", "frond": "5E9E4A", "frond_light": "86B85A",
    "moss": "6F9A45", "grass": "7DAF52", "grass_dry": "B5B060",
    "flower_yellow": "F2C94C", "flower_white": "F1EDE0", "flower_violet": "9C7BD0",
    "mushroom_cap": "C8553D", "mushroom_stem": "E9DCC0",
    "rock": "7F8B8D", "rock_dark": "5E686B", "rock_light": "A3AAA6", "rock_warm": "9C8B76",
    "statue_stone": "B9B19A", "statue_dark": "8E8670", "bone": "E8DDC2", "bone_dark": "C2B597",
    "berry_red": "D6334A", "berry_purple": "6E3A8E", "leaf_food": "4FA04A",
    "fruit_orange": "F09A2E", "fruit_yellow": "F4CF4A", "egg_cream": "F2E6C4", "egg_spot": "8C6A4A",
    "egg_teal": "8FC9C4", "nest_straw": "C9A15A", "amber": "F2A33A", "amber_deep": "C8661B",
}

# Per-asset triangle ceilings (single authored LOD; native fallback costs 2 parts/triangle).
BUDGETS = {
    "tree_s": 80, "tree_m": 120, "tree_l": 160, "shrub": 60, "groundcover": 40, "prehistoric": 60,
    "rock_s": 24, "rock_m": 48, "rock_l": 72, "formation": 120, "landmark": 300,
    "food_berry": 32, "food_fruit": 40, "food_egg": 60, "food_amber": 64,
}


# ---------------------------------------------------------------- primitives

def frustum(n, r0, r1, h, phase=0.0):
    """Closed n-gon frustum (r1 > 0) or cone (r1 == 0) from z=0 to z=h."""
    verts = [(r0 * math.cos(phase + 2 * math.pi * i / n), r0 * math.sin(phase + 2 * math.pi * i / n), 0.0) for i in range(n)]
    faces = [(0, i + 1, i) for i in range(1, n - 1)]  # bottom cap, facing -Z
    if r1 > 0:
        verts += [(r1 * math.cos(phase + 2 * math.pi * i / n), r1 * math.sin(phase + 2 * math.pi * i / n), h) for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            faces += [(i, j, n + j), (i, n + j, n + i)]
        faces += [(n, n + i, n + i + 1) for i in range(1, n - 1)]
    else:
        verts.append((0.0, 0.0, h))
        faces += [(i, (i + 1) % n, n) for i in range(n)]
    return verts, faces


def box():
    v, f = frustum(4, math.sqrt(0.5), math.sqrt(0.5), 1.0, math.pi / 4)
    return [(x, y, z - 0.5) for x, y, z in v], f


def octa():
    v = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    f = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    return v, f


def leaf(length, width, thick, widest=0.4):
    """Closed diamond blade from the origin along +X (8 triangles)."""
    w = widest * length
    v = [(length, 0, 0), (0, 0, 0), (w, width / 2, 0), (w, -width / 2, 0), (w, 0, thick / 2), (w, 0, -thick / 2)]
    return v, octa()[1]


def ico():
    t = (1 + 5 ** 0.5) / 2
    raw = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
           (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    s = math.sqrt(1 + t * t)
    v = [(x / s, z / s, y / s) for x, y, z in raw]  # swap to Z-up; recalc fixes winding
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    return v, [(a, c, b) for a, b, c in f]  # axis swap mirrors, so reverse winding


def lowsphere(seg, rings):
    v = [(0, 0, 1)]
    for k in range(1, rings):
        phi = math.pi * k / rings
        v += [(math.sin(phi) * math.cos(2 * math.pi * i / seg), math.sin(phi) * math.sin(2 * math.pi * i / seg), math.cos(phi)) for i in range(seg)]
    v.append((0, 0, -1))
    bottom = len(v) - 1
    f = [(0, 1 + i, 1 + (i + 1) % seg) for i in range(seg)]
    for k in range(rings - 2):
        u, l = 1 + k * seg, 1 + (k + 1) * seg
        for i in range(seg):
            j = (i + 1) % seg
            f += [(u + i, l + i, l + j), (u + i, l + j, u + j)]
    last = 1 + (rings - 2) * seg
    f += [(bottom, last + (i + 1) % seg, last + i) for i in range(seg)]
    return v, f


# ------------------------------------------------------------------ builder

class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.v: list[Vector] = []
        self.f: list[tuple[int, int, int]] = []
        self.m: list[str] = []
        self.colliders: list[dict] = []

    def add(self, prim, mat, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), jitter=0.0):
        verts, faces = prim
        matrix = Matrix.Translation(Vector(loc)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1.0))
        base, first = len(self.v), len(self.f)
        for p in verts:
            q = matrix @ Vector(p)
            if jitter:
                q += Vector((self.rng.uniform(-jitter, jitter), self.rng.uniform(-jitter, jitter), self.rng.uniform(-jitter, jitter)))
            self.v.append(q)
        for a, b, c in faces:
            self.f.append((a + base, b + base, c + base))
            self.m.append(mat)
        return range(first, len(self.f))

    def paint(self, faces, rule):
        """Recolour faces by outward normal/centre without adding triangles."""
        centre = Vector((0, 0, 0))
        idx = {i for face in faces for i in self.f[face]}
        for i in idx:
            centre += self.v[i]
        centre /= max(1, len(idx))
        for face in faces:
            a, b, c = (self.v[i] for i in self.f[face])
            n = (b - a).cross(c - a)
            mid = (a + b + c) / 3
            if n.dot(mid - centre) < 0:
                n = -n
            n.normalize()
            new = rule(n, mid)
            if new:
                self.m[face] = new

    def collider(self, centre, size, yaw=0.0):
        self.colliders.append({"centre": list(centre), "size": list(size), "yaw": yaw})


def moss_top(threshold=0.55, mat="moss"):
    return lambda n, mid: mat if n.z > threshold else None


# ------------------------------------------------------------------- assets

TREE_H = {"conifer": (10, 17, 26), "canopy": (9, 14, 21), "cycad": (6, 10, 15), "dead": (8, 13, 19)}
SIZES = ("s", "m", "l")


def tree_conifer(b, size):
    i = SIZES.index(size); H = TREE_H["conifer"][i]; r = b.rng
    rb = 0.045 * H; sides = 7 if size == "s" else 8
    b.add(frustum(5 if size != "l" else 6, rb, rb * 0.55, 0.36 * H, r.uniform(0, 1)), "bark", jitter=0.02 * H)
    tiers = 3 if size != "l" else 4
    hc = (0.44 if tiers == 3 else 0.36) * H
    z0 = 0.2 * H
    for t in range(tiers):
        z = z0 + t * (H - z0 - hc) / (tiers - 1)
        radius = 0.31 * H * (1 - 0.2 * t)
        b.add(frustum(sides, radius, 0.0, hc, r.uniform(0, 1)), "conifer" if t % 2 == 0 else "conifer_light",
              loc=(r.uniform(-0.02, 0.02) * H, r.uniform(-0.02, 0.02) * H, z),
              rot=(r.uniform(-0.05, 0.05), r.uniform(-0.05, 0.05), 0), jitter=0.025 * H)
    ch = min(0.5 * H, 12)
    b.collider((0, 0, ch / 2), (rb * 1.7, rb * 1.7, ch))


def tree_canopy(b, size):
    i = SIZES.index(size); H = TREE_H["canopy"][i]; r = b.rng
    rb = 0.055 * H
    b.add(frustum(6, rb, rb * 0.6, 0.62 * H, r.uniform(0, 1)), "bark", rot=(0.04, -0.03, 0), jitter=0.015 * H)
    branches = (1, 2, 2)[i]
    for k in range(branches):
        a = k * math.pi + r.uniform(-0.4, 0.4)
        b.add(frustum(4, rb * 0.45, 0.0, 0.34 * H, 0.3), "bark_light", loc=(0, 0, 0.42 * H),
              rot=(0.9 * math.cos(a), 0.9 * math.sin(a), 0), jitter=0.01 * H)
    clumps = (2, 3, 4)[i]
    mats = ("leaf", "leaf_deep", "leaf_light", "leaf")
    b.add(ico(), mats[0], loc=(0, 0, 0.74 * H), scale=(0.36 * H, 0.33 * H, 0.2 * H), jitter=0.035 * H)
    for k in range(1, clumps):
        a = 2 * math.pi * k / (clumps - 1) + r.uniform(-0.3, 0.3)
        rad = 0.26 * H if clumps > 2 else 0.2 * H
        b.add(ico(), mats[k], loc=(math.cos(a) * rad, math.sin(a) * rad, (0.62 + 0.06 * r.random()) * H),
              scale=(0.24 * H, 0.22 * H, 0.15 * H), jitter=0.03 * H)
    ch = 0.5 * H
    b.collider((0, 0, ch / 2), (rb * 1.8, rb * 1.8, ch))


def tree_cycad(b, size):
    i = SIZES.index(size); H = TREE_H["cycad"][i]; r = b.rng
    segs = (1, 3, 4)[i]
    seg_h = 0.62 * H / segs
    rb = 0.075 * H
    x = y = 0.0
    lean = r.uniform(0, 2 * math.pi)
    for k in range(segs):
        b.add(frustum(5, rb * (1 - 0.1 * k), rb * (0.88 - 0.1 * k), seg_h * 1.04, k * 0.6),
              "bark" if k % 2 == 0 else "bark_light", loc=(x, y, k * seg_h), jitter=0.01 * H)
        x += math.cos(lean) * 0.03 * H; y += math.sin(lean) * 0.03 * H
    top = segs * seg_h
    b.add(frustum(5, rb * 0.9, 0.0, 0.12 * H, 0.2), "frond", loc=(x, y, top - 0.02 * H))
    fronds = (6, 7, 8)[i]
    for k in range(fronds):
        a = 2 * math.pi * k / fronds + r.uniform(-0.15, 0.15)
        pitch = r.uniform(0.15, 0.45)
        b.add(leaf(0.5 * H, 0.24 * H, 0.05 * H, 0.45), "frond" if k % 2 == 0 else "frond_light",
              loc=(x, y, top + 0.04 * H), rot=(0, -pitch, a), jitter=0.006 * H)
    ch = 0.6 * H
    b.collider((x / 2, y / 2, ch / 2), (rb * 2.0, rb * 2.0, ch))


def tree_dead(b, size):
    i = SIZES.index(size); H = TREE_H["dead"][i]; r = b.rng
    rb = 0.06 * H
    b.add(frustum(5, rb * 1.7, rb * 0.9, 0.12 * H, 0.3), "bark_dark", jitter=0.015 * H)
    b.add(frustum(5, rb, rb * 0.3, 0.88 * H, 0.0), "deadwood", rot=(r.uniform(-0.05, 0.05), r.uniform(-0.05, 0.05), 0), jitter=0.012 * H)
    branches = (2, 3, 4)[i] + (0, 0, 2)[i]
    for k in range(branches):
        a = 2.4 * k + r.uniform(-0.3, 0.3)
        z = (0.35 + 0.42 * k / max(1, branches - 1)) * H
        tilt = r.uniform(0.6, 1.0)
        length = r.uniform(0.25, 0.38) * H * (0.6 if k >= 4 else 1.0)
        b.add(frustum(4, rb * 0.4, 0.0, length, 0.4), "deadwood" if k % 2 else "bark_light",
              loc=(0, 0, z), rot=(tilt * math.cos(a), tilt * math.sin(a), 0), jitter=0.006 * H)
    ch = 0.6 * H
    b.collider((0, 0, ch / 2), (rb * 1.9, rb * 1.9, ch))


def bush(b, variant):
    r = b.rng
    if variant == "a":
        for k, (dx, dy, s, m) in enumerate(((0, 0, 1.0, "leaf"), (1.0, 0.5, 0.75, "leaf_light"), (-0.8, 0.6, 0.7, "leaf_deep"))):
            b.add(ico(), m, loc=(dx, dy, 1.0 * s + 0.1), scale=(1.4 * s, 1.3 * s, 1.1 * s), jitter=0.12)
    else:
        b.add(ico(), "leaf_deep", loc=(0, 0, 1.1), scale=(1.5, 1.3, 1.15), jitter=0.12)
        b.add(ico(), "leaf", loc=(0.9, -0.4, 0.85), scale=(1.0, 1.0, 0.85), jitter=0.1)
        for dx, dy, dz in ((0.6, 0.9, 1.9), (-0.9, -0.5, 1.7)):
            b.add(octa(), "flower_white", loc=(dx, dy, dz), scale=(0.22, 0.22, 0.16))


def fern(b, variant):
    r = b.rng
    if variant == "a":
        for k in range(6):
            a = 2 * math.pi * k / 6 + r.uniform(-0.2, 0.2)
            b.add(leaf(2.0, 0.55, 0.08, 0.5), "frond" if k % 2 else "frond_light", loc=(0, 0, 0.1),
                  rot=(0, -r.uniform(0.35, 0.65), a), jitter=0.03)
    else:
        b.add(frustum(4, 0.32, 0.22, 1.1, 0.2), "bark_dark", jitter=0.03)
        for k in range(5):
            a = 2 * math.pi * k / 5 + r.uniform(-0.2, 0.2)
            b.add(leaf(1.9, 0.6, 0.08, 0.45), "frond_light" if k % 2 else "frond", loc=(0, 0, 1.05),
                  rot=(0, -r.uniform(0.0, 0.3), a), jitter=0.03)


def grass(b, variant):
    r = b.rng
    blades = 5 if variant == "a" else 4
    mat = "grass" if variant == "a" else "grass_dry"
    for k in range(blades):
        a = 2 * math.pi * k / blades + r.uniform(-0.4, 0.4)
        h = r.uniform(1.0, 1.5) * (1.0 if variant == "a" else 1.15)
        b.add(frustum(3, 0.13, 0.0, h, r.uniform(0, 1)), mat, loc=(0.25 * math.cos(a), 0.25 * math.sin(a), 0),
              rot=(0.35 * math.sin(a), -0.35 * math.cos(a), 0))


def flowers(b, variant):
    r = b.rng
    colours = ("flower_yellow", "flower_violet", "flower_white")
    for k in range(3):
        a = 2 * math.pi * k / 3 + r.uniform(-0.3, 0.3)
        h = r.uniform(0.9, 1.3)
        x, y = 0.3 * math.cos(a), 0.3 * math.sin(a)
        tilt = (0.2 * math.sin(a), -0.2 * math.cos(a), 0)
        b.add(frustum(3, 0.07, 0.0, h, 0), "grass", loc=(x, y, 0), rot=tilt)
        tip = Euler(tilt, "XYZ").to_matrix() @ Vector((0, 0, h * 0.95))
        b.add(octa(), colours[k], loc=(x + tip.x, y + tip.y, tip.z), scale=(0.22, 0.22, 0.12), rot=(0, 0, a))


def horsetail(b):
    r = b.rng
    for k in range(4):
        a = 2 * math.pi * k / 4 + r.uniform(-0.3, 0.3)
        h = r.uniform(3.2, 4.6)
        x, y = 0.5 * math.cos(a) * (k > 0), 0.5 * math.sin(a) * (k > 0)
        tilt = (0.1 * math.sin(a) * (k > 0), -0.1 * math.cos(a) * (k > 0), 0)
        b.add(frustum(4, 0.16, 0.0, h, 0.4), "frond", loc=(x, y, 0), rot=tilt)
        mid = Euler(tilt, "XYZ").to_matrix() @ Vector((0, 0, h * 0.55))
        b.add(octa(), "frond_light", loc=(x + mid.x, y + mid.y, mid.z), scale=(0.55, 0.55, 0.12), rot=(0, 0, 0.4))


def mushrooms(b):
    r = b.rng
    for k, (dx, dy, s) in enumerate(((0, 0, 1.0), (0.9, 0.4, 0.65), (-0.6, 0.7, 0.5))):
        h = 1.6 * s
        b.add(frustum(4, 0.2 * s, 0.14 * s, h, 0.3), "mushroom_stem", loc=(dx, dy, 0))
        b.add(frustum(5, 0.75 * s, 0.0, 0.55 * s, r.uniform(0, 1)), "mushroom_cap", loc=(dx, dy, h * 0.92), jitter=0.03)


BOULDER = {"s": (1, 2.4), "m": (2, 4.0), "l": (3, 6.5)}


def boulder(b, size, mossy):
    r = b.rng
    count, H = BOULDER[size]
    parts = [((0, 0), 1.0), ((0.55, 0.35), 0.7), ((-0.5, 0.45), 0.6)][:count]
    for (dx, dy), s in parts:
        w = H * 0.62 * s
        faces = b.add(ico(), "rock", loc=(dx * H, dy * H, H * 0.42 * s), scale=(w * r.uniform(0.95, 1.2), w * r.uniform(0.85, 1.05), H * 0.5 * s),
                      rot=(0, 0, r.uniform(0, math.pi)), jitter=0.07 * H * s)
        tone = (lambda n, mid: "rock_light" if n.z > 0.6 else ("rock_dark" if n.z < -0.2 else None))
        b.paint(faces, moss_top(0.5) if mossy else tone)
        b.collider((dx * H, dy * H, H * 0.38 * s), (w * 1.5, w * 1.4, H * 0.78 * s))


def formation(b, variant):
    r = b.rng
    if variant == "spires":
        for k, (dx, dy, h) in enumerate(((0, 0, 14), (3.2, 1.6, 10), (-2.8, 1.9, 8.5), (0.6, -3.0, 6.5))):
            rad = 0.16 * h
            b.add(frustum(5, rad, rad * 0.25, h, r.uniform(0, 1)), "rock_warm" if k % 2 else "rock",
                  loc=(dx, dy, -0.5), rot=(r.uniform(-0.06, 0.06), r.uniform(-0.06, 0.06), 0), jitter=0.12)
            b.collider((dx, dy, h * 0.45 - 0.5), (rad * 1.3, rad * 1.3, h * 0.9))
        for dx, dy in ((1.5, -1.0), (-1.4, -1.8)):
            f = b.add(ico(), "rock_dark", loc=(dx, dy, 0.8), scale=(1.6, 1.4, 1.1), jitter=0.2)
            b.paint(f, moss_top(0.6))
    else:
        layers = ((0, 0, 0.0, 9.0, 6.0, 2.4), (0.4, 0.3, 2.2, 7.4, 5.0, 2.2), (-0.3, 0.6, 4.2, 5.6, 3.8, 2.0), (0.5, 0.2, 6.0, 3.6, 2.6, 1.6))
        for k, (dx, dy, z, sx, sy, sz) in enumerate(layers):
            yaw = r.uniform(-0.15, 0.15)
            f = b.add(box(), "rock_warm" if k % 2 else "rock", loc=(dx, dy, z + sz / 2), rot=(0, 0, yaw), scale=(sx, sy, sz), jitter=0.12)
            b.paint(f, moss_top(0.8))
            b.collider((dx, dy, z + sz / 2), (sx * 0.95, sy * 0.95, sz), yaw)
        f = b.add(ico(), "rock_dark", loc=(4.4, -2.2, 0.9), scale=(1.7, 1.5, 1.2), jitter=0.2)
        b.paint(f, moss_top(0.6))


def plinth(b, sx, sy, sz, mat="statue_dark", z=0.0):
    b.add(box(), mat, loc=(0, 0, z + sz / 2), scale=(sx, sy, sz), jitter=0.04)
    b.collider((0, 0, z + sz / 2), (sx, sy, sz))


def landmark_statue(b):
    r = b.rng
    plinth(b, 9.0, 14.0, 1.6, z=-0.8)
    plinth(b, 6.5, 11.0, 1.2, "statue_stone", z=0.8)
    top = 2.0
    stone = "statue_stone"
    body = b.add(ico(), stone, loc=(0, -0.6, top + 3.4), scale=(2.3, 3.9, 2.2), jitter=0.08)
    for lx, ly in ((1.3, 1.6), (-1.3, 1.6), (1.3, -2.6), (-1.3, -2.6)):
        b.add(frustum(4, 0.7, 0.55, 3.0, 0.4), stone, loc=(lx, ly, top), jitter=0.05)
    neck = b.add(frustum(5, 0.95, 0.5, 7.5, 0.2), stone, loc=(0, 2.4, top + 4.2), rot=(-0.55, 0, 0), jitter=0.05)
    b.add(octa(), stone, loc=(0, 6.7, top + 10.7), scale=(0.75, 1.35, 0.65), jitter=0.04)
    tail = b.add(frustum(5, 0.95, 0.0, 6.5, 0.2), stone, loc=(0, -4.0, top + 3.6), rot=(1.95, 0, 0), jitter=0.05)
    for faces in (body, neck, tail):
        b.paint(faces, moss_top(0.62))
    b.collider((0, -0.6, top + 3.0), (4.2, 7.4, 4.4))


def landmark_fossil(b):
    r = b.rng
    plinth(b, 7.0, 15.0, 1.0, z=-0.5)
    top = 0.5
    b.add(frustum(5, 0.42, 0.32, 12.0, 0.0), "bone_dark", loc=(0, -6.2, top + 3.6), rot=(-math.pi / 2, 0, 0), jitter=0.03)
    for k in range(5):
        y = -4.6 + k * 2.0
        span = 2.4 - 0.25 * abs(k - 2)
        for side in (1, -1):
            b.add(frustum(4, 0.22, 0.0, 3.6, 0.3), "bone", loc=(0.15 * side, y, top + 3.6),
                  rot=(0, side * (math.pi - 0.42), 0), scale=(1, 1, span / 2.4), jitter=0.02)
    b.add(ico(), "bone", loc=(0, 7.0, top + 3.4), scale=(1.4, 1.9, 1.3), jitter=0.06)
    b.add(octa(), "bone_dark", loc=(0, 8.4, top + 2.4), scale=(0.9, 1.4, 0.4))
    for side in (1, -1):
        b.add(frustum(4, 0.25, 0.0, 1.8, 0.0), "bone", loc=(0.6 * side, 7.6, top + 4.4), rot=(-0.7, 0.3 * side, 0))
    for y in (-3.5, 3.5):
        b.add(frustum(4, 0.35, 0.3, 3.4, 0.0), "statue_dark", loc=(0, y, top))
    b.collider((0, 0.5, top + 2.3), (3.6, 14.0, 4.6))


def landmark_arch(b):
    r = b.rng
    gap, clear = 13.0, 14.5
    for side in (1, -1):
        x = side * (gap / 2 + 1.8)
        b.add(box(), "rock", loc=(x, 0, 3.6), scale=(3.6, 4.2, 8.2), rot=(0, 0, r.uniform(-0.05, 0.05)), jitter=0.12)
        f = b.add(box(), "rock_warm", loc=(x + side * 0.1, 0.1, 10.9), scale=(3.4, 3.9, 7.2), rot=(0, 0, r.uniform(-0.08, 0.08)), jitter=0.12)
        b.paint(f, moss_top(0.8))
        b.collider((x, 0, 7.0), (3.4, 4.0, 15.0))
    f = b.add(box(), "rock", loc=(0, 0, clear + 1.6), scale=(gap + 8.4, 4.6, 3.2), rot=(0, 0.02, 0), jitter=0.14)
    b.paint(f, moss_top(0.7))
    b.collider((0, 0, clear + 1.6), (gap + 8.4, 4.4, 3.2))
    for dx, dy in ((gap / 2 + 4.6, 2.4), (-gap / 2 - 4.2, -2.6)):
        f = b.add(ico(), "rock_dark", loc=(dx, dy, 0.7), scale=(1.6, 1.4, 1.1), jitter=0.2)
        b.paint(f, moss_top(0.6))


def landmark_altar(b):
    r = b.rng
    plinth(b, 15.0, 15.0, 1.4, z=-0.7)
    plinth(b, 10.0, 10.0, 1.0, "statue_stone", z=0.7)
    b.add(box(), "statue_dark", loc=(0, 0, 2.9), scale=(3.6, 2.4, 2.4), jitter=0.05)
    b.collider((0, 0, 2.9), (3.6, 2.4, 2.4))
    b.add(lowsphere(6, 4), "statue_stone", loc=(0, 0, 5.15), scale=(0.95, 0.95, 1.25), jitter=0.02)
    heights = (7.5, 5.0, 3.2)
    for k, (x, y) in enumerate(((5.6, 5.6), (-5.6, 5.6), (5.6, -5.6))):
        h = heights[k]
        f = b.add(frustum(6, 0.85, 0.75, h, 0.0), "statue_stone", loc=(x, y, 0.7), jitter=0.04)
        b.paint(f, moss_top(0.7))
        b.collider((x, y, 0.7 + h / 2), (1.6, 1.6, h))
    f = b.add(frustum(6, 0.8, 0.75, 6.0, 0.0), "statue_stone", loc=(-3.2, -6.0, 1.1), rot=(0, math.pi / 2, 0.3), jitter=0.04)
    b.paint(f, moss_top(0.6))


# ---------------------------------------------------------------- food kit

def food_berry(b, variant):
    if variant == "a":
        for dx, dy, dz, s in ((0.18, 0, 0.28, 0.28), (-0.17, 0.1, 0.27, 0.27), (0.0, -0.18, 0.5, 0.26)):
            b.add(octa(), "berry_red", loc=(dx, dy, dz), scale=(s, s, s * 0.95), rot=(0.2, 0.3, 0.785))
        b.add(leaf(0.55, 0.3, 0.05, 0.5), "leaf_food", loc=(0, 0.05, 0.72), rot=(0, -0.5, 1.2))
    else:
        b.add(ico(), "berry_purple", loc=(0, 0, 0.36), scale=(0.36, 0.36, 0.34), jitter=0.015)
        b.add(leaf(0.5, 0.28, 0.05, 0.5), "leaf_food", loc=(0, 0, 0.66), rot=(0, -0.45, 0.4))


def food_fruit(b, variant):
    if variant == "a":
        b.add(ico(), "fruit_orange", loc=(0, 0, 0.5), scale=(0.44, 0.44, 0.5), jitter=0.02)
        b.add(frustum(3, 0.05, 0.0, 0.3, 0), "bark", loc=(0, 0, 0.92))
        b.add(leaf(0.55, 0.3, 0.05, 0.5), "leaf_food", loc=(0, 0, 1.0), rot=(0, -0.35, 0.8))
    else:
        f = b.add(lowsphere(6, 4), "fruit_yellow", loc=(0, 0, 0.5), scale=(0.52, 0.52, 0.48))
        b.paint(f, lambda n, mid: "fruit_orange" if (math.atan2(n.y, n.x) % (math.pi / 1.5)) < math.pi / 3 else None)
        b.add(frustum(3, 0.06, 0.0, 0.34, 0), "bark", loc=(0, 0, 0.92))


def food_egg(b, variant):
    r = b.rng
    if variant == "a":
        f = b.add(lowsphere(6, 4), "egg_cream", loc=(0, 0, 0.78), scale=(0.52, 0.52, 0.72))
        b.paint(f, lambda n, mid: "egg_spot" if r.random() < 0.3 else None)
        for k in range(5):
            a = 2 * math.pi * k / 5
            b.add(frustum(3, 0.08, 0.0, 0.9, 0.5), "nest_straw", loc=(0.55 * math.cos(a), 0.55 * math.sin(a), 0.0),
                  rot=(-0.9 * math.sin(a + 1.2), 0.9 * math.cos(a + 1.2), 0))
    else:
        f = b.add(lowsphere(6, 4), "egg_teal", loc=(0, 0, 0.78), scale=(0.5, 0.5, 0.74))
        b.paint(f, lambda n, mid: "egg_cream" if abs(n.z) < 0.35 else None)
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4
            b.add(leaf(0.75, 0.32, 0.05, 0.5), "leaf_food", loc=(0.12 * math.cos(a), 0.12 * math.sin(a), 0.06), rot=(0, -0.25, a))


def food_amber(b, variant):
    if variant == "a":
        pole = len(b.v)  # lowsphere vertex 0 is the top pole
        f = b.add(lowsphere(6, 4), "amber", loc=(0, 0, 0.98), scale=(0.5, 0.5, 0.62))
        b.v[pole] = b.v[pole] + Vector((0, 0, 0.42))  # teardrop point, still closed
        b.paint(f, lambda n, mid: "amber_deep" if n.z < -0.3 or (n.x > 0.55 and n.z < 0.2) else None)
        rock = b.add(ico(), "rock_dark", loc=(0, 0, 0.26), scale=(0.62, 0.55, 0.3), jitter=0.03)
    else:
        for dx, dy, dz, s, m in ((0.18, 0.0, 0.85, 1.0, "amber"), (-0.32, 0.12, 0.55, 0.7, "amber_deep")):
            f = b.add(lowsphere(5, 3), m, loc=(dx, dy, dz), scale=(0.42 * s, 0.42 * s, 0.55 * s))
        b.add(ico(), "rock_dark", loc=(0, 0, 0.2), scale=(0.66, 0.56, 0.26), jitter=0.03)


# Logical id -> (builder, args, kind, family, size class, budget key, kit)
ASSETS = {}
for fam, fn in (("conifer", tree_conifer), ("canopy", tree_canopy), ("cycad", tree_cycad), ("dead", tree_dead)):
    for s in SIZES:
        ASSETS[f"world_tree_{fam}_{s}"] = (fn, (s,), "tree", fam, s, f"tree_{s}", "world")
for v in ("a", "b"):
    ASSETS[f"world_bush_{v}"] = (bush, (v,), "shrub", "bush", "m", "shrub", "world")
    ASSETS[f"world_fern_{v}"] = (fern, (v,), "shrub", "fern", "s", "shrub", "world")
    ASSETS[f"world_grass_{v}"] = (grass, (v,), "groundcover", "grass", "s", "groundcover", "world")
ASSETS["world_flowers_a"] = (flowers, ("a",), "groundcover", "flowers", "s", "groundcover", "world")
ASSETS["world_horsetail_a"] = (horsetail, (), "shrub", "horsetail", "m", "prehistoric", "world")
ASSETS["world_mushrooms_a"] = (mushrooms, (), "shrub", "mushrooms", "s", "prehistoric", "world")
for mossy in (True, False):
    for s in SIZES:
        ASSETS[f"world_boulder_{'mossy' if mossy else 'bare'}_{s}"] = (boulder, (s, mossy), "rock", "boulder_mossy" if mossy else "boulder_bare", s, f"rock_{s}", "world")
ASSETS["world_rocks_spires"] = (formation, ("spires",), "rock", "formation", "l", "formation", "world")
ASSETS["world_rocks_ledge"] = (formation, ("ledge",), "rock", "formation", "l", "formation", "world")
ASSETS["world_landmark_dino_statue"] = (landmark_statue, (), "landmark", "landmark", "l", "landmark", "world")
ASSETS["world_landmark_fossil_display"] = (landmark_fossil, (), "landmark", "landmark", "l", "landmark", "world")
ASSETS["world_landmark_stone_arch"] = (landmark_arch, (), "landmark", "landmark", "l", "landmark", "world")
ASSETS["world_landmark_ruins_altar"] = (landmark_altar, (), "landmark", "landmark", "l", "landmark", "world")
FOOD = {"berry": (food_berry, 1), "fruit": (food_fruit, 4), "egg": (food_egg, 15), "amber": (food_amber, 50)}
for name, (fn, points) in FOOD.items():
    for v in ("a", "b"):
        ASSETS[f"food_{name}_{v}"] = (fn, (v,), "food", name, "s", f"food_{name}", "food")


# ------------------------------------------------------------ blender glue

def srgb(hexcode):
    c = [int(hexcode[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def make_materials():
    mats = {}
    for name, hexcode in PALETTE.items():
        mat = bpy.data.materials.new("BD049_" + name)
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (*srgb(hexcode), 1)
        bsdf.inputs["Roughness"].default_value = 0.35 if name.startswith("amber") else 0.82
        if name.startswith("amber"):
            bsdf.inputs["Emission Color"].default_value = (*srgb(hexcode), 1)
            bsdf.inputs["Emission Strength"].default_value = 0.25
        mat.diffuse_color = (*srgb(hexcode), 1)
        mats[name] = mat
    return mats


def build_asset(asset_id, mats, collection, collider_collection):
    fn, args, kind, family, size, budget, kit = ASSETS[asset_id]
    rng = random.Random(f"{SEED}:{asset_id}")
    b = Builder(rng)
    fn(b, *args)
    lo = Vector((min(v.x for v in b.v), min(v.y for v in b.v), min(v.z for v in b.v)))
    hi = Vector((max(v.x for v in b.v), max(v.y for v in b.v), max(v.z for v in b.v)))
    shift = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    verts = [tuple(v + shift) for v in b.v]
    mesh = bpy.data.meshes.new(asset_id)
    mesh.from_pydata(verts, [], b.f)
    used = sorted(set(b.m), key=list(PALETTE).index)
    for name in used:
        mesh.materials.append(mats[name])
    for poly, name in zip(mesh.polygons, b.m):
        poly.material_index = used.index(name)
        poly.use_smooth = False
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    colour = mesh.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for poly in mesh.polygons:
        rgba = (*srgb(PALETTE[used[poly.material_index]]), 1.0)
        for li in poly.loop_indices:
            colour.data[li].color = rgba
    obj = bpy.data.objects.new(asset_id, mesh)
    collection.objects.link(obj)
    for k, c in enumerate(b.colliders):
        centre = Vector(c["centre"]) + shift
        c["centre"] = list(centre)
        proxy = bpy.data.objects.new(f"{asset_id}_collider{k + 1}", None)
        proxy.empty_display_type = "CUBE"
        proxy.empty_display_size = 0.5
        proxy.scale = Vector(c["size"])
        proxy.rotation_euler = (0, 0, c["yaw"])
        proxy.location = centre
        proxy.parent = obj
        collider_collection.objects.link(proxy)
    obj["logical_id"] = asset_id
    obj["kind"] = kind
    obj["triangle_budget"] = BUDGETS[budget]
    return obj, b.colliders


def to_roblox(v):
    return (v[0], v[2], -v[1])


def r5(x):
    value = round(x, 5)
    return 0.0 if value == 0 else value


def export_obj(obj):
    mesh = obj.data
    names = [m.name.replace("BD049_", "") for m in mesh.materials]
    lines = [f"mtllib {obj.name}.mtl", f"o {obj.name}"]
    verts = [tuple(r5(c) for c in to_roblox(v.co)) for v in mesh.vertices]
    lines += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in verts]
    current = None
    for poly in sorted(mesh.polygons, key=lambda p: (p.material_index, p.index)):
        if poly.material_index != current:
            current = poly.material_index
            lines.append(f"usemtl {names[current]}")
        a, b, c = (i + 1 for i in poly.vertices)
        lines.append(f"f {a} {b} {c}")
    (OBJ_OUT / f"{obj.name}.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")
    mtl = []
    for name in names:
        rgb = [int(PALETTE[name][i:i + 2], 16) / 255 for i in (0, 2, 4)]
        mtl += [f"newmtl {name}", "Kd " + " ".join(f"{c:.5f}" for c in rgb), "Ka 0.15 0.15 0.15", "Ks 0.05 0.05 0.05", "Ns 16", ""]
    (OBJ_OUT / f"{obj.name}.mtl").write_text("\n".join(mtl), encoding="utf-8")
    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    return len(mesh.polygons), [lo, hi], names


def export_fbx(obj):
    original = obj.location.copy()
    obj.location = (0, 0, 0)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = FBX_OUT / f"{obj.name}.fbx"
    try:
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                                 axis_forward="-Z", axis_up="Y", colors_type="SRGB", mesh_smooth_type="FACE",
                                 add_leaf_bones=False, bake_anim=False)
        result = path.relative_to(ROOT).as_posix()
    except Exception as error:  # exporter missing or renamed in a future Blender
        print("FBX export unavailable:", error)
        result = None
    obj.location = original
    return result


# ---------------------------------------------------------------- staging

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render(width, height, samples=32):
    scene = bpy.context.scene
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else engines[0]
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    world = bpy.data.worlds.new("BD049_Sky")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*srgb("BFD9E6"), 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.lights.new("BD049_Sun", "SUN")
    sun.energy = 3.2
    sun_obj = bpy.data.objects.new("BD049_Sun", sun)
    sun_obj.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    scene.collection.objects.link(sun_obj)


def add_ground(name, size, location, colour="8FB86A"):
    mesh = bpy.data.meshes.new(name)
    s = size / 2
    mesh.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*srgb(colour), 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_label(text, location, size):
    curve = bpy.data.curves.new("label_" + text, "FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new("label_" + text, curve)
    obj.location = location
    obj.rotation_euler = (math.radians(90), 0, 0)
    mat = bpy.data.materials.new("label_mat_" + text)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.02, 0.05, 0.04, 1)
    curve.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def camera(name, target, distance, ortho, elevation=18.0, azimuth=-90.0):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = ortho
    cam.clip_end = 2000
    obj = bpy.data.objects.new(name, cam)
    el, az = math.radians(elevation), math.radians(azimuth)
    obj.location = Vector(target) + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * distance
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(obj)
    return obj


def layout_row(objs, y, gap, label_size, labels=True):
    widths = [o.dimensions.x for o in objs]
    total = sum(widths) + gap * (len(objs) - 1)
    x = -total / 2
    staged = []
    for o, w in zip(objs, widths):
        o.location = (x + w / 2, y, 0)
        if labels:
            staged.append(add_label(o.name.replace("world_", "").replace("food_", ""), (x + w / 2, y - max(1.0, o.dimensions.y / 2) - 0.4, 0.05), label_size))
        x += w + gap
    return total, staged


def render(path, cam, visible):
    scene = bpy.context.scene
    scene.camera = cam
    for o in scene.objects:
        if o.type in {"MESH", "FONT"}:
            o.hide_render = o not in visible
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# -------------------------------------------------------------------- main

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--no-render" not in args
    for d in (OUT, FBX_OUT, OBJ_OUT, EVIDENCE):
        d.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "generator": "tools/blender/build_world_kit.py", "seed": SEED,
                "units": "1 Blender unit = 1 Roblox stud; OBJ exported Y-up", "pivot": "bounding-box bottom centre",
                "front": "Roblox -Z (Blender +Y)", "rights": "Original Be Dino! geometry generated from primitives; no third-party models or textures.",
                "palette": PALETTE, "budgets": BUDGETS, "assets": []}
    for kit, blend_name in (("world", "BD049_WorldKit.blend"), ("food", "BD050_FoodKit.blend")):
        clear_scene()
        mats = make_materials()
        root = bpy.context.scene.collection
        collider_collection = bpy.data.collections.new("Colliders")
        groups = {}
        objs = {}
        for asset_id, spec in ASSETS.items():
            if spec[6] != kit:
                continue
            kind = spec[2]
            if kind not in groups:
                groups[kind] = bpy.data.collections.new(kind.capitalize())
                root.children.link(groups[kind])
            obj, colliders = build_asset(asset_id, mats, groups[kind], collider_collection)
            tris, bounds, used = export_obj(obj)
            fbx = export_fbx(obj)
            budget = BUDGETS[spec[5]]
            if tris > budget:
                raise SystemExit(f"{asset_id}: {tris} triangles exceeds budget {budget}")
            roblox_colliders = []
            for c in colliders:
                cx, cy, cz = to_roblox(c["centre"])
                sx, sy, sz = c["size"]
                roblox_colliders.append({"centre": [r5(cx), r5(cy), r5(cz)], "size": [r5(sx), r5(sz), r5(sy)], "yaw": r5(c["yaw"])})
            entry = {"id": asset_id, "kit": kit, "kind": kind, "family": spec[3], "sizeClass": spec[4], "triangles": tris,
                     "budget": budget, "bounds": bounds, "colliders": roblox_colliders, "materials": used,
                     "obj": f"resources/models/world/{asset_id}.obj", "fbx": fbx, "blend": f"assets/blender/world/{blend_name}"}
            if kit == "food":
                entry["points"] = FOOD[spec[3]][1]
            manifest["assets"].append(entry)
            objs[asset_id] = obj
        root.children.link(collider_collection)
        collider_collection.hide_render = True
        setup_render(2400, 1100)
        stage(kit, objs, do_render)
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / blend_name), compress=True)
    (OUT / "world-kit-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"World kit: {len(manifest['assets'])} assets, {sum(a['triangles'] for a in manifest['assets'])} triangles")


def stage(kit, objs, do_render):
    if kit == "food":
        ids = sorted(objs, key=lambda i: (list(FOOD).index(i.split("_")[1]), i))
        row = [objs[i] for i in ids]
        total, labels = layout_row(row, 0, 0.7, 0.22)
        ground = add_ground("Ground", 60, (0, 0, 0))
        cam = camera("CamFoodKit", (0, 0, 0.6), 40, total + 1.6, 16)
        # Gameplay-scale readability: food beside the repository's own Compy at the default camera pitch.
        compy = None
        try:
            bpy.ops.wm.obj_import(filepath=str(ROOT / "resources/models/compy.obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
            compy = bpy.context.selected_objects[0]
            compy.location = (0, 14, 0)
        except Exception as error:
            print("Compy reference unavailable:", error)
        clones = []
        for k, o in enumerate(row):
            c = o.copy()
            c.location = (-6 + k * 1.7, 9.5 + (k % 2) * 1.2, 0)
            bpy.context.scene.collection.objects.link(c)
            clones.append(c)
        cam2 = camera("CamFoodGameplay", (0, 11, 1.0), 80, 26, 38, -100)
        if do_render:
            render(EVIDENCE / "bd050-food-kit.png", cam, set(row) | set(labels) | {ground})
            bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1600, 900
            render(EVIDENCE / "bd050-food-gameplay-scale.png", cam2, set(clones) | {ground} | ({compy} if compy else set()))
        return
    rows = {
        "trees": [i for i in objs if "_tree_" in i],
        "rocks": [i for i in objs if "boulder" in i or "_rocks_" in i],
        "foliage": [i for i in objs if objs[i]["kind"] in {"shrub", "groundcover"}],
        "landmarks": [i for i in objs if "landmark" in i],
    }
    ground = add_ground("Ground", 600, (0, 0, 0))
    y = 0
    plan = []
    for name, ids in rows.items():
        row = [objs[i] for i in ids]
        depth = max(o.dimensions.y for o in row)
        gap = {"trees": 3.0, "rocks": 2.0, "foliage": 1.0, "landmarks": 5.0}[name]
        label = {"trees": 0.9, "rocks": 0.7, "foliage": 0.35, "landmarks": 1.1}[name]
        total, labels = layout_row(row, y, gap, label)
        height = max(o.dimensions.z for o in row)
        plan.append((name, row, labels, y, total, height))
        y += depth + 30
    vignette = []
    rng = random.Random(SEED)
    picks = [i for i in objs if "landmark" not in i and "spires" not in i]
    for k in range(70):
        src = objs[rng.choice(picks)]
        c = src.copy()
        a, rad = rng.uniform(0, 2 * math.pi), rng.uniform(10, 55)
        c.location = (math.cos(a) * rad, y + 60 + math.sin(a) * rad, 0)
        c.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        bpy.context.scene.collection.objects.link(c)
        vignette.append(c)
    statue = objs["world_landmark_dino_statue"].copy()
    statue.location = (0, y + 60, 0)
    bpy.context.scene.collection.objects.link(statue)
    vignette.append(statue)
    if not do_render:
        return
    for name, row, labels, ry, total, height in plan:
        cam = camera(f"Cam_{name}", (0, ry, height * 0.42), 300, max(total + 6, height * 2.4), 12)
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 2400, 1000
        render(EVIDENCE / f"bd049-{name}.png", cam, set(row) | set(labels) | {ground})
    cam = camera("Cam_vignette", (0, y + 60, 2), 300, 120, 30, -70)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 2000, 1100
    render(EVIDENCE / "bd049-biome-vignette.png", cam, set(vignette) | {ground})


if __name__ == "__main__":
    main()
