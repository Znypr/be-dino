"""Execute the final-outcome enumerator against the actual Luau configuration."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text() + '\nend)()'


def script():
    return 'local Config=' + module('src/shared/Config.luau') + '\nlocal Progression=' + module('src/shared/ProgressionConfig.luau') + '''
local script={Parent={ProgressionConfig="Progression"}}
local require=function()return Progression end
''' + 'local Genetics=' + module('src/shared/EggGenetics.luau') + '''
local script={Parent={Config="Config",ProgressionConfig="Progression",EggGenetics="Genetics"}}
local require=function(id)return if id=="Config" then Config elseif id=="Genetics" then Genetics else Progression end
''' + 'local Odds=' + module('src/shared/EggOutcomeOdds.luau') + '''
local function close(a,b) assert(math.abs(a-b)<1e-10,tostring(a).." != "..tostring(b)) end
local function sum(rows) local n=0 for _,r in rows do n+=r.weight end return n end
local mode=Odds.blendMode()
local bins=if mode=="uniform" then 99 else 101
local histogram={}
for i=0,bins-1 do
 local rolls={.5,.5,.25,.65,(i+.5)/bins,.5};local next=0
 local g=Genetics.roll(0,{NextNumber=function() next+=1 return rolls[next] or .5 end})
 histogram[g.blend]=(histogram[g.blend] or 0)+1
 close(g.primaryColorId==g.secondaryColorId and 1 or 0,0)
end
for share=0,100 do close((histogram[share] or 0)/bins,Odds.shareProbability("white","blue",share)) end
local patternCount=#Odds.patterns()
local colorCount=#Progression.EggColors
local shares=if mode=="legacy" then colorCount^2*101 else colorCount+(colorCount^2-colorCount)*99
local full=Odds.catalog(0)
local fullProbability=0
for i=1,full.count do
 local row=full.at(i)
 assert(row.probability>0)
 fullProbability+=row.probability
end
close(fullProbability,1)
for tier=0,#Progression.ConditionWeights-1 do
 local all=Odds.catalog(tier)
 assert(all.count==#Config.ChestSpeciesWeights*#Config.ChestQuantityWeights*#Progression.Conditions*patternCount*2*shares+1)
 close(all.at(1).probability,Odds.failure(tier)) assert(all.at(1).failed)
 assert(all.at(0)==nil and all.at(all.count+1)==nil and all.at(.5)==nil)
 local rows=Odds.catalog(tier,{primary="white",secondary="white"})
 local probability=0
 for i=1,rows.count do
  local r=rows.at(i)
  assert(not r.failed and r.primaryId=="white" and r.secondaryId=="white")
  probability+=r.probability
 end
 close(probability,(1-Odds.failure(tier))*(Progression.EggColors[1].weight/sum(Progression.EggColors))^2)
end
local filters={species="compy",condition="astra",primary="black",secondary="black",copies=3,big=true,pattern=Odds.patterns()[1]}
local rare=Odds.catalog(0,filters)
assert(rare.count==(if mode=="legacy" then 101 else 1))
local r=rare.at(1)
assert(r.speciesId=="compy" and r.conditionId=="astra" and r.big and r.count==3)
local formatted=Odds.percent(r.probability)
assert(string.find(formatted,"%%") and tonumber(string.sub(formatted,1,-2))>0,"rare odds rounded to zero")
close(tonumber(string.sub(formatted,1,-2))/100,r.probability)
assert(Odds.catalog(0,{species="missing"}).count==0)
local patterns=Genetics.Patterns
local originalMode=Genetics.BlendMode
Genetics.Patterns=nil Genetics.BlendMode=nil
assert(Odds.blendMode()=="legacy") close(Odds.shareProbability("black","black",0),1/101)
Genetics.Patterns=patterns or {"01_blank"} Genetics.BlendMode="uniform"
close(Odds.shareProbability("white","blue",1),1/99)
close(Odds.shareProbability("white","blue",99),1/99)
close(Odds.shareProbability("black","black",100),1)
Genetics.Patterns=patterns Genetics.BlendMode=originalMode
print("Outcome odds passed: full normalization, actual blend roll parity, every tier, lazy enumeration, filters, rare precision, legacy and uniform modes")
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'outcomes.luau'
        path.write_text(script())
        subprocess.run([args.runner, str(path)], check=True)
