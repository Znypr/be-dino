--!strict
-- BD-1244 (owner 2026-11-16 "game still looks empty", "Yes, build all"): calm ambient life on the World V3 island. Butterfly flocks beside
-- the paths, dragonflies over the water, gulls crossing the sky and 2-4 small wild baby dinos grazing near the paths in every zone.
-- Look only, CLIENT ONLY (src/client/IslandLife.client.luau): nothing here is on the server, nothing collides, nothing can be caught or
-- eaten, no save, economy or reward change. The babies are not NPC predators (no BeDinoNpcs folder, no NpcLowPoly attribute, no Humanoid)
-- and use only herbivore species. Critters are Roblox generate_mesh Models (docs/77, docs/evidence/2026-11-16-world-fill-life); the babies
-- are the V3 low-poly dinos (Shared/LowPolyDinoAssets) animated with the BD-1217 clips (Shared/LowPolyClips, Shared/LowPolyGait).
-- Phone budget (docs/107, BD-1222): a few pooled models, only within CullRadius of the camera, capped per device class.
-- Pure data and rules, no Instances (tools/verify_island_life.py runs it). Active only while Config.IslandLifeEnabled and WorldV3Enabled.
local IslandLife = {}

-- key -> published Model id (numeric string, nothing invented), generate_mesh triangle cap, what it is.
IslandLife.Critters = {
    life_butterfly_orange = {assetId = "119423844496923", tris = 300, what = "toy butterfly, orange and yellow wings with cream spots"},
    life_butterfly_blue = {assetId = "92211125946330", tris = 300, what = "toy butterfly, sky blue and pink wings with white spots"},
    life_dragonfly = {assetId = "90347036204952", tris = 300, what = "toy dragonfly, teal body, pale blue wings"},
    life_gull = {assetId = "102465106637124", tris = 400, what = "toy seagull gliding, white body, grey wings"},
}
IslandLife.FolderName = "IslandLifeModels" -- ReplicatedStorage folder the server loader fills (one MeshPart per key)

-- Herbivores only (the NPC predators are raptor, baryonyx, tyrannosaurus, spinosaurus: Shared/NpcPredatorRules), two per zone.
IslandLife.Babies = {
    meadow = {"triceratops", "parasaurolophus"},
    forest = {"stegosaurus", "brachiosaurus"},
    pine = {"ankylosaurus", "pachycephalosaurus"},
    beach = {"gallimimus", "duck"},
    volcano = {"triceratops", "ankylosaurus"},
}
IslandLife.BigFlock = 1.5 -- the two spawn-plaza flocks: butterflies this much bigger (and one more of them)
IslandLife.BabyScale = .55 -- of the species' own size (a spawn dino is 4.4-6.6 studs tall; a baby triceratops shows about 4.5)
IslandLife.Zones = table.freeze({"meadow", "forest", "pine", "beach", "volcano"})

IslandLife.CullRadius = 150 -- studs from the camera: closer = shown, further = back in the pool (parts removed)
IslandLife.BehindPenalty = 80 -- culling order: a spot behind the camera counts this many studs further away
IslandLife.AnimRadius = 80 -- babies inside this animate at 20 Hz (the LowPolyAnimator range); further out they only move
IslandLife.WanderRadius = 12 -- a baby never strays further than this from its home spot
IslandLife.ShyRadius = 9 -- a player closer than this: the baby looks up and hops (happy clip), at most once per ShyCooldown
IslandLife.ShyCooldown = 20

-- Caps per device class (same classes as WorldCulling / WeatherVisuals: touch + short side under 600 = Phone).
IslandLife.Caps = {
    Desktop = {babiesPerZone = 3, babies = 8, flocks = 4, perFlock = 4, dragonflies = 3, gulls = 3},
    Tablet = {babiesPerZone = 3, babies = 6, flocks = 3, perFlock = 3, dragonflies = 2, gulls = 2},
    Phone = {babiesPerZone = 2, babies = 4, flocks = 2, perFlock = 3, dragonflies = 2, gulls = 2},
}
function IslandLife.capsFor(deviceClass: string): any
    return IslandLife.Caps[deviceClass] or IslandLife.Caps.Phone
end

function IslandLife.enabled(config: any): boolean
    return type(config) == "table" and config.IslandLifeEnabled == true and config.WorldV3Enabled == true
end

-- Deterministic small hash -> 0..1 (no math.random: every client sees the same herd in the same place).
local function hash01(a: number, b: number): number
    local v = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return v - math.floor(v)
end
IslandLife.hash01 = hash01

local function zoneOf(world: any, id: string): any
    for _, zone in world.Zones do if zone.id == id then return zone end end
    return nil
end
local function spokeOf(world: any, zone: any): any
    local mid = (zone.from + zone.to) / 2
    local best, bestD = nil, math.huge
    for _, spoke in world.Spokes do
        local d = math.abs((spoke.angle - mid + 540) % 360 - 180)
        if d < bestD then best, bestD = spoke, d end
    end
    return best
end

-- A spot is good for life when it is on land, in its own zone, off the path and the plaza, out of the lagoon, and not on a steep slope.
function IslandLife.goodSpot(world: any, zoneId: string, x: number, z: number): boolean
    if world.inland(x, z) < 20 and zoneId ~= "beach" then return false end
    if world.inland(x, z) < 6 then return false end
    if world.inPlaza(x, z) then return false end
    if world.path(x, z) > .05 then return false end
    if world.inPool(x, z, 6) then return false end
    local zone = world.zoneAt(x, z)
    if not zone or zone.id ~= zoneId then return false end
    local h, hx, hz = world.height(x, z), world.height(x + 4, z), world.height(x, z + 4)
    return math.abs(hx - h) < 2.5 and math.abs(hz - h) < 2.5
end

-- Home spots for a zone's herd: beside its spoke path (10-15 studs from its middle), spread along it. Deterministic.
function IslandLife.herdSpots(world: any, zoneId: string, count: number): {{x: number, z: number, species: string}}
    local zone = zoneOf(world, zoneId)
    local list = IslandLife.Babies[zoneId]
    if not zone or not list then return {} end
    local spoke = spokeOf(world, zone)
    local out = {}
    local a = math.rad(spoke.angle)
    local ux, uz = math.cos(a), math.sin(a)
    local tries = 0
    local first, span = world.PlazaRadius + 25, math.max(90, spoke.to - world.PlazaRadius - 50) -- a short spoke (volcano) still spreads 90 studs into its zone
    while #out < count and tries < 60 do
        tries += 1
        -- spread evenly along the path (slot #out of count), with a little jitter, so a walk down any path meets them one by one
        local along = first + (#out + .5) / count * span + (hash01(tries, #zoneId) - .5) * span / count * .6
        local side = if hash01(tries, 7) < .5 then -1 else 1
        local off = (10 + hash01(tries, 3) * 5) * side -- just off the path edge (half width 7): the forest bushes hide anything further in
        local x = world.CenterX + ux * along - uz * off
        local z = world.CenterZ + uz * along + ux * off
        local clear = true
        for _, other in out do
            if (other.x - x) ^ 2 + (other.z - z) ^ 2 < 30 * 30 then clear = false break end
        end
        if clear and IslandLife.goodSpot(world, zoneId, x, z) then
            table.insert(out, {x = x, z = z, species = list[1 + (#out % #list)]})
        end
    end
    return out
end

-- The spawn view (owner's screenshot: spawn, looking down the main path toward the giant tree, spoke 70): the nearest grass is 72+ studs
-- out, too far to read, so two babies wander the open plaza either side of the main path (Studio-checked open ground, clear of the stalls),
-- about 55 studs from the spawn camera. Angle and distance from the plaza centre. LEAD decision (owner delegated 2026-10-16), docs/115.
-- Lead review 2026-11-16: three babies 40-60 studs from spawn, a little bigger (scale), so they read in that first frame.
IslandLife.SpawnHerd = {
    {angle = 46, r = 40, species = "triceratops", zone = "meadow", scale = .7},
    {angle = 86, r = 40, species = "stegosaurus", zone = "forest", scale = .7}, -- clear of the BD-1248 Potions shop (Studio scan 2026-11-17)
    {angle = 96, r = 36, species = "parasaurolophus", zone = "forest", scale = .7},
}
function IslandLife.spawnSpots(world: any): {{x: number, z: number, species: string, zone: string, scale: number?}}
    local out = {}
    for _, s in IslandLife.SpawnHerd do
        local x, z = world.polar(s.angle, s.r)
        table.insert(out, {x = x, z = z, species = s.species, zone = s.zone, scale = s.scale})
    end
    return out
end

-- Butterfly flock spots: the flower zones, beside the paths and the ring road. Deterministic.
IslandLife.FlockZones = {meadow = 3, forest = 2, beach = 1, pine = 1}
function IslandLife.flockSpots(world: any): {{x: number, z: number, zone: string, kind: string, big: boolean?}}
    local out = {}
    for _, zoneId in IslandLife.Zones do
        local want = IslandLife.FlockZones[zoneId] or 0
        local zone = zoneOf(world, zoneId)
        if want > 0 and zone then
            local spoke = spokeOf(world, zone)
            local got, tries = 0, 0
            while got < want and tries < 40 do
                tries += 1
                local along = world.PlazaRadius + 10 + hash01(tries, 41 + #zoneId) * (spoke.to - world.PlazaRadius - 30)
                local off = (9 + hash01(tries, 17) * 8) * (if hash01(tries, 5) < .5 then -1 else 1)
                local a = math.rad(spoke.angle + (hash01(tries, 23) - .5) * 30)
                local x = world.CenterX + math.cos(a) * along - math.sin(a) * off
                local z = world.CenterZ + math.sin(a) * along + math.cos(a) * off
                if IslandLife.goodSpot(world, zoneId, x, z) then
                    got += 1
                    table.insert(out, {x = x, z = z, zone = zoneId, kind = if (got + #zoneId) % 2 == 0 then "life_butterfly_orange" else "life_butterfly_blue"})
                end
            end
        end
    end
    -- the spawn plaza: two flocks either side of the main path that greet the player at the first look down it (owner's spawn view)
    -- (lead review 2026-11-16: closer and bigger, so one is clearly visible in the spawn frame)
    local x1, z1 = world.polar(58, 22)
    local x2, z2 = world.polar(84, 20)
    table.insert(out, 1, {x = x1, z = z1, zone = "meadow", kind = "life_butterfly_orange", big = true})
    table.insert(out, 2, {x = x2, z = z2, zone = "meadow", kind = "life_butterfly_blue", big = true})
    return out
end

-- Dragonfly spots: over the lagoon edge (WorldV3.Pools) and below the pine waterfall.
function IslandLife.dragonflySpots(world: any): {{x: number, z: number}}
    local out = {}
    for _, pool in world.Pools do
        table.insert(out, {x = pool.x + pool.rx * .7, z = pool.z})
        table.insert(out, {x = pool.x - pool.rx * .5, z = pool.z + pool.rz * .6})
    end
    for _, mark in world.Landmarks do
        if mark.id == "waterfall" then
            local x, z = world.polar(mark.angle, mark.r - 30)
            table.insert(out, {x = x, z = z})
        end
    end
    return out
end

-- Gull loops: wide slow circles high over the island (studs; height above sea level). Seconds per loop = circumference / speed.
IslandLife.Gulls = {
    {cx = 40, cz = 90, r = 170, y = 78, speed = 16, dir = 1},
    {cx = -60, cz = -20, r = 230, y = 92, speed = 18, dir = -1},
    {cx = 20, cz = 30, r = 120, y = 66, speed = 14, dir = 1},
}
IslandLife.GullYaw = 0 -- degrees: turn of the generated gull mesh so its head points along the flight (Studio-checked)
function IslandLife.gullAt(index: number, t: number): (number, number, number, number)
    local g = IslandLife.Gulls[index]
    local w = g.speed / g.r * g.dir
    local a = t * w + index * 2.1
    local x, z = g.cx + math.cos(a) * g.r, g.cz + math.sin(a) * g.r
    local heading = a + math.pi / 2 * g.dir -- tangent direction (radians in the XZ plane)
    return x, g.y + math.sin(t * .3 + index) * 3, z, heading
end

-- Butterfly path around its flock centre: a slow lazy figure with height bobs. i = member, t = seconds. Offset in studs.
function IslandLife.flutter(i: number, t: number): (number, number, number)
    local s = .35 + .07 * i
    local ox = math.sin(t * s + i * 1.7) * 5 + math.sin(t * s * 2.3 + i) * 1.5
    local oz = math.cos(t * s * .8 + i * 2.9) * 5 + math.cos(t * s * 1.9 + i * .5) * 1.5
    local oy = 3.8 + math.sin(t * 1.3 + i * 2.2) * .9 + math.sin(t * 3.1 + i) * .25 -- above the round bushes (3-6 studs), below the crowns
    return ox, oy, oz
end
-- Wing beat: X scale of the butterfly mesh (1 = open). Quick flaps with short glides.
function IslandLife.flap(i: number, t: number): number
    local beat = math.abs(math.sin(t * 9 + i * 1.3))
    local glide = math.sin(t * .7 + i) > .6
    return if glide then .95 else .35 + .65 * beat
end
-- Dragonfly: darts between hover points; offset from its spot.
function IslandLife.dart(i: number, t: number): (number, number, number)
    local seg = math.floor(t / 1.6 + i * .37)
    local k = math.clamp((t / 1.6 + i * .37 - seg) * 3, 0, 1)
    k = k * k * (3 - 2 * k)
    local function at(n: number): (number, number) return (hash01(n, i) - .5) * 14, (hash01(i, n) - .5) * 14 end
    local ax, az = at(seg)
    local bx, bz = at(seg + 1)
    return ax + (bx - ax) * k, 1.6 + math.sin(t * 2 + i) * .3, az + (bz - az) * k
end

-- Baby behaviour: a small state machine stepped by the client. state = {mode, until, tx, tz, clip}. Pure: the caller passes the roll
-- (0..1 values) so tests are deterministic. Modes: graze (eat clip, repeated), look (look clip), idle, walk (to tx/tz near home).
IslandLife.Moods = {graze = .45, look = .2, idle = .1, walk = .25} -- chance of the next mode
IslandLife.WalkSpeed = 3.2 -- studs per second (a slow amble; the run starts at LowPolyAnimator RUN_SPEED 24)
function IslandLife.nextMode(roll: number): string
    local acc = 0
    for _, mode in {"graze", "look", "idle", "walk"} do
        acc += IslandLife.Moods[mode]
        if roll < acc then return mode end
    end
    return "idle"
end
-- Seconds a mode lasts (walk ends when it arrives, this is its cap).
function IslandLife.duration(mode: string, roll: number): number
    if mode == "graze" then return 2.8 + roll * 2.8 end -- two to four eat clips (1.4 s each)
    if mode == "look" then return 3 end -- one look clip
    if mode == "walk" then return 8 end
    return 1.5 + roll * 2.5
end
-- A walk target near home (inside WanderRadius).
function IslandLife.walkTarget(homeX: number, homeZ: number, rollA: number, rollR: number): (number, number)
    local a = rollA * math.pi * 2
    local r = (.35 + .65 * rollR) * IslandLife.WanderRadius
    return homeX + math.cos(a) * r, homeZ + math.sin(a) * r
end

return IslandLife
