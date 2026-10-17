--!strict
-- Settings menu v2 (BD-263, docs/103): four tabs Sound / Look / Controls / Help. Lives in its own module because
-- Bootstrap.client is at the 200-local limit; it only draws into the body (824 x 402) it is given, using the same
-- label/button helpers as every other menu. Changes go through SettingsModel (saved per player by SettingsSync.client).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local Model = require(Shared:WaitForChild("SettingsModel"))
local Mixer = require(Shared:WaitForChild("AudioMixer"))
local C = Theme.Colors

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

local ROW = 56 -- row pitch; every control is 48 px high (above the 44 px touch minimum)
local TOP = 64 -- first row under the tab bar
local LEVEL_TEXT = {full = "FULL", lite = "LITE", off = "OFF"}
local SIZE_TEXT = {small = "SMALL", normal = "NORMAL", big = "BIG"}

function Menu.tab(): string return currentTab end
function Menu.setTab(id: string) if table.find(Model.Tabs, id) then currentTab = id end end

local function toggle(body: Instance, ctx: Context, row: number, text: string, on: boolean, change: () -> ())
    ctx.label(body, text, 0, TOP + row * ROW, 400, 48, 28).TextXAlignment = Enum.TextXAlignment.Left
    local b = ctx.button(body, if on then "ON" else "OFF", 420, TOP + row * ROW, 160, 48, if on then C.accent else C.card, change)
    b.Name = "Toggle_" .. text
end

local function choice(body: Instance, ctx: Context, row: number, text: string, options: {string}, names: {[string]: string}, selected: string, pick: (string) -> ())
    ctx.label(body, text, 0, TOP + row * ROW, 250, 48, 28).TextXAlignment = Enum.TextXAlignment.Left
    for i, id in options do
        local b = ctx.button(body, names[id], 270 + (i - 1) * 180, TOP + row * ROW, 168, 48, if id == selected then C.accent else C.card, function() pick(id) end)
        b.Name = "Choice_" .. text .. "_" .. id
    end
end

local function drawSound(body: Instance, ctx: Context)
    local Volume = require(script.Parent.VolumeSliders)
    for i, key in Mixer.Order do
        Volume.row(body, key, 0, TOP + (i - 1) * ROW, 824, 25, function() Model.set(key, Mixer.get(key)) end)
    end
    local on = Theme.HatchSoundEnabled ~= false
    toggle(body, ctx, 3, "Hatch sound", on, function() Theme.HatchSoundEnabled = Theme.HatchSoundEnabled == false ctx.open("settings") end)
    ctx.button(body, "SOUND LAB", 0, TOP + 4 * ROW, 250, 48, C.blue, function() labOpen = true ctx.open("settings") end).Name = "Button_SoundLab"
    ctx.button(body, "RESET SOUND", 620, TOP + 3 * ROW, 204, 48, C.card, function()
        Mixer.reset()
        for _, key in Mixer.Order do Model.set(key, Mixer.get(key)) end
        ctx.open("settings")
    end)
end

local function drawLook(body: Instance, ctx: Context)
    local s = Model.get()
    choice(body, ctx, 0, "Effects", Model.Levels, LEVEL_TEXT, s.effects, function(id) Model.set("effects", id) ctx.open("settings") end)
    choice(body, ctx, 1, "Weather", Model.Levels, LEVEL_TEXT, s.weather, function(id) Model.set("weather", id) ctx.open("settings") end)
    toggle(body, ctx, 2, "Calm motion", s.calm, function() Model.set("calm", not Model.calm()) ctx.open("settings") end)
    toggle(body, ctx, 3, "Fast mode", Model.isFast(s), function() Model.set("fast", not Model.isFast(Model.get())) ctx.open("settings") end)
    ctx.label(body, "Fast mode: less sparkle for slow phones", 0, TOP + 4 * ROW, 824, 30, 20, C.gold)
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
    ctx.label(body, "Camera", 0, TOP, 250, 48, 28).TextXAlignment = Enum.TextXAlignment.Left
    ctx.button(body, "RESET", 270, TOP, 180, 48, C.blue, function() ctx.cameraReset() ctx.notify("Camera reset", C.blue) end)
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
        local row = ctx.label(body, line, 0, TOP + used * ROW + 2 + (i - 1) * 26, 824, 26, 19, C.text)
        row.Name = "ControlsLine" .. i
        row.TextXAlignment = Enum.TextXAlignment.Left
    end
end

-- Draws the tab bar and the active tab. Returns the active tab id; the Help tab is completed by the caller (guides, auto-open).
function Menu.build(body: Instance, ctx: Context): string
    local lab = currentTab == "sound" and labOpen
    -- The Sound lab is a page of its own: no tab bar under its BACK button (a purple tab sliver and a cut word showed through).
    for i, id in Model.Tabs do
        if lab then break end
        local b = ctx.button(body, Model.TabLabels[id], (i - 1) * 209, 0, 197, 48, if id == currentTab then C.purple else C.card, function()
            currentTab = id
            ctx.open("settings")
        end)
        b.Name = "Tab_" .. id
    end
    if lab then
        -- BD-081: Sound lab replaces the Sound tab body (the lab page has no tab bar); BACK returns to the sliders.
        require(script.Parent:WaitForChild("SoundLab")).draw(body, ctx, function() labOpen = false ctx.open("settings") end)
    elseif currentTab == "sound" then drawSound(body, ctx)
    elseif currentTab == "look" then drawLook(body, ctx)
    elseif currentTab == "controls" then drawControls(body, ctx) end
    return currentTab
end

return Menu
