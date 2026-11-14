--!strict
-- BD-1178 (owner target 2026-11-14, docs/228 board 3, docs/231): the Aura and Trail shop card in the "Toybox" look. ShopCards.build hands over to this file only
-- while Config.ToyboxUIEnabled is true AND the six toybox_card_* pictures are bound (Theme.Toybox exists and ToyboxKit.ready(.., "card")); with the flag
-- off, or while an id is missing, the old card is built exactly as before. Client presentation only: the words and states come from
-- Shared.ShopPreview.priceCard (the price-on-button data of BD-1118 / BD-1144), the rules from Shared.ToyboxShop; nothing here sends, saves or prices.
-- Parts: the tier card picture (9-slice), the outlined white name, the rarity word on a cream pill, a cream art box with slow rays behind the item art
-- (a tap on it opens the read-only details page), a cream benefit band with dark text, ONE wide button (the crystal icon and the number are one group,
-- BD-1192), and a gold ring + glow on the equipped card. The width is the cell the page grid gives (spec.width). No picture is drawn in code (docs/72):
-- the rays are the existing shaftGradient texture, the glow the existing glowPlate; a texture that is not uploaded is simply left out.
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
local PriceGroup = require(Shared.PriceGroup)
local Effects = require(Shared.EffectAssets)
local Preview = require(Shared.DinosaurPreview)
local ShopCard = require(script.Parent.ShopCard)
local C = Theme.Colors

local Card = {}
Card.Width = 264
local OUTLINE = Color3.fromRGB(Kit.Outline[1], Kit.Outline[2], Kit.Outline[3])

local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
local function tone(name: string): Color3
    local t = (Kit.Tone :: any)[name]
    return Color3.fromRGB(t[1], t[2], t[3])
end

local function round(object: GuiObject, radius: number)
    local corner = Instance.new("UICorner")
    corner.CornerRadius, corner.Parent = UDim.new(0, radius), object
end
local function outline(object: GuiObject, thickness: number)
    local line = Instance.new("UIStroke")
    line.Name, line.Color, line.Thickness, line.Parent = "CreamOutline", OUTLINE, thickness, object
end
-- Dark body text on a cream surface (no outline): the same rule as ToyboxLayout.ink.
local function ink(label: TextLabel, which: string?): TextLabel
    label.TextColor3, label.TextStrokeTransparency = tone(which or "value"), 1
    for _, child in label:GetChildren() do
        if child:IsA("UIStroke") then child.Transparency = 1 end
    end
    return label
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
local function rays(art: GuiObject, side: number)
    if not Effects.isRealUi(Rules.RaysKey) then return end
    local fan = Instance.new("Frame")
    fan.Name, fan.BackgroundTransparency, fan.AnchorPoint, fan.Position = "Rays", 1, Vector2.new(0.5, 0.5), UDim2.fromScale(0.5, 0.5)
    fan.Size, fan.ZIndex, fan.Parent = UDim2.fromOffset(side * 1.6, side * 1.6), art.ZIndex + 1, art
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

-- spec: the same table ShopCards.build gets, plus width (the grid cell). ui = {label, box, button, art}.
function Card.build(ui, parent: GuiObject, spec)
    local item, isTrail = spec.item, spec.kind == "trail"
    local base = if isTrail then P.trailCard(item, spec) else P.auraCard(item, UIFormat.boost("Growth", item.growth), spec)
    local data = P.priceCard(base, item, isTrail)
    local color = rgb(item.color)
    local W = spec.width or Card.Width
    local card = ui.box(parent, spec.x, spec.y, W, spec.height, ShopCard.cardColor(Color3.fromRGB(40, 46, 66):Lerp(color, .62), data.look), 24)
    card.Name = (if isTrail then "TrailCard_" else "AuraCard_") .. item.id
    card.BackgroundTransparency = 1 -- the picture is the card
    for _, child in card:GetChildren() do
        if child:IsA("UIStroke") then child.Enabled = false end
    end
    picture(card, Rules.cardSlot(data.rarity))
    local scale = math.max(spec.scale or 1, .1)
    local plan = Rules.layout(W, spec.height, spec.targetHeight, scale)
    local textPx = plan.parts.textPx
    local buttonTone = data.button.tone
    local mystery = Rules.mystery(data.rarity, buttonTone)

    -- name: outlined white (a secret card hides it)
    local name = ui.label(card, if mystery then Rules.MysteryName else data.name, plan.name.x, plan.name.y, plan.name.w, plan.name.h, 24, Color3.new(1, 1, 1))
    name.Name, name.TextXAlignment = "Name", Enum.TextXAlignment.Left
    -- the rarity word in its tier colour, on a small cream pill with a dark outline
    local word, tierColour = RarityWord.get(data.rarity)
    local pillW = math.min(math.max(88, math.ceil(#word * textPx * .6) + 24), plan.name.w)
    local pill = ui.label(card, word, plan.pill.x, plan.pill.y, pillW, plan.pill.h, textPx, tierColour)
    pill.Name, pill.BackgroundTransparency, pill.BackgroundColor3 = "RarityWord", 0, tone("panel")
    round(pill, 999)
    outline(pill, 2)

    -- the cream art box; a tap on it opens the read-only details page
    local art = ui.box(card, plan.art.x, plan.art.y, plan.art.w, plan.art.h, tone("previewTop"), card.ZIndex + 1)
    art.Name, art.ClipsDescendants = "ArtBox", true
    for _, child in art:GetChildren() do
        if child:IsA("UIStroke") then child.Enabled = false end
    end
    round(art, Kit.CardCorner)
    outline(art, Kit.CardStroke)
    local wash = Instance.new("UIGradient")
    wash.Rotation, wash.Color = 90, ColorSequence.new(tone("previewTop"), tone("previewBottom"))
    wash.Parent = art
    rays(art, math.max(plan.art.w, plan.art.h))
    local innerH = plan.art.h
    if mystery then
        local mark = ui.label(art, Rules.MysteryMark, 0, 0, plan.art.w, innerH, 64, tone("label"))
        mark.Name = "Mystery"
        mark.ZIndex = art.ZIndex + 3
        ink(mark, "label")
    else
        local iconId = if isTrail then P.trailIconId(Config.TrailIconAssetIds, item.id) else nil
        if iconId then
            local img = Instance.new("ImageLabel")
            img.Name, img.BackgroundTransparency, img.Image, img.ScaleType = "TrailIcon", 1, iconId, Enum.ScaleType.Fit
            img.Size, img.AnchorPoint, img.Position, img.ZIndex, img.Parent = UDim2.fromScale(.9, .85), Vector2.new(.5, .5), UDim2.fromScale(.5, .5), art.ZIndex + 3, art
        elseif isTrail then
            local live = Theme.icon(art, "trail_" .. item.id)
            if live then live.Position, live.Size, live.ZIndex = UDim2.fromScale(0, 0), UDim2.fromScale(1, 1), art.ZIndex + 3 end
            local who = Preview.add(art, spec.speciesId or "compy", "silhouette")
            who.Name, who.ZIndex = "DinoSilhouette", art.ZIndex + 6
            who.Size, who.Position = UDim2.fromScale(.34, 1), UDim2.fromScale(.64, 0)
        else
            local size = math.clamp(math.min(innerH - 8, plan.art.w - 8), 48, 140)
            local ring = (Slots.Images :: any)["aura_" .. item.id] -- the bound aura picture (the v2 ring alone), never the assembled layers
            if type(ring) == "string" and ring ~= "" then
                local img = Instance.new("ImageLabel")
                img.Name, img.BackgroundTransparency, img.Image, img.ScaleType = "AuraRing", 1, ring, Enum.ScaleType.Fit
                img.AnchorPoint, img.Position, img.Size, img.ZIndex = Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromOffset(size, size), art.ZIndex + 3
                img.Parent = art
            else
                local icon = ui.art(art, "aura_" .. item.id, (plan.art.w - size) / 2, (innerH - size) / 2, size)
                if icon then icon.ZIndex = art.ZIndex + 3 end
            end
        end
    end
    local tap = Instance.new("TextButton")
    tap.Name, tap.Text, tap.BackgroundTransparency, tap.AutoButtonColor, tap.TextSize = "InfoTap", "", 1, false, 14
    tap.Size, tap.ZIndex, tap.Parent = UDim2.fromScale(1, 1), art.ZIndex + 8, art
    tap.Activated:Connect(function() spec.onInfo() end)

    -- the benefit band: cream, dark text ("Growth +15%"); a locked Legendary shows its hint there instead
    local band = ui.box(card, plan.band.x, plan.band.y, plan.band.w, plan.band.h, tone("panel"), card.ZIndex + 1)
    band.Name = "BenefitBand"
    for _, child in band:GetChildren() do
        if child:IsA("UIStroke") then child.Enabled = false end
    end
    round(band, Kit.CardCorner)
    outline(band, Kit.CardStroke)
    local words = if mystery then Rules.hint(item) else data.benefit
    local line = ui.label(band, words, 4, 0, plan.band.w - 8, plan.band.h, 20, tone("value"))
    line.Name = if mystery then "Hint" else "Benefit"
    ink(line)

    -- ONE wide button
    local colours = {accent = C.accent, card = C.card, soldOut = ShopCard.SoldOutColor}
    local act = ui.button(card, if mystery then Rules.LockedWord else data.button.text, plan.button.x, plan.button.y, plan.button.w, plan.button.h, colours[Rules.buttonColour(buttonTone)], spec.onPress)
    act.Name = "Action"
    act.Active, act.AutoButtonColor = data.button.active, data.button.active
    if not data.button.active then act.TextTransparency = .25 end
    if buttonTone == "buy" then
        -- BD-1192: the crystal icon and the number are ONE group measured from the text and centred on the button; the padding moves every child
        -- (the icon and the skin's word label) by the same amount, so the number never touches the icon.
        local iconSize = math.clamp(plan.button.h - 12, 24, 40)
        act.Text = UIFormat.number(item.price)
        act.TextXAlignment = Enum.TextXAlignment.Left
        local function measure(size: number): number
            local ok, bounds = pcall(function() return game:GetService("TextService"):GetTextSize(act.Text, size, act.Font, Vector2.new(10000, 200)).X end)
            return if ok and typeof(bounds) == "number" then bounds else #act.Text * size * .6
        end
        local group = PriceGroup.layout(measure, math.max(act.TextSize, 14), 14, plan.button.w, iconSize, 8, 8)
        act.TextSize = group.size
        local place = PriceGroup.placement(group)
        local icon = ui.art(act, "amber", place.iconPos, (plan.button.h - iconSize) / 2, iconSize)
        if icon then icon.Name = "CrystalIcon" end
        local pad = Instance.new("UIPadding")
        pad.Name, pad.PaddingLeft, pad.Parent = "IconPad", UDim.new(0, place.padLeft), act
        act:SetAttribute("PriceGroupW", group.groupW)
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
