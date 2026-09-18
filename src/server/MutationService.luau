--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local MutationService = {}
local lastMutation: {[Player]: number} = {}
local lastSetup: {[Player]: number} = {}

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
    if now - last < Config.MutationRequestCooldownSeconds then return false end
    bucket[player] = now
    return true
end

function MutationService.start(profileRepository, dinosaur)
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local mutate = getRemote(folder, "MutateSpecies")
    local setupTest = getRemote(folder, "TestSetMutationCopies")

    mutate.OnServerEvent:Connect(function(player: Player, speciesId, targetMutation, requestToken, ...)
        if select("#", ...) ~= 0 then return end
        if typeof(speciesId) ~= "string" or #speciesId < 1 or #speciesId > 32 then
            player:SetAttribute("LastMutationStatus", "invalid_species")
            return
        end
        if targetMutation ~= "gold" then
            player:SetAttribute("LastMutationStatus", "unknown_mutation")
            return
        end
        if typeof(requestToken) ~= "string" or #requestToken < 1 or #requestToken > 80 then
            player:SetAttribute("LastMutationStatus", "invalid_token")
            return
        end
        if not allowed(lastMutation, player) then
            player:SetAttribute("LastMutationStatus", "rate_limited")
            return
        end

        local ok, _, status = profileRepository.mutateSpecies(player, speciesId, targetMutation, requestToken)
        player:SetAttribute("LastMutationStatus", status)
        if ok then
            player:SetAttribute("LastMutationToken", requestToken)
            local character = player.Character
            if character and character:GetAttribute("DinoAttached") then
                dinosaur.refreshForPlayer(character, player)
            end
        end
    end)

    setupTest.OnServerEvent:Connect(function(player: Player, baseCount, ...)
        if select("#", ...) ~= 0 then return end
        if not Config.MutationTestSetupEnabled then return end
        if typeof(baseCount) ~= "number" or baseCount % 1 ~= 0 then
            player:SetAttribute("LastMutationSetupStatus", "bad_count")
            return
        end
        if not allowed(lastSetup, player) then
            player:SetAttribute("LastMutationSetupStatus", "rate_limited")
            return
        end
        local ok, status = profileRepository.setMutationTestCopies(
            player, Config.MutationTestSpeciesId, baseCount
        )
        player:SetAttribute("LastMutationSetupStatus", status)
        if ok then
            local character = player.Character
            if character and character:GetAttribute("DinoAttached") then
                dinosaur.refreshForPlayer(character, player)
            end
        end
    end)

    Players.PlayerRemoving:Connect(function(player)
        lastMutation[player] = nil
        lastSetup[player] = nil
    end)
end

return MutationService
