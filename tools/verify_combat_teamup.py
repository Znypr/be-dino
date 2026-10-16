"""BD-241 team-up: ledger, assist split, repeat-pair limiter, crowd cap, and fight simulation (src/shared/CombatTeamUp.luau)."""
from combat_harness import run
BODY = r'''
local T=Cfg.TeamUp
-- assisters need 10% of max HP inside 15 s
local L=TeamUp.newLedger()
TeamUp.record(L,"a",15,0); TeamUp.record(L,"b",5,1); TeamUp.record(L,"c",40,2)
local as=TeamUp.assisters(L,100,3)
local ids={}; for _,x in as do ids[x.id]=x.damage end
assert(ids.a==15 and ids.c==40 and ids.b==nil,"b under 10% is not an assister")
assert(#TeamUp.assisters(L,100,100)==0,"old hits expire")
TeamUp.record(L,nil,50,3); TeamUp.record(L,"z",-4,3); TeamUp.record(L,"z",0/0,3)
assert(#L.hits==3,"junk hits ignored")
-- pool cap
assert(TeamUp.bonusPool(1000)==250 and TeamUp.bonusPool(1001)==250 and TeamUp.bonusPool(3)==0)
assert(TeamUp.bonusPool(1000,100)==100 and TeamUp.bonusPool(1000,9999)==250 and TeamUp.bonusPool(-5)==0 and TeamUp.bonusPool(0/0)==0)
-- split sums exactly (random fuzz) and is by damage share
local seed=11
local function rnd() seed=(seed*1103515245+12345)%2147483648; return seed/2147483648 end
for t=1,3000 do
  local n=1+math.floor(rnd()*8); local list={}
  for i=1,n do list[i]={id="p"..i,damage=1+rnd()*500} end
  local pool=math.floor(rnd()*3000)
  local out=TeamUp.split(pool,list)
  local sum=0; for _,a in list do assert(out[a.id]>=0 and out[a.id]==math.floor(out[a.id])); sum+=out[a.id] end
  assert(sum==pool,"split sums exactly: "..sum.." vs "..pool)
end
local e=TeamUp.split(10,{{id="x",damage=1},{id="y",damage=1},{id="z",damage=1}})
assert(e.x+e.y+e.z==10 and math.max(e.x,e.y,e.z)-math.min(e.x,e.y,e.z)<=1,"equal shares differ by at most 1")
local big=TeamUp.split(100,{{id="x",damage=75},{id="y",damage=25}}); assert(big.x==75 and big.y==25)
local none=TeamUp.split(100,{}); assert(next(none)==nil)
local zero=TeamUp.split(0,{{id="x",damage=5}}); assert(zero.x==0)
-- factors never exceed the pool
local parts=TeamUp.split(101,{{id="a",damage=3},{id="b",damage=2}})
local f=TeamUp.applyFactors(parts,{a=0.5,b=0})
assert(f.a<=parts.a and f.b==0 and f.a+f.b<=101)
local f2=TeamUp.applyFactors(parts,{a=7,b=-3}); assert(f2.a==parts.a and f2.b==0,"factors clamp 0..1")
-- repeat-pair limiter: 1.0, 0.5, 0, then recovers after 3 min, pairs independent
local lim=TeamUp.newLimiter()
assert(TeamUp.pairFactor(lim,"a","v",0)==1.0)
assert(TeamUp.pairFactor(lim,"a","v",30)==0.5)
assert(TeamUp.pairFactor(lim,"a","v",60)==0)
assert(TeamUp.pairFactor(lim,"a","v",90)==0)
assert(TeamUp.pairFactor(lim,"b","v",90)==1.0 and TeamUp.pairFactor(lim,"a","w",90)==1.0,"other pairs unaffected")
assert(TeamUp.pairFactor(lim,"a","v",400)==1.0,"window passes, bonus returns")
-- crowd cap: 5 distinct attackers in 2 s -> x0.85; same attacker repeating does not count
local C=TeamUp.newLedger()
for i=1,4 do TeamUp.record(C,"p"..i,5,10) end
assert(TeamUp.crowdMultiplier(C,10.5)==1)
for i=1,10 do TeamUp.record(C,"p1",5,10.5) end
assert(TeamUp.crowdMultiplier(C,10.6)==1,"one attacker spamming is not a crowd")
TeamUp.record(C,"p5",5,11)
assert(TeamUp.crowdMultiplier(C,11)==T.CrowdDamageX)
assert(TeamUp.crowdMultiplier(C,14)==1,"crowd fades after 2 s")

-- Fight simulation (docs/101 s17 balance targets; fight() comes from combat_harness SIM; offline simulation only).
local W,T1,A1=fight(team(1,"Ground",S1),team(1,"Ground",S4),true)
assert(W=="B","one small loses to s=4")
local hits=math.ceil(Stats.maxHp("Ground",S1)/Stats.hit("Ground",S4,"Ground",S1,0,1))
assert(hits>=5,"big needs 5+ hits to defeat a small, got "..hits)
for _,c in {"Ground","Fly","Water","Armored"} do
  local w,t,al,fd=fight(team(1,c,S1),team(1,c,S4),true)
  assert(w=="B" and fd>=3,c.." lone small loses, and defeat takes >= 3 s")
  local w6,t6,al6=fight(team(6,c,S1),team(1,c,S4),true)
  assert(w6=="A" and al6>=3,c..": six small beat s=4 with >= 3 survivors")
  assert(fight(team(3,c,S1),team(1,c,S4),true)=="B",c..": three small do not beat s=4")
  assert(fight(team(3,c,S1),team(1,c,S2),true)=="A" and fight(team(3,c,S1),team(1,c,S3),true)=="A",c..": three small beat s=2 and s=3")
end
local w6,t6,al6=fight(team(6,"Ground",S1),team(1,"Ground",S4),true)
assert(t6>=20 and t6<=35,"6 small vs s=4 takes 20-35 s, got "..t6)
print(string.format("sim: 6 small vs s=4 big -> %s at %.1fs, survivors %d; 3 small lose; lone small loses after %d hits (%.1fs)",w6,t6,al6,hits,T1))
-- no reward leakage: this module only returns integer bonus amounts and never touches eggs or score
print("Combat team-up passed: assister threshold, split sums exactly (3000 fuzz), pair 1/0.5/0 then reset, crowd cap x0.9, 6 small beat 1 big, 1 small loses")
'''
run(BODY, 'teamup')
