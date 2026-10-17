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
local function finite(x: number): number return if x == x and math.abs(x) < 1e6 then x else 0 end
-- BD-388: fwd is a forward shove in STUDS (the head peck), not a height fraction. PeckStuds / PeckPitch are the chicken-like head thrust per step.
Pose.PeckStuds = 0.4
Pose.PeckPitch = math.rad(6)
Pose.MaxBob = 0.04 -- whole-body bob, fraction of the model height (every part moves by the SAME amount: nothing slides against the body)
export type Out = {pitch: number, roll: number, yaw: number, dy: number, dz: number, fwd: number}
function Pose.new(): Out return {pitch = 0, roll = 0, yaw = 0, dy = 0, dz = 0, fwd = 0} end
-- BD-388: rotation of a point about a pivot, same order as CFrame.Angles(pitch, yaw, roll) (R = Rx * Ry * Rz). The animator builds each part's
-- offset as CFrame(pivot) * Angles * CFrame(-pivot), so the joint anchor never moves and the part is only rotated (no stretching): tested offline.
function Pose.rotatePoint(p: {number}, pivot: {number}, pitch: number, yaw: number, roll: number): {number}
    local x, y, z = p[1] - pivot[1], p[2] - pivot[2], p[3] - pivot[3]
    local c, s = math.cos(roll), math.sin(roll)
    x, y = c * x - s * y, s * x + c * y -- Rz
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = c * x + s * z, -s * x + c * z -- Ry
    c, s = math.cos(pitch), math.sin(pitch)
    y, z = c * y - s * z, s * y + c * z -- Rx
    return {x + pivot[1], y + pivot[2], z + pivot[3]}
end
-- BD-556: how far (studs, 0 or more) a part must be lifted so its lowest corner is never below where it rests. The Water flippers pivot at mid height,
-- so a walk or surge step swung a flipper tip up to 0.3 stud into the ground. size = the part's box, pivot = the joint, up = world up in the part's own
-- frame (default y). Pure: the animator adds the result to the part's shared shift. Bounded to MaxLift.
Pose.MaxLift = 1
function Pose.restLift(size: {number}, pivot: {number}, pitch: number, yaw: number, roll: number, up: {number}?): number
    local ux, uy, uz = 0, 1, 0
    if up then ux, uy, uz = finite(up[1]), finite(up[2]), finite(up[3]) end
    local hx, hy, hz = math.abs(finite(size[1])) / 2, math.abs(finite(size[2])) / 2, math.abs(finite(size[3])) / 2
    local rest, low = math.huge, math.huge
    for _, sx in {-1, 1} do for _, sy in {-1, 1} do for _, sz in {-1, 1} do
        local corner = {sx * hx, sy * hy, sz * hz}
        local r = Pose.rotatePoint(corner, pivot, finite(pitch), finite(yaw), finite(roll))
        rest = math.min(rest, ux * corner[1] + uy * corner[2] + uz * corner[3])
        low = math.min(low, ux * r[1] + uy * r[2] + uz * r[3])
    end end end
    return math.clamp(finite(rest - low), 0, Pose.MaxLift)
end
-- Whole-body bob (fraction of height), applied identically to EVERY part by the animator. The body part itself no longer rolls/pitches/bobs
-- on its own (that moved it against legs, head and tail: the owner's "limbs, eyes and nostrils shift", BD-388).
function Pose.bob(t: number, phase: number, speed01: number, amp: number, class: string?): number
    t, phase = finite(t), finite(phase)
    local w = math.clamp(finite(speed01), 0, 1)
    local a = math.clamp(finite(amp), 0, 1)
    local water = class == "Water"
    local dy = (1 - w) * math.sin(t * 1.7) * 0.008 + w * math.abs(math.sin(phase)) * (if water then 0.008 else 0.02)
    if water then dy -= 0.015 end
    return math.clamp(finite(dy) * a, -Pose.MaxBob, Pose.MaxBob)
end
-- Walk cycle speed: radians per second grows with speed01 (0..1 of max run speed), quick like a chicken.
function Pose.stepRate(speed01: number): number
    return 5 + 7 * math.clamp(speed01, 0, 1)
end
-- class (optional, default Ground): Fly folds wings; Water stays low (smaller bob, shorter strokes); Armored takes shorter steps.
-- role: body/head/neck/tail/arm/leg/wing/flipper; side: -1/1 (x side); lead: true for a quadruped front leg (diagonal pairing); t: idle clock seconds;
-- phase: walk phase radians; speed01: 0 idle .. 1 full run; amp: 0..1 (Reduce Motion passes 0).
function Pose.sample(role: string, side: number, lead: boolean, t: number, phase: number, speed01: number, amp: number, out: Out, class: string?): Out
    t, phase = finite(t), finite(phase)
    local w = math.clamp(finite(speed01), 0, 1)
    local a = math.clamp(finite(amp), 0, 1)
    local idle = 1 - w
    local pitch, roll, yaw, dy, dz, fwd = 0, 0, 0, 0, 0, 0
    local s = if side < 0 then -1 else 1
    local sw = math.sin(phase)
    local water, armored = class == "Water", class == "Armored"
    local stride = if water then 0.5 elseif armored then 0.8 else 1
    local fold = 0
    if role == "body" then
        -- BD-388: no motion of its own; Pose.bob moves the whole rig, so the body never shifts against its limbs.
    elseif role == "head" or role == "neck" then
        -- BD-388: the head mesh carries the eyes and nostrils, so it only turns a little; the walk adds a chicken peck:
        -- once per step the head thrusts about PeckStuds forward while tilting PeckPitch nose-down, then draws back.
        roll = idle * math.sin(t * 0.55) * 0.05 + w * -sw * 0.02
        yaw = idle * math.sin(t * 0.38 + 1) * 0.04
        local u = (math.sin(phase * 2 - 0.8) + 1) / 2
        pitch = idle * math.sin(t * 1.7 + 1.1) * 0.02 - w * u * Pose.PeckPitch
        fwd = w * u * Pose.PeckStuds
    elseif role == "tail" then
        yaw = idle * math.sin(t * 0.9) * 0.14 + w * -sw * 0.18
        pitch = idle * math.sin(t * 0.7 + 2) * 0.04 + w * math.sin(phase * 2) * 0.05
    elseif role == "leg" then
        local lift = if lead then 0 else math.pi
        local swing = math.sin(phase + (if s < 0 then 0 else math.pi) + lift)
        pitch = w * swing * 0.55 * stride -- swings about the hip pivot only (no slide: no per-leg translation; the foot lifts by the swing)
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
    out.fwd = math.clamp(finite(fwd) * a, 0, Pose.PeckStuds)
    return out
end
-- BD-233 spike: jump / leap / land / water-surge actions. Phases: crouch -> push (stretch) -> air (tuck, held until the dino lands) -> land (squash);
-- Water has no air time: a single "surge" (forward dash). Everything is calm and short (docs/87), absolute offsets from the REST pose, bounded.
Pose.Phases = {"crouch", "push", "air", "land", "surge", "windup", "bite", "defeat"}
Pose.DefeatSeconds = 1.5 -- docs/97: a skin defeat is about 1.5 s, soft and funny
Pose.Skins = {"Base", "Plush", "Clay", "Bricks"}
Pose.TuckTime = 0.18 -- seconds for the airborne tuck to settle
-- BD-555: the humanoid reports Jumping only once the dino has LEFT the ground, so a jump or leap arrives airborne. The animator skips the crouch
-- and the push-off then (they used to fold, unfold and fold the legs again inside 0.4 s, up to 14 degrees in one frame) and eases from whatever
-- pose the dino has into the airborne tuck over DirectBlend seconds (ctx.direct). Tuned so no part turns 8 degrees or more in one 60 Hz frame.
Pose.DirectBlend = 0.4
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
    if phase == "windup" then return 0.50 end -- BD-324: wild predator telegraph (Rules.Config.WindupSeconds); held until the cue ends
    if phase == "bite" then return 0.40 end
    if phase == "defeat" then return Pose.DefeatSeconds end
    return 0
end
local function ease(u: number): number u = math.clamp(u, 0, 1) return u * u * (3 - 2 * u) end
-- How strongly the action replaces the idle/walk pose: 0 at the start and at the very end so the hand-over is seamless.
function Pose.actionWeight(phase: string, p: number): number
    p = math.clamp(finite(p), 0, 1)
    if phase == "crouch" then return ease(p) end
    if phase == "land" then return 1 - ease(math.clamp((p - 0.5) / 0.5, 0, 1)) end
    if phase == "surge" or phase == "bite" then return ease(p / 0.15) * (1 - ease((p - 0.7) / 0.3)) end
    if phase == "windup" or phase == "defeat" then return ease(p / 0.35) end -- defeat: eases in, then HOLDS (the dino is leaving the world)
    return 1
end
-- ctx: phase, p (0..1 progress of a timed phase), t (seconds since the phase began), aggr (0 jump .. 1 leap), carry (0..1 tuck amount when landing began).
-- Fly landing hand-over (first Studio look, docs/evidence/2026-10-17-poses): the landing starts from the wing state the previous phase ended on.
-- flap = the wing flap angle the air phase ended on (else the flutter snapped to 0, about 20 degrees); wing = how far the wings were open (0 folded .. 1 open)
-- when the landing began (a short hop that lands before the wings opened used to snap them open, about 60 degrees in one frame). nil wing = 1 (open).
-- direct (BD-555): the air phase began at take-off with no crouch or push-off, so it holds the full tuck from t = 0 (no push-off stretch) and the
-- caller fades it in with Pose.airWeight; the landing then fades out from the weight the air ended on (Pose.landWeight).
export type Ctx = {phase: string, p: number, t: number, aggr: number, carry: number, flap: number?, wing: number?, direct: boolean?}
function Pose.newCtx(): Ctx return {phase = "crouch", p = 0, t = 0, aggr = 0, carry = 0, flap = 0, wing = 1, direct = false} end
-- Weight of the airborne tuck t seconds after a direct take-off (0 = still the walk pose, 1 = full tuck). Smooth at both ends.
function Pose.airWeight(t: number): number
    return ease(math.max(0, finite(t)) / Pose.DirectBlend)
end
-- Landing weight when the air phase ended at weight `from` (a hop that lands before the tuck finished): the landing carries on from the pose the
-- air left and squashes only as much as the hop deserved (a tiny hop = a tiny squash), instead of snapping to a full tuck and squash. from = 1
-- is the normal landing.
function Pose.landWeight(p: number, from: number): number
    return math.clamp(finite(from), 0, 1) * Pose.actionWeight("land", p)
end
-- Fraction the wings are open (0 folded .. 1 open) during a Fly phase, p = 0..1 progress of a timed phase. Used by the landing hand-over.
function Pose.wingOpen(phase: string, p: number): number
    if phase == "air" then return 1 end
    if phase == "push" then return ease(math.clamp(finite(p), 0, 1)) end
    return 0
end
-- Wing flap angle (radians) of a Fly in the air phase, t seconds in. A jump flaps, a leap glides on nearly still wings.
function Pose.airFlap(t: number, aggr: number): number
    return (1 - 0.8 * math.clamp(finite(aggr), 0, 1)) * math.sin(math.max(0, finite(t)) * 11) * 0.35
end
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
    elseif ph == "bite" then -- BD-324: lunge + snap for any class (the Water surge shape)
        lunge = math.sin(math.pi * p)
        snap = math.sin(math.pi * math.clamp((p - 0.3) / 0.4, 0, 1))
    elseif ph == "windup" then -- BD-324: rear back and lower, head cocked up (reads as the telegraph)
        q = ease(p) * 0.9
        tk = ease(p) * 0.25
    else
        if ph == "crouch" then q = ease(p) * cls.q
        elseif ph == "push" then q = (1 - ease(p)) * cls.q st = ease(p) * cls.s
        elseif ph == "air" then
            if ctx.direct then
                tk = cls.t -- already in the full tuck: the caller blends it in with Pose.airWeight
            else
                local e = ease(t / Pose.TuckTime)
                st, tk = (1 - e) * cls.s, e * cls.t
            end
        elseif ph == "land" then
            local c = math.clamp(finite(ctx.carry), 0, 1)
            local d = ease(p / 0.25)
            tk = c * (1 - d) * cls.t
            q = d * (1 - ease((p - 0.25) / 0.75)) * cls.l
        end
        if class == "Fly" then
            if ph == "push" then W = Pose.wingOpen("push", p) elseif ph == "air" then W = 1 elseif ph == "land" then W = math.clamp(finite(ctx.wing or 1), 0, 1) * (1 - ease(p)) end
            if ph == "air" then flap = Pose.airFlap(t, aggr) -- a leap glides on nearly still wings
            elseif ph == "land" then -- soft flutter landing; the last air flap fades out over the first 30% so the wings never snap
                flap = math.sin(t * 16) * 0.3 * (1 - p) + math.clamp(finite(ctx.flap or 0), -0.4, 0.4) * (1 - ease(p / 0.3))
            end
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
    out.fwd = 0
    return out
end
-- BD-249: gentle per-skin defeat hook (docs/97). Same shape as sampleAction (absolute offsets from the rest pose, bounded, Reduce Motion = rest).
-- Base: tips over sideways with a little dizzy wobble. Plush: slowly deflates (slumps down) with a soft wobble. Clay: pressed down flat
-- (sinks, limbs spread). Bricks: the parts drift apart a few percent, like a toy coming loose (never gore; the shards/sounds are art tasks).
-- Unknown skin names fall back to Base. ctx.p = 0..1 over DefeatSeconds, ctx.t = seconds.
function Pose.skinOf(name: any): string
    for _, k in Pose.Skins do if k == name then return k end end
    return "Base"
end
function Pose.sampleDefeat(role: string, side: number, lead: boolean, ctx: Ctx, amp: number, out: Out, class: string?, skin: string?): Out
    local a = math.clamp(finite(amp), 0, 1)
    local s = if side < 0 then -1 else 1
    local p, t = math.clamp(finite(ctx.p), 0, 1), math.max(0, finite(ctx.t))
    local e = ease(p)
    local kind = Pose.skinOf(skin)
    local pitch, roll, yaw, dy, dz = 0, 0, 0, 0, 0
    local fold = 0
    if kind == "Base" then
        local wob = math.sin(t * 9) * (1 - e) * 0.05
        if role == "body" then roll, dy = 0.45 * e + wob, -0.03 * e
        elseif role == "head" or role == "neck" then roll, pitch, yaw = 0.25 * e + wob, 0.15 * e, math.sin(t * 7) * 0.10 * (1 - e)
        elseif role == "tail" then roll, yaw = 0.2 * e, 0.2 * math.sin(t * 5) * (1 - e)
        elseif role == "leg" or role == "arm" then pitch, roll = -0.25 * e * s, 0.2 * e
        elseif role == "flipper" then roll = s * 0.3 * e end
    elseif kind == "Plush" then
        local pff = math.sin(t * 6) * (1 - e) * 0.03
        if role == "body" then dy, pitch = -0.06 * e, 0.10 * e + pff
        elseif role == "head" or role == "neck" then dy, pitch = -0.05 * e, 0.30 * e
        elseif role == "tail" then pitch = 0.25 * e
        elseif role == "leg" or role == "arm" then pitch = 0.3 * e * (if lead then 1 else -1) elseif role == "flipper" then roll = s * 0.25 * e end
    elseif kind == "Clay" then
        local press = ease(math.clamp(p / 0.4, 0, 1))
        local back = ease(math.clamp((p - 0.7) / 0.3, 0, 1)) * 0.3 -- starts to reshape at the end
        local k = press * (1 - back)
        if role == "body" then dy = -0.07 * k
        elseif role == "head" or role == "neck" then dy, pitch = -0.06 * k, 0.10 * k
        elseif role == "tail" then dy, pitch = -0.04 * k, 0.12 * k
        elseif role == "leg" or role == "arm" then roll, dy = s * 0.35 * k, -0.02 * k
        elseif role == "flipper" then roll = s * 0.35 * k end
    else -- Bricks
        local drift = ease(math.clamp(p / 0.6, 0, 1))
        local rattle = math.sin(t * 22) * (1 - e) * 0.004
        if role == "body" then dy = -0.04 * drift + rattle
        elseif role == "head" or role == "neck" then dy, dz, pitch = 0.02 * drift, 0.03 * drift, 0.35 * drift
        elseif role == "tail" then dz, dy, yaw = -0.04 * drift, -0.02 * drift, 0.30 * drift
        elseif role == "leg" or role == "arm" then dy, roll = -0.03 * drift + rattle, s * 0.30 * drift
        elseif role == "flipper" then roll = s * 0.4 * drift end
    end
    if role == "wing" then fold = -s * Pose.FoldAngle roll = s * 0.1 * e end
    out.pitch = math.clamp(finite(pitch) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.roll = math.clamp(finite(roll) * a + fold, -Pose.MaxFold, Pose.MaxFold)
    out.yaw = math.clamp(finite(yaw) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.dy = math.clamp(finite(dy) * a, -Pose.MaxOffset, Pose.MaxOffset)
    out.dz = math.clamp(finite(dz) * a, -Pose.MaxOffset, Pose.MaxOffset)
    out.fwd = 0
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
    base.fwd += (action.fwd - base.fwd) * k
    return base
end
return Pose
