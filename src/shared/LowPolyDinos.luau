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
local Tier = require(script.Parent.LowPolyTier)
local Recolor = require(script.Parent.LowPolyRecolor)
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
-- Template geometry of one part (unscaled, unposed) for the 3D pattern bake: mesh id, CFrame relative to the model centre,
-- mesh->part scale and 1 / the longest model side. nil when the template is gone (the bake then uses the UV-space pattern).
local geomCache: {[string]: any} = {}
function LowPoly.geometry(speciesId: string, partName: string): any?
    local key = speciesId .. "/" .. partName
    if geomCache[key] ~= nil then return geomCache[key] or nil end
    local source = template(speciesId)
    local part = if source then source:FindFirstChild(partName) else nil
    if not source or not part or not part:IsA("MeshPart") then return nil end
    local box, size = source:GetBoundingBox()
    local ms = part.MeshSize
    local scale = Vector3.new(part.Size.X / math.max(ms.X, 1e-6), part.Size.Y / math.max(ms.Y, 1e-6), part.Size.Z / math.max(ms.Z, 1e-6))
    local geom = {meshId = part.MeshId, cframe = box:ToObjectSpace(part.CFrame), scale = scale, norm = 1 / math.max(size.X, size.Y, size.Z, 1e-6)}
    geomCache[key] = geom
    return geom
end
-- Gene colours AND patterns (docs/87 low-poly language: matte, solid black eyes, cream belly). The model's own texture is KEPT, so
-- eyes/belly never disappear: it is shown immediately (tinted by MeshPart.Color as the cheap fallback), then each part's texture is
-- swapped for a bake (LowPolyTexture: LowPolyRecolor colours + LowPolyPattern procedural mask in the part's own UV space + LowPolyTier
-- additive tint) that only touches body-colour pixels. Blank pattern = the blended gene colour; any other pattern = primary colour
-- with the secondary colour in the pattern regions, the share following genes.blend. Fused tier (LPTier attribute, "gold" /
-- "emerald" / "diamond") adds the tier tint, Metal/Glass + reflectance on body-colour parts and one soft sparkle; base stays matte.
local genesOf = setmetatable({} :: {[Instance]: any}, {__mode = "k"})
LowPoly.Far = 160 -- studs: beyond this a world dino keeps the cheap tint (BD-203 LOD rule)
local function sparkle(container: Instance, body: BasePart?, entry: any?)
    local old = container:FindFirstChild("LPTierSparkle", true)
    if old then old:Destroy() end
    if not entry or not body or entry.sparkleRate <= 0 then return end
    local Effects = require(script.Parent.EffectAssets)
    local emitter = Instance.new("ParticleEmitter")
    emitter.Name = "LPTierSparkle"
    emitter.Texture = Effects.resolve("sparkSheet")
    if Effects.isSheet("sparkSheet") then
        emitter.FlipbookLayout, emitter.FlipbookMode = Enum.ParticleFlipbookLayout.Grid4x4, Enum.ParticleFlipbookMode.OneShot
    end
    emitter.Color = ColorSequence.new(Color3.fromRGB(entry.sparkle[1], entry.sparkle[2], entry.sparkle[3]))
    emitter.LightEmission, emitter.LightInfluence = 0.6, 0.3
    emitter.Rate, emitter.Lifetime = entry.sparkleRate, NumberRange.new(0.8, 1.2)
    emitter.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(0.4, 0.55), NumberSequenceKeypoint.new(1, 0)})
    emitter.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.3, 0.2), NumberSequenceKeypoint.new(1, 1)})
    emitter.Speed, emitter.SpreadAngle, emitter.Rotation = NumberRange.new(0.2, 0.5), Vector2.new(180, 180), NumberRange.new(0, 360)
    emitter.Parent = body
end
function LowPoly.tint(container: Instance, genes: any)
    if genes then genesOf[container] = genes else genes = genesOf[container] end
    local entry = Tier.get(container:GetAttribute("LPTier"))
    local species = tostring(container:GetAttribute("LPSpecies") or container.Name)
    local valid = genes ~= nil and Genetics.valid(genes)
    local spec: Texture.Spec? = nil
    if valid then
        local a, b = Genetics.color(genes.primaryColorId).rgb, Genetics.color(genes.secondaryColorId).rgb
        local patternId = if genes.patternId and table.find(Genetics.Patterns, genes.patternId) then genes.patternId else "01_blank"
        local primary = if patternId == "01_blank" then Genetics.tint(genes) else Color3.fromRGB(a[1], a[2], a[3])
        spec = {primary = primary, secondary = Color3.fromRGB(b[1], b[2], b[3]), same = genes.primaryColorId == genes.secondaryColorId,
            primaryShare = math.clamp((genes.blend or 50) / 100, 0, 1), patternId = patternId, tier = if entry then entry.id else nil, seedName = ""}
    elseif not entry then return end
    local camera = workspace.CurrentCamera
    local body: BasePart? = nil
    for _, part in container:GetDescendants() do
        if part:IsA("MeshPart") then
            local textureId = part:GetAttribute("LPTexture")
            local role = tostring(part:GetAttribute("LPRole") or "body")
            if role == "body" and not body then body = part end
            local eyeish = type(textureId) ~= "string" or textureId == ""
            -- BD-173: base dinos matte; only a fused tier gets Metal/Glass + reflectance, and only on textured body-colour parts.
            if entry and not eyeish then
                part.Material = (Enum.Material :: any)[entry.material] or Enum.Material.Metal
                part.Reflectance = math.min(entry.reflectance, Tier.MaxReflectance)
            else part.Material, part.Reflectance = Enum.Material.Plastic, 0 end
            if eyeish or not spec then part.Color = Color3.new(1, 1, 1) continue end
            local s = table.clone(spec :: Texture.Spec)
            s.seedName = species .. "|" .. role
            local base = Texture.baseOf(textureId) or Recolor.baseOf(species)
            local fr, fg, fb = Recolor.flatTint(base, s.primary.R, s.primary.G, s.primary.B)
            local key = Texture.key(textureId, s)
            if part:GetAttribute("LPTintKey") == key and part:GetAttribute("LPLod") == "texture" then continue end
            part:SetAttribute("LPTintKey", key)
            local far = camera ~= nil and part:IsDescendantOf(workspace) and (camera.CFrame.Position - part.Position).Magnitude > LowPoly.Far
            if far then Texture.release(part) part.TextureID = textureId part.Color = Color3.new(fr, fg, fb) part:SetAttribute("LPLod", "tint") continue end
            local geom = LowPoly.geometry(species, part.Name)
            part:SetAttribute("LPLod", "baking")
            task.spawn(function()
                local content = Texture.acquire(part, textureId, species, s, geom)
                if not part.Parent or part:GetAttribute("LPTintKey") ~= key then return end
                if content then part.TextureContent, part.Color = content, Color3.new(1, 1, 1) part:SetAttribute("LPLod", "texture")
                else
                    local b = Texture.baseOf(textureId) or base
                    part.TextureID = textureId part.Color = Color3.new(Recolor.flatTint(b, s.primary.R, s.primary.G, s.primary.B)) part:SetAttribute("LPLod", "tint")
                end
            end)
            -- cheap tint shows at once while the bake runs (or stays when the cache is full)
            if part:GetAttribute("LPLod") ~= "texture" then part.Color = Color3.new(fr, fg, fb) end
        end
    end
    sparkle(container, body, entry)
end
-- Fused tier look on a low-poly model (nil / "base" / false restores matte). Reads the same stage strings as the rest of the game.
function LowPoly.applyTier(container: Instance, stage: any)
    local entry = Tier.get(stage)
    container:SetAttribute("LPTier", if entry then entry.id else nil)
    for _, part in container:GetDescendants() do
        if part:IsA("MeshPart") then part:SetAttribute("LPTintKey", nil) end
    end
    LowPoly.tint(container, nil)
end
-- Maintenance (client only): far world dinos drop to the cheap tint, near ones get their bake back as slots free up.
if game:GetService("RunService"):IsClient() then
    task.spawn(function()
        while true do
            task.wait(1.5)
            if not LowPoly.enabled() then continue end
            pcall(function()
                local camera = workspace.CurrentCamera
                for container, _ in genesOf do
                    if camera and container.Parent and container:IsDescendantOf(workspace) then
                        local dirty = false
                        for _, part in container:GetDescendants() do
                            if part:IsA("MeshPart") and part:GetAttribute("LPTexture") then
                                local far = (camera.CFrame.Position - part.Position).Magnitude > LowPoly.Far
                                local lod = part:GetAttribute("LPLod")
                                if (far and lod == "texture") or (not far and lod == "tint") then part:SetAttribute("LPTintKey", nil) dirty = true end
                            end
                        end
                        if dirty then LowPoly.tint(container, nil) end
                    end
                end
            end)
        end
    end)
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
    -- the first bake waits one frame so the caller can still set LPTier (ResourceVisuals, DinosaurPreview) before any image is baked
    if genes then genesOf[copy] = genes task.defer(function() if copy.Parent then LowPoly.tint(copy, nil) end end) end
    return copy
end
return LowPoly
