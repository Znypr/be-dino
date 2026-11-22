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
-- BD-1298: the Potion Shop follows the owner's PROPOSED PICTURE (docs/evidence/2026-11-23-potion-proposal/proposal.jpg), not the docs/246
-- numbers above: window 71.5 % H at 1.40 : 1, top 16.5 %, header 13 % H, the X 11.4 % H, cards 2.5 % W apart, the bottle 50 % of the card
-- (owner 2026-11-23: one card must look like the picture's card), the name 10.8 % of the card, the buy button 12.5 %, the restock timer
-- at 63 % of the header (4.2 % H, yellow), the header stripes from 48 %.
M.Potion = {h = 0.715, aspect = 1.40, top = 0.165, header = 0.13, close = 0.114, gap = 0.025, bottle = 0.50, name = 0.108, button = 0.125, timerAt = 0.63, timerText = 0.042, stripeAt = 0.48, minShare = 0.47, perPage = 3}
-- bar: lead polish 2026-11-23 (ChatGPT round 1): 24-28 px at 720 p (docs/246 said 5 % H)
M.Index = {w = 0.50, h = 0.63, card = 0.16, render = 0.11, panel = 0.28, bar = 0.036, cols = 4, rows = 2}
M.PotionTitle, M.IndexTitle = "Potions", "Dino Index"
M.PotionColour, M.IndexColour = "green", "cyan" -- the shop green header; the Index cyan (docs/246)
-- kid words: what a potion does (never "+40 %") and how long it lasts
M.KindWords = {speed = "Run faster!", growth = "Grow faster!", loot = "More luck!"}
-- BD-1298: a Legendary potion says it is stronger, still without a number
M.SuperWords = {speed = "Run super fast!", growth = "Grow super fast!", loot = "Super lucky!"}
-- lead polish 2026-11-23: the page button pages potions ("Next >", "< Back"), the empty strip says "No potions yet!"
M.SoldOut, M.MoreWord, M.BackWord = "Sold out", "Next >", "< Back" -- kidtext-ok: the page arrow on the button (lead polish 2026-11-23: "Next" with an arrow)
M.YoursWord, M.NoneWord = "Yours", "No potions yet!"
-- BD-1298 (LEAD decision): no row under the cards. The small arrow in the header pages the shop, then the player's own potions ("My
-- Potions", a green "Drink!" button on each card), then back to the shop: drinking stays one tap away without a strip in the window.
-- LEAD decisions (owner 2026-11-23 "proposal still way better"): the card shows the picture's words only (the short name, the rarity
-- word, the "x3" count, the kid words, the price); how long a potion lasts shows on My Potions (its strip) and in the drink confirm; a
-- two-word catalog name shows its first word ("Swift Sip" -> "Swift") like the picture.
M.PageWord, M.YoursTitle, M.DrinkWord = ">", "My Potions", "Drink!" -- kidtext-ok: the page arrow
M.TimerSample = "New in 59 min" -- the longest restock words (TimerWords.restockIn), for the header room
M.TimerColour = {255, 232, 90} -- the yellow restock words in the header (the picture), dark outline as every kit word
-- the shop rail in the picture's order (Featured, Potions, Trails, Auras, Eggs)
M.PotionRail = {"featured", "potions", "trails", "auras", "eggs"}
M.PotionRailWords = {featured = "Featured", potions = "Potions", trails = "Trails", auras = "Auras", eggs = "Eggs"}
-- the Index rail (outside the window) and the shop rail (slice 1's tabs, Potions selected)
M.IndexRail = {"dinos", "patterns", "colours", "fusion"}
M.IndexRailWords = {dinos = "Dinos", patterns = "Patterns", colours = "Colours", fusion = "Fusion"}
M.LookWord, M.HatchWord, M.NotFoundWord = "View", "Find it!", "Not found yet!"
-- the preview boxes are bigger than their render rect (the camera leaves a margin): found dinos, the panel dino, silhouettes (each side)
M.CardZoom, M.PanelZoom, M.SilhouetteZoom = 0.30, 0.445, 0.305 -- lead polish round 2: the panel dino +18 %, silhouettes +9 %

local function round(x: number): number return math.floor(x + 0.5) end
-- Estimated width in px of a FredokaOne word (SaeFrameRules.textWidth: 0.56 em per character).
function M.textWidth(text: string, size: number): number return math.ceil(#text * 0.56 * size) end

-- "Lasts 5 min" from seconds (whole minutes, "Lasts 45 s" under a minute).
function M.lasts(seconds: number): string
    local s = math.max(0, math.ceil(seconds))
    return if s < 60 then "Lasts " .. s .. " s" else "Lasts " .. (s // 60) .. " min"
end
function M.kindWord(kind: string, rarity: string?): string
    if rarity == "Legendary" and M.SuperWords[kind] then return M.SuperWords[kind] end
    return M.KindWords[kind] or "Feel great!"
end
-- BD-1298: the card name, the first word of a catalog name ("Swift Sip" -> "Swift", one word stays)
function M.shortName(name: string): string return string.match(name, "^(%S+)") or name end
-- "x3" (how many: a potion in stock or owned, a dino; a count, never a multiplier)
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

-- The Potion Shop. w, guiH: ScreenGui AbsoluteSize; inset: the top bar above the ScreenGui. BD-1298 (the owner's PROPOSED PICTURE,
-- docs/evidence/2026-11-23-potion-proposal/proposal.jpg, beats the docs/246 numbers): the window 71.5 % H at about 1.40 : 1 (never
-- narrower than three 128 px cards), top 16.5 % H; the header 13 % H with the picture's title and X, the yellow restock timer INSIDE
-- the header at 63 % of its width, the small page arrow left of the X; three TALL cards (about 30 % of the window width, 72-73 % of its
-- height, 2.5 % apart), each like the picture's card: the big name, the small rarity word, the small "x3" count top right, the bottle
-- 50 % of the card centred between the rarity word and the strip, the dark kid-words strip, the price button. No row under the cards.
-- Returns the KitWindow / KitCard layout plus timer and page (window px), badge (card px), stripeAt and the rail (the picture's order).
function M.potionLayout(w: number, guiH: number, inset: number?)
    w, guiH = math.max(320, w), math.max(240, guiH)
    local top = math.max(0, inset or 0)
    local h = guiH + top
    local P = M.Potion
    local close = math.max(round(M.MinClose * 1.15), round(h * P.close)) -- the picture's X: 82 px at 720 p, 55+ on short screens
    local headerH = math.max(round(h * P.header), close + 10)
    local titleSize = math.max(30, round(h * 0.064)) -- 46 px at 720 p (the picture), 30+ on short screens
    -- the card parts at a card height cH; small = every part at its floor (19 px text, 44 px button) for a short phone
    -- owner 2026-11-23: the bottle takes the room: the rarity word 55 % of the name (19 px floor), no other line on the card
    local function parts(cH: number, small: boolean)
        local edge = math.max(4, round(cH * 0.025))
        local cardTitle = math.clamp(round(cH * P.name), 23, 64) -- the big name keeps its share even on a short screen (the picture)
        local rarityText = math.clamp(round(cardTitle * 0.55), M.MinText, 32)
        local lineText = if small then M.MinText else math.clamp(round(cH * 0.06), M.MinText, 34)
        local lineH = if small then lineText + 8 else math.max(lineText + 8, round(cH * 0.10))
        local button = if small then M.MinTap else math.max(M.MinTap, round(cH * P.button))
        local gap = math.max(3, round(cH * 0.014))
        local nameH, rarityH = cardTitle + 4, rarityText + 2
        local artTop = edge + nameH + rarityH
        return {edge = edge, cardTitle = cardTitle, nameH = nameH, rarityText = rarityText, rarityH = rarityH, lineText = lineText,
            lineH = lineH, button = button, innerGap = gap, artTop = artTop, fixed = artTop + 2 + lineH + gap + button + edge}
    end
    -- the header words: the title, the restock timer, the page arrow and the X side by side
    local pageS = math.max(M.MinTap, round(close * 0.6)) -- small: the picture has no arrow
    local timerSize = math.max(M.MinText, round(h * P.timerText))
    local timerW = M.textWidth(M.TimerSample, timerSize) + 8
    local headerNeed = math.floor(headerH * 0.2) + M.textWidth(M.YoursTitle, titleSize) + 6 + timerW + 6 + pageS + math.max(6, round(close * 0.15))
        + close + math.floor((headerH - close) / 2) + 2 * math.max(4, round(h * P.h * 0.019)) + 4
    -- the window: 71.5 % H at 1.40 : 1 (never narrower than three 128 px cards or its header words); on a short screen it grows (2 px
    -- steps, at most 90 % H, never off screen) until the bottle has minShare of the card, because the 19 px text and 44 px button floors
    -- take a bigger share of a small card
    local winH, winW, headerInset, padTop, cardGap, cardW, side, cardY, cardH, art = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    local c = parts(0, true)
    local function size(hh: number)
        winH = hh
        winW = math.min(math.max(round(winH * P.aspect), 3 * 128 + 2 * 8 + 2 * 10, headerNeed), w - 16)
        headerInset = math.max(4, round(winH * 0.019))
        padTop = math.max(6, round(winH * 0.035))
        cardGap = math.max(6, round(winW * P.gap))
        cardW = math.floor((winW - 2 * math.max(8, round(winW * 0.029)) - 2 * cardGap) / 3)
        side = math.floor((winW - 3 * cardW - 2 * cardGap) / 2) -- the rounding left over goes to both sides (the row stays centred)
        cardY = headerInset + headerH + padTop
        cardH = math.max(0, winH - cardY - math.max(6, round(winH * 0.045)))
        c = parts(cardH, false)
        if c.fixed + round(cardH * P.minShare) > cardH then c = parts(cardH, true) end
        art = math.max(0, math.min(round(cardH * P.bottle), cardW - 8, cardH - c.fixed))
    end
    size(math.min(round(h * P.h), guiH - 8))
    while art < math.min(round(cardH * P.minShare), cardW - 8) and winH + 2 <= math.min(guiH - 8, round(h * 0.9)) do size(winH + 2) end
    local y = math.max(4, round(h * P.top) - top)
    if y + winH > guiH - 4 then y = math.max(4, guiH - 4 - winH) end
    local winRect = {x = round((w - winW) / 2), y = y, w = winW, h = winH}
    local cards: {Rect} = {}
    for i = 1, 3 do table.insert(cards, {x = side + (i - 1) * (cardW + cardGap), y = cardY, w = cardW, h = cardH}) end
    -- card px: the small "x3" count in the top-right corner just under the rarity word, where the picture has it (the bottle's top is
    -- its narrow neck, so the corner stays clear)
    local badgeText = math.clamp(round(cardH * 0.053), M.MinText, 30)
    local badgeW = M.textWidth("x3", badgeText) + 8
    local badge = {x = cardW - c.edge - 4 - badgeW, y = c.artTop, w = badgeW, h = badgeText + 2, size = badgeText}
    -- window px: the X (where KitWindow draws it), the page arrow left of it, the timer centred at 63 % of the header width
    local headerW = winW - 2 * headerInset
    local closeX = headerInset + headerW - math.floor((headerH - close) / 2) - close
    local page = {x = closeX - math.max(6, round(close * 0.15)) - pageS, y = headerInset + math.floor((headerH - pageS) / 2), w = pageS, h = pageS,
        text = math.clamp(round(pageS * 0.6), 24, 34)}
    local titleEnd = headerInset + math.floor(headerH * 0.2) + M.textWidth(M.YoursTitle, titleSize) -- the longer title (the owned page)
    local timerX = math.clamp(round(headerInset + headerW * P.timerAt - timerW / 2), titleEnd + 6, math.max(titleEnd + 6, page.x - 6 - timerW))
    local timer = {x = timerX, y = headerInset - math.floor(headerH * 0.04), w = timerW, h = headerH, size = timerSize}
    local railWords = {}
    for _, tab in M.PotionRail do table.insert(railWords, M.PotionRailWords[tab]) end
    return {
        window = winRect, headerInset = headerInset, headerH = headerH, close = close, titleSize = titleSize, pad = padTop,
        cards = cards, edge = c.edge, nameH = c.nameH, cardTitle = c.cardTitle, rarityText = c.rarityText, rarityH = c.rarityH, line = true,
        lineH = c.lineH, lineText = c.lineText, stripInset = round(cardW * 0.055), innerGap = c.innerGap, art = art, artTop = c.artTop,
        button = c.button, buttonInset = round(cardW * 0.04),
        buttonText = math.clamp(round(c.button * 0.62), 24, 44), priceIcon = round(c.button * 0.72),
        badge = badge, timer = timer, page = page, stripeAt = P.stripeAt, rail = rail(w, guiH, h, winRect, railWords),
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
    local barRect = {x = gridX, y = rowY + math.floor((rowH - bar) / 2), w = prev.x - 8 - gridX, h = bar, text = math.clamp(round(bar * 0.6), M.MinText, 24), minFill = math.max(8, round(h * 0.015))}
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
