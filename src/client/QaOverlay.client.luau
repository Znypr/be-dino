--!strict
-- BD-085 / BD-322 phone QA overlay (docs/124). Owner-only developer tool: built only when the server marks this player
-- QaOverlay (Config.QaOverlayEnabled plus Studio or an allow-listed UserId; both false/empty in every committed build).
-- Shows fps, memory, instance/part/particle/light counts, EditableImage budget and ping; "Mark" sends a labelled snapshot that the
-- server prints as a [BD-QA] json line. Display and logging only: changes no gameplay. Plain Theme styling, not player art (docs/72).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Stats = game:GetService("Stats")
local UserInputService = game:GetService("UserInputService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Rules = require(Shared:WaitForChild("QaOverlayRules"))
local player = Players.LocalPlayer
local C = Theme.Colors

while player:GetAttribute("QaOverlay") ~= true do player:GetAttributeChangedSignal("QaOverlay"):Wait() end
local remote = ReplicatedStorage:WaitForChild("BeDinoRemotes"):WaitForChild("QaMark", 30) :: RemoteEvent?
if not remote then return end
local markRemote = remote :: RemoteEvent

local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder = "BeDinoQaOverlay", false, 40
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
gui.Parent = player:WaitForChild("PlayerGui")

local FULL, SMALL = UDim2.fromOffset(330, 230), UDim2.fromOffset(120, 52)
local panel = Instance.new("Frame")
panel.Name, panel.BackgroundColor3, panel.BackgroundTransparency = "QaPanel", C.panel, 0.15
panel.AnchorPoint, panel.Position, panel.Size = Vector2.new(1, 0), UDim2.new(1, -8, 0, 64), FULL
panel.Parent = gui
Theme.decorate(panel, 10)

local readout = Instance.new("TextLabel")
readout.Name = "Readout"
readout.BackgroundTransparency, readout.Position, readout.Size = 1, UDim2.fromOffset(8, 4), UDim2.new(1, -16, 0, 96)
readout.Font, readout.TextSize, readout.TextColor3 = Enum.Font.Code, 14, C.text
readout.TextXAlignment, readout.TextYAlignment, readout.TextWrapped = Enum.TextXAlignment.Left, Enum.TextYAlignment.Top, true
readout.Parent = panel

local stepLabel = Instance.new("TextLabel")
stepLabel.Name = "StepLabel"
stepLabel.BackgroundTransparency, stepLabel.Position, stepLabel.Size = 1, UDim2.fromOffset(8, 100), UDim2.new(1, -16, 0, 22)
stepLabel.Font, stepLabel.TextSize, stepLabel.TextColor3 = Enum.Font.Code, 14, C.gold
stepLabel.TextXAlignment, stepLabel.Parent = Enum.TextXAlignment.Left, panel

local function button(name: string, value: string, color: Color3, position: UDim2, size: UDim2): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.BackgroundColor3, b.Position, b.Size = name, value, color, position, size
    b.Font, b.TextSize, b.TextColor3, b.AutoButtonColor = Enum.Font.FredokaOne, 18, C.text, false
    b.Parent = panel
    Theme.decorate(b, 8)
    return b
end
-- Every target is at least 44 px tall (docs/114 minimum; tools/verify_qa_kit.py checks the literal sizes).
local markButton = button("MarkButton", "Mark", C.accent, UDim2.fromOffset(8, 126), UDim2.new(0.5, -12, 0, 48))
local stepButton = button("StepButton", "Next step", C.blue, UDim2.new(0.5, 4, 0, 126), UDim2.new(0.5, -12, 0, 48))
local hideButton = button("HideButton", "Hide", C.card, UDim2.fromOffset(8, 178), UDim2.new(1, -16, 0, 44))

local stepIndex = 1
local function refreshStep() stepLabel.Text = string.format("step %d/%d: %s", stepIndex, #Rules.Steps, Rules.Steps[stepIndex]) end
refreshStep()

-- Frame rate: average over the last second.
local frames, elapsed, fps = 0, 0, 0
RunService.Heartbeat:Connect(function(dt)
    frames += 1
    elapsed += dt
    if elapsed >= 1 then fps = frames / elapsed frames, elapsed = 0, 0 end
end)

-- Scene counts. One pass over workspace descendants, yielding, run every 5 s and before a mark (never per frame).
-- "Emitters" counts enabled ParticleEmitters and "rate" sums their Rate: Roblox exposes no live particle count, so these are the proxy.
local scene = {parts = 0, emitters = 0, particleRate = 0, beams = 0, lights = 0}
local scanning = false
local function scan()
    if scanning then return end
    scanning = true
    local parts, emitters, rate, beams, lights = 0, 0, 0, 0, 0
    for index, inst in workspace:GetDescendants() do
        if inst:IsA("BasePart") then
            parts += 1
        elseif inst:IsA("ParticleEmitter") then
            if inst.Enabled and inst.Rate > 0 then emitters += 1 rate += inst.Rate end
        elseif inst:IsA("Beam") then
            if inst.Enabled then beams += 1 end
        elseif inst:IsA("PointLight") or inst:IsA("SpotLight") or inst:IsA("SurfaceLight") then
            if inst.Enabled and inst.Brightness > 0 then lights += 1 end
        end
        if index % 4000 == 0 then task.wait() end
    end
    scene = {parts = parts, emitters = emitters, particleRate = rate, beams = beams, lights = lights}
    scanning = false
end

local function snapshot(label: string): {[string]: any}
    local okMem, mem = pcall(function() return Stats:GetTotalMemoryUsageMb() end)
    local okInst, inst = pcall(function() return (Stats :: any).InstanceCount end)
    local okPing, ping = pcall(function() return player:GetNetworkPing() * 2000 end) -- one-way seconds -> round trip ms
    local camera = workspace.CurrentCamera
    local dinos = 0
    for _, other in Players:GetPlayers() do if other.Character then dinos += 1 end end
    return {
        label = label, fps = fps, memMb = if okMem then mem else nil, instances = if okInst then inst else nil,
        parts = scene.parts, emitters = scene.emitters, particleRate = scene.particleRate, beams = scene.beams, lights = scene.lights,
        editableMiB = workspace:GetAttribute("LowPolyImagesMiB"), editableLive = workspace:GetAttribute("LowPolyImagesLive"),
        pingMs = if okPing then ping else nil, dinos = dinos,
        viewW = if camera then camera.ViewportSize.X else nil, viewH = if camera then camera.ViewportSize.Y else nil,
        touch = UserInputService.TouchEnabled,
    }
end

task.spawn(function()
    while gui.Parent do
        scan()
        task.wait(5)
    end
end)
task.spawn(function()
    while gui.Parent do
        readout.Text = table.concat(Rules.lines(Rules.sanitize(snapshot("live")) or {}), "\n")
        task.wait(0.5)
    end
end)

markButton.Activated:Connect(function()
    task.spawn(function()
        markButton.Text = "..."
        scan()
        markRemote:FireServer(snapshot(Rules.Steps[stepIndex]))
        markButton.Text = "Marked!"
        task.wait(0.8)
        markButton.Text = "Mark"
    end)
end)
stepButton.Activated:Connect(function()
    stepIndex = stepIndex % #Rules.Steps + 1
    refreshStep()
end)
local collapsed = false
hideButton.Activated:Connect(function()
    collapsed = not collapsed
    readout.Visible, stepLabel.Visible = not collapsed, not collapsed
    markButton.Visible, stepButton.Visible = not collapsed, not collapsed
    hideButton.Position = if collapsed then UDim2.fromOffset(8, 4) else UDim2.fromOffset(8, 178)
    hideButton.Text = if collapsed then "QA" else "Hide"
    panel.Size = if collapsed then SMALL else FULL
end)
