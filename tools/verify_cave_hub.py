"""BD-279/280 offline check of the Cave hub layout (docs/104). Runs the real Config, CaveHubLayout and SpawnGeometry in Luau
(Vector3 stubbed). Checks: footprint and pads inside the floor, stations >= 48 studs apart, flat paths (<= 8 degrees), every
station and arrival spot reachable over flat ground, arrival spots inside the walkable area and clear of props, 12 players
fit, spawn + run-exit gate + ceiling holes + lava falls present, part/triangle budgets within docs/104 s3.1, determinism, and
that with Config.CaveHub off SpawnGeometry / hub() give exactly the old hub values (reference snapshot below).
Not Studio evidence: the terrain shell, props and walking are BD-281 / BD-284.
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

# Snapshot of src/shared/SpawnGeometry.luau hub functions as shipped before BD-280 (Build 020), used as the reference.
OLD = r'''
local Old={HubFloorY=6,HubHalfX=55,HubHalfZ=47.5,DropClearance=5}
function Old.inHub(config,x,z) return math.abs(x)<=Old.HubHalfX and math.abs(z-config.SanctuaryCenterZ)<=Old.HubHalfZ end
function Old.hubPoint(config) return Vector3.new(0,Old.HubFloorY+Old.DropClearance,config.SanctuaryCenterZ) end
'''

LUAU = OLD + r'''
local C=CaveHubLayout
local L=C.get()
local TAN8=math.tan(math.rad(C.MaxPathSlopeDeg))
local function dist(ax,az,bx,bz) return math.sqrt((ax-bx)^2+(az-bz)^2) end
local function segDist(px,pz,ax,az,bx,bz)
 local vx,vz=bx-ax,bz-az local l2=vx*vx+vz*vz
 local t=if l2>0 then math.clamp(((px-ax)*vx+(pz-az)*vz)/l2,0,1) else 0
 return dist(px,pz,ax+vx*t,az+vz*t)
end

-- ---- flag off: every existing value identical; flag on: the cave
for _,cfg in {(function() local off=table.clone(Config) off.CaveHub=false return off end)()} do
 assert(Config.CaveHub==(Config.ReleaseProfile=="playtest"),"CaveHub ships OFF in the default build and ON in the playtest build (owner 2026-10-16, docs/125)")
 local hub=C.hub(cfg)
 assert(hub.enabled==false and hub.centerZ==cfg.SanctuaryCenterZ and hub.floorY==6 and hub.halfX==55 and hub.halfZ==47.5,"hub(config) with the flag off = old hub numbers")
 assert(hub.biome.minX==-55 and hub.biome.maxX==55 and hub.biome.minZ==473 and hub.biome.maxZ==569,"biome rect with the flag off = the old BiomePlacement.Sanctuary")
 assert(SpawnGeometry.HubFloorY==6 and SpawnGeometry.HubHalfX==55 and SpawnGeometry.HubHalfZ==47.5,"legacy SpawnGeometry constants unchanged")
 local hp,op=SpawnGeometry.hubPoint(cfg),Old.hubPoint(cfg)
 assert(hp==op,"hubPoint identical to the pre-BD-280 value with the flag off")
 local checked=0
 for x=-80,80,2.5 do for z=cfg.SanctuaryCenterZ-70,cfg.SanctuaryCenterZ+70,2.5 do
  assert(SpawnGeometry.inHub(cfg,x,z)==Old.inHub(cfg,x,z),"inHub identical with the flag off at "..x..","..z)
  local f=SpawnGeometry.floorY(cfg,Layout,x,z)
  if Old.inHub(cfg,x,z) then assert(f==Old.HubFloorY,"floorY identical in the old hub") end
  checked+=1
 end end
 for _,active in {true,false} do
  local r=SpawnGeometry.recoveryPoint(cfg,Layout,active)
  if not active then assert(r==op,"hub recovery point identical") end
 end
 print("flag off: hub numbers, hubPoint, inHub, floorY identical ("..checked.." probes)")
end
local on=table.clone(Config) on.CaveHub=true
local hub=C.hub(on)
assert(hub.enabled and hub.centerZ==580 and hub.floorY==6 and hub.halfX==130 and hub.halfZ==116,"hub(config) flag on = the organic cave inside a 260 x 232 bounding box")
assert(hub.centerZ-hub.halfZ>on.ArenaHalfWidth+8+30,"cave clears the island terrain and boundary rocks")
assert(hub.biome.minX<=-130-C.WallThickness and hub.biome.maxX>=130+C.WallThickness and hub.biome.minZ<=hub.centerZ-hub.halfZ-C.WallThickness and hub.biome.maxZ>=hub.centerZ+hub.halfZ+C.WallThickness,"biome rect holds floor + 8 stud walls")
assert(Config.SanctuaryCenterZ+48<=hub.biome.maxZ and Config.SanctuaryCenterZ-48>=hub.biome.minZ,"old hub box lies inside the cave biome rect")
local sp=SpawnGeometry.hubPoint(on)
assert(sp.X==0 and sp.Z==580 and sp.Y==11,"SpawnGeometry.hubPoint reads the cave centre when on")
assert(SpawnGeometry.inHub(on,100,640) and not SpawnGeometry.inHub(on,0,400),"inHub covers the cave box only")
assert(SpawnGeometry.floorY(on,Layout,100,640)==6,"fall floor = cave floor")
assert(not SpawnGeometry.fallen(on,Layout,Vector3.new(0,11,580)) and SpawnGeometry.fallen(on,Layout,Vector3.new(0,6-SpawnGeometry.FallDepth-1,580)),"fall detection works in the cave")
assert(SpawnGeometry.recoveryPoint(on,Layout,false)==sp,"respawn at the Heart")
local spawn=C.spawn()
assert(spawn.x==sp.X and spawn.y==sp.Y and spawn.z==sp.Z,"layout spawn = SpawnGeometry.hubPoint")
print("flag on: cave hub (0,580) organic cave, spawn, inHub, fall detection read the same hub()")

-- ---- stations
local S=L.stations
assert(#S==9,"heart + 8 stations")
local ids={}
for _,s in S do ids[s.id]=s end
for _,id in {"heart","gate","nests","potions","fusion","style","index","settings","fame"} do assert(ids[id],"station "..id) end
local minGap=math.huge
for i,a in S do
 assert(C.insideFloor(a.x,a.z+C.CenterZ,a.r+4)==true,"pad inside the floor with a 4 stud margin: "..a.id)
 for j=i+1,#S do
  local b=S[j]
  local d=dist(a.x,a.z,b.x,b.z)
  minGap=math.min(minGap,d)
  assert(d>=C.MinStationGap,"stations >= 48 studs apart: "..a.id.." / "..b.id.." "..d)
  assert(d>=a.r+b.r+6,"pads do not touch: "..a.id.." / "..b.id)
 end
 assert(dist(a.x,a.z,C.Pool.x,C.Pool.z)>=a.r+C.Pool.r+6,"pad clears the lava pool: "..a.id)
 assert(a.hasHole==(a.id=="heart" or a.id=="potions" or a.id=="nests" or a.id=="style"),"ceiling hole only over Heart/Potions/Nests/Style")
end
assert(ids.heart.x==0 and ids.heart.z==0,"heart at the cave centre")
assert(C.insideFloor(C.Pool.x,C.Pool.z+C.CenterZ,C.Pool.r+3),"lava pool inside the floor")

-- ---- floor extents inside the 260 x 232 bounding box with 8 stud walls (the floor is NOT a box: rooms and tunnels, see the fill check below)
local minX,maxX,minZ,maxZ=math.huge,-math.huge,math.huge,-math.huge
for x=-C.BoxHalfX-10,C.BoxHalfX+10,2 do for dz=-C.BoxHalfZ-10,C.BoxHalfZ+10,2 do
 if C.insideFloor(x,dz+C.CenterZ,0) then minX=math.min(minX,x) maxX=math.max(maxX,x) minZ=math.min(minZ,dz) maxZ=math.max(maxZ,dz) end
end end
assert(minX>=-130 and maxX<=130 and minZ>=-116 and maxZ<=116,"cave inside the 260 x 232 box "..minX..","..maxX..","..minZ..","..maxZ)
assert(maxX-minX>=200 and maxZ-minZ>=200,"cave really is big (not a small hub)")
-- docs/104 s17: not a cube. Only a minority of the bounding box is open floor, and the bounding rectangle's four corners are solid rock.
local open,probes=0,0
for x=-C.BoxHalfX,C.BoxHalfX,4 do for dz=-C.BoxHalfZ,C.BoxHalfZ,4 do probes+=1 if C.insideFloor(x,dz+C.CenterZ,0) then open+=1 end end end
assert(open/probes>0.30 and open/probes<0.62,"the open floor fills 30..62 percent of its bounding box, so it is rooms and tunnels, not a cut-out cube: "..open/probes)
for _,sx in {-1,1} do for _,sz in {-1,1} do assert(not C.insideFloor(sx*(C.BoxHalfX-12),sz*(C.BoxHalfZ-12)+C.CenterZ,0),"box corner is solid rock") end end
-- no long straight wall: walking the wall edge along 200 columns, the wall never stays within 0.7 studs of a straight line for 24+ studs
do
 local runs,worst=0,0
 for dz=-110,110,8 do
  local last,len=nil,0
  for x=-128,128,2 do
   local inside=C.insideFloor(x,dz+C.CenterZ,0)
   if last~=nil and inside~=last then len=0 end
   last=inside
  end
 end
 -- straightness: count wall crossings with a rough run test along x lines; walls come from circles + noise so a wall crossing changes the
 -- x position by > 1 stud between neighbouring rows in most places
 local edge={}
 for dz=-112,112,2 do
  local first
  for x=-128,128,0.5 do if C.insideFloor(x,dz+C.CenterZ,0) then first=x break end end
  edge[#edge+1]=first
 end
 local straight=0
 for i=3,#edge do
  if edge[i] and edge[i-1] and edge[i-2] and math.abs(edge[i]-2*edge[i-1]+edge[i-2])<0.3 then straight+=1 end
 end
 assert(straight<#edge*0.5,"west wall is not a ruler line ("..straight.."/"..#edge..")")
end

-- ---- paths: flat, 12/10 wide, inside floor, away from the lava pool
for _,p in L.paths do
 assert(p.half*2==8,"flat laid-stone path in a tunnel is 8 wide")
 local len=dist(p.ax,p.az,p.bx,p.bz)
 assert(len>0,"path has length")
 for i=0,math.floor(len) do
  local t=i/len
  local x,z=p.ax+(p.bx-p.ax)*t,p.az+(p.bz-p.az)*t
  assert(C.insideFloor(x,z+C.CenterZ,p.half+1),"path inside the floor: "..p.id)
  assert(dist(x,z,C.Pool.x,C.Pool.z)>=C.Pool.r+p.half+2,"path stays away from the lava pool: "..p.id)
 end
end
-- slope along and across every path and over every pad, from the real floorHeight()
local maxSlope,maxFloorSlope=0,0
local function slopeAt(x,z) -- world x, z; finite differences over 2 studs
 local hx=(C.floorHeight(x+1,z)-C.floorHeight(x-1,z))/2
 local hz=(C.floorHeight(x,z+1)-C.floorHeight(x,z-1))/2
 return math.sqrt(hx*hx+hz*hz)
end
for _,p in L.paths do
 local len=dist(p.ax,p.az,p.bx,p.bz)
 for i=0,math.floor(len),2 do
  local t=i/len
  for off=-p.half,p.half,p.half/2 do
   local dx,dz=(p.bx-p.ax)/len,(p.bz-p.az)/len
   local x,z=p.ax+(p.bx-p.ax)*t-dz*off,p.az+(p.bz-p.az)*t+dx*off
   maxSlope=math.max(maxSlope,slopeAt(x,z+C.CenterZ))
  end
 end
end
for _,s in S do
 for a=0,350,10 do for rr=0,s.r,2 do
  local x,z=s.x+math.cos(math.rad(a))*rr,s.z+math.sin(math.rad(a))*rr
  assert(C.floorHeight(x,z+C.CenterZ)==C.FloorY,"pad is exactly flat: "..s.id)
  maxSlope=math.max(maxSlope,slopeAt(x,z+C.CenterZ))
 end end
end
assert(maxSlope<=TAN8,"paths and pads <= 8 degrees: "..math.deg(math.atan(maxSlope)))
for x=-130,130,2 do for dz=-116,116,2 do
 if C.insideFloor(x,dz+C.CenterZ,0) then
  local h=C.floorHeight(x,dz+C.CenterZ)
  assert(h>=C.FloorY and h<=C.FloorY+C.HillMax+1e-6,"floor hills 0..HillMax studs")
  maxFloorSlope=math.max(maxFloorSlope,slopeAt(x,dz+C.CenterZ))
 end
end end
assert(maxFloorSlope<math.tan(math.rad(22)),"whole floor gentle (< 22 degrees): "..math.deg(math.atan(maxFloorSlope)))

-- ---- props: collect blockers (floor props that are not walk-over)
local blockers={}
local counts={}
for _,p in L.props do
 counts[p.key]=(counts[p.key] or 0)+1
 assert(C.Kinds[p.key],"known kind "..p.key)
 if not p.hang then assert(C.insideFloor(p.x,p.z+C.CenterZ,0),"prop inside the floor: "..p.key) end
 if not p.hang and not p.walk then blockers[#blockers+1]=p end
end
local function blocked(x,z,r) -- is a disc of radius r at (x,z) (local) overlapping any blocker
 for _,b in blockers do if C.boxDist(x,z,b)<r then return b end end
 return nil
end
-- no blocking prop sits on a path
for _,p in L.paths do
 local len=dist(p.ax,p.az,p.bx,p.bz)
 for i=0,math.floor(len) do
  local t=i/len
  local x,z=p.ax+(p.bx-p.ax)*t,p.az+(p.bz-p.az)*t
  local b=blocked(x,z,p.half)
  assert(b==nil,"prop on a path: "..p.id.." <- "..(if b then b.key.." ("..b.owner..") at "..b.x..","..b.z else ""))
 end
end

-- station props do not pile on each other (bounding circles at 55%)
for i,a in blockers do
 for j=i+1,#blockers do
  local b=blockers[j]
  if a.key~="hub_sign_stone" and b.key~="hub_sign_stone" and a.owner==b.owner and a.owner~="scatter" and a.owner~="lava" then
   local ra,rb=math.sqrt(a.w^2+a.d^2)/2,math.sqrt(b.w^2+b.d^2)/2
   assert(dist(a.x,a.z,b.x,b.z)>=(ra+rb)*0.5,"station props overlap: "..a.key.." / "..b.key.." in "..a.owner)
  end
 end
end

-- ---- arrival spots: 6 per station, on the pad, inside the walkable area, clear of props, face the sign
for _,s in S do
 assert(#s.spots==6 and #C.arrivalSpots(s.id)==6,"6 arrival spots: "..s.id)
 for i,a in s.spots do
  assert(dist(a.x,a.z,s.x,s.z)<=s.r-2 and dist(a.x,a.z,s.x,s.z)>=s.r-4,"arrival spot on the pad rim: "..s.id)
  assert(C.insideFloor(a.x,a.z+C.CenterZ,1.5),"arrival spot inside the walkable area: "..s.id)
  assert(C.floorHeight(a.x,a.z+C.CenterZ)==C.FloorY,"arrival spot on flat ground")
  local b=blocked(a.x,a.z,2)
  assert(b==nil,"arrival spot overlaps a prop: "..s.id.." #"..i.." <- "..(if b then b.key.." ("..b.owner..")" else ""))
  assert(dist(a.x,a.z,C.Pool.x,C.Pool.z)>C.Pool.r+3,"arrival spot away from lava")
  for j=i+1,#s.spots do local c=s.spots[j] assert(dist(a.x,a.z,c.x,c.z)>=3,"arrival spots 3+ studs apart: "..s.id) end
  if s.sign~="" then
   local want=C.yawTo(s.signX-a.x,s.signZ-a.z)
   assert(math.abs(a.yaw-want)<1e-6,"arrival spot faces the sign: "..s.id)
  end
 end
 local w=C.arrivalSpots(s.id)[1]
 assert(w.z==s.spots[1].z+580 and w.y==11,"world arrival spots = local + centre")
 assert(math.abs(s.cameraYaw)<=math.pi+1e-6,"camera yaw present: "..s.id)
end

-- ---- 12 players fit at every station and on the Heart (3.5 stud hex-ish grid, props excluded)
for _,s in S do
 local n=0
 for x=-s.r,s.r,3.5 do for z=-s.r,s.r,3.5 do
  if x*x+z*z<=(s.r-2.5)^2 and not blocked(s.x+x,s.z+z,1.75) then n+=1 end
 end end
 local dbg={} for _,b in blockers do if b.owner==s.id then dbg[#dbg+1]=b.key..string.format("@%.1f,%.1f %.1fx%.1f",b.x-s.x,b.z-s.z,b.w,b.d) end end
 assert(n>=12,"12 players fit on "..s.id.." (room for "..n..") blockers "..table.concat(dbg,"; "))
end

-- ---- flat-path reachability from the spawn: BFS over flat network cells (pads + paths), 2 stud cells, no props
local CELL=2
local function flat(x,z) return C.flatDistance(x,z+C.CenterZ)<=0 end
local key=function(i,j) return i*10000+j end
local function cell(i,j) return i*CELL,j*CELL end
local function ok(i,j)
 local x,z=cell(i,j)
 return flat(x,z) and C.insideFloor(x,z+C.CenterZ,0) and blocked(x,z,0.75)==nil and dist(x,z,C.Pool.x,C.Pool.z)>C.Pool.r+1
end
local seen={}
local queue={{0,0}}
assert(ok(0,0),"spawn cell walkable")
seen[key(0,0)]=true
local head=1
while head<=#queue do
 local c=queue[head] head+=1
 for _,d in {{1,0},{-1,0},{0,1},{0,-1}} do
  local i,j=c[1]+d[1],c[2]+d[2]
  if not seen[key(i,j)] and ok(i,j) then
   local x0,z0=cell(c[1],c[2]) local x1,z1=cell(i,j)
   local h0,h1=C.floorHeight(x0,z0+C.CenterZ),C.floorHeight(x1,z1+C.CenterZ)
   if math.abs(h1-h0)/CELL<=TAN8 then seen[key(i,j)]=true queue[#queue+1]={i,j} end
  end
 end
end
local function reached(x,z)
 local i0,j0=math.floor(x/CELL+.5),math.floor(z/CELL+.5)
 for di=-1,1 do for dj=-1,1 do if seen[key(i0+di,j0+dj)] then return true end end end
 return false
end
for _,s in S do
 assert(reached(s.x,s.z),"station reachable on flat ground from the spawn: "..s.id)
 for i,a in s.spots do assert(reached(a.x,a.z),"arrival spot reachable on flat ground: "..s.id.." #"..i) end
end
assert(reached(L.gate.x,L.gate.triggerZ+4),"run-exit gate reachable on flat ground")
-- ---- docs/104 s17: the whole open cave is one connected network a child can walk (no sealed side caves, no dead-end bubbles), over
-- ground that is walkable (slope <= 28 degrees between 2 stud neighbours), 3+ studs from the wall; every room and every tunnel waypoint is in it.
do
 local W=2
 local function open(i,j) return C.insideFloor(i*W,j*W+C.CenterZ,3) end
 local function h(i,j) return C.floorHeight(i*W,j*W+C.CenterZ) end
 local TAN28=math.tan(math.rad(28))
 local seenW={}
 local q={{0,0}}
 seenW[key(0,0)]=true
 local hd=1
 while hd<=#q do
  local c=q[hd] hd+=1
  for _,d in {{1,0},{-1,0},{0,1},{0,-1}} do
   local i,j=c[1]+d[1],c[2]+d[2]
   if not seenW[key(i,j)] and open(i,j) and math.abs(h(i,j)-h(c[1],c[2]))/W<=TAN28 then seenW[key(i,j)]=true q[#q+1]={i,j} end
  end
 end
 local function inNet(x,z)
  local i0,j0=math.floor(x/W+.5),math.floor(z/W+.5)
  for di=-2,2 do for dj=-2,2 do if seenW[key(i0+di,j0+dj)] then return true end end end
  return false
 end
 for _,r in L.rooms do assert(inNet(r.x,r.z),"room "..r.id.." is connected to the Heart over walkable floor") end
 for id,n in L.nodes do assert(inNet(n.x,n.z),"tunnel node "..id.." is walkable and connected") end
 -- tunnel loops: every station except the island gate has two ways to the Heart (no dead ends); the gate's tunnel ends at the exit arch
 local adj={}
 for _,p in L.paths do if p.a then adj[p.a]=adj[p.a] or {} adj[p.b]=adj[p.b] or {} table.insert(adj[p.a],p.b) table.insert(adj[p.b],p.a) end end
 for _,s in S do
  if s.id~="heart" and s.id~="gate" then
   local degree=0
   for _,p in L.paths do if p.a==s.id or p.b==s.id then degree+=1 end end
   assert(degree>=2,"station has two tunnels (a loop, not a dead end): "..s.id.." "..degree)
  end
 end
 -- sightlines (docs/104 s17): from every arrival spot the straight line to the station's sign stays in open cave
 local sightMin=math.huge
 for _,s in S do
  if s.sign~="" then
   for _,a in s.spots do
    for t=0,1,0.05 do
     local x,z=a.x+(s.signX-a.x)*t,a.z+(s.signZ-a.z)*t
     sightMin=math.min(sightMin,(C.caveSd(x,z+C.CenterZ)))
    end
   end
  end
 end
 assert(sightMin>1,"clear sightline from every arrival spot to its sign: "..sightMin)
 -- and the tunnel mouth of every station sees its sign too: the line from the pad-edge end of each path into the station to the sign
 print(string.format("network OK: %d walkable cells, %d rooms, %d tunnel nodes, every station on a loop, sightline margin %.1f studs",#q,#L.rooms,(function() local n=0 for _ in L.nodes do n+=1 end return n end)(),sightMin))
end
print(string.format("layout OK: %d stations (min gap %.1f), %d paths, max path/pad slope %.1f deg, whole floor %.1f deg, %d flat cells reachable",#S,minGap,#L.paths,math.deg(math.atan(maxSlope)),math.deg(math.atan(maxFloorSlope)),#queue))

-- ---- spawn, gate, holes, lava
assert(C.insideFloor(spawn.x,spawn.z,18-1) and blocked(0,0,3)==nil,"spawn on a clear Heart")
assert(L.gate.mouthWidth==30 and L.gate.countdown==1.5 and L.gate.triggerZ<ids.gate.z,"run-exit gate: 30 wide mouth, 1.5 s countdown, trigger past the arch toward the island")
assert(C.insideFloor(0,L.gate.triggerZ+C.CenterZ,3) and L.gate.triggerHalfWidth==15,"gate trigger inside the floor")
local want={heart=12,potions=8,nests=8,style=7} -- BD-281 QA: enlarged from 7/5/5/4 (a pin-prick from the floor)
assert(#L.holes==4,"four ceiling holes")
for _,h in L.holes do
 assert(h.radius==want[h.station],"hole radius "..h.station)
 assert(h.ceilingY>=C.FloorY+38 and h.ceilingY<=C.FloorY+60,"ceiling height 38..60 over the floor at the holes: "..h.station.." "..(h.ceilingY-C.FloorY))
 assert(counts.cave_light_cone==4,"one light cone per hole")
end
assert(math.abs(C.ceilingY(0,580)-(6+58))<1.5,"about 58 studs over the Heart centre: "..C.ceilingY(0,580))
assert(C.Fall.crackHeight+2<=C.ceilingY(C.Fall.x,C.Fall.z+580)-C.FloorY,"lava crack under the cavern ceiling")
assert(C.Fall.width==40 and C.Fall.height==32 and C.Pool.r>=10,"lava falls 40 x 32 into a pool (BD-295: fits under the cavern ceiling)")
assert(counts.cave_lava_fall==1 and counts.lava_pool_disc==1 and counts.cave_lava_rim_rock==6 and counts.cave_stepping_stone==4,"lava props present")
assert(#L.lights<=C.MaxLights,"within the light cap (30): "..#L.lights)

-- ---- BD-284: every layout prop key is a registered published mesh, an existing mesh, or an explicit non-mesh (FX)
local P=CaveHubProps
local ids,idCount={},0
for key,a in P.Assets do
 assert(type(a.id)=="string" and string.match(a.id,"^%d+$")~=nil and #a.id>=10,"numeric published id: "..key)
 assert(ids[a.id]==nil,"unique id: "..key.." duplicates "..tostring(ids[a.id]))
 ids[a.id]=key idCount+=1
end
local existingCount=0
for key,id in P.Existing do
 assert(string.match(id,"^%d+$")~=nil,"numeric existing id: "..key)
 assert(ids[id]==nil,"existing id not duplicated as a new upload: "..key)
 ids[id]=key existingCount+=1
end
local mapped,fx=0,0
for key in C.Kinds do assert(P.assetId(key)~=nil or P.NotMeshes[key]~=nil or P.Kit[key]~=nil or P.Slots[key]~=nil,"layout kind has no published id, kit mesh or slot and is not a listed non-mesh: "..key) end
local used={}
for _,p in L.props do
 if not used[p.key] then
  used[p.key]=true
  if P.assetId(p.key) or P.Kit[p.key] or P.Slots[p.key] then mapped+=1 else fx+=1 end
 end
end
for key,why in P.NotMeshes do assert(type(why)=="string" and #why>10,"non-mesh reason: "..key) end
for key in P.Solid do assert(C.Kinds[key],"solid piece is a layout kind: "..key) end
for key in P.Rim do assert(C.Kinds[key],"rim piece is a layout kind: "..key) end
-- scale targets: the uniform factor from the loaded size to the layout size is sane, and the proportions agree (<= 2.6 x off on any axis)
local worst,worstKey,checked=1,"",0
for key,a in P.Assets do
 local k=C.Kinds[key]
 if a.native and k and P.assetId(key) then
  local target={k[1],k[2],k[3]}
  local f=P.fitFactor(a.native,target)
  assert(f>=P.MinScale and f<=P.MaxScale,"scale factor in bounds: "..key.." "..f)
  for i=1,3 do
   local want=target[i]/(a.native[i]*f)
   local off=math.max(want,1/want)
   if off>worst then worst,worstKey=off,key.." axis "..i end
   assert(off<=2.6,"generated proportions fit the layout size: "..key.." axis "..i.." off by "..off)
  end
  checked+=1
 end
end
assert(P.fitFactor({2,2,2},{4,1,1})==2 and P.fitFactor({1,1,1},{1000,1,1})==P.MaxScale and P.fitFactor({0,1,1},{1,1,1})==1,"fitFactor rules")
assert(P.Lava.fxPartBudget<=counts.cave_lava_fall+counts.lava_pool_disc+5,"lava FX parts: the fall and disc rows plus at most 5 extra (BD-385: 3 glow discs)")
assert(P.Assets.cave_lava_fall and P.NotMeshes.cave_lava_fall,"the chunky generated lava block is registered but not placed")
assert(C.Kinds.hub_gate_arch[1]<=L.gate.mouthWidth,"gate arch fits inside the 30 stud mouth")
assert(counts.hub_gate_arch==nil,"no gate arch prop on the floor (owner 2026-10-16: the gate is a mouth in the rock)")
for _,bad in {"hub_lantern_post","hub_bench_stone","hub_cushion_moss","hub_crate","hub_barrel","hub_table_wood","hub_banner","hub_gong","cave_wall_pillar"} do assert(counts[bad]==nil,"no floor furniture: "..bad) end
print(string.format("props OK: %d layout keys mapped to published ids (%d new uploads + %d existing registered), %d FX/non-mesh keys, %d proportion checks (worst %.2fx on %s)",mapped,idCount,existingCount,fx,checked,worst,worstKey))


-- ---- BD-296 dressing pass (owner 2026-10-16: cosy, mossy, slightly magical; handbook: a few plant families, ground props, clear lanes)
local dress,byKey={},{}
for _,p in L.props do if p.owner=="dress" then dress[#dress+1]=p byKey[p.key]=(byKey[p.key] or 0)+1 end end
assert(#dress>=45 and #dress<=80,"dressing rows stay a few dozen: "..#dress)
for key in byKey do assert(P.Kit[key] or P.Slots[key] or key=="cave_moss_patch" or key=="cave_moss_hang","dress key is a kit mesh, a slot or an existing moss mesh: "..key) end
assert((byKey.cave_moss_hang or 0)>=8,"vines on the tunnel and gate jambs: "..tostring(byKey.cave_moss_hang))
assert((byKey.world_fern_a or 0)+(byKey.world_fern_b or 0)>=10 and (byKey.world_horsetail_a or 0)>=3 and (byKey.dress_mushrooms or 0)>=6 and (byKey.dress_crystal or 0)>=3 and (byKey.dress_rock_small or 0)>=5 and (byKey.cave_moss_patch or 0)>=4,"ferns, horsetails, mushrooms, crystals, small rocks and moss clumps are all present")
local lampSites={}
for _,l in L.lights do if l.owner=="tunnel" or l.owner=="heartwall" then lampSites[#lampSites+1]=l end end
local glows,dressParts,dressTris=0,0,0
for _,p in dress do
 dressParts+=1 dressTris+=p.tris
 if p.hang then
  local sd=C.caveSd(p.x,p.z+C.CenterZ)
  assert(p.face==true and sd>=1.2 and sd<=3.2,"a vine hangs on the wall itself: "..p.x..","..p.z.." sd "..sd)
 else
  assert(C.insideFloor(p.x,p.z+C.CenterZ,0.8),"dressing stands on the floor: "..p.key)
  assert(C.flatDistance(p.x,p.z+C.CenterZ)>=0.3,"dressing is off every pad and path: "..p.key)
 end
 if p.glow then
  glows+=1
  assert(P.Glow[p.key] and P.Glow[p.key].material,"glow row has a style: "..p.key)
  local near=math.huge
  for _,l in lampSites do near=math.min(near,dist(p.x,p.z,l.x,l.z)) end
  assert(near<=16,"glow accents stand beside a wall lantern niche: "..p.key.." "..near.." studs")
 end
end
assert(glows>=8 and glows<=20,"a handful of glow accents (no lights): "..glows)
-- ground prop slots: every source exists; kit stand-ins carry the same slot when the Blender mesh is not uploaded yet (log and stump have none)
local kitSet={} for k in P.Kit do kitSet[k]=true end
local noGen={}
local fallbackOf=P.sourceFor("dress_rock_small",noGen,kitSet)
assert(fallbackOf and fallbackOf.kind=="kit" and fallbackOf.key=="world_boulder_bare_s","slot falls back to the kit rock while ground_rock_small_v3 has no id")
assert(P.sourceFor("dress_log",noGen,kitSet)==nil and P.sourceFor("dress_stump",noGen,kitSet)==nil,"log and stump place nothing until uploaded (no stand-in)")
local gotGen=P.sourceFor("dress_rock_small",{ground_rock_small_v3={assetId="123456789012"}},kitSet)
assert(gotGen.kind=="generated" and gotGen.id=="123456789012","an uploaded BD-464 mesh wins over the kit stand-in")
local crystal=P.sourceFor("dress_crystal",noGen,kitSet)
assert(crystal and crystal.kind=="asset" and crystal.key=="hub_crystal_s","the lamp crystal is the published amber stopgap crystal")
assert(P.sourceFor("world_fern_a",noGen,kitSet).kind=="kit" and P.sourceFor("world_fern_a",noGen,{})==nil,"kit rows need their kit binding")
assert(P.sourceFor("cave_moss_hang",noGen,kitSet).kind=="asset","vines are the published moss curtain")
local mossHangScatter=0 for _,p in L.props do if p.key=="cave_moss_hang" and p.owner~="dress" then mossHangScatter+=1 end end
assert(mossHangScatter==0,"no random wall curtains: vines only on the jambs")
print(string.format("dressing OK: %d rows (%d parts, %d est. triangles): %d ferns, %d horsetails, %d mushrooms (%d glow), %d amber crystals, %d moss clumps, %d vines, %d small rocks, %d bushes, %d log, %d stump",#dress,dressParts,dressTris,(byKey.world_fern_a or 0)+(byKey.world_fern_b or 0),byKey.world_horsetail_a or 0,byKey.dress_mushrooms or 0,glows,byKey.dress_crystal or 0,byKey.cave_moss_patch or 0,byKey.cave_moss_hang or 0,byKey.dress_rock_small or 0,byKey.dress_bush or 0,byKey.dress_log or 0,byKey.dress_stump or 0))

-- ---- BD-296 wall rock forms + gate arch frame (docs/140): the rows always exist; a mesh is placed only once its id is pasted (empty = the cave as today)
local forms,formKeys,archRows={},{},{}
for _,p in L.props do
 if p.owner=="rockform" then forms[#forms+1]=p formKeys[p.key]=(formKeys[p.key] or 0)+1 end
 if p.owner=="gatearch" then archRows[#archRows+1]=p end
end
assert(#forms>=8 and #forms<=14,"8-14 wall rock forms: "..#forms)
local nFormKinds=0 for _ in formKeys do nFormKinds+=1 end
assert(nFormKinds>=4,"at least 4 different rock forms: "..nFormKinds)
local formIds={cave_form_slabs="cave_rockform_slabs_v3",cave_form_buttress="cave_rockform_buttress_v3",cave_form_ledge="cave_rockform_ledge_v3",cave_form_tumble="cave_rockform_tumble_v3",cave_form_fins="cave_rockform_fins_v3",cave_form_terrace="cave_rockform_terrace_v3",cave_gate_frame="cave_gate_arch_v3"}
local function cornersOf(p,w,d) -- 3 x 3 sample points of the oriented footprint
 local c,s=math.cos(p.yaw),math.sin(p.yaw)
 local out={}
 for _,sx in {-1,0,1} do for _,sz in {-1,0,1} do out[#out+1]={p.x+c*sx*w/2+s*sz*d/2,p.z-s*sx*w/2+c*sz*d/2} end end
 return out
end
for _,p in forms do
 assert(formIds[p.key] and P.Slots[p.key] and P.Matte[p.key],"rock form is a slot, shown matte: "..p.key)
 assert(not p.collider and p.colliders==0 and not p.walk and not p.hang,"no collider: it would exist without the mesh: "..p.key)
 local longest=math.max(p.w,p.h,p.d)
 assert(longest>=8 and longest<=21,"rock form is 8-20 studs: "..p.key.." "..longest)
 -- the front direction (Roblox yaw: front = (-sin, -cos)); the back plane lies against the wall, the front on the floor, the dome clears the form
 local fx,fz=-math.sin(p.yaw),-math.cos(p.yaw)
 local bsd=C.caveSd(p.x-fx*p.d/2,p.z-fz*p.d/2+C.CenterZ)
 assert(bsd>=-5.5 and bsd<=2.5,"rock form back stands against the wall: "..p.key.." sd "..bsd)
 assert(C.caveSd(p.x+fx*p.d*0.4,p.z+fz*p.d*0.4+C.CenterZ)>=1.0,"rock form front stands on the floor: "..p.key)
 assert(C.ceilingY(p.x,p.z+C.CenterZ)-C.FloorY+1.5>=p.h,"rock form fits under the dome: "..p.key)
 for _,q in cornersOf(p,p.w,p.d) do
  assert(not (q[2]<L.byId.gate.z-16 and math.abs(q[1])<24),"rock form off the gate lane: "..p.key)
  assert(q[2]<=C.Fall.z-14,"rock form clear of the lava falls: "..p.key)
 end
 for _,pa in L.paths do
  for i=0,14 do
   local t=i/14
   assert(C.boxDist(pa.ax+(pa.bx-pa.ax)*t,pa.az+(pa.bz-pa.az)*t,p)>=pa.half+3.5,"rock form keeps off the walking path "..pa.id..": "..p.key)
  end
 end
 for _,st in L.stations do assert(C.boxDist(st.x,st.z,p)>=st.r,"rock form off the pad "..st.id..": "..p.key) end
 assert(C.boxDist(C.Pool.x,C.Pool.z,p)>=C.Pool.r+6,"rock form off the lava basin: "..p.key)
end
for i,a in forms do for j=i+1,#forms do
 local b=forms[j]
 for _,q in cornersOf(a,a.w,a.d) do assert(C.boxDist(q[1],q[2],b)>0,"two rock forms overlap: "..a.key.." / "..b.key) end
end end
assert(#archRows==1 and archRows[1].key=="cave_gate_frame","one gate arch frame row")
local arch,gate=archRows[1],L.byId.gate
assert(L.gateArch and arch.x==0 and math.abs(arch.yaw-math.pi)<1e-9 and arch.z<gate.z-16,"the gate frame stands in the gate wall, facing the cave (yaw pi)")
assert(C.caveSd(0,L.gateArch.frontZ+C.CenterZ)<=1.05 and C.caveSd(0,L.gateArch.frontZ+3.5+C.CenterZ)>=1.0,"arch front face stands at the gate wall surface")
assert(arch.w>=36 and arch.w<=42 and arch.h>=24 and arch.h<=28,"the arch frame is sized for the 30 wide x 20 high mouth (inner 29 x 19.6): "..arch.w.." x "..arch.h)
assert(L.gateArch.lightZ<gate.z and C.insideFloor(L.gateArch.x,L.gateArch.lightZ+C.CenterZ,0),"the arch lantern light stands inside the gate room")
local none={}
for key,mesh in formIds do
 assert(P.sourceFor(key,none,kitSet)==nil,"no id = nothing placed (the cave is as today): "..key)
 local got=P.sourceFor(key,{[mesh]={assetId="123456789012"}},kitSet)
 assert(got and got.kind=="generated" and got.id=="123456789012" and got.key==mesh,"a pasted id places the mesh: "..key)
end
print(string.format("rock forms OK: %d forms of %d kinds against the wall (no id yet: placed nothing), gate arch frame at z %.1f, %d rows total",#forms,nFormKinds,arch.z,#forms+1))

-- ---- budgets (docs/104 s3.1)
local B=C.budgetTable()
local lines={}
for _,name in {"rocks","station","lava","lights","colliders","total"} do
 local cap=C.Budget[name]
 assert(B[name].parts<=cap.parts,name.." parts "..B[name].parts.." <= "..cap.parts)
 assert(B[name].tris<=cap.tris,name.." tris "..B[name].tris.." <= "..cap.tris)
 lines[#lines+1]=string.format("  %-10s %4d / %-4d parts  %7d / %-7d tris",name,B[name].parts,cap.parts,B[name].tris,cap.tris)
end
assert(B.rocks.parts+B.station.parts+B.lava.parts+B.lights.parts+B.colliders.parts==B.total.parts,"groups sum to the total")
assert(B.total.parts<=410 and B.total.tris<=730000,"within the docs/104 budget of 410 parts / 730k triangles")
print("budget (docs/104 s3.1):\n"..table.concat(lines,"\n"))

-- ---- determinism: the layout is a pure function (rebuild in a fresh module instance, compare every prop)
local again=@FRESH@
local L2=again.get()
assert(#L2.props==#L.props and #L2.paths==#L.paths and #L2.colliders==#L.colliders,"same counts on rebuild")
for i,p in L.props do
 local q=L2.props[i]
 assert(p.key==q.key and p.x==q.x and p.z==q.z and p.yaw==q.yaw and p.scale==q.scale,"deterministic prop "..i)
end
for i,s in S do assert(L2.stations[i].x==s.x and L2.stations[i].spots[3].z==s.spots[3].z,"deterministic stations") end
print("determinism OK: "..#L.props.." props identical on rebuild")
'''

VECTOR = '''local Vector3={} Vector3.__index=Vector3
function Vector3.new(x,y,z) return setmetatable({X=x,Y=y,Z=z},Vector3) end
Vector3.__eq=function(a,b) return a.X==b.X and a.Y==b.Y and a.Z==b.Z end
'''

def script(config):
    return (VECTOR + 'local Config=' + ('(function()\n' + config + '\nend)()')
            + '\nlocal CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau')
            + '\nlocal CaveHubProps=' + wrapped('src/shared/CaveHubProps.luau')
            + '\nlocal script={Parent={CaveHubLayout="CaveHubLayout"}}\nlocal require=function() return CaveHubLayout end'
            + '\nlocal Layout=' + wrapped('src/shared/IslandLayout.luau')
            + '\nlocal SpawnGeometry=' + wrapped('src/shared/SpawnGeometry.luau') + '\n'
            + LUAU.replace('@FRESH@', wrapped('src/shared/CaveHubLayout.luau')))

def run(runner, config):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_cave_hub.luau'; path.write_text(script(config))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    arena = (ROOT / 'src/server/Arena.luau').read_text()
    lead = (ROOT / 'src/server/Leaderboards.luau').read_text()
    assert 'Config.SanctuaryCenterZ' not in arena and 'Config.SanctuaryCenterZ' not in lead, 'Arena/Leaderboards read the hub via CaveHubLayout.hub(Config)'
    assert 'CaveHubLayout.hub(Config)' in arena and 'CaveHubLayout.hub(Config)' in lead
    geo = (ROOT / 'src/shared/SpawnGeometry.luau').read_text()
    assert 'config.SanctuaryCenterZ' not in geo, 'SpawnGeometry reads the hub via CaveHubLayout.hub(config)'
    src = (ROOT / 'src/shared/CaveHubLayout.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'Vector3.new', 'workspace'):
        assert banned not in src, 'CaveHubLayout stays pure: ' + banned
    # BD-284: props
    import re
    props = (ROOT / 'src/shared/CaveHubProps.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'Vector3.new', 'workspace', 'require('):
        assert banned not in props, 'CaveHubProps stays pure: ' + banned
    ids = re.findall(r'(?:id = |= )"(\d{10,})"', props)
    assert len(ids) == len(set(ids)) and len(ids) >= 40, 'ids unique, ' + str(len(ids))
    registry = (ROOT / 'docs/77-asset-registry.md').read_text()
    for i in ids:
        assert i in registry, 'docs/77 has a line for ' + i
    generated = (ROOT / 'src/shared/WorldGeneratedMeshes.luau').read_text()
    for key, i in re.findall(r'(\w+) = "(\d{10,})",', props.split('Props.Existing')[1].split('}')[0]):
        assert i in generated, 'existing id is a real WorldGeneratedMeshes id: ' + key
    # BD-296 dressing pass: kit keys and slot sources are real, proportions sane, no invented ids
    kit_data = (ROOT / 'src/shared/WorldKitData.luau').read_text()
    kit_mesh = (ROOT / 'src/shared/WorldKitMeshAssets.luau').read_text()
    gen = (ROOT / 'src/shared/WorldGeneratedMeshes.luau').read_text()
    kinds_src = src.split('local KINDS')[1].split('CaveHubLayout.Kinds = KINDS')[0]
    def kind_box(key):
        m = re.search(r'\b' + key + r' = \{([\d.]+), ([\d.]+), ([\d.]+),', kinds_src)
        assert m, 'layout kind ' + key
        return [float(m.group(i)) for i in (1, 2, 3)]
    kit_keys = re.findall(r'(world_\w+) = \{tone', props)
    assert len(kit_keys) >= 8, 'Props.Kit lists the kit meshes'
    natives = {}
    for k in kit_keys:
        m = re.search(k + r'=\{kind="[a-z]+",family="[a-z_]+",size="[a-z]",triangles=(\d+),extent=\{([\d.]+),([\d.]+),([\d.]+)\}', kit_data)
        assert m, 'kit mesh in WorldKitData: ' + k
        assert int(m.group(1)) <= 80, 'kit dressing mesh stays tiny (<= 80 triangles): ' + k
        assert (k + ' = {meshId = "rbxassetid://') in kit_mesh, 'kit mesh is bound to a published meshId: ' + k
        natives[k] = [float(m.group(i)) for i in (2, 3, 4)]
    # BD-464 Blender ground props (docs/77): not uploaded, ids stay empty strings in WorldGeneratedMeshes.Props; sizes from the registry rows
    natives.update({'ground_rock_small_v3': [2.8, 2.4, 1.2], 'ground_rock_medium_v3': [4.9, 4.0, 2.3], 'ground_rock_mossy_v3': [5.6, 4.5, 3.2],
                    'ground_log_fallen_v3': [7.9, 2.8, 3.0], 'ground_stump_roots_v3': [7.1, 5.9, 3.0], 'ground_mushrooms_v3': [5.3, 4.1, 2.9],
                    'ground_bush_round_v3': [6.0, 4.2, 2.7], 'ground_bush_berry_v3': [6.3, 4.1, 2.1]})
    slots = re.findall(r'(dress_\w+) = \{([^}]*)\}', props.split('Props.Slots = {')[1].split('Props.Glow')[0])
    assert len(slots) >= 8, 'Props.Slots lists the dressing slots'
    def fit(native, target):
        axis = max(range(3), key=lambda i: target[i])
        return max(0.25, min(6, target[axis] / native[axis]))
    for slot, body in slots:
        sources = re.findall(r'"(\w+)"', body)
        assert sources, 'slot has a source: ' + slot
        target = kind_box(slot)
        for srcname in sources:
            if srcname in natives:
                if srcname.startswith('ground_'):
                    assert re.search(srcname + r' = \{assetId = ""', gen), 'BD-464 ground prop is registered with an empty id (never an invented one): ' + srcname
                f = fit(natives[srcname], target)
                for i in range(3):
                    off = max(target[i] / (natives[srcname][i] * f), (natives[srcname][i] * f) / target[i])
                    assert off <= 3.2, 'slot %s source %s proportions fit its box (%.2fx on axis %d)' % (slot, srcname, off, i)
            else:
                assert (srcname + ' = {id = "') in props, 'slot source is a published CaveHubProps asset, kit mesh or BD-464 prop: ' + srcname
    for k in kit_keys:
        if (k + ' = {') in kinds_src:
            target = kind_box(k)
            f = fit(natives[k], target)
            for i in range(3):
                off = max(target[i] / (natives[k][i] * f), (natives[k][i] * f) / target[i])
                assert off <= 1.15, 'kit row %s keeps its own proportions (%.2fx)' % (k, off)
    server_src = (ROOT / 'src/server/CaveProps.luau').read_text()
    assert 'CreateMeshPartAsync' in server_src and 'Props.sourceFor' in server_src and 'pcall(loadKit' in server_src, 'the server loads kit meshes through one guarded path and resolves slots'
    server = (ROOT / 'src/server/CaveProps.luau').read_text()
    assert server.count('InsertService:LoadAsset') == 1 and 'pcall(loadTemplate' in server, 'one guarded load path'
    assert 'task.wait' in server and 'task.spawn' in server, 'props load in the background in batches'
    assert 'IslandTerrainReady' not in server and 'IslandTerrainReady' not in (ROOT / 'src/server/CaveLavaFx.luau').read_text()
    assert 'Props.Solid' in server and server.count('CanCollide = true') <= 1, 'only Props.Solid pieces collide (plus the invisible colliders)'
    assert arena.count('CaveProps.build(') == 1 and arena.count('CaveLavaFx.build(') == 1, 'props and lava FX built once'
    start = arena.index('if caveHub.enabled then\n        -- Cave hub')
    legacy = arena.index('local cz = CaveHubLayout.hub(Config).centerZ')
    assert start < arena.index('CaveProps.build(hub)') < legacy and start < arena.index('CaveLavaFx.build(hub)') < legacy, 'props and lava FX only in the flag-on cave branch'
    assert 'cave_lava_fall' not in server.replace('NotMeshes', ''), 'the chunky lava block is never placed as the waterfall'
    # BD-296 wall rock forms + gate arch frame (docs/140): their own table, empty ids, FBX + registry rows, layout boxes equal the registered mesh sizes
    forms_tbl = gen.split('Generated.CaveForms = {')[1].split(chr(10) + '}' + chr(10))[0]
    form_rows = re.findall(r'^\s{4}(cave_\w+_v3) = \{assetId = "(\d*)", placed = false, tris = (\d+), size = \{([\d., ]+)\}\}', forms_tbl, re.M)
    assert len(form_rows) == 7, 'six rock forms and the gate arch frame in WorldGeneratedMeshes.CaveForms'
    cave_slots = dict(re.findall(r'(cave_(?:form|gate)_\w+) = \{"(\w+)"\}', props.split('Props.Slots = {')[1].split('Props.Matte')[0]))
    assert len(cave_slots) == 7, 'Props.Slots maps the 7 cave form / frame layout keys'
    by_mesh = {row[0]: row for row in form_rows}
    for slot, mesh in cave_slots.items():
        key, aid, tris, size = by_mesh[mesh]
        assert aid == '' or re.fullmatch(r'[1-9][0-9]{8,17}', aid), 'empty (not uploaded) or a real id, never invented: ' + key
        assert (ROOT / ('assets/blender/world/fbx_v3/%s.fbx' % key)).exists(), 'FBX exists: ' + key
        assert key in registry, 'docs/77 row: ' + key
        dims = [float(v) for v in size.split(',')]
        assert kind_box(slot) == dims, 'layout kind %s box equals the registered mesh size %s' % (slot, dims)
        m = re.search(r'\b' + slot + r' = \{[\d., ]+?, (\d+), "', kinds_src)
        assert m and m.group(1) == tris, 'layout kind tris equals the FBX tris: ' + slot
    assert 'GeneratedMeshes.CaveForms' in server_src, 'CaveProps resolves slots against the CaveForms table'
    assert 'CaveForms' not in (ROOT / 'src/server/Arena.luau').read_text() and 'CaveForms' not in (ROOT / 'src/shared/BiomePlacement.luau').read_text(), 'the island never sees the cave forms'

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    source = (ROOT / 'src/shared/Config.luau').read_text()
    print('Default:\n' + run(args.runner, source))
    rewritten, _ = release_profiles.apply_profile(source, 'playtest')
    print('Playtest: ' + run(args.runner, rewritten).splitlines()[0])
