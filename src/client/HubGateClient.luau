--!strict
-- BD-290 (docs/104 s2.3): the calm "Leaving..." bar shown while the local player stands in the Island Gate arch. It is only
-- feedback: the server (HubGateService) measures the same 1.5 s and starts the run through the existing run-start path,
-- so nothing here fires a remote. Leaving the arch hides the bar (cancel). Reduce Motion: no fade, the bar moves in quarter
-- steps. No numbers on screen (docs/72). attach() returns at once while Config.CaveHub is false.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Rules = require(Shared:WaitForChild("CaveGateRules"))
local Settings = require(Shared:WaitForChild("SettingsModel"))
local SpawnGeometry = require(Shared:WaitForChild("SpawnGeometry"))

local Client = {}
local attached = false

function Client.attach(gui: Instance)
    if Config.CaveHub ~= true or attached then return end
    attached = true
    local player = Players.LocalPlayer
    local holder = Instance.new("Frame")
    holder.Name, holder.BackgroundColor3, holder.BackgroundTransparency, holder.BorderSizePixel = "IslandGateBar", Color3.fromRGB(40, 28, 70), 0.25, 0
    holder.AnchorPoint, holder.Position, holder.Size = Vector2.new(0.5, 1), UDim2.new(0.5, 0, 1, -90), UDim2.fromOffset(300, 44)
    holder.Visible, holder.ZIndex, holder.Active = false, 7, false
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 12) corner.Parent = holder
    local label = Instance.new("TextLabel")
    label.Name, label.BackgroundTransparency, label.Text, label.Font, label.TextSize = "Words", 1, Rules.BarText, Enum.Font.FredokaOne, 20
    label.TextColor3, label.Size, label.Position, label.ZIndex = Color3.fromRGB(255, 244, 220), UDim2.new(1, 0, 0, 22), UDim2.fromOffset(0, 3), 8
    label.Parent = holder
    local track = Instance.new("Frame")
    track.Name, track.BackgroundColor3, track.BorderSizePixel = "Track", Color3.fromRGB(20, 14, 40), 0
    track.Size, track.Position, track.ZIndex = UDim2.new(1, -24, 0, 8), UDim2.new(0, 12, 1, -14), 8
    local trackCorner = Instance.new("UICorner") trackCorner.CornerRadius = UDim.new(0, 4) trackCorner.Parent = track
    track.Parent = holder
    local fill = Instance.new("Frame")
    fill.Name, fill.BackgroundColor3, fill.BorderSizePixel, fill.Size, fill.ZIndex = "Fill", Color3.fromRGB(255, 200, 70), 0, UDim2.fromScale(0, 1), 9
    local fillCorner = Instance.new("UICorner") fillCorner.CornerRadius = UDim.new(0, 4) fillCorner.Parent = fill
    fill.Parent = track
    holder.Parent = gui

    local session = Rules.newSession()
    RunService.Heartbeat:Connect(function()
        local character = player.Character
        local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
        local state: any = {caveHub = true, profileState = "Loaded", dinoAttached = true, alive = true, inHub = false,
            runState = if character then character:GetAttribute("RunState") else nil}
        local inside = false
        if root and root:IsA("BasePart") then
            local p = root.Position
            state.inHub = SpawnGeometry.inHub(Config, p.X, p.Z)
            inside = Rules.inZone(p.X, p.Z, p.Y)
        end
        local progress = Rules.step(session, inside, Rules.eligible(state), os.clock())
        local show = inside and state.runState == "Sanctuary" and state.inHub and (session.since ~= nil)
        if holder.Visible ~= show then holder.Visible = show end
        if show then fill.Size = UDim2.fromScale(Rules.barFraction(progress, Settings.calm()), 1) end
    end)
end

return Client
