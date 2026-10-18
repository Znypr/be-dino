#!/usr/bin/env python3
"""BD-1047 (docs/187 B): checks the designed food map (src/shared/FoodLayerData.luau) against tools/targets/food_layer_targets.json.

  * the map decodes (Python and Luau), is 1,000 x 1,000 cells over the 416-stud half arena, and the Luau module and the Python copy
    (tools/food_layer_data.py) hold the same text;
  * counts per kind are exactly the planned ones (3,600 foods in all, same as today's kind mix 70 / 20 / 7 / 3), one food per cell;
  * the foods are small clusters of 3 to 5 (about 3 to 3.5 studs apart), clusters at least 12 studs apart centre to centre and 5.5 studs apart
    food to food; every amber cluster also holds an egg and a fruit; every food on ground (the FoodService rule, one stud from every edge);
  * both starter patches near (+-15, 24) are there (9 foods each, 2 berries to 1 fruit) and every lone amber stands alone;
  * tools/layer_stats.py rules: no empty small block, spread near or below random scatter, no big empty zone, short walks to the next egg and amber;
  * the food PACE stays about the same: tools/food_pace.py (a rough walker model, not a real player) on the map divided by the same model on
    today's placement is inside the band of the targets (the walker that just runs around within 8%, the two seeking walkers within 20%);
  * the map is deterministic: tools/generate_food_layer.py regenerates the identical text (a change of the terrain or of the generator
    needs `python tools/generate_food_layer.py --runner ... --write` and a commit);
  * src/shared/FoodLayer.luau (the reader FoodService uses) turns the map into the same foods, in the right sectors, in the pinned Luau runner.

    python tools/verify_food_layer.py --runner /path/to/luau
"""
from pathlib import Path
import argparse
import json
import math
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_food_layers as cmp  # noqa: E402
import dump_food_layout  # noqa: E402
import food_pace  # noqa: E402
import food_layer_data  # noqa: E402
import generate_food_layer as gen  # noqa: E402
import layer_stats  # noqa: E402
import worldlayer  # noqa: E402

TARGETS = ROOT / 'tools' / 'targets' / 'food_layer_targets.json'

READER_LUAU = r'''
local WorldLayer = (function()
@WORLDLAYER@
end)()
local FoodLayerData = (function()
@DATA@
end)()
local FoodLayer = (function()
local require = function(m) return m end
local script = {Parent = {WorldLayer = WorldLayer, FoodLayerData = FoodLayerData}}
@FOODLAYER@
end)()
local layer, reason = FoodLayer.load()
assert(layer, tostring(reason))
assert(WorldLayer.encode(layer) == (string.gsub(FoodLayerData.Map, "%s", "")), "re-encoding the map gives other text")
local plan, total = FoodLayer.plan(20, 408)
assert(plan, tostring(total))
print("T\t" .. tostring(total))
local starters = 0
for key, items in plan do
    for _, item in items do
        if item.starter then starters += 1 end
        print(string.format("I\t%d\t%.4f\t%.4f\t%d\t%d", key, item.x, item.z, item.kind, if item.starter then 1 else 0))
    end
end
print("S\t" .. tostring(starters))
-- a broken map is refused with a reason, never a crash
local bad, why = FoodLayer.plan(20, 408, "WL1:4:4:416:G")
assert(bad == nil and type(why) == "string", "a short map must be refused")
local empty, why2 = FoodLayer.plan(20, 408, "WL1:2:2:416:GH")
assert(empty == nil and type(why2) == "string", "a map without food must be refused")
print("OK")
'''


def reader_check(runner, layer, errors):
    src = READER_LUAU
    for token, path in (('@WORLDLAYER@', 'src/shared/WorldLayer.luau'), ('@DATA@', 'src/shared/FoodLayerData.luau'), ('@FOODLAYER@', 'src/shared/FoodLayer.luau')):
        src = src.replace(token, (ROOT / path).read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'reader.luau'
        path.write_text(src, encoding='utf-8')
        res = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if res.returncode or 'OK' not in res.stdout:
        errors.append('FoodLayer.luau reader failed in Luau: ' + (res.stdout[-400:] + res.stderr[-600:]).strip())
        return
    items = []
    total = starters = None
    for line in res.stdout.splitlines():
        p = line.split('\t')
        if p[0] == 'T':
            total = int(p[1])
        elif p[0] == 'S':
            starters = int(p[1])
        elif p[0] == 'I':
            items.append((int(p[1]), float(p[2]), float(p[3]), int(p[4]), int(p[5])))
    expect = sorted((round(x, 3), round(z, 3), gen.KIND_IDS[k]) for x, z, k in cmp.layer_points(layer))
    got = sorted((round(x, 3), round(z, 3), k) for _, x, z, k, _ in items)
    if total != gen.TOTAL or len(items) != gen.TOTAL:
        errors.append('the Luau reader found %s foods, expected %d' % (total, gen.TOTAL))
    elif expect != got:
        errors.append('the Luau reader and the Python reader disagree about food positions or kinds')
    if starters != 18:
        errors.append('the Luau reader marks %s starter foods, expected 18' % starters)
    count, extent = 20, 408.0
    width = 2 * extent / count
    for key, x, z, _, _ in items:
        sx, sz = max(0, min(count - 1, math.floor((x + extent) / width))), max(0, min(count - 1, math.floor((z + extent) / width)))
        if key != sx * count + sz:
            errors.append('a food at (%.1f, %.1f) is in sector key %d, expected %d' % (x, z, key, sx * count + sz))
            break


def groups(pts, link):
    """Single-link groups of foods closer than `link` studs: [[index, ...], ...]."""
    size = link
    cells = {}
    for i, (x, z, _) in enumerate(pts):
        cells.setdefault((math.floor(x / size), math.floor(z / size)), []).append(i)
    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for (cx, cz), members in cells.items():
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in cells.get((cx + dx, cz + dz), ()):
                    for i in members:
                        if i < j and math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]) < link:
                            parent[find(i)] = find(j)
    out = {}
    for i in range(len(pts)):
        out.setdefault(find(i), []).append(i)
    return list(out.values())


def check(runner):
    targets = json.loads(TARGETS.read_text(encoding='utf-8'))
    errors = []
    note = errors.append
    # --- files and decoding
    lay = targets['layer']
    try:
        layer = worldlayer.decode(food_layer_data.TEXT)
    except ValueError as err:
        return ['the Python copy of the map does not decode: %s' % err]
    if (layer.width, layer.height, layer.world_half_width) != (lay['width'], lay['height'], lay['half']):
        note('the map is %d x %d over half width %g, expected %d x %d over %g' % (layer.width, layer.height, layer.world_half_width, lay['width'], lay['height'], lay['half']))
    luau = gen.committed_text()
    if luau is None:
        note('src/shared/FoodLayerData.luau holds no map text')
    elif luau != food_layer_data.TEXT:
        note('src/shared/FoodLayerData.luau and tools/food_layer_data.py hold different maps; run tools/generate_food_layer.py --write')
    # --- counts and mix
    pts = cmp.layer_points(layer)
    counts = {k: sum(1 for p in pts if p[2] == k) for k in targets['counts']}
    if counts != targets['counts']:
        note('kind counts %r differ from the targets %r' % (counts, targets['counts']))
    if len(pts) != targets['total'] or layer.count() != targets['total']:
        note('%d foods in %d cells, expected %d each' % (len(pts), layer.count(), targets['total']))
    share = targets['kind_share']
    for kind in targets['counts']:
        got = counts.get(kind, 0) / max(1, len(pts))
        if abs(got - share[kind]) > share['tolerance']:
            note('%s is %.2f%% of the food, expected %.0f%% +- %.1f' % (kind, got * 100, share[kind] * 100, share['tolerance'] * 100))
    # --- clusters
    cl = targets['clusters']
    search = layer_stats.Buckets([(x, z) for x, z, _ in pts])
    nearest = min(search.nearest(x, z, skip=i) for i, (x, z, _) in enumerate(pts))
    if nearest < cl['foods_spacing_min']:
        note('two foods are only %.2f studs apart (minimum %.1f)' % (nearest, cl['foods_spacing_min']))
    found = groups(pts, cl['link_distance'])
    st_c = targets['starter']['centres']
    near_starter = lambda g: any(math.hypot(pts[g[0]][0] - cx, pts[g[0]][1] - cz) <= targets['starter']['radius'] for cx, cz in st_c)  # noqa: E731
    small, other = [], {'starter': 0, 'lone': 0, 'bad': []}
    for g in found:
        if cl['size_min'] <= len(g) <= cl['size_max']:
            small.append(g)
        elif len(g) == cl['starter_group_size'] and near_starter(g):
            other['starter'] += 1
        elif len(g) == cl['lone_group_size'] and pts[g[0]][2] == 'amber':
            other['lone'] += 1
        else:
            other['bad'].append(len(g))
    if other['bad']:
        note('%d food groups are not a cluster of %d to %d, a starter patch or a lone amber: sizes %r' % (len(other['bad']), cl['size_min'], cl['size_max'], sorted(other['bad'])[:10]))
    if other['starter'] != len(st_c) or other['lone'] != targets['lone_ambers']['count']:
        note('found %d starter patches and %d lone ambers, expected %d and %d' % (other['starter'], other['lone'], len(st_c), targets['lone_ambers']['count']))
    if small and statistics.fmean(len(g) for g in small) < cl['mean_size_min']:
        note('clusters hold %.2f foods on average, expected at least %.1f' % (statistics.fmean(len(g) for g in small), cl['mean_size_min']))
    centres = [(statistics.fmean(pts[i][0] for i in g), statistics.fmean(pts[i][1] for i in g)) for g in small]
    csearch = layer_stats.Buckets(centres)
    close = min((csearch.nearest(x, z, skip=i) for i, (x, z) in enumerate(centres)), default=math.inf)
    if close < cl['centre_spacing_min']:
        note('two cluster centres are only %.1f studs apart (minimum %.1f)' % (close, cl['centre_spacing_min']))
    who = {}
    for k, g in enumerate(small):
        for i in g:
            who[i] = k
    between = math.inf
    cells = {}
    for i, (x, z, _) in enumerate(pts):
        cells.setdefault((math.floor(x / 6), math.floor(z / 6)), []).append(i)
    for (cx, cz), members in cells.items():
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in cells.get((cx + dx, cz + dz), ()):
                    for i in members:
                        if i < j and who.get(i) != who.get(j):
                            between = min(between, math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]))
    if between < cl['between_clusters_min']:
        note('foods of two different groups are only %.1f studs apart (minimum %.1f)' % (between, cl['between_clusters_min']))
    amber_groups = [g for g in small if any(pts[i][2] == 'amber' for i in g)]
    rich = [g for g in amber_groups if any(pts[i][2] == 'egg' for i in g) and any(pts[i][2] == 'fruit' for i in g)]
    if amber_groups and len(rich) / len(amber_groups) < targets['amber_clusters_with_egg_and_fruit_min_share']:
        note('only %d of %d amber clusters also hold an egg and a fruit' % (len(rich), len(amber_groups)))
    # --- ground (needs the real terrain rule)
    model = dump_food_layout.ground_model(runner, 1.0, 4.0)
    ground = gen.Ground(model)
    off = [(round(x), round(z)) for x, z, _ in pts if not ground.ok(x, z)]
    if off:
        note('%d foods are not on valid ground, for example %r' % (len(off), off[:3]))
    # --- starter patches and lone ambers
    st = targets['starter']
    for cx, cz in st['centres']:
        near = [k for x, z, k in pts if math.hypot(x - cx, z - cz) <= st['radius']]
        if len(near) != st['foods_each'] or near.count('fruit') != st['fruit_each'] or near.count('berry') != st['foods_each'] - st['fruit_each']:
            note('starter patch at (%g, %g): %r, expected %d foods (%d fruit, rest berries)' % (cx, cz, {k: near.count(k) for k in set(near)}, st['foods_each'], st['fruit_each']))
    lone = targets['lone_ambers']
    ambers = [(x, z) for x, z, k in pts if k == 'amber']
    alone = [a for a in ambers if sum(1 for x, z, _ in pts if math.hypot(x - a[0], z - a[1]) <= lone['clear_radius']) == 1]
    if len(alone) != lone['count']:
        note('%d ambers stand alone (nothing within %g studs), expected %d (the hill tops)' % (len(alone), lone['clear_radius'], lone['count']))
    # --- spread rules (same ground model, 256-cell blocks)
    mask = {'rows': model['mask']}
    result = layer_stats.analyse(pts, lay['half'], 256, (10, 20, 30), mask)
    for line in layer_stats.check_targets(result, targets):
        note('layer_stats: ' + line)
    # --- pace: the same rough walker model on today's placement and on the map
    pc = targets['pace']
    older = dump_food_layout.dump(runner, pc['old_layouts'])
    before = cmp.mean_pace([[tuple(p) for p in item['points']] for item in older.values()])
    ratios = cmp.pace_ratios(before, food_pace.pace(pts))
    for key in ('nearest_foods', 'nearest_points', 'value_points', 'around_points'):
        if not pc[key]['min'] <= ratios[key] <= pc[key]['max']:
            note('pace %s is %.2f times today (allowed %.2f to %.2f)' % (key, ratios[key], pc[key]['min'], pc[key]['max']))
    # --- deterministic
    rebuilt = gen.generate(model)['layer'].encode()
    if rebuilt != food_layer_data.TEXT:
        note('regenerating the map gives different text: the terrain or tools/generate_food_layer.py changed; run it with --write and commit')
    # --- the Luau reader FoodService uses
    reader_check(runner, layer, errors)
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    args = ap.parse_args()
    errors = check(args.runner)
    if errors:
        print('FOOD MAP CHECK FAILED:')
        for e in errors:
            print('  -', e)
        return 1
    print('Food map passed: 3,600 foods (berry 2519 / fruit 722 / egg 251 / amber 108) in small clusters of 3 to 5, ground, starter patches, lone ambers, spread targets, pace band, deterministic, Luau reader')
    return 0


if __name__ == '__main__':
    sys.exit(main())
