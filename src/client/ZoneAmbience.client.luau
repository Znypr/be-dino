--!strict
-- BD-1225 (docs/242 gap 14): soft ambient loops per World V3 zone, crossfaded by where the local dino stands. ONLY while Config.ZoneAmbienceEnabled
-- and Config.WorldV3Enabled are on (playtest profile): otherwise this script returns on its first lines and nothing is created.
-- Data and pure rules: src/shared/ZoneAmbience.luau. Every loop goes through AudioMixer's "ambience" group (the Weather slider) and the sound switch.
-- It plays on the island only, and fades out while a menu window is open. Unheard by agents: the owner judges by ear (docs/87).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config")) :: any
if Config.ZoneAmbienceEnabled ~= true or Config.WorldV3Enabled ~= true then return end

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")
local Z = require(Shared:WaitForChild("ZoneAmbience"))
local WorldV3 = require(Shared:WaitForChild("WorldV3")) :: any
local Mixer = require(Shared:WaitForChild("AudioMixer"))
local Theme = require(Shared:WaitForChild("UITheme")) :: any

local player = Players.LocalPlayer
local folder = Instance.new("Folder")
folder.Name = "ZoneAmbience"
folder.Parent = SoundService
local loops: {[string]: Sound} = {}
local levels: {[string]: number} = {}
for _, name in Z.Order do
    local id = Z.normalizeId(Z.Loops[name].id)
    if id then
        local sound = Instance.new("Sound")
        sound.Name, sound.SoundId, sound.Looped, sound.Volume = "Zone_" .. name, id, true, 0
        sound.Parent = folder
        Mixer.attach(sound, "ambience")
        loops[name], levels[name] = sound, 0
    end
end
if next(loops) == nil then return end

local gui: Instance? = nil
task.spawn(function() gui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI", 60) end)
local active: string? = nil
local nextCheck = 0

RunService.Heartbeat:Connect(function(dt)
    local now = os.clock()
    if now >= nextCheck then -- the zone changes slowly: four looks a second are enough
        nextCheck = now + .25
        local character = player.Character
        local root = if character then character:FindFirstChild("HumanoidRootPart") :: BasePart? else nil
        active = if root then Z.zoneFor(root.Position.X, root.Position.Z, WorldV3) else nil
    end
    local g = gui
    local screen = if g then g:GetAttribute("Screen") else nil
    local location = player:GetAttribute("Location")
    local targets = Z.targets(active, location == "Island" or location == nil, screen, Theme.HatchSoundEnabled ~= false) -- nil = no cave hub: the island is all there is
    for name, sound in loops do
        local level = Z.step(levels[name], targets[name], dt, Z.Loops[name].volume)
        levels[name] = level
        sound.Volume = level
        if level > .002 then if not sound.IsPlaying then sound:Play() end elseif sound.IsPlaying then sound:Pause() end
    end
end)
