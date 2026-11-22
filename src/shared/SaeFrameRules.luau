--!strict
-- BD-1287 (docs/246 slice 1): the Crystal Shop landing while Config.MenusSaeFrameEnabled is on, built from the Toybox art kit to match the
-- owner's APPROVED shop window on the Design Board (page Phone UI, "Phone shop windows, built from the art kit"; owner redirect 2026-11-21:
-- "this is not what the proposed menu shop is supposed to look like compare to the dashboard"). Pure numbers, no Instances:
-- client/ShopSaeLanding places the kit pictures where layout() says, tools/verify_sae_frame.py runs it at desktop and phone sizes.
-- The look (the board mocks): the kit panel frame with the studs tile body, the kit green header strip with a big white outlined title at the
-- left and the kit red X at the right; a gold "-- FEATURED --" section heading; big kit rarity cards (name on top, the picture filling the
-- middle, one short kid line, the studded kit green button with the crystal icon and the price, the grey one for a lock); and the tabs
-- OUTSIDE the window on the right as an icon with a white outlined word under it, no tile box behind (Featured, Auras, Trails, Eggs, Potions).
-- Every % is of the whole SCREEN (ScreenGui height + the top bar inset), every position is in ScreenGui px. No text under 19 px (docs/72).
-- Window from 16 % to 88 % of the screen height, 49 % W (58 % narrowed by 15 %, ChatGPT round on v3); the HUD is hidden and the world
-- blurred (14 px) while it is open, like the approved one. v4 finish (ChatGPT 7.5/10 on v3, "structure close, finish differs"): boxy
-- corners (cards 4 px, window 6 px, 3 px black outlines), cards in ONE full-strength colour top to bottom with the faint stud pattern, the
-- body #343447 with low-contrast studs, the header about 19.5 % of the window, names 8 % of the window, buttons 9.5 %, art 43-50 % of
-- the card, standalone rail icons 13 % of the window with bold outlined words. Sizes inside the window are % of the WINDOW height.
local R = {}

R.Cover = 0.94 -- ModalScrim transparency while the window shows: 6 % dark overlay over the blurred world (5-8 %)
R.Blur = 14 -- px of the menus' blur behind the window (12-16 at 720 p)
R.WidthShare = 0.58 * 0.85 -- the window width share of the screen
R.OutlinePx = 3
R.ArtMax = 0.55 -- the picture's share of the card height: at most 55 % (the approved cards), at least 43 % where it fits
-- owner 2026-11-21 on v4 ("crystal shop looks too different"): the window is built from the kit pictures 1:1, as the approved one. A card is
-- the kit rarity card picture (9-sliced); its pale top band is covered by the card's own studded body (a crop of one stud period of the same
-- picture, x 88..168, y 158..233 of 256x320: studs every 80 x 75 px), so the card is one rarity colour top to bottom with studs, like the
-- approved cards. Inset of the studded fill inside the card outline, in picture px: 5 top and sides, 10 at the bottom (outline + drop).
R.CardStudCrop = {x = 88, y = 158, w = 80, h = 75}
R.CardInset = {side = 6, top = 6, bottom = 11}
-- lead review 2026-11-21 (the approved window): the world is blurred (the menus' normal blur) and the HUD is hidden while a kit shop window
-- is open, and the window runs from 16 % to 88 % of the screen height
R.Top, R.Bottom = 0.16, 0.88
R.MinText = 19
R.MinTap = 44
R.MinClose = 48
R.MaxCards = 3
R.Title = "Crystal Shop"
R.Featured = "-- FEATURED --"
R.Gold = {255, 214, 64} -- the section heading words (the mock's gold "-- BOOSTS --")
R.Ink = {13, 15, 20} -- ToyboxKit.Outline: every outline and word drop
R.HeaderSlot = "toybox_header_green" -- the Crystal Shop is green (an Aura page would be purple)
-- the tabs on the right, in the mocks' order; "featured" is this landing page itself
R.RailTabs = {"featured", "auras", "trails", "eggs", "potions"}
R.RailWords = {featured = "Featured", auras = "Auras", trails = "Trails", eggs = "Eggs", potions = "Potions"}
-- the kit card per featured slot: the item's rarity card (the approved Aura Shop: Common grey, Rare cyan, Legendary gold); the egg gold
R.RarityCard = {Common = "toybox_card_common", Uncommon = "toybox_card_uncommon", Rare = "toybox_card_rare", Epic = "toybox_card_epic",
    Legendary = "toybox_card_legendary", Mythic = "toybox_card_mythic"}
R.EggCard = "toybox_card_legendary"
R.EggWord = "Surprise" -- the small word under the egg's name (the others show their rarity)
-- the kit header's shine stripes repeat every 160 px of the 512 px picture (x 105, 265, 425); the 9-slice centre (x 150..224) has none, so
-- the client lays crops of x 150..310 (one stripe each) across the stretched middle, at the header's slice scale (lead review: "reads flat")
R.HeaderStripeCrop = {x = 150, w = 160, h = 128}
R.HeaderCaps = {left = 150, right = 512 - 224}
-- the strip line per card: an aura shows its growth as on the approved Aura Shop card ("x1.15 Growth", R.auraLine); the others a kid line
R.Lines = {auras = "Glow while you grow!", trails = "Leave a trail!", eggs = "A surprise dino!"}

local function round(x: number): number return math.floor(x + 0.5) end

-- The approved Aura Shop strip: "x1.15 Growth" (the number from ProgressionConfig.Auras growth). Returns the plain words and the same with
-- the number in green (RichText).
function R.auraLine(growth: number?): (string, string)
    local n = string.format("x%g", math.floor((growth or 1) * 100 + 0.5) / 100)
    return n .. " Growth", '<font color="#7CFF4F">' .. n .. "</font> Growth"
end

-- Estimated width in px of a FredokaOne word at this size (0.56 em per character, a little wider than the real average).
function R.textWidth(text: string, size: number): number
    return math.ceil(#text * 0.56 * size)
end

-- The biggest size from `max` down to 19 at which `text` fits `width` (never under the floor: the caller lets it clip only at 19).
function R.fitSize(text: string, width: number, max: number): number
    local size = max
    while size > R.MinText and R.textWidth(text, size) > width do size -= 1 end
    return size
end

-- 1250 -> "1,250" (kid words: a whole number, never "1.25k").
function R.grouped(n: number): string
    local out = tostring(math.max(0, math.floor(n)))
    while true do
        local nxt, k = string.gsub(out, "^(%d+)(%d%d%d)", "%1,%2")
        out = nxt
        if k == 0 then break end
    end
    return out
end

-- What the three cards show. d = {auras = ProgressionConfig.Auras, ownedAuras, trails = ProgressionConfig.Trails, ownedTrails, level,
-- eggPrice, eggBlocked}. Each entry is {tab, item?, price?, state, level?}:
--   "buy"    the cheapest aura / trail the player does not own and may buy now, or the egg while it can be bought (the green price button);
--   "locked" no trail can be bought yet: the next one by level (picture, name, the grey "Level N" button);
--   "soon"   the egg while the shop cannot sell it (PaidRandomGate): the egg picture and name, the grey "Coming soon" button;
--   "open"   nothing left there (everything owned): the category picture and name, OPEN.
-- Tapping any card opens its category page; the purchase confirm there does the buying.
function R.featured(d: any): {{tab: string, item: any?, price: number?, state: string, level: number?}}
    local function cheapest(list: any, owned: any, level: number?): any?
        local best = nil
        for _, item in (list or {}) do
            local mine = type(owned) == "table" and owned[item.id] == true
            local open = level == nil or (item.level or 1) <= level
            if not mine and open and type(item.price) == "number" and item.price > 0 and (best == nil or item.price < best.price) then best = item end
        end
        return best
    end
    local function nextLocked(list: any, owned: any, level: number): any?
        local best = nil
        for _, item in (list or {}) do
            local mine = type(owned) == "table" and owned[item.id] == true
            if not mine and (item.level or 1) > level and (best == nil or (item.level or 1) < (best.level or 1)) then best = item end
        end
        return best
    end
    local level = d.level or 1
    local out = {}
    local aura = cheapest(d.auras, d.ownedAuras, nil)
    table.insert(out, if aura then {tab = "auras", item = aura, price = aura.price, state = "buy"} else {tab = "auras", state = "open"})
    local trail = cheapest(d.trails, d.ownedTrails, level)
    if trail then
        table.insert(out, {tab = "trails", item = trail, price = trail.price, state = "buy"})
    else
        local later = nextLocked(d.trails, d.ownedTrails, level)
        table.insert(out, if later then {tab = "trails", item = later, state = "locked", level = later.level} else {tab = "trails", state = "open"})
    end
    if type(d.eggPrice) == "number" and d.eggPrice > 0 then
        local egg = {id = "random", name = "Random Egg", price = d.eggPrice}
        table.insert(out, if d.eggBlocked == true then {tab = "eggs", item = egg, state = "soon"} else {tab = "eggs", item = egg, price = egg.price, state = "buy"})
    else
        table.insert(out, {tab = "eggs", state = "open"})
    end
    return out
end

-- The word on a card's button for a state that is not "buy" (kid words).
function R.buttonWord(entry: any): string
    if entry.state == "locked" then return "Level " .. tostring(entry.level or 1) end
    if entry.state == "soon" then return "Coming soon" end
    return "OPEN"
end

-- The kit card picture of a featured entry.
function R.cardSlot(entry: any): string
    if entry.tab == "eggs" then return R.EggCard end
    local rarity = if entry.item then entry.item.rarity else nil
    return R.RarityCard[rarity or "Common"] or R.RarityCard.Common
end

-- The card title as on the approved cards: the first word of an aura or trail name ("Meadow", "Tidal", "Royal"), the egg's whole name.
function R.cardTitle(entry: any, fallback: string): string
    local item = entry.item
    if not item then return fallback end
    if entry.tab == "auras" or entry.tab == "trails" then return string.match(item.name, "^(%S+)") or item.name end
    return item.name
end

export type Rect = {x: number, y: number, w: number, h: number}
export type Layout = {
    window: Rect, frameInset: number, headerH: number, close: number, titleSize: number, heading: Rect, headingSize: number, showHeading: boolean,
    pad: number, cards: {Rect}, edge: number, nameH: number, cardTitle: number, rarityText: number, rarityH: number, line: boolean, lineH: number,
    lineText: number, art: number, button: number, buttonText: number, priceIcon: number,
    rail: {x: number, y: number, icon: number, selectedIcon: number, labelSize: number, gap: number, colW: number, slots: {Rect}},
}

-- w, guiH: ScreenGui AbsoluteSize. cards: how many cards (1..3). inset: the top bar above the ScreenGui.
function R.layout(w: number, guiH: number, cards: number, inset: number?): Layout
    w, guiH = math.max(320, w), math.max(240, guiH)
    local top = math.max(0, inset or 0)
    local h = guiH + top -- the screen height the % are taken of
    local nCards = math.clamp(cards, 1, R.MaxCards)
    local short = h < 600
    local frameInset = R.OutlinePx + 1 -- the header and the body sit inside the 3 px window outline
    local winY = math.max(4, round(h * R.Top) - top)
    local winH = math.min(round(h * (R.Bottom - R.Top)), guiH - 8)
    if winY + winH > guiH - 4 then winY = math.max(4, guiH - 4 - winH) end
    -- inside the window: % of the WINDOW height (ChatGPT v4), never under the phone floors
    local close = math.max(R.MinClose, round(winH * 0.14))
    local headerH = math.max(round(winH * 0.195), close + 6)
    local titleSize = math.clamp(round(headerH * 0.55), 26, 56)
    local pad = if short then 6 else math.max(10, round(winH * 0.025))
    local cardGap = math.clamp(round(w * 0.009), 8, 14)
    local headingSize = if short then math.max(22, round(h * 0.045)) else math.clamp(round(h * 0.045), 30, 34)
    local cardTitle = 23 -- set from the card width below (the approved titles: about 19 % of the card width)
    local rarityText = if short then R.MinText else math.clamp(round(winH * 0.04), 19, 22)
    local lineText = if short then R.MinText else math.clamp(round(winH * 0.04), 19, 22)
    local button = math.max(46, round(winH * 0.095))
    local buttonText = math.clamp(round(button * 0.55), 25, 32)
    local edge = if short then 6 else 10
    local nameH = cardTitle + 2
    local rarityH = rarityText + 2
    local lineH = lineText + 4
    local cardMin = edge + 25 + 40 + button + edge -- a picture of at least 40 px
    local minW = nCards * 128 + (nCards - 1) * cardGap + 2 * (pad + frameInset)
    local winW = math.min(math.max(round(w * R.WidthShare), minW), w - 16)
    local winX = round((w - winW) / 2)
    -- the section heading and the cards fill the body under the header
    local bodyTop = frameInset + headerH + pad
    local bodyH = winH - bodyTop - pad - frameInset
    local headingH = headingSize + 2
    local cardW = math.floor((winW - 2 * (frameInset + pad) - (nCards - 1) * cardGap) / nCards)
    cardTitle = math.clamp(round(cardW * 0.19), 23, 46)
    nameH = cardTitle + 2
    -- inside a card (client/ShopKitCard, the approved Aura Shop card): the name on top with the small rarity word under it, the picture
    -- (43-50 % of the card), the dark strip with one short line (dropped only when the picture would fall under 36 px), the button at the bottom
    local function cardFor(withHeading: boolean): (number, number, boolean, number)
        local y = bodyTop + (if withHeading then headingH + 4 else 0)
        local ch = winH - frameInset - pad - y
        local room = ch - 2 * edge - nameH - rarityH - button - 6
        local withLine = room - lineH - 5 >= 36
        local fit = room - (if withLine then lineH + 5 else 0)
        return y, ch, withLine, math.max(0, math.min(fit, cardW - 2 * edge, round(ch * R.ArtMax)))
    end
    -- FEATURED shows where it leaves a picture of at least 43 % of the card (a short canvas keeps the room for the cards)
    local showHeading = bodyH - headingH - 4 >= cardMin
    local cardY, cardH, line, art = cardFor(showHeading)
    if showHeading and art < 0.43 * cardH then
        showHeading = false
        cardY, cardH, line, art = cardFor(false)
    end
    local list: {Rect} = {}
    for i = 1, nCards do
        table.insert(list, {x = frameInset + pad + (i - 1) * (cardW + cardGap), y = cardY, w = cardW, h = cardH})
    end
    -- the rail: standalone illustrated icons (13 % of the window height) with a bold outlined word under each, no box; the selected one bigger
    local icon = math.max(R.MinTap, round(winH * 0.13))
    local labelSize = if short then R.MinText else math.clamp(round(h * 0.027), 19, 22)
    local gap = math.max(4, round(h * 0.01))
    local longest = 0
    for _, tab in R.RailTabs do longest = math.max(longest, R.textWidth(R.RailWords[tab], labelSize)) end
    local colW = math.max(icon, longest + 6)
    local railX = winX + winW + math.max(6, round(w * 0.0125))
    if railX + colW > w - 4 then colW = math.max(icon, w - 4 - railX) end
    local slotH = icon + labelSize + 2
    local n = #R.RailTabs
    local railH = n * slotH + (n - 1) * gap
    local railY = winY + frameInset
    if railY + railH > guiH - 4 then railY = math.max(4, guiH - 4 - railH) end
    local slots: {Rect} = {}
    for i = 1, n do table.insert(slots, {x = railX, y = railY + (i - 1) * (slotH + gap), w = colW, h = slotH}) end
    return {
        window = {x = winX, y = winY, w = winW, h = winH}, frameInset = frameInset, headerH = headerH, close = close, titleSize = titleSize,
        heading = {x = frameInset + pad, y = bodyTop, w = winW - 2 * (frameInset + pad), h = headingH}, headingSize = headingSize, showHeading = showHeading,
        pad = pad, cards = list, edge = edge, nameH = nameH, cardTitle = cardTitle, rarityText = rarityText, rarityH = rarityH, line = line, lineH = lineH,
        lineText = lineText, art = art, button = button, buttonText = buttonText, priceIcon = button - 14,
        rail = {x = railX, y = railY, icon = icon, selectedIcon = round(icon * 1.12), labelSize = labelSize, gap = gap, colW = colW, slots = slots},
    }
end

return R
