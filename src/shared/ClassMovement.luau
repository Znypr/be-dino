--!strict
-- BD-231 / BD-233 / BD-234 / docs/101 s11-12: per-class movement rules. PURE and NOT WIRED into gameplay yet.
-- Speed multipliers come from CombatConfig (one source). Every number here is PROVISIONAL, not final balance.
-- BD-246: wired by server/ClassMovementService.luau ONLY while Config.ClassMovementEnabled is true (flag off = shipped movement).
-- Enabled below stays false: it is the pure-module offline guard, not the runtime flag.
-- Velocities are returned as (x, y, z) numbers so the module runs without Roblox types in offline tests.
local Combat = require(script.Parent.CombatConfig)
local Config = require(script.Parent.Config)
local Progression = require(script.Parent.ProgressionConfig)

local ClassMovement = {}
ClassMovement.Enabled = false

-- Per-class tables. Multipliers apply to the existing Config.JumpPower / ProgressionConfig leap numbers.
-- kind "jump"/"leap" = Humanoid jump / existing leap shape; kind "dash" = forward surge on the same input, never upward.
ClassMovement.Classes = table.freeze({
    Ground = table.freeze({
        jump = table.freeze({ kind = "jump", powerX = 1.0, carryX = 1.0, heightCap = math.huge, glideFallSpeed = 0, glideSeconds = 0, cooldown = 0 }),
        leap = table.freeze({ kind = "leap", horizontalX = 1.0, verticalX = 1.0, durationX = 1.0, cooldown = Progression.LeapCooldown, glideFallSpeed = 0, heightCap = math.huge, hitWindow = 0 }),
    }),
    Fly = table.freeze({
        -- apex = (50*1.1)^2 / (2*250) = 6.05 studs: slightly higher and quicker than Ground (5.0), capped at 6.5 above ground.
        jump = table.freeze({ kind = "jump", powerX = 1.1, carryX = 1.2, heightCap = 6.5, glideFallSpeed = 12, glideSeconds = 1.0, cooldown = 0 }),
        leap = table.freeze({ kind = "leap", horizontalX = 1.3, verticalX = 0.6, durationX = 1.6, cooldown = Progression.LeapCooldown, glideFallSpeed = 12, heightCap = 9, hitWindow = 0 }),
    }),
    Water = table.freeze({
        -- No jump at all: the same input is a forward surge along the ground (vertical speed is always 0).
        jump = table.freeze({ kind = "dash", powerX = 0, carryX = 1.0, heightCap = 0, glideFallSpeed = 0, glideSeconds = 0, cooldown = 3,
            dashSpeed = 48, dashSeconds = 0.35 }),
        -- Aggressive dash: longer, faster, brief hit window. Still no upward velocity.
        leap = table.freeze({ kind = "dash", horizontalX = 1.25, verticalX = 0, durationX = 0.7, cooldown = Progression.LeapCooldown, glideFallSpeed = 0, heightCap = 0, hitWindow = 0.4,
            dashSpeed = 90, dashSeconds = 0.5 }),
    }),
    Armored = table.freeze({
        jump = table.freeze({ kind = "jump", powerX = 0.8, carryX = 0.9, heightCap = math.huge, glideFallSpeed = 0, glideSeconds = 0, cooldown = 0 }),
        leap = table.freeze({ kind = "leap", horizontalX = 0.85, verticalX = 0.8, durationX = 1.0, cooldown = Progression.LeapCooldown, glideFallSpeed = 0, heightCap = math.huge, hitWindow = 0 }),
    }),
})

ClassMovement.ClassNames = table.freeze({ "Ground", "Fly", "Water", "Armored" })
ClassMovement.Actions = table.freeze({ "jump", "leap" })

local function num(v: any, fallback: number): number
    if typeof(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return fallback end
    return v
end

local function classKey(name: any): string
    if typeof(name) == "string" and ClassMovement.Classes[name] then return name end
    return Combat.DefaultClass
end

-- Class of a species id: CombatConfig.SpeciesClasses (BD-246), unknown/nil = DefaultClass.
function ClassMovement.classForSpecies(speciesId: any): string
    local listed = if typeof(speciesId) == "string" then (Combat.SpeciesClasses :: any)[speciesId] else nil
    return classKey(listed)
end

-- Humanoid.JumpPower for a class (Water 0 = no jump; its dash is the ClassDash remote).
function ClassMovement.jumpPower(class: any, base: number): number
    return base * ClassMovement.Classes[classKey(class)].jump.powerX
end

function ClassMovement.rules(class: any): any
    return ClassMovement.Classes[classKey(class)]
end

-- Walk speed: Config.WalkSpeed x the CombatConfig class speed multiplier (potions and trails multiply on top elsewhere).
function ClassMovement.walkSpeed(class: any): number
    return Config.WalkSpeed * Combat.Classes[classKey(class)].speedX
end

-- Unit forward direction from a planar input. Zero/junk input falls back to facing -Z (never NaN).
local function planarDir(dx: any, dz: any): (number, number)
    local x, z = num(dx, 0), num(dz, 0)
    local m = math.sqrt(x * x + z * z)
    if m < 1e-6 then return 0, -1 end
    return x / m, z / m
end

function ClassMovement.cooldownRemaining(class: any, action: string, lastAt: any, now: any): number
    local r = ClassMovement.Classes[classKey(class)][action]
    if not r or typeof(lastAt) ~= "number" or lastAt ~= lastAt then return 0 end
    local n = num(now, lastAt)
    return math.max(0, r.cooldown - (n - lastAt))
end

-- Is a jump/leap request allowed? state = { grounded: boolean, now: number, lastJumpAt: number?, lastLeapAt: number? }.
-- Returns allowed, kind ("jump" | "dash" | "leap" | "none"). Everything starts from the ground (no sustained flight).
function ClassMovement.canStart(class: any, action: string, state: any): (boolean, string)
    local key = classKey(class)
    local r = ClassMovement.Classes[key][action]
    if not r then return false, "none" end
    if typeof(state) ~= "table" or state.grounded ~= true then return false, "none" end
    local last = if action == "leap" then state.lastLeapAt else state.lastJumpAt
    if ClassMovement.cooldownRemaining(key, action, last, state.now) > 0 then return false, "none" end
    if r.kind == "dash" then return true, "dash" end
    return true, action
end

-- Launch velocity for an action: (vx, vy, vz). Dash kinds NEVER return vy ~= 0 (water cannot go up).
function ClassMovement.launchVelocity(class: any, action: string, dx: any, dz: any): (number, number, number)
    local key = classKey(class)
    local r = ClassMovement.Classes[key][action]
    if not r then return 0, 0, 0 end
    local ux, uz = planarDir(dx, dz)
    if r.kind == "dash" then
        return ux * r.dashSpeed, 0, uz * r.dashSpeed
    end
    if action == "jump" then
        local speed = ClassMovement.walkSpeed(key) * Config.JumpForwardCarry * r.carryX
        return ux * speed, Config.JumpPower * r.powerX, uz * speed
    end
    local h = Progression.LeapHorizontalSpeed * r.horizontalX
    return ux * h, Progression.LeapVerticalSpeed * r.verticalX, uz * h
end

-- Seconds the action's launch phase lasts (the leap window / dash length).
function ClassMovement.duration(class: any, action: string): number
    local r = ClassMovement.Classes[classKey(class)][action]
    if not r then return 0 end
    if r.kind == "dash" then return r.dashSeconds end
    if action == "leap" then return Progression.LeapDuration * r.durationX end
    return 0
end

-- Value for the character's MovementSpeedLimit attribute while the action runs, so MovementGuard's planar cap fits it.
function ClassMovement.speedLimit(class: any, action: string): number
    local vx, _, vz = ClassMovement.launchVelocity(class, action, 0, -1)
    return math.max(ClassMovement.walkSpeed(class), math.sqrt(vx * vx + vz * vz))
end

-- Ground-height limit: a position is never above groundY + heightCap (Fly); water is ground-bound; others unclamped here.
function ClassMovement.clampHeight(class: any, action: string, y: any, groundY: any): number
    local r = ClassMovement.Classes[classKey(class)][action]
    local yy, gy = num(y, 0), num(groundY, 0)
    if not r then return yy end
    if r.kind == "dash" then return math.min(yy, gy) end
    if r.heightCap == math.huge then return yy end
    return math.min(yy, gy + r.heightCap)
end

-- Vertical velocity limiter per physics step: no upward speed at the height cap; Fly glide caps the fall speed.
function ClassMovement.limitVertical(class: any, action: string, vy: any, heightAboveGround: any, gliding: boolean?): number
    local r = ClassMovement.Classes[classKey(class)][action]
    local v, h = num(vy, 0), num(heightAboveGround, 0)
    if not r then return v end
    if r.kind == "dash" then return math.min(v, 0) end
    if r.heightCap ~= math.huge and h >= r.heightCap and v > 0 then v = 0 end
    if gliding and r.glideFallSpeed > 0 and v < -r.glideFallSpeed then v = -r.glideFallSpeed end
    return v
end

-- BD-593: the Fly glide, one frame, PURE. The character is owned by its client, so a velocity written by the server (the hover loop in
-- ClassMovementService) has no effect on it; the local client applies this instead (ClassGlide.client.luau), like the dash and the leap.
-- held = jump button held; grounded = standing on something; vy = current vertical speed; used = glide seconds spent this airtime;
-- dt = frame seconds. Returns the vertical speed to write and the new `used`. Only a FALL is slowed (never a rise), only while held,
-- only for `glideSeconds` per airtime, and only for Fly. The height cap is NOT applied here (height 0 is passed): a cap measured to
-- the root centre would shorten the Fly jump below the Ground jump (docs/145, BD-593).
function ClassMovement.glideStep(class: any, held: any, grounded: any, vy: any, used: any, dt: any): (number, number)
    local v, u = num(vy, 0), math.max(0, num(used, 0))
    if grounded == true then return v, 0 end
    local r = ClassMovement.Classes[classKey(class)].jump
    if held ~= true or r.glideFallSpeed <= 0 or v >= 0 or u >= r.glideSeconds then return v, u end
    return ClassMovement.limitVertical(class, "jump", v, 0, true), u + math.clamp(num(dt, 0), 0, 0.25)
end

-- BD-595 (LEAD decision FH1, docs/101 s20): the Fly hover cap, one frame, PURE. Measured at the FEET, not at the root centre: the root
-- centre already sits HipHeight + Size.Y / 2 (3 to 4 studs) above the ground while standing, so a cap on it would cut the Fly jump
-- (apex 6.05) to about 3 studs, below the Ground jump (5.0). The cap number is the class table's own heightCap (6.5); no new number.
function ClassMovement.feetHeight(rootHeightAboveGround: any, hipHeight: any, rootSizeY: any): number
    return num(rootHeightAboveGround, 0) - (num(hipHeight, 0) + num(rootSizeY, 0) / 2)
end

-- Returns the vertical speed to write. It can only LOWER an upward speed (never raises any speed, never touches a fall): a rise is
-- held so that the feet end exactly at the cap (v * dt never carries them past it). A leap (leaping = LeapUntil active) is exempt.
-- Classes without a finite jump cap (Ground, Armored) and Water (dash) are never touched.
function ClassMovement.hoverStep(class: any, vy: any, rootHeightAboveGround: any, hipHeight: any, rootSizeY: any, leaping: any, dt: any): number
    local v = num(vy, 0)
    if leaping == true or v <= 0 then return v end
    local r = ClassMovement.Classes[classKey(class)].jump
    if r.kind ~= "jump" or r.heightCap == math.huge then return v end
    local room = r.heightCap - ClassMovement.feetHeight(rootHeightAboveGround, hipHeight, rootSizeY)
    if room <= 0 then return 0 end
    local step = math.clamp(num(dt, 0), 1 / 240, 0.25)
    return math.min(v, room / step)
end

-- Map bounds: planar position never leaves the arena square (Config.ArenaHalfWidth).
function ClassMovement.clampToArena(x: any, z: any): (number, number)
    local h = Config.ArenaHalfWidth
    return math.clamp(num(x, 0), -h, h), math.clamp(num(z, 0), -h, h)
end

-- MovementGuard compatibility: same planar maths as MovementEnvelope.plausible. True when travelling at `speed` for `dt`
-- seconds with the given MovementSpeedLimit stays inside the guard tolerance (no false positive).
function ClassMovement.guardAllowsPlanar(speed: number, dt: number, limit: number): boolean
    return speed * dt <= limit * dt * Config.MovementGuardSpeedTolerance + Config.MovementGuardBurstStuds
end

-- Animation intent (BD-233 / BD-234): state -> { clip, speedScale }. Every class covers every state.
ClassMovement.States = table.freeze({ "idle", "walk", "jump", "leap", "dash", "land", "defeated" })
local CLIPS: { [string]: { [string]: string } } = {
    Ground = { idle = "ground_idle", walk = "ground_waddle", jump = "ground_jump", leap = "ground_lunge", dash = "ground_lunge", land = "ground_land_squash", defeated = "ground_defeated" },
    Fly = { idle = "fly_idle_folded", walk = "fly_waddle_folded", jump = "fly_jump_flutter", leap = "fly_swoop", dash = "fly_swoop", land = "fly_land_flutter", defeated = "fly_defeated" },
    Water = { idle = "water_idle_bob", walk = "water_slither", jump = "water_dash", leap = "water_dash_big", dash = "water_dash", land = "water_dash_end", defeated = "water_defeated" },
    Armored = { idle = "armored_idle_heavy", walk = "armored_stomp", jump = "armored_hop", leap = "armored_shoulder_bump", dash = "armored_shoulder_bump", land = "armored_land_puff", defeated = "armored_defeated" },
}

function ClassMovement.animationIntent(class: any, state: any, speed: any?): { clip: string, speedScale: number }
    local key = classKey(class)
    local s = if typeof(state) == "string" and CLIPS[key][state] then state else "idle"
    local sp = math.max(0, num(speed, 0))
    if s == "walk" and sp < 0.5 then s = "idle" end
    local scale = 1
    if s == "walk" then scale = math.clamp(sp / ClassMovement.walkSpeed(key), 0.25, 2) end
    return { clip = CLIPS[key][s], speedScale = scale }
end

return ClassMovement
