--!strict
-- BD-1166 (docs/122): the three inputs of the first-session funnel that TelemetryService must not fetch itself (it stays a read-only
-- observer without ids, profiles or remotes). Behind Config.RunTelemetryEnabled (default false, on only in the playtest profile);
-- with the flag off start() returns at once: no remote, no connection, no table.
--   1. FunnelBeat (RemoteEvent, client -> server): ONE whitelisted word saying which kind of screen is open (RunTelemetry.Beats).
--      Anything else is dropped. It changes no gameplay state, pays nothing and answers nothing; it only feeds `quit`,
--      `first_shop_open_s` and `first_index_open_s` of the anonymous session_end line. A lying client can only spoil its own line.
--   2. Save facts at join: "is this a brand-new save" and "days since the previous visit", read from ProfileRepository.joinInfo.
--   3. Friends in the server at join: a NUMBER. Player:IsFriendsWith yields, so it runs in its own thread, inside a pcall, for at
--      most RunTelemetry.MaxFriendChecks other players. The id it needs is used for that call only: never stored, printed or sent.
-- Nothing here prints, writes a profile, sets an attribute or fires a client.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local RunTelemetry = require(ReplicatedStorage.Shared.RunTelemetry)

local FunnelService = {}
local started = false

local function enabled(): boolean
    return (Config :: any).RunTelemetryEnabled == true
end

-- Yields (IsFriendsWith). `others` = the players already in the server; at most `cap` of them are asked. A failed look-up counts as
-- "not a friend". Kept free of services so the offline test can call it with plain tables.
function FunnelService.countFriends(player: any, others: {any}, cap: number): number
    local count, asked = 0, 0
    for _, other in others do
        if other ~= player then
            if asked >= cap then break end
            asked += 1
            local ok, isFriend = pcall(function() return player:IsFriendsWith(other.UserId) end)
            if ok and isFriend == true then count += 1 end
        end
    end
    return count
end

function FunnelService.start()
    if not enabled() then return end
    if started then return end
    started = true
    local telemetry = require(script.Parent.TelemetryService) :: any
    local repository = require(script.Parent.ProfileRepository) :: any

    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteEvent")
    remote.Name = "FunnelBeat"
    remote.Parent = folder
    remote.OnServerEvent:Connect(function(player: Player, word: any, ...: any)
        -- exactly one short string; the whitelist, the minimum gap and the per-visit budget are in RunTelemetry.beat
        if select("#", ...) ~= 0 or typeof(word) ~= "string" or #word > 16 then return end
        pcall(telemetry.beat, player, word)
    end)

    local function saveFacts(player: Player)
        if player:GetAttribute("ProfileState") ~= "Loaded" then return end
        pcall(function()
            local info = repository.joinInfo(player)
            if typeof(info) ~= "table" then return end
            telemetry.profileLoaded(player, info.isNew, RunTelemetry.daysSince(info.previousDay, info.today))
        end)
    end
    local function join(player: Player)
        player:GetAttributeChangedSignal("ProfileState"):Connect(function() saveFacts(player) end)
        saveFacts(player)
        task.spawn(function()
            task.wait() -- one step later: TelemetryService's own PlayerAdded handler has made the session by then, whatever the handler order
            local ok, count = pcall(FunnelService.countFriends, player, Players:GetPlayers(), RunTelemetry.MaxFriendChecks)
            if ok and player.Parent then pcall(telemetry.friends, player, count) end
        end)
    end
    Players.PlayerAdded:Connect(join)
    for _, player in Players:GetPlayers() do join(player) end
end

return FunnelService
