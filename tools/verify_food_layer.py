#!/usr/bin/env python3
"""BD-1047 (docs/187 B): checks the designed food map (src/shared/FoodLayerData.luau) against tools/targets/food_layer_targets.json.

  * the map decodes (Python and Luau), is 1,000 x 1,000 cells over the 416-stud half arena, and the Luau module and the Python copy
    (tools/food_layer_data.py) hold the same text;
  * counts per kind are exactly the planned ones (3,600 foods in all, same as today's kind mix 70 / 20 / 7 / 3), one food per cell;
  * no two foods closer than the minimum spacing; every food on ground (the FoodService rule, pulled in one stud from every edge);
  * both starter patches near (+-15, 24) are there (9 foods each, 2 berries to 1 fruit) and every lone amber stands alone;
  * tools/layer_stats.py rules: no empty small block, spread near or below random scatter, no big empty zone, short walks to the next egg and amber;
  * the map is deterministic: tools/generate_food_layer.py regenerates the identical text (a change of the terrain or of the generator
    needs `python tools/generate_food_layer.py --runner ... --write` and a commit);
  * src/shared/FoodLayer.luau (the reader FoodService uses) turns the map into the same foods, in the right sectors, in the pinned Luau runner.

    python tools/verify_food_layer.py --runner /path/to/luau
"""
from pathlib import Path
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_food_layers as cmp  # noqa: E402
import dump_food_layout  # noqa: E402
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
    # --- spacing
    search = layer_stats.Buckets([(x, z) for x, z, _ in pts])
    nearest = min(search.nearest(x, z, skip=i) for i, (x, z, _) in enumerate(pts))
    if nearest < targets['min_spacing']:
        note('two foods are only %.2f studs apart (minimum %.1f)' % (nearest, targets['min_spacing']))
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
    print('Food map passed: 3,600 foods (berry 2519 / fruit 722 / egg 251 / amber 108), spacing, ground, starter patches, lone ambers, spread targets, deterministic, Luau reader')
    return 0


if __name__ == '__main__':
    sys.exit(main())
