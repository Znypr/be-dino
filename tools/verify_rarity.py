"""BD-184 / docs/88 exponential rarity: proves every rarity table in the real configs follows the shared RarityCurve ladder.
Runs the real RarityCurve, Config and ProgressionConfig in Luau. Mocks validate numbers, not feel or Studio.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
BODY=r'''
local EPS=1e-9
local function near(a,b,rel) assert(math.abs(a-b)<=rel*math.abs(b),string.format("%s vs %s",tostring(a),tostring(b))) end
local function sum(t) local s=0 for _,v in t do s+=v end return s end
-- Every probability table: strictly decreasing, adjacent ratio inside [1/6,1/3], total 100%.
local function ladder(name,chances)
 near(sum(chances),1,1e-9)
 for i=2,#chances do
  assert(chances[i]<chances[i-1],name.." must strictly decrease")
  local ratio=chances[i]/chances[i-1]
  assert(ratio>=Curve.MinAdjacentRatio-1e-3 and ratio<=Curve.MaxAdjacentRatio+1e-3,string.format("%s ratio %g at tier %d",name,ratio,i))
 end
end

-- 1. The ladder itself.
local w6=Curve.weights(6)
local expect={80,16,3.2,.64,.128,.0256}
for i,p in expect do near(w6[i]*100*.999936,p,1e-6) end
ladder("RarityCurve(6)",w6)
local w5=Curve.weights(5) ladder("RarityCurve(5)",w5)
near(w5[1]*100,80.0205,1e-4) near(w5[5]*100,.128,1e-3)
assert(#Curve.Names==6 and Curve.Names[1]=="Common" and Curve.Names[6]=="Mythic" and Curve.index("Epic")==3 and Curve.index("x")==nil)
-- 2. Prices: x2.8 per tier, rounded to two figures.
local auraBase={60,170,470,1300,3700,10000} local trailBase={100,280,780,2200,6100,17000}
for k=0,5 do assert(Curve.price(k,60)==auraBase[k+1],"aura price "..k) assert(Curve.price(k,100)==trailBase[k+1],"trail price "..k) end
for k=1,5 do local r=Curve.price(k,60)/Curve.price(k-1,60) assert(r>2.7 and r<2.95,"price factor "..r) end
-- 3. Boost helper never flattens adjacent tiers past 1/3, never reorders, leaves ratio-above-cap tiers alone.
local boosted=Curve.boost({1,.2,.04},{1,10,10}) assert(boosted[2]<=1/3+EPS and boosted[3]<=boosted[2]*(1/3)+EPS and boosted[2]>.2)
assert(Curve.boost({1,.2},{1,1})[2]==.2)
-- The shipped species boost (kept by BD-184) stays inside the cap at the full-run factor.
local tiers={0,0,0,0,0} for _,row in Config.ChestSpeciesWeights do local t=Config.SpeciesRarities[row.speciesId] tiers[t]+=row.weight end
near(sum(tiers),100,1e-9) assert(math.abs(tiers[1]-91)<1e-9 and math.abs(tiers[2]-8.5)<1e-9 and math.abs(tiers[3]-.42)<1e-9 and math.abs(tiers[4]-.07)<1e-9 and math.abs(tiers[5]-.01)<1e-9,"species tier totals must stay 91/8.5/0.42/0.07/0.01 (BD-1032, docs/186 s3; the docs/88 ladder is deliberately steeper at the top, docs/116 C-54)")
local bs=Curve.boost(tiers,Config.SpeciesRunBoost)
for i=2,5 do assert(bs[i]/bs[i-1]<=1/3+EPS,"species boost tier "..i) assert(bs[i]<bs[i-1]) end
for i,f in Config.SpeciesRunBoost do near(bs[i],tiers[i]*f,1e-9) end -- the shipped boost is already within the cap

-- 4. Egg colours: tier totals follow the ladder, split inside tiers by weight.
local colorTier={} local scale=Progression.EggColorWeightScale local tot=0
for _,c in Progression.EggColors do
 local t=assert(Curve.index(c.rarity),"colour rarity "..c.id) colorTier[t+1]=(colorTier[t+1] or 0)+c.weight tot+=c.weight
end
assert(tot==scale,"colour weights must total the scale")
local want={} local ct={} for i=1,6 do ct[i]=colorTier[i]/scale*100 end
for i=1,6 do near(ct[i],expect[i]/.999936,5e-3) end
local colorChances={} for i=1,6 do colorChances[i]=colorTier[i]/scale end
ladder("EggColors tiers",colorChances)
-- BD-1036: EQUAL split inside a tier, strictly less weight per colour in a rarer tier, tier membership as in docs/88, the shared helper agrees.
do
 local members={Common={"white","blue"},Uncommon={"green"},Rare={"pink","teal"},Epic={"gold"},Legendary={"violet"},Mythic={"red","black"}}
 local weightOf={} local rarityOf={} for _,c in Progression.EggColors do weightOf[c.id]=c.weight rarityOf[c.id]=c.rarity end
 assert(#Progression.EggColors==9,"9 colours (new colours are BD-1037)")
 for tierName,ids in members do
  for _,id in ids do assert(rarityOf[id]==tierName,id.." must be "..tierName) assert(weightOf[id]==weightOf[ids[1]],"equal split inside "..tierName) end
 end
 local order={"Common","Uncommon","Rare","Epic","Legendary","Mythic"}
 for k=2,6 do assert(weightOf[members[order[k]][1]]<weightOf[members[order[k-1]][1]],"weight per colour must fall with the tier "..order[k]) end
 local totals=Curve.tierTotals(Progression.EggColors)
 for k=1,6 do near(totals[k],colorTier[k]/scale,1e-12) end
end
assert(Progression.EggColors[1].rarity=="Common")
local tierOfLast=-1 for _,c in {"white","blue","green","pink","teal","gold","violet","red","black"} do
 local row for _,r in Progression.EggColors do if r.id==c then row=r end end
 local t=Curve.index(row.rarity) :: number assert(t>=tierOfLast) tierOfLast=t
end
-- 4b. BD-1033 patterns (docs/186 s4): one table, a tier per pattern, five ladder tiers renormalised, equal split inside a tier,
-- short kid names (docs/72: no ids, no digits), integer weights that total the scale, strictly less weight per rarer tier.
do
 local rows=Progression.EggPatterns assert(#rows==8,"8 existing patterns")
 local pscale=Progression.PatternWeightScale local ptotal=0 local seenId,seenName={}, {}
 local perTier={} local tierOfPattern={}
 for _,p in rows do
  assert(not seenId[p.id] and not seenName[p.name],"unique pattern id and name") seenId[p.id],seenName[p.name]=true,true
  assert(string.match(p.id,"^%d%d_[%l_]+$"),"pattern id shape "..p.id)
  assert(type(p.name)=="string" and #p.name>=3 and #p.name<=12 and not string.find(p.name,"[%d_]"),"kid name "..tostring(p.name))
  assert(p.weight>0 and p.weight%1==0,"integer weight") ptotal+=p.weight
  local t=assert(Curve.index(p.rarity),"pattern rarity "..p.id) tierOfPattern[p.id]=t
  perTier[t+1]=perTier[t+1] or {} table.insert(perTier[t+1],p.weight)
 end
 assert(ptotal==pscale,"pattern weights must total the scale") assert(tierOfPattern["01_blank"]==0,"the blank pattern stays Common")
 -- Equal split inside a tier; only the FIRST tiers are used (no gaps); a rarer tier always has strictly less weight per pattern.
 local used=0 for k=1,6 do if perTier[k] then assert(used==k-1,"tiers must start at Common with no gap") used=k end end
 for k=1,used do for _,w in perTier[k] do assert(w==perTier[k][1],"equal split inside tier "..k) end end
 for k=2,used do assert(perTier[k][1]<perTier[k-1][1],"weights must strictly decrease by tier") end
 for _,a in rows do for _,b in rows do if tierOfPattern[a.id]<tierOfPattern[b.id] then assert(a.weight>b.weight,a.id.." must be likelier than "..b.id) end end end
 -- Tier chances = the ladder for the tiers in use, renormalised (RarityCurve.weights(used)); adjacent ratio inside the allowed band.
 local want=Curve.weights(used) local got=Curve.tierTotals(rows)
 for k=1,used do near(got[k],want[k],1e-3) end
 for k=used+1,6 do assert(got[k]==0) end
 local chances={} for k=1,used do chances[k]=got[k] end ladder("EggPatterns tiers",chances)
 assert(Progression.PatternOddsVersion=="bd1033-patterns-v1")
 print(string.format("Patterns passed: %d patterns, %d tiers: %s",#rows,used,table.concat((function() local o={} for k=1,used do o[k]=string.format("%s %.3f%%",Curve.Names[k],got[k]*100) end return o end)(),", ")))
end
-- 5. BIG (Rare tier) and Shiny (Epic tier), incl. nest luck.
near(Config.BigChance,.03,.2) assert(Config.BigChance<w6[2] and Config.BigChance>w6[4]) -- Rare-tier scale
near(Config.ShinyChance,.006,.2) assert(Config.ShinyChance<Config.BigChance and Config.ShinyChance/Config.BigChance>=.1 and Config.ShinyChance/Config.BigChance<=.3)
for _,luck in Config.NestLuckTiers do
 assert(luck.bigChance>=Config.BigChance and luck.bigChance<=Config.BigChance*2.5)
 assert(luck.shinyChance>=Config.ShinyChance and luck.shinyChance<=.02 and luck.shinyChance<luck.bigChance)
 assert(luck.shinyChance/luck.bigChance>=.1 and luck.shinyChance/luck.bigChance<=.34)
end
-- 6. Potion shop weights: five tiers, 80/16/3.2/0.64/0.13.
local pw={} for i=1,5 do pw[i]=Progression.PotionShop.RarityWeights[Progression.PotionShop.Rarities[i]] end
local ps=sum(pw) local pc={} for i=1,5 do pc[i]=pw[i]/ps near(pc[i],w5[i],.03) end
ladder("PotionShop",pc)
-- 6b. Potion prices: cheapest potion of tier k is Curve.price(k,20); others in the tier stay within 1.5x of it.
local cheapest={}
for _,p in Progression.Potions do local t=assert(Curve.index(p.rarity)) if not cheapest[t] or p.price<cheapest[t] then cheapest[t]=p.price end end
for t,price in cheapest do assert(price==Curve.price(t,20),"potion tier "..t.." price "..price) end
for _,p in Progression.Potions do assert(p.price<=cheapest[Curve.index(p.rarity) :: number]*1.6) end
-- 7. Auras and trails: price by tier follows x2.8; ids kept.
local seenTier=-1
for _,aura in Progression.Auras do
 local t=assert(Curve.index(aura.rarity)) assert(aura.price==Curve.price(t,60),aura.id.." aura price")
end
for i=2,#Progression.Auras do assert(Progression.Auras[i].price>Progression.Auras[i-1].price) end
local firstOfTier={} local lastTier=-1
for i,trail in Progression.Trails do
 local t=assert(Curve.index(trail.rarity),trail.id) assert(t>=lastTier,"trail tiers must not decrease") lastTier=t
 if trail.price>0 then
  if firstOfTier[t]==nil then firstOfTier[t]=trail.price assert(trail.price==Curve.price(t,100),trail.id.." trail price")
  else assert(trail.price>firstOfTier[t] and trail.price<=firstOfTier[t]*1.5,trail.id.." second trail in tier") end
 end
 if i>2 then assert(trail.price>Progression.Trails[i-1].price) end
end
for t=1,5 do if firstOfTier[t] and firstOfTier[t-1] then local r=firstOfTier[t]/firstOfTier[t-1] assert(r>2.6 and r<2.95,"trail tier factor") end end
-- 8. Weather frequency is a DOCUMENTED EXCEPTION to the ladder (lead decision 2026-10-15, docs/88: weather is a show, not loot).
-- Labels follow the tiers and every event in a higher tier is strictly rarer than every event in a lower tier; weights total 100.
local wt=0 local tierOf={}
for _,e in Progression.Weather do tierOf[e.id]=assert(Curve.index(e.rarity),e.id) wt+=e.weight end
assert(wt==100,"weather weights must total 100")
for _,a in Progression.Weather do for _,b in Progression.Weather do if tierOf[a.id]<tierOf[b.id] then assert(a.weight>b.weight,a.id.." must be more frequent than "..b.id) end end end
local byId={} for _,e in Progression.Weather do byId[e.id]=e end
assert(byId.rain.rarity=="Common" and byId.thunder.rarity=="Common" and byId.quake.rarity=="Uncommon" and byId.blizzard.rarity=="Uncommon" and byId.volcano.rarity=="Rare" and byId.bloodmoon.rarity=="Epic" and byId.aurora.rarity=="Legendary")
for _,e in Progression.Weather do if e.id~="aurora" then assert(byId.aurora.weight<e.weight) end end
local cycle=Progression.WeatherInterval+Progression.WeatherDuration
local perHour=3600/cycle
assert(perHour*.5>=3.5,"a 30 minute session must see 3-4 events on average")
assert(byId.aurora.weight/wt*perHour>=1/3,"Aurora must appear at least every 3 hours of play")
local auroraP=byId.aurora.weight/wt
print(string.format("Rarity passed: ladder %.4f/%.4f/%.4f/%.4f/%.4f/%.4f%%; colours, BIG/Shiny, potion odds and prices, auras, trails follow it; weather is a documented exception",w6[1]*100,w6[2]*100,w6[3]*100,w6[4]*100,w6[5]*100,w6[6]*100))
print(string.format("Weather cadence: cycle %ds = %.2f events/hour; 30 min = %.1f events, 60 min = %.1f; Aurora every %.0f hours (%.4f%% per event), Blood Moon every %.0f h, Volcano every %.1f h",cycle,perHour,perHour/2,perHour,1/(perHour*auroraP),auroraP*100,1/(perHour*byId.bloodmoon.weight/wt),1/(perHour*byId.volcano.weight/wt)))
'''
def script():
 s='local Curve='+module('src/shared/RarityCurve.luau')+'\nlocal Config='+module('src/shared/Config.luau')+'\nlocal Progression='+module('src/shared/ProgressionConfig.luau')+'\n'
 return s+BODY
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/'rarity.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
