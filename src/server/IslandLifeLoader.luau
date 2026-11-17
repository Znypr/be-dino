--!strict
-- BD-1244 (Config.IslandLifeEnabled): loads the island-life critters (Shared/IslandLife.Critters, generate_mesh Models, docs/77) as one
-- MeshPart each into ReplicatedStorage.IslandLifeModels, for src/client/IslandLife.client.luau. InsertService runs only on the server.
-- A failed load only warns: the client skips that critter. Nothing else is created on the server (the life itself is client-only).
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local InsertService = game:GetService("InsertService")
local Loader = {}

function Loader.load()
    local Life = require(ReplicatedStorage.Shared.IslandLife)
    if not Life.enabled(require(ReplicatedStorage.Shared.Config)) then return end
    local folder = ReplicatedStorage:FindFirstChild(Life.FolderName)
    if not folder then
        folder = Instance.new("Folder")
        folder.Name = Life.FolderName
        folder.Parent = ReplicatedStorage
    end
    for key, asset in Life.Critters do
        task.spawn(function()
            local ok, err = pcall(function()
                local container = InsertService:LoadAsset(tonumber(asset.assetId) :: number)
                local found: MeshPart? = nil
                for _, item in container:GetDescendants() do if item:IsA("MeshPart") then found = item break end end
                assert(found, "generated asset has no MeshPart")
                local mesh = (found :: MeshPart):Clone()
                container:Destroy()
                for _, child in mesh:GetChildren() do if not child:IsA("SurfaceAppearance") then child:Destroy() end end
                mesh.Name = key
                mesh.Anchored, mesh.CanCollide, mesh.CanTouch, mesh.CanQuery, mesh.CastShadow = true, false, false, false, false
                mesh.Parent = folder
            end)
            if not ok then warn("[Be Dino] island life critter " .. key .. " failed to load: " .. tostring(err)) end
        end)
    end
end

return Loader
