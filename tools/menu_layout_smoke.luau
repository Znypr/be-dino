-- Offline menu-layout smoke (BD-1101, BD-1102, BD-1103; driven by tools/verify_menu_layout.py; docs/201).
-- The REAL ShopScreens (Crystal Shops, Potion Shop, the confirm pages), the REAL Toasts and the REAL TouchLayout / ModalCompact / PhoneScale run in the
-- geometry mock of tools/close_paths_smoke.luau (the datatypes and instances are copied in by the verifier at the marker line below), inside a tree shaped
-- like Bootstrap's: BeDinoUI > the HUD rail (under the menu) + ModalScrim > panel > header + body, and the toast stack above everything.
-- Every size is a ScreenGui AbsoluteSize (the Studio window minus the top bar). What is proved here are rectangles and the hit test of the mock, which
-- mirrors the engine's ZIndex rules (ModalClose.topAt). It shows nothing about drawing, the real font or Studio.
--   1. every shop tab, X and the first row of every shop page is the TOP thing at its centre (a rail button under it never gets the tap), and the raw-tap
--      route of HubTravelClient (the same decision, run on the REAL rail rectangles) never turns a tap on a tab into "close the menu and travel";
--   2. toasts never cover the rail, a menu's tab row, its X, or the first row of the page that is open;
--   3. layout slips of the shop pages at small sizes (price line under BUY, hint over a card row, BUY touching CANCEL, text cut).
-- @@PREFIX@@

local sources = MODULE_SOURCES
local loaded, stubs = {}, {}
local failures = 0
local function check(ok, message)
    if not ok then failures += 1 print("FAIL " .. message) end
    return ok
end
function methods.FindFirstAncestorOfClass(self, class)
    local cur = rawget(self, "__p").Parent
    while cur do
        if rawget(cur, "__p").ClassName == class then return cur end
        cur = rawget(cur, "__p").Parent
    end
    return nil
end
function methods.GetPropertyChangedSignal(self, property)
    local e = rawget(self, "__ev")
    e["prop:" .. property] = e["prop:" .. property] or signal()
    return e["prop:" .. property]
end
function methods.FireServer() end
function methods.PlayLocalSound() end
events.DescendantAdded, events.ChildAdded, events.OnClientEvent = true, true, true
workspace = {GetServerTimeNow = function() return 1000 end}
do local realNew = Instance.new Instance.new = function(class) local o = realNew(class) if class == "UIScale" then o.Scale = 1 end return o end end -- a UIScale starts at 1 like the engine
Rect = {new = function(x0, y0, x1, y1) return {Min = {X = x0, Y = y0}, Max = {X = x1, Y = y1}, Width = x1 - x0, Height = y1 - y0} end}

-- ===== stubs for the visual / network modules =====
local Theme = {MotionEnabled = true, Colors = {panel = color(.2, .2, .2), card = color(.3, .3, .3), outline = color(0, 0, 0), text = color(1, 1, 1), gold = color(1, 1, 0),
    purple = color(1, 0, 1), accent = color(0, 1, 0), blue = color(0, 0, 1), red = color(1, 0, 0)},
    RarityColors = {color(.6, .6, .6), color(.3, .8, .3), color(.3, .5, 1), color(.7, .3, 1), color(1, .8, .2), color(1, .3, .3)},
    ImageIds = {}, TextStyle = {apply = function() return inst("UIStroke") end}}
function Theme.decorate() end
function Theme.texture() end
function Theme.icon() return nil end
function Theme.animate(target, _, goals) for k, v in goals do target[k] = v end end
stubs.UITheme = Theme
stubs.Sfx = {play = function() end, playLayers = function() end, playCue = function() end}
stubs.ModelPreview = {add = function() return nil end}
stubs.ShopPreview = nil -- the real one (pure words)
stubs.DinosaurPreview = {add = function(parent) return inst("Frame", "Preview", parent) end}
stubs.EggAppearance = {}
stubs.EggOutcomeView = {add = function() end}
stubs.PotionArt = {icon = function() return nil end}
stubs.SecretSpeciesConfig = {indexOrder = function(base) return base end, name = function(id) return id end, readyIds = function() return {} end}
stubs.PrivateState = {get = function() return nil end, str = function(_, fallback) return fallback or "" end}
stubs.HudSettings = nil
local clientNames = {SettingsMenu = true, ClassRow = true, RailRun = true, ShopScreens = true, ShopTiles = true, ShopCards = true, ShopCard = true, ModalCompact = true, ModalClose = true, Toasts = true, PrivateState = true}
Services.Players = {LocalPlayer = inst("Folder", "LocalPlayer")}
Services.MarketplaceService = {}
Services.UserInputService = {InputBegan = inputBegan, TouchEnabled = false}
Services.HttpService = {JSONDecode = function() return {} end, GenerateGUID = function() return "guid" end}
Services.TweenService = {Create = function(_, target, _, goals) return {Play = function() for k, v in goals do target[k] = v end end, Cancel = function() end, Completed = signal()} end}
local remotes = inst("Folder", "BeDinoRemotes", Replicated)
inst("Folder", "ProgressionAction", remotes)
inst("Folder", "ProgressionResult", remotes)
local function register(name)
    local m = Instance.new("ModuleScript") m.Name = name
    m.Parent = if clientNames[name] then ClientFolder else SharedFolder
end
for name in sources do register(name) end
for name in stubs do register(name) end
local function requireModule(m)
    local name = m.Name
    if stubs[name] then return stubs[name] end
    if loaded[name] == nil then loaded[name] = sources[name](m, requireModule) end
    return loaded[name]
end
local ConfigReal = requireModule(SharedFolder.Config)
local PhoneScale = requireModule(SharedFolder.PhoneScale)
local TouchLayout = requireModule(SharedFolder.TouchLayout)
local HubRules = requireModule(SharedFolder.HubTravelClientRules)
local ModalCloseReal = requireModule(ClientFolder.ModalClose)
local function frames(n, dt) for _ = 1, n do now += dt or 1 / 30 runDue() heartbeat:Fire(dt or 1 / 30) end end

-- ===== geometry helpers =====
local function rectOf(o) return {x = o.AbsolutePosition.X, y = o.AbsolutePosition.Y, w = o.AbsoluteSize.X, h = o.AbsoluteSize.Y} end
local function inside(r, box, slack) slack = slack or .75 return r.x >= box.x - slack and r.y >= box.y - slack and r.x + r.w <= box.x + box.w + slack and r.y + r.h <= box.y + box.h + slack end
local function overlaps(a, b) return a.x < b.x + b.w - .5 and b.x < a.x + a.w - .5 and a.y < b.y + b.h - .5 and b.y < a.y + a.h - .5 end
local function describe(r) return string.format("%d,%d %dx%d", r.x + .5, r.y + .5, r.w + .5, r.h + .5) end
local function centerOf(o) local r = rectOf(o) return r.x + r.w / 2, r.y + r.h / 2 end
local function isGuiObject(o) return o:IsA("GuiObject") end

local SIZES = {
    {516, 481}, {848, 423}, {848, 481}, {844, 390}, {844, 354}, {667, 375}, {667, 339}, {500, 465}, {500, 400}, {740, 340}, {1156, 793}, {1445, 841},
}
local NAV = {"collection", "eggs", "fusion", "auras", "potions", "settings"} -- the rail, in Bootstrap's order (each button has a Destination attribute)
local ConfigHub = nil -- a copy of Config with the Cave hub on (RailRun and the rail rules only act with it)

-- ===== a HUD + modal shaped like Bootstrap's =====
local ModalCompact
local RailRun
local function buildWorld(viewW, viewH, touch, runState)
    loaded.ModalCompact = nil
    ModalCompact = requireModule(ClientFolder.ModalCompact)
    if ConfigHub == nil then ConfigHub = table.clone(ConfigReal) ConfigHub.CaveHub = true end
    loaded.RailRun, loaded.Config = nil, ConfigHub
    RailRun = requireModule(ClientFolder.RailRun)
    loaded.Config = ConfigReal
    local character = inst("Model", "Character")
    character:SetAttribute("RunState", runState or "Sanctuary")
    Services.Players.LocalPlayer.Character = character
    local gui = inst("ScreenGui", "BeDinoUI", PlayerGui, {ViewSize = Vector2.new(viewW, viewH), DisplayOrder = 0})
    local buttons = {}
    -- Bootstrap's scales(): the rail is laid out for the buttons that are shown (RailRun.count) and each one takes the next slot (RailRun.position)
    local rail0 = inst("Frame", "Rail", gui, {ZIndex = 2})
    inst("UIScale", "Scale", rail0, {Scale = 1})
    for i, dest in NAV do
        local b = inst("TextButton", "Rail_" .. dest, rail0, {ZIndex = 4})
        b:SetAttribute("Destination", dest)
        buttons[i] = b
    end
    local layout = TouchLayout.compute({width = viewW, height = viewH, touch = touch, navCount = RailRun.count(buttons), goals = true})
    local r = layout.rail
    rail0.Position, rail0.Size = UDim2.fromOffset(r.x, r.y), UDim2.fromOffset(r.w, r.h)
    rail0:FindFirstChild("Scale").Scale = r.scale
    local rail = rail0
    for i, b in buttons do
        local pos = RailRun.position(buttons, i, r.positions)
        b.Position, b.Size = UDim2.fromOffset(pos.x, pos.y), UDim2.fromOffset(r.button.w, r.button.h)
        b.Visible = not RailRun.hidden(b)
    end
    local wallet = inst("Frame", "Crystals", gui, {Position = UDim2.fromOffset(layout.crystal.x, layout.crystal.y), Size = UDim2.fromOffset(layout.crystal.w, layout.crystal.h), ZIndex = 5})
    inst("UIScale", "Scale", wallet, {Scale = layout.crystal.scale})
    local shade = inst("TextButton", "ModalScrim", gui, {Size = UDim2.fromScale(1, 1), ZIndex = 20, Visible = false})
    local panel = inst("Frame", "Panel", shade, {Size = UDim2.fromOffset(860, 520), AnchorPoint = Vector2.new(.5, .5), Position = UDim2.fromScale(.5, .5), ZIndex = 21, Active = true})
    local scale = inst("UIScale", "Scale", panel, {Scale = 1})
    local header = inst("Frame", "Header", panel, {Position = UDim2.fromOffset(4, 4), Size = UDim2.fromOffset(852, 78), ZIndex = 22})
    local heading = inst("TextLabel", "Heading", header, {Position = UDim2.fromOffset(22, 4), Size = UDim2.fromOffset(730, 68), ZIndex = 23, TextSize = 40})
    local body = inst("Frame", "Body", panel, {Position = UDim2.fromOffset(18, 98), Size = UDim2.fromOffset(824, 402), ZIndex = 23, BackgroundTransparency = 1})
    local closeButton = inst("TextButton", "X", header, {Text = "X", AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -2, 0, 1), Size = UDim2.fromOffset(80, 76), ZIndex = 24})
    ModalCompact.attach({gui = gui, panel = panel, header = header, heading = heading, body = body, closeButton = closeButton, scale = scale})
    ModalCompact.setClearLeft(TouchLayout.modalClearLeft(layout))
    return {gui = gui, layout = layout, rail = rail, buttons = buttons, wallet = wallet, shade = shade, panel = panel, header = header, heading = heading, body = body, x = closeButton, scale = scale}
end
local function visibleBox(world)
    local scroller = world.panel:FindFirstChild("BodyScroll")
    if scroller and scroller.Visible then return rectOf(scroller), true end
    return rectOf(world.body), false
end
local function railRects(world)
    local list = {}
    for _, b in world.buttons do
        local r = rectOf(b)
        if b.Visible then table.insert(list, {kind = "rail", destination = b:GetAttribute("Destination"), x = r.x, y = r.y, w = r.w, h = r.h, enabled = true}) end
    end
    return list
end

-- ===== the REAL shop screens in that world =====
local Colors = Theme.Colors
local function uiLabel(parent, text, x, y, w, h, size, col)
    return inst("TextLabel", "Label", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(w, h), Text = text, TextSize = size, BackgroundTransparency = 1,
        TextWrapped = true, ZIndex = parent.ZIndex + 1, TextColor3 = col or Colors.text})
end
local function uiBox(parent, x, y, w, h, col, z) return inst("Frame", "Box", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(w, h), BackgroundColor3 = col, ZIndex = z}) end
local function uiButton(parent, text, x, y, w, h, col, callback)
    local b = inst("TextButton", "Button", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(w, h), BackgroundColor3 = col, Text = text, TextSize = 23, ZIndex = parent.ZIndex + 2})
    b.Activated:Connect(function() callback() end)
    return b
end
local function uiArt(parent, _, x, y, size) return inst("Frame", "Art", parent, {Position = UDim2.fromOffset(x, y), Size = UDim2.fromOffset(size, size), ZIndex = parent.ZIndex + 1}) end
local function mountShop(world, state)
    loaded.ShopScreens, loaded.ShopTiles = nil, nil
    Services.UserInputService.TouchEnabled = state.touch
    local Shop = requireModule(ClientFolder.ShopScreens)
    local ShopTiles = requireModule(ClientFolder.ShopTiles)
    ShopTiles.landing = false
    local label, box, button, art = uiLabel, uiBox, uiButton, uiArt
    local shop = {Shop = Shop, ShopTiles = ShopTiles, name = "auras"}
    local values = {Crystals = state.crystals or 1000000, AccountLevel = state.level or 1, ActiveChestCount = 0, QueuedEggsWaiting = 0}
    local profile = {crystals = values.Crystals, auras = {meadow = true}, trails = {}, potions = state.potions or {}, buffs = {}, equippedAura = "meadow", conditionLevel = 0, perks = {}}
    local function open(name)
        shop.name = name
        world.body:ClearAllChildren()
        Shop.render(name)
        ModalCompact.enforce()
    end
    Shop.attach({body = world.body, heading = world.heading, header = world.header, label = label, box = box, button = button, art = art, open = open, notify = function() end,
        viewportScale = function() return ModalCompact.model().scale end, num = function(n) return values[n] or 0 end, str = function(_, fallback) return fallback or "" end,
        decoded = function(_, fallback) return {} end, progression = function() return profile end, render = open, active = function() return shop.name end})
    shop.open = open
    return shop
end

local function showMenu(world)
    world.shade.Visible = true
    ModalCompact.layout()
    world.body.AnchorPoint, world.body.Position = Vector2.zero, ModalCompact.place(true, false)
end

-- tab button of the shop by its text
local function tabsOf(world)
    local out = {}
    for _, d in world.body:GetChildren() do
        if d:IsA("TextButton") and d.Position.Y.Offset <= 4 and d.Size.X.Offset == 155 then table.insert(out, d) end
    end
    return out
end

-- ===== 1. BD-1101: every shop tab, X and the first row can be tapped, the rail under them never gets the tap =====
local function railOver(world, ctrl) -- the rail rectangles that lie under the control's centre (the 500 px case)
    local cx, cy = centerOf(ctrl)
    local hits = {}
    for _, r in railRects(world) do
        if cx >= r.x and cx <= r.x + r.w and cy >= r.y and cy <= r.y + r.h then table.insert(hits, r.destination) end
    end
    return hits
end
local function routeOf(world, x, y)
    return HubRules.routeScrimTap(true, true, x, y, railRects(world), ModalCloseReal.onBackdrop(PlayerGui, x, y))
end
local function onTop(ctrl)
    local cx, cy = centerOf(ctrl)
    local top = ModalCloseReal.topAt(PlayerGui, cx, cy)
    return top == ctrl or (top ~= nil and top:IsDescendantOf(ctrl)), top
end

local TABS = {"auras", "trails", "eggs", "crystals"}
local overRail = 0
for _, touch in {false, true} do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        local world = buildWorld(w, h, touch)
        local shop = mountShop(world, {touch = touch})
        showMenu(world)
        shop.open("auras")
        local tag = string.format("Shop %dx%d%s", w, h, if touch then " touch" else "")
        local tabs = tabsOf(world)
        if check(#tabs == #TABS, tag .. ": the shop draws its " .. #TABS .. " tabs (" .. #tabs .. ")") then
            local vis = visibleBox(world)
            for i, tab in tabs do
                local ok, top = onTop(tab)
                check(ok, string.format("%s: the hit test at the centre of tab %s returns %s", tag, tab.Text, if top then top.Name else "nothing"))
                check(inside(rectOf(tab), vis), string.format("%s: tab %s (%s) is inside the visible body (%s)", tag, tab.Text, describe(rectOf(tab)), describe(vis)))
                local r = rectOf(tab)
                check(r.w >= 44 - .5 and r.h >= 44 - .5 or touch == false, string.format("%s: tab %s is a 44 px target on a touch screen (%s)", tag, tab.Text, describe(r)))
                if #railOver(world, tab) > 0 then overRail += 1 end
                local cx, cy = centerOf(tab)
                check(routeOf(world, cx, cy) == nil, string.format("%s: a tap on tab %s is routed to the rail button under it (it closes the shop and travels)", tag, tab.Text))
                -- the Studio picture (docs/199, 367 and 369): the rail at x 151..309, y 12..104 over the tab row at 500 x 465
                local studio = {{kind = "rail", destination = "auras", x = 151, y = 12, w = 158, h = 44, enabled = true}, {kind = "rail", destination = "eggs", x = 151, y = 60, w = 158, h = 44, enabled = true}}
                check(HubRules.routeScrimTap(true, true, cx, cy, studio, ModalCloseReal.onBackdrop(PlayerGui, cx, cy)) == nil,
                    string.format("%s: a tap on tab %s is routed to the Studio rail of picture 367", tag, tab.Text))
                if i > 1 then check(not overlaps(rectOf(tabs[i - 1]), r), string.format("%s: tabs %s and %s touch each other", tag, tabs[i - 1].Text, tab.Text)) end
            end
            -- X and the heading strip
            local ok, top = onTop(world.x)
            check(ok, string.format("%s: X is the top thing at its centre (%s)", tag, if top then top.Name else "nothing"))
            local xc, yc = centerOf(world.x)
            check(routeOf(world, xc, yc) == nil, tag .. ": a tap on X is routed to the rail")
            -- control: the bare backdrop over a rail button still travels (BD-382)
            local rail = rectOf(world.buttons[1])
            local bx, by = 3, 3
            if ModalCloseReal.onBackdrop(PlayerGui, bx, by) then
                local viaClient = routeOf(world, bx, by)
                local toRail = HubRules.routeScrimTap(true, true, rail.x + 2, rail.y + 2, railRects(world), true)
                check(toRail ~= nil, tag .. ": a tap on the bare backdrop over a rail button still travels")
                check(viaClient == nil or viaClient.kind == "rail" or viaClient.kind == "chip", tag .. ": route shape")
            end
        end
        world.gui:Destroy()
    end
end
check(overRail > 0, "the sizes must include at least one where a tab really lies over a rail button (else the check proves nothing)")


-- ===== 2. BD-1102: toasts never cover the rail, a menu's tab row, X or its first row =====
local function mountToasts(world)
    loaded.Toasts = nil
    local Toasts = requireModule(ClientFolder.Toasts)
    Toasts.attach({gui = world.gui, shade = world.shade, box = uiBox, label = uiLabel, art = uiArt, motion = function() return false end})
    -- what Bootstrap publishes (the wallet plates) and HudV2.layout (the rail)
    local wp = TouchLayout.walletPlates(world.layout)
    Toasts.layer:SetAttribute("WalletRect", Rect.new(wp.x, wp.y, wp.x + wp.w, wp.y + wp.h))
    local r = world.layout.rail
    world.gui:SetAttribute("RailRect", Rect.new(r.x, r.y, r.x + r.w * r.scale, r.y + r.h * r.scale))
    Toasts.scale.Scale = world.layout.toastScale
    return Toasts
end
local function pushToasts(Toasts)
    for i, text in {"Follow the glow", "Done!", "Level 2!"} do
        Toasts.notify(text, Colors.red, {key = "k" .. i}) -- a red toast is a warning: no 1.5 s throttle, never held back by a menu
    end
    frames(4)
end
local function toastCards(Toasts)
    local out = {}
    for _, c in Toasts.layer:GetChildren() do
        if c:IsA("Frame") and c.Visible then table.insert(out, c) end
    end
    return out
end
local function firstRow(world, page)
    local out = {}
    for _, tab in tabsOf(world) do table.insert(out, tab) end
    for _, d in world.body:GetChildren() do
        if d:IsA("GuiObject") and d.Visible and (d.Name == "ForDinoHeader" or string.find(d.Name, "AuraCard_", 1, true) or string.find(d.Name, "TrailCard_", 1, true)) then table.insert(out, d) end
    end
    local scroller = world.body:FindFirstChild("PotionScroll")
    if scroller then
        for _, d in scroller:GetChildren() do
            if d:IsA("Frame") and d.Position.Y.Offset == 0 then table.insert(out, d) end -- the first row of potion cards (name, price, BUY)
        end
        local restock = nil
        for _, d in world.body:GetChildren() do if d:IsA("TextLabel") and d.Position.Y.Offset == 0 then restock = d end end
        if restock then table.insert(out, restock) end
    end
    return out
end
local toastsSeenAt = {}
for _, touch in {false, true} do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        local tagBase = string.format("Toast %dx%d%s", w, h, if touch then " touch" else "")
        -- (a) no menu open: the stack is clear of the rail, the Crystals plate and the goal line, and on the canvas
        do
            local world = buildWorld(w, h, touch)
            local Toasts = mountToasts(world)
            pushToasts(Toasts)
            local cards = toastCards(Toasts)
            check(#cards == 3, tagBase .. ": three cards show with no menu (" .. #cards .. ")")
            local avoid = {{"the rail", rectOf(world.rail)}, {"the Crystals plate", rectOf(world.wallet)}}
            for _, b in world.buttons do if b.Visible then table.insert(avoid, {"rail button " .. b.Name, rectOf(b)}) end end
            local g = world.layout.goals
            if g then table.insert(avoid, {"the goal line", {x = g.x, y = g.y, w = g.w, h = g.h}}) end
            for _, card in cards do
                local r = rectOf(card)
                check(r.x >= -.5 and r.x + r.w <= w + .5 and r.y >= -.5 and r.y + r.h <= h + .5, string.format("%s: a toast card (%s) is not on the canvas %dx%d", tagBase, describe(r), w, h))
                for _, a in avoid do
                    check(not overlaps(r, a[2]), string.format("%s: a toast card (%s) covers %s (%s)", tagBase, describe(r), a[1], describe(a[2])))
                end
            end
            world.gui:Destroy()
        end
        -- (a2) a rail taller than the plates (40% of the window high): the stack still clears it
        do
            local world = buildWorld(w, h, touch)
            local Toasts = mountToasts(world)
            local r = world.layout.rail
            local tall = math.min(170, math.floor(h * 0.4))
            world.gui:SetAttribute("RailRect", Rect.new(r.x, r.y, r.x + r.w, r.y + tall))
            pushToasts(Toasts)
            for _, card in toastCards(Toasts) do
                local c = rectOf(card)
                check(not overlaps(c, {x = r.x, y = r.y, w = r.w, h = tall}) or c.x + c.w <= r.x or c.x >= r.x + r.w, string.format("%s: a toast card (%s) covers a tall rail (%s)", tagBase, describe(c), describe({x = r.x, y = r.y, w = r.w, h = tall})))
                check(c.y + c.h <= h + .5 and c.x >= -.5 and c.x + c.w <= w + .5, string.format("%s: with a tall rail the toast card (%s) leaves the canvas", tagBase, describe(c)))
            end
            world.gui:Destroy()
        end
        -- (b) a menu is open: one card, never over X, the heading, the tab row or the first row; a tap on an edge card goes to the menu
        for _, page in {"auras", "trails", "potions", "auraConfirm"} do
            local world = buildWorld(w, h, touch)
            local shop = mountShop(world, {touch = touch, potions = {speed_common = 2}})
            showMenu(world)
            shop.open("auras")
            if page == "trails" then for _, tab in tabsOf(world) do if tab.Text == "TRAILS" then tab.Activated:Fire() end end
            elseif page ~= "auras" then shop.open(page) end
            ModalCompact.enforce()
            local Toasts = mountToasts(world)
            pushToasts(Toasts)
            local tag = string.format("%s, menu on %s", tagBase, page)
            local cards = toastCards(Toasts)
            if check(#cards == 1, tag .. ": exactly one card shows with a menu open (" .. #cards .. ")") then
                local r = rectOf(cards[1])
                toastsSeenAt[Toasts.place.where] = (toastsSeenAt[Toasts.place.where] or 0) + 1
                check(r.x >= -.5 and r.x + r.w <= w + .5 and r.y >= -.5 and r.y + r.h <= h + .5, string.format("%s: the toast card (%s) is not on the canvas", tag, describe(r)))
                local forbidden = {{"X", rectOf(world.x)}, {"the heading", rectOf(world.heading)}}
                for _, d in firstRow(world, page) do
                    local fr = rectOf(d)
                    if d.Name ~= "Label" and not d:IsA("TextButton") and d.Name ~= "ForDinoHeader" then
                        -- a card of the first row: its top 60% (name, chips, picture, price) stays free; the BUY button at the bottom stays tappable (a toast
                        -- along the bottom edge lets taps through) and is what the player just pressed
                        fr = {x = fr.x, y = fr.y, w = fr.w, h = fr.h * 0.6}
                    end
                    table.insert(forbidden, {"'" .. (if d.Text ~= "" then d.Text else d.Name) .. "'", fr})
                end
                if page == "potions" or page == "auras" or page == "trails" then
                    for _, f in forbidden do
                        check(not overlaps(r, f[2]), string.format("%s: the toast card (%s, %s) covers %s (%s)", tag, describe(r), Toasts.place.where, f[1], describe(f[2])))
                    end
                end
                -- a tap on the middle of the card: dismisses it, or (along the bottom edge) goes to what is under it
                local cx, cy = r.x + r.w / 2, r.y + r.h / 2
                local top = ModalCloseReal.topAt(PlayerGui, cx, cy)
                local onToast = top ~= nil and top:IsDescendantOf(Toasts.layer)
                if Toasts.place.passThrough then
                    check(not onToast, tag .. ": along the bottom edge a tap on the toast must reach the menu under it (" .. (if top then top.Name else "nothing") .. ")")
                else
                    check(onToast, tag .. ": a tap on the toast dismisses it (" .. (if top then top.Name else "nothing") .. ")")
                end
            end
            world.gui:Destroy()
        end
    end
end
for _, where in {"above", "below", "edge"} do print("  toast place " .. where .. ": " .. (toastsSeenAt[where] or 0) .. " cases") end

-- ===== 5. BD-1105: in a run the "At home" buttons are hidden and the rail closes up =====
-- Hub (Sanctuary): all six buttons show in their old slots. Run (Active, and every other state that is not Sanctuary): exactly Dinos, Eggs, Fusion and Shop are
-- hidden, POTIONS and SETTINGS take the first two slots (no gap), stay 44 px, inside the canvas, and neither the toasts nor the rail rect overlap anything else.
local HOME_ONLY = {collection = true, eggs = true, fusion = true, auras = true}
for _, touch in {false, true} do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        local tag = string.format("Rail %dx%d%s", w, h, if touch then " touch" else "")
        local hub = buildWorld(w, h, touch, "Sanctuary")
        local shownHub = {}
        for _, b in hub.buttons do if b.Visible then table.insert(shownHub, b:GetAttribute("Destination")) end end
        check(#shownHub == 6, tag .. ": at home all six rail buttons show (" .. table.concat(shownHub, ",") .. ")")
        -- the hub slots are the ones the six-button layout gives (nothing moved)
        local sixLayout = TouchLayout.compute({width = w, height = h, touch = touch, navCount = 6, goals = true})
        for i, b in hub.buttons do
            local p = sixLayout.rail.positions[i]
            check(b.Position.X.Offset == p.x and b.Position.Y.Offset == p.y, string.format("%s: at home button %s sits in slot %d", tag, b.Name, i))
        end
        hub.gui:Destroy()
        for _, state in {"Active", "Ending", "Dead"} do
            local run = buildWorld(w, h, touch, state)
            local tagRun = tag .. " in a run (" .. state .. ")"
            local shown, hidden = {}, {}
            for _, b in run.buttons do
                local dest = b:GetAttribute("Destination")
                if b.Visible then table.insert(shown, b) else table.insert(hidden, dest) end
                check(b.Visible == not HOME_ONLY[dest], string.format("%s: button %s must be %s", tagRun, dest, if HOME_ONLY[dest] then "hidden" else "shown"))
            end
            if check(#shown == 2, tagRun .. ": two buttons stay (" .. #shown .. ")") then
                local a, b = rectOf(shown[1]), rectOf(shown[2])
                local lay = run.layout
                local p = lay.rail.positions
                check(shown[1].Position.X.Offset == p[1].x and shown[1].Position.Y.Offset == p[1].y, tagRun .. ": the first button takes slot 1")
                check(shown[2].Position.X.Offset == p[2].x and shown[2].Position.Y.Offset == p[2].y, tagRun .. ": the second button takes slot 2 (no gap)")
                check(not overlaps(a, b), tagRun .. ": the two buttons overlap")
                check(a.w >= 44 - .5 and a.h >= 44 - .5 and b.w >= 44 - .5 and b.h >= 44 - .5, tagRun .. ": the buttons are 44 px or more (" .. describe(a) .. " " .. describe(b) .. ")")
                local rr = rectOf(run.rail)
                check(inside(a, rr) and inside(b, rr), tagRun .. ": the buttons are inside the rail frame " .. describe(rr))
                check(rr.x >= -.5 and rr.y >= -.5 and rr.x + rr.w <= w + .5 and rr.y + rr.h <= h + .5, tagRun .. ": the rail is on the canvas")
                -- the toast stack and the wallet never lie over the two buttons
                local Toasts = mountToasts(run)
                pushToasts(Toasts)
                for _, card in toastCards(Toasts) do
                    local c = rectOf(card)
                    check(not overlaps(c, a) and not overlaps(c, b) and not overlaps(c, rr), string.format("%s: a toast card (%s) covers the rail (%s)", tagRun, describe(c), describe(rr)))
                    check(not overlaps(c, rectOf(run.wallet)), tagRun .. ": a toast covers the Crystals plate")
                end
                check(not overlaps(rr, rectOf(run.wallet)), tagRun .. ": the rail overlaps the Crystals plate")
            end
            check(RailRun.count(run.buttons) == 2 and RailRun.anyHidden(run.buttons), tagRun .. ": RailRun.count is 2")
            run.gui:Destroy()
        end
    end
end
-- the rail rules themselves, for every destination and run state
do
    local HubRulesNow = HubRules
    for _, dest in {"collection", "eggs", "fusion", "auras", "potions", "settings", "home", "other"} do
        for _, state in {"Sanctuary", "Active", "Ending", "Dead", "", false} do
            local want = HOME_ONLY[dest] == true and state ~= "Sanctuary" and state ~= "" and state ~= false
            check(HubRulesNow.hiddenInRun(dest, true, state) == want, string.format("hiddenInRun(%s, hub on, %s) must be %s", tostring(dest), tostring(state), tostring(want)))
            check(HubRulesNow.hiddenInRun(dest, false, state) == false, string.format("hiddenInRun(%s, hub OFF, %s) must be false (the default build is unchanged)", tostring(dest), tostring(state)))
        end
    end
end

-- ===== 6. BD-1099: the class icon on a Dino Index card and in the details list =====
do
    local ClassRow = requireModule(ClientFolder.ClassRow)
    local IndexProgress = requireModule(SharedFolder.IndexProgress)
    for _, scale in {1, .8, .571} do
        local lay = IndexProgress.cardLayout(scale, 326)
        local world = buildWorld(1156, 793, false)
        local cardBox = uiBox(world.body, 0, 0, 264, lay.cardHeight, Colors.card, 24)
        local nameLabel = uiLabel(cardBox, "Compy", 4, if lay.compact then 3 else 8, 256, if lay.compact then 26 else 35, 25)
        local rarityLabel = uiLabel(cardBox, "Common", 4, if lay.compact then 28 else 44, 256, if lay.compact then 20 else 25, 18)
        local tag = string.format("Index card (scale %.3f, %s)", scale, if lay.compact then "compact" else "tall")
        for _, species in {"compy", "pteranodon", "mosasaurus", "ankylosaurus"} do
            local badge = ClassRow.card(uiLabel, cardBox, species, "Ground - 3", lay.detailY, lay.compact, lay.heroY)
            local b, c = rectOf(badge), rectOf(cardBox)
            local icon = {x = b.x, y = b.y, w = 26, h = 26}
            check(badge:GetAttribute("Class") ~= nil and badge.Name == "ClassBadge", tag .. ": the badge is drawn for " .. species)
            check(inside(icon, c), string.format("%s: the badge icon %s is inside the card %s", tag, describe(icon), describe(c)))
            check(not overlaps(icon, rectOf(nameLabel)), tag .. ": the badge covers the dino name")
            check(not overlaps(icon, rectOf(rarityLabel)), tag .. ": the badge covers the rarity line")
            check(icon.y + 26 <= c.y + lay.detailY + .5, tag .. ": the badge is above the detail line")
            check(badge.ZIndex > cardBox.ZIndex + 1, tag .. ": the badge is above the picture")
            badge:Destroy()
        end
        world.gui:Destroy()
    end
    -- the details list: one row, replaced (never doubled), under the title
    local world = buildWorld(1156, 793, false)
    local list = uiBox(world.body, 0, 0, 300, 300, Colors.card, 24)
    ClassRow.row(list, "pteranodon", 1)
    ClassRow.row(list, "compy", 1)
    local rows = 0
    for _, d in list:GetChildren() do if d.Name == "ClassRow" then rows += 1 end end
    check(rows == 1, "the details list has exactly one class row (" .. rows .. ")")
    local row = list:FindFirstChild("ClassRow")
    check(row ~= nil and row.LayoutOrder == 1 and row:GetAttribute("Class") == "Ground" and row:FindFirstChild("ClassBadge") ~= nil, "the class row holds the badge of the species shown")
    world.gui:Destroy()
end

-- ===== 3. BD-1103: slips of the shop pages (overlaps, text that cannot fit its box) =====
-- Text cannot be measured in the mock (TextBounds is a constant), so a label's need is estimated: 0.5 em per character, lines wrap on the box width, 1.05 em per line.
local function textNeed(o)
    local size, len = o.TextSize, #o.Text
    if len == 0 then return 0, 1 end
    local width = o.AbsoluteSize.X / (o.AbsoluteSize.X > 0 and (rawget(o, "__p").Size.X.Offset > 0 and o.AbsoluteSize.X / rawget(o, "__p").Size.X.Offset or 1) or 1) -- design width of the box
    local lines = math.max(1, math.ceil(len * 0.5 * size / math.max(width, 1)))
    return lines * size * 1.05, lines
end
local function designSize(o) -- the box in the units its text size is in (the box divided by the cumulative scale)
    local _, _, k = layout(o)
    return o.AbsoluteSize.X / k, o.AbsoluteSize.Y / k
end
local function pageChecks(world, tag, opts)
    opts = opts or {}
    local vis = visibleBox(world)
    local things = {}
    for _, d in world.body:GetDescendants() do
        if isGuiObject(d) and d.Visible and d.AbsoluteSize.X > 0 and d.AbsoluteSize.Y > 0 then
            local isText = (d:IsA("TextLabel") or d:IsA("TextButton")) and #d.Text > 0
            if isText then table.insert(things, d) end
        end
    end
    for _, d in things do
        local r = rectOf(d)
        check(r.x >= vis.x - .75 and r.x + r.w <= vis.x + vis.w + .75, string.format("%s: '%s' (%s) leaves the visible body sideways (%s)", tag, d.Text, describe(r), describe(vis)))
        local dw, dh = designSize(d)
        if d:IsA("TextLabel") and not d.TextScaled then
            local need = 0
            local len = #d.Text
            local lines = math.max(1, math.ceil(len * 0.5 * d.TextSize / math.max(dw, 1)))
            need = lines * d.TextSize * 1.05
            check(need <= dh * 1.12 + 2, string.format("%s: the text '%s' needs about %d design px (%d line(s) at %d) but its box %s is %d", tag, d.Text, need, lines, d.TextSize, describe(r), dh))
        end
    end
    -- two things with text never overlap unless one is inside the other. A scrolling list is its own canvas: its rows are only compared with each other
    -- (the mock does not clip, so a row that is scrolled away would look like it lies under a button).
    local function canvasOf(d)
        local cur = rawget(d, "__p").Parent
        while cur and cur ~= world.body do
            if cur:IsA("ScrollingFrame") then return cur end
            cur = rawget(cur, "__p").Parent
        end
        return world.body
    end
    for i = 1, #things do
        for j = i + 1, #things do
            local a, b = things[i], things[j]
            if canvasOf(a) == canvasOf(b) and not (a:IsDescendantOf(b) or b:IsDescendantOf(a)) and overlaps(rectOf(a), rectOf(b)) then
                check(false, string.format("%s: '%s' (%s) overlaps '%s' (%s)", tag, a.Text, describe(rectOf(a)), b.Text, describe(rectOf(b))))
            end
        end
    end
end
for _, touch in {false, true} do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        for _, pageName in {"auras", "trails", "eggs", "crystals"} do
            local world = buildWorld(w, h, touch)
            local shop = mountShop(world, {touch = touch})
            showMenu(world)
            shop.open("auras")
            for _, tab in tabsOf(world) do
                if string.lower(tab.Text) == pageName then
                    tab.Activated:Fire()
                end
            end
            ModalCompact.enforce()
            pageChecks(world, string.format("Shop/%s %dx%d%s", pageName, w, h, if touch then " touch" else ""))
            world.gui:Destroy()
        end
        for _, pageName in {"auraConfirm", "eggPurchase", "oddsSimple", "eggOdds", "potions", "potionConfirm", "potionReplace"} do
            local world = buildWorld(w, h, touch)
            local shop = mountShop(world, {touch = touch, potions = {speed_common = 2}})
            showMenu(world)
            shop.open(pageName)
            ModalCompact.enforce()
            pageChecks(world, string.format("Shop/%s %dx%d%s", pageName, w, h, if touch then " touch" else ""))
            world.gui:Destroy()
        end
    end
end


-- ===== 3b. BD-1132: the Settings tabs (Look, Controls) at the small sizes =====
-- Studio round 8 (docs/205 picture 438) at 516 x 481: the Look tab's tab row touched the Effects row and the Calm motion button touched Fast mode.
local function mountSettings(world, tab)
    loaded.SettingsMenu = nil
    Services.UserInputService.TouchEnabled = false
    local Settings = requireModule(ClientFolder.SettingsMenu)
    Settings.setTab(tab)
    world.body:ClearAllChildren()
    Settings.build(world.body, {label = uiLabel, button = uiButton, open = function() end, notify = function() end, cameraReset = function() end})
    ModalCompact.enforce()
    return Settings
end
for _, touch in {false, true} do
    for _, size in SIZES do
        for _, tab in {"look", "controls"} do
            local world = buildWorld(size[1], size[2], touch)
            showMenu(world)
            mountSettings(world, tab)
            pageChecks(world, string.format("Settings/%s %dx%d%s", tab, size[1], size[2], if touch then " touch" else ""))
            local vis = visibleBox(world)
            local tabs = 0
            for _, d in world.body:GetChildren() do
                if string.sub(d.Name, 1, 4) == "Tab_" then
                    tabs += 1
                    local r = rectOf(d)
                    check(r.y >= vis.y - .75 and r.h >= 43.5, string.format("Settings/%s %dx%d: the tab '%s' (%s) is cut at the top of the body (%s) or under 44 px", tab, size[1], size[2], d.Text, describe(r), describe(vis)))
                end
            end
            check(tabs == 4, "Settings: four tabs")
            world.gui:Destroy()
        end
    end
end

-- ===== 4. a desktop window keeps the old design numbers (nothing above changes it) =====
for _, size in {{1156, 793}, {1445, 841}} do
    local tag = string.format("Desktop %dx%d", size[1], size[2])
    local function fresh(page)
        local world = buildWorld(size[1], size[2], false)
        local shop = mountShop(world, {touch = false, potions = {speed_common = 2}})
        showMenu(world)
        shop.open(page)
        return world, shop
    end
    local function byText(root, text) for _, d in root:GetDescendants() do if (d:IsA("TextLabel") or d:IsA("TextButton")) and d.Text == text then return d end end return nil end
    local world, shop = fresh("auras")
    local tabs = tabsOf(world)
    check(#tabs == 4 and tabs[1].Size.Y.Offset == 40, tag .. ": the shop tab row is 40 design px high")
    local card = nil
    for _, d in world.body:GetChildren() do if string.find(d.Name, "AuraCard_", 1, true) then card = d break end end
    check(card ~= nil and card.Size.Y.Offset == 250 and card.Position.Y.Offset == 92, tag .. ": aura cards are 250 high at y 92")
    local chipBox = card and card:FindFirstChild("Chip_Common")
    check(chipBox ~= nil and chipBox.Size.X.Offset == 104, tag .. ": the rarity chip is 104 wide")
    world.gui:Destroy()
    world, shop = fresh("auraConfirm")
    local cancel = byText(world.body, "CANCEL")
    check(cancel ~= nil and cancel.Position.Y.Offset == 337 and cancel.Size.Y.Offset == 45, tag .. ": the aura CANCEL button is at 337, 45 high")
    world.gui:Destroy()
    world, shop = fresh("potionConfirm")
    cancel = byText(world.body, "CANCEL")
    check(cancel ~= nil and cancel.Position.Y.Offset == 339 and cancel.Size.Y.Offset == 44, tag .. ": the potion CANCEL button is at 339, 44 high")
    world.gui:Destroy()
    -- BD-1132: the Settings Look tab keeps its old numbers on a desktop window (48 px controls, 56 px pitch, first row at 64)
    world = buildWorld(size[1], size[2], false)
    showMenu(world)
    mountSettings(world, "look")
    local calm, tabLook = byText(world.body, "Calm motion"), byText(world.body, "LOOK")
    check(calm ~= nil and calm.Position.Y.Offset == 64 + 2 * 56 and calm.Size.Y.Offset == 48, tag .. ": Settings Look rows are 56 apart from y 64, 48 high")
    check(tabLook ~= nil and tabLook.Size.Y.Offset == 48 and tabLook.Position.Y.Offset == 0, tag .. ": the Settings tab row is 48 high at y 0")
    world.gui:Destroy()
    world, shop = fresh("potions")
    local scroller = world.body:FindFirstChild("PotionScroll")
    local hint = byText(world.body, "Rarer potions show up less often.")
    local mine = byText(world.body, "Your potions (tap to use)")
    local use = byText(world.body, "Swift Sip x2  USE") or byText(world.body, "Speed Potion x2  USE")
    local first = nil
    for _, d in scroller:GetChildren() do if d:IsA("Frame") then first = d break end end
    check(first ~= nil and first.Size.Y.Offset == 132, tag .. ": a potion card is 132 high")
    check(hint ~= nil and hint.Position.Y.Offset == 278, tag .. ": the hint is at 278")
    check(mine ~= nil and mine.Position.Y.Offset == 298, tag .. ": the owned-potions title is at 298")
    local anyUse = nil
    for _, d in scroller:GetChildren() do if d:IsA("TextButton") then anyUse = d break end end
    check(anyUse ~= nil and anyUse.Position.Y.Offset == 322 and anyUse.Size.Y.Offset == 44, tag .. ": the first USE row is at 322, 44 high")
    world.gui:Destroy()
end

if failures > 0 then error(failures .. " menu-layout check(s) failed") end
print("Menu layout smoke passed: " .. #SIZES .. " sizes, " .. overRail .. " tabs over a rail button")
