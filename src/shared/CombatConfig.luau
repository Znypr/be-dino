--!strict
-- BD-239..241 / docs/101: combat tunables. Every number is PROVISIONAL, not final balance.
-- Enabled is a flag that NOTHING reads yet (no server/client wiring exists). Keep it false.
local CombatConfig = {
    Enabled = false,

    Classes = {
        Ground = { hpX = 1.00, speedX = 1.00, damageTakenX = 1.00, damageDealtX = 1.00 },
        Fly = { hpX = 0.75, speedX = 1.20, damageTakenX = 1.00, damageDealtX = 1.32 },
        Water = { hpX = 1.25, speedX = 0.85, damageTakenX = 1.00, damageDealtX = 0.80 },
        Armored = { hpX = 1.10, speedX = 0.80, damageTakenX = 0.80, damageDealtX = 0.73 },
    },
    DefaultClass = "Ground",

    BaseHp = 100,
    HpSizeExponent = 1.3,
    BaseDamage = 6,
    DamageSizeExponent = 0.2,
    AttackTierBonus = 0.05,
    MinHit = 1, -- armor never reduces a hit below this
    MinScale = 1,
    MaxScale = 4,
    ScaleDivisor = 100,
    ScaleExponent = 0.25,
    SizeDamperRatio = 0.5, -- attacker s below this fraction of target s ...
    SizeDamperX = 0.9, -- ... deals this multiple

    RegenDelaySeconds = 6,
    RegenFractionPerSecond = 0.04,
    FoodHealFraction = 0.05,

    TeamUp = {
        AssistWindowSeconds = 15,
        AssistMinFraction = 0.10, -- of the victim's max HP
        BonusCapFraction = 0.25, -- of the victim's score
        PairWindowSeconds = 180,
        PairFactors = { 1.0, 0.5 }, -- 1st, 2nd; anything later is 0
        CrowdWindowSeconds = 2,
        CrowdMinAttackers = 5,
        CrowdDamageX = 0.9,
    },
}

return table.freeze(CombatConfig)
