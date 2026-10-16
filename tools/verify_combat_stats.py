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
assert(math.abs(Stats.damage("Ground",1,0)-8)<1e-9)
assert(math.abs(Stats.damage("Ground",4,0)-22.63)<0.1)
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
assert(math.abs(Stats.maxHp("Armored",2)/Stats.maxHp("Ground",2)-1.5)<1e-9)
assert(math.abs(Stats.maxHp("Fly",2)/Stats.maxHp("Ground",2)-0.7)<1e-9)
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
print("Combat stats passed: 4 classes, baseline 1.0, HP 100..606, damage 8..22.6, armor floor 1, finite on junk, ratio kept on growth")
'''
run(BODY, 'stats')
