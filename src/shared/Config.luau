--!strict
-- Prototype tuning only. Persistent economy values remain private-test values.
return table.freeze({
    Build = "redesign-018",
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
    SecurityTestHarnessEnabled = false,
    ArtTestHarnessEnabled = false,
    ArtPreviewRequestCooldownSeconds = 0.25,

    -- Build 006/007 probes passed and are disabled again.
    DuplicateSettlementProbe = false,
})
