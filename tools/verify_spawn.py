"""BD-210 offline spawn geometry check. Runs the real Config, IslandLayout and SpawnGeometry in Luau (Vector3 stubbed):
the hub arrival point is over the solid SanctuaryGround inside its fences and outside the arena; the island run-start
point is over terrain, inside the boundary, out of water, on gentle ground and just above the surface; fall detection
fires below every floor but never on walkable ground. Also checks the server/client wiring statically. Not Studio evidence.
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles
import rehearsal_env
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local G=SpawnGeometry
local expectCave=EXPECT_CAVE
assert((Config.CaveHub==true)==expectCave,"Config.CaveHub == (profile is playtest)")
local hub=G.hubPoint(Config)
if Config.CaveHub==true then
 -- Cave hub (BD-280/BD-285): the spawn is CaveHubLayout.spawn() on the organic floor, inside the open cave.
 local C=CaveHubLayout
 local sp=C.spawn()
 assert(hub.X==sp.x and hub.Y==sp.y and hub.Z==sp.z,"hubPoint is CaveHubLayout.spawn()")
 assert(hub.Z==C.CenterZ and C.hub(Config).floorY==C.FloorY,"hub point at the cave centre")
 assert(G.inHub(Config,hub.X,hub.Z),"spawn inside the hub box")
 assert(C.insideFloor(hub.X,hub.Z,6),"spawn at least 6 studs inside the open cave (not in rock)")
 local fl=C.floorHeight(hub.X,hub.Z)
 assert(hub.Y-fl>=G.DropClearance-1 and hub.Y-fl<=G.DropClearance+8,"spawn just above the cave floor "..(hub.Y-fl))
 assert(C.ceilingY(hub.X,hub.Z)-hub.Y>8,"headroom at the spawn")
 for dx=-6,6,3 do for dz=-6,6,3 do
  assert(C.insideFloor(hub.X+dx,hub.Z+dz,2),"spawn surroundings are open floor")
  local f=C.floorHeight(hub.X+dx,hub.Z+dz)
  assert(not G.fallen(Config,Layout,Vector3.new(hub.X+dx,f+3,hub.Z+dz)),"standing near spawn must not count as fallen")
  assert(G.fallen(Config,Layout,Vector3.new(hub.X+dx,C.FloorY-G.FallDepth-1,hub.Z+dz)),"under the cave not detected")
 end end
 assert(C.hub(Config).centerZ-C.hub(Config).halfZ>Config.ArenaHalfWidth+8,"cave box does not overlap the terrain")
 assert(G.recoveryPoint(Config,Layout,false)==hub,"recovery returns to the cave spawn outside a run")
 -- flag-off identity on a clone: the legacy hub is untouched
 local off=table.clone(Config) off.CaveHub=false
 assert(G.hubPoint(off).Z==Config.SanctuaryCenterZ and G.hubPoint(off).Y==G.HubFloorY+G.DropClearance,"flag-off clone keeps the legacy hub")
else
 -- Legacy hub: SanctuaryGround 110x6x95 centred (0,3,cz); fences at x=+-48 and z=cz+-43 (Arena.build).
 assert(hub.X==0 and hub.Z==Config.SanctuaryCenterZ,"hub point at the sanctuary centre")
 assert(G.inHub(Config,hub.X,hub.Z),"hub point over SanctuaryGround")
 assert(math.abs(hub.X)<48-4 and math.abs(hub.Z-Config.SanctuaryCenterZ)<43-4,"hub point inside the fences")
 assert(hub.Y>G.HubFloorY+2 and hub.Y<G.HubFloorY+8,"hub point just above the floor "..hub.Y)
 assert(Config.SanctuaryCenterZ-G.HubHalfZ>Config.ArenaHalfWidth+8,"hub ground does not overlap the terrain")
 assert(G.HubHalfX==55 and G.HubHalfZ==47.5 and G.HubFloorY==6,"hub numbers mirror Arena.build")
end
-- Island run start.
local isl=G.islandPoint(Layout)
local ground=Layout.height(isl.X,isl.Z)
assert(G.inTerrain(Config,isl.X,isl.Z),"island spawn over terrain")
assert(math.max(math.abs(isl.X),math.abs(isl.Z))<Config.ArenaHalfWidth-40,"island spawn well inside the boundary")
assert(isl.Y-ground>=G.DropClearance+2 and isl.Y-ground<=10,"island spawn just above the surface")
assert(ground>G.TerrainBottom+8,"thick terrain under the spawn")
assert(not Layout.inPool(isl.X,isl.Z,12),"island spawn not in or beside water")
local maxSlope=0
for dx=-24,24,4 do for dz=-24,24,4 do
 local x,z=isl.X+dx,isl.Z+dz
 assert(G.inTerrain(Config,x,z),"spawn surroundings over terrain")
 local s=math.abs(Layout.height(x+2,z)-Layout.height(x-2,z))/4+math.abs(Layout.height(x,z+2)-Layout.height(x,z-2))/4
 maxSlope=math.max(maxSlope,s)
 assert(not G.fallen(Config,Layout,Vector3.new(x,Layout.height(x,z)+3,z)),"standing near spawn must not count as fallen")
end end
assert(maxSlope<math.tan(math.rad(Config.MaxSlopeAngle))*.5,"spawn surroundings walkable "..maxSlope)
-- Fall detection: everywhere on the map, standing is fine and 25 studs under the floor is fallen.
local E=Config.ArenaHalfWidth
for x=-E,E,16 do for z=-E,E,16 do
 local h=Layout.height(x,z)
 assert(h<Config.TerrainTop-4 and h>G.TerrainBottom+4,"surface inside the voxel range at "..x..","..z)
 assert(not G.fallen(Config,Layout,Vector3.new(x,h+3,z)),"walkable ground flagged as fallen")
 assert(G.fallen(Config,Layout,Vector3.new(x,h-G.FallDepth-1,z)),"under-map not detected")
end end
if Config.CaveHub~=true then
for x=-55,55,5 do for z=Config.SanctuaryCenterZ-47,Config.SanctuaryCenterZ+47,5 do
 assert(not G.fallen(Config,Layout,Vector3.new(x,G.HubFloorY+3,z)),"hub floor flagged as fallen")
 assert(G.fallen(Config,Layout,Vector3.new(x,G.HubFloorY-G.FallDepth-1,z)),"under the hub not detected")
end end
end
assert(G.fallen(Config,Layout,Vector3.new(0,-60,Config.ArenaHalfWidth+30)),"void between arena and hub")
local r1,r2=G.recoveryPoint(Config,Layout,true),G.recoveryPoint(Config,Layout,false)
assert(r1==isl and r2==hub,"recovery returns to island spawn in a run, hub otherwise")
print(string.format("Spawn geometry OK: hub (%.0f, %.1f, %.0f) over floor %.0f; island (%.0f, %.1f, %.0f) over ground %.2f, max slope %.2f",hub.X,hub.Y,hub.Z,G.HubFloorY,isl.X,isl.Y,isl.Z,ground,maxSlope))
'''

VECTOR = '''local Vector3={} Vector3.__index=Vector3
function Vector3.new(x,y,z) return setmetatable({X=x,Y=y,Z=z},Vector3) end
Vector3.__eq=function(a,b) return a.X==b.X and a.Y==b.Y and a.Z==b.Z end
'''

def script(config, cave):
    return (VECTOR + 'local Config=' + ('(function()\n' + config + '\nend)()')
            + '\nlocal CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau')
            + '\nlocal script={Parent={CaveHubLayout="CaveHubLayout"}}\nlocal require=function() return CaveHubLayout end'
            + '\nlocal Layout=' + wrapped('src/shared/IslandLayout.luau')
            + '\nlocal SpawnGeometry=' + wrapped('src/shared/SpawnGeometry.luau') + '\n' + LUAU.replace('EXPECT_CAVE', 'true' if cave else 'false'))

def run(runner, config, cave):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_spawn.luau'; path.write_text(script(config, cave))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-2000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text()
    run_lc = (ROOT / 'src/server/RunLifecycle.luau').read_text()
    guard = (ROOT / 'src/server/MovementGuard.luau').read_text()
    arena = (ROOT / 'src/server/Arena.luau').read_text()
    client = (ROOT / 'src/client/WorldReady.client.luau').read_text()
    assert boot.index('Arena.build()') < boot.index('Players.PlayerAdded:Connect(setup)'), 'world is built before players are set up'
    assert 'IslandTerrainReady' in boot.split('local function spawnLoadedPlayer')[1].split('LoadCharacterAsync')[0], 'character load waits for terrain'
    assert 'FallRecovery' in boot and 'MovementGuard.reset' in boot, 'fall safety net started'
    assert re.search(r'character:PivotTo\(hub\)\s*\n\s*task\.spawn', boot), 'hub placement happens before the attach yield'
    assert 'RunLifecycle.worldReady(player)' in run_lc and 'SpawnGeometry.islandPoint' in run_lc, 'run start gated and uses the shared spawn point'
    assert 'ClientWorldReady' in run_lc and 'ClientWorldReady' in client, 'client terrain-ready handshake wired'
    assert 'SpawnGeometry.fallen' in guard, 'MovementGuard leaves fallen characters to FallRecovery'
    fall = (ROOT / 'src/server/FallRecovery.luau').read_text()
    assert 'SetNetworkOwner(nil)' in fall and 'FallRecovery).teleport(' in run_lc, 'run-start teleport takes physics ownership first'
    assert 'SpawnGeometry.hubPoint(Config)' in arena and 'CaveHubLayout.hub(Config)' in arena, 'SpawnLocation sits in the hub'

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    source = (ROOT / 'src/shared/Config.luau').read_text()
    # docs/152 BD-626: in the all-on rehearsal tree the Config file returns the all-on values (CaveHub on). The DEFAULT variant is checked
    # against the committed Config (rehearsal_env.committed_config, a no-op everywhere else); the PLAYTEST variant against the rehearsal
    # Config itself, i.e. the cave hub together with every other flag on.
    print('Default: ' + run(args.runner, rehearsal_env.committed_config(source), False))
    rewritten = source if rehearsal_env.ACTIVE else release_profiles.apply_profile(source, 'playtest')[0]
    print('Playtest: ' + run(args.runner, rewritten, True))
