--!strict
-- Imported meshes are optional until Studio upload; no invented asset IDs.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local RuntimeMeshes = require(script.Parent.RuntimeMeshes)
local ResourceModels = {}
local Authored = require(script.Parent.AuthoredCreatures)
function ResourceModels.clearTextures(part: BasePart)
    for _,child in part:GetChildren() do
        if child:IsA("SurfaceAppearance") or child:IsA("Decal") or child:IsA("Texture") then child:Destroy() end
    end
    if part:IsA("MeshPart") then part.TextureID="" end
end
function ResourceModels.clone(id: string): Model?
    if RunService:IsClient() then
        local authored=Authored.clone(id)
        if authored then return authored end
    end
    local folder = ReplicatedStorage:FindFirstChild("Resources")
    local template = if folder then folder:FindFirstChild(id) else nil
    local overrides=ReplicatedStorage:FindFirstChild("ResourceOverrides")
    template=(if overrides then overrides:FindFirstChild(id) else nil) or template
    if not template then return if RunService:IsClient() then RuntimeMeshes.clone(id) else nil end
    local copy: Model
    if template:IsA("Model") then
        copy = template:Clone()
    elseif template:IsA("BasePart") then
        copy = Instance.new("Model")
        local part = template:Clone()
        part.Parent = copy
        copy.PrimaryPart = part
    else
        return nil
    end
    -- Only geometry and appearance survive import. Never execute imported code.
    for _, item in copy:GetDescendants() do
        if item:IsA("LuaSourceContainer") then item:Destroy()
        elseif item:IsA("BasePart") then
            item.CanCollide = false
            item.CanTouch = false
            item.CanQuery = false
            item.Massless = true
        end
    end
    -- Normalize the pivot to the ground under the bounding-box center. Keep imported -Z facing.
    copy.PrimaryPart = nil
    local box, size = copy:GetBoundingBox()
    local origin = box.Position - Vector3.new(0, size.Y / 2, 0)
    copy.WorldPivot = CFrame.new(origin)
    copy:SetAttribute("GeometryOrigin", origin)
    copy.Name = id
    return copy
end
return ResourceModels
