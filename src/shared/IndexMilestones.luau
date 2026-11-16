--!strict
-- BD-1230 (docs/242 benchmark gap 15, "hits pull completion with silhouettes and rewards at 25/50/100%"): the Dino Index milestone rewards,
-- used ONLY while Config.IndexMilestonesEnabled is on (playtest profile). Pure: no Roblox services, no Instances; the server (ProfileEggs, inside
-- the hatch transaction) and the client (the Index bar chips, the toast) run the SAME count, so the bar and the reward never disagree.
--   * found = species of Config.SpeciesOrder the save owns (any Base / Gold / Diamond copy, a variant or an event copy; secrets are counted
--     apart and never here), the same test as the server's ownsAny.
--   * at 25 / 50 / 75 / 100 % of the species the save gets FREE crystals once (PROVISIONAL amounts, LEAD decision, docs/115). Never Robux, never a
--     paid line, never a random item.
--   * stored: profile.indexMilestones = {"25", "50", ...} (ADDITIVE, created lazily on the first grant; an older build ignores it, docs/111).
--     A milestone in the list is never granted again, even if a later fusion makes the count drop.
-- The locked "?" silhouettes of unfound dinos already exist in the Index list (BD-1194, DinoIndexList); this file adds the rewards.
local M = {}

M.Steps = table.freeze({25, 50, 75, 100})
-- PROVISIONAL (LEAD decision 2026-11-16, owner delegated 2026-10-16): about one to five normal runs' worth of crystals per step.
M.Crystals = table.freeze({[25] = 50, [50] = 100, [75] = 200, [100] = 500})
M.MaxStored = 8 -- structural ceiling for the stored list (4 steps today)

local function ownsAny(entry: any): boolean
    if typeof(entry) ~= "table" then return false end
    for _, key in {"base", "gold", "diamond"} do
        if typeof(entry[key]) == "number" and entry[key] > 0 then return true end
    end
    return (typeof(entry.variants) == "table" and next(entry.variants) ~= nil)
        or (typeof(entry.events) == "table" and next(entry.events) ~= nil)
end

-- How many species of `order` the collection owns.
function M.found(collection: any, order: {string}): number
    if typeof(collection) ~= "table" then return 0 end
    local n = 0
    for _, id in order do
        if ownsAny(collection[id]) then n += 1 end
    end
    return n
end

-- Whole percent found (floor), the same number the Index bar shows (IndexProgress.summary).
function M.percent(found: number, total: number): number
    if total <= 0 then return 0 end
    return math.floor(math.clamp(found, 0, total) / total * 100 + 1e-9)
end

-- The steps already granted, as a set of numbers. Bad or missing input reads as none.
function M.granted(stored: any): {[number]: boolean}
    local set = {}
    if typeof(stored) ~= "table" then return set end
    for _, value in stored do
        local step = tonumber(value)
        if step and M.Crystals[step] then set[step] = true end
    end
    return set
end

-- The steps reached and not granted yet, smallest first.
function M.due(percent: number, stored: any): {number}
    local done, out = M.granted(stored), {}
    for _, step in M.Steps do
        if percent >= step and not done[step] then table.insert(out, step) end
    end
    return out
end

-- Server, INSIDE an UpdateAsync transform after the collection changed: grants every due step exactly once (the stored list is the guard, so
-- a repeated transform starts from the stored profile and grants nothing twice). Adds the crystals to progression.crystals (clamped to
-- maxCrystals) and appends the step to profile.indexMilestones. Returns the granted list {{step, crystals}} (empty when nothing was due).
function M.applyToProfile(profile: any, order: {string}, maxCrystals: number): {{step: number, crystals: number}}
    local out = {}
    if typeof(profile) ~= "table" or typeof(profile.collection) ~= "table" then return out end
    local stored = profile.indexMilestones
    if stored ~= nil and (typeof(stored) ~= "table" or #stored > M.MaxStored) then return out end -- a newer build's field: never touched
    local due = M.due(M.percent(M.found(profile.collection, order), #order), stored)
    if #due == 0 then return out end
    local wallet = profile.progression
    if typeof(wallet) ~= "table" or typeof(wallet.crystals) ~= "number" then return out end -- no wallet yet: nothing granted, tried again next hatch
    profile.indexMilestones = stored or {}
    for _, step in due do
        local crystals = M.Crystals[step]
        wallet.crystals = math.min(maxCrystals, wallet.crystals + crystals)
        table.insert(profile.indexMilestones, tostring(step))
        table.insert(out, {step = step, crystals = crystals})
    end
    return out
end

-- How many species reach `step` percent of `total` (the smallest count whose floored percent is at least the step).
function M.needFor(step: number, total: number): number
    for count = 0, total do
        if M.percent(count, total) >= step then return count end
    end
    return total
end

-- ---------------------------------------------------------------- kid words (docs/72)
-- The Index bar line about the next reward: "2 more: +100" / "+50 soon!" (reached, paid with the next hatch) / "" (all paid).
function M.nextHint(found: number, total: number, stored: any): string
    local done = M.granted(stored)
    for _, step in M.Steps do
        if not done[step] then
            local need = M.needFor(step, total) - found
            if need <= 0 then return "+" .. tostring(M.Crystals[step]) .. " soon!" end
            return tostring(need) .. " more: +" .. tostring(M.Crystals[step])
        end
    end
    return ""
end
function M.toast(step: number): string
    if step >= 100 then return "You found every dino!" end
    return "Dino Index " .. tostring(step) .. "%!"
end
function M.toastBody(crystals: number): string
    return "+" .. tostring(crystals) .. " Crystals"
end

return M
