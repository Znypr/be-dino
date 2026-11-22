--!strict
-- BD-1287 (docs/246 slice 1, owner 2026-11-21 "competitive with current famous roblox experiences"): the compact Steal-an-Egg window and the
-- tab rail outside it, for the Crystal Shop landing while Config.MenusSaeFrameEnabled is on. Pure numbers, no Instances: client/ShopSaeLanding
-- draws what layout() returns, tools/verify_sae_frame.py runs it at desktop and phone sizes.
-- Every size is in SCREEN px (the window has no UIScale), measured from the ScreenGui AbsoluteSize. Targets at 720 p (docs/246 shared frame):
-- window 58 % W x 67 % H, centred, top 21.5 % H; header 9.5-10 % H; red X 52-58 px; rail 1.25 % W right of the window, tiles 7.5 % H, 1 % H apart;
-- three cards across; OPEN 46-52 px with a 25-28 px word; crystal pill about 5 % H. No text under 19 px (docs/72 phone floor).
local R = {}

R.Header = {89, 233, 71} -- #59E947 shop green
R.HeaderStripe = {160, 255, 133} -- #A0FF85
R.Close = {244, 71, 80} -- #F44750
R.Body = {45, 49, 68} -- #2D3144
R.Open = {102, 245, 47} -- #66F52F
R.OpenEdge = {58, 170, 22} -- the darker lower edge of the OPEN button
R.Outline = {0, 0, 0}
R.PillFill = {28, 31, 44}
-- the category colours (the same as ShopTiles.TopLookFill, docs/243 G4)
R.Fill = {eggs = {255, 200, 64}, auras = {255, 122, 107}, trails = {96, 196, 255}, conditions = {186, 128, 255}, crystals = {255, 176, 72},
    potions = {207, 108, 250}} -- potions: the phone HUD's POTIONS purple (#CF6CFA)
R.Cover = 0.94 -- ModalScrim transparency while the window shows: 6 % dim, the world stays visible (docs/246: 0-8 % behind shops)
R.Blur = 0 -- no modal blur behind it
R.MinText = 19
R.MinTap = 44
R.MinClose = 48
R.MaxCards = 3
R.ArtShare = 0.42 -- the card picture's share of the card height
R.RailInk = {16, 16, 12} -- #10100C, the phone HUD's near-black outline
-- the rail tiles' toy-button gradient (like PhoneHud): highlight on top, the colour, a darker bottom with a thin lip
function R.gloss(fill: {number}): {{number}}
    local function mix(t: {number}, to: number, k: number): {number}
        return {math.floor(t[1] + (to - t[1]) * k + 0.5), math.floor(t[2] + (to - t[2]) * k + 0.5), math.floor(t[3] + (to - t[3]) * k + 0.5)}
    end
    local bottom = mix(fill, 0, 0.18)
    return {mix(fill, 255, 0.4), fill, bottom, mix(bottom, 0, 0.4)}
end
R.Title = "Shop"

local function round(x: number): number return math.floor(x + 0.5) end

-- Estimated width in px of a FredokaOne word at this size (0.56 em per character, a little wider than the real average).
function R.textWidth(text: string, size: number): number
    return math.ceil(#text * 0.56 * size)
end

-- 1250 -> "1,250" (kid words: a whole number, never "1.25k").
function R.grouped(n: number): string
    local s = tostring(math.max(0, math.floor(n)))
    local out = s
    while true do
        local nxt, k = string.gsub(out, "^(%d+)(%d%d%d)", "%1,%2")
        out = nxt
        if k == 0 then break end
    end
    return out
end

export type Rect = {x: number, y: number, w: number, h: number}
export type Layout = {
    window: Rect, headerH: number, close: number, closeText: number, titleSize: number, stroke: number, corner: number,
    pill: Rect, pillText: number, pillIcon: number,
    pad: number, cardGap: number, cards: {Rect}, art: number, cardTitle: number, sub: boolean, subText: number,
    button: number, buttonText: number,
    rail: {x: number, y: number, stroke: number, tile: number, gap: number, colW: number, labels: boolean, labelSize: number, slots: {Rect}},
}

-- w, h: ScreenGui AbsoluteSize. labels: the rail words (one per tab). cards: how many cards the window shows (1..3).
function R.layout(w: number, h: number, labels: {string}, cards: number): Layout
    w, h = math.max(320, w), math.max(240, h)
    local nCards = math.clamp(cards, 1, R.MaxCards)
    local close = math.clamp(round(h * 0.078), R.MinClose, 58)
    local headerH = math.max(round(h * 0.097), close + 6)
    local titleSize = math.clamp(round(h * 0.053), 26, 40)
    local pad = math.max(10, round(h * 0.028))
    local cardGap = math.clamp(round(w * 0.011), 10, 15)
    local cardTitle = math.clamp(round(h * 0.034), 23, 26)
    local subText = if h >= 600 then 20 else R.MinText
    local button = math.clamp(round(h * 0.068), 46, 52)
    local buttonText = math.clamp(round(h * 0.037), 25, 28)
    -- the fixed part of a card under its picture: title, one short line, the OPEN button, the gaps
    local fixedSub = 10 + (cardTitle + 6) + (subText + 6) + 8 + button + 10
    local minArt = math.max(44, round(h * 0.11))
    local winW = math.max(round(w * 0.58), nCards * 128 + (nCards - 1) * cardGap + 2 * pad)
    winW = math.min(winW, w - 16)
    local winH = math.max(round(h * 0.67), headerH + 2 * pad + fixedSub + minArt)
    winH = math.min(winH, h - 8)
    local winX = round((w - winW) / 2)
    local winY = round(h * 0.215)
    if winY + winH > h - 4 then winY = math.max(4, round((h - winH) / 2)) end
    -- cards fill the body; the picture is about 42 % of the card height (lead 2026-11-21: "40-45 % of the card", at least 14 % H), never
    -- wider than the card. The short line under the title drops first when the picture would not fit with it.
    local bodyH = winH - headerH - 2 * pad
    local cardW = math.floor((winW - 2 * pad - (nCards - 1) * cardGap) / nCards)
    local want = math.min(math.max(round(bodyH * R.ArtShare), round(h * 0.14)), cardW - 24)
    local sub = bodyH - fixedSub >= want
    local fixed = if sub then fixedSub else fixedSub - (subText + 6)
    local art = math.max(0, math.min(want, bodyH - fixed))
    local list: {Rect} = {}
    for i = 1, nCards do
        table.insert(list, {x = pad + (i - 1) * (cardW + cardGap), y = headerH + pad, w = cardW, h = bodyH})
    end
    -- the crystal pill sits in the header, left of the X
    local pillH = math.max(32, round(h * 0.05))
    local pillText = math.max(R.MinText, round(pillH * 0.6))
    local pillIcon = pillH - 6
    -- the rail: right of the window, from its top; a word under each tile only where it fits
    -- toy-button tiles like the phone HUD: near-black outline 0.85 % H (6 px at 720 p, at least 3) drawn OUTSIDE the tile, so the clear gap
    -- between two tiles is 1 % H plus both outlines
    local railStroke = math.max(3, round(h * 0.0085))
    local gap = math.max(4, round(h * 0.01)) + 2 * railStroke
    local tile = math.max(R.MinTap, round(h * 0.075))
    local railX = winX + winW + 3 + math.max(6, round(w * 0.0125)) + railStroke
    local room = w - 6 - railX
    local labelSize = if h >= 600 then 20 else R.MinText
    local longest = 0
    for _, word in labels do longest = math.max(longest, R.textWidth(word, labelSize)) end
    local n = #labels
    local withLabels = n * (tile + labelSize + 4) + (n - 1) * gap
    local labelsFit = n > 0 and longest + 4 <= room and withLabels <= winH
    if not labelsFit and n > 0 then
        local plain = n * tile + (n - 1) * gap
        if plain > winH then tile = math.max(R.MinTap, math.floor((winH - (n - 1) * gap) / n)) end
    end
    local colW = if labelsFit then math.max(tile, longest + 4) else tile
    colW = math.min(colW, math.max(tile, room))
    local slots: {Rect} = {}
    local slotH0 = tile + (if labelsFit then labelSize + 4 else 0)
    local railH = n * slotH0 + math.max(0, n - 1) * gap
    local railY = winY
    if railY + railH > h - 4 - railStroke then railY = math.max(4 + railStroke, h - 4 - railStroke - railH) end -- a short screen: the rail moves up, never off screen
    local y = railY
    for _ = 1, n do
        local slotH = tile + (if labelsFit then labelSize + 4 else 0)
        table.insert(slots, {x = railX, y = y, w = colW, h = slotH})
        y += slotH + gap
    end
    return {
        window = {x = winX, y = winY, w = winW, h = winH}, headerH = headerH, close = close, closeText = math.max(28, round(close * 0.6)),
        titleSize = titleSize, stroke = 3, corner = 7,
        -- pill.x is its RIGHT edge (its width follows the number: R.pillWidth)
        pill = {x = winW - close - round((headerH - close) / 2) - 12, y = round((headerH - pillH) / 2), w = 0, h = pillH},
        pillText = pillText, pillIcon = pillIcon,
        pad = pad, cardGap = cardGap, cards = list, art = art, cardTitle = cardTitle, sub = sub, subText = subText,
        button = button, buttonText = buttonText,
        rail = {x = railX, y = railY, stroke = railStroke, tile = tile, gap = gap, colW = colW, labels = labelsFit, labelSize = labelSize, slots = slots},
    }
end

-- The crystal pill's width for this number text: icon, gap, the number, the rounded ends.
function R.pillWidth(text: string, lay: Layout): number
    return lay.pillIcon + 8 + R.textWidth(text, lay.pillText) + 14
end

-- The tabs whose cards the window shows: the first three visible ones (Auras, Trails, Eggs); every tab stays on the rail.
function R.cardTabs(tabs: {string}): {string}
    local out = {}
    for i = 1, math.min(#tabs, R.MaxCards) do table.insert(out, tabs[i]) end
    return out
end

return R
