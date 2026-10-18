--!strict
-- BD-1102 (docs/200): where the toast stack goes. Pure numbers, no Roblox services (tools/verify_menu_layout.py runs it on the real layouts).
-- Studio round 6 (docs/199, pictures 361, 366, 376) at 500 x 465: a toast lay over the whole HUD rail row, and with a menu open over the shop tab row
-- and the first row of potion prices. The old rule (TouchLayout.toastPlacement) only knew the Crystals plate.
--   no menu open: the stack (3 cards tall) sits at the old slot (y 80) when it is clear of every `keepClear` rectangle (the Crystals plate and the goal line
--                 under it, the HUD rail); else it slides sideways to the nearest free spot; else it drops under the blockers.
--   menu open:    ONE card (the newest), never the stack. Above the menu panel when there is room (a desktop window), else below it, else along the bottom
--                 edge of the screen over the lowest part of the menu, slimmed to Slot.EdgeScale (14 px text) and letting taps through to the menu (a small
--                 window has no free spot: the toast then only hides the lowest few pixels for its few seconds). It never takes the top of the menu: the
--                 heading, X, the tab row and the first row's top stay free.
local Slot = {}

Slot.W, Slot.CardH, Slot.Pitch, Slot.MaxCards = 440, 56, 62, 3 -- design px of the cards (Toasts.luau draws them; NotifyQueue.MaxVisible is 3)
Slot.RunY, Slot.MenuY, Slot.Gap, Slot.Edge = 80, 4, 8, 4
Slot.EdgeScale = 0.7 -- along the bottom edge the card is 39 px tall; its 21 design px title still draws at 14.7 px (docs/72: text never under 14 px)

export type Rect = {x: number, y: number, w: number, h: number}
export type Place = {x: number, y: number, cards: number, passThrough: boolean, where: string, scale: number}

local function overlaps(a: Rect, b: Rect): boolean
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
end

local function hitsAny(r: Rect, list: {Rect}): boolean
    for _, b in list do
        if overlaps(r, b) then return true end
    end
    return false
end

function Slot.stackHeight(cards: number, scale: number): number
    return ((math.max(cards, 1) - 1) * Slot.Pitch + Slot.CardH) * scale
end

-- p: canvasW, canvasH (px of the BeDinoUI canvas), scale (the toast UIScale), keepClear (rects in canvas px), menu (the open menu panel's rect, or nil),
--    shift (px the admin panel pushes the stack right; 0 normally).
-- Returns x (px of the stack centre from the screen centre), y (top, px), cards (how many cards to draw: 1 with a menu, else MaxCards),
-- passThrough (true when a tap on the card must reach what is under it) and where ("run", "run-clear", "run-below", "above", "below", "edge").
function Slot.place(p: {canvasW: number, canvasH: number, scale: number, keepClear: {Rect}, menu: Rect?, shift: number?}): Place
    local W, H = p.canvasW, p.canvasH
    local shift = p.shift or 0
    local w = Slot.W * p.scale
    local function box(xOff: number, y: number, cards: number): Rect
        return {x = W / 2 + xOff - w / 2, y = y, w = w, h = Slot.stackHeight(cards, p.scale)}
    end
    local function onScreen(r: Rect): boolean return r.x >= 0 and r.x + r.w <= W + 0.5 and r.y >= 0 and r.y + r.h <= H + 0.5 end

    -- x choices: centred (with the admin shift), then just left of each blocker, then just right of each blocker (never when the admin panel pushes the stack)
    local function xChoices(y: number, cards: number): {number}
        local list = {shift}
        if shift == 0 then
            local h = Slot.stackHeight(cards, p.scale)
            for _, b in p.keepClear do
                if b.y < y + h and y < b.y + b.h then -- only blockers in the stack's rows can push it sideways
                    table.insert(list, b.x - Slot.Gap - w / 2 - W / 2)
                    table.insert(list, b.x + b.w + Slot.Gap + w / 2 - W / 2)
                end
            end
        end
        return list
    end

    local menu = p.menu
    if menu == nil then
        local ys = {Slot.RunY}
        for _, b in p.keepClear do if b.y + b.h + Slot.Gap > Slot.RunY then table.insert(ys, b.y + b.h + Slot.Gap) end end
        table.sort(ys)
        for index, y in ys do
            for _, xOff in xChoices(y, Slot.MaxCards) do
                local r = box(xOff, y, Slot.MaxCards)
                if onScreen(r) and not hitsAny(r, p.keepClear) then
                    return {x = xOff, y = y, cards = Slot.MaxCards, passThrough = false, scale = p.scale, where = if index == 1 then (if xOff == shift then "run" else "run-clear") else "run-below"}
                end
            end
        end
        -- nothing is free (a tiny canvas): the old rule, under the lowest blocker
        local lowest = Slot.RunY
        for _, b in p.keepClear do lowest = math.max(lowest, b.y + b.h + Slot.Gap) end
        return {x = shift, y = lowest, cards = Slot.MaxCards, passThrough = false, scale = p.scale, where = "run-below"}
    end

    -- a menu is open: one card
    local cardH = Slot.CardH * p.scale
    local clearAbove = menu.y - cardH - Slot.Gap / 2 -- the highest y that still leaves a gap above the menu
    if Slot.MenuY <= clearAbove then
        for _, xOff in xChoices(Slot.MenuY, 1) do
            local r = box(xOff, Slot.MenuY, 1)
            if onScreen(r) and not hitsAny(r, p.keepClear) then
                return {x = xOff, y = Slot.MenuY, cards = 1, passThrough = false, scale = p.scale, where = "above"}
            end
        end
    end
    local bottomY = H - Slot.Edge - cardH
    if bottomY >= menu.y + menu.h + Slot.Gap / 2 then
        return {x = shift, y = bottomY, cards = 1, passThrough = false, scale = p.scale, where = "below"}
    end
    local slim = math.min(p.scale, Slot.EdgeScale)
    return {x = shift, y = H - Slot.Edge - Slot.CardH * slim, cards = 1, passThrough = true, scale = slim, where = "edge"}
end

return Slot
