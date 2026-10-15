--!strict
local Resources=require(script.Parent.ResourceModels)
local Camera=require(script.Parent.PreviewCamera)
local ContentProvider=game:GetService("ContentProvider")
local Preview={}
local RunService=game:GetService("RunService")
local Http=game:GetService("HttpService")
local Appearance=require(script.Parent.EggAppearance)
local MutationLook=require(script.Parent.MutationLook)
local Authored=require(script.Parent.AuthoredCreatures)
local Theme=require(script.Parent.UITheme)
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
-- BD-219: when no loaded 3D model is available the card shows the flat dino picture (never a box, never empty).
local function dinoImage(viewport: ViewportFrame,gold: (boolean | string))
    if viewport:FindFirstChild("DinoImageFallback") then return end
    local image=Instance.new("ImageLabel")
    image.Name,image.BackgroundTransparency,image.BorderSizePixel="DinoImageFallback",1,0
    image.AnchorPoint,image.Position,image.Size=Vector2.new(.5,.5),UDim2.fromScale(.5,.5),UDim2.fromScale(.8,.8)
    image.ScaleType,image.Image=Enum.ScaleType.Fit,Theme.ImageIds.dinos or ""
    image.ImageColor3=if gold=="silhouette" then Color3.new(0,0,0) else Color3.new(1,1,1)
    image.ImageTransparency=viewport.ImageTransparency -- hidden/faded exactly like the 3D view (hatch build-up keeps it invisible)
    image.ZIndex,image.Parent=viewport.ZIndex+1,viewport
    local follow=viewport:GetPropertyChangedSignal("ImageTransparency"):Connect(function() image.ImageTransparency=viewport.ImageTransparency end)
    image.Destroying:Once(function() follow:Disconnect() end)
    viewport:SetAttribute("PreviewFallback","DinoImage")
end
function Preview.add(parent: GuiObject,speciesId: string,gold: (boolean | string)): ViewportFrame
    local viewport=Instance.new("ViewportFrame")
    viewport.Name,viewport.BackgroundTransparency="DinosaurPreview",1
    viewport.Size=UDim2.new(1,0,0,140)
    viewport.Ambient,viewport.LightColor,viewport.LightDirection=Color3.fromRGB(190,210,218),Color3.fromRGB(255,246,226),Vector3.new(-1,-1,-1)
    viewport.ZIndex,viewport.Parent=parent.ZIndex+1,parent
    local function load(): boolean
    local encoded=viewport:GetAttribute("TraitsJson")
    local traits=nil
    if encoded and gold~="silhouette" and gold~=true and gold~="gold" and gold~="diamond" and gold~="emerald" then
        local ok,decoded=pcall(function() return Http:JSONDecode(encoded) end)
        if ok and typeof(decoded)=="table" then traits=decoded end
    end
    local model=Resources.clone(speciesId,if traits then traits.genes else nil,true)
    if model and not viewport.Parent then model:Destroy();return false end
    -- Species with authored data must show the authored mesh, never any other (box) model.
    if model and Authored.has(speciesId) and not model:GetAttribute("AuthoredCreature") then model:Destroy() model=nil end
    -- Never show a model whose mesh content is not really loaded (it renders as a textured box).
    if model and not Authored.verify(model) then model:Destroy() model=nil end
    if model then
        local world=Instance.new("WorldModel") world.Parent=viewport
        for _,item in model:GetDescendants() do
            if item:IsA("BasePart") then
                item.Anchored=true
                if gold=="silhouette" then
                    Resources.clearTextures(item)
                    item.Color,item.Material,item.Reflectance=Color3.new(0,0,0),Enum.Material.SmoothPlastic,0
                    for _,child in item:GetChildren() do
                        if child:IsA("ParticleEmitter") or child:IsA("Highlight") or child:IsA("Light") or child:IsA("Trail") or child:IsA("Beam") then child:Destroy() end
                    end
                elseif gold==true or gold=="gold" or gold=="diamond" or gold=="emerald" then Resources.clearTextures(item) end
                -- BD-173: dinosaurs are matte; only fused tiers (Gold/Emerald/Diamond) keep a sheen below.
                if gold~="silhouette" and gold~=true and gold~="gold" and gold~="diamond" and gold~="emerald" then item.Material,item.Reflectance=Enum.Material.Plastic,0 end
                if gold == "diamond" then item.Color=Color3.fromRGB(85,213,245) item.Material=Enum.Material.Glass item.Reflectance=.2
                elseif gold == "emerald" then item.Color=Color3.fromRGB(46,196,120) item.Material=Enum.Material.Metal item.Reflectance=.1
                elseif gold == true or gold == "gold" then item.Color=Color3.fromRGB(242,199,63) item.Material=Enum.Material.Metal end
            end
        end
        model:PivotTo(CFrame.new())
        model.Parent=world
        local fallback=viewport:FindFirstChild("DinoImageFallback")
        if fallback then fallback:Destroy() viewport:SetAttribute("PreviewFallback",nil) end
        if gold=="silhouette" then
            viewport.Ambient,viewport.LightColor=Color3.new(0,0,0),Color3.new(0,0,0)
        elseif traits and traits.genes then Appearance.apply(model,traits.genes) end
        if traits and gold~="silhouette" then MutationLook.apply(model,traits.mutationId) end -- BD-155 (traits only decoded for base stage)
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
        return true
    end
    if viewport.Parent then dinoImage(viewport,gold) end
    return false
    end
    local data=script.Parent:FindFirstChild("CreatureData")
    if data and data:FindFirstChild(speciesId) then
        local elapsed=0;local loading=false;local attempts=0
        local connection=RunService.Heartbeat:Connect(function(dt)
            elapsed+=dt;if elapsed<.25 or loading then return end;elapsed=0
            local world=viewport:FindFirstChildOfClass("WorldModel")
            if visible(viewport) then
                -- The flat picture stays up while loading retries (at most 8); it is replaced the moment a real model lands.
                if not world and attempts<8 then attempts+=1;loading=true;task.spawn(function() if viewport.Parent then load() end;loading=false end) end
            elseif world then world:Destroy();attempts=0 end
        end)
        viewport.Destroying:Once(function() connection:Disconnect() end)
    else load() end
    return viewport
end
return Preview
