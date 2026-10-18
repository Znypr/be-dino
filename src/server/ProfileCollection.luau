--!strict
-- ProfileRepository part (docs/150): equip a species and Gold / Diamond mutation transactions.
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local EggTraits = shared.EggTraits
local ProgressionRules = shared.ProgressionRules
local admit = shared.admit
local adopt = shared.adopt
local equippedOf = shared.equippedOf
local findOperation = shared.findOperation
local handleLeaseLost = shared.handleLeaseLost
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local knownSpecies = shared.knownSpecies
local objectives = shared.objectives
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local secretSpecies = shared.secretSpecies
local store = shared.store
local syncAttributes = shared.syncAttributes
local trimOperations = shared.trimOperations

-- variantKey (optional, BD-150): equip one exact owned copy of the species. It must be a variant key of the player's
-- own collection entry with count > 0, so a client can never equip a copy it does not own.
-- deferToNextRun (BD-613): every check runs but nothing is written; a valid pick answers (true, "next_run") and the caller
-- (CollectionService) keeps it in memory until the next spawn, then calls this again without the flag.
function ProfileRepository.equipSpecies(player: Player, speciesId: string, variantKey: string?, deferToNextRun: boolean?): (boolean, string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, "profile_not_loaded"
    end
    if typeof(speciesId) ~= "string" or #speciesId < 1 or #speciesId > 32 then
        return false, "invalid_species"
    end
    -- BD-606 (SS7): a found secret species is equippable only while the flag is on and its model slot is filled; otherwise it is as unknown as before.
    local secretEquip = false
    if not knownSpecies(speciesId) then
        if Config.SecretSpeciesEnabled == true and secretSpecies().canEquip(speciesId, true) then secretEquip = true
        else return false, "unknown_species" end
    end

    local cachedEntry = cached.collection[speciesId]
    if typeof(cachedEntry) ~= "table" or (cachedEntry.base + cachedEntry.gold + (cachedEntry.emerald or 0) + cachedEntry.diamond <= 0 and not ProgressionRules.eventMutation(cachedEntry) and not EggTraits.selected(cachedEntry)) then
        return false, "locked"
    end
    if variantKey ~= nil then
        local variants = cachedEntry.variants
        local variant = if typeof(variants) == "table" then variants[variantKey] else nil
        if typeof(variantKey) ~= "string" or #variantKey > 160 or typeof(variant) ~= "table" or typeof(variant.count) ~= "number" or variant.count <= 0 then
            return false, "not_owned"
        end
    end
    local currentId, currentKey = equippedOf(cached)
    if currentId == speciesId and currentKey == variantKey then
        syncAttributes(player, cached)
        return true, "already_equipped"
    end
    if deferToNextRun == true then return true, "next_run" end

    local leaseLost = false
    local locked = false
    local now = os.time()
    if not admit(player) then return false, "rate_limited" end
    local ok, updated = retry("equip species", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end
            local entry = profileValue.collection[speciesId]
            if typeof(entry) ~= "table" or (entry.base + entry.gold + (entry.emerald or 0) + entry.diamond <= 0 and not ProgressionRules.eventMutation(entry) and not EggTraits.selected(entry)) then
                locked = true
                return nil
            end
            if variantKey ~= nil then
                local owned = if typeof(entry.variants) == "table" then entry.variants[variantKey] else nil
                if typeof(owned) ~= "table" or typeof(owned.count) ~= "number" or owned.count <= 0 then
                    locked = true
                    return nil
                end
            end
            if secretEquip then
                -- SS7: the stored pair stays a species Build 020 knows (RB1); the secret is the additive record beside it
                profileValue.equippedSpeciesId = secretSpecies().EquipFallback
                profileValue.equippedVariantKey = nil
                profileValue.equippedSecret = secretSpecies().equipRecord(speciesId, variantKey)
            else
                profileValue.equippedSpeciesId = speciesId
                profileValue.equippedVariantKey = variantKey
                profileValue.equippedSecret = nil
            end
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)

    if not ok or updated == nil then
        if leaseLost then
            handleLeaseLost(player)
            return false, "lease_lost"
        end
        if locked then return false, "locked" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    if Config.ObjectivesEnabled == true then objectives().record(player, "dino_equipped", 1) end -- BD-074: after the committed equip (not for "already_equipped")
    return true, "equipped"
end

-- LEGACY (BD-617): the Build 020 50-copy transaction. No remote and no client page call it any more (fusion is FusionAction); it is kept only so the
-- recorded golden session (tools/profile_golden.luau) and the Build 020 data proofs keep their bytes. Delete it together with a re-recorded golden.
function ProfileRepository.mutateSpecies(player: Player, speciesId: string, targetMutation: string, requestToken: string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, nil, "profile_not_loaded"
    end
    if not knownSpecies(speciesId) then return false, nil, "unknown_species" end
    if targetMutation ~= "gold" and targetMutation ~= "diamond" then return false, nil, "unknown_mutation" end
    local source = if targetMutation == "diamond" then "gold" else "base"
    local cost = if targetMutation == "diamond" then Config.DiamondMutationCost else Config.GoldMutationCost
    if typeof(requestToken) ~= "string" or #requestToken < 1 or #requestToken > 80 then
        return false, nil, "invalid_token"
    end

    local operationId = "mutation:" .. requestToken
    local cachedOperation = findOperation(cached, operationId)
    if cachedOperation then
        if cachedOperation.outcome.speciesId ~= speciesId or cachedOperation.outcome.mutationId ~= targetMutation then return false, nil, "token_conflict" end
        return true, cachedOperation.outcome, "duplicate"
    end

    local cachedEntry = cached.collection[speciesId]
    if typeof(cachedEntry) ~= "table" or cachedEntry[source] < cost then
        return false, nil, "insufficient_copies"
    end

    local outcome = {
        speciesId = speciesId,
        mutationId = targetMutation,
        spentBase = if source == "base" then cost else 0,
        gainedGold = if targetMutation == "gold" then 1 else 0,
        spentGold = if source == "gold" then cost else 0,
        gainedDiamond = if targetMutation == "diamond" then 1 else 0,
    }
    local duplicateOutcome = nil
    local leaseLost = false
    local insufficient = false
    local tokenConflict = false
    local now = os.time()

    if not admit(player) then return false, nil, "rate_limited" end
    local ok, updated = retry("mutation", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end

            local existing = findOperation(profileValue, operationId)
            if existing then
                if existing.outcome.speciesId ~= speciesId or existing.outcome.mutationId ~= targetMutation then tokenConflict = true return nil end
                duplicateOutcome = existing.outcome
                return profileValue
            end

            local entry = profileValue.collection[speciesId]
            if typeof(entry) ~= "table" or entry[source] < cost then
                insufficient = true
                return nil
            end

            entry[source] -= cost
            entry[targetMutation] += 1
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            table.insert(profileValue.recentOperations, {
                id = operationId,
                kind = "mutation",
                outcome = outcome,
            })
            trimOperations(profileValue)
            return profileValue
        end)
    end)

    if not ok or updated == nil then
        if leaseLost then
            handleLeaseLost(player)
            return false, nil, "lease_lost"
        end
        if tokenConflict then return false, nil, "token_conflict" end
        if insufficient then return false, nil, "insufficient_copies" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    local committedOutcome = duplicateOutcome or outcome
    return true, committedOutcome, if duplicateOutcome then "duplicate" else "mutated"
end
end
