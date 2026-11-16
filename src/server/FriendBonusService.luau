--!strict
-- BD-1228 (docs/242 gap 17): the server half of the friend bonus. Behind Config.FriendBonusEnabled (default false, ON only in the playtest profile);
-- with the flag off start() returns at once (no connection, no web call) and bonusFor() answers 0.
-- On every join and leave it asks Roblox (Player:IsFriendsWith, protected, cached per pair for FriendBonus.Seconds) whether each player has a friend in
-- this server and sets the owner-only value FriendBonus (percent, 0 = none). The settlement asks bonusFor(player, baseCrystals) before its transaction
-- (ProfileEggs), so the run id makes the extra crystals exactly-once. The client never sends anything; nothing is stored.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config) :: any
local F = require(ReplicatedStorage.Shared.FriendBonus)
local PrivateState = require(script.Parent.PrivateState)

local Service = {}
local started = false
local cache: {[string]: {yes: boolean, at: number}} = {}
local has: {[Player]: boolean} = setmetatable({}, {__mode = "k"}) :: any

local function enabled(): boolean return Config.FriendBonusEnabled == true end

local function isFriend(a: number, b: number): boolean
    local key = F.pairKey(a, b)
    local hit = cache[key]
    if hit and os.clock() - hit.at < F.Seconds then return hit.yes end
    local player = Players:GetPlayerByUserId(a)
    if not player then return false end
    local ok, yes = pcall(function() return player:IsFriendsWith(b) end)
    local answer = ok and yes == true
    cache[key] = {yes = answer, at = os.clock()}
    return answer
end

local function refresh()
    local ids = {}
    for _, p in Players:GetPlayers() do table.insert(ids, p.UserId) end
    local percent = F.percent(Config.FriendBonusPercent)
    for _, p in Players:GetPlayers() do
        local yes = #ids > 1 and F.hasFriend(p.UserId, ids, isFriend)
        if has[p] ~= yes then
            has[p] = yes
            PrivateState.set(p, "FriendBonus", if yes then percent else 0)
        end
    end
end

function Service.start()
    if not enabled() or started then return end
    started = true
    Players.PlayerAdded:Connect(function() task.spawn(refresh) end)
    Players.PlayerRemoving:Connect(function(leaving: Player)
        has[leaving] = nil
        for key in cache do
            if string.find(":" .. key .. ":", ":" .. leaving.UserId .. ":", 1, true) then cache[key] = nil end
        end
        task.defer(refresh) -- after the player is gone from GetPlayers
    end)
    task.spawn(refresh)
end

-- Extra crystals for this settlement (0 with the flag off or without a friend in the server right now).
function Service.bonusFor(player: Player, baseCrystals: any): number
    if not enabled() then return 0 end
    return F.crystals(baseCrystals, Config.FriendBonusPercent, has[player] == true)
end

return Service
