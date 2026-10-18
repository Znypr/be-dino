--!strict
-- ProfileRepository part (docs/150): mini objectives transactions (BD-073, docs/66).
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local HttpService = shared.HttpService
local ProgressionConfig = shared.ProgressionConfig
local ProgressionRules = shared.ProgressionRules
local admit = shared.admitAs("ProfileObjectives") -- BD-650: the label names the service in the rate_limited count
local adopt = shared.adopt
local findOperation = shared.findOperation
local handleLeaseLost = shared.handleLeaseLost
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local objectivePending = shared.objectivePending
local objectiveRules = shared.objectiveRules
local ownSession = shared.ownSession
local ownsAny = shared.ownsAny
local profiles = shared.profiles
local requeueObjectiveBatch = shared.requeueObjectiveBatch
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes
local takeObjectiveBatch = shared.takeObjectiveBatch
local trimOperations = shared.trimOperations

------------------------------------------------------------------ BD-073 mini objectives (docs/66)
-- Inert while Config.ObjectivesEnabled ~= true: no function below reads or writes a profile, no pending queue exists, nothing is
-- required (ObjectiveRules is required lazily, so builds and offline harnesses without it are unaffected). The rules are pure
-- (shared/ObjectiveRules); this section only supplies the transactions: ownership of the lease, the claim token in
-- recentOperations, the wallet (progression.crystals, clamped to MaxCrystals), and the write budget (admit).
-- Gameplay progress is queued in memory (objectiveRecord) and committed in batches: inside the lease renew (BD-625: every
-- Config.ProfileRenewSeconds, no write of its own; ProfileRepository.renew), inside every claim, and inside the lease release, so a
-- leave or reconnect never drops it. objectiveFlush stays as an explicit one-write commit (tests, tools); nothing calls it on a timer.
-- takeObjectiveBatch / requeueObjectiveBatch live in ProfileRepository next to the queue (renew and release use them too).

-- Server hooks (BD-074) call this through ObjectiveService.record. Memory only; returns false when the event was not queued.
function ProfileRepository.objectiveRecord(player: Player, event: any): boolean
    if Config.ObjectivesEnabled ~= true or not ProfileRepository.isLoaded(player) then return false end
    local pending = objectivePending[player]
    if pending == nil then pending = {} objectivePending[player] = pending end
    return objectiveRules().queue(pending :: any, event)
end

-- OB2 (docs/115): the player's client says it opened a menu ("seen"). The server accepts it only for a catalogue row that declares
-- that id (T9 "fusion_menu"), only once per profile (the stored/pending progress is checked first, so a repeat queues nothing) and
-- only after the player owns at least one dino. It queues the row's own event with a fixed event id; the client sends no amount.
-- Returns ok, status: seen | already_seen | no_dino | unknown_objective | queue_full | disabled | profile_not_loaded | newer_version.
function ProfileRepository.objectiveSeen(player: Player, seenId: any): (boolean, string)
    if Config.ObjectivesEnabled ~= true then return false, "disabled" end
    if not ProfileRepository.isLoaded(player) then return false, "profile_not_loaded" end
    local rules = objectiveRules()
    local entry = rules.seenEntry(seenId)
    if entry == nil then return false, "unknown_objective" end
    local cached = profiles[player]
    local owns = false
    if typeof(cached.collection) == "table" then
        for _, collected in cached.collection do
            if ownsAny(collected) or (typeof(collected) == "table" and typeof(collected.emerald) == "number" and collected.emerald > 0) then owns = true break end
        end
    end
    if not owns then return false, "no_dino" end
    local done, status = rules.seenDone(cached.objectives, seenId, os.time(), objectivePending[player])
    if status ~= "ok" then return false, status end
    if done then return true, "already_seen" end
    if not ProfileRepository.objectiveRecord(player, {kind = entry.event, amount = 1, id = rules.seenEventId(seenId)}) then return false, "queue_full" end
    return true, "seen"
end

-- Read-only (never writes, never rolls a window into the stored profile): the stored state plus the unflushed queue at os.time().
function ProfileRepository.objectiveView(player: Player): (any, string)
    if Config.ObjectivesEnabled ~= true then return nil, "disabled" end
    if not ProfileRepository.isLoaded(player) then return nil, "profile_not_loaded" end
    return objectiveRules().view(profiles[player].objectives, os.time(), objectivePending[player])
end

-- Commits the queued progress (one routine write, admit-limited). Safe to call any time; "nothing" when the queue is empty.
function ProfileRepository.objectiveFlush(player: Player): (boolean, string)
    if Config.ObjectivesEnabled ~= true then return false, "disabled" end
    if not ProfileRepository.isLoaded(player) then return false, "profile_not_loaded" end
    local queued = objectivePending[player]
    if queued == nil or #queued == 0 then return true, "nothing" end
    if not admit(player) then return false, "rate_limited" end
    local batch = takeObjectiveBatch(player)
    local batchId = HttpService:GenerateGUID(false)
    local now = os.time()
    local denied = "save_failed"
    local leaseLost = false
    local ok, updated = retry("objectives", function()
        return store:UpdateAsync(keyFor(player), function(profile)
            leaseLost = false
            if not isValidProfile(profile) then denied = "invalid_profile" return nil end
            if not ownSession(profile) then leaseLost = true return nil end
            local applied, status = objectiveRules().applyToProfile(profile, batch, now, batchId)
            if not applied then denied = status return nil end
            profile.revision += 1
            profile.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profile
        end)
    end)
    if not ok or updated == nil then
        if leaseLost then handleLeaseLost(player) return false, "lease_lost" end
        if denied ~= "newer_version" then requeueObjectiveBatch(player, batch) end -- a newer build's field is never touched: drop, do not loop
        if not ok then player:SetAttribute("ProfileState", "SaveFailed") return false, "save_failed" end
        return false, denied
    end
    adopt(player, updated)
    return true, "flushed"
end

-- Claim exactly once. The ONLY client inputs are the objective id and an opaque token; reward, windows and progress are server
-- state. Same token + same id again = the stored outcome (status "duplicate", nothing granted); a new token for a finished claim
-- = "already_claimed". Returns ok, status, outcome ({id, status, crystals, xp}).
function ProfileRepository.objectiveClaim(player: Player, id: any, token: any): (boolean, string, any)
    if Config.ObjectivesEnabled ~= true then return false, "disabled", nil end
    if not ProfileRepository.isLoaded(player) then return false, "profile_not_loaded", nil end
    local rules = objectiveRules()
    if typeof(token) ~= "string" or #token < 1 or #token > rules.Config.ClaimTokenMax then return false, "invalid_token", nil end
    if typeof(id) ~= "string" or rules.Config.ById[id] == nil then return false, "unknown_objective", nil end
    if not admit(player) then return false, "rate_limited", nil end
    local operationId = "objective:" .. token
    local batch = takeObjectiveBatch(player)
    local now = os.time()
    local denied = "save_failed"
    local leaseLost, duplicate = false, false
    local outcome: any = nil
    local attempts = 0
    local ok, updated = retry("objective claim", function()
        attempts += 1
        return store:UpdateAsync(keyFor(player), function(profile)
            leaseLost, duplicate = false, false
            if not isValidProfile(profile) then denied = "invalid_profile" return nil end
            if not ownSession(profile) then leaseLost = true return nil end
            local existing = findOperation(profile, operationId)
            if existing then
                if typeof(existing.outcome) ~= "table" or existing.outcome.id ~= id then denied = "token_conflict" return nil end
                outcome, duplicate = existing.outcome, true
                return profile
            end
            local progress = ProgressionRules.upgrade(profile)
            local claimed, status, grant = rules.claimOnProfile(profile, progress, id, batch, now, ProgressionConfig.MaxCrystals)
            if not claimed then denied = status return nil end
            outcome = {id = id, status = status, crystals = grant.crystals, xp = grant.xp}
            profile.revision += 1
            profile.session.expiresAt = now + Config.ProfileLeaseSeconds
            table.insert(profile.recentOperations, {id = operationId, kind = "objective", outcome = outcome})
            trimOperations(profile)
            return profile
        end)
    end)
    -- A duplicate found on a RETRY of this very call is our own earlier commit (lost acknowledgement): it already applied the batch.
    local consumed = ok and updated ~= nil and (not duplicate or attempts > 1)
    if not consumed then requeueObjectiveBatch(player, batch) end
    if not ok then player:SetAttribute("ProfileState", "SaveFailed") return false, "save_failed", nil end
    if leaseLost and updated == nil then handleLeaseLost(player) return false, "lease_lost", nil end
    if updated == nil then return false, denied, nil end
    if player.Parent then adopt(player, updated) end
    if player.Parent and profiles[player] then syncAttributes(player, profiles[player]) end
    return true, if duplicate and attempts == 1 then "duplicate" else outcome.status, outcome
end
end
