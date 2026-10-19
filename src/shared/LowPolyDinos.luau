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
local Lod = require(script.Parent.EffectsLod)
local MutationLook = require(script.Parent.MutationLook)
local Recolor = require(script.Parent.LowPolyRecolor)
local Ready = require(script.Parent.LowPolyReady)
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
-- BD-381: true while the template of a mapped species has not replicated yet and the server loader is still running. Callers that
-- would otherwise fall back to the legacy model (previews) wait instead; the character visual self-heals through ResourceVisuals.
local startedAt = os.clock()
function LowPoly.pending(speciesId: string): boolean
    if not LowPoly.has(speciesId) then return false end
    return Ready.pending(true, true, template(speciesId) ~= nil, workspace:GetAttribute("LowPolyDinosLoaded") ~= nil, os.clock() - startedAt)
end
-- Fires `callback` once when `pending` turns false (template arrived, loader done or timeout). Returns immediately when not pending.
function LowPoly.whenReady(speciesId: string, callback: () -> ())
    if not LowPoly.pending(speciesId) then callback() return end
    task.spawn(function()
        while LowPoly.pending(speciesId) do task.wait(0.25) end
        callback()
    end)
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
local function motionEnabled(): boolean
    if not game:GetService("RunService"):IsClient() then return true end
    local ok, theme = pcall(function() return require(script.Parent.UITheme) end)
    return not ok or theme.MotionEnabled ~= false
end
-- BD-308: sparkle sized and rated with the dino (a T-Rex gets bigger, more frequent sparks than a Compy), none under Reduce Motion
-- (Calm motion): the tier then reads by its tint, baked sheen and material alone (nothing moves).
local function sparkle(container: Instance, body: BasePart?, entry: any?)
    local old = container:FindFirstChild("LPTierSparkle", true)
    if old then old:Destroy() end
    -- Effects Off: no particles at all (the material, gloss and baked sheen still carry the tier); Lite: half the sparks.
    local okS, SettingsModel = pcall(function() return require(script.Parent.SettingsModel) end)
    local fx = if okS and SettingsModel and SettingsModel.effects then SettingsModel.effects() else "full"
    if not entry or not body or entry.sparkleRate <= 0 or not motionEnabled() or fx == "off" then return end
    local Effects = require(script.Parent.EffectAssets)
    local longest = 6 -- a Compy is about 6 studs long after LowPolyDinoAssets.scale, a T-Rex about 12
    if container:IsA("Model") then local _, size = container:GetBoundingBox() longest = math.max(size.X, size.Y, size.Z, 1) end
    local k = math.clamp(longest / 6, 0.7, 2)
    local emitter = Instance.new("ParticleEmitter")
    emitter.Name = "LPTierSparkle"
    emitter.Texture = Effects.resolve("sparkSheet")
    if Effects.isSheet("sparkSheet") then
        emitter.FlipbookLayout, emitter.FlipbookMode = Enum.ParticleFlipbookLayout.Grid4x4, Enum.ParticleFlipbookMode.OneShot
    end
    if entry.shimmer then -- Diamond: slow icy rainbow shimmer (the spark colour drifts through the list over its life)
        local pts = {}
        for i, c in entry.shimmer do pts[i] = ColorSequenceKeypoint.new((i - 1) / (#entry.shimmer - 1), Color3.fromRGB(c[1], c[2], c[3])) end
        emitter.Color = ColorSequence.new(pts)
    else emitter.Color = ColorSequence.new(Color3.fromRGB(entry.sparkle[1], entry.sparkle[2], entry.sparkle[3])) end
    emitter.LightEmission, emitter.LightInfluence = 1, 0
    -- few but crisp: sparkleCount concurrent twinkles (Gold 3 / Emerald 5 / Diamond 7), each ~1.2 s, big enough to read at ~20 studs
    emitter.Rate, emitter.Lifetime = entry.sparkleCount / Tier.SparkleBase * (if fx == "lite" then 0.5 else 1), NumberRange.new(Tier.SparkleLife[1], Tier.SparkleLife[2])
    local sz = entry.sparkleSize * math.clamp(k, 0.9, 1.6)
    -- short glint flash: the spark pops to 1.5x in the first 12 % of its life, settles to full size, then fades (bright at once, not a slow fade-in)
    emitter.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(0.12, sz * 1.5), NumberSequenceKeypoint.new(0.4, sz), NumberSequenceKeypoint.new(1, 0)})
    emitter.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.6), NumberSequenceKeypoint.new(0.12, 0), NumberSequenceKeypoint.new(0.7, 0.1), NumberSequenceKeypoint.new(1, 1)})
    emitter.ZOffset = 1
    emitter.Speed, emitter.SpreadAngle, emitter.Rotation = NumberRange.new(0.2, 0.5), Vector2.new(180, 180), NumberRange.new(0, 360)
    emitter.Parent = body
end
-- Glowing tier rim (2026-10-16 round 7, docs/114): a thin lit outline round the whole silhouette in the tier colour. The local player's dino
-- and previews always get a real Highlight; other fused dinos get one while under EffectsLod.RimHighlights (far below Roblox's 31), the rest
-- get the cheap glow (one slightly larger Neon shell on the body part). Effects Off = no rim. Material look (gloss, horns, claws) stays.
local liveRims: {[Instance]: boolean} = {}
local function rimCount(): number local n = 0 for _ in liveRims do n += 1 end return n end
local function rim(container: Instance, entry: any?, body: BasePart?)
    for _, name in {"LPTierRim", "LPTierGlow"} do
        local old = container:FindFirstChild(name, true)
        if old then liveRims[old] = nil old:Destroy() end
    end
    if not entry or not container:IsA("Model") then return end
    local mode = "full"
    local okS, SettingsModel = pcall(function() return require(script.Parent.SettingsModel) end)
    if okS and SettingsModel and SettingsModel.effects then mode = SettingsModel.effects() end
    local own = container:GetAttribute("LPOwn") == true or container:FindFirstAncestorOfClass("ViewportFrame") ~= nil
    local c = entry.rim
    local col = Color3.fromRGB(c[1], c[2], c[3])
    local trans = math.clamp(entry.rimTransparency, Tier.RimTransparency[1], Tier.RimTransparency[2])
    local cap = math.min((Lod.RimHighlights :: any)[mode] or 0, Lod.RimHighlightHardCap - 1)
    if own or rimCount() < cap then
        local h = Instance.new("Highlight")
        h.Name, h.Adornee = "LPTierRim", container
        local o = entry.outline
        local outlineCol = if o then Color3.fromRGB(o[1], o[2], o[3]) else col:Lerp(Color3.new(1, 1, 1), Tier.HighlightWhiten)
        h.FillColor, h.OutlineColor, h.FillTransparency, h.OutlineTransparency = col, outlineCol, entry.rimFill or Tier.HighlightFill, 0
        h.DepthMode = Enum.HighlightDepthMode.Occluded
        h.Parent = container
        liveRims[h] = true
        h.Destroying:Once(function() liveRims[h] = nil end)
    end
    if mode == "off" then return end
    -- soft glow (round 8): inflated Neon shell copies on EVERY textured part (body, head, tail, legs, arms); two layers = gradient falloff
    -- (Effects Lite: the outer soft layer only). Mostly seen at the silhouette; high transparency keeps the dino's own colours.
    if not Tier.UseGlowShells then return end
    local layers = if mode == "lite" then {Tier.GlowLayers[2]} else Tier.GlowLayers
    for _, p in container:GetDescendants() do
        local texId = if p:IsA("MeshPart") then p:GetAttribute("LPTexture") else nil
        if p:IsA("MeshPart") and type(texId) == "string" and texId ~= "" and not Tier.isAccentName(p.Name) then
            for i, layer in layers do
                local shell = p:Clone()
                for _, ch in shell:GetChildren() do ch:Destroy() end
                shell.Name, shell.TextureID = "LPTierGlow", ""
                shell:SetAttribute("LPTexture", nil) shell:SetAttribute("LPRole", nil)
                shell.Size, shell.Color, shell.Material, shell.Reflectance = p.Size * layer[1], col, Enum.Material.Neon, 0
                shell.Transparency = layer[2]
                shell.CanCollide, shell.CanQuery, shell.CanTouch, shell.Massless, shell.CastShadow = false, false, false, true, false
                shell.CFrame = p.CFrame
                local w = Instance.new("WeldConstraint")
                w.Part0, w.Part1 = p, shell
                w.Parent = shell
                shell.Parent = p
            end
        end
    end
end
-- Fallback (bake denied / cache full / far away): the model's OWN texture stays (eyes, belly, claws intact, species colour). A plain
-- MeshPart.Color is ignored on a textured MeshPart in Studio, so no tint is applied (docs/105: option 'keep the original texture').
-- One part's bake (body/head 256 px, other parts 128 px; BD-306): texture on success, the cheap tint when denied / full / failed.
local function partBake(container: Instance, species: string, part: MeshPart, textureId: string, role: string, spec: Texture.Spec, key: string)
    part:SetAttribute("LPLod", "baking")
    local geom = LowPoly.geometry(species, part.Name)
    local content = Texture.acquire(part, textureId, species, spec, geom, Texture.sizeFor(role), function() return part.Parent ~= nil and container:GetAttribute("LPLookKey") == key end)
    if not part.Parent or container:GetAttribute("LPLookKey") ~= key then return end
    if content then part.TextureContent, part.Color = content, Color3.new(1, 1, 1) part:SetAttribute("LPLod", "texture")
    else part.TextureID = textureId part.Color = Color3.new(1, 1, 1) part:SetAttribute("LPLod", "tint") end
end
-- Template lookup: ReplicatedStorage.TierCoatTemplates is written by tools/build.py (tools/tier_coat.py) from Tier.Maps.
local function coatTemplate(species: string, partName: string, tierId: string): Instance?
    local folder = ReplicatedStorage:FindFirstChild(Tier.TemplateFolder)
    local item = if folder then folder:FindFirstChild(Tier.templateName(species, partName, tierId)) else nil
    return if item and item:IsA("SurfaceAppearance") then item else nil
end
-- 2026-10-16 FINAL owner rule: "same exact colours and pattern, plus a semi-translucent glossy tier layer over it". The layer is a second,
-- slightly inflated copy of each textured body MeshPart (same mesh, welded, no collision / query / touch, Massless): +1 part per textured part
-- (a 7-part dino stays well inside the low-poly part budget; tris double only on those parts, no extra textures). Previews/ViewportFrames get it too.
local function shells(container: Instance, entry: any?)
    for _, old in container:GetDescendants() do if old.Name == "LPTierShell" then old:Destroy() end end
    if not entry then return end
    for _, p in container:GetDescendants() do
        local texId = if p:IsA("MeshPart") then p:GetAttribute("LPTexture") else nil
        if p:IsA("MeshPart") and type(texId) == "string" and texId ~= "" and not Tier.isAccentName(p.Name) then
            local shell = p:Clone()
            for _, ch in shell:GetChildren() do ch:Destroy() end
            shell.Name = "LPTierShell"
            shell.TextureID = ""
            shell:SetAttribute("LPTexture", nil) shell:SetAttribute("LPRole", nil)
            shell.Size = p.Size * Tier.ShellScale
            shell.Color = Color3.fromRGB(entry.shell[1], entry.shell[2], entry.shell[3])
            shell.Material = (Enum.Material :: any)[entry.shellMaterial] or Enum.Material.SmoothPlastic
            shell.Reflectance = math.min(entry.shellReflectance, Tier.MaxShellReflectance)
            shell.Transparency = math.clamp(entry.shellTransparency, Tier.ShellTransparency[1], Tier.ShellTransparency[2])
            -- approach C (docs/115): the SurfaceAppearance is a TEMPLATE authored in the place at build time (a runtime-made one does not render)
            -- and only CLONED here. No template for this species / part / tier (no map yet) = the plain translucent shell above, unchanged.
            local tpl = coatTemplate(tostring(container:GetAttribute("LPSpecies") or container.Name), p.Name, entry.id)
            if tpl then -- alpha lives in the ColorMap (AlphaMode Transparency), so the part itself is opaque and its look comes from the maps
                shell.Material, shell.Reflectance, shell.Color, shell.Transparency = Enum.Material.SmoothPlastic, 0, Color3.new(1, 1, 1), 0
                local coat = tpl:Clone()
                -- Owner 2026-10-17: "the sides / corners aren't glowing enough" -> the coat's own ColorMap is its emissive mask (edge-weighted
                -- alpha), so the tier edges glow without washing the stripes. Lead Studio tuning: strength 6.
                local glow = Tier.CoatGlow[entry.id]
                if glow then
                    pcall(function() -- EmissiveMaskContent is a newer API; an older client simply keeps the unlit coat
                        local sa: any = coat
                        sa.EmissiveMaskContent = Content.fromUri(sa.ColorMap)
                        sa.EmissiveStrength = glow.strength
                        sa.EmissiveTint = Color3.fromRGB(glow.tint[1], glow.tint[2], glow.tint[3])
                    end)
                end
                coat.Parent = shell
            end
            shell.CanCollide, shell.CanQuery, shell.CanTouch, shell.Massless, shell.CastShadow = false, false, false, true, false
            shell.CFrame = p.CFrame
            local w = Instance.new("WeldConstraint")
            w.Part0, w.Part1 = p, shell
            w.Parent = shell
            shell.Parent = p
        end
    end
end
-- BD-518: the event mutation (ember, frost ...) rides on the container attribute LPMutation and is BAKED into the body-colour pixels
-- (MeshPart.Color is ignored on a baked texture, so MutationLook.apply alone shows nothing on a low-poly dino). Never on fused tiers.
local function mutationOf(container: Instance, tier: any): string?
    local id = container:GetAttribute("LPMutation")
    if tier or type(id) ~= "string" or id == "" or not MutationLook.get(id) then return nil end
    return id
end
function LowPoly.setMutation(container: Instance, id: any)
    local want = if type(id) == "string" and id ~= "" and MutationLook.get(id) then id else nil
    if container:GetAttribute("LPMutation") == want then return end
    container:SetAttribute("LPMutation", want)
    container:SetAttribute("LPLookKey", nil)
    LowPoly.tint(container, nil)
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
            primaryShare = math.clamp((genes.blend or 50) / 100, 0, 1), patternId = patternId, tier = if entry then entry.id else nil, seedName = "",
            mutation = mutationOf(container, entry)}
    elseif not entry then shells(container, nil) return end
    if not spec then -- no genes (Index stage tiles, fusion previews): a fused tier still bakes over the species' own colour, so the tier reads (BD-326)
        local own = Color3.new(1, 1, 1)
        spec = {primary = own, secondary = own, same = false, primaryShare = 1, patternId = "01_blank", tier = (entry :: any).id, seedName = "", own = true}
    end
    local camera = workspace.CurrentCamera
    local body: BasePart? = nil
    local textured: {{part: MeshPart, textureId: string, role: string}} = {}
    for _, part in container:GetDescendants() do
        if part:IsA("MeshPart") and part.Name ~= "LPTierShell" and part.Name ~= "LPTierGlow" then
            local textureId = part:GetAttribute("LPTexture")
            local role = tostring(part:GetAttribute("LPRole") or "body")
            if role == "body" and not body then body = part end
            local eyeish = type(textureId) ~= "string" or textureId == ""
            -- BD-173: base dinos matte; only a fused tier gets Metal/Glass + reflectance, and only on textured body-colour parts.
            part.Material, part.Reflectance = Enum.Material.Plastic, 0
            if entry and not eyeish then part.Material, part.Reflectance = Enum.Material.SmoothPlastic, Tier.BodyGloss end -- fused: glossy highlights, texture stays
            if entry and Tier.isAccentName(part.Name) and eyeish then -- claws / toes / horns are untextured parts: tint them in the tier metal / gem
                local c = entry.accent
                part.Color = Color3.fromRGB(c[1], c[2], c[3])
                part.Material = (Enum.Material :: any)[entry.accentMaterial] or Enum.Material.SmoothPlastic
                part.Reflectance = Tier.MaxReflectance
                if eyeish then continue end
                part.TextureID = ""
                continue
            end
            if eyeish or not spec then part.Color = Color3.new(1, 1, 1) continue end
            table.insert(textured, {part = part, textureId = textureId, role = role})
        end
    end
    shells(container, entry)
    sparkle(container, body, entry)
    rim(container, entry, body)
    if not spec or #textured == 0 then return end
    local s = spec :: Texture.Spec
    local anchor = body or textured[1].part
    local far = camera ~= nil and anchor:IsDescendantOf(workspace) and (camera.CFrame.Position - anchor.Position).Magnitude > LowPoly.Far
    local key = Texture.key(species, s) .. (if far then "|far" else "|near")
    if container:GetAttribute("LPLookKey") == key and container:GetAttribute("LPLod") ~= "baking" then return end
    container:SetAttribute("LPLookKey", key)
    -- cheap tint at once (shows while the bakes run, or stays when far / denied / full); the model's own texture is never cleared
    for _, t in textured do
        Texture.release(t.part)
        t.part.TextureID = t.textureId
        t.part.Color = Color3.new(1, 1, 1)
        t.part:SetAttribute("LPLod", "tint")
    end
    if far then container:SetAttribute("LPLod", "tint") return end
    container:SetAttribute("LPLod", "baking")
    task.spawn(function()
        local left = #textured
        local textures = 0
        for _, t in textured do
            local ps = table.clone(s)
            ps.seedName = species .. "|" .. t.role
            task.spawn(function()
                partBake(container, species, t.part, t.textureId, t.role, ps, key)
                if t.part:GetAttribute("LPLod") == "texture" then textures += 1 end
                left -= 1
            end)
        end
        while left > 0 do task.wait(0.1) end
        if container:GetAttribute("LPLookKey") ~= key then return end
        -- "texture" = every part baked, "parts" = some on the tint (cache full / budget), "tint" = none
        container:SetAttribute("LPLod", if textures == #textured then "texture" elseif textures > 0 then "parts" else "tint")
    end)
end
-- Fused tier look on a low-poly model (nil / "base" / false restores matte). Reads the same stage strings as the rest of the game.
function LowPoly.applyTier(container: Instance, stage: any)
    local entry = Tier.get(stage)
    container:SetAttribute("LPTier", if entry then entry.id else nil)
    container:SetAttribute("LPLookKey", nil)
    LowPoly.tint(container, nil)
end
-- Maintenance (client only): far world dinos drop to the cheap tint (bakes released), near ones get their bakes back as slots free up.
if game:GetService("RunService"):IsClient() then
    task.spawn(function()
        while true do
            task.wait(1.5)
            if not LowPoly.enabled() then continue end
            pcall(function()
                local camera = workspace.CurrentCamera
                for container, _ in genesOf do
                    if camera and container.Parent and container:IsDescendantOf(workspace) and container:IsA("Model") then
                        local far = (camera.CFrame.Position - container:GetPivot().Position).Magnitude > LowPoly.Far
                        local key = tostring(container:GetAttribute("LPLookKey") or "")
                        local wasFar = string.sub(key, -4) == "|far"
                        local lod = container:GetAttribute("LPLod")
                        -- a near dino left on the tint (cache full / budget) retries every 10 s as slots free up
                        local stale = not far and (lod == "tint" or lod == "parts") and os.clock() >= (tonumber(container:GetAttribute("LPRetryAt")) or 0)
                        if key ~= "" and (far ~= wasFar or stale) then
                            container:SetAttribute("LPRetryAt", os.clock() + 10)
                            container:SetAttribute("LPLookKey", nil)
                            LowPoly.tint(container, nil)
                        end
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
