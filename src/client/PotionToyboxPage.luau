--!strict
-- BD-1205 (docs/236, finding P-d0e74b / P-6bd182 / P-33416f / P-1b265a): the Potion Shop in the "Toybox" look. ShopScreens calls this only while
-- Config.ToyboxUIEnabled is on (Theme.Toybox exists); flag off, the shop is drawn exactly as before. Client presentation only: no remote, no price,
-- no stock rule, no save; a tap still only opens the confirm page / uses the potion through the callbacks it is given.
-- Parts (rects in Shared.ToyboxKit.potionLayout): a cream info row (restock chip left, "Rarer potions show up less often." right), the six offers as
-- equal cream cards that fill the body width (12 px gaps) with ONE full-width buy button each (green + crystal icon, grey only for sold out), and the
-- cream "Your potions" panel with one row of use chips under them. Everything scrolls together when a small window has no room. Flat colours only.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Layout = require(Shared.ToyboxLayout)
local PriceGroup = require(Shared.PriceGroup)
local PotionArt = require(Shared.PotionArt)
local ProgressionConfig = require(Shared.ProgressionConfig)
local ProgressionRules = require(Shared.ProgressionRules)
local ShopCardState = require(Shared.ShopCardState)
local TimerWords = require(Shared.TimerWords)
local UIFormat = require(Shared.UIFormat)
local C = Theme.Colors

local Page = {}
local SOLD_OUT = Color3.fromRGB(70, 72, 82) -- ShopCard.SoldOutColor: the nearest gloss button is the grey one

local function size(r: any): UDim2 return UDim2.fromOffset(r.w, r.h) end
local function pos(r: any): UDim2 return UDim2.fromOffset(r.x, r.y) end

-- The potion picture inside its tile: the bound icon; when that picture does not load, the generic bottle (the common icon of the kind, else the
-- speed bottle), and when even that is missing the code-drawn flask. Never a blank tile (finding P-6bd182).
local function picture(tile: GuiObject, item: any)
    local slot = Kit.potionIconSlot(Slots.Images :: any, item.id, item.kind)
    local function flask()
        local root = Instance.new("Frame")
        root.Name, root.BackgroundTransparency, root.Size, root.Position, root.ZIndex = "PotionFlask", 1, UDim2.fromScale(0.9, 0.9), UDim2.fromScale(0.05, 0.05), tile.ZIndex + 2
        root.Parent = tile
        PotionArt.build(root, item.kind, item.rarity)
    end
    if slot == nil then flask() return end
    local image = Instance.new("ImageLabel")
    image.Name, image.BackgroundTransparency, image.Image, image.ScaleType = "PotionImage", 1, (Slots.Images :: any)[slot], Enum.ScaleType.Fit
    image.AnchorPoint, image.Position, image.Size, image.ZIndex = Vector2.new(0.5, 0.5), UDim2.fromScale(0.5, 0.5), UDim2.fromScale(0.86, 0.86), tile.ZIndex + 2
    image.Parent = tile
    task.spawn(function() -- an icon that never loads is swapped for the generic bottle, then for the flask
        local ok = pcall(function() game:GetService("ContentProvider"):PreloadAsync({image}) end)
        if not tile.Parent then return end
        if ok and image.IsLoaded then return end
        local generic = Kit.potionIconSlot(Slots.Images :: any, "none", "speed")
        if generic ~= nil and (Slots.Images :: any)[generic] ~= image.Image then
            image.Image = (Slots.Images :: any)[generic]
            pcall(function() game:GetService("ContentProvider"):PreloadAsync({image}) end)
            if tile.Parent and image.IsLoaded then return end
        end
        image.Visible = false
        flask()
    end)
end

-- The crystal icon and the price number are ONE group centred on the button (BD-1192, Shared.PriceGroup), like the Crystal Shop cards.
local function priceGroup(ui, button: TextButton, price: number, height: number, width: number)
    local iconSize = math.clamp(height - 12, 24, 40)
    button.Text = UIFormat.number(price)
    button.TextXAlignment = Enum.TextXAlignment.Left
    local function measure(textSize: number): number
        local ok, bounds = pcall(function() return game:GetService("TextService"):GetTextSize(button.Text, textSize, button.Font, Vector2.new(10000, 200)).X end)
        return if ok and typeof(bounds) == "number" then bounds else #button.Text * textSize * 0.6
    end
    local group = PriceGroup.layout(measure, math.max(button.TextSize, 14), 14, width, iconSize, 8, 8)
    button.TextSize = group.size
    local place = PriceGroup.placement(group)
    local icon = ui.art(button, "amber", place.iconPos, (height - iconSize) / 2, iconSize)
    if icon then icon.Name = "CrystalIcon" end
    local pad = Instance.new("UIPadding")
    pad.Name, pad.PaddingLeft, pad.Parent = "IconPad", UDim.new(0, place.padLeft), button
    button:SetAttribute("PriceGroupW", group.groupW)
end

-- spec = {scale, bodyW, bodyH, p (progression), window, crystals, closeSide, onBuy(item), onUse(item)}; ui = {label, button, art}.
-- Draws into `body`, puts the crystal wallet in `header` (left of the X). Returns {restock = the TextLabel of the restock chip, layout = the rects}.
function Page.build(ui, body: GuiObject, header: GuiObject, spec)
    local ShopPage = require(script.Parent.ShopToyboxPage)
    local lay = Kit.potionLayout(spec.scale, spec.bodyW, spec.bodyH)
    local P = Kit.Potions
    local color = Theme.RarityColors

    -- the info row: restock chip left, the note right, both dark ink on cream (no text on the studs)
    local chip, restock = Layout.chip(body, TimerWords.restockIn(0), size(lay.restock), pos(lay.restock))
    chip.Name = "RestockChip"
    restock.Name = "RestockText"
    local note = Layout.text(body, "Rarer potions show up less often.", size(lay.note), pos(lay.note), Kit.Type.body, "value", Enum.TextXAlignment.Right)
    note.Name = "RarityNote"
    note:SetAttribute("TextKind", "note")
    ShopPage.wallet({art = ui.art, label = ui.label}, header, chip, spec.crystals, spec.closeSide or 48)

    local scroller = Instance.new("ScrollingFrame")
    scroller.Name, scroller.BackgroundTransparency, scroller.BorderSizePixel, scroller.ClipsDescendants = "PotionScroll", 1, 0, true
    scroller.Position, scroller.Size, scroller.ZIndex = pos(lay.view), size(lay.view), body.ZIndex + 1
    scroller.ScrollBarThickness, scroller.ScrollBarImageColor3 = P.scrollBar, Layout.tone("label")
    scroller.ScrollingDirection, scroller.CanvasSize = Enum.ScrollingDirection.Y, UDim2.fromOffset(0, if lay.scrolls then lay.canvasH else 0)
    scroller.Parent = body

    local offers = ProgressionRules.shopOffers(spec.window)
    for i, offer in offers do
        local rect = lay.cards[i]
        if rect == nil then break end
        local item = ProgressionRules.item(ProgressionConfig.Potions, offer.id)
        local left = ProgressionRules.shopRemaining(spec.p, spec.window, offer.id)
        local look = ShopCardState.look({left = left, buyButton = item.price .. " Crystals"}, item.price .. " Crystals")
        local tier = color[item.rarity] or Layout.tone("label")
        local card = Layout.card(scroller, "PotionCard_" .. item.id, size(rect), pos(rect))
        local parts = Kit.potionCard(rect.w, rect.h, lay)
        local tile = Layout.preview(card, size(parts.icon), pos(parts.icon))
        tile.Name = "IconTile"
        local ring = Instance.new("UIStroke") -- the rarity colour rings the picture, so the tier reads without a coloured word on cream
        ring.Name, ring.Color, ring.Thickness, ring.Parent = "RarityRing", tier, 3, tile
        picture(tile, item)
        Layout.text(card, item.name, size(parts.name), pos(parts.name), Kit.Type.heading, "value").Name = "Name"
        Layout.text(card, UIFormat.potion(item.kind, item.multiplier, item.duration), size(parts.desc), pos(parts.desc), Kit.Type.body, "value").Name = "Effect"
        Layout.text(card, if left > 0 then left .. " left" else look.caption, size(parts.stock), pos(parts.stock), Kit.Type.body, "label").Name = "Stock"
        local soldOut = left <= 0
        local colour = if soldOut then SOLD_OUT elseif spec.crystals < item.price then C.card else C.accent -- grey only for sold out / cannot afford
        local buy = ui.button(card, if soldOut then look.buttonText else UIFormat.number(item.price), parts.button.x, parts.button.y, parts.button.w, parts.button.h, colour, function()
            if left > 0 then spec.onBuy(item) end
        end)
        buy.Name = "Buy"
        buy.Active, buy.AutoButtonColor = not soldOut, not soldOut
        buy.TextSize = 20
        if soldOut then buy.TextTransparency = 0.25 else priceGroup(ui, buy, item.price, parts.button.h, parts.button.w) end
    end

    -- the owned potions: one cream panel, one row of use chips (scrolls sideways when there are many)
    local owned = Layout.panel(scroller, "OwnedPanel", size(lay.owned), pos(lay.owned))
    Layout.text(owned, "Your potions", size(lay.ownedTitle), pos(lay.ownedTitle), Kit.Type.heading, "value").Name = "OwnedTitle"
    local list = {}
    for _, item in ProgressionConfig.Potions do
        local count = spec.p.potions[item.id] or 0
        if count > 0 then table.insert(list, {item = item, count = count}) end
    end
    if #list == 0 then
        Layout.text(owned, "Buy a potion above to use it", size(lay.ownedRow), pos(lay.ownedRow), Kit.Type.body, "label").Name = "OwnedEmpty"
    else
        local row = Instance.new("ScrollingFrame")
        row.Name, row.BackgroundTransparency, row.BorderSizePixel, row.ClipsDescendants = "OwnedRow", 1, 0, true
        row.Position, row.Size, row.ZIndex = pos(lay.ownedRow), size(lay.ownedRow), owned.ZIndex + 1
        row.ScrollBarThickness, row.ScrollingDirection, row.AutomaticCanvasSize = 0, Enum.ScrollingDirection.X, Enum.AutomaticSize.None
        local x = 0
        for _, entry in list do
            local text = entry.item.name .. " x" .. entry.count
            local width = math.max(P.chipW, math.ceil(#text * 9.5) + 52)
            local use = Layout.tabChip(row, "Use_" .. entry.item.id, text, UDim2.fromOffset(width, lay.ownedRow.h), UDim2.fromOffset(x, 0), false, Kit.Type.body, function() spec.onUse(entry.item) end)
            local word = use:FindFirstChild("ChipWord") :: TextLabel
            word.Position, word.Size = UDim2.fromOffset(40, 0), UDim2.new(1, -48, 1, 0)
            local tile = Instance.new("Frame")
            tile.Name, tile.BackgroundTransparency, tile.Size, tile.Position, tile.ZIndex = "UseIcon", 1, UDim2.fromOffset(28, 28), UDim2.fromOffset(8, (lay.ownedRow.h - 28) / 2), use.ZIndex + 1
            tile.Parent = use
            picture(tile, entry.item)
            x += width + Kit.Gutter
        end
        row.CanvasSize = UDim2.fromOffset(math.max(x - Kit.Gutter, 0), 0)
        row.Parent = owned
    end
    return {restock = restock, layout = lay}
end

return Page
