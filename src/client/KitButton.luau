--!strict
-- BD-1287 (docs/246): the shop menu kit button, as on the owner-approved Aura Shop card: the green studded kit 2 button with the orange
-- crystal and the whole price in big white outlined numbers, or the grey one with a word (a lock: "Level 3", "Coming soon"). While the kit 2
-- button is not bound it is the Toybox gloss button. Screens pass only data: KitButton.draw(parent, name, x, y, w, h, z, spec).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Kit2 = require(Shared.ShopKit2)
local Rules = require(Shared.SaeFrameRules)
local Art = require(script.Parent.KitArt)

local B = {}

export type Spec = {
    price: number?, -- a price: the green button with the crystal and the number
    word: string?, -- else this word ("OPEN" when nil)
    grey: boolean?, -- the grey button (a lock)
    gem: string?, -- the crystal picture id (the HUD counter's orange crystal)
    textSize: number, iconSize: number?,
    onPress: (() -> ())?,
}

function B.draw(parent: Instance, name: string, x: number, y: number, w: number, h: number, z: number, spec: Spec): Frame
    local holder = Art.box(parent, name, x, y, w, h, z)
    local k = h / Kit2.Studded[Kit2.buttonSlot(spec.grey)].h
    if not Art.studded(holder, "Face", Kit2.buttonSlot(spec.grey), 0, 0, w, h, z, k, k) then
        Art.kit(holder, "Face", if spec.grey then "toybox_button_grey" else "toybox_button_green", 0, 0, w, h, z)
    end
    local lift = math.floor(h * 0.06) -- the face sits above the button's bottom edge: the words centre on the face
    if spec.price then
        local price = Rules.grouped(spec.price)
        local icon = spec.iconSize or math.floor(h * 0.72)
        local size = Rules.fitSize(price, w - icon - 20, spec.textSize)
        local textW = Rules.textWidth(price, size)
        local left = math.max(4, math.floor((w - (icon + 4 + textW)) / 2))
        if spec.gem then Art.picture(holder, "PriceIcon", spec.gem, left, math.floor((h - icon) / 2) - lift, icon, icon, z + 1) end
        local words = Art.words(holder, "Price", price, left + icon + 4, -lift, textW + 10, h, size, z + 1)
        words.TextXAlignment = Enum.TextXAlignment.Left
    else
        local word = spec.word or "OPEN"
        Art.words(holder, "Word", word, 0, -lift, w, h, Rules.fitSize(word, w - 16, spec.textSize), z + 1)
    end
    if spec.onPress then Art.tap(holder, "Tap", 0, 0, w, h, z + 3, spec.onPress) end
    return holder
end

return B
