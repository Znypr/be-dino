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
-- inside) + Slack. Slack = FoodPickupRadius - the Compy's half head, so a Compy at scale 1 keeps exactly the old 2.25, and because its half head
-- grows about 0.8 stud per scale (the old rule gave 0.75) a Compy stays within 5% of the old radius at every growth scale.
local Config = require(script.Parent.Config)
local ScaleLadder = require(script.Parent.ScaleLadder)

local MouthReach = {}
MouthReach.MinHeadFraction = 0.20
MouthReach.MaxHeadFraction = 0.25
MouthReach.VerticalLimit = 6 -- studs of height difference between the root and the food, unchanged from the root-based rule
MouthReach.LegacyGrowthBonus = 0.75 -- studs per growth scale of the old rule (used for species without a measured row)
MouthReach.LegacyMaxRadius = 5
MouthReach.RefSpecies = "compy"

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

function MouthReach.has(speciesId: any): boolean
    return rowOf(speciesId) ~= nil
end

-- Studs from the root to the snout tip along the facing direction (the "mouth"), 0 for an unknown species.
function MouthReach.snoutOffset(speciesId: any, scale: any): number
    local row = rowOf(speciesId)
    return if row then row.snout * growthOf(scale) else 0
end

-- Studs from the root to the head point (the centre of the head) along the facing direction, 0 for an unknown species.
function MouthReach.headOffset(speciesId: any, scale: any): number
    local row = rowOf(speciesId)
    if not row then return 0 end
    return (row.snout - headLength1(row) / 2) * growthOf(scale)
end

-- The old root-based radius (and the radius of a species without a measured row).
function MouthReach.legacyRadius(scale: any): number
    return math.min(MouthReach.LegacyMaxRadius, Config.FoodPickupRadius + (growthOf(scale) - 1) * MouthReach.LegacyGrowthBonus)
end

-- Pickup radius around the head point.
function MouthReach.radius(speciesId: any, scale: any): number
    local row = rowOf(speciesId)
    if not row then return MouthReach.legacyRadius(scale) end
    local ref = rowOf(MouthReach.RefSpecies)
    local refHalf = if ref then headLength1(ref) / 2 else 0
    local slack = Config.FoodPickupRadius - refHalf
    return headLength1(row) / 2 * growthOf(scale) + slack
end

-- Head point on the ground plane. look = the root's look vector (any length); a vertical or junk look vector gives the root itself.
function MouthReach.point(rootX: number, rootZ: number, lookX: number, lookZ: number, speciesId: any, scale: any): (number, number)
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
