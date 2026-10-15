--!strict
-- Canonical authored egg; built-in geometry remains the API-unavailable fallback.
local Egg={}
-- The condition decoration (ConditionOverlays: a Decal with Face=Front) is projected onto the part's FRONT box face,
-- i.e. the egg's local -Z side (Studio 2026-10-16, docs/96: pointing -Z at the camera shows the marks; pointing the
-- UV-measured -X side there does not). Every egg preview looks along PreviewCamera's direction (1,.2,-.65), so the
-- body is yawed once here so that -Z points at the camera: the marks face the viewer in the shop, the hatch and the
-- Index alike. (Previews PivotTo the identity, so the turn is baked into the part, not the model pivot.)
Egg.DecorationNormal=Vector3.new(0,0,-1)
Egg.CameraDirection=Vector3.new(1,.2,-.65)
local function faceYaw(): number
    local want=Vector3.new(Egg.CameraDirection.X,0,Egg.CameraDirection.Z).Unit
    local have=Vector3.new(Egg.DecorationNormal.X,0,Egg.DecorationNormal.Z).Unit
    -- yaw about Y that turns `have` into `want` (Roblox CFrame.Angles(0,yaw,0) maps x,z -> x cos + z sin, -x sin + z cos;
    -- sign checked in Studio: the negative value turns the chosen side toward the camera, dot = 0.99)
    return -math.atan2(have.X*want.Z-have.Z*want.X,have.X*want.X+have.Z*want.Z)
end
Egg.FaceYaw=faceYaw()
function Egg.create(empty: boolean?): Model
    if not empty then
        local authored=require(script.Parent.AuthoredCreatures).clone("egg",nil,true)
        if authored then
            local body=authored:FindFirstChild("AuthoredBody")
            if body and body:IsA("BasePart") then body.CFrame=CFrame.Angles(0,Egg.FaceYaw,0)*body.CFrame end
            return authored
        end
    end
    local model=Instance.new("Model")
    model.Name="SmoothEggPreview"
    local function sphere(name: string,position: Vector3,scale: Vector3,color: Color3)
        local part=Instance.new("Part")
        part.Name,part.Size,part.CFrame=name,scale,CFrame.new(position)
        part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery=true,false,false,false
        part.Color,part.Material= color,Enum.Material.SmoothPlastic
        part.Transparency=0
        part.Parent=model
        -- A real Ball part (a SpecialMesh sphere can render as a plain cube in a ViewportFrame).
        part.Shape=Enum.PartType.Ball
        return part
    end
    -- Neutral shell only: genes (EggAppearance) supply pattern/colors; empty slots are a flat gray placeholder.
    sphere("Shell",Vector3.new(0,1.2,0),Vector3.new(1.55,2.3,1.55),if empty then Color3.fromRGB(96,100,116) else Color3.fromRGB(255,244,214))
    model.WorldPivot=CFrame.new()
    return model
end
return Egg
