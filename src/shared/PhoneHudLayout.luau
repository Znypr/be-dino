--!strict
-- BD-1258 / BD-1259 / BD-1260 / BD-1268 / BD-1269 / BD-1271 (docs/244 s2.14, owner phone test 2026-11-17, approved mock
-- docs/evidence/2026-11-17-ui-hud/mock-01-hud.png): the phone HUD zones. One job per corner and the middle box stays empty.
--   top-centre    the event banner (weather icon, one line, a short timer line, a faint strip), then the SIZE plate (health inside it)
--   left          exactly two word buttons, SHOP and DINOS (17 % h, word 8 % h, icon 13 % h)
--   right         one column of square tiles 13.5 % h, 1.5 % h apart (Home, Eggs, Fusion, Potions, gear); a second column only when one
--                 does not fit above the jump button
--   bottom-left   counters without plates: crystals, then eggs (icon 9.5 % h, number 6 % h)
--   bottom-right  the potion timers (icon 6 % h, "3 min left" 3.2 % h) left of the jump button, and the jump button itself (Roblox's)
--   bottom-centre LEAP and CHOMP as dark see-through squares; the one toast lane sits just above them
-- The middle box (x 33-67 %, y 31-76 %) holds no persistent HUD piece. Two lanes are transient and may cross it: the toast lane (a toast lasts
-- 3 s, BD-1260 puts it above the ability buttons) and the first-run goal hint under the SIZE plate. Neither may touch a persistent piece.
-- Sizes are a share of the canvas height ("% h") on the phone canvas; a tall desktop canvas keeps phone proportions (the unit is capped at
-- DesignH). Text sizes come from cap heights (cap = 0.7 x TextSize, measured on the owner's phone, docs/244 method), never under the phone
-- floor of TextSize 19 on a touch screen (BD-1259) and never under 14 anywhere (docs/72).
-- Pure numbers, no Roblox services: src/client/PhoneHud.client.luau draws it, tools/verify_phone_hud.py runs it on three phone canvases.
local L = {}

L.DesignH = 560 -- the unit is min(H, DesignH) / 100: a desktop canvas does not blow the HUD up
L.CapRatio = 0.7 -- cap height / TextSize of FredokaOne
L.PhoneFloor, L.MinText = 19, 14 -- BD-1259: TextSize >= 19 on a touch screen; docs/72: >= 14 everywhere
L.MinTarget = 44 -- docs/72 tap target, design px

-- docs/244 s2.14, in % h (the unit).
-- Owner 2026-11-21 on the first build: "more padding around, closer look to reference". Every size below was re-measured on the
-- approved mock (mock-01-hud.png, % of its height): side margin 5, bottom margin 3, SHOP/DINOS 15 tall, tiles 14, counters 9.5 / 6,
-- LEAP/CHOMP 19 with a 4.3 word, tiles 13.5 (mock 14), SIZE plate 50 x 7. The middle box ends at 76 % like the mock's dino (the squares start at 77 %).
-- v3 (owner 2026-11-21 "still looks way off, looks flat, black outline is off, spacing is off"): measured with tools/ref_compare.py
-- (mock vs Studio, % of the SCREEN height; the canvas is the screen minus the top bar, so canvas values are a little larger):
-- edge padding 5.6, SHOP top 27.9, tiles 13.8 tall 1.5 apart, crystals number 8.6 tall, button outline 0.7 % h, gloss 50-85 luma.
-- v5 (owner 2026-11-21 "use ChatGPT as a critic"): the ChatGPT art-director audit of v4 (5/10) gave a full spec in % of the
-- gameplay height; these are its numbers: SHOP/DINOS 42.5 x 16 at left 5.7, top 28, gap 2.4; tiles 15.3 x 13.7 at right 6.4, top 12,
-- gap 1.9; LEAP/CHOMP 22.4 x 20.5, 2.5 from the bottom, 3 apart; banner capsule 93 x 11 at top 1.5 (title 5.8, timer 3.7, icon 7.5);
-- SIZE bar 50.5 x 7.5; outlines 6 px at 720 p (0.85 % h); counters icon 10.5, upright.
L.Spec = {
    margin = 5.7, marginR = 6.4, marginY = 2.5,
    banner = {icon = 7.5, line = 5.3, timer = 3.5, pad = 0.5, top = 1.5, w = 93, h = 11, maxShare = 0.6},
    sizePlate = {h = 7.5, w = 50.5, gap = 1, word = 3.0},
    hint = {cap = 3.0, gap = 0.5, w = 90},
    left = {w = 45, h = 15.8, word = 7.1, icon = 11.5, gap = 2.3, top = 0.281, pad = 2.2, minH = 46}, -- pad/icon tightened so the word gets the mock's ~58 % of the width
    tile = {side = 13.7, gap = 1.9, top = 0.12, aspect = 1.117},
    counter = {icon = 11.5, cap = 6.8, gap = 0.5, chars = 6.5}, -- ChatGPT round 2: text -10 %, icons +20 %
    timer = {icon = 6, cap = 3.2, gap = 0.4, chars = 10, rows = 3},
    square = {side = 20.5, w = 22.4, gap = 3, word = 4.8, minSide = 50},
    toast = {cap = 3.2, lines = 2, gap = 1, w = 100, share = 0.5},
    middle = {x0 = 0.33, x1 = 0.67, y0 = 0.31, y1 = 0.76}, -- v5: the mock's SIZE bar ends at 30.8 %, its squares start at 77 %
}
L.Stroke = {word = 3.5, counter = 4, button = 0.85} -- word/counter: design px; button: % h (min 3 px), black (Kit.Outline)
L.CharW, L.CharWLower = 0.62, 0.44 -- FredokaOne width / TextSize of a capital and of a mixed-case word (estimates for box widths)

export type Rect = {x: number, y: number, w: number, h: number}

function L.unit(H: number): number
    return math.min(H, L.DesignH) / 100
end

-- TextSize for a cap height in % h.
function L.textSize(capPct: number, H: number, touch: boolean): number
    local size = math.floor(capPct * L.unit(H) / L.CapRatio + 0.5)
    return math.max(size, if touch then L.PhoneFloor else L.MinText)
end

local function lineH(textSize: number): number
    return math.ceil(textSize * 1.15)
end

function L.overlaps(a: Rect, b: Rect): boolean
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
end

-- Roblox's jump button when it has not been measured yet (TouchJumpController: 70 px on a screen whose short side is <= 500, else 120).
function L.jumpGuess(W: number, H: number): Rect
    local small = H <= 500
    local size = if small then 70 else 120
    local y = if small then H - size - 20 else H - size * 1.75
    return {x = W - (size * 1.5 - 10), y = y, w = size, h = size}
end

-- Short counter numbers: 1,250 / 12.4K / 3.4M / 1.2B (whole numbers below 10,000 are grouped).
function L.counterText(value: any): string
    local n = if typeof(value) == "number" and value == value then math.max(0, math.floor(value + 0.5)) else 0
    local function short(v: number, suffix: string): string
        local text = string.format("%.1f", math.floor(v * 10) / 10)
        text = string.gsub(text, "%.0$", "")
        return text .. suffix
    end
    if n >= 1e9 then return short(n / 1e9, "B") end
    if n >= 1e6 then return short(n / 1e6, "M") end
    if n >= 1e4 then return short(n / 1e3, "K") end
    local digits = tostring(n)
    local out = string.reverse((string.gsub(string.reverse(digits), "(%d%d%d)", "%1,")))
    if string.sub(out, 1, 1) == "," then out = string.sub(out, 2) end
    return out
end

-- Kid timer words (docs/72): "3 min left", "40 s left", never "2:59". Minutes round UP (2 min 59 s reads "3 min", like the mock).
function L.duration(seconds: number): string
    local total = math.max(0, math.ceil(seconds))
    if total < 60 then return total .. " s" end
    if total < 3600 then return math.ceil(total / 60) .. " min" end
    return math.ceil(total / 3600) .. " h"
end
function L.timeLeft(seconds: number): string return L.duration(seconds) .. " left" end

-- The banner words. id = workspace WeatherId ("clear" between events), name = WeatherName, secondsLeft to the end (event) or to the next one (clear).
function L.bannerWords(id: any, name: any, secondsLeft: number): (string, string)
    if id == nil or id == "clear" or id == "" then
        return "Sunny!", "Weather in " .. L.duration(secondsLeft)
    end
    local what = if type(name) == "string" and name ~= "" then name else tostring(id)
    return what .. " is here!", L.timeLeft(secondsLeft)
end

-- The Home tile shows one short word only when it is not a home picture: "GO" at home (start a run), the home picture in a run.
function L.homeWord(runState: any): string?
    if runState == "Active" then return nil end
    if runState == "Sanctuary" then return "GO" end
    return "..."
end

-- p = {W, H (canvas design px), touch, jump: Rect? (measured), tiles: number of visible right tiles, chomp: CHOMP shown, timers: potion rows (0-3)}
-- p.inset: Roblox's top bar height above the canvas (GuiService:GetGuiInset). v6 (ChatGPT round 2: "everything near the top is
-- 8-12 % h too low"): sizes and top positions are % of the WHOLE screen (canvas + top bar), like the reference mock; a top piece may
-- reach up into the top bar (negative canvas y), the bottom pieces keep their canvas-bottom anchor.
function L.compute(p: {W: number, H: number, touch: boolean, jump: Rect?, tiles: number, chomp: boolean, timers: number?, inset: number?}): any
    local W, H, touch = p.W, p.H, p.touch
    local inset = p.inset or 0
    local Hs = H + inset -- the whole screen
    local u = L.unit(Hs)
    local S = L.Spec
    local m = S.margin * u -- left
    local mr = S.marginR * u -- right
    local my = S.marginY * u -- bottom
    local out: any = {W = W, H = H, unit = u, touch = touch, text = {}, inset = inset}
    local t = out.text
    t.bannerLine, t.bannerTimer = L.textSize(S.banner.line, H, touch), L.textSize(S.banner.timer, H, touch)
    t.sizeWord, t.hint = L.textSize(S.sizePlate.word, H, touch), L.textSize(S.hint.cap, H, touch)
    t.leftWord, t.counter = L.textSize(S.left.word, H, touch), L.textSize(S.counter.cap, H, touch)
    t.timer, t.squareWord = L.textSize(S.timer.cap, H, touch), L.textSize(S.square.word, H, touch)
    t.toast, t.homeWord = L.textSize(S.toast.cap, H, touch), L.textSize(S.square.word, H, touch)

    -- top-centre: banner, SIZE plate, hint
    -- top-left corner (empty in the mock): one row of small chips (the playtest "Tell us!" button, then the owner's Admin button), 44 px tall
    local chipH, chipGap = L.MinTarget, 1.5 * u
    local chipY = S.marginY * u
    out.chips = {
        tellUs = {x = m, y = chipY, w = 100, h = chipH},
        admin = {x = m + 100 + chipGap, y = chipY, w = 88, h = chipH},
    }
    local bannerIcon = S.banner.icon * u
    local bannerH = math.max(S.banner.h * u, math.ceil((t.bannerLine + t.bannerTimer) * 0.9) + 2 * S.banner.pad * u) -- tight lines (0.9 x size)
    local chipsRight = out.chips.admin.x + out.chips.admin.w
    local bannerW = math.min(S.banner.w * u, W * S.banner.maxShare, W - 2 * (chipsRight + u))
    out.banner = {x = (W - bannerW) / 2, y = S.banner.top * u - inset, w = bannerW, h = bannerH, icon = bannerIcon}
    local plateH = math.max(S.sizePlate.h * u, lineH(t.sizeWord) + 4)
    local plateW = math.min(S.sizePlate.w * u, W * 0.4)
    out.sizePlate = {x = (W - plateW) / 2, y = out.banner.y + bannerH + S.sizePlate.gap * u, w = plateW, h = plateH}

    -- left: SHOP and DINOS
    local leftH = math.max(S.left.h * u, S.left.minH)
    local leftIcon = math.min(S.left.icon * u, leftH - 6)
    local leftW = math.ceil(S.left.w * u)
    -- the word fits the fixed width: "DINOS" (5 capitals) between the icon and the right padding, never under the text floor
    local roomForWord = leftW - S.left.pad * u - leftIcon - u - S.left.pad * u
    -- 0.5 x TextSize per capital: measured on the mock ("DINOS" is 2.44 x its TextSize wide); L.CharW (0.62) is a safe box estimate only
    t.leftWord = math.max(math.min(t.leftWord, math.floor(roomForWord / (5 * 0.5))), if touch then L.PhoneFloor else L.MinText) -- the client refits it with TextService
    local leftGap = S.left.gap * u + 2 * math.max(3, math.floor(L.Stroke.button * u + 0.5)) -- clear gap + both outlines
    local leftY = S.left.top * Hs - inset
    out.left = {
        {x = m, y = leftY, w = leftW, h = leftH, icon = leftIcon},
        {x = m, y = leftY + leftH + leftGap, w = leftW, h = leftH, icon = leftIcon},
    }

    -- the first-run hint under the SIZE plate: never wider than the room between the word buttons (v3: SHOP sits higher now)
    local hintW = math.min(S.hint.w * u, W * 0.6, W - 2 * (m + leftW + u), W - 2 * (chipsRight + u)) -- v6: clear of the chip row too
    out.hint = {x = (W - hintW) / 2, y = out.sizePlate.y + plateH + S.hint.gap * u, w = hintW, h = lineH(t.hint)}

    -- Owner 2026-11-21 ("closer look to reference"): the Codes button (GiftsPanel) joins this row when it fits left of the banner;
    -- otherwise it is nil and GiftsPanel keeps its own clear-spot rule (CodesButtonSpot).
    local codes = {x = out.chips.admin.x + out.chips.admin.w + chipGap, y = chipY, w = 96, h = chipH}
    if codes.x + codes.w <= out.banner.x - u then out.chips.codes = codes end

    -- bottom-left: crystals over eggs
    local counterIcon = S.counter.icon * u
    local counterRow = math.max(counterIcon, lineH(t.counter))
    local counterW = math.ceil(counterIcon + u + S.counter.chars * L.CharW * t.counter)
    out.eggs = {x = m, y = H - my - counterRow, w = counterW, h = counterRow, icon = counterIcon}
    out.crystals = {x = m, y = out.eggs.y - S.counter.gap * u - counterRow, w = counterW, h = counterRow, icon = counterIcon}

    -- bottom-right: Roblox's jump button, the potion timers left of it
    local jump = p.jump or L.jumpGuess(W, H)
    out.jump = jump
    local timerIcon = S.timer.icon * u
    local timerRow = math.max(timerIcon, lineH(t.timer))
    local timerW = math.ceil(timerIcon + u + S.timer.chars * L.CharWLower * t.timer)
    local rows = math.clamp(p.timers or S.timer.rows, 0, S.timer.rows)
    local timersH = rows * timerRow + math.max(rows - 1, 0) * S.timer.gap * u
    local timerRight = math.min(jump.x - u, W - mr)
    out.timers = {x = timerRight - timerW, y = H - my - timersH, w = timerW, h = timersH, row = timerRow, icon = timerIcon, gap = S.timer.gap * u}

    -- bottom-centre: LEAP and CHOMP squares, the toast lane above them
    local side = math.max(S.square.side * u, S.square.minSide)
    local squareW = math.max(S.square.w * u, math.ceil(5 * 0.66 * t.squareWord + 10)) -- "CHOMP" fits on one line at the text floor
    local gap = S.square.gap * u
    local count = if p.chomp then 2 else 1
    local rowW = count * squareW + (count - 1) * gap
    out.squares = {}
    for i = 1, count do
        table.insert(out.squares, {x = (W - rowW) / 2 + (i - 1) * (squareW + gap), y = H - my - side, w = squareW, h = side})
    end
    out.action = {x = (W - rowW) / 2, y = H - my - side, w = rowW, h = side}
    -- as wide as the gap between the counters and the timers allows (a toast never covers either)
    local laneHalf = math.min(out.timers.x - u - W / 2, W / 2 - (out.crystals.x + out.crystals.w) - u)
    local laneW = math.min(S.toast.w * u, W * S.toast.share, 2 * laneHalf)
    local laneLine = lineH(t.toast) + math.floor(u)
    local laneH = S.toast.lines * laneLine
    out.lane = {x = (W - laneW) / 2, y = out.action.y - S.toast.gap * u - laneH, w = laneW, h = laneH, line = laneLine}

    -- right: the square tiles, top down; a second column (to the left) only when one does not fit above the jump button
    local tile = math.max(S.tile.side * u, L.MinTarget)
    local stroke = math.max(3, math.floor(L.Stroke.button * u + 0.5))
    -- v4: the outline is drawn OUTSIDE each frame, so the clear gap between two tiles is gap + 2 outlines (mock: 1.6 % h clear)
    local tileGap = S.tile.gap * u + 2 * stroke
    local colX = W - mr - tile
    local columnHitsJump = colX < jump.x + jump.w and jump.x < colX + tile
    local bottom = if columnHitsJump then jump.y - u else H - my
    -- v6: the potion timers sit left of the jump button; when the (bigger) column would reach them, it stops above them too
    local colW = math.floor(tile * S.tile.aspect + 0.5)
    local colLeft = W - mr - colW
    if out.timers.h > 0 and out.timers.x < colLeft + colW and colLeft < out.timers.x + out.timers.w then
        bottom = math.min(bottom, out.timers.y - u)
    end
    local top = math.max(my - inset, S.tile.top * Hs - inset)
    local need = p.tiles * tile + math.max(p.tiles - 1, 0) * tileGap
    if top + need > bottom then top = my end
    -- v3: shrink the tiles (to 12 % h, never under 44 px) before a second column is ever used
    if p.tiles > 0 and top + need > bottom then
        local fit = math.floor((bottom - top - math.max(p.tiles - 1, 0) * tileGap) / p.tiles)
        if fit >= math.max(9.5 * u, L.MinTarget) then -- v6: 9.5 lets five tiles (GO included) stay in one column above the timers
            tile = fit
            colX = W - mr - tile
        end
    end
    local tileW = math.floor(tile * S.tile.aspect + 0.5) -- the mock's tiles are a little wider than tall (15.3 x 13.7 % h)
    colX = W - mr - tileW
    local perColumn = math.max(1, math.floor((bottom - top + tileGap) / (tile + tileGap)))
    out.tiles = {}
    for i = 1, p.tiles do
        local column = (i - 1) // perColumn
        local row = (i - 1) % perColumn
        table.insert(out.tiles, {x = colX - column * (tileW + tileGap), y = top + row * (tile + tileGap), w = tileW, h = tile})
    end
    out.tileSide = tile
    out.buttonStroke = math.max(3, math.floor(L.Stroke.button * u + 0.5))

    -- the Studio-only "Test game: not saved" chip (HudCohesion) goes to the empty top-left corner
    -- Studio only: between the counters and LEAP, on the bottom line (no player ever sees it)
    out.testChip = {x = out.crystals.x + out.crystals.w + u, y = H - my - 28, w = 176, h = 28}

    out.middle = {x = S.middle.x0 * W, y = S.middle.y0 * Hs - inset, w = (S.middle.x1 - S.middle.x0) * W, h = (S.middle.y1 - S.middle.y0) * Hs}
    return out
end

-- Every persistent HUD piece with a name (the middle box must stay clear of all of them, and none may touch another).
function L.persistent(layout: any): {{name: string, rect: Rect}}
    local list = {
        {name = "banner", rect = layout.banner}, {name = "sizePlate", rect = layout.sizePlate},
        {name = "shop", rect = layout.left[1]}, {name = "dinos", rect = layout.left[2]},
        {name = "crystals", rect = layout.crystals}, {name = "eggs", rect = layout.eggs},
        {name = "jump", rect = layout.jump},
        {name = "tellUs", rect = layout.chips.tellUs}, {name = "admin", rect = layout.chips.admin},
    }
    if layout.chips.codes then table.insert(list, {name = "codes", rect = layout.chips.codes}) end
    if layout.timers.h > 0 then table.insert(list, {name = "timers", rect = layout.timers}) end
    for i, r in layout.squares do table.insert(list, {name = "square" .. i, rect = r}) end
    for i, r in layout.tiles do table.insert(list, {name = "tile" .. i, rect = r}) end
    return list
end

-- Problems of a layout (empty = fine): two persistent pieces touch, one sits in the middle box or off the canvas, a lane touches a piece,
-- a tap target is under 44 px or a text size is under the floor.
function L.problems(layout: any): {string}
    local out = {}
    local items = L.persistent(layout)
    local W, H = layout.W, layout.H
    for i, a in items do
        local r = a.rect
        if a.name ~= "jump" and (r.x < -0.5 or r.y < -(layout.inset or 0) - 0.5 or r.x + r.w > W + 0.5 or r.y + r.h > H + 0.5) then table.insert(out, a.name .. " is off the canvas") end
        if L.overlaps(r, layout.middle) then table.insert(out, a.name .. " is in the middle box") end
        for j = i + 1, #items do
            if L.overlaps(r, items[j].rect) then table.insert(out, a.name .. " overlaps " .. items[j].name) end
        end
        if L.overlaps(r, layout.lane) then table.insert(out, "the toast lane covers " .. a.name) end
        if a.name ~= "sizePlate" and L.overlaps(r, layout.hint) then table.insert(out, "the goal hint covers " .. a.name) end
    end
    for _, r in layout.squares do if r.w < L.MinTarget or r.h < L.MinTarget then table.insert(out, "a square is under 44 px") end end
    for _, r in layout.tiles do if r.w < L.MinTarget then table.insert(out, "a tile is under 44 px") end end
    for _, r in layout.left do if r.h < L.MinTarget then table.insert(out, "a word button is under 44 px") end end
    local floor = if layout.touch then L.PhoneFloor else L.MinText
    for name, size in layout.text do if size < floor then table.insert(out, "text " .. name .. " is " .. size .. " (< " .. floor .. ")") end end
    if layout.text.counter < layout.text.timer then table.insert(out, "counters must be bigger than timer words") end
    return out
end

return L
