--!strict
-- BD-281: writes the Cave hub shell (docs/104 s3) as Terrain voxels from CaveTerrainRules (pure, tested offline by
-- tools/verify_cave_terrain.py). Same chunked, yielding pattern as IslandTerrain: one WriteVoxels per ChunkSlices x slices and a
-- task.wait() every YieldSlices slices, so no frame hitch. Only ever called from Arena's cave branch (Config.CaveHub on);
-- it writes terrain only (no props, no parts). With CaveHubLayout.Baked the owner's hand-smoothed shell in the place file is kept.
local CaveHubLayout = require(game:GetService("ReplicatedStorage").Shared.CaveHubLayout)
local Rules = require(game:GetService("ReplicatedStorage").Shared.CaveTerrainRules)
local CaveTerrain = {}

function CaveTerrain.build()
    local terrain = workspace.Terrain
    if CaveHubLayout.Baked then
        workspace:SetAttribute("CaveTerrainBaked", true)
        workspace:SetAttribute("CaveTerrainReady", true)
        return
    end
    for name, c in Rules.Colors do
        terrain:SetMaterialColor((Enum.Material :: any)[name], Color3.fromRGB(c[1], c[2], c[3]))
    end
    local enums: {[string]: Enum.Material} = {}
    for _, name in Rules.Materials do enums[name] = (Enum.Material :: any)[name] end
    local startedAt = os.clock()
    local res = Rules.Res
    local plan = Rules.plan()
    local nz, ny = plan.grid.nz, plan.grid.ny
    local solid = 0
    for _, chunk in plan.chunks do
        local region = Region3.new(Vector3.new(chunk.minX, Rules.YMin, Rules.ZMin), Vector3.new(chunk.maxX, Rules.YMax, Rules.ZMax))
        local materials, occupancy = {}, {}
        for x = 1, chunk.slices do
            materials[x], occupancy[x] = {}, {}
            local wx = chunk.minX + (x - .5) * res
            for y = 1, ny do materials[x][y], occupancy[x][y] = {}, {} end
            for z = 1, nz do
                local col = Rules.column(wx, Rules.ZMin + (z - .5) * res)
                for y = 1, ny do
                    local name, occ = Rules.cellAt(col, Rules.YMin + (y - .5) * res)
                    materials[x][y][z] = enums[name]
                    occupancy[x][y][z] = occ
                    if occ > 0 then solid += 1 end
                end
            end
            if x % Rules.YieldSlices == 0 then task.wait() end
        end
        terrain:WriteVoxels(region, res, materials, occupancy)
        task.wait()
    end
    workspace:SetAttribute("CaveTerrainBuildSeconds", math.floor((os.clock() - startedAt) * 10) / 10)
    workspace:SetAttribute("CaveTerrainVoxels", solid)
    workspace:SetAttribute("CaveTerrainReady", true)
end

return CaveTerrain
