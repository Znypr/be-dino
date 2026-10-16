--!strict
-- BD-142 / BD-143: the Aura and Trail shop cards. Layout and drawing only; every word and state comes from
-- Shared.ShopPreview (tested by tools/verify_shop_preview.py) and ShopCardState via ShopCard.
-- ui = Bootstrap's own helpers {label, box, button, art} so the cards match the rest of the Crystal Shops.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
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
    local c = ui.box(card, x, y, w, 26, color, card.ZIndex + 1)
    c.Name = "Chip_" .. text
    ui.label(c, text, 0, 0, w, 26, 18, Color3.new(1, 1, 1))
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

-- spec: {kind="trail"|"aura", item, owned, equipped, level, x, y, height, buyY, targetHeight, onPress}
function Cards.build(ui, parent: GuiObject, spec)
    local item, isTrail = spec.item, spec.kind == "trail"
    local data = if isTrail then P.trailCard(item, spec) else P.auraCard(item, UIFormat.boost("Growth", item.growth), spec)
    local color = rgb(item.color)
    local card = ui.box(parent, spec.x, spec.y, Cards.Width, spec.height, ShopCard.cardColor(Color3.fromRGB(40, 46, 66):Lerp(color, .62), data.look), 24)
    card.Name = (if isTrail then "TrailCard_" else "AuraCard_") .. item.id
    ui.label(card, item.name, 6, 4, 252, 32, 25)
    chip(ui, card, data.chip.text, rgb(data.chip.color):Lerp(Color3.fromRGB(20, 24, 40), .3), 8, 38, 104)
    if isTrail then
        ui.label(card, data.levelText, 118, 38, 138, 26, 19, if data.kind == "locked" then C.gold else ShopCard.CalmText)
    else
        local tier = chip(ui, card, "Tier " .. string.sub(data.tier, 2), C.purple, 118, 38, 92)
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
function Cards.forHeader(ui, parent: GuiObject, y: number, speciesId: string)
    local Copy = require(Shared.ShopForDino)
    local strip = ui.box(parent, 0, y, 824, Copy.HeaderHeight - 4, Color3.fromRGB(40, 46, 66):Lerp(C.blue, .25), 24)
    strip.Name = "ForDinoHeader"
    local well = ui.box(strip, 4, 2, 44, Copy.HeaderHeight - 8, Color3.fromRGB(190, 205, 230), strip.ZIndex + 1)
    well.Name, well.ClipsDescendants = "DinoIcon", true
    local view = Preview.add(well, speciesId, "silhouette") -- the silhouette is black: a light well so it reads
    view.Name, view.ZIndex, view.Size = "DinoSilhouette", well.ZIndex + 1, UDim2.fromScale(1, 1)
    local title = ui.label(strip, Copy.title(MainConfig.SpeciesDisplayNames[speciesId]), 54, 2, 270, Copy.HeaderHeight - 8, 26, C.gold)
    title.Name, title.TextXAlignment = "ForDinoName", Enum.TextXAlignment.Left
    local note = ui.label(strip, Copy.Note, 320, 2, 496, Copy.HeaderHeight - 8, 19, ShopCard.CalmText)
    note.Name, note.TextXAlignment = "ForDinoNote", Enum.TextXAlignment.Right
    return strip
end

return Cards
