--!strict
-- BD-1241 (emulator pass 2026-11-17, docs/240 R8): where the HUD "Codes" button goes. GiftsPanel used a fixed spot (right edge, y 162) that sat on
-- the weather chip whenever the timers column (LEAP, weather, potions) moves up on a short canvas (1274 x 481: Codes 162-206 over the chip 157-202).
-- Pure rule, no instances: the default spot stays when it is clear; otherwise the first clear spot of: left of the piece it hit (same height),
-- just above that piece, just below it. Blockers are the HUD rectangles Bootstrap / HudV2 publish on the BeDinoUI canvas (TimersRect, WalletBlockRect, ...).
-- Used only while Config.MenusCohesionEnabled is on (GiftsPanel asks for it); checked offline by tools/verify_codes_button_spot.py.
local Spot = {}

export type Rect = {x: number, y: number, w: number, h: number}

Spot.Gap = 8
Spot.Margin = 8

local function overlaps(a: Rect, b: Rect): boolean
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
end

local function inside(r: Rect, width: number, height: number): boolean
    return r.x >= Spot.Margin and r.y >= 0 and r.x + r.w <= width - Spot.Margin + 1e-6 and r.y + r.h <= height
end

local function clear(r: Rect, blockers: {Rect}, width: number, height: number): boolean
    if not inside(r, width, height) then return false end
    for _, b in blockers do
        if overlaps(r, b) then return false end
    end
    return true
end

-- default: the old spot; blockers: HUD rectangles (canvas px); width / height: the canvas. Returns the spot and whether it is clear of every blocker.
function Spot.place(default: Rect, blockers: {Rect}, width: number, height: number): (Rect, boolean)
    if clear(default, blockers, width, height) then return default, true end
    local gap = Spot.Gap
    for _, b in blockers do
        if overlaps(default, b) then
            local candidates: {Rect} = {
                {x = b.x - gap - default.w, y = default.y, w = default.w, h = default.h},
                {x = default.x, y = b.y - gap - default.h, w = default.w, h = default.h},
                {x = default.x, y = b.y + b.h + gap, w = default.w, h = default.h},
            }
            for _, c in candidates do
                if clear(c, blockers, width, height) then return c, true end
            end
        end
    end
    return default, false
end

-- A Roblox Rect attribute (Min / Max) -> Rect, or nil.
function Spot.fromAttribute(value: any): Rect?
    if typeof(value) ~= "Rect" then return nil end
    local w, h = value.Max.X - value.Min.X, value.Max.Y - value.Min.Y
    if w <= 0 or h <= 0 then return nil end
    return {x = value.Min.X, y = value.Min.Y, w = w, h = h}
end

return Spot
