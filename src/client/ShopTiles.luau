--!strict
-- BD-047: Crystal Shop art, drawing only. Rules and ids come from Shared.ShopArt (tested by tools/verify_shop_tiles.py); the images are
-- Blender renders (tools/blender/build_shop_tiles.py). Every function does nothing, and today's look stays, while its image slot is empty.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Slots = require(Shared.AssetSlots)
local Art = require(Shared.ShopArt)
local C = Theme.Colors

local Tiles = {}
-- true when the shop was opened from SHOP / the crystal counter and the landing page should show instead of a category.
Tiles.landing = false

local function image(parent: GuiObject, name: string, id: string, anchor: Vector2, position: UDim2, size: UDim2, z: number): ImageLabel
    local img = Instance.new("ImageLabel")
    img.Name, img.BackgroundTransparency, img.BorderSizePixel, img.Image, img.ScaleType = name, 1, 0, id, Enum.ScaleType.Fit
    img.AnchorPoint, img.Position, img.Size, img.ZIndex, img.Parent = anchor, position, size, z, parent
    return img
end

-- The live numbers the tile subtitles read: p = the decoded progression profile.
function Tiles.info(p: any, eggPrice: number, crystals: number, randomBlocked: boolean?): {[string]: number}
    return {auras = Art.countOwned(p.auras), trails = Art.countOwned(p.trails), eggPrice = eggPrice, crystals = crystals, randomBlocked = if randomBlocked then 1 else 0}
end

-- Decide whether the next shop open starts on the landing page (call before open("auras")).
function Tiles.enter(tabs: {string})
    Tiles.landing = Art.landingReady(Slots.Images, tabs)
end

-- A leading icon on a shop tab button (the button keeps its text). No icon id: nothing changes.
function Tiles.decorateTab(button: TextButton, tab: string, height: number)
    local id = Art.tabIconId(Slots.Images, tab)
    if not id then return end
    local layout = Art.tabLayout(true, height)
    local pad = Instance.new("UIPadding")
    pad.PaddingLeft = UDim.new(0, layout.pad)
    pad.Parent = button
    -- children sit inside the padded area, so the icon steps back out by the pad
    image(button, "TabIcon", id, Vector2.new(0, .5), UDim2.new(0, 4 - layout.pad, .5, 0), UDim2.fromOffset(layout.icon, layout.icon), button.ZIndex + 1)
    button.TextSize = layout.textSize
end

-- The Eggs product picture: the green-spotted egg when its id exists. Returns true when it drew (the caller then skips the old egg).
function Tiles.eggProduct(parent: GuiObject, x: number, y: number, size: number): boolean
    local id = Art.eggProductId(Slots.Images)
    if not id then return false end
    image(parent, "GreenSpottedEgg", id, Vector2.zero, UDim2.fromOffset(x, y), UDim2.fromOffset(size, size), parent.ZIndex + 1)
    return true
end

-- The landing page: one tall illustrated tile per visible tab. ui = Bootstrap's {label, box}; spec = {tabs, info, onPick(tab)}.
-- Each tile is ONE button (the whole card), far larger than the 44 px tap target. Words are live text, never baked into the picture.
function Tiles.build(ui, body: GuiObject, spec)
    local layout = Art.tileLayout(#spec.tabs)
    local total = #spec.tabs * layout.width + (#spec.tabs - 1) * Art.TileGap
    local x0 = math.floor((824 - total) / 2)
    for i, tab in spec.tabs do
        local x = x0 + (i - 1) * (layout.width + Art.TileGap)
        local card = Instance.new("TextButton")
        card.Name, card.Text, card.AutoButtonColor = "ShopTile_" .. tab, "", true
        card.Position, card.Size, card.BackgroundColor3 = UDim2.fromOffset(x, 0), UDim2.fromOffset(layout.width, layout.height), Color3.fromRGB(61, 58, 73)
        card.ZIndex, card.Parent = body.ZIndex + 1, body
        Theme.decorate(card, 8)
        local picture = Art.tileId(Slots.Images, tab)
        if picture then
            image(card, "TileArt", picture, Vector2.zero, UDim2.fromOffset(6, 4), UDim2.fromOffset(layout.image, layout.image), card.ZIndex + 1)
        end
        local title = ui.label(card, Art.Titles[tab], 0, layout.image + 6, layout.width, 34, 24)
        title.Name = "TileTitle"
        local sub = ui.label(card, Art.subtitle(tab, spec.info), 4, layout.image + 40, layout.width - 8, 48, 18, C.gold)
        sub.Name = "TileSubtitle"
        local open = ui.box(card, 8, layout.height - 50, layout.width - 16, 44, C.accent, card.ZIndex + 1)
        open.Name = "TileOpen"
        local words = ui.label(open, "OPEN", 0, 0, layout.width - 16, 44, 22)
        words.Name = "TileOpenText"
        card.Activated:Connect(function() spec.onPick(tab) end)
    end
end

return Tiles
