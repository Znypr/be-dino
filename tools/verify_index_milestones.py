#!/usr/bin/env python3
"""BD-1230 (docs/242 benchmark gap 15): Dino Index milestone rewards behind Config.IndexMilestonesEnabled.

Runs the REAL Shared/IndexMilestones in the pinned Luau runtime and checks: the found count is the server's ownsAny test over Config.SpeciesOrder
(secrets never counted), the percent is floored like the Index bar, each step is granted EXACTLY ONCE (a second transform on the stored profile
grants nothing), several steps reached at once are all paid, crystals clamp to the wallet cap, a save without a wallet or with a newer build's
field is never touched, the stored field is additive (nothing else in the profile changes), and the kid words are short.
Source guards: the flag ships false (once), is pinned off in the default profile, ON in the playtest profile, the rehearsal list and the manifest;
the grant sits inside the claimChest UpdateAsync transform behind the flag; the private value is owner-only and set only with the flag; the
client toast returns first with the flag off; no remote is added; the rewards are crystals only (no Robux, no paid line).
The mutants put each defect back and a check must fail. NOT Studio evidence (pictures: docs/evidence/2026-11-16-ui-feedback).
Usage: python tools/verify_index_milestones.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RULES = 'src/shared/IndexMilestones.luau'
CLIENT = 'src/client/IndexMilestoneCue.client.luau'
EGGS = 'src/server/ProfileEggs.luau'
REPO = 'src/server/ProfileRepository.luau'
LIST = 'src/client/DinoIndexList.luau'
FLAG_LINE = 'if (Config :: any).IndexMilestonesEnabled ~= true then return end'
GRANT_LINE = 'if Config.IndexMilestonesEnabled == true then indexMilestones().applyToProfile(profileValue, Config.SpeciesOrder, ProgressionConfig.MaxCrystals) end'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local order = {}
for i = 1, 20 do table.insert(order, "s" .. i) end
local function coll(n)
    local c = {}
    for i = 1, n do c["s" .. i] = {base = 1} end
    c.secret_duck = {base = 3} -- a secret is not in the order: never counted
    return c
end
check(M.found(coll(5), order) == 5, "found counts owned species of the order only")
check(M.found({s1 = {base = 0}, s2 = {gold = 1}, s3 = {variants = {x = 1}}, s4 = {events = {e = 1}}}, order) == 3, "ownsAny: base 0 is not owned")
check(M.found(nil, order) == 0, "no collection")
check(M.percent(5, 20) == 25 and M.percent(4, 20) == 20 and M.percent(7, 22) == 31, "floored percent")
check(M.percent(3, 0) == 0, "no species")
-- exactly once
local p = {collection = coll(5), progression = {crystals = 10}, other = "keep"}
local g = M.applyToProfile(p, order, 2000000000)
check(#g == 1 and g[1].step == 25 and g[1].crystals == M.Crystals[25], "25 % granted")
check(p.progression.crystals == 10 + M.Crystals[25], "crystals added")
check(p.indexMilestones and p.indexMilestones[1] == "25", "step stored as text")
local again = M.applyToProfile(p, order, 2000000000)
check(#again == 0 and p.progression.crystals == 10 + M.Crystals[25], "never twice")
check(p.other == "keep", "nothing else changes")
-- several at once
local q = {collection = coll(20), progression = {crystals = 0}}
local all = M.applyToProfile(q, order, 2000000000)
check(#all == 4 and q.progression.crystals == M.Crystals[25] + M.Crystals[50] + M.Crystals[75] + M.Crystals[100], "all reached steps paid")
-- a drop after fusion does not re-grant or take back
q.collection = coll(1)
check(#M.applyToProfile(q, order, 2000000000) == 0, "a lower count later grants nothing")
-- clamp
local r = {collection = coll(5), progression = {crystals = 1999999990}}
M.applyToProfile(r, order, 2000000000)
check(r.progression.crystals == 2000000000, "wallet cap")
-- untouched cases
local nw = {collection = coll(5)}
check(#M.applyToProfile(nw, order, 2000000000) == 0 and nw.indexMilestones == nil, "no wallet: nothing")
local newer = {collection = coll(20), progression = {crystals = 0}, indexMilestones = "v2"}
check(#M.applyToProfile(newer, order, 2000000000) == 0 and newer.progression.crystals == 0, "a newer build's field is never touched")
local none = {collection = coll(4), progression = {crystals = 0}}
check(#M.applyToProfile(none, order, 2000000000) == 0 and none.indexMilestones == nil, "below 25 %: no field created")
-- words
check(M.nextHint(4, 20, {}) == "1 more: +" .. M.Crystals[25], "next hint")
check(M.nextHint(5, 20, {}) == "+" .. M.Crystals[25] .. " soon!", "reached, paid next hatch")
check(M.nextHint(5, 20, {"25"}) == "5 more: +" .. M.Crystals[50], "next step after a paid one")
check(M.nextHint(20, 20, {"25", "50", "75", "100"}) == "", "all paid: no line")
check(M.needFor(25, 22) == 6 and M.needFor(100, 22) == 22, "need for a step")
check(M.toast(25) == "Dino Index 25%!" and M.toast(100) == "You found every dino!", "toast words")
check(M.toastBody(50) == "+50 Crystals", "toast body")
for _, step in M.Steps do
    check(M.Crystals[step] and M.Crystals[step] > 0 and M.Crystals[step] <= 1000, "a modest free reward at " .. step)
    check(#M.toast(step) <= 24 and #M.nextHint(0, 22, {}) <= 18, "short words")
end
if #fails > 0 then print("FAIL " .. table.concat(fails, "; ")) else print("OK") end
'''


def run_rules(runner, rules_text):
    source = 'local M = (function()\n' + rules_text + '\nend)()\n' + LUAU
    with tempfile.NamedTemporaryFile('w', suffix='.luau', delete=False, encoding='utf-8') as handle:
        handle.write(source)
        path = handle.name
    result = subprocess.run([runner, path], capture_output=True, text=True, timeout=60)
    Path(path).unlink(missing_ok=True)
    out = (result.stdout + result.stderr).strip()
    return out.splitlines()[-1] if out else 'FAIL no output'


def guards(texts):
    problems = []
    config, profiles, playtest = texts['config'], texts['profiles'], texts['playtest']
    if len(re.findall(r'^    IndexMilestonesEnabled = false,$', config, re.M)) != 1:
        problems.append('Config.IndexMilestonesEnabled must ship false exactly once')
    for needle in ('_flag_off("IndexMilestonesEnabled",', 'Rule("IndexMilestonesEnabled", "set", True,', '("IndexMilestonesEnabled", "BD-1230'):
        if needle not in profiles:
            problems.append('release_profiles.py misses ' + needle)
    if '"IndexMilestonesEnabled"' not in playtest:
        problems.append('the playtest manifest must show IndexMilestonesEnabled')
    eggs = texts['eggs']
    if GRANT_LINE not in eggs:
        problems.append('the grant must run behind the flag inside claimChest')
    else:
        claim = eggs.split('function ProfileRepository.claimChest', 1)[1]
        transform = claim.split('store:UpdateAsync', 1)[1].split('end)\n    end)', 1)[0]
        if GRANT_LINE not in transform:
            problems.append('the grant must sit INSIDE the claimChest UpdateAsync transform (exactly once with the hatch)')
    if eggs.count('indexMilestones()') != 1:
        problems.append('the grant has one call site')
    if 'if Config.IndexMilestonesEnabled == true then PrivateState.set(player, "IndexMilestonesJson"' not in texts['repo']:
        problems.append('the private value is set only with the flag on')
    if '"IndexMilestonesJson"' not in texts['core']:
        problems.append('IndexMilestonesJson must be an owner-only private value')
    client = texts['client']
    head = client.split('local Milestones = require', 1)[0]
    if FLAG_LINE not in head:
        problems.append('the toast script must return first with the flag off')
    code = '\n'.join(line.split('--', 1)[0] for line in (client + texts['rules']).splitlines())
    for banned in ('FireServer', 'InvokeServer', 'RemoteEvent', 'RemoteFunction', 'DataStore', 'Robux', 'MarketplaceService', 'ProductId'):
        if banned in code:
            problems.append('no remote, no store, no paid line: ' + banned)
    if '(Config :: any).IndexMilestonesEnabled == true and lay.meter.w >= 300' not in texts['list']:
        problems.append('the Index bar hint only with the flag on')
    return problems


MUTANTS = {
    'secrets counted': ('rules', '    for _, id in order do\n        if ownsAny(collection[id]) then n += 1 end\n    end', '    for _, entry in collection do\n        if ownsAny(entry) then n += 1 end\n    end'),
    'granted twice': ('rules', 'if percent >= step and not done[step] then', 'if percent >= step then'),
    'percent rounded up': ('rules', 'return math.floor(math.clamp(found, 0, total) / total * 100 + 1e-9)', 'return math.ceil(math.clamp(found, 0, total) / total * 100)'),
    'no wallet cap': ('rules', 'wallet.crystals = math.min(maxCrystals, wallet.crystals + crystals)', 'wallet.crystals = wallet.crystals + crystals'),
    'a newer field is overwritten': ('rules', 'if stored ~= nil and (typeof(stored) ~= "table" or #stored > M.MaxStored) then return out end', ''),
    'the step is not stored': ('rules', '        table.insert(profile.indexMilestones, tostring(step))\n', ''),
    'the field is created for nothing': ('rules', '    if #due == 0 then return out end\n', '    profile.indexMilestones = profile.indexMilestones or {}\n    if #due == 0 then return out end\n'),
    'the grant leaves the transaction': ('eggs', '            ' + GRANT_LINE + '\n', ''),
    'the flag is ignored by the toast': ('client', FLAG_LINE, ''),
    'the toast calls the server': ('client', 'local gui = Players', 'ReplicatedStorage.X:FireServer()\nlocal gui = Players'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    texts = {'rules': read(RULES), 'client': read(CLIENT), 'eggs': read(EGGS), 'repo': read(REPO), 'list': read(LIST),
             'core': read('src/shared/PrivateStateCore.luau'), 'config': read('src/shared/Config.luau'),
             'profiles': read('tools/release_profiles.py'), 'playtest': read('tools/release_playtest.py')}
    out = run_rules(args.runner, texts['rules'])
    problems = guards(texts)
    if out != 'OK' or problems:
        print('verify_index_milestones FAILED:', out, problems)
        return 1
    if not args.no_mutants:
        survived = []
        for name, (where, old, new) in MUTANTS.items():
            assert old in texts[where], 'mutant target missing: ' + name
            mutated = dict(texts)
            mutated[where] = texts[where].replace(old, new, 1)
            killed = (run_rules(args.runner, mutated['rules']) != 'OK') if where == 'rules' else bool(guards(mutated))
            if not killed:
                survived.append(name)
        if survived:
            print('verify_index_milestones FAILED: mutants survived:', survived)
            return 1
        print('verify_index_milestones: %d mutants killed' % len(MUTANTS))
    print('verify_index_milestones OK: rules, exactly-once grant, flag wiring and source guards')
    return 0


if __name__ == '__main__':
    sys.exit(main())
