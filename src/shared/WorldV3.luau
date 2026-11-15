--!strict
-- BD-1208 world redesign, step 1 (docs/241 W1-W3): a round island with a beach and soft cliffs, one spawn plaza in the middle,
-- five spoke paths and a ring road, and five readable zones around the plaza (meadow, broadleaf forest, pine hill, palm beach with
-- a lagoon, volcano corner). Pure math, no Instances: IslandLayout and BiomeMap switch to these functions while
-- Config.WorldV3Enabled is true, so the terrain painter, the prop grammar, food, spawn and NPCs all read the same island.
-- Every number is PROVISIONAL (LEAD, docs/241 s4); the plan picture is docs/evidence/2026-11-15-world/map-plan-v1.png.
local WorldV3 = {}
WorldV3.Version = 1
WorldV3.CenterX, WorldV3.CenterZ = 0, 30 -- the spawn plaza (IslandLayout.SpawnZ)
WorldV3.CoastRadius = 352 -- mean coast radius; the arena boundary square is 416, so the corners and edges are sea
WorldV3.PlazaRadius = 72
WorldV3.RingRadius = 205
WorldV3.PathHalfWidth = 7
WorldV3.SeaLevel = 0

-- Zones are angular sectors around the plaza (degrees, atan2(z - 30, x), the plan's layout). biome = the existing prop grammar id.
WorldV3.Zones = {
    {id = "meadow", name = "Flower Meadow", biome = "meadow", from = -60, to = 30},
    {id = "forest", name = "Broadleaf Forest", biome = "fern", from = 30, to = 110},
    {id = "pine", name = "Pine Hill", biome = "conifer", from = 110, to = 180},
    {id = "beach", name = "Palm Beach", biome = "badlands", from = 180, to = 250},
    {id = "volcano", name = "Volcano Corner", biome = "volcanic", from = 250, to = 300},
}
-- Spoke paths from the plaza: angle and the radius where each ends (short where it meets the volcano or the pine hill).
WorldV3.Spokes = {
    {angle = -15, to = 320}, {angle = 70, to = 315}, {angle = 145, to = 200}, {angle = 215, to = 300}, {angle = 275, to = 165},
}
-- Landmark sites (W4; the models arrive in step 3). r = distance from the plaza centre.
WorldV3.Landmarks = {
    {id = "giant_tree", zone = "forest", angle = 70, r = 262},
    {id = "waterfall", zone = "pine", angle = 150, r = 262},
    {id = "lagoon_arch", zone = "beach", angle = 215, r = 262},
    {id = "volcano", zone = "volcano", angle = 275, r = 268},
    {id = "fossil_statue", zone = "meadow", angle = -35, r = 262},
}
local function polar(angle: number, r: number): (number, number)
    local a = math.rad(angle)
    return WorldV3.CenterX + math.cos(a) * r, WorldV3.CenterZ + math.sin(a) * r
end
WorldV3.polar = polar
local PINE_X, PINE_Z = polar(148, 278)
local VOLCANO_X, VOLCANO_Z = polar(275, 300)
local LAGOON_X, LAGOON_Z = polar(212, 285)
-- The lagoon is a flat water disc like the old pools (decorative water; food and NPCs keep out of it).
WorldV3.Pools = {{x = LAGOON_X, z = LAGOON_Z, rx = 48, rz = 36, level = -.6}}

local function smoothstep(a: number, b: number, x: number): number
    local t = math.clamp((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
end
local function lerp(a: number, b: number, t: number): number return a + (b - a) * t end
local function angleOf(x: number, z: number): number
    return math.deg(math.atan2(z - WorldV3.CenterZ, x - WorldV3.CenterX))
end
-- Angular distance in degrees, wrapped to [0, 180].
local function angDist(a: number, b: number): number
    return math.abs((a - b + 540) % 360 - 180)
end

-- Coast radius for an angle (degrees): a rounded shape with two slow wobbles, never a square edge (W1).
function WorldV3.coast(angle: number): number
    local a = math.rad(angle)
    return WorldV3.CoastRadius + 20 * math.sin(a * 3 + .4) + 12 * math.cos(a * 5 + 1.1) + 6 * math.sin(a * 9 + 2.3)
end

-- Which zone sector an angle falls into, with a noisy border so the sectors never meet on a straight line.
function WorldV3.zoneAt(x: number, z: number): any
    local warp = math.noise(x / 90, z / 90, 31.7) * 16
    local a = angleOf(x, z) + warp
    for _, zone in WorldV3.Zones do
        if angDist(a, (zone.from + zone.to) / 2) <= (zone.to - zone.from) / 2 then return zone end
    end
    return WorldV3.Zones[1] -- the meadow covers the gap between the volcano (300) and its own start (-60 = 300)
end

-- 0..1: how much of (x, z) is path (spokes + ring road + plaza rim), soft-edged.
function WorldV3.path(x: number, z: number): number
    local dx, dz = x - WorldV3.CenterX, z - WorldV3.CenterZ
    local r = math.sqrt(dx * dx + dz * dz)
    local w = WorldV3.PathHalfWidth + math.noise(x / 40, z / 40, 7.3) * 1.5
    local best = 1 - smoothstep(w - 2, w + 2, math.abs(r - WorldV3.RingRadius))
    for _, spoke in WorldV3.Spokes do
        local a = math.rad(spoke.angle)
        local ux, uz = math.cos(a), math.sin(a)
        local along = dx * ux + dz * uz
        if along > WorldV3.PlazaRadius - 6 and along < spoke.to then
            local across = math.abs(-dx * uz + dz * ux)
            -- the path widens a little at its outer end (a small clearing)
            local width = w + smoothstep(spoke.to - 30, spoke.to, along) * 5
            best = math.max(best, 1 - smoothstep(width - 2, width + 2, across))
        end
    end
    return best
end

-- True on the paved plaza (W2).
function WorldV3.inPlaza(x: number, z: number): boolean
    local dx, dz = x - WorldV3.CenterX, z - WorldV3.CenterZ
    return dx * dx + dz * dz < WorldV3.PlazaRadius * WorldV3.PlazaRadius
end

-- Signed distance inland from the coast (negative = sea).
function WorldV3.inland(x: number, z: number): number
    local dx, dz = x - WorldV3.CenterX, z - WorldV3.CenterZ
    return WorldV3.coast(angleOf(x, z)) - math.sqrt(dx * dx + dz * dz)
end

-- Land height before the coast and the plaza shape it (zone relief + gentle roll).
local function landHeight(x: number, z: number): number
    local h = 3 + math.noise(x / 70, z / 70, 14) * 2.2 + math.noise(x / 23, z / 23, 15) * .6
    local relief = 0
    -- Pine hill: one broad hill the conifers climb (soft cliff to the sea on its outer side).
    local dp = math.sqrt((x - PINE_X) ^ 2 + (z - PINE_Z) ^ 2)
    relief += 42 * math.exp(-(dp / 100) ^ 2 * 1.4)
    -- Volcano: a cone with a shallow crater, readable from everywhere (W4).
    local dv = math.sqrt((x - VOLCANO_X) ^ 2 + (z - VOLCANO_Z) ^ 2)
    relief += 82 * math.max(0, 1 - dv / 122) ^ 1.5
    if dv < 18 then relief -= (18 - dv) * 1.2 end
    -- Broadleaf forest: two soft hills.
    for _, hill in {{70, 175, 11, 70}, {98, 295, 9, 60}} do
        local hx, hz = polar(hill[1], hill[2])
        relief += hill[3] * math.exp(-(((x - hx) ^ 2 + (z - hz) ^ 2) / hill[4] ^ 2) * 1.5)
    end
    -- The ring road cuts a gentle pass where it meets a hill's foot.
    local r = math.sqrt((x - WorldV3.CenterX) ^ 2 + (z - WorldV3.CenterZ) ^ 2)
    h += relief * (1 - .85 * (1 - smoothstep(9, 34, math.abs(r - WorldV3.RingRadius))))
    -- Palm beach: low and flat, with the lagoon basin.
    local zone = WorldV3.zoneAt(x, z)
    if zone.id == "beach" then h = lerp(h, 1.6, .6) end
    local dl = ((x - LAGOON_X) / 54) ^ 2 + ((z - LAGOON_Z) / 44) ^ 2
    h -= 7.5 * math.exp(-dl * 1.4)
    return h
end

function WorldV3.height(x: number, z: number): number
    local c = WorldV3.inland(x, z)
    if c < 0 then return math.max(-6, .4 + c * .22) end -- shallow sea shelf: wade-able near the beach, deeper further out
    local a = angleOf(x, z)
    -- Soft cliffs where the pine hill and the volcano meet the sea; wide beaches elsewhere.
    local cliffy = math.max(1 - smoothstep(25, 45, angDist(a, 145)), 1 - smoothstep(20, 40, angDist(a, 275)))
    local beach = lerp(42, 12, cliffy)
    local h = landHeight(x, z)
    if c < beach then
        h = lerp(.4, 1.3, c / beach)
    else
        h = lerp(1.3, h, smoothstep(beach, beach + lerp(40, 16, cliffy), c))
    end
    -- Flat plaza with a soft lip into the meadow.
    local dx, dz = x - WorldV3.CenterX, z - WorldV3.CenterZ
    local r = math.sqrt(dx * dx + dz * dz)
    h = lerp(1.6, h, smoothstep(WorldV3.PlazaRadius - 4, WorldV3.PlazaRadius + 38, r))
    -- Paths stay walkable: they lose the small bumps (not the hills).
    local p = WorldV3.path(x, z)
    if p > 0 then h -= math.noise(x / 23, z / 23, 15) * .6 * p end
    return h
end

function WorldV3.inPool(x: number, z: number, margin: number): boolean
    if WorldV3.inland(x, z) < 10 + margin then return true end -- the sea and the wet edge of the beach
    for _, pool in WorldV3.Pools do
        local dx, dz = (x - pool.x) / (pool.rx + margin), (z - pool.z) / (pool.rz + margin)
        if dx * dx + dz * dz < 1 then return true end
    end
    return false
end
function WorldV3.poolProximity(x: number, z: number): number
    local pool = WorldV3.Pools[1]
    local dx, dz = (x - pool.x) / pool.rx, (z - pool.z) / pool.rz
    local d = math.sqrt(dx * dx + dz * dz) * math.min(pool.rx, pool.rz)
    return math.clamp(1 - (d - math.min(pool.rx, pool.rz)) / 30, 0, 1)
end

-- BiomeMap.weights replacement: per-biome weights (sum 1) and the dominant biome; the sector borders blend over ~30 degrees.
local ORDER = {"meadow", "fern", "conifer", "marsh", "badlands", "volcanic"}
function WorldV3.weights(x: number, z: number, h: number, _seed: number): ({[string]: number}, string)
    local s = {meadow = 0, fern = 0, conifer = 0, marsh = 0, badlands = 0, volcanic = 0}
    local warp = math.noise(x / 90, z / 90, 31.7) * 16
    local a = angleOf(x, z) + warp
    for _, zone in WorldV3.Zones do
        local half = (zone.to - zone.from) / 2
        local d = angDist(a, (zone.from + zone.to) / 2) - half
        s[zone.biome] = math.max(s[zone.biome], 1 - smoothstep(-12, 14, d))
    end
    -- The meadow also wraps the plaza, and the beach ring belongs to the beach biome everywhere.
    local dx, dz = x - WorldV3.CenterX, z - WorldV3.CenterZ
    local r = math.sqrt(dx * dx + dz * dz)
    s.meadow = math.max(s.meadow, 1 - smoothstep(WorldV3.PlazaRadius + 20, WorldV3.PlazaRadius + 70, r))
    local c = WorldV3.inland(x, z)
    s.badlands = math.max(s.badlands, 1 - smoothstep(10, 34, c))
    if h > 30 then s.conifer = math.max(s.conifer, s.fern) s.fern = 0 end
    local total, best, bestW = 0, "meadow", -1
    for _, id in ORDER do total += s[id] end
    if total <= 1e-9 then s.meadow, total = 1, 1 end
    for _, id in ORDER do
        s[id] /= total
        if s[id] > bestW then best, bestW = id, s[id] end
    end
    return s, best
end

-- Terrain surface override: plaza, paths, beach and sea floor (nil = let the biome bands pick).
function WorldV3.surface(x: number, z: number, h: number): string?
    if WorldV3.inPlaza(x, z) then return "Limestone" end
    if WorldV3.path(x, z) > .5 and h < 30 then return "Limestone" end
    local c = WorldV3.inland(x, z)
    if c < 0 or (c < 30 and h < 2.4) then return "Sand" end
    -- Palm beach inland: sunny grass with sandy patches (not a desert).
    if WorldV3.zoneAt(x, z).id == "beach" then
        return if math.noise(x / 26, z / 26, 4.4) > .12 then "Sand" else "Grass"
    end
    return nil
end
-- The path/plaza colour (Limestone is unused elsewhere on the island) and a lighter beach sand.
WorldV3.Colors = {Limestone = {226, 204, 150}, Sand = {232, 212, 160}}
return WorldV3
