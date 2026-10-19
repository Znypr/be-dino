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
    -- BD-261: one fixed size for every admin button (TextScaled gave each label a different size and clipped long ones).
    b.Size, b.BackgroundColor3, b.Text, b.TextSize, b.TextColor3 = size, color, value, 20, C.text
    b.Font, b.TextWrapped = Enum.Font.FredokaOne, true
    b.AutoButtonColor = false
    b.Parent = parent
    Theme.decorate(b, 8)
    return b
end

local toggle = button(gui, "Admin", C.purple, UDim2.fromOffset(120, 48))
toggle.Name, toggle.Position = "AdminToggle", UDim2.fromOffset(14, 8)

-- BD-531: Bootstrap publishes where the Admin button may sit (TouchLayout.admin): desktop keeps (14, 8); on the phone layout that spot is the
-- egg plate, so it moves to the bottom-left row. The button only follows the attribute; nothing else moves it.
task.spawn(function()
    local main = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI", 30)
    if not main then return end
    local function pin()
        local rect = main:GetAttribute("AdminRect")
        if typeof(rect) == "Rect" then
            toggle.Position, toggle.Size = UDim2.fromOffset(rect.Min.X, rect.Min.Y), UDim2.fromOffset(rect.Width, rect.Height)
        end
    end
    main:GetAttributeChangedSignal("AdminRect"):Connect(pin)
    pin()
end)

local panel = Instance.new("Frame")
panel.Name, panel.BackgroundColor3, panel.Visible = "AdminPanel", C.panel, false
-- BD-261: as wide as the screen allows up to 420 px (phone landscape), so no button runs past the edge.
panel.Position, panel.Size = UDim2.fromOffset(14, 64), UDim2.new(1, -28, 1, -76)
panel.Parent = gui
Theme.decorate(panel, 12)
local sizeLimit = Instance.new("UISizeConstraint") sizeLimit.MaxSize = Vector2.new(420, 760) sizeLimit.Parent = panel
local scroll = Instance.new("ScrollingFrame")
scroll.BackgroundTransparency, scroll.BorderSizePixel, scroll.ScrollBarThickness = 1, 0, 6
scroll.Position, scroll.Size = UDim2.fromOffset(10, 8), UDim2.new(1, -20, 1, -16)
scroll.AutomaticCanvasSize, scroll.CanvasSize = Enum.AutomaticSize.Y, UDim2.new()
scroll.Parent = panel
-- BD-261: keep every row clear of the 6 px scroll bar (it used to cover the right-hand buttons).
local scrollPadding = Instance.new("UIPadding") scrollPadding.PaddingRight = UDim.new(0, 12) scrollPadding.Parent = scroll
local list = Instance.new("UIListLayout")
list.Padding, list.SortOrder = UDim.new(0, 8), Enum.SortOrder.LayoutOrder
list.Parent = scroll

-- BD-452 (docs/134 s5): the Gift page. The server creates AdminGiftAction only when GiftClaimEnabled, AdminGiftsEnabled and AdminPanelEnabled are
-- all on (pinned off), so with the flags off there is no remote here, no tab row, no page and the layout above is exactly as before.
do
    local folder = adminRemote.Parent
    local giftRemote = if folder then folder:FindFirstChild("AdminGiftAction") else nil
    if giftRemote and giftRemote:IsA("RemoteFunction") then
        local tabTop = 64
        scroll.Position, scroll.Size = UDim2.fromOffset(10, tabTop), UDim2.new(1, -20, 1, -(tabTop + 8))
        local giftPage = require(script.Parent:WaitForChild("AdminGiftPage")).build(panel, giftRemote, tabTop)
        local tabs = Instance.new("Frame")
        tabs.Name, tabs.BackgroundTransparency, tabs.Position, tabs.Size, tabs.Parent = "AdminTabs", 1, UDim2.fromOffset(10, 8), UDim2.new(1, -20, 0, 48), panel
        local tabLayout = Instance.new("UIListLayout")
        tabLayout.FillDirection, tabLayout.Padding = Enum.FillDirection.Horizontal, UDim.new(0, 8)
        tabLayout.Parent = tabs
        local toolsTab = button(tabs, "Tools", C.accent, UDim2.new(0.5, -4, 1, 0))
        local giftTab = button(tabs, "Gift", C.card, UDim2.new(0.5, -4, 1, 0))
        local function showPage(gifts: boolean)
            scroll.Visible, giftPage.Visible = not gifts, gifts
            toolsTab.BackgroundColor3 = if gifts then C.card else C.accent
            giftTab.BackgroundColor3 = if gifts then C.accent else C.card
        end
        toolsTab.Activated:Connect(function() showPage(false) end)
        giftTab.Activated:Connect(function() showPage(true) end)
    end
end

local order = 0
local function place<T>(object: T): T
    order += 1
    (object :: any).LayoutOrder = order
    return object
end
place(text(scroll, "Admin (only you)", 28, 36))
local status = place(text(scroll, "Changes last until the server restarts.", 18, 46))
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

-- Weather: pick one of the events, then Start now / Stop. A length row sets how long it lasts.
local function section(title: string)
    local header = place(text(scroll, title, 24, 34))
    header.TextColor3 = C.gold
    local line = Instance.new("Frame")
    line.BackgroundColor3, line.BorderSizePixel, line.Position, line.Size, line.Parent = C.gold, 0, UDim2.new(0, 0, 1, -3), UDim2.new(1, 0, 0, 2), header
end
section("Weather")
local weatherNow = place(text(scroll, "", 20, 28))
local chosenSeconds = ProgressionConfig.WeatherDuration
local chosenEvent: string = ProgressionConfig.Weather[1].id
local function row(height: number): Frame
    local frame = place(Instance.new("Frame"))
    frame.BackgroundTransparency, frame.Size, frame.Parent = 1, UDim2.new(1, 0, 0, height), scroll
    return frame
end
local lengthRow = row(48)
local rowLayout = Instance.new("UIListLayout")
rowLayout.FillDirection, rowLayout.Padding = Enum.FillDirection.Horizontal, UDim.new(0, 8)
rowLayout.Parent = lengthRow
local lengths = {{label = "1 min", seconds = 60}, {label = "3 min", seconds = 180}, {label = "10 min", seconds = 600}}
local lengthButtons: {[TextButton]: number} = {}
local eventButtons: {[TextButton]: string} = {}
local function refresh()
    for b, seconds in lengthButtons do b.BackgroundColor3 = if seconds == chosenSeconds then C.blue else C.card end
    for b, id in eventButtons do b.BackgroundColor3 = if id == chosenEvent then C.accent else C.card end
end
for _, entry in lengths do
    local b = button(lengthRow, entry.label, C.card, UDim2.new(1 / 3, -6, 1, 0))
    lengthButtons[b] = entry.seconds
    b.Activated:Connect(function() chosenSeconds = entry.seconds refresh() end)
end
local grid = place(Instance.new("Frame"))
grid.BackgroundTransparency, grid.AutomaticSize, grid.Size, grid.Parent = 1, Enum.AutomaticSize.Y, UDim2.new(1, 0, 0, 0), scroll
local gridLayout = Instance.new("UIGridLayout")
gridLayout.CellSize, gridLayout.CellPadding = UDim2.new(.5, -4, 0, 44), UDim2.fromOffset(8, 8)
gridLayout.SortOrder, gridLayout.Parent = Enum.SortOrder.LayoutOrder, grid
for index, event in ProgressionConfig.Weather do
    local b = button(grid, event.name, C.card, UDim2.new())
    b.LayoutOrder = index
    eventButtons[b] = event.id
    b.Activated:Connect(function() chosenEvent = event.id refresh() end)
end
local startStop = row(56)
local startLayout = Instance.new("UIListLayout")
startLayout.FillDirection, startLayout.Padding = Enum.FillDirection.Horizontal, UDim.new(0, 8)
startLayout.Parent = startStop
local start = button(startStop, "Start now", C.accent, UDim2.new(.5, -4, 1, 0))
start.Activated:Connect(function() call("startWeather", chosenEvent, chosenSeconds, "Weather started") end)
local stop = button(startStop, "Stop", C.red, UDim2.new(.5, -4, 1, 0))
stop.Activated:Connect(function() call("stopWeather", nil, nil, "Weather stopped") end)
refresh()

-- Sliders: the label updates while dragging; the value is sent once on release.
local dragging: {key: string, apply: (number) -> (), send: () -> ()}? = nil
local feelHeaderShown = false
local runHeaderShown = false
for _, key in Rules.SettingOrder do
    local spec = Rules.Settings[key]
    if spec.group ~= "feel" and not runHeaderShown then
        runHeaderShown = true
        section("Run")
    end
    if spec.group == "feel" and not feelHeaderShown then
        feelHeaderShown = true
        section("Feel (live, not saved)")
    end
    local holder = place(Instance.new("Frame"))
    holder.BackgroundTransparency, holder.Size, holder.Parent = 1, UDim2.new(1, 0, 0, 76), scroll
    local label = text(holder, "", 20, 28)
    local track = Instance.new("Frame")
    track.BackgroundColor3, track.Position, track.Size = C.card, UDim2.fromOffset(12, 42), UDim2.new(1, -24, 0, 16)
    track.Active, track.Parent = true, holder
    Theme.decorate(track, 6)
    local fill = Instance.new("Frame")
    fill.BackgroundColor3, fill.BorderSizePixel, fill.Parent = C.accent, 0, track
    local fillCorner = Instance.new("UICorner") fillCorner.CornerRadius = UDim.new(0, 6) fillCorner.Parent = fill
    local knob = Instance.new("Frame")
    knob.AnchorPoint, knob.Size, knob.BackgroundColor3, knob.ZIndex = Vector2.new(.5, .5), UDim2.fromOffset(32, 32), C.gold, 2
    knob.Parent = track
    Theme.decorate(knob, 16)
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

section("Debug")
local cullInfo = place(text(scroll, "", 18, 80))
cullInfo.TextYAlignment = Enum.TextYAlignment.Top
local reset = place(button(scroll, "Reset sliders", C.card, UDim2.new(1, 0, 0, 48)))
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
        if panel.Visible then
            cullInfo.Text = string.format("%s: %s props, %s parts (budget %s, radius %s)\nInstances: %d", tostring(player:GetAttribute("CullClass") or "?"),
                tostring(player:GetAttribute("CullProps") or "?"), tostring(player:GetAttribute("CullParts") or "?"),
                tostring(player:GetAttribute("CullBudget") or "?"), tostring(player:GetAttribute("CullRadius") or "?"), game:GetService("Stats").InstanceCount)
        end
        task.wait(.5)
    end
end)

local function setOpen(open: boolean)
    panel.Visible = open
    player:SetAttribute("AdminPanelRight", if open then panel.AbsolutePosition.X + panel.AbsoluteSize.X else 0) -- toasts read this and slide clear
    toggle.BackgroundColor3 = if open then C.gold else C.purple
end
toggle.Activated:Connect(function() setOpen(not panel.Visible) end)
-- BD-304: the Admin button sat on top of every menu's corner. Hide it while a game menu is open (unless the panel itself is open).
-- BD-1130: MenuWatch sees the Fusion menu too. It is a ScreenGui made on first use, so the old one-time look-up (30 s wait, which also held the scrim
-- hook back) never hid the button for it (docs/205 picture 440).
do
    local watch: any = nil
    local function sync() toggle.Visible = panel.Visible or not (watch ~= nil and watch.anyOpen()) end
    watch = require(script.Parent:WaitForChild("MenuWatch")).watch(player:WaitForChild("PlayerGui"), sync)
    panel:GetPropertyChangedSignal("Visible"):Connect(sync)
    sync()
end
UserInputService.InputBegan:Connect(function(input, processed)
    if not processed and input.KeyCode == Enum.KeyCode.F2 then setOpen(not panel.Visible) end
end)
player:GetAttributeChangedSignal("IsAdmin"):Connect(function()
    if player:GetAttribute("IsAdmin") ~= true then player:SetAttribute("AdminPanelRight", 0) gui:Destroy() end
end)
