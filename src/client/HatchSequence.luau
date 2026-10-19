--!strict
-- Hatch sequence (client). Draws the ~3 s egg opening + dinosaur reveal + tap-to-continue for ONE already
-- committed egg. Presentation only: it never reads or changes genes, species, odds or saved data.
-- Timing, curves, tap gating, rarity escalation and skip rules are pure and live in Shared.HatchTimeline
-- (verify_hatch_sequence.py). Performance: one Heartbeat connection per egg and persistent, reused pools
-- (rings, rays, motes, sparkles, fireworks, rain, arcs, shock rings); no Instances are created per frame.
-- Reduced Motion: no shake, zoom, particles or rotation, only a soft static glow and fades.
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Input = game:GetService("UserInputService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Theme = require(Shared.UITheme)
local Sfx = require(Shared.Sfx)
local SfxRules = require(Shared.SfxRules)
local Timeline = require(Shared.HatchTimeline)
local Copy = require(Shared.FtueP1)
local FxPlan = require(Shared.HatchFxPlan)
local EggGenetics = require(Shared.EggGenetics)
local ClassBadge = require(Shared.ClassBadge) -- owner 2026-10-16: class badge next to the dino name (icon slots, PLACEHOLDER until bound)
local InspectView = require(script.Parent.InspectView)
local HatchFx = require(script.Parent.HatchFx)
local MutationReveal = require(script.Parent.MutationReveal) -- BD-162
local Config = require(Shared.Config)
local V2Assets = require(Shared.HatchV2Assets) -- docs/118 s9: flag or Studio-only preview toggle
local EggV2 = require(script.Parent.HatchEggV2) -- BD-397 (docs/118): 3D egg + paint coats behind Config.HatchV2; nil handle = v1 look
local ModalClose = require(script.Parent.ModalClose) -- BD-1019: the tap catcher that never covers X, the end buttons or the backdrop
local CloseRules = require(Shared.ModalCloseRules)
local Chip = require(Shared.ChipStyle) -- BD-1070: the one chip style of the whole game (chunky tag: rounded rectangle, 3 px outline, palette fill)
local TagFit = require(Shared.TagFit) -- BD-1107: ribbons, the stop tag and the class badge are measured before they are drawn
local TagLayout = require(Shared.HatchTagLayout) -- BD-1107: where they go (stacked down the side columns, never over each other)
local NewFinds = require(Shared.PatternColourIndex) -- BD-1039: "New pattern!" / "New colour!" ribbons (flag Config.PatternColourIndexEnabled)
local PrivateState = require(script.Parent.PrivateState)
local HttpService = game:GetService("HttpService")

local Seq = {}
local batch = Timeline.session -- BD-444: where we are in the hatch party ("Egg 3 of 15")
local CENTER_EGG = Vector2.new(412, 130) -- body coordinates (824 x 402 virtual px)
local CENTER_DINO = Vector2.new(412, 118)
local BODY_HOME = Vector2.new(18, 98)
local BODY_CENTER = Vector2.new(430, 299)
local RING_N, RAY_N, MOTE_N, ARC_N = 8, 6, 12, 6
local GRAVITY = 260
local WHITE = Color3.new(1, 1, 1)
local TAU = math.pi * 2
local FIREWORKS = {{.35, 250, 120}, {.75, 580, 92}, {1.15, 412, 58}}

-- Failed-egg splat kit (built once, reused): native rounded shapes until the egg_splat / egg_shell icons are bound.
type Splat = {group: CanvasGroup, puddle: Frame, lobes: {Frame}, yolk: Frame, drips: {Frame}, shells: {Frame}, domes: {Frame},
    shellImages: {ImageLabel}, image: ImageLabel}
local PUDDLE = Vector2.new(412, 200) -- body coordinates
local YOLK_REST = 190
local SHELL_START_Y, SHELL_FALL = 112, 70
local CREAM = Color3.fromRGB(255, 244, 214)
local YOLK_GOLD = Color3.fromRGB(255, 196, 38)

local function corner(parent: Instance, radius: UDim?)
    local c = Instance.new("UICorner")
    c.CornerRadius = radius or UDim.new(1, 0)
    c.Parent = parent
end
local function dot(parent: Instance, name: string, z: number, w: number, h: number, round: boolean): Frame
    local f = Instance.new("Frame")
    f.Name, f.BorderSizePixel, f.BackgroundTransparency, f.Visible, f.AnchorPoint = name, 0, 1, false, Vector2.new(.5, .5)
    f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(w, h), z, parent
    if round then corner(f) end
    return f
end

-- Paint-bucket kit (BD-171), built once and reused. PLACEHOLDER (docs/72, docs/77 paint_bucket): the bucket is built from the game's own UI
-- primitives in the handbook style (chunky rounded shapes, 3 px dark outline, palette fills) until the paint_bucket icon (docs/83 item 31) is
-- uploaded and bound in UIIconAssets. It is filled with the REAL egg colour (HatchTimeline.revealRgb, EggColors rgb) and never shows a blend.
-- The splashes and droplets are effects, the chips come from ChipStyle. Positions are body coordinates.
type PaintKit = {buckets: {CanvasGroup}, bucketPaints: {{Frame}}, bucketImages: {ImageLabel}, bucketShapes: {Frame}, streams: {Frame},
    splashes: {Frame}, splashStrokes: {UIStroke}, splashScales: {UIScale}, drops: {Frame}, chips: {Frame}, chipLabels: {TextLabel},
    chipScales: {UIScale}, chipSwatches: {Frame}, chipStrokes: {UIStroke}, chipBadges: {Frame}, chipBadgeLabels: {TextLabel},
    patternChip: Frame, patternLabel: TextLabel, patternScale: UIScale, patternStroke: UIStroke,
    conditionChip: Frame, conditionLabel: TextLabel, conditionStroke: UIStroke}
local SPLASH_POINTS = {Vector2.new(412 - 40, 100), Vector2.new(412 + 40, 100)}
-- a mid-tone steel, so every egg colour reads on it: pale Cream and dark Black both have contrast against it
local TIN, TIN_SHADE, TIN_RIM, TIN_HANDLE = Color3.fromRGB(168, 184, 212), Color3.fromRGB(132, 148, 180), Color3.fromRGB(206, 216, 236), Color3.fromRGB(196, 208, 230)
local CHIP_FILL = Theme.Colors.card -- palette fill of a chip that holds a swatch and a tag
local TIER_COLORS: {Color3} = Theme.RarityColors -- Common grey .. Mythic red, the game's one rarity palette
-- Chip fill per egg condition, from the shared palette only (there is no condition colour table yet, docs/116 C-17): Cracked gold, Rainbow purple, Astra blue.
local function conditionFill(id: string?): Color3
    if id == "cracked" then return Theme.Colors.gold elseif id == "rainbow" then return Theme.Colors.purple elseif id == "astra" then return Theme.Colors.blue end
    return CHIP_FILL
end
-- BD-220 chip in the game UI style (docs/72, BD-1070): a chunky tag from ChipStyle, ONE line, big text. spec = HatchFxPlan.Chips row {cx, cy, w, h}.
-- Returns the frame, its label, scale and outline.
local function chipFrame(front: Frame, name: string, spec: {number}, textLeft: number, textRight: number): (Frame, TextLabel, UIScale, UIStroke)
    local chip, text, stroke = Chip.new(front, {name = name, fill = CHIP_FILL, size = UDim2.fromOffset(spec[3], spec[4]), position = UDim2.fromOffset(spec[1], spec[2]),
        anchor = Vector2.new(.5, .5), z = 27})
    chip.Visible = false
    text.Position, text.Size, text.ZIndex = UDim2.fromOffset(textLeft, 3), UDim2.new(1, -(textLeft + textRight), 1, -6), 28
    local scale = Instance.new("UIScale") scale.Scale, scale.Parent = 0, chip
    return chip, text, scale, stroke
end
-- PLACEHOLDER bucket from UI primitives: tin body, wire handle, a rim with the paint surface, paint dipped over the top with three drips.
-- Returns the shapes frame and every frame that shows the paint (named BucketPaint*, all filled with the real colour).
local function buildBucketShapes(group: CanvasGroup): (Frame, {Frame})
    local ink = Theme.Colors.outline
    local shapes = Instance.new("Frame")
    shapes.Name, shapes.BackgroundTransparency, shapes.Size, shapes.ZIndex, shapes.Parent = "NativeBucket", 1, UDim2.fromScale(1, 1), 26, group
    local function box(name: string, parent: GuiObject, x: number, y: number, w: number, h: number, z: number, fill: Color3, outlined: boolean, radius: number): Frame
        local f = Instance.new("Frame")
        f.Name, f.BorderSizePixel, f.Position, f.Size, f.ZIndex, f.BackgroundColor3 = name, 0, UDim2.fromOffset(x, y), UDim2.fromOffset(w, h), z, fill
        local c = Instance.new("UICorner") c.CornerRadius = UDim.new(0, radius) c.Parent = f
        if outlined then local st = Instance.new("UIStroke") st.Thickness, st.Color, st.Parent = Chip.Spec.outline, ink, f end
        f.Parent = parent
        return f
    end
    for _, spec in {{"HandleOutline", 9, ink}, {"HandleWire", 4, TIN_HANDLE}} do -- the wire handle: a dark outer arc and a light wire on top
        local arc = box(spec[1] :: string, shapes, 12, 4, 68, 60, 26, WHITE, false, 30)
        arc.BackgroundTransparency = 1
        local st = Instance.new("UIStroke") st.Thickness, st.Color, st.Parent = spec[2] :: number, spec[3] :: Color3, arc
    end
    local body = box("BucketBody", shapes, 14, 34, 64, 54, 27, TIN, true, 10)
    box("BucketShade", body, 4, 36, 56, 12, 28, TIN_SHADE, false, 6)
    local paints: {Frame} = {}
    table.insert(paints, box("BucketPaintCap", body, 0, 0, 64, 28, 28, WHITE, true, 10)) -- outlined: pale paint (Cream) must still read against the tin
    for n, d in {{8, 10, 18}, {26, 12, 26}, {46, 10, 14}} do table.insert(paints, box("BucketPaintDrip" .. n, body, d[1], 14, d[2], d[3] + 6, 28, WHITE, false, 5)) end
    local rim = box("BucketRim", shapes, 9, 26, 74, 17, 29, TIN_RIM, true, 8)
    table.insert(paints, box("BucketPaintSurface", rim, 5, 3, 64, 8, 30, WHITE, false, 4))
    return shapes, paints
end
local function buildPaint(front: Frame): PaintKit
    local kit: any = {buckets = {}, bucketPaints = {}, bucketImages = {}, bucketShapes = {}, streams = {}, splashes = {}, splashStrokes = {},
        splashScales = {}, drops = {}, chips = {}, chipLabels = {}, chipScales = {}, chipSwatches = {}, chipStrokes = {}, chipBadges = {}, chipBadgeLabels = {}}
    local bucketIcon = (Theme.ImageIds :: any).paint_bucket
    for i = 1, 2 do
        local group = Instance.new("CanvasGroup")
        group.Name, group.BackgroundTransparency, group.AnchorPoint, group.Visible = "PaintBucket" .. i, 1, Vector2.new(.5, .5), false
        group.Size, group.ZIndex, group.Active, group.Parent = UDim2.fromOffset(92, 92), 26, false, front
        local shapes, paints = buildBucketShapes(group) -- PLACEHOLDER bucket made of UI shapes; hidden once the real icon is bound
        local image = Instance.new("ImageLabel")
        image.Name, image.BackgroundTransparency, image.Size, image.ZIndex, image.Visible = "BucketImage", 1, UDim2.fromScale(1, 1), 26, false
        image.Parent = group
        if typeof(bucketIcon) == "string" and bucketIcon ~= "" then image.Image, image.Visible, shapes.Visible = bucketIcon, true, false end
        kit.buckets[i], kit.bucketPaints[i], kit.bucketImages[i], kit.bucketShapes[i] = group, paints, image, shapes
        local stream = dot(front, "PaintStream" .. i, 25, 9, 60, false)
        stream.AnchorPoint = Vector2.new(.5, 0)
        corner(stream)
        kit.streams[i] = stream
        local splash = dot(front, "PaintSplash" .. i, 25, 190, 190, true)
        local stroke = Instance.new("UIStroke") stroke.Thickness, stroke.Transparency, stroke.Parent = 9, 1, splash
        local scale = Instance.new("UIScale") scale.Parent = splash
        kit.splashes[i], kit.splashStrokes[i], kit.splashScales[i] = splash, stroke, scale
        -- Colour chip right under its bucket: [swatch] Name [TIER tag], one line. The swatch is the colour's exact palette rgb (set in showChip).
        local spec = FxPlan.Chips[if i == 1 then "left" else "right"]
        local chip, text, sc, cs = chipFrame(front, "PaintChip" .. i, spec, 46, 104)
        local swatch = Chip.swatch(chip, 30, nil, 28)
        swatch.Position = UDim2.new(0, 25, .5, 0)
        local badge, badgeText = Chip.new(chip, {name = "TierBadge", fill = WHITE, size = UDim2.fromOffset(94, 30), position = UDim2.new(1, -8, .5, 0), anchor = Vector2.new(1, .5), z = 28, textInset = 4})
        kit.chips[i], kit.chipLabels[i], kit.chipScales[i], kit.chipSwatches[i], kit.chipStrokes[i] = chip, text, sc, swatch, cs
        kit.chipBadges[i], kit.chipBadgeLabels[i] = badge, badgeText
    end
    -- Pattern label on the egg after the buckets, and the condition chip shown from the first frame (BD-220 / BD-223).
    local pchip, ptext, pscale, pstroke = chipFrame(front, "PatternChip", FxPlan.Chips.pattern, 12, 12)
    kit.patternChip, kit.patternLabel, kit.patternScale, kit.patternStroke = pchip, ptext, pscale, pstroke
    local cchip, ctext, cscale, cstroke = chipFrame(front, "ConditionChip", FxPlan.Chips.condition, 12, 12)
    cscale.Scale = 1
    kit.conditionChip, kit.conditionLabel, kit.conditionStroke = cchip, ctext, cstroke
    for i = 1, Timeline.PaintMax do kit.drops[i] = dot(front, "PaintDrop" .. i, 26, 10, 10, true) end
    return kit
end

type Layers = {paint: PaintKit, splat: Splat, back: Frame, front: Frame, backdrop: Frame, rings: {Frame}, ringScales: {UIScale}, rays: {Frame}, motes: {Frame},
    podium: {Frame}, particles: {Frame}, fw: {Frame}, rain: {Frame}, shocks: {Frame}, shockStrokes: {UIStroke}, shockScales: {UIScale},
    arcs: {Frame}, shimmer: Frame, shimmerGradient: UIGradient}
local layers: Layers? = nil

local function buildSplat(front: Frame): Splat
    -- PLACEHOLDER (docs/72): the egg-white puddle, yolk and shell cups below are native shape stacks. They are replaced by the
    -- ChatGPT icons egg_splat / egg_shell (docs/83 items 29 and 30) as soon as their asset IDs are bound in UIIconAssets; they never count as final art.
    local group = Instance.new("CanvasGroup")
    group.Name, group.BackgroundTransparency, group.Active, group.ZIndex = "EggSplat", 1, false, 24
    group.Size, group.Parent = UDim2.fromOffset(824, 402), front
    local function blob(name: string, z: number, w: number, h: number, color: Color3, transparency: number): Frame
        local f = dot(group, name, z, w, h, true)
        f.BackgroundColor3, f.BackgroundTransparency = color, transparency
        return f
    end
    local puddle = blob("EggWhitePuddle", 24, 250, 66, Color3.fromRGB(255, 252, 240), .12)
    local rim = Instance.new("UIStroke") rim.Color, rim.Thickness, rim.Transparency, rim.Parent = Color3.fromRGB(255, 255, 255), 3, .45, puddle
    local lobes = {blob("PuddleLobeL", 24, 80, 30, Color3.fromRGB(255, 252, 240), .25), blob("PuddleLobeR", 24, 64, 26, Color3.fromRGB(255, 252, 240), .25)}
    local drips = {blob("Drip1", 25, 12, 18, Color3.fromRGB(255, 252, 240), .2), blob("Drip2", 25, 10, 16, Color3.fromRGB(255, 252, 240), .2)}
    local yolk = blob("Yolk", 26, 74, 62, YOLK_GOLD, 0)
    local yolkStroke = Instance.new("UIStroke") yolkStroke.Color, yolkStroke.Thickness, yolkStroke.Parent = Color3.fromRGB(190, 120, 10), 3, yolk
    local shine = Instance.new("Frame")
    shine.BackgroundColor3, shine.BorderSizePixel, shine.AnchorPoint, shine.BackgroundTransparency = WHITE, 0, Vector2.new(.5, .5), .1
    shine.Position, shine.Size, shine.ZIndex, shine.Parent = UDim2.fromScale(.32, .3), UDim2.fromOffset(22, 13), 27, yolk
    corner(shine)
    local shells, domes, shellImages = {}, {}, {}
    for i = 1, 2 do
        -- A shell half is a cream cup: outer ellipse plus a darker hollow inside (no clipping: clips break on rotation).
        local shell = dot(group, "ShellHalf" .. i, 28, 104, 62, false)
        local dome = Instance.new("Frame")
        dome.Name, dome.BackgroundColor3, dome.BorderSizePixel, dome.Size, dome.ZIndex, dome.Parent = "NativeShell", CREAM, 0, UDim2.fromScale(1, 1), 28, shell
        corner(dome)
        local ds = Instance.new("UIStroke") ds.Color, ds.Thickness, ds.Parent = Color3.fromRGB(160, 118, 62), 4, dome
        local hollow = Instance.new("Frame")
        hollow.BackgroundColor3, hollow.BorderSizePixel, hollow.AnchorPoint, hollow.Position, hollow.Size, hollow.ZIndex, hollow.Parent = Color3.fromRGB(246, 214, 150), 0, Vector2.new(.5, .5), UDim2.fromScale(.5, .6), UDim2.fromScale(.74, .48), 29, dome
        corner(hollow)
        local gloss = Instance.new("Frame")
        gloss.BackgroundColor3, gloss.BackgroundTransparency, gloss.BorderSizePixel, gloss.Position, gloss.Size, gloss.ZIndex, gloss.Parent = WHITE, .2, 0, UDim2.fromOffset(14, 5), UDim2.fromOffset(26, 8), 30, dome
        corner(gloss)
        local img = Instance.new("ImageLabel")
        img.Name, img.BackgroundTransparency, img.AnchorPoint, img.Position, img.Size, img.ZIndex, img.Visible = "ShellImage", 1, Vector2.new(.5, .5), UDim2.fromScale(.5, .5), UDim2.fromOffset(110, 110), 28, false
        img.Parent = shell
        shells[i], domes[i], shellImages[i] = shell, dome, img
    end
    local image = Instance.new("ImageLabel")
    image.Name, image.BackgroundTransparency, image.AnchorPoint, image.Visible, image.ZIndex = "SplatImage", 1, Vector2.new(.5, .5), false, 25
    image.Size, image.Parent = UDim2.fromOffset(260, 260), group
    return {group = group, puddle = puddle, lobes = lobes, yolk = yolk, drips = drips, shells = shells, domes = domes, shellImages = shellImages, image = image}
end

-- BD-1067: put the two effect layers over the card. The body is at its home (anchor top-left) when a hatch starts; its screen position, taken back
-- through the panel's own scale, is the layer position in panel units. `fit` (and the scroller's own scale) shrinks the effects with the card. Desktop: (18, 98) and 1, as before.
local function placeLayers(fx: Layers, panel: GuiObject, body: GuiObject, fit: number)
    local panelPx = if panel.Size.X.Offset > 0 and panel.AbsoluteSize.X > 0 then panel.AbsoluteSize.X / panel.Size.X.Offset else 1
    local x = math.round((body.AbsolutePosition.X - panel.AbsolutePosition.X) / panelPx * 100) / 100
    local y = math.round((body.AbsolutePosition.Y - panel.AbsolutePosition.Y) / panelPx * 100) / 100
    if panel.AbsoluteSize.X <= 0 then x, y = BODY_HOME.X, BODY_HOME.Y end
    -- the phone scroller has its own fit scale between the panel and the body: the layers need the same screen size per design px as the card
    local rel = if body.Size.X.Offset > 0 and body.AbsoluteSize.X > 0 then body.AbsoluteSize.X / body.Size.X.Offset / panelPx else 1
    for _, f in {fx.back, fx.front} do
        f.Position = UDim2.fromOffset(x, y)
        local s = f:FindFirstChild("HatchFit")
        if s then (s :: UIScale).Scale = math.round(fit * rel * 10000) / 10000 end
    end
end

local function ensureLayers(panel: GuiObject): Layers
    local existing = layers
    if existing and existing.back.Parent == panel and existing.front.Parent == panel then return existing end
    if existing then existing.back:Destroy() existing.front:Destroy() end
    local function layer(name: string, z: number): Frame
        local f = Instance.new("Frame")
        f.Name, f.BackgroundTransparency, f.ClipsDescendants, f.Active = name, 1, true, false
        f.Position, f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(BODY_HOME.X, BODY_HOME.Y), UDim2.fromOffset(824, 402), z, panel
        local fitScale = Instance.new("UIScale") -- BD-1067: set by placeLayers; 1 on every desktop-sized window
        fitScale.Name, fitScale.Parent = "HatchFit", f
        return f
    end
    local back, front = layer("HatchFxBack", 22), layer("HatchFxFront", 24)
    local backdrop = Instance.new("Frame")
    backdrop.Name, backdrop.BorderSizePixel, backdrop.BackgroundTransparency, backdrop.Size, backdrop.ZIndex, backdrop.Parent = "Backdrop", 0, 1, UDim2.fromScale(1, 1), 22, back
    local rings, ringScales, rays, motes, podium, particles, fw, rain, arcs = {}, {}, {}, {}, {}, {}, {}, {}, {}
    -- Radial gradient: stacked translucent circles, bright centre fading to the dark backdrop vignette.
    for i = 1, RING_N do
        local size = 120 + (i - 1) * 92
        local ring = dot(back, "GlowRing" .. i, 22, size, size, true)
        ring.Visible, ring.Position = true, UDim2.fromOffset(CENTER_DINO.X, CENTER_DINO.Y)
        local s = Instance.new("UIScale") s.Parent = ring
        rings[i], ringScales[i] = ring, s
    end
    for i = 1, RAY_N do
        local ray = dot(back, "LightRay" .. i, 22, 78, 760, false)
        ray.Visible, ray.BackgroundTransparency, ray.Position = true, 1, UDim2.fromOffset(CENTER_DINO.X, CENTER_DINO.Y)
        local g = Instance.new("UIGradient")
        g.Rotation = 90
        g.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(.5, .1), NumberSequenceKeypoint.new(1, 1)})
        g.Parent = ray
        rays[i] = ray
    end
    for i = 1, MOTE_N do motes[i] = dot(back, "Mote" .. i, 22, 6 + (i % 4) * 2, 6 + (i % 4) * 2, true) end
    for i, size in {{330, 46}, {220, 28}} do
        local p = dot(back, "Podium" .. i, 22, size[1], size[2], true)
        p.Visible, p.Position = true, UDim2.fromOffset(CENTER_DINO.X, FxPlan.Card.dino.h - 10) -- BD-1073: the plinth sits just under the dinosaur's feet
        podium[i] = p
    end
    local total = Timeline.MaxParticles + Timeline.OrbitMax
    for i = 1, total do particles[i] = dot(front, "Sparkle" .. i, 24, 10, 10, i % 2 == 0) if i % 2 == 1 then particles[i].Rotation = 45 end end
    for i = 1, Timeline.FireworkMax do fw[i] = dot(front, "Firework" .. i, 24, 9, 9, true) end
    for i = 1, Timeline.RainMax do rain[i] = dot(front, "Rain" .. i, 24, 8, 8, false) rain[i].Rotation = 45 end
    local shocks, shockStrokes, shockScales = {}, {}, {}
    for i = 1, 2 do
        local s = dot(front, "Shockwave" .. i, 24, 300, 300, true)
        local stroke = Instance.new("UIStroke") stroke.Thickness, stroke.Transparency, stroke.Parent = 8, 1, s
        local scale = Instance.new("UIScale") scale.Parent = s
        shocks[i], shockStrokes[i], shockScales[i] = s, stroke, scale
    end
    for i = 1, ARC_N do arcs[i] = dot(front, "EnergyArc" .. i, 24, 76, 5, true) end
    local shimmer = dot(front, "ShinyShimmer", 25, 440, 300, false)
    shimmer.Position, shimmer.BackgroundColor3 = UDim2.fromOffset(CENTER_DINO.X, CENTER_DINO.Y), WHITE
    local sg = Instance.new("UIGradient")
    sg.Rotation = 25
    sg.Color = ColorSequence.new({ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 80, 120)), ColorSequenceKeypoint.new(.25, Color3.fromRGB(255, 220, 80)),
        ColorSequenceKeypoint.new(.5, Color3.fromRGB(80, 255, 160)), ColorSequenceKeypoint.new(.75, Color3.fromRGB(80, 170, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(200, 100, 255))})
    sg.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(.38, 1), NumberSequenceKeypoint.new(.5, .35),
        NumberSequenceKeypoint.new(.62, 1), NumberSequenceKeypoint.new(1, 1)})
    sg.Parent = shimmer
    local created: Layers = {paint = buildPaint(front), splat = buildSplat(front), back = back, front = front, backdrop = backdrop, rings = rings, ringScales = ringScales, rays = rays, motes = motes, podium = podium,
        particles = particles, fw = fw, rain = rain, shocks = shocks, shockStrokes = shockStrokes, shockScales = shockScales, arcs = arcs,
        shimmer = shimmer, shimmerGradient = sg}
    layers = created
    return created
end

local function fadeLabel(label: GuiObject, delay: number, seconds: number, rise: number)
    local stroke = label:FindFirstChildOfClass("UIStroke")
    local base = label.Position
    label.Visible = true
    task.delay(delay, function()
        if not label.Parent then return end
        local info = TweenInfo.new(seconds, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
        local goals: {[string]: any} = {TextTransparency = 0, TextStrokeTransparency = 0}
        if rise ~= 0 then label.Position = base + UDim2.fromOffset(0, rise) goals.Position = base end
        TweenService:Create(label, info, goals):Play()
        if stroke then TweenService:Create(stroke, info, {Transparency = 0}):Play() end
    end)
end
local function hideLabel(label: TextLabel)
    label.TextTransparency, label.TextStrokeTransparency = 1, 1
    local stroke = label:FindFirstChildOfClass("UIStroke")
    if stroke then stroke.Transparency = 1 end
end

-- Tilted ribbon tag with a diamond icon and a glowing outline (not a button). BD-1107: its size, tilt and words come from HatchTagLayout (measured at the
-- 14 px floor of this window): the word is a fixed size (never shrunk to fit, which cannot go under its minimum and ran out of the tag).
local function ribbon(parent: GuiObject, color: Color3, p: TagLayout.Placed): (Frame, UIScale, UIStroke)
    local f = Instance.new("Frame")
    f.Name, f.BackgroundColor3, f.AnchorPoint, f.Visible, f.Rotation = "Ribbon", WHITE, Vector2.new(.5, .5), false, p.tilt
    f.Position, f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(p.cx, p.cy), UDim2.fromOffset(p.w, p.h), parent.ZIndex + 6, parent
    local rc = Instance.new("UICorner") rc.CornerRadius = Chip.radius() rc.Parent = f -- BD-1070: the chunky tag corner, never a full-round pill
    local g = Instance.new("UIGradient")
    g.Rotation = 90
    g.Color = ColorSequence.new(color:Lerp(WHITE, .35), color:Lerp(Color3.new(0, 0, 0), .3))
    g.Parent = f
    local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = color:Lerp(WHITE, .6), 4, f
    local icon = Instance.new("Frame")
    icon.BackgroundColor3, icon.BorderSizePixel, icon.AnchorPoint, icon.Rotation = WHITE, 0, Vector2.new(.5, .5), 45
    icon.Position, icon.Size, icon.ZIndex, icon.Parent = UDim2.fromOffset(24, p.h / 2), UDim2.fromOffset(16, 16), f.ZIndex + 1, f
    local label = Instance.new("TextLabel")
    label.BackgroundTransparency, label.Position, label.Size, label.Font, label.Text = 1, UDim2.fromOffset(TagLayout.Ribbon.icon, 2), UDim2.new(1, -(TagLayout.Ribbon.icon + TagLayout.Ribbon.right), 1, -4), Enum.Font.FredokaOne, p.text
    label.TextColor3, label.TextScaled, label.TextSize, label.ZIndex, label.TextStrokeTransparency, label.TextStrokeColor3 = WHITE, false, p.size, f.ZIndex + 1, 0, Color3.new(0, 0, 0)
    label.TextWrapped, label.TextTruncate = false, Enum.TextTruncate.AtEnd -- the words were measured: the ellipsis is only a net under a font wider than the estimate
    label.Parent = f
    local scale = Instance.new("UIScale") scale.Scale, scale.Parent = 0, f
    return f, scale, stroke
end

-- What the server committed for this egg (never changed here). Supplied at start for a known egg, or later through handle.supply().
export type Result = {
    dino: GuiObject, rarity: number, color: Color3, failed: boolean, shiny: boolean, big: boolean,
    speciesId: string?, mutationName: string?, mutationColor: Color3?, mutationId: string?, remaining: number,
    genes: any?, colorReveal: any?, secondReveal: any?, patternReveal: any?, paintColors: {Color3}?,
}
export type Args = {
    gui: ScreenGui, panel: GuiObject, body: GuiObject,
    eggView: GuiObject, animateEgg: (number) -> (), splitEgg: (boolean?) -> (), paint: any,
    nameLabel: TextLabel, oddsLabel: TextLabel, detailLabel: TextLabel,
    motion: boolean,
    alive: () -> boolean, flash: (Color3, number) -> (),
    onNext: () -> (), onSkipAll: () -> (), onReveal: () -> (), onAgain: (() -> ())?,
    header: GuiObject?, -- BD-1019: the menu header strip (X lives there): the tap catcher starts below it
    onAbort: (() -> ())?, -- BD-1019: the menu was closed (X, tap outside, Escape) before the player continued: nothing more is coming from this egg
    result: Result?, -- nil = Open was just pressed and the server answer has not arrived: the egg already wobbles (BD-170)
    eggCondition: string?, -- BD-223: condition id of the egg being opened (client queue), shown from the first frame
    eggId: string?, -- BD-397: seeds the v2 paint splats (same egg -> same splashes)
}
export type Handle = {cancel: () -> (), supply: (Result) -> (), pending: () -> boolean, setRemaining: (number) -> ()}

-- Returns {cancel, supply, pending}. onNext runs once after the player taps on the revealed egg.
function Seq.play(args: Args): Handle
    local a: any = args -- result fields are merged in by applyResult
    local motion = a.motion
    local state = Timeline.new(motion, 1, false, a.result == nil)
    local bodyHomePos, bodyHomeAnchor = a.body.Position, a.body.AnchorPoint
    -- BD-1067: the card sits where Bootstrap / ModalCompact put the body: (18, 98) in the desktop panel, (4, 0) in the phone scroller, and the camera
    -- moves (anchor in the middle) used to assume (18, 98) always, which pushed the whole card 98 px down in a small window. The body is also shrunk,
    -- from its top-left corner, when the visible area is smaller than the card (848 x 423 shows 357 px of the 389 it needs). Desktop: fit = 1, same numbers.
    local home = BODY_HOME
    if bodyHomePos.X.Scale == 0 and bodyHomePos.Y.Scale == 0 and bodyHomeAnchor.X == 0 and bodyHomeAnchor.Y == 0 then home = Vector2.new(bodyHomePos.X.Offset, bodyHomePos.Y.Offset) end
    local fit = 1
    local screenScale = 1 -- screen px per design px of the card (BD-1107: the 14 px text floor of the tags in design px)
    local oldFit = a.body:FindFirstChild("HatchBodyFit") -- a UIScale left by the egg before: measure the body at its own size
    if oldFit then oldFit:Destroy() end
    local holder = a.body.Parent
    local bodyPx = a.body.AbsoluteSize
    if holder and holder:IsA("GuiObject") and bodyPx.X > 0 and bodyPx.Y > 0 and a.body.Size.X.Offset > 0 then
        local px = bodyPx.X / a.body.Size.X.Offset -- screen px per design px
        fit = math.min(1, (holder.AbsoluteSize.X - home.X * px) / bodyPx.X, (holder.AbsoluteSize.Y - home.Y * px) / bodyPx.Y)
        fit = math.clamp(fit, .5, 1)
        screenScale = px * fit
    end
    local bodyCenter = home + (BODY_CENTER - BODY_HOME) * fit
    local fx = ensureLayers(a.panel)
    placeLayers(fx, a.panel, a.body, fit) -- the effect layers sit exactly over the card (they used to assume the desktop home)
    local kit = fx.paint
    -- BD-397: the v2 3D egg (flag on AND its mesh loaded); otherwise everything below is the shipped v1 look.
    local v2 = if V2Assets.enabled(Config, RunService:IsStudio() and game.GameId == 0) then EggV2.create(fx.back, fx.front, motion) else nil
    if v2 then Timeline.useV2(state, true) end
    local durs = state.durs
    local mr: any = nil -- BD-162: mutation reveal burst, created when the result names an event mutation
    local hx = HatchFx.begin(HatchFx.ensure(fx.back, fx.front), motion) -- layered 2D polish (bloom, rim sparks, puffs, motes, droplets)
    -- Result-dependent values. Neutral until applyResult() runs (Open pressed, server answer on its way).
    local rarity, failed = 1, false
    local TEAL = Color3.fromRGB(70, 205, 170)
    local glow = TEAL
    local strength = .81
    local esc = Timeline.escalation(1, motion)
    local count, orbit = 0, 0
    local palette: {Color3} = {glow, WHITE}
    local cues: {{t: number, name: string}} = {}
    local cueIndex = 1
    local punchStart = 1 + esc.punch
    local connections: {RBXScriptConnection} = {}
    local finished = false
    local inspect: InspectView.Handle? = nil -- BD-149: drag to turn the revealed dino (never eats the continue tap)

    a.eggView.AnchorPoint = Vector2.new(.5, .5)
    a.eggView.Position = UDim2.fromOffset(CENTER_EGG.X, CENTER_EGG.Y)
    if v2 then a.eggView.Visible = false end -- the 2D egg only comes back for its shell fragments at the burst
    local eggZoom = Instance.new("UIScale") eggZoom.Parent = a.eggView
    local dinoScale: UIScale? = nil
    local bodyScale = Instance.new("UIScale") bodyScale.Name, bodyScale.Scale, bodyScale.Parent = "HatchBodyFit", fit, a.body
    if motion then
        a.body.AnchorPoint, a.body.Position = Vector2.new(.5, .5), UDim2.fromOffset(bodyCenter.X, bodyCenter.Y)
    end

    local nameStroke = a.nameLabel:FindFirstChildOfClass("UIStroke")
    local nameBase = {pos = a.nameLabel.Position, size = a.nameLabel.Size, align = a.nameLabel.TextXAlignment} -- BD-1107: the box Bootstrap gave it (the class badge moves it)
    local classBadge: Frame? = nil -- built in applyResult, shown with the name
    for _, l in {a.nameLabel, a.oddsLabel, a.detailLabel} do hideLabel(l) end
    local pill = Instance.new("Frame")
    pill.Name, pill.AnchorPoint, pill.Visible = "RarityPill", Vector2.new(.5, .5), false
    pill.Position, pill.Size, pill.ZIndex, pill.Parent = UDim2.fromOffset(412, 302), UDim2.fromOffset(380, 32), a.oddsLabel.ZIndex - 1, a.body
    Chip.apply(pill, glow:Lerp(Color3.new(0, 0, 0), .4), nil) -- BD-1070: the rarity line sits on a chunky tag (rounded rectangle, dark outline), not a round pill
    local pillScale = Instance.new("UIScale") pillScale.Scale, pillScale.Parent = 0, pill
    -- Shine sweep across the name (clipped strip, one tween per egg).
    local sweepClip = Instance.new("Frame")
    sweepClip.Name, sweepClip.BackgroundTransparency, sweepClip.ClipsDescendants, sweepClip.AnchorPoint = "NameShine", 1, true, Vector2.new(.5, 0)
    sweepClip.Position, sweepClip.Size, sweepClip.ZIndex, sweepClip.Parent = UDim2.fromOffset(412, 236), UDim2.fromOffset(360, 54), a.nameLabel.ZIndex + 2, a.body
    local sweep = Instance.new("Frame")
    sweep.BackgroundColor3, sweep.BorderSizePixel, sweep.Rotation, sweep.Visible = WHITE, 0, 18, false
    sweep.Position, sweep.Size, sweep.ZIndex, sweep.Parent = UDim2.fromOffset(-90, -10), UDim2.fromOffset(50, 90), sweepClip.ZIndex, sweepClip
    local sg = Instance.new("UIGradient")
    sg.Rotation = 0
    sg.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(.5, .35), NumberSequenceKeypoint.new(1, 1)})
    sg.Parent = sweep

    -- Ribbons (Shiny / BIG / mutation, created once the result is known) and the tap hint.
    local badges: {{any}} = {}
    local pulseStrokes: {UIStroke} = {}
    local function addRibbon(color: Color3, p: TagLayout.Placed)
        local f, s, st = ribbon(a.body, color, p)
        table.insert(badges, {f, s}) table.insert(pulseStrokes, st)
    end
    local hint = Instance.new("TextLabel")
    hint.Name, hint.BackgroundTransparency, hint.Position, hint.Size = "TapHint", 1, UDim2.fromOffset(152, 350), UDim2.fromOffset(520, 46)
    hint.Font, hint.TextColor3, hint.TextScaled, hint.Text = Enum.Font.FredokaOne, WHITE, true, Timeline.hint(0)
    hint.TextStrokeTransparency, hint.TextStrokeColor3, hint.ZIndex, hint.Visible = 0, Theme.Colors.outline, a.body.ZIndex + 6, false
    hint.Parent = a.body
    local hintLimit = Instance.new("UITextSizeConstraint") hintLimit.MaxTextSize, hintLimit.MinTextSize, hintLimit.Parent = 34, 14, hint

    -- Tap target over the card body plus a small "Skip all" while more eggs wait. Taps are ignored until the result is in.
    -- BD-1019: the catcher covers the card body only (ModalClose.hatchZone), so X, DONE / TRY AGAIN and the dark backdrop get their own taps.
    local zone = ModalClose.hatchZone(a.gui, a.panel, a.header, a.body)
    local overlay, layer = zone.overlay, zone.layer
    local readyClock: number? = nil -- when the tap hint appeared (a tap outside the card cannot close the dino for the first ReadyGrace seconds)
    local outsideFn: () -> boolean = function() return true end -- the backdrop-tap decision, set below once the sequence state exists
    local skipButton: TextButton? = nil
    -- BD-444: "Egg N of M" counter, hidden for a single egg. BD-1073: it lives in the header strip, left of the X (it used to lie over the dinosaur's
    -- head in the body). The header outlives this egg, so finish() removes the counter. Without a header it falls back to the top of the body.
    local counter = Instance.new("TextLabel")
    counter.Name, counter.BackgroundTransparency, counter.Visible = "EggCounter", 1, false
    if a.header then
        local closeWidth = 80
        for _, c in a.header:GetChildren() do
            if c:IsA("TextButton") and c.Text == "X" then closeWidth = c.Size.X.Offset + 2 end
        end
        counter.AnchorPoint, counter.Position, counter.Size = Vector2.new(1, .5), UDim2.new(1, -(closeWidth + FxPlan.Card.counterGap), .5, 0), UDim2.fromOffset(220, 40)
        counter.ZIndex, counter.Parent = a.header.ZIndex + 3, a.header
    else
        counter.AnchorPoint, counter.Position, counter.Size = Vector2.new(.5, 0), UDim2.fromOffset(412, 8), UDim2.fromOffset(260, 40)
        counter.ZIndex, counter.Parent = a.body.ZIndex + 6, a.body
    end
    counter.Font, counter.TextSize, counter.TextColor3, counter.Text = Enum.Font.FredokaOne, 28, WHITE, ""
    counter.TextXAlignment = Enum.TextXAlignment.Right
    counter.TextStrokeTransparency, counter.TextStrokeColor3 = 0, Theme.Colors.outline

    -- Pooled effects start neutral; applyResult() tints them for the egg.
    for i, ring in fx.rings do
        ring.BackgroundColor3 = glow:Lerp(WHITE, (1 - (i - 1) / (RING_N - 1)) * .5)
        ring.BackgroundTransparency = 1
        fx.ringScales[i].Scale = .6
    end
    fx.backdrop.BackgroundTransparency = 1
    for i, ray in fx.rays do
        ray.BackgroundColor3, ray.BackgroundTransparency = glow:Lerp(WHITE, .4), 1
        ray.Size = UDim2.fromOffset(if i <= 3 then 90 else 56, 760)
    end
    local mx, my, ms, mp = table.create(MOTE_N, 0), table.create(MOTE_N, 0), table.create(MOTE_N, 0), table.create(MOTE_N, 0)
    for i, m in fx.motes do
        mx[i], my[i], ms[i], mp[i] = 40 + (i * 67) % 744, (i * 131) % 402, 14 + (i * 7) % 22, i * 1.7
        m.BackgroundColor3, m.BackgroundTransparency, m.Visible = glow:Lerp(WHITE, .5), 1, motion
    end
    for i, p in fx.podium do p.BackgroundColor3, p.BackgroundTransparency = glow:Lerp(WHITE, if i == 1 then .1 else .4), 1 end
    for _, f in fx.particles do f.Visible = false end
    for _, f in fx.fw do f.Visible = false end
    for _, f in fx.rain do f.Visible = false end
    for _, f in fx.arcs do f.Visible = false end
    fx.shimmer.Visible = false
    local splat = fx.splat
    local useSplatImage, useShellImage = Theme.ImageIds.egg_splat ~= "", Theme.ImageIds.egg_shell ~= ""
    splat.group.GroupTransparency, splat.image.Image = 0, Theme.ImageIds.egg_splat
    for _, f in {splat.puddle, splat.yolk, splat.image} do f.Visible = false end
    for _, f in splat.lobes do f.Visible = false end
    for _, f in splat.drips do f.Visible = false end
    for i, f in splat.shells do
        f.Visible, f.Rotation = false, 0
        splat.domes[i].Visible, splat.shellImages[i].Visible, splat.shellImages[i].Image = not useShellImage, useShellImage, Theme.ImageIds.egg_shell
        splat.shellImages[i].Rotation = if i == 2 then 14 else 0
    end
    for i, s in fx.shocks do s.Visible, fx.shockStrokes[i].Color, fx.shockStrokes[i].Transparency = false, glow:Lerp(WHITE, .3), 1 end
    for i = 1, 2 do
        kit.buckets[i].Visible, kit.streams[i].Visible, kit.splashes[i].Visible, kit.chips[i].Visible = false, false, false, false
        kit.chipScales[i].Scale = 0
    end
    kit.patternChip.Visible, kit.patternScale.Scale, kit.conditionChip.Visible = false, 0, false
    for _, d in kit.drops do d.Visible = false end

    local px, py, vx, vy, life = table.create(Timeline.MaxParticles, 0), table.create(Timeline.MaxParticles, 0), table.create(Timeline.MaxParticles, 0), table.create(Timeline.MaxParticles, 0), table.create(Timeline.MaxParticles, 0)
    local burstDone, revealStarted, readyShown, bodyRestored = false, false, false, false
    local tweenHint: Tween? = nil
    local impactAt = .95
    local level = 0 -- overall glow level 0..1
    local revealT = 0 -- seconds after the burst when the dinosaur actually appeared
    local chipShown = {false, false, false}
    local dropN = {0, 0}
    local lastWash = {-1, -1, -1}
    local paintColors: {Color3} = {WHITE, WHITE}

    local function restoreBody()
        a.body.AnchorPoint, a.body.Position = bodyHomeAnchor, bodyHomePos
        bodyScale.Scale = fit
    end
    local function hidePaint()
        for i = 1, 2 do
            kit.buckets[i].Visible, kit.streams[i].Visible, kit.splashes[i].Visible, kit.chips[i].Visible = false, false, false, false
        end
        kit.patternChip.Visible, kit.conditionChip.Visible = false, false
        for _, d in kit.drops do d.Visible = false end
    end
    local function finish()
        if finished then return end
        finished = true
        for _, c in connections do c:Disconnect() end
        table.clear(connections)
        if tweenHint then tweenHint:Cancel() tweenHint = nil end
        if inspect then inspect.destroy() inspect = nil end
        restoreBody()
        HatchFx.hide(hx)
        MutationReveal.hide(mr)
        if v2 then EggV2.stop(v2) end
        if classBadge then classBadge:Destroy() classBadge = nil end
        zone.destroy()
        if counter.Parent then counter:Destroy() end -- it lives in the header, which outlives this egg
        ModalClose.clearOutside(outsideFn)
        if fx.back.Parent then
            fx.backdrop.BackgroundTransparency = 1
            for _, f in fx.rings do f.BackgroundTransparency = 1 end
            for _, f in fx.rays do f.BackgroundTransparency = 1 end
            for _, f in fx.motes do f.Visible = false end
            for _, f in fx.podium do f.BackgroundTransparency = 1 end
            for _, f in fx.particles do f.Visible = false end
            for _, f in fx.fw do f.Visible = false end
            for _, f in fx.rain do f.Visible = false end
            for _, f in fx.arcs do f.Visible = false end
            for _, f in fx.shocks do f.Visible = false end
            fx.shimmer.Visible = false
            for _, f in {fx.splat.puddle, fx.splat.yolk, fx.splat.image} do f.Visible = false end
            for _, f in fx.splat.lobes do f.Visible = false end
            for _, f in fx.splat.drips do f.Visible = false end
            for _, f in fx.splat.shells do f.Visible = false end
            hidePaint()
        end
    end

    local function setGlow(l: number)
        level = l
        local t = 1 - .16 * l * strength
        for _, ring in fx.rings do ring.BackgroundTransparency = t end
        fx.backdrop.BackgroundTransparency = 1 - .55 * l
    end

    -- Poses the pooled splat kit for `since` seconds after the burst (pure curves from HatchTimeline; no Instances created).
    local function applySplat(since: number)
        for i, shell in splat.shells do
            local dx, dy, rot = Timeline.shell(since, if i == 1 then -1 else 1, SHELL_FALL)
            shell.Position, shell.Rotation, shell.Visible = UDim2.fromOffset(CENTER_EGG.X + dx, SHELL_START_Y + dy), rot, true
        end
        local lift, ysx, ysy = Timeline.yolk(since)
        local pw, ph = Timeline.puddle(since)
        local landed = since >= Timeline.SplatDrop
        if useSplatImage then
            splat.image.Visible = landed
            -- Square canvas (art is ~76% of 1024 px and centred): never stretched at rest; squash only while wobbling.
            splat.image.Position = UDim2.fromOffset(PUDDLE.X, PUDDLE.Y - 42)
            splat.image.Size = UDim2.fromOffset(260 * pw * (1 + (ysx - 1) * .2), 260 * ph * (1 + (ysy - 1) * .2))
        else
            local puddle = splat.puddle
            puddle.Visible = pw > 0
            puddle.Position, puddle.Size = UDim2.fromOffset(PUDDLE.X, PUDDLE.Y), UDim2.fromOffset(250 * pw, 66 * ph)
            local l1, l2 = splat.lobes[1], splat.lobes[2]
            l1.Visible, l2.Visible = pw > 0, pw > 0
            l1.Position, l1.Size = UDim2.fromOffset(PUDDLE.X - 112 * pw, PUDDLE.Y + 6), UDim2.fromOffset(80 * pw, 30 * ph)
            l2.Position, l2.Size = UDim2.fromOffset(PUDDLE.X + 120 * pw, PUDDLE.Y + 4), UDim2.fromOffset(64 * pw, 26 * ph)
        end
        local yolk = splat.yolk
        yolk.Visible = not (useSplatImage and landed)
        yolk.Position, yolk.Size = UDim2.fromOffset(PUDDLE.X, YOLK_REST + lift), UDim2.fromOffset(74 * ysx, 62 * ysy)
        for i, drip in splat.drips do
            local dy, alpha = Timeline.drip(since, i)
            drip.Visible = dy ~= nil and not useSplatImage
            if dy and alpha then
                drip.Position, drip.BackgroundTransparency = UDim2.fromOffset(PUDDLE.X + (if i == 1 then -70 else 84), PUDDLE.Y + 14 + dy * .45), .15 + .85 * (1 - alpha)
            end
        end
    end

    -- BD-223: the egg's condition look and chip from the first frame (queue id now; the server answer replaces it).
    local conditionId: string? = nil
    local function setCondition(id: string?)
        if id == conditionId or burstDone then return end
        conditionId = id
        HatchFx.rainbow(hx, id == "rainbow") -- BD-1072: soft rainbow rings and rainbow sparks behind a Rainbow egg
        a.paint.setCondition(id)
        if v2 then EggV2.setCondition(v2, id) end -- v2: the overlay fades in at the condition beat, the chip is shown at once
        local text = Timeline.conditionChip(if id then EggGenetics.condition(id) else nil)
        kit.conditionChip.Visible = text ~= nil
        if text then
            kit.conditionLabel.Text = text
            kit.conditionChip.BackgroundColor3 = conditionFill(id) -- BD-1070: the chip's palette fill (its outline stays the dark chunky outline)
        end
    end
    -- BD-220 paint buckets: pose, pour stream, splash ring and droplets of both buckets; ONE colour chip under each bucket.
    local function showChip(i: number)
        local reveal = if i == 1 then a.colorReveal else (a.secondReveal or a.colorReveal)
        if not reveal then return end
        local chip = kit.chips[i]
        kit.chipLabels[i].Text = reveal.name
        kit.chipBadgeLabels[i].Text = string.upper(reveal.tierName)
        kit.chipBadges[i].BackgroundColor3 = TIER_COLORS[reveal.tier] or WHITE
        -- BD-1069: the swatch is the named colour's own palette rgb (EggColors), never the shell tint or a blend (a Cream chip showed a green dot)
        local rgb = Timeline.revealRgb(reveal)
        kit.chipSwatches[i].BackgroundColor3 = if rgb then Chip.color(rgb) else paintColors[i]
        chip.Visible = true
        TweenService:Create(kit.chipScales[i], TweenInfo.new(.28, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play()
        if reveal.tier >= 4 then
            Sfx.play(Sfx.revealName(math.clamp(reveal.tier - 1, 1, 5))) -- Epic and above get the rarity sting
            if reveal.tier >= 5 then a.flash(TIER_COLORS[reveal.tier] or WHITE, .12) end
        end
    end
    local function updatePaint(t: number)
        local ps = Timeline.paintState(durs, t)
        for i = 1, 2 do
            local side = if i == 1 then -1 else 1
            local b = if i == 1 then ps.left else ps.right
            local bucket, stream = kit.buckets[i], kit.streams[i]
            if v2 then
                -- BD-397: the 3D buckets, liquid arc, crown and drips are drawn by HatchEggV2; only the chips remain here.
                if b.impacted and not chipShown[i] then chipShown[i] = true showChip(i) end
                continue
            end
            local x, y, rot, alpha = Timeline.bucketPose(b.k, side)
            local show = b.k > 0 and b.k < 1
            bucket.Visible = show
            stream.Visible = false
            if show then
                bucket.Position, bucket.Rotation, bucket.GroupTransparency = UDim2.fromOffset(CENTER_EGG.X + x, CENTER_EGG.Y + y), rot, 1 - alpha
                -- Pour stream: grows from the tilted rim to the egg, thins out just after the splash.
                local grow = math.clamp((b.k - .46) / .14, 0, 1)
                local thin = 1 - math.clamp((b.k - (Timeline.Paint.impact + .04)) / .12, 0, 1)
                if grow > 0 and thin > 0 then
                    local rr = math.rad(rot)
                    local lx, ly = -side * 34, -22
                    local lipX = CENTER_EGG.X + x + lx * math.cos(rr) - ly * math.sin(rr)
                    local lipY = CENTER_EGG.Y + y + lx * math.sin(rr) + ly * math.cos(rr)
                    local target = SPLASH_POINTS[i]
                    local dx, dy = target.X - lipX, target.Y - lipY
                    stream.Visible = true
                    stream.BackgroundColor3 = paintColors[i]
                    stream.Position, stream.Size, stream.Rotation = UDim2.fromOffset(lipX, lipY), UDim2.fromOffset(9 * thin, math.sqrt(dx * dx + dy * dy) * grow), math.deg(math.atan2(-dx, dy))
                end
            end
            local since = b.sinceImpact
            local ring = kit.splashes[i]
            if b.impacted and since < .5 then
                local sc, tr = Timeline.splash(since)
                ring.Visible = true
                ring.Position = UDim2.fromOffset(SPLASH_POINTS[i].X, SPLASH_POINTS[i].Y)
                kit.splashScales[i].Scale, kit.splashStrokes[i].Transparency = sc, tr
            elseif ring.Visible then
                ring.Visible = false
            end
            HatchFx.splash(hx, i, SPLASH_POINTS[i].X, SPLASH_POINTS[i].Y, if b.impacted then since else nil)
            for j = 1, 10 do
                local d = kit.drops[(i - 1) * 10 + j]
                local dx, dy, tr = Timeline.drop(j, 10, since, side)
                if b.impacted and tr < 1 and j <= dropN[i] then
                    d.Visible = true
                    d.Position, d.BackgroundTransparency = UDim2.fromOffset(SPLASH_POINTS[i].X + dx, SPLASH_POINTS[i].Y + dy), tr
                elseif d.Visible then
                    d.Visible = false
                end
            end
            if b.impacted and not chipShown[i] then
                chipShown[i] = true
                showChip(i)
            end
        end
        if not v2 then -- v2 paints the 3D egg's texture itself (the hidden 2D egg only tints for its burst fragments)
            if ps.left.wash ~= lastWash[1] then lastWash[1] = ps.left.wash a.paint.color(ps.left.wash) end
            if ps.right.wash ~= lastWash[2] then lastWash[2] = ps.right.wash a.paint.second(ps.right.wash) end
            if ps.pattern ~= lastWash[3] then lastWash[3] = ps.pattern a.paint.pattern(ps.pattern) end
        end
        local pattern = a.patternReveal
        if ps.patternShown and not chipShown[3] and pattern then
            chipShown[3] = true
            kit.patternLabel.Text = Timeline.patternLabel(pattern)
            kit.patternChip.BackgroundColor3 = TIER_COLORS[pattern.tier] or CHIP_FILL -- BD-1070: the tier is the chip's palette fill
            kit.patternChip.Visible = true
            TweenService:Create(kit.patternScale, TweenInfo.new(.25, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play()
        end
    end

    local function burst()
        burstDone = true
        a.eggView.Rotation = 0
        eggZoom.Scale = 1
        hidePaint()
        a.paint.finish() -- fast-forwarded or Reduced Motion: the egg shows its final colour and pattern before it opens
        if v2 then EggV2.burst(v2) a.eggView.Visible = true end -- the 3D egg leaves; the 2D shell fragments fly from the same spot
        if motion then a.body.Position = UDim2.fromOffset(bodyCenter.X, bodyCenter.Y) end
        if motion then a.animateEgg(Timeline.EggClock) end
        a.splitEgg(not failed)
        for _, f in fx.arcs do f.Visible = false end
        if failed then
            -- SPLAT: our own shell halves replace the generic flying fragments.
            a.eggView.Visible = false
            if motion then
                a.flash(CREAM, .14)
                splat.group.GroupTransparency = 0
                for _, f in splat.shells do f.Visible = true end
                splat.yolk.Visible = not useSplatImage
                splat.puddle.Visible = false
                fx.shocks[1].Visible = true
                fx.shockStrokes[1].Color = Color3.fromRGB(255, 252, 240)
                for i = 1, count do
                    local angle = -math.pi / 2 + ((i / count) - .5) * 2.6
                    local speed = 90 + (i * 37) % 130
                    px[i], py[i] = CENTER_EGG.X, CENTER_EGG.Y
                    vx[i], vy[i] = math.cos(angle) * speed, math.sin(angle) * speed - 40
                    life[i] = .6 + (i * 13 % 7) * .08
                    local size = 5 + (i * 3) % 5
                    local p = fx.particles[i]
                    p.Size, p.BackgroundColor3, p.BackgroundTransparency, p.Visible = UDim2.fromOffset(size, size), palette[i % #palette + 1], 0, true
                end
            end
            return
        end
        a.flash(glow, Timeline.burstStrength(rarity))
        if esc.fireworks then task.delay(.12, function() if not finished then a.flash(Theme.Colors.gold, .3) end end) end
        for i = 1, count do
            local angle = (i / count) * TAU + (i % 3) * .21
            local speed = (170 + (i * 37) % 210) * (1 + .07 * rarity)
            px[i], py[i] = CENTER_EGG.X, CENTER_EGG.Y
            vx[i], vy[i] = math.cos(angle) * speed, math.sin(angle) * speed - 140
            life[i] = .8 + (i * 13 % 7) * .09
            local p = fx.particles[i]
            local size = 6 + (i * 5) % 9 + (if rarity >= 4 then 3 else 0)
            p.Size, p.BackgroundColor3, p.BackgroundTransparency, p.Visible = UDim2.fromOffset(size, if i % 5 == 0 then size * 2 else size), palette[i % #palette + 1], 0, true
        end
        for i = 1, 2 do
            if (i == 1 and esc.shock) or (i == 2 and esc.arcs) then fx.shocks[i].Visible = true end
        end
    end

    local function startReveal()
        revealStarted = true
        a.onReveal()
        if not motion then HatchFx.update(hx, 0, 1, 0, not failed) end -- Reduce Motion: one static soft glow behind the dino
        MutationReveal.update(mr, 0) -- BD-162 (Reduce Motion: one still mutation-coloured glow; motion: the burst starts)
        if failed then
            local rise = if motion then 10 else 0
            fadeLabel(a.nameLabel, if motion then .25 else 0, .3, rise)
            fadeLabel(a.oddsLabel, if motion then .4 else .1, .3, rise)
            fadeLabel(a.detailLabel, if motion then .55 else .2, .3, rise)
            if not motion then
                -- Reduced Motion: a static splat that simply fades in (no shake, tumble, wobble or particles).
                splat.group.GroupTransparency = 1
                applySplat(10)
                TweenService:Create(splat.group, TweenInfo.new(.35), {GroupTransparency = 0}):Play()
            end
            return
        end
        a.dino.Visible = true
        local view = a.dino :: any
        view.ImageTransparency = 0
        if a.dino:IsA("ViewportFrame") and overlay.Parent then
            -- Drags on the tap catcher turn the dino; a press that moves under 12 px is still a tap.
            inspect = InspectView.attach(a.dino :: ViewportFrame, {surface = overlay, uiParent = layer, baseZoom = FxPlan.Card.baseZoom, -- BD-262 / BD-1073: was 1.4, which cut the head at the top of the card
                hintPosition = UDim2.fromScale(.17, .6), resetPosition = UDim2.fromScale(.72, .345)})
        end
        if not motion then
            view.ImageTransparency = 1
            TweenService:Create(view, TweenInfo.new(.3), {ImageTransparency = 0}):Play()
            setGlow(.6)
            for _, sc in fx.ringScales do sc.Scale = 1 end
            for _, p in fx.podium do p.BackgroundTransparency = .6 end
        end
        local rise = if motion then 14 else 0
        fadeLabel(a.nameLabel, if motion then .25 else 0, .3, rise)
        if classBadge then classBadge.Visible = true end -- appears with the name (no extra motion, so Reduce Motion needs nothing)
        fadeLabel(a.oddsLabel, if motion then .4 else .1, .3, rise)
        fadeLabel(a.detailLabel, if motion then .55 else .2, .3, rise)
        task.delay(if motion then .35 else .1, function()
            if finished or not pill.Parent then return end
            pill.Visible = true
            if motion then TweenService:Create(pillScale, TweenInfo.new(.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play() else pillScale.Scale = 1 end
        end)
        if motion then
            task.delay(.55, function()
                if finished or not sweep.Parent then return end
                sweep.Visible = true
                sweep.Position = UDim2.fromOffset(-90, -10)
                local t = TweenService:Create(sweep, TweenInfo.new(.7, Enum.EasingStyle.Quad, Enum.EasingDirection.InOut), {Position = UDim2.fromOffset(400, -10)})
                t.Completed:Once(function() sweep.Visible = false end)
                t:Play()
            end)
        end
        for i, entry in badges do
            local frame, scale = entry[1], entry[2]
            task.delay(if motion then .45 + i * .12 else .1, function()
                if finished or not frame.Parent then return end
                frame.Visible = true
                if motion then TweenService:Create(scale, TweenInfo.new(.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {Scale = 1}):Play() else scale.Scale = 1 end
            end)
        end
    end

    local function showHint()
        readyShown = true
        readyClock = os.clock()
        local endRow = a.body:FindFirstChild("EndButtons")
        if endRow and endRow:IsA("GuiObject") then endRow.Visible = true else hint.Visible = true end
        if endRow then return end
        if motion then
            hint.TextTransparency = 1
            TweenService:Create(hint, TweenInfo.new(.25), {TextTransparency = 0}):Play()
            task.delay(.3, function()
                if finished or not hint.Parent then return end
                local t = TweenService:Create(hint, TweenInfo.new(.8, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), {TextTransparency = .4})
                tweenHint = t
                t:Play()
            end)
        end
    end

    local function advance()
        if finished then return end
        finish()
        a.onNext()
    end
    local function onTap()
        if finished then return end
        if inspect and (inspect :: InspectView.Handle).wasDrag() then return end -- a drag turns the dino, it never advances
        if state.pending then return end -- Open was just pressed: nothing to skip yet
        if not failed and not revealStarted then return end -- never advance past an egg whose dinosaur is not shown yet
        if Timeline.tap(state) == "advance" then advance() end
    end
    overlay.Activated:Connect(onTap)
    -- A tap on the dark backdrop (BD-1019): while the egg is being built it counts like a tap on the egg (as before); once the dino has been shown for
    -- ReadyGrace seconds it is the same as X. While the answer is on its way, or the egg is cracking, it does nothing (X always works).
    outsideFn = function(): boolean
        if finished then return true end
        local since = if readyClock then os.clock() - readyClock else nil
        local action = CloseRules.outsideAction(state.pending, Timeline.phase(state.durs, state.t), since)
        if action == "tap" then onTap() end
        return action == "close"
    end
    ModalClose.setOutside(outsideFn)
    table.insert(connections, Input.InputBegan:Connect(function(input, processed)
        if processed then return end
        local k = input.KeyCode
        if k == Enum.KeyCode.Space or k == Enum.KeyCode.Return or k == Enum.KeyCode.KeypadEnter or k == Enum.KeyCode.ButtonA then onTap() end
    end))

    local function place(f: Frame, x: number, y: number) f.Position = UDim2.fromOffset(x, y) end

    -- The server answer: styles everything that depends on the egg's species, rarity, colour and pattern, then lets the build-up run on.
    local function applyResult(r: Result)
        for k, v in r :: any do a[k] = v end
        rarity = math.clamp(r.rarity, 1, 5)
        failed = r.failed
        Timeline.supply(state, rarity, failed)
        durs = state.durs
        esc = Timeline.escalation(rarity, motion)
        punchStart = 1 + esc.punch
        -- Rarity palette: Common is lively teal, then the rarity colour up to gold for Legendary.
        glow = if failed then Color3.fromRGB(255, 205, 90) elseif rarity <= 1 then TEAL else r.color
        HatchFx.style(hx, rarity, glow, failed)
        strength = .75 + .06 * rarity
        count = if failed then Timeline.crumbCount(motion) else Timeline.particleCount(rarity, r.shiny, r.big, motion, failed)
        orbit = Timeline.orbitCount(rarity, motion, failed)
        palette = if failed then {CREAM, WHITE, YOLK_GOLD, Color3.fromRGB(225, 190, 130)} else {glow, WHITE, Theme.Colors.gold, glow:Lerp(WHITE, .5), Theme.RarityColors[math.min(5, rarity + 1)]}
        if not failed and r.genes and r.genes.conditionId == "rainbow" then -- BD-1072: a Rainbow egg bursts in the soft rainbow hues
            palette = {WHITE}
            for _, hue in FxPlan.rainbowPalette() do table.insert(palette, Color3.fromRGB(hue[1], hue[2], hue[3])) end
        end
        cues = SfxRules.hatchCues(Timeline.cues(durs, rarity, failed, Sfx.revealName(rarity)), rarity) -- BD-341: staggered, no redundant cues
        cueIndex = 1
        -- BD-1073: the dinosaur view starts at the top of the card and ends where the name starts (it used to start 12 px above the card and lay under the
        -- name), and its own "BIG / SHINY" label is hidden (the ribbons say it; it sat on the plinth).
        local card = FxPlan.Card.dino
        a.dino.AnchorPoint = Vector2.new(.5, .5)
        a.dino.Position = UDim2.fromOffset(card.cx, card.cy)
        a.dino.Size = UDim2.fromOffset(card.w, card.h)
        local traitBadge = a.dino:FindFirstChild("TraitBadge")
        if traitBadge and traitBadge:IsA("GuiObject") then traitBadge.Visible = false end
        local scaleObject = Instance.new("UIScale")
        scaleObject.Scale, scaleObject.Parent = if motion then .25 else 1, a.dino
        dinoScale = scaleObject
        -- Keep the viewport visible but transparent so DinosaurPreview loads the model during the build-up.
        a.dino.Visible = not failed
        local dinoView = a.dino :: any
        dinoView.ImageTransparency = 1
        -- Name: big white fill with a thick rarity-coloured stroke. Rarity line sits on a coloured pill.
        if not failed then
            a.nameLabel.TextColor3, a.nameLabel.TextSize = WHITE, 48
            a.nameLabel.TextStrokeColor3 = glow:Lerp(Color3.new(0, 0, 0), .45)
            if nameStroke then nameStroke.Color, nameStroke.Thickness = glow:Lerp(Color3.new(0, 0, 0), .35), 5 end
            a.oddsLabel.TextColor3 = WHITE
        else
            -- Funny, not sad: warm cream title with a brown outline, soft cream lines under it (no red).
            a.nameLabel.TextColor3, a.nameLabel.TextStrokeColor3 = Color3.fromRGB(255, 236, 150), Color3.fromRGB(110, 70, 15)
            if nameStroke then nameStroke.Color, nameStroke.Thickness = Color3.fromRGB(110, 70, 15), 5 end
            a.oddsLabel.TextColor3, a.detailLabel.TextColor3 = WHITE, Color3.fromRGB(255, 226, 140)
        end
        if classBadge then classBadge:Destroy() classBadge = nil end
        -- BD-1107 / BD-1097: the name label goes back to its own box; with a class badge it is LEFT-aligned right of the badge (the old code centred the name and
        -- put the badge left of its measured width, which the engine often answered too small, so the badge lay over the first letters).
        a.nameLabel.Position, a.nameLabel.Size, a.nameLabel.TextXAlignment = nameBase.pos, nameBase.size, nameBase.align
        if not failed and type(r.speciesId) == "string" then
            local badgeSize = 40
            local badge = ClassBadge.create(a.body, r.speciesId, badgeSize, true)
            -- how wide the badge will be (it grows to the right with its word): the icon, a gap and the class word at its 14 px floor size, plus the fallback tag's padding
            local word = badge:FindFirstChild("ClassWord")
            local icon = badge:FindFirstChild("Icon")
            local wordSize = if word and word:IsA("TextLabel") then math.max(word.TextSize, TagFit.floorSize(screenScale)) else 14
            local badgeW = (if icon then badgeSize + 6 else 0) + (if word and word:IsA("TextLabel") then TagFit.width(word.Text, wordSize) + (if icon then 0 else 24) else 0) + 6
            if not icon and not word then badgeW = badgeSize end
            -- the name's width: the engine's answer when it has one, never under the estimate (the estimate is on the wide side)
            local measured = a.nameLabel.TextBounds.X
            local labelX, labelY, labelW, labelH = nameBase.pos.X.Offset, nameBase.pos.Y.Offset, nameBase.size.X.Offset, nameBase.size.Y.Offset
            local nameW = math.max(if measured > 1 then measured else 0, TagFit.width(a.nameLabel.Text, a.nameLabel.TextSize))
            nameW = math.min(nameW, labelW - badgeW - 12)
            local gap = 10
            local left = math.max(labelX, labelX + labelW / 2 - (badgeW + gap + nameW) / 2)
            badge.AnchorPoint = Vector2.new(0, .5)
            badge.Position = UDim2.fromOffset(left, labelY + labelH / 2)
            a.nameLabel.Position = UDim2.fromOffset(left + badgeW + gap, labelY)
            a.nameLabel.Size = UDim2.fromOffset(math.max(60, labelX + labelW - (left + badgeW + gap)), labelH)
            a.nameLabel.TextXAlignment = Enum.TextXAlignment.Left
            badge.ZIndex, badge.Visible = a.nameLabel.ZIndex + 1, false
            for _, d in badge:GetDescendants() do if d:IsA("GuiObject") then d.ZIndex = badge.ZIndex end end
            classBadge = badge
        end
        pill.BackgroundColor3 = glow:Lerp(Color3.new(0, 0, 0), .4)
        do -- BD-1107: the ribbons (Shiny, mutation, BIG, New pattern! / New colour!) and the BD-1073 tag "why Skip stops" are MEASURED and STACKED down the card's two sides
            local items: {TagLayout.Item} = {}
            local fills: {Color3} = {}
            local function add(item: TagLayout.Item, fill: Color3) table.insert(items, item) table.insert(fills, fill) end
            local why = Timeline.stopReason({conditionId = if r.genes then r.genes.conditionId else nil, shiny = r.shiny, big = r.big, mutationName = r.mutationName, failed = failed})
            if r.shiny then add({kind = "ribbon", side = "left", text = "SHINY", minW = 170, tilt = -7}, Theme.Colors.gold) end
            if r.mutationName then add({kind = "ribbon", side = "left", text = string.upper(r.mutationName), minW = 210, tilt = -4}, r.mutationColor or Theme.Colors.gold) end
            if why then
                local fill = if r.genes and r.genes.conditionId == "rainbow" then Theme.Colors.purple elseif r.genes and r.genes.conditionId == "astra" then Theme.Colors.blue
                    elseif r.mutationColor and not r.shiny and not r.big then r.mutationColor else Theme.Colors.gold
                add({kind = "stop", side = "left", text = why, line = Timeline.StopLine}, fill)
            end
            if r.big then add({kind = "ribbon", side = "right", text = "BIG", minW = 150, tilt = 7}, Theme.Colors.purple) end
            if r.newFind and not failed then -- BD-436: a first-time colour, pattern or mutation. BD-1039 (flag): "New pattern!" and "New colour!" instead of one "NEW!"
                local ok, fresh = pcall(function() return HttpService:JSONDecode(PrivateState.str("LastChestNewJson", "{}")) end)
                local words = NewFinds.ribbons(if ok then fresh else nil, Config.PatternColourIndexEnabled)
                if #words == 0 then words = {"NEW!"} end
                for _, word in words do add({kind = "ribbon", side = "right", text = word, minW = if #word > 5 then 200 else 130, tilt = 5}, Theme.Colors.gold) end
            end
            local placed = TagLayout.plan(items, screenScale)
            for i, spot in placed do
                if spot.kind == "stop" then
                    local tag, tagTitle = Chip.new(a.body, {name = "StopTag", fill = fills[i], size = UDim2.fromOffset(spot.w, spot.h), position = UDim2.fromOffset(spot.cx, spot.cy),
                        anchor = Vector2.new(.5, .5), z = a.body.ZIndex + 6, textInset = 8})
                    local titleH = math.ceil(spot.textLines * spot.size * TagFit.LineHeight)
                    local lineSize = spot.lineSize or Chip.Spec.minText
                    local lineH = math.ceil(spot.lineLines * lineSize * TagFit.LineHeight)
                    tagTitle.Position, tagTitle.Size = UDim2.fromOffset(8, 3), UDim2.new(1, -16, 0, titleH)
                    tagTitle.TextScaled, tagTitle.TextSize, tagTitle.TextTruncate = false, spot.size, Enum.TextTruncate.AtEnd -- measured (HatchTagLayout), never shrunk to fit
                    local oldLimit = tagTitle:FindFirstChildOfClass("UITextSizeConstraint")
                    if oldLimit then oldLimit:Destroy() end
                    tagTitle.Text = spot.text
                    local line = Instance.new("TextLabel")
                    line.Name, line.BackgroundTransparency, line.Position, line.Size, line.ZIndex = "StopLine", 1, UDim2.fromOffset(8, 5 + titleH), UDim2.new(1, -16, 0, lineH), tag.ZIndex + 1
                    line.Font, line.TextColor3, line.TextScaled, line.TextSize, line.Text, line.Parent = Enum.Font.FredokaOne, WHITE, false, lineSize, spot.line or "", tag
                    line.TextWrapped, line.TextTruncate = false, Enum.TextTruncate.AtEnd
                    line.TextStrokeTransparency, line.TextStrokeColor3 = 0, Theme.Colors.outline
                    tag.Visible = false
                    table.insert(badges, {tag, (function() local sc = Instance.new("UIScale") sc.Scale, sc.Parent = 0, tag return sc end)()})
                else
                    addRibbon(fills[i], spot)
                end
            end
        end
        if r.mutationName and r.mutationId and not failed then mr = MutationReveal.begin(fx.front, r.mutationId, motion) end
        hint.Text = Timeline.hint(r.remaining)
        do
            local i, n = Timeline.batchStep(batch, r.remaining, os.clock())
            counter.Text = Timeline.counterText(i, n)
            counter.Visible = counter.Text ~= ""
        end
        -- BD-371: real, big, friendly buttons at the end (dark text on a bright button, contrast >= 4.5:1); no dead end after a splat.
        local oldRow = a.body:FindFirstChild("EndButtons")
        if oldRow then oldRow:Destroy() end
        local kinds = Copy.hatchButtons(failed, r.remaining)
        if #kinds > 0 then
            local row = Instance.new("Frame")
            row.Name, row.BackgroundTransparency, row.Visible, row.ZIndex = "EndButtons", 1, false, a.body.ZIndex + 8
            row.AnchorPoint, row.Position, row.Size, row.Parent = Vector2.new(.5, 0), UDim2.new(.5, 0, 0, 342), UDim2.fromOffset(#kinds * 246, 60), a.body
            for i, kind in kinds do
                local b = Instance.new("TextButton")
                b.Name, b.Text, b.AutoButtonColor, b.Font, b.TextSize = "End_" .. kind, Copy.ButtonText[kind], true, Enum.Font.FredokaOne, 30
                local fill, ink = Copy.ButtonColors[kind], Copy.ButtonTextColor
                b.BackgroundColor3, b.TextColor3 = Color3.fromRGB(fill[1], fill[2], fill[3]), Color3.fromRGB(ink[1], ink[2], ink[3])
                b.Position, b.Size, b.ZIndex, b.Parent = UDim2.fromOffset((i - 1) * 246, 0), UDim2.fromOffset(230, 60), row.ZIndex + 1, row
                local corner = Instance.new("UICorner") corner.CornerRadius = UDim.new(0, 16) corner.Parent = b
                local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = Theme.Colors.outline, 3, b
                b.Activated:Connect(function()
                    if kind == "again" then
                        if finished then return end
                        finish()
                        if a.onAgain then (a.onAgain :: () -> ())() end
                    else
                        advance()
                    end
                end)
            end
        end
        if r.remaining > 0 and not skipButton then
            local b = Instance.new("TextButton")
            b.Name, b.Text, b.AnchorPoint, b.AutoButtonColor = "SkipAll", Timeline.SkipText, Vector2.new(1, 1), true
            b.Position, b.Size, b.BackgroundColor3 = UDim2.new(1, -12, 1, -12), UDim2.fromOffset(176, 48), Theme.Colors.card
            b.Font, b.TextSize, b.TextColor3, b.ZIndex, b.Parent = Enum.Font.FredokaOne, 22, Theme.Colors.text, 47, layer
            local c = Instance.new("UICorner") c.CornerRadius = UDim.new(0, 12) c.Parent = b
            local s = Instance.new("UIStroke") s.Color, s.Thickness, s.Parent = Theme.Colors.outline, 2, b
            skipButton = b
            b.Activated:Connect(function()
                if finished then return end
                a.onSkipAll()
                if Timeline.skipAll(state) == "advance" then advance() end
            end)
        end
        -- Tint the pooled effects for this egg.
        fx.backdrop.BackgroundColor3 = glow:Lerp(Color3.new(0, 0, 0), .78)
        for i, ring in fx.rings do ring.BackgroundColor3 = glow:Lerp(WHITE, (1 - (i - 1) / (RING_N - 1)) * .5) end
        for _, ray in fx.rays do ray.BackgroundColor3 = glow:Lerp(WHITE, .4) end
        for _, m in fx.motes do m.BackgroundColor3 = glow:Lerp(WHITE, .5) end
        for i, p in fx.podium do p.BackgroundColor3 = glow:Lerp(WHITE, if i == 1 then .1 else .4) end
        for i, s in fx.shocks do fx.shockStrokes[i].Color = glow:Lerp(WHITE, .3) end
        -- Paint buckets: colour bucket pours the egg colour, pattern bucket pours the pattern's accent colour.
        a.paint.setGenes(r.genes)
        if r.genes and typeof(r.genes.conditionId) == "string" then setCondition(r.genes.conditionId) end
        local colors = r.paintColors
        paintColors = {if colors then colors[1] else WHITE, if colors then colors[2] else WHITE}
        if v2 then
            -- BD-397: left bucket = the PRIMARY colour, right bucket = the secondary colour on the pattern (a plain egg gets a
            -- clear varnish); same-family genes paint the pattern a darker shade (PatternGenes rule).
            local g = r.genes
            local base, accent = paintColors[1], paintColors[2]
            local plain = g == nil or g.patternId == nil or g.patternId == "01_blank"
            if g then
                local pc, sc = EggGenetics.color(g.primaryColorId), EggGenetics.color(g.secondaryColorId)
                if pc then base = Color3.fromRGB(pc.rgb[1], pc.rgb[2], pc.rgb[3]) end
                accent = if sc and g.secondaryColorId ~= g.primaryColorId then Color3.fromRGB(sc.rgb[1], sc.rgb[2], sc.rgb[3]) else base:Lerp(Color3.new(0, 0, 0), .22)
            end
            paintColors = {base, if plain then base:Lerp(WHITE, .6) else accent}
            EggV2.setGenes(v2, g, a.eggId, base, accent, plain)
            if not motion then EggV2.finish(v2) end
        end
        for i = 1, 2 do
            local reveal = if i == 1 then r.colorReveal else (r.secondReveal or r.colorReveal)
            -- BD-1069: bucket i pours exactly the colour its chip names (EggColors rgb), not the blended shell tint. The pour stream, splash and droplets follow.
            local exact = Timeline.revealRgb(reveal)
            if exact and not v2 then paintColors[i] = Chip.color(exact) end
            for _, part in kit.bucketPaints[i] do part.BackgroundColor3 = paintColors[i] end
            kit.splashStrokes[i].Color = paintColors[i]
            kit.splashes[i].BackgroundColor3 = paintColors[i]
            kit.splashes[i].BackgroundTransparency = .8
            HatchFx.paintStyle(hx, i, paintColors[i], if reveal then reveal.tier else 1)
            dropN[i] = if reveal then math.min(10, 4 + reveal.tier) else 5
            for j = 1, 10 do
                local d = kit.drops[(i - 1) * 10 + j]
                d.BackgroundColor3 = if j % 3 == 0 then paintColors[i]:Lerp(WHITE, .45) else paintColors[i]
                local size = 7 + (j * 5) % 7
                d.Size = UDim2.fromOffset(size, size)
            end
        end
        if not motion then a.paint.finish() end
    end

    table.insert(connections, RunService.Heartbeat:Connect(function(dt)
        if finished then return end
        if not a.alive() or (a.dino and not a.dino.Parent) then finish() if a.onAbort then (a.onAbort :: () -> ())() end return end
        zone.step()
        local frameDt = math.min(dt, 1 / 20) -- a hitch must not skip the whole build-up
        Timeline.step(state, frameDt)
        local t = state.t
        local vt = Timeline.visualT(state)

        while cueIndex <= #cues and cues[cueIndex].t <= t do
            Sfx.play(cues[cueIndex].name)
            Sfx.playLayers(cues[cueIndex].name) -- BD-437: Epic/Legendary second cue
            cueIndex += 1
        end

        if t < durs.build then
            if motion then
                local bp = Timeline.buildProgress(durs, t)
                local i = Timeline.intensity(bp)
                local rot, dx, dy = Timeline.rattle(t, i)
                local sx, sy = Timeline.shakeOffset(t, i * esc.shakeScale)
                -- A gentle sway while the buckets paint (and while the server answer is still on its way).
                local swayAmp = 1 - math.clamp(bp * 4, 0, 1)
                a.eggView.Rotation = rot * esc.shakeScale + math.sin(vt * 3.4) * 2.8 * swayAmp
                a.eggView.Position = UDim2.fromOffset(CENTER_EGG.X + dx * esc.shakeScale, CENTER_EGG.Y + dy * esc.shakeScale + math.sin(vt * 2.3) * 3 * swayAmp)
                eggZoom.Scale = Timeline.zoom(bp)
                bodyScale.Scale = Timeline.cameraZoom(bp) * fit
                a.body.Position = UDim2.fromOffset(bodyCenter.X + sx, bodyCenter.Y + sy)
                a.animateEgg(Timeline.eggClock(durs, t))
                if v2 then EggV2.update(v2, t, vt, if state.pending then nil else Timeline.paintState(durs, t), durs,
                    {rot = rot * esc.shakeScale, dx = dx * esc.shakeScale, dy = dy * esc.shakeScale, zoom = Timeline.zoom(bp)}) end
                if not state.pending then updatePaint(t) end
                local g = Timeline.glow(bp)
                HatchFx.update(hx, vt, bp, nil, false)
                for n, ring in fx.rings do
                    ring.BackgroundTransparency = 1 - .16 * g * strength * (1 - (n - 1) / (RING_N + 2))
                    fx.ringScales[n].Scale = (.35 + .5 * g) * (1 + .05 * math.sin(t * 9))
                    ring.Position = UDim2.fromOffset(CENTER_EGG.X, CENTER_EGG.Y)
                end
                fx.backdrop.BackgroundTransparency = 1 - .35 * g
                if esc.arcs then
                    for n, arc in fx.arcs do
                        local ang = n / ARC_N * TAU + t * 3
                        local rad = 110 + 18 * math.sin(t * 17 + n)
                        place(arc, CENTER_EGG.X + math.cos(ang) * rad, CENTER_EGG.Y + math.sin(ang) * rad * .85)
                        arc.Rotation = math.deg(ang) + 90
                        arc.BackgroundColor3 = Theme.Colors.purple:Lerp(WHITE, .35 + .3 * math.sin(t * 23 + n))
                        arc.BackgroundTransparency = 1 - .9 * g
                        arc.Visible = math.sin(t * 26 + n * 2.3) > -.3
                    end
                end
                for n, m in fx.motes do
                    my[n] -= ms[n] * frameDt
                    if my[n] < -10 then my[n] = 410 end
                    place(m, mx[n] + math.sin(t * 1.3 + mp[n]) * 14, my[n])
                    m.BackgroundTransparency = 1 - .6 * g
                end
            end
        elseif state.pending then
            return -- Reduced Motion: wait for the server answer before opening anything
        else
            if not burstDone then burst() end
            local since = t - durs.build
            -- Wait (up to 2.5 s) for the real model instead of revealing an empty viewport.
            local modelReady = failed or a.dino:FindFirstChildOfClass("WorldModel") ~= nil or since > 2.5
            if not revealStarted and modelReady and t >= durs.build + (if motion then .1 else 0) then revealT = since startReveal() end
            if motion then
                -- camera push-in releases with a short ease (stronger punch for rarer eggs)
                if since < .45 then
                    if failed then
                        local bumpScale, bumpDy = Timeline.bump(since)
                        bodyScale.Scale = bumpScale * fit
                        a.body.Position = UDim2.fromOffset(bodyCenter.X, bodyCenter.Y + bumpDy)
                    else
                        bodyScale.Scale = (1 + (punchStart - 1) * (1 - Timeline.easeOut(since / .45))) * fit
                    end
                elseif not bodyRestored then
                    bodyRestored = true
                    restoreBody()
                end
                HatchFx.update(hx, vt, 1, since, revealStarted)
                MutationReveal.update(mr, if revealStarted then math.max(0, since - revealT) else nil)
                if not failed then
                    if revealStarted and dinoScale then dinoScale.Scale = Timeline.revealScale((since - revealT) / .8, rarity) * (if a.big then Timeline.stamp(since - impactAt - revealT) else 1) end
                    if a.big and since >= impactAt + revealT and since < impactAt + revealT + .25 then
                        local k = 1 - (since - impactAt - revealT) / .25
                        a.body.AnchorPoint = Vector2.new(.5, .5)
                        a.body.Position = UDim2.fromOffset(bodyCenter.X + math.sin(since * 120) * 2 * k, bodyCenter.Y + math.cos(since * 100) * 1.5 * k)
                    elseif a.big and since >= impactAt + .25 and bodyRestored then
                        a.body.AnchorPoint, a.body.Position = bodyHomeAnchor, bodyHomePos
                    end
                    -- radial glow: burst, settle to a pulsing halo
                    local expand = Timeline.easeOut(since / .5)
                    local settle = Timeline.easeOut(since / (durs.burst + durs.settle))
                    local pulse = 1 + .045 * math.sin(since * 3.4)
                    setGlow(1 - .3 * settle + .08 * math.sin(since * 3.4))
                    for n, ring in fx.rings do
                        fx.ringScales[n].Scale = (.85 + .4 * expand) * pulse
                        ring.Position = UDim2.fromOffset(CENTER_DINO.X, CENTER_DINO.Y)
                    end
                    local rayT = 1 - (.55 + .1 * math.sin(since * 2.2)) * Timeline.easeOut(since / .4)
                    for n, ray in fx.rays do
                        ray.BackgroundTransparency = rayT
                        ray.Rotation = if n <= 3 then (n - 1) * 60 + since * 14 else (n - 4) * 60 + 30 - since * 10
                    end
                    for n, pd in fx.podium do pd.BackgroundTransparency = 1 - (if n == 1 then .45 else .6) * Timeline.easeOut(since / .5) end
                    for n, m in fx.motes do
                        my[n] -= ms[n] * frameDt
                        if my[n] < -10 then my[n] = 410 end
                        place(m, mx[n] + math.sin(t * 1.3 + mp[n]) * 14, my[n])
                        m.BackgroundTransparency = .3 + .3 * math.abs(math.sin(t * 2 + mp[n]))
                    end
                    -- confetti / sparkle burst
                    for i = 1, count do
                        local p = fx.particles[i]
                        local l = life[i]
                        if since >= l then
                            if p.Visible then p.Visible = false end
                        else
                            vy[i] += GRAVITY * frameDt
                            px[i] += vx[i] * frameDt
                            py[i] += vy[i] * frameDt
                            place(p, px[i], py[i])
                            p.BackgroundTransparency = math.clamp((since / l - .45) / .55, 0, 1)
                            p.Rotation += 240 * frameDt
                        end
                    end
                    -- twinkling sparkles orbiting the dinosaur
                    if since > .6 then
                        for n = 1, orbit do
                            local p = fx.particles[Timeline.MaxParticles + n]
                            local ang = since * 1.1 + n / orbit * TAU
                            p.Visible = true
                            place(p, CENTER_DINO.X + math.cos(ang) * 210, CENTER_DINO.Y + 10 + math.sin(ang) * 95)
                            local sz = 7 + (n % 3) * 3
                            p.Size = UDim2.fromOffset(sz, sz)
                            p.BackgroundColor3 = palette[n % #palette + 1]
                            p.BackgroundTransparency = .1 + .7 * (1 - math.abs(math.sin(since * 4 + n * 1.9)))
                            p.Rotation += 120 * frameDt
                        end
                    end
                    -- shockwave rings (Rare+; Epic+ gets a second one)
                    for n, s in fx.shocks do
                        if s.Visible then
                            local age = since - (n - 1) * .14
                            if age >= 0 and age < .65 then
                                local k = age / .65
                                place(s, CENTER_EGG.X, CENTER_EGG.Y)
                                fx.shockScales[n].Scale = .3 + 3.2 * Timeline.easeOut(k)
                                fx.shockStrokes[n].Transparency = k
                                fx.shockStrokes[n].Thickness = 2 + 8 * (1 - k)
                            elseif age >= .65 then
                                s.Visible = false
                            end
                        end
                    end
                    -- Legendary gold fireworks
                    if esc.fireworks then
                        for b, spec in FIREWORKS do
                            local age = since - spec[1]
                            for j = 1, 8 do
                                local f = fx.fw[(b - 1) * 8 + j]
                                if age >= 0 and age < .9 then
                                    local ang = j / 8 * TAU + b
                                    local r = 190 * Timeline.easeOut(age / .9)
                                    f.Visible = true
                                    place(f, spec[2] + math.cos(ang) * r, spec[3] + math.sin(ang) * r + age * age * 90)
                                    f.BackgroundColor3 = if j % 2 == 0 then Theme.Colors.gold else WHITE
                                    f.BackgroundTransparency = (age / .9) ^ 1.6
                                elseif f.Visible then
                                    f.Visible = false
                                end
                            end
                        end
                    end
                    -- Shiny: rainbow shimmer pass and gold sparkle rain
                    if a.shiny then
                        local sp = (since - .9) / 1.1
                        if sp >= 0 and sp <= 1 then
                            fx.shimmer.Visible = true
                            fx.shimmerGradient.Offset = Vector2.new(-1 + 2 * sp, 0)
                        elseif fx.shimmer.Visible then
                            fx.shimmer.Visible = false
                        end
                        for n, r in fx.rain do
                            if since > .2 and since < 3.4 then
                                local y = ((since - .2) * (150 + n * 9) + n * 61) % 440 - 20
                                r.Visible = true
                                place(r, 190 + (n * 47) % 450, y)
                                r.BackgroundColor3 = if n % 2 == 0 then Theme.Colors.gold else Color3.fromRGB(255, 240, 160)
                                r.BackgroundTransparency = .1 + .5 * math.abs(math.sin(since * 6 + n))
                            elseif r.Visible then
                                r.Visible = false
                            end
                        end
                    end
                    -- ribbon glow pulse
                    for n, st in pulseStrokes do st.Thickness = 4 + 1.6 * math.sin(since * 5 + n) end
                else
                    -- SPLAT: the build-up glow fades while shells bounce, the yolk plops and the puddle spreads.
                    local fade = Timeline.easeOut(since / .35)
                    for n, ring in fx.rings do ring.BackgroundTransparency = 1 - .16 * strength * (1 - fade) * (1 - (n - 1) / (RING_N + 2)) end
                    fx.backdrop.BackgroundTransparency = 1 - .35 * (1 - fade)
                    applySplat(since)
                    local pulseShock = fx.shocks[1]
                    if pulseShock.Visible then
                        local pulseScale, pulseAlpha = Timeline.splatPulse(since)
                        if pulseAlpha >= 1 and since > Timeline.SplatDrop then
                            pulseShock.Visible = false
                        else
                            place(pulseShock, PUDDLE.X, PUDDLE.Y)
                            fx.shockScales[1].Scale = pulseScale
                            fx.shockStrokes[1].Transparency = pulseAlpha
                            fx.shockStrokes[1].Thickness = 2 + 8 * (1 - pulseAlpha)
                        end
                    end
                    for i = 1, count do
                        local p = fx.particles[i]
                        local l = life[i]
                        if since >= l then
                            if p.Visible then p.Visible = false end
                        else
                            vy[i] += GRAVITY * frameDt
                            px[i] += vx[i] * frameDt
                            py[i] += vy[i] * frameDt
                            place(p, px[i], py[i])
                            p.BackgroundTransparency = math.clamp((since / l - .45) / .55, 0, 1)
                            p.Rotation += 240 * frameDt
                        end
                    end
                end
            end
        end
        if not motion and not bodyRestored and not state.pending then bodyRestored = true restoreBody() end
        if not readyShown and (revealStarted or failed) and not state.pending and t >= durs.readyAt + revealT then showHint() end
    end))

    setCondition(a.eggCondition)
    if a.result then applyResult(a.result) end
    return {
        cancel = function() finish() end,
        supply = function(r: Result)
            if finished or not state.pending then return end
            applyResult(r)
        end,
        pending = function() return state.pending end,
        -- BD-380: the egg counts arrive a moment after the result; keep the hint equal to the eggs really left.
        setRemaining = function(n: number)
            if finished then return end
            hint.Text = Timeline.hint(n)
            local i, total = Timeline.batchRefine(batch, n)
            counter.Text = Timeline.counterText(i, total)
            counter.Visible = counter.Text ~= ""
        end,
    }
end

return Seq
