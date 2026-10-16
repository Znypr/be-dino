--!strict
-- BD-288 / BD-292 (docs/104 s7, s8): client side of "teleport to a Cave hub station". Bootstrap hands over its menu
-- functions with one `attach` call; rail buttons ask `press(destination)` first. Everything is behind Config.CaveHub:
-- with it false attach() returns at once and press() answers false, so the rail behaves exactly as before.
-- Decisions live in the pure HubTravelClientRules (tools/verify_hub_travel_client.py). The server (HubTravelService)
-- does the move; this file only fades, asks, and opens the menu when the ack says ok.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Rules = require(Shared:WaitForChild("HubTravelClientRules"))
local Settings = require(Shared:WaitForChild("SettingsModel"))
local Sfx = require(Shared:WaitForChild("Sfx"))
local Copy = require(Shared:WaitForChild("HubSignCopy"))
local Guide = require(script.Parent:WaitForChild("HubGuideClient")) -- BD-289: moss trail for "Teleport to shops" OFF (no-op while the flag is off)
local WalkUp = require(script.Parent:WaitForChild("HubWalkUpClient")) -- BD-289: sign prompts + pad dwell (no-op while the flag is off)
local GateBar = require(script.Parent:WaitForChild("HubGateClient")) -- BD-290: "Leaving..." bar at the Island Gate (no-op while the flag is off)

local Client = {}
local player = Players.LocalPlayer
local ctx: any = nil
local busy = false
local at: string? = nil -- the station this client last travelled to (cleared when a run starts); the server HubStation attribute is not cleared yet
local serial = 0
local overlay: Frame? = nil
local walkUp: any = nil -- {note} from HubWalkUpClient once attached
local guide: any = nil -- {show, cancel} from HubGuideClient once attached
local chip: TextButton? = nil
local Cream = Color3.fromRGB(255, 244, 220)

-- BD-391/405: does this player own the Fast travel perk? (ProgressionJson is the server's own copy, read-only here.)
local function ownsFastTravel(): boolean
    local raw = require(script.Parent:WaitForChild("PrivateState")).get("ProgressionJson")
    if typeof(raw) ~= "string" then return false end
    local ok, data = pcall(function() return game:GetService("HttpService"):JSONDecode(raw) end)
    return ok and typeof(data) == "table" and typeof(data.perks) == "table" and data.perks.fastTravel == true
end
Client.ownsFastTravel = ownsFastTravel

local function runState(): any
    local character = player.Character
    return if character then character:GetAttribute("RunState") else nil
end

local function remote(): RemoteFunction?
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local found = folder and folder:FindFirstChild("HubTravel")
    return if found and found:IsA("RemoteFunction") then found else nil
end

local function fadeTo(transparency: number, seconds: number)
    local o = overlay
    if not o then return end
    o.Visible = true
    local tween = TweenService:Create(o, TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {BackgroundTransparency = transparency})
    tween:Play()
    tween.Completed:Wait()
    if transparency >= 1 then o.Visible = false end
end

local function refreshChip()
    local c = chip
    if c then c.Visible = Rules.chipVisible(Config.CaveHub, runState(), at, busy) end
end

-- One trip: fade in, ask the server, fade out, then `onArrive` (open the menu) or a calm toast.
local function travel(station: string, onArrive: (() -> ())?)
    local fn = remote()
    if busy or fn == nil then return end
    busy = true
    serial += 1
    local mine = serial
    refreshChip()
    local timing = Rules.fade(Settings.calm())
    if timing.cue then Sfx.play("shop_refresh") end
    task.delay(Rules.TimeoutSeconds, function() -- never leave the screen covered if the server never answers
        if busy and serial == mine then
            busy = false
            if overlay then overlay.BackgroundTransparency = 1 overlay.Visible = false end
            refreshChip()
        end
    end)
    task.spawn(function()
        fadeTo(0, timing.inSeconds)
        local called, ack = pcall(function() return (fn :: RemoteFunction):InvokeServer({station = station}) end)
        if serial ~= mine then return end -- the time-out already let go
        local ok, reason = Rules.readAck(if called then ack else nil, station)
        if not called then reason = "error" end
        busy = false
        if ok then
            at = station
            if walkUp then walkUp.note(station) end -- arriving by teleport must not also trigger the pad dwell
            if onArrive then pcall(onArrive) end
        else
            ctx.notify(Rules.refusal(reason), nil)
        end
        fadeTo(1, timing.outSeconds)
        refreshChip()
    end)
end

local function applyDimming()
    local state = runState()
    for _, b in ctx.buttons do
        local destination = b:GetAttribute("Destination")
        local dim = Rules.dimmed(destination, Config.CaveHub, state)
        local name = b:FindFirstChildWhichIsA("TextLabel")
        if name then
            if b:GetAttribute("RailName") == nil then b:SetAttribute("RailName", name.Text) end
            name.Text = if dim then Rules.HomeHint else (b:GetAttribute("RailName") :: string)
        end
        b.BackgroundTransparency = if dim then 0.55 else 0
        if b.AbsoluteSize.Y > 0 and b.AbsoluteSize.Y < Rules.MinTarget then b:SetAttribute("SmallTarget", true) end
    end
end

-- true = handled here (travelling or blocked); false = the caller opens the menu as before.
function Client.press(destination: string): boolean
    if ctx == nil or Config.CaveHub ~= true then return false end
    if guide then guide.cancel() end -- pressing any rail button cancels a trail still showing
    local decision = Rules.decide({
        caveHub = true, destination = destination, runState = runState(),
        fastTravelPerk = Config.FastTravelPerk == true, fastTravelOwned = ownsFastTravel(),
        teleportShops = Settings.teleportShops(), remote = remote() ~= nil, busy = busy,
    })
    if decision.kind == "blocked" then
        if decision.toast then ctx.notify(decision.toast, nil) end
        return true
    elseif decision.kind == "guide" then
        if guide and guide.show(decision.station) then
            ctx.notify(Copy.GuideToast, nil)
            return true
        end
        return false -- already on that pad (or not in the cave): open the menu plainly
    elseif decision.kind == "travel" then
        travel(decision.station, function()
            if destination == "fusion" then ctx.openFusion() else ctx.open(destination) end
        end)
        return true
    end
    return false
end

-- BD-382: one tap on a rail button / the chip while a station menu (ModalScrim or Fusion) is open closes it and travels.
local function scrimUp(): boolean
    local scrim = ctx.gui:FindFirstChild("ModalScrim")
    if scrim and scrim:IsA("GuiObject") and scrim.Visible then return true end
    local fusion = player:WaitForChild("PlayerGui"):FindFirstChild("BeDinoFusionUI")
    return fusion ~= nil and fusion:IsA("ScreenGui") and fusion.Enabled
end

local function routeTap(input: InputObject)
    if input.UserInputType ~= Enum.UserInputType.MouseButton1 and input.UserInputType ~= Enum.UserInputType.Touch then return end
    if busy or not scrimUp() then return end
    local origin = (ctx.gui :: any).AbsolutePosition :: Vector2
    local px, py = input.Position.X - origin.X, input.Position.Y - origin.Y
    local targets = {}
    for _, b in ctx.buttons do
        local dest = b:GetAttribute("Destination")
        if b.Visible and b.AbsoluteSize.X > 0 then
            table.insert(targets, {kind = "rail", destination = dest, x = b.AbsolutePosition.X, y = b.AbsolutePosition.Y, w = b.AbsoluteSize.X, h = b.AbsoluteSize.Y,
                enabled = not Rules.dimmed(dest, true, runState())})
        end
    end
    local c = chip
    if c and c.Visible then table.insert(targets, {kind = "chip", x = c.AbsolutePosition.X, y = c.AbsolutePosition.Y, w = c.AbsoluteSize.X, h = c.AbsoluteSize.Y}) end
    local hit = Rules.routeScrimTap(true, true, px, py, targets)
    if hit == nil then return end
    task.delay(Rules.SettleSeconds, function()
        if busy then return end
        if ctx.close then ctx.close() end
        pcall(function() require(script.Parent:WaitForChild("FusionMenu")).close() end)
        if hit.kind == "chip" then travel(Rules.HeartStation, nil) return end
        local dest = hit.destination :: string
        if Client.press(dest) then return end
        if dest == "fusion" then ctx.openFusion() else ctx.open(dest) end
    end)
end

function Client.attach(c: any)
    if Config.CaveHub ~= true or ctx ~= nil then return end
    ctx = c
    local gui: Instance = c.gui
    walkUp = WalkUp.attach(c, function() return busy end)
    GateBar.attach(gui)
    guide = Guide.attach()
    local o = Instance.new("Frame")
    o.Name, o.BackgroundColor3, o.BackgroundTransparency, o.BorderSizePixel = "HubTravelFade", Cream, 1, 0
    o.Size, o.Visible, o.Active, o.ZIndex = UDim2.fromScale(1, 1), false, false, 190
    o.Parent = gui
    overlay = o
    local b = Instance.new("TextButton")
    b.Name, b.Text, b.Font, b.TextSize, b.TextColor3 = "BackToMiddle", Rules.ChipText, Enum.Font.FredokaOne, 22, Color3.fromRGB(255, 255, 255)
    b.BackgroundColor3, b.AnchorPoint, b.Position = Color3.fromRGB(120, 90, 200), Vector2.new(0.5, 1), UDim2.new(0.5, 0, 1, -Rules.ChipBottom)
    b.Size, b.Visible, b.ZIndex, b.AutoButtonColor = UDim2.fromOffset(240, 48), false, 8, true
    local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 12) corner.Parent = b
    local stroke = Instance.new("UIStroke") stroke.Thickness, stroke.Color = 3, Color3.fromRGB(40, 28, 70) stroke.Parent = b
    b.Parent = gui
    chip = b
    b.Activated:Connect(function()
        if ctx.close then ctx.close() end
        travel(Rules.HeartStation, nil)
    end)
    local function watchCharacter(character: Model)
        character:GetAttributeChangedSignal("RunState"):Connect(function() if runState() ~= "Sanctuary" then at = nil end applyDimming() refreshChip() end)
        applyDimming()
        refreshChip()
    end
    UserInputService.InputEnded:Connect(routeTap)
    player.CharacterAdded:Connect(watchCharacter)
    if player.Character then watchCharacter(player.Character) else applyDimming() end
end

return Client
