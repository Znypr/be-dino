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
Ui.HeroSmokeSize, Ui.HeroSmokeAlpha, Ui.HeroSmokeRate = 0.4, 0.5, 0.5 -- BD-351 (verify_previews pins them)
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
            -- BD-226: only an alpha upload goes into an ImageLabel (one 256 px cell, tinted). The built-in particle .dds sprites
            -- draw as dark square boxes in 2D UI, so without a real alpha texture the puff is a soft round tinted dot instead.
            local real = Assets.isRealUi(layer.tex)
            for i = 1, cap do L.pool[i] = {obj = if real then sprite(h.frame, z + 1, tex) else dot(h.frame, z + 1, true), age = 1e9, life = layer.life, x = 0, y = 0, vx = 0, vy = 0, rot = 0} end
        end
    elseif k == "pillar" then
        -- FX v3 rays pillar: one sprite standing behind the dino, pulsing slowly (built-in sparkle until the upload resolves)
        if Assets.isRealUi(layer.tex) then L.img = sprite(h.frame, z - 1, Assets.resolveUi(layer.tex)) end -- BD-226: no built-in box
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

-- BD-351: a hero mutation preview lives BEHIND the dinosaur: its frame is a sibling just under the viewport (children of a
-- ViewportFrame always draw over the model), kept on the same rectangle every step. Visibility follows the viewport.
local function syncBehind(h)
    local view, frame = h.root, h.frame
    if not (h.behind and view:IsA("GuiObject")) then return end
    local holder = view.Parent
    if holder and frame.Parent ~= holder then frame.Parent = holder end
    frame.ZIndex = math.max(view.ZIndex - 1, 0)
    frame.AnchorPoint, frame.Position, frame.Visible = view.AnchorPoint, view.Position, view.Visible
    local scale = view:FindFirstChildOfClass("UIScale")
    local k = if scale then scale.Scale else 1
    frame.Size = UDim2.new(view.Size.X.Scale * k, view.Size.X.Offset * k, view.Size.Y.Scale * k, view.Size.Y.Offset * k)
end

local function stepHandle(h, dt: number)
    syncBehind(h)
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
        elseif k == "pillar" and L.img then
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

-- BD-229: shop aura cards. The recipe layers alone read as a faint ring on the coloured card, so an aura icon also gets a
-- HALO drawn BEHIND the coin (sibling of the icon, one ZIndex lower): slowly turning fx3 rays, a looping fx3 swirl about
-- 1.6x the coin, and a few fx3 sparkles drifting up. Tint is the aura colour lifted toward white so it shows on green,
-- blue and purple cards. Strength grows with rarity. Reduce Motion: one still frame (no turning, no sparkles).
local HaloTier = {
    Common = {scale = 1.6, rays = 0.4, swirl = 0.5, swirl2 = 0, sparks = 2, lift = 0.5},
    Rare = {scale = 1.8, rays = 0.55, swirl = 0.68, swirl2 = 0, sparks = 4, lift = 0.45},
    Legendary = {scale = 2.0, rays = 0.72, swirl = 0.8, swirl2 = 0.45, sparks = 6, lift = 0.4},
}
local function buildHalo(h, icon: GuiObject, item)
    local holder = icon.Parent
    if not (holder and holder:IsA("GuiObject")) then return end
    local tier = HaloTier[item.rarity] or HaloTier.Common
    local color = item.color or {255, 255, 255}
    local tint = Recipes.mix(color, {255, 255, 255}, tier.lift)
    local halo = Instance.new("Frame")
    halo.Name, halo.BackgroundTransparency, halo.BorderSizePixel, halo.Active = "FxUi_halo_" .. tostring(item.id), 1, 0, false
    halo.AnchorPoint = Vector2.new(0.5, 0.5)
    halo.ZIndex = math.max(icon.ZIndex - 1, 1)
    halo.Parent = holder
    local z = halo.ZIndex
    local function img(key: string, size: number)
        if not Assets.isRealUi(key) then return nil end -- BD-226: never a built-in sprite (dark boxes) in 2D UI
        local i = sprite(halo, z, Assets.resolveUi(key))
        i.Size, i.Position, i.ImageColor3, i.Visible = UDim2.fromScale(size, size), UDim2.fromScale(0.5, 0.5), c3(tint), true
        Assets.setCell(i, key, 1)
        return i
    end
    local H = {icon = icon, frame = halo, tier = tier, tint = tint, rays = img("rays", 1), swirl = img("swirl", 0.92), sparks = {}}
    if tier.swirl2 > 0 then H.swirl2 = img("swirl", 0.7) end
    if not h.reduced and Assets.isRealUi("sparkSheet") then
        for i = 1, tier.sparks do
            local sp = sprite(halo, z, Assets.resolveUi("sparkSheet"))
            sp.ImageColor3 = c3(Recipes.mix(color, {255, 255, 255}, 0.75))
            H.sparks[i] = {obj = sp, phase = (i - 1) / tier.sparks, x = 0.22 + 0.56 * ((i * 0.618) % 1)}
        end
    end
    h.halo = H
end
local function stepHalo(h)
    local H = h.halo
    if not H or not H.frame.Parent then return end
    local t, tier = if h.reduced then 0 else h.time, H.tier
    local icon, sz, ap = H.icon, H.icon.Size, H.icon.AnchorPoint -- follow the coin if the card lays it out later
    H.frame.Position = icon.Position + UDim2.new(sz.X.Scale * (0.5 - ap.X), sz.X.Offset * (0.5 - ap.X), sz.Y.Scale * (0.5 - ap.Y), sz.Y.Offset * (0.5 - ap.Y))
    H.frame.Size = UDim2.new(sz.X.Scale * tier.scale, sz.X.Offset * tier.scale, sz.Y.Scale * tier.scale, sz.Y.Offset * tier.scale)
    H.frame.Visible = icon.Visible
    local fade = if h.reduced then 1 else Recipes.easeOutCubic(t / Recipes.Timing.fadeIn)
    local breathe = if h.reduced then 0.5 else 0.5 + 0.5 * math.sin(t * 1.6)
    if H.rays then
        H.rays.Rotation = t * 10
        H.rays.ImageTransparency = 1 - tier.rays * (0.8 + 0.2 * breathe) * fade
    end
    if H.swirl then
        H.swirl.Rotation = -t * 14
        Assets.setCell(H.swirl, "swirl", Assets.frameAt("swirl", 0, t, 1))
        H.swirl.ImageTransparency = 1 - tier.swirl * (0.85 + 0.15 * breathe) * fade
        H.swirl.Size = UDim2.fromScale(0.9 + 0.04 * breathe, 0.9 + 0.04 * breathe)
    end
    if H.swirl2 then
        H.swirl2.Rotation = t * 20 + 90
        Assets.setCell(H.swirl2, "swirl", Assets.frameAt("swirl", 0, t, 9))
        H.swirl2.ImageTransparency = 1 - tier.swirl2 * fade
    end
    for _, p in H.sparks do
        local u = (t * 0.45 + p.phase) % 1 -- one gentle rise every ~2 s
        Assets.setCell(p.obj, "sparkSheet", Assets.frameAt("sparkSheet", u, 0, 1))
        p.obj.Position = UDim2.fromScale(p.x + 0.04 * math.sin(u * 6 + p.phase * 6), 0.78 - 0.6 * u)
        p.obj.Size = UDim2.fromScale(0.2, 0.2)
        p.obj.ImageTransparency = 1 - 0.9 * math.sin(u * math.pi) * fade
        p.obj.Visible = true
    end
end

local function kill(h)
    if h.halo then h.halo.frame:Destroy() h.halo = nil end
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
        if h.frame and h.behind then syncBehind(h) end
        if not h.frame or not h.frame.Parent or not h.frame:IsDescendantOf(game) or (h.behind and not h.root:IsDescendantOf(game)) then
            kill(h) table.remove(active, i)
        elseif h.frame.Parent and h.frame.Visible and h.frame.AbsoluteSize.X > 0 and not (h.root:IsA("GuiObject") and not h.root.Visible) then
            stepHandle(h, math.min(step, 0.1))
            stepHalo(h)
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
    if opts.hero and kind == "mutation" then
        -- BD-351 calm hero look: keep the colour glow and sparkles, shrink and thin the smoke so the dino body stays readable.
        for _, layer in resolved.layers do
            if layer.tex == "smokeSheet" then layer.size *= Ui.HeroSmokeSize layer.alpha *= Ui.HeroSmokeAlpha layer.rate *= Ui.HeroSmokeRate end
        end
    end
    local h = {frame = frame, root = parent, kind = kind, resolved = resolved, z = parent.ZIndex + 2, behind = opts.hero == true and kind == "mutation" and parent:IsA("ViewportFrame") and parent.BackgroundTransparency >= 0.95, time = 0, layers = {}, reduced = opts.reduce == true, hero = opts.hero == true}
    h.orb = dot(frame, h.z + 1, true)
    h.orb.Size = UDim2.fromScale(if kind == "trail" then 0.22 else 0.16, if kind == "trail" then 0.22 else 0.16)
    h.orb.SizeConstraint = Enum.SizeConstraint.RelativeYY
    h.orb.BackgroundColor3, h.orb.BackgroundTransparency, h.orb.Visible = Color3.fromRGB(20, 32, 53), 0, kind == "trail"
    for _, layer in resolved.layers do table.insert(h.layers, buildLayer(h, layer)) end
    if opts.halo then buildHalo(h, parent, item) end
    if opts.reduce then stepHandle(h, 0.5) stepHalo(h) return {destroy = function() kill(h) end, frame = frame} end
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
        return Ui.mount(icon, "aura", Rules.item(Config.Auras, auraId), {reduce = reduce, halo = true})
    end
    return nil
end

Ui.activeCount = function() return #active end
Ui.MaxActive = MAX_ACTIVE
return Ui
