--!strict
-- BD-1229 (docs/242 gap 18): BadgeService awards, behind Config.BadgesEnabled (default false, ON only in the playtest profile).
-- Which badge a moment earns is decided by the pure Shared/BadgeTable from SERVER facts only: the profile finished loading (welcome) and the
-- settled hatch outcome (ProfileEggs.publishHatch hands it over). A badge whose id is still 0 (the owner has not created it) is skipped.
-- Every award is protected (pcall), done once per player and key per session (UserHasBadgeAsync first, then AwardBadge), one at a time per
-- player so Roblox's badge limits are respected. Nothing is stored in the profile; Roblox keeps the badge.
local BadgeService = game:GetService("BadgeService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config) :: any
local B = require(ReplicatedStorage.Shared.BadgeTable)

local Service = {}
local started = false
local done: {[Player]: {[string]: boolean}} = setmetatable({}, {__mode = "k"}) :: any
local queue: {[Player]: {string}} = setmetatable({}, {__mode = "k"}) :: any
local busy: {[Player]: boolean} = setmetatable({}, {__mode = "k"}) :: any
Service.stats = {awarded = 0, skipped = 0, queued = 0} -- counters for the Studio check

local function enabled(): boolean return Config.BadgesEnabled == true end

local function drain(player: Player)
    if busy[player] then return end
    busy[player] = true
    task.spawn(function()
        while player.Parent and queue[player] and #queue[player] > 0 do
            local key = table.remove(queue[player], 1) :: string
            local id = B.idOf(key)
            if id then
                pcall(function()
                    if not BadgeService:UserHasBadgeAsync(player.UserId, id) then
                        BadgeService:AwardBadge(player.UserId, id)
                        Service.stats.awarded += 1
                    end
                end)
            else
                Service.stats.skipped += 1 -- the owner has not created this badge yet
            end
        end
        busy[player] = false
    end)
end

-- Queue badge keys for a player (each key at most once per session).
function Service.award(player: Player, keys: {string})
    if not enabled() then return end
    local seen = done[player] or {}
    done[player] = seen
    local list = queue[player] or {}
    queue[player] = list
    for _, key in keys do
        if not seen[key] then
            seen[key] = true
            Service.stats.queued += 1
            table.insert(list, key)
        end
    end
    drain(player)
end

local function speciesTotal(): number
    local n = 0
    for _ in Config.SpeciesRarities do n += 1 end
    return n
end

-- A settled hatch (ProfileEggs.publishHatch). found = species this save owns after the hatch.
function Service.onHatch(player: Player, outcome: any, found: number?)
    if not enabled() or type(outcome) ~= "table" then return end
    Service.award(player, B.forHatch(outcome, Config.SpeciesRarities[outcome.speciesId], found, speciesTotal()))
end

function Service.start()
    if not enabled() or started then return end
    started = true
    local function join(player: Player)
        local function loaded()
            if player:GetAttribute("ProfileState") == "Loaded" then Service.award(player, {"welcome"}) end
        end
        player:GetAttributeChangedSignal("ProfileState"):Connect(loaded)
        loaded()
    end
    Players.PlayerAdded:Connect(join)
    for _, player in Players:GetPlayers() do join(player) end
end

return Service
