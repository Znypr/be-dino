--!strict
-- BD-285 (docs/104 s5): the Cave hub lava falls and pool as FX from the existing alpha textures only (EffectAssets flameSheet, smokeSheet,
-- sparkSheet, swirl). Called from Arena's cave branch only (Config.CaveHub on). The generated cave_lava_fall mesh came out as a chunky
-- block, so it is NOT used. The waterfall is a thin warm translucent sheet in the falls recess that carries three scrolling alpha
-- layers (flames, swirl, flames) drawn in a SurfaceGui (a SurfaceGui is not faded by the part's Transparency, a Texture would be); the client
-- (CaveLavaClient) scrolls them and scales the emitters. The basin gets a slowly turning swirl, steam, popping embers and slow bubbles.
-- Nothing here damages a dino; the rim rocks and the lava_fence colliders keep walkers out of the basin.
-- FX, NOT MODEL ART: the sheet and disc are plain translucent Parts marked IsLightingFx (like the light shafts in CaveLighting).
-- Static first frame: the layers are created at their scroll-0 position, so a client that never animates (Reduce Motion) still sees
-- a finished lava wall. Rates and layers come from the pure CaveLavaRules (25 particles per second desktop, 10 phone).
-- NOT done: the quiet bubbling loop (owner judges by ear, agents cannot).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Layout = require(ReplicatedStorage.Shared.CaveHubLayout)
local Props = require(ReplicatedStorage.Shared.CaveHubProps)
local Assets = require(ReplicatedStorage.Shared.EffectAssets)
local Rules = require(ReplicatedStorage.Shared.CaveLavaRules)
local CaveLavaFx = {}

local function c3(c: {number}): Color3 return Color3.fromRGB(c[1], c[2], c[3]) end

local function fxPart(parent: Instance, name: string, size: Vector3, cf: CFrame, shape: Enum.PartType, color: Color3, transparency: number): Part
    local p = Instance.new("Part")
    p.Name, p.Size, p.CFrame, p.Shape = name, size, cf, shape
    p.Material, p.Color, p.Transparency = Enum.Material.SmoothPlastic, color, transparency
    p.Anchored, p.CanCollide, p.CanTouch, p.CanQuery, p.CastShadow = true, false, false, false, false
    p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
    p:SetAttribute("IsLightingFx", true)
    p.Parent = parent
    return p
end

-- One ParticleEmitter. `rule` names its rate in CaveLavaRules.Rates (the client scales it for phones / Reduce Motion).
local function emitter(parent: Instance, key: string, name: string, rule: string): ParticleEmitter
    local e = Instance.new("ParticleEmitter")
    e.Name = name
    local sheet = Assets.isSheet(key) and not Assets.isAdditive(key)
    e.Texture = if sheet then Assets.resolve(key) else (if key == "smokeSheet" then Assets.Builtin.smoke else Assets.Builtin.spark)
    e.FlipbookLayout = if sheet then Enum.ParticleFlipbookLayout.Grid4x4 else Enum.ParticleFlipbookLayout.None
    if sheet then
        e.FlipbookMode = (Enum.ParticleFlipbookMode :: any)[Assets.mode(key)]
        e.FlipbookStartRandom = Assets.mode(key) ~= "OneShot"
    end
    e.LockedToPart = false
    e.Rate = (Rules.Rates :: any)[rule]
    e:SetAttribute("LavaRule", rule)
    e.Parent = parent
    return e
end

-- One scrolling layer: a SurfaceGui on its own sheet holds two nested CanvasGroups (each with a UIGradient alpha edge fade, one across,
-- one down: soft edges, no hard rectangle) around one tiled ImageLabel one tile taller / wider than the canvas. Position at scroll 0 =
-- the static first frame (Reduce Motion).
local function fade(group: CanvasGroup, fraction: number, rotation: number)
    local g = Instance.new("UIGradient")
    local keys = {}
    for _, k in Rules.edgeFade(fraction) do table.insert(keys, NumberSequenceKeypoint.new(k[1], k[2])) end
    g.Transparency = NumberSequence.new(keys)
    g.Rotation = rotation
    g.Parent = group
end

local function buildLayer(sheet: Part, index: number, layer: any, width: number, height: number)
    local gui = Instance.new("SurfaceGui")
    gui.Name = "LavaLayer_" .. layer.name
    gui.Face = Enum.NormalId.Front
    gui.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
    gui.CanvasSize = Vector2.new(width * Rules.CanvasPxPerStud, height * Rules.CanvasPxPerStud)
    gui.LightInfluence = 0
    gui.Brightness = 1.4
    gui.AlwaysOnTop = false
    gui.Parent = sheet
    local across = Instance.new("CanvasGroup")
    across.Name, across.Size, across.BackgroundTransparency, across.BorderSizePixel = "FadeAcross", UDim2.fromScale(1, 1), 1, 0
    fade(across, layer.fade, 0)
    across.Parent = gui
    local down = Instance.new("CanvasGroup")
    down.Name, down.Size, down.BackgroundTransparency, down.BorderSizePixel, down.ClipsDescendants = "FadeDown", UDim2.fromScale(1, 1), 1, 0, true
    fade(down, layer.fade, 90)
    down.Parent = across
    local tile = Rules.tilePx(layer)
    local image = Instance.new("ImageLabel")
    image.Name = "Strip"
    image.BackgroundTransparency = 1
    image.BorderSizePixel = 0
    image.Image = Assets.resolve(layer.key)
    image.ImageColor3 = c3(layer.color)
    image.ImageTransparency = layer.alpha
    image.ScaleType = Enum.ScaleType.Tile
    image.TileSize = UDim2.fromOffset(tile, tile)
    image.Size = UDim2.fromOffset(width * Rules.CanvasPxPerStud + tile, height * Rules.CanvasPxPerStud + tile)
    image.Position = UDim2.fromOffset(-((layer.offsetU * Rules.CanvasPxPerStud) % tile) - 0, Rules.stripY(layer, 0, true))
    image.ZIndex = index
    image:SetAttribute("LayerIndex", index)
    image:SetAttribute("OffsetX", -((layer.offsetU * Rules.CanvasPxPerStud) % tile))
    image.Parent = down
end

function CaveLavaFx.build(parent: Instance): Folder
    local L = Props.Lava
    local F, P = Layout.Fall, Layout.Pool
    local cz, fy = Layout.CenterZ, Layout.FloorY
    local folder = Instance.new("Folder")
    folder.Name = "LavaFalls"
    local orange = c3(L.sheetColor)

    -- the falls: three thin layered sheets (BD-385), each a little nearer, narrower and shorter than the one behind, each with its own
    -- slowly scrolling layer and soft alpha edges. The back sheet also carries a faint warm body so the recess glows.
    local width = F.width - 2
    local sheet: Part
    for i, layer in Rules.Layers do
        local w, h = Rules.sheetSize(layer, width, F.height)
        local part = fxPart(folder, "FX_LavaSheet" .. (if i == 1 then "" else tostring(i)), Vector3.new(w, h, 0.2),
            CFrame.new(F.x, fy + h / 2, cz + F.z + L.sheetOffsetDz - layer.dz), Enum.PartType.Block, orange, if i == 1 then L.sheetTransparency else 0.97)
        buildLayer(part, i, layer, w, h)
        if i == 1 then sheet = part end
    end
    local flames = emitter(sheet, "flameSheet", "LipFlames", "lipFlames")
    flames.Lifetime = NumberRange.new(2.5, 3.5)
    flames.Speed = NumberRange.new(3, 6)
    flames.Acceleration = Vector3.new(0, -6, 0)
    flames.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 2.4), NumberSequenceKeypoint.new(1, 1.2)})
    flames.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.2, 0.4), NumberSequenceKeypoint.new(1, 1)})
    flames.Color = ColorSequence.new(c3({255, 150, 60}), c3({255, 90, 30}))
    flames.LightEmission = 0.8
    flames.Shape, flames.ShapeInOut, flames.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Surface
    flames.EmissionDirection = Enum.NormalId.Bottom
    flames.SpreadAngle = Vector2.new(8, 8)

    -- warm mist where the falls meet the basin
    local baseAnchor = Instance.new("Attachment")
    baseAnchor.Name = "BaseMist"
    baseAnchor.Position = Vector3.new(0, -F.height / 2 + 1, -1.5)
    baseAnchor.Parent = sheet
    local mist = emitter(baseAnchor, "smokeSheet", "BaseMist", "baseMist")
    mist.Lifetime = NumberRange.new(2.5, 3.5)
    mist.Speed = NumberRange.new(1, 2)
    mist.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 6), NumberSequenceKeypoint.new(1, 11)})
    mist.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.3, 0.78), NumberSequenceKeypoint.new(1, 1)})
    mist.Color = ColorSequence.new(c3({255, 190, 130}))
    mist.LightEmission = 0.4
    mist.Shape, mist.ShapeInOut, mist.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    mist.EmissionDirection = Enum.NormalId.Front
    mist.SpreadAngle = Vector2.new(20, 20)

    -- glowing base pool in front of the falls: stacked flat discs, brighter in the middle (a stepped soft edge), no extra lights
    local glowY = Layout.floorHeight(F.x, cz + F.z + 3) + 0.12
    for i, g in Rules.Glow do
        fxPart(folder, "FX_LavaGlow" .. i, Vector3.new(0.1, g.diameter, g.diameter),
            CFrame.new(F.x, glowY + i * 0.02, cz + F.z + L.sheetOffsetDz - Rules.GlowFront) * CFrame.Angles(0, 0, math.pi / 2),
            Enum.PartType.Cylinder, c3(g.color), g.transparency)
    end

    -- the pool: a flat translucent disc with a slowly turning swirl, just under the rim of the 2 stud basin
    local diameter = Layout.Kinds.lava_pool_disc[1]
    local base = CFrame.new(P.x, fy - L.discDrop, cz + P.z)
    local disc = fxPart(folder, "FX_LavaPool", Vector3.new(0.3, diameter, diameter), base * CFrame.Angles(0, 0, math.pi / 2),
        Enum.PartType.Cylinder, c3(L.discColor), L.discTransparency)
    local swirl = Instance.new("Decal")
    swirl.Name, swirl.Texture, swirl.Face, swirl.Transparency = "Swirl", Assets.resolve("swirl"), Enum.NormalId.Right, 0.35
    swirl.Color3 = c3({255, 190, 110})
    swirl.Parent = disc
    local steam = emitter(disc, "smokeSheet", "Steam", "steam")
    steam.Lifetime = NumberRange.new(2, 2.6)
    steam.Speed = NumberRange.new(1.5, 2.5)
    steam.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 4), NumberSequenceKeypoint.new(1, 7)})
    steam.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.25, 0.7), NumberSequenceKeypoint.new(1, 1)})
    steam.Color = ColorSequence.new(c3({255, 214, 170}))
    steam.LightEmission = 0.3
    steam.Shape, steam.ShapeInOut, steam.ShapeStyle = Enum.ParticleEmitterShape.Disc, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    steam.EmissionDirection = Enum.NormalId.Right
    -- sparks popping up and arcing back (the bubbling basin)
    local embers = emitter(disc, "sparkSheet", "Embers", "embers")
    embers.Lifetime = NumberRange.new(1.6, 2.6)
    embers.Speed = NumberRange.new(5, 9)
    embers.Acceleration = Vector3.new(0, -9, 0)
    embers.SpreadAngle = Vector2.new(25, 25)
    embers.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.9), NumberSequenceKeypoint.new(1, 0.3)})
    embers.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.1), NumberSequenceKeypoint.new(1, 1)})
    embers.Color = ColorSequence.new(c3({255, 190, 90}))
    embers.LightEmission = 1
    embers.Shape, embers.ShapeInOut, embers.ShapeStyle = Enum.ParticleEmitterShape.Disc, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    embers.EmissionDirection = Enum.NormalId.Right
    -- slow bubbles: a small puff that swells and pops on the surface
    local bubbles = emitter(disc, "smokeSheet", "Bubbles", "bubbles")
    bubbles.Lifetime = NumberRange.new(1.2, 1.8)
    bubbles.Speed = NumberRange.new(0.5, 1.2)
    bubbles.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.8), NumberSequenceKeypoint.new(1, 2.4)})
    bubbles.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.6), NumberSequenceKeypoint.new(0.8, 0.5), NumberSequenceKeypoint.new(1, 1)})
    bubbles.Color = ColorSequence.new(c3({255, 170, 90}), c3({255, 216, 150}))
    bubbles.LightEmission = 0.9
    bubbles.Shape, bubbles.ShapeInOut, bubbles.ShapeStyle = Enum.ParticleEmitterShape.Disc, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    bubbles.EmissionDirection = Enum.NormalId.Right

    folder:SetAttribute("FxBudget", L.fxPartBudget)
    folder:SetAttribute("EmittersPerSecond", Rules.totalRate())
    folder.Parent = parent

    -- the slow swirl turn of the pool disc is done by the client (CaveLavaClient), so Reduce Motion keeps it still
    disc:SetAttribute("SpinSeconds", L.discSpinSeconds)
    disc:SetAttribute("SpinBase", base)
    return folder
end

return CaveLavaFx
