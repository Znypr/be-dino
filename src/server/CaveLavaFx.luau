--!strict
-- BD-285 (docs/104 s5): the Cave hub lava falls and pool as FX from the existing alpha textures only (EffectAssets flameSheet,
-- smokeSheet, sparkSheet, swirl). Called from Arena's cave branch only (Config.CaveHub on). The generated cave_lava_fall mesh
-- came out as a chunky block, so it is NOT used: the waterfall is a soft orange translucent sheet in front of the lava-painted
-- recess wall plus falling flame particles, with steam and embers at the pool and a slowly turning swirl on the pool surface.
-- Nothing here damages a dino; the rim rocks and the lava_fence colliders keep walkers out of the basin.
-- FX, NOT MODEL ART: the sheet and disc are plain translucent Parts marked IsLightingFx (like the light shafts in CaveLighting).
-- NOT done yet: the scrolling texture on the sheet, the quiet bubbling loop, the Reduce Motion variant (needs the client).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local Layout = require(ReplicatedStorage.Shared.CaveHubLayout)
local Props = require(ReplicatedStorage.Shared.CaveHubProps)
local Assets = require(ReplicatedStorage.Shared.EffectAssets)
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

local function emitter(parent: Instance, key: string, name: string): ParticleEmitter
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

    -- the falls: a soft translucent sheet inside the recess, in front of the lava-painted rock
    local sheet = fxPart(folder, "FX_LavaSheet", Vector3.new(F.width - 2, F.height, 0.4),
        CFrame.new(F.x, fy + F.height / 2, cz + F.z + L.sheetOffsetDz), Enum.PartType.Block, orange, L.sheetTransparency)
    local flames = emitter(sheet, "flameSheet", "LipFlames")
    flames.Rate = L.emitterRates.flames
    flames.Lifetime = NumberRange.new(2.5, 3.5)
    flames.Speed = NumberRange.new(3, 6)
    flames.Acceleration = Vector3.new(0, -6, 0)
    flames.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 3), NumberSequenceKeypoint.new(1, 1.5)})
    flames.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.2, 0.35), NumberSequenceKeypoint.new(1, 1)})
    flames.Color = ColorSequence.new(c3({255, 150, 60}), c3({255, 90, 30}))
    flames.LightEmission = 1
    flames.Shape, flames.ShapeInOut, flames.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Surface
    flames.EmissionDirection = Enum.NormalId.Bottom
    flames.SpreadAngle = Vector2.new(8, 8)

    -- the pool: a flat translucent disc with a slowly turning swirl, just under the rim of the 2 stud basin
    local diameter = Layout.Kinds.lava_pool_disc[1]
    local base = CFrame.new(P.x, fy - L.discDrop, cz + P.z)
    local disc = fxPart(folder, "FX_LavaPool", Vector3.new(0.3, diameter, diameter), base * CFrame.Angles(0, 0, math.pi / 2),
        Enum.PartType.Cylinder, c3(L.discColor), L.discTransparency)
    local swirl = Instance.new("Decal")
    swirl.Name, swirl.Texture, swirl.Face, swirl.Transparency = "Swirl", Assets.resolve("swirl"), Enum.NormalId.Right, 0.35
    swirl.Color3 = c3({255, 190, 110})
    swirl.Parent = disc
    local steam = emitter(disc, "smokeSheet", "Steam")
    steam.Rate = L.emitterRates.steam
    steam.Lifetime = NumberRange.new(2, 2.6)
    steam.Speed = NumberRange.new(1.5, 2.5)
    steam.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 4), NumberSequenceKeypoint.new(1, 7)})
    steam.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.25, 0.7), NumberSequenceKeypoint.new(1, 1)})
    steam.Color = ColorSequence.new(c3({255, 214, 170}))
    steam.LightEmission = 0.3
    steam.Shape, steam.ShapeInOut, steam.ShapeStyle = Enum.ParticleEmitterShape.Disc, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    steam.EmissionDirection = Enum.NormalId.Right
    local embers = emitter(disc, "sparkSheet", "Embers")
    embers.Rate = L.emitterRates.embers
    embers.Lifetime = NumberRange.new(2.5, 3.5)
    embers.Speed = NumberRange.new(2, 4)
    embers.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.6), NumberSequenceKeypoint.new(1, 0.2)})
    embers.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.2), NumberSequenceKeypoint.new(1, 1)})
    embers.Color = ColorSequence.new(c3({255, 170, 80}))
    embers.LightEmission = 1
    embers.Shape, embers.ShapeInOut, embers.ShapeStyle = Enum.ParticleEmitterShape.Disc, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
    embers.EmissionDirection = Enum.NormalId.Right

    folder:SetAttribute("FxBudget", L.fxPartBudget)
    folder:SetAttribute("EmittersPerSecond", L.emitterRates.flames + L.emitterRates.embers + L.emitterRates.steam)
    folder.Parent = parent

    -- slow swirl: three 120 degree tweens per turn (a CFrame tween takes the short way round, so one 360 degree tween would not turn)
    task.spawn(function()
        local per = L.discSpinSeconds / 3
        local step = 0
        while folder.Parent do
            step += 1
            local goal = base * CFrame.Angles(0, step * 2 * math.pi / 3, 0) * CFrame.Angles(0, 0, math.pi / 2)
            local tween = TweenService:Create(disc, TweenInfo.new(per, Enum.EasingStyle.Linear), {CFrame = goal})
            tween:Play()
            tween.Completed:Wait()
        end
    end)
    return folder
end

return CaveLavaFx
