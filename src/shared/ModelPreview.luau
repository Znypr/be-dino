--!strict
local Resources=require(script.Parent.ResourceModels)
local Egg=require(script.Parent.EggPreview)
local Camera=require(script.Parent.PreviewCamera)
local Authored=require(script.Parent.AuthoredCreatures)
local Theme=require(script.Parent.UITheme)
local ModelPreview={}
-- BD-216/219: when the 3D egg is not available (mesh APIs off, budget, unloaded content) the preview shows the official
-- 2D egg picture (shell + condition layer, tinted by EggAppearance), never a cube or a bare ball. Marked EggImageFallback.
function ModelPreview.eggImage(viewport: ViewportFrame)
    local shell=Theme.ImageIds.egg
    viewport:SetAttribute("EggImageFallback",true)
    viewport:SetAttribute("PreviewFallback","EggImage")
    local function layer(name: string,z: number): ImageLabel
        local item=Instance.new("ImageLabel")
        item.Name,item.BackgroundTransparency,item.BorderSizePixel,item.Image=name,1,0,""
        item.AnchorPoint,item.Position,item.Size=Vector2.new(.5,.5),UDim2.fromScale(.5,.5),UDim2.fromScale(.92,.92)
        item.ScaleType,item.ZIndex,item.Parent=Enum.ScaleType.Fit,z,viewport
        return item
    end
    local base=layer("EggShell",viewport.ZIndex+1)
    if shell~=nil and shell~="" then base.Image=shell
    else -- no uploaded egg picture either: a soft cream ellipse (still never a box)
        base.BackgroundTransparency,base.BackgroundColor3,base.Size=0,Color3.fromRGB(255,244,214),UDim2.fromScale(.55,.8)
        local corner=Instance.new("UICorner") corner.CornerRadius=UDim.new(.5,0) corner.Parent=base
    end
    layer("EggCondition",viewport.ZIndex+2).Visible=false
end
function ModelPreview.add(parent: GuiObject,id: string,empty: boolean?): ViewportFrame
    local viewport=Instance.new("ViewportFrame")
    viewport.BackgroundTransparency,viewport.Size=1,UDim2.fromScale(1,1)
    viewport.Ambient,viewport.LightColor,viewport.LightDirection=Color3.fromRGB(193,211,220),Color3.fromRGB(255,246,220),Vector3.new(-1,-1,-1)
    if id=="egg" then
        -- BD-226 (docs/87 calm, bubbly): an egg is lit softly from the camera side (PreviewCamera looks along Egg.CameraDirection),
        -- with a high ambient, so no half of the shell turns black and the condition marks on the camera-facing side read clearly.
        viewport.Ambient,viewport.LightColor=Color3.fromRGB(196,196,204),Color3.fromRGB(120,116,106)
        viewport.LightDirection=Vector3.new(-Egg.CameraDirection.X,-.7,-Egg.CameraDirection.Z)
    end
    viewport.ZIndex,viewport.Parent=parent.ZIndex+1,parent
    local model=if id=="egg" then Egg.create(empty) else Resources.clone(id,nil,true)
    if model and not viewport.Parent then model:Destroy();return viewport end
    -- Never show a model whose mesh content is not really loaded (renders as a box): drop it and use the 2D picture.
    if model and model:GetAttribute("LowPoly")~=true and not Authored.verify(model) then model:Destroy() model=nil end
    -- A real (non-empty) egg must be the authored 3D egg; the primitive ball cannot carry pattern or condition.
    if model and id=="egg" and not empty and not model:GetAttribute("AuthoredCreature") then model:Destroy() model=nil end
    if model then
        for _,item in model:GetDescendants() do if item:IsA("BasePart") then item.Anchored=true end end
        model:PivotTo(CFrame.new())
        local world=Instance.new("WorldModel") world.Parent=viewport
        model.Parent=world
        Camera.bind(viewport,model,if id=="egg" then nil else id)
    elseif id=="egg" and not empty then ModelPreview.eggImage(viewport) end
    return viewport
end
return ModelPreview
