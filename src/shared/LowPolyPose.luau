--!strict
-- BD-234 spike: pure procedural idle/walk pose per body part (no Roblox types, offline-testable).
-- Angles are radians about the part's own pivot (pitch = X, roll = Z, yaw = Y); dy/dz are fractions of the model height.
-- Idle: gentle breathing, slow head tilt, tail sway. Walk (chicken/dino mix): quick bob, alternating legs, head peck, tail counter-swing.
local Pose = {}
Pose.Roles = {"body", "head", "neck", "tail", "arm", "leg", "wing", "flipper"}
Pose.MaxAngle = 0.9
Pose.MaxFold = 1.5 -- a folded wing rests well past MaxAngle (hangs against the body)
Pose.FoldAngle = 1.25 -- roll of a folded wing, radians (BD-232 / docs/101 section 11: wings folded while walking)
-- BD-232: classify a generated part name (e.g. `"front left leg"_geom`, "left wing", "neck and head", "right flipper").
-- Pure so the offline verifier can run every species' part-name set. Order matters: a combined "neck and head" is a head.
function Pose.roleOf(name: string): string?
    local n = string.lower(name)
    for _, pair in {{"head", "head"}, {"tail", "tail"}, {"wing", "wing"}, {"flipper", "flipper"}, {"fin", "flipper"}, {"neck", "neck"},
        {"arm", "arm"}, {"leg", "leg"}, {"foot", "leg"}, {"body", "body"}, {"torso", "body"}} do
        if string.find(n, pair[1], 1, true) then return pair[2] end
    end
    return nil
end
Pose.MaxOffset = 0.08
export type Out = {pitch: number, roll: number, yaw: number, dy: number, dz: number}
function Pose.new(): Out return {pitch = 0, roll = 0, yaw = 0, dy = 0, dz = 0} end
-- Walk cycle speed: radians per second grows with speed01 (0..1 of max run speed), quick like a chicken.
function Pose.stepRate(speed01: number): number
    return 5 + 7 * math.clamp(speed01, 0, 1)
end
local function finite(x: number): number return if x == x and math.abs(x) < 1e6 then x else 0 end
-- class (optional, default Ground): Fly folds wings; Water stays low (smaller bob, shorter strokes); Armored takes shorter steps.
-- role: body/head/neck/tail/arm/leg/wing/flipper; side: -1/1 (x side); lead: true for a quadruped front leg (diagonal pairing); t: idle clock seconds;
-- phase: walk phase radians; speed01: 0 idle .. 1 full run; amp: 0..1 (Reduce Motion passes 0).
function Pose.sample(role: string, side: number, lead: boolean, t: number, phase: number, speed01: number, amp: number, out: Out, class: string?): Out
    t, phase = finite(t), finite(phase)
    local w = math.clamp(finite(speed01), 0, 1)
    local a = math.clamp(finite(amp), 0, 1)
    local idle = 1 - w
    local pitch, roll, yaw, dy, dz = 0, 0, 0, 0, 0
    local s = if side < 0 then -1 else 1
    local sw = math.sin(phase)
    local water, armored = class == "Water", class == "Armored"
    local stride = if water then 0.5 elseif armored then 0.8 else 1
    local fold = 0
    if role == "body" then
        dy = idle * math.sin(t * 1.7) * 0.012 + w * math.abs(sw) * (if water then 0.012 else 0.03)
        if water then dy -= 0.02 end -- stays low to the ground
        roll = w * sw * 0.07
        pitch = idle * math.sin(t * 1.7 + 0.6) * 0.012
    elseif role == "head" or role == "neck" then
        roll = idle * math.sin(t * 0.55) * 0.14 + w * -sw * 0.05
        yaw = idle * math.sin(t * 0.38 + 1) * 0.10
        local peck = math.sin(phase * 2 - 0.8)
        pitch = idle * math.sin(t * 1.7 + 1.1) * 0.02 + w * peck * 0.16
        dz = w * math.max(0, peck) * -0.03
    elseif role == "tail" then
        yaw = idle * math.sin(t * 0.9) * 0.22 + w * -sw * 0.30
        pitch = idle * math.sin(t * 0.7 + 2) * 0.04 + w * math.sin(phase * 2) * 0.05
    elseif role == "leg" then
        local lift = if lead then 0 else math.pi
        local swing = math.sin(phase + (if s < 0 then 0 else math.pi) + lift)
        pitch = w * swing * 0.65 * stride
        dy = w * math.max(0, swing) * 0.015
    elseif role == "arm" then
        pitch = idle * math.sin(t * 1.7 + 0.3) * 0.04 + w * math.sin(phase + (if s < 0 then math.pi else 0)) * 0.30
    elseif role == "flipper" then
        local row = math.sin(phase + (if s < 0 then math.pi else 0))
        pitch = idle * math.sin(t * 1.1 + 0.3) * 0.08 + w * row * 0.25 * stride
        roll = s * (idle * math.sin(t * 0.8) * 0.06 + w * row * 0.08)
    elseif role == "wing" then
        -- Folded close to the body like a walking bird/bat; only a tiny shuffle while idle or walking.
        fold = -s * Pose.FoldAngle
        roll = s * (idle * math.sin(t * 0.9 + s) * 0.04 + w * math.sin(phase * 2) * 0.06)
        pitch = w * math.sin(phase + 0.5) * 0.05
    end
    out.pitch = math.clamp(finite(pitch) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.roll = math.clamp(finite(roll) * a + fold, -Pose.MaxFold, Pose.MaxFold) -- the fold is posture, not motion: kept under Reduce Motion
    out.yaw = math.clamp(finite(yaw) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.dy = math.clamp(finite(dy) * a, -Pose.MaxOffset, Pose.MaxOffset)
    out.dz = math.clamp(finite(dz) * a, -Pose.MaxOffset, Pose.MaxOffset)
    return out
end
-- BD-233 spike: jump / leap / land / water-surge actions. Phases: crouch -> push (stretch) -> air (tuck, held until the dino lands) -> land (squash);
-- Water has no air time: a single "surge" (forward dash). Everything is calm and short (docs/87), absolute offsets from the REST pose, bounded.
Pose.Phases = {"crouch", "push", "air", "land", "surge"}
Pose.TuckTime = 0.18 -- seconds for the airborne tuck to settle
local CLASS_SCALE = { -- q = crouch/squash depth, s = push-off stretch, t = airborne tuck, l = landing squash
    Ground = {q = 1, s = 1, t = 1, l = 1}, Armored = {q = 1.3, s = 0.4, t = 0.5, l = 1.5},
    Fly = {q = 0.5, s = 0.7, t = 0.8, l = 0.6}, Water = {q = 0, s = 0, t = 0, l = 0}}
-- Seconds each timed phase lasts (air has no length: it lasts until landing). aggr: 0 jump, 1 leap.
function Pose.duration(phase: string, aggr: number, class: string?): number
    local armored, fly = class == "Armored", class == "Fly"
    if phase == "crouch" then return if armored then 0.12 else 0.08 end
    if phase == "push" then return if armored then 0.16 else 0.12 end
    if phase == "land" then return if armored then 0.42 elseif fly then 0.45 else 0.30 end
    if phase == "surge" then return 0.40 + 0.15 * math.clamp(finite(aggr), 0, 1) end
    return 0
end
local function ease(u: number): number u = math.clamp(u, 0, 1) return u * u * (3 - 2 * u) end
-- How strongly the action replaces the idle/walk pose: 0 at the start and at the very end so the hand-over is seamless.
function Pose.actionWeight(phase: string, p: number): number
    p = math.clamp(finite(p), 0, 1)
    if phase == "crouch" then return ease(p) end
    if phase == "land" then return 1 - ease(math.clamp((p - 0.5) / 0.5, 0, 1)) end
    if phase == "surge" then return ease(p / 0.15) * (1 - ease((p - 0.7) / 0.3)) end
    return 1
end
-- ctx: phase, p (0..1 progress of a timed phase), t (seconds since the phase began), aggr (0 jump .. 1 leap), carry (0..1 tuck amount when landing began).
export type Ctx = {phase: string, p: number, t: number, aggr: number, carry: number}
function Pose.newCtx(): Ctx return {phase = "crouch", p = 0, t = 0, aggr = 0, carry = 0} end
function Pose.sampleAction(role: string, side: number, lead: boolean, ctx: Ctx, amp: number, out: Out, class: string?): Out
    local a = math.clamp(finite(amp), 0, 1)
    local s = if side < 0 then -1 else 1
    local ph = ctx.phase
    local p, t = math.clamp(finite(ctx.p), 0, 1), math.max(0, finite(ctx.t))
    local aggr = math.clamp(finite(ctx.aggr), 0, 1)
    local cls = CLASS_SCALE[class or "Ground"] or CLASS_SCALE.Ground
    local q, st, tk, W, flap = 0, 0, 0, 0, 0 -- squash, stretch, tuck, wings open (0..1), wing flap
    local lunge, snap, kick = 0, 0, 0
    if class == "Water" then
        if ph == "surge" then
            lunge = math.sin(math.pi * p)
            snap = math.sin(math.pi * math.clamp((p - 0.3) / 0.4, 0, 1)) * aggr
            kick = math.sin(2 * math.pi * p) * math.sin(math.pi * p)
        end
    else
        if ph == "crouch" then q = ease(p) * cls.q
        elseif ph == "push" then q = (1 - ease(p)) * cls.q st = ease(p) * cls.s
        elseif ph == "air" then
            local e = ease(t / Pose.TuckTime)
            st, tk = (1 - e) * cls.s, e * cls.t
        elseif ph == "land" then
            local c = math.clamp(finite(ctx.carry), 0, 1)
            local d = ease(p / 0.25)
            tk = c * (1 - d) * cls.t
            q = d * (1 - ease((p - 0.25) / 0.75)) * cls.l
        end
        if class == "Fly" then
            if ph == "push" then W = ease(p) elseif ph == "air" then W = 1 elseif ph == "land" then W = 1 - ease(p) end
            if ph == "air" then flap = (1 - 0.8 * aggr) * math.sin(t * 11) * 0.35 -- a leap glides on nearly still wings
            elseif ph == "land" then flap = math.sin(t * 16) * 0.3 * (1 - p) end -- soft flutter landing
        end
    end
    local L = 1 + aggr
    local pitch, roll, yaw, dy, dz = 0, 0, 0, 0, 0
    if role == "body" then
        dy = -0.05 * q + 0.03 * st - 0.01 * lunge
        pitch = -0.05 * q + (0.10 + 0.06 * aggr) * st + 0.02 * tk - 0.06 * lunge
        dz = -0.02 * st * L - 0.045 * lunge * (1 + 0.6 * aggr)
    elseif role == "head" or role == "neck" then
        dy = -0.02 * q
        pitch = 0.18 * st * (1 + 0.5 * aggr) - 0.08 * tk + 0.10 * lunge - 0.35 * snap
        dz = -0.03 * st * L - 0.03 * lunge * L
    elseif role == "tail" then
        pitch = 0.15 * q - 0.20 * st + 0.12 * tk + 0.20 * lunge
        yaw = 0.45 * (1 + 0.5 * aggr) * kick
    elseif role == "leg" then
        pitch = 0.55 * q - 0.45 * st + 0.70 * tk
        dy = 0.01 * q
    elseif role == "arm" then
        pitch = 0.20 * q - 0.50 * st + 0.50 * tk
    elseif role == "flipper" then
        pitch = 0.5 * lunge
        roll = s * 0.3 * lunge
    end
    local fold = 0
    if role == "wing" then
        fold = -s * Pose.FoldAngle
        local open = fold * (1 - W) + W * (s * 0.15 + s * flap) -- from the folded rest to open; flaps while open
        roll = open - fold -- the fold itself is posture and stays under Reduce Motion
        pitch = -0.1 * W
    end
    out.pitch = math.clamp(finite(pitch) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.roll = math.clamp(finite(roll) * a + fold, -Pose.MaxFold, Pose.MaxFold)
    out.yaw = math.clamp(finite(yaw) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.dy = math.clamp(finite(dy) * a, -Pose.MaxOffset, Pose.MaxOffset)
    out.dz = math.clamp(finite(dz) * a, -Pose.MaxOffset, Pose.MaxOffset)
    return out
end
-- out = base + (action - base) * k, written into base (idle/walk pose -> action pose).
function Pose.blend(base: Out, action: Out, k: number): Out
    k = math.clamp(finite(k), 0, 1)
    base.pitch += (action.pitch - base.pitch) * k
    base.roll += (action.roll - base.roll) * k
    base.yaw += (action.yaw - base.yaw) * k
    base.dy += (action.dy - base.dy) * k
    base.dz += (action.dz - base.dz) * k
    return base
end
return Pose
