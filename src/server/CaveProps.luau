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
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Layout = require(ReplicatedStorage.Shared.CaveHubLayout)
local Props = require(ReplicatedStorage.Shared.CaveHubProps)
local SignCopy = require(ReplicatedStorage.Shared.HubSignCopy)
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

-- Terrain surface height below (x, z): a raycast against Terrain only, falling back to the layout's floor height.
local function floorAt(params: RaycastParams, x: number, z: number): number
    local hit = workspace:Raycast(Vector3.new(x, Layout.FloorY + 30, z), Vector3.new(0, -60, 0), params)
    if hit and math.abs(hit.Position.Y - Layout.FloorY) < 6 then return hit.Position.Y end
    return Layout.floorHeight(x, z)
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
local function addSignText(mesh: MeshPart, key: string, text: string)
    local cfg = (Props.SignText :: any)[key]
    local gui = Instance.new("SurfaceGui")
    gui.Name = "SignText"
    gui.Face = (Enum.NormalId :: any)[cfg.face]
    gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
    gui.PixelsPerStud = 40
    gui.LightInfluence = 0.6
    gui.AlwaysOnTop = false
    gui.ClipsDescendants = true
    local label = Instance.new("TextLabel")
    label.Name = "Word"
    label.AnchorPoint = Vector2.new(0.5, 0.5)
    label.Position = UDim2.fromScale(0.5, 0.5)
    label.Size = UDim2.fromScale(1 - cfg.inset * 2, 0.4)
    label.BackgroundTransparency = 1
    label.Font = Enum.Font.FredokaOne
    label.Text = text
    label.TextScaled = true
    label.TextColor3 = Color3.fromRGB(255, 240, 205)
    label.TextStrokeColor3 = Color3.fromRGB(70, 40, 28)
    label.TextStrokeTransparency = 0.15
    label.Parent = gui
    gui.Parent = mesh
end

local function place(folder: Folder, params: RaycastParams, p: any, template: MeshPart)
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
        y = Layout.ceilingY(p.x, p.z + cz) + 1.5 - h / 2 -- top buried in the ceiling
    elseif key == "cave_moss_hang" then
        y = floorAt(params, x, z) + 7 + h / 2
        yaw = Layout.yawTo(-p.x, -p.z)
    elseif key == "cave_stepping_stone" then
        y = Layout.FloorY - 1.0 + h / 2 -- sits in the 2 stud deep basin, top just above the lava surface
    elseif Props.Rim[key] then
        y = floorAt(params, x, z) - 0.5 + h / 2
        yaw = Layout.yawTo(-p.x, -p.z) -- face the Heart
    else
        y = floorAt(params, x, z) - SINK + h / 2
    end
    mesh.CFrame = CFrame.new(x, y, z) * CFrame.Angles(0, yaw, 0)
    if Props.Solid[key] then mesh.CanCollide, mesh.CanQuery = true, true end
    local warm = (Props.Warm :: any)[key]
    if warm then -- BD-285 QA: blue / pink generated rocks -> flat warm basalt
        for _, child in mesh:GetChildren() do
            if child:IsA("SurfaceAppearance") then child:Destroy() end
        end
        mesh.Color = Color3.fromRGB(warm.color[1], warm.color[2], warm.color[3])
        mesh.Material = (Enum.Material :: any)[warm.material]
    end
    local text = SignCopy.forRow(key, p.owner)
    if text and signGuis < Props.MaxSignGuis then
        signGuis += 1
        addSignText(mesh, key, text)
    end
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
        -- one load per distinct asset id
        local keys: {string} = {}
        local seen: {[string]: boolean} = {}
        for _, p in L.props do
            if not seen[p.key] then
                seen[p.key] = true
                if Props.assetId(p.key) then keys[#keys + 1] = p.key end
            end
        end
        local templates: {[string]: MeshPart} = {}
        local nextKey, active, failed = 1, 0, 0
        local function worker()
            while nextKey <= #keys do
                local key = keys[nextKey]
                nextKey += 1
                local id = Props.assetId(key) :: string
                local ok, result = pcall(loadTemplate, key, id)
                if ok then templates[key] = result else
                    failed += 1
                    warn("[Be Dino] cave prop " .. key .. " (" .. id .. ") unavailable; skipping it: " .. tostring(result))
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
            local template = templates[p.key]
            if template then
                local ok, err = pcall(place, folder, params, p, template)
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
