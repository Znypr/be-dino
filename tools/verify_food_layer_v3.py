#!/usr/bin/env python3
"""BD-1208 (docs/241 W6 to W8): checks the designed food map of the redesigned round island (src/shared/FoodLayerDataV3.luau) against
tools/targets/food_layer_targets_v3.json. tools/verify_food_layer.py calls it, so CI runs it with the old map's checks.

  * the map decodes (Python and Luau), 1,000 x 1,000 cells over the 416-stud half arena, the Luau module and tools/food_layer_data_v3.py hold the same text;
  * the same totals and kind mix as the old map (3,600 foods: berry 2519 / fruit 722 / egg 251 / amber 108), one food per cell;
  * small clusters of 3 to 5, centres and foods spaced like the old map, amber clusters also hold an egg and a fruit, both starter patches (9 foods, 2 berries to
    1 fruit) just outside the plaza edge, four lone ambers;
  * every food on ground where a food may stand on the V3 island: dry land, not steep, NOT on the plaza, NOT on a path or the ring road, NOT inside a landmark
    keep-out disc, and clear of the solid props (tools/world_colliders.py world='v3'); at least the written distance from every path centre line;
  * patches mostly along the paths and the ring road (8 to 40 studs from the centre line) and in the meadow; fruit gathers near the WorldV3 groves; amber and eggs
    prefer rocks, kit landmarks and the ring around the landmark sites;
  * the gap rule on walkable land (the plaza interior, landmark discs and shore strips too narrow for a patch are not counted) and the tools/layer_stats.py rules;
  * the map is deterministic (`python tools/generate_food_layer.py --world v3` regenerates the identical text);
  * src/shared/FoodLayer.luau reads FoodLayerDataV3 (and its starter patches) while Config.WorldV3Enabled is true and the old FoodLayerData while it is false.

    python tools/verify_food_layer_v3.py --runner /path/to/luau [--picture docs/evidence/2026-11-15-world/v3-food-map.png]
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
import food_layer_data  # noqa: E402
import food_layer_data_v3 as data  # noqa: E402
import generate_food_layer as gen  # noqa: E402
import layer_stats  # noqa: E402
import world_colliders  # noqa: E402
import worldlayer  # noqa: E402

TARGETS = ROOT / 'tools' / 'targets' / 'food_layer_targets_v3.json'

READER_LUAU = r'''
local WorldLayer = (function()
@WORLDLAYER@
end)()
local OldData = (function()
@OLD@
end)()
local V3Data = (function()
@DATA@
end)()
local function reader(config)
    return (function()
    local require = function(m) return m end
    local script = {Parent = {WorldLayer = WorldLayer, FoodLayerData = OldData, FoodLayerDataV3 = V3Data, Config = config}}
@FOODLAYER@
    end)()
end
-- flag on: the V3 map and its starter patches
local on = reader({WorldV3Enabled = true})
local layer, reason = on.load()
assert(layer, tostring(reason))
assert(WorldLayer.encode(layer) == (string.gsub(V3Data.Map, "%s", "")), "re-encoding the V3 map gives other text")
local plan, total = on.plan(20, 408)
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
-- flag off (or no Config at all): the old map and the old starter patches, exactly as before
for _, config in {{WorldV3Enabled = false}, {}} do
    local off = reader(config)
    local offLayer = off.load()
    assert(offLayer and WorldLayer.encode(offLayer) == (string.gsub(OldData.Map, "%s", "")), "flag off must read the old map")
    assert(off.isStarter(-15, 24) and off.isStarter(15, 24) and not off.isStarter(81.8, 56.6), "flag off must keep the old starter patches")
end
assert(on.isStarter(V3Data.StarterCentres[1][1], V3Data.StarterCentres[1][2]) and not on.isStarter(-15, 24), "flag on uses the V3 starter patches")
-- a broken map is refused with a reason, never a crash
local bad, why = on.plan(20, 408, "WL1:4:4:416:G")
assert(bad == nil and type(why) == "string", "a short map must be refused")
print("OK")
'''


def reader_check(runner, layer, errors):
    src = READER_LUAU
    for token, path in (('@WORLDLAYER@', 'src/shared/WorldLayer.luau'), ('@OLD@', 'src/shared/FoodLayerData.luau'),
                        ('@DATA@', 'src/shared/FoodLayerDataV3.luau'), ('@FOODLAYER@', 'src/shared/FoodLayer.luau')):
        src = src.replace(token, (ROOT / path).read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'reader_v3.luau'
        path.write_text(src, encoding='utf-8')
        res = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if res.returncode or 'OK' not in res.stdout:
        errors.append('FoodLayer.luau V3 reader failed in Luau: ' + (res.stdout[-400:] + res.stderr[-600:]).strip())
        return
    items, total, starters = [], None, None
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
        errors.append('the Luau reader found %s V3 foods, expected %d' % (total, gen.TOTAL))
    elif expect != got:
        errors.append('the Luau reader and the Python reader disagree about V3 food positions or kinds')
    if starters != 18:
        errors.append('the Luau reader marks %s V3 starter foods, expected 18' % starters)


def measure(pts, ground, info, targets, obstacles):
    """The numbers the world rules are judged on (also printed by --report)."""
    w = targets['world']
    lo, hi = w['band']
    cx, cz = info['centre']
    path_d = [gen.path_distance(info, x, z) for x, z, _ in pts]
    meadow = lambda x, z: -60.0 <= math.degrees(math.atan2(z - cz, x - cx)) <= 30.0  # noqa: E731
    out = {
        'path_distance_min': min(path_d),
        'plaza_distance_min': min(math.hypot(x - cx, z - cz) for x, z, _ in pts),
        'band_share': sum(1 for d in path_d if lo <= d <= hi) / len(pts),
        'band_or_meadow_share': sum(1 for (x, z, _), d in zip(pts, path_d) if lo <= d <= hi or meadow(x, z)) / len(pts),
    }
    groves = info['groves']
    near_grove = lambda x, z: any((x - gx) ** 2 + (z - gz) ** 2 <= w['grove_radius'] ** 2 for gx, gz in groves)  # noqa: E731
    out['all_near_grove'] = sum(1 for x, z, _ in pts if near_grove(x, z)) / len(pts)
    fruit = [(x, z) for x, z, k in pts if k == 'fruit']
    out['fruit_near_grove'] = sum(1 for x, z in fruit if near_grove(x, z)) / len(fruit)
    sites = gen.rare_sites(info, obstacles)
    site_hash = gen.Hash(30.0)
    for x, z in sites:
        site_hash.add(x, z)
    near_rare = lambda x, z: site_hash.nearest(x, z, w['rare_reach']) < w['rare_reach']  # noqa: E731
    out['all_near_rare'] = sum(1 for x, z, _ in pts if near_rare(x, z)) / len(pts)
    for kind in ('amber', 'egg'):
        sel = [(x, z) for x, z, k in pts if k == kind]
        out[kind + '_near_rare'] = sum(1 for x, z in sel if near_rare(x, z)) / len(sel)
    search = layer_stats.Buckets([(x, z) for x, z, _ in pts])
    dist = sorted(search.nearest(x, z) for x, z in ground.lattice(w['gap_step'], 408.0))
    out['gap_max'], out['gap_p95'], out['gap_samples'] = dist[-1], dist[int(0.95 * (len(dist) - 1))], len(dist)
    return out


def check(runner, picture=None, report=False):
    from verify_food_layer import groups
    targets = json.loads(TARGETS.read_text(encoding='utf-8'))
    errors = []
    note = errors.append
    lay = targets['layer']
    try:
        layer = worldlayer.decode(data.TEXT)
    except ValueError as err:
        return ['the Python copy of the V3 map does not decode: %s' % err]
    if (layer.width, layer.height, layer.world_half_width) != (lay['width'], lay['height'], lay['half']):
        note('the V3 map is %d x %d over half width %g, expected %d x %d over %g' % (layer.width, layer.height, layer.world_half_width, lay['width'], lay['height'], lay['half']))
    luau = gen.committed_text(gen.LUAU_PATH_V3)
    if luau is None:
        note('src/shared/FoodLayerDataV3.luau holds no map text')
    elif luau != data.TEXT:
        note('src/shared/FoodLayerDataV3.luau and tools/food_layer_data_v3.py hold different maps; run tools/generate_food_layer.py --world v3 --write')
    if data.TEXT == food_layer_data.TEXT:
        note('the V3 map is the old map')
    # --- counts and mix
    pts = cmp.layer_points(layer)
    counts = {k: sum(1 for p in pts if p[2] == k) for k in targets['counts']}
    if counts != targets['counts']:
        note('V3 kind counts %r differ from the targets %r' % (counts, targets['counts']))
    if len(pts) != targets['total'] or layer.count() != targets['total']:
        note('%d V3 foods in %d cells, expected %d each' % (len(pts), layer.count(), targets['total']))
    share = targets['kind_share']
    for kind in targets['counts']:
        got = counts.get(kind, 0) / max(1, len(pts))
        if abs(got - share[kind]) > share['tolerance']:
            note('V3 %s is %.2f%% of the food, expected %.0f%% +- %.1f' % (kind, got * 100, share[kind] * 100, share['tolerance'] * 100))
    # --- clusters
    cl = targets['clusters']
    search = layer_stats.Buckets([(x, z) for x, z, _ in pts])
    nearest = min(search.nearest(x, z, skip=i) for i, (x, z, _) in enumerate(pts))
    if nearest < cl['foods_spacing_min']:
        note('two V3 foods are only %.2f studs apart (minimum %.1f)' % (nearest, cl['foods_spacing_min']))
    st = targets['starter']
    st_c = [tuple(c) for c in data.STARTER_CENTRES]
    if tuple(st_c) != tuple(gen.v3_starter_centres(dump_info(runner))):
        note('the starter centres of the V3 data %r differ from the generator %r' % (st_c, gen.v3_starter_centres(dump_info(runner))))
    if data.STARTER_RADIUS != st['radius'] or gen.STARTER_RADIUS != st['radius']:
        note('the starter radius is %r (data) / %r (generator), expected %r' % (data.STARTER_RADIUS, gen.STARTER_RADIUS, st['radius']))
    found = groups(pts, cl['link_distance'])
    near_starter = lambda g: any(math.hypot(pts[g[0]][0] - cx, pts[g[0]][1] - cz) <= st['radius'] for cx, cz in st_c)  # noqa: E731
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
        note('%d V3 food groups are not a cluster of %d to %d, a starter patch or a lone amber: sizes %r' % (len(other['bad']), cl['size_min'], cl['size_max'], sorted(other['bad'])[:10]))
    if other['starter'] != len(st_c) or other['lone'] != targets['lone_ambers']['count']:
        note('found %d V3 starter patches and %d lone ambers, expected %d and %d' % (other['starter'], other['lone'], len(st_c), targets['lone_ambers']['count']))
    if small and statistics.fmean(len(g) for g in small) < cl['mean_size_min']:
        note('V3 clusters hold %.2f foods on average, expected at least %.1f' % (statistics.fmean(len(g) for g in small), cl['mean_size_min']))
    centres = [(statistics.fmean(pts[i][0] for i in g), statistics.fmean(pts[i][1] for i in g)) for g in small]
    csearch = layer_stats.Buckets(centres)
    close = min((csearch.nearest(x, z, skip=i) for i, (x, z) in enumerate(centres)), default=math.inf)
    if close < cl['centre_spacing_min']:
        note('two V3 cluster centres are only %.1f studs apart (minimum %.1f)' % (close, cl['centre_spacing_min']))
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
        note('V3 foods of two different groups are only %.1f studs apart (minimum %.1f)' % (between, cl['between_clusters_min']))
    amber_groups = [g for g in small if any(pts[i][2] == 'amber' for i in g)]
    rich = [g for g in amber_groups if any(pts[i][2] == 'egg' for i in g) and any(pts[i][2] == 'fruit' for i in g)]
    if amber_groups and len(rich) / len(amber_groups) < targets['amber_clusters_with_egg_and_fruit_min_share']:
        note('only %d of %d V3 amber clusters also hold an egg and a fruit' % (len(rich), len(amber_groups)))
    # --- ground (the real WorldV3 rules), solid props
    model = dump_food_layout.ground_model(runner, 1.0, 4.0, world='v3')
    obstacles = world_colliders.load(runner, world='v3')
    ground = gen.GroundV3(model)
    info = ground.info
    ground.obstacles = obstacles
    off = [(round(x), round(z)) for x, z, _ in pts if not ground.ok(x, z)]
    if off:
        note('%d V3 foods are not on valid ground (sea, lagoon, plaza, path, landmark keep-out, steep or too near a solid prop), for example %r' % (len(off), off[:3]))
    margin = targets['obstacles']['margin']
    if margin > gen.OBSTACLE_MARGIN:
        note('the target margin %g studs is larger than the generator margin %g' % (margin, gen.OBSTACLE_MARGIN))
    near_props = []
    for x, z, k in pts:
        d, who_ = obstacles.nearest(x, z, margin)
        if who_ is not None and d < margin - 1e-6:
            near_props.append((round(x, 1), round(z, 1), k, round(d, 2), who_))
    if near_props:
        note('%d V3 foods are closer than %g studs to a solid prop, for example %r' % (len(near_props), margin, near_props[:3]))
    # --- starter patches and lone ambers
    for cx, cz in st_c:
        near = [k for x, z, k in pts if math.hypot(x - cx, z - cz) <= st['radius']]
        if len(near) != st['foods_each'] or near.count('fruit') != st['fruit_each'] or near.count('berry') != st['foods_each'] - st['fruit_each']:
            note('V3 starter patch at (%g, %g): %r, expected %d foods (%d fruit, rest berries)' % (cx, cz, {k: near.count(k) for k in set(near)}, st['foods_each'], st['fruit_each']))
        edge = math.hypot(cx - info['centre'][0], cz - info['centre'][1]) - info['plaza']
        if not 0 < edge <= st['plaza_edge_max']:
            note('V3 starter patch at (%g, %g) is %.1f studs from the plaza edge, expected just outside (0 to %g)' % (cx, cz, edge, st['plaza_edge_max']))
    lone = targets['lone_ambers']
    ambers = [(x, z) for x, z, k in pts if k == 'amber']
    alone = [a for a in ambers if sum(1 for x, z, _ in pts if math.hypot(x - a[0], z - a[1]) <= lone['clear_radius']) == 1]
    if len(alone) != lone['count']:
        note('%d V3 ambers stand alone (nothing within %g studs), expected %d (the hill tops)' % (len(alone), lone['clear_radius'], lone['count']))
    # --- world rules (docs/241 W7, W8)
    w = targets['world']
    m = measure(pts, ground, info, targets, obstacles)
    if report:
        print('V3 measures:', json.dumps({k: round(v, 3) for k, v in m.items()}))
    if m['path_distance_min'] < w['path_distance_min']:
        note('a V3 food is only %.1f studs from a path centre line (minimum %.1f)' % (m['path_distance_min'], w['path_distance_min']))
    if m['plaza_distance_min'] < w['plaza_distance_min']:
        note('a V3 food is only %.1f studs from the plaza centre (minimum %.1f, the plaza radius is %g)' % (m['plaza_distance_min'], w['plaza_distance_min'], info['plaza']))
    if m['band_share'] < w['band_share_min']:
        note('only %.0f%% of the V3 foods lie %g to %g studs from a path (minimum %.0f%%)' % (m['band_share'] * 100, w['band'][0], w['band'][1], w['band_share_min'] * 100))
    if m['band_or_meadow_share'] < w['band_or_meadow_share_min']:
        note('only %.0f%% of the V3 foods lie along a path or in the meadow (minimum %.0f%%)' % (m['band_or_meadow_share'] * 100, w['band_or_meadow_share_min'] * 100))
    if m['gap_max'] > w['gap_max'] or m['gap_p95'] > w['gap_p95_max']:
        note('V3 gap rule: farthest walkable spot %.1f studs (max %g), 95th percentile %.1f (max %g)' % (m['gap_max'], w['gap_max'], m['gap_p95'], w['gap_p95_max']))
    if m['fruit_near_grove'] < w['fruit_near_grove_min'] or m['fruit_near_grove'] < w['fruit_near_grove_vs_all_min'] * m['all_near_grove']:
        note('V3 fruit near groves: %.0f%% of the fruit (food in general %.0f%%), expected at least %.0f%% and %.1f times the general share' % (
            m['fruit_near_grove'] * 100, m['all_near_grove'] * 100, w['fruit_near_grove_min'] * 100, w['fruit_near_grove_vs_all_min']))
    for kind in ('amber', 'egg'):
        if m[kind + '_near_rare'] < w[kind + '_near_rare_min'] or m[kind + '_near_rare'] < w['rare_vs_all_min'] * m['all_near_rare']:
            note('V3 %s near rocks and landmarks: %.0f%% (food in general %.0f%%), expected at least %.0f%% and %.1f times the general share' % (
                kind, m[kind + '_near_rare'] * 100, m['all_near_rare'] * 100, w[kind + '_near_rare_min'] * 100, w['rare_vs_all_min']))
    # --- spread rules (walkable ground without the plaza and the landmark discs)
    result = layer_stats.analyse(pts, lay['half'], 256, (10, 20, 30), {'rows': ground.walk_rows})
    for line in layer_stats.check_targets(result, targets):
        note('V3 layer_stats: ' + line)
    # --- deterministic
    rebuilt = gen.generate_v3(model, obstacles)['layer'].encode()
    if rebuilt != data.TEXT:
        note('regenerating the V3 map gives different text: WorldV3 or tools/generate_food_layer.py changed; run it with --world v3 --write and commit')
    # --- the Luau reader FoodService uses
    reader_check(runner, layer, errors)
    if picture:
        draw(Path(picture), model, ground, info, pts)
    return errors


_INFO = {}


def dump_info(runner):
    """The WorldV3 geometry (cached): only needed to recompute the starter centres."""
    if 'info' not in _INFO:
        _INFO['info'] = dump_food_layout.ground_model(runner, 8.0, 8.0, world='v3')['v3']
    return _INFO['info']


def draw(path, model, ground, info, pts, px_per_stud=1.5):
    """Top-down picture: sea, land shaded by height, plaza and paths, landmark discs, groves, and the foods by kind (docs/evidence/2026-11-15-world/v3-food-map.png)."""
    from PIL import Image, ImageDraw
    arena = model['arena']
    size = int(2 * arena * px_per_stud)
    img = Image.new('RGB', (size, size), (60, 150, 200))
    d = ImageDraw.Draw(img)
    f = lambda x, z: ((x + arena) * px_per_stud, (z + arena) * px_per_stud)  # noqa: E731
    hs, hc = model['height'], model['hcell']
    n = len(hs)
    cell_px = hc * px_per_stud
    cx, cz = info['centre']
    for iz in range(n):
        for ix in range(n):
            x, z = -arena + (ix + 0.5) * hc, -arena + (iz + 0.5) * hc
            h = hs[iz][ix]
            if h < 0 or ground_is_sea(model, x, z):
                depth = min(1.0, max(0.0, -h) / 6)
                col = (int(110 - 50 * depth), int(190 - 40 * depth), int(215 - 25 * depth))
            else:
                shade = max(0.0, min(1.0, h / 70))
                col = (int(150 - 60 * shade), int(196 - 40 * shade), int(100 - 30 * shade))
            d.rectangle((ix * cell_px, iz * cell_px, (ix + 1) * cell_px, (iz + 1) * cell_px), fill=col)
    pathrows = model['path']
    pm = len(pathrows)
    pcell = 2 * arena / pm
    for iz in range(0, pm, 2):
        row = pathrows[iz]
        for ix in range(0, pm, 2):
            if row[ix] == '1':
                x0, z0 = f(-arena + ix * pcell, -arena + iz * pcell)
                d.rectangle((x0, z0, x0 + 2 * px_per_stud, z0 + 2 * px_per_stud), fill=(226, 204, 150))
    x0, z0 = f(cx - info['plaza'], cz - info['plaza'])
    x1, z1 = f(cx + info['plaza'], cz + info['plaza'])
    d.ellipse((x0, z0, x1, z1), fill=(226, 204, 150), outline=(150, 120, 70))
    for lx, lz, r in ground.discs:
        a, b = f(lx - r, lz - r)
        c, e = f(lx + r, lz + r)
        d.ellipse((a, b, c, e), outline=(120, 40, 160), width=2)
    for gx, gz in info['groves']:
        a, b = f(gx - 40, gz - 40)
        c, e = f(gx + 40, gz + 40)
        d.ellipse((a, b, c, e), outline=(20, 90, 40), width=1)
    colours = {'berry': (214, 40, 60), 'fruit': (250, 150, 20), 'egg': (255, 255, 255), 'amber': (255, 215, 0)}
    sizes = {'berry': 1.4, 'fruit': 2.0, 'egg': 2.4, 'amber': 3.2}
    for kind in ('berry', 'fruit', 'egg', 'amber'):
        for x, z, k in pts:
            if k != kind:
                continue
            a, b = f(x, z)
            r = sizes[kind]
            d.ellipse((a - r, b - r, a + r, b + r), fill=colours[kind], outline=(60, 30, 30) if kind != 'berry' else None)
    for sx, sz in data.STARTER_CENTRES:
        a, b = f(sx, sz)
        d.ellipse((a - 22, b - 22, a + 22, b + 22), outline=(0, 0, 0), width=2)
    d.rectangle((6, 6, 560, 62), fill=(255, 255, 255))
    d.text((12, 10), 'Be Dino! V3 island food map (BD-1208): 3,600 foods, berry red / fruit orange / egg white / amber gold', fill=(0, 0, 0))
    d.text((12, 26), 'tan = plaza, paths, ring road; purple circles = landmark keep-outs; green circles = groves; black rings = starter patches', fill=(0, 0, 0))
    d.text((12, 42), 'z grows downwards, x to the right; whole 832 stud arena', fill=(0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print('picture:', path)


def ground_is_sea(model, x, z):
    """True where the 1 stud ground rule says no ground and the height is at or below the water line (sea and lagoon colouring helper)."""
    n = len(model['mask'])
    cell = 2 * model['arena'] / n
    ix, iz = int((x + model['arena']) / cell), int((z + model['arena']) / cell)
    return False if not (0 <= ix < n and 0 <= iz < n) else (model['mask'][iz][ix] == '0' and model['height'][int((z + model['arena']) / model['hcell'])][int((x + model['arena']) / model['hcell'])] < 0.4)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    ap.add_argument('--picture', help='also draw the top-down picture of the map to this PNG')
    ap.add_argument('--report', action='store_true', help='print the measured world numbers')
    args = ap.parse_args()
    errors = check(args.runner, args.picture, args.report)
    if errors:
        print('V3 FOOD MAP CHECK FAILED:')
        for e in errors:
            print('  -', e)
        return 1
    print('V3 food map passed: 3,600 foods (berry 2519 / fruit 722 / egg 251 / amber 108) in small clusters of 3 to 5 on the round island: dry land only, off the plaza, paths and landmark discs, clear of solid props, '
          'along the paths and in the meadow, fruit at the groves, amber and eggs at rocks and landmarks, starter patches at the plaza edge, gap rule, spread targets, deterministic, Luau reader (flag on and off)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
