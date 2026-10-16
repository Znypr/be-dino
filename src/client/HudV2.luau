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
local PrivateState = require(script.Parent.PrivateState)
local Rules = require(Shared:WaitForChild("HudRules"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Ftue = require(Shared:WaitForChild("FtueRules"))
local Copy = require(Shared:WaitForChild("FtueP1"))
local ProgressionConfig = require(Shared:WaitForChild("ProgressionConfig"))
local ProgressionRules = require(Shared:WaitForChild("ProgressionRules"))
local Assets = require(Shared:WaitForChild("EffectAssets"))
local Sfx = require(Shared:WaitForChild("Sfx"))

local Hud = {}
local C = Theme.Colors
local player = Players.LocalPlayer
local barPlate: Frame? = nil
local hintLabel: TextLabel? = nil
local BAR_W, BAR_H = 250, 34

local function text(parent: Instance, name: string, size: number, color: Color3, x: number): TextLabel
    local t = Instance.new("TextLabel")
    t.Name, t.BackgroundTransparency, t.Font, t.TextSize, t.TextColor3 = name, 1, Enum.Font.FredokaOne, size, color
    t.TextXAlignment, t.ZIndex = Enum.TextXAlignment.Left, 6
    t.Position, t.Size, t.Parent = UDim2.new(0, x, 0, 0), UDim2.new(1, -x - 6, 1, 0), parent
    Theme.TextStyle.apply(t) -- BD-390
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
function Hud.attach(hud: Frame, gui: ScreenGui, hooks: any?)
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

    -- BD-366: calm one-line goal hint under the SIZE bar until the profile has found its first egg.
    local hint = Instance.new("TextLabel")
    hint.Name, hint.BackgroundTransparency, hint.Font, hint.TextSize, hint.TextColor3 = "GoalHint", 1, Enum.Font.FredokaOne, 20, C.text
    hint.TextWrapped, hint.Visible, hint.ZIndex = true, false, 6
    Theme.TextStyle.apply(hint) -- BD-390
    hint.AnchorPoint, hint.Position, hint.Size, hint.Parent = Vector2.new(0.5, 0), UDim2.new(0.5, 0, 0, 102), UDim2.fromOffset(360, 28), gui
    hintLabel = hint
    local sessionCatch, nearFood, lastNear = false, false, -10
    local lastMoment, momentsThisRun, wasRunning = nil :: number?, 0, false
    local pendingEggs, pendingMutation, tagsSeen = 0, nil :: string?, 0 -- BD-378: eggs found since the last toast (merged into one)
    local function foundBefore(): boolean
        local copies = 0
        local ok, collection = pcall(function() return game:GetService("HttpService"):JSONDecode(PrivateState.get("CollectionJson") :: string) end)
        if ok then copies = Ftue.collectionCopies(collection) end
        return Ftue.hasFoundEgg({sessionCatch = sessionCatch, activeEggs = PrivateState.get("ActiveChestCount"),
            waitingEggs = PrivateState.get("QueuedEggsWaiting"), lastRunEggs = PrivateState.get("LastRunEggCount"), copies = copies})
    end
    local function sparkle(character: Model)
        local count = Ftue.sparkle(Theme.MotionEnabled)
        local root = character:FindFirstChild("HumanoidRootPart")
        if count <= 0 or not root or not root:IsA("BasePart") then return end
        local at = Instance.new("Attachment")
        at.Name, at.Position, at.Parent = "EggFoundSparkle", Vector3.new(0, 1.5, 0), root
        local e = Instance.new("ParticleEmitter")
        e.Texture, e.Rate, e.Lifetime, e.Speed = Assets.resolve("starFour"), 0, NumberRange.new(0.7, 1.1), NumberRange.new(4, 8)
        e.SpreadAngle, e.Size, e.LightEmission = Vector2.new(180, 180), NumberSequence.new({NumberSequenceKeypoint.new(0, 0.9), NumberSequenceKeypoint.new(1, 0)}), 0.6
        e.Transparency, e.Color = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.1), NumberSequenceKeypoint.new(1, 1)}), ColorSequence.new(Color3.fromRGB(255, 240, 180))
        e.Parent = at
        e:Emit(count)
        task.delay(1.5, function() at:Destroy() end)
    end
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
        -- BD-367: a clear, calm "you found an egg" moment (sparkle, soft cue, toast); one at a time, Reduce Motion: no sparkle.
        if running and not wasRunning then momentsThisRun, pendingEggs, pendingMutation, tagsSeen = 0, 0, nil, 0 end
        wasRunning = running
        local nowEggs = if typeof(eggs) == "number" then eggs else 0
        local special = false
        if running and nowEggs > (previous or nowEggs) then
            sessionCatch = true
            pendingEggs += nowEggs - (previous or nowEggs)
            -- A weather egg (event mutation) is named in the SAME toast; the second "caught!" card is gone (BD-378).
            local ok, tags = pcall(function() return game:GetService("HttpService"):JSONDecode((character :: Model):GetAttribute("RunEggEvents") or "[]") end)
            if ok and typeof(tags) == "table" then
                for i = #tags, tagsSeen + 1, -1 do
                    local mutation = ProgressionRules.item(ProgressionConfig.EventMutations, (tags[i] :: any).mutationId or "")
                    if mutation and not pendingMutation then pendingMutation, special = mutation.name, true end
                end
                tagsSeen = #tags
            end
        end
        if Ftue.momentAllowed(previous, nowEggs, running, if lastMoment then os.clock() - lastMoment else nil, momentsThisRun) or special then
            lastMoment, momentsThisRun = os.clock(), momentsThisRun + 1
            if character then sparkle(character) end
            Sfx.playAlias(Ftue.SoundAlias)
            local toastText, toastBody = Copy.foundToast(pendingEggs, pendingMutation)
            pendingEggs, pendingMutation = 0, nil
            if hooks and hooks.notify then hooks.notify(toastText, C.gold, {key = "egg_found", icon = "egg", body = toastBody}) end
        end
        previous = nowEggs
        bar.Visible = running
        -- BD-366: the hint (computed from replicated data only; the food check runs twice a second and only while it shows).
        local hasFound = sessionCatch or foundBefore()
        if running and not hasFound and os.clock() - lastNear > 0.5 then
            lastNear = os.clock()
            nearFood = false
            local root = character and character:FindFirstChild("HumanoidRootPart")
            local food = workspace:FindFirstChild("Food")
            if root and food then
                local params = OverlapParams.new()
                params.FilterType, params.FilterDescendantsInstances = Enum.RaycastFilterType.Include, {food}
                for _, part in workspace:GetPartBoundsInRadius((root :: BasePart).Position, Ftue.NearDistance, params) do
                    if Ftue.isSpecialFood(part.Name) and part.Transparency < 1 then nearFood = true break end
                end
            end
        end
        local shownHint = Ftue.hint({running = running, hasFoundEgg = hasFound, nearSpecialFood = nearFood})
        hint.Visible = shownHint ~= nil
        if shownHint and hint.Text ~= shownHint then hint.Text = shownHint end
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
    if hintLabel then
        hintLabel.Position = UDim2.new(0.5, 0, 0, top + (BAR_H + 4) * scale)
        local hintScale = hintLabel:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
        hintScale.Scale, hintScale.Parent = scale, hintLabel
    end
end

return Hud
