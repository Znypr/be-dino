--!strict
-- BD-225 spike: low-poly generated base dinos (flag Config.LowPolyDinos, OFF by default). The server loader
-- (src/server/LowPolyDinoLoader.luau) puts the published Models into ReplicatedStorage.LowPolyDinoModels; clients clone from there.
-- clone() returns nil when the flag is off, the species is unmapped or the model did not load, so callers keep the current visual.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(script.Parent.Config)
local Assets = require(script.Parent.LowPolyDinoAssets)
local Genetics = require(script.Parent.EggGenetics)
local Texture = require(script.Parent.LowPolyTexture)
local Pose = require(script.Parent.LowPolyPose)
local LowPoly = {}
LowPoly.FolderName = "LowPolyDinoModels"

function LowPoly.enabled(): boolean
    return (Config :: any).LowPolyDinos == true
end
function LowPoly.has(speciesId: string): boolean
    return LowPoly.enabled() and Assets[speciesId] ~= nil
end
-- Generated part names look like `"left arm"_geom`; classification lives in the pure LowPolyPose.roleOf (offline-tested per species).
function LowPoly.roleOf(name: string): string?
    return Pose.roleOf(name)
end
local function template(speciesId: string): Model?
    local folder = ReplicatedStorage:FindFirstChild(LowPoly.FolderName)
    local item = if folder then folder:FindFirstChild(speciesId) else nil
    return if item and item:IsA("Model") then item else nil
end
-- Gene colours (docs/87 low-poly language: matte, solid black eyes, cream belly). The model's own texture is KEPT, so eyes/belly never
-- disappear: it is shown immediately, then each part's texture is swapped for a gene-coloured bake (LowPolyTexture/LowPolyRecolor) that
-- only recolours body-colour pixels. If the bake is unavailable the original species-coloured texture simply stays. Body = blended gene
-- colour; head/tail/limbs lean to the secondary colour. Spots/stripes (PatternGenes needs per-species UV data) are NOT on low-poly yet.
function LowPoly.tint(container: Instance, genes: any)
    if not genes or not Genetics.valid(genes) then return end
    local base = Genetics.tint(genes)
    local second = Genetics.color(genes.secondaryColorId).rgb
    local accent = base:Lerp(Color3.fromRGB(second[1], second[2], second[3]), 0.45)
    local species = tostring(container:GetAttribute("LPSpecies") or container.Name)
    for _, part in container:GetDescendants() do
        if part:IsA("MeshPart") then
            part.Color = Color3.new(1, 1, 1)
            part.Material, part.Reflectance = Enum.Material.Plastic, 0
            local textureId = part:GetAttribute("LPTexture")
            if type(textureId) ~= "string" or textureId == "" then continue end
            local color = if part:GetAttribute("LPRole") == "body" then base else accent
            local key = Texture.key(textureId, color)
            part:SetAttribute("LPTintKey", key)
            task.spawn(function()
                local content = Texture.bake(textureId, species, color)
                if content and part.Parent and part:GetAttribute("LPTintKey") == key then part.TextureContent = content end
            end)
        end
    end
end
function LowPoly.clone(speciesId: string, genes: any?): Model?
    if not LowPoly.has(speciesId) then return nil end
    local source = template(speciesId)
    if not source then return nil end
    local copy = source:Clone()
    local info = (Assets :: any)[speciesId]
    local parts: {MeshPart} = {}
    for _, item in copy:GetDescendants() do
        if item:IsA("LuaSourceContainer") then item:Destroy()
        elseif item:IsA("MeshPart") then table.insert(parts, item) end
    end
    if #parts == 0 then copy:Destroy() return nil end
    local box, size = copy:GetBoundingBox()
    local origin = box.Position - Vector3.new(0, size.Y / 2, 0)
    local bodyZ = box.Position.Z
    local k: number = info.scale
    for _, part in parts do
        local role = LowPoly.roleOf(part.Name)
        part:SetAttribute("LPRole", role or "body")
        part:SetAttribute("LPTexture", part.TextureID) -- the model's own texture (eyes, belly), kept as the fallback
        part:SetAttribute("LPSide", if part.Position.X < box.Position.X then -1 else 1)
        part:SetAttribute("LPLead", part.Position.Z < bodyZ)
        part.CanCollide, part.CanTouch, part.CanQuery, part.Massless = false, false, false, true
        part.Size *= k
        part.CFrame = CFrame.new((part.Position - origin) * k) * part.CFrame.Rotation
    end
    copy.WorldPivot = CFrame.new()
    copy.Name = speciesId
    copy:SetAttribute("LPSpecies", speciesId)
    copy:SetAttribute("LowPoly", true)
    copy:SetAttribute("UploadedModelId", info.assetId)
    copy:SetAttribute("LowPolyVersion", info.version)
    copy:SetAttribute("LPClass", info.class)
    LowPoly.tint(copy, genes)
    return copy
end
return LowPoly
