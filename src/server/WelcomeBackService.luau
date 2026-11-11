--!strict
-- BD-1168 (docs/221 section 3 and 4): the server half of the welcome-back card. Behind Config.WelcomeBackEnabled (default false, on
-- only in the playtest profile); with the flag off start() returns at once: no connection, no table, no value sent.
-- When a save finishes loading, it reads the three nest facts ProfileRepository kept in memory for this join (brand-new save, ready
-- nests as stored, ready nests now), applies the pure rule Shared/WelcomeBack.finishedAway and, when at least one nest finished
-- while the player was away, sets the owner-only value WelcomeBackNests ONCE for this join. The client only shows it.
-- No remote, no client input, no profile write, no reward: a number the owner could already work out from NestsJson.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local WelcomeBack = require(ReplicatedStorage.Shared.WelcomeBack)
local PrivateState = require(script.Parent.PrivateState)

local WelcomeBackService = {}
local started = false
local told: {[Player]: boolean} = setmetatable({}, {__mode = "k"}) :: any

local function enabled(): boolean
    return (Config :: any).WelcomeBackEnabled == true
end

function WelcomeBackService.start()
    if not enabled() then return end
    if started then return end
    started = true
    local repository = require(script.Parent.ProfileRepository) :: any

    local function tell(player: Player)
        if told[player] or player:GetAttribute("ProfileState") ~= "Loaded" then return end
        told[player] = true -- once per join, whatever the save says later
        pcall(function()
            local info = repository.welcomeInfo(player)
            if typeof(info) ~= "table" then return end
            local count = WelcomeBack.finishedAway(info.isNew, info.readyBefore, info.readyAfter)
            if count > 0 then PrivateState.set(player, "WelcomeBackNests", count) end
        end)
    end
    local function join(player: Player)
        player:GetAttributeChangedSignal("ProfileState"):Connect(function() tell(player) end)
        tell(player)
    end
    Players.PlayerAdded:Connect(join)
    for _, player in Players:GetPlayers() do join(player) end
end

return WelcomeBackService
