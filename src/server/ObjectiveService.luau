--!strict
-- BD-073 (docs/66 section 7): server surface of the mini objectives. Behind Config.ObjectivesEnabled (false in every committed
-- build): while it is false start() returns at once, the ObjectiveAction remote does not exist, record() is a no-op and no
-- profile is ever read or written for objectives. No UI (BD-075). BD-074: the server code paths that commit a gameplay fact call
-- ObjectiveService.record(player, kind, amount, eventId, value) (or one of the recorders below) AFTER the commit, each behind the
-- same one-boolean flag check; the full objective-to-hook table is docs/66 section 18, enforced by tools/verify_objective_hooks.py.
--
-- ObjectiveAction (RemoteFunction in ReplicatedStorage.BeDinoRemotes), request shapes (anything else is "bad_request"):
--   {action = "view"}                         -> {ok = true, view = {...}}   (read-only)
--   {action = "claim", id = "T1", token = "<opaque, 1..80>"} -> {ok = true, status, grant = {crystals, xp}, view}
-- The client never sends progress, rewards, windows or amounts. Every response is a table; failures are {ok = false, reason}.
-- Reasons: bad_request, rate_limited, disabled, profile_not_loaded, invalid_token, unknown_objective, not_done, not_active,
-- already_claimed, token_conflict, newer_version, lease_lost, save_failed. Pure rules: shared/ObjectiveRules. Rewards are
-- PROVISIONAL Crystals/XP only (shared/ObjectiveConfig); never Robux, never random items.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local ObjectiveConfig = require(ReplicatedStorage.Shared.ObjectiveConfig)

local ObjectiveService = {}
ObjectiveService.MaxIdLength = 8

local repository: any = nil
local windows: {[any]: {startedAt: number, count: number}} = {}
local clock = os.clock

local Shapes = {
    view = {action = true},
    claim = {action = true, id = true, token = true},
}

local function fail(reason: string): any
    return {ok = false, reason = reason}
end

local function boundedString(value: any, maxLength: number): boolean
    return type(value) == "string" and #value >= 1 and #value <= maxLength
end

-- Fixed-window per-player limiter (PROVISIONAL ObjectiveConfig values), same shape as FusionService.
local function allowed(player: any): boolean
    local now = clock()
    local window = windows[player]
    if not window or now - window.startedAt >= ObjectiveConfig.RateWindowSeconds then
        window = {startedAt = now, count = 0}
        windows[player] = window
    end
    window.count += 1
    return window.count <= ObjectiveConfig.RequestsPerWindow
end

local function validate(request: any): string?
    if type(request) ~= "table" then return "bad_request" end
    local shape = Shapes[request.action]
    if type(request.action) ~= "string" or not shape then return "bad_request" end
    for key in request do
        if type(key) ~= "string" or not shape[key] then return "bad_request" end
    end
    if request.action == "claim" then
        if not boundedString(request.id, ObjectiveService.MaxIdLength) or not boundedString(request.token, ObjectiveConfig.ClaimTokenMax) then
            return "bad_request"
        end
    end
    return nil
end

local function handleAction(player: any, request: any)
    if request.action == "view" then
        local view, status = repository.objectiveView(player)
        if not view then return fail(status or "disabled") end
        return {ok = true, view = view}
    end
    local ok, status, outcome = repository.objectiveClaim(player, request.id, request.token)
    if not ok or type(outcome) ~= "table" then return fail(status or "save_failed") end
    local view = repository.objectiveView(player)
    return {ok = true, status = status, grant = {crystals = outcome.crystals, xp = outcome.xp}, view = view}
end

-- Entry point for OnServerInvoke (and offline tests). Never throws to the client.
function ObjectiveService.handle(player: any, request: any, ...)
    if not repository or Config.ObjectivesEnabled ~= true then return fail("disabled") end
    if select("#", ...) ~= 0 then return fail("bad_request") end
    if not allowed(player) then return fail("rate_limited") end
    local invalid = validate(request)
    if invalid then return fail(invalid) end
    local ok, response = pcall(handleAction, player, request)
    if not ok then
        warn("[Be Dino] ObjectiveAction failed: " .. tostring(response))
        return fail("save_failed")
    end
    return response
end

-- BD-074 hook API. A NO-OP (returns false) while the flag is off or the service was not started; otherwise queues the event in
-- server memory (committed in batches by the repository). kind must be an ObjectiveConfig.EventKinds entry. eventId (e.g.
-- "run:<runId>") makes a replay count once. value is used by threshold objectives (level_reached). The ONE boolean check comes
-- first: nothing is allocated and no profile is touched while Config.ObjectivesEnabled is false. Call sites guard with the same
-- check, so with the flag off they do not even evaluate their arguments or require this module (tools/verify_objective_hooks.py).
function ObjectiveService.record(player: any, kind: string, amount: number?, eventId: string?, value: number?): boolean
    if Config.ObjectivesEnabled ~= true or not repository then return false end
    return repository.objectiveRecord(player, {kind = kind, amount = amount, id = eventId, value = value})
end

-- Derived recorders for the facts that carry several objective events at once. Same rule as record(): flag off = return at once.
-- Called only AFTER the transaction that committed the fact (ProfileRepository), never from client input.

-- Species tier from which "Rare or better" (D6) counts: Config.SpeciesRarityNames = Common 1, Uncommon 2, Rare 3, Epic 4, Legendary 5.
ObjectiveService.RareTier = 3

-- A settled run (ProfileRepository.commitRunSettlement, after adopt). `eggs` are the run's committed eggs ({eventId = ...}); an egg
-- caught during a weather event carries its weather id, a clear-weather egg "clear" (S5 "Catch an event egg"). `level` is the
-- account level read from the committed profile (T7 uses a threshold). runSeconds rides along as the run length for later gating.
-- All three events are id-keyed or threshold-merged, so a replayed settlement counts once.
function ObjectiveService.recordRunSettled(player: any, runId: string, runSeconds: number?, eggs: {any}?, level: number?)
    if Config.ObjectivesEnabled ~= true then return end
    local length = if type(runSeconds) == "number" and runSeconds == runSeconds and runSeconds >= 0 and runSeconds < 1e9 then runSeconds else nil -- a non-finite length must not drop the event
    ObjectiveService.record(player, "run_end", 1, "run:" .. runId, length)
    local eventEggs = 0
    if eggs then
        for _, egg in eggs do
            if egg.eventId ~= nil and egg.eventId ~= "clear" then eventEggs += 1 end
        end
    end
    if eventEggs > 0 then ObjectiveService.record(player, "event_egg_caught", eventEggs, "events:" .. runId) end
    if level ~= nil then ObjectiveService.record(player, "level_reached", 1, nil, level) end
end

-- Eggs opened by ONE committed claim (the head egg plus the rest of its hatch page: ProfileRepository.claimChest, after adopt).
-- Batched on purpose: one event per kind per claim, never one per egg, so a 120-egg run cannot overflow the pending queue.
-- Every opened egg counts as hatched, a failed (Cracked) one too; "Rare or better" needs a hatched dino of species tier >= RareTier.
-- `freshSpecies` = set of species ids the player did not own before this claim (computed inside the transaction).
function ObjectiveService.recordHatched(player: any, outcomes: {any}, freshSpecies: {[string]: boolean}?)
    if Config.ObjectivesEnabled ~= true then return end
    local opened, rare, fresh = 0, 0, 0
    for _, outcome in outcomes do
        opened += 1
        if outcome.failed ~= true and (Config.SpeciesRarities[outcome.speciesId] or 0) >= ObjectiveService.RareTier then rare += 1 end
    end
    if freshSpecies then
        for _ in freshSpecies do fresh += 1 end
    end
    if opened > 0 then ObjectiveService.record(player, "egg_hatched", opened) end
    if rare > 0 then ObjectiveService.record(player, "rare_hatched", rare) end
    if fresh > 0 then ObjectiveService.record(player, "species_new", fresh) end
end

-- A fusion the server verified: a quote for a full, owned donor set (FusionService) or a committed fusion (ProfileRepository).
-- The server cannot see a menu being opened (only the player's client can), so T9 "Open the Fusion menu" and D5 "Add a dino toward
-- a fusion step" both count on this server-verified use of the menu (docs/66 section 18).
function ObjectiveService.recordFusionUse(player: any)
    if Config.ObjectivesEnabled ~= true then return end
    ObjectiveService.record(player, "fusion_menu_opened", 1)
    ObjectiveService.record(player, "fusion_step_added", 1)
end

-- Test hook: deterministic clock for the rate limiter.
function ObjectiveService.setClock(fn: () -> number)
    clock = fn
    windows = {}
end

function ObjectiveService.start(profileRepository: any): any
    if Config.ObjectivesEnabled ~= true then return nil end
    repository = profileRepository
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local existing = folder:FindFirstChild("ObjectiveAction")
    if existing and not existing:IsA("RemoteFunction") then existing:Destroy() existing = nil end
    local remote = existing or Instance.new("RemoteFunction")
    remote.Name = "ObjectiveAction"
    remote.Parent = folder
    remote.OnServerInvoke = function(player, ...)
        return ObjectiveService.handle(player, ...)
    end
    Players.PlayerRemoving:Connect(function(player)
        windows[player] = nil
    end)
    -- Progress is queued in memory; this loop commits it (claims and the lease release commit it too).
    task.spawn(function()
        while true do
            task.wait(ObjectiveConfig.FlushSeconds)
            for _, player in Players:GetPlayers() do
                if repository.isLoaded(player) then task.spawn(repository.objectiveFlush, player) end
            end
        end
    end)
    return remote
end

return ObjectiveService
