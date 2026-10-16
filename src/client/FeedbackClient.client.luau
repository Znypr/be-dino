--!strict
-- Playtest feedback button (docs/128), behind Config.PlaytestFeedbackEnabled (default false). Own ScreenGui and module so
-- Bootstrap.client.luau (local limit) is untouched. A small "Tell us!" button bottom-left (48 px high, above the 44 px touch
-- minimum) opens three emoji ratings (Fun / Hard / Looks) and an optional short text box. The server filters the text and
-- rate-limits; this script only sends {fun, level, looks, text}. Copy follows docs/72: short, plain, no jargon.
-- PLACEHOLDER art: plain text and emoji only; final icons are a separate art task (docs/72).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).PlaytestFeedbackEnabled ~= true then return end
local Rules = require(Shared:WaitForChild("PlaytestFeedback"))

local folder = ReplicatedStorage:WaitForChild("BeDinoRemotes", 15)
local remote = if folder then folder:WaitForChild("PlaytestFeedback", 15) else nil
if not remote or not remote:IsA("RemoteEvent") then return end

local player = Players.LocalPlayer
local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder = "PlaytestFeedback", false, 40
gui.Parent = player:WaitForChild("PlayerGui")

local function make(class: string, parent: Instance, name: string, size: UDim2, pos: UDim2): any
    local o = Instance.new(class)
    o.Name, o.Size, o.Position = name, size, pos
    o.Parent = parent
    return o
end
local function round(o: Instance, r: number)
    local c = Instance.new("UICorner") c.CornerRadius = UDim.new(0, r) c.Parent = o
end
local function style(b: any, text: string, fill: Color3, textSize: number)
    b.Text, b.BackgroundColor3, b.TextColor3, b.TextSize = text, fill, Color3.new(1, 1, 1), textSize
    b.Font, b.AutoButtonColor = Enum.Font.FredokaOne, true
    round(b, 10)
end

local PANEL, CARD, ACCENT = Color3.fromRGB(42, 40, 53), Color3.fromRGB(61, 58, 73), Color3.fromRGB(93, 237, 31)

local open = make("TextButton", gui, "TellUsButton", UDim2.fromOffset(120, 48), UDim2.new(0, 12, 1, -68))
style(open, "Tell us!", Color3.fromRGB(194, 86, 255), 24)

local panel = make("Frame", gui, "FeedbackPanel", UDim2.fromOffset(420, 330), UDim2.new(0.5, -210, 0.5, -165))
panel.BackgroundColor3, panel.Visible = PANEL, false
round(panel, 14)

local choice = {fun = 0, level = 0, looks = 0}
local rows = {
    {key = "fun", label = "Fun?", faces = {"😞", "🙂", "😍"}},
    {key = "level", label = "Hard?", faces = {"😴", "🙂", "😰"}},
    {key = "looks", label = "Looks?", faces = {"😞", "🙂", "😍"}},
}
local faceButtons: {[string]: {any}} = {}
for i, row in rows do
    local y = 12 + (i - 1) * 60
    local l = make("TextLabel", panel, "Label_" .. row.key, UDim2.fromOffset(100, 48), UDim2.fromOffset(12, y))
    l.BackgroundTransparency, l.Text, l.TextColor3, l.TextSize, l.Font = 1, row.label, Color3.new(1, 1, 1), 24, Enum.Font.FredokaOne
    l.TextXAlignment = Enum.TextXAlignment.Left
    faceButtons[row.key] = {}
    for n, face in row.faces do
        local b = make("TextButton", panel, "Face_" .. row.key .. "_" .. n, UDim2.fromOffset(88, 48), UDim2.fromOffset(120 + (n - 1) * 96, y))
        style(b, face, CARD, 28)
        faceButtons[row.key][n] = b
        b.Activated:Connect(function()
            choice[row.key] = n
            for m, other in faceButtons[row.key] do other.BackgroundColor3 = if m == n then ACCENT else CARD end
        end)
    end
end

local box = make("TextBox", panel, "FeedbackText", UDim2.fromOffset(396, 48), UDim2.fromOffset(12, 192))
box.BackgroundColor3, box.TextColor3, box.PlaceholderText = CARD, Color3.new(1, 1, 1), "Tell us more (optional)"
box.PlaceholderColor3, box.TextSize, box.Font, box.Text = Color3.fromRGB(190, 190, 200), 20, Enum.Font.FredokaOne, ""
box.ClearTextOnFocus, box.TextXAlignment = false, Enum.TextXAlignment.Left
box.MaxVisibleGraphemes = Rules.MaxTextLength
round(box, 10)

local status = make("TextLabel", panel, "FeedbackStatus", UDim2.fromOffset(396, 28), UDim2.fromOffset(12, 246))
status.BackgroundTransparency, status.Text, status.TextColor3, status.TextSize, status.Font = 1, "", Color3.fromRGB(255, 210, 43), 20, Enum.Font.FredokaOne

local send = make("TextButton", panel, "FeedbackSend", UDim2.fromOffset(190, 48), UDim2.fromOffset(12, 276))
style(send, "SEND", ACCENT, 24)
send.TextColor3 = Color3.fromRGB(13, 15, 20)
local close = make("TextButton", panel, "FeedbackClose", UDim2.fromOffset(190, 48), UDim2.fromOffset(218, 276))
style(close, "CLOSE", CARD, 24)

open.Activated:Connect(function() status.Text = "" panel.Visible = not panel.Visible end)
close.Activated:Connect(function() panel.Visible = false end)
send.Activated:Connect(function()
    if choice.fun == 0 and choice.level == 0 and choice.looks == 0 and box.Text == "" then
        status.Text = "Pick a face first!"
        return
    end
    remote:FireServer({fun = choice.fun, level = choice.level, looks = choice.looks, text = string.sub(box.Text, 1, Rules.MaxTextLength * 4)})
end)
remote.OnClientEvent:Connect(function(result: any)
    if result == "ok" then
        status.Text = "Thank you!"
        box.Text = ""
        task.delay(1.2, function() panel.Visible = false end)
    elseif result == "wait" then
        status.Text = "Try again in a little while"
    elseif result == "limit" then
        status.Text = "Thanks! That is all for today"
    end
end)
