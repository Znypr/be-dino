"""BD-427: the three long-term goals lines (src/shared/GoalsRules.luau) run in the pinned Luau runtime, plus static
wiring checks for src/client/GoalsPanel.luau. Not Studio evidence: the panel is untested on screen/phone."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local order = {"compy", "rex", "raptor", "steg"}
local counts = Goals.speciesCounts({compy = {base = 2, gold = 0, diamond = 0}, rex = {base = 0, gold = 0, diamond = 0}, raptor = {base = 0, gold = 1}}, order,
    function(id) return id == "rex" end)
assert(counts.found == 3 and counts.owned == 2 and counts.total == 4, "found counts event/traits, owned counts copies")
assert(Goals.speciesCounts(nil, nil, nil).total == 0, "junk input never errors")

local c = Goals.collect(counts)
assert(c.progress == "3 of 4 found" and c.step == "1 more to find" and not c.done and c.fraction == 0.75)
assert(Goals.collect({found = 1, total = 22}).step == "Hatch eggs to find more")
assert(Goals.collect({found = 22, total = 22}).done and Goals.collect({found = 99, total = 22}).progress == "Everything found!")
assert(Goals.collect({}).fraction == 0 and Goals.collect({found = -3, total = 5}).progress == "0 of 5 found")

-- overall index: species + colours + patterns + mutations, derived from owned dinos and the collection
local dl = {{genes = {primaryColorId = "green", patternId = "p1"}, mutationId = "none"}, {genes = {primaryColorId = "blue", patternId = "p1"}, mutationId = "frost"}}
local col = {compy = {base = 1, events = {ember = 2}}, rex = {variants = {{count = 1, mutationId = "aurora"}, {count = 0, mutationId = "seismic"}}}}
local tot = {colours = 9, patterns = 8, mutations = 7}
local ic = Goals.indexCounts(col, {"compy", "rex"}, nil, dl, tot)
assert(ic.found == 1 and ic.total == 2, "species fields unchanged")
assert(ic.parts.colours.found == 2 and ic.parts.patterns.found == 1 and ic.parts.mutations.found == 3 and ic.parts.mutations.total == 7)
local oc = Goals.collect(ic)
assert(oc.progress == "7 of 26 found", oc.progress)
assert(oc.step == "Find new patterns" or oc.step == "Find new colours" or oc.step == "Hatch eggs to find more", oc.step)
assert(oc.fraction == 7 / 26)
local ic2 = Goals.indexCounts({compy = {base = 1}, rex = {base = 1}}, {"compy", "rex"}, nil, dl, tot)
assert(Goals.collect(ic2).step == "Find new patterns", Goals.collect(ic2).step)
local full = Goals.indexCounts({a = {base = 1}}, {"a"}, nil, {{genes = {primaryColorId = "x", patternId = "y"}, mutationId = "m"}}, {colours = 1, patterns = 1, mutations = 1})
assert(Goals.collect(full).done and Goals.collect(full).progress == "Everything found!")
assert(Goals.indexCounts(nil, nil, nil, nil, nil).parts.colours.total == 0, "junk input never errors")
assert(Goals.collect(Goals.indexCounts(nil, nil, nil, nil, nil)).fraction == 0)

local function dino(species, stage) return {speciesId = species, stage = stage, genes = {patternId = "p"}} end
local list = {} for i = 1, 4 do table.insert(list, dino("compy", "base")) end
local o = {dinos = list, stages = Goals_stages, speciesName = function(id) return "Compy" end, patternName = function(id) return id end}
local p = Goals.perfect(o)
assert(p.progress == "Gold: 4/6 Compy" and p.step == "Hatch more of the same" and not p.ready, p.progress)
for i = 5, 6 do table.insert(list, dino("compy", "base")) end
p = Goals.perfect(o)
assert(p.step == "Tap FUSION now!" and p.fraction == 1)
assert(Goals.perfect({dinos = nil}).progress == "Pick a favourite" and Goals.perfect({dinos = {}}).step == "Collect copies, then FUSION")
local d = Goals.perfect({dinos = {dino("rex", "diamond")}})
assert(d.done and d.progress == "Diamond dino!")

local pl = Goals.play(counts)
assert(pl.progress == "2 dinos to play" and pl.step == "Hatch a new kind to try" and pl.fraction == 0.5)
assert(Goals.play({owned = 1, total = 4}).progress == "1 dino to play")
assert(Goals.play({owned = 4, total = 4}).done)

local lines = Goals.lines({species = counts, dinos = list, speciesName = function() return "Compy" end})
assert(#lines == 3 and lines[1].id == "collect" and lines[2].id == "perfect" and lines[3].id == "play")
assert(#Goals.lines(nil) == 3, "no data still gives three lines")
local all = {lines, Goals.lines({species = {found = 22, owned = 22, total = 22}, dinos = {dino("rex", "diamond")}})}
for _, set in all do
    for _, l in set do
        for _, text in {l.title .. ": " .. l.progress, "Next: " .. l.step} do
            assert(#text <= Goals.MaxLine, text)
            assert(not text:find("%dm") and not text:find("%dx") and not text:lower():find("catch") and not text:lower():find("bank"), text)
        end
        assert(l.fraction >= 0 and l.fraction <= 1)
    end
end
print("goals rules passed")
'''


def script():
    s = 'local NextGoalSrc = ' + module('src/shared/NextGoal.luau') + '\n'
    s += 'local script = {Parent = {NextGoal = "ng"}}\nlocal realRequire = require\n'
    s += 'local require = function(id) return NextGoalSrc end\n'
    s += 'local Goals_stages = NextGoalSrc.Stages\n'
    s += 'local Goals = ' + module('src/shared/GoalsRules.luau') + '\n' + BODY
    return s


def static_checks():
    rules = (ROOT / 'src/shared/GoalsRules.luau').read_text(encoding='utf-8')
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'os.clock', 'task.'):
        assert banned not in rules, 'GoalsRules stays pure: ' + banned
    panel = (ROOT / 'src/client/GoalsPanel.luau').read_text(encoding='utf-8')
    assert 'rbxassetid' not in panel and 'ImageLabel' not in panel, 'no new art ids in the Goals panel'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert 'GoalsPanel).attach(gui,goalHUD' in boot and 'GoalsPanel).setDinos' in boot and 'GoalsPanel).setSpecies' in boot and 'indexCounts' in boot
    assert not re.search(r'^local Goals', boot, re.M), 'no new top-level local in Bootstrap'
    assert len(re.findall(r'^local ', boot, re.M)) <= 195, 'Bootstrap top-level locals'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'goals.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            raise SystemExit(result.stderr or 'failed')
