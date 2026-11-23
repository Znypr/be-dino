#!/usr/bin/env python3
"""BD-1248 plaza shops v2 (Config.PlazaShopsV2Enabled, src/shared/PlazaShopsLayout.luau), owner 2026-11-16 "not what famous roblox
experiences do with their 3d shops and texts", concept approved "Yes, build them".

Runs the REAL PlazaShopsLayout, PlazaHubLayout, HubTravelClientRules and LowPolyDinoAssets in the pinned Luau runtime and checks:
  * enabled(): needs WorldV3Enabled, PlazaHubEnabled and PlazaShopsV2Enabled;
  * one shop per BD-1221 stall (same stations and screens), the ONE label of each reads exactly EGGS / POTIONS / SHOP / DINOS and fits the board;
  * every building and the signboard is a published id, all distinct; every shopkeeper is a species of LowPolyDinoAssets;
  * the "At home" rule of BD-1221 option A is unchanged: in a run POTIONS opens, EGGS, SHOP and DINOS say "Open at HOME".
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile and in the rehearsal list; Arena builds the
shops only through PlazaShopsLayout.enabled; the server places no BillboardGui, exactly one SurfaceGui (the sign face), no visible code-built
Part (only the hidden collider and the prompt anchor) and no MeshPart made in code; the keeper script returns with the flag off, sends nothing
and only calls LowPolyClips / LowPolyDinos; Bootstrap.client is untouched; every id has a docs/77 line; the evidence pictures exist.
Usage: python tools/verify_plaza_shops.py --runner luau.exe"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/2026-11-16-plaza-shops-v2'
PICTURES = ('before-spawn-view.jpg', 'after-spawn-view.jpg', 'shop-eggs.jpg', 'shop-potions.jpg', 'shop-shop.jpg', 'shop-dinos.jpg',
            'ref-eggs.png', 'ref-potions.png', 'ref-shop.png', 'ref-dinos.png')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local all = {WorldV3Enabled = true, PlazaHubEnabled = true, PlazaShopsV2Enabled = true}
check(Shops.enabled(all), "enabled with the three flags")
for _, key in {"WorldV3Enabled", "PlazaHubEnabled", "PlazaShopsV2Enabled"} do
    local c = table.clone(all) c[key] = nil
    check(not Shops.enabled(c), "off without " .. key)
end
check(not Shops.enabled(nil), "off for nil")
local words = {nests = "EGGS", potions = "POTIONS", style = "SHOP", index = "DINOS"}
check(#Shops.Shops == #Hub.Stalls and #Shops.Shops == 4, "one shop per stall")
local seen, ids = {}, {}
for key, a in Shops.Assets do
    check(type(a.assetId) == "string" and string.match(a.assetId, "^%d+$") ~= nil and #a.assetId >= 9, "published id for " .. key)
    check(not ids[a.assetId], "distinct id " .. key)
    ids[a.assetId] = true
end
check(Shops.Assets[Shops.Sign.key] ~= nil, "the signboard is a published mesh")
for _, stall in Hub.Stalls do
    local shop = Shops.shop(stall.station)
    check(shop ~= nil, "shop for " .. stall.station)
    if shop then
        check(not seen[stall.station], "one shop per station " .. stall.station)
        seen[stall.station] = true
        check(shop.word == words[stall.station], "the label of " .. stall.station .. " reads " .. tostring(words[stall.station]))
        check(Shops.letterHeight(shop.word) >= Shops.MinLetter, "the word reads from the spawn: " .. shop.word)
        check(Shops.Assets[shop.building.key] ~= nil, "published building for " .. stall.station)
        check(Dinos[shop.keeper.species] ~= nil, "the keeper is a low-poly species: " .. tostring(shop.keeper.species))
        check(shop.keeper.height >= 4 and shop.keeper.height <= 8, "small keeper")
        check(shop.sign.y > shop.keeper.y + shop.keeper.height, "the sign hangs above the keeper")
        check(#shop.icon == 2 and (shop.icon[1] == "ui" or shop.icon[1] == "slot" or shop.icon[1] == "art"), "icon source")
        local dim = Travel.dimmed(stall.screen, true, "Active")
        check(Hub.promptText(dim) == (if stall.station == "potions" then "Open" else Hub.HomeLine), "At home rule for " .. stall.station)
        check(not Travel.dimmed(stall.screen, true, "Sanctuary"), "at home every shop opens: " .. stall.station)
    end
end
check(Shops.fit({10, 20, 5}, {20, 20, 20}) == 1 and Shops.fit({10, 10, 10}, {5, 20, 20}) == .5, "uniform fit")
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("plaza shops checks failed") end
print("Plaza shops checks passed")
'''


def run(runner):
    script = ('local Shops=' + module(read('src/shared/PlazaShopsLayout.luau')) + '\nlocal Hub=' + module(read('src/shared/PlazaHubLayout.luau')) +
              '\nlocal Travel=' + module(read('src/shared/HubTravelClientRules.luau')) + '\nlocal Dinos=' + module(read('src/shared/LowPolyDinoAssets.luau')) + LUAU)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_plaza_shops.luau'
        path.write_text(script, encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-3000:] + out.stderr[-3000:])
        return out.stdout.strip()


def static_checks():
    errors = []
    flag = 'PlazaShopsV2Enabled'
    config, profiles = read('src/shared/Config.luau'), read('tools/release_profiles.py')
    if len(re.findall(r'^    %s = false,$' % flag, config, re.M)) != 1:
        errors.append('Config.%s must ship false exactly once' % flag)
    for needle in ('_flag_off("%s",' % flag, 'Rule("%s", "set", False,' % flag, '("%s", "BD-1248' % flag):  # BD-1312: off in the playtest too (shops only in the cave)
        if needle not in profiles:
            errors.append('release_profiles.py is missing %s' % needle)
    if '"%s"' % flag not in read('tools/release_playtest.py') or '"%s"' % flag not in read('tests/test_rehearsal.py'):
        errors.append('%s must be in the playtest manifest and the rehearsal list' % flag)
    arena = read('src/server/Arena.luau')
    if 'if PlazaShopsLayout.enabled(Config) then require(script.Parent.PlazaShops).build(' not in arena:
        errors.append('Arena must build the shops only through PlazaShopsLayout.enabled')
    server = read('src/server/PlazaShops.luau')
    if 'Instance.new("BillboardGui")' in server:
        errors.append('PlazaShops: no floating BillboardGui words (one label per shop, on the board)')
    if server.count('Instance.new("SurfaceGui")') != 1:
        errors.append('PlazaShops: exactly one SurfaceGui (the sign face) per shop')
    if server.count('Instance.new("Part")') != 2 or 'Instance.new("MeshPart")' in server:
        errors.append('PlazaShops builds no visible Part: only the hidden collider and the prompt anchor')
    if 'box.Transparency' not in server or 'anchor.Transparency' not in server:
        errors.append('the collider and the prompt anchor stay hidden')
    if 'PlazaOneLabel' not in server or 'PlazaOneLabel' not in read('src/client/PlazaHub.client.luau'):
        errors.append('the prompt shows no object name next to the sign (PlazaOneLabel)')
    keepers = read('src/client/PlazaKeepers.client.luau')
    head = '\n'.join(keepers.split('\n')[:14])
    if 'if not Layout.enabled(Config) then return end' not in head:
        errors.append('PlazaKeepers.client must return on its first lines with the flag off')
    for banned in ('RemoteEvent', 'FireServer', 'InvokeServer', 'DataStore'):
        if banned in keepers:
            errors.append('PlazaKeepers.client is presentation only: %s found' % banned)
    if 'Clips.sampleCycle("idle"' not in keepers or 'Clips.sample("happy"' not in keepers or 'LowPoly.clone(species)' not in keepers:
        errors.append('the keepers play the authored idle loop and the happy clip on a LowPolyDinos.clone')
    if 'Theme.MotionEnabled' not in keepers:
        errors.append('the keepers keep still under Reduce Motion')
    if 'Plaza' in read('src/client/Bootstrap.client.luau'):
        errors.append('Bootstrap.client must not change')
    registry = read('docs/77-asset-registry.md')
    for key, aid in re.findall(r'(shop_\w+) = \{assetId = "(\d+)"', read('src/shared/PlazaShopsLayout.luau')):
        if '| plaza_%s |' % key not in registry or aid not in registry:
            errors.append('docs/77 needs a plaza_%s line with %s' % (key, aid))
    for name in PICTURES:
        if not (EVIDENCE / name).exists():
            errors.append('missing evidence picture %s' % name)
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    a = ap.parse_args()
    errors = static_checks()
    if errors:
        for e in errors:
            print('FAIL:', e)
        return 1
    print(run(a.runner))
    print('Plaza shops source guards passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
