--!strict
local Resources=require(script.Parent.ResourceModels)
local Camera=require(script.Parent.PreviewCamera)
local ContentProvider=game:GetService("ContentProvider")
local Preview={}
local RunService=game:GetService("RunService")
local Http=game:GetService("HttpService")
local Appearance=require(script.Parent.EggAppearance)
local function visible(view)
    local low,high=view.AbsolutePosition,view.AbsolutePosition+view.AbsoluteSize
    if view.AbsoluteSize.X<=0 or view.AbsoluteSize.Y<=0 then return false end
    local ancestor=view
    while ancestor do
        if ancestor:IsA("GuiObject") then
            if not ancestor.Visible then return false end
            if ancestor.ClipsDescendants then
                local a,b=ancestor.AbsolutePosition,ancestor.AbsolutePosition+ancestor.AbsoluteSize
                if high.X<=a.X or high.Y<=a.Y or low.X>=b.X or low.Y>=b.Y then return false end
            end
        elseif ancestor:IsA("ScreenGui") and not ancestor.Enabled then return false end
        ancestor=ancestor.Parent
    end
    return true
end
function Preview.add(parent: GuiObject,speciesId: string,gold: (boolean | string)): ViewportFrame
    local viewport=Instance.new("ViewportFrame")
    viewport.Name,viewport.BackgroundTransparency="DinosaurPreview",1
    viewport.Size=UDim2.new(1,0,0,140)
    viewport.Ambient,viewport.LightColor,viewport.LightDirection=Color3.fromRGB(190,210,218),Color3.fromRGB(255,246,226),Vector3.new(-1,-1,-1)
    viewport.ZIndex,viewport.Parent=parent.ZIndex+1,parent
    local function load()
    local model=Resources.clone(speciesId)
    if model and not viewport.Parent then model:Destroy();return end
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
        local encoded=viewport:GetAttribute("TraitsJson")
        if encoded then local ok,traits=pcall(function() return Http:JSONDecode(encoded) end);if ok and traits.genes then Appearance.apply(model,traits.genes) end end
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
    end
    local data=script.Parent:FindFirstChild("CreatureData")
    if data and data:FindFirstChild(speciesId) then
        local elapsed=0;local loading=false
        local connection=RunService.Heartbeat:Connect(function(dt)
            elapsed+=dt;if elapsed<.25 or loading then return end;elapsed=0
            local world=viewport:FindFirstChildOfClass("WorldModel")
            if visible(viewport) then
                if not world then loading=true;task.spawn(function() if viewport.Parent then load() end;loading=false end) end
            elseif world then world:Destroy() end
        end)
        viewport.Destroying:Once(function() connection:Disconnect() end)
    else load() end
    return viewport
end
return Preview
