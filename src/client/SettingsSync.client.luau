--!strict
-- Settings v2 sync (BD-264): loads the saved per-player settings (attribute SettingsJson, set by the server from
-- profile.settings), applies every change to its consumers, and sends changes back to the server (debounced).
-- Consumers: Calm motion -> Theme.MotionEnabled; sound -> AudioMixer; Effects -> CosmeticVisuals; Weather -> WeatherVisuals
-- (both read SettingsModel directly). jumpSize is stored with a getter only: no consumer yet.
local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Model = require(Shared:WaitForChild("SettingsModel"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Mixer = require(Shared:WaitForChild("AudioMixer"))

local player = Players.LocalPlayer
local remote = ReplicatedStorage:WaitForChild("BeDinoRemotes"):WaitForChild("SetSettings") :: RemoteEvent

local applying = false
local saveSerial = 0
local loaded = false

local function apply(s: Model.Settings)
    Theme.MotionEnabled = not s.calm
    Mixer.set("master", s.master)
    Mixer.set("sfx", s.sfx)
    Mixer.set("ambience", s.ambience)
end

Model.onChange(function(s)
    apply(s)
    if applying or not loaded then return end
    saveSerial += 1
    local mine = saveSerial
    task.delay(0.8, function()
        if mine ~= saveSerial then return end -- a newer change is coming: send only the last one
        remote:FireServer(Model.toStore(Model.get()))
    end)
end)

local function readSaved()
    local raw = player:GetAttribute("SettingsJson")
    if typeof(raw) ~= "string" or raw == "" then return end
    local ok, decoded = pcall(function() return HttpService:JSONDecode(raw) end)
    if not ok then return end
    applying = true
    Model.load(decoded)
    applying = false
    loaded = true
end

player:GetAttributeChangedSignal("SettingsJson"):Connect(function()
    -- The server echoes our own save: ignore it while a newer local change is waiting to be sent.
    readSaved()
end)
readSaved()
-- Old profiles (or a slow load) may have no value yet: edits still save once the first server value arrived or after 5 s.
task.delay(5, function() loaded = true end)
