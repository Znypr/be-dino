--!strict
local Resources=require(script.Parent.ResourceModels)
local Camera=require(script.Parent.PreviewCamera)
local ContentProvider=game:GetService("ContentProvider")
local Preview={}
function Preview.add(parent: GuiObject,speciesId: string,gold: (boolean | string)): ViewportFrame
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
                if gold==true or gold=="gold" or gold=="diamond" then Resources.clearTextures(item) end
                if gold == "diamond" then item.Color=Color3.fromRGB(85,213,245) item.Material=Enum.Material.Glass item.Reflectance=.2
                elseif gold == true or gold == "gold" then item.Color=Color3.fromRGB(242,199,63) item.Material=Enum.Material.Metal end
            end
        end
        model:PivotTo(CFrame.new())
        model.Parent=world
        Camera.bind(viewport,model,speciesId)
        task.spawn(function()
            local assets={}
            for _,part in model:GetDescendants() do
                if part:IsA("MeshPart") and part.MeshId~="" then table.insert(assets,part) end
            end
            local uploadedId=model:GetAttribute("UploadedModelId")
            if #assets==0 or not uploadedId then return end
            local failed=false
            local ok=pcall(function() ContentProvider:PreloadAsync(assets,function(_,status)
                if status~=Enum.AssetFetchStatus.Success then failed=true end
            end) end)
            if not viewport.Parent or (ok and not failed) then return end
            -- Keep the actual species visible when the uploaded mesh is unavailable.
            local image=Instance.new("ImageLabel")
            image.Name,image.BackgroundTransparency,image.BorderSizePixel="ModelThumbnailFallback",1,0
            image.Size,image.ScaleType=UDim2.fromScale(1,1),Enum.ScaleType.Fit
            image.Image="rbxthumb://type=Asset&id="..tostring(uploadedId).."&w=420&h=420"
            image.ZIndex,image.Parent=viewport.ZIndex+1,viewport
            pcall(function() ContentProvider:PreloadAsync({image}) end)
            if image.Parent then viewport:SetAttribute("PreviewFallback","AssetThumbnail") end
        end)
    end
    return viewport
end
return Preview
