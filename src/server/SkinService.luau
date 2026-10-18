--!strict
-- BD-456 (docs/137 s5-s7, s15): the SkinAction RemoteFunction in ReplicatedStorage.BeDinoRemotes, the ONLY way a client asks to wear a skin.
-- There is no purchase remote (purchases arrive only through Marketplace / gift claim / admin grant, which write profile.ownedSkins elsewhere)
-- and nothing here reads or writes genes, Shiny/BIG, mutations, stage or any fusion input: a skin is a look only.
--
-- FLAG-OFF IDENTITY: start() returns nil on its first line unless Config.DinoSkinsEnabled is true (pinned OFF in the default AND playtest
-- release profiles). Nothing is created: no SkinAction remote, no connection, no profile read or write. handle() and resolve() answer
-- "disabled" / Base before they touch the repository.
--
-- Requests (exact keys, anything else is "bad_request"; a client never names a price, an owner, a species or a result):
--   {action = "get", instanceId = id?}              -> {ok, owned = {sorted ids}, defaultSkin, skin?, speciesId?, wearing?}
--   {action = "equip", instanceId = id, skin = id}  -> {ok, status, skin}   wear a skin on ONE dino ("Base" = explicit Base)
--   {action = "unequip", instanceId = id}           -> {ok, status, skin}   back to the account default
--   {action = "setDefault", skin = id}              -> {ok, status}         the account default ("Base" clears it)
-- Order of checks: flag, extra args, rate limit, shape, catalogue, then the repository (ownership + model are checked AGAIN inside the
-- lease-checked transaction, so a revoke or a second server cannot be raced). Never throws to the client.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local SkinCatalog = require(ReplicatedStorage.Shared.SkinCatalog)

local SkinService = {}

-- PROVISIONAL limits (not balance values): a child tapping through a picker stays far below them.
SkinService.ActionsPerWindow = 10
SkinService.ActionWindowSeconds = 10
SkinService.MaxIdLength = 120
SkinService.MaxSkinLength = 24

local repository: any = nil
local windows: {[any]: {startedAt: number, count: number}} = {}
local clock = os.clock

local Shapes: {[string]: {[string]: boolean}} = {
    get = {action = true, instanceId = true},
    equip = {action = true, instanceId = true, skin = true},
    unequip = {action = true, instanceId = true},
    setDefault = {action = true, skin = true},
}

local function fail(reason: string): any
    return {ok = false, reason = reason}
end

local function boundedString(value: any, maxLength: number): boolean
    return type(value) == "string" and #value >= 1 and #value <= maxLength
end

-- Fixed-window per-player limiter.
local function allowed(player: any): boolean
    local now = clock()
    local window = windows[player]
    if not window or now - window.startedAt >= SkinService.ActionWindowSeconds then
        window = {startedAt = now, count = 0}
        windows[player] = window
    end
    window.count += 1
    return window.count <= SkinService.ActionsPerWindow
end

local function validate(request: any): string?
    if type(request) ~= "table" then return "bad_request" end
    local shape = if type(request.action) == "string" then Shapes[request.action] else nil
    if shape == nil then return "bad_request" end
    for key in request do
        if type(key) ~= "string" or not shape[key] then return "bad_request" end
    end
    if request.instanceId ~= nil and not boundedString(request.instanceId, SkinService.MaxIdLength) then return "bad_request" end
    if request.skin ~= nil and not boundedString(request.skin, SkinService.MaxSkinLength) then return "bad_request" end
    local action = request.action
    if (action == "equip" or action == "unequip") and request.instanceId == nil then return "bad_request" end
    if (action == "equip" or action == "setDefault") and request.skin == nil then return "bad_request" end
    return nil
end

local function sortedOwned(owned: {[string]: boolean}): {string}
    local list: {string} = {}
    for id in owned do
        if SkinCatalog.isKnown(id) then table.insert(list, id) end -- an id from a newer build stays in the profile but is not offered
    end
    table.sort(list)
    return list
end

-- What a dino wears right now, from a repository view. Pure catalogue math; never writes.
local function wearing(view: any, speciesId: any): string
    return SkinCatalog.effective(view.owned, view.defaultSkin, view.skin, speciesId)
end

local function handleAction(player: any, request: any): any
    local action = request.action :: string
    if action == "get" then
        local view, reason = repository.skinView(player, request.instanceId)
        if view == nil then return fail(reason or "profile_not_loaded") end
        local result: {[string]: any} = {ok = true, owned = sortedOwned(view.owned), defaultSkin = SkinCatalog.normalize(view.defaultSkin)}
        if request.instanceId ~= nil then
            result.speciesId = view.speciesId
            result.skin = if SkinCatalog.isKnown(view.skin) then view.skin else nil -- a choice from a newer build is kept in the profile but not offered
            result.wearing = wearing(view, view.speciesId)
        end
        return result
    elseif action == "setDefault" then
        local skin = request.skin :: string
        if not SkinCatalog.isKnown(skin) then return fail("unknown_skin") end
        if SkinCatalog.isFree(skin) then
            local ok, status = repository.applySkin(player, {kind = "clearDefault"})
            return if ok then {ok = true, status = status} else fail(status)
        end
        local view, reason = repository.skinView(player, nil)
        if view == nil then return fail(reason or "profile_not_loaded") end
        if not SkinCatalog.owns(view.owned, skin) then return fail("not_owned") end
        local ok, status = repository.applySkin(player, {kind = "setDefault", skin = skin})
        return if ok then {ok = true, status = status} else fail(status)
    end
    -- equip / unequip act on one dino instance of THIS player.
    local instanceId = request.instanceId :: string
    local view, reason = repository.skinView(player, instanceId)
    if view == nil then return fail(reason or "instance_missing") end
    if action == "unequip" then
        local ok, status = repository.applySkin(player, {kind = "unequip", instanceId = instanceId})
        if not ok then return fail(status) end
        local after = repository.skinView(player, instanceId)
        return {ok = true, status = status, skin = if after then wearing(after, after.speciesId) else SkinCatalog.Base}
    end
    local skin = request.skin :: string
    local allowedHere, why = SkinCatalog.canEquip(view.owned, skin, view.speciesId)
    if not allowedHere then return fail(why) end
    local free = SkinCatalog.isFree(skin)
    local ok, status = repository.applySkin(player, {kind = "equip", instanceId = instanceId, skin = skin, free = free,
        modelSpecies = if free then nil else SkinCatalog.modelSet(skin)})
    if not ok then return fail(status) end
    local after = repository.skinView(player, instanceId)
    return {ok = true, status = status, skin = if after then wearing(after, after.speciesId) else SkinCatalog.Base}
end

-- Entry point for OnServerInvoke (and offline tests). Never throws to the client.
function SkinService.handle(player: any, request: any, ...: any): any
    if Config.DinoSkinsEnabled ~= true then return fail("disabled") end
    if select("#", ...) > 0 then return fail("bad_request") end
    if repository == nil then return fail("disabled") end
    if not allowed(player) then
        if Config.RunTelemetryEnabled == true then pcall(function() require(script.Parent.TelemetryHook).count("rate_limited", "Skin") end) end -- BD-650
        return fail("rate_limited")
    end
    local invalid = validate(request)
    if invalid then return fail(invalid) end
    local ok, response = pcall(handleAction, player, request)
    if not ok then
        warn("[Be Dino] SkinAction failed: " .. tostring(response))
        return fail("save_failed")
    end
    return response
end

-- The look this player's dino renders (the future single input to LPSkin): the validated instance skin, else the account default, else Base.
-- Read-only; flag off, an unloaded profile, an unknown dino or any problem all read as Base.
function SkinService.resolve(player: any, instanceId: any): string
    if Config.DinoSkinsEnabled ~= true or repository == nil then return SkinCatalog.Base end
    local view = repository.skinView(player, instanceId)
    if view == nil then return SkinCatalog.Base end
    return wearing(view, view.speciesId)
end

-- Test hook: deterministic clock for the rate limiter.
function SkinService.setClock(fn: () -> number)
    clock = fn
    table.clear(windows)
end

function SkinService.reset()
    repository = nil
    table.clear(windows)
end

function SkinService.start(repo: any): any
    if Config.DinoSkinsEnabled ~= true then return nil end -- flag off: no remote, no connection, no profile access
    repository = repo
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if folder == nil then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteFunction")
    remote.Name = "SkinAction"
    remote.OnServerInvoke = function(player: any, request: any, ...: any)
        local ok, response = pcall(SkinService.handle, player, request, ...)
        return if ok then response else fail("error")
    end
    remote.Parent = folder
    Players.PlayerRemoving:Connect(function(player: any)
        windows[player] = nil
    end)
    return remote
end

return SkinService
