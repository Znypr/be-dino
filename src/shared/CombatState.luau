--!strict
-- BD-240 / docs/101 s6: HP and the idempotent Alive -> Defeated -> Settled machine. Pure (mutates the table it is given).
-- Defeat and settlement each happen exactly once; later hits are ignored. HP never leaves 0..maxHp.
local Cfg = require(script.Parent.CombatConfig)
local State = {}

local function num(v: any, fallback: number): number
    if typeof(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return fallback end
    return v
end

function State.new(maxHp: any): any
    local m = math.max(num(maxHp, Cfg.BaseHp), 1)
    return { maxHp = m, hp = m, phase = "Alive", lastCombatAt = -1e9 }
end

-- Returns applied damage, and true only on the one hit that defeats.
function State.damage(st: any, amount: any, now: any): (number, boolean)
    if st.phase ~= "Alive" then return 0, false end
    local a = math.max(0, num(amount, 0))
    local applied = math.min(a, st.hp)
    st.hp -= applied
    st.lastCombatAt = num(now, st.lastCombatAt)
    if st.hp <= 0 then
        st.hp = 0
        st.phase = "Defeated"
        return applied, true
    end
    return applied, false
end

function State.heal(st: any, amount: any): number
    if st.phase ~= "Alive" then return 0 end
    local before = st.hp
    st.hp = math.min(st.maxHp, st.hp + math.max(0, num(amount, 0)))
    return st.hp - before
end

function State.healFood(st: any): number
    return State.heal(st, st.maxHp * Cfg.FoodHealFraction)
end

-- Regen after RegenDelaySeconds without hitting or being hit; dt in seconds.
function State.regen(st: any, now: any, dt: any): number
    if st.phase ~= "Alive" then return 0 end
    if num(now, 0) - st.lastCombatAt < Cfg.RegenDelaySeconds then return 0 end
    return State.heal(st, st.maxHp * Cfg.RegenFractionPerSecond * math.max(0, num(dt, 0)))
end

-- Called when this dino hits something, so regen waits.
function State.touch(st: any, now: any)
    st.lastCombatAt = num(now, st.lastCombatAt)
end

-- Growth keeps the HP ratio and never kills.
function State.setMaxHp(st: any, newMax: any)
    local nm = math.max(num(newMax, st.maxHp), 1)
    if st.phase == "Alive" then
        st.hp = math.clamp(st.hp / st.maxHp, 0, 1) * nm
        if st.hp <= 0 then st.hp = math.min(1, nm) end
    end
    st.maxHp = nm
end

-- Defeated -> Settled, true exactly once.
function State.settle(st: any): boolean
    if st.phase ~= "Defeated" then return false end
    st.phase = "Settled"
    return true
end

return table.freeze(State)
