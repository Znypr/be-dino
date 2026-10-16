--!strict
-- BD-241 / docs/101 s5: damage ledger, assist split, repeat-pair limiter, crowd cap. Pure; PROVISIONAL numbers.
-- The assist bonus is a separate server-minted amount; run eggs and score are never transferred (docs/101 s6).
local Cfg = require(script.Parent.CombatConfig)
local T = Cfg.TeamUp
local TeamUp = {}

local function num(v: any, fallback: number): number
    if typeof(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return fallback end
    return v
end

-- One ledger per victim.
function TeamUp.newLedger(): any
    return { hits = {} }
end

local function prune(ledger: any, now: number)
    local keep = {}
    for _, h in ledger.hits do
        if now - h.t <= math.max(T.AssistWindowSeconds, T.CrowdWindowSeconds) then table.insert(keep, h) end
    end
    ledger.hits = keep
end

function TeamUp.record(ledger: any, attackerId: any, amount: any, now: any)
    local n = num(now, 0)
    local a = math.max(0, num(amount, 0))
    if a <= 0 or attackerId == nil then return end
    table.insert(ledger.hits, { id = attackerId, amount = a, t = n })
    prune(ledger, n)
end

-- Damage multiplier for the next hit: CrowdDamageX if enough distinct attackers hit lately, else 1.
function TeamUp.crowdMultiplier(ledger: any, now: any): number
    local n = num(now, 0)
    local seen, count = {}, 0
    for _, h in ledger.hits do
        if n - h.t <= T.CrowdWindowSeconds and not seen[h.id] then
            seen[h.id] = true
            count += 1
        end
    end
    return if count >= T.CrowdMinAttackers then T.CrowdDamageX else 1
end

-- Attackers who dealt >= AssistMinFraction of victimMaxHp inside the window: list of {id, damage}.
function TeamUp.assisters(ledger: any, victimMaxHp: any, now: any): { any }
    local n = num(now, 0)
    local totals, order = {}, {}
    for _, h in ledger.hits do
        if n - h.t <= T.AssistWindowSeconds then
            if totals[h.id] == nil then
                totals[h.id] = 0
                table.insert(order, h.id)
            end
            totals[h.id] += h.amount
        end
    end
    local out = {}
    local need = math.max(num(victimMaxHp, 0), 0) * T.AssistMinFraction
    for _, id in order do
        if totals[id] >= need and totals[id] > 0 then table.insert(out, { id = id, damage = totals[id] }) end
    end
    return out
end

-- Whole-number pool: floor(BonusCapFraction * victimScore) at most; `wanted` (optional) can only lower it.
function TeamUp.bonusPool(victimScore: any, wanted: any): number
    local cap = math.floor(math.max(0, num(victimScore, 0)) * T.BonusCapFraction)
    if wanted == nil then return cap end
    return math.min(cap, math.max(0, math.floor(num(wanted, 0))))
end

-- Largest-remainder split of an integer pool by damage share: the parts sum EXACTLY to the pool
-- (or are all 0 when there is no pool or no assisters). Returns {[id] = amount}.
function TeamUp.split(pool: any, assisters: { any }): any
    local p = math.max(0, math.floor(num(pool, 0)))
    local out = {}
    local total = 0
    for _, a in assisters do total += a.damage end
    if p == 0 or total <= 0 then
        for _, a in assisters do out[a.id] = 0 end
        return out
    end
    local rems, given = {}, 0
    for i, a in assisters do
        local exact = p * a.damage / total
        local base = math.floor(exact)
        out[a.id] = base
        given += base
        table.insert(rems, { i = i, id = a.id, r = exact - base })
    end
    table.sort(rems, function(x, y)
        if x.r ~= y.r then return x.r > y.r end
        return x.i < y.i
    end)
    local left = p - given
    for k = 1, left do
        local e = rems[((k - 1) % #rems) + 1]
        out[e.id] += 1
    end
    return out
end

-- Repeat-pair limiter: same attacker/victim inside PairWindowSeconds pays 1.0, 0.5, then 0.
function TeamUp.newLimiter(): any
    return { pairs = {} }
end

-- Records one bonus attempt and returns its factor.
function TeamUp.pairFactor(limiter: any, attackerId: any, victimId: any, now: any): number
    local n = num(now, 0)
    local key = tostring(attackerId) .. ">" .. tostring(victimId)
    local list = limiter.pairs[key] or {}
    local fresh = {}
    for _, t in list do
        if n - t <= T.PairWindowSeconds then table.insert(fresh, t) end
    end
    local factor = T.PairFactors[#fresh + 1] or 0
    table.insert(fresh, n)
    limiter.pairs[key] = fresh
    return factor
end

-- Apply per-assister factors (floor), so the total never exceeds the pool.
function TeamUp.applyFactors(parts: any, factors: any): any
    local out = {}
    for id, amount in parts do
        out[id] = math.floor(amount * math.clamp(num(factors[id], 1), 0, 1))
    end
    return out
end

return table.freeze(TeamUp)
