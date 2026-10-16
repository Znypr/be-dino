--!strict
-- BD-090 Egg Nests v2: pure one-at-a-time incubation queue, shared by the server (authoritative,
-- os.time) and the client (display projection with the server clock). No services, no randomness.
-- A nest is {nestId, state = "waiting" | "incubating" | "ready", readyAt?}. List order is queue order.
-- The next waiting nest starts the moment the previous one becomes READY (not when it is opened),
-- so offline time counts and N nests take N * duration in total.
local NestQueue = {}

-- Mutates `list` so it reflects time `now`. Returns true when anything changed.
function NestQueue.advance(list: {any}, now: number, duration: number): boolean
    local changed = false
    local chain: number? = nil
    while true do
        local incubating = nil
        for _, nest in list do
            if nest.state == "incubating" then incubating = nest break end
        end
        if incubating then
            if incubating.readyAt > now then return changed end
            incubating.state = "ready"
            chain = incubating.readyAt
            changed = true
        end
        local nextNest = nil
        for _, nest in list do
            if nest.state == "waiting" then nextNest = nest break end
        end
        if not nextNest then return changed end
        nextNest.state = "incubating"
        nextNest.readyAt = (chain or now) + duration
        chain = nil
        changed = true
    end
end

-- Display copy at time `now` (never mutates the input).
function NestQueue.project(list: {any}, now: number, duration: number): {any}
    local copy = {}
    for i, nest in list do copy[i] = table.clone(nest) end
    NestQueue.advance(copy, now, duration)
    return copy
end

-- Seconds until the whole queue has finished (0 when nothing is incubating or waiting).
function NestQueue.secondsUntilAllReady(list: {any}, now: number, duration: number): number
    local last, waiting = now, 0
    for _, nest in NestQueue.project(list, now, duration) do
        if nest.state == "incubating" and nest.readyAt > last then last = nest.readyAt end
        if nest.state == "waiting" then waiting += 1 end
    end
    last += waiting * duration
    return last - now
end

-- BD-259: seconds until the FIRST nest is ready, i.e. what the nest slot countdown shows (0 when one is ready already, or
-- when nothing is incubating). secondsUntilAllReady is the whole-queue total and must not be shown as "Ready in".
function NestQueue.secondsUntilNextReady(list: {any}, now: number, duration: number): number
    local soonest: number? = nil
    for _, nest in NestQueue.project(list, now, duration) do
        if nest.state == "ready" then return 0 end
        if nest.state == "incubating" and (soonest == nil or nest.readyAt < soonest) then soonest = nest.readyAt end
    end
    return if soonest then math.max(0, soonest - now) else 0
end

return NestQueue
