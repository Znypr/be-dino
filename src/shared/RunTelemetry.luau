--!strict
-- BD-426: pure, privacy-safe run/session telemetry. No Roblox types, no UserIds, no names: an event is a whitelisted name plus a few
-- bounded integers and one whitelisted reason. The server module (src/server/TelemetryService.luau) sends the result to
-- AnalyticsService custom events and to the server log; tools/telemetry_report.py reads the log lines.
local RunTelemetry = {}

RunTelemetry.LogPrefix = "[BD-TELEMETRY] "
RunTelemetry.EndReasons = {Death = true, ManualExit = true, Disconnect = true, Predation = true, Other = true}
RunTelemetry.MaxEventsPerMinute = 30 -- per server, token bucket
RunTelemetry.MaxEventsPerSession = 200
-- BD-649..653 (docs/167): counted lines (`count`), script-error lines and the visit line have their OWN budget so they can never starve
-- run_end / session_end: 20 lines a minute and 300 lines in total per server. Counters are rolled up (one line per name+service per
-- flush, never one line per event), so a spammer can raise a number but never the number of lines.
RunTelemetry.MaxCountLinesPerMinute = 20
RunTelemetry.MaxCountLinesPerServer = 300
RunTelemetry.RollupSeconds = 300
RunTelemetry.CountNames = {movement_rejects = true, rate_limited = true, script_errors = true, shop_purchases = true, hatches = true, fusions = true}
RunTelemetry.FunnelSteps = {run = "first_run_s", food = "first_food_s", egg = "first_egg_s", hatch = "first_hatch_s", shop = "first_shop_s"}
RunTelemetry.MaxCounterKeys = 40 -- distinct name+service pairs waiting for a flush
RunTelemetry.MaxErrorTexts = 12 -- distinct script-error texts logged per server; later ones are only counted
RunTelemetry.MaxErrorTextLength = 100

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
    return {startedAt = now, lastAt = now, location = location, hubSeconds = 0, runSeconds = 0, runs = 0, sent = 0, first = {}}
end

-- BD-653: seconds since join of the first food / run / egg / hatch / shop purchase; set once, bounded, memory only.
function RunTelemetry.noteStep(session: {[string]: any}, step: string, now: number)
    if RunTelemetry.FunnelSteps[step] == nil or session.first[step] ~= nil then return end
    session.first[step] = whole(now - session.startedAt, 86400)
end

-- location is "Island" while in a run; everything else counts as hub time.
function RunTelemetry.moved(session: {[string]: any}, now: number, newLocation: string)
    local dt = math.max(0, now - session.lastAt)
    if session.location == "Island" then session.runSeconds += dt else session.hubSeconds += dt end
    session.lastAt, session.location = now, newLocation
end

function RunTelemetry.runFinished(session: {[string]: any}) session.runs += 1 end

-- meta (BD-653, optional): {server = random per-server id, at = unix time}. Nothing here identifies a person.
function RunTelemetry.sessionEnd(session: {[string]: any}, now: number, meta: {[string]: any}?): {[string]: any}
    RunTelemetry.moved(session, now, session.location)
    local event: {[string]: any} = {
        event = "session_end",
        total_s = whole(now - session.startedAt, 86400),
        runs = whole(session.runs, 10000),
        hub_s = whole(session.hubSeconds, 86400),
        run_s = whole(session.runSeconds, 86400),
    }
    if meta then
        event.server = RunTelemetry.cleanId(meta.server)
        event.at = if typeof(meta.at) == "number" then whole(meta.at, 4294967295) else nil
    end
    for step, key in RunTelemetry.FunnelSteps do event[key] = session.first[step] end
    return event
end

-- BD-653: a random 8-hex-digit id per server start (not the engine server id, never a user id). `pick(lo, hi)` returns a random integer.
function RunTelemetry.serverId(pick: (number, number) -> number): string
    return string.format("%04x%04x", pick(0, 65535), pick(0, 65535))
end

-- Letters and digits only, 1 to 16 characters; anything else becomes nil, so a bad value can never put text into a line.
function RunTelemetry.cleanId(raw: any): string?
    if typeof(raw) ~= "string" or #raw < 1 or #raw > 16 or raw:find("[^%w]") then return nil end
    return raw
end

-- visit: logged at JOIN (BD-653), so a player who never leaves cleanly (the server closes first) still shows up.
function RunTelemetry.visit(serverId: any, at: any): {[string]: any}
    return {event = "visit", server = RunTelemetry.cleanId(serverId), at = if typeof(at) == "number" then whole(at, 4294967295) else nil}
end

-- BD-649/650/652: server-wide counters, rolled up. bump() is one table write; takeCounts() returns the pending deltas and resets them.
function RunTelemetry.newCounters(): {[string]: any}
    return {pending = {}, keys = 0}
end

-- A service label: letters and digits only, 1 to 20 characters ("Chest", "ProfileEggs"); anything else is "Other".
function RunTelemetry.label(raw: any): string
    if typeof(raw) ~= "string" or #raw < 1 or #raw > 20 or raw:find("[^%w]") then return "Other" end
    return raw
end

function RunTelemetry.bump(counters: {[string]: any}, name: string, service: any, amount: number?): boolean
    if RunTelemetry.CountNames[name] == nil then return false end
    local n = whole(amount or 1, 1000000)
    if n < 1 then return false end
    local label = if service == nil then "" else RunTelemetry.label(service)
    local key = name .. "|" .. label
    local pending = counters.pending
    if pending[key] == nil then
        if counters.keys >= RunTelemetry.MaxCounterKeys then
            key = name .. "|Other"
            if pending[key] == nil then counters.keys += 1 end
        else
            counters.keys += 1
        end
    end
    pending[key] = math.min(1000000000, (pending[key] or 0) + n)
    return true
end

function RunTelemetry.takeCounts(counters: {[string]: any}): {{name: string, service: string?, value: number}}
    local out = {}
    for key, value in counters.pending do
        local name, service = string.match(key, "^([^|]*)|(.*)$")
        out[#out + 1] = {name = name, service = if service ~= "" then service else nil, value = value}
    end
    table.sort(out, function(a, b)
        if a.name ~= b.name then return a.name < b.name end
        return (a.service or "") < (b.service or "")
    end)
    counters.pending, counters.keys = {}, 0
    return out
end

function RunTelemetry.countEvent(name: string, value: number, service: string?): {[string]: any}
    return {event = "count", name = name, value = whole(value, 1000000000), service = service}
end

-- BD-651: script-error text, bounded and scrubbed. `names` = player names / display names seen on this server (memory only, never logged).
-- One line, a short whitelist of characters, long digit runs (ids) replaced, any player name replaced, cut to MaxErrorTextLength.
function RunTelemetry.scrub(raw: any, names: {string}?): string
    local text = if typeof(raw) == "string" then raw else tostring(raw)
    text = text:match("^[^\r\n]*") or ""
    if names then
        for _, name in names do
            if #name >= 3 then
                local at = text:find(name, 1, true)
                while at do
                    text = text:sub(1, at - 1) .. "<p>" .. text:sub(at + #name)
                    at = text:find(name, at + 3, true)
                end
            end
        end
    end
    text = text:gsub("[^%w%s%._:%-%(%),=<>/#]", "")
    text = text:gsub("%d%d%d%d%d%d+", "#")
    text = text:gsub("%s+", " ")
    return string.sub(text, 1, RunTelemetry.MaxErrorTextLength)
end

function RunTelemetry.newErrorState(): {[string]: any}
    return {seen = {}, distinct = 0}
end

-- Returns the script_error event to log, or nil when this text was already logged or the per-server limit of distinct texts is reached.
function RunTelemetry.errorEvent(state: {[string]: any}, message: any, scriptName: any, names: {string}?): {[string]: any}?
    local text = RunTelemetry.scrub(message, names)
    if text == "" or state.seen[text] then return nil end
    if state.distinct >= RunTelemetry.MaxErrorTexts then return nil end
    state.seen[text] = true
    state.distinct += 1
    return {event = "script_error", script = RunTelemetry.label(scriptName), text = text}
end

-- Rate limiter: server-wide token bucket plus a per-session cap. Returns true when the event may be sent.
-- maxTotal / perMinute (optional, BD-649..653): a second bucket for count / error lines with a hard total per server.
function RunTelemetry.newLimiter(maxTotal: number?, perMinute: number?): {[string]: any}
    local rate = perMinute or RunTelemetry.MaxEventsPerMinute
    return {tokens = rate, at = 0, rate = rate, maxTotal = maxTotal, total = 0}
end

function RunTelemetry.allow(limiter: {[string]: any}, session: {[string]: any}?, now: number): boolean
    local elapsed = math.max(0, now - limiter.at)
    limiter.at = now
    local rate = limiter.rate or RunTelemetry.MaxEventsPerMinute
    limiter.tokens = math.min(rate, limiter.tokens + elapsed * rate / 60)
    if limiter.tokens < 1 then return false end
    if limiter.maxTotal ~= nil and limiter.total >= limiter.maxTotal then return false end
    if session then
        if session.sent >= RunTelemetry.MaxEventsPerSession then return false end
        session.sent += 1
    end
    limiter.tokens -= 1
    limiter.total = (limiter.total or 0) + 1
    return true
end

local ORDER = {"event", "duration_s", "reason", "food", "food_is_estimate", "food_raw", "eggs_food", "weather_s", "eggs", "nests", "crystals", "total_s", "runs", "hub_s", "run_s",
    "first_run_s", "first_food_s", "first_egg_s", "first_hatch_s", "first_shop_s", "server", "at", "name", "service", "value", "script", "text"}
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
