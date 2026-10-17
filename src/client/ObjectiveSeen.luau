--!strict
-- OB2 (docs/115): the one-time "the player opened a menu" report for a tutorial objective (T9 "Open the Fusion menu"). Behind
-- Config.ObjectivesEnabled (false in every committed build): with the flag off report() returns at once, looks up no remote and sends
-- nothing, and callers do not even require this module. It sends ONLY {action = "seen", id = <menu id>} through the existing
-- ObjectiveAction RemoteFunction: no amount, no objective id, no reward. The server decides everything (known id, once per profile,
-- player owns a dino, rate limit); a refusal is silent. FusionMenu is the only caller (tools/verify_objective_hooks.py and
-- tools/verify_objectives_panel.py check that).
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local ObjectiveSeen = {}

local finished: {[string]: boolean} = {} -- the server gave a definite answer for this id (this session)
local inFlight: {[string]: boolean} = {}

-- Reasons that are worth asking again on the next open (the answer says "not yet", not "never").
-- not_opened (BD-616): the menu's own request had not reached the server yet; asked once more below, then again on the next open.
local RETRY = {rate_limited = true, no_dino = true, profile_not_loaded = true, save_failed = true, lease_lost = true, not_opened = true}

function ObjectiveSeen.report(seenId: string)
    if Config.ObjectivesEnabled ~= true then return end
    if finished[seenId] or inFlight[seenId] then return end
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local remote = if folder then folder:FindFirstChild("ObjectiveAction") else nil -- exists only while the server flag is on
    if remote == nil or not remote:IsA("RemoteFunction") then return end
    inFlight[seenId] = true
    task.spawn(function() -- InvokeServer yields: the menu must not wait for it
        local ok, response = pcall(function() return (remote :: RemoteFunction):InvokeServer({action = "seen", id = seenId}) end)
        if ok and typeof(response) == "table" and response.reason == "not_opened" then
            task.wait(1.5) -- the menu's list request travels beside this one; give it time to land
            ok, response = pcall(function() return (remote :: RemoteFunction):InvokeServer({action = "seen", id = seenId}) end)
        end
        inFlight[seenId] = nil
        if ok and typeof(response) == "table" and (response.ok == true or RETRY[response.reason] ~= true) then finished[seenId] = true end
    end)
end

return ObjectiveSeen
