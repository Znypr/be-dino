"""BD-270 / BD-267 / BD-269: kid-readable odds, shared shop-card state and Index progress.
Runs the real Luau modules against the real config; odds must sum to exactly 100% and match the config."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BODY = r'''
local function sumOf(rows) local n=0 for _,r in rows do n+=r.percent end return n end
local function near(a,b) return math.abs(a-b)<1e-6 end
-- rounding helper: always exactly 100, for awkward weights too
for _,w in {{1,1,1},{26,22,9,8,7,6,6,5,1},{1,2},{3},{0.1,0.2,0.7},{1,1,1,1,1,1,1}} do
 local r=Copy.round(w,2) local s=0 for _,v in r do s+=v end
 assert(near(s,100),"round sum "..s)
end
assert(Copy.text(26)=="26%" and Copy.text(12.5)=="12.5%" and Copy.text(0.04)=="0.04%")
for level=0,#Progression.ConditionWeights-1 do
 local groups=Copy.eggGroups(level)
 assert(#groups==3)
 for _,g in groups do
  assert(near(sumOf(g.rows),100),g.title.." level "..level.." sums to "..sumOf(g.rows))
  for _,row in g.rows do assert(row.percent>=0 and not row.text:find("[xX]%d") and row.text:find("%%")) end
 end
 -- species matches the config weights (within rounding to 0.01%)
 local total=0 for _,r in Config.ChestSpeciesWeights do total+=r.weight end
 local species=groups[2]
 assert(#species.rows==#Config.ChestSpeciesWeights)
 for i,r in Config.ChestSpeciesWeights do assert(math.abs(species.rows[i].percent-100*r.weight/total)<=0.0101,"species "..r.speciesId) end
 -- condition matches ShopOdds exactly (within rounding)
 local exact=ShopOdds.conditionPercents(level)
 for i,row in groups[3].rows do assert(math.abs(row.percent-exact[i])<=0.0101,"condition "..i) end
 -- hatch group matches the failure chance
 assert(math.abs(groups[1].rows[2].percent-100*Outcomes.failure(level))<=0.0101)
 assert(#Copy.upgradeGroups(level)==1 and near(sumOf(Copy.upgradeGroups(level)[1].rows),100))
end
-- BD-301: the Buy Egg confirm sentence and the Egg Odds panel come from the same numbers
for level=0,#Progression.ConditionWeights-1 do
 local hatch=Copy.hatchGroup(level).rows[1]
 local sentence=Copy.hatchSentence(level)
 assert(sentence:find(string.format("%g",hatch.percent).." of every 100 eggs hatch",1,true),"sentence "..sentence)
 assert(#sentence<=80 and not sentence:find("success"))
end
-- BD-303: plain unlock words
assert(Copy.upgradeUnlock(3,1)=="Reach level 3 to buy this." and Copy.upgradeUnlock(3,3)=="Ready to buy!" and Copy.upgradeUnlock(nil,9)=="Top level reached")
for lv=1,#Progression.ConditionUpgrades do
 local id=Copy.biggestGain(lv-1,lv) local ok=false
 for _,c in Progression.Conditions do if c.id==id then ok=true end end
 assert(ok,"biggestGain "..lv)
end
for _,isEgg in {true,false} do for _,n in Copy.notes(isEgg) do assert(#n<=70 and not n:find("%d+x")) end end
-- shop card state
assert(State.kind({})=="normal" and State.kind({owned=true})=="owned" and State.kind({left=0})=="soldOut")
assert(State.kind({left=2})=="normal" and State.kind({levelNeeded=6,level=3})=="locked" and State.kind({levelNeeded=6,level=6})=="normal")
assert(State.kind({owned=true,left=0})=="owned")
local sold=State.look({left=0},"30 Crystals")
assert(sold.dim and not sold.active and sold.buttonText=="SOLD OUT" and sold.tone=="calm" and not sold.caption:find("!!"))
local owned=State.look({owned=true},"30 Crystals") assert(owned.caption=="Owned" and owned.tone=="calm")
local normal=State.look({left=3},"30 Crystals") assert(normal.active and normal.caption=="30 Crystals  3 left" and normal.tone=="price")
assert(State.look({levelNeeded=6,level=2},"x").buttonText=="LEVEL 6")
-- index progress
local s=Progress.summary(0,23) assert(s.percent==0 and s.text=="Collected 0 of 23  (0%)" and not s.ticks[1].reached)
s=Progress.summary(6,23) assert(s.percent==26 and s.ticks[1].reached and not s.ticks[2].reached)
s=Progress.summary(23,23) assert(s.percent==100 and s.ticks[4].reached and s.fraction==1)
s=Progress.summary(99,23) assert(s.found==23)
assert(Progress.summary(0,0).percent==0)
local pg=Progress.page(200,24,1) assert(pg.pages==9 and pg.first==1 and pg.last==24)
pg=Progress.page(200,24,99) assert(pg.page==9 and pg.first==193 and pg.last==200)
pg=Progress.page(0,24,1) assert(pg.pages==1 and pg.last==0)
print("odds copy / shop card / index progress passed")
'''


def module(path):
    return '(function()\n' + (ROOT / path).read_text() + '\nend)()'


def script():
    s = 'local Config=' + module('src/shared/Config.luau') + '\n'
    s += 'local Progression=' + module('src/shared/ProgressionConfig.luau') + '\n'
    s += 'local script={Parent={}}\nlocal require=function() return Progression end\n'
    s += 'local Genetics=' + module('src/shared/EggGenetics.luau') + '\n'
    s += 'script={Parent={Config="Config",ProgressionConfig="Progression",EggGenetics="Genetics"}}\n'
    s += 'require=function(id)return if id=="Config" then Config elseif id=="Genetics" then Genetics else Progression end\n'
    s += 'local Outcomes=' + module('src/shared/EggOutcomeOdds.luau') + '\n'
    s += 'script={Parent={Config="Config",ProgressionConfig="Progression",EggOutcomeOdds="Outcomes"}}\n'
    s += 'require=function(id)return if id=="Config" then Config elseif id=="Outcomes" then Outcomes else Progression end\n'
    s += 'local ShopOdds=' + module('src/shared/ShopOdds.luau') + '\n'
    s += 'script={Parent={Config="Config",ProgressionConfig="Progression",ShopOdds="ShopOdds",EggOutcomeOdds="Outcomes"}}\n'
    s += 'require=function(id)return if id=="Config" then Config elseif id=="Outcomes" then Outcomes elseif id=="ShopOdds" then ShopOdds else Progression end\n'
    s += 'local Copy=' + module('src/shared/OddsCopy.luau') + '\n'
    s += 'local State=' + module('src/shared/ShopCardState.luau') + '\n'
    s += 'local Progress=' + module('src/shared/IndexProgress.luau') + '\n'
    return s + BODY


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'odds_copy.luau'
        path.write_text(script())
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
