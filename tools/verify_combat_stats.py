"""BD-239 combat stats: class table invariants, size scale, HP and damage formulas, armor, junk input (src/shared/CombatStats.luau)."""
from combat_harness import run
BODY = r'''
assert(Cfg.Enabled==false,"combat flag defaults OFF")
local names={"Ground","Fly","Water","Armored"}
local count=0
for k in Cfg.Classes do count+=1 end
assert(count==4,"four classes")
for _,n in names do
  local c=Cfg.Classes[n]; assert(c,n)
  for _,f in {"hpX","speedX","damageTakenX","damageDealtX"} do
    assert(type(c[f])=="number" and c[f]>0 and c[f]<=2,n..f.." sane")
  end
  assert(c.speedX>=0.8 and c.speedX<=1.2,"speed stays in small-difference band")
end
local G=Cfg.Classes.Ground
assert(G.hpX==1 and G.speedX==1 and G.damageTakenX==1 and G.damageDealtX==1,"Ground is the 1.0 baseline")
assert(Cfg.Classes.Armored.damageTakenX<1 and Cfg.Classes.Armored.hpX>1,"armored is the tank")
assert(Cfg.Classes.Fly.hpX<1 and Cfg.Classes.Fly.speedX>1,"fly is fragile and fast")
assert(Cfg.Classes.Water.hpX>1 and Cfg.Classes.Water.speedX<1,"water is sturdy and slow")
-- scale
assert(Stats.scale(0)==1 and Stats.scale(-50)==1,"s floor 1")
assert(Stats.scale(25500)==4 and Stats.scale(1e12)==4,"s cap 4")
local prev=0
for sc=0,30000,250 do local s=Stats.scale(sc); assert(s>=prev and s>=1 and s<=4); prev=s end
-- HP / damage anchors from docs/101
assert(math.abs(Stats.maxHp("Ground",1)-100)<1e-9)
assert(math.abs(Stats.maxHp("Ground",4)-606.3)<1)
assert(math.abs(Stats.damage("Ground",1,0)-6)<1e-9)
assert(math.abs(Stats.damage("Ground",4,0)-7.92)<0.1)
assert(Stats.damage("Ground",2,2)>Stats.damage("Ground",2,0),"attackTier raises damage")
-- monotonic with size, per class
for _,n in names do
  local ph,pd=0,0
  for i=0,60 do
    local s=1+i*0.05
    local h,d=Stats.maxHp(n,s),Stats.damage(n,s,0)
    assert(h>ph and d>pd and h==h and d==d,"monotonic "..n); ph,pd=h,d
  end
end
-- class multipliers apply
assert(math.abs(Stats.maxHp("Armored",2)/Stats.maxHp("Ground",2)-1.1)<1e-9)
assert(math.abs(Stats.maxHp("Fly",2)/Stats.maxHp("Ground",2)-0.75)<1e-9)
-- class roles (docs/101 s17): armored = highest effective HP, slowest, lowest damage; fly fastest + fragile; water sturdy + slow
local function eff(n) return Cfg.Classes[n].hpX/Cfg.Classes[n].damageTakenX end
for _,n in {"Ground","Fly","Water"} do
  assert(eff("Armored")>eff(n) and Cfg.Classes.Armored.speedX<Cfg.Classes[n].speedX and Cfg.Classes.Armored.damageDealtX<Cfg.Classes[n].damageDealtX,"armored tank vs "..n)
end
assert(Cfg.Classes.Fly.speedX>Cfg.Classes.Ground.speedX and Cfg.Classes.Fly.speedX>Cfg.Classes.Water.speedX)
assert(Cfg.Classes.Fly.hpX<Cfg.Classes.Ground.hpX and Cfg.Classes.Water.hpX>Cfg.Classes.Ground.hpX and Cfg.Classes.Water.speedX<1)
-- equal-size 1v1 is near parity: hits needed differ by <= 5%, and no class beats all three others at any size
for _,sz in {1,Stats.scale(1500),4} do
  for _,x in names do
    local winsAll=true
    for _,y in names do if x~=y then
      local a=math.ceil(Stats.maxHp(y,sz)/Stats.hit(x,sz,y,sz,0,1)); local b=math.ceil(Stats.maxHp(x,sz)/Stats.hit(y,sz,x,sz,0,1))
      assert(math.abs(a-b)/math.max(a,b)<=0.05,x.." vs "..y.." near parity")
      if not (a<b) then winsAll=false end
    end end
    assert(not winsAll,x.." must not strictly dominate at s="..sz)
  end
end
-- no one-shot kills: even the biggest hit takes at most 15% of a small target
for _,x in names do for _,y in names do
  assert(Stats.hit(x,4,y,1,0,1)/Stats.maxHp(y,1)<=0.15,"no one-shots")
end end
-- armor and damage never negative / NaN / below 1
for _,t in names do for _,a in names do
  for _,as in {1,1.5,4} do for _,ts in {1,2,4} do
    local h=Stats.hit(a,as,t,ts,0,1)
    assert(h==h and h>=Cfg.MinHit and h<math.huge,"hit finite and >= MinHit")
  end end
end end
assert(Stats.hit("Ground",1,"Armored",1,0,0)==Cfg.MinHit,"zero damage still counts 1")
assert(Stats.hit("Ground",1,"Ground",4,0,1)<Stats.hit("Ground",1,"Ground",1,0,1),"size damper bites small-vs-big")
assert(Stats.hit("Ground",2,"Armored",2,0,1)<Stats.hit("Ground",2,"Ground",2,0,1),"armor reduces")
-- junk input
local junk={0/0,math.huge,-math.huge,-5,"x",nil,{},true}
for _,j in junk do
  for _,v in {Stats.scale(j),Stats.maxHp("Ground",j),Stats.maxHp(j,2),Stats.damage("Ground",j,j),Stats.armor(j,j),Stats.hit(j,j,j,j,j,j),Stats.rescaleHp(j,j,j)} do
    assert(v==v and v>-math.huge and v<math.huge and v>=0,"junk gives finite non-negative")
  end
end
assert(Stats.classOf("Nope")==Cfg.Classes.Ground)
-- growth keeps ratio
assert(math.abs(Stats.rescaleHp(50,100,200)-100)<1e-9,"50% stays 50%")
assert(Stats.rescaleHp(500,100,200)<=200 and Stats.rescaleHp(-5,100,200)==0,"rescale clamps")
-- BD-1025 (owner 2026-10-18: fights take too long): an even fight against a wild predator is short.
-- Wild score 60..250 (NpcPredatorRules.Config); the player has the same size. Ground: 6..10 bites and at most 8 s; every class: at most 8 s.
assert(Cfg.BiteCooldownSeconds<=0.6 and Cfg.BiteCooldownSeconds*Cfg.BiteRequestsPerSecond>=1,"faster bites, still inside the rate limit")
assert(Cfg.SizeUnitMax==1+750/Cfg.SizeUnitDivisor and Cfg.OneShotRatio==Cfg.SizeUnitMax and Cfg.WildMaxSizeRatio>1,"size unit config matches the growth cap")
assert(Cfg.WildHpX>0 and Cfg.WildHpX<=0.5,"wild HP clearly lower")
assert(Stats.maxHp("Ground",2,nil)==Stats.maxHp("Ground",2) and math.abs(Stats.maxHp("Ground",2,0.4)-0.4*Stats.maxHp("Ground",2))<1e-9,"hpX is optional and multiplies")
for _,sc in {60,155,250} do
  local ws=Stats.scale(sc)
  for _,pc in names do
    local bites=math.ceil(Stats.maxHp("Ground",ws,Cfg.WildHpX)/Stats.hit(pc,ws,"Ground",ws,0,1))
    local secs=(bites-1)*Cfg.BiteCooldownSeconds
    assert(secs<=8,pc.." even fight vs wild at score "..sc.." takes "..secs.." s")
    if pc=="Ground" then assert(bites>=6 and bites<=10,"Ground even fight is 6..10 bites, got "..bites) end
  end
end
-- BD-1025 part 2: the size difference R = bigger / smaller (size unit z = 1 + growth / 50, 1..16) sets the bites. PROVISIONAL curve.
assert(Stats.sizeUnits(0)==1 and Stats.sizeUnits(750)==16 and Stats.sizeUnits(1e9)==16 and Stats.sizeUnits(nil)==1,"size unit 1..16")
assert(math.abs(Stats.sizeRatio(800,100)-16/3)<1e-9,"100 vs 800 growth = R 5.33 (the cap is 750)")
local wsc=Stats.scale(155)
local function bigBitesVs(hpX,R) -- ground vs ground at the same combat scale, only R changes
  local base=Stats.hit("Ground",wsc,"Ground",wsc,0,1)
  return Stats.bigBites(Stats.maxHp("Ground",wsc,hpX)/base,R)
end
for _,hpX in {Cfg.WildHpX,1} do
  local prev=math.huge
  for i=0,200 do
    local R=1+(Cfg.OneShotRatio*1.5-1)*i/200
    local b=bigBitesVs(hpX,R)
    assert(b<=prev+1e-9 and b>=1-1e-9,"a bigger R never means a longer fight (hpX "..hpX..", R "..R..")")
    prev=b
  end
  assert(math.abs(bigBitesVs(hpX,Cfg.OneShotRatio)-1)<1e-9 and math.abs(bigBitesVs(hpX,Cfg.OneShotRatio*3)-1)<1e-9,"max R = ONE bite")
  assert(math.ceil(bigBitesVs(hpX,8)-1e-6)>=4 and math.ceil(bigBitesVs(hpX,8)-1e-6)<=6,"R 8 takes 4 to 6 bites")
  assert(math.ceil(bigBitesVs(hpX,5.33)-1e-6)<=6,"100 vs 800 growth takes about 5 bites")
  assert(bigBitesVs(hpX,2)>bigBitesVs(hpX,5) and bigBitesVs(hpX,5)>bigBitesVs(hpX,12),"falls the whole way")
end
local e1=math.ceil(bigBitesVs(Cfg.WildHpX,1)-1e-6)
assert(e1>=6 and e1<=10,"R 1 against a wild predator is 6 to 10 bites, got "..e1)
assert(math.abs(bigBitesVs(1,1)-Stats.maxHp("Ground",wsc)/Stats.hit("Ground",wsc,"Ground",wsc,0,1))<1e-9,"R 1 = the plain even fight, no step")
-- the real damage function: one bite at the max ratio, a smaller dino loses damage smoothly but never reaches 0
local hpT=Stats.maxHp("Ground",Stats.scale(0),Cfg.WildHpX)
assert(Stats.hitScored("Ground",750,"Ground",0,0,1,{targetHpX=Cfg.WildHpX})>=hpT*(1-1e-9),"capped dino one-shots a fresh one")
assert(Stats.hitScored("Ground",750,"Ground",0,0,1,nil)>=Stats.maxHp("Ground",Stats.scale(0))*(1-1e-9),"... also a full-HP player")
assert(Stats.hitScored("Ground",155,"Ground",155,0,1,nil)==Stats.hit("Ground",Stats.scale(155),"Ground",Stats.scale(155),0,1),"equal size = the plain hit")
assert(Stats.hitScored("Ground",750,"Ground",0,0,1,{wildAttacker=true})==Stats.hit("Ground",Stats.scale(750),"Ground",1,0,1),"a wild predator keeps the plain hit")
do
  local prev=math.huge
  for i=0,40 do
    local sc=i*20 -- attacker score 0..800; target is a capped dino (z 16): the smaller the attacker the weaker the bite
    local h=Stats.hitScored("Ground",sc,"Ground",800,0,1,nil)
    assert(h>=Cfg.MinHit and h==h and h<math.huge,"never 0, never negative, finite")
    if i>0 then assert(h>=prev-1e-9,"a bigger attacker never hits weaker (score "..sc..")") end
    prev=h
  end
  local fresh=Stats.hitScored("Ground",0,"Ground",750,0,1,nil)
  assert(math.ceil(Stats.maxHp("Ground",Stats.scale(750))/fresh)>=60,"a fresh dino against a capped one is hopeless (60+ bites)")
end
-- the strongest class order is unchanged (T-Rex stays the biggest hitter through size, class table untouched)
assert(Stats.maxHp("Ground",4)>Stats.maxHp("Ground",1) and Stats.damage("Ground",4,0)>Stats.damage("Ground",1,0),"size still wins")
print("Combat stats passed: 4 classes, baseline 1.0, HP 100..606, damage 6..7.9, armor floor 1, finite on junk, ratio kept on growth")
'''
run(BODY, 'stats')
