--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)

local RewardMath = {}

local function validateScore(catchScore: number)
    if catchScore ~= catchScore or catchScore == math.huge or catchScore == -math.huge then
        error("catchScore must be finite")
    end
    if catchScore % 1 ~= 0 or catchScore < 0 or catchScore > Config.MaxCatchScore then
        error("catchScore outside supported integer range")
    end
end

local function eligibleTierCount(catchScore: number): number
    local count = 0
    for _, threshold in Config.AlphaTierThresholds do
        if catchScore >= threshold then
            count += 1
        end
    end
    return count
end

function RewardMath.allocateTiers(catchScore: number): {number}
    validateScore(catchScore)
    local tierCount = eligibleTierCount(catchScore)
    if catchScore == 0 or tierCount == 0 then
        return {}
    end

    local allocated = table.create(tierCount, 0)
    local weights = table.create(tierCount, 0)
    for tier = 1, tierCount do
        weights[tier] = Config.RarityQ ^ (tier - 1)
    end

    for _ = 1, catchScore do
        local bestTier = 1
        local bestValue = -math.huge
        for tier = 1, tierCount do
            local value = weights[tier] / (allocated[tier] + 1)
            if value > bestValue then
                bestValue = value
                bestTier = tier
            end
        end
        allocated[bestTier] += 1
    end

    return allocated
end

function RewardMath.earnedChests(catchScore: number): number
    validateScore(catchScore)
    local result = 0
    for _, row in Config.ChestThresholds do
        if catchScore >= row.score then
            result = row.count
        end
    end
    return result
end

function RewardMath.computeRunReward(catchScore: number)
    local tierCounts = RewardMath.allocateTiers(catchScore)
    local stacks = {}
    for tier, count in tierCounts do
        if count > 0 then
            table.insert(stacks, {
                speciesId = Config.AlphaSpeciesByTier[tier],
                mutationId = "base",
                count = count,
            })
        end
    end
    return {
        rewardConfigVersion = 1,
        catchScore = catchScore,
        stacks = stacks,
        chestCount = RewardMath.earnedChests(catchScore),
    }
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

function RewardMath.computeChestReward(rng: Random?)
    local random = rng or Random.new()
    local speciesRow = weightedChoice(Config.ChestSpeciesWeights, random)
    local quantityRow = weightedChoice(Config.ChestQuantityWeights, random)
    return {
        rewardConfigVersion = 1,
        speciesId = speciesRow.speciesId,
        mutationId = "base",
        count = quantityRow.count,
    }
end

return RewardMath
