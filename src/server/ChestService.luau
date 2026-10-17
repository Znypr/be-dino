--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local ChestService = {}
local CooldownMemory = require(script.Parent.CooldownMemory)
local cooldowns = CooldownMemory.new(120) -- BD-363: keyed by UserId, survives a rejoin
local lastClaim = "lastClaim"
local lastGrant = "lastGrant"
local lastNest = "lastNest"
local lastSkip = "lastSkip"
local lastSettings = "lastSettings"
local nestClaimCount: {[Player]: number} = setmetatable({}, {__mode = "k"}) :: any -- BD-618 (e): LastNestClaimAt is this counter, not the server clock

local function getRemote(folder: Folder, name: string): RemoteEvent
    local existing = folder:FindFirstChild(name)
    if existing and existing:IsA("RemoteEvent") then return existing end
    if existing then existing:Destroy() end
    local remote = Instance.new("RemoteEvent")
    remote.Name = name
    remote.Parent = folder
    return remote
end

local function allowed(bucket: string, player: Player, cooldown: number?): boolean
    return cooldowns.allow(player.UserId, bucket, os.clock(), cooldown or Config.ChestClaimRequestCooldownSeconds)
end

function ChestService.start(profileRepository)
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local claimChest = getRemote(folder, "ClaimChest")
    -- BD-610: the test-grant remote exists ONLY while its flag is on (pinned off in every release profile), so a published server has no
    -- handler for it at all; the flag is still re-checked inside the handler.
    local testGrant = if Config.ChestTestGrantEnabled == true then getRemote(folder, "TestGrantChests") else nil

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

    -- BD-090 egg nests: open one READY nest; its rolled eggs join the reveal line next.
    local claimNest = getRemote(folder, "ClaimNest")
    claimNest.OnServerEvent:Connect(function(player: Player, nestId, ...)
        if select("#", ...) ~= 0 then return end
        if typeof(nestId) ~= "string" or #nestId < 1 or #nestId > 80 then
            player:SetAttribute("LastNestClaimStatus", "invalid_nest_id")
            return
        end
        if not allowed(lastNest, player, Config.NestClaimRequestCooldownSeconds) then
            player:SetAttribute("LastNestClaimStatus", "rate_limited")
            return
        end
        local _, _, status = profileRepository.claimNest(player, nestId)
        player:SetAttribute("LastNestClaimStatus", status)
        nestClaimCount[player] = (nestClaimCount[player] or 0) + 1
        player:SetAttribute("LastNestClaimAt", nestClaimCount[player]) -- BD-618 (e): a per-player counter (was the server's os.clock()); it changes every request so the client always sees a repeat
    end)

    -- BD-044 reveal-skip preference (UI only; never affects rewards).
    local setSkip = getRemote(folder, "SetRevealSkip")
    setSkip.OnServerEvent:Connect(function(player: Player, selection, ...)
        if select("#", ...) ~= 0 then return end
        if not allowed(lastSkip, player, 1) then return end
        profileRepository.setRevealSkip(player, selection)
    end)

    -- BD-264 settings v2 (UI preferences only; never affects rewards). Normalized server-side.
    local setSettings = getRemote(folder, "SetSettings")
    setSettings.OnServerEvent:Connect(function(player: Player, selection, ...)
        if select("#", ...) ~= 0 then return end
        if not allowed(lastSettings, player, 0.5) then return end
        profileRepository.setSettings(player, selection)
    end)

    if testGrant then
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
    end
end

return ChestService
