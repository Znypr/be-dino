--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local MutationService = {}
local CooldownMemory = require(script.Parent.CooldownMemory)
local cooldowns = CooldownMemory.new(120) -- BD-363: keyed by UserId, survives a rejoin
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

    -- BD-617 (LEAD decision, owner directive 2026-10-18): the Build 020 "MutateSpecies" remote (50 copies -> Gold / Diamond, no Emerald, no odds,
    -- no consent, no lineage) is REMOVED. Fusion is the FusionAction remote (6 Base -> Gold, 3 Gold -> Emerald, 2 Emerald -> Diamond).
    -- The repository keeps its old 50-copy transaction as unreachable LEGACY code only so the recorded golden session and the
    -- Build 020 rollback proofs keep their bytes; nothing calls it.
    -- BD-610: exists ONLY while its flag is on (pinned off in every release profile); the flag is still re-checked inside the handler.
    local setupTest = if Config.MutationTestSetupEnabled == true then getRemote(folder, "TestSetMutationCopies") else nil

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
                if Config.RunTelemetryEnabled == true then pcall(function() require(script.Parent.TelemetryHook).count("rate_limited", "MutationTest") end) end -- BD-650
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
