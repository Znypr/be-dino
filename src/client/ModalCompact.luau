--!strict
-- BD-333: the compact (phone landscape) layout of the Bootstrap modal (Shop, Eggs, Index, Settings, Potions...).
-- Desktop keeps the 860x520 panel and the 824x402 body exactly as before. On a short canvas (Shared/PhoneScale decides) the panel
-- fills the screen, the UIScale stays >= 0.8 and the body scrolls inside a ScrollingFrame instead of shrinking to ~0.56.
-- After the content is drawn, a floor pass raises design text to 14 px and buttons to 44 px on screen. Lives in its own module
-- because Bootstrap.client is at the 200-local limit. Everything is a no-op in desktop mode.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local PhoneScale = require(Shared:WaitForChild("PhoneScale"))
local Theme = require(Shared:WaitForChild("UITheme"))

local M = {}

type Ctx = {gui: ScreenGui, panel: Frame, header: Frame, heading: TextLabel, body: GuiObject, closeButton: TextButton, scale: UIScale}
local ctx: Ctx? = nil
local scroller: ScrollingFrame? = nil
local model: PhoneScale.Modal? = nil
local pending = false

function M.model(): PhoneScale.Modal
    local c = ctx :: Ctx
    local size = c.gui.AbsoluteSize
    return PhoneScale.modal(size.X, size.Y)
end

local function ensureScroller(c: Ctx): ScrollingFrame
    if scroller then return scroller :: ScrollingFrame end
    local s = Instance.new("ScrollingFrame")
    s.Name, s.BackgroundTransparency, s.BorderSizePixel, s.ClipsDescendants = "BodyScroll", 1, 0, true
    s.ScrollBarThickness, s.ScrollBarImageColor3, s.ZIndex = 8, Theme.Colors.gold, 23
    s.ScrollingDirection, s.CanvasSize, s.Visible = Enum.ScrollingDirection.XY, UDim2.new(), false
    pcall(function() s.ElasticBehavior = Enum.ElasticBehavior.Never end)
    s.Parent = c.panel
    scroller = s
    return s
end

-- Re-lay the panel for the current canvas. Safe to call often (open, resize).
function M.layout()
    local c = ctx
    if not c then return end
    local m = M.model()
    model = m
    c.scale.Scale = m.scale
    if m.mode == "desktop" then
        c.panel.Size = UDim2.fromOffset(860, 520)
        c.header.Size = UDim2.fromOffset(852, 78)
        c.heading.Size, c.heading.TextSize = UDim2.fromOffset(730, 68), 40
        c.closeButton.Size = UDim2.fromOffset(math.max(80, 46 / m.scale), math.max(62, 46 / m.scale))
        if scroller then (scroller :: ScrollingFrame).Visible = false end
        if c.body.Parent ~= c.panel then c.body.Parent = c.panel end
        c.body.Position, c.body.Size = UDim2.fromOffset(18, 98), UDim2.fromOffset(824, 402)
        return
    end
    c.panel.Size = UDim2.fromOffset(m.panelW, m.panelH)
    c.header.Size = UDim2.fromOffset(m.panelW - 8, m.headerH)
    c.heading.Size, c.heading.TextSize = UDim2.fromOffset(m.panelW - 130, m.headerH - 8), 32
    c.closeButton.Size = UDim2.fromOffset(PhoneScale.floorButton(80, m.scale), PhoneScale.floorButton(m.headerH - 6, m.scale))
    local s = ensureScroller(c)
    s.Visible = true
    s.Position, s.Size = UDim2.fromOffset(4, m.bodyTop), UDim2.fromOffset(m.panelW - 8, m.bodyH)
    if c.body.Parent ~= s then c.body.Parent = s end
    c.body.Size = UDim2.fromOffset(824, 402)
    task.defer(M.enforce) -- the canvas may have been resized while a screen is open
end

-- Body position for open(): desktop slides from y=106 to 98, compact slides from 8 to 0 inside the scroller.
function M.place(settled: boolean, motion: boolean): UDim2
    local m = model or M.model()
    if m.mode == "desktop" then return UDim2.fromOffset(18, if settled or not motion then 98 else 106) end
    return UDim2.fromOffset(4, if settled or not motion then 0 else 8)
end

local function ancestorScale(object: Instance, stop: Instance): number
    local total, node = 1, object.Parent
    while node and node ~= stop do
        local u = node:FindFirstChildOfClass("UIScale")
        if u then total *= u.Scale end
        node = node.Parent
    end
    return total
end

-- Floor pass: text >= 14 px and buttons >= 44 px on screen. Buttons grow around their centre when they sit in a free layout.
function M.enforce()
    local c, m = ctx, model
    if not c or not m or m.mode ~= "compact" then return end
    local body = c.body
    local bottom = 402
    for _, d in body:GetDescendants() do
        if d:IsA("TextLabel") or d:IsA("TextButton") then
            local object = d :: TextLabel
            if not object.TextScaled then
                local scale = ancestorScale(d, c.panel) * m.scale
                local want = PhoneScale.floorText(object.TextSize, scale)
                if want > object.TextSize then object.TextSize = want end
            end
        end
        if d:IsA("TextButton") and d.Size.Y.Scale == 0 and d.Parent and d.Parent:FindFirstChildOfClass("UIGridLayout") == nil
            and d.Parent:FindFirstChildOfClass("UIListLayout") == nil then
            local scale = ancestorScale(d, c.panel) * m.scale
            local want = PhoneScale.floorButton(d.Size.Y.Offset, scale)
            if want > d.Size.Y.Offset and d.Size.Y.Offset > 0 then
                local grow = want - d.Size.Y.Offset
                d.Size = UDim2.new(d.Size.X.Scale, d.Size.X.Offset, 0, want)
                d.Position = UDim2.new(d.Position.X.Scale, d.Position.X.Offset, d.Position.Y.Scale, d.Position.Y.Offset - grow / 2)
            end
        end
    end
    for _, child in body:GetChildren() do
        if child:IsA("GuiObject") and child.Visible and child.Size.Y.Scale == 0 and child.Position.Y.Scale == 0 then
            bottom = math.max(bottom, child.Position.Y.Offset + child.Size.Y.Offset)
        end
    end
    local s = scroller
    if s then
        local width = if m.scrollX then 4 + 824 + 8 else 0
        s.CanvasSize = UDim2.fromOffset(width, bottom + 12)
    end
end

-- Debounced: many children are added while one screen renders, run the pass once afterwards.
local function schedule()
    if pending then return end
    pending = true
    task.defer(function()
        pending = false
        M.enforce()
    end)
end

function M.attach(context: Ctx)
    ctx = context
    context.body.DescendantAdded:Connect(schedule)
    context.body.ChildAdded:Connect(schedule)
    M.layout()
end

-- Scroll the compact body back to the top when a new screen opens.
function M.reset()
    local s = scroller
    if s then s.CanvasPosition = Vector2.zero end
    schedule()
end

return M
