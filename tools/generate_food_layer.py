#!/usr/bin/env python3
"""BD-1047 (docs/187 B): make the DESIGNED FOOD MAP, a WorldLayer of food kinds, by rules instead of dice.

Today (FoodService without Config.FoodLayerEnabled) the food comes from 400 jittered cluster centres with 9 foods each: bundles about
2 studs apart with ~40 studs of nothing between them (and 115 patches farther than 25 studs from any food). This generator writes the map FoodService reads when the flag is on:

  * the same totals as today (3,600 foods; kind mix berry 70 / fruit 20 / egg 7 / amber 3 percent, starter patches included:
    berry 2519, fruit 722, egg 251, amber 108);
  * SMALL CLUSTERS of 3 to 5 foods 3 to 3.5 studs apart (like today's bundles of 9, but smaller: a food-seeking player still gets several
    pieces per stop, so the food pace stays about the same), cluster centres on a blue-noise grid (best-candidate sampling, at least
    CLUSTER_SPACING studs apart, foods of different clusters at least BETWEEN_SPACING apart); afterwards clusters are moved so no ground
    spot (rim included) is far from food and no 32-stud block is empty;
  * every amber cluster also holds one egg and one fruit (rich stops, like today's rich bundles);
  * gentle extra density near the run start (0, 30) and the Home exit, and two designed hot spots: a FRUIT GROVE and an EGG MEADOW;
  * a lone amber on each of the four mountain tops (high ground to climb to), the other ambers and the eggs spread so that the walk to
    the next one stays short everywhere (cover selection on a lattice of ground spots);
  * the two starter patches next to the run start kept: nine foods each around (-15, 24) and (15, 24), two berries to one fruit;
  * nothing in water, in the safe-spawn disc or on steep ground: the same ground rule as FoodService.groundAt (tools/dump_food_layout.py
    evaluates it with the real Config and IslandLayout in the pinned Luau runner), pulled in one stud from every edge;
  * BD-1098: no food inside or next to a solid world prop. The colliders the server builds (rocks, trunks, logs, landmarks, the arch, the boundary
    boulders) come from tools/world_colliders.py (the real BiomePlacement grammar run in the Luau runner); the last stage of generate() moves every
    food closer than OBSTACLE_MARGIN studs to one of them to the nearest free cell of its own cluster (see clear_obstacles), so nothing else moves;
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

VERSION = 'bd1098-foodlayer-v3'
SEED = 103            # picked from seeds 101 to 112 (the best balance of pace, gaps and spread; see docs/187 s G)
ARENA = 416.0          # Config.ArenaHalfWidth
EXTENT = 408.0         # FoodService places inside +-(ArenaHalfWidth - 8)
WIDTH = 1000           # layer cells across the arena
# Small clusters of 3 to 5 foods (SIZE_WEIGHTS): a food-seeking player still gets several pieces per stop, like today's bundles of 9
CLUSTER_FOOD_SPACING = (3.0, 3.5)   # studs between neighbours inside a cluster
MIN_SPACING = 2.8      # studs, hard rule between two foods of one cluster (and the starter patches)
BETWEEN_SPACING = 6.0  # studs, hard rule between foods of different clusters
CLUSTER_SPACING = 14.0 # studs, minimum distance between cluster centres (blue noise between clusters)
CANDIDATES = 64        # best-candidate tries per cluster
SIZE_WEIGHTS = ((3, 0.05), (4, 0.25), (5, 0.7))   # share of clusters of 3, 4 and 5 foods
GAP_TARGET = 16.0      # studs: after placing, clusters are moved until no ground spot is farther than this from any food (the written rule is 25)
REPAIR_ROUNDS = 400   # most cluster moves tried while closing gaps
STARTER_SPACING = 3.6  # studs between starter patch foods
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
# BD-1098: clearance from solid props. FoodService.groundAt rejects a spot when a 1.25 stud ray along x or z (from 1 stud above the ground) hits a
# collider, and the Studio check counted a food as inside a box when its part (up to 0.87 stud from its middle) touched it: 1.5 covers both.
OBSTACLE_MARGIN = 1.5
MOVE_REACH = 7.0       # studs: farthest a single food is moved away from the spot the generator gave it
SHIFT_REACH = 14.0     # studs: farthest a whole cluster is shifted when single moves do not work
LINK_MAX = 4.8         # studs: a moved food stays this close to a mate (verify_food_layer links foods closer than 5.0 into one cluster)
CENTRE_MIN = 12.5      # studs: moved clusters keep their centres at least this far apart (written rule: 12)


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

    def ok(self, x, z, limit=EXTENT):
        if abs(x) > limit or abs(z) > limit:
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

    def lattice(self, step=SAMPLE_STEP, limit=EXTENT):
        """Ground spots every `step` studs inside +-limit (the repair step uses the whole arena, rim included)."""
        out = []
        z = -limit + step / 2
        while z < limit:
            x = -limit + step / 2
            while x < limit:
                if self.ok(x, z, limit):
                    out.append((x, z))
                x += step
            z += step
        return out


# ------------------------------------------------------------------------------ small helpers
class Hash:
    """Points in square buckets for 'is anything closer than d' questions."""

    def __init__(self, size=12.0):
        self.size = size
        self.cells = {}

    def add(self, x, z):
        self.cells.setdefault((math.floor(x / self.size), math.floor(z / self.size)), []).append((x, z))

    def remove(self, x, z):
        self.cells[(math.floor(x / self.size), math.floor(z / self.size))].remove((x, z))

    def nearest(self, x, z, cap, skip_self=False):
        """Distance to the nearest stored point (not the point at exactly (x, z) with skip_self), or `cap` when none is closer."""
        cx, cz = math.floor(x / self.size), math.floor(z / self.size)
        reach = int(cap // self.size) + 1
        best = cap * cap
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                for px, pz in self.cells.get((cx + dx, cz + dz), ()):
                    d = (px - x) ** 2 + (pz - z) ** 2
                    if d < best and not (skip_self and d == 0):
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
    """Nine ground sites of a hexagonal lattice (spacing STARTER_SPACING) close to `centre`: the starter patch. Several lattice turns and shifts
    are tried (the safe-spawn disc cuts into the patch on the spawn side) and the one with the nine nearest sites wins."""
    best = None
    for turn in range(0, 60, 6):
        c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))
        for oa in (0.0, 0.25, 0.5, 0.75):
            for ob in (0.0, 0.25, 0.5, 0.75):
                sites = []
                for a in range(-5, 6):
                    for b in range(-5, 6):
                        u, v = STARTER_SPACING * (a + oa + (b + ob) / 2), STARTER_SPACING * (b + ob) * math.sqrt(3) / 2
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
def cluster_sizes(count, rng):
    """Cluster sizes 3, 4 or 5 (SIZE_WEIGHTS) that add up to exactly `count` foods."""
    sizes, left = [], count
    while left > 0:
        options = [(n, w) for n, w in SIZE_WEIGHTS if left - n >= CLUSTER_MIN or left == n]
        if not options:
            sizes[rng.randrange(len(sizes))] += left  # (cannot happen for the planned counts)
            break
        pick = rng.random() * sum(w for _, w in options)
        for n, w in options:
            pick -= w
            if pick <= 0:
                break
        sizes.append(n)
        left -= n
    return sizes


CLUSTER_MIN = min(n for n, _ in SIZE_WEIGHTS)


def cluster_shape(n, rng):
    """Offsets of n foods 3.2 to 4 studs apart: a triangle, a square or a pentagon, turned and nudged a little."""
    spacing = rng.uniform(*CLUSTER_FOOD_SPACING)
    radius = spacing / (2 * math.sin(math.pi / n))
    turn = rng.uniform(0, 2 * math.pi)
    return [(radius * math.cos(turn + 2 * math.pi * k / n) + rng.uniform(-0.25, 0.25),
             radius * math.sin(turn + 2 * math.pi * k / n) + rng.uniform(-0.25, 0.25)) for k in range(n)]


class Placer:
    """Holds the foods and cluster centres placed so far and answers 'may a cluster of n foods go here'."""

    def __init__(self, ground, layer, rng, fixed):
        self.ground, self.layer, self.rng = ground, layer, rng
        self.keep_out = [(c[0], c[1], STARTER_RADIUS) for c in STARTER_CENTRES]
        self.keep_out += [(x, z, LONE_AMBER_CLEAR) for x, z in fixed['lone']]
        self.foods, self.centres = Hash(), Hash(CLUSTER_SPACING)
        for x, z in list(fixed['starter']) + list(fixed['lone']):
            self.foods.add(x, z)
        for centre in STARTER_CENTRES:
            self.centres.add(*centre)
        for x, z in fixed['lone']:
            self.centres.add(x, z)

    def shape_at(self, cx, cz, n):
        """The n food positions of a cluster centred at (cx, cz), or None when a rule is broken (ground, spacing, keep-out zones)."""
        layer, ground = self.layer, self.ground
        if self.centres.nearest(cx, cz, CLUSTER_SPACING) < CLUSTER_SPACING or not ground.ok(*snap(layer, cx, cz)):
            return None
        shape = [snap(layer, cx + ox, cz + oz) for ox, oz in cluster_shape(n, self.rng)]
        if len({layer.cell_of(*p) for p in shape}) != n:
            return None
        for x, z in shape:
            if not ground.ok(x, z) or any((x - kx) ** 2 + (z - kz) ** 2 < kr * kr for kx, kz, kr in self.keep_out):
                return None
            if self.foods.nearest(x, z, BETWEEN_SPACING) < BETWEEN_SPACING:
                return None
        if any(math.hypot(a[0] - b[0], a[1] - b[1]) < MIN_SPACING for i, a in enumerate(shape) for b in shape[i + 1:]):
            return None
        return shape

    def add(self, cluster):
        self.centres.add(*cluster['centre'])
        for x, z in cluster['shape']:
            self.foods.add(x, z)

    def remove(self, cluster):
        self.centres.remove(*cluster['centre'])
        for x, z in cluster['shape']:
            self.foods.remove(x, z)


def repair_gaps(placer, clusters, samples, rng, rounds=None):
    """Move clusters so no ground spot is farther than GAP_TARGET from any food: take the spot farthest from every food, lift away the most
    crowded cluster (the one with the closest neighbouring centre, among a few tries) and put one there. A move that would open a bigger gap
    where the cluster was, or that cannot be placed, is undone."""
    cap = GAP_TARGET + 16.0

    def near(x, z):
        return placer.foods.nearest(x, z, cap)

    buckets = {}
    for i, (sx, sz) in enumerate(samples):
        buckets.setdefault((int(sx // 40), int(sz // 40)), []).append(i)

    def around(x, z):
        """Indexes of the samples within `cap` studs (a square) of (x, z)."""
        bx, bz = int(x // 40), int(z // 40)
        return [i for dx in (-1, 0, 1) for dz in (-1, 0, 1) for i in buckets.get((bx + dx, bz + dz), ())
                if abs(samples[i][0] - x) < cap and abs(samples[i][1] - z) < cap]

    dist = [near(sx, sz) for sx, sz in samples]
    skipped = set()
    for _ in range(rounds or REPAIR_ROUNDS):
        far = max((i for i in range(len(samples)) if i not in skipped), key=dist.__getitem__, default=None)
        if far is None or dist[far] <= GAP_TARGET:
            break
        tx, tz = samples[far]
        movable = rng.sample(range(len(clusters)), min(80, len(clusters)))
        movable.sort(key=lambda k: placer.centres.nearest(*clusters[k]['centre'], 40.0, skip_self=True))
        done = False
        for k in movable[:12]:
            old = clusters[k]
            ox, oz = old['centre']
            if math.hypot(ox - tx, oz - tz) < 2 * GAP_TARGET:
                continue
            placer.remove(old)
            area = around(ox, oz)
            after = {i: near(*samples[i]) for i in area}
            if max(after.values(), default=0.0) >= 0.97 * dist[far]:  # the hole left behind must stay clearly smaller than the one being closed
                placer.add(old)
                continue
            new = None
            for _ in range(40):
                cx, cz = tx + rng.uniform(-10, 10), tz + rng.uniform(-10, 10)
                shape = placer.shape_at(cx, cz, len(old['shape']))
                if shape:
                    new = {'centre': (cx, cz), 'shape': shape}
                    break
            if new is None:
                placer.add(old)
                continue
            placer.add(new)
            clusters[k] = new
            for i in set(area) | set(around(tx, tz)):
                dist[i] = near(*samples[i])
            done = True
            break
        if not done:
            skipped.add(far)
    return clusters


BLOCK = 10 * 2 * ARENA / 256   # studs: the small block of tools/layer_stats.py (10 cells of a 256-cell grid, 32.5 studs)


def fix_empty_blocks(placer, clusters, rng):
    """No empty small block: every block of BLOCK studs that is mostly ground gets a cluster. A cluster is taken from the most crowded block
    nearby (one with at least 12 foods) and put inside the empty one; a move that cannot be placed is undone."""
    ground = placer.ground
    n = int(2 * ARENA / BLOCK)

    def block_of(x, z):
        return int((x + ARENA) / BLOCK), int((z + ARENA) / BLOCK)

    for _ in range(6):
        counts = {}
        for k, cluster in enumerate(clusters):
            for x, z in cluster['shape']:
                counts.setdefault(block_of(x, z), []).append(k)
        moved = False
        for bz in range(n):
            for bx in range(n):
                if counts.get((bx, bz)):
                    continue
                x0, z0 = -ARENA + bx * BLOCK, -ARENA + bz * BLOCK
                spots = [(x0 + (i + 0.5) * BLOCK / 8, z0 + (j + 0.5) * BLOCK / 8) for i in range(8) for j in range(8)]
                if sum(1 for sx, sz in spots if ground.ok(sx, sz)) < 32:
                    continue  # mostly water or cliff: not counted by the tool either
                donors = sorted({k for key, ks in counts.items() if len(ks) * 4 >= 12 for k in ks},
                                key=lambda k: math.hypot(clusters[k]['centre'][0] - x0, clusters[k]['centre'][1] - z0))
                for k in donors[:8]:
                    old = clusters[k]
                    placer.remove(old)
                    new = None
                    for _ in range(80):
                        cx, cz = x0 + rng.uniform(4, BLOCK - 4), z0 + rng.uniform(4, BLOCK - 4)
                        shape = placer.shape_at(cx, cz, len(old['shape']))
                        if shape and any(block_of(x, z) == (bx, bz) for x, z in shape):
                            new = {'centre': (cx, cz), 'shape': shape}
                            break
                    if new is None:
                        placer.add(old)
                        continue
                    placer.add(new)
                    clusters[k] = new
                    moved = True
                    break
        if not moved:
            break
    return clusters


def place_points(ground, layer, rng, fixed):
    """Small clusters on a blue-noise grid of centres: every new cluster is the best of CANDIDATES tries, scored by the distance to its nearest
    cluster centre times the square root of the local density, never closer than CLUSTER_SPACING to another centre and never with a food closer
    than BETWEEN_SPACING to another cluster's food; then repair_gaps closes any hole. `fixed` foods (starter patches, lone ambers) go in first.
    Returns (points, cluster id per point; -1 for the fixed foods)."""
    placer = Placer(ground, layer, rng, fixed)
    pts = list(fixed['starter']) + list(fixed['lone'])
    clusters = []
    reach = CLUSTER_SPACING * 4
    tries = 0
    for n in cluster_sizes(TOTAL - len(pts), rng):
        while True:
            best, best_score = None, -1.0
            for _ in range(CANDIDATES):
                tries += 1
                cx, cz = rng.uniform(-EXTENT, EXTENT), rng.uniform(-EXTENT, EXTENT)
                shape = placer.shape_at(cx, cz, n)
                if shape is None:
                    continue
                score = placer.centres.nearest(cx, cz, reach) * math.sqrt(density(cx, cz))
                if score > best_score:
                    best, best_score = {'centre': (cx, cz), 'shape': shape}, score
            if best is not None:
                break
            if tries > 50_000_000:
                raise SystemExit('could not place the clusters with spacing %.1f' % CLUSTER_SPACING)
        placer.add(best)
        clusters.append(best)
    clusters = repair_gaps(placer, clusters, ground.lattice(8.0, ARENA - 2.0), rng)
    clusters = fix_empty_blocks(placer, clusters, rng)
    clusters = repair_gaps(placer, clusters, ground.lattice(8.0, ARENA - 2.0), rng, 200)
    cid = [-1] * len(pts)
    for k, cluster in enumerate(clusters):
        for x, z in cluster['shape']:
            pts.append((x, z))
            cid.append(k)
    return pts, cid


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


def assign_kinds(ground, points, fixed_kinds, rng, cid):
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
    # every amber cluster also holds an egg and a fruit, like the rich bundles of today: a stop at an amber is worth a detour
    for i in [i for i, k in kinds.items() if k == 'amber' and cid[i] >= 0]:
        mates = [j for j in free if cid[j] == cid[i]]
        for kind in ('egg', 'fruit'):
            if mates:
                free = take(kind, [mates.pop(rng.randrange(len(mates)))])
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


# ------------------------------------------------------------------------------ BD-1098: keep clear of solid props
def clear_obstacles(pts, cid, n_starter, n_lone, ground, layer, obstacles):
    """Move every food closer than OBSTACLE_MARGIN studs to a solid world prop (tools/world_colliders.py) out of its way, changing as little as possible.

    The pipeline before this stage knows only the terrain, so its random choices stay exactly as they were; this last stage then takes each blocked
    food and puts it on the nearest free cell (at most MOVE_REACH studs away, nearest first) that keeps every rule of the map: valid ground, its own
    cell, MIN_SPACING to its cluster mates, BETWEEN_SPACING to other clusters, LONE_AMBER_CLEAR around a hill-top amber, within the starter radius for
    a starter patch, and still linked to its cluster (so groups stay 3 to 5 and connected) with the cluster centres still CENTRE_MIN apart. A cluster
    in which some food has no such cell is shifted as a whole (up to SHIFT_REACH studs). Kinds are by index, so a moved egg is still an egg.
    Returns (new points, [(index, old, new)])."""
    pos = list(pts)
    groups = []
    for i, (x, z) in enumerate(pos):
        if i < n_starter:
            groups.append(('s', min(range(len(STARTER_CENTRES)), key=lambda k: math.hypot(x - STARTER_CENTRES[k][0], z - STARTER_CENTRES[k][1]))))
        elif i < n_starter + n_lone:
            groups.append(('l', i))
        else:
            groups.append(('c', cid[i]))
    size = 8.0
    buckets, taken, members = {}, {}, {}

    def key(x, z):
        return math.floor(x / size), math.floor(z / size)

    for i, (x, z) in enumerate(pos):
        buckets.setdefault(key(x, z), set()).add(i)
        taken[layer.cell_of(x, z)] = i
        members.setdefault(groups[i], []).append(i)

    def put(i, x, z):
        buckets[key(*pos[i])].discard(i)
        del taken[layer.cell_of(*pos[i])]
        pos[i] = (x, z)
        buckets.setdefault(key(x, z), set()).add(i)
        taken[layer.cell_of(x, z)] = i

    def near(x, z, r):
        k = key(x, z)
        reach = int(r // size) + 1
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                yield from buckets.get((k[0] + dx, k[1] + dz), ())

    def connected(g, override):
        """True when the foods of group g (positions overridden by {index: (x, z)}) form one group linked by gaps below LINK_MAX."""
        pts_g = [override.get(i, pos[i]) for i in members[g]]
        seen, todo = {0}, [0]
        while todo:
            a = pts_g[todo.pop()]
            for b in range(len(pts_g)):
                if b not in seen and math.hypot(a[0] - pts_g[b][0], a[1] - pts_g[b][1]) < LINK_MAX + 0.19:
                    seen.add(b)
                    todo.append(b)
        return len(seen) == len(pts_g)

    def centroid(g, override):
        ids = members[g]
        return (sum(override.get(i, pos[i])[0] for i in ids) / len(ids), sum(override.get(i, pos[i])[1] for i in ids) / len(ids))

    cluster_ids = [g for g in members if g[0] == 'c']

    def centres_ok(g, override):
        if g[0] != 'c':
            return True
        cx, cz = centroid(g, override)
        for h in cluster_ids:
            if h != g:
                hx, hz = centroid(h, {})
                if math.hypot(cx - hx, cz - hz) < CENTRE_MIN:
                    return False
        return True

    def spot_ok(i, x, z, ignore):
        """May food i stand at the cell centre (x, z) (the foods in `ignore` are being moved too and do not count)?"""
        if not ground.ok(x, z) or obstacles.distance(x, z, OBSTACLE_MARGIN) < OBSTACLE_MARGIN:
            return False
        holder = taken.get(layer.cell_of(x, z))
        if holder is not None and holder != i and holder not in ignore:
            return False
        g = groups[i]
        if g[0] == 's' and math.hypot(x - STARTER_CENTRES[g[1]][0], z - STARTER_CENTRES[g[1]][1]) > STARTER_RADIUS - 0.5:
            return False
        linked = g[0] == 'l'
        for j in near(x, z, LONE_AMBER_CLEAR + 1.0):
            if j == i or j in ignore:
                continue
            d = math.hypot(pos[j][0] - x, pos[j][1] - z)
            h = groups[j]
            need = LONE_AMBER_CLEAR if (g[0] == 'l' or h[0] == 'l') else (MIN_SPACING if h == g else BETWEEN_SPACING)
            if d < need:
                return False
            if h == g and d < LINK_MAX:
                linked = True
        return linked or bool(ignore)   # a whole-cluster shift checks the links of the moved group itself (connected)

    cell_w = 2 * ARENA / WIDTH

    def lattice(x, z, reach):
        """Every cell centre within `reach` studs of (x, z), nearest first."""
        ix, iz = layer.cell_of(x, z)
        n = int(reach / cell_w) + 1
        out = []
        for dz in range(-n, n + 1):
            for dx in range(-n, n + 1):
                if layer.contains(ix + dx, iz + dz):
                    cx, cz = layer.centre_of(ix + dx, iz + dz)
                    d = math.hypot(cx - x, cz - z)
                    if d <= reach:
                        out.append((d, cx, cz))
        out.sort()
        return out

    def blocked(i):
        return obstacles.distance(pos[i][0], pos[i][1], OBSTACLE_MARGIN) < OBSTACLE_MARGIN

    moved, stuck = {}, []
    for i in [i for i in range(len(pos)) if blocked(i)]:
        old = pos[i]
        g = groups[i]
        for _, cx, cz in lattice(old[0], old[1], MOVE_REACH):
            if not spot_ok(i, cx, cz, ()):
                continue
            if g[0] != 'l' and (not connected(g, {i: (cx, cz)}) or not centres_ok(g, {i: (cx, cz)})):
                continue
            put(i, cx, cz)
            moved[i] = (moved[i][0] if i in moved else old, (cx, cz))
            break
        else:
            stuck.append(i)
    for g in sorted({groups[i] for i in stuck}):
        if g[0] != 'c':
            first = [i for i in stuck if groups[i] == g][0]
            raise SystemExit('a %s food at %r cannot get clear of the solid props' % ('starter' if g[0] == 's' else 'hill-top amber', pos[first]))
        ids = members[g]
        ignore = set(ids)
        base = {i: pos[i] for i in ids}
        cx0, cz0 = centroid(g, {})
        for _, ox, oz in lattice(cx0, cz0, SHIFT_REACH):
            dx, dz = ox - cx0, oz - cz0
            to = {i: snap(layer, base[i][0] + dx, base[i][1] + dz) for i in ids}
            if len({layer.cell_of(*p) for p in to.values()}) != len(ids):
                continue
            if not all(spot_ok(i, to[i][0], to[i][1], ignore) for i in ids):
                continue
            if any(math.hypot(to[a][0] - to[b][0], to[a][1] - to[b][1]) < MIN_SPACING for a in ids for b in ids if a < b):
                continue
            if not connected(g, to) or not centres_ok(g, to):
                continue
            for i in ids:
                put(i, *to[i])
                moved[i] = (moved[i][0] if i in moved else base[i], to[i])
            break
        else:
            raise SystemExit('a cluster near (%.0f, %.0f) cannot get clear of the solid props' % (cx0, cz0))
    left = [i for i in range(len(pos)) if blocked(i)]
    if left:
        raise SystemExit('%d foods are still inside the clearance of a solid prop' % len(left))
    return pos, [(i, a, b) for i, (a, b) in sorted(moved.items()) if a != b]


# ------------------------------------------------------------------------------ whole map
def generate(ground_model, obstacles=None):
    """Returns {"layer": WorldLayer, "points": [(x, z, kind name)], "tops": [...], "meta": {...}} for a ground model (dump_food_layout.ground_model).
    `obstacles` (tools/world_colliders.Obstacles, BD-1098) keeps every food OBSTACLE_MARGIN studs clear of the solid props; None = terrain only."""
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
    pts, cid = place_points(ground, layer, rng, {'starter': starter, 'lone': tops})
    kinds = assign_kinds(ground, pts, fixed_kinds, rng, cid)
    moved = []
    if obstacles is not None:
        pts, moved = clear_obstacles(pts, cid, len(starter), len(tops), ground, layer, obstacles)
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
    meta = {'version': VERSION, 'seed': SEED, 'min_spacing': MIN_SPACING, 'between_spacing': BETWEEN_SPACING, 'cluster_spacing': CLUSTER_SPACING, 'counts': counts, 'total': TOTAL,
            'zones': [(z['name'], z['x'], z['z'], z['r']) for z in ZONES], 'lone_ambers': [(round(x, 1), round(z, 1)) for x, z in pts[len(starter):len(starter) + len(tops)]]}
    return {'layer': layer, 'points': out, 'tops': tops, 'meta': meta, 'ground': ground, 'moved': moved}


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
    import world_colliders
    obstacles = world_colliders.load(args.runner)
    print('solid props: %(props)d placed props -> %(obstacles)d footprints; foods keep %(margin)g studs clear' % dict(obstacles.summary, margin=OBSTACLE_MARGIN))
    result = generate(dump_food_layout.ground_model(args.runner, 1.0, 4.0), obstacles)
    text = result['layer'].encode()
    far = max((math.hypot(b[0] - a[0], b[1] - a[1]) for _, a, b in result['moved']), default=0.0)
    print('%d foods moved out of the way of solid props (farthest move %.1f studs)' % (len(result['moved']), far))
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
