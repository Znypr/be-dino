--!strict
-- Client-local precipitation pool: bounded instance count and no gameplay collision.
local Lighting=game:GetService("Lighting")
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local Shared=game:GetService("ReplicatedStorage").Shared
local Theme=require(Shared.UITheme)
local player=Players.LocalPlayer
local random=Random.new()
local folder=Instance.new("Folder") folder.Name="LocalWeatherFX" folder.Parent=workspace
local drops={}
for _=1,36 do
    local part=Instance.new("Part") part.Name="Precipitation"
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Material=Enum.Material.Neon part.Transparency=1 part.Parent=folder
    table.insert(drops,{part=part,x=random:NextNumber(-20,20),z=random:NextNumber(-20,20),y=random:NextNumber(-10,20)})
end
local flash=Instance.new("ColorCorrectionEffect") flash.Name="ThunderFlash" flash.Parent=Lighting
local nextFlash=0 local flashUntil=0
local moon=Instance.new("Part") moon.Name="EventMoon" moon.Shape=Enum.PartType.Ball
moon.Anchored,moon.CanCollide,moon.CanTouch,moon.CanQuery,moon.CastShadow=true,false,false,false,false
moon.Size,moon.Material,moon.Color,moon.Transparency,moon.Parent=Vector3.one*18,Enum.Material.Neon,Color3.fromRGB(255,95,125),1,folder
local skyPoints={} local skyBeams={}
for i=1,7 do
    local point=Instance.new("Attachment") point.Parent=workspace.Terrain table.insert(skyPoints,point)
    if i>1 then
        local beam=Instance.new("Beam") beam.Attachment0,beam.Attachment1=skyPoints[i-1],point
        beam.FaceCamera,beam.Width0,beam.Width1,beam.LightEmission,beam.Segments=true,12,12,1,16
        beam.Texture="rbxasset://textures/particles/smoke_main.dds"
        beam.TextureMode,beam.TextureSpeed=Enum.TextureMode.Stretch,.05
        beam.Color=ColorSequence.new(Color3.fromRGB(84,255,189),Color3.fromRGB(168,122,255))
        beam.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,.85),NumberSequenceKeypoint.new(.5,.45),NumberSequenceKeypoint.new(1,.85)})
        beam.Enabled,beam.Parent=false,folder table.insert(skyBeams,beam)
    end
end
local atmosphere=Instance.new("ColorCorrectionEffect") atmosphere.Name="LocalEventColor" atmosphere.Parent=Lighting
local elapsed=0
RunService.Heartbeat:Connect(function(dt)
    elapsed+=dt
    if elapsed<1/30 then return end
    dt=elapsed elapsed=0
    local id=workspace:GetAttribute("WeatherId") or "clear"
    local c=player.Character
    local root=if c then c:FindFirstChild("HumanoidRootPart") else nil
    local on=table.find({"rain","thunder","blizzard","volcano","quake"},id)~=nil and Theme.MotionEnabled and root~=nil
    for _,drop in drops do
        local part=drop.part
        part.Transparency=if on then .35 else 1
        if on then
            drop.y-=dt*(if id=="blizzard" then 6 elseif id=="volcano" then -7 elseif id=="quake" then 4 else 48)
            if drop.y< -10 then drop.y=20 drop.x=random:NextNumber(-20,20) drop.z=random:NextNumber(-20,20) end
            if drop.y>20 then drop.y=-10 end
            part.Size=if id=="blizzard" or id=="volcano" then Vector3.one*.15 elseif id=="quake" then Vector3.one*.28 else Vector3.new(.04,1.7,.04)
            part.Color=if id=="blizzard" then Color3.new(1,1,1) elseif id=="volcano" then Color3.fromRGB(255,140,67) elseif id=="quake" then Color3.fromRGB(202,182,142) else Color3.fromRGB(125,197,239)
            part.Position=root.Position+Vector3.new(drop.x,drop.y,drop.z)
        end
    end
    local now=os.clock()
    if id=="thunder" and on and now>=nextFlash then nextFlash=now+random:NextNumber(12,25) flashUntil=now+.12 end
    flash.Brightness=if id=="thunder" and on and now<flashUntil then .25 else 0
    local skyOn=Theme.MotionEnabled and root~=nil
    moon.Transparency=if skyOn and id=="bloodmoon" then .12 else 1
    if skyOn then
        moon.Position=root.Position+Vector3.new(-80,90,-130)
        for i,point in skyPoints do point.Position=root.Position+Vector3.new((i-4)*24,65+math.sin(now*.25+i)*7,-75) end
    end
    for _,beam in skyBeams do beam.Enabled=skyOn and id=="aurora" beam.CurveSize0=math.sin(now*.3)*8 beam.CurveSize1=-beam.CurveSize0 end
    atmosphere.TintColor=if skyOn and id=="bloodmoon" then Color3.fromRGB(255,200,215) elseif skyOn and id=="volcano" then Color3.fromRGB(255,226,194) elseif skyOn and id=="aurora" then Color3.fromRGB(215,243,255) else Color3.new(1,1,1)
    if c then
        local rootPart=c:FindFirstChild("HumanoidRootPart")
        if rootPart then for _,part in rootPart:GetDescendants() do if part:IsA("ParticleEmitter") and part.Name=="AuraParticles" then part.Enabled=Theme.MotionEnabled end end end
    end
end)
