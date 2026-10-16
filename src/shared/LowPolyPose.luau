--!strict
-- BD-234 spike: pure procedural idle/walk pose per body part (no Roblox types, offline-testable).
-- Angles are radians about the part's own pivot (pitch = X, roll = Z, yaw = Y); dy/dz are fractions of the model height.
-- Idle: gentle breathing, slow head tilt, tail sway. Walk (chicken/dino mix): quick bob, alternating legs, head peck, tail counter-swing.
local Pose = {}
Pose.Roles = {"body", "head", "tail", "arm", "leg"}
Pose.MaxAngle = 0.9
Pose.MaxOffset = 0.08
export type Out = {pitch: number, roll: number, yaw: number, dy: number, dz: number}
function Pose.new(): Out return {pitch = 0, roll = 0, yaw = 0, dy = 0, dz = 0} end
-- Walk cycle speed: radians per second grows with speed01 (0..1 of max run speed), quick like a chicken.
function Pose.stepRate(speed01: number): number
    return 5 + 7 * math.clamp(speed01, 0, 1)
end
local function finite(x: number): number return if x == x and math.abs(x) < 1e6 then x else 0 end
-- role: body/head/tail/arm/leg; side: -1/1 (x side); lead: true for a quadruped front leg (diagonal pairing); t: idle clock seconds;
-- phase: walk phase radians; speed01: 0 idle .. 1 full run; amp: 0..1 (Reduce Motion passes 0).
function Pose.sample(role: string, side: number, lead: boolean, t: number, phase: number, speed01: number, amp: number, out: Out): Out
    t, phase = finite(t), finite(phase)
    local w = math.clamp(finite(speed01), 0, 1)
    local a = math.clamp(finite(amp), 0, 1)
    local idle = 1 - w
    local pitch, roll, yaw, dy, dz = 0, 0, 0, 0, 0
    local s = if side < 0 then -1 else 1
    local sw = math.sin(phase)
    if role == "body" then
        dy = idle * math.sin(t * 1.7) * 0.012 + w * math.abs(sw) * 0.03
        roll = w * sw * 0.07
        pitch = idle * math.sin(t * 1.7 + 0.6) * 0.012
    elseif role == "head" then
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
        pitch = w * swing * 0.65
        dy = w * math.max(0, swing) * 0.015
    elseif role == "arm" then
        pitch = idle * math.sin(t * 1.7 + 0.3) * 0.04 + w * math.sin(phase + (if s < 0 then math.pi else 0)) * 0.30
    end
    out.pitch = math.clamp(finite(pitch) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.roll = math.clamp(finite(roll) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.yaw = math.clamp(finite(yaw) * a, -Pose.MaxAngle, Pose.MaxAngle)
    out.dy = math.clamp(finite(dy) * a, -Pose.MaxOffset, Pose.MaxOffset)
    out.dz = math.clamp(finite(dz) * a, -Pose.MaxOffset, Pose.MaxOffset)
    return out
end
return Pose
