--!strict
-- BD-239 / docs/101 s2-3: class table, size scale, max HP, per-hit damage, armor. Pure; PROVISIONAL numbers.
-- Nothing requires this module yet. Every function returns a finite number (junk input falls back safely).
local Cfg = require(script.Parent.CombatConfig)
local Stats = {}

local function num(v: any, fallback: number): number
    if typeof(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return fallback end
    return v
end

function Stats.classOf(name: any): any
    if typeof(name) == "string" and (Cfg.Classes :: any)[name] then return (Cfg.Classes :: any)[name] end
    return (Cfg.Classes :: any)[Cfg.DefaultClass]
end

-- s = clamp((1 + score/100)^0.25, 1, 4)
function Stats.scale(score: any): number
    local sc = math.max(0, num(score, 0))
    local s = (1 + sc / Cfg.ScaleDivisor) ^ Cfg.ScaleExponent
    return math.clamp(s, Cfg.MinScale, Cfg.MaxScale)
end

local function clampS(s: any): number
    return math.clamp(num(s, 1), Cfg.MinScale, Cfg.MaxScale)
end

-- hpX is optional (BD-1025): a multiplier for wild predators (Cfg.WildHpX). Players pass nothing and keep the full HP.
function Stats.maxHp(className: any, s: any, hpX: any): number
    local x = math.clamp(num(hpX, 1), 0.05, 4)
    return Cfg.BaseHp * Stats.classOf(className).hpX * clampS(s) ^ Cfg.HpSizeExponent * x
end

-- Raw hit before armor and damper. attackTier is an extension hook (0 for now).
function Stats.damage(className: any, s: any, attackTier: any): number
    local tier = math.max(0, num(attackTier, 0))
    return Cfg.BaseDamage * Stats.classOf(className).damageDealtX * clampS(s) ^ Cfg.DamageSizeExponent
        * (1 + Cfg.AttackTierBonus * tier)
end

-- Armor: every hit counts at least MinHit.
function Stats.armor(rawDamage: any, targetClass: any): number
    return math.max(num(rawDamage, 0) * Stats.classOf(targetClass).damageTakenX, Cfg.MinHit)
end

-- Final damage for one hit. extraX is for multipliers like the crowd cap or leap (>=0).
function Stats.hit(attackerClass: any, attackerS: any, targetClass: any, targetS: any, attackTier: any, extraX: any): number
    local a, t = clampS(attackerS), clampS(targetS)
    local raw = Stats.damage(attackerClass, a, attackTier)
    if a < t * Cfg.SizeDamperRatio then raw *= Cfg.SizeDamperX end
    raw *= math.max(0, num(extraX, 1))
    return Stats.armor(raw, targetClass)
end

-- BD-1025: size unit z = 1 + score / 50, clamped 1..16 (score = GrowthScore; z = the drawn scale squared, cap scale 4).
function Stats.sizeUnits(score: any): number
    return math.clamp(1 + math.max(0, num(score, 0)) / Cfg.SizeUnitDivisor, 1, Cfg.SizeUnitMax)
end

-- R = attacker z / target z (above 1 = the attacker is bigger).
function Stats.sizeRatio(attackerScore: any, targetScore: any): number
    return Stats.sizeUnits(attackerScore) / Stats.sizeUnits(targetScore)
end

-- Bites a BIGGER attacker needs, from the bites an even fight would take (evenBites >= 1) and the ratio R >= 1. Smooth, falling, 1 at OneShotRatio.
function Stats.bigBites(evenBites: any, ratio: any): number
    local n = math.max(1, num(evenBites, 1))
    local x = math.clamp(math.log(math.max(1, num(ratio, 1))) / math.log(Cfg.OneShotRatio), 0, 1)
    return 1 + (n - 1) * (1 - x ^ Cfg.BigHitCurvePower)
end

-- Multiplier on a SMALLER attacker's hit (R = bigger / smaller >= 1): 1 at R = 1, SmallHitFloorX at R >= OneShotRatio, smooth, always > 0.
function Stats.smallHitX(ratio: any): number
    local y = math.clamp(math.log(math.max(1, num(ratio, 1))) / math.log(Cfg.OneShotRatio), 0, 1)
    return Cfg.SmallHitFloorX ^ (y ^ Cfg.SmallHitPower)
end

-- Damage of one bite including the size-difference rule. Scores are GrowthScore. opts = {wildAttacker = bool, targetHpX = number}.
-- A wild predator keeps the plain hit (it must never one-shot a new player: its own rules limit it to two bites per chase).
-- Equal sizes give exactly Stats.hit. A bigger attacker: HP / bigBites (a smooth fall to one bite). A smaller attacker: hit x smallHitX, at least MinHit.
function Stats.hitScored(attackerClass: any, attackerScore: any, targetClass: any, targetScore: any, attackTier: any, extraX: any, opts: any): number
    local a, t = Stats.scale(attackerScore), Stats.scale(targetScore)
    local base = Stats.hit(attackerClass, a, targetClass, t, attackTier, extraX)
    local ratio = Stats.sizeRatio(attackerScore, targetScore)
    if ratio > 1 then
        if typeof(opts) == "table" and opts.wildAttacker == true then return base end
        local hpX = if typeof(opts) == "table" then opts.targetHpX else nil
        local hp = Stats.maxHp(targetClass, t, hpX)
        local even = hp / base
        if even <= 1 then return base end
        return math.max(base, hp / Stats.bigBites(even, ratio) * (1 + 1e-9))
    elseif ratio < 1 then
        return math.max(base * Stats.smallHitX(1 / ratio), Cfg.MinHit)
    end
    return base
end

-- Keep the HP ratio when size changes (eating never fully heals and never kills). Returns the new hp.
function Stats.rescaleHp(hp: any, oldMax: any, newMax: any): number
    local om, nm = math.max(num(oldMax, 1), 1e-9), math.max(num(newMax, 1), 1e-9)
    return math.clamp(num(hp, 0) / om, 0, 1) * nm
end

return table.freeze(Stats)
