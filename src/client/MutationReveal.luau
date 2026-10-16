--!nonstrict
-- BD-162: draws Shared/MutationRevealPlan in the hatch. A small pooled sprite set (built once per hatch panel, reused for every egg)
-- on the FRONT layer frame, centred on the dinosaur: a soft glow, thin rings, mist puffs and a few motif sprites in the mutation's own
-- MutationLook colours. Textures only come from EffectAssets keys (real fx3 sheets when uploaded, otherwise native rounded shapes).
-- Effects Full / Lite / Off and Reduce Motion are applied by Plan.counts. Never touches the server outcome or the HatchV2 egg.
local UserInputService = game:GetService("UserInputService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Plan = require(Shared.MutationRevealPlan)
local Look = require(Shared.MutationLook)
local Assets = require(Shared.EffectAssets)
local Recipes = require(Shared.FxRecipes)
local Settings = require(Shared.SettingsModel)

local M = {}
local cache = setmetatable({}, {__mode = "k"})
local WHITE = Color3.new(1, 1, 1)

local function node(parent, key: string, shape: string, seed: number)
    local n = {key = key, shape = shape, seed = seed}
    if Assets.isRealUi(key) then
        local i = Instance.new("ImageLabel")
        i.BackgroundTransparency, i.BorderSizePixel, i.Image = 1, 0, Assets.resolveUi(key)
        Assets.setCell(i, key, seed)
        n.obj, n.img = i, true
    else
        local f = Instance.new("Frame")
        f.BorderSizePixel = 0
        if shape == "spark" then f.Rotation = 45
        else local c = Instance.new("UICorner") c.CornerRadius = UDim.new(1, 0) c.Parent = f end
        if shape == "ring" then
            f.BackgroundTransparency = 1
            local s = Instance.new("UIStroke") s.Thickness = 3 s.Parent = f
            n.stroke = s
        end
        n.obj = f
    end
    n.obj.AnchorPoint, n.obj.ZIndex, n.obj.Visible = Vector2.new(0.5, 0.5), 24, false
    n.obj.Parent = parent
    return n
end
local function put(n, x: number, y: number, size: number, color: Color3, opacity: number, rot: number?)
    local o = n.obj
    o.Position, o.Size = UDim2.fromOffset(x, y), UDim2.fromOffset(size, size)
    if rot and not n.stroke then o.Rotation = rot + (if n.shape == "spark" then 45 else 0) end
    if n.img then o.ImageColor3, o.ImageTransparency = color, 1 - opacity
    elseif n.stroke then n.stroke.Color, n.stroke.Transparency = color, 1 - opacity
    else o.BackgroundColor3, o.BackgroundTransparency = color, 1 - opacity end
    o.Visible = opacity > 0.01 and size > 0
end
local function c3(c) return Color3.fromRGB(c[1], c[2], c[3]) end
local function hideList(list) for _, n in list do n.obj.Visible = false end end

local function deviceClass(): string
    local cam = workspace.CurrentCamera
    local short = if cam then math.min(cam.ViewportSize.X, cam.ViewportSize.Y) else 1080
    return Recipes.deviceClass(UserInputService.TouchEnabled, UserInputService.MouseEnabled, short)
end

-- Built once per front layer. Motif sprites are rebuilt only when the next egg's mutation uses a different texture or shape.
local function pool(front: Frame)
    local p = cache[front]
    if p then return p end
    p = {front = front, glow = node(front, "glowPlate", "disc", 1), rings = {}, puffs = {}, motifs = {}, motifKey = "", device = deviceClass()}
    for i = 1, 2 do p.rings[i] = node(front, "ringShock", "ring", 1) end
    for i = 1, 3 do p.puffs[i] = node(front, "smokeSheet", "disc", i) end
    cache[front] = p
    return p
end
local function motifs(p, entry)
    local tag = entry.key .. "/" .. entry.shape
    if p.motifKey == tag then return end
    for _, n in p.motifs do n.obj:Destroy() end
    table.clear(p.motifs)
    for i = 1, Plan.Caps[p.device] or Plan.Caps.desktop do p.motifs[i] = node(p.front, entry.key, entry.shape, i) end
    p.motifKey = tag
end

-- Start a run for one hatched dino. Returns nil when the egg has no (known) mutation.
function M.begin(front: Frame, mutationId: any, motion: boolean)
    local look = if type(mutationId) == "string" then Look.get(mutationId) else nil
    if not look then return nil end
    local p = pool(front)
    local entry = Plan.Motifs[look.id]
    local counts = Plan.counts(look.id, p.device, Settings.effects(), not motion)
    if counts.motifs > 0 then motifs(p, entry) end
    return {
        pool = p, id = look.id, counts = counts, loop = Plan.loopCount(counts), still = not motion,
        rim = c3(look.rim), spark = c3(look.spark), mist = c3(look.mist):Lerp(WHITE, 0.35),
    }
end

function M.hide(h)
    if not h then return end
    local p = h.pool
    p.glow.obj.Visible = false
    hideList(p.rings) hideList(p.puffs) hideList(p.motifs)
end

-- Per frame. since = seconds after the reveal started (nil before it: nothing shows yet).
function M.update(h, since: number?)
    if not h then return end
    if not since then M.hide(h) return end
    local p, c, id = h.pool, h.counts, h.id
    local cx, cy = Plan.Center[1], Plan.Center[2]
    local size, alpha = Plan.glow(id, since)
    if h.still then size, alpha = Plan.StillGlow[1], Plan.StillGlow[2] end
    put(p.glow, cx, cy, size, h.rim, alpha)
    for i, ring in p.rings do
        if i <= c.rings then
            local rs, ra = Plan.ring(i, since)
            put(ring, cx, cy, rs, h.rim, ra)
        else ring.obj.Visible = false end
    end
    for i, puff in p.puffs do
        if i <= c.puffs then
            local dx, dy, ps, pa = Plan.puff(i, c.puffs, since)
            put(puff, cx + dx, cy + dy, ps, h.mist, pa)
        else puff.obj.Visible = false end
    end
    local live = if since < Plan.Limits.burstLife then c.motifs else h.loop
    for i, m in p.motifs do
        if i <= live then
            local dx, dy, ms, ma, rot = Plan.motif(id, i, c.motifs, since)
            local col
            if id == "aurora" then col = c3(Plan.AuroraCycle[Plan.colorIndex(id, i)]) else col = if Plan.colorIndex(id, i) == 1 then h.rim else h.spark end
            put(m, cx + dx, cy + dy, ms, col, ma, rot)
        else m.obj.Visible = false end
    end
end

return M
