--!strict
-- BD-059 (docs/121): per-dino aura/trail ownership, legacy account purchases grandfathered.
-- Pure module: no DataStore, RNG, remotes or Robux. Phase 2: apply() runs INSIDE ProfileRepository.progressionAction's
-- UpdateAsync callback (one atomic, token-idempotent write) and view() feeds reads. Flag off = exactly the old account-wide
-- behaviour (ProfileRepository never calls apply/view).
local Own = {}

local function sorted(set: any): {string}
    local list = {}
    if type(set) == "table" then
        for id, owned in set do if owned == true and type(id) == "string" then table.insert(list, id) end end
    end
    table.sort(list)
    return list
end

local function has(list: {string}, id: string): boolean
    return table.find(list, id) ~= nil
end

-- Account-wide purchases already stored in profile.progression (Build 020). Read only; never edited by this module.
function Own.legacy(progression: any)
    local p = if type(progression) == "table" then progression else {}
    return {auraIds = sorted(p.auras), trailIds = sorted(p.trails)}
end

-- What one dino may wear. enabled=false: the legacy account sets only (today's behaviour).
-- enabled=true: the dino's own purchases plus the grandfathered legacy sets (kept account-wide, see docs/121 section 3).
function Own.usable(progression: any, instance: any, enabled: boolean)
    local legacy = Own.legacy(progression)
    if not enabled then
        return {auraIds = legacy.auraIds, trailIds = legacy.trailIds, ownAuraIds = {}, ownTrailIds = {}, legacy = legacy}
    end
    local c = if type(instance) == "table" and type(instance.cosmetics) == "table" then instance.cosmetics else {}
    local ownA, ownT = sorted(c.ownedAuraIds), sorted(c.ownedTrailIds)
    local auras, trails = table.clone(ownA), table.clone(ownT)
    for _, id in legacy.auraIds do if not has(auras, id) then table.insert(auras, id) end end
    for _, id in legacy.trailIds do if not has(trails, id) then table.insert(trails, id) end end
    table.sort(auras)
    table.sort(trails)
    return {auraIds = auras, trailIds = trails, ownAuraIds = ownA, ownTrailIds = ownT, legacy = legacy}
end

function Own.canEquip(progression: any, instance: any, kind: string, id: string, enabled: boolean): boolean
    if id == "" then return true end
    local u = Own.usable(progression, instance, enabled)
    if kind == "aura" then return has(u.auraIds, id) end
    if kind == "trail" then return has(u.trailIds, id) end
    return false
end

-- Copy-on-write grant of a purchase to ONE dino (for the later shop phase). Idempotent. Returns nil, reason on failure.
-- Never touches progression.auras/trails, so rolling the flag back loses nothing.
function Own.grant(state: any, instanceId: string, kind: string, id: string, enabled: boolean)
    if not enabled then return nil, "per_dino_disabled" end
    if type(state) ~= "table" or type(state.instances) ~= "table" or type(id) ~= "string" or id == "" then return nil, "invalid_request" end
    local instance = state.instances[instanceId]
    if type(instance) ~= "table" or type(instance.cosmetics) ~= "table" then return nil, "unknown_instance" end
    local field = if kind == "aura" then "ownedAuraIds" elseif kind == "trail" then "ownedTrailIds" else nil
    if field == nil or type(instance.cosmetics[field]) ~= "table" then return nil, "invalid_request" end
    if instance.cosmetics[field][id] == true then return state, "already_owned" end
    local out = table.clone(state)
    out.instances = table.clone(state.instances)
    local inst = table.clone(instance)
    inst.cosmetics = table.clone(instance.cosmetics)
    inst.cosmetics[field] = table.clone(instance.cosmetics[field])
    inst.cosmetics[field][id] = true
    out.instances[instanceId] = inst
    return out, "granted"
end


local StageKeys = {"/base", "/gold", "/emerald", "/diamond"}

-- The "equipped dino" is a collection stack (species + variantKey); purchases bind to ONE instance of that stack: the lowest
-- instance sequence (deterministic across retries and reconnects). nil when the sidecar has no matching instance.
function Own.equippedInstanceId(state: any, speciesId: any, variantKey: any): string?
    if type(state) ~= "table" or type(state.instances) ~= "table" or type(speciesId) ~= "string" then return nil end
    local keys = {}
    if type(variantKey) == "string" then table.insert(keys, speciesId .. "/variant/" .. variantKey)
    else for _, stage in StageKeys do table.insert(keys, speciesId .. stage) end end
    for _, bucketKey in keys do
        local best, bestSeq = nil, math.huge
        for id, inst in state.instances do
            if type(inst) == "table" and inst.bucketKey == bucketKey and type(id) == "string" then
                local seq = tonumber(string.match(id, "/d:(%d+)$")) or math.huge
                if best == nil or seq < bestSeq or (seq == bestSeq and id < best) then best, bestSeq = id, seq end
            end
        end
        if best then return best end
    end
    return nil
end

local function withEquipped(state: any, instanceId: string, field: string, id: string)
    local out = table.clone(state)
    out.instances = table.clone(state.instances)
    local inst = table.clone(state.instances[instanceId])
    inst.cosmetics = table.clone(inst.cosmetics)
    inst.cosmetics[field] = id
    out.instances[instanceId] = inst
    return out
end

-- Per-dino shop action on the LIVE profile (called inside the progressionAction UpdateAsync callback, which owns a private
-- copy). ctx = {rules = ProgressionRules, config = ProgressionConfig, identityOk = boolean}. Returns applied, status, instanceId.
-- Buy: price/level exactly as ProgressionRules.apply, ownership bound to the equipped dino, progression.auras/trails never edited.
-- Equip: only own + legacy items; a legacy item sets the account equip (as today) and clears this dino's own choice; "" clears both.
function Own.apply(profile: any, action: string, id: string, ctx: any): (boolean, string, string?)
    local kind = if action == "buyAura" or action == "equipAura" then "aura" else "trail"
    local buying = action == "buyAura" or action == "buyTrail"
    local state = profile.dinosaurIdentity
    if ctx.identityOk ~= true or type(state) ~= "table" then return false, "no_dino_instance" end
    -- BD-606: ctx.equipped = the dino actually played (a secret species is stored beside a fallback pair, ProfileRepository.equippedOf)
    local equipped = ctx.equipped
    local instanceId = Own.equippedInstanceId(state, if equipped then equipped.speciesId else profile.equippedSpeciesId, if equipped then equipped.variantKey else profile.equippedVariantKey)
    if not instanceId then return false, "no_dino_instance" end
    local rules = ctx.rules
    local p = rules.upgrade(profile)
    local instance = state.instances[instanceId]
    local usable = Own.usable(p, instance, true)
    local list = if kind == "aura" then usable.auraIds else usable.trailIds
    if buying then
        local item = rules.item(if kind == "aura" then ctx.config.Auras else ctx.config.Trails, id)
        if not item then return false, "unknown_item" end
        if has(list, id) then return false, "already_owned" end
        if kind == "trail" and rules.level(p) < item.level then return false, "level_locked" end
        if p.crystals < item.price then return false, "insufficient_crystals" end
        local nextState, why = Own.grant(state, instanceId, kind, id, true)
        if not nextState then return false, why :: string end
        p.crystals -= item.price
        profile.dinosaurIdentity = nextState
        return true, "purchased", instanceId
    end
    local field = if kind == "aura" then "equippedAuraId" else "equippedTrailId"
    local legacyField = if kind == "aura" then "equippedAura" else "equippedTrail"
    if id == "" then
        profile.dinosaurIdentity = withEquipped(state, instanceId, field, "")
        p[legacyField] = ""
        return true, "equipped", instanceId
    end
    if not has(list, id) then return false, "not_owned" end
    if has(if kind == "aura" then usable.legacy.auraIds else usable.legacy.trailIds, id) then
        p[legacyField] = id
        profile.dinosaurIdentity = withEquipped(state, instanceId, field, "")
    else
        profile.dinosaurIdentity = withEquipped(state, instanceId, field, id)
    end
    return true, "equipped", instanceId
end

-- Read view of progression for the equipped dino: auras/trails = own + legacy, equipped = this dino's choice else the account
-- (legacy) equip. Never stored; the real progression stays the rollback-safe legacy view. Returns the input when no instance.
function Own.view(progression: any, state: any, speciesId: any, variantKey: any)
    local instanceId = Own.equippedInstanceId(state, speciesId, variantKey)
    if not instanceId then return progression end
    local instance = state.instances[instanceId]
    local u = Own.usable(progression, instance, true)
    local out = table.clone(progression)
    out.auras, out.trails = {}, {}
    for _, id in u.auraIds do out.auras[id] = true end
    for _, id in u.trailIds do out.trails[id] = true end
    local c = instance.cosmetics
    local ea = if type(c) == "table" and type(c.equippedAuraId) == "string" then c.equippedAuraId else ""
    local et = if type(c) == "table" and type(c.equippedTrailId) == "string" then c.equippedTrailId else ""
    out.equippedAura = if ea ~= "" and out.auras[ea] then ea else progression.equippedAura
    out.equippedTrail = if et ~= "" and out.trails[et] then et else progression.equippedTrail
    return out
end

-- Warning data for the Fusion Menu (quote.cosmeticNotice when the flag is on). Itemises what the donors' OWN cosmetics lose (the existing quote lossManifest
-- already lists them per donor) and states that legacy account-wide purchases are NOT consumed.
function Own.fusionNotice(quote: any, progression: any, enabled: boolean)
    local lostA, lostT, seenA, seenT = {}, {}, {}, {}
    if type(quote) == "table" and type(quote.lossManifest) == "table" then
        for _, entry in quote.lossManifest do
            for _, id in entry.auraIds or {} do if not seenA[id] then seenA[id] = true table.insert(lostA, id) end end
            for _, id in entry.trailIds or {} do if not seenT[id] then seenT[id] = true table.insert(lostT, id) end end
        end
    end
    table.sort(lostA)
    table.sort(lostT)
    local legacy = Own.legacy(progression)
    return {enabled = enabled, irreversible = #lostA + #lostT > 0, lostAuraIds = lostA, lostTrailIds = lostT,
        legacyKept = enabled, legacyAuraIds = legacy.auraIds, legacyTrailIds = legacy.trailIds}
end

return Own
