--!strict
-- Prototype tuning only. Persistent economy values remain private-test values.
return table.freeze({
    Build = "security-regression-012",
    WalkSpeed = 18,
    ArenaHalfWidth = 90,
    CameraMinZoom = 12,
    CameraMaxZoom = 80,

    FoodPoints = 10,
    FoodRespawnSeconds = 8,
    FoodPickupRadius = 4,
    FoodTickSeconds = 0.1,

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
    SpeciesOrder = {"compy", "triceratops", "tyrannosaurus"},
    SpeciesDisplayNames = {
        compy = "Compy",
        triceratops = "Triceratops",
        tyrannosaurus = "T-Rex",
    },
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

    ChestTimerSeconds = 60,
    ChestQueueCapacity = 5,
    ChestOverflowCapacity = 10,
    ChestClaimRequestCooldownSeconds = 0.35,
    ChestTestGrantEnabled = false,
    ChestTestGrantCount = 7,
    ChestTestGrantVersion = 1,
    ChestSpeciesWeights = {
        {speciesId = "compy", weight = 70},
        {speciesId = "triceratops", weight = 25},
        {speciesId = "tyrannosaurus", weight = 5},
    },
    ChestQuantityWeights = {
        {count = 1, weight = 70},
        {count = 2, weight = 25},
        {count = 3, weight = 5},
    },

    GoldMutationCost = 50,
    MutationRequestCooldownSeconds = 0.4,
    MutationTestSetupEnabled = false,
    MutationTestSpeciesId = "compy",

    MovementGuardTickSeconds = 0.1,
    MovementGuardSpeedTolerance = 3,
    MovementGuardBurstStuds = 4,
    MovementGuardRejectCooldownSeconds = 0.75,
    SecurityTestHarnessEnabled = true,

    -- Build 006/007 probes passed and are disabled again.
    DuplicateSettlementProbe = false,
})
