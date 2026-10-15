--!strict
-- BD-214: textured potion models (Roblox generate_mesh, published to the owner's account; docs/77) shown in menus through
-- ViewportFrames (Shared/PotionArt). Loaded once on the server with InsertService, stripped to visual parts only, and cached
-- in ReplicatedStorage.PotionModels. If a load fails the client keeps the vector flask fallback.
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local PotionArt = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("PotionArt"))
local Models = {}

local KEEP = {MeshPart = true, SurfaceAppearance = true, Decal = true, Texture = true, Model = true, SpecialMesh = true, Part = true}

local function sanitize(root: Instance): Model?
    local model = Instance.new("Model")
    for _, item in root:GetDescendants() do
        if item:IsA("BasePart") and KEEP[item.ClassName] then
            local copy = item:Clone()
            for _, child in copy:GetDescendants() do
                if not KEEP[child.ClassName] then child:Destroy() end
            end
            copy.Anchored, copy.CanCollide, copy.CanQuery, copy.CanTouch = true, false, false, false
            copy.Parent = model
        end
    end
    if #model:GetChildren() == 0 then model:Destroy() return nil end
    return model
end

function Models.load()
    local folder = ReplicatedStorage:FindFirstChild("PotionModels") or Instance.new("Folder")
    folder.Name = "PotionModels"
    folder.Parent = ReplicatedStorage
    for key, assetId in PotionArt.ModelAssets do
        if folder:FindFirstChild(key) then continue end
        task.spawn(function()
            local ok, result = pcall(function() return InsertService:LoadAsset(assetId) end)
            if not ok or not result then warn("[PotionModels] load failed", key, assetId, result) return end
            local model = sanitize(result)
            result:Destroy()
            if not model then warn("[PotionModels] no mesh parts in", key, assetId) return end
            model.Name = key
            model.Parent = folder
        end)
    end
end

return Models
