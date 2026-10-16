--!strict
-- BD-286 (docs/104 s4): builds the Cave hub lighting from the pure CaveLightingRules: soft light-shaft beams under the 4 ceiling
-- holes with dust motes, warm fill / lava / crystal / forge point lights, and the gate arch light with a soft glow. Only called
-- from Arena's cave branch (Config.CaveHub on): flag off = this module is never run and nothing is created.
-- FX, NOT MODEL ART: each shaft is two camera-facing Beams (a wide haze and a narrow core) between two Attachments on the invisible dust
-- volume Part, textured with the soft mist sprite (soft on every side). BD-296: the first version used translucent cylinder Parts, whose
-- flat silhouette edges showed as faint vertical seams in the tunnel views; a camera-facing soft-edged Beam has no edge to see edge-on.
-- They are named FX_* and carry the attribute IsLightingFx. The tapered cone mesh (BD-282) replaces them.
-- Textures come only from EffectAssets (softMist, sparkSheet / smokeSheet, all uploaded with alpha).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Rules = require(ReplicatedStorage.Shared.CaveLightingRules)
local Layout = require(ReplicatedStorage.Shared.CaveHubLayout)
local Assets = require(ReplicatedStorage.Shared.EffectAssets)
local CaveLighting = {}

local function c3(c: {number}): Color3 return Color3.fromRGB(c[1], c[2], c[3]) end

local function fxPart(parent: Instance, name: string, size: Vector3, cf: CFrame, shape: Enum.PartType?, transparency: number): Part
    local p = Instance.new("Part")
    p.Name, p.Size, p.CFrame = name, size, cf
    p.Shape = shape or Enum.PartType.Block
    p.Material, p.Color, p.Transparency = Enum.Material.SmoothPlastic, c3(Rules.BeamColor), transparency
    p.Anchored, p.CanCollide, p.CanTouch, p.CanQuery, p.CastShadow = true, false, false, false, false
    p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
    p:SetAttribute("IsLightingFx", true)
    p.Parent = parent
    return p
end

local function emitter(parent: Instance, key: string): ParticleEmitter
    local e = Instance.new("ParticleEmitter")
    local sheet = Assets.isSheet(key) and not Assets.isAdditive(key)
    e.Texture = if sheet then Assets.resolve(key) else (if key == "smokeSheet" then Assets.Builtin.smoke else Assets.Builtin.spark)
    e.FlipbookLayout = if sheet then Enum.ParticleFlipbookLayout.Grid4x4 else Enum.ParticleFlipbookLayout.None
    if sheet then
        e.FlipbookMode = (Enum.ParticleFlipbookMode :: any)[Assets.mode(key)]
        e.FlipbookStartRandom = Assets.mode(key) ~= "OneShot"
    end
    e.LockedToPart = false
    e.Parent = parent
    return e
end

-- BD-296: one soft shaft ribbon. FaceCamera keeps it flat to the viewer from every angle (never edge-on), the soft mist texture fades its
-- sides, and the transparency ramp fades its ends, so no hard silhouette shows. `alpha` is the mid-beam transparency (0.9 = 10 percent).
local function shaftTexture(): string
    local id = Assets.Uploaded.softMist
    return if Assets.isValid(id) then id else Assets.Builtin.smoke
end
local function shaftBeam(parent: Instance, a0: Attachment, a1: Attachment, name: string, width: number, alpha: number): Beam
    local b = Instance.new("Beam")
    b.Name, b.Attachment0, b.Attachment1 = name, a0, a1
    b.FaceCamera, b.Segments, b.CurveSize0, b.CurveSize1 = true, 1, 0, 0
    b.Width0, b.Width1 = width, width
    b.Texture, b.TextureMode, b.TextureSpeed, b.LightEmission = shaftTexture(), Enum.TextureMode.Stretch, 0, 0.5
    b.Color = ColorSequence.new(c3(Rules.BeamColor))
    b.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.12, alpha), NumberSequenceKeypoint.new(0.85, alpha), NumberSequenceKeypoint.new(1, 1)})
    b:SetAttribute("IsLightingFx", true)
    b:SetAttribute("SoftEdged", true)
    b.Parent = parent
    return b
end

-- Lights sit on an Attachment under Terrain (no extra Part per light).
local function light(spec: any): PointLight
    local holder = Instance.new("Attachment")
    holder.Name = "CaveLight_" .. spec.owner
    holder:SetAttribute("IsLightingFx", true)
    holder.Parent = workspace.Terrain
    holder.WorldPosition = Vector3.new(spec.x, spec.y, spec.z)
    local l = Instance.new("PointLight")
    l.Color, l.Range, l.Brightness, l.Shadows = c3(spec.color), spec.range, spec.brightness, spec.shadows == true
    l:SetAttribute("Owner", spec.owner)
    if spec.pulse then l:SetAttribute("Pulse", true) end
    if spec.lamp then -- cosy pass: the client breathes these (CaveLightingRules.lampBrightness); the server value stays the steady base
        l:SetAttribute("Lamp", true)
        l:SetAttribute("LampBase", spec.brightness)
        l:SetAttribute("LampPhase", spec.phase)
        l:SetAttribute("LampPeriod", spec.period)
    end
    l.Parent = holder
    return l
end

function CaveLighting.build(parent: Instance): Folder
    local data = Rules.get()
    local folder = Instance.new("Folder")
    folder.Name = "CaveLighting"
    local B = Rules.Beam
    for _, s in data.shafts do
        -- dust volume: an invisible Part that carries the beam Attachments and the motes emitter (Reduce Motion turns the motes off on the client)
        local volume = fxPart(folder, "FX_LightShaftDust_" .. s.station, Vector3.new(s.outerRadius * 1.6, s.height, s.outerRadius * 1.6), CFrame.new(s.x, s.bottom + s.height / 2, s.z), nil, 1)
        local top, bottom = Instance.new("Attachment"), Instance.new("Attachment")
        top.Name, bottom.Name = "ShaftTop", "ShaftBottom"
        top.Position, bottom.Position = Vector3.new(0, s.height / 2, 0), Vector3.new(0, -s.height / 2, 0)
        top.Parent, bottom.Parent = volume, volume
        shaftBeam(volume, top, bottom, "FX_LightShaftHaze_" .. s.station, s.outerRadius * 2, B.outerAlpha)
        shaftBeam(volume, top, bottom, "FX_LightShaftCore_" .. s.station, s.coreRadius * 2, B.coreAlpha)
        -- dust motes drift slowly inside the beam (an invisible volume with one small emitter; Reduce Motion turns them off on the client)
        local e = emitter(volume, "sparkSheet")
        e.Name = "Motes"
        e:SetAttribute("Dust", true)
        e.Rate = B.motesPerSecond
        e.Lifetime = NumberRange.new(5, 8)
        e.Speed = NumberRange.new(0.2, 0.6)
        e.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(0.5, 0.45), NumberSequenceKeypoint.new(1, 0.2)})
        e.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.2, 0.45), NumberSequenceKeypoint.new(0.8, 0.45), NumberSequenceKeypoint.new(1, 1)})
        e.Color = ColorSequence.new(c3(Rules.BeamColor))
        e.LightEmission = 0.3
        e.Acceleration = Vector3.new(0, -0.15, 0)
        e.Shape, e.ShapeInOut, e.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
        e.EmissionDirection = Enum.NormalId.Bottom
    end
    -- gate arch: a soft warm mist in the mouth (the light itself is the gate's entry in the light list)
    local G = Rules.GateGlow
    local anchor = fxPart(folder, "FX_GateGlow", Vector3.new(data.gate.mouthWidth * 0.6, 12, 2), CFrame.new(data.gate.x, data.gate.y, data.gate.z), nil, 1)
    local g = emitter(anchor, "smokeSheet")
    g.Name = "GateMist"
    g.Rate, g.Lifetime, g.Speed = G.rate, NumberRange.new(5, 7), NumberRange.new(0.2, 0.5)
    g.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, G.size[1]), NumberSequenceKeypoint.new(1, G.size[2])})
    g.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.3, G.alpha), NumberSequenceKeypoint.new(1, 1)})
    g.Color = ColorSequence.new(c3(G.color))
    g.LightEmission = 0.6
    g.Shape, g.ShapeInOut, g.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    g.EmissionDirection = Enum.NormalId.Front
    -- lights (the layout's light list, at most CaveHubLayout.MaxLights)
    local count = 0
    for _, spec in data.lights do
        light(spec)
        count += 1
    end
    folder:SetAttribute("LightCount", count)
    folder:SetAttribute("FxPartCount", data.fxParts)
    folder:SetAttribute("MaxLights", Layout.MaxLights)
    folder.Parent = parent
    return folder
end

return CaveLighting
