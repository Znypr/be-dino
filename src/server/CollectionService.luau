--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local CollectionService = {}
local CooldownMemory = require(script.Parent.CooldownMemory)
local cooldowns = CooldownMemory.new(120) -- BD-363: keyed by UserId, survives a rejoin
local lastEquipRequest = "lastEquipRequest"
local lastGrantRequest = "lastGrantRequest"

local function getRemote(folder: Folder, name: string): RemoteEvent
    local existing = folder:FindFirstChild(name)
    if existing and existing:IsA("RemoteEvent") then return existing end
    if existing then existing:Destroy() end
    local remote = Instance.new("RemoteEvent")
    remote.Name = name
    remote.Parent = folder
    return remote
end

local function rateAllowed(bucket: string, player: Player): boolean
    return cooldowns.allow(player.UserId, bucket, os.clock(), Config.EquipRequestCooldownSeconds)
end

function CollectionService.start(profileRepository, dinosaur)
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local equipSpecies = getRemote(folder :: Folder, "EquipSpecies")
    -- BD-610: exists ONLY while its flag is on (pinned off in every release profile); the flag is still re-checked inside the handler.
    local testGrant = if Config.CollectionTestGrantEnabled == true then getRemote(folder :: Folder, "TestGrantSpecies") else nil

    equipSpecies.OnServerEvent:Connect(function(player: Player, speciesId, requestToken, variantKey, ...)
        if select("#", ...) ~= 0 then return end
        -- BD-150: optional exact copy (EggTraits variant key); the repository checks the player owns it.
        if variantKey ~= nil and (typeof(variantKey) ~= "string" or #variantKey < 1 or #variantKey > 160) then
            player:SetAttribute("LastEquipStatus", "invalid_variant")
            return
        end
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

        local ok, status = profileRepository.equipSpecies(player, speciesId, variantKey)
        player:SetAttribute("LastEquipStatus", status)
        if not ok then return end
        if status == "already_equipped" then return end -- BD-618 (d): nothing changed, so there is nothing to render again

        local character = player.Character
        if character and character:GetAttribute("DinoAttached") then
            dinosaur.refreshForPlayer(character, player)
        end
    end)

    if testGrant then
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
    end
end

return CollectionService
