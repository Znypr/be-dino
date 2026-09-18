--!strict
local Arena = {}

local function part(
    parent: Instance,
    name: string,
    size: Vector3,
    position: Vector3,
    color: Color3,
    material: Enum.Material?,
    canCollide: boolean?
): Part
    local p = Instance.new("Part")
    p.Name = name
    p.Size = size
    p.Position = position
    p.Color = color
    p.Material = material or Enum.Material.SmoothPlastic
    p.Anchored = true
    p.CanCollide = canCollide ~= false
    p.TopSurface = Enum.SurfaceType.Smooth
    p.BottomSurface = Enum.SurfaceType.Smooth
    p.Parent = parent
    return p
end

local function decorativeRock(parent: Instance, position: Vector3, scale: number)
    local rock = part(parent, "DecorRock", Vector3.new(3.8, 2.8, 4.4) * scale, position,
        Color3.fromRGB(128, 122, 105), Enum.Material.Slate, false)
    rock.Shape = Enum.PartType.Ball
end

local function bush(parent: Instance, position: Vector3, scale: number)
    for i = 1, 3 do
        local offset = Vector3.new((i - 2) * 1.3 * scale, 0, if i == 2 then 0.55 * scale else 0)
        local leaf = part(parent, "Bush", Vector3.new(2.5, 2.0, 2.5) * scale,
            position + offset, Color3.fromRGB(80, 137, 76), Enum.Material.SmoothPlastic, false)
        leaf.Shape = Enum.PartType.Ball
    end
end

local function tree(parent: Instance, position: Vector3, scale: number)
    local trunk = part(parent, "TreeTrunk", Vector3.new(1.6, 5.8, 1.6) * scale,
        position + Vector3.new(0, 2.9 * scale, 0),
        Color3.fromRGB(119, 86, 58), Enum.Material.Wood, false)
    trunk.Shape = Enum.PartType.Cylinder
    trunk.CFrame = CFrame.new(trunk.Position) * CFrame.Angles(0, 0, math.rad(90))
    for _, offset in {
        Vector3.new(0, 6.0, 0),
        Vector3.new(1.4, 5.5, 0.4),
        Vector3.new(-1.3, 5.4, -0.5),
    } do
        local crown = part(parent, "TreeCrown", Vector3.new(4.3, 3.5, 4.3) * scale,
            position + offset * scale, Color3.fromRGB(73, 128, 72),
            Enum.Material.SmoothPlastic, false)
        crown.Shape = Enum.PartType.Ball
    end
end

function Arena.build()
    local world = Instance.new("Folder")
    world.Name = "BeDinoArena"
    world.Parent = workspace

    part(world, "Ground", Vector3.new(180, 4, 180), Vector3.new(0, -2, 0),
        Color3.fromRGB(120, 158, 91), Enum.Material.Grass, true)

    -- Collision boundary stays simple; visible surface is dressed as warm stone.
    for _, x in {-92, 92} do
        part(world, "Boundary", Vector3.new(4, 20, 188), Vector3.new(x, 8, 0),
            Color3.fromRGB(105, 105, 87), Enum.Material.Rock, true)
    end
    for _, z in {-92, 92} do
        part(world, "Boundary", Vector3.new(180, 20, 4), Vector3.new(0, 8, z),
            Color3.fromRGB(105, 105, 87), Enum.Material.Rock, true)
    end

    local spawn = Instance.new("SpawnLocation")
    spawn.Name = "PrototypeSpawn"
    spawn.Size = Vector3.new(16, 1, 16)
    spawn.Position = Vector3.new(0, 0.5, 30)
    spawn.Anchored = true
    spawn.Neutral = true
    spawn.Duration = 0
    spawn.Color = Color3.fromRGB(230, 209, 142)
    spawn.Material = Enum.Material.Sand
    spawn.Parent = world

    local nest = Instance.new("Folder")
    nest.Name = "StarterNest"
    nest.Parent = world
    for i = 1, 10 do
        local angle = math.rad(i * 36)
        local stone = part(nest, "NestStone", Vector3.new(2.8, 1.0, 1.6),
            Vector3.new(math.cos(angle) * 8, 0.55, 30 + math.sin(angle) * 8),
            Color3.fromRGB(151, 126, 89), Enum.Material.Sandstone, false)
        stone.CFrame = CFrame.new(stone.Position) * CFrame.Angles(0, -angle, math.rad(8))
    end
    local egg = part(nest, "NestEgg", Vector3.new(2.2, 3.0, 2.2), Vector3.new(0, 1.6, 30),
        Color3.fromRGB(238, 226, 188), Enum.Material.SmoothPlastic, false)
    egg.Shape = Enum.PartType.Ball

    -- Fixed-collider obstacle lane retained for gameplay testing, now styled as natural stone.
    for i = 1, 5 do
        local rock = part(world, "Rock", Vector3.new(4 + i, 2 + i, 6),
            Vector3.new(-50 + i * 17, (2 + i) / 2, -30),
            Color3.fromRGB(130, 127, 110), Enum.Material.Slate, true)
        rock.Orientation = Vector3.new(0, i * 11, if i % 2 == 0 then 4 else -5)
    end

    local ramp = part(world, "SlopeTest", Vector3.new(16, 2, 24), Vector3.new(-48, 3, 10),
        Color3.fromRGB(177, 152, 111), Enum.Material.Sandstone, true)
    ramp.CFrame = CFrame.new(-48, 3, 10) * CFrame.Angles(math.rad(12), 0, 0)

    -- Decorative kit. All pieces are non-colliding so they cannot create traps.
    for _, spec in {
        {Vector3.new(-72, 1.4, 58), 1.1},
        {Vector3.new(68, 1.2, 60), 0.9},
        {Vector3.new(-68, 1.3, -62), 1.0},
        {Vector3.new(70, 1.5, -58), 1.2},
        {Vector3.new(36, 1.0, 55), 0.75},
        {Vector3.new(-30, 1.0, 62), 0.8},
    } do
        decorativeRock(world, spec[1], spec[2])
    end

    for _, spec in {
        {Vector3.new(-65, 1.0, 42), 1.0},
        {Vector3.new(62, 1.0, 38), 0.9},
        {Vector3.new(-57, 1.0, -48), 0.9},
        {Vector3.new(55, 1.0, -44), 1.1},
        {Vector3.new(28, 1.0, -62), 0.75},
    } do
        bush(world, spec[1], spec[2])
    end

    for _, spec in {
        {Vector3.new(-74, 0, 20), 0.95},
        {Vector3.new(73, 0, 16), 0.9},
        {Vector3.new(-70, 0, -18), 0.8},
        {Vector3.new(72, 0, -22), 0.85},
    } do
        tree(world, spec[1], spec[2])
    end

    local bones = Instance.new("Folder")
    bones.Name = "BonePatch"
    bones.Parent = world
    for i = 1, 4 do
        local bone = part(bones, "Bone", Vector3.new(0.55, 0.55, 3.4),
            Vector3.new(46 + i * 1.3, 0.5, 66 + (i % 2) * 1.3),
            Color3.fromRGB(225, 215, 181), Enum.Material.SmoothPlastic, false)
        bone.CFrame = CFrame.new(bone.Position) * CFrame.Angles(0, math.rad(24 * i), 0)
    end
end

return Arena
