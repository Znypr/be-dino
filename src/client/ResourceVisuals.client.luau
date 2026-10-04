--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local RuntimeMeshes = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("RuntimeMeshes"))
local watched = setmetatable({}, {__mode = "k"})
local function characterVisual(character: Model)
    local root = character:FindFirstChild("HumanoidRootPart")
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not root or not root:IsA("BasePart") or not humanoid then return end
    local id = character:GetAttribute("SpeciesId") or "compy"
    local scale = character:GetAttribute("VisualScale") or 1
    local gold = character:GetAttribute("GoldVisual") == true
    local previous = character:FindFirstChild("LocalMeshVisual")
    if previous and previous:GetAttribute("SpeciesId") == id and previous:GetAttribute("Scale") == scale
        and previous:GetAttribute("Gold") == gold then return end
    local model = RuntimeMeshes.clone(id)
    if not model then return end
    if previous then previous:Destroy() end
    local groundHeight = root.Size.Y / 2 + humanoid.HipHeight
    if humanoid.RigType == Enum.HumanoidRigType.R6 then
        local leg = character:FindFirstChild("Left Leg")
        groundHeight += if leg and leg:IsA("BasePart") then leg.Size.Y else 2
    end
    model.Name = "LocalMeshVisual"
    model:SetAttribute("SpeciesId", id)
    model:SetAttribute("Scale", scale)
    model:SetAttribute("Gold", gold)
    model:ScaleTo(scale)
    model:PivotTo(root.CFrame * CFrame.new(0, -groundHeight, 0))
    for _, item in model:GetDescendants() do
        if item:IsA("BasePart") then
            item.Anchored = false
            if gold then item.Color = Color3.fromRGB(255, 207, 99) item.Material = Enum.Material.Metal end
            local weld = Instance.new("WeldConstraint")
            weld.Part0, weld.Part1, weld.Parent = root, item, item
        end
    end
    model.Parent = character
    local fallback = character:FindFirstChild("DinoVisual")
    if fallback then
        for _, item in fallback:GetDescendants() do
            if item:IsA("BasePart") then item.LocalTransparencyModifier = 1 end
        end
    end
end
local function watchCharacter(character: Model)
    if watched[character] then return end
    watched[character] = true
    local queued = false
    local function refresh()
        if queued then return end
        queued = true
        task.defer(function()
            queued = false
            if character.Parent then characterVisual(character) end
        end)
    end
    for _, attribute in {"SpeciesId", "VisualScale", "GoldVisual", "DinoAttached"} do
        character:GetAttributeChangedSignal(attribute):Connect(refresh)
    end
    character.DescendantAdded:Connect(function(item)
        if item:IsA("BasePart") and item:FindFirstAncestor("DinoVisual") and character:FindFirstChild("LocalMeshVisual") then
            item.LocalTransparencyModifier = 1
        end
    end)
    refresh()
end
local function watchPlayer(player: Player)
    player.CharacterAdded:Connect(watchCharacter)
    if player.Character then watchCharacter(player.Character) end
end
Players.PlayerAdded:Connect(watchPlayer)
for _, player in Players:GetPlayers() do watchPlayer(player) end
local function propVisual(prop: Instance)
    if not prop:IsA("Model") or prop:FindFirstChild("LocalResourceMesh") then return end
    local id = prop:GetAttribute("ResourceId")
    local position = prop:GetAttribute("SourcePosition")
    if typeof(id) ~= "string" or typeof(position) ~= "Vector3" then return end
    local mesh = RuntimeMeshes.clone(id)
    if not mesh then return end
    mesh.Name = "LocalResourceMesh"
    mesh:ScaleTo(prop:GetAttribute("SourceScale") or 1)
    mesh:PivotTo(CFrame.new(position) * CFrame.Angles(0, prop:GetAttribute("SourceYaw") or 0, 0))
    for _, item in prop:GetDescendants() do
        if item:IsA("BasePart") then item.LocalTransparencyModifier = 1 end
    end
    mesh.Parent = prop
end
local function upgradeAll()
    for _, player in Players:GetPlayers() do if player.Character then characterVisual(player.Character) end end
    local arena = workspace:FindFirstChild("BeDinoArena")
    if arena then for _, item in arena:GetChildren() do propVisual(item) end end
end
RuntimeMeshes.Ready.Event:Connect(upgradeAll)
workspace.DescendantAdded:Connect(function(item)
    if item:IsA("Model") and item:GetAttribute("ResourceId") then task.defer(propVisual, item) end
end)
-- Food shares each source MeshPart; positions and visibility remain server-owned.
local foods = setmetatable({}, {__mode = "k"})
local elapsed = 0
RunService.Heartbeat:Connect(function(dt)
    elapsed += dt
    if elapsed < .15 then return end
    elapsed = 0
    local folder = workspace:FindFirstChild("Food")
    if not folder then return end
    for _, item in folder:GetChildren() do
        if not item:IsA("BasePart") or not item:GetAttribute("Points") then continue end
        local model = foods[item]
        if not model then
            model = RuntimeMeshes.clone(item.Name)
            if not model then continue end
            local sourceHeight = ({berry = .61, fruit = .96, egg = 2.4, amber = 1.3})[item.Name] or 1
            model:ScaleTo(item.Size.Y / sourceHeight)
            model.Name = "LocalFoodMesh"
            model.Parent = item
            foods[item] = model
            item.LocalTransparencyModifier = 1
        end
        model:PivotTo(CFrame.new(item.Position - Vector3.new(0, item.Size.Y / 2 + .08, 0)))
        for _, piece in model:GetDescendants() do
            if piece:IsA("BasePart") then piece.Transparency = item.Transparency end
        end
    end
end)
-- Native models are packaged. Optional API meshes are no longer needed.
