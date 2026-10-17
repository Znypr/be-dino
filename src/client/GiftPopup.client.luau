--!strict
-- BD-451 (docs/134 s3, GF1c): the minimal "You got a gift from <name>!" popup. Behind Config.GiftClaimEnabled (default false, pinned off in
-- every release profile): with the flag off this script returns on its first line, builds no UI and waits for no remote.
-- The text comes from the server (GiftNoticeJson on the owner-only PrivateState channel, name resolved fresh and never stored). Buttons:
-- Thanks, Mute (only for a gift from another player) and Turn gifts off. There is NO decline-one-gift button (owner, 2026-10-17) and no reply.
-- Shown only while the player is in the cave hub, never during a run. PLACEHOLDER look: plain text and flat buttons; real art, the
-- Settings row "Gifts from" and phone layout are a separate UI task (docs/72).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).GiftClaimEnabled ~= true then return end
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))

local folder = ReplicatedStorage:WaitForChild("BeDinoRemotes", 15)
local remote = if folder then folder:WaitForChild("GiftAction", 15) else nil
if not remote or not remote:IsA("RemoteFunction") then return end

local player = Players.LocalPlayer
local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder, gui.Enabled = "GiftPopup", false, 45, false
gui.Parent = player:WaitForChild("PlayerGui")

local panel = Instance.new("Frame")
panel.Name, panel.AnchorPoint, panel.Position, panel.Size = "Panel", Vector2.new(0.5, 0), UDim2.new(0.5, 0, 0, 24), UDim2.fromOffset(360, 208)
panel.BackgroundColor3 = Color3.fromRGB(42, 40, 53)
panel.Parent = gui
local corner = Instance.new("UICorner")
corner.CornerRadius = UDim.new(0, 14)
corner.Parent = panel

local function label(name: string, y: number, height: number, size: number): TextLabel
    local text = Instance.new("TextLabel")
    text.Name, text.Position, text.Size = name, UDim2.fromOffset(12, y), UDim2.new(1, -24, 0, height)
    text.BackgroundTransparency, text.TextColor3, text.TextSize = 1, Color3.new(1, 1, 1), size
    text.Font, text.TextWrapped = Enum.Font.FredokaOne, true
    text.Parent = panel
    return text
end
local title = label("Title", 10, 56, 24)
local detail = label("Detail", 68, 44, 18)

local function button(name: string, text: string, x: number, width: number): TextButton
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.Position, b.Size = name, text, UDim2.fromOffset(x, 144), UDim2.fromOffset(width, 48)
    b.BackgroundColor3, b.TextColor3, b.TextSize, b.Font = Color3.fromRGB(93, 237, 31), Color3.fromRGB(20, 20, 20), 18, Enum.Font.FredokaOne
    b.Parent = panel
    local c = Instance.new("UICorner")
    c.CornerRadius = UDim.new(0, 10)
    c.Parent = b
    return b
end
local thanks = button("Thanks", "Thanks!", 12, 100)
local mute = button("Mute", "Mute", 120, 100)
local turnOff = button("TurnOff", "Gifts off", 228, 120)

local payload: any = nil
local function refresh()
    local raw = PrivateState.str("GiftNoticeJson", "")
    payload = nil
    if raw ~= "" then
        local ok, decoded = pcall(function() return HttpService:JSONDecode(raw) end)
        if ok and typeof(decoded) == "table" and typeof(decoded.line) == "string" then payload = decoded end
    end
    if payload == nil then gui.Enabled = false return end
    title.Text = payload.line
    local extra = if typeof(payload.message) == "string" and payload.message ~= "" then " - " .. payload.message else ""
    detail.Text = (if typeof(payload.item) == "string" then payload.item else "") .. extra .. (if payload.converted == true then " (you had it, so: crystals!)" else "")
    mute.Visible = payload.canMute == true
    gui.Enabled = player:GetAttribute("Location") ~= "Island"
end

local busy = false
local function act(action: string)
    if busy then return end
    busy = true
    pcall(function() (remote :: RemoteFunction):InvokeServer({action = action}) end)
    busy = false
end
thanks.Activated:Connect(function() act("ack") end)
mute.Activated:Connect(function() act("mute") end)
turnOff.Activated:Connect(function() act("turnOff") end)

-- GF12 (docs/134 s2.1): report this player's own Roblox block list once per join, BEFORE the server's first claim waits it out. The list only
-- ever restricts this player's own inbox. GetCore can fail until the core scripts are ready, so retry; if it never works the server falls back
-- to Mute and Nobody. Not testable offline: verify in Studio (BD-570).
task.spawn(function()
    for _ = 1, 10 do
        local ok, list = pcall(function() return game:GetService("StarterGui"):GetCore("GetBlockedUserIds") end)
        if ok and typeof(list) == "table" then
            local ids: {number} = {}
            for _, id in list do
                if typeof(id) == "number" and id >= 1 and id % 1 == 0 and #ids < 200 then table.insert(ids, id) end
            end
            pcall(function() (remote :: RemoteFunction):InvokeServer({action = "blocked", ids = ids}) end)
            return
        end
        task.wait(1)
    end
end)

PrivateState.onChanged("GiftNoticeJson", refresh)
player:GetAttributeChangedSignal("Location"):Connect(function()
    if payload ~= nil then gui.Enabled = player:GetAttribute("Location") ~= "Island" end
end)
refresh()
