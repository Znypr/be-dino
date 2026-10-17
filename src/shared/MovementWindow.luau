--!strict
-- BD-611: sliding displacement window for the server's movement checks (docs/151 section 5, F1). PURE: no Roblox services, only Config and Vector3.
--
-- MovementEnvelope.plausible compares ONE tick (0.1 s guard, 0.08 s food, 0.25 s crystals) with `speed x dt x tolerance + burst`. Every plausible tick
-- then became the new baseline, so a client that moved the largest allowed step on every tick passed forever (106 studs/s at WalkSpeed 22).
-- This window keeps the samples of the last `MovementGuardWindowSeconds` and checks EVERY span inside it against
--     limit x SpeedFactor x (span + JitterSeconds) + SlackStuds
-- so sustained speed is bounded by limit x SpeedFactor x (1 + Jitter / Window) + Slack / Window (about 1.75 x WalkSpeed with the shipped numbers).
-- `limit` is the peak of MovementSpeedLimit / WalkSpeed over the ring (window + LimitHoldSeconds): a dash or leap the server opened, a potion that
-- just ran out. Horizontal only; the vertical envelope stays in MovementEnvelope.
local Config = require(script.Parent.Config)

local MovementWindow = {}

export type Window = { t: {number}, x: {number}, z: {number}, limit: {number}, tag: {any}, head: number }

function MovementWindow.new(): Window
    return { t = {}, x = {}, z = {}, limit = {}, tag = {}, head = 1 }
end

function MovementWindow.reset(w: Window)
    w.t, w.x, w.z, w.limit, w.tag, w.head = {}, {}, {}, {}, {}, 1
end

-- Studs the window allows over `span` seconds at `limit` studs/s.
function MovementWindow.allowed(limit: number, span: number): number
    return limit * Config.MovementGuardWindowSpeedFactor * (span + Config.MovementGuardWindowJitterSeconds) + Config.MovementGuardWindowSlackStuds
end

-- Highest sustained speed (studs/s) the window accepts at `limit`: the tightest span is the full window.
function MovementWindow.sustained(limit: number): number
    local span = Config.MovementGuardWindowSeconds
    return MovementWindow.allowed(limit, span) / span
end

-- Adds a sample taken at `now` (seconds, any monotonic clock) and checks every span in the window against the newest sample.
-- Returns true when it is inside the budget. Otherwise false, the tag stored with the OLDEST sample of the window (the caller's rollback target,
-- e.g. its CFrame) and that sample's x, z. The caller should then roll back and MovementWindow.reset(w).
function MovementWindow.push(w: Window, now: number, position: Vector3, limit: number, tag: any?): (boolean, any?, number?, number?)
    local t, xs, zs, limits, tags = w.t, w.x, w.z, w.limit, w.tag
    local last = #t + 1
    t[last], xs[last], zs[last], limits[last], tags[last] = now, position.X, position.Z, limit, tag
    if Config.MovementGuardWindowEnabled ~= true then
        w.t, w.x, w.z, w.limit, w.tag, w.head = { now }, { position.X }, { position.Z }, { limit }, { tag }, 1
        return true
    end
    local keepFrom = now - Config.MovementGuardWindowSeconds - Config.MovementGuardLimitHoldSeconds
    local head = w.head
    while head < last and t[head] < keepFrom do head += 1 end
    if head > 24 then -- compact now and then: the ring holds about 30 samples, never grows
        local nt, nx, nz, nl, ng = {}, {}, {}, {}, {}
        for i = head, last do local k = i - head + 1 nt[k], nx[k], nz[k], nl[k], ng[k] = t[i], xs[i], zs[i], limits[i], tags[i] end
        w.t, w.x, w.z, w.limit, w.tag, w.head = nt, nx, nz, nl, ng, 1
        t, xs, zs, limits, tags, head, last = nt, nx, nz, nl, ng, 1, #nt
    else
        w.head = head
    end
    local peak = 0
    for i = head, last do if limits[i] > peak then peak = limits[i] end end
    local windowFrom = now - Config.MovementGuardWindowSeconds
    local x, z = position.X, position.Z
    for i = last - 1, head, -1 do
        local span = now - t[i]
        if span > Config.MovementGuardWindowSeconds then break end
        local dx, dz = x - xs[i], z - zs[i]
        if math.sqrt(dx * dx + dz * dz) > MovementWindow.allowed(peak, span) then
            -- roll back to the oldest sample still inside the window: everything gained since then is taken away
            local first = i
            while first > head and t[first - 1] >= windowFrom do first -= 1 end
            return false, tags[first], xs[first], zs[first]
        end
    end
    return true
end

return MovementWindow
