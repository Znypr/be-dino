--!strict
-- BD-246: Water dinos cannot jump; the jump input asks the server for a dash (ClassDash remote) and applies the velocity it
-- answers with. Does nothing unless the server created the remote (Config.ClassMovementEnabled) and the dino is Water class.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local CM = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("ClassMovement"))
local player = Players.LocalPlayer
local folder = ReplicatedStorage:WaitForChild("BeDinoRemotes", 60)
local found = if folder then folder:WaitForChild("ClassDash", 5) else nil
if not found or not found:IsA("RemoteEvent") then return end
local remote: RemoteEvent = found

local function isWater(): boolean
    return CM.classForSpecies(player:GetAttribute("EquippedSpeciesId")) == "Water"
end
UserInputService.JumpRequest:Connect(function()
    local c = player.Character
    if isWater() and c and c:GetAttribute("RunState") == "Active" then remote:FireServer() end
end)
remote.OnClientEvent:Connect(function(vx: any, _vy: any, vz: any)
    if typeof(vx) ~= "number" or typeof(vz) ~= "number" or vx ~= vx or vz ~= vz then return end
    local c = player.Character
    local root = if c then c:FindFirstChild("HumanoidRootPart") else nil
    if root and root:IsA("BasePart") and isWater() then
        local v = root.AssemblyLinearVelocity
        root.AssemblyLinearVelocity = Vector3.new(vx, math.min(v.Y, 0), vz) -- never upward
    end
end)
