--!strict
-- BD-1107 (docs/203): where the ribbons and the "why Skip stops" tag of the hatch reveal card go, and how big their words are. Pure numbers (no Instances).
-- Studio round 7 (docs/200, picture 416, a 498 x 463 window, a Rainbow egg): the "Rainbow egg!" tag was cut at the left edge of the card and the chips lay over
-- each other. The old code put every ribbon at a fixed spot and let the words shrink to fit a box, and a shrinking word cannot go under its minimum size.
-- Now every item is MEASURED first (TagFit, at the 14 px floor of the window it will be drawn in), gets the size its words need, and the items of one side
-- are STACKED downwards with a gap, so they cannot overlap whatever their number or length. Two items never share a spot; a word that is too wide for the
-- column wraps onto a second line (the item grows taller) before it is cut.
-- Body coordinates: the card is 824 x 402 design px; the name starts at y 236. Desktop numbers are the old ones where the words fit.
local TagFit = require(script.Parent.TagFit)

local L = {}
L.BodyW = 824
L.Margin = 10 -- design px kept free between an item (with its tilt) and the card's left or right edge
L.FirstCy = 52 -- the first item of a side is centred here (the old ribbon row)
L.Bottom = 228 -- the lowest an item may reach: the name label starts at 236
L.Gap = 6 -- between two items of a side
L.MaxW = 236 -- the widest item (a column of the card's sides, the dino view in the middle stays free)
L.Ribbon = {h = 44, icon = 42, right = 8, textMax = 26}
L.Tag = {titleMax = 24, lineMax = 18, pad = 8, minW = 190, titleLinesMax = 2}

export type Item = {kind: string, side: string, text: string, line: string?, minW: number?, tilt: number?}
export type Placed = {kind: string, side: string, cx: number, cy: number, w: number, h: number, tilt: number, text: string, size: number, line: string?, lineSize: number?, textLines: number, lineLines: number}

-- Half width and half height of a w x h box turned by `tilt` degrees.
function L.halfExtent(w: number, h: number, tilt: number): (number, number)
    local r = math.rad(math.abs(tilt))
    return (w * math.cos(r) + h * math.sin(r)) / 2, (w * math.sin(r) + h * math.cos(r)) / 2
end

-- One ribbon (a diamond, then the word): its own size from its word.
local function ribbonSize(item: Item, floor: number): Placed
    local R = L.Ribbon
    local roomW = L.MaxW - R.icon - R.right - 6
    local fit = TagFit.fit(item.text, roomW, {maxSize = R.textMax, minSize = floor, maxLines = 2})
    local w = math.min(L.MaxW, math.max(item.minW or 0, R.icon + R.right + 6 + fit.width))
    local h = math.max(R.h, fit.height + 8)
    return {kind = item.kind, side = item.side, cx = 0, cy = 0, w = w, h = h, tilt = item.tilt or 0, text = fit.text, size = fit.size, textLines = fit.lines, lineLines = 0}
end

-- The stop tag: the title (the reason), then the plain line "Skip stops here".
local function tagSize(item: Item, floor: number): Placed
    local T = L.Tag
    local roomW = L.MaxW - 2 * T.pad
    local title = TagFit.fit(item.text, roomW, {maxSize = T.titleMax, minSize = floor, maxLines = T.titleLinesMax})
    local line = TagFit.fit(item.line or "", roomW, {maxSize = T.lineMax, minSize = floor, maxLines = 2})
    local w = math.min(L.MaxW, math.max(item.minW or T.minW, 2 * T.pad + math.max(title.width, line.width)))
    local h = title.height + line.height + 8
    return {kind = item.kind, side = item.side, cx = 0, cy = 0, w = w, h = h, tilt = item.tilt or 0, text = title.text, size = title.size, line = line.text, lineSize = line.size,
        textLines = title.lines, lineLines = line.lines}
end

-- Place the items. `screenScale` = screen px per design px of the card (it decides the 14 px floor in design px). Items are stacked in the order given
-- within their side ("left" / "right"). When an item would reach below L.Bottom on its own side and fits on the other one, it goes to the other side (a Shiny
-- ribbon, a long mutation name and the stop tag on one side do not fit a 500 px window). Returns the placed items (same order) and `ok` = nothing reaches
-- below L.Bottom.
function L.plan(items: {Item}, screenScale: number): ({Placed}, boolean)
    local floor = TagFit.floorSize(screenScale)
    local cursor: {[string]: number} = {}
    local placed: {Placed} = {}
    local ok = true
    -- where would `p` sit at the bottom of `side`? returns the centre y and the next free y of that side
    local function at(p: Placed, side: string): (number, number)
        local hw, hh = L.halfExtent(p.w, p.h, p.tilt)
        local top = cursor[side]
        local cy = if top == nil then L.FirstCy else top + hh
        if top == nil and cy - hh < 4 then cy = 4 + hh end -- the first item keeps the old centre line, a tall one still must not start above the card
        return cy, cy + hh + L.Gap
    end
    for _, item in items do
        local p = if item.kind == "stop" then tagSize(item, floor) else ribbonSize(item, floor)
        local _, hh = L.halfExtent(p.w, p.h, p.tilt)
        local side = item.side
        local cy, nextY = at(p, side)
        if cy + hh > L.Bottom + 1e-6 then
            local other = if side == "left" then "right" else "left"
            local cy2, next2 = at(p, other)
            if cy2 + hh <= L.Bottom + 1e-6 then side, cy, nextY = other, cy2, next2 else ok = false end
        end
        local hw = L.halfExtent(p.w, p.h, p.tilt)
        p.side, p.cy = side, cy
        p.cx = if side == "left" then L.Margin + hw else L.BodyW - L.Margin - hw
        cursor[side] = nextY
        table.insert(placed, p)
    end
    return placed, ok
end

return L
