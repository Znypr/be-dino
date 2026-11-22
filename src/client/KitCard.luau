--!strict
-- BD-1287 (docs/246, owner 2026-11-22: "build reusable menus that just look like the proposed approved ones"): ONE shop card, the owner's
-- APPROVED Aura Shop card, for every shop page on the kit window: the kit 2 L-stud rarity card (9-sliced, the black outline kept, the studs
-- tiled so they never stretch), the name in big white outlined words with the small rarity word under it, a BIG centred picture (the dino
-- wearing the aura, up to 55 % of the card), the dark effect strip ("x1.15 Growth", the number green) and the kit button (the orange crystal
-- + the price, or the grey one with a word). While the kit 2 card is not bound it is the Toybox rarity card. Sizes: Shared/SaeFrameRules.
-- Screens pass only data: KitCard.draw(parent, rect, spec, lay).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Kit2 = require(Shared.ShopKit2)
local Rules = require(Shared.SaeFrameRules)
local Art = require(script.Parent.KitArt)
local Button = require(script.Parent.KitButton)
local Strip = require(script.Parent.KitStrip)

local Card = {}

export type Spec = {
    key: string, -- names the card ("KitCard_<key>")
    rarity: string, -- the card colour: Common, Uncommon, Rare, Epic, Legendary, Mythic
    name: string, rarityWord: string?, -- the big name and the small word under it
    picture: string?, pictureCrop: {x: number, y: number, w: number, h: number}?, -- the item picture (and the part of it to show)
    effect: string?, effectRich: string?, -- the strip line (effectRich: the same with the number green)
    price: number?, word: string?, grey: boolean?, -- the button: a price (green), else the word (grey = a lock)
    gem: string?, onPick: () -> (),
}

-- The Toybox card (fallback): the kit 1 rarity card 9-sliced, its pale top band covered by its own studded body.
local function toyboxFace(parent: Instance, slot: string, w: number, h: number, z: number)
    local face = Art.kit(parent, "Face", slot, 0, 0, w, h, z)
    local id = Kit.image(Slots.Images, slot)
    if not face or not id then return end
    local k = face.SliceScale
    local inset, crop = Rules.CardInset, Rules.CardStudCrop
    local sx, ty, by = math.ceil(inset.side * k), math.ceil(inset.top * k), math.ceil(inset.bottom * k)
    Art.tiled(parent, "Studs", id, sx, ty, w - 2 * sx, h - ty - by, z, crop, math.max(8, crop.w * k), math.max(8, crop.h * k))
end

-- One card in `parent` at rect r (lay = SaeFrameRules.layout: the card sizes). Tapping anywhere on it calls spec.onPick.
function Card.draw(parent: Instance, r: Rules.Rect, spec: Spec, lay: Rules.Layout): Frame
    local card = Art.box(parent, "KitCard_" .. spec.key, r.x, r.y, r.w, r.h, 34)
    local slot = Kit2.cardSlot(spec.rarity)
    local d = Kit2.Studded[slot]
    -- the outline at about 70 % of the picture's own size, the studs at the card's width (four columns, as approved)
    local studK = r.w / d.w
    if not Art.studded(card, "Face", slot, 0, 0, r.w, r.h, 34, studK * 0.7, studK) then
        toyboxFace(card, Rules.RarityCard[spec.rarity] or Rules.RarityCard.Common, r.w, r.h, 34)
    end
    Art.tap(card, "Tap", 0, 0, r.w, r.h, 35, spec.onPick)
    local edge = lay.edge
    Art.words(card, "Name", spec.name, 4, edge, r.w - 8, lay.nameH, Rules.fitSize(spec.name, r.w - 12, lay.cardTitle), 38)
    if spec.rarityWord then Art.words(card, "Rarity", spec.rarityWord, 4, edge + lay.nameH - 2, r.w - 8, lay.rarityH, lay.rarityText, 38) end
    local buttonY = r.h - edge - lay.button
    local stripY = buttonY - lay.innerGap - lay.lineH
    local artBottom = (if lay.line then stripY - 2 else buttonY - 2) - ((lay :: any).artGap or 0) -- BD-1298: room for a screen line over the strip
    local art = math.min(lay.art, artBottom - lay.artTop, r.w - 4)
    if spec.picture and art > 0 then
        Art.picture(card, "Picture", spec.picture, math.floor((r.w - art) / 2), lay.artTop + math.floor((artBottom - lay.artTop - art) / 2), art, art, 36, spec.pictureCrop)
    end
    if lay.line and spec.effect then
        Strip.draw(card, "Strip", lay.stripInset, stripY, r.w - 2 * lay.stripInset, lay.lineH, 37, {text = spec.effect, rich = spec.effectRich, textSize = lay.lineText})
    end
    Button.draw(card, "Button", lay.buttonInset, buttonY, r.w - 2 * lay.buttonInset, lay.button, 37, {
        price = spec.price, word = spec.word, grey = spec.grey, gem = spec.gem, textSize = lay.buttonText, iconSize = lay.priceIcon,
        onPress = spec.onPick,
    })
    return card
end

return Card
