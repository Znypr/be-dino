--!strict
-- BD-184 / docs/88 exponential rarity. The ONE place that defines the shared six-tier ladder.
-- Tier k (0 = Common) has chance proportional to Ratio^k (r = 1/5): 80 / 16 / 3.2 / 0.64 / 0.128 / 0.0256 %.
-- Prices and effort grow PriceFactor (x2.8) per tier. Pure functions, no Roblox services.
-- Config tables (ProgressionConfig, Config) keep literal numbers because the offline verifiers inline those files;
-- tools/verify_rarity.py proves every literal still matches this module, so an owner tweak here is caught everywhere.
local Curve = {}

Curve.Names = table.freeze({"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"})
Curve.Ratio = 1 / 5
Curve.PriceFactor = 2.8
Curve.MinAdjacentRatio = 1 / 6 -- no table may be steeper than this
Curve.MaxAdjacentRatio = 1 / 3 -- no boost may flatten adjacent tiers beyond this (each tier >= 3x rarer)

function Curve.tierCount(): number return #Curve.Names end

-- 0-based tier index of a rarity name, nil when unknown.
function Curve.index(name: string): number?
    for i, n in Curve.Names do if n == name then return i - 1 end end
    return nil
end

-- Unnormalised weight of tier k (Common = 1).
function Curve.weight(tier: number, ratio: number?): number
    return (ratio or Curve.Ratio) ^ tier
end

-- Chances (0..1) for the first `count` tiers, renormalised to sum to exactly 1.
-- count 6: 80/16/3.2/0.64/0.128/0.0256 (of 99.9936); count 5: 80.02/16.00/3.20/0.64/0.128.
function Curve.weights(count: number, ratio: number?): {number}
    assert(count >= 1 and count <= #Curve.Names and count % 1 == 0, "RarityCurve: tier count")
    local out, total = {}, 0
    for k = 0, count - 1 do local w = Curve.weight(k, ratio) out[k + 1] = w total += w end
    for k = 1, count do out[k] /= total end
    return out
end

-- Price of tier k from a Common base price, rounded to two significant figures (60 -> 60,170,470,1300,3700,10000).
function Curve.price(tier: number, base: number, factor: number?): number
    local raw = base * (factor or Curve.PriceFactor) ^ tier
    if raw < 10 then return math.floor(raw + .5) end
    local magnitude = 10 ^ (math.floor(math.log10(raw)) - 1)
    return math.floor(raw / magnitude + .5) * magnitude
end

-- Apply per-tier boost factors to tier weights, then flatten no adjacent pair beyond MaxAdjacentRatio: a boost may make a
-- tier easier only until it is within `cap` of the tier below (a tier whose base ratio is already above the cap is left
-- alone). Never reorders tiers. NOT renormalised: callers divide by the sum.
function Curve.boost(weights: {number}, factors: {number}, maxRatio: number?): {number}
    local cap = maxRatio or Curve.MaxAdjacentRatio
    local out = {}
    for i, w in weights do out[i] = w * (factors[i] or 1) end
    for i = 2, #out do
        local limit = out[i - 1] * cap
        if out[i] > limit then out[i] = math.max(limit, weights[i]) end
    end
    return out
end

-- BD-1033: chance of each tier (0..1, index 1 = Common, always 6 entries, 0 for an empty tier) of a table of rows
-- {rarity = "Common".., weight = n}. One helper for every weighted table that carries rarity names (patterns, colours),
-- used by the offline verifiers and the timing simulation so nobody re-derives tier shares by hand.
function Curve.tierTotals(rows: {any}): {number}
    local out, total = {}, 0
    for i = 1, #Curve.Names do out[i] = 0 end
    for _, row in rows do
        local k = Curve.index(row.rarity)
        if k then out[k + 1] += row.weight total += row.weight end
    end
    if total > 0 then for i = 1, #out do out[i] /= total end end
    return out
end

-- BD-1036: the rarer of two tier names ("Common".."Mythic"). A dino has two colours; the colour rarity it shows is the rarer one.
-- Unknown or missing names count as Common; the first argument wins a tie.
function Curve.rarer(a: string?, b: string?): string
    local ia, ib = Curve.index(a or "") or 0, Curve.index(b or "") or 0
    return Curve.Names[(if ib > ia then ib else ia) + 1]
end

-- Percent text for a chance in percent: 80 -> "80%", 0.0256 -> "0.0256%".
function Curve.percentText(percent: number): string
    return string.format("%g%%", tonumber(string.format("%.4g", percent)) :: number)
end

return table.freeze(Curve)
