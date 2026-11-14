--!strict
-- BD-1189 (docs/232): the layout helpers of the Toybox skin. Screens ask these for panels, label / value rows, buttons and empty grid slots
-- instead of placing and colouring things by hand. Flat colours only (UICorner + UIStroke, one gradient on the preview box); no texture is
-- drawn in code (docs/72). Numbers live in Shared/ToyboxKit. Required by a screen only while Theme.Toybox is on (Config.ToyboxUIEnabled).
local Kit = require(script.Parent.ToyboxKit)
local Skin = require(script.Parent.ToyboxSkin)

local Layout = {}
Layout.Kit = Kit
local OUTLINE = Color3.fromRGB(Kit.Outline[1], Kit.Outline[2], Kit.Outline[3])

-- ---- BD-1189 (docs/232): layout helpers. Screens ask these instead of placing and colouring things by hand. They draw flat colours
-- (UICorner + UIStroke, one gradient on the preview box); no texture is drawn in code (docs/72). Numbers: Shared/ToyboxKit.
local function tone(name: string): Color3
    local t = (Kit.Tone :: any)[name]
    return Color3.fromRGB(t[1], t[2], t[3])
end
Layout.tone = tone
local function frame(parent: GuiObject, name: string, size: UDim2, position: UDim2, fill: Color3, corner: number, stroke: number?): Frame
    local f = Instance.new("Frame")
    f.Name, f.Size, f.Position, f.BackgroundColor3, f.BorderSizePixel = name, size, position, fill, 0
    f.ZIndex = parent.ZIndex
    local round = Instance.new("UICorner")
    round.CornerRadius, round.Parent = UDim.new(0, corner), f
    if stroke then
        local line = Instance.new("UIStroke")
        line.Color, line.Thickness, line.Parent = OUTLINE, stroke, f
    end
    f.Parent = parent
    return f
end
-- A cream panel: 14 px corners, 3 px dark outline. Content goes PanelPad (12) inside it.
function Layout.panel(parent: GuiObject, name: string, size: UDim2, position: UDim2): Frame
    return frame(parent, name, size, position, tone("panel"), Kit.PanelCorner, Kit.PanelStroke)
end
-- BD-1195 / BD-1194: a card on a panel: the lighter cream (or a soft tint such as "ready" / "busy"), 12 px corners, 2 px dark outline.
function Layout.card(parent: GuiObject, name: string, size: UDim2, position: UDim2, tint: string?): Frame
    return frame(parent, name, size, position, tone(tint or "card"), Kit.CardCorner, Kit.CardStroke)
end
-- A small count chip ("Nests 0/5"): warm tone, 8 px corners, 2 px outline, dark ink (no outline on the text). Returns the chip and its label.
function Layout.chip(parent: GuiObject, text: string, size: UDim2, position: UDim2): (Frame, TextLabel)
    local chip = frame(parent, "Chip", size, position, tone("previewTop"), Kit.ChipCorner, Kit.CardStroke)
    local label = Layout.text(chip, text, UDim2.new(1, -8, 1, 0), UDim2.fromOffset(4, 0), Kit.Type.body, "value", Enum.TextXAlignment.Center)
    return chip, label
end
-- The preview box of a panel: warm gradient, 10 px corners, clips the 3D view.
function Layout.preview(parent: GuiObject, size: UDim2, position: UDim2): Frame
    local box = frame(parent, "Preview", size, position, Color3.new(1, 1, 1), Kit.PreviewCorner, nil)
    local gradient = Instance.new("UIGradient")
    local top, bottom = (Kit.Tone :: any).previewTop, (Kit.Tone :: any).previewBottom
    gradient.Rotation = 90
    gradient.Color = ColorSequence.new(Color3.fromRGB(top[1], top[2], top[3]), Color3.fromRGB(bottom[1], bottom[2], bottom[3]))
    gradient.Parent = box
    box.ClipsDescendants = true
    return box
end
-- Dark body text on a cream surface: no outline (outline only on titles and button words). Works on a label the old helpers built too.
function Layout.ink(label: TextLabel, which: string?): TextLabel
    label.TextColor3, label.TextStrokeTransparency = tone(which or "value"), 1
    for _, child in label:GetChildren() do
        if child:IsA("UIStroke") then child.Transparency = 1 end
    end
    return label
end
-- BD-1205: a cream chip button (a tab, a choice): `selected` = amber. The word is dark ink on its OWN label with no outline, so the skin's outlined
-- white button word can never draw over the cream; the button itself keeps the text (accessibility, tests) but is transparent.
Layout.Amber = Color3.fromRGB(255, 215, 106)
function Layout.tabChip(parent: GuiObject, name: string, text: string, size: UDim2, position: UDim2, selected: boolean, textSize: number, callback: () -> ()): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.AutoButtonColor, b.BorderSizePixel = name, text, false, 0
    b.BackgroundColor3 = if selected then Layout.Amber else tone("panel")
    b.Position, b.Size, b.ZIndex = position, size, parent.ZIndex + 1
    b.Font, b.TextSize, b.TextColor3 = Enum.Font.FredokaOne, Kit.textSize(textSize), tone("value")
    b.TextTransparency, b.TextStrokeTransparency = 1, 1
    local round = Instance.new("UICorner")
    round.CornerRadius, round.Parent = UDim.new(0, Kit.CardCorner), b
    local line = Instance.new("UIStroke")
    line.Name, line.Color, line.Thickness, line.Parent = "CreamOutline", OUTLINE, Kit.PanelStroke, b
    line.ApplyStrokeMode = Enum.ApplyStrokeMode.Border -- Contextual on a TextButton outlines its (hidden) TEXT: the dark halo around the chip word
    local word = Instance.new("TextLabel")
    word.Name, word.BackgroundTransparency, word.Size, word.ZIndex, word.Text = "ChipWord", 1, UDim2.fromScale(1, 1), b.ZIndex + 1, text
    word.Font, word.TextSize, word.TextWrapped, word.TextXAlignment = Enum.Font.FredokaOne, Kit.textSize(textSize), false, Enum.TextXAlignment.Center
    Layout.ink(word)
    word.Parent = b
    word.ChildAdded:Connect(function(child) if child:IsA("UIStroke") then child.Transparency = 1 end end)
    b.Activated:Connect(callback)
    b.Parent = parent
    return b
end
-- A text label on a panel: type scale size (28 / 20 / 16 / 14), never under 14, shrinks to 14 rather than clip.
function Layout.text(parent: GuiObject, text: string, size: UDim2, position: UDim2, textSize: number, which: string?, alignX: Enum.TextXAlignment?): TextLabel
    local label = Instance.new("TextLabel")
    label.BackgroundTransparency, label.Size, label.Position, label.Text = 1, size, position, text
    label.Font, label.TextSize, label.TextScaled, label.TextWrapped = Enum.Font.FredokaOne, Kit.textSize(textSize), true, false
    label.TextXAlignment, label.ZIndex = alignX or Enum.TextXAlignment.Left, parent.ZIndex + 1
    local limit = Instance.new("UITextSizeConstraint")
    limit.MinTextSize, limit.MaxTextSize, limit.Parent = Kit.MinText, Kit.textSize(textSize), label
    Layout.ink(label, which)
    label.Parent = parent
    return label
end
-- One label / value row of a panel: label left in the muted tone, value right in the dark tone, Kit.RowH high.
function Layout.row(parent: GuiObject, index: number, width: number, label: string, value: string): Frame
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.BorderSizePixel = "Row_" .. label, 1, 0
    row.Size, row.Position, row.ZIndex = UDim2.fromOffset(width, Kit.RowH), UDim2.fromOffset(0, (index - 1) * Kit.RowH), parent.ZIndex + 1
    row.Parent = parent
    local labelWidth = math.floor(width * 0.3)
    Layout.text(row, label, UDim2.fromOffset(labelWidth, Kit.RowH), UDim2.new(), Kit.Type.body, "label").Name = "Label"
    local text = Layout.text(row, value, UDim2.fromOffset(width - labelWidth - Kit.Gutter, Kit.RowH), UDim2.fromOffset(labelWidth + Kit.Gutter, 0), Kit.Type.body, "value", Enum.TextXAlignment.Right)
    text.Name = "Value"
    return row
end
-- A button of the kit's height (48, or 40 small; `height` = what the screen worked out from Kit.buttonHeights). Colour = the gloss picture
-- (green = the one primary button of a screen; grey for everything else). Without bound pictures it is a flat rounded button.
function Layout.actionButton(parent: GuiObject, text: string, size: UDim2, position: UDim2, color: Color3, small: boolean, callback: () -> ()): TextButton
    local b = Instance.new("TextButton")
    b.Size, b.Position, b.BackgroundColor3, b.AutoButtonColor, b.ZIndex = size, position, color, false, parent.ZIndex + 1
    b.Font, b.Text, b.TextSize, b.TextColor3 = Enum.Font.FredokaOne, text, if small then Kit.Type.body else Kit.Type.heading, Color3.new(1, 1, 1)
    local limit = Instance.new("UITextSizeConstraint")
    limit.MinTextSize, limit.MaxTextSize, limit.Parent = Kit.MinText, b.TextSize, b
    b.TextScaled = true
    if Skin.ready("button") then
        Skin.button(b, nil)
        b.MouseButton1Down:Connect(function() local face = b:FindFirstChild("ToyboxFace") if face and face:IsA("ImageLabel") then face.ImageTransparency = 0.15 end end)
        for _, event in {b.MouseButton1Up, b.MouseLeave} do
            event:Connect(function() local face = b:FindFirstChild("ToyboxFace") if face and face:IsA("ImageLabel") then face.ImageTransparency = 0 end end)
        end
    else
        local round = Instance.new("UICorner")
        round.CornerRadius, round.Parent = UDim.new(0, 10), b
        local line = Instance.new("UIStroke")
        line.Color, line.Thickness, line.ApplyStrokeMode, line.Parent = OUTLINE, Kit.PanelStroke, Enum.ApplyStrokeMode.Border, b
    end
    b.Activated:Connect(callback)
    b.Parent = parent
    return b
end
-- An empty grid slot: a card-sized box drawn as dashes (no dashed stroke exists, so short bars round the edge), so the grid looks finished.
function Layout.emptySlot(parent: GuiObject, width: number, height: number, order: number): Frame
    local slot = Instance.new("Frame")
    slot.Name, slot.BackgroundTransparency, slot.LayoutOrder, slot.BorderSizePixel = "EmptySlot", 1, order, 0
    slot.ZIndex = parent.ZIndex + 1
    local t, dash, gap = Kit.DashThickness, Kit.DashLength, Kit.DashGap
    local colour = tone("slot")
    local function bar(x: number, y: number, w: number, h: number)
        local f = Instance.new("Frame")
        f.BackgroundColor3, f.BorderSizePixel, f.Position, f.Size, f.ZIndex = colour, 0, UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), slot.ZIndex
        f.Parent = slot
    end
    local x = 0
    while x < width do local w = math.min(dash, width - x) bar(x, 0, w, t) bar(x, height - t, w, t) x += dash + gap end
    local y = 0
    while y < height do local h = math.min(dash, height - y) bar(0, y, t, h) bar(width - t, y, t, h) y += dash + gap end
    slot.Parent = parent
    return slot
end

return Layout
