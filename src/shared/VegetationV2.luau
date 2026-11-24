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
    -- BD-1311 (owner 2026-11-23: "more trees more variations and remodel some current trees that look too geometric"): the layered cone pines
    -- veg2_pine_a (104792252201636) and veg2_pine_b (77837197584497) read as hard cone stacks and are retired; three soft pines replace them,
    -- plus a fourth broadleaf. Same route (Roblox generate_mesh, text prompt in the approved sheet's style), reference = a Studio picture of
    -- the generated mesh in docs/evidence/2026-11-23-tree-variety/refs.
    veg2_pine_fir = {assetId = "121078729284419", tris = 1200, ref = "pine_fir", what = "soft fir with three puffy rounded tiers and a round tip"},
    veg2_pine_cypress = {assetId = "94010378329800", tris = 1000, ref = "pine_cypress", what = "soft flame-shaped cypress with mushrooms at the foot"},
    veg2_pine_bonsai = {assetId = "71668823008966", tris = 1200, ref = "pine_bonsai", what = "leaning bonsai pine with three cloud pads"},
    veg2_tree_oak = {assetId = "93533177854872", tris = 1200, ref = "tree_oak", what = "wide umbrella oak with a bent trunk and three round cloud crowns"},
    veg2_palm_coconut = {assetId = "87978584265482", tris = 1200, ref = "palm_coconut", what = "coconut palm with a hibiscus at the foot"},
    veg2_palm_flower = {assetId = "131648210939538", tris = 1200, ref = "palm_flower", what = "flower palm with a vine and a pink bloom"},
    -- BD-1315 jungle kit (biome overhaul docs/250 S2): shown only through kitVisual("jungle", ...) once the S1 biome clock swaps kits. Roblox
    -- generate_mesh in the toy style of the Jungle panel (docs/evidence/2026-11-23-biome-overhaul/biome-grid-chatgpt.jpg); reference = a
    -- Studio picture of the mesh in docs/evidence/2026-11-23-jungle-kit/refs. Ferns and mossy rocks reuse the approved veg2 ones.
    veg2_jungle_canopy = {assetId = "139306681391247", tris = 1500, ref = "jungle_canopy", what = "jungle canopy tree, buttress roots, two leaf layers, hanging vines"},
    veg2_jungle_elephant_ear = {assetId = "136970222010366", tris = 800, ref = "jungle_elephant_ear", what = "wide clump of big heart-shaped elephant ear leaves"},
    veg2_jungle_monstera = {assetId = "80843788267545", tris = 900, ref = "jungle_monstera", what = "mound of split monstera leaves"},
    veg2_jungle_hibiscus = {assetId = "139247532251059", tris = 500, ref = "jungle_hibiscus", what = "two red hibiscus blooms in dark leaves"},
    veg2_jungle_stump = {assetId = "80638240272132", tris = 800, ref = "jungle_stump", what = "mossy stump wrapped in a vine, orange mushrooms"},
    -- BD-1315 biome kits (docs/250 S2): desert, tundra and volcano for the same slots, plus a jungle rock ledge. Roblox generate_mesh with
    -- prompts written from ChatGPT style sheets in the approved toy style (docs/evidence/2026-11-23-biome-kits); shown only through kitVisual.
    veg2_desert_saguaro = {assetId = "88215990023102", tris = 1190, ref = "kit_desert", what = "tall round-armed saguaro cactus with pink flowers"},
    veg2_desert_acacia = {assetId = "98055641929016", tris = 1500, ref = "kit_desert", what = "acacia tree with a wide flat umbrella canopy"},
    veg2_desert_cactus_cluster = {assetId = "73356820925066", tris = 1000, ref = "kit_desert", what = "three fat round cacti with yellow flowers"},
    veg2_desert_barrel = {assetId = "73501662599786", tris = 798, ref = "kit_desert", what = "squat barrel cactus with pink flowers"},
    veg2_desert_fruit_cactus = {assetId = "104357785768075", tris = 896, ref = "kit_desert", what = "small cactus with red fruits"},
    veg2_desert_grass = {assetId = "137246578898278", tris = 400, ref = "kit_desert", what = "dry golden grass tuft"},
    veg2_desert_flowers = {assetId = "94345384129402", tris = 500, ref = "kit_desert", what = "pink and yellow desert flowers"},
    veg2_desert_bones = {assetId = "96210042686377", tris = 700, ref = "kit_desert", what = "bleached dino rib bones in a sand mound"},
    veg2_desert_spire = {assetId = "133332310281004", tris = 1198, ref = "kit_desert", what = "red striped mesa rock spire"},
    veg2_desert_ledge = {assetId = "78999617003904", tris = 1000, ref = "kit_desert", what = "low sandstone ledge with a small cactus"},
    veg2_tundra_pine = {assetId = "119655066986735", tris = 1198, ref = "kit_tundra", what = "snowy pine with soft snow caps"},
    veg2_tundra_frost_tree = {assetId = "94552299953576", tris = 1500, ref = "kit_tundra", what = "frosted tree, white trunk, snowy teal crown"},
    veg2_tundra_berry_bush = {assetId = "84346387380367", tris = 900, ref = "kit_tundra", what = "snowy holly bush with red berries"},
    veg2_tundra_snow_mound = {assetId = "123505817236731", tris = 600, ref = "kit_tundra", what = "soft snow mound with a green sprout"},
    veg2_tundra_ice_crystals = {assetId = "101643348157940", tris = 700, ref = "kit_tundra", what = "pale blue ice crystals in snow"},
    veg2_tundra_grass = {assetId = "125854880822565", tris = 400, ref = "kit_tundra", what = "frosty grass tuft"},
    veg2_tundra_snowdrops = {assetId = "132615553392343", tris = 500, ref = "kit_tundra", what = "white and lilac snowdrops"},
    veg2_tundra_tusk = {assetId = "118081433288326", tris = 600, ref = "kit_tundra", what = "old tusks sticking out of snow"},
    veg2_tundra_boulder = {assetId = "82576923565628", tris = 700, ref = "kit_tundra", what = "grey boulder with a snow cap"},
    veg2_tundra_ice_spire = {assetId = "100307921925448", tris = 998, ref = "kit_tundra", what = "tall ice spire of rounded blocks"},
    veg2_tundra_ledge = {assetId = "88617261219663", tris = 1000, ref = "kit_tundra", what = "low snowy rock outcrop with icicles"},
    veg2_volcano_charred_tree = {assetId = "136574200915810", tris = 1500, ref = "kit_volcano", what = "regrowing tree with a dark trunk and fresh green leaves"},
    veg2_volcano_red_tree = {assetId = "99058049156741", tris = 1500, ref = "kit_volcano", what = "slender twisty tree with a round crown of red leaves"},
    veg2_volcano_boulder = {assetId = "93625416188101", tris = 700, ref = "kit_volcano", what = "ash-dusted pumice boulder with a fern sprout"},
    veg2_volcano_stump = {assetId = "99559384947949", tris = 798, ref = "kit_volcano", what = "charcoal stump with a green sprout"},
    veg2_volcano_fire_fern = {assetId = "117623704015728", tris = 900, ref = "kit_volcano", what = "fire-coloured fern shrub"},
    veg2_volcano_crystals = {assetId = "107214976859144", tris = 700, ref = "kit_volcano", what = "amber crystals on dark rocks"},
    veg2_volcano_ash_grass = {assetId = "90131431323706", tris = 400, ref = "kit_volcano", what = "ash grass with warm tips"},
    veg2_volcano_fire_flowers = {assetId = "87669606566547", tris = 500, ref = "kit_volcano", what = "red-orange fire flowers"},
    veg2_volcano_ledge = {assetId = "129149613550662", tris = 1000, ref = "kit_volcano", what = "cooled lava rock ledge with ash and a red-leaf plant"},
    veg2_jungle_ledge = {assetId = "79977803283463", tris = 1000, ref = "jungle_ledge", what = "mossy jungle rock ledge with vines"},
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
-- BD-1311: three-way pick: a below share1, b below share1 + share2, else c.
local function pick3(roll: number, a: string, share1: number, b: string, share2: number, c: string): string
    return if roll < share1 then a elseif roll < share1 + share2 then b else c
end

-- Which v2 key shows for a kit id in a sub-biome (BiomeMap id), with roll in [0, 1) a deterministic per-prop value. nil = keep the current
-- visual (dead trees, bare rocks, mushrooms, logs and landmarks are not part of this family).
function VegetationV2.visualFor(id: string, biome: string, roll: number): string?
    local beach = biome == "badlands" -- the palm beach zone of World V3
    local damp = biome == "fern" or biome == "marsh" or biome == "conifer"
    if id == "world_tree_canopy_s" then return pick3(roll, "veg2_tree_flower", .45, "veg2_tree_fruit", .3, "veg2_tree_oak") end
    if id == "world_tree_canopy_m" then
        return if biome == "meadow" then pick3(roll, "veg2_tree_fruit", .45, "veg2_tree_flower", .3, "veg2_tree_oak")
            else pick3(roll, "veg2_tree_oak", .35, "veg2_tree_flower", .35, "veg2_tree_fruit")
    end
    if id == "world_tree_canopy_l" then return choose(roll, "veg2_tree_twisty", "veg2_tree_oak", .6) end
    -- BD-1311: three soft pines (fir, cypress, bonsai) instead of the two cone stacks; the leaning bonsai stays rare so groves read as pines.
    if id == "world_tree_conifer_s" then return pick3(roll, "veg2_pine_fir", .45, "veg2_pine_cypress", .4, "veg2_pine_bonsai") end
    if id == "world_tree_conifer_m" or id == "world_tree_conifer_l" then return pick3(roll, "veg2_pine_fir", .4, "veg2_pine_cypress", .35, "veg2_pine_bonsai") end
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

-- BD-1315 (docs/250, contract with S1 BD-1314): the visual key for a placed slot in a whole-island biome kit, or nil = keep today's
-- visualFor(id, subBiome, roll). Pure: S1's BiomeClock / client swap reads CurrentBiome and calls this; placements, colliders and food
-- hosts never change. "meadow" is today's map (nil everywhere). layer (optional): "log" slots (a dead tree lying down) keep today's look.
-- BD-1315 desert, tundra and volcano kits: the same slots, one table per biome. Each entry maps a slot group to weighted picks
-- {key, share, ...}; the last share is implied. Groups: tree (every standing tree), bush (round bushes), small (mushroom clumps),
-- leafy (ferns, horsetail), flowers, grass, boulder_s / boulder (small / medium-large boulders), spire, ledge.
local KITS = {
    desert = {
        tree = {"veg2_desert_acacia", .65, "veg2_desert_saguaro"}, -- groves read as acacia savanna with lone saguaros
        bush = {"veg2_desert_barrel", .4, "veg2_desert_fruit_cactus", .35, "veg2_desert_cactus_cluster"},
        small = {"veg2_desert_bones", .15, "veg2_desert_barrel", .5, "veg2_desert_grass"},
        leafy = {"veg2_desert_grass", .6, "veg2_desert_flowers"},
        flowers = {"veg2_desert_flowers"}, grass = {"veg2_desert_grass"},
        boulder_s = {"veg2_desert_bones"}, boulder = {"veg2_desert_ledge"},
        spire = {"veg2_desert_spire"}, ledge = {"veg2_desert_ledge"},
    },
    tundra = {
        tree = {"veg2_tundra_pine", .6, "veg2_tundra_frost_tree"},
        bush = {"veg2_tundra_berry_bush", .65, "veg2_tundra_ice_crystals", .2, "veg2_tundra_snow_mound"},
        small = {"veg2_tundra_ice_crystals", .45, "veg2_tundra_snow_mound", .4, "veg2_tundra_tusk"},
        leafy = {"veg2_tundra_grass", .6, "veg2_tundra_snowdrops"},
        flowers = {"veg2_tundra_snowdrops"}, grass = {"veg2_tundra_grass"},
        boulder_s = {"veg2_tundra_boulder"}, boulder = {"veg2_tundra_boulder", .7, "veg2_tundra_ledge"},
        spire = {"veg2_tundra_ice_spire"}, ledge = {"veg2_tundra_ledge"},
    },
    volcano = { -- owner 2026-11-23: no painted fire, embers, glow or lava in meshes (flat and static); cooled volcanic land instead
        tree = {"veg2_volcano_red_tree", .7, "veg2_volcano_charred_tree"},
        bush = {"veg2_volcano_fire_fern", .6, "veg2_volcano_crystals"},
        small = {"veg2_volcano_stump", .5, "veg2_volcano_crystals", .3, "veg2_volcano_fire_fern"},
        leafy = {"veg2_volcano_ash_grass", .6, "veg2_volcano_fire_flowers"},
        flowers = {"veg2_volcano_fire_flowers"}, grass = {"veg2_volcano_ash_grass"},
        boulder_s = {"veg2_volcano_boulder"}, boulder = {"veg2_volcano_boulder", .7, "veg2_volcano_ledge"},
        ledge = {"veg2_volcano_ledge"}, -- spires keep today's grey rock pillar
    },
}
VegetationV2.Kits = KITS

local function slotGroup(id: string): string?
    if string.sub(id, 1, 11) == "world_tree_" then return "tree" end
    if id == "world_bush_a" or id == "world_bush_b" then return "bush" end
    if id == "world_mushrooms_a" then return "small" end
    if id == "world_fern_a" or id == "world_fern_b" or id == "world_horsetail_a" then return "leafy" end
    if id == "world_flowers_a" then return "flowers" end
    if id == "world_grass_a" or id == "world_grass_b" then return "grass" end
    if string.sub(id, 1, 14) == "world_boulder_" then return if string.sub(id, -2) == "_s" then "boulder_s" else "boulder" end
    if id == "world_rocks_spires" then return "spire" end
    if id == "world_rocks_ledge" then return "ledge" end
    return nil
end

local function weighted(list: {any}, roll: number): string
    local acc = 0
    for i = 1, #list - 1, 2 do
        acc += list[i + 1]
        if roll < acc then return list[i] end
    end
    return list[#list]
end

-- BD-1315 natural density (owner 2026-11-23: "think about ... how plants are naturally planted normally in biomes"): the share of the
-- collider-free small slots (bushes, mushroom clumps, ferns, flowers, grass) each kit keeps; the rest show nothing in that biome. Desert
-- and volcano are sparse with rare flowers, the tundra keeps pine stands but few flowers, the jungle stays dense. Trees, boulders, spires
-- and ledges always show (they have colliders, so hiding them would leave invisible walls).
VegetationV2.KitDensity = table.freeze({
    jungle = table.freeze({bush = 1, small = 1, leafy = 1, flowers = 1, grass = 1}),
    desert = table.freeze({bush = .55, small = .45, leafy = .35, flowers = .2, grass = .5}),
    tundra = table.freeze({bush = .8, small = .6, leafy = .6, flowers = .25, grass = .7}),
    volcano = table.freeze({bush = .45, small = .5, leafy = .3, flowers = .15, grass = .35}),
})

-- True when this slot shows nothing in that biome (only the collider-free groups above). roll = the same per-slot roll kitVisual gets;
-- a second value is derived from it so the hidden slots do not follow the visual picks.
function VegetationV2.kitHidden(biomeId: string, kitId: string, roll: number, layer: string?): boolean
    local density = VegetationV2.KitDensity[biomeId]
    local group = slotGroup(kitId)
    local keep = density and group and density[group]
    if keep == nil or layer == "log" then return false end
    local u = (roll * 7.31 + .137) % 1
    return u >= keep
end

function VegetationV2.kitVisual(biomeId: string, kitId: string, roll: number, layer: string?): string?
    if layer == "log" then return nil end
    local kit = KITS[biomeId]
    if kit then
        local group = slotGroup(kitId)
        local list = group and kit[group]
        return if list then weighted(list, roll) else nil
    end
    if biomeId ~= "jungle" then return nil end
    local id = kitId
    if id == "world_rocks_ledge" then return "veg2_jungle_ledge" end
    if string.sub(id, 1, 11) == "world_tree_" then
        -- every standing tree is jungle: mostly the buttress canopy tree, some twisty vine trees and flower palms for variety
        return pick3(roll, "veg2_jungle_canopy", .6, "veg2_tree_twisty", .25, "veg2_palm_flower")
    end
    if id == "world_bush_a" or id == "world_bush_b" then return choose(roll, "veg2_jungle_elephant_ear", "veg2_jungle_monstera", .5) end
    -- the mushroom slots grow to 4-12 studs (SmallBand): mostly leafy plants, a mossy stump only now and then
    if id == "world_mushrooms_a" then return pick3(roll, "veg2_jungle_elephant_ear", .5, "veg2_fern_a", .3, "veg2_jungle_stump") end
    if id == "world_fern_a" or id == "world_horsetail_a" then return choose(roll, "veg2_fern_a", "veg2_jungle_elephant_ear", .7) end
    if id == "world_fern_b" then return "veg2_fern_b" end
    if id == "world_flowers_a" then return choose(roll, "veg2_jungle_hibiscus", "veg2_flowers_hibiscus", .6) end
    if id == "world_grass_a" or id == "world_grass_b" then return choose(roll, "veg2_fern_a", "veg2_fern_b", .55) end
    if string.sub(id, 1, 14) == "world_boulder_" then return choose(roll, "veg2_rock_mossy", "veg2_rock_spiral", .65) end
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
