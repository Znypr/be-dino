--!strict
-- BD-234 spike: procedural idle/walk for the low-poly dinos (Config.LowPolyDinos). Pose math: Shared/LowPolyPose (pure).
-- Writes Weld.C1 (the animation offset) so DinoMotion's C0 poses (eat, jump squash/stretch, landing) keep working on top.
-- Respects Reduce Motion (Theme.MotionEnabled). Remote dinos are animated at 20 Hz within 80 studs only.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Pose = require(Shared.LowPolyPose)
local LowPoly = require(Shared.LowPolyDinos)
local Theme = require(Shared.UITheme)
if not LowPoly.enabled() then return end

local RANGE, REMOTE_STEP, RUN_SPEED = 80, 1 / 20, 24
local rigs: {[Model]: any} = {}
local out = Pose.new()

local function pivotFor(role: string, size: Vector3): Vector3
    if role == "head" then return Vector3.new(0, -size.Y / 2, size.Z / 2) end -- neck, bottom back
    if role == "tail" then return Vector3.new(0, 0, -size.Z / 2) end -- tail root: the front (-Z) end meets the body
    if role == "arm" or role == "leg" then return Vector3.new(0, size.Y / 2, 0) end -- hip/shoulder
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

local function apply(rig: any, now: number, dt: number, amp: number)
    local root = rig.root
    local v = root.AssemblyLinearVelocity
    local speed01 = math.clamp(math.sqrt(v.X * v.X + v.Z * v.Z) / RUN_SPEED, 0, 1)
    if speed01 < 0.06 then speed01 = 0 end
    rig.speed = rig.speed + (speed01 - rig.speed) * math.min(1, dt * 8) -- ease in/out
    rig.phase = (rig.phase + dt * Pose.stepRate(rig.speed) * (if rig.speed > 0.01 then 1 else 0)) % (2 * math.pi * 8)
    local height = rig.height
    for _, item in rig.parts do
        local part = item.part :: MeshPart
        if not part.Parent then continue end
        Pose.sample(item.role, item.side, item.lead, now + rig.seed, rig.phase, rig.speed, amp, out)
        if amp == 0 then
            item.weld.C1 = CFrame.identity
        else
            local pivot = pivotFor(item.role, part.Size)
            local anim = CFrame.new(pivot) * CFrame.Angles(out.pitch, out.yaw, out.roll) * CFrame.new(-pivot)
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
                height = math.max(size.Y, 1), seed = math.random() * 10}
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
Players.PlayerRemoving:Connect(function(player) if player.Character then untrack(player.Character) end end)
