#!/usr/bin/env python3
"""BD-1047 (docs/187 B and F): before / after of the food placement, with pictures.

BEFORE = today's placement re-created offline (tools/dump_food_layout.py, seed Config.FoodSeed; the same rules with different dice).
AFTER  = the committed designed food map (tools/food_layer_data.py, made by tools/generate_food_layer.py).
Both go through tools/layer_stats.py on the SAME ground, blocks of 10 / 20 / 30 cells of a 256-cell grid (32 / 65 / 97 studs), so the numbers
are comparable with docs/187 section F. It prints a table, a food-points-per-block table (do the hot spots make rich areas?) and a rough
"greedy walker" estimate (a walker that always goes to the closest food, or to the best food per second of walking; NOT a real player: the
smart test bot of BD-1048 does not exist yet) so the change in food per minute is visible.

  python tools/compare_food_layers.py --runner C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe [--png-dir docs/evidence/review-2026-10-17] [--json out.json]
"""
from pathlib import Path
import argparse
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dump_food_layout  # noqa: E402
import food_layer_data  # noqa: E402
import generate_food_layer as gen  # noqa: E402
import layer_stats  # noqa: E402
import worldlayer  # noqa: E402

POINTS = {'berry': 1, 'fruit': 4, 'egg': 15, 'amber': 50}   # Config / FoodService TYPES
WALK_SPEED = 22.0      # studs per second (docs/187 F)
PICKUP_RADIUS = 2.25   # Config.FoodPickupRadius
RESPAWN = 8.0          # Config.FoodRespawnSeconds
SPAWN = (0.0, 30.0)


def layer_points(layer):
    """[(x, z, kind name)] for every food cell of a WorldLayer (cell centres)."""
    out = []
    for ix, iz, value in layer.non_zero():
        x, z = layer.centre_of(ix, iz)
        out.append((x, z, gen.KIND_NAMES[value]))
    return out


def committed_layer():
    return worldlayer.decode(food_layer_data.TEXT)


def block_points(points, size=65.0, half=416.0):
    """Food points (not counts) per square of `size` studs: [value, ...] for the squares inside the arena."""
    n = int(2 * half / size)
    grid = [[0] * n for _ in range(n)]
    for x, z, kind in points:
        bx, bz = int((x + half) / size), int((z + half) / size)
        if 0 <= bx < n and 0 <= bz < n:
            grid[bz][bx] += POINTS[kind]
    return grid


def greedy_walk(points, seconds=300.0, policy='nearest'):
    """A walker from the run start: goes to the closest food ('nearest') or to the food with the most points per second of walking
    ('value'), eats it, repeats; a food comes back RESPAWN seconds after it was eaten. Returns (foods eaten, points) in `seconds`."""
    xs = [p[0] for p in points]
    zs = [p[1] for p in points]
    pts = [POINTS[p[2]] for p in points]
    ready = [0.0] * len(points)
    x, z = SPAWN
    t, eaten, gained = 0.0, 0, 0
    while t < seconds:
        best, best_score = -1, -1.0
        for i in range(len(points)):
            if ready[i] > t:
                continue
            d = max(0.0, math.hypot(xs[i] - x, zs[i] - z) - PICKUP_RADIUS)
            score = (1.0 / (d + 1.0)) if policy == 'nearest' else pts[i] / (d / WALK_SPEED + 0.25)
            if score > best_score:
                best, best_score = i, score
        if best < 0:
            break
        d = max(0.0, math.hypot(xs[best] - x, zs[best] - z) - PICKUP_RADIUS)
        t += d / WALK_SPEED + 0.1
        x, z = xs[best], zs[best]
        ready[best] = t + RESPAWN
        eaten += 1
        gained += pts[best]
    return eaten, gained


def numbers(points, mask, half=416.0):
    a = layer_stats.analyse(points, half, 256, (10, 20, 30), mask)
    blocks = a['blocks']
    row = {
        'foods': a['totals']['all'],
        'spread': {b: blocks[b]['kinds']['all']['spread'] for b in blocks},
        'random_spread': {b: blocks[b]['kinds']['all']['random_spread'] for b in blocks},
        'empty_share_10': blocks[10]['kinds']['all']['empty_share'],
        'crowded_10': blocks[10]['kinds']['all']['crowded_blocks'],
        'count_min_max_20': (blocks[20]['kinds']['all']['count_min'], blocks[20]['kinds']['all']['count_max']),
        'nn_min': a['nn']['all']['nn_min'], 'nn_median': a['nn']['all']['nn_median'],
        'walk_median': a['walk']['all']['walk_median'], 'walk_max': a['walk']['all']['walk_max'],
        'egg_median': a['walk']['egg']['walk_median'], 'egg_p95': a['walk']['egg']['walk_p95'], 'egg_max': a['walk']['egg']['walk_max'],
        'amber_median': a['walk']['amber']['walk_median'], 'amber_p95': a['walk']['amber']['walk_p95'], 'amber_max': a['walk']['amber']['walk_max'],
        'empty_zone_count': a['empty']['empty_zone_count'], 'empty_zone_radius': a['empty']['empty_zone_radius'],
        'empty_far_share': a['empty']['far_share'],
        'counts': {k: a['totals'][k] for k in a['kinds']},
    }
    value = [v for r in block_points(points) for v in r]
    mean = statistics.fmean(value)
    row['value_block_mean'], row['value_block_max'], row['value_block_max_over_mean'] = mean, max(value), max(value) / mean
    row['walker'] = {p: greedy_walk(points, 300.0, p) for p in ('nearest', 'value')}
    return a, row


def table(before, after):
    def f(label, key, fmt='{:.1f}', sub=None):
        b, a = (before[key], after[key]) if sub is None else (before[key][sub], after[key][sub])
        return f'| {label} | {fmt.format(b)} | {fmt.format(a)} |'
    rows = ['| Measure | Before (today) | After (designed map) |', '| --- | ---: | ---: |']
    rows.append(f('Foods in total', 'foods', '{:.0f}'))
    for b in (10, 20, 30):
        rows.append(f'| Spread score, blocks of {b} x {b} cells ({ {10: 32, 20: 65, 30: 97}[b] } studs; random scatter = 1) | {before["spread"][b]:.2f} | {after["spread"][b]:.2f} |')
    rows.append(f('Empty small blocks (32 studs), share', 'empty_share_10', '{:.1%}'))
    rows.append(f('Crowded small blocks (more than 2 x the middle)', 'crowded_10', '{:.0f}'))
    rows.append(f('Nearest other food, middle (studs)', 'nn_median'))
    rows.append(f('Nearest other food, closest pair (studs)', 'nn_min'))
    rows.append(f('Walk to nearest food, middle (studs)', 'walk_median'))
    rows.append(f'| Walk to nearest food, worst (studs) | {before["walk_max"]:.1f} | {after["walk_max"]:.1f} |')
    rows.append(f('Walk to nearest egg, 95th (studs)', 'egg_p95'))
    rows.append(f('Walk to nearest amber, middle (studs)', 'amber_median'))
    rows.append(f('Walk to nearest amber, worst (studs)', 'amber_max'))
    rows.append(f('Empty patches (ground more than 25 studs from any food)', 'empty_zone_count', '{:.0f}'))
    rows.append(f('Biggest empty circle (radius, studs)', 'empty_zone_radius'))
    rows.append(f'| Richest 65-stud square vs the average square (food points) | {before["value_block_max_over_mean"]:.1f} x | {after["value_block_max_over_mean"]:.1f} x |')
    for p, name in (('nearest', 'closest-food walker'), ('value', 'best-food-per-second walker')):
        rows.append(f'| Greedy {name}, 5 minutes: foods / points | {before["walker"][p][0]} / {before["walker"][p][1]} | {after["walker"][p][0]} / {after["walker"][p][1]} |')
    return '\n'.join(rows)


def side_by_side(old_png, new_png, out):
    from PIL import Image
    a, b = Image.open(old_png), Image.open(new_png)
    img = Image.new('RGB', (a.width + b.width, max(a.height, b.height)), (255, 255, 255))
    img.paste(a, (0, 0))
    img.paste(b, (a.width, 0))
    img.save(out)


def draw_design(layer, ground_mask, path):
    """The designed map in one picture: foods by kind, the hot spots circled, the lone ambers ringed, the starter patches marked."""
    from PIL import ImageDraw
    pts = layer_points(layer)
    half = 416.0
    img, d, left, top, px = layer_stats._frame('Designed food map: hot spots, lone ambers, starter patches',
                                               f'{len(pts)} foods in a {layer.width} x {layer.height} layer ({layer.cell_size:.2f} studs per cell)', half)
    scale = px / (2 * half)
    ground = layer_stats.Ground(half, ground_mask)
    c = ground.cell * scale
    for iz in range(ground.n):
        for ix in range(ground.n):
            if ground.rows[iz][ix] != '1':
                d.rectangle([left + ix * c, top + iz * c, left + (ix + 1) * c, top + (iz + 1) * c], fill=(200, 200, 210))
    for x, z, kind in pts:
        cx, cy = left + (x + half) * scale, top + (z + half) * scale
        r = 3 if kind in ('egg', 'amber') else 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=layer_stats.KIND_COLOURS[kind])
    f = layer_stats._font(16)
    for zone in gen.ZONES:
        cx, cy, r = left + (zone['x'] + half) * scale, top + (zone['z'] + half) * scale, zone['r'] * scale
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 140, 60), width=3)
        d.text((cx - r, cy - r - 20), zone['name'], fill=(0, 110, 50), font=f)
    for centre in gen.STARTER_CENTRES:
        cx, cy, r = left + (centre[0] + half) * scale, top + (centre[1] + half) * scale, gen.STARTER_RADIUS * scale
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(150, 0, 150), width=2)
    d.text((left + (-70 + half) * scale, top + (62 + half) * scale), 'start patches', fill=(120, 0, 120), font=f)
    layer_stats._axes(d, left, top, px, half)
    lx = left + px + 30
    d.text((lx, top), 'Food kind', fill=(20, 20, 20), font=f)
    for i, kind in enumerate(('berry', 'fruit', 'egg', 'amber')):
        y = top + 34 + i * 30
        d.ellipse([lx, y, lx + 14, y + 14], fill=layer_stats.KIND_COLOURS[kind])
        d.text((lx + 24, y - 2), kind, fill=(20, 20, 20), font=f)
    y = top + 34 + 4 * 30 + 10
    d.ellipse([lx, y, lx + 18, y + 18], outline=(0, 140, 60), width=3)
    d.text((lx + 26, y), 'hot spot', fill=(20, 20, 20), font=f)
    d.ellipse([lx, y + 30, lx + 18, y + 48], outline=(150, 0, 150), width=2)
    d.text((lx + 26, y + 30), 'start patch', fill=(20, 20, 20), font=f)
    d.rectangle([lx, y + 60, lx + 18, y + 74], fill=(200, 200, 210), outline=(120, 120, 120))
    d.text((lx + 26, y + 58), 'water / cliff', fill=(20, 20, 20), font=f)
    d.text((lx, y + 100), 'The 4 amber dots far from', fill=(60, 60, 60), font=layer_stats._font(14))
    d.text((lx, y + 120), 'everything are the lone ones', fill=(60, 60, 60), font=layer_stats._font(14))
    d.text((lx, y + 140), 'on the mountain tops.', fill=(60, 60, 60), font=layer_stats._font(14))
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    ap.add_argument('--png-dir', help='write numbered pictures here')
    ap.add_argument('--json', help='write the numbers here')
    args = ap.parse_args()
    old = dump_food_layout.dump(args.runner, 1)
    seed = min(old)
    old_item = old[seed]
    mask = old_item['mask']
    old_points = [tuple(p) for p in old_item['points']]
    layer = committed_layer()
    new_points = layer_points(layer)
    a_old, before = numbers(old_points, mask)
    a_new, after = numbers(new_points, mask)
    print(table(before, after))
    if args.json:
        Path(args.json).write_text(json.dumps({'before': before, 'after': after, 'seed': seed}, indent=1, default=str), encoding='utf-8')
    if args.png_dir:
        directory = Path(args.png_dir)
        directory.mkdir(parents=True, exist_ok=True)
        n = layer_stats.next_number(directory)
        paths = []
        for b in a_new['blocks']:
            paths.append(layer_stats.draw_heatmap(a_new, new_points, b, directory / f'{n}-food-map-new-spread-{b}x{b}-blocks.png', title='New food map spread'))
            n += 1
        dots_new = layer_stats.draw_dots(a_new, new_points, directory / f'{n}-food-map-new-dots-and-empty-zones.png', mask=mask, title='New food map: dots and empty zones')
        paths.append(dots_new)
        n += 1
        tmp = directory / f'_old_dots_{n}.png'
        layer_stats.draw_dots(a_old, old_points, tmp, mask=mask, title='Today: dots and empty zones')
        side = directory / f'{n}-food-map-before-after-dots.png'
        side_by_side(tmp, dots_new, side)
        tmp.unlink()
        paths.append(side)
        n += 1
        paths.append(draw_design(layer, mask, directory / f'{n}-food-map-design-hot-spots-lone-ambers.png'))
        for p in paths:
            print('picture:', p)


if __name__ == '__main__':
    main()
