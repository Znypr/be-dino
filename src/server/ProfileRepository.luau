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
    player:SetAttribute("TriceratopsCopies", collection.triceratops.base)
    player:SetAttribute("TyrannosaurusCopies", collection.tyrannosaurus.base)
    player:SetAttribute("PendingChestGrants", profile.pendingChestGrants or 0)
    player:SetAttribute("ProfileRevision", profile.revision or 0)
    player:SetAttribute("EquippedSpeciesId", profile.equippedSpeciesId)
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
    local leaseLost = false
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

            for _, stack in outcome.stacks do
                local species = profileValue.collection[stack.speciesId]
                if typeof(species) ~= "table" or typeof(species.base) ~= "number" then
                    return nil
                end
                species.base += stack.count
            end

            profileValue.pendingChestGrants = (profileValue.pendingChestGrants or 0) + outcome.chestCount
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
        else
            player:SetAttribute("ProfileState", "SaveFailed")
        end
        return false, nil, if leaseLost then "lease_lost" else "save_failed"
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
