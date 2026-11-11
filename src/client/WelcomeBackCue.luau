--!strict
-- BD-1168 (docs/221 section 3 and 4): the client half of the welcome-back card. Behind Config.WelcomeBackEnabled (default false, on
-- only in the playtest profile): with the flag off attach returns at once, no thread, no read.
-- The SERVER decides how many nests finished while the player was away (owner-only value WelcomeBackNests, set once per join); this
-- file only shows ONE toast card for it, through the existing toast stack: "Your nest is ready!" / "2 nests are ready!" with the
-- registered nest icon. A tap on the card opens the Nests screen; it never blocks play and fades by itself (Rules.Seconds). The stack
-- holds a big-moment card back while a menu or the hatch reveal is open, so it never lands on top of one. Shown once per join.
-- All words and decisions are in the pure Shared/WelcomeBack (tools/verify_welcome_back.py); no new art, one registered soft cue.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config) :: any
local Rules = require(Shared.WelcomeBack)
local Sfx = require(Shared.Sfx)
local Theme = require(Shared.UITheme)
local PrivateState = require(script.Parent.PrivateState)

local Cue = {}
local attached = false

local function runState(): any
    local character = Players.LocalPlayer.Character
    return if character then character:GetAttribute("RunState") else nil
end

-- notify = Bootstrap's toast function; open = Bootstrap's menu opener (open("eggs") is the Nests and eggs screen).
function Cue.attach(notify: any, open: any)
    if Config.WelcomeBackEnabled ~= true or attached then return end
    attached = true
    local player = Players.LocalPlayer
    local function openNests()
        if not Rules.canOpen(runState()) then return end
        -- the same path as the OPEN EGGS button of Run Complete: with the cave hub on, the stall trip decides; otherwise the menu opens
        if not require(script.Parent.HubTravelClient).press("eggs", true) then open("eggs") end
    end
    task.spawn(function()
        local started = os.clock()
        local seenAt: number? = nil
        while os.clock() - started < 120 do -- a finite wait: the number arrives with the save, seconds after the join
            local count = PrivateState.num("WelcomeBackNests")
            if count > 0 and seenAt == nil then seenAt = os.clock() end
            if Rules.showNow({shown = false, count = count, worldReady = player:GetAttribute("WorldReady") == true,
                waited = if seenAt then os.clock() - seenAt else 0, runState = runState()}) then
                local card = Rules.card(count) :: any
                task.wait(1) -- let the loading screen finish its fade
                notify(card.text, Theme.Colors.gold, {kind = card.kind, key = card.key, icon = card.icon, body = card.body, seconds = card.seconds, action = openNests})
                Sfx.playCue(Rules.Sound)
                return -- once per join
            end
            task.wait(0.5)
        end
    end)
end

return Cue
