--!strict
-- BD-239..241 / docs/101: combat tunables. Every number is PROVISIONAL, not final balance.
-- The runtime flag is Config.CombatEnabled (read by CombatService, PredationService and CombatHud). `Enabled` here is a
-- second guard for the pure modules' offline tests and stays false too.
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

    -- BD-243 / docs/101 s4, s7, s13 (server rules in CombatRules, glue in CombatService). ALL PROVISIONAL.
    BiteCooldownSeconds = 0.9,
    BiteRangeBase = 2.5, -- reach = BiteRangeBase + BiteRangePerScale * s studs, measured from the attacker's BODY SURFACE (BD-311)
    BiteRangePerScale = 1.0,
    BiteRangeSlack = 1.5, -- extra studs for latency: the client aims, the server measures a moment later
    BodyRadiusPerScale = 1.2, -- BD-311: fallback body radius (studs) per combat scale when the server has no measured size
    BodyRadiusMax = 14, -- BD-311: any radius is clamped to this (a measured bounding box can never open an infinite range)
    BiteConeDegrees = 70, -- full cone angle in front of the attacker
    BiteVerticalLimit = 7, -- same as PredationVerticalLimit
    BiteRequestsPerSecond = 2, -- rate limit per player (sliding 1 s window)
    LeapBiteX = 1.6, -- a bite landed inside the leap window hits this much harder
    KnockbackStuds = 4, -- soft push away from the attacker; halved for Armored, scaled down for big targets
    KnockbackBigScaleDivisor = 2, -- push / max(1, targetS / divisor)
    HpByteMax = 255, -- replicated HP is one byte (0..255 of max)
    HpSendHz = 5,
    TickHz = 10,
    FriendShieldDefeats = 3, -- defeated this often ...
    FriendShieldWindowSeconds = 180, -- ... inside this window ...
    FriendShieldSeconds = 30, -- ... gives the next run this much extra spawn protection

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
