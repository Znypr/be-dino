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

-- Fight simulation (docs/101 s3 feel check). Fixed 0.1 s steps, 0.9 s cooldown, big dino hits one small target at a time.
local function sim(nSmall,smallScore,bigScore,smallClass,bigClass,crowd)
  local ss,bs=Stats.scale(smallScore),Stats.scale(bigScore)
  local big=State.new(Stats.maxHp(bigClass,bs))
  local smalls={}
  for i=1,nSmall do smalls[i]={st=State.new(Stats.maxHp(smallClass,ss)),cd=0} end
  local ledger=TeamUp.newLedger(); local bigCd=0
  local t=0
  while t<300 do
    t+=0.1
    for i,sm in smalls do
      sm.cd-=0.1
      if sm.st.phase=="Alive" and sm.cd<=0 then
        sm.cd=0.9
        local x=if crowd then TeamUp.crowdMultiplier(ledger,t) else 1
        local h=Stats.hit(smallClass,ss,bigClass,bs,0,x)
        local ap=State.damage(big,h,t); TeamUp.record(ledger,"s"..i,ap,t)
        if big.phase~="Alive" then local alive=0; for _,q in smalls do if q.st.phase=="Alive" then alive+=1 end end; return "smalls",t,alive end
      end
    end
    bigCd-=0.1
    if bigCd<=0 then
      for _,sm in smalls do
        if sm.st.phase=="Alive" then State.damage(sm.st,Stats.hit(bigClass,bs,smallClass,ss,0,1),t); bigCd=0.9; break end
      end
    end
    local alive=0; for _,q in smalls do if q.st.phase=="Alive" then alive+=1 end end
    if alive==0 then return "big",t,0 end
  end
  return "none",t,0
end
-- the big dino defeats one lone small one in about 5 hits (docs/101)
do
  local bs=Stats.scale(25500); local ss=1
  local hits=math.ceil(Stats.maxHp("Ground",ss)/Stats.hit("Ground",bs,"Ground",ss,0,1))
  assert(hits>=4 and hits<=6,"big kills small in about 5 hits, got "..hits)
end
-- 1 small loses to 1 big (also with crowd off/on)
for _,c in {false,true} do local w=sim(1,0,25500,"Ground","Ground",c); assert(w=="big","one small loses") end
-- 6 small beat one big: use a big at the documented s=4 and a milder s~3 big; report survivors
local w4,t4,al4=sim(6,0,25500,"Ground","Ground",true)
local w3,t3,al3=sim(6,0,8000,"Ground","Ground",true)
print(string.format("sim: 6 small vs s=4 big -> %s at %.1fs, survivors %d; vs s~3 big -> %s at %.1fs, survivors %d",w4,t4,al4,w3,t3,al3))
assert(w4=="smalls" and w3=="smalls","six small beat one big")
assert(al3>=1)
-- team-up pays off: 6 together beat it, while the same 6 one at a time (each alone) all lose
local aloneWins=0
for i=1,6 do if sim(1,0,25500,"Ground","Ground",true)=="smalls" then aloneWins+=1 end end
assert(aloneWins==0,"going alone loses")
-- 3 small do not beat s=4 big (it still takes a crowd)
assert(sim(3,0,25500,"Ground","Ground",true)=="big","three small are not enough")
-- no reward leakage: this module only returns integer bonus amounts and never touches eggs or score
print("Combat team-up passed: assister threshold, split sums exactly (3000 fuzz), pair 1/0.5/0 then reset, crowd cap x0.85, 6 small beat 1 big, 1 small loses")
'''
run(BODY, 'teamup')
