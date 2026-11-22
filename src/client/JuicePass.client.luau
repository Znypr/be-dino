--!strict
-- BD-1286 (docs/245 "Juice to add", slice 1): ONLY while Config.JuicePassEnabled and Config.PhoneHudZonesEnabled are on (flag off: this script returns on
-- its first lines and nothing changes). Two small answers, drawn over the phone HUD (client/PhoneHud):
--   * Eat pop: when the dino eats (GrowthScore rises in a run) the SIZE plate pops and a "+N" floats up from it (bites closer than MergeSeconds add up).
--   * Crystal fly: when crystals rise, 3-6 small crystals (the existing amber icon) fly along a curve from the dino's place on the screen to the crystal
--     counter, which pops as they land.
-- Reduce Motion (Theme.MotionEnabled, GuiService.ReducedMotionEnabled, player attribute ReduceMotion): no flying, no scale pop; the number only changes with a
-- tiny fade. At most Rules.MaxFlying icons in the air, all from one pool made at start; every tween finishes and nothing is left behind.
-- Client presentation only: nothing is stored, sent or decided; PhoneHud and Bootstrap are untouched.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local GuiService = game:GetService("GuiService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).JuicePassEnabled ~= true or (Config :: any).PhoneHudZonesEnabled ~= true then return end

local Rules = require(Shared:WaitForChild("JuiceRules"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Icons = require(Shared:WaitForChild("UIIconAssets"))
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")
local gui = playerGui:WaitForChild("BeDinoUI") :: ScreenGui
local hud = gui:WaitForChild("PhoneHud")
local plate = hud:WaitForChild("SizePlate") :: GuiObject
local crystalsRow = hud:WaitForChild("Crystals") :: GuiObject
local crystalsNumber = crystalsRow:WaitForChild("Number") :: TextLabel
local crystalsScale = crystalsRow:FindFirstChildOfClass("UIScale")
local INK = Color3.fromRGB(36, 32, 42)

local function motion(): boolean
    return Theme.MotionEnabled ~= false and GuiService.ReducedMotionEnabled ~= true and player:GetAttribute("ReduceMotion") ~= true
end
local function menuOpen(): boolean
    local scrim = gui:FindFirstChild("ModalScrim")
    return scrim ~= nil and scrim:IsA("GuiObject") and scrim.Visible
end

-- One layer over the HUD, under the menus' scrim (ZIndex 20).
local layer = Instance.new("Frame")
layer.Name, layer.Size, layer.BackgroundTransparency, layer.ZIndex, layer.Active = "JuiceLayer", UDim2.fromScale(1, 1), 1, 9, false
layer.Parent = gui

local function center(object: GuiObject): (number, number)
    local origin = gui.AbsolutePosition
    return object.AbsolutePosition.X - origin.X + object.AbsoluteSize.X / 2, object.AbsolutePosition.Y - origin.Y + object.AbsoluteSize.Y / 2
end

local function pop(scale: UIScale?)
    if scale == nil or not motion() then return end
    scale.Scale = Rules.PopScale
    TweenService:Create(scale, TweenInfo.new(Rules.PopSeconds, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play()
end

-- ===== Eat: the SIZE plate pops, "+N" floats =====
local plateScale = Instance.new("UIScale")
plateScale.Parent = plate
local floats: {TextLabel} = {}
local function floatWord(text: string)
    while #floats >= Rules.MaxFloats do
        local oldest = table.remove(floats, 1)
        if oldest then oldest:Destroy() end
    end
    local x, y = center(plate)
    local size = math.clamp(math.floor(plate.AbsoluteSize.Y * 0.8), 24, 44)
    local label = Instance.new("TextLabel")
    label.Name, label.BackgroundTransparency, label.AnchorPoint = "SizeFloat", 1, Vector2.new(0.5, 1)
    label.Position, label.Size = UDim2.fromOffset(x, y + plate.AbsoluteSize.Y / 2 + size), UDim2.fromOffset(120, size)
    label.Font, label.Text, label.TextSize, label.TextColor3, label.ZIndex = Enum.Font.FredokaOne, text, size, Color3.new(1, 1, 1), 10
    local stroke = Instance.new("UIStroke")
    stroke.Color, stroke.Thickness, stroke.ApplyStrokeMode, stroke.Parent = INK, 3, Enum.ApplyStrokeMode.Contextual, label
    label.Parent = layer
    table.insert(floats, label)
    local moving = motion()
    local seconds = if moving then Rules.FloatSeconds else Rules.FadeSeconds * 2
    if moving then
        TweenService:Create(label, TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {Position = label.Position - UDim2.fromOffset(0, size * Rules.FloatRise)}):Play()
    end
    local fade = TweenInfo.new(seconds * 0.5, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, seconds * 0.5)
    TweenService:Create(label, fade, {TextTransparency = 1}):Play()
    TweenService:Create(stroke, fade, {Transparency = 1}):Play()
    task.delay(seconds + 0.05, function()
        local at = table.find(floats, label)
        if at then table.remove(floats, at) end
        label:Destroy()
    end)
end

local function watch(character: Model)
    local last = character:GetAttribute("GrowthScore")
    local lastNumber = if typeof(last) == "number" then last else 0
    local pending, scheduled = 0, false
    character:GetAttributeChangedSignal("GrowthScore"):Connect(function()
        local now = character:GetAttribute("GrowthScore")
        local value = if typeof(now) == "number" then now else 0
        local gained = Rules.rose(lastNumber, value)
        lastNumber = value
        if gained <= 0 or character:GetAttribute("RunState") ~= "Active" then return end
        pending += gained
        if scheduled then return end
        scheduled = true
        task.delay(Rules.MergeSeconds, function()
            scheduled = false
            local text = Rules.growthText(pending, (Config :: any).GrowthPerFood)
            pending = 0
            if text == nil or not character.Parent or menuOpen() then return end
            pop(plateScale)
            floatWord(text)
        end)
    end)
end
player.CharacterAdded:Connect(watch)
if player.Character then watch(player.Character) end

-- ===== Crystals: small crystals fly to the counter =====
type Slot = {image: ImageLabel, alpha: NumberValue, busy: boolean, x0: number, y0: number, x1: number, y1: number, side: number}
local pool: {Slot} = {}
local inAir = 0
for i = 1, Rules.MaxFlying do
    local image = Instance.new("ImageLabel")
    image.Name, image.BackgroundTransparency, image.Image, image.ScaleType = "FlyingCrystal", 1, Icons.amber, Enum.ScaleType.Fit
    image.AnchorPoint, image.Size, image.ZIndex, image.Visible = Vector2.new(0.5, 0.5), UDim2.fromOffset(Rules.IconSize, Rules.IconSize), 11, false
    image.Parent = layer
    local alpha = Instance.new("NumberValue")
    local slot: Slot = {image = image, alpha = alpha, busy = false, x0 = 0, y0 = 0, x1 = 0, y1 = 0, side = 1}
    alpha.Changed:Connect(function(t)
        local x, y = Rules.curve(slot.x0, slot.y0, slot.x1, slot.y1, t, slot.side)
        local k = Rules.iconScale(t) * Rules.IconSize
        image.Position, image.Size = UDim2.fromOffset(x, y), UDim2.fromOffset(k, k)
    end)
    pool[i] = slot
end

local function fly(gained: number, fromX: number, fromY: number)
    local want = Rules.canStart(Rules.iconCount(gained), inAir)
    local toX, toY = center(crystalsRow)
    local started = 0
    for _, slot in pool do
        if started >= want then break end
        if not slot.busy then
            started += 1
            slot.busy = true
            inAir += 1
            slot.x0, slot.y0, slot.x1, slot.y1, slot.side = fromX, fromY, toX, toY, if started % 2 == 0 then -1 else 1
            slot.alpha.Value = 0
            slot.image.Position = UDim2.fromOffset(fromX, fromY)
            slot.image.Visible = true
            local info = TweenInfo.new(Rules.FlySeconds, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, (started - 1) * Rules.FlyStagger)
            local tween = TweenService:Create(slot.alpha, info, {Value = 1})
            tween.Completed:Once(function()
                slot.image.Visible, slot.busy = false, false
                inAir -= 1
                pop(crystalsScale)
            end)
            tween:Play()
        end
    end
end

local function dinoOnScreen(): (number, number)
    local camera = workspace.CurrentCamera
    local character = player.Character
    local root = character and character:FindFirstChild("HumanoidRootPart")
    if camera and root and root:IsA("BasePart") then
        local point, visible = camera:WorldToViewportPoint(root.Position)
        local origin = gui.AbsolutePosition
        if visible then return point.X - origin.X, point.Y - origin.Y end
    end
    return gui.AbsoluteSize.X / 2, gui.AbsoluteSize.Y / 2
end

local lastCrystals: number? = nil
PrivateState.onChanged("Crystals", function()
    local amount = PrivateState.num("Crystals")
    local gained = Rules.rose(lastCrystals, amount)
    lastCrystals = amount
    if gained <= 0 then return end
    if motion() and not menuOpen() then
        local x, y = dinoOnScreen()
        fly(gained, x, y)
    else
        -- Reduce Motion (or a window is open): the number just changes, with a tiny fade
        crystalsNumber.TextTransparency = 0.5
        TweenService:Create(crystalsNumber, TweenInfo.new(Rules.FadeSeconds), {TextTransparency = 0}):Play()
    end
end)
lastCrystals = PrivateState.num("Crystals")
