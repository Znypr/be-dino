--!strict
-- Fit actual geometry, excluding controller roots and invisible humanoid parts.
local RunService = game:GetService("RunService")
local Theme = require(script.Parent.UITheme)
local Geometry = require(script.Parent.ResourceGeometry)
local Pose = require(script.Parent.LowPolyPose)
local PreviewCamera = {}
-- Owner 2026-10-16: the hatched dino must face the camera (slight 3/4 view), whichever way the model was authored.
-- Imported models face -Z (ResourceModels). Low-poly and other generated models are not guaranteed to: when a part named
-- "head" (Pose.roleOf, same naming as the pose code) sits clearly off the body centre in the horizontal plane, the dino faces that way.
-- Pure: heads / centre are world positions; returns the unit horizontal facing (x, z), default -Z.
function PreviewCamera.facing(centre: Vector3, heads: { Vector3 }): Vector3
    local sum = Vector3.zero
    for _, h in heads do sum += Vector3.new(h.X - centre.X, 0, h.Z - centre.Z) end
    if sum.Magnitude < 0.05 then return Vector3.new(0, 0, -1) end
    return sum.Unit
end
-- Camera offset in the dino's own frame: in front (-Z) and 30 degrees to its left, a little above; rotated onto its facing.
PreviewCamera.LocalDirection = Vector3.new(0.5, 0.2, -0.85).Unit
function PreviewCamera.direction(facing: Vector3, wobble: number): Vector3
    local rotation = CFrame.lookAt(Vector3.zero, facing)
    return rotation:VectorToWorldSpace(Vector3.new(PreviewCamera.LocalDirection.X + wobble, PreviewCamera.LocalDirection.Y, PreviewCamera.LocalDirection.Z)).Unit
end
function PreviewCamera.bind(viewport: ViewportFrame, model: Model, geometryId: string?)
    local camera=Instance.new("Camera")
    camera.FieldOfView,camera.Parent=32,viewport
    viewport.CurrentCamera=camera
    local bounds,size=model:GetBoundingBox()
    local points={}
    local data=if geometryId and not model:GetAttribute("UploadedModelId") then Geometry[geometryId] else nil
    local origin=model:GetAttribute("GeometryOrigin") or Vector3.zero
    local function boxCorners()
        local corners={}
        for _,x in {-1,1} do for _,y in {-1,1} do for _,z in {-1,1} do
            table.insert(corners,bounds:PointToWorldSpace(Vector3.new(x*size.X/2,y*size.Y/2,z*size.Z/2)))
        end end end
        return corners
    end
    if data then
        local gLow,gHigh=Vector3.new(math.huge,math.huge,math.huge),Vector3.new(-math.huge,-math.huge,-math.huge)
        for _,v in data.vertices do
            local local_=Vector3.new(v[1],v[2],v[3])
            gLow,gHigh=gLow:Min(local_),gHigh:Max(local_)
            table.insert(points,model:GetPivot():PointToWorldSpace(local_-origin))
        end
        -- BD-180: the stored mesh only describes the unscaled template. If the live model is bigger or smaller (BIG, gene
        -- scale, species size) its real bounding box is the truth, so the preview can never crop a big or small dino.
        local extent=gHigh-gLow
        local tolerance=.1*math.max(extent.X,extent.Y,extent.Z)
        if math.abs(extent.X-size.X)>tolerance or math.abs(extent.Y-size.Y)>tolerance or math.abs(extent.Z-size.Z)>tolerance then points=boxCorners() end
    else
        points=boxCorners()
    end
    local low,high=Vector3.new(math.huge,math.huge,math.huge),Vector3.new(-math.huge,-math.huge,-math.huge)
    for _,p in points do low=low:Min(p) high=high:Max(p) end
    local target=(low+high)/2
    local heads={}
    for _,part in model:GetDescendants() do
        if part:IsA("BasePart") and Pose.roleOf(part.Name)=="head" then table.insert(heads,part.Position) end
    end
    local facing=PreviewCamera.facing(bounds.Position,heads)
    local elapsed=0
    local function frame(dt: number)
        if Theme.MotionEnabled then elapsed+=dt end
        local direction=PreviewCamera.direction(facing,math.sin(elapsed*.5)*.035) -- elapsed only advances with motion enabled (Reduce Motion: fixed view)
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
        camera.CFrame=CFrame.lookAt(target+direction*math.max(1,distance*1.12/(if typeof(zoom)=="number" and zoom>0 then zoom else 1)),target)
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
