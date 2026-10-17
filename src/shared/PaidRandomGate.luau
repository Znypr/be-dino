--!strict
-- BD-532 (docs/115 EG1): the ONE rule for "random crystal items are not available". Roblox treats a random item that costs crystals as a paid random
-- item whenever the experience sells Robux products (Config.DeveloperProducts non-empty) unless the paid-random release gate is open
-- (Config.PaidRandomItemsEnabled) AND PolicyService said this player may buy them (PaidRandomEligible). The server refuses with
-- "random_items_unavailable" under exactly this rule (ProfileRepository.progressionAction: buyEgg and upgradeCondition), and the client greys the
-- tile out under the SAME function before the tap, so nobody taps a green BUY EGG that can only answer "Not available yet".
-- Pure (no services): tools/verify_paid_random_gate.py runs it in Luau. Never loosen it here: the policy gate stays as it is (AGENTS.md).
local Gate = {}

Gate.ComingSoon = "Coming soon" -- docs/72: short, plain; shown on the greyed tile

-- developerProducts: Config.DeveloperProducts (any table); enabled: Config.PaidRandomItemsEnabled; eligible: the player's PaidRandomEligible.
function Gate.blocked(developerProducts: any, enabled: any, eligible: any): boolean
    local sells = type(developerProducts) == "table" and next(developerProducts) ~= nil
    return sells and (enabled ~= true or eligible ~= true)
end

-- The server's two guarded actions.
function Gate.guards(action: string): boolean
    return action == "buyEgg" or action == "upgradeCondition"
end

return Gate
