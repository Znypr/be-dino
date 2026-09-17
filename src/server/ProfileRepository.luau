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
end

local function ownSession(profile: any): boolean
    local session = profile.session
    return typeof(session) == "table" and session.leaseId == leaseId
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
            local profile = current
            if profile == nil then
                profile = defaultProfile()
            end
            if not isValidProfile(profile) then
                invalidSchema = true
                return nil
            end

            local session = profile.session
            if typeof(session) == "table"
                and session.leaseId ~= leaseId
                and typeof(session.expiresAt) == "number"
                and session.expiresAt > now then
                blockedByLease = true
                return nil
            end

            profile.session = {
                leaseId = leaseId,
                jobId = game.JobId,
                expiresAt = now + Config.ProfileLeaseSeconds,
            }
            profile.revision += 1
            return profile
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

local function findOperation(profile: any, operationId: string)
    for _, entry in profile.recentOperations do
        if entry.id == operationId then
            return entry
        end
    end
    return nil
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
        return store:UpdateAsync(keyFor(player), function(profile)
            if not isValidProfile(profile) then
                return nil
            end
            if not ownSession(profile) then
                leaseLost = true
                return nil
            end

            local existing = findOperation(profile, operationId)
            if existing then
                duplicateOutcome = existing.outcome
                return profile
            end

            for _, stack in outcome.stacks do
                local species = profile.collection[stack.speciesId]
                if typeof(species) ~= "table" or typeof(species.base) ~= "number" then
                    return nil
                end
                species.base += stack.count
            end

            profile.pendingChestGrants = (profile.pendingChestGrants or 0) + outcome.chestCount
            profile.revision += 1
            profile.session.expiresAt = now + Config.ProfileLeaseSeconds
            profile.lastCheckpoint = {
                committedAt = now,
                lastSettledRunId = runId,
            }
            table.insert(profile.recentOperations, {
                id = operationId,
                kind = "run",
                outcome = outcome,
            })
            while #profile.recentOperations > Config.ProfileMaxRecentOperations do
                table.remove(profile.recentOperations, 1)
            end
            return profile
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
    if #summaryParts == 0 then
        table.insert(summaryParts, "no dinosaur copies")
    end
    if committedOutcome.chestCount > 0 then
        table.insert(summaryParts, string.format("%d chest(s)", committedOutcome.chestCount))
    end
    player:SetAttribute("LastRewardText", table.concat(summaryParts, " | "))
    return true, committedOutcome, if duplicateOutcome then "duplicate" else "committed"
end

function ProfileRepository.renew(player: Player): boolean
    if not profiles[player] or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false
    end
    local leaseLost = false
    local now = os.time()
    local ok, updated = retry("lease renew", function()
        return store:UpdateAsync(keyFor(player), function(profile)
            if not isValidProfile(profile) or not ownSession(profile) then
                leaseLost = true
                return nil
            end
            profile.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profile
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
        return store:UpdateAsync(keyFor(player), function(profile)
            if not isValidProfile(profile) or not ownSession(profile) then
                return nil
            end
            profile.session = nil
            return profile
        end)
    end)
end

function ProfileRepository.runLeaseSelfTest(): (boolean, string)
    if not Config.PersistenceLeaseSelfTest then
        return true, "disabled"
    end

    -- This probe never uses a player profile key. It exercises the same DataStore
    -- lease rule with two synthetic server identities, then deletes the probe.
    local probeKey = "__lease_probe:" .. HttpService:GenerateGUID(false)
    local probeLeaseA = "probe-a:" .. HttpService:GenerateGUID(false)
    local probeLeaseB = "probe-b:" .. HttpService:GenerateGUID(false)
    local now = os.time()

    local function cleanup()
        pcall(function()
            store:RemoveAsync(probeKey)
        end)
    end

    local function fail(reason: string): (boolean, string)
        cleanup()
        return false, reason
    end

    local acquiredA = false
    local okA = select(1, retry("lease self-test acquire A", function()
        return store:UpdateAsync(probeKey, function(current)
            if current ~= nil then return nil end
            acquiredA = true
            return {
                kind = "lease_probe",
                leaseId = probeLeaseA,
                expiresAt = now + 30,
                value = 0,
            }
        end)
    end))
    if not okA or not acquiredA then
        return fail("acquire-a")
    end

    local blockedB = false
    local okBlocked = select(1, retry("lease self-test block B", function()
        return store:UpdateAsync(probeKey, function(current)
            if typeof(current) ~= "table" then return nil end
            if current.leaseId ~= probeLeaseB
                and typeof(current.expiresAt) == "number"
                and current.expiresAt > now then
                blockedB = true
                return nil
            end
            return current
        end)
    end))
    if not okBlocked or not blockedB then
        return fail("live-lease-not-blocked")
    end

    local expiredA = false
    local okExpire = select(1, retry("lease self-test expire A", function()
        return store:UpdateAsync(probeKey, function(current)
            if typeof(current) ~= "table" or current.leaseId ~= probeLeaseA then
                return nil
            end
            current.expiresAt = now - 1
            expiredA = true
            return current
        end)
    end))
    if not okExpire or not expiredA then
        return fail("expire-a")
    end

    local acquiredB = false
    local okB = select(1, retry("lease self-test acquire B", function()
        return store:UpdateAsync(probeKey, function(current)
            if typeof(current) ~= "table" then return nil end
            local expiresAt = current.expiresAt
            if typeof(expiresAt) ~= "number" or expiresAt > now then
                return nil
            end
            current.leaseId = probeLeaseB
            current.expiresAt = now + 30
            acquiredB = true
            return current
        end)
    end))
    if not okB or not acquiredB then
        return fail("expired-lease-takeover")
    end

    local staleRejected = false
    local okStale = select(1, retry("lease self-test reject stale A", function()
        return store:UpdateAsync(probeKey, function(current)
            if typeof(current) ~= "table" then return nil end
            if current.leaseId ~= probeLeaseA then
                staleRejected = true
                return nil
            end
            current.value = 999
            return current
        end)
    end))
    if not okStale or not staleRejected then
        return fail("stale-write-not-rejected")
    end

    local freshCommitted = false
    local okFresh = select(1, retry("lease self-test write B", function()
        return store:UpdateAsync(probeKey, function(current)
            if typeof(current) ~= "table" or current.leaseId ~= probeLeaseB then
                return nil
            end
            current.value = (current.value or 0) + 1
            freshCommitted = true
            return current
        end)
    end))
    if not okFresh or not freshCommitted then
        return fail("current-owner-write-failed")
    end

    local readOk, final = retry("lease self-test verify", function()
        return store:GetAsync(probeKey)
    end)
    if not readOk or typeof(final) ~= "table"
        or final.leaseId ~= probeLeaseB or final.value ~= 1 then
        return fail("final-state-mismatch")
    end

    cleanup()
    return true, "pass"
end

function ProfileRepository.start()
    if renewing then return end
    renewing = true
    task.spawn(function()
        while renewing do
            task.wait(Config.ProfileRenewSeconds)
            for player in profiles do
                if player.Parent then
                    task.spawn(ProfileRepository.renew, player)
                end
            end
        end
    end)
end

return ProfileRepository
