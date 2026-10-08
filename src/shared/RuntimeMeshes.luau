--!strict
-- Build local visual MeshParts from embedded original geometry. Server collision stays separate.
local AssetService = game:GetService("AssetService")
local RunService = game:GetService("RunService")
local Geometry = require(script.Parent.ResourceGeometry)
local RuntimeMeshes = {}
local resourceIds = {}
for id in Geometry do table.insert(resourceIds,id) end
table.sort(resourceIds)
local templates: {[string]: Model} = {}
local editableMeshes: {[string]: EditableMesh} = {}
local started = false
RuntimeMeshes.Ready = Instance.new("BindableEvent")
function RuntimeMeshes.clone(id: string): Model?
    local template = templates[id]
    return if template then template:Clone() else nil
end
function RuntimeMeshes.prepare()
    if started or not RunService:IsClient() then return end
    started = true
    task.spawn(function()
        local succeeded = 0
        for _, id in resourceIds do
            local editable: EditableMesh? = nil
            local ok, result = pcall(function()
                local data = Geometry[id]
                local mesh = AssetService:CreateEditableMesh()
                if not mesh then error("EditableMesh memory unavailable") end
                editable = mesh
                local vertices, colors = {}, {}
                for _, position in data.vertices do
                    table.insert(vertices, mesh:AddVertex(Vector3.new(position[1], position[2], position[3])))
                end
                for _, color in data.colors do
                    table.insert(colors, mesh:AddColor(Color3.new(color[1], color[2], color[3]), 1))
                end
                for _, triangle in data.faces do
                    local face = mesh:AddTriangle(vertices[triangle[1]], vertices[triangle[2]], vertices[triangle[3]])
                    local color = colors[triangle[4]]
                    mesh:SetFaceColors(face, {color, color, color})
                    local a, b, c = data.vertices[triangle[1]], data.vertices[triangle[2]], data.vertices[triangle[3]]
                    local normal = (Vector3.new(b[1]-a[1],b[2]-a[2],b[3]-a[3])):Cross(Vector3.new(c[1]-a[1],c[2]-a[2],c[3]-a[3])).Unit
                    local normalId = mesh:AddNormal(normal)
                    mesh:SetFaceNormals(face, {normalId, normalId, normalId})
                end
                local part = AssetService:CreateMeshPartAsync(Content.fromObject(mesh))
                part.Name = id .. "Mesh"
                part.Color = Color3.new(1, 1, 1)
                part.Material = Enum.Material.SmoothPlastic
                part.Anchored = true
                part.CanCollide, part.CanTouch, part.CanQuery = false, false, false
                part.Massless = true
                -- EditableMesh vertices are relative to mesh bounds center.
                local min, max = Vector3.new(math.huge,math.huge,math.huge), Vector3.new(-math.huge,-math.huge,-math.huge)
                for _, p in data.vertices do
                    local v = Vector3.new(p[1],p[2],p[3])
                    min = Vector3.new(math.min(min.X,v.X),math.min(min.Y,v.Y),math.min(min.Z,v.Z))
                    max = Vector3.new(math.max(max.X,v.X),math.max(max.Y,v.Y),math.max(max.Z,v.Z))
                end
                part.Size = max - min
                part.CFrame = CFrame.new((min + max) / 2)
                local model = Instance.new("Model")
                model.Name = id
                part.Parent = model
                model.WorldPivot = CFrame.new(0, 0, 0)
                return model
            end)
            if ok then
                editableMeshes[id] = editable :: EditableMesh -- preserve the content lifetime
                templates[id] = result
                succeeded += 1
                RuntimeMeshes.Ready:Fire(id)
            else
                if editable then editable:Destroy() end
                warn("[Be Dino] mesh " .. id .. " unavailable: " .. tostring(result))
                -- A permission failure should not cause repeated heavyweight failures.
                if succeeded == 0 then break end
            end
            task.wait()
        end
        workspace:SetAttribute("LocalMeshCount", succeeded)
        workspace:SetAttribute("LocalMeshStatus", if succeeded == #resourceIds then "Ready" else "Enable Mesh / Image APIs or import OBJ assets")
    end)
end
return RuntimeMeshes
