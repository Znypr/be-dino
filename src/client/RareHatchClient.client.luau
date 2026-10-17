--!nonstrict
-- BD-428: client side of the rare-hatch celebration. The SERVER decides (RareHatchService) and sends
-- BeDinoRemotes.RareHatch: {k = "me"} to the hatcher (fanfare + confetti + special sound, shown when the egg reveal lands),
-- {k = "all"} to everyone else (short HUD banner, text already built and cut on the server). Nothing here is sent back.
-- Confetti reuses the uploaded fx3 sparkle sheet (EffectAssets starFour), tinted: no new art. Effects Off or Reduce Motion
-- (calm) draws no confetti; Lite draws fewer pieces. The sound is Sfx "shiny_bang" (docs/77, docs/110).
-- BD-433: the OWN banner (never the others') also gets one soft light sweep at Full (RareHatch.plan().sweep), drawn from the shaftGradient render
-- only while that slot holds a real upload. A mutation hatch also lights the own dino's rim for 1.5 s (MomentRim: its own Full / Lite / Off rules).
-- BD-430 / BD-433: when the Blender starPop flipbook slot holds a real upload, the own banner gets star pops at its two ends (one at Lite,
-- none at Off or with Reduce Motion): the 16-frame twinkle plays once (EffectAssets.frameAt, OneShot) and is gone. Empty slot = today's banner.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rare = require(Shared:WaitForChild("RareHatch"))
local Settings = require(Shared:WaitForChild("SettingsModel"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local Assets = require(Shared:WaitForChild("EffectAssets"))
local Timeline = require(Shared:WaitForChild("HatchTimeline"))
local MomentRim = require(script.Parent:WaitForChild("MomentRim"))

local player = Players.LocalPlayer
local remote = (ReplicatedStorage:WaitForChild("BeDinoRemotes", 60) :: Folder):WaitForChild("RareHatch", 60)
if not remote then return end

local gui = Instance.new("ScreenGui")
gui.Name = "RareHatchGui"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.DisplayOrder = 40
gui.Parent = player:WaitForChild("PlayerGui")

local COLORS = {Color3.fromRGB(255, 214, 77), Color3.fromRGB(255, 122, 168), Color3.fromRGB(122, 211, 255), Color3.fromRGB(170, 140, 255), Color3.fromRGB(140, 235, 160)}

-- HUD banner (text only; the glow behind it is plain UI colour, not final art).
local function banner(text: string, big: boolean)
    local label = Instance.new("TextLabel")
    label.AnchorPoint = Vector2.new(0.5, 0)
    label.Position = UDim2.new(0.5, 0, 0, if big then 70 else 118)
    label.Size = UDim2.new(0, if big then 420 else 360, 0, if big then 56 else 40)
    label.BackgroundColor3 = Color3.fromRGB(40, 30, 70)
    label.BackgroundTransparency = 0.15
    label.TextColor3 = Color3.fromRGB(255, 232, 140)
    label.Font = Enum.Font.FredokaOne
    label.TextScaled = true
    label.Text = text
    label.Parent = gui
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 14) corner.Parent = label
    local limit = Instance.new("UITextSizeConstraint") limit.MaxTextSize = if big then 30 else 22 limit.Parent = label
    local pad = Instance.new("UIPadding") pad.PaddingLeft = UDim.new(0, 10) pad.PaddingRight = UDim.new(0, 10) pad.Parent = label
    task.delay(if big then 4.5 else 3.5, function()
        if label.Parent then label:Destroy() end
    end)
    return label, (if big then 420 else 360), (if big then 56 else 40)
end

-- One soft light sweep across the own banner (BD-433). The vertical shaftGradient render (bright at its top) is turned on its side and slid from
-- the left to the right end, clipped by the banner; it is gone after Rare.SweepLife seconds. Plain stock instances, no drawing in code.
local sweeps = {}
local sweepConn = nil
local function stepSweeps(dt: number)
    for i = #sweeps, 1, -1 do
        local s = sweeps[i]
        s.age += dt
        if s.age >= Rare.SweepLife or not s.obj.Parent then
            s.obj:Destroy()
            table.remove(sweeps, i)
        else
            local progress, alpha = Rare.sweepAt(s.age)
            s.obj.Position = UDim2.fromOffset(-s.len * 0.5 + (s.width + s.len) * progress, s.height * 0.5)
            s.obj.ImageTransparency = 1 - alpha
        end
    end
    if #sweeps == 0 and sweepConn then sweepConn:Disconnect() sweepConn = nil end
end
local function sweep(label, width: number, height: number)
    if not Assets.isRealUi("shaftGradient") then return end
    label.ClipsDescendants = true
    local len = width * Rare.SweepWidth
    local img = Instance.new("ImageLabel")
    img.BackgroundTransparency, img.BorderSizePixel = 1, 0
    img.AnchorPoint = Vector2.new(0.5, 0.5)
    img.Image = Assets.resolveUi("shaftGradient")
    img.ImageColor3 = Color3.fromRGB(255, 244, 204)
    img.Rotation = 90 -- bright end (top of the render) leads, to the right
    img.Size = UDim2.fromOffset(height * 1.4, len) -- turned 90 degrees: this width is the band's height, this height its length
    img.ImageTransparency = 1
    img.ZIndex = 6
    local soft = Instance.new("UIGradient") -- the render tiles around its sides: this fades the band's top and bottom edges
    soft.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.28, 0), NumberSequenceKeypoint.new(0.72, 0), NumberSequenceKeypoint.new(1, 1)})
    soft.Parent = img
    img.Parent = label
    table.insert(sweeps, {obj = img, age = 0, len = len, width = width, height = height})
    if not sweepConn then sweepConn = RunService.Heartbeat:Connect(stepSweeps) end
end

-- Star pops flanking the own banner (BD-430). At most 2 alive at once; each plays the starPop flipbook once over Rare.PopLife seconds.
local pops = {}
local popConn = nil
local function stepPops(dt: number)
    for i = #pops, 1, -1 do
        local p = pops[i]
        p.age += dt
        if p.age >= Rare.PopLife then p.obj:Destroy() table.remove(pops, i)
        else
            local t = p.age / Rare.PopLife
            Assets.setCell(p.obj, "starPop", Assets.frameAt("starPop", t, p.age, 1))
        end
    end
    if #pops == 0 and popConn then popConn:Disconnect() popConn = nil end
end
local function starPops(count: number)
    if count <= 0 or not Assets.isRealUi("starPop") then return end
    local width = gui.AbsoluteSize.X
    local half = math.min(220 + Rare.PopSize * 0.5, width * 0.5 - Rare.PopSize * 0.5) -- banner end, kept on screen on narrow phones
    local room = math.max(0, 2 - #pops)
    for i = 1, math.min(count, room) do
        local img = Instance.new("ImageLabel")
        img.BackgroundTransparency = 1
        img.AnchorPoint = Vector2.new(0.5, 0.5)
        img.Image = Assets.resolve("starPop")
        Assets.setCell(img, "starPop", 1)
        img.ImageColor3 = COLORS[1]
        img.Size = UDim2.fromOffset(Rare.PopSize, Rare.PopSize)
        img.Position = UDim2.fromOffset(width * 0.5 + (if i == 1 then half else -half), 98)
        img.ZIndex = 5
        img.Parent = gui
        table.insert(pops, {obj = img, age = 0})
    end
    if #pops > 0 and not popConn then popConn = RunService.Heartbeat:Connect(stepPops) end
end

local pieces = {}
local conn = nil
local function stepConfetti(dt: number)
    for i = #pieces, 1, -1 do
        local p = pieces[i]
        p.age += dt
        p.vy += 520 * dt
        p.x += p.vx * dt
        p.y += p.vy * dt
        if p.age > p.life then p.obj:Destroy() table.remove(pieces, i)
        else
            p.obj.Position = UDim2.fromOffset(p.x, p.y)
            p.obj.Rotation += p.spin * dt
            p.obj.ImageTransparency = math.clamp((p.age - p.life * 0.6) / (p.life * 0.4), 0, 1)
        end
    end
    if #pieces == 0 and conn then conn:Disconnect() conn = nil end
end
local function confetti(count: number)
    if count <= 0 then return end
    local width = gui.AbsoluteSize.X
    local room = math.max(0, 36 - #pieces) -- never more than 36 pieces alive at once, even on repeated rares
    for i = 1, math.min(count, room) do
        local img = Instance.new("ImageLabel")
        img.BackgroundTransparency = 1
        img.AnchorPoint = Vector2.new(0.5, 0.5)
        img.Image = Assets.resolve("starFour")
        Assets.setCell(img, "starFour", 7)
        img.ImageColor3 = COLORS[(i % #COLORS) + 1]
        local size = 18 + (i * 7) % 18
        img.Size = UDim2.fromOffset(size, size)
        img.ZIndex = 5
        img.Parent = gui
        table.insert(pieces, {obj = img, x = width * (0.1 + 0.8 * ((i * 37 % 100) / 100)), y = -20, vx = ((i * 53 % 200) - 100) * 1.4,
            vy = 120 + (i * 29 % 120), spin = ((i * 71 % 200) - 100) * 3, age = 0, life = 2.4 + (i % 5) * 0.2})
    end
    if not conn then conn = RunService.Heartbeat:Connect(stepConfetti) end
end

local lastMe = -100
local function celebrate(data)
    local now = os.clock()
    if now - lastMe < Rare.Celebrate.gap then return end -- several rares in a row: the first one gets the show
    lastMe = now
    local s = Settings.get()
    local plan = Rare.plan(s.effects, s.calm, tostring(data.kind))
    -- show it when this egg's reveal lands (not when the server settled it)
    local delay = Timeline.durations(not s.calm, tonumber(data.rarity) or 1, false, false).revealAt
    task.delay(delay, function()
        if plan.banner then
            local label, width, height = banner(tostring(data.text), true)
            starPops(plan.pop)
            if plan.sweep > 0 then sweep(label, width, height) end -- own banner only: the "all" path below never sweeps
        end
        if data.kind == "mutation" or data.mutation == true then
            local mutationId = if type(data.mutationId) == "string" and #data.mutationId <= 24 then data.mutationId else nil
            pcall(MomentRim.play, player.Character, {mutationId = mutationId})
        end
        confetti(plan.confetti)
        if plan.sound ~= "" then pcall(Sfx.play, plan.sound) end -- BD-606: a secret find adds no sound of its own
    end)
end

remote.OnClientEvent:Connect(function(data)
    if type(data) ~= "table" or type(data.text) ~= "string" then return end
    if #data.text > 80 then return end
    if data.k == "me" then celebrate(data)
    elseif data.k == "all" then banner(data.text, false) end
end)
