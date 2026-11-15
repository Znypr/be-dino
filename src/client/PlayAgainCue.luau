--!strict
-- BD-1199 (docs/239): the soft "Run streak 3!" line when a run starts. Behind Config.PlayAgainEnabled (default false, on only in the
-- playtest profile): with the flag off attach returns at once, no connection, no read. The SERVER decides the streak (owner-only RunStreak,
-- set when the run begins, session-only); this file only shows it through the existing toast stack, from streak 2 on, once per run.
-- Never a warning, never a countdown. Words come from the pure Shared/PlayAgain (tools/verify_play_again.py).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config) :: any
local Rules = require(Shared.PlayAgain)
local Theme = require(Shared.UITheme)
local PrivateState = require(script.Parent.PrivateState)

local Cue = {}
local attached = false

-- notify = Bootstrap's toast function.
function Cue.attach(notify: any)
    if Config.PlayAgainEnabled ~= true or attached then return end
    attached = true
    PrivateState.onChanged("RunStreak", function(value: any)
        local text = Rules.text(value)
        if text then notify(text, Theme.Colors.gold) end
    end)
end

return Cue
