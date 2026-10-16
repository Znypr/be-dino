--!nonstrict
-- docs/93: builds ONE dino's anime-style layered effect (aura, trail or mutation) from a Shared/FxRecipes recipe.
-- Client only; local instances, nothing replicates. Pooled instances, one invisible anchor part at most, every layer
-- counted against the device budget in the recipe. Rig API:
--   local rig = FxRig.attach(root, "aura"|"trail"|"mutation", item, {reduce=bool, detail="full"|"lite", device=?})
--   rig:update(scale, time, moving)   -- call at <= 30 Hz
--   rig:burst()                       -- one-shot pop (also fired once on attach for aura/mutation, never with Reduce Motion)
--   rig:destroy()                     -- returns every instance to the pool
-- World only: ParticleEmitter / Beam / Trail do not draw inside ViewportFrames, so menus use Shared/FxUi (same recipes).
local UserInputService = game:GetService("UserInputService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Recipes = require(Shared.FxRecipes)
local Assets = require(Shared.EffectAssets)
local Slots = require(Shared.AssetSlots)

local Rig = {}
Rig.__index = Rig

-- ---------------------------------------------------------------- device class (cached)
local deviceName: string? = nil
function Rig.device(): string
    if deviceName then return deviceName end
    local camera = workspace.CurrentCamera
    local size = if camera then camera.ViewportSize else Vector2.new(1920, 1080)
    deviceName = Recipes.deviceClass(UserInputService.TouchEnabled, UserInputService.MouseEnabled, math.min(size.X, size.Y))
    return deviceName
end

-- ---------------------------------------------------------------- pool
local POOL_CAP = 64
local pool: {[string]: {Instance}} = {}
local function acquire(class: string): Instance
    local list = pool[class]
    if list and #list > 0 then return table.remove(list) end
    return Instance.new(class)
end
local function release(inst: Instance)
    local class = inst.ClassName
    if class == "Trail" then (inst :: Trail):Clear() end
    if class == "ParticleEmitter" then (inst :: ParticleEmitter).Enabled = false end
    if class == "Trail" or class == "Beam" then (inst :: any).Enabled = false end
    if class == "Attachment" or class == "ParticleEmitter" or class == "Beam" or class == "Trail" then
        local list = pool[class]
        if not list then list = {} pool[class] = list end
        if #list < POOL_CAP then
            inst.Parent = nil
            if class == "Attachment" then (inst :: Attachment).CFrame = CFrame.new() end
            table.insert(list, inst)
            return
        end
    end
    inst:Destroy()
end
Rig._acquire, Rig._release = acquire, release -- exposed for tests

-- ---------------------------------------------------------------- conversions
local function c3(c: {number}): Color3
    return Color3.fromRGB(math.clamp(math.floor(c[1] + 0.5), 0, 255), math.clamp(math.floor(c[2] + 0.5), 0, 255), math.clamp(math.floor(c[3] + 0.5), 0, 255))
end
local function colorSeq(colors: {{number}}): ColorSequence
    if type(colors) ~= "table" or #colors == 0 then return ColorSequence.new(Color3.fromRGB(255, 255, 255)) end -- never throw on a recipe without colours
    if #colors == 1 then return ColorSequence.new(c3(colors[1])) end
    local keys = {}
    for i, c in colors do keys[i] = ColorSequenceKeypoint.new((i - 1) / (#colors - 1), c3(c)) end
    return ColorSequence.new(keys)
end
local function fadeSeq(alpha: number): NumberSequence -- soft in, long soft out (Recipes.Curves.fadeInOut spirit)
    local peak = 1 - alpha
    return NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.2, peak),
        NumberSequenceKeypoint.new(0.6, peak + (1 - peak) * 0.4), NumberSequenceKeypoint.new(1, 1)})
end
local function sizeSeq(layer, scale: number): NumberSequence
    local s = layer.size * scale
    if layer.grow then
        return NumberSequence.new({NumberSequenceKeypoint.new(0, s * 0.3), NumberSequenceKeypoint.new(1, s * layer.grow)})
    elseif layer.curve == "sizePop" then
        return NumberSequence.new({NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(0.2, s), NumberSequenceKeypoint.new(1, 0)})
    end
    return NumberSequence.new({NumberSequenceKeypoint.new(0, s * 0.4), NumberSequenceKeypoint.new(0.35, s), NumberSequenceKeypoint.new(1, s * 1.25)})
end
local function orient(position: Vector3, angle: number): CFrame -- attachment X axis = orbit tangent (beam curves follow it)
    local tangent = Vector3.new(-math.sin(angle), 0, math.cos(angle))
    return CFrame.fromMatrix(position, tangent, Vector3.yAxis, tangent:Cross(Vector3.yAxis))
end

-- ---------------------------------------------------------------- shared ribbon + optional shell (BD-432)
-- ONE soft ribbon texture serves every trail ribbon and orbit beam. While the slot is empty (docs/77 fx_ribbonSoft) the plain
-- coloured ribbon is used: nothing is drawn in code.
local function ribbonTexture(): string
    return if Assets.isReal("ribbonSoft") then Assets.resolve("ribbonSoft") else ""
end
-- The aura shell is a slightly inflated Blender mesh (slot aura_shell_mesh). It exists only when that slot holds a real upload,
-- on Epic+ auras at the full look, never with Reduce Motion. Empty slot = no shell, no fallback shape.
local SHELL_MIN_TIER = 4
local function wantsShell(kind: string, resolved, opts): boolean
    return kind == "aura" and not resolved.reduced and opts.detail ~= "lite" and (resolved.tier or 0) >= SHELL_MIN_TIER and Slots.mesh("aura_shell_mesh") ~= nil
end
-- Cost of a look as the global budget sees it (FxRecipes cost plus shells), without building anything.
function Rig.cost(kind: string, item, opts)
    opts = opts or {}
    local resolved = Recipes.resolve(kind, item, {device = opts.device or Rig.device(), reduce = opts.reduce, detail = opts.detail})
    local out = {}
    for k, v in resolved.cost do out[k] = v end
    out.shells = if wantsShell(kind, resolved, opts) then 1 else 0
    return out
end

-- ---------------------------------------------------------------- build
local FEET = -1.7 -- anchor height below the root part (studs at scale 1)

function Rig.attach(root: BasePart, kind: string, item, opts)
    opts = opts or {}
    local device = opts.device or Rig.device()
    local resolved = Recipes.resolve(kind, item, {device = device, reduce = opts.reduce, detail = opts.detail})
    local self = setmetatable({root = root, resolved = resolved, scale = 1, lastScale = -1, age = 0, wasMoving = false, lastPop = -10,
        objects = {}, emitters = {}, moving = {}, orbits = {}, trails = {}, beams = {}, lights = {}, bursts = {}, pillars = {}, alive = true}, Rig)

    local function own(inst: Instance) table.insert(self.objects, inst) return inst end
    local function needsAnchor(): boolean
        return resolved.cost.parts > 0
    end
    local anchor: Part? = nil
    if needsAnchor() then
        local part = Instance.new("Part")
        part.Name = "FxAnchor_" .. kind
        part.Size = Vector3.new(2.6, 0.2, 2.6)
        part.Transparency, part.Anchored, part.CanCollide, part.CanTouch, part.CanQuery, part.CastShadow = 1, true, false, false, false, false
        part.CFrame = CFrame.new(root.Position + Vector3.new(0, FEET, 0))
        local folder = workspace:FindFirstChild("LocalDinoFX")
        if not folder then folder = Instance.new("Folder") folder.Name = "LocalDinoFX" folder.Parent = workspace end
        part.Parent = folder
        anchor = part
        self.anchor = part
    end
    local function attachment(parent: Instance, name: string): Attachment
        local a = acquire("Attachment") :: Attachment
        a.Name, a.Parent = name, parent
        own(a)
        return a
    end

    for _, layer in resolved.layers do
        local k = layer.kind
        if k == "glow" then
            local a = attachment(root, "FxGlow")
            local light = Instance.new("PointLight")
            light.Color, light.Range, light.Shadows, light.Brightness, light.Parent = c3(layer.color[1]), layer.range, false, 0, a
            own(light)
            table.insert(self.lights, {light = light, layer = layer})
        elseif k == "emitter" or k == "burst" then
            local parent: Instance
            local emitsMoving = layer.onlyMoving == true
            if emitsMoving then
                parent = attachment(root, "FxTail")
                parent.Position = Vector3.new(0, -0.9, 1.4)
            elseif layer.flat then
                parent = attachment(root, "FxFeet") -- swirl lies flat, centred under the dino
                parent.Position = Vector3.new(0, FEET + 0.15, 0)
            elseif layer.shape and anchor then
                parent = anchor
            else
                parent = attachment(root, "FxBody")
                parent.Position = Vector3.new(0, -1, 0)
            end
            local e = acquire("ParticleEmitter") :: ParticleEmitter
            e.Name = "Fx_" .. layer.id
            e.Texture = Assets.resolve(layer.tex)
            e.Color = colorSeq(layer.color)
            e.Transparency = fadeSeq(layer.alpha)
            e.Size = sizeSeq(layer, 1)
            e.Lifetime = NumberRange.new(layer.life * 0.8, layer.life)
            e.Speed = NumberRange.new(layer.speed * 0.5, layer.speed)
            e.LightEmission = if Assets.isAdditive(layer.tex) then 1 else (layer.light or 0.5)
            e.Rotation = NumberRange.new(-180, 180)
            e.RotSpeed = if layer.spin then NumberRange.new(-layer.spin, layer.spin) else NumberRange.new(0, 0)
            e.LockedToPart = false
            e.Squash = NumberSequence.new(0)
            e.Drag = 0
            e.Shape, e.ShapeInOut, e.ShapeStyle = Enum.ParticleEmitterShape.Box, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Volume
            -- FX v3 sheets: OneShot plays the 16 cells in order over each particle's life (smoke, sparkle), Random picks one
            -- shape (flame), Loop cycles (swirl). Single images and built-in sprites have no flipbook.
            local sheet = Assets.isSheet(layer.tex)
            e.FlipbookLayout = if sheet then Enum.ParticleFlipbookLayout.Grid4x4 else Enum.ParticleFlipbookLayout.None
            if sheet then
                e.FlipbookMode = (Enum.ParticleFlipbookMode :: any)[Assets.mode(layer.tex)]
                e.FlipbookFramerate = NumberRange.new(Assets.LoopFps)
                e.FlipbookStartRandom = Assets.mode(layer.tex) ~= "OneShot"
            end
            e.Orientation = if layer.flat then Enum.ParticleOrientation.VelocityPerpendicular else Enum.ParticleOrientation.FacingCamera
            if k == "burst" then
                e.Rate = 0
                e.SpreadAngle = Vector2.new(180, 180)
                e.Acceleration = Vector3.new(0, 0.5, 0)
                e.EmissionDirection = Enum.NormalId.Top
                e.Enabled = false
            else
                e.Rate = layer.rate
                e.Acceleration = Vector3.new(0, layer.rise or 0, 0)
                e.EmissionDirection = Enum.NormalId.Top
                e.SpreadAngle = Vector2.new(30, 30)
                if layer.shape == "Disc" then
                    e.Shape, e.ShapeInOut, e.ShapeStyle = Enum.ParticleEmitterShape.Disc, Enum.ParticleEmitterShapeInOut.Outward, Enum.ParticleEmitterShapeStyle.Surface
                    e.SpreadAngle = Vector2.new(0, 0)
                    e.Acceleration = Vector3.zero
                elseif layer.shape == "Cylinder" then
                    e.SpreadAngle = Vector2.new(35, 35)
                end
                if layer.flat then
                    e.Shape, e.SpreadAngle, e.Acceleration = Enum.ParticleEmitterShape.Box, Vector2.zero, Vector3.zero
                end
                e.Enabled = false
            end
            e.Parent = parent
            own(e)
            local entry = {emitter = e, layer = layer, moving = emitsMoving}
            if k == "burst" then table.insert(self.bursts, entry) else
                table.insert(self.emitters, entry)
            end
        elseif k == "pillar" and anchor and not Assets.isAdditive(layer.tex) then
            -- (skipped while the rays upload is opaque on black: a BillboardGui cannot blend additively, docs EffectAssets.HasAlpha)
            -- Rays pillar (FX v3, Epic+): one camera-facing image standing on the feet, pushed slightly behind the dino, pulsing slowly.
            local board = Instance.new("BillboardGui")
            board.Name = "Fx_" .. layer.id
            board.LightInfluence, board.AlwaysOnTop, board.ResetOnSpawn, board.MaxDistance = 0, false, false, 220
            local img = Instance.new("ImageLabel")
            img.BackgroundTransparency, img.Size, img.Image, img.ImageTransparency = 1, UDim2.fromScale(1, 1), Assets.resolve(layer.tex), 1
            img.ImageColor3 = c3(layer.color[#layer.color])
            img.Parent = board
            board.Adornee, board.Parent = anchor, anchor
            own(board)
            table.insert(self.pillars, {board = board, img = img, layer = layer})
        elseif k == "ring" or k == "spiral" then
            local n = layer.beams
            local points = {}
            local stepAngle = 2 * math.pi / n
            for i = 1, n do
                local a0 = attachment(anchor, "FxOrbit")
                local a1 = if k == "spiral" then attachment(anchor, "FxOrbitHigh") else nil
                points[i] = {a0, a1}
            end
            for i = 1, n do
                local beam = acquire("Beam") :: Beam
                beam.Name = "Fx_" .. layer.id
                beam.Texture = ribbonTexture()
                beam.Color = colorSeq(layer.color)
                beam.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.92), NumberSequenceKeypoint.new(0.2, 1 - layer.alpha),
                    NumberSequenceKeypoint.new(0.8, 1 - layer.alpha), NumberSequenceKeypoint.new(1, 0.92)})
                beam.LightEmission, beam.FaceCamera, beam.Segments, beam.Enabled = 0.9, true, 10, true
                if k == "ring" then
                    beam.Attachment0, beam.Attachment1 = points[i][1], points[i % n + 1][1]
                else
                    beam.Attachment0, beam.Attachment1 = points[i][1], points[i][2]
                end
                beam.Parent = anchor
                own(beam)
                table.insert(self.beams, {beam = beam, layer = layer, k = k})
            end
            table.insert(self.orbits, {points = points, layer = layer, n = n, step = stepAngle, k = k})
        elseif k == "trail" then
            local count = layer.count or 1
            for i = 1, count do
                local side = if count == 1 then 0 else (if i == 1 then -1 else 1)
                local a, b = attachment(root, "FxTrailA"), attachment(root, "FxTrailB")
                local ribbon = acquire("Trail") :: Trail
                ribbon.Name = "Fx_" .. layer.id
                ribbon.Attachment0, ribbon.Attachment1 = a, b
                ribbon.Color = colorSeq(layer.color)
                ribbon.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 1 - layer.alpha), NumberSequenceKeypoint.new(0.5, 1 - layer.alpha * 0.5), NumberSequenceKeypoint.new(1, 1)})
                ribbon.WidthScale = NumberSequence.new({NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, 0)})
                ribbon.Lifetime, ribbon.MinLength, ribbon.FaceCamera, ribbon.LightEmission = layer.life, 0.12, true, layer.light or 0.8
                ribbon.Texture = ribbonTexture()
                ribbon.Enabled = false
                ribbon.Parent = root
                own(ribbon)
                table.insert(self.trails, {ribbon = ribbon, a = a, b = b, side = side, layer = layer, lines = layer.id == "lines"})
            end
        end
    end
    if wantsShell(kind, resolved, opts) then
        local mesh = Slots.mesh("aura_shell_mesh")
        local shell = Instance.new("Part")
        shell.Name = "FxShell"
        shell.Size = Vector3.new(4, 4, 4)
        shell.Transparency, shell.Anchored, shell.CanCollide, shell.CanTouch, shell.CanQuery, shell.CastShadow = 0.88, true, false, false, false, false
        shell.Material, shell.Color = Enum.Material.Neon, c3(resolved.layers[1].color[#resolved.layers[1].color])
        local special = Instance.new("SpecialMesh")
        special.MeshType, special.MeshId, special.Scale = Enum.MeshType.FileMesh, mesh, Vector3.new(1, 1, 1)
        special.Parent = shell
        local folder = workspace:FindFirstChild("LocalDinoFX")
        if not folder then folder = Instance.new("Folder") folder.Name = "LocalDinoFX" folder.Parent = workspace end
        shell.Parent = folder
        self.shell = shell
    end
    self._anchorPart = anchor
    self.fade = 0
    if not opts.reduce then self:burst() end -- equip pop (aura / mutation); trails pop when they start moving
    return self
end

-- ---------------------------------------------------------------- runtime
function Rig:burst()
    if not self.alive or self.resolved.reduced then return end
    for _, entry in self.bursts do
        if entry.emitter.Parent then entry.emitter:Emit(entry.layer.count) end
    end
end

function Rig:update(scale: number, time: number, moving: boolean)
    if not self.alive then return end
    local root = self.root
    if not root.Parent then self:destroy() return end
    local reduced = self.resolved.reduced
    self.age += 1 / 30
    local fade = if reduced then 1 else Recipes.easeOutCubic(self.age / Recipes.Timing.fadeIn)
    local anchor = self._anchorPart
    local rebuild = math.abs(scale - self.lastScale) > 0.05 * math.max(self.lastScale, 0.05)
    if anchor then
        anchor.CFrame = CFrame.new(root.Position + Vector3.new(0, FEET * scale, 0))
        if rebuild then anchor.Size = Vector3.new(2.6 * scale, 0.2, 2.6 * scale) end
    end
    local pulse = if reduced then 0.5 else Recipes.pulse(time)
    if self.shell then -- slow breathing, always soft and see-through (calm rule)
        self.shell.CFrame = root.CFrame
        local size = (4.2 + 0.25 * pulse) * scale
        self.shell.Size = Vector3.new(size, size, size)
        self.shell.Transparency = 1 - 0.14 * fade
    end
    for _, entry in self.lights do
        entry.light.Brightness = entry.layer.brightness * (0.75 + 0.25 * pulse) * fade
        if rebuild then entry.light.Range = entry.layer.range * scale end
    end
    for _, entry in self.pillars do
        local layer = entry.layer
        if rebuild then
            entry.board.Size = UDim2.fromScale(layer.width * scale, layer.height * scale)
            -- bottom on the feet; StudsOffset is camera-relative, so -Z keeps it BEHIND the dino from any view angle
            entry.board.StudsOffset = Vector3.new(0, layer.height * scale * 0.5, -1.6 * scale)
        end
        local glow = if reduced then 0.5 else Recipes.pulse(time, layer.hz)
        entry.img.ImageTransparency = 1 - layer.alpha * (0.55 + 0.45 * glow) * fade
    end
    for _, entry in self.emitters do
        local e = entry.emitter
        local on = (not entry.moving) or moving
        e.Enabled = on
        if on and fade < 1 then e.Rate = entry.layer.rate * fade elseif on and e.Rate ~= entry.layer.rate then e.Rate = entry.layer.rate end
        if rebuild then e.Size = sizeSeq(entry.layer, scale) end
        if on and entry.layer.shape == "Disc" and anchor then
            e.Speed = NumberRange.new(entry.layer.speed * 0.5 * scale, entry.layer.speed * scale)
        end
    end
    -- orbits: rings turn slowly (docs/93 timing), spirals rise and sweep
    for _, orbit in self.orbits do
        local layer = orbit.layer
        local base = time * layer.spin
        local r = layer.radius * scale
        local k = (4 / 3) * math.tan(orbit.step / 4) * r
        for i, pair in orbit.points do
            local angle = base + (i - 1) * orbit.step
            if orbit.k == "ring" then
                local y = (layer.height - FEET) * scale
                pair[1].CFrame = orient(Vector3.new(math.cos(angle) * r, y, math.sin(angle) * r), angle)
            else
                local lowAngle = base + (i - 1) * orbit.step
                local highAngle = lowAngle + 2.0
                pair[1].CFrame = orient(Vector3.new(math.cos(lowAngle) * r, (layer.low - FEET) * scale, math.sin(lowAngle) * r), lowAngle)
                pair[2].CFrame = orient(Vector3.new(math.cos(highAngle) * r * 0.8, (layer.high - FEET) * scale, math.sin(highAngle) * r * 0.8), highAngle)
            end
        end
        for _, b in self.beams do
            if b.layer == layer then
                local width = layer.width * scale
                b.beam.Width0, b.beam.Width1 = width, if orbit.k == "spiral" then width * 0.15 else width
                local curve = if orbit.k == "ring" then k else r * 0.6
                b.beam.CurveSize0, b.beam.CurveSize1 = curve, if orbit.k == "ring" then curve else -curve * 0.8
            end
        end
    end
    -- trails: only while moving; pop sparkles when starting to run
    for _, entry in self.trails do
        local layer = entry.layer
        local x = if entry.lines then entry.side * (layer.offset or 0.9) * scale else 0
        entry.a.Position = Vector3.new(x, -0.55 * scale, 1.3 * scale)
        local height = layer.width * scale
        entry.b.Position = entry.a.Position + Vector3.new(0, -math.max(height, 0.08), 0)
        if not moving and entry.ribbon.Enabled then entry.ribbon:Clear() end
        entry.ribbon.Enabled = moving
    end
    if moving and not self.wasMoving and time - self.lastPop > 1.5 then
        self.lastPop = time
        self:burst()
    end
    self.wasMoving = moving
    self.scale, self.lastScale = scale, scale
end

function Rig:destroy()
    if not self.alive then return end
    self.alive = false
    for _, inst in self.objects do release(inst) end
    self.objects = {}
    if self._anchorPart then self._anchorPart:Destroy() end
    if self.shell then self.shell:Destroy() self.shell = nil end
end

return Rig
