--!strict
-- BD-1287 (docs/246 slice 1): with Config.MenusSaeFrameEnabled the Crystal Shop LANDING page shows in a compact Steal-an-Egg window instead of
-- the near full-screen panel: a green "Shop" header with the red X and the crystal pill, three bright cards (the landing pictures, the title,
-- one short line, a green OPEN) on a dark body, and a rail of category tiles OUTSIDE the window to its right. Numbers: Shared/SaeFrameRules.
-- How it sits on the shared modal: the window is a sibling of the Bootstrap panel inside ModalScrim; while it shows, the panel is hidden, the
-- cover is 6 % and the modal blur is off. A tiny marker in the panel body ties it to the screen: the next open() clears the body, the marker
-- is destroyed and everything (panel, cover, blur) goes back to the normal rules. Every other screen is untouched. No new art: the pictures
-- are the uploaded landing tiles and tab icons (ShopArt / AssetSlots); the rest is plain frames, strokes and one gradient.
local Lighting = game:GetService("Lighting")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Art = require(Shared.ShopArt)
local Rules = require(Shared.SaeFrameRules)

local M = {}

local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end

local function frame(parent: Instance, name: string, x: number, y: number, w: number, h: number, color: {number}, z: number): Frame
    local f = Instance.new("Frame")
    f.Name, f.BorderSizePixel, f.BackgroundColor3 = name, 0, rgb(color)
    f.Position, f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    return f
end

local function corner(parent: Instance, r: number)
    local c = Instance.new("UICorner") c.CornerRadius, c.Parent = UDim.new(0, r), parent
end

local function outline(parent: Instance, thickness: number)
    local s = Instance.new("UIStroke")
    s.Color, s.Thickness, s.ApplyStrokeMode, s.Parent = Color3.new(0, 0, 0), thickness, Enum.ApplyStrokeMode.Border, parent
end

-- white heavy words with a black outline (FredokaOne, like every top-game title)
local function words(parent: Instance, name: string, text: string, x: number, y: number, w: number, h: number, size: number, z: number, stroke: number): TextLabel
    local t = Instance.new("TextLabel")
    t.Name, t.Text, t.BackgroundTransparency, t.Font, t.TextSize = name, text, 1, Enum.Font.FredokaOne, size
    t.TextColor3, t.TextWrapped = Color3.new(1, 1, 1), false
    t.Position, t.Size, t.ZIndex, t.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    local s = Instance.new("UIStroke")
    s.Color, s.Thickness, s.ApplyStrokeMode, s.Parent = Color3.new(0, 0, 0), stroke, Enum.ApplyStrokeMode.Contextual, t
    return t
end

local function picture(parent: Instance, name: string, id: string, x: number, y: number, size: number, z: number): ImageLabel
    local img = Instance.new("ImageLabel")
    img.Name, img.BackgroundTransparency, img.Image, img.ScaleType = name, 1, id, Enum.ScaleType.Fit
    img.Position, img.Size, img.ZIndex, img.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(size, size), z, parent
    return img
end

local function tapArea(parent: Instance, name: string, x: number, y: number, w: number, h: number, z: number, fn: () -> ()): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.BackgroundTransparency, b.AutoButtonColor = name, "", 1, false
    b.Position, b.Size, b.ZIndex, b.Parent = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, parent
    b.Activated:Connect(fn)
    return b
end

-- One whole window + rail for a screen of this size. Returns the holder (a full-screen, input-transparent frame).
local function draw(shade: GuiObject, size: Vector2, spec: any): Frame
    local tabs: {string} = spec.tabs
    local titles = {}
    for _, tab in tabs do table.insert(titles, Art.Titles[tab] or tab) end
    local cardTabs = Rules.cardTabs(tabs)
    local lay = Rules.layout(size.X, size.Y, titles, #cardTabs)
    local holder = Instance.new("Frame")
    holder.Name, holder.BackgroundTransparency, holder.Size, holder.ZIndex, holder.Parent = "SaeShopLanding", 1, UDim2.fromScale(1, 1), 30, shade
    local win = lay.window
    -- the window (Active: a tap on its empty body never reaches the scrim, which would close the menu)
    local window = frame(holder, "SaeWindow", win.x, win.y, win.w, win.h, Rules.Body, 31)
    window.Active = true
    corner(window, lay.corner)
    outline(window, lay.stroke)
    -- the green header: rounded on top, square at the bottom (a foot strip of the same green), a light stripe along the top
    local header = frame(window, "SaeHeader", 0, 0, win.w, lay.headerH, Rules.Header, 32)
    corner(header, lay.corner)
    frame(header, "SaeHeaderFoot", 0, lay.headerH - lay.corner, win.w, lay.corner, Rules.Header, 32)
    local stripe = frame(header, "SaeHeaderStripe", lay.corner, 4, win.w - 2 * lay.corner, math.max(4, math.floor(lay.headerH * 0.12)), Rules.HeaderStripe, 33)
    corner(stripe, 3)
    frame(window, "SaeHeaderLine", 0, lay.headerH, win.w, lay.stroke, Rules.Outline, 33)
    local title = words(header, "SaeTitle", Rules.Title, lay.pad, 0, win.w * 0.4, lay.headerH, lay.titleSize, 34, 3)
    title.TextXAlignment = Enum.TextXAlignment.Left
    -- the red X
    local inset = math.floor((lay.headerH - lay.close) / 2)
    local closeButton = Instance.new("TextButton")
    closeButton.Name, closeButton.Text, closeButton.Font, closeButton.TextSize = "SaeClose", "X", Enum.Font.FredokaOne, lay.closeText
    closeButton.TextColor3, closeButton.BackgroundColor3, closeButton.AutoButtonColor, closeButton.BorderSizePixel = Color3.new(1, 1, 1), rgb(Rules.Close), true, 0
    closeButton.Position, closeButton.Size, closeButton.ZIndex, closeButton.Parent = UDim2.fromOffset(win.w - inset - lay.close, inset), UDim2.fromOffset(lay.close, lay.close), 35, header
    corner(closeButton, 6)
    outline(closeButton, 3)
    local xStroke = Instance.new("UIStroke") xStroke.Color, xStroke.Thickness, xStroke.ApplyStrokeMode, xStroke.Parent = Color3.new(0, 0, 0), 2, Enum.ApplyStrokeMode.Contextual, closeButton
    closeButton.Activated:Connect(function() if spec.close then spec.close() end end)
    -- the crystal pill (a whole number, no words)
    local amount = Rules.grouped(spec.info and spec.info.crystals or 0)
    local pw = Rules.pillWidth(amount, lay)
    local pill = frame(header, "SaeCrystalPill", lay.pill.x - pw, lay.pill.y, pw, lay.pill.h, Rules.PillFill, 34)
    corner(pill, math.floor(lay.pill.h / 2))
    outline(pill, 2)
    local gem = Art.tabIconId(Slots.Images, "crystals")
    if gem then picture(pill, "SaeCrystalIcon", gem, 6, 3, lay.pillIcon, 35) end
    local count = words(pill, "SaeCrystalCount", amount, lay.pillIcon + 10, 0, pw - lay.pillIcon - 18, lay.pill.h, lay.pillText, 35, 2)
    count.TextXAlignment = Enum.TextXAlignment.Left
    -- three bright cards
    for i, tab in cardTabs do
        local r = lay.cards[i]
        local fill = Rules.Fill[tab] or Rules.Fill.eggs
        local card = frame(window, "SaeCard_" .. tab, r.x, r.y, r.w, r.h, fill, 32)
        corner(card, 6)
        outline(card, 3)
        local shine = Instance.new("UIGradient") -- lighter at the top, the category colour at the bottom
        shine.Rotation, shine.Color, shine.Parent = 90, ColorSequence.new(rgb(fill):Lerp(Color3.new(1, 1, 1), 0.35), rgb(fill)), card
        local pick = function() spec.onPick(tab) end
        tapArea(card, "SaeCardTap", 0, 0, r.w, r.h, 33, pick)
        local bottom = r.h - 10
        local buttonY = bottom - lay.button
        local subY = buttonY - 8 - (lay.subText + 6)
        local titleY = (if lay.sub then subY else buttonY - 8) - (lay.cardTitle + 6)
        local artTop = 10
        local artY = artTop + math.max(0, math.floor((titleY - artTop - lay.art) / 2))
        local id = Art.tileId(Slots.Images, tab)
        if id and lay.art > 0 then picture(card, "SaeCardArt", id, math.floor((r.w - lay.art) / 2), artY, lay.art, 34) end
        words(card, "SaeCardTitle", Art.Titles[tab] or tab, 4, titleY, r.w - 8, lay.cardTitle + 6, lay.cardTitle, 34, 3)
        local line = Art.subtitle(tab, spec.info or {})
        if lay.sub and Rules.textWidth(line, lay.subText) <= r.w - 8 then -- the short line only where it fits at 19 px or more (never shrunk)
            words(card, "SaeCardLine", line, 4, subY, r.w - 8, lay.subText + 6, lay.subText, 34, 2)
        end
        local open = Instance.new("TextButton")
        open.Name, open.Text, open.Font, open.TextSize = "SaeCardOpen", "OPEN", Enum.Font.FredokaOne, lay.buttonText
        open.TextColor3, open.BackgroundColor3, open.AutoButtonColor, open.BorderSizePixel = Color3.new(1, 1, 1), rgb(Rules.Open), true, 0
        open.Position, open.Size, open.ZIndex, open.Parent = UDim2.fromOffset(10, buttonY), UDim2.fromOffset(r.w - 20, lay.button), 35, card
        corner(open, 6)
        outline(open, 3)
        local openWord = Instance.new("UIStroke") openWord.Color, openWord.Thickness, openWord.ApplyStrokeMode, openWord.Parent = Color3.new(0, 0, 0), 2, Enum.ApplyStrokeMode.Contextual, open
        local edge = Instance.new("UIGradient") -- the darker lower edge
        edge.Rotation, edge.Parent = 90, open
        edge.Color = ColorSequence.new({ColorSequenceKeypoint.new(0, rgb(Rules.Open)), ColorSequenceKeypoint.new(0.78, rgb(Rules.Open)), ColorSequenceKeypoint.new(0.8, rgb(Rules.OpenEdge)), ColorSequenceKeypoint.new(1, rgb(Rules.OpenEdge))})
        open.Activated:Connect(pick)
    end
    -- the rail outside the window
    for i, tab in tabs do
        local s = lay.rail.slots[i]
        if not s then break end
        local fill = Rules.Fill[tab] or Rules.Fill.eggs
        local tileX = s.x + math.floor((s.w - lay.rail.tile) / 2)
        local tile = frame(holder, "SaeRail_" .. tab, tileX, s.y, lay.rail.tile, lay.rail.tile, fill, 31)
        tile.Active = true
        corner(tile, 6)
        outline(tile, 3)
        local icon = Art.tabIconId(Slots.Images, tab) or Art.tileId(Slots.Images, tab)
        if icon then picture(tile, "SaeRailIcon", icon, 4, 4, lay.rail.tile - 8, 32) end
        tapArea(tile, "SaeRailTap", 0, 0, lay.rail.tile, lay.rail.tile, 33, function() spec.onPick(tab) end)
        if lay.rail.labels then
            words(holder, "SaeRailLabel_" .. tab, Art.Titles[tab] or tab, s.x, s.y + lay.rail.tile + 2, s.w, lay.rail.labelSize + 2, lay.rail.labelSize, 31, 2)
        end
    end
    return holder
end

-- body: the Bootstrap panel body; spec: ShopTiles.build's {tabs, info, onPick(tab), close()}. Returns false when the shared window is not
-- attached yet (the caller then draws the old landing tiles).
function M.build(body: GuiObject, spec: any): boolean
    local parts = require(script.Parent.ModalCompact).parts()
    if not parts then return false end
    local panel, gui = parts.panel, parts.gui
    local shade = panel.Parent
    if not shade or not shade:IsA("GuiObject") then return false end
    local mark = Instance.new("Frame")
    mark.Name, mark.BackgroundTransparency, mark.Size, mark.Parent = "SaeLandingMark", 1, UDim2.fromOffset(0, 0), body
    local holder: Frame? = nil
    local function redraw()
        if holder then holder:Destroy() end
        holder = draw(shade, gui.AbsoluteSize, spec)
    end
    panel.Visible = false
    redraw()
    local conns: {RBXScriptConnection} = {}
    table.insert(conns, gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(redraw))
    local function light() if shade.BackgroundTransparency < Rules.Cover then shade.BackgroundTransparency = Rules.Cover end end
    light()
    table.insert(conns, shade:GetPropertyChangedSignal("BackgroundTransparency"):Connect(light))
    local blur = Lighting:FindFirstChild("BeDinoModalBlur")
    if blur and blur:IsA("BlurEffect") then
        local function calm() if blur.Size > Rules.Blur then blur.Size = Rules.Blur end end
        calm()
        table.insert(conns, blur:GetPropertyChangedSignal("Size"):Connect(calm))
    end
    mark.Destroying:Connect(function()
        for _, c in conns do c:Disconnect() end
        if holder then holder:Destroy() holder = nil end
        panel.Visible = true
    end)
    return true
end

return M
