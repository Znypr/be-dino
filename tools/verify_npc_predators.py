"""BD-245 NPC predators (src/shared/NpcPredatorRules.luau, the pure core of src/server/NpcPredatorService.luau).

Runs the module with the pinned Luau runtime: flag-off identity, state transitions (patrol/alert/chase/windup/bite/retreat),
aggro range, give-up, leash, dodge, soft cooldown + grace + bite cap, never-targeting rules (protected, dead,
inactive, safe meadow, recently bitten), hard NPC cap and player-scaled count, spawn points from BiomePlacement/BiomeMap
rules (away from players, off water, allowed biomes, spread), respawn timers, defeat exactly once, capped assist bonus,
never-one-shot across all classes, determinism with a seeded RNG, sleeping NPCs, a 12-player fuzz. Static checks prove the
flag-off wiring (service guards, Bootstrap hook, no touching of eggs/settlement, HUD hook, Bootstrap.client untouched).
Not a Studio test: Humanoid movement, models, the real remote and HUD rendering are NOT covered here.
"""
from pathlib import Path
import re
import subprocess
import combat_harness as H

ROOT = Path(__file__).resolve().parents[1]
H.MODULES = ['CombatConfig', 'CombatStats', 'CombatState', 'CombatTeamUp', 'LowPolyDinoAssets', 'CombatRules',
             'IslandLayout', 'BiomeMap', 'BiomePlacement', 'NpcPredatorRules']

BODY = r'''
local R,Npc,Layout=M.CombatRules,M.NpcPredatorRules,M.IslandLayout
local NC=Npc.Config
local function key(u,r) return R.key(u,r) end
local function P(k,x,z,extra) local p={key=k,x=x,y=Layout.height(x,z),z=z,alive=true,active=true,peaceful=false,protectedUntil=0}
  if extra then for a,b in extra do p[a]=b end end return p end
local function terrain() return Npc.newTerrain({half=416,seed=1404}) end

-- 1. flag-off identity: inert world, nothing created, RNG untouched
local off=Npc.newWorld(false,42,terrain())
local st0=off.rng.state
local o=Npc.populate(off,100,{P("a",200,200)}); assert(#o.spawned==0 and #o.removed==0)
assert(#Npc.step(off,1,0.2,{P("a",200,200)})==0 and Npc.defeated(off,1,5)==nil and Npc.count(off)==0)
assert(next(off.slots)==nil and next(off.respawnAt)==nil and next(off.grace)==nil and off.serial==0 and off.rng.state==st0,"flag off leaves no state")
local cw0=R.new(true)
assert(Npc.joinCombat(off,cw0,{userId="npc1",runId="w1",class="Ground",score=1},0)==nil and next(cw0.dinos)==nil,"flag off: nobody joins combat")
assert(Npc.performBite(off,cw0,{slot=1,npcKey="x"},0,{}).ok==false)

-- 2. caps and player-scaled count
assert(NC.MaxNpcs<=8 and NC.MaxNpcs==6)
assert(Npc.desiredCount(0)==0 and Npc.desiredCount(-3)==0 and Npc.desiredCount(0/0)==0 and Npc.desiredCount(1)==2 and Npc.desiredCount(3)==2 and Npc.desiredCount(4)==3)
assert(Npc.desiredCount(12)==5 and Npc.desiredCount(500)==NC.MaxNpcs,"hard cap")
for n=0,60 do assert(Npc.desiredCount(n)<=NC.MaxNpcs and Npc.desiredCount(n)>=Npc.desiredCount(math.max(0,n-1)),"monotone and capped") end
-- every speed is far below a player's walk speed (22, Armored x0.8) so a child can always run away
for _,sp in {NC.PatrolSpeed,NC.ChaseSpeed,NC.RetreatSpeed} do assert(sp<=12) end
assert(NC.WindupSeconds>=0.5 and NC.RespawnSeconds>=45 and NC.MaxBitesPerAggro<=2 and NC.BiteCooldownSeconds>=2)
assert(NC.AggroRange<=30 and NC.ChaseMaxSeconds<=8 and NC.GiveUpRange>NC.AggroRange and NC.LeashRadius>NC.PatrolRadius)
local b=Npc.budget(); assert(b.maxMovesPerSecond<=30 and b.maxNpcs==6)

-- 3. spawn points: rule checks + spread + away from players, many seeds
local biomesSeen={}
for seed=1,40 do
  local w=Npc.newWorld(true,seed,terrain())
  local players={P("1|a",150,-100),P("2|a",-200,250),P("3|a",20,40)}
  local out=Npc.populate(w,0,players); assert(#out.spawned==Npc.desiredCount(3),"spawned the wanted count")
  for _,n in out.spawned do
    local ok,why=Npc.spawnPointOk(w.terrain,n.x,n.z); assert(ok,"spawn rule: "..tostring(why))
    assert(not Npc.inSafeZone(n.x,n.z) and not Layout.inPool(n.x,n.z,8),"not in the meadow or water")
    for _,p in players do assert(math.sqrt((p.x-n.x)^2+(p.z-n.z)^2)>=NC.SpawnMinPlayerDistance,"away from players") end
    for _,m in out.spawned do if m~=n then assert(math.sqrt((m.x-n.x)^2+(m.z-n.z)^2)>=NC.SpawnMinSeparation,"apart") end end
    assert(n.state=="patrol" and n.class=="Ground" and n.score>=NC.ScoreMin and n.score<=NC.ScoreMax)
    assert(n.userId=="npc"..n.slot and n.key==key(n.userId,n.runId))
    local found=false for _,bm in NC.Biomes do if bm==n.biome then found=true end end assert(found,"island biome only: "..n.biome)
    biomesSeen[n.biome]=true
  end
end
local nb=0 for _ in biomesSeen do nb+=1 end assert(nb>=3,"spawns spread over at least 3 biomes, got "..nb)
-- spawnPointOk rejects: edge, safe meadow, water, steep/keep-out
local T=terrain()
assert(select(2,Npc.spawnPointOk(T,410,0))=="edge" and select(2,Npc.spawnPointOk(T,0,30))=="safe_zone")
local pool=Layout.Pools[1]; assert(select(2,Npc.spawnPointOk(T,pool.x,pool.z))=="water")
-- no valid point: nothing spawns and a retry is scheduled
local closed=Npc.newWorld(true,5,terrain())
local crowd={} for i=1,60 do crowd[i]=P("c"..i,-340+(i%10)*70,-340+math.floor(i/10)*120) end
local oc=Npc.populate(closed,0,crowd); assert(#oc.spawned==0 and closed.respawnAt[1]==NC.RetrySeconds,"no valid spawn: retry later")

-- helpers for state machine scenarios -------------------------------------------------------------------------------
local function openSpot() -- a point with a walkable disc of radius 70 around it
  for x=-300,300,20 do for z=-300,300,20 do
    local ok=true
    for a=0,11 do local ax,az=x+math.cos(a/12*6.2832)*70,z+math.sin(a/12*6.2832)*70
      if not Npc.walkable(T,ax,az) then ok=false break end end
    if ok and Npc.walkable(T,x,z) then return x,z end
  end end
  error("no open spot")
end
local OX,OZ=openSpot()
local function setup(seed)
  local w=Npc.newWorld(true,seed,terrain(),{kinematic=true})
  Npc.populate(w,0,{P("far",-399,399)})
  local n=w.slots[1]; assert(n,"npc spawned")
  n.x,n.z,n.y,n.homeX,n.homeZ,n.lastX,n.lastZ=OX,OZ,Layout.height(OX,OZ),OX,OZ,OX,OZ
  n.idleUntil=0; n.noAggroUntil=0
  local cw=R.new(true); cw.defeatCount=0; cw.bonuses={}
  cw.onDefeat=function(v,a,bo) cw.defeatCount+=1; cw.bonuses[v.key]=bo end
  local jd=Npc.joinCombat(w,cw,n,0)
  -- BD-1025: a wild predator has Cfg.WildHpX of the normal HP for its size; a player of the same size keeps the full HP
  assert(math.abs(jd.state.maxHp-Stats.maxHp(n.class,n.s)*M.CombatConfig.WildHpX)<1e-6,"wild predator HP = normal HP x WildHpX")
  assert(M.CombatConfig.WildHpX<1 and R.join(R.new(true),{userId=9,runId="p",class=n.class,score=n.score,now=0}).state.maxHp==Stats.maxHp(n.class,n.s),"players keep full HP")
  return w,cw,n
end
local function joinP(cw,u,r,score) return R.join(cw,{userId=u,runId=r,class="Ground",score=score or 0,now=0}) end
local DT=0.2

-- 4. A: stationary player in range -> alert -> chase -> windup -> bite; soft cooldown, grace, bite cap, then retreat/patrol
do
  local w,cw,n=setup(1)
  local pd=joinP(cw,1,"r"); local pl=P(pd.key,OX+15,OZ)
  local players={pl}
  local seen,bites,hits,times={},0,0,{}
  local t,left,cycleDone,alertAfter,retreatAt,homeAtDone=0,false,false,false,nil,nil
  while t<60 do
    t+=DT
    local evs=Npc.step(w,t,DT,players)
    seen[n.state]=true
    if n.state~="patrol" then left=true elseif left and not cycleDone then cycleDone=t; homeAtDone=math.sqrt((n.x-n.homeX)^2+(n.z-n.homeZ)^2) end
    if n.state=="retreat" and not retreatAt then retreatAt=t end
    if cycleDone and retreatAt and t<retreatAt+NC.ForgiveSeconds-0.5 and n.state~="patrol" and n.state~="retreat" then alertAfter=true end
    for _,ev in evs do
      bites+=1; table.insert(times,t)
      local res=Npc.performBite(w,cw,ev,t,players)
      if res.ok then hits+=1; assert(not res.defeated and res.damage/pd.state.maxHp<=0.25,"never one-shot") end
    end
    R.tick(cw,t,DT)
  end
  for _,s in {"alert","chase","windup","bite","retreat","patrol"} do assert(seen[s],"state visited: "..s) end
  assert(cycleDone,"first aggro ended")
  assert(not alertAfter,"forgives the player it gave up on")
  local firstCycle=0 for _,bt in times do if bt<=cycleDone then firstCycle+=1 end end
  assert(firstCycle>=1 and firstCycle<=NC.MaxBitesPerAggro,"at most "..NC.MaxBitesPerAggro.." bites per aggro, got "..firstCycle)
  assert(hits>=1 and pd.state.phase=="Alive")
  assert(times[1]>=NC.AlertSeconds+NC.WindupSeconds,"alert then windup before the first bite")
  if times[2] and times[2]<=cycleDone then assert(times[2]-times[1]>=NC.TargetGraceSeconds-1e-6 and times[2]-times[1]>=NC.BiteCooldownSeconds-1e-6,"grace + soft cooldown between bites") end
  assert(homeAtDone<=NC.HomeArrive+NC.RetreatSpeed*DT,"walked home before calming down: "..homeAtDone)
  assert(w.grace[pd.key]~=nil)
end

-- 5. B: fleeing player is never caught; the chase gives up; speeds respected; leash respected
do
  local w,cw,n=setup(2)
  local pd=joinP(cw,1,"r"); local px=OX+15
  local hitsB,t,maxHome,gaveUp,maxStep,ran=0,0,0,false,0,false
  while t<14 do
    t+=DT; if n.state=="chase" or ran then ran=true; px+=22*DT end
    local pl=P(pd.key,px,OZ); if not Npc.walkable(T,px,OZ) then px=OX+15 end
    local bx,bz=n.x,n.z
    local evs=Npc.step(w,t,DT,{pl})
    maxStep=math.max(maxStep,math.sqrt((n.x-bx)^2+(n.z-bz)^2))
    for _,ev in evs do local r=Npc.performBite(w,cw,ev,t,{pl}); if r.ok then hitsB+=1 end end
    maxHome=math.max(maxHome,math.sqrt((n.x-n.homeX)^2+(n.z-n.homeZ)^2))
    if n.state=="retreat" then gaveUp=true end
  end
  assert(hitsB==0 and gaveUp,"a runner is never caught and the NPC gives up")
  assert(maxStep<=NC.ChaseSpeed*DT+1e-6,"never faster than ChaseSpeed")
  assert(maxHome<=NC.LeashRadius+NC.ChaseSpeed*DT,"stays inside the leash, got "..maxHome)
end

do -- immediate runner: slips away during the alert, the NPC just goes back to patrol
  local w,cw,n=setup(21); local pd=joinP(cw,1,"r"); local px,t,hitsB,sawChase=OX+15,0,0,false
  while t<10 do
    t+=DT; px+=22*DT
    local pl=P(pd.key,px,OZ)
    for _,ev in Npc.step(w,t,DT,{pl}) do if Npc.performBite(w,cw,ev,t,{pl}).ok then hitsB+=1 end end
    if n.state=="chase" then sawChase=true end
  end
  assert(hitsB==0 and pd.state.hp==pd.state.maxHp and n.state~="windup","an instant runner is never bitten")
end

-- 6. C: dodge during the windup -> the bite misses, nobody is hurt, no grace is set
do
  local w,cw,n=setup(3)
  local pd=joinP(cw,1,"r"); local pl=P(pd.key,OX+14,OZ)
  local t,missed,sawWindup=0,false,false
  while t<12 and not missed do
    t+=DT
    if n.state=="windup" and not sawWindup then sawWindup=true; pl=P(pd.key,pl.x,pl.z+13) end -- step sideways 13 studs
    local evs=Npc.step(w,t,DT,{pl})
    for _,ev in evs do
      local res=Npc.performBite(w,cw,ev,t,{pl})
      assert(res.ok==false and res.reason=="no_target","dodged bite finds nobody, got "..tostring(res.reason))
      missed=true
    end
  end
  assert(sawWindup and missed and pd.state.hp==pd.state.maxHp and w.grace[pd.key]==nil,"dodge: no damage, no grace")
end

-- 7. D: never-targeting rules (protected, dead, inactive, safe meadow, grace) + combat-level backstop
do
  local cases={
    {"protected",{protectedUntil=1e9}},{"dead",{alive=false}},{"inactive",{active=false}},
  }
  for _,case in cases do
    local w,cw,n=setup(4)
    local pd=joinP(cw,1,"r"); local pl=P(pd.key,OX+4,OZ,case[2])
    local t,bites=0,0
    while t<30 do t+=DT; local evs=Npc.step(w,t,DT,{pl}); bites+=#evs; assert(n.state~="alert" and n.state~="chase" and n.state~="windup" and n.state~="bite","ignored: "..case[1]) end
    assert(bites==0 and pd.state.hp==pd.state.maxHp,"no bite on "..case[1])
    assert(Npc.pickTarget(w,n,{pl},t,100)==nil)
  end
  -- safe meadow: a player inside it is invisible to NPCs even right next to the edge
  local w=Npc.newWorld(true,9,terrain(),{kinematic=true}); local n={x=0,z=30+90,y=0,s=1}
  local inside=P("s",0,30+60); local outside=P("o",0,30+85)
  assert(Npc.valid(w,inside,0)==false and Npc.valid(w,outside,0)==true,"safe zone radius")
  assert(Npc.pickTarget(w,n,{inside},0,100)==nil and Npc.pickTarget(w,n,{inside,outside},0,100)==outside)
  -- junk input is never a target
  for _,junk in {5,"x",{},{key="k"},{key="k",x=0/0,z=0,alive=true,active=true},{key="k",x=math.huge,z=0,alive=true,active=true}} do assert(Npc.valid(w,junk,0)==false) end
  -- default-deny: alive/active must be exactly true
  assert(Npc.valid(w,{key="k",x=200,z=200},0)==false,"missing flags are not eligible")
  -- grace: a just-bitten player is skipped by every NPC
  w.grace["g"]=50; assert(Npc.canBite(w,P("g",200,200),10)==false and Npc.canBite(w,P("g",200,200),50)==true)
  -- the performBite candidate filter drops ineligible players even if passed in
  local w2,cw2,n2=setup(5)
  local pd2=R.join(cw2,{userId=2,runId="r",class="Ground",score=0,now=0,protectedUntil=999})
  local pl2=P(pd2.key,OX+2,OZ+0.1,{protectedUntil=0})
  local res2=Npc.performBite(w2,cw2,{slot=1,npcKey=n2.key},11,{pl2}); assert(res2.ok==false,"combat world protects spawn-protected players too")
end

-- 8. E: leash from the middle of a chase, and safe-meadow edge is never entered
do
  local w,cw,n=setup(6)
  local pd=joinP(cw,1,"r"); local pl=P(pd.key,OX+20,OZ)
  n.state="chase"; n.targetKey=pd.key; n.chaseStartedAt=0; n.homeX=OX-NC.LeashRadius-5
  Npc.step(w,0.2,DT,{pl}); assert(n.state=="retreat","beyond the leash -> retreat")
  -- fuzz walk near the meadow edge: kinematic NPC never steps inside
  local w3=Npc.newWorld(true,7,terrain(),{kinematic=true}); Npc.populate(w3,0,{P("far",-399,399)})
  local n3=w3.slots[1]; n3.x,n3.z,n3.homeX,n3.homeZ=0,30+NC.SafeRadius+10,0,30+NC.SafeRadius+10; n3.y=Layout.height(n3.x,n3.z); n3.lastX,n3.lastZ=n3.x,n3.z
  local pl3=P("a",0,30+NC.SafeRadius+1) -- valid (just outside)
  for i=1,200 do Npc.step(w3,i*DT,DT,{pl3}); assert(not Npc.inSafeZone(n3.x,n3.z),"NPC never enters the start meadow") end
end

-- 9. F: defeat by a team, exactly once, capped assist bonus, no eggs, respawn after the delay away from players
do
  local w,cw,n=setup(8)
  local smalls={} for i=1,4 do smalls[i]=joinP(cw,i,"s"..i) end
  local cand={{key=n.key,pos={X=n.x,Y=n.y,Z=n.z}}}
  cw.onDefeat=function(v,a,bo)
    cw.defeatCount+=1; cw.bonuses[v.key]=bo
    assert(R.settle(cw,v.key)); assert(Npc.defeated(w,n.slot,cw.now)==n,"slot freed")
  end
  local t=1
  local fwd={X=1,Y=0,Z=0}
  while cw.defeatCount==0 and t<200 do
    t+=0.5
    cw.now=t
    for i,s in smalls do local pos={X=n.x-3,Y=n.y,Z=n.z+(i-2)*0.2}; R.attack(cw,s.key,t+i*0.01,pos,fwd,cand) end
  end
  assert(cw.defeatCount==1,"NPC defeated exactly once")
  assert(n.s>=1 and R.get(cw,n.key).state.phase=="Settled","settled once")
  local bo=cw.bonuses[n.key]; local total=0
  for k,a in bo do assert(a==math.floor(a) and a>0 and cw.dinos[k]); total+=a end
  assert(total<=math.floor(n.score*M.CombatConfig.TeamUp.BonusCapFraction),"assist bonus capped at 25% of the NPC score: "..total)
  assert(total>0 and total<=100,"small, capped growth only (no eggs, no catches)")
  assert(R.settle(cw,n.key)==false and Npc.defeated(w,n.slot,t)==nil,"never twice")
  -- respawn: not before the delay, then somewhere new, away from the players
  local players={P("far",-399,399),P("2|x",OX,OZ)}
end
do
  local w=Npc.newWorld(true,11,terrain(),{kinematic=true})
  local players={P("far",-399,399),P("b",-100,-200)}
  local o1=Npc.populate(w,0,players); local first=o1.spawned[1]; assert(first)
  local gone=Npc.defeated(w,first.slot,100); assert(gone==first and w.slots[first.slot]==nil)
  assert(#Npc.populate(w,100+NC.RespawnSeconds-0.5,players).spawned==0,"no respawn before "..NC.RespawnSeconds.." s")
  local later=Npc.populate(w,100+NC.RespawnSeconds+NC.RespawnJitter+0.1,players)
  local back=false
  for _,n in later.spawned do if n.slot==first.slot then back=true; assert(n.key~=first.key and n.serial>first.serial,"fresh run id")
    for _,p in players do assert(math.sqrt((p.x-n.x)^2+(p.z-n.z)^2)>=NC.SpawnMinPlayerDistance,"respawn away from players") end end end
  assert(back,"respawned after the delay")
  assert(Npc.count(w)<=NC.MaxNpcs)
  -- players leave: calm NPCs are removed, count follows the wanted count, nothing respawns for nobody
  local gone2=Npc.populate(w,500,{}); assert(Npc.count(w)==0 and #gone2.removed>=1 and #Npc.populate(w,900,{}).spawned==0)
end

-- 10. never one-shot across every class and size, with NPC scores at both ends
do
  local worst=0
  for _,class in {"Ground","Fly","Water","Armored"} do
    for _,score in {0,10,100,1500,8000,25500} do
      for _,ns in {NC.ScoreMin,NC.ScoreMax} do
        for _,sp in NC.Species do
          local npc={class=R.classForSpecies(sp),s=M.CombatStats.scale(ns)}
          local f=Npc.biteFraction(npc,class,score); worst=math.max(worst,f)
          assert(f<=0.20,"one NPC bite takes at most 20% of max HP, got "..f.." for "..class.." score "..score)
        end
      end
    end
  end
  assert(worst>0)
end

-- 11. sleeping NPCs do nothing; wake calm
do
  local w,cw,n=setup(12)
  local far=P("far",OX+400,OZ+390); local bx,bz=n.x,n.z
  for i=1,100 do Npc.step(w,i*DT,DT,{far}); assert(n.x==bx and n.z==bz and n.moving==false and n.state=="patrol") end
  assert(n.sleeping==true)
  Npc.step(w,30,DT,{P("near",OX+60,OZ)}); assert(n.sleeping==false)
end

-- 12. determinism: same seed + same inputs -> identical run; different seed differs
local function trace(seed)
  local w=Npc.newWorld(true,seed,terrain(),{kinematic=true}); local cw=R.new(true)
  local pl={P("a",100,100),P("b",-250,-100)}; local out={}
  for i=1,600 do
    local t=i*DT
    local pop=Npc.populate(w,t,pl); for _,n in pop.spawned do Npc.joinCombat(w,cw,n,t) end
    local evs=Npc.step(w,t,DT,pl)
    for _,ev in evs do table.insert(out,"B"..ev.targetKey..t) end
    if i%25==0 then for s=1,NC.MaxNpcs do local n=w.slots[s]; if n then table.insert(out,string.format("%d:%s:%.3f:%.3f:%s",s,n.species,n.x,n.z,n.state)) end end end
    pl[1]=P("a",100+i*0.3,100+math.sin(i/10)*30)
  end
  return table.concat(out,"|")
end
local t1,t2,t3=trace(77),trace(77),trace(78)
assert(t1==t2 and #t1>100,"seeded run is deterministic")
assert(t1~=t3,"a different seed differs")

-- 13. fuzz: 12 players, hard cap, never bite an ineligible player, exactly-once defeat, bounds, leash, no water/meadow
local hitsTotal,defeatsTotal,npcDefeats=0,0,0
for seed=1,3 do
  local rngs=seed*9301
  local function rnd() rngs=(rngs*1103515245+12345)%2147483648; return rngs/2147483648 end
  local w=Npc.newWorld(true,seed,terrain(),{kinematic=true})
  local cw=R.new(true); local npcDefeated={}
  cw.onDefeat=function(v,a,bo)
    assert(R.settle(cw,v.key))
    if string.sub(v.userId,1,3)=="npc" then
      assert(not npcDefeated[v.key],"NPC defeated once"); npcDefeated[v.key]=true; npcDefeats+=1
      local slot=tonumber(string.sub(v.userId,4)); Npc.defeated(w,slot,cw.now)
    else
      defeatsTotal+=1
      -- a defeated player leaves the run
    end
  end
  local people={}
  for i=1,12 do
    local x,z=(rnd()-0.5)*700,(rnd()-0.5)*700
    local d=R.join(cw,{userId=i,runId="r",class=({"Ground","Fly","Water","Armored"})[i%4+1],score=rnd()*3000,now=0})
    people[i]={d=d,x=x,z=z,wx=(rnd()-0.5)*700,wz=(rnd()-0.5)*700,speed=(i%3==0) and 0 or 22,prot=(i%5==0) and 60 or 0}
  end
  local joined={}
  for step=1,3000 do
    local t=step*DT; cw.now=t
    local players={}
    for i,p in people do
      if p.speed>0 then
        local dx,dz=p.wx-p.x,p.wz-p.z; local m=math.sqrt(dx*dx+dz*dz)
        if m<5 then p.wx,p.wz=(rnd()-0.5)*700,(rnd()-0.5)*700 else p.x+=dx/m*p.speed*DT; p.z+=dz/m*p.speed*DT end
      end
      table.insert(players,P(p.d.key,p.x,p.z,{alive=p.d.state.phase=="Alive",active=p.d.state.phase=="Alive",protectedUntil=p.prot}))
    end
    if step%40==0 then -- curious players wander over to an NPC (and sometimes get chased)
      local pick=people[1+math.floor(rnd()*12)]
      for _,n in w.slots do if rnd()<0.5 then pick.wx,pick.wz=n.x+10,n.z; if pick.speed==0 then pick.x,pick.z=n.x+14,n.z end break end end
    end
    local pop=Npc.populate(w,t,players)
    for _,n in pop.removed do R.leave(cw,n.key); joined[n.key]=nil end
    for _,n in pop.spawned do Npc.joinCombat(w,cw,n,t); joined[n.key]=n end
    assert(Npc.count(w)<=NC.MaxNpcs,"hard cap")
    local evs=Npc.step(w,t,DT,players)
    for _,ev in evs do
      local res=Npc.performBite(w,cw,ev,t,players)
      if res.ok then
        hitsTotal+=1
        local victim; for _,p in players do if p.key==res.targetKey then victim=p end end
        assert(victim and victim.alive and victim.active and t>=victim.protectedUntil and not Npc.inSafeZone(victim.x,victim.z),"NPC bit an ineligible player")
        assert(res.damage/ cw.dinos[res.targetKey].state.maxHp<=0.25,"never one-shot")
      end
    end
    -- some players fight back at NPCs in reach
    for i,p in people do
      if p.d.state.phase=="Alive" and step%3==i%3 then
        for _,n in w.slots do
          if joined[n.key] and math.sqrt((n.x-p.x)^2+(n.z-p.z)^2)<4 then
            R.attack(cw,p.d.key,t,{X=p.x,Y=0,Z=p.z},{X=n.x-p.x,Y=0,Z=n.z-p.z},{{key=n.key,pos={X=n.x,Y=0,Z=n.z}}}); break
          end
        end
      end
    end
    R.tick(cw,t,DT)
    for _,n in w.slots do
      assert(not Npc.inSafeZone(n.x,n.z) and not Layout.inPool(n.x,n.z,4),"NPC in the meadow or water")
      assert(math.sqrt((n.x-n.homeX)^2+(n.z-n.homeZ)^2)<=NC.LeashRadius+NC.ChaseSpeed*DT+1,"leash")
      local d=cw.dinos[n.key]; assert(d and d.state.hp>=0 and d.state.hp<=d.state.maxHp+1e-9)
    end
  end
end
assert(hitsTotal>=1,"fuzz produced NPC bites")
-- 12. BD-312: the DRAWN NPC is at most about 1.3x an average player dino; defeat fade and bob are tiny and Reduce-Motion aware
for seed=1,40 do
  local w=Npc.newWorld(true,seed,terrain()); Npc.populate(w,0,{P("p",150,-100)})
  for _,n in w.slots do
    assert(n.visualScale>=NC.VisualScaleMin-1e-9 and n.visualScale<=1.3+1e-9,"NPC visual scale <= 1.3x: "..n.visualScale)
    assert(math.abs(n.radius-NC.RadiusPerVisual*n.visualScale)<1e-9 and n.radius>0)
  end
end
assert(NC.VisualScaleMax<=1.3 and NC.FadeSeconds==0.6 and NC.FadeSecondsReduced==0.15)
assert(Npc.fadeSeconds(false)==0.6 and Npc.fadeSeconds(true)==0.15)
assert(Npc.bobOffset(1.3,1,true)==0 and Npc.bobOffset(1.3,0,false)~=0 and math.abs(Npc.bobOffset(1.57,1,false))<=0.2+1e-9)
assert(math.abs(Npc.bobOffset(1.57,0/0,false))<=0.04+1e-9,"junk speed is safe")

-- 13. BD-311 + NPC reach: a chasing NPC bites a player at body-surface distance (radius-aware), still dodgeable
do
  local w,cw,n=setup(3)
  local pd=joinP(cw,1,"r"); local pl=P(pd.key,OX,OZ-(NC.AggroRange-6)); pl.radius=1.6
  local players={pl}
  local bites=0
  local t=0
  while t<40 do
    t+=DT
    for _,ev in Npc.step(w,t,DT,players) do
      local r=Npc.performBite(w,cw,ev,t,players)
      if r.ok then bites+=1 end
    end
    if bites>0 then break end
  end
  assert(bites>=1,"the NPC lands a bite on a player using radius-aware reach")
end

-- 14. BD-313: NPC defeat growth is small, capped, once per slot per 120 s per player, and few per 5 minutes
do
  assert(NC.RewardCapFraction==0.05 and NC.RewardSlotCooldownSeconds==120 and NC.RespawnSeconds>=45)
  local lim=Npc.newRewardLimiter()
  local function hit(id,dmg) return {id=id,damage=dmg} end
  local users={a=1,b=2,c=3}
  -- one killer: exactly 5% of their own growth, floored
  local r=Npc.growthRewards(lim,"npc1",{hit("a",100)},{a=500},users,0); assert(r.a==25,"5% of 500 = 25, got "..tostring(r.a))
  -- the same slot cannot pay the same player again for 120 s
  assert(next(Npc.growthRewards(lim,"npc1",{hit("a",100)},{a=500},users,119.9))==nil,"slot cooldown")
  assert(Npc.growthRewards(lim,"npc1",{hit("a",100)},{a=500},users,120.1).a==25,"pays again after 120 s")
  -- another slot is a different cooldown but the per-window cap (3 per 300 s) still applies: 2 paid so far
  assert(Npc.growthRewards(lim,"npc2",{hit("a",100)},{a=500},users,121).a==25)
  assert(next(Npc.growthRewards(lim,"npc3",{hit("a",100)},{a=500},users,122))==nil,"4th reward inside 300 s refused")
  assert(Npc.growthRewards(lim,"npc3",{hit("a",100)},{a=500},users,121+NC.RewardWindowSeconds).a==25,"window slides")
  -- damage share split; each killer capped by THEIR growth; never more than 5% of anyone's growth
  local lim2=Npc.newRewardLimiter()
  local r2=Npc.growthRewards(lim2,"npc1",{hit("a",75),hit("b",25)},{a=1000,b=200},users,0)
  assert(r2.a==37 and r2.b==2,"share x 5% of own growth: "..tostring(r2.a).."/"..tostring(r2.b))
  for k,v in r2 do assert(v<=math.floor(({a=1000,b=200})[k]*NC.RewardCapFraction)) end
  -- tiny growth or no damage pays nothing; junk is safe
  assert(next(Npc.growthRewards(Npc.newRewardLimiter(),"npc1",{hit("a",50)},{a=10},users,0))==nil)
  assert(next(Npc.growthRewards(Npc.newRewardLimiter(),"npc1",{},{},users,0))==nil)
  assert(next(Npc.growthRewards(Npc.newRewardLimiter(),"npc1",{hit("a",0/0)},{a=1e9},users,0))==nil)
  -- a farmer killing slot after slot for 30 minutes (one kill every 50 s) gets few rewards, far below the old loop
  local lim3=Npc.newRewardLimiter(); local paid,total=0,0
  for k=0,35 do
    local got=Npc.growthRewards(lim3,"npc"..(k%2+1),{hit("a",100)},{a=500},users,k*50)
    if got.a then paid+=1 total+=got.a end
  end
  assert(paid<=3*(1800/NC.RewardWindowSeconds)+3 and total<=25*paid,"farming loop is limited: "..paid.." rewards")
  for _,v in r2 do assert(type(v)=="number" and v==math.floor(v)) end
end
print(string.format("NPC predator rules passed: flag-off identity, cap %d (12 players -> %d), spawn rules over 40 seeds in %d biomes, state machine + dodge + flee + leash, grace/cooldown/bite cap, never-target matrix, exactly-once defeat, capped assist, respawn %ds, never-one-shot, sleeping, determinism, fuzz %d NPC hits %d npc defeats", NC.MaxNpcs, Npc.desiredCount(12), nb, NC.RespawnSeconds, hitsTotal, npcDefeats))
'''


def static_checks():
    errors = []
    read = lambda p: (ROOT / p).read_text(encoding='utf-8')
    if not re.search(r'^\s*CombatEnabled = false,', read('src/shared/Config.luau'), re.M):
        errors.append('Config.CombatEnabled must stay false (BD-252 gate)')
    svc = read('src/server/NpcPredatorService.luau')
    if 'if not Config.CombatEnabled' not in svc or 'return' not in svc.split('if not Config.CombatEnabled', 1)[1][:120]:
        errors.append('NpcPredatorService.start must return first while Config.CombatEnabled is false')
    if 'Config.NpcPredatorsEnabled' not in svc:
        errors.append('NpcPredatorService must also honour Config.NpcPredatorsEnabled')
    if not re.search(r'^\s*NpcPredatorsEnabled = true,', read('src/shared/Config.luau'), re.M):
        errors.append('Config.NpcPredatorsEnabled must exist (only effective with CombatEnabled)')
    for bad in ('commitRunSettlement', 'CatchScore', 'RunEggEvents', 'tryEnd', 'addGrowth'):
        if bad in svc:
            errors.append('NpcPredatorService must not touch eggs/settlement/growth directly: ' + bad)
    for needle in ('Rules.step', 'Rules.performBite', 'Rules.populate', 'SetNetworkOwner(nil)', 'BeDinoNpcs'):
        if needle not in svc.replace('Npc.', 'Rules.'):
            errors.append('NpcPredatorService is missing ' + needle)
    combat = read('src/server/CombatService.luau')
    for needle in ('addNpc', 'removeNpc', 'onNpcDefeated', 'return api'):
        if needle not in combat:
            errors.append('CombatService must expose ' + needle)
    if 'if not Config.CombatEnabled then return end' not in combat:
        errors.append('CombatService.start must still return first with the flag off')
    boot = read('src/server/Bootstrap.server.luau')
    if 'NpcPredatorService' not in boot:
        errors.append('server bootstrap must start NpcPredatorService')
    hud = read('src/client/CombatHud.luau')
    if 'BeDinoNpcs' not in hud or 'NpcPredator' not in hud:
        errors.append('CombatHud must draw the wild bar for NPC predators')
    if 'if not Config.CombatEnabled then return end' not in hud:
        errors.append('CombatHud.attach must stay a no-op while the flag is off')
    # BD-310: a big dino's bar (player or wild) must sit above the model top (extents), not at the small-dino scale rule.
    if 'function Hud.barLift' not in hud or 'topAboveRoot + 0.8' not in hud or 'Hud.barLift(s, topAboveRoot(character))' not in hud:
        errors.append('CombatHud must lift every bar above the model top (Hud.barLift with the model top)')
    if 'bar.placedScale' not in hud or 's ~= bar.placedScale' not in hud:
        errors.append('CombatHud must re-place a bar when the dino grows (placedScale)')
    rules = re.sub(r'--[^\n]*', '', read('src/shared/NpcPredatorRules.luau'))  # code only; comments may name services
    for bad in ('game:', 'workspace', 'Instance.new', 'Players', 'RunLifecycle', 'CatchScore', 'math.random'):
        if re.search(r'(?<![A-Za-z])' + re.escape(bad) + r'(?![A-Za-z])', rules):
            errors.append('NpcPredatorRules must stay pure: found ' + bad)
    # BD-312..315: Bootstrap.client may only change the Run Complete modal (no new top-level locals; verify_combat_service counts them).
    boot = read('src/client/Bootstrap.client.luau')
    if 'Oops! Good try!' not in boot or 'Your eggs are safe!' not in boot or 'LastRunEndReason' not in boot:
        errors.append('the Run Complete modal must start with the gentle defeat copy (BD-315)')
    if 'Oops! Good try!' in re.sub(r'--[^\n]*', '', hud):
        errors.append('CombatHud must not show the defeat toast any more: it was covered by the Run Complete modal (BD-315)')
    for needle in ('CHOMP', 'KeyHint', 'AlertBubble', 'NpcMotion'):
        if needle not in hud:
            errors.append('CombatHud is missing ' + needle + ' (BD-314/BD-312)')
    if 'BITE [F]' in hud:
        errors.append('the red BITE [F] button copy must be gone (BD-314)')
    if 'NpcFading' not in svc or 'task.delay(Rules.Config.FadeSeconds' not in svc:
        errors.append('NpcPredatorService must fade a defeated NPC out before removing it (BD-312)')
    motion = read('src/client/NpcMotion.luau')
    if 'NpcFading' not in motion or 'Rules.fadeSeconds(not Theme.MotionEnabled)' not in motion:
        errors.append('NpcMotion must fade NpcFading models and honour Reduce Motion')
    if 'growthRewards' not in combat or 'api.npcRewards' not in combat:
        errors.append('CombatService must pay NPC defeats only through NpcRules.growthRewards (BD-313)')
    npc_branch = re.sub(r'--[^\n]*', '', combat.split('if api.npcs[victim.key] then', 1)[1].split('if api.onNpcDefeated', 1)[0])
    for bad in ('bonuses', 'CatchScore', 'rystal', 'RunEgg'):
        if bad in npc_branch:
            errors.append('the NPC defeat branch must not use ' + bad + ' (BD-313)')
    return errors


if __name__ == '__main__':
    errs = static_checks()
    if errs:
        for e in errs:
            print('ERROR: ' + e)
        raise SystemExit(1)
    print('NPC predator static checks passed')
    H.run(BODY, 'verify_npc_predators')
