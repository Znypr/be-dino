--!strict
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local InsertService=game:GetService("InsertService")
local Bindings=require(ReplicatedStorage.Shared.ResourceMeshAssets)
local Import={}
function Import.load()
    local folder=Instance.new("Folder") folder.Name="ResourceOverrides" folder.Parent=ReplicatedStorage
    for id,assetId in Bindings do
        if assetId=="" then continue end
        local container=nil
        local ok,result=pcall(function()
            container=InsertService:LoadAsset(tonumber(assetId))
            local model=Instance.new("Model") model.Name=id
            -- Copy geometry/appearance only; never retain executable or physics objects.
            for _,part in container:GetDescendants() do
                if part:IsA("BasePart") then
                    local copy=part:Clone()
                    for _,child in copy:GetDescendants() do
                        if not child:IsA("SurfaceAppearance") and not child:IsA("Decal") and not child:IsA("Texture") then child:Destroy() end
                    end
                    copy.Anchored,copy.CanCollide,copy.CanTouch,copy.CanQuery,copy.Massless=true,false,false,false,true
                    copy.Parent=model
                end
            end
            assert(#model:GetChildren()>0,"Imported model has no geometry")
            local box,size=model:GetBoundingBox()
            local fallback=ReplicatedStorage.Resources:FindFirstChild(id)
            local targetHeight=size.Y
            if fallback and fallback:IsA("Model") then local _,bounds=fallback:GetBoundingBox() targetHeight=bounds.Y end
            local scale=targetHeight/size.Y
            local origin=box.Position-Vector3.new(0,size.Y/2,0)
            for _,part in model:GetChildren() do
                part.Size*=scale
                part.CFrame=CFrame.new((part.Position-origin)*scale)*part.CFrame.Rotation
            end
            model.WorldPivot=CFrame.new()
            model:SetAttribute("UploadedModelId",assetId)
            return model
        end)
        if container then container:Destroy() end
        if ok then result.Parent=folder else warn("[Be Dino] textured model "..id.." unavailable; keeping original: "..tostring(result)) end
    end
end
return Import
