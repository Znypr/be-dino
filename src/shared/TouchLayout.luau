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
local PhoneScale = require(script.Parent.PhoneScale)
local TouchLayout = {}

export type Rect = {x: number, y: number, w: number, h: number}

TouchLayout.HUD = {w = 210, h = 64} -- BD-080: egg plate (was the 390 x 94 growth tile)
TouchLayout.CRYSTAL = {w = 260, h = 48}
TouchLayout.TIMERS_W = 286
TouchLayout.LEAP_H, TouchLayout.WEATHER_H, TouchLayout.BUFFS_H = 60, 62, 68
TouchLayout.ACTION = {w = 244, h = 60}
-- BD-507: the playtest "Tell us!" button (FeedbackClient). Fixed 120 x 48 design px, never scaled (48 >= the 44 px tap floor, 14+ px text).
-- Desktop: straight above the egg plate (x of the plate, 8 px gap), else right of it, so it never covers "EGGS N". Touch: bottom-left corner
-- (the egg plate is top-left there). Bootstrap publishes the rect as the FeedbackRect attribute of the BeDinoUI gui; FeedbackClient places itself on it.
TouchLayout.FEEDBACK = {w = 120, h = 48, gap = 8}
-- BD-531: the Studio/admin "Admin" button (AdminPanel). Desktop keeps its old top-left spot (14, 8); on the phone layout that spot is the
-- egg plate, so it goes in the bottom-left row next to Tell us! (never on a HUD piece). Bootstrap publishes it as the AdminRect attribute.
TouchLayout.ADMIN = {w = 120, h = 48, desktopX = 14, desktopY = 8}
-- BD-531: the hub Goals panel (GoalsPanel.luau): a 44 px tall header under the goal line, right edge on the wallet's right edge, at the scale
-- PhoneScale.floorScale gives (1:1 on phones). On the phone layout the FOLDED header is only as wide as the wallet (at least MinW), so it
-- never reaches under the rail; the panel grows to its 260 px width only while the player has it open. Bootstrap publishes the rect as GoalsRect.
TouchLayout.GOALS = {w = 260, h = 44, dy = 34, minW = 130}
-- BD-075: the collapsible objectives panel (ObjectivesPanel.luau), behind Config.ObjectivesEnabled. Real pixels, never scaled (44 px tall header
-- and buttons, text >= 14 px at 1:1). `objectives` is the FOLDED rect (always clear of every HUD piece), `objectivesOpen` is the rect while it is
-- open. Desktop: straight LEFT of the hub Goals panel (same top edge), clear of the open Goals panel too. Phone: under the rail, between the thumbstick
-- zone and the Goals header (the weather column starts under it); the open sheet is the one part that may cover the Goals header, the weather column
-- and the hub chip while the player has it open (everything else stays clear: tools/verify_movement_mobile.py). Bootstrap publishes both as the
-- ObjectivesRect / ObjectivesOpenRect attributes of the BeDinoUI gui.
-- rowH is the FIXED height of one task row (name, bar, count, prize or a centred 44 px CLAIM, no overlap); rowGap is the space between two rows (a divider sits in it).
TouchLayout.OBJECTIVES = {w = 300, minW = 190, h = 44, rowH = 60, rows = 3, gap = 4, deskGap = 8, rowGap = 4}
TouchLayout.GOALS_OPEN_H = 214 -- GoalsPanel unfolded: 44 + 2 + 3 x 56
function TouchLayout.objectivesOpenH(): number
    local O = TouchLayout.OBJECTIVES
    return O.h + 2 + O.rows * O.rowH + (O.rows - 1) * O.rowGap + 4
end
-- Desktop (not compact) hub Goals panel, mirroring GoalsPanel.luau's own formula (right edges aligned on the wallet, 34 px design under the goal line, 260 wide).
function TouchLayout.goalsDesktop(crystal): (Rect, Rect)
    local G = TouchLayout.GOALS
    local s = PhoneScale.floorScale(crystal.scale, G.h, 14)
    local x = crystal.x + crystal.w * crystal.scale - G.w * s
    local y = crystal.y + crystal.h * crystal.scale + TouchLayout.GOAL_GAP + G.dy * crystal.scale
    return {x = x, y = y, w = G.w * s, h = G.h * s}, {x = x, y = y, w = G.w * s, h = TouchLayout.GOALS_OPEN_H * s}
end
-- BD-538: the in-run SIZE bar and the one-line goal hint under it (HudV2) and the hub "Back to the middle" chip (HubTravelClient). They used to
-- sit at the screen centre on every canvas, which on a 667-wide phone put them 4 to 9 px under the weather/LEAP column. Both now come from
-- the layout: centred when clear, else slid left of the right-hand column. Sizes are design px (the bar and hint carry a UIScale); the chip
-- is 240 x 48, `bottom` px above the screen bottom (HubTravelClientRules.ChipBottom, asserted equal by tools/verify_movement_mobile.py).
TouchLayout.SIZEBAR = {w = 250, h = 34, hintW = 360, hintH = 28, hintDy = 38, gap = 4}
TouchLayout.CHIP = {w = 240, h = 48, bottom = 96, gap = 4}

-- BD-378: where the toast stack goes. The Crystals plate (top right) has the goal line ("Level 1: 0/100 XP") right under it;
-- the stack is TOAST.w wide, centred, and used to sit at y = 80 (y = 4 with a menu open), which covers both on any canvas
-- narrower than about 1000 px. walletPlates gives that rect from the layout; toastPlacement keeps the stack clear of it:
-- unchanged when it already is, else slid left of the plates (if it still fits on screen), else dropped below them.
TouchLayout.TOAST = {w = 440, h = 186, runY = 80, menuY = 4, gap = 8}
TouchLayout.GOAL_H, TouchLayout.GOAL_GAP = 30, 4 -- Bootstrap places the goal line at crystal.y + crystal.h * scale + GOAL_GAP, GOAL_H * scale tall
function TouchLayout.goalsRect(crystal): Rect
    local G = TouchLayout.GOALS
    local s = PhoneScale.floorScale(crystal.scale, G.h, 14)
    local w = math.max(crystal.w * crystal.scale, G.minW)
    local right = crystal.x + crystal.w * crystal.scale
    return {x = right - w, y = crystal.y + crystal.h * crystal.scale + TouchLayout.GOAL_GAP + G.dy * crystal.scale, w = w, h = G.h * s}
end
function TouchLayout.walletPlates(layout): Rect
    local c = layout.crystal
    local plates = {x = c.x, y = c.y, w = c.w * c.scale, h = c.h * c.scale + TouchLayout.GOAL_GAP + TouchLayout.GOAL_H * c.scale}
    local g = layout.goals -- BD-531: the hub Goals header hangs under the goal line and reaches further left than the wallet
    if g then
        local x, y = math.min(plates.x, g.x), math.min(plates.y, g.y)
        plates = {x = x, y = y, w = math.max(plates.x + plates.w, g.x + g.w) - x, h = math.max(plates.y + plates.h, g.y + g.h) - y}
    end
    local o = layout.objectives -- BD-075: the folded objectives pill is part of the top-right block too (the toast stack keeps clear of it)
    if o then
        local x, y = math.min(plates.x, o.x), math.min(plates.y, o.y)
        plates = {x = x, y = y, w = math.max(plates.x + plates.w, o.x + o.w) - x, h = math.max(plates.y + plates.h, o.y + o.h) - y}
    end
    return plates
end
-- Returns (x shift from the screen centre, top y). `shift` is the caller's own slide (the admin panel); `plates` may be nil.
function TouchLayout.toastPlacement(width: number, toastScale: number, plates: Rect?, menuOpen: boolean, shift: number): (number, number)
    local T = TouchLayout.TOAST
    local top = if menuOpen then T.menuY else T.runY
    if not plates then return shift, top end
    local w, h = T.w * toastScale, T.h * toastScale
    local function hits(centre: number, y: number): boolean
        return TouchLayout.overlaps({x = centre - w / 2, y = y, w = w, h = h}, plates)
    end
    if not hits(width / 2 + shift, top) then return shift, top end
    local centre = plates.x - T.gap - w / 2
    if shift == 0 and centre - w / 2 >= T.gap then return centre - width / 2, top end
    return shift, math.max(top, plates.y + plates.h + T.gap)
end

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
            labelW = bw - icon - 10, labelH = bh, textSize = clamp(math.floor((bw - icon - 10) / 4.8), PhoneScale.MinText, 17)}
    end
    if bw < PhoneScale.RailLabelW then
        -- BD-333: too narrow for a 14 px label (SETTINGS needs ~64 px): icon-only button, the label is hidden by Bootstrap.
        local icon = math.min(bw - 8, bh - 8)
        return {iconX = (bw - icon) / 2, iconY = (bh - icon) / 2, icon = icon, labelX = 0, labelY = 0, labelW = 0, labelH = 0,
            textSize = PhoneScale.MinText, iconOnly = true}
    end
    -- Phones: icon above a short label.
    local icon = math.min(math.floor(bh * 0.5), bw - 12)
    return {iconX = (bw - icon) / 2, iconY = 3, icon = icon, labelX = 0, labelY = icon + 3,
        labelW = bw, labelH = bh - icon - 5, textSize = clamp(math.floor((bw - 4) / 4.7), PhoneScale.MinText, 14)}
end

-- BD-538: SIZE bar + hint rects. `top` = y of the bar; `column` = the right-hand weather/LEAP column (or nil). Centred on the canvas unless a piece
-- would touch the column, then both slide left together (one common centre) so their right edge stops `gap` px before it.
local function sizeBarRects(width: number, top: number, scale: number, column: Rect?)
    local S = TouchLayout.SIZEBAR
    local bw, bh, hw, hh = S.w * scale, S.h * scale, S.hintW * scale, S.hintH * scale
    local hy = top + S.hintDy * scale
    local centre = width / 2
    if column then
        local limit = column.x - S.gap
        local c0 = centre
        if TouchLayout.overlaps({x = c0 - bw / 2, y = top, w = bw, h = bh}, column) then centre = math.min(centre, limit - bw / 2) end
        if TouchLayout.overlaps({x = c0 - hw / 2, y = hy, w = hw, h = hh}, column) then centre = math.min(centre, limit - hw / 2) end
    end
    centre = math.max(centre, hw / 2)
    return {x = centre - bw / 2, y = top, scale = scale, w = S.w, h = S.h}, {x = centre - hw / 2, y = hy, scale = scale, w = S.hintW, h = S.hintH}
end

-- BD-538: where the "Back to the middle" chip goes: bottom centre, or slid left until it stops short of the column / Goals header on its right.
local function chipRect(width: number, height: number, blockers: {Rect}): Rect
    local C = TouchLayout.CHIP
    local y = height - C.bottom - C.h
    local x = width / 2 - C.w / 2
    for _, b in blockers do
        if TouchLayout.overlaps({x = x, y = y, w = C.w, h = C.h}, b) then x = math.min(x, b.x - C.gap - C.w) end
    end
    return {x = math.max(x, Config.TouchSafeMargin), y = y, w = C.w, h = C.h}
end

local function feedbackRect(layout, width: number, height: number): Rect
    local F, hud = TouchLayout.FEEDBACK, layout.hud
    local hudR = TouchLayout.rendered(hud)
    if layout.touch then
        local m = Config.TouchSafeMargin
        return {x = m, y = height - m - F.h, w = F.w, h = F.h}
    end
    local blockers = {TouchLayout.rendered(layout.action), TouchLayout.rendered(layout.rail), TouchLayout.rendered(layout.timers),
        TouchLayout.rendered(layout.crystal)}
    local above = {x = hudR.x, y = hudR.y - F.gap - F.h, w = F.w, h = F.h}
    local beside = {x = hudR.x + hudR.w + F.gap, y = hudR.y + hudR.h - F.h, w = F.w, h = F.h}
    for _, candidate in {above, beside} do
        local clear = candidate.y >= 0 and candidate.x + candidate.w <= width
        for _, b in blockers do if TouchLayout.overlaps(candidate, b) then clear = false end end
        if clear then return candidate end
    end
    return above
end

local function desktop(width: number, height: number, count: number, objectives: boolean?)
    local small = clamp(math.min(width / 1000, height / 800), 0.3, 1)
    local crystalScale = math.max(0.65, small)
    local hud = {x = 18, y = height - 18 - TouchLayout.HUD.h * small, scale = small, w = TouchLayout.HUD.w, h = TouchLayout.HUD.h}
    local railH = count * 62 + 10
    local action = {x = 0, y = height - 22 - TouchLayout.ACTION.h * small, scale = small, w = TouchLayout.ACTION.w, h = TouchLayout.ACTION.h}
    action.x = math.max(width / 2 - action.w * small / 2, hud.x + hud.w * small + 12)
    local crystalX = width - 20 - TouchLayout.CRYSTAL.w * crystalScale
    local noticeW = math.min(500, 2 * (crystalX - 8 - width / 2))
    local result = {
        touch = false,
        feedback = {x = 0, y = 0, w = 0, h = 0} :: Rect, -- BD-507: filled below, once the rest of the layout is known
        admin = {x = TouchLayout.ADMIN.desktopX, y = TouchLayout.ADMIN.desktopY, w = TouchLayout.ADMIN.w, h = TouchLayout.ADMIN.h} :: Rect, -- BD-531: desktop spot unchanged
        reserved = {},
        crystal = {x = crystalX, y = 8, scale = crystalScale, w = TouchLayout.CRYSTAL.w, h = TouchLayout.CRYSTAL.h},
        hud = hud,
        rail = {x = 14, y = height / 2 - railH * small / 2, scale = small, w = 186, h = railH,
            button = {w = 172, h = 54, iconX = 5, iconY = 6, icon = 40, labelX = 52, labelY = 0, labelW = 114, labelH = 54, textSize = 19},
            positions = railButtons(count, 1, 172, 54, 7) :: any},
        timers = {x = width - 20 - TouchLayout.TIMERS_W * small, y = height - 22 - 220 * small, scale = small, w = TouchLayout.TIMERS_W, h = 220,
            leapY = 0, weatherY = 72, weatherVisible = true, buffsY = 145, buffsH = 68, buffsVisible = true,
            leapText = PhoneScale.floorText(22, small), weatherText = PhoneScale.floorText(20, small), buffsText = PhoneScale.floorText(16, small)}, -- BD-376: >= 14 px rendered
        action = action,
        badge = {x = width / 2 - 125, y = 36, scale = 1, w = 250, h = 24, textSize = 15},
        notice = {x = width / 2 - noticeW / 2, y = 8, scale = 1, w = noticeW, h = 25, textSize = 14},
        toastScale = math.min(1, (width - 20) / 440),
    }
    result.feedback = feedbackRect(result, width, height) -- BD-507
    if objectives then -- BD-075: left of the hub Goals panel, same top edge, clear of the rail and of the OPEN Goals panel
        local O = TouchLayout.OBJECTIVES
        local g, gOpen = TouchLayout.goalsDesktop(result.crystal)
        result.goalsPanel, result.goalsPanelOpen = g, gOpen
        local railRight = result.rail.x + result.rail.w * small
        local right = g.x - O.deskGap
        local x = math.max(right - O.w, railRight + O.deskGap)
        local y = g.y
        if right - x < O.minW then x, y = math.max(g.x + g.w - O.w, railRight + O.deskGap), g.y + gOpen.h + O.deskGap end -- tiny desktop: under the open Goals panel
        local w = math.min(O.w, g.x + g.w - x)
        if y == g.y then w = right - x end
        result.objectives = {x = x, y = y, w = w, h = O.h}
        result.objectivesOpen = {x = x, y = y, w = w, h = TouchLayout.objectivesOpenH()}
    end
    local barScale = clamp(hud.scale, 0.7, 1) -- BD-538: the SIZE bar sits under the build badge at y 64 (HudV2 used to compute this itself)
    result.sizeBar, result.sizeHint = sizeBarRects(width, 64, barScale, TouchLayout.rendered(result.timers))
    result.chip = chipRect(width, height, {TouchLayout.rendered(result.timers)})
    return result
end

-- `goals` (BD-531): true while the hub Goals header is on screen (out of a run, after the first egg); the right-hand column then starts under it.
-- `objectives` (BD-075): true while the objectives pill is on screen (same condition as `goals`, and Config.ObjectivesEnabled); nil/false = nothing changes.
function TouchLayout.compute(params: {width: number, height: number, touch: boolean, navCount: number, thumb: Rect?, jump: Rect?, goals: boolean?, objectives: boolean?})
    local width, height, count = params.width, params.height, params.navCount
    -- BD-333: a short canvas (phone landscape) always gets the phone layout, even when Studio/PC reports a mouse.
    if not (params.touch or PhoneScale.isCompact(height)) then return desktop(width, height, count, params.objectives) end
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
            crystalScale = 0.6 -- BD-333: 24 px design text stays >= 14 px (was 0.55 = 13 px)
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

    local badgeY = hud.y + hud.h * hud.scale + 2
    -- Studio-only preview notice: beside the build badge, or below it when the rail is in the way.
    local notice = {x = m + 154, y = badgeY, scale = 1, w = 230, h = 20, textSize = PhoneScale.MinText}
    if TouchLayout.overlaps(TouchLayout.rendered(notice), {x = rail.x, y = rail.y, w = rail.w, h = rail.h}) then
        notice.x, notice.y = m, badgeY + 22
        -- Seven nav buttons give a wider rail: keep the (short, touch) notice left of it.
        notice.w = math.max(60, math.min(notice.w, rail.x - m - notice.x - 1)) -- BD-080: floor 60, Bootstrap scales the text to fit
    end
    local badge = {x = m, y = badgeY, scale = 1, w = math.max(60, math.min(150, rail.x - m - 2)), h = 20, textSize = PhoneScale.MinText} -- BD-080: the compact egg plate leaves less room before the rail

    -- Right column above the jump corner: weather on top, LEAP nearest the right thumb.
    local timersScale = math.max(target / TouchLayout.LEAP_H, s)
    local columnX = width - m - TouchLayout.TIMERS_W * timersScale
    local top = crystal.y + crystal.h * crystal.scale + m
    if rail.x + rail.w > columnX then top = math.max(top, rail.y + rail.h + m) end
    local goals: Rect? = if params.goals then TouchLayout.goalsRect(crystal) else nil
    if goals and goals.x < rail.x + rail.w and rail.x < goals.x + goals.w and goals.y < rail.y + rail.h + m then
        goals.y = rail.y + rail.h + m -- BD-531: on a narrow canvas the header reaches under the rail: it starts below the rail (GoalsPanel follows the GoalsRect attribute)
    end
    if goals and goals.x + goals.w > columnX then top = math.max(top, goals.y + goals.h + m) end -- BD-531: weather/leap never sit under the Goals header
    -- Bottom-centre Home/Explore between the thumbstick zone and the jump corner.
    local actionScale = math.max(target / TouchLayout.ACTION.h, s)
    local halfSpace = math.min(width / 2 - (thumb.x + thumb.w) - m, corner.x - m - width / 2)
    local actionW = math.min(TouchLayout.ACTION.w, 2 * halfSpace / actionScale)
    local action = {x = width / 2 - actionW * actionScale / 2, y = height - m - TouchLayout.ACTION.h * actionScale,
        scale = actionScale, w = actionW, h = TouchLayout.ACTION.h}

    -- BD-075: the objectives pill. Under the rail, left of the Goals header, right of the badge / notice and (where it reaches down into it) the thumbstick zone.
    local objectives: Rect?, objectivesOpen: Rect? = nil, nil
    if params.objectives then
        local O = TouchLayout.OBJECTIVES
        local y0 = if goals then goals.y else crystal.y + crystal.h * crystal.scale + TouchLayout.GOAL_GAP + TouchLayout.GOAL_H * crystal.scale + m
        y0 = math.max(y0, rail.y + rail.h * rail.scale + O.gap)
        local right = (if goals then goals.x else crystal.x) - O.gap
        local left = m
        if y0 + O.h > thumb.y then left = math.max(left, thumb.x + thumb.w + O.gap) end
        for _, b in {TouchLayout.rendered(hud), TouchLayout.rendered(badge), TouchLayout.rendered(notice)} do
            if b.y < y0 + O.h and y0 < b.y + b.h and b.x < right then left = math.max(left, b.x + b.w + O.gap) end
        end
        if y0 + O.h > top and right > columnX and columnX - O.gap - left >= O.minW then right = columnX - O.gap end -- narrow the pill before pushing the column down
        local w = math.min(O.w, right - left)
        objectives = {x = right - w, y = y0, w = w, h = O.h}
        if y0 + O.h > top and objectives.x + objectives.w > columnX then top = y0 + O.h + m end -- the weather column starts under the pill
        -- The open sheet grows right and down from the pill, never into the thumbstick zone's columns, the jump corner or Home.
        local openH = TouchLayout.objectivesOpenH()
        local sheetLeft = math.max(m, thumb.x + thumb.w + O.gap)
        local sheetRight = width - m
        if y0 + openH > corner.y then sheetRight = math.min(sheetRight, corner.x - O.gap) end
        local x0 = math.max(sheetLeft, math.min(objectives.x, sheetRight - O.w))
        local sw = math.min(O.w, sheetRight - x0)
        local sh = math.min(openH, height - m - y0)
        if x0 < action.x + action.w * action.scale and action.x < x0 + sw then sh = math.min(sh, action.y - O.gap - y0) end
        objectivesOpen = {x = x0, y = y0, w = sw, h = math.max(sh, O.h)}
    end
    local bottom = corner.y - 1 -- 1 px guard against float rounding at the shared edge
    local designH = math.min(220, (bottom - top) / timersScale)
    local leapY = designH - TouchLayout.LEAP_H
    local weatherVisible = leapY >= TouchLayout.WEATHER_H + 6
    local buffsY = TouchLayout.WEATHER_H + 6
    local buffsH = math.min(TouchLayout.BUFFS_H, leapY - 6 - buffsY)
    -- BD-333: design text sizes that render >= 14 px under timersScale (secondary buffs text hides when two rows do not fit).
    local leapText = PhoneScale.floorText(22, timersScale)
    local weatherText = PhoneScale.floorText(20, timersScale)
    local buffsText = PhoneScale.floorText(16, timersScale)
    local timers = {x = columnX, y = bottom - designH * timersScale, scale = timersScale, w = TouchLayout.TIMERS_W, h = designH,
        leapY = leapY, weatherY = 0, weatherVisible = weatherVisible, buffsY = leapY - 6 - math.max(buffsH, 0),
        buffsH = math.max(buffsH, 0), buffsVisible = weatherVisible and buffsH >= buffsText * 2,
        leapText = leapText, weatherText = weatherText, buffsText = buffsText}

    local result = {
        touch = true,
        feedback = {x = 0, y = 0, w = 0, h = 0} :: Rect, -- BD-507: filled below, once the rest of the layout is known
        admin = {x = 0, y = 0, w = TouchLayout.ADMIN.w, h = TouchLayout.ADMIN.h} :: Rect, -- BD-531: filled below, next to Tell us!
        goals = goals,
        objectives = objectives, -- BD-075: nil unless params.objectives (flag off = no key)
        objectivesOpen = objectivesOpen,
        reserved = {thumb = thumb, jump = corner},
        crystal = crystal,
        hud = hud,
        rail = rail,
        timers = timers,
        action = action,
        badge = badge,
        notice = notice,
        toastScale = math.min(1, (width - 20) / 440),
    }
    result.feedback = feedbackRect(result, width, height) -- BD-507
    result.admin = {x = result.feedback.x + result.feedback.w + TouchLayout.FEEDBACK.gap, y = result.feedback.y, w = TouchLayout.ADMIN.w, h = TouchLayout.ADMIN.h} -- BD-531
    local column = TouchLayout.rendered(timers)
    local blockers = {column}
    if goals then table.insert(blockers, goals) end
    -- BD-538: SIZE bar under the rail (HudV2 used to compute this itself, centred), clear of the weather column; the hub chip clear of column and Goals header
    result.sizeBar, result.sizeHint = sizeBarRects(width, rail.y + rail.h * rail.scale + 4, clamp(rail.scale, 0.7, 1), column)
    result.chip = chipRect(width, height, blockers)
    return result
end

return TouchLayout
