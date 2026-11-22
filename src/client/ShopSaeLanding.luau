--!strict
-- BD-1287 (docs/246 slice 1): with Config.MenusSaeFrameEnabled the Crystal Shop LANDING page is the owner's APPROVED art-kit shop window
-- (Design Board, page Phone UI, "Phone shop windows, built from the art kit"): the Toybox kit panel frame with the studs tile body, the kit
-- green header strip with "Crystal Shop" in big white outlined words and the kit red X, a gold "-- FEATURED --" heading over big kit rarity
-- cards (name, the picture, one short kid line, the kit green button with the crystal icon and the price; the grey kit button for a lock),
-- and the tabs OUTSIDE the window on the right as an icon with a white outlined word under it (Featured, Auras, Trails, Eggs, Potions).
-- Numbers: Shared/SaeFrameRules; kit slices: Shared/ToyboxKit. Tapping a card, its button or a tab opens that category page (the purchase
-- confirm there does the buying; no Robux path here). Code only places and slices uploaded pictures; it draws none of them (docs/72).
-- How it sits on the shared modal: the window is a sibling of the Bootstrap panel inside ModalScrim; while it shows, the panel and the HUD
-- are hidden, the cover is 6 % and the menus' blur stays on. A tiny marker in the panel body ties it to the screen: the next open() clears the body, the marker
-- is destroyed and everything (panel, cover, blur) goes back to the normal rules. Every other screen is untouched.
local GuiService = game:GetService("GuiService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Slots = require(Shared.AssetSlots)
local Art = require(Shared.ShopArt)
local Kit = require(Shared.ToyboxKit)
local Card = require(script.Parent.ShopKitCard)
local Rules = require(Shared.SaeFrameRules)
local Preview = require(Shared.ShopPreview)
local ProgressionConfig = require(Shared.ProgressionConfig)

local M = {}

local function rgb(t: {number}): Color3 return Color3.fromRGB(t[1], t[2], t[3]) end
local INK = rgb(Rules.Ink)

-- the kit parts every shop page builds from (client/ShopKitCard)
local holderFrame, kitPicture, picture, words, tapArea = Card.box, Card.kit, Card.picture, Card.words, Card.tap

-- The item picture of a featured card (uploaded, owner-picked art only), or the category picture.
local function itemPicture(tab: string, item: any): string?
    if item then
        if tab == "auras" then return Art.validId(Slots.Images["aura_" .. tostring(item.id)])
        elseif tab == "trails" then return Preview.trailIconId(ProgressionConfig.TrailIconAssetIds, item.id)
        elseif tab == "eggs" then return Art.eggProductId(Slots.Images) end
    end
    return Art.tileId(Slots.Images, tab)
end

-- The tab icons (uploaded): no "%" sale-tag picture exists, so Featured wears the crystal tab icon (the closest existing one).
local function tabIcon(tab: string): string?
    if tab == "featured" then return Art.tabIconId(Slots.Images, "crystals") end
    if tab == "potions" then return Art.validId(Slots.Images.potion_icon_speed_common) end
    return Art.tabIconId(Slots.Images, tab) or Art.tileId(Slots.Images, tab)
end

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

-- One whole window + rail for a screen of this size. Returns the holder (a full-screen, input-transparent frame).
local function draw(shade: GuiObject, gui: GuiBase2d, spec: any): Frame
    local size = gui.AbsoluteSize
    local featured = Rules.featured(spec.progress or {})
    local inset = if (gui :: any).IgnoreGuiInset == true then 0 else GuiService:GetGuiInset().Y
    local lay = Rules.layout(size.X, size.Y, #featured, inset)
    local holder = Instance.new("Frame")
    holder.Name, holder.BackgroundTransparency, holder.Size, holder.ZIndex, holder.Parent = "SaeShopLanding", 1, UDim2.fromScale(1, 1), 30, shade
    local win = lay.window
    local fi = lay.frameInset
    -- the window (Active: a tap on its empty body never reaches the scrim, which would close the menu): kit frame + studs tile
    -- the window: the kit panel frame with the kit studs tile body, as the approved one
    local window = holderFrame(holder, "SaeWindow", win.x, win.y, win.w, win.h, 31)
    window.Active = true
    kitPicture(window, "SaeFrame", "toybox_panel_frame", 0, 0, win.w, win.h, 31)
    local studs = kitPicture(window, "SaeStuds", "toybox_studs_tile", Kit.StudInset.left, Kit.StudInset.top,
        win.w - Kit.StudInset.left - Kit.StudInset.right, win.h - Kit.StudInset.top - Kit.StudInset.bottom, 32)
    if studs then
        studs.ScaleType, studs.TileSize = Enum.ScaleType.Tile, UDim2.fromOffset(Kit.StudTile / 2, Kit.StudTile / 2)
        local round = Instance.new("UICorner") round.CornerRadius, round.Parent = UDim.new(0, Kit.StudCorner), studs
    end
    -- the kit header strip (green), the title at the left, the kit X at the right
    local header = holderFrame(window, "SaeHeader", fi, fi, win.w - 2 * fi, lay.headerH, 33)
    local headerW = win.w - 2 * fi
    local xInset = math.floor((lay.headerH - 6 - lay.close) / 2)
    local closeX = win.w - 2 * fi - xInset - lay.close - 4
    kitPicture(header, "SaeHeaderStrip", Rules.HeaderSlot, 0, 0, headerW, lay.headerH, 33)
    -- the shine stripes across the stretched middle: crops of the same kit picture (one stripe each), at the header's own slice scale
    local headerId = Kit.image(Slots.Images, Rules.HeaderSlot)
    if headerId then
        local k = lay.headerH / Rules.HeaderStripeCrop.h
        -- the stripes run up to the X (the uploaded strip's right cap is lighter lower down; the X covers the rest of it)
        local x0, x1 = math.floor(Rules.HeaderCaps.left * k), closeX + math.floor(lay.close / 2)
        local band = holderFrame(header, "SaeHeaderStripes", x0, 0, math.max(0, x1 - x0), lay.headerH, 34)
        band.ClipsDescendants = true
        local step = Rules.HeaderStripeCrop.w * k
        local x = 0
        while x < x1 - x0 do
            local crop = Instance.new("ImageLabel")
            crop.Name, crop.BackgroundTransparency, crop.BorderSizePixel, crop.Image = "Stripe", 1, 0, headerId
            crop.ImageRectOffset, crop.ImageRectSize = Vector2.new(Rules.HeaderStripeCrop.x, 0), Vector2.new(Rules.HeaderStripeCrop.w, Rules.HeaderStripeCrop.h)
            crop.Position, crop.Size, crop.ZIndex, crop.Parent = UDim2.fromOffset(math.floor(x), 0), UDim2.fromOffset(math.ceil(step) + 1, lay.headerH), 34, band
            x += step
        end
    end
    local title = words(header, "SaeTitle", Rules.Title, 16, 0, win.w * 0.6, lay.headerH - 6, lay.titleSize, 35)
    title.TextXAlignment = Enum.TextXAlignment.Left
    kitPicture(header, "SaeCloseArt", "toybox_close", closeX, xInset, lay.close, lay.close, 36)
    tapArea(header, "SaeClose", closeX, xInset, lay.close, lay.close, 37, function() if spec.close then spec.close() end end)
    -- the gold section heading
    if lay.showHeading then
        local hd = lay.heading
        words(window, "SaeFeatured", Rules.Featured, hd.x, hd.y, hd.w, hd.h, lay.headingSize, 34, rgb(Rules.Gold))
    end
    -- the cards: three of the shared shop card (client/ShopKitCard, the approved Aura Shop card)
    local gem = Art.validId(require(Shared.UIIconAssets).amber) -- the orange crystal of the HUD counter (the approved buttons)
    for i, f in featured do
        local r = lay.cards[i]
        if not r then break end
        local tab = f.tab
        local item = f.item
        local line, rich = Rules.Lines[tab] or "", nil
        if tab == "auras" and item then line, rich = Rules.auraLine(item.growth) end
        Card.draw(window, r, {
            key = tab, slot = Rules.cardSlot(f), name = Rules.cardTitle(f, Art.Titles[tab] or tab),
            rarity = if tab == "eggs" then Rules.EggWord elseif item and item.rarity then item.rarity else nil,
            picture = itemPicture(tab, item), line = line, lineRich = rich,
            price = if f.state == "buy" then f.price else nil, word = Rules.buttonWord(f), grey = f.state == "locked" or f.state == "soon",
            gem = gem, onPick = function() spec.onPick(tab) end,
        }, lay)
    end
    -- the tabs outside the window: icon + white outlined word under it, no box; the selected one (Featured on this page) is bigger
    local rail = lay.rail
    for i, tab in Rules.RailTabs do
        local s = rail.slots[i]
        local selected = tab == (spec.selected or "featured")
        local iconSize = if selected then rail.selectedIcon else rail.icon
        local icon = tabIcon(tab)
        local cx = s.x + math.floor(s.w / 2)
        if icon then picture(holder, "SaeTabIcon_" .. tab, icon, cx - math.floor(iconSize / 2), s.y + rail.icon - iconSize, iconSize, 32) end
        words(holder, "SaeTabWord_" .. tab, Rules.RailWords[tab], s.x - 6, s.y + rail.icon, s.w + 12, rail.labelSize + 2, rail.labelSize, 32)
        local go: () -> ()
        if tab == "featured" then go = function() end
        elseif tab == "potions" then go = function() if spec.openPotions then spec.openPotions() end end
        else go = function() spec.onPick(tab) end end
        tapArea(holder, "SaeTab_" .. tab, s.x, s.y, s.w, s.h, 34, go)
    end
    return holder
end

-- body: the Bootstrap panel body; spec: ShopTiles.build's {tabs, info, progress, onPick(tab), close(), openPotions(), selected?}. Returns false
-- when the shared window is not attached yet or the kit is not bound (the caller then draws the old landing tiles).
function M.build(body: GuiObject, spec: any): boolean
    local parts = require(script.Parent.ModalCompact).parts()
    if not parts then return false end
    for _, group in {"header", "button", "card", "close", "panel"} do
        if not Kit.ready(Slots.Images, group) then return false end -- never half a kit
    end
    local panel, gui = parts.panel, parts.gui
    local shade = panel.Parent
    if not shade or not shade:IsA("GuiObject") then return false end
    local mark = Instance.new("Frame")
    mark.Name, mark.BackgroundTransparency, mark.Size, mark.Parent = "SaeLandingMark", 1, UDim2.fromOffset(0, 0), body
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

return M
