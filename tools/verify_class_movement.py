"""BD-231/233/234 class movement rules: pure module checks (src/shared/ClassMovement.luau). Not wired into gameplay."""
import argparse, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['Config', 'ProgressionConfig', 'CombatConfig', 'ClassMovement']

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
print("class movement ok")
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
    raise SystemExit(result.returncode)
