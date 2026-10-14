--!strict
-- Fit actual geometry, excluding controller roots and invisible humanoid parts.
local RunService = game:GetService("RunService")
local Theme = require(script.Parent.UITheme)
local Geometry = require(script.Parent.ResourceGeometry)
local PreviewCamera = {}
function PreviewCamera.bind(viewport: ViewportFrame, model: Model, geometryId: string?)
    local camera=Instance.new("Camera")
    camera.FieldOfView,camera.Parent=32,viewport
    viewport.CurrentCamera=camera
    local bounds,size=model:GetBoundingBox()
    local points={}
    local data=if geometryId and not model:GetAttribute("UploadedModelId") then Geometry[geometryId] else nil
    local origin=model:GetAttribute("GeometryOrigin") or Vector3.zero
    if data then
        for _,v in data.vertices do table.insert(points,model:GetPivot():PointToWorldSpace(Vector3.new(v[1],v[2],v[3])-origin)) end
    else
        for _,x in {-1,1} do for _,y in {-1,1} do for _,z in {-1,1} do
            table.insert(points,bounds:PointToWorldSpace(Vector3.new(x*size.X/2,y*size.Y/2,z*size.Z/2)))
        end end end
    end
    local low,high=Vector3.new(math.huge,math.huge,math.huge),Vector3.new(-math.huge,-math.huge,-math.huge)
    for _,p in points do low=low:Min(p) high=high:Max(p) end
    local target=(low+high)/2
    local elapsed=0
    local function frame(dt: number)
        if Theme.MotionEnabled then elapsed+=dt end
        local direction=Vector3.new(1+math.sin(elapsed*.5)*.035,.2,-.65).Unit
        -- BD-149 inspect: InspectView turns the dino by orbiting the camera around the vertical axis (and keeps the
        -- light with the camera); InspectZoom pulls it closer. Previews without the attributes are unchanged.
        local yaw=viewport:GetAttribute("InspectYaw")
        if typeof(yaw)=="number" then
            local turn=CFrame.Angles(0,-yaw,0)
            direction=turn:VectorToWorldSpace(direction)
            viewport.LightDirection=turn:VectorToWorldSpace(Vector3.new(-1,-1,-1))
        end
        local zoom=viewport:GetAttribute("InspectZoom")
        local basis=CFrame.lookAt(target+direction,target)
        local pixels=viewport.AbsoluteSize
        local aspect=if pixels.Y>0 then pixels.X/pixels.Y else 1.4
        local vertical=math.tan(math.rad(camera.FieldOfView/2))
        local horizontal=vertical*math.max(.3,aspect)
        local distance=0
        for _,point in points do
            local corner=point-target
            local depth=corner:Dot(basis.ZVector)
            distance=math.max(distance,depth+math.abs(corner:Dot(basis.XVector))/horizontal,depth+math.abs(corner:Dot(basis.YVector))/vertical)
        end
        camera.CFrame=CFrame.lookAt(target+direction*math.max(1,distance*1.045/(if typeof(zoom)=="number" and zoom>0 then zoom else 1)),target)
    end
    frame(0)
    local resized=viewport:GetPropertyChangedSignal("AbsoluteSize"):Connect(function() frame(0) end)
    local inspectYaw=viewport:GetAttributeChangedSignal("InspectYaw"):Connect(function() frame(0) end)
    local inspectZoom=viewport:GetAttributeChangedSignal("InspectZoom"):Connect(function() frame(0) end)
    local motion=RunService.RenderStepped:Connect(function(dt)
        if not Theme.MotionEnabled then return end
        local ancestor: Instance?=viewport
        while ancestor do
            if ancestor:IsA("GuiObject") and not ancestor.Visible then return end
            if ancestor:IsA("ScreenGui") and not ancestor.Enabled then return end
            ancestor=ancestor.Parent
        end
        -- Camera orbit does not need a full geometry fit on every rendered frame.
        elapsed+=dt
        if elapsed-(viewport:GetAttribute("LastOrbitUpdate") or 0)<1/30 then return end
        viewport:SetAttribute("LastOrbitUpdate",elapsed)
        frame(0)
    end)
    local function cleanup() resized:Disconnect();inspectYaw:Disconnect();inspectZoom:Disconnect();motion:Disconnect();camera:Destroy() end
    viewport.Destroying:Once(cleanup)
    model.Destroying:Once(cleanup)
end
return PreviewCamera
