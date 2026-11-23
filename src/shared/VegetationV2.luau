--!strict
-- BD-1239 (owner 2026-11-16: "vegetation looks cheap ... it should have more personality and fit the game"; concept sheet approved with
-- "Yes, build all", docs/evidence/2026-11-16-vegetation-v2): the island's plants as one chunky, glossy toy family.
-- Every mesh is a Roblox generate_mesh Model written from the approved sheet (one magenta reference picture per object in
-- docs/evidence/2026-11-16-vegetation-v2/refs, published to the owner's account, docs/77). Nothing code-built.
-- Look only: the kit ids, the placement grammar, the colliders and the food hosts stay exactly as they are; this module only says which
-- generated mesh SHOWS for a kit id (Arena.generatedProp) and how it is fitted into the kit box. Ground cover is thinned (CoverKeep), so the
-- island has fewer parts, and the flat spiky grass tufts (kit world_grass_a / world_grass_b) are replaced by soft grass clumps and ferns.
-- Pure data and math, no Instances. Active only while Config.WorldV3Enabled, ToonWorldEnabled and VegetationV2Enabled are all true.
local VegetationV2 = {}

-- key -> published Model id (numeric string; nothing invented), triangles cap given to generate_mesh, reference picture, what it is.
VegetationV2.Assets = {
    veg2_tree_flower = {assetId = "77092440397911", tris = 1500, ref = "tree_flower", what = "rounded flower tree, white blossoms, mushrooms at the foot"},
    veg2_tree_twisty = {assetId = "76763874077682", tris = 2500, ref = "tree_twisty_landmark", what = "big twisty-trunk tree with vines and pink flowers"},
    veg2_tree_fruit = {assetId = "109141890199115", tris = 1500, ref = "tree_fruit_orange", what = "fruit tree with oranges"},
    veg2_pine_a = {assetId = "104792252201636", tris = 900, ref = "pine_a", what = "dark four-layer pine with mushrooms"},
    veg2_pine_b = {assetId = "77837197584497", tris = 900, ref = "pine_b", what = "young three-layer pine with a lime tip"},
    veg2_palm_coconut = {assetId = "87978584265482", tris = 1200, ref = "palm_coconut", what = "coconut palm with a hibiscus at the foot"},
    veg2_palm_flower = {assetId = "131648210939538", tris = 1200, ref = "palm_flower", what = "flower palm with a vine and a pink bloom"},
    veg2_bush_red = {assetId = "77978853272967", tris = 900, ref = "bush_berry_red", what = "green dome with small red berries"},
    veg2_bush_blue = {assetId = "99690382623326", tris = 900, ref = "bush_berry_blue", what = "green dome with small blueberries"},
    veg2_bush_grape = {assetId = "139210058341686", tris = 900, ref = "bush_grape_purple", what = "green dome with small purple grape bunches"},
    veg2_flowers_daisy = {assetId = "116872167176322", tris = 500, ref = "flowers_a", what = "purple, yellow and white daisies"},
    veg2_flowers_hibiscus = {assetId = "115140435674207", tris = 500, ref = "flowers_hibiscus", what = "pink and yellow hibiscus in broad leaves"},
    veg2_grass_a = {assetId = "125477923669500", tris = 400, ref = "grass_a", what = "soft round grass clump with a white flower"},
    veg2_grass_b = {assetId = "106175427368675", tris = 400, ref = "grass_b", what = "tall grass clump with a flower and a mushroom"},
    veg2_fern_a = {assetId = "107416773840661", tris = 500, ref = "fern_a", what = "round lime fern with fiddleheads"},
    veg2_fern_b = {assetId = "83786014984437", tris = 500, ref = "fern_b", what = "upright fern with one big fiddlehead"},
    veg2_rock_mossy = {assetId = "123042036522291", tris = 600, ref = "rock_mossy_a", what = "grey boulder with a moss cap and a mushroom"},
    veg2_rock_spiral = {assetId = "110545121175304", tris = 700, ref = "rock_mossy_spiral", what = "mossy stone with a carved spiral"},
}

-- Share of the ground cover placements kept (the rest are dropped, deterministic by position): a soft clump reads as more plant than
-- the thin kit tuft, and the phone part budget (BD-1222: 4,989 parts within 300 studs of spawn against about 3,000) needs fewer parts.
VegetationV2.CoverKeep = .5
-- BD-1239 follow-up (lead review 2026-11-16): the bush rule Arena hands to BiomePlacement.BushV2. Round bushes are 2.6-5 kit studs tall (the
-- dome shows about 3-6 studs, a spawn dino is 4.4-6.6) instead of the 4-12 stud Small band; of the shrub-layer bush picks 60% stay bushes, 25%
-- become flower or grass clumps, 15% are open ground. The food map for this world is FoodLayerDataV3HostsVeg2 (tools/food_hosts.py --veg2).
-- Height factor of the shown mesh for the berry bushes (a lower dome, so a row of bushes reads as bushes, not a hedge). 1 = uniform.
VegetationV2.Squash = table.freeze({veg2_bush_red = .8, veg2_bush_blue = .8, veg2_bush_grape = .8})
VegetationV2.BushRule = table.freeze({minHeight = 3, maxHeight = 5.5, maxWidth = 11, keep = .74, flowers = .15}) -- BD-1309: keep .75 -> .74 on the hillier island

-- BD-1309: tree growth on this island (BiomePlacement.TreeGrowth): scale .6-2.0 skewed young, times an age field .75-1.3 over ~70 studs,
-- so the same kit tree shows from a 0.45x sapling to a 2.6x old giant and groves differ in age.
VegetationV2.TreeGrowth = table.freeze({min = .6, max = 2.0, skew = 1.35, ageScale = 70, young = .75, old = 1.3})

function VegetationV2.enabled(config: any): boolean
    return type(config) == "table" and config.WorldV3Enabled == true and config.ToonWorldEnabled == true and config.VegetationV2Enabled == true
end

-- True for a key whose id is a real published id (empty = not generated yet: the current mesh keeps showing).
function VegetationV2.ready(key: string): boolean
    local entry = VegetationV2.Assets[key]
    if not entry then return false end
    local id = entry.assetId
    return #id >= 9 and #id <= 18 and string.match(id, "^[1-9]%d*$") == id
end

local function choose(roll: number, a: string, b: string, share: number): string
    return if roll < share then a else b
end

-- Which v2 key shows for a kit id in a sub-biome (BiomeMap id), with roll in [0, 1) a deterministic per-prop value. nil = keep the current
-- visual (dead trees, bare rocks, mushrooms, logs and landmarks are not part of this family).
function VegetationV2.visualFor(id: string, biome: string, roll: number): string?
    local beach = biome == "badlands" -- the palm beach zone of World V3
    local damp = biome == "fern" or biome == "marsh" or biome == "conifer"
    if id == "world_tree_canopy_s" then return choose(roll, "veg2_tree_flower", "veg2_tree_fruit", .55) end
    if id == "world_tree_canopy_m" then return choose(roll, "veg2_tree_fruit", "veg2_tree_flower", if biome == "meadow" then .55 else .4) end
    if id == "world_tree_canopy_l" then return "veg2_tree_twisty" end
    if id == "world_tree_conifer_s" then return choose(roll, "veg2_pine_b", "veg2_pine_a", .7) end
    if id == "world_tree_conifer_m" or id == "world_tree_conifer_l" then return choose(roll, "veg2_pine_a", "veg2_pine_b", .65) end
    if string.sub(id, 1, 16) == "world_tree_cycad" then return choose(roll, "veg2_palm_coconut", "veg2_palm_flower", if beach then .65 else .4) end
    if id == "world_bush_a" then return choose(roll, "veg2_bush_red", "veg2_bush_blue", .5) end
    if id == "world_bush_b" then return if roll < .34 then "veg2_bush_grape" elseif roll < .67 then "veg2_bush_blue" else "veg2_bush_red" end
    if id == "world_fern_a" or id == "world_horsetail_a" then return "veg2_fern_a" end
    if id == "world_fern_b" then return "veg2_fern_b" end
    if id == "world_flowers_a" then return choose(roll, "veg2_flowers_hibiscus", "veg2_flowers_daisy", if beach then .6 else .25) end
    if id == "world_grass_a" or id == "world_grass_b" then
        if damp and roll < .35 then return choose(roll, "veg2_fern_a", "veg2_fern_b", .17) end
        return if id == "world_grass_a" then "veg2_grass_a" else "veg2_grass_b"
    end
    if id == "world_boulder_mossy_s" then return "veg2_rock_mossy" end
    if id == "world_boulder_mossy_m" or id == "world_boulder_mossy_l" then return choose(roll, "veg2_rock_spiral", "veg2_rock_mossy", .3) end
    return nil
end

-- Uniform scale that fits a mesh of `size` {x, y, z} into the kit box `extent` {x, y, z} of a prop of `kind`:
--   tree        = the existing generated-tree rule (height, crown at most 1.15x the widest kit side);
--   shrub       = round footprint as wide as the kit bush's mean width (the food host ring is built on that footprint);
--   groundcover = kit height (the kit tufts are thin, a clump is round; ground cover has no colliders);
--   rock/other  = inside the box (the kit colliders keep matching).
function VegetationV2.fit(kind: string, extent: {number}, size: {number}): number
    local wide = math.max(size[1], size[3])
    if kind == "tree" then return math.min(extent[2] / size[2], math.max(extent[1], extent[3]) * 1.15 / wide) end
    if kind == "shrub" then return (extent[1] + extent[3]) / 2 / wide end
    if kind == "groundcover" then return extent[2] / size[2] end
    return math.min(extent[1] / size[1], extent[2] / size[2], extent[3] / size[3])
end

-- Deterministic keep/drop for one ground cover placement at (x, z): keeps about CoverKeep of them, never in a grid pattern.
function VegetationV2.keepCover(x: number, z: number): boolean
    local h = math.floor(x * 8) * 73856093 + math.floor(z * 8) * 19349663
    local u = (h % 1000003) / 1000003
    if u < 0 then u += 1 end
    return u < VegetationV2.CoverKeep
end

-- The placements with ground cover thinned (all other layers untouched, order kept).
function VegetationV2.thin(placed: {any}): {any}
    local out = {}
    for _, p in placed do
        if p.layer ~= "groundcover" or VegetationV2.keepCover(p.x, p.z) then table.insert(out, p) end
    end
    return out
end

return VegetationV2
