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

-- BD-593 Fly glide on the client (Shared/ClassMovement.glideStep + src/client/ClassGlide.client.luau). Free fall at gravity 250 against
-- a glide held the whole way down: the fall is held at glideFallSpeed for glideSeconds, then falls freely; it never touches a rise.
local fly=CM.rules("Fly").jump
local cap,secs=fly.glideFallSpeed,fly.glideSeconds
assert(cap==12 and secs==1.0,"BD-593 changes no glide numbers (12 studs/s, 1 s)")
local function fall(held,class)
  local vy,used,t,worst,atCap=0,0,0,0,0
  for k=1,240 do
    vy-=250*DT                                           -- the physics step
    vy,used=CM.glideStep(class or "Fly",held,false,vy,used,DT) -- the Heartbeat write
    t+=DT; worst=math.min(worst,vy)
    if math.abs(vy+cap)<1e-6 then atCap+=DT end
  end
  return worst,atCap,used
end
local wFree,cFree=fall(false)
assert(wFree<-100 and cFree==0,"no glide held: free fall ("..wFree..")")
local wGlide,cGlide,uGlide=fall(true)
assert(cGlide>0.9 and cGlide<=secs+2*DT and uGlide<=secs+2*DT,"glide held: fall held at "..cap.." for about "..secs.." s ("..cGlide..")")
assert(wGlide<-cap,"after the glide budget the dino falls freely again ("..wGlide..")")
local wG2,cG2=fall(true,"Ground"); assert(cG2==0 and wG2<-100,"Ground never glides")
local wW,cW=fall(true,"Water"); assert(cW==0,"Water never glides")
-- rising is never slowed; grounded resets the budget; junk is harmless
local r1,u1=CM.glideStep("Fly",true,false,40,0.5,DT); assert(r1==40 and u1==0.5,"a rise is untouched")
local r2,u2=CM.glideStep("Fly",true,true,-50,0.9,DT); assert(r2==-50 and u2==0,"grounded: no limit, budget reset")
local r3,u3=CM.glideStep("Fly",false,false,-50,0,DT); assert(r3==-50 and u3==0,"button not held: no limit")
local r4,u4=CM.glideStep("Fly",true,false,-5,0,DT); assert(r4==-5 and math.abs(u4-DT)<1e-9,"slower than the cap: kept, budget still counts")
for _,j in {0/0,math.huge,-math.huge,"x",nil} do
  local a,b=CM.glideStep("Fly",true,false,j,j,j); assert(a==a and b==b and a~=math.huge and a~=-math.huge,"junk is finite")
end
assert(select(2,CM.glideStep("Fly",true,false,-50,0,5))<=0.25,"one huge frame cannot burn more than 0.25 s")
-- MUTANTS: a glide that never limits, limits forever, or limits a rise must fail the checks above
local function limitsFall(f) local vy,used,worst=0,0,0 for k=1,240 do vy-=250*DT vy,used=f(vy,used) worst=math.min(worst,vy) end return worst end
assert(limitsFall(function(v,u) return v,u end)<-100,"control: no glide falls freely")
assert(limitsFall(function(v,u) return math.max(v,-cap),0 end)>=-cap-1e-9,"control: a glide that never ends keeps the cap (which the budget check rejects)")
print("fly glide ok")

-- BD-595 (LEAD decision FH1, docs/101 s20) Fly hover cap on the client: ClassMovement.hoverStep, measured at the FEET, cap 6.5 from the
-- class table, a leap exempt, only ever lowering an upward speed. Simulated like the game: physics step (gravity, move), then Heartbeat.
local HIP,SIZEY=2,2.4                    -- stand-in Humanoid.HipHeight and root Size.Y
local STAND=HIP+SIZEY/2                  -- root centre height above the ground while standing (3.2)
local CAP=CM.rules("Fly").jump.heightCap
assert(CAP==6.5,"BD-595 keeps the cap number (6.5)")
assert(math.abs(CM.feetHeight(STAND,HIP,SIZEY))<1e-9 and math.abs(CM.feetHeight(STAND+6,HIP,SIZEY)-6)<1e-9,"feet height = root height - (HipHeight + Size.Y/2)")
local function realStep(v,rh,t,leap) return CM.hoverStep("Fly",v,rh,HIP,SIZEY,leap,DT) end
local function none(v) return v end
-- one airtime: returns the highest feet height (studs above standing) and the seconds in the air
local function flight(v0,step,leapSeconds,glide)
  local vy,root,peak,t,used,worstFall=v0,STAND,0,0,0,0
  for k=1,1200 do
    vy-=Cfg.Gravity*DT; root+=vy*DT; t+=DT
    if vy<0 and root<=STAND then break end
    peak=math.max(peak,root-STAND)
    vy=step(vy,root,t,t<leapSeconds)
    if glide then vy,used=CM.glideStep("Fly",true,false,vy,used,DT); if t>0.1 then worstFall=math.min(worstFall,vy) end end
  end
  return peak,t,worstFall
end
local function hoverChecks(step)
  local plainV=CM.jumpPower("Fly",Cfg.JumpPower)
  local freePlain=flight(plainV,none,0)
  assert(freePlain>5.4 and freePlain<6.2,"control: a plain Fly jump rises about 6.05 uncapped ("..freePlain..")")
  assert(flight(plainV,step,0)==freePlain,"a plain Fly jump is NOT cut (apex "..freePlain..")")
  local boostedV=CM.jumpPower("Fly",150)      -- Admin_jumpPower 150
  assert(flight(boostedV,none,0)>20,"control: a boosted jump would rise far past the cap")
  local capped=flight(boostedV,step,0)
  assert(capped<=CAP+1e-6 and capped>CAP-0.1,"a boosted jump is held at "..CAP.." studs of feet height ("..capped..")")
  local leapV=Prog.LeapVerticalSpeed
  local freeLeap=flight(leapV,none,0)
  assert(freeLeap>9.5,"control: a leap rises about 10 studs ("..freeLeap..")")
  assert(flight(leapV,step,Prog.LeapDuration)==freeLeap,"a leap is exempt (apex "..freeLeap..")")
  assert(flight(leapV,step,0)<=CAP+1e-6,"control: without the exemption the same leap would be cut to the cap")
  -- never adds: over a grid the written speed is never above the speed read
  for _,cls in {"Fly","Ground","Armored","Water","Bogus"} do
    for _,v in {-50,-1,0,0.5,10,55,200} do
      for rh=0,40,0.5 do
        for _,leap in {false,true} do
          local r=CM.hoverStep(cls,v,rh,HIP,SIZEY,leap,DT); assert(r<=v+1e-12,"never adds speed ("..cls..","..v..","..rh..")")
          if v<=0 then assert(r==v,"a fall is never touched") end
        end
      end
    end
  end
  for _,v in {-50,0,0.5,10,55,200} do for rh=0,40,0.5 do
    local r=step(v,rh,0.01,false); assert(r<=v+1e-12,"step never adds speed")
  end end
end
hoverChecks(realStep)
print(string.format("hover numbers: plain Fly jump apex %.3f (uncapped %.3f), boosted (jump power 165) %.3f (uncapped %.1f), leap %.3f (uncapped %.3f, without exemption %.3f)",
  flight(CM.jumpPower("Fly",Cfg.JumpPower),realStep,0),flight(CM.jumpPower("Fly",Cfg.JumpPower),none,0),
  flight(CM.jumpPower("Fly",150),realStep,0),flight(CM.jumpPower("Fly",150),none,0),
  flight(Prog.LeapVerticalSpeed,realStep,Prog.LeapDuration),flight(Prog.LeapVerticalSpeed,none,0),flight(Prog.LeapVerticalSpeed,realStep,0)))
-- Ground / Armored / Water are never touched; junk is harmless
for _,cls in {"Ground","Armored","Water","Bogus"} do assert(CM.hoverStep(cls,80,100,HIP,SIZEY,false,DT)==80,cls.." has no hover cap") end
for _,j in {0/0,math.huge,-math.huge,"x",nil} do
  local a=CM.hoverStep("Fly",j,j,j,j,j,j); assert(a==a and a~=math.huge and a~=-math.huge,"junk is finite")
end
assert(CM.hoverStep("Fly",50,0/0,HIP,SIZEY,false,DT)<=50 and CM.hoverStep("Fly",50,STAND+CAP+1,HIP,SIZEY,false,DT)==0,"above the cap: no more rise")
-- glide still 12 studs/s after a capped boosted jump and after a plain one (hover first, then glide, like the client)
for _,v0 in {CM.jumpPower("Fly",Cfg.JumpPower),CM.jumpPower("Fly",150)} do
  local _,airtime,worst=flight(v0,realStep,0,true)
  assert(math.abs(worst+cap)<1e-6,"glide still holds the fall at "..cap.." studs/s ("..worst..")")
  local _,freeAir=flight(v0,realStep,0,false)
  assert(airtime>freeAir+0.1,"the glide lengthens the airtime ("..airtime.." vs "..freeAir..")")
end
-- MUTANTS: each broken stepper must fail the checks above
local function mutantCaught(step,label) assert(not pcall(hoverChecks,step),"MUTANT not caught: "..label) end
mutantCaught(function(v,rh,t,leap) return CM.hoverStep("Fly",v,rh,0,0,leap,DT) end,"measures the root centre, not the feet")
mutantCaught(function(v,rh,t,leap) return CM.hoverStep("Fly",v,rh,HIP,SIZEY,false,DT) end,"no leap exemption")
mutantCaught(function(v,rh,t,leap) return math.max(CM.hoverStep("Fly",v,rh,HIP,SIZEY,leap,DT),1) end,"adds upward velocity")
mutantCaught(function(v,rh,t,leap) local r=CM.hoverStep("Fly",v,rh,HIP,SIZEY,leap,DT); if r==0 and v>0 then return 12 end return r end,"pushes up at the cap")
mutantCaught(function(v) return v end,"cap off")
print("fly hover cap ok")
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
    assert 'Heartbeat' not in svc and 'AssemblyLinearVelocity' not in svc and 'limitVertical' not in svc, 'BD-595: the dead server hover/glide loop is gone (the character is client-owned)'
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
    glide = (ROOT / 'src/client/ClassGlide.client.luau').read_text(encoding='utf-8')
    for needle, why in (
        ('RunService.Heartbeat:Connect', 'glide is applied every frame'),
        ('CM.glideStep("Fly"', 'per-frame decision comes from the pure module'),
        ('CM.hoverStep("Fly"', 'BD-595: the hover cap comes from the pure module'),
        ('h.HipHeight, root.Size.Y', 'BD-595: the cap is measured at the feet'),
        ('isLeaping(c)', 'BD-595: a leap is exempt'),
        ('RunState") ~= "Active"', 'only during a run'),
        ('remote:FireServer(value)', 'server is still told (one boolean)'),
    ):
        assert needle in glide, 'ClassGlide.client: ' + why
    assert glide.count('AssemblyLinearVelocity = Vector3.new(') == 1, 'ClassGlide.client: single write site'
    # The character is network-owned by its player (server/FallRecovery.luau, Studio measurement BD-593): a server write to its
    # velocity does nothing, so the glide must not be (only) a server loop. Fail if the only glide limiter is the server's.
    assert 'glideStep' in (ROOT / 'src/shared/ClassMovement.luau').read_text(encoding='utf-8'), 'glideStep exists'
    print('class movement wiring ok')
raise SystemExit(result.returncode)
