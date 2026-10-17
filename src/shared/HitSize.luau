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
-- BD-245 (docs/115 s HZ) adds a PROPOSED capsule zone below, behind CombatConfig.HitZoneRule (default "circle" = this rule); not wired.
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
    local row = ScaleLadder.dinoRow(speciesId) -- BD-606: the 22 shipped species, then the seven secrets
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

-- ---------------------------------------------------------------- BD-245 PROPOSAL (docs/115 s HZ, owner decides): hit ZONE shape
-- NOT WIRED: CombatRules / CombatService / NpcPredatorService still call HitSize.radius, so nothing below changes a bite while
-- CombatConfig.HitZoneRule is "circle" (the default) or while no caller reads it. A zone is a body-axis CAPSULE: a round radius around a
-- straight spine of half-length `halfSpan` (planar, centred on the root, lying along the body's facing). halfSpan 0 is today's circle.
--   "circle"  today's rule (HS1): radius = HitSize.radius, halfSpan 0.
--   "capsule" radius = half the body WIDTH x scale, halfSpan = (length - width) / 2 x scale (0 when wider than long, e.g. a flier's wingspan),
--             so the zone is the real body footprint: as long as the body, no wider than the body, and nothing flattens it at growth 2.
HitSize.Rules = {"circle", "capsule"}
HitSize.CapsuleRadiusMax = CombatConfig.HitCapsuleRadiusMax -- junk guard, above the widest real body (19.7 at growth 4.8)
HitSize.CapsuleSpanMax = CombatConfig.HitCapsuleSpanMax -- junk guard, above the longest real spine (16.9 at growth 4.8)

-- The active rule: CombatConfig.HitZoneRule when it names a known rule, otherwise "circle" (a typo can never change a bite).
function HitSize.rule(): string
    local r = (CombatConfig :: any).HitZoneRule
    for _, known in HitSize.Rules do
        if r == known then return r end
    end
    return "circle"
end

-- The capsule of a species at a growth scale: (radius, halfSpan), whatever the switch says. nil for an unknown species.
function HitSize.capsule(speciesId: any, scale: any): (number?, number?)
    local width, length = HitSize.footprint(speciesId, scale)
    if not width or not length then return nil, nil end
    local radius = math.clamp(width / 2, HitSize.MinRadius, HitSize.CapsuleRadiusMax)
    local halfSpan = math.clamp((length - width) / 2, 0, HitSize.CapsuleSpanMax)
    return radius, halfSpan
end

-- What a server would use for a hit zone under the rule (override `rule` only in tests): (radius, halfSpan). nil for an unknown species.
function HitSize.zone(speciesId: any, scale: any, rule: string?): (number?, number?)
    if (rule or HitSize.rule()) == "capsule" then return HitSize.capsule(speciesId, scale) end
    local r = HitSize.radius(speciesId, scale)
    return r, if r then 0 else nil
end

-- zone, or the CombatRules fallback circle for an unknown species. Never nil.
function HitSize.zoneOrFallback(speciesId: any, scale: any, rule: string?): (number, number)
    local r, span = HitSize.zone(speciesId, scale, rule)
    if r and span then return r, span end
    return HitSize.fallbackRadius(scale), 0
end

-- How far the zone reaches along the body from the root (nose or tail): radius + halfSpan. For a capsule of a body longer than wide this
-- is length / 2 x scale, today's UNCAPPED raw radius (Compy at growth 1: 3.85 in both rules). Use it as the ATTACKER's reach origin.
function HitSize.reach(radius: number, halfSpan: number): number
    return radius + halfSpan
end

-- Planar gap from a point to the zone surface (0 inside). (dx, dz) = the point minus the dinosaur's root; (hx, hz) = the body's facing
-- direction (any length; zero = no axis, a plain circle). A bite hits when gap <= bite reach + the attacker's own reach.
function HitSize.gap(radius: number, halfSpan: number, dx: number, dz: number, hx: number, hz: number): number
    local px, pz = finite(dx, 0), finite(dz, 0)
    local ax, az = finite(hx, 0), finite(hz, 0)
    local m = math.sqrt(ax * ax + az * az)
    local t = 0
    if m > 1e-6 and halfSpan > 0 then
        t = math.clamp((px * ax + pz * az) / m, -halfSpan, halfSpan)
        px, pz = px - t * ax / m, pz - t * az / m
    end
    return math.max(0, math.sqrt(px * px + pz * pz) - radius)
end

return HitSize
