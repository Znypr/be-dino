"""Run the real world v2 grammar offline: IslandLayout (relief + pools), BiomeMap (sub-biomes) and BiomePlacement (kit props).
Checks determinism, path/sanctuary/keep-out/water clearance, biome area and smooth borders, giant classes, part budgets and
ground contact. Optional --map writes a top-down plan PNG coloured by sub-biome. Not Studio evidence.
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles
ROOT = Path(__file__).resolve().parents[1]
BIOME_COLOURS = {'meadow': (150, 205, 90), 'fern': (45, 120, 70), 'conifer': (80, 100, 62), 'marsh': (60, 130, 140), 'badlands': (205, 150, 95), 'volcanic': (80, 62, 72)}
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local PLAYTEST=@PLAYTEST@
-- World v2 floors (a prop is one MeshPart; the owner asked for far more vegetation on a 1.6x wider island).
local TREE_LO,GIANT_LO,LOG_LO,ROCK_LO,SHRUB_LO,COVER_LO,PROPS_LO=300,20,25,70,350,600,1500
-- Whole scene at the playtest density: kit props + food pickups + everything else (hub, boundary, arch, spring, rigs).
local WORLD_MAX,RESIDUAL_PARTS,TOTAL_MAX=5000,600,9000 -- BD-387: 8000 + 800 more food pickups (+10 percent headroom); phone scene is culled, see verify_world_budget
assert(Config.ArenaHalfWidth==260*Layout.Scale and Layout.Scale==1.6,"map is 1.6x the 520 map")
assert(Config.SanctuaryCenterZ==Config.ArenaHalfWidth+105,"hub sits 105 studs past the boundary")
assert(Biome.Sanctuary.minZ>Config.ArenaHalfWidth,"hub footprint is outside the arena")
if PLAYTEST then
 assert(Config.WorldArtMode=="BiomeKit" and Config.FoodArtMode=="Kit","playtest profile must enable the kit")
else
 assert(Config.WorldArtMode=="Legacy","default must keep the current look")
 assert(Config.FoodArtMode=="Legacy","default must keep the current food look")
end
local DENSITY=if PLAYTEST then Config.WorldArtDensity else 1
local function gen(seed,density,meshes) return Biome.generate({seed=seed,density=density,extent=Config.ArenaHalfWidth,height=Layout.height,kit=Kit,meshes=meshes or Meshes,map=BiomeMap,layout=Layout}) end
local t0=os.clock()
local a=gen(Config.WorldArtSeed,DENSITY)
local elapsed=os.clock()-t0
local b=gen(Config.WorldArtSeed,DENSITY)
assert(#a==#b,"nondeterministic count")
-- BD-395 before/after (analytic layout): how many trees/giants/shrubs have their bottom more than 0.5 stud below the highest
-- terrain point under the trunk with the OLD rule (lowest footprint point - 3% of height) and with the new PropGround rule.
do
 local G=Biome.Ground
 local oldBad,newBad,total,worstOld=0,0,0,0
 for _,p in a do
  local data=Kit[p.id]
  if G.Raised[p.layer] and data.kind~="rock" then
   total+=1
   local hs={}
   for _,pt in G.samplePoints(p.x,p.z,G.trunkRadius(data,p.scale,p.radius*.5)) do table.insert(hs,Layout.height(pt[1],pt[2])) end
   local lo=math.huge for _,h in hs do lo=math.min(lo,h) end
   local sink=if p.layer=="tree" or p.layer=="giant" then .03 else .035 -- the old per-layer sink (shrub .02-.05)
   local oldY=lo-sink*data.extent[2]*p.scale
   local hi=-math.huge for _,h in hs do hi=math.max(hi,h) end
   if G.submerged(oldY,hs,.5) then oldBad+=1 worstOld=math.max(worstOld,hi-oldY) end
   if G.submerged(p.y,hs,.5) then newBad+=1 end
  end
 end
 assert(newBad==0,"props still below the terrain: "..newBad)
 print(string.format("BD-395 analytic: %d raised props, bottom >0.5 stud below the terrain: old rule %d (worst %.1f studs), PropGround rule %d",total,oldBad,worstOld,newBad))
end
for i,p in a do local q=b[i] assert(p.id==q.id and p.x==q.x and p.z==q.z and p.yaw==q.yaw and p.scale==q.scale and p.roll==q.roll,"nondeterministic placement") end
local c=gen(Config.WorldArtSeed+1,DENSITY)
local differs=#c~=#a
for i=1,math.min(#a,#c) do if a[i].id~=c[i].id or a[i].x~=c[i].x then differs=true end end
assert(differs,"seed has no effect")
local counts={tree=0,giant=0,log=0,rock=0,shrub=0,groundcover=0,landmark=0}
local byBiome={}
for _,id in BiomeMap.Order do byBiome[id]={tree=0,giant=0,log=0,rock=0,shrub=0,groundcover=0,landmark=0} end
local S=Biome.Sanctuary
local tallest,giantMin,giantMax=0,math.huge,0
for _,p in a do
 counts[p.layer]+=1
 byBiome[p.biome][p.layer]+=1
 local data=Kit[p.id]
 assert(data,"unknown asset "..p.id)
 local half=math.max(data.extent[1],data.extent[3])*.5*p.scale
 if p.layer=="log" then half=data.extent[2]*.5*p.scale end
 assert(math.max(math.abs(p.x),math.abs(p.z))+(if p.layer=="log" then 0 else half)<=Config.ArenaHalfWidth,"prop pokes through boundary")
 assert(p.x+half<S.minX or p.x-half>S.maxX or p.z+half<S.minZ or p.z-half>S.maxZ,"prop clips sanctuary")
 assert(not Layout.inPool(p.x,p.z,0),"prop standing in water: "..p.id)
 local blocking=p.layer~="shrub" and p.layer~="groundcover"
 if blocking then
  local trunk=if p.layer=="tree" or p.layer=="giant" then half*.28 elseif p.layer=="log" then half*.6 else half*.5
  assert(Biome.pathClearance(p.x,p.z)>=trunk,"blocking prop in path: "..p.id)
  assert(Biome.keepOutClearance(p.x,p.z,true)>=0,"blocking prop in keep-out: "..p.id)
 else
  assert(Biome.pathClearance(p.x,p.z)>=1 and Biome.keepOutClearance(p.x,p.z,false)>=0,"foliage in path/keep-out")
 end
 local ground=Layout.height(p.x,p.z)
 if p.layer~="log" then
  local G=Biome.Ground
  if G.Raised[p.layer] and data.kind~="rock" then
   -- BD-395: trees, giants and shrubs rest ON the highest terrain point under the trunk (+0.2): never buried, never floating
   local hs={}
   for _,pt in G.samplePoints(p.x,p.z,G.trunkRadius(data,p.scale,p.radius*.5)) do table.insert(hs,Layout.height(pt[1],pt[2])) end
   assert(not G.submerged(p.y,hs,1e-6),"prop bottom below the terrain under its trunk "..p.id)
   assert(math.abs(p.y-G.restY(p.layer,hs,data.extent[2],p.scale))<1e-6,"prop does not use the PropGround rule "..p.id)
   assert(p.y>=ground-1e-6,"prop below the ground at its pivot "..p.id)
   local hi=-math.huge for _,h in hs do hi=math.max(hi,h) end
   assert(p.y-hi<=G.Clearance+1e-6,"prop floats above the terrain "..p.id)
   assert(p.y-ground<=3.5+data.extent[2]*p.scale*.1,"prop lifted too far "..p.id)
  else
   assert(p.y<=ground+1e-6,"floating base "..p.id)
   assert(ground-p.y<=math.max(2.5,data.extent[2]*p.scale*(if data.kind=="rock" then .42 else .3)),"buried too deep "..p.id)
  end
 else
  assert(math.abs(p.roll-math.pi/2)<1e-9 and string.find(p.id,"world_tree_dead"),"logs are dead trees on their side")
  assert(p.y<=ground+.3*p.scale+2.4 and p.y>=ground-2.4,"log not resting on ground "..p.id)
 end
 if p.layer=="giant" then
  tallest=math.max(tallest,data.extent[2]*p.scale)
  if data.kind=="tree" then giantMin=math.min(giantMin,p.scale) giantMax=math.max(giantMax,p.scale) end
  assert(math.sqrt(p.x^2+(p.z-30)^2)>=150,"giants belong to the outer zones")
 end
end
assert(counts.landmark==4,"four landmarks")
local tris=Biome.triangles(a,Kit)
local worldParts=Biome.parts(a,Kit,Meshes) -- MeshPart props = 1 part + invisible colliders; unbound ids cost the native fallback
assert(worldParts<=Biome.PartBudget*DENSITY,"part budget "..worldParts)
local meshProps,nativeProps=0,0
for _,p in a do if Meshes[p.id] then meshProps+=1 else nativeProps+=1 end end
-- every food pickup is one MeshPart replacing the ball (no growth)
local foodParts=Config.FoodSectorCount*Config.FoodSectorCount*Config.FoodClusterItems
-- Whole-kit failure drill: with no MeshPart loaded the budget falls back to native costs instead of exploding.
local nativeOnly=gen(Config.WorldArtSeed,DENSITY,{})
assert(Biome.parts(nativeOnly,Kit,{})<=Biome.PartBudget*DENSITY,"native fallback blows the part budget")
assert(#nativeOnly<#a,"native fallback must thin the world")
-- Sub-biome map: every biome owns real area, weights sum to 1, borders blend smoothly.
local area={}
for _,id in BiomeMap.Order do area[id]=0 end
local samples=0
for x=-Config.ArenaHalfWidth+8,Config.ArenaHalfWidth-8,8 do for z=-Config.ArenaHalfWidth+8,Config.ArenaHalfWidth-8,8 do
 local h=Layout.height(x,z)
 assert(h>-16 and h<Config.TerrainTop,"height outside voxel region")
 local w,dom=BiomeMap.weights(x,z,h,Config.WorldArtSeed)
 local sum=0 for _,id in BiomeMap.Order do sum+=w[id] end
 assert(math.abs(sum-1)<1e-6,"biome weights must sum to 1")
 area[dom]+=1 samples+=1
end end
for _,id in BiomeMap.Order do assert(area[id]/samples>=.05,"biome too small: "..id.." "..area[id]/samples) end
local w0=BiomeMap.weights(0,30,Layout.height(0,30),Config.WorldArtSeed)
assert(w0.meadow>.9,"spawn is the Meadow")
local jump=0
for x=-400,400,2 do
 local a1=BiomeMap.weights(x,100,Layout.height(x,100),Config.WorldArtSeed)
 local a2=BiomeMap.weights(x+2,100,Layout.height(x+2,100),Config.WorldArtSeed)
 for _,id in BiomeMap.Order do jump=math.max(jump,math.abs(a1[id]-a2[id])) end
end
assert(jump<.35,"biome weights must change smoothly: "..jump)
for _,id in BiomeMap.Order do assert(BiomeMap.Ground[id] and BiomeMap.Rock[id] and BiomeMap.Names[id] and BiomePlacementBiomes[id],"biome data complete: "..id) end
if PLAYTEST then
 assert(counts.giant>=GIANT_LO and tallest>=75,"giant classes: "..counts.giant.." tallest "..tallest)
 assert(giantMin>=2.4 and giantMax<=4.0001,"giant trees are 2.4x-4x")
 assert(Config.WorldArtDensity>=.5 and Config.WorldArtDensity<=2 and Config.WorldArtDensity>1,"playtest density")
 assert(#a>=PROPS_LO,"the kit must dress the map richly: "..#a.." props")
 assert(counts.tree>=TREE_LO and counts.log>=LOG_LO and counts.rock>=ROCK_LO and counts.shrub>=SHRUB_LO and counts.groundcover>=COVER_LO,"kit must clearly dress the map")
 for _,id in BiomeMap.Order do assert(byBiome[id].tree+byBiome[id].giant+byBiome[id].rock>=8,"biome has no structure props: "..id) end
 assert(nativeProps==0,"every kit prop must be a MeshPart now (all 41 uploaded): "..nativeProps)
 assert(worldParts<=WORLD_MAX,"world kit parts "..worldParts)
 assert(foodParts<=3700,"food pickup parts "..foodParts) -- BD-387: 400 clusters x 9 = 3,600 (cap 3,700; was 3,300 for 8 per cluster); the phone side is covered by verify_world_budget
 assert(worldParts+foodParts+RESIDUAL_PARTS<=TOTAL_MAX,"total world parts "..(worldParts+foodParts+RESIDUAL_PARTS))
 -- BD-167: colour variation stays a mild tint; undergrowth is capped and every kit id is used by at least two biomes
 for _,bid in BiomeMap.Order do for k=0,8 do local r,g,b=Biome.tint(bid,k/8,(k*3%9)/8) assert(r>=.72 and g>=.72 and b>=.72 and r<=1 and g<=1 and b<=1,"tint out of range "..bid) end end
 local usedIn={} for _,bid in BiomeMap.Order do local d=BiomePlacementBiomes[bid] for _,list in {d.trees,d.rocks,d.shrubs,d.cover} do for _,e in list do usedIn[e[1]]=(usedIn[e[1]] or 0)+1 end end end
 for _,fam in {"canopy","conifer","cycad","dead"} do assert((usedIn[fam] or 0)>=3,"tree family used in too few biomes: "..fam) end
 for _,fam in {"mossy","bare"} do assert((usedIn[fam] or 0)>=4,"rock family used in too few biomes: "..fam) end
 for _,family in {"berry","fruit","egg","amber"} do
  for _,v in {"a","b"} do assert(Kit["food_"..family.."_"..v],"missing food variant "..family..v) end
 end
end
local low=gen(Config.WorldArtSeed,DENSITY*.5)
assert(#low<#a,"density does not scale")
for id,data in Kit do
 if data.kind=="tree" or data.kind=="landmark" or (data.kind=="rock") then assert(#data.colliders>0,"missing collider proxy "..id) end
 if data.kind=="shrub" or data.kind=="groundcover" or data.kind=="food" then assert(#data.colliders==0,"foliage/food must not collide "..id) end
end
local byId,ids,list={},{},{}
for _,p in a do byId[p.id]=(byId[p.id] or 0)+1 end
for id in byId do table.insert(ids,id) end
table.sort(ids)
for _,id in ids do table.insert(list,id.."="..byId[id]) end
print(string.format("%s world art: %d kit parts + %d food pickup parts + ~%d other = %d; %d placements (%d trees, %d giants, %d logs, %d rocks, %d shrubs, %d cover, 4 landmarks; %d MeshPart props), %d triangles, tallest giant %.0f studs, %.3fs",if PLAYTEST then "Playtest" else "Default",worldParts,foodParts,RESIDUAL_PARTS,worldParts+foodParts+RESIDUAL_PARTS,#a,counts.tree,counts.giant,counts.log,counts.rock,counts.shrub,counts.groundcover,meshProps,tris,tallest,elapsed))
for _,id in BiomeMap.Order do
 local t=byBiome[id]
 print(string.format("  %-9s area %2d%%  trees %3d giants %2d logs %2d rocks %3d shrubs %3d cover %3d",id,math.floor(area[id]/samples*100+.5),t.tree,t.giant,t.log,t.rock,t.shrub,t.groundcover))
end
print("by id: "..table.concat(list," "))
'''

def script(dump, config=None, playtest=False):
    head = ('local Config=' + ('(function()\n' + config + '\nend)()' if config else wrapped('src/shared/Config.luau'))
            + '\nlocal Layout=' + wrapped('src/shared/IslandLayout.luau') + '\nlocal BiomeMap=' + wrapped('src/shared/BiomeMap.luau')
            + '\nlocal Kit=' + wrapped('src/shared/WorldKitData.luau') + '\nlocal Meshes=' + wrapped('src/shared/WorldKitMeshAssets.luau')
            + '\nlocal Biome=' + wrapped('src/shared/BiomePlacement.luau') + '\nlocal BiomePlacementBiomes=Biome.Biomes\n')
    tail = ''
    if dump:
        tail = ('for _,p in a do print(string.format("P %s %s %.2f %.2f %.3f %s",p.layer,p.id,p.x,p.z,p.radius,p.biome)) end\n'
                'for pi,path in Biome.Paths do for i=1,#path.points do print(string.format("L %d %.1f %.1f",pi,path.points[i][1],path.points[i][2])) end end\n'
                'for _,pool in Layout.Pools do print(string.format("W %.1f %.1f %.1f %.1f",pool.x,pool.z,pool.rx,pool.rz)) end\n'
                'local N=208 for iz=0,N-1 do local row={} for ix=0,N-1 do local x=-416+(ix+.5)*832/N local z=-416+(iz+.5)*832/N local h=Layout.height(x,z) local _,d=BiomeMap.weights(x,z,h,Config.WorldArtSeed) table.insert(row,table.find(BiomeMap.Order,d)) end print("M "..table.concat(row,",")) end\n')
    return head + LUAU.replace('@PLAYTEST@', 'true' if playtest else 'false') + tail

def draw(lines, path):
    from PIL import Image, ImageDraw
    E, S = 416, 2  # pixels per stud / 2 = 1 px per 1 stud * S/2
    size = 2 * E * S // 2
    im = Image.new('RGB', (size, size), (150, 190, 120)); d = ImageDraw.Draw(im)
    f = lambda x, z: ((x + E) * S / 2, (z + E) * S / 2)
    order = ['meadow', 'fern', 'conifer', 'marsh', 'badlands', 'volcanic']
    rows = [l[2:].split(',') for l in lines if l.startswith('M ')]
    cell = size / len(rows)
    for z, row in enumerate(rows):
        for x, v in enumerate(row):
            d.rectangle((x * cell, z * cell, (x + 1) * cell, (z + 1) * cell), fill=tuple(int(c * .8 + 40) for c in BIOME_COLOURS[order[int(v) - 1]]))
    colours = {'tree': (20, 70, 40), 'giant': (10, 30, 20), 'log': (110, 70, 40), 'rock': (120, 125, 128), 'shrub': (90, 160, 80), 'groundcover': (200, 210, 110), 'landmark': (220, 40, 40)}
    paths = {}
    for l in lines:
        if l.startswith('L '):
            _, i, x, z = l.split(); paths.setdefault(i, []).append(f(float(x), float(z)))
    for pts in paths.values(): d.line(pts, fill=(235, 220, 170), width=6)
    for l in lines:
        if l.startswith('W '):
            _, x, z, rx, rz = l.split(); cx, cy = f(float(x), float(z)); a, b = float(rx) * S / 2, float(rz) * S / 2
            d.ellipse((cx - a, cy - b, cx + a, cy + b), fill=(40, 90, 210))
    for l in lines:
        if l.startswith('P '):
            _, layer, pid, x, z, r, biome = l.split(); x, z, r = float(x), float(z), max(1.0, float(r))
            cx, cy = f(x, z); rr = r * S / 2
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=colours[layer])
    d.text((10, 10), 'World v2 placement plan (seed 1404) - biomes tinted, giants dark, logs brown, landmarks red, water blue', fill=(0, 0, 0))
    im.save(path)

def legacy_parts():
    """Part count of the legacy world props (baked models in resources/roblox) at the old Arena.luau placement counts."""
    def count(name): return len(re.findall(r'<Item class="(?:Wedge|Mesh)?Part"', (ROOT / 'resources/roblox' / (name + '.rbxmx')).read_text(errors='ignore')))
    tree, rock, fern = count('tree') + 1, count('rock') + 1, count('fern')  # tree/rock add one invisible collider
    world = (8 * 4 + 2) * tree + (8 * 3 + 48) * rock + (8 * 4 + 65) * fern
    food = 77 * count('egg') + 31 * count('amber')
    return world, food, dict(tree=tree, rock=rock, fern=fern)

def static_checks():
    food = (ROOT / 'src/server/FoodService.luau').read_text()
    assert 'kitVisuals < Config.FoodKitVisualCap' in food and 'useModel = (kind.id == "egg" or kind.id == "amber") and not meshPickup' in food, 'native fallback models only for egg/amber, capped'
    assert 'pickup, meshPickup = mesh, true' in food and '"KitMesh"' in food, 'kit mesh is the pickup part (no extra part)'
    assert re.findall(r'id = "(\w+)", weight = \d+, points = (\d+)', food) == [('berry', '1'), ('fruit', '4'), ('egg', '15'), ('amber', '50')], 'food values changed'
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'FoodArtMode = "Legacy"' in cfg and 'WorldArtMode = "Legacy"' in cfg, 'source default must stay Legacy'
    arena = (ROOT / 'src/server/Arena.luau').read_text()
    assert 'CaveHubLayout.hub(Config)' in arena and 'Layout.Pools' in arena, 'arena derives the hub and water from Config/IslandLayout'

def run(runner, source, dump=False, playtest=False):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify.luau'; path.write_text(script(dump, source, playtest))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-2000:] + out.stderr)
        return out.stdout

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); p.add_argument('--map'); args = p.parse_args()
    static_checks()
    keep = lambda out: chr(10).join(l for l in out.splitlines() if l[:2] not in ('P ', 'L ', 'W ', 'M '))
    print(keep(run(args.runner, None, False)))
    rewritten, _ = release_profiles.apply_profile((ROOT / 'src/shared/Config.luau').read_text(), 'playtest')
    out = run(args.runner, rewritten, bool(args.map), True)
    print(keep(out))
    world, food, per = legacy_parts()
    print(f"Legacy world props ~{world:,} parts (+~{food:,} legacy egg/amber food models), per prop {per}")
    if args.map: draw(out.splitlines(), args.map)
