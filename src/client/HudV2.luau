--!strict
-- BD-080 (BD-056 spec): the calm gameplay HUD. Bottom-left (top-left on phones, clear of the thumb) a plate with the egg
-- icon and "EGGS N" that pops when N grows; top-centre a slim SIZE bar for growth. Replaces the old three-bar growth tile,
-- the "N catches . Island/Sanctuary" text and the big GROWTH number. Reuses the existing "egg" icon: no new art.
-- All decisions live in the pure Shared/HudRules (tools/verify_hud.py). Reduce Motion (Theme.MotionEnabled): no pop, no
-- bar tween. Bootstrap keeps the `hud` frame (its layout slot), calls attach once and layout() from scales().
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("HudRules"))
local Theme = require(Shared:WaitForChild("UITheme"))

local Hud = {}
local C = Theme.Colors
local player = Players.LocalPlayer
local barPlate: Frame? = nil
local BAR_W, BAR_H = 250, 34

local function text(parent: Instance, name: string, size: number, color: Color3, x: number): TextLabel
    local t = Instance.new("TextLabel")
    t.Name, t.BackgroundTransparency, t.Font, t.TextSize, t.TextColor3 = name, 1, Enum.Font.FredokaOne, size, color
    t.TextStrokeTransparency, t.TextStrokeColor3, t.TextXAlignment, t.ZIndex = 0.2, C.outline, Enum.TextXAlignment.Left, 6
    t.Position, t.Size, t.Parent = UDim2.new(0, x, 0, 0), UDim2.new(1, -x - 6, 1, 0), parent
    return t
end

local function plate(parent: Instance, name: string, w: number, h: number): Frame
    local f = Instance.new("Frame")
    f.Name, f.Size, f.BackgroundColor3, f.BackgroundTransparency, f.BorderSizePixel, f.ZIndex = name, UDim2.fromOffset(w, h), C.panel, 0.12, 0, 5
    f.Active = false
    Theme.decorate(f, 12)
    f.Parent = parent
    return f
end

-- hud = Bootstrap's bottom-left (phone: top-left) layout slot; gui = the BeDinoUI ScreenGui.
function Hud.attach(hud: Frame, gui: ScreenGui)
    for _, child in hud:GetChildren() do
        if child:IsA("GuiObject") or child:IsA("UICorner") or child:IsA("UIStroke") or child:IsA("UIGradient") then child:Destroy() end
    end
    hud.BackgroundTransparency = 1

    -- Egg plate: fills the layout slot (TouchLayout.HUD, 210 x 64).
    local eggPlate = plate(hud, "EggsPlate", 210, 64)
    local holder = Instance.new("Frame") -- the icon grows from its middle
    holder.Name, holder.BackgroundTransparency, holder.AnchorPoint = "EggIcon", 1, Vector2.new(0.5, 0.5)
    holder.Position, holder.Size, holder.ZIndex, holder.Parent = UDim2.fromOffset(38, 32), UDim2.fromOffset(54, 54), 6, eggPlate
    Theme.icon(holder, "egg")
    local pop = Instance.new("UIScale")
    pop.Parent = holder
    local eggsLabel = text(eggPlate, "EggsText", 30, C.gold, 74)
    eggsLabel.TextScaled = true
    local limit = Instance.new("UITextSizeConstraint")
    limit.MaxTextSize, limit.MinTextSize, limit.Parent = 30, 12, eggsLabel

    -- SIZE bar: slim, top-centre, only during a run.
    local bar = plate(gui, "SizeBar", BAR_W, BAR_H)
    bar.AnchorPoint, bar.Position, bar.Visible = Vector2.new(0.5, 0), UDim2.new(0.5, 0, 0, 64), false
    barPlate = bar
    local word = text(bar, "SizeWord", 18, C.text, 12)
    word.Size, word.Text = UDim2.fromOffset(60, BAR_H), Rules.SizeWord
    local track = Instance.new("Frame")
    track.Name, track.BackgroundColor3, track.BorderSizePixel, track.ZIndex = "Track", C.outline, 0, 6
    track.Position, track.Size, track.Parent = UDim2.fromOffset(72, 9), UDim2.fromOffset(BAR_W - 72 - 12, BAR_H - 18), bar
    local trackCorner = Instance.new("UICorner")
    trackCorner.CornerRadius, trackCorner.Parent = UDim.new(0.5, 0), track
    local fill = Instance.new("Frame")
    fill.Name, fill.BackgroundColor3, fill.BorderSizePixel, fill.ZIndex = "Fill", C.accent, 0, 7
    fill.Size, fill.Parent = UDim2.fromScale(0, 1), track
    local fillCorner = Instance.new("UICorner")
    fillCorner.CornerRadius, fillCorner.Parent = UDim.new(0.5, 0), fill

    local previous: number? = nil
    local lastPop = -10
    local lastFill = -1
    local elapsed = 0
    RunService.Heartbeat:Connect(function(dt)
        elapsed += dt
        if elapsed < 0.1 then return end
        elapsed = 0
        local character = player.Character
        local running = character ~= nil and character:GetAttribute("RunState") == "Active"
        local eggs = if character then character:GetAttribute("CatchScore") else 0
        local growth = if character then character:GetAttribute("GrowthScore") else 0
        local shown = Rules.eggsText(eggs)
        if eggsLabel.Text ~= shown then eggsLabel.Text = shown end
        if Rules.shouldPop(previous, eggs, running, Theme.MotionEnabled, os.clock() - lastPop) then
            lastPop = os.clock()
            pop.Scale = Rules.PopScale
            Theme.animate(pop, Rules.PopSeconds, {Scale = 1}, Enum.EasingStyle.Back)
        end
        previous = if typeof(eggs) == "number" then eggs else 0
        bar.Visible = running
        local amount = Rules.barFill(growth)
        if math.abs(amount - lastFill) > 0.002 then
            lastFill = amount
            Theme.animate(fill, 0.25, {Size = UDim2.fromScale(amount, 1)})
        end
    end)
end

-- Called from Bootstrap's scales() with the TouchLayout result. Puts the SIZE bar under whatever sits at the top centre
-- (the build badge on desktop, the nav rail on phones) so nothing overlaps; the bar shrinks a little on small canvases.
function Hud.layout(layout: any)
    local bar = barPlate
    if not bar then return end
    local scale = math.clamp(if layout.touch then layout.rail.scale else layout.hud.scale, 0.7, 1)
    local top = if layout.touch then layout.rail.y + layout.rail.h * layout.rail.scale + 4 else 64
    bar.AnchorPoint, bar.Position = Vector2.new(0.5, 0), UDim2.new(0.5, 0, 0, top)
    local uiScale = bar:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
    uiScale.Scale, uiScale.Parent = scale, bar
end

return Hud
