--!strict
-- BD-1248 (owner 2026-11-16: the plaza stalls are "not what famous roblox experiences do with their 3d shops and texts"; concept sheet
-- docs/evidence/2026-11-16-plaza-shops-v2, owner "Yes, build them"): the four plaza stalls of BD-1221 become themed shop buildings.
-- One generated MeshPart per building (Roblox generate_mesh, docs/77), ONE chunky generated wooden signboard per shop whose words are a
-- SurfaceGui on the board face (exact letters, the game font, thick dark outline, an icon), and a small V3 low-poly dino shopkeeper behind the
-- counter that plays the authored idle loop and the happy clip (Shared/LowPolyClips, BD-1217). No floating BillboardGui words, no stone sign.
-- Same spots, stations, screens and walk-up prompts as PlazaHubLayout (the "At home" rule of BD-1105 / BD-1221 option A is unchanged).
-- Pure data and math, no Instances. Active only while Config.WorldV3Enabled, Config.PlazaHubEnabled and Config.PlazaShopsV2Enabled are all true.
-- Shop frame = the PlazaHubLayout stall frame: local x = to the right as you face the shop, local z = away from the plaza centre; the
-- generated buildings face their own -Z, so a building is turned to face the centre like every stall.
local PlazaShopsLayout = {}

-- Published generate_mesh Models (one MeshPart each, docs/77 "plaza_shop_*" lines). tris = the maxTriangles the job was asked for.
PlazaShopsLayout.Assets = {
    shop_egg = {assetId = "102770540776592", tris = 8000},
    shop_potion = {assetId = "120298016764631", tris = 8000},
    shop_gem = {assetId = "101902619409856", tris = 8000},
    shop_fossil = {assetId = "96802664646030", tris = 8000},
    shop_signboard = {assetId = "133588952843204", tris = 1500},
}

-- The sign: the generated board stretched wide (w x h x d studs) with the words on its front face (the side toward the plaza centre).
-- PixelsPerStud sets the SurfaceGui canvas; Stroke is the word outline in canvas pixels.
PlazaShopsLayout.Sign = {key = "shop_signboard", w = 15, h = 5, d = 1.4, pixelsPerStud = 40, stroke = 7, iconShare = .3}
PlazaShopsLayout.Font = "FredokaOne" -- the game font (UITheme)
PlazaShopsLayout.WordColor = {255, 236, 150} -- warm yellow fill like the concept letters
PlazaShopsLayout.StrokeColor = {70, 36, 20} -- dark brown outline

-- station / screen = PlazaHubLayout.Stalls (matched by station). word = the ONE label of the shop. icon = {table, key}: "ui" = UIIconAssets,
-- "slot" = AssetSlots.Images, "art" = ArtworkAssets (existing uploaded icons, nothing new). building.size = fit box (w, h, d studs, uniform
-- scale), building.z = local z of the building centre. sign = {y above the ground of the board centre, z local z of the board centre}.
-- keeper = {species (LowPolyDinoAssets), x, z local, y above the ground of its feet, height studs}.
PlazaShopsLayout.Shops = {
    {station = "nests", word = "EGGS", icon = {"ui", "egg"},
        building = {key = "shop_egg", size = {19, 22, 17}, z = 5},
        sign = {y = 14.8, z = -2.2},
        keeper = {species = "compy", x = 0, z = 3, y = 4.6, height = 6.5}},
    {station = "potions", word = "POTIONS", icon = {"art", "potion_growth_base"},
        building = {key = "shop_potion", size = {20, 20, 18}, z = 5},
        sign = {y = 15, z = -4.5},
        keeper = {species = "triceratops", x = 1.5, z = 3, y = 4.4, height = 5.5}},
    {station = "style", word = "SHOP", icon = {"slot", "notify_crystal"},
        building = {key = "shop_gem", size = {19, 24, 15}, z = 4},
        sign = {y = 13.6, z = -2.9},
        keeper = {species = "stegosaurus", x = 0, z = 2.5, y = 5.2, height = 6}},
    {station = "index", word = "DINOS", icon = {"ui", "dinos"},
        building = {key = "shop_fossil", size = {19, 18.5, 20}, z = 6},
        sign = {y = 15.2, z = -4},
        keeper = {species = "tyrannosaurus", x = 1, z = 4, y = 4.4, height = 6.5}},
}

-- Shopkeeper motion: the authored idle loop all the time, the happy clip every HappyEvery seconds (+ up to HappyJitter), animated on the
-- client within KeeperRange studs only. Reduce Motion keeps them still.
PlazaShopsLayout.HappyEvery = 7
PlazaShopsLayout.HappyJitter = 5
PlazaShopsLayout.KeeperRange = 120

function PlazaShopsLayout.enabled(config: any): boolean
    return type(config) == "table" and config.WorldV3Enabled == true and config.PlazaHubEnabled == true and config.PlazaShopsV2Enabled == true
end

function PlazaShopsLayout.shop(station: string): any?
    for _, s in PlazaShopsLayout.Shops do
        if s.station == station then return s end
    end
    return nil
end

-- Uniform scale that fits a native box into the target box (the largest that fits every side).
function PlazaShopsLayout.fit(native: {number}, target: {number}): number
    local k = math.huge
    for i = 1, 3 do
        if native[i] > 0 then k = math.min(k, target[i] / native[i]) end
    end
    return if k == math.huge then 1 else k
end

-- Letter height (studs) of a word on the board: the SurfaceGui text is TextScaled, so a long word shrinks to the text area (row = 90% x 84% of
-- the board, the icon takes iconShare of it); FredokaOne capitals advance about .62 em. MinLetter = readable from the spawn (about 46 studs).
PlazaShopsLayout.MinLetter = 2
function PlazaShopsLayout.letterHeight(word: string): number
    local s = PlazaShopsLayout.Sign
    if #word == 0 then return 0 end
    local textW, rowH = s.w * .9 * (.98 - s.iconShare), s.h * .84
    return math.min(rowH, textW / (#word * .62))
end

return PlazaShopsLayout
