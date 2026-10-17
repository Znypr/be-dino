--!strict
-- BD-246: Fly glide. Holding jump in the air tells the server (one boolean) and, since BD-593, slows the fall HERE: the character is
-- owned by this client, so the server's own velocity write (ClassMovementService hover loop) never reached it (measured: fall 40 to 58
-- studs/s with the glide held, cap 12). The per-frame decision is Shared/ClassMovement.glideStep (pure, tools/verify_class_movement.py).
-- Does nothing unless the server created the remote (Config.ClassMovementEnabled) and the dino is Fly class.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
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
-- BD-593: the glide itself, every frame, on the local character (single velocity write, vertical only; the planar speed is kept).
local used = 0
RunService.Heartbeat:Connect(function(dt: number)
    local c = player.Character
    local h = if c then c:FindFirstChildOfClass("Humanoid") else nil
    local root = if c then c:FindFirstChild("HumanoidRootPart") else nil
    if not (c and h and root and root:IsA("BasePart")) or h.Health <= 0 or c:GetAttribute("RunState") ~= "Active" or not isFly() then
        used = 0
        return
    end
    local v = root.AssemblyLinearVelocity
    local newY, newUsed = CM.glideStep("Fly", held, h.FloorMaterial ~= Enum.Material.Air, v.Y, used, dt)
    used = newUsed
    if newY ~= v.Y then root.AssemblyLinearVelocity = Vector3.new(v.X, newY, v.Z) end
end)
