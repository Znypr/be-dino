--!strict
-- BD-285 (docs/104 s5): the Cave hub lava falls and pool as FX from the existing alpha textures only (EffectAssets flameSheet, smokeSheet,
-- sparkSheet, swirl). Called from Arena's cave branch only (Config.CaveHub on). The generated cave_lava_fall mesh came out as a chunky
-- block, so it is NOT used. BD-385: the waterfall is soft flameSheet particle strands dropping from an irregular lip (no tiled texture,
-- no SurfaceGui, no visible rectangle: the earlier scrolling-sheet version read as a tiled billboard); the client (CaveLavaClient) scales the emitters. The basin gets a slowly turning swirl, steam, popping embers and slow bubbles.
-- Nothing here damages a dino; the rim rocks and the lava_fence colliders keep walkers out of the basin.
-- FX, NOT MODEL ART: the invisible emitter carrier, glow discs and pool disc are plain translucent Parts marked IsLightingFx (like the light shafts in CaveLighting).
-- Reduce Motion: the client freezes a one-off burst of soft glow puffs (StillGlow) and the floor glow discs: a calm warm wall. Rates and layers come from the pure CaveLavaRules (25 particles per second desktop, 10 phone).
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

function CaveLavaFx.build(parent: Instance): Folder
    local L = Props.Lava
    local F, P = Layout.Fall, Layout.Pool
    local cz, fy = Layout.CenterZ, Layout.FloorY
    local folder = Instance.new("Folder")
    folder.Name = "LavaFalls"
    local orange = c3(L.sheetColor)

    -- BD-385: no sheet, no tiled texture. ONE invisible carrier part (the emitter box, NOT a visible rectangle) stands in the falls
    -- recess; soft flameSheet puff strands drop from irregular spots along the lip (CaveLavaRules.Strands) and overlap into a
    -- ragged, flowing curtain with no hard edge, and big faint puffs fill the wall with a warm glow.
    local width = F.width - 2
    local sheet = fxPart(folder, "FX_LavaSheet", Vector3.new(width, F.height, 0.2),
        CFrame.new(F.x, fy + F.height / 2, cz + F.z + L.sheetOffsetDz), Enum.PartType.Block, orange, 1)
    for i, strand in Rules.Strands do
        local anchor = Instance.new("Attachment")
        anchor.Name = "Strand" .. i
        anchor.Position = Vector3.new(strand.dx, F.height / 2 - 1 - strand.dy, 0.4)
        anchor.Parent = sheet
        local e = emitter(anchor, "flameSheet", "Strand" .. i, "strand" .. i)
        e.Lifetime = NumberRange.new(strand.life * 0.85, strand.life)
        e.Speed = NumberRange.new(0.5, 1.5)
        e.Acceleration = Vector3.new(0, -strand.fall, 0)
        e.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, strand.size * 0.7), NumberSequenceKeypoint.new(0.5, strand.size), NumberSequenceKeypoint.new(1, strand.size * 1.25)})
        e.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.18, 0.55), NumberSequenceKeypoint.new(0.75, 0.7), NumberSequenceKeypoint.new(1, 1)})
        e.Color = ColorSequence.new(c3({255, 170, 80}), c3({255, 110, 40}))
        e.LightEmission = 0.55
        e.Rotation = NumberRange.new(-25, 25)
        e.SpreadAngle = Vector2.new(4, 4)
        e.EmissionDirection = Enum.NormalId.Front
        e.ZOffset = -(i % 3) * 0.2
    end
    -- faint warm puffs across the whole wall (box = the carrier volume): the recess glows with a soft cloud edge
    local wall = emitter(sheet, "smokeSheet", "WallGlow", "wallGlow")
    wall.Lifetime = NumberRange.new(4.5, 6)
    wall.Speed = NumberRange.new(0, 0.4)
    wall.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 12), NumberSequenceKeypoint.new(1, 17)})
    wall.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.3, 0.84), NumberSequenceKeypoint.new(0.7, 0.88), NumberSequenceKeypoint.new(1, 1)})
    wall.Color = ColorSequence.new(c3({255, 130, 50}), c3({255, 170, 90}))
    wall.LightEmission = 0.6
    wall.Shape, wall.ShapeInOut, wall.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    wall.EmissionDirection = Enum.NormalId.Front
    -- Reduce Motion (static variant): the client emits one burst of these constant-alpha puffs across the wall and freezes them
    -- (TimeScale 0). No Rate, no LavaRule: it never runs in the normal look.
    local still = Instance.new("ParticleEmitter")
    still.Name, still.Rate, still.Enabled = "StillGlow", 0, false
    still.Texture = Assets.Builtin.smoke
    still.Lifetime = NumberRange.new(30, 30)
    still.Speed = NumberRange.new(0, 0)
    still.Size = NumberSequence.new(13)
    still.Transparency = NumberSequence.new(0.84)
    still.Color = ColorSequence.new(c3({255, 140, 60}), c3({255, 180, 100}))
    still.LightEmission = 0.6
    still.Shape, still.ShapeInOut, still.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    still:SetAttribute("StillBurst", Rules.StillBurst)
    still.Parent = sheet

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
