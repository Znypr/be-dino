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
-- BD-464 step 1 + BD-463 step 1 (docs/140, docs/120): Blender ground props (ground_*_v3) and plants (plant_*_v3) from assets/blender/world/fbx_v3.
-- NEW kinds, not replacements. assetId = "" means NOT uploaded yet: nothing is loaded and nothing is placed, and the world is EXACTLY what it was
-- before these entries existed. BD-463/464 step 2 (docs/140 "Placement"): BiomePlacement uses a key only when its assetId is a valid numeric id
-- (BiomePlacement.validAssetId), and each placed prop REPLACES existing small clutter (net-neutral phone triangle budget). placed = true means
-- "a placement rule reads this key once its id is filled in" (like Replacements above); it is NOT a claim that anything is on the island today.
-- tris = triangle count of the FBX; size = {x, height, z} studs of the mesh at scale 1 (Blender X, Z up, Y; the FBX pivot is the bbox bottom
-- centre), used as the kit-style extent for spacing, grounding and the budget. ImportedResources.loadGeneratedWorld loads a non-empty id into
-- ReplicatedStorage.GeneratedWorld; Arena places only the keys whose template really loaded.
Generated.Props = {
    ground_rock_small_v3 = {assetId = "", placed = true, tris = 68, size = {2.8, 1.2, 2.4}}, -- ground_rock_small_v3.fbx, 68 tris, Blender 2.8 x 2.4 x 1.2
    ground_rock_medium_v3 = {assetId = "", placed = true, tris = 278, size = {4.9, 2.3, 4.0}}, -- ground_rock_medium_v3.fbx, 278 tris, Blender 4.9 x 4.0 x 2.3
    ground_rock_mossy_v3 = {assetId = "", placed = true, tris = 262, size = {5.6, 3.2, 4.5}}, -- ground_rock_mossy_v3.fbx, 262 tris, Blender 5.6 x 4.5 x 3.2
    ground_log_fallen_v3 = {assetId = "", placed = true, tris = 199, size = {7.9, 3.0, 2.8}}, -- ground_log_fallen_v3.fbx, 199 tris, Blender 7.9 x 2.8 x 3.0
    ground_stump_roots_v3 = {assetId = "", placed = true, tris = 199, size = {7.1, 3.0, 5.9}}, -- ground_stump_roots_v3.fbx, 199 tris, Blender 7.1 x 5.9 x 3.0
    ground_mushrooms_v3 = {assetId = "", placed = true, tris = 303, size = {5.3, 2.9, 4.1}}, -- ground_mushrooms_v3.fbx, 303 tris, Blender 5.3 x 4.1 x 2.9
    ground_bush_round_v3 = {assetId = "", placed = true, tris = 340, size = {6.0, 2.7, 4.2}}, -- ground_bush_round_v3.fbx, 340 tris, Blender 6.0 x 4.2 x 2.7
    ground_bush_berry_v3 = {assetId = "", placed = true, tris = 304, size = {6.3, 2.1, 4.1}}, -- ground_bush_berry_v3.fbx, 304 tris, Blender 6.3 x 4.1 x 2.1
    plant_grass_broad_v3 = {assetId = "", placed = true, tris = 120, size = {2.0, 2.2, 2.3}}, -- plant_grass_broad_v3.fbx, 120 tris, Blender 2.0 x 2.3 x 2.2
    plant_grass_arch_v3 = {assetId = "", placed = true, tris = 105, size = {2.4, 2.1, 2.3}}, -- plant_grass_arch_v3.fbx, 105 tris, Blender 2.4 x 2.3 x 2.1
    plant_grass_low_v3 = {assetId = "", placed = true, tris = 90, size = {2.4, 1.2, 2.3}}, -- plant_grass_low_v3.fbx, 90 tris, Blender 2.4 x 2.3 x 1.2
    plant_jungle_leaf_v3 = {assetId = "", placed = true, tris = 168, size = {4.1, 3.5, 4.2}}, -- plant_jungle_leaf_v3.fbx, 168 tris, Blender 4.1 x 4.2 x 3.5
    plant_flowers_daisy_v3 = {assetId = "", placed = true, tris = 258, size = {2.3, 2.4, 2.4}}, -- plant_flowers_daisy_v3.fbx, 258 tris, Blender 2.3 x 2.4 x 2.4
    plant_flowers_yellow_v3 = {assetId = "", placed = true, tris = 201, size = {2.3, 2.3, 2.1}}, -- plant_flowers_yellow_v3.fbx, 201 tris, Blender 2.3 x 2.1 x 2.3
    plant_flowers_red_v3 = {assetId = "", placed = true, tris = 201, size = {2.6, 2.5, 2.3}}, -- plant_flowers_red_v3.fbx, 201 tris, Blender 2.6 x 2.3 x 2.5
    plant_fern_arch_v3 = {assetId = "", placed = true, tris = 189, size = {4.9, 2.1, 4.9}}, -- plant_fern_arch_v3.fbx, 189 tris, Blender 4.9 x 4.9 x 2.1
}
-- BD-296 (docs/140 "Cave wall rock forms", docs/120): six cave wall rock forms and the gate arch frame, Blender FBX in assets/blender/world/fbx_v3/cave_*_v3.fbx.
-- Their OWN table (not Props) so the island's BiomePlacement / Arena never sees them: only CaveProps reads it, through CaveHubProps.Slots (cave_form_*,
-- cave_gate_frame). assetId = "" means NOT uploaded: nothing is loaded, nothing is placed and the arch lantern light is not added, so the cave is exactly
-- what it is today. ImportedResources.loadGeneratedWorld loads a non-empty id into ReplicatedStorage.GeneratedWorld like the other keys.
-- tris = triangle count of the FBX; size = {x, height, depth} studs at scale 1 (Blender X, Z up, Y; pivot = bbox bottom centre, the wall side is the back).
Generated.CaveForms = {
    cave_rockform_slabs_v3 = {assetId = "", placed = false, tris = 336, size = {15.01, 12.68, 6.36}}, -- cave_rockform_slabs_v3.fbx, 336 tris
    cave_rockform_buttress_v3 = {assetId = "", placed = false, tris = 380, size = {12.5, 18.66, 7.82}}, -- cave_rockform_buttress_v3.fbx, 380 tris
    cave_rockform_ledge_v3 = {assetId = "", placed = false, tris = 308, size = {17.49, 11.25, 8.77}}, -- cave_rockform_ledge_v3.fbx, 308 tris
    cave_rockform_tumble_v3 = {assetId = "", placed = false, tris = 364, size = {18.44, 9.61, 8.65}}, -- cave_rockform_tumble_v3.fbx, 364 tris
    cave_rockform_fins_v3 = {assetId = "", placed = false, tris = 350, size = {10.85, 19.2, 7.57}}, -- cave_rockform_fins_v3.fbx, 350 tris
    cave_rockform_terrace_v3 = {assetId = "", placed = false, tris = 362, size = {20.44, 7.58, 7.83}}, -- cave_rockform_terrace_v3.fbx, 362 tris
    cave_gate_arch_v3 = {assetId = "", placed = false, tris = 456, size = {39.79, 25.79, 9.77}}, -- cave_gate_arch_v3.fbx, 456 tris
}
-- BD-463/464 step 2: true for a pasted Roblox asset id (digits only, no leading zero, 9-18 long). "" and anything else mean "not uploaded yet".
function Generated.validId(id: any): boolean
    if type(id) ~= "string" then return false end
    return #id >= 9 and #id <= 18 and string.match(id, "^[1-9]%d*$") == id
end
-- BD-474 (docs/140 "Colossal ancient trees"): colossal ancient trees for the `colossal` placement layer (BiomePlacement.Colossal, 80-140 studs), Blender FBX in
-- assets/blender/world/fbx_v3/. Today the layer shows the stand-ins (the _l kit models, i.e. the existing generated meshes scaled 3-8x).
-- assetId = "" means NOT uploaded: nothing is loaded, colossalFor() returns nil and the stand-in keeps being used. Fill a LOD0 id AND its _lod1 id
-- (BD-475: the tree is only used as a PAIR, a LOD0 without its LOD1 keeps the stand-in) and Arena.generatedProp uses that mesh for colossal
-- placements ONLY (ordinary size-l trees keep their meshes). Each mesh is fitted into the kit extent box like every generated tree (by height),
-- so the colossal height rule (80-140) and the placement stay as they are. WorldCulling swaps LOD0 and LOD1 by distance (ColossalRules).
-- Per entry (numbers of the Blender build, docs/140 and docs/evidence/2026-10-17-colossal/tris.txt, intended size in studs):
-- size = bbox {x, y, z} in Blender axes; base = trunk base offset from the bbox centre {x, y} (the pivot is the bbox bottom centre, so LOD0 and
-- LOD1 stand on different points: ColossalRules.lod1Offset moves LOD1 so the trunks coincide); trunk (LOD0 only) = {trunk diameter at about 15% of
-- the height, height of the bare trunk below the crown}, from which ColossalRules.colliders re-fits the invisible trunk colliders (BD-475).
Generated.Colossal = {
    tree_colossal_broadleaf_v3 = {assetId = "", placed = true, lod = 0, kit = "world_tree_canopy_l", standIn = "tree_jungle_giant", tris = 4154, size = {108.55, 105.84, 117.59}, base = {3.08, -0.87}, trunk = {26, 47}}, -- world_tree_colossal_broad_v3.fbx
    tree_colossal_pine_v3 = {assetId = "", placed = true, lod = 0, kit = "world_tree_conifer_l", standIn = "tree_pine", tris = 4052, size = {74.39, 80.34, 117.29}, base = {-0.67, -3.04}, trunk = {23, 36}}, -- world_tree_colossal_pine_v3.fbx
    tree_colossal_palm_v3 = {assetId = "", placed = true, lod = 0, kit = "world_tree_cycad_l", standIn = "tree_palm", tris = 3834, size = {118.55, 106.61, 105.03}, base = {-0.49, -0.38}, trunk = {21, 80}}, -- world_tree_colossal_palm_v3.fbx
    tree_colossal_broadleaf_v3_lod1 = {assetId = "", placed = true, lod = 1, kit = "world_tree_canopy_l", standIn = "tree_jungle_giant", tris = 925, size = {110.2, 95.34, 116.81}, base = {3.67, 3.4}}, -- world_tree_colossal_broad_v3_lod1.fbx
    tree_colossal_pine_v3_lod1 = {assetId = "", placed = true, lod = 1, kit = "world_tree_conifer_l", standIn = "tree_pine", tris = 927, size = {73.16, 77.66, 117.23}, base = {-4.16, -6.17}}, -- world_tree_colossal_pine_v3_lod1.fbx
    tree_colossal_palm_v3_lod1 = {assetId = "", placed = true, lod = 1, kit = "world_tree_cycad_l", standIn = "tree_palm", tris = 966, size = {118.55, 106.61, 105.02}, base = {-0.49, -0.38}}, -- world_tree_colossal_palm_v3_lod1.fbx
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
