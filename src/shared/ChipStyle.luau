--!strict
-- BD-1070 (docs/192 section 4): ONE chip style for the whole game, the "chunky tag".
-- A chip is a rounded RECTANGLE (corner about 9 px, never a full-round pill), a 3 px dark outline, a flat palette fill, FredokaOne text with a
-- 2 px dark stroke, text at least 14 px, at least 28 px high (44 px when it can be tapped). Fill colours come from the shared tables only:
-- rarity from Theme.RarityColors, egg colours from ProgressionConfig.EggColors (exact rgb), conditions from the condition palette. A colour
-- dot is a small rounded SQUARE with the same outline and the exact palette colour (Chip.swatch).
-- Spec and maths are pure (offline-tested by tools/verify_hatch_polish.py); only new / apply / swatch touch Instances.
local Theme = require(script.Parent.UITheme)

local Chip = {}
Chip.Spec = {radius = 9, swatchRadius = 6, outline = 3, textStroke = 2, minText = 14, minHeight = 28, tapHeight = 44}

-- Corner radius in pixels. Always an offset, so a chip can never become a full-round pill by scale.
function Chip.radius(): UDim return UDim.new(0, Chip.Spec.radius) end
function Chip.swatchRadius(): UDim return UDim.new(0, Chip.Spec.swatchRadius) end
-- Is this chip box big enough? tappable chips need the 44 px target (docs/72).
function Chip.heightOk(height: number, tappable: boolean?): boolean
    return height >= (if tappable then Chip.Spec.tapHeight else Chip.Spec.minHeight)
end
-- Text size that fits a chip of this height: one line, never under 14 px (docs/114 s4.4).
function Chip.textSize(height: number): number
    return math.max(Chip.Spec.minText, math.floor(height * 0.6))
end
-- The exact palette colour of a swatch: an {r, g, b} 0..255 triple from the shared tables, never a blend or a tint.
function Chip.color(rgb: {number}): Color3
    return Color3.fromRGB(rgb[1], rgb[2], rgb[3])
end

-- Round the corners and outline a frame in the chunky tag style. Returns the corner and the outline.
function Chip.apply(frame: GuiObject, fill: Color3, outline: Color3?): (UICorner, UIStroke)
    frame.BackgroundColor3, frame.BackgroundTransparency, frame.BorderSizePixel = fill, 0, 0
    local corner = frame:FindFirstChildOfClass("UICorner") or Instance.new("UICorner")
    corner.CornerRadius = Chip.radius()
    corner.Parent = frame
    local stroke = frame:FindFirstChildOfClass("UIStroke") or Instance.new("UIStroke")
    stroke.Thickness, stroke.Color, stroke.ApplyStrokeMode = Chip.Spec.outline, outline or Theme.Colors.outline, Enum.ApplyStrokeMode.Border
    stroke.Parent = frame
    return corner, stroke
end

-- A chunky tag with one line of text. opts: name, fill, size (UDim2), position (UDim2, optional), anchor (Vector2, optional), z, text.
-- Returns the frame, its label and its outline.
function Chip.new(parent: GuiObject, opts: {name: string, fill: Color3, size: UDim2, position: UDim2?, anchor: Vector2?, z: number?, text: string?, textInset: number?}): (Frame, TextLabel, UIStroke)
    local frame = Instance.new("Frame")
    frame.Name, frame.Size, frame.ZIndex = opts.name, opts.size, opts.z or 1
    if opts.position then frame.Position = opts.position end
    if opts.anchor then frame.AnchorPoint = opts.anchor end
    local _, stroke = Chip.apply(frame, opts.fill, nil)
    frame.Parent = parent
    local inset = opts.textInset or 6
    local label = Instance.new("TextLabel")
    label.Name, label.BackgroundTransparency, label.Position, label.Size = "Text", 1, UDim2.fromOffset(inset, 2), UDim2.new(1, -2 * inset, 1, -4)
    label.Font, label.TextColor3, label.Text = Enum.Font.FredokaOne, Color3.new(1, 1, 1), opts.text or ""
    label.TextScaled, label.TextWrapped, label.TextStrokeTransparency, label.TextStrokeColor3 = true, false, 0, Theme.Colors.outline
    label.ZIndex, label.Parent = (opts.z or 1) + 1, frame
    local limit = Instance.new("UITextSizeConstraint")
    limit.MinTextSize, limit.MaxTextSize, limit.Parent = Chip.Spec.minText, 30, label
    return frame, label, stroke
end

-- A colour dot: a small rounded square, same outline, the exact palette colour. rgb = {r, g, b} 0..255 from EggColors.
function Chip.swatch(parent: GuiObject, size: number, rgb: {number}?, z: number?): Frame
    local frame = Instance.new("Frame")
    frame.Name, frame.AnchorPoint, frame.Size, frame.ZIndex = "Swatch", Vector2.new(.5, .5), UDim2.fromOffset(size, size), z or 1
    frame.BackgroundColor3, frame.BorderSizePixel = if rgb then Chip.color(rgb) else Color3.new(1, 1, 1), 0
    local corner = Instance.new("UICorner") corner.CornerRadius = Chip.swatchRadius() corner.Parent = frame
    local stroke = Instance.new("UIStroke") stroke.Thickness, stroke.Color, stroke.ApplyStrokeMode, stroke.Parent = Chip.Spec.outline, Theme.Colors.outline, Enum.ApplyStrokeMode.Border, frame
    frame.Parent = parent
    return frame
end

return Chip
