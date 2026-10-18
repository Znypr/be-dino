--!strict
-- ProfileRepository part (docs/150): run settlement, bonus nest claim and egg hatch transactions (BD-044 / BD-090).
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local DinosaurIdentity = shared.DinosaurIdentity
local EggGenetics = shared.EggGenetics
local EggTraits = shared.EggTraits
local FtueRules = shared.FtueRules
local HttpService = shared.HttpService
local PrivateState = shared.PrivateState
local ProgressionConfig = shared.ProgressionConfig
local ProgressionRules = shared.ProgressionRules
local RareHatchService = shared.RareHatchService
local RewardMath = shared.RewardMath
local admit = shared.admitAs("ProfileEggs") -- BD-650: the label names the service in the rate_limited count
local adopt = shared.adopt
local advanceNests = shared.advanceNests
local settlementAdvancesState = shared.settlementAdvancesState
local bankEggs = shared.bankEggs
local findOperation = shared.findOperation
local handleLeaseLost = shared.handleLeaseLost
local hasSettledRun = shared.hasSettledRun
local identityAvailable = shared.identityAvailable
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local lastChestReadyAt = shared.lastChestReadyAt
local migrateLegacyNests = shared.migrateLegacyNests
local objectives = shared.objectives
local ownSession = shared.ownSession
local ownsAny = shared.ownsAny
local pendingSettlements = shared.pendingSettlements
local profiles = shared.profiles
local recordSettledRun = shared.recordSettledRun
local refillFromBank = shared.refillFromBank
local retry = shared.retry
local retrySettlement = shared.retrySettlement
local revealBuffer = shared.revealBuffer
local secretSpecies = shared.secretSpecies
local settlementStats = shared.settlementStats
local store = shared.store
local syncAttributes = shared.syncAttributes
local trimOperations = shared.trimOperations

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
        if Config.SecretSpeciesEnabled == true then -- BD-604: an egg that carries a secret species reveals last
            if a.reward.secretSpeciesId ~= nil then ar = Config.SpeciesRarityScale + 1 end
            if b.reward.secretSpeciesId ~= nil then br = Config.SpeciesRarityScale + 1 end
        end
        return if ar == br then a.source.ordinal < b.source.ordinal else ar < br
    end)
end

local function runRewardText(outcome): string
    local eggs = outcome.eggCount or outcome.chestCount or 0
    local parts = {}
    for _, stack in outcome.stacks or {} do -- legacy Build 020 operation replay only
        table.insert(parts, string.format("%dx %s", stack.count, stack.speciesId))
    end
    table.insert(parts, if eggs == 1 then "1 egg" elseif eggs > 0 then string.format("%d eggs", eggs) else "no eggs")
    local nests = outcome.nestCount or 0
    if nests > 0 then table.insert(parts, if nests == 1 then "1 nest" else string.format("%d nests", nests)) end
    if outcome.nestFull then table.insert(parts, "nest storage full") end
    if (outcome.nestCrystals or 0) > 0 then table.insert(parts, string.format("%d crystals for extra nests", outcome.nestCrystals)) end
    return table.concat(parts, " + ")
end

-- BD-615 (docs/151 F5): a run that earned nothing (0 eggs, 0 crystals, 0 nests, 0 XP, no egg events) is settled in memory when the stored profile would
-- not change anyway (no banked eggs, no nest to advance, state Loaded): the ledger entry it would write is the only difference. Its run id is
-- remembered for the session so a repeat is answered "duplicate" exactly like a stored one. Everything else about the settlement is unchanged.
local emptyRunsSettled: {[Player]: {order: {string}, byId: {[string]: any}}} = setmetatable({}, {__mode = "k"}) :: any
local EMPTY_RUN_MEMORY = 64

-- BD-044 settlement: catches -> exactly that many run eggs (capped per run), plus
-- deterministic crystals and separate bonus nests. Every random draw is committed
-- before UpdateAsync; settledRuns + recentOperations make the run exactly-once.
function ProfileRepository.commitRunSettlement(player: Player, runId: string, catchScore: number, eggEvents, runSeconds: number?, nestWeather: any?, maxAttempts: number?)
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
        PrivateState.set(player, "LastSettledRunId", runId)
        return true, if cachedOperation then cachedOperation.outcome else nil, "duplicate"
    end
    local emptyMemory = emptyRunsSettled[player]
    if emptyMemory and emptyMemory.byId[runId] ~= nil then
        PrivateState.set(player, "LastSettledRunId", runId)
        return true, emptyMemory.byId[runId], "duplicate" -- an empty run settled in memory earlier this session (BD-615)
    end
    local skipWrite = priorState == "Loaded" and eggCount == 0 and outcome.crystals == 0 and nestsEarned == 0 and (outcome.accountXP or 0) == 0
        and (eggEvents == nil or #eggEvents == 0) and not settlementAdvancesState(cached, os.time())

    -- BD-479: `nestWeather` is the run's per-nest ledger ({"rain", "clear", ...}, index = nest ordinal, recorded when each nest was
    -- found) or, from legacy callers, one weather id for every nest. Each nest below takes its own entry through
    -- RewardMath.nestWeatherId, which stores only a known, non-clear weather; anything else (nil, forged, "clear") means no tag.
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
            reward = RewardMath.computeChestReward(rng, eggCount, "run"), -- BD-604: "run" may roll a secret species (flag on)
            shiny = traits.shiny, big = traits.big,
            genes = traits.genes, traitRollVersion = traits.traitRollVersion,
            source = {kind = "run", runId = runId, ordinal = i, originalEggId = eggId},
        })
    end
    sortByRarity(runEggs)
    -- BD-365: a new profile's first eggs are safe (never Cracked). Applied after the rarity sort so the FIRST eggs hatched
    -- are the safe ones; derived from the cached profile (hatched + already waiting eggs), no new persistent field.
    local safeLeft = FtueRules.safeEggsLeft(cached)
    for i = 1, math.min(safeLeft, #runEggs) do
        local egg = runEggs[i]
        if egg.genes and egg.genes.conditionId == "cracked" then
            local progress = ProfileRepository.progression(player)
            egg.genes = EggGenetics.roll(if progress then progress.conditionLevel else 0, rng, true)
            egg.traitRollVersion = "bd045-genes-v2"
        end
    end
    local leaseLost = false
    local invalid = false
    local duplicate = false
    local duplicateOutcome = nil
    local now = os.time()

    local ok, updated = true, cached
    if skipWrite then
        outcome.nestCount, outcome.nestFull, outcome.nestCrystals = 0, false, 0 -- what the transaction below would record for a run with nothing earned
        local memory = emptyRunsSettled[player]
        if not memory then
            memory = {order = {}, byId = {}}
            emptyRunsSettled[player] = memory
        end
        memory.byId[runId] = outcome
        table.insert(memory.order, runId)
        while #memory.order > EMPTY_RUN_MEMORY do memory.byId[table.remove(memory.order, 1) :: string] = nil end
    else
    ok, updated = retrySettlement("run settlement", function()
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
                -- BD-156 / BD-479: a nest found during weather carries THAT weather's tag (the weather when it was found, not at
                -- settlement); its eggs roll the same event mutation chance as run eggs when it is claimed. Clear stores nothing.
                table.insert(profileValue.eggNests, {nestId = nestId, droppedFromRun = runId,
                    size = RewardMath.nestSize(nestId), luck = 1, state = "waiting", weatherId = RewardMath.nestWeatherId(nestWeather, j)})
            end
            advanceNests(profileValue, now)
            outcome.nestCount = granted
            outcome.nestFull = granted < nestsEarned
            -- Owner 2026-10-16: every nest without a free spot converts to crystals now (same exactly-once transform).
            outcome.nestCrystals = (nestsEarned - granted) * Config.NestOverflowCrystals

            local progress = ProgressionRules.upgrade(profileValue)
            progress.crystals = math.min(ProgressionConfig.MaxCrystals, progress.crystals + outcome.crystals + (outcome.nestCrystals or 0))
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
    end

    if not ok or updated == nil then
        if leaseLost then
            handleLeaseLost(player)
            return false, nil, "lease_lost"
        end
        if invalid then return false, nil, "invalid_profile" end
        player:SetAttribute("ProfileState", "SaveFailed")
        -- BD-359: keep what the retry window could not commit; the renew tick tries again (same run id, exactly once).
        if profiles[player] then
            settlementStats.failedWindows += 1
            pendingSettlements[player] = {runId = runId, catchScore = catchScore, eggEvents = eggEvents, runSeconds = runSeconds, nestWeather = nestWeather}
        end
        return false, nil, "save_failed"
    end

    local pendingRun = pendingSettlements[player]
    if pendingRun and pendingRun.runId == runId then pendingSettlements[player] = nil end
    if not skipWrite then
        adopt(player, updated)
        if profiles[player] then syncAttributes(player, profiles[player]) end
    end
    local committedOutcome = if duplicate then duplicateOutcome else outcome
    if committedOutcome then
        PrivateState.set(player, "LastRewardText", runRewardText(committedOutcome))
        PrivateState.set(player, "LastRunCrystals", committedOutcome.crystals or 0)
        PrivateState.set(player, "LastRunCrystalBox", committedOutcome.crystalBox or 0)
        PrivateState.set(player, "LastRunEggCount", committedOutcome.eggCount or committedOutcome.chestCount or 0)
        PrivateState.set(player, "LastRunNestCount", committedOutcome.nestCount or 0)
        PrivateState.set(player, "LastRunNestFull", committedOutcome.nestFull == true)
        PrivateState.set(player, "LastRunNestCrystals", committedOutcome.nestCrystals or 0)
    end
    PrivateState.set(player, "LastSettledRunId", runId)
    if priorState == "SaveFailed" and player:GetAttribute("ProfileState") == "SaveFailed" then player:SetAttribute("ProfileState", "Loaded") end
    if Config.ObjectivesEnabled == true then -- BD-074: after the committed + adopted settlement (also for the in-call duplicate of a lost acknowledgement; the run id makes a replay count once)
        local progress = ProfileRepository.progression(player)
        objectives().recordRunSettled(player, runId, runSeconds, runEggs, if progress then ProgressionRules.level(progress) else nil, catchScore)
    end
    return true, committedOutcome, if duplicate then "duplicate" else "committed"
end

-- Number of already-credited eggs whose reveal animation is still buffered in memory.
function ProfileRepository.pendingReveals(player: Player): number
    local buffered = revealBuffer[player]
    return if buffered then #buffered else 0
end

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
            reward = RewardMath.computeChestReward(rng, tier.rarityBoostEggs, "nest"), -- BD-604: a free nest may roll a secret species (flag on)
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
            handleLeaseLost(player)
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

-- Credits one queue egg (collection, identity, metrics), refills the queue and records
-- its operation. Returns the committed outcome or nil. Runs inside an UpdateAsync transform.
local function applyHatch(profileValue: any, chest: any, index: number, outcome: any, now: number, freshSpecies: {[string]: boolean}?)
    table.remove(profileValue.eggs, index)
    -- BD-604 (docs/149): an egg that carries a committed secret species hatches it, but only while the flag is on and its model slot is
    -- filled (otherwise the normally rolled species hatches, exactly as before). A failed Cracked egg hatches nothing, so it never
    -- reveals a secret (that roll is simply lost). The collection entry is created here, lazily, on the first secret hatch: a profile
    -- that never hatched a secret has no secret key.
    if Config.SecretSpeciesEnabled == true and outcome.secretSpeciesId ~= nil and not (chest.genes ~= nil and not chest.genes.hatchSuccess) then
        local secretId = secretSpecies().resolve(outcome)
        if secretId ~= nil then
            outcome.speciesId = secretId
            outcome.secret = true
            if profileValue.collection[secretId] == nil then profileValue.collection[secretId] = secretSpecies().newEntry() end
        end
    end
    local species = profileValue.collection[outcome.speciesId]
    if typeof(species) ~= "table" then return nil end
    if freshSpecies ~= nil and not (chest.genes ~= nil and not chest.genes.hatchSuccess) and not ownsAny(species) then freshSpecies[outcome.speciesId] = true end -- BD-074: BEFORE this egg is added (objective hook only; nothing persisted)
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
    if not outcome.failed then -- BD-436: permanent discovery log; first-time finds feed the hatch "NEW!" tag
        local fresh=ProgressionRules.discover(profileValue,chest.genes,mutationId)
        if next(fresh) then outcome.discovered=fresh end
    end
    outcome.eventMutationId=mutationId
    outcome.eventId=chest.eventId or "clear"
    outcome.big=chest.big == true
    outcome.shiny=chest.shiny == true
    outcome.eggId=chest.eggId
    if not outcome.failed then profileValue.metrics.rarest = math.max(profileValue.metrics.rarest, Config.SpeciesRarities[outcome.speciesId] or 0) end -- BD-604: a secret species is not a tier and never raises it

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
    PrivateState.set(player, "LastChestRewardText", string.format("%dx %s", committedOutcome.count, committedOutcome.speciesId))
    PrivateState.set(player, "LastChestEventMutation",committedOutcome.eventMutationId or "")
    PrivateState.set(player, "LastChestBig",committedOutcome.big == true)
    PrivateState.set(player, "LastChestShiny",committedOutcome.shiny == true)
    PrivateState.set(player, "LastChestGenesJson",HttpService:JSONEncode(committedOutcome.genes))
    PrivateState.set(player, "LastChestFailed",committedOutcome.failed==true)
    PrivateState.set(player, "LastChestNewJson",HttpService:JSONEncode(committedOutcome.discovered or {}))
    PrivateState.set(player, "LastClaimedChestId", chestId)
    RareHatchService.record(player, committedOutcome) -- BD-428: celebration + one rate-limited announcement, from the settled outcome
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
    local freshSpecies: {[string]: boolean}? = if Config.ObjectivesEnabled == true then {} else nil -- BD-074: only allocated while the flag is on

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
            if freshSpecies ~= nil then table.clear(freshSpecies) end -- a repeated transform starts from the stored profile again
            if not applyHatch(profileValue, chest, index, outcome, now, freshSpecies) then return nil end
            -- Hatch page: following ready run/nest eggs at the queue head commit in the same
            -- transaction (their rewards are precommitted, so nothing is rerolled).
            while #pageOutcomes < Config.HatchPageSize - 1 and chest.reward and chest.genes
                and (chest.kind == "run_egg" or chest.kind == "nest_egg") do
                local nextEgg = profileValue.eggs[1]
                if not nextEgg or not nextEgg.reward or not nextEgg.genes or now < nextEgg.readyAt
                    or (nextEgg.kind ~= "run_egg" and nextEgg.kind ~= "nest_egg") then break end
                local nextOutcome = applyHatch(profileValue, nextEgg, 1, table.clone(nextEgg.reward), now, freshSpecies)
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
            handleLeaseLost(player)
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
    -- BD-609: a retry after a LOST ACKNOWLEDGEMENT finds its own earlier commit and answers "duplicate", but the hatch page that commit
    -- credited is still ours to reveal (pageOutcomes survives from the pass that wrote it). So a duplicate buffers the page too when every
    -- outcome's operation record is in the adopted profile and no page is already waiting; a plain duplicate claim has no pageOutcomes.
    local pageBuffer = {}
    if #pageOutcomes > 0 and not (duplicateOutcome and revealBuffer[player] and #revealBuffer[player] > 0) then
        for _, pageOutcome in pageOutcomes do
            if not duplicateOutcome or findOperation(updated, "chest:" .. tostring(pageOutcome.eggId)) then
                table.insert(pageBuffer, {eggId = pageOutcome.eggId, outcome = pageOutcome})
            end
        end
    end
    if #pageBuffer > 0 then
        revealBuffer[player] = pageBuffer
        if profiles[player] then syncAttributes(player, profiles[player]) end
    end
    publishHatch(player, chestId, committedOutcome)
    if Config.ObjectivesEnabled == true and not duplicateOutcome then -- BD-074: after the committed claim; the head egg and its whole hatch page count once, here (the later buffered reveals do not)
        local opened = {outcome}
        for _, pageOutcome in pageOutcomes do table.insert(opened, pageOutcome) end
        objectives().recordHatched(player, opened, freshSpecies)
    end
    return true, committedOutcome, if duplicateOutcome then "duplicate" else "claimed"
end
end
