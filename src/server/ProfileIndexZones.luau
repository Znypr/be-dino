--!strict
-- ProfileRepository part (docs/150): the Dino Index zone reward claim (BD-1299). Inert while Config.IndexZonesEnabled ~= true: one boolean
-- test, no store request, no profile read.
-- Additive and lazy, like the code tokens: `indexZoneRewards` ({"meadow_half", ...}) is created by the first paid claim (a load, a renew and a
-- refused claim never add it), the Build 020 reader ignores and preserves it (docs/111 RB1), and a non-table value there is never a validity
-- condition: it only makes THIS call answer "invalid_state" and leaves the profile alone. The word in the list makes it exactly-once across
-- retries, a lost acknowledgement or a second server. The rule (Shared/IndexZones.apply) checks the zone, the step, the species found in the
-- STORED collection and the wallet cap; the client sends only a zone id and a step word. Crystals only, never Robux.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local ProgressionConfig = shared.ProgressionConfig
local admit = shared.admitAs("ProfileIndexZones")
local adopt = shared.adopt
local handleLeaseLost = shared.handleLeaseLost
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes

-- Claim one zone step. Returns ok, status, crystals: ok = true with "applied" | "already"; ok = false with "disabled",
-- "profile_not_loaded", "rate_limited", "bad_zone", "bad_step", "not_reached", "full", "no_wallet", "invalid_state", "invalid_profile",
-- "lease_lost", "save_failed".
function ProfileRepository.claimIndexZone(player: Player, zoneId: any, step: any): (boolean, string, number)
    if Config.IndexZonesEnabled ~= true then return false, "disabled", 0 end
    if not ProfileRepository.isLoaded(player) then return false, "profile_not_loaded", 0 end
    local Zones = require(game:GetService("ReplicatedStorage").Shared.IndexZones)
    if not Zones.zone(zoneId) then return false, "bad_zone", 0 end
    if typeof(step) ~= "string" or not Zones.Crystals[step] then return false, "bad_step", 0 end
    -- a word already in the cached profile: answered without a store request (the transform below still guards a second server)
    local cached = profiles[player]
    if cached and Zones.claimed(cached.indexZoneRewards)[Zones.key(zoneId, step)] then return true, "already", 0 end
    if not admit(player) then return false, "rate_limited", 0 end
    local now = os.time()
    local status, paid = "already", 0
    local leaseLost = false
    local ok, updated = retry("indexZones", function()
        return store:UpdateAsync(keyFor(player), function(profile)
            status, paid, leaseLost = "already", 0, false
            if not isValidProfile(profile) then status = "invalid_profile" return nil end
            if not ownSession(profile) then leaseLost = true return nil end
            local result, crystals = Zones.apply(profile, zoneId, step, ProgressionConfig.MaxCrystals)
            status, paid = result, crystals
            if result ~= "applied" then return nil end
            profile.revision += 1
            profile.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profile
        end)
    end)
    if not ok then
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed", 0
    end
    if leaseLost then handleLeaseLost(player) return false, "lease_lost", 0 end
    if updated ~= nil then
        adopt(player, updated)
        if profiles[player] then syncAttributes(player, profiles[player]) end
    end
    if status == "applied" or status == "already" then return true, status, paid end
    return false, status, 0
end
end
