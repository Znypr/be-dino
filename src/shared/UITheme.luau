--!strict
local TweenService = game:GetService("TweenService")
local UITheme = {}
UITheme.Colors = {
    panel = Color3.fromRGB(26, 52, 65),
    card = Color3.fromRGB(38, 72, 86),
    outline = Color3.fromRGB(12, 33, 45),
    text = Color3.fromRGB(250, 248, 230),
    accent = Color3.fromRGB(102, 203, 161),
    gold = Color3.fromRGB(247, 196, 96),
}
-- Upload resources/ui/icons/*.png, then set these logical icon IDs.
UITheme.ImageIds = {home = "", dinos = "", egg = "", leaf = "", amber = "", close = ""}
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
    if not imageId or imageId == "" then return nil end
    local icon = Instance.new("ImageLabel")
    icon.Size = UDim2.fromOffset(30,30)
    icon.Position = UDim2.fromOffset(8,7)
    icon.BackgroundTransparency = 1
    icon.Image = imageId
    icon.ZIndex = parent.ZIndex + 1
    icon.Parent = parent
    return icon
end
return UITheme
