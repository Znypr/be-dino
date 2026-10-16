--!strict
-- BD-206/207: Roblox-generated (generate_mesh) world props, published to the owner's account (docs/77 lists each id).
-- Visual only: the existing kit ids (WorldKitData) still decide placement, size class, part budget and invisible colliders;
-- visualFor() swaps which generated mesh is shown, and a failed load keeps the current kit model (nothing is ever missing).
local Generated = {}
-- key -> published mesh asset id (numeric string, no invented ids). placed=false: registered and load-checked, not yet placed.
Generated.Assets = {
    tree_broadleaf = {assetId = "137262237243889", placed = true},
    tree_pine = {assetId = "123860208068220", placed = true},
    tree_palm = {assetId = "115520379209668", placed = true},
    tree_birch = {assetId = "132703556702568", placed = true},
    tree_jungle_giant = {assetId = "100306166052872", placed = true},
    tree_burnt = {assetId = "71416776916365", placed = true},
    rock_mossy_boulder = {assetId = "135107793396569", placed = true},
    rock_pillar = {assetId = "101039067942415", placed = true},
    rock_sand_cliff = {assetId = "122546672856917", placed = true},
    rock_crystal = {assetId = "84690157197711", placed = true},
    rock_lava = {assetId = "118262268018795", placed = true},
    rock_pebbles = {assetId = "125187345067740", placed = true},
    bush = {assetId = "70576143860722", placed = true},
    landmark_dino_statue = {assetId = "82545380144820", placed = true},
    food_drumstick = {assetId = "71496347169753", placed = false}, -- BD-207, needs FoodService rules
    food_egg = {assetId = "80664439797104", placed = false},
    nest = {assetId = "102765517629578", placed = false},
}
-- BD-462 (docs/140): owner-approved V3 tree meshes (Blender, assets/blender/world/fbx_v3/*.fbx) that replace the Roblox-generated
-- broadleaf, pine and palm once uploaded. assetId = "" means NOT uploaded yet: nothing is loaded, replacementFor() returns nil and the
-- current generated mesh above keeps being used (same visual as before this table existed). Paste the numeric MeshPart-model id here
-- after the owner uploads the FBX (docs/140 and the BD-462 row have the click-by-click steps). Only these three tree kinds are covered.
Generated.Replacements = {
    tree_broadleaf_v3 = {assetId = "", placed = true, replaces = "tree_broadleaf"}, -- world_tree_broad_v3.fbx, 726 tris
    tree_pine_v3 = {assetId = "", placed = true, replaces = "tree_pine"}, -- world_tree_pine_v3.fbx, 462 tris
    tree_palm_v3 = {assetId = "", placed = true, replaces = "tree_palm"}, -- world_tree_palm_v3.fbx, 700 tris
}
-- BD-464 step 1 (docs/140, docs/120): Blender ground props for tree bases and clearings (assets/blender/world/fbx_v3/ground_*_v3.fbx).
-- NEW kinds, not replacements: assetId = "" means NOT uploaded yet, nothing is loaded and nothing is placed. Nothing reads these keys for
-- placement until step 2 (placement grammar plus the net-neutral replacement of small clutter, after the owner uploads and picks).
-- Pasting an id here only makes ImportedResources load the mesh into ReplicatedStorage.GeneratedWorld; Arena does not place it yet.
-- BD-463 step 1 (docs/140, docs/120) adds the eight plant_*_v3 kinds (grass tufts, jungle plant, flower clusters, fern) to this table the same way:
-- empty ids, placed = false, nothing places them until BD-463 step 2 (placement that REPLACES some existing clutter, net-neutral on the phone triangle budget).
Generated.Props = {
    ground_rock_small_v3 = {assetId = "", placed = false}, -- ground_rock_small_v3.fbx, 68 tris
    ground_rock_medium_v3 = {assetId = "", placed = false}, -- ground_rock_medium_v3.fbx, 278 tris
    ground_rock_mossy_v3 = {assetId = "", placed = false}, -- ground_rock_mossy_v3.fbx, 262 tris
    ground_log_fallen_v3 = {assetId = "", placed = false}, -- ground_log_fallen_v3.fbx, 199 tris
    ground_stump_roots_v3 = {assetId = "", placed = false}, -- ground_stump_roots_v3.fbx, 199 tris
    ground_mushrooms_v3 = {assetId = "", placed = false}, -- ground_mushrooms_v3.fbx, 303 tris
    ground_bush_round_v3 = {assetId = "", placed = false}, -- ground_bush_round_v3.fbx, 340 tris
    ground_bush_berry_v3 = {assetId = "", placed = false}, -- ground_bush_berry_v3.fbx, 304 tris
    plant_grass_broad_v3 = {assetId = "", placed = false}, -- plant_grass_broad_v3.fbx, 120 tris
    plant_grass_arch_v3 = {assetId = "", placed = false}, -- plant_grass_arch_v3.fbx, 105 tris
    plant_grass_low_v3 = {assetId = "", placed = false}, -- plant_grass_low_v3.fbx, 90 tris
    plant_jungle_leaf_v3 = {assetId = "", placed = false}, -- plant_jungle_leaf_v3.fbx, 168 tris
    plant_flowers_daisy_v3 = {assetId = "", placed = false}, -- plant_flowers_daisy_v3.fbx, 258 tris
    plant_flowers_yellow_v3 = {assetId = "", placed = false}, -- plant_flowers_yellow_v3.fbx, 201 tris
    plant_flowers_red_v3 = {assetId = "", placed = false}, -- plant_flowers_red_v3.fbx, 201 tris
    plant_fern_arch_v3 = {assetId = "", placed = false}, -- plant_fern_arch_v3.fbx, 189 tris
}
-- BD-474 (docs/140 "Colossal ancient trees"): colossal ancient trees for the `colossal` placement layer (BiomePlacement.Colossal, 80-140 studs), Blender FBX in
-- assets/blender/world/fbx_v3/. Today the layer shows the stand-ins (the _l kit models, i.e. the existing generated meshes scaled 3-8x).
-- assetId = "" means NOT uploaded: nothing is loaded, colossalFor() returns nil and the stand-in keeps being used. Fill a LOD0 id and
-- Arena.generatedProp uses that mesh for colossal placements ONLY (ordinary size-l trees keep their meshes). Each mesh is fitted into the
-- kit extent box like every generated tree (by height), so the colossal height rule (80-140) and the placement stay as they are.
-- The _lod1 entries (about 1,000 tris, same silhouette) are stored and loaded once their id exists, but NOTHING swaps to them yet: that is
-- BD-475 (WorldCulling radius and the LOD1 swap). `trunk` = {trunk diameter at about 15% of the height, height of the bare trunk below the crown} of the intended-size
-- mesh in studs (Blender build, docs/140 "Colossal ancient trees"), for the collider follow-up (the kit collider boxes are thinner than a colossal trunk, docs/140 "Colossal ancient trees" "Left to do").
Generated.Colossal = {
    tree_colossal_broadleaf_v3 = {assetId = "", placed = true, lod = 0, kit = "world_tree_canopy_l", standIn = "tree_jungle_giant", tris = 4154, trunk = {26, 47}}, -- world_tree_colossal_broad_v3.fbx
    tree_colossal_pine_v3 = {assetId = "", placed = true, lod = 0, kit = "world_tree_conifer_l", standIn = "tree_pine", tris = 4052, trunk = {23, 36}}, -- world_tree_colossal_pine_v3.fbx
    tree_colossal_palm_v3 = {assetId = "", placed = true, lod = 0, kit = "world_tree_cycad_l", standIn = "tree_palm", tris = 3834, trunk = {21, 80}}, -- world_tree_colossal_palm_v3.fbx
    tree_colossal_broadleaf_v3_lod1 = {assetId = "", placed = false, lod = 1, kit = "world_tree_canopy_l", standIn = "tree_jungle_giant", tris = 925}, -- world_tree_colossal_broad_v3_lod1.fbx
    tree_colossal_pine_v3_lod1 = {assetId = "", placed = false, lod = 1, kit = "world_tree_conifer_l", standIn = "tree_pine", tris = 939}, -- world_tree_colossal_pine_v3_lod1.fbx
    tree_colossal_palm_v3_lod1 = {assetId = "", placed = false, lod = 1, kit = "world_tree_cycad_l", standIn = "tree_palm", tris = 966}, -- world_tree_colossal_palm_v3_lod1.fbx
}
-- The LOD0 colossal key to try first for a kit id (e.g. "world_tree_canopy_l" -> "tree_colossal_broadleaf_v3"), or nil while its id is empty.
-- Callers must only ask for placements of the colossal layer; the same kit id is also used by ordinary size-l trees.
function Generated.colossalFor(kitId: string): string?
    local entries: {[string]: any} = Generated.Colossal
    for key, info in entries do
        if info.lod == 0 and info.kit == kitId and info.assetId ~= "" then return key end
    end
    return nil
end
-- Returns the V3 key to try first for a current key (e.g. "tree_palm" -> "tree_palm_v3"), or nil while that V3 id is still empty.
function Generated.replacementFor(key: string): string?
    for replacementKey, info in Generated.Replacements do
        if info.replaces == key and info.assetId ~= "" then return replacementKey end
    end
    return nil
end
-- Kit ids this module may replace (the rest keep their current models). Returns a key of Generated.Assets or nil.
-- biome: BiomeMap id ("meadow", "badlands", "volcanic", ...); roll in [0,1) is a deterministic per-prop value.
local TREES = {
    world_tree_conifer_s = "tree_pine", world_tree_conifer_m = "tree_pine", world_tree_conifer_l = "tree_pine",
    world_tree_canopy_s = "tree_birch", world_tree_canopy_m = "tree_broadleaf", world_tree_canopy_l = "tree_jungle_giant",
    world_tree_cycad_s = "tree_palm", world_tree_cycad_m = "tree_palm", world_tree_cycad_l = "tree_palm",
    world_tree_dead_s = "tree_burnt", world_tree_dead_m = "tree_burnt", world_tree_dead_l = "tree_burnt",
    world_bush_a = "bush", world_bush_b = "bush",
    world_boulder_mossy_s = "rock_mossy_boulder", world_boulder_mossy_m = "rock_mossy_boulder", world_boulder_mossy_l = "rock_mossy_boulder",
    world_rocks_spires = "rock_pillar", world_rocks_ledge = "rock_sand_cliff",
    world_landmark_dino_statue = "landmark_dino_statue",
}
Generated.KitMap = TREES
-- BD-460 (docs/138): per-asset foliage tone. Multiplies the mesh's own texture (SurfaceAppearance.Color, applied once per key on the template, so
-- no per-prop or per-frame cost). Less blue and a little less green/red: the minty crowns turn leaf green and the sunlit treetops stop clipping.
-- Only foliage keys; rocks, the burnt tree and the landmark keep their art colours. Every channel in [0.75, 1] (checked by verify_world_art).
Generated.Tone = {
    tree_broadleaf = {.94, .92, .80}, tree_birch = {.94, .92, .80}, tree_jungle_giant = {.94, .92, .80},
    tree_palm = {.95, .93, .84}, tree_pine = {.95, .94, .86}, bush = {.94, .92, .82},
}
local BARE = {world_boulder_bare_s = true, world_boulder_bare_m = true, world_boulder_bare_l = true}
Generated.BareIds = BARE
function Generated.visualFor(id: string, biome: string, roll: number): string?
    local direct = TREES[id]
    if direct then return direct end
    if not BARE[id] then return nil end
    if biome == "volcanic" then return if roll < .18 and id ~= "world_boulder_bare_s" then "rock_crystal" else "rock_lava" end
    if biome == "badlands" then
        if id == "world_boulder_bare_s" then return "rock_pebbles" end
        return if roll < .16 then "rock_crystal" else "rock_sand_cliff"
    end
    return if id == "world_boulder_bare_s" then "rock_pebbles" else "rock_mossy_boulder"
end
return Generated
