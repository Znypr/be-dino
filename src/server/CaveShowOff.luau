--!strict
-- Cosy pass (docs/104 s14, owner 2026-10-16): the Heart "show off" spot. A ProximityPrompt on the Heart pedestal steps the player's
-- dino onto it so the others in the den can admire it; walking or jumping off ends it. Server-side move only (FallRecovery.teleport),
-- no ownership, cosmetic, progression or HUD state is touched. Only called from Arena's cave branch (Config.CaveHub on): flag off = this
-- module never runs. The pedestal mesh itself is the existing hub_pedestal asset placed by CaveProps; this module adds only the invisible
-- prompt anchor (no art, no code-drawn model).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Rules = require(ReplicatedStorage.Shared.CaveLightingRules)
local Layout = require(ReplicatedStorage.Shared.CaveHubLayout)
local FallRecovery = require(script.Parent.FallRecovery)
local CaveShowOff = {}

local lastUse: {[Player]: number} = {}

local function standPoint(spot: any): Vector3
    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances = {workspace.Terrain}
    local hit = workspace:Raycast(Vector3.new(spot.x, Layout.FloorY + 30, spot.z), Vector3.new(0, -60, 0), params)
    local floorY = if hit and math.abs(hit.Position.Y - Layout.FloorY) < 6 then hit.Position.Y else Layout.floorHeight(spot.x, spot.z)
    return Vector3.new(spot.x, floorY + spot.standHeight + 3, spot.z)
end

function CaveShowOff.build(parent: Instance): Instance?
    local spot = Rules.showOffSpot()
    if not spot then return nil end
    local cfg = Rules.ShowOff
    local anchor = Instance.new("Part")
    anchor.Name = "ShowOffSpot"
    anchor.Size = Vector3.new(1, 1, 1)
    anchor.Transparency = 1
    anchor.Anchored, anchor.CanCollide, anchor.CanTouch, anchor.CanQuery, anchor.CastShadow = true, false, false, false, false
    anchor.Position = Vector3.new(spot.x, Layout.floorHeight(spot.x, spot.z) + spot.standHeight, spot.z)
    anchor:SetAttribute("IsCaveShowOff", true)
    local prompt = Instance.new("ProximityPrompt")
    prompt.ActionText = cfg.prompt
    prompt.ObjectText = ""
    prompt.MaxActivationDistance = cfg.promptDistance
    prompt.HoldDuration = 0
    prompt.RequiresLineOfSight = false
    prompt.Parent = anchor
    prompt.Triggered:Connect(function(player: Player)
        local now = os.clock()
        if now - (lastUse[player] or -math.huge) < cfg.cooldown then return end
        lastUse[player] = now
        local character = player.Character
        local root = character and character:FindFirstChild("HumanoidRootPart")
        if not character or not root or not root:IsA("BasePart") then return end
        local humanoid = character:FindFirstChildOfClass("Humanoid")
        if not humanoid or humanoid.Health <= 0 then return end
        -- only from inside the den, near the pedestal (the prompt distance already limits it; this stops a stale trigger)
        if ((root :: BasePart).Position - Vector3.new(spot.x, (root :: BasePart).Position.Y, spot.z)).Magnitude > cfg.promptDistance + 6 then return end
        FallRecovery.teleport(player, character, CFrame.new(standPoint(spot)) * CFrame.Angles(0, spot.yaw + math.pi, 0))
    end)
    Players.PlayerRemoving:Connect(function(player: Player) lastUse[player] = nil end)
    anchor.Parent = parent
    return anchor
end

return CaveShowOff
