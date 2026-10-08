"""Run actual rarity weights and independent trait rolls in pinned Luau."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text() + '\nend)()'


def script():
    return 'local Progression=' + module('src/shared/ProgressionConfig.luau') + '\nlocal script={Parent={ProgressionConfig=true}}\nlocal require=function()return Progression end\nlocal Genetics=' + module('src/shared/EggGenetics.luau') + '\nlocal Config=' + module('src/shared/Config.luau') + '''
local script={Parent={Config="Config",EggGenetics="Genetics",GeneTextureAssets="TextureAssets"}}
local require=function(id)return if id=="Genetics" then Genetics elseif id=="TextureAssets" then {} else Config end
local game={GetService=function()return {Shared={Config=true}}end}
''' + 'local Traits=' + module('src/shared/EggTraits.luau') + '\nlocal Textures=' + module('src/shared/GeneTextures.luau') + '\nlocal Rewards=' + module('src/server/RewardMath.luau') + '''
local pixels=buffer.create(8)
for i,value in {40,180,240,123,20,22,29,255} do buffer.writeu8(pixels,i-1,value) end
local neutral,w,h=Textures.neutralPixels(pixels,2,1)
assert(w==2 and h==1 and buffer.readu8(neutral,0)==240 and buffer.readu8(neutral,1)==240 and buffer.readu8(neutral,2)==240 and buffer.readu8(neutral,3)==123)
assert(buffer.readu8(neutral,4)==29 and buffer.readu8(neutral,7)==255)
local wide=buffer.create(1024*4)
buffer.writeu8(wide,8,201) buffer.writeu8(wide,11,99)
local resized,rw,rh=Textures.neutralPixels(wide,1024,1)
assert(rw==512 and rh==1 and buffer.len(resized)==2048 and buffer.readu8(resized,4)==201 and buffer.readu8(resized,7)==99)
print("Gene texture pixels passed: painted-value detail and alpha retained; bounded 512px neutral texture sampling")
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
assert(Config.BigScaleMultiplier==1.2)
assert(#Progression.Trails==10 and Progression.Trails[1].id=="white" and Progression.Trails[10].id=="astra")
local previousCracked,previousAstra=100,0
for level,weights in Progression.ConditionWeights do
 local total=0 for _,weight in weights do total+=weight end
 assert(total==100 and weights[1]<previousCracked and weights[5]>previousAstra)
 previousCracked,previousAstra=weights[1],weights[5]
 local seen={} local failed=0
 for i=0,99 do
  for j=0,99 do
   local n=0
   local rng={NextNumber=function()n+=1 return if n==1 then (i+.5)/100 elseif n==2 then (j+.5)/100 else .5 end}
   local genes=Genetics.roll(level-1,rng)
   assert(Genetics.valid(genes))
   seen[genes.conditionId]=(seen[genes.conditionId] or 0)+1
   if not genes.hatchSuccess then failed+=1 assert(genes.conditionId=="cracked") end
  end
 end
 for k,condition in Progression.Conditions do assert(seen[condition.id]==weights[k]*100) end
 assert(failed==weights[1]*80)
end
local palette={}
for i=0,9999 do
 local n=0 local rng={NextNumber=function()n+=1 return if n==3 then (i+.5)/10000 else .5 end}
 local g=Genetics.roll(0,rng)
 palette[g.primaryColorId]=(palette[g.primaryColorId] or 0)+1
end
for _,color in Progression.EggColors do assert(palette[color.id]==color.weight) end
assert(palette.black==1)
assert(not Genetics.valid({conditionId="astra",hatchSuccess=false,primaryColorId="white",secondaryColorId="black",blend=80}))
for i,trail in Progression.Trails do
 if i>1 then local prior=Progression.Trails[i-1] assert(trail.level>prior.level and trail.price>prior.price and trail.speed>prior.speed) end
end
print("Genetics passed: seven exact condition distributions, 20% Cracked hatch success, weighted color slots, 1-in-10000 Black, size-only BIG 1.2x and ten increasing trail tiers")
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
print("Egg rules passed: all 22 species, monotonic 1-15 egg rarity boost, exact independent 5% Shiny/10% BIG and 0.5% stacked outcomes")
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
