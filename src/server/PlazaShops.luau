--!strict
-- BD-1248 (Config.PlazaShopsV2Enabled, Shared/PlazaShopsLayout): the four plaza stalls of BD-1221 as themed shop buildings. Server side
-- places, per shop: ONE generated building MeshPart, one hidden box collider, ONE generated wooden signboard with the shop word and icon as
-- a SurfaceGui on its front face (no BillboardGui, no second label), the invisible prompt anchor (same attributes as PlazaHub, so
-- src/client/PlazaHub.client.luau keeps the walk-up prompts and the "At home" rule) and the shopkeeper spot as attributes on the shop model
-- (src/client/PlazaKeepers.client.luau builds and animates the low-poly dino shopkeepers on the client).
-- Built in the background; a failed load skips that piece (nothing is ever code-built in its place).
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Hub = require(Shared.PlazaHubLayout)
local Layout = require(Shared.PlazaShopsLayout)
local Island = require(Shared.IslandLayout)

local PlazaShops = {}

local function loadTemplate(key: string): MeshPart?
    local asset = (Layout.Assets :: any)[key]
    if not asset then return nil end
    local ok, container = pcall(function() return InsertService:LoadAsset(tonumber(asset.assetId) :: number) end)
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
    mesh:SetAttribute("GeneratedAssetId", asset.assetId)
    return mesh
end

local function iconId(icon: {string}): string?
    local source = icon[1]
    local t: any = if source == "ui" then require(Shared.UIIconAssets)
        elseif source == "slot" then require(Shared.AssetSlots).Images
        elseif source == "art" then require(Shared.ArtworkAssets)
        else nil
    local id = if t then t[icon[2]] else nil
    return if type(id) == "string" and id ~= "" then id else nil
end

local function rgb(c: {number}): Color3
    return Color3.fromRGB(c[1], c[2], c[3])
end

-- The ONE label of a shop: icon + word on the board's front face, game font, thick dark outline, sunlit like the board.
local function signFace(board: MeshPart, shop: any)
    local s = Layout.Sign
    local gui = Instance.new("SurfaceGui")
    gui.Name, gui.Face = "ShopSign", Enum.NormalId.Front
    gui.SizingMode, gui.PixelsPerStud = Enum.SurfaceGuiSizingMode.PixelsPerStud, s.pixelsPerStud
    gui.LightInfluence, gui.Brightness, gui.ClipsDescendants = 0, 1.1, true
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.AnchorPoint = "Row", 1, Vector2.new(.5, .5)
    row.Position, row.Size = UDim2.fromScale(.5, .5), UDim2.fromScale(.9, .84)
    row.Parent = gui
    local list = Instance.new("UIListLayout")
    list.FillDirection, list.HorizontalAlignment, list.VerticalAlignment = Enum.FillDirection.Horizontal, Enum.HorizontalAlignment.Center, Enum.VerticalAlignment.Center
    list.Padding, list.SortOrder = UDim.new(.02, 0), Enum.SortOrder.LayoutOrder
    list.Parent = row
    local id = iconId(shop.icon)
    if id then
        local image = Instance.new("ImageLabel")
        image.Name, image.BackgroundTransparency, image.Image, image.LayoutOrder = "Icon", 1, id, 1
        image.Size, image.ScaleType = UDim2.fromScale(s.iconShare, 1), Enum.ScaleType.Fit
        image.Parent = row
    end
    local word = Instance.new("TextLabel")
    word.Name, word.BackgroundTransparency, word.LayoutOrder = "Word", 1, 2
    word.Size = UDim2.fromScale(if id then .98 - s.iconShare else 1, 1)
    word.Font, word.Text, word.TextScaled = (Enum.Font :: any)[Layout.Font], shop.word, true
    word.TextColor3, word.TextStrokeTransparency = rgb(Layout.WordColor), 1
    word.Parent = row
    local stroke = Instance.new("UIStroke")
    stroke.Color, stroke.Thickness, stroke.LineJoinMode = rgb(Layout.StrokeColor), s.stroke, Enum.LineJoinMode.Round
    stroke.Parent = word
    gui.Parent = board
end

local function frame(stall: any, at: {number}, y: number, centerX: number, centerZ: number): CFrame
    local x, z, yaw = Hub.place(stall, at, centerX, centerZ)
    return CFrame.new(x, Island.height(x, z) - .15 + y, z) * CFrame.Angles(0, yaw, 0)
end

-- Returns the folder at once (named PlazaHub, the client prompts wait for it); the meshes arrive as their assets load.
function PlazaShops.build(parent: Instance, centerX: number, centerZ: number): Folder
    local folder = Instance.new("Folder")
    folder.Name, folder.Parent = "PlazaHub", parent
    folder:SetAttribute("ShopsV2", true)
    task.spawn(function()
        local templates: {[string]: MeshPart} = {}
        for key in Layout.Assets do
            local t = loadTemplate(key)
            if t then templates[key] = t end
        end
        local placed = 0
        for _, stall in Hub.Stalls do
            local shop = Layout.shop(stall.station)
            if not shop then continue end
            local group = Instance.new("Model")
            group.Name = "Shop_" .. stall.station
            local b = shop.building
            local t = templates[b.key]
            if t then
                local mesh = t:Clone()
                mesh.Size = t.Size * Layout.fit({t.Size.X, t.Size.Y, t.Size.Z}, b.size)
                mesh.CFrame = frame(stall, {0, b.z}, mesh.Size.Y / 2, centerX, centerZ)
                mesh.Parent = group
                local box = Instance.new("Part")
                box.Name, box.Anchored, box.Transparency, box.CanCollide, box.CanQuery, box.CanTouch = b.key .. "_Collider", true, 1, true, true, false
                box.Size = Vector3.new(mesh.Size.X * .8, mesh.Size.Y, mesh.Size.Z * .7)
                box.CFrame = mesh.CFrame
                box.Parent = group
                placed += 1
            end
            local board = templates[Layout.Sign.key]
            if board then
                local sign = board:Clone()
                sign.Name = "ShopSign"
                sign.Size = Vector3.new(Layout.Sign.w, Layout.Sign.h, Layout.Sign.d)
                sign.CFrame = frame(stall, {0, shop.sign.z}, shop.sign.y, centerX, centerZ)
                signFace(sign, shop)
                sign.Parent = group
                placed += 1
            end
            local k = shop.keeper
            group:SetAttribute("KeeperSpecies", k.species)
            group:SetAttribute("KeeperHeight", k.height)
            group:SetAttribute("KeeperCFrame", frame(stall, {k.x, k.z}, k.y, centerX, centerZ))
            local px, pz = Hub.place(stall, Hub.PromptAt, centerX, centerZ)
            local anchor = Instance.new("Part")
            anchor.Name, anchor.Anchored, anchor.Transparency, anchor.Size = "PlazaPrompt", true, 1, Vector3.new(1, 1, 1)
            anchor.CanCollide, anchor.CanQuery, anchor.CanTouch = false, false, false
            anchor.Position = Vector3.new(px, Island.height(px, pz) + 3, pz)
            anchor:SetAttribute("PlazaStation", stall.station)
            anchor:SetAttribute("PlazaScreen", stall.screen)
            anchor:SetAttribute("PlazaOneLabel", true) -- the sign is the only label: the prompt shows no object name
            anchor.Parent = group
            group.Parent = folder
        end
        for _, t in templates do t:Destroy() end
        folder:SetAttribute("Placed", placed)
    end)
    return folder
end

return PlazaShops
