--!strict
-- BD-426: server-side playtest telemetry, behind Config.RunTelemetryEnabled (default false, on only in the playtest profile).
-- Read-only observer: it never writes a profile, an attribute or a remote. Events go to AnalyticsService custom events when the
-- API exists (pcall) and always to the server log as one JSON line each, which tools/telemetry_report.py aggregates.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local RunTelemetry = require(ReplicatedStorage.Shared.RunTelemetry)

local TelemetryService = {}
local sessions: {[Player]: {[string]: any}} = {}
local limiter = RunTelemetry.newLimiter()
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

-- BD-575: called by FoodService at most once per player per food tick (already batched there) and only while the flag is on. Pure memory:
-- nothing is stored or sent to a client. A new runId starts a fresh accumulator, so a run that never settled cannot leak into the next.
function TelemetryService.noteFood(player: Player, runId: any, rawPoints: number, gainedPoints: number)
    if not enabled() then return end
    local rid = if typeof(runId) == "string" then runId else nil
    local stats = runStats[player]
    if not stats or stats.runId ~= rid then
        stats = RunTelemetry.newRunStats(rid)
        runStats[player] = stats
    end
    RunTelemetry.noteFood(stats, rawPoints, gainedPoints, Config.FoodCatchRate)
end

-- Called by the settlement callback in Bootstrap after the commit; outcome is the committed run outcome table (may be nil).
function TelemetryService.runSettled(player: Player, reason: string, runSeconds: number, outcome: any, runId: any?)
    if not enabled() then return end
    local session = sessions[player]
    if session then RunTelemetry.runFinished(session) end
    local o = if typeof(outcome) == "table" then outcome else {}
    local stats = runStats[player]
    runStats[player] = nil -- one run, one accumulator
    if stats and runId ~= nil and stats.runId ~= runId then stats = nil end -- food of some other run is not this run's food
    local nowServer = workspace:GetServerTimeNow()
    emit(player, RunTelemetry.runEnd({
        runSeconds = runSeconds, reason = reason,
        eggs = o.eggCount or o.chestCount, nests = o.nestCount, crystals = o.crystals,
        foodCatchRate = Config.FoodCatchRate,
        foodRaw = if stats then stats.foodRaw else 0, -- no food tick for this run = it really ate nothing
        eggsFood = if stats then stats.eggsFood else 0,
        weatherSeconds = RunTelemetry.weatherSeconds(weatherLog, nowServer - (if typeof(runSeconds) == "number" then runSeconds else 0), nowServer),
    }))
end

function TelemetryService.start()
    if not enabled() then return end
    -- BD-575: weather intervals on the server clock (the same clock the run length uses); an event-driven log, no polling.
    RunTelemetry.weatherChanged(weatherLog, workspace:GetAttribute("WeatherId"), workspace:GetServerTimeNow())
    workspace:GetAttributeChangedSignal("WeatherId"):Connect(function()
        RunTelemetry.weatherChanged(weatherLog, workspace:GetAttribute("WeatherId"), workspace:GetServerTimeNow())
    end)
    local function join(player: Player)
        if sessions[player] then return end
        sessions[player] = RunTelemetry.newSession(os.clock(), "Sanctuary")
        player:GetAttributeChangedSignal("Location"):Connect(function()
            local session = sessions[player]
            local location = player:GetAttribute("Location")
            if session and typeof(location) == "string" then RunTelemetry.moved(session, os.clock(), location) end
        end)
    end
    Players.PlayerAdded:Connect(join)
    for _, player in Players:GetPlayers() do join(player) end
    Players.PlayerRemoving:Connect(function(player)
        local session = sessions[player]
        if not session then return end
        emit(player, RunTelemetry.sessionEnd(session, os.clock()))
        sessions[player] = nil
    end)
end

return TelemetryService
