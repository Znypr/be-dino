--!strict
-- BD-287 (docs/104 s7): the pure rules for "teleport to a Cave hub station". Plain numbers and tables only: the server
-- (HubTravelService) gathers a plain `state` table and tools/verify_hub_travel.py runs the same code offline.
-- Everything is behind Config.CaveHub (state.caveHub); with it false every request is refused ("flag_off").
-- state = {caveHub, profileState, runState, dinoAttached, alive, inHub, now, lastAt, occupied = {{x, z}...}}
local CaveHubLayout = require(script.Parent.CaveHubLayout)
local HubTravelRules = {}
HubTravelRules.RateSeconds = 0.8 -- PROVISIONAL (docs/104 s7): one request per player per 0.8 s
HubTravelRules.OccupiedRadius = 2.5 -- studs: an arrival spot this close to another player counts as taken (spots are >= 3 apart)
HubTravelRules.MaxKeyLength = 24

-- Reasons: flag_off, not_owned, bad_request, not_loaded, not_home, no_dino, dead, outside, unknown, settings, rate_limited
local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end

-- Station id from a request (`{station = "nests"}` or the bare string); nil when malformed.
function HubTravelRules.stationKey(request: any): string?
    local key = request
    if typeof(request) == "table" then key = (request :: any).station end
    if typeof(key) ~= "string" or #key == 0 or #key > HubTravelRules.MaxKeyLength then return nil end
    return key
end

-- ok, reason. Pure; does not touch rate-limit state (process() stamps it).
function HubTravelRules.validate(request: any, state: any): (boolean, string?)
    if typeof(state) ~= "table" or state.caveHub ~= true then return false, "flag_off" end
    local key = HubTravelRules.stationKey(request)
    if key == nil or not finite(state.now) then return false, "bad_request" end
    if state.profileState ~= "Loaded" then return false, "not_loaded" end
    -- BD-391/405 (docs/115 D22): with the perk flag on, only a player who bought Fast travel may be moved.
    if state.fastTravelPerk == true and state.fastTravelOwned ~= true then return false, "not_owned" end
    if state.runState ~= "Sanctuary" then return false, "not_home" end
    if state.dinoAttached ~= true then return false, "no_dino" end
    if state.alive ~= true then return false, "dead" end
    if state.inHub ~= true then return false, "outside" end
    local station = CaveHubLayout.get().byId[key]
    if station == nil then return false, "unknown" end
    if station.rail == "settings" then return false, "settings" end -- docs/104 s15.1: Settings never teleports
    if finite(state.lastAt) and state.now - state.lastAt < HubTravelRules.RateSeconds then return false, "rate_limited" end
    return true, nil
end

-- Arrival spot among the station's 6: the first one no other player stands within OccupiedRadius of; if all are taken,
-- the one farthest from everybody (ties: lowest index). Deterministic. Returns {x, y, z, yaw, index} (world coordinates).
function HubTravelRules.pickSpot(stationId: string, occupied: any): any?
    if CaveHubLayout.get().byId[stationId] == nil then return nil end
    local spots = CaveHubLayout.arrivalSpots(stationId)
    local people = {}
    if typeof(occupied) == "table" then
        for _, p in occupied :: any do
            if typeof(p) == "table" and finite(p.x) and finite(p.z) then people[#people + 1] = p end
        end
    end
    local r2 = HubTravelRules.OccupiedRadius ^ 2
    local bestIndex, bestScore = 1, -1
    for i, sp in spots do
        local nearest = math.huge
        for _, p in people do
            local d2 = (sp.x - p.x) ^ 2 + (sp.z - p.z) ^ 2
            if d2 < nearest then nearest = d2 end
        end
        if nearest >= r2 then return {x = sp.x, y = sp.y, z = sp.z, yaw = sp.yaw, index = i} end
        if nearest > bestScore then bestIndex, bestScore = i, nearest end
    end
    local sp = spots[bestIndex]
    return {x = sp.x, y = sp.y, z = sp.z, yaw = sp.yaw, index = bestIndex}
end

-- Full decision. `session` = {lastAt = number?} per player (mutated: every well-formed request that is not itself
-- rate-limited stamps lastAt, so a spammer is measured from their last accepted-or-refused try).
-- Returns ack = {ok, station?, reason?} for the client and the arrival spot (nil on refusal).
function HubTravelRules.process(session: any, request: any, state: any): (any, any?)
    if typeof(state) ~= "table" then return {ok = false, reason = "flag_off"}, nil end
    state.lastAt = session.lastAt
    local ok, reason = HubTravelRules.validate(request, state)
    if state.caveHub == true and reason ~= "bad_request" and reason ~= "rate_limited" then session.lastAt = state.now end
    if not ok then return {ok = false, reason = reason}, nil end
    local key = HubTravelRules.stationKey(request) :: string
    local spot = HubTravelRules.pickSpot(key, state.occupied)
    if spot == nil then return {ok = false, reason = "unknown"}, nil end
    return {ok = true, station = key}, spot
end
return HubTravelRules
