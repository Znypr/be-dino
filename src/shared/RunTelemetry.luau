--!strict
-- BD-426: pure, privacy-safe run/session telemetry. No Roblox types, no UserIds, no names: an event is a whitelisted name plus a few
-- bounded integers and one whitelisted reason. The server module (src/server/TelemetryService.luau) sends the result to
-- AnalyticsService custom events and to the server log; tools/telemetry_report.py reads the log lines.
local RunTelemetry = {}

RunTelemetry.LogPrefix = "[BD-TELEMETRY] "
RunTelemetry.EndReasons = {Death = true, ManualExit = true, Disconnect = true, Predation = true, Other = true}
RunTelemetry.MaxEventsPerMinute = 30 -- per server, token bucket
RunTelemetry.MaxEventsPerSession = 200

function RunTelemetry.reason(raw: any): string
    if typeof(raw) == "string" and RunTelemetry.EndReasons[raw] then return raw end
    return "Other"
end

local function whole(value: any, cap: number): number
    if typeof(value) ~= "number" or value ~= value then return 0 end
    return math.clamp(math.floor(value + 0.5), 0, cap)
end

-- run_end: duration_s, food, eggs, nests, crystals, reason. food is an estimate (eggs / FoodCatchRate) unless a real value is given.
function RunTelemetry.runEnd(input: {runSeconds: any, reason: any, eggs: any, nests: any, crystals: any, food: any?, foodCatchRate: number?}): {[string]: any}
    local eggs = whole(input.eggs, 100000)
    local food = input.food
    local rate = input.foodCatchRate
    local foodValue = if typeof(food) == "number" then whole(food, 10000000)
        elseif typeof(rate) == "number" and rate > 0 then whole(eggs / rate, 10000000) else 0
    return {
        event = "run_end",
        duration_s = whole(input.runSeconds, 86400),
        reason = RunTelemetry.reason(input.reason),
        food = foodValue,
        food_is_estimate = typeof(food) ~= "number",
        eggs = eggs,
        nests = whole(input.nests, 1000),
        crystals = whole(input.crystals, 10000000),
    }
end

-- Per-session accumulator (one table per player per server visit, kept in server memory only, never in a profile).
function RunTelemetry.newSession(now: number, location: string): {[string]: any}
    return {startedAt = now, lastAt = now, location = location, hubSeconds = 0, runSeconds = 0, runs = 0, sent = 0}
end

-- location is "Island" while in a run; everything else counts as hub time.
function RunTelemetry.moved(session: {[string]: any}, now: number, newLocation: string)
    local dt = math.max(0, now - session.lastAt)
    if session.location == "Island" then session.runSeconds += dt else session.hubSeconds += dt end
    session.lastAt, session.location = now, newLocation
end

function RunTelemetry.runFinished(session: {[string]: any}) session.runs += 1 end

function RunTelemetry.sessionEnd(session: {[string]: any}, now: number): {[string]: any}
    RunTelemetry.moved(session, now, session.location)
    return {
        event = "session_end",
        total_s = whole(now - session.startedAt, 86400),
        runs = whole(session.runs, 10000),
        hub_s = whole(session.hubSeconds, 86400),
        run_s = whole(session.runSeconds, 86400),
    }
end

-- Rate limiter: server-wide token bucket plus a per-session cap. Returns true when the event may be sent.
function RunTelemetry.newLimiter(): {[string]: any}
    return {tokens = RunTelemetry.MaxEventsPerMinute, at = 0}
end

function RunTelemetry.allow(limiter: {[string]: any}, session: {[string]: any}?, now: number): boolean
    local elapsed = math.max(0, now - limiter.at)
    limiter.at = now
    limiter.tokens = math.min(RunTelemetry.MaxEventsPerMinute, limiter.tokens + elapsed * RunTelemetry.MaxEventsPerMinute / 60)
    if limiter.tokens < 1 then return false end
    if session then
        if session.sent >= RunTelemetry.MaxEventsPerSession then return false end
        session.sent += 1
    end
    limiter.tokens -= 1
    return true
end

local ORDER = {"event", "duration_s", "reason", "food", "food_is_estimate", "eggs", "nests", "crystals", "total_s", "runs", "hub_s", "run_s"}
-- One stable JSON line (no HttpService needed, so it can be tested offline).
function RunTelemetry.line(event: {[string]: any}): string
    local parts = {}
    for _, key in ORDER do
        local v = event[key]
        if v ~= nil then
            parts[#parts + 1] = string.format("\"%s\":%s", key, if typeof(v) == "string" then string.format("\"%s\"", v) else tostring(v))
        end
    end
    return RunTelemetry.LogPrefix .. "{" .. table.concat(parts, ",") .. "}"
end

return RunTelemetry
