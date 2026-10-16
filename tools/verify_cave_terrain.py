"""BD-281 offline check of the Cave terrain shell rules (docs/104 s3). Runs the real CaveHubLayout + CaveTerrainRules in Luau and
tests the pure voxel rules (material + occupancy per cell), never Studio: paths and pads flat to the stud, stations and paths
clear above, the 4 ceiling holes open to the sky, walls and ceiling closed and >= 8 studs thick, the gate mouth open and closed
behind, the lava basin carved, no isolated air bubbles anywhere in the grid (6-neighbour flood fill), deterministic, material
mix (stone, rock, slate, cobblestone, a little moss) and budgets (cells, solid voxels, WriteVoxels chunks, work between yields).
Also static checks: Config.CaveHub is false in source (on only in the playtest build), the server writer is only called from the Arena cave branch and follows
IslandTerrain's chunked yielding pattern, BiomePlacement.Sanctuary follows hub(config).biome when the flag is on.
Not Studio evidence: see the BD-281 kanban row for what was and was not verified in Studio.
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local C=CaveHubLayout
local L=C.get()
local R=Rules
local FY=C.FloorY
local CZ=C.CenterZ
local res=R.Res
local function dist(ax,az,bx,bz) return math.sqrt((ax-bx)^2+(az-bz)^2) end
local function occAt(x,y,z) local _,o=R.cell(x,y,z) return o end

assert(res==Config.TerrainResolution,"voxel size = Config.TerrainResolution")
assert(Config.CaveHub==(Config.ReleaseProfile=="playtest"),"CaveHub ships OFF in the default build and ON in the playtest build (owner 2026-10-16, docs/125)")
assert(R.XMin%res==0 and R.XMax%res==0 and R.YMin%res==0 and R.YMax%res==0 and R.ZMin%res==0 and R.ZMax%res==0,"region aligned to the voxel grid")
assert(R.ZMin>Config.ArenaHalfWidth+8,"cave region never overlaps the island terrain (writes cannot clobber it)")
local hub=C.hub(setmetatable({CaveHub=true},{__index=Config}))
local B=hub.biome
assert(R.XMin>=B.minX and R.XMax<=B.maxX and R.ZMin>=B.minZ and R.ZMax<=B.maxZ,"region inside the cave biome rect")

-- ---- grid evaluation (also the budget and determinism numbers)
local g=R.grid()
local nx,ny,nz=g.nx,g.ny,g.nz
local occ,mat={},{}
local idx=function(i,j,k) return (i*ny+j)*nz+k+1 end
local t0=os.clock()
local solid,counts=0,{}
local maxZMin,maxZMax,maxXMin,maxXMax=math.huge,-math.huge,math.huge,-math.huge
for i=0,nx-1 do
 local wx=R.XMin+(i+.5)*res
 for k=0,nz-1 do
  local wz=R.ZMin+(k+.5)*res
  local col=R.column(wx,wz)
  for j=0,ny-1 do
   local wy=R.YMin+(j+.5)*res
   local m,o=R.cellAt(col,wy)
   occ[idx(i,j,k)]=o mat[idx(i,j,k)]=m
   if o>0 then
    solid+=1 counts[m]=(counts[m] or 0)+1
    maxZMin=math.min(maxZMin,wz-res/2) maxZMax=math.max(maxZMax,wz+res/2) maxXMin=math.min(maxXMin,wx-res/2) maxXMax=math.max(maxXMax,wx+res/2)
   else assert(m=="Air","zero occupancy is Air") end
  end
 end
end
local evalSeconds=os.clock()-t0
local total=nx*ny*nz
local plan=R.plan()
assert(plan.cells==total,"plan covers the grid")
assert(total<=130000,"voxel budget: "..total.." cells in the region")
assert(solid<=total*0.9,"solid voxels sane")
assert(#plan.chunks==math.ceil(nx/R.ChunkSlices) and #plan.chunks<=12,"WriteVoxels chunks: "..#plan.chunks)
assert(plan.cellsPerChunk<=16000,"cells per WriteVoxels call <= 16k: "..plan.cellsPerChunk)
assert(plan.cellsBetweenYields<=4000,"cell evaluations between yields <= 4k (no frame hitch): "..plan.cellsBetweenYields)
local sliceSum=0 for _,c in plan.chunks do sliceSum+=c.slices end
assert(sliceSum==nx and plan.chunks[1].minX==R.XMin and plan.chunks[#plan.chunks].maxX==R.XMax,"chunks tile the region exactly")
assert(maxZMin>=B.minZ and maxZMax<=B.maxZ and maxXMin>=B.minX and maxXMax<=B.maxX,"solid voxels stay inside the biome rect "..maxXMin..","..maxXMax..","..maxZMin..","..maxZMax)
assert(evalSeconds<20,"full evaluation under 20 s on the runner: "..evalSeconds)

-- ---- flat paths and pads: the voxel column reproduces the floor height to the stud
local function columnTop(i,k)
 local top=0
 for j=0,ny-1 do
  local wy=R.YMin+(j+.5)*res
  if wy<=FY+12 then top+=occ[idx(i,j,k)]*res end
 end
 return R.YMin+top+res/2 -- Studio measured: the engine surface sits half a cell above the summed occupancy
end
local flatCols,maxDev=0,0
for i=0,nx-1 do for k=0,nz-1 do
 local wx,wz=R.XMin+(i+.5)*res,R.ZMin+(k+.5)*res
 if C.flatDistance(wx,wz)<=-1 and C.insideFloor(wx,wz,0) and dist(wx,wz-CZ,C.Pool.x,C.Pool.z)>C.Pool.r+6 and not (wz-CZ<-92) then
  local top=columnTop(i,k)
  maxDev=math.max(maxDev,math.abs(top-FY))
  assert(math.abs(top-FY)<=0.05,"path/pad column not flat at "..wx..","..wz.." top "..top)
  flatCols+=1
 end
end end
assert(flatCols>=450,"enough flat path/pad columns tested: "..flatCols)

-- ---- stations and paths stay clear above the floor (nothing blocks walking or props)
for _,s in L.stations do
 local checked=0
 for a=0,359,15 do for rr=0,s.r-1,4 do
  local x,z=s.x+rr*math.cos(math.rad(a)),s.z+rr*math.sin(math.rad(a))
  for y=FY+3,FY+24,3 do assert(occAt(x,y,z+CZ)==0,"station not clear: "..s.id.." at "..x..","..y..","..z) checked+=1 end
 end end
 assert(checked>0)
end
local pathChecks=0
for _,p in L.paths do
 local len=dist(p.ax,p.az,p.bx,p.bz)
 for t=0,len,3 do
  local x,z=p.ax+(p.bx-p.ax)*t/len,p.az+(p.bz-p.az)*t/len
  for y=FY+3,FY+18,3 do assert(occAt(x,y,z+CZ)==0,"path not clear: "..p.id) pathChecks+=1 end
 assert(math.abs(columnTop(math.floor((x-R.XMin)/res),math.floor((z+CZ-R.ZMin)/res))-FY)<=0.6,"path height ~floor at "..p.id)
 end
end

-- ---- ceiling holes open to the sky; roof closed elsewhere
for _,h in L.holes do
 local ceil=C.ceilingY(h.x,h.z+CZ)
 for _,f in {0,0.5} do for a=0,315,45 do
  local x,z=h.x+f*(h.radius-1)*math.cos(math.rad(a)),h.z+f*(h.radius-1)*math.sin(math.rad(a))
  for y=ceil+3,R.YMax-res/2,2 do assert(occAt(x,y,z+CZ)==0,"hole "..h.station.." blocked at y "..y) end
 end end
 -- rim: just outside the hole the roof is solid
 local ox=h.x+h.radius+res+2
 local _,o=R.cell(ox,C.ceilingY(ox,h.z+CZ)+4,h.z+CZ)
 assert(o>0.2,"roof solid next to hole "..h.station)
end
assert(#L.holes==4)

-- ---- ceiling closed (>= 8 thick) everywhere else over the cave footprint, and high enough (domes: low at the wall, rising inward)
local ceilChecks,minClear,minDeep=0,math.huge,math.huge
for x=-124,124,4 do for dz=-112,112,4 do
 local wz=dz+CZ
 if C.insideFloor(x,wz,2) then
  local nearHole=false
  for _,h in L.holes do if dist(x,dz,h.x,h.z)<h.radius+5 then nearHole=true end end
  for _,lg in L.ledges do if C.boxDist(x,dz,lg)<2 then nearHole=true end end -- stone shelves stand on the floor: not a ceiling probe
  if not nearHole and not (dz>C.Fall.z-12 and math.abs(x-C.Fall.x)<C.Fall.width/2+4) then
   local floor=C.floorHeight(x,wz)
   local y=floor+1
   while occAt(x,y,wz)<=0 and y<R.YMax do y+=0.5 end
   minClear=math.min(minClear,y-floor)
   if C.caveSd(x,wz)>=9 then minDeep=math.min(minDeep,y-floor) end
   local thick=0
   while occAt(x,y+thick,wz)>0 and thick<30 do thick+=0.5 end
   assert(thick>=8,"ceiling thinner than 8 studs at "..x..","..dz.." ("..thick..")")
   ceilChecks+=1
  end
 end
end end
assert(ceilChecks>800 and minClear>=12 and minDeep>=20,"ceiling domes from the wall up: >= 12 studs anywhere, >= 20 studs 9+ studs from the wall (min "..minClear.." / "..minDeep..")")

-- ---- walls closed and thick all the way round (organic cave: march outward from every wall-side point along the wall normal;
-- gate mouth and falls recess are the only cuts, and stay closed behind; a divider between two parts of the cave may be thinner)
local wallChecks,minThick,thinDividers=0,math.huge,0
for x=-124,124,3 do for dz=-116,116,3 do
 local wz=dz+CZ
 local sd=C.caveSd(x,wz)
 if sd>=1 and sd<=3.5 then
  -- outward normal = direction of falling sd
  local gx=(C.caveSd(x+1,wz)-C.caveSd(x-1,wz))/2
  local gz=(C.caveSd(x,wz+1)-C.caveSd(x,wz-1))/2
  local gl=math.sqrt(gx*gx+gz*gz)
  if gl>0.05 then
   local ux,uz=-gx/gl,-gz/gl
   for _,h in {FY+4,FY+8} do
    if occAt(x,h,wz)<=0 then
     local r=0
     while r<30 and occAt(x+ux*r,h,wz+uz*r)<=0 do r+=0.5 end
     if r<30 then
      local thick=0
      while occAt(x+ux*(r+thick),h,wz+uz*(r+thick))>0 and thick<40 do thick+=0.5 end
      local x0,z0=x+ux*r,wz+uz*r-CZ
      local inGate=z0<-88 and math.abs(x0)<19 and h<FY+22
      local inFalls=z0>C.Fall.z-6 and math.abs(x0-C.Fall.x)<C.Fall.width/2+6
      local nearLedge=false
      for _,lg in L.ledges do if C.boxDist(x0,z0,lg)<3 then nearLedge=true end end
      if not nearLedge then
       minThick=math.min(minThick,thick)
       local divider=C.caveSd(x+ux*(r+thick+1),wz+uz*(r+thick+1))>-4 -- the far side is cave (or its wall relief) again: a thin divider
       if inGate then assert(thick>=3,"gate mouth is closed behind (>= 3 studs): "..thick)
       elseif divider then assert(thick>=2,"divider between two parts of the cave >= 2 studs at "..x..","..z0.." ("..thick..")") thinDividers+=1
       elseif inFalls then assert(thick>=4,"falls recess keeps rock behind it: "..thick.." at "..x0..","..z0.." h "..h.." dir "..ux..","..uz)
       else assert(thick>=8,"wall >= 8 studs at "..x..","..z0.." height "..h.." ("..thick..")") end
       wallChecks+=1
      end
     end
    end
   end
  end
 end
end end
assert(wallChecks>600,"enough wall probes: "..wallChecks)

-- ---- no sky through the shell (Studio 2026-10-16 showed square gaps in domes and tunnel mouths): rays from many interior points, straight
-- up, 45 degrees up and horizontally in 12 directions, must all hit rock before leaving the region (only the 4 ceiling holes are open upward)
local rayChecks,gaps=0,{}
local function nearHole(x,dz) for _,h in L.holes do if dist(x,dz,h.x,h.z)<h.radius+16 then return true end end return false end
for x=-124,124,5 do for dz=-116,116,5 do
 if C.caveSd(x,dz+CZ)>=1.5 then
  local fl=C.floorHeight(x,dz+CZ)
  local y0=fl+2
  if occAt(x,y0,dz+CZ)<=0 then
   local skip=nearHole(x,dz)
   if not skip then
    local hit=false
    for y=y0,R.YMax,1 do if occAt(x,y,dz+CZ)>0 then hit=true break end end
    rayChecks+=1
    if not hit then gaps[#gaps+1]=string.format("up %d,%d",x,dz) end
    for k=0,7 do
     local a=k*math.pi/4
     local ux,uz=math.cos(a)*0.7071,math.sin(a)*0.7071
     local hit2=false
     for t=1,90 do
      local px,py,pz=x+ux*t,y0+t*0.7071,dz+CZ+uz*t
      if nearHole(px,pz-CZ) and py>FY+30 then hit2=true break end -- a ray may leave through one of the 4 sky holes
      if py>R.YMax or px<R.XMin or px>R.XMax or pz<R.ZMin or pz>R.ZMax then break end
      if occAt(px,py,pz)>0 then hit2=true break end
     end
     rayChecks+=1
     if not hit2 and not nearHole(x,dz) then gaps[#gaps+1]=string.format("diag %d,%d dir %d",x,dz,k) end
    end
   end
   for k=0,11 do
    local a=k*math.pi/6
    local hit3=false
    for t=1,320 do
     local px,pz=x+math.cos(a)*t,dz+CZ+math.sin(a)*t
     if px<R.XMin or px>R.XMax or pz<R.ZMin or pz>R.ZMax then break end
     if C.caveSd(px,pz)<-0.5 then -- left the open cave: rock must be right there
      for u=0,14,1 do if occAt(px+math.cos(a)*u,fl+5,pz+math.sin(a)*u)>0 then hit3=true break end end
      break
     end
    end
    rayChecks+=1
    if not hit3 then gaps[#gaps+1]=string.format("side %d,%d dir %d",x,dz,k) end
   end
  end
 end
end end
assert(rayChecks>5000 and #gaps==0,"the rock shell is closed (no sky): "..rayChecks.." rays, "..#gaps.." gaps, first "..tostring(gaps[1]).." "..tostring(gaps[2]))

-- ---- gate opening: the arch mouth toward the island is real air above the flat floor
local g0=L.byId.gate
for _,y in {FY+2,FY+8,FY+14} do
 assert(occAt(g0.x,y,CZ+g0.z-12)==0,"gate approach clear")
 assert(occAt(g0.x,y,CZ-112)==0,"gate mouth open at the centre, y "..y)
 assert(occAt(g0.x+11,FY+3,CZ-112)==0,"gate mouth open near the pillars")
end
assert(occAt(g0.x,FY+17,CZ-112)==0 and occAt(g0.x+14,FY+17,CZ-112)> 0,"mouth is an arch (round top, closed in the corner)")
assert(occAt(g0.x,FY+8,CZ-118)>0,"gate mouth is closed at the far end (no void outside)")
assert(select(2,R.cell(g0.x,FY-4,CZ-112))>=0.99,"gate floor solid")

-- ---- lava basin carved, rock around it, falls recess + lava vein behind the fall
local P=C.Pool
local mP,oP=R.cell(P.x,FY-3,P.z+CZ)
local mP2,oP2=R.cell(P.x+P.r-1,FY-3.5,P.z+CZ)
assert(oP>0 and mP=="CrackedLava","pool bottom is lava material: "..mP)
assert(occAt(P.x,FY+1,P.z+CZ)==0 and occAt(P.x+P.r+6,FY-3,P.z+CZ)>=0.7,"basin is a depression with solid rim")
local carved=occAt(P.x,FY-1,P.z+CZ) assert(carved<=0,"basin carved below the floor top")
assert(select(1,R.cell(P.x+P.r+3,FY-1,P.z+CZ))=="Basalt","basalt rim")
local F=C.Fall
assert(occAt(F.x,FY+20,CZ+F.z+2)==0,"falls recess carved behind the sheet")
-- QA (Studio): the recess once ran through the roof (sheet 48 high, ceiling 38 over the floor) and showed a sky gap
for fx=F.x-18,F.x+18,3 do for fz=F.z-1,F.z+7,2 do
 local roof=false
 for y=FY+8,R.YMax-res/2,1 do if occAt(fx,y,CZ+fz)>0 then roof=true break end end
 assert(roof,"roof closed above the falls recess at "..fx..","..fz)
end end
local fz=F.z+2
while occAt(F.x,FY+7,CZ+fz)<=0 and fz<F.z+30 do fz+=0.5 end
local mF,oF=R.cell(F.x,FY+7,CZ+fz)
assert(oF>0 and mF=="CrackedLava","lava vein behind the falls "..mF)

-- ---- stations: pad material is laid stone; the mix has stone, rock, slate, cobblestone and only a little moss
local function pct(m) return (counts[m] or 0)/solid end
for _,m in {"Rock","Concrete","Slate","Cobblestone","Basalt","Grass","LeafyGrass","CrackedLava"} do assert((counts[m] or 0)>0,"material used: "..m) end
local floorMix={}
local floorCols=0
for i=0,nx-1 do for k=0,nz-1 do
 local wx,wz=R.XMin+(i+.5)*res,R.ZMin+(k+.5)*res
 if C.insideFloor(wx,wz,0) and C.flatDistance(wx,wz)>2 and dist(wx,wz-CZ,C.Pool.x,C.Pool.z)>C.Pool.r+8 and not (wz-CZ>C.Fall.z-8) and not (wz-CZ<-90) then
  local col=R.column(wx,wz)
  local top
  for j=ny-1,0,-1 do if occ[idx(i,j,k)]>0 and R.YMin+(j+.5)*res<=col.floorTop+res then top=mat[idx(i,j,k)] break end end
  if top then floorMix[top]=(floorMix[top] or 0)+1 floorCols+=1 end
 end
end end
local moss=((floorMix.Grass or 0)+(floorMix.LeafyGrass or 0))/floorCols
assert(moss>0.02 and moss<0.15,"moss is a little: "..moss)
for _,m in {"Concrete","Cobblestone"} do assert((floorMix[m] or 0)/floorCols>0.12,"floor stone mix has "..m) end
assert((floorMix.Rock or 0)+(floorMix.Limestone or 0)==0,"BD-296: no dark Rock patches and no striped Limestone on the floor")
local hs=L.byId.heart
local pathMoss=0
for _,p in L.paths do
 local len=dist(p.ax,p.az,p.bx,p.bz)
 for t=0,len,2 do
  local x,z=p.ax+(p.bx-p.ax)*t/len,p.az+(p.bz-p.az)*t/len
  local col=R.column(x,z+CZ)
  local m=select(1,R.cellAt(col,FY-1))
  assert(m=="Cobblestone" or m=="Slate","paths are laid stone, got "..m)
 end
end

-- ---- no isolated air bubbles in the whole grid: every air cell reaches the open sky/outside (6-neighbour flood fill)
local seen={}
local queue={}
local head=1
local function push(i,j,k)
 if i<0 or j<0 or k<0 or i>=nx or j>=ny or k>=nz then return end
 local id=idx(i,j,k)
 if seen[id] or occ[id]>0 then return end
 seen[id]=true queue[#queue+1]=id
end
push(0,ny-1,0)
while head<=#queue do
 local id=queue[head] head+=1
 local k=(id-1)%nz local rest=(id-1-k)//nz local j=rest%ny local i=(rest-j)//ny
 push(i+1,j,k) push(i-1,j,k) push(i,j+1,k) push(i,j-1,k) push(i,j,k+1) push(i,j,k-1)
end
local airTotal,bubbles=0,0
for id=1,total do if occ[id]<=0 then airTotal+=1 if not seen[id] then bubbles+=1 end end end
assert(bubbles==0,"isolated air bubbles: "..bubbles)
-- the walkable footprint (arrival spots, stations) connects to the open sky through the holes
for _,s in L.stations do
 for _,sp in s.spots do
  local i,k=math.floor((sp.x-R.XMin)/res),math.floor((sp.z+CZ-R.ZMin)/res)
  local j=math.floor((FY+res+1-R.YMin)/res)
  assert(seen[idx(i,j,k)],"arrival spot air connected to the sky: "..s.id)
 end
end

-- ---- visible surface budget (faces of solid cells that touch air), measured not claimed
local faces=0
for i=0,nx-1 do for j=0,ny-1 do for k=0,nz-1 do
 if occ[idx(i,j,k)]>0 then
  for _,d in {{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}} do
   local a,b,c=i+d[1],j+d[2],k+d[3]
   if a<0 or b<0 or c<0 or a>=nx or b>=ny or c>=nz or occ[idx(a,b,c)]<=0 then faces+=1 end
  end
 end
end end end
assert(faces<1500000,"voxel faces under 1.5 M (docs/104 s3.1): "..faces)

-- ---- determinism: same cells from a second module instance and from a repeat evaluation
local Fresh=@FRESH@
local Fresh2=(function()
 local script={Parent={CaveHubLayout="x"}}
 local require=function() return @FRESHLAYOUT@ end
 return @FRESHRULES@
end)()
local diffs=0
for n=1,2500 do
 local x=R.XMin+((n*37)%nx+.5)*res local y=R.YMin+((n*11)%ny+.5)*res local z=R.ZMin+((n*53)%nz+.5)*res
 local m1,o1=R.cell(x,y,z) local m2,o2=R.cell(x,y,z) local m3,o3=Fresh2.cell(x,y,z)
 if m1~=m2 or o1~=o2 or m1~=m3 or o1~=o3 then diffs+=1 end
end
assert(diffs==0,"voxel rules deterministic: "..diffs)

local names={} for m,c in counts do names[#names+1]=string.format("%s %.0f%%",m,100*c/solid) end table.sort(names)
-- ---- BD-384 look: cooler cave-only colours, no island Sandstone in the hall, stalactite ceiling rule
for name,c in R.Colors do
 if name~="CrackedLava" then
  assert(c[1]-c[3]<=45 and c[1]<=195 and c[2]<=180 and c[3]>=110,"light warm stone, not orange-hot: "..name)
 end
end
for _,iso in {"Sandstone","Slate","Rock","Basalt","Grass","LeafyGrass"} do assert(R.Colors[iso]==nil,"island material never recoloured: "..iso) end
local wallMats={}
for _,p in {{-60,16},{70,30},{0,40},{-40,26},{20,10},{-90,20}} do
 for i=1,40 do
  local x,z=p[1]+i*1.7,C.CenterZ+p[2]*3-i*1.3
  local col=R.column(x,z)
  local m=R.cellAt(col,col.ceil+2)
  if m~="Air" then wallMats[m]=true end
 end
end
assert(not wallMats.Sandstone,"walls and roof use no Sandstone (island colour)")
-- BD-296 (lead Studio look): the visible wall / ceiling surface is ONE matte stone. No Limestone (horizontal strata stripes), no Rock (dark
-- island teal, BeDino_Stone art variant: smudge patches), no Cobblestone (tile grid) on any cave-shell cell that touches air above the floor,
-- except the lava vein behind the falls, the basin rim and the laid-stone pads / path edges near the floor.
do
 local wallCells,bad,badName=0,0,nil
 for i=1,nx-2 do for k=1,nz-2 do
  local wx,wz=R.XMin+(i+.5)*res,R.ZMin+(k+.5)*res
  local col=R.column(wx,wz)
  for j=1,ny-2 do
   if occ[idx(i,j,k)]>0 and (occ[idx(i+1,j,k)]==0 or occ[idx(i-1,j,k)]==0 or occ[idx(i,j+1,k)]==0 or occ[idx(i,j-1,k)]==0 or occ[idx(i,j,k+1)]==0 or occ[idx(i,j,k-1)]==0) then
    local wy=R.YMin+(j+.5)*res
    local m=mat[idx(i,j,k)]
    if wy>col.floorTop+res+1 and col.sd>-8 and wy<col.ceil+6 and m~="CrackedLava" and m~="Basalt" then -- inside the cave, not the outer skin of the rock shell (never seen)
     wallCells+=1
     if m~=R.WallStone then bad+=1 badName=badName or (m.." at "..wx..","..wy..","..wz) end
    end
   end
  end
 end end
 assert(wallCells>2000,"wall surface cells scanned: "..wallCells)
 assert(bad/wallCells<0.03,"BD-296 wall surface is one matte stone, "..bad.." of "..wallCells.." differ, first "..tostring(badName))
 assert(R.WallStone=="Concrete" and R.Colors.Concrete and R.Colors.Limestone==nil,"walls are Concrete, Limestone is not used")
end
for _,xz in {{0,0},{30,10},{-40,60},{60,-30},{-70,20}} do
 local x,z=xz[1],C.CenterZ+xz[2]
 assert(math.abs(R.ceilingAt(x,z)-R.column(x,z).ceil)<1e-9,"ceilingAt is the shell ceiling")
 assert(math.abs(R.ceilingAt(x,z)-C.ceilingY(x,z))<=R.CeilingRough+1e-6,"within the relief of the smooth ceiling")
end
print(string.format("Cave terrain OK: grid %dx%dx%d = %d cells, %d solid, %d chunks of <= %d cells, %d cells between yields, %d visible faces, %d flat path/pad columns (max dev %.3f), 0 air bubbles of %d air cells, eval %.2f s; mix: %s",
 nx,ny,nz,total,solid,#plan.chunks,plan.cellsPerChunk,plan.cellsBetweenYields,faces,flatCols,maxDev,airTotal,evalSeconds,table.concat(names,", ")))
'''

def script(config):
    layout = wrapped('src/shared/CaveHubLayout.luau')
    rules = wrapped('src/shared/CaveTerrainRules.luau')
    body = (LUAU.replace('local Fresh=@FRESH@\n', '')
                .replace('@FRESHLAYOUT@', layout).replace('@FRESHRULES@', rules))
    return ('local Config=(function()\n' + config + '\nend)()\n'
            + 'local CaveHubLayout=' + layout
            + '\nlocal script={Parent={CaveHubLayout="CaveHubLayout"}}\nlocal require=function() return CaveHubLayout end'
            + '\nlocal Rules=' + rules + '\n' + body)

def run(runner, config):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_cave_terrain.luau'; path.write_text(script(config))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    arena = (ROOT / 'src/server/Arena.luau').read_text()
    island = (ROOT / 'src/server/IslandTerrain.luau').read_text()
    writer = (ROOT / 'src/server/CaveTerrain.luau').read_text()
    assert 'CaveTerrain' in arena and 'CaveHubLayout.hub(Config)' in arena, 'Arena cave branch calls the writer'
    assert 'caveHub.enabled' in arena, 'the writer is only used with the flag on'
    assert 'CaveTerrain' not in island and 'CaveHub' not in island, 'IslandTerrain stays flag-agnostic (it only runs a callback)'
    assert 'beforeReady' in island and 'if beforeReady' in island, 'IslandTerrain runs the cave writer before IslandTerrainReady (no race)'
    assert 'WriteVoxels' in writer and 'task.wait' in writer and 'Rules.plan()' in writer and 'YieldSlices' in writer, 'chunked yielding write like IslandTerrain'
    assert 'Baked' in writer, 'a baked (owner-smoothed) shell skips the fill'
    assert 'Instance.new' not in writer and 'Part' not in writer, 'the shell writes terrain only: no props, no parts'
    rules = (ROOT / 'src/shared/CaveTerrainRules.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'Vector3', 'workspace', 'Config'):
        assert banned not in rules, 'CaveTerrainRules stays pure: ' + banned
    bp = (ROOT / 'src/shared/BiomePlacement.luau').read_text()
    assert 'function BiomePlacement.useHub' in bp, 'BiomePlacement.Sanctuary can follow hub(config).biome'
    assert 'Biome.useHub(caveHub.biome)' in arena and arena.index('Biome.useHub(caveHub.biome)') < arena.index('biomeKit(world)'), 'Arena applies the cave biome rect before placing kit props, flag on only'

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    source = (ROOT / 'src/shared/Config.luau').read_text()
    print('Default: ' + run(args.runner, source))
    rewritten, _ = release_profiles.apply_profile(source, 'playtest')
    print('Playtest: ' + run(args.runner, rewritten)[:60])
