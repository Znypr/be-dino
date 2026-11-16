--!strict
-- BD-1228 (docs/242 gap 17): the HUD chip "Friend bonus +10%" while a Roblox friend is in the same server. ONLY while Config.FriendBonusEnabled
-- is on (playtest profile): otherwise this script returns on its first lines. The SERVER decides (FriendBonusService sets the owner-only value
-- FriendBonus, a percent, 0 = none); this file only shows it, one chunky tag (Chip.apply) on the right edge under the crystals, hidden while a menu is open.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config")) :: any
if Config.FriendBonusEnabled ~= true then return end

local Players = game:GetService("Players")
local F = require(Shared:WaitForChild("FriendBonus"))
local Chip = require(Shared:WaitForChild("ChipStyle"))
local Theme = require(Shared:WaitForChild("UITheme")) :: any
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))

local player = Players.LocalPlayer
local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder = "FriendBonusGui", false, 4
gui.Parent = player:WaitForChild("PlayerGui")
local holder = Instance.new("Frame")
holder.Name, holder.BackgroundTransparency, holder.Size = "Holder", 1, UDim2.fromScale(1, 1)
holder.Parent = gui

-- Right edge, under the crystals plate (the top centre holds the size bar and the goal line).
local chip, label = Chip.new(holder, {name = "FriendBonus", fill = Theme.Colors.accent, size = UDim2.fromOffset(196, 30),
    position = UDim2.new(1, -18, 0, 122), anchor = Vector2.new(1, 0), z = 3, text = ""})
chip.Visible = false

local ui: Instance? = nil
local refresh: () -> ()
task.spawn(function()
    ui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI", 60)
    local u = ui
    if u then u:GetAttributeChangedSignal("Screen"):Connect(function() refresh() end) end
    refresh()
end)

function refresh()
    local text = F.label(PrivateState.num("FriendBonus"))
    local u = ui
    local screen = if u then u:GetAttribute("Screen") else nil
    label.Text = text
    chip.Visible = text ~= "" and (screen == nil or screen == "")
end

PrivateState.onChanged("FriendBonus", function() refresh() end)
refresh()
