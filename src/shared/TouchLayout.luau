--!strict
-- BD-054: pure gameplay-HUD layout math for touch phones/tablets and desktop.
-- No Roblox services are used: every number is a pixel inside the BeDinoUI ScreenGui
-- canvas, which uses ScreenInsets = CoreUISafeInsets (device notch/gesture bar and the
-- Roblox top bar are already excluded). Bootstrap.client.luau applies the result;
-- tools/verify_movement_mobile.py checks it for several viewports offline.
--
-- Each placed element is {x, y, scale, w, h}: (x, y) is the top-left corner with
-- AnchorPoint (0, 0), (w, h) is the design size before UIScale, so the rendered
-- rectangle is (x, y, w * scale, h * scale).
local Config = require(script.Parent.Config)
local TouchLayout = {}

export type Rect = {x: number, y: number, w: number, h: number}

TouchLayout.HUD = {w = 390, h = 94}
TouchLayout.CRYSTAL = {w = 260, h = 48}
TouchLayout.TIMERS_W = 286
TouchLayout.LEAP_H, TouchLayout.WEATHER_H, TouchLayout.BUFFS_H = 60, 62, 68
TouchLayout.ACTION = {w = 244, h = 60}

local function clamp(value: number, low: number, high: number): number
    return math.max(low, math.min(high, value))
end

function TouchLayout.rendered(element): Rect
    return {x = element.x, y = element.y, w = element.w * element.scale, h = element.h * element.scale}
end

function TouchLayout.overlaps(a: Rect, b: Rect): boolean
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
end

local function union(a: Rect, b: Rect?): Rect
    if not b or b.w <= 0 or b.h <= 0 then return a end
    local x, y = math.min(a.x, b.x), math.min(a.y, b.y)
    return {x = x, y = y, w = math.max(a.x + a.w, b.x + b.w) - x, h = math.max(a.y + a.h, b.y + b.h) - y}
end

-- Mirrors the Roblox PlayerModule defaults: DynamicThumbstickFrame covers the left 40%
-- of the lower two thirds; TouchJump is a 70 px button on small screens (shorter side
-- <= 500) or 120 px otherwise. Measured rects from the live TouchGui are unioned in.
function TouchLayout.reservedZones(width: number, height: number, measuredThumb: Rect?, measuredJump: Rect?): (Rect, Rect)
    local thumb = union({x = 0, y = height / 3, w = width * 0.4, h = height * 2 / 3}, measuredThumb)
    local small = math.min(width, height) <= 500
    local jump: Rect = if small then {x = width - 95, y = height - 90, w = 70, h = 70}
        else {x = width - 170, y = height - 210, w = 120, h = 120}
    jump = union(jump, measuredJump)
    -- Reserve the whole thumb-resting corner from the jump button to the screen edges.
    local m = Config.TouchSafeMargin
    local corner = {x = jump.x - m, y = jump.y - m, w = width - jump.x + m, h = height - jump.y + m}
    local thumbZone = {x = thumb.x, y = thumb.y - m, w = thumb.w + m, h = height - thumb.y + m}
    return thumbZone, corner
end

local function railButtons(count: number, columns: number, bw: number, bh: number, gap: number)
    local positions = {}
    for i = 1, count do
        local column = (i - 1) % columns
        local row = (i - 1) // columns
        positions[i] = {x = gap + column * (bw + gap), y = gap + row * (bh + gap)}
    end
    return positions
end

local function buttonContent(bw: number, bh: number)
    if bw >= 120 then
        -- Wide tablets: icon left, label right (desktop style).
        local icon = math.min(bh - 12, 40)
        return {iconX = 4, iconY = (bh - icon) / 2, icon = icon, labelX = icon + 8, labelY = 0,
            labelW = bw - icon - 10, labelH = bh, textSize = clamp(math.floor((bw - icon - 10) / 4.8), 12, 17)}
    end
    -- Phones: icon above a short label.
    local icon = math.min(math.floor(bh * 0.5), bw - 12)
    return {iconX = (bw - icon) / 2, iconY = 3, icon = icon, labelX = 0, labelY = icon + 3,
        labelW = bw, labelH = bh - icon - 5, textSize = clamp(math.floor((bw - 4) / 4.7), 10, 14)}
end

local function desktop(width: number, height: number, count: number)
    local small = clamp(math.min(width / 1000, height / 800), 0.3, 1)
    local crystalScale = math.max(0.65, small)
    local hud = {x = 18, y = height - 18 - TouchLayout.HUD.h * small, scale = small, w = TouchLayout.HUD.w, h = TouchLayout.HUD.h}
    local railH = count * 62 + 10
    local action = {x = 0, y = height - 22 - TouchLayout.ACTION.h * small, scale = small, w = TouchLayout.ACTION.w, h = TouchLayout.ACTION.h}
    action.x = math.max(width / 2 - action.w * small / 2, hud.x + hud.w * small + 12)
    local crystalX = width - 20 - TouchLayout.CRYSTAL.w * crystalScale
    local noticeW = math.min(500, 2 * (crystalX - 8 - width / 2))
    return {
        touch = false,
        reserved = {},
        crystal = {x = crystalX, y = 8, scale = crystalScale, w = TouchLayout.CRYSTAL.w, h = TouchLayout.CRYSTAL.h},
        hud = hud,
        rail = {x = 14, y = height / 2 - railH * small / 2, scale = small, w = 186, h = railH,
            button = {w = 172, h = 54, iconX = 5, iconY = 6, icon = 40, labelX = 52, labelY = 0, labelW = 114, labelH = 54, textSize = 19},
            positions = railButtons(count, 1, 172, 54, 7) :: any},
        timers = {x = width - 20 - TouchLayout.TIMERS_W * small, y = height - 22 - 220 * small, scale = small, w = TouchLayout.TIMERS_W, h = 220,
            leapY = 0, weatherY = 72, weatherVisible = true, buffsY = 145, buffsH = 68, buffsVisible = true},
        action = action,
        badge = {x = width / 2 - 125, y = 36, scale = 1, w = 250, h = 24, textSize = 15},
        notice = {x = width / 2 - noticeW / 2, y = 8, scale = 1, w = noticeW, h = 25, textSize = 14},
        toastScale = math.min(1, (width - 20) / 440),
    }
end

function TouchLayout.compute(params: {width: number, height: number, touch: boolean, navCount: number, thumb: Rect?, jump: Rect?})
    local width, height, count = params.width, params.height, params.navCount
    if not params.touch then return desktop(width, height, count) end
    local target, m = Config.TouchMinTargetPx, Config.TouchSafeMargin
    local s = clamp(math.min(width / 1000, height / 560), 0.55, 1)
    local thumb, corner = TouchLayout.reservedZones(width, height, params.thumb, params.jump)

    -- Top-left status HUD: stays above the thumbstick zone.
    local hudScale = math.min(1, math.max(s, Config.TouchMinHudScale), (thumb.y - 2 * m) / TouchLayout.HUD.h)
    local crystalScale = math.max(0.65, s)
    local hud, crystal, rail
    for attempt = 1, 2 do
        if attempt == 2 then
            -- Narrow phones: compact status widgets to their floor before shrinking buttons.
            hudScale = math.min(hudScale, 0.55)
            crystalScale = 0.55
        end
        hud = {x = m, y = m, scale = hudScale, w = TouchLayout.HUD.w, h = TouchLayout.HUD.h}
        crystal = {x = width - m - TouchLayout.CRYSTAL.w * crystalScale, y = m, scale = crystalScale, w = TouchLayout.CRYSTAL.w, h = TouchLayout.CRYSTAL.h}
        local left = hud.x + hud.w * hudScale + m
        local available = crystal.x - m - left
        local gap = 4
        -- One row of navigation buttons between HUD and wallet, else a 2-row grid.
        for _, rows in {1, 2} do
            local columns = math.ceil(count / rows)
            local bh = if rows == 1 then math.max(target + 8, math.round(56 * s)) else target
            local bw = math.min(132, math.floor((available - (columns + 1) * gap) / columns))
            local railW = columns * bw + (columns + 1) * gap
            local railH = rows * bh + (rows + 1) * gap
            if bw >= target and m + railH <= thumb.y then
                rail = {x = left + (available - railW) / 2, y = m, scale = 1, w = railW, h = railH,
                    button = buttonContent(bw, bh), positions = railButtons(count, columns, bw, bh, gap), rows = rows}
                rail.button.w, rail.button.h = bw, bh
                break
            end
        end
        if rail then break end
    end
    if not rail then
        -- Last resort (very narrow canvas): minimum-size grid, verified by tests not to be hit.
        local columns = math.ceil(count / 2)
        local railW = columns * target + (columns + 1) * 4
        rail = {x = (width - railW) / 2, y = m, scale = 1, w = railW, h = 2 * target + 12,
            button = buttonContent(target, target), positions = railButtons(count, columns, target, target, 4), rows = 2}
        rail.button.w, rail.button.h = target, target
    end

    -- Right column above the jump corner: weather on top, LEAP nearest the right thumb.
    local timersScale = math.max(target / TouchLayout.LEAP_H, s)
    local columnX = width - m - TouchLayout.TIMERS_W * timersScale
    local top = crystal.y + crystal.h * crystal.scale + m
    if rail.x + rail.w > columnX then top = math.max(top, rail.y + rail.h + m) end
    local bottom = corner.y - 1 -- 1 px guard against float rounding at the shared edge
    local designH = math.min(220, (bottom - top) / timersScale)
    local leapY = designH - TouchLayout.LEAP_H
    local weatherVisible = leapY >= TouchLayout.WEATHER_H + 6
    local buffsY = TouchLayout.WEATHER_H + 6
    local buffsH = math.min(TouchLayout.BUFFS_H, leapY - 6 - buffsY)
    local timers = {x = columnX, y = bottom - designH * timersScale, scale = timersScale, w = TouchLayout.TIMERS_W, h = designH,
        leapY = leapY, weatherY = 0, weatherVisible = weatherVisible, buffsY = leapY - 6 - math.max(buffsH, 0),
        buffsH = math.max(buffsH, 0), buffsVisible = weatherVisible and buffsH >= 30}

    -- Bottom-centre Home/Explore between the thumbstick zone and the jump corner.
    local actionScale = math.max(target / TouchLayout.ACTION.h, s)
    local halfSpace = math.min(width / 2 - (thumb.x + thumb.w) - m, corner.x - m - width / 2)
    local actionW = math.min(TouchLayout.ACTION.w, 2 * halfSpace / actionScale)
    local action = {x = width / 2 - actionW * actionScale / 2, y = height - m - TouchLayout.ACTION.h * actionScale,
        scale = actionScale, w = actionW, h = TouchLayout.ACTION.h}

    local badgeY = hud.y + hud.h * hud.scale + 2
    -- Studio-only preview notice: beside the build badge, or below it when the rail is in the way.
    local notice = {x = m + 154, y = badgeY, scale = 1, w = 230, h = 16, textSize = 12}
    if TouchLayout.overlaps(TouchLayout.rendered(notice), {x = rail.x, y = rail.y, w = rail.w, h = rail.h}) then
        notice.x, notice.y = m, badgeY + 18
    end
    return {
        touch = true,
        reserved = {thumb = thumb, jump = corner},
        crystal = crystal,
        hud = hud,
        rail = rail,
        timers = timers,
        action = action,
        badge = {x = m, y = badgeY, scale = 1, w = 150, h = 16, textSize = 12},
        notice = notice,
        toastScale = math.min(1, (width - 20) / 440),
    }
end

return TouchLayout
