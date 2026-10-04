--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local IslandTerrain = {}
function IslandTerrain.build()
    local terrain = workspace.Terrain
    terrain:SetMaterialColor(Enum.Material.Grass, Color3.fromRGB(96, 148, 105))
    terrain:SetMaterialColor(Enum.Material.Rock, Color3.fromRGB(114, 133, 137))
    terrain:SetMaterialColor(Enum.Material.Ground, Color3.fromRGB(151, 124, 91))
    local resolution = Config.TerrainResolution
    local extent = Config.ArenaHalfWidth + 8
    local region = Region3.new(Vector3.new(-extent,-16,-extent), Vector3.new(extent,Config.TerrainTop,extent)):ExpandToGrid(resolution)
    local size = region.Size / resolution
    local low = region.CFrame.Position - region.Size / 2
    local materials, occupancy = {}, {}
    for x = 1, size.X do
        materials[x], occupancy[x] = {}, {}
        local wx = low.X + (x-.5)*resolution
        for y = 1, size.Y do materials[x][y], occupancy[x][y] = {}, {} end
        for z = 1, size.Z do
            local wz = low.Z + (z-.5)*resolution
            local height = Layout.height(wx,wz)
            for y = 1, size.Y do
                local wy = low.Y + (y-.5)*resolution
                occupancy[x][y][z] = math.clamp((height-wy)/resolution+.5,0,1)
                materials[x][y][z] = if wy < height - 5 then Enum.Material.Rock
                    elseif height > 42 and math.noise(wx/15,wz/15,2)>.1 then Enum.Material.Rock else Enum.Material.Grass
            end
        end
        if x % 24 == 0 then task.wait() end
    end
    terrain:WriteVoxels(region,resolution,materials,occupancy)
    workspace:SetAttribute("IslandTerrainReady", true)
end
return IslandTerrain
