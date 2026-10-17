"""BD-365 / BD-301: the Egg Odds panel tells a brand-new player "Your first 2 eggs from runs are always safe." (never Cracked).

Checks, with the real Luau modules and the real config:
  * the line exists on a brand-new profile and is gone for every profile that has used its safe eggs (only where true);
  * its number is built from ProgressionConfig.SafeEggs (one source: change it and the line follows) and equals the
    server rule: FtueRules.SafeEggs / safeEggsLeft(brand-new profile), and a safe roll is never Cracked;
  * the rule is run-egg only (shop eggs roll normal odds), which is why the line says "from runs";
  * text size >= 14 (FtueP1.MinTextSize) on both screens that show it, docs/72 copy rules hold.
Not Studio evidence: see docs/evidence/2026-10-17-egg-odds/.
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (docs/150: ProfileRepository plus its parts)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_odds_copy as base  # noqa: E402

BODY = r'''
local Random = {new = function(seed)
    local state = seed * 2654435761 % 4294967296
    return {NextNumber = function()
        state = (state * 1664525 + 1013904223) % 4294967296
        return state / 4294967296
    end}
end}
local function brand() return {collection = {compy = {base = 1, gold = 0, diamond = 0, variants = {}, events = {}}},
    recentOperations = {}, eggs = {}, runEggBank = {}, pendingChestGrants = 0} end

-- the server rule on a brand-new profile
local serverLeft = Ftue.safeEggsLeft(brand())
assert(serverLeft == Ftue.SafeEggs and Ftue.SafeEggs == Progression.SafeEggs and serverLeft == 2, "server rule: 2 safe eggs")
-- client view gives the same answer for a brand-new profile, so the panel and the server agree
local copies = Ftue.collectionCopies(brand().collection)
local viewLeft = Ftue.safeEggsLeftView(copies, 0, 0)
assert(viewLeft == serverLeft, "client view == server rule")

-- the line exists on a fresh profile and carries exactly the server number
local line = Copy.safeEggsLine(viewLeft)
assert(line ~= nil, "line shows on a brand-new profile")
local numbers = {}
for n in (line :: string):gmatch("%d+") do table.insert(numbers, tonumber(n)) end
assert(#numbers == 1 and numbers[1] == serverLeft and numbers[1] == Ftue.SafeEggs, "one number, equal to the server rule")

-- only where true: nothing once a safe egg is used, hatched or waiting; nothing for nil or junk
assert(Copy.safeEggsLine(1) == nil and Copy.safeEggsLine(0) == nil and Copy.safeEggsLine(nil) == nil)
assert(Copy.safeEggsLine(Ftue.safeEggsLeftView(2, 0, 0)) == nil, "a hatched copy beyond the starter")
assert(Copy.safeEggsLine(Ftue.safeEggsLeftView(1, 1, 0)) == nil and Copy.safeEggsLine(Ftue.safeEggsLeftView(1, 0, 38)) == nil, "eggs waiting")

-- the egg odds groups: the line is the note of "Is the egg Cracked?", only on a fresh profile; upgrade odds never carry it
for level = 0, #Progression.ConditionWeights - 1 do
    local fresh = Copy.eggGroups(level, viewLeft)
    assert(fresh[3].title == "Is the egg Cracked?" and fresh[3].note == line, "fresh profile: note on level " .. level)
    assert(Copy.eggGroups(level, 0)[3].note == nil and Copy.eggGroups(level)[3].note == nil, "used up: no note")
    assert(Copy.upgradeGroups(level)[1].note == nil, "upgrade odds are not run eggs")
    for _, g in fresh do local total = 0 for _, r in g.rows do total += r.percent end assert(math.abs(total - 100) < 1e-6) end
end

-- the rule is real: a safe roll is never Cracked, an ordinary roll is Cracked about half the time (tier 0)
local safeRng, normalRng, cracked = Random.new(11), Random.new(11), 0
for i = 1, 4000 do
    assert(Genetics.roll(0, safeRng, true).conditionId ~= "cracked", "safe roll cracked")
    if Genetics.roll(0, normalRng).conditionId == "cracked" then cracked += 1 end
end
assert(cracked > 1700 and cracked < 2300, "normal rolls still crack ~50%: " .. cracked)

-- docs/72 copy rules for children
local l = line :: string
assert(#l <= 50, "short")
assert(l:find("always safe", 1, true) and l:find("from runs", 1, true), "plain words and scope")
assert(not l:find("%d+%.%d") and not l:find("%d+[xXmsh]%f[%W]") and not l:find("%%"), "no decimals, multipliers, times or percents")
for _, jargon in {"transform", "window", "idle", "ledger", "tier", "roll", "chance", "server", "profile", "threshold", "probability"} do
    assert(not l:lower():find(jargon, 1, true), "jargon: " .. jargon)
end
assert(l:sub(-1) == "." and not l:find("!!") and not l:find("  "))
assert(Copy.NoteTextSize >= Ftue1.MinTextSize and Ftue1.MinTextSize == 14, "note text size >= 14")
print("safe eggs line passed: " .. l)
'''


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


# Single source: a copy of the config with SafeEggs=5 must produce a line with 5 and nothing else changed by hand.
ALT = r'''
local line5 = Copy.safeEggsLine(5)
assert(line5 ~= nil and line5:find("5", 1, true) and not line5:find("2", 1, true), "the line is built from ProgressionConfig.SafeEggs")
assert(Copy.safeEggsLine(2) == nil, "fewer safe eggs than the rule gives: no line")
print("safe eggs line follows the config number: " .. line5)
'''


def alt_script():
    s = base.script().replace(base.BODY, '')
    assert s.count('SafeEggs=2,') == 1
    return s.replace('SafeEggs=2,', 'SafeEggs=5,') + ALT


def script():
    s = base.script().replace(base.BODY, '')
    s += 'local Ftue=' + module('src/shared/FtueRules.luau') + '\n'
    s += 'local Ftue1=' + module('src/shared/FtueP1.luau') + '\n'
    s += 'local Genetics=' + module('src/shared/EggGenetics.luau') + '\n'
    return s + BODY


def static_checks():
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    odds = (ROOT / 'src/shared/OddsCopy.luau').read_text(encoding='utf-8')
    repo = profile_sources.repository_text()
    # panel wiring: egg odds get the safe-eggs count, upgrade odds do not; the note is drawn at the shared >= 14 size
    assert re.search(r'OddsCopy\.eggGroups\(progression\(\)\.conditionLevel or 0,require\(Shared\.FtueRules\)\.safeEggsLeftView\(', boot), 'Egg Odds passes the safe-eggs view'
    assert 'OddsCopy.upgradeGroups(oddsLevelOverride :: number)' in boot, 'Upgrade Odds does not'
    assert 'label(list,group.note,10,lineY,790,28,OddsCopy.NoteTextSize)' in boot, 'note drawn at OddsCopy.NoteTextSize'
    m = re.search(r'label\(body,safeLine,0,cardsY,824,30,(\d+)', boot)
    assert m and int(m.group(1)) >= 14, 'Conditions tab line is drawn at >= 14'
    assert 'ConditionsHeader' not in boot
    # one source: no sentence with the number typed by hand anywhere in src
    for path in (ROOT / 'src').rglob('*.luau'):
        text = path.read_text(encoding='utf-8')
        assert 'SafeEggsLine' not in text and 'ConditionsHeader' not in text, f'{path.name}: old duplicated line still referenced'
        assert not re.search(r'first 2 (run )?eggs are', text, re.I), f'{path.name}: hand-typed number in a sentence'
    assert 'string.format("Your first %d eggs from runs are always safe."' in odds and 'Progression.SafeEggs' in odds
    # the rule covers RUN eggs only: settlement applies it, the shop purchase and nest eggs do not
    assert 'FtueRules.safeEggsLeft(cached)' in repo and 'EggGenetics.roll(if progress then progress.conditionLevel else 0, rng, true)' in repo
    assert 'result.genes=EggGenetics.roll(if p then p.conditionLevel else 0,rng)\n' in repo, 'shop eggs still roll normal odds: the line must keep saying "from runs"'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as d:
        alt = Path(d) / 'alt.luau'
        alt.write_text(alt_script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(alt)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        if result.returncode:
            raise SystemExit(result.returncode)
        path = Path(d) / 'safe_eggs_line.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        if result.returncode == 0:
            print('safe eggs line: static wiring ok')
        raise SystemExit(result.returncode)
