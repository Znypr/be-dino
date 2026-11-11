--!strict
-- BD-1163 (docs/225): the server half of the starter run. Behind Config.StarterRunEnabled (default false, on only in the playtest
-- profile); with the flag off start() returns at once: no connection, no thread, no table.
-- A brand-new save (zero settled runs: ProfileRepository sets the owner-only value StarterRun = 1 from the pure rule
-- FtueRules.starterQualifies) does not have to find and press EXPLORE: when its dinosaur stands ready in the hub, the server starts the
-- first run through the ONE run-start path, RunLifecycle.requestStart (same checks: save loaded, world ready, dinosaur attached, room
-- for the eggs). Once per join, for a bounded time; a save that already settled a run is never touched.
-- The egg floor and the safe eggs are part of the settlement (ProfileEggs.commitRunSettlement); nothing is paid, stored or sent here.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local FtueRules = require(ReplicatedStorage.Shared.FtueRules)
local PrivateState = require(script.Parent.PrivateState)

local StarterRunService = {}
StarterRunService.TrySeconds = 90 -- the world gate alone can take Config.WorldReadyTimeoutSeconds on a slow device
StarterRunService.StepSeconds = 0.5
local started = false
local autoStarted: {[Player]: boolean} = setmetatable({}, {__mode = "k"}) :: any

local function enabled(): boolean
    return (Config :: any).StarterRunEnabled == true
end

function StarterRunService.start()
    if not enabled() then return end
    if started then return end
    started = true
    local RunLifecycle = require(script.Parent.RunLifecycle) :: any

    local function isStarter(player: Player): boolean
        return PrivateState.get(player, "StarterRun") == 1
    end
    local function watch(player: Player, character: Model)
        if autoStarted[player] or not isStarter(player) then return end
        task.spawn(function()
            local deadline = os.clock() + StarterRunService.TrySeconds
            while os.clock() < deadline and player.Parent ~= nil and player.Character == character do
                if autoStarted[player] or not isStarter(player) then return end
                local attached = character:GetAttribute("DinoAttached")
                if FtueRules.starterAutoStart({enabled = enabled(), starter = true, started = false,
                    runState = character:GetAttribute("RunState"), attached = attached ~= nil and attached ~= false}) then
                    local ok, began = pcall(RunLifecycle.requestStart, player)
                    if ok and began == true then
                        autoStarted[player] = true -- once per join: after a starter run that found nothing the child presses EXPLORE like everyone
                        return
                    end
                end
                task.wait(StarterRunService.StepSeconds)
            end
        end)
    end
    local function join(player: Player)
        player.CharacterAdded:Connect(function(character) watch(player, character) end)
        local character = player.Character
        if character then watch(player, character) end
    end
    Players.PlayerAdded:Connect(join)
    for _, player in Players:GetPlayers() do join(player) end
end

return StarterRunService
