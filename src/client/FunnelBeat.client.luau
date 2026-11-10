--!strict
-- BD-1166 (docs/122): tells the server which KIND of screen is open, as one whitelisted word (RunTelemetry.Beats: Closed, HatchScreen,
-- Results, Shop, Index, Menu), so the anonymous playtest telemetry can say where a player was when they left and when a shop or the
-- Index was first opened. Only while Config.RunTelemetryEnabled is on (playtest profile); in the default build this script returns
-- on its first line: no wait, no connection, no remote. It sends a word only when the kind of screen CHANGES, draws nothing and
-- reads only the "Screen" attribute that Bootstrap sets on BeDinoUI. The Fusion menu is its own ScreenGui and is not reported yet.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config")) :: any
if Config.RunTelemetryEnabled ~= true then return end

local Players = game:GetService("Players")
local RunTelemetry = require(Shared:WaitForChild("RunTelemetry"))

local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes", 30)
local remote = if remotes then remotes:WaitForChild("FunnelBeat", 30) else nil
local gui = Players.LocalPlayer:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI", 60)
if not remote or not gui or not remote:IsA("RemoteEvent") then return end

local last = "Closed"
local function send()
    local word = RunTelemetry.screenBeat(gui:GetAttribute("Screen"))
    if word == last then return end
    last = word
    remote:FireServer(word)
end
gui:GetAttributeChangedSignal("Screen"):Connect(send)
send()
