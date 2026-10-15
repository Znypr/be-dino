--!strict
-- Client-local authored meshes. Twelve live allocations, released with their models.
local Assets=game:GetService("AssetService")
local RunService=game:GetService("RunService")
local Http=game:GetService("HttpService")
local Gate=require(script.Parent.LoadGate)
local Creatures={}
local Sanity=require(script.Parent.MeshSanity)
-- At most a few concurrent EditableMesh builds. Extra patient requests wait for a slot instead of failing.
local gate=Gate.new(4)
Creatures.Gate=gate
local function frame(v) return CFrame.new(table.unpack(v)) end
-- Used only when the caller has no genes (e.g. index entry never hatched); real genes are painted in place.
Creatures.DefaultGenes={conditionId="normal",hatchSuccess=true,primaryColorId="green",secondaryColorId="white",blend=70,patternId="03_round_spots"}
function Creatures.has(id: string): boolean
    local source=script.Parent:FindFirstChild("CreatureData")
    return source~=nil and source:FindFirstChild(id)~=nil and RunService:IsClient()
end
local function build(id: string,genes: any?,patient: boolean): Model?
    local source=script.Parent:FindFirstChild("CreatureData")
    local module=if source then source:FindFirstChild(id) else nil
    if not module or not RunService:IsClient() then return nil end
    if patient then
        if not Gate.acquire(gate,6,os.clock,task.wait) then return nil end
    elseif not Gate.tryAcquire(gate) then return nil end
    local mesh
    local released=false
    local function release() if not released then released=true Gate.release(gate) end end
    local ok,result=pcall(function()
        local data=Http:JSONDecode(require(module))
        mesh=Assets:CreateEditableMesh()
        assert(mesh,"EditableMesh memory budget exhausted")
        local vertices,bones,uvs,normals={},{},{},{}
        local low,high=Vector3.new(math.huge,math.huge,math.huge),Vector3.new(-math.huge,-math.huge,-math.huge)
        for _,p in data.vertices do
            local v=Vector3.new(table.unpack(p))
            low,high=low:Min(v),high:Max(v)
            table.insert(vertices,mesh:AddVertex(v))
        end
        for _,b in data.bones do
            local params={Name=b.name,CFrame=frame(b.bind),Virtual=false}
            if b.parent>0 then params.ParentId=bones[b.parent] end
            table.insert(bones,mesh:AddBone(params))
        end
        for i,pairs in data.weights do
            local bs,ws={},{}
            for _,pair in pairs do table.insert(bs,bones[pair[1]]);table.insert(ws,pair[2]) end
            if #bs>0 then mesh:SetVertexBones(vertices[i],bs);mesh:SetVertexBoneWeights(vertices[i],ws) end
        end
        for _,uv in data.uvs do table.insert(uvs,mesh:AddUV(Vector2.new(table.unpack(uv)))) end
        for _,n in data.normals do table.insert(normals,mesh:AddNormal(Vector3.new(table.unpack(n)))) end
        for i,tri in data.faces do
            local f=mesh:AddTriangle(vertices[tri[1]],vertices[tri[2]],vertices[tri[3]])
            local n=(i-1)*3+1
            mesh:SetFaceUVs(f,{uvs[n],uvs[n+1],uvs[n+2]})
            mesh:SetFaceNormals(f,{normals[n],normals[n+1],normals[n+2]})
        end
        local part=Assets:CreateMeshPartAsync(Content.fromObject(mesh),{CollisionFidelity=Enum.CollisionFidelity.Box})
        -- The MeshPart owns a copy: free the EditableMesh budget now, not when the model dies. Holding it made menus and
        -- previews exhaust the budget so the real character fell back to the primitive blob.
        mesh:Destroy() mesh=nil
        release()
        -- A MeshPart whose mesh did not really load renders as a plain cube/box: treat it as a failed load (retried by clone).
        local ok2,why=Sanity.check(high-low,part.Size,data.triangles)
        if not ok2 then part:Destroy() error("mesh sanity failed: "..tostring(why)) end
        local model=Instance.new("Model")
        model.Name=id
        part.Name="AuthoredBody";part.Anchored=true;part.CanCollide=false;part.CanTouch=false;part.CanQuery=false;part.Massless=true
        part.Material=Enum.Material.Plastic;part.Reflectance=0;part.Color=Color3.new(1,1,1) -- BD-173: matte; only fused tiers (Gold/Emerald/Diamond) get a sheen, set elsewhere
        part:SetAttribute("GeneSpecies",id);part.Parent=model
        model.WorldPivot=CFrame.new(0,-data.height/2,0)
        model:SetAttribute("AuthoredCreature",true)
        model:SetAttribute("Triangles",data.triangles)
        local nodes,clips={},{Idle={},Move={}}
        for i,b in data.bones do
            local node=Instance.new("Bone");node.Name=b.name
            node.CFrame=if b.parent>0 then frame(data.bones[b.parent].bind):Inverse()*frame(b.bind) else frame(b.bind)
            node.Parent=if b.parent>0 then nodes[b.parent] else part
            nodes[i]=node
        end
        for name,samples in data.animations do
            for _,sample in samples do
                local pose={};for _,v in sample do table.insert(pose,frame(v)) end
                table.insert(clips[name],pose)
            end
        end
        local elapsed,accumulator=0,0
        local connection=RunService.Heartbeat:Connect(function(dt)
            accumulator+=dt;if accumulator<1/15 or not model.Parent then return end
            elapsed+=accumulator;accumulator=0
            if not require(script.Parent.UITheme).MotionEnabled then return end
            local character=model.Parent
            local root=if character:IsA("Model") then character:FindFirstChild("HumanoidRootPart") else nil
            local camera=workspace.CurrentCamera
            if root and camera and (camera.CFrame.Position-root.Position).Magnitude>180 then return end
            local clip=if root and root.AssemblyLinearVelocity.Magnitude>2 then clips.Move else clips.Idle
            local position=(elapsed%1)*4
            local index=math.floor(position)+1;local blend=position%1
            local scale=model:GetScale()
            for i,node in nodes do
                local pose=clip[index][i]:Lerp(clip[index+1][i],blend)
                node.Transform=pose.Rotation+pose.Position*scale
            end
        end)
        require(script.Parent.PatternGenes).apply(part,if genes then genes else Creatures.DefaultGenes)
        model.Destroying:Once(function() connection:Disconnect() end)
        return model
    end)
    if ok then return result end
    if mesh then mesh:Destroy() end
    release()
    warn("Be Dino creature unavailable: "..id.." ("..tostring(result)..")")
    return nil
end
-- patient=true (previews): waits for a load slot and retries once; callers must be able to yield.
function Creatures.clone(id: string,genes: any?,patient: boolean?): Model?
    local model=build(id,genes,patient==true)
    if not model and patient==true and Creatures.has(id) then
        for _,delay in {.4,1.2} do
            task.wait(delay)
            model=build(id,genes,true)
            if model then break end
        end
    end
    return model
end
return Creatures
