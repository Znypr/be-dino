--!strict
-- BD-284 (docs/104 s3, s13): places the Cave hub props from the pure CaveHubLayout rows with the published generate_mesh ids
-- in CaveHubProps. Only called from Arena's cave branch (Config.CaveHub on); flag off = this module never runs.
-- Rules: generated meshes only (no code-built models). Each prop is one anchored MeshPart (CanCollide false for decoration; CollisionFidelity is not script-writable, the asset default stays,
-- true only for the large wall/rim pieces in CaveHubProps.Solid), scaled uniformly to the layout size, bottom on the cave floor
-- (terrain raycast, falling back to CaveHubLayout.floorHeight), facing the station / the Heart. Invisible box colliders come from
-- CaveHubLayout.colliders and are created at once (they need no asset). Meshes load in the background in small batches with
-- task.wait, so this never blocks Arena.build or the terrain-ready signal; a mesh that fails to load is skipped (warn + counter) and
-- its station keeps pad, sign and prompt. The lava waterfall and pool are CaveLavaFx, not meshes.
local InsertService = game:GetService("InsertService")
local AssetService = game:GetService("AssetService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Layout = require(ReplicatedStorage.Shared.CaveHubLayout)
local Props = require(ReplicatedStorage.Shared.CaveHubProps)
local KitMeshes = require(ReplicatedStorage.Shared.WorldKitMeshAssets)
local GeneratedMeshes = require(ReplicatedStorage.Shared.WorldGeneratedMeshes)
local SignCopy = require(ReplicatedStorage.Shared.HubSignCopy)
local TerrainRules = require(ReplicatedStorage.Shared.CaveTerrainRules)
local CaveProps = {}
local signGuis = 0 -- sign texts placed this build (capped by Props.MaxSignGuis)

local LOAD_WORKERS = 6 -- parallel LoadAsset calls
local PLACE_BATCH = 16 -- props placed per frame
local LOAD_DEADLINE = 90 -- seconds; assets still pending after this are skipped
local SINK = 0.15 -- studs a floor prop sinks into the floor so nothing floats on the rough terrain

local function loadTemplate(key: string, assetId: string): MeshPart
    -- generate_mesh publishes a Model ("Roblox Generated Object") that holds one textured MeshPart.
    local container = InsertService:LoadAsset(tonumber(assetId) :: number)
    local found: MeshPart? = nil
    for _, item in container:GetDescendants() do
        if item:IsA("MeshPart") then found = item break end
    end
    assert(found, "generated asset has no MeshPart")
    local mesh = found:Clone()
    container:Destroy()
    for _, child in mesh:GetChildren() do
        if not child:IsA("SurfaceAppearance") then child:Destroy() end
    end
    mesh.Name = key
    mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless = true, false, false, false, true
    mesh:SetAttribute("GeneratedAssetId", assetId)
    return mesh
end

-- BD-296 dressing: a kit mesh (the island's own low-poly plants and rocks, WorldKitMeshAssets: vertex colours, no texture) as one MeshPart, sized in studs
-- from the binding like ImportedResources.loadWorldKit does.
local function loadKit(key: string, binding: any): MeshPart
    local mesh = AssetService:CreateMeshPartAsync(Content.fromUri(binding.meshId), {CollisionFidelity = Enum.CollisionFidelity.Box, RenderFidelity = Enum.RenderFidelity.Automatic})
    mesh.Name = key
    mesh.Size = Vector3.new(binding.size[1], binding.size[2], binding.size[3])
    mesh.Color = Color3.new(1, 1, 1)
    mesh.Material = Enum.Material.SmoothPlastic
    mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless = true, false, false, false, true
    mesh:SetAttribute("KitMeshId", binding.meshId)
    return mesh
end

local function kitKeySet(): {[string]: boolean}
    local set: {[string]: boolean} = {}
    for key in KitMeshes do set[key] = true end
    return set
end

-- Terrain surface height below (x, z): a raycast against Terrain only, falling back to the layout's floor height.
local function floorAt(params: RaycastParams, x: number, z: number): number
    local hit = workspace:Raycast(Vector3.new(x, Layout.FloorY + 30, z), Vector3.new(0, -60, 0), params)
    if hit and math.abs(hit.Position.Y - Layout.FloorY) < 6 then return hit.Position.Y end
    return Layout.floorHeight(x, z)
end

-- BD-384: terrain ceiling height above (x, z): a raycast UP against Terrain, falling back to the shell rule (the rough ceiling the
-- voxels are written from). Stalactites hang from this so they touch the rock instead of floating below it.
local function ceilingAt(params: RaycastParams, x: number, z: number): number
    local rule = TerrainRules.ceilingAt(x, z)
    local hit = workspace:Raycast(Vector3.new(x, Layout.FloorY + 4, z), Vector3.new(0, 90, 0), params)
    if hit and math.abs(hit.Position.Y - rule) < 6 then return hit.Position.Y end
    return rule
end

local function colliderHeight(owner: string): number
    local base = string.gsub(owner, "_pillar%d+$", "")
    if owner == "lava_fence" then return 5 end
    local kind = Layout.Kinds[base]
    return if kind then math.clamp(kind[2], 4, 16) else 6
end

local function buildColliders(parent: Instance, params: RaycastParams)
    local folder = Instance.new("Folder")
    folder.Name = "Colliders"
    local cz = Layout.CenterZ
    for _, c in Layout.get().colliders do
        local h = colliderHeight(c.owner)
        local y = floorAt(params, c.x, c.z + cz)
        local p = Instance.new("Part")
        p.Name = "Collider_" .. c.owner
        p.Size = Vector3.new(c.w, h, c.d)
        p.CFrame = CFrame.new(c.x, y + h / 2 - 0.2, c.z + cz) * CFrame.Angles(0, c.yaw, 0)
        p.Anchored, p.CanCollide, p.CanTouch, p.CanQuery, p.CastShadow = true, true, false, false, false
        p.Transparency = 1
        p:SetAttribute("IsCaveCollider", true)
        p.Parent = folder
    end
    folder.Parent = parent
end

-- BD-292: readable station text on a sign mesh: one SurfaceGui on the front face only, one TextLabel (FredokaOne, TextScaled) with the
-- HubSignCopy word. Cream text with a dark outline so it reads on the stone and in the warm light.
local function signLabel(text: string, inset: number): TextLabel
    local label = Instance.new("TextLabel")
    label.Name = "Word"
    label.AnchorPoint = Vector2.new(0.5, 0.5)
    label.Position = UDim2.fromScale(0.5, 0.5)
    label.Size = UDim2.fromScale(1 - inset * 2, 0.55)
    label.BackgroundTransparency = 1
    label.Font = Enum.Font.FredokaOne
    label.Text = text
    label.TextScaled = true
    label.TextColor3 = Color3.fromRGB(255, 240, 205)
    label.TextStrokeColor3 = Color3.fromRGB(70, 40, 28)
    label.TextStrokeTransparency = 0.15
    return label
end

-- BD-292 + OWNER 2026-10-16: readable station text on a sign mesh from EVERY side: a SurfaceGui on the front face, one on the back
-- face, and a small BillboardGui word above the sign for the side angles (HubSignCopy word, cream with a dark outline, self-lit).
local function addSignText(mesh: MeshPart, key: string, text: string)
    local cfg = (Props.SignText :: any)[key]
    for _, face in {cfg.face, cfg.back} do
        local gui = Instance.new("SurfaceGui")
        gui.Name = if face == cfg.face then "SignText" else "SignTextBack"
        gui.Face = (Enum.NormalId :: any)[face]
        gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
        gui.PixelsPerStud = 40
        -- BD-292: signs are self-lit so the word stays readable in the dim lamp-lit cave (docs/114 s6.1 cave band 0.15-0.35)
        gui.LightInfluence = Props.SignLightInfluence
        gui.Brightness = Props.SignBrightness
        gui.AlwaysOnTop = false
        gui.ClipsDescendants = true
        signLabel(text, cfg.inset).Parent = gui
        gui.Parent = mesh
    end
    local b = Props.SignBillboard
    local board = Instance.new("BillboardGui")
    board.Name = "SignBillboard"
    board.Size = UDim2.fromOffset(b.width, b.height)
    board.StudsOffsetWorldSpace = Vector3.new(0, mesh.Size.Y / 2 + b.lift, 0)
    board.MaxDistance = b.maxDistance
    board.AlwaysOnTop = false
    board.LightInfluence = Props.SignLightInfluence
    board.Brightness = b.brightness
    signLabel(text, 0).Parent = board
    board.Parent = mesh
end

local function place(folder: Folder, params: RaycastParams, p: any, template: MeshPart, src: any)
    local key = p.key
    local target = {p.w, p.h, p.d}
    local mesh = template:Clone()
    local f = Props.fitFactor({template.Size.X, template.Size.Y, template.Size.Z}, target)
    mesh.Size = template.Size * f
    local cz = Layout.CenterZ
    local x, z = p.x, p.z + cz
    local yaw = p.yaw
    local h = mesh.Size.Y
    local y: number
    if key == "cave_stalactite" then
        y = ceilingAt(params, x, z) + 1.0 - h / 2 -- top buried 1 stud in the real ceiling surface (BD-384: no floating cones)
    elseif key == "cave_moss_hang" then
        -- BD-296 dressing: a vine curtain drapes on its jamb facing the wall's own inward direction (row.face, yaw from the layout)
        y = floorAt(params, x, z) + Props.HangBottom + h / 2
    elseif key == "cave_stepping_stone" then
        y = Layout.FloorY - 1.0 + h / 2 -- sits in the 2 stud deep basin, top just above the lava surface
    elseif Props.Rim[key] then
        y = floorAt(params, x, z) - 0.5 + h / 2
        yaw = Layout.yawTo(-p.x, -p.z) -- face the Heart
    else
        local sinkFrac = (Props.SinkFrac :: any)[key]
        y = floorAt(params, x, z) - (if sinkFrac then h * sinkFrac else SINK) + h / 2
    end
    mesh.CFrame = CFrame.new(x, y, z) * CFrame.Angles(0, yaw, 0)
    if Props.Solid[key] then mesh.CanCollide, mesh.CanQuery = true, true end
    local warm = (Props.Warm :: any)[src.key] or (Props.Warm :: any)[key]
    if warm then -- BD-285 QA: blue / pink generated rocks -> flat warm basalt
        for _, child in mesh:GetChildren() do
            if child:IsA("SurfaceAppearance") then child:Destroy() end
        end
        mesh.TextureID = "" -- the generated meshes carry their colours in MeshPart.TextureID (found in Studio), not in a SurfaceAppearance
        mesh.Color = Color3.fromRGB(warm.color[1], warm.color[2], warm.color[3])
        mesh.Material = (Enum.Material :: any)[warm.material]
    end
    -- BD-296 dressing: kit foliage / rocks keep their vertex colours (a little darker so island greens sit in the dim cave); glow accents are Neon.
    local kit = if src.kind == "kit" then (Props.Kit :: any)[src.key] else nil
    if kit then mesh.Color = Color3.new(kit.tone[1], kit.tone[2], kit.tone[3]) end
    local glow = if p.glow then (Props.Glow :: any)[key] else nil
    if glow then
        mesh.Material = (Enum.Material :: any)[glow.material]
        if src.kind ~= "kit" then -- textured generated mesh (the amber crystal): flat colour like the shop crystals
            for _, child in mesh:GetChildren() do
                if child:IsA("SurfaceAppearance") then child:Destroy() end
            end
            mesh.TextureID = ""
        end
        mesh.Color = Color3.fromRGB(glow.color[1], glow.color[2], glow.color[3])
        mesh:SetAttribute("Glow", true)
    end
    local text = SignCopy.forRow(key, p.owner)
    if text and signGuis < Props.MaxSignGuis then
        signGuis += 1
        addSignText(mesh, key, text)
    end
    mesh.CastShadow = not p.walk and p.owner ~= "dress" -- BD-398: rocks and stalls cast shadows from the lamps and shafts; flat walk-over pieces and the tiny dressing do not need to
    mesh:SetAttribute("Owner", p.owner)
    mesh.Parent = folder
end

function CaveProps.build(parent: Instance): Folder
    local folder = Instance.new("Folder")
    folder.Name = "CaveProps"
    signGuis = 0
    folder:SetAttribute("PropsPlaced", 0)
    folder:SetAttribute("PropsSkipped", 0)
    folder:SetAttribute("AssetsFailed", 0)
    folder:SetAttribute("Done", false)
    folder.Parent = parent
    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances = {workspace.Terrain}
    buildColliders(folder, params)

    task.spawn(function()
        local L = Layout.get()
        -- one load per distinct source (a published model, a Blender ground prop once uploaded, or a kit mesh): a layout key resolves to its first
        -- available source (CaveHubProps.sourceFor); a key with none (the log / stump before the owner uploads them) places nothing
        local kitKeys = kitKeySet()
        local sources: {[string]: any} = {}
        local keys: {string} = {}
        local rowSource: {[string]: any} = {}
        for _, p in L.props do
            if rowSource[p.key] == nil then
                local src = Props.sourceFor(p.key, GeneratedMeshes.Props, kitKeys)
                rowSource[p.key] = src or false
                if src then
                    local id = src.kind .. ":" .. src.key
                    if not sources[id] then
                        sources[id] = src
                        keys[#keys + 1] = id
                    end
                end
            end
        end
        local templates: {[string]: MeshPart} = {}
        local nextKey, active, failed = 1, 0, 0
        local function worker()
            while nextKey <= #keys do
                local id = keys[nextKey]
                nextKey += 1
                local src = sources[id]
                local ok, result
                if src.kind == "kit" then
                    ok, result = pcall(loadKit, src.key, (KitMeshes :: any)[src.key])
                else
                    ok, result = pcall(loadTemplate, src.key, src.id)
                end
                if ok then templates[id] = result else
                    failed += 1
                    warn("[Be Dino] cave prop " .. src.key .. " (" .. (src.id or (KitMeshes :: any)[src.key].meshId) .. ") unavailable; skipping it: " .. tostring(result))
                end
            end
            active -= 1
        end
        for _ = 1, math.min(LOAD_WORKERS, #keys) do
            active += 1
            task.spawn(worker)
        end
        local deadline = os.clock() + LOAD_DEADLINE
        while active > 0 and os.clock() < deadline do task.wait(0.1) end
        folder:SetAttribute("AssetsFailed", failed)

        local placed, skipped = 0, 0
        for i, p in L.props do
            local src = rowSource[p.key]
            local template = if src then templates[src.kind .. ":" .. src.key] else nil
            if template and src then
                local ok, err = pcall(place, folder, params, p, template, src)
                if ok then placed += 1 else skipped += 1 warn("[Be Dino] cave prop " .. p.key .. " not placed: " .. tostring(err)) end
            else
                skipped += 1
            end
            if i % PLACE_BATCH == 0 then task.wait() end
        end
        folder:SetAttribute("PropsPlaced", placed)
        folder:SetAttribute("PropsSkipped", skipped)
        folder:SetAttribute("SignTexts", signGuis)
        folder:SetAttribute("Done", true)
    end)
    return folder
end

return CaveProps
