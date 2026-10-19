--!strict
-- BD-427 (docs/114 s1.1): small Goals panel under the top-right goal line, shown in the hub/sanctuary (hidden during a run).
-- Three short lines: collect dinos, perfect a favourite, play new dinos, each with a progress bar and a next step. Uses
-- existing UI parts only (Theme.decorate panels and bars, no new art, no asset ids). Tap the header to fold it (a phone
-- keeps the screen clear); it starts folded. BD-1074 (owner 2026-10-18, LEAD decision): it stays fold-only, no tap-outside close (it is a
-- corner HUD card, not a modal: a catcher over the screen would eat run and hub taps). Rules in Shared/GoalsRules (tools/verify_goals.py). Heartbeat touches it ~2x a second.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("GoalsRules"))
local Theme = require(Shared:WaitForChild("UITheme"))
local PhoneScale = require(Shared:WaitForChild("PhoneScale"))
local Stack = require(Shared:WaitForChild("HudPanelStack")) -- BD-1095: one of Goals / Tasks open at a time, the other hides if it is in the way

local Panel = {}
local state = {dinos = nil :: any, species = {found = 0, owned = 0, total = 0} :: any, dirty = true, width = 260}

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
        line.BackgroundTransparency, line.Position, line.Size, line.ZIndex, line.Parent = 1, UDim2.fromOffset(8, y), UDim2.fromOffset(236, 22), root.ZIndex + 1, root
        -- BD-1074: a long line ("FAVOURITE: Gold ready: fuse Compy", picture 264) used to run into the right edge: it shrinks to 14 px, then ends in "..."
        line.TextScaled, line.TextTruncate = true, Enum.TextTruncate.AtEnd
        local fit = Instance.new("UITextSizeConstraint")
        fit.MinTextSize, fit.MaxTextSize, fit.Parent = 14, 16, line
        Theme.TextStyle.apply(line)
        local bar = Instance.new("Frame")
        bar.Name, bar.BackgroundColor3, bar.Position, bar.Size, bar.ZIndex, bar.Parent = "Bar", C.card, UDim2.fromOffset(8, y + 23), UDim2.fromOffset(244, 8), root.ZIndex + 1, root
        Theme.decorate(bar, 3)
        local fill = Instance.new("Frame")
        fill.Name, fill.BackgroundColor3, fill.BorderSizePixel, fill.Size, fill.ZIndex, fill.Parent = "Fill", C.accent, 0, UDim2.fromScale(0, 1), bar.ZIndex + 1, bar
        Theme.decorate(fill, 3)
        local step = Instance.new("TextLabel")
        step.Name, step.Font, step.TextSize, step.TextColor3, step.TextXAlignment = "Step", Enum.Font.FredokaOne, 14, C.gold, Enum.TextXAlignment.Left
        step.BackgroundTransparency, step.Position, step.Size, step.ZIndex, step.Parent = 1, UDim2.fromOffset(8, y + 32), UDim2.fromOffset(236, 20), root.ZIndex + 1, root
        step.TextTruncate = Enum.TextTruncate.AtEnd
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
        root.Size = UDim2.fromOffset(state.width, if folded then HEADER_H else HEADER_H + 2 + #rows * 56)
        header.Text = Rules.Title .. (if folded then "  (tap)" else "")
    end
    local elapsed = 0
    header.Activated:Connect(function()
        folded = not folded
        gui:SetAttribute(Stack.Attribute, Stack.after(gui:GetAttribute(Stack.Attribute), Stack.Goals, not folded)) -- BD-1095: opening Goals folds the Tasks panel
        render()
        elapsed = 0.5 -- BD-1108: place it (under the rail when it would cover it) on the next frame, not after the half-second tick
    end)

    gui:GetAttributeChangedSignal(Stack.Attribute):Connect(function() -- BD-1095: the Tasks panel opened: fold at once, and re-place on the next frame
        if not folded and Stack.mustFold(gui:GetAttribute(Stack.Attribute), Stack.Goals) then folded = true render() end
        elapsed = 0.5
    end)
    RunService.Heartbeat:Connect(function(dt)
        elapsed += dt
        if elapsed < 0.5 then return end
        elapsed = 0
        local character = Players.LocalPlayer.Character
        local inRun = character ~= nil and character:GetAttribute("RunState") == "Active"
        if inRun or not anchor.Visible then root.Visible = false return end
        -- sit just under the goal line, right edges aligned. BD-507: the goal line is scaled down on phones (0.6), and GoalsPanel is not part
        -- of the ModalCompact floor pass, so the header would render 44 x 0.6 = 26 px; the panel takes the smallest scale at which the header
        -- tap target is >= 44 px and the text >= 14 px (1:1), growing LEFT from the goal line's right edge.
        local anchorScale = anchor:FindFirstChildOfClass("UIScale")
        local lineScale = if anchorScale then anchorScale.Scale else 1
        local s = PhoneScale.floorScale(lineScale, HEADER_H, 14)
        scale.Scale = s
        root.Position = UDim2.fromOffset(anchor.Position.X.Offset + anchor.Size.X.Offset * lineScale - 260 * s, anchor.Position.Y.Offset + 34 * lineScale)
        -- BD-531: on the phone layout TouchLayout reserves the folded header's spot (wallet width, clear of the rail and the weather column) and
        -- publishes it as GoalsRect; the panel grows to its full 260 px only while it is open.
        local reserved = gui:GetAttribute("GoalsRect")
        if typeof(reserved) == "Rect" then
            s = reserved.Height / HEADER_H
            scale.Scale = s
            state.width = if folded then reserved.Width / s else 260
            root.Position = UDim2.fromOffset(reserved.Max.X - state.width * s, reserved.Min.Y)
            root.Size = UDim2.fromOffset(state.width, root.Size.Y.Offset)
        else
            state.width = 260
        end
        -- BD-1095: publish the FOLDED rect (the Tasks panel works out the open one from it) and hide while the Tasks sheet is open over this spot.
        local right = root.Position.X.Offset + state.width * scale.Scale
        local foldedW = if typeof(reserved) == "Rect" then reserved.Width else 260 * scale.Scale
        local top = root.Position.Y.Offset
        local mine = Rect.new(right - foldedW, top, right, top + HEADER_H * scale.Scale)
        if gui:GetAttribute("GoalsFoldedRect") ~= mine then gui:SetAttribute("GoalsFoldedRect", mine) end
        -- BD-1108: the OPEN card keeps off the HUD rail (RailRect, from HudV2.layout: two buttons in a run, six at home): it opens under the rail when it would cover it.
        local openRect: Rect? = nil
        if not folded then
            local o: Stack.R = {x = right - state.width * scale.Scale, y = top, w = state.width * scale.Scale, h = root.Size.Y.Offset * scale.Scale}
            local dy = Stack.clearRail(o, Stack.fromRect(gui:GetAttribute("RailRect")), gui.AbsoluteSize.Y)
            if dy > 0 then root.Position = root.Position + UDim2.fromOffset(0, dy) end
            openRect = Rect.new(o.x, o.y + dy, o.x + o.w, o.y + dy + o.h)
        end
        if gui:GetAttribute("GoalsOpenRect") ~= openRect then gui:SetAttribute("GoalsOpenRect", openRect) end -- the Tasks panel hides if it lies under it
        root.Visible = not Stack.hidden(Stack.Goals, gui:GetAttribute(Stack.Attribute), Stack.fromRect(mine), Stack.fromRect(gui:GetAttribute("ObjectivesOpenRect")))
        if state.dirty then
            state.dirty = false
            render()
        end
    end)
    render()
end

return Panel
