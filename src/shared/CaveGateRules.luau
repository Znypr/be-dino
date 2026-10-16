--!strict
-- BD-290 / BD-291 (docs/104 s2.3, s9): pure rules for the Cave hub Island Gate and the hub-only HubDinos collision group.
-- Plain numbers and tables only (no Instances, no Config require): the server (HubGateService), the client bar
-- (HubGateClient) and tools/verify_cave_gate.py all run this same file. Everything is behind Config.CaveHub (state.caveHub);
-- with it false nothing is eligible, no group is assigned and the bar never shows. All numbers are PROVISIONAL.
local CaveHubLayout = require(script.Parent.CaveHubLayout)
local CaveGateRules = {}
CaveGateRules.DwellSeconds = 1.5 -- standing in the arch for this long starts the run (docs/104 s2.3)
CaveGateRules.AlongMin, CaveGateRules.AlongMax = 0, 10 -- studs outward from the arch centre (0 = standing in the arch mouth)
CaveGateRules.LateralMax = 12 -- studs either side of the arch centre line (the arch is 30 wide; pillars sit outside this)
CaveGateRules.HeightMax = 12 -- studs above the floor: a jump over the arch does not count
CaveGateRules.GroupName = "HubDinos"
CaveGateRules.BarSteps = 4 -- Reduce Motion: the bar moves in quarter steps instead of smoothly
CaveGateRules.BarText = "Leaving..."

local function finite(n: any): boolean return typeof(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end

-- The gate zone in world coordinates, built once from the layout (one geometry source).
local cached: any = nil
function CaveGateRules.zone(): any
    if cached then return cached end
    local s = CaveHubLayout.get().byId.gate
    cached = {sx = s.signX, sz = s.signZ + CaveHubLayout.CenterZ, ux = math.cos(s.outward), uz = math.sin(s.outward), floorY = CaveHubLayout.FloorY}
    return cached
end

-- (along, lateral) of a world point relative to the arch: along is positive toward the island.
function CaveGateRules.frame(x: number, z: number): (number, number)
    local zn = CaveGateRules.zone()
    local dx, dz = x - zn.sx, z - zn.sz
    return dx * zn.ux + dz * zn.uz, -dx * zn.uz + dz * zn.ux
end

-- True when (x, z[, y]) is inside the arch trigger zone. Bad numbers are never inside. Edges are inclusive.
function CaveGateRules.inZone(x: any, z: any, y: any?): boolean
    if not finite(x) or not finite(z) then return false end
    local along, lateral = CaveGateRules.frame(x, z)
    if along < CaveGateRules.AlongMin or along > CaveGateRules.AlongMax or math.abs(lateral) > CaveGateRules.LateralMax then return false end
    if y ~= nil then
        if not finite(y) then return false end
        if y > CaveGateRules.zone().floorY + CaveGateRules.HeightMax then return false end
    end
    return true
end

-- state = {caveHub, profileState, runState, dinoAttached, alive, inHub}: the same gates as RequestStartRun plus "in the cave".
function CaveGateRules.eligible(state: any): boolean
    return typeof(state) == "table" and state.caveHub == true and state.profileState == "Loaded" and state.runState == "Sanctuary"
        and state.dinoAttached == true and state.alive == true and state.inHub == true
end

function CaveGateRules.newSession(): any return {since = nil, fired = false} end

-- One tick for one player. Returns (progress 0..1, fire). `fire` is true at most once per stay in the zone: the latch
-- clears only when the player leaves the zone or stops being eligible (a run starting moves them to the island).
function CaveGateRules.step(session: any, inside: boolean, eligible: boolean, now: number): (number, boolean)
    if not (inside and eligible) or not finite(now) then
        session.since, session.fired = nil, false
        return 0, false
    end
    if session.since == nil then session.since = now end
    if session.fired then return 1, false end
    local progress = math.clamp((now - session.since) / CaveGateRules.DwellSeconds, 0, 1)
    if progress >= 1 then
        session.fired = true
        return 1, true
    end
    return progress, false
end

-- The server's start attempt was refused (for example the island is still loading): wait another full dwell, still once at a time.
function CaveGateRules.retry(session: any, now: number)
    session.since, session.fired = now, false
end

-- Bar fill for the HUD. Normal = smooth; Reduce Motion (calm) = whole quarter steps. Never a number on screen (docs/72).
function CaveGateRules.barFraction(progress: any, calm: any): number
    local p = if finite(progress) then math.clamp(progress :: number, 0, 1) else 0
    if calm == true then return math.floor(p * CaveGateRules.BarSteps + 1e-9) / CaveGateRules.BarSteps end
    return p
end

-- Collision group for a character: "HubDinos" while it stands at home inside the cave, nil = leave the character's own
-- group (restored when a run starts or it leaves the hub). Flag off: always nil.
function CaveGateRules.groupFor(state: any): string?
    if typeof(state) == "table" and state.caveHub == true and state.runState == "Sanctuary" and state.inHub == true then
        return CaveGateRules.GroupName
    end
    return nil
end

return CaveGateRules
