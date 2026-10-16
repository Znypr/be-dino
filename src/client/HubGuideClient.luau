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
local LOOK = Rules.Look -- BD-396: bigger (1.8 studs), brighter, softer; halo + white core
local DOT_SIZE = LOOK.dotSize
local LIFT = 0.8 -- studs above the floor
local CoreWhite = Color3.fromRGB(255, 255, 255)
local ARROW_MARGIN = 44 -- px from the screen edge

-- Returns {show = function(station): boolean, cancel = function()} or nil with the flag off.
function Client.attach(): any?
    if Config.CaveHub ~= true then return nil end
    local player = Players.LocalPlayer
    local pool: {{part: Part, face: ImageLabel, halo: Frame, core: ImageLabel, board: BillboardGui}} = {}
    local arrowGui: ScreenGui? = nil
    local arrow: TextLabel? = nil
    local target: Vector3? = nil
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
            -- the board is the halo's size (haloScale x the dot) so the soft glow is never clipped
            board.Size, board.LightInfluence, board.AlwaysOnTop, board.Active = UDim2.fromScale(DOT_SIZE * LOOK.haloScale, DOT_SIZE * LOOK.haloScale), 0, false, false
            pcall(function() board.Brightness = LOOK.brightness end) -- brighter in daylight (Neon-free)
            board.Enabled = false
            -- PLACEHOLDER soft glow (a round tinted disc; no new art): the real glow sprite is a later asset task (docs/72).
            local halo = Instance.new("Frame")
            halo.Name, halo.AnchorPoint, halo.Position, halo.Size = "Halo", Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromScale(1, 1)
            halo.BackgroundColor3, halo.BackgroundTransparency, halo.BorderSizePixel = Moss, LOOK.haloTransparency, 0
            local round = Instance.new("UICorner") round.CornerRadius = UDim.new(.5, 0) round.Parent = halo
            halo.Parent = board
            local face = Instance.new("ImageLabel")
            face.Name, face.AnchorPoint, face.Position = "Dot", Vector2.new(.5, .5), UDim2.fromScale(.5, .5)
            face.BackgroundTransparency, face.Size, face.ImageColor3, face.Image = 1, UDim2.fromScale(1 / LOOK.haloScale, 1 / LOOK.haloScale), Moss, Assets.resolveUi(SPRITE)
            Assets.setCell(face, SPRITE, CELL)
            face.Parent = board
            local core = Instance.new("ImageLabel")
            core.Name, core.AnchorPoint, core.Position = "Core", Vector2.new(.5, .5), UDim2.fromScale(.5, .5)
            core.BackgroundTransparency, core.Size, core.ImageColor3, core.Image = 1, UDim2.fromScale(LOOK.coreScale / LOOK.haloScale, LOOK.coreScale / LOOK.haloScale), CoreWhite, Assets.resolveUi(SPRITE)
            Assets.setCell(core, SPRITE, CELL)
            core.Parent = board
            board.Parent = part
            part.Parent = f
            pool[i] = {part = part, face = face, halo = halo, core = core, board = board}
        end
        f.Parent = workspace
        folder = f
    end

    local function hide()
        if connection then connection:Disconnect() connection = nil end
        state, count, target = nil, 0, nil
        for _, d in pool do d.board.Enabled = false end
        if arrow then arrow.Visible = false end
    end

    -- BD-396: a small arrow on the screen edge points at the station while it is off-screen (static when Reduce Motion is on).
    local function ensureArrow()
        if arrow then return end
        local gui = Instance.new("ScreenGui")
        gui.Name, gui.ResetOnSpawn, gui.IgnoreGuiInset, gui.DisplayOrder = "HubGuideArrow", false, true, 30
        local label = Instance.new("TextLabel") -- PLACEHOLDER arrow glyph until a drawn arrow icon exists (docs/72)
        label.Name, label.Text, label.TextSize, label.Font = "Arrow", "▲", 34, Enum.Font.GothamBold
        label.TextColor3, label.TextStrokeColor3, label.TextStrokeTransparency = Moss, Color3.fromRGB(30, 60, 30), 0.2
        label.BackgroundTransparency, label.Size, label.AnchorPoint, label.Visible = 1, UDim2.fromOffset(44, 44), Vector2.new(.5, .5), false
        label.Parent = gui
        gui.Parent = player:WaitForChild("PlayerGui")
        arrowGui, arrow = gui, label
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
            d.face.ImageTransparency = 1 - alpha * 0.95
            d.core.ImageTransparency = 1 - alpha
            d.halo.BackgroundTransparency = 1 - alpha * (1 - LOOK.haloTransparency) * Rules.glow(i, count, now, calm) / 0.8
        end
        local camera = workspace.CurrentCamera
        if arrow and camera and target and alpha > 0 then
            local view = camera:WorldToViewportPoint(target)
            local size = camera.ViewportSize
            local a = Rules.edgeArrow(view.X, view.Y, view.Z, size.X, size.Y, ARROW_MARGIN)
            arrow.Visible = a.visible
            if a.visible then
                arrow.Position, arrow.Rotation = UDim2.fromOffset(a.x, a.y), a.angle
                arrow.TextTransparency = 1 - alpha
            end
        elseif arrow then arrow.Visible = false end
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
        ensureArrow()
        for _, st in Layout.get().stations do
            if st.id == station then target = Vector3.new(st.x, Layout.floorHeight(st.x, st.z + Layout.CenterZ) + 3, st.z + Layout.CenterZ) end
        end
        state = Rules.begin(station, os.clock())
        tick()
        if state ~= nil then connection = RunService.Heartbeat:Connect(tick) end
        return true
    end

    return {show = show, cancel = hide}
end

return Client
