--!strict
local Arena = {}

local function block(parent: Instance, name: string, size: Vector3, position: Vector3, color: Color3): Part
    local part = Instance.new("Part")
    part.Name = name
    part.Size = size
    part.Position = position
    part.Color = color
    part.Material = Enum.Material.SmoothPlastic
    part.Anchored = true
    part.TopSurface = Enum.SurfaceType.Smooth
    part.BottomSurface = Enum.SurfaceType.Smooth
    part.Parent = parent
    return part
end

function Arena.build()
    local world = Instance.new("Folder")
    world.Name = "BeDinoArena"
    world.Parent = workspace
    block(world, "Ground", Vector3.new(180, 4, 180), Vector3.new(0, -2, 0), Color3.fromRGB(111, 151, 93))
    for _, x in {-92, 92} do
        block(world, "Boundary", Vector3.new(4, 20, 188), Vector3.new(x, 8, 0), Color3.fromRGB(94, 113, 82))
    end
    for _, z in {-92, 92} do
        block(world, "Boundary", Vector3.new(180, 20, 4), Vector3.new(0, 8, z), Color3.fromRGB(94, 113, 82))
    end
    local spawn = Instance.new("SpawnLocation")
    spawn.Name = "PrototypeSpawn"
    spawn.Size = Vector3.new(14, 1, 14)
    spawn.Position = Vector3.new(0, 0.5, 30)
    spawn.Anchored = true
    spawn.Neutral = true
    spawn.Duration = 0
    spawn.Color = Color3.fromRGB(236, 220, 169)
    spawn.Parent = world

    -- A lane with varying obstacle widths for the fixed-collider experiment.
    for i = 1, 5 do
        block(world, "Rock", Vector3.new(4 + i, 2 + i, 6),
            Vector3.new(-50 + i * 17, (2 + i) / 2, -30), Color3.fromRGB(126, 128, 115))
    end
    local ramp = block(world, "SlopeTest", Vector3.new(16, 2, 24), Vector3.new(-48, 3, 10), Color3.fromRGB(178, 157, 120))
    ramp.CFrame = CFrame.new(-48, 3, 10) * CFrame.Angles(math.rad(12), 0, 0)

    local pads = {}
    for i, scale in {1, 2, 4} do
        local pad = block(world, "Size" .. scale, Vector3.new(12, 0.4, 12),
            Vector3.new((i - 2) * 24, 0.2, -5), Color3.fromRGB(220, 180 - i * 18, 90))
        local gui = Instance.new("BillboardGui")
        gui.Size = UDim2.fromOffset(140, 42)
        gui.StudsOffset = Vector3.new(0, 3, 0)
        gui.AlwaysOnTop = true
        gui.MaxDistance = 120
        gui.Parent = pad
        local label = Instance.new("TextLabel")
        label.Size = UDim2.fromScale(1, 1)
        label.BackgroundTransparency = 1
        label.Text = tostring(scale) .. "× SIZE"
        label.Font = Enum.Font.GothamBold
        label.TextSize = 22
        label.TextColor3 = Color3.fromRGB(255, 255, 235)
        label.TextStrokeTransparency = 0.4
        label.Parent = gui
        table.insert(pads, {part = pad, scale = scale})
    end
    return pads
end

return Arena
