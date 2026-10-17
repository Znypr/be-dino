--!strict
-- BD-047: pure rules for the Crystal Shop art: leading tab icons, the green-spotted egg and the landing page tiles (docs/45 section B).
-- No Instances here: src/client/ShopTiles.luau draws what this returns. Tested by tools/verify_shop_tiles.py.
-- Every image is optional. An image shows only when its slot (src/shared/AssetSlots.luau Images, filled by tools/bind_assets.py) holds a
-- real "rbxassetid://N"; while a slot is empty the shop keeps today's look (text-only tabs, the old egg picture, no landing page).
local P = {}

P.Tabs = {"auras", "trails", "eggs", "conditions", "crystals"}
P.Titles = {auras = "Auras", trails = "Trails", eggs = "Eggs", conditions = "Conditions", crystals = "Crystals"}
-- The leading icon slot of each tab. EGGS wears the green-spotted egg (docs/45: the same icon is the Eggs product art).
P.TabIconKeys = {auras = "shop_tab_auras", trails = "shop_tab_trails", eggs = "egg_green_spotted", conditions = "shop_tab_conditions", crystals = "shop_tab_crystals"}
P.EggProductKey = "egg_green_spotted"
P.TileWidthMax = 190
P.TileGap = 10
P.MinText = 14

function P.tileKey(tab: string): string return "shop_tile_" .. tab end

-- A usable image id, or nil.
function P.validId(id: any): string?
    if type(id) == "string" and string.match(id, "^rbxassetid://%d+$") then return id end
    return nil
end

-- images: a name -> id table (AssetSlots.Images, or Theme.ImageIds).
function P.tabIconId(images: {[string]: string}?, tab: string): string?
    local key = P.TabIconKeys[tab]
    return if images and key then P.validId(images[key]) else nil
end

function P.eggProductId(images: {[string]: string}?): string?
    return if images then P.validId(images[P.EggProductKey]) else nil
end

function P.tileId(images: {[string]: string}?, tab: string): string?
    return if images then P.validId(images[P.tileKey(tab)]) else nil
end

-- The landing page shows only when EVERY visible tab has its tile image, so a half-uploaded set never shows a gap.
function P.landingReady(images: {[string]: string}?, tabs: {string}): boolean
    if #tabs == 0 then return false end
    for _, tab in tabs do
        if P.tileId(images, tab) == nil then return false end
    end
    return true
end

-- Tab button layout: with an icon the text gets a left pad and 17 px text so "CONDITIONS" still fits a 155 px tab.
function P.tabLayout(hasIcon: boolean, height: number): {icon: number, pad: number, textSize: number}
    if not hasIcon then return {icon = 0, pad = 0, textSize = 20} end
    local icon = math.clamp(height - 8, 30, 36)
    return {icon = icon, pad = icon + 6, textSize = 17}
end

-- Landing tiles: how wide and tall each one is for `count` tiles in a 824 px body. Tall cards: picture, name, one short line, OPEN.
function P.tileLayout(count: number): {width: number, image: number, height: number}
    local n = math.max(1, count)
    local width = math.min(P.TileWidthMax, math.floor((824 - (n - 1) * P.TileGap) / n))
    local image = width - 12
    return {width = width, image = image, height = image + 6 + 34 + 48 + 44 + 6}
end

-- How many entries of an owned-map ({[id] = true}) are set.
function P.countOwned(owned: any): number
    local n = 0
    if type(owned) == "table" then
        for _, value in owned do if value == true then n += 1 end end
    end
    return n
end

-- The short live line under a tile's name (docs/72: kid words, no jargon). info: {auras, trails, eggPrice, crystals}.
function P.subtitle(tab: string, info: {[string]: number}): string
    if tab == "auras" then
        local n = info.auras or 0
        return if n > 0 then n .. " yours" else "Glow around you"
    elseif tab == "trails" then
        local n = info.trails or 0
        return if n > 0 then n .. " yours" else "Leave a trail"
    elseif tab == "eggs" then
        return (info.eggPrice or 0) .. " Crystals"
    elseif tab == "conditions" then
        return "Better eggs"
    elseif tab == "crystals" then
        return "You have " .. (info.crystals or 0)
    end
    return ""
end

return P
