--!strict
-- Prototype tuning only. Persistent economy values remain private-test values.
return table.freeze({
    Build = "redesign-020",
    WalkSpeed = 22,
    -- Movement feel (PROVISIONAL): default gravity 196.2 felt floaty. 250 + JumpPower 56 keeps a
    -- ~6.3 stud jump but cuts air time ~0.51s -> ~0.45s; leap vertical speed is retuned in ProgressionConfig.
    Gravity = 250,
    -- BD-212: jumps read as a forward bound: 50 -> ~5.0 stud apex, ~0.40 s air (was 56: ~6.3, ~0.45 s),
    -- and the client carries the run direction at JumpForwardCarry x speed while airborne.
    JumpPower = 50,
    JumpForwardCarry = 1.3, -- PROVISIONAL; MovementGuard allows WalkSpeed x MovementGuardSpeedTolerance (3)
    TurnRate = 16, -- PROVISIONAL rad/s facing steer (Humanoid default ~8 gave a 0.38 s 180 turn)
    CameraVerticalSmoothing = .18, -- BD-164: seconds; low-pass on the camera's vertical follow of the root (terrain rattle)
    CameraLiftSharpness = 7, -- PROVISIONAL: per-second exponential follow of growth camera lift
    MaxSlopeAngle = 46,
    -- BD-053 torso collider. Footprint grows with the dinosaur, but its underside is lifted so
    -- it clears any ground slope up to MaxSlopeAngle under every footprint corner. PROVISIONAL.
    DinoColliderWidth = 2.6,
    DinoColliderLength = 3.2,
    DinoColliderTopPerScale = 2.6, -- PROVISIONAL: collider top above floor per unit visual scale
    DinoColliderMinHeight = 1.2, -- PROVISIONAL
    DinoColliderMinClearance = 0.2,
    DinoColliderSlopeMargin = 0.35, -- PROVISIONAL: studs on top of the planar slope clearance
    MovementGuardMaxVerticalSpeed = 120,
    TerrainResolution = 4,
    TerrainTop = 120,
    ArenaHalfWidth = 416, -- world v2: 1.6x the 260 of the 520 map (IslandLayout.Scale)
    SanctuaryCenterZ = 521, -- hub centre: ArenaHalfWidth + 105 (it sits past the north boundary)
    FastTravelPerk = false, -- BD-391/405 (docs/115 D22): true = fast travel to shops is a Crystal Shop perk (crystals, no Robux); false = unchanged. Needs CaveHub.
    CaveHub = false, -- BD-280 (docs/104): true = big cave Sanctuary at CaveHubLayout.CenterZ; false = the current hub, unchanged
    CameraMinZoom = 12,
    CameraMaxZoom = 110,
    -- BD-054 touch HUD layout (shared/TouchLayout). PROVISIONAL until physical Android review.
    TouchMinTargetPx = 44, -- PROVISIONAL minimum touch target edge in canvas px
    TouchSafeMargin = 8, -- PROVISIONAL gap to safe-area edges, Roblox touch controls and each other
    TouchMinHudScale = 0.62, -- PROVISIONAL keeps HUD text >= ~12 px on 360 px tall phones

    FoodPoints = 1,
    FoodRespawnSeconds = 8,
    FoodPickupRadius = 2.25,
    FoodTickSeconds = 0.08, -- PROVISIONAL: was 0.15; shorter pickup latency
    FoodSectorCount = 20, -- world v2: 400 clusters of 8 over a 2.56x larger island (was 256)
    FoodClusterItems = 8, -- BD-387: was 6 (+33% food, owner 2026-10-16); 3,200 pickups, phone culling keeps the visible part budget (docs/107)
    FoodClusterRadius = 7,
    FoodSeed = 1404,
    FoodArtMode = "Legacy", -- "Kit": BD-050 Blender food variants (visual only; points unchanged) PROVISIONAL
    WorldArtMode = "Legacy", -- "BiomeKit": BD-049 Blender props + placement grammar PROVISIONAL
    WorldGeneratedMeshes = true, -- BD-206: Roblox-generated MeshParts for mapped kit props (WorldGeneratedMeshes.luau); a failed load keeps the kit model
    WorldArtSeed = 1404,
    WorldArtDensity = 1, -- the playtest profile sets 1.25 (tools/release_profiles.py, docs/68); 1 is the default density
    -- BD-168 client distance culling of decorative props/food (docs/89). PartBudget = max prop parts a client keeps parented;
    -- radius = studs kept (hysteresis = +15%). Collision proxies, crystals, hub and server food logic are never culled.
    CameraOcclusion = {Enabled = true}, -- BD-253: props between camera and dino fade (Shared/CameraOcclusion.luau); false = off
    WorldCulling = {
        Enabled = true,
        Hysteresis = 1.15,
        FoodRadiusFactor = 1.25,
        Phone = {radius = 190, budget = 1400},
        Tablet = {radius = 280, budget = 2400},
        Desktop = {radius = 440, budget = 5000},
    },
    FoodKitVisualCap = 12, -- PROVISIONAL max native egg/amber kit models (about 115 parts each); other pickups keep the light ball
    StudioLocalProfilesEnabled = true, -- unpublished Studio only; never a live fallback
    StudioTestWalletEnabled = true, -- only unpublished, nonpersistent local profiles
    StudioTestCrystals = 1000000,
    FoodCatchRate = 4 / 500, -- PROVISIONAL (owner 2026-10-15, BD-165: 500 food = 4 run eggs; 5,000 food -> 40; was 40/500 on 2026-10-13, 15/500 before); raw food points, growth boosts do not multiply catches
    ProfileLoadWarningSeconds = 20,

    SpawnProtectionSeconds = 5,
    PredationScoreMultiplier = 1.10,
    PredationTickSeconds = 0.1,
    PredationBaseRadius = 5.5,
    PredationMaxRadius = 9,
    PredationVerticalLimit = 7,
    GrowthPerFood = 0.1, -- owner 2026-10-16 (BD-386): 5x slower again (was 0.5 on 2026-10-15, 1.0 before); catches/eggs still use RAW food points, never growth
    PredationGrowthPoints = 2.5, -- BD-386: 5x slower with GrowthPerFood (was 12.5, 25)
    RepeatVictimCatchCooldownSeconds = 60,

    -- BD-052: Home is a confirmed, immediate return; the 3-second stay-still channel is removed.
    ExitRequestCooldownSeconds = 0.75,
    HomeThreatRadius = 30, -- PROVISIONAL: Home is refused while a dinosaur that can eat you is this close
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
    -- BD-044 five species rarity tiers (index = rank, higher is rarer). PROVISIONAL tier mapping by the
    -- lead (2026-10-14); see docs/82. Saved values written before this scale are migrated on load
    -- (ProfileRepository, profile.rarityScale) and the rarest leaderboard moved to a new "_v2" store.
    SpeciesRarityNames = {"Common", "Uncommon", "Rare", "Epic", "Legendary"},
    SpeciesRarityScale = 5,
    SpeciesRarities = {
        compy = 1, raptor = 1, gallimimus = 1, microraptor = 1, dimorphodon = 1,
        archaeopteryx = 2, stegosaurus = 2, parasaurolophus = 2, pachycephalosaurus = 2, pteranodon = 2,
        triceratops = 3, brachiosaurus = 3, baryonyx = 3, ichthyosaurus = 3, plesiosaurus = 3,
        ankylosaurus = 4, elasmosaurus = 4, therizinosaurus = 4, quetzalcoatlus = 4,
        tyrannosaurus = 5, spinosaurus = 5, mosasaurus = 5,
    },
    -- Pre-BD-044 three-tier scale (1 Common, 2 Rare, 3 Legendary), used only to migrate saved values.
    LegacySpeciesRarities = {compy = 1, raptor = 1, triceratops = 2, stegosaurus = 2, tyrannosaurus = 3, ankylosaurus = 3, archaeopteryx = 1, baryonyx = 2, brachiosaurus = 2, dimorphodon = 1, elasmosaurus = 3, gallimimus = 1, ichthyosaurus = 2, microraptor = 1, mosasaurus = 3, pachycephalosaurus = 2, parasaurolophus = 2, plesiosaurus = 2, pteranodon = 2, quetzalcoatlus = 3, spinosaurus = 3, therizinosaurus = 3},
    -- HISTORICAL (removed by BD-044): ChestThresholds 10/100/500 catches -> 1/2/3 eggs and
    -- AlphaTierThresholds direct N(c)=c copies. See docs/15-economy-simulation.md.

    ProfileDataStoreName = "BeDino_PrivateTest_v1",
    -- Release keys (BD-004/BD-020). `python tools/build.py --profile playtest` rewrites
    -- ReleaseProfile and ProfileDataStoreName in the generated place only; rules live in
    -- tools/release_profiles.py and are enforced by tools/verify_release.py.
    ReleaseProfile = "development",
    PlaytestUniverseId = 10769812255, -- BD-004: private experience "newbuild" (universe), recorded 2026-10-14
    PlaytestPlaceId = 111259822927673, -- BD-004: private experience "newbuild" (start place), recorded 2026-10-14
    PlaytestProfileDataStoreName = "BeDino_Playtest_M1_v1", -- rotate _vN to isolate a corrupted test store
    ProfileSchemaVersion = 1,
    ProfileLeaseSeconds = 90,
    ProfileRenewSeconds = 30,
    ProfileMaxAttempts = 3,
    -- BD-358: one DataStore write budget per player for ROUTINE remote-triggered writes (equip, claims, settings, fusion...).
    -- Settlement, lease renew/release, load and purchases are PRIORITY and never use it. Over budget = a calm "rate_limited"
    -- answer (settings/reveal preferences are coalesced to the latest value instead). WriteBudgetReserve keeps that share of the
    -- server's 60 + 10 x players requests/min free for priority writes.
    WriteBudgetEnabled = true, -- kill switch; offline tests that run hundreds of claims in zero time switch it off
    WriteBurst = 6,
    WriteRefillPerSecond = 1,
    WriteBudgetReserve = 0.4,
    -- BD-359: run settlement is retried longer than other writes: up to 6 attempts, exponential back-off with jitter
    -- (0.6, 1.2, 2.4, 4.8, 9.6 s, about 19 s in all plus request time), never past the window. Still failing = SaveFailed + a pending record that
    -- the lease renew tick retries (2 attempts per tick, exactly once by run id) while the player is present.
    SettlementMaxAttempts = 6,
    SettlementBaseDelaySeconds = 0.6,
    SettlementJitter = 0.1,
    SettlementRetryWindowSeconds = 26, -- leave: 26 s + the lease release stay inside BindToClose's 30 s
    ProfileMaxRecentOperations = 50,

    EquipRequestCooldownSeconds = 0.5,
    CollectionTestGrantEnabled = false,
    CollectionTestGrantSpeciesId = "triceratops",
    CollectionTestGrantVersion = 1,

    ChestTimerSeconds = 0, -- Reveals, rather than offline incubation, pace new eggs.
    HatchRevealSeconds = 1, -- PROVISIONAL owner decision 2026-10-13: 1 s per egg reveal (was 5 s)
    -- PROVISIONAL run-size species boost (BD-044 five tiers). A batch of N run eggs multiplies each tier's
    -- weight by 1 + s * (SpeciesRunBoost[tier] - 1), s = (clamp(N, 1, EggRarityBoostMaxEggs) - 1) / (max - 1).
    -- 2026-10-15 (BD-165, docs/88 exponential rarity): a full run is now ~4-40 eggs, so the boost is gentle and
    -- caps at 40 eggs (5,000 food). Adjacent tier ratios stay 0.33 / 0.15 / 0.22 / 0.14 (never flatter than 1/3); Rare+ is at most ~10% easier at full boost.
    SpeciesRunBoost = {1, 1, 1.1, 1.1, 1.1},
    EggRarityBoostMaxEggs = 40,
    BigChance = 0.03, -- BD-184: Rare-tier chance (docs/88)
    ShinyChance = 0.006, -- BD-184: Epic-tier chance, earned eggs in irregular weather only
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
    RunRewardConfigVersion = 3, -- 3: five species rarity tiers + run-size boost (BD-044)
    HatchPageSize = 10, -- PROVISIONAL: queued run eggs committed per claim transaction; at 1 s/egg = 6 claims/min/player (size 5 would be 12/min and bust the 8/12-player budgets)
    RunEggMaxPerRun = 50, -- PROVISIONAL: catches stop counting at 50 eggs per run (6,250 food); a 5,000-food run (40 eggs) is not truncated
    RunEggBankCapacity = 1000, -- PROVISIONAL: banked run eggs behind the queue (~540 B each, ~0.54 MB); a run starts only while banked <= capacity - RunEggMaxPerRun (500)
    SettledRunLedgerSize = 200, -- PROVISIONAL: settled run IDs kept for exactly-once settlement beyond recentOperations
    -- BD-090 Egg Nests v2 (owner 2026-10-14). ALL PROVISIONAL. A nest is a separate loot item
    -- dropped at the end of a qualified run; it incubates on SERVER time (os.time), ONE nest at a
    -- time (queue), and opens into NestMinSize..NestMaxSize eggs rolled with luck. See docs/71.
    -- Auto-open by rarity (owner 2026-10-15). UI preference only; the server still credits every egg.
    -- When true, a player without the pass sees locked rows and the setting is ignored (no Robux code here).
    AutoOpenRequiresPass = false,
    NestStorageCapacity = 5, -- owned nests (waiting + incubating + ready); when full a new nest is not granted
    NestIncubationSeconds = 10800, -- 3 h each; the next waiting nest starts the moment the previous becomes ready
    NestMinSize = 6, -- (owner 2026-10-15: 6-12, was 10-15; a nest should out-produce a 4-5 egg run but not absurdly) eggs per nest, rolled deterministically from the run id at drop
    NestMaxSize = 12,
    -- Hidden drop gate (never shown in the UI; measured on the server, never client-reported).
    NestMinRunSeconds = 120, -- PROVISIONAL: server clock from RunLifecycle.begin to settlement
    NestMinCatches = 1, -- PROVISIONAL: validated server CatchScore (run eggs) needed for a nest
    NestEggsPerExtraNest = 10, -- PROVISIONAL (BD-165: was 100 at 40/500): +1 nest per 10 further catches on top of a qualified run
    NestMaxPerRun = 3, -- PROVISIONAL cap per run
    -- Luck tiers (index = nest.luck). PROVISIONAL, disclosed in the Nests menu. rarityBoostEggs feeds
    -- the run-batch species boost (EggRarityBoostMaxEggs = maximum), conditionLevels adds to the condition-upgrade level
    -- (clamped to the top tier), shinyChance applies even without irregular weather, bigChance replaces BigChance.
    NestLuckTiers = {
        {rarityBoostEggs = 40, conditionLevels = 2, shinyChance = 0.015, bigChance = 0.06},
    },
    NestClaimRequestCooldownSeconds = 0.5,
    ChestClaimRequestCooldownSeconds = 0.35,
    ChestTestGrantEnabled = false,
    ChestTestGrantCount = 7,
    ChestTestGrantVersion = 1,
    -- PROVISIONAL base species weights (sum 100): Common 72, Uncommon 24, Rare 3.2, Epic 0.7, Legendary 0.1.
    -- Single shop eggs use these directly; run and nest batches add SpeciesRunBoost.
    ChestSpeciesWeights = {
        {speciesId = "compy", weight = 26},
        {speciesId = "raptor", weight = 22},
        {speciesId = "gallimimus", weight = 9},
        {speciesId = "microraptor", weight = 8},
        {speciesId = "dimorphodon", weight = 7},
        {speciesId = "archaeopteryx", weight = 6},
        {speciesId = "stegosaurus", weight = 6},
        {speciesId = "parasaurolophus", weight = 5},
        {speciesId = "pachycephalosaurus", weight = 4},
        {speciesId = "pteranodon", weight = 3},
        {speciesId = "triceratops", weight = 1},
        {speciesId = "brachiosaurus", weight = 0.7},
        {speciesId = "baryonyx", weight = 0.5},
        {speciesId = "ichthyosaurus", weight = 0.5},
        {speciesId = "plesiosaurus", weight = 0.5},
        {speciesId = "ankylosaurus", weight = 0.2},
        {speciesId = "elasmosaurus", weight = 0.2},
        {speciesId = "therizinosaurus", weight = 0.15},
        {speciesId = "quetzalcoatlus", weight = 0.15},
        {speciesId = "tyrannosaurus", weight = 0.04},
        {speciesId = "spinosaurus", weight = 0.03},
        {speciesId = "mosasaurus", weight = 0.03},
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
    -- BD-210 spawn safety: a run only starts once this client reports the island terrain under the spawn as loaded
    -- (or after this many seconds in the hub, so a slow client is never locked out); falls are checked every tick.
    WorldReadyTimeoutSeconds = 20,
    FallRecoveryTickSeconds = 0.2,
    -- BD-225 spike (docs/77): low-poly generated base dinos (Compy, Raptor, Triceratops). OFF by default; shipped look unchanged.
    LowPolyDinos = false,
    -- BD-397 (docs/118): v2 hatch (3D egg viewport, two paint buckets that coat the egg texture, condition, cracks). OFF by
    -- default: the shipped v1 sequence is unchanged. ON = the server loads HatchV2Assets; the client falls back to v1 for any
    -- egg whose meshes or images are unavailable. Playtest profile may turn it on once docs/118 evidence is owner-approved.
    HatchV2 = false,
    -- BD-243/244/247 (docs/101): HP combat behind ONE flag. OFF = no CombatService, no Bite remote, no health bars, the
    -- instant "bigger eats smaller" predation stays exactly as shipped. ON (Studio tests only) = PredationService's
    -- instant eat stops and CombatService runs. Keep false until the BD-252 phone test passes.
    CombatEnabled = false,
    -- BD-245 (docs/101 s8): calm wild predators. Only effective while CombatEnabled is true; false here removes just the NPCs.
    NpcPredatorsEnabled = true,
    SecurityTestHarnessEnabled = false,
    ArtTestHarnessEnabled = false,
    ArtPreviewRequestCooldownSeconds = 0.25,

    -- Build 006/007 probes passed and are disabled again.
    DuplicateSettlementProbe = false,

    -- BD-120 owner admin panel (docs/79). Runtime-only overrides, never saved to profiles.
    -- Admins: the experience's user creator, rank 255 of its group creator, unpublished Studio, or AdminUserIds.
    AdminPanelEnabled = true,
    AdminUserIds = {}, -- extra Roblox UserIds (numbers); empty by default
})
