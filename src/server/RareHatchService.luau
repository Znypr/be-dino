--!strict
-- BD-428: server side of the rare-hatch celebration (rules in src/shared/RareHatch.luau). ProfileRepository.publishHatch hands
-- every SETTLED hatch outcome to RareHatchService.record; nothing here reads client input. The hatcher gets a "me" message
-- (celebration), everyone else gets at most one "all" announcement per hatcher window (best egg only), rate limited.
-- Remote: ReplicatedStorage.BeDinoRemotes.RareHatch (server -> client only; the server ignores anything a client sends).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local Config = require(ReplicatedStorage.Shared.Config)
local Rare = require(ReplicatedStorage.Shared.RareHatch)
local CooldownMemory = require(script.Parent.CooldownMemory)

local Service = {}
local state = Rare.newState()
local remote: RemoteEvent? = nil
-- BD-439: the 45 s announcement cooldown is UserId-keyed memory, so leaving and rejoining does not reset it (Rare.forget only drops the open window).
local announced = CooldownMemory.new(math.max(120, Rare.Cooldown * 2))
local ANNOUNCE_KEY = "announce"

local function getRemote(): RemoteEvent
    if remote then return remote end
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local found = (folder :: Folder):FindFirstChild("RareHatch")
    if found and found:IsA("RemoteEvent") then remote = found return found end
    local event = Instance.new("RemoteEvent")
    event.Name = "RareHatch"
    event.Parent = folder
    remote = event
    return event
end

function Service.start()
    getRemote()
    Players.PlayerRemoving:Connect(function(player: Player) Rare.forget(state, player.UserId) end)
end

-- committedOutcome comes from the profile transaction (speciesId, shiny, eventMutationId, failed, eggId).
function Service.record(player: Player, outcome: any)
    local ok, err = pcall(function()
        local species = outcome.speciesId
        local info = Rare.classify(outcome, Config.SpeciesRarities[species])
        if not info then return end
        local speciesName = Config.SpeciesDisplayNames[species] or species
        local event = getRemote()
        local eggId = tostring(outcome.eggId or "")
        if eggId == "" or state.seen[eggId] then return end -- one celebration and one announcement per egg
        event:FireClient(player, {k = "me", kind = info.kind, text = Rare.ownText(info, speciesName), rarity = Config.SpeciesRarities[species] or 1})
        local text = Rare.text(player.DisplayName, info, speciesName)
        local flushAt = nil
        if os.clock() - announced.last(player.UserId, ANNOUNCE_KEY) >= Rare.Cooldown then
            flushAt = Rare.offer(state, player.UserId, eggId, info, text, os.clock())
        else
            state.seen[eggId] = true -- quiet: still one celebration per egg
        end
        if flushAt then
            local userId = player.UserId
            task.delay(flushAt - os.clock(), function()
                local out = Rare.flush(state, userId, os.clock())
                if not out then return end
                announced.mark(userId, ANNOUNCE_KEY, os.clock())
                for _, other in Players:GetPlayers() do
                    if other ~= player then event:FireClient(other, {k = "all", kind = out.info.kind, text = out.text}) end
                end
            end)
        end
    end)
    if not ok then warn("[Be Dino] rare hatch announce failed: " .. tostring(err)) end
end

return Service
