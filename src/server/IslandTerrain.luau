--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local BiomeMap = require(ReplicatedStorage.Shared.BiomeMap)
local Biome = require(ReplicatedStorage.Shared.BiomePlacement)
local IslandTerrain = {}
-- World v2: the surface material per column comes from the sub-biome map (BiomeMap) dithered with multi-octave noise, so a
-- single grass material no longer tiles flat across the map: Grass/LeafyGrass/Mud/Ground/Sand/Sandstone/Slate/Basalt mix in
-- irregular patches with each biome's own colours, and the borders blend instead of switching on a line.
local STRIP = 32 -- voxel columns written per WriteVoxels call (bounds the Lua table memory on the 2.5x larger island)
local function smooth(x: number, z: number, scale: number, offset: number): number
    return math.noise(x / scale, z / scale, offset)
end
function IslandTerrain.build()
    local terrain = workspace.Terrain
    for name, c in BiomeMap.Colors do
        terrain:SetMaterialColor((Enum.Material :: any)[name], Color3.fromRGB(c[1], c[2], c[3]))
    end
    -- Roblox's own grass decoration adds real 3D tufts on Grass terrain for free (no parts); not scriptable everywhere.
    pcall(function() (terrain :: any).Decoration = true end)
    local resolution = Config.TerrainResolution
    local extent = Config.ArenaHalfWidth + 8
    local seed = Config.WorldArtSeed
    local o = .5 + (seed * .137) % 47
    local fullLow = -extent
    local columns = math.ceil(2 * extent / resolution)
    local startedAt = os.clock()
    local biomeCells = 0
    for strip = 0, math.ceil(columns / STRIP) - 1 do
        local minX = fullLow + strip * STRIP * resolution
        local maxX = math.min(extent, minX + STRIP * resolution)
        local region = Region3.new(Vector3.new(minX, -16, -extent), Vector3.new(maxX, Config.TerrainTop, extent)):ExpandToGrid(resolution)
        local size = region.Size / resolution
        local low = region.CFrame.Position - region.Size / 2
        local materials, occupancy = {}, {}
        for x = 1, size.X do
            materials[x], occupancy[x] = {}, {}
            local wx = low.X + (x - .5) * resolution
            for y = 1, size.Y do materials[x][y], occupancy[x][y] = {}, {} end
            for z = 1, size.Z do
                local wz = low.Z + (z - .5) * resolution
                local height = Layout.height(wx, wz)
                local gx = (Layout.height(wx + 3, wz) - Layout.height(wx - 3, wz)) / 6
                local gz = (Layout.height(wx, wz + 3) - Layout.height(wx, wz - 3)) / 6
                local slope = math.sqrt(gx * gx + gz * gz)
                local weights, dominant = BiomeMap.weights(wx, wz, height, seed)
                -- Band noise: dapples the biome's own materials; pick noise: dithers neighbouring biomes (never a straight line).
                local band = math.clamp(.5 + .85 * (smooth(wx, wz, 15, o + 2) * .65 + smooth(wx, wz, 5.3, o + 4) * .35), 0, 1)
                local white = Biome.hash(seed, math.floor(wx / resolution), math.floor(wz / resolution), 3)
                local pickRoll = .62 * white + .38 * math.clamp(.5 + .75 * smooth(wx, wz, 26, o + 7), 0, 1)
                local name = BiomeMap.surface(weights, height, slope, pickRoll, band, smooth(wx, wz, 21, o + 11))
                local wet = Layout.poolProximity(wx, wz)
                if wet > .55 and height < 3 then name = if weights.marsh > .35 then "Mud" else "Sand" end
                local surface = (Enum.Material :: any)[name] :: Enum.Material
                local deep = (Enum.Material :: any)[BiomeMap.Rock[dominant]] :: Enum.Material
                biomeCells += 1
                for y = 1, size.Y do
                    local wy = low.Y + (y - .5) * resolution
                    occupancy[x][y][z] = math.clamp((height - wy) / resolution + .5, 0, 1)
                    materials[x][y][z] = if wy < height - 6 then deep else surface
                end
            end
            if x % 8 == 0 then task.wait() end
        end
        terrain:WriteVoxels(region, resolution, materials, occupancy)
        task.wait()
    end
    workspace:SetAttribute("IslandTerrainBuildSeconds", math.floor((os.clock() - startedAt) * 10) / 10)
    workspace:SetAttribute("IslandTerrainReady", true)
end
return IslandTerrain
