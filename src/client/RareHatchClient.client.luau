--!nonstrict
-- BD-428: client side of the rare-hatch celebration. The SERVER decides (RareHatchService) and sends
-- BeDinoRemotes.RareHatch: {k = "me"} to the hatcher (fanfare + confetti + special sound, shown when the egg reveal lands),
-- {k = "all"} to everyone else (short HUD banner, text already built and cut on the server). Nothing here is sent back.
-- Confetti reuses the uploaded fx3 sparkle sheet (EffectAssets starFour), tinted: no new art. Effects Off or Reduce Motion
-- (calm) draws no confetti; Lite draws fewer pieces. The sound is Sfx "shiny_bang" (docs/77, docs/110).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rare = require(Shared:WaitForChild("RareHatch"))
local Settings = require(Shared:WaitForChild("SettingsModel"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local Assets = require(Shared:WaitForChild("EffectAssets"))
local Timeline = require(Shared:WaitForChild("HatchTimeline"))

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
        if plan.banner then banner(tostring(data.text), true) end
        confetti(plan.confetti)
        pcall(Sfx.play, plan.sound)
    end)
end

remote.OnClientEvent:Connect(function(data)
    if type(data) ~= "table" or type(data.text) ~= "string" then return end
    if #data.text > 80 then return end
    if data.k == "me" then celebrate(data)
    elseif data.k == "all" then banner(data.text, false) end
end)
