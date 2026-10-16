--!nonstrict
-- BD-397 (docs/114): the v2 hatch egg, behind Config.HatchV2. ONE ViewportFrame over the hatch panel (824 x 402 virtual px)
-- holds the generated 3D egg (HatchV2Assets.egg, loaded by the server into ReplicatedStorage.HatchV2Models) and the two paint
-- buckets (PLACEHOLDER barrel mesh until the bucket mesh exists). The paint lands on the egg's own texture: ONE EditableImage
-- (HatchV2Plan.Budget bake size, 256 KiB on desktop) rewritten a few times per second from the pure HatchPaintBake composite
-- (base coat flood + drips from the left bucket's splats, accent coat only where the gene pattern mask is, pattern mask from
-- LowPolyPattern.mask3 over the egg's position map, same approach as docs/105). The liquid arc, splash crown, 2D drip streaks
-- and the wet gloss are pooled 2D sprites over the viewport (existing fx3 alpha sheets tinted with the paint colour) and the
-- MeshPart's reflectance; ViewportFrames do not draw ParticleEmitters or Beams, which is why the splash is 2D.
-- Fallback chain (never blank, never a cube): no egg mesh -> create() returns nil and HatchSequence runs the shipped v1 look;
-- no texture read -> flat shading bake; no position map -> UV-space pattern; no EditableImage (budget, permission) -> the mesh
-- is tinted by MeshPart.Color with the same timing; no bucket mesh -> the arc and splash play without a bucket.
-- Presentation only: never reads or changes genes, odds or saved data. Reduce Motion: the finished egg is shown at once.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local AssetService = game:GetService("AssetService")
local UserInputService = game:GetService("UserInputService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Plan = require(Shared.HatchV2Plan)
local Bake = require(Shared.HatchPaintBake)
local Assets = require(Shared.HatchV2Assets)
local Pattern = require(Shared.LowPolyPattern)
local Overlays = require(Shared.ConditionOverlays)
local Fx = require(Shared.EffectAssets)
local Recipes = require(Shared.FxRecipes)

local M = {}
local WHITE = Color3.new(1, 1, 1)
local CREAM = {.9, .9, .93} -- bare shell: a neutral pale grey-white, so even a Cream gene reads when it lands (Studio pass 2)
local W, H = Plan.ScreenWidthPx, Plan.ScreenHeightPx
local cache = setmetatable({}, {__mode = "k"}) -- back frame -> scene (viewport, parts, pools, image), reused for every egg
local sources = {} -- asset key -> {buf, posmap, size} | "loading" | false (one read per session)

local function deviceClass(): string
    local cam = workspace.CurrentCamera
    local short = if cam then math.min(cam.ViewportSize.X, cam.ViewportSize.Y) else 1080
    return Recipes.deviceClass(UserInputService.TouchEnabled, UserInputService.MouseEnabled, short)
end
local function triple(c: Color3) return {c.R, c.G, c.B} end
local function yielder(every: number) return function(y) if y % every == every - 1 then task.wait() end end end

function M.available(): boolean
    local folder = ReplicatedStorage:FindFirstChild(Assets.FolderName)
    local egg = folder and folder:FindFirstChild("egg")
    return egg ~= nil and egg:IsA("MeshPart")
end

-- 2D sprite helpers (pooled, created once per panel).
local function sprite(parent, z: number, key: string): ImageLabel
    local i = Instance.new("ImageLabel")
    i.BackgroundTransparency, i.BorderSizePixel, i.AnchorPoint, i.ZIndex, i.Visible = 1, 0, Vector2.new(.5, .5), z, false
    i.Image = Fx.resolveUi(key)
    i.ScaleType = Enum.ScaleType.Stretch
    i.Parent = parent
    return i
end
local function streak(parent, z: number): Frame
    local f = Instance.new("Frame")
    f.BackgroundColor3, f.BorderSizePixel, f.AnchorPoint, f.ZIndex, f.Visible = WHITE, 0, Vector2.new(.5, 0), z, false
    local c = Instance.new("UICorner") c.CornerRadius = UDim.new(1, 0) c.Parent = f
    local g = Instance.new("UIGradient")
    g.Rotation = 90
    g.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(.7, .15), NumberSequenceKeypoint.new(1, 1)})
    g.Parent = f
    f.Parent = parent
    return f
end
local function show(i: GuiObject, x: number, y: number, w: number, h: number, color: Color3, opacity: number)
    i.Position, i.Size = UDim2.fromOffset(x, y), UDim2.fromOffset(w, h)
    if i:IsA("ImageLabel") then i.ImageColor3, i.ImageTransparency = color, 1 - opacity else i.BackgroundColor3, i.BackgroundTransparency = color, 1 - opacity end
    i.Visible = opacity > .02
end

-- The persistent scene for one hatch panel: viewport (between the back and front FX layers), camera, egg, buckets, pools.
local function scene(back: Frame, front: Frame)
    local s = cache[back]
    if s and s.front == front and s.viewport.Parent == back then return s end
    local folder = ReplicatedStorage:FindFirstChild(Assets.FolderName)
    local eggSource = folder and folder:FindFirstChild("egg")
    if not eggSource or not eggSource:IsA("MeshPart") then return nil end
    local device = deviceClass()
    local budget = Plan.budget(device)
    local viewport = Instance.new("ViewportFrame")
    viewport.Name, viewport.BackgroundTransparency, viewport.Size, viewport.ZIndex = "HatchEggV2", 1, UDim2.fromOffset(W, H), 23
    viewport.Ambient, viewport.LightColor, viewport.LightDirection = Color3.fromRGB(196, 196, 206), Color3.fromRGB(255, 244, 222), Vector3.new(-.4, -.8, -.6)
    viewport.Parent = back
    local world = Instance.new("WorldModel") world.Parent = viewport
    local camera = Instance.new("Camera")
    camera.FieldOfView, camera.Parent = Plan.Camera.fov, viewport
    viewport.CurrentCamera = camera
    -- camera: looks along -dir at the egg centre, offset so the egg projects onto HatchFxPlan.Center.egg
    local dir = Vector3.new(Plan.Camera.dir[1], Plan.Camera.dir[2], Plan.Camera.dir[3]).Unit
    local rot = CFrame.lookAt(dir * Plan.Camera.distance, Vector3.zero).Rotation
    local ex, ey, ez = Plan.eggCameraSpace()
    camera.CFrame = rot + rot:VectorToWorldSpace(-Vector3.new(ex, ey, ez))
    -- egg: scaled to Plan.EggHeight, yawed so its decal (Front = -Z) side faces the camera (+Z)
    local egg = eggSource:Clone()
    egg.Name = "Egg"
    local longest = math.max(egg.Size.X, egg.Size.Y, egg.Size.Z)
    local scale = Plan.EggHeight / math.max(1e-3, egg.Size.Y)
    egg.Size = egg.Size * scale
    egg.CFrame = CFrame.Angles(0, math.pi, 0)
    egg.Material, egg.Reflectance = Enum.Material.SmoothPlastic, 0
    egg.Parent = world
    local buckets = {}
    local bucketSource = folder:FindFirstChild("bucket")
    for i = 1, 2 do
        if bucketSource and bucketSource:IsA("MeshPart") then
            local b = bucketSource:Clone()
            b.Name = "Bucket" .. i
            local bs = Plan.BucketHeight / math.max(1e-3, b.Size.Y)
            b.Size = b.Size * bs
            b.Transparency = 1
            b.Parent = world
            buckets[i] = b
        end
    end
    local pools = {blobs = {}, crown = {{}, {}}, drips = {{}, {}}, puddle = {}}
    for i = 1, budget.streamBlobs do pools.blobs[i] = sprite(front, 25, "smokeSheet") Fx.setCell(pools.blobs[i], "smokeSheet", 1 + (i * 5) % 16) end
    for side = 1, 2 do
        for i = 1, budget.crown do pools.crown[side][i] = sprite(front, 26, "smokeSheet") Fx.setCell(pools.crown[side][i], "smokeSheet", 1 + (i * 3 + side) % 16) end
        for i = 1, budget.drips do pools.drips[side][i] = streak(front, 25) end
        pools.puddle[side] = sprite(front, 25, "smokeSheet") Fx.setCell(pools.puddle[side], "smokeSheet", 6)
    end
    s = {back = back, front = front, viewport = viewport, camera = camera, world = world, egg = egg, eggSize = egg.Size, buckets = buckets,
        pools = pools, budget = budget, device = device, image = nil, imageTried = false, longest = longest * scale}
    cache[back] = s
    return s
end

-- The egg's texture (downsampled to `size`) and position map, read once per session. nil parts are the documented fallbacks.
local function readSource(egg: MeshPart, size: number)
    local sa = egg:FindFirstChildOfClass("SurfaceAppearance")
    local textureId = if sa then sa.ColorMap else egg.TextureID
    local key = tostring(textureId) .. "|" .. tostring(egg.MeshId) .. "@" .. size
    while sources[key] == "loading" do task.wait(.05) end
    if sources[key] ~= nil then return sources[key] or nil end
    sources[key] = "loading"
    local buf = nil
    if textureId and textureId ~= "" then
        local ok, err = pcall(function()
            local img = AssetService:CreateEditableImageAsync(Content.fromUri(textureId))
            if not img then error("no image (budget or permission)") end
            local full = img.Size
            local raw = img:ReadPixelsBuffer(Vector2.zero, full)
            img:Destroy()
            buf = buffer.create(size * size * 4)
            for y = 0, size - 1 do
                local sy = math.min(full.Y - 1, math.floor((y + .5) * full.Y / size))
                for x = 0, size - 1 do
                    local sx = math.min(full.X - 1, math.floor((x + .5) * full.X / size))
                    buffer.writeu32(buf, (y * size + x) * 4, buffer.readu32(raw, (sy * full.X + sx) * 4))
                end
                if y % 32 == 31 then task.wait() end
            end
        end)
        if not ok then warn("[Be Dino] hatch v2 egg texture unreadable (flat shading): " .. tostring(err)) buf = nil end
    end
    local posmap = nil
    local okMesh, errMesh = pcall(function()
        if egg.MeshId == "" then return end
        local mesh = AssetService:CreateEditableMeshAsync(Content.fromUri(egg.MeshId))
        if not mesh then error("no mesh (budget or permission)") end
        local tris = {}
        local sc = egg.Size / egg.MeshSize
        local norm = 1 / math.max(egg.Size.X, egg.Size.Y, egg.Size.Z)
        for _, face in mesh:GetFaces() do
            local verts, uvs = mesh:GetFaceVertices(face), mesh:GetFaceUVs(face)
            if #verts ~= 3 or #uvs ~= 3 then continue end
            local t = {}
            for i = 1, 3 do
                local uv = mesh:GetUV(uvs[i])
                local p = mesh:GetPosition(verts[i]) * sc * norm
                table.insert(t, uv.X) table.insert(t, uv.Y) table.insert(t, p.X) table.insert(t, p.Y) table.insert(t, p.Z)
            end
            table.insert(tris, t)
        end
        mesh:Destroy()
        if #tris > 0 then posmap = Pattern.rasterize(tris, size) end
    end)
    if not okMesh then warn("[Be Dino] hatch v2 egg mesh unreadable (UV-space pattern): " .. tostring(errMesh)) end
    local result = {buf = buf, posmap = posmap, size = size, shade = Bake.shade(buf, size)}
    sources[key] = result
    return result
end

-- One hatch egg. back / front: the HatchSequence FX layers. Returns nil when the egg mesh is not loaded (v1 runs instead).
function M.create(back: Frame, front: Frame, motion: boolean)
    local s = scene(back, front)
    if not s then return nil end
    local h = {s = s, motion = motion, ready = false, mode = "pending", t1 = -1, t2 = -1, lastWrite = 0, writing = false,
        cream = CREAM, base = CREAM, accent = CREAM, plain = true, seed = 1, condition = nil, conditionShown = false, finished = false,
        conditionDecals = {}, colors = {WHITE, WHITE}, impactPx = {{412 - 40, 100}, {412 + 40, 100}}, lipPx = {{0, 0}, {0, 0}},
        impactWorld = {Vector3.zero, Vector3.zero}, splashShown = {false, false}, gen = 0}
    local egg = s.egg
    egg.Size, egg.CFrame, egg.Reflectance, egg.Transparency = s.eggSize, CFrame.Angles(0, math.pi, 0), 0, 0
    for _, d in egg:GetChildren() do if d:IsA("Decal") then d:Destroy() end end
    s.viewport.Visible = true
    for _, b in s.buckets do b.Transparency = 1 end
    M.hideFx(h)
    -- image: one per panel, created once; nil = tint fallback for this and every later egg of the session
    if not s.imageTried then
        s.imageTried = true
        local ok, img = pcall(function() return AssetService:CreateEditableImage({Size = Vector2.new(s.budget.bake, s.budget.bake)}) end)
        s.image = if ok and img then img else nil
        if not s.image then warn("[Be Dino] hatch v2: no EditableImage (budget or permission), tint fallback") end
    end
    if s.image then
        for _, c in egg:GetChildren() do if c:IsA("SurfaceAppearance") then c:Destroy() end end
        egg.TextureContent = Content.fromObject(s.image)
        egg.Color = WHITE
        h.mode = "bake"
        h.out = buffer.create(s.budget.bake * s.budget.bake * 4)
    else
        for _, c in egg:GetChildren() do if c:IsA("SurfaceAppearance") then c:Destroy() end end
        egg.TextureContent = Content.none
        egg.TextureID = ""
        egg.Color = Color3.new(CREAM[1], CREAM[2], CREAM[3])
        h.mode = "tint"
    end
    -- the plain bare egg from the first frame: a flat write at once (the image is black until its first write, Studio pass 2),
    -- then its own facet shading once the source is read
    if h.mode == "bake" then M.write(h, -1, -1, true) end
    task.spawn(function()
        local src = readSource(egg, s.budget.bake)
        if h.finished then return end
        h.src = src
        if h.mode == "bake" and not h.ready then M.write(h, -1, -1, true) end
    end)
    return h
end

function M.hideFx(h)
    local p = h.s.pools
    for _, b in p.blobs do b.Visible = false end
    for side = 1, 2 do
        for _, c in p.crown[side] do c.Visible = false end
        for _, d in p.drips[side] do d.Visible = false end
        p.puddle[side].Visible = false
    end
end

-- Project a world point of the viewport scene to panel px.
local function toPx(h, world: Vector3): (number, number)
    local p = h.s.camera.CFrame:PointToObjectSpace(world)
    local x, y = Plan.project(p.X, p.Y, p.Z, Plan.Camera.fov, W, H)
    return x or 0, y or 0
end

-- Result known: colours and pattern. genes may be nil (no genetics): the two colours are still painted, no pattern.
-- base / accent = Color3 of the left / right bucket; patternId / blend / same from the genes; eggId seeds the splats.
function M.setGenes(h, genes, eggId: string?, base: Color3, accent: Color3, plain: boolean)
    h.gen += 1
    local gen = h.gen
    h.base, h.accent, h.plain = triple(base), triple(accent), plain
    h.colors = {base, if plain then base:Lerp(WHITE, .6) else accent}
    h.seed = Plan.seed(tostring(eggId or "") .. "|" .. tostring(genes and genes.primaryColorId) .. "|" .. tostring(genes and genes.patternId))
    local s = h.s
    local egg = s.egg
    -- world impact points (splat 1 of each coat) for the 2D splash; model side is mirrored by the egg's 180 deg yaw
    for i, side in {-1, 1} do
        local sp = Plan.splats(h.seed, -side, i)[1]
        h.impactWorld[i] = egg.CFrame:PointToWorldSpace(Vector3.new(sp.x, sp.y, sp.z) * s.longest)
        h.impactPx[i] = {toPx(h, h.impactWorld[i])}
    end
    if h.mode ~= "bake" then h.ready = true return end
    task.spawn(function()
        local size = s.budget.bake
        local src = h.src or readSource(egg, size)
        if h.finished or gen ~= h.gen then return end
        h.src = src
        local posmap = src and src.posmap
        local mask = nil
        if not plain and genes and genes.patternId and genes.patternId ~= "01_blank" then
            local weights = table.create(size * size, 1)
            local okMask, m = pcall(Pattern.compute, genes.patternId, Pattern.seed("egg|" .. tostring(genes.patternId)), weights,
                math.clamp((genes.blend or 50) / 100, 0, 1), genes.primaryColorId == genes.secondaryColorId, yielder(16), posmap, size)
            if okMask then mask = m else warn("[Be Dino] hatch v2 pattern failed (plain accent): " .. tostring(m)) end
        end
        if h.finished or gen ~= h.gen then return end
        h.mask = mask
        h.map1 = Bake.revealMap(size, posmap, h.seed, 1, 1, yielder(32))
        h.map2 = Bake.revealMap(size, posmap, h.seed, -1, 2, yielder(32))
        if h.finished or gen ~= h.gen then return end
        h.ready = true
        if h.wantFinal then M.write(h, 99, 99, true) end
    end)
end
function M.setCondition(h, conditionId: string?) h.condition = conditionId end

-- Composite the texture at coat times t1 / t2 and push it to the image (yields; one in flight at a time).
function M.write(h, t1: number, t2: number, force: boolean?)
    local s = h.s
    if h.mode ~= "bake" or not s.image or h.finished then return end
    if h.writing and not force then return end
    local size = s.budget.bake
    local shade = if h.src then h.src.shade else nil
    if not shade then shade = table.create(size * size, 1) end
    local map1 = h.map1 or table.create(size * size, 99)
    local map2 = h.map2 or table.create(size * size, 99)
    h.writing = true
    h.t1, h.t2 = t1, t2
    task.spawn(function()
        local gen = h.gen
        local ok, err = pcall(function()
            Bake.composite(size, shade, h.mask, map1, map2, t1, t2, h.cream, h.base, h.accent, h.out, yielder(if s.device == "phone" then 16 else 48))
            if h.finished or gen ~= h.gen then return end
            s.image:WritePixelsBuffer(Vector2.zero, Vector2.new(size, size), h.out)
        end)
        if not ok then warn("[Be Dino] hatch v2 paint write failed: " .. tostring(err)) end
        h.writing = false
        h.lastWrite = os.clock()
    end)
end

-- Per frame while the build-up runs. t = sequence time, vt = visual clock, ps = HatchTimeline.paintState (nil while the result
-- is pending), durs = timeline durations, shake = {rot, dx, dy, zoom} from the sequence's rattle curves.
function M.update(h, t: number, vt: number, ps, durs, shake)
    local s = h.s
    if h.finished then return end
    local egg = s.egg
    if not h.motion then return end
    local p = durs.paint
    local swayRot, swayDy = Plan.sway(vt)
    local pxPerStud = Plan.pxPerStud()
    -- egg: sway while painting, rattle + push-in later; squash on each impact; wet gloss dries
    local sx, sy, gloss = 1, 1, 0
    local since1, since2 = if ps then ps.left.sinceImpact else -1, if ps then ps.right.sinceImpact else -1
    if ps then
        local a, b = Plan.squash(since1), Plan.squash(since2)
        sx, sy = a * b, (2 - a) * (2 - b)
        gloss = math.max(Plan.gloss(since1), Plan.gloss(since2))
    end
    local rot = (shake and shake.rot or 0) + swayRot * (if ps and ps.pattern >= 1 then 0 else 1)
    local dx, dy = (shake and shake.dx or 0), (shake and shake.dy or 0) + swayDy * (if ps and ps.pattern >= 1 then 0 else 1)
    local zoom = shake and shake.zoom or 1
    egg.Size = s.eggSize * Vector3.new(sx * zoom, sy * zoom, sx * zoom)
    egg.CFrame = CFrame.new(dx / pxPerStud, -dy / pxPerStud, 0) * CFrame.Angles(0, 0, math.rad(-rot)) * CFrame.Angles(0, math.pi, 0)
    egg.Reflectance = gloss
    if not ps then
        for _, b in s.buckets do b.Transparency = 1 end
        return
    end
    -- texture writes while a coat runs
    if h.mode == "bake" and h.ready and not h.writing then
        local active1 = since1 > -.1 and since1 < Plan.Coat.span + .3
        local active2 = since2 > -.1 and since2 < Plan.Coat.span + .3
        if (active1 or active2) and os.clock() - h.lastWrite >= 1 / s.budget.writes then M.write(h, since1, since2) end
    elseif h.mode == "tint" then
        local c = Color3.new(CREAM[1], CREAM[2], CREAM[3]):Lerp(Color3.new(h.base[1], h.base[2], h.base[3]), ps.left.wash)
        if not h.plain then c = c:Lerp(Color3.new(h.accent[1], h.accent[2], h.accent[3]), ps.right.wash * .5) end
        egg.Color = c
    end
    -- buckets, liquid arc, splash crown, 2D drips
    local pools = s.pools
    for i, side in {-1, 1} do
        local b = if i == 1 then ps.left else ps.right
        local sinceStart = b.since
        local x, y, tilt, alpha, squash = Plan.bucketPose(sinceStart, side)
        local bucket = s.buckets[i]
        local lipWorld = Vector3.new(x - side * .32, y + Plan.BucketHeight * .5, 0)
        if bucket then
            local pos = Vector3.new(x, y, 0)
            local half = bucket.Size / 2
            local lip = Vector3.new(-side * half.X * .85, half.Y * .95, 0)
            bucket.CFrame = CFrame.new(pos + lip) * CFrame.Angles(0, 0, math.rad(-tilt)) * CFrame.new(-lip)
            bucket.Transparency = 1 - alpha
            lipWorld = bucket.CFrame:PointToWorldSpace(lip)
        end
        local lx, ly = toPx(h, lipWorld)
        local ix, iy = h.impactPx[i][1], h.impactPx[i][2]
        local color = h.colors[i]
        -- liquid arc
        local strength = Plan.stream(sinceStart)
        local blobs = if strength > 0 and alpha > 0 then Plan.streamBlobs(lx, ly, ix, iy, strength, #pools.blobs) else {}
        for j, blob in pools.blobs do
            local d = blobs[j]
            if d then show(blob, d[1], d[2], d[3] * 3.4, d[3] * 3.4, color, math.min(1, strength * 2)) else blob.Visible = false end -- Studio pass 1: 2.4 x read as a dotted line
        end
        -- splash crown and puddle on impact
        local sinceImpact = b.sinceImpact
        for j, drop in pools.crown[i] do
            local ddx, ddy, size, op = Plan.crown(j, #pools.crown[i], sinceImpact, side, h.seed + i)
            if op > 0 then show(drop, ix + ddx, iy + ddy, size * 2.6, size * 2.6, color, op) else drop.Visible = false end
        end
        local puddle = pools.puddle[i]
        if sinceImpact >= 0 and sinceImpact < .7 then
            local k = sinceImpact / .7
            local grow = 40 + 150 * Plan.easeOut(k)
            show(puddle, ix, iy + 6, grow * 1.3, grow, color, .85 * (1 - k * k))
        else puddle.Visible = false end
        -- drips under the splash
        for j, d in pools.drips[i] do
            local ox, oy, len, width, op = Plan.dripStreak(j, sinceImpact, h.seed + i * 7)
            if ox then
                d.Position, d.Size = UDim2.fromOffset(ix + ox, iy + oy), UDim2.fromOffset(width, len)
                d.BackgroundColor3, d.BackgroundTransparency, d.Visible = color, 1 - op, op > .02
            else d.Visible = false end
        end
    end
    -- condition overlay (cracks, dirt, stars) fades in after the pattern chip
    if h.condition and not h.conditionShown and t >= p.patternEnd + Plan.Condition.delay then
        h.conditionShown = true
        Overlays.apply(egg, h.condition)
        for _, d in egg:GetChildren() do if d:IsA("Decal") then d.Transparency = 1 table.insert(h.conditionDecals, d) end end
    end
    if h.conditionShown then
        local k = math.clamp((t - (p.patternEnd + Plan.Condition.delay)) / Plan.Condition.span, 0, 1)
        for _, d in h.conditionDecals do d.Transparency = 1 - Plan.easeOut(k) end
        egg.Reflectance = math.max(gloss, (Overlays.describe(h.condition).reflectance or 0) * Plan.easeOut(k))
    end
end

-- Fast-forward / Reduce Motion: the finished egg (both coats, pattern, condition) at once.
function M.finish(h)
    if h.finished then return end
    local s = h.s
    M.hideFx(h)
    for _, b in s.buckets do b.Transparency = 1 end
    local egg = s.egg
    egg.Size, egg.CFrame, egg.Reflectance = s.eggSize, CFrame.Angles(0, math.pi, 0), 0
    if h.mode == "bake" then
        if h.ready then M.write(h, 99, 99, true) else h.wantFinal = true end
    elseif h.mode == "tint" then
        local c = Color3.new(h.base[1], h.base[2], h.base[3])
        if not h.plain then c = c:Lerp(Color3.new(h.accent[1], h.accent[2], h.accent[3]), .5) end
        egg.Color = c
    end
    if h.condition and not h.conditionShown then
        h.conditionShown = true
        Overlays.apply(egg, h.condition)
    end
    for _, d in h.conditionDecals do d.Transparency = 0 end
end
-- The burst: the egg leaves the viewport (the v1 shell fragments fly over the panel). The pools are reused by the next egg.
function M.burst(h)
    h.finished = true
    h.gen += 1
    M.hideFx(h)
    local s = h.s
    s.viewport.Visible = false
    for _, b in s.buckets do b.Transparency = 1 end
end
function M.stop(h) M.burst(h) end

return M
