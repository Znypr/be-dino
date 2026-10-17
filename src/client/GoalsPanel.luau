--!strict
-- BD-427 (docs/114 s1.1): small Goals panel under the top-right goal line, shown in the hub/sanctuary (hidden during a run).
-- Three short lines: collect dinos, perfect a favourite, play new dinos, each with a progress bar and a next step. Uses
-- existing UI parts only (Theme.decorate panels and bars, no new art, no asset ids). Tap the header to fold it (a phone
-- keeps the screen clear); it starts folded. Rules in Shared/GoalsRules (tools/verify_goals.py). Heartbeat touches it ~2x a second.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("GoalsRules"))
local Theme = require(Shared:WaitForChild("UITheme"))

local Panel = {}
local state = {dinos = nil :: any, species = {found = 0, owned = 0, total = 0} :: any, dirty = true}

-- Bootstrap feeds data through these two calls (no new top-level locals there).
function Panel.setDinos(dinos: any) state.dinos, state.dirty = dinos, true end
function Panel.setSpecies(counts: any) state.species, state.dirty = counts, true end

local HEADER_H = 44 -- the header is a button: docs/114 s4.4 tap-target floor (the folded panel is as tall as its header)
function Panel.attach(gui: ScreenGui, anchor: GuiObject, opts: any)
    local C = Theme.Colors
    local root = Instance.new("Frame")
    root.Name, root.Size, root.BackgroundColor3, root.BackgroundTransparency, root.ZIndex = "GoalsPanel", UDim2.fromOffset(260, HEADER_H), C.panel, 0.15, 2
    Theme.decorate(root, 5)
    root.Visible, root.Parent = false, gui
    local scale = Instance.new("UIScale")
    scale.Parent = root

    local header = Instance.new("TextButton")
    header.Name, header.Text, header.Font, header.TextSize, header.TextColor3 = "Header", Rules.Title .. "  (tap)", Enum.Font.FredokaOne, 17, C.gold
    header.BackgroundTransparency, header.Size, header.ZIndex, header.Parent = 1, UDim2.new(1, 0, 0, 44), root.ZIndex + 1, root
    Theme.TextStyle.apply(header)

    local rows = {}
    local bars: {Frame} = {}
    for i, id in Rules.Order do
        local y = HEADER_H + 2 + (i - 1) * 56
        local line = Instance.new("TextLabel")
        line.Name, line.Font, line.TextSize, line.TextColor3, line.TextXAlignment = id, Enum.Font.FredokaOne, 16, C.text, Enum.TextXAlignment.Left
        line.BackgroundTransparency, line.Position, line.Size, line.ZIndex, line.Parent = 1, UDim2.fromOffset(8, y), UDim2.fromOffset(244, 22), root.ZIndex + 1, root
        Theme.TextStyle.apply(line)
        local bar = Instance.new("Frame")
        bar.Name, bar.BackgroundColor3, bar.Position, bar.Size, bar.ZIndex, bar.Parent = "Bar", C.card, UDim2.fromOffset(8, y + 23), UDim2.fromOffset(244, 8), root.ZIndex + 1, root
        Theme.decorate(bar, 3)
        local fill = Instance.new("Frame")
        fill.Name, fill.BackgroundColor3, fill.BorderSizePixel, fill.Size, fill.ZIndex, fill.Parent = "Fill", C.accent, 0, UDim2.fromScale(0, 1), bar.ZIndex + 1, bar
        Theme.decorate(fill, 3)
        local step = Instance.new("TextLabel")
        step.Name, step.Font, step.TextSize, step.TextColor3, step.TextXAlignment = "Step", Enum.Font.FredokaOne, 14, C.gold, Enum.TextXAlignment.Left
        step.BackgroundTransparency, step.Position, step.Size, step.ZIndex, step.Parent = 1, UDim2.fromOffset(8, y + 32), UDim2.fromOffset(244, 20), root.ZIndex + 1, root
        Theme.TextStyle.apply(step)
        rows[i] = {line = line, bar = bar, fill = fill, step = step}
        table.insert(bars, bar)
    end

    local folded = true
    local function render()
        local lines = Rules.lines({dinos = state.dinos, species = state.species, stages = opts.stages, speciesName = opts.speciesName, patternName = opts.patternName})
        for i, l in lines do
            local r = rows[i]
            r.line.Text = l.title .. ": " .. l.progress
            r.step.Text = "Next: " .. l.step
            r.fill.Size = UDim2.fromScale(math.clamp(l.fraction, 0, 1), 1)
            r.fill.BackgroundColor3 = if l.done then C.gold else C.accent
            r.line.Visible, r.step.Visible, r.bar.Visible = not folded, not folded, not folded
        end
        root.Size = UDim2.fromOffset(260, if folded then HEADER_H else HEADER_H + 2 + #rows * 56)
        header.Text = Rules.Title .. (if folded then "  (tap)" else "")
    end
    header.Activated:Connect(function() folded = not folded render() end)

    local elapsed = 0
    RunService.Heartbeat:Connect(function(dt)
        elapsed += dt
        if elapsed < 0.5 then return end
        elapsed = 0
        local character = Players.LocalPlayer.Character
        local inRun = character ~= nil and character:GetAttribute("RunState") == "Active"
        root.Visible = not inRun and anchor.Visible
        if not root.Visible then return end
        -- sit just under the goal line, same scale
        local anchorScale = anchor:FindFirstChildOfClass("UIScale")
        local s = if anchorScale then anchorScale.Scale else 1
        scale.Scale = s
        root.Position = UDim2.fromOffset(anchor.Position.X.Offset, anchor.Position.Y.Offset + 34 * s)
        if state.dirty then
            state.dirty = false
            render()
        end
    end)
    render()
end

return Panel
