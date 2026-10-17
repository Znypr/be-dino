--!strict
-- BD-073 (docs/66 section 7): server surface of the mini objectives. Behind Config.ObjectivesEnabled (false in every committed
-- build): while it is false start() returns at once, the ObjectiveAction remote does not exist, record() is a no-op and no
-- profile is ever read or written for objectives. No UI (BD-075) and no gameplay hooks (BD-074) yet: BD-074 will call
-- ObjectiveService.record(player, kind, amount, eventId, value) from the server events that already exist.
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
-- "egg:<outcomeId>", "run:<runId>") makes a replay count once. value is used by threshold objectives (level_reached).
function ObjectiveService.record(player: any, kind: string, amount: number?, eventId: string?, value: number?): boolean
    if not repository or Config.ObjectivesEnabled ~= true then return false end
    return repository.objectiveRecord(player, {kind = kind, amount = amount, id = eventId, value = value})
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
