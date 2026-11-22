#!/usr/bin/env python3
"""BD-1299: the Dino Index zones and zone rewards behind Config.IndexZonesEnabled.

Runs the REAL Shared/IndexZones, server/ProfileIndexZones (the repository claim, with an in-memory store whose UpdateAsync calls the
transform like Roblox) and server/IndexZoneService (the remote handler) in the pinned Luau runtime and checks:
  * the zones: four, in the picture's order (Meadow, Forest, Beach, Volcano) and colours, every Config.SpeciesOrder species in exactly one
    zone, at most 8 per zone, no secret in a zone, each zone has a picture id (one table entry) and is marked PROVISIONAL;
  * the rule: half = half rounded up, all = every one; a claim pays once (a second claim answers "already" and pays nothing), a double
    claim inside one session pays once, a step not reached pays nothing, a bad zone / step pays nothing, the wallet cap refuses without a
    change, a newer build's field is never touched, the field is additive (nothing else in the profile changes) and created only by a paid
    claim; the client-side state words ("ready", "claimed", "locked") follow the same rule;
  * the remote: only {action = "claim", zone, step} (extra keys, extra arguments, wrong types: bad_request), rate limited, crystals from the
    server table (a forged amount is ignored), flag off = "disabled" with NO store request and NO profile read or write;
  * source guards: the flag ships false once, pinned off in the default profile, ON in playtest, in the rehearsal list and the manifest; the
    service starts only with the flag; the private value is owner-only and set only with the flag; no Robux, no paid line, no random item.
The mutants put each defect back and a check must fail. NOT Studio evidence (pictures: docs/evidence/2026-11-23-index-proposal).
Usage: python tools/verify_index_zones.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'rules': 'src/shared/IndexZones.luau', 'part': 'src/server/ProfileIndexZones.luau', 'service': 'src/server/IndexZoneService.luau',
    'social': 'src/server/SocialServices.luau', 'repo': 'src/server/ProfileRepository.luau', 'pscore': 'src/shared/PrivateStateCore.luau',
    'config': 'src/shared/Config.luau', 'profiles': 'tools/release_profiles.py', 'playtest': 'tools/release_playtest.py',
    'client': 'src/client/DinoIndexZones.luau', 'kit': 'src/client/DinoIndexKit.luau', 'layout': 'src/shared/SaeMenuRules.luau',
}


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def species_order(config):
    m = re.search(r'^    SpeciesOrder = \{([^}]*)\}', config, re.M)
    return re.findall(r'"([a-z_]+)"', m.group(1)) if m else []


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local Z = require("IndexZones")
-- zones
local names, seen = {}, {}
for _, zone in Z.Zones do
    table.insert(names, zone.name)
    check(#zone.species >= 1 and #zone.species <= Z.PerPage, zone.id .. ": 1-8 species")
    check(type(zone.art) == "string" and (zone.art == "" or string.match(zone.art, "^rbxassetid://%d+$") ~= nil), zone.id .. ": one picture id entry")
    for _, id in zone.species do
        check(seen[id] == nil, "species in two zones: " .. id)
        seen[id] = zone.id
        check(Z.zoneOf(id) == zone, "zoneOf " .. id)
    end
end
check(table.concat(names, ",") == "Meadow,Forest,Beach,Volcano", "zone order and names as on the picture")
check(Z.Zones[1].colour == "#72F239" and Z.Zones[2].colour == "#248A44" and Z.Zones[3].colour == "#E9D197" and Z.Zones[4].colour == "#F04440", "zone colours")
local n = 0
for _, id in ORDER do n += 1 check(seen[id] ~= nil, "species without a zone: " .. id) end
local total = 0
for _ in seen do total += 1 end
check(total == n, "only Config.SpeciesOrder species in the zones")
for _, secret in {"chickosaurus", "pigeon", "dodo", "duck", "penguin", "budgiesaurus"} do check(Z.zoneOf(secret) == nil, "no secret in a zone") end
check(Z.secretZone("Water") == "beach" and Z.secretZone("Fly") == "meadow" and Z.secretZone("nope") == "forest", "secret zones")
-- need
local meadow = Z.zone("meadow")
check(Z.need(Z.zone("beach"), "half") == 4 and Z.need(Z.zone("volcano"), "half") == 2, "half of 7 is 4, half of 4 is 2")
check(Z.need(meadow, "half") == math.ceil(#meadow.species / 2) and Z.need(meadow, "all") == #meadow.species, "need half (rounded up) / all")
for _, step in Z.Steps do check(Z.Crystals[step] > 0 and Z.Crystals[step] <= 1000, "a modest free reward") end
-- the rule
local function coll(zone, k)
    local c = {}
    for i = 1, k do c[zone.species[i]] = {base = 1} end
    c.duck = {base = 2} -- a secret never counts
    return c
end
local half = Z.need(meadow, "half")
local p = {collection = coll(meadow, half), progression = {crystals = 10}, other = "keep"}
check(Z.state(meadow, "half", half, nil) == "ready" and Z.state(meadow, "all", half, nil) == "locked", "state words")
local s, c = Z.apply(p, "meadow", "half", 2000000000)
check(s == "applied" and c == Z.Crystals.half and p.progression.crystals == 10 + Z.Crystals.half, "half paid")
check(p.indexZoneRewards and p.indexZoneRewards[1] == "meadow_half", "stored word")
check(Z.state(meadow, "half", half, p.indexZoneRewards) == "claimed", "claimed word")
s, c = Z.apply(p, "meadow", "half", 2000000000)
check(s == "already" and c == 0 and p.progression.crystals == 10 + Z.Crystals.half and #p.indexZoneRewards == 1, "never twice")
s = Z.apply(p, "meadow", "all", 2000000000)
check(s == "not_reached" and #p.indexZoneRewards == 1, "all not reached")
check(p.other == "keep", "nothing else changes")
local q = {collection = coll(meadow, half - 1), progression = {crystals = 0}}
check(Z.apply(q, "meadow", "half", 2000000000) == "not_reached" and q.indexZoneRewards == nil and q.progression.crystals == 0, "not reached: no field")
check(Z.apply(q, "atlantis", "half", 2000000000) == "bad_zone" and Z.apply(q, "meadow", "most", 2000000000) == "bad_step", "bad zone / step")
local full = {collection = coll(meadow, #meadow.species), progression = {crystals = 1999999990}}
check(Z.apply(full, "meadow", "all", 2000000000) == "full" and full.progression.crystals == 1999999990 and full.indexZoneRewards == nil, "wallet cap: no change")
local newer = {collection = coll(meadow, #meadow.species), progression = {crystals = 0}, indexZoneRewards = "v2"}
check(Z.apply(newer, "meadow", "all", 2000000000) == "invalid_state" and newer.progression.crystals == 0, "a newer field is never touched")
local nowallet = {collection = coll(meadow, #meadow.species)}
check(Z.apply(nowallet, "meadow", "all", 2000000000) == "no_wallet" and nowallet.indexZoneRewards == nil, "no wallet: nothing")
local step, st = Z.current(meadow, #meadow.species, {"meadow_half", "meadow_all"})
check(st == "claimed", "all claimed")
step, st = Z.current(meadow, 0, {})
check(step == "half" and st == "locked", "first goal")
check(#Z.goal(meadow, "half", 0) <= 14 and #Z.goal(meadow, "all", 0) <= 14 and Z.progress(4, meadow) == "4/" .. #meadow.species, "short words")

-- the repository claim + the remote handler, with an in-memory store
local cfg = require("Config")
local store = {reads = 0, writes = 0, data = nil}
function store:UpdateAsync(_, fn)
    self.reads += 1
    local copy = table.clone(self.data)
    copy.progression = table.clone(self.data.progression)
    local out = fn(copy)
    if out ~= nil then self.writes += 1 self.data = out end
    return out
end
local player = {UserId = 7, SetAttribute = function() end}
local profiles = {}
local Repo = {isLoaded = function() return true end}
local shared = {Config = cfg, ProgressionConfig = {MaxCrystals = 2000000000}, admitAs = function() return function() return true end end,
    adopt = function(pl, prof) profiles[pl] = prof end, handleLeaseLost = function() end, isValidProfile = function(x) return type(x) == "table" end,
    keyFor = function() return "k" end, ownSession = function() return true end, profiles = profiles, retry = function(_, fn) return true, fn() end,
    store = store, syncAttributes = function() end}
require("ProfileIndexZones")(Repo, shared)
local Service = require("IndexZoneService")
local function fresh(k)
    store.data = {revision = 1, session = {expiresAt = 0}, collection = coll(Z.zone("beach"), k), progression = {crystals = 5}}
    profiles[player] = store.data
    store.reads, store.writes = 0, 0
end
-- flag off: nothing read or written
cfg.IndexZonesEnabled = false
fresh(#Z.zone("beach").species)
check(Service.start(Repo) == nil, "flag off: no remote")
local a = Service.handle(player, {action = "claim", zone = "beach", step = "all"})
local ok, why = Repo.claimIndexZone(player, "beach", "all")
check(a.ok == false and a.status == "disabled" and ok == false and why == "disabled" and store.reads == 0 and store.writes == 0, "flag off: nothing read or written")
-- flag on
cfg.IndexZonesEnabled = true
Service.start(Repo)
local t = 0
Service.TryGap = 0
fresh(Z.need(Z.zone("beach"), "half"))
a = Service.handle(player, {action = "claim", zone = "beach", step = "half"})
check(a.ok == true and a.status == "applied" and a.crystals == Z.Crystals.half and store.data.progression.crystals == 5 + Z.Crystals.half, "claim pays")
a = Service.handle(player, {action = "claim", zone = "beach", step = "half"})
check(a.ok == true and a.status == "already" and a.crystals == 0 and store.data.progression.crystals == 5 + Z.Crystals.half, "second claim: already, nothing paid")
profiles[player] = nil -- a second server (no cached word): the transform still guards
local ok2, st2, c2 = Repo.claimIndexZone(player, "beach", "half")
check(ok2 == true and st2 == "already" and c2 == 0 and store.data.progression.crystals == 5 + Z.Crystals.half, "double claim across servers pays once")
profiles[player] = store.data
a = Service.handle(player, {action = "claim", zone = "beach", step = "all"})
check(a.ok == false and a.status == "not_reached" and store.data.progression.crystals == 5 + Z.Crystals.half, "not reached")
for _, bad in {{action = "claim", zone = "beach", step = "all", crystals = 99999}, {action = "give", zone = "beach", step = "all"},
        {action = "claim", zone = 3, step = "all"}, {action = "claim", zone = "beach"}, {action = "claim", zone = "atlantis", step = "all"}, "claim", nil} do
    local r = Service.handle(player, bad)
    check(r.ok == false and r.status == "bad_request", "bad request refused")
end
local r = Service.handle(player, {action = "claim", zone = "beach", step = "half"}, 500)
check(r.ok == false and r.status == "bad_request", "an extra argument is refused")
-- rate limit
Service.TryGap, Service.PerMinute = 0, 3
fresh(0)
local limited = false
for i = 1, 6 do if Service.handle({UserId = 99}, {action = "claim", zone = "meadow", step = "half"}).status == "rate_limited" then limited = true end end
check(limited, "rate limited")
if #fails > 0 then print("FAIL " .. table.concat(fails, "; ")) else print("OK") end
'''


def run(runner, texts):
    order = species_order(texts['config'])
    mods = {'IndexZones': texts['rules'], 'ProfileIndexZones': texts['part'], 'IndexZoneService': texts['service'],
            'Config': 'return {IndexZonesEnabled = false, ProfileLeaseSeconds = 300}'}
    shim = [
        'local loaders, cache = {}, {}',
        'local function require(name) if cache[name] == nil then cache[name] = loaders[name]() end return cache[name] end',
        'local services = {ReplicatedStorage = {Shared = {Config = "Config", IndexZones = "IndexZones"}, FindFirstChild = function() return nil end}}',
        'local Instance = {new = function(kind) return {Name = "", kind = kind} end}',
        'local game = {GetService = function(_, name) return services[name] end}',
        'local script = {Parent = setmetatable({}, {__index = function(_, k) return k end})}',
        'local os = {clock = function() return 0 end, time = os.time}',
        'local ORDER = {%s}' % ', '.join('"%s"' % s for s in order),
    ]
    for name, text in mods.items():
        shim.append('loaders["%s"] = function()\n%s\nend' % (name, text.replace('--!strict', '')))
    source = '\n'.join(shim) + '\n' + LUAU
    with tempfile.NamedTemporaryFile('w', suffix='.luau', delete=False, encoding='utf-8') as handle:
        handle.write(source)
        path = handle.name
    result = subprocess.run([runner, path], capture_output=True, text=True, timeout=60)
    Path(path).unlink(missing_ok=True)
    out = (result.stdout + result.stderr).strip()
    return out.splitlines()[-1] if out else 'FAIL no output'


def guards(t):
    problems = []
    if len(re.findall(r'^    IndexZonesEnabled = false,$', t['config'], re.M)) != 1:
        problems.append('Config.IndexZonesEnabled must ship false exactly once')
    for needle in ('_flag_off("IndexZonesEnabled",', 'Rule("IndexZonesEnabled", "set", True,', '("IndexZonesEnabled", "BD-1299'):
        if needle not in t['profiles']:
            problems.append('release_profiles.py misses ' + needle)
    if '"IndexZonesEnabled"' not in t['playtest']:
        problems.append('the playtest manifest must show IndexZonesEnabled')
    if 'if Config.IndexZonesEnabled == true then require(script.Parent.IndexZoneService).start(' not in t['social']:
        problems.append('the service starts only with the flag on')
    if 'if Config.IndexZonesEnabled ~= true or repository == nil then return answer(false, "disabled") end' not in t['service'].split('function Service.handle', 1)[-1].split(chr(10))[1]:
        problems.append('the remote handler must test the flag first')
    if 'if Config.IndexZonesEnabled ~= true then return nil end' not in t['service']:
        problems.append('start() must return at once with the flag off')
    if 'if Config.IndexZonesEnabled ~= true then return false, "disabled", 0 end' not in t['part'].split('function ProfileRepository.claimIndexZone', 1)[-1].split('\n')[1]:
        problems.append('the claim must test the flag first')
    if 'require(script.Parent.ProfileIndexZones)(ProfileRepository, shared)' not in t['repo']:
        problems.append('the repository part must be loaded')
    if 'if Config.IndexZonesEnabled == true then PrivateState.set(player, "IndexZonesJson"' not in t['repo']:
        problems.append('the private value is set only with the flag on')
    if '"IndexZonesJson"' not in t['pscore'].split('local PUBLIC', 1)[0]:
        problems.append('IndexZonesJson must be an owner-only private value')
    if '(Config :: any).IndexZonesEnabled == true then return require(script.Parent.DinoIndexZones).build(body, d) end' not in t['kit']:
        problems.append('the kit Index shows the zones only with the flag on')
    if 'PROVISIONAL' not in t['rules'].split('M.Zones', 1)[0]:
        problems.append('the species split must be marked PROVISIONAL')
    if 'function M.indexZonesLayout' not in t['layout']:
        problems.append('the zones layout lives in SaeMenuRules')
    code = '\n'.join(line.split('--', 1)[0] for line in (t['rules'] + t['part'] + t['service'] + t['client']).splitlines())
    for banned in ('Robux', 'MarketplaceService', 'ProductId', 'PromptPurchase', 'math.random', 'Random.new'):
        if banned in code:
            problems.append('no paid line, no random item: ' + banned)
    if 'crystals = request' in code or 'request.crystals' in code or 'request.amount' in code:
        problems.append('the amount never comes from the request')
    return problems


MUTANTS = {
    'paid twice': ('rules', '    if M.claimed(stored)[key] then return "already", 0 end\n', ''),
    'not reached is paid': ('rules', '    if M.found(profile.collection, zone) < M.need(zone, step) then return "not_reached", 0 end\n', ''),
    'half rounds down': ('rules', 'math.ceil(n / 2)', 'math.floor(n / 2)'),
    'no wallet cap': ('rules', '    if wallet.crystals + crystals > maxCrystals then return "full", 0 end\n', ''),
    'a newer field is overwritten': ('rules', '    if stored ~= nil and (typeof(stored) ~= "table" or #stored > M.MaxStored) then return "invalid_state", 0 end\n', ''),
    'the word is not stored': ('rules', '    table.insert(list, key)\n', ''),
    'a species in two zones': ('rules', '"tyrannosaurus", "ankylosaurus"', '"tyrannosaurus", "compy", "ankylosaurus"'),
    'a species missing': ('rules', '"tyrannosaurus", "ankylosaurus"', '"ankylosaurus"'),
    'zone order': ('rules', 'name = "Beach"', 'name = "Sand"'),
    'flag ignored by the claim': ('part', '    if Config.IndexZonesEnabled ~= true then return false, "disabled", 0 end\n', ''),
    'flag ignored by the service': ('service', '    if Config.IndexZonesEnabled ~= true or repository == nil then return answer(false, "disabled") end\n', '    if repository == nil then return answer(false, "disabled") end\n'),
    'extra keys accepted': ('service', '        if key ~= "action" and key ~= "zone" and key ~= "step" then return false end\n', ''),
    'extra arguments accepted': ('service', 'if select("#", ...) ~= 0 or not validate(request)', 'if not validate(request)'),
    'no rate limit': ('service', '    if not allowed(player, os.clock()) then return answer(false, "rate_limited") end\n', ''),
    'the transform pays outside the guard': ('part', '            if result ~= "applied" then return nil end\n', '            if result ~= "applied" then profile.progression.crystals += 1 return profile end\n'),
    'the service always starts': ('social', 'if Config.IndexZonesEnabled == true then require(script.Parent.IndexZoneService)', 'if true then require(script.Parent.IndexZoneService)'),
}
RUN_SIDES = ('rules', 'part', 'service', 'config')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    texts = {k: read(v) for k, v in FILES.items()}
    out = run(args.runner, texts)
    problems = guards(texts)
    if out != 'OK' or problems:
        print('verify_index_zones FAILED:', out, problems)
        return 1
    if not args.no_mutants:
        survived = []
        for name, (where, old, new) in MUTANTS.items():
            assert old in texts[where], 'mutant target missing: ' + name
            mutated = dict(texts)
            mutated[where] = texts[where].replace(old, new, 1)
            killed = bool(guards(mutated)) or (where in RUN_SIDES and run(args.runner, mutated) != 'OK')
            if not killed:
                survived.append(name)
        if survived:
            print('verify_index_zones FAILED: mutants survived:', survived)
            return 1
        print('verify_index_zones: %d mutants killed' % len(MUTANTS))
    print('verify_index_zones OK: zones, exactly-once claim, remote validation, flag off = nothing read or written, source guards')
    return 0


if __name__ == '__main__':
    sys.exit(main())
