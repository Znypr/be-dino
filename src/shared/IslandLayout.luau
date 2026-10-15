--!strict
-- Authored broad ramps and mountain masses; the center remains a readable chase meadow.
-- World v2: the island is Scale (1.6x) wider than the 520x520 playtest map. Authored footprints (radii, meadow,
-- edge ramp) scale with it so the climb angles only get gentler; heights stay the same except for added rolling
-- hills and marsh basins that give the sub-biomes (BiomeMap) different relief.
local IslandLayout = {}
IslandLayout.Scale = 1.6
IslandLayout.SpawnZ = 30
local S = IslandLayout.Scale
IslandLayout.Peaks = {
    {x = -145 * S, z = -140 * S, height = 65, radius = 90 * S},
    {x = 145 * S, z = -130 * S, height = 80, radius = 105 * S},
    {x = -165 * S, z = 125 * S, height = 46, radius = 82 * S},
    {x = 160 * S, z = 140 * S, height = 58, radius = 95 * S},
}
-- Gentle rolling hills in the lowlands (relief for the fern forest and meadows).
IslandLayout.Hills = {
    {x = -120, z = 150, height = 11, radius = 80},
    {x = 90, z = 215, height = 13, radius = 85},
    {x = -80, z = -165, height = 12, radius = 75},
    {x = 330, z = 20, height = 10, radius = 70},
    {x = -345, z = -20, height = 9, radius = 70},
    {x = 10, z = -330, height = 12, radius = 85},
    {x = 215, z = 330, height = 9, radius = 60},
    {x = -250, z = 340, height = 10, radius = 65},
}
-- Marsh basins dip below sea level; flat water discs (Pools) fill them. level is the absolute water surface.
IslandLayout.Basins = {
    {x = 176, z = -64, radius = 46, depth = 1.2},
    {x = 150, z = 70, radius = 60, depth = 3.4},
    {x = -45, z = 305, radius = 66, depth = 3.6},
    {x = -330, z = 40, radius = 44, depth = 2.8},
}
IslandLayout.Pools = {
    {x = 176, z = -64, rx = 26, rz = 21, level = nil, spring = true},
    {x = 150, z = 70, rx = 40, rz = 32, level = -.9},
    {x = 112, z = 38, rx = 17, rz = 13, level = -.9},
    {x = -45, z = 305, rx = 46, rz = 38, level = -1},
    {x = -78, z = 330, rx = 20, rz = 15, level = -1},
    {x = -330, z = 40, rx = 30, rz = 24, level = -.9},
}
-- Pools whose water level follows the ground (the old decorative spring).
function IslandLayout.waterLevel(pool: any): number
    return pool.level or (IslandLayout.height(pool.x, pool.z) + .2)
end
-- True when (x,z) is inside a pool grown by margin studs (elliptical test).
function IslandLayout.inPool(x: number, z: number, margin: number): boolean
    for _, pool in IslandLayout.Pools do
        local dx, dz = (x - pool.x) / (pool.rx + margin), (z - pool.z) / (pool.rz + margin)
        if dx * dx + dz * dz < 1 then return true end
    end
    return false
end
-- Distance-ish wetness (1 at the rim of the nearest pool, falling to 0 about 30 studs away).
function IslandLayout.poolProximity(x: number, z: number): number
    local best = 0
    for _, pool in IslandLayout.Pools do
        local dx, dz = (x - pool.x) / pool.rx, (z - pool.z) / pool.rz
        local d = math.sqrt(dx * dx + dz * dz) * math.min(pool.rx, pool.rz)
        best = math.max(best, math.clamp(1 - (d - math.min(pool.rx, pool.rz)) / 30, 0, 1))
    end
    return best
end

function IslandLayout.height(x: number, z: number): number
    local h = 0
    for _, peak in IslandLayout.Peaks do
        local r2 = ((x-peak.x)^2 + (z-peak.z)^2) / peak.radius^2
        h += peak.height * math.exp(-r2 * 1.6)
    end
    for _, hill in IslandLayout.Hills do
        local r2 = ((x-hill.x)^2 + (z-hill.z)^2) / hill.radius^2
        h += hill.height * math.exp(-r2 * 1.5)
    end
    local meadow = math.exp(-(x*x + (z-IslandLayout.SpawnZ)^2) / (5000 * S * S))
    h *= 1 - meadow * .95
    local edge = math.max(math.abs(x), math.abs(z))
    h += math.max(0, edge - 190 * S) * .55 / S
    for _, basin in IslandLayout.Basins do
        local r2 = ((x-basin.x)^2 + (z-basin.z)^2) / basin.radius^2
        h -= basin.depth * math.exp(-r2 * 1.8)
    end
    -- Two octaves: broad undulation plus a small bump so open ground never reads as a flat plate.
    local wobble = (math.noise(x / (65 * S), z / (65 * S), 14) * 2.4 + math.noise(x / 23, z / 23, 15) * .7) * (1 - meadow * .8)
    return h + wobble
end
return IslandLayout
