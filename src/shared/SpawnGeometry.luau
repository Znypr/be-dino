--!strict
-- BD-210: one place for every point a character is put into the world, and for "has it fallen out of the world".
-- Pure functions of Config + IslandLayout so the offline verifier (tools/verify_spawn.py) checks the same numbers the
-- server uses. The hub floor numbers mirror Arena.build (SanctuaryGround 110x6x95 at y=3, NestPlaza top at 6.5).
local SpawnGeometry = {}
SpawnGeometry.HubFloorY = 6 -- top of SanctuaryGround
SpawnGeometry.HubHalfX, SpawnGeometry.HubHalfZ = 55, 47.5 -- SanctuaryGround footprint
SpawnGeometry.DropClearance = 5 -- studs above the floor a character root is placed (it settles onto the floor)
SpawnGeometry.VoxelMargin = 3 -- the voxel surface reads up to ~2 studs above IslandLayout.height (4-stud voxels)
SpawnGeometry.TerrainBottom = -16 -- IslandTerrain fills voxels from y=-16 up to the surface
SpawnGeometry.FallDepth = 20 -- a root this far below the floor under it has fallen out of the world

function SpawnGeometry.inHub(config: any, x: number, z: number): boolean
    return math.abs(x) <= SpawnGeometry.HubHalfX and math.abs(z - config.SanctuaryCenterZ) <= SpawnGeometry.HubHalfZ
end
function SpawnGeometry.inTerrain(config: any, x: number, z: number): boolean
    local extent = config.ArenaHalfWidth + 8 -- IslandTerrain writes ArenaHalfWidth + 8
    return math.abs(x) <= extent and math.abs(z) <= extent
end
-- Expected solid floor height under (x, z); nil when nothing solid was ever built there.
function SpawnGeometry.floorY(config: any, layout: any, x: number, z: number): number?
    if SpawnGeometry.inHub(config, x, z) then return SpawnGeometry.HubFloorY end
    if SpawnGeometry.inTerrain(config, x, z) then return layout.height(x, z) end
    return nil
end
-- True when a root at `position` is below anything it could stand on (or over a void well below the map).
function SpawnGeometry.fallen(config: any, layout: any, position: Vector3): boolean
    local floor = SpawnGeometry.floorY(config, layout, position.X, position.Z)
    if floor then return position.Y < floor - SpawnGeometry.FallDepth end
    return position.Y < SpawnGeometry.TerrainBottom - SpawnGeometry.FallDepth
end
-- Hub arrival point (sanctuary centre, on the NestPlaza).
function SpawnGeometry.hubPoint(config: any): Vector3
    return Vector3.new(0, SpawnGeometry.HubFloorY + SpawnGeometry.DropClearance, config.SanctuaryCenterZ)
end
-- Island run-start point: on the meadow at SpawnZ, a few studs above the terrain surface.
function SpawnGeometry.islandPoint(layout: any): Vector3
    return Vector3.new(0, layout.height(0, layout.SpawnZ) + SpawnGeometry.DropClearance + SpawnGeometry.VoxelMargin, layout.SpawnZ)
end
-- Where a fallen character is put back: the hub outside a run, the island spawn during one.
function SpawnGeometry.recoveryPoint(config: any, layout: any, active: boolean): Vector3
    return if active then SpawnGeometry.islandPoint(layout) else SpawnGeometry.hubPoint(config)
end
return SpawnGeometry
