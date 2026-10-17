--!strict
-- BD-570 (docs/134 s13): the gift popup "You got a gift from <name>!". Behind Config.GiftClaimEnabled (default false, pinned off in every release
-- profile): with the flag off this script returns on its first line, builds no UI and waits for no remote.
-- The text comes from the server (GiftNoticeJson on the owner-only PrivateState channel; the name is resolved fresh and never stored). The server hands over
-- ONE notice at a time and queues the rest, so one popup is on screen at a time. Buttons: "Nice!" (close), "Mute <name>" (only for a gift from another
-- player) and "Turn gifts off". There is NO refuse / decline button and no reply (owner, 2026-10-17). All wording, sizes and requests come from the pure
-- Shared/GiftUiModel (verified offline by tools/verify_gift_ui.py); the spot comes from TouchLayout.giftRect (Bootstrap publishes it as GiftRect /
-- GiftVariant), real pixels, never scaled, so text stays >= 14 px and buttons >= 44 px. Reduce Motion (Theme.MotionEnabled) = no bounce.
-- Shown only in the cave hub, never during a run, and not on top of an open menu. Icons are the registered ones (docs/77); plates are UITheme's.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).GiftClaimEnabled ~= true then return end
local Model = require(Shared:WaitForChild("GiftUiModel"))
local Theme = require(Shared:WaitForChild("UITheme"))
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))
local Gifts = require(script.Parent:WaitForChild("GiftSettings"))
local C = Theme.Colors

local folder = ReplicatedStorage:WaitForChild("BeDinoRemotes", 15)
local remote = if folder then folder:WaitForChild("GiftAction", 15) else nil
if not remote or not remote:IsA("RemoteFunction") then return end

local player = Players.LocalPlayer
local gui = Instance.new("ScreenGui")
gui.Name, gui.ResetOnSpawn, gui.DisplayOrder, gui.Enabled = "GiftPopup", false, 45, false
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets -- the same pixel space as BeDinoUI, so its GiftRect lines up
gui.Parent = player:WaitForChild("PlayerGui")

local panel = Instance.new("Frame")
panel.Name, panel.BackgroundColor3, panel.Active = "Panel", C.panel, true
panel.Parent = gui
Theme.decorate(panel, 10)
local pop = Instance.new("UIScale") -- the one-time bounce on arrival (skipped under Reduce Motion)
pop.Parent = panel

local notice: Model.Notice? = nil
local shown = "" -- "<id>|<variant>" currently drawn, so an unchanged notice is not rebuilt (and its bounce does not replay)
local busy = false
local uiRoot: Instance? = nil
local scrim: GuiObject? = nil

local function label(name: string, box: any, text: string): TextLabel
    local l = Instance.new("TextLabel")
    l.Name, l.Text, l.Position, l.Size = name, text, UDim2.fromOffset(box.x, box.y), UDim2.fromOffset(box.w, box.h)
    l.BackgroundTransparency, l.TextColor3, l.TextSize, l.Font = 1, C.text, box.size, Enum.Font.FredokaOne
    l.TextXAlignment, l.TextYAlignment, l.TextTruncate, l.TextWrapped = Enum.TextXAlignment.Left, Enum.TextYAlignment.Center, Enum.TextTruncate.AtEnd, false
    l.Parent = panel
    return l
end

local function act(id: string)
    if busy then return end
    busy = true
    task.spawn(function()
        Gifts.controller().press(id) -- the server then sends the next notice (or an empty one); refresh() reacts to that
        busy = false
    end)
end

local function variantName(): string
    local name = if uiRoot then uiRoot:GetAttribute("GiftVariant") else nil
    return if typeof(name) == "string" then name else "compact"
end

-- Where the panel goes: the published rect (clear of the HUD), else a safe default just below the top rail.
local function place(layout: Model.Layout)
    local rect = if uiRoot then uiRoot:GetAttribute("GiftRect") else nil
    if typeof(rect) == "Rect" then
        panel.Position = UDim2.fromOffset(rect.Min.X, rect.Min.Y)
    else
        panel.Position = UDim2.new(0.5, -layout.w / 2, 0, 120)
    end
    panel.Size = UDim2.fromOffset(layout.w, layout.h)
end

local function build()
    local current = notice
    if current == nil then shown = "" return end
    local name = variantName()
    local key = current.id .. "|" .. name
    local layout = Model.layout(name, current.canMute)
    place(layout)
    if key == shown then return end
    shown = key
    for _, child in panel:GetChildren() do
        if child:IsA("GuiObject") then child:Destroy() end
    end
    local icon = Theme.icon(panel, Model.iconFor(current))
    if icon then
        icon.Position, icon.Size = UDim2.fromOffset(layout.icon.x, layout.icon.y), UDim2.fromOffset(layout.icon.w, layout.icon.h)
    end
    label("Title", layout.title, Model.title(current, layout))
    label("Detail", layout.detail, Model.detail(current)).TextColor3 = C.gold
    for _, id in layout.order do
        local box = layout.buttons[id]
        local b = Instance.new("TextButton")
        b.Name, b.Text, b.Position, b.Size = "Button_" .. id, Model.buttonText(id, current, layout), UDim2.fromOffset(box.x, box.y), UDim2.fromOffset(box.w, box.h)
        b.BackgroundColor3, b.TextColor3, b.TextSize, b.Font = if id == "ack" then C.accent else C.card, C.text, box.size, Enum.Font.FredokaOne
        b.TextTruncate = Enum.TextTruncate.AtEnd
        b.Parent = panel
        Theme.decorate(b, 8)
        b.Activated:Connect(function() act(id) end)
    end
    -- Arrival: a small bounce, or nothing at all under Reduce Motion.
    Theme.cancel(pop)
    if Theme.MotionEnabled then
        pop.Scale = 0.88
        Theme.animate(pop, 0.28, {Scale = 1}, Enum.EasingStyle.Back)
    else
        pop.Scale = 1
    end
end

local function refreshVisibility()
    local menuOpen = scrim ~= nil and (scrim :: GuiObject).Visible
    gui.Enabled = notice ~= nil and player:GetAttribute("Location") ~= "Island" and not menuOpen
end

local function refresh()
    local raw = PrivateState.str("GiftNoticeJson", "")
    notice = nil
    if raw ~= "" then
        local ok, decoded = pcall(function() return HttpService:JSONDecode(raw) end)
        if ok then notice = Model.parseNotice(decoded) end
    end
    build()
    refreshVisibility()
end

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
player:GetAttributeChangedSignal("Location"):Connect(refreshVisibility)

-- The HUD layout (GiftRect) and the menu scrim live in BeDinoUI, which Bootstrap builds; follow them once they exist.
task.spawn(function()
    local root = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI", 30)
    if not root then return end
    uiRoot = root
    local found = root:WaitForChild("ModalScrim", 30)
    if found and found:IsA("GuiObject") then
        scrim = found
        found:GetPropertyChangedSignal("Visible"):Connect(refreshVisibility)
    end
    root:GetAttributeChangedSignal("GiftRect"):Connect(build)
    root:GetAttributeChangedSignal("GiftVariant"):Connect(build)
    build()
    refreshVisibility()
end)
refresh()
