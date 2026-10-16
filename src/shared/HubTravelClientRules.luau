--!strict
-- BD-288 / BD-292 (docs/104 s7, s8, s15.1): pure client rules for the Cave hub rail. Which station a rail button goes to,
-- whether it travels, opens plainly or is blocked ("At home" during a run), the calm words for a refused trip, the fade
-- timing. No Roblox services here: tools/verify_hub_travel_client.py runs this file offline. Everything is behind
-- Config.CaveHub (`caveHub` false -> always {kind = "open"}: the rail behaves exactly as before).
local Rules = {}

-- Rail destination (the Destination attribute on each rail button) -> hub station id. Settings never teleports.
Rules.Stations = table.freeze({collection = "index", eggs = "nests", fusion = "fusion", auras = "style", potions = "potions"})
-- In a run these four are dimmed; POTIONS and SETTINGS stay usable (docs/104 s7.7).
Rules.RunDimmed = table.freeze({collection = true, eggs = true, fusion = true, auras = true})
Rules.HomeHint = "At home"
Rules.MinTarget = 44 -- px: smallest touch target (rail buttons are 54 px high)
Rules.HeartStation = "heart"
Rules.ChipText = "Back to the middle"
Rules.ChipBottom = 96 -- px above the screen bottom: the chip sits ABOVE the 60 px EXPLORE ISLAND button (acceptance walk: it used to cover it)
Rules.GateBarBottom = 150 -- px: the Island Gate "Leaving..." bar sits above the chip so the two never overlap
Rules.TimeoutSeconds = 5 -- a travel that has not answered by then lets go of the screen

-- Refused-trip words (docs/72: short, calm, say what to do next). Unknown reasons get the generic line.
Rules.Refusals = table.freeze({
    rate_limited = "One moment...",
    busy = "One moment...",
    not_home = "At home",
    outside = "Walk into the cave first",
    no_dino = "Pick a dino first",
    dead = "Try again in a moment",
    not_loaded = "Almost ready...",
})
Rules.Generic = "Try again"
function Rules.refusal(reason: any): string
    return (if typeof(reason) == "string" then Rules.Refusals[reason] else nil) or Rules.Generic
end

function Rules.stationFor(destination: any): string?
    return if typeof(destination) == "string" then Rules.Stations[destination] else nil
end

-- A run is anything that is not Sanctuary and not still loading (nil / "").
function Rules.inRun(runState: any): boolean
    return typeof(runState) == "string" and runState ~= "" and runState ~= "Sanctuary"
end

function Rules.dimmed(destination: any, caveHub: any, runState: any): boolean
    return caveHub == true and typeof(destination) == "string" and Rules.RunDimmed[destination] == true and Rules.inRun(runState)
end

-- in = {caveHub, destination, runState, teleportShops, remote (HubTravel exists), busy}
-- out = {kind = "open"} | {kind = "travel", station} | {kind = "guide", station} | {kind = "blocked", toast}
-- "guide" = Teleport to shops is OFF at home: HubGuideClient draws the moss trail (falls back to a plain open on the pad).
function Rules.decide(i: any): any
    if typeof(i) ~= "table" or i.caveHub ~= true then return {kind = "open"} end
    if Rules.dimmed(i.destination, true, i.runState) then return {kind = "blocked", toast = Rules.HomeHint} end
    if Rules.inRun(i.runState) then return {kind = "open"} end -- POTIONS / SETTINGS in a run: as today
    local station = Rules.stationFor(i.destination)
    if station == nil then return {kind = "open"} end
    if i.teleportShops == false then return {kind = "guide", station = station} end -- BD-289: walk there, with the moss trail
    if i.remote ~= true then return {kind = "open"} end
    if i.busy == true then return {kind = "blocked", toast = nil} end -- a trip is already running: ignore the tap quietly
    return {kind = "travel", station = station}
end

-- The "Back to the middle" chip: only at home, only when the server put the player at a station other than the heart.
function Rules.chipVisible(caveHub: any, runState: any, hubStation: any, busy: any): boolean
    return caveHub == true and busy ~= true and runState == "Sanctuary" and typeof(hubStation) == "string"
        and hubStation ~= "" and hubStation ~= Rules.HeartStation
end

-- Fade timing (cream overlay in, then out when the menu is up). Reduce Motion = quick dissolve, no cue, no camera turn.
-- cameraTurn stays false: docs/104 s8 says the camera does not change on arrival (the 0.35 s turn in the BD-288 row is not built).
function Rules.fade(calm: any): any
    if calm == true then return {inSeconds = 0.08, outSeconds = 0.08, cue = false, cameraTurn = false} end
    return {inSeconds = 0.18, outSeconds = 0.18, cue = true, cameraTurn = false}
end

-- ack from the HubTravel RemoteFunction -> ok, reason. Any junk counts as a refusal.
function Rules.readAck(ack: any, station: string): (boolean, string?)
    if typeof(ack) ~= "table" then return false, "error" end
    if (ack :: any).ok == true and (ack :: any).station == station then return true, nil end
    local reason = (ack :: any).reason
    return false, if typeof(reason) == "string" then reason else "error"
end

return Rules
