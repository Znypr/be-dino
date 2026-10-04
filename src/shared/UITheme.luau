--!strict
local TweenService = game:GetService("TweenService")
local Tiles = require(script.Parent.IconTiles)
local Theme = {}
Theme.BackgroundImageId = ""
Theme.MotionEnabled = true
Theme.Colors = {panel=Color3.fromRGB(42,40,53),card=Color3.fromRGB(61,58,73),outline=Color3.fromRGB(13,15,20),text=Color3.new(1,1,1),accent=Color3.fromRGB(93,237,31),gold=Color3.fromRGB(255,210,43),blue=Color3.fromRGB(46,206,255),purple=Color3.fromRGB(194,86,255),red=Color3.fromRGB(247,57,48)}
Theme.ImageIds = {}
function Theme.imageContent(_id: string): Content? return nil end
function Theme.decorate(object: GuiObject, radius: number)
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(0,radius)
    corner.Parent = object
    local border = Instance.new("UIStroke")
    border.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
    border.Color, border.Thickness, border.Parent = Theme.Colors.outline,3,object
    local gradient = Instance.new("UIGradient")
    gradient.Color = ColorSequence.new(Color3.new(1,1,1),Color3.fromRGB(157,168,185))
    gradient.Rotation, gradient.Parent = 90,object
    if object:IsA("TextButton") then
        object.Font, object.TextStrokeColor3, object.TextStrokeTransparency = Enum.Font.FredokaOne,Theme.Colors.outline,0
        local scale = Instance.new("UIScale")
        scale.Parent = object
        local function animate(value: number)
            TweenService:Create(scale,TweenInfo.new(if Theme.MotionEnabled then .12 else 0),{Scale=value*(object:GetAttribute("UIScaleBase") or 1)}):Play()
        end
        object.MouseEnter:Connect(function() animate(1.04) end)
        object.MouseLeave:Connect(function() animate(1) end)
        object.MouseButton1Down:Connect(function() animate(.94) end)
        object.MouseButton1Up:Connect(function() animate(1.04) end)
    end
end
function Theme.texture(parent: GuiObject, width: number, height: number)
    local pattern = Instance.new("Frame")
    pattern.Name,pattern.Size,pattern.BackgroundTransparency,pattern.ClipsDescendants = "FossilTexture",UDim2.fromScale(1,1),1,true
    pattern.ZIndex,pattern.Parent = parent.ZIndex,parent
    for x=8,width,24 do for y=8,height,24 do
        local stud = Instance.new("Frame")
        stud.Position,stud.Size = UDim2.fromOffset(x,y),UDim2.fromOffset(7,7)
        stud.BackgroundColor3,stud.BackgroundTransparency,stud.BorderSizePixel = Color3.new(1,1,1),.95,0
        stud.ZIndex,stud.Parent = parent.ZIndex,pattern
        local edge = Instance.new("UIStroke")
        edge.Color,edge.Transparency,edge.Thickness,edge.Parent = Color3.new(0,0,0),.85,1,stud
    end end
end
-- Quantized exported PNG pixels rendered as merged native GUI tiles. No restricted image API.
function Theme.icon(parent: GuiObject,id: string): Frame?
    local uploaded = Theme.ImageIds[id]
    if uploaded and uploaded ~= "" then
        local root = Instance.new("Frame")
        root.Name,root.BackgroundTransparency,root.Size = "Art_"..id,1,UDim2.fromOffset(42,42)
        root.Position,root.ZIndex,root.Parent = UDim2.fromOffset(8,5),parent.ZIndex+1,parent
        local image = Instance.new("ImageLabel")
        image.Image,image.Size,image.BackgroundTransparency,image.ZIndex,image.Parent = uploaded,UDim2.fromScale(1,1),1,root.ZIndex,root
        return root
    end
    local data = Tiles[id]
    if not data then return nil end
    local root = Instance.new("Frame")
    root.Name,root.BackgroundTransparency,root.Size = "Art_"..id,1,UDim2.fromOffset(42,42)
    root.Position,root.ZIndex,root.Parent = UDim2.fromOffset(8,5),parent.ZIndex+1,parent
    for _, tile in data.tiles do
        local pixel = Instance.new("Frame")
        pixel.BorderSizePixel = 0
        pixel.Position = UDim2.fromScale(tile[1]/data.size,tile[2]/data.size)
        pixel.Size = UDim2.fromScale(tile[3]/data.size,tile[4]/data.size)
        local c = data.colors[tile[5]]
        pixel.BackgroundColor3 = Color3.fromRGB(c[1],c[2],c[3])
        pixel.ZIndex,pixel.Parent = root.ZIndex,root
    end
    return root
end
return Theme
