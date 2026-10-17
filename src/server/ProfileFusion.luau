--!strict
-- ProfileRepository part (docs/150): individual-dinosaur reads and the identity fusion transactions (BD-057 / BD-064).
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local CosmeticOwnership = shared.CosmeticOwnership
local DinosaurIdentity = shared.DinosaurIdentity
local EggGenetics = shared.EggGenetics
local FusionOdds = shared.FusionOdds
local IdentityFusion = shared.IdentityFusion
local PrivateState = shared.PrivateState
local ProgressionRules = shared.ProgressionRules
local admit = shared.admit
local adopt = shared.adopt
local handleLeaseLost = shared.handleLeaseLost
local identityAvailable = shared.identityAvailable
local identityPersistent = shared.identityPersistent
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local localPreview = shared.localPreview
local objectives = shared.objectives
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes
local trimOperations = shared.trimOperations

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
    return robuxLinked and (not Config.PaidRandomItemsEnabled or PrivateState.get(player, "PaidRandomEligible") ~= true)
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
    if Config.PerDinoCosmeticsEnabled == true then -- BD-059: itemized loss list for the confirm screen; absent when the flag is off
        result.cosmeticNotice = CosmeticOwnership.fusionNotice(quote, ProgressionRules.upgrade(cached), true)
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
            if type(result) == "table" and type(result.traits) == "table" then -- BD-436: the fused result is a discovery too
                ProgressionRules.discover(nextProfile, result.traits.genes, result.traits.mutationId)
            end
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
            handleLeaseLost(player)
            return false, nil, "lease_lost"
        end
        if failure then return false, nil, failure end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, nil, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    if Config.ObjectivesEnabled == true and not duplicate then objectives().recordFusionUse(player) end -- BD-074: after the committed fusion
    return true, committed, if duplicate then "duplicate" else "fused"
end
end
