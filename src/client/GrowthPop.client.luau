--!strict
-- BD-1231 (docs/242 benchmark gap 15, "numbers are the juice"): ONLY while Config.PlayCuesEnabled is on (flag off: this script returns on its first
-- lines and nothing changes). When the dino eats, a big "+N" (N = food points, Shared/PlayCuesRules.popText) rises softly at the dino and fades;
-- bites closer than PlayCuesRules.MergeSeconds add up into one number. When the SIZE bar passes a quarter, one short word banner ("Bigger!",
-- "Huge!") shows above HOME, once per quarter per run. Calm (docs/87): no shake, no flash; Reduce Motion = the number fades in place.
-- The old screen-centre "+0.1" pop of Bootstrap is hidden while this runs (one number, at the dino). Nothing floats over an open window.
-- Client presentation only: nothing is stored, sent or decided. Bootstrap is untouched (size ceiling).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local GuiService = game:GetService("GuiService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).PlayCuesEnabled ~= true then return end

local Rules = require(Shared:WaitForChild("PlayCuesRules"))
local HudRules = require(Shared:WaitForChild("HudRules"))
local Theme = require(Shared:WaitForChild("UITheme"))

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")
local gui = playerGui:WaitForChild("BeDinoUI")
local INK = Theme.Colors.outline

local function motion(): boolean
    return Theme.MotionEnabled ~= false and GuiService.ReducedMotionEnabled ~= true and player:GetAttribute("ReduceMotion") ~= true
end
local function menuOpen(): boolean
    local scrim = gui:FindFirstChild("ModalScrim")
    return scrim ~= nil and scrim:IsA("GuiObject") and scrim.Visible
end

-- Bootstrap's centre pop label (an unnamed TextLabel, ZIndex 43, 160 x 40, centred): one number at the dino instead.
local function hideOldPop(child: Instance)
    if not child:IsA("TextLabel") or child.ZIndex ~= 43 or child.AnchorPoint ~= Vector2.new(.5, .5) then return end
    if child.Size ~= UDim2.fromOffset(160, 40) then return end
    child.Name = "OldPickupPop"
    child.Visible = false
    child:GetPropertyChangedSignal("Visible"):Connect(function() if child.Visible then child.Visible = false end end)
end
for _, child in gui:GetChildren() do hideOldPop(child) end
gui.ChildAdded:Connect(hideOldPop)

-- White words with a 3 px ink outline on the world (style rule R2).
local function word(parent: Instance, text: string, size: number): TextLabel
    local label = Instance.new("TextLabel")
    label.BackgroundTransparency, label.Size, label.Font, label.Text = 1, UDim2.fromScale(1, 1), Enum.Font.FredokaOne, text
    label.TextColor3, label.TextSize, label.TextStrokeTransparency = Color3.new(1, 1, 1), size, 1
    local stroke = Instance.new("UIStroke")
    stroke.Color, stroke.Thickness, stroke.ApplyStrokeMode, stroke.Parent = INK, 3, Enum.ApplyStrokeMode.Contextual, label
    label.Parent = parent
    return label
end

local live: {BillboardGui} = {}
local function pop(character: Model, text: string)
    local anchor = character:FindFirstChild("HumanoidRootPart")
    if not anchor or not anchor:IsA("BasePart") then return end
    while #live >= Rules.MaxPops do
        local oldest = table.remove(live, 1)
        if oldest then oldest:Destroy() end
    end
    local _, height = character:GetBoundingBox()
    local top = math.max(height.Y * 0.5, 2) + 1
    local board = Instance.new("BillboardGui")
    board.Name, board.Adornee, board.Size, board.LightInfluence = "GrowthPop", anchor, UDim2.fromOffset(150, 60), 0
    board.AlwaysOnTop = false -- Studio's screen capture does not draw AlwaysOnTop billboards (docs/evidence note); the dino is in front of the camera anyway
    board.StudsOffset, board.MaxDistance = Vector3.new(0, top, 0), 200
    board.SizeOffset = Vector2.new(0.75, 0) -- beside the head, clear of the health bar above it (style rule R8: nothing overlaps)
    local label = word(board, text, 40)
    board.Parent = playerGui
    table.insert(live, board)
    local rise, seconds = Rules.popMotion(motion())
    local info = TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
    TweenService:Create(board, info, {StudsOffset = Vector3.new(0, top + rise, 0)}):Play()
    TweenService:Create(label, TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.In), {TextTransparency = 1}):Play()
    local stroke = label:FindFirstChildOfClass("UIStroke")
    if stroke then TweenService:Create(stroke, TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.In), {Transparency = 1}):Play() end
    task.delay(seconds + 0.05, function()
        local at = table.find(live, board)
        if at then table.remove(live, at) end
        board:Destroy()
    end)
end

-- The word banner: bottom centre, in the free strip between the dino's feet and the HOME button (the top holds SIZE and its hint).
local bannerLayer = Instance.new("ScreenGui")
bannerLayer.Name, bannerLayer.ResetOnSpawn, bannerLayer.IgnoreGuiInset, bannerLayer.DisplayOrder = "GrowthBanner", false, false, 5
bannerLayer.Parent = playerGui
local bannerSerial = 0
local function banner(text: string)
    bannerSerial += 1
    local serial = bannerSerial
    for _, old in bannerLayer:GetChildren() do old:Destroy() end
    local holder = Instance.new("Frame")
    holder.Name, holder.BackgroundTransparency, holder.AnchorPoint = "Banner", 1, Vector2.new(0.5, 1)
    holder.Position, holder.Size = UDim2.new(0.5, 0, 1, -96), UDim2.fromOffset(360, 64) -- the free strip between the dino and HOME (R8)
    local scale = Instance.new("UIScale")
    scale.Scale, scale.Parent = if motion() then 0.6 else 1, holder
    local label = word(holder, text, 48)
    holder.Parent = bannerLayer
    if motion() then TweenService:Create(scale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play() end
    task.delay(Rules.BannerSeconds, function()
        if serial ~= bannerSerial then return end
        local fade = TweenInfo.new(0.4)
        TweenService:Create(label, fade, {TextTransparency = 1}):Play()
        local stroke = label:FindFirstChildOfClass("UIStroke")
        if stroke then TweenService:Create(stroke, fade, {Transparency = 1}):Play() end
        task.delay(0.45, function() if serial == bannerSerial then holder:Destroy() end end)
    end)
end

local function watch(character: Model)
    local last = character:GetAttribute("GrowthScore")
    local lastNumber = if typeof(last) == "number" then last else 0
    local pending = 0
    local shownWords: {[string]: boolean} = {}
    local function flush()
        local text = Rules.popText(pending, Config.GrowthPerFood)
        pending = 0
        if text and not menuOpen() and character.Parent then pop(character, text) end
    end
    character:GetAttributeChangedSignal("RunState"):Connect(function()
        if character:GetAttribute("RunState") == "Active" then shownWords = {} end -- a new run: every banner may show again
    end)
    character:GetAttributeChangedSignal("GrowthScore"):Connect(function()
        local now = character:GetAttribute("GrowthScore")
        local value = if typeof(now) == "number" then now else 0
        local before = lastNumber
        lastNumber = value
        if value <= before or character:GetAttribute("RunState") ~= "Active" then return end
        if pending == 0 then task.delay(Rules.MergeSeconds, flush) end
        pending += value - before
        local milestone = Rules.milestone(HudRules.barFill(before), HudRules.barFill(value))
        if milestone and not shownWords[milestone] and not menuOpen() then
            shownWords[milestone] = true
            banner(milestone)
        end
    end)
end

player.CharacterAdded:Connect(watch)
if player.Character then watch(player.Character) end
