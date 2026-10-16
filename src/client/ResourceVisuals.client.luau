--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local RuntimeMeshes = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("RuntimeMeshes"))
local Resources = require(ReplicatedStorage.Shared.ResourceModels)
local Appearance = require(ReplicatedStorage.Shared.EggAppearance)
local MutationLook = require(ReplicatedStorage.Shared.MutationLook)
local Http = game:GetService("HttpService")
local LowPoly = require(ReplicatedStorage.Shared.LowPolyDinos) -- BD-225/BD-061: genes + fused tier on the low-poly model
local watched = setmetatable({}, {__mode = "k"})
-- The server shell (DinoVisual) shares geometry with the local mesh; keep it invisible on this client or its
-- original texture z-fights through the genes-painted pattern. Client-local Transparency survives the camera script.
local function hideShell(character: Model)
    local shell = character:FindFirstChild("DinoVisual")
    if not shell or not character:FindFirstChild("LocalMeshVisual") then return end
    for _, item in shell:GetDescendants() do
        if item:IsA("BasePart") and item.Transparency ~= 1 then item:SetAttribute("ShellTransparency",item.Transparency) item.LocalTransparencyModifier = 1 item.Transparency = 1 end
    end
end
local function characterVisual(character: Model)
    local root = character:FindFirstChild("HumanoidRootPart")
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    if not root or not root:IsA("BasePart") or not humanoid then return end
    local id = character:GetAttribute("SpeciesId") or "compy"
    local scale = character:GetAttribute("VisualScale") or 1
    local mutation = character:GetAttribute("MutationVisual") or (if character:GetAttribute("GoldVisual") == true then "gold" else "base")
    local genesJson=character:GetAttribute("GenesJson") or "null"
    local previous = character:FindFirstChild("LocalMeshVisual")
    local function groundFrame()
        local height=root.Size.Y/2+humanoid.HipHeight
        if humanoid.RigType==Enum.HumanoidRigType.R6 then
            local leg=character:FindFirstChild("Left Leg")
            height+=if leg and leg:IsA("BasePart") then leg.Size.Y else 2
        end
        return root.CFrame*CFrame.new(0,-height,0)
    end
    if previous and previous:GetAttribute("SpeciesId") == id and previous:GetAttribute("Mutation") == mutation
        and (genesJson~="null" or previous:GetAttribute("GenesJson")=="null") then
        -- Growth reuses geometry, bones and editable images instead of allocating every pickup.
        if previous:GetAttribute("Scale")~=scale then
            local welds={}
            for _,item in previous:GetDescendants() do
                if item:IsA("Weld") or item:IsA("WeldConstraint") then item.Enabled=false;table.insert(welds,item) end
            end
            previous.WorldPivot=groundFrame()
            previous:ScaleTo(scale);previous:PivotTo(groundFrame());previous:SetAttribute("Scale",scale)
            for _,weld in welds do
                if weld:IsA("Weld") and weld.Part1 then weld.C0=root.CFrame:ToObjectSpace(weld.Part1.CFrame*weld.C1) end -- *C1: drop the low-poly animation offset (BD-225)
                weld.Enabled=true
            end
        end
        hideShell(character)
        if previous:GetAttribute("GenesJson")~=genesJson then
            local ok,genes=pcall(function() return Http:JSONDecode(genesJson) end)
            if ok and typeof(genes)=="table" and (mutation=="base" or previous:GetAttribute("LowPoly")==true) then Appearance.apply(previous,genes) if mutation=="base" then MutationLook.apply(previous,character:GetAttribute("EventMutationId")) end end
            previous:SetAttribute("GenesJson",genesJson)
        end
        return
    end
    local overrides=ReplicatedStorage:FindFirstChild("ResourceOverrides")
    local okGenes,genes=pcall(function() return Http:JSONDecode(genesJson) end)
    local realGenes=if okGenes and typeof(genes)=="table" and (mutation=="base" or LowPoly.enabled()) then genes else nil -- a low-poly fused dino keeps its genes under the tier
    local model = Resources.clone(id,realGenes)
    if not model then
        -- BD-146: the new species has no local mesh (yet). Never keep the OLD species on top: drop it and let the
        -- server shell show until a retry (RuntimeMeshes.Ready / attribute change) succeeds.
        if previous and (previous:GetAttribute("SpeciesId") ~= id or previous:GetAttribute("Mutation") ~= mutation) then
            previous:Destroy()
            local shell = character:FindFirstChild("DinoVisual")
            if shell then
                for _, item in shell:GetDescendants() do
                    if item:IsA("BasePart") then item.LocalTransparencyModifier = 0 item.Transparency = item:GetAttribute("ShellTransparency") or 0 end
                end
            end
        end
        return
    end
    if not character.Parent or not root.Parent then model:Destroy();return end
    for _, extra in character:GetChildren() do
        if extra.Name == "LocalMeshVisual" then extra:Destroy() end -- exactly one local visual per character
    end
    local groundHeight = root.Size.Y / 2 + humanoid.HipHeight
    if humanoid.RigType == Enum.HumanoidRigType.R6 then
        local leg = character:FindFirstChild("Left Leg")
        groundHeight += if leg and leg:IsA("BasePart") then leg.Size.Y else 2
    end
    model.Name = "LocalMeshVisual"
    model:SetAttribute("SpeciesId", id)
    model:SetAttribute("Scale", scale)
    model:SetAttribute("Mutation", mutation)
    model:SetAttribute("GenesJson",genesJson)
    model:ScaleTo(scale)
    model:PivotTo(root.CFrame * CFrame.new(0, -groundHeight, 0))
    local lowPoly = model:GetAttribute("LowPoly") == true
    for _, item in model:GetDescendants() do
        if item:IsA("BasePart") then
            item.Anchored = false
            if not lowPoly and (mutation=="gold" or mutation=="emerald" or mutation=="diamond") then Resources.clearTextures(item) end
            if lowPoly then -- BD-061: LowPoly.applyTier below (additive tint + gloss over the genes, eyes/belly kept)
            elseif mutation == "gold" then item.Color = Color3.fromRGB(242,199,63) item.Material = Enum.Material.Metal
            elseif mutation == "emerald" then item.Color = Color3.fromRGB(46,196,120) item.Material = Enum.Material.Metal item.Reflectance=.1
            elseif mutation == "diamond" then item.Color = Color3.fromRGB(85,213,245) item.Material = Enum.Material.Glass item.Reflectance=.2 end
            -- BD-211: a Weld (not a WeldConstraint) so DinoMotion poses edit C0. Writing part.CFrame on a
            -- WeldConstraint-attached part drags the whole assembly, which made the root rattle every frame.
            local weld = Instance.new("Weld")
            weld.Name = "ResourceWeld"
            weld.C0 = root.CFrame:ToObjectSpace(item.CFrame)
            weld.Part0, weld.Part1, weld.Parent = root, item, item
        end
    end
    model.Parent = character
    if lowPoly then model:SetAttribute("LPTier", if mutation ~= "base" then mutation else nil) model:SetAttribute("LPOwn", character == game:GetService("Players").LocalPlayer.Character) end
    if realGenes then Appearance.apply(model,realGenes) elseif lowPoly then LowPoly.applyTier(model, mutation) end
    hideShell(character)

end
local function watchCharacter(character: Model)
    if watched[character] then return end
    watched[character] = true
    local queued = false
    local dirty = false
    local function refresh()
        if queued then dirty=true return end
        queued = true
        task.defer(function()
            repeat
                dirty=false
                if character.Parent then characterVisual(character) end
            until not dirty or not character.Parent
            queued = false
        end)
    end
    for _, attribute in {"SpeciesId", "VisualScale", "GoldVisual", "MutationVisual", "DinoAttached","GenesJson"} do
        character:GetAttributeChangedSignal(attribute):Connect(refresh)
    end
    character.ChildAdded:Connect(function(child)
        if child.Name == "DinoVisual" then task.delay(.5, function() hideShell(character) end) end
    end)
    character.DescendantAdded:Connect(function(item)
        if item:IsA("BasePart") and item:FindFirstAncestor("DinoVisual") and character:FindFirstChild("LocalMeshVisual") then
            if item.Transparency ~= 1 then item:SetAttribute("ShellTransparency",item.Transparency) end
            item.LocalTransparencyModifier = 1 item.Transparency = 1
        end
    end)
    refresh()
    -- BD-389: on a respawn (after a run or a hatch) the attributes are already set when the character arrives, so no attribute change ever
    -- re-runs characterVisual if the Humanoid/RootPart had not streamed in yet: the old legacy shell stayed visible. Parts arriving
    -- and a short retry ladder (until the local mesh exists, or the low-poly template has loaded) close that gap.
    for _, partName in {"HumanoidRootPart", "Humanoid"} do
        local existing = character:FindFirstChild(partName)
        if not existing then
            local conn
            conn = character.ChildAdded:Connect(function(child) if child.Name == partName then conn:Disconnect() refresh() end end)
        end
    end
    task.spawn(function()
        for _, wait in {0.3, 0.7, 1.5, 3, 6, 10} do
            task.wait(wait)
            if not character.Parent then return end
            if not character:FindFirstChild("LocalMeshVisual") then refresh() end
        end
    end)
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
-- BD-225 spike: the low-poly models replicate after spawn; swap any fallback visual of that species for the low-poly one.
task.spawn(function()
    local LowPoly = require(ReplicatedStorage.Shared.LowPolyDinos)
    if not LowPoly.enabled() then return end
    local folder = ReplicatedStorage:WaitForChild(LowPoly.FolderName, 60)
    if not folder then return end
    folder.ChildAdded:Connect(function(child)
        task.wait(.2)
        for _, player in Players:GetPlayers() do
            local visual = if player.Character then player.Character:FindFirstChild("LocalMeshVisual") else nil
            if visual and visual:GetAttribute("SpeciesId") == child.Name and visual:GetAttribute("LowPoly") ~= true then visual:Destroy() end
        end
        upgradeAll()
    end)
end)
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
        if not item:IsA("BasePart") or not item:GetAttribute("Points") or item:GetAttribute("KitMesh") then continue end
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
        -- Re-pivot only when the server moved the food, so FoodGlow's local bob/spin is not reset every tick.
        local at = item.Position
        if model:GetAttribute("At") ~= at then
            model:SetAttribute("At", at)
            model:PivotTo(CFrame.new(at - Vector3.new(0, item.Size.Y / 2 + .08, 0)))
        end
        for _, piece in model:GetDescendants() do
            if piece:IsA("BasePart") then piece.Transparency = item.Transparency end
        end
    end
end)
-- Native models are packaged. Optional API meshes are no longer needed.
