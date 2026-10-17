--!strict
-- Imported meshes are optional until Studio upload; no invented asset IDs.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local RuntimeMeshes = require(script.Parent.RuntimeMeshes)
local ResourceModels = {}
local Authored = require(script.Parent.AuthoredCreatures)
local LowPoly = require(script.Parent.LowPolyDinos)
function ResourceModels.clearTextures(part: BasePart)
    for _,child in part:GetChildren() do
        if child:IsA("SurfaceAppearance") or child:IsA("Decal") or child:IsA("Texture") then child:Destroy() end
    end
    -- Authored creatures paint an EditableImage into TextureContent; Gold/Diamond/silhouette must drop it too.
    if part:IsA("MeshPart") then part.TextureID="";part.TextureContent=Content.none end
end
-- patient=true (previews, may yield): wait for a load slot, retry once, and NEVER fall back to a placeholder
-- box for an authored creature: return nil so the caller shows nothing until a retry succeeds.
function ResourceModels.clone(id: string,genes: any?,patient: boolean?): Model?
    if RunService:IsClient() then
        local lowPoly=LowPoly.clone(id,genes) -- BD-225 spike: nil when the flag is off or the model is not loaded
        if lowPoly then return lowPoly end
        -- BD-381: a preview (patient) never takes the legacy model while the low-poly one is still being loaded; the caller shows the
        -- flat picture and asks again (LowPoly.whenReady). Only a real failure (loader done, no template) falls back to legacy.
        if patient==true and LowPoly.pending(id) then return nil end
        local authored=Authored.clone(id,genes,patient)
        if authored then return authored end
        if patient==true and Authored.has(id) then return nil end
    end
    local folder = ReplicatedStorage:FindFirstChild("Resources")
    local template = if folder then folder:FindFirstChild(id) else nil
    local overrides=ReplicatedStorage:FindFirstChild("ResourceOverrides")
    template=(if overrides then overrides:FindFirstChild(id) else nil) or template
    if not template then -- BD-049/050 Blender kit (native fallback until owner MeshPart uploads)
        local kit = ReplicatedStorage:FindFirstChild("WorldKit")
        template = if kit then kit:FindFirstChild(id) else nil
    end
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
