--!strict
-- Client-local authored creatures (16 species + the egg) from CreatureData.
--
-- BD-219 root cause (Studio evidence, docs/96): AssetService:CreateMeshPartAsync(Content.fromObject(mesh)) does NOT
-- copy the geometry into the MeshPart. The part's MeshContent keeps pointing at the EditableMesh, so once that mesh is
-- destroyed the content has 0 faces and the part, and EVERY clone of it (world or ViewportFrame), renders as a box of
-- the right Size. The old build destroyed the mesh right after creating the part ("the MeshPart owns a copy": wrong).
--
-- Now: ONE template per species, built once and kept for the whole session (its EditableMesh stays alive: at most 17
-- small meshes, 916-2,010 triangles each, instead of one allocation per instance). Every instance is a Clone of the
-- template part, which shares the live mesh. An uploaded mesh (CreatureMeshAssets or ReplicatedStorage.CreatureMeshes)
-- is preferred when bound. Before anything is returned the content itself is checked (MeshSanity.contentLoaded): a part
-- whose mesh is not really loaded is never handed out, so callers fall back to a 2D picture, never a cube.
local Assets=game:GetService("AssetService")
local RunService=game:GetService("RunService")
local Http=game:GetService("HttpService")
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local Gate=require(script.Parent.LoadGate)
local Creatures={}
local Sanity=require(script.Parent.MeshSanity)
local Bindings=require(script.Parent.CreatureMeshAssets)
-- At most a few concurrent template builds. Extra requests wait for a slot instead of failing.
local gate=Gate.new(4)
Creatures.Gate=gate
local function frame(v) return CFrame.new(table.unpack(v)) end
-- Used only when the caller has no genes (e.g. index entry never hatched); real genes are painted in place.
Creatures.DefaultGenes={conditionId="normal",hatchSuccess=true,primaryColorId="green",secondaryColorId="white",blend=70,patternId="03_round_spots"}
type Template={part: MeshPart,mesh: EditableMesh?,source: string,bones: {any},animations: any,height: number,triangles: number,extent: Vector3}
local templates: {[string]: Template}={}
local building: {[string]: boolean}={}
local function publish()
    local live=0
    for _,t in templates do if t.mesh then live+=1 end end
    pcall(function() workspace:SetAttribute("AuthoredMeshesLive",live) end)
end
function Creatures.has(id: string): boolean
    local source=script.Parent:FindFirstChild("CreatureData")
    return source~=nil and source:FindFirstChild(id)~=nil and RunService:IsClient()
end
-- Content-level check: true only when the part really has mesh geometry to draw (never a box). Pure logic in MeshSanity.
function Creatures.isLoaded(part: Instance): (boolean,string?)
    if not part:IsA("MeshPart") then return true,nil end
    local content=part.MeshContent
    local sourceType=if content then content.SourceType.Name else "None"
    local faces: number?=nil
    if sourceType=="Object" then
        local object=content.Object
        if object then
            local ok,count=pcall(function() return #(object :: any):GetFaces() end)
            if ok and typeof(count)=="number" then faces=count end
        end
    end
    return Sanity.contentLoaded(sourceType,faces,part.MeshId)
end
-- Every MeshPart of a model is loaded (an authored body or an imported part). Used by previews before showing anything.
function Creatures.verify(model: Instance): (boolean,string?)
    for _,item in model:GetDescendants() do
        if item:IsA("MeshPart") then
            local ok,why=Creatures.isLoaded(item)
            if not ok then return false,item.Name..": "..tostring(why) end
        end
    end
    return true,nil
end
local function extentOf(data): Vector3
    local low,high=Vector3.new(math.huge,math.huge,math.huge),Vector3.new(-math.huge,-math.huge,-math.huge)
    for _,p in data.vertices do
        local v=Vector3.new(table.unpack(p))
        low,high=low:Min(v),high:Max(v)
    end
    return high-low
end
local function prepare(part: MeshPart)
    for _,child in part:GetChildren() do child:Destroy() end -- bones/decals are rebuilt per instance from CreatureData
    part.Name="AuthoredBody";part.Anchored=true;part.CanCollide=false;part.CanTouch=false;part.CanQuery=false;part.Massless=true
    part.Material=Enum.Material.Plastic;part.Reflectance=0;part.Color=Color3.new(1,1,1) -- BD-173: matte; only fused tiers get a sheen, set elsewhere
    part.TextureID="";part.TextureContent=Content.none
end
-- Uploaded mesh first (binding id, or an imported MeshPart dropped into ReplicatedStorage.CreatureMeshes); nil when none.
local function uploadedPart(id: string,extent: Vector3,triangles: number): MeshPart?
    local binding=Bindings[id]
    local candidates: {() -> MeshPart?}={}
    if binding and typeof(binding.meshId)=="string" and binding.meshId~="" then
        table.insert(candidates,function()
            return Assets:CreateMeshPartAsync(Content.fromUri(binding.meshId),{CollisionFidelity=Enum.CollisionFidelity.Box,RenderFidelity=Enum.RenderFidelity.Automatic})
        end)
    end
    local folder=ReplicatedStorage:FindFirstChild("CreatureMeshes")
    local dropIn=if folder then folder:FindFirstChild(id) else nil
    if dropIn and dropIn:IsA("MeshPart") then table.insert(candidates,function() return (dropIn :: MeshPart):Clone() end) end
    for _,make in candidates do
        local ok,part=pcall(make)
        if ok and part then
            local good,why=Sanity.check(extent,part.Size,triangles)
            local loaded,why2=Creatures.isLoaded(part)
            if good and loaded then prepare(part) return part end
            warn("Be Dino uploaded mesh for "..id.." rejected ("..tostring(why or why2).."); using the runtime mesh")
            part:Destroy()
        elseif not ok then warn("Be Dino uploaded mesh for "..id.." failed: "..tostring(part)) end
    end
    return nil
end
local function runtimePart(data,extent: Vector3): (MeshPart,EditableMesh)
    local mesh=Assets:CreateEditableMesh()
    assert(mesh,"EditableMesh memory budget exhausted")
    local ok,result=pcall(function()
        local vertices,bones,uvs,normals={},{},{},{}
        for _,p in data.vertices do table.insert(vertices,mesh:AddVertex(Vector3.new(table.unpack(p)))) end
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
        -- The EditableMesh is NOT destroyed: the part renders from it for as long as the template lives (see header).
        local part=Assets:CreateMeshPartAsync(Content.fromObject(mesh),{CollisionFidelity=Enum.CollisionFidelity.Box})
        local good,why=Sanity.check(extent,part.Size,data.triangles)
        if not good then part:Destroy() error("mesh sanity failed: "..tostring(why)) end
        local loaded,why2=Creatures.isLoaded(part)
        if not loaded then part:Destroy() error("mesh content not loaded: "..tostring(why2)) end
        prepare(part)
        return part
    end)
    if not ok then mesh:Destroy() error(result) end
    return result,mesh
end
local function dropTemplate(id: string)
    local t=templates[id]
    if not t then return end
    templates[id]=nil
    if t.mesh then t.mesh:Destroy() end
    t.part:Destroy()
    publish()
end
-- Builds (or waits for) the species template. Yields. nil when the data or the mesh APIs are unavailable.
local function template(id: string,timeout: number): Template?
    local source=script.Parent:FindFirstChild("CreatureData")
    local module=if source then source:FindFirstChild(id) else nil
    if not module or not RunService:IsClient() then return nil end
    local started=os.clock()
    while building[id] do
        if os.clock()-started>timeout then return nil end
        task.wait(.05)
    end
    local existing=templates[id]
    if existing then
        -- A template whose mesh died (budget reclaim, Destroy by someone else) must never be cloned into a box.
        if Creatures.isLoaded(existing.part) then return existing end
        warn("Be Dino creature template for "..id.." lost its mesh; rebuilding")
        dropTemplate(id)
    end
    if not Gate.acquire(gate,math.max(0,timeout-(os.clock()-started)),os.clock,task.wait) then return nil end
    building[id]=true
    local ok,result=pcall(function()
        local data=Http:JSONDecode(require(module))
        local extent=extentOf(data)
        local part=uploadedPart(id,extent,data.triangles)
        local mesh: EditableMesh?=nil
        local sourceName="uploaded"
        if not part then part,mesh=runtimePart(data,extent) sourceName="runtime" end
        local t: Template={part=part,mesh=mesh,source=sourceName,bones=data.bones,animations=data.animations,height=data.height,triangles=data.triangles,extent=extent}
        templates[id]=t
        return t
    end)
    building[id]=nil
    Gate.release(gate)
    publish()
    if ok then return result end
    warn("Be Dino creature unavailable: "..id.." ("..tostring(result)..")")
    return nil
end
-- Live instance parts per species (weak keys): the watchdog re-applies a rebuilt template mesh to them.
local instances: {[string]: {[MeshPart]: any}}={} -- part -> genes it was painted with
local function instance(id: string,t: Template,genes: any?): Model?
    local part=t.part:Clone()
    local loaded,why=Creatures.isLoaded(part)
    if not loaded then part:Destroy() warn("Be Dino creature clone for "..id.." has no mesh ("..tostring(why)..")") return nil end
    local list=instances[id]
    if not list then list=setmetatable({},{__mode="k"}) :: any instances[id]=list end
    list[part]=if genes then genes else Creatures.DefaultGenes
    local model=Instance.new("Model")
    model.Name=id
    part:SetAttribute("GeneSpecies",id);part:SetAttribute("MeshSource",t.source);part.Parent=model
    model.WorldPivot=CFrame.new(0,-t.height/2,0)
    model:SetAttribute("AuthoredCreature",true)
    model:SetAttribute("Triangles",t.triangles)
    model:SetAttribute("MeshSource",t.source)
    local nodes,clips={},{Idle={},Move={}}
    for i,b in t.bones do
        local node=Instance.new("Bone");node.Name=b.name
        node.CFrame=if b.parent>0 then frame(t.bones[b.parent].bind):Inverse()*frame(b.bind) else frame(b.bind)
        node.Parent=if b.parent>0 then nodes[b.parent] else part
        nodes[i]=node
    end
    for name,samples in t.animations do
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
end
-- patient=true (previews): waits longer for a build slot and retries; callers must be able to yield (both paths yield
-- while the species template is first built; later clones are immediate).
function Creatures.clone(id: string,genes: any?,patient: boolean?): Model?
    local timeout=if patient==true then 6 else 2
    local t=template(id,timeout)
    local model=if t then instance(id,t,genes) else nil
    if not model and patient==true and Creatures.has(id) then
        for _,delay in {.4,1.2} do
            task.wait(delay)
            t=template(id,timeout)
            model=if t then instance(id,t,genes) else nil
            if model then break end
        end
    end
    return model
end
-- Watchdog (client): if a species template loses its mesh after instances were handed out (engine budget reclaim, a
-- stray Destroy), every live instance would turn into a box. Rebuild the template and re-apply its mesh to the live
-- parts (MeshPart:ApplyMesh); when that is impossible the parts are hidden (invisible, never a cube).
function Creatures.sweep(): number
    local repaired=0
    for id,list in instances do
        local t=templates[id]
        if t and Creatures.isLoaded(t.part) then continue end
        local alive={}
        for part,genes in list do if part.Parent then table.insert(alive,{part=part,genes=genes}) end end
        if #alive==0 then continue end
        local rebuilt=template(id,2)
        for _,entry in alive do
            local part=entry.part
            if rebuilt then
                -- ApplyMesh copies the template's (blank) texture too, so the pattern is painted again afterwards.
                local ok=pcall(function() part:ApplyMesh(rebuilt.part) end)
                if ok and Creatures.isLoaded(part) then
                    pcall(function() require(script.Parent.PatternGenes).refresh(part,entry.genes) end)
                    part.Transparency=0 part:SetAttribute("MeshLost",nil) repaired+=1 continue
                end
            end
            part.Transparency=1 part:SetAttribute("MeshLost",true)
        end
    end
    return repaired
end
if RunService:IsClient() then
    task.spawn(function() while true do task.wait(2) pcall(Creatures.sweep) end end)
end
-- Diagnostics (Studio): live templates by source.
function Creatures.stats(): {[string]: string}
    local out={}
    for id,t in templates do out[id]=t.source end
    return out
end
return Creatures
