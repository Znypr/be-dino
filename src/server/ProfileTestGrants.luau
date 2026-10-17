--!strict
-- ProfileRepository part (docs/150): flag-gated test setups and Studio demo triggers (inert in the shipped build).
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local DinosaurIdentity = shared.DinosaurIdentity
local HttpService = shared.HttpService
local ProgressionConfig = shared.ProgressionConfig
local ProgressionRules = shared.ProgressionRules
local adopt = shared.adopt
local availableChestCapacity = shared.availableChestCapacity
local bankEggs = shared.bankEggs
local demoActive = shared.demoActive
local enqueueChestIds = shared.enqueueChestIds
local findOperation = shared.findOperation
local handleLeaseLost = shared.handleLeaseLost
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local knownSpecies = shared.knownSpecies
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes
local trimOperations = shared.trimOperations

function ProfileRepository.grantCollectionTestSpecies(player: Player): (boolean, string)
    if not Config.CollectionTestGrantEnabled then return false, "disabled" end
    local speciesId = Config.CollectionTestGrantSpeciesId
    if not knownSpecies(speciesId) then return false, "bad_config" end

    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, "profile_not_loaded"
    end

    local operationId = string.format("test-grant:v%d:%s", Config.CollectionTestGrantVersion, speciesId)
    local duplicate = false
    local leaseLost = false
    local now = os.time()

    local ok, updated = retry("collection test grant", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end
            if findOperation(profileValue, operationId) then
                duplicate = true
                return profileValue
            end

            profileValue.collection[speciesId].base += 1
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            table.insert(profileValue.recentOperations, {
                id = operationId,
                kind = "collection_test_grant",
                outcome = {speciesId = speciesId, count = 1},
            })
            trimOperations(profileValue)
            return profileValue
        end)
    end)

    if not ok or updated == nil then
        if leaseLost then
            handleLeaseLost(player)
            return false, "lease_lost"
        end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, if duplicate then "duplicate" else "granted"
end

-- docs/133 DEMO TRIGGERS. Unreachable unless unpublished Studio (memory-only local profile) AND the demo flag.
-- demoGrantEggs banks the given, fully specified eggs through the SAME bankEggs/queue path a real settlement uses.
function ProfileRepository.demoGrantEggs(player: Player, eggs: {any}, newFind: boolean): (boolean, string)
    if not demoActive then return false, "disabled" end
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return false, "profile_not_loaded" end
    if typeof(eggs) ~= "table" or #eggs < 1 or #eggs > 60 then return false, "bad_eggs" end
    for _, egg in eggs do
        if typeof(egg) ~= "table" or typeof(egg.eggId) ~= "string" or not ProgressionRules.validEgg(egg)
            or typeof(egg.reward) ~= "table" or not knownSpecies(egg.reward.speciesId) then return false, "bad_eggs" end
    end
    local leaseLost = false
    local now = os.time()
    local ok, updated = retry("demo egg party", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost = false
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            local batch = table.create(#eggs)
            for _, egg in eggs do table.insert(batch, DinosaurIdentity.copy(egg)) end
            local progress = ProgressionRules.upgrade(profileValue)
            for _, egg in batch do
                local g = egg.genes or {}
                if newFind then -- forget these traits so the first hatch of each shows the NEW! ribbon
                    local log = progress.discovered
                    if typeof(log) == "table" then
                        if typeof(log.colours) == "table" then log.colours[g.primaryColorId or ""] = nil end
                        if typeof(log.patterns) == "table" then log.patterns[g.patternId or ""] = nil end
                        if typeof(log.mutations) == "table" then log.mutations[egg.mutationId or ""] = nil end
                    end
                else
                    ProgressionRules.discover(profileValue, g, egg.mutationId)
                end
            end
            bankEggs(profileValue, batch, now)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if leaseLost then handleLeaseLost(player) return false, "lease_lost" end
        return false, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "granted"
end

function ProfileRepository.demoEquip(player: Player, speciesId: string): (boolean, string)
    if not demoActive then return false, "disabled" end
    if not knownSpecies(speciesId) then return false, "unknown_species" end
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return false, "profile_not_loaded" end
    local leaseLost = false
    local now = os.time()
    local ok, updated = retry("demo equip", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost = false
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            profileValue.equippedSpeciesId = speciesId -- owned or not: Studio demo only
            profileValue.equippedVariantKey = nil
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if leaseLost then handleLeaseLost(player) return false, "lease_lost" end
        return false, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "equipped"
end

function ProfileRepository.demoAddCrystals(player: Player, amount: number): (boolean, string)
    if not demoActive then return false, "disabled" end
    if typeof(amount) ~= "number" or amount ~= amount or amount % 1 ~= 0 or amount < 1 or amount > 100000 then return false, "bad_amount" end
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return false, "profile_not_loaded" end
    local leaseLost = false
    local now = os.time()
    local ok, updated = retry("demo crystals", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost = false
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            local progress = ProgressionRules.upgrade(profileValue)
            progress.crystals = math.min(ProgressionConfig.MaxCrystals, progress.crystals + amount)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if leaseLost then handleLeaseLost(player) return false, "lease_lost" end
        return false, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "granted"
end

function ProfileRepository.grantChestTest(player: Player): (boolean, string)
    if not Config.ChestTestGrantEnabled then return false, "disabled" end
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, "profile_not_loaded"
    end

    local operationId = string.format("test-chests:v%d", Config.ChestTestGrantVersion)
    local chestIds = {}
    for _ = 1, Config.ChestTestGrantCount do
        table.insert(chestIds, HttpService:GenerateGUID(false))
    end
    local duplicate = false
    local queueFull = false
    local leaseLost = false
    local now = os.time()

    local ok, updated = retry("chest test grant", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end
            if findOperation(profileValue, operationId) then
                duplicate = true
                return profileValue
            end
            if #chestIds > availableChestCapacity(profileValue) then
                queueFull = true
                return nil
            end

            enqueueChestIds(profileValue, chestIds, now)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            table.insert(profileValue.recentOperations, {
                id = operationId,
                kind = "chest_test_grant",
                outcome = {count = #chestIds},
            })
            trimOperations(profileValue)
            return profileValue
        end)
    end)

    if not ok or updated == nil then
        if leaseLost then
            handleLeaseLost(player)
            return false, "lease_lost"
        end
        if queueFull then return false, "queue_full" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, if duplicate then "duplicate" else "granted"
end

function ProfileRepository.setMutationTestCopies(player: Player, speciesId: string, baseCount: number): (boolean, string)
    if not Config.MutationTestSetupEnabled then return false, "disabled" end
    if speciesId ~= Config.MutationTestSpeciesId then return false, "bad_species" end
    if baseCount ~= 49 and baseCount ~= 50 and baseCount ~= 51 then
        return false, "bad_count"
    end

    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, "profile_not_loaded"
    end

    local leaseLost = false
    local now = os.time()
    local ok, updated = retry("mutation test setup", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end
            local entry = profileValue.collection[speciesId]
            if typeof(entry) ~= "table" then return nil end
            entry.base = baseCount
            entry.gold = 0
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
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "set_" .. tostring(baseCount)
end
end
