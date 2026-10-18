--!strict
-- BD-1065 / docs/186 s7: the small detail of one pattern or colour (a tap on a card of the Patterns or Colours tab). Behind
-- Config.PatternColourIndexEnabled like the tabs (only IndexTabs calls it). Draws what Shared/PatternColourIndex.detail returns:
--   name (??? until found), tier word in its tier colour, boost pips and "Boost 3 of 5", the colour detail only adds "The accent colour counts more",
--   and the "Found on" list (two dinos to a line, every dino, scrolls), or "Not found yet / Hatch eggs to find it!".
-- Close paths (docs/72, docs/181): the red X (56 px), the OK button (48 px), a tap on the dark backdrop or on the card, and Escape / gamepad B, which
-- close the whole menu (Bootstrap) and so remove this popup with the screen body. Closing only hides it: it never claims, buys or sends anything.
-- The popup lives INSIDE the screen body (never over the header or X), like the Dino Index egg popup. Static: no tween, Reduce Motion needs nothing.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Index = require(Shared:WaitForChild("PatternColourIndex"))
local Cards = require(script.Parent.PatternColourCards)

local Detail = {}
Detail.Name = "PatternColourDetail"
Detail.CardW, Detail.CardH = 580, 384

local C = Theme.Colors

-- host = the screen body; kind = "patterns" | "colours"; card = one entry of Index.cards; found = Index.foundSets(...); nameOf(speciesId) -> kid name.
-- Returns the backdrop (a second call replaces the first popup).
function Detail.open(host: GuiObject, kind: string, card: any, found: any, nameOf: any): GuiObject
    local old = host:FindFirstChild(Detail.Name)
    if old then old:Destroy() end
    local info = Index.detail(kind, card, found, nameOf)

    local scrim = Instance.new("TextButton")
    scrim.Name, scrim.Text, scrim.AutoButtonColor, scrim.Size = Detail.Name, "", false, UDim2.fromScale(1, 1)
    scrim.BackgroundColor3, scrim.BackgroundTransparency, scrim.ZIndex, scrim.Parent = Color3.new(0, 0, 0), 0.45, 40, host
    scrim.Activated:Connect(function() scrim:Destroy() end) -- a tap on the dark area (or on the card, which passes it on) closes

    local box = Instance.new("Frame")
    box.Name, box.Size, box.AnchorPoint, box.Position = "DetailCard", UDim2.fromOffset(Detail.CardW, Detail.CardH), Vector2.new(0.5, 0.5), UDim2.fromScale(0.5, 0.5)
    box.BackgroundColor3, box.ZIndex, box.Parent = C.panel, 41, scrim
    Theme.decorate(box, 24)
    local stroke = box:FindFirstChildOfClass("UIStroke")
    if stroke then stroke.Color, stroke.Thickness = Cards.borderColor(card), 5 end

    Cards.label(box, info.title, 16, 8, Detail.CardW - 96, 44, 32, C.gold, Enum.TextXAlignment.Left).Name = "Title"
    local x = Instance.new("TextButton")
    x.Name, x.Text, x.AutoButtonColor, x.Font, x.TextSize, x.TextColor3 = "Close", "X", false, Enum.Font.FredokaOne, 28, C.text
    x.Size, x.Position, x.AnchorPoint = UDim2.fromOffset(56, 56), UDim2.new(1, -10, 0, 8), Vector2.new(1, 0)
    x.BackgroundColor3, x.ZIndex, x.Parent = C.red, 43, box
    Theme.decorate(x, 8)
    x.Activated:Connect(function() scrim:Destroy() end)

    Cards.tile(box, kind, card, 110, 18, 62)
    local tierColor = if info.found then Cards.borderColor(card) else Cards.borderColor(card):Lerp(C.text, 0.25)
    Cards.label(box, info.tier, 146, 62, 400, 32, 26, tierColor).Name = "Tier"
    Cards.pips(box, card, 148, 100)
    Cards.label(box, info.boostText, 146, 126, 400, 28, 22, C.text).Name = "Boost"
    if info.hint then
        Cards.label(box, info.hint, 146, 156, 420, 28, 20, C.gold).Name = "Hint" -- colour detail only
    end

    local top = 196
    if info.found then
        Cards.label(box, "Found on:", 18, top, 300, 28, 22, C.gold).Name = "FoundOn"
        top += 30
    end
    -- the list scrolls (a Plain pattern can sit on every dino); four lines show at once, next to OK, not under it
    local list = Instance.new("ScrollingFrame")
    list.Name, list.BackgroundTransparency, list.BorderSizePixel, list.ScrollBarThickness = "Lines", 1, 0, 6
    list.Position, list.Size, list.ZIndex, list.Parent = UDim2.fromOffset(18, top), UDim2.fromOffset(400, 4 * 28), 42, box
    list.ScrollingDirection, list.CanvasSize = Enum.ScrollingDirection.Y, UDim2.fromOffset(0, #info.lines * 28)
    for i, line in info.lines do
        Cards.label(list, line, 0, (i - 1) * 28, 392, 28, 22, C.text).Name = "Line" .. i
    end

    local ok = Instance.new("TextButton")
    ok.Name, ok.Text, ok.AutoButtonColor, ok.Font, ok.TextSize, ok.TextColor3 = "Ok", "OK", false, Enum.Font.FredokaOne, 26, C.text
    ok.Size, ok.Position, ok.AnchorPoint = UDim2.fromOffset(140, 48), UDim2.new(1, -16, 1, -12), Vector2.new(1, 1)
    ok.BackgroundColor3, ok.ZIndex, ok.Parent = C.accent, 43, box
    Theme.decorate(ok, 8)
    ok.Activated:Connect(function() scrim:Destroy() end)

    return scrim
end

return Detail
