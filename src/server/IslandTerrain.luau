--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local BiomeMap = require(ReplicatedStorage.Shared.BiomeMap)
local Biome = require(ReplicatedStorage.Shared.BiomePlacement)
local Sea = require(ReplicatedStorage.Shared.WorldSea)
local Toon = require(ReplicatedStorage.Shared.WorldToon)
local Fill = require(ReplicatedStorage.Shared.WorldFill) -- BD-1245
local Patches = require(ReplicatedStorage.Shared.GroundPatches) -- BD-1320
local IslandTerrain = {}
-- World v2: the surface material per column comes from the sub-biome map (BiomeMap) dithered with multi-octave noise, so a
-- single grass material no longer tiles flat across the map: Grass/LeafyGrass/Mud/Ground/Sand/Sandstone/Slate/Basalt mix in
-- irregular patches with each biome's own colours, and the borders blend instead of switching on a line.
local STRIP = 32 -- voxel columns written per WriteVoxels call (bounds the Lua table memory on the 2.5x larger island)
local function smooth(x: number, z: number, scale: number, offset: number): number
    return math.noise(x / scale, z / scale, offset)
end
-- BD-1220 (Config.RealSeaEnabled, Shared/WorldSea): terrain water past the island square out to WorldSea.Radius, so the sea reaches the
-- fog instead of ending on a square plate. Blocks that touch the home's terrain box (WorldSea.HomeBox) are written first, BEFORE the
-- beforeReady callback, so the home shell always overwrites the sea there; the rest runs after IslandTerrainReady (nothing waits for it).
-- Far blocks share one flat column. early = true: only the home-box blocks; false: every other block.
local function farSea(V3: any, half: number, resolution: number, early: boolean)
    local startedAt = os.clock()
    local flatM, flatO = Sea.column(Sea.SeaFloor, resolution)
    local cells, n = Sea.Tile / resolution, 0
    local function block(fill: (number, number) -> ({string}, {number}), x0: number, z0: number)
        local materials, occupancy = {}, {}
        for x = 1, cells do
            materials[x], occupancy[x] = {}, {}
            for y = 1, #flatM do materials[x][y], occupancy[x][y] = {}, {} end
            for z = 1, cells do
                local m, o = fill(x0 + (x - .5) * resolution, z0 + (z - .5) * resolution)
                for y = 1, #m do
                    materials[x][y][z] = (Enum.Material :: any)[m[y]]
                    occupancy[x][y][z] = o[y]
                end
            end
        end
        local region = Region3.new(Vector3.new(x0, Sea.FloorLow, z0), Vector3.new(x0 + Sea.Tile, 0, z0 + Sea.Tile))
        workspace.Terrain:WriteVoxels(region, resolution, materials, occupancy)
    end
    local flat = function(_x: number, _z: number) return flatM, flatO end
    local shaped = function(x: number, z: number) return Sea.column(V3.height(x, z), resolution) end
    for _, t in Sea.tiles(V3.CenterX, V3.CenterZ, half) do
        if Sea.overlaps(t, Sea.HomeBox) ~= early then continue end
        -- the nearest corner decides: blocks touching the shelf by the island get their real floor per column
        local nx = math.clamp(V3.CenterX, t[1], t[1] + Sea.Tile) - V3.CenterX
        local nz = math.clamp(V3.CenterZ, t[2], t[2] + Sea.Tile) - V3.CenterZ
        block(if nx * nx + nz * nz < Sea.FlatFrom * Sea.FlatFrom then shaped else flat, t[1], t[2])
        n += 1
        if not early and n % 4 == 0 then task.wait() end
    end
    if early then return end
    workspace:SetAttribute("WorldSeaBlocks", n)
    workspace:SetAttribute("WorldSeaBuildSeconds", math.floor((os.clock() - startedAt) * 10) / 10)
end
-- beforeReady (BD-281): optional extra terrain work (the cave shell, flag on only) that must finish before IslandTerrainReady.
function IslandTerrain.build(beforeReady: (() -> ())?)
    local terrain = workspace.Terrain
    for name, c in BiomeMap.Colors do
        terrain:SetMaterialColor((Enum.Material :: any)[name], Color3.fromRGB(c[1], c[2], c[3]))
    end
    -- BD-1209: the redesigned island (Config.WorldV3Enabled, Layout.V3) paints the plaza, paths, beach and sea floor itself and fills the sea.
    local V3 = if (Layout :: any).V3 then BiomeMap.V3 else nil
    if V3 then
        for name, c in V3.Colors do
            terrain:SetMaterialColor((Enum.Material :: any)[name], Color3.fromRGB(c[1], c[2], c[3]))
        end
        pcall(function() terrain.WaterColor, terrain.WaterTransparency, terrain.WaterWaveSize = Color3.fromRGB(64, 182, 214), .35, .08 end)
    end
    -- BD-1223 (Config.ToonWorldEnabled, Shared/WorldToon): the place carries one flat MaterialVariant per island material (authored at build
    -- time, unbound: resources/world-materials.rbxmx); with the flag on they become the overrides, so the ground shows only its flat toon
    -- colour (no photo grass, sand or rock). The Enum materials stay the same for footsteps, food and placement.
    if V3 and Toon.enabled(Config) then
        local MaterialService = game:GetService("MaterialService")
        local bound = 0
        for _, name in Toon.materials() do
            local c = Toon.Palette[name]
            local material = (Enum.Material :: any)[name] :: Enum.Material
            terrain:SetMaterialColor(material, Color3.fromRGB(c[1], c[2], c[3]))
            if MaterialService:FindFirstChild(Toon.VariantPrefix .. name) then
                local ok = pcall(function() MaterialService:SetBaseMaterialOverride(material, Toon.VariantPrefix .. name) end)
                if ok then bound += 1 end
            end
        end
        workspace:SetAttribute("WorldToonVariants", bound)
    end
    -- Roblox's own grass decoration adds real 3D tufts on Grass terrain for free (no parts); not scriptable everywhere.
    pcall(function() (terrain :: any).Decoration = true end)
    local resolution = Config.TerrainResolution
    local extent = Config.ArenaHalfWidth + 8
    local realSea = V3 ~= nil and Sea.enabled(Config)
    local fillGround = V3 ~= nil and Fill.groundEnabled(Config)
    local floorLow = if realSea then Sea.FloorLow else -16
    local seed = Config.WorldArtSeed
    local o = .5 + (seed * .137) % 47
    local fullLow = -extent
    local columns = math.ceil(2 * extent / resolution)
    local startedAt = os.clock()
    local biomeCells = 0
    for strip = 0, math.ceil(columns / STRIP) - 1 do
        local minX = fullLow + strip * STRIP * resolution
        local maxX = math.min(extent, minX + STRIP * resolution)
        local region = Region3.new(Vector3.new(minX, floorLow, -extent), Vector3.new(maxX, Config.TerrainTop, extent)):ExpandToGrid(resolution)
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
                if V3 then
                    local fixed = V3.surface(wx, wz, height)
                    -- BD-1245 (Config.GroundDetailEnabled): grass lip along the paths, soft darker grass and earth patches (0 parts)
                    -- BD-1320 (same flag): worn soil at path junctions, grove floors, beach fingers and slope rock first (docs/251 s5)
                    if not fixed and fillGround then fixed = Patches.surface(V3, wx, wz, height, slope, name) or Fill.surface(V3, wx, wz, height, name) end
                    name = fixed or name
                end
                local surface = (Enum.Material :: any)[name] :: Enum.Material
                local deep = (Enum.Material :: any)[BiomeMap.Rock[dominant]] :: Enum.Material
                biomeCells += 1
                for y = 1, size.Y do
                    local wy = low.Y + (y - .5) * resolution
                    local solid = math.clamp((height - wy) / resolution + .5, 0, 1)
                    if V3 and solid < .5 and wy - resolution / 2 < V3.SeaLevel then
                        -- sea water above the shelf (the top cell holds only the part under sea level)
                        occupancy[x][y][z] = math.clamp((V3.SeaLevel - (wy - resolution / 2)) / resolution, 0, 1)
                        materials[x][y][z] = Enum.Material.Water
                    else
                        occupancy[x][y][z] = solid
                        materials[x][y][z] = if wy < height - 6 then deep else surface
                    end
                end
            end
            if x % 8 == 0 then task.wait() end
        end
        terrain:WriteVoxels(region, resolution, materials, occupancy)
        task.wait()
    end
    workspace:SetAttribute("IslandTerrainBuildSeconds", math.floor((os.clock() - startedAt) * 10) / 10)
    if realSea then farSea(V3, extent, resolution, true) end -- BD-1220: the sea under the home box first, then the beforeReady shell over it
    if beforeReady then beforeReady() end
    workspace:SetAttribute("IslandTerrainReady", true)
    if realSea then task.spawn(farSea, V3, extent, resolution, false) end
end
return IslandTerrain
