"""Run actual rarity weights and independent trait rolls in pinned Luau."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text() + '\nend)()'


def script():
    return 'local Config=' + module('src/shared/Config.luau') + '''
local script={Parent={Config=true}}
local require=function()return Config end
local game={GetService=function()return {Shared={Config=true}}end}
''' + 'local Traits=' + module('src/shared/EggTraits.luau') + '\nlocal Rewards=' + module('src/server/RewardMath.luau') + '''
for _,weather in {"clear","rain","thunder","blizzard","volcano","aurora","quake","bloodmoon"} do
 local shiny,big,stacked=0,0,0
 for a=0,99 do for b=0,99 do
  local t=Traits.roll(weather,(a+.5)/100,(b+.5)/100)
  shiny+=if t.shiny then 1 else 0
  big+=if t.big then 1 else 0
  stacked+=if t.shiny and t.big then 1 else 0
 end end
 assert(big==1000)
 assert(shiny==(if Config.IrregularWeather[weather] then 500 else 0))
 assert(stacked==(if Config.IrregularWeather[weather] then 50 else 0))
end
assert(not Traits.roll("volcano",.05,.1).shiny and not Traits.roll("volcano",.05,.1).big)
assert(Traits.valid({[':shiny:big']={mutationId="",shiny=true,big=true,count=1}}))
assert(not Traits.valid({['bad']={mutationId="",shiny=true,big=true,count=1}}))
local previousRare,previousLegend=0,0
for count=1,15 do
 local seen={}
 local rare,legend=0,0
 for i=0,9999 do
  local call=0
  local rng={NextNumber=function(_,low,high)
   call+=1
   return (if call==1 then (i+.5)/10000 else .1)*(high-low)+low
  end}
  local reward=Rewards.computeChestReward(rng,count)
  seen[reward.speciesId]=true
  local rarity=Config.SpeciesRarities[reward.speciesId]
  rare+=if rarity>=2 then 1 else 0
  legend+=if rarity==3 then 1 else 0
 end
 for _,id in Config.SpeciesOrder do assert(seen[id],"species missing: "..id) end
 assert(rare>previousRare and legend>previousLegend,"rarity boost not monotonic")
 previousRare,previousLegend=rare,legend
end
print("Egg rules passed: all six species, monotonic 1-15 egg rarity boost, exact independent 5% Shiny/10% BIG and 0.5% stacked outcomes")
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'eggs.luau'
        path.write_text(script())
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
