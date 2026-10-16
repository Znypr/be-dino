--!strict
-- BD-049 deterministic biome placement grammar, world v2 (PROVISIONAL tuning). Pure math: no Instances, so server
-- colliders and offline tests derive the same layout from one seed. Only used when Config.WorldArtMode == "BiomeKit";
-- the default "Legacy" keeps the old look.
-- v2: the island is 1.6x wider (IslandLayout.Scale); sub-biomes (BiomeMap) pick which kit ids grow where, with
-- six layers: tree, giant (the same meshes at 2.4x-4x so late-game dinos still feel small), fallen log (a dead tree on its
-- side), rock, shrub (understory) and groundcover (clustered tufts and flower meadows, never a grid).
local BiomePlacement = {}
BiomePlacement.Version = 2
-- BD-395 PropGround (bottom-on-terrain rule) lives in this file so every offline tool that wraps BiomePlacement gets it.
-- where a world prop's BOTTOM sits on the terrain. Pure math (no Instances): BiomePlacement uses it for the analytic
-- layout height, Arena uses the same rule with Terrain raycast samples, and tools/verify_world_art.py checks both.
-- Every generated prop mesh (Arena.generatedProp) has its pivot at the BOTTOM CENTRE of the mesh bounding box (the clone is
-- CFrame(0, Size.Y / 2, 0)), so a prop rests on the ground when its pivot y = the highest terrain point under the trunk
-- footprint + Clearance. The old rule used the LOWEST footprint point minus 3% of the prop height, which buried the uphill
-- side of trees and the base of giants (scale 2.4x-4x, so up to ~2.3 studs) in the slope.
local PropGround = {}
PropGround.Clearance = 0.2 -- studs the bottom sits above the highest terrain sample under the trunk
-- Layers that must never be buried (the rest embed on purpose: rocks sink a little, logs lie on the ground).
PropGround.Raised = {tree = true, giant = true, shrub = true, groundcover = true}
-- Bottom offset of the pivot from the mesh bounding-box bottom, per prop kind (studs, before scale). 0 = pivot is the bottom.
-- Rocks embed by a fraction of their height instead (BiomePlacement sink .12).
PropGround.BottomOffset = {tree = 0, shrub = 0, groundcover = 0, rock = 0, landmark = 0}
PropGround.RockSink = 0.12
-- BD-416/417 (raycast placement, Arena): per-kind sampling policy. ONE footprint rule is shared with tools/qa/ground_probe so the gate
-- grades what the placement used. Rationale per kind:
--   plants (tree, giant, shrub, groundcover): the HIGHEST of the 5 rays at the stem footprint, minus RootSink, so the roots meet the
--     ground on the uphill side and nothing floats (a plant buried 0.15 stud is invisible; a floating one is not).
--   rocks, spires, ledges, landmarks: the LOWEST of the 5 rays at the WHOLE base (footprint 30% of the mesh, max 6 studs), minus the
--     RockSink embed for rocks, so a tall pillar never hangs on its downhill side; the embed hides the uphill side.
--   tall props (spires, ledges) are not placed on slopes steeper than TallMaxSlope degrees (BiomePlacement rock choice).
PropGround.RootSink = 0.15
PropGround.TallMaxSlope = 25
PropGround.Policy = {plant = "highest", rock = "lowest", landmark = "lowest"}
PropGround.MaxRaycastCorrection = 6

-- Layer used for the raycast rule: giants that are rocks (spires, bare boulders in badlands) follow the rock policy.
function PropGround.rayLayer(layer: string, kind: string?): string
    if kind == "rock" and layer == "giant" then return "rock" end
    return layer
end

-- Footprint radius of the 5 sample rays from the REAL mesh size (studs, already scaled), the same rule the probe uses.
function PropGround.footprintRadius(layer: string, sizeX: number, sizeZ: number): number
    local m = math.max(sizeX, sizeZ)
    if layer == "rock" or layer == "landmark" then return math.min(6, .3 * m) end
    return math.min(1, .04 * m)
end

-- Pivot y from RAY heights (Terrain raycast): plants highest - RootSink, rocks lowest - embed, landmarks lowest.
function PropGround.restYRay(layer: string, heights: {number}, height: number, scale: number): number
    local hi, lo = -math.huge, math.huge
    for _, h in heights do hi, lo = math.max(hi, h), math.min(lo, h) end
    if layer == "rock" then return lo - PropGround.RockSink * height * scale end
    if layer == "landmark" then return lo end
    return hi - PropGround.RootSink
end -- studs; a raycast answer further than this from the layout height is ignored

-- Radius (studs) of the trunk footprint to sample: the first collider box of the kit id (the trunk), else a fraction of the prop.
function PropGround.trunkRadius(data: any, scale: number, fallback: number): number
    local c = if type(data) == "table" and type(data.colliders) == "table" then data.colliders[1] else nil
    if c then return math.max(c[4], c[6]) * .5 * scale end
    return math.max(fallback, 0)
end

-- The five sample points (centre + 4 around the trunk) as {x, z} pairs.
function PropGround.samplePoints(x: number, z: number, r: number): {{number}}
    return {{x, z}, {x + r, z}, {x - r, z}, {x, z + r}, {x, z - r}}
end

-- Pivot y of a prop whose bottom must rest on the terrain. heights = terrain heights at the sample points.
-- raised layers: highest sample + Clearance. Others (rock, log, landmark) are handled by their own rules; this returns the
-- highest sample minus the embed depth (rockSink * height) for rocks.
function PropGround.restY(layer: string, heights: {number}, height: number, scale: number): number
    local hi, lo = -math.huge, math.huge
    for _, h in heights do hi, lo = math.max(hi, h), math.min(lo, h) end
    if PropGround.Raised[layer] then return hi + PropGround.Clearance end
    if layer == "rock" then return lo - PropGround.RockSink * height * scale end
    return lo
end

-- true when the prop's bottom is below the highest terrain sample under the trunk by more than `tolerance` studs.
function PropGround.submerged(bottomY: number, heights: {number}, tolerance: number): boolean
    local hi = -math.huge
    for _, h in heights do hi = math.max(hi, h) end
    return bottomY < hi - tolerance
end

-- Combine a raycast answer with the layout height: use the ray result when it exists and is within MaxRaycastCorrection of the
-- layout y, else keep the layout y (a wrong ray must never throw a prop into the sky or the ground).
function PropGround.corrected(layoutY: number, hits: {number?}, layer: string, height: number, scale: number): number
    local found: {number} = {}
    for _, h in hits do if h ~= nil and h == h then table.insert(found, h) end end
    if #found < 3 then return layoutY end -- not enough rays hit the terrain
    local y = PropGround.restYRay(layer, found, height, scale)
    if math.abs(y - layoutY) > PropGround.MaxRaycastCorrection then return layoutY end
    return y
end

BiomePlacement.Ground = PropGround

local S = 1.6 -- IslandLayout.Scale; verify_world_art asserts they agree

local function scaled(points: {{number}}): {{number}}
    local out = {}
    for i, p in points do out[i] = if i == 1 then {p[1], p[2]} else {p[1] * S, p[2] * S} end
    return out
end
-- Navigation corridors kept clear of blocking props (x,z polylines, half-width in studs).
BiomePlacement.Paths = {
    {width = 18, points = scaled({{0, 30}, {-40, 8}, {-80, -15}, {-125, -100}})},
    {width = 18, points = scaled({{0, 30}, {40, -30}, {110, -40}, {105, -80}})},
    {width = 16, points = scaled({{0, 30}, {0, -180}})},
    {width = 16, points = scaled({{0, 30}, {15, 190}, {0, 255}})},
    {width = 16, points = scaled({{0, 30}, {-105, 80}, {-190, 15}})},
    {width = 16, points = scaled({{0, 30}, {128, 102}, {182, 20}})},
}
-- Circles that stay clear: spawn meadow, jump stones, legacy arch, spring, sanctuary approach.
BiomePlacement.KeepOuts = {
    {x = 0, z = 30, radius = 64, all = false}, -- BD-460: spawn meadow 56 -> 64 (and paths +2 wide above): clearer main routes, dense elsewhere
    {x = 0, z = 30, radius = 20, all = true},
    {x = 55, z = -30, radius = 26, all = true},
    {x = -128, z = -24, radius = 52, all = true},
    {x = 176, z = -64, radius = 40, all = true},
    {x = 0, z = 400, radius = 40, all = true},
}
-- Sanctuary hub footprint (outside the arena, Config.ArenaHalfWidth + 105 +/- 48); nothing may intersect it.
BiomePlacement.Sanctuary = {minX = -55, maxX = 55, minZ = 473, maxZ = 569}
-- BD-281: with Config.CaveHub on, Arena calls this with CaveHubLayout.hub(config).biome so the rect follows the cave.
function BiomePlacement.useHub(rect: {minX: number, maxX: number, minZ: number, maxZ: number})
    BiomePlacement.Sanctuary = {minX = rect.minX, maxX = rect.maxX, minZ = rect.minZ, maxZ = rect.maxZ}
end
-- Dense lush groves (the lush groveBoost of v1) now supplement the noise forest field.
BiomePlacement.Groves = {
    {-168, 128}, {168, -128}, {-200, -160}, {205, 163}, {-304, 24}, {291, 32}, {0, -288}, {24, 304},
    {-60, -250}, {70, 255}, {-300, 300}, {330, -250},
}
BiomePlacement.Landmarks = {
    {id = "world_landmark_dino_statue", x = 96, z = 152},
    {id = "world_landmark_fossil_display", x = -96, z = 200},
    {id = "world_landmark_stone_arch", x = 240, z = -272},
    {id = "world_landmark_ruins_altar", x = -64, z = -192},
}
BiomePlacement.LandmarkScale = 1.4
-- Layers: grid cell size, base acceptance chance (times biome weight, forest field and density), slope limit, cap, blocking.
BiomePlacement.Layers = {
    {name = "tree", cell = 10, chance = .105, maxSlope = 32, cap = 560, blocking = true},
    {name = "giant", cell = 40, chance = .42, maxSlope = 22, cap = 46, blocking = true},
    {name = "log", cell = 20, chance = .06, maxSlope = 20, cap = 62, blocking = true},
    {name = "rock", cell = 14, chance = .075, maxSlope = 46, cap = 150, blocking = true},
    {name = "shrub", cell = 6.4, chance = .12, maxSlope = 36, cap = 900, blocking = false},
    {name = "groundcover", cell = 4.6, chance = .11, maxSlope = 32, cap = 1300, blocking = false},
}
-- Placed-part budget at density 1: MeshPart props cost 1 part (+ their invisible collider boxes); a prop whose mesh is not
-- available costs the native fallback (2 wedge parts per triangle + colliders), so a failed upload thins the world instead
-- of blowing the phone budget. Whole-scene accounting (food, hub, rigs) is in docs/68 and tools/verify_world_art.py.
BiomePlacement.UndergrowthChance = .5 -- per placed tree
BiomePlacement.UndergrowthCap = 190 -- companion plants at density 1
BiomePlacement.PartBudget = 3800 -- BD-167: +100 at density 1 (+125 parts at the playtest 1.25) pays for tree undergrowth; see docs/68 'World density v3'

-- Per-biome density multiplier for each layer and the weighted kit picks. A pick is {id, weight}; tree/giant picks use
-- family names ("canopy", ...) that get a size appended, log picks always lie a dead tree on its side.
BiomePlacement.Biomes = {
    meadow = {
        tree = .55, giant = .15, log = .6, rock = .45, shrub = .75, groundcover = 1.3,
        trees = {{"canopy", .5}, {"conifer", .22}, {"cycad", .2}, {"dead", .04}},
        giants = {{"canopy", 1}},
        rocks = {{"mossy", .6}, {"bare", .4}},
        shrubs = {{"world_bush_a", .22}, {"world_bush_b", .2}, {"world_fern_b", .14}, {"world_fern_a", .1}, {"world_mushrooms_a", .08}, {"world_horsetail_a", .05}, {"world_bush_b", .21}},
        cover = {{"world_grass_a", .3}, {"world_grass_b", .28}, {"world_flowers_a", .42}},
        bloom = .85,
    },
    fern = {
        tree = 1.35, giant = 1.0, log = 1.4, rock = .5, shrub = 1.7, groundcover = .9,
        trees = {{"canopy", .46}, {"cycad", .28}, {"conifer", .19}, {"dead", .07}},
        giants = {{"canopy", .6}, {"cycad", .4}},
        rocks = {{"mossy", .82}, {"bare", .18}},
        shrubs = {{"world_fern_a", .3}, {"world_fern_b", .3}, {"world_bush_a", .08}, {"world_bush_b", .08}, {"world_mushrooms_a", .12}, {"world_horsetail_a", .12}},
        cover = {{"world_grass_a", .4}, {"world_grass_b", .4}, {"world_flowers_a", .2}},
        bloom = .35,
    },
    conifer = {
        tree = 1.5, giant = 1.4, log = 1.0, rock = 1.25, shrub = 1.0, groundcover = .6,
        trees = {{"conifer", .76}, {"dead", .1}, {"canopy", .08}, {"cycad", .06}},
        giants = {{"conifer", 1}},
        rocks = {{"bare", .5}, {"mossy", .5}},
        shrubs = {{"world_fern_a", .22}, {"world_fern_b", .2}, {"world_mushrooms_a", .2}, {"world_bush_a", .14}, {"world_bush_b", .14}, {"world_horsetail_a", .1}},
        cover = {{"world_grass_b", .6}, {"world_grass_a", .3}, {"world_flowers_a", .1}},
        bloom = .1,
    },
    marsh = {
        tree = .75, giant = .6, log = 1.7, rock = .35, shrub = 1.7, groundcover = 1.0,
        trees = {{"cycad", .46}, {"canopy", .25}, {"dead", .25}, {"conifer", .04}},
        giants = {{"cycad", .55}, {"canopy", .45}},
        rocks = {{"mossy", .85}, {"bare", .15}},
        shrubs = {{"world_horsetail_a", .5}, {"world_fern_a", .12}, {"world_fern_b", .1}, {"world_bush_a", .08}, {"world_bush_b", .08}, {"world_mushrooms_a", .12}},
        cover = {{"world_grass_a", .48}, {"world_grass_b", .37}, {"world_flowers_a", .15}},
        bloom = .3,
    },
    badlands = {
        tree = .2, giant = .2, log = .6, rock = 2.3, shrub = .32, groundcover = .26,
        trees = {{"dead", .55}, {"conifer", .35}, {"cycad", .1}},
        giants = {{"dead", 1}},
        rocks = {{"bare", .88}, {"mossy", .12}},
        shrubs = {{"world_bush_b", .6}, {"world_fern_a", .1}, {"world_horsetail_a", .1}, {"world_bush_a", .1}, {"world_mushrooms_a", .1}},
        cover = {{"world_grass_b", .85}, {"world_flowers_a", .15}},
        bloom = .05,
    },
    volcanic = {
        tree = .13, giant = .35, log = .5, rock = 2.0, shrub = .1, groundcover = .06,
        trees = {{"dead", .88}, {"conifer", .12}},
        giants = {{"dead", 1}},
        rocks = {{"bare", .92}, {"mossy", .08}},
        shrubs = {{"world_bush_b", .7}, {"world_mushrooms_a", .2}, {"world_fern_a", .1}},
        cover = {{"world_grass_b", 1}},
        bloom = 0,
    },
}
-- Scale ranges per layer (min, max): trees are mature (sizes s/m/l are already different), giants are 2.4x-4x.
BiomePlacement.Scales = {
    tree = {.9, 1.6}, giant = {2.4, 4}, log = {.9, 1.5}, rock = {.85, 1.8},
    shrub = {1.1, 2.3}, groundcover = {1.6, 3.0}, landmark = {1.4, 1.4},
}

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
local function pick(list: {{any}}, roll: number): any
    local total = 0
    for _, e in list do total += e[2] end
    local acc, target = 0, roll * total
    for _, e in list do
        acc += e[2]
        if target < acc then return e[1] end
    end
    return list[#list][1]
end
-- Smooth value in [0,1] from two noise octaves (never a grid; used for forest cores, tuft patches, flower meadows).
local function field(seed: number, k: number, x: number, z: number, scale: number): number
    local o = .5 + ((seed * .137 + k * 11.3) % 53)
    local n = math.noise(x / scale, z / scale, o) * .75 + math.noise(x / (scale * .43), z / (scale * .43), o + 5.7) * .35
    return math.clamp(.5 + n * .62, 0, 1)
end
BiomePlacement.field = field

-- BD-167 colour variation: a small multiplicative tint on the (white) MeshPart so the same mesh never repeats exactly. Pure math,
-- deterministic from the placement hash; every channel stays in [0.80, 1.0] so the vertex-colour palette is only dimmed/warmed.
BiomePlacement.TintMin = .8
BiomePlacement.BiomeWarmth = { -- extra (r, g, b) multipliers per sub-biome, each in [0.9, 1.0]
    meadow = {1, .97, .93}, fern = {.96, .98, .93}, conifer = {.93, .98, 1}, marsh = {.92, 1, .97},
    badlands = {1, .96, .9}, volcanic = {1, .92, .9},
}
function BiomePlacement.tint(biome: string, h1: number, h2: number): (number, number, number)
    local w = BiomePlacement.BiomeWarmth[biome] or {1, 1, 1}
    local v = BiomePlacement.TintMin + (1 - BiomePlacement.TintMin) * h1 -- brightness
    local hueShift = (h2 - .5) * .1 -- warm (+) vs cool (-)
    return math.clamp(v * w[1] * (1 + hueShift), BiomePlacement.TintMin * .9, 1),
        math.clamp(v * w[2], BiomePlacement.TintMin * .9, 1),
        math.clamp(v * w[3] * (1 - hueShift), BiomePlacement.TintMin * .9, 1)
end

export type Placement = {id: string, x: number, y: number, z: number, yaw: number, roll: number, scale: number, radius: number, layer: string, biome: string}

-- options: {seed, density, extent, height=(x,z)->y, kit=WorldKitData, meshes=WorldKitMeshAssets (ids that are real MeshParts),
-- map=BiomeMap, layout=IslandLayout (pools)}
function BiomePlacement.generate(options): {Placement}
    local seed, density, extent, height, kit = options.seed, math.clamp(options.density or 1, .25, 2), options.extent - 12, options.height, options.kit
    local map, layout = options.map, options.layout
    local placed: {Placement} = {}
    local meshes = options.meshes or {}
    local parts = 0
    local budget = BiomePlacement.PartBudget * density
    local grid: {[number]: {Placement}} = {}
    local CELL = 40
    local function key(x: number, z: number): number return math.floor(x / CELL) * 4096 + math.floor(z / CELL) end
    local blockingLayer = {tree = true, giant = true, log = true, rock = true, landmark = true}
    local function clear(x: number, z: number, r: number, blocking: boolean): boolean
        local gx, gz = math.floor(x / CELL), math.floor(z / CELL)
        for ix = gx - 1, gx + 1 do
            for iz = gz - 1, gz + 1 do
                for _, p in grid[ix * 4096 + iz] or {} do
                    local need = if blocking or blockingLayer[p.layer] then r + p.radius else (r + p.radius) * .6
                    if (p.x - x) ^ 2 + (p.z - z) ^ 2 < need * need then return false end
                end
            end
        end
        return true
    end
    local function inWater(x: number, z: number, margin: number): boolean
        return layout ~= nil and layout.inPool(x, z, margin)
    end
    local function add(id: string, x: number, z: number, yaw: number, scale: number, layer: string, sink: number, biome: string, roll: number?, y: number?, radius: number?)
        local data = kit[id]
        local r = radius or math.max(data.extent[1], data.extent[3]) * .5 * scale * (if layer == "tree" or layer == "giant" then .42 else .8)
        local lo = footprintRange(height, x, z, r * .5)
        if y == nil and PropGround.Raised[layer] and data.kind ~= "rock" then
            -- BD-395: the bottom rests ON the highest terrain point under the trunk (+0.2), never buried in the slope
            local heights = {}
            for _, pt in PropGround.samplePoints(x, z, PropGround.trunkRadius(data, scale, r * .5)) do table.insert(heights, height(pt[1], pt[2])) end
            y = PropGround.restY(layer, heights, data.extent[2], scale)
        end
        local p = {id = id, x = x, y = y or (lo - sink * data.extent[2] * scale), z = z, yaw = yaw, roll = roll or 0, scale = scale, radius = r, layer = layer, biome = biome}
        table.insert(placed, p)
        parts += BiomePlacement.partCost(id, kit, meshes)
        local k = key(x, z)
        grid[k] = grid[k] or {}
        table.insert(grid[k], p)
    end
    for i, site in BiomePlacement.Landmarks do
        local data = kit[site.id]
        local sc = BiomePlacement.LandmarkScale
        local r = math.max(data.extent[1], data.extent[3]) * .5 * sc
        local best, bx, bz = math.huge, site.x, site.z
        for step = 0, 24 do -- search a small spiral for the flattest footprint
            local a, d = step * 2.4, math.sqrt(step) * 8
            local x, z = site.x + math.cos(a) * d, site.z + math.sin(a) * d
            local lo, hi = footprintRange(height, x, z, r)
            local score = hi - lo
            if score < best and BiomePlacement.pathClearance(x, z) > r * .6 and BiomePlacement.keepOutClearance(x, z, true) > r and not inWater(x, z, r) then best, bx, bz = score, x, z end
        end
        add(site.id, bx, bz, BiomePlacement.hash(seed, 99, i) * math.pi * 2, sc, "landmark", .04, "meadow", nil, nil, math.sqrt(data.extent[1] ^ 2 + data.extent[3] ^ 2) * .5 * sc) -- BD-410: keep-clear radius = half the footprint DIAGONAL (a yawed box reaches that far)
    end
    local undergrowth, undergrowthCap = 0, math.floor(BiomePlacement.UndergrowthCap * density)
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
                local h = height(x, z)
                local weights, dominant = map.weights(x, z, h, seed)
                -- Dither between the neighbouring biomes by weight: borders are mixed bands, not lines.
                local biome = map.pick(weights, BiomePlacement.hash(seed, li, ix, iz, 9))
                local def = BiomePlacement.Biomes[biome]
                local forest = field(seed, 1, x, z, 64)
                local grove = math.huge
                for _, g in BiomePlacement.Groves do grove = math.min(grove, math.sqrt((x - g[1]) ^ 2 + (z - g[2]) ^ 2)) end
                local chance = layer.chance * def[layer.name] * density
                if layer.name == "tree" then
                    chance *= (.18 + 2.1 * forest ^ 1.7) * (1 + 1.4 * math.exp(-(grove / 30) ^ 2))
                    if h > 52 and biome ~= "conifer" then chance *= .25 end
                elseif layer.name == "giant" then
                    local fromSpawn = math.sqrt(x ^ 2 + (z - 30) ^ 2)
                    -- Giants are outer-zone landmarks: none near the spawn meadow, full strength 260 studs out.
                    chance *= math.clamp((fromSpawn - 150) / 120, 0, 1) * (.4 + 1.2 * forest) * (1 + 1.6 * math.exp(-(grove / 40) ^ 2))
                elseif layer.name == "log" then
                    chance *= (.3 + 1.4 * forest)
                elseif layer.name == "shrub" then
                    chance *= (.3 + 1.5 * forest ^ 1.3) * (1 + .9 * math.exp(-(grove / 40) ^ 2))
                    if layout then chance *= 1 + 1.6 * layout.poolProximity(x, z) * (if biome == "marsh" then 1 else .3) end
                elseif layer.name == "groundcover" then
                    -- Clustered tufts: dense in patches, sparse between them, patches drift with the terrain noise.
                    local patch = field(seed, 3, x, z, 22)
                    chance *= .1 + 2.6 * patch ^ 2.2
                end
                if BiomePlacement.hash(seed, li, ix, iz, 3) > chance then continue end
                local s = BiomePlacement.slope(height, x, z)
                if s > layer.maxSlope then continue end
                local n = BiomePlacement.hash(seed, li, ix, iz, 4)
                local roll = BiomePlacement.hash(seed, li, ix, iz, 5)
                local id: string
                local lay = layer.name
                local sinkRoll = BiomePlacement.hash(seed, li, ix, iz, 10)
                if lay == "tree" or lay == "giant" then
                    local family = pick(if lay == "tree" then def.trees else def.giants, n)
                    local sizeRoll = if lay == "giant" then .95 else math.clamp(roll + (if grove < 40 then .2 else 0) + (if h > 40 then -.15 else 0), 0, 1)
                    local size = if sizeRoll < .28 then "s" elseif sizeRoll < .72 then "m" else "l"
                    if lay == "giant" then size = "l" end
                    id = "world_tree_" .. family .. "_" .. size
                elseif lay == "log" then
                    id = "world_tree_dead_" .. (if roll < .35 then "s" elseif roll < .8 then "m" else "l")
                elseif lay == "rock" then
                    local family = pick(def.rocks, n)
                    local size = if roll < .4 then "s" elseif roll < .82 then "m" else "l"
                    id = "world_boulder_" .. family .. "_" .. size
                    if (biome == "badlands" or biome == "volcanic" or h > 36) and s > 14 and s <= PropGround.TallMaxSlope and n < .22 then
                        id = if n < .11 then "world_rocks_spires" else "world_rocks_ledge"
                    end
                elseif lay == "shrub" then
                    id = pick(def.shrubs, n)
                    if layout and biome == "marsh" and n > .75 and layout.poolProximity(x, z) > .15 then id = "world_horsetail_a" end
                else
                    id = pick(def.cover, n)
                    -- Flower meadows: where the bloom field is high the tufts turn into flowers.
                    if def.bloom > 0 and field(seed, 4, x, z, 40) > 1 - def.bloom * .55 and n > .15 then id = "world_flowers_a" end
                end
                if lay == "giant" and (biome == "badlands" or biome == "volcanic") and roll > .5 then
                    id = if n < .5 then "world_rocks_spires" else "world_boulder_bare_l"
                end
                id = BiomePlacement.substitute(id, kit, meshes)
                local data = kit[id]
                if not data or parts + BiomePlacement.partCost(id, kit, meshes) > budget then continue end
                local range = BiomePlacement.Scales[lay]
                local scale = range[1] + (range[2] - range[1]) * BiomePlacement.hash(seed, li, ix, iz, 6)
                if lay == "giant" and kit[id].kind == "rock" then scale *= (if id == "world_rocks_spires" then .75 else .85) end
                local r = math.max(data.extent[1], data.extent[3]) * .5 * scale
                local blockingR = if lay == "tree" or lay == "giant" then r * .42 else r
                local needed = if layer.blocking then blockingR * .7 else 1
                if lay == "log" then r = data.extent[2] * .5 * scale * .85 end
                if BiomePlacement.pathClearance(x, z) < (if lay == "log" then r else needed) or BiomePlacement.keepOutClearance(x, z, layer.blocking) < r * .5 then continue end
                if math.max(math.abs(x), math.abs(z)) + r > extent then continue end
                if inWater(x, z, if layer.blocking then r * .5 else 1) then continue end
                if not clear(x, z, if lay == "log" then r * .8 else if lay == "tree" or lay == "giant" then blockingR else r, layer.blocking) then continue end
                local yaw = BiomePlacement.hash(seed, li, ix, iz, 7) * math.pi * 2
                if lay == "log" then
                    -- Dead tree lying on its side: needs flat ground along the trunk and dry ends.
                    local len = data.extent[2] * scale * .9
                    local ex, ez = x + math.sin(yaw) * -len, z + math.cos(yaw) * -len
                    local h0, h1 = height(x, z), height(ex, ez)
                    if math.abs(h1 - h0) > 2.2 or inWater(ex, ez, 1) or math.max(math.abs(ex), math.abs(ez)) > extent then continue end
                    if BiomePlacement.pathClearance(ex, ez) < 2 or BiomePlacement.keepOutClearance(ex, ez, true) < 0 then continue end
                    add(id, x, z, yaw, scale, "log", 0, biome, math.pi / 2, math.min(h0, h1) + .3 * scale, r)
                    count += 1
                    continue
                end
                local sink = if lay == "rock" or lay == "giant" and kit[id].kind == "rock" then .12 elseif lay == "tree" or lay == "giant" then .03 else .02 + .03 * sinkRoll
                add(id, x, z, yaw, scale, lay, sink, biome)
                count += 1
                -- BD-167 undergrowth: ferns, bushes and mushrooms gather around a tree foot (small, never on the trunk, never on a
                -- walkway), limited by its own cap and the part budget. Layer "shrub" so PropGround treats them as plants.
                if lay == "tree" and undergrowth < undergrowthCap and BiomePlacement.hash(seed, li, ix, iz, 70) < BiomePlacement.UndergrowthChance then
                    local trunk = math.max(PropGround.trunkRadius(data, scale, r * .4), .6)
                    for c = 1, (if BiomePlacement.hash(seed, li, ix, iz, 71) < .45 then 2 else 1) do
                        local a = BiomePlacement.hash(seed, li, ix, iz, 72 + c) * math.pi * 2
                        local d = trunk + 1.6 + 2.6 * BiomePlacement.hash(seed, li, ix, iz, 74 + c)
                        local ux, uz = x + math.cos(a) * d, z + math.sin(a) * d
                        local uid = BiomePlacement.substitute(pick(def.shrubs, BiomePlacement.hash(seed, li, ix, iz, 76 + c)), kit, meshes)
                        if kit[uid] and parts + BiomePlacement.partCost(uid, kit, meshes) <= budget and undergrowth < undergrowthCap
                            and BiomePlacement.pathClearance(ux, uz) >= 1.5 and BiomePlacement.keepOutClearance(ux, uz, false) >= 0
                            and math.max(math.abs(ux), math.abs(uz)) + 3 < extent and not inWater(ux, uz, 1.5)
                            and BiomePlacement.slope(height, ux, uz) <= 30 and clear(ux, uz, 1.6, false) then
                            local us = BiomePlacement.Scales.shrub[1] * (.8 + .5 * BiomePlacement.hash(seed, li, ix, iz, 78 + c))
                            add(uid, ux, uz, BiomePlacement.hash(seed, li, ix, iz, 80 + c) * math.pi * 2, us, "shrub", .02 + .03 * sinkRoll, biome)
                            undergrowth += 1
                        end
                    end
                end
                if lay == "groundcover" and BiomePlacement.hash(seed, li, ix, iz, 11) < .6 and count < cap then
                    -- Tufts grow in clumps: one or two smaller companions a stride away (irregular, never gridded).
                    for c = 1, (if BiomePlacement.hash(seed, li, ix, iz, 12) < .4 then 2 else 1) do
                        local a = BiomePlacement.hash(seed, li, ix, iz, 20 + c) * math.pi * 2
                        local d = 1.1 + 1.7 * BiomePlacement.hash(seed, li, ix, iz, 30 + c)
                        local cx, cz = x + math.cos(a) * d, z + math.sin(a) * d
                        local cs = scale * (.6 + .35 * BiomePlacement.hash(seed, li, ix, iz, 40 + c))
                        local cid = if n > .3 and BiomePlacement.hash(seed, li, ix, iz, 50 + c) < .25 then (if id == "world_flowers_a" then "world_grass_a" else id) else id
                        cid = BiomePlacement.substitute(cid, kit, meshes)
                        if kit[cid] and parts + BiomePlacement.partCost(cid, kit, meshes) <= budget and count < cap
                            and BiomePlacement.pathClearance(cx, cz) >= 1 and BiomePlacement.keepOutClearance(cx, cz, false) >= 0
                            and math.max(math.abs(cx), math.abs(cz)) + 2 < extent and not inWater(cx, cz, 1)
                            and BiomePlacement.slope(height, cx, cz) <= layer.maxSlope and clear(cx, cz, 1.2, false) then
                            add(cid, cx, cz, BiomePlacement.hash(seed, li, ix, iz, 60 + c) * math.pi * 2, cs, "groundcover", .03, biome)
                            count += 1
                        end
                    end
                end
            end
        end
    end
    return placed
end

-- An id with no uploaded mesh swaps to another size of the same family that has one (a missing upload must not
-- bring back ~100-part native models); with no mesh info at all (offline native budget) nothing changes.
function BiomePlacement.substitute(id: string, kit, meshes): string
    if meshes[id] or next(meshes) == nil then return id end
    local base = string.match(id, "^(.*)_[sml]$")
    if base then
        for _, size in {"m", "s", "l"} do
            local alt = base .. "_" .. size
            if meshes[alt] and kit[alt] then return alt end
        end
    end
    return id
end
-- Parts one placement adds to the world: 1 MeshPart (or 2 wedges per triangle of the native fallback) + collider boxes.
function BiomePlacement.partCost(id: string, kit, meshes): number
    local data = kit[id]
    return (if meshes[id] then 1 else 2 * data.triangles) + #data.colliders
end
function BiomePlacement.parts(placed: {Placement}, kit, meshes): number
    local total = 0
    for _, p in placed do total += BiomePlacement.partCost(p.id, kit, meshes or {}) end
    return total
end
function BiomePlacement.triangles(placed: {Placement}, kit): number
    local total = 0
    for _, p in placed do total += kit[p.id].triangles end
    return total
end
return BiomePlacement
