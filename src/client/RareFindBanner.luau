--!strict
-- BD-1121 (docs/202 R6, flag Config.RareFindBannerEnabled): the announcement other players see for a rare hatch, as two lines on the world with NO panel:
--   1. a huge title, white with a thick dark outline ("RARE FIND!"),
--   2. one sentence in white with the rarity word in its colour ("A Legendary Compy was found!").
-- It fades in, stays a few seconds and fades out; with Reduce Motion it just appears and goes (same time on screen). The words come from Shared/RareHatch (findFromPayload:
-- the client checks the server's tier number and species name again), the colour from Shared/RarityWord, the outline from Shared/TextStyle. No player name, no free text.
-- The server still decides and rate-limits (RareHatch.offer / flush); this file only draws. Called by RareHatchClient only while the flag is on.
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rare = require(Shared:WaitForChild("RareHatch"))
local RarityWord = require(Shared:WaitForChild("RarityWord"))
local TextStyle = require(Shared:WaitForChild("TextStyle"))

local Banner = {}
Banner.Y = 118 -- px from the top, where the old strip sat
Banner.TitleMax, Banner.LineMax = 56, 30 -- text sizes (px) at most; TextScaled shrinks them on a narrow screen, never under the floors
Banner.Name = "RareFind"

local current: Frame? = nil

local function fadeTo(label: TextLabel, seconds: number, transparency: number)
    local stroke = label:FindFirstChildOfClass("UIStroke")
    local info = TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
    TweenService:Create(label, info, {TextTransparency = transparency}):Play()
    if stroke then TweenService:Create(stroke, info, {Transparency = transparency}):Play() end
end

local function textLabel(parent: Instance, name: string, text: string, y: number, height: number, minSize: number, maxSize: number, kind: string): TextLabel
    local label = Instance.new("TextLabel")
    label.Name, label.BackgroundTransparency, label.BorderSizePixel = name, 1, 0 -- NO panel
    label.AnchorPoint, label.Position, label.Size = Vector2.new(0.5, 0), UDim2.new(0.5, 0, 0, y), UDim2.new(1, 0, 0, height)
    label.Font, label.TextColor3, label.TextScaled, label.TextWrapped, label.Text = Enum.Font.FredokaOne, Color3.new(1, 1, 1), true, false, text
    label.TextSize = maxSize
    label.Active = false
    local limit = Instance.new("UITextSizeConstraint")
    limit.MinTextSize, limit.MaxTextSize, limit.Parent = minSize, maxSize, label
    label.Parent = parent
    TextStyle.outlined(label, kind) -- font, kind tag and the dark outline (title: 3 px)
    label.TextSize = maxSize
    return label
end

-- data = the server payload {k = "all", kind, tier, species, shiny, mutation, text}. calm = Reduce Motion. Returns true when the new banner was drawn;
-- false when the payload fails the checks (the caller then shows the old text banner).
function Banner.show(gui: Instance, data: any, calm: boolean): boolean
    local find = Rare.findFromPayload(data, RarityWord.Names)
    if find == nil then return false end
    if current and current.Parent then current:Destroy() end
    local plan = Rare.findPlan(calm)
    local root = Instance.new("Frame")
    root.Name, root.BackgroundTransparency, root.BorderSizePixel, root.Active = Banner.Name, 1, 0, false
    root.AnchorPoint, root.Position, root.Size = Vector2.new(0.5, 0), UDim2.new(0.5, 0, 0, 0), UDim2.new(0.92, 0, 0, 0)
    local widest = Instance.new("UISizeConstraint")
    widest.MaxSize = Vector2.new(820, 400)
    widest.Parent = root
    root.Parent = gui
    local title = textLabel(root, "Title", find.title, Banner.Y, 64, TextStyle.Floors.title, Banner.TitleMax, "title")
    local stroke = title:FindFirstChildOfClass("UIStroke")
    if stroke then stroke.Thickness = 4 end -- huge text, thick outline
    local line = textLabel(root, "Line", find.line, Banner.Y + 64, 38, TextStyle.Floors.card, Banner.LineMax, "card")
    RarityWord.set(line, find.line) -- the rarity word in its colour (RichText, whole words, the rest escaped)
    current = root
    if plan.fadeIn > 0 then
        for _, label in {title, line} do
            label.TextTransparency = 1
            local s = label:FindFirstChildOfClass("UIStroke")
            if s then s.Transparency = 1 end
            fadeTo(label, plan.fadeIn, 0)
        end
    end
    task.delay(plan.fadeIn + plan.hold, function()
        if not root.Parent then return end
        if plan.fadeOut > 0 then
            for _, label in {title, line} do fadeTo(label, plan.fadeOut, 1) end
        end
        task.delay(plan.fadeOut, function()
            if root.Parent then root:Destroy() end
            if current == root then current = nil end
        end)
    end)
    return true
end

return Banner
