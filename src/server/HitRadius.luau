--!strict
-- BD-514 (docs/115 HS1): the ONE server place that answers "what is this dinosaur's hit radius". CombatService (player vs player,
-- player vs NPC) and NpcPredatorService (aggro, chase and bite reach) both call it, so the same species at the same growth scale has
-- the same radius whoever asks.
--   Config.LowPolyDinos ON : Shared/HitSize (the measured low-poly box in ScaleLadder x the growth scale). The model is NOT measured:
--                            on the server it is the hidden legacy shell, which is not the dinosaur a player sees.
--   Config.LowPolyDinos OFF: today's rule, max(X, Z) / 2 of the model's bounding box (the legacy shell IS the visual then).
-- BD-381 rule: the LowPolyDinos flag is read only through LowPoly.enabled (verify_lowpoly_views); a test harness without it counts as off.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HitSize = require(ReplicatedStorage.Shared.HitSize)

local lowPolyModule: any = false
local function lowPolyOn(): boolean
    if lowPolyModule == false then
        local ok, lp = pcall(function() local shared: any = ReplicatedStorage.Shared return require(shared.LowPolyDinos) end)
        lowPolyModule = if ok and type(lp) == "table" and type(lp.enabled) == "function" then lp else nil
    end
    return lowPolyModule ~= nil and lowPolyModule.enabled() == true
end

local HitRadius = {}

function HitRadius.lowPolyOn(): boolean
    return lowPolyOn()
end

-- The flag-off rule of Build 020 (BD-311): planar half-size of the model's bounding box; 0 when it cannot be measured.
local function legacyMeasured(model: Instance): number
    local ok, size = pcall(function() return (model :: Model):GetExtentsSize() end)
    if not ok or typeof(size) ~= "Vector3" then return 0 end
    return math.max(size.X, size.Z) / 2
end

-- speciesId / scale default to the character attributes SpeciesId and VisualScale (written by DinosaurVisual.render on the server).
-- A wild predator passes its own species and drawn scale. Callers keep their own clamp (CombatRules.bodyRadius, the NPC [1, 14]).
function HitRadius.of(model: Instance, speciesId: string?, scale: number?): number
    if lowPolyOn() then
        return HitSize.radiusOrFallback(speciesId or model:GetAttribute("SpeciesId"), scale or model:GetAttribute("VisualScale"))
    end
    return legacyMeasured(model)
end

return HitRadius
