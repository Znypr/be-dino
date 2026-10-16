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
CaveHubLayout.BoxHalfX, CaveHubLayout.BoxHalfZ = 130, 110 -- 260 x 220 footprint box (lead decision, docs/104 s15)
CaveHubLayout.Biome = {minX = -150, maxX = 150, minZ = 450, maxZ = 710} -- island kit never intersects this when on (BD-281: widened from 140/460/700 so the rough 12 stud shell fits)
CaveHubLayout.WallThickness = 8
CaveHubLayout.DropClearance = 5 -- spawn root height above the floor (matches SpawnGeometry.DropClearance)
CaveHubLayout.MaxPathSlopeDeg = 8
CaveHubLayout.MinStationGap = 48
CaveHubLayout.ArrivalSpotsPerStation = 6
CaveHubLayout.Baked = false -- true once the owner smooths the shell by hand (BD-281 skips the server fill)
CaveHubLayout.CeilingWall, CaveHubLayout.CeilingCentre = 38, 62 -- studs above the floor
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

-- ---------------------------------------------------------------- floor blob (local coords)
local BASE_X, BASE_Z = 125, 105.5
local function wobble(theta: number): number
    return 1 + 0.025 * math.sin(3 * theta + 0.7) + 0.015 * math.sin(5 * theta + 2.1)
end
-- <= 1 inside the irregular floor blob (a squarish ellipse with a gentle wobble).
local function blobNorm(x: number, dz: number): number
    local w = wobble(math.atan2(dz, x))
    local nx, nz = math.abs(x) / (BASE_X * w), math.abs(dz) / (BASE_Z * w)
    return (nx ^ 3 + nz ^ 3) ^ (1 / 3)
end
-- True when a disc of `margin` studs around (x, dz) is inside the floor blob.
local function insideFloorLocal(x: number, dz: number, margin: number): boolean
    if blobNorm(x, dz) > 1 then return false end
    if margin <= 0 then return true end
    for i = 0, 11 do
        local a = i * math.pi / 6
        if blobNorm(x + margin * math.cos(a), dz + margin * math.sin(a)) > 1 then return false end
    end
    return true
end
-- BD-281: floor-blob norm in WORLD coordinates (<= 1 inside the floor blob), and the blob's base radii, for the terrain rules.
function CaveHubLayout.floorNorm(x: number, z: number): number
    return blobNorm(x, z - CaveHubLayout.CenterZ)
end
CaveHubLayout.BaseX, CaveHubLayout.BaseZ = BASE_X, BASE_Z
function CaveHubLayout.insideFloor(x: number, z: number, margin: number?): boolean
    return insideFloorLocal(x, z - CaveHubLayout.CenterZ, margin or 0)
end
-- Ceiling height above the floor at a local point (38 at the walls, 62 over the centre).
local function ceilingAbove(x: number, dz: number): number
    local n = math.min(blobNorm(x, dz), 1)
    return CaveHubLayout.CeilingWall + (CaveHubLayout.CeilingCentre - CaveHubLayout.CeilingWall) * (1 - n) ^ 0.5
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
    cave_stalagmite_s = {3, 6, 3, 1500, "rocks"},
    cave_stalagmite_l = {7, 12, 7, 3500, "rocks", collider = true},
    cave_stalactite = {3, 9, 3, 1500, "rocks", hang = true},
    cave_rock_round = {6, 4, 5, 2000, "rocks"},
    cave_rock_flat = {8, 1.5, 6, 1500, "rocks"},
    cave_moss_patch = {5, 0.8, 4, 800, "rocks", walk = true},
    cave_moss_hang = {4, 5, 1, 800, "rocks", hang = true},
    rock_mossy_boulder = {6, 4, 5, 3000, "rocks"},
    rock_crystal = {3, 4, 3, 2500, "rocks"},
    rock_pebbles = {3, 0.5, 3, 600, "rocks", walk = true},
    cave_light_cone = {14, 40, 14, 400, "lights", hang = true},
    cave_lava_fall = {40, 32, 6, 5000, "lava", hang = true}, -- BD-295: was 40 x 48
    cave_lava_rim_rock = {5, 3, 4, 1500, "lava"},
    cave_stepping_stone = {4, 0.8, 4, 400, "lava", walk = true},
    lava_pool_disc = {18, 0.3, 18, 200, "lava"}, -- BD-295: 18 wide inside the 22 wide basin, not walkable (was 26 wide, walk = true)
    hub_stall_potion = {14, 10, 7, 5000, "station", collider = true},
    hub_cauldron = {3, 3, 3, 1800, "station"},
    hub_crate = {2.5, 2.5, 2.5, 600, "station"},
    hub_barrel = {2.5, 3, 2.5, 800, "station"},
    hub_lantern_hang = {1.5, 2.5, 1.5, 700, "station", hang = true},
    hub_lantern_post = {1.5, 6, 1.5, 900, "station"},
    hub_sign_stone = {8, 4, 1, 900, "station"},
    hub_sign_arrow = {5, 5, 0.8, 700, "station"},
    hub_banner = {3, 7, 0.3, 400, "station", hang = true},
    hub_forge_altar = {8, 5, 5, 3500, "station", collider = true},
    hub_forge_ring = {12, 0.5, 12, 900, "station", walk = true},
    hub_pedestal = {3, 3.5, 3, 1000, "station"},
    hub_counter_stone = {14, 3.5, 4, 3500, "station", collider = true},
    hub_crystal_l = {8, 12, 8, 4000, "station"},
    hub_crystal_s = {3, 4, 3, 1500, "station"},
    hub_gem_chest = {4, 3, 3, 2500, "station"},
    hub_lectern_book = {3, 4, 3, 2500, "station", collider = true},
    hub_bench_stone = {6, 2, 2, 1500, "station"},
    hub_gong = {3, 4, 1, 2000, "station"},
    hub_cushion_moss = {2.5, 0.8, 2.5, 500, "station", walk = true},
    hub_wall_frame = {8, 10, 1, 1500, "station", hang = true},
    hub_gate_arch = {30, 20, 6, 8000, "station", walk = true, colliders = 2}, -- walk-through arch, two pillar colliders
    hub_straw_mat = {6, 0.5, 6, 600, "station", walk = true},
    hub_nest_ledge = {32, 3, 10, 6000, "station", collider = true},
    nest = {5, 1, 5, 2500, "station", walk = true}, -- existing mesh 102765517629578
    landmark_dino_statue = {4, 5, 4, 8000, "station"}, -- existing, scaled 0.4
    potion_model = {1, 2, 1, 2500, "station", walk = true}, -- existing; stands on the counter
}
CaveHubLayout.Kinds = KINDS

-- Station props: {key, count, mode}. mode: "centre" = on the pad centre, "sign" = at the sign, "back" = the big piece
-- behind the station, "arc" = spread in the outward arc (behind the station, away from the walking approach). Counts follow docs/104 s13 (trimmed where noted).
local STATION_PROPS: {[string]: {{any}}} = {
    nests = {{"hub_nest_ledge", 1, "back"}, {"nest", 5, "arc"}, {"hub_straw_mat", 5, "arc"}, {"hub_lantern_hang", 3, "arc"}, {"hub_sign_stone", 1, "sign"}},
    potions = {{"hub_stall_potion", 1, "back"}, {"potion_model", 4, "arc"}, {"hub_crate", 3, "arc"}, {"hub_barrel", 1, "arc"}, {"hub_cauldron", 1, "arc"}, {"hub_lantern_hang", 2, "arc"}, {"hub_sign_stone", 1, "sign"}},
    fusion = {{"hub_forge_ring", 1, "centre"}, {"hub_forge_altar", 1, "back"}, {"hub_pedestal", 3, "arc"}, {"hub_crate", 2, "arc"}, {"hub_sign_stone", 1, "sign"}},
    style = {{"hub_counter_stone", 1, "back"}, {"hub_crystal_l", 2, "arc"}, {"hub_crystal_s", 5, "arc"}, {"hub_pedestal", 1, "arc"}, {"hub_gem_chest", 1, "arc"}, {"hub_lantern_hang", 2, "arc"}, {"hub_sign_stone", 1, "sign"}},
    index = {{"hub_pedestal", 6, "arc"}, {"landmark_dino_statue", 6, "arc"}, {"hub_banner", 3, "arc"}, {"hub_lectern_book", 1, "back"}, {"hub_bench_stone", 2, "arc"}, {"hub_sign_stone", 1, "sign"}},
    settings = {{"hub_bench_stone", 1, "arc"}, {"hub_lantern_post", 1, "arc"}, {"hub_gong", 1, "arc"}, {"hub_cushion_moss", 2, "arc"}, {"hub_sign_stone", 1, "sign"}},
    fame = {{"hub_wall_frame", 3, "arc"}, {"hub_lantern_post", 2, "arc"}, {"hub_sign_stone", 1, "sign"}},
    gate = {{"hub_gate_arch", 1, "sign"}, {"rock_mossy_boulder", 2, "arc"}, {"hub_sign_arrow", 2, "arc"}},
}
-- Scatter props (rocks, stalagmites, moss ...): {key, count}. Lava props are placed around the pool, light cones in the holes.
local SCATTER = {
    {"cave_stalagmite_l", 8}, {"cave_stalagmite_s", 18}, {"cave_rock_round", 20}, {"cave_rock_flat", 14},
    {"rock_mossy_boulder", 6}, {"rock_crystal", 4}, {"rock_pebbles", 10}, {"cave_moss_patch", 24},
    {"cave_stalactite", 24}, {"cave_moss_hang", 10},
}
local LAVA_PROPS = {rim = 6, steps = 4}

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
local built: any = nil
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

local function buildPaths(stations: {any}): {any}
    local paths = {}
    local function add(id: string, a: any, b: any, width: number, kind: string)
        local dx, dz = b.x - a.x, b.z - a.z
        local len = math.sqrt(dx * dx + dz * dz)
        local ux, uz = dx / len, dz / len
        paths[#paths + 1] = {id = id, kind = kind, width = width, half = width / 2,
            ax = a.x + ux * a.r, az = a.z + uz * a.r, bx = b.x - ux * b.r, bz = b.z - uz * b.r}
    end
    local heart = station("heart")
    for _, s in stations do
        if s.id ~= "heart" then add("star_" .. s.id, heart, s, 12, "star") end
    end
    -- ring path linking neighbours in angular order around the Heart
    local ring = {"gate", "nests", "style", "fame", "fusion", "settings", "index", "potions"}
    for i, id in ring do
        local nextId = ring[i % #ring + 1]
        add("ring_" .. id .. "_" .. nextId, station(id), station(nextId), 10, "ring")
    end
    return paths
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
-- Floor top height: exactly FloorY on pads and paths, gentle 0-1.5 stud undulation elsewhere (docs/104 s2.1).
local function floorHeightLocal(x: number, dz: number): number
    local d = flatDistanceLocal(x, dz)
    local t = math.clamp(d / 8, 0, 1)
    local mask = t * t * (3 - 2 * t)
    local u = 0.75 + 0.75 * math.sin(x * 0.045 + 1.3) * math.cos(dz * 0.05 + 0.4)
    return CaveHubLayout.FloorY + u * mask
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
    built = {stations = stations, byId = STATION_INDEX, paths = {}}
    built.paths = buildPaths(stations)
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
                for _, q in mine do
                    if dist(px, pz, q[1], q[2]) < (br + q[3]) * 0.55 then return false end
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
                    for _ = 1, count do put(key, s.x + math.cos(s.outward) * s.r * 0.55, s.z + math.sin(s.outward) * s.r * 0.55) end
                end
            end
            for _, e in list do -- everything else: first free spot in the outward arc, deepest ring first
                local key, count, mode = e[1], e[2], e[3]
                if mode == "arc" then
                    local br = boundRadius(KINDS[key])
                    for _ = 1, count do
                        local spot = nil
                        for _, rf in {0.7, 0.5, 0.85, 0.3} do
                            for step = 0, 18 do
                                local deg = ((step % 2 == 0) and 1 or -1) * math.ceil(step / 2) * 9
                                local a = s.outward + deg * math.pi / 180
                                local px, pz = s.x + math.cos(a) * s.r * rf, s.z + math.sin(a) * s.r * rf
                                if not spot and free(px, pz, br) then spot = {px, pz} end
                            end
                        end
                        if not spot then
                            local rf = 0.3 + 0.1 * #mine % 0.5
                            local a = s.outward + ((#mine * 37) % 140 - 70) * math.pi / 180
                            spot = {s.x + math.cos(a) * s.r * rf, s.z + math.sin(a) * s.r * rf}
                        end
                        put(key, spot[1], spot[2])
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
        if dist(x, z, POOL.x, POOL.z) < POOL.r + br + 5 then return false end
        if z > FALL.z - 14 then return false end
        for _, q in placed do
            if dist(x, z, q[1], q[2]) < (br + q[3]) * 0.8 then return false end
        end
        return true
    end
    for _, e in SCATTER do
        local key, count = e[1], e[2]
        local k = KINDS[key]
        local br = boundRadius(k)
        local hang = k.hang == true
        local n, tries = 0, 0
        while n < count and tries < 4000 do
            tries += 1
            local x, z
            if key == "cave_moss_hang" then
                -- hang on the wall: on the blob rim, inside it
                local a = rand() * 2 * math.pi
                local w = wobble(a)
                x, z = math.cos(a) * BASE_X * w * 0.97, math.sin(a) * BASE_Z * w * 0.97
                for _ = 1, 8 do
                    if insideFloorLocal(x, z, 1.5) then break end
                    x, z = x * 0.98, z * 0.98
                end
            else
                x, z = (rand() * 2 - 1) * CaveHubLayout.BoxHalfX, (rand() * 2 - 1) * CaveHubLayout.BoxHalfZ
            end
            if clearOfEverything(x, z, br, not hang) then
                n += 1
                placed[#placed + 1] = {x, z, br}
                addProp(key, x, z, rand() * 2 * math.pi, 0.85 + rand() * 0.4, "scatter")
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

-- ---------------------------------------------------------------- budgets (docs/104 s3.1)
CaveHubLayout.Budget = {
    rocks = {parts = 170, tris = 400000}, station = {parts = 120, tris = 300000}, lava = {parts = 12, tris = 20000},
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
