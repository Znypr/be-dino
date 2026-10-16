--!strict
-- BD-247 / docs/101 s10 (art PLACEHOLDER until BD-248): health bars over dinos, the own HP strip and the Bite button.
-- Lives in its own module because Bootstrap.client is at the 200-local limit; Bootstrap calls attach(ctx) once with its
-- helpers. With Config.CombatEnabled false attach() returns at once: no instances, no loops, no input hooks.
-- Rules (docs/72, docs/87): no damage numbers, no "HP" text, no red flash, no loud sound. Heart + bar are the message.
-- Bars are pooled BillboardGuis (at most MAX_BARS), plain Frames, hidden beyond FAR_STUDS and, when full, beyond NEAR_STUDS.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Input = game:GetService("UserInputService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Cfg = require(Shared:WaitForChild("CombatConfig"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local C = Theme.Colors

local Hud = {}
local MAX_BARS = 12
local FAR_STUDS = 60 -- never shown beyond this
local NEAR_STUDS = 40 -- a full bar is shown only inside this (or for 3 s after a hit)
local SHOW_AFTER_HIT = 3
local BAR_W, BAR_H = 64, 12 -- px at scale 1 (>= 60 px on phones, docs/101 s10)
local GREEN, YELLOW, ORANGE = Color3.fromRGB(93, 237, 31), Color3.fromRGB(255, 210, 43), Color3.fromRGB(255, 150, 70)

-- Pure helpers (also used by the verifier through a static read; keep them simple).
function Hud.fillColor(fraction: number): Color3
    if fraction > 0.5 then return GREEN elseif fraction > 0.25 then return YELLOW end
    return ORANGE
end
-- Heart glyph by fraction: full, half, small (never colour alone).
function Hud.heartText(fraction: number): string
    if fraction > 0.5 then return "\u{2665}" elseif fraction > 0.25 then return "\u{2661}" end
    return "\u{00B7}"
end

type Bar = {gui: BillboardGui, fill: Frame, heart: TextLabel, wobble: UIScale, character: Model?, lastFraction: number}

local function makeBar(parent: Instance): Bar
    local gui = Instance.new("BillboardGui")
    gui.Name, gui.Size, gui.AlwaysOnTop, gui.Enabled, gui.MaxDistance = "HpBar", UDim2.fromOffset(BAR_W + 18, BAR_H + 6), false, false, FAR_STUDS + 5
    gui.LightInfluence, gui.ResetOnSpawn = 0, false
    local heart = Instance.new("TextLabel")
    heart.BackgroundTransparency, heart.Size, heart.Position = 1, UDim2.fromOffset(16, BAR_H + 6), UDim2.fromOffset(0, 0)
    heart.Font, heart.TextSize, heart.TextColor3, heart.Text = Enum.Font.FredokaOne, 14, Color3.fromRGB(255, 120, 140), "\u{2665}"
    heart.TextStrokeTransparency, heart.TextStrokeColor3, heart.Parent = 0, C.outline, gui
    local back = Instance.new("Frame")
    back.Position, back.Size, back.BackgroundColor3, back.BorderSizePixel = UDim2.fromOffset(18, 3), UDim2.fromOffset(BAR_W, BAR_H), C.panel, 0
    back.Parent = gui
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0.5, 0) corner.Parent = back
    local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = C.outline, 2, back
    local fill = Instance.new("Frame")
    fill.Size, fill.BackgroundColor3, fill.BorderSizePixel, fill.Parent = UDim2.fromScale(1, 1), GREEN, 0, back
    local fillCorner = Instance.new("UICorner") fillCorner.CornerRadius = UDim.new(0.5, 0) fillCorner.Parent = fill
    local wobble = Instance.new("UIScale") wobble.Parent = back
    gui.Parent = parent
    return {gui = gui, fill = fill, heart = heart, wobble = wobble, character = nil, lastFraction = 1}
end

local function fractionOf(character: Model): number
    local byte = character:GetAttribute("HpByte")
    if typeof(byte) ~= "number" then return 1 end
    return math.clamp(byte / Cfg.HpByteMax, 0, 1)
end

local function paint(bar: Bar, fraction: number, animate: boolean)
    bar.fill.BackgroundColor3 = Hud.fillColor(fraction)
    bar.heart.Text = Hud.heartText(fraction)
    if animate and Theme.MotionEnabled then
        Theme.animate(bar.fill, 0.3, {Size = UDim2.fromScale(fraction, 1)}, Enum.EasingStyle.Quad)
    else
        bar.fill.Size = UDim2.fromScale(fraction, 1)
    end
end

-- Soft hit feedback: a bubble wobble on the bar; no screen shake, no red vignette (docs/101 s10).
local function wobbleBar(bar: Bar)
    if not Theme.MotionEnabled then return end
    bar.wobble.Scale = 1.18
    Theme.animate(bar.wobble, 0.25, {Scale = 1}, Enum.EasingStyle.Back)
end

-- ctx = {timers, leapButton, leapText, button, label, notify, shade}: Bootstrap's HUD column and helpers.
function Hud.attach(ctx: any)
    if not Config.CombatEnabled then return end
    local player = Players.LocalPlayer
    local remote = ReplicatedStorage:WaitForChild("BeDinoRemotes"):WaitForChild("CombatBite", 15)
    if not remote or not remote:IsA("RemoteEvent") then return end

    -- Bite button shares the leap row: the leap button shrinks to the left half, Bite takes the right half.
    ctx.leapButton.Size = UDim2.fromOffset(140, 60)
    ctx.leapText.Size, ctx.leapText.TextScaled = UDim2.fromOffset(80, 60), true
    local lastBiteAt = -10
    local function bite()
        if ctx.shade.Visible then return end
        local c = player.Character
        if not c or c:GetAttribute("RunState") ~= "Active" or c:GetAttribute("CombatPeaceful") == true then return end
        if os.clock() - lastBiteAt < Cfg.BiteCooldownSeconds then return end
        lastBiteAt = os.clock()
        remote:FireServer() -- no target, no damage: the server decides everything
    end
    local biteButton = ctx.button(ctx.timers, "BITE [F]", 146, 0, 140, 60, C.red, bite) -- PLACEHOLDER text button until BD-248 art
    biteButton.Name = "BiteButton"
    local ownStrip = Instance.new("Frame") -- own HP strip under the Bite label (the bigger bar floats over the own dino)
    ownStrip.Position, ownStrip.Size, ownStrip.BackgroundColor3, ownStrip.BorderSizePixel, ownStrip.ZIndex = UDim2.fromOffset(10, 46), UDim2.fromOffset(120, 8), C.panel, 0, biteButton.ZIndex + 1
    ownStrip.Parent = biteButton
    local ownCorner = Instance.new("UICorner") ownCorner.CornerRadius = UDim.new(0.5, 0) ownCorner.Parent = ownStrip
    local ownFill = Instance.new("Frame")
    ownFill.Size, ownFill.BackgroundColor3, ownFill.BorderSizePixel, ownFill.ZIndex, ownFill.Parent = UDim2.fromScale(1, 1), GREEN, 0, ownStrip.ZIndex + 1, ownStrip
    local ownFillCorner = Instance.new("UICorner") ownFillCorner.CornerRadius = UDim.new(0.5, 0) ownFillCorner.Parent = ownFill
    biteButton.TextSize = 20
    biteButton.Position = UDim2.fromOffset(146, ctx.leapButton.Position.Y.Offset)

    Input.InputBegan:Connect(function(input, processed)
        if processed then return end
        if input.KeyCode == Enum.KeyCode.F or input.KeyCode == Enum.KeyCode.ButtonX then bite() end
    end)

    local barFolder = Instance.new("Folder")
    barFolder.Name = "CombatBars"
    barFolder.Parent = player:WaitForChild("PlayerGui")
    local pool: {Bar} = {}
    for _ = 1, MAX_BARS do table.insert(pool, makeBar(barFolder)) end
    local hitAt: {[Model]: number} = {} -- last hit time per character (shows a full bar briefly)
    local hitSeqSeen: {[Model]: number} = {}
    local assigned: {[Model]: Bar} = {}
    local playerHitSeq = 0

    local function onHit(character: Model, isMine: boolean)
        hitAt[character] = os.clock()
        local bar = assigned[character]
        if bar then wobbleBar(bar) end
        -- Soft cues from the existing quiet set (docs/87): the owner has not heard these in this role yet.
        if isMine then Sfx.play("pickup_lo") end
    end

    local accumulator = 0
    RunService.Heartbeat:Connect(function(dt)
        accumulator += dt
        if accumulator < 0.1 then return end
        accumulator = 0
        local camera = workspace.CurrentCamera
        local now = os.clock()
        local me = player.Character
        -- Bite button state (client prediction only; the server enforces the cooldown).
        local cooling = now - lastBiteAt < Cfg.BiteCooldownSeconds
        local peaceful = me ~= nil and me:GetAttribute("CombatPeaceful") == true
        biteButton.BackgroundColor3 = if cooling or peaceful then C.card else C.red
        biteButton.Active = not cooling and not peaceful and me ~= nil and me:GetAttribute("RunState") == "Active"
        biteButton.Text = if peaceful then "PEACEFUL" else "BITE [F]"
        biteButton.Position = UDim2.fromOffset(146, ctx.leapButton.Position.Y.Offset)
        if me then
            local f = fractionOf(me)
            ownFill.Size, ownFill.BackgroundColor3 = UDim2.fromScale(f, 1), Hud.fillColor(f)
            local seq = me:GetAttribute("HitSeq")
            if typeof(seq) == "number" and seq ~= playerHitSeq then
                playerHitSeq = seq
                onHit(me, true)
            end
        end
        -- Assign pooled bars by distance: own dino first, then nearest; a full bar only within NEAR_STUDS or after a hit.
        local wanted: {{character: Model, distance: number}} = {}
        for _, other in Players:GetPlayers() do
            local character = other.Character
            local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
            if character and root and root:IsA("BasePart") and character:GetAttribute("RunState") == "Active" and character:GetAttribute("HpByte") ~= nil then
                local distance = if camera then (camera.CFrame.Position - root.Position).Magnitude else 0
                local seq = character:GetAttribute("HitSeq")
                if typeof(seq) == "number" and seq ~= (hitSeqSeen[character] or 0) then
                    hitSeqSeen[character] = seq
                    if character ~= me then onHit(character, false) end
                end
                local fraction = fractionOf(character)
                local recentlyHit = now - (hitAt[character] or -100) < SHOW_AFTER_HIT
                local show = character == me or (distance <= FAR_STUDS and (fraction < 1 or recentlyHit or distance <= NEAR_STUDS))
                if show then table.insert(wanted, {character = character, distance = if character == me then -1 else distance}) end
            end
        end
        table.sort(wanted, function(a, b) return a.distance < b.distance end)
        local keep: {[Model]: boolean} = {}
        for i = 1, math.min(#wanted, MAX_BARS) do keep[wanted[i].character] = true end
        for character, bar in assigned do
            if not keep[character] or not character.Parent then
                bar.gui.Adornee, bar.gui.Enabled, bar.character = nil, false, nil
                assigned[character] = nil
                hitAt[character] = nil
                hitSeqSeen[character] = nil
            end
        end
        local free = 1
        for i = 1, math.min(#wanted, MAX_BARS) do
            local character = wanted[i].character
            local bar = assigned[character]
            if not bar then
                while free <= MAX_BARS and pool[free].character ~= nil do free += 1 end
                if free > MAX_BARS then break end
                bar = pool[free]
                bar.character = character
                assigned[character] = bar
                local root = character:FindFirstChild("HumanoidRootPart")
                local scale = character:GetAttribute("VisualScale")
                local s = if typeof(scale) == "number" then scale else 1
                bar.gui.Adornee = root
                bar.gui.StudsOffsetWorldSpace = Vector3.new(0, 1.4 + 1.9 * s, 0) -- Studio check: 2.2 + 2.4 s floated too high over the head
                bar.gui.Size = UDim2.fromOffset((BAR_W + 18) * math.min(1.5, 0.9 + 0.15 * s), BAR_H + 6)
                bar.gui.Enabled = true
                bar.lastFraction = fractionOf(character)
                paint(bar, bar.lastFraction, false)
            end
            local fraction = fractionOf(character)
            if fraction ~= bar.lastFraction then
                paint(bar, fraction, true)
                bar.lastFraction = fraction
            end
        end
    end)

    -- Gentle defeat (docs/101 s6): DinoMotion already plays the soft "death" flop on RunState "Ending"; add the copy.
    player:GetAttributeChangedSignal("LastRunEndReason"):Connect(function()
        if player:GetAttribute("LastRunEndReason") == "Defeated" then
            ctx.notify("Oops! Good try!", C.blue, {key = "defeated", icon = "egg", body = "Your eggs are safe"})
        end
    end)
end

return Hud
