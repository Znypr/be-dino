#!/usr/bin/env python3
"""BD-1049 (docs/187 s A and E): measure how evenly things (food, trees, rocks, statues) are spread over the world.

Input is a list of (x, z, kind) points or a grid of numbers (one number per cell, 0 = nothing, 1.. = a kind). The world is
the square arena [-half, half] in x and z (default half 416 studs = 832 wide). The cell size is a parameter: --cells 256
(default) gives 3.25 studs per cell. The tool cuts the arena into blocks of 10 x 10, 20 x 20 and 30 x 30 cells and, for all
kinds together and for each kind, prints:

  * foods per block: min / median / max, the share of EMPTY blocks, the CROWDED blocks (more than 2 x the median; for a kind
    whose median is 0 the limit falls back to 2 x the mean);
  * a SPREAD SCORE = variance / mean of the block counts. Plain random scatter gives about 1, above 1 is clumped, below 1 is
    evenly spaced. Because the island has water and cliffs, the tool also draws the SAME number of points uniformly over the
    walkable ground and prints that as "random would give" (so the verdict compares like with like);
  * nearest-neighbour distance between two points of the kind (min / median / max) and the same median for random scatter;
  * the walking distance from 2,000 random walkable spots to the nearest point (min / median / 95th percentile / max);
  * an EMPTY-ZONE report: connected patches of walkable ground more than --empty-radius studs from any point.

It writes one heat-map picture per block size and one dot map into --png-dir (next free number prefix) and checks optional
TARGETS: a small JSON {"rules": [{"kind": "all", "block": 20, "metric": "empty_share", "max": 0.1}, ...]} and exits
non-zero when a rule is broken (CI). Metrics: count_min, count_median, count_max, empty_share, crowded_share, spread,
nn_min, nn_median, nn_max, walk_median, walk_p95, walk_max, empty_zone_radius, empty_zone_count. "block" is needed for the
block metrics only. Walkable blocks (half or more of the block is walkable ground) are used when a ground mask is known.

Usage:
  python tools/layer_stats.py --points build/food_layout_1404.json [--cells 256] [--png-dir DIR] [--targets t.json]
  python tools/layer_stats.py --grid layer.json          # {"half": 416, "rows": [[0, 1, ...], ...]}  (rows[iz][ix])
  python tools/layer_stats.py --layer layer.txt [--kind-names 1=berry,2=fruit]   # WorldLayer text (src/shared/WorldLayer.luau via tools/worldlayer.py); each non-zero cell is one point
Points files: JSON {"points": [[x, z, kind], ...], "arena": 416, "mask": {"cell": 4, "rows": ["0101..", ...]}} or CSV x,z,kind.
Pure Python plus Pillow for the pictures (CI installs it).
"""
from collections import defaultdict
from pathlib import Path
import argparse
import json
import math
import random
import statistics
import sys

BLOCK_CELLS = (10, 20, 30)
DEFAULT_CELLS = 256
DEFAULT_HALF = 416.0
WALK_SAMPLES = 2000
EMPTY_RADIUS = 25.0
KIND_ORDER = ('berry', 'fruit', 'egg', 'amber')


# ------------------------------------------------------------------------------ input
class Ground:
    """Which spots of the arena are walkable. Without a mask everything inside the arena is walkable."""

    def __init__(self, half, mask=None):
        self.half = float(half)
        self.rows = mask['rows'] if mask else None
        self.n = len(self.rows) if self.rows else 0
        self.cell = (2 * self.half / self.n) if self.n else 0.0

    def ok(self, x, z):
        if abs(x) >= self.half or abs(z) >= self.half:
            return False
        if not self.rows:
            return True
        ix, iz = int((x + self.half) / self.cell), int((z + self.half) / self.cell)
        return self.rows[min(iz, self.n - 1)][min(ix, self.n - 1)] == '1'

    def share(self, x0, z0, x1, z1, step=4.0):
        """Share of walkable ground inside the rectangle (sampled on a lattice)."""
        if not self.rows:
            return 1.0
        hit = total = 0
        z = z0 + step / 2
        while z < z1:
            x = x0 + step / 2
            while x < x1:
                total += 1
                hit += self.ok(x, z)
                x += step
            z += step
        return hit / total if total else 0.0


def points_from_grid(rows, half=DEFAULT_HALF, kinds=None):
    """A grid (rows[iz][ix], 0 = nothing) becomes one point per non-zero cell, at the cell centre; kind = kinds[value] or the number."""
    n_z, n_x = len(rows), len(rows[0]) if rows else 0
    cell_x, cell_z = 2 * half / n_x, 2 * half / n_z
    out = []
    for iz, row in enumerate(rows):
        for ix, value in enumerate(row):
            if value:
                name = (kinds or {}).get(str(value), str(value))
                out.append((-half + (ix + 0.5) * cell_x, -half + (iz + 0.5) * cell_z, name))
    return out


def load_points(path):
    """Returns (points, half, mask or None). JSON (with optional arena and mask) or CSV x,z,kind."""
    path = Path(path)
    if path.suffix.lower() == '.csv':
        lines = path.read_text(encoding='utf-8').splitlines()
        pts = []
        for line in lines[1:]:
            x, z, kind = line.split(',')
            pts.append((float(x), float(z), kind))
        return pts, DEFAULT_HALF, None
    data = json.loads(path.read_text(encoding='utf-8'))
    pts = [(float(p[0]), float(p[1]), str(p[2]) if len(p) > 2 else 'item') for p in data['points']]
    return pts, float(data.get('arena', DEFAULT_HALF)), data.get('mask')


# ------------------------------------------------------------------------------ geometry
class Buckets:
    """Nearest-point search on a coarse bucket grid."""

    def __init__(self, points, size=16.0):
        self.size = size
        self.cells = defaultdict(list)
        for i, (x, z) in enumerate(points):
            self.cells[(math.floor(x / size), math.floor(z / size))].append((i, x, z))
        self.count = len(points)

    def nearest(self, x, z, skip=-1, cap=math.inf):
        """Distance to the nearest point (inf when none is within `cap`, which only saves time)."""
        if self.count == 0 or (self.count == 1 and skip == 0):
            return math.inf
        cx, cz = math.floor(x / self.size), math.floor(z / self.size)
        best = math.inf
        ring = 0
        while ring < 200:
            if best < math.inf and (ring - 1) * self.size > best:
                break
            if (ring - 1) * self.size > cap:
                break
            for dx in range(-ring, ring + 1):
                for dz in range(-ring, ring + 1):
                    if max(abs(dx), abs(dz)) != ring:
                        continue
                    for i, px, pz in self.cells.get((cx + dx, cz + dz), ()):
                        if i != skip:
                            d = math.hypot(px - x, pz - z)
                            if d < best:
                                best = d
            ring += 1
        return best


def percentile(values, q):
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def random_walkable(ground, count, rng):
    pts = []
    while len(pts) < count:
        x, z = rng.uniform(-ground.half, ground.half), rng.uniform(-ground.half, ground.half)
        if ground.ok(x, z):
            pts.append((x, z))
    return pts


# ------------------------------------------------------------------------------ block statistics
def block_grid(half, cells, block_cells):
    """Full blocks only: n x n blocks of block_cells cells; the strip left over at the far edges is skipped."""
    cell = 2 * half / cells
    size = block_cells * cell
    n = int(2 * half / size + 1e-9)
    return cell, size, n


def count_blocks(points_xz, half, size, n):
    counts = [[0] * n for _ in range(n)]
    for x, z in points_xz:
        bx, bz = int((x + half) / size), int((z + half) / size)
        if 0 <= bx < n and 0 <= bz < n:
            counts[bz][bx] += 1
    return counts


def summarise(values):
    """min / median / max, empty share, crowded limit and share, spread score (variance / mean) of a list of block counts."""
    if not values:
        return {'blocks': 0, 'count_min': 0, 'count_median': 0, 'count_max': 0, 'mean': 0.0, 'empty_share': 1.0,
                'crowded_limit': 0.0, 'crowded_blocks': 0, 'crowded_share': 0.0, 'spread': 0.0}
    mean = statistics.fmean(values)
    median = statistics.median(values)
    var = statistics.pvariance(values)
    limit = 2 * median if median > 0 else 2 * mean
    crowded = sum(1 for v in values if v > limit) if limit > 0 else 0
    return {'blocks': len(values), 'count_min': min(values), 'count_median': median, 'count_max': max(values), 'mean': mean,
            'empty_share': sum(1 for v in values if v == 0) / len(values), 'crowded_limit': limit, 'crowded_blocks': crowded,
            'crowded_share': crowded / len(values), 'spread': (var / mean) if mean > 0 else 0.0}


def analyse(points, half=DEFAULT_HALF, cells=DEFAULT_CELLS, blocks=BLOCK_CELLS, mask=None, empty_radius=EMPTY_RADIUS,
            walk_samples=WALK_SAMPLES, seed=1, baseline_draws=12):
    """points = [(x, z, kind), ...]. Returns a plain dict with everything the printout, pictures and targets use."""
    rng = random.Random(seed)
    ground = Ground(half, mask)
    kinds = sorted({k for _, _, k in points}, key=lambda k: (KIND_ORDER.index(k) if k in KIND_ORDER else 99, k))
    groups = {'all': [(x, z) for x, z, _ in points]}
    for kind in kinds:
        groups[kind] = [(x, z) for x, z, k in points if k == kind]
    result = {'half': half, 'cells': cells, 'cell_studs': 2 * half / cells, 'kinds': ['all'] + kinds,
              'totals': {k: len(v) for k, v in groups.items()}, 'walkable_share': None, 'blocks': {}, 'nn': {},
              'walk': {}, 'empty': {}}
    if ground.rows:
        result['walkable_share'] = sum(r.count('1') for r in ground.rows) / (ground.n * ground.n)

    # --- blocks at several sizes, with a random-scatter reference drawn on the same walkable ground
    for b in blocks:
        cell, size, n = block_grid(half, cells, b)
        walkable = [[ground.share(-half + bx * size, -half + bz * size, -half + (bx + 1) * size, -half + (bz + 1) * size) >= 0.5
                     for bx in range(n)] for bz in range(n)]
        entry = {'cells': b, 'studs': size, 'n': n, 'covered': (n * size / (2 * half)) ** 2, 'walkable': walkable,
                 'walkable_blocks': sum(sum(1 for v in r if v) for r in walkable), 'kinds': {}, 'grid': {}}
        for kind, pts in groups.items():
            grid = count_blocks(pts, half, size, n)
            entry['grid'][kind] = grid
            values = [grid[bz][bx] for bz in range(n) for bx in range(n) if walkable[bz][bx]]
            stats = summarise(values)
            base = []
            for _ in range(baseline_draws):
                g = count_blocks(random_walkable(ground, len(pts), rng), half, size, n)
                base.append(summarise([g[bz][bx] for bz in range(n) for bx in range(n) if walkable[bz][bx]]))
            stats['random_spread'] = statistics.fmean(s['spread'] for s in base)
            stats['random_empty_share'] = statistics.fmean(s['empty_share'] for s in base)
            stats['verdict'] = verdict(stats['spread'], stats['random_spread'], stats['blocks'])
            entry['kinds'][kind] = stats
        result['blocks'][b] = entry

    # --- nearest neighbour between two points of the same kind (and a random-scatter reference)
    for kind, pts in groups.items():
        search = Buckets(pts)
        d = [search.nearest(x, z, skip=i) for i, (x, z) in enumerate(pts)]
        d = [v for v in d if v < math.inf]
        ref = random_walkable(ground, len(pts), rng)
        rsearch = Buckets(ref)
        rd = [rsearch.nearest(x, z, skip=i) for i, (x, z) in enumerate(ref)]
        rd = [v for v in rd if v < math.inf]
        result['nn'][kind] = {'nn_min': min(d, default=0.0), 'nn_median': statistics.median(d) if d else 0.0,
                              'nn_max': max(d, default=0.0), 'random_median': statistics.median(rd) if rd else 0.0}

    # --- walking distance from random walkable spots to the nearest point, per kind
    spots = random_walkable(ground, walk_samples, rng)
    for kind, pts in groups.items():
        search = Buckets(pts)
        d = sorted(search.nearest(x, z) for x, z in spots)
        d = [v for v in d if v < math.inf]
        result['walk'][kind] = {'walk_min': d[0] if d else 0.0, 'walk_median': statistics.median(d) if d else 0.0,
                                'walk_p95': percentile(d, 0.95), 'walk_max': d[-1] if d else 0.0}

    # --- empty zones (all kinds together): connected walkable patches farther than empty_radius from any point
    result['empty'] = empty_zones(groups['all'], ground, empty_radius)
    return result


def verdict(spread, random_spread, blocks=100):
    """Compare with random scatter on the same ground. var / mean of n blocks wobbles by about sqrt(2 / (n - 1)) even for pure
    random, so the 'like random' band is three of those wide (few big blocks = a wide band)."""
    if random_spread <= 0 or blocks < 3:
        return 'n/a'
    band = max(0.15, 3 * math.sqrt(2 / (blocks - 1)))
    ratio = spread / random_spread
    if ratio > 1 + band:
        return 'CLUMPED'
    if ratio < 1 - band:
        return 'EVEN'
    return 'like random'


def empty_zones(points, ground, radius, step=8.0):
    """Connected patches of walkable ground whose nearest point is farther than `radius`. Returns zones sorted by size."""
    search = Buckets(points)
    n = int(2 * ground.half / step)
    far = {}
    for iz in range(n):
        for ix in range(n):
            x, z = -ground.half + (ix + 0.5) * step, -ground.half + (iz + 0.5) * step
            if ground.ok(x, z) and search.nearest(x, z, cap=radius) > radius:
                far[(ix, iz)] = (x, z)
    seen, zones = set(), []
    for start in far:
        if start in seen:
            continue
        stack, members = [start], []
        seen.add(start)
        while stack:
            c = stack.pop()
            members.append(c)
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    nb = (c[0] + dx, c[1] + dz)
                    if nb in far and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
        xs = [far[m][0] for m in members]
        zs = [far[m][1] for m in members]
        cx, cz = statistics.fmean(xs), statistics.fmean(zs)
        # biggest circle with no point inside: the member farthest from every point
        best_m = max(members, key=lambda m: search.nearest(*far[m]))
        zones.append({'x': far[best_m][0], 'z': far[best_m][1], 'radius': search.nearest(*far[best_m]),
                      'area': len(members) * step * step, 'cx': cx, 'cz': cz})
    zones.sort(key=lambda z: -z['area'])
    total_walkable = sum(1 for iz in range(n) for ix in range(n) if ground.ok(-ground.half + (ix + 0.5) * step, -ground.half + (iz + 0.5) * step))
    return {'radius': radius, 'count': len(zones), 'zones': zones, 'empty_zone_count': len(zones),
            'empty_zone_radius': max((z['radius'] for z in zones), default=0.0),
            'far_share': (len(far) / total_walkable) if total_walkable else 0.0}


# ------------------------------------------------------------------------------ targets
def metric_value(result, kind, block, metric):
    if metric in ('count_min', 'count_median', 'count_max', 'empty_share', 'crowded_share', 'spread'):
        return result['blocks'][int(block)]['kinds'][kind][metric]
    if metric in ('nn_min', 'nn_median', 'nn_max'):
        return result['nn'][kind][metric]
    if metric in ('walk_min', 'walk_median', 'walk_p95', 'walk_max'):
        return result['walk'][kind][metric]
    if metric in ('empty_zone_radius', 'empty_zone_count'):
        return result['empty'][metric]
    raise KeyError(f'unknown metric {metric}')


def check_targets(result, targets):
    """Returns a list of broken-rule messages (empty = all good)."""
    broken = []
    for rule in targets.get('rules', []):
        kind, block, metric = rule.get('kind', 'all'), rule.get('block'), rule['metric']
        try:
            value = metric_value(result, kind, block, metric)
        except KeyError as err:
            broken.append(f'cannot check {rule}: missing {err}')
            continue
        where = f'{kind}' + (f' @ {block}x{block}' if block else '')
        if 'min' in rule and value < rule['min']:
            broken.append(f'{where}: {metric} = {value:.3g} is below the minimum {rule["min"]}')
        if 'max' in rule and value > rule['max']:
            broken.append(f'{where}: {metric} = {value:.3g} is above the maximum {rule["max"]}')
    return broken


# ------------------------------------------------------------------------------ printing
def report(result, title='layer'):
    out = []
    w = out.append
    w(f'== {title}: {result["totals"]["all"]} points, arena {2 * result["half"]:.0f} studs, {result["cells"]} cells ({result["cell_studs"]:.2f} studs per cell)')
    if result['walkable_share'] is not None:
        w(f'   walkable ground: {result["walkable_share"] * 100:.1f}% of the arena (blocks with half or more walkable ground are counted)')
    w('   totals: ' + ', '.join(f'{k} {result["totals"][k]}' for k in result['kinds']))
    for b, entry in result['blocks'].items():
        w('')
        w(f'-- blocks of {b} x {b} cells = {entry["studs"]:.1f} studs ({entry["walkable_blocks"]} walkable blocks of {entry["n"] ** 2}; '
          f'covers {entry["covered"] * 100:.0f}% of the arena)')
        w(f'   {"kind":<7} {"total":>6} {"min":>4} {"median":>7} {"max":>4} {"empty":>7} {"crowded":>8} {"limit":>6} {"spread":>7} {"random":>7}  verdict')
        for kind in result['kinds']:
            s = entry['kinds'][kind]
            w(f'   {kind:<7} {result["totals"][kind]:>6} {s["count_min"]:>4.0f} {s["count_median"]:>7.1f} {s["count_max"]:>4.0f} '
              f'{s["empty_share"] * 100:>6.1f}% {s["crowded_blocks"]:>8} {s["crowded_limit"]:>6.1f} {s["spread"]:>7.2f} {s["random_spread"]:>7.2f}  {s["verdict"]}')
    w('')
    w('-- nearest other point of the same kind (studs)')
    w(f'   {"kind":<7} {"min":>6} {"median":>7} {"max":>7} {"random median":>14}')
    for kind in result['kinds']:
        n = result['nn'][kind]
        w(f'   {kind:<7} {n["nn_min"]:>6.1f} {n["nn_median"]:>7.1f} {n["nn_max"]:>7.1f} {n["random_median"]:>14.1f}')
    w('')
    w(f'-- walk from {WALK_SAMPLES} random walkable spots to the nearest point (studs)')
    w(f'   {"kind":<7} {"min":>6} {"median":>7} {"95th":>7} {"max":>7}')
    for kind in result['kinds']:
        d = result['walk'][kind]
        w(f'   {kind:<7} {d["walk_min"]:>6.1f} {d["walk_median"]:>7.1f} {d["walk_p95"]:>7.1f} {d["walk_max"]:>7.1f}')
    e = result['empty']
    w('')
    w(f'-- empty zones: walkable ground more than {e["radius"]:.0f} studs from any point: {e["count"]} patches, '
      f'{e["far_share"] * 100:.1f}% of the walkable ground; biggest empty circle radius {e["empty_zone_radius"]:.1f} studs')
    for zone in e['zones'][:6]:
        w(f'   patch at ({zone["x"]:.0f}, {zone["z"]:.0f}): area {zone["area"]:.0f} sq studs, empty circle radius {zone["radius"]:.1f}')
    return '\n'.join(out)


# ------------------------------------------------------------------------------ pictures
def _font(size):
    from PIL import ImageFont
    for name in ('arial.ttf', 'Arial.ttf', 'DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'LiberationSans-Regular.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def next_number(directory):
    """Next free numeric prefix among files such as 194-name.png."""
    best = 0
    for p in Path(directory).glob('*'):
        head = p.name.split('-', 1)[0]
        if head.isdigit():
            best = max(best, int(head))
    return best + 1


def _heat_colour(v, vmax):
    """White (0) -> pale yellow -> orange -> dark red (vmax)."""
    if v <= 0:
        return (245, 245, 245)
    t = min(1.0, v / max(vmax, 1))
    stops = [(0.0, (255, 245, 170)), (0.35, (250, 190, 70)), (0.7, (225, 90, 40)), (1.0, (120, 20, 30))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
    return stops[-1][1]


KIND_COLOURS = {'berry': (200, 40, 70), 'fruit': (235, 140, 20), 'egg': (60, 110, 200), 'amber': (30, 30, 30)}


def _frame(title, subtitle, half, map_px=900):
    from PIL import Image, ImageDraw
    left, top, right, bottom = 90, 110, 250, 70
    img = Image.new('RGB', (left + map_px + right, top + map_px + bottom), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((left, 18), title, fill=(20, 20, 20), font=_font(26))
    d.text((left, 58), subtitle, fill=(70, 70, 70), font=_font(17))
    return img, d, left, top, map_px


def _axes(d, left, top, px, half):
    f = _font(15)
    step = 100
    v = -int(half // step) * step
    while v <= half:
        pos = (v + half) / (2 * half) * px
        d.line([(left + pos, top + px), (left + pos, top + px + 6)], fill=(60, 60, 60))
        d.text((left + pos - 14, top + px + 9), str(v), fill=(60, 60, 60), font=f)
        d.line([(left - 6, top + pos), (left, top + pos)], fill=(60, 60, 60))
        d.text((left - 48, top + pos - 8), str(v), fill=(60, 60, 60), font=f)
        v += step
    d.text((left + px / 2 - 60, top + px + 36), 'x (studs, west to east)', fill=(40, 40, 40), font=_font(16))
    d.text((8, top - 22), 'z (studs, north to south)', fill=(40, 40, 40), font=_font(16))
    d.rectangle([left, top, left + px, top + px], outline=(60, 60, 60))


def draw_heatmap(result, points, block, path, title='Food spread'):
    """Heat map of the 'all' counts per block; grey = mostly water or cliff (not counted); dots = every point."""
    from PIL import ImageDraw
    entry = result['blocks'][block]
    half = result['half']
    img, d, left, top, px = _frame(f'{title}: blocks of {block} x {block} cells ({entry["studs"]:.0f} studs)',
                                   f'{result["totals"]["all"]} points; every square counts the points inside it', half)
    n, size = entry['n'], entry['studs']
    scale = px / (2 * half)
    grid = entry['grid']['all']
    s = entry['kinds']['all']
    vmax = max(s['count_max'], 1)
    big = _font(16 if block >= 20 else 12)
    for bz in range(n):
        for bx in range(n):
            x0, y0 = left + bx * size * scale, top + bz * size * scale
            box = [x0, y0, x0 + size * scale, y0 + size * scale]
            if entry['walkable'][bz][bx]:
                v = grid[bz][bx]
                colour = _heat_colour(v, vmax)
                if v > s['crowded_limit'] > 0:
                    d.rectangle(box, fill=colour, outline=(0, 0, 0), width=3)
                else:
                    d.rectangle(box, fill=colour, outline=(190, 190, 190))
                if block >= 20 or v > 0:
                    d.text((x0 + 4, y0 + 3), str(v), fill=(0, 0, 0) if v < 0.6 * vmax else (255, 255, 255), font=big)
            else:
                d.rectangle(box, fill=(150, 150, 160), outline=(190, 190, 190))
    # the rim strip that does not fill a whole block
    edge = left + n * size * scale
    d.rectangle([edge, top, left + px, top + px], fill=(235, 235, 245))
    d.rectangle([left, top + n * size * scale, left + px, top + px], fill=(235, 235, 245))
    for x, z, _ in points:
        cx, cy = left + (x + half) * scale, top + (z + half) * scale
        d.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=(40, 40, 40))
    _axes(d, left, top, px, half)
    # legend
    lx = left + px + 30
    f = _font(16)
    d.text((lx, top), 'Points per square', fill=(20, 20, 20), font=f)
    for i in range(10):
        v = vmax * i / 9
        d.rectangle([lx, top + 30 + i * 26, lx + 36, top + 52 + i * 26], fill=_heat_colour(v, vmax), outline=(120, 120, 120))
        d.text((lx + 46, top + 32 + i * 26), f'{v:.0f}' + ('  (most)' if i == 9 else '  (none)' if i == 0 else ''), fill=(20, 20, 20), font=f)
    y = top + 30 + 10 * 26 + 14
    d.rectangle([lx, y, lx + 36, y + 22], fill=(150, 150, 160), outline=(120, 120, 120))
    d.text((lx + 46, y + 2), 'water / cliff', fill=(20, 20, 20), font=f)
    d.rectangle([lx, y + 34, lx + 36, y + 56], fill=(250, 190, 70), outline=(0, 0, 0), width=3)
    d.text((lx + 46, y + 36), 'crowded (> 2 x', fill=(20, 20, 20), font=f)
    d.text((lx + 46, y + 56), 'the middle square)', fill=(20, 20, 20), font=f)
    d.rectangle([lx, y + 84, lx + 36, y + 106], fill=(235, 235, 245), outline=(120, 120, 120))
    d.text((lx + 46, y + 86), 'edge strip, not counted', fill=(20, 20, 20), font=f)
    lines = [f'middle square: {s["count_median"]:.0f}', f'fewest / most: {s["count_min"]:.0f} / {s["count_max"]:.0f}',
             f'empty squares: {s["empty_share"] * 100:.0f}%', f'crowded squares: {s["crowded_blocks"]}',
             f'spread score: {s["spread"]:.2f}', f'random scatter: {s["random_spread"]:.2f}', f'verdict: {s["verdict"]}']
    for i, line in enumerate(lines):
        d.text((lx, y + 140 + i * 22), line, fill=(20, 20, 20), font=f)
    d.text((lx, y + 140 + len(lines) * 22 + 4), '(1 = random, more = clumped,', fill=(90, 90, 90), font=_font(14))
    d.text((lx, y + 140 + len(lines) * 22 + 22), 'less = evenly spread)', fill=(90, 90, 90), font=_font(14))
    img.save(path)
    return path


def draw_dots(result, points, path, mask=None, title='Food dots and empty zones'):
    """Every point coloured by kind, walkable ground white, water/cliff grey, empty zones circled."""
    half = result['half']
    ground = Ground(half, mask)
    e = result['empty']
    img, d, left, top, px = _frame(title, f'{result["totals"]["all"]} points; red circles = ground more than {e["radius"]:.0f} studs from any point', half)
    scale = px / (2 * half)
    if ground.rows:
        c = ground.cell * scale
        for iz in range(ground.n):
            for ix in range(ground.n):
                if ground.rows[iz][ix] != '1':
                    d.rectangle([left + ix * c, top + iz * c, left + (ix + 1) * c, top + (iz + 1) * c], fill=(200, 200, 210))
    for x, z, kind in points:
        cx, cy = left + (x + half) * scale, top + (z + half) * scale
        r = 3 if kind in ('egg', 'amber') else 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=KIND_COLOURS.get(kind, (90, 90, 90)))
    for zone in e['zones'][:12]:
        cx, cy, r = left + (zone['x'] + half) * scale, top + (zone['z'] + half) * scale, zone['radius'] * scale
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(220, 0, 0), width=3)
    _axes(d, left, top, px, half)
    lx = left + px + 30
    f = _font(16)
    d.text((lx, top), 'Food kind', fill=(20, 20, 20), font=f)
    for i, kind in enumerate(k for k in result['kinds'] if k != 'all'):
        y = top + 34 + i * 30
        d.ellipse([lx, y, lx + 14, y + 14], fill=KIND_COLOURS.get(kind, (90, 90, 90)))
        d.text((lx + 24, y - 2), f'{kind} ({result["totals"][kind]})', fill=(20, 20, 20), font=f)
    y = top + 34 + 5 * 30
    d.rectangle([lx, y, lx + 18, y + 14], fill=(200, 200, 210), outline=(120, 120, 120))
    d.text((lx + 26, y - 2), 'water / cliff', fill=(20, 20, 20), font=f)
    d.ellipse([lx, y + 30, lx + 18, y + 48], outline=(220, 0, 0), width=3)
    d.text((lx + 26, y + 30), 'empty zone', fill=(20, 20, 20), font=f)
    w = result['walk']['all']
    for i, line in enumerate([f'walk to nearest food', f'  middle: {w["walk_median"]:.0f} studs', f'  95th: {w["walk_p95"]:.0f} studs',
                              f'  worst: {w["walk_max"]:.0f} studs', f'empty patches: {e["count"]}',
                              f'biggest empty circle:', f'  radius {e["empty_zone_radius"]:.0f} studs']):
        d.text((lx, y + 80 + i * 22), line, fill=(20, 20, 20), font=f)
    img.save(path)
    return path


def write_pictures(result, points, directory, mask=None, name='food', title='Food'):
    """One heat map per block size and one dot map; returns the paths. Numbers continue the existing prefixes in `directory`."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    n = next_number(directory)
    paths = []
    for b in result['blocks']:
        paths.append(draw_heatmap(result, points, b, directory / f'{n}-{name}-spread-{b}x{b}-blocks.png', title=f'{title} spread'))
        n += 1
    paths.append(draw_dots(result, points, directory / f'{n}-{name}-dots-and-empty-zones.png', mask=mask, title=f'{title} dots and empty zones'))
    return paths


# ------------------------------------------------------------------------------ command line
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--points', help='JSON or CSV with x, z, kind')
    src.add_argument('--grid', help='JSON {"half": 416, "rows": [[..], ..]}')
    src.add_argument('--layer', help='WorldLayer text file (WL1:...), a square layer')
    ap.add_argument('--kind-names', help='names for the digits of --layer / --grid, for example 1=berry,2=fruit,3=egg,4=amber')
    ap.add_argument('--half', type=float, default=None, help='half arena width in studs (default 416 or the file)')
    ap.add_argument('--cells', type=int, default=DEFAULT_CELLS, help='cells across the arena (cell size = 2 x half / cells)')
    ap.add_argument('--blocks', default=','.join(map(str, BLOCK_CELLS)), help='block sizes in cells')
    ap.add_argument('--empty-radius', type=float, default=EMPTY_RADIUS)
    ap.add_argument('--png-dir', help='write the pictures here (numbered)')
    ap.add_argument('--name', default='food', help='picture name part and report title')
    ap.add_argument('--targets', help='JSON of min/max rules; exit 1 when broken')
    ap.add_argument('--json', help='also write the numbers here')
    args = ap.parse_args(argv)

    mask = None
    half = args.half
    names = dict(part.split('=', 1) for part in (args.kind_names or '').split(',') if '=' in part)
    if args.points:
        points, file_half, mask = load_points(args.points)
        half = half or file_half
    elif args.grid:
        data = json.loads(Path(args.grid).read_text(encoding='utf-8'))
        half = half or float(data.get('half', DEFAULT_HALF))
        points = points_from_grid(data['rows'], half, {**data.get('kinds', {}), **names})
        args.cells = len(data['rows'])
    else:
        import worldlayer
        layer = worldlayer.decode(Path(args.layer).read_text(encoding='utf-8'))
        if layer.width != layer.height:
            ap.error('--layer needs a square layer (width = height)')
        half = half or layer.world_half_width
        points = points_from_grid(layer.rows(), half, names)
        args.cells = layer.width
    blocks = tuple(int(b) for b in args.blocks.split(','))
    result = analyse(points, half, args.cells, blocks, mask, args.empty_radius)
    print(report(result, args.name))
    if args.png_dir:
        for p in write_pictures(result, points, args.png_dir, mask, args.name, args.name.capitalize()):
            print('picture:', p)
    if args.json:
        slim = json.loads(json.dumps(result, default=str))
        for entry in slim['blocks'].values():
            entry.pop('grid', None)
            entry.pop('walkable', None)
        Path(args.json).write_text(json.dumps(slim, indent=1), encoding='utf-8')
    if args.targets:
        broken = check_targets(result, json.loads(Path(args.targets).read_text(encoding='utf-8')))
        if broken:
            print('\nTARGETS BROKEN:')
            for line in broken:
                print('  -', line)
            return 1
        print('\ntargets: all met')
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
