--!strict
-- BD-1299: the Dino Index zone rewards, server side. Behind Config.IndexZonesEnabled (default false, ON only in the playtest profile); with the
-- flag off start() returns at once: no IndexZoneAction remote, no connection, no profile access.
-- ReplicatedStorage.BeDinoRemotes.IndexZoneAction (RemoteFunction) is the only way in. request = {action = "claim", zone = string, step =
-- "half" | "all"} and nothing else (any other key, type or extra argument is "bad_request"). The client sends a zone id and a step word only;
-- the server counts the species in the STORED collection, takes the amount from Shared/IndexZones and pays exactly once through
-- ProfileRepository.claimIndexZone (additive field `indexZoneRewards`). Answers {ok, status, crystals}; it never throws to the client.
-- Rate limited: one claim per TryGap seconds and PerMinute claims per minute per player (kept by UserId, so a rejoin is no fresh window).
-- Crystals only: never Robux, never a paid line, never a random item.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config) :: any
local Zones = require(ReplicatedStorage.Shared.IndexZones)

local Service = {}
Service.TryGap, Service.PerMinute = 0.5, 20
local repository: any = nil
local lastTry: {[any]: number} = {}
local windows: {[any]: {startedAt: number, count: number}} = {}

local function answer(ok: boolean, status: string, crystals: number?): any
    return {ok = ok, status = status, crystals = crystals or 0}
end

local function userKey(player: any): any
    local ok, id = pcall(function() return player.UserId end)
    return if ok and type(id) == "number" then id else player
end

local function allowed(player: any, now: number): boolean
    local key = userKey(player)
    if now - (lastTry[key] or -100) < Service.TryGap then return false end
    lastTry[key] = now
    local window = windows[key]
    if not window or now - window.startedAt >= 60 then
        for other, old in windows do
            if now - old.startedAt >= 120 then windows[other], lastTry[other] = nil, nil end
        end
        window = {startedAt = now, count = 0}
        windows[key] = window
    end
    window.count += 1
    return window.count <= Service.PerMinute
end

local function validate(request: any): boolean
    if typeof(request) ~= "table" then return false end
    for key in request do
        if key ~= "action" and key ~= "zone" and key ~= "step" then return false end
    end
    if request.action ~= "claim" then return false end
    if typeof(request.zone) ~= "string" or #request.zone < 1 or #request.zone > 16 or not Zones.zone(request.zone) then return false end
    return typeof(request.step) == "string" and Zones.Crystals[request.step] ~= nil
end

-- Entry point for OnServerInvoke (and offline tests). Never throws to the client.
function Service.handle(player: any, request: any, ...): any
    if Config.IndexZonesEnabled ~= true or repository == nil then return answer(false, "disabled") end
    if select("#", ...) ~= 0 or not validate(request) then return answer(false, "bad_request") end
    if not allowed(player, os.clock()) then return answer(false, "rate_limited") end
    local ok, status, crystals = repository.claimIndexZone(player, request.zone, request.step)
    return answer(ok == true, if typeof(status) == "string" then status else "save_failed", if ok then crystals else 0)
end

function Service.start(repo: any): any
    if Config.IndexZonesEnabled ~= true then return nil end -- flag off: no remote, no connection, no profile access
    if repository ~= nil then return nil end
    repository = repo
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if folder == nil then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteFunction")
    remote.Name = "IndexZoneAction"
    remote.OnServerInvoke = function(player: any, ...: any)
        local ok, response = pcall(Service.handle, player, ...)
        return if ok then response else answer(false, "save_failed")
    end
    remote.Parent = folder
    return remote
end

return Service
