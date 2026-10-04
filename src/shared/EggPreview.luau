--!strict
-- Smooth built-in sphere geometry, no uploaded mesh or editable APIs required.
local Egg={}
function Egg.create(empty: boolean?): Model
    local model=Instance.new("Model")
    model.Name="SmoothEggPreview"
    local function sphere(name: string,position: Vector3,scale: Vector3,color: Color3)
        local part=Instance.new("Part")
        part.Name,part.Size,part.CFrame=name,scale,CFrame.new(position)
        part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery=true,false,false,false
        part.Color,part.Material= color,Enum.Material.SmoothPlastic
        part.Transparency=if empty then .48 else 0
        part.Parent=model
        local mesh=Instance.new("SpecialMesh")
        mesh.MeshType,mesh.Scale,mesh.Parent=Enum.MeshType.Sphere,Vector3.one,part
        return part
    end
    sphere("Shell",Vector3.new(0,1.2,0),Vector3.new(1.55,2.3,1.55),if empty then Color3.fromRGB(182,183,199) else Color3.fromRGB(255,237,182))
    if not empty then
        for i,p in {Vector3.new(.49,1.58,-.59),Vector3.new(-.32,.94,-.66),Vector3.new(.17,2.01,-.43),Vector3.new(-.68,1.48,-.21)} do
            sphere("JadePatch"..i,p,Vector3.new(.32,.36,.12),Color3.fromRGB(58,172,117))
        end
    end
    model.WorldPivot=CFrame.new()
    return model
end
return Egg
