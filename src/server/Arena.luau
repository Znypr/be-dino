--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Resources = require(ReplicatedStorage.Shared.ResourceModels)
local Arena = {}
local function part(parent: Instance, name: string, size: Vector3, position: Vector3, color: Color3, material: Enum.Material, solid: boolean): Part
    local p = Instance.new("Part")
    p.Name, p.Size, p.Position, p.Color, p.Material = name, size, position, color, material
    p.Anchored, p.CanCollide, p.CanTouch, p.CanQuery = true, solid, false, solid
    p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
    p.Parent = parent
    return p
end
local function imported(parent: Instance, id: string, position: Vector3, scale: number, yaw: number): boolean
    local model = Resources.clone(id)
    if not model then return false end
    model:ScaleTo(scale)
    model:PivotTo(CFrame.new(position) * CFrame.Angles(0, yaw, 0))
    for _, item in model:GetDescendants() do if item:IsA("BasePart") then item.Anchored = true end end
    model.Parent = parent
    return true
end
local function rock(parent: Instance, position: Vector3, scale: number, yaw: number)
    local collider = part(parent, "RockCollider", Vector3.new(4.7, 2.8, 4.0) * scale,
        position + Vector3.new(0, 1.4 * scale, 0), Color3.fromRGB(113, 133, 139), Enum.Material.Slate, true)
    collider.CFrame = CFrame.new(collider.Position) * CFrame.Angles(0, yaw, 0)
    if imported(parent, "rock", position, scale, yaw) then collider.Transparency = 1
    else
        collider.Shape = Enum.PartType.Ball
        local chip = part(parent, "RockChip", Vector3.new(2.6, 1.6, 2.6) * scale,
            position + Vector3.new(2, 0.8, 0.8) * scale, Color3.fromRGB(83, 109, 116), Enum.Material.Slate, true)
        chip.Shape = Enum.PartType.Ball
    end
end
local function tree(parent: Instance, position: Vector3, scale: number, yaw: number)
    local trunk = part(parent, "TreeCollider", Vector3.new(1.6, 7, 1.6) * scale,
        position + Vector3.new(0, 3.5 * scale, 0), Color3.fromRGB(119, 83, 65), Enum.Material.Wood, true)
    if imported(parent, "tree", position, scale, yaw) then trunk.Transparency = 1
    else
        trunk.Shape = Enum.PartType.Cylinder
        trunk.CFrame = CFrame.new(trunk.Position) * CFrame.Angles(0, yaw, math.pi / 2)
        for _, offset in {Vector3.new(0, 9, 0), Vector3.new(2.7, 8.5, 0.4), Vector3.new(-2.3, 8.9, -0.8)} do
            local crown = part(parent, "Canopy", Vector3.new(5.5, 3.5, 5.5) * scale,
                position + offset * scale, Color3.fromRGB(64, 144, 112), Enum.Material.SmoothPlastic, false)
            crown.Shape = Enum.PartType.Ball
        end
    end
end
local function fern(parent: Instance, position: Vector3, scale: number, yaw: number)
    if imported(parent, "fern", position, scale, yaw) then return end
    for i = 1, 7 do
        local angle = yaw + i * math.pi * 2 / 7
        local leaf = part(parent, "FernLeaf", Vector3.new(0.45, 0.16, 2.0) * scale,
            position + Vector3.new(math.sin(angle) * .6, .6, math.cos(angle) * .6) * scale,
            Color3.fromRGB(106, 180, 125), Enum.Material.SmoothPlastic, false)
        leaf.Shape = Enum.PartType.Ball
        leaf.CFrame = CFrame.new(leaf.Position) * CFrame.Angles(-0.28, angle, 0)
    end
end
function Arena.build()
    local old = workspace:FindFirstChild("BeDinoArena")
    if old then old:Destroy() end
    local world = Instance.new("Folder")
    world.Name, world.Parent = "BeDinoArena", workspace
    local extent = Config.ArenaHalfWidth
    part(world, "Ground", Vector3.new(extent * 2, 4, extent * 2), Vector3.new(0, -2, 0),
        Color3.fromRGB(100, 149, 112), Enum.Material.Grass, true)
    -- Simple hidden boundary; irregular rock silhouettes dress it instead of a block wall.
    for _, x in {-extent - 2, extent + 2} do
        local boundary = part(world, "Boundary", Vector3.new(4, 24, extent * 2 + 8), Vector3.new(x, 10, 0),
            Color3.fromRGB(81, 106, 116), Enum.Material.Rock, true)
        boundary.Transparency = 1
    end
    for _, z in {-extent - 2, extent + 2} do
        local boundary = part(world, "Boundary", Vector3.new(extent * 2, 24, 4), Vector3.new(0, 10, z),
            Color3.fromRGB(81, 106, 116), Enum.Material.Rock, true)
        boundary.Transparency = 1
    end
    local random = Random.new(1404)
    for side = 1, 4 do
        for i = 0, 11 do
            local t = -extent + i * extent * 2 / 11
            local position = if side == 1 then Vector3.new(t, 0, -extent - 5)
                elseif side == 2 then Vector3.new(t, 0, extent + 5)
                elseif side == 3 then Vector3.new(-extent - 5, 0, t) else Vector3.new(extent + 5, 0, t)
            rock(world, position, random:NextNumber(2.4, 3.7), random:NextNumber(0, math.pi * 2))
        end
    end
    local spawn = Instance.new("SpawnLocation")
    spawn.Name = "PrototypeSpawn"
    spawn.Size, spawn.Position = Vector3.new(12, 1, 12), Vector3.new(0, .5, 30)
    spawn.Anchored, spawn.Neutral, spawn.Duration, spawn.Transparency = true, true, 0, 1
    spawn.CanCollide, spawn.CanQuery = false, false
    spawn.Parent = world
    -- Authored landmark centers; within each, offset props avoid a uniform grid.
    for _, center in {Vector3.new(-53,0,44), Vector3.new(51,0,-45), Vector3.new(-49,0,-43), Vector3.new(54,0,42)} do
        for i = 1, 4 do
            local angle = i * 1.65 + random:NextNumber(-.4, .4)
            local position = center + Vector3.new(math.cos(angle) * 12, 0, math.sin(angle) * 10)
            tree(world, position, random:NextNumber(.85, 1.25), angle)
            fern(world, position + Vector3.new(3.5,0,2.5), random:NextNumber(.7,1.1), angle)
        end
        for i = 1, 3 do
            rock(world, center + Vector3.new(random:NextNumber(-7,7),0,random:NextNumber(-6,6)), random:NextNumber(.6,1.1), i)
        end
    end
    -- Scattered smaller vegetation connects landmarks while the central chase lane stays open.
    for i = 1, 26 do
        local angle, radius = i * 2.4, random:NextNumber(32,78)
        local position = Vector3.new(math.cos(angle)*radius,0,math.sin(angle)*radius)
        if (position - Vector3.new(0,0,30)).Magnitude > 14 then fern(world, position, .8, angle) end
    end
    workspace:SetAttribute("ArenaArtMode", if ReplicatedStorage.Resources:FindFirstChild("tree") then "Resource meshes" else "Import resources/models for mesh art")
end
return Arena
