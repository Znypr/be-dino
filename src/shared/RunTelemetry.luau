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

-- run_end: duration_s, food, eggs, nests, crystals, reason. `food` is the DERIVED legacy figure (eggs / FoodCatchRate, so weather and potion
-- multipliers inflate it), kept for comparison with older logs. BD-575: the real numbers are food_raw (raw food points eaten, summed from the
-- server pickups), eggs_food (eggs the food alone earned at x1, before the weather and potion multipliers) and weather_s (seconds of the run
-- spent in a weather event). They are absent (nil) when the caller did not track them, never guessed.
function RunTelemetry.runEnd(input: {runSeconds: any, reason: any, eggs: any, nests: any, crystals: any, food: any?, foodCatchRate: number?, foodRaw: any?, eggsFood: any?, weatherSeconds: any?}): {[string]: any}
    local eggs = whole(input.eggs, 100000)
    local food = input.food
    local rate = input.foodCatchRate
    local foodValue = if typeof(food) == "number" then whole(food, 10000000)
        elseif typeof(rate) == "number" and rate > 0 then whole(eggs / rate, 10000000) else 0
    local duration = whole(input.runSeconds, 86400)
    return {
        event = "run_end",
        duration_s = duration,
        reason = RunTelemetry.reason(input.reason),
        food = foodValue,
        food_is_estimate = typeof(food) ~= "number",
        food_raw = if typeof(input.foodRaw) == "number" then whole(input.foodRaw, 10000000) else nil,
        eggs_food = if typeof(input.eggsFood) == "number" then whole(input.eggsFood, 100000) else nil,
        weather_s = if typeof(input.weatherSeconds) == "number" then math.min(duration, whole(input.weatherSeconds, 86400)) else nil,
        eggs = eggs,
        nests = whole(input.nests, 1000),
        crystals = whole(input.crystals, 10000000),
    }
end

-- BD-575: per-run food accumulator (server memory only, one small table per player, never in a profile). noteFood is called ONCE per
-- player per food tick with the points that tick ate, so it is a few additions, not a per-pickup call. `rawPoints` is the pickup value
-- before any admin multiplier; `gainedPoints` is what FoodService fed into the egg award (admin multiplier included, weather and potion
-- multipliers NOT included: those apply inside FoodCatchRules.award). eggsFood is therefore gainedPoints * rate, a float rounded at the end.
function RunTelemetry.newRunStats(runId: string?): {[string]: any}
    return {runId = runId, foodRaw = 0, eggsFood = 0, ticks = 0}
end

function RunTelemetry.noteFood(stats: {[string]: any}, rawPoints: number, gainedPoints: number, foodCatchRate: number)
    if typeof(rawPoints) ~= "number" or rawPoints ~= rawPoints or rawPoints <= 0 then return end
    stats.foodRaw += rawPoints
    if typeof(gainedPoints) == "number" and gainedPoints == gainedPoints and gainedPoints > 0 and typeof(foodCatchRate) == "number" then
        stats.eggsFood += gainedPoints * foodCatchRate
    end
    stats.ticks += 1
end

-- BD-575: weather intervals as a bounded log, so the minutes a run spent in weather are computed once at its end instead of ticking
-- every second. changed(log, id, now) is called when the WeatherId changes ("clear", "" and nil all mean no weather).
RunTelemetry.MaxWeatherIntervals = 64
function RunTelemetry.newWeatherLog(): {[string]: any}
    return {closed = {}, openAt = nil}
end

function RunTelemetry.weatherChanged(log: {[string]: any}, id: any, now: number)
    local inWeather = typeof(id) == "string" and id ~= "" and id ~= "clear"
    if inWeather and log.openAt == nil then
        log.openAt = now
    elseif not inWeather and log.openAt ~= nil then
        local closed = log.closed
        if #closed >= RunTelemetry.MaxWeatherIntervals then table.remove(closed, 1) end
        closed[#closed + 1] = {log.openAt, now}
        log.openAt = nil
    end
end

-- Seconds of [from, to] that overlap a weather interval (the open one counts up to `to`).
function RunTelemetry.weatherSeconds(log: {[string]: any}, from: number, to: number): number
    if to <= from then return 0 end
    local total = 0
    for _, interval in log.closed do
        total += math.max(0, math.min(to, interval[2]) - math.max(from, interval[1]))
    end
    if log.openAt ~= nil then total += math.max(0, to - math.max(from, log.openAt)) end
    return total
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

local ORDER = {"event", "duration_s", "reason", "food", "food_is_estimate", "food_raw", "eggs_food", "weather_s", "eggs", "nests", "crystals", "total_s", "runs", "hub_s", "run_s"}
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
