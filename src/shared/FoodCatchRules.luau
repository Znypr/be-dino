--!strict
local Config = require(script.Parent.Config)
local Rules = {}
function Rules.award(points: number, carry: number, multiplier: number): (number, number)
    if points ~= points or points <= 0 or points == math.huge then return 0, carry end
    local total = math.max(0, carry) + points * Config.FoodCatchRate * math.clamp(multiplier, 1, 8)
    local whole = math.floor(total + 1e-9)
    return whole, math.max(0, total - whole)
end
-- BD-439: a player kill earns Config.PredationEggPerKill run eggs, whole eggs paid out through a carry, at most
-- Config.PredationEggMaxPerRun per run. Returns (wholeEggs, newCarry, newTotalFromKills). Pure; the caller adds `whole` to CatchScore.
function Rules.awardKill(fromKills: number, carry: number): (number, number, number)
    local cap = Config.PredationEggMaxPerRun
    if fromKills >= cap then return 0, 0, fromKills end
    local total = math.max(0, carry) + Config.PredationEggPerKill
    local whole = math.min(math.floor(total + 1e-9), cap - fromKills)
    local nextTotal = fromKills + whole
    return whole, if nextTotal >= cap then 0 else math.max(0, total - whole), nextTotal
end
return Rules
