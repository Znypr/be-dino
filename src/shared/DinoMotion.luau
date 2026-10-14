--!strict
-- BD-079 pure procedural action curves for the visual dino model. No Roblox APIs here, so the
-- bounds / determinism / return-to-rest rules are unit tested (tools/verify_dino_motion.py).
-- All offsets are dimensionless fractions of the model's own bounding box, so BIG/large scales
-- need no special casing. Pose axes are root-relative: -Z is forward, +pitch = nose up.
local DinoMotion = {}

DinoMotion.MinScale = 0.6
DinoMotion.MaxScale = 1.4
DinoMotion.MaxOffset = 0.35
DinoMotion.MaxAngle = 1.6
DinoMotion.MaxLean = 0.25
DinoMotion.Duration = {eat = 0.18, takeoff = 0.22, land = 0.28, leap = 0.5, bite = 0.22, death = 0.4,
    grow = 0.35, windup = 0.08} -- grow/windup: movement-feel additions (PROVISIONAL)
local SLOTS = {"eat", "takeoff", "land", "leap", "bite", "death", "grow", "windup"}
DinoMotion.Kinds = SLOTS

export type Pose = {sx: number, sy: number, sz: number, pitch: number, roll: number, fx: number, dy: number, fade: number}
export type State = {start: {[string]: number}, power: {[string]: number}, lean: number, dead: boolean}

function DinoMotion.newPose(): Pose
    return {sx = 1, sy = 1, sz = 1, pitch = 0, roll = 0, fx = 0, dy = 0, fade = 0}
end

function DinoMotion.new(): State
    return {start = {}, power = {}, lean = 0, dead = false}
end

local function clamp(v: number, lo: number, hi: number): number
    if v ~= v then return (lo + hi) / 2 end -- NaN guard
    return if v < lo then lo elseif v > hi then hi else v
end

-- Restarting the same kind replaces it (no stacking), so spam can never grow the state.
function DinoMotion.trigger(state: State, kind: string, now: number, power: number?)
    if state.dead or DinoMotion.Duration[kind] == nil then return end
    state.start[kind] = now
    state.power[kind] = clamp(power or 1, 0, 1)
    if kind == "death" then state.dead = true end
end

function DinoMotion.cancel(state: State, kind: string)
    state.start[kind] = nil
end

-- Client-side growth tween: the replicated model is already at its new size, so the displayed
-- factor starts at (old/new) and eases out (cubic) back to 1 over Duration.grow. Returns the
-- factor currently displayed, so a new pickup mid-tween continues from it without a step.
function DinoMotion.growFactor(state: State, now: number): number
    local start = state.start.grow
    if not start then return 1 end
    local u = clamp((now - start) / DinoMotion.Duration.grow, 0, 1)
    local v = (1 - u) * (1 - u) * (1 - u)
    return 1 - (state.power.grow or 0) * v
end

function DinoMotion.clear(state: State)
    for _, kind in SLOTS do state.start[kind] = nil end
    state.lean = 0
    state.dead = false
end

-- Smoothed bank angle from yaw rate (rad/s) and horizontal speed (studs/s).
function DinoMotion.lean(previous: number, yawRate: number, speed: number, dt: number): number
    if yawRate ~= yawRate or speed ~= speed or dt ~= dt then return 0 end
    local moving = clamp(speed / 8, 0, 1)
    local target = clamp(-yawRate * 0.08, -DinoMotion.MaxLean, DinoMotion.MaxLean) * moving
    local blend = 1 - math.exp(-clamp(dt, 0, 0.25) * 10)
    local nextLean = previous + (target - previous) * blend
    if math.abs(nextLean) < 1e-3 and math.abs(target) < 1e-3 then return 0 end
    return clamp(nextLean, -DinoMotion.MaxLean, DinoMotion.MaxLean)
end

local function ease(u: number): number return u * u * (3 - 2 * u) end

-- Writes the combined pose into `out`. Returns true while any action/lean is non-rest; when false
-- `out` is EXACTLY the rest pose (1,1,1,0,0,0,0,0).
function DinoMotion.sample(state: State, now: number, out: Pose): boolean
    local sx, sy, sz, pitch, roll, fx, dy, fade = 1, 1, 1, 0, 0, 0, 0, 0
    local active = false
    for _, kind in SLOTS do
        local start = state.start[kind]
        if start then
            local duration = DinoMotion.Duration[kind]
            local u = (now - start) / duration
            local p = state.power[kind] or 1
            if u < 0 then u = 0 end
            if kind == "death" then
                active = true
                local e = ease(math.min(u, 1))
                roll += 1.35 * e * p
                local s = 1 - 0.4 * e
                sx *= s sy *= s sz *= s
                dy -= 0.15 * e
                fade = math.max(fade, e)
            elseif u >= 1 then
                state.start[kind] = nil
            else
                active = true
                if kind == "eat" then
                    local v = math.sin(2 * math.pi * u) * (1 - u) * p
                    sy *= 1 + 0.12 * v sx *= 1 - 0.06 * v sz *= 1 - 0.06 * v
                elseif kind == "takeoff" then
                    local v = math.sin(math.pi * u) * (1 - 0.3 * u) * p
                    sy *= 1 + 0.16 * v sx *= 1 - 0.07 * v sz *= 1 - 0.07 * v
                elseif kind == "land" then
                    local v = math.sin(math.pi * u) * (1 - u) * p
                    sy *= 1 - 0.18 * v sx *= 1 + 0.09 * v sz *= 1 + 0.09 * v
                    dy -= 0.02 * v
                elseif kind == "leap" then
                    local v = math.sin(math.pi * u) * p
                    sz *= 1 + 0.3 * v sy *= 1 - 0.1 * v sx *= 1 - 0.08 * v
                    pitch += 0.15 * v
                elseif kind == "grow" then
                    local v = (1 - u) * (1 - u) * (1 - u)
                    local s = 1 - p * v
                    sx *= s sy *= s sz *= s
                elseif kind == "windup" then
                    local v = math.sin(math.pi * u) * p
                    sy *= 1 - 0.18 * v sx *= 1 + 0.08 * v sz *= 1 + 0.08 * v
                    dy -= 0.02 * v
                elseif kind == "bite" then
                    local v = math.sin(math.pi * u) * p
                    fx += 0.2 * v
                    pitch -= 0.12 * v
                    sz *= 1 + 0.08 * v
                end
            end
        end
    end
    if state.lean ~= 0 then
        active = true
        roll += state.lean
    end
    if not active then
        out.sx, out.sy, out.sz, out.pitch, out.roll, out.fx, out.dy, out.fade = 1, 1, 1, 0, 0, 0, 0, 0
        return false
    end
    out.sx = clamp(sx, DinoMotion.MinScale, DinoMotion.MaxScale)
    out.sy = clamp(sy, DinoMotion.MinScale, DinoMotion.MaxScale)
    out.sz = clamp(sz, DinoMotion.MinScale, DinoMotion.MaxScale)
    out.pitch = clamp(pitch, -DinoMotion.MaxAngle, DinoMotion.MaxAngle)
    out.roll = clamp(roll, -DinoMotion.MaxAngle, DinoMotion.MaxAngle)
    out.fx = clamp(fx, -DinoMotion.MaxOffset, DinoMotion.MaxOffset)
    out.dy = clamp(dy, -DinoMotion.MaxOffset, DinoMotion.MaxOffset)
    out.fade = clamp(fade, 0, 1)
    return true
end

return DinoMotion
