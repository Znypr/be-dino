--!strict
-- BD-149 pure inspect math: drag threshold, yaw, inertia, idle spin, zoom limits. No Instances or services, so
-- tools/verify_inspect.py can run it offline. src/client/InspectView.luau feeds it pointer events and applies the
-- yaw/zoom to the preview camera (PreviewCamera reads the InspectYaw / InspectZoom attributes).
local M = {}

M.DragThreshold = 12 -- px of movement before a press counts as a drag; below it the press is still a TAP
M.RadiansPerPixel = .012 -- ~520 px of drag = one full turn
M.MaxSpin = 9 -- rad/s cap for a flick
M.Decay = 3.2 -- inertia: velocity *= exp(-Decay * dt); settles in about a second
M.StopSpeed = .05 -- rad/s below which inertia stops
M.IdleSpin = .5 -- rad/s slow turntable until the first touch
M.MinZoom, M.MaxZoom = .75, 2
M.WheelStep = .12
M.TAU = math.pi * 2

function M.new()
    return {yaw = 0, vel = 0, zoom = 1, touched = false, dragging = false, moved = false, dragged = false,
        startX = 0, startY = 0, lastX = 0, lastT = 0}
end

function M.clampZoom(z: number): number
    if z ~= z then return 1 end
    return math.clamp(z, M.MinZoom, M.MaxZoom)
end

function M.wrap(yaw: number): number
    local r = yaw % M.TAU
    if r ~= r then return 0 end
    return r
end

-- A press starts. The first press ends the idle auto-spin and kills any inertia.
function M.press(s, x: number, y: number, t: number)
    s.dragging, s.moved, s.touched = true, false, true
    s.startX, s.startY, s.lastX, s.lastT, s.vel = x, y, x, t, 0
    s.dragged = false
end

-- Pointer moves. Returns true when this move rotated the dino. Nothing rotates until the pointer left the
-- 12 px threshold circle, and rotation starts from where it crossed (no jump).
function M.move(s, x: number, y: number, t: number): boolean
    if not s.dragging then return false end
    if not s.moved then
        local dx, dy = x - s.startX, y - s.startY
        if dx * dx + dy * dy < M.DragThreshold * M.DragThreshold then return false end
        s.moved, s.dragged = true, true
        s.lastX, s.lastT = x, t
        return false
    end
    local dx = x - s.lastX
    local dt = math.max(t - s.lastT, 1 / 240)
    s.yaw = M.wrap(s.yaw + dx * M.RadiansPerPixel)
    local instant = dx * M.RadiansPerPixel / dt
    s.vel = math.clamp(s.vel * .5 + instant * .5, -M.MaxSpin, M.MaxSpin) -- smoothed flick speed
    s.lastX, s.lastT = x, t
    return true
end

-- Release. A press that never left the threshold is a tap (returns "tap"); otherwise "drag". Inertia only with
-- motion enabled and when the finger was still moving at release (held still = no fling).
function M.release(s, t: number, motion: boolean): string
    local wasDrag = s.moved
    s.dragging = false
    if not wasDrag then s.vel = 0 return "tap" end
    if not motion or t - s.lastT > .12 then s.vel = 0 end
    return "drag"
end

-- True while the current/last gesture was a drag. HatchSequence uses it so a drag never advances the egg.
function M.consumedTap(s): boolean return s.dragged end

-- Advance by dt. motion=false: no inertia and no idle spin, yaw only changes while dragging.
function M.step(s, dt: number, motion: boolean): boolean
    if s.dragging then return false end
    local before = s.yaw
    if motion and s.vel ~= 0 then
        s.yaw = M.wrap(s.yaw + s.vel * dt)
        s.vel *= math.exp(-M.Decay * dt)
        if math.abs(s.vel) < M.StopSpeed then s.vel = 0 end
    elseif not motion then
        s.vel = 0
    end
    if motion and not s.touched then s.yaw = M.wrap(s.yaw + M.IdleSpin * dt) end
    return s.yaw ~= before
end

function M.wheel(s, delta: number)
    s.zoom = M.clampZoom(s.zoom * (1 + M.WheelStep * delta))
end

-- scale = pinch distance / distance when the pinch started.
function M.pinch(s, startZoom: number, scale: number)
    s.zoom = M.clampZoom(startZoom * scale)
end

function M.reset(s)
    s.yaw, s.vel, s.zoom, s.dragging = 0, 0, 1, false
end

-- The reset button only matters once the view differs from the default.
function M.changed(s): boolean
    return math.abs(s.zoom - 1) > .001 or (s.yaw > .01 and s.yaw < M.TAU - .01)
end

return M
