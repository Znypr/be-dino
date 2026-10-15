--!strict
-- Additive identity sidecar. No DataStore access, RNG, economy or cosmetic grants.
local Identity = {}
Identity.Version = 1
-- Worst-case Studio serialization measured ~938 KB/1,000 identities. Keep enough
-- room for the rest of the profile and fail closed until BD-057 adds compaction or
-- sharding. This guard never truncates the grouped legacy collection.
Identity.MaxInstances = 3000

local function copy(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for key, child in value do result[key] = copy(child) end
    return result
end
Identity.copy = copy

local function cosmetics()
    return {ownedAuraIds = {}, ownedTrailIds = {}, equippedAuraId = "", equippedTrailId = ""}
end

-- Sorted buckets make migration reproducible across callback retries and reconnects.
local function buckets(collection)
    local result = {}
    for speciesId, entry in collection do
        for _, stage in {"base", "gold", "diamond"} do
            result[speciesId .. "/" .. stage] = {speciesId = speciesId, stage = stage, count = entry[stage]}
        end
        -- Additive optional Emerald counter (BD-057 ladder 6/3/2): nil means 0.
        result[speciesId .. "/emerald"] = {speciesId = speciesId, stage = "emerald", count = if entry.emerald == nil then 0 else entry.emerald}
        for mutationId, count in entry.events or {} do
            result[speciesId .. "/event/" .. mutationId] = {speciesId = speciesId, stage = "base", count = count, mutationId = mutationId}
        end
        for key, variant in entry.variants or {} do
            local bucket = copy(variant)
            bucket.speciesId, bucket.stage = speciesId, "base"
            result[speciesId .. "/variant/" .. key] = bucket
        end
    end
    return result
end

local function record(id, bucketKey, bucket, origin)
    return {instanceId = id, bucketKey = bucketKey, speciesId = bucket.speciesId,
        stage = bucket.stage, genes = copy(bucket.genes), traitRollVersion = bucket.traitRollVersion, big = bucket.big or false,
        shiny = bucket.shiny or false, mutationId = bucket.mutationId or "",
        traitsKnown = bucket.genes ~= nil, origin = copy(origin), cosmetics = cosmetics()}
end

-- Returns a new sidecar or error, leaving the input profile entirely untouched.
-- Unknown legacy DNA/pattern/egg is deliberately absent, never rolled retroactively.
function Identity.reconcile(collection, existing, ownerKey)
    ownerKey = ownerKey or "fixture"
    local desired = buckets(collection)
    local total = 0
    for _, bucket in desired do
        local n = bucket.count
        if type(n) ~= "number" or n ~= n or n < 0 or n % 1 ~= 0 then return nil, "invalid_count" end
        total += n
    end
    if total > Identity.MaxInstances then return nil, "identity_capacity" end
    if existing ~= nil and (type(existing) ~= "table" or existing.version ~= Identity.Version
        or type(existing.instances) ~= "table" or type(existing.nextId) ~= "number"
        or existing.nextId < 1 or existing.nextId % 1 ~= 0) then return nil, "invalid_identity" end
    if existing and type(existing.eggs) ~= "table" then return nil, "invalid_eggs" end
    if existing and existing.fusions ~= nil and type(existing.fusions) ~= "table" then return nil, "invalid_fusion_ledger" end
    local state = copy(existing or {version = Identity.Version, ownerKey = ownerKey, nextId = 1, instances = {}, eggs = {}})
    if state.ownerKey ~= ownerKey then return nil, "wrong_owner" end
    local fusions = state.fusions or {}
    local ids = {}
    local fused = {}
    for id, instance in state.instances do
        if type(instance) == "table" and type(instance.origin) == "table" and instance.origin.kind == "fusion" then
            -- BD-057: fused outputs are identity-authoritative. Their grouped projection is the
            -- plain stage count; genes/traits are freshly rolled and need not match a bucket.
            local entry = fusions[instance.origin.operationId]
            if type(entry) ~= "table" or entry.resultId ~= id then return nil, "missing_fusion_ledger" end
            if instance.instanceId ~= id or instance.bucketKey ~= tostring(instance.speciesId) .. "/" .. tostring(instance.stage)
                or not desired[instance.bucketKey] or type(instance.genes) ~= "table"
                or type(instance.cosmetics) ~= "table" or type(instance.cosmetics.ownedAuraIds) ~= "table"
                or type(instance.cosmetics.ownedTrailIds) ~= "table" then return nil, "invalid_instance" end
            fused[id] = true
        elseif type(instance) ~= "table" or instance.instanceId ~= id or not desired[instance.bucketKey]
            or type(instance.cosmetics) ~= "table" or type(instance.cosmetics.ownedAuraIds) ~= "table"
            or type(instance.cosmetics.ownedTrailIds) ~= "table" or type(instance.origin) ~= "table" then return nil, "invalid_instance" end
        local sequence = tonumber(string.match(id, "/d:(%d+)$"))
        if not sequence or id ~= state.ownerKey .. "/d:" .. tostring(sequence) or sequence >= state.nextId then return nil, "invalid_sequence" end
        local bucket = desired[instance.bucketKey]
        if fused[id] then
            -- Validated above; skip grouped trait comparison.
        elseif instance.speciesId ~= bucket.speciesId or instance.stage ~= bucket.stage
            or instance.big ~= (bucket.big or false) or instance.shiny ~= (bucket.shiny or false)
            or instance.mutationId ~= (bucket.mutationId or "") then return nil, "trait_mismatch" end
        if not fused[id] and (instance.genes == nil) ~= (bucket.genes == nil) then return nil, "gene_mismatch" end
        if instance.genes and not fused[id] then
            for key, value in bucket.genes do if instance.genes[key] ~= value then return nil, "gene_mismatch" end end
            for key, value in instance.genes do if bucket.genes[key] ~= value then return nil, "gene_mismatch" end end
        end
        if instance.origin.kind == "hatch" then
            if not state.eggs[instance.origin.eggId] then return nil, "missing_origin" end
        elseif instance.origin.kind ~= "legacy_unknown" and not fused[id] then return nil, "unsupported_origin" end
        table.insert(ids, id)
    end
    -- Fused outputs are kept first so a grouped decrement (e.g. legacy Gold->Diamond)
    -- spends legacy copies; non-fused order is unchanged from the BD-060 contract.
    table.sort(ids, function(a, b)
        if (fused[a] == true) ~= (fused[b] == true) then return fused[a] == true end
        return a < b
    end)
    local counts = {}
    for _, id in ids do
        local instance = state.instances[id]
        local key = instance.bucketKey
        counts[key] = (counts[key] or 0) + 1
        -- Existing Build 020 conversion spends only plain buckets. Never erase cosmetics
        -- or a crafted fusion result; fail closed instead.
        if counts[key] > desired[key].count then
            if fused[id] or next(instance.cosmetics.ownedAuraIds) or next(instance.cosmetics.ownedTrailIds) then
                return nil, "protected_identity"
            end
            state.instances[id] = nil
        end
    end
    local keys = {}
    for key in desired do table.insert(keys, key) end
    table.sort(keys)
    for _, key in keys do
        for _ = (counts[key] or 0) + 1, desired[key].count do
            local id = state.ownerKey .. "/d:" .. tostring(state.nextId)
            state.nextId += 1 -- monotonic within an owner profile; never reuse consumed IDs
            if state.instances[id] then return nil, "identity_collision" end
            state.instances[id] = record(id, key, desired[key], {kind = "legacy_unknown"})
        end
    end
    -- Retain shared egg snapshots only while referenced by living individuals.
    -- Future fusion must archive referenced parents/eggs in its transaction ledger first.
    local referenced = {}
    for _, instance in state.instances do
        if instance.origin.kind == "hatch" then referenced[instance.origin.eggId] = true end
    end
    -- The fusion ledger archives consumed parents' original eggs (BD-057 lineage).
    for _, entry in fusions do
        if type(entry) == "table" and type(entry.parentEggIds) == "table" then
            for _, eggId in entry.parentEggIds do referenced[eggId] = true end
        end
    end
    for eggId in state.eggs do if not referenced[eggId] then state.eggs[eggId] = nil end end
    return state
end

-- Call inside the same transaction as grouped hatch credit, before reconciliation.
-- Egg payload stored once even when one egg yields three distinct dinosaurs.
function Identity.hatch(state, egg, speciesId, count, bucketKey)
    if count == 0 then return {} end
    if type(count) ~= "number" or count < 1 or count > 3 or count % 1 ~= 0 then error("invalid hatch count") end
    local originId = egg.eggId
    local saved = state.eggs[originId]
    if saved then error("egg already credited") end
    local eggCopy = copy(egg)
    state.eggs[originId] = eggCopy
    local ids = {}
    for _ = 1, count do
        local id = state.ownerKey .. "/d:" .. tostring(state.nextId)
        state.nextId += 1
        assert(state.instances[id] == nil, "identity collision")
        state.instances[id] = record(id, bucketKey, {speciesId = speciesId, stage = "base",
            genes = egg.genes, big = egg.big, shiny = egg.shiny, mutationId = egg.mutationId, traitRollVersion = egg.traitRollVersion},
            {kind = "hatch", eggId = originId})
        table.insert(ids, id)
    end
    return ids
end

-- Data contract only: caller supplies already rolled output. Does not consume or roll.
-- Immediate parent snapshots retain traits and origins without recursively copying trees.
-- Compact (ladder 6/3/2): speciesId and stage are identical for every parent, so they are
-- stored once on the record (origin.parentStage). genes.patternId is stored on a parent snapshot
-- ONLY when it differs from the result (Gold takes the plurality pattern of mixed-pattern Base
-- donors); readers fall back to the result's speciesId/pattern.
Identity.MaxFusionParents = 6
function Identity.fusionRecord(id, output, parents, operationId, recipeVersion, oddsVersion)
    assert(type(id) == "string" and #id > 0 and #id <= 120, "invalid result ID")
    assert(type(operationId) == "string" and #operationId > 0 and #operationId <= 120, "invalid operation ID")
    assert(type(recipeVersion) == "string" and #recipeVersion > 0 and type(oddsVersion) == "string" and #oddsVersion > 0, "versioned recipe and odds required")
    assert(type(output.genes) == "table" and output.genes.patternId ~= nil, "fresh output genes required")
    assert(output.stage == "gold" or output.stage == "emerald" or output.stage == "diamond", "invalid result stage")
    assert(#parents >= 2 and #parents <= Identity.MaxFusionParents, "bounded immediate parents required")
    local snapshots, seen = {}, {}
    local parentStage = parents[1] and parents[1].stage
    for _, parent in parents do
        assert(not seen[parent.instanceId] and parent.instanceId ~= id, "duplicate/cyclic parent")
        assert(parent.speciesId == output.speciesId and parent.genes
            and type(parent.genes.patternId) == "string"
            and (parent.stage == "base" or parent.genes.patternId == output.genes.patternId), "matching species/pattern required")
        assert(parent.stage == parentStage, "single parent stage required")
        seen[parent.instanceId] = true
        local genes = copy(parent.genes)
        if parent.genes.patternId == output.genes.patternId then genes.patternId = nil end
        table.insert(snapshots, {instanceId = parent.instanceId, genes = genes, big = parent.big, shiny = parent.shiny,
            mutationId = parent.mutationId, origin = {kind = parent.origin.kind, eggId = parent.origin.eggId, operationId = parent.origin.operationId}})
    end
    -- Grouped compatibility projection: the plain stage bucket (BD-057).
    local result = record(id, output.speciesId .. "/" .. output.stage, output, {kind = "fusion", operationId = operationId,
        recipeVersion = recipeVersion, oddsVersion = oddsVersion, parentStage = parentStage, parents = snapshots})
    -- No parent cosmetic fields are copied into either output or lineage.
    return result
end
return Identity
