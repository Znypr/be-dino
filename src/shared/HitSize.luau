--!strict
-- BD-514 (docs/115 HS1): ONE rule for "how big is this dinosaur for a hit". Pure numbers (no Instances), so the server (CombatService,
-- NpcPredatorService), the offline verifier and any client prediction or bite preview call the same function.
--
-- Before: the server measured the bounding box of the character model, but on the server that model is the hidden LEGACY shell
-- (the low-poly model is only cloned on clients): Compy 4.2 x 5.6 x 6.1 instead of the real 3.5 x 6.6 x 7.7, and the 15 species with
-- no legacy model all got the same fallback box (radius 4.9). NPC predators measured the real low-poly clone, so a player and a wild
-- predator of the same species disagreed.
-- Now (Config.LowPolyDinos on, read only through LowPolyDinos.enabled by src/server/HitRadius): the radius comes from the measured
-- low-poly box in ScaleLadder.Dino.species (width and length at growth scale 1, the BD-232 sizes) times the growth scale.
-- The old rule was max(box X, box Z) / 2 of the model, so the radius is the larger of width and length, halved. It is a planar
-- circle around the root (CombatRules measures bite range on the ground plane).
local ScaleLadder = require(script.Parent.ScaleLadder)
local CombatConfig = require(script.Parent.CombatConfig)

local HitSize = {}
HitSize.MinRadius = 1 -- the NPC service clamped to [1, 14] before; players to [0, 14]
HitSize.MaxRadius = CombatConfig.BodyRadiusMax -- the hit cap of CombatRules.bodyRadius (14): a size can never open an infinite range
HitSize.MinScale = 1 -- the growth scale never goes below 1 (VisualScale 1 to 4.8)
HitSize.MaxScale = 6

local function finite(v: any, fallback: number): number
    return if typeof(v) == "number" and v == v and v > -1e9 and v < 1e9 then v else fallback
end

local function rowOf(speciesId: any): any?
    if typeof(speciesId) ~= "string" then return nil end
    local row = (ScaleLadder.Dino.species :: any)[speciesId]
    return if row and typeof(row.width) == "number" and typeof(row.length) == "number" then row else nil
end

function HitSize.has(speciesId: any): boolean
    return rowOf(speciesId) ~= nil
end

local function scaleOf(scale: any): number
    return math.clamp(finite(scale, 1), HitSize.MinScale, HitSize.MaxScale)
end

-- The body box (width, length) in studs at a growth scale: the measured low-poly box times the scale. nil for an unknown species.
function HitSize.footprint(speciesId: any, scale: any): (number?, number?)
    local row = rowOf(speciesId)
    if not row then return nil, nil end
    local s = scaleOf(scale)
    return row.width * s, row.length * s
end

-- The ScaleLadder-derived radius BEFORE the hit cap: max(width, length) / 2 x growth scale. nil for an unknown species.
function HitSize.rawRadius(speciesId: any, scale: any): number?
    local width, length = HitSize.footprint(speciesId, scale)
    if not width or not length then return nil end
    return math.max(width, length) / 2
end

-- What the server uses: the raw radius inside [MinRadius, MaxRadius]. nil for an unknown species (the caller keeps its own fallback).
function HitSize.radius(speciesId: any, scale: any): number?
    local raw = HitSize.rawRadius(speciesId, scale)
    if not raw then return nil end
    return math.clamp(raw, HitSize.MinRadius, HitSize.MaxRadius)
end

-- Unknown species with the low-poly sizes on: the same fallback CombatRules.bodyRadius uses (BodyRadiusPerScale x scale), so a species
-- missing from the ladder never reads a legacy box.
function HitSize.fallbackRadius(scale: any): number
    return math.clamp(CombatConfig.BodyRadiusPerScale * scaleOf(scale), HitSize.MinRadius, HitSize.MaxRadius)
end

-- radius, or the fallback for an unknown species. Never nil.
function HitSize.radiusOrFallback(speciesId: any, scale: any): number
    return HitSize.radius(speciesId, scale) or HitSize.fallbackRadius(scale)
end

return HitSize
