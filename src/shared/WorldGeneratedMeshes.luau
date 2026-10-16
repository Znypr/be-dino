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
