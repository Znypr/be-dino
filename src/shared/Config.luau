--!strict
-- Prototype tuning only. Persistent economy values remain private-test values.
return table.freeze({
    Build = "persistence-lease-007",
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
    DuplicateSettlementProbe = true,
    PersistenceLeaseSelfTest = true,
})
