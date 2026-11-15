--!strict
-- BD-1199 (docs/239): the server half of the gentle run streak, behind Config.PlayAgainEnabled (every caller checks the flag first, and this
-- module is required lazily, so with the flag off it never loads). SESSION-ONLY memory, nothing is saved: leaving the game or waiting longer than
-- Config.RunStreakWindowSeconds simply starts again at 1. The client never sends a streak or a bonus; it only reads the owner-only numbers below.
--   onBegin   run starts: the streak of THIS run (from the previous run end, server clock) -> owner-only RunStreak, remembered per run id
--   onEnd     run ends: remembers the end time, shows the streak on Run Complete (owner-only LastRunStreak)
--   bonusFor  settlement asks: crystals for this run id (0 unless the run was real and its bonus is not yet paid)
--   committed settlement stored: marks the run paid (exactly once on top of the settlement ledger) and shows the bonus (owner-only LastRunStreakCrystals)
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config) :: any
local Rules = require(ReplicatedStorage.Shared.PlayAgain)
local PrivateState = require(script.Parent.PrivateState)

local Service = {}
type Memory = {streak: number, lastEndAt: number?, runs: {[string]: number}, paid: {[string]: boolean}}
local memory: {[Player]: Memory} = setmetatable({}, {__mode = "k"}) :: any
local MAX_RUNS = 8 -- a run that never settled cannot pin entries for ever

local function of(player: Player): Memory
    local m = memory[player]
    if not m then
        m = {streak = 0, lastEndAt = nil, runs = {}, paid = {}}
        memory[player] = m
    end
    return m
end

function Service.onBegin(player: Player, runId: string, now: number): number
    local m = of(player)
    local streak = Rules.nextStreak(m.streak, m.lastEndAt, now, Config.RunStreakWindowSeconds)
    m.streak = streak
    local count = 0
    for _ in m.runs do count += 1 end
    if count >= MAX_RUNS then m.runs, m.paid = {}, {} end
    m.runs[runId] = streak
    PrivateState.set(player, "RunStreak", streak)
    return streak
end

function Service.onEnd(player: Player, runId: string, now: number)
    local m = of(player)
    m.lastEndAt = now
    PrivateState.set(player, "LastRunStreak", m.runs[runId] or 0)
    PrivateState.set(player, "LastRunStreakCrystals", 0) -- until the settlement says otherwise
end

function Service.bonusFor(player: Player, runId: string, catchScore: any, runSeconds: any): number
    local m = memory[player]
    if not m or m.paid[runId] then return 0 end
    local streak = m.runs[runId]
    if not streak then return 0 end
    if not Rules.qualifies(catchScore, runSeconds, Config.RunStreakMinRunSeconds) then return 0 end
    return Rules.crystalsFor(streak, Config.RunStreakCrystals)
end

function Service.committed(player: Player, runId: string, bonus: number)
    local m = memory[player]
    if not m then return end
    m.paid[runId] = true
    PrivateState.set(player, "LastRunStreakCrystals", bonus)
end

function Service.streakOf(player: Player): number
    local m = memory[player]
    return if m then m.streak else 0
end

return Service
