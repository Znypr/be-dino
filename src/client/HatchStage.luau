--!strict
-- BD-1211 (BD-1206 cohesion order step 1, docs/240 R1/R2/R3/R7, style tile v2 boards 2-4): with Config.HatchStageEnabled the hatch is a full
-- STAGE over the world, not a window: the shared modal's stud body, frame and header strip are hidden while the hatch is open, the dark scrim
-- becomes a light veil with soft rays (the uploaded fx3 rays picture) behind the egg, "Egg 2 of 5" sits in a cream chip at the top, and every
-- dark plate or chip the hatch builds (colour and pattern buckets, labels, "Skip the rest") is turned into the one style: cream plate with an ink
-- outline and ink text, buttons grey (the green NEXT EGG stays green). The X stays (red, top right of the stage).
-- Bootstrap calls apply() when the hatch opens and restore() whenever any screen opens or the modal closes, so every other screen keeps its
-- window exactly as before. Flag off = this file is never required.
local TweenService = game:GetService("TweenService")
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
    if o.Name == "Backdrop" and o.Parent and o.Parent.Name == "HatchFxBack" then
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
        if state and state.restore == restore then keep(p.shade, "BackgroundTransparency", 1) end
    end)
    -- a soft warm glow behind the egg (real art: the uploaded neutral radial glow plate); it breathes gently, still with Reduce Motion
    local rays = Instance.new("ImageLabel")
    rays.Name, rays.BackgroundTransparency, rays.Image = "HatchStageRays", 1, Effects.Requested.glowPlate.id
    rays.AnchorPoint, rays.Position, rays.Size = Vector2.new(.5, .5), UDim2.fromScale(.5, .46), UDim2.fromOffset(760, 760)
    rays.ImageColor3, rays.ImageTransparency, rays.ZIndex = Color3.fromRGB(255, 244, 200), .35, 1 -- behind the egg and the dino, never over them
    rays.Parent = p.panel
    table.insert(restore, function() rays:Destroy() end)
    if not p.reduceMotion then
        local spin = TweenService:Create(rays, TweenInfo.new(2.4, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {ImageTransparency = .55})
        spin:Play()
        table.insert(restore, function() spin:Cancel() end)
    end
    -- BD-1212 full screen: the Blender sunburst fills the whole screen behind the egg (a child of the scrim, under the panel), turning slowly
    local sun = Instance.new("ImageLabel")
    sun.Name, sun.BackgroundTransparency, sun.Image = "HatchStageSunburst", 1, Stage.RaysImage
    sun.AnchorPoint, sun.Position, sun.SizeConstraint = Vector2.new(.5, .5), UDim2.fromScale(.5, .47), Enum.SizeConstraint.RelativeXX
    sun.Size, sun.ZIndex, sun.ImageColor3, sun.ImageTransparency = UDim2.fromScale(1.5, 1.5), 2, Color3.new(1, 1, 1), .45
    sun.Parent = backdrop
    table.insert(restore, function() sun:Destroy() end)
    if not p.reduceMotion then
        local turn = TweenService:Create(sun, TweenInfo.new(60, Enum.EasingStyle.Linear, Enum.EasingDirection.In, -1), {Rotation = 360})
        turn:Play()
        table.insert(restore, function() turn:Cancel() end)
    end
    -- the HUD steps aside (only the crystal counter stays, docs/240 s2 board 2): every other top-level UI piece hides while the stage is up
    for _, child in p.gui:GetChildren() do
        if child:IsA("GuiObject") and child.Visible and not Stage.KeepOnStage[child.Name] and child ~= p.shade then
            local crystals = false
            for _, d in child:GetDescendants() do
                if d:IsA("TextLabel") and string.find(d.Text, "Crystals", 1, true) then crystals = true break end
            end
            if not crystals then
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
    stageParts = {gui = p.gui, shade = p.shade, panel = p.panel, body = p.body, sun = sun, glow = rays, veil = veil, reduceMotion = p.reduceMotion, restore = restore}
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
    if not layer then
        table.insert(conns, p.gui.ChildAdded:Connect(function(o)
            if o.Name == "HatchUiLayer" then
                task.defer(function() Stage.styleTree(o) end)
                table.insert(conns, o.DescendantAdded:Connect(function(d) task.defer(function() if d.Parent then style(d, o) end end) end))
            end
        end))
    end
    state = {restore = restore, conns = conns}
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
    local rank = math.clamp(info.rarity or 1, 1, #Stage.Ladder)
    local tier = Stage.Ladder[rank]
    local restore = s.restore
    local color: Color3 = if info.failed then Color3.fromRGB(220, 220, 220) else (info.color or Color3.new(1, 1, 1))
    s.sun.ImageColor3 = if rank <= 1 then Color3.new(1, 1, 1) else color:Lerp(Color3.new(1, 1, 1), .15)
    s.sun.ImageTransparency = tier.rays
    s.glow.ImageColor3 = color:Lerp(Color3.new(1, 1, 1), .5)
    s.veil.BackgroundTransparency = tier.veil
    if rank >= 5 then s.veil.BackgroundColor3 = Color3.fromRGB(60, 34, 0) end
    -- keep something hidden for the rest of this reveal even if the sequence shows it again (it fades labels in after the burst)
    local function hold(o: GuiObject)
        o.Visible = false
        table.insert(state.conns, o:GetPropertyChangedSignal("Visible"):Connect(function() if o.Visible and stageParts == s then o.Visible = false end end))
    end
    -- the big word replaces the "You hatched a ..." banner and the "Egg N of M" chip while the dino is shown
    local function scan()
        if stageParts ~= s then return end
        for _, d in s.panel:GetDescendants() do
            if d:IsA("TextLabel") and d.Visible and (string.find(d.Text, "You hatched a", 1, true) or d.Name == "EggCounter") then
                local plate = d.Parent
                hold(if plate and plate:IsA("Frame") and plate ~= s.panel and plate ~= s.body and plate.AbsoluteSize.X < 700 then plate else d)
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
    local bw = math.min(screen.X * .3, 520)
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
    -- the dino is the star: its 3D view grows by a third on the stage (more for Legendary and up), with a little overshoot
    for _, v in s.body:GetDescendants() do
        if v:IsA("ViewportFrame") and v.AbsoluteSize.X > 200 and not v:FindFirstChild("StageGrow") then
            if v.AnchorPoint == Vector2.zero then -- grow around the middle, not the top-left corner
                v.AnchorPoint = Vector2.new(.5, .5)
                v.Position = v.Position + UDim2.new(v.Size.X.Scale / 2, v.Size.X.Offset / 2, v.Size.Y.Scale / 2, v.Size.Y.Offset / 2)
            end
            local grow = Instance.new("UIScale")
            grow.Name, grow.Scale = "StageGrow", if s.reduceMotion then (if rank >= 5 then 1.85 else 1.6) else 1
            grow.Parent = v
            if not s.reduceMotion then
                TweenService:Create(grow, TweenInfo.new(.45, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = if rank >= 5 then 1.85 else 1.6}):Play()
            end
        end
    end
    -- the dino stands on a glowing pedestal in the rarity colour (behind the panel, so behind the dino)
    local view = s.body:FindFirstChild("DinosaurPreview", true) :: GuiObject?
    local vc = if view then view.AbsolutePosition + view.AbsoluteSize / 2 - base else Vector2.new(screen.X / 2, screen.Y * .48)
    local vh = if view then view.AbsoluteSize.Y else screen.Y * .4
    local pw = math.min(screen.X * .2, 340)
    local pedestalY = vc.Y + vh * .6 -- under the feet (the view grows around its middle)
    local pedestal = art("HatchStagePedestal", Stage.Art.pedestal, Vector2.new(pw, pw * 212 / 429), Vector2.new(vc.X, pedestalY), s.panel.ZIndex - 1,
        if rank <= 1 then Color3.fromRGB(150, 225, 255) else color:Lerp(Color3.new(1, 1, 1), .35))
    pop(pedestal, .05)
    for _, l in {info.nameLabel, info.oddsLabel, info.detailLabel} do if l then hold(l) end end
    for _, plate in {s.body:FindFirstChild("RarityPill"), s.body:FindFirstChild("NameShine")} do
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
        local plateW = math.min(screen.X * .2, 300)
        local plateH = plateW * 137 / 439
        local plateC = Vector2.new(vc.X + 26, pedestalY + pw * 212 / 429 * .45 + plateH * .55)
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
        for k, c in Stage.lastColors do
            local d = Instance.new("Frame")
            d.Name, d.AnchorPoint, d.ZIndex = "ColourDot" .. k, Vector2.new(.5, .5), plate.ZIndex
            d.Size = UDim2.fromOffset(dot, dot)
            d.Position = UDim2.fromOffset(plateC.X - plateW / 2 - dot * (#Stage.lastColors - k + .7) - 6 * (#Stage.lastColors - k), plateC.Y)
            Chip.apply(d, c, Stage.Ink)
            d.Parent = s.shade
            table.insert(restore, function() d:Destroy() end)
            pop(d, .18 + k * .05)
        end
        if newFind then
            local sticker = art("HatchStageNew", Stage.Art.new, Vector2.new(plateH * 1.25, plateH * 1.17), Vector2.new(plateC.X + plateW / 2 + plateH * .25, plateC.Y - plateH * .25), plate.ZIndex + 2)
            sticker.Rotation = 12
            pop(sticker, .3)
        end
    end
    -- one big glossy NEXT exactly where "Tap for next egg" was (a picture only: the tap goes through to the hatch's own tap catcher)
    local nextShown = false
    local function placeNext()
    if stageParts ~= s then return end
    -- SKIP is one short word, and the dino-view RESET button never covers the stage (both are rebuilt after the burst)
    for _, b in s.gui:GetDescendants() do
        if (b:IsA("TextButton") or b:IsA("TextLabel")) and string.upper(b.Text) == "SKIP THE REST" then b.Text = "SKIP" end
        if b:IsA("TextButton") and (b.Name == "ResetView" or b.Text == "RESET") and b.Visible then hold(b) end
    end
    -- the dino is the star (target: about 40% of the screen): its view grows once it exists
    for _, v in s.body:GetDescendants() do
        if v:IsA("ViewportFrame") and v.Name == "DinosaurPreview" and not v:GetAttribute("StageGrown") then
            v:SetAttribute("StageGrown", true)
            if v.AnchorPoint == Vector2.zero then
                v.AnchorPoint = Vector2.new(.5, .5)
                v.Position = v.Position + UDim2.new(v.Size.X.Scale / 2, v.Size.X.Offset / 2, v.Size.Y.Scale / 2, v.Size.Y.Offset / 2)
            end
            -- Roblox uses only ONE UIScale per object: grow the view's own one (or add one if it has none)
            local grow = v:FindFirstChildOfClass("UIScale")
            if not grow then grow = Instance.new("UIScale") grow.Parent = v end
            local target = grow.Scale * 1.6
            if s.reduceMotion then grow.Scale = target
            else TweenService:Create(grow, TweenInfo.new(.45, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = target}):Play() end
        end
    end
    if nextShown then return end
    local hint = s.body:FindFirstChild("TapHint", true) :: TextLabel?
    if hint and hint.Visible and hint.Text ~= "" then
        nextShown = true
        local hc = hint.AbsolutePosition + hint.AbsoluteSize / 2 - base
        hold(hint)
        local ok, Skin = pcall(require, Shared:WaitForChild("ToyboxSkin"))
        local next = Instance.new("TextButton")
        next.Name, next.Text, next.AutoButtonColor = "HatchStageNext", "NEXT", false
        next.AnchorPoint, next.Size, next.Position = Vector2.new(.5, .5), UDim2.fromOffset(250, 66), UDim2.fromOffset(hc.X, hc.Y)
        next.BackgroundColor3, next.Font, next.TextSize, next.TextColor3, next.ZIndex = Color3.fromRGB(88, 200, 64), Enum.Font.FredokaOne, 34, Color3.new(1, 1, 1), s.panel.ZIndex + 32
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
    if egg then
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
function Stage.nextEgg()
    local s = stageParts
    if not s or not state then return end
    for _, o in s.shade:GetChildren() do if o.Name == "HatchStageWord" or o.Name == "HatchStageWordDrop" then o:Destroy() end end
    s.sun.ImageColor3, s.sun.ImageTransparency = Color3.new(1, 1, 1), .45
    s.veil.BackgroundColor3, s.veil.BackgroundTransparency = Color3.new(0, 0, 0), Stage.Veil
    pending = nil
end

-- Back to the window look (any screen opens, or the modal closes). Safe to call when nothing was applied.
function Stage.restore()
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
