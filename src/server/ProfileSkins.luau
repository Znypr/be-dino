--!strict
-- ProfileRepository part (docs/150): dino skin reads and the equip / default-skin transaction (BD-456, docs/137).
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local admit = shared.admitAs("ProfileSkins") -- BD-650: the label names the service in the rate_limited count
local adopt = shared.adopt
local handleLeaseLost = shared.handleLeaseLost
local identityAvailable = shared.identityAvailable
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes

-- BD-456 (docs/137 s7): the profile half of dino skins. Inert while Config.DinoSkinsEnabled ~= true: one boolean test, no store request, no profile read.
-- Additive and lazy, like the gift fields: `defaultSkin` and the instance `skin` are created only by an equip/setDefault that actually changes
-- something (a load, a renew and a no-op never add them), the Build 020 reader ignores and preserves them (docs/111 RB1), and a junk value is
-- never a validity condition (it only makes THIS call answer "invalid_skin_state" and leaves the profile alone). The entitlement record
-- `ownedSkins` is read here and NEVER written: only gifts, receipts and admin grants add to it (docs/137 s7). Nothing else on an instance
-- (genes, shiny, big, mutation, stage, origin, cosmetics) or in the profile is touched, so a skin can never change rarity or fusion inputs.
-- Reads (cached profile, no store request): view = {owned = {[id] = true}, defaultSkin = string?, speciesId? and skin? when instanceId is given}.
function ProfileRepository.skinView(player: Player, instanceId: any?): (any, string?)
    if Config.DinoSkinsEnabled ~= true then return nil, "disabled" end
    if not ProfileRepository.isLoaded(player) then return nil, "profile_not_loaded" end
    local profile = profiles[player]
    local owned: {[string]: boolean} = {}
    if typeof(profile.ownedSkins) == "table" then
        for id, yes in profile.ownedSkins do
            if typeof(id) == "string" and yes == true then owned[id] = true end
        end
    end
    local view: {[string]: any} = {owned = owned, defaultSkin = if typeof(profile.defaultSkin) == "string" then profile.defaultSkin else nil}
    if instanceId ~= nil then
        local state = profile.dinosaurIdentity
        if not identityAvailable(state) then return nil, "identity_unavailable" end
        local instance = if typeof(instanceId) == "string" then state.instances[instanceId] else nil
        if typeof(instance) ~= "table" then return nil, "instance_missing" end
        view.speciesId = instance.speciesId
        view.skin = if typeof(instance.skin) == "string" then instance.skin else nil
    end
    return view, nil
end

-- plan = {kind = "equip"|"unequip"|"setDefault"|"clearDefault", instanceId?, skin?, free?, modelSpecies?}. The service builds it from SkinCatalog:
-- `free` = the skin needs no entitlement and fits every species (Base); `modelSpecies` = the set of species that have a model for a non-free skin.
-- Everything is re-checked here against the CURRENT profile inside the lease-checked transaction, so a revoke or a second server cannot be raced.
-- Returns ok, status ("equipped" | "unequipped" | "default_set" | "default_cleared" | "unchanged") or ok = false, reason
-- ("disabled", "profile_not_loaded", "bad_plan", "identity_unavailable", "instance_missing", "not_owned", "no_model", "invalid_skin_state",
-- "invalid_profile", "lease_lost", "save_failed").
function ProfileRepository.applySkin(player: Player, plan: any): (boolean, string)
    if Config.DinoSkinsEnabled ~= true then return false, "disabled" end
    if not ProfileRepository.isLoaded(player) then return false, "profile_not_loaded" end
    if typeof(plan) ~= "table" then return false, "bad_plan" end
    local kind = plan.kind
    if kind ~= "equip" and kind ~= "unequip" and kind ~= "setDefault" and kind ~= "clearDefault" then return false, "bad_plan" end
    local needsInstance = kind == "equip" or kind == "unequip"
    local needsSkin = kind == "equip" or kind == "setDefault"
    if needsInstance and (typeof(plan.instanceId) ~= "string" or #plan.instanceId < 1 or #plan.instanceId > 120) then return false, "bad_plan" end
    if needsSkin and (typeof(plan.skin) ~= "string" or #plan.skin < 1 or #plan.skin > 40) then return false, "bad_plan" end
    if plan.modelSpecies ~= nil and typeof(plan.modelSpecies) ~= "table" then return false, "bad_plan" end
    if not admit(player) then return false, "rate_limited" end -- BD-618 (i): a skin write counts in the same per-player and server-wide budget as every other routine write
    local now = os.time()
    local status = "unchanged"
    local denied: string? = nil
    local leaseLost = false
    local ok, updated = retry("skins", function()
        return store:UpdateAsync(keyFor(player), function(profile)
            denied, leaseLost, status = nil, false, "unchanged"
            if not isValidProfile(profile) then denied = "invalid_profile" return nil end
            if not ownSession(profile) then leaseLost = true return nil end
            -- Entitlement check (not for the free Base look). A junk `ownedSkins` only refuses this call.
            if needsSkin and plan.free ~= true then
                if profile.ownedSkins ~= nil and typeof(profile.ownedSkins) ~= "table" then denied = "invalid_skin_state" return nil end
                local ownedSkins: any = profile.ownedSkins
                if ownedSkins == nil or ownedSkins[plan.skin] ~= true then denied = "not_owned" return nil end
            end
            local changed = false
            if needsInstance then
                local state = profile.dinosaurIdentity
                if not identityAvailable(state) then denied = "identity_unavailable" return nil end
                local instance = state.instances[plan.instanceId]
                if typeof(instance) ~= "table" then denied = "instance_missing" return nil end
                if kind == "equip" then
                    if plan.free ~= true then
                        local set: any = plan.modelSpecies
                        if typeof(set) ~= "table" or typeof(instance.speciesId) ~= "string" or set[instance.speciesId] ~= true then denied = "no_model" return nil end
                    end
                    if instance.skin ~= plan.skin then
                        instance.skin = plan.skin
                        changed = true
                    end
                    status = if changed then "equipped" else "unchanged"
                elseif instance.skin ~= nil then
                    instance.skin = nil
                    changed, status = true, "unequipped"
                end
            elseif kind == "setDefault" then
                if profile.defaultSkin ~= plan.skin then
                    profile.defaultSkin = plan.skin
                    changed = true
                end
                status = if changed then "default_set" else "unchanged"
            elseif profile.defaultSkin ~= nil then -- clearDefault
                profile.defaultSkin = nil
                changed, status = true, "default_cleared"
            end
            if not changed then return nil end -- nothing to write: cancel the transaction, the profile stays byte-identical
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
