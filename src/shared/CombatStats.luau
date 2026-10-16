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

function Stats.maxHp(className: any, s: any): number
    return Cfg.BaseHp * Stats.classOf(className).hpX * clampS(s) ^ Cfg.HpSizeExponent
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

-- Keep the HP ratio when size changes (eating never fully heals and never kills). Returns the new hp.
function Stats.rescaleHp(hp: any, oldMax: any, newMax: any): number
    local om, nm = math.max(num(oldMax, 1), 1e-9), math.max(num(newMax, 1), 1e-9)
    return math.clamp(num(hp, 0) / om, 0, 1) * nm
end

return table.freeze(Stats)
