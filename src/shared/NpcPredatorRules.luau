--!strict
-- BD-245 / docs/101 s8, s13, s16: calm NPC predators as a PURE module (no Roblox APIs; positions are plain x/z numbers) so
-- tools/verify_npc_predators.py can drive every branch. src/server/NpcPredatorService.luau is the thin glue (model, Humanoid
-- movement, remote-free; bites go through the SAME CombatRules world as players). Every number is PROVISIONAL.
--
-- Reward safety (docs/101 s6): this module knows nothing about eggs, catches, crystals or nests. An NPC bite is a normal
-- CombatRules.attack, so a defeated player goes through CombatService -> RunLifecycle.tryEnd exactly once and keeps everything
-- earned. Players can defeat an NPC (capped assist bonus only, no eggs, docs/101 s8). With the flag off (`enabled=false`)
-- nothing is ever created: newWorld(false) is inert and every function returns an empty result.
--
-- State machine: patrol -> alert -> chase -> windup -> bite -> (chase | retreat); chase/alert give up quickly or at the leash;
-- retreat walks home and cannot aggro for a few seconds, then back to patrol. Dead NPCs leave the world and come back after
-- RespawnSeconds at a fresh point away from every player.
local Stats = require(script.Parent.CombatStats)
local CombatRules = require(script.Parent.CombatRules)
local CombatConfig = require(script.Parent.CombatConfig)
local Layout = require(script.Parent.IslandLayout)
local BiomeMap = require(script.Parent.BiomeMap)
local Placement = require(script.Parent.BiomePlacement)

local Npc = {}

Npc.Config = table.freeze({
    MaxNpcs = 6, -- HARD cap (docs/101 s13 budgets 8); slots are 1..MaxNpcs and nothing can create a 7th
    MinNpcs = 2, -- with at least one player in a run
    PlayersPerExtraNpc = 3, -- +1 NPC per this many players: 1-3 players -> 2, 4-6 -> 3, ... 12 -> 5
    Species = {"raptor", "baryonyx", "tyrannosaurus", "spinosaurus"}, -- existing Ground predators, same visual path as players
    ScoreMin = 60, -- score -> HP/damage through CombatStats exactly like a player (combat scale s about 1.1 to 1.4)
    ScoreMax = 250,
    VisualScaleMin = 1.0, -- BD-312: the DRAWN size is capped near 1.3x an average player dino (it was 1.5x to 2.4x and filled the camera)
    VisualScaleMax = 1.3,
    RadiusPerVisual = 2.9, -- planar body radius (studs) per visual scale; the service replaces it with the measured model size
    PlayerRadiusFallback = 1.6, -- a player with no measured size
    FadeSeconds = 0.6, -- BD-312: a defeated NPC fades out softly (client side) before the server removes the model
    FadeSecondsReduced = 0.15, -- Reduce Motion
    FadeCleanupExtra = 0.4, -- the server keeps the faded model this much longer so slow clients still see the fade
    RewardCapFraction = 0.05, -- BD-313: a defeat gives each killer at most this share of THEIR OWN current growth, split by damage share
    RewardSlotCooldownSeconds = 120, -- the same NPC slot never pays the same player again inside this window
    RewardMaxPerWindow = 3, -- and one player gets at most this many NPC rewards ...
    RewardWindowSeconds = 300, -- ... per window, whatever the slots
    TickHz = 5, -- service step rate; positions are replicated by Roblox physics, not by us
    AggroRange = 26, -- studs: an NPC only notices a player this close
    AlertSeconds = 0.8, -- stands still and "!" before it chases
    GiveUpRange = 42, -- chase ends beyond this
    ChaseMaxSeconds = 7, -- chase ends after this, whatever happens
    LeashRadius = 70, -- never farther than this from its home point
    PatrolRadius = 38,
    PatrolSpeed = 5, -- studs/s. Players walk 22 (Armored x0.8 = 17.6): every NPC speed is far slower, so you can always run
    ChaseSpeed = 11,
    RetreatSpeed = 9,
    IdleMin = 2,
    IdleMax = 5,
    ArriveDistance = 2,
    WindupSeconds = 0.5, -- docs/101 s8 telegraph
    BiteCooldownSeconds = 2.5, -- NPC-level soft cooldown (CombatRules still enforces its own 0.9 s and 2/s)
    BiteRecoverSeconds = 1.0,
    MaxBitesPerAggro = 2, -- then it loses interest, hit or miss
    TargetGraceSeconds = 4, -- a player who was just bitten cannot be targeted by ANY NPC for this long
    RetreatSeconds = 5, -- minimum time it ignores everybody after giving up
    RetreatMaxSeconds = 12,
    ForgiveSeconds = 15, -- after giving up on a player this NPC ignores that player for this long (no endless re-chasing)
    HomeArrive = 6,
    StuckSeconds = 1.5,
    VerticalLimit = 10, -- ignore players this much higher/lower (cliff tops, leaps)
    RespawnSeconds = 45, -- docs/101 s8, BD-313 (was 30): at least this long before the slot refills
    RespawnJitter = 6,
    RetrySeconds = 2, -- no valid spawn point right now: try again later
    SpawnMinPlayerDistance = 90,
    SpawnMinSeparation = 120,
    SpawnAttempts = 24,
    SpawnEdgeMargin = 70, -- stay this far inside the arena edge
    SpawnMaxSlopeDeg = 18,
    SpawnKeepOutClearance = 3,
    PatrolEdgeMargin = 20,
    PoolMargin = 8,
    SafeCenterX = 0, -- the island start meadow: no NPC ever spawns in, patrols into, or targets a player inside it
    SafeCenterZ = 30,
    SafeRadius = 80,
    SleepRange = 160, -- an NPC with no player this close does nothing at all (no movement, no CPU beyond a distance check)
    Biomes = {"fern", "conifer", "marsh", "badlands", "volcanic"}, -- island biomes; not the beginner meadow
})
local C = Npc.Config

local function num(v: any, fallback: number): number
    if typeof(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return fallback end
    return v
end

local function planar(ax: number, az: number, bx: number, bz: number): (number, number, number)
    local dx, dz = bx - ax, bz - az
    return math.sqrt(dx * dx + dz * dz), dx, dz
end

-- Seeded LCG (deterministic, no globals).
local function newRng(seed: any): any
    local s = math.floor(num(seed, 1)) % 2147483647
    if s <= 0 then s += 2147483646 end
    return {state = s}
end
local function roll(r: any): number
    r.state = (r.state * 48271) % 2147483647
    return r.state / 2147483647
end
local function between(r: any, lo: number, hi: number): number
    return lo + (hi - lo) * roll(r)
end

-- cfg = {half=ArenaHalfWidth, seed=WorldArtSeed}. Pure functions of the shared layout modules.
function Npc.newTerrain(cfg: any): any
    return {half = num(cfg and cfg.half, 416), seed = num(cfg and cfg.seed, 1404)}
end

function Npc.inSafeZone(x: number, z: number): boolean
    return (planar(x, z, C.SafeCenterX, C.SafeCenterZ)) <= C.SafeRadius
end

-- Where an NPC may walk (patrol points and every step it takes): inside the arena, not in a pool, not in the safe meadow.
function Npc.walkable(terrain: any, x: number, z: number): boolean
    local limit = terrain.half - C.PatrolEdgeMargin
    if math.abs(x) > limit or math.abs(z) > limit then return false end
    if Npc.inSafeZone(x, z) then return false end
    if Layout.inPool(x, z, 4) then return false end
    return true
end

function Npc.biomeAt(terrain: any, x: number, z: number): string
    local _, dominant = BiomeMap.weights(x, z, Layout.height(x, z), terrain.seed)
    return dominant
end

-- A point an NPC may spawn at: walkable, well inside the arena, off water, off the placement keep-outs (spring, jump stones,
-- arch, start meadow) and on gentle ground. Returns ok, reason.
function Npc.spawnPointOk(terrain: any, x: number, z: number): (boolean, string)
    local limit = terrain.half - C.SpawnEdgeMargin
    if math.abs(x) > limit or math.abs(z) > limit then return false, "edge" end
    if Npc.inSafeZone(x, z) then return false, "safe_zone" end
    if Layout.inPool(x, z, C.PoolMargin) then return false, "water" end
    if Placement.keepOutClearance(x, z, true) < C.SpawnKeepOutClearance then return false, "keep_out" end
    if Placement.slope(Layout.height, x, z) > C.SpawnMaxSlopeDeg then return false, "steep" end
    local allowed = false
    for _, b in C.Biomes do
        if b == Npc.biomeAt(terrain, x, z) then allowed = true break end
    end
    if not allowed then return false, "biome" end
    return true, "ok"
end

-- enabled=false is the flag-off identity: the world is inert, nothing is ever created, no RNG is consumed.
-- opts.kinematic: the pure module moves NPCs itself (offline tests); the service leaves it false and feeds real positions.
function Npc.newWorld(enabled: boolean, seed: any, terrain: any?, opts: any?): any
    return {
        enabled = enabled == true, rng = newRng(seed), terrain = terrain or Npc.newTerrain(nil),
        slots = {}, respawnAt = {}, serial = 0, grace = {},
        kinematic = opts ~= nil and (opts :: any).kinematic == true, canMove = if opts then (opts :: any).canMove else nil,
    }
end

function Npc.count(world: any): number
    local n = 0
    for _ in world.slots do n += 1 end
    return n
end

function Npc.desiredCount(playerCount: any): number
    local n = math.max(0, math.floor(num(playerCount, 0)))
    if n <= 0 then return 0 end
    return math.min(C.MaxNpcs, C.MinNpcs + (n - 1) // C.PlayersPerExtraNpc)
end

-- Players are plain tables {key,x,y,z,alive,active,peaceful,protectedUntil}. Default-deny: anything not clearly eligible
-- is ignored. `valid` = may be an NPC's target at all; `canBite` additionally respects the post-bite grace.
function Npc.valid(world: any, p: any, now: number): boolean
    if typeof(p) ~= "table" or typeof(p.key) ~= "string" then return false end
    if p.alive ~= true or p.active ~= true then return false end -- dead, settling or not in a run
    if p.peaceful == true then return false end
    if now < num(p.protectedUntil, 0) then return false end -- spawn protection
    local x, z = num(p.x, math.huge), num(p.z, math.huge)
    if x == math.huge or z == math.huge then return false end
    if Npc.inSafeZone(x, z) then return false end
    return true
end

function Npc.canBite(world: any, p: any, now: number): boolean
    if not Npc.valid(world, p, now) then return false end
    return now >= (world.grace[p.key] or 0)
end

-- Nearest bite-able player inside `range` (ties by key, so it is deterministic). Never returns an ineligible player.
function Npc.pickTarget(world: any, npc: any, players: any, now: number, range: number): any
    local best, bestDistance = nil, math.huge
    for _, p in players do
        if Npc.canBite(world, p, now) and ((if npc.ignore then npc.ignore[p.key] else nil) or 0) <= now and math.abs(num(p.y, 0) - npc.y) <= C.VerticalLimit then
            local d = planar(npc.x, npc.z, p.x, p.z)
            if d <= range and (d < bestDistance or (d == bestDistance and best and p.key < best.key)) then
                best, bestDistance = p, d
            end
        end
    end
    return best
end

local function findPlayer(players: any, key: any): any
    for _, p in players do
        if typeof(p) == "table" and p.key == key then return p end
    end
    return nil
end

-- Up to SpawnAttempts random points; the best is the one in the least-populated biome (spread over the island). Needs the
-- point to be far from every player and from every other NPC. Returns x, z, biome or nil.
function Npc.pickSpawn(world: any, players: any, now: number): (number?, number?, string?)
    local limit = world.terrain.half - C.SpawnEdgeMargin
    local counts: {[string]: number} = {}
    for _, other in world.slots do counts[other.biome] = (counts[other.biome] or 0) + 1 end
    local bx, bz, bBiome, bScore = nil, nil, nil, math.huge
    for _ = 1, C.SpawnAttempts do
        local x, z = between(world.rng, -limit, limit), between(world.rng, -limit, limit)
        local ok = Npc.spawnPointOk(world.terrain, x, z)
        if ok then
            for _, p in players do
                if typeof(p) == "table" and planar(x, z, num(p.x, 0), num(p.z, 0)) < C.SpawnMinPlayerDistance then ok = false break end
            end
        end
        if ok then
            for _, other in world.slots do
                if planar(x, z, other.x, other.z) < C.SpawnMinSeparation then ok = false break end
            end
        end
        if ok then
            local biome = Npc.biomeAt(world.terrain, x, z)
            local score = counts[biome] or 0
            if score < bScore then bx, bz, bBiome, bScore = x, z, biome, score end
        end
    end
    return bx, bz, bBiome
end

local function makeNpc(world: any, slot: number, x: number, z: number, biome: string, now: number): any
    local rng = world.rng
    world.serial += 1
    local species = C.Species[1 + math.floor(roll(rng) * #C.Species) % #C.Species]
    local score = math.floor(between(rng, C.ScoreMin, C.ScoreMax))
    local userId, runId = "npc" .. slot, "w" .. world.serial
    local visual = C.VisualScaleMin + (C.VisualScaleMax - C.VisualScaleMin) * math.clamp((score - C.ScoreMin) / math.max(1, C.ScoreMax - C.ScoreMin), 0, 1)
    return {
        visualScale = visual, radius = C.RadiusPerVisual * visual,
        slot = slot, serial = world.serial, userId = userId, runId = runId, key = CombatRules.key(userId, runId),
        species = species, class = CombatRules.classForSpecies(species), score = score, s = Stats.scale(score),
        x = x, y = Layout.height(x, z), z = z, homeX = x, homeZ = z, biome = biome, faceX = 0, faceZ = -1,
        state = "patrol", stateSince = now, idleUntil = now + between(rng, C.IdleMin, C.IdleMax), patrolX = nil, patrolZ = nil,
        noAggroUntil = 0, ignore = {}, targetKey = nil, bitesThisAggro = 0, biteReadyAt = 0, chaseStartedAt = 0, alertUntil = 0,
        windupEndsAt = 0, recoverUntil = 0, stuck = 0, moving = false, speed = 0, goalX = x, goalZ = z, sleeping = false,
        lastX = x, lastZ = z,
    }
end

-- Fill empty slots up to the wanted count (respecting respawn timers and spawn rules) and drop surplus calm NPCs when players
-- leave. players = the active-run players. Returns {spawned = {npc}, removed = {npc}}.
function Npc.populate(world: any, now: number, players: any): any
    local out = {spawned = {}, removed = {}}
    if not world.enabled then return out end
    local active = {}
    for _, p in players do
        if typeof(p) == "table" and p.active == true and p.alive == true then table.insert(active, p) end
    end
    local want = Npc.desiredCount(#active)
    local have = Npc.count(world)
    if have > want then
        for slot = C.MaxNpcs, 1, -1 do
            local npc = world.slots[slot]
            if npc and have > want and (npc.state == "patrol" or npc.sleeping) then
                world.slots[slot] = nil
                have -= 1
                table.insert(out.removed, npc)
            end
        end
    end
    for slot = 1, math.min(want, C.MaxNpcs) do
        if world.slots[slot] == nil and Npc.count(world) < C.MaxNpcs and now >= (world.respawnAt[slot] or 0) then
            local x, z, biome = Npc.pickSpawn(world, active, now)
            if x and z and biome then
                local npc = makeNpc(world, slot, x, z, biome, now)
                world.slots[slot] = npc
                world.respawnAt[slot] = nil
                table.insert(out.spawned, npc)
            else
                world.respawnAt[slot] = now + C.RetrySeconds
            end
        end
    end
    return out
end

-- BD-313: NPC defeats are NOT an egg source. A defeat pays a small growth bonus only: each killer gets floor(share * 5% of THEIR
-- OWN current growth), share = their part of the damage dealt by all killers. Per player and slot the reward repeats only after
-- RewardSlotCooldownSeconds, and a player gets at most RewardMaxPerWindow rewards per RewardWindowSeconds. No eggs, catches or
-- crystals are ever produced here. Pure: the caller supplies the damage ledger and growth values.
function Npc.newRewardLimiter(): any
    return {bySlot = {}, byPlayer = {}}
end

-- assisters = {{id = combat key, damage = number}}, growthOf/userOf = {[combat key] = number / userId}. Returns {[key] = growth}.
function Npc.growthRewards(limiter: any, slotId: any, assisters: any, growthOf: any, userOf: any, now: any): any
    local out = {}
    local n = num(now, 0)
    local total = 0
    for _, a in assisters do total += math.max(0, num(a.damage, 0)) end
    if total <= 0 then return out end
    for _, a in assisters do
        local user = tostring(userOf[a.id])
        local slotKey = user .. ">" .. tostring(slotId)
        local last = limiter.bySlot[slotKey]
        local fresh = {}
        for _, t in limiter.byPlayer[user] or {} do
            if n - t < C.RewardWindowSeconds then table.insert(fresh, t) end
        end
        limiter.byPlayer[user] = fresh
        local amount = math.floor(math.max(0, num(a.damage, 0)) / total * C.RewardCapFraction * math.max(0, num(growthOf[a.id], 0)))
        local cooling = last ~= nil and n - last < C.RewardSlotCooldownSeconds
        if amount >= 1 and not cooling and #fresh < C.RewardMaxPerWindow then
            out[a.id] = amount
            limiter.bySlot[slotKey] = n
            table.insert(fresh, n)
        end
    end
    return out
end

function Npc.fadeSeconds(reduceMotion: boolean): number
    return if reduceMotion then C.FadeSecondsReduced else C.FadeSeconds
end

-- Idle/walk bob for the simple NPC models (BD-312): the caller accumulates phase += dt * bobRate(speed01); bobOffset is the
-- gentle whole-body offset in studs (0 under Reduce Motion). speed01 = 0 (standing) .. 1 (running).
function Npc.bobRate(speed01: number): number
    return 2 + 8 * math.clamp(num(speed01, 0), 0, 1)
end
function Npc.bobOffset(phase: number, speed01: number, reduceMotion: boolean): number
    if reduceMotion then return 0 end
    return math.sin(num(phase, 0)) * (0.04 + 0.16 * math.clamp(num(speed01, 0), 0, 1))
end

-- Remove an NPC (defeated, or fell out of the world) and schedule its respawn.
function Npc.defeated(world: any, slot: number, now: number): any
    local npc = world.slots[slot]
    if not world.enabled or not npc then return nil end
    world.slots[slot] = nil
    world.respawnAt[slot] = now + C.RespawnSeconds + roll(world.rng) * C.RespawnJitter
    return npc
end

local function setFace(npc: any, dx: number, dz: number)
    local m = math.sqrt(dx * dx + dz * dz)
    if m > 1e-6 then npc.faceX, npc.faceZ = dx / m, dz / m end
end

local function halt(npc: any)
    npc.moving, npc.speed = false, 0
end

-- Set the walking goal; in kinematic mode also advance (offline tests). A step into a non-walkable spot is refused (halt).
local function goTo(world: any, npc: any, tx: number, tz: number, speed: number, dt: number): number
    local d, dx, dz = planar(npc.x, npc.z, tx, tz)
    setFace(npc, dx, dz)
    if d <= 1e-6 then halt(npc) return d end
    local stepLen = math.min(speed * math.max(dt, 0.05), d)
    local nx, nz = npc.x + dx / d * stepLen, npc.z + dz / d * stepLen
    if not Npc.walkable(world.terrain, nx, nz) or (world.canMove ~= nil and not world.canMove(npc, nx, nz)) then
        halt(npc)
        npc.blocked = true
        return d
    end
    npc.blocked = false
    npc.goalX, npc.goalZ, npc.speed, npc.moving = tx, tz, speed, true
    if world.kinematic then
        npc.x, npc.z = nx, nz
        npc.y = Layout.height(nx, nz)
    end
    return d
end

local function enter(npc: any, state: string, now: number)
    npc.state, npc.stateSince = state, now
end

local function retreat(npc: any, now: number)
    enter(npc, "retreat", now)
    if npc.targetKey then npc.ignore[npc.targetKey] = now + C.ForgiveSeconds end
    npc.targetKey = nil
    npc.bitesThisAggro = 0
    npc.noAggroUntil = now + C.RetreatSeconds
    npc.patrolX, npc.patrolZ = nil, nil
    halt(npc)
end

local function toPatrol(world: any, npc: any, now: number)
    enter(npc, "patrol", now)
    npc.targetKey = nil
    npc.patrolX, npc.patrolZ = nil, nil
    npc.idleUntil = now + between(world.rng, C.IdleMin, C.IdleMax)
    halt(npc)
end

local function newPatrolPoint(world: any, npc: any)
    for _ = 1, 8 do
        local a = roll(world.rng) * math.pi * 2
        local r = C.PatrolRadius * math.sqrt(roll(world.rng))
        local x, z = npc.homeX + math.cos(a) * r, npc.homeZ + math.sin(a) * r
        if Npc.walkable(world.terrain, x, z) then npc.patrolX, npc.patrolZ = x, z return end
    end
    npc.patrolX, npc.patrolZ = nil, nil
end

local function reach(npc: any): number
    return CombatConfig.BiteRangeBase + CombatConfig.BiteRangePerScale * npc.s
end
Npc.reach = reach

local function stepOne(world: any, npc: any, now: number, dt: number, players: any, events: any)
    -- Far from everybody: do nothing (CPU/network budget). Wake up calm, back on patrol.
    local nearest = math.huge
    for _, p in players do
        if typeof(p) == "table" and p.active == true then
            nearest = math.min(nearest, (planar(npc.x, npc.z, num(p.x, math.huge), num(p.z, math.huge))))
        end
    end
    if nearest > C.SleepRange then
        if not npc.sleeping then
            npc.sleeping = true
            halt(npc)
            toPatrol(world, npc, now)
        end
        npc.lastX, npc.lastZ = npc.x, npc.z
        return
    end
    npc.sleeping = false

    -- Stuck detection from real displacement (physical mode) or refused steps (kinematic mode).
    if npc.moving then
        local moved = planar(npc.lastX, npc.lastZ, npc.x, npc.z)
        if moved < npc.speed * dt * 0.2 then npc.stuck += dt else npc.stuck = 0 end
    else
        npc.stuck = 0
    end
    npc.lastX, npc.lastZ = npc.x, npc.z

    -- Leash: too far from home in any aggro state -> go home.
    local homeDistance = planar(npc.x, npc.z, npc.homeX, npc.homeZ)
    local state = npc.state
    if (state == "alert" or state == "chase" or state == "windup" or state == "bite") and homeDistance > C.LeashRadius then
        retreat(npc, now)
        state = "retreat"
    end

    if state == "patrol" then
        if now >= npc.noAggroUntil then
            local t = Npc.pickTarget(world, npc, players, now, C.AggroRange)
            if t then
                enter(npc, "alert", now)
                npc.targetKey, npc.alertUntil, npc.bitesThisAggro = t.key, now + C.AlertSeconds, 0
                setFace(npc, t.x - npc.x, t.z - npc.z)
                halt(npc)
                return
            end
        end
        if now < npc.idleUntil then halt(npc) return end
        if npc.patrolX == nil then newPatrolPoint(world, npc) end
        if npc.patrolX == nil then npc.idleUntil = now + C.IdleMax halt(npc) return end
        local d = goTo(world, npc, npc.patrolX :: number, npc.patrolZ :: number, C.PatrolSpeed, dt)
        if d <= C.ArriveDistance or npc.stuck >= C.StuckSeconds or npc.blocked then
            npc.patrolX, npc.patrolZ = nil, nil
            npc.idleUntil = now + between(world.rng, C.IdleMin, C.IdleMax)
            npc.stuck = 0
            halt(npc)
        end
    elseif state == "alert" then
        halt(npc)
        local t = findPlayer(players, npc.targetKey)
        if not t or not Npc.valid(world, t, now) then toPatrol(world, npc, now) npc.noAggroUntil = now + 1 return end
        setFace(npc, t.x - npc.x, t.z - npc.z)
        if now >= npc.alertUntil then
            if planar(npc.x, npc.z, t.x, t.z) <= C.AggroRange * 1.3 then
                enter(npc, "chase", now)
                npc.chaseStartedAt = now
            else
                toPatrol(world, npc, now)
                npc.noAggroUntil = now + 1
            end
        end
    elseif state == "chase" then
        local t = findPlayer(players, npc.targetKey)
        if not t or not Npc.valid(world, t, now) then retreat(npc, now) return end
        local d = planar(npc.x, npc.z, t.x, t.z)
        if d > C.GiveUpRange or now - npc.chaseStartedAt > C.ChaseMaxSeconds or npc.stuck >= C.StuckSeconds then
            retreat(npc, now)
            return
        end
        setFace(npc, t.x - npc.x, t.z - npc.z)
        if d <= reach(npc) + npc.radius + math.max(0, num(t.radius, C.PlayerRadiusFallback)) then
            halt(npc)
            if now >= npc.biteReadyAt and Npc.canBite(world, t, now) then
                enter(npc, "windup", now)
                npc.windupEndsAt = now + C.WindupSeconds
            end
        else
            goTo(world, npc, t.x, t.z, C.ChaseSpeed, dt)
        end
    elseif state == "windup" then
        halt(npc)
        local t = findPlayer(players, npc.targetKey)
        if not t or not Npc.valid(world, t, now) then retreat(npc, now) return end
        -- No re-aim during the windup: it keeps the facing it had when the windup began, so a player who moves away dodges.
        if now >= npc.windupEndsAt then
            table.insert(events, {kind = "bite", slot = npc.slot, npcKey = npc.key, targetKey = t.key})
            npc.bitesThisAggro += 1
            npc.biteReadyAt = now + C.BiteCooldownSeconds
            npc.recoverUntil = now + C.BiteRecoverSeconds
            enter(npc, "bite", now)
        end
    elseif state == "bite" then
        halt(npc)
        if now >= npc.recoverUntil then
            local t = findPlayer(players, npc.targetKey)
            if npc.bitesThisAggro >= C.MaxBitesPerAggro or not t or not Npc.valid(world, t, now) then
                retreat(npc, now)
            else
                enter(npc, "chase", now)
            end
        end
    elseif state == "retreat" then
        local d = goTo(world, npc, npc.homeX, npc.homeZ, C.RetreatSpeed, dt)
        local arrived = d <= C.HomeArrive
        local timedOut = now - npc.stateSince > C.RetreatMaxSeconds or npc.stuck >= C.StuckSeconds * 2 or npc.blocked == true
        if timedOut and not arrived and Npc.walkable(world.terrain, npc.x, npc.z) then
            npc.homeX, npc.homeZ = npc.x, npc.z -- cannot get back: call this spot home (still inside the leash)
            arrived = true
        end
        if arrived and now >= npc.noAggroUntil then toPatrol(world, npc, now) end
    end
end

-- One tick for every NPC (slot order = deterministic). players = {key,x,y,z,alive,active,peaceful,protectedUntil} for every
-- tracked player. Returns bite events {kind="bite", slot, npcKey, targetKey}; resolve each with Npc.performBite.
function Npc.step(world: any, now: any, dt: any, players: any): any
    local events = {}
    if not world.enabled then return events end
    local n = num(now, 0)
    local step = math.clamp(num(dt, 0), 0, 1)
    for slot = 1, C.MaxNpcs do
        local npc = world.slots[slot]
        if npc then stepOne(world, npc, n, step, players, events) end
    end
    return events
end

-- Join the NPC into the shared combat world: same class table, HP, damage and regen as a player (CombatStats via CombatRules).
function Npc.joinCombat(world: any, combatWorld: any, npc: any, now: number): any
    if not world.enabled then return nil end
    return CombatRules.join(combatWorld, {userId = npc.userId, runId = npc.runId, class = npc.class, score = npc.score, now = now})
end

-- Resolve one bite event through CombatRules.attack (range, cone, cooldown, spawn protection, peaceful all re-checked there).
-- Candidates are ONLY the players that are valid targets right now. On a hit the victim gets the post-bite grace.
function Npc.performBite(world: any, combatWorld: any, event: any, now: number, players: any): any
    local npc = world.slots[event.slot]
    if not world.enabled or not npc or npc.key ~= event.npcKey then return {ok = false, reason = "gone"} end
    local candidates = {}
    for _, p in players do
        if Npc.canBite(world, p, now) then
            table.insert(candidates, {key = p.key, pos = {X = p.x, Y = num(p.y, 0), Z = p.z}, radius = p.radius})
        end
    end
    local result = CombatRules.attack(combatWorld, npc.key, now, {X = npc.x, Y = npc.y, Z = npc.z}, {X = npc.faceX, Y = 0, Z = npc.faceZ}, candidates, false, npc.radius)
    if result.ok then world.grace[result.targetKey] = now + C.TargetGraceSeconds end
    return result
end

-- Fraction of a target's max HP one NPC bite takes (never-one-shot guard used by the verifier and the service log).
function Npc.biteFraction(npc: any, targetClass: any, targetScore: any): number
    local ts = Stats.scale(targetScore)
    return Stats.hit(npc.class, npc.s, targetClass, ts, 0, 1) / Stats.maxHp(targetClass, ts)
end

-- Cheap budget summary for docs/tests: the most position updates per second all NPCs can cause.
function Npc.budget(): any
    return {maxNpcs = C.MaxNpcs, tickHz = C.TickHz, maxMovesPerSecond = C.MaxNpcs * C.TickHz}
end

return Npc
