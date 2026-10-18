--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local MutationService = {}
local CooldownMemory = require(script.Parent.CooldownMemory)
local cooldowns = CooldownMemory.new(120) -- BD-363: keyed by UserId, survives a rejoin
local lastMutation = "lastMutation"
local lastSetup = "lastSetup"

local function getRemote(folder: Folder, name: string): RemoteEvent
    local existing = folder:FindFirstChild(name)
    if existing and existing:IsA("RemoteEvent") then return existing end
    if existing then existing:Destroy() end
    local remote = Instance.new("RemoteEvent")
    remote.Name = name
    remote.Parent = folder
    return remote
end

local function allowed(bucket: string, player: Player): boolean
    return cooldowns.allow(player.UserId, bucket, os.clock(), Config.MutationRequestCooldownSeconds)
end

function MutationService.start(profileRepository, dinosaur)
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local mutate = getRemote(folder, "MutateSpecies")
    -- BD-610: exists ONLY while its flag is on (pinned off in every release profile); the flag is still re-checked inside the handler.
    local setupTest = if Config.MutationTestSetupEnabled == true then getRemote(folder, "TestSetMutationCopies") else nil

    mutate.OnServerEvent:Connect(function(player: Player, speciesId, targetMutation, requestToken, ...)
        if select("#", ...) ~= 0 then return end
        -- docs/155 s6 item 1 / docs/157: once the identity fusion path (6 Base -> Gold, 3 Gold -> Emerald, 2 Emerald -> Diamond,
        -- FusionAction) is on, the Build 020 50-copy shortcut (no Emerald, no odds, no consent, no lineage) is closed on the server.
        -- The client page for it is already unreachable in the playtest profile (FusionSelection.navTarget); this stops a hand-fired remote.
        if Config.IdentityFusionPreviewEnabled == true then
            player:SetAttribute("LastMutationStatus", "fusion_moved")
            return
        end
        if typeof(speciesId) ~= "string" or #speciesId < 1 or #speciesId > 32 then
            player:SetAttribute("LastMutationStatus", "invalid_species")
            return
        end
        if targetMutation ~= "gold" and targetMutation ~= "diamond" then
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

    if setupTest then
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
    end
end

return MutationService
