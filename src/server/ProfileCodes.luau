--!strict
-- ProfileRepository part (docs/150): the one-use code and group gift chest transaction (BD-1233, docs/242 gap 18).
-- Inert while Config.CodesEnabled ~= true: one boolean test, no store request, no profile read.
-- Additive and lazy, like the gift fields: `redeemedCodes` ({[token] = unix time}) is created by the first applied code (a load, a renew and a
-- refused try never add it), the Build 020 reader ignores and preserves it (docs/111 RB1), and a non-table value there is never a validity
-- condition: it only makes THIS call answer "invalid_code_state" and leaves the profile alone. The token makes it exactly-once across retries,
-- a lost acknowledgement or a second server. Crystals only, capped by ProgressionConfig.MaxCrystals (full = nothing written).
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local ProgressionConfig = shared.ProgressionConfig
local ProgressionRules = shared.ProgressionRules
local admit = shared.admitAs("ProfileCodes")
local adopt = shared.adopt
local handleLeaseLost = shared.handleLeaseLost
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes

local MAX_STORED = 300 -- Shared/CodeRules.MaxStored

-- Has this save used the token? (cached profile, no store request)
function ProfileRepository.codeUsed(player: Player, token: string): boolean
    if Config.CodesEnabled ~= true then return false end
    local profile = profiles[player]
    if not profile or typeof(profile.redeemedCodes) ~= "table" then return false end
    return profile.redeemedCodes[token] ~= nil
end

-- Apply one token with `crystals` free crystals. Returns ok, status: "applied" | "already" | "full" or ok = false, reason
-- ("disabled", "profile_not_loaded", "bad_plan", "rate_limited", "invalid_code_state", "held_cap", "invalid_profile", "lease_lost", "save_failed").
function ProfileRepository.redeemToken(player: Player, token: any, crystals: any): (boolean, string)
    if Config.CodesEnabled ~= true then return false, "disabled" end
    if not ProfileRepository.isLoaded(player) then return false, "profile_not_loaded" end
    if typeof(token) ~= "string" or #token < 3 or #token > 40 then return false, "bad_plan" end
    if typeof(crystals) ~= "number" or crystals < 1 or crystals > 100000 or crystals % 1 ~= 0 then return false, "bad_plan" end
    if not admit(player) then return false, "rate_limited" end
    local now = os.time()
    local status = "already"
    local denied: string? = nil
    local leaseLost = false
    local ok, updated = retry("codes", function()
        return store:UpdateAsync(keyFor(player), function(profile)
            denied, leaseLost, status = nil, false, "already"
            if not isValidProfile(profile) then denied = "invalid_profile" return nil end
            if not ownSession(profile) then leaseLost = true return nil end
            if profile.redeemedCodes ~= nil and typeof(profile.redeemedCodes) ~= "table" then denied = "invalid_code_state" return nil end
            local used: {[string]: any} = if profile.redeemedCodes ~= nil then table.clone(profile.redeemedCodes) else {}
            if used[token] ~= nil then status = "already" return nil end
            local count = 0
            for _ in used do count += 1 end
            if count >= MAX_STORED then denied = "held_cap" return nil end
            local progress = ProgressionRules.upgrade(profile)
            if progress.crystals + crystals > ProgressionConfig.MaxCrystals then status = "full" return nil end
            progress.crystals += crystals
            used[token] = now
            profile.redeemedCodes = used
            status = "applied"
            profile.revision += 1
            profile.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profile
        end)
    end)
    if not ok then
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end
    if leaseLost then handleLeaseLost(player) return false, "lease_lost" end
    if denied ~= nil then return false, denied end
    if updated ~= nil then
        adopt(player, updated)
        if profiles[player] then syncAttributes(player, profiles[player]) end
    end
    return true, status
end
end
