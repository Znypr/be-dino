--!strict
local TweenService = game:GetService("TweenService")
local AssetService = game:GetService("AssetService")
local IconRaster = require(script.Parent.IconRaster)
local imageCache = {}
local UITheme = {}
UITheme.BackgroundImageId = "" -- optional permanent upload of resources/ui/backgrounds/prehistoric-island.png
function UITheme.imageContent(id: string): Content?
    if imageCache[id] == false then return nil end
    if imageCache[id] then return Content.fromObject(imageCache[id]) end
    local runs = IconRaster[id]
    if not runs then return nil end
    local ok, image = pcall(function()
        local editable = AssetService:CreateEditableImage({Size = Vector2.new(64,64)})
        if not editable then error("Image memory unavailable") end
        local pixels = buffer.create(64*64*4)
        local offset = 0
        for i = 1, #runs, 2 do
            for _ = 1, runs[i] do buffer.writeu32(pixels,offset,runs[i+1]) offset += 4 end
        end
        editable:WritePixelsBuffer(Vector2.zero, Vector2.new(64,64), pixels)
        return editable
    end)
    if not ok then imageCache[id] = false return nil end
    imageCache[id] = image
    return Content.fromObject(image)
end
UITheme.Colors = {
    panel = Color3.fromRGB(49, 94, 110),
    card = Color3.fromRGB(55, 104, 122),
    outline = Color3.fromRGB(16, 42, 56),
    text = Color3.fromRGB(250, 248, 230),
    accent = Color3.fromRGB(102, 203, 161),
    gold = Color3.fromRGB(247, 196, 96),
}
-- Upload resources/ui/icons/*.png, then set these logical icon IDs.
UITheme.ImageIds = {home = "", dinos = "", egg = "", leaf = "", amber = "", close = "", settings = "", shop = "", play = "", lock = "", trophy = "", gift = "", bolt = "", snow = ""}
function UITheme.decorate(object: GuiObject, radius: number)
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(0, radius)
    corner.Parent = object
    local stroke = Instance.new("UIStroke")
    stroke.Color = UITheme.Colors.outline
    stroke.Thickness = 2
    stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
    stroke.Parent = object
    local gradient = Instance.new("UIGradient")
    gradient.Rotation = 90
    gradient.Color = ColorSequence.new(Color3.fromRGB(255,255,255), Color3.fromRGB(184,206,215))
    gradient.Parent = object
    if object:IsA("TextButton") then
        local scale = Instance.new("UIScale")
        scale.Parent = object
        object.MouseEnter:Connect(function()
            TweenService:Create(scale, TweenInfo.new(.12), {Scale = 1.03}):Play()
        end)
        object.MouseLeave:Connect(function()
            TweenService:Create(scale, TweenInfo.new(.12), {Scale = 1}):Play()
        end)
        object.MouseButton1Down:Connect(function()
            TweenService:Create(scale, TweenInfo.new(.08), {Scale = .96}):Play()
        end)
        object.MouseButton1Up:Connect(function()
            TweenService:Create(scale, TweenInfo.new(.12), {Scale = 1}):Play()
        end)
    end
end
function UITheme.icon(parent: GuiObject, id: string): ImageLabel?
    local imageId = UITheme.ImageIds[id]
    local content = if not imageId or imageId == "" then UITheme.imageContent(id) else nil
    if (not imageId or imageId == "") and not content then return nil end
    local icon = Instance.new("ImageLabel")
    icon.Size = UDim2.fromOffset(30,30)
    icon.Position = UDim2.fromOffset(8,7)
    icon.BackgroundTransparency = 1
    if content then icon.ImageContent = content else icon.Image = imageId end
    icon.ZIndex = parent.ZIndex + 1
    icon.Parent = parent
    return icon
end
return UITheme
