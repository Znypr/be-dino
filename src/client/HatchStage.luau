--!strict
-- BD-1211 (BD-1206 cohesion order step 1, docs/240 R1/R2/R3/R7, style tile v2 boards 2-4): with Config.HatchStageEnabled the hatch is a full
-- STAGE over the world, not a window: the shared modal's stud body, frame and header strip are hidden while the hatch is open, the dark scrim
-- becomes a light veil with soft rays (the uploaded fx3 rays picture) behind the egg, "Egg 2 of 5" sits in a cream chip at the top, and every
-- dark plate or chip the hatch builds (colour and pattern buckets, labels, "Skip the rest") is turned into the one style: cream plate with an ink
-- outline and ink text, buttons grey (the green NEXT EGG stays green). The X stays (red, top right of the stage).
-- Bootstrap calls apply() when the hatch opens and restore() whenever any screen opens or the modal closes, so every other screen keeps its
-- window exactly as before. Flag off = this file is never required.
local TweenService = game:GetService("TweenService")
local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Effects = require(Shared:WaitForChild("EffectAssets"))
local Chip = require(Shared:WaitForChild("ChipStyle")) -- BD-1070: every tag on the stage is the one chip style

local Stage = {}
Stage.Cream = Color3.fromRGB(255, 247, 227)
Stage.Ink = Color3.fromRGB(46, 38, 30)
Stage.Grey = Color3.fromRGB(196, 200, 208)
Stage.Veil = .78 -- scrim transparency on the stage (the window used .42): the world stays visible under the rays

local function luminance(c: Color3): number return .299 * c.R + .587 * c.G + .114 * c.B end
-- true for the dark navy / slate plates the old window style used (R1)
function Stage.isDark(c: Color3): boolean return luminance(c) < .42 end
-- true for a green "main" button (kept: one green button per screen, R3)
function Stage.isGreen(c: Color3): boolean return c.G > .5 and c.G > c.R * 1.25 and c.G > c.B * 1.25 end

local state: {restore: {() -> ()}, conns: {RBXScriptConnection}}? = nil
-- BD-1212: the uploaded Blender sunburst (resources/ui/v2/hatch/hatch-rays-v1.png, docs/77), white on transparency, tinted per rarity
Stage.RaysImage = "rbxassetid://101879664534811"
-- BD-1212 reveal pieces (ChatGPT art on the owner-approved target, cut by tools/ui_piece_cut.py, docs/77 ui_hatch_reveal_*)
Stage.Art = {ribbon = "rbxassetid://121511299885018", plate = "rbxassetid://131844292652547", new = "rbxassetid://83897608776051",
    pedestal = "rbxassetid://120694157611008"}
-- top-level UI that stays on the stage: the hatch's own layers, the reveal flash and the toasts
Stage.KeepOnStage = {ModalScrim = true, HatchUiLayer = true, HatchTapCatcher = true, RevealFlash = true, Toasts = true}
-- the rarity ladder (docs/evidence/2026-11-16-hatch-fullscreen): ray strength, veil, word size, tilt, confetti
Stage.Ladder = {
    {word = "COMMON", rays = .55, veil = .78, size = 54, tilt = 0, confetti = 0},
    {word = "UNCOMMON", rays = .45, veil = .76, size = 58, tilt = 0, confetti = 0},
    {word = "RARE!", rays = .35, veil = .72, size = 62, tilt = -2, confetti = 6},
    {word = "EPIC!", rays = .3, veil = .66, size = 66, tilt = -3, confetti = 10},
    {word = "LEGENDARY!", rays = .2, veil = .6, size = 76, tilt = -4, confetti = 18},
    {word = "MYTHIC!", rays = .15, veil = .55, size = 80, tilt = -4, confetti = 26},
}
local stageParts: any = nil
local pending: any = nil
-- BD-1288 slice 1 (Config.HatchStoryboardEnabled): Client/HatchStoryboard sets these hooks (HatchStoryboard.init); nil / false = as before.
Stage.HideCrystals = false -- true: the crystal counter steps aside too (the storyboard stage hides the whole HUD)
Stage.eggRect = nil :: ((any) -> any)? -- where the paint flipbook goes: {x, y, side} in shade px
Stage.isNew = nil :: (() -> boolean)? -- one more reason for the NEW! sticker (a species not owned before the batch)
Stage.revealExtras = nil :: ((any, any, {() -> ()}, (GuiObject, number) -> ()) -> ())? -- colour + pattern chips instead of the colour dots
Stage.onEnds = nil :: ((any, GuiObject, {() -> ()}) -> ())? -- the last egg's PLAY AGAIN / HOME row was placed
Stage.onRestore = nil :: (() -> ())? -- the stage closes
function Stage.parts(): any return stageParts end

local function painted(o: Instance, stop: Instance): GuiObject?
    local node: Instance? = o
    while node and node ~= stop do
        if node:IsA("GuiObject") and node.BackgroundTransparency < .9 then return node end
        node = node.Parent
    end
    return nil
end
-- One object to the style: dark plates -> cream + ink outline, dark buttons -> grey, light text on cream -> ink.
local function style(o: Instance, stop: Instance)
    if not o:IsA("GuiObject") then return end
    -- the old window's flat backdrop behind the egg (HatchFx) would read as a pale box on the stage
    -- (and its podium pill: the pedestal picture replaces it; on a short window it sat beside the pedestal, BD-1211)
    if (o.Name == "Backdrop" or string.match(o.Name, "^Podium%d")) and o.Parent and o.Parent.Name == "HatchFxBack" then
        o.Visible = false -- the hatch tweens its transparency, never Visible; keep it hidden if something shows it again
        if not o:GetAttribute("StageHidden") then
            o:SetAttribute("StageHidden", true)
            o:GetPropertyChangedSignal("Visible"):Connect(function() if o.Visible and state then o.Visible = false end end)
        end
        return
    end
    if o.BackgroundTransparency < .9 and Stage.isDark(o.BackgroundColor3) and o.AbsoluteSize.X < 700 then
        local isButton = o:IsA("TextButton") or o:IsA("ImageButton")
        o.BackgroundColor3 = if isButton then Stage.Grey else Stage.Cream
        if isButton and o:IsA("TextButton") then
            -- the game's gloss kit button (the same face Theme.decorate gives every menu button)
            local ok, Skin = pcall(require, Shared:WaitForChild("ToyboxSkin"))
            if ok and Skin.ready("button") then
                o.Text = string.upper(o.Text)
                pcall(Skin.button, o, o:FindFirstChildOfClass("UIStroke"))
                return
            end
        end
        for _, old in o:GetChildren() do if old:IsA("UIStroke") and old.ApplyStrokeMode == Enum.ApplyStrokeMode.Border then old:Destroy() end end
        Chip.apply(o, o.BackgroundColor3, Stage.Ink)
    end
    if o:IsA("TextButton") and (o.Name == "ResetView" or o.Text == "RESET") then o.Visible = false return end
    -- the "Drag to turn" hint floats outside the stage (docs/240 R8); dragging still turns the dino
    if o:IsA("TextLabel") and o.Text == "Drag to turn" then
        local plate = o.Parent
        if plate and plate:IsA("GuiObject") and plate.AbsoluteSize.X < 260 and plate.Name ~= "HatchUiLayer" then plate.Visible = false else o.Visible = false end
        return
    end
    if (o:IsA("TextLabel") or o:IsA("TextButton")) and luminance(o.TextColor3) > .55 then
        local plate = painted(o, stop)
        if plate and (plate.BackgroundColor3 == Stage.Cream or plate.BackgroundColor3 == Stage.Grey) then
            o.TextColor3 = Stage.Ink
            o.TextStrokeTransparency = 1
            for _, child in o:GetChildren() do if child:IsA("UIStroke") and child.ApplyStrokeMode == Enum.ApplyStrokeMode.Contextual then child.Enabled = false end end
        end
    end
end
function Stage.styleTree(root: Instance)
    style(root, root)
    for _, o in root:GetDescendants() do style(o, root) end
end

export type Parts = {gui: ScreenGui, shade: GuiObject, panel: GuiObject, header: GuiObject, heading: GuiObject, body: GuiObject, reduceMotion: boolean}
function Stage.apply(p: Parts)
    Stage.restore()
    local restore: {() -> ()} = {}
    local conns: {RBXScriptConnection} = {}
    local function keep(object: Instance, property: string, value: any)
        local ok, before = pcall(function() return (object :: any)[property] end)
        if not ok then return end -- the object has no such property (a stroke has no Visible)
        table.insert(restore, function() pcall(function() (object :: any)[property] = before end) end)
        pcall(function() (object :: any)[property] = value end)
    end
    -- chrome off: panel plate + its Toybox pictures (stud body, frame), header strip and its title (the X keeps its own picture)
    keep(p.panel, "BackgroundTransparency", 1)
    -- no clip box: the glow and rays of a reveal spill softly onto the stage instead of ending at the old window's edge
    keep(p.panel, "ClipsDescendants", false)
    keep(p.body, "ClipsDescendants", false)
    for _, name in {"HatchFxBack", "HatchFxFront"} do
        local layerFx = p.panel:FindFirstChild(name)
        if layerFx then keep(layerFx, "ClipsDescendants", false) end
    end
    keep(p.header, "BackgroundTransparency", 1)
    keep(p.heading, "Visible", false)
    for _, child in p.panel:GetChildren() do
        if child:IsA("ImageLabel") or child:IsA("UIStroke") then keep(child, "Visible", false) keep(child, "Enabled", false) end
    end
    for _, child in p.header:GetChildren() do
        if child:IsA("ImageLabel") or child:IsA("UIStroke") then keep(child, "Visible", false) keep(child, "Enabled", false) end
    end
    -- full screen (owner 2026-11-16 "there is a border top"): the veil and the sunburst sit in their own ScreenGui that ignores the
    -- Roblox top-bar inset, drawn just under the game UI; the scrim itself becomes clear (set after Bootstrap's open tween)
    local backdrop = Instance.new("ScreenGui")
    backdrop.Name, backdrop.IgnoreGuiInset, backdrop.ResetOnSpawn, backdrop.DisplayOrder = "HatchStageBackdrop", true, false, p.gui.DisplayOrder - 1
    pcall(function() (backdrop :: any).ScreenInsets = Enum.ScreenInsets.None end)
    local veil = Instance.new("Frame")
    veil.Name, veil.Size, veil.BorderSizePixel = "Veil", UDim2.fromScale(1, 1), 0
    veil.BackgroundColor3, veil.BackgroundTransparency = Color3.new(0, 0, 0), Stage.Veil
    veil.Parent = backdrop
    backdrop.Parent = p.gui.Parent
    table.insert(restore, function() backdrop:Destroy() end)
    task.delay(.2, function()
        if not (state and state.restore == restore) then return end
        keep(p.shade, "BackgroundTransparency", 1)
        table.insert(conns, p.shade:GetPropertyChangedSignal("BackgroundTransparency"):Connect(function()
            if state and state.conns == conns and p.shade.BackgroundTransparency < 1 then p.shade.BackgroundTransparency = 1 end
        end))
    end)
    -- a soft warm glow behind the egg (real art: the uploaded neutral radial glow plate); it breathes gently, still with Reduce Motion
    local rays = Instance.new("ImageLabel")
    rays.Name, rays.BackgroundTransparency, rays.Image = "HatchStageRays", 1, Effects.Requested.glowPlate.id
    rays.AnchorPoint, rays.Position, rays.Size = Vector2.new(.5, .5), UDim2.fromScale(.5, .46), UDim2.fromOffset(760, 760)
    rays.ImageColor3, rays.ImageTransparency, rays.ZIndex = Color3.fromRGB(255, 244, 200), .35, 1 -- behind the egg and the dino, never over them
    rays.Parent = p.panel
    table.insert(restore, function() rays:Destroy() end)
    local breathe: Tween? = nil
    if not p.reduceMotion then
        breathe = TweenService:Create(rays, TweenInfo.new(2.4, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {ImageTransparency = .55})
        breathe:Play()
        table.insert(restore, function() if breathe then breathe:Cancel() end end)
    end
    -- BD-1212 full screen: the Blender sunburst fills the whole screen behind the egg (a child of the scrim, under the panel), turning slowly
    local sun = Instance.new("ImageLabel")
    sun.Name, sun.BackgroundTransparency, sun.Image = "HatchStageSunburst", 1, Stage.RaysImage
    sun.AnchorPoint, sun.Position, sun.SizeConstraint = Vector2.new(.5, .5), UDim2.fromScale(.5, .47), Enum.SizeConstraint.RelativeXX
    sun.Size, sun.ZIndex, sun.ImageColor3, sun.ImageTransparency = UDim2.fromScale(1.5, 1.5), 2, Color3.new(1, 1, 1), .45
    sun.Parent = backdrop
    table.insert(restore, function() sun:Destroy() end)
    -- degrees per second (one turn a minute); the Legendary / Mythic build-up spins it up (BD-1211). Reduce Motion: it stands still.
    local spin = {speed = 6}
    if not p.reduceMotion then
        local turn = RunService.RenderStepped:Connect(function(dt) sun.Rotation = (sun.Rotation + spin.speed * dt) % 360 end)
        table.insert(restore, function() turn:Disconnect() end)
    end
    -- the HUD steps aside (only the crystal counter stays, docs/240 s2 board 2): every other top-level UI piece hides while the stage is up
    for _, child in p.gui:GetChildren() do
        if child:IsA("GuiObject") and child.Visible and not Stage.KeepOnStage[child.Name] and child ~= p.shade then
            local crystals = false
            for _, d in child:GetDescendants() do
                if d:IsA("TextLabel") and string.find(d.Text, "Crystals", 1, true) then crystals = true break end
            end
            if not crystals or Stage.HideCrystals then
                keep(child, "Visible", false)
                -- the HUD refreshes some pieces every frame (the size bar): keep them hidden while the stage is up
                table.insert(conns, child:GetPropertyChangedSignal("Visible"):Connect(function()
                    if child.Visible and state and state.conns == conns then child.Visible = false end
                end))
            end
        end
    end
    -- no floating X on the stage (the way out is SKIP / a tap outside, owner 2026-11-16 "buttons overlapping")
    for _, b in p.header:GetDescendants() do
        if b:IsA("GuiButton") then keep(b, "Visible", false) end
    end
    stageParts = {gui = p.gui, shade = p.shade, panel = p.panel, body = p.body, sun = sun, glow = rays, veil = veil, reduceMotion = p.reduceMotion, restore = restore,
        spin = spin, breathe = breathe, builtUp = false, charge = 1}
    Stage.mirrorBuckets(stageParts, keep, conns)
    -- "Egg N of M": the counter HatchSequence puts in the header becomes a cream chip at the top centre of the stage
    local function chipCounter(o: Instance)
        if o.Name ~= "EggCounter" or not o:IsA("TextLabel") then return end
        o.AnchorPoint, o.Position, o.Size = Vector2.new(.5, 0), UDim2.new(.5, 0, 0, 8), UDim2.fromOffset(170, 36)
        o.TextXAlignment, o.TextSize = Enum.TextXAlignment.Center, 22
        o.BackgroundColor3, o.BackgroundTransparency = Stage.Cream, 0
        o.TextColor3, o.TextStrokeTransparency = Stage.Ink, 1
        Chip.apply(o, Stage.Cream, Stage.Ink)
    end
    -- everything the hatch builds now and later (buckets, labels, the end buttons, the Skip layer) follows the style
    local layer = p.gui:FindFirstChild("HatchUiLayer")
    -- the whole panel: body, header strip and the HatchFx layers (the colour and pattern chips live there)
    for _, root in {p.panel, layer} do
        if root then
            Stage.styleTree(root)
            for _, o in root:GetDescendants() do chipCounter(o) end
            if root == p.panel then
                table.insert(conns, root.ChildAdded:Connect(function(o)
                    if o:IsA("GuiObject") and (o.Name == "HatchFxBack" or o.Name == "HatchFxFront") then o.ClipsDescendants = false end
                end))
            end
            table.insert(conns, root.DescendantAdded:Connect(function(o)
                task.defer(function()
                    if not o.Parent then return end
                    style(o, root)
                    for _, d in o:GetDescendants() do style(d, root) end
                    chipCounter(o)
                end)
            end))
        end
    end
    do -- a new HatchUiLayer (every egg of a batch builds its own) follows the style too
        table.insert(conns, p.gui.ChildAdded:Connect(function(o)
            if o.Name == "HatchUiLayer" then
                task.defer(function() Stage.styleTree(o) end)
                table.insert(conns, o.DescendantAdded:Connect(function(d) task.defer(function() if d.Parent then style(d, o) end end) end))
            end
        end))
    end
    state = {restore = restore, conns = conns}
end

-- BD-1211: the two generated 3D paint buckets (ReplicatedStorage.HatchStageBuckets, ImportedResources.loadHatchBuckets, docs/77
-- hatch_bucket_*) replace the 2D bucket pictures. Each one follows its PaintBucket group every frame (place, tip, fade), so it stays in time
-- with the sequence and the paint flipbooks, and its paint takes the colour the sequence gives that bucket. Bucket 1 is the tin pail, bucket 2
-- the paint can (the two pours look different). No 3D bucket loaded = the 2D picture stays.
Stage.BucketModels = {"pail", "can"}
Stage.BucketView = {side = 2.3, fov = 30, lift = .55, yaw = {math.rad(-30), math.rad(30)}} -- view side in bucket sizes; camera a little above
local function bucketView(template: BasePart, s: any, i: number): any
    local frame = Instance.new("ViewportFrame")
    frame.Name, frame.BackgroundTransparency, frame.AnchorPoint = "HatchStageBucket" .. i, 1, Vector2.new(.5, .5)
    frame.ZIndex, frame.Visible = s.panel.ZIndex + 12, false
    frame.Ambient, frame.LightColor, frame.LightDirection = Color3.fromRGB(170, 170, 170), Color3.new(1, 1, 1), Vector3.new(-.3, -1, -.5)
    local world = Instance.new("WorldModel")
    world.Parent = frame
    local part = template:Clone()
    part.Parent = world
    local radius = part.Size.Magnitude / 2
    local base = CFrame.Angles(0, Stage.BucketView.yaw[i] or 0, 0)
    part.CFrame = base
    local camera = Instance.new("Camera")
    camera.FieldOfView = Stage.BucketView.fov
    local distance = radius / math.tan(math.rad(Stage.BucketView.fov / 2)) * 1.05
    camera.CFrame = CFrame.lookAt(Vector3.new(0, distance * Stage.BucketView.lift, distance), Vector3.zero)
    camera.Parent = frame
    frame.CurrentCamera = camera
    frame.Parent = s.shade
    table.insert(s.restore, function() frame:Destroy() end)
    return {frame = frame, part = part, base = base, axis = camera.CFrame.LookVector}
end
function Stage.mirrorBuckets(s: any, keep: (Instance, string, any) -> (), conns: {RBXScriptConnection})
    local folder = game:GetService("ReplicatedStorage"):FindFirstChild("HatchStageBuckets")
    if not folder then return end
    local views = {}
    table.insert(conns, RunService.RenderStepped:Connect(function()
        local front = s.panel:FindFirstChild("HatchFxFront")
        for i = 1, 2 do
            local group = front and front:FindFirstChild("PaintBucket" .. i)
            local template = folder:FindFirstChild(Stage.BucketModels[i])
            if not (group and group:IsA("CanvasGroup") and template and template:IsA("BasePart")) then continue end
            local v = views[i]
            if not v then
                v = bucketView(template, s, i)
                views[i] = v
                for _, d in group:GetChildren() do if d:IsA("GuiObject") then keep(d, "Visible", false) end end -- the 2D picture steps aside
            end
            local show = group.Visible and group.GroupTransparency < .99
            v.frame.Visible = show
            if show then
                local c = group.AbsolutePosition + group.AbsoluteSize / 2 - s.shade.AbsolutePosition
                local side = group.AbsoluteSize.X * Stage.BucketView.side
                v.frame.Position, v.frame.Size, v.frame.ImageTransparency = UDim2.fromOffset(c.X, c.Y), UDim2.fromOffset(side, side), group.GroupTransparency
                -- the same tip as the picture: a turn about the camera's line of sight (screen clockwise = positive Rotation)
                v.part.CFrame = CFrame.fromAxisAngle(v.axis, math.rad(group.Rotation)) * v.base
                local cap = group:FindFirstChild("BucketPaintCap", true)
                if cap and cap:IsA("GuiObject") then v.part.Color = cap.BackgroundColor3 end
            end
        end
    end))
end
-- BD-1211 Legendary / Mythic build-up before the burst (calm, docs/87): the stage dims to a warm dark, the sunburst turns gold and spins up,
-- a gold glow swells behind the egg and the egg's shake builds a little more. Reduce Motion: only the dim and the gold (no spin, no pulse,
-- no extra shake). The watcher calls it when the rattle starts; HatchSequence puts the rarity on the body (HatchStageRarity).
Stage.BuildUp = {ramp = 1.8, veil = .38, veilColor = Color3.fromRGB(28, 16, 4), sun = .16, glow = 1080, spinTo = 230,
    gold = Color3.fromRGB(255, 205, 70), mythic = Color3.fromRGB(255, 110, 130), shake = 1.7}
function Stage.buildUp()
    local s = stageParts
    if not s or not state or s.builtUp then return end
    local rank = s.body:GetAttribute("HatchStageRarity")
    if type(rank) ~= "number" or rank < 5 then return end
    s.builtUp = true
    local b = Stage.BuildUp
    local tint = if rank >= 6 then b.mythic else b.gold
    if s.breathe then s.breathe:Cancel() end
    s.buildTweens = {}
    local function to(o: Instance, props: {[string]: any})
        if s.reduceMotion then for k, v in props do (o :: any)[k] = v end return end
        local tween = TweenService:Create(o, TweenInfo.new(b.ramp, Enum.EasingStyle.Sine, Enum.EasingDirection.Out), props)
        table.insert(s.buildTweens, tween) -- the burst stops them (it sets its own veil and rays)
        tween:Play()
    end
    to(s.veil, {BackgroundColor3 = b.veilColor, BackgroundTransparency = b.veil})
    to(s.sun, {ImageColor3 = tint, ImageTransparency = b.sun})
    s.glow.ImageColor3 = tint
    to(s.glow, {Size = UDim2.fromOffset(b.glow, b.glow), ImageTransparency = .05})
    if s.reduceMotion then return end
    s.charge = b.shake
    task.spawn(function()
        local t = 0
        while stageParts == s and s.builtUp do
            t += task.wait()
            s.spin.speed = 6 + (b.spinTo - 6) * math.min(1, t / b.ramp) ^ 2
        end
    end)
end
-- The dino is the star (target: about half the screen tall, reveal-target-chatgpt.png). The sequence tweens its own UIScale on the view, so
-- the stage grows the view's SIZE (in body pixels, through the body's fit scale). Returns the view's centre and height on the screen.
-- The reveal stack in shares of the screen height (target picture: ribbon at the top, dino, pedestal, name plate, NEXT at the bottom).
Stage.Layout = {dinoY = .39, dinoYBig = .37, dinoH = .5, dinoHBig = .54, pedestalY = .655, plateY = .755, nextY = .885}
function Stage.growDino(s: any, rank: number): (Vector2?, number?)
    local v = s.body:FindFirstChild("DinosaurPreview", true)
    if not (v and v:IsA("GuiObject")) then return nil, nil end
    local fit = s.body:FindFirstChild("HatchBodyFit")
    local k = if fit and fit:IsA("UIScale") then fit.Scale else 1
    local L = Stage.Layout
    local want = s.shade.AbsoluteSize.Y * (if rank >= 5 then L.dinoHBig else L.dinoH)
    if v.AnchorPoint == Vector2.zero then -- grow around the middle, not the top-left corner
        v.AnchorPoint = Vector2.new(.5, .5)
        v.Position = v.Position + UDim2.new(v.Size.X.Scale / 2, v.Size.X.Offset / 2, v.Size.Y.Scale / 2, v.Size.Y.Offset / 2)
    end
    -- centre the view on the stage's dino line (the UIScale the sequence tweens scales around this centre)
    local centre = v.AbsolutePosition + v.AbsoluteSize / 2
    local goal = s.shade.AbsolutePosition + Vector2.new(s.shade.AbsoluteSize.X / 2, s.shade.AbsoluteSize.Y * (if rank >= 5 then L.dinoYBig else L.dinoY))
    local move = (goal - centre) / k
    if move.Magnitude > 1 then v.Position = v.Position + UDim2.fromOffset(move.X, move.Y) end
    local h = math.max(1, v.Size.Y.Offset)
    if h * k < want - 2 then
        local before = v.Size
        local ratio = want / k / h
        v.Size = UDim2.fromOffset(v.Size.X.Offset * ratio, want / k)
        table.insert(s.restore, function() if v.Parent and v.Size ~= before then v.Size = before end end)
    end
    return goal - s.shade.AbsolutePosition, want
end

-- BD-1212: Bootstrap hands over what the egg holds as soon as the server answer arrives (before the burst).
-- info = {rarity = 1..6, color = Color3, failed, nameLabel, oddsLabel, detailLabel}
function Stage.prepare(info: any)
    pending = info
end
-- Kid words for a chance (docs/240 R6: no "0.004%"): 1 % and up stays a whole or one-decimal percent, rarer becomes "1 in 25,000 eggs".
function Stage.chanceWords(pct: number): string
    if pct >= 10 then return string.format("%d%% of eggs", math.floor(pct + .5)) end
    if pct >= 1 then return (string.gsub(string.format("%.1f", pct), "%.0$", "")) .. "% of eggs" end
    local n = 100 / math.max(pct, 1e-9)
    local digits = math.floor(math.log10(n))
    local unit = 10 ^ math.max(0, digits - 1) -- two significant digits: 24,800 -> 25,000
    n = math.floor(n / unit + .5) * unit
    local text = tostring(math.floor(n))
    while true do
        local k
        text, k = string.gsub(text, "^(%d+)(%d%d%d)", "%1,%2")
        if k == 0 then break end
    end
    return "1 in " .. text .. " eggs"
end
local function plain(text: string): string
    return (string.gsub(string.gsub(text or "", "<[^>]->", ""), "%s+", " "))
end
local function chip(parent: Instance, text: string, order: number): TextLabel
    local c = Instance.new("TextLabel")
    c.AutomaticSize, c.Size = Enum.AutomaticSize.X, UDim2.fromOffset(0, 40)
    c.BackgroundColor3, c.BackgroundTransparency = Stage.Cream, 0
    c.Font, c.TextSize, c.TextColor3, c.Text, c.LayoutOrder = Enum.Font.FredokaOne, 24, Stage.Ink, text, order
    local pad = Instance.new("UIPadding")
    pad.PaddingLeft, pad.PaddingRight = UDim.new(0, 14), UDim.new(0, 14)
    pad.Parent = c
    Chip.apply(c, Stage.Cream, Stage.Ink)
    c.Parent = parent
    return c
end
-- The burst: big outlined rarity word at the top of the screen, sunburst and veil in the rarity's strength, cream chips under the dino
-- (name, colour and pattern, the chance), confetti for Rare and up. Called from HatchSequence's onReveal.
function Stage.reveal()
    local s, info = stageParts, pending
    if not s or not info or not state then return end
    pcall(Stage.crackBurst)
    local rank = math.clamp(info.rarity or 1, 1, #Stage.Ladder)
    local tier = Stage.Ladder[rank]
    -- everything this reveal adds is undone by the next egg (Stage.nextEgg) or when the stage closes
    if s.reveal then Stage.clearReveal(s) end
    local restore: {() -> ()} = {}
    s.reveal, s.revealConns = restore, {}
    table.insert(s.restore, function() Stage.clearReveal(s) end)
    local color: Color3 = if info.failed then Color3.fromRGB(220, 220, 220) else (info.color or Color3.new(1, 1, 1))
    s.sun.ImageColor3 = if rank <= 1 then Color3.new(1, 1, 1) else color:Lerp(Color3.new(1, 1, 1), .15)
    s.sun.ImageTransparency = tier.rays
    s.glow.ImageColor3 = color:Lerp(Color3.new(1, 1, 1), .5)
    s.veil.BackgroundTransparency = tier.veil
    if rank >= 5 then s.veil.BackgroundColor3 = Color3.fromRGB(60, 34, 0) end
    -- keep something hidden for the rest of this reveal even if the sequence shows it again (it fades labels in after the burst)
    -- forever = for as long as the stage is up (the "You hatched a ..." plate is the ribbon's job on every egg of a batch)
    local function hold(o: GuiObject, forever: boolean?)
        o.Visible = false
        table.insert(if forever then state.conns else s.revealConns, o:GetPropertyChangedSignal("Visible"):Connect(function() if o.Visible and stageParts == s then o.Visible = false end end))
    end
    -- the big word replaces the "You hatched a ..." banner and the "Egg N of M" chip while the dino is shown
    local function scan()
        if stageParts ~= s then return end
        for _, d in s.panel:GetDescendants() do
            if d:IsA("TextLabel") and d.Visible and (string.find(d.Text, "You hatched a", 1, true) or d.Name == "EggCounter") then
                local plate = d.Parent
                hold(if plate and plate:IsA("Frame") and plate ~= s.panel and plate ~= s.body and plate.AbsoluteSize.X < 700 then plate else d, d.Name ~= "EggCounter")
            end
        end
    end
    scan()
    task.delay(.4, scan) -- the banner arrives a moment after the burst
    task.delay(1.2, scan)
    -- BD-1212 reveal on the owner-approved target (docs/evidence/2026-11-16-hatch-fullscreen/reveal-target-chatgpt.png): a glossy ribbon banner
    -- tinted in the rarity colour with the outlined rarity word, the dino on a glowing pedestal, a cream name plate with the colour dots and a
    -- NEW! sticker, one big glossy NEXT where the tap goes on, a small SKIP. Pieces: ChatGPT art cut by tools/ui_piece_cut.py (docs/77).
    local screen = s.shade.AbsoluteSize
    local base = s.shade.AbsolutePosition
    local function art(name: string, image: string, size: Vector2, center: Vector2, z: number, tint: Color3?): ImageLabel
        local l = Instance.new("ImageLabel")
        l.Name, l.BackgroundTransparency, l.Image, l.ScaleType = name, 1, image, Enum.ScaleType.Fit
        l.AnchorPoint, l.Size, l.Position, l.ZIndex = Vector2.new(.5, .5), UDim2.fromOffset(size.X, size.Y), UDim2.fromOffset(center.X, center.Y), z
        if tint then l.ImageColor3 = tint end
        l.Parent = s.shade
        table.insert(restore, function() l:Destroy() end)
        return l
    end
    local function pop(o: GuiObject, delay: number)
        if s.reduceMotion then return end
        local sc = Instance.new("UIScale")
        sc.Scale = 0
        sc.Parent = o
        task.delay(delay, function()
            if sc.Parent then TweenService:Create(sc, TweenInfo.new(.38, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play() end
        end)
    end
    local bannerTint = if info.failed then Color3.fromRGB(200, 200, 200) elseif rank <= 1 then Color3.fromRGB(255, 205, 70) else color:Lerp(Color3.new(1, 1, 1), .12)
    -- sizes follow the shorter side too, so the stack (ribbon, dino, pedestal, plate, NEXT) fits a short phone-landscape screen
    local fitY = math.min(1, screen.Y / 793)
    local bw = math.min(screen.X * .3, 520 * fitY)
    local banner = art("HatchStageBanner", Stage.Art.ribbon, Vector2.new(bw, bw * 167 / 444), Vector2.new(screen.X / 2, bw * 167 / 444 / 2 + 6), s.panel.ZIndex + 30, bannerTint)
    banner.Rotation = tier.tilt * .5
    local word = Instance.new("TextLabel")
    word.Name, word.BackgroundTransparency = "HatchStageWord", 1
    word.AnchorPoint, word.Position, word.Size = Vector2.new(.5, .5), UDim2.fromScale(.5, .4), UDim2.fromScale(.66, .5)
    word.Font, word.TextScaled, word.Text = Enum.Font.FredokaOne, true, if info.failed then "OOPS!" else string.gsub(tier.word, "!", "")
    word.TextColor3, word.ZIndex = Color3.new(1, 1, 1), banner.ZIndex + 1
    local outline = Instance.new("UIStroke")
    outline.Color, outline.Thickness = Stage.Ink, 5
    outline.Parent = word
    word.Parent = banner
    pop(banner, 0)
    -- the dino is the star: its view grows to about half the screen (Stage.growDino); the Legendary build-up calms down into the reveal
    for _, tween in s.buildTweens or {} do tween:Cancel() end
    s.buildTweens = nil
    s.builtUp = false
    s.charge = 1
    if not s.reduceMotion then s.spin.speed = if rank >= 5 then 14 else 6 end
    s.glow.Size, s.glow.ImageTransparency = UDim2.fromOffset(760, 760), .35
    -- the dino stands on a glowing pedestal in the rarity colour (behind the panel, so behind the dino)
    local grownC = Stage.growDino(s, rank)
    local vc = grownC or Vector2.new(screen.X / 2, screen.Y * Stage.Layout.dinoY)
    local pw = math.min(screen.X * .2, 340 * fitY)
    local pedestalY = screen.Y * Stage.Layout.pedestalY -- under the feet
    local pedestal = art("HatchStagePedestal", Stage.Art.pedestal, Vector2.new(pw, pw * 212 / 429), Vector2.new(vc.X, pedestalY), s.panel.ZIndex - 1,
        if rank <= 1 then Color3.fromRGB(150, 225, 255) else color:Lerp(Color3.new(1, 1, 1), .35))
    pop(pedestal, .05)
    for _, l in {info.nameLabel, info.oddsLabel, info.detailLabel} do if l then hold(l) end end
    for _, plate in {s.body:FindFirstChild("RarityPill"), s.body:FindFirstChild("NameShine"), s.body:FindFirstChild("ClassBadge")} do
        if plate and plate:IsA("GuiObject") then hold(plate) end
    end
    -- "New pattern!" / "New colour!" ribbons become one NEW! sticker on the name plate
    local newFind = false
    for _, d in s.panel:GetDescendants() do
        if d:IsA("TextLabel") and (string.find(d.Text, "New pattern", 1, true) or string.find(d.Text, "New colour", 1, true) or string.find(d.Text, "New mutation", 1, true)) then
            newFind = true
            local plate = d.Parent
            hold(if plate and plate:IsA("GuiObject") and plate ~= s.panel and plate ~= s.body and plate.AbsoluteSize.X < 500 then plate else d)
        end
    end
    if not info.failed then
        local name = plain(if info.nameLabel then info.nameLabel.Text else "")
        local plateW = math.min(screen.X * .2, 300 * fitY)
        local plateH = plateW * 137 / 439
        local plateC = Vector2.new(vc.X + (if Stage.revealExtras then 0 else 26), screen.Y * Stage.Layout.plateY)
        local plate = art("HatchStagePlate", Stage.Art.plate, Vector2.new(plateW, plateH), plateC, s.panel.ZIndex + 31)
        local nameLabel = Instance.new("TextLabel")
        nameLabel.BackgroundTransparency, nameLabel.AnchorPoint = 1, Vector2.new(.5, .5)
        nameLabel.Position, nameLabel.Size, nameLabel.ZIndex = UDim2.fromScale(.5, .47), UDim2.fromScale(.8, .62), plate.ZIndex + 1
        nameLabel.Font, nameLabel.TextScaled, nameLabel.Text, nameLabel.TextColor3 = Enum.Font.FredokaOne, true, name, Stage.Ink
        local ns = Instance.new("UIStroke")
        ns.Color, ns.Thickness = Color3.new(1, 1, 1), 2.5
        ns.Parent = nameLabel
        nameLabel.Parent = plate
        pop(plate, .12)
        -- the egg's colours as dots left of the plate (kid-minimal: no colour or pattern words)
        local dot = plateH * .62
        if Stage.revealExtras then pcall(Stage.revealExtras, s, {x = plateC.X, y = plateC.Y, w = plateW, h = plateH}, restore, pop) end -- BD-1288: chips instead
        for k, c in (if Stage.revealExtras then {} else Stage.lastColors) do
            local d = Instance.new("Frame")
            d.Name, d.AnchorPoint, d.ZIndex = "ColourDot" .. k, Vector2.new(.5, .5), plate.ZIndex
            d.Size = UDim2.fromOffset(dot, dot)
            d.Position = UDim2.fromOffset(plateC.X - plateW / 2 - dot * (#Stage.lastColors - k + .7) - 6 * (#Stage.lastColors - k), plateC.Y)
            Chip.apply(d, c, Stage.Ink)
            d.Parent = s.shade
            table.insert(restore, function() d:Destroy() end)
            pop(d, .18 + k * .05)
        end
        if not newFind and Stage.isNew then newFind = Stage.isNew() end -- BD-1288: a species new to the player too
        if newFind then
            local sticker = art("HatchStageNew", Stage.Art.new, Vector2.new(plateH * 1.25, plateH * 1.17), Vector2.new(plateC.X + plateW / 2 + plateH * .25, plateC.Y - plateH * .25), plate.ZIndex + 2)
            sticker.Rotation = 12
            pop(sticker, .3)
        end
    end
    -- one big glossy NEXT exactly where "Tap for next egg" was (a picture only: the tap goes through to the hatch's own tap catcher)
    local nextShown, endMoved = false, false
    local function placeNext()
    if stageParts ~= s then return end
    -- SKIP is one short word, and the dino-view RESET button never covers the stage (both are rebuilt after the burst)
    for _, b in s.gui:GetDescendants() do
        if (b:IsA("TextButton") or b:IsA("TextLabel")) and string.upper(b.Text) == "SKIP THE REST" then b.Text = "SKIP" end
        if b:IsA("TextButton") and (b.Name == "ResetView" or b.Text == "RESET") and b.Visible then hold(b) end
    end
    -- the last egg of a batch shows PLAY AGAIN / HOME instead of the tap hint: they move under the name plate (where NEXT goes)
    local ends = s.body:FindFirstChild("EndButtons", true)
    if not endMoved and ends and ends:IsA("GuiObject") and ends.Visible and ends.AbsoluteSize.X > 0 then
        endMoved = true
        local fit = s.body:FindFirstChild("HatchBodyFit")
        local k = if fit and fit:IsA("UIScale") then fit.Scale else 1
        local goal = s.shade.AbsolutePosition + Vector2.new(screen.X / 2, screen.Y * Stage.Layout.nextY)
        local move = (goal - (ends.AbsolutePosition + ends.AbsoluteSize / 2)) / k
        local before = ends.Position
        ends.Position = ends.Position + UDim2.fromOffset(move.X, move.Y)
        table.insert(restore, function() if ends.Parent then ends.Position = before end end)
        -- the same glossy kit face as NEXT (green PLAY AGAIN, grey HOME)
        local ok, Skin = pcall(require, Shared:WaitForChild("ToyboxSkin"))
        if ok and Skin.ready("button") then
            for _, b in ends:GetChildren() do
                if b:IsA("TextButton") then
                    if not Stage.isGreen(b.BackgroundColor3) then b.BackgroundColor3 = Stage.Grey end
                    b.Text, b.TextColor3 = string.upper(b.Text), Color3.new(1, 1, 1) -- white word with the kit's ink drop, like NEXT
                    pcall(Skin.button, b, b:FindFirstChildOfClass("UIStroke"))
                end
            end
        end
        if Stage.onEnds then pcall(Stage.onEnds, s, ends, restore) end -- BD-1288: the storyboard's NEXT -> BEST FIND! summary
    end
    if nextShown then return end
    local hint = s.body:FindFirstChild("TapHint", true) :: TextLabel?
    if hint and hint.Visible and hint.Text ~= "" then
        nextShown = true
        local hc = Vector2.new(screen.X / 2, screen.Y * Stage.Layout.nextY) -- under the name plate (the old hint sat on it)
        hold(hint)
        local ok, Skin = pcall(require, Shared:WaitForChild("ToyboxSkin"))
        local next = Instance.new("TextButton")
        next.Name, next.Text, next.AutoButtonColor = "HatchStageNext", "NEXT", false
        next.AnchorPoint, next.Size, next.Position = Vector2.new(.5, .5), UDim2.fromOffset(250 * fitY, 66 * fitY), UDim2.fromOffset(hc.X, hc.Y)
        next.BackgroundColor3, next.Font, next.TextSize, next.TextColor3, next.ZIndex = Color3.fromRGB(88, 200, 64), Enum.Font.FredokaOne, math.max(20, math.floor(34 * fitY)), Color3.new(1, 1, 1), s.panel.ZIndex + 32
        next.Parent = s.shade
        next.Activated:Connect(function()
            -- the same tap as on the egg (HatchSequence's StageTap), never the backdrop's close
            local catcher = s.gui:FindFirstChild("HatchTapCatcher")
            local tap = catcher and catcher:FindFirstChild("StageTap")
            if tap and tap:IsA("BindableEvent") then tap:Fire() end
        end)
        if ok and Skin.ready("button") then pcall(Skin.button, next, nil) end
        table.insert(restore, function() next:Destroy() end)
        pop(next, .05)
    end
    end
    task.spawn(function() -- the tap hint (and the rebuilt SKIP / RESET) can arrive seconds after the burst
        for _ = 1, 16 do
            if stageParts ~= s then return end
            placeNext()
            task.wait(.5)
        end
    end)
    -- SKIP is short (one word)
    for _, b in s.gui:GetDescendants() do
        if (b:IsA("TextButton") or b:IsA("TextLabel")) and string.upper(b.Text) == "SKIP THE REST" then b.Text = "SKIP" end
    end
    -- the old name line's class icon (left of the name) goes with the old lines
    if info.nameLabel then
        local y = info.nameLabel.AbsolutePosition.Y
        for _, d in s.body:GetChildren() do
            if d:IsA("ImageLabel") and math.abs(d.AbsolutePosition.Y + d.AbsoluteSize.Y / 2 - (y + info.nameLabel.AbsoluteSize.Y / 2)) < 40 then hold(d) end
        end
    end
    if tier.confetti > 0 and not s.reduceMotion then
        local colours = {Color3.fromRGB(255, 107, 107), Color3.fromRGB(79, 195, 247), Color3.fromRGB(156, 204, 101), Color3.fromRGB(255, 213, 79), Color3.fromRGB(186, 104, 200)}
        local sheet = Effects.Sheets and Effects.Sheets.starFour
        for i = 1, tier.confetti do
            local bit = Instance.new("ImageLabel")
            bit.BackgroundTransparency, bit.Image = 1, Effects.Requested.starFour.id
            if sheet then
                local cell = sheet.size / sheet.grid
                bit.ImageRectSize, bit.ImageRectOffset = Vector2.new(cell, cell), Vector2.new(cell * 2, cell)
            end
            bit.ImageColor3, bit.ZIndex = colours[(i - 1) % #colours + 1], s.panel.ZIndex + 20
            bit.Size, bit.AnchorPoint = UDim2.fromOffset(28, 28), Vector2.new(.5, .5)
            local x = .08 + .84 * ((i * 37) % 100) / 100
            bit.Position = UDim2.fromScale(x, -.05)
            bit.Parent = s.shade
            local fall = TweenService:Create(bit, TweenInfo.new(2.6 + (i % 5) * .35, Enum.EasingStyle.Sine, Enum.EasingDirection.In),
                {Position = UDim2.fromScale(x + ((i % 3) - 1) * .05, 1.05), Rotation = (i % 2 * 2 - 1) * 240})
            task.delay((i % 7) * .08, function() if bit.Parent then fall:Play() end end)
            fall.Completed:Connect(function() bit:Destroy() end)
            table.insert(restore, function() if bit.Parent then bit:Destroy() end end)
        end
    end
end
-- BD-1212 board 5: the end of a batch ("You hatched 5 dinos!") on the same stage: no window, the title as the big outlined word,
-- the cards and buttons as the screen builds them (styled by apply()).
function Stage.summary(p: Parts)
    Stage.apply(p)
    local s = stageParts
    if not s or not state then return end
    local word = Instance.new("TextLabel")
    word.Name, word.BackgroundTransparency = "HatchStageWord", 1
    word.AnchorPoint, word.Position, word.Size = Vector2.new(.5, 0), UDim2.new(.5, 0, 0, 70), UDim2.new(1, 0, 0, 66)
    word.Font, word.TextSize, word.Text = Enum.Font.FredokaOne, 50, (p.heading :: any).Text
    word.TextColor3, word.ZIndex = Color3.new(1, 1, 1), p.panel.ZIndex + 30
    local outline = Instance.new("UIStroke")
    outline.Color, outline.Thickness = Stage.Ink, 4
    outline.Parent = word
    word.Parent = s.shade
    table.insert(s.restore, function() word:Destroy() end)
end
-- BD-1212 paint beat (owner picked the ChatGPT cartoon frames 2026-11-16): two 4 x 2 flipbooks of 256 px cells cut by
-- tools/paint_sheet_cut.py from the owner-approved sheets (docs/77 ui_hatch_paint_*). Paint layers are white and tinted with the egg's real
-- colours; the egg layer (shell, highlights, sparkle) is drawn over them. While a flipbook plays, the old 2D buckets / streams / splashes
-- and the 3D egg hide; the 3D egg (already painted by the v2 bake) comes back when the paint beat ends.
Stage.Paint = {
    pour = {egg = "rbxassetid://92069732192394", paint1 = "rbxassetid://73353455894694", frame = .09},
    spots = {egg = "rbxassetid://81242850190606", paint1 = "rbxassetid://135360744887859", paint2 = "rbxassetid://81436669855366", frame = .09},
    crack = {egg = "rbxassetid://128268812904756", paint1 = "rbxassetid://86542718494821", paint2 = "rbxassetid://131196554258662", frame = .07},
}
local paintOverlay: Frame? = nil
Stage.lastColors = {} :: {Color3} -- the colours the paint beat used, shown as dots on the reveal
local hiddenForPaint: {GuiObject} = {}
local OLD_PAINT = {PaintStream1 = true, PaintStream2 = true, PaintSplash1 = true, PaintSplash2 = true} -- the 2D bucket pictures stay: they pour
local function hideOldPaint(s: any)
    for _, d in s.panel:GetDescendants() do
        if d:IsA("GuiObject") and d.Visible and (OLD_PAINT[d.Name] or d.Name == "HatchEggV2" or d.Name == "PremiumHatchEgg" or string.match(d.Name, "^PaintDrop")) then
            d.Visible = false
            if not table.find(hiddenForPaint, d) then table.insert(hiddenForPaint, d) end
        end
    end
end
local function overlayFor(s: any): Frame
    if paintOverlay and paintOverlay.Parent then return paintOverlay end
    local egg = s.panel:FindFirstChild("HatchEggV2", true) :: GuiObject?
    local base = s.shade.AbsolutePosition
    local cx, cy, side
    local hook = if Stage.eggRect then Stage.eggRect(s) else nil -- BD-1288: the storyboard's big egg
    if hook then
        cx, cy, side = hook.x, hook.y, hook.side
    elseif egg then
        cx, cy = egg.AbsolutePosition.X + egg.AbsoluteSize.X / 2 - base.X, egg.AbsolutePosition.Y + egg.AbsoluteSize.Y / 2 - base.Y
        side = egg.AbsoluteSize.Y * 1.35
    else
        cx, cy = s.body.AbsolutePosition.X + s.body.AbsoluteSize.X / 2 - base.X, s.body.AbsolutePosition.Y + s.body.AbsoluteSize.Y * .38 - base.Y
        side = s.body.AbsoluteSize.Y * .85
    end
    local f = Instance.new("Frame")
    f.Name, f.BackgroundTransparency, f.AnchorPoint = "HatchStagePaint", 1, Vector2.new(.5, .5)
    f.Position, f.Size, f.ZIndex = UDim2.fromOffset(cx, cy), UDim2.fromOffset(side, side), s.panel.ZIndex + 5
    f.Parent = s.shade
    paintOverlay = f
    table.insert(s.restore, function() f:Destroy() paintOverlay = nil end)
    return f
end
local function layer(parent: Frame, name: string, image: string, color: Color3?, z: number): ImageLabel
    local l = Instance.new("ImageLabel")
    l.Name, l.BackgroundTransparency, l.Image, l.Size, l.ZIndex = name, 1, image, UDim2.fromScale(1, 1), z
    l.ImageRectSize = Vector2.new(256, 256)
    if color then l.ImageColor3 = color end
    l.Parent = parent
    return l
end
-- Play one flipbook (8 frames, then hold the last). colors = {paint1, paint2?}
-- Play frames [from..to] of a flipbook (0-based, 4 x 2 cells), each `frameTime` seconds; afterDone runs after the last frame.
function Stage.playBook(kind: string, colors: {Color3}, from: number, to: number, frameTime: number, afterDone: ((Frame) -> ())?)
    local s = stageParts
    if not s or not state then return end
    local book = Stage.Paint[kind]
    if not book or book.egg == "" then return end
    hideOldPaint(s)
    local f = overlayFor(s)
    f:ClearAllChildren()
    f.Rotation = 0
    local z = f.ZIndex
    local layers = {layer(f, "Paint1", book.paint1, colors[1], z + 1)}
    if book.paint2 then table.insert(layers, layer(f, "Paint2", book.paint2, colors[2] or colors[1], z + 2)) end
    table.insert(layers, layer(f, "Egg", book.egg, nil, z + 3))
    task.spawn(function()
        for i = from, to do
            if not f.Parent then return end
            local offset = Vector2.new((i % 4) * 256, math.floor(i / 4) * 256)
            for _, l in layers do l.ImageRectOffset = offset end
            hideOldPaint(s)
            task.wait(if s.reduceMotion then 0 else frameTime)
        end
        if afterDone and f.Parent then afterDone(f) end
    end)
end
-- BD-1212 shell break (ChatGPT sheet continuing the spot spray): frames 1-4 = cracks with white light (during the rattle, the last one
-- held with a soft shake), frames 5-8 = flash and painted shards flying out (at the burst, under the ribbon and the dino).
-- BD-1212 3D egg break (owner 2026-11-16: the drawn break looked bad -> "Yes, 3D shards").
-- Charge (during the rattle): the painted egg shakes harder and harder and a white glow swells behind it.
function Stage.crackCharge()
    local s, f = stageParts, paintOverlay
    if not s or not f or s.reduceMotion then return end
    local glow = Instance.new("ImageLabel")
    glow.Name, glow.BackgroundTransparency, glow.Image = "ChargeGlow", 1, Effects.Requested.glowPlate.id
    glow.AnchorPoint, glow.Position, glow.Size, glow.ZIndex = Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromScale(.9, .9), f.ZIndex
    glow.ImageTransparency = .9
    glow.Parent = f
    task.spawn(function()
        local t = 0
        while f.Parent and stageParts == s do
            t += task.wait()
            local k = math.min(1, t / 2.5) -- builds up over ~2.5 s, then stays at full strength
            f.Rotation = math.sin(t * (24 + 30 * k)) * (2 + 5 * k) * (s.charge or 1) -- Legendary / Mythic shake a little more (Stage.buildUp)
            glow.ImageTransparency = .9 - .75 * k
            glow.Size = UDim2.fromScale(.9 + .7 * k + .08 * math.sin(t * 9), .9 + .7 * k + .08 * math.sin(t * 9))
        end
    end)
end
-- Burst (at the reveal): a white flash, then the 3D shell shards in the egg's colour fly out with spin, gravity and fade, plus sparkles.
function Stage.crackBurst()
    local s, f = stageParts, paintOverlay
    if not s or not f then return end
    local center = f.AbsolutePosition + f.AbsoluteSize / 2 - s.shade.AbsolutePosition
    local side = f.AbsoluteSize.X
    f:Destroy()
    paintOverlay = nil
    if s.reduceMotion then return end
    local colour = Stage.lastColors[1] or Color3.fromRGB(245, 236, 214)
    -- flash
    local flash = Instance.new("ImageLabel")
    flash.Name, flash.BackgroundTransparency, flash.Image = "BurstFlash", 1, Effects.Requested.glowPlate.id
    flash.AnchorPoint, flash.Position, flash.Size, flash.ZIndex = Vector2.new(.5, .5), UDim2.fromOffset(center.X, center.Y), UDim2.fromOffset(side, side), s.panel.ZIndex + 40
    flash.ImageColor3 = Color3.new(1, 1, 1)
    flash.Parent = s.shade
    TweenService:Create(flash, TweenInfo.new(.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {Size = UDim2.fromOffset(side * 3.2, side * 3.2), ImageTransparency = 1}):Play()
    task.delay(.4, function() flash:Destroy() end)
    -- sparkles flying out
    local sheet = Effects.Sheets and Effects.Sheets.starFour
    for i = 1, 10 do
        local star = Instance.new("ImageLabel")
        star.BackgroundTransparency, star.Image, star.ZIndex = 1, Effects.Requested.starFour.id, s.panel.ZIndex + 41
        if sheet then
            local cell = sheet.size / sheet.grid
            star.ImageRectSize, star.ImageRectOffset = Vector2.new(cell, cell), Vector2.new(cell * 2, cell)
        end
        star.AnchorPoint, star.Size, star.Position = Vector2.new(.5, .5), UDim2.fromOffset(34, 34), UDim2.fromOffset(center.X, center.Y)
        star.Parent = s.shade
        local a = i / 10 * math.pi * 2
        local d = side * (1.1 + (i % 3) * .25)
        TweenService:Create(star, TweenInfo.new(.7, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
            {Position = UDim2.fromOffset(center.X + math.cos(a) * d, center.Y + math.sin(a) * d), ImageTransparency = 1, Rotation = 180}):Play()
        task.delay(.75, function() star:Destroy() end)
    end
    -- 3D shards
    local template = game:GetService("ReplicatedStorage"):FindFirstChild("HatchStageShards")
    if not template then return end
    local view = Instance.new("ViewportFrame")
    view.Name, view.BackgroundTransparency, view.ZIndex = "BurstShards", 1, s.panel.ZIndex + 39
    view.AnchorPoint, view.Position, view.Size = Vector2.new(.5, .5), UDim2.fromOffset(center.X, center.Y), UDim2.fromOffset(side * 3, side * 3)
    view.Ambient, view.LightColor, view.LightDirection = Color3.fromRGB(150, 150, 150), Color3.new(1, 1, 1), Vector3.new(-.4, -1, -.6)
    view.Parent = s.shade
    local world = Instance.new("WorldModel")
    world.Parent = view
    local model = template:Clone()
    model.Parent = world
    local cf, size = model:GetBoundingBox()
    local radius = math.max(size.X, size.Y, size.Z) / 2
    local camera = Instance.new("Camera")
    camera.FieldOfView = 40
    camera.CFrame = CFrame.lookAt(cf.Position + Vector3.new(0, radius * .2, radius * 3 * 3.2), cf.Position)
    camera.Parent = view
    view.CurrentCamera = camera
    local shards = {}
    for i, part in model:GetChildren() do
        if part:IsA("BasePart") then
            part.Color, part.Material, part.Reflectance = colour, Enum.Material.SmoothPlastic, .15
            local out = part.Position - cf.Position
            if out.Magnitude < 1e-3 then out = Vector3.new(0, 1, 0) end
            local dir = out.Unit
            table.insert(shards, {part = part, start = part.CFrame,
                vel = dir * radius * (5 + (i % 4)) + Vector3.new(0, radius * 3, radius * 2),
                spin = Vector3.new((i * 1.3) % 6 - 3, (i * 2.1) % 6 - 3, (i * .7) % 6 - 3)})
        end
    end
    local t, duration = 0, .9
    local conn
    conn = RunService.RenderStepped:Connect(function(dt)
        t += dt
        if t >= duration or not view.Parent then
            conn:Disconnect()
            view:Destroy()
            return
        end
        for _, sh in shards do
            local pos = sh.start.Position + sh.vel * t + Vector3.new(0, -radius * 14, 0) * t * t * .5
            sh.part.CFrame = CFrame.new(pos) * (sh.start - sh.start.Position) * CFrame.Angles(sh.spin.X * t * 3, sh.spin.Y * t * 3, sh.spin.Z * t * 3)
            sh.part.Transparency = math.clamp((t - duration * .55) / (duration * .45), 0, 1)
        end
    end)
    table.insert(s.restore, function() if view.Parent then view:Destroy() end end)
end
function Stage.playPaint(kind: string, colors: {Color3})
    local s = stageParts
    if not s or not state then return end
    local book = Stage.Paint[kind]
    Stage.lastColors = if book.paint2 then {colors[1], colors[2] or colors[1]} else {colors[1]}
    hideOldPaint(s)
    local f = overlayFor(s)
    f:ClearAllChildren()
    local z = f.ZIndex
    local layers = {layer(f, "Paint1", book.paint1, colors[1], z + 1)}
    if book.paint2 then table.insert(layers, layer(f, "Paint2", book.paint2, colors[2] or colors[1], z + 2)) end
    table.insert(layers, layer(f, "Egg", book.egg, nil, z + 3))
    task.spawn(function()
        for i = 0, 7 do
            if not f.Parent then return end
            local offset = Vector2.new((i % 4) * 256, math.floor(i / 4) * 256)
            for _, l in layers do l.ImageRectOffset = offset end
            hideOldPaint(s) -- the 3D egg and old splashes may be shown again by the sequence while the flipbook plays
            task.wait(if s.reduceMotion then 0 else book.frame)
        end
    end)
end
-- The paint beat is over (rattle starts): the 3D egg comes back with its real pattern.
function Stage.paintDone()
    if paintOverlay then paintOverlay:Destroy() paintOverlay = nil end
    for _, d in hiddenForPaint do if d.Parent then d.Visible = true end end
    hiddenForPaint = {}
end

-- Next egg: back to the calm egg look (word gone, white rays, light veil).
function Stage.clearReveal(s: any)
    local list, conns = s.reveal, s.revealConns
    s.reveal, s.revealConns = nil, nil
    for _, c in conns or {} do c:Disconnect() end
    if list then for i = #list, 1, -1 do pcall(list[i]) end end
    -- the counter chip comes back for the next egg ("Egg 2 of 5"); the sequence shows its own lines again at its reveal
    for _, d in s.panel:GetDescendants() do if d.Name == "EggCounter" and d:IsA("GuiObject") then d.Visible = true end end
end
function Stage.nextEgg()
    local s = stageParts
    if not s or not state then return end
    if s.reveal then Stage.clearReveal(s) end
    s.shade.BackgroundTransparency = 1
    for _, o in s.shade:GetChildren() do if o.Name == "HatchStageWord" or o.Name == "HatchStageWordDrop" then o:Destroy() end end
    s.sun.ImageColor3, s.sun.ImageTransparency = Color3.new(1, 1, 1), .45
    s.veil.BackgroundColor3, s.veil.BackgroundTransparency = Color3.new(0, 0, 0), Stage.Veil
    -- back from a Legendary / Mythic build-up: calm spin, the warm glow at its normal size
    for _, tween in s.buildTweens or {} do tween:Cancel() end
    s.builtUp, s.charge, s.spin.speed, s.buildTweens = false, 1, 6, nil
    s.glow.Size, s.glow.ImageColor3, s.glow.ImageTransparency = UDim2.fromOffset(760, 760), Color3.fromRGB(255, 244, 200), .35
    pending = nil
end

-- Back to the window look (any screen opens, or the modal closes). Safe to call when nothing was applied.
function Stage.restore()
    if Stage.onRestore then pcall(Stage.onRestore) end
    local s = state
    state = nil
    stageParts, pending = nil, nil
    Stage.paintDone()
    Stage.lastColors = {}
    if not s then return end
    for _, c in s.conns do c:Disconnect() end
    for i = #s.restore, 1, -1 do s.restore[i]() end
end
return Stage
