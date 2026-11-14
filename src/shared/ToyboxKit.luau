--!strict
-- BD-1177 (docs/228 board 1, docs/230): the "Toybox" UI kit as plain numbers. No engine call, no clock, no RNG: tools/verify_toybox_ui.py
-- runs this file with the pinned Luau runtime and measures every slice rect below against the real PNGs.
-- The art is Blender renders (resources/ui/v2/toybox/final, source assets/blender/ui/toybox-kit-v1.blend; the owner picked draft A on
-- 2026-11-13). Code only places and slices the pictures; it draws none of them (docs/72). Ids live in AssetSlots.Images ("" until the
-- upload is bound with tools/bind_assets.py); a group whose ids are not all bound keeps today's look (Kit.ready).
local Kit = {}

Kit.MinText = 14 -- docs/72 floor: no text under 14 px
Kit.MinClose = 48 -- docs/202 R6 / BD-1117: the X is a square of at least 48 px on screen
Kit.StrokeSmall, Kit.StrokeBig, Kit.StrokeBigFrom = 4, 4, 28 -- owner 2026-11-14 (C-57): text outline 4 px at every size (was 3 px, 4 px from 28 px text up)
Kit.DropPixels = 3 -- the dark copy of a title or button word sits this far under it
Kit.Outline = {13, 15, 20} -- the same dark as Theme.Colors.outline / TextStyle.Dark

Kit.HeaderColours = {"amber", "green", "blue", "purple", "dark", "cream", "red"}
Kit.ButtonColours = {"green", "grey", "gold", "blue", "red", "purple", "dark"}
Kit.CardRarities = {"common", "uncommon", "rare", "epic", "legendary", "mythic"}

type Asset = {slot: string, file: string, w: number, h: number, slice: {number}?, fit: string?}
-- slice = {x0, y0, x1, y1}: the stretching centre of the 9-slice in picture pixels (Roblox Rect.new(x0, y0, x1, y1)).
--   header (512x128): the centre is the stripe-free band between the first and the second shine stripe, so no stripe is ever stretched;
--     fit = "height": the slice scale is height / 128, so nothing stretches up or down either. Corner 21 px, outline 5 px, drop 11 px.
--   button (256x112): corner 16 px, outline 4 px, drop 8 px; the two flat tones meet at y 51..52 inside the centre and stretch as flat colour.
--   card (256x320): the centre is a stud-free patch of the light top band, so the studs keep their shape (they stay in the right and bottom caps).
--   frame (256x256): corner 30 px, edge 10 px (bottom 14 px with the drop); flat centre.
local HEADER_SLICE, BUTTON_SLICE, CARD_SLICE, FRAME_SLICE = {150, 30, 224, 98}, {24, 20, 232, 88}, {70, 34, 108, 92}, {36, 36, 220, 220}
local assets: {[string]: Asset} = {}
local function add(slot: string, file: string, w: number, h: number, slice: {number}?, fit: string?)
    assets[slot] = {slot = slot, file = file, w = w, h = h, slice = slice, fit = fit}
end
for _, colour in Kit.HeaderColours do add("toybox_header_" .. colour, "header-" .. colour .. ".png", 512, 128, HEADER_SLICE, "height") end
for _, colour in Kit.ButtonColours do add("toybox_button_" .. colour, "button-" .. colour .. ".png", 256, 112, BUTTON_SLICE) end
for _, rarity in Kit.CardRarities do add("toybox_card_" .. rarity, "card-" .. rarity .. ".png", 256, 320, CARD_SLICE) end
add("toybox_close", "close.png", 128, 128) -- drawn whole (Fit), never sliced
add("toybox_panel_frame", "panel-frame.png", 256, 256, FRAME_SLICE)
add("toybox_studs_tile", "studs-tile.png", 256, 256) -- tiled, never sliced
Kit.Assets = assets
Kit.Folder = "resources/ui/v2/toybox/final"

Kit.SliceScale = 0.5 -- buttons, cards and the frame are drawn at half picture size: button corner 8 px, frame corner 15 px
Kit.StudTile = 128 -- px of one studs-tile repeat on a window (4 x 4 studs, 32 px apart)
Kit.StudInset = {left = 5, top = 5, right = 5, bottom = 7} -- the frame edge at half size: the studs stay inside it
Kit.StudCorner = 10

-- The groups: a group is used only when every id of it is bound, so a window never shows half a kit.
Kit.Groups = {"header", "button", "card", "close", "panel"}
function Kit.slots(group: string): {string}
    local out = {}
    if group == "header" then for _, c in Kit.HeaderColours do table.insert(out, "toybox_header_" .. c) end
    elseif group == "button" then for _, c in Kit.ButtonColours do table.insert(out, "toybox_button_" .. c) end
    elseif group == "card" then for _, r in Kit.CardRarities do table.insert(out, "toybox_card_" .. r) end
    elseif group == "close" then out = {"toybox_close"}
    elseif group == "panel" then out = {"toybox_panel_frame", "toybox_studs_tile"} end
    return out
end
local function valid(id: any): boolean
    return type(id) == "string" and string.match(id, "^rbxassetid://%d+$") ~= nil
end
-- The bound id of a slot, or nil while it is empty or malformed (never an invented id).
function Kit.image(images: {[string]: any}, slot: string): string?
    local id = images[slot]
    return if assets[slot] ~= nil and valid(id) then id else nil
end
function Kit.ready(images: {[string]: any}, group: string): boolean
    local list = Kit.slots(group)
    if #list == 0 then return false end
    for _, slot in list do if Kit.image(images, slot) == nil then return false end end
    return true
end

-- Places and their header colour (owner, docs/228): amber Crystal Shop, green Potions, blue Dinos / Index, purple Fusion, cream Eggs,
-- dark Settings. Red is kept for the X only, so no place uses the red header.
Kit.PlaceHeader = {shop = "amber", potions = "green", dinos = "blue", fusion = "purple", eggs = "cream", settings = "dark"}
Kit.DefaultPlace = "dinos" -- an unknown screen keeps blue, the colour the window header has today before a screen sets one
-- Every screen name the menu window opens (Bootstrap open(name)) and the place it belongs to.
-- PROVISIONAL (LEAD fill-ins, docs/228 names six places only): home = dinos, results / starter / batchSummary = eggs, exit and the Food page = settings.
Kit.ScreenPlace = {
    auras = "shop", auraConfirm = "shop", auraInfo = "shop", conditionConfirm = "shop", eggPurchase = "shop", crystalReveal = "shop",
    eggOdds = "shop", eggOutcomes = "shop", oddsSimple = "shop",
    potions = "potions", potionConfirm = "potions", potionReplace = "potions",
    collection = "dinos", detail = "dinos", home = "dinos", tutorial = "dinos",
    fusion = "fusion",
    eggs = "eggs", hatch = "eggs", results = "eggs", batchSummary = "eggs", starter = "eggs",
    settings = "settings", food = "settings", exit = "settings",
}
function Kit.placeOf(screen: string?): string
    return (if screen then Kit.ScreenPlace[screen] else nil) or Kit.DefaultPlace
end
-- Owner 2026-11-14 (C-58): the dino detail page keeps its rarity colour under the skin. Rarity tier 1..6 (Common .. Mythic) -> header picture,
-- the nearest kit colour to Theme.RarityColors. PROVISIONAL (LEAD): Common = cream (the kit has no grey header), Mythic = red.
Kit.RarityHeader = {"cream", "green", "blue", "purple", "amber", "red"}
function Kit.raritySlot(tier: number): string
    return "toybox_header_" .. (Kit.RarityHeader[tier] or Kit.RarityHeader[1])
end
function Kit.headerOf(place: string): string
    return Kit.PlaceHeader[place] or Kit.PlaceHeader[Kit.DefaultPlace]
end
-- The header picture of a screen of the menu window (nil or unknown = blue) ...
function Kit.headerSlot(screen: string?): string
    return "toybox_header_" .. Kit.headerOf(Kit.placeOf(screen))
end
-- ... and of a window that always belongs to one place (the Fusion Menu).
function Kit.placeSlot(place: string): string
    return "toybox_header_" .. Kit.headerOf(place)
end

-- Which gloss button a flat button colour becomes: the nearest of the seven (0..255 rgb). The anchors are the Theme colours the screens use.
Kit.ButtonAnchors = {
    green = {93, 237, 31}, grey = {128, 142, 158}, gold = {255, 210, 43}, blue = {46, 206, 255},
    red = {247, 57, 48}, purple = {194, 86, 255}, dark = {61, 58, 73},
}
function Kit.buttonKey(r: number, g: number, b: number): string
    -- a colourless button (white, grey, black, the card and panel colours) is grey when light and dark when dark, never a colour
    if math.max(r, g, b) - math.min(r, g, b) < 40 then return if (r + g + b) / 3 >= 100 then "grey" else "dark" end
    local best, bestDistance = "dark", math.huge
    for _, key in Kit.ButtonColours do -- fixed order: a tie always gives the same button
        local a = Kit.ButtonAnchors[key]
        local d = (a[1] - r) ^ 2 + (a[2] - g) ^ 2 + (a[3] - b) ^ 2
        if d < bestDistance then best, bestDistance = key, d end
    end
    return best
end
function Kit.buttonSlot(r: number, g: number, b: number): string
    return "toybox_button_" .. Kit.buttonKey(r, g, b)
end

-- Text: one outlined style. 3 px outline, 4 px from 28 px text up; never under 14 px.
function Kit.stroke(textSize: number): number
    local size = if textSize == textSize then textSize else Kit.MinText
    return if size >= Kit.StrokeBigFrom then Kit.StrokeBig else Kit.StrokeSmall
end
function Kit.textSize(size: number): number
    local wanted = if size == size then size else Kit.MinText
    return math.max(wanted, Kit.MinText)
end

-- The X: a square. absW / absH = the button's size on screen, scale = the window's UIScale. Returns the side in design px (before the
-- UIScale), so that the square is the short side of the button but never under 48 px on screen.
function Kit.closeSide(absW: number, absH: number, scale: number): number
    local s = if scale == scale and scale > 0.01 then scale else 1
    local short = math.min(absW, absH)
    if short ~= short then short = 0 end
    return math.max(short, Kit.MinClose) / s
end

-- The slice scale of a picture drawn `width` x `height` px. A header never stretches up or down (scale = height / 128). The others use
-- half size, less when the box is so small that the caps would not fit.
function Kit.sliceScale(slot: string, width: number, height: number): number
    local asset = assets[slot]
    if asset == nil or asset.slice == nil then return 1 end
    local slice = asset.slice
    if asset.fit == "height" then return math.max(height, 1) / asset.h end
    local capsW, capsH = asset.w - (slice[3] - slice[1]), asset.h - (slice[4] - slice[2])
    return math.max(0.05, math.min(Kit.SliceScale, width / capsW, height / capsH))
end

return Kit
