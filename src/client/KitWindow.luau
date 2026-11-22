--!strict
-- BD-1287 (docs/246, owner 2026-11-22: "build reusable menus that just look like the proposed approved ones ... no reason to create fully new
-- menus that look way off"): the shop menu kit WINDOW, the owner's APPROVED Aura Shop window, for every shop page: the dark studded body
-- (the kit 2 effect strip art at window size; the Toybox frame + stud tile while it is not bound), the kit 2 header strip in the page colour (studs, three shine stripes, drawn in pieces at its own height so the
-- stripes and studs stay crisp) with the title in big white outlined words at the left and the kit 2 red X at the right, the kit cards
-- (client/KitCard) and the tabs outside the window (client/KitRail). While a kit 2 piece is not bound it keeps the Toybox look.
-- Screens pass only data: KitWindow.open(body, spec) with spec = {title, colour ("green" | "purple"), cards = {KitCard.Spec}, rail =
-- KitRail.Spec, onClose, layout(w, h, cards, inset) -> SaeFrameRules.Layout}. Returns false when the shared window is not attached yet or
-- the kit 1 frame is not bound (the caller then draws its old page).
-- The lifecycle (on the shared modal): the window is a sibling of the Bootstrap panel inside ModalScrim; while it shows, the panel and the HUD
-- are hidden, the cover is 6 % and the menus' blur is 14 px. A tiny marker in the panel body ties it to the screen: the next open() clears
-- the body, the marker is destroyed and everything (panel, cover, blur, HUD) goes back to the normal rules. Every other screen is untouched.
local GuiService = game:GetService("GuiService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Kit = require(Shared.ToyboxKit)
local Kit2 = require(Shared.ShopKit2)
local Rules = require(Shared.SaeFrameRules)
local Art = require(script.Parent.KitArt)
local KitCard = require(script.Parent.KitCard)
local KitRail = require(script.Parent.KitRail)

local W = {}

-- While the window is open the HUD is hidden (the approved window sits over a blurred world with no HUD around it): every other top-level
-- piece of BeDinoUI (but the menu cover and the toasts) and every other enabled ScreenGui drawn at or under BeDinoUI. A script that shows
-- one of them meanwhile is remembered, not overruled for good: on close each one goes back to what it last asked for.
local KEEP = {ModalScrim = true, Toasts = true}
local function veil(gui: ScreenGui): () -> ()
    local conns: {RBXScriptConnection} = {}
    local wanted: {[Instance]: boolean} = {}
    local function hold(object: Instance, prop: string)
        wanted[object] = (object :: any)[prop]
        ;(object :: any)[prop] = false
        table.insert(conns, object:GetPropertyChangedSignal(prop):Connect(function()
            if (object :: any)[prop] == true then wanted[object] = true (object :: any)[prop] = false end
        end))
    end
    for _, child in gui:GetChildren() do
        if child:IsA("GuiObject") and child.Visible and not KEEP[child.Name] then hold(child, "Visible") end
    end
    local playerGui = gui.Parent
    if playerGui then
        for _, other in playerGui:GetChildren() do
            if other ~= gui and other:IsA("ScreenGui") and other.Enabled and other.DisplayOrder <= gui.DisplayOrder then hold(other, "Enabled") end
        end
    end
    return function()
        for _, c in conns do c:Disconnect() end
        for object, value in wanted do
            if object.Parent then (object :: any)[if object:IsA("ScreenGui") then "Enabled" else "Visible"] = value end
        end
    end
end

-- The kit 2 header strip in pieces (Shared/ShopKit2.headerPieces): caps and stripes at the strip's height scale, the stud column tiled.
local function header2(parent: Instance, colour: string, w: number, h: number): boolean
    local id = Kit2.image(Slots.Images, Kit2.headerSlot(colour))
    if not id then return false end
    local k = h / Kit2.Header.h
    for i, p in Kit2.headerPieces(w, h) do
        local crop = {x = p.cropX, y = 0, w = p.cropW, h = Kit2.Header.h}
        if p.tile then Art.tiled(parent, "Strip" .. i, id, p.x, 0, p.w, h, 33, crop, p.cropW * k, h)
        else Art.picture(parent, "Strip" .. i, id, p.x, 0, p.w, h, 33, crop).ScaleType = Enum.ScaleType.Stretch end
    end
    return true
end

-- The Toybox header strip (fallback): the kit 1 header 9-sliced, its shine stripes laid across the stretched middle as crops.
local function header1(parent: Instance, colour: string, w: number, h: number, stripesTo: number)
    local slot = "toybox_header_" .. colour
    Art.kit(parent, "Strip", slot, 0, 0, w, h, 33)
    local id = Kit.image(Slots.Images, slot)
    if not id then return end
    local k = h / Rules.HeaderStripeCrop.h
    local x0 = math.floor(Rules.HeaderCaps.left * k)
    local band = Art.box(parent, "Stripes", x0, 0, math.max(0, stripesTo - x0), h, 34)
    band.ClipsDescendants = true
    local step = Rules.HeaderStripeCrop.w * k
    local x = 0
    while x < stripesTo - x0 do
        local crop = Art.picture(band, "Stripe", id, math.floor(x), 0, math.ceil(step) + 1, h, 34, {x = Rules.HeaderStripeCrop.x, y = 0, w = Rules.HeaderStripeCrop.w, h = Rules.HeaderStripeCrop.h})
        crop.ScaleType = Enum.ScaleType.Stretch
        x += step
    end
end

-- One whole window + rail for a screen of this size. Returns the holder (a full-screen, input-transparent frame).
local function draw(shade: GuiObject, gui: GuiBase2d, spec: any): Frame
    local size = gui.AbsoluteSize
    local inset = if (gui :: any).IgnoreGuiInset == true then 0 else GuiService:GetGuiInset().Y
    local lay = spec.layout(size.X, size.Y, #spec.cards, inset)
    local holder = Art.box(shade, "KitWindowHolder", 0, 0, 0, 0, 30)
    holder.Size = UDim2.fromScale(1, 1)
    local win = lay.window
    -- the window (Active: a tap on its empty body never reaches the scrim, which would close the menu): kit frame + dark studded body
    local window = Art.box(holder, "KitWindow", win.x, win.y, win.w, win.h, 31)
    window.Active = true
    local studK = Kit2.BodyStuds * win.h / 517
    local body = Art.studded(window, "Body", Kit2.StripSlot, 0, 0, win.w, win.h, 31, Kit2.BodyCap, studK)
    local studs = if body then nil else Art.kit(window, "Studs", "toybox_studs_tile", Kit.StudInset.left, Kit.StudInset.top,
        win.w - Kit.StudInset.left - Kit.StudInset.right, win.h - Kit.StudInset.top - Kit.StudInset.bottom, 32)
    if not body then Art.kit(window, "Frame", "toybox_panel_frame", 0, 0, win.w, win.h, 31) end
    if studs then
        studs.ScaleType, studs.TileSize = Enum.ScaleType.Tile, UDim2.fromOffset(Kit.StudTile / 2, Kit.StudTile / 2)
        local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, Kit.StudCorner), studs
    end
    -- the header strip, the title at the left, the X at the right (inside the strip, as approved)
    local hi = lay.headerInset
    local headerW = win.w - 2 * hi
    local header = Art.box(window, "KitHeader", hi, hi, headerW, lay.headerH, 33)
    local xInset = math.floor((lay.headerH - lay.close) / 2)
    local closeX = headerW - xInset - lay.close
    if not header2(header, spec.colour, headerW, lay.headerH) then header1(header, spec.colour, headerW, lay.headerH, closeX + math.floor(lay.close / 2)) end
    local title = Art.words(header, "Title", spec.title, math.floor(lay.headerH * 0.2), -math.floor(lay.headerH * 0.04), headerW * 0.6, lay.headerH, lay.titleSize, 35)
    title.TextXAlignment = Enum.TextXAlignment.Left
    local closeId = Kit2.image(Slots.Images, Kit2.CloseSlot)
    if closeId then Art.picture(header, "CloseArt", closeId, closeX, xInset, lay.close, lay.close, 36)
    else Art.kit(header, "CloseArt", "toybox_close", closeX, xInset, lay.close, lay.close, 36) end
    Art.tap(header, "Close", closeX, xInset, lay.close, lay.close, 37, function() if spec.onClose then spec.onClose() end end)
    -- the cards
    for i, card in spec.cards do
        local r = lay.cards[i]
        if not r then break end
        KitCard.draw(window, r, card, lay)
    end
    if spec.rail then KitRail.draw(holder, lay.rail, spec.rail) end
    return holder
end

function W.open(body: GuiObject, spec: any): boolean
    local parts = require(script.Parent.ModalCompact).parts()
    if not parts then return false end
    if not Kit.ready(Slots.Images, "panel") then return false end -- the frame and the studded body are kit 1 pictures: never half a window
    local panel, gui = parts.panel, parts.gui
    local shade = panel.Parent
    if not shade or not shade:IsA("GuiObject") then return false end
    local mark = Instance.new("Frame")
    mark.Name, mark.BackgroundTransparency, mark.Size, mark.Parent = "KitWindowMark", 1, UDim2.fromOffset(0, 0), body
    local holder: Frame? = nil
    local function redraw()
        if holder then holder:Destroy() end
        holder = draw(shade, gui, spec)
    end
    panel.Visible = false
    redraw()
    local conns: {RBXScriptConnection} = {}
    table.insert(conns, gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(redraw))
    local function light() if shade.BackgroundTransparency < Rules.Cover then shade.BackgroundTransparency = Rules.Cover end end
    light()
    table.insert(conns, shade:GetPropertyChangedSignal("BackgroundTransparency"):Connect(light))
    -- the world behind the window is blurred (14 px, once the open tween is done; the close tween takes it down as for every menu) and the
    -- HUD is hidden, like the approved one
    local unveil = veil(gui :: ScreenGui)
    task.delay(0.2, function()
        local blur = game:GetService("Lighting"):FindFirstChild("BeDinoModalBlur")
        if mark.Parent and shade.Visible and blur and blur:IsA("BlurEffect") and blur.Size > 0 then blur.Size = Rules.Blur end
    end)
    -- the menu closed (X, a tap outside, travel): the body keeps its children until the next open(), so the marker goes now (HUD back at once)
    table.insert(conns, shade:GetPropertyChangedSignal("Visible"):Connect(function() if not shade.Visible then mark:Destroy() end end))
    mark.Destroying:Connect(function()
        for _, c in conns do c:Disconnect() end
        unveil()
        if holder then holder:Destroy() holder = nil end
        panel.Visible = true
    end)
    return true
end

return W
