--!strict
-- BD-1287 (docs/246, owner 2026-11-22: "build reusable menus that just look like the proposed approved ones"): the shop menu kit 2 as plain
-- numbers. ChatGPT art made from the owner-APPROVED Aura Shop window (resources/ui/v2/shopkit2, uploaded 2026-11-22): L-stud rarity cards,
-- green and grey buttons, the dark effect strip, green and purple header strips, the red X and the item pictures (a dino wearing the aura).
-- No engine call: the client Kit* modules (KitWindow, KitCard, KitButton, KitStrip, KitRail) place and slice the pictures where these
-- numbers say, tools/verify_sae_frame.py measures every rect below against the real PNGs. Code only places, slices and tiles uploaded
-- pictures; it draws none of them (docs/72). Ids live in AssetSlots.Images; an empty slot keeps the Toybox look (each piece on its own).
local K = {}

-- How a studded piece is drawn (KitArt.studded): the whole picture 9-sliced by `slice` (only its outline and bevel show), then the inside
-- (`inner`: px from each edge to the coloured face) covered by a tile of `crop`, one stud period of the same picture, so the studs keep
-- their shape at any size instead of stretching. All in picture px.
export type Studded = {slot: string, w: number, h: number, slice: {number}, inner: {l: number, t: number, r: number, b: number}, crop: {x: number, y: number, w: number, h: number}, corner: number}
local studded: {[string]: Studded} = {}
local function add(slot: string, w: number, h: number, slice: {number}, inner: {l: number, t: number, r: number, b: number}, crop: {x: number, y: number, w: number, h: number}, corner: number)
    studded[slot] = {slot = slot, w = w, h = h, slice = slice, inner = inner, crop = crop, corner = corner}
end
-- cards 240x328: black outline + dark bevel to x 16 / y 17; L studs every ~53 x 50 px (x 28, 81, 134, 188; y 34, 84, 134 ...)
K.Rarities = {"common", "uncommon", "rare", "epic", "legendary", "mythic"}
for _, rarity in K.Rarities do
    add("shopkit2_card_" .. rarity, 240, 328, {24, 24, 216, 304}, {l = 16, t = 17, r = 16, b = 16}, {x = 62, y = 65, w = 53, h = 50}, 10)
end
-- buttons 210x84: outline + bevel to x 13 / y 12, two rows of L studs about every 27 px; the crop is the whole inside height
for _, colour in {"green", "grey"} do
    add("shopkit2_button_" .. colour, 210, 84, {18, 16, 192, 68}, {l = 13, t = 12, r = 15, b = 14}, {x = 40, y = 12, w = 27, h = 58}, 8)
end
-- the effect strip 296x84 (dark, two rows of faint studs about every 30 px)
add("shopkit2_effect_strip", 296, 84, {18, 16, 278, 68}, {l = 12, t = 12, r = 13, b = 13}, {x = 40, y = 12, w = 30, h = 59}, 8)
K.Studded = studded

-- The header strips 313x85 (green, purple): studs on the left, three shine stripes from x 87 to the right cap. Drawn in five pieces at the
-- strip's height scale (no stretch): the left cap (x 0..42), a tile of one stud column (x 42..67, whole height so the outline runs on),
-- the stripes (x 67..292) starting at StripeAt of the header width, the tile again, the right cap (x 292..313, under the X).
K.HeaderColours = {"green", "purple"}
K.Header = {w = 313, h = 85, leftCap = 42, tile = {x = 42, w = 25}, stripes = {x = 67, w = 225, first = 87}, rightCap = {x = 292, w = 21}}
K.StripeAt = 0.38 -- the first shine stripe starts at 38 % of the header width (the approved Aura Shop header)
K.Close = {w = 111, h = 110} -- the red X, drawn whole (Fit)
-- the window body: the dark effect strip art is the approved window body (dark blue-grey, faint L studs, black outline), so the window is
-- that picture studded at the window size: the outline at BodyCap of its own size, the studs at BodyStuds x (winH / 517, the approved height)
K.BodyCap, K.BodyStuds = 0.55, 1.0
-- the item pictures 512x512: the dino and its aura sit in the middle, so the card shows this square crop (the art then fills its box)
K.ArtCrop = {x = 96, y = 96, w = 320, h = 320} -- the widest picture (Royal) spans x 92..419: at most 4 px of a sparkle is cut

K.Ink = {13, 15, 20} -- every outline and word drop (ToyboxKit.Outline)
K.Green = "#7CFF4F" -- the number on the effect strip ("x1.15" green, "Growth" white), as approved

local function valid(id: any): boolean
    return type(id) == "string" and string.match(id, "^rbxassetid://%d+$") ~= nil
end
-- The bound id of a kit 2 slot, or nil while it is empty (the caller then keeps the Toybox piece).
function K.image(images: {[string]: any}, slot: string): string?
    local id = images[slot]
    return if string.sub(slot, 1, 9) == "shopkit2_" and valid(id) then id else nil
end
function K.cardSlot(rarity: string?): string
    local r = string.lower(rarity or "common")
    return "shopkit2_card_" .. (if table.find(K.Rarities, r) then r else "common")
end
function K.headerSlot(colour: string): string
    return "shopkit2_header_" .. (if table.find(K.HeaderColours, colour) then colour else "green")
end
function K.buttonSlot(grey: boolean?): string
    return if grey then "shopkit2_button_grey" else "shopkit2_button_green"
end
K.StripSlot = "shopkit2_effect_strip"
K.CloseSlot = "shopkit2_close"
-- The card picture slot of a shop item: an aura by its id ("shopkit2_card_art_aura_meadow"), a trail by its name in snake case
-- ("Fern Drift" -> "shopkit2_card_art_trail_fern_drift"). nil for other tabs.
function K.artSlot(tab: string, item: any): string?
    if type(item) ~= "table" then return nil end
    if tab == "auras" and type(item.id) == "string" then return "shopkit2_card_art_aura_" .. item.id end
    if tab == "trails" and type(item.name) == "string" then
        return "shopkit2_card_art_trail_" .. string.gsub(string.lower(item.name), "%s+", "_")
    end
    return nil
end

-- The five header pieces for a header of width w and height h: {x, w, cropX, cropW, tile}. tile = the stud column repeated over that width.
function K.headerPieces(w: number, h: number): {{x: number, w: number, cropX: number, cropW: number, tile: boolean}}
    local H = K.Header
    local k = h / H.h
    local left = math.floor(H.leftCap * k + 0.5)
    local right = math.floor(H.rightCap.w * k + 0.5)
    local stripesW = math.floor(H.stripes.w * k + 0.5)
    local stripesX = math.floor(w * K.StripeAt - (H.stripes.first - H.stripes.x) * k + 0.5)
    stripesX = math.clamp(stripesX, left, math.max(left, w - right - stripesW))
    local out = {{x = 0, w = left, cropX = 0, cropW = H.leftCap, tile = false}}
    if stripesX > left then table.insert(out, {x = left, w = stripesX - left, cropX = H.tile.x, cropW = H.tile.w, tile = true}) end
    local shown = math.min(stripesW, w - right - stripesX) -- a header too short for all three stripes shows the first ones, never squeezed
    table.insert(out, {x = stripesX, w = shown, cropX = H.stripes.x, cropW = math.floor(shown / k + 0.5), tile = false})
    local after = stripesX + stripesW
    if w - right > after then table.insert(out, {x = after, w = w - right - after, cropX = H.tile.x, cropW = H.tile.w, tile = true}) end
    table.insert(out, {x = w - right, w = right, cropX = H.rightCap.x, cropW = H.rightCap.w, tile = false})
    return out
end

return K
