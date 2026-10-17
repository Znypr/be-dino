--!strict
-- Native vector potion icons (docs/68). No image assets and no symbol on the glass:
-- the effect family sets the bottle SHAPE and liquid colour, the rarity sets cork, trim, glow and pip count.
local PotionArt = {}
PotionArt.Rarities = {"Common","Uncommon","Rare","Epic","Legendary"}
PotionArt.RarityColor = {
    Common=Color3.fromRGB(176,188,200), Uncommon=Color3.fromRGB(93,237,31), Rare=Color3.fromRGB(46,206,255),
    Epic=Color3.fromRGB(194,86,255), Legendary=Color3.fromRGB(255,210,43),
}
-- body = {x,y,w,h}, neck = {x,w,top,height}, corner = body corner radius (scale), all fractions of the 42x42 root.
PotionArt.Shapes = {
    speed={body={.30,.34,.40,.52}, neck={.40,.20,.14,.22}, corner=.5, liquid=Color3.fromRGB(64,214,255)}, -- tall slim flask, cyan
    growth={body={.18,.42,.64,.46}, neck={.38,.24,.20,.24}, corner=1, liquid=Color3.fromRGB(98,236,112)}, -- round flask, green
    loot={body={.16,.48,.68,.38}, neck={.30,.40,.30,.20}, corner=.3, liquid=Color3.fromRGB(255,170,48)}, -- wide squat jar, amber
}
local function frame(parent: GuiObject, name: string, x: number, y: number, w: number, h: number, color: Color3, z: number, corner: number?, transparency: number?)
    local f = Instance.new("Frame")
    f.Name, f.BackgroundColor3, f.BorderSizePixel, f.ZIndex = name, color, 0, z
    f.BackgroundTransparency = transparency or 0
    f.Position, f.Size = UDim2.fromScale(x,y), UDim2.fromScale(w,h)
    if corner then
        local c = Instance.new("UICorner")
        c.CornerRadius, c.Parent = UDim.new(corner,0), f
    end
    f.Parent = parent
    return f
end
local function stroke(parent: GuiObject, color: Color3, thickness: number)
    local s = Instance.new("UIStroke")
    s.Color, s.Thickness, s.Parent = color, thickness, parent
    return s
end
-- Owner 2026-10-16: 2D glossy glass icons drawn by the owner (ChatGPT), keyed "<kind>_<rarity lowercase>" = potion id.
-- BD-101 2026-10-17: the ids live in AssetSlots.Images.potion_icon_<id> (tools/bind_assets.py slots, 512 px uploads).
-- An empty or malformed slot is left out, so the code-drawn vector flask below stays as the fallback for that potion.
local AssetSlots = require(script.Parent.AssetSlots)
PotionArt.Images = {} :: {[string]: string}
for _, id in {"speed_common","growth_common","loot_common","speed_uncommon","growth_uncommon","speed_rare","growth_rare","loot_rare",
    "growth_epic","loot_epic","speed_legendary","growth_legendary"} do
    local uri = (AssetSlots.Images :: {[string]: string})["potion_icon_" .. id]
    if uri and string.match(uri, "^rbxassetid://%d+$") then PotionArt.Images[id] = uri end
end
-- Image uri for a potion id ("speed_common"), or nil when no valid id is bound (callers keep the code bottle).
function PotionArt.imageFor(potionId: string): string?
    return PotionArt.Images[potionId]
end
-- Small plain icon (inventory buttons, active-potion chips). ScaleType Fit, never stretched. Returns nil without an id.
function PotionArt.icon(parent: GuiObject, potionId: string, size: UDim2, position: UDim2, z: number): ImageLabel?
    local uri = PotionArt.Images[potionId]
    if not uri then return nil end
    local image = Instance.new("ImageLabel")
    image.Name, image.Image, image.BackgroundTransparency = "PotionIcon", uri, 1
    image.ScaleType, image.AnchorPoint = Enum.ScaleType.Fit, Vector2.new(0, .5)
    image.Size, image.Position, image.ZIndex, image.Parent = size, position, z, parent
    return image
end
PotionArt.UseModels = false -- dormant BD-214 3D path; keep false
-- BD-214 (dormant): textured 3D models (Roblox generate_mesh, docs/77). The server caches stripped copies in
-- ReplicatedStorage.PotionModels (Server/PotionModels); the vector flask above stays as the fallback.
PotionArt.ModelAssets = {flask=114182681867384, jar=121478365783622, heart=126942715659365, claw=100441458834806}
PotionArt.ReduceMotion = false
function PotionArt.modelFor(kind: string, rarity: string): string
    if rarity == "Legendary" then return "claw" end
    return if kind == "loot" then "jar" elseif kind == "growth" then "heart" else "flask"
end
local spinning: {[Camera]: {focus: Vector3, dist: number, angle: number}} = setmetatable({}, {__mode = "k"}) :: any
local spinConnection: RBXScriptConnection? = nil
local function place(camera: Camera, s)
    local eye = s.focus + Vector3.new(math.sin(s.angle) * s.dist, s.dist * .12, math.cos(s.angle) * s.dist)
    camera.CFrame = CFrame.lookAt(eye, s.focus)
end
local function spin(dt: number)
    local any = false
    for camera, s in spinning do
        if camera.Parent and camera:IsDescendantOf(game) then
            any = true
            s.angle += dt * .6
            place(camera, s)
        else spinning[camera] = nil end
    end
    if not any and spinConnection then spinConnection:Disconnect() spinConnection = nil end
end
local function mountModel(root: GuiObject, source: Model, tier: number, trim: Color3): boolean
    local view = Instance.new("ViewportFrame")
    view.Name, view.BackgroundTransparency, view.Size, view.ZIndex = "PotionModel", 1, UDim2.fromScale(1, 1), root.ZIndex + 4
    view.Ambient, view.LightColor, view.LightDirection = Color3.fromRGB(170,170,180), Color3.new(1,1,1), Vector3.new(-1,-1,-.6)
    local model = source:Clone()
    model.Parent = view
    local cf, size = model:GetBoundingBox()
    local radius = math.max(size.X, size.Y, size.Z) * .5
    if radius <= 0 then view:Destroy() return false end
    local camera = Instance.new("Camera")
    camera.FieldOfView, camera.Parent = 40, view
    view.CurrentCamera = camera
    local s = {focus = cf.Position, dist = radius / math.tan(math.rad(20)) * 1.15, angle = .5}
    place(camera, s)
    view.Parent = root
    -- Hide the vector flask but keep the rarity glow plate and pips (docs/88 tier frame).
    for _, child in root:GetChildren() do
        if child:IsA("GuiObject") and (child.Name == "Neck" or child.Name == "Glass" or child.Name == "Cork") then child.Visible = false end
    end
    if tier >= 4 then view.ImageColor3 = Color3.new(1,1,1):Lerp(trim, .08) end
    if not PotionArt.ReduceMotion then
        spinning[camera] = s
        if not spinConnection then spinConnection = game:GetService("RunService").Heartbeat:Connect(spin) end
    end
    return true
end
function PotionArt.attachModel(root: GuiObject, kind: string, rarity: string)
    local ReplicatedStorage = game:GetService("ReplicatedStorage")
    local key = PotionArt.modelFor(kind, rarity)
    local tier = PotionArt.rarityIndex(rarity)
    local trim = PotionArt.RarityColor[rarity] or PotionArt.RarityColor.Common
    local function try(): boolean
        local folder = ReplicatedStorage:FindFirstChild("PotionModels")
        local source = folder and folder:FindFirstChild(key)
        if source and source:IsA("Model") then local ok, mounted = pcall(mountModel, root, source, tier, trim) return ok and mounted == true end
        return false
    end
    if try() then return end
    task.spawn(function() -- models stream in after the server loads them; give up quietly (flask stays) after 15 s
        for _ = 1, 30 do
            task.wait(.5)
            if not root.Parent then return end
            if try() then return end
        end
    end)
end
local bobbing: {[ImageLabel]: number} = setmetatable({}, {__mode = "k"}) :: any
local bobConnection: RBXScriptConnection? = nil
local function bob()
    local t, any = os.clock(), false
    for image, phase in bobbing do
        if image.Parent and image:IsDescendantOf(game) then
            any = true
            image.Position = UDim2.fromScale(.5, .46 + math.sin(t * 1.6 + phase) * .015)
        else bobbing[image] = nil end
    end
    if not any and bobConnection then bobConnection:Disconnect() bobConnection = nil end
end
-- Image sits above the rarity glow but below the pips, so the tier frame stays readable.
function PotionArt.attachImage(root: GuiObject, uri: string, z: number, flask: {GuiObject})
    local image = Instance.new("ImageLabel")
    image.Name, image.Image, image.BackgroundTransparency = "PotionImage", uri, 1
    image.ScaleType, image.AnchorPoint = Enum.ScaleType.Fit, Vector2.new(.5, .5)
    image.Position, image.Size, image.ZIndex = UDim2.fromScale(.5, .46), UDim2.fromScale(.9, .84), z + 2
    image.Parent = root
    for _, part in flask do part.Visible = false end
    if game == nil or not game:GetService("RunService"):IsClient() then return end
    task.spawn(function() -- fallback: show the vector flask again if the image never loads
        local ContentProvider = game:GetService("ContentProvider")
        local ok = pcall(function() ContentProvider:PreloadAsync({image}) end)
        if not root.Parent then return end
        if not ok or not image.IsLoaded then
            for _ = 1, 20 do if image.IsLoaded or not root.Parent then break end task.wait(.5) end
        end
        if root.Parent and not image.IsLoaded then
            image.Visible = false
            for _, f in flask do f.Visible = true end
        end
    end)
    if not PotionArt.ReduceMotion then
        bobbing[image] = math.random() * 6
        if not bobConnection then bobConnection = game:GetService("RunService").Heartbeat:Connect(bob) end
    end
end
function PotionArt.rarityIndex(rarity: string): number
    return table.find(PotionArt.Rarities, rarity) or 1
end
function PotionArt.build(root: GuiObject, kind: string, rarity: string)
    local shape = PotionArt.Shapes[kind] or PotionArt.Shapes.speed
    local tier = PotionArt.rarityIndex(rarity)
    local trim = PotionArt.RarityColor[rarity] or PotionArt.RarityColor.Common
    local z = root.ZIndex + 1
    -- Glow plate: invisible for Common, strengthening each tier; Epic/Legendary get a bright rim.
    local glow = frame(root, "RarityGlow", .02, .02, .96, .96, trim, z, .3, if tier == 1 then 1 else 0.9 - tier * .1)
    if tier >= 4 then stroke(glow, trim, tier - 2) end
    local b, n = shape.body, shape.neck
    local neck = frame(root, "Neck", n[1], n[3], n[2], n[4] + .06, Color3.fromRGB(214,238,246), z + 1, .2, .25)
    local body = frame(root, "Glass", b[1], b[2], b[3], b[4], Color3.fromRGB(214,238,246), z + 1, shape.corner, .25)
    stroke(body, trim, if tier >= 3 then 2 else 1)
    -- Liquid fills the lower 65% of the body, clipped by matching corners.
    frame(body, "Liquid", .06, .35, .88, .59, shape.liquid, z + 2, shape.corner, .05)
    frame(body, "Shine", .14, .14, .12, .3, Color3.new(1,1,1), z + 3, 1, .45)
    local cork = frame(root, "Cork", n[1] - .02, n[3] - .06, n[2] + .04, .1, trim, z + 3, .35)
    -- Pips (1 per tier) make rarity readable without colour.
    for i = 1, tier do
        frame(root, "Pip", .5 + (i - (tier + 1) / 2) * .11 - .03, .92, .06, .06, trim, z + 3, 1)
    end
    local uri = PotionArt.Images[kind .. "_" .. string.lower(rarity)]
    if uri then PotionArt.attachImage(root, uri, z, {neck, body, cork}) end
    if PotionArt.UseModels and game ~= nil and game:GetService("RunService"):IsClient() then PotionArt.attachModel(root, kind, rarity) end
    return neck
end
return PotionArt
