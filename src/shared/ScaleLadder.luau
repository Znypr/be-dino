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
-- ESTIMATE = arithmetic on CODE, can be 30% off. BD-471 still has to measure the unmeasured species in Studio (Dino.species[..].measured).
local ScaleLadder = {}
ScaleLadder.Version = 1
ScaleLadder.Unit = "studs"

-- ---------------------------------------------------------------- dinosaurs
-- height = bounding-box height in studs at scale 1 of the LOW-POLY model (Config.LowPolyDinos, the playtest profile); scale = the
-- LowPolyDinoAssets clone-time scale (MIRRORED, CODE). measured = true: a Studio bounding box (Compy 3.5 x 6.6 x 7.7 BD-329,
-- Gallimimus 1.8 x 4.9 x 5.8 BD-329/BD-337, Tyrannosaurus 5.6 x 10.3 x 11.3 docs/108). measured = false: ESTIMATE = scale x
-- heightPerScaleEstimate (docs/139 s3.1 planning value: Brachiosaurus 3.87 -> 11 studs; measured rows run 1.69 to 3.0 per unit).
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
        compy = {scale = 2.2, height = 6.6, measured = true},
        triceratops = {scale = 3.0, height = 8.5, measured = false},
        tyrannosaurus = {scale = 3.66, height = 10.3, measured = true},
        raptor = {scale = 2.1, height = 6.0, measured = false},
        stegosaurus = {scale = 2.64, height = 7.5, measured = false},
        ankylosaurus = {scale = 2.66, height = 7.6, measured = false},
        archaeopteryx = {scale = 1.76, height = 5.0, measured = false},
        baryonyx = {scale = 2.42, height = 6.9, measured = false},
        brachiosaurus = {scale = 3.87, height = 11.0, measured = false},
        dimorphodon = {scale = 1.9, height = 5.4, measured = false},
        elasmosaurus = {scale = 2.66, height = 7.6, measured = false},
        gallimimus = {scale = 2.9, height = 4.9, measured = true},
        ichthyosaurus = {scale = 2.3, height = 6.5, measured = false},
        microraptor = {scale = 1.7, height = 4.8, measured = false},
        mosasaurus = {scale = 3.22, height = 9.1, measured = false},
        pachycephalosaurus = {scale = 1.98, height = 5.6, measured = false},
        parasaurolophus = {scale = 2.31, height = 6.6, measured = false},
        plesiosaurus = {scale = 2.42, height = 6.9, measured = false},
        pteranodon = {scale = 2.31, height = 6.6, measured = false},
        quetzalcoatlus = {scale = 2.8, height = 8.0, measured = false},
        spinosaurus = {scale = 3.51, height = 10.0, measured = false},
        therizinosaurus = {scale = 3.19, height = 9.1, measured = false},
    },
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
-- Height of a species at a drawn scale (the low-poly model scales uniformly with the dino).
function ScaleLadder.dinoHeight(speciesId: string, scale: number): number
    local row = ScaleLadder.Dino.species[speciesId]
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

return ScaleLadder
