--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Resources = require(ReplicatedStorage.Shared.ResourceModels)
local Terrain = require(script.Parent.IslandTerrain)
local CaveTerrain = require(script.Parent.CaveTerrain)
local CaveLighting = require(script.Parent.CaveLighting)
local CaveProps = require(script.Parent.CaveProps)
local CaveShowOff = require(script.Parent.CaveShowOff)
local CaveLavaFx = require(script.Parent.CaveLavaFx)
local Layout = require(ReplicatedStorage.Shared.IslandLayout)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)
local CaveHubLayout = require(ReplicatedStorage.Shared.CaveHubLayout)
local Biome = require(ReplicatedStorage.Shared.BiomePlacement)
local BiomeMap = require(ReplicatedStorage.Shared.BiomeMap)
local KitData = require(ReplicatedStorage.Shared.WorldKitData)
local KitMeshes = require(ReplicatedStorage.Shared.WorldKitMeshAssets)
local Generated = require(ReplicatedStorage.Shared.WorldGeneratedMeshes)
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
local function group(parent: Instance, id: string, position: Vector3, scale: number, yaw: number): Model
    local model = Instance.new("Model")
    model.Name = id .. "Prop"
    model:SetAttribute("ResourceId", id)
    model:SetAttribute("SourcePosition", position)
    model:SetAttribute("SourceScale", scale)
    model:SetAttribute("SourceYaw", yaw)
    model.Parent = parent
    return model
end
local function rock(parent: Instance, position: Vector3, scale: number, yaw: number)
    parent = group(parent, "rock", position, scale, yaw)
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
    parent = group(parent, "tree", position, scale, yaw)
    local trunk = part(parent, "TreeCollider", Vector3.new(1.6, 7, 1.6) * scale,
        position + Vector3.new(0, 3.5 * scale, 0), Color3.fromRGB(119, 83, 65), Enum.Material.Wood, true)
    if imported(parent, "tree", position, scale, yaw) then trunk.Transparency = 1
    else
        -- Roblox cylinders run along local X; rotate the long X dimension upright.
        trunk.Size = Vector3.new(7, 1.6, 1.6) * scale
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
    parent = group(parent, "fern", position, scale, yaw)
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
-- BD-206: Roblox-generated MeshPart for a kit id (one part). Scaled uniformly to fit inside the kit id's extent box so the
-- invisible kit colliders still match, pivot = bottom centre. nil (flag off, id not mapped, mesh failed to load) means the
-- caller keeps the current kit model, so a failed asset never leaves a hole.
local generatedCache: {[string]: Model} = {}
local function generatedProp(id: string, biome: string, roll: number): Model?
    if not Config.WorldGeneratedMeshes then return nil end
    local key = Generated.visualFor(id, biome, roll)
    local folder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local template = if key and folder then folder:FindFirstChild(key) else nil
    if not template or not template:IsA("MeshPart") then return nil end
    local cacheKey = key .. "|" .. id
    if not generatedCache[cacheKey] then
        local extent, size = KitData[id].extent, template.Size
        local fit = math.min(extent[1] / size.X, extent[2] / size.Y, extent[3] / size.Z)
        if KitData[id].kind == "tree" then fit = math.min(extent[2] / size.Y, math.max(extent[1], extent[3]) * 1.15 / math.max(size.X, size.Z)) end
        local mesh = template:Clone()
        mesh.Size = size * fit
        mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless = true, false, false, false, true
        mesh.CFrame = CFrame.new(0, mesh.Size.Y / 2, 0)
        -- BD-409: a Model with a PrimaryPart pivots on THAT part's PivotOffset (WorldPivot is ignored), which defaults to the mesh
        -- centre: every generated prop stood half-buried. Put the pivot at the bottom centre (ScaleTo scales the offset with it).
        mesh.PivotOffset = CFrame.new(0, -mesh.Size.Y / 2, 0)
        local model = Instance.new("Model")
        mesh.Parent = model
        model.PrimaryPart = mesh
        model.WorldPivot = CFrame.new()
        model.Name = id
        model:SetAttribute("GeneratedMesh", key)
        generatedCache[cacheKey] = model
    end
    workspace:SetAttribute("WorldGeneratedProps", (workspace:GetAttribute("WorldGeneratedProps") or 0) + 1)
    return generatedCache[cacheKey]:Clone()
end
-- One kit prop = the uploaded MeshPart model (1 part) plus simplified invisible box colliders scaled with it.
local function kitProp(folder: Instance, id: string, pivot: CFrame, scale: number, biome: string?, roll: number?, made: Model?): boolean
    local model = made or generatedProp(id, biome or "meadow", roll or .5) or Resources.clone(id)
    if model then
        if not made then model:ScaleTo(scale) end
        model:PivotTo(pivot)
        model.Parent = folder
    end
    for _, c in KitData[id].colliders do
        local collider = part(folder, id .. "Collider", Vector3.new(c[4], c[5], c[6]) * scale, Vector3.zero,
            Color3.fromRGB(113, 133, 139), Enum.Material.Slate, true)
        collider.CFrame = pivot * CFrame.new(Vector3.new(c[1], c[2], c[3]) * scale) * CFrame.Angles(0, c[7], 0)
        collider.Transparency = 1
    end
    return model ~= nil
end
-- BD-049 BiomeKit dressing (world v2): sub-biome driven kit props, giants, fallen logs, understory and ground cover.
local function biomeKit(parent: Instance)
    local folder = Instance.new("Folder")
    folder.Name, folder.Parent = "WorldKit", parent
    -- Only ids whose uploaded MeshPart really loaded count as one part; the rest cost their native fallback.
    local meshes: {[string]: boolean} = {}
    local overrides = ReplicatedStorage:FindFirstChild("ResourceOverrides")
    for id in KitMeshes do
        local template = if overrides then overrides:FindFirstChild(id) else nil
        if template and template:IsA("MeshPart") then meshes[id] = true end
    end
    local placed = Biome.generate({seed = Config.WorldArtSeed, density = Config.WorldArtDensity,
        extent = Config.ArenaHalfWidth, height = Layout.height, kit = KitData, meshes = meshes, map = BiomeMap, layout = Layout})
    local missing = 0
    local counts = {tree = 0, giant = 0, log = 0, rock = 0, shrub = 0, groundcover = 0, landmark = 0}
    -- BD-395: trees, giants and shrubs rest ON the real voxel terrain: five rays (centre + around the trunk) from above, the
    -- bottom (pivot) goes to the highest hit + 0.2 (BiomePlacement.Ground). A missed ray keeps the analytic layout height.
    local rayParams = RaycastParams.new()
    rayParams.FilterType, rayParams.FilterDescendantsInstances = Enum.RaycastFilterType.Include, {workspace.Terrain}
    local Ground, rayMoved = Biome.Ground, 0
    for i, p in placed do
        counts[p.layer] += 1
        local data = KitData[p.id]
        -- BD-409: rocks and landmarks too (measured in Studio: every boulder sat ~2.3 studs INSIDE the voxel terrain, the analytic layout height
        -- is lower than the real surface). Rocks keep their RockSink embed; landmarks rest on the lowest sample.
        -- BD-416/417: build + scale the model first so the ray footprint and the embed come from the REAL mesh size (the generated mesh is
        -- fitted inside the kit extent, so extent * scale over-estimates it), with the per-kind policy of BiomePlacement.Ground.
        local made: Model? = nil
        if p.layer ~= "log" then
            made = generatedProp(p.id, p.biome or "meadow", Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 77)) or Resources.clone(p.id)
            if made then made:ScaleTo(p.scale) end
            -- BD-167: per-prop colour variation (a tint of the white MeshPart; landmarks keep their art colours).
            if made and made.PrimaryPart and p.layer ~= "landmark" then
                local tr, tg, tb = Biome.tint(p.biome or "meadow", Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 91), Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 92))
                made.PrimaryPart.Color = Color3.new(tr, tg, tb)
            end
        end
        local rayLayer = Ground.rayLayer(p.layer, data.kind)
        if (Ground.Raised[p.layer] and data.kind ~= "rock") or rayLayer == "rock" or p.layer == "landmark" then
            local hits = {}
            local size = if made and made.PrimaryPart then made.PrimaryPart.Size else Vector3.new(data.extent[1], data.extent[2], data.extent[3]) * p.scale
            local footprint = Ground.footprintRadius(rayLayer, size.X, size.Z)
            for _, pt in Ground.samplePoints(p.x, p.z, footprint) do
                local result = workspace:Raycast(Vector3.new(pt[1], p.y + 40, pt[2]), Vector3.new(0, -90, 0), rayParams)
                table.insert(hits, if result then result.Position.Y else nil)
            end
            local y = Ground.corrected(p.y, hits, rayLayer, size.Y, 1)
            if math.abs(y - p.y) > .05 then rayMoved += 1 end
            p.y = y
        end
        local pivot = CFrame.new(p.x, p.y, p.z) * CFrame.Angles(0, p.yaw, 0) * CFrame.Angles(0, 0, p.roll)
        if p.layer == "log" then
            -- A dead tree on its side: one box along the whole trunk replaces the (upright) kit collider.
            local data = KitData[p.id]
            local model = generatedProp(p.id, p.biome, 0) or Resources.clone(p.id)
            if model then model:ScaleTo(p.scale) model:PivotTo(pivot) model.Parent = folder else missing += 1 end
            local c = data.colliders[1]
            local collider = part(folder, p.id .. "Collider", Vector3.new(c[4], data.extent[2] * .9, c[6]) * p.scale, Vector3.zero,
                Color3.fromRGB(113, 133, 139), Enum.Material.Slate, true)
            collider.CFrame = pivot * CFrame.new(0, data.extent[2] * .45 * p.scale, 0)
            collider.Transparency = 1
        elseif not kitProp(folder, p.id, pivot, p.scale, p.biome, Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 77), made) then
            missing += 1
        end
        if i % 40 == 0 then task.wait() end
    end
    workspace:SetAttribute("WorldKitRayMoved", rayMoved) -- props the Terrain raycast moved (> 0.05 stud) from the analytic height
    workspace:SetAttribute("WorldKitPlacements", #placed)
    workspace:SetAttribute("WorldKitTriangles", Biome.triangles(placed, KitData))
    workspace:SetAttribute("WorldKitParts", Biome.parts(placed, KitData, meshes))
    workspace:SetAttribute("WorldKitMissing", missing)
    for layer, n in counts do workspace:SetAttribute("WorldKit_" .. layer, n) end
end
-- Flat water discs fill the marsh basins and the spring (decorative: they never block movement, like the old pool).
local function pools(parent: Instance)
    for i, pool in Layout.Pools do
        local y = Layout.waterLevel(pool)
        local disc = part(parent, if pool.spring then "SpringWater" else "MarshWater", Vector3.new(.3, pool.rz * 2, pool.rx * 2),
            Vector3.new(pool.x, y, pool.z), if pool.spring then Color3.fromRGB(77, 192, 200) else Color3.fromRGB(78, 132, 122), Enum.Material.Glass, false)
        disc.Shape = Enum.PartType.Cylinder
        disc.CFrame = CFrame.new(pool.x, y, pool.z) * CFrame.Angles(0, 0, math.pi / 2)
        disc.Transparency = if pool.spring then .28 else .2
        if pool.spring then
            local falls = part(parent, "Waterfall", Vector3.new(12, 16, .3) * Layout.Scale,
                Vector3.new(pool.x + 5, y + 8 * Layout.Scale, pool.z - 19), Color3.fromRGB(183, 236, 232), Enum.Material.Glass, false)
            falls.Transparency = .4
        end
    end
end

function Arena.build()
    local old = workspace:FindFirstChild("BeDinoArena")
    if old then old:Destroy() end
    local world = Instance.new("Folder")
    world.Name, world.Parent = "BeDinoArena", workspace
    -- BD-281: with Config.CaveHub on, the cave shell (terrain voxels) is written before IslandTerrainReady; off = nothing new.
    local caveHub = CaveHubLayout.hub(Config)
    Terrain.build(if caveHub.enabled then CaveTerrain.build else nil)
    if caveHub.enabled then Biome.useHub(caveHub.biome) end
    local extent = Config.ArenaHalfWidth
    -- Simple hidden boundary; irregular rock silhouettes dress it instead of a block wall.
    for _, x in {-extent - 2, extent + 2} do
        local boundary = part(world, "Boundary", Vector3.new(4, 160, extent * 2 + 8), Vector3.new(x, 60, 0),
            Color3.fromRGB(81, 106, 116), Enum.Material.Rock, true)
        boundary.Transparency = 1
    end
    for _, z in {-extent - 2, extent + 2} do
        local boundary = part(world, "Boundary", Vector3.new(extent * 2, 160, 4), Vector3.new(0, 60, z),
            Color3.fromRGB(81, 106, 116), Enum.Material.Rock, true)
        boundary.Transparency = 1
    end
    local random = Random.new(1404)
    local S = Layout.Scale
    local kitMode = Config.WorldArtMode == "BiomeKit"
    for side = 1, 4 do
        -- BiomeKit: every third legacy ring slot, as kit boulders (one MeshPart each, no 41-part legacy rock); Legacy: all.
        local slots = if kitMode then 5 else 11
        for i = 0, slots do
            local t = -extent + i * extent * 2 / slots
            local position = if side == 1 then Vector3.new(t, 0, -extent - 5)
                elseif side == 2 then Vector3.new(t, 0, extent + 5)
                elseif side == 3 then Vector3.new(-extent - 5, 0, t) else Vector3.new(extent + 5, 0, t)
            local ground = Vector3.new(position.X, Layout.height(position.X, position.Z), position.Z)
            local yaw = random:NextNumber(0, math.pi * 2)
            if kitMode then
                kitProp(world, if i % 2 == 0 then "world_boulder_bare_l" else "world_boulder_mossy_l", CFrame.new(ground) * CFrame.Angles(0, yaw, 0), random:NextNumber(1.6, 2.6))
            else
                rock(world, ground, random:NextNumber(2.4, 3.7) * S, yaw)
            end
        end
    end
    local spawn = Instance.new("SpawnLocation")
    spawn.Name = "PrototypeSpawn"
    -- BD-210: characters load in the hub (they used to load on the island and be moved to the hub after attach).
    -- Run starts use SpawnGeometry.islandPoint, not this part.
    spawn.Size, spawn.Position = Vector3.new(12, 1, 12), SpawnGeometry.hubPoint(Config) - Vector3.new(0, SpawnGeometry.DropClearance - .5, 0)
    spawn.Anchored, spawn.Neutral, spawn.Duration, spawn.Transparency = true, true, 0, 1
    spawn.CanCollide, spawn.CanQuery = false, false
    spawn.Parent = world
    -- Authored landmark centers; within each, offset props avoid a uniform grid.
    if kitMode then biomeKit(world) else
    for _, c in {Vector3.new(-105,0,80), Vector3.new(105,0,-80), Vector3.new(-125,0,-100), Vector3.new(128,0,102), Vector3.new(-190,0,15), Vector3.new(182,0,20), Vector3.new(0,0,-180), Vector3.new(15,0,190)} do
        local center = c * S
        for i = 1, 4 do
            local angle = i * 1.65 + random:NextNumber(-.4, .4)
            local position = center + Vector3.new(math.cos(angle) * 12, 0, math.sin(angle) * 10)
            position = Vector3.new(position.X,Layout.height(position.X,position.Z),position.Z)
            tree(world, position, random:NextNumber(1.5, 2.3), angle)
            fern(world, Vector3.new(position.X+5,Layout.height(position.X+5,position.Z+4),position.Z+4), random:NextNumber(.7,1.1), angle)
        end
        for i = 1, 3 do
            local p = center + Vector3.new(random:NextNumber(-14,14),0,random:NextNumber(-12,12))
            rock(world, Vector3.new(p.X,Layout.height(p.X,p.Z),p.Z), random:NextNumber(1.0,2.0), i)
        end
    end
    -- Scattered smaller vegetation connects landmarks while the central chase lane stays open.
    for i = 1, 65 * 2 do
        local angle, radius = i * 2.4, random:NextNumber(36,230) * S
        local position = Vector3.new(math.cos(angle)*radius,0,math.sin(angle)*radius)
        position = Vector3.new(position.X,Layout.height(position.X,position.Z),position.Z)
        if (position - Vector3.new(0,0,30)).Magnitude > 14 then fern(world, position, 1.2, angle) end
    end
    end -- Legacy dressing
    -- Stone arch landmark (1.6x with the island) with an open passage.
    local archZ = -15 * S
    for _, x in {-96 * S, -64 * S} do
        local y = Layout.height(x, archZ)
        part(world,"ArchPillar",Vector3.new(7,23,8) * S,Vector3.new(x,y+11.5*S,archZ),Color3.fromRGB(142,153,140),Enum.Material.Rock,true)
    end
    part(world,"ArchTop",Vector3.new(42,6,9) * S,Vector3.new(-80*S,Layout.height(-80*S,archZ)+24*S,archZ),Color3.fromRGB(148,157,139),Enum.Material.Rock,true)
    -- Spring and marsh water; neither blocks navigation.
    pools(world)
    for i = 1, 4 do
        local x,z = 30+i*10,-30
        part(world,"JumpStone",Vector3.new(6,1.2+i*.4,6),Vector3.new(x,Layout.height(x,z)+.6+i*.2,z),Color3.fromRGB(133,147,143),Enum.Material.Slate,true)
    end
    -- Separate safe hub beyond the north boundary, with explicit server-owned entry.
    if caveHub.enabled then
        -- Cave hub (docs/104): the shell is terrain (CaveTerrain). Props are CaveProps (BD-284); signs/text are BD-292; Leaderboards still
        -- needs a SanctuarySign anchor, so keep an invisible one until the Fame Wall exists.
        local hub = Instance.new("Model")
        hub.Name, hub.Parent = "Sanctuary", world
        local anchor = part(hub, "SanctuarySign", Vector3.new(1, 1, 1), Vector3.new(0, 35, caveHub.centerZ + 37), Color3.new(1, 1, 1), Enum.Material.SmoothPlastic, false)
        anchor.Transparency = 1
        CaveLighting.build(hub) -- BD-286: light shafts, warm fill, lava glow, gate arch light (flag on only)
        CaveLavaFx.build(hub) -- BD-285: lava falls + pool FX from the existing alpha textures (flag on only)
        CaveShowOff.build(hub) -- cosy pass: Heart pedestal "Show off" prompt (flag on only)
        CaveProps.build(hub) -- BD-284: colliders now, generated meshes load in the background and are skipped if a load fails (flag on only)
    else
        local hub = Instance.new("Model")
        local cz = CaveHubLayout.hub(Config).centerZ -- BD-280: one hub geometry source (the cave shell itself is BD-281)
        hub.Name, hub.Parent = "Sanctuary", world
        part(hub,"SanctuaryGround",Vector3.new(110,6,95),Vector3.new(0,3,cz),Color3.fromRGB(111,178,91),Enum.Material.Grass,true)
        part(hub,"NestPlaza",Vector3.new(34,.5,30),Vector3.new(0,6.25,cz),Color3.fromRGB(223,205,154),Enum.Material.Sandstone,true)
        for _, x in {-48,48} do
            part(hub,"HubFence",Vector3.new(2,10,92),Vector3.new(x,11,cz),Color3.fromRGB(83,131,73),Enum.Material.Wood,true)
        end
        for _, z in {cz-43,cz+43} do
            part(hub,"HubFence",Vector3.new(96,10,2),Vector3.new(0,11,z),Color3.fromRGB(83,131,73),Enum.Material.Wood,true)
        end
        for _, x in {-32,32} do
            if kitMode then kitProp(hub, "world_tree_conifer_m", CFrame.new(x, 6, cz + 15) * CFrame.Angles(0, x, 0), 1.2) else tree(hub,Vector3.new(x,6,cz+15),1.2,x) end
        end
        for i = 1,5 do
            local nest = part(hub,"EggNest",Vector3.new(5,1,5),Vector3.new(-18+i*6,6.6,cz+20),Color3.fromRGB(174,129,70),Enum.Material.Wood,false)
            nest.Shape = Enum.PartType.Cylinder
        end
        local sign = part(hub,"SanctuarySign",Vector3.new(30,7,1),Vector3.new(0,15,cz+37),Color3.fromRGB(27,76,51),Enum.Material.Wood,false)
        local surface = Instance.new("SurfaceGui")
        surface.Face, surface.CanvasSize, surface.Parent = Enum.NormalId.Front, Vector2.new(600,140), sign
        local label = Instance.new("TextLabel")
        label.Size, label.BackgroundTransparency, label.Text = UDim2.fromScale(1,1),1,"SANCTUARY"
        label.Font, label.TextScaled, label.TextColor3, label.Parent = Enum.Font.FredokaOne,true,Color3.new(1,1,1),surface
    end
    workspace:SetAttribute("ArenaArtMode", if ReplicatedStorage.Resources:FindFirstChild("tree") then "Resource meshes" else "Import resources/models for mesh art")
end
return Arena
