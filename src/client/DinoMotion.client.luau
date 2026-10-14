--!strict
-- BD-079: client-only procedural action motion for the visible dino model (eat, jump, leap, turn,
-- bite, death). Visual only: the physics root and server authority are never touched. One shared
-- Heartbeat; zero work for characters at rest; pooled particles. Curves: src/shared/DinoMotion.luau.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Motion = require(Shared.DinoMotion)
local Theme = require(Shared.UITheme)
local Sfx = require(Shared.Sfx)

local OTHER_RANGE = 120
local OTHER_STEP = 1 / 20
local EAT_DELAY = 0.1 -- lets growth rescale the model first (ResourceVisuals refreshes deferred)

local rigs: {[Model]: any} = {}

-- Pooled particle puffs: 3 dust + 3 munch emitters, created lazily, never more.
local pool: {ParticleEmitter} = {}
local poolAttachments: {Attachment} = {}
local nextDust, nextMunch = 0, 0
local function ensurePool()
    if #pool > 0 then return end
    for i = 1, 6 do
        local attachment = Instance.new("Attachment")
        attachment.Name = "DinoMotionFx"
        attachment.Parent = workspace.Terrain
        local emitter = Instance.new("ParticleEmitter")
        emitter.Enabled = false
        emitter.Rate = 0
        emitter.Lifetime = NumberRange.new(0.25, 0.45)
        emitter.Speed = NumberRange.new(3, 6)
        emitter.SpreadAngle = Vector2.new(180, 180)
        emitter.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.5), NumberSequenceKeypoint.new(1, 0)})
        emitter.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.2), NumberSequenceKeypoint.new(1, 1)})
        emitter.Color = ColorSequence.new(if i <= 3 then Color3.fromRGB(190, 170, 130) else Color3.fromRGB(150, 220, 110))
        emitter.Parent = attachment
        table.insert(pool, emitter)
        table.insert(poolAttachments, attachment)
    end
end
local function puff(kind: string, position: Vector3, count: number)
    ensurePool()
    local index
    if kind == "dust" then
        nextDust = nextDust % 3 + 1
        index = nextDust
    else
        nextMunch = nextMunch % 3 + 1
        index = 3 + nextMunch
    end
    poolAttachments[index].WorldPosition = position
    pool[index]:Emit(count)
end

local function number(instance: Instance, name: string): number
    local value = instance:GetAttribute(name)
    return if typeof(value) == "number" then value else 0
end

local function writePose(rig: any, pose: any)
    local rootCF = rig.root.CFrame
    local pivot = rig.pivot
    local rotation = CFrame.Angles(pose.pitch, 0, pose.roll)
    local offset = Vector3.new(0, pose.dy * rig.height, -pose.fx * rig.length)
    local sx, sy, sz = pose.sx, pose.sy, pose.sz
    local sx2, sy2, sz2 = sx * sx, sy * sy, sz * sz
    for i = 1, rig.count do
        local item = rig.parts[i]
        local part = item.part
        local relPos = item.rel.Position - pivot
        local position = pivot + offset + rotation:VectorToWorldSpace(Vector3.new(relPos.X * sx, relPos.Y * sy, relPos.Z * sz))
        local newRel = CFrame.new(position) * (rotation.Rotation * item.rel.Rotation)
        if item.weld then item.weld.C0 = newRel else part.CFrame = rootCF * newRel end
        part.Size = Vector3.new(
            item.size.X * math.sqrt(item.a11 * sx2 + item.a12 * sy2 + item.a13 * sz2),
            item.size.Y * math.sqrt(item.a21 * sx2 + item.a22 * sy2 + item.a23 * sz2),
            item.size.Z * math.sqrt(item.a31 * sx2 + item.a32 * sy2 + item.a33 * sz2))
        part.Transparency = item.transparency + (1 - item.transparency) * pose.fade
    end
end

-- Exact rest write: captured CFrames/sizes/transparency go back verbatim.
local function restore(rig: any)
    if not rig.applied then return end
    rig.applied = false
    if rig.visual and rig.visual.Parent then
        for i = 1, rig.count do
            local item = rig.parts[i]
            if item.part.Parent then
                if item.weld then item.weld.C0 = item.rel else item.part.CFrame = rig.root.CFrame * item.rel end
                item.part.Size = item.size
                item.part.Transparency = item.transparency
            end
        end
    end
    rig.count = 0
end

local function capture(rig: any): boolean
    local visual = rig.character:FindFirstChild("LocalMeshVisual") or rig.character:FindFirstChild("DinoVisual")
    if not visual or not visual:IsA("Model") then return false end
    rig.visual = visual
    local count = 0
    local inverse = rig.root.CFrame:Inverse()
    for _, item in visual:GetDescendants() do
        if item:IsA("BasePart") and not item.Anchored then
            count += 1
            local found = item:FindFirstChild("ResourceWeld")
            local weld = if found and found:IsA("Weld") and found.Part0 == rig.root then found else nil
            local rel = if weld then weld.C0 else inverse * item.CFrame
            local r = rel.Rotation
            local x, y, z = r.RightVector, r.UpVector, r.LookVector
            rig.parts[count] = {part = item, weld = weld, rel = rel, size = item.Size, transparency = item.Transparency,
                a11 = x.X * x.X, a12 = x.Y * x.Y, a13 = x.Z * x.Z,
                a21 = y.X * y.X, a22 = y.Y * y.Y, a23 = y.Z * y.Z,
                a31 = z.X * z.X, a32 = z.Y * z.Y, a33 = z.Z * z.Z}
        end
    end
    if count == 0 then return false end
    rig.count = count
    local cf, size = visual:GetBoundingBox()
    local center = inverse * cf
    rig.pivot = Vector3.new(center.X, center.Y - size.Y / 2, center.Z)
    rig.length, rig.height = math.max(size.Z, 1), math.max(size.Y, 1)
    return true
end

local function trigger(rig: any, kind: string, power: number?)
    if not Theme.MotionEnabled then return end
    Motion.trigger(rig.motion, kind, os.clock(), power)
end

local function untrack(character: Model)
    local rig = rigs[character]
    if not rig then return end
    for _, connection in rig.connections do connection:Disconnect() end
    rig.connections = {}
    restore(rig)
    rigs[character] = nil
end

local function track(player: Player, character: Model)
    untrack(character)
    local root = character:WaitForChild("HumanoidRootPart", 10)
    if not root or not root:IsA("BasePart") or not character.Parent then return end
    local humanoid = character:FindFirstChildOfClass("Humanoid")
    local rig: any = {character = character, root = root, isLocal = player == Players.LocalPlayer,
        motion = Motion.new(), pose = Motion.newPose(), parts = {}, count = 0, visual = nil, pivot = Vector3.zero,
        length = 1, height = 1, applied = false, accumulator = 0, lastYaw = nil, eatAt = nil,
        lastGrowth = number(character, "GrowthScore"), lastCatch = number(character, "CatchScore"),
        lastBite = number(character, "BiteSeq"), lastLeap = number(player, "LeapReadyAt"), connections = {}}
    rigs[character] = rig
    local function connect(signal: RBXScriptSignal, callback: (...any) -> ())
        table.insert(rig.connections, signal:Connect(callback))
    end
    local function watchScore(name: string, field: string)
        connect(character:GetAttributeChangedSignal(name), function()
            local value = number(character, name)
            if value > rig[field] and Theme.MotionEnabled and not rig.eatAt then rig.eatAt = os.clock() + EAT_DELAY end
            rig[field] = value
        end)
    end
    watchScore("GrowthScore", "lastGrowth")
    watchScore("CatchScore", "lastCatch")
    -- Any visual rebuild/rescale: put the model back BEFORE ResourceVisuals resizes it.
    for _, name in {"VisualScale", "SpeciesId", "MutationVisual", "GoldVisual", "GenesJson", "DinoAttached"} do
        connect(character:GetAttributeChangedSignal(name), function() restore(rig) end)
    end
    connect(character:GetAttributeChangedSignal("BiteSeq"), function()
        local value = number(character, "BiteSeq")
        if value ~= rig.lastBite then
            rig.lastBite = value
            trigger(rig, "bite")
        end
    end)
    connect(character:GetAttributeChangedSignal("RunState"), function()
        if character:GetAttribute("RunState") == "Ending" and Theme.MotionEnabled then
            restore(rig)
            trigger(rig, "death")
        end
    end)
    connect(player:GetAttributeChangedSignal("LeapReadyAt"), function()
        local value = number(player, "LeapReadyAt")
        if value > rig.lastLeap then
            rig.lastLeap = value
            trigger(rig, "leap")
        end
    end)
    if humanoid then
        connect(humanoid.StateChanged, function(old, new)
            if new == Enum.HumanoidStateType.Jumping then
                local leapStart = rig.motion.start.leap
                if not leapStart or os.clock() - leapStart > 0.35 then trigger(rig, "takeoff") end
            elseif old == Enum.HumanoidStateType.Freefall
                and (new == Enum.HumanoidStateType.Landed or new == Enum.HumanoidStateType.Running) then
                trigger(rig, "land")
                local camera = workspace.CurrentCamera
                if Theme.MotionEnabled and (rig.isLocal or (camera and (camera.CFrame.Position - root.Position).Magnitude < OTHER_RANGE / 2)) then
                    puff("dust", root.Position - Vector3.new(0, humanoid.HipHeight + root.Size.Y / 2, 0), 5)
                end
            end
        end)
    end
    connect(character.Destroying, function() untrack(character) end)
end

local function step(rig: any, now: number, dt: number)
    local character = rig.character
    local root = rig.root
    if not character.Parent or not root.Parent then
        untrack(character)
        return
    end
    local look = root.CFrame.LookVector
    local yaw = math.atan2(-look.X, -look.Z)
    local rate = 0
    if rig.lastYaw and dt > 0 then
        rate = ((yaw - rig.lastYaw + math.pi) % (2 * math.pi) - math.pi) / dt
    end
    rig.lastYaw = yaw
    local velocity = root.AssemblyLinearVelocity
    rig.motion.lean = Motion.lean(rig.motion.lean, rate, math.sqrt(velocity.X * velocity.X + velocity.Z * velocity.Z), dt)
    if rig.eatAt and now >= rig.eatAt then
        rig.eatAt = nil
        Motion.trigger(rig.motion, "eat", now)
        puff("munch", root.Position + look * (rig.length * 0.5), 3)
        if rig.isLocal then Sfx.play("pickup") end
    end
    if Motion.sample(rig.motion, now, rig.pose) then
        if not rig.applied then
            if not capture(rig) then return end
            rig.applied = true
        end
        writePose(rig, rig.pose)
    elseif rig.applied then
        restore(rig)
    end
end

RunService.Heartbeat:Connect(function(dt)
    if next(rigs) == nil then return end
    local enabled = Theme.MotionEnabled
    local camera = workspace.CurrentCamera
    local now = os.clock()
    for _, rig in rigs do
        if not enabled then
            if rig.applied then restore(rig) end
            Motion.clear(rig.motion)
            rig.eatAt = nil
        elseif rig.isLocal then
            step(rig, now, dt)
        elseif camera and (camera.CFrame.Position - rig.root.Position).Magnitude <= OTHER_RANGE then
            rig.accumulator += dt
            if rig.accumulator >= OTHER_STEP then
                local elapsed = rig.accumulator
                rig.accumulator = 0
                step(rig, now, elapsed)
            end
        elseif rig.applied then
            restore(rig)
            Motion.clear(rig.motion)
        end
    end
end)

local function watch(player: Player)
    player.CharacterAdded:Connect(function(character) track(player, character) end)
    if player.Character then task.spawn(track, player, player.Character) end
end
Players.PlayerAdded:Connect(watch)
for _, player in Players:GetPlayers() do watch(player) end
Players.PlayerRemoving:Connect(function(player)
    if player.Character then untrack(player.Character) end
end)
