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
-- BD-245: wild predators (workspace.BeDinoNpcs, attribute NpcPredator) get a purple "wild" bar so nobody mistakes them for a player.
local WILD, WILD_LOW, WILD_HEART = Color3.fromRGB(176, 120, 255), Color3.fromRGB(255, 150, 190), Color3.fromRGB(176, 120, 255)
local HEART = Color3.fromRGB(255, 120, 140)

-- Pure helpers (also used by the verifier through a static read; keep them simple).
function Hud.fillColor(fraction: number, wild: boolean?): Color3
    if wild then return if fraction > 0.25 then WILD else WILD_LOW end
    if fraction > 0.5 then return GREEN elseif fraction > 0.25 then return YELLOW end
    return ORANGE
end
-- Heart glyph by fraction: full, half, small (never colour alone).
function Hud.heartText(fraction: number): string
    if fraction > 0.5 then return "\u{2665}" elseif fraction > 0.25 then return "\u{2661}" end
    return "\u{00B7}"
end

-- Bar height over a dino: the scale rule, but never lower than just above the top of the model (topAboveRoot + 0.8).
function Hud.barLift(scale: number, topAboveRoot: number): number
    return math.max(1.4 + 1.9 * scale, topAboveRoot + 0.8)
end
local function topAboveRoot(character: Model): number
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root or not root:IsA("BasePart") then return 0 end
    local cf, size = character:GetBoundingBox()
    return cf.Position.Y + size.Y / 2 - root.Position.Y
end

type Bar = {gui: BillboardGui, fill: Frame, heart: TextLabel, wobble: UIScale, character: Model?, lastFraction: number, lastCue: string, placedScale: number}

-- BD-314: a big soft "!" bubble over a wild predator that noticed you (alert and windup). One lazy BillboardGui per NPC (at most 6).
local alertBubbles: {[Model]: BillboardGui} = setmetatable({}, {__mode = "k"}) :: any
local function setAlertBubble(character: Model, root: BasePart, on: boolean)
    local gui = alertBubbles[character]
    if not gui then
        if not on then return end
        gui = Instance.new("BillboardGui")
        gui.Name, gui.Size, gui.AlwaysOnTop, gui.LightInfluence, gui.ResetOnSpawn, gui.MaxDistance = "AlertBubble", UDim2.fromOffset(52, 52), true, 0, false, FAR_STUDS + 5
        local bubble = Instance.new("TextLabel")
        bubble.Size, bubble.BackgroundColor3, bubble.Text, bubble.TextColor3 = UDim2.fromScale(1, 1), C.gold, "!", C.outline
        bubble.Font, bubble.TextSize, bubble.BorderSizePixel = Enum.Font.FredokaOne, 38, 0
        bubble.Parent = gui
        local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0.5, 0) corner.Parent = bubble
        local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = C.outline, 3, bubble
        gui.Parent = root
        alertBubbles[character] = gui
    end
    local scaleNow = character:GetAttribute("VisualScale")
    gui.StudsOffsetWorldSpace = Vector3.new(0, Hud.barLift(if typeof(scaleNow) == "number" then scaleNow else 1, topAboveRoot(character)) + 2.4, 0)
    gui.Adornee = root
    gui.Enabled = on
end

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
    return {gui = gui, fill = fill, heart = heart, wobble = wobble, character = nil, lastFraction = 1, lastCue = "", placedScale = -1}
end

local function fractionOf(character: Model): number
    local byte = character:GetAttribute("HpByte")
    if typeof(byte) ~= "number" then return 1 end
    return math.clamp(byte / Cfg.HpByteMax, 0, 1)
end

local function isWild(character: Model): boolean
    return character:GetAttribute("NpcPredator") == true
end

local function paint(bar: Bar, fraction: number, animate: boolean)
    local character = bar.character
    local wild = character ~= nil and isWild(character)
    bar.fill.BackgroundColor3 = Hud.fillColor(fraction, wild)
    bar.heart.TextColor3 = if wild then WILD_HEART else HEART
    -- A wild predator that noticed you shows "!" (alert and the half-second windup before a bite): time to run or dodge.
    local cue = if character and wild then character:GetAttribute("NpcCue") else nil
    bar.heart.Text = if cue == "alert" or cue == "windup" then "!" else Hud.heartText(fraction)
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
        if not c or c:GetAttribute("RunState") ~= "Active" then return end
        if os.clock() - lastBiteAt < Cfg.BiteCooldownSeconds then return end
        lastBiteAt = os.clock()
        remote:FireServer() -- no target, no damage: the server decides everything
    end
    -- BD-314: a soft, friendly CHOMP button (calm palette colour, pill shape, 60 px tall >= 44 px target). No key hint on touch
    -- devices; on desktop a small "F" chip in the corner. PLACEHOLDER text button until BD-248 art.
    local biteButton = ctx.button(ctx.timers, "CHOMP", 146, 0, 140, 60, C.accent, bite)
    biteButton.Name = "BiteButton"
    local pill = biteButton:FindFirstChildOfClass("UICorner")
    if pill then pill.CornerRadius = UDim.new(0, 28) end
    if Input.KeyboardEnabled and not Input.TouchEnabled then
        local chip = Instance.new("TextLabel")
        chip.Name, chip.Text, chip.Size, chip.Position = "KeyHint", "F", UDim2.fromOffset(22, 22), UDim2.fromOffset(112, 4)
        chip.BackgroundColor3, chip.TextColor3, chip.Font, chip.TextSize = C.panel, C.text, Enum.Font.FredokaOne, 15
        chip.BorderSizePixel, chip.ZIndex, chip.Parent = 0, biteButton.ZIndex + 2, biteButton
        local chipCorner = Instance.new("UICorner") chipCorner.CornerRadius = UDim.new(0.5, 0) chipCorner.Parent = chip
    end
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
    local npcWindupSeen: {[Model]: boolean} = setmetatable({}, {__mode = "k"}) :: any

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
        biteButton.BackgroundColor3 = if cooling then C.card else C.accent
        biteButton.Active = not cooling and me ~= nil and me:GetAttribute("RunState") == "Active"
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
        -- Wild predators (BD-245): server-made models, no RunState; same bar pool and distance rules as players.
        local npcFolder = workspace:FindFirstChild("BeDinoNpcs")
        for _, character in if npcFolder then npcFolder:GetChildren() else {} do
            local root = if character:IsA("Model") then character:FindFirstChild("HumanoidRootPart") else nil
            if character:IsA("Model") and root and root:IsA("BasePart") and character:GetAttribute("HpByte") ~= nil and character:GetAttribute("NpcFading") ~= true then
                local distance = if camera then (camera.CFrame.Position - root.Position).Magnitude else 0
                local seq = character:GetAttribute("HitSeq")
                if typeof(seq) == "number" and seq ~= (hitSeqSeen[character] or 0) then
                    hitSeqSeen[character] = seq
                    onHit(character, false)
                end
                local cue = character:GetAttribute("NpcCue")
                setAlertBubble(character, root, (cue == "alert" or cue == "windup") and distance <= FAR_STUDS)
                if cue == "windup" and npcWindupSeen[character] ~= true and distance <= NEAR_STUDS then
                    npcWindupSeen[character] = true
                    Sfx.play("pickup_hi") -- soft heads-up (existing quiet cue, PLACEHOLDER until a dedicated sound is made)
                elseif cue ~= "windup" then
                    npcWindupSeen[character] = nil
                end
                local fraction = fractionOf(character)
                local recentlyHit = now - (hitAt[character] or -100) < SHOW_AFTER_HIT
                if distance <= FAR_STUDS and (fraction < 1 or recentlyHit or distance <= NEAR_STUDS or cue == "alert" or cue == "windup") then
                    table.insert(wanted, {character = character, distance = distance})
                end
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
                bar.gui.Adornee = character:FindFirstChild("HumanoidRootPart")
                bar.placedScale = -1
                bar.gui.Enabled = true
                bar.lastFraction = fractionOf(character)
                bar.lastCue = if isWild(character) then tostring(character:GetAttribute("NpcCue") or "") else ""
                paint(bar, bar.lastFraction, false)
            end
            -- BD-310: place (and re-place when the dino grows). 1.4 + 1.9 s (Studio check: 2.2 + 2.4 s floated too high) put the bar INSIDE
            -- the head above s ~ 1.6, for a big player and for the big wild predators alike, and it was never updated after growth.
            local scaleNow = character:GetAttribute("VisualScale")
            local s = if typeof(scaleNow) == "number" then scaleNow else 1
            if s ~= bar.placedScale then
                bar.placedScale = s
                bar.gui.StudsOffsetWorldSpace = Vector3.new(0, Hud.barLift(s, topAboveRoot(character)), 0)
                bar.gui.Size = UDim2.fromOffset((BAR_W + 18) * math.min(1.5, 0.9 + 0.15 * s), BAR_H + 6)
            end
            local fraction = fractionOf(character)
            local cueNow =if isWild(character) then tostring(character:GetAttribute("NpcCue") or "") else ""
            if cueNow ~= bar.lastCue then
                bar.lastCue = cueNow
                paint(bar, fraction, false)
                bar.lastFraction = fraction
            elseif fraction ~= bar.lastFraction then
                paint(bar, fraction, true)
                bar.lastFraction = fraction
            end
        end
    end)

    -- Gentle defeat (docs/101 s6): DinoMotion already plays the soft "death" flop on RunState "Ending". The "Oops! Good try!" copy
    -- is the first section of the Run Complete modal (Bootstrap "results", BD-315), so no toast is shown here: a toast was
    -- covered by that modal.
    require(script.Parent.NpcMotion).attach()
end

return Hud
