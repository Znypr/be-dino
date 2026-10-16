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
return Pose
