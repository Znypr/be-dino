--!strict
-- BD-312 / docs/87: the client side of the wild predators' look. (1) A gentle idle/walk bob on the LEGACY simple NPC models. Low-poly
-- NPCs (model attribute NpcLowPoly, BD-324) are animated by LowPolyAnimator instead, with the same LowPolyPose functions as players. (2) The soft fade-out when the server marks a defeated NPC NpcFading (0.6 s, 0.15 s under Reduce Motion).
-- Pure maths: Shared/NpcPredatorRules (bobOffset, fadeSeconds). Started by CombatHud.attach, so with Config.CombatEnabled false
-- nothing in this file ever runs.
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("NpcPredatorRules"))
local Theme = require(Shared:WaitForChild("UITheme"))

local Motion = {}
local RANGE = 120
local baseC0: {[Weld]: CFrame} = setmetatable({}, {__mode = "k"}) :: any
local fading: {[Model]: boolean} = setmetatable({}, {__mode = "k"}) :: any
local phase: {[Model]: number} = setmetatable({}, {__mode = "k"}) :: any

local function fade(model: Model)
    fading[model] = true
    local info = TweenInfo.new(Rules.fadeSeconds(not Theme.MotionEnabled), Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
    for _, item in model:GetDescendants() do
        if item:IsA("BasePart") and item.Transparency < 1 then
            TweenService:Create(item, info, {Transparency = 1}):Play()
        end
    end
end

local function bob(model: Model, root: BasePart, dt: number)
    local v = root.AssemblyLinearVelocity
    local speed01 = math.clamp(math.sqrt(v.X * v.X + v.Z * v.Z) / 11, 0, 1)
    local t = (phase[model] or math.random() * 10) + dt * Rules.bobRate(speed01)
    phase[model] = t
    local offset = Rules.bobOffset(t, speed01, not Theme.MotionEnabled)
    for _, item in model:GetDescendants() do
        if item:IsA("Weld") and (item.Name == "ResourceWeld" or item.Name == "VisualWeld") and item.Part0 == root then
            local base = baseC0[item]
            if not base then base = item.C0 baseC0[item] = base end
            item.C0 = CFrame.new(0, offset, 0) * base
        end
    end
end

function Motion.attach()
    RunService.Heartbeat:Connect(function(dt)
        local folder = workspace:FindFirstChild("BeDinoNpcs")
        if not folder then return end
        local camera = workspace.CurrentCamera
        for _, model in folder:GetChildren() do
            if not model:IsA("Model") then continue end
            if model:GetAttribute("NpcFading") == true then
                if not fading[model] then fade(model) end
                continue
            end
            local root = model:FindFirstChild("HumanoidRootPart")
            -- BD-324: low-poly NPCs are posed by LowPolyAnimator (same pose functions as players); the bob is for the legacy models only
            if model:GetAttribute("NpcLowPoly") ~= true and root and root:IsA("BasePart") and (not camera or (camera.CFrame.Position - root.Position).Magnitude <= RANGE) then
                bob(model, root, dt)
            end
        end
    end)
end

return Motion
