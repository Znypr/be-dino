#!/usr/bin/env python3
"""BD-1239 vegetation v2 (Config.VegetationV2Enabled, src/shared/VegetationV2.luau), owner 2026-11-16 "vegetation looks cheap", concept sheet
approved ("Yes, build all", docs/evidence/2026-11-16-vegetation-v2).

Runs the REAL VegetationV2 and the World V3 / toon placement in the pinned Luau runtime and checks:
  * all 18 sheet objects have a real published id (digits, no duplicates), each listed in docs/77 and in generated-vegetation.json, and a
    magenta reference picture exists for each in refs/;
  * enabled() needs WorldV3Enabled, ToonWorldEnabled AND VegetationV2Enabled;
  * every kit id the World V3 toon island places in the tree, shrub, rock and ground cover layers either maps to a v2 key or is a kind this
    family leaves alone (dead trees, bare rocks, mushrooms); the round bushes (the berry hosts of BD-1238) always show a berry bush, the
    kit grass tufts never stay (they show grass clumps or ferns), and every v2 key is used somewhere;
  * fit(): a bush is as wide as the kit bush's mean width (the food host ring), a rock stays inside its kit box (colliders), ground cover
    keeps the kit height;
  * thin() keeps only ground cover thinned (every other layer and its order untouched) at about CoverKeep, and the island has fewer parts.
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile and in the rehearsal list; Arena
uses the v2 visual only through veg2Prop and thins only with the flag; the loader fetches the family only with the flag; Bootstrap.client
is untouched; the plaza sign word is sized in studs (BD-1239 NESTS / POTIONS overlap).
Usage: python tools/verify_vegetation_v2.py --runner luau.exe"""
from pathlib import Path
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import world_colliders  # noqa: E402
EVIDENCE = ROOT / 'docs/evidence/2026-11-16-vegetation-v2'
TREES = ROOT / 'docs/evidence/2026-11-23-tree-variety'  # BD-1311: tree variants (generated-trees.json, refs/)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
check(Veg.enabled({WorldV3Enabled = true, ToonWorldEnabled = true, VegetationV2Enabled = true}), "enabled with all three flags")
check(not Veg.enabled({WorldV3Enabled = true, ToonWorldEnabled = true}) and not Veg.enabled({WorldV3Enabled = true, VegetationV2Enabled = true})
    and not Veg.enabled({ToonWorldEnabled = true, VegetationV2Enabled = true}) and not Veg.enabled(nil), "off otherwise")
local n = 0
for key in Veg.Assets do n += 1 check(Veg.ready(key), "published id for " .. key) end
check(n == expected, "published family size (" .. n .. " of " .. expected .. ")")
-- the island as the playtest builds it (World V3 + toon swap; tools/world_colliders.dump), placement only: `placed` is injected
check(#placed > 1000, "island has placements (" .. #placed .. ")")
local used, leftAlone = {}, {}
local kitTufts = 0
for i, p in placed do
    if p.layer ~= "landmark" and p.layer ~= "log" then
        local roll = (i * 0.618) % 1
        local key = Veg.visualFor(p.id, p.biome or "meadow", roll)
        if key then
            check(Veg.Assets[key] ~= nil, "visual key exists: " .. key)
            used[key] = true
            if p.id == "world_bush_a" or p.id == "world_bush_b" then check(string.sub(key, 1, 10) == "veg2_bush_", "a round bush shows a berry bush") end
        else
            local data = Kit[p.id]
            local ok = string.find(p.id, "dead") or string.find(p.id, "bare") or p.id == "world_mushrooms_a" or (data and data.family == "dead")
            if not ok then leftAlone[p.id] = true end
            if p.id == "world_grass_a" or p.id == "world_grass_b" then kitTufts += 1 end
        end
    end
end
for id in leftAlone do check(false, "kit id with no v2 visual: " .. id) end
check(kitTufts == 0, "no flat kit grass tufts left (" .. kitTufts .. ")")
for _, roll in {0, .2, .4, .6, .8, .99} do
    for _, biome in {"meadow", "fern", "conifer", "marsh", "badlands", "volcanic"} do
        for _, id in {"world_tree_canopy_s", "world_tree_canopy_m", "world_tree_canopy_l", "world_tree_conifer_s", "world_tree_conifer_m", "world_tree_cycad_m",
            "world_bush_a", "world_bush_b", "world_fern_a", "world_fern_b", "world_flowers_a", "world_grass_a", "world_grass_b", "world_boulder_mossy_s", "world_boulder_mossy_m"} do
            local key = Veg.visualFor(id, biome, roll)
            if key then used[key] = true end
        end
    end
end
for key in Veg.Assets do check(used[key], "v2 key is used: " .. key) end
-- BD-1239 follow-up: berry bushes no taller than the bush rule allows (kit height x scale), lower domes
for _, p in placed do
    if p.layer == "shrub" and (p.id == "world_bush_a" or p.id == "world_bush_b") then
        check(Kit[p.id].extent[2] * p.scale <= Veg.BushRule.maxHeight + 1e-3, "bush taller than the v2 rule: " .. p.id)
    end
end
for key, f in Veg.Squash do check(Veg.Assets[key] ~= nil and f > .5 and f <= 1, "squash factor for " .. key) end
-- fit
local bush = Kit.world_bush_a.extent
local s = Veg.fit("shrub", bush, {4, 4, 4})
check(math.abs(4 * s - (bush[1] + bush[3]) / 2) < 1e-6, "a bush is as wide as the kit bush mean width")
local rock = Kit.world_boulder_mossy_m.extent
local r = Veg.fit("rock", rock, {3.7, 4, 2.9})
check(3.7 * r <= rock[1] + 1e-6 and 4 * r <= rock[2] + 1e-6 and 2.9 * r <= rock[3] + 1e-6, "a rock stays inside its kit box")
local g = Kit.world_grass_a.extent
check(math.abs(2.2 * Veg.fit("groundcover", g, {1.9, 2.2, 1.7}) - g[2]) < 1e-6, "ground cover keeps the kit height")
-- thin
local thin = Veg.thin(placed)
local before, after, other1, other2 = 0, 0, {}, {}
for _, p in placed do if p.layer == "groundcover" then before += 1 else table.insert(other1, p) end end
for _, p in thin do if p.layer == "groundcover" then after += 1 else table.insert(other2, p) end end
check(#other1 == #other2, "other layers keep their count")
for i, p in other1 do check(other2[i] == p, "other layers keep their order") end
local share = after / math.max(before, 1)
check(math.abs(share - Veg.CoverKeep) < .06, string.format("ground cover kept near CoverKeep (%.3f)", share))
check(#thin < #placed, "fewer placements")
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("vegetation v2 checks failed") end
print(string.format("Vegetation v2 checks passed (%d placements, ground cover %d -> %d)", #placed, before, after))
'''


PR619_KEEP = .55  # the ground cover share PR #619 shipped (no bush rule): the part count may not grow past it


def keep_cover(x, z, keep):
    """VegetationV2.keepCover in Python (same integer hash; floats are exact at these sizes)."""
    h = math.floor(x * 8) * 73856093 + math.floor(z * 8) * 19349663
    return (h % 1000003) / 1000003 < keep


def source_checks():
    errors = []
    config = read('src/shared/Config.luau')
    if '    VegetationV2Enabled = false,\n' not in config:
        errors.append('Config.VegetationV2Enabled must ship false')
    profiles = read('tools/release_profiles.py')
    if '_flag_off("VegetationV2Enabled"' not in profiles or 'Rule("VegetationV2Enabled", "set", True' not in profiles or '("VegetationV2Enabled", "BD-1239' not in profiles:
        errors.append('VegetationV2Enabled: off in default, on in playtest, in the rehearsal list')
    arena = read('src/server/Arena.luau')
    if 'local veg2On = Veg2.enabled(Config)' not in arena or 'if veg2On then placed = Veg2.thin(placed) end' not in arena:
        errors.append('Arena must gate the v2 visual and the thinning on Veg2.enabled(Config)')
    loader = read('src/server/ImportedResources.luau')
    if 'if Veg2.enabled(require(ReplicatedStorage.Shared.Config)) then for key,asset in Veg2.Assets do if Veg2.ready(key)' not in loader:
        errors.append('the loader must fetch the v2 family only with the flag on')
    if 'Veg2' in read('src/client/Bootstrap.client.luau') or 'Vegetation' in read('src/client/Bootstrap.client.luau'):
        errors.append('Bootstrap.client must not change')
    plaza = read('src/server/PlazaHub.luau')
    if 'UDim2.fromScale(Layout.Sign.size[1]' not in plaza or 'UDim2.fromOffset(b.width' in plaza:
        errors.append('the plaza sign word must be sized in studs')
    registry = read('docs/77-asset-registry.md')
    veg = read('src/shared/VegetationV2.luau')
    items = re.findall(r'(veg2_\w+) = \{assetId = "(\d+)", tris = \d+, ref = "(\w+)"', veg)
    ids = [i for _, i, _ in items]
    if len(items) < 18 or len(set(ids)) != len(items):
        errors.append('distinct published ids expected (%d items, %d ids)' % (len(items), len(set(ids))))
    evidence = json.loads((EVIDENCE / 'generated-vegetation.json').read_text(encoding='utf-8'))['items']
    evidence.update(json.loads((TREES / 'generated-trees.json').read_text(encoding='utf-8'))['items'])
    for key, aid, ref in items:
        if f'| world_gen_{key} |' not in registry or f'| {aid} |' not in registry:
            errors.append(f'docs/77 line missing for {key} ({aid})')
        if evidence.get(key, {}).get('asset') != int(aid):
            errors.append(f'generated-vegetation.json / generated-trees.json does not match {key}')
        if not any((d / 'refs' / f'ref-{ref}.png').is_file() for d in (EVIDENCE, TREES)):
            errors.append(f'reference picture missing: refs/ref-{ref}.png')
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    problems = source_checks()
    for p in problems:
        print('FAIL:', p)
    props = world_colliders.dump(args.runner, 'playtest', world='v3', toon=True, veg2=True)[0]
    base = world_colliders.dump(args.runner, 'playtest', world='v3', toon=True)[0]
    bush = lambda P: sum(1 for p in P if p['layer'] == 'shrub' and p['id'] in ('world_bush_a', 'world_bush_b'))  # noqa: E731
    print('round bushes: toon island %d, vegetation v2 %d; placements %d -> %d' % (bush(base), bush(props), len(base), len(props)))
    if not bush(props) < bush(base) * .9:
        problems.append('the v2 bush rule must thin the round bushes (%d of %d)' % (bush(props), bush(base)))
        print('FAIL:', problems[-1])
    keep = float(re.search(r'VegetationV2.CoverKeep = ([.\d]+)', read('src/shared/VegetationV2.luau')).group(1))
    kept = lambda P, k: sum(1 for p in P if p['layer'] != 'groundcover' or keep_cover(p['x'], p['z'], k))  # noqa: E731
    now, before = kept(props, keep), kept(base, PR619_KEEP)
    print('in game (ground cover thinned): %d placements, PR #619 rule %d' % (now, before))
    if now > before:
        problems.append('the v2 island must not have more placements in game than the PR #619 rule (%d > %d)' % (now, before))
        print('FAIL:', problems[-1])
    rows = ',\n'.join('{layer="%s",id="%s",x=%.3f,z=%.3f,scale=%.4f}' % (p['layer'], p['id'], p['x'], p['z'], p['scale']) for p in props)
    expected = len(re.findall(r'(veg2_\w+) = \{assetId = "(\d+)"', read('src/shared/VegetationV2.luau')))
    source = ('local expected = %d\n' % expected + 'local Kit=' + module(read('src/shared/WorldKitData.luau')) + '\nlocal Veg=' + module(read('src/shared/VegetationV2.luau')) +
              '\nlocal placed = {\n' + rows + '\n}\n' + LUAU)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'veg2.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode or 'Vegetation v2 checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
