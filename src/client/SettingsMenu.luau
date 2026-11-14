--!strict
-- Settings menu v2 (BD-263, docs/103): four tabs Sound / Look / Controls / Help. Lives in its own module because
-- Bootstrap.client is at the 200-local limit; it only draws into the body (824 x 402) it is given, using the same
-- label/button helpers as every other menu. Changes go through SettingsModel (saved per player by SettingsSync.client).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Model = require(Shared:WaitForChild("SettingsModel"))
local Mixer = require(Shared:WaitForChild("AudioMixer"))
local C = Theme.Colors
local Kit: any = nil -- the Toybox kit, required only while Theme.Toybox is on
local Layout: any = nil -- the Toybox layout helpers, required only while Theme.Toybox is on

local Menu = {}
local currentTab = "sound"
local labOpen = false -- BD-081: the Sound lab page (every sound, PLAY) replaces the Sound tab body

export type Context = {
    label: (Instance, string, number, number, number, number, number, Color3?) -> TextLabel,
    button: (Instance, string, number, number, number, number, Color3, () -> ()) -> TextButton,
    open: (string) -> (),
    notify: (string, Color3?) -> (),
    cameraReset: () -> (),
}

local ROW = 56 -- row pitch; every control is BTN design px high (48 on a desktop window: above the 44 px touch minimum)
local TOP = 64 -- first row under the tab bar
local BTN = 48 -- height of a control
-- BD-1132 (docs/205 picture 438): in a small window the body is drawn smaller than 1:1 (0.57 at 516 px wide), so a 48 design px control is only 27 px on screen and the
-- floor pass (ModalCompact) grew each one to 44 px around its middle: the tab row touched the Effects row and the rows touched each other. The numbers are now
-- worked out from the scale really drawn, as the shop pages do: controls are 44 px on screen, the pitch keeps an 8 px gap, the first row clears the tab bar.
-- At 1:1 (a desktop window) this gives 48 / 56 / 64, the old numbers exactly.
local function fitMetrics()
    local scale = 1
    local ok, s = pcall(function() return require(script.Parent:WaitForChild("ModalCompact")).bodyScale() end)
    if ok and typeof(s) == "number" and s > 0 then scale = s end
    BTN = math.max(48, math.ceil(44 / scale))
    ROW = BTN + 8
    TOP = BTN + 16
end
-- BD-1205 (docs/236, finding P-54d840): with Config.ToyboxUIEnabled (Theme.Toybox) the tabs are cream chips and every tab sits on ONE cream panel: rows =
-- label left | control column (sliders: label | slider | value), dark ink with no outline, one button height, a selected choice amber. T = the rects of
-- Kit.settingsLayout for the open tab (nil = the old layout, every line below runs as before).
local T: any = nil
local function rowY(row: number): number
    return if T then T.panel.y + Kit.PanelPad + row * T.pitch else TOP + row * ROW
end
local function ink(label: TextLabel): TextLabel
    if T then Layout.ink(label, "value") end
    return label
end
local function soundLabAllowed(): boolean
    local player = game:GetService("Players").LocalPlayer
    return Kit.soundLabVisible(game:GetService("RunService"):IsStudio(), player ~= nil and player:GetAttribute("IsAdmin") == true)
end
local LEVEL_TEXT = {full = "FULL", lite = "LITE", off = "OFF"}
local SIZE_TEXT = {small = "SMALL", normal = "NORMAL", big = "BIG"}

function Menu.tab(): string return currentTab end
function Menu.setTab(id: string) if table.find(Model.Tabs, id) then currentTab = id end end

local function rowLabel(body: Instance, ctx: Context, row: number, text: string, oldWidth: number)
    local l = if T then ctx.label(body, text, Kit.PanelPad, rowY(row), T.labelW, BTN, Kit.Type.heading) else ctx.label(body, text, 0, TOP + row * ROW, oldWidth, BTN, 28)
    l.TextXAlignment = Enum.TextXAlignment.Left
    ink(l).Name = "RowLabel"
end

local function toggle(body: Instance, ctx: Context, row: number, text: string, on: boolean, change: () -> ())
    rowLabel(body, ctx, row, text, 400)
    local b = if T then ctx.button(body, if on then "ON" else "OFF", T.controlX, rowY(row), Kit.Settings.toggleW, BTN, if on then C.accent else C.card, change)
        else ctx.button(body, if on then "ON" else "OFF", 420, TOP + row * ROW, 160, BTN, if on then C.accent else C.card, change)
    b.Name = "Toggle_" .. text
end

local function choice(body: Instance, ctx: Context, row: number, text: string, options: {string}, names: {[string]: string}, selected: string, pick: (string) -> ())
    rowLabel(body, ctx, row, text, 250)
    local count = math.max(#options, 1)
    local w = if T then math.min(168, math.floor((T.controlW - Kit.Gutter * (count - 1)) / count)) else 168
    for i, id in options do
        local x = if T then T.controlX + (i - 1) * (w + Kit.Gutter) else 270 + (i - 1) * 180
        local b = ctx.button(body, names[id], x, if T then rowY(row) else TOP + row * ROW, w, BTN, if id == selected then (if T then Layout.Amber else C.accent) else C.card, function() pick(id) end)
        b.Name = "Choice_" .. text .. "_" .. id
    end
end

local function drawSound(body: Instance, ctx: Context)
    local Volume = require(script.Parent.VolumeSliders)
    for i, key in Mixer.Order do
        local change = function() Model.set(key, Mixer.get(key)) end
        if T then
            Volume.row(body, key, Kit.PanelPad, rowY(i - 1) + (BTN - 40) // 2, T.width - 2 * Kit.PanelPad, 25, change, {labelW = T.labelW, valueW = Kit.Settings.valueW, textSize = Kit.Type.heading})
        else
            Volume.row(body, key, 0, TOP + (i - 1) * ROW, 824, 25, change)
        end
    end
    local on = Theme.HatchSoundEnabled ~= false
    toggle(body, ctx, 3, "Hatch sound", on, function() Theme.HatchSoundEnabled = Theme.HatchSoundEnabled == false ctx.open("settings") end)
    local function reset()
        Mixer.reset()
        for _, key in Mixer.Order do Model.set(key, Mixer.get(key)) end
        ctx.open("settings")
    end
    if T then
        ctx.button(body, "RESET SOUND", T.controlX + Kit.Settings.toggleW + Kit.Gutter, rowY(3), Kit.Settings.resetW, BTN, C.card, reset).Name = "Button_ResetSound"
        -- SOUND LAB is a test page: Studio and admins only (a player never sees it)
        if soundLabAllowed() then
            ctx.button(body, "SOUND LAB", T.controlX, rowY(4), Kit.Settings.resetW, BTN, C.card, function() labOpen = true ctx.open("settings") end).Name = "Button_SoundLab"
        end
    else
        ctx.button(body, "SOUND LAB", 0, TOP + 4 * ROW, 250, BTN, C.blue, function() labOpen = true ctx.open("settings") end).Name = "Button_SoundLab"
        ctx.button(body, "RESET SOUND", 620, TOP + 3 * ROW, 204, BTN, C.card, reset)
    end
end

local function drawLook(body: Instance, ctx: Context)
    local s = Model.get()
    choice(body, ctx, 0, "Effects", Model.Levels, LEVEL_TEXT, s.effects, function(id) Model.set("effects", id) ctx.open("settings") end)
    choice(body, ctx, 1, "Weather", Model.Levels, LEVEL_TEXT, s.weather, function(id) Model.set("weather", id) ctx.open("settings") end)
    toggle(body, ctx, 2, "Calm motion", s.calm, function() Model.set("calm", not Model.calm()) ctx.open("settings") end)
    toggle(body, ctx, 3, "Fast mode", Model.isFast(s), function() Model.set("fast", not Model.isFast(Model.get())) ctx.open("settings") end)
    if T then
        local note = ctx.label(body, "Fast mode: less sparkle for slow phones", Kit.PanelPad, rowY(4), T.width - 2 * Kit.PanelPad, 30, Kit.Type.body)
        note.TextXAlignment, note.Name = Enum.TextXAlignment.Left, "FastNote"
        Layout.ink(note, "label")
    else
        ctx.label(body, "Fast mode: less sparkle for slow phones", 0, TOP + 4 * ROW, 824, 30, 20, C.gold)
    end
end

-- BD-570 (docs/134 s13): the row "Gifts from: Everyone / Friends / Nobody". Drawn only with Config.GiftClaimEnabled and a GiftAction remote on the
-- server; the saved value is read through GiftAction and each pick is saved there (shown at once, put back if the save fails). Returns whether a row was drawn.
local function drawGifts(body: Instance, ctx: Context, row: number): boolean
    local Gifts = require(script.Parent:WaitForChild("GiftSettings"))
    if not Gifts.available() then return false end
    local GiftUi = require(Shared:WaitForChild("GiftUiModel"))
    local function redraw() if Gifts.rowShowing() then ctx.open("settings") end end
    choice(body, ctx, row, GiftUi.RowLabel, GiftUi.Options, GiftUi.OptionLabels, Gifts.controller().current(), function(id)
        task.spawn(function() if not Gifts.controller().choose(id) then redraw() end end)
        ctx.open("settings")
    end)
    Gifts.refresh(redraw)
    return true
end

local function drawControls(body: Instance, ctx: Context)
    rowLabel(body, ctx, 0, "Camera", 250)
    ctx.button(body, "RESET", if T then T.controlX else 270, rowY(0), 180, BTN, if T then C.card else C.blue, function() ctx.cameraReset() ctx.notify("Camera reset", C.blue) end)
    choice(body, ctx, 1, "Jump button", Model.JumpSizes, SIZE_TEXT, Model.get().jumpSize, function(id) Model.set("jumpSize", id) ctx.open("settings") end)
    -- BD-288 (docs/104 s7.6): only shown while the Cave hub is on; OFF = the rail just opens the menu, no teleport.
    -- BD-391/405 (docs/115 D22): with the perk flag on, the toggle shows only after the player bought Fast travel.
    local cfg = require(Shared:WaitForChild("Config"))
    if cfg.CaveHub and (cfg.FastTravelPerk ~= true or require(script.Parent:WaitForChild("HubTravelClient")).ownsFastTravel()) then
        toggle(body, ctx, 2, if cfg.FastTravelPerk == true then "Fast travel" else "Teleport to shops", Model.teleportShops(), function() Model.set("teleportShops", not Model.teleportShops()) ctx.open("settings") end)
    end
    -- BD-374: the keys (or phone controls) in two short lines under the last row; read from the real input code.
    local Config = require(Shared:WaitForChild("Config"))
    local used = 2 + (if Config.CaveHub then 1 else 0)
    if Config.GiftClaimEnabled == true and drawGifts(body, ctx, used) then used += 1 end -- BD-570: flag off = nothing drawn, nothing required, no remote call
    local lines = require(Shared:WaitForChild("FtueP1")).controlsLines(game:GetService("UserInputService").TouchEnabled, Config.CombatEnabled == true)
    for i, line in lines do
        local row = if T then ctx.label(body, line, Kit.PanelPad, rowY(used) + 2 + (i - 1) * 26, T.width - 2 * Kit.PanelPad, 26, Kit.Type.body) else ctx.label(body, line, 0, TOP + used * ROW + 2 + (i - 1) * 26, 824, 26, 19, C.text)
        row.Name = "ControlsLine" .. i
        row.TextXAlignment = Enum.TextXAlignment.Left
        if T then Layout.ink(row, "label") end
    end
end

-- Draws the tab bar and the active tab. Returns the active tab id; the Help tab is completed by the caller (guides, auto-open).
function Menu.build(body: Instance, ctx: Context): string
    fitMetrics()
    local lab = currentTab == "sound" and labOpen
    T = nil
    if Theme.Toybox and not lab then -- BD-1205: the cream chips + one cream panel (the Sound lab test page keeps the old look)
        Layout = require(Shared:WaitForChild("ToyboxLayout"))
        Kit = Layout.Kit
        local compact = require(script.Parent:WaitForChild("ModalCompact"))
        local rows = if currentTab == "sound" then (if soundLabAllowed() then 5 else 4) elseif currentTab == "look" then 5 elseif currentTab == "controls" then 6 else 1
        T = Kit.settingsLayout(compact.bodyScale(), compact.bodyWidth(), compact.bodyHeight(), rows)
        BTN = T.big
        local panel = Layout.panel(body :: GuiObject, "SettingsPanel", UDim2.fromOffset(T.panel.w, T.panel.h), UDim2.fromOffset(T.panel.x, T.panel.y))
        panel.Name = "SettingsPanel"
    end
    -- The Sound lab is a page of its own: no tab bar under its BACK button (a purple tab sliver and a cut word showed through).
    for i, id in Model.Tabs do
        if lab then break end
        local pick = function()
            currentTab = id
            ctx.open("settings")
        end
        if T then
            Layout.tabChip(body :: GuiObject, "Tab_" .. id, Model.TabLabels[id], UDim2.fromOffset(T.tabs[i].w, T.tabs[i].h), UDim2.fromOffset(T.tabs[i].x, T.tabs[i].y), id == currentTab, Kit.Type.heading, pick)
        else
            local b = ctx.button(body, Model.TabLabels[id], (i - 1) * 209, 0, 197, BTN, if id == currentTab then C.purple else C.card, pick)
            b.Name = "Tab_" .. id
        end
    end
    if lab then
        -- BD-081: Sound lab replaces the Sound tab body (the lab page has no tab bar); BACK returns to the sliders.
        require(script.Parent:WaitForChild("SoundLab")).draw(body, ctx, function() labOpen = false ctx.open("settings") end)
    elseif currentTab == "sound" then drawSound(body, ctx)
    elseif currentTab == "look" then drawLook(body, ctx)
    elseif currentTab == "controls" then drawControls(body, ctx) end
    return currentTab
end

-- BD-1205: the Help tab is drawn by SmallScreens with 824 px design coordinates. On the Toybox look it goes into a frame inset by the panel padding (scaled
-- to fit), on the cream panel; `inkHelp` makes its plain labels dark ink. Flag off (or another tab) = the body itself, nothing changes.
function Menu.helpHost(body: Instance): Instance
    if T == nil then return body end
    local host = Instance.new("Frame")
    host.Name, host.BackgroundTransparency, host.BorderSizePixel = "HelpHost", 1, 0
    host.Position, host.Size = UDim2.fromOffset(Kit.PanelPad, 0), UDim2.fromOffset(824, 402)
    host.ZIndex = if body:IsA("GuiObject") then body.ZIndex else 1
    local fit = Instance.new("UIScale")
    fit.Scale = (T.width - 2 * Kit.PanelPad) / 824
    fit.Parent = host
    host.Parent = body
    return host
end
function Menu.inkHelp(host: Instance)
    if T == nil then return end
    for _, child in host:GetChildren() do
        if child:IsA("TextLabel") then Layout.ink(child, "value") end
    end
end

return Menu
