--!strict
-- BD-1247 (owner 2026-11-16 "game still looks empty"): warmer light and atmosphere on the World V3 island. ONLY while Config.WarmLightEnabled
-- and Config.WorldV3Enabled are on (playtest profile): otherwise this script returns on its first lines and nothing is created.
-- Its own post effects (WarmGrade, WarmBloom, WarmRays) stack on the weather's and fade to nothing in other weather and off the island, so
-- WeatherVisuals keeps the event moods untouched. Slow pollen / light motes per zone come from one invisible emitter box ahead of the camera
-- (five emitters, one per zone, crossfaded by where the local dino stands; no physics, not locked to the box so they float in place).
-- Data and rules: src/shared/WarmLight.luau. Reduce Motion: no motes (the grade, bloom and rays stay; they do not move).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config")) :: any
local W = require(Shared:WaitForChild("WarmLight"))
if not W.enabled(Config) then return end

local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local WorldV3 = require(Shared:WaitForChild("WorldV3")) :: any
local Zones = require(Shared:WaitForChild("ZoneAmbience"))
local EffectAssets = require(Shared:WaitForChild("EffectAssets"))
local Theme = require(Shared:WaitForChild("UITheme")) :: any

local player = Players.LocalPlayer
local deviceClass = (function(): string
    local size = workspace.CurrentCamera.ViewportSize
    return if not UserInputService.TouchEnabled then "Desktop" elseif math.min(size.X, size.Y) >= 600 then "Tablet" else "Phone"
end)()
local function c3(rgb: {number}): Color3 return Color3.fromRGB(rgb[1], rgb[2], rgb[3]) end

local grade = Instance.new("ColorCorrectionEffect")
grade.Name = "WarmGrade"
grade.Parent = Lighting
local bloom = Instance.new("BloomEffect")
bloom.Name = "WarmBloom"
bloom.Intensity, bloom.Size, bloom.Threshold = 0, W.Bloom.size, W.Bloom.threshold
bloom.Parent = Lighting
local rays = Instance.new("SunRaysEffect")
rays.Name = "WarmRays"
rays.Intensity, rays.Spread = 0, W.Rays.spread
rays.Parent = Lighting

local box = Instance.new("Part")
box.Name = "WarmMotes"
box.Size = Vector3.new(W.Box.x, W.Box.y, W.Box.z)
box.Transparency = 1
box.Anchored, box.CanCollide, box.CanTouch, box.CanQuery, box.CastShadow = true, false, false, false, false
box.Parent = workspace
local emitters: {[string]: ParticleEmitter} = {}
for _, zone in W.Order do
    local m = W.Motes[zone]
    local e = Instance.new("ParticleEmitter")
    e.Name = "Motes_" .. zone
    e.Texture = EffectAssets.resolve(m.texture)
    if m.texture == "ashFlake" and EffectAssets.isSheet and EffectAssets.isSheet("ashFlake") then
        e.FlipbookLayout = Enum.ParticleFlipbookLayout.Grid4x4
        e.FlipbookMode = Enum.ParticleFlipbookMode.Random
    end
    e.Shape, e.ShapeStyle, e.ShapeInOut = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeStyle.Volume, Enum.ParticleEmitterShapeInOut.Outward
    e.Rate = 0
    e.Lifetime = NumberRange.new(m.life[1], m.life[2])
    e.Speed = NumberRange.new(.2, .7)
    e.SpreadAngle = Vector2.new(180, 180)
    e.Acceleration = Vector3.new(0, if zone == "volcano" then -.08 else .03, 0)
    e.Drag = .4
    e.RotSpeed = NumberRange.new(-30, 30)
    e.Rotation = NumberRange.new(0, 360)
    e.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, m.size[1]), NumberSequenceKeypoint.new(.5, m.size[2]), NumberSequenceKeypoint.new(1, m.size[1])})
    e.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(.2, .25), NumberSequenceKeypoint.new(.8, .35), NumberSequenceKeypoint.new(1, 1)})
    e.Color = ColorSequence.new(c3(m.colors[1]), c3(m.colors[2]))
    e.LightEmission, e.LightInfluence, e.Brightness = m.emission, .6, 1.2
    e.LockedToPart = false
    e.Parent = box
    emitters[zone] = e
end

local level = 0
local weights: {[string]: number} = {}
for _, zone in W.Order do weights[zone] = 0 end
local zoneNow: string? = nil
local nextZone = 0
RunService.Heartbeat:Connect(function(dt)
    local now = os.clock()
    local location = player:GetAttribute("Location")
    local onIsland = location == nil or location == "Island" -- nil = no cave hub: the island is all there is
    level = W.step(level, W.target(workspace:GetAttribute("WeatherId"), onIsland), dt)
    local g = W.Grade
    grade.TintColor = Color3.new(1, 1, 1):Lerp(c3(g.tint), level)
    grade.Saturation, grade.Contrast, grade.Brightness = g.saturation * level, g.contrast * level, g.brightness * level
    grade.Enabled = level > .001
    bloom.Intensity = W.Bloom.intensity * level
    bloom.Enabled = level > .001
    rays.Intensity = W.Rays.intensity * level
    rays.Enabled = level > .001
    -- motes: the zone under the local dino, crossfaded; the box rides ahead of the camera
    local camera = workspace.CurrentCamera
    if now >= nextZone then
        nextZone = now + .5
        local character = player.Character
        local root = if character then character:FindFirstChild("HumanoidRootPart") :: BasePart? else nil
        zoneNow = if root and onIsland then Zones.zoneFor(root.Position.X, root.Position.Z, WorldV3) else nil
    end
    local motes = Theme.MotionEnabled and level > 0
    for _, zone in W.Order do
        weights[zone] = W.step(weights[zone], if motes and zone == zoneNow then level else 0, dt)
        emitters[zone].Rate = W.rateFor(zone, deviceClass, weights[zone])
    end
    if camera then
        local look = camera.CFrame.LookVector
        local flat = Vector3.new(look.X, 0, look.Z)
        local ahead = if flat.Magnitude > 1e-3 then flat.Unit * W.Ahead else Vector3.zero
        box.CFrame = CFrame.new(camera.CFrame.Position + ahead + Vector3.new(0, 2, 0))
    end
end)
