--!strict
-- BD-390: one readable text style. Owner playtest 2026-10-16: text with only a thin black outline (floating "+0.6", menu titles) is barely
-- readable on busy grass or dark panels. Rules (docs/72): light fill + DARK stroke 2..3 px for text over the world and the HUD;
-- dark fill with no stroke on light panels. Contrast fill vs stroke is at least 4.5:1.
-- Pure colour maths (no Roblox types: offline-tested by tools/verify_text_style.py) plus apply(), the only function that touches an Instance.
local TextStyle = {}
TextStyle.MinContrast = 4.5
TextStyle.Light = {255, 255, 255}
TextStyle.Dark = {13, 15, 20}
TextStyle.MinThickness, TextStyle.MaxThickness = 2, 3
TextStyle.DarkFill = 0.05 -- relative luminance at or under which a fill counts as dark text (the outline colour itself)

local function channel(v: number): number
    local c = math.clamp(v, 0, 255) / 255
    return if c <= 0.03928 then c / 12.92 else ((c + 0.055) / 1.055) ^ 2.4
end
-- WCAG relative luminance of an 0..255 rgb triple.
function TextStyle.luminance(rgb: {number}): number
    return 0.2126 * channel(rgb[1]) + 0.7152 * channel(rgb[2]) + 0.0722 * channel(rgb[3])
end
function TextStyle.contrast(a: {number}, b: {number}): number
    local la, lb = TextStyle.luminance(a), TextStyle.luminance(b)
    return (math.max(la, lb) + 0.05) / (math.min(la, lb) + 0.05)
end
-- Stroke thickness scaled by text size: 2 for small text, 3 from about 25 px up (never thinner than 2, never a heavy 4+).
function TextStyle.thickness(textSize: number): number
    local t = if textSize == textSize then textSize else 18
    return math.clamp(math.floor(t / 10 + 0.5), TextStyle.MinThickness, TextStyle.MaxThickness)
end
-- fill / stroke pair for text over the world or HUD. The wanted fill (a tint such as the accent green is allowed) must keep 4.5:1
-- against the dark stroke, otherwise it is replaced by white. The stroke is always the dark outline colour.
function TextStyle.pair(fill: {number}?): ({number}, {number})
    local f = fill or TextStyle.Light
    if TextStyle.contrast(f, TextStyle.Dark) < TextStyle.MinContrast then f = TextStyle.Light end
    return f, TextStyle.Dark
end
-- Is this (fill, stroke, thickness) readable? stroke nil = no stroke: only fine as dark text on a light panel.
function TextStyle.readable(fill: {number}, stroke: {number}?, thickness: number?): boolean
    if stroke == nil then return TextStyle.luminance(fill) <= TextStyle.DarkFill end
    if TextStyle.contrast(fill, stroke) < TextStyle.MinContrast then return false end
    return (thickness or 0) >= TextStyle.MinThickness
end
local function rgbOf(color: Color3): {number}
    return {math.floor(color.R * 255 + 0.5), math.floor(color.G * 255 + 0.5), math.floor(color.B * 255 + 0.5)}
end
-- Applies the shared style to a TextLabel/TextButton: fill kept when readable (else white), ONE UIStroke (Contextual, round joins, thickness
-- by size) and the legacy thin TextStroke turned off so nothing double-outlines. Returns the UIStroke so fades can tween its Transparency.
function TextStyle.apply(label: TextLabel | TextButton, fill: Color3?): UIStroke
    local wanted = rgbOf(fill or label.TextColor3)
    local existingStroke = label:FindFirstChildOfClass("UIStroke")
    if TextStyle.luminance(wanted) <= TextStyle.DarkFill then -- dark text on a light badge/panel: no outline (a dark outline turns it into a blob)
        label.TextColor3, label.TextStrokeTransparency = Color3.fromRGB(wanted[1], wanted[2], wanted[3]), 1
        if existingStroke then existingStroke.Transparency = 1 end
        return existingStroke or Instance.new("UIStroke")
    end
    local f, s = TextStyle.pair(wanted)
    label.TextColor3 = Color3.fromRGB(f[1], f[2], f[3])
    label.TextStrokeTransparency = 1
    local existing = label:FindFirstChildOfClass("UIStroke")
    local stroke: UIStroke
    if existing then stroke = existing else
        stroke = Instance.new("UIStroke")
        stroke.Parent = label
    end
    stroke.ApplyStrokeMode, stroke.LineJoinMode = Enum.ApplyStrokeMode.Contextual, Enum.LineJoinMode.Round
    stroke.Color, stroke.Thickness, stroke.Transparency = Color3.fromRGB(s[1], s[2], s[3]), TextStyle.thickness(label.TextSize), 0
    return stroke
end

-- BD-1119 (docs/202 R4): ONE outlined text style with size floors by kind. White (or a readable tint) bold rounded text with a thick dark outline, short copy.
--   title = a window title or a big headline: at least 22 px, outline 3.   card = text on a card, a button or a counter: at least 16 px, outline 2..3.
--   note  = fine print (a hint, an odds line): the docs/72 floor of 14 px stays.
-- The floors are design sizes at scale 1 (a desktop window). A small window (phone, ModalCompact) scales the panel; its floor pass keeps every text at 14 px on screen
-- and PhoneScale.titleSize keeps a title at 22 px on screen. tools/verify_text_style.py measures both.
TextStyle.Floors = {title = 22, card = 16, note = 14}
TextStyle.Kinds = {"title", "card", "note"}
function TextStyle.floorOf(kind: string): number
    return TextStyle.Floors[kind] or TextStyle.Floors.note
end
-- The size to use: what was asked for, but never under the floor of its kind.
function TextStyle.fit(kind: string, size: number): number
    return math.max(size, TextStyle.floorOf(kind))
end
-- Outline thickness of a kind: titles are always 3 (thick), the rest follow the text size (2..3).
function TextStyle.thicknessFor(kind: string, size: number): number
    if kind == "title" then return TextStyle.MaxThickness end
    return TextStyle.thickness(size)
end
-- Is this text (kind, px it renders at on screen) big enough? A title needs its 22 px on every window. A card needs 16 px on a desktop window; a small
-- (compact, phone) window keeps the docs/72 floor of 14 px until the Studio re-check (compact = true). Notes are 14 px everywhere.
function TextStyle.onScreenOk(kind: string, px: number, compact: boolean): boolean
    if kind == "title" then return px >= TextStyle.Floors.title - 0.01 end
    if kind == "card" and not compact then return px >= TextStyle.Floors.card - 0.01 end
    return px >= TextStyle.Floors.note - 0.01
end
-- The standard call: font FredokaOne, size raised to the floor of its kind, the kind remembered in the TextKind attribute (the checks read it), the shared outline.
-- Returns the UIStroke. Only the size and the stroke change; position, box and wrapping stay the screen's own.
function TextStyle.outlined(label: TextLabel | TextButton, kind: string, fill: Color3?): UIStroke
    label.Font = Enum.Font.FredokaOne
    label.TextSize = TextStyle.fit(kind, label.TextSize)
    local target: Instance = label
    target:SetAttribute("TextKind", kind)
    local stroke = TextStyle.apply(label, fill)
    if kind == "title" and stroke.Parent == label then stroke.Thickness = TextStyle.thicknessFor(kind, label.TextSize) end
    return stroke
end
return TextStyle
