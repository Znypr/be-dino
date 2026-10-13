"""Run the real BD-049 BiomePlacement grammar offline against IslandLayout and WorldKitData.
Checks determinism, path/sanctuary/keep-out clearance, density bounds, ground contact and the
triangle budget. Optional --map writes a top-down placement plan PNG. Not Studio evidence.
"""
from pathlib import Path
import argparse, json, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'
def script(dump):
    return ('local Config=' + wrapped('src/shared/Config.luau') + '\nlocal Layout=' + wrapped('src/shared/IslandLayout.luau')
            + '\nlocal Kit=' + wrapped('src/shared/WorldKitData.luau') + '\nlocal Biome=' + wrapped('src/shared/BiomePlacement.luau') + '\n' + '''
assert(Config.WorldArtMode=="Legacy","default must keep the current look")
assert(Config.FoodArtMode=="Legacy","default must keep the current food look")
local function gen(seed,density) return Biome.generate({seed=seed,density=density,extent=Config.ArenaHalfWidth,height=Layout.height,kit=Kit}) end
local t0=os.clock()
local a=gen(Config.WorldArtSeed,1)
local elapsed=os.clock()-t0
local b=gen(Config.WorldArtSeed,1)
assert(#a==#b,"nondeterministic count")
for i,p in a do local q=b[i] assert(p.id==q.id and p.x==q.x and p.z==q.z and p.yaw==q.yaw and p.scale==q.scale,"nondeterministic placement") end
local c=gen(Config.WorldArtSeed+1,1)
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
assert(counts.tree>=25 and counts.tree<=40,"tree density "..counts.tree)
assert(counts.rock>=15 and counts.rock<=34,"rock density "..counts.rock)
assert(counts.shrub>=20 and counts.shrub<=50,"shrub density "..counts.shrub)
assert(counts.groundcover>=20 and counts.groundcover<=70,"groundcover density "..counts.groundcover)
local tris=Biome.triangles(a,Kit)
assert(tris<=Biome.TriangleBudget,"triangle budget "..tris)
local low=gen(Config.WorldArtSeed,.5)
assert(#low<#a,"density does not scale")
for id,data in Kit do
 if data.kind=="tree" or data.kind=="landmark" or (data.kind=="rock") then assert(#data.colliders>0,"missing collider proxy "..id) end
 if data.kind=="shrub" or data.kind=="groundcover" or data.kind=="food" then assert(#data.colliders==0,"foliage/food must not collide "..id) end
end
print(string.format("World art passed: %d placements (%d trees, %d rocks, %d shrubs, %d cover, 4 landmarks), %d triangles, %.3fs",#a,counts.tree,counts.rock,counts.shrub,counts.groundcover,tris,elapsed))
''' + ('for _,p in a do print(string.format("P %s %s %.2f %.2f %.3f",p.layer,p.id,p.x,p.z,p.radius)) end\n' if dump else ''))

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

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); p.add_argument('--map'); args = p.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify.luau'; path.write_text(script(bool(args.map)))
        out = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-2000:] + out.stderr)
        out = out.stdout
    print('\n'.join(l for l in out.splitlines() if not l.startswith('P ')))
    if args.map: draw([l for l in out.splitlines() if l.startswith('P ')], args.map)
