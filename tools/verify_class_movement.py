"""BD-231/233/234 class movement rules: pure module checks (src/shared/ClassMovement.luau). Not wired into gameplay."""
import argparse, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['Config', 'ProgressionConfig', 'CombatConfig', 'ClassMovement', 'DashHold']

BODY = r'''
local CM,Cfg,Prog,Combat=M.ClassMovement,M.Config,M.ProgressionConfig,M.CombatConfig
assert(CM.Enabled==false,"flag defaults OFF")
local function fin(...) for _,v in {...} do assert(v==v and v~=math.huge and v~=-math.huge,"finite") end end
local dirs={{1,0},{0,1},{-1,0},{0,-1},{0.6,0.8},{0,0},{0/0,5},{math.huge,1},{-3,-4}}
local tick=Cfg.MovementGuardTickSeconds
for _,c in CM.ClassNames do
  local ws=CM.walkSpeed(c)
  assert(math.abs(ws-Cfg.WalkSpeed*Combat.Classes[c].speedX)<1e-9,c.." speed from CombatConfig")
  assert(ws>0)
  for _,a in CM.Actions do
    for _,d in dirs do
      local vx,vy,vz=CM.launchVelocity(c,a,d[1],d[2]); fin(vx,vy,vz)
      local planar=math.sqrt(vx*vx+vz*vz)
      local lim=CM.speedLimit(c,a)
      assert(planar<=lim+1e-6,c..a.." planar within MovementSpeedLimit")
      assert(CM.guardAllowsPlanar(planar,tick,lim),c..a.." guard accepts")
      assert(not CM.guardAllowsPlanar(lim*Cfg.MovementGuardSpeedTolerance+100,1,lim),"guard still rejects teleports")
      assert(vy<=math.max(Cfg.JumpPower,Prog.LeapVerticalSpeed)+1e-9 and vy<=Cfg.MovementGuardMaxVerticalSpeed,c..a.." vertical inside guard")
      assert(vy>=0 and CM.duration(c,a)>=0 and CM.cooldownRemaining(c,a,nil,nil)==0)
    end
    assert(CM.cooldownRemaining(c,a,10,10)==CM.rules(c)[a].cooldown)
    assert(CM.cooldownRemaining(c,a,10,1e9)==0 and CM.cooldownRemaining(c,a,10,0/0)>=0)
  end
  for _,s in CM.States do
    local i=CM.animationIntent(c,s,ws); assert(type(i.clip)=="string" and #i.clip>0 and i.speedScale>0 and i.speedScale<=2,c..s)
  end
  assert(CM.animationIntent(c,"walk",0).clip==CM.animationIntent(c,"idle",0).clip,"walk at rest shows idle")
  assert(CM.animationIntent(c,"nonsense",0/0).clip==CM.animationIntent(c,"idle",0).clip,"junk -> idle")
end
-- distinct clips per class for the same state (BD-233/234 can bind separately)
for _,s in CM.States do
  local seen={}
  for _,c in CM.ClassNames do local id=CM.animationIntent(c,s,30).clip; assert(not seen[id],"clip id unique across classes "..s); seen[id]=true end
end
assert(CM.walkSpeed("Ground")==Cfg.WalkSpeed)
local gx,gy=CM.launchVelocity("Ground","jump",1,0)
local ax,ay=CM.launchVelocity("Armored","jump",1,0)
assert(gy==Cfg.JumpPower and ay>0 and ay<gy and CM.walkSpeed("Armored")<CM.walkSpeed("Ground"))
local lgx,lgy=CM.launchVelocity("Ground","leap",1,0)
assert(lgx==Prog.LeapHorizontalSpeed and lgy==Prog.LeapVerticalSpeed,"ground leap is the existing leap")
assert(CM.rules("Ground").leap.cooldown==60 and CM.rules("Armored").leap.cooldown==60)
-- Fly
local fx,fy=CM.launchVelocity("Fly","jump",1,0)
assert(fy>gy and fx>gx,"fly jumps higher and faster")
local apex=fy*fy/(2*Cfg.Gravity); assert(apex<=CM.rules("Fly").jump.heightCap,"fly jump apex under its cap")
assert(CM.clampHeight("Fly","jump",100,10)==10+CM.rules("Fly").jump.heightCap,"fly height clamped")
assert(CM.clampHeight("Ground","jump",100,10)==100,"ground not clamped")
assert(CM.limitVertical("Fly","jump",50,CM.rules("Fly").jump.heightCap+1)==0,"no climbing above cap")
assert(CM.limitVertical("Fly","jump",-100,3,true)==-CM.rules("Fly").jump.glideFallSpeed,"glide caps fall")
assert(CM.limitVertical("Fly","jump",-100,3,false)==-100,"no glide, no cap")
local flx,fly2=CM.launchVelocity("Fly","leap",1,0)
assert(flx>lgx and CM.duration("Fly","leap")>CM.duration("Ground","leap") and fly2<=Prog.LeapVerticalSpeed,"fly leap longer arc")
for h=0,200 do local y=CM.clampHeight("Fly","leap",1000,h); assert(y-h<=CM.rules("Fly").leap.heightCap) end
-- Water: never up
for _,a in CM.Actions do
  for _,d in dirs do
    local _,vy=CM.launchVelocity("Water",a,d[1],d[2]); assert(vy==0,"water never upward "..a)
  end
  assert(CM.limitVertical("Water",a,999,0)==0 and CM.limitVertical("Water",a,-5,0)==-5,"water limitVertical")
  assert(CM.clampHeight("Water",a,50,3)==3,"water ground-bound")
end
assert(CM.rules("Water").jump.kind=="dash" and CM.rules("Water").jump.powerX==0)
local wl=CM.rules("Water").leap; local wj=CM.rules("Water").jump
assert(wl.dashSpeed>wj.dashSpeed and wl.dashSeconds>wj.dashSeconds and wl.hitWindow>0,"water leap: longer, faster, hit window")
assert(wj.cooldown>0,"water dash has its own cooldown")
-- canStart
local ok,k=CM.canStart("Water","jump",{grounded=true,now=100}); assert(ok and k=="dash")
ok=CM.canStart("Water","jump",{grounded=true,now=101,lastJumpAt=100}); assert(not ok,"dash cooling down")
ok=CM.canStart("Water","jump",{grounded=true,now=100+wj.cooldown,lastJumpAt=100}); assert(ok)
ok=CM.canStart("Fly","jump",{grounded=false,now=1}); assert(not ok,"no flying from the air")
ok,k=CM.canStart("Ground","jump",{grounded=true,now=1}); assert(ok and k=="jump")
ok=CM.canStart("Ground","leap",{grounded=true,now=30,lastLeapAt=0}); assert(not ok,"leap 60 s cooldown")
ok=CM.canStart("Ground","leap",{grounded=true,now=60,lastLeapAt=0}); assert(ok)
ok=CM.canStart("Bogus","jump",nil); assert(not ok)
ok=CM.canStart("Bogus","jump",{grounded=true,now=0}); assert(ok,"unknown class = Ground")
local x,z=CM.clampToArena(1e9,-1e9); assert(x==Cfg.ArenaHalfWidth and z==-Cfg.ArenaHalfWidth)
-- BD-246 wiring helpers
assert(CM.classForSpecies("mosasaurus")=="Water" and CM.classForSpecies("pteranodon")=="Fly" and CM.classForSpecies("ankylosaurus")=="Armored")
assert(CM.classForSpecies(nil)=="Ground" and CM.classForSpecies("nope")=="Ground" and CM.classForSpecies(5)=="Ground")
assert(CM.jumpPower("Water",Cfg.JumpPower)==0 and CM.jumpPower("Ground",Cfg.JumpPower)==Cfg.JumpPower and CM.jumpPower("Fly",Cfg.JumpPower)>Cfg.JumpPower)
print("class movement ok")

-- BD-571 client delivery of the Water dash (Shared/DashHold + src/client/ClassDash.client.luau).
local DH=M.DashHold
local wj2=CM.rules("Water").jump
assert(wj2.dashSpeed==48 and wj2.dashSeconds==0.35 and wj2.cooldown==3,"BD-571 changes no speed numbers (48 studs/s, 0.35 s, 3 s)")
local dvx,dvy,dvz=CM.launchVelocity("Water","jump",1,0)
local dsec=CM.duration("Water","jump")
local want=dvx*dsec -- 16.8 studs
assert(math.abs(want-16.8)<1e-9 and dvy==0 and dvz==0,"dash is about 17 studs")
-- junk answers never start a hold
for _,j in {{0/0,0},{math.huge,0},{0,0},{1000,0},{"a",1},{1,nil}} do assert(DH.begin(j[1],j[2],0,dsec)==nil,"junk answer refused") end
assert(DH.begin(dvx,dvz,0,0)==nil and DH.begin(dvx,dvz,0,-1)==nil and DH.begin(dvx,dvz,0/0,dsec)==nil,"bad duration/time refused")
assert(DH.begin(dvx,dvz,5,100).untilAt-5==DH.MaxSeconds,"hold length capped")
-- 60 Hz delivery against a stand-in for the Humanoid ground controller: velocity decays by exp(-K dt) every frame (target 0 = worst
-- case, the player is not steering). The sim writes like the client: Heartbeat step, then the physics step moves and damps.
local K,DT=12,1/60
local function deliver(stepFn,wallAtFrame,aliveUntil)
  local hold=DH.begin(dvx,dvz,0,dsec)
  local pos,vel,vy=0,0,0
  local writes,ended,after,frames=0,false,0,0
  for k=0,90 do
    local action,vx,y,vz
    if not ended then
      frames+=1
      action,vx,y,vz=stepFn(hold,k*DT,vy,wallAtFrame~=nil and k>=wallAtFrame,aliveUntil==nil or k<aliveUntil)
      if action~="end" then vel=vx; writes+=1; assert(y<=0,"never upward") end
      if action~="hold" then ended=true end
    else after+=1 end
    pos+=vel*DT; vel=vel*math.exp(-K*DT)
  end
  return pos,writes,ended,frames
end
local function single(hold,now,vy,blocked,alive)
  if now==0 then return "hold",hold.vx,0,hold.vz end -- the old client: one write, then nothing (ends at once)
  return "end",0,0,0
end
local pos,writes,ended,frames=deliver(DH.step)
assert(ended and writes==math.ceil(dsec/DT) and frames==writes+1,"velocity written every frame for the duration, then one clean end ("..writes..","..frames..")")
assert(pos>=want*0.9 and pos<=want*1.3,"held dash travels ~17 studs (plus a short coast) through a damping controller ("..pos..")")
local pos1=deliver(single)
assert(pos1<want*0.35 and pos>3*pos1,"CONTROL: a single write barely moves the dino ("..pos1.." vs "..pos..")")
-- ends cleanly: after the end no further writes (steps return end for any later time)
for _,t in {dsec,dsec+0.01,dsec*3,1e9} do local a=DH.step(DH.begin(dvx,dvz,0,dsec),t,0,false,true); assert(a=="end","no write after the duration") end
-- wall: stops at once, one zero write, no more holding; blocked from frame 0 never moves the dino
local posw,writesw,endedw=deliver(DH.step,6)
assert(endedw and writesw==7 and posw<want*0.5,"wall stops the dash ("..posw..", "..writesw..")")
local ax,avx,ay,avz,why=DH.step(DH.begin(dvx,dvz,0,dsec),0.1,0,true,true)
assert(ax=="stop" and avx==0 and avz==0 and why=="wall","wall = planar stop")
local pos0=deliver(DH.step,0); assert(pos0<=0.01,"wall at the start: no travel")
-- not alive (died, run ended, changed dino): nothing written
local posd,writesd,endedd=deliver(DH.step,nil,5)
assert(endedd and writesd==5 and posd<want*0.5,"dash ends when the dino is no longer alive/Water")
assert(DH.step(DH.begin(dvx,dvz,0,dsec),0.1,0,false,false)=="end","dead = end without a write")
-- vertical: never above 0, falling kept, junk vertical -> 0
for _,vyIn in {50,3,0,-9,-300,0/0,math.huge,-math.huge} do
  local a,_,y=DH.step(DH.begin(dvx,dvz,0,dsec),0.1,vyIn,false,true)
  assert(a=="hold" and y<=0 and y==y and (vyIn>=0 or vyIn~=vyIn or vyIn==math.huge or y==vyIn or vyIn==-math.huge),"vertical clamp "..tostring(vyIn))
end
-- MovementGuard: the dash is plausible at every sampling interval, with the dash MovementSpeedLimit AND (expired / late) walk speed only
local limit=CM.speedLimit("Water","jump"); local walk=CM.walkSpeed("Water")
assert(limit==48 and walk*Cfg.MovementGuardSpeedTolerance>=48,"walk-speed envelope alone already covers 48 studs/s")
for i=1,40 do
  local dt=math.max(i*0.0125,tick*0.5)
  local dist=math.min(dvx*dt,want)
  assert(dist<=limit*dt*Cfg.MovementGuardSpeedTolerance+Cfg.MovementGuardBurstStuds,"guard accepts dash at dt "..dt)
  assert(dist<=walk*dt*Cfg.MovementGuardSpeedTolerance+Cfg.MovementGuardBurstStuds,"guard accepts dash on walk speed alone at dt "..dt)
end
assert(CM.guardAllowsPlanar(48,tick*0.5,limit) and CM.guardAllowsPlanar(48,tick*0.5,walk),"guardAllowsPlanar agrees")
-- MUTANTS: the delivery checks above must fail for broken steppers
local function caught(stepFn,label,wall)
  local ok=pcall(function()
    local p,w,e,f=deliver(stepFn,wall)
    assert(e and w==math.ceil(dsec/DT) and f==w+1,"every frame then end")
    assert(p>=want*0.9 and p<=want*1.3,"distance")
    if wall then assert(p<want*0.5,"wall") end
  end)
  assert(not ok,"MUTANT not caught: "..label)
end
caught(single,"single write")
caught(function(h,n,vy,b,a) local r={DH.step(h,n,vy,b,a)}; if r[1]=="hold" and n>=0.1 then return "end",0,0,0 end return table.unpack(r) end,"stops early")
caught(function(h,n,vy,b,a) local r={DH.step(h,n+10,vy,b,a)}; if r[1]=="end" then return "hold",h.vx,0,h.vz end return table.unpack(r) end,"never ends")
caught(function(h,n,vy,b,a) return DH.step(h,n,vy,false,a) end,"ignores wall",6)
print("dash delivery ok")
'''


def module(name):
    return '(function()\n' + (ROOT / 'src/shared' / f'{name}.luau').read_text(encoding='utf-8') + '\nend)()'


def script():
    parts = ['local M={}', 'local script={Parent=M}', 'local require=function(x) return x end']
    for n in MODULES:
        parts.append(f'M.{n}={module(n)}')
    parts.append(BODY)
    return '\n'.join(parts)


parser = argparse.ArgumentParser()
parser.add_argument('--runner', required=True)
args = parser.parse_args()
with tempfile.TemporaryDirectory() as d:
    path = Path(d) / 'class_movement.luau'
    path.write_text(script(), encoding='utf-8')
    result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
    print(result.stdout, end='')
    print(result.stderr, end='')
if result.returncode == 0:
    # BD-246 static wiring: everything is behind Config.CombatEnabled; default config is unchanged.
    svc = (ROOT / 'src/server/ClassMovementService.luau').read_text(encoding='utf-8')
    assert 'if not Config.ClassMovementEnabled then return end' in svc, 'service must be flag gated'
    assert 'ClassMovementService' in (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    prog = (ROOT / 'src/server/ProgressionService.luau').read_text(encoding='utf-8')
    assert 'if GameConfig.ClassMovementEnabled then ClassMovement.walkSpeed' in prog, 'class speed must be flag gated'
    assert 'ClassMovementEnabled = false' in (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert 'select("#", ...) ~= 0' in svc and 'MinRequestGap' in svc, 'dash remote validates args and rate limits'
    assert 'ClassGlide' in svc and 'glideDecision' in svc and 'typeof((...)) ~= "boolean"' in svc, 'glide remote validates a single boolean'
    assert 'CM.limitVertical("Fly", "jump", v.Y, root.Position.Y - hit.Position.Y, gliding)' in svc, 'glide goes through the hover-capped limiter'
    assert (ROOT / 'src/client/ClassGlide.client.luau').exists()
    for f in ('CombatService', 'PredationService', 'MovementGuard'):
        assert 'CooldownMemory' in (ROOT / f'src/server/{f}.luau').read_text(encoding='utf-8'), f + ' clocks keyed by UserId (BD-363)'
    dash = (ROOT / 'src/client/ClassDash.client.luau').read_text(encoding='utf-8')
    for needle, why in (
        ('RunService.Heartbeat:Connect', 'dash velocity is re-applied every frame'),
        ('DashHold.step(', 'per-frame decision comes from the pure module'),
        ('DashHold.begin(', 'the answer starts a hold'),
        ('workspace:Blockcast(', 'wall check each frame'),
        ('CM.duration("Water", "jump")', 'hold length is the class dash duration'),
        ('isWater()', 'Water only'),
        ('remote:FireServer()', 'server stays authoritative: the request still goes to the server'),
    ):
        assert needle in dash, 'ClassDash.client: ' + why
    assert dash.count('AssemblyLinearVelocity = Vector3.new(') == 1 and 'math.min(v.Y, 0)' not in dash, 'single write site, vertical clamp lives in DashHold'
    assert 'remote:FireClient(player, vx, vy, vz)' in svc and 'dist' in svc and 'Blockcast' in svc, 'server answer + wall check unchanged'
    print('class movement wiring ok')
raise SystemExit(result.returncode)
