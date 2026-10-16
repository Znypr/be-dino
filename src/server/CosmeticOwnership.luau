--!strict
-- BD-059 phase 1 (docs/121): per-dino aura/trail ownership, legacy account purchases grandfathered.
-- Pure module: no DataStore, RNG, remotes, currencies, Robux or PolicyService. Nothing here writes a profile by itself;
-- callers decide when (not wired to any shop or remote in phase 1). Flag off = exactly the old account-wide behaviour.
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

-- Warning data for the (future) Fusion Menu. Itemises what the donors' OWN cosmetics lose (the existing quote lossManifest
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
