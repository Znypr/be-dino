--!strict
-- BD-1223 + BD-1224 (docs/242 benchmark gaps 8 and 9, "one art rule per game"): the World V3 island in one toy style.
-- BD-1223 ground: every terrain material the island uses has an authored MaterialVariant whose colour map is one flat white texture (uploaded
-- 2026-11-16, docs/77), so the photo grass, sand and rock textures are gone and the ground shows only its flat toon colour (Palette below),
-- matching the glossy round props and the cartoon landmarks. Terrain keeps its Enum materials (footsteps, food and placement read them).
-- BD-1224 plants: the spiky flat-shaded kit plants (ferns and horsetail) leave the shrub lists; the round glossy bush family takes their
-- share (Swaps below), so the shrub layer keeps its count and spacing.
-- Pure data, no Instances. Active only while Config.WorldV3Enabled and Config.ToonWorldEnabled are both true (off = exactly as before).
local WorldToon = {}
-- Image id of the flat white map (Decal 77613688457456 "BeDino_TerrainToonFlatWhite", 64 x 64 RGBA, plain white: a neutral map, not art).
WorldToon.FlatMap = "rbxassetid://86126915537669"
WorldToon.VariantPrefix = "BeDinoToon_" -- the authored variants (resources/visual-upgrade-bindings.json worldMaterials, tools/bind_visual_assets.py)
-- Flat toon colours (Studio A/B 2026-11-16, docs/evidence/2026-11-16-world-look): soft fresh greens like the tree crowns, warm sand and
-- paths, warm earth, and grey-violet volcano rock. Values are the terrain colour multipliers over the white map.
WorldToon.Palette = {
    Grass = {126, 188, 86},
    LeafyGrass = {102, 164, 74},
    Sand = {240, 222, 168},
    Limestone = {230, 202, 146}, -- plaza and paths
    Ground = {180, 136, 92},
    Mud = {136, 106, 78},
    Rock = {152, 148, 140},
    Slate = {130, 134, 142},
    Basalt = {104, 92, 96},
    Sandstone = {216, 162, 112},
}
-- Spiky kit plant -> round glossy replacement (the shrub layer picks the replacement wherever it would have picked the spiky one).
WorldToon.Swaps = {
    world_fern_a = "world_bush_a",
    world_fern_b = "world_bush_b",
    world_horsetail_a = "world_bush_a",
}

function WorldToon.enabled(config: any): boolean
    return type(config) == "table" and config.WorldV3Enabled == true and config.ToonWorldEnabled == true
end

-- Sorted material names (stable order for the server and the checks).
function WorldToon.materials(): {string}
    local out = {}
    for name in WorldToon.Palette do table.insert(out, name) end
    table.sort(out)
    return out
end

-- A weighted pick list {{id, weight}} with every spiky id swapped and equal ids merged (weights kept, order of first appearance kept).
function WorldToon.swapList(list: {{any}}): {{any}}
    local out, index = {}, {}
    for _, entry in list do
        local id = WorldToon.Swaps[entry[1]] or entry[1]
        local at = index[id]
        if at then out[at][2] += entry[2] else table.insert(out, {id, entry[2]}) index[id] = #out end
    end
    return out
end

return WorldToon
