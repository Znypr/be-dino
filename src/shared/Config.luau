--!strict
-- Prototype tuning only. Persistent economy values are defined separately.
return table.freeze({
    Build = "pvp-run-005",
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

    ExitChannelSeconds = 3,
    ExitMoveCancelDistance = 2,
    ExitRequestCooldownSeconds = 0.75,
})
