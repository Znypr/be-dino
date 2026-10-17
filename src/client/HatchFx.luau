--!nonstrict
-- Layered 2D hatch effects (client). Draws Shared/HatchFxPlan with ONE persistent pool of sprites per hatch panel: no Instances are
-- created per egg or per frame. Back layer: soft glow bloom that grows through the build-up, colour-matched rim sparks, shock
-- rings, soft smoke puffs, floating motes. Front layer: a gentle sparkle pass in the side margins only (never over the dinosaur,
-- the paint chips, the tap hint or the ribbons) and the paint-splash droplet bursts.
-- Textures: Shared/EffectAssets keys glowPlate / ringShock / smokeSheet / sparkSheet / starFour. A key without a real upload falls
-- back to plain rounded shapes (calm, tinted at runtime); once the owner uploads the Blender PNGs the real ids are used automatically.
-- Reduce Motion: ONE static soft glow, nothing else.
-- BD-431 / BD-433: Epic and up also show ONE soft light shaft behind the egg (Blender texture shaftGradient, Plan.shaft), only while that slot
-- holds a real upload, only in the full Effects look, never with Reduce Motion. An empty slot keeps exactly today's sprites.
local UserInputService = game:GetService("UserInputService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Plan = require(Shared.HatchFxPlan)
local Recipes = require(Shared.FxRecipes)
local Assets = require(Shared.EffectAssets)
local Settings = require(Shared.SettingsModel)

local M = {}
local cache = setmetatable({}, {__mode = "k"})
local WHITE = Color3.new(1, 1, 1)

local function c3(c) return Color3.fromRGB(math.clamp(math.floor(c[1] + 0.5), 0, 255), math.clamp(math.floor(c[2] + 0.5), 0, 255), math.clamp(math.floor(c[3] + 0.5), 0, 255)) end
local function triple(c: Color3) return {c.R * 255, c.G * 255, c.B * 255} end

-- shape: "disc" | "ring" | "spark" | "puff". A real texture (Assets) makes it an ImageLabel, otherwise a native shape.
local function node(parent, z: number, key: string, shape: string, seed: number)
    local n = {shape = shape, key = key, seed = seed, cell = 0}
    if Assets.isRealUi(key) then
        local i = Instance.new("ImageLabel")
        i.BackgroundTransparency, i.BorderSizePixel, i.Image = 1, 0, Assets.resolveUi(key)
        Assets.setCell(i, key, seed)
        n.obj, n.img = i, true
    else
        local f = Instance.new("Frame")
        f.BorderSizePixel = 0
        if shape == "spark" then f.Rotation = 45
        else
            local c = Instance.new("UICorner") c.CornerRadius = UDim.new(1, 0) c.Parent = f
        end
        if shape == "ring" then
            f.BackgroundTransparency = 1
            local s = Instance.new("UIStroke") s.Thickness = 3 s.Parent = f
            n.stroke = s
        end
        n.obj = f
    end
    n.obj.AnchorPoint, n.obj.ZIndex, n.obj.Visible = Vector2.new(0.5, 0.5), z, false
    n.obj.Parent = parent
    return n
end
-- The light shaft: a tall soft image whose sides fade out through a UIGradient (the texture itself tiles around, it has no soft sides).
local function shaftNode(parent)
    local i = Instance.new("ImageLabel")
    i.BackgroundTransparency, i.BorderSizePixel, i.Image = 1, 0, Assets.resolveUi("shaftGradient")
    i.AnchorPoint, i.ZIndex, i.Visible = Vector2.new(0.5, 0), Plan.Shaft.z, false
    local g = Instance.new("UIGradient")
    g.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.28, 0), NumberSequenceKeypoint.new(0.72, 0), NumberSequenceKeypoint.new(1, 1)})
    g.Parent = i
    i.Parent = parent
    return {obj = i, key = "shaftGradient", shape = "shaft", img = true}
end
local function put(n, x: number, y: number, size: number, color: Color3, opacity: number)
    local o = n.obj
    o.Position, o.Size = UDim2.fromOffset(x, y), UDim2.fromOffset(size, size)
    if n.img then o.ImageColor3, o.ImageTransparency = color, 1 - opacity
    elseif n.stroke then n.stroke.Color, n.stroke.Transparency = color, 1 - opacity
    else o.BackgroundColor3, o.BackgroundTransparency = color, 1 - opacity end
    o.Visible = opacity > 0.01
end
-- FX v3 flipbooks: show cell `Assets.frameAt` (OneShot plays in order over t 0..1, otherwise loops / random). No-op for single images.
local function flip(n, t: number, age: number)
    if not n.img or not Assets.isSheet(n.key) or not Assets.isRealUi(n.key) then return end
    local cell = if Assets.mode(n.key) == "OneShot" and t >= 0 then Assets.frameAt(n.key, t, age, n.seed)
        else math.floor(age * Assets.LoopFps + n.seed * 3) % 16 + 1
    if cell ~= n.cell then n.cell = cell Assets.setCell(n.obj, n.key, cell) end
end
local function hideAll(list) for _, n in list do n.obj.Visible = false end end

local function deviceClass(): string
    local cam = workspace.CurrentCamera
    local short = if cam then math.min(cam.ViewportSize.X, cam.ViewportSize.Y) else 1080
    return Recipes.deviceClass(UserInputService.TouchEnabled, UserInputService.MouseEnabled, short)
end

-- The pool for one hatch panel (back / front layer frames are owned by HatchSequence). Built once, reused for every egg.
function M.ensure(back: Frame, front: Frame)
    local existing = cache[back]
    if existing and existing.front == front then return existing end
    local device = deviceClass()
    local max = Plan.counts(6, device, false)
    local pool = {back = back, front = front, device = device, max = max, bloom = {}, sparks = {}, motes = {}, puffs = {}, shocks = {}, fg = {}, drops = {}}
    pool.shaft = if Assets.isRealUi("shaftGradient") then shaftNode(back) else nil
    for i = 1, max.bloom do pool.bloom[i] = node(back, 22, "glowPlate", "disc", 1) end
    for i = 1, max.motes do pool.motes[i] = node(back, 23, "sparkSheet", "disc", i) end
    for i = 1, max.sparks do pool.sparks[i] = node(back, 23, "starFour", "spark", i) end
    for i = 1, max.puffs do pool.puffs[i] = node(back, 23, "smokeSheet", "puff", i) end
    for i = 1, max.shocks do pool.shocks[i] = node(back, 23, "ringShock", "ring", 1) end
    for i = 1, max.fg do pool.fg[i] = node(front, 24, "starFour", "spark", i) end
    for i = 1, max.drops * 2 do pool.drops[i] = node(front, 24, "glowPlate", "disc", 1) end
    cache[back] = pool
    return pool
end

-- A run of one egg. motion = Theme.MotionEnabled. tier/colour are supplied (and may change) when the server result arrives.
function M.begin(pool, motion: boolean)
    local h = {pool = pool, motion = motion, tier = 1, shaft = 0, color = Color3.fromRGB(70, 205, 170), failed = false, counts = Plan.counts(1, pool.device, not motion),
        palette = {WHITE}, dropColors = {{WHITE}, {WHITE}}, dropTier = {1, 1}}
    h.palette = M.colors(h, h.color)
    M.hide(h)
    return h
end
function M.colors(h, color: Color3)
    local list = Plan.palette(triple(color), h.tier)
    local out = {}
    for i, c in list do out[i] = c3(c) end
    return out
end
-- tier 1..6 (species rarity for the hatch), colour = the rarity colour; failed eggs only get a soft cream puff.
function M.style(h, tier: number, color: Color3, failed: boolean)
    h.tier, h.color, h.failed = math.clamp(tier, 1, 6), color, failed
    h.counts = Plan.counts(h.tier, h.pool.device, not h.motion)
    h.palette = M.colors(h, color)
    h.shaft = 0
    if h.pool.shaft then h.counts, h.shaft = Plan.withShaft(h.tier, h.pool.device, not h.motion, Settings.effects()) end -- 0 or 1 sprite, never over the cap
end
-- The colour / pattern being revealed by a paint bucket (side 1 = colour, 2 = pattern): sets that splash's droplet colours.
function M.paintStyle(h, side: number, color: Color3, revealTier: number)
    h.dropTier[side] = math.clamp(revealTier or 1, 1, 6)
    local list = Plan.palette(triple(color), h.dropTier[side])
    local out = {}
    for i, c in list do out[i] = c3(c) end
    out[#out + 1] = color:Lerp(WHITE, 0.5)
    h.dropColors[side] = out
end

function M.hide(h)
    local p = h.pool
    for _, list in {p.bloom, p.sparks, p.motes, p.puffs, p.shocks, p.fg, p.drops} do hideAll(list) end
    if p.shaft then p.shaft.obj.Visible = false end
end

-- Per frame. vt = visual clock, bp = build progress 0..1, since = seconds after the burst (nil while building), revealed = dino shown.
function M.update(h, vt: number, bp: number, since: number?, revealed: boolean)
    local p, c = h.pool, h.counts
    local cx, cy = Plan.Center.egg[1], Plan.Center.egg[2]
    if not h.motion then
        -- Reduce Motion: one still, soft glow behind the dinosaur once it is shown.
        local disc = p.bloom[1]
        if revealed and disc then put(disc, Plan.Center.dino[1], Plan.Center.dino[2], 320, h.color, 0.22) elseif disc then disc.obj.Visible = false end
        return
    end
    if since then
        local k = math.clamp(since / 0.4, 0, 1)
        cx, cy = cx + (Plan.Center.dino[1] - cx) * k, cy + (Plan.Center.dino[2] - cy) * k
    end
    local failed = h.failed
    local pal = h.palette
    -- light shaft (Epic+, one sprite, behind the bloom): fades in with the build-up, then eases down; hidden for a failed egg
    local sh = p.shaft
    if sh then
        if h.shaft > 0 and not failed then
            local k, a = Plan.shaftLook(bp, since)
            local o = sh.obj
            o.Position, o.Size = UDim2.fromOffset(cx, 0), UDim2.fromOffset(Plan.Shaft.width, Plan.Shaft.height * k)
            o.ImageColor3, o.ImageTransparency = h.color:Lerp(WHITE, 0.55), 1 - a
            o.Visible = a > 0.01
        else sh.obj.Visible = false end
    end
    -- bloom: three soft discs, inner light to outer deep, growing through the build-up
    local grow = Plan.bloomScale(bp, since)
    for i = 1, p.bloom and c.bloom or 0 do
        local fade = if failed and since then math.clamp(1 - since / 0.5, 0, 1) else 1
        local col = h.color:Lerp(WHITE, 0.5 - 0.22 * (i - 1))
        put(p.bloom[i], cx, cy, (150 + 110 * (i - 1)) * grow * (1 + 0.04 * Recipes.pulse(vt)), col, Plan.bloomAlpha(i, bp, since) * fade)
    end
    -- rim sparks: colour-matched, front/back depth
    local showSparks = not failed or not since
    for i, n in p.sparks do
        if i <= c.sparks and showSparks then
            local dx, dy, depth, opacity, size = Plan.rimSpark(i, c.sparks, vt, h.tier, bp)
            n.obj.ZIndex = if depth > 0 then 23 else 22
            flip(n, ((vt * 0.8 + i * 0.37) % 1), vt)
            put(n, cx + dx, cy + dy, size, pal[(i - 1) % #pal + 1], opacity)
        else n.obj.Visible = false end
    end
    -- background motes
    for i, n in p.motes do
        if i <= c.motes and (not failed or not since) then
            local x, y, size, opacity = Plan.mote(i, vt, h.tier)
            flip(n, ((vt * 0.6 + i * 0.29) % 1), vt)
            put(n, x, y, size, pal[(i * 2 - 1) % #pal + 1]:Lerp(WHITE, 0.35), opacity * (0.4 + 0.6 * math.clamp(bp * 2, 0, 1)))
        else n.obj.Visible = false end
    end
    -- burst: smoke puffs + shock rings (hidden before the burst)
    for i, n in p.puffs do
        if since and i <= c.puffs then
            local dx, dy, size, opacity = Plan.puff(i, c.puffs, since)
            flip(n, since / Plan.Limits.puffLife, since) -- smoke-anime poof: grows, then breaks into curls
            put(n, cx + dx, cy + dy, size, if failed then Color3.fromRGB(255, 244, 214) else h.color:Lerp(WHITE, 0.6), opacity)
        else n.obj.Visible = false end
    end
    for i, n in p.shocks do
        if since and not failed and i <= c.shocks then
            local size, opacity = Plan.shock(i, since)
            put(n, cx, cy, size, pal[(i - 1) % #pal + 1]:Lerp(WHITE, 0.3), opacity)
        else n.obj.Visible = false end
    end
    -- foreground sparkle pass: only after the reveal, only in the side margins
    for i, n in p.fg do
        if since and revealed and not failed and i <= c.fg then
            local x, y, size, opacity = Plan.fgSpark(i, c.fg, vt)
            flip(n, ((vt * 0.7 + i * 0.41) % 1), vt)
            put(n, x, y, size, pal[(i * 3 - 1) % #pal + 1]:Lerp(WHITE, 0.4), opacity * math.clamp((since - 0.5) / 0.6, 0, 1))
        else n.obj.Visible = false end
    end
end

-- Paint bucket splash droplets (side 1 colour / 2 pattern). since = seconds after impact (nil / negative = hide). x, y = splash point.
function M.splash(h, side: number, x: number, y: number, since: number?)
    local p = h.pool
    if not h.motion then return end
    local per = p.max.drops
    local n = if h.counts.drops > 0 then math.min(per, Plan.counts(h.dropTier[side], p.device, false).drops) else 0
    local colors = h.dropColors[side]
    for j = 1, per do
        local nd = p.drops[(side - 1) * per + j]
        if since and since >= 0 and j <= n then
            local dx, dy, opacity, size = Plan.drop(j, n, since, if side == 1 then -1 else 1)
            put(nd, x + dx, y + dy, size, colors[(j - 1) % #colors + 1], opacity)
        else nd.obj.Visible = false end
    end
end

return M
