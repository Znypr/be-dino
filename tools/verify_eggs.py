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
 for a=0,499 do for b=0,499 do
  local t=Traits.roll(weather,(a+.5)/500,(b+.5)/500)
  shiny+=if t.shiny then 1 else 0
  big+=if t.big then 1 else 0
  stacked+=if t.shiny and t.big then 1 else 0
 end end
 assert(big==7500) -- 3% BIG of 250,000 grid cells
 assert(shiny==(if Config.IrregularWeather[weather] then 1500 else 0)) -- 0.6% Shiny
 assert(stacked==(if Config.IrregularWeather[weather] then 45 else 0))
end
assert(not Traits.roll("volcano",.006,.03).shiny and not Traits.roll("volcano",.006,.03).big)
assert(Traits.valid({[':shiny:big']={mutationId="",shiny=true,big=true,count=1}}))
assert(not Traits.valid({['bad']={mutationId="",shiny=true,big=true,count=1}}))
assert(Config.BigScaleMultiplier==1.2)
assert(#Progression.Trails==10 and Progression.Trails[1].id=="white" and Progression.Trails[10].id=="astra")
-- BD-045: integer weights out of ConditionWeightScale; tier 0 = owner target 50/30/15/4.5/0.5.
assert(Progression.ConditionWeightScale==10000 and Progression.ConditionOddsVersion=="bd045-conditions-v1")
local tier0=Progression.ConditionWeights[1]
assert(tier0[1]==5000 and tier0[2]==3000 and tier0[3]==1500 and tier0[4]==450 and tier0[5]==50)
assert(Progression.Conditions[1].id=="cracked" and Progression.Conditions[1].hatchChance==.2)
local previous=nil
for level,weights in Progression.ConditionWeights do
 local total=0 for _,weight in weights do assert(weight>0 and weight%1==0) total+=weight end
 assert(total==Progression.ConditionWeightScale,"condition tier does not total 100%")
 if previous then
  -- Upgrades improve odds monotonically: Cracked/Dirty fall, Normal/Rainbow/Astra rise.
  assert(weights[1]<previous[1] and weights[2]<previous[2],"bad eggs must decrease every tier")
  assert(weights[3]>previous[3] and weights[4]>previous[4] and weights[5]>previous[5],"good eggs must increase every tier")
 end
 previous=weights
 local seen={} local failed=0
 for i=0,9999 do
  for j=0,4 do
   local n=0
   local rng={NextNumber=function()n+=1 return if n==1 then (i+.5)/10000 elseif n==2 then (j+.5)/5 else .5 end}
   local genes=Genetics.roll(level-1,rng)
   assert(Genetics.valid(genes))
   seen[genes.conditionId]=(seen[genes.conditionId] or 0)+1
   if not genes.hatchSuccess then failed+=1 assert(genes.conditionId=="cracked") end
  end
 end
 for k,condition in Progression.Conditions do assert(seen[condition.id]==weights[k]*5) end
 assert(failed==weights[1]*4,"Cracked must keep exactly 20% hatch success")
end
-- Tier 0 failure: 50% Cracked x 80% failure = 40% of eggs.
assert(tier0[1]*4==20000)
-- BD-184: weights are out of EggColorWeightScale (10,000,000), so probe the middle and both edges of each colour's interval.
local function colorAt(roll)
 local n=0 local rng={NextNumber=function()n+=1 return if n==3 then roll else .5 end}
 return Genetics.roll(0,rng).primaryColorId
end
local cum,scale=0,Progression.EggColorWeightScale
for _,color in Progression.EggColors do
 assert(colorAt((cum+color.weight/2)/scale)==color.id,color.id)
 assert(colorAt((cum+.001)/scale)==color.id,color.id.." lower edge")
 cum+=color.weight
 assert(colorAt((cum-.001)/scale)==color.id,color.id.." upper edge")
end
assert(cum==scale)
assert(Progression.EggColors[9].id=="black" and Progression.EggColors[9].weight==512)
assert(not Genetics.valid({conditionId="astra",hatchSuccess=false,primaryColorId="white",secondaryColorId="black",blend=80}))
for i,trail in Progression.Trails do
 if i>1 then local prior=Progression.Trails[i-1] assert(trail.level>prior.level and trail.price>prior.price and trail.speed>prior.speed) end
end
print("Genetics passed: seven exact BD-045 condition distributions (tier 0 50/30/15/4.5/0.5, monotonic upgrades), 20% Cracked hatch success, weighted color slots, exact tiered colour intervals (Black 0.00512%), size-only BIG 1.2x and ten increasing trail tiers")
local previousRare,previousLegend=0,0
for count=1,40,3 do
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
print("Egg rules passed: all 22 species, monotonic 1-40 egg rarity boost, exact independent 0.6% Shiny/3% BIG (BD-184) and stacked outcomes")
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
