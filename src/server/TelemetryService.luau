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

-- Called by the settlement callback in Bootstrap after the commit; outcome is the committed run outcome table (may be nil).
function TelemetryService.runSettled(player: Player, reason: string, runSeconds: number, outcome: any)
    if not enabled() then return end
    local session = sessions[player]
    if session then RunTelemetry.runFinished(session) end
    local o = if typeof(outcome) == "table" then outcome else {}
    emit(player, RunTelemetry.runEnd({
        runSeconds = runSeconds, reason = reason,
        eggs = o.eggCount or o.chestCount, nests = o.nestCount, crystals = o.crystals,
        foodCatchRate = Config.FoodCatchRate,
    }))
end

function TelemetryService.start()
    if not enabled() then return end
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
