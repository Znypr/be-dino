--!strict
local Resources=require(script.Parent.ResourceModels)
local Camera=require(script.Parent.PreviewCamera)
local Preview={}
function Preview.add(parent: GuiObject,speciesId: string,gold: boolean): ViewportFrame
    local viewport=Instance.new("ViewportFrame")
    viewport.Name,viewport.BackgroundTransparency="DinosaurPreview",1
    viewport.Size=UDim2.new(1,0,0,140)
    viewport.Ambient,viewport.LightColor,viewport.LightDirection=Color3.fromRGB(190,210,218),Color3.fromRGB(255,246,226),Vector3.new(-1,-1,-1)
    viewport.ZIndex,viewport.Parent=parent.ZIndex+1,parent
    local model=Resources.clone(speciesId)
    if model then
        local world=Instance.new("WorldModel") world.Parent=viewport
        for _,item in model:GetDescendants() do
            if item:IsA("BasePart") then
                item.Anchored=true
                if gold then item.Color=Color3.fromRGB(242,199,63) item.Material=Enum.Material.Metal end
            end
        end
        model:PivotTo(CFrame.new())
        model.Parent=world
        Camera.bind(viewport,model)
    end
    return viewport
end
return Preview
