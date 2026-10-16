--!strict
-- BD-243 / BD-244 / docs/101 s4-s7: the server's combat rules as a PURE module (no Roblox APIs, positions are any
-- table with X/Y/Z fields) so tools/verify_combat_service.py can drive every branch. src/server/CombatService.luau is
-- the thin glue (remote, attributes, settlement call). Every number comes from CombatConfig and is PROVISIONAL.
--
-- Reward safety (docs/101 s6): this module knows nothing about eggs, catches, crystals or nests. A defeat only fires
-- `world.onDefeat` exactly once per (userId, runId); the service turns that into RunLifecycle.tryEnd, the same
-- idempotent settlement path as "Eaten" and "ManualExit". The assist bonus is a separate server-minted growth amount.
local Cfg = require(script.Parent.CombatConfig)
local Stats = require(script.Parent.CombatStats)
local State = require(script.Parent.CombatState)
local TeamUp = require(script.Parent.CombatTeamUp)
local LowPoly = require(script.Parent.LowPolyDinoAssets)

local Rules = {}

local function num(v: any, fallback: number): number
    if typeof(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return fallback end
    return v
end

local function fail(reason: string): any
    return { ok = false, reason = reason }
end

-- One world per server. `enabled=false` is the flag-off identity: nothing joins, every call is a no-op.
function Rules.new(enabled: boolean): any
    return { enabled = enabled == true, dinos = {}, limiter = TeamUp.newLimiter(), defeats = {}, requests = {}, onDefeat = nil }
end

function Rules.key(userId: any, runId: any): string
    return tostring(userId) .. "|" .. tostring(runId)
end

-- Class per species from the low-poly registry (docs/101 s2, s16); unknown species are Ground.
function Rules.classForSpecies(speciesId: any): string
    local entry = if typeof(speciesId) == "string" then (LowPoly :: any)[speciesId] else nil
    local listed = if typeof(speciesId) == "string" then (Cfg.SpeciesClasses :: any)[speciesId] else nil -- BD-246 config first
    local class = if listed ~= nil then listed elseif entry then entry.class else nil
    if typeof(class) == "string" and (Cfg.Classes :: any)[class] then return class end
    return Cfg.DefaultClass
end

-- Friend shield (docs/101 s7): defeated FriendShieldDefeats times inside the window -> extra protection next run.
function Rules.shieldSeconds(world: any, userId: any, now: any): number
    local list = world.defeats[tostring(userId)]
    if not list then return 0 end
    local n, count = num(now, 0), 0
    for _, t in list do
        if n - t <= Cfg.FriendShieldWindowSeconds then count += 1 end
    end
    return if count >= Cfg.FriendShieldDefeats then Cfg.FriendShieldSeconds else 0
end

function Rules.recordDefeat(world: any, userId: any, now: any)
    local id = tostring(userId)
    local n = num(now, 0)
    local fresh = {}
    for _, t in world.defeats[id] or {} do
        if n - t <= Cfg.FriendShieldWindowSeconds then table.insert(fresh, t) end
    end
    table.insert(fresh, n)
    world.defeats[id] = fresh
end

-- opts = {userId, runId, class, score, now, peaceful, protectedUntil}. Returns the dino (existing one for a repeat join)
-- or nil while the flag is off.
function Rules.join(world: any, opts: any): any
    if not world.enabled or typeof(opts) ~= "table" then return nil end
    local key = Rules.key(opts.userId, opts.runId)
    local existing = world.dinos[key]
    if existing then return existing end
    local class = if typeof(opts.class) == "string" and (Cfg.Classes :: any)[opts.class] then opts.class else Cfg.DefaultClass
    local score = math.max(0, num(opts.score, 0))
    local s = Stats.scale(score)
    local now = num(opts.now, 0)
    local dino = {
        key = key, userId = opts.userId, runId = opts.runId, class = class, score = score, s = s,
        state = State.new(Stats.maxHp(class, s)),
        peaceful = opts.peaceful == true,
        protectedUntil = num(opts.protectedUntil, 0) + Rules.shieldSeconds(world, opts.userId, now),
        lastBiteAt = -1e9, ledger = TeamUp.newLedger(), defeatedBy = nil,
        hpSentByte = -1, hpSentAt = -1e9,
    }
    world.dinos[key] = dino
    return dino
end

function Rules.get(world: any, key: any): any
    return world.dinos[key]
end

-- Run over (settled, left, disconnected): forget the dino. The defeat log stays for the friend shield.
function Rules.leave(world: any, key: any)
    world.dinos[key] = nil
    world.requests[key] = nil
end

-- Growth keeps the HP ratio (docs/101 s3) and never kills or fully heals.
function Rules.setScore(world: any, key: any, score: any): any
    local d = world.dinos[key]
    if not d then return nil end
    d.score = math.max(0, num(score, d.score))
    d.s = Stats.scale(d.score)
    State.setMaxHp(d.state, Stats.maxHp(d.class, d.s))
    return d
end

function Rules.foodHeal(world: any, key: any): number
    local d = world.dinos[key]
    if not d then return 0 end
    return State.healFood(d.state)
end

local function planarUnit(x: any, z: any): (number, number, boolean)
    local px, pz = num(x, 0), num(z, 0)
    local m = math.sqrt(px * px + pz * pz)
    if m < 1e-6 then return 0, 0, false end
    return px / m, pz / m, true
end

-- Rate limit: every request counts (spam is rejected, not queued). True when this request may proceed.
local function allowRequest(world: any, key: string, now: number): boolean
    local fresh = {}
    for _, t in world.requests[key] or {} do
        if now - t < 1 then table.insert(fresh, t) end
    end
    local ok = #fresh < Cfg.BiteRequestsPerSecond
    table.insert(fresh, now)
    world.requests[key] = fresh
    return ok
end

-- Assist bonus on a defeat (docs/101 s5-s6): a whole-number pool capped at BonusCapFraction of the victim's score,
-- split by damage share among assisters, then the repeat-pair limiter; Peaceful dinos get nothing. {[key] = growth}.
function Rules.assistBonuses(world: any, victim: any, now: number): any
    local assisters = TeamUp.assisters(victim.ledger, victim.state.maxHp, now)
    local parts = TeamUp.split(TeamUp.bonusPool(victim.score), assisters)
    local factors = {}
    for key in parts do
        local d = world.dinos[key]
        factors[key] = if d and not d.peaceful then TeamUp.pairFactor(world.limiter, d.userId, victim.userId, now) else 0
    end
    local out = {}
    for key, amount in TeamUp.applyFactors(parts, factors) do
        if amount > 0 then out[key] = amount end
    end
    return out
end

-- BD-311: a body radius in studs. The SERVER measures it from the model's bounding box; junk or missing values fall back to
-- BodyRadiusPerScale * s, and everything is clamped to [0, BodyRadiusMax].
function Rules.bodyRadius(measured: any, s: any): number
    local fallback = Cfg.BodyRadiusPerScale * math.max(1, num(s, 1))
    return math.clamp(num(measured, fallback), 0, Cfg.BodyRadiusMax)
end

-- One validated bite. apos/alook = attacker root position and look vector; candidates = {{key=, pos=, radius=?}} for every
-- other tracked dino (the server supplies them; the client sends NOTHING but the request). Range is measured from BODY
-- SURFACE to body surface (BD-311): reach + attacker radius + target radius, so big bodies can be bitten at their snout. Returns
-- {ok, reason, targetKey, damage, defeated, hp, maxHp, knockX, knockZ, bonuses}.
function Rules.attack(world: any, attackerKey: any, now: any, apos: any, alook: any, candidates: any, leaping: boolean?, attackerRadius: number?): any
    if not world.enabled then return fail("disabled") end
    local a = world.dinos[attackerKey]
    if not a then return fail("unknown") end
    local n = num(now, 0)
    if a.state.phase ~= "Alive" then return fail("dead") end
    if a.peaceful then return fail("peaceful") end
    if not allowRequest(world, a.key, n) then return fail("rate") end
    if n - a.lastBiteAt < Cfg.BiteCooldownSeconds then return fail("cooldown") end
    if apos == nil or alook == nil then return fail("facing") end -- Vector3 or any {X,Y,Z} table
    local lx, lz, facing = planarUnit(alook.X, alook.Z)
    if not facing then return fail("facing") end
    -- Spawn protection ends the moment the player attacks (docs/101 s7).
    if n < a.protectedUntil then a.protectedUntil = n end

    local range = Cfg.BiteRangeBase + Cfg.BiteRangePerScale * a.s + Cfg.BiteRangeSlack + Rules.bodyRadius(attackerRadius, a.s)
    local cosHalf = math.cos(math.rad(Cfg.BiteConeDegrees / 2))
    local best, bestDistance, bx, bz = nil, math.huge, 0, 0
    for _, c in (if typeof(candidates) == "table" then candidates else {}) do
        local t = if typeof(c) == "table" then world.dinos[c.key] else nil
        if t and t ~= a and t.state.phase == "Alive" and not t.peaceful and n >= t.protectedUntil and c.pos ~= nil then
            local dx, dy, dz = num(c.pos.X, 0) - num(apos.X, 0), num(c.pos.Y, 0) - num(apos.Y, 0), num(c.pos.Z, 0) - num(apos.Z, 0)
            local planar = math.sqrt(dx * dx + dz * dz)
            if planar <= range + Rules.bodyRadius(c.radius, t.s) and math.abs(dy) <= Cfg.BiteVerticalLimit then
                local dot = if planar > 1e-6 then (dx * lx + dz * lz) / planar else 1
                if dot >= cosHalf and planar < bestDistance then
                    best, bestDistance = t, planar
                    if planar > 1e-6 then bx, bz = dx / planar, dz / planar else bx, bz = lx, lz end
                end
            end
        end
    end
    if not best then return fail("no_target") end

    a.lastBiteAt = n
    State.touch(a.state, n)
    local extra = TeamUp.crowdMultiplier(best.ledger, n) * (if leaping then Cfg.LeapBiteX else 1)
    local damage = Stats.hit(a.class, a.s, best.class, best.s, 0, extra)
    local applied, defeated = State.damage(best.state, damage, n)
    TeamUp.record(best.ledger, a.key, applied, n)
    local push = Cfg.KnockbackStuds / math.max(1, best.s / Cfg.KnockbackBigScaleDivisor)
    if best.class == "Armored" then push *= 0.5 end
    local result = {
        ok = true, reason = "hit", targetKey = best.key, damage = applied, defeated = defeated,
        hp = best.state.hp, maxHp = best.state.maxHp, knockX = bx * push, knockZ = bz * push, bonuses = {},
    }
    if defeated then
        best.defeatedBy = a.key
        Rules.recordDefeat(world, best.userId, n)
        result.bonuses = Rules.assistBonuses(world, best, n)
        if world.onDefeat then world.onDefeat(best, a, result.bonuses) end
    end
    return result
end

-- Defeated -> Settled exactly once (the service calls the one settlement path when this returns true).
function Rules.settle(world: any, key: any): boolean
    local d = world.dinos[key]
    if not d then return false end
    return State.settle(d.state)
end

-- Regen for everyone alive (docs/101 s4): call at TickHz.
function Rules.tick(world: any, now: any, dt: any)
    if not world.enabled then return end
    for _, d in world.dinos do
        State.regen(d.state, now, dt)
    end
end

function Rules.hpByte(d: any): number
    if not d or d.state.maxHp <= 0 then return 0 end
    return math.clamp(math.floor(d.state.hp / d.state.maxHp * Cfg.HpByteMax + 0.5), 0, Cfg.HpByteMax)
end

-- The one-byte HP to replicate now, or nil when nothing changed / the HpSendHz budget says wait. A defeat (0) is
-- never delayed. Marks the value as sent.
function Rules.pendingHpByte(world: any, key: any, now: any): number?
    local d = world.dinos[key]
    if not d then return nil end
    local byte = Rules.hpByte(d)
    if byte == d.hpSentByte then return nil end
    local n = num(now, 0)
    if byte > 0 and n - d.hpSentAt < 1 / Cfg.HpSendHz then return nil end
    d.hpSentByte, d.hpSentAt = byte, n
    return byte
end

return table.freeze(Rules)
