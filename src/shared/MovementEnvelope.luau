--!strict
-- Shared movement envelope. The same numbers drive the Humanoid setup (Dinosaur.luau),
-- the torso collider and every server plausibility check, so allowed traversal and
-- anti-cheat tolerance cannot drift apart (BD-053).
local Config = require(script.Parent.Config)
local MovementEnvelope = {}

local function slopeTangent(): number
    return math.tan(math.rad(Config.MaxSlopeAngle))
end

-- Fastest legitimate vertical climb while walking up the steepest allowed slope.
function MovementEnvelope.maxClimbRate(speed: number): number
    return math.max(0, speed) * slopeTangent()
end

function MovementEnvelope.plausible(delta: Vector3, dt: number, tolerance: number, burst: number, verticalVelocity: number, speed: number?): boolean
    local walk = speed or Config.WalkSpeed
    local horizontal = Vector2.new(delta.X, delta.Z).Magnitude
    local verticalSpeed = math.max(
        Config.JumpPower,
        MovementEnvelope.maxClimbRate(walk),
        math.min(Config.MovementGuardMaxVerticalSpeed, math.abs(verticalVelocity))
    )
    return horizontal <= walk * dt * tolerance + burst
        and math.abs(delta.Y) <= verticalSpeed * dt + workspace.Gravity * dt * dt / 2 + burst
end

-- Torso collider box for a dinosaur at `scale`, welded to the HumanoidRootPart whose
-- floor sits `groundHeight` studs below its centre. Returns width, height, length and
-- the collider centre's Y offset from the root. The footprint grows with the visual,
-- but the underside clears a plane tilted to MaxSlopeAngle in any direction (the worst
-- case is the half-diagonal), so the box never wedges into a walkable hill.
function MovementEnvelope.collider(scale: number, groundHeight: number): (number, number, number, number)
    local width = Config.DinoColliderWidth * scale
    local length = Config.DinoColliderLength * scale
    local halfDiagonal = math.sqrt(width * width + length * length) / 2
    local bottom = math.max(
        Config.DinoColliderMinClearance,
        halfDiagonal * slopeTangent() + Config.DinoColliderSlopeMargin
    )
    local top = math.max(bottom + Config.DinoColliderMinHeight, Config.DinoColliderTopPerScale * scale)
    local height = top - bottom
    return width, height, length, -groundHeight + bottom + height / 2
end

return MovementEnvelope
