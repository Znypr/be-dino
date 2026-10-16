"""BD-243/244 combat service rules (src/shared/CombatRules.luau, the pure core of src/server/CombatService.luau).

Runs the rules with the pinned Luau runtime: flag-off identity, range/cone/cooldown/alive/protected/peaceful checks,
rate limit, exactly-once defeat and settlement per (userId, runId), no negative HP, assist bonus cap and pair limiter,
regen, food heal, HP byte replication budget, friend shield, knockback bound, fuzz. Static checks prove the flag-off
wiring: Config.CombatEnabled=false, CombatService/PredationService/CombatHud guard on it, no new Bootstrap locals.
Not a Studio test: replication, raycasts, the remote and the real settlement write are NOT covered here.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['CombatConfig', 'CombatStats', 'CombatState', 'CombatTeamUp', 'LowPolyDinoAssets', 'CombatRules']

BODY = r'''
local Cfg,Stats,State,R=M.CombatConfig,M.CombatStats,M.CombatState,M.CombatRules
local function P(x,y,z) return {X=x,Y=y or 0,Z=z or 0} end
local FWD=P(0,0,-1) -- facing -Z
local BIG=25500 -- s=4
-- 1. flag off = identity: nothing joins, every call is a no-op
local off=R.new(false)
assert(R.join(off,{userId=1,runId="r",class="Ground",score=0,now=0})==nil,"flag off: nobody joins")
assert(next(off.dinos)==nil)
local r=R.attack(off,"1|r",0,P(0,0,0),FWD,{}); assert(r.ok==false and r.reason=="disabled")
R.tick(off,1,0.1); assert(R.pendingHpByte(off,"1|r",1)==nil and R.settle(off,"1|r")==false)
assert(next(off.dinos)==nil and next(off.requests)==nil,"flag off leaves no state")
-- 2. classes from the species registry
assert(R.classForSpecies("pteranodon")=="Fly" and R.classForSpecies("mosasaurus")=="Water" and R.classForSpecies("ankylosaurus")=="Armored")
assert(R.classForSpecies("compy")=="Ground" and R.classForSpecies("nope")=="Ground" and R.classForSpecies(nil)=="Ground")
-- 3. join, validation reasons
local function world()
  local w=R.new(true); w.defeatCount=0; w.log={}
  w.onDefeat=function(v,a,b) w.defeatCount+=1; table.insert(w.log,{v=v.key,a=a.key,b=b}) end
  return w
end
local w=world()
local A=R.join(w,{userId=1,runId="ra",class="Ground",score=0,now=0})
local B=R.join(w,{userId=2,runId="rb",class="Ground",score=BIG,now=0})
assert(A.key=="1|ra" and B.s==4 and B.state.maxHp==Stats.maxHp("Ground",4))
assert(R.join(w,{userId=1,runId="ra",class="Fly",score=9,now=5})==A,"repeat join returns the same dino")
local cand={{key=B.key,pos=P(0,0,-4)}}
assert(R.attack(w,"9|x",1,P(0,0,0),FWD,cand).reason=="unknown")
assert(R.attack(w,A.key,1,P(0,0,0),FWD,{{key=B.key,pos=P(0,0,-40)}}).reason=="no_target","out of range")
assert(R.attack(w,A.key,1.6,P(0,0,0),FWD,{{key=B.key,pos=P(0,0,4)}}).reason=="no_target","behind the attacker")
assert(R.attack(w,A.key,2.2,P(0,0,0),FWD,{{key=B.key,pos=P(0,20,-4)}}).reason=="no_target","too high")
assert(R.attack(w,A.key,2.8,P(0,0,0),P(0,0,0),cand).reason=="facing","no look vector")
assert(R.attack(w,A.key,3.4,P(0,0,0),FWD,{{key=A.key,pos=P(0,0,-1)}}).reason=="no_target","never self")
local hit=R.attack(w,A.key,4,P(0,0,0),FWD,cand)
assert(hit.ok and hit.targetKey==B.key and not hit.defeated)
assert(math.abs(hit.damage-Stats.hit("Ground",1,"Ground",4,0,1))<1e-9,"module damage formula, never client damage")
assert(math.abs(B.state.hp-(B.state.maxHp-hit.damage))<1e-9)
assert(math.sqrt(hit.knockX^2+hit.knockZ^2)<=Cfg.KnockbackStuds+1e-9 and hit.knockZ<0,"knockback bounded, away from attacker")
assert(R.attack(w,A.key,4.5,P(0,0,0),FWD,cand).reason=="cooldown","0.9 s cooldown")
-- rate limit: a third request inside one second is refused even after the cooldown
local w2=world(); local a2=R.join(w2,{userId=1,runId="x",class="Ground",score=0,now=0}); local b2=R.join(w2,{userId=2,runId="y",class="Ground",score=BIG,now=0})
local c2={{key=b2.key,pos=P(0,0,-4)}}
assert(R.attack(w2,a2.key,10,P(0,0,0),FWD,c2).ok)
assert(R.attack(w2,a2.key,10.95,P(0,0,0),FWD,c2).ok,"second in the second after the cooldown")
assert(R.attack(w2,a2.key,10.96,P(0,0,0),FWD,c2).reason=="rate","third request inside 1 s")
assert(R.attack(w2,a2.key,11.96,P(0,0,0),FWD,c2).ok,"window passed")
-- spawn protection: protected targets cannot be hit; attacking ends the attacker's own protection
local w3=world(); local a3=R.join(w3,{userId=1,runId="x",class="Ground",score=0,now=0,protectedUntil=5}); local b3=R.join(w3,{userId=2,runId="y",class="Ground",score=0,now=0,protectedUntil=5})
local c3={{key=b3.key,pos=P(0,0,-3)}}
assert(R.attack(w3,a3.key,1,P(0,0,0),FWD,c3).reason=="no_target","protected target")
assert(a3.protectedUntil<=1,"attacking ends the attacker's protection early")
assert(R.attack(w3,a3.key,6,P(0,0,0),FWD,c3).ok,"protection over")
-- peaceful: cannot bite, cannot be bitten
local w4=world(); local p=R.join(w4,{userId=1,runId="x",class="Ground",score=0,now=0,peaceful=true}); local q=R.join(w4,{userId=2,runId="y",class="Ground",score=0,now=0})
assert(R.attack(w4,p.key,1,P(0,0,0),FWD,{{key=q.key,pos=P(0,0,-3)}}).reason=="peaceful")
assert(R.attack(w4,q.key,1,P(0,0,0),FWD,{{key=p.key,pos=P(0,0,-3)}}).reason=="no_target","peaceful target untouchable")
-- 4. exactly-once defeat and settlement; hp never negative; later bites ignored
local w5=world(); local big=R.join(w5,{userId=99,runId="big",class="Ground",score=BIG,now=0})
local smalls={}
for i=1,6 do smalls[i]=R.join(w5,{userId=i,runId="s"..i,class="Ground",score=0,now=0}) end
local t,bites=0,0
while big.state.phase=="Alive" and t<200 do
  t+=0.5 -- one request per 0.5 s per small: every second one is inside the cooldown (rejected, still counted by the rate limit)
  for i,s in smalls do
    local res=R.attack(w5,s.key,t+i*0.01,P(0,0,0),FWD,{{key=big.key,pos=P(0,0,-3)}})
    if res.ok then bites+=1 end
    assert(big.state.hp>=0,"never negative")
  end
end
assert(big.state.phase=="Defeated" and w5.defeatCount==1,"exactly one defeat event, got "..w5.defeatCount)
assert(big.state.hp==0 and R.hpByte(big)==0)
assert(R.settle(w5,big.key)==true and R.settle(w5,big.key)==false and R.settle(w5,big.key)==false,"settled exactly once")
for i,s in smalls do assert(R.attack(w5,s.key,t+10+i,P(0,0,0),FWD,{{key=big.key,pos=P(0,0,-3)}}).reason=="no_target","defeated dino cannot be hit again") end
assert(w5.defeatCount==1 and big.state.hp==0)
assert(t>=15 and t<=40,"six smalls beat s=4 in 20-35 s of sim (team-up target), got "..t)
-- assist bonuses: whole numbers, capped by the pool, only to real assisters, never eggs
local total=0
for key,amount in w5.log[1].b do assert(amount==math.floor(amount) and amount>0); total+=amount; assert(w5.dinos[key],"bonus only to tracked dinos") end
assert(total<=math.floor(BIG*Cfg.TeamUp.BonusCapFraction),"bonus total under the cap")
assert(total>0,"assisters get something")
for k in w5.log[1].b do assert(k~=big.key,"victim never gets a bonus") end
-- a defeated attacker cannot bite
assert(R.attack(w5,big.key,t+50,P(0,0,0),FWD,{{key=smalls[1].key,pos=P(0,0,-3)}}).reason=="dead")
-- pair limiter: the same attacker beating the same victim (new run) soon after gets half, then nothing
local w6=world()
local function duel(runNo,now)
  local v=R.join(w6,{userId=2,runId="v"..runNo,class="Ground",score=1000,now=now})
  local a=R.join(w6,{userId=1,runId="a"..runNo,class="Ground",score=BIG,now=now})
  local tt=now
  while v.state.phase=="Alive" do tt+=1; R.attack(w6,a.key,tt,P(0,0,0),FWD,{{key=v.key,pos=P(0,0,-3)}}) end
  local b=w6.log[#w6.log].b
  R.leave(w6,v.key); R.leave(w6,a.key)
  return b[a.key] or 0,tt
end
local b1,t1=duel(1,0); local b2b,t2=duel(2,t1+1); local b3b,t3=duel(3,t2+1)
assert(b1>0 and b2b==math.floor(b1*0.5) and b3b==0,"pair factors 1, 0.5, 0: "..b1..","..b2b..","..b3b)
assert(w6.defeatCount==3)
-- peaceful assister gets 0 even after dealing damage (defensive: peaceful cannot attack at all)
-- 5. growth keeps the ratio and food heals 5%; 6. regen after 6 s
local w7=world(); local g=R.join(w7,{userId=1,runId="g",class="Ground",score=0,now=0}); local h=R.join(w7,{userId=2,runId="h",class="Ground",score=BIG,now=0})
for k=1,5 do assert(R.attack(w7,h.key,k,P(0,0,0),FWD,{{key=g.key,pos=P(0,0,-3)}}).ok) end
local frac=g.state.hp/g.state.maxHp; assert(frac<0.7 and frac>0)
R.setScore(w7,g.key,BIG); assert(math.abs(g.state.hp/g.state.maxHp-frac)<1e-9 and g.state.maxHp==Stats.maxHp("Ground",4),"ratio kept on growth")
local healed=R.foodHeal(w7,g.key); assert(math.abs(healed-g.state.maxHp*Cfg.FoodHealFraction)<1e-9,"food heals 5%")
R.tick(w7,7,1); assert(math.abs(g.state.hp/g.state.maxHp-(frac+Cfg.FoodHealFraction))<1e-9,"no regen inside 6 s of combat")
R.tick(w7,12,1); assert(math.abs(g.state.hp/g.state.maxHp-(frac+Cfg.FoodHealFraction+Cfg.RegenFractionPerSecond))<1e-9,"regen 4%/s after 6 s")
R.tick(w7,13,1000); assert(g.state.hp==g.state.maxHp,"regen clamps at max")
assert(R.setScore(w7,"none",5)==nil and R.foodHeal(w7,"none")==0)
-- 7. HP byte: first send, then only on change at <= HpSendHz, defeat (0) never delayed
local w8=world(); local u=R.join(w8,{userId=1,runId="u",class="Ground",score=0,now=0}); local v=R.join(w8,{userId=2,runId="v",class="Ground",score=BIG,now=0})
assert(R.pendingHpByte(w8,u.key,0)==Cfg.HpByteMax and R.pendingHpByte(w8,u.key,0.5)==nil,"full once, then quiet")
R.attack(w8,v.key,1,P(0,0,0),FWD,{{key=u.key,pos=P(0,0,-3)}})
local byte=R.pendingHpByte(w8,u.key,1.0); assert(byte and byte<Cfg.HpByteMax and byte>0,"changed hp is sent")
assert(R.pendingHpByte(w8,u.key,1.05)==nil,"unchanged: nothing to send")
R.tick(w8,9,0.5) -- regen changes hp again
assert(R.pendingHpByte(w8,u.key,1.1)==nil,"inside the 5 Hz budget: wait")
local byte2=R.pendingHpByte(w8,u.key,1.3); assert(byte2 and byte2>byte,"sent after the budget passed")
local tt=2
while u.state.phase=="Alive" do tt+=1; R.attack(w8,v.key,tt,P(0,0,0),FWD,{{key=u.key,pos=P(0,0,-3)}}) end
assert(R.pendingHpByte(w8,u.key,tt)==0,"defeat byte sent at once")
assert(w8.defeatCount==1)
-- 8. friend shield: three defeats inside 3 min -> next run joins with extra protection; a fresh player gets none
local w9=world()
for i=1,3 do R.recordDefeat(w9,7,i*10) end
assert(R.shieldSeconds(w9,7,31)==Cfg.FriendShieldSeconds and R.shieldSeconds(w9,8,31)==0)
assert(R.shieldSeconds(w9,7,1000)==0,"window passed")
local sh=R.join(w9,{userId=7,runId="n",class="Ground",score=0,now=31,protectedUntil=36})
assert(sh.protectedUntil==36+Cfg.FriendShieldSeconds,"shield added to spawn protection")
-- 9. fuzz: random bites among 8 dinos; hp in bounds, each key defeated at most once, onDefeat count == settled count
local seed=3
local function rnd() seed=(seed*1103515245+12345)%2147483648; return seed/2147483648 end
local wf=world(); local keys={}; local settled=0
wf.onDefeat=function(v) wf.defeatCount+=1; assert(R.settle(wf,v.key)); settled+=1 end
for i=1,8 do keys[i]=R.join(wf,{userId=i,runId="f",class=({"Ground","Fly","Water","Armored"})[i%4+1],score=rnd()*BIG,now=0}).key end
local defeatedKeys={}
for step=1,4000 do
  local now=step*0.05
  local ak=keys[1+math.floor(rnd()*8)]; local tk=keys[1+math.floor(rnd()*8)]
  local res=R.attack(wf,ak,now,P(0,0,0),P((rnd()-0.5)*0.6,0,-1),{{key=tk,pos=P((rnd()-0.5)*4,0,-rnd()*6)}},rnd()<0.1)
  if res.ok and res.defeated then assert(not defeatedKeys[res.targetKey],"a key is defeated at most once"); defeatedKeys[res.targetKey]=true end
  if step%7==0 then R.tick(wf,now,0.35) end
  if step%11==0 then R.setScore(wf,ak,rnd()*BIG) end
  for _,d in wf.dinos do assert(d.state.hp>=0 and d.state.hp<=d.state.maxHp+1e-9 and d.state.hp==d.state.hp,"hp bounds") end
end
assert(wf.defeatCount==settled,"every defeat settled exactly once")
assert(settled>=1,"fuzz produced defeats")
print(string.format("Combat service rules passed: flag-off identity, validation reasons, rate limit, exactly-once defeat/settle, 6 small beat s=4 in %.1f s, pair 1/0.5/0, ratio growth, food heal, regen, hp byte budget, friend shield, fuzz %d defeats", t, settled))
'''


def static_checks():
    errors = []
    read = lambda p: (ROOT / p).read_text(encoding='utf-8')
    if not re.search(r'^\s*CombatEnabled = false,', read('src/shared/Config.luau'), re.M):
        errors.append('Config.CombatEnabled must stay false (BD-252 gate)')
    if 'Enabled = false,' not in read('src/shared/CombatConfig.luau'):
        errors.append('CombatConfig.Enabled must stay false')
    service = read('src/server/CombatService.luau')
    if 'if not Config.CombatEnabled then return end' not in service:
        errors.append('CombatService.start must return before creating anything while the flag is off')
    if 'runLifecycle.tryEnd(player, character, "Defeated"' not in service:
        errors.append('defeat must go through RunLifecycle.tryEnd (single settlement path)')
    if 'commitRunSettlement' in service or 'CatchScore' in service or 'RunEggEvents' in service:
        errors.append('CombatService must never touch eggs/catches/settlement data directly')
    if 'select("#", ...) ~= 0' not in service:
        errors.append('the Bite remote must reject any payload (no client target or damage)')
    if 'if Config.CombatEnabled then return end' not in read('src/server/PredationService.luau'):
        errors.append('PredationService instant-eat must stop only while the flag is on')
    if 'CombatService).start(RunLifecycle, Dinosaur)' not in read('src/server/Bootstrap.server.luau'):
        errors.append('server bootstrap must start CombatService')
    boot = read('src/client/Bootstrap.client.luau')
    if re.search(r'^local (Combat|combat|bite|Bite)', boot, re.M):
        errors.append('Bootstrap.client is at the 200-local limit: no new top-level combat locals')
    if 'CombatHud).attach(' not in boot:
        errors.append('Bootstrap.client must attach CombatHud (module, no locals)')
    hud = read('src/client/CombatHud.luau')
    if 'if not Config.CombatEnabled then return end' not in hud:
        errors.append('CombatHud.attach must be a no-op while the flag is off')
    if re.search(r'Text\s*=.*(damage|%d|HpByte)', hud) or re.search(r'string\.format\([^\n]*HpByte', hud):
        errors.append('no damage numbers or HP numbers in the HUD (docs/101 s10)')
    for needle in ('"Oops! Good try!"', 'PLACEHOLDER', 'MAX_BARS = 12', 'Theme.MotionEnabled'):
        if needle not in hud:
            errors.append('CombatHud is missing ' + needle)
    if 'peaceful' not in read('src/shared/SettingsModel.luau') or '"Peaceful"' not in read('src/client/SettingsMenu.luau'):
        errors.append('Peaceful setting must exist in SettingsModel and the Controls tab')
    return errors


def module(name):
    return '(function()\n' + (ROOT / 'src/shared' / f'{name}.luau').read_text(encoding='utf-8') + '\nend)()'


def script():
    parts = ['local M={}', 'local script={Parent=M}', 'local require=function(x) return x end']
    for n in MODULES:
        parts.append(f'M.{n}={module(n)}')
    parts.append(BODY)
    return '\n'.join(parts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_checks()
    for problem in problems:
        print('FAIL:', problem)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'combat_service.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode or (1 if problems else 0))
