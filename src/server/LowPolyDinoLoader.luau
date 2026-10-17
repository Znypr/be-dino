--!strict
-- BD-225 spike: loads the published low-poly dino Models (InsertService:LoadAsset, server only) into
-- ReplicatedStorage.LowPolyDinoModels once, when Config.LowPolyDinos is on. A failed load is skipped: that species keeps its current visual.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local InsertService = game:GetService("InsertService")
local Assets = require(ReplicatedStorage.Shared.LowPolyDinoAssets)
local LowPoly = require(ReplicatedStorage.Shared.LowPolyDinos)
local Loader = {}
function Loader.load(): (number, number)
    if not LowPoly.enabled() then return 0, 0 end
    local folder = ReplicatedStorage:FindFirstChild(LowPoly.FolderName) or Instance.new("Folder")
    folder.Name = LowPoly.FolderName
    folder.Parent = ReplicatedStorage
    local loaded, failed = 0, 0
    local function loadOne(speciesId: string, info: any)
        if folder:FindFirstChild(speciesId) then return end
        local container: Instance? = nil
        local ok, result = pcall(function()
            container = InsertService:LoadAsset(info.assetId)
            local model = Instance.new("Model")
            model.Name = speciesId
            -- Geometry only: MeshParts are copied, scripts and anything else never survive.
            for _, part in (container :: Instance):GetDescendants() do
                if part:IsA("MeshPart") then
                    local copy = part:Clone()
                    for _, child in copy:GetDescendants() do child:Destroy() end
                    copy.Anchored = true
                    copy.Parent = model
                end
            end
            assert(#model:GetChildren() > 0, "no mesh parts")
            return model
        end)
        if container then container:Destroy() end
        if ok then
            (result :: Instance).Parent = folder
            loaded += 1
        else
            failed += 1
            warn("[Be Dino] low-poly " .. speciesId .. " unavailable; keeping current visual: " .. tostring(result))
        end
    end
    -- BD-381: the starter (compy) first, then every other species at once. One after the other took about 25 s, and every menu
    -- preview or world dino built in that window showed the legacy model. The clients also wait for a pending template (LowPoly.pending).
    local running = 0
    if (Assets :: any).compy then loadOne("compy", (Assets :: any).compy) end
    for speciesId, info in Assets :: any do
        if speciesId == "compy" then continue end
        running += 1
        task.spawn(function()
            loadOne(speciesId, info)
            running -= 1
        end)
    end
    while running > 0 do task.wait(0.1) end
    workspace:SetAttribute("LowPolyDinosLoaded", loaded)
    workspace:SetAttribute("LowPolyDinosFailed", failed)
    return loaded, failed
end
return Loader
