--!strict
-- BD-246: Fly glide. Holding jump in the air tells the server (one boolean); the server caps the fall speed. Does nothing unless
-- the server created the remote (Config.ClassMovementEnabled) and the dino is Fly class.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local CM = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("ClassMovement"))
local player = Players.LocalPlayer
local folder = ReplicatedStorage:WaitForChild("BeDinoRemotes", 60)
local found = if folder then folder:WaitForChild("ClassGlide", 5) else nil
if not found or not found:IsA("RemoteEvent") then return end
local remote: RemoteEvent = found

local held = false
local function set(value: boolean)
    if held == value then return end
    held = value
    remote:FireServer(value)
end
local function isFly(): boolean
    return CM.classForSpecies(player:GetAttribute("EquippedSpeciesId")) == "Fly"
end
UserInputService.InputBegan:Connect(function(input)
    if input.KeyCode == Enum.KeyCode.Space and isFly() then set(true) end
end)
UserInputService.InputEnded:Connect(function(input)
    if input.KeyCode == Enum.KeyCode.Space then set(false) end
end)
UserInputService.JumpRequest:Connect(function()
    if isFly() then set(true) end
end)
-- Touch has no key-up for the jump button: release once the character is back on the ground.
task.spawn(function()
    while true do
        task.wait(0.15)
        local c = player.Character
        local h = if c then c:FindFirstChildOfClass("Humanoid") else nil
        if held and (not h or h.FloorMaterial ~= Enum.Material.Air) and not UserInputService:IsKeyDown(Enum.KeyCode.Space) then set(false) end
    end
end)
