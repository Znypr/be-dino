"""BD-1041 / docs/186 s7: the starter goals of the collection hunt ("Find 3 patterns", "Find 3 colours", "Find all Common patterns"), offline.

The goals are three tutorial rows of the existing objectives system (src/shared/ObjectiveConfig.luau, behind Config.ObjectivesEnabled). The SERVER counts
the finds (ProgressionRules.findCounts: the discovery log plus the dinos owned, the same sets the Index shows) and ObjectiveService.syncFinds sends a
running total only when it grew. The real behaviour is tested in tools/verify_objective_hooks.py (section E, real ProfileRepository + ObjectiveService on
the mocked DataStore) and tools/verify_objectives.py (the catalogue). This verifier adds:

1. CATALOGUE RULES: the three rows sit right after T3, are "total" rows with kid copy (docs/72), small Crystal-only rewards in line with their neighbours,
   and the last goal's number equals the number of Common rows in ProgressionConfig.EggPatterns (a retier makes this fail, so the copy never lies).
2. PARITY: ProgressionRules.findCounts (server) gives the same numbers as PatternColourIndex.foundSets + cards (client Index) for the same data.
3. MUTANTS: broken copies of the real sources are run through the hooks verifier and must FAIL: no sync after a hatch, a sync that never stops, a
   "total" that adds up, a count that forgets the accent colour, a count that includes ids that are no row, no sync on view.

Not Studio evidence: nothing here shows the Goals panel on a screen. Usage: python tools/verify_starter_goals.py --runner luau.exe
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_objective_hooks  # noqa: E402


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path):
    return '(function()\n' + read(path) + '\nend)()'


def check_catalogue():
    text = read('src/shared/ObjectiveConfig.luau')
    rows = re.findall(r'\{id = "(T\d+)", group = "tutorial", name = "([^"]+)", event = "([a-z_]+)"(, total = true)?, goal = (\d+), reward = \{crystals = (\d+)\}', text)
    order = [r[0] for r in rows]
    assert order[:6] == ['T1', 'T2', 'T3', 'T10', 'T11', 'T12'], 'the starter goals come right after "Hatch 3 eggs": ' + str(order)
    goals = {r[0]: r for r in rows if r[0] in ('T10', 'T11', 'T12')}
    assert [goals[k][1] for k in ('T10', 'T11', 'T12')] == ['Find 3 patterns', 'Find 3 colours', 'Find all Common patterns'], 'kid copy: short, plain (docs/72)'
    assert [goals[k][2] for k in ('T10', 'T11', 'T12')] == ['patterns_found', 'colours_found', 'common_patterns_found']
    for key, row in goals.items():
        assert row[3] == ', total = true', key + ' must be a total row (progress = the running total)'
        assert int(row[5]) <= 20, key + ' reward stays small (neighbours give 10 to 30)'
    assert sum(int(goals[k][5]) for k in goals) == 50, 'the three goals give 50 Crystals together (15 + 15 + 20, PROVISIONAL, docs/115)'
    assert 'Robux' not in text.split('local byId')[0].replace('never Robux', ''), 'no Robux in the catalogue'
    # the goal of T12 is the count of Common rows in the real pattern table
    config = read('src/shared/ProgressionConfig.luau')
    block = config[config.index('EggPatterns={'):]
    block = block[:block.index('\n    },')]
    common = len(re.findall(r'rarity="Common"', block))
    assert int(goals['T12'][4]) == common, 'T12 goal %s differs from the %d Common patterns in ProgressionConfig.EggPatterns' % (goals['T12'][4], common)
    assert int(goals['T10'][4]) <= len(re.findall(r'\{id="', block)) and int(goals['T11'][4]) <= 9
    print('  catalogue: T10 / T11 / T12 after T3, total rows, kid copy, 50 Crystals, T12 goal = %d Common patterns' % common)


PARITY = r'''
local ProgressionConfig = @@PROGRESSION_CONFIG@@
local Rules, Index
do
    local script = {Parent = {ProgressionConfig = "ProgressionConfig", EggGenetics = "EggGenetics", RarityCurve = "RarityCurve", GeneBoost = "GeneBoost"}}
    local Genetics, Curve, Boost
    local require = function(id)
        if id == "ProgressionConfig" then return ProgressionConfig elseif id == "EggGenetics" then return Genetics elseif id == "RarityCurve" then return Curve elseif id == "GeneBoost" then return Boost end
        error("unexpected " .. tostring(id))
    end
    Genetics = @@GENETICS@@
    Curve = @@CURVE@@
    Boost = @@BOOST@@
    Rules = @@RULES@@
    Index = @@INDEX@@
end
local P, C = ProgressionConfig.EggPatterns, ProgressionConfig.EggColors
local function variant(pattern, main, accent, count) return {count = count, genes = {patternId = pattern, primaryColorId = main, secondaryColorId = accent}} end
local function parity(profile, label)
    local order = {}
    for id in profile.collection do table.insert(order, id) end
    table.sort(order)
    local discovered = {ids = Rules.discoveryIds(profile)}
    local found = Index.foundSets(profile.collection, discovered, order)
    local server = Rules.findCounts(profile)
    local clientPatterns = Index.header("patterns", Index.cards("patterns", P, found, tostring)).found
    local clientColours = Index.header("colours", Index.cards("colours", C, found, tostring)).found
    local clientCommon = 0
    for _, card in Index.cards("patterns", P, found, tostring) do if card.found and card.tier == 0 then clientCommon += 1 end end
    assert(server.patterns == clientPatterns and server.colours == clientColours and server.commonPatterns == clientCommon,
        label .. ": server " .. server.patterns .. "/" .. server.colours .. "/" .. server.commonPatterns .. " vs client " .. clientPatterns .. "/" .. clientColours .. "/" .. clientCommon)
    return server
end
-- nothing: a brand new profile, a profile with junk in the optional fields
local empty = parity({collection = {}, progression = {}}, "empty")
assert(empty.patterns == 0 and empty.colours == 0 and empty.commonPatterns == 0)
for _, junk in {{}, {collection = 5, progression = "x"}, {collection = {compy = 3}, progression = {discovered = 7}}, {collection = {compy = {variants = 4}}}} do
    local c = Rules.findCounts(junk)
    assert(c.patterns == 0 and c.colours == 0 and c.commonPatterns == 0, "junk in the optional fields counts nothing")
end
assert(Rules.findCounts(nil).patterns == 0 and Rules.findCounts("x").colours == 0)
-- owned dinos only (an old save, no discovery log): main AND accent colours count, count 0 does not, ids that are no row do not
local owned = parity({collection = {
    compy = {base = 2, variants = {a = variant("03_round_spots", "blue", "red", 2), b = variant("07_diamond_scales", "white", "white", 1), z = variant("06_wavy_stripes", "teal", "pink", 0)}},
    raptor = {variants = {c = variant("not_a_pattern", "not_a_colour", "blue", 1)}},
}, progression = {}}, "owned")
assert(owned.patterns == 2 and owned.commonPatterns == 1 and owned.colours == 3, "owned: 2 patterns (1 Common), colours blue red white")
-- the log alone (every dino fused away) keeps the finds; the log and the owned dinos merge without double counting
local logged = parity({collection = {}, progression = {discovered = {patterns = {["01_blank"] = true, ["08_freckles"] = true, junk = true}, colours = {green = true, black = true, junk = true}}}}, "log")
assert(logged.patterns == 2 and logged.commonPatterns == 2 and logged.colours == 2, "the log: ids that are no row do not count")
local both = parity({collection = {compy = {variants = {a = variant("01_blank", "green", "green", 1)}}}, progression = {discovered = {patterns = {["01_blank"] = true}, colours = {green = true, white = true}}}}, "both")
assert(both.patterns == 1 and both.commonPatterns == 1 and both.colours == 2)
-- every pattern and colour found
local allPatterns, allColours = {}, {}
for _, row in P do allPatterns[row.id] = true end
for _, row in C do allColours[row.id] = true end
local everything = parity({collection = {}, progression = {discovered = {patterns = allPatterns, colours = allColours}}}, "everything")
assert(everything.patterns == #P and everything.colours == #C)
-- read-only
local snapshot = {collection = {compy = {variants = {a = variant("03_round_spots", "blue", "red", 1)}}}, progression = {discovered = {patterns = {}, colours = {}}}}
Rules.findCounts(snapshot)
assert(next(snapshot.progression.discovered.patterns) == nil and snapshot.collection.compy.variants.a.count == 1, "findCounts never writes")
print("Parity passed: the server count (ProgressionRules.findCounts) equals the Index count (PatternColourIndex) on 8 profiles, junk counts nothing, read-only")
'''


def parity_script():
    text = PARITY
    for token, path in (('@@PROGRESSION_CONFIG@@', 'src/shared/ProgressionConfig.luau'), ('@@GENETICS@@', 'src/shared/EggGenetics.luau'),
                        ('@@CURVE@@', 'src/shared/RarityCurve.luau'), ('@@BOOST@@', 'src/shared/GeneBoost.luau'),
                        ('@@RULES@@', 'src/shared/ProgressionRules.luau'), ('@@INDEX@@', 'src/shared/PatternColourIndex.luau')):
        text = text.replace(token, module(path))
    return text


def run(runner, source, name):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


# (name, [(old, new)]) applied to the generated hooks script, where the real sources are inlined. Each must be caught.
MUTANTS = [
    ('no sync after a hatch claim', [('    ObjectiveService.syncFinds(player) -- BD-1041: this claim may have found a new pattern or colour\n', '')]),
    ('a sync that never stops (sends the same total again and again)', [('count > (last[find.key] or 0)', 'count > -1')]),
    ('a total row that adds up instead of keeping the highest', [('return math.max(current, math.min(cap(entry), math.floor(value)))', 'return math.min(cap(entry), current + math.floor(value))')]),
    ('P: the accent colour is not counted', [('add(colours,v.genes.secondaryColorId)', '')]),
    ('P: an id that is no pattern row is counted', [('for _,row in Config.EggPatterns do\n        if patterns[row.id] then\n            out.patterns+=1', 'for id in patterns do\n        if true then\n            out.patterns+=1'),
                                                   ('            if row.rarity=="Common" then out.commonPatterns+=1 end', '            if id=="01_blank" or id=="03_round_spots" or id=="08_freckles" then out.commonPatterns+=1 end')]),
    ('a view does not sync the finds', [('if request.action ~= "seen" then ObjectiveService.syncFinds(player) end', 'if false then ObjectiveService.syncFinds(player) end')]),
    ('P: every pattern is counted as Common', [('if row.rarity=="Common" then out.commonPatterns+=1 end', 'out.commonPatterns+=1')]),
]


def check_mutants(runner):
    """Mutants named "P: ..." break the pure count (run against the parity script); the others run against the real-repository hooks script."""
    hooks = verify_objective_hooks.dynamic_script()
    baseline = run(runner, hooks, 'hooks.luau')
    assert baseline.returncode == 0 and 'Starter goals passed' in baseline.stdout, 'the unmutated hooks script must pass first: ' + baseline.stdout + baseline.stderr
    parity = parity_script()
    for name, edits in MUTANTS:
        pure = name.startswith('P: ')
        text = parity if pure else hooks
        for old, new in edits:
            assert old in text, 'mutant target missing (%s): %s' % (name, old[:60])
            text = text.replace(old, new)
        result = run(runner, text, 'mutant.luau')
        marker = 'Parity passed' if pure else 'Starter goals passed'
        assert result.returncode != 0 or marker not in result.stdout, 'MUTANT SURVIVED (the tests did not notice): ' + name
        print('  mutant caught: ' + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    check_catalogue()
    result = run(args.runner, parity_script(), 'parity.luau')
    print(result.stdout, end='')
    if result.returncode or 'Parity passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        check_mutants(args.runner)
    print('Starter goals verification passed (BD-1041): catalogue, server count = Index count, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
