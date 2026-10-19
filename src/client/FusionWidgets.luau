--!strict
-- Small relative-layout UI helpers for the BD-065 Fusion Menu and BD-062 Dino Details.
-- Matches the Bootstrap visual style (FredokaOne, outlined text, Theme.decorate) but
-- sizes with Scale/Offset + text constraints instead of one fixed 860x520 canvas, so
-- the same screens fit a phone in landscape. Touch targets use W.Touch (>= 44 px).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local ProgressionConfig = require(Shared.ProgressionConfig)
local C = Theme.Colors

local W = {}
W.Colors = C
W.Touch = 44
W.MinText = 14 -- BD-083 / docs/72: no text under 14 px, even when a label is squeezed

local function textConstraint(t: TextLabel | TextButton, maxSize: number)
    t.TextScaled = true
    local limit = Instance.new("UITextSizeConstraint")
    limit.MaxTextSize, limit.MinTextSize, limit.Parent = maxSize, W.MinText, t
end

function W.label(parent: Instance, text: string, size: UDim2, position: UDim2, maxText: number?, color: Color3?, alignLeft: boolean?): TextLabel
    local t = Instance.new("TextLabel")
    t.BackgroundTransparency, t.Size, t.Position = 1, size, position
    t.Font, t.Text, t.TextColor3 = Enum.Font.FredokaOne, text, color or C.text
    t.TextStrokeTransparency, t.TextStrokeColor3, t.TextWrapped = 0, C.outline, true
    if alignLeft then t.TextXAlignment = Enum.TextXAlignment.Left end
    textConstraint(t, maxText or 22)
    if color == C.outline then
        -- QA 2026-10-16: dark text on a light badge/tab (GOLD, NEW GOLD, slot numbers) turned into a blob with a dark outline.
        t.TextStrokeTransparency = 1
    else
        Theme.TextStyle.outlined(t, "card") -- BD-390 / BD-1119: shared outlined style (light fill, dark stroke 2..3); the text is scaled to its box, so only the kind is recorded
    end
    t.Parent = parent
    return t
end

function W.box(parent: Instance, size: UDim2, position: UDim2, color: Color3, radius: number?): Frame
    local b = Instance.new("Frame")
    b.Size, b.Position, b.BackgroundColor3 = size, position, color
    Theme.decorate(b, radius or 5)
    b.Parent = parent
    return b
end

function W.button(parent: Instance, text: string, size: UDim2, position: UDim2, color: Color3, callback: () -> ()): TextButton
    local b = Instance.new("TextButton")
    b.Size, b.Position, b.BackgroundColor3 = size, position, color
    b.Font, b.Text, b.TextColor3 = Enum.Font.FredokaOne, text, C.text
    b.TextStrokeTransparency, b.TextStrokeColor3 = 0, C.outline
    textConstraint(b, 22)
    Theme.decorate(b, 4)
    local floor = Instance.new("UISizeConstraint") -- BD-334: never narrower or shorter than a 44 px touch target (Clear was 41 px)
    floor.MinSize, floor.Parent = Vector2.new(W.Touch, W.Touch), b
    b.Activated:Connect(callback)
    b.Parent = parent
    return b
end

function W.scroll(parent: Instance, size: UDim2, position: UDim2): ScrollingFrame
    local s = Instance.new("ScrollingFrame")
    s.Size, s.Position, s.BackgroundTransparency, s.BorderSizePixel = size, position, 1, 0
    s.ScrollBarThickness, s.ScrollingDirection = 8, Enum.ScrollingDirection.Y
    s.AutomaticCanvasSize, s.CanvasSize = Enum.AutomaticSize.Y, UDim2.new()
    s.Parent = parent
    return s
end

function W.list(parent: Instance, padding: number, horizontal: boolean?): UIListLayout
    local l = Instance.new("UIListLayout")
    l.Padding, l.SortOrder = UDim.new(0, padding), Enum.SortOrder.LayoutOrder
    if horizontal then l.FillDirection = Enum.FillDirection.Horizontal end
    l.Parent = parent
    return l
end

function W.colorOf(id: string?): Color3
    for _, row in ProgressionConfig.EggColors do
        if row.id == id then return Color3.fromRGB(row.rgb[1], row.rgb[2], row.rgb[3]) end
    end
    return C.card
end

-- Two-gene swatch: never the only signal; callers also print color names.
function W.swatch(parent: Instance, genes, size: UDim2, position: UDim2): Frame
    local frame = Instance.new("Frame")
    frame.Size, frame.Position, frame.BackgroundTransparency = size, position, 1
    frame.Parent = parent
    local blend = (genes and tonumber(genes.blend)) or 100
    local a = W.box(frame, UDim2.fromScale(math.clamp(blend / 100, .08, 1), 1), UDim2.new(), W.colorOf(genes and genes.primaryColorId), 3)
    a.Name = "Primary"
    if blend < 100 then
        local b = W.box(frame, UDim2.fromScale(1 - math.clamp(blend / 100, .08, 1), 1), UDim2.fromScale(math.clamp(blend / 100, .08, 1), 0), W.colorOf(genes and genes.secondaryColorId), 3)
        b.Name = "Secondary"
    end
    return frame
end

W.StageColors = {base = C.card, gold = C.gold, emerald = Color3.fromRGB(46, 196, 120), diamond = C.blue}

return W
