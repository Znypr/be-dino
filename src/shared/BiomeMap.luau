--!strict
-- World v2 sub-biome map: a smooth, seeded, deterministic zone field (pure math, no Instances) shared by the terrain
-- painter, the prop placement grammar and the offline verifier. Each point has a weight per biome (they sum to 1);
-- neighbours blend because both the borders (domain warp + per-biome noise) and the terrain/prop pickers dither
-- between the biomes by weight instead of switching at a hard line.
local BiomeMap = {}
BiomeMap.Version = 1
BiomeMap.Order = {"meadow", "fern", "conifer", "marsh", "badlands", "volcanic"}
BiomeMap.Names = {
    meadow = "Meadow", fern = "Fern Forest", conifer = "Conifer Highlands",
    marsh = "Marsh", badlands = "Rocky Badlands", volcanic = "Volcanic Slopes",
}
-- Zone anchors in world studs: {biome, x, z, radius, strength}. Mountains carry the highland biomes; the spring and the
-- southern basin carry the marshes; the centre is the readable spawn meadow; the fern forest is the lowland default.
BiomeMap.Blobs = {
    {"meadow", 0, 30, 150, 1.7},
    {"meadow", 0, 30, 70, 3},
    {"meadow", -345, -30, 100, 1.15},
    {"meadow", 20, -345, 90, 1.0},
    {"meadow", 250, 345, 70, .9},
    {"fern", -120, 140, 150, 1.25},
    {"fern", 105, 215, 130, 1.2},
    {"fern", -85, -165, 140, 1.2},
    {"fern", 320, -50, 90, 1.1},
    {"fern", -330, 330, 90, 1.0},
    {"marsh", 165, 25, 125, 1.35},
    {"marsh", -45, 305, 118, 1.35},
    {"marsh", -330, 40, 78, 1.15},
    {"conifer", -232, -224, 180, 1.45},
    {"conifer", -264, 215, 160, 1.4},
    {"conifer", -110, -360, 70, 1.0},
    {"badlands", 256, 224, 165, 1.4},
    {"badlands", 365, 110, 85, 1.05},
    {"volcanic", 232, -208, 150, 1.5},
    {"volcanic", 105, -370, 70, 1.05},
}
-- Surface material bands per biome (Enum.Material names): {material, upper noise bound}, last band takes the rest.
BiomeMap.Ground = {
    meadow = {{"Grass", .7}, {"LeafyGrass", 1}},
    fern = {{"LeafyGrass", .62}, {"Grass", .8}, {"Mud", 1}},
    conifer = {{"Ground", .55}, {"LeafyGrass", .8}, {"Grass", 1}},
    marsh = {{"Mud", .42}, {"LeafyGrass", .8}, {"Grass", 1}},
    badlands = {{"Sandstone", .5}, {"Sand", .75}, {"Ground", 1}},
    volcanic = {{"Basalt", .62}, {"Slate", .85}, {"Ground", 1}},
}
-- Material above the biome's rock line / on steep ground.
BiomeMap.Rock = {meadow = "Rock", fern = "Rock", conifer = "Slate", marsh = "Mud", badlands = "Sandstone", volcanic = "Basalt"}
-- Global colours the terrain painter sets (SetMaterialColor): chosen so each biome reads differently at a glance.
BiomeMap.Colors = {
    -- BD-460 (docs/138, owner 2026-10-16: built-in Grass, the BeDino_Meadow override is unbound). The built-in Grass albedo is pale and grey-green, so the colour
    -- multiplier must be rich and warm: low blue is what removes the grey. Studio A/B (docs/138): A 118,164,72, B 102,150,60 (deeper),
    -- C 132,166,68 (sunny); owner picked C on 2026-10-16. Original before BD-460: 132,170,84.
    Grass = {132, 166, 68}, -- S .59, V .65
    LeafyGrass = {88, 132, 62}, -- S .53, V .52; was 62,124,78 (dark teal patches). Alternatives: 76,124,60 (deeper), 100,138,66 (lighter)
    Mud = {92, 76, 55},
    Ground = {112, 100, 66},
    Sand = {214, 190, 136},
    Sandstone = {186, 122, 80},
    Slate = {92, 102, 108},
    Basalt = {50, 47, 55},
    Rock = {114, 133, 137},
}

local function offset(seed: number, k: number): number
    return .37 + ((seed * 0.6180339 + k * 7.31) % 61)
end
local function sharpen(value: number): number return value ^ 2.4 end

-- Returns per-biome weights (sum 1) and the dominant biome id. h is the terrain height at (x,z).
function BiomeMap.weights(x: number, z: number, h: number, seed: number): ({[string]: number}, string)
    local o = offset(seed, 1)
    -- Domain warp makes the zone borders organic instead of circular.
    local wx = x + math.noise(x / 85, z / 85, o) * 52
    local wz = z + math.noise(x / 85 + 41.3, z / 85, o + 3.3) * 52
    local s = {meadow = 0, fern = 0, conifer = 0, marsh = 0, badlands = 0, volcanic = 0}
    for _, blob in BiomeMap.Blobs do
        local d2 = ((wx - blob[2]) ^ 2 + (wz - blob[3]) ^ 2) / (blob[4] * blob[4])
        local v = blob[5] * math.exp(-d2)
        if v > s[blob[1]] then s[blob[1]] = v end
    end
    -- Lowland default: the fern forest fills whatever the other zones leave over.
    s.fern = math.max(s.fern, .55 + .1 * math.noise(x / 120, z / 120, o + 9))
    -- Height rules: high ground leans conifer, wet ground stays low.
    s.conifer += math.clamp((h - 26) / 30, 0, 1) * .55
    if h > 12 then s.marsh *= math.max(0, 1 - (h - 12) / 10) end
    local total = 0
    for i, id in BiomeMap.Order do
        -- A touch of per-biome noise ragged-edges each border (different seed slice per biome).
        local n = 1 + .32 * math.noise(x / 52, z / 52, o + 17 + i * 5.1)
        local v = sharpen(math.max(0, s[id] * n))
        s[id] = v
        total += v
    end
    if total <= 1e-9 then s.fern, total = 1, 1 end
    local best, bestW = "fern", -1
    for _, id in BiomeMap.Order do
        s[id] /= total
        if s[id] > bestW then best, bestW = id, s[id] end
    end
    return s, best
end

-- Picks one biome from the weights with a [0,1) roll (dithering; every border becomes a mixed band, not a line).
function BiomeMap.pick(weights: {[string]: number}, roll: number): string
    local acc = 0
    for _, id in BiomeMap.Order do
        acc += weights[id]
        if roll < acc then return id end
    end
    return "fern"
end

-- Terrain surface material name for one column; nz / nd are smooth noise values in [0,1] and a white-noise value.
function BiomeMap.surface(weights: {[string]: number}, h: number, slope: number, pickRoll: number, bandRoll: number, veinNoise: number): string
    local biome = BiomeMap.pick(weights, pickRoll)
    if biome == "volcanic" and h > 34 and math.abs(veinNoise) < .035 then return "CrackedLava" end
    local rockLine = if biome == "conifer" then 58 elseif biome == "badlands" then 44 elseif biome == "volcanic" then 30 else 50
    if slope > 1.05 or h > rockLine then return BiomeMap.Rock[biome] end
    for _, band in BiomeMap.Ground[biome] do
        if bandRoll <= band[2] then return band[1] end
    end
    return BiomeMap.Ground[biome][#BiomeMap.Ground[biome]][1]
end
return BiomeMap
