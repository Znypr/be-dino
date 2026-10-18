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
local lastMode: string? = nil -- BD-1067: the mode of the last layout(), so a change of mode puts the body back at that mode's home
local touched = false -- BD-1067: a compact pass has run, so something may be grown and a desktop pass must put it back
local clearLeft = 0 -- BD-546: px a desktop panel stays right of (the left rail + gap), set by Bootstrap from TouchLayout.modalClearLeft

function M.model(): PhoneScale.Modal
    local c = ctx :: Ctx
    local size = c.gui.AbsoluteSize
    return PhoneScale.modal(size.X, size.Y, clearLeft)
end

-- BD-546: where the panel sits. `yScale` is .5 settled, .52 while it slides in or out. Desktop slides right of the rail when the centre would
-- cover it; phones (compact) and every canvas wide enough for a centred panel keep UDim2.fromScale(.5, y) exactly.
function M.home(yScale: number): UDim2
    local m = if ctx then M.model() else nil
    return UDim2.new(0.5, if m then m.centerDx else 0, yScale, 0)
end

-- Called by Bootstrap after every HUD layout pass. A changed value re-lays the open panel at once (scale and position).
function M.setClearLeft(px: number)
    px = math.floor(px + 0.5)
    if px == clearLeft then return end
    clearLeft = px
    M.layout()
end

local function ensureScroller(c: Ctx): ScrollingFrame
    if scroller then return scroller :: ScrollingFrame end
    local s = Instance.new("ScrollingFrame")
    s.Name, s.BackgroundTransparency, s.BorderSizePixel, s.ClipsDescendants = "BodyScroll", 1, 0, true
    s.ScrollBarThickness, s.ScrollBarImageColor3, s.ZIndex = 8, Theme.Colors.gold, 23
    s.ScrollingDirection, s.CanvasSize, s.Visible = Enum.ScrollingDirection.Y, UDim2.new(), false -- BD-538: never sideways, the body is fitted to the width (PhoneScale.modal.fit)
    local fit = Instance.new("UIScale") -- BD-538: scales the whole scroller so a 836 px screen fits a narrow panel (667 px phone); 1 on wider canvases
    fit.Name, fit.Parent = "BodyFit", s
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
    c.panel.Position = UDim2.new(0.5, m.centerDx, c.panel.Position.Y.Scale, 0) -- BD-546: x only; the open/close slide owns y
    if m.mode == "desktop" then
        lastMode = "desktop"
        c.panel.Size = UDim2.fromOffset(860, 520)
        c.header.Size = UDim2.fromOffset(852, 78)
        c.heading.Size, c.heading.TextSize = UDim2.fromOffset(730, 68), PhoneScale.titleSize(40, m.scale, 68) -- BD-1119: a title renders at least 22 px
        local side = PhoneScale.closeSide(PhoneScale.CloseDesktop, m.scale, 78) -- BD-1117: a red square X, at least 48 px on screen
        c.closeButton.Size, c.closeButton.TextSize = UDim2.fromOffset(side, side), math.max(28, math.floor(side * 0.55))
        c.heading:SetAttribute("TextKind", "title")
        if scroller then (scroller :: ScrollingFrame).Visible = false end
        if c.body.Parent ~= c.panel then c.body.Parent = c.panel end
        c.body.Position, c.body.Size = UDim2.fromOffset(18, 98), UDim2.fromOffset(824, 402)
        if touched then task.defer(M.enforce) end -- BD-1067: undo what a compact canvas grew
        return
    end
    c.panel.Size = UDim2.fromOffset(m.panelW, m.panelH)
    c.header.Size = UDim2.fromOffset(m.panelW - 8, m.headerH)
    local side = PhoneScale.closeSide(0, m.scale, m.headerH) -- BD-1117: the X is a square of at least 48 px on screen, inside the (taller) header
    c.heading.Size, c.heading.TextSize = UDim2.fromOffset(m.panelW - side - 38, m.headerH - 8), PhoneScale.titleSize(32, m.scale, m.headerH - 8)
    c.closeButton.Size, c.closeButton.TextSize = UDim2.fromOffset(side, side), math.max(28, math.floor(side * 0.55))
    c.heading:SetAttribute("TextKind", "title")
    local s = ensureScroller(c)
    s.Visible = true
    -- BD-538: the scroller is innerW x innerH inside its own UIScale `fit`, so on screen it is still (panelW - 8) x bodyH design px wide and tall
    s.Position, s.Size = UDim2.fromOffset(4, m.bodyTop), UDim2.fromOffset(m.innerW, m.innerH)
    local fitScale = s:FindFirstChild("BodyFit")
    if fitScale and fitScale:IsA("UIScale") then fitScale.Scale = m.fit end
    if c.body.Parent ~= s then c.body.Parent = s end
    c.body.Size = UDim2.fromOffset(824, 402)
    if lastMode ~= "compact" then -- BD-1067: the window became compact while a screen was open (or this is the first layout): the body still had the desktop home (18, 98)
        c.body.AnchorPoint, c.body.Position = Vector2.zero, UDim2.fromOffset(4, 0)
    end
    lastMode = "compact"
    task.defer(M.enforce) -- the canvas may have been resized while a screen is open
end

-- BD-531: the body height (design px) that is on screen without scrolling: 402 on desktop, the scroller height on a phone canvas. Screens that
-- can fit a short canvas (Eggs, Go home) lay themselves out inside it instead of relying on the scroll.
-- BD-538: in the scroller's own units (innerH), and bodyScale is the scale a screen's px really render at (scale * fit).
function M.bodyHeight(): number
    local m = if ctx then M.model() else nil
    if m and m.mode == "compact" then return math.floor(m.innerH) end
    return 402
end

function M.bodyScale(): number
    local m = if ctx then M.model() else nil
    return if m then m.effScale else 1
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

-- BD-1067: the floor pass used to GROW design sizes for good: a window dragged narrow for a moment left every button and text bigger (a nest slot
-- 138 px tall, shifted up over the header) after the window was big again. The pass is now reversible: the design value is remembered in an
-- attribute (CmBaseH / CmBaseText) together with the value this pass set (CmH / CmText). A value that is not the one this pass set was changed by
-- the screen itself, so it becomes the new design value. Each pass recomputes from the design value, so growing and shrinking back are the same rule.
local function designValue(d: Instance, baseKey: string, appliedKey: string, current: number): number
    local base, applied = d:GetAttribute(baseKey), d:GetAttribute(appliedKey)
    if typeof(base) ~= "number" or typeof(applied) ~= "number" or applied ~= current then return current end
    return base
end

-- Floor pass: text >= 14 px and buttons >= 44 px on screen. Buttons grow around their centre when they sit in a free layout.
-- With floor = false (a desktop panel) every remembered design value is put back instead.
local function floorPass(c: Ctx, scalePanel: number, floor: boolean)
    for _, d in c.body:GetDescendants() do
        if d:IsA("TextLabel") or d:IsA("TextButton") then
            local object = d :: TextLabel
            if not object.TextScaled then
                local size = object.TextSize
                local base = designValue(d, "CmBaseText", "CmText", size)
                local want = if floor then PhoneScale.floorText(base, ancestorScale(d, c.panel) * scalePanel) else base
                if want ~= size then object.TextSize = want end
                d:SetAttribute("CmBaseText", base)
                d:SetAttribute("CmText", want)
            end
        end
        if d:IsA("TextButton") and d.Size.Y.Scale == 0 and d.Parent and d.Parent:FindFirstChildOfClass("UIGridLayout") == nil
            and d.Parent:FindFirstChildOfClass("UIListLayout") == nil and d.Size.Y.Offset > 0 then
            local height = d.Size.Y.Offset
            local base = designValue(d, "CmBaseH", "CmH", height)
            local want = if floor then PhoneScale.floorButton(base, ancestorScale(d, c.panel) * scalePanel) else base
            if want ~= height then
                d.Size = UDim2.new(d.Size.X.Scale, d.Size.X.Offset, 0, want)
                d.Position = UDim2.new(d.Position.X.Scale, d.Position.X.Offset, d.Position.Y.Scale, d.Position.Y.Offset - (want - height) / 2)
            end
            d:SetAttribute("CmBaseH", base)
            d:SetAttribute("CmH", want)
        end
    end
end

function M.enforce()
    local c, m = ctx, model
    if not c or not m then return end
    if m.mode ~= "compact" then
        if touched then touched = false floorPass(c, 1, false) end -- BD-1067: back on a desktop-sized canvas nothing stays grown
        return
    end
    touched = true
    local body = c.body
    local bottom = 0 -- BD-531: content that fits the scroller no longer gets a scroll bar from a 402 px minimum (see the Y-scale case below)
    floorPass(c, m.scale, true)
    for _, child in body:GetChildren() do
        if child:IsA("GuiObject") and child.Visible and child.Size.Y.Scale == 0 and child.Position.Y.Scale == 0 then
            bottom = math.max(bottom, child.Position.Y.Offset + child.Size.Y.Offset)
        elseif child:IsA("GuiObject") and child.Visible then
            bottom = math.max(bottom, 402) -- scale-sized or scale-placed children keep the old full-body canvas
        end
    end
    local s = scroller
    if s then
        -- BD-538: no horizontal canvas at all (the body is fitted to the width); BD-531: content that fits the scroller gets no scroll either
        s.CanvasSize = UDim2.fromOffset(0, if bottom <= m.innerH then 0 else bottom + 12)
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

-- BD-1039: the pieces of the Bootstrap modal for a screen that decorates its header (the Index tabs). nil before attach().
function M.parts(): Ctx?
    return ctx
end

-- Scroll the compact body back to the top when a new screen opens.
function M.reset()
    local s = scroller
    if s then s.CanvasPosition = Vector2.zero end
    schedule()
end

return M
