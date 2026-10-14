"""Run the real BD-049 BiomePlacement grammar offline against IslandLayout and WorldKitData.
Checks determinism, path/sanctuary/keep-out clearance, density bounds, ground contact and the
triangle budget. Optional --map writes a top-down placement plan PNG. Not Studio evidence.
"""
from pathlib import Path
import argparse, json, re, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'
def script(dump, config=None, playtest=False):
    return ('local Config=' + ('(function()\n' + config + '\nend)()' if config else wrapped('src/shared/Config.luau')) + '\nlocal Layout=' + wrapped('src/shared/IslandLayout.luau')
            + '\nlocal Kit=' + wrapped('src/shared/WorldKitData.luau') + '\nlocal Meshes=' + wrapped('src/shared/WorldKitMeshAssets.luau') + '\nlocal Biome=' + wrapped('src/shared/BiomePlacement.luau') + '\n' + '''
local PLAYTEST=@PLAYTEST@
local TREE_LO,ROCK_LO,SHRUB_LO,COVER_LO,PROPS_LO,WORLD_MAX=60,30,150,250,400,4500
if PLAYTEST then
 assert(Config.WorldArtMode=="BiomeKit" and Config.FoodArtMode=="Kit","playtest profile must enable the kit")
else
 assert(Config.WorldArtMode=="Legacy","default must keep the current look")
 assert(Config.FoodArtMode=="Legacy","default must keep the current food look")
end
local DENSITY=if PLAYTEST then Config.WorldArtDensity else 1
local function gen(seed,density) return Biome.generate({seed=seed,density=density,extent=Config.ArenaHalfWidth,height=Layout.height,kit=Kit,meshes=Meshes}) end
local t0=os.clock()
local a=gen(Config.WorldArtSeed,DENSITY)
local elapsed=os.clock()-t0
local b=gen(Config.WorldArtSeed,DENSITY)
assert(#a==#b,"nondeterministic count")
for i,p in a do local q=b[i] assert(p.id==q.id and p.x==q.x and p.z==q.z and p.yaw==q.yaw and p.scale==q.scale,"nondeterministic placement") end
local c=gen(Config.WorldArtSeed+1,DENSITY)
local differs=#c~=#a
for i=1,math.min(#a,#c) do if a[i].id~=c[i].id or a[i].x~=c[i].x then differs=true end end
assert(differs,"seed has no effect")
local counts={tree=0,rock=0,shrub=0,groundcover=0,landmark=0}
local S=Biome.Sanctuary
for _,p in a do
 counts[p.layer]+=1
 local data=Kit[p.id]
 assert(data,"unknown asset "..p.id)
 local half=math.max(data.extent[1],data.extent[3])*.5*p.scale
 assert(math.max(math.abs(p.x),math.abs(p.z))+half<=Config.ArenaHalfWidth,"prop pokes through boundary")
 assert(p.x+half<S.minX or p.x-half>S.maxX or p.z+half<S.minZ or p.z-half>S.maxZ,"prop clips sanctuary")
 local blocking=p.layer~="shrub" and p.layer~="groundcover"
 if blocking then
  local trunk=if p.layer=="tree" then half*.3 else half*.5
  assert(Biome.pathClearance(p.x,p.z)>=trunk,"blocking prop in path: "..p.id)
  assert(Biome.keepOutClearance(p.x,p.z,true)>=0,"blocking prop in keep-out: "..p.id)
 else
  assert(Biome.pathClearance(p.x,p.z)>=1 and Biome.keepOutClearance(p.x,p.z,false)>=0,"foliage in path/keep-out")
 end
 local ground=Layout.height(p.x,p.z)
 assert(p.y<=ground+1e-6,"floating base "..p.id)
 assert(ground-p.y<=math.max(2.5,data.extent[2]*p.scale*.3),"buried too deep "..p.id)
end
assert(counts.landmark==4,"four landmarks")
if not PLAYTEST then
assert(counts.tree>=TREE_LO and counts.tree<=130,"tree density "..counts.tree)
assert(counts.rock>=ROCK_LO and counts.rock<=80,"rock density "..counts.rock)
assert(counts.shrub>=SHRUB_LO and counts.shrub<=380,"shrub density "..counts.shrub)
assert(counts.groundcover>=COVER_LO and counts.groundcover<=620,"groundcover density "..counts.groundcover)
end
local tris=Biome.triangles(a,Kit)
local worldParts=Biome.parts(a,Kit,Meshes) -- MeshPart props = 1 part + invisible colliders; unbound ids cost the native fallback
assert(worldParts<=Biome.PartBudget*DENSITY,"part budget "..worldParts)
local meshProps,nativeProps=0,0
for _,p in a do if Meshes[p.id] then meshProps+=1 else nativeProps+=1 end end
-- every food pickup is one MeshPart replacing the ball (no growth); legacy dressing kept in kit mode (docs/68)
local foodParts=Config.FoodSectorCount*Config.FoodSectorCount*Config.FoodClusterItems
local residualParts=1100
-- Whole-kit failure drill: with no MeshPart loaded the budget falls back to native costs instead of exploding.
local nativeOnly=Biome.generate({seed=Config.WorldArtSeed,density=DENSITY,extent=Config.ArenaHalfWidth,height=Layout.height,kit=Kit,meshes={}})
assert(Biome.parts(nativeOnly,Kit,{})<=Biome.PartBudget*DENSITY,"native fallback blows the part budget")
assert(#nativeOnly<#a,"native fallback must thin the world")
if PLAYTEST then
 assert(Config.WorldArtDensity>=.5 and Config.WorldArtDensity<=2 and Config.WorldArtDensity>1,"playtest density")
 assert(#a>=PROPS_LO,"the kit must dress the map richly: "..#a.." props (owner: lush; was ~45 as native models)")
 assert(counts.tree>=TREE_LO and counts.rock>=ROCK_LO and counts.shrub>=SHRUB_LO and counts.groundcover>=COVER_LO,"kit must clearly dress the map")
 assert(nativeProps<=1,"only the unuploaded dead_m may be native: "..nativeProps)
 assert(worldParts<=WORLD_MAX,"world kit parts "..worldParts)
 assert(foodParts<=1600,"food pickup parts "..foodParts)
 assert(worldParts+foodParts+residualParts<=8000,"total world parts "..(worldParts+foodParts+residualParts))
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
print(string.format("%s world art: %d kit parts + %d food pickup parts + ~%d legacy dressing = %d; %d placements (%d trees, %d rocks, %d shrubs, %d cover, 4 landmarks; %d MeshPart props), %d triangles, %.3fs",if PLAYTEST then "Playtest" else "Default",worldParts,foodParts,residualParts,worldParts+foodParts+residualParts,#a,counts.tree,counts.rock,counts.shrub,counts.groundcover,meshProps,tris,elapsed))
print("by id: "..table.concat(list," "))
'''.replace('@PLAYTEST@','true' if playtest else 'false') + ('for _,p in a do print(string.format("P %s %s %.2f %.2f %.3f",p.layer,p.id,p.x,p.z,p.radius)) end\n' if dump else ''))

def draw(lines, path):
    from PIL import Image, ImageDraw
    import importlib
    S, E = 4, 260
    im = Image.new('RGB', (2 * E * S // 2, 2 * E * S // 2), (150, 190, 120)); d = ImageDraw.Draw(im)
    f = lambda x, z: ((x + E) * S / 2, (z + E) * S / 2)
    colours = {'tree': (40, 100, 60), 'rock': (120, 125, 128), 'shrub': (90, 160, 80), 'groundcover': (200, 210, 110), 'landmark': (200, 60, 50)}
    paths = [((0, 30), (-40, 8), (-80, -15), (-125, -100)), ((0, 30), (40, -30), (110, -40), (105, -80)), ((0, 30), (0, -180)), ((0, 30), (15, 190), (0, 255)), ((0, 30), (-105, 80), (-190, 15)), ((0, 30), (128, 102), (182, 20))]
    for p in paths: d.line([f(*q) for q in p], fill=(225, 205, 150), width=20)
    for line in lines:
        _, layer, pid, x, z, r = line.split(); x, z, r = float(x), float(z), max(1.5, float(r))
        (cx, cy) = f(x, z); rr = r * S / 2
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=colours[layer])
    d.text((10, 10), 'BD-049 BiomeKit placement plan (seed 1404, density 1) - paths beige, landmarks red', fill=(0, 0, 0))
    im.save(path)

def legacy_parts():
    """Part count of the legacy world props (baked models in resources/roblox) at the Arena.luau placement counts."""
    def count(name): return len(re.findall(r'<Item class="(?:Wedge|Mesh)?Part"', (ROOT / 'resources/roblox' / (name + '.rbxmx')).read_text(errors='ignore')))
    tree, rock, fern = count('tree') + 1, count('rock') + 1, count('fern')  # tree/rock add one invisible collider
    world = (8 * 4 + 2) * tree + (8 * 3 + 48) * rock + (8 * 4 + 65) * fern
    food = 77 * count('egg') + 31 * count('amber')  # ~5% eggs, ~2% amber of 1,536 pickups (legacy clones the models)
    return world, food, dict(tree=tree, rock=rock, fern=fern)

def static_checks():
    food = (ROOT / 'src/server/FoodService.luau').read_text()
    assert 'kitVisuals < Config.FoodKitVisualCap' in food and 'useModel = (kind.id == "egg" or kind.id == "amber") and not meshPickup' in food, 'native fallback models only for egg/amber, capped'
    assert 'pickup, meshPickup = mesh, true' in food and '"KitMesh"' in food, 'kit mesh is the pickup part (no extra part)'
    assert re.findall(r'id = "(\w+)", weight = \d+, points = (\d+)', food) == [('berry', '1'), ('fruit', '4'), ('egg', '15'), ('amber', '50')], 'food values changed'
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'FoodArtMode = "Legacy"' in cfg and 'WorldArtMode = "Legacy"' in cfg, 'source default must stay Legacy'

def run(runner, source, dump=False, playtest=False):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify.luau'; path.write_text(script(dump, source, playtest))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-2000:] + out.stderr)
        return out.stdout

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); p.add_argument('--map'); args = p.parse_args()
    static_checks()
    out = run(args.runner, None, bool(args.map))
    print(chr(10).join(l for l in out.splitlines() if not l.startswith('P ')))
    rewritten, _ = release_profiles.apply_profile((ROOT / 'src/shared/Config.luau').read_text(), 'playtest')
    print(chr(10).join(l for l in run(args.runner, rewritten, False, True).splitlines() if not l.startswith('P ')))
    world, food, per = legacy_parts()
    print(f"Legacy world props ~{world:,} parts (+~{food:,} legacy egg/amber food models), per prop {per}")
    if args.map: draw([l for l in out.splitlines() if l.startswith('P ')], args.map)
