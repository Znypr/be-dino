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
local WorldSea = require(ReplicatedStorage.Shared.WorldSea)
local WorldToon = require(ReplicatedStorage.Shared.WorldToon)
local Veg2 = require(ReplicatedStorage.Shared.VegetationV2) -- BD-1239
local Fill = require(ReplicatedStorage.Shared.WorldFill) -- BD-1245 / BD-1246
local PlazaHubLayout = require(ReplicatedStorage.Shared.PlazaHubLayout)
local PlazaShopsLayout = require(ReplicatedStorage.Shared.PlazaShopsLayout)
local KitData = require(ReplicatedStorage.Shared.WorldKitData)
local KitMeshes = require(ReplicatedStorage.Shared.WorldKitMeshAssets)
local Generated = require(ReplicatedStorage.Shared.WorldGeneratedMeshes)
local ColossalRules = require(ReplicatedStorage.Shared.ColossalRules)
local ScaleLadder = require(ReplicatedStorage.Shared.ScaleLadder) -- BD-407: legacy-hub nest and sign sizes live in the one scale ladder
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
                position + offset * scale, Color3.fromRGB(76, 138, 100), Enum.Material.SmoothPlastic, false) -- BD-460: was 64,144,112 (mint)
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
            Color3.fromRGB(112, 164, 116), Enum.Material.SmoothPlastic, false) -- BD-460: was 106,180,125
        leaf.Shape = Enum.PartType.Ball
        leaf.CFrame = CFrame.new(leaf.Position) * CFrame.Angles(-0.28, angle, 0)
    end
end
-- BD-206: Roblox-generated MeshPart for a kit id (one part). Scaled uniformly to fit inside the kit id's extent box so the
-- invisible kit colliders still match, pivot = bottom centre. nil (flag off, id not mapped, mesh failed to load) means the
-- caller keeps the current kit model, so a failed asset never leaves a hole.
local generatedCache: {[string]: Model} = {}
-- BD-1239: the vegetation v2 mesh for a kit id (Shared/VegetationV2), fitted into the kit box by kind (Veg2.fit), pivot = bottom centre.
-- nil (flag off, kit id not in the family, id not published or the load failed) = the rules of generatedProp below, exactly as before.
local veg2On = Veg2.enabled(Config)
local function veg2Prop(id: string, biome: string, roll: number): Model?
    local key = Veg2.visualFor(id, biome, roll)
    local folder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local template = if key and Veg2.ready(key) and folder then folder:FindFirstChild(key) else nil
    if not key or not template or not template:IsA("MeshPart") or not KitData[id] then return nil end
    local cacheKey = key .. "|" .. id
    if not generatedCache[cacheKey] then
        local size = template.Size
        local mesh = template:Clone()
        mesh.Size = size * Veg2.fit(KitData[id].kind, KitData[id].extent, {size.X, size.Y, size.Z})
        mesh.Size = Vector3.new(mesh.Size.X, mesh.Size.Y * (Veg2.Squash[key] or 1), mesh.Size.Z) -- BD-1239 follow-up: lower bush domes
        mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless = true, false, false, false, true
        mesh.CFrame = CFrame.new(0, mesh.Size.Y / 2, 0)
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
local function generatedProp(id: string, biome: string, roll: number, layer: string?): Model?
    if not Config.WorldGeneratedMeshes then return nil end
    if veg2On then
        local v2 = veg2Prop(id, biome, roll)
        if v2 then return v2 end
    end
    local key = Generated.visualFor(id, biome, roll)
    local folder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local template = nil
    -- BD-474: the `colossal` layer gets the ancient-tree mesh (only once its asset id is filled in AND it loaded). Ordinary size-l trees share
    -- the same kit id, so the layer decides; no id or a failed load keeps the stand-in below (the current generated mesh scaled up).
    -- BD-475: the ancient tree is only used as a PAIR: LOD0 and its LOD1 must both have loaded (the client swaps them by distance and the
    -- triangle budget counts on the light one), else the stand-in below stays.
    local colossalKey = if layer == "colossal" then Generated.colossalFor(id) else nil
    local lodTemplate: Instance? = nil
    if colossalKey and folder then
        local near, far = folder:FindFirstChild(colossalKey), folder:FindFirstChild(ColossalRules.lod1Key(colossalKey))
        if near and near:IsA("MeshPart") and far and far:IsA("MeshPart") then
            template, lodTemplate, key = near, far, colossalKey
        end
    end
    -- BD-462: owner-approved V3 tree first (only once its asset id is filled in AND it loaded); otherwise the current generated mesh.
    local v3Key = if key then Generated.replacementFor(key) else nil
    if v3Key and folder then
        template = folder:FindFirstChild(v3Key)
        if template then key = v3Key end
    end
    if not template and key and folder then template = folder:FindFirstChild(key) end
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
        if lodTemplate and lodTemplate:IsA("MeshPart") then
            -- BD-475: the far mesh rides along as a second part. Same height as LOD0, centre moved so both trunks stand on the same point
            -- (the pivot is each mesh's bbox bottom centre and the two bboxes differ by up to ~5 studs). WorldCulling parents ONE of them.
            local e0, e1 = Generated.Colossal[key], Generated.Colossal[ColossalRules.lod1Key(key)]
            local far = lodTemplate:Clone()
            local k = mesh.Size.Y / far.Size.Y
            far.Size = far.Size * k
            local dx, dz = ColossalRules.lod1Offset(e0, e1, mesh.Size.Y)
            far.Name = "ColossalLod1"
            far.Anchored, far.CanCollide, far.CanTouch, far.CanQuery, far.Massless = true, false, false, false, true
            far.CFrame = CFrame.new(dx, far.Size.Y / 2, dz)
            far.Parent = model
            model:SetAttribute("ColossalKey", key)
            model:SetAttribute("ColossalTris0", e0.tris)
            model:SetAttribute("ColossalTris1", e1.tris)
        end
        generatedCache[cacheKey] = model
    end
    workspace:SetAttribute("WorldGeneratedProps", (workspace:GetAttribute("WorldGeneratedProps") or 0) + 1)
    return generatedCache[cacheKey]:Clone()
end
-- BD-463 / BD-464 step 2: one Blender plant or ground prop (WorldGeneratedMeshes.Props key). Only called for keys BiomePlacement placed, i.e. whose
-- asset id is valid AND whose template really loaded into GeneratedWorld. The mesh is fitted inside the size recorded for the key (so an import
-- scale mismatch cannot make a tuft huge) and its pivot is the bottom centre, exactly like generatedProp.
local propCache: {[string]: Model} = {}
local function propProp(key: string): Model?
    local folder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local template = if folder then folder:FindFirstChild(key) else nil
    local entry = Generated.Props[key]
    if not template or not template:IsA("MeshPart") or not entry then return nil end
    if not propCache[key] then
        local size, want = template.Size, entry.size
        local fit = math.min(want[1] / size.X, want[2] / size.Y, want[3] / size.Z)
        local mesh = template:Clone()
        mesh.Size = size * fit
        mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless = true, false, false, false, true
        mesh.CFrame = CFrame.new(0, mesh.Size.Y / 2, 0)
        mesh.PivotOffset = CFrame.new(0, -mesh.Size.Y / 2, 0)
        local model = Instance.new("Model")
        mesh.Parent = model
        model.PrimaryPart = mesh
        model.WorldPivot = CFrame.new()
        model.Name = key
        model:SetAttribute("GeneratedMesh", key)
        propCache[key] = model
    end
    workspace:SetAttribute("WorldGeneratedProps", (workspace:GetAttribute("WorldGeneratedProps") or 0) + 1)
    return propCache[key]:Clone()
end
-- One kit prop = the uploaded MeshPart model (1 part) plus simplified invisible box colliders scaled with it.
local function kitProp(folder: Instance, id: string, pivot: CFrame, scale: number, biome: string?, roll: number?, made: Model?, kitAll: any?, fitted: {{number}}?): boolean
    local model = made or generatedProp(id, biome or "meadow", roll or .5) or Resources.clone(id)
    if model then
        if not made then model:ScaleTo(scale) end
        model:PivotTo(pivot)
        model.Parent = folder
    end
    if fitted then
        -- BD-475: trunk colliders re-fitted from the colossal mesh's own trunk numbers (pivot-local studs, already scaled).
        for _, c in fitted do
            local collider = part(folder, id .. "Collider", Vector3.new(c[4], c[5], c[6]), Vector3.zero, Color3.fromRGB(113, 133, 139), Enum.Material.Slate, true)
            collider.CFrame = pivot * CFrame.new(c[1], c[2], c[3]) * CFrame.Angles(0, c[7], 0)
            collider.Transparency = 1
        end
        return model ~= nil
    end
    for _, c in (kitAll or KitData)[id].colliders do
        local collider = part(folder, id .. "Collider", Vector3.new(c[4], c[5], c[6]) * scale, Vector3.zero,
            Color3.fromRGB(113, 133, 139), Enum.Material.Slate, true)
        collider.CFrame = pivot * CFrame.new(Vector3.new(c[1], c[2], c[3]) * scale) * CFrame.Angles(0, c[7], 0)
        collider.Transparency = 1
    end
    return model ~= nil
end
-- BD-475: the re-fitted trunk colliders of a colossal ancient tree (nil for every other prop, so they keep their kit colliders).
local function ancientColliders(made: Model?): {{number}}?
    local entry = if made then Generated.Colossal[made:GetAttribute("ColossalKey") :: any] else nil
    if not entry or not made or not made.PrimaryPart then return nil end
    return ColossalRules.colliders(entry, made.PrimaryPart.Size.Y)
end
-- BD-1245 / BD-1246 (Config.GroundDetailEnabled / ThingsToDoEnabled, Shared/WorldFill): generated ground detail along the paths and in the open
-- grass, and one set piece beside each spoke. One MeshPart each, fitted into its WorldFill size box, pivot bottom centre, resting on the real
-- terrain (lowest of five rays, sunk a little). They go into WorldKit, so WorldCulling hides them by distance like the plants. Flags off = nothing.
local fillCache: {[string]: Model} = {}
local function fillModel(key: string): Model?
    local folder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local template = if folder and Fill.ready(key) then folder:FindFirstChild(Fill.Assets[key].use or key) else nil
    if not template or not template:IsA("MeshPart") then return nil end
    if not fillCache[key] then
        local want, size = Fill.Assets[key].size, template.Size
        local mesh = template:Clone()
        -- longest side to want[1], height at most want[2]; a mesh that came out long along Z is turned so its long side lies along local X
        mesh.Size = size * math.min(want[1] / math.max(size.X, size.Z), want[2] / size.Y)
        mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless, mesh.CastShadow = true, false, false, false, true, key:sub(1, 4) == "set_"
        local turn = if size.Z > size.X * 1.15 then CFrame.Angles(0, math.pi / 2, 0) else CFrame.new()
        mesh.CFrame = CFrame.new(0, mesh.Size.Y / 2, 0) * turn
        mesh.PivotOffset = CFrame.new(0, -mesh.Size.Y / 2, 0) * turn:Inverse()
        local model = Instance.new("Model")
        mesh.Parent = model
        model.PrimaryPart = mesh
        model.WorldPivot = CFrame.new()
        model.Name = key
        model:SetAttribute("GeneratedMesh", key)
        fillCache[key] = model
    end
    return fillCache[key]:Clone()
end
local function signWords(model: Model)
    local mesh = model.PrimaryPart
    if not mesh then return end
    local gui = Instance.new("BillboardGui")
    gui.Name, gui.Size, gui.StudsOffset = "SignWords", UDim2.fromScale(7, 4.2), Vector3.new(0, mesh.Size.Y * .5 + 2.4, 0)
    gui.MaxDistance, gui.LightInfluence, gui.Parent = 140, 0, mesh
    local list = Instance.new("UIListLayout")
    list.HorizontalAlignment, list.VerticalAlignment, list.Parent = Enum.HorizontalAlignment.Center, Enum.VerticalAlignment.Center, gui
    for i, word in Fill.SignWords do
        local label = Instance.new("TextLabel")
        label.Size, label.BackgroundTransparency, label.Text, label.LayoutOrder = UDim2.fromScale(1, .33), 1, word, i
        label.Font, label.TextScaled, label.TextColor3 = Enum.Font.FredokaOne, true, Color3.fromRGB(92, 60, 34)
        local stroke = Instance.new("UIStroke") -- cream outline: reads on the sky and on the trees
        stroke.Color, stroke.Thickness, stroke.Parent = Color3.fromRGB(255, 244, 214), 2.5, label
        label.Parent = gui
    end
end
local function worldFill(folder: Instance, placed: {any}, kitAll: any)
    local V3 = if (Layout :: any).V3 then BiomeMap.V3 else nil
    local ground, things = Fill.groundEnabled(Config), Fill.thingsEnabled(Config)
    if not V3 or not (ground or things) then return end
    local blockers = {}
    for _, p in placed do
        if p.layer == "groundcover" then continue end
        local e = kitAll[p.id].extent
        table.insert(blockers, {x = p.x, z = p.z, r = math.max(e[1], e[3]) * .5 * p.scale})
    end
    for _, site in V3.Landmarks do
        local x, z = V3.polar(site.angle, site.r)
        table.insert(blockers, {x = x, z = z, r = if site.id == "volcano" then 60 else 30})
    end
    local rayParams = RaycastParams.new()
    rayParams.FilterType, rayParams.FilterDescendantsInstances = Enum.RaycastFilterType.Include, {workspace.Terrain}
    local made, sets = 0, 0
    local function put(p: any): Model?
        local model = fillModel(p.key)
        if not model or not model.PrimaryPart then return nil end
        model:ScaleTo(p.scale)
        local size = model.PrimaryPart.Size
        local r = math.min(size.X, size.Z) * .35
        local y = math.huge
        for _, o in {{0, 0}, {r, 0}, {-r, 0}, {0, r}, {0, -r}} do
            local hit = workspace:Raycast(Vector3.new(p.x + o[1], 200, p.z + o[2]), Vector3.new(0, -260, 0), rayParams)
            y = math.min(y, if hit then hit.Position.Y else Layout.height(p.x + o[1], p.z + o[2]))
        end
        model:PivotTo(CFrame.new(p.x, y - size.Y * .06, p.z) * CFrame.Angles(0, p.yaw, 0))
        model.Parent = folder
        made += 1
        return model
    end
    local detail = if ground then Fill.groundDetail(V3, blockers) else {}
    if things then
        for _, p in Fill.setPieceSites(V3, blockers) do
            local model = put(p)
            if not model or not model.PrimaryPart then continue end
            sets += 1
            local size = model.PrimaryPart.Size
            if p.key == "set_signpost" then signWords(model) end
            if p.key ~= "set_log_bridge" then
                -- one low hidden box so dinos walk around it (named *Collider: the phone culls it like the kit colliders)
                local w = if p.key == "set_signpost" then 1.6 else .7
                local box = part(folder, p.key .. "Collider", Vector3.new(size.X * w * (if p.key == "set_signpost" then .3 else 1), math.min(size.Y, 4), size.Z * w * (if p.key == "set_signpost" then .3 else 1)),
                    Vector3.zero, Color3.fromRGB(113, 133, 139), Enum.Material.Slate, true)
                box.CFrame = model:GetPivot() * CFrame.new(0, math.min(size.Y, 4) / 2, 0)
                box.Transparency = 1
            end
            -- the set pieces count as blockers for the ground detail
            table.insert(blockers, {x = p.x, z = p.z, r = math.max(size.X, size.Z) * .5})
        end
        if ground then detail = Fill.groundDetail(V3, blockers) end
    end
    for i, p in detail do
        put(p)
        if i % 40 == 0 then task.wait() end
    end
    workspace:SetAttribute("WorldFillParts", made)
    workspace:SetAttribute("WorldFillSetPieces", sets)
end
-- BD-049 BiomeKit dressing (world v2): sub-biome driven kit props, colossal trees (BD-473, was giants), fallen logs, a 4-12 stud Small band, clearings and ground cover.
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
    -- BD-463/464 step 2: the Blender plants and ground props take part only when Config.WorldGeneratedMeshes is on, the key has a valid asset id
    -- (BiomePlacement.validAssetId) AND its template really loaded into GeneratedWorld. Empty ids (today) = the grammar exactly as before.
    local propEntries: {[string]: any} = {}
    local generatedFolder = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    if Config.WorldGeneratedMeshes and generatedFolder then
        for key, entry in Generated.Props do
            local template = generatedFolder:FindFirstChild(key)
            if template and template:IsA("MeshPart") and Generated.validId(entry.assetId) then propEntries[key] = entry end
        end
    end
    local kitAll = Biome.withProps(KitData, propEntries)
    meshes = Biome.propMeshes(meshes, propEntries)
    local placed = Biome.generate({seed = Config.WorldArtSeed, density = Config.WorldArtDensity,
        extent = Config.ArenaHalfWidth, height = Layout.height, kit = KitData, meshes = meshes, map = BiomeMap, layout = Layout, props = propEntries})
    -- BD-1245 (Config.GroundDetailEnabled): the flower patches take over the open grass, so fewer single ground cover clumps stay (fewer parts)
    if veg2On and Fill.groundEnabled(Config) then Veg2.CoverKeep = Fill.CoverKeep end
    if veg2On then placed = Veg2.thin(placed) end -- BD-1239: fewer, fuller ground cover clumps (the other layers and the food hosts are untouched)
    local missing = 0
    local counts = {tree = 0, colossal = 0, log = 0, rock = 0, shrub = 0, groundcover = 0, landmark = 0}
    -- BD-395: trees, colossal trees and shrubs rest ON the real voxel terrain: five rays (centre + around the trunk) from above, the
    -- bottom (pivot) goes to the highest hit + 0.2 (BiomePlacement.Ground). A missed ray keeps the analytic layout height.
    local rayParams = RaycastParams.new()
    rayParams.FilterType, rayParams.FilterDescendantsInstances = Enum.RaycastFilterType.Include, {workspace.Terrain}
    local Ground, rayMoved = Biome.Ground, 0
    for i, p in placed do
        counts[p.layer] += 1
        local data = kitAll[p.id]
        local isNewProp = propEntries[p.id] ~= nil
        -- BD-409: rocks and landmarks too (measured in Studio: every boulder sat ~2.3 studs INSIDE the voxel terrain, the analytic layout height
        -- is lower than the real surface). Rocks keep their RockSink embed; landmarks rest on the lowest sample.
        -- BD-416/417: build + scale the model first so the ray footprint and the embed come from the REAL mesh size (the generated mesh is
        -- fitted inside the kit extent, so extent * scale over-estimates it), with the per-kind policy of BiomePlacement.Ground.
        local made: Model? = nil
        if p.layer ~= "log" then
            made = if isNewProp then propProp(p.id)
                else generatedProp(p.id, p.biome or "meadow", Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 77), p.layer) or Resources.clone(p.id)
            if made then made:ScaleTo(p.scale) end
            -- BD-167: per-prop colour variation (a tint of the white MeshPart; landmarks keep their art colours).
            if made and made.PrimaryPart and p.layer ~= "landmark" and not (isNewProp and (data.family == "flowers" or data.family == "ground_mushrooms")) then
                local tr, tg, tb = Biome.tint(p.biome or "meadow", Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 91), Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 92))
                made.PrimaryPart.Color = Color3.new(tr, tg, tb)
            end
        end
        local rayLayer = Ground.rayLayer(p.layer, data.kind)
        if (Ground.Raised[p.layer] and data.kind ~= "rock") or rayLayer == "rock" or p.layer == "landmark" then
            local hits = {}
            local size = if made and made.PrimaryPart then made.PrimaryPart.Size else Vector3.new(data.extent[1], data.extent[2], data.extent[3]) * p.scale
            -- BD-475: a colossal ancient tree is grounded on its real trunk footprint (9 rays, the LOWEST one wins), not the 1-stud centre ray.
            local ancient = if made then Generated.Colossal[made:GetAttribute("ColossalKey") :: any] else nil
            local points = if ancient then ColossalRules.groundPoints(p.x, p.z, p.yaw, ancient, size.Y)
                else Ground.samplePoints(p.x, p.z, Ground.footprintRadius(rayLayer, size.X, size.Z))
            for _, pt in points do
                local result = workspace:Raycast(Vector3.new(pt[1], p.y + 40, pt[2]), Vector3.new(0, -90, 0), rayParams)
                table.insert(hits, if result then result.Position.Y else nil)
            end
            local y = if ancient then ColossalRules.groundY(p.y, hits) else Ground.corrected(p.y, hits, rayLayer, size.Y, 1)
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
        elseif not kitProp(folder, p.id, pivot, p.scale, p.biome, Biome.hash(math.floor(p.x * 8), math.floor(p.z * 8), 77), made, kitAll, ancientColliders(made)) then
            missing += 1
        end
        if i % 40 == 0 then task.wait() end
    end
    workspace:SetAttribute("WorldKitRayMoved", rayMoved) -- props the Terrain raycast moved (> 0.05 stud) from the analytic height
    workspace:SetAttribute("WorldKitPlacements", #placed)
    workspace:SetAttribute("WorldKitTriangles", Biome.triangles(placed, kitAll))
    workspace:SetAttribute("WorldKitParts", Biome.parts(placed, kitAll, meshes))
    workspace:SetAttribute("WorldKitNewProps", (function() local n = 0 for _, p in placed do if propEntries[p.id] then n += 1 end end return n end)()) -- BD-463/464: Blender plants and ground props placed
    workspace:SetAttribute("WorldKitMissing", missing)
    for layer, n in counts do workspace:SetAttribute("WorldKit_" .. layer, n) end
    worldFill(folder, placed, kitAll)
end
-- BD-1210 (docs/241 W4, Config.WorldV3Enabled): one big generated landmark per zone on its WorldV3 site, resting on the terrain, facing the
-- plaza, scaled to its height; hidden boxes collide instead of the mesh (the arch stays walkable). The volcano is the terrain itself plus a
-- calm crater smoke and glow. A landmark whose mesh failed to load leaves its site an open clearing.
local function v3Landmarks(parent: Instance, V3: any)
    local folder = Instance.new("Folder")
    folder.Name, folder.Parent = "Landmarks", parent
    local generated = ReplicatedStorage:FindFirstChild("GeneratedWorld")
    local rayParams = RaycastParams.new()
    rayParams.FilterType, rayParams.FilterDescendantsInstances = Enum.RaycastFilterType.Include, {workspace.Terrain}
    local function groundAt(x: number, z: number): number
        local hit = workspace:Raycast(Vector3.new(x, 200, z), Vector3.new(0, -260, 0), rayParams)
        return if hit then hit.Position.Y else Layout.height(x, z)
    end
    local placed = 0
    for key, entry in Generated.Landmarks do
        local template = if generated then generated:FindFirstChild(key) else nil
        local site = nil
        for _, s in V3.Landmarks do if s.id == entry.site then site = s end end
        if not template or not template:IsA("BasePart") or not site then continue end
        local x, z = V3.polar(site.angle, site.r)
        local mesh = template:Clone() :: BasePart
        local factor = entry.height / mesh.Size.Y
        mesh.Size *= factor
        -- rest on the lowest of five ground samples under the footprint, sunk a little so no edge floats
        local r = math.min(mesh.Size.X, mesh.Size.Z) * .35
        local y = math.huge
        for _, o in {{0, 0}, {r, 0}, {-r, 0}, {0, r}, {0, -r}} do y = math.min(y, groundAt(x + o[1], z + o[2])) end
        y -= .6
        local base = CFrame.lookAt(Vector3.new(x, y, z), Vector3.new(V3.CenterX, y, V3.CenterZ))
        if entry.flip then base *= CFrame.Angles(0, math.pi, 0) end -- a mesh whose front is +Z
        mesh.CFrame = base * CFrame.new(0, mesh.Size.Y / 2, 0)
        mesh.Anchored, mesh.CanCollide, mesh.CanQuery, mesh.CanTouch = true, false, false, false
        mesh.Name = key
        mesh.Parent = folder
        for _, c in entry.colliders do
            local box = part(folder, key .. "Collider", Vector3.new(c[4] * mesh.Size.X, c[5] * mesh.Size.Y, c[6] * mesh.Size.Z), Vector3.zero,
                Color3.fromRGB(113, 133, 139), Enum.Material.Slate, true)
            box.CFrame = base * CFrame.new(c[1] * mesh.Size.X, c[2] * mesh.Size.Y, c[3] * mesh.Size.Z)
            box.Transparency = 1
        end
        placed += 1
    end
    -- Volcano crater: soft smoke and a warm glow (calm, docs/87).
    for _, s in V3.Landmarks do
        if s.id ~= "volcano" then continue end
        local x, z = V3.polar(s.angle, s.r)
        local vent = part(folder, "VolcanoVent", Vector3.new(14, 1, 14), Vector3.new(x, groundAt(x, z) + 1, z), Color3.fromRGB(255, 120, 40), Enum.Material.Neon, false)
        vent.Transparency = 1
        local smoke = Instance.new("ParticleEmitter")
        smoke.Texture = "rbxasset://textures/particles/smoke_main.dds" -- built-in soft smoke (the uploaded smokeSoft id does not load, Studio 2026-11-16)
        smoke.Rate, smoke.Lifetime, smoke.Speed = 2.5, NumberRange.new(9, 13), NumberRange.new(4, 7)
        smoke.Size = NumberSequence.new({NumberSequenceKeypoint.new(0, 10), NumberSequenceKeypoint.new(1, 34)})
        smoke.Transparency = NumberSequence.new({NumberSequenceKeypoint.new(0, .55), NumberSequenceKeypoint.new(.7, .75), NumberSequenceKeypoint.new(1, 1)})
        smoke.Color = ColorSequence.new(Color3.fromRGB(150, 140, 136), Color3.fromRGB(220, 214, 208))
        smoke.SpreadAngle, smoke.Acceleration, smoke.LightInfluence = Vector2.new(12, 12), Vector3.new(1.5, .6, 0), .6
        smoke.Parent = vent
        local glow = Instance.new("PointLight")
        glow.Color, glow.Brightness, glow.Range = Color3.fromRGB(255, 130, 50), 3, 40
        glow.Parent = vent
    end
    workspace:SetAttribute("WorldV3Landmarks", placed)
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
    if (Layout :: any).V3 then Biome.useV3(BiomeMap.V3) end -- BD-1209: routes, keep-outs and landmark sites of the round island
    if WorldToon.enabled(Config) then Biome.useToonPlants(WorldToon.Swaps, WorldToon.swapList) end -- BD-1224: round glossy bushes, no spiky fronds
    if Veg2.enabled(Config) then Biome.BushV2 = Veg2.BushRule end -- BD-1239 follow-up: smaller berry bushes, open grass and flowers between clumps
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
    -- BD-1209 (Config.WorldV3Enabled): the round island. A hidden wall follows the coast out in the shallow sea, an ocean plane reaches the
    -- horizon past the terrain square, and the square-edge boulder ring, the old stone arch and the jump stones are not built.
    local V3 = if (Layout :: any).V3 then BiomeMap.V3 else nil
    if V3 then
        local segments, previous = 72, nil
        for i = 0, segments do
            local angle = i * 360 / segments
            local x, z = V3.polar(angle, V3.coast(angle) + 14)
            local point = Vector3.new(x, 60, z)
            if previous then
                local mid, span = (previous + point) / 2, (point - previous)
                local wall = part(world, "CoastBoundary", Vector3.new(span.Magnitude + 3, 160, 4), mid, Color3.fromRGB(81, 106, 116), Enum.Material.Rock, true)
                wall.CFrame = CFrame.lookAt(mid, mid + Vector3.new(-span.Z, 0, span.X))
                wall.Transparency = 1
            end
            previous = point
        end
        if WorldSea.enabled(Config) then
            -- BD-1220: terrain water reaches the horizon (IslandTerrain), so no square ocean plate (the Atmosphere is set in Bootstrap).
        else
            local ocean = part(world, "Ocean", Vector3.new(6000, 1, 6000), Vector3.new(0, V3.SeaLevel - .9, 0), Color3.fromRGB(64, 170, 206), Enum.Material.SmoothPlastic, false)
            ocean.CanCollide, ocean.CanQuery, ocean.CanTouch, ocean.CastShadow = false, false, false, false
            ocean.Transparency = .05
        end
    end
    for side = 1, if V3 then 0 else 4 do
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
    if V3 and PlazaHubLayout.enabled(Config) then -- BD-1221: stalls on the plaza; BD-1248: themed shop buildings instead (PlazaShopsV2Enabled)
        if PlazaShopsLayout.enabled(Config) then require(script.Parent.PlazaShops).build(world, V3.CenterX, V3.CenterZ)
        else require(script.Parent.PlazaHub).build(world, V3.CenterX, V3.CenterZ) end
    end
    if kitMode then biomeKit(world) if V3 then v3Landmarks(world, V3) end else
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
    if not V3 then
    local archZ = -15 * S
    for _, x in {-96 * S, -64 * S} do
        local y = Layout.height(x, archZ)
        part(world,"ArchPillar",Vector3.new(7,23,8) * S,Vector3.new(x,y+11.5*S,archZ),Color3.fromRGB(142,153,140),Enum.Material.Rock,true)
    end
    part(world,"ArchTop",Vector3.new(42,6,9) * S,Vector3.new(-80*S,Layout.height(-80*S,archZ)+24*S,archZ),Color3.fromRGB(148,157,139),Enum.Material.Rock,true)
    end -- not V3 (arch)
    -- Spring and marsh water; neither blocks navigation.
    pools(world)
    for i = 1, if V3 then 0 else 4 do
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
            local nest = part(hub,"EggNest",Vector3.new(ScaleLadder.Nest.pad[1], ScaleLadder.Nest.pad[2], ScaleLadder.Nest.pad[3]),Vector3.new(-18+i*6,6.6,cz+20),Color3.fromRGB(174,129,70),Enum.Material.Wood,false)
            nest.Shape = Enum.PartType.Cylinder
        end
        local sign = part(hub,"SanctuarySign",Vector3.new(ScaleLadder.Hub.sign.legacyBoard[1], ScaleLadder.Hub.sign.legacyBoard[2], ScaleLadder.Hub.sign.legacyBoard[3]),Vector3.new(0,15,cz+37),Color3.fromRGB(27,76,51),Enum.Material.Wood,false)
        local surface = Instance.new("SurfaceGui")
        surface.Face, surface.CanvasSize, surface.Parent = Enum.NormalId.Front, Vector2.new(600,140), sign
        local label = Instance.new("TextLabel")
        label.Size, label.BackgroundTransparency, label.Text = UDim2.fromScale(1,1),1,"SANCTUARY"
        label.Font, label.TextScaled, label.TextColor3, label.Parent = Enum.Font.FredokaOne,true,Color3.new(1,1,1),surface
    end
    workspace:SetAttribute("ArenaArtMode", if ReplicatedStorage.Resources:FindFirstChild("tree") then "Resource meshes" else "Import resources/models for mesh art")
end
return Arena
