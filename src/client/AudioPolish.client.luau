--!strict
-- BD-1218 + BD-1219 (docs/242 benchmark): calm music beds (island, home, softer hatch bed) with crossfades, the sounds for the silent
-- Sfx cues, a soft pop when a menu window opens or closes, a soft defeat and nest-open cue, and soft dino footsteps by surface instead
-- of Roblox's human footsteps. ONLY while Config.AudioPolishEnabled is on (playtest profile): flag off = this script returns on its
-- first line and the game sounds exactly as before. Data and pure rules: src/shared/AudioPolish.luau (offline-tested by
-- tools/verify_audio_polish.py). Every sound goes through AudioMixer (music group / Sfx group), Sfx.Master and the sound switch.
-- Nobody has listened to it: the owner judges by ear before it ships (docs/87).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config")) :: any
if Config.AudioPolishEnabled ~= true then return end

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")
local A = require(Shared:WaitForChild("AudioPolish"))
local Sfx = require(Shared:WaitForChild("Sfx")) :: any
local Rules = require(Shared:WaitForChild("SfxRules")) :: any
local Mixer = require(Shared:WaitForChild("AudioMixer"))
local Theme = require(Shared:WaitForChild("UITheme")) :: any

local player = Players.LocalPlayer
A.apply(Sfx, Rules)
local function soundOn(): boolean return Theme.HatchSoundEnabled ~= false end

-- Music beds: created once, looped, volume 0 until faded in.
local folder = Instance.new("Folder")
folder.Name = "AudioPolish"
folder.Parent = SoundService
local beds: {[string]: Sound} = {}
local levels: {[string]: number} = {}
for _, name in A.MusicOrder do
    local sound = Instance.new("Sound")
    sound.Name, sound.SoundId, sound.Looped, sound.Volume = "Music_" .. name, A.Music[name].id, true, 0
    sound.Parent = folder
    Mixer.attach(sound, "music")
    beds[name], levels[name] = sound, 0
end

local gui: Instance? = nil
task.spawn(function() gui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI", 60) end)
local function screen(): string
    local g = gui
    local value = if g then g:GetAttribute("Screen") else nil
    return if type(value) == "string" then value else ""
end

-- Footsteps: a small pool, Sfx group, Sfx.Master; the local dino only.
local stepPool: {Sound} = {}
for i = 1, 3 do
    local s = Instance.new("Sound")
    s.Name = "Step" .. i
    s.Parent = folder
    Mixer.attach(s, "sfx")
    stepPool[i] = s
end
local stepSlot, stepVariant, stepCount, nextStep = 0, 0, 0, 0
local function playStep(set: string)
    local def = A.Steps[set]
    if not def then return end
    stepSlot = stepSlot % #stepPool + 1
    stepVariant = stepVariant % #def.ids + 1
    stepCount += 1
    local s = stepPool[stepSlot]
    s.SoundId = def.ids[stepVariant]
    s.Volume = def.volume * Sfx.Master
    s.PlaybackSpeed = def.rate * (if stepCount % 2 == 0 then 1.03 else .97)
    s.TimePosition = 0
    s:Play()
end

-- Roblox's default character sounds play human footsteps ("Running" in the root part): silence that one sound on every character.
local function muteRunning(sound: Instance)
    if sound:IsA("Sound") and sound.Name == "Running" then
        sound.Volume = 0
        sound:GetPropertyChangedSignal("Volume"):Connect(function() if sound.Volume ~= 0 then sound.Volume = 0 end end)
    end
end
local function watchCharacter(character: Model)
    local root = character:WaitForChild("HumanoidRootPart", 10)
    if not root then return end
    for _, child in root:GetChildren() do muteRunning(child) end
    root.ChildAdded:Connect(muteRunning)
end
local function watchPlayer(p: Player)
    if p.Character then task.spawn(watchCharacter, p.Character) end
    p.CharacterAdded:Connect(watchCharacter)
end
for _, p in Players:GetPlayers() do watchPlayer(p) end
Players.PlayerAdded:Connect(watchPlayer)

-- Soft defeat: the server marks the run "Ending" and then the reason; only a defeat (not a manual exit) gets the cue.
local function watchRunState(character: Model)
    character:GetAttributeChangedSignal("RunState"):Connect(function()
        if character:GetAttribute("RunState") ~= "Ending" then return end
        task.delay(.2, function()
            if A.DefeatReasons[player:GetAttribute("LastRunEndReason") :: any] then Sfx.playCue("defeat_soft") end
        end)
    end)
end
if player.Character then watchRunState(player.Character) end
player.CharacterAdded:Connect(watchRunState)

player:GetAttributeChangedSignal("LastNestClaimAt"):Connect(function()
    if player:GetAttribute("LastNestClaimStatus") == "opened" then Sfx.playCue("nest_open_cue") end
end)

-- Window open / close pop (the hatch screen has its own sounds).
local lastScreen = ""
RunService.Heartbeat:Connect(function(dt)
    local current = screen()
    if current ~= lastScreen then
        if lastScreen == "" and current ~= "hatch" then Sfx.play("ui_open")
        elseif current == "" and lastScreen ~= "hatch" then Sfx.play("ui_close") end
        lastScreen = current
    end
    -- music crossfade
    local on = soundOn()
    local targets = A.bedTargets(A.musicTarget(player:GetAttribute("Location"), current), on)
    for name, sound in beds do
        local level = A.step(levels[name], targets[name], dt, A.Music[name].volume)
        levels[name] = level
        sound.Volume = level
        if level > .002 then if not sound.IsPlaying then sound:Play() end elseif sound.IsPlaying then sound:Pause() end
    end
    -- footsteps
    local character = player.Character
    local humanoid = if character then character:FindFirstChildOfClass("Humanoid") else nil
    local root = if character then character:FindFirstChild("HumanoidRootPart") :: BasePart? else nil
    if not (on and humanoid and root and character) or humanoid.Health <= 0 then return end
    local swimming = humanoid:GetState() == Enum.HumanoidStateType.Swimming
    local set = A.surface(humanoid.FloorMaterial.Name, swimming)
    local v = root.AssemblyLinearVelocity
    local okScale, scale = pcall(function() return character:GetScale() end)
    local interval = A.stepInterval(Vector3.new(v.X, 0, v.Z).Magnitude, if okScale then scale else 1)
    local now = os.clock()
    if not set or not interval then nextStep = now return end
    if now >= nextStep then
        if nextStep > 0 then playStep(set) end
        nextStep = now + interval
    end
end)
