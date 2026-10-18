--!strict
-- BD-1039 / docs/186 s7: the card grid of the Patterns and Colours tabs. Draws what Shared/PatternColourIndex.cards returns.
-- One scrolling grid, three cards across (264 px wide, like the Dino Index cards), nothing hover-only: name, tier word, boost pips and
-- the "Found on" line are always on the card. Static (no tweens), so Reduce Motion needs no special case.
--   found      dark card, tier-colour border, the pattern picture (or a plain tinted tile) / the colour swatch in its real rgb, name,
--              tier word, boost pips, "Found on: Compy, Raptor +1".
--   not found  darker card, the SAME tier colour dimmed (so how rare it is stays visible), a grey tile with a question mark, "???",
--              the same pips (so a player sees what is worth hunting), "Not found yet".
-- Pattern pictures: the final pattern icons do not exist yet (docs/catalog Missing list, resources/ui/v2/patterns/<id>-v1.png). Until
-- AssetSlots.Images.pattern_<id> is bound the card shows a plain tinted tile. PLACEHOLDER (docs/72): the tile is not art, it never counts as done.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local AssetSlots = require(Shared:WaitForChild("AssetSlots"))
local Index = require(Shared:WaitForChild("PatternColourIndex"))

local Cards = {}
Cards.CardW, Cards.CardH, Cards.Gap, Cards.Columns = 264, 176, 12, 3
Cards.Pips = 5

local C = Theme.Colors
local DARK = Color3.fromRGB(46, 46, 58) -- a card not found yet
local GREY = Color3.fromRGB(86, 88, 100) -- its tile
local PIP_OFF = Color3.fromRGB(70, 70, 84)

function Cards.label(parent: GuiObject, text: string, x: number, y: number, w: number, h: number, size: number, color: Color3?, align: Enum.TextXAlignment?): TextLabel
    local t = Instance.new("TextLabel")
    t.BackgroundTransparency, t.Position, t.Size = 1, UDim2.fromOffset(x, y), UDim2.fromOffset(w, h)
    t.Font, t.TextSize, t.Text, t.TextColor3 = Enum.Font.FredokaOne, size, text, color or C.text
    t.TextWrapped, t.TextXAlignment, t.ZIndex, t.Parent = true, align or Enum.TextXAlignment.Left, parent.ZIndex + 1, parent
    Theme.TextStyle.outlined(t, "card") -- BD-1119
    return t
end
local label = Cards.label

local function rgb3(c: Color3): {number} return {c.R, c.G, c.B} end
local function fromRgb3(t: {number}): Color3 return Color3.new(t[1], t[2], t[3]) end

-- The tier colour of a card (Theme.RarityColors, one colour everywhere); a card not found yet gets it pulled toward the dark card.
function Cards.borderColor(card: any): Color3
    local base = (Theme.RarityColors :: any)[card.rarity] or (Theme.RarityColors :: any)[1]
    if card.found then return base end
    return fromRgb3(Index.dim(rgb3(base), rgb3(DARK)))
end

-- size (design px) defaults to the card's 84; the detail popup (PatternColourDetail) draws the same tile bigger.
function Cards.tile(parent: GuiObject, kind: string, card: any, size: number?, x: number?, y: number?): Frame
    local px = size or 84
    local t = Instance.new("Frame")
    t.Name, t.Position, t.Size, t.ZIndex, t.Parent = "Tile", UDim2.fromOffset(x or 10, y or 46), UDim2.fromOffset(px, px), parent.ZIndex + 1, parent
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(if kind == "colours" then 0.5 else 0.18, 0)
    corner.Parent = t
    local edge = Instance.new("UIStroke")
    edge.Color, edge.Thickness, edge.Parent = C.outline, 3, t
    if not card.found then
        t.BackgroundColor3 = GREY
        local q = label(t, "?", 0, 0, px, px, math.floor(px * 48 / 84), Color3.fromRGB(205, 208, 220), Enum.TextXAlignment.Center)
        q.Name = "Question"
        -- a pattern picture, when bound, shows as a dark silhouette on the grey tile
        local id = if kind == "patterns" then AssetSlots.image("pattern_" .. card.id) else nil
        if id then
            local img = Instance.new("ImageLabel")
            img.Name, img.BackgroundTransparency, img.Image, img.ImageColor3, img.ImageTransparency = "Silhouette", 1, id, Color3.fromRGB(40, 40, 50), 0.35
            img.Size, img.ScaleType, img.ZIndex, img.Parent = UDim2.fromScale(1, 1), Enum.ScaleType.Fit, t.ZIndex + 1, t
            q.Visible = false
        end
        return t
    end
    if kind == "colours" then
        local c = card.rgb
        t.BackgroundColor3 = if type(c) == "table" then Color3.fromRGB(c[1], c[2], c[3]) else GREY -- the REAL colour
        return t
    end
    local id = AssetSlots.image("pattern_" .. card.id)
    if id then
        t.BackgroundColor3 = Color3.fromRGB(245, 245, 248)
        local img = Instance.new("ImageLabel")
        img.Name, img.BackgroundTransparency, img.Image = "PatternPicture", 1, id
        img.Size, img.ScaleType, img.ZIndex, img.Parent = UDim2.fromScale(1, 1), Enum.ScaleType.Fit, t.ZIndex + 1, t
    else
        t.Name = "PlaceholderTile" -- PLACEHOLDER (docs/72): a plain tinted tile until resources/ui/v2/patterns/<id>-v1.png is delivered
        t.BackgroundColor3 = Cards.borderColor(card):Lerp(C.card, 0.4)
    end
    return t
end

function Cards.pips(parent: GuiObject, card: any, x: number, y: number)
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.Position, row.Size, row.ZIndex, row.Parent = "Pips", 1, UDim2.fromOffset(x, y), UDim2.fromOffset(148, 20), parent.ZIndex + 1, parent
    for i = 1, Cards.Pips do
        local pip = Instance.new("Frame")
        local on = i <= card.pips
        pip.Name, pip.Position, pip.Size, pip.ZIndex, pip.Parent = if on then "PipOn" else "PipOff", UDim2.fromOffset((i - 1) * 25, 0), UDim2.fromOffset(20, 20), row.ZIndex + 1, row
        pip.BackgroundColor3 = if on then (if card.found then C.gold else C.gold:Lerp(DARK, 0.45)) else PIP_OFF
        local corner = Instance.new("UICorner")
        corner.CornerRadius = UDim.new(0.5, 0)
        corner.Parent = pip
        local edge = Instance.new("UIStroke")
        edge.Color, edge.Thickness, edge.Parent = C.outline, 2, pip
    end
end

-- One card at grid position (x, y) inside `parent`.
function Cards.card(parent: GuiObject, kind: string, card: any, x: number, y: number, onPick: ((any) -> ())?): Frame
    local f = Instance.new("Frame")
    f.Name, f.Position, f.Size, f.ZIndex, f.Parent = "Card_" .. card.id, UDim2.fromOffset(x, y), UDim2.fromOffset(Cards.CardW, Cards.CardH), parent.ZIndex + 1, parent
    f.BackgroundColor3 = if card.found then C.card else DARK
    Theme.decorate(f, 8)
    local stroke = f:FindFirstChildOfClass("UIStroke")
    if stroke then stroke.Color, stroke.Thickness = Cards.borderColor(card), 5 end
    f:SetAttribute("Found", card.found)
    f:SetAttribute("Tier", card.rarity)
    label(f, if card.found then card.name else "???", 10, 8, 244, 34, 26, nil, Enum.TextXAlignment.Left).Name = "Name"
    Cards.tile(f, kind, card)
    local tierColor = if card.found then Cards.borderColor(card) else Cards.borderColor(card):Lerp(C.text, 0.25)
    local tier = label(f, card.rarity, 104, 46, 150, 26, 22, tierColor)
    tier.Name = "Tier"
    Cards.pips(f, card, 106, 78)
    label(f, card.boostText, 104, 102, 152, 24, 18, if card.found then C.text else Color3.fromRGB(190, 192, 205)).Name = "Boost"
    label(f, card.line, 10, 134, 244, 38, 18, if card.found then C.text else Color3.fromRGB(190, 192, 205)).Name = "Line"
    if onPick then
        -- BD-1065: a tap on the card opens its small detail (PatternColourDetail). This button covers ONE card, never the screen, the header or X;
        -- a drag on the grid still scrolls it (Activated fires on a tap only).
        local hit = Instance.new("TextButton")
        hit.Name, hit.Text, hit.AutoButtonColor, hit.BackgroundTransparency = "CardHit", "", false, 1
        hit.Size, hit.ZIndex, hit.Parent = UDim2.fromScale(1, 1), f.ZIndex + 8, f
        hit.Activated:Connect(function() onPick(card) end)
    end
    return f
end

-- Fills `parent` (the tab body) with the header line and the scrolling grid. kind = "patterns" | "colours"; cards = Index.cards(...);
-- headerText = Index.header(...).text; hint = one short line on the right; height = the room under the header line (design px).
-- onPick (optional, BD-1065) = called with the card when it is tapped.
function Cards.build(parent: GuiObject, kind: string, cards: {any}, headerText: string, hint: string, height: number, onPick: ((any) -> ())?): ScrollingFrame
    local top = label(parent, headerText, 0, 0, 380, 40, 30, C.text, Enum.TextXAlignment.Left)
    top.Name = "IndexHeader"
    local sub = label(parent, hint, 392, 6, 432, 30, 20, C.gold, Enum.TextXAlignment.Right)
    sub.Name = "IndexHint"
    local grid = Instance.new("ScrollingFrame")
    grid.Name, grid.BackgroundTransparency, grid.BorderSizePixel, grid.ScrollBarThickness = "IndexGrid", 1, 0, 8
    grid.Position, grid.Size, grid.ZIndex, grid.Parent = UDim2.fromOffset(0, 46), UDim2.fromOffset(824, height), parent.ZIndex + 1, parent
    grid.ScrollingDirection = Enum.ScrollingDirection.Y
    local rows = math.max(1, math.ceil(#cards / Cards.Columns))
    grid.CanvasSize = UDim2.fromOffset(0, rows * (Cards.CardH + Cards.Gap))
    for i, card in cards do
        local col, row = (i - 1) % Cards.Columns, math.floor((i - 1) / Cards.Columns)
        Cards.card(grid, kind, card, col * (Cards.CardW + Cards.Gap), row * (Cards.CardH + Cards.Gap), onPick)
    end
    return grid
end

return Cards
