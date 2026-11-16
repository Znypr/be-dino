--!strict
-- BD-1233 (docs/242 gap 18): the Gifts button with the code box and the group gift chest. ONLY while Config.CodesEnabled is on (playtest profile):
-- otherwise this script returns on its first lines. The client sends WORDS only (what the player typed, or "open the chest") through the
-- CodeAction remote; the SERVER (CodeService) checks the code table, the group and the one-use token and answers in kid words, shown here.
-- Style: a cream panel with an ink outline (style tile R1), chunky tags (Chip.apply), FredokaOne, text at least 14 px, buttons at least 44 px.
-- Placement: the button sits on the right edge, under the top bar, and hides while another menu window is open.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config")) :: any
if Config.CodesEnabled ~= true then return end

local Players = game:GetService("Players")
local Chip = require(Shared:WaitForChild("ChipStyle"))
local Kit = require(Shared:WaitForChild("ToyboxKit")) :: any
local Theme = require(Shared:WaitForChild("UITheme")) :: any
local remote = (ReplicatedStorage:WaitForChild("BeDinoRemotes", 60) :: Folder):WaitForChild("CodeAction", 60)
if not (remote and remote:IsA("RemoteFunction")) then return end

local player = Players.LocalPlayer
local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
local CREAM, INK, LINE = rgb(Kit.Tone.panel), rgb(Kit.Tone.value), rgb(Kit.Outline)
local GREEN, GOLD = Theme.Colors.accent, Theme.Colors.gold

local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder = "GiftsGui", false, 6
gui.Parent = player:WaitForChild("PlayerGui")

local function text(parent: Instance, name: string, words: string, size: number, color: Color3): TextLabel
    local label = Instance.new("TextLabel")
    label.Name, label.BackgroundTransparency, label.Text, label.Font = name, 1, words, Enum.Font.FredokaOne
    label.TextSize, label.TextColor3, label.TextWrapped = size, color, true
    label.Parent = parent
    return label
end

local function button(parent: Instance, name: string, words: string, fill: Color3, size: UDim2, position: UDim2): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Size, b.Position, b.Text, b.AutoButtonColor = name, size, position, words, true
    b.Font, b.TextSize, b.TextColor3 = Enum.Font.FredokaOne, 20, Color3.new(1, 1, 1)
    b.TextStrokeTransparency, b.TextStrokeColor3 = 0, Theme.Colors.outline
    Chip.apply(b, fill)
    b.Parent = parent
    return b
end

-- The Gifts button: right edge, under the crystals plate and the friend chip slot (44 px target).
local open = button(gui, "GiftsButton", "Codes", GOLD, UDim2.fromOffset(110, 44), UDim2.new(1, -128, 0, 162)) -- under the crystals plate and the friend chip

-- The panel: centred, cream with an ink outline.
local panel = Instance.new("Frame")
panel.Name, panel.AnchorPoint, panel.Position, panel.Size = "GiftsPanel", Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromOffset(360, 330)
panel.BackgroundColor3, panel.Visible = CREAM, false
Chip.apply(panel, CREAM, LINE)
panel.Parent = gui
local title = text(panel, "Title", "Gifts", 28, INK)
title.Size, title.Position = UDim2.new(1, -60, 0, 40), UDim2.fromOffset(16, 10)
title.TextXAlignment = Enum.TextXAlignment.Left
local close = button(panel, "Close", "X", Theme.Colors.red, UDim2.fromOffset(44, 44), UDim2.new(1, -54, 0, 8))

local codeTitle = text(panel, "CodeTitle", "Got a code?", 20, INK)
codeTitle.Size, codeTitle.Position = UDim2.new(1, -32, 0, 26), UDim2.fromOffset(16, 58)
codeTitle.TextXAlignment = Enum.TextXAlignment.Left
local box = Instance.new("TextBox")
box.Name, box.Size, box.Position = "CodeBox", UDim2.new(1, -150, 0, 44), UDim2.fromOffset(16, 88)
box.Font, box.TextSize, box.Text, box.PlaceholderText, box.ClearTextOnFocus = Enum.Font.FredokaOne, 20, "", "Type it here", false
box.TextColor3, box.PlaceholderColor3, box.BackgroundColor3 = INK, Color3.fromRGB(150, 140, 120), Color3.new(1, 1, 1)
Chip.apply(box, Color3.new(1, 1, 1), LINE)
box.Parent = panel
local redeem = button(panel, "Redeem", "GO", GREEN, UDim2.fromOffset(110, 44), UDim2.new(1, -126, 0, 88))

local groupTitle = text(panel, "GroupTitle", "Group gift", 20, INK)
groupTitle.Size, groupTitle.Position = UDim2.new(1, -32, 0, 26), UDim2.fromOffset(16, 150)
groupTitle.TextXAlignment = Enum.TextXAlignment.Left
local groupLine = text(panel, "GroupLine", "", 16, INK)
groupLine.Size, groupLine.Position = UDim2.new(1, -32, 0, 40), UDim2.fromOffset(16, 176)
groupLine.TextXAlignment = Enum.TextXAlignment.Left
local chest = button(panel, "OpenChest", "Open", GOLD, UDim2.fromOffset(140, 44), UDim2.fromOffset(16, 220))

local answer = text(panel, "Answer", "", 18, INK)
answer.Size, answer.Position = UDim2.new(1, -32, 0, 44), UDim2.new(0, 16, 1, -56)

local busy = false
local function ask(request: any): any
    if busy then return nil end
    busy = true
    local ok, result = pcall(function() return (remote :: RemoteFunction):InvokeServer(request) end)
    busy = false
    return if ok and type(result) == "table" then result else nil
end

local function show(result: any)
    if result == nil then answer.Text = "Please wait a moment." return end
    answer.Text = if type(result.text) == "string" and #result.text <= 60 then result.text else ""
    answer.TextColor3 = if result.ok == true then Color3.fromRGB(46, 140, 40) else INK
end

local function loadInfo()
    local info = ask({action = "info"})
    local hasGroup = info ~= nil and info.group == true
    groupTitle.Visible, groupLine.Visible, chest.Visible = hasGroup, hasGroup, hasGroup
    panel.Size = UDim2.fromOffset(360, if hasGroup then 330 else 200) -- no group id yet: a short panel without the empty chest space
    if hasGroup and info then
        local n = if type(info.groupCrystals) == "number" then info.groupCrystals else 0
        groupLine.Text = if info.groupDone == true then "You opened it already!" else string.format("Join our group, then open it for %d crystals!", n)
        chest.Text = if info.groupDone == true then "Opened" else "Open"
    end
end

open.Activated:Connect(function()
    panel.Visible = not panel.Visible
    answer.Text = ""
    if panel.Visible then loadInfo() end
end)
close.Activated:Connect(function() panel.Visible = false end)
local function tryCode()
    if box.Text == "" then return end
    show(ask({action = "code", text = string.sub(box.Text, 1, 64)}))
end
redeem.Activated:Connect(tryCode)
box.FocusLost:Connect(function(enter: boolean) if enter then tryCode() end end)
chest.Activated:Connect(function()
    show(ask({action = "group"}))
    loadInfo()
end)

-- Hide the button while another menu window is open or a run is going (the panel stays a calm, between-runs thing).
local ui: Instance? = nil
local function refresh()
    local u = ui
    local screen = if u then u:GetAttribute("Screen") else nil
    local character = player.Character
    local running = character ~= nil and character:GetAttribute("RunState") == "Active"
    open.Visible = (screen == nil or screen == "") and not running
    if not open.Visible then panel.Visible = false end
end
local function watchCharacter(character: Model)
    character:GetAttributeChangedSignal("RunState"):Connect(refresh)
    refresh()
end
if player.Character then watchCharacter(player.Character) end
player.CharacterAdded:Connect(watchCharacter)
task.spawn(function()
    ui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI", 60)
    local u = ui
    if u then u:GetAttributeChangedSignal("Screen"):Connect(refresh) end
    refresh()
end)
