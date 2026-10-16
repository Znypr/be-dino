--!strict
-- Trailer clip shot lists (docs/133): pure data helpers, no Roblox services. Used by the dev-only client DemoDirector and by
-- tools/verify_demo_director.py. Never reads Config; the director itself is gated by Config.DemoDirectorEnabled + Studio.
local DemoShots = {}

DemoShots.Version = 1
DemoShots.CameraKinds = {static = true, orbit = true, dolly = true, pushin = true, track = true}
DemoShots.Easings = {linear = true, inSine = true, outSine = true, inOutSine = true, inQuad = true, outQuad = true, inOutQuad = true, outCubic = true, inOutCubic = true}
DemoShots.TriggerKinds = {remote = true, teleport = true, hud = true, note = true, wait = true}
-- Only existing Studio test harness remotes may be fired (each is itself gated by its own Config flag on the server).
DemoShots.AllowedRemotes = {TestGrantChests = true, TestSetMutationCopies = true, TestGrantSpecies = true}
DemoShots.Aspects = {["16:9"] = 16 / 9, ["9:16"] = 9 / 16}
-- Fraction of the screen kept free on each side so titles survive platform crops (9:16 needs more at top/bottom for app UI).
DemoShots.SafeInsets = {["16:9"] = {x = 0.05, y = 0.06}, ["9:16"] = {x = 0.06, y = 0.12}}

function DemoShots.ease(name: string?, t: number): number
    t = math.clamp(t, 0, 1)
    if name == nil or name == "linear" then return t end
    if name == "inSine" then return 1 - math.cos(t * math.pi / 2) end
    if name == "outSine" then return math.sin(t * math.pi / 2) end
    if name == "inOutSine" then return -(math.cos(math.pi * t) - 1) / 2 end
    if name == "inQuad" then return t * t end
    if name == "outQuad" then return 1 - (1 - t) * (1 - t) end
    if name == "inOutQuad" then return if t < 0.5 then 2 * t * t else 1 - (-2 * t + 2) ^ 2 / 2 end
    if name == "outCubic" then return 1 - (1 - t) ^ 3 end
    if name == "inOutCubic" then return if t < 0.5 then 4 * t * t * t else 1 - (-2 * t + 2) ^ 3 / 2 end
    return t
end

local function isVec(v: any): boolean
    return type(v) == "table" and #v == 3 and type(v[1]) == "number" and type(v[2]) == "number" and type(v[3]) == "number"
end

local function lerp(a: number, b: number, t: number): number return a + (b - a) * t end
local function lerpVec(a: {number}, b: {number}, t: number): {number}
    return {lerp(a[1], b[1], t), lerp(a[2], b[2], t), lerp(a[3], b[3], t)}
end

-- Camera pose at normalized time t (0..1): returns position, look as plain {x,y,z} arrays (testable without Vector3).
-- `subject` is the tracked player position (used by kind "track").
function DemoShots.cameraPose(cam: any, t: number, subject: {number}?): ({number}, {number})
    local e = DemoShots.ease(cam.ease, t)
    local kind = cam.kind
    if kind == "static" then
        return cam.pos, cam.look
    elseif kind == "orbit" then
        local c = cam.center
        local deg = lerp(cam.startDeg or 0, cam.endDeg or 360, e)
        local r = cam.radius or 20
        local rad = math.rad(deg)
        return {c[1] + math.cos(rad) * r, c[2] + (cam.height or 6), c[3] + math.sin(rad) * r}, {c[1], c[2] + (cam.lookHeight or 0), c[3]}
    elseif kind == "dolly" then
        return lerpVec(cam.from, cam.to, e), if cam.lookTo then lerpVec(cam.look, cam.lookTo, e) else cam.look
    elseif kind == "pushin" then
        local p, l = cam.from, cam.look
        local dx, dy, dz = l[1] - p[1], l[2] - p[2], l[3] - p[3]
        local len = math.sqrt(dx * dx + dy * dy + dz * dz)
        if len < 1e-6 then return p, l end
        local move = math.min(cam.distance or 8, len - 1) * e
        return {p[1] + dx / len * move, p[2] + dy / len * move, p[3] + dz / len * move}, l
    else -- track
        local s = subject or {0, 0, 0}
        local o = cam.offset or {0, 6, 14}
        return {s[1] + o[1], s[2] + o[2], s[3] + o[3]}, {s[1], s[2] + (cam.lookHeight or 2), s[3]}
    end
end

local function validateCamera(cam: any, where: string): string?
    if type(cam) ~= "table" then return where .. ": camera must be a table" end
    if not DemoShots.CameraKinds[cam.kind] then return where .. ": unknown camera kind " .. tostring(cam.kind) end
    if cam.ease ~= nil and not DemoShots.Easings[cam.ease] then return where .. ": unknown easing " .. tostring(cam.ease) end
    local k = cam.kind
    if k == "static" and not (isVec(cam.pos) and isVec(cam.look)) then return where .. ": static needs pos and look" end
    if k == "orbit" and not (isVec(cam.center) and type(cam.radius) == "number" and cam.radius > 0) then return where .. ": orbit needs center and radius > 0" end
    if k == "dolly" and not (isVec(cam.from) and isVec(cam.to) and isVec(cam.look)) then return where .. ": dolly needs from, to, look" end
    if k == "pushin" and not (isVec(cam.from) and isVec(cam.look)) then return where .. ": pushin needs from and look" end
    if k == "track" and cam.offset ~= nil and not isVec(cam.offset) then return where .. ": track offset must be a vector" end
    return nil
end

local function validateTrigger(trig: any, duration: number, where: string): string?
    if type(trig) ~= "table" then return where .. ": trigger must be a table" end
    if not DemoShots.TriggerKinds[trig.kind] then return where .. ": unknown trigger kind " .. tostring(trig.kind) end
    if type(trig.at) ~= "number" or trig.at < 0 or trig.at > duration then return where .. ": at must be 0..duration seconds" end
    if trig.kind == "remote" then
        if not DemoShots.AllowedRemotes[trig.remote] then return where .. ": remote not on the Studio test allow-list: " .. tostring(trig.remote) end
        if trig.repeatCount ~= nil and (type(trig.repeatCount) ~= "number" or trig.repeatCount < 1 or trig.repeatCount > 60) then return where .. ": repeatCount 1..60" end
    elseif trig.kind == "teleport" then
        if not (isVec(trig.pos) or type(trig.spot) == "string") then return where .. ": teleport needs pos or spot" end
    elseif trig.kind == "hud" then
        if type(trig.visible) ~= "boolean" then return where .. ": hud needs visible boolean" end
    end
    return nil
end

-- Returns nil when valid, otherwise a readable error string.
function DemoShots.validate(list: any): string?
    if type(list) ~= "table" then return "shot list must be a table" end
    if type(list.name) ~= "string" or list.name == "" then return "name required" end
    if list.version ~= DemoShots.Version then return "version must be " .. DemoShots.Version end
    if DemoShots.Aspects[list.aspect] == nil then return "aspect must be 16:9 or 9:16" end
    if type(list.shots) ~= "table" or #list.shots == 0 then return "shots must be a non-empty array" end
    local total = 0
    for i, shot in list.shots do
        local where = "shot " .. i
        if type(shot) ~= "table" then return where .. ": must be a table" end
        if type(shot.duration) ~= "number" or shot.duration <= 0 or shot.duration > 60 then return where .. ": duration 0..60 seconds" end
        total += shot.duration
        local err = validateCamera(shot.camera, where)
        if err then return err end
        if shot.title ~= nil and (type(shot.title) ~= "string" or #shot.title > 40) then return where .. ": title is a string of at most 40 characters" end
        if shot.lowerThird ~= nil and (type(shot.lowerThird) ~= "string" or #shot.lowerThird > 60) then return where .. ": lowerThird is a string of at most 60 characters" end
        if shot.triggers ~= nil then
            if type(shot.triggers) ~= "table" then return where .. ": triggers must be an array" end
            for j, trig in shot.triggers do
                local terr = validateTrigger(trig, shot.duration, where .. " trigger " .. j)
                if terr then return terr end
            end
        end
    end
    if total > 180 then return "total length over 180 seconds; split the clip" end
    return nil
end

return DemoShots
