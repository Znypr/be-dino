--!strict
-- BD-172 / docs/94: colour growth bonus. PROVISIONAL numbers. Each colour has a rarity tier (EggColors[].rarity ->
-- RarityCurve index); a dino's bonus is +1% growth per tier of its primary colour plus the same for its secondary colour
-- (a single-colour dino has primary == secondary, so "double black" = 5% + 5%), capped at MaxPercent.
-- Pure: pass the colour catalog (ProgressionConfig.EggColors). The server reads genes from the equipped dino, never from the client.
local Curve = require(script.Parent.RarityCurve)
local Bonus = {}

Bonus.PercentPerTier = 1 -- Common 0, Uncommon 1, Rare 2, Epic 3, Legendary 4, Mythic 5
Bonus.MaxPercent = 10

local function tierPercent(colors: any, id: any): number
    if typeof(colors) ~= "table" or typeof(id) ~= "string" then return 0 end
    for _, row in colors do
        if row.id == id then return (Curve.index(row.rarity) or 0) * Bonus.PercentPerTier end
    end
    return 0
end

-- genes = {primaryColorId, secondaryColorId}; nil/garbage -> 0. Returns whole percent (0..MaxPercent).
function Bonus.percent(colors: any, genes: any): number
    if typeof(genes) ~= "table" then return 0 end
    local primary = tierPercent(colors, genes.primaryColorId)
    local secondary = if genes.secondaryColorId == nil then primary else tierPercent(colors, genes.secondaryColorId)
    return math.min(Bonus.MaxPercent, primary + secondary)
end

-- Multiplier applied to growth gained: 1 .. 1 + MaxPercent/100.
function Bonus.multiplier(colors: any, genes: any): number
    return 1 + Bonus.percent(colors, genes) / 100
end

-- Kid-short text, nil when there is no bonus.
function Bonus.text(colors: any, genes: any): string?
    local percent = Bonus.percent(colors, genes)
    if percent <= 0 then return nil end
    return string.format("Colour bonus +%d%% growth", percent)
end

return table.freeze(Bonus)
