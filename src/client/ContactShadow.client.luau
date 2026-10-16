--!strict
-- BD-460 (docs/138): a soft contact shadow under each dino so it reads as standing ON the grass, not a flat cut-out against it.
-- Client-only visuals (nothing replicates): three flat translucent discs (ContactShadowRules.Layers) parented to the camera, never
-- colliding, never queryable, never casting. The local dino is always shadowed (one raycast per frame); other dinos only within
-- range and up to a per-device cap that the Effects setting lowers (Lite halves it, Off drops it), refreshed 10 times a second.
-- All numbers and rules live in the pure module Shared/ContactShadowRules (tools/verify_contact_shadow.py).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("ContactShadowRules"))
local Settings = require(Shared:WaitForChild("SettingsModel"))

local localPlayer = Players.LocalPlayer
local camera = workspace.CurrentCamera

local function deviceClass(): string
    if not UserInputService.TouchEnabled then return "Desktop" end
    local size = camera.ViewportSize
    return if math.min(size.X, size.Y) >= 600 then "Tablet" else "Phone"
end
local device = deviceClass()

type Shadow = {parts: {Part}, shown: boolean, width: number, length: number}
local folder = Instance.new("Folder")
folder.Name = "ContactShadows"
folder.Parent = camera

local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude
rayParams.IgnoreWater = true
local function refreshFilter()
    local ignore: {Instance} = {folder}
    for _, p in Players:GetPlayers() do if p.Character then table.insert(ignore, p.Character) end end
    rayParams.FilterDescendantsInstances = ignore
end

local function newShadow(): Shadow
    local parts = {}
    local c = Rules.Color
    for i = 1, #Rules.Layers do
        local part = Instance.new("Part")
        part.Name = "ContactShadow" .. i
        part.Shape = Enum.PartType.Cylinder
        part.Material = Enum.Material.SmoothPlastic
        part.Color = Color3.fromRGB(c[1], c[2], c[3])
        part.Anchored, part.CanCollide, part.CanQuery, part.CanTouch, part.CastShadow, part.Massless = true, false, false, false, false, true
        part.Size = Vector3.new(Rules.Thickness, 1, 1)
        part.Transparency = 1
        part.Parent = folder
        parts[i] = part
    end
    return {parts = parts, shown = false, width = 0, length = 0}
end

local function hide(shadow: Shadow)
    if not shadow.shown then return end
    shadow.shown = false
    for _, part in shadow.parts do part.Transparency = 1 end
end

-- Place one shadow under this character. Returns false (and hides it) when there is no ground close below.
local function place(shadow: Shadow, character: Model): boolean
    local root = character:FindFirstChild("HumanoidRootPart")
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not root or not root:IsA("BasePart") or not humanoid or humanoid.Health <= 0 then hide(shadow) return false end
    local scaleValue = character:GetAttribute("VisualScale")
    local scale = if typeof(scaleValue) == "number" then scaleValue else 1
    local rootPos = root.Position
    local standHeight = humanoid.HipHeight + root.Size.Y / 2
    local result = workspace:Raycast(rootPos, Vector3.new(0, -(standHeight + 14 + 6 * scale), 0), rayParams)
    if not result then hide(shadow) return false end
    local normal = result.Normal
    if normal.Y < Rules.MinNormalY then normal = Vector3.yAxis end
    local opacity, sizeFactor = Rules.airborne(rootPos.Y - result.Position.Y - standHeight)
    if opacity <= 0.02 then hide(shadow) return false end
    local width, length = Rules.footprint(scale)
    local look = root.CFrame.LookVector
    local forward = look - normal * look:Dot(normal)
    forward = if forward.Magnitude < 1e-3 then normal:Cross(Vector3.xAxis) else forward.Unit
    local across = forward:Cross(normal)
    shadow.shown = true
    for i, part in shadow.parts do
        local layer = Rules.Layers[i]
        local origin = result.Position + normal * (Rules.Lift + (i - 1) * Rules.LayerStep)
        -- A cylinder's axis is its local X: X = ground normal, Y = across the dino, Z = along it.
        part.CFrame = CFrame.fromMatrix(origin, normal, across, forward)
        part.Size = Vector3.new(Rules.Thickness, width * layer.size * sizeFactor, length * layer.size * sizeFactor)
        part.Transparency = Rules.transparency(i, opacity)
    end
    return true
end

local shadows: {[Player]: Shadow} = {}
local function shadowFor(player: Player): Shadow
    local s = shadows[player]
    if not s then s = newShadow() shadows[player] = s end
    return s
end
local function drop(player: Player)
    local s = shadows[player]
    if not s then return end
    shadows[player] = nil
    for _, part in s.parts do part:Destroy() end
end
Players.PlayerRemoving:Connect(drop)
for _, event in {Players.PlayerAdded, Players.PlayerRemoving} do event:Connect(refreshFilter) end
localPlayer.CharacterAdded:Connect(function() task.defer(refreshFilter) end)
refreshFilter()

local accumulator = 0
local chosen: {[Player]: boolean} = {}
RunService.PreRender:Connect(function(dt)
    local own = localPlayer.Character
    if own then place(shadowFor(localPlayer), own) else hide(shadowFor(localPlayer)) end

    -- WHO gets a shadow is decided ten times a second; WHERE it sits is updated every frame (a few raycasts at most) so it never lags a walking dino.
    accumulator += dt
    if accumulator >= 1 / Rules.OthersHz then
        accumulator = 0
        refreshFilter()
        local candidates = {}
        local camPos = camera.CFrame.Position
        for _, player in Players:GetPlayers() do
            local root = if player ~= localPlayer and player.Character then player.Character:FindFirstChild("HumanoidRootPart") else nil
            if root and root:IsA("BasePart") then table.insert(candidates, {id = player, distance = (root.Position - camPos).Magnitude}) end
        end
        chosen = {}
        for _, player in Rules.pick(candidates, device, Settings.effects()) do chosen[player] = true end
        for player, shadow in shadows do
            if player ~= localPlayer and not chosen[player] then hide(shadow) end
        end
    end
    for player in chosen do
        local character = player.Character
        if character and player.Parent then place(shadowFor(player), character) else chosen[player] = nil end
    end
end)
