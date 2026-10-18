"""BD-1033 / docs/186 s4: pattern rarity on the 8 existing patterns, proved with the REAL modules in Luau.
Covers: Genetics.Patterns is built from the one table (ProgressionConfig.EggPatterns) in the old id order, every Build 020 pattern id
is still valid (nothing stored is rewritten), seeded rolls are deterministic and match the table's cumulative weights, a seeded
sample follows the table, the disclosed odds (ShopOdds, EggOutcomeOdds) use the same chances and show kid names (no ids), the hatch
reveal reports the declared tier, and kid names are short and unique. Mocks check numbers, not feel or Studio.
"""
from pathlib import Path
import argparse, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


def sandbox(path, parents):
    """Module text wrapped so `require(script.Parent.X)` returns the already-built table named in `parents` (X -> Luau variable)."""
    shim = '{' + ','.join(f'{k}={v}' for k, v in parents.items()) + '}'
    return ('(function() local script={Parent=' + shim + '} local require=function(x) return x end return '
            + module(path) + ' end)()')


BODY = r'''
local function near(a, b, e) assert(math.abs(a - b) <= (e or 1e-9), tostring(a) .. " vs " .. tostring(b)) end
local function sum(rows) local s = 0 for _, r in rows do s += r.weight end return s end
local rows = PC.EggPatterns
-- 1. The id list is built from the table, in table order; the Build 020 ids are all still valid and none was dropped.
local legacy = {"01_blank","02_emerald_islands","03_round_spots","04_bold_patches","05_horizontal_bands","06_wavy_stripes","07_diamond_scales","08_freckles"}
assert(#G.Patterns == #rows and #rows == #legacy)
for i, row in rows do assert(G.Patterns[i] == row.id and G.Patterns[i] == legacy[i], "order kept: " .. row.id) end
for _, id in legacy do
    assert(table.find(G.Patterns, id), "legacy id kept " .. id)
    assert(G.valid({primaryColorId = "white", secondaryColorId = "white", hatchSuccess = true, blend = 100, patternId = id}), "valid " .. id)
end
assert(not G.valid({primaryColorId = "white", secondaryColorId = "white", hatchSuccess = true, blend = 100, patternId = "99_nope"}))
assert(G.valid(G.neutral("normal")) and G.neutral("normal").patternId == "01_blank")
-- 2. Chances and info come from the table.
local total = sum(rows)
for _, r in rows do
    near(G.patternChance(r.id), r.weight / total) near(G.patternInfo(r.id).pct, 100 * r.weight / total, 1e-9)
    assert(G.patternInfo(r.id).name == r.name and G.patternInfo(r.id).rarity == r.rarity)
    assert(G.Patterns.info[r.id] == G.patternInfo(r.id))
end
for k, v in G.Patterns do assert(type(k) == "number" and type(v) == "string", "iterating the list yields ids only") end
assert(G.patternChance("nope") == nil and G.patternInfo("nope") == nil)
-- 3. Seeded rolls: one pattern draw (the 6th), cumulative weights decide, same numbers give the same dinosaur.
local function rollWith(values)
    local i = 0
    return G.roll(0, {NextNumber = function() i += 1 return values[i] or .5 end})
end
local function expected(r)
    local v = r * total
    for _, row in rows do v -= row.weight if v < 0 then return row.id end end
    return rows[#rows].id
end
local cum = 0
for _, row in rows do
    local mid = (cum + row.weight / 2) / total cum += row.weight -- the middle of each pattern's slice of 0..1
    local g = rollWith({.5, .5, .25, .65, .5, mid})
    assert(g.patternId == row.id, "slice middle -> " .. row.id .. " got " .. g.patternId)
end
for _, r in {0, .1, .2667, .27, .5, .8, .9, .96, .999, .9999999, 1} do
    assert(rollWith({.5, .5, .25, .65, .5, r}).patternId == expected(r), "cumulative pick at " .. r)
end
assert(rollWith({.5, .5, .25, .65, .5, 0}).patternId == "01_blank" and rollWith({.5, .5, .25, .65, .5, 1}).patternId == rows[#rows].id)
for seed = 1, 50 do
    local function seq() math.randomseed(seed) local out = {} for k = 1, 6 do out[k] = math.random() end return out end
    local a, b = rollWith(seq()), rollWith(seq())
    assert(G.key(a) == G.key(b), "same numbers, same dinosaur")
    assert(G.valid(a), "rolled genes are valid")
end
do -- 6 draws per egg as before; the pattern is the last one
    local n = 0 G.roll(0, {NextNumber = function() n += 1 return .3 end}) assert(n == 6, "6 draws per egg, as before")
    assert(rollWith({.1, .9, .9, .9, .9, .3}).patternId == rollWith({.9, .1, .1, .1, .1, .3}).patternId)
end
-- 4. A seeded sample follows the table (5 sigma), and a rarer tier is seen less.
do
    local N = 200000 math.randomseed(1018)
    local rng = {NextNumber = function() return math.random() end}
    local counts = {} for _, r in rows do counts[r.id] = 0 end
    for _ = 1, N do local g = G.roll(0, rng) counts[g.patternId] += 1 end
    for _, r in rows do
        local p = r.weight / total local sd = math.sqrt(N * p * (1 - p))
        assert(math.abs(counts[r.id] - N * p) <= 5 * sd, string.format("%s seeded %d vs %.1f", r.id, counts[r.id], N * p))
    end
    for _, a in rows do for _, b in rows do
        if Curve.index(a.rarity) < Curve.index(b.rarity) then assert(counts[a.id] > counts[b.id], a.id .. " must be seen more than " .. b.id) end
    end end
end
-- 5. Kid names: short, unique, no ids and no digits; the hatch screen name function uses them.
local names = {}
for _, r in rows do
    assert(not names[r.name]) names[r.name] = true
    assert(#r.name >= 3 and #r.name <= 12 and not string.find(r.name, "[%d_]"), r.name)
    assert(Sel.patternName(r.id) == r.name, "FusionSelection.patternName gives the kid name for " .. r.id)
end
assert(Sel.patternName("99_old_thing") == "Old Thing" and Sel.patternName("") == "Unknown pattern" and Sel.patternName(nil) == "Unknown pattern")
-- 6. Disclosure: ShopOdds lists every pattern with its tier and the table's percent; no ids; EggOutcomeOdds uses the same chances.
local text = table.concat(ShopOdds.lines(0), "\n")
assert(not string.find(text, "equally likely"), "patterns are no longer equally likely")
assert(not string.find(text, "%d%d_%l"), "no pattern ids shown to players")
for _, r in rows do
    local line = string.format("%s (%s): %.4f%%", r.name, r.rarity, 100 * r.weight / total)
    assert(string.find(text, line, 1, true), "ShopOdds line missing: " .. line)
end
do
    local speciesP = Config.ChestSpeciesWeights[1].weight / sum(Config.ChestSpeciesWeights)
    local colourP = (PC.EggColors[1].weight / sum(PC.EggColors)) ^ 2
    local conditionP = PC.ConditionWeights[1][3] / PC.ConditionWeightScale -- Normal
    local base = conditionP * speciesP * colourP * (1 - Config.BigChance)
    local acc = 0
    for _, r in rows do
        near(Odds.patternChance(r.id), r.weight / total)
        local c = Odds.catalog(0, {species = "compy", condition = "normal", primary = "white", secondary = "white", big = false, copies = 1, pattern = r.id})
        assert(c.count == 1)
        near(c.at(1).probability, base * r.weight / total, 1e-12)
        acc += c.at(1).probability
    end
    near(acc, base, 1e-12) -- the pattern chances add up to 100%
end
-- 7. Hatch reveal: the declared tier and the real chance; blank stays "Plain".
for _, r in rows do
    local rv = T.patternReveal(G.Patterns, r.id, Sel.patternName)
    if string.find(r.id, "blank", 1, true) then assert(rv.plain and rv.name == "Plain" and rv.tierName == "Common")
    else assert(not rv.plain and rv.name == r.name and rv.tierName == r.rarity, r.id .. " tier " .. tostring(rv.tierName)) end
    near(rv.pct, 100 * r.weight / total, 1e-9)
end
assert(T.patternReveal({"01_blank", "03_x"}, "03_x", tostring).pct == 50, "a list without info is treated as equally likely")
print(string.format("Patterns passed: %d patterns from one table, ids and order kept, seeded rolls deterministic and follow the weights, odds text and hatch tier match, kid names short and unique", #rows))
'''


def script():
    return ('local Curve=' + module('src/shared/RarityCurve.luau') + '\n'
            'local Config=' + module('src/shared/Config.luau') + '\n'
            'local PC=' + module('src/shared/ProgressionConfig.luau') + '\n'
            'local G=' + sandbox('src/shared/EggGenetics.luau', {'ProgressionConfig': 'PC'}) + '\n'
            'local Sel=' + sandbox('src/shared/FusionSelection.luau', {'ProgressionConfig': 'PC'}) + '\n'
            'local Odds=' + sandbox('src/shared/EggOutcomeOdds.luau', {'Config': 'Config', 'ProgressionConfig': 'PC', 'EggGenetics': 'G'}) + '\n'
            'local T=' + sandbox('src/shared/HatchTimeline.luau', {'RevealSkip': '{}', 'HatchV2Plan': '{}'}) + '\n'
            'local ShopOdds=' + sandbox('src/shared/ShopOdds.luau', {'Config': 'Config', 'ProgressionConfig': 'PC', 'EggOutcomeOdds': 'Odds'}) + '\n'
            + BODY)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'patterns.luau'
        path.write_text(script(), encoding='utf-8')
        r = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
    print(r.stdout, end='')
    print(r.stderr, end='')
    raise SystemExit(r.returncode)
