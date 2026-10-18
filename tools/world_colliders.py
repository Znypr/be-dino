#!/usr/bin/env python3
"""BD-1098: the SOLID world as the server builds it, seen offline: every collider box of the island dressing as a footprint on the ground plane.

Studio round 5 (docs/197) found 60 of 3,600 foods inside a WorldKit collider box. The food generator only knew the terrain (water, slope,
spawn disc), not the rocks, trunks, logs and landmarks that Arena.biomeKit() puts on it. This module closes that hole without Roblox:

  * the placements come from the REAL pure grammar (BiomePlacement.generate with the playtest profile: BiomeKit, density 1.25, the cave hub
    rectangle) run in the pinned Luau runner, the same harness as tools/verify_world_overlap.py (estimate_world_budget.luau_script);
  * the boxes follow src/server/Arena.luau exactly: kit colliders = pivot * CFrame(c.xyz * scale) * Angles(0, c[7], 0) with size c[4..6] * scale,
    the pivot being CFrame(x, y, z) * Angles(0, yaw, 0) * Angles(0, 0, roll); a fallen log is ONE box (c[4], extent.y * .9, c[6]) * scale at the pivot
    plus extent.y * .45 * scale up its (rolled) local Y; colliders of ids with none (shrubs, ground cover) add nothing;
  * the parts Arena.build() always makes: the arch pillars and lintel, the four jump stones, and the ring of boundary boulders (their yaw and scale
    use Roblox's Random, which cannot run here, so each slot is a disc of the farthest reach at the largest scale 2.6: never too small);
  * every box is reduced to the convex hull of its 8 corners on the XZ plane. Height is ignored on purpose: a food under an overhang or on top of
    a low box is also "inside" for the Studio check (GetPartBoundsInBox), and a few studs of extra clearance cost nothing.

Not modelled (all off or empty in the shipped state): colliders re-fitted from a colossal ancient mesh (Generated.Colossal asset ids are empty) and
Blender ground props (Generated.Props ids are empty; when filled, Kit = Biome.withProps already brings their colliders). The raycast height fix-up
of Arena only moves a prop up or down, never sideways, so the footprint on the ground plane does not change.

    python tools/world_colliders.py --runner luau.exe [--foods build/foods.txt]     # summary (and a check of a list of foods x,z per line)
"""
from pathlib import Path
import argparse
import math
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_world_budget as est  # noqa: E402
import release_profiles  # noqa: E402

DUMP = r'''
for _, p in a do print(string.format("P\t%s\t%s\t%.4f\t%.4f\t%.4f\t%.6f\t%.6f\t%.6f", p.layer, p.id, p.x, p.y, p.z, p.yaw, p.roll or 0, p.scale)) end
for id, d in Kit do
 for _, c in d.colliders do print(string.format("C\t%s\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.6f", id, c[1], c[2], c[3], c[4], c[5], c[6], c[7])) end
 print(string.format("E\t%s\t%s\t%.4f\t%.4f\t%.4f", id, d.kind, d.extent[1], d.extent[2], d.extent[3]))
end
print("H\t" .. tostring(Config.CaveHub == true))
'''

# Arena.build(), every time (kit mode): the ring of boundary boulders, the arch, the jump stones. Numbers copied from src/server/Arena.luau;
# tests/test_world_colliders.py greps the source so a change there fails the test.
ARENA_HALF = 416.0
SCALE = 1.6                                  # IslandLayout.Scale
RING_SLOTS = 5                               # kit mode: slots = 5 (i = 0..5) per side
RING_OFFSET = 5.0                            # the ring sits 5 studs outside the boundary
RING_MAX_SCALE = 2.6                         # random:NextNumber(1.6, 2.6)
RING_IDS = ('world_boulder_bare_l', 'world_boulder_mossy_l')
ARCH_Z = -15 * SCALE
ARCH_PILLAR = (7 * SCALE, 23 * SCALE, 8 * SCALE)                 # Vector3.new(7, 23, 8) * S, at x = -96 S and -64 S
ARCH_TOP = (42 * SCALE, 6 * SCALE, 9 * SCALE)                    # at x = -80 S
JUMP_STONE_SIZE = 6.0                                            # Vector3.new(6, 1.2 + i * .4, 6) at (30 + i * 10, -30)


# ------------------------------------------------------------------------------ small 3 x 3 matrices (Roblox CFrame.Angles rules)
def ry(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def hull(points):
    """Convex hull (Andrew's monotone chain) of (x, z) points, counter clockwise."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def box_footprint(pivot, rot, local_centre, size, extra_yaw=0.0):
    """XZ hull of a box. pivot = (x, y, z) of the prop; rot = the prop's 3 x 3 rotation; local_centre and size are in pivot space (already scaled)."""
    r = mul(rot, ry(extra_yaw))
    out = []
    for sx in (-.5, .5):
        for sy in (-.5, .5):
            for sz in (-.5, .5):
                corner = apply(r, (sx * size[0], sy * size[1], sz * size[2]))
                centre = apply(rot, local_centre)
                out.append((pivot[0] + centre[0] + corner[0], pivot[2] + centre[2] + corner[2]))
    return hull(out)


# ------------------------------------------------------------------------------ the obstacles
class Obstacle:
    __slots__ = ('kind', 'poly', 'cx', 'cz', 'r', 'min_x', 'max_x', 'min_z', 'max_z', 'label')

    def __init__(self, kind, poly=None, centre=None, radius=0.0, label=''):
        self.kind, self.label = kind, label
        if poly is not None:
            self.poly = poly
            self.cx = sum(p[0] for p in poly) / len(poly)
            self.cz = sum(p[1] for p in poly) / len(poly)
            self.r = 0.0
            self.min_x, self.max_x = min(p[0] for p in poly), max(p[0] for p in poly)
            self.min_z, self.max_z = min(p[1] for p in poly), max(p[1] for p in poly)
        else:
            self.poly = None
            self.cx, self.cz = centre
            self.r = radius
            self.min_x, self.max_x, self.min_z, self.max_z = self.cx - radius, self.cx + radius, self.cz - radius, self.cz + radius

    def distance(self, x, z):
        """Studs from (x, z) to the footprint (0 when inside)."""
        if self.poly is None:
            return max(0.0, math.hypot(x - self.cx, z - self.cz) - self.r)
        poly, n = self.poly, len(self.poly)
        if n < 3:
            return min(math.hypot(x - px, z - pz) for px, pz in poly)
        inside = True
        best = math.inf
        for i in range(n):
            ax, az = poly[i]
            bx, bz = poly[(i + 1) % n]
            ex, ez = bx - ax, bz - az
            side = ex * (z - az) - ez * (x - ax)
            if side < 0:
                inside = False
            t = max(0.0, min(1.0, ((x - ax) * ex + (z - az) * ez) / (ex * ex + ez * ez or 1.0)))
            best = min(best, math.hypot(x - (ax + t * ex), z - (az + t * ez)))
        return 0.0 if inside else best


class Obstacles:
    """All obstacles in a coarse hash; distance(x, z) answers 'how far is the nearest solid thing' up to `cap`."""

    def __init__(self, items, bucket=24.0):
        self.items, self.bucket, self.cells = items, bucket, {}
        for k, o in enumerate(items):
            for bx in range(math.floor(o.min_x / bucket), math.floor(o.max_x / bucket) + 1):
                for bz in range(math.floor(o.min_z / bucket), math.floor(o.max_z / bucket) + 1):
                    self.cells.setdefault((bx, bz), []).append(k)

    def distance(self, x, z, cap=6.0):
        bucket = self.bucket
        reach = int(cap // bucket) + 1
        bx, bz = math.floor(x / bucket), math.floor(z / bucket)
        seen, best = set(), cap
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                for k in self.cells.get((bx + dx, bz + dz), ()):
                    if k in seen:
                        continue
                    seen.add(k)
                    o = self.items[k]
                    if o.min_x - best > x or o.max_x + best < x or o.min_z - best > z or o.max_z + best < z:
                        continue
                    best = min(best, o.distance(x, z))
        return best

    def nearest(self, x, z, cap=6.0):
        """(distance, label) of the nearest obstacle within `cap`, or (cap, None)."""
        best, who = cap, None
        for k in {k for dx in range(-2, 3) for dz in range(-2, 3) for k in self.cells.get((math.floor(x / self.bucket) + dx, math.floor(z / self.bucket) + dz), ())}:
            d = self.items[k].distance(x, z)
            if d < best:
                best, who = d, self.items[k].label
        return best, who


def parse(stdout):
    props, cols, ext, hub = [], {}, {}, False
    for line in stdout.splitlines():
        f = line.split('\t')
        if f[0] == 'P':
            props.append(dict(layer=f[1], id=f[2], x=float(f[3]), y=float(f[4]), z=float(f[5]), yaw=float(f[6]), roll=float(f[7]), scale=float(f[8])))
        elif f[0] == 'C':
            cols.setdefault(f[1], []).append(tuple(float(v) for v in f[2:]))
        elif f[0] == 'E':
            ext[f[1]] = (f[2],) + tuple(float(v) for v in f[3:])
        elif f[0] == 'H':
            hub = f[1] == 'true'
    return props, cols, ext, hub


def dump(runner, profile='playtest'):
    """The placements, kit colliders and kit extents of the profile as the server would build them (one Luau run, a few seconds)."""
    text = (ROOT / 'src' / 'shared' / 'Config.luau').read_text(encoding='utf-8')
    cfg = release_profiles.apply_profile(text, profile)[0] if profile == 'playtest' else text
    old = est.DUMP
    est.DUMP = DUMP
    try:
        src = est.luau_script(cfg, profile == 'playtest')
    finally:
        est.DUMP = old
    # Arena.build() calls Biome.useHub(hub.biome) when the cave hub is on, before it places the kit props
    hub = 'local CaveHubLayout=' + est.vwa.wrapped('src/shared/CaveHubLayout.luau') + '\nlocal caveHub=CaveHubLayout.hub(Config)\nif caveHub.enabled then Biome.useHub(caveHub.biome) end\n'
    marker = 'local a=Biome.generate('
    assert marker in src, 'estimate_world_budget.luau_script changed: update world_colliders.dump'
    src = src.replace(marker, hub + marker, 1)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'colliders.luau'
        path.write_text(src, encoding='utf-8')
        res = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if res.returncode:
        raise SystemExit(res.stdout[-1500:] + res.stderr[-1500:])
    return parse(res.stdout)


def prop_obstacles(props, cols, ext):
    """Convex XZ footprints of every collider box of every placed prop (Arena.biomeKit / kitProp)."""
    items = []
    for p in props:
        rot = mul(ry(p['yaw']), rz(p['roll']))
        pivot = (p['x'], p['y'], p['z'])
        s = p['scale']
        label = '%s %s (%.1f, %.1f)' % (p['layer'], p['id'], p['x'], p['z'])
        if p['layer'] == 'log':
            c = cols[p['id']][0]
            size = (c[3] * s, ext[p['id']][2] * .9 * s, c[5] * s)
            items.append(Obstacle('box', box_footprint(pivot, rot, (0.0, ext[p['id']][2] * .45 * s, 0.0), size), label=label))
            continue
        for c in cols.get(p['id'], ()):
            items.append(Obstacle('box', box_footprint(pivot, rot, (c[0] * s, c[1] * s, c[2] * s), (c[3] * s, c[4] * s, c[5] * s), c[6]), label=label))
    return items


def arena_obstacles(cols):
    """The solid parts Arena.build() always adds (see the constants above)."""
    items = []
    # ring of boundary boulders: positions are fixed, scale and yaw are random -> a disc of the farthest collider reach at the largest scale
    reach = max(math.hypot(c[0], c[2]) + .5 * math.hypot(c[3], c[5]) for i in RING_IDS for c in cols[i])
    for side in range(4):
        for i in range(RING_SLOTS + 1):
            t = -ARENA_HALF + i * ARENA_HALF * 2 / RING_SLOTS
            pos = [(t, -ARENA_HALF - RING_OFFSET), (t, ARENA_HALF + RING_OFFSET), (-ARENA_HALF - RING_OFFSET, t), (ARENA_HALF + RING_OFFSET, t)][side]
            items.append(Obstacle('disc', centre=pos, radius=reach * RING_MAX_SCALE, label='boundary boulder (%.0f, %.0f)' % pos))
    for x in (-96 * SCALE, -64 * SCALE):
        items.append(Obstacle('box', [(x - ARCH_PILLAR[0] / 2, ARCH_Z - ARCH_PILLAR[2] / 2), (x + ARCH_PILLAR[0] / 2, ARCH_Z - ARCH_PILLAR[2] / 2),
                                       (x + ARCH_PILLAR[0] / 2, ARCH_Z + ARCH_PILLAR[2] / 2), (x - ARCH_PILLAR[0] / 2, ARCH_Z + ARCH_PILLAR[2] / 2)], label='arch pillar'))
    x = -80 * SCALE
    items.append(Obstacle('box', [(x - ARCH_TOP[0] / 2, ARCH_Z - ARCH_TOP[2] / 2), (x + ARCH_TOP[0] / 2, ARCH_Z - ARCH_TOP[2] / 2),
                                   (x + ARCH_TOP[0] / 2, ARCH_Z + ARCH_TOP[2] / 2), (x - ARCH_TOP[0] / 2, ARCH_Z + ARCH_TOP[2] / 2)], label='arch lintel'))
    for i in range(1, 5):
        x, z, h = 30 + i * 10, -30, JUMP_STONE_SIZE / 2
        items.append(Obstacle('box', [(x - h, z - h), (x + h, z - h), (x + h, z + h), (x - h, z + h)], label='jump stone'))
    return items


_CACHE = {}


def load(runner, profile='playtest'):
    """Obstacles for the profile (cached per process)."""
    key = (str(runner), profile)
    if key not in _CACHE:
        props, cols, ext, hub = dump(runner, profile)
        items = prop_obstacles(props, cols, ext) + arena_obstacles(cols)
        _CACHE[key] = Obstacles(items)
        _CACHE[key].summary = {'props': len(props), 'obstacles': len(items), 'cave_hub': hub}
    return _CACHE[key]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    ap.add_argument('--foods', help='text file, one "x z" or "kind x y z" per line: print the distance to the nearest collider')
    args = ap.parse_args()
    obs = load(args.runner)
    print('%(props)d placed props -> %(obstacles)d solid footprints (cave hub rectangle: %(cave_hub)s)' % obs.summary)
    if args.foods:
        for line in Path(args.foods).read_text().splitlines():
            f = line.split()
            if len(f) >= 4:
                x, z = float(f[1]), float(f[3])
            elif len(f) >= 2:
                x, z = float(f[0]), float(f[1])
            else:
                continue
            d, who = obs.nearest(x, z, 6.0)
            print('%8.1f %8.1f  %s' % (x, z, ('%.2f studs from %s' % (d, who)) if who else 'clear (> 6 studs)'))


if __name__ == '__main__':
    main()
