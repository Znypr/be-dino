"""BD-240 combat state: HP clamps, idempotent Alive -> Defeated -> Settled, overkill, regen, growth (src/shared/CombatState.luau)."""
from combat_harness import run
BODY = r'''
local st=State.new(100)
assert(st.hp==100 and st.phase=="Alive")
local ap,d=State.damage(st,30,1); assert(ap==30 and not d and st.hp==70)
-- negative / NaN / inf damage never heals or breaks
for _,j in {-50,0/0,math.huge,-math.huge,"x",nil} do
  local before=st.hp
  local a=State.damage(st,j,1)
  assert(a>=0 and st.hp<=before and st.hp==st.hp and st.hp>=0,"junk damage safe")
  st.hp=70; st.phase="Alive"
end
-- overkill clamps and defeats exactly once
st=State.new(100)
local a1,d1=State.damage(st,9999,2)
assert(a1==100 and d1 and st.hp==0 and st.phase=="Defeated")
local a2,d2=State.damage(st,50,3)
assert(a2==0 and not d2 and st.hp==0,"second hit ignored")
-- simultaneous defeat: two hitters in one frame, only the first gets the defeat flag
st=State.new(100)
local flags=0
for i=1,5 do local _,x=State.damage(st,60,5); if x then flags+=1 end end
assert(flags==1,"exactly one defeat event")
-- settle once
assert(State.settle(st)==true and st.phase=="Settled")
assert(State.settle(st)==false and State.settle(st)==false,"settle idempotent")
local s2=State.new(100); assert(State.settle(s2)==false and s2.phase=="Alive","cannot settle a live dino")
assert(State.damage(st,10,9)==0 and st.phase=="Settled","settled stays settled")
assert(State.heal(st,50)==0,"no healing after defeat")
-- heal clamps to max
st=State.new(100); State.damage(st,40,0)
assert(State.heal(st,1000)==40 and st.hp==100)
assert(State.heal(st,-5)==0 and State.heal(st,0/0)==0)
-- food heal = 5% of max
st=State.new(200); State.damage(st,100,0); assert(math.abs(State.healFood(st)-10)<1e-9)
-- regen waits 6s without combat, then 4%/s
st=State.new(100); State.damage(st,50,10)
assert(State.regen(st,12,1)==0 and st.hp==50,"no regen inside 6s")
assert(math.abs(State.regen(st,17,1)-4)<1e-9 and math.abs(st.hp-54)<1e-9)
State.touch(st,17.5); assert(State.regen(st,18,1)==0,"touch resets the regen delay")
st=State.new(100); State.damage(st,99.5,0); State.regen(st,100,1000); assert(st.hp==100,"regen clamps")
-- growth keeps ratio and never kills
st=State.new(100); State.damage(st,50,0); State.setMaxHp(st,300)
assert(math.abs(st.hp-150)<1e-9 and st.maxHp==300,"50% stays 50%")
st=State.new(100); State.setMaxHp(st,0/0); assert(st.maxHp>=1 and st.hp==st.hp)
local dead=State.new(100); State.damage(dead,500,0); State.setMaxHp(dead,400); assert(dead.hp==0 and dead.phase=="Defeated","growth cannot revive")
-- fuzz: hp always in 0..maxHp
local seed=7
local function rnd() seed=(seed*1103515245+12345)%2147483648; return seed/2147483648 end
st=State.new(250)
for i=1,5000 do
  local r=rnd()
  if r<0.5 then State.damage(st,rnd()*80,i*0.1) elseif r<0.7 then State.heal(st,rnd()*80)
  elseif r<0.9 then State.regen(st,i*0.1,rnd()) else State.setMaxHp(st,50+rnd()*500) end
  assert(st.hp>=0 and st.hp<=st.maxHp+1e-9 and st.hp==st.hp,"hp stays clamped")
end
print("Combat state passed: clamps, overkill, one defeat event, settle once, regen 6s/4pct, ratio kept on growth, 5000-step fuzz")
'''
run(BODY, 'state')
