--!strict
local Visual = require(script.Parent.DinosaurVisual)
local RuntimeMeshes = require(script.Parent.RuntimeMeshes)
local Preview = {}
function Preview.add(parent: GuiObject, speciesId: string, gold: boolean): ViewportFrame
    local viewport = Instance.new("ViewportFrame")
    viewport.Name = "DinosaurPreview"
    viewport.BackgroundTransparency = 1
    viewport.Size = UDim2.new(1, 0, 0, 140)
    viewport.Ambient = Color3.fromRGB(178, 204, 213)
    viewport.LightColor = Color3.fromRGB(255, 240, 207)
    viewport.LightDirection = Vector3.new(-1, -1, -1)
    viewport.ZIndex = parent.ZIndex + 1
    viewport.Parent = parent
    local world = Instance.new("WorldModel")
    world.Parent = viewport
    local character = Instance.new("Model")
    character.Parent = world
    local humanoid = Instance.new("Humanoid")
    humanoid.HipHeight = 0
    humanoid.Parent = character
    local root = Instance.new("Part")
    root.Name = "HumanoidRootPart"
    root.Size = Vector3.one
    root.Anchored = true
    root.Transparency = 1
    root.Parent = character
    Visual.render(character, 1, speciesId, gold)
    local ready: RBXScriptConnection?
    ready = RuntimeMeshes.Ready.Event:Connect(function(id)
        if id == speciesId and viewport.Parent then Visual.render(character, 1, speciesId, gold) end
    end)
    viewport.Destroying:Connect(function() if ready then ready:Disconnect() end end)
    local camera = Instance.new("Camera")
    camera.FieldOfView = 34
    camera.CFrame = CFrame.lookAt(Vector3.new(6, 5, -9), Vector3.new(0, 2, .8))
    camera.Parent = viewport
    viewport.CurrentCamera = camera
    local elapsed = 0
    local motion = game:GetService("RunService").RenderStepped:Connect(function(dt)
        if not require(script.Parent.UITheme).MotionEnabled then return end
        local ancestor: Instance? = viewport
        while ancestor do
            if ancestor:IsA("GuiObject") and not ancestor.Visible then return end
            ancestor = ancestor.Parent
        end
        elapsed += dt
        local base = camera.CFrame.Position
        local target = Vector3.new(0,2,.8)
        camera.CFrame = CFrame.lookAt(Vector3.new(6 + math.sin(elapsed*.6)*.8,5,-9),target)
    end)
    viewport.Destroying:Connect(function() motion:Disconnect() end)
    return viewport
end
return Preview
