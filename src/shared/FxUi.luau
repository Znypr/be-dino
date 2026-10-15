--!nonstrict
-- docs/93: animated FX previews inside normal UI (shop cards, menus). ParticleEmitter / Beam / Trail do not draw inside
-- ViewportFrames, so this is the 2D twin of client/FxRig: it reads the SAME Shared/FxRecipes layers and plays them as pooled
-- sprites (soft glow discs, orbit dots with front/back depth, particle sprites, a trailing ribbon behind a runner orb).
-- One shared 30 Hz loop for all previews; a preview stops by itself when its frame leaves the game. Reduce Motion: aura/
-- mutation show one still glow; trails return nil so the caller keeps the static ribbon art.
local RunService = game:GetService("RunService")
local Recipes = require(script.Parent.FxRecipes)
local Assets = require(script.Parent.EffectAssets)

local Ui = {}
local MAX_ACTIVE = 8
local active = {}
local connection
local clock = 0

local function c3(c) return Color3.fromRGB(math.clamp(math.floor(c[1] + 0.5), 0, 255), math.clamp(math.floor(c[2] + 0.5), 0, 255), math.clamp(math.floor(c[3] + 0.5), 0, 255)) end
local function gradient(colors, t: number)
    if #colors == 1 then return colors[1] end
    local f = math.clamp(t, 0, 1) * (#colors - 1)
    local i = math.min(math.floor(f) + 1, #colors - 1)
    return Recipes.mix(colors[i], colors[i + 1], f - (i - 1))
end

local function dot(parent, z: number, circle: boolean): Frame
    local f = Instance.new("Frame")
    f.AnchorPoint, f.BorderSizePixel, f.ZIndex, f.Visible = Vector2.new(0.5, 0.5), 0, z, false
    if circle then local c = Instance.new("UICorner") c.CornerRadius = UDim.new(1, 0) c.Parent = f end
    f.Parent = parent
    return f
end
local function sprite(parent, z: number, texture: string): ImageLabel
    local i = Instance.new("ImageLabel")
    i.BackgroundTransparency, i.BorderSizePixel, i.Image, i.AnchorPoint, i.ZIndex, i.Visible = 1, 0, texture, Vector2.new(0.5, 0.5), z, false
    i.Parent = parent
    return i
end
local function place(obj, x: number, y: number, px: number, color, transparency: number)
    obj.Position = UDim2.fromScale(x, y)
    obj.Size = UDim2.fromOffset(px, px)
    if obj:IsA("ImageLabel") then obj.ImageColor3, obj.ImageTransparency = c3(color), transparency
    else obj.BackgroundColor3, obj.BackgroundTransparency = c3(color), transparency end
    obj.Visible = true
end

local function buildLayer(h, layer)
    local z = h.z
    local L = {layer = layer, kind = layer.kind}
    local k = layer.kind
    if k == "glow" then
        L.discs = {}
        -- A real glowPlate upload (Blender, docs/93 section 8) replaces the plain discs automatically; until then rounded frames.
        local plate = Assets.isReal("glowPlate")
        for i = 1, 3 do L.discs[i] = if plate then sprite(h.frame, z, Assets.resolveUi("glowPlate")) else dot(h.frame, z, true) end
    elseif k == "emitter" then
        L.pool, L.acc = {}, 0
        local cap = math.clamp(math.ceil(layer.rate * layer.life * 2.2) + 1, 3, 14)
        local tex = Assets.resolveUi(layer.tex) -- built-in sprite while an upload has no alpha (EffectAssets.HasAlpha)
        if layer.shape == "Disc" then
            L.ripples = true
            if Assets.isRealUi(layer.tex) then
                -- real thin-ring texture (ringShock): tinted sprite instead of a stroked frame
                for i = 1, 3 do L.pool[i] = {obj = sprite(h.frame, z, tex), age = 1e9, life = layer.life} end
            else
                for i = 1, 3 do L.pool[i] = {obj = dot(h.frame, z, true), age = 1e9, life = layer.life} local s = Instance.new("UIStroke") s.Thickness = 2 s.Parent = L.pool[i].obj L.pool[i].obj.BackgroundTransparency = 1 L.pool[i].stroke = s end
            end
        else
            for i = 1, cap do L.pool[i] = {obj = sprite(h.frame, z + 1, tex), age = 1e9, life = layer.life, x = 0, y = 0, vx = 0, vy = 0, rot = 0} end
        end
    elseif k == "pillar" then
        -- FX v3 rays pillar: one sprite standing behind the dino, pulsing slowly (built-in sparkle until the upload resolves)
        L.img = sprite(h.frame, z - 1, Assets.resolveUi(layer.tex))
    elseif k == "ring" or k == "spiral" then
        L.dots = {}
        local n = if k == "ring" then 9 else 8
        for i = 1, n do L.dots[i] = dot(h.frame, z, true) end
    elseif k == "trail" then
        L.samples = {}
        local n = if layer.id == "ribbon" then 24 elseif layer.id == "under" then 14 else 0 -- BD-215: long, readable ribbon
        for i = 1, n do L.samples[i] = dot(h.frame, z - 1, true) end
    end
    return L
end

local function runner(h, time: number)
    local phase = (time * 0.32) % 1
    return 0.14 + 0.72 * phase, 0.52 + 0.1 * math.sin(phase * math.pi * 2) - 0.05
end

local function stepHandle(h, dt: number)
    local frame = h.frame
    local size = frame.AbsoluteSize
    local unit = math.max(math.min(size.X, size.Y), 24)
    h.time += dt
    local time = h.time
    local fade = Recipes.easeOutCubic(time / Recipes.Timing.fadeIn)
    local aura = h.kind ~= "trail"
    if h.orb then
        if aura then
            h.orb.Position = UDim2.fromScale(0.5, 0.58)
        else
            local rx, ry = runner(h, time)
            h.orb.Position = UDim2.fromScale(rx, ry)
        end
    end
    local headX, headY = runner(h, time)
    local pulse = if h.reduced then 0.5 else Recipes.pulse(time)
    for _, L in h.layers do
        local layer, k = L.layer, L.kind
        if k == "glow" then
            for i, d in L.discs do
                local r = unit * (0.55 + 0.22 * i) * (0.92 + 0.08 * pulse)
                place(d, 0.5, if aura then 0.58 else 0.55, r, layer.color[1], 0.78 + 0.07 * i + (1 - fade) * 0.2)
            end
        elseif k == "emitter" then
            local sizePx = layer.size * unit * 0.3
            if L.ripples then
                L.acc += dt * layer.rate * 2
                if L.acc >= 1 then
                    L.acc -= 1
                    for _, p in L.pool do if p.age > p.life then p.age = 0 break end end
                end
                for _, p in L.pool do
                    p.age += dt
                    if p.age <= p.life then
                        local t = p.age / p.life
                        local d = unit * (0.3 + 0.9 * t)
                        local c = gradient(layer.color, t)
                        p.obj.Position = UDim2.fromScale(0.5, 0.78)
                        p.obj.Size = UDim2.fromOffset(d, d * 0.32)
                        p.obj.Visible = true
                        if p.stroke then p.stroke.Color, p.stroke.Transparency = c3(c), 1 - layer.alpha * (1 - t) * 0.8
                        else p.obj.ImageColor3, p.obj.ImageTransparency = c3(c), 1 - layer.alpha * (1 - t) * 0.8 end
                    else p.obj.Visible = false end
                end
            else
                local emits = not layer.onlyMoving or not aura
                L.acc += dt * layer.rate * 2.2 * (if emits then 1 else 0)
                while L.acc >= 1 do
                    L.acc -= 1
                    for _, p in L.pool do
                        if p.age > p.life then
                            p.age = 0
                            p.seed, p.cell = math.random(16), 0
                            if layer.flat then
                                p.x, p.y, p.vx, p.vy = 0.5, 0.8, 0, 0 -- swirl at the feet
                            elseif aura then
                                p.x, p.y = 0.28 + math.random() * 0.44, 0.7 + math.random() * 0.08
                                p.vx, p.vy = (math.random() - 0.5) * 0.04, -(0.05 + layer.rise * 0.035 + layer.speed * 0.02)
                            else
                                p.x, p.y = headX - 0.04, headY + (math.random() - 0.5) * 0.08
                                p.vx, p.vy = -(0.02 + layer.speed * 0.03), (math.random() - 0.5) * 0.04 - layer.rise * 0.02
                            end
                            break
                        end
                    end
                end
                for _, p in L.pool do
                    p.age += dt
                    if p.age <= p.life then
                        local t = p.age / p.life
                        p.x += p.vx * dt p.y += p.vy * dt
                        -- flipbook (FX v3): step through the 4x4 cells like the world emitter (OneShot in order, Random one shape, Loop cycles)
                        local cell = Assets.frameAt(layer.tex, t, p.age, p.seed or 1)
                        if cell ~= p.cell then p.cell = cell Assets.setCell(p.obj, layer.tex, cell) end
                        local curve = if layer.curve == "sizePop" then Recipes.Curves.sizePop else Recipes.Curves.sizeGrow
                        local px = math.max(2, sizePx * Recipes.sample(curve, t) * (if layer.curve == "sizeGrow" then 2.2 else 1.4))
                        local opacity = layer.alpha * math.clamp((1 - Recipes.sample(Recipes.Curves.fadeInOut, t)) / 0.7, 0, 1) * fade
                        p.obj.Rotation = p.rot + (layer.spin or 0) * p.age
                        place(p.obj, p.x, p.y, px, gradient(layer.color, t), 1 - opacity)
                        if layer.flat then p.obj.Size = UDim2.fromOffset(px * 1.6, px * 0.6) end
                    else p.obj.Visible = false end
                end
            end
        elseif k == "pillar" and Assets.isRealUi(layer.tex) then
            local glow = if h.reduced then 0.5 else Recipes.pulse(time, layer.hz)
            place(L.img, 0.5, 0.42, unit * 0.95, layer.color[#layer.color], 1 - layer.alpha * (0.55 + 0.45 * glow) * fade)
        elseif k == "ring" or k == "spiral" then
            local n = #L.dots
            local rx = 0.2 + layer.radius * 0.07
            for i, d in L.dots do
                local a = time * layer.spin * 1.4 + (i - 1) * (2 * math.pi / n)
                local depth = math.sin(a) -- +1 front, -1 back
                local x, y
                if k == "ring" then
                    x, y = 0.5 + math.cos(a) * rx, 0.58 + (layer.height * -0.05) + depth * 0.075
                else
                    local u = (i - 1) / (n - 1)
                    x, y = 0.5 + math.cos(a + u * 3) * rx * (1 - 0.35 * u), 0.8 - u * 0.5 + depth * 0.03
                end
                local px = unit * (0.045 + layer.width * 0.18) * (0.75 + 0.25 * depth)
                d.ZIndex = if depth > 0 then h.z + 3 else h.z - 1 -- orbit passes in FRONT of and BEHIND the dino: depth
                place(d, x, y, px, gradient(layer.color, (i - 1) / math.max(n - 1, 1)), 1 - layer.alpha * (0.55 + 0.35 * depth) * fade)
            end
        elseif k == "trail" and #L.samples > 0 then
            if not h.history then h.history = {} end
            local hist = h.history
            if layer.id == "ribbon" then
                h.sampleClock = (h.sampleClock or 0) + dt
                if h.sampleClock >= 0.045 then
                    h.sampleClock = 0
                    table.insert(hist, 1, {headX, headY})
                    if #hist > 34 then table.remove(hist) end
                end
            end
            local n = #L.samples
            for i, d in L.samples do
                local s = hist[math.floor((i - 1) * #hist / n) + 1]
                if s then
                    local t = (i - 1) / n
                    local wrapped = math.abs(s[1] - headX) > 0.6 -- the runner looped around: hide the old tail
                    if wrapped then d.Visible = false
                    else
                        local px = unit * (0.09 + layer.width * 0.18) * (1 - t * 0.7) * (if layer.id == "under" then 1.5 else 1)
                        place(d, s[1] - 0.01, s[2], px, gradient(layer.color, t), 1 - layer.alpha * (1 - t * 0.9) * fade)
                    end
                else d.Visible = false end
            end
        end
    end
end

local function kill(h)
    if h.frame then h.frame:Destroy() end
    h.frame = nil
end

local function loop(dt: number)
    clock += dt
    if clock < 1 / 30 then return end
    local step = clock
    clock = 0
    for i = #active, 1, -1 do
        local h = active[i]
        if not h.frame or not h.frame.Parent or not h.frame:IsDescendantOf(game) then
            kill(h) table.remove(active, i)
        elseif h.frame.Parent and h.frame.Visible and h.frame.AbsoluteSize.X > 0 and not (h.root:IsA("GuiObject") and not h.root.Visible) then
            stepHandle(h, math.min(step, 0.1))
        end
    end
    if #active == 0 and connection then connection:Disconnect() connection = nil end
end

-- kind: "aura" | "trail" | "mutation"; item: ProgressionConfig row or MutationLook entry. Returns a handle {destroy} or nil
-- (Reduce Motion trail, over the preview cap, unknown kind): the caller keeps its static art.
function Ui.mount(parent: GuiObject, kind: string, item, opts)
    opts = opts or {}
    if not item then return nil end
    if #active >= MAX_ACTIVE then
        -- A hero preview (hatch dino, Index / details hero) takes the slot of the oldest small one; small previews just wait.
        local victim
        if opts.hero then for i, other in active do if not other.hero and not victim then victim = i end end end
        if not victim then return nil end
        kill(active[victim]) table.remove(active, victim)
    end
    if opts.reduce and kind == "trail" then return nil end
    local resolved = Recipes.resolve(kind, item, {device = opts.device or "phone", reduce = opts.reduce, detail = if opts.hero then nil else opts.detail})
    if #resolved.layers == 0 then return nil end
    local frame = Instance.new("Frame")
    frame.Name, frame.BackgroundTransparency, frame.BorderSizePixel, frame.ClipsDescendants = "FxUi_" .. kind .. "_" .. tostring(item.id), 1, 0, true
    frame.Size, frame.ZIndex = UDim2.fromScale(1, 1), parent.ZIndex + 1
    frame.Active = false
    frame.Parent = parent
    local h = {frame = frame, root = parent, kind = kind, resolved = resolved, z = parent.ZIndex + 2, time = 0, layers = {}, reduced = opts.reduce == true, hero = opts.hero == true}
    h.orb = dot(frame, h.z + 1, true)
    h.orb.Size = UDim2.fromScale(if kind == "trail" then 0.22 else 0.16, if kind == "trail" then 0.22 else 0.16)
    h.orb.SizeConstraint = Enum.SizeConstraint.RelativeYY
    h.orb.BackgroundColor3, h.orb.BackgroundTransparency, h.orb.Visible = Color3.fromRGB(20, 32, 53), 0, kind == "trail"
    for _, layer in resolved.layers do table.insert(h.layers, buildLayer(h, layer)) end
    if opts.reduce then stepHandle(h, 0.5) return {destroy = function() kill(h) end, frame = frame} end
    table.insert(active, h)
    if not connection then connection = RunService.Heartbeat:Connect(loop) end
    return {destroy = function() kill(h) end, resolved = resolved, frame = frame}
end

-- Shop / menu hook (UITheme.icon): "trail_<id>" replaces the static ribbon art with the live preview (static art stays under
-- it and returns when Reduce Motion is on); "aura_<id>" overlays the animated aura on the existing icon.
function Ui.decorateIcon(icon: GuiObject, id: string, reduce: boolean)
    local Config = require(script.Parent.ProgressionConfig)
    local Rules = require(script.Parent.ProgressionRules)
    local trailId = string.match(id, "^trail_(%w+)$")
    local auraId = string.match(id, "^aura_(%w+)$")
    if trailId then
        local handle = Ui.mount(icon, "trail", Rules.item(Config.Trails, trailId), {reduce = reduce})
        if handle then for _, child in icon:GetChildren() do if child:IsA("GuiObject") and not string.match(child.Name, "^FxUi_") then child.Visible = false end end end
        return handle
    elseif auraId then
        return Ui.mount(icon, "aura", Rules.item(Config.Auras, auraId), {reduce = reduce})
    end
    return nil
end

Ui.activeCount = function() return #active end
Ui.MaxActive = MAX_ACTIVE
return Ui
