--!strict
-- BD-286 / BD-296 (docs/104 s4): the cave-only look, applied by the client only while the player stands inside the Cave hub and
-- restored when they leave. WeatherVisuals calls step(dt) at the end of its own Heartbeat, so these values are written AFTER the
-- weather has written its own (no flicker, no fight) and the weather rigs ask inside() to stay outside. With Config.CaveHub false
-- step() returns at once and inside() is false: nothing is created, nothing is touched.
-- What it does while inside: warm Ambient / OutdoorAmbient, warm fog + Atmosphere, one temporary ColorCorrection ("CaveGrade",
-- created on entry, destroyed on exit: never global), the weather Depth-of-Field blur off (it blurred the whole hall), dust motes off
-- with Reduce Motion, and the forge light pulse (static with Reduce Motion).
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Rules = require(Shared:WaitForChild("CaveLightingRules"))
local Settings = require(Shared:WaitForChild("SettingsModel"))
local Lava = require(script.Parent:WaitForChild("CaveLavaClient"))
local PhoneGuard = require(script.Parent:WaitForChild("CavePhoneGuard")) -- BD-495: phone only, 12 nearest cave lights and 4 shaft beams (no-op elsewhere)

local Cave = {}
local player = Players.LocalPlayer
local isInside = false
local amount = 0 -- 0 = island look, 1 = full cave look
local grade: ColorCorrectionEffect? = nil
local saved: any = nil

local function c3(c: {number}): Color3 return Color3.fromRGB(c[1], c[2], c[3]) end

function Cave.inside(): boolean return isInside end
function Cave.amount(): number return amount end

local function save()
    local atmosphere = Lighting:FindFirstChildOfClass("Atmosphere")
    local dof = Lighting:FindFirstChild("WeatherDof")
    saved = {ambient = Lighting.Ambient, outdoor = Lighting.OutdoorAmbient, shift = Lighting.ColorShift_Top, exposure = Lighting.ExposureCompensation, brightness = Lighting.Brightness, softness = Lighting.ShadowSoftness,
        fogStart = Lighting.FogStart, fogEnd = Lighting.FogEnd, fogColor = Lighting.FogColor,
        dof = if dof and dof:IsA("DepthOfFieldEffect") then dof.Enabled else nil, emitters = {}, lights = {}}
    if atmosphere then
        saved.atmo = {density = atmosphere.Density, offset = atmosphere.Offset, haze = atmosphere.Haze, glare = atmosphere.Glare,
            color = atmosphere.Color, decay = atmosphere.Decay}
    end
    local arena = workspace:FindFirstChild("BeDinoArena") -- BD-505: Sanctuary lives under BeDinoArena, never directly in Workspace
    local sanctuary = arena and arena:FindFirstChild("Sanctuary")
    local folder = sanctuary and sanctuary:FindFirstChild("CaveLighting")
    if folder then
        for _, d in folder:GetDescendants() do
            if d:IsA("ParticleEmitter") and d:GetAttribute("Dust") then table.insert(saved.emitters, d) end
        end
    end
    saved.lamps = {}
    for _, d in workspace.Terrain:GetDescendants() do
        if d:IsA("PointLight") and d:GetAttribute("Pulse") then table.insert(saved.lights, d) end
        if d:IsA("PointLight") and d:GetAttribute("Lamp") then table.insert(saved.lamps, d) end
    end
end

local function restore()
    local s = saved
    if not s then return end
    Lighting.Ambient, Lighting.OutdoorAmbient, Lighting.ColorShift_Top, Lighting.ExposureCompensation = s.ambient, s.outdoor, s.shift, s.exposure
    Lighting.Brightness, Lighting.ShadowSoftness = s.brightness, s.softness
    Lighting.FogStart, Lighting.FogEnd, Lighting.FogColor = s.fogStart, s.fogEnd, s.fogColor
    local atmosphere = Lighting:FindFirstChildOfClass("Atmosphere")
    if atmosphere and s.atmo then
        atmosphere.Density, atmosphere.Offset, atmosphere.Haze, atmosphere.Glare = s.atmo.density, s.atmo.offset, s.atmo.haze, s.atmo.glare
        atmosphere.Color, atmosphere.Decay = s.atmo.color, s.atmo.decay
    end
    local dof = Lighting:FindFirstChild("WeatherDof")
    if dof and dof:IsA("DepthOfFieldEffect") and s.dof ~= nil then dof.Enabled = s.dof end
    saved = nil
end

local function motes(calm: boolean)
    local s = saved
    if not s then return end
    for _, e in s.emitters do e.Enabled = not calm end
    for _, l in s.lights do
        local base = Rules.Forge.base
        l.Brightness = if calm then base else base + math.sin(os.clock() * 2 * math.pi / Rules.Forge.period) * Rules.Forge.amplitude
    end
    -- cosy pass: warm lamps breathe a little (steady base with Reduce Motion)
    local now = os.clock()
    for _, l in s.lamps do
        local base = l:GetAttribute("LampBase")
        if typeof(base) == "number" then
            l.Brightness = Rules.lampBrightness(base, now, l:GetAttribute("LampPhase") or 0, l:GetAttribute("LampPeriod") or 3, calm)
        end
    end
end

-- Cosy pass: the soft ambient bed. One looped Sound made on first use, only when CaveLightingRules.Bed.id is registered ("" = never made).
local bed: Sound? = nil
local function stepBed(dt: number)
    local B = Rules.Bed
    if B.id == "" then return end
    if not bed then
        local sound = Instance.new("Sound")
        sound.Name, sound.SoundId, sound.Looped, sound.Volume, sound.RollOffMaxDistance = "CaveBed", B.id, true, 0, 0
        pcall(function() require(Shared:WaitForChild("AudioMixer")).attach(sound, "ambience") end) -- follows the ambience slider (verify_audio)
        sound.Parent = workspace.CurrentCamera or workspace
        bed = sound
    end
    local sound = bed :: Sound
    local target = Rules.bedVolume(amount)
    sound.Volume += math.clamp(target - sound.Volume, -dt * B.volume / B.fadeSeconds, dt * B.volume / B.fadeSeconds)
    if sound.Volume > 0.002 then if not sound.IsPlaying then sound:Play() end elseif sound.IsPlaying then sound:Stop() end
end

function Cave.step(dt: number)
    if not Config.CaveHub then return end
    PhoneGuard.step(dt)
    local character = player.Character
    local root = character and character:FindFirstChild("HumanoidRootPart")
    local p = if root and root:IsA("BasePart") then (root :: BasePart).Position else nil
    isInside = p ~= nil and Rules.insideAt(p.X, p.Y, p.Z, isInside)
    local calm = Settings.calm()
    amount = Rules.blend(amount, if isInside then 1 else 0, dt, calm)
    stepBed(dt)
    if amount <= 0 then
        if grade then
            grade:Destroy()
            grade = nil
            restore()
        end
        return
    end
    if not saved then save() end
    local L = Rules.Look
    local t = amount
    if not grade then
        local g = Instance.new("ColorCorrectionEffect")
        g.Name = "CaveGrade"
        g.Parent = Lighting
        grade = g
    end
    local g = grade :: ColorCorrectionEffect
    g.Brightness, g.Contrast, g.Saturation = L.grade.brightness * t, L.grade.contrast * t, L.grade.saturation * t
    g.TintColor = Color3.new(1, 1, 1):Lerp(c3(L.grade.tint), t)
    local dof = Lighting:FindFirstChild("WeatherDof")
    if dof and dof:IsA("DepthOfFieldEffect") then dof.Enabled = false end
    Lighting.Ambient = Lighting.Ambient:Lerp(c3(L.ambient), t)
    Lighting.OutdoorAmbient = Lighting.OutdoorAmbient:Lerp(c3(L.outdoorAmbient), t)
    Lighting.ColorShift_Top = Lighting.ColorShift_Top:Lerp(c3(L.colorShiftTop), t)
    Lighting.ExposureCompensation += L.exposure * t
    Lighting.Brightness = saved.brightness + (L.brightness - saved.brightness) * t -- BD-398
    Lighting.ShadowSoftness = saved.softness + (L.shadowSoftness - saved.softness) * t
    Lighting.FogStart = Lighting.FogStart + (L.fogStart - Lighting.FogStart) * t
    Lighting.FogEnd = Lighting.FogEnd + (L.fogEnd - Lighting.FogEnd) * t
    Lighting.FogColor = Lighting.FogColor:Lerp(c3(L.fogColor), t)
    local atmosphere = Lighting:FindFirstChildOfClass("Atmosphere")
    if atmosphere then
        local A = L.atmosphere
        atmosphere.Density = atmosphere.Density + (A.density - atmosphere.Density) * t
        atmosphere.Offset = atmosphere.Offset + (A.offset - atmosphere.Offset) * t
        atmosphere.Haze = atmosphere.Haze + (A.haze - atmosphere.Haze) * t
        atmosphere.Glare = atmosphere.Glare + (A.glare - atmosphere.Glare) * t
        atmosphere.Color = atmosphere.Color:Lerp(c3(A.color), t)
        atmosphere.Decay = atmosphere.Decay:Lerp(c3(A.decay), t)
    end
    motes(calm)
    if isInside then Lava.step(dt, calm) end -- BD-285: scrolling lava falls, phone / Reduce Motion rates
end

return Cave
