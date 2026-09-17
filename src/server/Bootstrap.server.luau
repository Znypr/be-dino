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
workspace.FallenPartsDestroyHeight = -80
local pads = Arena.build()

local function setup(player: Player)
    player.CanLoadCharacterAppearance = false
    player.CharacterAdded:Connect(function(character)
        Dinosaur.attach(character, Config.WalkSpeed)
    end)
    if player.Character then task.spawn(Dinosaur.attach, player.Character, Config.WalkSpeed) end
end
Players.PlayerAdded:Connect(setup)
for _, player in Players:GetPlayers() do setup(player) end

-- Server-side station checks; no client-reported size or progression.
-- These pads are for the movement spike only and must be removed for release.
task.spawn(function()
    while true do
        task.wait(0.2)
        for _, player in Players:GetPlayers() do
            local character = player.Character
            local root = if character then character:FindFirstChild("HumanoidRootPart") :: BasePart? else nil
            local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
            if character and root and humanoid and humanoid.Health > 0 and character:GetAttribute("DinoAttached") then
                for _, station in pads do
                    local delta = root.Position - station.part.Position
                    if math.abs(delta.X) <= 6 and math.abs(delta.Z) <= 6 and math.abs(delta.Y) < 8 then
                        if character:GetAttribute("VisualScale") ~= station.scale then
                            Dinosaur.render(character, station.scale)
                        end
                        break
                    end
                end
            end
        end
    end
end)
print("[Be Dino] " .. Config.Build .. " ready. Movement only; no progression saves.")
