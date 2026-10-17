--!strict
-- BD-246: Fly glide and (BD-595) Fly hover cap. Holding jump in the air tells the server (one boolean) and, since BD-593, slows the fall HERE: the character is
-- owned by this client, so the server's own velocity write (ClassMovementService hover loop) never reached it (measured: fall 40 to 58
-- studs/s with the glide held, cap 12). The per-frame decision is Shared/ClassMovement.glideStep (pure, tools/verify_class_movement.py).
-- BD-595: the hover cap (6.5 studs, measured at the FEET, not the root centre; a leap is exempt) is applied here in the same single write,
-- through the pure Shared/ClassMovement.hoverStep. It only ever lowers an upward speed.
-- Does nothing unless the server created the remote (Config.ClassMovementEnabled) and the dino is Fly class.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local ProgressionConfig = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("ProgressionConfig"))
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
-- BD-595: the same write also carries the hover cap.
local used = 0
local groundParams = RaycastParams.new()
groundParams.FilterType = Enum.RaycastFilterType.Include
-- A leap is running when the local prediction stamp (os.clock, set by Bootstrap on the key press) or the server's LeapUntil says so.
local function isLeaping(c: Model): boolean
    local predicted = c:GetAttribute("LeapPredictAt")
    if typeof(predicted) == "number" and os.clock() - predicted < ProgressionConfig.LeapDuration then return true end
    local untilAt = c:GetAttribute("LeapUntil")
    return typeof(untilAt) == "number" and workspace:GetServerTimeNow() < untilAt
end
RunService.Heartbeat:Connect(function(dt: number)
    local c = player.Character
    local h = if c then c:FindFirstChildOfClass("Humanoid") else nil
    local root = if c then c:FindFirstChild("HumanoidRootPart") else nil
    if not (c and h and root and root:IsA("BasePart")) or h.Health <= 0 or c:GetAttribute("RunState") ~= "Active" or not isFly() then
        used = 0
        return
    end
    local v = root.AssemblyLinearVelocity
    local airborne = h.FloorMaterial == Enum.Material.Air
    local newY = v.Y
    -- Hover cap: only while rising in the air; the ground is looked up only then (one short ray).
    if airborne and v.Y > 0 and not isLeaping(c) then
        groundParams.FilterDescendantsInstances = { workspace.Terrain, workspace:FindFirstChild("BeDinoArena") or workspace.Terrain }
        local hit = workspace:Raycast(root.Position, Vector3.new(0, -60, 0), groundParams)
        if hit then newY = CM.hoverStep("Fly", newY, root.Position.Y - hit.Position.Y, h.HipHeight, root.Size.Y, false, dt) end
    end
    local glideY, newUsed = CM.glideStep("Fly", held, not airborne, newY, used, dt)
    used = newUsed
    newY = glideY
    if newY ~= v.Y then root.AssemblyLinearVelocity = Vector3.new(v.X, newY, v.Z) end
end)
