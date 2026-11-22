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
-- BD-1298: the Potion Shop is built from the element spec of the owner's PROPOSED PICTURE (docs/menu-specs/potion-shop/spec.json, the
-- same numbers: boxes [x, y, w, h] in % of the window, card parts in % of the card; caps = letter heights in % of the window height
-- measured on the picture; capShare = FredokaOne letter height / text size). tools/verify_sae_frame.py checks the two agree.
M.PotionSpec = {
    window = {h = 0.717, aspect = 724 / 516, top = 0.161},
    header = {2.0, 2.0, 96.0, 18.0}, title = {4.1, 6.8, 24.9, 9.4}, timer = {55.6, 9.2, 20.7, 4.9}, close = {86.0, 2.9, 11.5, 16.6},
    cards = {x = {3.1, 35.2, 67.4}, y = 23.5, w = {29.7, 29.6, 29.5}, h = 72.4},
    card = {name = {15.0, 3.0, 70.0, 9.4}, rarity = {25.0, 13.0, 50.0, 5.0}, badge = {84.0, 21.0, 13.0, 5.4}, art = {24.0, 27.0, 52.0, 38.0},
        strip = {6.0, 72.5, 87.5, 10.7}, price = {3.5, 85.0, 92.5, 13.0}},
    rail = {x = 102.7, y = 1.5, w = 11.4, h = 16.5, pitch = 17.5},
    titleCap = 7.56, timerCap = 4.46, nameCap = 5.81, rarityCap = 2.91, badgeCap = 2.91, stripCap = 3.4, capShare = 0.7, stripeAt = 0.48,
}
M.Potion = {perPage = 3}
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
M.TimerSample = "New in 2 min" -- the restock words at their longest (TimerWords.restockIn, a 2 min shop window), for the header room
M.TimerColour = {255, 224, 74} -- the yellow restock words in the header (the picture), dark outline as every kit word
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

-- The Potion Shop. w, guiH: ScreenGui AbsoluteSize; inset: the top bar above the ScreenGui. BD-1298: every rect comes from the
-- element spec of the owner's PROPOSED PICTURE (M.PotionSpec = docs/menu-specs/potion-shop/spec.json; boxes in % of the window, card
-- parts in % of the card; tools/menu_spec_check.py compares the Studio build element by element). The window is 71.7 % H at the
-- picture's 1.403 : 1; on a short screen it grows (at most 90 % H) so the buy button keeps 44 px, and the floors (19 px text, 44 px
-- buttons, 48 px X) win over the picture where they meet. Returns the KitWindow layout (window, headerInset, headerH, close, titleSize,
-- stripeAt, cards = the card rects) plus, in window px: title, timer, page (the small arrow left of the X) and rail (one slot per tab);
-- in card px: parts = {name, rarity, badge, art, strip, price} (each {x, y, w, h, size?}).
function M.potionLayout(w: number, guiH: number, inset: number?)
    w, guiH = math.max(320, w), math.max(240, guiH)
    local top = math.max(0, inset or 0)
    local h = guiH + top
    local S = M.PotionSpec
    local C = S.card
    -- the window: the buy button (13 % of a 72.4 % card) needs 44 px
    local needH = math.ceil(M.MinTap / (C.price[4] / 100 * S.cards.h / 100))
    local winH = math.min(math.max(round(h * S.window.h), needH), guiH - 8, round(h * 0.9))
    local winW = math.min(round(winH * S.window.aspect), w - 16)
    -- a narrow screen: the window (centred) leaves room for the rail on its right; it keeps the picture's shape
    local maxW = math.floor((w / 2 - 4) / ((S.rail.x + S.rail.w) / 100 - 0.5))
    if winW > maxW then winW = maxW winH = math.min(winH, round(winW / S.window.aspect)) end
    local y = math.max(4, round(h * S.window.top) - top)
    if y + winH > guiH - 4 then y = math.max(4, guiH - 4 - winH) end
    local win = {x = round((w - winW) / 2), y = y, w = winW, h = winH}
    local function rect(b: {number}, fw: number, fh: number): Rect
        return {x = round(b[1] / 100 * fw), y = round(b[2] / 100 * fh), w = round(b[3] / 100 * fw), h = round(b[4] / 100 * fh)}
    end
    local function text(capPct: number, fh: number): number return math.max(M.MinText, round(capPct / 100 * fh / S.capShare)) end
    -- the header: KitWindow draws the strip at headerInset with headerH and the X centred in its height at its right end
    local header = rect(S.header, winW, winH)
    local close = math.max(M.MinClose, round(S.close[4] / 100 * winH))
    local headerH = math.max(header.h, close + 4)
    local headerInset = header.y
    local title = rect(S.title, winW, winH)
    local titleSize = text(S.titleCap, winH)
    local timer = rect(S.timer, winW, winH)
    -- the page arrow is not in the picture: as small as a tap allows, right after the title (each page's own title), so the timer keeps
    -- the picture's place and size between it and the X; its words get smaller (19 px floor) only when that room is short
    local closeX = winW - headerInset - math.floor((headerH - close) / 2) - close
    local spec = rect(S.timer, winW, winH)
    local function row(titleWord: string)
        local page = {x = title.x + M.textWidth(titleWord, titleSize) + 6, y = headerInset + math.floor((headerH - M.MinTap) / 2), w = M.MinTap, h = M.MinTap, text = 26}
        local left, right = page.x + page.w + 6, closeX - 6
        local size = math.max(M.MinText, math.min(text(S.timerCap, winH), math.floor((right - left) / (#M.TimerSample * 0.5))))
        local half = math.ceil(#M.TimerSample * 0.5 * size / 2)
        local centre = math.max(left + half, math.min(right - half, spec.x + spec.w / 2))
        return page, {x = round(centre - spec.w / 2), y = spec.y, w = spec.w, h = math.max(spec.h, math.ceil(size * 0.8)), size = size}
    end
    local page, timer = row(M.PotionTitle)
    local pageMine, timerMine = row(M.YoursTitle)
    -- the cards and their parts
    local cards: {Rect} = {}
    for i = 1, 3 do table.insert(cards, rect({S.cards.x[i], S.cards.y, S.cards.w[i], S.cards.h}, winW, winH)) end
    local cw, ch = cards[1].w, cards[1].h
    local name, rarity, badge = rect(C.name, cw, ch), rect(C.rarity, cw, ch), rect(C.badge, cw, ch)
    local art, strip, price = rect(C.art, cw, ch), rect(C.strip, cw, ch), rect(C.price, cw, ch)
    name.size, rarity.size, badge.size = text(S.nameCap, winH), text(S.rarityCap, winH), text(S.badgeCap, winH)
    -- the labels keep the picture's boxes (the letters, about 0.7 of the text size, fit them; a right-aligned count may run left)
    name.h, rarity.h, badge.h = math.max(name.h, math.ceil(name.size * 0.8)), math.max(rarity.h, math.ceil(rarity.size * 0.8)), math.max(badge.h, math.ceil(badge.size * 0.8))
    -- floors: the buy button 44 px (kept on the card's bottom), the strip over it, the bottle between the rarity word and the strip
    local priceBottom = price.y + price.h
    price.h = math.max(M.MinTap, price.h)
    price.y = math.min(price.y, priceBottom - price.h)
    strip.size = text(S.stripCap, winH)
    strip.h = math.max(strip.h, strip.size + 8)
    strip.y = math.min(strip.y, price.y - math.max(2, round(ch * 0.018)) - strip.h)
    art.h = math.max(0, math.min(art.h, strip.y - 4 - art.y))
    price.size = math.max(24, round(price.h * 0.6))
    -- the rail outside the window: one slot per tab (an icon with its word under it)
    local railSlots = {}
    for i, tab in M.PotionRail do
        local r = rect({S.rail.x, S.rail.y + (i - 1) * S.rail.pitch, S.rail.w, S.rail.h}, winW, winH)
        local label = math.max(M.MinText, round(r.h * 0.24))
        railSlots[tab] = {x = r.x, y = r.y, w = r.w, h = math.max(r.h, M.MinTap + label + 2), icon = math.max(M.MinTap, r.h - label - 2), label = label}
    end
    return {
        window = win, headerInset = headerInset, headerH = headerH, close = close, titleSize = titleSize, stripeAt = S.stripeAt,
        cards = cards, title = title, timer = timer, page = page, timerMine = timerMine, pageMine = pageMine,
        parts = {name = name, rarity = rarity, badge = badge, art = art, strip = strip, price = price}, rail = railSlots,
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

-- BD-1299 (owner 2026-11-23 "Rebuild both now", target docs/evidence/2026-11-23-index-proposal/proposal.jpg; Config.IndexZonesEnabled): the
-- Dino Index split into zones, measured from the picture (window 522 x 273 on a 920 x 431 screen): the window 63 % H, about 1.91 x as wide as
-- high; inside it the illustrated zone panel 17 % of the window width on the left, the 4 x 2 card grid 54 %, the right column 23 % (the
-- selected dino on a charcoal panel, under it the rewards box), the zone bar ("4/8") under the grid, the blue "Found" footer under the zone
-- panel and the grid; the zone buttons stacked OUTSIDE the window on the right (20 % H wide, 6.8 % H high), the Patterns / Colours / Fusion
-- icons in a column right of them. The title 15-20 % bigger than the other kit windows.
M.IndexZones = {h = 0.63, hShort = 0.74, aspect = 1.91, left = 0.169, right = 0.23, button = 0.068, buttonW = 0.20, footer = 0.11, bar = 0.075}
M.ZoneRailWords = {patterns = "Patterns", colours = "Colours", fusion = "Fusion"}
M.SecretMark = "???"

function M.indexZonesLayout(w: number, guiH: number, inset: number?, icons: number?)
    w, guiH = math.max(320, w), math.max(240, guiH)
    local top = math.max(0, inset or 0)
    local h = guiH + top
    local Z = M.IndexZones
    -- the rail first: it decides how wide the window may be
    local zoneW = math.max(110, round(h * Z.buttonW))
    local zoneH = math.max(M.MinTap, round(h * Z.button))
    local zoneGap = math.max(6, round(h * 0.0186))
    local zoneText = math.clamp(round(h * 0.034), M.MinText + 1, 26)
    local nIcons = icons or 3
    local icon = math.max(M.MinTap, round(h * 0.068))
    local narrow = w < 760 -- a small phone: the icons without their words (the cards keep 44+ px)
    local iconText = if narrow then 0 else M.MinText
    local iconColW = if nIcons > 0 then (if narrow then icon else math.max(icon, M.textWidth("Patterns", iconText) + 4)) else 0
    local railGap = math.max(6, round(w * 0.006))
    local railW = zoneW + (if nIcons > 0 then railGap + iconColW else 0)
    -- a short screen (a phone held sideways) gets a taller window share so the selected dino is still big enough to read
    local winH = math.min(math.max(round(h * (if h < 600 then Z.hShort else Z.h)), 300), guiH - 8)
    local winW = math.min(round(winH * Z.aspect), w - 16 - railGap - railW)
    winW = math.max(winW, 420)
    local groupW = winW + railGap + railW
    local x = math.max(8, round((w - groupW) / 2))
    local y = math.max(4, round(h * M.Top) - top - round(h * 0.01))
    if y + winH > guiH - 4 then y = math.max(4, guiH - 4 - winH) end
    local win = {x = x, y = y, w = winW, h = winH}
    local headerInset, headerH, close = header(h, winH)
    local titleSize = math.clamp(round(h * 0.063), 30, 46) -- the picture's title: about 18 % bigger than the kit windows' 0.053 H
    local side = math.max(6, round(winW * 0.019))
    local colGap = math.max(5, round(winW * 0.0115))
    local y0 = headerInset + headerH + math.max(6, round(winH * 0.035))
    local bottom = math.max(6, round(winH * 0.03))
    local footerH = math.max(M.MinTap, round(winH * Z.footer))
    local footerY = winH - bottom - footerH
    local leftW = round(winW * Z.left)
    local rightW = math.max(172, round(winW * Z.right)) -- "Rewards:" and "+250" on one line need about 172 px
    local leftX = side
    local gridX = leftX + leftW + colGap
    local rightX = winW - side - rightW
    local gridW = rightX - colGap - gridX
    local barH = math.max(M.MinText + 7, round(winH * Z.bar))
    local barGap = math.max(4, round(winH * 0.018))
    local barY = footerY - math.max(6, round(winH * 0.035)) - barH
    local cardGap = math.clamp(round(h * 0.011), 5, 10)
    local cardW = math.floor((gridW - 3 * cardGap) / 4)
    local gridH = barY - barGap - y0
    local cardH = math.floor((gridH - cardGap) / 2)
    local cards: {Rect} = {}
    for r = 0, 1 do
        for c = 0, 3 do
            table.insert(cards, {x = gridX + c * (cardW + cardGap), y = y0 + r * (cardH + cardGap), w = cardW, h = cardH})
        end
    end
    local nameText = math.clamp(round(h * 0.027), M.MinText, 22)
    local pageW = M.MinTap
    local column = footerY + footerH - y0
    -- the rewards box: "Rewards:", the crystal row, the CLAIM button
    local rText = math.clamp(round(h * 0.03), M.MinText, 22)
    local rRow = math.max(M.MinTap - 8, round(h * 0.05))
    local rButton = math.max(M.MinTap, round(h * 0.062))
    local rPad = math.max(4, round(h * 0.008))
    local oneLine = h < 600 -- a short screen: "Rewards:" and the crystal share one line
    local rewardsH = rPad + (if oneLine then rRow else rText + 2 + rRow) + 4 + rButton + rPad
    local panelH = column - colGap - rewardsH
    local pText = math.clamp(round(h * 0.036), 22, 27)
    local pWord = math.clamp(round(h * 0.027), M.MinText, 21)
    local pButton = M.MinTap
    local pButtonW = math.max(70, round(rightW * 0.42))
    local pEdge = math.max(4, round(h * 0.008))
    -- the View button sits in the top right corner of the picture, so the dino gets the height left over by the three lines under it
    local pRender = math.max(40, panelH - (pEdge + pText + pWord + pWord + 4 + pEdge))
    -- the rail: the zone buttons stacked from the header's bottom, the icons in a column right of them
    local railX = win.x + winW + railGap
    local railY = win.y + headerInset + math.floor(headerH * 0.5)
    local zones: {Rect} = {}
    for i = 1, 4 do table.insert(zones, {x = railX, y = railY + (i - 1) * (zoneH + zoneGap), w = zoneW, h = zoneH}) end
    local iconSlots: {Rect} = {}
    for i = 1, nIcons do
        table.insert(iconSlots, {x = railX + zoneW + railGap, y = railY + (i - 1) * (icon + iconText + 2 + zoneGap), w = iconColW, h = math.max(M.MinTap, icon + iconText + 2)})
    end
    return {
        window = win, headerInset = headerInset, headerH = headerH, close = close, titleSize = titleSize, cards = cards, cardName = nameText,
        zonePanel = {x = leftX, y = y0, w = leftW, h = barY + barH - y0, text = math.clamp(round(h * 0.034), 21, 26)},
        bar = {x = gridX, y = barY, w = gridW, h = barH, text = math.clamp(round(barH * 0.62), M.MinText, 24), minFill = math.max(8, round(h * 0.015))},
        prev = {x = gridX, y = barY - math.floor((pageW - barH) / 2), w = pageW, h = pageW},
        next = {x = gridX + gridW - pageW, y = barY - math.floor((pageW - barH) / 2), w = pageW, h = pageW},
        footer = {x = leftX, y = footerY, w = gridX + gridW - leftX, h = footerH, text = math.clamp(round(footerH * 0.52), 22, 30), icon = round(footerH * 1.25)},
        panel = {x = rightX, y = y0, w = rightW, h = panelH, edge = pEdge, nameText = pText, wordText = pWord, render = pRender, button = pButton, buttonW = pButtonW,
            buttonText = math.clamp(round(h * 0.034), 22, 26), inset = round(rightW * 0.06)},
        rewards = {x = rightX, y = y0 + panelH + colGap, w = rightW, h = rewardsH, oneLine = oneLine, pad = rPad, text = rText, row = rRow, button = rButton,
            buttonText = math.clamp(round(h * 0.037), 24, 28), inset = round(rightW * 0.07)},
        zones = zones, zoneText = zoneText, icons = iconSlots, icon = icon, iconText = iconText,
    }
end

return M
