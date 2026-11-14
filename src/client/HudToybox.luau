--!strict
-- BD-1205 (docs/236, finding P-476117): the bottom-right HUD (LEAP, CHOMP, the weather pill) and HOME in ONE style from the Toybox kit: the same
-- height (Kit.Hud.height), the same 14 px corners, an icon on the left and ONE word (LEAP / CHOMP / HOME; the leap countdown is the word while it
-- recharges), the key hint as a small round cream badge in the top-right corner, the weather pill a flat cream chip with dark ink. HOME is grey,
-- not red (red is for the X only). Called by Bootstrap only while Theme.Toybox is on; it restyles what Bootstrap / CombatHud / HudTimers built and
-- never moves or resizes a button (TouchLayout and the BD-1193 rail fix keep their numbers; every button stays >= 44 px on screen).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Kit = require(Shared:WaitForChild("ToyboxKit"))
local Layout = require(Shared:WaitForChild("ToyboxLayout"))
local Slots = require(Shared:WaitForChild("AssetSlots"))
local Theme = require(Shared:WaitForChild("UITheme"))
local UIFormat = require(Shared:WaitForChild("UIFormat"))

local M = {}
local H = Kit.Hud

local function pill(object: GuiObject)
    local corner: UICorner? = object:FindFirstChildOfClass("UICorner")
    local made = corner or Instance.new("UICorner")
    made.CornerRadius = UDim.new(0, H.corner)
    made.Parent = object
end

-- The icon of a button (the first Frame the artwork helper made, or the bound picture): left, vertically centred, Kit.Hud.icon px.
local function placeIcon(button: GuiObject, icon: GuiObject?)
    if icon == nil then return end
    icon.Position, icon.Size = UDim2.fromOffset(H.iconX, (H.height - H.icon) // 2), UDim2.fromOffset(H.icon, H.icon)
end

-- The small key badge in the top-right corner (desktop only: a touch device has no key to show).
function M.badge(button: GuiObject, key: string): TextLabel?
    local old = button:FindFirstChild("KeyHint")
    if old then old:Destroy() end
    if not (UserInputService.KeyboardEnabled and not UserInputService.TouchEnabled) then return nil end
    local badge = Instance.new("TextLabel")
    badge.Name, badge.Text, badge.BackgroundColor3, badge.BorderSizePixel = "KeyHint", key, Layout.tone("panel"), 0
    badge.Size = UDim2.fromOffset(H.badge, H.badge)
    badge.Position = UDim2.fromOffset(button.Size.X.Offset - H.badge - H.badgeInset, H.badgeInset)
    badge.Font, badge.TextSize, badge.ZIndex = Enum.Font.FredokaOne, 15, button.ZIndex + 3
    Layout.ink(badge, "value")
    local round = Instance.new("UICorner")
    round.CornerRadius, round.Parent = UDim.new(0.5, 0), badge
    local line = Instance.new("UIStroke")
    line.Color, line.Thickness, line.Parent = Color3.fromRGB(Kit.Outline[1], Kit.Outline[2], Kit.Outline[3]), 2, badge
    badge.Parent = button
    return badge
end

-- A word label beside the icon: left edge Kit.Hud.wordX, one line, centred in what is left of the button.
local function wordBox(word: TextLabel, button: GuiObject)
    word.Position = UDim2.fromOffset(H.wordX, 0)
    word.Size = UDim2.fromOffset(math.max(button.Size.X.Offset - H.wordX - H.badgeInset, 40), H.height)
    word.TextXAlignment = Enum.TextXAlignment.Center
end

-- ctx = HudTimers' table {timers, leap, leapText, tile, text, num}. Once, after Bootstrap built the column and CombatHud added CHOMP.
function M.attach(ctx: any)
    local leap: GuiObject = ctx.leap
    pill(leap)
    leap.Size = UDim2.fromOffset(leap.Size.X.Offset, H.height)
    for _, child in leap:GetChildren() do
        if child:IsA("Frame") then placeIcon(leap, child) break end
    end
    wordBox(ctx.leapText, leap)
    leap:GetPropertyChangedSignal("Size"):Connect(function() wordBox(ctx.leapText, leap) end)
    M.badge(leap, "E")

    local bite = ctx.timers:FindFirstChild("BiteButton")
    if bite and bite:IsA("TextButton") then
        pill(bite)
        bite.Size = UDim2.fromOffset(bite.Size.X.Offset, H.height)
        bite.TextSize = H.word
        local id = (Slots.Images :: any).hud_bite
        if type(id) == "string" and string.match(id, "^rbxassetid://%d+$") then -- the owner's bite picture beside the word, never a blank box
            local icon = Instance.new("ImageLabel")
            icon.Name, icon.BackgroundTransparency, icon.Image, icon.ScaleType, icon.ZIndex = "BiteIcon", 1, id, Enum.ScaleType.Fit, bite.ZIndex + 2
            icon.Parent = bite
            placeIcon(bite, icon)
        end
        M.badge(bite, "F")
    end

    local tile: GuiObject = ctx.tile
    pill(tile)
    tile.Size = UDim2.fromOffset(tile.Size.X.Offset, H.height)
    tile.BackgroundColor3 = Layout.tone("panel")
    local gradient = tile:FindFirstChildOfClass("UIGradient")
    if gradient then gradient:Destroy() end
    Layout.ink(ctx.text, "value")
    wordBox(ctx.text, tile)
    ctx.text.TextXAlignment = Enum.TextXAlignment.Left
end

-- Every HUD tick: LEAP shows ONE word (its countdown while it recharges), and HOME / EXPLORE gets the column's corners and is grey, never red, while in a run
-- (Bootstrap sets its colour every 0.15 s; the change is turned into grey the moment it happens).
local homeButton: GuiObject? = nil
function M.tick(ctx: any, now: number)
    ctx.leapText.Text = Kit.hudWord("leap", ctx.num("LeapReadyAt") - now, UIFormat.duration)
    if homeButton == nil then
        local gui = ctx.tile:FindFirstAncestorOfClass("ScreenGui")
        local found = if gui then gui:FindFirstChild("HomeButton") else nil
        if found == nil or not found:IsA("TextButton") then return end
        homeButton = found
        pill(found)
        local C = Theme.Colors
        local function grey()
            if found.BackgroundColor3 == C.red then found.BackgroundColor3 = C.card end
        end
        found:GetPropertyChangedSignal("BackgroundColor3"):Connect(grey)
        grey()
    end
end

return M
