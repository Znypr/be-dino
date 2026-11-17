--!strict
-- BD-1248 (Config.PlazaShopsV2Enabled, Shared/PlazaShopsLayout): a small V3 low-poly dino shopkeeper behind each plaza shop counter.
-- The server marks the spot on each shop model (KeeperSpecies, KeeperHeight, KeeperCFrame); this script clones the species with
-- LowPolyDinos.clone (no genes: the model's own texture), shrinks it to the keeper height and plays the authored idle loop with the
-- happy clip now and then (Shared/LowPolyClips, BD-1217; the modules are only called, never changed). Animated within KeeperRange studs,
-- still under Reduce Motion. Client presentation only: nothing is sent or stored.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Layout = require(Shared:WaitForChild("PlazaShopsLayout"))
if not Layout.enabled(Config) then return end
local LowPoly = require(Shared:WaitForChild("LowPolyDinos"))
local Clips = require(Shared:WaitForChild("LowPolyClips"))
local Theme = require(Shared:WaitForChild("UITheme"))
if not LowPoly.enabled() then return end

type Piece = {part: BasePart, base: CFrame, joint: Vector3, role: string, side: number}
type Keeper = {model: Model, root: CFrame, pieces: {Piece}, height: number, happyAt: number, seed: number}
local keepers: {Keeper} = {}
local out, add = Clips.new(), Clips.new()

local function nextHappy(now: number): number
    return now + Layout.HappyEvery + math.random() * Layout.HappyJitter
end

local function build(shop: Model)
    if shop:GetAttribute("KeeperBuilt") then return end
    local species, height, at = shop:GetAttribute("KeeperSpecies"), shop:GetAttribute("KeeperHeight"), shop:GetAttribute("KeeperCFrame")
    if typeof(species) ~= "string" or typeof(height) ~= "number" or typeof(at) ~= "CFrame" then return end
    shop:SetAttribute("KeeperBuilt", true)
    LowPoly.whenReady(species, function()
        local model = LowPoly.clone(species)
        if not model then return end
        -- clone(): feet at y = 0, centred on x / z, facing -Z (the plaza centre once placed). Shrink to the keeper height about the feet.
        local _, size = model:GetBoundingBox()
        local k = height / math.max(size.Y, .1)
        local box = model:GetBoundingBox()
        local center = Vector3.new(box.Position.X, box.Position.Y * k, box.Position.Z)
        local pieces: {Piece} = {}
        for _, item in model:GetDescendants() do
            if item:IsA("BasePart") then
                item.Anchored, item.CanCollide, item.CanQuery, item.CanTouch, item.CastShadow = true, false, false, false, false
                item.Size *= k
                local local0 = CFrame.new(item.Position * k) * item.CFrame.Rotation
                -- joint = the part's end nearest the body centre (heads turn at the neck, tails at the hip)
                local toward = center - local0.Position
                local joint = if toward.Magnitude > .01 then local0.Position + toward.Unit * math.min(toward.Magnitude, item.Size.Magnitude * .35) else local0.Position
                table.insert(pieces, {part = item, base = local0, joint = joint, role = tostring(item:GetAttribute("LPRole") or "body"),
                    side = tonumber(item:GetAttribute("LPSide")) or 1})
                item.CFrame = at * local0
            end
        end
        model.Name = "Shopkeeper"
        model.Parent = shop
        local now = os.clock()
        table.insert(keepers, {model = model, root = at, pieces = pieces, height = height, happyAt = nextHappy(now) - Layout.HappyEvery * math.random(), seed = math.random() * 4})
    end)
end

local arena = workspace:WaitForChild("BeDinoArena")
local folder = arena:WaitForChild("PlazaHub", 60)
if not folder then return end
local function watch(item: Instance)
    if item:IsA("Model") and item:GetAttribute("KeeperCFrame") ~= nil then build(item) end
end
for _, item in folder:GetChildren() do watch(item) end
folder.ChildAdded:Connect(function(item) task.defer(watch, item) end)

local acc = 0
RunService.RenderStepped:Connect(function(dt)
    acc += dt
    if acc < 1 / 30 then return end
    acc = 0
    if not Theme.MotionEnabled then return end
    local camera = workspace.CurrentCamera
    if not camera then return end
    local now = os.clock()
    for _, keeper in keepers do
        if not keeper.model.Parent then continue end
        if (camera.CFrame.Position - keeper.root.Position).Magnitude > Layout.KeeperRange then continue end
        local happyT = now - keeper.happyAt
        if happyT > Clips.length("happy") then
            keeper.happyAt = nextHappy(now)
            happyT = -1
        end
        local idleT = now + keeper.seed
        local lift = 0
        for _, p in keeper.pieces do
            Clips.sampleCycle("idle", p.role, p.side, idleT, out)
            if happyT >= 0 then
                Clips.sample("happy", p.role, p.side, happyT, add)
                out.pitch += add.pitch out.yaw += add.yaw out.roll += add.roll out.bob += add.bob
            end
            lift = out.bob * keeper.height
            local cf = p.base
            if p.role ~= "body" and p.role ~= "root" then
                local pivot = CFrame.new(p.joint)
                cf = pivot * CFrame.Angles(out.pitch, out.yaw, out.roll) * pivot:Inverse() * cf
            end
            p.part.CFrame = keeper.root * CFrame.new(0, lift, 0) * cf
        end
    end
end)
