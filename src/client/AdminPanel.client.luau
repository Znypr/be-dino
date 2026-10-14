--!strict
-- BD-120 owner-only admin panel (docs/79). Built only when the server marks this player IsAdmin;
-- every button is re-checked on the server (AdminService), so this UI grants nothing by itself.
-- Developer tool: plain Theme styling, not player-facing art (docs/72 applies to player UI).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Rules = require(Shared:WaitForChild("AdminRules"))
local ProgressionConfig = require(Shared:WaitForChild("ProgressionConfig"))
local player = Players.LocalPlayer
local C = Theme.Colors

while player:GetAttribute("IsAdmin") ~= true do player:GetAttributeChangedSignal("IsAdmin"):Wait() end
local remote = ReplicatedStorage:WaitForChild("BeDinoRemotes"):WaitForChild("AdminAction", 30) :: RemoteFunction?
if not remote then return end
local adminRemote = remote :: RemoteFunction

local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder = "BeDinoAdminUI", false, 30
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
gui.Parent = player:WaitForChild("PlayerGui")

local function text(parent: Instance, value: string, size: number, height: number): TextLabel
    local label = Instance.new("TextLabel")
    label.BackgroundTransparency, label.Size, label.Text = 1, UDim2.new(1, 0, 0, height), value
    label.Font, label.TextSize, label.TextColor3 = Enum.Font.FredokaOne, size, C.text
    label.TextStrokeTransparency, label.TextXAlignment, label.TextWrapped = 0, Enum.TextXAlignment.Left, true
    label.Parent = parent
    return label
end
local function button(parent: Instance, value: string, color: Color3, size: UDim2): TextButton
    local b = Instance.new("TextButton")
    b.Size, b.BackgroundColor3, b.Text, b.TextSize, b.TextColor3 = size, color, value, 16, C.text
    b.AutoButtonColor = false
    b.Parent = parent
    Theme.decorate(b, 8)
    return b
end

local toggle = button(gui, "Admin", C.purple, UDim2.fromOffset(84, 36))
toggle.Name, toggle.Position = "AdminToggle", UDim2.fromOffset(14, 8)

local panel = Instance.new("Frame")
panel.Name, panel.BackgroundColor3, panel.Visible = "AdminPanel", C.panel, false
panel.Position, panel.Size = UDim2.fromOffset(14, 52), UDim2.new(0, 320, 1, -64)
panel.Parent = gui
Theme.decorate(panel, 12)
local sizeLimit = Instance.new("UISizeConstraint") sizeLimit.MaxSize = Vector2.new(320, 640) sizeLimit.Parent = panel
local scroll = Instance.new("ScrollingFrame")
scroll.BackgroundTransparency, scroll.BorderSizePixel, scroll.ScrollBarThickness = 1, 0, 6
scroll.Position, scroll.Size = UDim2.fromOffset(10, 8), UDim2.new(1, -20, 1, -16)
scroll.AutomaticCanvasSize, scroll.CanvasSize = Enum.AutomaticSize.Y, UDim2.new()
scroll.Parent = panel
local list = Instance.new("UIListLayout")
list.Padding, list.SortOrder = UDim.new(0, 6), Enum.SortOrder.LayoutOrder
list.Parent = scroll

local order = 0
local function place<T>(object: T): T
    order += 1
    (object :: any).LayoutOrder = order
    return object
end
place(text(scroll, "Admin (only you)", 22, 28))
local status = place(text(scroll, "Changes last until the server restarts.", 14, 34))
status.TextColor3 = C.gold

local function call(action: string, a: any?, b: any?, done: string?)
    task.spawn(function()
        local ok, okValue, message = pcall(adminRemote.InvokeServer, adminRemote, action, a, b)
        local success = ok and okValue == true
        local failure = string.gsub("Failed: " .. tostring(if ok then message else okValue), "_", " ")
        status.Text = if success then (done or "Done") else failure
        status.TextColor3 = if success then C.accent else C.red
    end)
end

-- Sliders: the label updates while dragging; the value is sent once on release.
local dragging: {key: string, apply: (number) -> (), send: () -> ()}? = nil
local feelHeaderShown = false
for _, key in Rules.SettingOrder do
    local spec = Rules.Settings[key]
    if spec.group == "feel" and not feelHeaderShown then
        feelHeaderShown = true
        place(text(scroll, "Feel (live, not saved)", 18, 24))
    end
    local holder = place(Instance.new("Frame"))
    holder.BackgroundTransparency, holder.Size, holder.Parent = 1, UDim2.new(1, 0, 0, 62), scroll
    local label = text(holder, "", 16, 22)
    local track = Instance.new("Frame")
    track.BackgroundColor3, track.Position, track.Size = C.card, UDim2.fromOffset(8, 30), UDim2.new(1, -16, 0, 12)
    track.Active, track.Parent = true, holder
    Theme.decorate(track, 6)
    local fill = Instance.new("Frame")
    fill.BackgroundColor3, fill.BorderSizePixel, fill.Parent = C.accent, 0, track
    local fillCorner = Instance.new("UICorner") fillCorner.CornerRadius = UDim.new(0, 6) fillCorner.Parent = fill
    local knob = Instance.new("Frame")
    knob.AnchorPoint, knob.Size, knob.BackgroundColor3, knob.ZIndex = Vector2.new(.5, .5), UDim2.fromOffset(24, 24), C.gold, 2
    knob.Parent = track
    Theme.decorate(knob, 12)
    local function show(value: number)
        local fraction = Rules.toFraction(key, value)
        label.Text = spec.label .. ": " .. Rules.format(value, key)
        fill.Size = UDim2.fromScale(fraction, 1)
        knob.Position = UDim2.fromScale(fraction, .5)
    end
    local attribute = "Admin_" .. key
    show(workspace:GetAttribute(attribute) or spec.default)
    workspace:GetAttributeChangedSignal(attribute):Connect(function()
        if not (dragging and dragging.key == key) then show(workspace:GetAttribute(attribute) or spec.default) end
    end)
    local current = spec.default
    local function apply(x: number)
        current = Rules.fromFraction(key, (x - track.AbsolutePosition.X) / math.max(1, track.AbsoluteSize.X))
        show(current)
    end
    -- 44 px touch target around the thin track (phones): a transparent hit area, same drag behaviour.
    local hit = Instance.new("Frame")
    hit.BackgroundTransparency, hit.Size, hit.Position, hit.Active, hit.Parent = 1, UDim2.new(1, 0, 0, 44), UDim2.fromOffset(0, -16), true, track
    hit.InputBegan:Connect(function(input)
        if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
            dragging = {key = key, apply = apply, send = function()
                call("set", key, current, spec.label .. " " .. Rules.format(current, key))
            end}
            apply(input.Position.X)
        end
    end)
end
UserInputService.InputChanged:Connect(function(input)
    if dragging and (input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch) then
        dragging.apply(input.Position.X)
    end
end)
UserInputService.InputEnded:Connect(function(input)
    if dragging and (input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch) then
        local finished = dragging
        dragging = nil
        finished.send()
    end
end)

-- Weather: pick a length, then tap an event to start it now.
place(text(scroll, "Weather", 18, 24))
local weatherNow = place(text(scroll, "", 14, 20))
local lengths = {{label = "1 min", seconds = 60}, {label = "3 min", seconds = 180}, {label = "10 min", seconds = 600}}
local chosenSeconds = ProgressionConfig.WeatherDuration
local lengthRow = place(Instance.new("Frame"))
lengthRow.BackgroundTransparency, lengthRow.Size, lengthRow.Parent = 1, UDim2.new(1, 0, 0, 34), scroll
local rowLayout = Instance.new("UIListLayout")
rowLayout.FillDirection, rowLayout.Padding = Enum.FillDirection.Horizontal, UDim.new(0, 6)
rowLayout.Parent = lengthRow
local lengthButtons: {[TextButton]: number} = {}
local function refreshLengths()
    for b, seconds in lengthButtons do b.BackgroundColor3 = if seconds == chosenSeconds then C.blue else C.card end
end
for _, entry in lengths do
    local b = button(lengthRow, entry.label, C.card, UDim2.new(1 / 3, -4, 1, 0))
    lengthButtons[b] = entry.seconds
    b.Activated:Connect(function() chosenSeconds = entry.seconds refreshLengths() end)
end
refreshLengths()
local grid = place(Instance.new("Frame"))
grid.BackgroundTransparency, grid.AutomaticSize, grid.Size, grid.Parent = 1, Enum.AutomaticSize.Y, UDim2.new(1, 0, 0, 0), scroll
local gridLayout = Instance.new("UIGridLayout")
gridLayout.CellSize, gridLayout.CellPadding = UDim2.new(.5, -4, 0, 36), UDim2.fromOffset(6, 6)
gridLayout.SortOrder, gridLayout.Parent = Enum.SortOrder.LayoutOrder, grid
for index, event in ProgressionConfig.Weather do
    local b = button(grid, event.name, C.card, UDim2.new())
    b.LayoutOrder, b.TextScaled = index, true
    b.Activated:Connect(function() call("startWeather", event.id, chosenSeconds, event.name .. " started") end)
end
local stop = place(button(scroll, "Stop weather", C.red, UDim2.new(1, 0, 0, 36)))
stop.Activated:Connect(function() call("stopWeather", nil, nil, "Weather stopped") end)
local reset = place(button(scroll, "Reset sliders", C.card, UDim2.new(1, 0, 0, 36)))
reset.Activated:Connect(function() call("reset", nil, nil, "Sliders reset") end)

task.spawn(function()
    while gui.Parent do
        if panel.Visible then
            local name = workspace:GetAttribute("WeatherName") or "Clear"
            local endsAt = workspace:GetAttribute("WeatherEndsAt") or 0
            local left = math.max(0, math.floor(endsAt - workspace:GetServerTimeNow()))
            weatherNow.Text = if (workspace:GetAttribute("WeatherId") or "clear") == "clear" then "Now: Clear"
                else string.format("Now: %s (%d:%02d left)", name, left // 60, left % 60)
        end
        task.wait(.5)
    end
end)

local function setOpen(open: boolean)
    panel.Visible = open
    toggle.BackgroundColor3 = if open then C.gold else C.purple
end
toggle.Activated:Connect(function() setOpen(not panel.Visible) end)
UserInputService.InputBegan:Connect(function(input, processed)
    if not processed and input.KeyCode == Enum.KeyCode.F2 then setOpen(not panel.Visible) end
end)
player:GetAttributeChangedSignal("IsAdmin"):Connect(function()
    if player:GetAttribute("IsAdmin") ~= true then gui:Destroy() end
end)
