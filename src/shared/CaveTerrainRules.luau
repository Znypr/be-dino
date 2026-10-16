--!strict
-- BD-281 / docs/104 s17 (owner 2026-10-16: organic cave, not a cube): the Cave shell as pure voxel rules (docs/104 s3). Given a voxel centre (x, y, z) in world studs it returns the
-- terrain material and occupancy, built only from CaveHubLayout (floor blob, ceiling, holes, stations, paths, pool, falls,
-- gate). Pure numbers only (no engine objects, no settings table): src/server/CaveTerrain.luau only writes what this module says, and
-- tools/verify_cave_terrain.py runs the same functions offline. Everything is PROVISIONAL (docs/104).
-- Shell = solid minus air. Air = the cavity (floor blob between floor top and ceiling) + the 4 ceiling holes (open to the
-- sky) + the lava basin + the falls recess + the gate mouth. Occupancy comes from a signed distance (studs, > 0 inside rock)
-- as clamp(sd / Res). Measured in Studio (BD-281 QA): the engine puts a flat top at (centre of the partial cell) + Res * occupancy, i.e. half
-- a cell ABOVE the naive 0.5 + sd / Res surface, so the old formula made the floor 2 studs too high (8 instead of 6) and every
-- wall, ceiling and hole 2 studs fatter. clamp(sd / Res) puts the floor exactly on the layout height.
local Layout = require(script.Parent.CaveHubLayout)
local Rules = {}
Rules.Version = 1
Rules.Res = 4 -- voxel size (the terrain resolution setting; asserted equal by the verifier)
-- Region the shell lives in (aligned to the grid, outside the island terrain which ends at z = 424).
Rules.XMin, Rules.XMax = -148, 148
Rules.YMin, Rules.YMax = -8, 84
Rules.ZMin, Rules.ZMax = 452, 708
Rules.ChunkSlices = 8 -- x slices per WriteVoxels call
Rules.YieldSlices = 2 -- x slices computed between two task.wait() calls
Rules.RoofThickness = 10
Rules.RockThickness = Layout.RockThickness -- plan distance the rock reaches beyond the open cave (>= 8 studs of rock everywhere)
Rules.CeilingRough = 2.5 -- ceiling relief, +-studs
Rules.PoolDepth = 2 -- lava basin floor below the hall floor
Rules.GateCut = 6 -- the gate mouth is cut this many studs beyond the cave wall (closed behind it)
Rules.GateHeight = 20
Rules.FallRecess = {halfWidth = 20, front = -1, back = 7} -- dz range around Layout.Fall.z carved behind the sheet
-- Cave-only colours (the island uses none of these three): warm stone floor and warm tan walls, so the hall reads soft and calm
-- (docs/87) instead of the island's dark teal Rock / Slate / Basalt. Island material colours are untouched.
-- BD-384 look pass: cooler, softer grey-lilac stone (the warm lamps and the cave grade carry the colour) instead of hot orange
-- cracked sandstone. Only Cobblestone, Limestone and CrackedLava are recoloured (terrain colours are place-wide, and the island uses
-- Sandstone, Slate, Rock and Basalt), so the walls and floor are built from those two only; the island palette is untouched.
Rules.Colors = {Cobblestone = {138, 132, 138}, Limestone = {160, 154, 158}, CrackedLava = {255, 120, 40}}
Rules.Materials = {"Air", "Rock", "Limestone", "Sandstone", "Slate", "Basalt", "Cobblestone", "Grass", "LeafyGrass", "CrackedLava"}

local FLOOR_BAND = 6 -- studs below the floor top that carry the floor surface mix
local BOTTOM = Rules.YMin - Rules.Res -- one cell lower so the bottom layer is full (occupancy = sd / Res)

local function clamp(v: number, lo: number, hi: number): number return if v < lo then lo elseif v > hi then hi else v end
local function noise01(x: number, z: number, scale: number, offset: number): number
    return clamp(0.5 + 0.85 * math.noise(x / scale, z / scale, offset), 0, 1)
end
local function relief(x: number, z: number, scale: number, offset: number): number
    return clamp(0.5 + 0.85 * (math.noise(x / scale, z / scale, offset) * 0.65 + math.noise(x / (scale * 0.37), z / (scale * 0.37), offset + 4.1) * 0.35), 0, 1)
end

-- Per-column constants (everything that does not depend on y).
function Rules.column(x: number, z: number): any
    local L = Layout.get()
    local cz = Layout.CenterZ
    local dz = z - cz
    local sd, dome = Layout.caveField(x, z)
    local floorTop = Layout.floorHeight(x, z)
    local ceil = Layout.FloorY + Layout.domeHeightAt(sd, dome) + (relief(x, z, 17, 9.7) - 0.5) * 2 * Rules.CeilingRough
    local col: any = {x = x, z = z, dz = dz, sd = sd, floorTop = floorTop, ceil = ceil,
        dIn = sd, dOut = Rules.RockThickness + sd, dome = dome,
        -- closed envelope: rock fills up to the room's full height + 12 over the whole shell, so a steep dome / tunnel mouth never thins to a sky gap
        roofTop = math.max(ceil + Rules.RoofThickness, Layout.FloorY + dome + Rules.RoofThickness + 2)}
    -- ceiling holes: horizontal inset (> 0 inside the shaft); open from just under the ceiling up through the roof
    local hole = -math.huge
    for _, h in L.holes do
        hole = math.max(hole, h.radius - math.sqrt((x - h.x) ^ 2 + (dz - h.z) ^ 2))
    end
    col.hole = hole
    -- rock ledges grown from the alcove walls (stone shelves in the stations): horizontal inset into the oriented box, > 0 inside
    local ledge = -math.huge
    for _, lg in L.ledges do
        local dx, dy = x - lg.x, dz - lg.z
        local c, s = math.cos(lg.yaw), math.sin(lg.yaw)
        local lx, lz = dx * c - dy * s, dx * s + dy * c
        ledge = math.max(ledge, math.min(lg.w / 2 - math.abs(lx), lg.d / 2 - math.abs(lz)))
        if ledge > 0 then col.ledgeTop = floorTop + lg.h end
    end
    col.ledge = ledge
    -- lava pool basin (carved below the floor) and the basalt rim around it
    local P = Layout.Pool
    local pd = math.sqrt((x - P.x) ^ 2 + (dz - P.z) ^ 2)
    col.poolDist = pd
    col.pool = P.r - pd
    -- falls recess behind the lava sheet (horizontal part) and the lava band painted on its rock
    local F, R = Layout.Fall, Rules.FallRecess
    col.fall = math.min(R.halfWidth - math.abs(x - F.x), dz - (F.z + R.front), (F.z + R.back) - dz, sd + 2) -- never more than 2 studs into the rock
    col.fallBand = math.abs(x - F.x) <= F.width / 2 and dz >= F.z + R.front - 1 and dz <= F.z + R.back + 6
    -- gate mouth: 30 wide, a half-ellipse arch, cut GateCut studs beyond the cave wall and closed behind
    local g = L.byId.gate
    local gx = math.abs(x - g.x)
    col.gateTop = Layout.FloorY + Rules.GateHeight * math.sqrt(math.max(0, 1 - (gx / (L.gate.mouthWidth / 2)) ^ 2))
    col.gate = math.min(L.gate.mouthWidth / 2 - gx, sd + Rules.GateCut, -(dz - (g.z - 10)))
    col.flat = Layout.flatDistance(x, z)
    return col
end

-- BD-384: the real (rough) ceiling surface height at a world (x, z): what stalactites hang from. Layout.ceilingY is the smooth ideal;
-- the shell's ceiling differs from it by up to +-CeilingRough studs, which made stalactites float.
function Rules.ceilingAt(x: number, z: number): number
    return Layout.ceilingY(x, z) + (relief(x, z, 17, 9.7) - 0.5) * 2 * Rules.CeilingRough
end

-- Signed distance to the air (> 0 inside air) at height y in a column.
local function airSd(col: any, y: number): number
    local air = math.min(col.dIn, y - col.floorTop, col.ceil - y)
    if col.hole > -math.huge then air = math.max(air, math.min(col.hole, y - (col.ceil - 4))) end
    local FY = Layout.FloorY
    air = math.max(air, math.min(col.pool, y - (FY - Rules.PoolDepth), FY + 3 - y))
    local F = Layout.Fall
    -- the recess never reaches the roof: at the back wall the ceiling is only 38 over the floor, below the 48 high sheet (QA: it opened a sky gap)
    air = math.max(air, math.min(col.fall, FY + F.height - 2 - y, col.ceil - 4 - y, y - FY))
    air = math.max(air, math.min(col.gate, col.gateTop - y, y - FY))
    return air
end

local function solidSd(col: any, y: number): number
    local sd = math.min(col.dOut, col.roofTop - y, y - BOTTOM, -airSd(col, y))
    if col.ledge > 0 then sd = math.max(sd, math.min(col.ledge, col.ledgeTop - y)) end -- the stone shelf stands in the air
    return sd
end

-- Material for a solid cell (occupancy > 0).
local function material(col: any, y: number, air: number): string
    local x, z = col.x, col.z
    local FY = Layout.FloorY
    -- lava: basin bottom and the vein behind the falls
    if col.poolDist <= Layout.Pool.r + 1.5 and y <= FY - 0.5 and y > FY - 6 then return "CrackedLava" end
    if col.fallBand and y >= FY and y <= math.min(FY + Layout.Fall.crackHeight, col.ceil - 3) and -air < 4 then return "CrackedLava" end
    local onFloor = col.dIn >= 0 and y < col.floorTop + 1 and y > col.floorTop - FLOOR_BAND
    if onFloor then
        if col.poolDist <= Layout.Pool.r + 4.5 then return "Basalt" end -- rim of the lava pool
        local v = relief(x, z, 6, 21.3)
        if col.flat <= 0.5 then
            -- paths and pads: laid stone, a little slate
            return if v < 0.72 then "Cobblestone" else "Slate"
        end
        local moss = relief(x, z, 14, 33.9)
        if col.flat > 2 and moss > 0.8 then return if moss > 0.9 then "LeafyGrass" else "Grass" end
        if v < 0.3 then return "Rock" elseif v < 0.58 then return "Limestone" end
        return "Cobblestone"
    end
    -- walls, ceiling, roof and deep rock
    if -air > 10 then return "Rock" end
    -- walls: soft blotches of three stones, no horizontal strata (owner 2026-10-16: no striped brick look). Cobblestone (tile grid) stays rare.
    local v = relief(x * 0.8 + y * 0.45, z * 0.8 - y * 0.45, 13, 12.9)
    local w = relief(x * 0.6 - y * 0.5, z * 0.6 + y * 0.35, 29, 41.7)
    if w > 0.8 then return "Cobblestone" end
    if v < 0.3 then return "Rock" end
    return "Limestone"
end

-- (material name, occupancy 0..1) for a cell given its column constants and the height of its centre.
function Rules.cellAt(col: any, y: number): (string, number)
    local sd = solidSd(col, y)
    local occ = clamp(sd / Rules.Res, 0, 1)
    if occ <= 0 then return "Air", 0 end
    return material(col, y, airSd(col, y)), occ
end
function Rules.cell(x: number, y: number, z: number): (string, number)
    return Rules.cellAt(Rules.column(x, z), y)
end

-- ---------------------------------------------------------------- write plan (budgets)
-- Cell centres of the region; the server writes chunks of ChunkSlices x slices and yields every YieldSlices slices.
function Rules.grid(): any
    local r = Rules.Res
    return {nx = (Rules.XMax - Rules.XMin) // r, ny = (Rules.YMax - Rules.YMin) // r, nz = (Rules.ZMax - Rules.ZMin) // r}
end
function Rules.plan(): any
    local g = Rules.grid()
    local chunks = {}
    local r = Rules.Res
    local first = 0
    while first < g.nx do
        local last = math.min(first + Rules.ChunkSlices, g.nx)
        chunks[#chunks + 1] = {minX = Rules.XMin + first * r, maxX = Rules.XMin + last * r, slices = last - first}
        first = last
    end
    return {chunks = chunks, cells = g.nx * g.ny * g.nz, cellsPerSlice = g.ny * g.nz, cellsPerChunk = Rules.ChunkSlices * g.ny * g.nz,
        cellsBetweenYields = Rules.YieldSlices * g.ny * g.nz, columnsPerSlice = g.nz, grid = g}
end

return Rules
