--!strict
-- BD-1266 / BD-1267 (docs/244 s2.12 to s2.14, owner 2026-11-17 "Yes, build it"): the ONE standard menu window every screen uses.
--   local w = MenuWindow.new({title = "Crystal Shop", colour = "green", kind = "long", gui = screenGui, onClose = fn})
--   w:setTabs({"featured", "auras"}, "featured", function(tab) ... end)   -- side category tabs OUTSIDE the window (BD-1267)
--   w:clear()  w:section("Auras", "green")  local grid = w:grid("offer")  w:offerCard(grid, {...})  w:itemCard(grid, {...})
--   w.redraw = function() ... end   -- called again when the screen size changes
--   w:close()
-- The frame: a striped title bar in the window colour (the Toybox header picture, Blender art), the title on the left, a big red square X
-- (the Toybox close picture), a dark body with the stud pattern, the world blurred (BlurEffect 12) and NO dark scrim, so the HUD corners stay
-- visible around it. Sizes are shares of the screen (Shared/MenuWindowRules, tested offline by tools/verify_menu_window.py).
-- Pictures come only from AssetSlots / existing art (docs/72, docs/77): code places and slices them, it draws no art. Client presentation only:
-- nothing here sends, saves or prices.
local Lighting = game:GetService("Lighting")
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared.MenuWindowRules)
local Kit = require(Shared.ToyboxKit)
local Slots = require(Shared.AssetSlots)
local Theme = require(Shared.UITheme)
local Chip = require(Shared.ChipStyle)
local Effects = require(Shared.EffectAssets)
local Sfx = require(Shared.Sfx)

local MenuWindow = {}
MenuWindow.__index = MenuWindow
MenuWindow.Rules = Rules

local BLACK = Color3.fromRGB(Kit.Outline[1], Kit.Outline[2], Kit.Outline[3])
local Z = 30 -- above the HUD (Bootstrap's own window is 20..23), under the toasts (50)

local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
-- A bound picture id of any AssetSlots image (kit pictures, tab icons, potion icons), nil while it is empty or malformed (never an invented id).
local function image(slot: string): string?
    local id = (Slots.Images :: any)[slot]
    return if type(id) == "string" and string.match(id, "^rbxassetid://%d+$") then id else nil
end
MenuWindow.image = image
local function motion(): boolean return Theme.MotionEnabled ~= false end

-- One blur for every standard window: on while at least one is open.
local blur: BlurEffect? = nil
local openCount = 0
local function setBlur(on: boolean)
    openCount = math.max(openCount + (if on then 1 else -1), 0)
    if not blur or not blur.Parent then
        local b = Instance.new("BlurEffect")
        b.Name, b.Size, b.Parent = "BeDinoMenuBlur", 0, Lighting
        blur = b
    end
    local b = blur :: BlurEffect
    local target = if openCount > 0 then Rules.Blur else 0
    if motion() then TweenService:Create(b, TweenInfo.new(0.15), {Size = target}):Play() else b.Size = target end
end

local function outline(label: TextLabel | TextButton, thickness: number?): UIStroke
    local stroke = Instance.new("UIStroke")
    stroke.Color, stroke.Thickness, stroke.LineJoinMode = BLACK, thickness or Rules.WordStroke, Enum.LineJoinMode.Round
    stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Contextual
    stroke.Parent = label
    return stroke
end
local function text(parent: GuiObject, name: string, words: string, size: number, colour: Color3, align: Enum.TextXAlignment?): TextLabel
    local label = Instance.new("TextLabel")
    label.Name, label.BackgroundTransparency, label.Text = name, 1, words
    label.Font, label.TextSize, label.TextColor3 = Enum.Font.FredokaOne, math.max(size, Rules.MinText), colour
    label.TextXAlignment, label.TextYAlignment = align or Enum.TextXAlignment.Center, Enum.TextYAlignment.Center
    label.TextScaled, label.TextWrapped = true, false
    local limit = Instance.new("UITextSizeConstraint")
    limit.MinTextSize, limit.MaxTextSize, limit.Parent = Rules.MinText, math.max(size, Rules.MinText), label
    label.ZIndex = parent.ZIndex + 1
    outline(label)
    label.Parent = parent
    return label
end
local function rect(o: GuiObject, r: any)
    o.Position, o.Size = UDim2.fromOffset(r.x, r.y), UDim2.fromOffset(r.w, r.h)
end
-- A Toybox picture 9-sliced to its box (header, card, button). Returns nil while the slot is not bound.
local function sliced(parent: GuiObject, name: string, slot: string, w: number, h: number): ImageLabel?
    local id = image(slot)
    local asset = Kit.Assets[slot]
    if not id or not asset or not asset.slice then return nil end
    local pic = Instance.new("ImageLabel")
    pic.Name, pic.BackgroundTransparency, pic.Image, pic.Size, pic.ZIndex = name, 1, id, UDim2.fromScale(1, 1), parent.ZIndex
    pic.ScaleType = Enum.ScaleType.Slice
    local s = asset.slice :: {number}
    pic.SliceCenter, pic.SliceScale = Rect.new(s[1], s[2], s[3], s[4]), Kit.sliceScale(slot, w, h)
    pic:SetAttribute("ToyboxSlot", slot)
    pic.Parent = parent
    return pic
end
local function picture(parent: GuiObject, name: string, id: string?, z: number?): ImageLabel?
    if not id or id == "" then return nil end
    local pic = Instance.new("ImageLabel")
    pic.Name, pic.BackgroundTransparency, pic.Image, pic.ScaleType = name, 1, id, Enum.ScaleType.Fit
    pic.Size, pic.ZIndex, pic.Parent = UDim2.fromScale(1, 1), z or parent.ZIndex + 1, parent
    return pic
end

export type Spec = {title: string, colour: string?, kind: string?, gui: ScreenGui, onClose: (() -> ())?}

function MenuWindow.new(spec: Spec)
    local self = setmetatable({}, MenuWindow) :: any
    self.spec, self.gui, self.colourName = spec, spec.gui, spec.colour or "grey"
    self.colour = rgb(Rules.colour(self.colourName))
    self.kind = spec.kind or "item"
    self.tabList, self.activeTab = {}, nil
    self.connections = {}
    local root = Instance.new("Frame")
    root.Name, root.BackgroundTransparency, root.BorderSizePixel, root.ZIndex = "StandardMenu", 1, 0, Z
    root.Active = true -- taps on the window never reach the world under it
    root:SetAttribute("MenuKind", self.kind)
    root:SetAttribute("MenuColour", self.colourName)
    self.root = root
    -- the dark body (stud picture on top, tinted dark)
    local back = Instance.new("Frame")
    back.Name, back.ZIndex = "Body", Z
    Chip.apply(back, rgb(Rules.Body)) -- the one chunky style: rounded rectangle, 3 px dark outline
    local studs = picture(back, "Studs", image("toybox_studs_tile"), Z)
    if studs then
        studs.ScaleType, studs.ImageColor3, studs.ImageTransparency = Enum.ScaleType.Tile, Color3.fromRGB(70, 66, 92), 0.55
        local round = Instance.new("UICorner") round.CornerRadius, round.Parent = Chip.radius(), studs
    end
    back.Parent = root
    self.back, self.studs = back, studs
    -- the title bar: the striped header picture in the window colour; a flat colour bar while the picture is not bound
    local bar = Instance.new("Frame")
    bar.Name, bar.BorderSizePixel, bar.ZIndex, bar.BackgroundColor3 = "TitleBar", 0, Z + 2, self.colour
    bar.Parent = root
    self.bar = bar
    self.title = text(bar, "Title", spec.title, 30, Color3.new(1, 1, 1), Enum.TextXAlignment.Left)
    self.title.ZIndex = Z + 4
    -- the red square X
    local x = Instance.new("ImageButton")
    x.Name, x.BackgroundColor3, x.BorderSizePixel, x.ZIndex, x.AutoButtonColor = "Close", Color3.fromRGB(247, 57, 48), 0, Z + 5, true
    local closeId = image("toybox_close")
    if closeId then
        x.Image, x.ScaleType, x.BackgroundTransparency = closeId, Enum.ScaleType.Fit, 1
    else
        Chip.apply(x, Color3.fromRGB(247, 57, 48))
        text(x, "X", "X", 30, Color3.new(1, 1, 1)).Size = UDim2.fromScale(1, 1)
    end
    x.Activated:Connect(function() Sfx.play("ui_click") self:close() end)
    x.Parent = bar
    self.closeButton = x
    -- the scrolling content
    local body = Instance.new("ScrollingFrame")
    body.Name, body.BackgroundTransparency, body.BorderSizePixel, body.ZIndex = "Content", 1, 0, Z + 1
    body.ScrollBarThickness, body.ScrollBarImageColor3, body.ScrollingDirection = 6, Color3.fromRGB(255, 255, 255), Enum.ScrollingDirection.Y
    body.AutomaticCanvasSize, body.CanvasSize = Enum.AutomaticSize.Y, UDim2.new()
    pcall(function() body.ElasticBehavior = Enum.ElasticBehavior.Never end)
    body.Parent = root
    self.body = body
    -- the side tabs live next to the window, outside it
    -- (their own ScreenGui, one step above the HUD panels that are ScreenGuis of their own (Codes 6), so a tab is never covered; same insets as the window)
    local tabsGui = Instance.new("ScreenGui")
    tabsGui.Name, tabsGui.ResetOnSpawn, tabsGui.DisplayOrder, tabsGui.ScreenInsets = "BeDinoMenuTabs", false, 7, spec.gui.ScreenInsets
    tabsGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
    local tabs = Instance.new("Frame")
    tabs.Name, tabs.BackgroundTransparency, tabs.ZIndex = "StandardMenuTabs", 1, Z
    tabs.Parent = tabsGui
    self.tabs, self.tabsGui = tabs, tabsGui
    root.Parent, tabsGui.Parent = spec.gui, spec.gui.Parent
    self:layout()
    table.insert(self.connections, spec.gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(function()
        local before = self.size
        self:layout()
        if self.size ~= before and self.redraw then self:clear() self.redraw() end
    end))
    setBlur(true)
    self.open = true
    if motion() then
        local pop = Instance.new("UIScale") pop.Scale, pop.Parent = 0.94, root
        TweenService:Create(pop, TweenInfo.new(0.16, Enum.EasingStyle.Back), {Scale = 1}):Play()
    end
    return self
end

-- Screen size in gui px.
function MenuWindow:screen(): (number, number)
    local s = self.gui.AbsoluteSize
    return math.max(s.X, 1), math.max(s.Y, 1)
end
function MenuWindow:screenH(): number
    local _, h = self:screen()
    return h
end

-- Lay the frame out for the current screen (sizes are shares of the screen, docs/244 s2.14).
function MenuWindow:layout()
    local W, H = self:screen()
    self.size = W .. "x" .. H
    local r = Rules.rect(W, H, self.kind)
    self.rect = r
    self.root.Position, self.root.Size = UDim2.fromOffset(r.x, r.y), UDim2.fromOffset(r.w, r.h)
    local barH = Rules.px(H, Rules.H.titleBar)
    local pad = Rules.px(H, Rules.H.pad)
    self.bar.Position, self.bar.Size = UDim2.new(), UDim2.new(1, 0, 0, barH)
    local old = self.bar:FindFirstChild("Stripes")
    if old then old:Destroy() end
    local stripes = sliced(self.bar, "Stripes", Rules.headerSlot(self.colourName), r.w, barH)
    if stripes then stripes.ZIndex, self.bar.BackgroundTransparency = Z + 2, 1 else self.bar.BackgroundTransparency = 0 end
    local side = math.max(Rules.px(H, Rules.H.close), Rules.MinTarget)
    local inset = math.max(math.floor((barH - side) / 2), 2)
    self.closeButton.AnchorPoint = Vector2.new(1, 0.5)
    self.closeButton.Position, self.closeButton.Size = UDim2.new(1, -inset, 0.5, 0), UDim2.fromOffset(side, side)
    local titleSize = Rules.textSize(H, Rules.H.title)
    self.title.Position, self.title.Size = UDim2.fromOffset(pad, 0), UDim2.new(1, -(pad + side + 2 * inset), 1, 0)
    self.title.TextSize = titleSize
    local limit = self.title:FindFirstChildOfClass("UITextSizeConstraint")
    if limit then limit.MaxTextSize = titleSize end
    self.back.Position, self.back.Size = UDim2.fromOffset(0, math.floor(barH / 2)), UDim2.new(1, 0, 1, -math.floor(barH / 2))
    if self.studs then self.studs.TileSize = UDim2.fromOffset(math.max(barH * 2, 64), math.max(barH * 2, 64)) end
    self.body.Position, self.body.Size = UDim2.fromOffset(pad, barH + pad), UDim2.new(1, -2 * pad + 4, 1, -(barH + 2 * pad))
    self.contentW = r.w - 2 * pad - 8 -- the 6 px scroll bar plus a hair
    self.pad = pad
    local list = self.body:FindFirstChildOfClass("UIListLayout")
    if not list then
        list = Instance.new("UIListLayout")
        list.Name, list.SortOrder, list.FillDirection = "List", Enum.SortOrder.LayoutOrder, Enum.FillDirection.Vertical
        list.HorizontalAlignment = Enum.HorizontalAlignment.Left
        list.Parent = self.body
    end
    list.Padding = UDim.new(0, Rules.px(H, Rules.H.gap) // 2)
    self:layoutTabs()
end

-- ---------------------------------------------------------------- side category tabs (BD-1267)
-- tabs = list of tab keys (Rules.TabArt / Rules.TabWords); onTab(tab) is called on a tap. The active tab glows in the window colour and bounces.
function MenuWindow:setTabs(tabs: {string}, active: string?, onTab: ((string) -> ())?)
    self.tabList, self.activeTab, self.onTab = tabs, active, onTab
    self:layoutTabs()
end
function MenuWindow:layoutTabs()
    local column = self.tabs :: Frame
    column:ClearAllChildren()
    local list = self.tabList
    if #list == 0 then return end
    local W, H = self:screen()
    local t = Rules.tabs(W, H, self.kind, #list)
    column.Position, column.Size = UDim2.fromOffset(t.x, t.y), UDim2.fromOffset(t.w, t.h)
    for i, key in list do
        local on = key == self.activeTab
        local tab = Instance.new("TextButton")
        tab.Name, tab.Text, tab.BackgroundTransparency, tab.AutoButtonColor, tab.ZIndex = "Tab_" .. key, "", 1, false, Z + 1
        tab.Position, tab.Size = UDim2.fromOffset(0, (i - 1) * t.pitch), UDim2.fromOffset(t.tabW, t.tabH)
        tab:SetAttribute("Active", on)
        tab.Parent = column
        local holder = Instance.new("Frame")
        holder.Name, holder.BackgroundTransparency, holder.ZIndex = "Icon", 1, Z + 2
        holder.AnchorPoint, holder.Position, holder.Size = Vector2.new(0.5, 0), UDim2.new(0.5, 0, 0, 0), UDim2.fromOffset(t.icon, t.icon)
        holder.Parent = tab
        if on and Effects.isRealUi("glowPlate") then -- the soft glow behind the active icon, in the window colour (the existing glowPlate texture)
            local glow = picture(holder, "Glow", Effects.resolveUi("glowPlate"), Z + 2)
            if glow then
                glow.ImageColor3, glow.ImageTransparency = self.colour, 0.15
                glow.AnchorPoint, glow.Position, glow.Size = Vector2.new(0.5, 0.5), UDim2.fromScale(0.5, 0.5), UDim2.fromScale(1.6, 1.6)
            end
        end
        local icon = picture(holder, "Art", image(Rules.TabArt[key] or ""), Z + 3)
        if icon and not on then icon.ImageTransparency = 0.15 end
        local word = text(tab, "Word", Rules.tabWord(key), t.word, if on then self.colour else Color3.new(1, 1, 1))
        word.Position, word.Size, word.ZIndex = UDim2.fromOffset(-t.word, t.icon), UDim2.new(1, 2 * t.word, 0, t.tabH - t.icon), Z + 4
        if on then
            local s = Instance.new("UIScale") s.Parent = holder
            if motion() then
                s.Scale = 0.85
                TweenService:Create(s, TweenInfo.new(0.25, Enum.EasingStyle.Back), {Scale = 1.1}):Play()
            else
                s.Scale = 1.1
            end
        end
        tab.Activated:Connect(function()
            if key == self.activeTab then return end
            Sfx.play("ui_click")
            self.activeTab = key
            self:layoutTabs()
            if self.onTab then self.onTab(key) end
        end)
    end
end

-- ---------------------------------------------------------------- content
function MenuWindow:setTitle(words: string) self.title.Text = words end
-- A short timer in kid words on the title bar, left of the X ("New in 1 min"), in the counter style: white, outlined, no plate.
-- nil removes it. Returns the label so a page can update its text every second.
function MenuWindow:setStatus(words: string?): TextLabel?
    local old = self.bar:FindFirstChild("Status")
    if old then old:Destroy() end
    if not words then return nil end
    local H = self:screenH()
    local side = math.max(Rules.px(H, Rules.H.close), Rules.MinTarget)
    local w = math.floor(self.rect.w * 0.34)
    local label = text(self.bar, "Status", words, Rules.textSize(H, Rules.H.offerLine), Color3.new(1, 1, 1), Enum.TextXAlignment.Right)
    label.AnchorPoint, label.Position, label.Size, label.ZIndex = Vector2.new(1, 0.5), UDim2.new(1, -(side + 2 * self.pad), 0.5, 0), UDim2.new(0, w, 0.8, 0), Z + 4
    return label
end
function MenuWindow:clear()
    for _, child in self.body:GetChildren() do
        if not child:IsA("UIListLayout") then child:Destroy() end
    end
    self.order = 0
end
function MenuWindow:nextOrder(): number
    self.order = (self.order or 0) + 1
    return self.order
end

-- "-- AURAS --": a coloured section word with a black outline, 3.8 % h cap.
function MenuWindow:section(name: string, colour: string?)
    local H = self:screenH()
    local size = Rules.textSize(H, Rules.H.section)
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.ZIndex, row.LayoutOrder = "Section_" .. name, 1, Z + 1, self:nextOrder()
    row.Size = UDim2.new(1, 0, 0, size + 6)
    row.Parent = self.body
    local word = text(row, "Word", Rules.section(name), size, rgb(Rules.colour(colour or self.colourName)))
    word.Size = UDim2.fromScale(1, 1)
    return row
end

-- A plain outlined line (a note, a timer in kid words).
function MenuWindow:line(words: string, share: number?, colour: Color3?)
    local H = self:screenH()
    local size = Rules.textSize(H, share or Rules.H.offerLine)
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.ZIndex, row.LayoutOrder = "Line", 1, Z + 1, self:nextOrder()
    row.Size = UDim2.new(1, 0, 0, size + 6)
    row.Parent = self.body
    local word = text(row, "Word", words, size, colour or Color3.new(1, 1, 1))
    word.Size = UDim2.fromScale(1, 1)
    return row, word
end

-- A grid of equal cards: "offer" = 2 per row on a phone (3 on desktop), "item" = 3 per row. Returns the grid frame and the cell size.
function MenuWindow:grid(card: string, columns: number?, cardH: number?): (Frame, number, number)
    local H = self:screenH()
    local gap = Rules.px(H, Rules.H.gap)
    local cols = columns or Rules.columns(card, H)
    local cellW = Rules.cell(self.contentW, cols, gap)
    local cellH = cardH or (if card == "offer" then Rules.px(H, Rules.H.offerCard) else self:itemHeight())
    local grid = Instance.new("Frame")
    grid.Name, grid.BackgroundTransparency, grid.ZIndex, grid.LayoutOrder = "Grid_" .. card, 1, Z + 1, self:nextOrder()
    grid.Size, grid.AutomaticSize = UDim2.fromOffset(self.contentW, 0), Enum.AutomaticSize.Y
    local layout = Instance.new("UIGridLayout")
    layout.CellSize, layout.CellPadding = UDim2.fromOffset(cellW, cellH), UDim2.fromOffset(gap, gap)
    layout.SortOrder, layout.HorizontalAlignment = Enum.SortOrder.LayoutOrder, Enum.HorizontalAlignment.Center
    layout.Parent = grid
    grid.Parent = self.body
    return grid, cellW, cellH
end
-- An item card is 44 % h tall, never taller than the body can show.
function MenuWindow:itemHeight(): number
    local H = self:screenH()
    local bodyH = self.rect.h - Rules.px(H, Rules.H.titleBar) - 2 * self.pad
    local used = 0 -- rows already in the body (a timer line, a section word) push the first card row down: it still fits
    for _, child in self.body:GetChildren() do
        if child:IsA("GuiObject") and not child:IsA("UIListLayout") then used += math.max(child.Size.Y.Offset, child.AbsoluteSize.Y) + Rules.px(H, Rules.H.gap) // 2 end
    end
    return math.max(math.min(Rules.px(H, Rules.H.itemCard), bodyH - used - 4), 120)
end

-- The one card button: green with the crystal icon and the number, or a word ("Equip", "Use"). Gloss button picture when bound.
local function cardButton(parent: GuiObject, r: any, state: any, H: number, onPress: (() -> ())?): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.AutoButtonColor, b.BorderSizePixel, b.ZIndex = "Action", "", false, 0, parent.ZIndex + 2
    rect(b, r)
    b.Active = state.active
    local fill = if state.green then Color3.fromRGB(93, 237, 31) else Color3.fromRGB(128, 142, 158)
    local face = sliced(b, "Face", "toybox_button_" .. (if state.green then "green" else "grey"), r.w, r.h)
    if face then b.BackgroundTransparency = 1 face.ZIndex = b.ZIndex else Chip.apply(b, fill) end
    local size = Rules.textSize(H, Rules.H.offerLine)
    local word = text(b, "Price", state.text, size, Color3.new(1, 1, 1))
    word.ZIndex = b.ZIndex + 2
    if state.icon then
        local iconSide = math.floor(r.h * 0.7)
        -- the game's crystal icon (Theme.icon "amber": the uploaded crystal picture, else the crystal model in a ViewportFrame), as on the HUD counter
        local icon = Instance.new("Frame")
        icon.Name, icon.BackgroundTransparency, icon.ZIndex = "CrystalIcon", 1, b.ZIndex + 1
        local art = Theme.icon(icon, "amber")
        if art then art.Position, art.Size = UDim2.new(), UDim2.fromScale(1, 1) icon.Parent = b else icon:Destroy() icon = nil :: any end
        if icon then
            icon.AnchorPoint, icon.Size = Vector2.new(0, 0.5), UDim2.fromOffset(iconSide, iconSide)
            local textW = math.min(#state.text * size * 0.62, r.w - iconSide - 12)
            local groupW = iconSide + 6 + textW
            local left = math.max(math.floor((r.w - groupW) / 2), 4)
            icon.Position = UDim2.new(0, left, 0.5, 0)
            word.TextXAlignment = Enum.TextXAlignment.Left
            word.Position, word.Size = UDim2.fromOffset(left + iconSide + 6, 0), UDim2.new(0, math.ceil(textW) + 4, 1, 0)
        else
            word.Size = UDim2.fromScale(1, 1)
        end
    else
        word.Size = UDim2.fromScale(1, 1)
    end
    if onPress then b.Activated:Connect(function() Sfx.play("ui_click") onPress() end) end
    b.Parent = parent
    return b
end

-- The card picture: the tier card (Blender art, toybox_card_<rarity>), else the flat rarity colour.
local function cardBack(parent: GuiObject, name: string, rarity: string?, w: number, h: number, order: number): Frame
    local card = Instance.new("Frame")
    card.Name, card.BorderSizePixel, card.ZIndex, card.LayoutOrder = name, 0, Z + 2, order
    local pic = sliced(card, "CardArt", Rules.cardSlot(rarity), w, h)
    if pic then card.BackgroundTransparency = 1 else Chip.apply(card, rgb(Rules.rarityColour(rarity))) end
    card:SetAttribute("Rarity", Rules.rarity(rarity))
    card.Parent = parent
    return card
end

-- The art box of a card: spec.art(box) puts the real picture in it (an ImageLabel, a ViewportFrame or the existing item icon). Never drawn here.
local function artBox(card: GuiObject, r: any, spec: any): Frame
    local box = Instance.new("Frame")
    box.Name, box.BackgroundTransparency, box.ZIndex, box.ClipsDescendants = "Render", 1, card.ZIndex + 2, false
    rect(box, r)
    box.Parent = card
    if spec.image then picture(box, "Picture", spec.image, box.ZIndex + 1) end
    if spec.art then spec.art(box) end
    return box
end

-- Pass / offer card (Crystal Shop sections, BD-1266): 28 % h tall, the tier picture, a 15 % h icon on the left, the title, ONE line with the key
-- word green, the green crystal price button. spec = {name, title, line, rarity, image?, art?, state, price, level?, onPress, order?}
function MenuWindow:offerCard(parent: GuiObject, spec: any): Frame
    local H = self:screenH()
    local layout = parent:FindFirstChildOfClass("UIGridLayout")
    local w = if layout then layout.CellSize.X.Offset else self.contentW
    local parts = Rules.offerParts(w, H)
    local card = cardBack(parent, "Offer_" .. (spec.name or spec.title), spec.rarity, w, parts.h, spec.order or self:nextOrder())
    if not layout then card.Size = UDim2.fromOffset(w, parts.h) end
    artBox(card, parts.icon, spec)
    local title = text(card, "Title", spec.title, Rules.textSize(H, Rules.H.offerTitle), Color3.new(1, 1, 1), Enum.TextXAlignment.Left)
    rect(title, parts.title)
    title.ZIndex = card.ZIndex + 3
    local line = text(card, "Line", Rules.highlight(spec.line or ""), Rules.textSize(H, Rules.H.offerLine), Color3.new(1, 1, 1), Enum.TextXAlignment.Left)
    line.RichText = true
    rect(line, parts.line)
    line.ZIndex = card.ZIndex + 3
    cardButton(card, parts.button, Rules.button(spec.state or "buy", spec.price, spec.level), H, spec.onPress)
    return card
end

-- Item card (potions, auras, trails, eggs, BD-1266): one solid rarity colour, the name with the rarity word under it, a big render, a dark
-- effect strip with the number green, a full-width button. spec = {name, title, rarity, effect, image?, art?, state, price, level?, onPress}
function MenuWindow:itemCard(parent: GuiObject, spec: any): Frame
    local H = self:screenH()
    local layout = parent:FindFirstChildOfClass("UIGridLayout")
    local w = if layout then layout.CellSize.X.Offset else self.contentW
    local h = if layout then layout.CellSize.Y.Offset else self:itemHeight()
    local noButton = spec.state == "none"
    local parts = Rules.itemParts(w, H, h, noButton)
    local card = cardBack(parent, "Item_" .. (spec.name or spec.title), spec.rarity, w, h, spec.order or self:nextOrder())
    if not layout then card.Size = UDim2.fromOffset(w, h) end
    local name = text(card, "Name", spec.title, Rules.textSize(H, Rules.H.itemName), Color3.new(1, 1, 1))
    rect(name, parts.name)
    name.ZIndex = card.ZIndex + 3
    local rarity = text(card, "RarityWord", Rules.rarity(spec.rarity), Rules.textSize(H, Rules.H.itemRarity), rgb(Rules.rarityColour(spec.rarity)):Lerp(Color3.new(1, 1, 1), 0.35))
    rect(rarity, parts.rarity)
    rarity.ZIndex = card.ZIndex + 3
    artBox(card, parts.render, spec)
    local strip = Instance.new("Frame")
    strip.Name, strip.BackgroundColor3, strip.BackgroundTransparency, strip.BorderSizePixel, strip.ZIndex = "EffectStrip", rgb(Rules.Strip), 0.2, 0, card.ZIndex + 3
    rect(strip, parts.strip)
    local round = Instance.new("UICorner") round.CornerRadius, round.Parent = Chip.radius(true), strip
    strip.Parent = card
    local effect = text(strip, "Effect", Rules.highlight(spec.effect or ""), Rules.textSize(H, Rules.H.itemEffect), Color3.new(1, 1, 1))
    effect.RichText, effect.Size, effect.ZIndex = true, UDim2.fromScale(1, 1), strip.ZIndex + 1
    if not noButton then cardButton(card, parts.button, Rules.button(spec.state or "buy", spec.price, spec.level), H, spec.onPress) end
    return card
end

-- A small confirm panel over the window body ("Buy Meadow Glow?" with the price, BUY and NOT NOW). No Robux, crystals only.
function MenuWindow:confirm(spec: {title: string, price: number, onBuy: () -> (), image: string?, art: ((GuiObject) -> ())?})
    local H = self:screenH()
    local old = self.root:FindFirstChild("Confirm")
    if old then old:Destroy() end
    local veil = Instance.new("TextButton")
    veil.Name, veil.Text, veil.AutoButtonColor, veil.BackgroundColor3, veil.BackgroundTransparency = "Confirm", "", false, Color3.new(0, 0, 0), 0.35
    local barH = Rules.px(H, Rules.H.titleBar) -- the veil covers the body only: the X stays tappable
    veil.Position, veil.Size, veil.ZIndex = UDim2.fromOffset(0, barH), UDim2.new(1, 0, 1, -barH), Z + 20
    veil.Parent = self.root
    local w, h = math.floor(self.rect.w * 0.62), math.floor(self.rect.h * 0.7)
    local panel = Instance.new("Frame")
    panel.Name, panel.AnchorPoint, panel.Position, panel.Size, panel.ZIndex = "Panel", Vector2.new(0.5, 0.5), UDim2.fromScale(0.5, 0.55), UDim2.fromOffset(w, h), Z + 21
    Chip.apply(panel, rgb(Rules.Body))
    panel.Parent = veil
    local pad = self.pad
    local titleSize = Rules.textSize(H, Rules.H.offerTitle)
    local title = text(panel, "Title", spec.title, titleSize, Color3.new(1, 1, 1))
    title.Position, title.Size, title.ZIndex = UDim2.fromOffset(pad, pad), UDim2.new(1, -2 * pad, 0, titleSize + 6), Z + 23
    local buttonH = math.max(Rules.px(H, Rules.H.priceButton), Rules.MinTarget)
    local artTop = pad + titleSize + 10
    local artH = math.max(h - artTop - 2 * buttonH - 3 * pad, 24)
    local art = Instance.new("Frame")
    art.Name, art.BackgroundTransparency, art.ZIndex = "Render", 1, Z + 22
    art.Position, art.Size = UDim2.new(0.5, -artH // 2, 0, artTop), UDim2.fromOffset(artH, artH)
    art.Parent = panel
    if artH >= 32 then -- a short screen has no room for the picture: the words and the two buttons stay
        if spec.image then picture(art, "Picture", spec.image, Z + 23) end
        if spec.art then spec.art(art) end
    end
    local bw = w - 2 * pad
    local buy = cardButton(panel, {x = pad, y = h - 2 * buttonH - pad - pad // 2, w = bw, h = buttonH}, Rules.button("buy", spec.price), H, function()
        veil:Destroy()
        spec.onBuy()
    end)
    buy.Name = "Buy"
    local no = cardButton(panel, {x = pad, y = h - buttonH - pad, w = bw, h = buttonH}, {text = "Not now", green = false, active = true, icon = false}, H, function() veil:Destroy() end)
    no.Name = "NotNow"
    return veil
end

-- Close the window: the blur goes, the tabs go, onClose runs once.
function MenuWindow:close()
    if not self.open then return end
    self.open = false
    for _, c in self.connections do c:Disconnect() end
    setBlur(false)
    self.root:Destroy()
    self.tabsGui:Destroy()
    if self.spec.onClose then self.spec.onClose() end
end

-- For tests and captures: is a standard window open now?
function MenuWindow.anyOpen(): boolean
    return openCount > 0
end

return MenuWindow
