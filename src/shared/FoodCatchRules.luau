--!strict
local Config = require(script.Parent.Config)
local Rules = {}
function Rules.award(points: number, carry: number, multiplier: number): (number, number)
    if points ~= points or points <= 0 or points == math.huge then return 0, carry end
    local total = math.max(0, carry) + points * Config.FoodCatchRate * math.clamp(multiplier, 1, 8)
    local whole = math.floor(total + 1e-9)
    return whole, math.max(0, total - whole)
end
return Rules
