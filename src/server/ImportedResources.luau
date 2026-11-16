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
    if require(ReplicatedStorage.Shared.Config).HatchStageEnabled then task.spawn(Import.loadHatchShards) task.spawn(Import.loadHatchBuckets) end -- BD-1212 / BD-1211 (defined below)
    local folder=ReplicatedStorage:FindFirstChild("GeneratedWorld")
    if not folder then folder=Instance.new("Folder") folder.Name="GeneratedWorld" folder.Parent=ReplicatedStorage end
    local loaded,failed,pending=0,0,0
    -- BD-462: V3 tree replacements load like the others, but an empty assetId (not uploaded yet) is skipped silently, not a failure.
    local entries: {{key: string, asset: {assetId: string}}}={}
    for key,asset in GeneratedMeshes.Assets do table.insert(entries,{key=key,asset=asset}) end
    for key,asset in GeneratedMeshes.Replacements do if asset.assetId~="" then table.insert(entries,{key=key,asset=asset}) end end
    -- BD-463/464: the Blender plants and ground props load the same way once an id is pasted; empty = skipped silently. Arena (step 2) places a key
    -- only when its id is valid AND this load succeeded (a failed load just leaves the old clutter, see Arena.biomeKit).
    for key,asset in GeneratedMeshes.Props do if asset.assetId~="" then table.insert(entries,{key=key,asset=asset}) end end
    -- BD-474/BD-475: colossal ancient trees (LOD0 near and LOD1 far, used together as a pair by the colossal layer) load the same way; empty ids are skipped silently.
    for key,asset in GeneratedMeshes.Colossal do if asset.assetId~="" then table.insert(entries,{key=key,asset=asset}) end end
    -- BD-1208: the V3 food pickups load only with Config.FoodV3Enabled (flag off = nothing extra is fetched).
    if require(ReplicatedStorage.Shared.Config).FoodV3Enabled then for key,asset in GeneratedMeshes.Food do table.insert(entries,{key=key,asset=asset}) end end
    -- BD-1210: the zone landmarks of the redesigned island load only with Config.WorldV3Enabled; empty ids are skipped silently.
    if require(ReplicatedStorage.Shared.Config).WorldV3Enabled then for key,asset in GeneratedMeshes.Landmarks do if asset.assetId~="" then table.insert(entries,{key=key,asset=asset}) end end end
    -- BD-1239: the vegetation v2 family loads only with VegetationV2Enabled (+ WorldV3 + ToonWorld); an id not published yet is skipped silently.
    local Veg2=require(ReplicatedStorage.Shared.VegetationV2)
    if Veg2.enabled(require(ReplicatedStorage.Shared.Config)) then for key,asset in Veg2.Assets do if Veg2.ready(key) then table.insert(entries,{key=key,asset=asset}) end end end
    -- BD-1245 / BD-1246: ground detail and set pieces load only with GroundDetailEnabled / ThingsToDoEnabled (ground pieces fill_*, set pieces set_*).
    local Fill=require(ReplicatedStorage.Shared.WorldFill)
    local fillGround,fillThings=Fill.groundEnabled(require(ReplicatedStorage.Shared.Config)),Fill.thingsEnabled(require(ReplicatedStorage.Shared.Config))
    for key,asset in Fill.Assets do
        local wanted=if string.sub(key,1,4)=="set_" then fillThings else fillGround
        if wanted and Fill.ready(key) then table.insert(entries,{key=key,asset=asset}) end
    end
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
                -- BD-1208: the upright turn FoodService applies (rotX, degrees about X). A tinted food becomes a Part with a FileMesh SpecialMesh of the
                -- same mesh and texture: SpecialMesh.VertexColor tints the texture and, unlike a SurfaceAppearance map, a game script may set it (Studio
                -- test 2026-11-15). MeshSize keeps the mesh's own size so FoodService can scale the SpecialMesh with the part.
                local food=GeneratedMeshes.Food[key]
                if food then
                    mesh:SetAttribute("RotX",food.rotX)
                    if food.tint then
                        local part=Instance.new("Part")
                        part.Size=mesh.MeshSize
                        local special=Instance.new("SpecialMesh")
                        special.MeshType=Enum.MeshType.FileMesh special.MeshId=mesh.MeshId special.TextureId=mesh.TextureID
                        special.VertexColor=Vector3.new(food.tint[1]/255,food.tint[2]/255,food.tint[3]/255)
                        special.Parent=part
                        part:SetAttribute("MeshSize",mesh.MeshSize) part:SetAttribute("RotX",food.rotX)
                        mesh:Destroy()
                        mesh=part :: any
                    end
                end
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
-- BD-1212: the 3D egg shards of the full-screen hatch (tools/blender/egg_shards.py, docs/77 hatch_egg_shards), one Model of MeshParts in
-- ReplicatedStorage.HatchStageShards. Only with Config.HatchStageEnabled; a failed load leaves the burst without shards (flash and sparkles stay).
Import.HatchShardsAsset=72971857567912
function Import.loadHatchShards()
    if ReplicatedStorage:FindFirstChild("HatchStageShards") then return end
    local ok,err=pcall(function()
        local container=InsertService:LoadAsset(Import.HatchShardsAsset)
        local model=Instance.new("Model")
        model.Name="HatchStageShards"
        for _,item in container:GetDescendants() do
            if item:IsA("MeshPart") then
                local part=item:Clone()
                for _,child in part:GetChildren() do child:Destroy() end
                part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.Massless=true,false,false,false,true
                part.Parent=model
            end
        end
        container:Destroy()
        assert(#model:GetChildren()>0,"shard model has no MeshParts")
        model.Parent=ReplicatedStorage
    end)
    if not ok then warn("[Be Dino] hatch shards unavailable: "..tostring(err)) end
end
-- BD-1211: the two generated paint buckets of the hatch stage (docs/77 hatch_bucket_pail / _can) in ReplicatedStorage.HatchStageBuckets.
-- The paint area of each texture is see-through (SurfaceAppearance overlay from Resources.HatchBucketSurfaces), so MeshPart.Color = the
-- egg's paint colour. A failed load keeps the 2D bucket picture.
Import.HatchBuckets={pail=105190298129955,can=77568845237888}
function Import.loadHatchBuckets()
    if ReplicatedStorage:FindFirstChild("HatchStageBuckets") then return end
    local resources=ReplicatedStorage:FindFirstChild("Resources")
    local surfaces=resources and resources:FindFirstChild("HatchBucketSurfaces")
    local folder=Instance.new("Folder")
    folder.Name="HatchStageBuckets"
    for key,id in Import.HatchBuckets do
        local ok,err=pcall(function()
            local container=InsertService:LoadAsset(id)
            local found=container:FindFirstChildWhichIsA("MeshPart",true)
            assert(found and surfaces and surfaces:FindFirstChild(key),"bucket mesh or surface missing")
            local part=found:Clone()
            container:Destroy()
            for _,child in part:GetChildren() do child:Destroy() end
            surfaces[key]:Clone().Parent=part
            part.TextureID,part.Name="",key
            part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.Massless=true,false,false,false,true
            part.Parent=folder
        end)
        if not ok then warn("[Be Dino] hatch bucket "..key.." unavailable: "..tostring(err)) end
    end
    folder.Parent=ReplicatedStorage
end
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
