--!strict
-- BD-515 (docs/115 MR1-MR3): eating happens at the MOUTH. Pure numbers (no Instances), required by the server (FoodService, PredationService)
-- and usable by any client pickup preview, so the same function answers "is this berry in reach" on both sides. The server stays authoritative.
--
-- Before: reach = FoodPickupRadius 2.25 + 0.75 x (scale - 1) (max 5) measured from the dino ROOT, whatever the species. The root is the middle
-- of the body, so after the BD-500 resize the 14.4 stud Ankylosaurus had its mouth 7.2 studs ahead of the pickup point and ate with its chest.
-- Now (low-poly dinos): the pickup point is the HEAD point, root + forward x headOffset(species, scale), and the radius scales with the
-- species' HEAD size (not its body length), plus the small growth bonus the old rule had. The numbers come from ScaleLadder.Dino.species:
--   snout      = how far the snout tip is ahead of the model centre (the root) at growth scale 1, Studio-measured (the head part's front edge);
--   headLength = the head part's length along the body, Studio-measured. The generated head parts include the neck, crest or frill, so the
--                head used here is that length as a fraction of the body, clamped to [MinHeadFraction, MaxHeadFraction] (about a quarter at most);
--   length     = the body box length (spawn size, template pose).
-- Head point = the centre of the head = snout - headLength / 2, scaled by the growth scale. radius = headLength / 2 (so the snout tip is always
-- inside) + RadiusPad. BD-515 set both slack and pad to FoodPickupRadius - the Compy's half head (1.425); BD-522 (MR5) lowers them, see below.
local Config = require(script.Parent.Config)
local ScaleLadder = require(script.Parent.ScaleLadder)

local MouthReach = {}
MouthReach.MinHeadFraction = 0.20
MouthReach.MaxHeadFraction = 0.25
MouthReach.VerticalLimit = 6 -- studs of height difference between the root and the food, unchanged from the root-based rule
MouthReach.LegacyGrowthBonus = 0.75 -- studs per growth scale of the old rule (used for species without a measured row)
MouthReach.LegacyMaxRadius = 5
MouthReach.RefSpecies = "compy"
-- BD-522 (docs/115 MR5, LEAD): the BD-515 zone (slack 1.425 = Config.FoodPickupRadius - the Compy half head, radius = half head x scale + 1.425) made every species,
-- the Compy too, eat +27% to +44% more food per minute than the Build 020 root rule (the walker eats where the NOSE is, 3.8 studs ahead of the root at scale 1, 8.6 at
-- growth 2.25, instead of 2.25 from the root). Parity needs a front edge of about HALF the snout distance, which would leave the nose outside the zone, so the snout rule
-- wins and these two numbers are the smallest zone that still eats a berry at the snout; docs/evidence/2026-10-17-food-reach/ has the sweep and the trade-off.
-- Fields (not locals) so tools/simulate_food_reach.py can sweep them; the game never writes them.
MouthReach.SlackStuds = 0.25 -- studs the zone reaches beyond the snout tip (a berry touching the nose is eaten); was 1.425
MouthReach.RadiusPad = 1.0 -- studs added to (RadiusFactor x half head x scale) for the radius; was 1.425. Kept above half a walking step (0.9 to 1.1 studs per 0.08 s tick) so a berry cannot be skipped between two ticks
MouthReach.RadiusFactor = 1 -- share of the half head (it grows with the scale) in the radius

local function finite(v: any, fallback: number): number
    return if typeof(v) == "number" and v == v and v > -1e9 and v < 1e9 then v else fallback
end
local function growthOf(scale: any): number
    return math.clamp(finite(scale, 1), 1, 6)
end

-- The measured row of a species, nil for an unknown one.
local function rowOf(speciesId: any): any?
    if typeof(speciesId) ~= "string" then return nil end
    local row = (ScaleLadder.Dino.species :: any)[speciesId]
    return if row and row.snout and row.headLength and row.length then row else nil
end

-- Head length at growth scale 1 in studs: the measured head part as a share of the body, clamped.
local function headLength1(row: any): number
    local fraction = math.clamp(row.headLength / row.length, MouthReach.MinHeadFraction, MouthReach.MaxHeadFraction)
    return fraction * row.length
end

-- Half the head length in studs at a growth scale (the radius of the zone is this plus the pad).
function MouthReach.headHalf(speciesId: any, scale: any): number
    local row = rowOf(speciesId)
    return if row then headLength1(row) / 2 * growthOf(scale) else 0
end

function MouthReach.has(speciesId: any): boolean
    return rowOf(speciesId) ~= nil
end

-- Studs from the root to the snout tip along the facing direction (the "mouth"), 0 for an unknown species.
function MouthReach.snoutOffset(speciesId: any, scale: any): number
    local row = rowOf(speciesId)
    return if row then row.snout * growthOf(scale) else 0
end

-- The old root-based radius (and the radius of a species without a measured row).
function MouthReach.legacyRadius(scale: any): number
    return math.min(MouthReach.LegacyMaxRadius, Config.FoodPickupRadius + (growthOf(scale) - 1) * MouthReach.LegacyGrowthBonus)
end

-- Studs the zone reaches beyond the snout tip (BD-522: 0.25, BD-515: the old 2.25 minus the Compy's half head = 1.425). The FRONT EDGE of the zone is always snout + slack.
function MouthReach.slack(): number
    return MouthReach.SlackStuds
end

-- BD-515 radius before the BD-521 cap (docs/115 MR2): follows the head size, plus the old growth bonus.
function MouthReach.uncappedRadius(speciesId: any, scale: any): number
    local row = rowOf(speciesId)
    if not row then return MouthReach.legacyRadius(scale) end
    return headLength1(row) / 2 * growthOf(scale) * MouthReach.RadiusFactor + MouthReach.RadiusPad
end

-- Head point offset before the cap: the front edge minus the radius (BD-515: the centre of the head, snout - half the head, while slack == pad; BD-522: a little
-- ahead of it because the radius pad is larger than the slack).
function MouthReach.uncappedHeadOffset(speciesId: any, scale: any): number
    if not rowOf(speciesId) then return 0 end
    return MouthReach.uncappedFront(speciesId, scale) - MouthReach.uncappedRadius(speciesId, scale)
end

-- BD-521 (docs/115 MR4): the cap factor k = Config.FoodReachCapCompy (nil or not a number >= 1 = no cap). A species never gets a zone that reaches
-- farther ahead of the root than k x the Compy's zone at the same growth scale, nor a wider one: the simulated food per minute is driven by how far
-- AHEAD of the root a berry is eaten (front edge = snout + slack, so it follows the body length), much more than by the head size. Where the cap
-- binds the front edge and the radius shrink, the head point moves back accordingly; the Compy and every shorter species are never changed.
function MouthReach.capFactor(): number?
    local k = (Config :: any).FoodReachCapCompy
    return if typeof(k) == "number" and k == k and k >= 1 and k < 1e9 then k else nil
end

-- Front edge of the zone ahead of the root (studs) before the cap: the snout tip plus the slack.
function MouthReach.uncappedFront(speciesId: any, scale: any): number
    local row = rowOf(speciesId)
    if not row then return MouthReach.legacyRadius(scale) end
    return row.snout * growthOf(scale) + MouthReach.slack()
end

-- (offset of the pickup point ahead of the root, radius) for a species at a growth scale, with an optional cap factor (default: the config one).
function MouthReach.zone(speciesId: any, scale: any, capK: number?): (number, number)
    if not rowOf(speciesId) then return 0, MouthReach.legacyRadius(scale) end
    local radius, front = MouthReach.uncappedRadius(speciesId, scale), MouthReach.uncappedFront(speciesId, scale)
    local k = if capK ~= nil then capK else MouthReach.capFactor()
    if k ~= nil then
        radius = math.min(radius, k * MouthReach.uncappedRadius(MouthReach.RefSpecies, scale))
        front = math.min(front, k * MouthReach.uncappedFront(MouthReach.RefSpecies, scale))
    end
    return front - radius, radius
end

-- Studs from the root to the head point (the pickup point) along the facing direction, 0 for an unknown species.
function MouthReach.headOffset(speciesId: any, scale: any): number
    return (MouthReach.zone(speciesId, scale))
end

-- Pickup radius around the head point (capped, see MouthReach.capFactor).
function MouthReach.radius(speciesId: any, scale: any): number
    local _, radius = MouthReach.zone(speciesId, scale)
    return radius
end

-- Head point on the ground plane. look = the root's look vector (any length); a vertical or junk look vector gives the root itself.
-- uncapped = true gives the BD-515 centre of the head (predation, MR3) instead of the food pickup point of the BD-521 capped zone.
function MouthReach.point(rootX: number, rootZ: number, lookX: number, lookZ: number, speciesId: any, scale: any, uncapped: boolean?): (number, number)
    local lx, lz = finite(lookX, 0), finite(lookZ, 0)
    local length = math.sqrt(lx * lx + lz * lz)
    if length < 0.05 then return rootX, rootZ end
    local offset = MouthReach.headOffset(speciesId, scale)
    return rootX + lx / length * offset, rootZ + lz / length * offset
end

-- One server-side check: is a target (a berry, or a victim's root) inside the reach of a dino at the root with this look vector.
-- speciesId = nil gives the old rule (root point, legacy radius). Returns the flat distance to the head point too (nil when out of reach).
function MouthReach.reaches(root: {x: number, y: number, z: number}, look: {x: number, z: number}, speciesId: any, scale: any, target: {x: number, y: number, z: number}): (boolean, number?)
    local id = if MouthReach.has(speciesId) then speciesId else nil
    local px, pz = MouthReach.point(root.x, root.z, look.x, look.z, id, scale)
    local r = if id then MouthReach.radius(id, scale) else MouthReach.legacyRadius(scale)
    local dx, dz = target.x - px, target.z - pz
    local d2 = dx * dx + dz * dz
    if d2 > r * r or math.abs(target.y - root.y) >= MouthReach.VerticalLimit then return false, nil end
    return true, math.sqrt(d2)
end

return MouthReach
