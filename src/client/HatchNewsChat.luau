--!strict
-- BD-1227 (docs/242 gap 17, flag Config.RareHatchNewsEnabled): the rare hatch news as ONE plain system line in the Roblox chat window, next to the banner
-- ("Mia hatched a Legendary T-Rex!"). Required by RareHatchClient only while the flag is on. The server decided and rate-limited it (RareHatch.offer /
-- flush: best egg of a burst, one per hatcher per 45 s, 4 per 10 s for the server); this file re-checks the payload (RareHatch.newsFromPayload: known
-- kind, real tier, clean species and display name) and posts nothing when a check fails or the new chat is not in use. No free text, nothing sent back.
local TextChatService = game:GetService("TextChatService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rare = require(Shared:WaitForChild("RareHatch"))
local RarityWord = require(Shared:WaitForChild("RarityWord"))

local Chat = {}
Chat.Color = "#FFD86B" -- soft gold, the rare-find colour

function Chat.post(data: any)
    local news = Rare.newsFromPayload(data, RarityWord.Names)
    if news == nil then return end
    pcall(function()
        if TextChatService.ChatVersion ~= Enum.ChatVersion.TextChatService then return end
        local channels = TextChatService:FindFirstChild("TextChannels")
        local general = if channels then channels:FindFirstChild("RBXGeneral") else nil
        if general and general:IsA("TextChannel") then
            general:DisplaySystemMessage(string.format('<font color="%s">%s</font>', Chat.Color, news.line))
        end
    end)
end

return Chat
