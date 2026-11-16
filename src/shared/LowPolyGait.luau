--!strict
-- BD-1217 rig follow-up (Config.DinoRigClipsEnabled, docs/242 benchmark gap 2): the low-poly dinos idle, walk and run with AUTHORED loops
-- (Shared/LowPolyClips.Gait, keys in tools/blender/dino_clips.py) instead of the sine poses of LowPolyPose.sample, plus follow-through: the
-- tail and the head lag behind turns, take-offs and landings on a soft spring. Pure (no Roblox types): tools/verify_lowpoly_gait.py runs it.
--
-- Still driven by the real movement: the animator's step phase advances with the planar speed (LowPolyPose.stepRate) and is the clock of the
-- walk and run loops, the eased speed blends idle -> walk -> run, the humanoid state picks the jump and landing (LowPolyAnimator). Water dinos,
-- wings and flippers keep the sine poses (rowing, folded wings); the body never turns (one shared bob moves every part, nothing slides).
-- Reduce Motion (amp 0): every offset and the springs are exactly 0.
local Clips = require(script.Parent.LowPolyClips)

local Gait = {}
Gait.Roles = {head = true, neck = true, tail = true, arm = true, leg = true}
Gait.WalkFrom = 0.25 -- speed01 at which the walk loop is fully in (below: blends from idle)
Gait.RunFrom, Gait.RunFull = 0.45, 0.8 -- speed01 band in which the walk blends into the run
Gait.ArmoredStride = 0.8 -- Armored dinos take shorter steps (same as LowPolyPose)
Gait.MaxAngle = 0.9 -- LowPolyPose.MaxAngle
Gait.MaxBob = 0.04 -- LowPolyPose.MaxBob
Gait.PeckStuds = 0.4 -- LowPolyPose.PeckStuds: the head never reaches further forward than the sine peck did

local function finite(x: number): number return if x == x and math.abs(x) < 1e6 then x else 0 end
local function smooth(u: number): number u = math.clamp(u, 0, 1) return u * u * (3 - 2 * u) end

-- true when this role of this class plays the authored loops (false = keep LowPolyPose.sample)
function Gait.uses(role: string, class: string?): boolean
    return class ~= "Water" and Gait.Roles[role] == true
end

-- idle, walk, run weights for an eased speed01 (they add up to 1)
function Gait.weights(speed01: number): (number, number, number)
    local w = math.clamp(finite(speed01), 0, 1)
    local g = smooth(w / Gait.WalkFrom)
    local r = smooth((w - Gait.RunFrom) / (Gait.RunFull - Gait.RunFrom))
    return 1 - g, g * (1 - r), g * r
end

-- part of a stride by which this limb runs behind the reference leg (left front): the right side half a stride later, a back leg of a
-- quadruped (lead false) another half (so the diagonal pairs move together, like LowPolyPose)
function Gait.offset(role: string, side: number, lead: boolean): number
    if role == "leg" then return ((if side < 0 then 0 else 0.5) + (if lead then 0 else 0.5)) % 1 end
    if role == "arm" then return if side < 0 then 0 else 0.5 end
    return 0
end

export type Out = {pitch: number, roll: number, yaw: number, dy: number, dz: number, fwd: number}
local tmp = Clips.new()

-- Writes one part's loop pose into out (the LowPolyPose.Out shape; fwd in studs, dy / dz 0). t = clock seconds (idle loop), phase = the
-- animator's step phase in radians (one stride = 2 pi), speed01 eased, amp 0..1 (Reduce Motion = 0), height = dino height in studs.
function Gait.sample(role: string, side: number, lead: boolean, t: number, phase: number, speed01: number, amp: number, height: number, out: Out, class: string?): Out
    out.pitch, out.roll, out.yaw, out.dy, out.dz, out.fwd = 0, 0, 0, 0, 0, 0
    local a = math.clamp(finite(amp), 0, 1)
    if a == 0 or not Gait.Roles[role] then return out end
    t, phase = finite(t), finite(phase)
    local wi, ww, wr = Gait.weights(speed01)
    local u = phase / (2 * math.pi) + Gait.offset(role, side, lead)
    local pitch, roll, yaw, fwd = 0, 0, 0, 0
    for _, item in {{"idle", t, wi}, {"walk", u, ww}, {"run", u, wr}} do
        local k = item[3] :: number
        if k > 1e-4 then
            Clips.sampleCycle(item[1] :: string, role, side, item[2] :: number, tmp)
            pitch += tmp.pitch * k
            roll += tmp.roll * k
            yaw += tmp.yaw * k
            fwd += tmp.fwd * k
        end
    end
    if role == "leg" and class == "Armored" then pitch *= Gait.ArmoredStride end
    out.pitch = math.clamp(finite(pitch) * a, -Gait.MaxAngle, Gait.MaxAngle)
    out.roll = math.clamp(finite(roll) * a, -Gait.MaxAngle, Gait.MaxAngle)
    out.yaw = math.clamp(finite(yaw) * a, -Gait.MaxAngle, Gait.MaxAngle)
    out.fwd = math.clamp(finite(fwd) * finite(height) * a, 0, Gait.PeckStuds)
    return out
end

-- whole-dino lift (fraction of the height, never below 0, at most MaxBob) of the blended loops
function Gait.bob(t: number, phase: number, speed01: number, amp: number): number
    local a = math.clamp(finite(amp), 0, 1)
    if a == 0 then return 0 end
    local wi, ww, wr = Gait.weights(speed01)
    local u = finite(phase) / (2 * math.pi)
    local b = Clips.sampleCycle("idle", "root", 1, finite(t), tmp).bob * wi
        + Clips.sampleCycle("walk", "root", 1, u, tmp).bob * ww + Clips.sampleCycle("run", "root", 1, u, tmp).bob * wr
    return math.clamp(finite(b) * a, 0, Gait.MaxBob)
end

-- ---------------------------------------------------------------------------------------------------------------- follow-through
-- One damped spring per channel (underdamped: the tail swings past and settles, like a real tail). Targets: turning (yaw rate, rad/s,
-- > 0 = turning left) swings the tail OUT of the turn and the head INTO it; rising drags the tail tip down and the nose a little down, falling
-- lifts them; a landing kicks the tail down and the head into a nod that springs back. Signs as LowPolyClips: head pitch > 0 = nose up,
-- tail pitch > 0 = tail tip down, yaw > 0 = tip / nose to the dino's left... the spring itself is sign-free.
Gait.Follow = {
    stiffness = 11, -- rad/s natural frequency
    damping = 0.45, -- ratio (< 1 overshoots a little)
    tailYawPerTurn = 0.06, headYawPerTurn = 0.035, -- rad per rad/s of turning
    tailPitchPerRise = 0.006, headPitchPerRise = -0.003, -- rad per stud/s of vertical speed
    tailLandKick = 0.03, headLandKick = -0.02, -- rad/s per stud/s of landing speed (soft: the procedural squash also lands)
    max = 0.4, -- rad, every channel
}
local CHANNELS = {"tailYaw", "tailPitch", "headYaw", "headPitch"}

export type Follow = {[string]: number}
function Gait.newFollow(): Follow
    return {tailYaw = 0, tailYawV = 0, tailPitch = 0, tailPitchV = 0, headYaw = 0, headYawV = 0, headPitch = 0, headPitchV = 0}
end

-- Advances the springs by dt (sub-stepped at 1/60 s, dt capped at 0.25 s). turnRate rad/s, vy studs/s, landSpeed = studs/s of the touch-down
-- this frame (0 when none). amp 0 = everything back to exact rest.
function Gait.stepFollow(f: Follow, dt: number, turnRate: number, vy: number, landSpeed: number, amp: number)
    local a = math.clamp(finite(amp), 0, 1)
    if a == 0 then
        for _, c in CHANNELS do f[c], f[c .. "V"] = 0, 0 end
        return
    end
    local F = Gait.Follow
    local turn, rise = math.clamp(finite(turnRate), -12, 12), math.clamp(finite(vy), -80, 80)
    local land = math.clamp(finite(landSpeed), 0, 80)
    local target = {
        tailYaw = math.clamp(turn * F.tailYawPerTurn, -F.max, F.max), headYaw = math.clamp(turn * F.headYawPerTurn, -F.max, F.max),
        tailPitch = math.clamp(rise * F.tailPitchPerRise, -F.max, F.max), headPitch = math.clamp(rise * F.headPitchPerRise, -F.max, F.max),
    }
    if land > 0 then
        f.tailPitchV += land * F.tailLandKick
        f.headPitchV += land * F.headLandKick
    end
    local left = math.clamp(finite(dt), 0, 0.25)
    local k, c = F.stiffness * F.stiffness, 2 * F.damping * F.stiffness
    while left > 1e-6 do
        local h = math.min(left, 1 / 60)
        left -= h
        for _, ch in CHANNELS do
            local v = f[ch .. "V"] + (k * (target[ch] - f[ch]) - c * f[ch .. "V"]) * h -- semi-implicit Euler: stable at 60 Hz for these rates
            f[ch .. "V"] = v
            f[ch] = math.clamp(f[ch] + v * h, -F.max, F.max)
        end
    end
end

-- Adds the follow-through of this role to out (head; neck at LowPolyClips.NeckShare; tail). Other roles unchanged.
function Gait.addFollow(f: Follow, role: string, amp: number, out: Out): Out
    local a = math.clamp(finite(amp), 0, 1)
    if a == 0 then return out end
    if role == "tail" then
        out.yaw += f.tailYaw * a
        out.pitch += f.tailPitch * a
    elseif role == "head" or role == "neck" then
        local k = if role == "neck" then Clips.NeckShare else 1
        out.yaw += f.headYaw * a * k
        out.pitch += f.headPitch * a * k
    end
    return out
end

-- turn rate (rad/s, > 0 = left) between two facing angles (radians, atan2 of the look vector) over dt; wraps across +-pi
function Gait.turnRate(prevYaw: number, yaw: number, dt: number): number
    if dt <= 0 or prevYaw ~= prevYaw or yaw ~= yaw then return 0 end
    local d = (yaw - prevYaw + math.pi) % (2 * math.pi) - math.pi
    return finite(d / dt)
end

return Gait
