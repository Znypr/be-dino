--!strict
-- BD-1296 (docs/246 slice 2): the numbers of the POTION SHOP and the DINO INDEX (Dinos page) on the shop menu kit (client KitWindow, KitCard,
-- KitButton, KitStrip, KitRail; slice 1 = BD-1287) while Config.MenusSaeFrameEnabled is on. Pure numbers, no Instances, no requires:
-- tools/verify_sae_frame.py runs it at desktop and phone sizes and tools/mock_menus_slice2.py draws the mock from the SAME rects.
-- Every % is of the whole SCREEN (ScreenGui height + the top bar inset) unless it says window or card; positions are ScreenGui px
-- (the window rect) or window px (everything inside it). No text under 19 px, tap targets >= 44 px, the X >= 48 px (docs/72, docs/246).
-- docs/246 targets at 720 p:
--   Potion Shop 58 x 67 %, top about 21.5 %: three potions per page, cards 28-32 % H with the bottle 12-14 % H on the rarity card, kid words
--   ("Grow faster!", "Lasts 7 min", never "+40 %"), the buy button 6.5 % H, "New in 3 min" as one 22 px line.
--   Dino Index 50 x 63 %: four columns x two rows of cards 14-16 % H with a 9-11 % H render (found dinos in full colour), one cyan title,
--   Dinos / Patterns / Colours on the outside rail, a selected-dino panel of about 28 % of the window width, the progress bar 5 % H.
--   Shared: header 9.5-10 % H, title 36-40 px, the X 52-58 px, padding 2.5-3 % H, cards 12-15 px apart, rail icons 7-8 % H 1 % H apart
--   starting 1-1.5 % W right of the window, item names 23-26 px, body 19-22 px, price / button word 25-28 px.
local M = {}

M.MinText, M.MinTap, M.MinClose = 19, 44, 48
M.Top = 0.215 -- the window top (21-22 % H)
M.Potion = {w = 0.58, h = 0.67, card = 0.32, bottle = 0.13, minBottle = 84, button = 0.065, restockText = 22, perPage = 3, band = 0.07}
-- bar: lead polish 2026-11-23 (ChatGPT round 1): 24-28 px at 720 p (docs/246 said 5 % H)
M.Index = {w = 0.50, h = 0.63, card = 0.16, render = 0.11, panel = 0.28, bar = 0.036, cols = 4, rows = 2}
M.PotionTitle, M.IndexTitle = "Potion Shop", "Dino Index"
M.PotionColour, M.IndexColour = "green", "cyan" -- the shop green header; the Index cyan (docs/246)
-- kid words: what a potion does (never "+40 %") and how long it lasts
M.KindWords = {speed = "Run faster!", growth = "Grow faster!", loot = "More luck!"}
-- lead polish 2026-11-23: the page button pages potions ("Next >", "< Back"), the empty strip says "No potions yet!"
M.SoldOut, M.MoreWord, M.BackWord = "Sold out", "Next >", "< Back" -- kidtext-ok: the page arrow on the button (lead polish 2026-11-23: "Next" with an arrow)
M.YoursWord, M.NoneWord = "Yours", "No potions yet!"
-- the Index rail (outside the window) and the shop rail (slice 1's tabs, Potions selected)
M.IndexRail = {"dinos", "patterns", "colours", "fusion"}
M.IndexRailWords = {dinos = "Dinos", patterns = "Patterns", colours = "Colours", fusion = "Fusion"}
M.LookWord, M.HatchWord, M.NotFoundWord = "View", "Find it!", "Not found yet!"
-- the preview boxes are bigger than their render rect (the camera leaves a margin): found dinos, the panel dino, silhouettes (each side)
M.CardZoom, M.PanelZoom, M.SilhouetteZoom = 0.30, 0.30, 0.24

local function round(x: number): number return math.floor(x + 0.5) end
-- Estimated width in px of a FredokaOne word (SaeFrameRules.textWidth: 0.56 em per character).
function M.textWidth(text: string, size: number): number return math.ceil(#text * 0.56 * size) end

-- "Lasts 5 min" from seconds (whole minutes, "Lasts 45 s" under a minute).
function M.lasts(seconds: number): string
    local s = math.max(0, math.ceil(seconds))
    return if s < 60 then "Lasts " .. s .. " s" else "Lasts " .. (s // 60) .. " min"
end
function M.kindWord(kind: string): string return M.KindWords[kind] or "Feel great!" end
-- "x3" (how many of a potion or a dino the player has)
function M.count(n: number): string return "x" .. tostring(math.max(0, math.floor(n))) end

-- The offers of one page (1-based) and how many pages there are.
function M.page(count: number, page: number, perPage: number): (number, number, number)
    local pages = math.max(1, math.ceil(count / perPage))
    page = math.clamp(page, 1, pages)
    local first = (page - 1) * perPage + 1
    return first, math.min(count, first + perPage - 1), pages
end

export type Rect = {x: number, y: number, w: number, h: number}

-- The header and the X for a window of height winH on a screen of height h (shared by both screens).
local function header(h: number, winH: number)
    local headerInset = math.max(4, round(winH * 0.019))
    local close = math.clamp(round(h * 0.078), M.MinClose, 58)
    local headerH = math.max(round(h * 0.10), close + 8)
    local titleSize = math.clamp(round(h * 0.053), 26, 40)
    return headerInset, headerH, close, titleSize
end

-- The rail right of the window: n icons 7.5 % H (44+), 1 % H apart, a 19-20 px word under each.
local function rail(w: number, guiH: number, h: number, win: Rect, words: {string})
    local icon = math.max(M.MinTap, round(h * 0.075))
    local labelSize = if h < 600 then M.MinText else 20
    local gap = math.max(4, round(h * 0.01))
    local longest = 0
    for _, word in words do longest = math.max(longest, M.textWidth(word, labelSize)) end
    local colW = math.max(icon, longest + 6)
    local x = win.x + win.w + math.max(6, round(w * 0.0125))
    if x + colW > w - 4 then colW = math.max(icon, w - 4 - x) end
    local slotH = icon + labelSize + 2
    local n = #words
    local railH = n * slotH + (n - 1) * gap
    local y = win.y + 6
    if y + railH > guiH - 4 then y = math.max(4, guiH - 4 - railH) end
    local slots: {Rect} = {}
    for i = 1, n do table.insert(slots, {x = x, y = y + (i - 1) * (slotH + gap), w = colW, h = slotH}) end
    return {x = x, y = y, icon = icon, selectedIcon = round(icon * 1.12), labelSize = labelSize, gap = gap, colW = colW, slots = slots}
end

-- The window rect: share of the screen, never smaller than `needW` x `needH`, never off screen.
local function windowRect(w: number, guiH: number, h: number, top: number, shareW: number, shareH: number, needW: number, needH: number): Rect
    local winW = math.min(math.max(round(w * shareW), needW), w - 16)
    local winH = math.min(math.max(round(h * shareH), needH), guiH - 8)
    local y = math.max(4, round(h * M.Top) - top)
    if y + winH > guiH - 4 then y = math.max(4, guiH - 4 - winH) end
    return {x = round((w - winW) / 2), y = y, w = winW, h = winH}
end

-- The Potion Shop. w, guiH: ScreenGui AbsoluteSize; inset: the top bar above the ScreenGui. Returns the KitWindow / KitCard layout plus
-- restock (the "New in 3 min" line), more (the page button) and band (the "Yours" strip with the owned potions; nil when no room).
function M.potionLayout(w: number, guiH: number, inset: number?)
    w, guiH = math.max(320, w), math.max(240, guiH)
    local top = math.max(0, inset or 0)
    local h = guiH + top
    local P = M.Potion
    local pad = math.max(6, round(h * 0.027))
    local edge = math.max(4, round(h * 0.008))
    local cardTitle = math.clamp(round(h * 0.035), 23, 26)
    local nameH = cardTitle + 2
    local rarityText = math.clamp(round(h * 0.028), M.MinText, 22)
    local rarityH = rarityText + 2
    local button = math.max(M.MinTap, round(h * P.button))
    local buttonText = math.clamp(round(h * 0.037), 24, 28)
    local lineText = math.clamp(round(h * 0.028), M.MinText, 22)
    local lineH = math.max(lineText + 8, round(h * 0.042))
    local gap = math.max(3, round(h * 0.0055))
    local artTop = edge + nameH + round(rarityH * 0.4)
    local rowH = math.max(M.MinTap, button)
    local bandH = math.max(M.MinTap + 4, round(h * P.band))
    -- a provisional header for the needed height (the real one is from the final window height)
    local hi0, hh0 = header(h, round(h * P.h))
    -- the bottle: 13 % H, at least minBottle px (a short screen: big enough to read), never more than the screen leaves (40 px floor)
    local around = hi0 + hh0 + pad + artTop + gap + lineH + gap + button + edge + pad + rowH + math.max(6, round(pad * 0.6)) + (M.MinTap + 4) + pad
    local art = math.clamp(math.max(round(h * P.bottle), P.minBottle), 40, math.max(40, guiH - 8 - around))
    local needCard = artTop + art + gap + lineH + gap + button + edge
    local cardH = math.max(round(h * P.card), needCard)
    local needH = hi0 + hh0 + pad + cardH + pad + rowH + math.max(6, round(pad * 0.6)) + (M.MinTap + 4) + pad -- room for the owned strip (the only place to drink a potion)
    local winRect = windowRect(w, guiH, h, top, P.w, P.h, 3 * 128 + 2 * 12 + 2 * 16, needH)
    local headerInset, headerH, close, titleSize = header(h, winRect.h)
    local side = math.max(8, round(winRect.w * 0.03))
    local cardGap = math.clamp(round(h * 0.019), 8, 15)
    local cardW = math.floor((winRect.w - 2 * side - 2 * cardGap) / 3)
    local cardY = headerInset + headerH + pad
    -- squeezed (a short phone): the card gives back what it can (never under what its parts need)
    local spare = winRect.h - (cardY + cardH + math.max(6, round(pad * 0.7)) + rowH + math.max(6, round(pad * 0.6)) + M.MinTap + 4 + math.max(6, round(pad * 0.8)))
    if spare < 0 then cardH = math.max(needCard, cardH + spare) end
    local cards: {Rect} = {}
    for i = 1, 3 do table.insert(cards, {x = side + (i - 1) * (cardW + cardGap), y = cardY, w = cardW, h = cardH}) end
    local rowY = cardY + cardH + math.max(6, round(pad * 0.7))
    local moreW = math.max(110, round(cardW * 0.62))
    local more = {x = winRect.w - side - moreW, y = rowY, w = moreW, h = rowH}
    local restock = {x = side + 4, y = rowY, w = more.x - side - 12, h = rowH, size = P.restockText}
    local bandY = rowY + rowH + math.max(6, round(pad * 0.6))
    local bandRoom = winRect.h - bandY - math.max(6, round(pad * 0.8))
    local band: any = nil
    if bandRoom >= M.MinTap + 4 then
        local bh = math.min(bandRoom, bandH)
        band = {x = side, y = bandY, w = winRect.w - 2 * side, h = bh, icon = math.max(M.MinTap, math.min(bh - 4, bh - 12)), text = math.clamp(round(h * 0.028), M.MinText, 22)}
    end
    local shopWords = {"Featured", "Auras", "Trails", "Eggs", "Potions"}
    return {
        window = winRect, headerInset = headerInset, headerH = headerH, close = close, titleSize = titleSize, pad = pad,
        cards = cards, edge = edge, nameH = nameH, cardTitle = cardTitle, rarityText = rarityText, rarityH = rarityH, line = true,
        lineH = lineH, lineText = lineText, stripInset = round(cardW * 0.07), innerGap = gap, art = art, artTop = artTop, button = button,
        buttonInset = round(cardW * 0.045), buttonText = buttonText, priceIcon = round(button * 0.72),
        restock = restock, more = more, band = band, rail = rail(w, guiH, h, winRect, shopWords),
    }
end

-- The Dino Index (Dinos page): the 4 x 2 card grid on the left, the selected-dino panel on the right (about 28 % of the window width), the
-- progress bar (5 % H) with the page buttons under the grid.
function M.indexLayout(w: number, guiH: number, inset: number?, railWords: {string}?)
    w, guiH = math.max(320, w), math.max(240, guiH)
    local top = math.max(0, inset or 0)
    local h = guiH + top
    local I = M.Index
    local pad = math.max(6, round(h * 0.027))
    local cardGap = math.clamp(round(h * 0.011), 5, 10)
    local cardH = math.max(M.MinTap + 30, round(h * I.card))
    local render = math.max(40, math.min(cardH - 26, round(h * I.render)))
    local countText = M.MinText + 1
    local bar = math.max(M.MinText + 5, round(h * I.bar))
    local rowH = math.max(M.MinTap, bar)
    local hi0, hh0 = header(h, round(h * I.h))
    local needH = hi0 + hh0 + pad + I.rows * cardH + (I.rows - 1) * cardGap + pad + rowH + pad
    local panelMin = 150
    local needW = I.cols * 62 + (I.cols - 1) * cardGap + panelMin + 3 * 12
    local win = windowRect(w, guiH, h, top, I.w, I.h, needW, needH)
    local headerInset, headerH, close, titleSize = header(h, win.h)
    local side = math.max(8, round(win.w * 0.025))
    local panelW = math.max(panelMin, round(win.w * I.panel))
    local gridX, gridY = side, headerInset + headerH + pad
    local gridW = win.w - 2 * side - panelW - side
    local cardW = math.floor((gridW - (I.cols - 1) * cardGap) / I.cols)
    local spare = win.h - (gridY + I.rows * cardH + (I.rows - 1) * cardGap + pad + rowH + pad)
    if spare < 0 then cardH = math.max(M.MinTap + 30, cardH + math.floor(spare / I.rows)) render = math.max(40, math.min(render, cardH - 26)) end
    if spare > 0 then gridY += math.floor(spare / 2) end -- the grid, the bar and the panel sit in the middle of the body
    local cards: {Rect} = {}
    for r = 0, I.rows - 1 do
        for c = 0, I.cols - 1 do
            table.insert(cards, {x = gridX + c * (cardW + cardGap), y = gridY + r * (cardH + cardGap), w = cardW, h = cardH})
        end
    end
    local gridBottom = gridY + I.rows * cardH + (I.rows - 1) * cardGap
    local rowY = gridBottom + math.max(8, round(pad * 0.8))
    local pageW = M.MinTap + 6
    local nxt = {x = gridX + gridW - pageW, y = rowY, w = pageW, h = rowH}
    local prev = {x = nxt.x - 6 - pageW, y = rowY, w = pageW, h = rowH}
    local barRect = {x = gridX, y = rowY + math.floor((rowH - bar) / 2), w = prev.x - 8 - gridX, h = bar, text = math.clamp(round(bar * 0.6), M.MinText, 24)}
    local panel = {x = gridX + gridW + side, y = gridY, w = panelW, h = rowY + rowH - gridY}
    -- inside the panel (panel px): the name, the rarity word, the big render, the "You have 3" strip, the Look button
    local pEdge = math.max(4, round(h * 0.008))
    local nameText = math.clamp(round(h * 0.035), 23, 26)
    local wordText = math.clamp(round(h * 0.028), M.MinText, 22)
    local pButton = math.max(M.MinTap, round(h * 0.065))
    local pLine = math.max(wordText + 8, round(h * 0.042))
    local pGap = math.max(3, round(h * 0.0055))
    local badge = wordText + 8 -- the rarity as a small badge (a kit rarity card piece) under the name
    local renderTop = pEdge + nameText + 2 + badge + 4
    local pRender = math.max(40, math.min(panelW - 16, panel.h - renderTop - pGap - pLine - pGap - pButton - pEdge))
    return {
        window = win, headerInset = headerInset, headerH = headerH, close = close, titleSize = titleSize, pad = pad, cards = cards,
        cardRender = render, countText = countText, bar = barRect, prev = prev, next = nxt, panel = panel,
        panelParts = {edge = pEdge, nameText = nameText, wordText = wordText, button = pButton, buttonText = math.clamp(round(h * 0.037), 24, 28),
            line = pLine, gap = pGap, renderTop = renderTop, render = pRender, inset = round(panelW * 0.06), badge = badge},
        rail = rail(w, guiH, h, win, railWords or {"Dinos", "Patterns", "Colours", "Fusion"}),
    }
end

return M
