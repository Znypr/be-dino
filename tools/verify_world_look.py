#!/usr/bin/env python3
"""World look rows of the docs/242 benchmark, behind their own flags (off by default, ON in the playtest profile).

BD-1220 real sea (Config.RealSeaEnabled, src/shared/WorldSea.luau): runs the REAL WorldSea and WorldV3 in the pinned Luau runtime and checks:
the far-sea blocks never overlap the island square, sit on the 4-stud grid, reach WorldSea.Radius on every side and stay within it; a voxel
column is Sand under the floor and Water up to sea level 0; the deeper floor is still wade-able at the hidden coast wall (coast + 14) and every
column past FlatFrom is at SeaFloor; phones keep their classic fog. Source guards: the flag ships false once, is pinned off in the default
profile and ON in the playtest profile, is in the rehearsal list and the manifest; the square ocean plate is only built with the flag off; the
Atmosphere is set in the server Bootstrap before any client joins; Bootstrap.client and the hatch files are untouched.

BD-1223 + BD-1224 one toy style (Config.ToonWorldEnabled, src/shared/WorldToon.luau): every island terrain material (the BiomeMap and
WorldV3 colour tables) has a toon colour, the flat map is a real image id listed in docs/77, the palette stays soft (no channel 0 or 255);
after useToonPlants no shrub list (every biome, the V3 beach and meadow) names a fern or horsetail, each list keeps its total weight, and the
marsh pool edge is swapped too. Source guards: the variants are made only with the flag on and only in IslandTerrain; the swap runs after
useV3 in Arena.
Usage: python tools/verify_world_look.py --runner luau.exe"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FLAGS = {'RealSeaEnabled': 'BD-1220', 'ToonWorldEnabled': 'BD-1223'}


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
-- BD-1220 real sea
check(Sea.enabled({WorldV3Enabled = true, RealSeaEnabled = true}), "enabled with both flags")
check(not Sea.enabled({WorldV3Enabled = false, RealSeaEnabled = true}) and not Sea.enabled({WorldV3Enabled = true}) and not Sea.enabled(nil), "off otherwise")
check(Sea.clearFog("Phone") == nil, "phones keep their classic fog")
check(Sea.clearFog("Desktop") ~= nil and Sea.clearFog("Tablet") ~= nil and Sea.clearFog("Desktop").fogEnd > Sea.Radius, "desktop/tablet clear fog past the sea")
check(Sea.Tile % 4 == 0 and 848 % Sea.Tile == 0, "blocks line up with the island square on the 4-stud grid")
local half = 424
local tiles = Sea.tiles(V3.CenterX, V3.CenterZ, half)
check(#tiles > 100, "far sea has blocks (" .. #tiles .. ")")
local reachX, reachZ, lowX, lowZ = -math.huge, -math.huge, math.huge, math.huge
for _, t in tiles do
    local x, z = t[1], t[2]
    local overlap = x < half and x + Sea.Tile > -half and z < half and z + Sea.Tile > -half
    check(not overlap, "block overlaps the island square at " .. x .. "," .. z)
    check((x + half) % 4 == 0 and (z + half) % 4 == 0, "block on the grid")
    local cx, cz = x + Sea.Tile / 2 - V3.CenterX, z + Sea.Tile / 2 - V3.CenterZ
    check(cx * cx + cz * cz <= Sea.Radius * Sea.Radius, "block centre within Radius")
    reachX, reachZ = math.max(reachX, x + Sea.Tile), math.max(reachZ, z + Sea.Tile)
    lowX, lowZ = math.min(lowX, x), math.min(lowZ, z)
end
for _, r in {reachX - V3.CenterX, reachZ - V3.CenterZ, V3.CenterX - lowX, V3.CenterZ - lowZ} do
    check(r >= Sea.Radius - Sea.Tile, "sea reaches Radius on every side (" .. r .. ")")
end
-- cave home box: its blocks are written before the cave shell (IslandTerrain), the rest after
local early = 0
for _, t in tiles do if Sea.overlaps(t, {-148, 452, 148, 708}) then early += 1 end end
check(early >= 2 and early <= 6, "a few blocks touch the cave box (" .. early .. ")")
check(Sea.overlaps({-100, 500}, {-148, 452, 148, 708}) and not Sea.overlaps({200, 500}, {-148, 452, 148, 708}) and not Sea.overlaps({-148 - Sea.Tile, 500}, {-148, 452, 148, 708}), "overlap rule")
-- voxel column rule
local m, o = Sea.column(Sea.SeaFloor, 4)
check(#m == -Sea.FloorLow / 4, "one cell per 4 studs from FloorLow to 0")
check(m[1] == "Sand" and m[#m] == "Water" and o[#m] == 1, "sand under, water on top")
local mid = math.floor((Sea.SeaFloor - Sea.FloorLow) / 4) + 1
check(m[mid] == "Sand" and math.abs(o[mid] - .5) < 1e-6, "the floor cell is half full at SeaFloor")
local mh, oh = Sea.column(-10, 4)
check(mh[#mh] == "Water" and mh[#mh - 1] == "Water" and mh[#mh - 2] == "Sand" and math.abs(oh[#mh - 2] - .5) < 1e-6, "shelf column at -10")
-- deeper floor (applied the way IslandLayout applies it)
local oldFloor, oldSlope = V3.SeaFloor, V3.SeaSlope
check(oldFloor == -6 and oldSlope == .22, "WorldV3 default shelf unchanged")
V3.SeaFloor, V3.SeaSlope = Sea.SeaFloor, Sea.SeaSlope
for a = 0, 355, 5 do
    local x, z = V3.polar(a, V3.coast(a) + 14)
    check(V3.height(x, z) > -5, "wade-able at the coast wall, angle " .. a)
    local fx, fz = V3.polar(a, Sea.FlatFrom + 1)
    check(math.abs(V3.height(fx, fz) - Sea.SeaFloor) < 1e-6, "flat past FlatFrom, angle " .. a)
end
V3.SeaFloor, V3.SeaSlope = oldFloor, oldSlope
-- BD-1223 ground palette
for name in BiomeMap.Colors do check(Toon.Palette[name] ~= nil, "toon colour for island material " .. name) end
for name in V3.Colors do check(Toon.Palette[name] ~= nil, "toon colour for V3 material " .. name) end
for name, c in Toon.Palette do
    for i = 1, 3 do check(c[i] >= 40 and c[i] <= 245, "soft toon colour " .. name) end
end
check(string.match(Toon.FlatMap, "^rbxassetid://[1-9]%d+$") ~= nil, "flat map is an image id")
check(Toon.enabled({WorldV3Enabled = true, ToonWorldEnabled = true}) and not Toon.enabled({ToonWorldEnabled = true}), "toon flag needs World V3")
-- BD-1224 plants
local SPIKY = {world_fern_a = true, world_fern_b = true, world_horsetail_a = true}
for id in SPIKY do check(Toon.Swaps[id] ~= nil and not SPIKY[Toon.Swaps[id]], "spiky plant swapped to a round one: " .. id) end
Biome.useV3(V3) -- the V3 beach and meadow lists too
local before = {}
for name, def in Biome.Biomes do
    local total = 0 for _, e in def.shrubs or {} do total += e[2] end
    before[name] = total
end
Biome.useToonPlants(Toon.Swaps, Toon.swapList)
for name, def in Biome.Biomes do
    local total = 0
    for _, e in def.shrubs or {} do
        total += e[2]
        check(not SPIKY[e[1]], "no spiky plant left in " .. name .. ": " .. e[1])
    end
    check(math.abs(total - before[name]) < 1e-9, "shrub weight kept in " .. name)
end
check(Biome.ToonSwaps == Toon.Swaps, "marsh pool edge swap is on")
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("world look checks failed") end
print("World look checks passed")
'''


def static_checks():
    errors = []
    config, profiles = read('src/shared/Config.luau'), read('tools/release_profiles.py')
    playtest, rehearsal = read('tools/release_playtest.py'), read('tests/test_rehearsal.py')
    for flag, row in FLAGS.items():
        if len(re.findall(r'^    %s = false,$' % flag, config, re.M)) != 1:
            errors.append('Config.%s must ship false exactly once' % flag)
        for needle in ('_flag_off("%s",' % flag, 'Rule("%s", "set", True,' % flag, '("%s", "%s' % (flag, row)):
            if needle not in profiles:
                errors.append('release_profiles.py is missing %s' % needle)
        if '"%s"' % flag not in playtest or '"%s"' % flag not in rehearsal:
            errors.append('%s must be in the playtest manifest and the rehearsal list' % flag)
    arena = read('src/server/Arena.luau')
    if 'if WorldSea.enabled(Config) then' not in arena or arena.index('if WorldSea.enabled(Config) then') > arena.index('"Ocean", Vector3.new(6000'):
        errors.append('Arena must build the square ocean plate only with RealSeaEnabled off')
    boot = read('src/server/Bootstrap.server.luau')
    if 'if Sea.enabled(Config) then local A = Sea.Atmosphere' not in boot or boot.index('Sea.Atmosphere') > boot.index('Arena.build()'):
        errors.append('the Atmosphere must be set in the server Bootstrap before Arena.build (before a client joins)')
    terrain_src = read('src/server/IslandTerrain.luau')
    if 'if V3 and Toon.enabled(Config) then' not in terrain_src or 'SetBaseMaterialOverride(material, Toon.VariantPrefix .. name)' not in terrain_src:
        errors.append('IslandTerrain must bind the toon variants only with ToonWorldEnabled (and World V3)')
    for path in (ROOT / 'src').rglob('*.luau'):
        rel = path.relative_to(ROOT).as_posix()
        if 'Instance.new("MaterialVariant")' in read(rel):
            errors.append('%s: game scripts cannot write MaterialVariant.BaseMaterial; author variants in resources/world-materials.rbxmx' % rel)
    import json
    bindings = json.loads(read('resources/visual-upgrade-bindings.json'))['worldMaterials']
    toon_names = re.findall(r'^    (\w+) = \{\d+, \d+, \d+\},', read('src/shared/WorldToon.luau'), re.M)
    flat = re.search(r'rbxassetid://(\d+)', read('src/shared/WorldToon.luau')).group(1)
    for name in toon_names:
        entry = [m for m in bindings if m['name'] == 'BeDinoToon_' + name]
        if len(entry) != 1 or entry[0]['base'] != name or entry[0]['color'] != flat or entry[0].get('bound', True) is not False:
            errors.append('worldMaterials needs one unbound BeDinoToon_%s on %s with the flat map %s' % (name, name, flat))
    if len(toon_names) != 10 or read('resources/world-materials.rbxmx').count('BeDinoToon_') < 10:
        errors.append('world-materials.rbxmx must carry the 10 toon variants (python tools/bind_visual_assets.py)')
    arena_src = read('src/server/Arena.luau')
    swap = 'if WorldToon.enabled(Config) then Biome.useToonPlants(WorldToon.Swaps, WorldToon.swapList) end'
    if swap not in arena_src or arena_src.index(swap) < arena_src.index('Biome.useV3(BiomeMap.V3)'):
        errors.append('Arena must swap the plants with ToonWorldEnabled, after useV3')
    toon = read('src/shared/WorldToon.luau')
    image = re.search(r'rbxassetid://(\d+)', toon).group(1)
    decal = re.search(r'Decal (\d+)', toon).group(1)
    registry = read('docs/77-asset-registry.md')
    if image not in registry or decal not in registry:
        errors.append('the flat map ids (image %s, decal %s) need a docs/77 line' % (image, decal))
    weather = read('src/client/WeatherVisuals.client.luau')
    if 'Sea.enabled(require(Shared.Config)) and Sea.clearFog(deviceClass)' not in weather:
        errors.append('WeatherVisuals must take the clear fog from WorldSea only with the flag on')
    terrain = read('src/server/IslandTerrain.luau')
    if 'if realSea then task.spawn(farSea, V3, extent, resolution, false) end' not in terrain or terrain.index('task.spawn(farSea') < terrain.index('"IslandTerrainReady", true'):
        errors.append('the far sea must be written after IslandTerrainReady (nothing waits for it)')
    early = 'if realSea then farSea(V3, extent, resolution, true) end'
    if early not in terrain or terrain.index(early) > terrain.index('if beforeReady then beforeReady() end'):
        errors.append('the sea blocks under the cave box must be written BEFORE the cave shell (beforeReady)')
    for path in ['src/client/Bootstrap.client.luau', 'src/client/HatchSequence.luau'] + [str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'src').rglob('HatchStage*.luau')]:
        text = read(path)
        if 'WorldSea' in text or 'RealSea' in text:
            errors.append('%s must not mention the world look modules' % path)
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_checks()
    for p in problems:
        print('FAIL:', p)
    source = ('local V3=' + module(read('src/shared/WorldV3.luau')) + '\nlocal Sea=' + module(read('src/shared/WorldSea.luau')) +
              '\nlocal Toon=' + module(read('src/shared/WorldToon.luau')) + '\nlocal BiomeMap=' + module(read('src/shared/BiomeMap.luau')) +
              '\nlocal Biome=' + module(read('src/shared/BiomePlacement.luau')) + '\n' + LUAU)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'world_look.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode or 'World look checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
