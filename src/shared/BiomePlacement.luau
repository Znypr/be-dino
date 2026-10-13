--!strict
-- BD-049 deterministic biome placement grammar (PROVISIONAL tuning). Pure math: no Instances,
-- so server colliders, client visuals and offline tests all derive the same layout from one seed.
-- Only used when Config.WorldArtMode == "BiomeKit"; the default "Legacy" keeps the current look.
local BiomePlacement = {}
BiomePlacement.Version = 1

-- Navigation corridors kept clear of blocking props (x,z polylines, half-width in studs).
BiomePlacement.Paths = {
    {width = 12, points = {{0, 30}, {-40, 8}, {-80, -15}, {-125, -100}}},
    {width = 12, points = {{0, 30}, {40, -30}, {110, -40}, {105, -80}}},
    {width = 10, points = {{0, 30}, {0, -180}}},
    {width = 10, points = {{0, 30}, {15, 190}, {0, 255}}},
    {width = 10, points = {{0, 30}, {-105, 80}, {-190, 15}}},
    {width = 10, points = {{0, 30}, {128, 102}, {182, 20}}},
}
-- Circles that stay clear: spawn meadow, legacy arch, spring, sanctuary approach.
BiomePlacement.KeepOuts = {
    {x = 0, z = 30, radius = 40, all = false},
    {x = 0, z = 30, radius = 16, all = true},
    {x = -80, z = -15, radius = 30, all = true},
    {x = 110, z = -40, radius = 24, all = true},
    {x = 0, z = 255, radius = 30, all = true},
}
-- Sanctuary hub footprint (outside the arena); nothing may intersect it.
BiomePlacement.Sanctuary = {minX = -55, maxX = 55, minZ = 317, maxZ = 413}
BiomePlacement.Groves = {{-105, 80}, {105, -80}, {-125, -100}, {128, 102}, {-190, 15}, {182, 20}, {0, -180}, {15, 190}}
BiomePlacement.Landmarks = {
    {id = "world_landmark_dino_statue", x = 60, z = 95},
    {id = "world_landmark_fossil_display", x = -60, z = 125},
    {id = "world_landmark_stone_arch", x = 150, z = -170},
    {id = "world_landmark_ruins_altar", x = -40, z = -120},
}
-- Layers: grid cell size, acceptance chance, slope limit (degrees), count cap, blocking.
BiomePlacement.Layers = {
    {name = "tree", cell = 15, chance = .2, groveBoost = .75, maxSlope = 32, cap = 40, blocking = true},
    {name = "rock", cell = 20, chance = .2, groveBoost = 0, maxSlope = 46, cap = 34, blocking = true},
    {name = "shrub", cell = 13, chance = .14, groveBoost = .45, maxSlope = 34, cap = 50, blocking = false},
    {name = "groundcover", cell = 11, chance = .1, groveBoost = .1, maxSlope = 30, cap = 70, blocking = false},
}
BiomePlacement.TriangleBudget = 9000 -- total placed triangles at density 1 (native fallback = 2 parts each)

local function mul32(a: number, b: number): number
    local lo, hi = a % 65536, math.floor(a / 65536)
    return (lo * b + ((hi * b) % 65536) * 65536) % 4294967296
end
function BiomePlacement.hash(...: number): number
    local h = 2166136261
    for i = 1, select("#", ...) do
        h = mul32(bit32.bxor(h, math.floor(select(i, ...)) % 4294967296), 16777619)
    end
    h = mul32(bit32.bxor(h, bit32.rshift(h, 15)), 2246822519)
    h = bit32.bxor(h, bit32.rshift(h, 13))
    return h / 4294967296
end

local function segmentDistance(px: number, pz: number, a: {number}, b: {number}): number
    local dx, dz = b[1] - a[1], b[2] - a[2]
    local t = math.clamp(((px - a[1]) * dx + (pz - a[2]) * dz) / (dx * dx + dz * dz), 0, 1)
    local x, z = a[1] + dx * t - px, a[2] + dz * t - pz
    return math.sqrt(x * x + z * z)
end
-- Clearance from (x,z) to the nearest corridor edge (negative = inside a path).
function BiomePlacement.pathClearance(x: number, z: number): number
    local best = math.huge
    for _, path in BiomePlacement.Paths do
        for i = 1, #path.points - 1 do
            best = math.min(best, segmentDistance(x, z, path.points[i], path.points[i + 1]) - path.width)
        end
    end
    return best
end
function BiomePlacement.keepOutClearance(x: number, z: number, blocking: boolean): number
    local best = math.huge
    for _, k in BiomePlacement.KeepOuts do
        if k.all or blocking then best = math.min(best, math.sqrt((x - k.x) ^ 2 + (z - k.z) ^ 2) - k.radius) end
    end
    return best
end
function BiomePlacement.slope(height: (number, number) -> number, x: number, z: number): number
    local gx = (height(x + 2, z) - height(x - 2, z)) / 4
    local gz = (height(x, z + 2) - height(x, z - 2)) / 4
    return math.deg(math.atan(math.sqrt(gx * gx + gz * gz)))
end
local function footprintRange(height: (number, number) -> number, x: number, z: number, r: number): (number, number)
    local lo, hi = height(x, z), height(x, z)
    for i = 0, 5 do
        local a = i * math.pi / 3
        local h = height(x + math.cos(a) * r, z + math.sin(a) * r)
        lo, hi = math.min(lo, h), math.max(hi, h)
    end
    return lo, hi
end

-- Family choice by elevation / wetness (distance to the spring) / noise.
local function chooseTree(h: number, wet: number, n: number, sizeRoll: number): string
    local family = if h > 34 then (if n < .25 then "dead" else "conifer")
        elseif wet > .5 or h < 4 then (if n < .55 then "cycad" else "canopy")
        elseif n < .08 then "dead" elseif n < .55 then "canopy" else "conifer"
    local size = if sizeRoll < .3 then "s" elseif sizeRoll < .78 then "m" else "l"
    return "world_tree_" .. family .. "_" .. size
end
local function chooseRock(h: number, s: number, wet: number, n: number, sizeRoll: number): string
    if s > 24 and h > 25 and n < .18 then return if n < .09 then "world_rocks_spires" else "world_rocks_ledge" end
    local kind = if wet > .3 or h < 15 then "mossy" else "bare"
    local size = if sizeRoll < .45 then "s" elseif sizeRoll < .85 then "m" else "l"
    return "world_boulder_" .. kind .. "_" .. size
end
local function chooseShrub(wet: number, n: number, nearGrove: boolean): string
    if wet > .4 and n < .35 then return "world_horsetail_a" end
    if nearGrove and n < .12 then return "world_mushrooms_a" end
    if n < .5 then return if n < .3 then "world_fern_a" else "world_fern_b" end
    return if n < .75 then "world_bush_a" else "world_bush_b"
end
local function chooseCover(n: number): string
    return if n < .45 then "world_grass_a" elseif n < .75 then "world_grass_b" else "world_flowers_a"
end

export type Placement = {id: string, x: number, y: number, z: number, yaw: number, scale: number, radius: number, layer: string}

-- options: {seed, density, extent, height=(x,z)->y, kit=WorldKitData}
function BiomePlacement.generate(options): {Placement}
    local seed, density, extent, height, kit = options.seed, math.clamp(options.density or 1, .25, 2), options.extent - 12, options.height, options.kit
    local placed: {Placement} = {}
    local triangles = 0
    local budget = BiomePlacement.TriangleBudget * density
    local grid: {[number]: {Placement}} = {}
    local function key(x: number, z: number): number return math.floor(x / 24) * 4096 + math.floor(z / 24) end
    local function clear(x: number, z: number, r: number, blocking: boolean): boolean
        local gx, gz = math.floor(x / 24), math.floor(z / 24)
        for ix = gx - 1, gx + 1 do
            for iz = gz - 1, gz + 1 do
                for _, p in grid[ix * 4096 + iz] or {} do
                    local need = if blocking or p.layer == "tree" or p.layer == "rock" or p.layer == "landmark" then r + p.radius else (r + p.radius) * .6
                    if (p.x - x) ^ 2 + (p.z - z) ^ 2 < need * need then return false end
                end
            end
        end
        return true
    end
    local function add(id: string, x: number, z: number, yaw: number, scale: number, layer: string, sink: number)
        local data = kit[id]
        local r = math.max(data.extent[1], data.extent[3]) * .5 * scale * (if layer == "tree" then .45 else .8)
        local lo = footprintRange(height, x, z, r * .5)
        local p = {id = id, x = x, y = lo - sink * data.extent[2] * scale, z = z, yaw = yaw, scale = scale, radius = r, layer = layer}
        table.insert(placed, p)
        triangles += data.triangles
        local k = key(x, z)
        grid[k] = grid[k] or {}
        table.insert(grid[k], p)
    end
    for i, site in BiomePlacement.Landmarks do
        local data = kit[site.id]
        local r = math.max(data.extent[1], data.extent[3]) * .5
        local best, bx, bz = math.huge, site.x, site.z
        for step = 0, 24 do -- search a small spiral for the flattest footprint
            local a, d = step * 2.4, math.sqrt(step) * 6
            local x, z = site.x + math.cos(a) * d, site.z + math.sin(a) * d
            local lo, hi = footprintRange(height, x, z, r)
            local score = hi - lo
            if score < best and BiomePlacement.pathClearance(x, z) > r * .6 and BiomePlacement.keepOutClearance(x, z, true) > r then best, bx, bz = score, x, z end
        end
        add(site.id, bx, bz, BiomePlacement.hash(seed, 99, i) * math.pi * 2, 1, "landmark", .04)
    end
    for li, layer in BiomePlacement.Layers do
        local count, cap = 0, math.floor(layer.cap * density)
        local cells = math.floor(2 * extent / layer.cell)
        -- Visit cells in a seeded shuffled order so count caps thin the whole map evenly.
        local order = {}
        for ix = 0, cells - 1 do for iz = 0, cells - 1 do table.insert(order, {ix, iz, BiomePlacement.hash(seed, li, ix, iz, 8)}) end end
        table.sort(order, function(p, q) return p[3] < q[3] end)
        for _, cell in order do
            local ix, iz = cell[1], cell[2]
            do
                if count >= cap then break end
                local x = -extent + (ix + BiomePlacement.hash(seed, li, ix, iz, 1)) * layer.cell
                local z = -extent + (iz + BiomePlacement.hash(seed, li, ix, iz, 2)) * layer.cell
                local grove = math.huge
                for _, g in BiomePlacement.Groves do grove = math.min(grove, math.sqrt((x - g[1]) ^ 2 + (z - g[2]) ^ 2)) end
                local chance = (layer.chance + layer.groveBoost * math.exp(-(grove / 22) ^ 2)) * density
                if BiomePlacement.hash(seed, li, ix, iz, 3) > chance then continue end
                local h = height(x, z)
                local s = BiomePlacement.slope(height, x, z)
                if s > layer.maxSlope then continue end
                local wet = math.exp(-(((x - 110) ^ 2 + (z + 40) ^ 2) / 6000)) + (if h < 3 then .3 else 0)
                local n = BiomePlacement.hash(seed, li, ix, iz, 4)
                local roll = BiomePlacement.hash(seed, li, ix, iz, 5)
                local id = if layer.name == "tree" then chooseTree(h, wet, n, roll + (if grove < 15 then .2 else 0))
                    elseif layer.name == "rock" then chooseRock(h, s, wet, n, roll)
                    elseif layer.name == "shrub" then chooseShrub(wet, n, grove < 25) else chooseCover(n)
                local data = kit[id]
                if not data or triangles + data.triangles > budget then continue end
                local scale = .88 + .24 * BiomePlacement.hash(seed, li, ix, iz, 6)
                local r = math.max(data.extent[1], data.extent[3]) * .5 * scale
                local needed = if layer.blocking then r * .7 else 1
                if BiomePlacement.pathClearance(x, z) < needed or BiomePlacement.keepOutClearance(x, z, layer.blocking) < r * .5 then continue end
                if math.max(math.abs(x), math.abs(z)) + r > extent then continue end
                if not clear(x, z, r * (if layer.name == "tree" then .45 else .8), layer.blocking) then continue end
                local sink = if layer.name == "rock" then .12 elseif layer.name == "tree" then .03 else .02
                add(id, x, z, BiomePlacement.hash(seed, li, ix, iz, 7) * math.pi * 2, scale, layer.name, sink)
                count += 1
            end
        end
    end
    return placed
end

function BiomePlacement.triangles(placed: {Placement}, kit): number
    local total = 0
    for _, p in placed do total += kit[p.id].triangles end
    return total
end
return BiomePlacement
