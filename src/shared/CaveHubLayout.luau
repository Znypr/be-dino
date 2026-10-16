--!strict
-- BD-279/280: the Cave hub layout (docs/104), pure data and math: no Instances, no Vector3, no Config require, so the
-- server, the client and tools/verify_cave_hub.py read the same numbers. Everything is PROVISIONAL (docs/104).
-- Coordinates: world x, z (z = CenterZ + dz); "local" = offsets from the cave centre (0, FloorY, CenterZ), +dz = deeper
-- into the cave (away from the island). Yaw follows Roblox CFrame.Angles(0, yaw, 0) (yaw 0 faces -Z).
-- hub(config) is THE single source for the Sanctuary centre / floor / half extents: SpawnGeometry, FallRecovery (via
-- SpawnGeometry), Arena and Leaderboards read it. With config.CaveHub false it returns the old hub numbers unchanged.
local CaveHubLayout = {}
CaveHubLayout.Version = 1
CaveHubLayout.CenterZ = 580 -- only used when Config.CaveHub is true (the old hub stays at Config.SanctuaryCenterZ)
CaveHubLayout.FloorY = 6 -- same as the old hub floor, so SpawnGeometry / fall recovery keep working
CaveHubLayout.BoxHalfX, CaveHubLayout.BoxHalfZ = 130, 116 -- bounding box of the organic cave (rooms + tunnels), not a room: the floor only fills part of it (docs/104 s16, owner 2026-10-16)
CaveHubLayout.Biome = {minX = -150, maxX = 150, minZ = 450, maxZ = 710} -- island kit never intersects this when on (BD-281: widened from 140/460/700 so the rough 12 stud shell fits)
CaveHubLayout.WallThickness = 8
CaveHubLayout.DropClearance = 5 -- spawn root height above the floor (matches SpawnGeometry.DropClearance)
CaveHubLayout.MaxPathSlopeDeg = 8
CaveHubLayout.MinStationGap = 48
CaveHubLayout.ArrivalSpotsPerStation = 6
CaveHubLayout.Baked = false -- true once the owner smooths the shell by hand (BD-281 skips the server fill)
CaveHubLayout.CeilingEdge = 10 -- studs above the floor at the rock wall; the ceiling domes up to each room / tunnel height (docs/104 s16)
CaveHubLayout.CeilingDomeDepth = 14 -- studs from the wall over which the ceiling rises to its full height
CaveHubLayout.WallNoise = 3.2 -- +- studs of wall relief (two noise octaves): no straight wall faces, no box corners
CaveHubLayout.RockThickness = 12 -- plan distance the rock shell reaches beyond the open cave
CaveHubLayout.TunnelRadius = 11 -- tunnel half width (22 wide); the flat laid-stone path in it is 8 wide
CaveHubLayout.PathHalf = 4
CaveHubLayout.MaxLights = 16

local LEGACY = {halfX = 55, halfZ = 47.5, floorY = 6, biomeHalf = 48}

-- One geometry source for the Sanctuary. `config` needs CaveHub (nil = false) and SanctuaryCenterZ.
function CaveHubLayout.hub(config: any): any
    if config.CaveHub == true then
        return {enabled = true, centerX = 0, centerZ = CaveHubLayout.CenterZ, floorY = CaveHubLayout.FloorY,
            halfX = CaveHubLayout.BoxHalfX, halfZ = CaveHubLayout.BoxHalfZ, biome = CaveHubLayout.Biome}
    end
    local cz = config.SanctuaryCenterZ
    return {enabled = false, centerX = 0, centerZ = cz, floorY = LEGACY.floorY, halfX = LEGACY.halfX, halfZ = LEGACY.halfZ,
        biome = {minX = -LEGACY.halfX, maxX = LEGACY.halfX, minZ = cz - LEGACY.biomeHalf, maxZ = cz + LEGACY.biomeHalf}}
end

local built: any = nil
-- ---------------------------------------------------------------- cave field (local coords)
-- docs/104 s16 (owner 2026-10-16): the cave is NOT a room. It is a union of ROOMS (a central chamber and one alcove per station)
-- joined by short winding TUNNELS (capsules along the walkable paths), with noisy walls. caveSd(x, dz) = signed distance in studs to the
-- cave wall (> 0 inside the open cave). Each room / tunnel also carries a ceiling `height` (studs over the floor at full dome).
-- {id, x, z, rx, rz, height}. Pad radius + 10..13 so every pad has >= 4 studs of clear floor around it after the wall noise.
local ROOMS = {
    {"heart", 0, 0, 31, 31, 58},
    {"gate", 0, -82, 30, 30, 40},
    {"nests", 66, -38, 27, 27, 50},
    {"potions", -66, -38, 25, 25, 50},
    {"fusion", 0, 48, 30, 30, 42},
    {"style", 84, 34, 28, 28, 50},
    {"index", -84, 34, 30, 30, 40},
    {"settings", -48, 76, 24, 24, 34},
    {"fame", 52, 76, 32, 32, 38},
    {"cavern", -4, 86, 34, 21, 54}, -- lava pool + falls
    -- small side caves (nooks) that break up the silhouette; each overlaps a room so none is an isolated bubble
    {"nook_nw", -30, -62, 13, 13, 28}, {"nook_ne", 34, -68, 12, 12, 30}, {"nook_e", 104, 10, 13, 13, 30},
    {"nook_w", -106, 12, 12, 12, 30}, {"nook_sw", -78, 84, 12, 12, 28}, {"nook_se", 78, 98, 11, 11, 28},
    {"nook_s", 26, 98, 10, 10, 28},
}
-- Tunnels: {from, to, waypoints}. Winding on purpose (+-8..15 studs off the straight line) but short; every station is on a loop except the
-- Island gate, so the way back to the Heart is never a dead end.
local LINKS = {
    {"heart", "gate", {{9, -40}, {-8, -60}}},
    {"heart", "nests", {{30, -6}, {50, -22}}},
    {"nests", "style", {{88, -10}}},
    {"style", "fame", {{70, 52}}},
    {"fame", "fusion", {{28, 62}}},
    {"heart", "potions", {{-28, -4}, {-46, -18}}},
    {"potions", "index", {{-60, -2}}},
    {"index", "settings", {{-82, 64}}},
    {"settings", "fusion", {{-28, 68}}},
    {"heart", "fusion", {{-6, 26}}},
}
local function ellipseSd(x: number, dz: number, r: any): number
    local dx, dy = (x - r[2]) / r[4], (dz - r[3]) / r[5]
    return (1 - math.sqrt(dx * dx + dy * dy)) * math.min(r[4], r[5])
end
local function clampN(v: number): number return if v < -1 then -1 elseif v > 1 then 1 else v end
-- relief of the wall, in studs: broad swells plus a finer crumple
local function wallRelief(x: number, dz: number): number
    local n = 0.7 * math.noise(x / 19, dz / 19, 2.3) + 0.3 * math.noise(x / 6.5, dz / 6.5, 7.9)
    return clampN(n * 1.35) * CaveHubLayout.WallNoise
end
-- (sd, ceilingHeightOverFloor) at a local point. Smooth: the height is a weighted blend of the nearby rooms / tunnels.
local function caveField(x: number, dz: number): (number, number)
    CaveHubLayout.get()
    local best, wsum, hsum = -math.huge, 0, 0
    local function take(sd: number, h: number)
        if best == -math.huge then best = sd
        else -- smooth union (k = 8): rooms and tunnels melt into each other, no knife-edge rock slivers between them
            local d = math.max(8 - math.abs(best - sd), 0) / 8
            best = math.max(best, sd) + d * d * 2
        end
        local w = math.exp(math.clamp(sd, -30, 40) / 3.5) -- the deepest room / tunnel dominates; neighbours blend over a few studs
        wsum += w
        hsum += w * h
    end
    for _, r in ROOMS do take(ellipseSd(x, dz, r), r[6]) end
    for _, t in built.tunnels do
        local px, pz = x - t.ax, dz - t.az
        local vx, vz = t.bx - t.ax, t.bz - t.az
        local l2 = vx * vx + vz * vz
        local u = if l2 > 0 then math.clamp((px * vx + pz * vz) / l2, 0, 1) else 0
        local ex, ez = px - vx * u, pz - vz * u
        take(t.r - math.sqrt(ex * ex + ez * ez), t.h)
    end
    local h = if wsum > 0 then hsum / wsum else 30
    return best + wallRelief(x, dz), h
end
-- ceiling height over the floor for a point `sd` studs inside the wall at full height `h`
local function domeHeight(sd: number, h: number): number
    local e = CaveHubLayout.CeilingEdge
    return e + (h - e) * math.sqrt(math.clamp(sd / CaveHubLayout.CeilingDomeDepth, 0, 1))
end
CaveHubLayout.domeHeightAt = domeHeight
-- signed distance to the cave wall in WORLD coordinates (> 0 inside the open cave), and the dome height there
function CaveHubLayout.caveSd(x: number, z: number): number
    return (caveField(x, z - CaveHubLayout.CenterZ))
end
function CaveHubLayout.caveField(x: number, z: number): (number, number)
    return caveField(x, z - CaveHubLayout.CenterZ)
end
local SD_SCALE = 95 -- legacy "norm" unit: floorNorm = 1 - sd / SD_SCALE keeps CaveLightingRules.insideAt (<= 1 inside) unchanged
CaveHubLayout.SdScale = SD_SCALE
function CaveHubLayout.floorNorm(x: number, z: number): number
    return 1 - (caveField(x, z - CaveHubLayout.CenterZ)) / SD_SCALE
end
-- True when a disc of `margin` studs around (x, dz) is inside the open cave (sd is a distance, so sd >= margin).
local function insideFloorLocal(x: number, dz: number, margin: number): boolean
    return (caveField(x, dz)) >= math.max(margin, 0)
end
function CaveHubLayout.insideFloor(x: number, z: number, margin: number?): boolean
    return insideFloorLocal(x, z - CaveHubLayout.CenterZ, margin or 0)
end
-- Ceiling height above the floor at a local point (domes from CeilingEdge at the wall up to the room / tunnel height).
local function ceilingAbove(x: number, dz: number): number
    local sd, h = caveField(x, dz)
    return domeHeight(sd, h)
end
function CaveHubLayout.ceilingY(x: number, z: number): number
    return CaveHubLayout.FloorY + ceilingAbove(x, z - CaveHubLayout.CenterZ)
end

-- ---------------------------------------------------------------- stations (docs/104 s2.2, s6)
-- r = pad radius (half the longer pad side). Offsets are PROVISIONAL and were nudged from the doc table so every pair of
-- stations is >= 48 studs apart and every pad clears the lava pool (docs/104 s2.2 listed settings/fame/fusion too close).
local STATION_DEFS = {
    {id = "heart", x = 0, z = 0, w = 36, d = 36, r = 18, sign = "", rail = "", outward = math.pi / 2},
    {id = "gate", x = 0, z = -80, w = 30, d = 30, r = 15, sign = "ISLAND", rail = "explore"},
    {id = "nests", x = 66, z = -38, w = 34, d = 30, r = 17, sign = "NESTS", rail = "eggs"},
    {id = "potions", x = -66, z = -38, w = 30, d = 26, r = 15, sign = "POTIONS", rail = "potions"},
    {id = "fusion", x = 0, z = 48, w = 40, d = 34, r = 20, sign = "FUSE", rail = "fusion"},
    {id = "style", x = 84, z = 34, w = 36, d = 32, r = 18, sign = "SHOP", rail = "auras"},
    {id = "index", x = -84, z = 34, w = 40, d = 30, r = 20, sign = "DINOS", rail = "collection"},
    {id = "settings", x = -48, z = 76, w = 20, d = 20, r = 10, sign = "QUIET SPOT", rail = "settings"},
    {id = "fame", x = 48, z = 76, w = 24, d = 24, r = 12, sign = "TOP DINOS", rail = ""},
}
local POOL = {x = -4, z = 86, r = 11} -- lava pool (scenic, fenced; local coords)
local FALL = {x = -4, z = 100, width = 40, height = 32, crackHeight = 26} -- lava sheet on the back wall (BD-295: 32 high so it fits under the back-wall ceiling, which is only 38 over the floor)
CaveHubLayout.Pool, CaveHubLayout.Fall = POOL, FALL

-- Ceiling holes: radius over Heart, Potion Stall, Egg Nests, Style Grotto (docs/104 s4).
local HOLE_DEFS = {{"heart", 12}, {"potions", 8}, {"nests", 8}, {"style", 7}} -- BD-281 QA: 7/5/5/4 read as a pin-prick from the floor

-- ---------------------------------------------------------------- prop kinds
-- w, h, d = size in studs (docs/104 s13), tris = PROVISIONAL generated-mesh triangle estimate, group = budget group,
-- walk = flat/walk-over (never blocks arrival or paths), hang = hangs from the ceiling/wall (not a floor prop),
-- collider = needs one invisible collider.
local KINDS: {[string]: any} = {
    cave_stalagmite_s = {4.5, 5.6, 4.4, 1500, "rocks"},
    cave_stalagmite_l = {7, 10, 7, 3500, "rocks", collider = true},
    cave_stalactite = {3, 8.4, 3, 1500, "rocks", hang = true},
    cave_rock_round = {5.1, 2.5, 5, 2000, "rocks"},
    cave_rock_flat = {6, 1.5, 6, 1500, "rocks"},
    cave_moss_patch = {4.8, 1.4, 4.8, 800, "rocks", walk = true},
    cave_moss_hang = {4, 4.3, 0.8, 800, "rocks", hang = true},
    -- BD-284: wall/rim pieces and a cluster (generated 2026-10-16): Props.Rim pieces go on the wall rim, Props.Solid ones collide
    cave_wall_boulder_l = {14, 11, 13.7, 3000, "rocks"},
    cave_wall_pillar = {6, 16.6, 6, 2500, "rocks"},
    cave_wall_arch_small = {10, 5.6, 3.5, 2000, "rocks"},
    cave_stalagmite_cluster = {8, 8.8, 6.3, 3500, "rocks"},
    rock_mossy_boulder = {6, 4, 5, 3000, "rocks"},
    rock_crystal = {3, 4, 3, 2500, "rocks"},
    rock_pebbles = {3, 0.5, 3, 600, "rocks", walk = true},
    cave_light_cone = {14, 40, 14, 400, "lights", hang = true},
    cave_lava_fall = {40, 32, 6, 5000, "lava", hang = true}, -- BD-295: was 40 x 48
    cave_lava_rim_rock = {6, 2.3, 4.3, 1500, "lava"},
    cave_stepping_stone = {6, 1.4, 6, 400, "lava", walk = true},
    lava_pool_disc = {18, 0.3, 18, 200, "lava"}, -- BD-295: 18 wide inside the 22 wide basin, not walkable (was 26 wide, walk = true)
    hub_stall_potion = {14, 10, 7, 5000, "station", collider = true},
    hub_cauldron = {3, 3, 3, 1800, "station"},
    hub_crate = {2.5, 2.5, 2.5, 600, "station"},
    hub_barrel = {2.6, 3.5, 2.6, 800, "station"},
    hub_lantern_hang = {1.5, 2.5, 1.5, 700, "station", hang = true},
    hub_lantern_post = {1.6, 5.8, 1.6, 900, "station"},
    hub_sign_stone = {5.5, 5.5, 2, 900, "station"},
    hub_sign_arrow = {5, 5, 0.8, 700, "station"},
    hub_banner = {5.4, 5.5, 0.8, 400, "station"},
    hub_forge_altar = {8, 5, 5, 3500, "station", collider = true},
    hub_forge_ring = {12, 0.5, 12, 900, "station", walk = true},
    hub_pedestal = {3, 3.5, 3, 1000, "station", collider = true},
    hub_counter_stone = {8.8, 7, 4.5, 3500, "station", collider = true},
    hub_crystal_l = {8, 12, 8, 4000, "station"},
    hub_crystal_s = {3, 4, 3, 1500, "station"},
    hub_gem_chest = {4, 3, 3, 2500, "station"},
    hub_lectern_book = {3, 4, 3, 2500, "station", collider = true},
    hub_bench_stone = {6, 2, 2, 1500, "station"},
    hub_gong = {3.2, 3.2, 1.2, 2000, "station"},
    hub_cushion_moss = {2.6, 2.6, 2.6, 500, "station", walk = true},
    hub_wall_frame = {3.8, 4.5, 0.7, 1500, "station"},
    hub_gate_arch = {24, 24, 8.7, 8000, "station", walk = true, colliders = 2}, -- walk-through arch, two pillar colliders
    hub_straw_mat = {2.3, 0.8, 4, 600, "station", walk = true},
    hub_nest_ledge = {12, 12, 6.4, 6000, "station", collider = true},
    hub_table_wood = {5, 2.8, 3, 1500, "station"},
    hub_statue_triceratops = {5.1, 6.9, 7.5, 3500, "station"},
    hub_statue_trex = {6.8, 7.7, 7.6, 3500, "station"},
    hub_statue_brachiosaurus = {6.5, 9.2, 10, 3500, "station"},
    nest = {5, 1, 5, 2500, "station", walk = true}, -- existing mesh 102765517629578
    landmark_dino_statue = {4, 5, 4, 8000, "station"}, -- existing, scaled 0.4
    potion_model = {1, 2, 1, 2500, "station", walk = true}, -- existing; stands on the counter
}
CaveHubLayout.Kinds = KINDS

-- Station props: {key, count, mode}. mode: "centre" = on the pad centre, "sign" = at the sign, "back" = the big piece
-- behind the station, "arc" = spread in the outward arc (behind the station, away from the walking approach). Counts follow docs/104 s13 (trimmed where noted).
local STATION_PROPS: {[string]: {{any}}} = {
    nests = {{"hub_nest_ledge", 1, "back"}, {"nest", 5, "arc"}, {"hub_straw_mat", 5, "arc"}, {"hub_lantern_post", 1, "arc"}, {"hub_sign_stone", 1, "sign"}},
    potions = {{"hub_stall_potion", 1, "back"}, {"potion_model", 4, "arc"}, {"hub_lantern_post", 1, "arc"}, {"hub_sign_stone", 1, "sign"}},
    fusion = {{"hub_forge_ring", 1, "centre"}, {"hub_forge_altar", 1, "back"}, {"hub_pedestal", 3, "arc"}, {"hub_sign_stone", 1, "sign"}},
    style = {{"hub_counter_stone", 1, "back"}, {"hub_crystal_l", 2, "arc"}, {"hub_crystal_s", 5, "arc"}, {"hub_pedestal", 1, "arc"}, {"hub_gem_chest", 1, "arc"}, {"hub_lantern_post", 1, "arc"}, {"hub_sign_stone", 1, "sign"}},
    index = {{"hub_pedestal", 4, "arc"}, {"hub_statue_triceratops", 1, "arc"}, {"hub_statue_trex", 1, "arc"}, {"hub_statue_brachiosaurus", 1, "arc"}, {"hub_banner", 2, "arc"}, {"hub_lectern_book", 1, "back"}, {"hub_bench_stone", 2, "arc"}, {"hub_sign_stone", 1, "sign"}},
    settings = {{"hub_lantern_post", 1, "arc"}, {"hub_gong", 1, "arc"}, {"hub_cushion_moss", 2, "arc"}, {"hub_bench_stone", 1, "arc"}, {"hub_sign_stone", 1, "sign"}},
    -- Cosy pass (docs/104 s14, owner 2026-10-16): the Heart gets the show-off pedestal (the FIRST hub_pedestal of the Heart is the spot,
    -- CaveLightingRules.ShowOff), stone benches and moss cushions to rest on, and two lamp posts. Registered assets only.
    heart = {{"hub_pedestal", 1, "arc"}, {"hub_bench_stone", 2, "arc"}, {"hub_cushion_moss", 2, "arc"}, {"hub_lantern_post", 1, "arc"}},
    fame = {{"hub_wall_frame", 3, "arc"}, {"hub_lantern_post", 1, "arc"}, {"hub_sign_stone", 1, "sign"}},
    gate = {{"hub_gate_arch", 1, "sign"}, {"rock_mossy_boulder", 2, "arc"}, {"hub_sign_arrow", 2, "arc"}},
}
-- Scatter props (rocks, stalagmites, moss ...): {key, count}. Lava props are placed around the pool, light cones in the holes.
local SCATTER = {
    -- docs/104 s16 (owner 2026-10-16): decor is reduced and grows out of the rock. Wall pieces, clusters and moss hug the cave wall
    -- (zone "wall"/"edge"); only a few free-standing floor rocks remain, and nothing reads as furniture dropped on the floor.
    {"cave_stalagmite_l", 4, "edge"}, {"cave_stalagmite_s", 6}, {"cave_rock_round", 6, "edge"}, {"cave_rock_flat", 3, "edge"},
    {"rock_mossy_boulder", 3, "edge"}, {"rock_crystal", 4, "edge"}, {"rock_pebbles", 6}, {"cave_moss_patch", 10, "edge"},
    {"cave_stalactite", 24}, {"cave_moss_hang", 10},
    {"cave_stalagmite_cluster", 4, "wall"}, {"cave_wall_boulder_l", 16, "wall"}, {"cave_wall_pillar", 10, "wall"}, {"cave_wall_arch_small", 4, "wall"},
    {"cave_stalagmite_cluster", 4, "edge"}, {"cave_stalagmite_s", 4, "edge"}, {"cave_moss_patch", 8, "lava"},
}
local WALLPIECES = {cave_wall_boulder_l = true, cave_wall_pillar = true, cave_wall_arch_small = true} -- put against the cave wall
local LAVA_PROPS = {rim = 6, steps = 4}
local CLUSTER_COUNT, CLUSTER_R, CLUSTER_APART = 9, 11, 34 -- floor scatter groups (studs; PROVISIONAL)

-- ---------------------------------------------------------------- small math helpers
local function dist(ax: number, az: number, bx: number, bz: number): number
    return math.sqrt((ax - bx) ^ 2 + (az - bz) ^ 2)
end
-- yaw that makes a CFrame face the direction (dx, dz): yaw 0 faces -Z
local function yawTo(dx: number, dz: number): number
    return math.atan2(-dx, -dz)
end
CaveHubLayout.yawTo = yawTo
local function segDist(px: number, pz: number, ax: number, az: number, bx: number, bz: number): number
    local vx, vz = bx - ax, bz - az
    local len2 = vx * vx + vz * vz
    local t = if len2 > 0 then math.clamp(((px - ax) * vx + (pz - az) * vz) / len2, 0, 1) else 0
    return dist(px, pz, ax + vx * t, az + vz * t)
end
-- distance from (px, pz) to an oriented box {x, z, yaw, w, d}; 0 inside (Roblox yaw axes)
local function boxDist(px: number, pz: number, b: any): number
    local dx, dz = px - b.x, pz - b.z
    local c, s = math.cos(b.yaw), math.sin(b.yaw)
    local lx, lz = dx * c - dz * s, dx * s + dz * c -- local = R(-yaw) applied with x axis (cos, -sin), z axis (sin, cos)
    local ox, oz = math.max(math.abs(lx) - b.w / 2, 0), math.max(math.abs(lz) - b.d / 2, 0)
    return math.sqrt(ox * ox + oz * oz)
end
CaveHubLayout.boxDist = boxDist

-- ---------------------------------------------------------------- build (cached, deterministic)
local STATION_INDEX: {[string]: any} = {}

local function station(id: string): any return STATION_INDEX[id] end

local function buildStations(): {any}
    local list = {}
    for _, def in STATION_DEFS do
        local outward = if def.outward then def.outward else math.atan2(def.z, def.x)
        local inward = outward + math.pi
        local signR = def.r * 0.78
        local signX, signZ = def.x + math.cos(outward) * signR, def.z + math.sin(outward) * signR
        local spots = {}
        local n = CaveHubLayout.ArrivalSpotsPerStation
        local spotR = def.r - 3
        for i = 1, n do
            local a = inward + (-70 + 140 * (i - 1) / (n - 1)) * math.pi / 180
            local sx, sz = def.x + math.cos(a) * spotR, def.z + math.sin(a) * spotR
            spots[i] = {x = sx, z = sz, yaw = if def.sign ~= "" then yawTo(signX - sx, signZ - sz) else yawTo(math.cos(outward), math.sin(outward))}
        end
        local item = {id = def.id, rail = def.rail, x = def.x, z = def.z, w = def.w, d = def.d, r = def.r, sign = def.sign,
            outward = outward, signX = signX, signZ = signZ, spots = spots, arrivalSpots = spots,
            cameraYaw = if def.sign ~= "" then yawTo(signX - def.x, signZ - def.z) else yawTo(math.cos(outward), math.sin(outward)),
            hasHole = false, holeRadius = 0}
        for _, h in HOLE_DEFS do
            if h[1] == def.id then item.hasHole, item.holeRadius = true, h[2] end
        end
        list[#list + 1] = item
        STATION_INDEX[def.id] = item
    end
    return list
end

-- Paths = the flat laid-stone way along every tunnel, one record per straight piece (so a winding tunnel is several paths). Each piece
-- joins two graph NODES (station centres or tunnel waypoints, L.nodes): `a`/`b`. ax..bz are the flat segment (clipped at the pad edge of a
-- station end). built.tunnels are the centre-to-centre capsules that carve the tunnel (radius TunnelRadius).
local function buildPaths(stations: {any}): ({any}, {any}, {[string]: any})
    local paths, tunnels = {}, {}
    local nodes: {[string]: any} = {}
    for _, s in stations do nodes[s.id] = {x = s.x, z = s.z, r = s.r} end
    for _, link in LINKS do
        local chain = {link[1]}
        for i, wp in link[3] do
            local id = string.format("w_%s_%s_%d", link[1], link[2], i)
            nodes[id] = {x = wp[1], z = wp[2], r = 0}
            chain[#chain + 1] = id
        end
        chain[#chain + 1] = link[2]
        for i = 1, #chain - 1 do
            local ia, ib = chain[i], chain[i + 1]
            local a, b = nodes[ia], nodes[ib]
            local dx, dz = b.x - a.x, b.z - a.z
            local len = math.sqrt(dx * dx + dz * dz)
            local ux, uz = dx / len, dz / len
            paths[#paths + 1] = {id = string.format("%s_%s_%d", link[1], link[2], i), kind = "tunnel", width = CaveHubLayout.PathHalf * 2, half = CaveHubLayout.PathHalf,
                a = ia, b = ib, ax = a.x + ux * a.r, az = a.z + uz * a.r, bx = b.x - ux * b.r, bz = b.z - uz * b.r}
            tunnels[#tunnels + 1] = {ax = a.x, az = a.z, bx = b.x, bz = b.z, r = CaveHubLayout.TunnelRadius, h = 30}
        end
    end
    -- the stub from the gate pad to the mouth in the north wall (flat floor under the arch); not a graph edge
    local g = nodes.gate
    paths[#paths + 1] = {id = "gate_mouth", kind = "mouth", width = 8, half = 4, ax = g.x, az = g.z - g.r, bx = g.x, bz = g.z - 22}
    return paths, tunnels, nodes
end

-- distance beyond the nearest flat zone (pad or path); <= 0 means flat ground
local function flatDistanceLocal(x: number, dz: number): number
    local best = math.huge
    for _, s in STATION_INDEX do
        best = math.min(best, dist(x, dz, s.x, s.z) - s.r)
    end
    for _, p in built.paths do
        best = math.min(best, segDist(x, dz, p.ax, p.az, p.bx, p.bz) - p.half)
    end
    return best
end
function CaveHubLayout.flatDistance(x: number, z: number): number
    CaveHubLayout.get()
    return flatDistanceLocal(x, z - CaveHubLayout.CenterZ)
end
-- Floor top height: exactly FloorY on pads and the laid-stone paths; elsewhere gentle rolling hills and a few low terraces (0..HillMax studs
-- over FloorY, slopes < 20 degrees) that fade in over HillRamp studs from the nearest flat zone (docs/104 s16).
CaveHubLayout.HillMax, CaveHubLayout.HillRamp = 3.0, 18
local function floorHeightLocal(x: number, dz: number): number
    local d = flatDistanceLocal(x, dz)
    d = math.min(d, dist(x, dz, POOL.x, POOL.z) - (POOL.r + 6), dist(x, dz, FALL.x, FALL.z - 6) - 24) -- the lava pool and the falls sit on flat ground
    local gx, gz = math.max(math.abs(x) - 20, 0), math.max(dz + 92, 0) -- the ground under the gate arch (|x| < 20 north of dz -92) stays flat
    d = math.min(d, math.sqrt(gx * gx + gz * gz))
    local t = math.clamp(d / CaveHubLayout.HillRamp, 0, 1)
    local mask = t * t * (3 - 2 * t)
    if mask <= 0 then return CaveHubLayout.FloorY end
    local u = math.clamp(0.5 + 0.9 * (0.75 * math.noise(x / 41, dz / 41, 5.5) + 0.25 * math.noise(x / 15, dz / 15, 1.7)), 0, 1)
    u = u - 0.5 * math.sin(2 * math.pi * 3 * u) / (2 * math.pi * 3) -- terraces: shallow shelves between the swells
    return CaveHubLayout.FloorY + CaveHubLayout.HillMax * u * mask
end
function CaveHubLayout.floorHeight(x: number, z: number): number
    CaveHubLayout.get()
    return floorHeightLocal(x, z - CaveHubLayout.CenterZ)
end

local function boundRadius(kind: any): number
    return math.sqrt(kind[1] ^ 2 + kind[3] ^ 2) / 2
end

function CaveHubLayout.get(): any
    if built then return built end
    local stations = buildStations()
    built = {stations = stations, byId = STATION_INDEX, paths = {}, tunnels = {}, nodes = {}}
    built.paths, built.tunnels, built.nodes = buildPaths(stations)
    built.rooms = {}
    local props = {}
    local seed = 1404
    local function rand(): number
        seed = (seed * 1103515245 + 12345) % 2147483648
        return seed / 2147483648
    end
    local function addProp(key: string, x: number, z: number, yaw: number, scale: number, owner: string, y: number?)
        local k = KINDS[key]
        props[#props + 1] = {key = key, x = x, z = z, yaw = yaw, scale = scale, owner = owner, group = k[5],
            w = k[1] * scale, h = k[2] * scale, d = k[3] * scale, y = y, walk = k.walk == true, hang = k.hang == true,
            collider = k.collider == true, colliders = k.colliders or 0, tris = k[4]}
    end
    -- station props
    for _, s in stations do
        local list = STATION_PROPS[s.id]
        if list then
            local mine = {}
            local function free(px: number, pz: number, br: number): boolean
                if dist(px, pz, s.x, s.z) + br * 0.5 > s.r - 1 then return false end
                for _, pa in built.paths do -- BD-399: keep path mouths clear
                    if segDist(px, pz, pa.ax, pa.az, pa.bx, pa.bz) < pa.half + br + 1.5 then return false end
                end
                for _, sp in s.spots do -- arrival spots stay free (docs/104 s9): nothing stands within 2 studs of a spot
                    if dist(px, pz, sp.x, sp.z) < br + 2.5 then return false end
                end
                for _, q in mine do
                    if dist(px, pz, q[1], q[2]) < (br + q[3]) * 0.95 then return false end -- BD-399: was 0.55 (overlapping station props)
                end
                return true
            end
            local function put(key: string, px: number, pz: number)
                local k = KINDS[key]
                mine[#mine + 1] = {px, pz, boundRadius(k)}
                addProp(key, px, pz, yawTo(s.x - px, s.z - pz), 1, s.id)
            end
            for _, e in list do -- big back pieces and fixed spots first
                local key, count, mode = e[1], e[2], e[3]
                if mode == "centre" then
                    mine[#mine + 1] = {s.x, s.z, 0}
                    addProp(key, s.x, s.z, 0, 1, s.id)
                elseif mode == "sign" then
                    for _ = 1, count do put(key, s.signX, s.signZ) end
                elseif mode == "back" then
                    for _ = 1, count do put(key, s.x + math.cos(s.outward) * s.r * 0.45, s.z + math.sin(s.outward) * s.r * 0.45) end
                end
            end
            for _, e in list do -- everything else: first free spot in the outward arc, deepest ring first
                local key, count, mode = e[1], e[2], e[3]
                if mode == "arc" then
                    local br = boundRadius(KINDS[key])
                    for _ = 1, count do
                        local spot = nil
                        for _, rf in {0.7, 0.5, 0.85, 0.3, 0.6, 0.4, 0.2} do
                            for step = 0, 26 do
                                local deg = ((step % 2 == 0) and 1 or -1) * math.ceil(step / 2) * 9
                                local a = s.outward + deg * math.pi / 180
                                local px, pz = s.x + math.cos(a) * s.r * rf, s.z + math.sin(a) * s.r * rf
                                if not spot and free(px, pz, br) then spot = {px, pz} end
                            end
                        end
                        if spot then put(key, spot[1], spot[2]) end -- BD-399: no room = the prop is dropped (the old fallback spot overlapped other props)
                    end
                end
            end
        end
    end
    -- lava: fall sheet, pool disc, rim rocks (the fence), stepping stones
    addProp("cave_lava_fall", FALL.x, FALL.z, yawTo(0, -1), 1, "lava")
    addProp("lava_pool_disc", POOL.x, POOL.z, 0, 1, "lava")
    for i = 1, LAVA_PROPS.rim do
        local a = (i - 0.5) / LAVA_PROPS.rim * 2 * math.pi
        addProp("cave_lava_rim_rock", POOL.x + math.cos(a) * (POOL.r + 2), POOL.z + math.sin(a) * (POOL.r + 2), -a, 1, "lava")
    end
    for i = 1, LAVA_PROPS.steps do
        local a = (i - 0.5) / LAVA_PROPS.steps * 2 * math.pi + 0.4
        addProp("cave_stepping_stone", POOL.x + math.cos(a) * 6, POOL.z + math.sin(a) * 6, a, 1, "lava")
    end
    -- light cones in the ceiling holes
    local holes = {}
    for _, h in HOLE_DEFS do
        local s = station(h[1])
        holes[#holes + 1] = {station = h[1], x = s.x, z = s.z, radius = h[2], ceilingY = CaveHubLayout.FloorY + ceilingAbove(s.x, s.z)}
        addProp("cave_light_cone", s.x, s.z, 0, 1, h[1])
    end
    built.holes = holes
    built.rooms = {}
    for _, r in ROOMS do built.rooms[#built.rooms + 1] = {id = r[1], x = r[2], z = r[3], rx = r[4], rz = r[5], height = r[6]} end
    -- rock ledges (docs/104 s16): at the back of a station alcove the wall grows a low stone shelf in the same palette, where the old
    -- counters / stalls stood on the floor. Terrain-only (CaveTerrainRules adds them to the shell). Skipped where one would crowd the lava
    -- pool or a path mouth. {owner, x, z, yaw, w, d, h}: oriented box (Roblox yaw), top `h` studs over the floor.
    local ledges = {}
    for _, s in stations do
        if s.id ~= "heart" and s.id ~= "gate" then
            local lx, lz = s.x + math.cos(s.outward) * (s.r + 5), s.z + math.sin(s.outward) * (s.r + 5)
            local lg = {owner = s.id, x = lx, z = lz, yaw = yawTo(math.cos(s.outward), math.sin(s.outward)), w = math.min(2 * s.r - 4, 22), d = 8, h = 3}
            local ok = dist(lx, lz, POOL.x, POOL.z) > POOL.r + 16 and (caveField(lx, lz)) > 0
            for _, p in built.paths do
                if segDist(lx, lz, p.ax, p.az, p.bx, p.bz) < p.half + 14 then ok = false end
            end
            if ok then ledges[#ledges + 1] = lg end
        end
    end
    built.ledges = ledges
    built.props = props
    -- scatter (rejection sampling, deterministic)
    local placed = {}
    local function clearOfEverything(x: number, z: number, br: number, floorProp: boolean): boolean
        if not insideFloorLocal(x, z, br + 2) then return false end
        if not floorProp then return true end
        for _, s in stations do
            if dist(x, z, s.x, s.z) < s.r + br + 2 then return false end
        end
        for _, p in built.paths do
            if segDist(x, z, p.ax, p.az, p.bx, p.bz) < p.half + br + 1.5 then return false end
        end
        for _, lg in built.ledges do
            if boxDist(x, z, lg) < br + 1.5 then return false end
        end
        if dist(x, z, POOL.x, POOL.z) < POOL.r + br + 5 then return false end
        if z > FALL.z - 14 then return false end
        if z < station("gate").z - 16 and math.abs(x) < 24 then return false end -- gate mouth stays clear
        for _, q in placed do
            if dist(x, z, q[1], q[2]) < (br + q[3]) * 1.15 then return false end -- BD-399: scaled radii; 1.15 for the denser clusters (elongated rocks)
        end
        return true
    end
    -- Floor scatter is grouped, not sprinkled: a few cluster centres on free ground (kept apart, off paths and pads), and every
    -- plain floor prop lands within CLUSTER_R of one of them. Walkways stay clear because clearOfEverything still applies.
    local clusters = {}
    do
        local ctries = 0
        while #clusters < CLUSTER_COUNT and ctries < 6000 do
            ctries += 1
            local cx, cz = (rand() * 2 - 1) * CaveHubLayout.BoxHalfX, (rand() * 2 - 1) * CaveHubLayout.BoxHalfZ
            local apart = true
            for _, c in clusters do
                if dist(cx, cz, c[1], c[2]) < CLUSTER_APART then apart = false break end
            end
            if apart and clearOfEverything(cx, cz, CLUSTER_R, true) then clusters[#clusters + 1] = {cx, cz} end
        end
    end
    built.clusters = clusters
    for _, e in SCATTER do
        local key, count, zone = e[1], e[2], e[3]
        local k = KINDS[key]
        local br = boundRadius(k)
        local hang = k.hang == true
        local n, tries = 0, 0
        while n < count and tries < 4000 do
            tries += 1
            local scale = 0.85 + rand() * 0.4
            local x, z
            x, z = (rand() * 2 - 1) * CaveHubLayout.BoxHalfX, (rand() * 2 - 1) * CaveHubLayout.BoxHalfZ
            if zone == "lava" then
                -- moss around the lava glow (the pool itself stays clear)
                local a = rand() * 2 * math.pi
                local r = POOL.r + 9 + rand() * 12
                x, z = POOL.x + math.cos(a) * r, POOL.z + math.sin(a) * r
            end
            if zone == nil and #clusters > 0 and not hang then -- floor groups (main): rocks gather in a few clusters
                local c = clusters[1 + math.floor(rand() * #clusters)]
                local ca, cr = rand() * 2 * math.pi, 2 + rand() * (CLUSTER_R - 2)
                x, z = c[1] + math.cos(ca) * cr, c[2] + math.sin(ca) * cr
            end
            local sd = (caveField(x, z))
            if key == "cave_moss_hang" then
                if sd < 1.5 or sd > 3.5 then continue end -- hangs on the wall itself
            elseif WALLPIECES[key] or zone == "wall" then
                if sd < br * scale + 2 or sd > br * scale + 8 then continue end -- grows out of the wall
            elseif zone == "edge" then
                if sd < br * scale + 2 or sd > br * scale + 16 then continue end
            end
            if clearOfEverything(x, z, br * scale, not hang) then
                n += 1
                placed[#placed + 1] = {x, z, br * scale}
                addProp(key, x, z, rand() * 2 * math.pi, scale, "scatter")
            end
        end
    end
    -- invisible colliders: one per flagged prop, plus the lava fence and the gate pillars
    local colliders = {}
    for _, p in props do
        if p.collider then colliders[#colliders + 1] = {owner = p.key, x = p.x, z = p.z, yaw = p.yaw, w = p.w, d = p.d} end
        for i = 1, p.colliders do colliders[#colliders + 1] = {owner = p.key .. "_pillar" .. i, x = p.x + (i == 1 and -1 or 1) * (p.w / 2 - 1.5), z = p.z, yaw = p.yaw, w = 3, d = p.d} end
    end
    for i = 1, 8 do
        local a = (i - 0.5) / 8 * 2 * math.pi
        colliders[#colliders + 1] = {owner = "lava_fence", x = POOL.x + math.cos(a) * (POOL.r + 2.5), z = POOL.z + math.sin(a) * (POOL.r + 2.5), yaw = -a, w = 11, d = 2}
    end
    built.colliders = colliders
    -- lights (docs/104 s4): Heart 2, one fill per other station, lava 3, crystals 2, forge ring 1
    local lights = {{owner = "heart"}, {owner = "heart"}, {owner = "lava"}, {owner = "lava"}, {owner = "lava"}, {owner = "crystal"}, {owner = "crystal"}, {owner = "forge"}}
    for _, s in stations do
        if s.id ~= "heart" then lights[#lights + 1] = {owner = s.id} end
    end
    built.lights = lights
    -- run-exit gate
    local g = station("gate")
    built.gate = {x = g.x, z = g.z, mouthWidth = 30, archDepth = 6, triggerZ = g.z - 5, triggerHalfWidth = 15, countdown = 1.5, cancelDistance = 3}
    built.spawn = {x = 0, y = CaveHubLayout.FloorY + CaveHubLayout.DropClearance, z = 0} -- local; CaveHubLayout.spawn() gives world
    -- lights-group parts: cones are props; pads, prompt anchors and sign anchors are counted here
    built.padParts = #stations
    built.promptParts = #stations - 1
    built.signParts = #stations - 1
    return built
end

-- Spawn point in world coordinates (Heart centre, a few studs above the floor).
function CaveHubLayout.spawn(): any
    return {x = 0, y = CaveHubLayout.FloorY + CaveHubLayout.DropClearance, z = CaveHubLayout.CenterZ}
end
-- World arrival spots of a station (x, y, z, yaw): the server picks a free one (docs/104 s9).
function CaveHubLayout.arrivalSpots(id: string): {any}
    CaveHubLayout.get()
    local out = {}
    for i, sp in station(id).spots do
        out[i] = {x = sp.x, y = CaveHubLayout.FloorY + CaveHubLayout.DropClearance, z = sp.z + CaveHubLayout.CenterZ, yaw = sp.yaw}
    end
    return out
end

-- ---------------------------------------------------------------- leaderboards (BD-285 QA)
-- The three Fame boards stand in a little arc on the far (east) side of the Fame pad, facing it, so they never stand between a
-- player and the lava falls (QA: the old row beside the falls hid the basin). Local coords; `yaw` faces the pad centre (yaw 0
-- faces -Z, like a Part's front face). Pure: tools/verify_cave_lava.py checks line of sight, floor and pad clearance.
CaveHubLayout.Boards = {radius = 24, anglesDeg = {-65, 0, 65}, width = 22, height = 18.7, y = 17}
function CaveHubLayout.boardSpots(): {any}
    local fame = CaveHubLayout.get().byId.fame
    local B = CaveHubLayout.Boards
    local out = {}
    for i, deg in B.anglesDeg do
        local a = math.rad(deg)
        local x, z = fame.x + math.cos(a) * B.radius, fame.z + math.sin(a) * B.radius
        out[i] = {x = x, z = z, yaw = CaveHubLayout.yawTo(fame.x - x, fame.z - z)}
    end
    return out
end

-- ---------------------------------------------------------------- budgets (docs/104 s3.1)
CaveHubLayout.Budget = {
    rocks = {parts = 190, tris = 400000}, station = {parts = 120, tris = 300000}, lava = {parts = 12, tris = 20000},
    lights = {parts = 48, tris = 10000}, colliders = {parts = 60, tris = 0},
    total = {parts = 410, tris = 730000},
}
function CaveHubLayout.budgetTable(): any
    local L = CaveHubLayout.get()
    local rows = {rocks = {parts = 0, tris = 0}, station = {parts = 0, tris = 0}, lava = {parts = 0, tris = 0},
        lights = {parts = 0, tris = 0}, colliders = {parts = #L.colliders, tris = 0}}
    for _, p in L.props do
        local row = rows[p.group]
        row.parts += 1
        row.tris += p.tris
    end
    -- pads, prompt anchors and sign gui anchors: thin parts (12 triangles each)
    local thin = L.padParts + L.promptParts + L.signParts
    rows.lights.parts += thin
    rows.lights.tris += thin * 12
    local parts, tris = 0, 0
    for _, r in rows do parts += r.parts tris += r.tris end
    rows.total = {parts = parts, tris = tris}
    return rows
end

return CaveHubLayout
