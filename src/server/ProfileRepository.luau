--!strict
local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local RewardMath = require(script.Parent.RewardMath)
local ProgressionRules = require(ReplicatedStorage.Shared.ProgressionRules)
local EggTraits = require(ReplicatedStorage.Shared.EggTraits)
local EggGenetics = require(ReplicatedStorage.Shared.EggGenetics)
local NestQueue = require(ReplicatedStorage.Shared.NestQueue)
local ProgressionConfig = require(ReplicatedStorage.Shared.ProgressionConfig)

local ProfileRepository = {}
local DinosaurIdentity = require(script.Parent.DinosaurIdentity)
local IdentityFusion = require(script.Parent.IdentityFusion)
local FusionOdds = require(script.Parent.FusionOdds)
local SettingsModel = require(ReplicatedStorage.Shared.SettingsModel)

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
-- Identity gating helpers. Unpublished memory-only Studio keeps the BD-060 behavior.
-- Persistent profiles get the sidecar only when Config.IdentityPersistentEnabled is
-- true (Milestone 1 private playtest with a fresh DataStore; default false).
local function identityPersistent(): boolean
    return not localPreview and Config.IdentityPersistentEnabled == true
end
-- True when the sidecar exists, is enabled for this server and is not suspended.
local function identityAvailable(state: any): boolean
    return (localPreview or identityPersistent()) and type(state) == "table" and state.suspendedReason == nil
end
-- Fail closed for identity features only: keep the last good sidecar untouched (never
-- delete identities, cosmetics or fused results) and mark it suspended. A later write
-- whose grouped collection reconciles again clears the mark automatically.
local function suspendIdentity(before: any, reason: string)
    if type(before) == "table" then before.suspendedReason = reason end
    return before
end
local function persistentIdentityTransform(key: string, current: any, transform)
    local before = if type(current) == "table" then DinosaurIdentity.copy(current.dinosaurIdentity) else nil
    local updated = transform(current)
    if updated == nil then return nil end
    local identity, reason = DinosaurIdentity.reconcile(updated.collection, updated.dinosaurIdentity, key)
    if identity then
        identity.suspendedReason = nil
        updated.dinosaurIdentity = identity
    else
        -- Legacy/over-capacity/protected profiles keep loading and playing.
        updated.dinosaurIdentity = suspendIdentity(before, reason :: string)
    end
    -- Whole-profile byte preflight (estimate matched Roblox JSONEncode in Studio).
    local limit = Config.IdentityProfileHardLimitBytes
    if IdentityFusion.encodedSize(updated) > limit then
        if identity then updated.dinosaurIdentity = suspendIdentity(DinosaurIdentity.copy(before), "storage_limit") end
        if IdentityFusion.encodedSize(updated) > limit then return nil end
    end
    return updated
end
-- Development integration (unpublished memory-only profiles): unchanged BD-060 path.
if localPreview then
    local backingStore = store
    store = {UpdateAsync = function(_, key, transform)
        return backingStore:UpdateAsync(key, function(current)
            local updated = transform(current)
            if updated == nil then return nil end
            local identity, reason = DinosaurIdentity.reconcile(updated.collection, updated.dinosaurIdentity, key)
            if not identity then error(reason) end
            updated.dinosaurIdentity = identity
            return updated
        end)
    end}
elseif identityPersistent() then
    -- Persistent identity (Milestone 1 playtest): reconcile in the SAME UpdateAsync
    -- transform as every grouped change, so sidecar and collection commit together.
    local backingStore = store
    store = {UpdateAsync = function(_, key, transform)
        return backingStore:UpdateAsync(key, function(current)
            return persistentIdentityTransform(key, current, transform)
        end)
    end}
end
-- BD-358: every store request is counted (sliding 60 s window) so routine writes can respect the server's DataStore budget of
-- 60 + 10 x players requests per minute. Counting is the only thing this wrapper does; behaviour is unchanged.
local PlayersService = game:GetService("Players")
local requestLog: {[number]: number} = {}
local requestHead, requestTail = 1, 0
local function requestsInWindow(at: number): number
    while requestHead <= requestTail and requestLog[requestHead] <= at - 60 do
        requestLog[requestHead] = nil
        requestHead += 1
    end
    return requestTail - requestHead + 1
end
do
    local countedStore = store
    store = {UpdateAsync = function(_, key, transform)
        requestTail += 1
        requestLog[requestTail] = os.clock()
        return countedStore:UpdateAsync(key, transform)
    end}
end
local leaseId = HttpService:GenerateGUID(false)
local profiles: {[Player]: any} = {}
-- BD-044 hatch pages: one claim transaction commits up to Config.HatchPageSize queued run
-- eggs; committed (already credited) results wait here so the client still reveals them
-- one at a time (~1 s each) without a DataStore request per egg. Memory only: a rejoin
-- mid-page loses just the animation, never a credit (see docs/50).
local revealBuffer: {[Player]: {any}} = {}
local renewing = false
-- BD-354: userIds whose lease release is still in flight. A rejoin of the same user on this server shares our leaseId, so a late
-- release would clear the NEW session; load waits for it instead.
local releasing: {[number]: number} = {}

-- BD-358: one token bucket per player for ROUTINE writes (anything a client remote can trigger repeatedly). PRIORITY writes (run
-- settlement, lease renew/release, load, purchases) never call admit, so a spamming client cannot starve them. A routine write
-- that is not admitted is answered "rate_limited" without touching the store; preference writes are coalesced instead.
local writeBuckets: {[Player]: {tokens: number, at: number}} = setmetatable({}, {__mode = "k"}) :: any
local coalesced: {[Player]: {[string]: {value: any}}} = setmetatable({}, {__mode = "k"}) :: any
local flushing: {[Player]: boolean} = setmetatable({}, {__mode = "k"}) :: any
local coalesceWriters: {[string]: (Player, any) -> any} = {}
-- A preference write that is still retrying when a NEWER one for the same preference is issued must not commit afterwards (stale
-- overwrite). Each write takes a number; a transform of an out-of-date write cancels itself and the write counts as superseded.
local prefSeq: {[Player]: {[string]: number}} = setmetatable({}, {__mode = "k"}) :: any
local function takePrefSeq(player: Player, kind: string): number
    local seqs = prefSeq[player]
    if not seqs then seqs = {}; prefSeq[player] = seqs end
    seqs[kind] = (seqs[kind] or 0) + 1
    return seqs[kind]
end
local function prefSuperseded(player: Player, kind: string, seq: number): boolean
    local seqs = prefSeq[player]
    return seqs ~= nil and (seqs[kind] or 0) ~= seq
end
local writeStats = {admitted = 0, rejected = 0, coalesced = 0, flushed = 0}
local function admit(player: Player): boolean
    if Config.WriteBudgetEnabled == false then return true end
    local at = os.clock()
    local bucket = writeBuckets[player]
    if not bucket then
        bucket = {tokens = Config.WriteBurst, at = at}
        writeBuckets[player] = bucket
    end
    bucket.tokens = math.min(Config.WriteBurst, bucket.tokens + (at - bucket.at) * Config.WriteRefillPerSecond)
    bucket.at = at
    local players = if PlayersService then #PlayersService:GetPlayers() else 1 -- offline mocks may not model Players
    local share = (60 + 10 * math.max(1, players)) * (1 - Config.WriteBudgetReserve)
    if bucket.tokens < 1 or requestsInWindow(at) >= share then
        writeStats.rejected += 1
        return false
    end
    bucket.tokens -= 1
    writeStats.admitted += 1
    return true
end

-- Latest value wins: a preference write that is over budget is remembered and written when a token is free (or merged into the
-- lease release), so a slider dragged quickly costs one write, not one per tick.
local function coalesce(player: Player, kind: string, value: any): (boolean, string)
    local pending = coalesced[player]
    if not pending then pending = {}; coalesced[player] = pending end
    pending[kind] = {value = value}
    writeStats.coalesced += 1
    if not flushing[player] then
        flushing[player] = true
        task.spawn(function()
            while profiles[player] and coalesced[player] and next(coalesced[player]) ~= nil do
                task.wait(1.1)
                local waiting = coalesced[player]
                if waiting and profiles[player] and player:GetAttribute("ProfileState") == "Loaded" then
                    for waitingKind, entry in waiting do
                        if admit(player) then
                            waiting[waitingKind] = nil
                            writeStats.flushed += 1
                            local saved, status = coalesceWriters[waitingKind](player, entry.value)
                            -- A failed save is not a lost value: keep it for the next token unless a newer value arrived meanwhile.
                            local still = coalesced[player]
                            if not saved and status == "save_failed" and still and still[waitingKind] == nil then
                                still[waitingKind] = entry
                            end
                        end
                    end
                end
            end
            flushing[player] = nil
        end)
    end
    return true, "queued"
end

-- BD-354: adopt a transaction result only while the player is still loaded. A player who left (release already ran) must not get
-- a profile entry back: it would leak the Player instance plus up to megabytes of profile for the rest of the server's life.
local function adopt(player: Player, updated: any)
    local live = profiles[player]
    if live ~= nil and updated.revision >= live.revision then profiles[player] = updated end
end

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

-- BD-044: metrics.rarest and revealSkip were saved on the old three-tier species scale
-- (1 Common, 2 Rare, 3 Legendary) until profile.rarityScale exists. Migrate once, additively, and
-- never overclaim: old Rare covered today's Uncommon/Rare, old Legendary today's Epic/Legendary, so
-- rarest takes the lowest new tier of its old band, raised to the best owned species inside that band.
local LEGACY_RAREST_BAND = {[0] = {0, 0}, [1] = {1, 2}, [2] = {2, 3}, [3] = {4, 5}}
local LEGACY_SKIP_TIERS = {{1}, {2, 3}, {4, 5}}
local function ownsAny(entry: any): boolean
    if typeof(entry) ~= "table" then return false end
    for _, key in {"base", "gold", "diamond"} do
        if typeof(entry[key]) == "number" and entry[key] > 0 then return true end
    end
    return (typeof(entry.variants) == "table" and next(entry.variants) ~= nil)
        or (typeof(entry.events) == "table" and next(entry.events) ~= nil)
end
local function upgradeRarityScale(profile: any)
    if profile.rarityScale ~= nil then return end
    local band = LEGACY_RAREST_BAND[profile.metrics.rarest]
    if band == nil then return end -- malformed legacy value: validation rejects it unchanged
    local skip = nil
    if profile.revealSkip ~= nil then
        if typeof(profile.revealSkip) ~= "table" then return end
        local set = {}
        for _, legacy in profile.revealSkip do
            local tiers = LEGACY_SKIP_TIERS[legacy]
            if tiers == nil then return end
            for _, tier in tiers do set[tier] = true end
        end
        skip = {}
        for tier = 1, Config.SpeciesRarityScale do if set[tier] then table.insert(skip, tier) end end
    end
    local rarest = band[1]
    if rarest > 0 then
        for id, entry in profile.collection do
            local tier = Config.SpeciesRarities[id]
            if tier and tier <= band[2] and ownsAny(entry) then rarest = math.max(rarest, tier) end
        end
    end
    profile.metrics.rarest = rarest
    profile.revealSkip = skip
    profile.rarityScale = Config.SpeciesRarityScale
end

local function upgradeCollection(profile: any)
    if typeof(profile) ~= "table" or profile.schemaVersion ~= Config.ProfileSchemaVersion
        or typeof(profile.collection) ~= "table" then return end
    for _, id in Config.SpeciesOrder do
        local entry = profile.collection[id]
        -- Add only new catalog fields. Existing malformed balances remain invalid.
        if entry == nil and table.find({"raptor", "stegosaurus", "ankylosaurus", "archaeopteryx", "baryonyx", "brachiosaurus", "dimorphodon", "elasmosaurus", "gallimimus", "ichthyosaurus", "microraptor", "mosasaurus", "pachycephalosaurus", "parasaurolophus", "plesiosaurus", "pteranodon", "quetzalcoatlus", "spinosaurus", "therizinosaurus"}, id) then
            entry = {base = 0, gold = 0, diamond = 0}
            profile.collection[id] = entry
        end
        if typeof(entry) == "table" and entry.diamond == nil then entry.diamond = 0 end
        if typeof(entry) == "table" and entry.events == nil then entry.events = {} end
        if typeof(entry) == "table" and entry.variants == nil then entry.variants = {} end
    end
    if profile.metrics == nil then profile.metrics = {playSeconds = 0, rarest = 0, robux = 0} end
    if profile.purchaseReceipts == nil then profile.purchaseReceipts = {} end
    if typeof(profile.metrics) == "table" then upgradeRarityScale(profile) end
end

local function defaultProfile()
    local collection = {}
    for _, id in Config.SpeciesOrder do collection[id] = {base = if id == "compy" then 1 else 0, gold = 0, diamond = 0} end
    return {
        schemaVersion = Config.ProfileSchemaVersion,
        rarityScale = Config.SpeciesRarityScale,
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
    -- BD-044 additive fields. Absent on older saves; capacities gate run starts, not loads,
    -- so only a generous structural ceiling is enforced here (never strand a save).
    local function validId(id) return typeof(id) == "string" and #id >= 1 and #id <= 80 end
    local function validBankedEgg(egg) return validEgg(egg) and validId(egg.eggId) end
    local function validNest(nest, slotted: boolean)
        if typeof(nest) ~= "table" or not validId(nest.nestId) or typeof(nest.eggs) ~= "table" or #nest.eggs > 20 then return false end
        if slotted and (typeof(nest.readyAt) ~= "number" or nest.readyAt ~= nest.readyAt or nest.readyAt < 0
            or nest.readyAt % 1 ~= 0 or nest.readyAt == math.huge) then return false end
        for _, egg in nest.eggs do if not validBankedEgg(egg) then return false end end
        return true
    end
    if profile.runEggBank ~= nil then
        if typeof(profile.runEggBank) ~= "table" or #profile.runEggBank > 5000 then return false end
        for _, egg in profile.runEggBank do if not validBankedEgg(egg) then return false end end
    end
    if profile.nests ~= nil then
        if typeof(profile.nests) ~= "table" or #profile.nests > 50 then return false end -- structural ceiling only
        for _, nest in profile.nests do if not validNest(nest, true) then return false end end
    end
    if profile.pendingNests ~= nil then
        if typeof(profile.pendingNests) ~= "table" or #profile.pendingNests > 1000 then return false end
        for _, nest in profile.pendingNests do if not validNest(nest, false) then return false end end
    end
    if profile.eggNests ~= nil then -- BD-090 nests v2
        if typeof(profile.eggNests) ~= "table" or #profile.eggNests > 50 then return false end -- structural ceiling only
        for _, nest in profile.eggNests do
            if typeof(nest) ~= "table" or not validId(nest.nestId) or not validId(nest.droppedFromRun)
                or typeof(nest.size) ~= "number" or nest.size % 1 ~= 0 or nest.size < 1 or nest.size > 50
                or typeof(nest.luck) ~= "number" or nest.luck % 1 ~= 0 or nest.luck < 1 or nest.luck > #Config.NestLuckTiers
                or (nest.state ~= "waiting" and nest.state ~= "incubating" and nest.state ~= "ready") then return false end
            -- BD-156 (additive): the weather active when the nest dropped; absent on older nests (rolls no mutations).
            if nest.weatherId ~= nil and (not validId(nest.weatherId) or not ProgressionRules.item(ProgressionConfig.Weather, nest.weatherId)) then return false end
            if nest.state ~= "waiting" and (typeof(nest.readyAt) ~= "number" or nest.readyAt ~= nest.readyAt
                or nest.readyAt < 0 or nest.readyAt % 1 ~= 0 or nest.readyAt == math.huge) then return false end
            if nest.eggs ~= nil then -- legacy precommitted eggs (migrated Build 020 nests)
                if typeof(nest.eggs) ~= "table" or #nest.eggs > 20 or #nest.eggs ~= nest.size then return false end
                for _, egg in nest.eggs do if not validBankedEgg(egg) then return false end end
            end
        end
    end
    if profile.revealSkip ~= nil then
        if typeof(profile.revealSkip) ~= "table" or #profile.revealSkip > Config.SpeciesRarityScale then return false end
        for _, rarity in profile.revealSkip do if typeof(rarity) ~= "number" or rarity % 1 ~= 0 or rarity < 1 or rarity > Config.SpeciesRarityScale then return false end end
    end
    -- BD-264/BD-320: profile.settings is cosmetic and additive. It is NEVER a validity condition: a non-table or
    -- corrupted value reads as defaults (SettingsModel.normalize) and stays untouched in the store until the player
    -- saves settings again. Rejecting it would lock a player out over a volume slider.
    if profile.settledRuns ~= nil then
        if typeof(profile.settledRuns) ~= "table" then return false end
        for _, id in profile.settledRuns do if not validId(id) then return false end end
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
        -- Additive optional Emerald counter (fusion ladder 6/3/2); nil == 0.
        if entry.emerald ~= nil and (typeof(entry.emerald) ~= "number" or entry.emerald < 0
            or entry.emerald % 1 ~= 0 or entry.emerald > 2000000000) then return false end
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
    if profile.rarityScale ~= Config.SpeciesRarityScale or profile.metrics.rarest > Config.SpeciesRarityScale then return false end
    return ProgressionRules.valid(profile.progression)
end

-- BD-359: a run settlement that failed after its whole retry window. Memory only; the lease renew tick retries it by run id
-- (exactly once: settledRuns + recentOperations), so a store hiccup longer than the window delays rewards instead of dropping them.
local pendingSettlements: {[Player]: any} = setmetatable({}, {__mode = "k"}) :: any
local recoveringSettlement: {[Player]: boolean} = setmetatable({}, {__mode = "k"}) :: any
local settlementRecovered: ((Player, string, any) -> ())? = nil
local settlementStats = {attempts = 0, failedWindows = 0, recovered = 0}

local function retrySettlement(label: string, fn, maxAttempts: number?)
    local started = os.clock()
    local lastError = nil
    local attempts = maxAttempts or Config.SettlementMaxAttempts
    for attempt = 1, attempts do
        settlementStats.attempts += 1
        local ok, result = pcall(fn)
        if ok then return true, result end
        lastError = result
        warn(string.format("[Be Dino] %s attempt %d failed: %s", label, attempt, tostring(result)))
        if attempt < attempts then
            local jitter = 1 + Config.SettlementJitter * (2 * math.random() - 1)
            local delay = Config.SettlementBaseDelaySeconds * (2 ^ (attempt - 1)) * jitter
            if os.clock() - started + delay > Config.SettlementRetryWindowSeconds then break end
            task.wait(delay)
        end
    end
    return false, lastError
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
    local traits = EggTraits.selected(collection[profile.equippedSpeciesId], profile.equippedVariantKey)
    player:SetAttribute("EquippedBig", traits ~= nil and traits.big)
    player:SetAttribute("EquippedShiny", traits ~= nil and traits.shiny)
    player:SetAttribute("EquippedGenesJson",HttpService:JSONEncode(if traits then traits.genes else nil))
    player:SetAttribute("AccountLevel",ProgressionRules.level(progress))
    player:SetAttribute("AccountXP",progress.accountXP or 0)
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
    -- BD-044: banked run eggs and separate bonus nests (counts and slot summaries only).
    local banked = if typeof(profile.runEggBank) == "table" then #profile.runEggBank else 0
    player:SetAttribute("BankedRunEggCount", banked)
    player:SetAttribute("QueuedEggsWaiting", banked + (profile.pendingChestGrants or 0))
    local nestSummary = {}
    for _, nest in profile.eggNests or {} do
        table.insert(nestSummary, {id = nest.nestId, size = nest.size, luck = nest.luck, state = nest.state, readyAt = nest.readyAt})
    end
    player:SetAttribute("NestsJson", HttpService:JSONEncode(nestSummary))
    player:SetAttribute("RevealSkipJson", HttpService:JSONEncode(profile.revealSkip or {}))
    -- BD-264: per-player settings; profiles saved before settings v2 have no field and read as defaults.
    player:SetAttribute("SettingsJson", HttpService:JSONEncode(SettingsModel.toStore(SettingsModel.fromStore(profile.settings))))
    player:SetAttribute("RunStartBlocked", ProfileRepository.runStartBlockReason(profile))
    local nextChest = profile.eggs[1]
    local buffered = revealBuffer[player]
    if buffered and #buffered > 0 then
        player:SetAttribute("NextChestId", buffered[1].eggId)
        player:SetAttribute("NextChestReadyAt", 0)
    elseif typeof(nextChest) == "table" then
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
        metadata=table.clone(metadata or {eventId="clear",mutationId=""})
        if metadata.source then
            metadata.source = table.clone(metadata.source)
            metadata.source.originalEggId = chestId
        end
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
                source=metadata.source,
                traitRollVersion=metadata.traitRollVersion,
            })
        else
            profile.pendingChestGrants += 1
            table.insert(profile.pendingEggEvents,metadata)
        end
    end
end

-- BD-044 egg bank. The five-slot queue stays the reveal window; banked run eggs wait
-- behind it (and behind any legacy pending grants) in committed reveal order.
function ProfileRepository.runStartBlockReason(profile: any): string
    local banked = if typeof(profile.runEggBank) == "table" then #profile.runEggBank else 0
    if banked > Config.RunEggBankCapacity - Config.RunEggMaxPerRun then return "egg_bank_full" end
    return ""
end

local function queueEntry(egg: any, readyAt: number)
    local entry = table.clone(egg)
    entry.readyAt = readyAt
    return entry
end

-- Moves banked eggs into free queue slots, preserving FIFO behind legacy overflow.
local function refillFromBank(profile: any, now: number)
    local bank = profile.runEggBank
    if typeof(bank) ~= "table" then return end
    while #profile.eggs < Config.ChestQueueCapacity and profile.pendingChestGrants == 0 and #bank > 0 do
        local readyAt = if Config.ChestTimerSeconds == 0 then now else lastChestReadyAt(profile, now) + Config.ChestTimerSeconds
        table.insert(profile.eggs, queueEntry(table.remove(bank, 1), readyAt))
    end
end

local function bankEggs(profile: any, eggs: {any}, now: number, atFront: boolean?)
    profile.runEggBank = profile.runEggBank or {}
    local bank = profile.runEggBank
    if atFront then
        for i = #eggs, 1, -1 do table.insert(bank, 1, eggs[i]) end
    else
        for _, egg in eggs do table.insert(bank, egg) end
    end
    refillFromBank(profile, now)
end

-- BD-090: advance the one-at-a-time incubation queue on server time.
local function advanceNests(profile: any, now: number)
    if typeof(profile.eggNests) == "table" then NestQueue.advance(profile.eggNests, now, Config.NestIncubationSeconds) end
end

-- Old (Build 020) nests/pendingNests become v2 records that keep their precommitted eggs, so
-- nothing is lost: ready ones are ready, the first unready slotted one keeps its readyAt and
-- incubates, everything else waits in the one-at-a-time queue. Idempotent (fields are cleared).
local function migrateLegacyNests(profile: any, now: number)
    if profile.nests == nil and profile.pendingNests == nil then return end
    local list = if typeof(profile.eggNests) == "table" then profile.eggNests else {}
    local incubating = false
    for _, nest in list do if nest.state == "incubating" then incubating = true end end
    local function convert(old: any, state: string, readyAt: number?)
        local record: any = {nestId = old.nestId, droppedFromRun = (old.source and old.source.runId) or "legacy",
            size = #old.eggs, luck = 1, state = state, eggs = old.eggs}
        if state ~= "waiting" then record.readyAt = readyAt end
        table.insert(list, record)
    end
    for _, old in profile.nests or {} do
        if old.readyAt <= now then convert(old, "ready", old.readyAt)
        elseif not incubating then incubating = true convert(old, "incubating", old.readyAt)
        else convert(old, "waiting") end
    end
    for _, old in profile.pendingNests or {} do convert(old, "waiting") end
    profile.eggNests = list
    profile.nests, profile.pendingNests = nil, nil
    advanceNests(profile, now)
end

local function hasSettledRun(profile: any, runId: string): boolean
    return typeof(profile.settledRuns) == "table" and table.find(profile.settledRuns, runId) ~= nil
end

local function recordSettledRun(profile: any, runId: string)
    profile.settledRuns = profile.settledRuns or {}
    table.insert(profile.settledRuns, runId)
    while #profile.settledRuns > Config.SettledRunLedgerSize do table.remove(profile.settledRuns, 1) end
end

-- Server-only read interface for future selection/details; no new network surface.
function ProfileRepository.dinosaurDetails(player: Player, instanceId: string)
    local profile = profiles[player]
    local state = profile and profile.dinosaurIdentity
    local instance = state and state.instances[instanceId]
    if not instance then return nil end
    local result = DinosaurIdentity.copy(instance)
    if result.origin.kind == "hatch" then result.originalEgg = DinosaurIdentity.copy(state.eggs[result.origin.eggId]) end
    if result.origin.kind == "fusion" then result.lineage = IdentityFusion.lineage(state, result.origin.operationId) end
    return result
end

-- BD-057/BD-064 fusion. Enabled by Config.IdentityFusionPreviewEnabled on unpublished
-- memory profiles, or on persistent profiles when Config.IdentityPersistentEnabled is
-- also true. Trait odds come from the versioned PROVISIONAL FusionOdds roller; tests may
-- inject a controlled roller. FusionService exposes this over the FusionAction remote.
local fusionTestRoller: any = nil
local productionRoller = FusionOdds.roller(function() return Random.new() end)
local function fusionEnabled(): boolean
    return Config.IdentityFusionPreviewEnabled == true and (localPreview or identityPersistent())
end
local function activeRoller(): any
    return if fusionTestRoller ~= nil then fusionTestRoller else productionRoller
end

-- Test hook: inject a controlled roller (nil restores the production roller).
function ProfileRepository.setFusionTestRoller(roller: any): boolean
    if not fusionEnabled() then return false end
    fusionTestRoller = roller
    return true
end

-- Randomized synthesis is a paid random item when donors are Robux-linked. Milestone 1
-- runs with all Robux features off; any profile that ever spent Robux, or a build with
-- crystal packs on, needs the paid-random release gate and a passed PolicyService check.
local function paidRandomBlocked(player: Player, profile: any): boolean
    local robuxLinked = Config.CrystalPacksEnabled == true
        or (type(profile.metrics) == "table" and type(profile.metrics.robux) == "number" and profile.metrics.robux > 0)
    return robuxLinked and (not Config.PaidRandomItemsEnabled or player:GetAttribute("PaidRandomEligible") ~= true)
end

-- Shared precondition for every fusion read/write. Returns cached profile or nil, reason.
local function fusionProfile(player: Player)
    if not fusionEnabled() then return nil, "fusion_disabled" end
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return nil, "profile_not_loaded" end
    if not identityAvailable(cached.dinosaurIdentity) then return nil, "identity_unavailable" end
    if paidRandomBlocked(player, cached) then return nil, "random_items_unavailable" end
    return cached, nil
end

function ProfileRepository.fusionStatus(player: Player): (boolean, string?)
    local cached, reason = fusionProfile(player)
    return cached ~= nil, reason
end

local function instanceSequence(id: string): number
    return tonumber(string.match(id, "/d:(%d+)$")) or 0
end

-- Paged individual-dinosaur list for the Fusion Menu, sorted by instanceId sequence.
-- cursor = last sequence already seen (exclusive); limit 1..200.
function ProfileRepository.listDinosaurs(player: Player, cursor: number?, limit: number?)
    local cached, reason = fusionProfile(player)
    if not cached then return nil, reason end
    local after = cursor or 0
    local size = math.clamp(limit or 100, 1, 200)
    local entries = {}
    for id, instance in cached.dinosaurIdentity.instances do
        local sequence = instanceSequence(id)
        if sequence > after then table.insert(entries, {sequence = sequence, instance = instance}) end
    end
    table.sort(entries, function(a, b) return a.sequence < b.sequence end)
    local page = {}
    for i = 1, math.min(size, #entries) do
        local d = entries[i].instance
        local c = if type(d.cosmetics) == "table" then d.cosmetics else {}
        local auras, trails = 0, 0
        for _, owned in c.ownedAuraIds or {} do if owned then auras += 1 end end
        for _, owned in c.ownedTrailIds or {} do if owned then trails += 1 end end
        table.insert(page, {instanceId = d.instanceId, speciesId = d.speciesId, stage = d.stage,
            genes = DinosaurIdentity.copy(d.genes), big = d.big == true, shiny = d.shiny == true,
            mutationId = d.mutationId or "", originKind = if type(d.origin) == "table" then d.origin.kind else "legacy_unknown",
            locked = d.locked == true, favorited = d.favorited == true, auraCount = auras, trailCount = trails,
            equippedAuraId = c.equippedAuraId or "", equippedTrailId = c.equippedTrailId or ""})
    end
    local nextCursor = if #entries > size then entries[size].sequence else nil
    return {dinosaurs = page, nextCursor = nextCursor}
end

-- Gated Dino Details copy (original egg or fusion lineage) for the remote.
function ProfileRepository.fusionDetails(player: Player, instanceId: string)
    local cached, reason = fusionProfile(player)
    if not cached then return nil, reason end
    local details = ProfileRepository.dinosaurDetails(player, instanceId)
    if not details then return nil, "donor_missing" end
    return details
end

-- Returns a frozen quote (donor validation, ingredient summary, itemized loss
-- manifest, digests) plus the EXACT active odds, without consuming anything.
function ProfileRepository.quoteFusion(player: Player, targetStage: any, donorIds: any)
    local cached, gate = fusionProfile(player)
    if not cached then return nil, gate end
    local quote, reason = IdentityFusion.quote(cached.dinosaurIdentity, keyFor(player), targetStage, donorIds)
    if not quote then return nil, reason end
    local result = DinosaurIdentity.copy(quote)
    local roller = activeRoller()
    if type(roller) == "table" and type(roller.distribution) == "function" then
        local ok, odds = pcall(roller.distribution, DinosaurIdentity.copy(quote.summary))
        result.oddsVersion = roller.version
        result.odds = if ok then odds else nil
    end
    return result
end

-- request = {token, targetStage, donorIds, quoteDigest, consentDigest?}
function ProfileRepository.fuseDinosaurs(player: Player, request: any)
    local cached, gate = fusionProfile(player)
    if not cached then return false, nil, gate end
    if typeof(request) ~= "table" or typeof(request.token) ~= "string" or #request.token < 1
        or #request.token > IdentityFusion.MaxTokenLength then return false, nil, "invalid_token" end
    local ownerKey = keyFor(player)
    local operationId = "fusion:" .. request.token
    local cachedLedger = cached.dinosaurIdentity and cached.dinosaurIdentity.fusions
    if cachedLedger and cachedLedger[operationId] then
        -- Replays never need odds; validate the token still matches the same request.
        local _, status, replay = IdentityFusion.apply(cached, ownerKey, request, nil)
        if status == "duplicate" then return true, replay, "duplicate" end
        return false, nil, "token_conflict"
    end
    local quote, quoteReason = IdentityFusion.quote(cached.dinosaurIdentity, ownerKey, request.targetStage, request.donorIds)
    if not quote then return false, nil, quoteReason end
    if request.quoteDigest ~= quote.quoteDigest then return false, nil, "stale_quote" end
    if quote.consentRequired and request.consentDigest ~= quote.consentDigest then return false, nil, "consent_required" end
    -- Precommit traits ONCE outside UpdateAsync: retries cannot reroll.
    local outcome, outcomeReason = IdentityFusion.prepareOutcome(quote, activeRoller(), EggGenetics.valid)
    if not outcome then return false, nil, outcomeReason end

    local now = os.time()
    local committed, failure, duplicate, leaseLost = nil, nil, false, false
    if not admit(player) then return false, nil, "rate_limited" end
    local ok, updated = retry("identity fusion", function()
        return store:UpdateAsync(ownerKey, function(profileValue)
            committed, failure, duplicate, leaseLost = nil, nil, false, false
            if not isValidProfile(profileValue) then failure = "invalid_profile" return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            local state = profileValue.dinosaurIdentity
            local replay = type(state) == "table" and type(state.fusions) == "table" and state.fusions[operationId] ~= nil
            if not replay and not identityAvailable(state) then failure = "identity_unavailable" return nil end
            local nextProfile, status, result = IdentityFusion.apply(profileValue, ownerKey, request, outcome, now)
            if not nextProfile then failure = status return nil end
            committed = result
            if status == "duplicate" then duplicate = true return profileValue end
            nextProfile.revision += 1
            nextProfile.session.expiresAt = now + Config.ProfileLeaseSeconds
            table.insert(nextProfile.recentOperations, {id = operationId, kind = "identity_fusion",
                outcome = {resultId = result.resultId, targetStage = result.targetStage, speciesId = result.speciesId}})
            trimOperations(nextProfile)
            -- Whole-profile byte preflight before the write (4 MiB DataStore limit).
            if IdentityFusion.encodedSize(nextProfile) > Config.IdentityFusionProfileBudgetBytes then
                failure = "storage_limit"
                return nil
            end
            return nextProfile
        end)
    end)
    if not ok or updated == nil then
        if leaseLost then
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, nil, "lease_lost"
        end
        if failure then return false, nil, failure end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, committed, if duplicate then "duplicate" else "fused"
end

function ProfileRepository.isLoaded(player: Player): boolean
    return profiles[player] ~= nil and player:GetAttribute("ProfileState") == "Loaded"
end

-- Catch-time assignment is immutable; upgraded odds only affect future eggs.
function ProfileRepository.prepareEgg(player: Player,tag)
    local rng=Random.new()
    local p=ProfileRepository.progression(player)
    local result=table.clone(tag)
    -- bd045-genes-v2 = Build 020 genes with ProgressionConfig.ConditionOddsVersion
    -- (bd045-conditions-v1). Older eggs keep "build020-genes-v1" and their saved genes.
    result.traitRollVersion="bd045-genes-v2"
    result.genes=EggGenetics.roll(if p then p.conditionLevel else 0,rng)
    local traits=EggTraits.roll(tag.eventId or "clear",rng:NextNumber(),rng:NextNumber())
    result.shiny,result.big=traits.shiny,traits.big
    return result
end

function ProfileRepository.load(player: Player): boolean
    if profiles[player] then return true end
    local releaseWait = 0
    while (releasing[player.UserId] or 0) > 0 and releaseWait < 150 do -- <= 15 s (release retries are bounded)
        task.wait(0.1)
        releaseWait += 1
    end
    if not player.Parent then return false end
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
            migrateLegacyNests(profileValue, now)
            advanceNests(profileValue, now)

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

    if not player.Parent then
        -- BD-354: the player left while the load was in flight. Take the lease we just wrote back instead of holding it for
        -- ProfileLeaseSeconds (a rejoin would see SessionBusy) and never cache a profile for a departed Player.
        profiles[player] = updated
        ProfileRepository.release(player)
        return false
    end
    if not profiles[player] or updated.revision >= profiles[player].revision then profiles[player] = updated end
    player:SetAttribute("ProfileState", "Loaded")
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true
end

-- Places weather/mutation tags (catch-time metadata) onto egg ordinals. A tag may name
-- its catch ordinal as n; otherwise it takes the next free ordinal.
local function placeEggTags(eggEvents, eggCount: number)
    local placed = table.create(eggCount, false)
    local leftovers = {}
    for _, tag in eggEvents or {} do
        local n = tag.n
        if typeof(n) == "number" and n % 1 == 0 and n >= 1 and n <= eggCount and not placed[n] then
            placed[n] = tag
        else
            table.insert(leftovers, tag)
        end
    end
    local cursor = 1
    for _, tag in leftovers do
        while cursor <= eggCount and placed[cursor] do cursor += 1 end
        if cursor > eggCount then break end
        placed[cursor] = tag
    end
    return placed
end

local function sortByRarity(eggs)
    table.sort(eggs, function(a, b)
        local ar, br = Config.SpeciesRarities[a.reward.speciesId], Config.SpeciesRarities[b.reward.speciesId]
        return if ar == br then a.source.ordinal < b.source.ordinal else ar < br
    end)
end

local function runRewardText(outcome): string
    local eggs = outcome.eggCount or outcome.chestCount or 0
    local parts = {}
    for _, stack in outcome.stacks or {} do -- legacy Build 020 operation replay only
        table.insert(parts, string.format("%dx %s", stack.count, stack.speciesId))
    end
    table.insert(parts, if eggs == 1 then "1 run egg" elseif eggs > 0 then string.format("%d run eggs", eggs) else "no run eggs")
    local nests = outcome.nestCount or 0
    if nests > 0 then table.insert(parts, if nests == 1 then "1 egg nest" else string.format("%d egg nests", nests)) end
    if outcome.nestFull then table.insert(parts, "nest storage full") end
    return table.concat(parts, " | ")
end

-- BD-044 settlement: catches -> exactly that many run eggs (capped per run), plus
-- deterministic crystals and separate bonus nests. Every random draw is committed
-- before UpdateAsync; settledRuns + recentOperations make the run exactly-once.
function ProfileRepository.commitRunSettlement(player: Player, runId: string, catchScore: number, eggEvents, runSeconds: number?, weatherId: string?, maxAttempts: number?)
    local cached = profiles[player]
    local priorState = player:GetAttribute("ProfileState")
    -- BD-354: settlement is the one write that must still be tried after an earlier failed write ("SaveFailed"): it is an
    -- atomic, lease-checked, exactly-once (run id) transaction, and refusing it forfeited the whole run's eggs.
    if not cached or (priorState ~= "Loaded" and priorState ~= "SaveFailed") then
        return false, nil, "profile_not_loaded"
    end
    if typeof(runId) ~= "string" or #runId < 1 or #runId > 64 then
        return false, nil, "invalid_run_id"
    end

    local outcome = RewardMath.computeRunReward(catchScore, runSeconds)
    local nestsEarned = outcome.nestCount -- hidden qualification (server run time + server catches), committed below
    outcome.crystalBox = 0 -- retired random crystal box; kept for client/operation compatibility
    local eggCount = outcome.eggCount
    if eggEvents ~= nil then
        if typeof(eggEvents) ~= "table" or #eggEvents > eggCount then return false, nil, "invalid_egg_events" end
        for _, metadata in eggEvents do if not ProgressionRules.validEgg(metadata) then return false, nil, "invalid_egg_events" end end
    end
    local operationId = "run:" .. runId
    local cachedOperation = findOperation(cached, operationId)
    if cachedOperation or hasSettledRun(cached, runId) then
        -- Cheap replay: skip preparing up to 300 eggs for a run that already committed.
        player:SetAttribute("LastSettledRunId", runId)
        return true, if cachedOperation then cachedOperation.outcome else nil, "duplicate"
    end

    -- Only a known, non-clear weather is stored; anything else (nil, forged, "clear") means no tag.
    local nestWeatherId: string? = nil
    if typeof(weatherId) == "string" and weatherId ~= "clear" and ProgressionRules.item(ProgressionConfig.Weather, weatherId) then nestWeatherId = weatherId end
    local rng = Random.new()
    local tags = placeEggTags(eggEvents, eggCount)
    local runEggs = table.create(eggCount)
    for i = 1, eggCount do
        local tag = tags[i] or {eventId = "clear", mutationId = ""}
        local traits = if tag.genes then tag else ProfileRepository.prepareEgg(player, tag)
        local eggId = RewardMath.runEggId(runId, i)
        table.insert(runEggs, {
            eggId = eggId, kind = "run_egg",
            eventId = tag.eventId or "clear", mutationId = tag.mutationId or "",
            reward = RewardMath.computeChestReward(rng, eggCount),
            shiny = traits.shiny, big = traits.big,
            genes = traits.genes, traitRollVersion = traits.traitRollVersion,
            source = {kind = "run", runId = runId, ordinal = i, originalEggId = eggId},
        })
    end
    sortByRarity(runEggs)
    local leaseLost = false
    local invalid = false
    local duplicate = false
    local duplicateOutcome = nil
    local now = os.time()

    local ok, updated = retrySettlement("run settlement", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost, invalid, duplicate, duplicateOutcome = false, false, false, nil
            if not isValidProfile(profileValue) then invalid = true return nil end
            if not ownSession(profileValue) then
                leaseLost = true
                return nil
            end

            local existing = findOperation(profileValue, operationId)
            if existing or hasSettledRun(profileValue, runId) then
                duplicate = true
                duplicateOutcome = if existing then existing.outcome else nil
                return profileValue
            end

            -- Copies keep the prepared batch immutable across repeated transforms.
            local batch = table.create(#runEggs)
            for _, egg in runEggs do table.insert(batch, DinosaurIdentity.copy(egg)) end
            bankEggs(profileValue, batch, now)
            -- BD-090: nest drop for qualified runs only; storage cap never blocks the settlement.
            profileValue.eggNests = profileValue.eggNests or {}
            advanceNests(profileValue, now)
            local granted = math.min(nestsEarned, math.max(0, Config.NestStorageCapacity - #profileValue.eggNests))
            for j = 1, granted do
                local nestId = RewardMath.nestId(runId, j)
                -- BD-156: a nest dropped during weather carries that weather's tag; its eggs roll the same event
                -- mutation chance as run eggs when it is claimed. Clear weather stores nothing (additive field).
                table.insert(profileValue.eggNests, {nestId = nestId, droppedFromRun = runId,
                    size = RewardMath.nestSize(nestId), luck = 1, state = "waiting", weatherId = nestWeatherId})
            end
            advanceNests(profileValue, now)
            outcome.nestCount = granted
            outcome.nestFull = granted < nestsEarned

            local progress = ProgressionRules.upgrade(profileValue)
            progress.crystals = math.min(ProgressionConfig.MaxCrystals, progress.crystals + outcome.crystals)
            progress.accountXP = math.min(2000000000, progress.accountXP + (outcome.accountXP or eggCount))
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            profileValue.lastCheckpoint = {
                committedAt = now,
                lastSettledRunId = runId,
            }
            recordSettledRun(profileValue, runId)
            table.insert(profileValue.recentOperations, {
                id = operationId,
                kind = "run",
                outcome = outcome,
            })
            trimOperations(profileValue)
            return profileValue
        end)
    end, maxAttempts)

    if not ok or updated == nil then
        if leaseLost then
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, nil, "lease_lost"
        end
        if invalid then return false, nil, "invalid_profile" end
        player:SetAttribute("ProfileState", "SaveFailed")
        -- BD-359: keep what the retry window could not commit; the renew tick tries again (same run id, exactly once).
        if profiles[player] then
            settlementStats.failedWindows += 1
            pendingSettlements[player] = {runId = runId, catchScore = catchScore, eggEvents = eggEvents, runSeconds = runSeconds, weatherId = weatherId}
        end
        return false, nil, "save_failed"
    end

    local pendingRun = pendingSettlements[player]
    if pendingRun and pendingRun.runId == runId then pendingSettlements[player] = nil end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    local committedOutcome = if duplicate then duplicateOutcome else outcome
    if committedOutcome then
        player:SetAttribute("LastRewardText", runRewardText(committedOutcome))
        player:SetAttribute("LastRunCrystals", committedOutcome.crystals or 0)
        player:SetAttribute("LastRunCrystalBox", committedOutcome.crystalBox or 0)
        player:SetAttribute("LastRunEggCount", committedOutcome.eggCount or committedOutcome.chestCount or 0)
        player:SetAttribute("LastRunNestCount", committedOutcome.nestCount or 0)
        player:SetAttribute("LastRunNestFull", committedOutcome.nestFull == true)
    end
    player:SetAttribute("LastSettledRunId", runId)
    if priorState == "SaveFailed" and player:GetAttribute("ProfileState") == "SaveFailed" then player:SetAttribute("ProfileState", "Loaded") end
    return true, committedOutcome, if duplicate then "duplicate" else "committed"
end

-- Number of already-credited eggs whose reveal animation is still buffered in memory.
function ProfileRepository.pendingReveals(player: Player): number
    local buffered = revealBuffer[player]
    return if buffered then #buffered else 0
end

-- UI preference only (which species rarities the client auto-skips while revealing). Rewards
-- never depend on it; skipped eggs are still hatched and credited. Additive profile field.
function ProfileRepository.setRevealSkip(player: Player, selection: any): (boolean, string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return false, "profile_not_loaded" end
    if typeof(selection) ~= "table" or #selection > Config.SpeciesRarityScale then return false, "invalid_selection" end
    local seen, clean = {}, {}
    for _, rarity in selection do
        if typeof(rarity) ~= "number" or rarity % 1 ~= 0 or rarity < 1 or rarity > Config.SpeciesRarityScale or seen[rarity] then return false, "invalid_selection" end
        seen[rarity] = true
        table.insert(clean, rarity)
    end
    table.sort(clean)
    if not admit(player) then return coalesce(player, "revealSkip", clean) end
    if coalesced[player] then coalesced[player].revealSkip = nil end
    return ProfileRepository.writeRevealSkip(player, clean)
end

function ProfileRepository.writeRevealSkip(player: Player, clean: any): (boolean, string)
    local leaseLost = false
    local superseded = false
    local seq = takePrefSeq(player, "revealSkip")
    local now = os.time()
    local ok, updated = retry("reveal skip", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost = false
            superseded = false
            if prefSuperseded(player, "revealSkip", seq) then superseded = true return nil end
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            profileValue.revealSkip = table.clone(clean)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if superseded then return true, "saved" end -- a newer write of the same preference owns the stored value
        if leaseLost then player:SetAttribute("ProfileState", "LeaseLost") return false, "lease_lost" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "saved"
end

-- BD-264 settings v2: UI preferences only (sound levels, effects, weather, calm motion, jump size). Additive profile
-- field `settings`; the server normalizes whatever the client sends, so bad values become defaults.
function ProfileRepository.setSettings(player: Player, raw: any): (boolean, string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return false, "profile_not_loaded" end
    if typeof(raw) ~= "table" then return false, "invalid_settings" end
    local clean = SettingsModel.toStore(SettingsModel.fromStore(raw))
    if not admit(player) then return coalesce(player, "settings", clean) end
    if coalesced[player] then coalesced[player].settings = nil end
    return ProfileRepository.writeSettings(player, clean)
end

function ProfileRepository.writeSettings(player: Player, clean: any): (boolean, string)
    local leaseLost = false
    local superseded = false
    local seq = takePrefSeq(player, "settings")
    local now = os.time()
    local ok, updated = retry("settings", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost = false
            superseded = false
            if prefSuperseded(player, "settings", seq) then superseded = true return nil end
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            profileValue.settings = table.clone(clean)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if superseded then return true, "saved" end -- a newer write of the same preference owns the stored value
        if leaseLost then player:SetAttribute("ProfileState", "LeaseLost") return false, "lease_lost" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "saved"
end

coalesceWriters.settings = function(player, value) return ProfileRepository.writeSettings(player, value) end
coalesceWriters.revealSkip = function(player, value) return ProfileRepository.writeRevealSkip(player, value) end

-- Opens a READY nest (server time): credits its eggs to the front of the banked-egg pipeline,
-- rolled with the nest's luck tier (config), atomically with removing the nest. Idempotent via
-- the "nestclaim:<nestId>" operation record.
local function rollNestEggs(profileValue: any, nest: any): {any}
    if nest.eggs then return nest.eggs end -- migrated legacy nest: precommitted eggs
    local tier = Config.NestLuckTiers[nest.luck]
    local level = ProgressionRules.upgrade(profileValue).conditionLevel + tier.conditionLevels
    local rng = Random.new()
    local eggs = table.create(nest.size)
    for k = 1, nest.size do
        local eggId = nest.nestId .. ":" .. tostring(k)
        local shinyRoll, bigRoll = rng:NextNumber(), rng:NextNumber()
        -- BD-156: same per-egg event roll and chance as run eggs (ProgressionRules.eventEgg), only for weather nests.
        local tag = if nest.weatherId then ProgressionRules.eventEgg(nest.weatherId, rng:NextNumber()) else nil
        table.insert(eggs, {
            eggId = eggId, kind = "nest_egg", eventId = if tag then tag.eventId else "clear", mutationId = if tag then tag.mutationId else "",
            reward = RewardMath.computeChestReward(rng, tier.rarityBoostEggs),
            shiny = shinyRoll < tier.shinyChance, big = bigRoll < tier.bigChance,
            genes = EggGenetics.roll(level, rng), traitRollVersion = "bd045-genes-v2",
            source = {kind = "nest", runId = nest.droppedFromRun, nestId = nest.nestId, ordinal = k, originalEggId = eggId, luck = nest.luck},
        })
    end
    sortByRarity(eggs)
    return eggs
end

function ProfileRepository.claimNest(player: Player, nestId: string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, nil, "profile_not_loaded"
    end
    if typeof(nestId) ~= "string" or #nestId < 1 or #nestId > 80 then
        return false, nil, "invalid_nest_id"
    end
    local operationId = "nestclaim:" .. nestId
    local cachedOperation = findOperation(cached, operationId)
    if cachedOperation then return true, cachedOperation.outcome, "duplicate" end

    local status = nil
    local duplicateOutcome = nil
    local leaseLost = false
    local outcome = nil
    local now = os.time()
    if not admit(player) then return false, nil, "rate_limited" end
    local ok, updated = retry("nest claim", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            status, duplicateOutcome, leaseLost, outcome = nil, nil, false, nil
            if not isValidProfile(profileValue) then status = "invalid_profile" return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            local existing = findOperation(profileValue, operationId)
            if existing then duplicateOutcome = existing.outcome return profileValue end
            migrateLegacyNests(profileValue, now)
            advanceNests(profileValue, now)
            local index = nil
            for i, nest in profileValue.eggNests or {} do
                if nest.nestId == nestId then index = i break end
            end
            if not index then status = "missing" return nil end
            local nest = profileValue.eggNests[index]
            if nest.state ~= "ready" then status = if nest.state == "waiting" then "nest_pending" else "not_ready" return nil end
            local banked = if profileValue.runEggBank then #profileValue.runEggBank else 0
            if banked + nest.size > Config.RunEggBankCapacity then status = "bank_full" return nil end
            table.remove(profileValue.eggNests, index)
            bankEggs(profileValue, rollNestEggs(profileValue, nest), now, true)
            advanceNests(profileValue, now)
            outcome = {nestId = nestId, eggCount = nest.size, luck = nest.luck}
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            table.insert(profileValue.recentOperations, {id = operationId, kind = "nest_claim", outcome = outcome})
            trimOperations(profileValue)
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if leaseLost then
            player:SetAttribute("ProfileState", "LeaseLost")
            return false, nil, "lease_lost"
        end
        if status then return false, nil, status end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    if duplicateOutcome then return true, duplicateOutcome, "duplicate" end
    return true, outcome, "opened"
end


-- variantKey (optional, BD-150): equip one exact owned copy of the species. It must be a variant key of the player's
-- own collection entry with count > 0, so a client can never equip a copy it does not own.
function ProfileRepository.equipSpecies(player: Player, speciesId: string, variantKey: string?): (boolean, string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then
        return false, "profile_not_loaded"
    end
    if typeof(speciesId) ~= "string" or #speciesId < 1 or #speciesId > 32 then
        return false, "invalid_species"
    end
    if not knownSpecies(speciesId) then return false, "unknown_species" end

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
    if cached.equippedSpeciesId == speciesId and cached.equippedVariantKey == variantKey then
        syncAttributes(player, cached)
        return true, "already_equipped"
    end

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
            profileValue.equippedSpeciesId = speciesId
            profileValue.equippedVariantKey = variantKey
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

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
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

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
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

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, if duplicate then "duplicate" else "granted"
end

-- Credits one queue egg (collection, identity, metrics), refills the queue and records
-- its operation. Returns the committed outcome or nil. Runs inside an UpdateAsync transform.
local function applyHatch(profileValue: any, chest: any, index: number, outcome: any, now: number)
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
    if identityAvailable(profileValue.dinosaurIdentity) and not outcome.failed then
        local bucketKey = outcome.speciesId .. "/base"
        if chest.big or chest.shiny or chest.genes then
            bucketKey = outcome.speciesId .. "/variant/" .. EggTraits.key(mutationId, chest.shiny == true, chest.big == true, chest.genes)
        elseif mutationId ~= "" then bucketKey = outcome.speciesId .. "/event/" .. mutationId end
        outcome.instanceIds = DinosaurIdentity.hatch(profileValue.dinosaurIdentity, chest,
            outcome.speciesId, outcome.count, bucketKey)
    end
    outcome.eventMutationId=mutationId
    outcome.eventId=chest.eventId or "clear"
    outcome.big=chest.big == true
    outcome.shiny=chest.shiny == true
    outcome.eggId=chest.eggId
    if not outcome.failed then profileValue.metrics.rarest = math.max(profileValue.metrics.rarest, Config.SpeciesRarities[outcome.speciesId]) end

    if profileValue.pendingChestGrants > 0 then
        profileValue.pendingChestGrants -= 1
        local readyAt = if Config.ChestTimerSeconds == 0 then now else lastChestReadyAt(profileValue, now) + Config.ChestTimerSeconds
        local metadata=if profileValue.pendingEggEvents then table.remove(profileValue.pendingEggEvents,1) else nil
        table.insert(profileValue.eggs, {
            eggId = HttpService:GenerateGUID(false),
            kind = "alpha_chest",
            readyAt = readyAt,
            eventId=if metadata then metadata.eventId else "clear",
            mutationId=if metadata then metadata.mutationId else "",
            reward=if metadata then metadata.reward else nil,
            shiny=if metadata then metadata.shiny else nil,
            big=if metadata then metadata.big else nil,
            genes=if metadata then metadata.genes else nil,
            source=if metadata then metadata.source else nil,
            traitRollVersion=if metadata then metadata.traitRollVersion else nil,
        })
    end
    -- BD-044: banked run/nest eggs advance once legacy overflow is drained.
    refillFromBank(profileValue, now)
    table.insert(profileValue.recentOperations, {id = "chest:" .. chest.eggId, kind = "chest_claim", outcome = outcome})
    return outcome
end

local function publishHatch(player: Player, chestId: string, committedOutcome: any)
    player:SetAttribute("LastChestRewardText", string.format("%dx %s", committedOutcome.count, committedOutcome.speciesId))
    player:SetAttribute("LastChestEventMutation",committedOutcome.eventMutationId or "")
    player:SetAttribute("LastChestBig",committedOutcome.big == true)
    player:SetAttribute("LastChestShiny",committedOutcome.shiny == true)
    player:SetAttribute("LastChestGenesJson",HttpService:JSONEncode(committedOutcome.genes))
    player:SetAttribute("LastChestFailed",committedOutcome.failed==true)
    player:SetAttribute("LastClaimedChestId", chestId)
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
    -- Reveal an already-committed page entry: no DataStore request.
    local buffered = revealBuffer[player]
    if buffered and #buffered > 0 then
        if buffered[1].eggId ~= chestId then
            local done = findOperation(cached, operationId)
            if done then return true, done.outcome, "duplicate" end
            -- "Reveal next": a claim for a still-queued egg while a page is waiting reveals the
            -- page head (pages precede later queue eggs); anything else is unknown.
            local queued = false
            for _, queuedEgg in cached.eggs do if queuedEgg.eggId == chestId then queued = true break end end
            if not queued then return false, nil, "missing" end
            chestId = buffered[1].eggId
        end
        local entry = table.remove(buffered, 1)
        syncAttributes(player, cached)
        publishHatch(player, chestId, entry.outcome)
        return true, entry.outcome, "claimed"
    end
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
    local pageOutcomes = {}
    local duplicateOutcome = nil
    local leaseLost = false
    local notReady = false
    local missing = false

    if not admit(player) then return false, nil, "rate_limited" end
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

            pageOutcomes = {}
            if not applyHatch(profileValue, chest, index, outcome, now) then return nil end
            -- Hatch page: following ready run/nest eggs at the queue head commit in the same
            -- transaction (their rewards are precommitted, so nothing is rerolled).
            while #pageOutcomes < Config.HatchPageSize - 1 and chest.reward and chest.genes
                and (chest.kind == "run_egg" or chest.kind == "nest_egg") do
                local nextEgg = profileValue.eggs[1]
                if not nextEgg or not nextEgg.reward or not nextEgg.genes or now < nextEgg.readyAt
                    or (nextEgg.kind ~= "run_egg" and nextEgg.kind ~= "nest_egg") then break end
                local nextOutcome = applyHatch(profileValue, nextEgg, 1, table.clone(nextEgg.reward), now)
                if not nextOutcome then return nil end
                table.insert(pageOutcomes, nextOutcome)
            end

            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
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

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    local committedOutcome = duplicateOutcome or outcome
    if not duplicateOutcome and #pageOutcomes > 0 then
        local pageBuffer = {}
        for _, pageOutcome in pageOutcomes do table.insert(pageBuffer, {eggId = pageOutcome.eggId, outcome = pageOutcome}) end
        revealBuffer[player] = pageBuffer
        if profiles[player] then syncAttributes(player, profiles[player]) end
    end
    publishHatch(player, chestId, committedOutcome)
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
            player:SetAttribute("ProfileState", "LeaseLost")
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

    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
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
        egg.source={kind="crystal_shop", currency="crystals", funding="unknown", conditionLevel=purchaseConditionLevel}
        egg.reward=RewardMath.computeChestReward(Random.new(),1)
    end
    local operationId="progression:"..token
    local now=os.time()
    local denied="save_failed"
    local duplicate=false
    local outcome=nil
    local leaseLost=false
    if not admit(player) then return false,"rate_limited" end
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
    adopt(player, updated)
    if player.Parent and profiles[player] then syncAttributes(player,profiles[player]) end
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
    adopt(player, updated)
    syncAttributes(player,profiles[player])
    return true
end

-- BD-359: retry the settlement that exhausted its window. Called by the renew tick; one at a time per player.
-- Two attempts per tick keep a long outage from adding more than ~2 requests / 30 s per stuck player. Returns true when nothing
-- is pending any more.
local function recoverSettlement(player: Player): boolean
    local pending = pendingSettlements[player]
    if not pending then return true end
    if recoveringSettlement[player] or not profiles[player] then return false end
    recoveringSettlement[player] = true
    local ok, outcome, status = ProfileRepository.commitRunSettlement(player, pending.runId, pending.catchScore, pending.eggEvents, pending.runSeconds, pending.weatherId, 2)
    recoveringSettlement[player] = nil
    if ok then
        settlementStats.recovered += 1
        if settlementRecovered and player.Parent then
            local hooked, err = pcall(settlementRecovered, player, pending.runId, outcome)
            if not hooked then warn("[Be Dino] settlement recovery hook failed: " .. tostring(err)) end
        end
    elseif status == "lease_lost" or status == "invalid_profile" then
        pendingSettlements[player] = nil -- not retryable: another server owns the profile / the stored copy is invalid
    end
    return ok == true
end

-- Called once by Bootstrap: what to do (respawn the player) after a delayed settlement finally commits.
function ProfileRepository.setSettlementRecoveredHook(hook: (Player, string, any) -> ())
    settlementRecovered = hook
end

-- Offline-test and diagnostics counters (no profile data).
function ProfileRepository.budgetStats()
    return {admitted = writeStats.admitted, rejected = writeStats.rejected, coalesced = writeStats.coalesced, flushed = writeStats.flushed,
        settlementAttempts = settlementStats.attempts, settlementFailedWindows = settlementStats.failedWindows, settlementRecovered = settlementStats.recovered}
end

function ProfileRepository.pendingSettlement(player: Player): string?
    local pending = pendingSettlements[player]
    return if pending then pending.runId else nil
end

function ProfileRepository.renew(player: Player): boolean
    -- BD-359: first commit the settlement that outlasted its retry window. It also renews the lease, so when it fails (store
    -- still down) skip the renew's own retries instead of adding more requests to an outage.
    if pendingSettlements[player] and not recoverSettlement(player) then return false end
    local state = player:GetAttribute("ProfileState")
    -- BD-354: "SaveFailed" is recoverable. Every write is one atomic UpdateAsync that is checked against our lease, so a
    -- successful renew proves the store is consistent and hands back the authoritative copy; without this one failed
    -- equip/potion write bricked the player (no runs, no claims, settlement refused) until they rejoined.
    if not profiles[player] or (state ~= "Loaded" and state ~= "SaveFailed") then return false end
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
    adopt(player, updated) -- the store copy is authoritative after a recovery (its revision is never older)
    if state == "SaveFailed" then player:SetAttribute("ProfileState", "Loaded") end
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true
end

function ProfileRepository.release(player: Player)
    revealBuffer[player] = nil
    local pendingPrefs = coalesced[player]
    coalesced[player] = nil
    pendingSettlements[player] = nil
    local cached = profiles[player]
    profiles[player] = nil
    if not cached then return end

    local userId = player.UserId
    releasing[userId] = (releasing[userId] or 0) + 1
    local ok, updated = retry("lease release", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            if not isValidProfile(profileValue) or not ownSession(profileValue) then return nil end
            profileValue.metrics.playSeconds = math.min(2000000000, profileValue.metrics.playSeconds + math.max(0, os.time() - (profileValue.session.metricsAt or os.time())))
            -- BD-358: coalesced preferences that were still waiting for a token are saved here, never dropped.
            if pendingPrefs and pendingPrefs.settings then profileValue.settings = table.clone(pendingPrefs.settings.value) end
            if pendingPrefs and pendingPrefs.revealSkip then profileValue.revealSkip = table.clone(pendingPrefs.revealSkip.value) end
            profileValue.session = nil
            profileValue.revision += 1
            return profileValue
        end)
    end)
    releasing[userId] = (releasing[userId] or 1) - 1
    if releasing[userId] <= 0 then releasing[userId] = nil end
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
