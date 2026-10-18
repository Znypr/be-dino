--!strict
-- BD-289 (docs/104 s8, OWNER 2026-10-16): pure rules for walking up to a station sign. A station NEVER opens by itself: only a
-- ProximityPrompt press opens it (key G, gamepad, 96 px tap). No dwell, no auto-open. No Instances. Behind Config.CaveHub.
local CaveHubLayout = require(script.Parent.CaveHubLayout)
local ClientRules = require(script.Parent.HubTravelClientRules)
local HubWalkUpRules = {}
HubWalkUpRules.PromptKey = "G" -- keyboard key (E is LEAP, F is BITE, C / B open menus)
-- BD-1017 (docs/180 option A, LEAD decision docs/115 C-52): with Config.ShopPromptBubbleEnabled the stall key is E (gamepad X), the keys every Roblox player knows.
-- E (Leap) and X do nothing else at home: Leap and bite work only in a run, a stall prompt exists only at home. PromptKey / L1 stay the flag-off values.
HubWalkUpRules.PromptKeyBubble = "E"
HubWalkUpRules.PromptGamepad = "ButtonL1"
HubWalkUpRules.PromptGamepadBubble = "ButtonX"
HubWalkUpRules.PromptButtonText = "Open"
HubWalkUpRules.PromptDistance = 10 -- studs (docs/104 s8)
HubWalkUpRules.TriggerGap = 0.5 -- seconds between two opens, so a held or hammered prompt never spams
HubWalkUpRules.PromptHeight = 3 -- studs above the floor

-- The keyboard key name and the gamepad button name of a stall prompt. bubbleOn = Config.ShopPromptBubbleEnabled (anything but true = the old G / L1).
function HubWalkUpRules.keyFor(bubbleOn: any): string
    return if bubbleOn == true then HubWalkUpRules.PromptKeyBubble else HubWalkUpRules.PromptKey
end
function HubWalkUpRules.gamepadFor(bubbleOn: any): string
    return if bubbleOn == true then HubWalkUpRules.PromptGamepadBubble else HubWalkUpRules.PromptGamepad
end

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

function HubWalkUpRules.newState(): any return {lastOpen = -math.huge} end

-- A menu for `station` was opened some other way (teleport arrival): a prompt press in the same instant is ignored.
function HubWalkUpRules.note(state: any, station: string, now: number)
    state.lastOpen = now
end

-- ProximityPrompt activation. Returns true when the station should open now.
function HubWalkUpRules.trigger(state: any, station: any, canOpen: boolean, now: number): boolean
    if not canOpen or HubWalkUpRules.destination(station) == nil then return false end
    if now - state.lastOpen < HubWalkUpRules.TriggerGap then return false end
    state.lastOpen = now
    return true
end

-- BD-1074: what a prompt press does ("open", "close" or "none"). openName = the rail destination whose screen is on show now ("" for none).
-- The key of the station whose OWN screen is open closes that screen; the gap still stops a held or hammered key from opening then closing at once.
-- Stations still open only on their key or prompt (docs/114 6.2): a press never opens a screen the station does not own.
function HubWalkUpRules.press(state: any, station: any, canOpen: boolean, openName: any, now: number): string
    local destination = HubWalkUpRules.destination(station)
    if destination == nil or now - state.lastOpen < HubWalkUpRules.TriggerGap then return "none" end
    if typeof(openName) == "string" and openName == destination then
        state.lastOpen = now
        return "close"
    end
    if not canOpen then return "none" end
    state.lastOpen = now
    return "open"
end

return HubWalkUpRules
