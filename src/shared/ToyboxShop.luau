--!strict
-- BD-1178 (docs/228 board 3, docs/231): the Crystal Shop in the "Toybox" look, as plain rules. No engine call, no clock, no RNG:
-- tools/verify_toybox_shop.py runs this file with the pinned Luau runtime. src/client/ShopToyboxCard.luau draws what this returns.
-- Words are for children (docs/72): short, obvious, no numbers like "1.25x". Nothing here touches prices, saves or the server.
local S = {}

S.Rarities = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}

-- The card picture (one of the six toybox_card_* slots) of a rarity word. An unknown or missing rarity is Common, like RarityWord.get.
function S.cardSlot(rarity: any): string
    if type(rarity) == "string" then
        local lower = string.lower(rarity)
        for _, name in S.Rarities do
            if string.lower(name) == lower then return "toybox_card_" .. lower end
        end
    end
    return "toybox_card_common"
end

-- A locked Legendary (or Mythic) card keeps its secret: a "?" instead of the picture and one short hint. Only a LOCKED card does this.
function S.mystery(rarity: any, tone: any): boolean
    return tone == "locked" and (rarity == "Legendary" or rarity == "Mythic")
end
S.MysteryMark = "?"
S.MysteryName = "???"
S.LockedWord = "LOCKED"

-- The hint under the "?": what the item asks for, in words the game already knows (a trail needs an account level).
function S.hint(item: {level: number?}): string
    local level = item.level or 1
    if level > 1 then return "Reach level " .. level end
    return "Keep playing to find it"
end

-- The one wide button: which colour it wears. Green for buy and equip, the card grey for unequip, flat grey for locked and sold out
-- (the skin turns each of them into the nearest gloss button).
function S.buttonColour(tone: string): string
    if tone == "buy" or tone == "equip" then return "accent" end
    if tone == "unequip" then return "card" end
    return "soldOut"
end

-- The slow rays behind the art: the existing shaftGradient texture (EffectAssets, owner upload), three copies fanned out and turned very
-- slowly. No texture bound = no rays (the cream box stays plain); nothing is drawn in code. Reduce Motion keeps them still.
S.RaysKey = "shaftGradient"
S.RayAngles = {-35, 0, 35}
S.RaySeconds = 40 -- one full turn
S.RayTransparency = 0.55
function S.raySeconds(reduceMotion: boolean): number
    return if reduceMotion then 0 else S.RaySeconds
end

-- The soft gold glow of the equipped card: the existing glowPlate texture behind the card, plus the gold ring the old card already has.
S.GlowKey = "glowPlate"

-- The "Buy X?" popup: the name in the title and "Not now" instead of Cancel. The page keeps its price and balance lines.
function S.confirm(name: string, isTrail: boolean): {title: string, buy: string, cancel: string}
    return {
        title = "Buy " .. name .. "?",
        buy = if isTrail then "BUY TRAIL" else "BUY AURA",
        cancel = "NOT NOW",
    }
end

-- BD-1178 (owner target 2026-11-14, docs/231 s2, docs/232): the card parts and the page grid, in design px of the shop body.
-- A card: name row, the rarity word on a cream pill, a cream art box, a cream benefit band and ONE wide button at the foot. The grid fills the WHOLE
-- body width (4 equal columns when a cell is at least MinCell px on screen, else 3), 12 px gaps, a 4 px pad (room for the gold ring) and the 8 px
-- scroll-bar strip on the right; rows below the first one scroll inside the grid (the grid itself never leaves the body).
S.Page = {tabH = 44, gutter = 12, pad = 4, scrollBar = 8, minCell = 170, minColumns = 3, maxColumns = 4, minArt = 64,
    insetX = 16, insetTop = 10, insetBottom = 22, gapY = 6, hintH = 28}

-- The heights of the text rows of a card for a window drawn at `scale` (a 14 px word on screen is more design px when the body is shrunk to fit).
function S.parts(scale: number): {textPx: number, nameH: number, pillH: number, bandH: number}
    local k = math.max(if scale == scale then scale else 1, 0.1)
    local textPx = math.max(18, math.ceil(14 / k))
    return {textPx = textPx, nameH = math.max(30, textPx + 10), pillH = textPx + 8, bandH = math.max(28, math.ceil(14 / k) + 10)}
end

-- Where the card parts go inside a card `width` x `height` (design px). `buttonH` = the action button's height. All rects are x, y, w, h.
function S.layout(width: number, height: number, buttonH: number, scale: number)
    local P, parts = S.Page, S.parts(scale)
    local innerW = width - 2 * P.insetX
    local buyY = height - P.insetBottom - buttonH
    local bandY = buyY - P.gapY - parts.bandH
    local nameY = P.insetTop
    local pillY = nameY + parts.nameH + 2
    local artY = pillY + parts.pillH + P.gapY
    local artH = math.max(bandY - P.gapY - artY, 0)
    return {
        parts = parts,
        name = {x = P.insetX, y = nameY, w = innerW, h = parts.nameH},
        pill = {x = P.insetX, y = pillY, h = parts.pillH},
        art = {x = P.insetX, y = artY, w = innerW, h = artH},
        band = {x = P.insetX, y = bandY, w = innerW, h = parts.bandH},
        button = {x = P.insetX, y = buyY, w = innerW, h = buttonH},
    }
end

-- The least height a card needs: the picture keeps room for MinArt px of art.
function S.cardMin(buttonH: number, scale: number): number
    local P, parts = S.Page, S.parts(scale)
    return P.insetTop + parts.nameH + 2 + parts.pillH + P.gapY + P.minArt + P.gapY + parts.bandH + P.gapY + buttonH + P.insetBottom
end

-- 4 columns when each cell is at least MinCell px on screen (scale = what the body really renders at), else 3.
function S.columns(bodyW: number, scale: number): number
    local P = S.Page
    local k = math.max(if scale == scale then scale else 1, 0.1)
    local content = bodyW - P.scrollBar - 2 * P.pad
    for columns = P.maxColumns, P.minColumns + 1, -1 do
        local cell = (content - P.gutter * (columns - 1)) / columns
        if cell * k >= P.minCell then return columns end
    end
    return P.minColumns
end

-- The grid of `count` cards in a view `bodyW` x `viewH`: equal cells that fill the width, each as tall as the view (or the least a card needs),
-- the rows below the first scroll. cells[i] = {x, y, w, h}; canvasH = the scroll height.
function S.grid(bodyW: number, viewH: number, scale: number, count: number, buttonH: number)
    local P = S.Page
    local columns = math.max(math.min(S.columns(bodyW, scale), count), 1) -- fewer cards than columns (the 3 Auras): the cards share the whole width
    local content = bodyW - P.scrollBar - 2 * P.pad
    local cellW = math.floor((content - P.gutter * (columns - 1)) / columns)
    local used = cellW * columns + P.gutter * (columns - 1)
    local x0 = P.pad + math.floor((content - used) / 2)
    local cellH = math.max(S.cardMin(buttonH, scale), viewH - 2 * P.pad)
    local cells = {}
    for i = 1, count do
        local col, row = (i - 1) % columns, (i - 1) // columns
        cells[i] = {x = x0 + col * (cellW + P.gutter), y = P.pad + row * (cellH + P.gutter), w = cellW, h = cellH}
    end
    local rows = math.ceil(count / columns)
    local canvasH = P.pad * 2 + rows * cellH + math.max(rows - 1, 0) * P.gutter
    return {columns = columns, cellW = cellW, cellH = cellH, cells = cells, canvasH = canvasH, scrolls = canvasH > viewH + 0.5}
end

-- The tab chips: a chip is as wide as its word at 18 px, never under 84. "Auras", "Trails", "Eggs", "Conditions", "Crystals".
function S.tabTitle(tab: string): string
    return string.upper(string.sub(tab, 1, 1)) .. string.sub(tab, 2)
end
function S.chipWidth(text: string, textScale: number?): number
    local f = math.max(textScale or 1, 1)
    return math.max(84, math.ceil(#text * 10.5 * f) + 32)
end
-- The width a screen can fill: a compact window draws the body 4 px in from the scroller edge and keeps 8 px for its scroll bar (PhoneScale.BodyW = 4 + 824 + 8).
function S.usableWidth(bodyWidth: number, compact: boolean): number
    return if compact then bodyWidth - 12 else bodyWidth
end
-- "Styling: Compy": the dino the cards are for.
function S.styling(name: any): string
    local text = if type(name) == "string" and name ~= "" then name else "your dino"
    if #text > 18 then text = string.sub(text, 1, 17) .. "." end
    return "Styling: " .. text
end

-- A wallet number with thousands commas: 12450 -> "12,450".
function S.walletText(amount: any): string
    local n = if type(amount) == "number" and amount == amount then math.max(math.floor(amount), 0) else 0
    local text = tostring(n)
    while true do
        local changed
        text, changed = string.gsub(text, "^(%d+)(%d%d%d)", "%1,%2")
        if changed == 0 then break end
    end
    return text
end

return S
