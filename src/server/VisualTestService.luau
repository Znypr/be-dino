--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local VisualTestService = {}
local lastRequest: {[Player]: number} = {}

local function validSpecies(speciesId: any): boolean
    if typeof(speciesId) ~= "string" then return false end
    for _, id in Config.SpeciesOrder do
        if id == speciesId then return true end
    end
    return false
end

function VisualTestService.start(dinosaur)
    if not Config.ArtTestHarnessEnabled then return end

    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end

    local preview = Instance.new("RemoteEvent")
    preview.Name = "PreviewDinosaurArt"
    preview.Parent = folder

    preview.OnServerEvent:Connect(function(player: Player, speciesId, gold, restore, ...)
        if select("#", ...) ~= 0 then return end
        if typeof(restore) ~= "boolean" then return end

        local now = os.clock()
        local last = lastRequest[player] or -math.huge
        if now - last < Config.ArtPreviewRequestCooldownSeconds then return end
        lastRequest[player] = now

        local character = player.Character
        if not character or not character:GetAttribute("DinoAttached")
            or character:GetAttribute("RunState") ~= "Active" then
            return
        end

        if restore then
            dinosaur.refreshForPlayer(character, player)
            player:SetAttribute("ArtPreviewStatus", "SAVED EQUIP")
            return
        end
        if not validSpecies(speciesId) or typeof(gold) ~= "boolean" then return end

        dinosaur.setSpecies(character, speciesId, gold)
        player:SetAttribute("ArtPreviewStatus",
            (if gold then "GOLD " else "") .. string.upper(speciesId))
    end)

    Players.PlayerRemoving:Connect(function(player)
        lastRequest[player] = nil
    end)
end

return VisualTestService
