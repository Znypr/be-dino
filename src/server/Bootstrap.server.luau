--!strict
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Arena = require(script.Parent.Arena)
local Dinosaur = require(script.Parent.Dinosaur)

Lighting.ClockTime = 14
Lighting.Brightness = 2
Lighting.Ambient = Color3.fromRGB(130, 143, 148)
-- Keep the place's default destroy height; this setting is protected at runtime.
Arena.build()

local function setup(player: Player)
    player.CanLoadCharacterAppearance = false
    player.CharacterAdded:Connect(function(character)
        character:SetAttribute("GrowthScore", 0)
        Dinosaur.attach(character, Config.WalkSpeed, player)
    end)
    if player.Character then
        player.Character:SetAttribute("GrowthScore", 0)
        task.spawn(Dinosaur.attach, player.Character, Config.WalkSpeed, player)
    end
end
Players.PlayerAdded:Connect(setup)
for _, player in Players:GetPlayers() do setup(player) end

local FoodService = require(script.Parent.FoodService)
FoodService.start(Dinosaur)
print("[Be Dino] " .. Config.Build .. " ready. Food/growth test; no progression saves.")
