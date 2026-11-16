--!strict
-- BD-1244 (owner 2026-11-16 "game still looks empty"): calm ambient life on the World V3 island, CLIENT ONLY. ONLY while
-- Config.IslandLifeEnabled and Config.WorldV3Enabled are on (playtest profile): otherwise this script returns on its first lines.
-- Butterfly flocks beside the paths, dragonflies at the water, gulls circling high, and small wild baby dinos grazing near the paths
-- (the V3 low-poly dinos posed with the BD-1217 clips through Shared/LowPolyPose, LowPolyGait and LowPolyClips; those files are only called).
-- Cheap on purpose (docs/107, BD-1222): models are pooled and exist only within IslandLife.CullRadius of the camera, capped per device
-- class; everything is anchored, CanCollide / CanTouch / CanQuery off, no Humanoid, no physics. Nothing here talks to the server, so the
-- babies can never be caught, eaten, hit or counted by the NPC predators (they live in workspace.IslandLife, not in the NPC folder).
-- Data and pure rules: src/shared/IslandLife.luau (tools/verify_island_life.py). Reduce Motion: no flying critters, babies stand still.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config")) :: any
local Life = require(Shared:WaitForChild("IslandLife"))
if not Life.enabled(Config) then return end

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local WorldV3 = require(Shared:WaitForChild("WorldV3")) :: any
local Theme = require(Shared:WaitForChild("UITheme")) :: any
local LowPoly = require(Shared:WaitForChild("LowPolyDinos"))
local Pose = require(Shared:WaitForChild("LowPolyPose"))
local Gait = require(Shared:WaitForChild("LowPolyGait"))
local Clips = require(Shared:WaitForChild("LowPolyClips"))

local player = Players.LocalPlayer
local RIG = Config.DinoRigClipsEnabled == true
local RUN_SPEED = 24 -- LowPolyAnimator's run speed; a baby's legs are half as long, so its cadence uses RUN_SPEED * BabyScale
local deviceClass = (function(): string
    local size = workspace.CurrentCamera.ViewportSize
    return if not UserInputService.TouchEnabled then "Desktop" elseif math.min(size.X, size.Y) >= 600 then "Tablet" else "Phone"
end)()
local caps = Life.capsFor(deviceClass)

local folder = Instance.new("Folder")
folder.Name = "IslandLife"
folder.Parent = workspace
local random = Random.new()

local terrainRay = RaycastParams.new()
terrainRay.FilterType = Enum.RaycastFilterType.Include
terrainRay.FilterDescendantsInstances = {workspace.Terrain}
local openRay = RaycastParams.new()
openRay.FilterType = Enum.RaycastFilterType.Exclude
openRay.FilterDescendantsInstances = {folder}

local function groundY(x: number, z: number): number?
    local hit = workspace:Raycast(Vector3.new(x, 300, z), Vector3.new(0, -600, 0), terrainRay)
    if not hit or hit.Material == Enum.Material.Water then return nil end
    return hit.Position.Y
end
-- true when nothing (a tree, rock, bush, food or player) stands on the terrain at (x, z): babies only walk to open ground
local function openGround(x: number, z: number): boolean
    local hit = workspace:Raycast(Vector3.new(x, 300, z), Vector3.new(0, -600, 0), openRay)
    return hit ~= nil and hit.Instance == workspace.Terrain and hit.Material ~= Enum.Material.Water
end
local function hidden(): boolean
    local location = player:GetAttribute("Location")
    return location ~= nil and location ~= "Island" -- nil = no cave hub: the island is all there is
end

-- ---------------------------------------------------------------- baby dinos
local function pivotFor(role: string, size: Vector3, side: number): Vector3 -- same joints as LowPolyAnimator
    if role == "wing" or role == "flipper" then return Vector3.new(-side * size.X / 2, 0, 0) end
    if role == "head" or role == "neck" then return Vector3.new(0, -size.Y / 2, size.Z / 2) end
    if role == "tail" then return Vector3.new(0, 0, -size.Z / 2) end
    if role == "arm" or role == "leg" then return Vector3.new(0, size.Y / 2, 0) end
    return Vector3.zero
end

local babyPool: {[string]: {any}} = {}
local function buildBaby(species: string): any?
    local model = LowPoly.clone(species, nil)
    if not model then return nil end
    model:ScaleTo(Life.BabyScale)
    model:PivotTo(CFrame.new())
    local root = Instance.new("Part")
    root.Name = "LifeRoot"
    root.Size = Vector3.new(.2, .2, .2)
    root.Transparency = 1
    root.Anchored, root.CanCollide, root.CanTouch, root.CanQuery = true, false, false, false
    root.CFrame = CFrame.new()
    local parts = {}
    for _, item in model:GetDescendants() do
        if item:IsA("BasePart") then
            item.Anchored, item.CanCollide, item.CanTouch, item.CanQuery = false, false, false, false
            item.CastShadow = deviceClass == "Desktop"
            local weld = Instance.new("Weld")
            weld.Name = "LifeWeld"
            weld.C0 = root.CFrame:ToObjectSpace(item.CFrame)
            weld.Part0, weld.Part1, weld.Parent = root, item, item
            table.insert(parts, {part = item, weld = weld, role = item:GetAttribute("LPRole") or "body", side = item:GetAttribute("LPSide") or 1,
                lead = item:GetAttribute("LPLead") == true, pivot = pivotFor(item:GetAttribute("LPRole") or "body", item.Size, item:GetAttribute("LPSide") or 1)})
        end
    end
    root.Parent = model
    model.PrimaryPart = root
    model.Name = "Baby_" .. species
    local _, size = model:GetBoundingBox()
    return {model = model, root = root, parts = parts, height = math.max(size.Y, 1), class = model:GetAttribute("LPClass"), species = species}
end

type Baby = {home: Vector3, species: string, zone: string, rig: any?, mode: string, modeUntil: number, tx: number, tz: number,
    pos: Vector3, yaw: number, phase: number, speed: number, clip: string?, clipAt: number, shyAt: number, nextGround: number, failedAt: number, acc: number}
local babies: {Baby} = {}
local herd: {any} = {}
for _, spot in Life.spawnSpots(WorldV3) do table.insert(herd, spot) end
for _, zoneId in Life.Zones do
    for _, spot in Life.herdSpots(WorldV3, zoneId, caps.babiesPerZone) do spot.zone = zoneId table.insert(herd, spot) end
end
do
    for _, spot in herd do
        local zoneId = spot.zone
        local home = Vector3.new(spot.x, 0, spot.z)
        table.insert(babies, {home = home, species = spot.species, zone = zoneId, rig = nil, mode = "idle", modeUntil = 0, tx = spot.x, tz = spot.z,
            pos = home, yaw = Life.hash01(spot.x, spot.z) * math.pi * 2, phase = 0, speed = 0, clip = nil, clipAt = 0, shyAt = -100, nextGround = 0, failedAt = -100, acc = 0})
    end
end

local out, clipOut = Pose.new(), Clips.new()
local function poseBaby(b: Baby, now: number, dt: number, amp: number)
    local rig = b.rig
    if not rig then return end
    local speed01 = math.clamp(b.speed / (RUN_SPEED * Life.BabyScale), 0, 1)
    b.phase = (b.phase + dt * Pose.stepRate(speed01) * (if speed01 > .01 then 1 else 0)) % (2 * math.pi * 8)
    local height = rig.height
    local seed = b.home.X
    local bob = (if RIG then Gait.bob(now + seed, b.phase, speed01, amp) else Pose.bob(now + seed, b.phase, speed01, amp, rig.class)) * height
    local clip = if amp > 0 then b.clip else nil
    local clipT = now - b.clipAt
    if clip and clipT >= Clips.length(clip) then
        if b.mode == "graze" and clip == "eat" then b.clipAt, clipT = now, 0 else b.clip, clip = nil, nil end -- grazing repeats the eat clip
    end
    if clip then bob += Clips.sample(clip, "root", 1, clipT, clipOut).bob * height end
    for _, item in rig.parts do
        Pose.sample(item.role, item.side, item.lead, now + seed, b.phase, speed01, amp, out, rig.class)
        if RIG and Gait.uses(item.role, rig.class) then
            Gait.sample(item.role, item.side, item.lead, now + seed, b.phase, speed01, amp, height, out, rig.class)
        end
        if clip then
            Clips.sample(clip, item.role, item.side, clipT, clipOut)
            out.pitch += clipOut.pitch
            out.yaw += clipOut.yaw
            out.roll += clipOut.roll
            out.fwd += clipOut.fwd * height
        end
        local pivot = item.pivot
        local shift = item.weld.C0.Rotation:Inverse() * Vector3.new(0, bob, -out.fwd)
        local anim = CFrame.new(shift) * CFrame.new(pivot) * CFrame.Angles(out.pitch, out.yaw, out.roll) * CFrame.new(-pivot)
            * CFrame.new(0, out.dy * height, out.dz * height)
        item.weld.C1 = anim:Inverse()
    end
end

local function setMode(b: Baby, mode: string, now: number)
    b.mode = mode
    b.modeUntil = now + Life.duration(mode, random:NextNumber())
    if mode == "graze" then b.clip, b.clipAt = "eat", now
    elseif mode == "look" then b.clip, b.clipAt = "look", now
    elseif mode == "walk" then
        b.clip = nil
        for _ = 1, 4 do -- open ground only; otherwise it stays and grazes
            local tx, tz = Life.walkTarget(b.home.X, b.home.Z, random:NextNumber(), random:NextNumber())
            if WorldV3.path(tx, tz) < .3 and openGround(tx, tz) then b.tx, b.tz = tx, tz return end -- grass, not the path
        end
        b.mode, b.clip, b.clipAt = "graze", "eat", now
    else b.clip = nil end
end

local function stepBaby(b: Baby, now: number, dt: number, amp: number, me: Vector3?)
    if amp == 0 then b.speed = 0 return end
    if me and now - b.shyAt > Life.ShyCooldown and (Vector3.new(me.X, 0, me.Z) - Vector3.new(b.pos.X, 0, b.pos.Z)).Magnitude < Life.ShyRadius then
        b.shyAt = now -- a player walks up: look at them and hop (happy clip), then carry on
        b.yaw = math.atan2(-(me.X - b.pos.X), -(me.Z - b.pos.Z))
        b.mode, b.modeUntil, b.clip, b.clipAt, b.speed = "idle", now + Clips.length("happy") + .4, "happy", now, 0
    end
    if b.mode == "walk" then
        local dx, dz = b.tx - b.pos.X, b.tz - b.pos.Z
        local d = math.sqrt(dx * dx + dz * dz)
        if d < .5 or now > b.modeUntil then setMode(b, Life.nextMode(random:NextNumber()), now) b.speed = 0 return end
        local want = math.atan2(-dx, -dz)
        local diff = (want - b.yaw + math.pi) % (2 * math.pi) - math.pi
        b.yaw += math.clamp(diff, -dt * 2.5, dt * 2.5)
        local speed = if math.abs(diff) > .8 then Life.WalkSpeed * .3 else Life.WalkSpeed
        b.speed += (speed - b.speed) * math.min(1, dt * 4)
        local step = math.min(d, b.speed * dt)
        b.pos += Vector3.new(dx / d * step, 0, dz / d * step)
    else
        b.speed += (0 - b.speed) * math.min(1, dt * 5)
        if now > b.modeUntil then setMode(b, Life.nextMode(random:NextNumber()), now) end
    end
end

local function placeBaby(b: Baby, now: number)
    if now >= b.nextGround then
        b.nextGround = now + (if b.speed > .1 then .25 else 2)
        local y = groundY(b.pos.X, b.pos.Z)
        if y then b.pos = Vector3.new(b.pos.X, y, b.pos.Z) end
    end
    local rig = b.rig
    if rig then rig.root.CFrame = CFrame.new(b.pos) * CFrame.Angles(0, b.yaw, 0) end
end

local function activateBaby(b: Baby, now: number): boolean
    if now - b.failedAt < 5 then return false end
    local pool = babyPool[b.species]
    local rig = if pool and #pool > 0 then table.remove(pool) else buildBaby(b.species)
    if not rig then b.failedAt = now return false end -- template not replicated yet (LowPolyDinos loader): try again in 5 s
    b.rig = rig
    if b.pos.Y == 0 and not openGround(b.home.X, b.home.Z) then -- the home spot is under a bush or a rock: the nearest open ground around it
        for _, r in {4, 7, 10} do
            local moved = false
            for k = 0, 7 do
                local a = k * math.pi / 4
                local x, z = b.home.X + math.cos(a) * r, b.home.Z + math.sin(a) * r
                if WorldV3.path(x, z) < .3 and openGround(x, z) then b.home, b.pos, moved = Vector3.new(x, 0, z), Vector3.new(x, 0, z), true break end
            end
            if moved then break end
        end
    end
    if b.pos.Y == 0 then
        local y = groundY(b.pos.X, b.pos.Z)
        b.pos = Vector3.new(b.pos.X, y or 2, b.pos.Z)
    end
    b.nextGround = 0
    placeBaby(b, now)
    rig.model.Parent = folder
    setMode(b, "graze", now)
    return true
end
local function deactivateBaby(b: Baby)
    local rig = b.rig
    if not rig then return end
    rig.model.Parent = nil
    for _, item in rig.parts do item.weld.C1 = CFrame.identity end
    babyPool[b.species] = babyPool[b.species] or {}
    table.insert(babyPool[b.species], rig)
    b.rig = nil
end

-- ---------------------------------------------------------------- critters (one MeshPart each)
local templates: Folder? = nil
task.spawn(function() templates = ReplicatedStorage:WaitForChild(Life.FolderName, 120) :: Folder? end)
local critterPool: {[string]: {MeshPart}} = {}
local SIZE = {life_butterfly_orange = 2.2, life_butterfly_blue = 2.2, life_dragonfly = 2.6, life_gull = 7} -- studs across (wingspan)
local function takeCritter(key: string): MeshPart?
    local pool = critterPool[key]
    if pool and #pool > 0 then return table.remove(pool) end
    local t = templates
    local source = if t then t:FindFirstChild(key) else nil
    if not source or not source:IsA("MeshPart") then return nil end
    local part = source:Clone()
    part.Size = part.Size * (SIZE[key] / math.max(part.Size.X, .01))
    part:SetAttribute("BaseSize", part.Size)
    part.Anchored, part.CanCollide, part.CanTouch, part.CanQuery, part.CastShadow = true, false, false, false, false
    return part
end
local function giveBack(key: string, part: MeshPart)
    part.Parent = nil
    critterPool[key] = critterPool[key] or {}
    table.insert(critterPool[key], part)
end

type Group = {centre: Vector3, key: string, kind: string, members: {MeshPart}, count: number}
local flocks: {Group} = {}
for _, spot in Life.flockSpots(WorldV3) do
    table.insert(flocks, {centre = Vector3.new(spot.x, 0, spot.z), key = spot.kind, kind = "flock", members = {}, count = caps.perFlock})
end
for i, spot in Life.dragonflySpots(WorldV3) do
    if i > caps.dragonflies then break end
    table.insert(flocks, {centre = Vector3.new(spot.x, 0, spot.z), key = "life_dragonfly", kind = "dart", members = {}, count = 1})
end
local gulls: {MeshPart?} = {}

-- The generated butterfly and dragonfly stand upright (body along +Y, wings in the XY plane). A butterfly is tipped 50 degrees (head up,
-- wings open toward the sky) so it reads from the low game camera as well as from above; the dragonfly is laid flat, head forward.
local BUTTERFLY_TURN = CFrame.Angles(-math.rad(50), 0, 0)
local DRAGONFLY_TURN = CFrame.Angles(-math.pi / 2, 0, 0)
local GULL_TURN = CFrame.Angles(0, math.rad(Life.GullYaw or 0), 0)
local function stepGroup(g: Group, t: number)
    for i, part in g.members do
        local base = part:GetAttribute("BaseSize") :: Vector3
        if g.kind == "flock" then
            local x, y, z = Life.flutter(i, t)
            local x2, _, z2 = Life.flutter(i, t + .1)
            local at = g.centre + Vector3.new(x, y, z)
            local dir = Vector3.new(x2 - x, 0, z2 - z)
            local look = if dir.Magnitude > 1e-3 then CFrame.lookAt(at, at + dir) else CFrame.new(at)
            part.CFrame = look * CFrame.Angles(0, 0, math.sin(t * 2 + i) * .25) * BUTTERFLY_TURN
            part.Size = Vector3.new(base.X * Life.flap(i, t), base.Y, base.Z)
        else
            local x, y, z = Life.dart(i + g.centre.X, t)
            local x2, _, z2 = Life.dart(i + g.centre.X, t + .05)
            local at = g.centre + Vector3.new(x, y, z)
            local dir = Vector3.new(x2 - x, 0, z2 - z)
            local look = if dir.Magnitude > 1e-3 then CFrame.lookAt(at, at + dir) else CFrame.new(at)
            part.CFrame = look * DRAGONFLY_TURN
        end
    end
end
local function showGroup(g: Group): boolean
    if #g.members > 0 then return true end
    local y = groundY(g.centre.X, g.centre.Z)
    if not y then return false end
    g.centre = Vector3.new(g.centre.X, y, g.centre.Z)
    for _ = 1, g.count do
        local part = takeCritter(g.key)
        if not part then break end
        part.Parent = folder
        table.insert(g.members, part)
    end
    return #g.members > 0
end
local function hideGroup(g: Group)
    for _, part in g.members do giveBack(g.key, part) end
    table.clear(g.members)
end

-- ---------------------------------------------------------------- the loops: cull twice a second, move every frame (cheap: a few CFrames)
local nextCull = 0
local babyCount, flockCount = 0, 0
RunService.Heartbeat:Connect(function(dt)
    local now = os.clock()
    local camera = workspace.CurrentCamera
    if not camera then return end
    local eye = camera.CFrame.Position
    local amp = if Theme.MotionEnabled then 1 else 0
    local flyOk = amp > 0 and (workspace:GetAttribute("WeatherId") or "clear") == "clear" and not hidden()
    if now >= nextCull then
        nextCull = now + .5
        local away = hidden()
        -- babies: in front of the camera and nearest first, within the cap
        local order = {}
        local look = camera.CFrame.LookVector
        local function score(x: number, z: number, d: number): number -- in front of the camera first: what is behind waits for a free slot
            return d + (if (x - eye.X) * look.X + (z - eye.Z) * look.Z < 0 then Life.BehindPenalty else 0)
        end
        for _, b in babies do
            local d = (Vector3.new(b.pos.X, eye.Y, b.pos.Z) - eye).Magnitude
            table.insert(order, {b = b, d = d, s = score(b.pos.X, b.pos.Z, d)})
        end
        table.sort(order, function(a, c) return a.s < c.s end)
        babyCount = 0
        for _, item in order do
            local b = item.b :: Baby
            local inRange = item.d <= Life.CullRadius or (b.rig ~= nil and item.d <= Life.CullRadius + 10) -- 10 studs of hysteresis: no flicker at the edge
            if not away and inRange and babyCount < caps.babies and (b.rig ~= nil or activateBaby(b, now)) then babyCount += 1
            elseif b.rig then deactivateBaby(b) end
        end
        -- flocks and dragonflies
        local shown = {flock = 0, dart = 0}
        local groups = {}
        for _, g in flocks do
            local d = (Vector3.new(g.centre.X, eye.Y, g.centre.Z) - eye).Magnitude
            table.insert(groups, {g = g, d = d, s = score(g.centre.X, g.centre.Z, d)})
        end
        table.sort(groups, function(a, c) return a.s < c.s end)
        for _, item in groups do
            local g, d = item.g :: Group, item.d
            local cap = if g.kind == "flock" then caps.flocks else caps.dragonflies
            local inRange = d <= Life.CullRadius or (#g.members > 0 and d <= Life.CullRadius + 10)
            if flyOk and inRange and shown[g.kind] < cap and showGroup(g) then shown[g.kind] += 1
            elseif #g.members > 0 then hideGroup(g) end
        end
        flockCount = shown.flock + shown.dart
        -- gulls: always in the sky over the island (a handful of parts), gone with Reduce Motion or off the island
        for i = 1, math.min(caps.gulls, #Life.Gulls) do
            local part = gulls[i]
            if amp > 0 and not away then
                if not part then
                    part = takeCritter("life_gull")
                    if part then part.Parent = folder end
                    gulls[i] = part
                end
            elseif part then giveBack("life_gull", part) gulls[i] = nil end
        end
        folder:SetAttribute("Babies", babyCount)
        folder:SetAttribute("Groups", flockCount)
    end
    local me: Vector3? = nil
    local character = player.Character
    local rootPart = if character then character:FindFirstChild("HumanoidRootPart") else nil
    if rootPart and rootPart:IsA("BasePart") then me = rootPart.Position end
    for _, b in babies do
        if b.rig then
            stepBaby(b, now, dt, amp, me)
            local near = (b.pos - eye).Magnitude <= Life.AnimRadius
            b.acc += dt
            if near and b.acc >= 1 / 20 or b.acc >= .25 then
                placeBaby(b, now)
                poseBaby(b, now, b.acc, amp)
                b.acc = 0
            end
        end
    end
    for _, g in flocks do if #g.members > 0 then stepGroup(g, now) end end
    for i, part in gulls do
        if part then
            local x, y, z, heading = Life.gullAt(i, now)
            local fwd = Vector3.new(math.cos(heading), 0, math.sin(heading))
            local at = Vector3.new(x, y, z)
            part.CFrame = CFrame.lookAt(at, at + fwd) * CFrame.Angles(0, 0, .25 * (Life.Gulls[i].dir)) * GULL_TURN
        end
    end
end)
