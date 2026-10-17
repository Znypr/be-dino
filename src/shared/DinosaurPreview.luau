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
local LowPoly=require(script.Parent.LowPolyDinos)
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
-- BD-345: a fused output shows ITS OWN rolled colours under the tier. Low-poly dinos bake the genes under the tier tint
-- (LowPoly.tint); legacy models keep the Metal/Glass sheen and pull the gene colour 30% toward the tier colour so the colours still read.
local TierColors={gold=Color3.fromRGB(242,199,63),emerald=Color3.fromRGB(46,196,120),diamond=Color3.fromRGB(85,213,245)}
function Preview.tierName(gold:(boolean|string)):string?
    if gold==true then return "gold" end
    if gold=="gold" or gold=="emerald" or gold=="diamond" then return gold :: string end
    return nil
end
function Preview.tierBlend(container:Instance,tier:string?)
    local color=if tier then TierColors[tier] else nil
    if not color then return end
    for _,item in container:GetDescendants() do
        if item:IsA("BasePart") then item.Color=item.Color:Lerp(color,.3) end
    end
end
function Preview.add(parent: GuiObject,speciesId: string,gold: (boolean | string)): ViewportFrame
    local viewport=Instance.new("ViewportFrame")
    viewport.Name,viewport.BackgroundTransparency="DinosaurPreview",1
    viewport.Size=UDim2.new(1,0,0,140)
    viewport.Ambient,viewport.LightColor,viewport.LightDirection=Color3.fromRGB(190,210,218),Color3.fromRGB(255,246,226),Vector3.new(-1,-1,-1)
    viewport.ZIndex,viewport.Parent=parent.ZIndex+1,parent
    viewport:SetAttribute("PreviewTier",Preview.tierName(gold))
    local function load(): boolean
    local encoded=viewport:GetAttribute("TraitsJson")
    local traits=nil
    local fused=gold==true or gold=="gold" or gold=="diamond" or gold=="emerald"
    if encoded and gold~="silhouette" then -- BD-061 / BD-345: a fused dino (low-poly or legacy) shows its own genes under the tier
        local ok,decoded=pcall(function() return Http:JSONDecode(encoded) end)
        if ok and typeof(decoded)=="table" then traits=decoded end
    end
    local model=Resources.clone(speciesId,if traits then traits.genes else nil,true)
    if model and not viewport.Parent then model:Destroy();return false end
    -- Species with authored data must show the authored mesh, never any other (box) model.
    if model and model:GetAttribute("LowPoly")~=true and Authored.has(speciesId) and not model:GetAttribute("AuthoredCreature") then model:Destroy() model=nil end
    -- Never show a model whose mesh content is not really loaded (it renders as a textured box).
    if model and model:GetAttribute("LowPoly")~=true and not Authored.verify(model) then model:Destroy() model=nil end
    if model then
        local world=Instance.new("WorldModel") world.Parent=viewport
        local lowPoly=model:GetAttribute("LowPoly")==true
        if lowPoly and fused then model:SetAttribute("LPTier",if gold==true then "gold" else gold) end
        for _,item in model:GetDescendants() do
            if item:IsA("BasePart") then
                item.Anchored=true
                if lowPoly and gold~="silhouette" then continue end -- BD-061: LowPoly.tint / applyTier own the material and tier look
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
        if lowPoly and not fused and gold~="silhouette" and traits then model:SetAttribute("LPMutation",traits.mutationId) end -- BD-518: Part.Color cannot tint a baked texture; the bake reads this
        if gold=="silhouette" then
            viewport.Ambient,viewport.LightColor=Color3.new(0,0,0),Color3.new(0,0,0)
        elseif traits and traits.genes then Appearance.apply(model,traits.genes)
        elseif lowPoly and fused then LowPoly.applyTier(model,gold) end
        if fused and not lowPoly and traits and traits.genes then Preview.tierBlend(model,Preview.tierName(gold)) end
        if traits and gold~="silhouette" and not fused then MutationLook.apply(model,traits.mutationId) end -- BD-155 (fused tiers never get a mutation tint)
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
                -- BD-381: while the low-poly template is still loading the retries do not count (the flat picture stays up until it lands).
                local waiting=LowPoly.pending(speciesId)
                if not world and (attempts<8 or waiting) then
                    if not waiting then attempts+=1 end
                    loading=true;task.spawn(function() if viewport.Parent then load() end;loading=false end)
                end
            elseif world then world:Destroy();attempts=0 end
        end)
        viewport.Destroying:Once(function() connection:Disconnect() end)
    else
        -- BD-381: species without CreatureData (and the first try for the rest) wait for the low-poly template instead of keeping a legacy model.
        if not load() then
            LowPoly.whenReady(speciesId,function()
                if viewport.Parent and not viewport:FindFirstChildOfClass("WorldModel") then load() end
            end)
        end
    end
    return viewport
end
return Preview
