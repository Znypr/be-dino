--!strict
-- BD-1287 (docs/246 slice 1): the numbers of the shop menu kit window (client/KitWindow, KitCard, KitButton, KitStrip, KitRail) and of the
-- Crystal Shop landing built on it while Config.MenusSaeFrameEnabled is on. The target is the owner's APPROVED Aura Shop window (owner
-- 2026-11-22: "build reusable menus that just look like the proposed approved ones"): a dark studded window with a striped header strip and a
-- big white outlined title at the left, the red X at the right, big rarity cards (name, small rarity word, the item picture, a dark effect
-- strip "x1.15 Growth", the green price button with the orange crystal), and the tabs OUTSIDE the window on the right as an icon with a white
-- outlined word under it, no box (Featured, Auras, Trails, Eggs, Potions). Pure numbers, no Instances: tools/verify_sae_frame.py runs it at
-- desktop and phone sizes. Every % is of the whole SCREEN (ScreenGui height + the top bar inset) unless it says window or card; positions are
-- ScreenGui px. No text under 19 px (docs/72). The HUD is hidden and the world blurred (14 px) while the window is open, like the approved one.
-- The art: Shared/ShopKit2 (the kit 2 pictures made from the approved window); while a kit 2 slot is empty that piece keeps the Toybox look
-- (Shared/ToyboxKit; the Card* and Header* crops below are for that fallback).
local R = {}

R.Cover = 0.94 -- ModalScrim transparency while the window shows: 6 % dark overlay over the blurred world (5-8 %)
R.Blur = 14 -- px of the menus' blur behind the window (12-16 at 720 p)
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
R.Ink = {13, 15, 20} -- ToyboxKit.Outline: every outline and word drop
R.HeaderColour = "green" -- the Crystal Shop is green (the Aura page will be purple)
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

-- The rarity of a featured entry's card (kit 2 card colour): the item's rarity; the egg on the gold (Legendary) card.
function R.cardRarity(entry: any): string
    if entry.tab == "eggs" then return "Legendary" end
    return if entry.item and type(entry.item.rarity) == "string" then entry.item.rarity else "Common"
end

-- The Toybox kit card picture of a featured entry (the fallback while the kit 2 card is not bound).
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
    window: Rect, frameInset: number, headerInset: number, headerH: number, close: number, titleSize: number,
    pad: number, cards: {Rect}, edge: number, nameH: number, cardTitle: number, rarityText: number, rarityH: number, line: boolean, lineH: number,
    lineText: number, stripInset: number, innerGap: number, art: number, artTop: number, button: number, buttonInset: number, buttonText: number, priceIcon: number,
    rail: {x: number, y: number, icon: number, selectedIcon: number, labelSize: number, gap: number, colW: number, slots: {Rect}},
}

-- The approved Aura Shop window (1544x720 phone shot), measured: window 725x517 from 16 % to 88 % of the screen (w / h = 1.40); header
-- inset 10 px, 95 px high (18.4 %), the X 86 px (90 % of the header); cards 216x375 (72.5 % of the window), 22 px from the sides, 17 px
-- apart, 17 px under the header. Inside a card (% of the card height): the name 10.5 % with the rarity word under it, the picture from 21 %
-- (the dino and its aura about 51 %), the effect strip 10 % (7 % in from each side), the button 12.3 % (4.5 % in), 2.5 % gaps.
R.Aspect = 1.40
R.HeaderShare, R.CloseShare = 0.184, 0.9
R.CardTop, R.CardSide, R.CardGap = 0.033, 0.03, 0.023 -- of the window height / width / width
R.Card = {edge = 0.025, name = 0.105, rarity = 0.05, strip = 0.10, stripInset = 0.07, button = 0.123, buttonInset = 0.045, gap = 0.025}

-- w, guiH: ScreenGui AbsoluteSize. cards: how many cards (1..3). inset: the top bar above the ScreenGui.
function R.layout(w: number, guiH: number, cards: number, inset: number?): Layout
    w, guiH = math.max(320, w), math.max(240, guiH)
    local top = math.max(0, inset or 0)
    local h = guiH + top -- the screen height the % are taken of
    local nCards = math.clamp(cards, 1, R.MaxCards)
    local frameInset = R.OutlinePx + 1 -- the body sits inside the 3 px window outline
    local winY = math.max(4, round(h * R.Top) - top)
    local winH = math.min(round(h * (R.Bottom - R.Top)), guiH - 8)
    if winY + winH > guiH - 4 then winY = math.max(4, guiH - 4 - winH) end
    local headerInset = math.max(frameInset, round(winH * 0.019))
    local close = math.max(R.MinClose, round(winH * R.HeaderShare * R.CloseShare))
    local headerH = math.max(round(winH * R.HeaderShare), close + 6)
    local titleSize = math.clamp(round(headerH * 0.53), 26, 56)
    local pad = math.max(6, round(winH * R.CardTop))
    -- the window keeps the approved shape (w / h = 1.40) on any screen; never narrower than three cards wide enough for their buttons
    local cardGap = math.max(6, round(winH * R.Aspect * R.CardGap))
    local side = math.max(frameInset + 4, round(winH * R.Aspect * R.CardSide))
    local minW = nCards * 128 + (nCards - 1) * cardGap + 2 * side
    local winW = math.min(math.max(round(winH * R.Aspect), minW), w - 16)
    local winX = round((w - winW) / 2)
    local cardY = headerInset + headerH + pad
    local cardH = winH - cardY - math.max(frameInset + 4, round(winH * 0.039))
    local cardW = math.floor((winW - 2 * side - (nCards - 1) * cardGap) / nCards)
    local C = R.Card
    local edge = math.max(4, round(cardH * C.edge))
    local cardTitle = math.clamp(math.min(round(cardH * C.name), round(cardW * 0.19)), 23, 46)
    local nameH = cardTitle + 2
    local rarityText = math.clamp(round(cardH * C.rarity), R.MinText, 22)
    local rarityH = rarityText + 2
    local button = math.max(R.MinTap, round(cardH * C.button))
    local buttonText = math.clamp(round(button * 0.6), 24, 34)
    local lineText = math.clamp(round(cardH * C.strip * 0.62), R.MinText, 26)
    local lineH = math.max(lineText + 8, round(cardH * C.strip))
    local gap = math.max(3, round(cardH * C.gap))
    -- the picture may run up under the small rarity word (drawn over it): its own top is mostly the aura's glow, as on the approved cards
    local artTop = edge + nameH + round(rarityH * 0.4)
    local room = cardH - artTop - edge - button - gap - lineH - gap
    local line = room >= 40
    if not line then room = cardH - artTop - edge - button - gap end
    local art = math.max(0, math.min(room, cardW - 4, math.floor(cardH * R.ArtMax)))
    local list: {Rect} = {}
    for i = 1, nCards do
        table.insert(list, {x = side + (i - 1) * (cardW + cardGap), y = cardY, w = cardW, h = cardH})
    end
    -- the rail: standalone illustrated icons (13 % of the window height) with a bold outlined word under each, no box; the selected one bigger
    local short = h < 600
    local icon = math.max(R.MinTap, round(winH * 0.13))
    local labelSize = if short then R.MinText else math.clamp(round(h * 0.027), 19, 22)
    local railGap = math.max(4, round(h * 0.01))
    local longest = 0
    for _, tab in R.RailTabs do longest = math.max(longest, R.textWidth(R.RailWords[tab], labelSize)) end
    local colW = math.max(icon, longest + 6)
    local railX = winX + winW + math.max(6, round(w * 0.0125))
    if railX + colW > w - 4 then colW = math.max(icon, w - 4 - railX) end
    local slotH = icon + labelSize + 2
    local n = #R.RailTabs
    local railH = n * slotH + (n - 1) * railGap
    local railY = winY + frameInset
    if railY + railH > guiH - 4 then railY = math.max(4, guiH - 4 - railH) end
    local slots: {Rect} = {}
    for i = 1, n do table.insert(slots, {x = railX, y = railY + (i - 1) * (slotH + railGap), w = colW, h = slotH}) end
    return {
        window = {x = winX, y = winY, w = winW, h = winH}, frameInset = frameInset, headerInset = headerInset, headerH = headerH, close = close,
        titleSize = titleSize, pad = pad, cards = list, edge = edge, nameH = nameH, cardTitle = cardTitle, rarityText = rarityText, rarityH = rarityH,
        line = line, lineH = lineH, lineText = lineText, stripInset = round(cardW * C.stripInset), innerGap = gap, art = art, artTop = artTop, button = button,
        buttonInset = round(cardW * C.buttonInset), buttonText = buttonText, priceIcon = round(button * 0.72),
        rail = {x = railX, y = railY, icon = icon, selectedIcon = round(icon * 1.12), labelSize = labelSize, gap = railGap, colW = colW, slots = slots},
    }
end

return R
