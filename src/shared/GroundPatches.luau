--!strict
-- BD-1320 (docs/251 s5 + s8, owner 2026-11-24 "Yes, start BD-1320"): ground variation on the World V3 island, terrain only (0 parts).
-- The island read as "one flat neon-green ground" (docs/251 s2.2 #1). Nature does not look like that: soil is worn bare where paths meet
-- and at the clearings the paths end in, the floor under a grove is bare earth in deeper shade, and rock shows on steep slopes. Four masks, each a soft noise-warped blob (never a one-voxel spot: the lead review of #623 rejected thin
-- brown rims as hard voxel hexagons), painted with the island's own materials (Ground, LeafyGrass, Rock). The biome rotation (BD-1314,
-- BiomeRotation.Terrain) recolours those materials, so the same patches turn into terracotta soil in the desert, grey frozen earth in the
-- tundra and dark ash in the volcano with no extra work.
-- Pure math, no Instances. Called by IslandTerrain only with Config.GroundDetailEnabled (BD-1245, playtest profile), after the World V3
-- fixed surfaces (plaza, paths, beach) and before the BD-1245 grass blotches. nil = keep what the other rules pick.
local GroundPatches = {}

-- Worn soil: where a spoke meets the ring road and at the clearing each spoke ends in (radius in studs, before the edge noise).
GroundPatches.Worn = {junction = 22, spokeEnd = 24}
-- Forest floor under the grove cores of these zones (radius in studs) and the material of the core.
GroundPatches.Floor = {forest = {r = 24, core = "Ground"}, pine = {r = 20, core = "Ground"}, meadow = {r = 13, core = "Ground"}}
-- (No beach fingers: the World V3 beach band already reaches the grass; a finger mask measured 2 patches on the whole island, 2026-11-24.)
-- Slope rock: gradient (rise per stud) above which rock shows through, scaled by noise. BiomeMap already puts rock above 1.05.
GroundPatches.RockSlope = .76
-- Zones whose grass these masks may change (the beach and the volcano keep their own World V3 rules).
GroundPatches.Zones = {meadow = true, forest = true, pine = true}

local function smoothstep(a: number, b: number, x: number): number
    local t = math.clamp((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
end

-- Edge noise for a blob: two broad octaves (no fine octave: it breaks the edge into one-voxel spots), about -1..1. Different `salt` per mask so the blobs never share a shape.
local function edge(x: number, z: number, salt: number): number
    return math.noise(x / 13, z / 13, salt) * .8 + math.noise(x / 6.5, z / 6.5, salt + 1.3) * .2
end

-- Blob strength 0..1 at distance d from a centre of radius r (the edge wanders by `wobble` of r, default 35 %).
local function blob(d: number, r: number, x: number, z: number, salt: number, wobble: number?): number
    local reach = r * (1 + (wobble or .35) * edge(x, z, salt))
    return 1 - smoothstep(reach * .8, reach, d)
end

-- Centres of the worn patches: {x, z, r}. Built once per V3 (the layout is fixed data).
local wornCache: {[any]: {{number}}} = {}
function GroundPatches.wornCentres(V3: any): {{number}}
    local cached = wornCache[V3]
    if cached then return cached end
    local out = {}
    for _, spoke in V3.Spokes do
        if spoke.to > V3.RingRadius + 10 then
            local x, z = V3.polar(spoke.angle, V3.RingRadius)
            table.insert(out, {x, z, GroundPatches.Worn.junction})
        end
        local ex, ez = V3.polar(spoke.angle, spoke.to - 6)
        table.insert(out, {ex, ez, GroundPatches.Worn.spokeEnd})
    end
    wornCache[V3] = out
    return out
end

-- Grove centres in the floor zones: {x, z, zoneId}.
local groveCache: {[any]: {{any}}} = {}
function GroundPatches.groveCentres(V3: any): {{any}}
    local cached = groveCache[V3]
    if cached then return cached end
    local out = {}
    for _, g in V3.Groves do
        local x, z = V3.polar(g[1], g[2])
        local zone = V3.zoneAt(x, z).id
        if GroundPatches.Floor[zone] then table.insert(out, {x, z, zone}) end
    end
    groveCache[V3] = out
    return out
end

-- Which mask a land column falls in ("rock", "worn", "floor", "shade") and the material, or nil. h = terrain height, slope = gradient,
-- picked = what the biome bands chose. Only grass columns of the meadow, forest and pine zones change, never the plaza or a path.
function GroundPatches.surface(V3: any, x: number, z: number, h: number, slope: number, picked: string): (string?, string?)
    if picked ~= "Grass" and picked ~= "LeafyGrass" then return nil, nil end
    if V3.inland(x, z) <= 0 or V3.inPlaza(x, z) or V3.path(x, z) > .5 then return nil, nil end
    local zone = V3.zoneAt(x, z).id
    if not GroundPatches.Zones[zone] then return nil, nil end
    -- 1. rock through the grass on steep slopes: the slope is measured over a wide footprint (+-8 studs) so the rock follows whole
    --    hillsides, not single steep voxels (no specks)
    local wide = (math.abs(V3.height(x + 8, z) - V3.height(x - 8, z)) + math.abs(V3.height(x, z + 8) - V3.height(x, z - 8))) / 16
    if wide > GroundPatches.RockSlope then -- no noise on the threshold: noise breaks the slope band into specks
        return "Rock", "rock"
    end
    if h > 30 then return nil, nil end -- soil only on the low ground (rock above runs up the whole hillside, no cut at a contour)
    -- 2. worn soil where paths meet and at the spoke-end clearings
    for i, c in GroundPatches.wornCentres(V3) do
        local dx, dz = x - c[1], z - c[2]
        if blob(math.sqrt(dx * dx + dz * dz), c[3], x, z, 55 + i, .2) > .5 then return "Ground", "worn" end -- calmer edge: the paths already cut it
    end
    -- 3. grove floor: bare earth in the core, a ring of the deeper green around it
    for i, g in GroundPatches.groveCentres(V3) do
        local spec = GroundPatches.Floor[g[3]]
        local dx, dz = x - g[1], z - g[2]
        local d = math.sqrt(dx * dx + dz * dz)
        if blob(d, spec.r * .6, x, z, 71 + i) > .5 then return spec.core, "floor" end
        -- the shade ring: deeper green around the bare core (only where the pick is the light green)
        if picked == "Grass" and blob(d, spec.r * 1.25, x, z, 91 + i) > .5 then return "LeafyGrass", "shade" end
    end
    return nil, nil
end

return GroundPatches
