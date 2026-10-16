--!strict
-- BD-225 spike: low-poly generated base dinos (flag Config.LowPolyDinos, OFF by default). The server loader
-- (src/server/LowPolyDinoLoader.luau) puts the published Models into ReplicatedStorage.LowPolyDinoModels; clients clone from there.
-- clone() returns nil when the flag is off, the species is unmapped or the model did not load, so callers keep the current visual.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(script.Parent.Config)
local Assets = require(script.Parent.LowPolyDinoAssets)
local Genetics = require(script.Parent.EggGenetics)
local LowPoly = {}
LowPoly.FolderName = "LowPolyDinoModels"

function LowPoly.enabled(): boolean
    return (Config :: any).LowPolyDinos == true
end
function LowPoly.has(speciesId: string): boolean
    return LowPoly.enabled() and Assets[speciesId] ~= nil
end
-- Generated part names look like `"left arm"_geom`; classify by keywords, tolerant of quotes and brackets.
function LowPoly.roleOf(name: string): string?
    local n = string.lower(name)
    for _, role in {"head", "tail", "arm", "leg", "body"} do
        if string.find(n, role, 1, true) then return role end
    end
    return nil
end
local function template(speciesId: string): Model?
    local folder = ReplicatedStorage:FindFirstChild(LowPoly.FolderName)
    local item = if folder then folder:FindFirstChild(speciesId) else nil
    return if item and item:IsA("Model") then item else nil
end
-- Colours on the flat facets. Body = the dino's blended gene colour; head/tail/limbs lean to the secondary colour so both
-- genes show. Matte (docs/173): no gloss, no texture. Spots/stripes (PatternGenes needs per-species UV data) are NOT on low-poly yet.
function LowPoly.tint(container: Instance, genes: any)
    if not genes or not Genetics.valid(genes) then return end
    local base = Genetics.tint(genes)
    local second = Genetics.color(genes.secondaryColorId).rgb
    local accent = base:Lerp(Color3.fromRGB(second[1], second[2], second[3]), 0.45)
    for _, part in container:GetDescendants() do
        if part:IsA("MeshPart") then
            part.TextureID = ""
            part.TextureContent = Content.none
            part.Color = if part:GetAttribute("LPRole") == "body" then base else accent
            part.Material, part.Reflectance = Enum.Material.Plastic, 0
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
        part:SetAttribute("LPSide", if part.Position.X < box.Position.X then -1 else 1)
        part:SetAttribute("LPLead", part.Position.Z < bodyZ)
        part.CanCollide, part.CanTouch, part.CanQuery, part.Massless = false, false, false, true
        part.Size *= k
        part.CFrame = CFrame.new((part.Position - origin) * k) * part.CFrame.Rotation
    end
    copy.WorldPivot = CFrame.new()
    copy.Name = speciesId
    copy:SetAttribute("LowPoly", true)
    copy:SetAttribute("UploadedModelId", info.assetId)
    copy:SetAttribute("LowPolyVersion", info.version)
    LowPoly.tint(copy, genes)
    return copy
end
return LowPoly
