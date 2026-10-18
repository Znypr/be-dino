#!/usr/bin/env python3
"""BD-1047 (docs/187 B): make the DESIGNED FOOD MAP, a WorldLayer of food kinds, by rules instead of dice.

Today (FoodService without Config.FoodLayerEnabled) the food comes from 400 jittered cluster centres with 9 foods each: bundles about
2 studs apart with ~40 studs of nothing between them. This generator writes the map FoodService reads when the flag is on:

  * the same totals as today (3,600 foods; kind mix berry 70 / fruit 20 / egg 7 / amber 3 percent, starter patches included:
    berry 2519, fruit 722, egg 251, amber 108);
  * blue-noise placement (best-candidate sampling): no two foods closer than MIN_SPACING studs, no big gaps;
  * gentle extra density near the run start (0, 30) and the Home exit, and two designed hot spots: a FRUIT GROVE and an EGG MEADOW;
  * a lone amber on each of the four mountain tops (high ground to climb to), the other ambers and the eggs spread so that the walk to
    the next one stays short everywhere (cover selection on a lattice of ground spots);
  * the two starter patches next to the run start kept: nine foods each around (-15, 24) and (15, 24), two berries to one fruit;
  * nothing in water, in the safe-spawn disc or on steep ground: the same ground rule as FoodService.groundAt (tools/dump_food_layout.py
    evaluates it with the real Config and IslandLayout in the pinned Luau runner), pulled in one stud from every edge;
  * 1,000 x 1,000 cells over the arena (about 0.83 stud per cell), every food in its own cell; deterministic from SEED.

Output (only with --write): src/shared/FoodLayerData.luau (the run-length text WorldLayer.encode makes, in a Luau long string) and
tools/food_layer_data.py (the same text for the Python tools). tools/verify_food_layer.py regenerates the map and fails when the
committed files differ, so a change of the terrain (IslandLayout) or of this file needs `--write` and a commit.

Usage:
  python tools/generate_food_layer.py --runner C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe            # build, print a summary, compare with the committed files
  python tools/generate_food_layer.py --runner ... --write                                                      # also (re)write the two data files
"""
from pathlib import Path
import argparse
import math
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import worldlayer  # noqa: E402

VERSION = 'bd1047-foodlayer-v1'
SEED = 20261018
ARENA = 416.0          # Config.ArenaHalfWidth
EXTENT = 408.0         # FoodService places inside +-(ArenaHalfWidth - 8)
WIDTH = 1000           # layer cells across the arena
MIN_SPACING = 7.0      # studs, hard rule between any two foods
CANDIDATES = 64        # best-candidate tries per food
KIND_IDS = {'berry': 1, 'fruit': 2, 'egg': 3, 'amber': 4}
KIND_NAMES = {v: k for k, v in KIND_IDS.items()}
# Same totals as today's expectation (3,582 random slots at 70/20/7/3 plus the 12 berries + 6 fruits of the starter patches), rounded to 3,600.
COUNTS = {'berry': 2519, 'fruit': 722, 'egg': 251, 'amber': 108}
TOTAL = sum(COUNTS.values())

SPAWN = (0.0, 30.0)                       # run start (IslandLayout.SpawnZ); the Home door opens onto it
STARTER_CENTRES = ((-15.0, 24.0), (15.0, 24.0))
STARTER_RADIUS = 14.0                     # must match FoodLayer.StarterRadius in src/shared/FoodLayer.luau
STARTER_FOODS = 9                         # per patch; every 3rd is a fruit, as in the old placement
LONE_AMBER_CLEAR = 18.0                   # no other food within this many studs of a hill-top amber
SPAWN_BOOST, SPAWN_RADIUS = 0.8, 90.0     # gentle extra density around the run start
# Designed hot spots: density boost (peak, in units of the base density) and the share of the food inside that gets the special kind.
ZONES = (
    {'name': 'fruit grove', 'x': -110.0, 'z': 150.0, 'r': 38.0, 'boost': 1.0, 'kind': 'fruit', 'share': 0.55},
    {'name': 'egg meadow', 'x': 215.0, 'z': 40.0, 'r': 45.0, 'boost': 0.8, 'kind': 'egg', 'share': 0.18},
)
LLOYD_ROUNDS = 4                          # smoothing rounds for the amber and egg spots
SAMPLE_STEP = 12.0                        # lattice of ground spots used to judge walking distances while choosing amber / egg spots
RIM_FREE = 330.0                          # hill tops are looked for inside +-RIM_FREE (the outer rim is a ramp, not a mountain)


# ------------------------------------------------------------------------------ ground
class Ground:
    """FoodService's ground rule on a 1-stud lattice, eroded by one stud so a food never sits on an edge."""

    def __init__(self, model):
        self.arena = model['arena']
        n = len(model['mask'])
        self.n = n
        self.cell = model['cell']
        raw = [bytearray(1 if c == '1' else 0 for c in row) for row in model['mask']]
        self.ok_cells = [bytearray(n) for _ in range(n)]
        for iz in range(1, n - 1):
            above, here, below, out = raw[iz - 1], raw[iz], raw[iz + 1], self.ok_cells[iz]
            for ix in range(1, n - 1):
                if (here[ix] and here[ix - 1] and here[ix + 1] and above[ix] and above[ix - 1] and above[ix + 1]
                        and below[ix] and below[ix - 1] and below[ix + 1]):
                    out[ix] = 1
        self.h_rows = model['height']
        self.hcell = model['hcell']
        self.walkable_cells = sum(sum(r) for r in self.ok_cells)

    def ok(self, x, z):
        if abs(x) > EXTENT or abs(z) > EXTENT:
            return False
        ix, iz = int((x + self.arena) / self.cell), int((z + self.arena) / self.cell)
        return 0 <= ix < self.n and 0 <= iz < self.n and self.ok_cells[iz][ix] == 1

    def height(self, x, z):
        m = len(self.h_rows)
        ix = min(m - 1, max(0, int((x + self.arena) / self.hcell)))
        iz = min(m - 1, max(0, int((z + self.arena) / self.hcell)))
        return self.h_rows[iz][ix]

    def share_in_disc(self, cx, cz, r, step=4.0):
        hit = tot = 0
        z = cz - r
        while z <= cz + r:
            x = cx - r
            while x <= cx + r:
                if (x - cx) ** 2 + (z - cz) ** 2 <= r * r:
                    tot += 1
                    hit += self.ok(x, z)
                x += step
            z += step
        return hit / tot if tot else 0.0

    def lattice(self, step=SAMPLE_STEP):
        out = []
        z = -EXTENT + step / 2
        while z < EXTENT:
            x = -EXTENT + step / 2
            while x < EXTENT:
                if self.ok(x, z):
                    out.append((x, z))
                x += step
            z += step
        return out


# ------------------------------------------------------------------------------ small helpers
class Hash:
    """Points in square buckets for 'is anything closer than d' questions."""

    def __init__(self, size=MIN_SPACING * 2):
        self.size = size
        self.cells = {}

    def add(self, x, z):
        self.cells.setdefault((math.floor(x / self.size), math.floor(z / self.size)), []).append((x, z))

    def nearest(self, x, z, cap):
        """Distance to the nearest stored point, or `cap` when none is closer."""
        cx, cz = math.floor(x / self.size), math.floor(z / self.size)
        reach = int(cap // self.size) + 1
        best = cap * cap
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                for px, pz in self.cells.get((cx + dx, cz + dz), ()):
                    d = (px - x) ** 2 + (pz - z) ** 2
                    if d < best:
                        best = d
        return math.sqrt(best)


def snap(layer, x, z):
    """Centre of the layer cell that holds (x, z)."""
    return layer.centre_of(*layer.cell_of(x, z))


def density(x, z):
    """Relative food density at (x, z): 1 everywhere, more near the run start and in the hot spots (gentle, never zero)."""
    d = 1.0
    r = math.hypot(x - SPAWN[0], z - SPAWN[1]) / SPAWN_RADIUS
    d += SPAWN_BOOST * max(0.0, 1.0 - r * r)
    for zone in ZONES:
        r = math.hypot(x - zone['x'], z - zone['z']) / zone['r']
        d += zone['boost'] * max(0.0, 1.0 - r * r)
    return d


def in_zone(zone, x, z):
    return (x - zone['x']) ** 2 + (z - zone['z']) ** 2 <= zone['r'] ** 2


# ------------------------------------------------------------------------------ fixed foods
def starter_patch(ground, layer, centre):
    """Nine ground sites of a hexagonal lattice (spacing MIN_SPACING) close to `centre`: the starter patch. Several lattice turns and shifts
    are tried (the safe-spawn disc cuts into the patch on the spawn side) and the one with the nine nearest sites wins."""
    best = None
    for turn in range(0, 60, 6):
        c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
        for oa in (0.0, 0.25, 0.5, 0.75):
            for ob in (0.0, 0.25, 0.5, 0.75):
                sites = []
                for a in range(-5, 6):
                    for b in range(-5, 6):
                        u, v = MIN_SPACING * (a + oa + (b + ob) / 2), MIN_SPACING * (b + ob) * math.sqrt(3) / 2
                        x, z = snap(layer, centre[0] + u * c - v * s, centre[1] + u * s + v * c)
                        d = math.hypot(x - centre[0], z - centre[1])
                        if d <= STARTER_RADIUS - 0.5 and ground.ok(x, z):
                            sites.append((d, x, z))
                sites.sort()
                if len(sites) >= STARTER_FOODS:
                    score = sum(d for d, _, _ in sites[:STARTER_FOODS])
                    if best is None or score < best[0]:
                        best = (score, [(x, z) for _, x, z in sites[:STARTER_FOODS]])
    if best is None:
        raise SystemExit('starter patch near %s: not enough ground sites' % (centre,))
    return best[1]


def hill_tops(ground, layer, count=4, apart=120.0):
    """The highest ground spots inside +-RIM_FREE, at least `apart` studs from each other: where the lone ambers sit."""
    cands = []
    m = len(ground.h_rows)
    for iz in range(m):
        for ix in range(m):
            x, z = -ground.arena + (ix + 0.5) * ground.hcell, -ground.arena + (iz + 0.5) * ground.hcell
            if abs(x) <= RIM_FREE and abs(z) <= RIM_FREE:
                cands.append((ground.h_rows[iz][ix], x, z))
    cands.sort(reverse=True)
    tops, summits = [], []
    for _, ox, oz in cands:
        # non-maximum suppression: a spot within 48 studs of a higher summit is a slope, not a top
        if any(math.hypot(ox - sx, oz - sz) <= 48.0 for sx, sz in summits):
            continue
        summits.append((ox, oz))
        x, z = snap(layer, ox, oz)
        if not ground.ok(x, z) or ground.share_in_disc(x, z, 4.0, 2.0) < 1.0:
            continue
        if all(math.hypot(x - tx, z - tz) >= apart for tx, tz in tops):
            tops.append((x, z))
            if len(tops) == count:
                break
    return tops


# ------------------------------------------------------------------------------ placement
def place_points(ground, layer, rng, fixed):
    """Best-candidate blue noise: every new food is the best of CANDIDATES tries, scored by the distance to its nearest neighbour times the
    square root of the local density, never closer than MIN_SPACING to another food. `fixed` foods (starter patches, lone ambers) go in first."""
    keep_out = [(c[0], c[1], STARTER_RADIUS) for c in STARTER_CENTRES]
    keep_out += [(x, z, LONE_AMBER_CLEAR) for x, z in fixed['lone']]
    pts = list(fixed['starter']) + list(fixed['lone'])
    hashed = Hash()
    for x, z in pts:
        hashed.add(x, z)
    reach = MIN_SPACING * 5
    tries = 0
    while len(pts) < TOTAL:
        best, best_score = None, -1.0
        for _ in range(CANDIDATES):
            tries += 1
            x, z = snap(layer, rng.uniform(-EXTENT, EXTENT), rng.uniform(-EXTENT, EXTENT))
            if not ground.ok(x, z):
                continue
            if any((x - kx) ** 2 + (z - kz) ** 2 < kr * kr for kx, kz, kr in keep_out):
                continue
            d = hashed.nearest(x, z, reach)
            if d < MIN_SPACING:
                continue
            score = d * math.sqrt(density(x, z))
            if score > best_score:
                best, best_score = (x, z), score
        if best is None:
            if tries > 50_000_000:
                raise SystemExit('could not place %d foods with spacing %.1f' % (TOTAL, MIN_SPACING))
            continue
        pts.append(best)
        hashed.add(*best)
    return pts


# ------------------------------------------------------------------------------ kinds
def cover_select(points, allowed, samples, count, taken, rng=None):
    """Choose `count` of the `allowed` point indexes so the walk from any ground sample to the nearest chosen point is short:
    repeatedly take the sample farthest from every chosen point (and from `taken`, foods of this kind already placed) and choose
    the allowed food nearest to it. With `rng` the farthest sample is picked at random from the farthest tenth (a looser, natural spread)."""
    dist = [math.inf] * len(samples)
    for tx, tz in taken:
        for i, (sx, sz) in enumerate(samples):
            d = (sx - tx) ** 2 + (sz - tz) ** 2
            if d < dist[i]:
                dist[i] = d
    left = list(allowed)
    chosen = []
    for _ in range(count):
        if not left:
            break
        if rng is None:
            far = max(range(len(samples)), key=dist.__getitem__)
        else:
            order = sorted(range(len(samples)), key=dist.__getitem__, reverse=True)
            far = order[rng.randrange(max(1, len(order) // 10))]
        sx, sz = samples[far]
        pick = min(left, key=lambda i: (points[i][0] - sx) ** 2 + (points[i][1] - sz) ** 2)
        left.remove(pick)
        chosen.append(pick)
        px, pz = points[pick]
        for i, (qx, qz) in enumerate(samples):
            d = (qx - px) ** 2 + (qz - pz) ** 2
            if d < dist[i]:
                dist[i] = d
    return chosen


def lloyd(points, allowed, samples, chosen, fixed_xy, rounds):
    """Even out a cover selection: move every chosen food to the allowed food nearest to the middle of the ground spots it serves
    (the spots whose nearest chosen/fixed food it is). A few rounds shorten the worst walk without changing how many are chosen."""
    chosen = list(chosen)
    for _ in range(rounds):
        sites = [points[i] for i in chosen] + list(fixed_xy)
        sums = [[0.0, 0.0, 0] for _ in chosen]
        for sx, sz in samples:
            best, best_d = -1, math.inf
            for k, (px, pz) in enumerate(sites):
                d = (px - sx) ** 2 + (pz - sz) ** 2
                if d < best_d:
                    best, best_d = k, d
            if best < len(chosen):
                acc = sums[best]
                acc[0] += sx
                acc[1] += sz
                acc[2] += 1
        used = set(chosen)
        for k in range(len(chosen)):
            if sums[k][2] == 0:
                continue
            cx, cz = sums[k][0] / sums[k][2], sums[k][1] / sums[k][2]
            pick = min((i for i in allowed if i == chosen[k] or i not in used),
                       key=lambda i: (points[i][0] - cx) ** 2 + (points[i][1] - cz) ** 2)
            if pick != chosen[k]:
                used.discard(chosen[k])
                used.add(pick)
                chosen[k] = pick
    return chosen


def poisson_pick(points, allowed, count, taken, rng, radius):
    """Random foods that keep `radius` studs from each other (and from `taken`); relaxes the radius until `count` are found."""
    pool = list(allowed)
    chosen = []
    while len(chosen) < count and radius > 0:
        hashed = Hash(max(radius, 4.0))
        for x, z in taken:
            hashed.add(x, z)
        for i in chosen:
            hashed.add(*points[i])
        rng.shuffle(pool)
        rest = []
        for i in pool:
            if len(chosen) < count and hashed.nearest(points[i][0], points[i][1], radius) >= radius:
                chosen.append(i)
                hashed.add(*points[i])
            else:
                rest.append(i)
        pool = rest
        radius -= 4.0
    return chosen


def assign_kinds(ground, points, fixed_kinds, rng):
    """kinds[i] for every point: fixed ones keep theirs, then ambers, the egg meadow, eggs, the fruit grove, fruit, and berries for the rest."""
    kinds = dict(fixed_kinds)
    free = [i for i in range(len(points)) if i not in kinds]
    samples = ground.lattice()
    xy = lambda idx: [points[i] for i in idx]  # noqa: E731

    def take(kind, chosen):
        for i in chosen:
            kinds[i] = kind
        return [i for i in free if i not in kinds]

    # ambers: the 4 lone hill-top ones are fixed; the rest cover the ground evenly
    have = [i for i, k in kinds.items() if k == 'amber']
    ambers = cover_select(points, free, samples, COUNTS['amber'] - len(have), xy(have))
    free = take('amber', lloyd(points, free, samples, ambers, xy(have), LLOYD_ROUNDS))
    # egg meadow first (its eggs count toward the total), then the eggs everywhere
    meadow = next(z for z in ZONES if z['kind'] == 'egg')
    inside = [i for i in free if in_zone(meadow, *points[i])]
    want = round(meadow['share'] * len([i for i in range(len(points)) if in_zone(meadow, *points[i])]))
    free = take('egg', cover_select(points, inside, samples, want, []))
    have = [i for i, k in kinds.items() if k == 'egg']
    eggs = cover_select(points, free, samples, COUNTS['egg'] - len(have), xy(have))
    free = take('egg', lloyd(points, free, samples, eggs, xy(have), LLOYD_ROUNDS))
    # fruit grove, then fruit everywhere (loose natural spread)
    grove = next(z for z in ZONES if z['kind'] == 'fruit')
    inside = [i for i in free if in_zone(grove, *points[i])]
    want = round(grove['share'] * len([i for i in range(len(points)) if in_zone(grove, *points[i])]))
    free = take('fruit', poisson_pick(points, inside, want, [], rng, 12.0))
    have = [i for i, k in kinds.items() if k == 'fruit']
    free = take('fruit', poisson_pick(points, free, COUNTS['fruit'] - len(have), xy(have), rng, 24.0))
    take('berry', free)
    return kinds


# ------------------------------------------------------------------------------ whole map
def generate(ground_model):
    """Returns {"layer": WorldLayer, "points": [(x, z, kind name)], "tops": [...], "meta": {...}} for a ground model (dump_food_layout.ground_model)."""
    ground = Ground(ground_model)
    layer = worldlayer.WorldLayer(WIDTH, WIDTH, ARENA)
    rng = random.Random(SEED)
    for zone in ZONES:
        share = ground.share_in_disc(zone['x'], zone['z'], zone['r'])
        if share < 0.9:
            raise SystemExit('hot spot %s is only %.0f%% ground, move it' % (zone['name'], share * 100))
    starter, fixed_kinds = [], {}
    for centre in STARTER_CENTRES:
        for n, site in enumerate(starter_patch(ground, layer, centre)):
            fixed_kinds[len(starter)] = 'fruit' if (n + 1) % 3 == 0 else 'berry'
            starter.append(site)
    tops = hill_tops(ground, layer)
    for k in range(len(tops)):
        fixed_kinds[len(starter) + k] = 'amber'
    pts = place_points(ground, layer, rng, {'starter': starter, 'lone': tops})
    kinds = assign_kinds(ground, pts, fixed_kinds, rng)
    out = []
    for i, (x, z) in enumerate(pts):
        kind = kinds[i]
        if not layer.set(x, z, KIND_IDS[kind]):
            raise SystemExit('food outside the layer: %r' % ((x, z),))
        out.append((x, z, kind))
    if layer.count() != TOTAL:
        raise SystemExit('two foods share a cell: %d cells for %d foods' % (layer.count(), TOTAL))
    counts = {k: sum(1 for p in out if p[2] == k) for k in COUNTS}
    if counts != COUNTS:
        raise SystemExit('kind counts %r differ from the plan %r' % (counts, COUNTS))
    meta = {'version': VERSION, 'seed': SEED, 'min_spacing': MIN_SPACING, 'counts': counts, 'total': TOTAL,
            'zones': [(z['name'], z['x'], z['z'], z['r']) for z in ZONES], 'lone_ambers': [(round(x, 1), round(z, 1)) for x, z in tops]}
    return {'layer': layer, 'points': out, 'tops': tops, 'meta': meta, 'ground': ground}


# ------------------------------------------------------------------------------ files
LUAU_PATH = ROOT / 'src' / 'shared' / 'FoodLayerData.luau'
PY_PATH = ROOT / 'tools' / 'food_layer_data.py'


def wrap(text, width=110):
    return '\n'.join(text[i:i + width] for i in range(0, len(text), width))


def luau_source(result):
    meta = result['meta']
    return ('--!strict\n'
            '-- GENERATED by tools/generate_food_layer.py (BD-1047, docs/187 B). Do not edit by hand: change the generator, run it with --write and commit both outputs.\n'
            '-- The designed food map: a WorldLayer (src/shared/WorldLayer.luau) over the arena, %d x %d cells, every cell 0 (none) or a food kind 1 berry, 2 fruit, 3 egg, 4 amber.\n'
            '-- %d foods: %s. Seed %d, minimum spacing %g studs. Read by src/shared/FoodLayer.luau; only used while Config.FoodLayerEnabled is true.\n'
            'return table.freeze({\n'
            '    Version = "%s",\n'
            '    Map = [==[\n%s\n]==],\n'
            '})\n') % (WIDTH, WIDTH, meta['total'], ', '.join('%s %d' % (k, v) for k, v in meta['counts'].items()), meta['seed'],
                       meta['min_spacing'], VERSION, wrap(result['layer'].encode()))


def python_source(result):
    meta = result['meta']
    return ('"""GENERATED by tools/generate_food_layer.py (BD-1047). Do not edit by hand. The same map as src/shared/FoodLayerData.luau for the Python tools."""\n'
            'VERSION = %r\nSEED = %d\nMIN_SPACING = %r\nCOUNTS = %r\nTEXT = (\n%s\n)\n') % (
        VERSION, meta['seed'], meta['min_spacing'], meta['counts'],
        '\n'.join('    %r' % result['layer'].encode()[i:i + 110] for i in range(0, len(result['layer'].encode()), 110)))


def committed_text():
    """The map text in the committed Luau module (whitespace removed), or None."""
    import re
    if not LUAU_PATH.exists():
        return None
    m = re.search(r'Map = \[==\[(.*?)\]==\]', LUAU_PATH.read_text(encoding='utf-8'), re.S)
    return re.sub(r'\s', '', m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    ap.add_argument('--write', action='store_true', help='write src/shared/FoodLayerData.luau and tools/food_layer_data.py')
    args = ap.parse_args()
    import dump_food_layout
    result = generate(dump_food_layout.ground_model(args.runner, 1.0, 4.0))
    text = result['layer'].encode()
    print('%d foods %s, %d characters of text, lone ambers at %s' % (result['meta']['total'], result['meta']['counts'], len(text), result['meta']['lone_ambers']))
    old = committed_text()
    print('committed map: %s' % ('missing' if old is None else ('identical' if old == text else 'DIFFERENT')))
    if args.write:
        LUAU_PATH.write_text(luau_source(result), encoding='utf-8', newline='\n')
        PY_PATH.write_text(python_source(result), encoding='utf-8', newline='\n')
        print('wrote', LUAU_PATH.relative_to(ROOT), 'and', PY_PATH.relative_to(ROOT))
    return 0 if (old == text or args.write) else 1


if __name__ == '__main__':
    sys.exit(main())
