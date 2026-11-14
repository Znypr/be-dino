--!strict
-- BD-1178 (docs/228 board 3, docs/231): the Aura and Trail shop card in the "Toybox" look. ShopCards.build hands over to this file only while
-- Config.ToyboxUIEnabled is true AND the six toybox_card_* pictures are bound (Theme.Toybox exists and ToyboxKit.ready(.., "card")); with the flag
-- off, or while an id is missing, the old card is built exactly as before. Client presentation only: the words and states come from
-- Shared.ShopPreview.priceCard (the price-on-button data of BD-1118 / BD-1144), the rules from Shared.ToyboxShop; nothing here sends, saves or prices.
-- Parts: the tier card picture (9-slice), the name and Info word, the rarity word on a cream pill, a cream art box with slow rays behind the item
-- art, the benefit band, ONE wide button, and a gold glow ring on the equipped card. No picture is drawn in code (docs/72): the rays are the
-- existing shaftGradient texture, the glow the existing glowPlate; a texture that is not uploaded is simply left out.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Rules = require(Shared.ToyboxShop)
local RarityWord = require(Shared.RarityWord)
local Config = require(Shared.ProgressionConfig)
local P = require(Shared.ShopPreview)
local UIFormat = require(Shared.UIFormat)
local Effects = require(Shared.EffectAssets)
local Preview = require(Shared.DinosaurPreview)
local ShopCard = require(script.Parent.ShopCard)
local C = Theme.Colors

local Card = {}
Card.Width = 264
local CREAM = Color3.fromRGB(246, 236, 208)

local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end

local function round(object: GuiObject, radius: number)
    local corner = Instance.new("UICorner")
    corner.CornerRadius, corner.Parent = UDim.new(0, radius), object
end

-- The tier picture, sliced like the skin slices every picture (the rect comes from the kit).
local function picture(card: GuiObject, slot: string): ImageLabel
    local image = Instance.new("ImageLabel")
    image.Name, image.BackgroundTransparency, image.BorderSizePixel = "ToyboxCard", 1, 0
    image.Image, image.ScaleType, image.Size, image.ZIndex = Kit.image(Slots.Images, slot) or "", Enum.ScaleType.Slice, UDim2.fromScale(1, 1), card.ZIndex
    local rect = (Kit.Assets[slot].slice :: {number})
    image.SliceCenter = Rect.new(rect[1], rect[2], rect[3], rect[4])
    image.SliceScale = Kit.sliceScale(slot, card.Size.X.Offset, card.Size.Y.Offset)
    image:SetAttribute("ToyboxSlot", slot)
    image.Parent = card
    return image
end

-- Slow rays: three copies of the shaft texture fanned out around the middle of the art box, the whole fan turning once in 40 s.
local function rays(art: GuiObject)
    if not Effects.isRealUi(Rules.RaysKey) then return end
    local fan = Instance.new("Frame")
    fan.Name, fan.BackgroundTransparency, fan.AnchorPoint, fan.Position = "Rays", 1, Vector2.new(0.5, 0.5), UDim2.fromScale(0.5, 0.5)
    fan.Size, fan.ZIndex, fan.Parent = UDim2.fromOffset(art.Size.X.Offset * 1.6, art.Size.X.Offset * 1.6), art.ZIndex + 1, art
    for i, angle in Rules.RayAngles do
        local ray = Instance.new("ImageLabel")
        ray.Name, ray.BackgroundTransparency, ray.BorderSizePixel = "Ray" .. i, 1, 0
        ray.Image, ray.ImageTransparency, ray.ScaleType = Effects.resolveUi(Rules.RaysKey), Rules.RayTransparency, Enum.ScaleType.Fit
        ray.AnchorPoint, ray.Position, ray.Size = Vector2.new(0.5, 1), UDim2.fromScale(0.5, 0.5), UDim2.fromScale(0.45, 0.5)
        ray.Rotation, ray.ZIndex, ray.Parent = angle, fan.ZIndex, fan
    end
    local seconds = Rules.raySeconds(not Theme.MotionEnabled)
    if seconds > 0 then
        TweenService:Create(fan, TweenInfo.new(seconds, Enum.EasingStyle.Linear, Enum.EasingDirection.In, -1), {Rotation = 360}):Play()
    end
end

-- spec: the same table ShopCards.build gets. ui = {label, box, button, art}.
function Card.build(ui, parent: GuiObject, spec)
    local item, isTrail = spec.item, spec.kind == "trail"
    local base = if isTrail then P.trailCard(item, spec) else P.auraCard(item, UIFormat.boost("Growth", item.growth), spec)
    local data = P.priceCard(base, item, isTrail)
    local color = rgb(item.color)
    local card = ui.box(parent, spec.x, spec.y, Card.Width, spec.height, ShopCard.cardColor(Color3.fromRGB(40, 46, 66):Lerp(color, .62), data.look), 24)
    card.Name = (if isTrail then "TrailCard_" else "AuraCard_") .. item.id
    card.BackgroundTransparency = 1 -- the picture is the card
    for _, child in card:GetChildren() do
        if child:IsA("UIStroke") then child.Enabled = false end
    end
    picture(card, Rules.cardSlot(data.rarity))
    local scale = math.max(spec.scale or 1, .1)
    local textPx = math.max(18, math.ceil(14 / scale))
    local infoH = math.max(36, math.ceil(P.Touch / scale))
    local infoW = math.max(72, math.ceil(#data.info * textPx * .55) + 24)
    local rowH = infoH + 4
    local pillH = textPx + 10
    local bandH = math.max(28, math.ceil(14 / scale) + 10)
    local plan = Rules.layout(spec.buyY, rowH, pillH, bandH)

    -- name row: the name (white on the tier colour) and the Info word
    local name = ui.label(card, data.name, 10, 4, Card.Width - 20 - infoW - 6, infoH, 25, Color3.new(1, 1, 1))
    name.Name, name.TextXAlignment = "Name", Enum.TextXAlignment.Left
    local info = ui.button(card, data.info, Card.Width - 10 - infoW, 4, infoW, infoH, C.blue, spec.onInfo)
    info.Name, info.TextSize = "Info", 20
    -- the rarity word in its tier colour, on a small cream pill (a colour on the same colour would not read)
    local word, tierColour = RarityWord.get(data.rarity)
    local pillW = math.max(88, math.ceil(#word * textPx * .6) + 20)
    local pill = ui.label(card, word, 10, plan.pillY, pillW, pillH, textPx, tierColour)
    pill.Name, pill.BackgroundTransparency, pill.BackgroundColor3 = "RarityWord", 0, CREAM
    round(pill, 8)

    -- the cream art box
    local tone = data.button.tone
    local mystery = Rules.mystery(data.rarity, tone)
    local art = ui.box(card, 10, plan.artY, Card.Width - 20, plan.artH, CREAM, card.ZIndex + 1)
    art.Name, art.ClipsDescendants = "ArtBox", true
    for _, child in art:GetChildren() do
        if child:IsA("UIStroke") then child.Enabled = false end
    end
    rays(art)
    if mystery then
        local mark = ui.label(art, Rules.MysteryMark, 0, 0, Card.Width - 20, math.max(plan.artH - bandH, 40), 64, C.panel)
        mark.Name = "Mystery"
        mark.ZIndex = art.ZIndex + 3
    else
        local iconId = if isTrail then P.trailIconId(Config.TrailIconAssetIds, item.id) else nil
        if iconId then
            local img = Instance.new("ImageLabel")
            img.Name, img.BackgroundTransparency, img.Image, img.ScaleType = "TrailIcon", 1, iconId, Enum.ScaleType.Fit
            img.Size, img.AnchorPoint, img.Position, img.ZIndex, img.Parent = UDim2.fromScale(.9, .8), Vector2.new(.5, .5), UDim2.fromScale(.5, .45), art.ZIndex + 3, art
        elseif isTrail then
            local live = Theme.icon(art, "trail_" .. item.id)
            if live then live.Position, live.Size, live.ZIndex = UDim2.fromScale(0, 0), UDim2.fromScale(1, 1), art.ZIndex + 3 end
            local who = Preview.add(art, spec.speciesId or "compy", "silhouette")
            who.Name, who.ZIndex = "DinoSilhouette", art.ZIndex + 6
            who.Size, who.Position = UDim2.fromScale(.34, 1), UDim2.fromScale(.64, 0)
        else
            local size = math.clamp(plan.artH - bandH - 6, 48, 120)
            local icon = ui.art(art, "aura_" .. item.id, (Card.Width - 20 - size) / 2, (plan.artH - bandH - size) / 2, size)
            if icon then icon.ZIndex = art.ZIndex + 3 end
        end
    end
    -- the benefit band along the bottom of the art box ("Growth +15%"); a locked Legendary shows its hint there instead
    local band = ui.box(art, 0, plan.bandY, Card.Width - 20, bandH, Color3.fromRGB(14, 18, 30), art.ZIndex + 30)
    band.Name, band.BackgroundTransparency = "BenefitBand", .18
    local words = if mystery then Rules.hint(item) else data.benefit
    ui.label(band, words, 6, 0, Card.Width - 32, bandH, 20, ShopCard.CalmText).Name = if mystery then "Hint" else "Benefit"

    -- ONE wide button
    local colours = {accent = C.accent, card = C.card, soldOut = ShopCard.SoldOutColor}
    local act = ui.button(card, data.button.text, 10, spec.buyY, Card.Width - 20, spec.targetHeight, colours[Rules.buttonColour(tone)], spec.onPress)
    act.Name = "Action"
    act.Active, act.AutoButtonColor = data.button.active, data.button.active
    if not data.button.active then act.TextTransparency = .25 end
    if tone == "buy" then
        local iconSize = math.clamp(spec.targetHeight - 12, 24, 40)
        local icon = ui.art(act, "amber", 10, (spec.targetHeight - iconSize) / 2, iconSize)
        if icon then
            icon.Name = "CrystalIcon"
            local pad = Instance.new("UIPadding")
            pad.Name, pad.PaddingLeft, pad.Parent = "IconPad", UDim.new(0, iconSize + 14), act
        end
    end

    -- the equipped card: the gold ring and, where glowPlate is uploaded, a soft gold glow behind the card
    if data.equipped then
        local ring = Instance.new("UIStroke")
        ring.Name, ring.Color, ring.Thickness, ring.ApplyStrokeMode, ring.Parent = "EquippedRing", C.gold, 4, Enum.ApplyStrokeMode.Border, card
        if Effects.isRealUi(Rules.GlowKey) then
            local glow = Instance.new("ImageLabel")
            glow.Name, glow.BackgroundTransparency, glow.Image, glow.ImageColor3 = "EquippedGlow", 1, Effects.resolveUi(Rules.GlowKey), C.gold
            glow.ImageTransparency, glow.AnchorPoint, glow.Position = 0.35, Vector2.new(.5, .5), UDim2.fromScale(.5, .5)
            glow.Size, glow.ZIndex, glow.Parent = UDim2.new(1, 36, 1, 36), card.ZIndex - 1, card
        end
    end
    return card, data
end

return Card
