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

    -- BD-246 / docs/101 s2, s12 / docs/115: class per species (one source; the low-poly registry class must agree, verify_classes.py).
    -- Owner: Armored = Ankylosaurus, Sauropelta, Styracosaurus; Kentrosaurus is Ground; Elasmosaurus counts as a normal Ground dino.
    -- Entries without a model yet (liopleurodon, sauropelta, styracosaurus, kentrosaurus, the secret birds) are planned roster data.
    SpeciesClasses = {
        compy = "Ground", raptor = "Ground", triceratops = "Ground", tyrannosaurus = "Ground", stegosaurus = "Ground",
        baryonyx = "Ground", brachiosaurus = "Ground", gallimimus = "Ground", pachycephalosaurus = "Ground",
        parasaurolophus = "Ground", spinosaurus = "Ground", therizinosaurus = "Ground", elasmosaurus = "Ground",
        kentrosaurus = "Ground",
        archaeopteryx = "Fly", dimorphodon = "Fly", microraptor = "Fly", pteranodon = "Fly", quetzalcoatlus = "Fly",
        ichthyosaurus = "Water", mosasaurus = "Water", plesiosaurus = "Water", liopleurodon = "Water",
        ankylosaurus = "Armored", sauropelta = "Armored", styracosaurus = "Armored",
        -- Secret birds and the fox (BD-604, docs/115 SS5): Penguin is Water (slow, sturdy, dash), Budgiesaurus Fly, the rest Ground. Shared/SecretSpeciesConfig must agree (verify_secret_species).
        chickosaurus = "Ground", pigeon = "Ground", duck = "Ground", dodo = "Ground", penguin = "Water", budgiesaurus = "Fly", foxosaurus = "Ground",
        cockatoosaurus = "Fly", eaglesaurus = "Fly",
    },
    -- Silly birds are secret finds: never listed in a roster/index until found (owner, docs/115).
    SecretSpecies = { "chickosaurus", "pigeon", "duck", "dodo", "penguin", "budgiesaurus", "foxosaurus", "cockatoosaurus", "eaglesaurus" },

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

    -- BD-1025 / docs/183 (owner 2026-10-18): the SIZE DIFFERENCE decides how long a fight takes. Size unit z = 1 + growth/50 (the square of the
    -- drawn scale s = sqrt(1 + growth/50), cap s = 4, so z = 1..16). R = bigger z / smaller z. Similar sizes = a long fight (about 9 bites);
    -- a big R = very few bites; R >= OneShotRatio = ONE bite. A small dino hitting a big one deals less and less (never 0). PROVISIONAL.
    SizeUnitDivisor = 50,
    SizeUnitMax = 16, -- growth cap 750 -> z = 16
    OneShotRatio = 16, -- R at (and above) which the bigger dino wins in one bite (fresh dino against a capped one)
    BigCurveBites = 9, -- the curve starts at this many bites (an even fight against a wild predator); a longer even fight eases into it
    BigCurveBlendX = 0.3, -- ... over this part of x (x = ln R / ln OneShotRatio)
    BigHitCurvePower = 1.37, -- bites = 1 + (even bites - 1) x (1 - x^power), x = ln R / ln OneShotRatio: gentle first, then steeper
    SmallHitFloorX = 0.1, -- a small dino's bite is multiplied by this at R = OneShotRatio (smoothly from 1); never below MinHit
    SmallHitPower = 1.5,
    -- Wild predators (NpcPredatorRules) do not start a fight with a player more than this many times smaller (no reward, hard to see)
    -- or bigger (hopeless). Players may still choose to. Wild dinos reach R = 6 at most against a fresh player, so 6 would never trigger.
    WildMaxSizeRatio = 4,

    RegenDelaySeconds = 6,
    RegenFractionPerSecond = 0.04,
    FoodHealFraction = 0.05,

    -- BD-243 / docs/101 s4, s7, s13 (server rules in CombatRules, glue in CombatService). ALL PROVISIONAL.
    BiteCooldownSeconds = 0.6, -- BD-1025 (owner 2026-10-18: fights too slow): was 0.9; the rate limit below (2 per second) still allows it
    WildHpX = 0.4, -- BD-1025: wild predators (NpcPredatorRules) have this share of the normal HP for their size; players are unchanged
    BiteRangeBase = 2.5, -- reach = BiteRangeBase + BiteRangePerScale * s studs, measured from the attacker's BODY SURFACE (BD-311)
    BiteRangePerScale = 1.0,
    BiteRangeSlack = 1.5, -- extra studs for latency: the client aims, the server measures a moment later
    BodyRadiusPerScale = 1.2, -- BD-311: fallback body radius (studs) per combat scale when the server has no measured size
    BodyRadiusMax = 14, -- BD-311: any radius is clamped to this (a measured bounding box can never open an infinite range)
    -- BD-245 PROPOSAL (docs/115 HZ1): the shape of a hit zone, Shared/HitSize.zone. "circle" = today's rule (HS1, max(width, length) / 2 x growth,
    -- capped by BodyRadiusMax); "capsule" = the body footprint (half width round a spine as long as the body). Default "circle": nothing reads
    -- "capsule" yet (CombatRules still calls HitSize.radius). The owner decides combat feel; do not flip this without a Studio hit test.
    HitZoneRule = "circle",
    HitCapsuleRadiusMax = 20, -- capsule safety caps, above every real body at growth 4.8 (widest 19.7; longest spine 27.5, Mosasaurus after the C-39 water-by-bulk resize)
    HitCapsuleSpanMax = 32,
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
