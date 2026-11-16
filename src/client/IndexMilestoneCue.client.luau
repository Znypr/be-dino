--!strict
-- BD-1230 (docs/242 benchmark gap 15): ONLY while Config.IndexMilestonesEnabled is on (flag off: this script returns on its first lines). When
-- the server granted a Dino Index milestone (a new step in the owner-only value IndexMilestonesJson, set by ProfileRepository after the hatch
-- transaction that reached it), one toast through the existing stack: "Dino Index 25%!" / "+50 Crystals" with the trophy icon and the
-- existing soft level_up cue. The first reading after the join never toasts (old steps are not news). The crystals themselves were already
-- added by the server; this script only shows. Client presentation only: nothing is stored, sent or decided.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).IndexMilestonesEnabled ~= true then return end

local Milestones = require(Shared:WaitForChild("IndexMilestones"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))
local Toasts = require(script.Parent:WaitForChild("Toasts"))

local gui = Players.LocalPlayer:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI")

local function steps(): {[number]: boolean}
    local ok, list = pcall(function() return HttpService:JSONDecode(PrivateState.str("IndexMilestonesJson", "[]")) end)
    return Milestones.granted(if ok then list else nil)
end

task.spawn(function()
    while not Toasts.layer and gui.Parent do task.wait(0.5) end -- Bootstrap attaches the toast stack at start
    while not PrivateState.isReady() and gui.Parent do task.wait(0.5) end
    local seen = steps()
    PrivateState.onChanged("IndexMilestonesJson", function()
        local now = steps()
        for _, step in Milestones.Steps do
            if now[step] and not seen[step] then
                Toasts.notify(Milestones.toast(step), Theme.Colors.gold, {kind = "major", key = "index_milestone_" .. step, icon = "trophy",
                    body = Milestones.toastBody(Milestones.Crystals[step]), seconds = 6})
                Sfx.playCue("level_up")
            end
        end
        seen = now
    end)
end)
