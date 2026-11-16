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

local P = require(script.Parent.ProgressionRules) -- the pure grant lives in ProgressionRules (every server harness embeds it)
M.Steps = P.IndexMilestoneSteps
-- PROVISIONAL (LEAD decision 2026-11-16, owner delegated 2026-10-16, docs/115): about one to five normal runs' worth of crystals per step.
M.Crystals = P.IndexMilestoneCrystals
M.found = P.indexFound -- species of the order the collection owns (the server's ownsAny test; secrets never in the order)
M.percent = P.indexPercent -- whole percent found, floored like the Index bar
M.granted = P.indexGranted -- the stored steps as a set; bad input reads as none
M.due = P.indexDue -- the steps reached and not granted yet, smallest first
M.applyToProfile = P.applyIndexMilestones -- server, inside the hatch UpdateAsync transform: grants every due step exactly once

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
