--!strict
-- BD-1287 (docs/246 slice 1): with Config.MenusSaeFrameEnabled the Crystal Shop LANDING page is the shop menu kit window (client/KitWindow,
-- the owner's APPROVED Aura Shop window): the green header with "Crystal Shop", three kit cards (the cheapest aura with its picture, the next
-- trail, the Random Egg) and the tabs outside the window (Featured, Auras, Trails, Eggs, Potions). This file only turns the shop data into
-- kit data; the kit draws it. Tapping a card, its button or a tab opens that category page (the purchase confirm there does the buying; no
-- Robux path here). Numbers: Shared/SaeFrameRules; art: Shared/ShopKit2 (an empty kit 2 slot keeps the Toybox look).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Art = require(Shared.ShopArt)
local Kit2 = require(Shared.ShopKit2)
local Rules = require(Shared.SaeFrameRules)
local Preview = require(Shared.ShopPreview)
local ProgressionConfig = require(Shared.ProgressionConfig)
local KitWindow = require(script.Parent.KitWindow)

local M = {}

-- The item picture of a featured card: the kit 2 card picture (the dino wearing the aura / trail) when bound, else the uploaded item or
-- category picture. Returns the id and the part of the picture to show.
local function itemPicture(tab: string, item: any): (string?, any)
    local slot = Kit2.artSlot(tab, item)
    local kit2 = if slot then Kit2.image(Slots.Images, slot) else nil
    if kit2 then return kit2, Kit2.ArtCrop end
    if item then
        if tab == "auras" then return Art.validId(Slots.Images["aura_" .. tostring(item.id)]), nil
        elseif tab == "trails" then return Preview.trailIconId(ProgressionConfig.TrailIconAssetIds, item.id), nil
        elseif tab == "eggs" then return Art.eggProductId(Slots.Images), nil end
    end
    return Art.tileId(Slots.Images, tab), nil
end

-- The tab icons (uploaded): no "%" sale-tag picture exists, so Featured wears the crystal tab icon (the closest existing one).
local function tabIcon(tab: string): string?
    if tab == "featured" then return Art.tabIconId(Slots.Images, "crystals") end
    if tab == "potions" then return Art.validId(Slots.Images.potion_icon_speed_common) end
    return Art.tabIconId(Slots.Images, tab) or Art.tileId(Slots.Images, tab)
end

-- body: the Bootstrap panel body; spec: ShopTiles.build's {tabs, info, progress, onPick(tab), close(), openPotions(), selected?}. Returns false
-- when the kit window cannot open (the caller then draws the old landing tiles).
function M.build(body: GuiObject, spec: any): boolean
    local gem = Art.validId(require(Shared.UIIconAssets).amber) -- the orange crystal of the HUD counter (the approved buttons)
    local cards = {}
    for _, f in Rules.featured(spec.progress or {}) do
        local tab, item = f.tab, f.item
        local effect, rich = Rules.Lines[tab], nil
        if tab == "auras" and item then effect, rich = Rules.auraLine(item.growth) end
        local picture, crop = itemPicture(tab, item)
        table.insert(cards, {
            key = tab, rarity = Rules.cardRarity(f), name = Rules.cardTitle(f, Art.Titles[tab] or tab),
            rarityWord = if tab == "eggs" then Rules.EggWord elseif item and item.rarity then item.rarity else nil,
            picture = picture, pictureCrop = crop, effect = effect, effectRich = rich,
            price = if f.state == "buy" then f.price else nil, word = Rules.buttonWord(f), grey = f.state == "locked" or f.state == "soon",
            gem = gem, onPick = function() spec.onPick(tab) end,
        })
    end
    return KitWindow.open(body, {
        title = Rules.Title, colour = Rules.HeaderColour, cards = cards, layout = Rules.layout,
        onClose = function() if spec.close then spec.close() end end,
        rail = {
            tabs = Rules.RailTabs, words = Rules.RailWords, selected = spec.selected or "featured", icon = tabIcon,
            onTab = function(tab: string)
                if tab == "featured" then return end
                if tab == "potions" then if spec.openPotions then spec.openPotions() end return end
                spec.onPick(tab)
            end,
        },
    })
end

return M
