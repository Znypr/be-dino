--!strict
-- BD-407 (docs/114 section 8.1): THE numeric scale ladder. Every size is in STUDS. Pure data and two helpers (no Instances, no requires), so
-- the game, the offline verifier and docs/114 section 8.1.1 read one table.
--
-- Where each number comes from (tools/verify_scale_ladder.py fails when any of it drifts):
--   WIRED: the game code READS this table (FoodService, SpecialFoods, Arena legacy hub). Changing a number here changes the game.
--   MIRRORED: the owner module stays the source (LowPolyDinoAssets, HubScaleRules, Config, WorldKitData, BiomePlacement, CaveHubLayout,
--   WorldGeneratedMeshes, CaveTerrainRules) because many harnesses load it without a require. The verifier recomputes the value
--   from that module and fails if it differs from this table.
-- Labels: CODE = what the source does today, MEASURED = a Studio bounding box (docs/07-kanban.md BD-329/BD-337, docs/108),
-- ESTIMATE = arithmetic on CODE, can be 30% off. BD-471 measured all 22 species in Studio (Dino.species[..].measured, all true).
local ScaleLadder = {}
ScaleLadder.Version = 1
ScaleLadder.Unit = "studs"

-- ---------------------------------------------------------------- dinosaurs
-- BD-232 (owner rule: "Sizes follow about 10% growth per unlock tier; fly and water species are scaled by bulk up to the T-Rex"; LEAD
-- decision 2026-10-17, owner delegated, docs/115; Water corrected from length to bulk, C-39). Sizing is THE size rule; each species row has its unlock tier (Config.SpeciesRarities),
-- its basis and its target in studs. scale = the LowPolyDinoAssets clone-time scale (MIRRORED, CODE; the one place a species size is set),
-- and width/height/length = the Studio bounding box of LowPolyDinos.clone(species) at spawn (growth scale 1), template pose, 2 decimals
-- (BD-471 method, re-measured after the BD-232 scale change; docs/evidence/2026-10-17-species-sizes/). That box IS the in-game spawn size:
-- the clone bakes `scale` into the parts and DinosaurVisual.render only multiplies by the growth scale (1 at spawn, HubScaleRules 1 in the hub).
-- measured = true for ALL 22 species. The three Water species (C-39, bulk instead of length) were re-read in Studio on 2026-10-17 after the scale change
-- (docs/evidence/2026-10-17-water-bulk/): the boxes equal old box x new scale / old scale to 2 decimals.
-- BD-515 (docs/115 MR1-MR3): snout = how far the snout tip is ahead of the model centre (the root) at spawn, and headLength = the length of the
-- `head` MeshPart along the body, both from the same Studio measurement (the part's bounding box in the model frame, 2 decimals). snout equals
-- length / 2 for all species but Microraptor (its template wings reach further forward than the head). The generated head parts include neck,
-- crest or frill, so Shared/MouthReach clamps the head to 20% to 25% of the body length. The eating point and radius come from these two numbers.
-- BD-992 (docs/115 OWNER decision 2026-10-18, Q14 of docs/116: "T-Rex must be the biggest"): the T-Rex is the KING, `Sizing.kingSteps` growth steps (x1.1 each)
-- above the top unlock tier, so it is the tallest AND the bulkiest dino (bulk 8.91 against Spinosaurus 8.64 and Mosasaurus 8.12). The Armored class is sized by
-- BULK like Fly and Water (a low, wide, long body is not "tall"; by height the Ankylosaurus was the bulkiest dino at 9.95). Fly and Water still top out at
-- Sizing.bulk.top (the Legendary level), which is now below the T-Rex. Not changed: every other species' scale and the unlock tiers.
-- Length is NOT part of "biggest": a long low swimmer (Mosasaurus 16.9) or the Spinosaurus (12.1) are longer by design (fly/water by bulk, owner BD-232).
-- The legacy (non-low-poly) Compy is about 5.5 studs (docs/68); only the low-poly rows are in this table.
ScaleLadder.HeightPerScaleEstimate = 2.84
ScaleLadder.Dino = {
    hubScale = 1, -- OWNER 2026-10-16 (docs/115, BD-480): every dinosaur is exactly 1x in the cave hub, whatever BIG, potions or growth
    maxScale = 4, -- growth cap, HubScaleRules.MaxGrowthScale: s = min(4, sqrt(1 + growth / 50))
    bigMultiplier = 1.2, -- Config.BigScaleMultiplier, so the largest drawn size is maxScale x bigMultiplier = 4.8
    collider = {width = 2.6, length = 3.2, topPerScale = 2.6}, -- Config.DinoCollider*: torso collider, studs per unit of scale
    -- Growth stages: growth = GrowthScore (food x Config.GrowthPerFood 0.1), scale = HubScaleRules.growthScale(growth) rounded to 2 decimals.
    -- spawn 0 food, run = a normal 5-minute run (about 650 food), mid 1,500 food, long 4,000 food, max 7,500 food (the cap), bigMax = max with BIG.
    stages = {
        {id = "spawn", growth = 0, scale = 1, big = false},
        {id = "run", growth = 65, scale = 1.52, big = false},
        {id = "mid", growth = 150, scale = 2, big = false},
        {id = "long", growth = 400, scale = 3, big = false},
        {id = "max", growth = 750, scale = 4, big = false},
        {id = "bigMax", growth = 750, scale = 4.8, big = true},
    },
    order = {"compy", "triceratops", "tyrannosaurus", "raptor", "stegosaurus", "ankylosaurus", "archaeopteryx", "baryonyx", "brachiosaurus", "dimorphodon", "elasmosaurus", "gallimimus", "ichthyosaurus", "microraptor", "mosasaurus", "pachycephalosaurus", "parasaurolophus", "plesiosaurus", "pteranodon", "quetzalcoatlus", "spinosaurus", "therizinosaurus"}, -- Config.SpeciesOrder
    species = {
        compy = {scale = 2.2, tier = 1, basis = "height", target = 6.60, width = 3.49, height = 6.60, length = 7.69, snout = 3.84, headLength = 1.65, measured = true},
        triceratops = {scale = 2.86, tier = 3, basis = "height", target = 7.99, width = 5.79, height = 8.00, length = 8.58, snout = 4.29, headLength = 4.76, measured = true},
        tyrannosaurus = {scale = 3.81, tier = 5, basis = "height", target = 10.63, width = 5.83, height = 10.62, length = 11.43, snout = 5.71, headLength = 5.63, measured = false}, -- BD-992: the KING, one step above tier 5; box = the BD-232 Studio box x 3.81 / 3.47 (not re-read in Studio)
        raptor = {scale = 1.65, tier = 1, basis = "height", target = 6.60, width = 3.49, height = 6.60, length = 7.74, snout = 3.87, headLength = 2.80, measured = true},
        stegosaurus = {scale = 3.9, tier = 2, basis = "height", target = 7.26, width = 5.25, height = 7.25, length = 11.70, snout = 5.85, headLength = 2.55, measured = true},
        ankylosaurus = {scale = 2.67, tier = 4, basis = "bulk", target = 7.38, width = 5.77, height = 6.51, length = 10.68, snout = 5.34, headLength = 3.83, measured = false}, -- BD-992: Armored is sized by bulk (squat, wide); box = the BD-232 Studio box x 2.67 / 3.6 (not re-read in Studio)
        archaeopteryx = {scale = 1.77, tier = 2, basis = "bulk", target = 6.10, width = 7.17, height = 5.31, length = 5.92, snout = 2.96, headLength = 1.34, measured = true},
        baryonyx = {scale = 3.11, tier = 3, basis = "height", target = 7.99, width = 3.99, height = 7.99, length = 9.33, snout = 4.67, headLength = 3.82, measured = true},
        brachiosaurus = {scale = 2.91, tier = 3, basis = "height", target = 7.99, width = 3.73, height = 8.00, length = 8.73, snout = 4.37, headLength = 3.52, measured = true},
        dimorphodon = {scale = 1.71, tier = 1, basis = "bulk", target = 5.55, width = 5.76, height = 5.13, length = 5.73, snout = 2.86, headLength = 3.06, measured = true},
        elasmosaurus = {scale = 3.58, tier = 4, basis = "height", target = 8.78, width = 3.95, height = 8.78, length = 10.74, snout = 5.37, headLength = 4.38, measured = true},
        gallimimus = {scale = 3.89, tier = 1, basis = "height", target = 6.60, width = 2.42, height = 6.61, length = 7.78, snout = 3.89, headLength = 2.52, measured = true},
        ichthyosaurus = {scale = 3.71, tier = 3, basis = "bulk", target = 6.71, width = 4.89, height = 5.57, length = 11.13, snout = 5.57, headLength = 5.11, measured = true},
        microraptor = {scale = 1.52, tier = 1, basis = "bulk", target = 5.55, width = 7.11, height = 4.56, length = 5.29, snout = 2.31, headLength = 0.32, measured = true},
        mosasaurus = {scale = 5.64, tier = 5, basis = "bulk", target = 8.12, width = 5.48, height = 5.77, length = 16.92, snout = 8.46, headLength = 4.37, measured = true},
        pachycephalosaurus = {scale = 2.81, tier = 2, basis = "height", target = 7.26, width = 4.51, height = 7.25, length = 8.43, snout = 4.21, headLength = 3.54, measured = true},
        parasaurolophus = {scale = 3.03, tier = 2, basis = "height", target = 7.26, width = 5.30, height = 7.27, length = 9.09, snout = 4.54, headLength = 3.94, measured = true},
        plesiosaurus = {scale = 2.78, tier = 3, basis = "bulk", target = 6.71, width = 4.66, height = 7.74, length = 8.34, snout = 4.17, headLength = 3.92, measured = true},
        pteranodon = {scale = 1.54, tier = 2, basis = "bulk", target = 6.10, width = 7.07, height = 4.62, length = 6.89, snout = 3.45, headLength = 2.29, measured = true},
        quetzalcoatlus = {scale = 2.04, tier = 4, basis = "bulk", target = 7.38, width = 8.20, height = 6.12, length = 8.04, snout = 4.02, headLength = 3.41, measured = true},
        spinosaurus = {scale = 4.02, tier = 5, basis = "height", target = 9.66, width = 5.53, height = 9.66, length = 12.06, snout = 6.03, headLength = 4.54, measured = true},
        therizinosaurus = {scale = 2.56, tier = 4, basis = "height", target = 8.78, width = 4.91, height = 8.78, length = 10.24, snout = 5.12, headLength = 2.75, measured = true},
    },
    -- BD-606 (docs/115 SS8, LEAD decision, owner delegated): the SEVEN SECRET species (Shared/SecretSpeciesConfig). They are not in `order` or `species` above
    -- (the 22 shipped species, the Index and the doc table stay as they are) but they follow the very same rule, and the pure sizing modules
    -- (HitSize, MouthReach) and the camera verifier read them through ScaleLadder.dinoRow. Unlock tier for SIZE = 1 for all seven (the secret
    -- tier is calm Legendary only for colour and sound, SS3; a secret is a Compy-sized silly find next to the others). Basis by CLASS exactly as
    -- SZ1: Ground height 6.6, Fly and Water bulk 5.55 (the Penguin is Water, so bulk; the Budgiesaurus is Fly, bulk).
    -- measured = false: no mesh exists yet, so the box, `scale` (target / about 3 studs, the generator normalisation, Compy 2.2) and the head numbers are DESIGN
    -- ESTIMATES with bird proportions. A secret species with a filled model slot (SecretSpeciesConfig.assetId) MUST have measured = true,
    -- i.e. its row re-read from the Studio bounding box like the 22 (tools/verify_scale_ladder.py fails otherwise).
    secret = {
        order = {"chickosaurus", "pigeon", "dodo", "duck", "penguin", "budgiesaurus", "foxosaurus"}, -- Shared/SecretSpeciesConfig.Order
        species = {
            chickosaurus = {scale = 2.2, tier = 1, basis = "height", target = 6.60, width = 4.00, height = 6.60, length = 5.80, snout = 2.90, headLength = 1.28, measured = false},
            pigeon = {scale = 2.2, tier = 1, basis = "height", target = 6.60, width = 3.70, height = 6.60, length = 6.30, snout = 3.15, headLength = 1.39, measured = false},
            dodo = {scale = 2.2, tier = 1, basis = "height", target = 6.60, width = 5.30, height = 6.60, length = 6.50, snout = 3.25, headLength = 1.43, measured = false},
            duck = {scale = 2.2, tier = 1, basis = "height", target = 6.60, width = 3.90, height = 6.60, length = 6.70, snout = 3.35, headLength = 1.47, measured = false},
            penguin = {scale = 1.85, tier = 1, basis = "bulk", target = 5.55, width = 4.40, height = 6.60, length = 5.89, snout = 2.95, headLength = 1.30, measured = false},
            budgiesaurus = {scale = 1.85, tier = 1, basis = "bulk", target = 5.55, width = 6.40, height = 5.20, length = 5.14, snout = 2.57, headLength = 1.13, measured = false},
            foxosaurus = {scale = 2.2, tier = 1, basis = "height", target = 6.60, width = 3.40, height = 6.60, length = 8.70, snout = 4.35, headLength = 1.91, measured = false},
        },
    },
}

-- ---------------------------------------------------------------- the size rule (BD-232)
-- Unlock tier = Config.SpeciesRarities (1 Common .. 5 Legendary; a species is unlocked by hatching it). Basis by class: Ground
-- (Elasmosaurus is a normal Ground dino, docs/101) uses HEIGHT; Fly, Water and (BD-992) Armored use BULK (C-39: the owner said "fly/water scaled by bulk"; Water was by length first).
-- The king species (Sizing.kingSpecies, the T-Rex) is sized at tier topTier + kingSteps, so it is the biggest dino.
--   height target(tier) = Sizing.height.tier1 x growthPerTier^(tier - 1)            (Compy, tier 1, is 6.6)
--   bulk   target(tier) = Sizing.bulk.top   / growthPerTier^(topTier - tier)        (the T-Rex's bulk is the top, tier 5)
--   length target(tier) = Sizing.length.top / growthPerTier^(topTier - tier)        (kept as a helper; no species uses it since C-39)
-- bulk = cube root of the bounding-box volume (width x height x length), in studs, so it compares with a height. The tolerance is the
-- allowed relative gap between a species' measured size and its target (scale is rounded to 2 decimals, so the real gap is under 0.5%).
ScaleLadder.Sizing = {
    growthPerTier = 1.1,
    tolerance = 0.02,
    topTier = 5,
    kingSpecies = "tyrannosaurus", -- BD-992: "T-Rex must be the biggest" (owner 2026-10-18)
    kingSteps = 1, -- the king is this many growth steps (x growthPerTier each) above the top unlock tier: target = rule(topTier + kingSteps)
    height = {tier1 = 6.6},
    bulk = {top = 8.12}, -- the Legendary level of the bulk rule (Fly/Water top; the T-Rex was exactly this before BD-992): (5.31 x 9.67 x 10.41) ^ (1/3)
    length = {top = 10.41}, -- the Legendary level of the length rule (kept as a helper)
}

-- ---------------------------------------------------------------- world: plants, trees, rocks, landmarks
-- heights are kit extent height x the placement scale (an upper bound: generated meshes are fitted INSIDE the kit extent box). MIRRORED.
ScaleLadder.Plants = {
    groundcover = {minHeight = 1.9, maxHeight = 4.8}, -- grass and flowers: BiomePlacement.Scales.groundcover 1.6-3.0 x kit extent 1.18-1.61
    small = {minHeight = 4.2, maxHeight = 12}, -- the Small band (ferns, bushes, mushrooms, horsetail): BiomePlacement.SmallBand (BD-473)
}
ScaleLadder.Trees = {
    -- normal trees: every WorldKitData tree extent (5.235 to 26.222) x BiomePlacement.Scales.tree 0.9 to 1.6
    normal = {scale = {0.9, 1.6}, kitHeight = {5.235, 26.222}, minHeight = 4.7, maxHeight = 42},
    -- V3 Blender trees (broadleaf, conifer, palm) are fitted into the SAME kit extent box (Arena.generatedProp), so they share the normal range
    v3 = {minHeight = 4.7, maxHeight = 42},
    -- colossal ancient trees: sized from a target height by BiomePlacement.colossalScale (nothing is placed between 42 and 80)
    colossal = {minHeight = 80, maxHeight = 140, maxCrown = 100, ancientMesh = {broadleaf = 117.59, pine = 117.29, palm = 105.03}}, -- ancientMesh: WorldGeneratedMeshes.Colossal LOD0 size height at the intended size
}
ScaleLadder.Rocks = {
    -- boulders s/m/l and the tall spire and ledge formations x BiomePlacement.Scales.rock 0.85 to 1.8
    island = {scale = {0.85, 1.8}, minHeight = 1.7, boulderMaxHeight = 10.6, maxHeight = 25.6},
    -- Blender ground rocks (WorldGeneratedMeshes.Props size height at scale 1; ids empty until uploaded)
    groundV3 = {small = 1.2, medium = 2.3, mossy = 3.2},
}
ScaleLadder.Landmarks = {scale = 1.4, minHeight = 9.4, maxHeight = 25.8} -- BiomePlacement.LandmarkScale x the four landmark kit extents

-- ---------------------------------------------------------------- food and egg props
-- size = the LARGEST side of the pickup: the ball diameter (Legacy art) or the longest side of the kit MeshPart before the natural-size
-- variety below. WIRED: FoodService.TYPES and SpecialFoods read these numbers.
ScaleLadder.Food = {
    berry = {size = 0.7},
    fruit = {size = 1.0},
    egg = {size = 1.3},
    amber = {size = 1.5},
    goldenDrumstick = {size = 1.9}, -- BD-207 special food (flag off)
    drumstickScale = 1.45, -- the generated drumstick mesh is drawn 1.45 times its kind size
    variety = {0.86, 1.16}, -- natural size variety of the kit mesh (FoodService random:NextNumber)
    pickupRadius = 2.25, -- Config.FoodPickupRadius, reach in studs
}
ScaleLadder.Nest = {
    pad = {5, 1, 5}, -- {w, h, d}: CaveHubLayout.Kinds.nest (cave hub) and the Arena legacy-hub EggNest (WIRED); a flat walk-over mat
    ledge = {12, 12, 6.4}, -- hub_nest_ledge, the big rock behind the Egg Nests station
}

-- ---------------------------------------------------------------- hub: gate, tunnels, stations, signs
-- {w, h, d} in studs unless named. MIRRORED from CaveHubLayout.Kinds / byId / TunnelRadius, CaveTerrainRules.GateHeight.
ScaleLadder.Hub = {
    gate = {mouthWidth = 30, mouthHeight = 20, frame = {39.79, 25.79, 9.77}}, -- the dino door; frame = cave_gate_frame mesh (Blender, id empty until uploaded)
    tunnel = {width = 22, ceiling = 30, pathWidth = 8}, -- CaveHubLayout.TunnelRadius x 2, tunnel ceiling height, laid-stone path
    stationPadRadius = {heart = 18, gate = 15, nests = 17, potions = 15, fusion = 20, style = 18, index = 20, settings = 10, fame = 12},
    sign = {stone = {5.5, 5.5, 2}, arrow = {5, 5, 0.8}, legacyBoard = {30, 7, 1}}, -- legacyBoard = Arena SanctuarySign, WIRED
    station = {
        stallPotion = {14, 10, 7}, forgeAltar = {8, 5, 5}, counterStone = {8.8, 7, 4.5},
        lecternBook = {3, 4, 3}, wallFrame = {3.8, 4.5, 0.7},
    },
}

-- ---------------------------------------------------------------- helpers
-- Size of a species on its own basis (height, bulk or length), from a box.
function ScaleLadder.sizeOf(basis: string, width: number, height: number, length: number): number
    if basis == "length" then return length end
    if basis == "bulk" then return (width * height * length) ^ (1 / 3) end
    return height
end

-- The rule: target size in studs for a basis and unlock tier (1 to 5, or topTier + kingSteps for the king), not rounded.
function ScaleLadder.targetSize(basis: string, tier: number): number
    local s = ScaleLadder.Sizing
    if basis == "height" then return s.height.tier1 * s.growthPerTier ^ (tier - 1) end
    local top = if basis == "bulk" then s.bulk.top else s.length.top
    return top / s.growthPerTier ^ (s.topTier - tier)
end

-- The size row of a species: one of the 22 shipped species, else one of the seven secrets (BD-606), else nil. The ONE lookup that HitSize and
-- MouthReach use, so a secret species is sized by the very same rules as the others.
function ScaleLadder.dinoRow(speciesId: any): any?
    if typeof(speciesId) ~= "string" then return nil end
    local row = (ScaleLadder.Dino.species :: any)[speciesId]
    if row ~= nil then return row end
    return (ScaleLadder.Dino.secret.species :: any)[speciesId]
end

-- Height of a species at a drawn scale (the low-poly model scales uniformly with the dino).
function ScaleLadder.dinoHeight(speciesId: string, scale: number): number
    local row = ScaleLadder.dinoRow(speciesId)
    return if row then row.height * scale else 0
end

-- Scale of a growth stage by id ("spawn", "run", "mid", "long", "max", "bigMax"), nil for an unknown id.
function ScaleLadder.stageScale(stageId: string): number?
    for _, stage in ScaleLadder.Dino.stages do
        if stage.id == stageId then return stage.scale end
    end
    return nil
end

-- The tallest species at scale 1 (the one a door or gate must still clear in the hub).
function ScaleLadder.tallestDinoAtOne(): (string, number)
    local bestId, best = "", 0
    for id, row in ScaleLadder.Dino.species do
        if row.height > best then bestId, best = id, row.height end
    end
    return bestId, best
end

-- BD-992: the tier a species is SIZED at: its unlock tier, plus Sizing.kingSteps for the king (the T-Rex). nil for an unknown species.
function ScaleLadder.sizingTier(speciesId: string): number?
    local row: any = ScaleLadder.dinoRow(speciesId)
    if row == nil then return nil end
    if speciesId == ScaleLadder.Sizing.kingSpecies then return row.tier + ScaleLadder.Sizing.kingSteps end
    return row.tier
end

return ScaleLadder
