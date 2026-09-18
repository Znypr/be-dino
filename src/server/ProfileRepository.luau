--!strict
local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local RewardMath = require(script.Parent.RewardMath)

local ProfileRepository = {}

local store = DataStoreService:GetDataStore(Config.ProfileDataStoreName)
local leaseId = HttpService:GenerateGUID(false)
local profiles: {[Player]: any} = {}
local renewing = false

local function keyFor(player: Player): string
    return "u:" .. tostring(player.UserId)
end

local function knownSpecies(speciesId: any): boolean
    if typeof(speciesId) ~= "string" then return false end
    for _, configuredId in Config.SpeciesOrder do
        if configuredId == speciesId then return true end
    end
    return false
end

local function defaultProfile()
    return {
        schemaVersion = Config.ProfileSchemaVersion,
        revision = 0,
        session = nil,
        equippedSpeciesId = "compy",
        collection = {
            compy = {base = 1, gold = 0},
            triceratops = {base = 0, gold = 0},
            tyrannosaurus = {base = 0, gold = 0},
        },
        pendingChestGrants = 0,
        eggs = {},
        recentOperations = {},
        lastCheckpoint = {
            committedAt = 0,
            lastSettledRunId = nil,
        },
    }
end

local function isValidProfile(profile: any): boolean
    if typeof(profile) ~= "table" then return false end
    if profile.schemaVersion ~= Config.ProfileSchemaVersion then return false end
    if typeof(profile.revision) ~= "number" or profile.revision < 0 then return false end
    if typeof(profile.collection) ~= "table" then return false end
    if typeof(profile.recentOperations) ~= "table" then return false end
    if typeof(profile.eggs) ~= "table" then return false end
    if typeof(profile.pendingChestGrants) ~= "number"
        or profile.pendingChestGrants < 0 or profile.pendingChestGrants % 1 ~= 0 then
        return false
    end
    if not knownSpecies(profile.equippedSpeciesId) then return false end
    for _, speciesId in Config.SpeciesOrder do
        local entry = profile.collection[speciesId]
        if typeof(entry) ~= "table"
            or typeof(entry.base) ~= "number" or entry.base < 0 or entry.base % 1 ~= 0
            or typeof(entry.gold) ~= "number" or entry.gold < 0 or entry.gold % 1 ~= 0 then
            return false
        end
    end
    return true
end

local function retry(label: string, fn)
    local lastError = nil
    for attempt = 1, Config.ProfileMaxAttempts do
        local ok, result = pcall(fn)
        if ok then
            return true, result
        end
        lastError = result
        warn(string.format("[Be Dino] %s attempt %d failed: %s", label, attempt, tostring(result)))
        if attempt < Config.ProfileMaxAttempts then
            task.wait(0.5 * (2 ^ (attempt - 1)))
        end
    end
    return false, lastError
end

local function syncAttributes(player: Player, profile: any)
    local collection = profile.collection
    player:SetAttribute("CompyCopies", collection.compy.base)
    player:SetAttribute("CompyGold", collection.compy.gold)
    player:SetAttribute("TriceratopsCopies", collection.triceratops.base)
    player:SetAttribute("TriceratopsGold", collection.triceratops.gold)
    player:SetAttribute("TyrannosaurusCopies", collection.tyrannosaurus.base)
    player:SetAttribute("TyrannosaurusGold", collection.tyrannosaurus.gold)
    player:SetAttribute("PendingChestGrants", profile.pendingChestGrants or 0)
    player:SetAttribute("ProfileRevision", profile.revision or 0)
    player:SetAttribute("EquippedSpeciesId", profile.equippedSpeciesId)
    player:SetAttribute("ActiveChestCount", #profile.eggs)
    local chestSummary = {}
    for index, chest in profile.eggs do
        if index > Config.ChestQueueCapacity then break end
        table.insert(chestSummary, {
            id = chest.eggId,
            readyAt = chest.readyAt,
        })
    end
    player:SetAttribute("ChestQueueJson", HttpService:JSONEncode(chestSummary))
    local nextChest = profile.eggs[1]
    if typeof(nextChest) == "table" then
        player:SetAttribute("NextChestId", nextChest.eggId)
        player:SetAttribute("NextChestReadyAt", nextChest.readyAt)
    else
        player:SetAttribute("NextChestId", "")
        player:SetAttribute("NextChestReadyAt", 0)
    end
end

local function ownSession(profile: any): boolean
    local session = profile.session
    return typeof(session) == "table" and session.leaseId == leaseId
end

local function findOperation(profile: any, operationId: string)
    for _, entry in profile.recentOperations do
        if entry.id == operationId then
            return entry
        end
    end
    return nil
end

local function trimOperations(profile: any)
    while #profile.recentOperations > Config.ProfileMaxRecentOperations do
        table.remove(profile.recentOperations, 1)
    end
end

local function lastChestReadyAt(profile: any, now: number): number
    local result = now
    for _, chest in profile.eggs do
        if typeof(chest) == "table" and typeof(chest.readyAt) == "number" then
            result = math.max(result, chest.readyAt)
        end
    end
    return result
end

local function availableChestCapacity(profile: any): number
    return (Config.ChestQueueCapacity - #profile.eggs)
        + (Config.ChestOverflowCapacity - profile.pendingChestGrants)
end

local function enqueueChestIds(profile: any, chestIds: {string}, now: number)
    local nextReadyAt = lastChestReadyAt(profile, now)
    for _, chestId in chestIds do
        if #profile.eggs < Config.ChestQueueCapacity then
            nextReadyAt += Config.ChestTimerSeconds
            table.insert(profile.eggs, {
                eggId = chestId,
                kind = "alpha_chest",
                readyAt = nextReadyAt,
            })
        else
            profile.pendingChestGrants += 1
        end
    end
end

function ProfileRepository.isLoaded(player: Player): boolean
    return profiles[player] ~= nil and player:GetAttribute("ProfileState") == "Loaded"
end

function ProfileRepository.load(player: Player): boolean
    if profiles[player] then return true end
    player:SetAttribute("ProfileState", "Loading")

    local blockedByLease = false
    local invalidSchema = false
    local now = os.time()

    local ok, updated = retry("profile load", function()
        return store:UpdateAsync(keyFor(player), function(current)
            local profileValue = current
            if profileValue == nil then
                profileValue = defaultProfile()
            end
            if not isValidProfile(profileValue) then
                invalidSchema = true
                return nil
            end

            local session = profileValue.session
            if typeof(session) == "table"
                and session.leaseId ~= leaseId
                and typeof(session.expiresAt) == "number"
                and session.expiresAt > now then
                blockedByLease = true
                return nil
            end

            profileValue.session = {
                leaseId = leaseId,
                jobId = game.JobId,
                expiresAt = now + Config.ProfileLeaseSeconds,
            }
            profileValue.revision += 1
            return profileValue
        end)
    end)

    if not ok or updated == nil or blockedByLease or invalidSchema then
        if blockedByLease then
            player:SetAttribute("ProfileState", "SessionBusy")
        elseif invalidSchema then
            player:SetAttribute("ProfileState", "SchemaError")
        else
            player:SetAttribute("ProfileState", "LoadFailed")
        end
        return false
    end

    profiles[player] = updated
    player:SetAttribute("ProfileState", "Loaded")
    syncAttributes(player, updated)
    return true
end

function ProfileRepository.commitRunSettlement(player: Player, runId: string, catchScore: number)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, nil, "profile_not_loaded"
    end
    if typeof(runId) ~= "string" or #runId < 1 or #runId > 80 then
        return false, nil, "invalid_run_id"
    end

    local outcome = RewardMath.computeRunReward(catchScore)
    local operationId = "run:" .. runId
    local chestIds = {}
    for _ = 1, outcome.chestCount do
        table.insert(chestIds, HttpService:GenerateGUID(false))
    end
    outcome.chestIds = chestIds
    local leaseLost = false
    local queueFull = false
    local duplicateOutcome = nil
    local now = os.time()

    local ok, updated = retry("run settlement", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end

            local existing = findOperation(profileValue, operationId)
            if existing then
                duplicateOutcome = existing.outcome
                return profileValue
            end

            if outcome.chestCount > availableChestCapacity(profileValue) then
                queueFull = true
                return nil
            end

            for _, stack in outcome.stacks do
                local species = profileValue.collection[stack.speciesId]
                if typeof(species) ~= "table" or typeof(species.base) ~= "number" then
                    return nil
                end
                species.base += stack.count
            end

            enqueueChestIds(profileValue, chestIds, now)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            profileValue.lastCheckpoint = {
                committedAt = now,
                lastSettledRunId = runId,
            }
            table.insert(profileValue.recentOperations, {
                id = operationId,
                kind = "run",
                outcome = outcome,
            })
            trimOperations(profileValue)
            return profileValue
        end)
    end)

    if not ok or updated == nil then
        if leaseLost then
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, nil, "lease_lost"
        end
        if queueFull then
            player:SetAttribute("LastChestClaimStatus", "queue_full")
            return false, nil, "queue_full"
        end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end

    profiles[player] = updated
    syncAttributes(player, updated)
    local committedOutcome = duplicateOutcome or outcome
    local summaryParts = {}
    for _, stack in committedOutcome.stacks do
        table.insert(summaryParts, string.format("%dx %s", stack.count, stack.speciesId))
    end
    if #summaryParts == 0 then table.insert(summaryParts, "no dinosaur copies") end
    if committedOutcome.chestCount > 0 then
        table.insert(summaryParts, string.format("%d chest(s)", committedOutcome.chestCount))
    end
    player:SetAttribute("LastRewardText", table.concat(summaryParts, " | "))
    return true, committedOutcome, if duplicateOutcome then "duplicate" else "committed"
end

function ProfileRepository.equipSpecies(player: Player, speciesId: string): (boolean, string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, "profile_not_loaded"
    end
    if typeof(speciesId) ~= "string" or #speciesId < 1 or #speciesId > 32 then
        return false, "invalid_species"
    end
    if not knownSpecies(speciesId) then return false, "unknown_species" end

    local cachedEntry = cached.collection[speciesId]
    if typeof(cachedEntry) ~= "table" or cachedEntry.base + cachedEntry.gold <= 0 then
        return false, "locked"
    end
    if cached.equippedSpeciesId == speciesId then
        syncAttributes(player, cached)
        return true, "already_equipped"
    end

    local leaseLost = false
    local locked = false
    local now = os.time()
    local ok, updated = retry("equip species", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end
            local entry = profileValue.collection[speciesId]
            if typeof(entry) ~= "table" or entry.base + entry.gold <= 0 then
                locked = true
                return nil
            end
            profileValue.equippedSpeciesId = speciesId
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)

    if not ok or updated == nil then
        if leaseLost then
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, "lease_lost"
        end
        if locked then return false, "locked" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    profiles[player] = updated
    syncAttributes(player, updated)
    return true, "equipped"
end

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
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, "lease_lost"
        end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    profiles[player] = updated
    syncAttributes(player, updated)
    return true, if duplicate then "duplicate" else "granted"
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
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, "lease_lost"
        end
        if queueFull then return false, "queue_full" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    profiles[player] = updated
    syncAttributes(player, updated)
    return true, if duplicate then "duplicate" else "granted"
end

function ProfileRepository.claimChest(player: Player, chestId: string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, nil, "profile_not_loaded"
    end
    if typeof(chestId) ~= "string" or #chestId < 1 or #chestId > 80 then
        return false, nil, "invalid_chest_id"
    end

    local operationId = "chest:" .. chestId
    local cachedOperation = findOperation(cached, operationId)
    if cachedOperation then
        return true, cachedOperation.outcome, "duplicate"
    end

    local cachedChest = nil
    for _, chest in cached.eggs do
        if chest.eggId == chestId then
            cachedChest = chest
            break
        end
    end
    if not cachedChest then return false, nil, "missing" end

    local now = os.time()
    if now < cachedChest.readyAt then return false, nil, "not_ready" end

    -- Generate once outside UpdateAsync so retries cannot reroll the reward.
    local outcome = RewardMath.computeChestReward(Random.new())
    local refillChestId = HttpService:GenerateGUID(false)
    local duplicateOutcome = nil
    local leaseLost = false
    local notReady = false
    local missing = false

    local ok, updated = retry("chest claim", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end

            local existing = findOperation(profileValue, operationId)
            if existing then
                duplicateOutcome = existing.outcome
                return profileValue
            end

            local index = nil
            local chest = nil
            for i, candidate in profileValue.eggs do
                if candidate.eggId == chestId then
                    index = i
                    chest = candidate
                    break
                end
            end
            if not index or not chest then
                missing = true
                return nil
            end
            if now < chest.readyAt then
                notReady = true
                return nil
            end

            table.remove(profileValue.eggs, index)
            local species = profileValue.collection[outcome.speciesId]
            if typeof(species) ~= "table" then return nil end
            species.base += outcome.count

            if profileValue.pendingChestGrants > 0 then
                profileValue.pendingChestGrants -= 1
                local readyAt = lastChestReadyAt(profileValue, now) + Config.ChestTimerSeconds
                table.insert(profileValue.eggs, {
                    eggId = refillChestId,
                    kind = "alpha_chest",
                    readyAt = readyAt,
                })
            end

            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            table.insert(profileValue.recentOperations, {
                id = operationId,
                kind = "chest_claim",
                outcome = outcome,
            })
            trimOperations(profileValue)
            return profileValue
        end)
    end)

    if not ok or updated == nil then
        if leaseLost then
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, nil, "lease_lost"
        end
        if notReady then return false, nil, "not_ready" end
        if missing then return false, nil, "missing" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end

    profiles[player] = updated
    syncAttributes(player, updated)
    local committedOutcome = duplicateOutcome or outcome
    player:SetAttribute("LastClaimedChestId", chestId)
    player:SetAttribute("LastChestRewardText", string.format(
        "%dx %s", committedOutcome.count, committedOutcome.speciesId
    ))
    return true, committedOutcome, if duplicateOutcome then "duplicate" else "claimed"
end

function ProfileRepository.mutateSpecies(player: Player, speciesId: string, targetMutation: string, requestToken: string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, nil, "profile_not_loaded"
    end
    if not knownSpecies(speciesId) then return false, nil, "unknown_species" end
    if targetMutation ~= "gold" then return false, nil, "unknown_mutation" end
    if typeof(requestToken) ~= "string" or #requestToken < 1 or #requestToken > 80 then
        return false, nil, "invalid_token"
    end

    local operationId = "mutation:" .. requestToken
    local cachedOperation = findOperation(cached, operationId)
    if cachedOperation then
        return true, cachedOperation.outcome, "duplicate"
    end

    local cachedEntry = cached.collection[speciesId]
    if typeof(cachedEntry) ~= "table" or cachedEntry.base < Config.GoldMutationCost then
        return false, nil, "insufficient_copies"
    end

    local outcome = {
        speciesId = speciesId,
        mutationId = "gold",
        spentBase = Config.GoldMutationCost,
        gainedGold = 1,
    }
    local duplicateOutcome = nil
    local leaseLost = false
    local insufficient = false
    local now = os.time()

    local ok, updated = retry("gold mutation", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end

            local existing = findOperation(profileValue, operationId)
            if existing then
                duplicateOutcome = existing.outcome
                return profileValue
            end

            local entry = profileValue.collection[speciesId]
            if typeof(entry) ~= "table" or entry.base < Config.GoldMutationCost then
                insufficient = true
                return nil
            end

            entry.base -= Config.GoldMutationCost
            entry.gold += 1
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
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, nil, "lease_lost"
        end
        if insufficient then return false, nil, "insufficient_copies" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end

    profiles[player] = updated
    syncAttributes(player, updated)
    local committedOutcome = duplicateOutcome or outcome
    return true, committedOutcome, if duplicateOutcome then "duplicate" else "mutated"
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
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, "lease_lost"
        end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end

    profiles[player] = updated
    syncAttributes(player, updated)
    return true, "set_" .. tostring(baseCount)
end

function ProfileRepository.renew(player: Player): boolean
    if not profiles[player] or player:GetAttribute("ProfileState") ~= "Loaded" then return false end
    local leaseLost = false
    local now = os.time()
    local ok, updated = retry("lease renew", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) or not ownSession(profileValue) then
                leaseLost = true
                return nil
            end
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        player:SetAttribute("ProfileState", if leaseLost then "LeaseLost" else "SaveFailed")
        return false
    end
    profiles[player] = updated
    return true
end

function ProfileRepository.release(player: Player)
    local cached = profiles[player]
    profiles[player] = nil
    if not cached then return end

    retry("lease release", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) or not ownSession(profileValue) then return nil end
            profileValue.session = nil
            return profileValue
        end)
    end)
end

function ProfileRepository.start()
    if renewing then return end
    renewing = true
    task.spawn(function()
        while renewing do
            task.wait(Config.ProfileRenewSeconds)
            for player in profiles do
                if player.Parent then task.spawn(ProfileRepository.renew, player) end
            end
        end
    end)
end

return ProfileRepository
