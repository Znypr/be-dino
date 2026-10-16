--!strict
-- BD-360: owner-only player state. Player attributes replicate to EVERY client, so the large or sensitive values
-- (collection, egg and nest queues, crystals, settings, run summary) travel by RemoteEvent to their owner only.
-- This module is the pure core shared by the server sender and the client cache: the classification table, the
-- coalescing buffer, and the snapshot/delta messages. Docs: docs/112-private-state.md.
local Core = {}

Core.CoalesceSeconds = 0.2 -- changes made inside one window leave as one message

-- PRIVATE: only the owner needs it. Never set as a Player attribute (tools/verify_private_state.py enforces this).
local PRIVATE = {
    -- inventory and progression
    "QaOverlay", -- BD-085 owner phone QA overlay gate
    "CollectionJson", "ProgressionJson", "SettingsJson", "RevealSkipJson",
    "Crystals", "AccountXP", "PlaySeconds", "RarestCaught", "RobuxSpent", "ProfileRevision",
    "CompyCopies", "CompyGold", "TriceratopsCopies", "TriceratopsGold", "TyrannosaurusCopies", "TyrannosaurusGold",
    -- egg and nest queues
    "ChestQueueJson", "NestsJson", "PendingChestGrants", "ActiveChestCount", "BankedRunEggCount", "QueuedEggsWaiting",
    "NextChestId", "NextChestReadyAt", "RunStartBlocked",
    -- run and hatch summaries
    "LastChestBig", "LastChestShiny", "LastChestFailed", "LastChestGenesJson", "LastChestRewardText", "LastChestEventMutation",
    "LastClaimedChestId", "LastSettledRunId", "LastRewardText", "LastRunCrystals", "LastRunCrystalBox", "LastRunEggCount", "LastRunNestCount", "LastRunNestFull", "LastRunNestCrystals",
    -- owner-only multipliers and policy flags
    "GrowthMultiplier", "SpeedMultiplier", "LootMultiplier", "ColourGrowthPercent", "StudioTestWallet", "PaidRandomEligible",
}

-- PUBLIC: other clients (or the loading screen and admin hooks) may read it, or it is a tiny status string/number.
-- "render" = needed to draw or rank another player; "status" = tiny diagnostic/test hook (docs/79), accepted leak.
local PUBLIC: {[string]: string} = {
    EquippedSpeciesId = "render", EquippedBig = "render", EquippedShiny = "render", EquippedGenesJson = "render",
    EquippedEventMutation = "render", EquippedAura = "render", AccountLevel = "render",
    ProfileState = "state", ProfileMode = "state", CharacterState = "state", Location = "state", WorldReady = "state",
    IsAdmin = "state", JoinedAt = "state", HubStation = "state",
    LastRunId = "run", LastRunEndAt = "run", LastRunEndReason = "run", LastRunCatchScore = "run", LastRunGrowthScore = "run",
    LastNestClaimAt = "status", LastExitStatusAt = "status", LastMutationToken = "status", LastPredatorUserId = "status", LeapReadyAt = "status",
    LastBiteStatus = "status", LastChestClaimStatus = "status", LastChestTestGrantStatus = "status", LastCollectionGrantStatus = "status",
    LastCrystalStatus = "status", LastEquipStatus = "status", LastExitStatus = "status", LastLeapStatus = "status",
    LastMutationSetupStatus = "status", LastMutationStatus = "status", LastNestClaimStatus = "status", LastRunStartStatus = "status",
    LastSettlementProbe = "status", MovementSecurityStatus = "status", LeapRejectCount = "status", FallRecoveries = "status", ArtPreviewStatus = "status", MovementRejectCount = "status",
}

Core.Private = {} :: {[string]: boolean}
for _, name in PRIVATE do Core.Private[name] = true end
Core.Public = PUBLIC
Core.PrivateNames = PRIVATE

-- "private", "public", or nil (unclassified: the static check fails the build on those).
function Core.classify(name: string): string?
    if Core.Private[name] then return "private" end
    if PUBLIC[name] then return "public" end
    return nil
end

function Core.isPrivate(name: string): boolean return Core.Private[name] == true end

-- Rough wire size of a value in bytes (strings dominate; used by tests and the diagnostics line).
function Core.bytes(value: any): number
    local t = typeof(value)
    if t == "string" then return #value + 2 end
    if t == "number" then return 8 end
    if t == "boolean" then return 1 end
    if t == "table" then
        local n = 4
        for k, v in value do n += Core.bytes(k) + Core.bytes(v) end
        return n
    end
    return 0
end

-- Server side: one buffer per player. dirty keeps the ORDER of the sets, because the client reacts to
-- LastClaimedChestId only after the LastChest* values beside it were set.
export type Buffer = {values: {[string]: any}, sent: {[string]: any}, dirty: {string}, queued: {[string]: boolean}, seq: number, ready: boolean, scheduled: boolean}

function Core.newBuffer(): Buffer
    return {values = {}, sent = {}, dirty = {}, queued = {}, seq = 0, ready = false, scheduled = false}
end

-- Returns true when the value changed and a send is now due.
function Core.set(buffer: Buffer, name: string, value: any): boolean
    if buffer.values[name] == value then return false end
    buffer.values[name] = value
    if buffer.queued[name] == nil then
        buffer.queued[name] = true
        table.insert(buffer.dirty, name)
    end
    return true
end

function Core.snapshotMessage(buffer: Buffer): any
    buffer.seq += 1
    local data = {}
    for name, value in buffer.values do data[name] = value end
    buffer.sent = table.clone(buffer.values)
    buffer.dirty, buffer.queued = {}, {}
    return {k = "s", v = buffer.seq, d = data}
end

-- A delta holds only what really differs from the last message sent (a value set back to what the client has is dropped).
function Core.deltaMessage(buffer: Buffer): any?
    local order, data, removed = {}, {}, {}
    for _, name in buffer.dirty do
        local value = buffer.values[name]
        if value ~= buffer.sent[name] then
            table.insert(order, name)
            if value == nil then table.insert(removed, name) else data[name] = value end
            buffer.sent[name] = value
        end
    end
    buffer.dirty, buffer.queued = {}, {}
    if #order == 0 then return nil end
    buffer.seq += 1
    return {k = "d", v = buffer.seq, o = order, d = data, x = if #removed > 0 then removed else nil}
end

-- Client side cache. apply returns the names that changed, in set order, or "gap" when a delta was missed (ask for a snapshot).
export type Cache = {values: {[string]: any}, seq: number, received: boolean}

function Core.newCache(): Cache
    return {values = {}, seq = 0, received = false}
end

function Core.apply(cache: Cache, message: any): ({string}, string?)
    if typeof(message) ~= "table" then return {}, "bad" end
    local changed: {string} = {}
    if message.k == "s" and typeof(message.d) == "table" and typeof(message.v) == "number" then
        for name, value in message.d do
            if Core.isPrivate(name) and cache.values[name] ~= value then table.insert(changed, name) end
        end
        for name in cache.values do
            if message.d[name] == nil then table.insert(changed, name) end
        end
        table.sort(changed)
        local nextValues = {}
        for name, value in message.d do if Core.isPrivate(name) then nextValues[name] = value end end
        cache.values, cache.seq, cache.received = nextValues, message.v, true
        return changed, nil
    end
    if message.k == "d" and typeof(message.d) == "table" and typeof(message.o) == "table" and typeof(message.v) == "number" then
        if not cache.received or message.v ~= cache.seq + 1 then
            if message.v <= cache.seq then return {}, nil end -- an old duplicate
            return {}, "gap"
        end
        cache.seq = message.v
        for name, value in message.d do
            if Core.isPrivate(name) then cache.values[name] = value end
        end
        if typeof(message.x) == "table" then
            for _, name in message.x do cache.values[name] = nil end
        end
        for _, name in message.o do
            if typeof(name) == "string" and Core.isPrivate(name) then table.insert(changed, name) end
        end
        return changed, nil
    end
    return {}, "bad"
end

return Core
