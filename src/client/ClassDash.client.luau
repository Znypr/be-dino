--!strict
-- BD-246: Water dinos cannot jump; the jump input asks the server for a dash (ClassDash remote) and applies the velocity it
-- answers with. Does nothing unless the server created the remote (Config.ClassMovementEnabled) and the dino is Water class.
-- BD-571: one write is damped by the Humanoid ground controller within a few frames (the dino barely moved), so the answered
-- velocity is re-applied every Heartbeat for the dash duration, like the E leap (Bootstrap.client leapHold). The decisions are in
-- Shared/DashHold (pure, tools/verify_class_movement.py). The server only decides whether a dash is allowed.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local CM = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("ClassMovement"))
local DashHold = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("DashHold"))
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
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
local SLOPE_NORMAL_Y = math.cos(math.rad(Config.MaxSlopeAngle)) -- a surface flatter than the walkable slope limit is ground, not a wall
type Active = { hold: { [string]: number }, character: Model, root: BasePart, params: RaycastParams }
local active: Active? = nil

local function alive(a: Active): boolean
    local c = player.Character
    local h = if c then c:FindFirstChildOfClass("Humanoid") else nil
    return c == a.character and a.root.Parent ~= nil and h ~= nil and h.Health > 0
        and c:GetAttribute("RunState") == "Active" and isWater()
end

-- Same Blockcast as the server's start check (ClassMovementService), looked at every frame a little ahead of the dino.
local function wallAhead(a: Active, dt: number): boolean
    local dir = Vector3.new(a.hold.vx, 0, a.hold.vz)
    local ahead = dir.Magnitude * math.max(dt, 1 / 30) + 0.5
    local hit = workspace:Blockcast(a.root.CFrame, Vector3.new(a.root.Size.X, 1.5, a.root.Size.Z), dir.Unit * ahead, a.params)
    return hit ~= nil and hit.Normal.Y < SLOPE_NORMAL_Y
end

-- One frame of the dash. Returns false when the dash is over.
local function applyFrame(dt: number): boolean
    local a = active
    if not a then return false end
    local isAlive = alive(a)
    local v = if isAlive then a.root.AssemblyLinearVelocity else Vector3.zero
    local action, vx, vy, vz = DashHold.step(a.hold, os.clock(), v.Y, isAlive and wallAhead(a, dt), isAlive)
    if action ~= "end" then a.root.AssemblyLinearVelocity = Vector3.new(vx, vy, vz) end
    if action == "hold" then return true end
    active = nil
    return false
end

RunService.Heartbeat:Connect(function(dt: number)
    if active then applyFrame(dt) end
end)

remote.OnClientEvent:Connect(function(vx: any, _vy: any, vz: any)
    local c = player.Character
    local root = if c then c:FindFirstChild("HumanoidRootPart") else nil
    if not (c and root and root:IsA("BasePart") and isWater()) then return end
    local hold = DashHold.begin(vx, vz, os.clock(), CM.duration("Water", "jump"))
    if not hold then return end
    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances = { workspace.Terrain, workspace:FindFirstChild("BeDinoArena") or workspace.Terrain }
    active = { hold = hold, character = c, root = root, params = params }
    applyFrame(1 / 60) -- first write now, not a frame later
end)
