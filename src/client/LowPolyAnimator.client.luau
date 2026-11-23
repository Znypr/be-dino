--!strict
-- BD-234/BD-233 spike: procedural idle/walk + jump/leap/land/water-surge for the low-poly dinos (Config.LowPolyDinos). Pose math: Shared/LowPolyPose (pure).
-- Writes Weld.C1 (the animation offset) so DinoMotion's C0 poses (eat, jump squash/stretch, landing) keep working on top.
-- Jump/leap state is derived client-side (humanoid state/velocity, LeapPredictAt/LeapUntil attributes); the server rules are untouched.
-- Respects Reduce Motion (Theme.MotionEnabled). Remote dinos are animated at 20 Hz within 80 studs only.
-- BD-1217: authored clips (Shared/LowPolyClips, keys from tools/blender/dino_clips.py) play ON TOP: eat when the dino eats (GrowthScore /
-- CatchScore up), happy when it grows (VisualScale up) or a new species is put on, a look-around after standing still a while.
-- BD-1217 rig follow-up (Config.DinoRigClipsEnabled): idle / walk / run come from AUTHORED loops (Shared/LowPolyGait) instead of the sine
-- poses, still clocked by the real speed (step phase) and blended by it; a "jump" clip plays at take-off and a "land" clip at touch-down on
-- top of the procedural tuck / squash; the tail and head follow through on a spring (turns, rise, fall, landing); and the local character's
-- default R15 Animate script is switched off while the dino is shown (the avatar is hidden; movement is the Humanoid's, not Animate's).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Pose = require(Shared.LowPolyPose)
local LowPoly = require(Shared.LowPolyDinos)
local Theme = require(Shared.UITheme)
local EffectAssets = require(Shared.EffectAssets)
local NpcLowPoly = require(Shared.NpcLowPoly)
local Clips = require(Shared.LowPolyClips)
local Gait = require(Shared.LowPolyGait)
local Config = require(Shared.Config)
if not LowPoly.enabled() then return end
local RIG = (Config :: any).DinoRigClipsEnabled == true -- BD-1217 rig follow-up (off = the procedural poses exactly as before)

local RANGE, REMOTE_STEP, RUN_SPEED = 80, 1 / 20, 24
local rigs: {[Model]: any} = {}
local out, actOut, ctx = Pose.new(), Pose.new(), Pose.newCtx()
local clipOut = Clips.new()
local LOOK_AFTER, LOOK_JITTER, CLIP_FADE = 8, 6, 0.25 -- s standing still before a look-around; fade when a clip is cut short

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
    local airborne = state == Enum.HumanoidStateType.Jumping or state == Enum.HumanoidStateType.Freefall
        or (hum.FloorMaterial == Enum.Material.Air and math.abs(root.AssemblyLinearVelocity.Y) > 3)
    rig.inAir = airborne
    if airborne then rig.airAt = now end -- BD-556: the hip-dip cover looks for a dip for a moment after the last airborne frame
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
    local ph = rig.act
    if airborne then
        -- BD-555: the humanoid reports Jumping only once the dino has left the ground, so a crouch and a push-off here would play AFTER take-off
        -- (legs fold, unfold, fold again inside 0.4 s). Every take-off and every ledge step-off goes straight into the air tuck instead, faded in
        -- from the current pose (Pose.airWeight); the leap crouch from the request is left out for the same reason (the leap is already moving).
        if ph == nil or ph == "land" then
            rig.aggr = if leaping then 1 else 0
            startPhase(rig, "air", now) -- take-off
        end
        if leaping then rig.aggr = 1 end
    elseif ph ~= nil and ph ~= "land" then
        rig.carry = if ph == "air" then 1 else 0
        rig.landFrom = if ph == "air" then Pose.airWeight(now - rig.actAt) else 1 -- a hop that lands before the tuck finished lands from that weight
        rig.flap = if ph == "air" and rig.class == "Fly" then Pose.airFlap(now - rig.actAt, rig.aggr) else 0 -- the landing flutter continues from here
        local dur = Pose.duration(ph, rig.aggr, rig.class)
        rig.wing = Pose.wingOpen(ph, if dur > 0 then math.clamp((now - rig.actAt) / dur, 0, 1) else 1) -- a hop that lands before the wings opened keeps them folded
        startPhase(rig, "land", now)
    elseif ph == "land" and now - rig.actAt >= Pose.duration("land", rig.aggr, rig.class) then
        rig.act = nil
    end
end

-- BD-1217: clip state. playClip restarts nothing that is already playing the same clip; stopClip fades out over CLIP_FADE.
local function playClip(rig: any, name: string, now: number)
    if rig.clip == name and not rig.clipFadeAt then return end
    rig.clip, rig.clipAt, rig.clipFadeAt = name, now, nil
end
local function stopClip(rig: any, now: number)
    if rig.clip and not rig.clipFadeAt then rig.clipFadeAt = now end
end
local function updateClip(rig: any, now: number)
    local character = rig.character
    if not character then return end
    local growth, catch, scale = num(character, "GrowthScore"), num(character, "CatchScore"), num(character, "VisualScale")
    if rig.lastScale == nil then rig.lastGrowth, rig.lastCatch, rig.lastScale = growth, catch, scale end
    if scale > rig.lastScale and rig.lastScale > 0 then playClip(rig, "happy", now)
    elseif (growth > rig.lastGrowth or catch > rig.lastCatch) and rig.clip ~= "happy" then playClip(rig, "eat", now) end
    rig.lastGrowth, rig.lastCatch, rig.lastScale = growth, catch, scale
    if rig.clip and now - rig.clipAt >= Clips.length(rig.clip) then rig.clip, rig.clipFadeAt = nil, nil end
    local still = rig.speed < 0.02 and rig.act == nil
    if not still then
        rig.lookAt = now + LOOK_AFTER
        if rig.clip == "look" then stopClip(rig, now) end
        if rig.clip == "happy" and rig.act ~= nil then stopClip(rig, now) end -- a jump takes over from the hops
    elseif rig.clip == nil and now >= rig.lookAt then
        playClip(rig, "look", now)
        rig.lookAt = now + Clips.length("look") + LOOK_AFTER + math.random() * LOOK_JITTER
    end
end
-- weight of the playing clip (0 = none); a stopped clip fades out
local function clipWeight(rig: any, now: number): number
    if not rig.clip then return 0 end
    if not rig.clipFadeAt then return 1 end
    local w = 1 - (now - rig.clipFadeAt) / CLIP_FADE
    if w <= 0 then rig.clip, rig.clipFadeAt = nil, nil return 0 end
    return w
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

-- BD-1217 rig follow-up: the hidden avatar's default R15 Animate plays human walk / jump tracks nobody sees (wasted work, human footstep
-- markers). Switch it off and stop its tracks, and any track it still starts while it shuts down (Studio showed its idle starting a moment
-- after a one-time stop). Nothing else in the game plays Animator tracks on the character. Returns false while there is no Animate or Animator
-- yet (added after spawn): asked again next frame.
local function muteDefaultAnimate(character: Model): boolean
    local animate = character:FindFirstChild("Animate")
    if not animate then return false end
    local hum = character:FindFirstChildOfClass("Humanoid")
    local animator = if hum then hum:FindFirstChildOfClass("Animator") else nil
    if not animate or not animator or not animator:IsA("Animator") then return false end
    if animate:IsA("BaseScript") then (animate :: any).Disabled = true end
    for _, track in animator:GetPlayingAnimationTracks() do track:Stop(0) end
    animator.AnimationPlayed:Connect(function(track: AnimationTrack) -- dies with the character's Animator
        if (animate :: any).Disabled == true then track:Stop(0) end
    end)
    return true
end

local function pivotFor(role: string, size: Vector3, side: number, joint: Vector3?): Vector3
    -- BD-1307: a model built with its own head/tail joint (Blender origin at the centre of the neck/tail cut, kept as the MeshPart PivotOffset,
    -- stored by LowPolyDinos.clone as a fraction of the part size) turns there; the box-corner guesses below are for the generated models.
    if joint and (role == "head" or role == "tail" or role == "neck") then return joint * size end
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
                side = part:GetAttribute("LPSide") or 1, lead = part:GetAttribute("LPLead") == true, joint = part:GetAttribute("LPJoint")})
        end
    end
    return list
end

-- BD-556: root height over the floor below it (nil = no floor in reach). Only the local player is checked (a ray 4 times a second while settled,
-- every frame for Pose.HipDipWindow after touch-down), so the cost is a handful of rays per second.
local function floorGap(rig: any): number?
    local at = rig.root.Position
    local hit = workspace:Raycast(at, Vector3.new(0, -12, 0), rig.rayParams)
    return if hit then at.Y - hit.Position.Y else nil
end
-- Studs the whole visual must be lifted so the hard-landing hip compression (the humanoid's spring) does not sink the feet into the ground.
local function hipDipFor(rig: any, now: number): number
    if rig.inAir and rig.root.AssemblyLinearVelocity.Y > -1 then return 0 end -- no rays while rising; a falling dino casts (the touch-down frame still reads as airborne)
    if now - rig.airAt > Pose.HipDipWindow then
        if now - rig.gapAt >= 0.25 then -- settled: learn the normal root-to-floor height
            rig.gapAt = now
            local g = floorGap(rig)
            if g then rig.restGap = if rig.restGap then rig.restGap + (g - rig.restGap) * 0.5 else g end
        end
        return 0
    end
    if not rig.restGap then return 0 end
    local g = floorGap(rig)
    return if g then Pose.hipDip(rig.restGap, g) else 0
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
    if amp == 0 then rig.act, rig.clip = nil, nil elseif npc then updateNpcAction(rig, npc, now) else updateAction(rig, now) updateClip(rig, now) end
    local phase = rig.act
    local rigOn = RIG and rig.class ~= "Water" -- Water dinos keep the sine strokes and the surge
    -- BD-1217: the jump / land clips start on the humanoid state change. Each plays to its own end (every clip ends at rest), so a landing
    -- during the jump clip overlaps the two instead of cutting one off (a cut popped up to 12 degrees in a frame: verify_motion_poses 555.smooth).
    -- A clip already playing is not restarted.
    local hops = rig.hops
    if not hops then hops = {} rig.hops = hops end
    if rigOn and not npc and phase ~= rig.prevAct then
        local name = if phase == "air" then "jump" elseif phase == "land" then "land" else nil
        if name and not hops[name] then hops[name] = now end
    end
    rig.prevAct = phase
    for name, at in hops do if amp == 0 or now - at >= Clips.length(name) then hops[name] = nil end end
    if RIG then -- BD-1217: follow-through springs (turn rate from the facing, rise / fall, the touch-down speed)
        rig.follow = rig.follow or Gait.newFollow()
        local look = root.CFrame.LookVector
        local yaw = math.atan2(-look.X, -look.Z)
        local turn = if rig.yaw then Gait.turnRate(rig.yaw, yaw, dt) else 0
        rig.yaw = yaw
        local landSpeed = if rig.wasAir and not rig.inAir then math.max(0, -(rig.fallVy or 0)) else 0
        if rig.inAir then rig.fallVy = v.Y end
        rig.wasAir = rig.inAir
        Gait.stepFollow(rig.follow, dt, turn, if rig.inAir then v.Y else 0, landSpeed, amp)
    end
    local k = 0
    if phase then
        local elapsed = now - rig.actAt
        local dur = Pose.duration(phase, rig.aggr, rig.class)
        ctx.phase, ctx.t, ctx.aggr, ctx.carry, ctx.flap, ctx.wing = phase, elapsed, rig.aggr, rig.carry, rig.flap, rig.wing
        ctx.p = if dur > 0 then math.clamp(elapsed / dur, 0, 1) else 0
        ctx.direct = phase == "air" -- BD-555: the air phase always begins at take-off now, with no stretch of its own
        k = if phase == "air" then Pose.airWeight(elapsed) elseif phase == "land" then Pose.landWeight(ctx.p, rig.landFrom) else Pose.actionWeight(phase, ctx.p)
    end
    local bob = (if rigOn then Gait.bob(now + rig.seed, rig.phase, rig.speed, amp) else Pose.bob(now + rig.seed, rig.phase, rig.speed, amp, rig.class))
        * height -- BD-388: one shared translation for every part
    if amp > 0 and rig.rayParams then bob += hipDipFor(rig, now) end -- BD-556: the same lift for every part, so nothing slides
    local cw = clipWeight(rig, now)
    local clipT = if cw > 0 then now - rig.clipAt else 0
    if cw > 0 then bob += Clips.sample(rig.clip, "root", 1, clipT, clipOut).bob * height * cw end -- BD-1217: the clip's whole-dino lift
    for _, item in rig.parts do
        local part = item.part :: MeshPart
        if not part.Parent then continue end
        Pose.sample(item.role, item.side, item.lead, now + rig.seed, rig.phase, rig.speed, amp, out, rig.class)
        if rigOn and Gait.uses(item.role, rig.class) then -- BD-1217: the authored loop replaces the sine pose of this part
            Gait.sample(item.role, item.side, item.lead, now + rig.seed, rig.phase, rig.speed, amp, height, out, rig.class)
        end
        if phase == "defeat" then Pose.blend(out, Pose.sampleDefeat(item.role, item.side, item.lead, ctx, amp, actOut, rig.class, rig.skin), k)
        elseif phase then Pose.blend(out, Pose.sampleAction(item.role, item.side, item.lead, ctx, amp, actOut, rig.class), k) end
        if cw > 0 then
            Clips.sample(rig.clip, item.role, item.side, clipT, clipOut)
            out.pitch += clipOut.pitch * cw
            out.yaw += clipOut.yaw * cw
            out.roll += clipOut.roll * cw
            out.fwd += clipOut.fwd * height * cw
        end
        for name, at in hops do -- BD-1217: jump / land clips on top of the procedural tuck and squash
            Clips.sample(name, item.role, item.side, now - at, clipOut)
            out.pitch += clipOut.pitch
            out.yaw += clipOut.yaw
            out.roll += clipOut.roll
        end
        if RIG then Gait.addFollow(rig.follow, item.role, amp, out) end
        if amp == 0 and item.role ~= "wing" then
            item.weld.C1 = CFrame.identity
        else
            local pivot = pivotFor(item.role, part.Size, item.side, item.joint)
            -- Joint pivot rotation (the anchor never moves, no stretch) + shared whole-body bob + head peck forward in studs (-Z), both
            -- expressed in the part's own frame through the weld's rest rotation.
            local lift = 0 -- BD-556: a Water flipper pivots at mid height and its tip dipped up to 0.3 stud into the ground: hold the lowest corner at its rest height
            if item.role == "flipper" then
                local up = item.weld.C0.Rotation:Inverse() * Vector3.new(0, 1, 0)
                lift = Pose.restLift({part.Size.X, part.Size.Y, part.Size.Z}, {pivot.X, pivot.Y, pivot.Z}, out.pitch, out.yaw, out.roll, {up.X, up.Y, up.Z})
            end
            local shift = item.weld.C0.Rotation:Inverse() * Vector3.new(0, bob, -out.fwd)
            if lift > 0 then shift += item.weld.C0.Rotation:Inverse() * Vector3.new(0, lift, 0) end
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
        local previous = rig
        if not rig or rig.visual ~= visual then
            local _, size = visual:GetBoundingBox()
            -- character: updateAction reads it (jump, leap, land, surge, defeat). It was never set, so those poses never played (found by tools/verify_motion_poses.py).
            rig = {character = character, visual = visual, root = root, parts = collect(visual), phase = 0, speed = 0, acc = 0,
                height = math.max(size.Y, 1), aggr = 0, carry = 0, landFrom = 1, flap = 0, wing = 1, airAt = -10, gapAt = -10, leapAt = -10, lastPredict = 0, lastUntil = 0, jumpHeld = false, surgeLeap = -1, amp = 1, class = visual:GetAttribute("LPClass"), skin = Pose.skinOf(visual:GetAttribute("LPSkin")), seed = math.random() * 10}
            if player == Players.LocalPlayer then -- BD-556: only the local dino looks for the hard-landing hip dip
                local params = RaycastParams.new()
                params.FilterType = Enum.RaycastFilterType.Exclude
                params.FilterDescendantsInstances = {character}
                rig.rayParams = params
            end
            rigs[character] = rig
            rig.lookAt = now + LOOK_AFTER
            rig.species = character:GetAttribute("SpeciesId")
            if previous then -- BD-1217: a rebuilt visual keeps the clip triggers' memory; a NEW species put on plays happy
                rig.lastGrowth, rig.lastCatch, rig.lastScale = previous.lastGrowth, previous.lastCatch, previous.lastScale
                if previous.species ~= nil and rig.species ~= previous.species and amp > 0 then playClip(rig, "happy", now) end
            end
        end
        if player == Players.LocalPlayer then
            if RIG and not rig.animateOff then rig.animateOff = muteDefaultAnimate(character) end
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
            rig = {visual = visual, root = root, parts = collect(visual), phase = 0, speed = 0, acc = 0, height = math.max(size.Y, 1), aggr = 0, carry = 0, landFrom = 1, flap = 0, wing = 1,
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
