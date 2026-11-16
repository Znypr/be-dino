--!strict
-- BD-1221 (Config.PlazaHubEnabled, Shared/PlazaHubLayout): four stalls with big signs on the World V3 spawn plaza. Server side only places
-- the meshes (the cave home's own generated props, loaded by id like CaveProps), one hidden box collider per big piece, the sign words and
-- one invisible prompt anchor per stall (attribute PlazaStation / PlazaScreen); src/client/PlazaHub.client.luau adds the walk-up prompts.
-- Built in the background after the island props; a failed load skips that piece (nothing is ever code-built in its place).
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Layout = require(Shared.PlazaHubLayout)
local Props = require(Shared.CaveHubProps)
local SignCopy = require(Shared.HubSignCopy)
local Island = require(Shared.IslandLayout)

local PlazaHub = {}

local function loadTemplate(key: string): MeshPart?
    local id = Props.assetId(key)
    if not id then return nil end
    local ok, container = pcall(function() return InsertService:LoadAsset(tonumber(id) :: number) end)
    if not ok or not container then return nil end
    local found: MeshPart? = nil
    for _, item in container:GetDescendants() do
        if item:IsA("MeshPart") then found = item break end
    end
    local mesh = if found then found:Clone() else nil
    container:Destroy()
    if not mesh then return nil end
    for _, child in mesh:GetChildren() do
        if not child:IsA("SurfaceAppearance") then child:Destroy() end
    end
    mesh.Name = key
    mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.Massless = true, false, false, false, true
    mesh:SetAttribute("GeneratedAssetId", id)
    return mesh
end

-- The sign word on both faces plus a small word above the board (same look as the cave signs, BD-292), sunlit outdoors.
local function signWord(text: string, inset: number): TextLabel
    local label = Instance.new("TextLabel")
    label.Name, label.AnchorPoint, label.Position = "Word", Vector2.new(.5, .5), UDim2.fromScale(.5, .5)
    label.Size, label.BackgroundTransparency = UDim2.fromScale(1 - inset * 2, .55), 1
    label.Font, label.Text, label.TextScaled = Enum.Font.FredokaOne, text, true
    label.TextColor3, label.TextStrokeColor3, label.TextStrokeTransparency = Color3.fromRGB(255, 240, 205), Color3.fromRGB(70, 40, 28), .15
    return label
end
local function addSignText(mesh: MeshPart, text: string)
    local cfg = (Props.SignText :: any)[Layout.Sign.key]
    for _, face in {cfg.face, cfg.back} do
        local gui = Instance.new("SurfaceGui")
        gui.Name = if face == cfg.face then "SignText" else "SignTextBack"
        gui.Face = (Enum.NormalId :: any)[face]
        gui.SizingMode, gui.PixelsPerStud = Enum.SurfaceGuiSizingMode.PixelsPerStud, 24
        gui.LightInfluence, gui.Brightness, gui.ClipsDescendants = 0, 1.2, true
        signWord(text, cfg.inset).Parent = gui
        gui.Parent = mesh
    end
    local b = Props.SignBillboard
    local board = Instance.new("BillboardGui")
    board.Name, board.Size = "SignBillboard", UDim2.fromOffset(b.width * 1.5, b.height * 1.5)
    board.StudsOffsetWorldSpace = Vector3.new(0, mesh.Size.Y / 2 + b.lift * 2, 0)
    board.MaxDistance, board.AlwaysOnTop, board.LightInfluence, board.Brightness = 160, false, 0, 1.2
    signWord(text, 0).Parent = board
    board.Parent = mesh
end

local function put(folder: Instance, template: MeshPart, size: {number}, x: number, z: number, yaw: number, solid: boolean?): MeshPart
    local mesh = template:Clone()
    mesh.Size = template.Size * Props.fitFactor({template.Size.X, template.Size.Y, template.Size.Z}, size)
    local y = Island.height(x, z) - .15 + mesh.Size.Y / 2
    mesh.CFrame = CFrame.new(x, y, z) * CFrame.Angles(0, yaw, 0)
    mesh.Parent = folder
    if solid then
        local box = Instance.new("Part")
        box.Name, box.Anchored, box.Transparency, box.CanCollide, box.CanQuery, box.CanTouch = template.Name .. "_Collider", true, 1, true, true, false
        box.Size = Vector3.new(mesh.Size.X * .8, mesh.Size.Y, mesh.Size.Z * .8)
        box.CFrame = mesh.CFrame
        box.Parent = folder
    end
    return mesh
end

-- Returns the folder at once; the meshes arrive as their assets load.
function PlazaHub.build(parent: Instance, centerX: number, centerZ: number): Folder
    local folder = Instance.new("Folder")
    folder.Name, folder.Parent = "PlazaHub", parent
    task.spawn(function()
        local keys: {[string]: boolean} = {[Layout.Sign.key] = true}
        for _, stall in Layout.Stalls do for _, p in stall.props do keys[p.key] = true end end
        local templates: {[string]: MeshPart} = {}
        for key in keys do
            local t = loadTemplate(key)
            if t then templates[key] = t end
        end
        local placed = 0
        for _, stall in Layout.Stalls do
            local group = Instance.new("Model")
            group.Name = "Stall_" .. stall.station
            for _, p in stall.props do
                local t = templates[p.key]
                if t then
                    local x, z, yaw = Layout.place(stall, p.at, centerX, centerZ)
                    put(group, t, p.size, x, z, yaw + math.rad(p.yaw or 0), p.solid)
                    placed += 1
                end
            end
            local sign = templates[Layout.Sign.key]
            local word = SignCopy.sign(stall.station)
            if sign and word then
                local x, z, yaw = Layout.place(stall, Layout.Sign.at, centerX, centerZ)
                addSignText(put(group, sign, Layout.Sign.size, x, z, yaw + math.rad(Layout.Sign.yaw or 0)), word)
                placed += 1
            end
            local px, pz = Layout.place(stall, Layout.PromptAt, centerX, centerZ)
            local anchor = Instance.new("Part")
            anchor.Name, anchor.Anchored, anchor.Transparency, anchor.Size = "PlazaPrompt", true, 1, Vector3.new(1, 1, 1)
            anchor.CanCollide, anchor.CanQuery, anchor.CanTouch = false, false, false
            anchor.Position = Vector3.new(px, Island.height(px, pz) + 3, pz)
            anchor:SetAttribute("PlazaStation", stall.station)
            anchor:SetAttribute("PlazaScreen", stall.screen)
            anchor.Parent = group
            group.Parent = folder
        end
        for _, t in templates do t:Destroy() end
        folder:SetAttribute("Placed", placed)
    end)
    return folder
end

return PlazaHub
