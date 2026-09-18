--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local ChestService = {}
local lastClaim: {[Player]: number} = {}
local lastGrant: {[Player]: number} = {}

local function getRemote(folder: Folder, name: string): RemoteEvent
    local existing = folder:FindFirstChild(name)
    if existing and existing:IsA("RemoteEvent") then return existing end
    if existing then existing:Destroy() end
    local remote = Instance.new("RemoteEvent")
    remote.Name = name
    remote.Parent = folder
    return remote
end

local function allowed(bucket: {[Player]: number}, player: Player): boolean
    local now = os.clock()
    local last = bucket[player] or -math.huge
    if now - last < Config.ChestClaimRequestCooldownSeconds then return false end
    bucket[player] = now
    return true
end

function ChestService.start(profileRepository)
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local claimChest = getRemote(folder, "ClaimChest")
    local testGrant = getRemote(folder, "TestGrantChests")

    claimChest.OnServerEvent:Connect(function(player: Player, chestId, requestToken, ...)
        if select("#", ...) ~= 0 then return end
        if typeof(chestId) ~= "string" or #chestId < 1 or #chestId > 80 then
            player:SetAttribute("LastChestClaimStatus", "invalid_chest_id")
            return
        end
        if typeof(requestToken) ~= "string" or #requestToken < 1 or #requestToken > 80 then
            player:SetAttribute("LastChestClaimStatus", "invalid_token")
            return
        end
        if not allowed(lastClaim, player) then
            player:SetAttribute("LastChestClaimStatus", "rate_limited")
            return
        end
        local _, _, status = profileRepository.claimChest(player, chestId)
        player:SetAttribute("LastChestClaimStatus", status)
    end)

    testGrant.OnServerEvent:Connect(function(player: Player, ...)
        if select("#", ...) ~= 0 then return end
        if not Config.ChestTestGrantEnabled then return end
        if not allowed(lastGrant, player) then
            player:SetAttribute("LastChestTestGrantStatus", "rate_limited")
            return
        end
        local _, status = profileRepository.grantChestTest(player)
        player:SetAttribute("LastChestTestGrantStatus", status)
    end)

    Players.PlayerRemoving:Connect(function(player)
        lastClaim[player] = nil
        lastGrant[player] = nil
    end)
end

return ChestService
