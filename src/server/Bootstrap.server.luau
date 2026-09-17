--!strict
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Arena = require(script.Parent.Arena)
local Dinosaur = require(script.Parent.Dinosaur)
local ProfileRepository = require(script.Parent.ProfileRepository)
local RunLifecycle = require(script.Parent.RunLifecycle)

Players.CharacterAutoLoads = false

Lighting.ClockTime = 14
Lighting.Brightness = 2
Lighting.Ambient = Color3.fromRGB(130, 143, 148)
Arena.build()

ProfileRepository.start()
RunLifecycle.configureSettlement(function(player: Player, runId: string, catchScore: number, reason: string)
    local ok = ProfileRepository.commitRunSettlement(player, runId, catchScore)
    if not ok then
        warn(string.format("[Be Dino] settlement failed for %s (%s)", player.Name, reason))
        return false
    end

    if Config.DuplicateSettlementProbe then
        local retryOk, _, retryStatus = ProfileRepository.commitRunSettlement(player, runId, catchScore)
        if not retryOk or retryStatus ~= "duplicate" then
            player:SetAttribute("ProfileState", "SaveFailed")
            warn("[Be Dino] duplicate settlement probe failed for " .. player.Name)
            return false
        end
        player:SetAttribute("LastSettlementProbe", "duplicate-ok")
    end

    -- If the player vanished while this async settlement was running, release the lease now.
    if not player.Parent then
        ProfileRepository.release(player)
    end
    return true
end)
RunLifecycle.start()

local function spawnLoadedPlayer(player: Player)
    player.CanLoadCharacterAppearance = false
    local loaded = ProfileRepository.load(player)
    if not loaded or not player.Parent then
        warn("[Be Dino] profile load blocked character spawn for " .. player.Name)
        return
    end

    local ok, err = pcall(function()
        player:LoadCharacterAsync()
    end)
    if not ok then
        warn("[Be Dino] initial character load failed: " .. tostring(err))
    end
end

local function setup(player: Player)
    player.CanLoadCharacterAppearance = false
    player.CharacterAdded:Connect(function(character)
        if player:GetAttribute("ProfileState") ~= "Loaded" then
            character:Destroy()
            return
        end
        RunLifecycle.begin(player, character)
        task.spawn(Dinosaur.attach, character, Config.WalkSpeed, player)
    end)
    task.spawn(spawnLoadedPlayer, player)
end

Players.PlayerAdded:Connect(setup)
for _, player in Players:GetPlayers() do
    setup(player)
end

Players.PlayerRemoving:Connect(function(player)
    local status = RunLifecycle.endForDisconnect(player)
    if status ~= "busy" then
        ProfileRepository.release(player)
    end
end)

game:BindToClose(function()
    for _, player in Players:GetPlayers() do
        local status = RunLifecycle.endForDisconnect(player)
        if status ~= "busy" then
            ProfileRepository.release(player)
        end
    end
end)

local FoodService = require(script.Parent.FoodService)
FoodService.start(Dinosaur)
local PredationService = require(script.Parent.PredationService)
PredationService.start(RunLifecycle, Dinosaur)

print("[Be Dino] " .. Config.Build .. " ready. Persistent settlement test.")
