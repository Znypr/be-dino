--!strict
-- BD-1228 (docs/242 gap 17, flag Config.FriendBonusEnabled): the friend bonus rules. Pure: no Roblox services, so tools/verify_social.py drives them.
-- While at least one Roblox friend of the player is in the same server, the run's crystals get Config.FriendBonusPercent more (at least 1 when the
-- run earned any), added BEFORE the settlement transaction like the run streak, so the run id makes it exactly-once. Free, no paid line, nothing stored.
local F = {}

F.MaxPercent = 50 -- a junk config value can never give more than this
F.Seconds = 30 -- the server re-checks friendships at most this often per pair (Roblox web call)

-- Percent to use: a whole number 0..MaxPercent; anything else is 0 (no bonus).
function F.percent(value: any): number
    if type(value) ~= "number" or value ~= value or value < 1 then return 0 end
    return math.min(F.MaxPercent, math.floor(value))
end

-- Extra crystals for a run that earned `base` crystals: 0 without a friend or with nothing earned, else at least 1.
function F.crystals(base: any, percent: any, hasFriend: boolean): number
    local p = F.percent(percent)
    if not hasFriend or p == 0 or type(base) ~= "number" or base ~= base or base < 1 then return 0 end
    return math.max(1, math.floor(base * p / 100))
end

-- The HUD chip: "Friend bonus +10%" while it applies, "" when it does not (the chip hides).
function F.label(percent: any): string
    local p = F.percent(percent)
    return if p > 0 then string.format("Friend bonus +%d%%", p) else ""
end

-- Does `userId` have a friend among `others` (user ids)? isFriend(a, b) is the (cached) Roblox check.
function F.hasFriend(userId: number, others: {number}, isFriend: (number, number) -> boolean): boolean
    for _, other in others do
        if other ~= userId and isFriend(userId, other) then return true end
    end
    return false
end

-- Order-free key for a pair of user ids (the friend cache).
function F.pairKey(a: number, b: number): string
    return if a < b then a .. ":" .. b else b .. ":" .. a
end

return F
