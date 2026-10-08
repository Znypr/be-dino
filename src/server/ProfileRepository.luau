--!strict
local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local RewardMath = require(script.Parent.RewardMath)
local ProgressionRules = require(ReplicatedStorage.Shared.ProgressionRules)
local EggTraits = require(ReplicatedStorage.Shared.EggTraits)
local EggGenetics = require(ReplicatedStorage.Shared.EggGenetics)
local ProgressionConfig = require(ReplicatedStorage.Shared.ProgressionConfig)

local ProfileRepository = {}

local RunService = game:GetService("RunService")
local localPreview = RunService:IsStudio() and game.GameId == 0 and Config.StudioLocalProfilesEnabled
local store: any
if localPreview then
    -- Unpublished F5 sessions have no DataStore. Deep copies mirror transaction boundaries.
    local memory = {}
    store = {UpdateAsync = function(_, key, transform)
        local current = if memory[key] then HttpService:JSONDecode(HttpService:JSONEncode(memory[key])) else nil
        local updated = transform(current)
        if updated == nil then return nil end
        memory[key] = HttpService:JSONDecode(HttpService:JSONEncode(updated))
        return updated
    end}
else
    store = DataStoreService:GetDataStore(Config.ProfileDataStoreName)
end
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

local function upgradeCollection(profile: any)
    if typeof(profile) ~= "table" or profile.schemaVersion ~= Config.ProfileSchemaVersion
        or typeof(profile.collection) ~= "table" then return end
    for _, id in Config.SpeciesOrder do
        local entry = profile.collection[id]
        -- Add only new catalog fields. Existing malformed balances remain invalid.
        if entry == nil and table.find({"raptor", "stegosaurus", "ankylosaurus"}, id) then
            entry = {base = 0, gold = 0, diamond = 0}
            profile.collection[id] = entry
        end
        if typeof(entry) == "table" and entry.diamond == nil then entry.diamond = 0 end
        if typeof(entry) == "table" and entry.events == nil then entry.events = {} end
        if typeof(entry) == "table" and entry.variants == nil then entry.variants = {} end
    end
    if profile.metrics == nil then profile.metrics = {playSeconds = 0, rarest = 0, robux = 0} end
    if profile.purchaseReceipts == nil then profile.purchaseReceipts = {} end
end

local function defaultProfile()
    local collection = {}
    for _, id in Config.SpeciesOrder do collection[id] = {base = if id == "compy" then 1 else 0, gold = 0, diamond = 0} end
    return {
        schemaVersion = Config.ProfileSchemaVersion,
        revision = 0,
        session = nil,
        equippedSpeciesId = "compy",
        collection = collection,
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
    upgradeCollection(profile)
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
    local function validEgg(egg, active: boolean?)
        if not ProgressionRules.validEgg(egg) then return false end
        if active and (typeof(egg.eggId) ~= "string" or #egg.eggId < 1 or #egg.eggId > 80
            or typeof(egg.readyAt) ~= "number" or egg.readyAt ~= egg.readyAt
            or egg.readyAt < 0 or egg.readyAt % 1 ~= 0 or egg.readyAt == math.huge) then return false end
        if egg.big ~= nil and typeof(egg.big) ~= "boolean" then return false end
        if egg.shiny ~= nil and typeof(egg.shiny) ~= "boolean" then return false end
        local reward = egg.reward
        return reward == nil or (typeof(reward) == "table" and knownSpecies(reward.speciesId)
            and typeof(reward.count) == "number" and reward.count >= 1 and reward.count <= 3 and reward.count % 1 == 0)
    end
    for _,egg in profile.eggs do if not validEgg(egg,true) then return false end end
    if profile.pendingEggEvents~=nil then
        if typeof(profile.pendingEggEvents)~="table" or #profile.pendingEggEvents~=profile.pendingChestGrants then return false end
        for _,metadata in profile.pendingEggEvents do if not validEgg(metadata) then return false end end
    end
    for _, speciesId in Config.SpeciesOrder do
        local entry = profile.collection[speciesId]
        if typeof(entry) ~= "table"
            or typeof(entry.base) ~= "number" or entry.base < 0 or entry.base % 1 ~= 0
            or typeof(entry.gold) ~= "number" or entry.gold < 0 or entry.gold % 1 ~= 0
            or typeof(entry.diamond) ~= "number" or entry.diamond < 0 or entry.diamond % 1 ~= 0
            or entry.base > 2000000000 or entry.gold > 2000000000 or entry.diamond > 2000000000 then
            return false
        end
        if not ProgressionRules.validEvents(entry.events) then return false end
        if not EggTraits.valid(entry.variants) then return false end
        for _,variant in entry.variants do
            if variant.mutationId ~= "" and not ProgressionRules.knownEventMutation(variant.mutationId) then return false end
        end
    end
    if typeof(profile.metrics) ~= "table" or typeof(profile.purchaseReceipts) ~= "table" then return false end
    for id,processed in profile.purchaseReceipts do
        if typeof(id) ~= "string" or #id < 1 or #id > 120 or processed ~= true then return false end
    end
    if typeof(profile.session) == "table" and profile.session.metricsAt ~= nil then
        local at=profile.session.metricsAt
        if typeof(at) ~= "number" or at ~= at or at < 0 or at % 1 ~= 0 or at == math.huge then return false end
    end
    for _,key in {"playSeconds", "rarest", "robux"} do
        local n = profile.metrics[key]
        if typeof(n) ~= "number" or n ~= n or n < 0 or n % 1 ~= 0 or n > 2000000000 then return false end
    end
    if profile.metrics.rarest > 3 then return false end
    return ProgressionRules.valid(profile.progression)
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
    local progress=ProgressionRules.upgrade(profile)
    player:SetAttribute("StudioTestWallet", localPreview and Config.StudioTestWalletEnabled)
    player:SetAttribute("CollectionJson", HttpService:JSONEncode(profile.collection))
    player:SetAttribute("Crystals",progress.crystals)
    player:SetAttribute("ProgressionJson",HttpService:JSONEncode(progress))
    player:SetAttribute("EquippedAura",progress.equippedAura)
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
    local traits = EggTraits.selected(collection[profile.equippedSpeciesId])
    player:SetAttribute("EquippedBig", traits ~= nil and traits.big)
    player:SetAttribute("EquippedShiny", traits ~= nil and traits.shiny)
    player:SetAttribute("EquippedGenesJson",HttpService:JSONEncode(if traits then traits.genes else nil))
    player:SetAttribute("EquippedCondition",if traits and traits.genes then traits.genes.conditionId else "normal")
    player:SetAttribute("AccountLevel",ProgressionRules.level(progress))
    player:SetAttribute("PlaySeconds", profile.metrics.playSeconds)
    player:SetAttribute("RarestCaught", profile.metrics.rarest)
    player:SetAttribute("RobuxSpent", profile.metrics.robux)
    local eventMutation=if traits then ProgressionRules.item(ProgressionConfig.EventMutations,traits.mutationId) else ProgressionRules.eventMutation(collection[profile.equippedSpeciesId])
    player:SetAttribute("EquippedEventMutation",if eventMutation then eventMutation.id else "")
    player:SetAttribute("ActiveChestCount", #profile.eggs)
    local chestSummary = {}
    for index, chest in profile.eggs do
        if index > Config.ChestQueueCapacity then break end
        table.insert(chestSummary, {
            id = chest.eggId,
            readyAt = chest.readyAt,
            eventId=chest.eventId or "clear",
            mutationId=chest.mutationId or "",
            rarity=if chest.reward then Config.SpeciesRarities[chest.reward.speciesId] else 1,
            shiny=chest.shiny or false,
            big=chest.big or false,
            genes=chest.genes,
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

local function enqueueChestIds(profile: any, chestIds: {string}, now: number, events)
    local nextReadyAt = if Config.ChestTimerSeconds == 0 then now else lastChestReadyAt(profile, now)
    if not profile.pendingEggEvents then
        profile.pendingEggEvents={}
        for _=1,profile.pendingChestGrants do table.insert(profile.pendingEggEvents,{eventId="clear",mutationId=""}) end
    end
    for i, chestId in chestIds do
        local metadata=if events then events[i] else nil
        metadata=metadata or {eventId="clear",mutationId=""}
        if #profile.eggs < Config.ChestQueueCapacity then
            nextReadyAt += Config.ChestTimerSeconds
            table.insert(profile.eggs, {
                eggId = chestId,
                kind = "alpha_chest",
                readyAt = nextReadyAt,
                eventId=metadata.eventId,
                mutationId=metadata.mutationId,
                reward=metadata.reward,
                shiny=metadata.shiny,
                big=metadata.big,
                genes=metadata.genes,
            })
        else
            profile.pendingChestGrants += 1
            table.insert(profile.pendingEggEvents,metadata)
        end
    end
end

function ProfileRepository.isLoaded(player: Player): boolean
    return profiles[player] ~= nil and player:GetAttribute("ProfileState") == "Loaded"
end

-- Catch-time assignment is immutable; upgraded odds only affect future eggs.
function ProfileRepository.prepareEgg(player: Player,tag)
    local rng=Random.new()
    local p=ProfileRepository.progression(player)
    local result=table.clone(tag)
    result.genes=EggGenetics.roll(if p then p.conditionLevel else 0,rng)
    local traits=EggTraits.roll(tag.eventId or "clear",rng:NextNumber(),rng:NextNumber())
    result.shiny,result.big=traits.shiny,traits.big
    return result
end

function ProfileRepository.load(player: Player): boolean
    if profiles[player] then return true end
    player:SetAttribute("ProfileMode", if localPreview then "Studio preview (not saved)" else "Persistent")
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

            local progress = ProgressionRules.upgrade(profileValue)
            if localPreview and Config.StudioTestWalletEnabled then progress.crystals = Config.StudioTestCrystals end
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
                metricsAt = now,
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

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    player:SetAttribute("ProfileState", "Loaded")
    syncAttributes(player, profiles[player])
    return true
end

function ProfileRepository.commitRunSettlement(player: Player, runId: string, catchScore: number, eggEvents)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, nil, "profile_not_loaded"
    end
    if typeof(runId) ~= "string" or #runId < 1 or #runId > 80 then
        return false, nil, "invalid_run_id"
    end

    local outcome = RewardMath.computeRunReward(catchScore)
    local rng=Random.new()
    local box=0
    if catchScore>0 then
        local total=0 for _,row in ProgressionConfig.CrystalBoxes do total+=row.weight end
        local roll=rng:NextNumber()*total
        for _,row in ProgressionConfig.CrystalBoxes do roll-=row.weight if roll<0 then box=row.amount break end end
        if box==0 then box=ProgressionConfig.CrystalBoxes[#ProgressionConfig.CrystalBoxes].amount end
    end
    outcome.crystalBox=box
    outcome.crystals=math.min(ProgressionConfig.RunCrystalCap,catchScore*ProgressionConfig.RunCrystalPerCatch)+box
    if eggEvents~=nil then
        if typeof(eggEvents)~="table" or #eggEvents>outcome.chestCount then return false,nil,"invalid_egg_events" end
        for _,metadata in eggEvents do if not ProgressionRules.validEgg(metadata) then return false,nil,"invalid_egg_events" end end
    end
    local operationId = "run:" .. runId
    -- Commit all random draws before UpdateAsync. Catch-time event tags stay authoritative.
    local prepared = {}
    for i = 1, outcome.chestCount do
        local tag = (eggEvents and eggEvents[i]) or {eventId = "clear", mutationId = ""}
        local traits = if tag.genes then tag else ProfileRepository.prepareEgg(player,tag)
        table.insert(prepared, {
            eventId = tag.eventId, mutationId = tag.mutationId,
            reward = RewardMath.computeChestReward(rng, outcome.chestCount),
            shiny = traits.shiny, big = traits.big, ordinal = i,
            genes=traits.genes,
        })
    end
    table.sort(prepared, function(a,b)
        local ar, br = Config.SpeciesRarities[a.reward.speciesId], Config.SpeciesRarities[b.reward.speciesId]
        return if ar == br then a.ordinal < b.ordinal else ar < br
    end)
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
                profileValue.metrics.rarest = math.max(profileValue.metrics.rarest, Config.SpeciesRarities[stack.speciesId])
            end

            enqueueChestIds(profileValue, chestIds, now, prepared)
            local progress=ProgressionRules.upgrade(profileValue)
            if progress.crystals+outcome.crystals>ProgressionConfig.MaxCrystals then return nil end
            progress.crystals+=outcome.crystals
            progress.accountXP=math.min(2000000000,progress.accountXP+catchScore)
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

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
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
    player:SetAttribute("LastRunCrystals",committedOutcome.crystals or 0)
    player:SetAttribute("LastRunCrystalBox",committedOutcome.crystalBox or 0)
    player:SetAttribute("LastSettledRunId", runId)
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
    if typeof(cachedEntry) ~= "table" or (cachedEntry.base + cachedEntry.gold + cachedEntry.diamond <= 0 and not ProgressionRules.eventMutation(cachedEntry) and not EggTraits.selected(cachedEntry)) then
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
            if typeof(entry) ~= "table" or (entry.base + entry.gold + entry.diamond <= 0 and not ProgressionRules.eventMutation(entry) and not EggTraits.selected(entry)) then
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

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
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

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
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

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
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
    local outcome = if cachedChest.reward then table.clone(cachedChest.reward) else RewardMath.computeChestReward(Random.new())
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
            if chest.reward and index ~= 1 then missing = true return nil end

            table.remove(profileValue.eggs, index)
            local species = profileValue.collection[outcome.speciesId]
            if typeof(species) ~= "table" then return nil end
            local mutationId=chest.mutationId or ""
            outcome.genes=chest.genes
            outcome.failed=chest.genes~=nil and not chest.genes.hatchSuccess
            if outcome.failed then
                outcome.count=0
            elseif chest.big or chest.shiny or chest.genes then
                local key = EggTraits.key(mutationId, chest.shiny == true, chest.big == true,chest.genes)
                local variant = species.variants[key] or {mutationId=mutationId, shiny=chest.shiny == true, big=chest.big == true, count=0,genes=chest.genes}
                variant.count += outcome.count
                species.variants[key] = variant
            elseif mutationId~="" then
                if not ProgressionRules.knownEventMutation(mutationId) then return nil end
                species.events[mutationId]=(species.events[mutationId] or 0)+outcome.count
            else species.base += outcome.count end
            outcome.eventMutationId=mutationId
            outcome.eventId=chest.eventId or "clear"
            outcome.big=chest.big == true
            outcome.shiny=chest.shiny == true
            if not outcome.failed then profileValue.metrics.rarest = math.max(profileValue.metrics.rarest, Config.SpeciesRarities[outcome.speciesId]) end

            if profileValue.pendingChestGrants > 0 then
                profileValue.pendingChestGrants -= 1
                local readyAt = if Config.ChestTimerSeconds == 0 then now else lastChestReadyAt(profileValue, now) + Config.ChestTimerSeconds
                local metadata=if profileValue.pendingEggEvents then table.remove(profileValue.pendingEggEvents,1) else nil
                table.insert(profileValue.eggs, {
                    eggId = refillChestId,
                    kind = "alpha_chest",
                    readyAt = readyAt,
                    eventId=if metadata then metadata.eventId else "clear",
                    mutationId=if metadata then metadata.mutationId else "",
                    reward=if metadata then metadata.reward else nil,
                    shiny=if metadata then metadata.shiny else nil,
                    big=if metadata then metadata.big else nil,
                    genes=if metadata then metadata.genes else nil,
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

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
    local committedOutcome = duplicateOutcome or outcome
    player:SetAttribute("LastChestRewardText", string.format(
        "%dx %s", committedOutcome.count, committedOutcome.speciesId
    ))
    player:SetAttribute("LastChestEventMutation",committedOutcome.eventMutationId or "")
    player:SetAttribute("LastChestBig",committedOutcome.big == true)
    player:SetAttribute("LastChestShiny",committedOutcome.shiny == true)
    player:SetAttribute("LastChestGenesJson",HttpService:JSONEncode(committedOutcome.genes))
    player:SetAttribute("LastChestFailed",committedOutcome.failed==true)
    player:SetAttribute("LastClaimedChestId", chestId)
    return true, committedOutcome, if duplicateOutcome then "duplicate" else "claimed"
end

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
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, nil, "lease_lost"
        end
        if tokenConflict then return false, nil, "token_conflict" end
        if insufficient then return false, nil, "insufficient_copies" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
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

    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
    return true, "set_" .. tostring(baseCount)
end

function ProfileRepository.progression(player: Player)
    if not ProfileRepository.isLoaded(player) then return nil end
    return ProgressionRules.upgrade(profiles[player])
end
function ProfileRepository.progressionAction(player: Player, action: string, id: string, token: string, replace: boolean?, amount: number?)
    if not ProfileRepository.isLoaded(player) then return false,"profile_not_loaded" end
    if typeof(token)~="string" or #token<1 or #token>80 then return false,"invalid_token" end
    if (action=="buyEgg" or action=="upgradeCondition") and next(Config.DeveloperProducts)~=nil
        and (not Config.PaidRandomItemsEnabled or player:GetAttribute("PaidRandomEligible")~=true) then return false,"random_items_unavailable" end
    local eggId=nil
    local egg=nil
    local purchaseConditionLevel=ProfileRepository.progression(player).conditionLevel
    if action=="buyEgg" then
        if id~="random" then return false,"unknown_item" end
        eggId=HttpService:GenerateGUID(false)
        egg=ProfileRepository.prepareEgg(player,{eventId="clear",mutationId=""})
        egg.reward=RewardMath.computeChestReward(Random.new(),1)
    end
    local operationId="progression:"..token
    local now=os.time()
    local denied="save_failed"
    local duplicate=false
    local outcome=nil
    local leaseLost=false
    local ok,updated=retry("progression",function()
        return store:UpdateAsync(keyFor(player),function(profile)
            if not isValidProfile(profile) then denied="invalid_profile" return nil end
            if not ownSession(profile) then leaseLost=true return nil end
            local existing=findOperation(profile,operationId)
            if existing then
                if existing.outcome.action~=action or existing.outcome.item~=id then denied="token_conflict" return nil end
                outcome=existing.outcome duplicate=true return profile
            end
            local progress = ProgressionRules.upgrade(profile)
            if localPreview and Config.StudioTestWalletEnabled then progress.crystals = Config.StudioTestCrystals end
            local applied,status
            if action=="buyEgg" then
                if availableChestCapacity(profile)<1 then denied="queue_full" return nil end
                if progress.crystals<ProgressionConfig.RandomEggPrice then denied="insufficient_crystals" return nil end
                -- Do not buy against stale odds if a concurrent condition upgrade committed.
                if progress.conditionLevel~=purchaseConditionLevel then denied="upgrade_changed" return nil end
                progress.crystals-=ProgressionConfig.RandomEggPrice
                enqueueChestIds(profile,{eggId},now,{egg})
                applied,status=true,"egg_purchased"
            else applied,status=ProgressionRules.apply(profile,action,id,now,replace,amount) end
            if localPreview and Config.StudioTestWalletEnabled then progress.crystals = Config.StudioTestCrystals end
            if not applied then denied=status return nil end
            outcome={action=action,item=id,status=status}
            profile.revision+=1
            profile.session.expiresAt=now+Config.ProfileLeaseSeconds
            table.insert(profile.recentOperations,{id=operationId,kind="progression",outcome=outcome})
            trimOperations(profile)
            return profile
        end)
    end)
    if not ok then player:SetAttribute("ProfileState","SaveFailed") return false,"save_failed" end
    if leaseLost then player:SetAttribute("ProfileState","LeaseLost") return false,"lease_lost" end
    if not updated then return false,denied end
    if not player.Parent then return true,if duplicate then "duplicate" else outcome.status end
    if not profiles[player] or updated.revision>=profiles[player].revision then profiles[player]=updated end
    if player.Parent then syncAttributes(player,profiles[player]) end
    return true,if duplicate then "duplicate" else outcome.status
end

-- Only called by the server's MarketplaceService callback. Receipts are never trimmed.
function ProfileRepository.purchase(player: Player, receipt)
    if not ProfileRepository.isLoaded(player) then return false end
    local crystals = Config.DeveloperProducts[receipt.ProductId]
    if typeof(crystals) ~= "number" or crystals < 1 or crystals % 1 ~= 0 then return false end
    if receipt.PlayerId ~= player.UserId or typeof(receipt.PurchaseId) ~= "string" or #receipt.PurchaseId < 1 or #receipt.PurchaseId > 120
        or typeof(receipt.CurrencySpent) ~= "number" or receipt.CurrencySpent ~= receipt.CurrencySpent
        or receipt.CurrencySpent < 0 or receipt.CurrencySpent % 1 ~= 0 or receipt.CurrencySpent > 2000000000 then return false end
    local ok, updated = retry("purchase", function()
        return store:UpdateAsync(keyFor(player),function(profile)
            if not isValidProfile(profile) or not ownSession(profile) then return nil end
            if profile.purchaseReceipts[receipt.PurchaseId] then return profile end
            local count=0 for _ in profile.purchaseReceipts do count+=1 end
            if count>=10000 then return nil end -- Fail closed before the profile size limit.
            local progress=ProgressionRules.upgrade(profile)
            local maxCrystals=require(ReplicatedStorage.Shared.ProgressionConfig).MaxCrystals
            if progress.crystals+crystals>maxCrystals or profile.metrics.robux+receipt.CurrencySpent>2000000000 then return nil end
            progress.crystals+=crystals
            profile.metrics.robux+=receipt.CurrencySpent
            profile.purchaseReceipts[receipt.PurchaseId]=true
            profile.revision+=1
            profile.session.expiresAt=os.time()+Config.ProfileLeaseSeconds
            return profile
        end)
    end)
    if not ok or not updated then return false end
    if not profiles[player] then return true end
    if updated.revision>=profiles[player].revision then profiles[player]=updated end
    syncAttributes(player,profiles[player])
    return true
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
            local since = profileValue.session.metricsAt or now
            profileValue.metrics.playSeconds = math.min(2000000000, profileValue.metrics.playSeconds + math.max(0, now - since))
            profileValue.session.metricsAt = now
            profileValue.revision += 1
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        player:SetAttribute("ProfileState", if leaseLost then "LeaseLost" else "SaveFailed")
        return false
    end
    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    syncAttributes(player, profiles[player])
    return true
end

function ProfileRepository.release(player: Player)
    local cached = profiles[player]
    profiles[player] = nil
    if not cached then return end

    local ok, updated = retry("lease release", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) or not ownSession(profileValue) then return nil end
            profileValue.metrics.playSeconds = math.min(2000000000, profileValue.metrics.playSeconds + math.max(0, os.time() - (profileValue.session.metricsAt or os.time())))
            profileValue.session = nil
            profileValue.revision += 1
            return profileValue
        end)
    end)
    return if ok and updated then updated.metrics else nil
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
