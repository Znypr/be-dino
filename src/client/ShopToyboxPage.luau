--!strict
-- BD-1178 (owner target 2026-11-14, docs/231): the page chrome of the Crystal Shop in the "Toybox" look. ShopScreens calls this only while
-- Config.ToyboxUIEnabled is true AND the six toybox_card_* pictures are bound (Page.active()); flag off, the shop is drawn exactly as before.
-- Client presentation only: no remote, no price, no save. Parts: the crystal wallet pill in the header (left of the X), cream tab chips with the
-- selected one amber, the "Styling: <dino>" chip (a tap goes to Dinos, where the dino is switched), one cream panel behind the Eggs / Conditions /
-- Crystals pages and the confirm popup (no text on studs), and the scrolling card grid that fills the whole body width (rules in Shared.ToyboxShop).
-- Flat colours only (UICorner + UIStroke): no picture is drawn in code (docs/72).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Rules = require(Shared.ToyboxShop)

local Page = {}
local OUTLINE = Color3.fromRGB(Kit.Outline[1], Kit.Outline[2], Kit.Outline[3])
local AMBER = Color3.fromRGB(255, 215, 106)

local function tone(name: string): Color3
    local t = (Kit.Tone :: any)[name]
    return Color3.fromRGB(t[1], t[2], t[3])
end
local function round(object: GuiObject, radius: number)
    local corner = Instance.new("UICorner")
    corner.CornerRadius, corner.Parent = UDim.new(0, radius), object
end
local function outline(object: GuiObject, thickness: number)
    local line = Instance.new("UIStroke")
    line.Name, line.Color, line.Thickness, line.ApplyStrokeMode = "CreamOutline", OUTLINE, thickness, Enum.ApplyStrokeMode.Border -- Border: the line round the box only, never round its text
    line.Parent = object
end
local function ink(label: TextLabel, which: string?): TextLabel
    label.TextColor3, label.TextStrokeTransparency = tone(which or "value"), 1
    for _, child in label:GetChildren() do
        if child:IsA("UIStroke") then child.Transparency = 1 end
    end
    return label
end

-- true while the skin is on and the six card pictures are bound: the shop then draws the Toybox page.
function Page.active(): boolean
    local skin = Theme.Toybox
    return skin ~= nil and skin.Kit.ready(Slots.Images, "card")
end

-- The crystal wallet in the header, left of the X: a cream pill with the crystal icon and the number. It lives in the header (not the body), so it
-- goes when `mark` (a frame in the body) is destroyed, which is what clearing the body for another screen does.
function Page.wallet(ui, header: GuiObject, mark: GuiObject, crystals: number, closeSide: number)
    local text = Rules.walletText(crystals)
    local height = 32
    local width = math.max(88, 44 + #text * 11)
    local pill = Instance.new("Frame")
    pill.Name, pill.BackgroundColor3, pill.BorderSizePixel = "WalletPill", tone("panel"), 0
    pill.AnchorPoint = Vector2.new(1, 0.5)
    pill.Position = UDim2.new(1, -(closeSide + 2 * Kit.CloseInset + 8), 0.5, 0)
    pill.Size, pill.ZIndex = UDim2.fromOffset(width, height), header.ZIndex + 4
    round(pill, 999)
    outline(pill, 3)
    pill.Parent = header
    local icon = ui.art(pill, "amber", 6, 3, height - 6)
    if icon then icon.Name = "WalletIcon" end
    local number = ui.label(pill, text, height - 2, 0, width - height - 2, height, 18, tone("value"))
    number.Name, number.TextXAlignment = "WalletNumber", Enum.TextXAlignment.Center
    ink(number)
    mark.Destroying:Connect(function() pill:Destroy() end)
    return pill
end

-- One cream chip button (a tab, the Styling chip). `selected` = amber. Its word is not shrunk: the window's floor pass lifts it to 14 px on screen
-- and the chip is as wide as the word (Shared.ToyboxShop.chipWidth).
local function chip(parent: GuiObject, name: string, text: string, x: number, width: number, height: number, selected: boolean, callback: () -> (), textSize: number): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.AutoButtonColor, b.BorderSizePixel = name, text, false, 0
    b.BackgroundColor3 = if selected then AMBER else tone("panel")
    b.Position, b.Size, b.ZIndex = UDim2.fromOffset(x, 0), UDim2.fromOffset(width, height), parent.ZIndex + 1
    b.Font, b.TextSize, b.TextColor3 = Enum.Font.FredokaOne, textSize, tone("value")
    b.TextTransparency, b.TextStrokeTransparency = 1, 1 -- the button keeps the word (tests, accessibility); the dark word below is what is drawn
    round(b, 12)
    outline(b, 3)
    -- the word: dark ink, no outline, on its own label so no outline style of the window can touch it (owner / lead Studio check 2026-11-14)
    local word = Instance.new("TextLabel")
    word.Name, word.BackgroundTransparency, word.Size, word.ZIndex, word.Text = "ChipWord", 1, UDim2.fromScale(1, 1), b.ZIndex + 1, text
    word.Font, word.TextSize, word.TextWrapped, word.TextXAlignment = Enum.Font.FredokaOne, textSize, false, Enum.TextXAlignment.Center
    ink(word)
    word.Parent = b
    word.ChildAdded:Connect(function(child) if child:IsA("UIStroke") then child.Transparency = 1 end end)
    b.Activated:Connect(callback)
    b.Parent = parent
    return b
end

-- The tab row: cream chips, the selected one amber; the "Styling: <dino>" chip (Auras and Trails only; it opens Dinos) sits at the right end of the
-- row, or on a row of its own under it when the row has no room (a small window). spec = {tabs, current, height, bodyW, textPx, styling = name?,
-- onTab(tab), onStyling()}. Returns the height the rows take (the cards start 12 px under it).
function Page.tabs(body: GuiObject, spec): number
    local size = spec.textPx or 18
    local f = size / 18
    local x = 0
    for _, tab in spec.tabs do
        local title = Rules.tabTitle(tab)
        local width = Rules.chipWidth(title, f)
        chip(body, "ShopTab_" .. tab, title, x, width, spec.height, spec.current == tab, function() spec.onTab(tab) end, size)
        x += width + Rules.Page.gutter
    end
    local rows = spec.height
    if spec.styling ~= nil then
        local text = Rules.styling(spec.styling)
        local width = math.min(Rules.chipWidth(text, f) + 16, spec.bodyW)
        local b = chip(body, "StylingChip", text, spec.bodyW - width, width, spec.height, false, spec.onStyling, size)
        if spec.bodyW - x < width then
            b.Position = UDim2.fromOffset(spec.bodyW - width, spec.height + Rules.Page.gutter)
            rows = spec.height * 2 + Rules.Page.gutter
        end
    end
    return rows
end

-- A cream panel behind a page (Eggs, Conditions, Crystals, the confirm popup): the content sits on it, never on the studs.
function Page.panel(body: GuiObject, y: number, width: number, height: number): Frame
    local panel = Instance.new("Frame")
    panel.Name, panel.BackgroundColor3, panel.BorderSizePixel = "ShopPanel", tone("panel"), 0
    panel.Position, panel.Size, panel.ZIndex = UDim2.fromOffset(0, y), UDim2.fromOffset(width, math.max(height, 0)), body.ZIndex
    round(panel, Kit.PanelCorner)
    outline(panel, Kit.PanelStroke)
    panel.Parent = body
    return panel
end

-- Dark ink on the cream panel for the labels a page draws on it (the old pages use gold and white words).
Page.ink = ink

-- A one-line cream note (the "no crystals yet" hint). Returns its bottom y.
function Page.hint(ui, body: GuiObject, text: string, y: number, width: number, textPx: number): number
    local h = Rules.Page.hintH + math.max(textPx - 18, 0)
    local holder = Instance.new("Frame")
    holder.Name, holder.BackgroundColor3, holder.BorderSizePixel = "ShopHint", tone("panel"), 0
    holder.Position, holder.Size, holder.ZIndex = UDim2.fromOffset(0, y), UDim2.fromOffset(width, h), body.ZIndex + 1
    round(holder, Kit.CardCorner)
    outline(holder, Kit.CardStroke)
    holder.Parent = body
    local line = ui.label(holder, text, 8, 0, width - 16, h, 18, tone("value"))
    ink(line)
    return y + h + Rules.Page.gutter
end

-- The scrolling card grid: fills the body width, cards as tall as the view (or the least a card needs). Returns the scroller and the grid
-- of Shared.ToyboxShop.grid (cells[i] = {x, y, w, h}). The cards are children of the scroller.
function Page.grid(body: GuiObject, y: number, bodyW: number, viewH: number, scale: number, count: number, buttonH: number)
    local grid = Rules.grid(bodyW, viewH, scale, count, buttonH)
    local scroller = Instance.new("ScrollingFrame")
    scroller.Name, scroller.BackgroundTransparency, scroller.BorderSizePixel, scroller.ClipsDescendants = "ShopGrid", 1, 0, true
    scroller.Position, scroller.Size, scroller.ZIndex = UDim2.fromOffset(0, y), UDim2.fromOffset(bodyW, viewH), body.ZIndex + 1
    scroller.ScrollBarThickness, scroller.ScrollBarImageColor3 = Rules.Page.scrollBar, tone("label")
    scroller.ScrollingDirection, scroller.CanvasSize = Enum.ScrollingDirection.Y, UDim2.fromOffset(0, if grid.scrolls then grid.canvasH else 0)
    scroller.Parent = body
    return scroller, grid
end

return Page
