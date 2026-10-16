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

local function drawControls(body: Instance, ctx: Context)
    ctx.label(body, "Camera", 0, TOP, 250, 48, 28).TextXAlignment = Enum.TextXAlignment.Left
    ctx.button(body, "RESET", 270, TOP, 180, 48, C.blue, function() ctx.cameraReset() ctx.notify("Camera reset", C.blue) end)
    choice(body, ctx, 1, "Jump button", Model.JumpSizes, SIZE_TEXT, Model.get().jumpSize, function(id) Model.set("jumpSize", id) ctx.open("settings") end)
end

-- Draws the tab bar and the active tab. Returns the active tab id; the Help tab is completed by the caller (guides, auto-open).
function Menu.build(body: Instance, ctx: Context): string
    for i, id in Model.Tabs do
        local b = ctx.button(body, Model.TabLabels[id], (i - 1) * 209, 0, 197, 48, if id == currentTab then C.purple else C.card, function()
            currentTab = id
            ctx.open("settings")
        end)
        b.Name = "Tab_" .. id
    end
    if currentTab == "sound" then drawSound(body, ctx)
    elseif currentTab == "look" then drawLook(body, ctx)
    elseif currentTab == "controls" then drawControls(body, ctx) end
    return currentTab
end

return Menu
