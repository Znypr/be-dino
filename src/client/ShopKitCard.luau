--!strict
-- BD-1287 (docs/246, owner 2026-11-21: "both shops don't have the same design language"): ONE shop card, copied from the owner's APPROVED
-- Aura Shop card on the Design Board, for every shop page that uses the kit window (the Featured landing now; Aura, Trail, Potion and Egg
-- pages later), built from the kit pictures 1:1 (owner 2026-11-21): the item's kit rarity card (studded, one rarity colour top to bottom),
-- the name in big white outlined words with the small rarity word under it, a BIG centred picture (up to 55 % of the card), a dark kit
-- strip with one short line ("x1.15 Growth" for an aura, the number green, as approved; a kid line for the others) and the studded kit
-- price button (the orange crystal + the whole price; the grey kit button with a word for a lock). Sizes: Shared/SaeFrameRules.layout;
-- slices: Shared/ToyboxKit. Code only places, slices and tiles uploaded pictures; it draws none (docs/72).
-- Also the small kit helpers the shop window uses (pictures, outlined words, tap areas), so every page builds from the same parts.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Rules = require(Shared.SaeFrameRules)

local Card = {}

local INK = Color3.fromRGB(Rules.Ink[1], Rules.Ink[2], Rules.Ink[3])

function Card.box(parent: Instance, name: string, x: number, y: number, w: number, h: number, z: number): Frame
    local f = Instance.new("Frame")
    f.Name, f.BackgroundTransparency, f.BorderSizePixel = name, 1, 0
    f.Position, f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    return f
end

-- An uploaded kit picture, whole (Fit) or 9-sliced to its box by the kit's slice rect and scale. nil while the slot is not bound.
function Card.kit(parent: Instance, name: string, slot: string, x: number, y: number, w: number, h: number, z: number): ImageLabel?
    local id = Kit.image(Slots.Images, slot)
    if not id then return nil end
    local img = Instance.new("ImageLabel")
    img.Name, img.BackgroundTransparency, img.BorderSizePixel, img.Image = name, 1, 0, id
    img.Position, img.Size, img.ZIndex = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z
    local asset = Kit.Assets[slot]
    if asset and asset.slice then
        local s = asset.slice
        img.ScaleType, img.SliceCenter, img.SliceScale = Enum.ScaleType.Slice, Rect.new(s[1], s[2], s[3], s[4]), Kit.sliceScale(slot, w, h)
    else
        img.ScaleType = Enum.ScaleType.Fit
    end
    img.Parent = parent
    return img
end

function Card.picture(parent: Instance, name: string, id: string, x: number, y: number, size: number, z: number): ImageLabel
    local img = Instance.new("ImageLabel")
    img.Name, img.BackgroundTransparency, img.Image, img.ScaleType = name, 1, id, Enum.ScaleType.Fit
    img.Position, img.Size, img.ZIndex, img.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(size, size), z, parent
    return img
end

-- Kit words: heavy FredokaOne, the kit outline and a dark copy under it (the kit title drop). rich = RichText (a coloured part), plain = the
-- same words without tags for the drop.
function Card.words(parent: Instance, name: string, text: string, x: number, y: number, w: number, h: number, size: number, z: number, color: Color3?, plain: string?): TextLabel
    local function one(n: string, dy: number, c: Color3, zz: number, t: string, rich: boolean): TextLabel
        local label = Instance.new("TextLabel")
        label.Name, label.Text, label.RichText, label.BackgroundTransparency, label.Font, label.TextSize = n, t, rich, 1, Enum.Font.FredokaOne, size
        label.TextColor3, label.TextWrapped = c, false
        label.Position, label.Size, label.ZIndex, label.Parent = UDim2.fromOffset(x, y + dy), UDim2.fromOffset(w, h), zz, parent
        local s = Instance.new("UIStroke")
        s.Color, s.Thickness, s.LineJoinMode, s.ApplyStrokeMode, s.Parent = INK, Kit.stroke(size), Enum.LineJoinMode.Round, Enum.ApplyStrokeMode.Contextual, label
        return label
    end
    local drop = one(name .. "Drop", Kit.DropPixels, INK, z, plain or text, false)
    local main = one(name, 0, color or Color3.new(1, 1, 1), z + 1, text, plain ~= nil)
    main:GetPropertyChangedSignal("TextXAlignment"):Connect(function() drop.TextXAlignment = main.TextXAlignment end)
    return main
end

-- A kit card: the rarity card picture 9-sliced to the box, its pale top band covered by its own studded body (a tiled crop of one stud
-- period of the same picture), so the card is one rarity colour top to bottom with studs, like the approved cards.
function Card.face(parent: Instance, name: string, slot: string, x: number, y: number, w: number, h: number, z: number): Frame
    local holder = Card.box(parent, name, x, y, w, h, z)
    local face = Card.kit(holder, "Face", slot, 0, 0, w, h, z)
    local id = Kit.image(Slots.Images, slot)
    if face and id then
        local k = face.SliceScale
        local inset, crop = Rules.CardInset, Rules.CardStudCrop
        local fill = Instance.new("ImageLabel")
        fill.Name, fill.BackgroundTransparency, fill.BorderSizePixel, fill.Image = "Studs", 1, 0, id
        fill.ImageRectOffset, fill.ImageRectSize = Vector2.new(crop.x, crop.y), Vector2.new(crop.w, crop.h)
        fill.ScaleType, fill.TileSize = Enum.ScaleType.Tile, UDim2.fromOffset(math.max(8, math.floor(crop.w * k)), math.max(8, math.floor(crop.h * k)))
        local sx, ty, by = math.ceil(inset.side * k), math.ceil(inset.top * k), math.ceil(inset.bottom * k)
        fill.Position, fill.Size, fill.ZIndex = UDim2.fromOffset(sx, ty), UDim2.fromOffset(w - 2 * sx, h - ty - by), z
        local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, math.floor(16 * k)), fill
        fill.Parent = holder
    end
    return holder
end

function Card.tap(parent: Instance, name: string, x: number, y: number, w: number, h: number, z: number, fn: () -> ()): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.BackgroundTransparency, b.AutoButtonColor = name, "", 1, false
    b.Position, b.Size, b.ZIndex, b.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    b.Activated:Connect(fn)
    return b
end

export type Spec = {
    key: string, slot: string, name: string, rarity: string?, picture: string?,
    line: string, lineRich: string?, -- the strip words (lineRich: the same with a coloured part, e.g. the green "x1.15")
    price: number?, word: string?, grey: boolean?, -- a price = the green buy button; else `word` on the grey (grey = true) or green button
    gem: string?, onPick: () -> (),
}

-- One card in `parent` at rect r. lay = SaeFrameRules.layout(...) (its card sizes). Tapping anywhere on it calls spec.onPick.
function Card.draw(parent: Instance, r: Rules.Rect, spec: Spec, lay: Rules.Layout): Frame
    local card = Card.face(parent, "ShopKitCard_" .. spec.key, spec.slot, r.x, r.y, r.w, r.h, 34)
    Card.tap(card, "Tap", 0, 0, r.w, r.h, 35, spec.onPick)
    local edge = lay.edge
    Card.words(card, "Name", spec.name, 4, edge, r.w - 8, lay.nameH, Rules.fitSize(spec.name, r.w - 12, lay.cardTitle), 38)
    if spec.rarity then Card.words(card, "Rarity", spec.rarity, 4, edge + lay.nameH - 2, r.w - 8, lay.rarityH, lay.rarityText, 38) end
    local buttonY = r.h - edge - lay.button
    local stripY = buttonY - 5 - lay.lineH
    local artTop = edge + lay.nameH + lay.rarityH
    local artBottom = if lay.line then stripY - 2 else buttonY - 2
    local art = math.min(lay.art, artBottom - artTop, r.w - 2 * edge)
    if spec.picture and art > 0 then
        Card.picture(card, "Picture", spec.picture, math.floor((r.w - art) / 2), artTop + math.floor((artBottom - artTop - art) / 2), art, 36)
    end
    -- the dark kit strip with one short line
    if lay.line then
        Card.kit(card, "Strip", "toybox_button_dark", edge + 4, stripY, r.w - 2 * edge - 8, lay.lineH, 37)
        local size = Rules.fitSize(spec.line, r.w - 2 * edge - 16, lay.lineText)
        Card.words(card, "Line", spec.lineRich or spec.line, edge + 4, stripY - 1, r.w - 2 * edge - 8, lay.lineH, size, 38, nil, if spec.lineRich then spec.line else nil)
    end
    -- the studded kit button: green with the crystal icon and the price, or a word (grey for a lock)
    local bx, bw = edge, r.w - 2 * edge
    Card.kit(card, "Button", if spec.grey then "toybox_button_grey" else "toybox_button_green", bx, buttonY, bw, lay.button, 37)
    if spec.price then
        local price = Rules.grouped(spec.price)
        local size = Rules.fitSize(price, bw - lay.priceIcon - 20, lay.buttonText)
        local textW = Rules.textWidth(price, size)
        local left = bx + math.max(4, math.floor((bw - (lay.priceIcon + 4 + textW)) / 2))
        if spec.gem then Card.picture(card, "PriceIcon", spec.gem, left, buttonY + math.floor((lay.button - lay.priceIcon) / 2) - 2, lay.priceIcon, 38) end
        local priceText = Card.words(card, "Price", price, left + lay.priceIcon + 4, buttonY, textW + 10, lay.button - 6, size, 38)
        priceText.TextXAlignment = Enum.TextXAlignment.Left
    else
        local word = spec.word or "OPEN"
        Card.words(card, "Word", word, bx, buttonY, bw, lay.button - 6, Rules.fitSize(word, bw - 16, lay.buttonText), 38)
    end
    Card.tap(card, "ButtonTap", bx, buttonY, bw, lay.button, 39, spec.onPick)
    return card
end

return Card
