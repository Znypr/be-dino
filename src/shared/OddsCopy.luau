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

-- BD-365: the safe first eggs. The number is Progression.SafeEggs (the server rule in FtueRules is checked equal by
-- tools/verify_safe_eggs_line.py). The rule only covers eggs found on RUNS (shop and nest eggs roll the normal odds), so the
-- line says "from runs", and it only shows while the profile still has all its safe eggs left (safeLeft comes from
-- FtueRules.safeEggsLeftView). Plain words for children (docs/72); drawn at NoteTextSize, never below FtueP1.MinTextSize.
Copy.NoteTextSize = 18
function Copy.safeEggsLine(safeLeft: number?): string?
    if safeLeft == nil or safeLeft < Progression.SafeEggs then return nil end
    return string.format("Your first %d eggs from runs are always safe.", Progression.SafeEggs)
end

function Copy.conditionGroup(level: number, safeLeft: number?)
    local percents = ShopOdds.conditionPercents(level)
    local names = {}
    for _, row in Progression.Conditions do table.insert(names, row.name) end
    return group("Is the egg Cracked?", names, percents, Copy.safeEggsLine(safeLeft))
end

-- Two different numbers, never mixed up: "chance an egg IS Cracked" is the Cracked weight in the Egg condition group;
-- "chance a Cracked egg HATCHES" is Conditions[cracked].hatchChance (a separate 20%). Both come from ProgressionConfig.
local function crackedHatchChance(): number
    for _, c in Progression.Conditions do if c.id == "cracked" then return c.hatchChance end end
    return 1
end

function Copy.hatchGroup(level: number)
    local ok = crackedHatchChance()
    return group("Does a Cracked egg hatch?", {"Cracked egg hatches", "Cracked egg stays shut"}, {ok, 1 - ok},
        "Only Cracked eggs can stay shut. A shut egg gives no dino and no crystals back.")
end

-- All eggs together: how many of every 100 eggs give a dino (derived from the two numbers above).
function Copy.overallHatchPercent(level: number): number
    return Copy.round({1 - Outcomes.failure(level), Outcomes.failure(level)}, 2)[1]
end

-- BD-301: ONE sentence for the Buy Egg confirm; same config numbers as the odds panel.
function Copy.hatchSentence(level: number): string
    return string.format("%s of every 100 eggs hatch a dino. A cracked egg gives nothing back.", string.format("%g", Copy.overallHatchPercent(level)))
end

-- BD-303: plain words for the condition upgrade. requiredLevel is the player level the server demands (ProgressionRules).
function Copy.upgradeUnlock(requiredLevel: number?, playerLevel: number): string
    if requiredLevel == nil then return "Top level reached" end
    if playerLevel >= requiredLevel then return "Ready to buy!" end
    return "Reach level " .. requiredLevel .. " to buy this."
end

-- BD-303: the condition whose chance grows the most when going from oldLevel to newLevel (its egg is shown on the confirm).
function Copy.biggestGain(oldLevel: number, newLevel: number): string
    local old, new = ShopOdds.conditionPercents(oldLevel), ShopOdds.conditionPercents(newLevel)
    local bestId, best = Progression.Conditions[1].id, -math.huge
    for i, row in Progression.Conditions do
        local gain = new[i] - old[i]
        if gain > best then bestId, best = row.id, gain end
    end
    return bestId
end

-- Egg shop: groups in reading order.
function Copy.eggGroups(level: number, safeLeft: number?)
    return {Copy.hatchGroup(level), Copy.speciesGroup(), Copy.conditionGroup(level, safeLeft)}
end

-- Condition upgrade confirm: the chances your eggs will have AFTER the upgrade.
function Copy.upgradeGroups(newLevel: number)
    return {Copy.conditionGroup(newLevel)}
end

-- BD-347 (paid-random policy, AGENTS.md): fusion is odds-first and costs no real money in this version. These are plain
-- lines for the Fusion Menu: a calm one-liner beside FUSE and a details line in the odds panel. If Robux-linked donors or a
-- paid fusion ever ship, the server gate (random_items_unavailable) stays and this wording must be revisited first.
Copy.fusionCalm = "Odds are shown before you fuse"
Copy.fusionDetails = "Fusion uses no real money in this version. The chances above are exact and are shown before you fuse."

-- BD-606 (docs/115 SS9, docs/149 s5): ONE honest line about the secret dino, for FREE eggs only (eggs found on runs and opened from free nests).
-- It is told only while secret dinos can really drop (Config.SecretSpeciesEnabled AND at least one model slot filled: the caller passes that as
-- `secretLive`), never as "guaranteed", never with a number or a price, and never as part of a shop egg's own odds: Copy.eggGroups, Copy.notes and
-- ShopOdds.lines (what a bought egg can be) never mention it. Plain words for children (docs/72).
Copy.secretLine = "A tiny chance of a secret dino in free eggs"
function Copy.freeEggNotes(secretLive: boolean?): {string}
    if secretLive == true then return {Copy.secretLine} end
    return {}
end

function Copy.notes(isEgg: boolean): {string}
    local notes = {"Each egg is a fresh roll. Past eggs do not change the next one."}
    if isEgg then table.insert(notes, "Shop eggs never have Shiny or event looks.") end
    table.insert(notes, "Only your Condition level changes these chances.")
    return notes
end

return Copy
