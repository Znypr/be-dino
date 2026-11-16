#!/usr/bin/env python3
"""BD-1238 (docs/241 W6 + W7): checks the V3 food map with the food at matching hosts (src/shared/FoodLayerDataV3Hosts.luau, tools/food_hosts.py)
against tools/targets/food_hosts_targets.json.

  * the map decodes, the Luau module and tools/food_layer_data_v3_hosts.py hold the same text, it is not the plain V3 map, and regenerating it gives the
    identical text (deterministic; a change of the V3 map, World V3 or the toon bushes needs `python tools/food_hosts.py --write`);
  * FAIRNESS: the same 3,600 foods and kind counts as the V3 map, and the same count of every kind in every one of the five zones; the two starter patches and
    the four lone hill-top ambers are exactly the V3 ones;
  * every food on valid V3 food ground and clear of the solid props of the toon island; no two foods closer than the minimum spacing; the gap rule;
  * HOSTS, measured from the world geometry (not from the generator's slots): the share of berries inside the soft edge of a round bush, fruit under a tree
    crown, amber against a rock or at a landmark edge, eggs against a rock, at a tree foot or at a landmark edge, each at least the target;
  * src/shared/FoodLayer.luau reads the hosts map only while FoodHostsEnabled, ToonWorldEnabled and WorldV3Enabled are all true (else the V3 map, as before),
    with the V3 starter patches.

    python tools/verify_food_hosts.py --runner <luau.exe> [--picture docs/evidence/2026-11-16-food-hosts/map.png] [--report]
"""
from pathlib import Path
import argparse
import json
import math
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_food_layers as cmp  # noqa: E402
import food_hosts as fh  # noqa: E402
import food_layer_data_v3 as v3data  # noqa: E402
import food_layer_data_v3_hosts as data  # noqa: E402
import food_layer_data_v3_hosts_veg2 as data_veg2  # noqa: E402
import generate_food_layer as gen  # noqa: E402
import layer_stats  # noqa: E402
import worldlayer  # noqa: E402

TARGETS = ROOT / 'tools' / 'targets' / 'food_hosts_targets.json'

READER_LUAU = r'''
local WorldLayer = (function()
@WORLDLAYER@
end)()
local OldData = (function()
@OLD@
end)()
local V3Data = (function()
@V3@
end)()
local Hosts = (function()
@HOSTS@
end)()
local HostsVeg2 = (function()
@HOSTSVEG2@
end)()
local function reader(config)
    return (function()
    local require = function(m) return m end
    local script = {Parent = {WorldLayer = WorldLayer, FoodLayerData = OldData, FoodLayerDataV3 = V3Data, FoodLayerDataV3Hosts = Hosts, FoodLayerDataV3HostsVeg2 = HostsVeg2, Config = config}}
@FOODLAYER@
    end)()
end
local function text(r) local layer = r.load() assert(layer) return WorldLayer.encode(layer) end
local strip = function(s) return (string.gsub(s, "%s", "")) end
local on = reader({WorldV3Enabled = true, ToonWorldEnabled = true, FoodHostsEnabled = true})
assert(text(on) == strip(Hosts.Map), "all three flags on must read the hosts map")
assert(text(reader({WorldV3Enabled = true, ToonWorldEnabled = true, FoodHostsEnabled = true, VegetationV2Enabled = true})) == strip(HostsVeg2.Map), "with vegetation v2: the veg2 hosts map")
assert(text(reader({WorldV3Enabled = true, ToonWorldEnabled = true, FoodHostsEnabled = false, VegetationV2Enabled = true})) == strip(V3Data.Map), "vegetation v2 without hosts: the V3 map")
assert(text(reader({WorldV3Enabled = true, ToonWorldEnabled = true, FoodHostsEnabled = false})) == strip(V3Data.Map), "hosts flag off: the V3 map")
assert(text(reader({WorldV3Enabled = true, ToonWorldEnabled = false, FoodHostsEnabled = true})) == strip(V3Data.Map), "toon off: the V3 map (the bushes stand elsewhere)")
assert(text(reader({WorldV3Enabled = false, ToonWorldEnabled = true, FoodHostsEnabled = true})) == strip(OldData.Map), "World V3 off: the old map")
local plan, total = on.plan(20, 408)
assert(plan and total == 3600, tostring(total))
local starters = 0
for _, items in plan do for _, item in items do if item.starter then starters += 1 end end end
assert(starters == 18, "the hosts map keeps the 18 starter foods: " .. starters)
print("OK")
'''


def reader_check(runner, errors):
    src = READER_LUAU
    for token, path in (('@WORLDLAYER@', 'src/shared/WorldLayer.luau'), ('@OLD@', 'src/shared/FoodLayerData.luau'), ('@V3@', 'src/shared/FoodLayerDataV3.luau'),
                        ('@HOSTSVEG2@', 'src/shared/FoodLayerDataV3HostsVeg2.luau'), ('@HOSTS@', 'src/shared/FoodLayerDataV3Hosts.luau'), ('@FOODLAYER@', 'src/shared/FoodLayer.luau')):
        src = src.replace(token, (ROOT / path).read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'reader_hosts.luau'
        path.write_text(src, encoding='utf-8')
        res = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if res.returncode or 'OK' not in res.stdout:
        errors.append('FoodLayer.luau hosts reader failed in Luau: ' + (res.stdout[-400:] + res.stderr[-600:]).strip())


def inside_ellipse(x, z, cx, cz, rx, rz, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    dx, dz = x - cx, z - cz
    lx, lz = c * dx - s * dz, s * dx + c * dz   # into the prop's own frame (inverse of fh.ring)
    return (lx / rx) ** 2 + (lz / rz) ** 2 <= 1.0


def host_kind_at(x, z, kind, geo, t):
    """The kind of matching host the food at (x, z) sits at (from the world geometry), or None."""
    near = geo.near(x, z)
    if kind == 'berry':
        for p, e in near['bush']:
            s = p['scale']
            if inside_ellipse(x, z, p['x'], p['z'], e[1] * s / 2 + t['bush_edge'], e[3] * s / 2 + t['bush_edge'], p['yaw']):
                return 'bush'
        return None
    if kind == 'fruit':
        for tx, tz, trunk_r, crown in near['tree']:
            if math.hypot(x - tx, z - tz) <= crown:
                return 'tree'
        return None
    for p, e in near['rock']:
        s = p['scale']
        if inside_ellipse(x, z, p['x'], p['z'], e[1] * s / 2 + t['rock_reach'], e[3] * s / 2 + t['rock_reach'], p['yaw']):
            return 'rock'
    for lx, lz, r in geo.landmarks:
        if r <= math.hypot(x - lx, z - lz) <= r + t['landmark_band']:
            return 'landmark'
    if kind == 'egg':
        for tx, tz, trunk_r, crown in near['tree']:
            if math.hypot(x - tx, z - tz) <= trunk_r + t['tree_foot_reach']:
                return 'treefoot'
    return None


class Geometry:
    def __init__(self, props, cols, ext, info):
        self.cells = {}
        for p in props:
            pid = p['id']
            if p['layer'] == 'shrub' and pid in fh.BUSH_IDS:
                self._add('bush', p['x'], p['z'], (p, ext[pid]))
            elif p['layer'] in ('tree', 'colossal') and pid.startswith(fh.TREE_PREFIXES):
                e, trunk, s = ext[pid], cols[pid][0], p['scale']
                c, sn = math.cos(p['yaw']), math.sin(p['yaw'])
                tx, tz = p['x'] + c * trunk[0] * s + sn * trunk[2] * s, p['z'] - sn * trunk[0] * s + c * trunk[2] * s
                self._add('tree', tx, tz, (tx, tz, max(trunk[3], trunk[5]) * s / 2, min(e[1], e[3]) * s / 2))
            elif p['layer'] in ('rock', 'landmark'):
                self._add('rock', p['x'], p['z'], (p, ext[pid]))
        self.landmarks = []
        for _, lx, lz in info['landmarks']:
            r = max((r for x, z, r, every in info['keepouts'] if every and math.hypot(x - lx, z - lz) < 0.5), default=34.0)
            self.landmarks.append((lx, lz, r))

    def _add(self, kind, x, z, item):
        self.cells.setdefault((kind, math.floor(x / 32), math.floor(z / 32)), []).append(item)

    def near(self, x, z):
        cx, cz = math.floor(x / 32), math.floor(z / 32)
        out = {}
        for kind in ('bush', 'tree', 'rock'):
            out[kind] = [it for dx in (-1, 0, 1) for dz in (-1, 0, 1) for it in self.cells.get((kind, cx + dx, cz + dz), ())]
        return out


def check(runner, picture=None, report=False):
    targets = json.loads(TARGETS.read_text(encoding='utf-8'))
    errors = []
    note = errors.append
    try:
        layer = worldlayer.decode(data.TEXT)
    except ValueError as err:
        return ['the Python copy of the hosts map does not decode: %s' % err]
    luau = gen.committed_text(fh.LUAU_PATH)
    if luau is None:
        note('src/shared/FoodLayerDataV3Hosts.luau holds no map text')
    elif luau != data.TEXT:
        note('src/shared/FoodLayerDataV3Hosts.luau and tools/food_layer_data_v3_hosts.py hold different maps; run tools/food_hosts.py --write')
    if data.TEXT == v3data.TEXT:
        note('the hosts map is the plain V3 map')
    if (layer.width, layer.height, layer.world_half_width) != (gen.WIDTH, gen.WIDTH, gen.ARENA):
        note('the hosts map is %d x %d over %g, expected %d x %d over %g' % (layer.width, layer.height, layer.world_half_width, gen.WIDTH, gen.WIDTH, gen.ARENA))
    pts = cmp.layer_points(layer)
    v3pts = cmp.layer_points(worldlayer.decode(v3data.TEXT))
    # --- fairness
    counts = {k: sum(1 for p in pts if p[2] == k) for k in gen.COUNTS}
    if counts != gen.COUNTS or len(pts) != gen.TOTAL or layer.count() != gen.TOTAL:
        note('hosts map kind counts %r (%d cells), expected %r' % (counts, layer.count(), gen.COUNTS))
    result = fh.build(runner)
    ground, info = result['ground'], result['ground'].info
    zc, vzc = fh.zone_counts([p + (None,) for p in pts], info['centre']), fh.zone_counts([p + (None,) for p in v3pts], info['centre'])
    if zc != vzc:
        diff = sorted(k for k in set(zc) | set(vzc) if zc.get(k) != vzc.get(k))
        note('the count of a kind in a zone differs from the V3 map: %s' % ', '.join('%s %s %s -> %s' % (z, k, vzc.get((z, k)), zc.get((z, k))) for z, k in diff[:6]))
    for cx, cz in v3data.STARTER_CENTRES:
        a = sorted(p for p in pts if math.hypot(p[0] - cx, p[1] - cz) <= v3data.STARTER_RADIUS)
        b = sorted(p for p in v3pts if math.hypot(p[0] - cx, p[1] - cz) <= v3data.STARTER_RADIUS)
        if a != b:
            note('the starter patch at (%g, %g) differs from the V3 map' % (cx, cz))
    lone = lambda P: sorted(p for p in P if p[2] == 'amber' and sum(1 for q in P if math.hypot(q[0] - p[0], q[1] - p[1]) <= fh.LONE_CLEAR) == 1)  # noqa: E731
    if lone(pts) != lone(v3pts):
        note('the lone hill-top ambers differ from the V3 map: %r vs %r' % (lone(pts)[:4], lone(v3pts)[:4]))
    # --- ground, props, spacing, gaps
    bad = [(round(x), round(z)) for x, z, _ in pts if not ground.ok(x, z)]
    if bad:
        note('%d hosts-map foods are not on valid V3 food ground or too near a solid prop of the toon island, for example %r' % (len(bad), bad[:3]))
    search = layer_stats.Buckets([(x, z) for x, z, _ in pts])
    nearest = min(search.nearest(x, z, skip=i) for i, (x, z, _) in enumerate(pts))
    if nearest < targets['spacing_min']:
        note('two hosts-map foods are only %.2f studs apart (minimum %.1f)' % (nearest, targets['spacing_min']))
    g, p95 = fh.gap([p + (None,) for p in pts], ground)
    if g > targets['gap_max'] or p95 > targets['gap_p95_max']:
        note('hosts-map gap rule: farthest walkable spot %.1f studs (max %g), 95th percentile %.1f (max %g)' % (g, targets['gap_max'], p95, targets['gap_p95_max']))
    # --- hosts, from the world geometry
    geo = Geometry(*_dump(runner), info)
    t = targets['hosts']
    shares = {}
    for kind in gen.COUNTS:
        sel = [(x, z) for x, z, k in pts if k == kind]
        shares[kind] = sum(1 for x, z in sel if host_kind_at(x, z, kind, geo, t)) / len(sel)
        v3sel = [(x, z) for x, z, k in v3pts if k == kind]
        shares['v3_' + kind] = sum(1 for x, z in v3sel if host_kind_at(x, z, kind, geo, t)) / len(v3sel)
        if shares[kind] < t['share_min'][kind]:
            note('only %.0f%% of the %s sit at a matching host (minimum %.0f%%)' % (shares[kind] * 100, kind, t['share_min'][kind] * 100))
    if report:
        print('hosts-map measures:', json.dumps({k: round(v, 3) for k, v in shares.items()}), 'gap %.1f / p95 %.1f, nearest %.2f' % (g, p95, nearest))
    # --- deterministic, reader
    if result['layer'].encode() != data.TEXT:
        note('regenerating the hosts map gives different text: the V3 map, World V3, the toon bushes or tools/food_hosts.py changed; run tools/food_hosts.py --write')
    reader_check(runner, errors)
    if picture:
        draw(Path(picture), pts, geo, info)
    return errors


_DUMP = {}


def _dump(runner):
    if runner not in _DUMP:
        import world_colliders
        props, cols, ext, _ = world_colliders.dump(runner, world='v3', toon=True, veg2=fh.VEG2)
        _DUMP[runner] = (props, cols, ext)
    return _DUMP[runner]


def draw(path, pts, geo, info, half=416.0, px=1.5):
    """A top-down picture: bushes green, tree crowns dark green, rocks grey, foods in their kind colour (for the evidence folder)."""
    from PIL import Image, ImageDraw
    size = int(2 * half * px)
    img = Image.new('RGB', (size, size), (236, 232, 214))
    d = ImageDraw.Draw(img)
    to = lambda x, z: ((x + half) * px, (z + half) * px)  # noqa: E731
    for (kind, _, _), items in geo.cells.items():
        for it in items:
            if kind == 'tree':
                (x, y), r = to(it[0], it[1]), it[3] * px
                d.ellipse((x - r, y - r, x + r, y + r), outline=(40, 110, 50))
            else:
                p, e = it
                (x, y), r = to(p['x'], p['z']), max(e[1], e[3]) * p['scale'] / 2 * px
                d.ellipse((x - r, y - r, x + r, y + r), fill=(150, 200, 120) if kind == 'bush' else (140, 140, 140))
    colour = {'berry': (70, 80, 200), 'fruit': (230, 120, 30), 'egg': (40, 170, 170), 'amber': (220, 170, 20)}
    for x, z, k in pts:
        cx, cy = to(x, z)
        d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=colour[k])
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runner', required=True, help='pinned luau.exe (docs/160)')
    ap.add_argument('--picture', help='also draw the map (PNG)')
    ap.add_argument('--report', action='store_true', help='print the measures')
    ap.add_argument('--veg2', action='store_true', help='BD-1239 follow-up: check the vegetation v2 hosts map (FoodLayerDataV3HostsVeg2)')
    args = ap.parse_args()
    if args.veg2:
        global data
        fh.set_mode(True)
        data = data_veg2
    errors = check(args.runner, args.picture, args.report)
    for e in errors:
        print('FAIL:', e)
    print('food hosts map: %s' % ('OK' if not errors else '%d problem(s)' % len(errors)))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
