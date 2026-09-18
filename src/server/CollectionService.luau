--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local CollectionService = {}
local lastEquipRequest: {[Player]: number} = {}
local lastGrantRequest: {[Player]: number} = {}

local function getRemote(folder: Folder, name: string): RemoteEvent
    local existing = folder:FindFirstChild(name)
    if existing and existing:IsA("RemoteEvent") then return existing end
    if existing then existing:Destroy() end
    local remote = Instance.new("RemoteEvent")
    remote.Name = name
    remote.Parent = folder
    return remote
end

local function rateAllowed(bucket: {[Player]: number}, player: Player): boolean
    local now = os.clock()
    local last = bucket[player] or -math.huge
    if now - last < Config.EquipRequestCooldownSeconds then return false end
    bucket[player] = now
    return true
end

function CollectionService.start(profileRepository, dinosaur)
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local equipSpecies = getRemote(folder :: Folder, "EquipSpecies")
    local testGrant = getRemote(folder :: Folder, "TestGrantSpecies")

    equipSpecies.OnServerEvent:Connect(function(player: Player, speciesId, requestToken, ...)
        if select("#", ...) ~= 0 then return end
        if typeof(speciesId) ~= "string" or #speciesId < 1 or #speciesId > 32 then
            player:SetAttribute("LastEquipStatus", "invalid_species")
            return
        end
        if typeof(requestToken) ~= "string" or #requestToken < 1 or #requestToken > 80 then
            player:SetAttribute("LastEquipStatus", "invalid_token")
            return
        end
        if not rateAllowed(lastEquipRequest, player) then
            player:SetAttribute("LastEquipStatus", "rate_limited")
            return
        end

        local ok, status = profileRepository.equipSpecies(player, speciesId)
        player:SetAttribute("LastEquipStatus", status)
        if not ok then return end

        local character = player.Character
        if character and character:GetAttribute("DinoAttached") then
            dinosaur.setSpecies(character, speciesId)
        end
    end)

    testGrant.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 0 then return end
        if not Config.CollectionTestGrantEnabled then return end
        if not rateAllowed(lastGrantRequest, player) then
            player:SetAttribute("LastCollectionGrantStatus", "rate_limited")
            return
        end
        local _, status = profileRepository.grantCollectionTestSpecies(player)
        player:SetAttribute("LastCollectionGrantStatus", status)
    end)

    Players.PlayerRemoving:Connect(function(player)
        lastEquipRequest[player] = nil
        lastGrantRequest[player] = nil
    end)
end

return CollectionService
