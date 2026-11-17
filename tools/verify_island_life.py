#!/usr/bin/env python3
"""BD-1244 life on the island (Config.IslandLifeEnabled, src/shared/IslandLife.luau, src/client/IslandLife.client.luau), owner 2026-11-16
"game still looks empty", "Yes, build all".

Runs the REAL IslandLife rules with the REAL World V3 shape in the pinned Luau runtime and checks:
  * enabled() needs IslandLifeEnabled AND WorldV3Enabled;
  * every critter has a real published id (digits, distinct), a docs/77 line and a line in the evidence README;
  * the baby species are V3 low-poly dinos (LowPolyDinoAssets) and never an NPC predator species (NpcPredatorRules.Species);
  * every zone gets its herd (caps.babiesPerZone spots on all device classes), each home on land in its own zone, off the path and the plaza,
    out of the lagoon, and herds keep 30 studs apart; the spawn herd stands in front of the spawn camera, inside the plaza, off the main path;
  * flock and dragonfly spots exist and are on land; gull loops stay over the island and high up; flutter / dart stay near their spot;
  * the behaviour machine only picks known modes, walk targets stay inside WanderRadius, durations are short;
  * phone budget: at most `PartCap.Phone` parts alive at once on a phone (babies x parts per baby + critters), CullRadius <= 150.
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile and in the rehearsal list; the client
script returns at once without the flag, makes no Humanoid, no BeDinoNpcs folder, no NpcLowPoly attribute, no RemoteEvent, keeps every part
anchored or welded to an anchored root with CanCollide / CanTouch / CanQuery off; the server loader is gated by the flag; Bootstrap.client
is untouched and the LowPoly clip files are only called (unchanged by this row).
Usage: python tools/verify_island_life.py --runner luau.exe"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PARTS_PER_BABY = 9  # 8 MeshParts (Studio count 2026-11-16, every herbivore species used) + the invisible root
PART_CAP_PHONE = 60  # parts alive at once on a phone (docs/107: the whole island is already over its ~3,000; this row may add almost nothing)


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
check(Life.enabled({IslandLifeEnabled = true, WorldV3Enabled = true}), "enabled with both flags")
check(not Life.enabled({IslandLifeEnabled = true}) and not Life.enabled({WorldV3Enabled = true}) and not Life.enabled(nil), "off otherwise")
local ids = {}
for key, c in Life.Critters do
    check(string.match(c.assetId, "^%d+$") ~= nil, "published id for " .. key)
    check(ids[c.assetId] == nil, "distinct id " .. key) ids[c.assetId] = true
end
for zone, list in Life.Babies do
    for _, species in list do
        check(Assets[species] ~= nil, "baby species is a V3 low-poly dino: " .. species)
        check(Assets[species] == nil or Assets[species].class ~= "Water", "baby species walks: " .. species)
        for _, p in Predators do check(species ~= p, "baby species is never a predator: " .. species) end
    end
end
local W = World
check(Life.CullRadius <= 150, "cull radius at most 150")
for _, device in {"Desktop", "Tablet", "Phone"} do
    local caps = Life.capsFor(device)
    local all = {}
    for _, zone in Life.Zones do
        local spots = Life.herdSpots(W, zone, caps.babiesPerZone)
        check(#spots == caps.babiesPerZone, device .. ": full herd in " .. zone .. " (" .. #spots .. ")")
        for _, s in spots do
            check(Life.goodSpot(W, zone, s.x, s.z), "good herd spot in " .. zone)
            check(W.zoneAt(s.x, s.z).id == zone and W.path(s.x, s.z) <= .05 and not W.inPlaza(s.x, s.z) and W.inland(s.x, s.z) >= 6, "herd home rule " .. zone)
            for _, o in all do check((o.x - s.x) ^ 2 + (o.z - s.z) ^ 2 >= 29 ^ 2 or o.zone ~= zone, "herd homes 30 studs apart in " .. zone) end
            s.zone = zone table.insert(all, s)
        end
    end
    check(caps.babies <= 9 and caps.babies >= 4, device .. ": baby cap 4..9")
end
-- the spawn herd: on the plaza, off the main path, in front of the spawn camera (looking down spoke 70)
for _, s in Life.spawnSpots(W) do
    check(W.inPlaza(s.x, s.z) and W.path(s.x, s.z) < .05, "spawn herd on open plaza ground")
    local dx, dz = s.x - W.CenterX, s.z - W.CenterZ
    check(dx * math.cos(math.rad(70)) + dz * math.sin(math.rad(70)) > 20, "spawn herd ahead of the spawn camera")
    check(Assets[s.species] ~= nil, "spawn herd species is a V3 dino")
end
local flocks = Life.flockSpots(W)
check(#flocks >= 6, "flock spots (" .. #flocks .. ")")
for i, f in flocks do
    check(Life.Critters[f.kind] ~= nil, "flock kind is a critter")
    check(W.inland(f.x, f.z) > 6, "flock over land")
    if i > 2 then check(Life.goodSpot(W, f.zone, f.x, f.z), "flock spot rule " .. f.zone) end
end
check(#Life.dragonflySpots(W) >= 2, "dragonfly spots")
for i = 1, #Life.Gulls do
    for t = 0, 120, 7 do
        local x, y, z = Life.gullAt(i, t)
        check(y >= 55, "gulls stay high")
        check(math.sqrt((x - W.CenterX) ^ 2 + (z - W.CenterZ) ^ 2) < W.CoastRadius + 40, "gulls stay over the island")
    end
end
for i = 1, 4 do
    for t = 0, 60, 1.3 do
        local x, y, z = Life.flutter(i, t)
        check(math.abs(x) < 8 and math.abs(z) < 8 and y > 2 and y < 6, "butterflies stay near their flock")
        local f = Life.flap(i, t) check(f >= .3 and f <= 1, "flap scale 0.3..1")
        local dx, dy, dz = Life.dart(i, t) check(math.abs(dx) <= 7.01 and math.abs(dz) <= 7.01 and dy > 1, "dragonfly stays near its spot")
    end
end
local seen = {}
for r = 0, .99, .01 do
    local m = Life.nextMode(r) seen[m] = true
    check(m == "graze" or m == "look" or m == "idle" or m == "walk", "known mode")
    check(Life.duration(m, r) > 0 and Life.duration(m, r) <= 8, "short mode")
    local x, z = Life.walkTarget(100, 50, r, 1 - r)
    check(math.sqrt((x - 100) ^ 2 + (z - 50) ^ 2) <= Life.WanderRadius + 1e-6, "walk target inside WanderRadius")
end
check(seen.graze and seen.look and seen.idle and seen.walk, "every mode reachable")
local phone = Life.capsFor("Phone")
local parts = phone.babies * PARTS_PER_BABY + phone.flocks * phone.perFlock + phone.dragonflies + phone.gulls
check(parts <= PART_CAP, "phone part cap (" .. parts .. ")")
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("island life checks failed") end
print(string.format("Island life checks passed (phone parts at most %d, desktop at most %d)", parts,
    Life.capsFor("Desktop").babies * PARTS_PER_BABY + Life.capsFor("Desktop").flocks * Life.capsFor("Desktop").perFlock + Life.capsFor("Desktop").dragonflies + Life.capsFor("Desktop").gulls))
'''


def source_checks():
    errors = []
    if '    IslandLifeEnabled = false,\n' not in read('src/shared/Config.luau'):
        errors.append('Config.IslandLifeEnabled must ship false')
    profiles = read('tools/release_profiles.py')
    if '_flag_off("IslandLifeEnabled"' not in profiles or 'Rule("IslandLifeEnabled", "set", True' not in profiles or '("IslandLifeEnabled", "BD-1244' not in profiles:
        errors.append('IslandLifeEnabled: off in default, on in playtest, in the rehearsal list')
    client = read('src/client/IslandLife.client.luau')
    if 'if not Life.enabled(Config) then return end' not in client:
        errors.append('the client script must return at once without the flag')
    for bad in ('"Humanoid"', 'BeDinoNpcs', 'NpcLowPoly', 'RemoteEvent', 'RemoteFunction', ':FireServer', ':InvokeServer'):
        if bad in client:
            errors.append('the client script must not use ' + bad)
    for need in ('root.Anchored, root.CanCollide, root.CanTouch, root.CanQuery = true, false, false, false',
                 'item.Anchored, item.CanCollide, item.CanTouch, item.CanQuery = false, false, false, false',
                 'part.Anchored, part.CanCollide, part.CanTouch, part.CanQuery, part.CastShadow = true, false, false, false, false'):
        if need not in client:
            errors.append('client parts must be anchored / welded with no collision, touch or query: ' + need[:40])
    loader = read('src/server/IslandLifeLoader.luau')
    if 'if not Life.enabled(require(ReplicatedStorage.Shared.Config)) then return end' not in loader:
        errors.append('the critter loader must be gated by the flag')
    if 'IslandLife' in read('src/client/Bootstrap.client.luau'):
        errors.append('Bootstrap.client must not change')
    registry = read('docs/77-asset-registry.md')
    readme = read('docs/evidence/2026-11-16-world-fill-life/README.md')
    for key, aid in re.findall(r'(life_\w+) = \{assetId = "(\d+)"', read('src/shared/IslandLife.luau')):
        if f'| {key} |' not in registry or aid not in registry:
            errors.append(f'docs/77 line missing for {key} ({aid})')
        if aid not in readme:
            errors.append(f'evidence README does not list {key} ({aid})')
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    problems = source_checks()
    for p in problems:
        print('FAIL:', p)
    predators = re.search(r'Species = \{([^}]*)\}', read('src/shared/NpcPredatorRules.luau')).group(1)
    source = ('local Life=' + module(read('src/shared/IslandLife.luau')) + '\nlocal World=' + module(read('src/shared/WorldV3.luau')) +
              '\nlocal Assets=' + module(read('src/shared/LowPolyDinoAssets.luau')) + '\nlocal Predators={' + predators + '}' +
              '\nlocal PART_CAP=%d\nlocal PARTS_PER_BABY=%d\n' % (PART_CAP_PHONE, PARTS_PER_BABY) + LUAU)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'life.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode or 'Island life checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
