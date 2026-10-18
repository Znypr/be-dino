--!strict
-- BD-1038 / docs/186 s6: the pattern and colour BOOST. A dino with a rarer pattern and rarer colours grows a bit faster and walks a bit
-- faster. Pure: pass the tables (ProgressionConfig.EggPatterns, ProgressionConfig.EggColors) and the dino's genes; nothing here reads
-- a client number. The SERVER computes it from the genes it holds for the equipped dino (ProgressionService), and only when
-- Config.GeneBoostEnabled is true; with the flag off every multiplier is exactly 1.
--
--   boostPoints = patternPoints + MainColourWeight * mainColourPoints + AccentColourWeight * accentColourPoints
--   main colour = genes.primaryColorId, accent colour = genes.secondaryColorId (the accent is worth MORE than the main colour:
--   owner 2026-10-18). A dino whose two colour ids are the same counts that colour twice (once as main, once as accent).
--   growthMultiplier = 1 + min(GrowthCap, GrowthPerPoint * boostPoints)      -- +1% a point, at most +15% in total
--   walkMultiplier   = 1 + min(WalkCap,   WalkPerPoint   * boostPoints)      -- +0.5% a point, at most +7% in total
-- The caps are totals for one dino: pattern and colour points together can never give more. PROVISIONAL numbers (docs/186 s6).
-- Bought cosmetics never add points (docs/46); patterns and colours come only from free eggs.
local Curve = require(script.Parent.RarityCurve)
local Boost = {}

-- Version of the formula. Bump it whenever a number below changes, so a profile or a log can say which formula produced a value.
Boost.Version = "bd1038-geneboost-v1"
Boost.TierPoints = table.freeze({0, 1, 2, 4, 6, 10}) -- Common, Uncommon, Rare, Epic, Legendary, Mythic (index = tier + 1)
Boost.MainColourWeight = 0.7
Boost.AccentColourWeight = 1.0
Boost.GrowthPerPoint = 0.01
Boost.GrowthCap = 0.15
Boost.WalkPerPoint = 0.005
Boost.WalkCap = 0.07

-- Points of one pattern or colour id in a table of rows {id, rarity}. Unknown ids, junk and rows without a known rarity are 0.
local function rowPoints(rows: any, id: any): number
    if typeof(rows) ~= "table" or typeof(id) ~= "string" then return 0 end
    for _, row in rows do
        if row.id == id then
            local tier = Curve.index(row.rarity)
            return if tier then Boost.TierPoints[tier + 1] else 0
        end
    end
    return 0
end

-- Pattern points of a pattern id, and colour points of a colour id (0 .. 10).
function Boost.patternPoints(patterns: any, id: any): number return rowPoints(patterns, id) end
function Boost.colourPoints(colours: any, id: any): number return rowPoints(colours, id) end

-- Boost points of a dino's genes ({patternId, primaryColorId, secondaryColorId}). nil or junk genes give 0.
-- A missing secondary colour counts as the main colour again (the same as "both ids are the same").
function Boost.points(patterns: any, colours: any, genes: any): number
    if typeof(genes) ~= "table" then return 0 end
    local main = rowPoints(colours, genes.primaryColorId)
    local accent = if genes.secondaryColorId == nil then main else rowPoints(colours, genes.secondaryColorId)
    return rowPoints(patterns, genes.patternId) + Boost.MainColourWeight * main + Boost.AccentColourWeight * accent
end

function Boost.growthMultiplier(points: number): number
    if type(points) ~= "number" or points ~= points or points <= 0 then return 1 end
    return 1 + math.min(Boost.GrowthCap, Boost.GrowthPerPoint * points)
end

function Boost.walkMultiplier(points: number): number
    if type(points) ~= "number" or points ~= points or points <= 0 then return 1 end
    return 1 + math.min(Boost.WalkCap, Boost.WalkPerPoint * points)
end

-- What the server applies: growth multiplier, walk multiplier and the points. With `enabled` anything but true (the flag
-- Config.GeneBoostEnabled is off) the answer is exactly 1, 1, 0 whatever the genes say.
function Boost.multipliers(enabled: any, patterns: any, colours: any, genes: any): (number, number, number)
    if enabled ~= true then return 1, 1, 0 end
    local points = Boost.points(patterns, colours, genes)
    return Boost.growthMultiplier(points), Boost.walkMultiplier(points), points
end

return table.freeze(Boost)
