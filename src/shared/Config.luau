--!strict
-- Prototype tuning only. Persistent economy values remain private-test values.
return table.freeze({
    Build = "redesign-020",
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
    SpeciesOrder = {"compy", "triceratops", "tyrannosaurus", "raptor", "stegosaurus", "ankylosaurus", "archaeopteryx", "baryonyx", "brachiosaurus", "dimorphodon", "elasmosaurus", "gallimimus", "ichthyosaurus", "microraptor", "mosasaurus", "pachycephalosaurus", "parasaurolophus", "plesiosaurus", "pteranodon", "quetzalcoatlus", "spinosaurus", "therizinosaurus"},
    SpeciesDisplayNames = {
        compy = "Compy",
        triceratops = "Triceratops",
        tyrannosaurus = "T-Rex",
        raptor = "Raptor",
        stegosaurus = "Stegosaurus",
        ankylosaurus = "Ankylosaurus",
        archaeopteryx = "Archaeopteryx",
        baryonyx = "Baryonyx",
        brachiosaurus = "Brachiosaurus",
        dimorphodon = "Dimorphodon",
        elasmosaurus = "Elasmosaurus",
        gallimimus = "Gallimimus",
        ichthyosaurus = "Ichthyosaurus",
        microraptor = "Microraptor",
        mosasaurus = "Mosasaurus",
        pachycephalosaurus = "Pachycephalosaurus",
        parasaurolophus = "Parasaurolophus",
        plesiosaurus = "Plesiosaurus",
        pteranodon = "Pteranodon",
        quetzalcoatlus = "Quetzalcoatlus",
        spinosaurus = "Spinosaurus",
        therizinosaurus = "Therizinosaurus",
    },
    SpeciesRarities = {compy = 1, raptor = 1, triceratops = 2, stegosaurus = 2, tyrannosaurus = 3, ankylosaurus = 3, archaeopteryx = 1, baryonyx = 2, brachiosaurus = 2, dimorphodon = 1, elasmosaurus = 3, gallimimus = 1, ichthyosaurus = 2, microraptor = 1, mosasaurus = 3, pachycephalosaurus = 2, parasaurolophus = 2, plesiosaurus = 2, pteranodon = 2, quetzalcoatlus = 3, spinosaurus = 3, therizinosaurus = 3},
    -- HISTORICAL (removed by BD-044): ChestThresholds 10/100/500 catches -> 1/2/3 eggs and
    -- AlphaTierThresholds direct N(c)=c copies. See docs/15-economy-simulation.md.

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
    -- BD-044 reward loop (owner decision 2026-10-13): every earned run catch banks
    -- exactly ONE run egg; no direct N(c)=c copies and no 10/100/500 threshold eggs.
    -- Run eggs beyond the five-slot reveal queue wait in a server-side ordered bank.
    RunRewardConfigVersion = 2,
    RunEggMaxPerRun = 300, -- PROVISIONAL: catches stop counting at 300 eggs per run (storage bound)
    RunEggBankCapacity = 600, -- PROVISIONAL: banked run eggs behind the queue; runs start only with room for a full run
    SettledRunLedgerSize = 200, -- PROVISIONAL: settled run IDs kept for exactly-once settlement beyond recentOperations
    -- Separate bonus egg nests (never the ordinary egg queue). Excess nests wait as
    -- pending/capacity-blocked and are never silently granted or discarded.
    NestSlotCapacity = 5,
    NestPendingCapacity = 30, -- PROVISIONAL
    NestFirstAtEggs = 15, -- PROVISIONAL: 15 run eggs (500 food) earn the first nest
    NestEggsPerExtraNest = 27, -- PROVISIONAL: +1 nest per 27 further eggs (150 eggs -> 6 nests)
    NestMaxPerRun = 11, -- PROVISIONAL: equals the nest count at RunEggMaxPerRun
    NestEggCount = 3, -- PROVISIONAL: each nest contains three precommitted bonus eggs
    NestIncubationSeconds = 300, -- PROVISIONAL: a slotted nest opens five minutes after it takes a slot
    NestRarityBoostEggs = 15, -- PROVISIONAL: nest eggs use the maximum run-batch species boost
    NestClaimRequestCooldownSeconds = 0.5,
    ChestClaimRequestCooldownSeconds = 0.35,
    ChestTestGrantEnabled = false,
    ChestTestGrantCount = 7,
    ChestTestGrantVersion = 1,
    ChestSpeciesWeights = {
        {speciesId = "compy", weight = 25},
        {speciesId = "raptor", weight = 20},
        {speciesId = "gallimimus", weight = 8},
        {speciesId = "microraptor", weight = 7},
        {speciesId = "archaeopteryx", weight = 5},
        {speciesId = "dimorphodon", weight = 5},
        {speciesId = "triceratops", weight = 10},
        {speciesId = "stegosaurus", weight = 5},
        {speciesId = "brachiosaurus", weight = 3},
        {speciesId = "parasaurolophus", weight = 2},
        {speciesId = "pachycephalosaurus", weight = 1},
        {speciesId = "baryonyx", weight = 1},
        {speciesId = "pteranodon", weight = 1},
        {speciesId = "ichthyosaurus", weight = 1},
        {speciesId = "plesiosaurus", weight = 1},
        {speciesId = "tyrannosaurus", weight = 1},
        {speciesId = "ankylosaurus", weight = 1},
        {speciesId = "therizinosaurus", weight = 0.5},
        {speciesId = "spinosaurus", weight = 0.5},
        {speciesId = "quetzalcoatlus", weight = 0.5},
        {speciesId = "mosasaurus", weight = 0.75},
        {speciesId = "elasmosaurus", weight = 0.75},
    },
    -- Owner decision 2026-10-13: exactly one dinosaur per successfully hatched egg.
    -- Historical Build 020 split was 1/2/3 copies at 70/25/5; already-saved eggs keep
    -- their committed count when claimed.
    ChestQuantityWeights = {
        {count = 1, weight = 1},
    },

    GoldMutationCost = 50,
    DiamondMutationCost = 50, -- provisional balance: 50 Gold -> 1 Diamond
    MutationRequestCooldownSeconds = 0.4,
    MutationTestSetupEnabled = false,
    -- BD-057/BD-064 fusion flag. Fusion runs in unpublished memory-only Studio profiles,
    -- or in persistent profiles when IdentityPersistentEnabled is also true, using the
    -- PROVISIONAL FusionOdds roller. Keep false in committed builds.
    IdentityFusionPreviewEnabled = false,
    -- Milestone 1 private playtest (fresh, empty DataStore): identity sidecar, hatch
    -- credit and reconciliation for persistent profiles. Keep false in committed builds.
    IdentityPersistentEnabled = false,
    -- PROVISIONAL byte budgets (IdentityFusion.encodedSize of the WHOLE profile) under
    -- the 4 MiB (4,194,304 B) DataStore value limit. A fusion that would exceed the
    -- fusion budget is rejected; any persistent write above the hard limit first drops
    -- identity growth (identity suspended) and otherwise aborts.
    IdentityFusionProfileBudgetBytes = 3400000,
    IdentityProfileHardLimitBytes = 3800000,
    -- PROVISIONAL FusionAction remote rate limit: requests per player per window.
    FusionRequestsPerWindow = 20,
    FusionRateWindowSeconds = 10,
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
