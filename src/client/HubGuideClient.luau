--!strict
-- BD-289 (docs/104 s7.6): the soft moss trail for "Teleport to shops" OFF. show(station) draws up to 24 small moss-green glow
-- dots (pooled anchored Parts, each with one Billboard sprite from the alpha FX sheet "starFour") along the layout paths from
-- the player's dino to the station; they fade in, ripple gently, and fade out when the player steps onto the pad (the
-- walk-up logic then opens the station once) or after 25 s. cancel() removes them at once. Reduce Motion (Settings.calm):
-- static dots, no fade, no ripple. All decisions live in the pure HubGuideRules. attach() returns nil while Config.CaveHub
-- is false. The parts are lighting-style FX, not model art (no asset beyond the existing FX sheet).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Layout = require(Shared:WaitForChild("CaveHubLayout"))
local Rules = require(Shared:WaitForChild("HubGuideRules"))
local WalkRules = require(Shared:WaitForChild("HubWalkUpRules"))
local Settings = require(Shared:WaitForChild("SettingsModel"))
local Assets = require(Shared:WaitForChild("EffectAssets"))

local Client = {}
local Moss = Color3.fromRGB(150, 210, 120)
local SPRITE, CELL = "starFour", 6 -- a mid-size star cell of the alpha sheet (built-in sparkle until the real art is wired)
local DOT_SIZE = 1.3 -- studs
local LIFT = 0.6 -- studs above the floor

-- Returns {show = function(station): boolean, cancel = function()} or nil with the flag off.
function Client.attach(): any?
    if Config.CaveHub ~= true then return nil end
    local player = Players.LocalPlayer
    local pool: {{part: Part, face: ImageLabel, board: BillboardGui}} = {}
    local folder: Folder? = nil
    local state: any = nil
    local count = 0
    local connection: RBXScriptConnection? = nil

    local function ensurePool()
        if folder then return end
        local f = Instance.new("Folder")
        f.Name = "HubGuideDots"
        for i = 1, Rules.MaxDots do
            local part = Instance.new("Part")
            part.Name, part.Anchored, part.CanCollide, part.CanTouch, part.CanQuery, part.CastShadow = "Dot" .. i, true, false, false, false, false
            part.Transparency, part.Size = 1, Vector3.new(0.2, 0.2, 0.2)
            local board = Instance.new("BillboardGui")
            board.Size, board.LightInfluence, board.AlwaysOnTop, board.Active = UDim2.fromScale(DOT_SIZE, DOT_SIZE), 0, false, false
            board.Enabled = false
            local face = Instance.new("ImageLabel")
            face.BackgroundTransparency, face.Size, face.ImageColor3, face.Image = 1, UDim2.fromScale(1, 1), Moss, Assets.resolveUi(SPRITE)
            Assets.setCell(face, SPRITE, CELL)
            face.Parent = board
            board.Parent = part
            part.Parent = f
            pool[i] = {part = part, face = face, board = board}
        end
        f.Parent = workspace
        folder = f
    end

    local function hide()
        if connection then connection:Disconnect() connection = nil end
        state, count = nil, 0
        for _, d in pool do d.board.Enabled = false end
    end

    local function tick()
        local s = state
        if s == nil then return end
        local calm = Settings.calm()
        local character = player.Character
        local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
        if not root or not root:IsA("BasePart") or character:GetAttribute("RunState") ~= "Sanctuary" then hide() return end
        local pad = WalkRules.padAt(root.Position.X, root.Position.Z)
        local now = os.clock()
        local alpha, finished = Rules.update(s, now, pad, calm)
        if finished then hide() return end
        for i = 1, count do
            local d = pool[i]
            local scale = Rules.pulse(i, count, now, calm) * DOT_SIZE
            d.board.Size = UDim2.fromScale(scale, scale)
            d.face.ImageTransparency = 1 - alpha * 0.85
        end
    end

    local function show(station: string): boolean
        local character = player.Character
        local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
        if not root or not root:IsA("BasePart") then return false end
        local route = Rules.route(Layout, root.Position.X, root.Position.Z, station)
        if route == nil then return false end -- already on that pad, or not in the cave: the caller opens the menu plainly
        ensurePool()
        hide()
        local dots = Rules.dots(route.points, Rules.MaxDots)
        count = #dots
        for i, p in dots do
            local d = pool[i]
            d.part.Position = Vector3.new(p.x, Layout.floorHeight(p.x, p.z) + LIFT, p.z)
            d.board.Enabled = true
        end
        state = Rules.begin(station, os.clock())
        tick()
        if state ~= nil then connection = RunService.Heartbeat:Connect(tick) end
        return true
    end

    return {show = show, cancel = hide}
end

return Client
