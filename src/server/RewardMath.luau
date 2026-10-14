--!strict
-- BD-044 reward math. Pure functions: no DataStore access, no wall clock.
-- Every earned run catch is exactly one run egg; crystals and bonus nests are separate.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local ProgressionConfig = require(ReplicatedStorage.Shared.ProgressionConfig)

local RewardMath = {}

-- Sanitizes an untrusted catch count: NaN/non-number/negative -> 0, fractions floor,
-- anything above the per-run cap (including +inf) clamps to RunEggMaxPerRun.
function RewardMath.runEggCount(catchScore: any): number
    if typeof(catchScore) ~= "number" or catchScore ~= catchScore or catchScore <= 0 then return 0 end
    if catchScore >= Config.RunEggMaxPerRun then return Config.RunEggMaxPerRun end
    return math.floor(catchScore)
end

-- PROVISIONAL deterministic run crystals (see ProgressionConfig.RunCrystal*).
function RewardMath.runCrystals(eggCount: number): number
    local n = RewardMath.runEggCount(eggCount)
    local tier = ProgressionConfig.RunCrystalTierEggs
    local crystals = (ProgressionConfig.RunCrystalPerEggHundredths * math.min(n, tier)
        + ProgressionConfig.RunCrystalPerExtraEggHundredths * math.max(0, n - tier)) // 100
    return math.min(ProgressionConfig.RunCrystalCap, crystals)
end

-- PROVISIONAL nest count for a QUALIFIED run (see RewardMath.nestQualifies): one nest, plus one
-- per NestEggsPerExtraNest catches beyond NestMinCatches, capped per run. 0 when not qualified.
function RewardMath.nestCount(eggCount: number, runSeconds: any?): number
    local n = RewardMath.runEggCount(eggCount)
    if not RewardMath.nestQualifies(n, runSeconds) then return 0 end
    return math.min(Config.NestMaxPerRun, 1 + (n - Config.NestMinCatches) // Config.NestEggsPerExtraNest)
end

-- Hidden gate: server-measured run length AND validated server catch score.
function RewardMath.nestQualifies(eggCount: number, runSeconds: any?): boolean
    if typeof(runSeconds) ~= "number" or runSeconds ~= runSeconds then return false end
    return runSeconds >= Config.NestMinRunSeconds and RewardMath.runEggCount(eggCount) >= Config.NestMinCatches
end

-- Deterministic nest size NestMinSize..NestMaxSize from the nest id (committed at drop).
function RewardMath.nestSize(nestId: string): number
    local h = 5381
    for i = 1, #nestId do h = (h * 33 + string.byte(nestId, i)) % 2147483629 end
    h = bit32.bxor(h, bit32.rshift(h, 7), bit32.rshift(h, 15)) -- spread low bits (djb2 alone is skewed mod small n)
    return Config.NestMinSize + h % (Config.NestMaxSize - Config.NestMinSize + 1)
end

function RewardMath.computeRunReward(catchScore: any, runSeconds: any?)
    local eggCount = RewardMath.runEggCount(catchScore)
    return {
        rewardConfigVersion = Config.RunRewardConfigVersion,
        catchScore = eggCount,
        eggCount = eggCount,
        crystals = RewardMath.runCrystals(eggCount),
        nestCount = RewardMath.nestCount(eggCount, runSeconds),
        accountXP = eggCount, -- unchanged rate: 1 account XP per catch (= per run egg)
    }
end

-- Deterministic, bounded egg identifiers: retries and reconnects cannot mint new IDs.
function RewardMath.runEggId(runId: string, ordinal: number): string
    return "run:" .. runId .. ":" .. tostring(ordinal)
end
function RewardMath.nestId(runId: string, ordinal: number): string
    return "nest:" .. runId .. ":" .. tostring(ordinal)
end

local function weightedChoice(rows, rng: Random)
    local total = 0
    for _, row in rows do total += row.weight end
    local roll = rng:NextNumber(0, total)
    local cumulative = 0
    for _, row in rows do
        cumulative += row.weight
        if roll <= cumulative then return row end
    end
    return rows[#rows]
end

-- Species roll for one egg. Run batches boost Rare/Legendary weights by
-- B = 1 + (clamp(N,1,15)-1)*0.25. Quantity is now always one dinosaur.
function RewardMath.computeChestReward(rng: Random?, eggCount: number?)
    local random = rng or Random.new()
    local boost = 1 + (math.clamp(eggCount or 1, 1, Config.EggRarityBoostMaxEggs) - 1) * Config.EggRarityBoostPerExtraEgg
    local rows = {}
    for _, row in Config.ChestSpeciesWeights do
        table.insert(rows, {speciesId = row.speciesId, weight = row.weight * boost ^ (Config.SpeciesRarities[row.speciesId] - 1)})
    end
    local speciesRow = weightedChoice(rows, random)
    local quantityRow = weightedChoice(Config.ChestQuantityWeights, random)
    return {
        rewardConfigVersion = Config.RunRewardConfigVersion,
        speciesId = speciesRow.speciesId,
        mutationId = "base",
        count = quantityRow.count,
    }
end

return RewardMath
