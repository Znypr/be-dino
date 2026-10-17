--!strict
-- BD-475 (docs/142): the rules that make the colossal ancient trees (BD-474) safe to switch on. PURE math, no Instances and no requires, so
-- tools/verify_colossal_lod.py and tools/estimate_world_budget.py run the SAME code the server (Arena) and the client (WorldCulling) run.
-- Everything here is only reached for a colossal tree whose mesh ids are filled in (WorldGeneratedMeshes.Colossal); with empty ids no
-- caller ever builds an entry, so the game is exactly what it was. Numbers are PROVISIONAL until the BD-085 phone pass.
-- "entry" = a row of WorldGeneratedMeshes.Colossal: size = Blender bbox {x, y, z} studs of the intended-size mesh, base = trunk base offset
-- from the bbox centre {x, y} in Blender axes, trunk = {diameter at ~15% height, bare trunk height} (LOD0 only), tris.
local Rules = {}

-- FBX export is axis_forward -Z, axis_up Y (tools/blender/build_colossal_v3.py): Blender (x, y, z) arrives as Roblox (x, z, -y). UNVERIFIED
-- until the first upload (nobody has imported the FBX in Studio yet): if the LOD swap jumps SIDEWAYS after the ids are pasted, flip this sign.
Rules.BlenderYToStudZ = -1
Rules.RootSink = 0.15 -- studs the lowest footprint ray is sunk, the same value as BiomePlacement.Ground.RootSink (asserted by the verifier)

-- Trunk colliders (docs/139 s8 rule 3): three stacked boxes up to the first branch height, widths a share of the trunk diameter measured at
-- 15% of the height (a little wider at the root flare, tapering up). The box side equals the diameter, so the round trunk is inside the box
-- (a dino can never walk into it; the invisible corners stick out at most 0.2 x the diameter).
Rules.Collider = {
    tiers = {{from = 0, to = 1 / 3, width = 1.1}, {from = 1 / 3, to = 2 / 3, width = 1.0}, {from = 2 / 3, to = 1, width = 0.9}},
    maxHeight = 45, -- docs/139 s8: the first branch height; a maxed dino can stand under the lower canopy
    minHeight = 12,
}
-- Grounding: 9 rays (centre + 8 around) at the trunk radius, the bottom goes to the LOWEST hit (minus RootSink), so no side floats; the
-- uphill side is buried instead, which is what a tree on a slope looks like. A bigger correction limit than a small prop (22 degrees x 26 studs).
Rules.Ground = {rays = 9, minHits = 5, maxCorrection = 14}

export type Entry = {size: {number}, base: {number}, trunk: {number}?, tris: number}

function Rules.lod1Key(key: string): string return key .. "_lod1" end

-- Studs per Blender unit once the LOD0 mesh is fitted to `fittedY` studs tall.
function Rules.studsPerUnit(entry: Entry, fittedY: number): number
    return fittedY / entry.size[3]
end

-- Trunk base in the pivot's local XZ (pivot = bbox bottom centre of the fitted LOD0 mesh), studs.
function Rules.trunkOffset(entry: Entry, fittedY: number): (number, number)
    local s = Rules.studsPerUnit(entry, fittedY)
    return entry.base[1] * s, Rules.BlenderYToStudZ * entry.base[2] * s
end

-- LOD1 is fitted to the SAME height as LOD0 (their bboxes differ by up to 1%), and its centre moves so both trunk bases coincide:
-- centre1 = centre0 + base0 - base1 (local XZ, studs). Returns dx, dz of the LOD1 mesh centre from the LOD0 mesh centre.
function Rules.lod1Offset(e0: Entry, e1: Entry, fittedY: number): (number, number)
    local s0, s1 = fittedY / e0.size[3], fittedY / e1.size[3]
    local sign = Rules.BlenderYToStudZ
    return e0.base[1] * s0 - e1.base[1] * s1, sign * (e0.base[2] * s0 - e1.base[2] * s1)
end

-- World position of a point given in the pivot's local XZ (pivot yawed by `yaw`, CFrame.Angles(0, yaw, 0) convention).
function Rules.toWorld(px: number, pz: number, yaw: number, lx: number, lz: number): (number, number)
    local c, s = math.cos(yaw), math.sin(yaw)
    return px + lx * c + lz * s, pz - lx * s + lz * c
end

-- Trunk colliders {cx, cy, cz, width, height, depth, yaw} in the pivot's local studs (already scaled), from the stored `trunk` numbers.
function Rules.colliders(entry: Entry, fittedY: number): {{number}}
    local trunk = entry.trunk :: {number}
    local s = Rules.studsPerUnit(entry, fittedY)
    local cx, cz = Rules.trunkOffset(entry, fittedY)
    local diameter = trunk[1] * s
    local c = Rules.Collider
    local height = math.clamp(trunk[2] * s, c.minHeight, c.maxHeight)
    local out: {{number}} = {}
    for _, tier in c.tiers do
        local h = (tier.to - tier.from) * height
        local w = diameter * tier.width
        table.insert(out, {cx, (tier.from + tier.to) * .5 * height, cz, w, h, w, 0})
    end
    return out
end

-- The ray origins {x, z} under the trunk footprint (world XZ) for a tree placed at (px, pz) with `yaw`.
function Rules.groundPoints(px: number, pz: number, yaw: number, entry: Entry, fittedY: number): {{number}}
    local lx, lz = Rules.trunkOffset(entry, fittedY)
    local wx, wz = Rules.toWorld(px, pz, yaw, lx, lz)
    local r = (entry.trunk :: {number})[1] * Rules.studsPerUnit(entry, fittedY) * .5
    local out: {{number}} = {{wx, wz}}
    local n = Rules.Ground.rays - 1
    for k = 0, n - 1 do
        local a = k * math.pi * 2 / n
        table.insert(out, {wx + math.cos(a) * r, wz + math.sin(a) * r})
    end
    return out
end

-- Pivot y from the ray hits (nil = miss): the lowest hit minus RootSink. Too few hits, or an answer further than maxCorrection from the
-- layout height, keeps the layout height (a wrong ray never throws a tree into the sky or the ground).
function Rules.groundY(layoutY: number, hits: {number?}): number
    local lowest, found = math.huge, 0
    for _, h in hits do
        if h ~= nil and h == h then
            found += 1
            lowest = math.min(lowest, h)
        end
    end
    if found < Rules.Ground.minHits then return layoutY end
    local y = lowest - Rules.RootSink
    if math.abs(y - layoutY) > Rules.Ground.maxCorrection then return layoutY end
    return y
end

-- ------------------------------------------------------------------------------------------ client: radius, LOD swap, budget
export type Settings = {radius: number, ceiling: number, lod0: number, lod0Max: number, triBudget: number, fade: number}

-- Colossal settings of a device class from Config.WorldCulling: the radius is the config value clamped to [normal radius, ceiling]
-- (never smaller than the other props, never above the ceiling: docs/139 Q12, phone 420). Default radius = the normal radius = today.
function Rules.settings(culling: any, class: string): Settings?
    local c = if culling.Colossal then culling.Colossal[class] else nil
    if not c then return nil end
    local normal = culling[class].radius
    local ceiling = math.max(normal, c.ceiling or normal)
    return {radius = math.clamp(c.radius or normal, normal, ceiling), ceiling = ceiling, lod0 = c.lod0, lod0Max = c.lod0Max,
        triBudget = c.triBudget, fade = culling.Colossal.Fade or 0}
end

export type Item = {d: number, state: string, tris0: number, tris1: number}

-- Decide for every colossal tree: "off" (not parented), "lod0" (near, detailed) or "lod1" (far, light). d = horizontal distance to the
-- trunk, studs; state = the previous result (hysteresis keeps a tree from flickering at a border). Nearest first, so the budget starves
-- the far trees: at most `partsLeft` trees (one part each), at most lod0Max trees at LOD0, and the triangles never pass triBudget.
-- A tree beyond the swap distance, or one that does not fit the LOD0 triangles, drops to LOD1; one that does not fit at all is off.
function Rules.assign(items: {Item}, s: Settings, hysteresis: number, partsLeft: number): ({string}, {lod0: number, lod1: number, off: number, tris: number, parts: number})
    local order: {number} = {}
    for i = 1, #items do order[i] = i end
    table.sort(order, function(a, b)
        local da, db = items[a].d, items[b].d
        if da ~= db then return da < db end
        return a < b
    end)
    local out: {string} = {}
    local stats = {lod0 = 0, lod1 = 0, off = 0, tris = 0, parts = 0}
    for _, i in order do
        local it = items[i]
        local state = "off"
        local limit = if it.state ~= "off" then s.radius * hysteresis else s.radius
        if it.d < limit and stats.parts < partsLeft then
            local near = it.d < (if it.state == "lod0" then s.lod0 * hysteresis else s.lod0)
            if near and stats.lod0 < s.lod0Max and stats.tris + it.tris0 <= s.triBudget then
                state = "lod0"
            elseif stats.tris + it.tris1 <= s.triBudget then
                state = "lod1"
            end
        end
        out[i] = state
        if state == "lod0" then
            stats.lod0 += 1
            stats.parts += 1
            stats.tris += it.tris0
        elseif state == "lod1" then
            stats.lod1 += 1
            stats.parts += 1
            stats.tris += it.tris1
        else
            stats.off += 1
        end
    end
    return out, stats
end

-- Transparency 0 (solid) to 1 (gone) for a tree at distance d: solid until the last `fade` share of the radius, gone AT the radius, so
-- the removal at the border (and the hysteresis band behind it) is never seen. fade 0 = off (a plain pop, today's behaviour).
function Rules.fadeAlpha(d: number, radius: number, fade: number): number
    if fade <= 0 then return 0 end
    local start = radius * (1 - fade)
    if d <= start then return 0 end
    return math.clamp((d - start) / (radius - start), 0, 1)
end

return Rules
