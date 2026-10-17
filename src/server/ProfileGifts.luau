--!strict
-- ProfileRepository part (docs/150): gift claim transaction (BD-451, docs/134).
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local ProgressionConfig = shared.ProgressionConfig
local ProgressionRules = shared.ProgressionRules
local adopt = shared.adopt
local handleLeaseLost = shared.handleLeaseLost
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes

------------------------------------------------------------------ BD-451 gifting core (docs/134 s7)
-- The profile half of the gift claim. Inert while Config.GiftClaimEnabled ~= true: one boolean test, no store request, no profile read.
-- GiftService decides WHICH gifts apply (setting, mute, block, validity); this transaction only applies a plan, lease-checked, exactly
-- once: profile.claimedGifts[giftId] (a unix time, or "revoked") is the token, so a duplicate delivery, a retry after a lost acknowledgement
-- or a second server can never grant twice. Additive and lazy: claimedGifts / ownedSkins are created by the first applied gift (a load never
-- adds them), the Build 020 reader ignores and preserves them, and a non-table value there is never a validity condition (docs/111): it only
-- makes this transaction answer "invalid_gift_state" and leaves the profile alone.
-- plan = {apply = {{id, kind = "skin"|"crystals", skin?, amount?, thankYou?}...}, revoke = {{id, skin?}...}, claimedCap = n}.
-- Returns ok, results ({[giftId] = applied | converted | already | held_crystals | held_cap | revoked | revoked_pending | already_revoked}) or ok = false, status.
function ProfileRepository.applyGifts(player: Player, plan: any): (boolean, any)
    if Config.GiftClaimEnabled ~= true then return false, "disabled" end
    if not ProfileRepository.isLoaded(player) then return false, "profile_not_loaded" end
    if typeof(plan) ~= "table" or typeof(plan.apply) ~= "table" or typeof(plan.revoke) ~= "table" then return false, "bad_plan" end
    local cap = if typeof(plan.claimedCap) == "number" and plan.claimedCap >= 1 and plan.claimedCap <= 100000 then plan.claimedCap else 5000
    local maxCrystals = ProgressionConfig.MaxCrystals
    local now = os.time()
    local results: {[string]: string} = {}
    local denied: string? = nil
    local leaseLost = false
    local ok, updated = retry("gifts", function()
        return store:UpdateAsync(keyFor(player), function(profile)
            denied, leaseLost = nil, false
            table.clear(results)
            if not isValidProfile(profile) then denied = "invalid_profile" return nil end
            if not ownSession(profile) then leaseLost = true return nil end
            if (profile.claimedGifts ~= nil and typeof(profile.claimedGifts) ~= "table") or (profile.ownedSkins ~= nil and typeof(profile.ownedSkins) ~= "table") then
                denied = "invalid_gift_state"
                return nil
            end
            local claimed: {[string]: any} = if profile.claimedGifts ~= nil then table.clone(profile.claimedGifts) else {}
            local owned: {[string]: any} = if profile.ownedSkins ~= nil then table.clone(profile.ownedSkins) else {}
            local claimedCount = 0
            for _ in claimed do claimedCount += 1 end
            local progress: any = nil
            local changed = false
            for _, op in plan.apply do
                local id = op.id
                if typeof(id) ~= "string" or (op.kind == "skin" and typeof(op.skin) ~= "string") then continue end
                if claimed[id] ~= nil then
                    results[id] = "already"
                elseif claimedCount >= cap then
                    results[id] = "held_cap" -- fail closed, like purchaseReceipts: never grant what cannot be recorded
                elseif op.kind == "skin" and typeof(op.skin) == "string" and owned[op.skin] ~= true then
                    owned[op.skin] = true
                    claimed[id], claimedCount, changed, results[id] = now, claimedCount + 1, true, "applied"
                elseif op.kind == "skin" or op.kind == "crystals" then
                    -- A skin the player already owns (a purchase raced the gift) becomes thank-you crystals instead of a no-op (GF16).
                    local amount = if op.kind == "crystals" then op.amount else op.thankYou
                    if typeof(amount) ~= "number" or amount < 1 or amount % 1 ~= 0 then
                        results[id] = "held_cap"
                    else
                        progress = progress or ProgressionRules.upgrade(profile)
                        if progress.crystals + amount > maxCrystals then
                            results[id] = "held_crystals" -- stays pending: "Make room, then open your gift"
                        else
                            progress.crystals += amount
                            claimed[id], claimedCount, changed = now, claimedCount + 1, true
                            results[id] = if op.kind == "crystals" then "applied" else "converted"
                        end
                    end
                end
            end
            for _, op in plan.revoke do
                local id = op.id
                if typeof(id) ~= "string" then continue end
                local current = claimed[id]
                if current == "revoked" then
                    results[id] = "already_revoked"
                elseif current == nil and claimedCount >= cap then
                    results[id] = "held_cap"
                else
                    if typeof(current) == "number" and typeof(op.skin) == "string" then owned[op.skin] = nil end -- crystals already spent are not clawed back
                    if current == nil then claimedCount += 1 end
                    claimed[id], changed = "revoked", true
                    results[id] = if current == nil then "revoked_pending" else "revoked"
                end
            end
            if not changed then return nil end -- nothing to write: cancel the transaction, the profile stays byte-identical
            profile.claimedGifts = claimed
            if next(owned) ~= nil or profile.ownedSkins ~= nil then profile.ownedSkins = owned end
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
    return true, results
end
end
