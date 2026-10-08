--!strict
local TweenService = game:GetService("TweenService")
local Vectors = require(script.Parent.IconVectors)
local Artwork = require(script.Parent.Artwork)
local Theme = {}
Theme.BackgroundImageId = ""
Theme.MotionEnabled = true
Theme.Colors = {panel=Color3.fromRGB(42,40,53),card=Color3.fromRGB(61,58,73),outline=Color3.fromRGB(13,15,20),text=Color3.new(1,1,1),accent=Color3.fromRGB(93,237,31),gold=Color3.fromRGB(255,210,43),blue=Color3.fromRGB(46,206,255),purple=Color3.fromRGB(194,86,255),red=Color3.fromRGB(247,57,48)}
Theme.ImageIds = require(script.Parent.UIIconAssets)
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
-- Original scalable graphics render sharply at any card size; uploaded original PNGs override them.
local function nativeIcon(parent: GuiObject,id: string): Frame?
    local uploaded = Theme.ImageIds[id]
    if uploaded and uploaded ~= "" then
        local root = Instance.new("Frame")
        root.Name,root.BackgroundTransparency,root.Size = "Art_"..id,1,UDim2.fromOffset(42,42)
        root.Position,root.ZIndex,root.Parent = UDim2.fromOffset(8,5),parent.ZIndex+1,parent
        local image = Instance.new("ImageLabel")
        image.Name,image.ScaleType = id,Enum.ScaleType.Fit
        image.Image,image.Size,image.BackgroundTransparency,image.ZIndex,image.Parent = uploaded,UDim2.fromScale(1,1),1,root.ZIndex,root
        return root
    end
    if id=="amber" then
        local root=Instance.new("Frame")
        root.Name,root.BackgroundTransparency,root.Size="Art_amber",1,UDim2.fromOffset(42,42)
        root.Position,root.ZIndex,root.Parent=UDim2.fromOffset(8,5),parent.ZIndex+1,parent
        -- Reuse the original crystal model at full geometry quality without upload IDs.
        local preview=require(script.Parent.ModelPreview).add(root,"amber")
        preview.Size=UDim2.fromScale(1,1)
        return root
    end
    local data = Vectors[id]
    if not data then return nil end
    local root = Instance.new("Frame")
    root.Name,root.BackgroundTransparency,root.Size = "Art_"..id,1,UDim2.fromOffset(42,42)
    root.Position,root.ZIndex,root.Parent = UDim2.fromOffset(8,5),parent.ZIndex+1,parent
    for _,shape in data do
        local part=Instance.new("Frame")
        part.BorderSizePixel=0
        part.Position=UDim2.fromScale(shape.x/100,shape.y/100)
        part.Size=UDim2.fromScale(shape.w/100,shape.h/100)
        part.Rotation=shape.rotation
        part.BackgroundColor3=Color3.fromHex(shape.color:sub(2))
        part.ZIndex,part.Parent=root.ZIndex,root
        if shape.color~="#142035" then
            local sheen=Instance.new("UIGradient")
            sheen.Color=ColorSequence.new(Color3.new(1,1,1),Color3.fromRGB(184,195,214))
            sheen.Rotation,sheen.Parent=90,part
        end
        if shape.radius>0 then
            local round=Instance.new("UICorner")
            round.CornerRadius=UDim.new(shape.radius/math.min(shape.w,shape.h),0)
            round.Parent=part
        end
    end
    return root
end
function Theme.icon(parent: GuiObject,id: string): Frame?
    return Artwork.build(parent,id,nativeIcon) or nativeIcon(parent,id)
end
return Theme
