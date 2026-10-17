--!strict
-- The profile store: lease-checked UpdateAsync transactions over one DataStore key per player. THIS file keeps the shared
-- infrastructure (store wrappers, lease, retry, write budget, profile defaults / migration / validity, syncAttributes, load, renew,
-- release); the transaction groups live in ProfileEggs, ProfileFusion, ProfileObjectives, ProfileGifts, ProfileSkins, ProfileShop,
-- ProfileCollection, ProfilePrefs and ProfileTestGrants and are installed on this table at the bottom (docs/150, BD-607).
local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local RewardMath = require(script.Parent.RewardMath)
local ProgressionRules = require(ReplicatedStorage.Shared.ProgressionRules)
local EggTraits = require(ReplicatedStorage.Shared.EggTraits)
local EggGenetics = require(ReplicatedStorage.Shared.EggGenetics)
local FtueRules = require(ReplicatedStorage.Shared.FtueRules)
local NestQueue = require(ReplicatedStorage.Shared.NestQueue)
local ProgressionConfig = require(ReplicatedStorage.Shared.ProgressionConfig)

local ProfileRepository: any = {}
local PrivateState = require(script.Parent.PrivateState)
local RareHatchService = require(script.Parent.RareHatchService) -- BD-428
local DinosaurIdentity = require(script.Parent.DinosaurIdentity)
local IdentityFusion = require(script.Parent.IdentityFusion)
local FusionOdds = require(script.Parent.FusionOdds)
local CosmeticOwnership = require(script.Parent.CosmeticOwnership) -- BD-059 phase 2, only used when Config.PerDinoCosmeticsEnabled
local SettingsModel = require(ReplicatedStorage.Shared.SettingsModel)
local PaidRandomGate = require(ReplicatedStorage.Shared.PaidRandomGate) -- BD-532

-- BD-074 (docs/66 s18): a committed gameplay fact is reported to ObjectiveService AFTER its transaction (never before, never from
-- the client). Every call site is `if Config.ObjectivesEnabled == true then objectives().x(...) end`: with the flag off that is one
-- boolean test, ObjectiveService is never even required, and no argument is evaluated. Required lazily so offline harnesses that
-- do not carry the module are unaffected while the flag is off (tools/verify_objective_hooks.py checks every site).
local objectiveService: any = nil
local function objectives(): any
    if objectiveService == nil then objectiveService = require(script.Parent.ObjectiveService) end
    return objectiveService
end

local RunService = game:GetService("RunService")
local localPreview = RunService:IsStudio() and game.GameId == 0 and Config.StudioLocalProfilesEnabled
local demoActive = localPreview and Config.DemoDirectorEnabled == true -- docs/133: Studio-only, unpublished, flag-gated demo triggers
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

-- BD-604 (docs/149): the secret species data/rules module, required lazily so a harness that does not carry it is unaffected while
-- Config.SecretSpeciesEnabled is false (every use below is behind that flag).
local secretModule: any = nil
local function secretSpecies(): any
    if secretModule == nil then secretModule = require(ReplicatedStorage.Shared.SecretSpeciesConfig) end
    return secretModule
end

-- BD-604: knownSpecies stays the NORMAL 22 on purpose. A secret species is not equippable or mutable by request yet (docs/149 s7), so no
-- profile ever stores a secret id in equippedSpeciesId or a reward.speciesId, and Build 020 keeps loading every profile (RB1).
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

-- BD-059 phase 2: with the flag on, reads see the equipped dino's own + legacy cosmetics (stored data is unchanged).
local function progressionView(profile: any)
    local progress=ProgressionRules.upgrade(profile)
    if Config.PerDinoCosmeticsEnabled==true and identityAvailable(profile.dinosaurIdentity) then
        return CosmeticOwnership.view(progress,profile.dinosaurIdentity,profile.equippedSpeciesId,profile.equippedVariantKey)
    end
    return progress
end

local function syncAttributes(player: Player, profile: any)
    local progress=progressionView(profile)
    PrivateState.set(player, "StudioTestWallet", localPreview and Config.StudioTestWalletEnabled)
    PrivateState.set(player, "CollectionJson", HttpService:JSONEncode(profile.collection))
    PrivateState.set(player, "Crystals",progress.crystals)
    PrivateState.set(player, "ProgressionJson",HttpService:JSONEncode(progress))
    PrivateState.set(player, "DiscoveryJson",HttpService:JSONEncode(ProgressionRules.discoveryCounts(profile))) -- BD-436 counts only
    player:SetAttribute("EquippedAura",progress.equippedAura)
    local collection = profile.collection
    PrivateState.set(player, "CompyCopies", collection.compy.base)
    PrivateState.set(player, "CompyGold", collection.compy.gold)
    PrivateState.set(player, "TriceratopsCopies", collection.triceratops.base)
    PrivateState.set(player, "TriceratopsGold", collection.triceratops.gold)
    PrivateState.set(player, "TyrannosaurusCopies", collection.tyrannosaurus.base)
    PrivateState.set(player, "TyrannosaurusGold", collection.tyrannosaurus.gold)
    PrivateState.set(player, "PendingChestGrants", profile.pendingChestGrants or 0)
    PrivateState.set(player, "ProfileRevision", profile.revision or 0)
    player:SetAttribute("EquippedSpeciesId", profile.equippedSpeciesId)
    local traits = EggTraits.selected(collection[profile.equippedSpeciesId], profile.equippedVariantKey)
    player:SetAttribute("EquippedBig", traits ~= nil and traits.big)
    player:SetAttribute("EquippedShiny", traits ~= nil and traits.shiny)
    player:SetAttribute("EquippedGenesJson",HttpService:JSONEncode(if traits then traits.genes else nil))
    player:SetAttribute("AccountLevel",ProgressionRules.level(progress))
    PrivateState.set(player, "AccountXP",progress.accountXP or 0)
    PrivateState.set(player, "PlaySeconds", profile.metrics.playSeconds)
    PrivateState.set(player, "RarestCaught", profile.metrics.rarest)
    PrivateState.set(player, "RobuxSpent", profile.metrics.robux)
    local eventMutation=if traits then ProgressionRules.item(ProgressionConfig.EventMutations,traits.mutationId) else ProgressionRules.eventMutation(collection[profile.equippedSpeciesId])
    player:SetAttribute("EquippedEventMutation",if eventMutation then eventMutation.id else "")
    PrivateState.set(player, "ActiveChestCount", #profile.eggs)
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
    PrivateState.set(player, "ChestQueueJson", HttpService:JSONEncode(chestSummary))
    -- BD-044: banked run eggs and separate bonus nests (counts and slot summaries only).
    local banked = if typeof(profile.runEggBank) == "table" then #profile.runEggBank else 0
    PrivateState.set(player, "BankedRunEggCount", banked)
    PrivateState.set(player, "QueuedEggsWaiting", banked + (profile.pendingChestGrants or 0))
    -- BD-380: eggs of the current hatch page are already credited and out of profile.eggs, so neither count above includes
    -- them; the hatch hint ("N left", "Egg 2 of 4") adds this number so it equals the eggs really left to open.
    local pendingPage = revealBuffer[player]
    PrivateState.set(player, "BufferedRevealCount", if pendingPage then #pendingPage else 0)
    local nestSummary = {}
    for _, nest in profile.eggNests or {} do
        table.insert(nestSummary, {id = nest.nestId, size = nest.size, luck = nest.luck, state = nest.state, readyAt = nest.readyAt})
    end
    PrivateState.set(player, "NestsJson", HttpService:JSONEncode(nestSummary))
    PrivateState.set(player, "RevealSkipJson", HttpService:JSONEncode(profile.revealSkip or {}))
    -- BD-264: per-player settings; profiles saved before settings v2 have no field and read as defaults.
    PrivateState.set(player, "SettingsJson", HttpService:JSONEncode(SettingsModel.toStore(SettingsModel.fromStore(profile.settings))))
    PrivateState.set(player, "RunStartBlocked", ProfileRepository.runStartBlockReason(profile))
    local nextChest = profile.eggs[1]
    local buffered = revealBuffer[player]
    if buffered and #buffered > 0 then
        PrivateState.set(player, "NextChestId", buffered[1].eggId)
        PrivateState.set(player, "NextChestReadyAt", 0)
    elseif typeof(nextChest) == "table" then
        PrivateState.set(player, "NextChestId", nextChest.eggId)
        PrivateState.set(player, "NextChestReadyAt", nextChest.readyAt)
    else
        PrivateState.set(player, "NextChestId", "")
        PrivateState.set(player, "NextChestReadyAt", 0)
    end
end

-- BD-363 (docs/111 L4): the lease is gone (another server took the profile over). It used to be silent: the player kept running
-- while every settlement was refused. Now it is logged once, the client gets a message through ProfileState, and after a short
-- grace the player is sent back to rejoin and load the authoritative profile. Nothing is rewritten here: every settled run is
-- already committed in the store by run id, and an unsettled one is logged with its run id (this server cannot write it anymore).
local LEASE_LOST_KICK_SECONDS = 6
local leaseLostHandled: {[Player]: boolean} = setmetatable({}, {__mode = "k"}) :: any
local leaseLostStats = {handled = 0, kicked = 0}
local function handleLeaseLost(player: Player)
    player:SetAttribute("ProfileState", "LeaseLost")
    if leaseLostHandled[player] then return end
    leaseLostHandled[player] = true
    leaseLostStats.handled += 1
    local pending = pendingSettlements[player]
    warn(string.format("[Be Dino] LeaseLost for user %d%s; sending the player back to rejoin", player.UserId,
        if pending then " with an unsettled run " .. tostring(pending.runId) else ""))
    task.spawn(function()
        task.wait(LEASE_LOST_KICK_SECONDS)
        if player.Parent and player:GetAttribute("ProfileState") == "LeaseLost" then
            leaseLostStats.kicked += 1
            player:Kick("Your save session changed. Please rejoin.")
        end
    end)
end

function ProfileRepository.leaseLostStats() return leaseLostStats end

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
            ProgressionRules.backfillDiscovered(profileValue) -- BD-436: add-only, idempotent
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

function ProfileRepository.progression(player: Player)
    if not ProfileRepository.isLoaded(player) then return nil end
    return progressionView(profiles[player])
end

-- BD-073 (docs/66): kept here because release() below flushes it; the objective transactions are in ProfileObjectives.
local objectivePending: {[Player]: {any}} = setmetatable({}, {__mode = "k"}) :: any

local function objectiveRules(): any
    return require(ReplicatedStorage.Shared.ObjectiveRules)
end

-- BD-359: retry the settlement that exhausted its window. Called by the renew tick; one at a time per player.
-- Two attempts per tick keep a long outage from adding more than ~2 requests / 30 s per stuck player. Returns true when nothing
-- is pending any more.
local function recoverSettlement(player: Player): boolean
    local pending = pendingSettlements[player]
    if not pending then return true end
    if recoveringSettlement[player] or not profiles[player] then return false end
    recoveringSettlement[player] = true
    local ok, outcome, status = ProfileRepository.commitRunSettlement(player, pending.runId, pending.catchScore, pending.eggEvents, pending.runSeconds, pending.nestWeather, 2)
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
        if leaseLost then handleLeaseLost(player) else player:SetAttribute("ProfileState", "SaveFailed") end
        return false
    end
    adopt(player, updated) -- the store copy is authoritative after a recovery (its revision is never older)
    if state == "SaveFailed" then player:SetAttribute("ProfileState", "Loaded") end
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true
end

function ProfileRepository.release(player: Player)
    revealBuffer[player] = nil
    local pendingObjectives = objectivePending[player] -- BD-073: unflushed progress rides the lease release (nil while the flag is off)
    objectivePending[player] = nil
    local objectiveBatchId = if pendingObjectives ~= nil and #pendingObjectives > 0 and Config.ObjectivesEnabled == true then HttpService:GenerateGUID(false) else nil
    local pendingPrefs = coalesced[player]
    coalesced[player] = nil
    pendingSettlements[player] = nil
    local cached = profiles[player]
    profiles[player] = nil
    PrivateState.forget(player) -- BD-360: the owner-only values go with the profile
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
            if objectiveBatchId ~= nil and pendingObjectives ~= nil then
                -- A rules bug must never block the lease release: applyToProfile only assigns on success, pcall absorbs a throw.
                pcall(function() objectiveRules().applyToProfile(profileValue, pendingObjectives, os.time(), objectiveBatchId) end)
            end
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

-- Split modules (docs/150): each part holds one group of transactions, moved out unchanged, and installs its functions on this table.
-- Everything they share with the code above is handed over here, after the store wrappers, `profiles` and the helpers exist.
local shared = {
    Config = Config,
    CosmeticOwnership = CosmeticOwnership,
    DinosaurIdentity = DinosaurIdentity,
    EggGenetics = EggGenetics,
    EggTraits = EggTraits,
    FtueRules = FtueRules,
    FusionOdds = FusionOdds,
    HttpService = HttpService,
    IdentityFusion = IdentityFusion,
    PaidRandomGate = PaidRandomGate,
    PrivateState = PrivateState,
    ProgressionConfig = ProgressionConfig,
    ProgressionRules = ProgressionRules,
    RareHatchService = RareHatchService,
    ReplicatedStorage = ReplicatedStorage,
    RewardMath = RewardMath,
    SettingsModel = SettingsModel,
    admit = admit,
    adopt = adopt,
    advanceNests = advanceNests,
    availableChestCapacity = availableChestCapacity,
    bankEggs = bankEggs,
    coalesce = coalesce,
    coalesceWriters = coalesceWriters,
    coalesced = coalesced,
    demoActive = demoActive,
    enqueueChestIds = enqueueChestIds,
    findOperation = findOperation,
    handleLeaseLost = handleLeaseLost,
    hasSettledRun = hasSettledRun,
    identityAvailable = identityAvailable,
    identityPersistent = identityPersistent,
    isValidProfile = isValidProfile,
    keyFor = keyFor,
    knownSpecies = knownSpecies,
    lastChestReadyAt = lastChestReadyAt,
    localPreview = localPreview,
    migrateLegacyNests = migrateLegacyNests,
    objectivePending = objectivePending,
    objectiveRules = objectiveRules,
    objectives = objectives,
    ownSession = ownSession,
    ownsAny = ownsAny,
    pendingSettlements = pendingSettlements,
    prefSuperseded = prefSuperseded,
    profiles = profiles,
    recordSettledRun = recordSettledRun,
    refillFromBank = refillFromBank,
    retry = retry,
    retrySettlement = retrySettlement,
    revealBuffer = revealBuffer,
    secretSpecies = secretSpecies,
    settlementStats = settlementStats,
    store = store,
    syncAttributes = syncAttributes,
    takePrefSeq = takePrefSeq,
    trimOperations = trimOperations,
}
require(script.Parent.ProfileFusion)(ProfileRepository, shared)
require(script.Parent.ProfileEggs)(ProfileRepository, shared)
require(script.Parent.ProfilePrefs)(ProfileRepository, shared)
require(script.Parent.ProfileCollection)(ProfileRepository, shared)
require(script.Parent.ProfileTestGrants)(ProfileRepository, shared)
require(script.Parent.ProfileShop)(ProfileRepository, shared)
require(script.Parent.ProfileObjectives)(ProfileRepository, shared)
require(script.Parent.ProfileGifts)(ProfileRepository, shared)
require(script.Parent.ProfileSkins)(ProfileRepository, shared)

return ProfileRepository
