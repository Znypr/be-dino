--!strict
-- BD-1095 (docs/197 pictures 347 and 348): the hub Goals panel and the Tasks (objectives) panel are two corner HUD cards. Opened together at 500 x 465 they drew over each
-- other and the text was unreadable (Goals opens leftwards over the Tasks pill, the Tasks sheet opens over the Goals header). The rule, pure so it can be tested on every canvas:
--   * ONE panel is open at a time: opening one folds the other (the one the player touched last stays).
--   * A folded panel whose spot the open one needs is HIDDEN until the open one folds (its folded rect overlaps the other's open rect).
-- Goals stays fold-only (BD-1074, docs/115): no tap-outside close, no catcher. The panels share the BeDinoUI attribute "HudPanelOpen" ("goals" | "tasks" | "").
-- No Instances, no services. Rects are {x, y, w, h} in the same pixel space.
local TouchLayout = require(script.Parent.TouchLayout)

local Stack = {}
export type R = {x: number, y: number, w: number, h: number}

Stack.Attribute = "HudPanelOpen"
Stack.Goals, Stack.Tasks = "goals", "tasks"

-- The rect the Goals panel covers while open, from its folded rect (44 px tall at scale s; opens leftwards from the right edge, 260 design px wide, 214 tall).
function Stack.goalsOpen(folded: R): R
    local G = TouchLayout.GOALS
    local s = folded.h / G.h
    local w = G.w * s
    return {x = folded.x + folded.w - w, y = folded.y, w = w, h = TouchLayout.GOALS_OPEN_H * s}
end

-- A Roblox Rect attribute -> {x, y, w, h} (nil for anything else, e.g. an attribute that is not published yet).
function Stack.fromRect(r: any): R?
    if typeof(r) ~= "Rect" then return nil end
    return {x = r.Min.X, y = r.Min.Y, w = r.Width, h = r.Height}
end

local function overlaps(a: R, b: R): boolean
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
end
Stack.overlaps = overlaps

-- The new value of the shared attribute after `panel` opened or folded. Folding a panel never clears what another panel set.
function Stack.after(current: any, panel: string, opening: boolean): string
    if opening then return panel end
    if current == panel then return "" end
    return if typeof(current) == "string" then current else ""
end

-- Must `panel` fold itself now? (it is open but the shared attribute names another panel)
function Stack.mustFold(current: any, panel: string): boolean
    return typeof(current) == "string" and current ~= "" and current ~= panel
end

-- Is `panel` (folded, at `own`) hidden because another panel is open and needs that spot? otherOpen = the open rect of the other panel (nil = unknown = not hidden).
function Stack.hidden(panel: string, current: any, own: R?, otherOpen: R?): boolean
    if typeof(current) ~= "string" or current == "" or current == panel or own == nil or otherOpen == nil then return false end
    return overlaps(own, otherOpen)
end

return Stack
