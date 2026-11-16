--!strict
-- BD-1234 (docs/242 benchmark gap 19, "nests take 3 h; hits remind players"): ONLY while Config.PlayCuesEnabled is on (flag off: this script
-- returns on its first lines and nothing changes). When a nest egg finishes while the player is in the game:
--   * one toast through the existing stack (Toasts.notify): "Your egg is ready!" with the registered nest icon; at home a tap opens the eggs
--     (the same path as the welcome-back card: the cave-hub stall trip);
--   * a number badge (a small chip, Shared/ChipStyle) on the EGGS button of the rail while eggs are ready.
-- The first reading after the join never toasts (the welcome-back card, BD-1168, owns that moment). In game only: Roblox experience notifications
-- need Creator Hub setup on the owner's account (docs/160 s2: account settings need the owner), so they are not used. Client presentation only.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).PlayCuesEnabled ~= true then return end

local Rules = require(Shared:WaitForChild("PlayCuesRules"))
local Chip = require(Shared:WaitForChild("ChipStyle"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local NestQueue = require(Shared:WaitForChild("NestQueue"))
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))
local Toasts = require(script.Parent:WaitForChild("Toasts"))

local player = Players.LocalPlayer
local gui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI")
local SOUND = "level_up" -- the registered soft reward cue a nest already uses (WelcomeBack.Sound); no new sound

local function runState(): any
    local character = player.Character
    return if character then character:GetAttribute("RunState") else nil
end

local function readyNests(): number
    local ok, list = pcall(function() return HttpService:JSONDecode(PrivateState.str("NestsJson", "[]")) end)
    if not ok or typeof(list) ~= "table" then return 0 end
    return Rules.readyCount(NestQueue.project(list, math.floor(workspace:GetServerTimeNow()), Config.NestIncubationSeconds))
end

local function openEggs()
    if runState() ~= "Sanctuary" then return end
    require(script.Parent:WaitForChild("HubTravelClient")).press("eggs", true)
end

-- The badge: a small chip in the accent green (never red: red is only the X, style rule R3) on the top-right corner of the EGGS rail button.
-- It is NOT a child of the button (the rail lays out every child of its buttons, RailRun.place): it sits in its own layer of the HUD and
-- follows the button's corner every tick.
local badgeLayer = Instance.new("Frame")
badgeLayer.Name, badgeLayer.BackgroundTransparency, badgeLayer.Size, badgeLayer.ZIndex = "EggReadyBadges", 1, UDim2.fromScale(1, 1), 30
badgeLayer.Parent = gui
local badge, badgeText = Chip.new(badgeLayer, {name = "ReadyBadge", fill = Theme.Colors.accent, size = UDim2.fromOffset(30, 30), anchor = Vector2.new(0.5, 0.5),
    z = 31, text = "", textInset = 3})
badge.Visible = false
local found: {GuiObject} = {}
local foundAt = -math.huge
local function eggButton(): GuiObject?
    if os.clock() - foundAt >= 5 then -- the rail is built once; look again every few seconds, not every tick
        foundAt, found = os.clock(), {}
        for _, item in gui:GetDescendants() do
            if item:IsA("GuiButton") and item:GetAttribute("Destination") == "eggs" then table.insert(found, item) end
        end
    end
    for _, button in found do
        if button.Parent and button.Visible then return button end
    end
    return nil
end
local function showBadge(count: number)
    local words = Rules.badgeText(count)
    local button = if words ~= "" then eggButton() else nil
    badge.Visible = button ~= nil
    if not button then return end
    badgeText.Text = words
    local corner = button.AbsolutePosition - badgeLayer.AbsolutePosition + Vector2.new(button.AbsoluteSize.X - 6, 4)
    badge.Position = UDim2.fromOffset(corner.X, corner.Y)
end

task.spawn(function()
    while not Toasts.layer and gui.Parent do task.wait(0.5) end -- Bootstrap attaches the toast stack at start; a bounded wait in practice
    while not PrivateState.isReady() and gui.Parent do task.wait(0.5) end
    local previous: number? = nil
    local lastRead, count = -math.huge, 0
    while gui.Parent do
        if os.clock() - lastRead >= 1 then lastRead, count = os.clock(), readyNests() end
        if Rules.toastNow(previous, count) then
            local home = runState() == "Sanctuary"
            Toasts.notify(Rules.toastText(count), Theme.Colors.gold, {kind = "major", key = "egg_ready", icon = "egg_nest",
                body = if home then Rules.ToastBody else nil, seconds = Rules.ToastSeconds, action = if home then openEggs else nil})
            Sfx.playCue(SOUND)
        end
        previous = count
        showBadge(count)
        task.wait(0.25)
    end
end)
