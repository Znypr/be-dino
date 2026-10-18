--!strict
-- BD-426: server-side playtest telemetry, behind Config.RunTelemetryEnabled (default false, on only in the playtest profile).
-- Read-only observer: it never writes a profile, an attribute or a remote. Events go to AnalyticsService custom events when the
-- API exists (pcall) and always to the server log as one JSON line each, which tools/telemetry_report.py aggregates.
-- BD-649..653 (docs/167): also counts movement set-backs, "rate_limited" answers per service, script errors, shop purchases / hatches /
-- fusions, and logs the visit at join, first-food / first-run / first-egg / first-hatch seconds and a random per-server id.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local RunTelemetry = require(ReplicatedStorage.Shared.RunTelemetry)

local TelemetryService = {}
local sessions: {[Player]: {[string]: any}} = {}
local limiter = RunTelemetry.newLimiter()
-- BD-649..653: count lines, script errors and nothing else use their own bucket (20 a minute, 300 a server), never the run_end one.
local countLimiter = RunTelemetry.newLimiter(RunTelemetry.MaxCountLinesPerServer, RunTelemetry.MaxCountLinesPerMinute)
local counters = RunTelemetry.newCounters()
local errorState = RunTelemetry.newErrorState()
local serverId: string? = nil -- random per server start, set in start(); not the engine server id, never a user id
local knownNames: {string} = {} -- player names seen on this server, memory only, ONLY used to scrub script-error text; never logged
local started = false
-- BD-575: per-player food accumulator for the current run (memory only) and the weather interval log; both stay empty while the flag is off.
local runStats: {[Player]: {[string]: any}} = setmetatable({}, {__mode = "k"}) :: any -- weak: a Disconnect run settles after PlayerRemoving, so the entry must outlive the leave but not the Player
local weatherLog = RunTelemetry.newWeatherLog()

local function enabled(): boolean
    return (Config :: any).RunTelemetryEnabled == true
end

local function emit(player: Player?, event: {[string]: any})
    local session = if player then sessions[player] else nil
    if not RunTelemetry.allow(limiter, session, os.clock()) then return end
    print(RunTelemetry.line(event))
    if player then
        -- AnalyticsService custom events (aggregated on the Creator Dashboard); absent or failing API just means log-only.
        pcall(function()
            local analytics = game:GetService("AnalyticsService") :: any
            analytics:LogCustomEvent(player, event.event, event.eggs or event.runs or event.duration_s or 0)
        end)
    end
end

-- A line on the count budget (no per-player session cap, no Analytics call).
local function emitCounted(event: {[string]: any})
    if not RunTelemetry.allow(countLimiter, nil, os.clock()) then return end
    print(RunTelemetry.line(event))
end

-- BD-649/650/652/653: a counted event. Flag-gated: with the flag off this is one boolean test. `service` is a short label ("Chest");
-- `player` (optional) also marks the first-hatch / first-shop-purchase step of that visit. Memory only until flush().
function TelemetryService.count(name: string, service: string?, player: Player?)
    if not enabled() then return end
    RunTelemetry.bump(counters, name, service, 1)
    local session = if player then sessions[player] else nil
    if session then
        if name == "hatches" then RunTelemetry.noteStep(session, "hatch", os.clock())
        elseif name == "shop_purchases" then RunTelemetry.noteStep(session, "shop", os.clock()) end
    end
end

-- Writes the pending counters as one `count` line per name+service, then clears them. Called every RollupSeconds, when a player leaves
-- and when the server closes; with nothing pending it prints nothing.
function TelemetryService.flush()
    if not enabled() then return end
    for _, item in RunTelemetry.takeCounts(counters) do
        emitCounted(RunTelemetry.countEvent(item.name, item.value, item.service))
    end
end

-- BD-575: called by FoodService at most once per player per food tick (already batched there) and only while the flag is on. Pure memory:
-- nothing is stored or sent to a client. A new runId starts a fresh accumulator, so a run that never settled cannot leak into the next.
function TelemetryService.noteFood(player: Player, runId: any, rawPoints: number, gainedPoints: number)
    if not enabled() then return end
    local rid = if typeof(runId) == "string" then runId else nil
    local session = sessions[player]
    if session and typeof(rawPoints) == "number" and rawPoints > 0 then RunTelemetry.noteStep(session, "food", os.clock()) end
    local stats = runStats[player]
    if not stats or stats.runId ~= rid then
        stats = RunTelemetry.newRunStats(rid)
        runStats[player] = stats
    end
    RunTelemetry.noteFood(stats, rawPoints, gainedPoints, Config.FoodCatchRate)
end

-- The body of the run_end report. Bounded work only: a few table reads, at most RunTelemetry.MaxWeatherIntervals (64) weather
-- intervals, one print, one pcall'd Analytics call. It runs OFF the settle thread (see runSettled), never inside it.
local function reportRunEnd(player: Player, reason: string, runSeconds: number, counts: {eggs: any, nests: any, crystals: any}, runId: any?, nowServer: number)
    local session = sessions[player]
    if session then RunTelemetry.runFinished(session) end
    local eggCount = counts.eggs
    if session and typeof(eggCount) == "number" and eggCount > 0 then RunTelemetry.noteStep(session, "egg", os.clock()) end
    local stats = runStats[player]
    runStats[player] = nil -- one run, one accumulator
    if stats and runId ~= nil and stats.runId ~= runId then stats = nil end -- food of some other run is not this run's food
    emit(player, RunTelemetry.runEnd({
        runSeconds = runSeconds, reason = reason,
        eggs = eggCount, nests = counts.nests, crystals = counts.crystals,
        foodCatchRate = Config.FoodCatchRate,
        foodRaw = if stats then stats.foodRaw else 0, -- no food tick for this run = it really ate nothing
        eggsFood = if stats then stats.eggsFood else 0,
        weatherSeconds = RunTelemetry.weatherSeconds(weatherLog, nowServer - (if typeof(runSeconds) == "number" then runSeconds else 0), nowServer),
    }))
end

-- Called by the settlement callback in Bootstrap after the commit; outcome is the committed run outcome table (may be nil).
-- BD-1096: THIS CALL CANNOT BLOCK, DELAY OR BREAK A SETTLEMENT. Studio round 5 saw a run stay in "Ending" for good after a script
-- timeout surfaced inside this function on the settle thread: the error killed the continuation that marks the run Settled. So the
-- settle thread only copies three numbers and the clock (cannot loop, cannot yield) and hands the report to task.defer; the report
-- runs in its own thread inside a pcall. A report that errors, yields forever or runs long costs the player nothing.
function TelemetryService.runSettled(player: Player, reason: string, runSeconds: number, outcome: any, runId: any?)
    local ok, err = pcall(function()
        if not enabled() then return end
        local o = if typeof(outcome) == "table" then outcome else {}
        local counts = {eggs = o.eggCount or o.chestCount, nests = o.nestCount, crystals = o.crystals}
        local nowServer = workspace:GetServerTimeNow()
        task.defer(function()
            local reported, reportErr = pcall(reportRunEnd, player, reason, runSeconds, counts, runId, nowServer)
            if not reported then warn("[Be Dino] telemetry run_end failed (settlement is unaffected): " .. tostring(reportErr)) end
        end)
    end)
    if not ok then warn("[Be Dino] telemetry runSettled failed (settlement is unaffected): " .. tostring(err)) end
end

-- BD-651: every uncaught server script error is counted; each DISTINCT scrubbed text (12 per server) is logged once.
local function listenForErrors()
    pcall(function()
        local scriptContext = game:GetService("ScriptContext") :: any
        scriptContext.Error:Connect(function(message: any, _trace: any, errorScript: any)
            RunTelemetry.bump(counters, "script_errors", nil, 1)
            local scriptName = if typeof(errorScript) == "Instance" then errorScript.Name else nil
            local event = RunTelemetry.errorEvent(errorState, message, scriptName, knownNames)
            if event then emitCounted(event) end
        end)
    end)
end

function TelemetryService.start()
    if not enabled() then return end
    if started then return end
    started = true
    -- BD-653: one random id for this server start (not the engine server id, no user id): lets a report tell servers apart without identifying anyone.
    local ok, id = pcall(function()
        local rng = Random.new()
        return RunTelemetry.serverId(function(lo, hi) return rng:NextInteger(lo, hi) end)
    end)
    serverId = if ok and typeof(id) == "string" then id else RunTelemetry.serverId(function(lo, hi) return math.random(lo, hi) end)
    -- BD-575: weather intervals on the server clock (the same clock the run length uses); an event-driven log, no polling.
    RunTelemetry.weatherChanged(weatherLog, workspace:GetAttribute("WeatherId"), workspace:GetServerTimeNow())
    workspace:GetAttributeChangedSignal("WeatherId"):Connect(function()
        RunTelemetry.weatherChanged(weatherLog, workspace:GetAttribute("WeatherId"), workspace:GetServerTimeNow())
    end)
    listenForErrors()
    local function join(player: Player)
        if sessions[player] then return end
        sessions[player] = RunTelemetry.newSession(os.clock(), "Sanctuary")
        if #knownNames < 60 then
            for _, text in {player.Name, player.DisplayName} do
                if typeof(text) == "string" and not table.find(knownNames, text) then knownNames[#knownNames + 1] = text end
            end
        end
        -- BD-653: the visit is logged at JOIN, so a player who never leaves cleanly (the server closes first) is still counted.
        emit(player, RunTelemetry.visit(serverId, os.time()))
        player:GetAttributeChangedSignal("Location"):Connect(function()
            local session = sessions[player]
            local location = player:GetAttribute("Location")
            if session and typeof(location) == "string" then
                RunTelemetry.moved(session, os.clock(), location)
                if location == "Island" then RunTelemetry.noteStep(session, "run", os.clock()) end
            end
        end)
        -- BD-649: MovementGuard already adds one to this attribute on every set-back; counting the change needs no change in MovementGuard.
        player:GetAttributeChangedSignal("MovementRejectCount"):Connect(function()
            RunTelemetry.bump(counters, "movement_rejects", nil, 1)
        end)
    end
    Players.PlayerAdded:Connect(join)
    for _, player in Players:GetPlayers() do join(player) end
    Players.PlayerRemoving:Connect(function(player)
        local session = sessions[player]
        if not session then return end
        emit(player, RunTelemetry.sessionEnd(session, os.clock(), {server = serverId, at = os.time()}))
        sessions[player] = nil
        TelemetryService.flush() -- a leaving player may be the last one: write the counters before the server can close
    end)
    pcall(function() game:BindToClose(function() TelemetryService.flush() end) end)
    pcall(function()
        task.spawn(function()
            while true do
                task.wait(RunTelemetry.RollupSeconds)
                TelemetryService.flush()
            end
        end)
    end)
end

return TelemetryService
