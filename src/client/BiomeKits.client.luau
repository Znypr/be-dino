--!strict
-- BD-1315 (docs/250 S2): the biome-kit swap. The whole World V3 island is one biome at a time (S1, BD-1314, workspace attribute CurrentBiome).
-- When the biome changes (inside the storm, which hides the island), every placed plant and rock slot is re-skinned on THIS client with its
-- biome kit mesh (Shared/VegetationV2 kitVisual), or shows nothing where the kit is sparser (kitHidden, collider-free slots only), or goes back
-- to its own mesh (meadow / no kit piece). Look only: placements, colliders, food and every server object stay exactly as they are; the
-- original mesh is hidden with LocalTransparencyModifier and the kit mesh is a local child of the same model, so WorldCulling (which
-- re-parents whole models) keeps working. Fallen logs and props without the server's Kit attributes (Arena) are never touched.
-- Off unless VegetationV2 (WorldV3 + ToonWorld + VegetationV2Enabled) and BiomeRotation (BiomeRotationEnabled) are both on.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Veg = require(Shared:WaitForChild("VegetationV2"))
local Rotation = require(Shared:WaitForChild("BiomeRotation"))
local Kit = require(Shared:WaitForChild("WorldKitData"))
if not Veg.enabled(Config) or not Rotation.enabled(Config) then return end

local BATCH = 120 -- slots re-skinned per frame (about 1,500 slots: the swap finishes in well under a second, inside the storm)
local MESH = "BiomeKitMesh"

type Slot = {model: Model, id: string, roll: number, layer: string, scale: number, applied: string}
local slots: {Slot} = {}
local seen: {[Instance]: boolean} = {}
local current = "meadow"

local fitted: {[string]: Vector3} = {} -- key|kit id -> mesh size at kit scale 1
local function meshSize(key: string, id: string, template: MeshPart): Vector3
    local cacheKey = key .. "|" .. id
    if not fitted[cacheKey] then
        local s = template.Size
        fitted[cacheKey] = s * Veg.fit(Kit[id].kind, Kit[id].extent, {s.X, s.Y, s.Z})
    end
    return fitted[cacheKey]
end

local function setOriginal(model: Model, visible: boolean)
    for _, d in model:GetDescendants() do
        if d:IsA("BasePart") and d.Name ~= MESH then d.LocalTransparencyModifier = if visible then 0 else 1 end
    end
end

local function apply(slot: Slot, biome: string)
    if slot.applied == biome then return end
    slot.applied = biome
    local model = slot.model
    local old = model:FindFirstChild(MESH)
    if old then old:Destroy() end
    if Veg.kitHidden(biome, slot.id, slot.roll, slot.layer) then
        setOriginal(model, false)
        return
    end
    local key = Veg.kitVisual(biome, slot.id, slot.roll, slot.layer)
    local folder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local template = if key and Veg.ready(key) and folder then folder:FindFirstChild(key) else nil
    if not key or not template or not template:IsA("MeshPart") then
        setOriginal(model, true) -- meadow, no kit piece for this slot, or the mesh did not load: the slot keeps its own look
        return
    end
    local mesh = template:Clone()
    mesh.Name = MESH
    mesh.Size = meshSize(key, slot.id, template) * slot.scale
    mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless = true, false, false, false, true
    mesh.Color = Color3.new(1, 1, 1)
    mesh.CFrame = model:GetPivot() * CFrame.new(0, mesh.Size.Y / 2, 0)
    setOriginal(model, false)
    mesh.Parent = model
end

local function track(item: Instance)
    if seen[item] or not item:IsA("Model") then return end
    local scale, layer, roll = item:GetAttribute("KitScale"), item:GetAttribute("KitLayer"), item:GetAttribute("KitRoll")
    if type(scale) ~= "number" or type(layer) ~= "string" or type(roll) ~= "number" or layer == "log" or not Kit[item.Name] then return end
    seen[item] = true
    local slot: Slot = {model = item, id = item.Name, roll = roll, layer = layer, scale = scale, applied = "meadow"}
    table.insert(slots, slot)
    if current ~= "meadow" then apply(slot, current) end
end

local function swapAll(biome: string)
    current = biome
    for i, slot in slots do
        apply(slot, biome)
        if i % BATCH == 0 then task.wait() end
    end
end

local function biomeNow(): string
    local b = workspace:GetAttribute("CurrentBiome")
    return if type(b) == "string" and Rotation.Looks[b] then b else "meadow"
end

task.spawn(function()
    local arena = workspace:WaitForChild("BeDinoArena", 120)
    local kitFolder = if arena then arena:WaitForChild("WorldKit", 60) else nil
    if not kitFolder then return end
    for _, child in kitFolder:GetChildren() do track(child) end
    kitFolder.ChildAdded:Connect(track) -- props arrive over several frames; WorldCulling re-parents culled ones (seen keeps them once)
    swapAll(biomeNow())
    workspace:GetAttributeChangedSignal("CurrentBiome"):Connect(function()
        local b = biomeNow()
        if b ~= current then swapAll(b) end
    end)
end)
