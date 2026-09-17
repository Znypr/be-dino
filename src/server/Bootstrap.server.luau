--!strict
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Arena = require(script.Parent.Arena)
local Dinosaur = require(script.Parent.Dinosaur)
local RunLifecycle = require(script.Parent.RunLifecycle)

Lighting.ClockTime = 14
Lighting.Brightness = 2
Lighting.Ambient = Color3.fromRGB(130, 143, 148)
-- Keep the place's default destroy height; this setting is protected at runtime.
Arena.build()
RunLifecycle.start()

local function setup(player: Player)
    player.CanLoadCharacterAppearance = false
    player.CharacterAdded:Connect(function(character)
        RunLifecycle.begin(player, character)
        task.spawn(Dinosaur.attach, character, Config.WalkSpeed, player)
    end)
    if player.Character then
        RunLifecycle.begin(player, player.Character)
        task.spawn(Dinosaur.attach, player.Character, Config.WalkSpeed, player)
    end
end
Players.PlayerAdded:Connect(setup)
for _, player in Players:GetPlayers() do setup(player) end

local FoodService = require(script.Parent.FoodService)
FoodService.start(Dinosaur)
local PredationService = require(script.Parent.PredationService)
PredationService.start(RunLifecycle, Dinosaur)
print("[Be Dino] " .. Config.Build .. " ready. PvP/run-ending test; no progression saves.")
