--!strict
local Resources=require(script.Parent.ResourceModels)
local Egg=require(script.Parent.EggPreview)
local Camera=require(script.Parent.PreviewCamera)
local ModelPreview={}
function ModelPreview.add(parent: GuiObject,id: string,empty: boolean?): ViewportFrame
    local viewport=Instance.new("ViewportFrame")
    viewport.BackgroundTransparency,viewport.Size=1,UDim2.fromScale(1,1)
    viewport.Ambient,viewport.LightColor,viewport.LightDirection=Color3.fromRGB(193,211,220),Color3.fromRGB(255,246,220),Vector3.new(-1,-1,-1)
    viewport.ZIndex,viewport.Parent=parent.ZIndex+1,parent
    local model=if id=="egg" then Egg.create(empty) else Resources.clone(id)
    if model then
        for _,item in model:GetDescendants() do if item:IsA("BasePart") then item.Anchored=true end end
        model:PivotTo(CFrame.new())
        model.Parent=viewport
        Camera.bind(viewport,model)
    end
    return viewport
end
return ModelPreview
