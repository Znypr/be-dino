--!strict
-- BD-1245 + BD-1246 (owner 2026-11-16, spawn screenshot: "game still looks empty"): fill the World V3 island without adding phone cost.
-- Pure data and math, no Instances. Two flags, both need WorldV3Enabled, ToonWorldEnabled and VegetationV2Enabled:
--   GroundDetailEnabled (BD-1245): a darker grass lip along every path and soft darker grass / earth patches in the open grass (terrain
--     material only, 0 parts); along the paths small generated edge-stone rows, pebble clusters and a fallen log per spoke; flower-and-grass
--     patches (one mesh per patch) in the open grass. To pay for them the single ground cover clumps are thinned further (CoverKeep), so the
--     parts near spawn go DOWN overall (BD-1222 phone budget).
--   ThingsToDoEnabled (BD-1246): food you can see from spawn (berries and some fruit moved, inside the food map grid, from the far edge of
--     their own zone to little clusters along the first stretch of each spoke path: the same foods, kinds and per-zone counts) and one small
--     generated set piece beside each spoke (egg nest, signpost, campfire, log jetty, fossil dig).
-- Every mesh is a Roblox generate_mesh Model (docs/77); nothing is code-built. Every number is PROVISIONAL (LEAD).
local WorldFill = {}

-- key -> published Model id (numeric string, filled from the generate_mesh job results; empty = not published, the piece is skipped),
-- the size it is fitted into (studs: longest side, height cap, shorter side; the longest side lies along the path) and what it is.
WorldFill.Assets = {
    fill_pebbles = {assetId = "118507450426245", size = {5, 1.3, 4}, what = "cluster of five smooth pebbles"},
    -- Lead review of #623: the generated edge-stone row (73588589747994) came out as sharp blocky cubes, so the edge stones show the rounded
    -- vegetation v2 mossy rock instead (use = a GeneratedWorld key loaded by VegetationV2; nothing new is uploaded or fetched for it).
    fill_edge_stones = {assetId = "", use = "veg2_rock_mossy", size = {4.2, 2.2, 3.6}, what = "rounded mossy rock (vegetation v2) along the path edge"},
    fill_flower_patch = {assetId = "121062536751756", size = {8, 1.9, 8}, what = "round patch of soft grass clumps with daisies, buttercups and pink flowers"},
    fill_log = {assetId = "76677189977321", size = {8, 4, 3}, what = "short fallen log with moss and a red mushroom"},
    set_egg_nest = {assetId = "100943523462285", size = {12, 7, 12}, what = "twig nest with two cracked dino egg shells"},
    set_signpost = {assetId = "91305330994046", size = {8.5, 12, 7}, what = "wooden signpost with three arrow boards"},
    set_campfire = {assetId = "94349226114379", size = {12, 6, 12}, what = "campfire in a stone ring with two log seats"},
    set_log_bridge = {assetId = "77047493053772", size = {16, 7, 11}, what = "little log footbridge with rope and railings"},
    set_fossil_dig = {assetId = "137570981399607", size = {14, 7, 14}, what = "sand patch with a dino skull, ribs and a shovel (v2; v1 122635853934201 came out as a blue tub, rejected)"},
}

-- Ground cover share kept with GroundDetailEnabled (VegetationV2.CoverKeep is .5): the flower patches take over the open grass.
WorldFill.CoverKeep = .3

-- One set piece per spoke (WorldV3.Spokes angle): preferred distance from the plaza centre and side of the path (+1 left of the walk out).
WorldFill.SetPieces = {
    {spoke = -15, key = "set_egg_nest", along = 128, side = 1, turn = 0},
    {spoke = 70, key = "set_signpost", along = 96, side = -1, turn = 90}, -- turned: its boards face the path -- the main view from spawn: the first thing down the path to the big tree
    {spoke = 145, key = "set_campfire", along = 138, side = 1, turn = 0},
    {spoke = 215, key = "set_log_bridge", along = 0, side = 1, turn = 0}, -- special site: a little jetty at the lagoon shore (see setPieceSites)
    {spoke = 275, key = "set_fossil_dig", along = 120, side = -1, turn = 0},
}
-- Zone names on the signpost (the three boards), short words for children.
WorldFill.SignWords = {"Forest", "Meadow", "Beach"}

-- Food trail: clusters of 3 along the first stretch of every spoke, alternating sides, just inside the path edge.
WorldFill.Trail = {first = 84, step = 17, clusters = 6, gap = 3, inset = 2.5, fruitEvery = 3}
-- Foods only come from this band of distances from the plaza centre (the outer part of the zone inside the phone budget circle of BD-1222, 300
-- studs), so the near grass keeps its own food and the part count within 300 studs of spawn does not change.
WorldFill.DonorMinRadius, WorldFill.DonorMaxRadius = 180, 300
WorldFill.MinSpacing = 2.8 -- the food map's own spacing (tools/food_layer_data_v3.py MIN_SPACING)

local function config(c: any, key: string): boolean
    return type(c) == "table" and c.WorldV3Enabled == true and c.ToonWorldEnabled == true and c.VegetationV2Enabled == true and c[key] == true
end
function WorldFill.groundEnabled(c: any): boolean return config(c, "GroundDetailEnabled") end
function WorldFill.thingsEnabled(c: any): boolean return config(c, "ThingsToDoEnabled") end

function WorldFill.ready(key: string): boolean
    local entry = WorldFill.Assets[key]
    if not entry then return false end
    if entry.use then return true end -- shown with another family's loaded mesh (fetched by that family)
    local id = entry.assetId
    return #id >= 9 and #id <= 18 and string.match(id, "^[1-9]%d*$") == id
end

-- Deterministic 0..1 from integers (no dice).
local function hash(a: number, b: number, c: number): number
    local h = (a * 73856093 + b * 19349663 + c * 83492791) % 1000003
    if h < 0 then h += 1000003 end
    return h / 1000003
end
WorldFill.hash = hash

-- Terrain surface for a column the World V3 rules left to the biome bands (nil = keep the biome pick). Only the grass zones (meadow, forest, pine);
-- the beach and the volcano keep theirs. Lead review of #623: earth on the path rim showed as hard brown voxel hexagons on the sand, so the rim
-- takes the path colour (a brown or rock biome pick there becomes Limestone, grass stays grass) and only the grass varies: soft blotches of the
-- OTHER green (the meadow is mostly Grass, the forest mostly LeafyGrass). No earth spots.
local GREENS = {Grass = "LeafyGrass", LeafyGrass = "Grass"}
function WorldFill.surface(V3: any, x: number, z: number, h: number, picked: string): string?
    if h > 30 then return nil end
    local zone = V3.zoneAt(x, z).id
    if zone ~= "meadow" and zone ~= "forest" and zone ~= "pine" then return nil end
    if V3.path(x, z) > .04 then return if GREENS[picked] then nil else "Limestone" end -- the path rim: grass or path colour, never brown
    if not GREENS[picked] then return nil end
    local blotch = math.noise(x / 34, z / 34, 9.7) + math.noise(x / 11, z / 11, 2.9) * .25
    if blotch > .28 then return GREENS[picked] end
    return nil
end

-- Unit vectors of a spoke (along = out from the plaza, across = to its left).
local function spokeAxes(angle: number): (number, number, number, number)
    local a = math.rad(angle)
    local ux, uz = math.cos(a), math.sin(a)
    return ux, uz, -uz, ux
end
local function at(V3: any, ux: number, uz: number, vx: number, vz: number, along: number, across: number): (number, number)
    return V3.CenterX + ux * along + vx * across, V3.CenterZ + uz * along + vz * across
end

export type Placement = {key: string, x: number, z: number, yaw: number, scale: number, kind: string}
export type Blocker = {x: number, z: number, r: number}

-- A coarse grid of blockers for quick "is this spot clear" checks.
local function grid(blockers: {Blocker}): {[number]: {Blocker}}
    local g: {[number]: {Blocker}} = {}
    for _, b in blockers do
        local key = math.floor(b.x / 16) * 4096 + math.floor(b.z / 16)
        local list = g[key]
        if not list then list = {} g[key] = list end
        table.insert(list, b)
    end
    return g
end
local function clear(g: {[number]: {Blocker}}, x: number, z: number, r: number): boolean
    local cx, cz = math.floor(x / 16), math.floor(z / 16)
    for ix = cx - 2, cx + 2 do
        for iz = cz - 2, cz + 2 do
            for _, b in g[ix * 4096 + iz] or {} do
                local d = r + b.r
                if (b.x - x) ^ 2 + (b.z - z) ^ 2 < d * d then return false end
            end
        end
    end
    return true
end
WorldFill.clear = clear
WorldFill.grid = grid

-- The ground detail along the paths and in the open grass. blockers = trees, rocks, shrubs, logs, landmarks already standing (x, z, radius).
-- Returns placements on the analytic ground (Arena rests them on the real terrain with a ray).
function WorldFill.groundDetail(V3: any, blockers: {Blocker}): {Placement}
    local g = grid(blockers)
    local out: {Placement} = {}
    local function add(key: string, x: number, z: number, yaw: number, scale: number, kind: string, r: number): boolean
        if V3.inPool(x, z, 2) or V3.inPlaza(x, z) or V3.path(x, z) > .35 or not clear(g, x, z, r) then return false end
        table.insert(out, {key = key, x = x, z = z, yaw = yaw, scale = scale, kind = kind})
        table.insert(g[math.floor(x / 16) * 4096 + math.floor(z / 16)] or (function()
            local list = {}
            g[math.floor(x / 16) * 4096 + math.floor(z / 16)] = list
            return list
        end)(), {x = x, z = z, r = r})
        return true
    end
    for si, spoke in V3.Spokes do
        local ux, uz, vx, vz = spokeAxes(spoke.angle)
        local yaw = -math.rad(spoke.angle)
        -- edge stone rows: every 21 studs, alternating sides, just outside the path edge, lying along it
        local i = 0
        local along = V3.PlazaRadius + 12
        while along < spoke.to - 18 do
            local side = if i % 2 == 0 then 1 else -1
            local across = side * (V3.PathHalfWidth + 2.2 + hash(si, i, 1) * 1.2)
            local x, z = at(V3, ux, uz, vx, vz, along, across)
            if V3.height(x, z) < 30 then add("fill_edge_stones", x, z, yaw + (hash(si, i, 2) - .5) * .3, .85 + hash(si, i, 3) * .35, "stones", 4.2) end
            -- a pebble cluster on the other side, a little further on
            local px, pz = at(V3, ux, uz, vx, vz, along + 9, -side * (V3.PathHalfWidth + 1.5 + hash(si, i, 4) * 3))
            add("fill_pebbles", px, pz, hash(si, i, 5) * math.pi * 2, .8 + hash(si, i, 6) * .5, "pebbles", 2)
            i += 1
            along += 21
        end
        -- one fallen log beside each spoke, about halfway out
        for k = 0, 5 do
            local lx, lz = at(V3, ux, uz, vx, vz, spoke.to * .55 + k * 7, (if si % 2 == 0 then 1 else -1) * (V3.PathHalfWidth + 9 + (k % 2) * 3))
            if add("fill_log", lx, lz, yaw + .5 + hash(si, 9, 7) * .6, 1, "log", 4) then break end
        end
    end
    -- flower patches in the open grass: one try per 30-stud cell inside the ring road and a little past it (the spawn views), grass zones only
    for cx = -9, 9 do
        for cz = -9, 9 do
            local u = hash(cx, cz, 11)
            if u > .5 then continue end
            local x = V3.CenterX + (cx + .2 + hash(cx, cz, 12) * .6) * 30
            local z = V3.CenterZ + (cz + .2 + hash(cx, cz, 13) * .6) * 30
            local r = math.sqrt((x - V3.CenterX) ^ 2 + (z - V3.CenterZ) ^ 2)
            if r < V3.PlazaRadius + 8 or r > 265 or V3.path(x, z) > 0 then continue end
            local zone = V3.zoneAt(x, z).id
            if zone ~= "meadow" and zone ~= "forest" and zone ~= "pine" then continue end
            if V3.height(x, z) > 30 then continue end
            add("fill_flower_patch", x, z, hash(cx, cz, 14) * math.pi * 2, .8 + hash(cx, cz, 15) * .45, "patch", 3.6)
        end
    end
    return out
end

-- The set piece sites: the preferred spot first, then further out and nearer in (6-stud steps), the first clear one wins. The jetty stands
-- at the lagoon shore at the end of the beach spoke, pointing at the water.
function WorldFill.setPieceSites(V3: any, blockers: {Blocker}): {Placement}
    local g = grid(blockers)
    local out: {Placement} = {}
    for _, s in WorldFill.SetPieces do
        local entry = WorldFill.Assets[s.key]
        local r = math.max(entry.size[1], entry.size[3]) * .5
        if s.key == "set_log_bridge" then
            local pool = V3.Pools[1]
            local dx, dz = pool.x - V3.CenterX, pool.z - V3.CenterZ
            local d = math.sqrt(dx * dx + dz * dz)
            -- on the line from the plaza to the lagoon centre, the bridge centre right at the shore (half over the water)
            local shore = d - pool.rx * .7 -- the water starts here (measured in Studio 2026-11-16)
            local x, z = V3.CenterX + dx / d * shore, V3.CenterZ + dz / d * shore
            table.insert(out, {key = s.key, x = x, z = z, yaw = -math.atan2(dz, dx), scale = 1, kind = "set"})
            continue
        end
        local ux, uz, vx, vz = spokeAxes(s.spoke)
        local across = s.side * (V3.PathHalfWidth + 3 + r)
        for k = 0, 12 do
            local step = if k == 0 then 0 elseif k % 2 == 1 then (k + 1) // 2 * 6 else -(k // 2) * 6
            local x, z = at(V3, ux, uz, vx, vz, s.along + step, across)
            if clear(g, x, z, r) and not V3.inPool(x, z, 2) then
                -- face the path (the front of a generated mesh is -Z)
                local yaw = math.atan2(s.side * vx, s.side * vz) + math.rad(s.turn or 0)
                table.insert(out, {key = s.key, x = x, z = z, yaw = yaw, scale = 1, kind = "set"})
                break
            end
        end
    end
    return out
end

-- The food trail targets (x, z, kind) for one spoke: clusters of three alternating sides, every third cluster has a fruit in the middle.
function WorldFill.trailTargets(V3: any): {{x: number, z: number, kind: number}}
    local t = WorldFill.Trail
    local out = {}
    for _, spoke in V3.Spokes do
        local ux, uz, vx, vz = spokeAxes(spoke.angle)
        for c = 0, t.clusters - 1 do
            local along = t.first + c * t.step
            if along > spoke.to - 8 then break end
            local side = if c % 2 == 0 then 1 else -1
            local across = side * (V3.PathHalfWidth - t.inset)
            for k = 0, 2 do
                local x, z = at(V3, ux, uz, vx, vz, along + k * t.gap, across + (if k == 1 then -side * 1.2 else 0))
                local kind = if k == 1 and c % t.fruitEvery == t.fruitEvery - 1 then 2 else 1
                table.insert(out, {x = x, z = z, kind = kind})
            end
        end
    end
    return out
end

-- Move foods inside a decoded food map layer (WorldLayer): for every trail target the donor is the same kind, in the same zone, at least
-- DonorMinRadius..DonorMaxRadius from the plaza, the farthest one first (deterministic order). The donor cell becomes 0 and the target cell takes its kind,
-- so the food grid, the kinds and the per-zone counts stay exactly the same. A target whose cell is taken or within MinSpacing of a food is
-- skipped. Starter patches are never touched. Returns the number moved.
function WorldFill.moveFood(V3: any, WorldLayer: any, layer: any, isStarter: (number, number) -> boolean): number
    -- donors per zone and kind, farthest first
    local donors: {[string]: {{ix: number, iz: number, d: number}}} = {}
    local occupied: {[number]: boolean} = {}
    WorldLayer.forEachNonZero(layer, function(ix: number, iz: number, value: number)
        occupied[ix * 100000 + iz] = true
        if value ~= 1 and value ~= 2 then return end
        local x, z = WorldLayer.centreOf(layer, ix, iz)
        local d = math.sqrt((x - V3.CenterX) ^ 2 + (z - V3.CenterZ) ^ 2)
        if d < WorldFill.DonorMinRadius or d > WorldFill.DonorMaxRadius or isStarter(x, z) then return end
        local key = V3.zoneAt(x, z).id .. "|" .. value
        local list = donors[key]
        if not list then list = {} donors[key] = list end
        table.insert(list, {ix = ix, iz = iz, d = d})
    end)
    for _, list in donors do
        table.sort(list, function(a, b) if a.d ~= b.d then return a.d > b.d end if a.ix ~= b.ix then return a.ix < b.ix end return a.iz < b.iz end)
    end
    local cell = layer.cellSize or 0
    local reach = if cell > 0 then math.ceil(WorldFill.MinSpacing / cell) else 4
    local moved = 0
    for _, t in WorldFill.trailTargets(V3) do
        local ix, iz = WorldLayer.cellOf(layer, t.x, t.z)
        if not WorldLayer.contains(layer, ix, iz) then continue end
        local cx, cz = WorldLayer.centreOf(layer, ix, iz)
        if isStarter(cx, cz) then continue end
        local free = true
        for dx = -reach, reach do
            for dz = -reach, reach do
                if occupied[(ix + dx) * 100000 + (iz + dz)] then
                    local ox, oz = WorldLayer.centreOf(layer, ix + dx, iz + dz)
                    if (ox - cx) ^ 2 + (oz - cz) ^ 2 < WorldFill.MinSpacing ^ 2 then free = false end
                end
            end
        end
        if not free then continue end
        local list = donors[V3.zoneAt(cx, cz).id .. "|" .. t.kind]
        local donor = if list then table.remove(list, 1) else nil
        if not donor then continue end
        WorldLayer.setCell(layer, donor.ix, donor.iz, 0)
        occupied[donor.ix * 100000 + donor.iz] = nil
        WorldLayer.setCell(layer, ix, iz, t.kind)
        occupied[ix * 100000 + iz] = true
        moved += 1
    end
    return moved
end

return WorldFill
