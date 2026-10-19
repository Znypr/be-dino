--!strict
-- BD-142 / BD-143: the Aura and Trail shop cards. Layout and drawing only; every word and state comes from
-- Shared.ShopPreview (tested by tools/verify_shop_preview.py) and ShopCardState via ShopCard.
-- ui = Bootstrap's own helpers {label, box, button, art} so the cards match the rest of the Crystal Shops.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Chip = require(Shared.ChipStyle)
local RarityWord = require(Shared.RarityWord) -- BD-1120: the tier colour of a rarity chip comes from RarityWord / Theme.RarityColors (no second palette)
local Config = require(Shared.ProgressionConfig)
local MainConfig = require(Shared.Config)
local P = require(Shared.ShopPreview)
local UIFormat = require(Shared.UIFormat)
local Preview = require(Shared.DinosaurPreview)
local ShopCard = require(script.Parent.ShopCard)
local C = Theme.Colors

local Cards = {}
Cards.Width = 264

local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end

local function chip(ui, card: GuiObject, text: string, color: Color3, x: number, y: number, w: number)
    local c = ui.box(card, x, y, w, Chip.Spec.minHeight, color, card.ZIndex + 1)
    c.Name = "Chip_" .. text
    Chip.apply(c, color) -- BD-1077: the shared chunky tag (28 px high, 3 px outline, flat fill) like the hatch screen
    ui.label(c, text, 0, 0, w, Chip.Spec.minHeight, 18, Color3.new(1, 1, 1))
    return c
end

-- Dark rounded stage that clips the live preview (the halo and the trail never leak onto the text).
local function stage(ui, card: GuiObject, y: number, h: number, tint: Color3, dim: boolean)
    local s = ui.box(card, 8, y, Cards.Width - 16, h, Color3.fromRGB(18, 24, 40):Lerp(tint, .22), card.ZIndex + 1)
    s.Name, s.ClipsDescendants = "PreviewStage", true
    if dim then
        local veil = Instance.new("Frame")
        veil.Name, veil.BackgroundColor3, veil.BackgroundTransparency, veil.BorderSizePixel = "LockedVeil", Color3.fromRGB(20, 22, 30), .6, 0
        veil.Size, veil.ZIndex, veil.Parent = UDim2.fromScale(1, 1), s.ZIndex + 40, s
    end
    return s
end

local function equippedRing(card: GuiObject)
    local ring = Instance.new("UIStroke")
    ring.Name, ring.Color, ring.Thickness, ring.ApplyStrokeMode, ring.Parent = "EquippedRing", C.gold, 4, Enum.ApplyStrokeMode.Border, card
end

-- BD-1118 / BD-1144 (docs/202 R3, docs/213): the card with the price on the button, drawn when Config.ShopCardPriceButtonEnabled is true.
-- Row 1: the name in its tier colour (RarityWord) and the Info word button (44 px or more on screen); then the stage (more than half the card) with the
-- benefit as a dark band along its bottom; then ONE full-width button with the crystal icon and the price. No chips, no price caption. The equipped ring stays.
-- spec adds onInfo (opens the read-only details page). onPress is the same as the old card: a tap on the price only opens the confirm page.
function Cards.buildPrice(ui, parent: GuiObject, spec)
    local item, isTrail = spec.item, spec.kind == "trail"
    local base = if isTrail then P.trailCard(item, spec) else P.auraCard(item, UIFormat.boost("Growth", item.growth), spec)
    local data = P.priceCard(base, item, isTrail)
    local color = rgb(item.color)
    local card = ui.box(parent, spec.x, spec.y, Cards.Width, spec.height, ShopCard.cardColor(Color3.fromRGB(40, 46, 66):Lerp(color, .62), data.look), 24)
    card.Name = (if isTrail then "TrailCard_" else "AuraCard_") .. item.id
    local scale = math.max(spec.scale or 1, .1)
    local infoH = math.max(36, math.ceil(P.Touch / scale)) -- the Info button is a 44 px tap target on screen
    local infoW = math.max(72, math.ceil(#data.info * math.max(18, math.ceil(14 / scale)) * .55) + 24)
    local rowH = infoH + 8
    local _, tierColour = RarityWord.get(data.rarity)
    local name = ui.label(card, data.name, 8, 4, Cards.Width - 16 - infoW - 6, infoH, 25, tierColour)
    name.Name, name.TextXAlignment = "Name", Enum.TextXAlignment.Left
    local info = ui.button(card, data.info, Cards.Width - 8 - infoW, 4, infoW, infoH, C.blue, spec.onInfo)
    info.Name, info.TextSize = "Info", 20
    local previewY = rowH
    local previewH = spec.buyY - 6 - previewY
    local s = stage(ui, card, previewY, previewH, color, data.dim)
    local iconId = if isTrail then P.trailIconId(Config.TrailIconAssetIds, item.id) else nil
    if iconId then
        local img = Instance.new("ImageLabel")
        img.Name, img.BackgroundTransparency, img.Image, img.ScaleType = "TrailIcon", 1, iconId, Enum.ScaleType.Fit
        img.Size, img.AnchorPoint, img.Position, img.ZIndex, img.Parent = UDim2.fromScale(.9, .9), Vector2.new(.5, .5), UDim2.fromScale(.5, .5), s.ZIndex + 1, s
    elseif isTrail then
        local live = Theme.icon(s, "trail_" .. item.id)
        if live then live.Position, live.Size = UDim2.fromScale(0, 0), UDim2.fromScale(1, 1) end
        local who = Preview.add(s, spec.speciesId or "compy", "silhouette")
        who.Name, who.ZIndex = "DinoSilhouette", s.ZIndex + 6
        who.Size, who.Position = UDim2.fromScale(.34, 1), UDim2.fromScale(.64, 0)
    else
        local size = math.clamp(previewH - 36, 56, 120)
        ui.art(s, "aura_" .. item.id, (Cards.Width - 16 - size) / 2, (previewH - 30 - size) / 2, size)
    end
    -- the benefit ("Growth +15%", "Faster") as a dark band along the bottom of the stage, never over the button
    local bandH = math.max(28, math.ceil(14 / scale) + 10)
    local band = ui.box(s, 0, previewH - bandH, Cards.Width - 16, bandH, Color3.fromRGB(14, 18, 30), s.ZIndex + 30)
    band.Name, band.BackgroundTransparency = "BenefitBand", .18
    ui.label(band, data.benefit, 6, 0, Cards.Width - 28, bandH, 20, ShopCard.CalmText).Name = "Benefit"
    -- ONE wide button: the price on it while it can be bought
    local tone = data.button.tone
    local buttonColor = if tone == "buy" or tone == "equip" then C.accent elseif tone == "unequip" then C.card else ShopCard.SoldOutColor
    local act = ui.button(card, data.button.text, 8, spec.buyY, Cards.Width - 16, spec.targetHeight, buttonColor, spec.onPress)
    act.Name = "Action"
    act.Active, act.AutoButtonColor = data.button.active, data.button.active
    if not data.button.active then act.TextTransparency = .25 end
    if tone == "buy" then
        local iconSize = math.clamp(spec.targetHeight - 12, 24, 40)
        local icon = ui.art(act, "amber", 10, (spec.targetHeight - iconSize) / 2, iconSize) -- nil where the art is not bound (and in the mocks)
        if icon then
            icon.Name = "CrystalIcon"
            local pad = Instance.new("UIPadding")
            pad.Name, pad.PaddingLeft, pad.Parent = "IconPad", UDim.new(0, iconSize + 14), act -- the price never touches the icon
        end
    end
    if data.equipped then equippedRing(card) end
    return card, data
end

-- spec: {kind="trail"|"aura", item, owned, equipped, level, x, y, height, buyY, targetHeight, onPress, onInfo}
function Cards.build(ui, parent: GuiObject, spec)
    if MainConfig.ShopCardPriceButtonEnabled == true then return Cards.buildPrice(ui, parent, spec) end
    local item, isTrail = spec.item, spec.kind == "trail"
    local data = if isTrail then P.trailCard(item, spec) else P.auraCard(item, UIFormat.boost("Growth", item.growth), spec)
    local color = rgb(item.color)
    local card = ui.box(parent, spec.x, spec.y, Cards.Width, spec.height, ShopCard.cardColor(Color3.fromRGB(40, 46, 66):Lerp(color, .62), data.look), 24)
    card.Name = (if isTrail then "TrailCard_" else "AuraCard_") .. item.id
    ui.label(card, item.name, 6, 4, 252, 32, 25)
    -- BD-1103: a chip is as wide as its word at the size the window really draws it (14 px on screen is more design px when the body is shrunk to fit a narrow window)
    local textPx = math.max(18, math.ceil(14 / math.max(spec.scale or 1, .1)))
    local function wide(text: string, least: number): number return math.max(least, math.ceil(#text * textPx * .55) + 14) end
    local rarityW = wide(data.chip.text, 104)
    local _, tierColour = RarityWord.get(data.chip.text)
    chip(ui, card, data.chip.text, tierColour:Lerp(Color3.fromRGB(20, 24, 40), .3), 8, 38, rarityW)
    local secondX = if rarityW > 104 then 8 + rarityW + 6 else 118
    if isTrail then
        ui.label(card, data.levelText, secondX, 38, Cards.Width - 8 - secondX, 26, 19, if data.kind == "locked" then C.gold else ShopCard.CalmText)
    else
        local tierText = "Tier " .. string.sub(data.tier, 2)
        local tier = chip(ui, card, tierText, C.purple, secondX, 38, wide(tierText, 92))
        tier.Name = "TierBadge"
    end
    local previewY = 68
    local previewH = spec.buyY - 52 - previewY
    local s = stage(ui, card, previewY, previewH, color, isTrail and data.kind == "locked")
    local iconId = if isTrail then P.trailIconId(Config.TrailIconAssetIds, item.id) else nil
    if iconId then
        local img = Instance.new("ImageLabel")
        img.Name, img.BackgroundTransparency, img.Image, img.ScaleType = "TrailIcon", 1, iconId, Enum.ScaleType.Fit
        img.Size, img.AnchorPoint, img.Position, img.ZIndex, img.Parent = UDim2.fromScale(.9, .9), Vector2.new(.5, .5), UDim2.fromScale(.5, .5), s.ZIndex + 1, s
    elseif isTrail then
        local live = Theme.icon(s, "trail_" .. item.id)
        if live then live.Position, live.Size = UDim2.fromScale(0, 0), UDim2.fromScale(1, 1) end
        -- BD-143: the equipped dino as a dark silhouette at the head of the trail (existing DinosaurPreview, no new art).
        local who = Preview.add(s, spec.speciesId or "compy", "silhouette")
        who.Name, who.ZIndex = "DinoSilhouette", s.ZIndex + 6
        who.Size, who.Position = UDim2.fromScale(.34, 1), UDim2.fromScale(.64, 0)
    else
        local size = math.clamp(previewH - 6, 56, 120)
        ui.art(s, "aura_" .. item.id, (Cards.Width - 16 - size) / 2, (previewH - size) / 2, size)
    end
    ui.label(card, if isTrail then data.speedText else data.growthText, 6, spec.buyY - 50, 252, 24, 20, ShopCard.CalmText)
    ui.label(card, data.caption, 4, spec.buyY - 26, 256, 24, 21, if data.tone == "equipped" then C.accent else ShopCard.captionColor(data.look))
    local act = ui.button(card, data.buttonText, 12, spec.buyY, 240, spec.targetHeight, if data.equipped then C.accent else C.card, spec.onPress)
    act.Name = "Action"
    if data.equipped then equippedRing(card) end
    return card, data
end

-- BD-393: header strip above the Aura and Trail cards: the equipped dino's dark silhouette (existing DinosaurPreview, no new art),
-- "For: <dino>" and the one-line note. ui = {label, box}; y = top of the strip in the shop body (824 wide).
function Cards.forHeader(ui, parent: GuiObject, y: number, speciesId: string, height: number?)
    local Copy = require(Shared.ShopForDino)
    local H = height or Copy.HeaderHeight -- BD-1101: a small window asks for a taller strip so the 14 px note fits (two lines)
    local strip = ui.box(parent, 0, y, 824, H - 4, Color3.fromRGB(40, 46, 66):Lerp(C.blue, .25), 24)
    strip.Name = "ForDinoHeader"
    local well = ui.box(strip, 4, 2, 44, H - 8, Color3.fromRGB(190, 205, 230), strip.ZIndex + 1)
    well.Name, well.ClipsDescendants = "DinoIcon", true
    local view = Preview.add(well, speciesId, "silhouette") -- the silhouette is black: a light well so it reads
    view.Name, view.ZIndex, view.Size = "DinoSilhouette", well.ZIndex + 1, UDim2.fromScale(1, 1)
    local title = ui.label(strip, Copy.title(MainConfig.SpeciesDisplayNames[speciesId] or require(Shared.SecretSpeciesConfig).name(speciesId)), 54, 2, 262, H - 8, 26, C.gold)
    title.Name, title.TextXAlignment = "ForDinoName", Enum.TextXAlignment.Left
    local note = ui.label(strip, Copy.Note, 320, 2, 496, H - 8, 19, ShopCard.CalmText)
    note.Name, note.TextXAlignment = "ForDinoNote", Enum.TextXAlignment.Right
    return strip
end

return Cards
