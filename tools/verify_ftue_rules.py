"""BD-365..368: first-time-player rules (docs/112). Runs the real Shared/FtueRules and Shared/EggGenetics in Luau.

BD-365: a brand-new profile's first 2 eggs are never Cracked (safe); others re-weighted proportionally; seeded roll is
deterministic; veteran profiles keep the normal odds; the odds sum to 100%. BD-366/367/368: hint, egg moment and collapsed
menu decisions. Static checks cover the wiring (no new top-level local in Bootstrap, no new persistent field, Sfx alias
reuses a registered cue). Not Studio evidence: see docs/evidence/2026-10-16-ftue-fixes/.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (docs/150: ProfileRepository plus its parts)


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


LUAU = r'''
-- Plain Luau has no Random class: a small deterministic stand-in with the same NextNumber() API.
local Random = {new = function(seed)
    local state = seed * 2654435761 % 4294967296
    return {NextNumber = function()
        state = (state * 1664525 + 1013904223) % 4294967296
        return state / 4294967296
    end}
end}
local Progression = PROGRESSION
local Ftue = FTUE
local script = {Parent = {ProgressionConfig = "Progression"}}
local require = function(id) return Progression end
local Genetics = GENETICS

-- profiles
local function brand() return {collection = {compy = {base = 1, gold = 0, diamond = 0, variants = {}, events = {}}, raptor = {base = 0, gold = 0, diamond = 0}},
    recentOperations = {}, eggs = {}, pendingChestGrants = 0} end
assert(Ftue.collectionCopies(brand().collection) == 1)
assert(Ftue.safeEggsLeft(brand()) == 2, "new profile: 2 safe eggs")
assert(Ftue.safeEggsLeft(nil) == 2 and Ftue.hatchedEggs("x") == 0, "junk input never errors")
local one = brand() table.insert(one.recentOperations, {id = "chest:a", kind = "chest_claim"})
assert(Ftue.safeEggsLeft(one) == 1, "one hatch used one safe egg")
local two = brand() for i = 1, 2 do table.insert(two.recentOperations, {kind = "chest_claim"}) end
assert(Ftue.safeEggsLeft(two) == 0)
local waiting = brand() waiting.eggs = {{}} waiting.runEggBank = {{}}
assert(Ftue.safeEggsLeft(waiting) == 0, "eggs already rolled and waiting use the safe slots")
local grants = brand() grants.pendingChestGrants = 1
assert(Ftue.safeEggsLeft(grants) == 1)
local veteran = brand() veteran.collection.raptor.base = 3
assert(Ftue.safeEggsLeft(veteran) == 0, "older profile with copies and no operations left is not new")
local variantVet = brand() variantVet.collection.raptor.variants = {k = {count = 2}}
assert(Ftue.safeEggsLeft(variantVet) == 0)
local other = brand() table.insert(other.recentOperations, {kind = "run"})
assert(Ftue.safeEggsLeft(other) == 2, "only hatches count")

-- condition roll
local crackedIndex
for i, c in Progression.Conditions do if c.id == "cracked" then crackedIndex = i end end
assert(crackedIndex == 1)
local function sample(level, safe, seed, n)
    local rng = Random.new(seed)
    local counts, failed = {}, 0
    for _ = 1, n do
        local g = Genetics.roll(level, rng, safe)
        assert(Genetics.valid(g))
        counts[g.conditionId] = (counts[g.conditionId] or 0) + 1
        if not g.hatchSuccess then failed += 1 end
    end
    return counts, failed
end
local N = 60000
local safeCounts, safeFailed = sample(0, true, 7, N)
assert((safeCounts.cracked or 0) == 0 and safeFailed == 0, "safe eggs are never Cracked and always hatch")
-- other conditions keep their proportions: dirty:normal:rainbow:astra = 30:15:4.5:0.5 out of 50
local w = Progression.ConditionWeights[1]
local rest = w[2] + w[3] + w[4] + w[5]
for i = 2, 5 do
    local id = Progression.Conditions[i].id
    local expected = w[i] / rest
    local got = (safeCounts[id] or 0) / N
    assert(math.abs(got - expected) < 0.01, id .. " proportion " .. got .. " vs " .. expected)
end
local normalCounts, normalFailed = sample(0, nil, 7, N)
assert(math.abs((normalCounts.cracked or 0) / N - 0.5) < 0.01, "after the safe eggs Cracked is 50% again")
assert(math.abs(normalFailed / N - 0.4) < 0.01, "implied 40% failures unchanged")
local falsy = sample(0, false, 7, 1000)
local againFalse = sample(0, false, 7, 1000)
assert(falsy.cracked == againFalse.cracked, "deterministic")
local a, b = Random.new(99), Random.new(99)
for _ = 1, 50 do
    local x, y = Genetics.roll(0, a, true), Genetics.roll(0, b, true)
    assert(Genetics.key(x) == Genetics.key(y) and x.hatchSuccess == y.hatchSuccess, "seeded safe roll is deterministic")
end
for level = 0, #Progression.ConditionWeights - 1 do
    local counts = sample(level, true, level + 1, 3000)
    assert((counts.cracked or 0) == 0, "every upgrade level: safe means no Cracked")
end
-- the re-weighted odds still sum to 100%
local sum = 0 for _, v in Ftue.withoutCracked(w, 1) do sum += v end
assert(sum == rest and Ftue.withoutCracked(w, 1) ~= w and w[1] == 5000, "input table untouched")
local pct = 0 for i = 2, 5 do pct += 100 * w[i] / rest end
assert(math.abs(pct - 100) < 1e-9)
assert(Progression.SafeEggs == Ftue.SafeEggs and Ftue.SafeEggs == 2, "one number, two modules that must agree")
-- client view of the rule (BD-365): fresh = all safe eggs left; a hatched copy or waiting eggs use them up
assert(Ftue.safeEggsLeftView(1, 0, 0) == 2 and Ftue.safeEggsLeftView(2, 0, 0) == 0 and Ftue.safeEggsLeftView(1, 1, 0) == 1)
assert(Ftue.safeEggsLeftView(1, 40, 0) == 0 and Ftue.safeEggsLeftView(1, 0, 5) == 0 and Ftue.safeEggsLeftView(0, -3, -3) == 2)
assert(Ftue.safeEggsLeftView(1, 0, 0) == Ftue.safeEggsLeft(brand()), "client view equals the server rule on a brand-new profile")

-- BD-366 hint
assert(Ftue.hint({running = true, hasFoundEgg = false}) == "Eat food to grow. Bigger dinos find eggs!")
assert(Ftue.hint({running = true, hasFoundEgg = false, nearSpecialFood = true}) == "Look for a glowing egg!")
assert(Ftue.hint({running = true, hasFoundEgg = true, nearSpecialFood = true}) == nil, "gone after the first egg")
assert(Ftue.hint({running = false, hasFoundEgg = false}) == nil and Ftue.hint(nil) == nil)
for _, line in {Ftue.HintGrow, Ftue.HintNear, Ftue.FoundText, Ftue.MenuChipText} do
    assert(not line:lower():find("catch") and not line:lower():find("bank") and not line:find("%dm") and not line:find("%dx"), line)
end
assert(#Ftue.HintGrow <= 44 and #Ftue.HintNear <= 30)
assert(Ftue.isSpecialFood("egg") and Ftue.isSpecialFood("amber") and not Ftue.isSpecialFood("berry") and not Ftue.isSpecialFood(nil))
assert(not Ftue.hasFoundEgg({}) and not Ftue.hasFoundEgg(nil))
assert(Ftue.hasFoundEgg({sessionCatch = true}) and Ftue.hasFoundEgg({activeEggs = 1}) and Ftue.hasFoundEgg({lastRunEggs = 3}))
assert(Ftue.hasFoundEgg({waitingEggs = 5}) and Ftue.hasFoundEgg({copies = 2}) and not Ftue.hasFoundEgg({copies = 1, activeEggs = 0}))
-- BD-440: goal line and Goals panel hidden on a brand-new profile, shown after the first egg
assert(not Ftue.showGoals({copies = 1, activeEggs = 0, waitingEggs = 0, lastRunEggs = 0}) and not Ftue.showGoals(nil))
assert(Ftue.showGoals({lastRunEggs = 1}) and Ftue.showGoals({copies = 3}))

-- BD-367 moment
assert(Ftue.momentAllowed(0, 1, true, nil, 0), "first egg: moment")
assert(not Ftue.momentAllowed(nil, 1, true, nil, 0), "first reading is not a find")
assert(not Ftue.momentAllowed(1, 1, true, 99, 0) and not Ftue.momentAllowed(3, 1, true, 99, 0), "no change / reset")
assert(not Ftue.momentAllowed(0, 1, false, nil, 0), "not outside a run")
assert(not Ftue.momentAllowed(1, 2, true, 1, 1), "one at a time: min gap")
assert(Ftue.momentAllowed(1, 2, true, 5, 1))
assert(not Ftue.momentAllowed(10, 11, true, 60, Ftue.MomentsPerRun), "a long run does not spam")
assert(Ftue.sparkle(true) == Ftue.SparkleCount and Ftue.sparkle(false) == 0, "Reduce Motion: no burst")

-- BD-368 rail
assert(Ftue.collapseForRun(true, false) and not Ftue.collapseForRun(true, true) and not Ftue.collapseForRun(false, false))
for _, d in {"collection", "eggs", "fusion", "auras"} do
    assert(not Ftue.buttonVisible(d, true, false) and Ftue.buttonVisible(d, true, true) and Ftue.buttonVisible(d, false, false))
end
for _, d in {"potions", "settings"} do assert(Ftue.buttonVisible(d, true, false), d .. " stays") end
assert(Ftue.chipVisible(true, false) and not Ftue.chipVisible(true, true) and not Ftue.chipVisible(false, false))
print("ftue rules: safe first eggs, hint, egg moment, collapsed menu ok")
'''


def script():
    body = LUAU.replace('PROGRESSION', module('src/shared/ProgressionConfig.luau'))
    body = body.replace('FTUE', module('src/shared/FtueRules.luau'))
    body = body.replace('GENETICS', module('src/shared/EggGenetics.luau'))
    return body


def static_checks():
    rules = (ROOT / 'src/shared/FtueRules.luau').read_text(encoding='utf-8')
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'os.clock', 'task.', 'require('):
        assert banned not in rules, 'FtueRules stays pure: ' + banned
    repo = profile_sources.repository_text()
    assert 'FtueRules.safeEggsLeft(cached)' in repo and 'EggGenetics.roll(' in repo, 'settlement applies safe eggs'
    assert repo.index('sortByRarity(runEggs)') < repo.index('FtueRules.safeEggsLeft(cached)'), 'safe eggs are chosen after the rarity sort'
    assert 'safeEggs' not in repo.replace('safeEggsLeft', ''), 'no new persistent field'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    from bootstrap_sources import MAX_TOP_LOCALS
    assert len(re.findall(r'^local ', boot, re.M)) <= MAX_TOP_LOCALS, 'Bootstrap top-level locals'
    assert 'FtueRail).attach(rail,navigationButtons)' in boot and not re.search(r'^local Ftue', boot, re.M)
    sfx = (ROOT / 'src/shared/SfxRules.luau').read_text(encoding='utf-8')
    assert 'egg_found = {cue = "pickup_hi"' in sfx, 'the egg cue reuses a registered sound'
    hud = (ROOT / 'src/client/HudV2.luau').read_text(encoding='utf-8')
    assert 'rbxassetid' not in hud and 'Ftue.sparkle(Theme.MotionEnabled)' in hud and 'Ftue.momentAllowed' in hud
    odds = (ROOT / 'src/shared/OddsCopy.luau').read_text(encoding='utf-8')
    assert 'Copy.safeEggsLine(safeLeft)' in odds, 'the odds panel says the first eggs are safe (tools/verify_safe_eggs_line.py)'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'ftue_rules.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        if result.returncode:
            raise SystemExit(result.stdout[-3000:] + result.stderr)
        print(result.stdout.strip())
        print('ftue rules: static wiring ok')
