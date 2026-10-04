--!strict
-- Fit actual geometry, excluding controller roots and invisible humanoid parts.
local RunService = game:GetService("RunService")
local Theme = require(script.Parent.UITheme)
local PreviewCamera = {}
function PreviewCamera.bind(viewport: ViewportFrame, model: Model)
    local camera=Instance.new("Camera")
    camera.FieldOfView,camera.Parent=32,viewport
    viewport.CurrentCamera=camera
    local bounds,size=model:GetBoundingBox()
    local target=bounds.Position
    local elapsed=0
    local function frame(dt: number)
        if Theme.MotionEnabled then elapsed+=dt end
        local direction=Vector3.new(.65+math.sin(elapsed*.5)*.06,.28,-1).Unit
        local basis=CFrame.lookAt(target+direction,target)
        local pixels=viewport.AbsoluteSize
        local aspect=if pixels.Y>0 then pixels.X/pixels.Y else 1.4
        local vertical=math.tan(math.rad(camera.FieldOfView/2))
        local horizontal=vertical*math.max(.3,aspect)
        local distance=0
        for _,x in {-1,1} do for _,y in {-1,1} do for _,z in {-1,1} do
            local corner=bounds:PointToWorldSpace(Vector3.new(x*size.X/2,y*size.Y/2,z*size.Z/2))-target
            local depth=corner:Dot(basis.ZVector)
            distance=math.max(distance,depth+math.abs(corner:Dot(basis.XVector))/horizontal,depth+math.abs(corner:Dot(basis.YVector))/vertical)
        end end end
        camera.CFrame=CFrame.lookAt(target+direction*math.max(1,distance*1.16),target)
    end
    frame(0)
    local resized=viewport:GetPropertyChangedSignal("AbsoluteSize"):Connect(function() frame(0) end)
    local motion=RunService.RenderStepped:Connect(function(dt)
        if not Theme.MotionEnabled then return end
        local ancestor: Instance?=viewport
        while ancestor do
            if ancestor:IsA("GuiObject") and not ancestor.Visible then return end
            ancestor=ancestor.Parent
        end
        frame(dt)
    end)
    viewport.Destroying:Connect(function() resized:Disconnect() motion:Disconnect() end)
end
return PreviewCamera
