--!strict
-- BD-234/BD-233 spike: procedural idle/walk + jump/leap/land/water-surge for the low-poly dinos (Config.LowPolyDinos). Pose math: Shared/LowPolyPose (pure).
-- Writes Weld.C1 (the animation offset) so DinoMotion's C0 poses (eat, jump squash/stretch, landing) keep working on top.
-- Jump/leap state is derived client-side (humanoid state/velocity, LeapPredictAt/LeapUntil attributes); the server rules are untouched.
-- Respects Reduce Motion (Theme.MotionEnabled). Remote dinos are animated at 20 Hz within 80 studs only.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Pose = require(Shared.LowPolyPose)
local LowPoly = require(Shared.LowPolyDinos)
local Theme = require(Shared.UITheme)
local EffectAssets = require(Shared.EffectAssets)
local NpcLowPoly = require(Shared.NpcLowPoly)
if not LowPoly.enabled() then return end

local RANGE, REMOTE_STEP, RUN_SPEED = 80, 1 / 20, 24
local rigs: {[Model]: any} = {}
local out, actOut, ctx = Pose.new(), Pose.new(), Pose.newCtx()

-- Small splash puff for the Water surge: the existing smoke sheet (alpha), 3 pooled emitters, none under Reduce Motion.
local splash: {ParticleEmitter} = {}
local splashAt: {Attachment} = {}
local nextSplash = 0
local function splashPuff(position: Vector3, count: number, scale: number)
    if #splash == 0 then
        local sheet = EffectAssets.isSheet("smokeSheet") and not EffectAssets.isAdditive("smokeSheet")
        for i = 1, 3 do
            local at = Instance.new("Attachment")
            at.Name = "LowPolySplash"
            at.Parent = workspace.Terrain
            local e = Instance.new("ParticleEmitter")
            e.Enabled = false
            e.Rate = 0
            e.Texture = if sheet then EffectAssets.resolve("smokeSheet") else EffectAssets.Builtin.smoke
            e.FlipbookLayout = if sheet then Enum.ParticleFlipbookLayout.Grid4x4 else Enum.ParticleFlipbookLayout.None
            if sheet then e.FlipbookMode = Enum.ParticleFlipbookMode.OneShot end
            e.Lifetime = NumberRange.new(0.4, 0.7)
            e.Speed = NumberRange.new(3, 6)
            e.SpreadAngle = Vector2.new(60, 60)
            e.EmissionDirection = Enum.NormalId.Top
            e.Color = ColorSequence.new(Color3.fromRGB(205, 235, 255))
            e.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.35), NumberSequenceKeypoint.new(1, 1)})
            e.Parent = at
            table.insert(splash, e)
            table.insert(splashAt, at)
        end
    end
    nextSplash = nextSplash % 3 + 1
    local e = splash[nextSplash]
    e.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 0.5 * scale), NumberSequenceKeypoint.new(1, 1.4 * scale)})
    splashAt[nextSplash].WorldPosition = position
    e:Emit(count)
end

local function num(instance: Instance, name: string): number
    local v = instance:GetAttribute(name)
    return if typeof(v) == "number" then v else 0
end

local function startPhase(rig: any, phase: string, now: number)
    rig.act, rig.actAt = phase, now
end

-- Derives the action state from humanoid state/velocity and the leap attributes. Returns nothing; writes rig.act/rig.aggr.
local function updateAction(rig: any, now: number)
    local character, root = rig.character, rig.root
    if not character or not root then rig.act = nil return end -- local character not spawned yet or already gone
    -- BD-249: the run ended in a defeat (DinoMotion also plays its own "death" flop on RunState Ending, on C0, so the two stack).
    if character:GetAttribute("RunState") == "Ending" then
        if rig.act ~= "defeat" then rig.aggr = 0 startPhase(rig, "defeat", now) end
        return
    elseif rig.act == "defeat" then rig.act = nil end
    local hum = rig.humanoid
    if not hum or not hum.Parent then hum = character:FindFirstChildOfClass("Humanoid") rig.humanoid = hum end
    if not hum or hum.Health <= 0 then rig.act = nil return end
    -- leap signal: the local prediction stamp, or the server's LeapUntil changing (replicated to remote players)
    local predict, untilAt = num(character, "LeapPredictAt"), num(character, "LeapUntil")
    if (predict ~= rig.lastPredict and predict > 0) or (untilAt ~= rig.lastUntil and untilAt > 0) then rig.leapAt = now end
    rig.lastPredict, rig.lastUntil = predict, untilAt
    local state = hum:GetState()
    local jumpKey = hum.Jump or state == Enum.HumanoidStateType.Jumping
    local jumpEdge = jumpKey and not rig.jumpHeld
    rig.jumpHeld = jumpKey
    local leaping = now - rig.leapAt < 0.7
    if rig.class == "Water" then -- no air time: the jump / leap button is a forward surge
        if rig.act == "surge" and now - rig.actAt >= Pose.duration("surge", rig.aggr, "Water") then rig.act = nil end
        if rig.act == nil and (jumpEdge or (leaping and rig.leapAt ~= rig.surgeLeap)) then
            rig.aggr = if leaping then 1 else 0
            rig.surgeLeap = rig.leapAt
            startPhase(rig, "surge", now)
            if rig.amp > 0 then
                local scale = (if leaping then 1.6 else 1) * math.clamp(rig.height / 4, 0.6, 2)
                splashPuff(root.Position - Vector3.new(0, rig.height * 0.3, 0), if leaping then 9 else 5, scale)
            end
        end
        return
    end
    local airborne = state == Enum.HumanoidStateType.Jumping or state == Enum.HumanoidStateType.Freefall
        or (hum.FloorMaterial == Enum.Material.Air and math.abs(root.AssemblyLinearVelocity.Y) > 3)
    local ph = rig.act
    if airborne then
        if ph == nil or ph == "land" then
            rig.aggr = if leaping then 1 else 0
            if state == Enum.HumanoidStateType.Freefall and not jumpKey and not leaping then startPhase(rig, "air", now) -- stepped off a ledge: no crouch
            else startPhase(rig, "crouch", now) end
        elseif ph ~= "air" and now - rig.actAt >= Pose.duration(ph, rig.aggr, rig.class) then
            startPhase(rig, if ph == "crouch" then "push" else "air", now)
        end
        if leaping then rig.aggr = 1 end
    elseif ph ~= nil and ph ~= "land" then
        rig.carry = if ph == "air" then math.clamp((now - rig.actAt) / Pose.TuckTime, 0, 1) else 0
        startPhase(rig, "land", now)
    elseif ph == "land" and now - rig.actAt >= Pose.duration("land", rig.aggr, rig.class) then
        rig.act = nil
    end
end

-- BD-324: wild NPC predators (server-made models flagged NpcLowPoly, visual child "NpcVisual") use the SAME pose functions. Their action
-- comes from the replicated NpcCue ("windup") and BiteSeq attributes, not from a Humanoid: windup lean, bite lunge.
local function updateNpcAction(rig: any, model: Model, now: number)
    local seq = num(model, "BiteSeq")
    local biteChanged = rig.biteSeq ~= nil and seq ~= rig.biteSeq
    rig.biteSeq = seq
    local cue = tostring(model:GetAttribute("NpcCue") or "")
    if rig.act == "bite" and now - rig.actAt >= Pose.duration("bite", 0, rig.class) then rig.act = nil end
    if rig.act == "windup" and cue ~= "windup" then rig.act = nil end
    local want = NpcLowPoly.phase(cue, biteChanged, rig.act)
    if want and want ~= rig.act then rig.aggr = 0 startPhase(rig, want, now) end
end

local function pivotFor(role: string, size: Vector3, side: number): Vector3
    if role == "wing" or role == "flipper" then return Vector3.new(-side * size.X / 2, 0, 0) end -- inner edge, at the body
    if role == "head" then return Vector3.new(0, -size.Y / 2, size.Z / 2) end -- neck, bottom back
    if role == "tail" then return Vector3.new(0, 0, -size.Z / 2) end -- tail root: the front (-Z) end meets the body
    if role == "arm" or role == "leg" then return Vector3.new(0, size.Y / 2, 0) end -- hip/shoulder
    if role == "neck" then return Vector3.new(0, -size.Y / 2, size.Z / 2) end -- neck base, like the head
    return Vector3.zero
end

local function collect(visual: Model): {any}
    local list = {}
    for _, part in visual:GetDescendants() do
        local weld = if part:IsA("MeshPart") then part:FindFirstChild("ResourceWeld") else nil
        if weld and weld:IsA("Weld") then
            table.insert(list, {part = part, weld = weld, role = part:GetAttribute("LPRole") or "body",
                side = part:GetAttribute("LPSide") or 1, lead = part:GetAttribute("LPLead") == true})
        end
    end
    return list
end

local function apply(rig: any, now: number, dt: number, amp: number, npc: Model?)
    local root = rig.root
    local v = root.AssemblyLinearVelocity
    local speed01 = math.clamp(math.sqrt(v.X * v.X + v.Z * v.Z) / RUN_SPEED, 0, 1)
    if speed01 < 0.06 then speed01 = 0 end
    rig.speed = rig.speed + (speed01 - rig.speed) * math.min(1, dt * 8) -- ease in/out
    rig.phase = (rig.phase + dt * Pose.stepRate(rig.speed) * (if rig.speed > 0.01 then 1 else 0)) % (2 * math.pi * 8)
    local height = rig.height
    rig.amp = amp
    if amp == 0 then rig.act = nil elseif npc then updateNpcAction(rig, npc, now) else updateAction(rig, now) end
    local phase = rig.act
    local k = 0
    if phase then
        local elapsed = now - rig.actAt
        local dur = Pose.duration(phase, rig.aggr, rig.class)
        ctx.phase, ctx.t, ctx.aggr, ctx.carry = phase, elapsed, rig.aggr, rig.carry
        ctx.p = if dur > 0 then math.clamp(elapsed / dur, 0, 1) else 0
        k = Pose.actionWeight(phase, ctx.p)
    end
    local bob = Pose.bob(now + rig.seed, rig.phase, rig.speed, amp, rig.class) * height -- BD-388: one shared translation for every part
    for _, item in rig.parts do
        local part = item.part :: MeshPart
        if not part.Parent then continue end
        Pose.sample(item.role, item.side, item.lead, now + rig.seed, rig.phase, rig.speed, amp, out, rig.class)
        if phase == "defeat" then Pose.blend(out, Pose.sampleDefeat(item.role, item.side, item.lead, ctx, amp, actOut, rig.class, rig.skin), k)
        elseif phase then Pose.blend(out, Pose.sampleAction(item.role, item.side, item.lead, ctx, amp, actOut, rig.class), k) end
        if amp == 0 and item.role ~= "wing" then
            item.weld.C1 = CFrame.identity
        else
            local pivot = pivotFor(item.role, part.Size, item.side)
            -- Joint pivot rotation (the anchor never moves, no stretch) + shared whole-body bob + head peck forward in studs (-Z), both
            -- expressed in the part's own frame through the weld's rest rotation.
            local shift = item.weld.C0.Rotation:Inverse() * Vector3.new(0, bob, -out.fwd)
            local anim = CFrame.new(shift) * CFrame.new(pivot) * CFrame.Angles(out.pitch, out.yaw, out.roll) * CFrame.new(-pivot)
                * CFrame.new(0, out.dy * height, out.dz * height)
            item.weld.C1 = anim:Inverse()
        end
    end
end

local function untrack(character: Model)
    local rig = rigs[character]
    if not rig then return end
    for _, item in rig.parts do if item.weld.Parent then item.weld.C1 = CFrame.identity end end
    rigs[character] = nil
end

RunService.Heartbeat:Connect(function(dt)
    local camera = workspace.CurrentCamera
    local now = os.clock()
    local amp = if Theme.MotionEnabled then 1 else 0
    for _, player in Players:GetPlayers() do
        local character = player.Character
        local visual = if character then character:FindFirstChild("LocalMeshVisual") else nil
        local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
        if not character or not visual or not root or not root:IsA("BasePart") or visual:GetAttribute("LowPoly") ~= true then
            if character then rigs[character] = nil end
            continue
        end
        local rig = rigs[character]
        if not rig or rig.visual ~= visual then
            local _, size = visual:GetBoundingBox()
            rig = {visual = visual, root = root, parts = collect(visual), phase = 0, speed = 0, acc = 0,
                height = math.max(size.Y, 1), aggr = 0, carry = 0, leapAt = -10, lastPredict = 0, lastUntil = 0, jumpHeld = false, surgeLeap = -1, amp = 1, class = visual:GetAttribute("LPClass"), skin = Pose.skinOf(visual:GetAttribute("LPSkin")), seed = math.random() * 10}
            rigs[character] = rig
        end
        if player == Players.LocalPlayer then
            apply(rig, now, dt, amp)
        elseif camera and (camera.CFrame.Position - root.Position).Magnitude <= RANGE then
            rig.acc += dt
            if rig.acc >= REMOTE_STEP then apply(rig, now, rig.acc, amp) rig.acc = 0 end
        end
    end
end)
-- Wild NPC rigs, 20 Hz within RANGE (like remote players). Nothing runs while the folder is absent (CombatEnabled false).
local npcRigs: {[Model]: any} = setmetatable({}, {__mode = "k"}) :: any
RunService.Heartbeat:Connect(function(dt)
    local folder = workspace:FindFirstChild("BeDinoNpcs")
    if not folder then return end
    local camera = workspace.CurrentCamera
    local now = os.clock()
    local amp = if Theme.MotionEnabled then 1 else 0
    for _, model in folder:GetChildren() do
        local visual = if model:IsA("Model") and model:GetAttribute("NpcLowPoly") == true then model:FindFirstChild("NpcVisual") else nil
        local root = model:FindFirstChild("HumanoidRootPart")
        if not visual or not visual:IsA("Model") or not root or not root:IsA("BasePart") or model:GetAttribute("NpcFading") == true then continue end
        local rig = npcRigs[model]
        if not rig or rig.visual ~= visual then
            local _, size = visual:GetBoundingBox()
            rig = {visual = visual, root = root, parts = collect(visual), phase = 0, speed = 0, acc = 0, height = math.max(size.Y, 1), aggr = 0, carry = 0,
                leapAt = -10, lastPredict = 0, lastUntil = 0, jumpHeld = false, surgeLeap = -1, amp = 1, class = visual:GetAttribute("LPClass"), skin = Pose.skinOf(visual:GetAttribute("LPSkin")), seed = math.random() * 10}
            npcRigs[model] = rig
        end
        if camera and (camera.CFrame.Position - root.Position).Magnitude <= RANGE then
            rig.acc += dt
            if rig.acc >= REMOTE_STEP then apply(rig, now, rig.acc, amp, model) rig.acc = 0 end
        end
    end
end)
Players.PlayerRemoving:Connect(function(player) if player.Character then untrack(player.Character) end end)
