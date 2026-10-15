--!strict
-- BD-064 PROVISIONAL fusion trait odds. Pure module: no DataStore, remotes or UI.
--
-- PROVISIONAL (owner decision 2026-10-13: provisional numbers are allowed for the
-- private Milestone 1 playtest; NOT final balance). Every coefficient lives below and
-- the formula is versioned, so a change must bump `Version`; committed outcomes keep
-- the version they were rolled with.
--
-- Formula, for N donors from IdentityFusion's neutral ingredient summary:
--   P(Shiny)              = ShinyCoefficient    * shinyDonors / N     (2/10 -> 10%)
--   P(BIG)                = BigCoefficient      * bigDonors / N
--   P(any event mutation) = MutationCoefficient * mutatedDonors / N
--     P(mutation m)       = MutationCoefficient * donorsWith(m) / N  (proportional pick)
--     P(no mutation)      = 1 - sum(P(m))
--   (no condition wheel: dinosaurs have no condition, only eggs do; v2)
--   P(primary color k)    = donorsWithPrimary(k) / N
--   P(secondary color k)  = donorsWithSecondary(k) / N
--   blend                 = uniform integer 1..99, or 100 when both colors are equal
--   pattern               = locked by the recipe (never rolled)
--   hatchSuccess          = true (a fusion result never fails or cracks open)
--
-- `distribution` is the EXACT distribution `roll` samples from: `roll` draws one
-- uniform per wheel in a fixed order and inverts the same tables with sorted keys, so
-- a quote shown to the player is the distribution the server commits against.
local FusionOdds = {}

FusionOdds.Version = "fusion-odds-provisional-v2"
FusionOdds.ShinyCoefficient = 0.5 -- PROVISIONAL
FusionOdds.BigCoefficient = 0.5 -- PROVISIONAL
FusionOdds.MutationCoefficient = 0.5 -- PROVISIONAL
FusionOdds.BlendMin = 1 -- PROVISIONAL (matches Build 020 egg genes)
FusionOdds.BlendMax = 99
FusionOdds.EqualColorBlend = 100
-- Fixed draw order; one uniform per wheel, always consumed (even when blend is fixed).
FusionOdds.DrawOrder = {"shiny", "big", "mutation", "primaryColor", "secondaryColor", "blend"}

local function sortedKeys(map): {string}
    local keys = {}
    for key in map do table.insert(keys, key) end
    table.sort(keys)
    return keys
end

local function proportional(counts: {[string]: number}, total: number): {[string]: number}
    local result = {}
    for key, n in counts do
        if n > 0 then result[key] = n / total end
    end
    return result
end

-- Returns the exact outcome distribution for a quote summary, or nil, reason.
function FusionOdds.distribution(summary)
    if type(summary) ~= "table" then return nil, "invalid_summary" end
    local n = summary.donorCount
    if type(n) ~= "number" or n < 1 or n % 1 ~= 0 or type(summary.colors) ~= "table" or #summary.colors ~= n
        or type(summary.mutationCounts) ~= "table"
        or type(summary.shinyCount) ~= "number" or type(summary.bigCount) ~= "number"
        or summary.shinyCount < 0 or summary.shinyCount > n or summary.bigCount < 0 or summary.bigCount > n then
        return nil, "invalid_summary"
    end
    local mutated = 0
    for id, count in summary.mutationCounts do
        if type(id) ~= "string" or id == "" or type(count) ~= "number" or count < 0 then return nil, "invalid_summary" end
        mutated += count
    end
    if mutated > n then return nil, "invalid_summary" end

    local mutation = {}
    local mutationTotal = 0
    for id, count in summary.mutationCounts do
        if count > 0 then
            mutation[id] = FusionOdds.MutationCoefficient * count / n
            mutationTotal += mutation[id]
        end
    end
    local primary, secondary = {}, {}
    for _, colors in summary.colors do
        if type(colors) ~= "table" or type(colors.primaryColorId) ~= "string" or type(colors.secondaryColorId) ~= "string" then
            return nil, "invalid_summary"
        end
        primary[colors.primaryColorId] = (primary[colors.primaryColorId] or 0) + 1
        secondary[colors.secondaryColorId] = (secondary[colors.secondaryColorId] or 0) + 1
    end
    return {
        version = FusionOdds.Version,
        shiny = FusionOdds.ShinyCoefficient * summary.shinyCount / n,
        big = FusionOdds.BigCoefficient * summary.bigCount / n,
        mutation = mutation,
        noMutation = math.max(0, 1 - mutationTotal),
        primaryColor = proportional(primary, n),
        secondaryColor = proportional(secondary, n),
        blend = {min = FusionOdds.BlendMin, max = FusionOdds.BlendMax, equalColors = FusionOdds.EqualColorBlend},
    }
end

-- Inverse-CDF pick over sorted keys; `u` in [0, 1). Falls back to the last key with
-- positive probability so floating-point sums slightly below 1 never return nil.
local function pick(dist: {[string]: number}, u: number): string?
    local keys = sortedKeys(dist)
    local acc, last = 0, nil
    for _, key in keys do
        local p = dist[key]
        if p > 0 then
            acc += p
            last = key
            if u < acc then return key end
        end
    end
    return last
end
FusionOdds.pick = pick

-- Mutation wheel including the "" (no mutation) outcome; "" sorts first.
local function mutationWheel(dist)
    local wheel = {[""] = dist.noMutation}
    for id, p in dist.mutation do wheel[id] = p end
    return wheel
end
FusionOdds.mutationWheel = mutationWheel

-- Deterministic for a given sequence of uniforms. Returns traits in the shape
-- IdentityFusion.prepareOutcome validates (pattern overwritten by the recipe there).
function FusionOdds.rollWith(summary, patternId: string, nextNumber: () -> number)
    local dist, reason = FusionOdds.distribution(summary)
    if not dist then error(reason) end
    local u = {}
    for i = 1, #FusionOdds.DrawOrder do
        local value = nextNumber()
        assert(type(value) == "number" and value == value, "invalid uniform")
        -- Clamp into [0, 1): Random:NextNumber() edge values must not escape a wheel.
        u[i] = math.clamp(value, 0, 1 - 2 ^ -53)
    end
    local primary = pick(dist.primaryColor, u[4])
    local secondary = pick(dist.secondaryColor, u[5])
    local blend = FusionOdds.BlendMin + math.min(FusionOdds.BlendMax - FusionOdds.BlendMin,
        math.floor(u[6] * (FusionOdds.BlendMax - FusionOdds.BlendMin + 1)))
    if primary == secondary then blend = FusionOdds.EqualColorBlend end
    return {
        shiny = u[1] < dist.shiny,
        big = u[2] < dist.big,
        mutationId = pick(mutationWheel(dist), u[3]) or "",
        genes = {
            patternId = patternId,
            primaryColorId = primary,
            secondaryColorId = secondary,
            blend = blend,
            hatchSuccess = true,
        },
    }
end

-- Roller in the IdentityFusion contract: {version, roll(summary, patternId)}, plus
-- `distribution` for quotes. `newRng` returns an object with NextNumber() in [0, 1).
function FusionOdds.roller(newRng: () -> any)
    return {
        version = FusionOdds.Version,
        distribution = FusionOdds.distribution,
        roll = function(summary, patternId)
            local rng = newRng()
            return FusionOdds.rollWith(summary, patternId, function() return rng:NextNumber() end)
        end,
    }
end

return FusionOdds
