--!strict
-- BD-085 / BD-322 phone QA kit (docs/127). Owner-only: the client QA overlay sends a labelled snapshot and the server prints it as
-- ONE "[BD-QA] {json}" line (tools/qa/phone_report.py turns those lines into a table). Authorization is re-checked here; the
-- client overlay grants nothing. Does nothing at all (no remote, no attribute) while Config.QaOverlayEnabled is false (the default).
-- Never touches profiles, rewards or gameplay.
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Config = require(ReplicatedStorage.Shared.Config)
local Rules = require(ReplicatedStorage.Shared.QaOverlayRules)
local PrivateState = require(script.Parent.PrivateState)

local QaService = {}
local allowed: {[Player]: boolean} = {}
local lastMark: {[Player]: number} = {}
local seq = 0

function QaService.start()
    if not Config.QaOverlayEnabled then return end
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes") :: Folder?
    if not folder then
        local created = Instance.new("Folder")
        created.Name = "BeDinoRemotes"
        created.Parent = ReplicatedStorage
        folder = created
    end
    local remote = Instance.new("RemoteEvent")
    remote.Name = "QaMark"
    remote.Parent = folder
    local function authorize(player: Player)
        local ok = Rules.allowed({
            userId = player.UserId, allowedIds = Config.QaOverlayUserIds,
            unpublishedStudio = RunService:IsStudio() and game.GameId == 0, enabled = Config.QaOverlayEnabled,
        })
        if not player.Parent then return end
        allowed[player] = ok
        PrivateState.set(player, "QaOverlay", ok) -- display hint only; marks are checked against `allowed`
    end
    Players.PlayerAdded:Connect(authorize)
    for _, player in Players:GetPlayers() do authorize(player) end
    Players.PlayerRemoving:Connect(function(player) allowed[player] = nil lastMark[player] = nil end)
    remote.OnServerEvent:Connect(function(player: Player, raw: any)
        if allowed[player] ~= true then return end
        local now = os.clock()
        if not Rules.mayMark(lastMark[player], now) then return end
        lastMark[player] = now
        local snapshot = Rules.sanitize(raw)
        if not snapshot then return end
        seq += 1
        snapshot.seq, snapshot.serverTime, snapshot.players = seq, os.time(), #Players:GetPlayers()
        print(Rules.LogTag .. " " .. HttpService:JSONEncode(snapshot))
    end)
end

return QaService
