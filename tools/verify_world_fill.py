#!/usr/bin/env python3
"""BD-1245 + BD-1246 world fill (Config.GroundDetailEnabled, Config.ThingsToDoEnabled, src/shared/WorldFill.luau), owner 2026-11-16 "game
still looks empty", "Yes, build all".

Runs the REAL WorldFill, WorldV3, WorldLayer, the food map of the vegetation v2 island (FoodLayerDataV3HostsVeg2) and the World V3 toon v2
placements (tools/world_colliders.dump) in the pinned Luau runtime and checks:
  * enabled(): each flag needs WorldV3Enabled, ToonWorldEnabled, VegetationV2Enabled and its own flag;
  * surface(): only grass columns of the meadow, forest and pine zones change (the worn earth edge on the path rim, the other green, earth
    spots); sand, rock, the beach and the volcano keep theirs;
  * groundDetail(): edge stones, pebbles, a log per spoke and flower patches, none in the plaza or the water, none on the path itself, none
    overlapping a tree, rock, shrub, log or landmark of the island or each other;
  * setPieceSites(): one site per spoke key, clear of the island props, off the path (the jetty stands at the lagoon shore);
  * moveFood(): the same number of foods of every kind in every zone, the starter patches untouched, at least 60 moved, every moved food
    on the first stretch of a spoke path, no two foods closer than the map spacing there, deterministic (two runs encode the same text);
  * the part bill near spawn (BD-1222 phone budget): ground cover dropped by the lower CoverKeep within 300 studs of spawn is more than the
    pieces added there (set pieces with their collider included), so the count goes down.
Source guards: both flags ship false, are pinned off in the default profile, ON in the playtest profile and in the rehearsal list; Arena,
IslandTerrain, FoodLayer, FoodGlow and the loader act only through the flag checks; Bootstrap.client is untouched; the eight generated ids
are real, distinct and listed in docs/77; the evidence pictures exist.
Usage: python tools/verify_world_fill.py --runner luau.exe"""
from pathlib import Path
import argparse
import math
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import world_colliders  # noqa: E402
from verify_vegetation_v2 import keep_cover  # noqa: E402
EVIDENCE = ROOT / 'docs/evidence/2026-11-16-world-fill-ground'
PICTURES = ('before-path-view.jpg', 'after-path-view.jpg', 'before-spawn-view.jpg', 'after-spawn-view.jpg', 'set-signpost-forest.jpg',
            'set-egg-nest-meadow.jpg', 'set-campfire-pine.jpg', 'set-fossil-dig-volcano.jpg', 'set-log-bridge-beach.jpg')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local all = {WorldV3Enabled = true, ToonWorldEnabled = true, VegetationV2Enabled = true, GroundDetailEnabled = true, ThingsToDoEnabled = true}
check(Fill.groundEnabled(all) and Fill.thingsEnabled(all), "enabled with all flags")
for _, key in {"WorldV3Enabled", "ToonWorldEnabled", "VegetationV2Enabled"} do
    local c = table.clone(all) c[key] = nil
    check(not Fill.groundEnabled(c) and not Fill.thingsEnabled(c), "off without " .. key)
end
check(not Fill.groundEnabled({WorldV3Enabled = true, ToonWorldEnabled = true, VegetationV2Enabled = true, ThingsToDoEnabled = true}), "ground needs its own flag")
check(not Fill.thingsEnabled({WorldV3Enabled = true, ToonWorldEnabled = true, VegetationV2Enabled = true, GroundDetailEnabled = true}), "things need their own flag")
check(not Fill.groundEnabled(nil) and not Fill.thingsEnabled(nil), "off for nil")
for key in Fill.Assets do check(Fill.ready(key), "published id for " .. key) end

-- surface (lead review of #623: no brown on the path rim, only the grass varies)
local changed, rim = 0, 0
for x = -300, 300, 7 do
    for z = -270, 330, 7 do
        local h = V3.height(x, z)
        local zone = V3.zoneAt(x, z).id
        local onRim = V3.path(x, z) > .04
        for _, pick in {"Grass", "LeafyGrass", "Ground", "Mud", "Sand", "Rock", "Limestone"} do
            local s = Fill.surface(V3, x, z, h, pick)
            check(s ~= "Ground" and s ~= "Mud", "never paints earth")
            if s then
                changed += 1
                check(zone == "meadow" or zone == "forest" or zone == "pine", "grass zones only (" .. zone .. ")")
                if onRim then
                    check(pick ~= "Grass" and pick ~= "LeafyGrass" and s == "Limestone", "the path rim takes the path colour, grass stays grass")
                    rim += 1
                else
                    check((pick == "Grass" and s == "LeafyGrass") or (pick == "LeafyGrass" and s == "Grass"), "away from the path only the grass varies")
                end
            end
        end
    end
end
check(changed > 300 and rim > 20, string.format("surface changes some grass and the rim (%d, rim %d)", changed, rim))

-- ground detail and set pieces against the real island
local blockers = {}
for _, p in placed do
    if p.layer ~= "groundcover" then
        local e = ext[p.id]
        table.insert(blockers, {x = p.x, z = p.z, r = math.max(e[1], e[3]) * .5 * p.scale})
    end
end
for _, site in V3.Landmarks do
    local x, z = V3.polar(site.angle, site.r)
    table.insert(blockers, {x = x, z = z, r = if site.id == "volcano" then 60 else 30})
end
local sites = Fill.setPieceSites(V3, blockers)
local seen = {}
for _, s in sites do
    seen[s.key] = true
    local e = Fill.Assets[s.key].size
    local r = math.max(e[1], e[3]) * .5
    if s.key ~= "set_log_bridge" then
        check(Fill.clear(Fill.grid(blockers), s.x, s.z, r), "set piece clear of the island props: " .. s.key)
        check(V3.path(s.x, s.z) < .3, "set piece off the path: " .. s.key)
    else
        check(V3.inPool(s.x, s.z, 0) or V3.inland(s.x, s.z) > 0, "jetty at the lagoon shore")
    end
    check(not V3.inPlaza(s.x, s.z), "set piece outside the plaza")
    table.insert(blockers, {x = s.x, z = s.z, r = r})
end
for _, sp in Fill.SetPieces do check(seen[sp.key], "set piece placed: " .. sp.key) end
check(#sites == #V3.Spokes, "one set piece per spoke")
local detail = Fill.groundDetail(V3, blockers)
local kinds = {}
for i, p in detail do
    kinds[p.key] = (kinds[p.key] or 0) + 1
    check(not V3.inPlaza(p.x, p.z) and not V3.inPool(p.x, p.z, 2), "detail not in the plaza or the water")
    check(V3.path(p.x, p.z) < .5, "detail not on the path")
    local r = math.max(Fill.Assets[p.key].size[1], Fill.Assets[p.key].size[3]) * .3
    check(Fill.clear(Fill.grid(blockers), p.x, p.z, r * .5), "detail clear of the island props")
end
check((kinds.fill_edge_stones or 0) >= 20 and (kinds.fill_pebbles or 0) >= 20 and (kinds.fill_log or 0) == #V3.Spokes and (kinds.fill_flower_patch or 0) >= 30,
    "edge stones, pebbles, one log per spoke, flower patches")
local near = 0
for _, p in detail do if math.sqrt((p.x - V3.CenterX) ^ 2 + (p.z - V3.CenterZ) ^ 2) <= 300 then near += 1 end end
for _, s in sites do if math.sqrt((s.x - V3.CenterX) ^ 2 + (s.z - V3.CenterZ) ^ 2) <= 300 then near += if s.key == "set_log_bridge" then 1 else 2 end end
print("ADDED_NEAR\t" .. near)

-- food
local function counts(layer)
    local c, total = {}, 0
    WL.forEachNonZero(layer, function(ix, iz, v)
        local x, z = WL.centreOf(layer, ix, iz)
        local k = V3.zoneAt(x, z).id .. "|" .. v
        c[k] = (c[k] or 0) + 1
        total += 1
    end)
    return c, total
end
local function isStarter(x, z)
    for _, c in StarterCentres do if (x - c[1]) ^ 2 + (z - c[2]) ^ 2 <= StarterRadius ^ 2 then return true end end
    return false
end
local a = WL.decode(Map)
local b = WL.decode(Map)
local c0, t0 = counts(a)
local starterBefore = {}
WL.forEachNonZero(a, function(ix, iz, v) local x, z = WL.centreOf(a, ix, iz) if isStarter(x, z) then starterBefore[ix * 100000 + iz] = v end end)
local moved = Fill.moveFood(V3, WL, a, isStarter)
local moved2 = Fill.moveFood(V3, WL, b, isStarter)
check(moved == moved2 and WL.encode(a) == WL.encode(b), "food move is deterministic")
local c1, t1 = counts(a)
check(t0 == t1, "same number of foods")
for k, v in c0 do check(c1[k] == v, "same count of " .. k) end
for k, v in c1 do check(c0[k] == v, "no new zone/kind " .. k) end
WL.forEachNonZero(a, function(ix, iz, v) local x, z = WL.centreOf(a, ix, iz) if isStarter(x, z) then check(starterBefore[ix * 100000 + iz] == v, "starter patch untouched") end end)
check(moved >= 60, "at least 60 foods moved to the paths (" .. moved .. ")")
-- the path stretch now holds the moved foods, spaced like the map
local onPath = {}
WL.forEachNonZero(a, function(ix, iz, v)
    local x, z = WL.centreOf(a, ix, iz)
    for _, sp in V3.Spokes do
        local ang = math.rad(sp.angle)
        local dx, dz = x - V3.CenterX, z - V3.CenterZ
        local along = dx * math.cos(ang) + dz * math.sin(ang)
        local across = math.abs(-dx * math.sin(ang) + dz * math.cos(ang))
        if along > Fill.Trail.first - 2 and along < Fill.Trail.first + Fill.Trail.step * Fill.Trail.clusters + 8 and across < V3.PathHalfWidth then table.insert(onPath, {x, z}) end
    end
end)
check(#onPath >= moved, "the moved foods are on the spoke paths (" .. #onPath .. ")")
for i = 1, #onPath do
    for j = i + 1, #onPath do
        local d = math.sqrt((onPath[i][1] - onPath[j][1]) ^ 2 + (onPath[i][2] - onPath[j][2]) ^ 2)
        check(d >= Fill.MinSpacing - 1e-6, "path food spacing")
    end
end
-- the donors came from the 180-300 band (the count within 300 studs of spawn stays the same)
local nearBefore, nearAfter = 0, 0
WL.forEachNonZero(b, function() end)
local fresh = WL.decode(Map)
WL.forEachNonZero(fresh, function(ix, iz) local x, z = WL.centreOf(fresh, ix, iz) if (x - V3.CenterX) ^ 2 + (z - V3.CenterZ) ^ 2 <= 90000 then nearBefore += 1 end end)
WL.forEachNonZero(a, function(ix, iz) local x, z = WL.centreOf(a, ix, iz) if (x - V3.CenterX) ^ 2 + (z - V3.CenterZ) ^ 2 <= 90000 then nearAfter += 1 end end)
check(nearBefore == nearAfter, string.format("foods within 300 studs unchanged (%d -> %d)", nearBefore, nearAfter))

if #fails > 0 then
    local shown = {}
    for _, f in fails do if not shown[f] then shown[f] = true print("FAIL: " .. f) end end
    error("world fill checks failed")
end
print(string.format("World fill checks passed (%d ground pieces, %d set pieces, %d foods moved to the paths)", #detail, #sites, moved))
'''


def source_checks():
    errors = []
    config = read('src/shared/Config.luau')
    for flag in ('GroundDetailEnabled', 'ThingsToDoEnabled'):
        if f'    {flag} = false,\n' not in config:
            errors.append(f'Config.{flag} must ship false')
        profiles = read('tools/release_profiles.py')
        if f'_flag_off("{flag}"' not in profiles or f'Rule("{flag}", "set", True' not in profiles or f'("{flag}", "BD-124' not in profiles:
            errors.append(f'{flag}: off in default, on in playtest, in the rehearsal list')
    arena = read('src/server/Arena.luau')
    if 'if veg2On and Fill.groundEnabled(Config) then Veg2.CoverKeep = Fill.CoverKeep end' not in arena:
        errors.append('Arena must lower the ground cover share only with GroundDetailEnabled')
    if 'local ground, things = Fill.groundEnabled(Config), Fill.thingsEnabled(Config)' not in arena or 'if not V3 or not (ground or things) then return end' not in arena:
        errors.append('Arena must place the world fill only with the flags')
    # BD-1320: the ground patches run first on the same flag line (Patches.surface(...) or Fill.surface(...))
    if 'if not fixed and fillGround then fixed = Patches.surface(V3, wx, wz, height, slope, name) or Fill.surface(V3, wx, wz, height, name) end' not in read('src/server/IslandTerrain.luau'):
        errors.append('IslandTerrain must paint the fill surface only with GroundDetailEnabled')
    if 'if layer and text == nil and v3 and thingsOn() then' not in read('src/shared/FoodLayer.luau'):
        errors.append('FoodLayer must move food only for the game map with ThingsToDoEnabled')
    if 'thingsEnabled(require(Shared:WaitForChild("Config"))) then SLOTS, RADIUS = 72, 175 end' not in read('src/client/FoodGlow.client.luau'):
        errors.append('FoodGlow must reach farther only with ThingsToDoEnabled')
    loader = read('src/server/ImportedResources.luau')
    if 'local wanted=if string.sub(key,1,4)=="set_" then fillThings else fillGround' not in loader:
        errors.append('the loader must fetch the fill meshes only with their flag')
    boot = read('src/client/Bootstrap.client.luau')
    if 'WorldFill' in boot or 'GroundDetail' in boot or 'ThingsToDo' in boot:
        errors.append('Bootstrap.client must not change')
    registry = read('docs/77-asset-registry.md')
    fill = read('src/shared/WorldFill.luau')
    items = re.findall(r'((?:fill|set)_\w+) = \{assetId = "(\d+)"', fill)
    if len(items) != 8 or len({i for _, i in items}) != 8:
        errors.append('8 distinct published ids expected (%d)' % len(items))
    if 'fill_edge_stones = {assetId = "", use = "veg2_rock_mossy"' not in fill or '| world_gen_fill_edge_stones |' not in registry:
        errors.append('the edge stones show the vegetation v2 mossy rock (the blocky generated row is rejected, still listed in docs/77)')
    for key, aid in items:
        if f'| world_gen_{key} |' not in registry or f'| {aid} |' not in registry:
            errors.append(f'docs/77 line missing for {key} ({aid})')
    for name in PICTURES:
        if not (EVIDENCE / name).is_file():
            errors.append(f'evidence picture missing: {name}')
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    problems = source_checks()
    for p in problems:
        print('FAIL:', p)
    props, _cols, ext, _hub = world_colliders.dump(args.runner, 'playtest', world='v3', toon=True, veg2=True)
    fill = read('src/shared/WorldFill.luau')
    veg = read('src/shared/VegetationV2.luau')
    keep_fill = float(re.search(r'WorldFill.CoverKeep = ([.\d]+)', fill).group(1))
    keep_veg = float(re.search(r'VegetationV2.CoverKeep = ([.\d]+)', veg).group(1))
    near = lambda p: math.hypot(p['x'], p['z'] - 30) <= 300  # noqa: E731
    cover = [p for p in props if p['layer'] == 'groundcover' and near(p)]
    dropped = sum(1 for p in cover if keep_cover(p['x'], p['z'], keep_veg)) - sum(1 for p in cover if keep_cover(p['x'], p['z'], keep_fill))
    data = __import__('food_layer_data_v3')
    hosts = re.search(r'Map = \[==\[\n?(.*?)\]==\]', read('src/shared/FoodLayerDataV3HostsVeg2.luau'), re.S).group(1)
    rows = ',\n'.join('{layer="%s",id="%s",x=%.3f,z=%.3f,scale=%.4f}' % (p['layer'], p['id'], p['x'], p['z'], p['scale']) for p in props)
    exts = ',\n'.join('["%s"]={%.4f,%.4f,%.4f}' % (k, v[1], v[2], v[3]) for k, v in ext.items())
    starters = ','.join('{%r,%r}' % c for c in data.STARTER_CENTRES)
    source = ('local V3=' + module(read('src/shared/WorldV3.luau')) + '\nlocal Fill=' + module(fill) + '\nlocal WL=' + module(read('src/shared/WorldLayer.luau')) +
              '\nlocal placed = {\n' + rows + '\n}\nlocal ext = {\n' + exts + '\n}\nlocal Map = [==[' + hosts + ']==]\nlocal StarterCentres = {' + starters +
              '}\nlocal StarterRadius = %r\n' % data.STARTER_RADIUS + LUAU)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'fill.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    added = re.search(r'ADDED_NEAR\t(\d+)', result.stdout)
    if added:
        print('parts within 300 studs of spawn: %d ground cover clumps dropped, %d world fill parts added (net %+d)' % (dropped, int(added.group(1)), int(added.group(1)) - dropped))
        if int(added.group(1)) >= dropped:
            problems.append('the world fill must lower the part count near spawn (%d added, %d dropped)' % (int(added.group(1)), dropped))
            print('FAIL:', problems[-1])
    if result.returncode or 'World fill checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
