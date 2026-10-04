--!strict
local Resources = require(script.Parent.ResourceModels)
local RuntimeMeshes = require(script.Parent.RuntimeMeshes)
local ModelPreview = {}
function ModelPreview.add(parent: GuiObject, id: string): ViewportFrame
    local viewport = Instance.new("ViewportFrame")
    viewport.Size = UDim2.fromScale(1,1)
    viewport.BackgroundTransparency = 1
    viewport.Ambient = Color3.fromRGB(185,209,209)
    viewport.LightColor = Color3.fromRGB(255,242,214)
    viewport.LightDirection = Vector3.new(-1,-1,-1)
    viewport.ZIndex = parent.ZIndex + 1
    viewport.Parent = parent
    local camera = Instance.new("Camera")
    camera.FieldOfView = 32
    camera.CFrame = CFrame.lookAt(Vector3.new(4,3,-5),Vector3.new(0,1,0))
    camera.Parent = viewport
    viewport.CurrentCamera = camera
    local current: Model? = nil
    local function render()
        if not viewport.Parent then return end
        local model = Resources.clone(id)
        if not model then return end
        if current then current:Destroy() end
        for _, item in model:GetDescendants() do if item:IsA("BasePart") then item.Anchored = true end end
        model:PivotTo(CFrame.new())
        model.Parent = viewport
        current = model
    end
    render()
    local ready = RuntimeMeshes.Ready.Event:Connect(function(name) if name == id then render() end end)
    viewport.Destroying:Connect(function() ready:Disconnect() end)
    return viewport
end
return ModelPreview
