--!strict
-- BD-120 owner-only admin panel (docs/79). Every request is re-authorized and validated here;
-- the client panel is display only. Overrides live in server memory, are mirrored to workspace
-- attributes for display, and are never written to player profiles.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Config = require(ReplicatedStorage.Shared.Config)
local ProgressionConfig = require(ReplicatedStorage.Shared.ProgressionConfig)
local Rules = require(ReplicatedStorage.Shared.AdminRules)
local FoodService = require(script.Parent.FoodService)
local ProgressionService = require(script.Parent.ProgressionService)

local AdminService = {}
local values: {[string]: number} = {}
local admins: {[Player]: boolean} = {}
local lastRequest: {[Player]: number} = {}

local function publish(key: string, value: number)
    values[key] = value
    workspace:SetAttribute("Admin_" .. key, value)
    if key == "foodMultiplier" then FoodService.setAdminFoodMultiplier(value) end
    if key == "mutationChanceMultiplier" then FoodService.setAdminMutationMultiplier(value) end
    if key == "gravity" then workspace.Gravity = value end
    if key == "jumpPower" then
        -- Server-validated range (Rules.sanitize); applies to live characters, Dinosaur.attach reads the attribute for new ones.
        for _, player in Players:GetPlayers() do
            local humanoid = if player.Character then player.Character:FindFirstChildOfClass("Humanoid") else nil
            if humanoid then humanoid.JumpPower = value end
        end
    end
end

local function authorize(player: Player)
    local rank: number? = nil
    if game.CreatorType == Enum.CreatorType.Group and game.CreatorId > 0 then
        local ok, result = pcall(function() return player:GetRankInGroup(game.CreatorId) end)
        rank = if ok then result else nil
    end
    local allowed = Rules.isAdmin({
        userId = player.UserId,
        creatorType = game.CreatorType.Name,
        creatorId = game.CreatorId,
        groupRank = rank,
        adminIds = Config.AdminUserIds,
        unpublishedStudio = RunService:IsStudio() and game.GameId == 0,
        enabled = Config.AdminPanelEnabled,
    })
    if not player.Parent then return end
    admins[player] = allowed
    player:SetAttribute("IsAdmin", allowed) -- display hint only; requests are checked against `admins`
end

local function handle(player: Player, action: any, a: any, b: any): (boolean, string)
    if admins[player] ~= true then return false, "not_admin" end
    local now = os.clock()
    if now - (lastRequest[player] or 0) < 0.15 then return false, "busy" end
    lastRequest[player] = now
    if typeof(action) ~= "string" or not table.find(Rules.Actions, action) then return false, "bad_action" end
    if action == "set" then
        local value = Rules.sanitize(a, b)
        if value == nil then return false, "bad_value" end
        publish(a, value)
        print(string.format("[Be Dino admin] %s set %s = %s", player.Name, a, tostring(value)))
        return true, Rules.format(value, a)
    elseif action == "startWeather" then
        if typeof(a) ~= "string" or #a > 24 then return false, "bad_weather" end
        local seconds = Rules.weatherSeconds(b, ProgressionConfig.WeatherDuration)
        if seconds == nil or not ProgressionService.adminStartWeather(a, seconds) then return false, "bad_weather" end
        print(string.format("[Be Dino admin] %s started weather %s for %ds", player.Name, a, seconds))
        return true, "started"
    elseif action == "stopWeather" then
        ProgressionService.adminStopWeather()
        print("[Be Dino admin] " .. player.Name .. " stopped the weather")
        return true, "stopped"
    else -- reset
        for _, key in Rules.SettingOrder do publish(key, Rules.Settings[key].default) end
        print("[Be Dino admin] " .. player.Name .. " reset admin values")
        return true, "reset"
    end
end

function AdminService.start()
    for _, key in Rules.SettingOrder do publish(key, Rules.Settings[key].default) end
    ProgressionService.setAdminMultipliers(function()
        return values.growthMultiplier or 1, values.speedMultiplier or 1
    end)
    if not Config.AdminPanelEnabled then return end
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        local created = Instance.new("Folder")
        created.Name = "BeDinoRemotes"
        created.Parent = ReplicatedStorage
        folder = created
    end
    local remote = Instance.new("RemoteFunction")
    remote.Name = "AdminAction"
    remote.Parent = folder
    remote.OnServerInvoke = function(player: Player, ...)
        if select("#", ...) > 3 then return false, "bad_args" end
        local action, a, b = ...
        return handle(player, action, a, b)
    end
    Players.PlayerAdded:Connect(function(player) task.spawn(authorize, player) end)
    for _, player in Players:GetPlayers() do task.spawn(authorize, player) end
    Players.PlayerRemoving:Connect(function(player) admins[player] = nil lastRequest[player] = nil end)
end

return AdminService
