--!strict
-- Prototype tuning only. Persistent economy values remain private-test values.
return table.freeze({
    Build = "redesign-019",
    WalkSpeed = 22,
    JumpPower = 50,
    MaxSlopeAngle = 46,
    TerrainResolution = 4,
    TerrainTop = 120,
    ArenaHalfWidth = 260,
    CameraMinZoom = 12,
    CameraMaxZoom = 110,

    FoodPoints = 1,
    FoodRespawnSeconds = 8,
    FoodPickupRadius = 2.25,
    FoodTickSeconds = 0.15,
    FoodSectorCount = 16,
    FoodClusterItems = 6,
    FoodClusterRadius = 7,
    FoodSeed = 1404,
    StudioLocalProfilesEnabled = true, -- unpublished Studio only; never a live fallback
    StudioTestWalletEnabled = true, -- only unpublished, nonpersistent local profiles
    StudioTestCrystals = 1000000,
    FoodCatchRate = 15 / 500, -- raw food points; growth boosts do not multiply catches
    ProfileLoadWarningSeconds = 20,

    SpawnProtectionSeconds = 5,
    PredationScoreMultiplier = 1.10,
    PredationTickSeconds = 0.1,
    PredationBaseRadius = 5.5,
    PredationMaxRadius = 9,
    PredationVerticalLimit = 7,
    PredationGrowthPoints = 25,
    RepeatVictimCatchCooldownSeconds = 60,

    ExitChannelSeconds = 3,
    ExitMoveCancelDistance = 2,
    ExitRequestCooldownSeconds = 0.75,
    RespawnDelaySeconds = 2,

    MaxCatchScore = 5000,
    RarityQ = 0.25,
    AlphaTierThresholds = {1, 25, 100},
    AlphaSpeciesByTier = {"compy", "triceratops", "tyrannosaurus"},
    SpeciesOrder = {"compy", "triceratops", "tyrannosaurus", "raptor", "stegosaurus", "ankylosaurus"},
    SpeciesDisplayNames = {
        compy = "Compy",
        triceratops = "Triceratops",
        tyrannosaurus = "T-Rex",
        raptor = "Raptor",
        stegosaurus = "Stegosaurus",
        ankylosaurus = "Ankylosaurus",
    },
    SpeciesRarities = {compy = 1, raptor = 1, triceratops = 2, stegosaurus = 2, tyrannosaurus = 3, ankylosaurus = 3},
    ChestThresholds = {
        {score = 10, count = 1},
        {score = 100, count = 2},
        {score = 500, count = 3},
    },

    ProfileDataStoreName = "BeDino_PrivateTest_v1",
    ProfileSchemaVersion = 1,
    ProfileLeaseSeconds = 90,
    ProfileRenewSeconds = 30,
    ProfileMaxAttempts = 3,
    ProfileMaxRecentOperations = 50,

    EquipRequestCooldownSeconds = 0.5,
    CollectionTestGrantEnabled = false,
    CollectionTestGrantSpeciesId = "triceratops",
    CollectionTestGrantVersion = 1,

    ChestTimerSeconds = 0, -- Reveals, rather than offline incubation, pace new eggs.
    HatchRevealSeconds = 5,
    EggRarityBoostPerExtraEgg = 0.25,
    EggRarityBoostMaxEggs = 15,
    BigChance = 0.1,
    ShinyChance = 0.05,
    BigScaleMultiplier = 1.2,
    IrregularWeather = {volcano = true, aurora = true, quake = true, bloodmoon = true},
    DeveloperProducts = { [3717200374] = 500, [3717200467] = 1500, [3717200523] = 4000, [3717200920] = 10000, [3717200940] = 25000, [3717200979] = 90000 },
    CrystalPacksEnabled = false, -- Enable only after paid-random disclosure/release review.
    PaidRandomItemsEnabled = false, -- Release gate: complete combined-outcome disclosure/policy acceptance first.
    ChestQueueCapacity = 5,
    ChestOverflowCapacity = 10,
    ChestClaimRequestCooldownSeconds = 0.35,
    ChestTestGrantEnabled = false,
    ChestTestGrantCount = 7,
    ChestTestGrantVersion = 1,
    ChestSpeciesWeights = {
        {speciesId = "compy", weight = 40},
        {speciesId = "raptor", weight = 30},
        {speciesId = "triceratops", weight = 15},
        {speciesId = "stegosaurus", weight = 10},
        {speciesId = "tyrannosaurus", weight = 3},
        {speciesId = "ankylosaurus", weight = 2},
    },
    ChestQuantityWeights = {
        {count = 1, weight = 70},
        {count = 2, weight = 25},
        {count = 3, weight = 5},
    },

    GoldMutationCost = 50,
    DiamondMutationCost = 50, -- provisional balance: 50 Gold -> 1 Diamond
    MutationRequestCooldownSeconds = 0.4,
    MutationTestSetupEnabled = false,
    MutationTestSpeciesId = "compy",

    MovementGuardTickSeconds = 0.1,
    MovementGuardSpeedTolerance = 3,
    MovementGuardBurstStuds = 4,
    MovementGuardRejectCooldownSeconds = 0.75,
    SecurityTestHarnessEnabled = false,
    ArtTestHarnessEnabled = false,
    ArtPreviewRequestCooldownSeconds = 0.25,

    -- Build 006/007 probes passed and are disabled again.
    DuplicateSettlementProbe = false,
})
