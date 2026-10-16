--!strict
-- BD-270: short, kid-readable odds for the "ODDS / DETAILS" panel shown before any random action that costs
-- crystals (random egg, condition upgrade). Every number is computed from the same config tables the server
-- rolls with (Config.ChestSpeciesWeights, ProgressionConfig.ConditionWeights, EggOutcomeOdds.failure); nothing is typed
-- by hand. Percents are rounded with the largest-remainder rule so each group shown adds up to exactly 100%.
-- Pure: no Instances. Checked by tools/verify_odds_copy.py. The long technical list stays in ShopOdds.lines.
local Config = require(script.Parent.Config)
local Progression = require(script.Parent.ProgressionConfig)
local ShopOdds = require(script.Parent.ShopOdds)
local Outcomes = require(script.Parent.EggOutcomeOdds)
local Copy = {}

-- weights -> percents rounded to `decimals` that sum to exactly 100.
function Copy.round(weights: {number}, decimals: number?): {number}
    local unit = 10 ^ (decimals or 2)
    local total = 0
    for _, w in weights do total += w end
    local result, order, used = {}, {}, 0
    for i, w in weights do
        local exact = if total > 0 then 100 * unit * w / total else 0
        local floor = math.floor(exact + 1e-9)
        result[i], used = floor, used + floor
        table.insert(order, {i = i, frac = exact - floor})
    end
    table.sort(order, function(a, b) if a.frac ~= b.frac then return a.frac > b.frac end return a.i < b.i end)
    local missing = math.floor(100 * unit + 0.5) - used
    for k = 1, math.max(0, missing) do local row = order[((k - 1) % #order) + 1] result[row.i] += 1 end
    for i, v in result do result[i] = v / unit end
    return result
end

-- 26 -> "26%", 12.5 -> "12.5%", 0.04 -> "0.04%" (no trailing zeros).
function Copy.text(percent: number): string
    local s = string.format("%.2f", percent)
    s = string.gsub(s, "0+$", "")
    s = string.gsub(s, "%.$", "")
    return s .. "%"
end

local function group(title: string, names: {string}, weights: {number}, note: string?)
    local percents = Copy.round(weights, 2)
    local rows = {}
    for i, name in names do table.insert(rows, {name = name, percent = percents[i], text = Copy.text(percents[i])}) end
    return {title = title, rows = rows, note = note}
end

function Copy.speciesGroup()
    local names, weights = {}, {}
    for _, row in Config.ChestSpeciesWeights do
        table.insert(names, Config.SpeciesDisplayNames[row.speciesId] or row.speciesId)
        table.insert(weights, row.weight)
    end
    return group("Which dino?", names, weights)
end

function Copy.conditionGroup(level: number)
    local percents = ShopOdds.conditionPercents(level)
    local names = {}
    for _, row in Progression.Conditions do table.insert(names, row.name) end
    return group("Egg condition", names, percents)
end

-- Cracked eggs can fail; everything else always hatches.
function Copy.hatchGroup(level: number)
    local failed = Outcomes.failure(level)
    return group("Does it hatch?", {"Hatches a dino", "Cracked: no dino"}, {1 - failed, failed},
        "A cracked egg gives no dino and no crystals back.")
end

-- Egg shop: groups in reading order.
function Copy.eggGroups(level: number)
    return {Copy.hatchGroup(level), Copy.speciesGroup(), Copy.conditionGroup(level)}
end

-- Condition upgrade confirm: the chances your eggs will have AFTER the upgrade.
function Copy.upgradeGroups(newLevel: number)
    return {Copy.conditionGroup(newLevel)}
end

function Copy.notes(isEgg: boolean): {string}
    local notes = {"Each egg is a fresh roll. Past eggs do not change the next one."}
    if isEgg then table.insert(notes, "Shop eggs never have Shiny or event looks.") end
    table.insert(notes, "Only your Condition level changes these chances.")
    return notes
end

return Copy
