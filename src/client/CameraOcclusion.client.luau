--!strict
-- BD-253: world props between the camera and the dino (or around the camera) fade to ~80% transparent so the dino and food
-- stay readable (docs/87). Client-only visuals through LocalTransparencyModifier; nothing replicates, nothing collides.
-- Only WorldKit props are ever touched (never the dino, food, eggs, crystals or UI). All rules live in the pure module
-- Shared/CameraOcclusion (tools/verify_camera_occlusion.py). Cost: a grid lookup 15 times a second plus at most MaxProps
-- props / MaxParts parts faded per frame.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Occ = require(Shared:WaitForChild("CameraOcclusion"))
local settings = (Config :: any).CameraOcclusion
if settings and settings.Enabled == false then return end
local player = Players.LocalPlayer
local camera = workspace.CurrentCamera

type Prop = {item: Instance, parts: {BasePart}, box: {x: number, y: number, z: number, sx: number, sy: number, sz: number}, fade: number, goal: number}
local props: {Prop} = {}
local grid = Occ.newGrid()
local known: {[Instance]: boolean} = {}
local pending: {Instance} = {}
local active: {[number]: boolean} = {} -- prop ids currently fading or faded
local scratch: {number} = {}

local function register(item: Instance)
    if known[item] or string.sub(item.Name, -8) == "Collider" then return end
    local parts: {BasePart} = {}
    local function take(p: Instance) if p:IsA("BasePart") and p.Transparency < 0.95 and string.sub(p.Name, -8) ~= "Collider" then table.insert(parts, p) end end
    take(item)
    for _, d in item:GetDescendants() do take(d) end
    if #parts == 0 then return end
    known[item] = true
    local cf, size
    if item:IsA("Model") then cf, size = item:GetBoundingBox() else cf, size = (item :: BasePart).CFrame, (item :: BasePart).Size end
    local box = {x = cf.Position.X, y = cf.Position.Y, z = cf.Position.Z, sx = size.X, sy = size.Y, sz = size.Z}
    if math.max(box.sx, box.sz) / 2 < Occ.MinRadius or box.sy < Occ.MinHeight then return end -- ground cover never fades
    table.insert(props, {item = item, parts = parts, box = box, fade = 0, goal = 0})
    Occ.insert(grid, #props, box.x, box.z, math.max(box.sx, box.sz) / 2 + Occ.CameraPad)
end

task.spawn(function()
    local arena = workspace:WaitForChild("BeDinoArena", 60)
    local kit = if arena then arena:WaitForChild("WorldKit", 20) else nil
    if not kit then return end
    for _, item in kit:GetChildren() do table.insert(pending, item) end
    kit.ChildAdded:Connect(function(item) table.insert(pending, item) end)
end)

local function setFade(prop: Prop, value: number)
    prop.fade = value
    for _, part in prop.parts do part.LocalTransparencyModifier = value end
end

local accumulator, lastMotion = 0, Theme.MotionEnabled
RunService.Heartbeat:Connect(function(dt)
    -- Register a few props per frame (they arrive over several frames and a big kit must not hitch one frame).
    for _ = 1, 60 do
        local item = table.remove(pending)
        if not item then break end
        register(item)
    end
    local reduce = not Theme.MotionEnabled
    local character = player.Character
    local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
    local enabled = camera and root and root:IsA("BasePart") and camera.CameraType == Enum.CameraType.Custom
    accumulator += dt
    if accumulator >= 1 / 15 or reduce ~= not lastMotion then
        accumulator, lastMotion = 0, Theme.MotionEnabled
        for _, prop in props do prop.goal = 0 end
        if enabled then
            local scale = character:GetAttribute("VisualScale")
            local aim = (root :: BasePart).Position + Vector3.new(0, 1.5 * (if typeof(scale) == "number" then scale else 1), 0)
            local cp = camera.CFrame.Position
            local camT, aimT = {x = cp.X, y = cp.Y, z = cp.Z}, {x = aim.X, y = aim.Y, z = aim.Z}
            local candidates = {}
            for _, id in Occ.query(grid, cp.X, cp.Z, aim.X, aim.Z, scratch) do
                local prop = props[id]
                if prop.item.Parent then -- culled (parent nil) props are not rendered anyway
                    local dist = Occ.qualifies(prop.box, camT, aimT)
                    if dist then table.insert(candidates, {id = id, dist = dist, parts = #prop.parts}) end
                end
            end
            for _, id in Occ.select(candidates) do
                props[id].goal = Occ.FadeTransparency
                active[id] = true
            end
        end
        -- Anything still fading that is no longer chosen keeps animating back to 0 below.
        for id in active do if props[id].goal == 0 and props[id].fade == 0 then active[id] = nil end end
    end
    for id in active do
        local prop = props[id]
        local nextFade = Occ.step(prop.fade, prop.goal, dt, reduce)
        if nextFade ~= prop.fade then setFade(prop, nextFade) end
        if prop.goal == 0 and nextFade == 0 then active[id] = nil end
    end
end)
