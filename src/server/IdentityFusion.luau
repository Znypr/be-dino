--!strict
-- BD-057 Phase 1: server-authoritative pattern fusion over the BD-060 identity sidecar.
-- Pure module: no DataStore, RNG, remotes, currencies or UI. Callers run `apply` inside
-- one UpdateAsync transform with an outcome precommitted by `prepareOutcome`.
--
-- Trait randomness is NOT owned here. A roller `{version: string, roll(summary, patternId)}`
-- is injected. No production roller exists until BD-064 approves probabilities, so the
-- only roller in the repository lives in the offline test harness.
local Identity = require(script.Parent.DinosaurIdentity)

local Fusion = {}
Fusion.Version = "bd057-ladder-15-4-2"

-- OWNER DECISION 2026-10-14 (supersedes 50/10/3 of 2026-10-13 and the 10-donor Gold rule; docs/57, docs/58):
-- same species + same pattern at every tier, guaranteed, consumes ALL donors and
-- creates ONE new individual. Gold = 15 Base, Emerald = 4 Gold, Diamond = 2 Emerald.
-- The donor count is per recipe; nothing else may hard-code it.
Fusion.Ladder = {"base", "gold", "emerald", "diamond"}
Fusion.Recipes = {
    gold = {targetStage = "gold", sourceStage = "base", donorCount = 15, version = "gold-same-species-pattern-15-v1"},
    emerald = {targetStage = "emerald", sourceStage = "gold", donorCount = 4, version = "emerald-same-species-pattern-4-v1"},
    diamond = {targetStage = "diamond", sourceStage = "emerald", donorCount = 2, version = "diamond-same-species-pattern-2-v1"},
}
-- Largest approved donor count (remote/list bounds derive from this).
Fusion.MaxDonorCount = 15
-- Stages the grouped collection can represent. Emerald uses the additive optional
-- collection[species].emerald counter (nil == 0).
Fusion.GroupedProjection = {gold = true, emerald = true, diamond = true}

-- Byte preflight for the sidecar after fusion. BD-060 measured ~938 KB per 1,000
-- worst-case identities and a 4 MiB DataStore value limit; this leaves ~1 MiB for the
-- rest of the profile. Development safety ceiling, not a balance value.
Fusion.MaxSidecarBytes = 3200000
Fusion.MaxTokenLength = 80

local copy = Identity.copy

-- Deterministic, key-sorted serialization. Used for snapshots/digests, never persisted
-- as a security boundary on its own.
local function canonical(value): string
    local kind = type(value)
    if kind == "table" then
        local keys = {}
        for key in value do table.insert(keys, key) end
        table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
        local parts = {}
        for _, key in keys do
            table.insert(parts, string.format("%q", tostring(key)) .. "=" .. canonical(value[key]))
        end
        return "{" .. table.concat(parts, ",") .. "}"
    elseif kind == "string" then
        return string.format("%q", value)
    elseif kind == "number" then
        return string.format("%.17g", value)
    end
    return tostring(value)
end
Fusion.canonical = canonical

-- Two independent 32-bit FNV-1a lanes; equality checks only, not cryptographic.
-- prime = 2^24 + 403, multiplied in two parts to stay exact in doubles.
local function fnvStep(hash: number, byte: number): number
    local x = bit32.bxor(hash, byte)
    return bit32.band(bit32.lshift(x, 24) + x * 403, 0xffffffff)
end
local function digest(text: string): string
    local a, b = 2166136261, 3735928559
    for i = 1, #text do
        local byte = string.byte(text, i)
        a = fnvStep(a, byte)
        b = fnvStep(b, (byte + i) % 256)
    end
    return string.format("%08x%08x%x", a, b, #text)
end
Fusion.digest = digest

-- JSON-equivalent byte estimate (keys, quotes, separators). Approximates Roblox
-- HttpService:JSONEncode closely enough for a conservative preflight.
local function encodedSize(value): number
    local kind = type(value)
    if kind == "table" then
        local n = #value
        local isArray = true
        local count = 0
        for key in value do
            count += 1
            if type(key) ~= "number" or key < 1 or key > n or key % 1 ~= 0 then isArray = false end
        end
        if count == 0 then return 2 end
        local size = 2 + (count - 1)
        for key, child in value do
            if not isArray then size += encodedSize(tostring(key)) + 1 end
            size += encodedSize(child)
        end
        return size
    elseif kind == "string" then
        local escapes = 0
        for _ in string.gmatch(value, "[\"\\%c]") do escapes += 1 end
        return #value + 2 + escapes
    elseif kind == "number" then
        return #string.format("%.14g", value)
    elseif kind == "boolean" then
        return if value then 4 else 5
    end
    return 4
end
Fusion.encodedSize = encodedSize

local function sequence(id: string, ownerKey: string): number?
    local n = tonumber(string.match(id, "^(.*)/d:%d+$") == ownerKey and string.match(id, "/d:(%d+)$") or nil)
    return n
end

-- A fused donor's origin embeds up to 15 immutable parent snapshots; the quote digest
-- needs only the origin identity (kind/operation/versions), keeping quotes O(donors).
local function compactOrigin(origin)
    if type(origin) ~= "table" then return origin end
    local slim = {}
    for key, value in origin do if key ~= "parents" then slim[key] = value end end
    return slim
end

local function hasCosmetics(instance): boolean
    local c = instance.cosmetics
    return type(c) == "table" and (next(c.ownedAuraIds or {}) ~= nil or next(c.ownedTrailIds or {}) ~= nil
        or (c.equippedAuraId or "") ~= "" or (c.equippedTrailId or "") ~= "")
end

local function sortedKeys(set): {string}
    local list = {}
    for key, owned in set or {} do if owned then table.insert(list, key) end end
    table.sort(list)
    return list
end

-- Validates the exact selection against the current sidecar and freezes it.
-- Returns nil, reason on any problem. Never mutates `state`.
function Fusion.quote(state, ownerKey: string, targetStage: any, donorIds: any)
    if type(state) ~= "table" or state.version ~= Identity.Version or type(state.instances) ~= "table" then
        return nil, "identity_unavailable"
    end
    if state.ownerKey ~= ownerKey then return nil, "wrong_owner" end
    if type(targetStage) ~= "string" or not table.find(Fusion.Ladder, targetStage) or targetStage == "base" then
        return nil, "unknown_stage"
    end
    local recipe = Fusion.Recipes[targetStage]
    if not recipe or type(recipe.donorCount) ~= "number" or type(recipe.version) ~= "string" then
        return nil, "recipe_not_approved"
    end
    if type(donorIds) ~= "table" or #donorIds ~= recipe.donorCount then return nil, "wrong_donor_count" end
    local count = 0
    for _ in donorIds do count += 1 end
    if count ~= recipe.donorCount then return nil, "wrong_donor_count" end

    local seen, donors = {}, {}
    local speciesId, patternId = nil, nil
    for _, id in donorIds do
        if type(id) ~= "string" or #id < 1 or #id > 120 then return nil, "invalid_donor_id" end
        if seen[id] then return nil, "duplicate_donor" end
        seen[id] = true
        if sequence(id, ownerKey) == nil then return nil, "wrong_owner" end
        local instance = state.instances[id]
        if type(instance) ~= "table" then return nil, "donor_missing" end
        if instance.instanceId ~= id then return nil, "invalid_instance" end
        if instance.stage ~= recipe.sourceStage then return nil, "wrong_stage" end
        if instance.locked == true or instance.favorited == true then return nil, "donor_locked" end
        if instance.traitsKnown ~= true or type(instance.genes) ~= "table"
            or type(instance.genes.patternId) ~= "string" or instance.genes.patternId == "" then
            return nil, "missing_pattern"
        end
        speciesId = speciesId or instance.speciesId
        patternId = patternId or instance.genes.patternId
        if instance.speciesId ~= speciesId then return nil, "species_mismatch" end
        if instance.genes.patternId ~= patternId then return nil, "pattern_mismatch" end
        table.insert(donors, instance)
    end
    table.sort(donors, function(a, b) return a.instanceId < b.instanceId end)

    -- Neutral ingredient facts for a future BD-064 roller. Contains no probabilities.
    local summary = {speciesId = speciesId, patternId = patternId, targetStage = targetStage,
        donorCount = #donors, shinyCount = 0, bigCount = 0, mutationCounts = {}, colors = {}}
    local losses, sortedIds, snapshot = {}, {}, {}
    for _, d in donors do
        table.insert(sortedIds, d.instanceId)
        if d.shiny then summary.shinyCount += 1 end
        if d.big then summary.bigCount += 1 end
        if (d.mutationId or "") ~= "" then summary.mutationCounts[d.mutationId] = (summary.mutationCounts[d.mutationId] or 0) + 1 end
        table.insert(summary.colors, {primaryColorId = d.genes.primaryColorId, secondaryColorId = d.genes.secondaryColorId, blend = d.genes.blend})
        -- Exact frozen payload: any change to a donor (genes, traits, cosmetics,
        -- stage, protection) after quoting invalidates the quote.
        table.insert(snapshot, {instanceId = d.instanceId, bucketKey = d.bucketKey, stage = d.stage, speciesId = d.speciesId,
            genes = d.genes, big = d.big, shiny = d.shiny, mutationId = d.mutationId, cosmetics = d.cosmetics,
            locked = d.locked, favorited = d.favorited, origin = compactOrigin(d.origin)})
        -- Itemized irreversible loss: purchased looks AND valuable natural traits.
        local auras = sortedKeys(d.cosmetics and d.cosmetics.ownedAuraIds)
        local trails = sortedKeys(d.cosmetics and d.cosmetics.ownedTrailIds)
        local valuable = d.shiny == true or d.big == true or (d.mutationId or "") ~= ""
        if hasCosmetics(d) or valuable then
            table.insert(losses, {instanceId = d.instanceId, auraIds = auras, trailIds = trails,
                equippedAuraId = d.cosmetics and d.cosmetics.equippedAuraId or "",
                equippedTrailId = d.cosmetics and d.cosmetics.equippedTrailId or "",
                shiny = d.shiny == true, big = d.big == true, mutationId = d.mutationId or ""})
        end
    end
    local snapshotText = canonical(snapshot)
    return {
        targetStage = targetStage,
        recipeVersion = recipe.version,
        sourceStage = recipe.sourceStage,
        speciesId = speciesId,
        patternId = patternId,
        donorIds = sortedIds,
        summary = summary,
        lossManifest = losses,
        consentRequired = #losses > 0,
        consentDigest = digest(canonical(losses)),
        -- Identifies the request independent of donor contents (idempotency/conflicts).
        requestDigest = digest(canonical({targetStage = targetStage, donorIds = sortedIds})),
        -- Identifies the exact frozen donor payloads (stale-writer detection).
        quoteDigest = digest(snapshotText),
        snapshot = snapshotText,
    }
end

local function validTraits(traits, patternId: string, validateGenes): boolean
    if type(traits) ~= "table" or traits.stage ~= nil then return false end
    if type(traits.big) ~= "boolean" or type(traits.shiny) ~= "boolean" or type(traits.mutationId) ~= "string" then return false end
    local genes = traits.genes
    if type(genes) ~= "table" or genes.patternId ~= patternId then return false end
    if type(genes.primaryColorId) ~= "string" or type(genes.secondaryColorId) ~= "string"
        or genes.conditionId ~= nil or type(genes.blend) ~= "number"
        or genes.blend ~= genes.blend or genes.blend < 0 or genes.blend > 100 then return false end
    for key, value in genes do
        if type(key) ~= "string" or (type(value) ~= "string" and type(value) ~= "number" and type(value) ~= "boolean") then return false end
    end
    if validateGenes and not validateGenes(genes) then return false end
    return true
end

-- Call ONCE outside UpdateAsync. Retries reuse the returned outcome, so a write retry
-- can never reroll traits. The guaranteed stage comes from the recipe, never the roller.
function Fusion.prepareOutcome(quote, roller, validateGenes)
    if type(roller) ~= "table" or type(roller.version) ~= "string" or #roller.version == 0
        or type(roller.roll) ~= "function" then return nil, "odds_not_approved" end
    local ok, traits = pcall(roller.roll, copy(quote.summary), quote.patternId)
    if not ok or not validTraits(traits, quote.patternId, validateGenes) then return nil, "invalid_outcome" end
    traits = copy(traits)
    traits.genes.patternId = quote.patternId -- pattern is recipe-locked, not rolled
    return {oddsVersion = roller.version, requestDigest = quote.requestDigest,
        quoteDigest = quote.quoteDigest, targetStage = quote.targetStage, traits = traits}
end

-- Groups a donor's bucket key back to its grouped collection counter.
local function groupedCounter(entry, bucketKey: string, speciesId: string)
    local prefix = speciesId .. "/"
    if string.sub(bucketKey, 1, #prefix) ~= prefix then return nil end
    local rest = string.sub(bucketKey, #prefix + 1)
    if rest == "base" or rest == "gold" or rest == "emerald" or rest == "diamond" then
        return function() return entry[rest] or 0 end, function(n) entry[rest] = n end
    end
    local eventId = string.match(rest, "^event/(.+)$")
    if eventId then
        return function() return (entry.events or {})[eventId] end,
            function(n) entry.events[eventId] = n end
    end
    local variantKey = string.match(rest, "^variant/(.+)$")
    if variantKey then
        local variants = entry.variants or {}
        return function() local v = variants[variantKey] return v and v.count end,
            function(n) if n == 0 then variants[variantKey] = nil else variants[variantKey].count = n end end
    end
    return nil
end

-- Copy-on-write transaction body. Returns (newProfile, "fused", result) on success,
-- (originalProfile, "duplicate", result) on an idempotent replay, or (nil, reason)
-- on any failure. The passed profile is never mutated; returning nil from an
-- UpdateAsync transform aborts the write, so every failure is a full rollback.
function Fusion.apply(profile, ownerKey: string, request, outcome, now: number?)
    if type(profile) ~= "table" or type(profile.collection) ~= "table" then return nil, "invalid_profile" end
    if type(request) ~= "table" or type(request.token) ~= "string" or #request.token < 1
        or #request.token > Fusion.MaxTokenLength then return nil, "invalid_token" end
    local operationId = "fusion:" .. request.token
    local state = profile.dinosaurIdentity
    if type(state) ~= "table" then return nil, "identity_unavailable" end
    local ledger = state.fusions
    if ledger ~= nil and type(ledger) ~= "table" then return nil, "invalid_fusion_ledger" end

    local requestDigest = digest(canonical({targetStage = request.targetStage,
        donorIds = (function()
            local ids = {}
            for _, id in (if type(request.donorIds) == "table" then request.donorIds else {}) do table.insert(ids, tostring(id)) end
            table.sort(ids)
            return ids
        end)()}))
    local existing = ledger and ledger[operationId]
    if existing then
        if existing.requestDigest ~= requestDigest then return nil, "token_conflict" end
        return profile, "duplicate", copy(existing.outcome)
    end

    local quote, reason = Fusion.quote(state, ownerKey, request.targetStage, request.donorIds)
    if not quote then return nil, reason end
    if type(outcome) ~= "table" or outcome.requestDigest ~= quote.requestDigest then return nil, "invalid_outcome" end
    -- Stale writer: a donor changed between quote/roll and this transaction.
    if outcome.quoteDigest ~= quote.quoteDigest or request.quoteDigest ~= quote.quoteDigest then return nil, "stale_quote" end
    if quote.consentRequired and request.consentDigest ~= quote.consentDigest then return nil, "consent_required" end
    if not validTraits(outcome.traits, quote.patternId, nil) or outcome.targetStage ~= quote.targetStage then
        return nil, "invalid_outcome"
    end
    if not Fusion.GroupedProjection[quote.targetStage] then return nil, "projection_unsupported" end

    local nextProfile = copy(profile)
    local nextState = nextProfile.dinosaurIdentity
    nextState.fusions = nextState.fusions or {}
    local entry = nextProfile.collection[quote.speciesId]
    if type(entry) ~= "table" then return nil, "grouped_mismatch" end

    -- Consume every donor exactly once, keeping the grouped projection in lockstep.
    local parents, parentEggIds, parentOperationIds = {}, {}, {}
    for _, id in quote.donorIds do
        local donor = nextState.instances[id]
        local get, set = groupedCounter(entry, donor.bucketKey, quote.speciesId)
        local current = get and get()
        if type(current) ~= "number" or current < 1 then return nil, "grouped_mismatch" end
        set(current - 1)
        table.insert(parents, donor)
        if donor.origin and donor.origin.kind == "hatch" and not table.find(parentEggIds, donor.origin.eggId) then
            table.insert(parentEggIds, donor.origin.eggId) -- one entry per shared egg
        end
        if donor.origin and donor.origin.kind == "fusion" then table.insert(parentOperationIds, donor.origin.operationId) end
    end
    entry[quote.targetStage] = (entry[quote.targetStage] or 0) + 1

    -- Exactly one NEW individual; server-allocated ID from the persisted sequence.
    local resultId = nextState.ownerKey .. "/d:" .. tostring(nextState.nextId)
    nextState.nextId += 1
    if nextState.instances[resultId] then return nil, "identity_collision" end
    local traits = outcome.traits
    local built, result = pcall(Identity.fusionRecord, resultId, {
        speciesId = quote.speciesId, stage = quote.targetStage, genes = copy(traits.genes),
        big = traits.big, shiny = traits.shiny, mutationId = traits.mutationId,
        traitRollVersion = outcome.oddsVersion,
    }, parents, operationId, quote.recipeVersion, outcome.oddsVersion)
    if not built then return nil, "invalid_outcome" end
    for _, id in quote.donorIds do nextState.instances[id] = nil end
    nextState.instances[resultId] = result

    local committed = {operationId = operationId, resultId = resultId, targetStage = quote.targetStage,
        speciesId = quote.speciesId, patternId = quote.patternId, consumedIds = copy(quote.donorIds),
        recipeVersion = quote.recipeVersion, oddsVersion = outcome.oddsVersion, traits = copy(traits)}
    -- Durable, never-trimmed ledger: idempotent replay plus lineage that outlives the
    -- consumed parents (their egg snapshots stay referenced through parentEggIds).
    nextState.fusions[operationId] = {operationId = operationId, requestDigest = quote.requestDigest,
        quoteDigest = quote.quoteDigest, resultId = resultId, targetStage = quote.targetStage,
        speciesId = quote.speciesId, patternId = quote.patternId, recipeVersion = quote.recipeVersion,
        oddsVersion = outcome.oddsVersion, parentIds = copy(quote.donorIds), parentEggIds = parentEggIds,
        parentOperationIds = parentOperationIds, committedAt = now or 0, outcome = committed}

    -- Whole-state consistency check: grouped projection vs identities, ledger, eggs.
    local reconciled, reconcileReason = Identity.reconcile(nextProfile.collection, nextState, ownerKey)
    if not reconciled then return nil, reconcileReason end
    if encodedSize(reconciled) > Fusion.MaxSidecarBytes then return nil, "storage_limit" end
    nextProfile.dinosaurIdentity = reconciled
    return nextProfile, "fused", copy(committed)
end

-- Read-only lineage view for later Dino Details (BD-062). Resolves parent egg
-- snapshots from the ledger even after the parents were consumed.
function Fusion.lineage(state, operationId: string)
    local entry = type(state) == "table" and type(state.fusions) == "table" and state.fusions[operationId]
    if type(entry) ~= "table" then return nil end
    local eggs = {}
    for _, eggId in entry.parentEggIds do eggs[eggId] = copy(state.eggs[eggId]) end
    return {operationId = operationId, resultId = entry.resultId, parentIds = copy(entry.parentIds),
        parentOperationIds = copy(entry.parentOperationIds), recipeVersion = entry.recipeVersion,
        oddsVersion = entry.oddsVersion, parentEggs = eggs}
end

return Fusion
