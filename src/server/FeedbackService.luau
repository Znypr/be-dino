--!strict
-- Playtest feedback (docs/128), behind Config.PlaytestFeedbackEnabled (default false, on only in the playtest profile).
-- One RemoteEvent in BeDinoRemotes ("PlaytestFeedback"). Server rules: rate limit 1 per 2 min and 10 per session per player,
-- free text goes through TextService:FilterStringAsync and is NEVER stored or printed unfiltered; if filtering fails the text is
-- dropped and only the ratings are logged. Prints one "[BD-FEEDBACK] {json}" line. No UserId or name is logged. Gameplay is untouched.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TextService = game:GetService("TextService")
local Config = require(ReplicatedStorage.Shared.Config)
local Feedback = require(ReplicatedStorage.Shared.PlaytestFeedback)

local FeedbackService = {}
local sessions: {[Player]: {[string]: any}} = {}

local function enabled(): boolean
    return (Config :: any).PlaytestFeedbackEnabled == true
end

-- Returns the filtered text, or "" when the filter fails (never the raw text).
local function filtered(player: Player, text: string): string
    if text == "" then return "" end
    local ok, result = pcall(function()
        local obj = TextService:FilterStringAsync(text, player.UserId, Enum.TextFilterContext.PublicChat)
        return obj:GetNonChatStringForBroadcastAsync()
    end)
    if ok and typeof(result) == "string" then return result end
    return ""
end

function FeedbackService.start()
    if not enabled() then return end
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteEvent")
    remote.Name = "PlaytestFeedback"
    remote.Parent = folder
    local function join(player: Player)
        if sessions[player] then return end
        local session = Feedback.newSession()
        sessions[player] = session
        player:GetAttributeChangedSignal("Location"):Connect(function()
            if player:GetAttribute("Location") == "Island" then session.runs += 1 end
        end)
    end
    Players.PlayerAdded:Connect(join)
    for _, player in Players:GetPlayers() do join(player) end
    Players.PlayerRemoving:Connect(function(player) sessions[player] = nil end)
    remote.OnServerEvent:Connect(function(player: Player, payload: any)
        local session = sessions[player]
        local clean = Feedback.sanitize(payload)
        if not session or not clean then return end
        local ok, reason = Feedback.allow(session, os.clock())
        if not ok then
            remote:FireClient(player, reason) -- "wait" or "limit": the client shows a short kind message
            return
        end
        local location = if player:GetAttribute("Location") == "Island" then "Run" else "Hub"
        print(Feedback.line(Feedback.event({
            fun = clean.fun, level = clean.level, looks = clean.looks, filteredText = filtered(player, clean.text),
            runs = session.runs, location = location, species = player:GetAttribute("EquippedSpeciesId"),
        })))
        remote:FireClient(player, "ok")
    end)
end

return FeedbackService
