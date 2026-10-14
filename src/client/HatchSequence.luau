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
local Timeline = require(Shared.HatchTimeline)

local Seq = {}
local CENTER_EGG = Vector2.new(412, 130) -- body coordinates (824 x 402 virtual px)
local CENTER_DINO = Vector2.new(412, 118)
local BODY_HOME = Vector2.new(18, 98)
local BODY_CENTER = Vector2.new(430, 299)
local RING_N, RAY_N, MOTE_N, ARC_N = 8, 6, 12, 6
local GRAVITY = 260
local WHITE = Color3.new(1, 1, 1)
local TAU = math.pi * 2
local FIREWORKS = {{.35, 250, 120}, {.75, 580, 92}, {1.15, 412, 58}}

type Layers = {back: Frame, front: Frame, backdrop: Frame, rings: {Frame}, ringScales: {UIScale}, rays: {Frame}, motes: {Frame},
    podium: {Frame}, particles: {Frame}, fw: {Frame}, rain: {Frame}, shocks: {Frame}, shockStrokes: {UIStroke}, shockScales: {UIScale},
    arcs: {Frame}, shimmer: Frame, shimmerGradient: UIGradient}
local layers: Layers? = nil

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

local function ensureLayers(panel: GuiObject): Layers
    local existing = layers
    if existing and existing.back.Parent == panel and existing.front.Parent == panel then return existing end
    if existing then existing.back:Destroy() existing.front:Destroy() end
    local function layer(name: string, z: number): Frame
        local f = Instance.new("Frame")
        f.Name, f.BackgroundTransparency, f.ClipsDescendants, f.Active = name, 1, true, false
        f.Position, f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(BODY_HOME.X, BODY_HOME.Y), UDim2.fromOffset(824, 402), z, panel
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
        p.Visible, p.Position = true, UDim2.fromOffset(CENTER_DINO.X, 236)
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
    local created: Layers = {back = back, front = front, backdrop = backdrop, rings = rings, ringScales = ringScales, rays = rays, motes = motes, podium = podium,
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

-- Tilted ribbon tag with a diamond icon and a glowing outline (not a button).
local function ribbon(parent: GuiObject, text: string, color: Color3, cx: number, cy: number, w: number, tilt: number): (Frame, UIScale, UIStroke)
    local f = Instance.new("Frame")
    f.Name, f.BackgroundColor3, f.AnchorPoint, f.Visible, f.Rotation = "Ribbon", WHITE, Vector2.new(.5, .5), false, tilt
    f.Position, f.Size, f.ZIndex, f.Parent = UDim2.fromOffset(cx, cy), UDim2.fromOffset(w, 44), parent.ZIndex + 6, parent
    corner(f, UDim.new(0, 8))
    local g = Instance.new("UIGradient")
    g.Rotation = 90
    g.Color = ColorSequence.new(color:Lerp(WHITE, .35), color:Lerp(Color3.new(0, 0, 0), .3))
    g.Parent = f
    local stroke = Instance.new("UIStroke") stroke.Color, stroke.Thickness, stroke.Parent = color:Lerp(WHITE, .6), 4, f
    local icon = Instance.new("Frame")
    icon.BackgroundColor3, icon.BorderSizePixel, icon.AnchorPoint, icon.Rotation = WHITE, 0, Vector2.new(.5, .5), 45
    icon.Position, icon.Size, icon.ZIndex, icon.Parent = UDim2.fromOffset(24, 22), UDim2.fromOffset(16, 16), f.ZIndex + 1, f
    local label = Instance.new("TextLabel")
    label.BackgroundTransparency, label.Position, label.Size, label.Font, label.Text = 1, UDim2.fromOffset(42, 2), UDim2.new(1, -50, 1, -4), Enum.Font.FredokaOne, text
    label.TextColor3, label.TextScaled, label.ZIndex, label.TextStrokeTransparency, label.TextStrokeColor3 = WHITE, true, f.ZIndex + 1, 0, Color3.new(0, 0, 0)
    label.Parent = f
    local limit = Instance.new("UITextSizeConstraint") limit.MaxTextSize, limit.MinTextSize, limit.Parent = 26, 10, label
    local scale = Instance.new("UIScale") scale.Scale, scale.Parent = 0, f
    return f, scale, stroke
end

export type Args = {
    gui: ScreenGui, panel: GuiObject, body: GuiObject,
    eggView: GuiObject, animateEgg: (number) -> (), splitEgg: (boolean?) -> (),
    dino: GuiObject, rarity: number, color: Color3, failed: boolean, shiny: boolean, big: boolean,
    mutationName: string?, mutationColor: Color3?,
    nameLabel: TextLabel, oddsLabel: TextLabel, detailLabel: TextLabel,
    remaining: number, motion: boolean,
    alive: () -> boolean, flash: (Color3, number) -> (),
    onNext: () -> (), onSkipAll: () -> (), onReveal: () -> (),
}

-- Returns {cancel}. onNext runs once after the player taps on the revealed egg.
function Seq.play(a: Args)
    local motion = a.motion
    local rarity = math.clamp(a.rarity, 1, 5)
    local state = Timeline.new(motion, rarity)
    local durs = state.durs
    local esc = Timeline.escalation(rarity, motion)
    local fx = ensureLayers(a.panel)
    local failed = a.failed
    -- Rarity palette: Common is lively teal, then the rarity colour up to gold for Legendary.
    local glow = if rarity <= 1 then Color3.fromRGB(70, 205, 170) else a.color
    local bodyHomePos, bodyHomeAnchor = a.body.Position, a.body.AnchorPoint
    local connections: {RBXScriptConnection} = {}
    local finished = false

    a.eggView.AnchorPoint = Vector2.new(.5, .5)
    a.eggView.Position = UDim2.fromOffset(CENTER_EGG.X, CENTER_EGG.Y)
    a.dino.AnchorPoint = Vector2.new(.5, .5)
    a.dino.Position = UDim2.fromOffset(CENTER_DINO.X, CENTER_DINO.Y)
    local eggZoom = Instance.new("UIScale") eggZoom.Parent = a.eggView
    local dinoScale = Instance.new("UIScale") dinoScale.Scale, dinoScale.Parent = if motion then .25 else 1, a.dino
    local bodyScale = Instance.new("UIScale") bodyScale.Parent = a.body
    if motion then
        a.body.AnchorPoint, a.body.Position = Vector2.new(.5, .5), UDim2.fromOffset(BODY_CENTER.X, BODY_CENTER.Y)
    end
    a.dino.Visible = false

    -- Name: big white fill with a thick rarity-coloured stroke. Rarity line sits on a coloured pill.
    local nameStroke = a.nameLabel:FindFirstChildOfClass("UIStroke")
    if not failed then
        a.nameLabel.TextColor3, a.nameLabel.TextSize = WHITE, 48
        a.nameLabel.TextStrokeColor3 = glow:Lerp(Color3.new(0, 0, 0), .45)
        if nameStroke then nameStroke.Color, nameStroke.Thickness = glow:Lerp(Color3.new(0, 0, 0), .35), 5 end
        a.oddsLabel.TextColor3 = WHITE
    end
    for _, l in {a.nameLabel, a.oddsLabel, a.detailLabel} do hideLabel(l) end
    local pill = Instance.new("Frame")
    pill.Name, pill.BackgroundColor3, pill.AnchorPoint, pill.Visible = "RarityPill", glow:Lerp(Color3.new(0, 0, 0), .4), Vector2.new(.5, .5), false
    pill.Position, pill.Size, pill.ZIndex, pill.Parent = UDim2.fromOffset(412, 302), UDim2.fromOffset(380, 32), a.oddsLabel.ZIndex - 1, a.body
    corner(pill)
    local pillStroke = Instance.new("UIStroke") pillStroke.Color, pillStroke.Thickness, pillStroke.Parent = glow:Lerp(WHITE, .25), 2.5, pill
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

    -- Ribbons (Shiny / BIG / mutation) and the tap hint.
    local badges: {{any}} = {}
    local pulseStrokes: {UIStroke} = {}
    local function addRibbon(text: string, color: Color3, cx: number, cy: number, w: number, tilt: number)
        local f, s, st = ribbon(a.body, text, color, cx, cy, w, tilt)
        table.insert(badges, {f, s}) table.insert(pulseStrokes, st)
    end
    if a.shiny then addRibbon("SHINY", Theme.Colors.gold, 100, 52, 170, -7) end
    if a.big then addRibbon("BIG", Theme.Colors.purple, 724, 52, 150, 7) end
    if a.mutationName then addRibbon(string.upper(a.mutationName), a.mutationColor or Theme.Colors.gold, 116, if a.shiny then 108 else 52, 210, -4) end
    local hint = Instance.new("TextLabel")
    hint.Name, hint.BackgroundTransparency, hint.Position, hint.Size = "TapHint", 1, UDim2.fromOffset(152, 350), UDim2.fromOffset(520, 46)
    hint.Font, hint.TextColor3, hint.TextScaled, hint.Text = Enum.Font.FredokaOne, WHITE, true, Timeline.hint(a.remaining)
    hint.TextStrokeTransparency, hint.TextStrokeColor3, hint.ZIndex, hint.Visible = 0, Theme.Colors.outline, a.body.ZIndex + 6, false
    hint.Parent = a.body
    local hintLimit = Instance.new("UITextSizeConstraint") hintLimit.MaxTextSize, hintLimit.MinTextSize, hintLimit.Parent = 34, 12, hint

    -- Full-screen tap target (>= 44 px everywhere) plus a small "Skip all" while more eggs wait.
    local overlay = Instance.new("TextButton")
    overlay.Name, overlay.Text, overlay.BackgroundTransparency, overlay.AutoButtonColor = "HatchTapCatcher", "", 1, false
    overlay.Size, overlay.ZIndex, overlay.Parent = UDim2.fromScale(1, 1), 46, a.gui
    local skipButton: TextButton? = nil
    if a.remaining > 0 then
        local b = Instance.new("TextButton")
        b.Name, b.Text, b.AnchorPoint, b.AutoButtonColor = "SkipAll", "Skip all", Vector2.new(1, 1), true
        b.Position, b.Size, b.BackgroundColor3 = UDim2.new(1, -12, 1, -12), UDim2.fromOffset(132, 46), Theme.Colors.card
        b.Font, b.TextSize, b.TextColor3, b.ZIndex, b.Parent = Enum.Font.FredokaOne, 22, Theme.Colors.text, 47, overlay
        local c = Instance.new("UICorner") c.CornerRadius = UDim.new(0, 12) c.Parent = b
        local s = Instance.new("UIStroke") s.Color, s.Thickness, s.Parent = Theme.Colors.outline, 2, b
        skipButton = b
    end

    -- Reset the pooled effects and tint them for this egg.
    local strength = .75 + .06 * rarity
    fx.backdrop.BackgroundColor3, fx.backdrop.BackgroundTransparency = glow:Lerp(Color3.new(0, 0, 0), .78), 1
    for i, ring in fx.rings do
        ring.BackgroundColor3 = glow:Lerp(WHITE, (1 - (i - 1) / (RING_N - 1)) * .5)
        ring.BackgroundTransparency = 1
        fx.ringScales[i].Scale = .6
    end
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
    for i, s in fx.shocks do s.Visible, fx.shockStrokes[i].Color, fx.shockStrokes[i].Transparency = false, glow:Lerp(WHITE, .3), 1 end

    local count = Timeline.particleCount(rarity, a.shiny, a.big, motion, failed)
    local orbit = Timeline.orbitCount(rarity, motion, failed)
    local px, py, vx, vy, life = table.create(count, 0), table.create(count, 0), table.create(count, 0), table.create(count, 0), table.create(count, 0)
    local palette = {glow, WHITE, Theme.Colors.gold, glow:Lerp(WHITE, .5), Theme.RarityColors[math.min(5, rarity + 1)]}
    local cues = Timeline.cues(durs, rarity, failed, Sfx.revealName(rarity))
    local cueIndex = 1
    local burstDone, revealStarted, readyShown, bodyRestored = false, false, false, false
    local burstAt = durs.build
    local tweenHint: Tween? = nil
    local punchStart = 1 + esc.punch
    local impactAt = .95
    local level = 0 -- overall glow level 0..1

    local function restoreBody()
        a.body.AnchorPoint, a.body.Position = bodyHomeAnchor, bodyHomePos
        bodyScale.Scale = 1
    end
    local function finish()
        if finished then return end
        finished = true
        for _, c in connections do c:Disconnect() end
        table.clear(connections)
        if tweenHint then tweenHint:Cancel() tweenHint = nil end
        restoreBody()
        if overlay.Parent then overlay:Destroy() end
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
        end
    end

    local function setGlow(l: number)
        level = l
        local t = 1 - .16 * l * strength
        for _, ring in fx.rings do ring.BackgroundTransparency = t end
        fx.backdrop.BackgroundTransparency = 1 - .55 * l
    end

    local function burst()
        burstDone = true
        a.eggView.Rotation = 0
        eggZoom.Scale = 1
        if motion then a.body.Position = UDim2.fromOffset(BODY_CENTER.X, BODY_CENTER.Y) end
        if motion then a.animateEgg(Timeline.EggClock) end
        a.splitEgg(not failed)
        for _, f in fx.arcs do f.Visible = false end
        if failed then return end
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
        if failed then
            fadeLabel(a.nameLabel, .15, .35, 0)
            fadeLabel(a.detailLabel, .3, .35, 0)
            return
        end
        a.dino.Visible = true
        if not motion then
            local view = a.dino :: any
            view.ImageTransparency = 1
            TweenService:Create(view, TweenInfo.new(.3), {ImageTransparency = 0}):Play()
            setGlow(.6)
            for _, sc in fx.ringScales do sc.Scale = 1 end
            for _, p in fx.podium do p.BackgroundTransparency = .6 end
        end
        local rise = if motion then 14 else 0
        fadeLabel(a.nameLabel, if motion then .25 else 0, .3, rise)
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
        hint.Visible = true
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
        if Timeline.tap(state) == "advance" then advance() end
    end
    overlay.Activated:Connect(onTap)
    if skipButton then
        skipButton.Activated:Connect(function()
            if finished then return end
            a.onSkipAll()
            if Timeline.skipAll(state) == "advance" then advance() end
        end)
    end
    table.insert(connections, Input.InputBegan:Connect(function(input, processed)
        if processed then return end
        local k = input.KeyCode
        if k == Enum.KeyCode.Space or k == Enum.KeyCode.Return or k == Enum.KeyCode.KeypadEnter or k == Enum.KeyCode.ButtonA then onTap() end
    end))

    local function place(f: Frame, x: number, y: number) f.Position = UDim2.fromOffset(x, y) end

    table.insert(connections, RunService.Heartbeat:Connect(function(dt)
        if finished then return end
        if not a.alive() or not a.dino.Parent then finish() return end
        local frameDt = math.min(dt, 1 / 20) -- a hitch must not skip the whole build-up
        Timeline.step(state, frameDt)
        local t = state.t

        while cueIndex <= #cues and cues[cueIndex].t <= t do
            Sfx.play(cues[cueIndex].name)
            cueIndex += 1
        end

        if t < burstAt then
            if motion then
                local p = t / durs.build
                local i = Timeline.intensity(p)
                local rot, dx, dy = Timeline.rattle(t, i)
                local sx, sy = Timeline.shakeOffset(t, i * esc.shakeScale)
                a.eggView.Rotation = rot * esc.shakeScale
                a.eggView.Position = UDim2.fromOffset(CENTER_EGG.X + dx * esc.shakeScale, CENTER_EGG.Y + dy * esc.shakeScale)
                eggZoom.Scale = Timeline.zoom(p)
                bodyScale.Scale = Timeline.cameraZoom(p)
                a.body.Position = UDim2.fromOffset(BODY_CENTER.X + sx, BODY_CENTER.Y + sy)
                a.animateEgg(p * Timeline.EggClock)
                local g = Timeline.glow(p)
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
        else
            if not burstDone then burst() end
            if not revealStarted and t >= burstAt + (if motion then .1 else 0) then startReveal() end
            local since = t - burstAt
            if motion then
                -- camera push-in releases with a short ease (stronger punch for rarer eggs)
                if since < .45 then
                    bodyScale.Scale = 1 + (punchStart - 1) * (1 - Timeline.easeOut(since / .45))
                elseif not bodyRestored then
                    bodyRestored = true
                    restoreBody()
                end
                if not failed then
                    if revealStarted then dinoScale.Scale = Timeline.revealScale((since - .1) / .8) * (if a.big then Timeline.stamp(since - impactAt) else 1) end
                    if a.big and since >= impactAt and since < impactAt + .25 then
                        local k = 1 - (since - impactAt) / .25
                        a.body.AnchorPoint = Vector2.new(.5, .5)
                        a.body.Position = UDim2.fromOffset(BODY_CENTER.X + math.sin(since * 120) * 4 * k, BODY_CENTER.Y + math.cos(since * 100) * 3 * k)
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
                    for _, ring in fx.rings do ring.BackgroundTransparency = 1 end
                    fx.backdrop.BackgroundTransparency = 1
                end
            end
        end
        if not motion and not bodyRestored then bodyRestored = true restoreBody() end
        if not readyShown and t >= durs.readyAt then showHint() end
    end))

    return {
        cancel = function() finish() end,
    }
end

return Seq
