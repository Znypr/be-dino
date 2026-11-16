--!strict
-- BD-1214 (docs/240 order step 3, style tile v2 board 6 and v3 boards 8-10): the rects of Run complete, Home (Sanctuary) and the Welcome
-- steps on the style rules R1-R8. Plain numbers (design px inside the menu body: 824 x 402 on a desktop window, the scroller size on a compact
-- one), no engine call, so tools/verify_screens_cohesion.py measures every rect with the pinned Luau runtime: everything inside the body,
-- nothing overlapping, buttons never under 44 px on screen (R8, docs/72). Numbers PROVISIONAL (LEAD), multiples of 4 from Shared/ToyboxKit.
local Kit = require(script.Parent.ToyboxKit)

local L = {}
export type Rect = {x: number, y: number, w: number, h: number}

local function rect(x: number, y: number, w: number, h: number): Rect
    return {x = math.floor(x), y = math.floor(y), w = math.max(0, math.floor(w)), h = math.max(0, math.floor(h))}
end
L.rect = rect

-- `count` buttons in one row at the foot of the body, right-aligned (one button: centred). Width 220, narrower only when the row would not fit.
function L.buttonRow(bodyW: number, bodyH: number, scale: number, count: number, centred: boolean?): {Rect}
    local h = Kit.buttonHeights(scale)
    local n = math.max(1, count)
    local w = math.min(220, Kit.cellWidth(bodyW, n, Kit.Gutter))
    local rowW = w * n + Kit.Gutter * (n - 1)
    local x0 = if centred or n == 1 then (bodyW - rowW) / 2 else bodyW - rowW
    local out = {}
    for i = 1, count do table.insert(out, rect(x0 + (i - 1) * (w + Kit.Gutter), bodyH - h, w, h)) end
    return out
end

-- Two cream panels side by side over a button row (Run complete: facts | eggs; Home: dino | what is waiting). `leftShare` = the left panel's
-- share of the width (0..1); the left panel is never under 220 px and the right never under 260 px when the body is wide enough for both.
function L.split(bodyW: number, bodyH: number, scale: number, leftShare: number, buttons: number)
    local h = Kit.buttonHeights(scale)
    local panelH = bodyH - Kit.Gutter - h
    local leftW = math.clamp(math.floor(bodyW * leftShare), math.min(220, bodyW), math.max(220, bodyW - Kit.Gutter - 260))
    local left = rect(0, 0, leftW, panelH)
    local right = rect(leftW + Kit.Gutter, 0, bodyW - leftW - Kit.Gutter, panelH)
    return {left = left, right = right, buttons = L.buttonRow(bodyW, bodyH, scale, buttons, false)}
end

-- The fact rows of Run complete and Home: 20 px words (the heading size) in 36 px rows, so what you earned reads at a glance.
L.FactRowH = 36
-- Rows of a panel: fact rows L.FactRowH high from `top`, as many as fit above the panel's padding (a long list never runs out of its panel).
function L.rowsThatFit(panelH: number, top: number, count: number): number
    local room = panelH - Kit.PanelPad - top
    return math.clamp(math.floor(room / L.FactRowH), 0, count)
end
-- The free room of a panel under `top`: one picture (at most 96) and one line under it, centred in that room; nil when under 72 px are left.
function L.tip(panel: Rect, top: number)
    local room = panel.h - Kit.PanelPad - top
    if room < 72 then return nil end
    local pic = math.min(96, room - 40)
    local y = top + math.floor((room - pic - 36) / 2)
    return {picture = rect((panel.w - pic) / 2, y, pic, pic), line = rect(Kit.PanelPad, y + pic + 8, panel.w - Kit.PanelPad * 2, 28)}
end

-- The Welcome steps: `count` equal cream cards in a row over one centred button.
function L.cards(bodyW: number, bodyH: number, scale: number, count: number)
    local h = Kit.buttonHeights(scale)
    local cardH = bodyH - Kit.Gutter - h
    local w = Kit.cellWidth(bodyW, count, Kit.Gutter)
    local cards = {}
    for i = 1, count do table.insert(cards, rect((i - 1) * (w + Kit.Gutter), 0, w, cardH)) end
    return {cards = cards, buttons = L.buttonRow(bodyW, bodyH, scale, 1, true)}
end

-- Inside one Welcome card: the number chip, the picture (as big as fits, at most 128), the title and the line under it, as one block
-- centred in the card (a tall card gets an even margin above and below, never a top-heavy card with an empty foot).
function L.card(card: Rect)
    local pad = Kit.PanelPad
    local gap = Kit.Gutter / 2
    local titleH, lineH = Kit.Type.heading + 8, Kit.Type.body * 2 + 8
    local pic = math.clamp(card.h - pad * 2 - 32 - titleH - lineH - gap * 2, 32, math.min(128, card.w - pad * 2))
    local block = 32 + gap + pic + gap + titleH + lineH
    local top = math.max(pad, math.floor((card.h - block) / 2))
    local chip = rect((card.w - 40) / 2, top, 40, 32)
    local picture = rect((card.w - pic) / 2, chip.y + chip.h + gap, pic, pic)
    local title = rect(pad, picture.y + pic + gap, card.w - pad * 2, titleH)
    local line = rect(pad, title.y + title.h, card.w - pad * 2, lineH)
    return {chip = chip, picture = picture, title = title, line = line}
end

-- Inside a right-hand panel of Run complete with eggs: up to three egg pictures centred, the line under them.
function L.eggsPanel(panel: Rect, eggs: number)
    local pad = Kit.PanelPad
    local n = math.clamp(eggs, 1, 3)
    local size = math.clamp(math.floor((panel.h - pad * 2 - 64) / 1.6), 40, if n == 1 then 120 else 72)
    local rowW = size * n + 8 * (n - 1)
    local y = math.floor((panel.h - size - 64) / 2)
    local pics = {}
    for i = 1, n do table.insert(pics, rect((panel.w - rowW) / 2 + (i - 1) * (size + 8), y, size, size)) end
    return {pictures = pics, line = rect(pad, y + size + 12, panel.w - pad * 2, 52)}
end

-- True when `inner` lies inside a box of w x h (R8: nothing outside its screen).
function L.inside(inner: Rect, w: number, h: number): boolean
    return inner.x >= 0 and inner.y >= 0 and inner.x + inner.w <= w and inner.y + inner.h <= h
end
-- True when two rects overlap (R8: nothing overlapping).
function L.overlap(a: Rect, b: Rect): boolean
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
end

return L
