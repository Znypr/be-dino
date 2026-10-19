--!strict
-- BD-1132 (docs/205 picture 447): where the SOFT weather title goes. At home in the cave the weather name ("Volcanic Bloom") is a small soft line, not the big card,
-- and it was drawn at 31 percent of the screen height whatever the window: at 516 x 481 that is on top of the Potions button of the HUD rail (the title layer is above
-- the HUD). Pure numbers, no Roblox services: tools/verify_shop_prompt_bubble.py runs it on the real HUD rectangles at every window size.
-- The soft line keeps its place when nothing is there; else it slides up or down to the nearest spot where its box touches no HUD piece (and stays on the screen).
local Slot = {}
Slot.Gap = 8 -- px kept free between the title box and a HUD piece

export type Rect = {x: number, y: number, w: number, h: number}

local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end

local function free(box: Rect, blockers: {Rect}): boolean
    for _, b in blockers do
        if box.x < b.x + b.w + Slot.Gap and b.x - Slot.Gap < box.x + box.w and box.y < b.y + b.h + Slot.Gap and b.y - Slot.Gap < box.y + box.h then return false end
    end
    return true
end

-- p = {w, h = the screen in px, boxW, boxH = the soft title's box in px (centred on x = w / 2), wantY = where its centre would be, blockers = {Rect} HUD pieces in
-- screen px (the HUD canvas is offset by the top bar: the caller adds that offset)}. Returns the centre y in px.
function Slot.centreY(p: any): number
    if typeof(p) ~= "table" or not finite(p.w) or not finite(p.h) or not finite(p.boxW) or not finite(p.boxH) or not finite(p.wantY) then
        return if typeof(p) == "table" and finite(p.wantY) then p.wantY else 0
    end
    local w, h, bw, bh, want = p.w :: number, p.h :: number, p.boxW :: number, p.boxH :: number, p.wantY :: number
    local blockers: {Rect} = {}
    if typeof(p.blockers) == "table" then
        for _, b in p.blockers do
            if typeof(b) == "table" and finite(b.x) and finite(b.y) and finite(b.w) and finite(b.h) and b.w > 0 and b.h > 0 then table.insert(blockers, {x = b.x, y = b.y, w = b.w, h = b.h}) end
        end
    end
    local function boxAt(cy: number): Rect return {x = w / 2 - bw / 2, y = cy - bh / 2, w = bw, h = bh} end
    local function onScreen(cy: number): boolean return cy - bh / 2 >= 0 and cy + bh / 2 <= h end
    if free(boxAt(want), blockers) then return want end
    local candidates = {}
    for _, b in blockers do
        table.insert(candidates, b.y - Slot.Gap - bh / 2 - 0.5)
        table.insert(candidates, b.y + b.h + Slot.Gap + bh / 2 + 0.5)
    end
    local best, bestDistance = want, math.huge
    for _, cy in candidates do
        if onScreen(cy) and free(boxAt(cy), blockers) and math.abs(cy - want) < bestDistance then best, bestDistance = cy, math.abs(cy - want) end
    end
    return best
end

return Slot
