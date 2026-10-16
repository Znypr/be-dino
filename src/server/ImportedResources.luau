--!strict
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local InsertService=game:GetService("InsertService")
local AssetService=game:GetService("AssetService")
local Bindings=require(ReplicatedStorage.Shared.ResourceMeshAssets)
local KitMeshes=require(ReplicatedStorage.Shared.WorldKitMeshAssets)
local GeneratedMeshes=require(ReplicatedStorage.Shared.WorldGeneratedMeshes)
local Import={}
local function overrides(): Folder
    local existing=ReplicatedStorage:FindFirstChild("ResourceOverrides")
    if existing and existing:IsA("Folder") then return existing end
    local folder=Instance.new("Folder") folder.Name="ResourceOverrides" folder.Parent=ReplicatedStorage
    return folder
end
-- BD-049/050 kit: one real MeshPart per uploaded kit mesh (vertex colours carry the palette; no textures).
-- Sized in studs from the generated bindings, pivot = bounding-box bottom centre (ResourceModels.clone normalises it).
-- An id whose mesh fails to load keeps its native fallback model; the world is never left empty.
function Import.loadWorldKit(): (number, number)
    local folder=overrides()
    local loaded,failed,pending=0,0,0
    for id,binding in KitMeshes do
        pending+=1
        task.spawn(function()
            local ok,result=pcall(function()
                local mesh=AssetService:CreateMeshPartAsync(Content.fromUri(binding.meshId),{CollisionFidelity=Enum.CollisionFidelity.Box,RenderFidelity=Enum.RenderFidelity.Automatic})
                mesh.Name=id
                mesh.Size=Vector3.new(binding.size[1],binding.size[2],binding.size[3])
                mesh.Color=Color3.new(1,1,1) -- white tint: the kit palette comes from the mesh vertex colours
                mesh.Material=Enum.Material.SmoothPlastic
                mesh.Anchored,mesh.CanCollide,mesh.CanTouch,mesh.CanQuery,mesh.Massless=true,false,false,false,true
                mesh:SetAttribute("KitMeshId",binding.meshId)
                return mesh
            end)
            if ok then result.Parent=folder loaded+=1 else failed+=1 warn("[Be Dino] kit mesh "..id.." unavailable; keeping native fallback: "..tostring(result)) end
            pending-=1
        end)
    end
    local deadline=os.clock()+30
    while pending>0 and os.clock()<deadline do task.wait() end
    workspace:SetAttribute("WorldKitMeshParts",loaded)
    workspace:SetAttribute("WorldKitMeshFailed",failed+pending)
    return loaded,failed+pending
end
-- BD-206: Roblox-generated world meshes (WorldGeneratedMeshes.Assets) as one MeshPart each in ReplicatedStorage.GeneratedWorld.
-- A failed load only logs and counts; Arena then keeps the current kit model for that prop (same fallback as loadWorldKit).
function Import.loadGeneratedWorld(): (number, number)
    local folder=ReplicatedStorage:FindFirstChild("GeneratedWorld")
    if not folder then folder=Instance.new("Folder") folder.Name="GeneratedWorld" folder.Parent=ReplicatedStorage end
    local loaded,failed,pending=0,0,0
    -- BD-462: V3 tree replacements load like the others, but an empty assetId (not uploaded yet) is skipped silently, not a failure.
    local entries: {{key: string, asset: {assetId: string}}}={}
    for key,asset in GeneratedMeshes.Assets do table.insert(entries,{key=key,asset=asset}) end
    for key,asset in GeneratedMeshes.Replacements do if asset.assetId~="" then table.insert(entries,{key=key,asset=asset}) end end
    -- BD-464 step 1: ground props load the same way once an id is pasted; empty = skipped silently, and nothing places them yet.
    for key,asset in GeneratedMeshes.Props do if asset.assetId~="" then table.insert(entries,{key=key,asset=asset}) end end
    for _,entry in entries do
        local key,asset=entry.key,entry.asset
        pending+=1
        task.spawn(function()
            local ok,result=pcall(function()
                -- generate_mesh publishes a Model ("Roblox Generated Object") that holds one textured MeshPart.
                local container=InsertService:LoadAsset(tonumber(asset.assetId))
                local found: MeshPart? = nil
                for _,item in container:GetDescendants() do if item:IsA("MeshPart") then found=item break end end
                assert(found,"generated asset has no MeshPart")
                local mesh=found:Clone()
                container:Destroy()
                for _,child in mesh:GetChildren() do if not child:IsA("SurfaceAppearance") then child:Destroy() end end
                -- BD-460: per-asset foliage tone (data in WorldGeneratedMeshes.Tone); a missing property only skips the tint.
                local tone=GeneratedMeshes.Tone[key]
                local surface=mesh:FindFirstChildOfClass("SurfaceAppearance")
                if tone and surface then pcall(function() surface.Color=Color3.new(tone[1],tone[2],tone[3]) end) end
                mesh.Name=key
                mesh.Anchored,mesh.CanCollide,mesh.CanTouch,mesh.CanQuery,mesh.Massless=true,false,false,false,true
                mesh:SetAttribute("GeneratedAssetId",asset.assetId)
                return mesh
            end)
            if ok then result.Parent=folder loaded+=1 else failed+=1 warn("[Be Dino] generated mesh "..key.." ("..asset.assetId..") unavailable; keeping the current kit model: "..tostring(result)) end
            pending-=1
        end)
    end
    local deadline=os.clock()+30
    while pending>0 and os.clock()<deadline do task.wait() end
    workspace:SetAttribute("GeneratedMeshLoaded",loaded)
    workspace:SetAttribute("GeneratedMeshFailed",failed+pending)
    return loaded,failed+pending
end
-- BD-397 (docs/118): the v2 hatch meshes (generated egg, PLACEHOLDER barrel as the bucket) as one MeshPart each in
-- ReplicatedStorage.HatchV2Models. Only called while Config.HatchV2 is true. A failed egg load leaves the folder without "egg":
-- the client then runs the shipped v1 sequence; a failed bucket load only hides the bucket.
function Import.loadHatchV2(): (number, number)
    local Assets=require(ReplicatedStorage.Shared.HatchV2Assets)
    local folder=ReplicatedStorage:FindFirstChild(Assets.FolderName)
    if not folder then folder=Instance.new("Folder") folder.Name=Assets.FolderName folder.Parent=ReplicatedStorage end
    local loaded,failed,pending=0,0,0
    for key,asset in Assets.Models do
        if folder:FindFirstChild(key) then continue end
        pending+=1
        task.spawn(function()
            local ok,result=pcall(function()
                local container=InsertService:LoadAsset(tonumber(asset.assetId))
                local found: MeshPart? = nil
                for _,item in container:GetDescendants() do if item:IsA("MeshPart") then found=item break end end
                assert(found,"generated asset has no MeshPart")
                local mesh=found:Clone()
                container:Destroy()
                for _,child in mesh:GetChildren() do if not child:IsA("SurfaceAppearance") then child:Destroy() end end
                mesh.Name=key
                mesh.Anchored,mesh.CanCollide,mesh.CanTouch,mesh.CanQuery,mesh.Massless=true,false,false,false,true
                mesh:SetAttribute("GeneratedAssetId",asset.assetId)
                mesh:SetAttribute("Placeholder",Assets.Placeholder[key]==true)
                return mesh
            end)
            if ok then result.Parent=folder loaded+=1 else failed+=1 warn("[Be Dino] hatch v2 mesh "..key.." ("..asset.assetId..") unavailable: "..tostring(result)) end
            pending-=1
        end)
    end
    local deadline=os.clock()+30
    while pending>0 and os.clock()<deadline do task.wait() end
    workspace:SetAttribute("HatchV2MeshLoaded",loaded)
    workspace:SetAttribute("HatchV2MeshFailed",failed+pending)
    return loaded,failed+pending
end
function Import.load()
    local folder=overrides()
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
