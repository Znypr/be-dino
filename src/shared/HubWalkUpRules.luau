--!strict
-- BD-289 (docs/104 s8, first part): pure rules for walking up to a station sign. A ProximityPrompt on each sign opens the
-- station at once; standing on the pad for 0.5 s opens it once; leaving the pad resets the dwell and closes nothing.
-- No Instances: HubWalkUpClient (client) and tools/verify_cave_gate.py run this same file. Behind Config.CaveHub.
local CaveHubLayout = require(script.Parent.CaveHubLayout)
local ClientRules = require(script.Parent.HubTravelClientRules)
local HubWalkUpRules = {}
HubWalkUpRules.DwellSeconds = 0.5
HubWalkUpRules.PromptDistance = 10 -- studs (docs/104 s8)
HubWalkUpRules.TriggerGap = 0.5 -- seconds between two opens, so a held or hammered prompt never spams
HubWalkUpRules.PromptHeight = 3 -- studs above the floor

local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end

-- station id -> rail destination (the existing open() / openFusion() name), only stations that have a menu.
local menuFor: {[string]: string} = {}
for destination, station in ClientRules.Stations do menuFor[station] = destination end
function HubWalkUpRules.destination(station: any): string?
    return if typeof(station) == "string" then menuFor[station] else nil
end

-- Stations that get a sign prompt, in layout order (layout x, z; world z = z + CaveHubLayout.CenterZ).
function HubWalkUpRules.stations(): {any}
    local out = {}
    for _, s in CaveHubLayout.get().stations do
        if menuFor[s.id] ~= nil then out[#out + 1] = s end
    end
    return out
end

-- The menu station whose pad (radius r) contains the WORLD point (x, z), or nil. Pads are >= 48 apart: at most one matches.
function HubWalkUpRules.padAt(x: any, z: any): string?
    if not finite(x) or not finite(z) then return nil end
    for _, s in HubWalkUpRules.stations() do
        if (x - s.x) ^ 2 + (z - CaveHubLayout.CenterZ - s.z) ^ 2 <= s.r ^ 2 then return s.id end
    end
    return nil
end

function HubWalkUpRules.newState(): any return {pad = nil, since = 0, opened = {}, lastOpen = -math.huge} end

-- One tick. `pad` = padAt(player). `canOpen` = at home, no trip running, no menu already open. Returns the station to
-- open, or nil. Leaving a pad resets everything for it; arriving by teleport calls note() so the dwell never reopens.
function HubWalkUpRules.step(state: any, pad: string?, canOpen: boolean, now: number): string?
    if pad ~= state.pad then
        if state.pad ~= nil then state.opened[state.pad] = nil end
        state.pad, state.since = pad, now
    end
    if pad == nil then return nil end
    if not canOpen then state.since = now return nil end -- the dwell counts only while a menu could open
    if state.opened[pad] or now - state.since < HubWalkUpRules.DwellSeconds then return nil end
    if now - state.lastOpen < HubWalkUpRules.TriggerGap then return nil end
    state.opened[pad], state.lastOpen = true, now
    return pad
end

-- A menu for `station` was opened some other way (teleport arrival, prompt): the pad dwell must not open it again.
function HubWalkUpRules.note(state: any, station: string, now: number)
    state.opened[station], state.lastOpen = true, now
end

-- ProximityPrompt activation. Returns true when the station should open now.
function HubWalkUpRules.trigger(state: any, station: any, canOpen: boolean, now: number): boolean
    if not canOpen or HubWalkUpRules.destination(station) == nil then return false end
    if state.opened[station] or now - state.lastOpen < HubWalkUpRules.TriggerGap then return false end
    HubWalkUpRules.note(state, station :: string, now)
    return true
end

return HubWalkUpRules
