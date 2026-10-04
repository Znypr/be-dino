--!strict
local Config = require(script.Parent.Config)
local MovementEnvelope = {}
function MovementEnvelope.plausible(delta: Vector3, dt: number, tolerance: number, burst: number, verticalVelocity: number, speed: number?): boolean
    local horizontal = Vector2.new(delta.X, delta.Z).Magnitude
    local verticalSpeed = math.max(Config.JumpPower, math.min(120, math.abs(verticalVelocity)))
    return horizontal <= (speed or Config.WalkSpeed) * dt * tolerance + burst
        and math.abs(delta.Y) <= verticalSpeed * dt + workspace.Gravity * dt * dt / 2 + burst
end
return MovementEnvelope
