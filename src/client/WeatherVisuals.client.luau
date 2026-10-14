--!strict
-- Weather v2 (docs/84): client-local mood. Lighting grade + haze + bloom per event, particle rigs that follow the
-- player, forked lightning, lava bombs, quake shake, aurora curtains, blood moon and a title card.
-- Nothing here is authoritative or collides; the server only publishes WeatherId / WeatherName.
local Debris=game:GetService("Debris")
local Lighting=game:GetService("Lighting")
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local TweenService=game:GetService("TweenService")
local UserInputService=game:GetService("UserInputService")
local Shared=game:GetService("ReplicatedStorage").Shared
local Theme=require(Shared.UITheme)
local player=Players.LocalPlayer
local random=Random.new()
local phone=UserInputService.TouchEnabled and not UserInputService.MouseEnabled
local DENSITY=if phone then .5 else 1
local TEX_SMOKE="rbxasset://textures/particles/smoke_main.dds"
local TEX_SPARK="rbxasset://textures/particles/sparkles_main.dds"
local TEX_FIRE="rbxasset://textures/particles/fire_main.dds"

local folder=Instance.new("Folder") folder.Name="LocalWeatherFX" folder.Parent=workspace

-- ---------------------------------------------------------------- look (grade + haze + bloom per weather)
type Look={tint:Color3,sat:number,contrast:number,bright:number,fog:Color3,density:number,haze:number,glare:number,bloom:number,rays:number,rayTint:Color3}
local function look(t:{[string]:any}):Look
    return {
        tint=t.tint or Color3.new(1,1,1),sat=t.sat or 0,contrast=t.contrast or 0,bright=t.bright or 0,
        fog=t.fog or Color3.fromRGB(199,214,230),density=t.density or 0,haze=t.haze or 0,glare=t.glare or 0,
        bloom=t.bloom or 0,rays=t.rays or 0,rayTint=t.rayTint or Color3.new(1,1,1),
    }
end
local LOOKS:{[string]:Look}={
    clear=look({}),
    rain=look({tint=Color3.fromRGB(176,196,226),sat=-.18,contrast=.1,bright=-.04,fog=Color3.fromRGB(140,155,178),density=.28,haze=1.8,bloom=.15}),
    thunder=look({tint=Color3.fromRGB(170,182,222),sat=-.18,contrast=.14,bright=-.07,fog=Color3.fromRGB(112,122,156),density=.3,haze=2.2,bloom=.45}),
    blizzard=look({tint=Color3.fromRGB(214,232,255),sat=-.35,contrast=-.08,bright=.06,fog=Color3.fromRGB(232,240,250),density=.68,haze=3.2,bloom=.35,rays=.08,rayTint=Color3.fromRGB(220,235,255)}),
    volcano=look({tint=Color3.fromRGB(255,184,128),sat=.4,contrast=.18,bright=-.06,fog=Color3.fromRGB(255,110,50),density=.4,haze=2.6,glare=.6,bloom=.85,rays=.22,rayTint=Color3.fromRGB(255,150,70)}),
    aurora=look({tint=Color3.fromRGB(176,255,230),sat=.3,contrast=.1,bright=-.06,fog=Color3.fromRGB(60,170,160),density=.24,haze=.8,bloom=.9}),
    quake=look({tint=Color3.fromRGB(232,200,156),sat=-.12,contrast=.14,bright=-.06,fog=Color3.fromRGB(190,160,120),density=.34,haze=2,bloom=.1}),
    bloodmoon=look({tint=Color3.fromRGB(255,112,128),sat=.45,contrast=.2,bright=-.08,fog=Color3.fromRGB(200,28,52),density=.34,haze=2.4,glare=.3,bloom=1,rays=.1,rayTint=Color3.fromRGB(255,60,80)}),
}
local TITLE_COLOR:{[string]:Color3}={
    rain=Color3.fromRGB(110,200,255),thunder=Color3.fromRGB(190,170,255),blizzard=Color3.fromRGB(190,235,255),
    volcano=Color3.fromRGB(255,150,60),aurora=Color3.fromRGB(110,255,200),quake=Color3.fromRGB(235,190,120),bloodmoon=Color3.fromRGB(255,70,100),
}

local grade=Instance.new("ColorCorrectionEffect") grade.Name="WeatherGrade" grade.Parent=Lighting
local bloom=Instance.new("BloomEffect") bloom.Name="WeatherBloom" bloom.Intensity,bloom.Size,bloom.Threshold=0,24,.9 bloom.Parent=Lighting
local rays=Instance.new("SunRaysEffect") rays.Name="WeatherRays" rays.Intensity,rays.Spread=0,.6 rays.Parent=Lighting
local atmosphere=Lighting:FindFirstChildOfClass("Atmosphere")
local ownAtmosphere=false
if not atmosphere then
    atmosphere=Instance.new("Atmosphere") atmosphere.Density,atmosphere.Offset,atmosphere.Glare,atmosphere.Haze=0,0,0,0
    atmosphere.Name="WeatherAtmosphere" atmosphere.Parent=Lighting ownAtmosphere=true
end
local baseAtmo={density=atmosphere.Density,haze=atmosphere.Haze,glare=atmosphere.Glare,color=atmosphere.Color}

-- ---------------------------------------------------------------- particle helpers
local function seq(a:number,b:number,c:number?):NumberSequence
    if c then return NumberSequence.new({NumberSequenceKeypoint.new(0,a),NumberSequenceKeypoint.new(.5,b),NumberSequenceKeypoint.new(1,c)}) end
    return NumberSequence.new(a,b)
end
local function volume(size:Vector3):Part
    local part=Instance.new("Part") part.Name="WeatherVolume" part.Size,part.Transparency=size,1
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Parent=folder return part
end
type Emitter={e:ParticleEmitter,rate:number}
local function emitter(parent:Instance,rate:number,props:{[string]:any}):Emitter
    local e=Instance.new("ParticleEmitter") e.Name="WeatherParticles"
    e.Rate,e.Enabled=0,false e.LockedToPart=false e.LightInfluence=0
    local any:any=e
    for key,value in props do any[key]=value end
    e.Parent=parent
    return {e=e,rate=rate}
end
local rig:{[string]:{Emitter}}={}
local rigParts:{[string]:{part:Part,offset:Vector3,world:boolean?}}={}
local function addRig(id:string,part:Part,offset:Vector3,list:{Emitter})
    rig[id]=rig[id] or {} rigParts[id]=rigParts[id] or {}
    for _,item in list do table.insert(rig[id],item) end
    table.insert(rigParts[id],{part=part,offset=offset})
end
local WIDE=Vector3.new(90,1,90)
local FEET=Vector3.new(0,-2.8,0)

-- RAIN + THUNDER
for _,id in {"rain","thunder"} do
    local heavy=id=="thunder"
    local sky=volume(WIDE)
    local streaks=emitter(sky,(if heavy then 1500 else 950)*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(.55,.7),Speed=NumberRange.new(95,115),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(if heavy then 30 else 10,-70,0),Orientation=Enum.ParticleOrientation.VelocityParallel,
        Size=seq(if heavy then .5 else .38,.38),Squash=seq(-14,-14),Transparency=seq(.35,.15),LightEmission=.6,
        Color=ColorSequence.new(Color3.fromRGB(190,220,255),Color3.fromRGB(140,185,240)),SpreadAngle=Vector2.new(4,4),
    })
    local ground=volume(Vector3.new(60,.2,60))
    local splash=emitter(ground,(if heavy then 260 else 160)*DENSITY,{
        Texture=TEX_SPARK,Lifetime=NumberRange.new(.22,.38),Speed=NumberRange.new(3,7),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,-24,0),Size=seq(.1,.9,0),Transparency=seq(.2,.5,1),LightEmission=.4,
        Color=ColorSequence.new(Color3.fromRGB(215,236,255)),SpreadAngle=Vector2.new(40,40),
    })
    local mist=emitter(ground,10*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(3,4.5),Speed=NumberRange.new(1,3),EmissionDirection=Enum.NormalId.Top,
        Size=seq(16,34),Transparency=seq(1,.82,1),Color=ColorSequence.new(Color3.fromRGB(150,165,185)),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-8,8),
    })
    addRig(id,sky,Vector3.new(0,40,0),{streaks})
    addRig(id,ground,FEET,{splash,mist})
end
-- BLIZZARD
do
    local sky=volume(WIDE)
    local snow=emitter(sky,1100*DENSITY,{
        Texture=TEX_SPARK,Lifetime=NumberRange.new(3,4.2),Speed=NumberRange.new(10,22),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(-46,-6,14),Size=seq(.45,.7),Transparency=seq(.05,.1,.5),LightEmission=.35,Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-90,90),
        Color=ColorSequence.new(Color3.new(1,1,1),Color3.fromRGB(205,230,255)),SpreadAngle=Vector2.new(18,18),
    })
    local side=volume(Vector3.new(2,40,110))
    local gust=emitter(side,40*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(1.4,2),Speed=NumberRange.new(60,85),EmissionDirection=Enum.NormalId.Right,
        Orientation=Enum.ParticleOrientation.VelocityParallel,Size=seq(2.2,2.8),Squash=seq(-10,-10),Transparency=seq(.9,.62,1),
        Color=ColorSequence.new(Color3.fromRGB(235,244,255)),
    })
    local drift=emitter(side,10*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(2.6,3.4),Speed=NumberRange.new(22,34),EmissionDirection=Enum.NormalId.Right,
        Size=seq(22,40),Transparency=seq(1,.78,1),Color=ColorSequence.new(Color3.fromRGB(238,246,255)),Rotation=NumberRange.new(0,360),
    })
    addRig("blizzard",sky,Vector3.new(0,36,0),{snow})
    addRig("blizzard",side,Vector3.new(-70,12,0),{gust,drift})
end
-- VOLCANO (ash, embers, distant eruption column, lava bombs below)
local column=volume(Vector3.new(40,2,40))
do
    local sky=volume(WIDE)
    local ash=emitter(sky,260*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(4,5.5),Speed=NumberRange.new(4,9),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(7,-4,3),Size=seq(.7,1.2),Transparency=seq(.55,.35,.9),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-60,60),
        Color=ColorSequence.new(Color3.fromRGB(70,64,68),Color3.fromRGB(38,34,36)),
    })
    local low=volume(Vector3.new(70,2,70))
    local embers=emitter(low,150*DENSITY,{
        Texture=TEX_SPARK,Lifetime=NumberRange.new(3,5),Speed=NumberRange.new(4,10),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(3,5,0),Size=seq(.5,.35,0),Transparency=seq(0,0,1),LightEmission=1,
        Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(255,235,120)),ColorSequenceKeypoint.new(.5,Color3.fromRGB(255,120,30)),ColorSequenceKeypoint.new(1,Color3.fromRGB(180,30,10))}),
        SpreadAngle=Vector2.new(45,45),
    })
    local plume=emitter(column,34*DENSITY,{
        Texture=TEX_FIRE,Lifetime=NumberRange.new(5,7),Speed=NumberRange.new(70,110),EmissionDirection=Enum.NormalId.Top,
        Size=seq(55,120,180),Transparency=seq(.15,.35,1),LightEmission=1,Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-20,20),
        Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(255,240,150)),ColorSequenceKeypoint.new(.35,Color3.fromRGB(255,120,30)),ColorSequenceKeypoint.new(1,Color3.fromRGB(70,20,10))}),
        SpreadAngle=Vector2.new(12,12),
    })
    local smoke=emitter(column,16*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(8,11),Speed=NumberRange.new(40,70),EmissionDirection=Enum.NormalId.Top,
        Size=seq(120,260,380),Transparency=seq(.35,.5,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-8,8),
        Color=ColorSequence.new(Color3.fromRGB(46,38,38),Color3.fromRGB(28,24,26)),SpreadAngle=Vector2.new(18,18),
    })
    addRig("volcano",sky,Vector3.new(0,40,0),{ash})
    addRig("volcano",low,FEET,{embers})
    rig.volcano=rig.volcano or {} for _,item in {plume,smoke} do table.insert(rig.volcano,item) end
end
-- AURORA (curtains below) + drifting motes
do
    local air=volume(Vector3.new(70,16,70))
    local motes=emitter(air,70*DENSITY,{
        Texture=TEX_SPARK,Lifetime=NumberRange.new(4,6),Speed=NumberRange.new(.5,2),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,1.6,0),Size=seq(0,.7,0),Transparency=seq(1,.1,1),LightEmission=1,Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(110,255,190)),ColorSequenceKeypoint.new(.5,Color3.fromRGB(120,190,255)),ColorSequenceKeypoint.new(1,Color3.fromRGB(220,130,255))}),
    })
    addRig("aurora",air,Vector3.new(0,8,0),{motes})
end
-- QUAKE (dust + falling rubble)
do
    local ground=volume(Vector3.new(70,.2,70))
    local dust=emitter(ground,70*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(3,4.5),Speed=NumberRange.new(3,8),EmissionDirection=Enum.NormalId.Top,
        Size=seq(8,20,30),Transparency=seq(.7,.55,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-14,14),
        Color=ColorSequence.new(Color3.fromRGB(196,170,128),Color3.fromRGB(160,138,104)),SpreadAngle=Vector2.new(30,30),
    })
    local sky=volume(Vector3.new(60,1,60))
    local rubble=emitter(sky,90*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(1.2,1.8),Speed=NumberRange.new(2,6),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(0,-80,0),Size=seq(.8,1.5),Transparency=seq(0,0,.4),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-300,300),
        Color=ColorSequence.new(Color3.fromRGB(110,92,74),Color3.fromRGB(78,70,64)),
    })
    addRig("quake",ground,FEET,{dust})
    addRig("quake",sky,Vector3.new(0,34,0),{rubble})
end
-- BLOOD MOON (red motes + ground haze)
do
    local air=volume(Vector3.new(80,14,80))
    local motes=emitter(air,90*DENSITY,{
        Texture=TEX_SPARK,Lifetime=NumberRange.new(4,6),Speed=NumberRange.new(.5,2.5),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,1.2,0),Size=seq(0,.8,0),Transparency=seq(1,.05,1),LightEmission=1,Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new(Color3.fromRGB(255,60,90),Color3.fromRGB(255,150,170)),
    })
    local ground=volume(Vector3.new(90,.2,90))
    local fogBank=emitter(ground,14*DENSITY,{
        Texture=TEX_SMOKE,Lifetime=NumberRange.new(5,7),Speed=NumberRange.new(1,3),EmissionDirection=Enum.NormalId.Top,
        Size=seq(24,46),Transparency=seq(1,.76,1),Color=ColorSequence.new(Color3.fromRGB(150,16,40)),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-5,5),
    })
    addRig("bloodmoon",air,Vector3.new(0,6,0),{motes})
    addRig("bloodmoon",ground,FEET,{fogBank})
end

-- ---------------------------------------------------------------- sky props: blood moon + aurora curtains
local moonCore=Instance.new("Part") moonCore.Name="EventMoon" moonCore.Shape=Enum.PartType.Ball
moonCore.Anchored,moonCore.CanCollide,moonCore.CanTouch,moonCore.CanQuery,moonCore.CastShadow=true,false,false,false,false
moonCore.Size,moonCore.Material,moonCore.Color,moonCore.Transparency,moonCore.Parent=Vector3.one*90,Enum.Material.Neon,Color3.fromRGB(255,48,76),1,folder
local halos:{Part}={}
for i,spec in {{150,.78},{230,.9},{340,.95}} do
    local halo=moonCore:Clone() halo.Name="EventMoonHalo"..i halo.Size=Vector3.one*spec[1] halo.Transparency=1 halo.Color=Color3.fromRGB(255,40,70) halo.Parent=folder
    table.insert(halos,halo)
end
local MOON_DIR=Vector3.new(-.32,.5,-.8).Unit
local curtains:{{points:{Attachment},beams:{Beam},phase:number,height:number,dist:number}}={}
local CURTAIN_COLORS={
    {Color3.fromRGB(70,255,150),Color3.fromRGB(60,230,220)},
    {Color3.fromRGB(80,200,255),Color3.fromRGB(150,120,255)},
    {Color3.fromRGB(190,110,255),Color3.fromRGB(255,110,200)},
    {Color3.fromRGB(110,255,190),Color3.fromRGB(120,255,120)},
}
for c=1,4 do
    local points:{Attachment}={} local beams:{Beam}={}
    for i=1,10 do
        local a=Instance.new("Attachment") a.Parent=workspace.Terrain table.insert(points,a)
        if i>1 then
            local beam=Instance.new("Beam") beam.Attachment0,beam.Attachment1=points[i-1],a
            beam.FaceCamera,beam.Width0,beam.Width1,beam.LightEmission,beam.LightInfluence,beam.Segments=true,38,38,1,0,8
            beam.Texture=TEX_SMOKE beam.TextureMode,beam.TextureLength=Enum.TextureMode.Stretch,1
            beam.Color=ColorSequence.new(CURTAIN_COLORS[c][1],CURTAIN_COLORS[c][2])
            beam.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.25,.55),NumberSequenceKeypoint.new(.75,.55),NumberSequenceKeypoint.new(1,1)})
            beam.Enabled=false beam.Parent=folder table.insert(beams,beam)
        end
    end
    table.insert(curtains,{points=points,beams=beams,phase=c*1.7,height=70+c*14,dist=150+c*28})
end

-- ---------------------------------------------------------------- one-shot effects
local transient:{{update:(number)->boolean}}={}
local function worldAttachment(position:Vector3):Attachment
    local a=Instance.new("Attachment") a.WorldPosition=position a.Parent=workspace.Terrain return a
end
local rayParams=RaycastParams.new() rayParams.FilterType=Enum.RaycastFilterType.Exclude rayParams.FilterDescendantsInstances={folder}
local function groundAt(position:Vector3):Vector3
    local hit=workspace:Raycast(position+Vector3.new(0,260,0),Vector3.new(0,-600,0),rayParams)
    return if hit then hit.Position else Vector3.new(position.X,position.Y-3,position.Z)
end
local flash=0
local shake=0
local function bolt(root:Vector3)
    local angle=random:NextNumber(0,math.pi*2) local dist=random:NextNumber(60,170)
    local top=root+Vector3.new(math.cos(angle)*dist,190,math.sin(angle)*dist)
    local bottom=groundAt(Vector3.new(top.X,root.Y,top.Z))
    local attachments:{Attachment}={} local beams:{Beam}={}
    for i=0,9 do
        local t=i/9 local p=top:Lerp(bottom,t)
        if i>0 and i<9 then p+=Vector3.new(random:NextNumber(-16,16),0,random:NextNumber(-16,16)) end
        table.insert(attachments,worldAttachment(p))
    end
    for i=2,#attachments do
        for layer=1,2 do
            local beam=Instance.new("Beam") beam.Attachment0,beam.Attachment1=attachments[i-1],attachments[i]
            beam.FaceCamera,beam.LightEmission,beam.LightInfluence,beam.Segments=true,1,0,1
            beam.Width0,beam.Width1=if layer==1 then 9 else 2.2,if layer==1 then 6 else 1.4
            beam.Color=ColorSequence.new(if layer==1 then Color3.fromRGB(150,130,255) else Color3.new(1,1,1))
            beam.Transparency=NumberSequence.new(if layer==1 then .55 else 0)
            beam.Parent=folder table.insert(beams,beam)
        end
    end
    local branchFrom=attachments[random:NextInteger(3,6)]
    local branchEnd=worldAttachment(branchFrom.WorldPosition+Vector3.new(random:NextNumber(-60,60),-random:NextNumber(40,80),random:NextNumber(-60,60)))
    table.insert(attachments,branchEnd)
    local fork=Instance.new("Beam") fork.Attachment0,fork.Attachment1=branchFrom,branchEnd fork.FaceCamera,fork.LightEmission,fork.LightInfluence=true,1,0
    fork.Width0,fork.Width1=3,.6 fork.Color=ColorSequence.new(Color3.fromRGB(225,215,255)) fork.Segments=6 fork.CurveSize0=random:NextNumber(-8,8) fork.Parent=folder
    table.insert(beams,fork)
    flash=math.max(flash,.55) shake=math.max(shake,.5)
    local age=0 local flickered=false
    table.insert(transient,{update=function(dt:number):boolean
        age+=dt
        if age>.09 and age<.17 then for _,b in beams do b.Enabled=false end elseif age>=.17 then
            for _,b in beams do b.Enabled=true end
            if not flickered then flickered=true flash=math.max(flash,.4) end
        end
        if age>.42 then
            for _,b in beams do b:Destroy() end
            for _,a in attachments do a:Destroy() end
            return false
        end
        return true
    end})
end

local function ring(position:Vector3,color:Color3,maxSize:number,seconds:number)
    local part=Instance.new("Part") part.Name="ShockRing" part.Shape=Enum.PartType.Cylinder
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Material,part.Color,part.Size=Enum.Material.Neon,color,Vector3.new(.5,2,2)
    part.CFrame=CFrame.new(position+Vector3.new(0,.4,0))*CFrame.Angles(0,0,math.pi/2) part.Parent=folder
    local age=0
    table.insert(transient,{update=function(dt:number):boolean
        age+=dt local t=math.min(1,age/seconds)
        local d=2+maxSize*(1-(1-t)^3)
        part.Size=Vector3.new(.5,d,d) part.Transparency=.2+.8*t
        if t>=1 then part:Destroy() return false end
        return true
    end})
end

local function burst(position:Vector3,strong:boolean)
    local holder=Instance.new("Part") holder.Name="LavaImpact" holder.Size,holder.Transparency=Vector3.one,1
    holder.Anchored,holder.CanCollide,holder.CanTouch,holder.CanQuery=true,false,false,false holder.Position=position holder.Parent=folder
    local sparks=emitter(holder,0,{Texture=TEX_SPARK,Lifetime=NumberRange.new(.8,1.6),Speed=NumberRange.new(30,70),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,-70,0),Size=seq(1.4,.8,0),Transparency=seq(0,0,1),LightEmission=1,SpreadAngle=Vector2.new(70,70),
        Color=ColorSequence.new(Color3.fromRGB(255,225,110),Color3.fromRGB(255,90,20))})
    local puffs=emitter(holder,0,{Texture=TEX_FIRE,Lifetime=NumberRange.new(.9,1.5),Speed=NumberRange.new(8,22),EmissionDirection=Enum.NormalId.Top,
        Size=seq(7,16,20),Transparency=seq(.1,.4,1),LightEmission=1,SpreadAngle=Vector2.new(60,60),Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new(Color3.fromRGB(255,190,80),Color3.fromRGB(110,30,16))})
    local smoke=emitter(holder,0,{Texture=TEX_SMOKE,Lifetime=NumberRange.new(2,3),Speed=NumberRange.new(5,14),EmissionDirection=Enum.NormalId.Top,
        Size=seq(10,26),Transparency=seq(.4,.65,1),SpreadAngle=Vector2.new(40,40),Color=ColorSequence.new(Color3.fromRGB(50,42,42))})
    sparks.e:Emit(if strong then 60 else 36) puffs.e:Emit(if strong then 14 else 8) smoke.e:Emit(6)
    local light=Instance.new("PointLight") light.Color,light.Range,light.Brightness=Color3.fromRGB(255,130,50),42,8 light.Parent=holder
    TweenService:Create(light,TweenInfo.new(.9),{Brightness=0}):Play()
    Debris:AddItem(holder,4)
    ring(position,Color3.fromRGB(255,150,60),if strong then 46 else 30,.7)
end

local bombCount=0
local function lavaBomb(root:Vector3)
    if bombCount>=5 then return end
    bombCount+=1
    local angle=random:NextNumber(0,math.pi*2) local radius=random:NextNumber(26,90)
    local target=groundAt(root+Vector3.new(math.cos(angle)*radius,0,math.sin(angle)*radius))
    local from=random:NextNumber(0,math.pi*2)
    local start=target+Vector3.new(math.cos(from)*210,230,math.sin(from)*210)
    local flight=random:NextNumber(2.1,2.8) local g=Vector3.new(0,-workspace.Gravity*.5,0)
    local v=(target-start-.5*g*flight*flight)/flight
    local size=random:NextNumber(3,5.5)
    local part=Instance.new("Part") part.Name="LavaBomb" part.Shape=Enum.PartType.Ball part.Size=Vector3.one*size
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Material,part.Color=Enum.Material.Neon,Color3.fromRGB(255,120,30) part.Position=start part.Parent=folder
    local a0=Instance.new("Attachment") a0.Position=Vector3.new(0,size*.4,0) a0.Parent=part
    local a1=Instance.new("Attachment") a1.Position=Vector3.new(0,-size*.4,0) a1.Parent=part
    local trail=Instance.new("Trail") trail.Attachment0,trail.Attachment1=a0,a1 trail.Lifetime,trail.LightEmission,trail.FaceCamera=.9,1,true
    trail.Color=ColorSequence.new(Color3.fromRGB(255,220,120),Color3.fromRGB(255,70,20)) trail.Transparency=NumberSequence.new(.1,1) trail.WidthScale=NumberSequence.new(1,0) trail.Parent=part
    local trailSmoke=emitter(part,70*DENSITY,{Texture=TEX_SMOKE,Lifetime=NumberRange.new(1.4,2),Speed=NumberRange.new(0,2),Size=seq(size*1.4,size*3.4),
        Transparency=seq(.45,.7,1),Color=ColorSequence.new(Color3.fromRGB(60,48,46)),Rotation=NumberRange.new(0,360)})
    trailSmoke.e.Rate=trailSmoke.rate trailSmoke.e.Enabled=true
    local glow=Instance.new("PointLight") glow.Color,glow.Range,glow.Brightness=Color3.fromRGB(255,120,40),36,4 glow.Parent=part
    local age=0
    table.insert(transient,{update=function(dt:number):boolean
        age+=dt local t=math.min(age,flight)
        part.Position=start+v*t+.5*g*t*t
        if age>=flight then
            local near=(target-root).Magnitude
            burst(target,near<60)
            if near<55 then shake=math.max(shake,.7*(1-near/60)+.15) end
            part:Destroy() bombCount-=1 return false
        end
        return true
    end})
end

-- ---------------------------------------------------------------- title card
local gui=Instance.new("ScreenGui") gui.Name="WeatherTitle" gui.ResetOnSpawn=false gui.IgnoreGuiInset=true gui.DisplayOrder=40
gui.Parent=player:WaitForChild("PlayerGui")
local title=Instance.new("TextLabel") title.Name="Title" title.AnchorPoint=Vector2.new(.5,.5) title.Position=UDim2.fromScale(.5,.26) title.Size=UDim2.fromScale(.7,.12)
title.BackgroundTransparency=1 title.Font=Enum.Font.FredokaOne title.TextScaled=true title.TextTransparency=1 title.Text="" title.ZIndex=5 title.Parent=gui
local stroke=Instance.new("UIStroke") stroke.Thickness=5 stroke.Color=Color3.fromRGB(14,20,34) stroke.Transparency=1 stroke.Parent=title
local titleScale=Instance.new("UIScale") titleScale.Parent=title
local sub=Instance.new("TextLabel") sub.Name="Sub" sub.AnchorPoint=Vector2.new(.5,0) sub.Position=UDim2.fromScale(.5,1) sub.Size=UDim2.fromScale(.7,.42)
sub.BackgroundTransparency=1 sub.Font=Enum.Font.FredokaOne sub.TextScaled=true sub.TextTransparency=1 sub.TextColor3=Color3.new(1,1,1) sub.Text="Special eggs can drop!" sub.ZIndex=5 sub.Parent=title
local subStroke=Instance.new("UIStroke") subStroke.Thickness=3 subStroke.Color=Color3.fromRGB(14,20,34) subStroke.Transparency=1 subStroke.Parent=sub
local titleToken=0
local function showTitle(id:string,name:string)
    titleToken+=1 local mine=titleToken
    title.Text=string.upper(name).."!" title.TextColor3=TITLE_COLOR[id] or Color3.new(1,1,1)
    titleScale.Scale=if Theme.MotionEnabled then 2.2 else 1
    title.TextTransparency,stroke.Transparency,sub.TextTransparency,subStroke.Transparency=0,0,0,0
    if Theme.MotionEnabled then TweenService:Create(titleScale,TweenInfo.new(.45,Enum.EasingStyle.Back,Enum.EasingDirection.Out),{Scale=1}):Play() end
    task.delay(3.2,function()
        if mine~=titleToken then return end
        local info=TweenInfo.new(.8)
        TweenService:Create(title,info,{TextTransparency=1}):Play() TweenService:Create(stroke,info,{Transparency=1}):Play()
        TweenService:Create(sub,info,{TextTransparency=1}):Play() TweenService:Create(subStroke,info,{Transparency=1}):Play()
    end)
end

-- ---------------------------------------------------------------- main loop
local activeId="clear" local k=0 local shownId="clear"
local nextBolt=0 local nextBomb=0 local nextQuakeBurst=0 local quakeUntil=0 local nextPulse=0 local pulse=0
local columnAnchor:Vector3?=nil
local function lerpNum(a:number,b:number,t:number):number return a+(b-a)*t end
local elapsed=0
RunService.Heartbeat:Connect(function(dt)
    elapsed+=dt
    local id=workspace:GetAttribute("WeatherId") or "clear"
    local c=player.Character
    local rootPart=if c then c:FindFirstChild("HumanoidRootPart") else nil
    local root:Vector3?=if rootPart and rootPart:IsA("BasePart") then (rootPart::BasePart).Position else nil
    local motion=Theme.MotionEnabled and root~=nil
    -- fade current weather out, then switch; ramp the new one in
    if id==activeId then k=math.min(1,k+dt/2.4) else k=math.max(0,k-dt/1.1) if k<=0 then activeId=id columnAnchor=nil end end
    if activeId~=shownId and id==activeId and id~="clear" then
        shownId=activeId
        showTitle(id,workspace:GetAttribute("WeatherName") or id)
    elseif id=="clear" then shownId="clear" end

    local target=LOOKS[activeId] or LOOKS.clear
    local neutral=LOOKS.clear
    local t=if Theme.MotionEnabled then k else k*.5
    flash=math.max(0,flash-dt*2.2) pulse=math.max(0,pulse-dt*.9)
    grade.TintColor=neutral.tint:Lerp(target.tint,t)
    grade.Saturation=lerpNum(0,target.sat,t) grade.Contrast=lerpNum(0,target.contrast,t)
    grade.Brightness=lerpNum(0,target.bright,t)+flash*.5+pulse*.12
    bloom.Intensity=lerpNum(0,target.bloom,t)+flash*1.5
    bloom.Threshold=lerpNum(.95,.72,t) bloom.Size=lerpNum(24,40,t)
    rays.Intensity=lerpNum(0,target.rays,t) rays.Spread=.7
    atmosphere.Density=lerpNum(baseAtmo.density,math.max(baseAtmo.density,target.density),t)
    atmosphere.Haze=lerpNum(baseAtmo.haze,math.max(baseAtmo.haze,target.haze),t)
    atmosphere.Glare=lerpNum(baseAtmo.glare,math.max(baseAtmo.glare,target.glare),t)
    atmosphere.Color=baseAtmo.color:Lerp(target.fog,t)

    -- particle rigs follow the player; only the active weather emits
    for weatherId,list in rig do
        local on=motion and weatherId==activeId and k>0
        for _,item in list do
            item.e.Enabled=on item.e.Rate=item.rate*k
        end
        if on and root then
            local parts=rigParts[weatherId]
            if parts then for _,p in parts do p.part.Position=root+p.offset end end
        end
    end
    local sky=motion and root~=nil
    -- volcano: far eruption column + lava bombs
    if sky and root and activeId=="volcano" and k>.3 then
        if not columnAnchor then columnAnchor=root+Vector3.new(-340,-10,-560) end
        column.Position=groundAt(columnAnchor)
        if os.clock()>=nextBomb then nextBomb=os.clock()+random:NextNumber(.8,1.9) lavaBomb(root) end
        shake=math.max(shake,.12)
    end
    -- thunder bolts
    if sky and root and activeId=="thunder" and k>.5 and os.clock()>=nextBolt then
        nextBolt=os.clock()+random:NextNumber(4,9) bolt(root)
    end
    -- quake shake, bursts and rings
    if sky and root and activeId=="quake" and k>.3 then
        shake=math.max(shake,.22)
        if os.clock()>=nextQuakeBurst then
            nextQuakeBurst=os.clock()+random:NextNumber(3,5.5) quakeUntil=os.clock()+1.3
            ring(groundAt(root),Color3.fromRGB(235,200,140),70,.9) pulse=.6
        end
        if os.clock()<quakeUntil then shake=math.max(shake,.75) end
    end
    -- blood moon + aurora sky props
    local moonOn=sky and activeId=="bloodmoon" and k>0
    if moonOn and root then
        local base=root+MOON_DIR*520
        moonCore.Position=base moonCore.Transparency=lerpNum(1,.04,k)
        local beat=1+math.sin(os.clock()*.7)*.04
        moonCore.Size=Vector3.one*90*beat
        for i,halo in halos do halo.Position=base halo.Transparency=lerpNum(1,({.78,.9,.95})[i],k) end
        if os.clock()>=nextPulse then nextPulse=os.clock()+random:NextNumber(7,13) pulse=1 end
    else
        moonCore.Transparency=1 for _,halo in halos do halo.Transparency=1 end
    end
    local auroraOn=sky and activeId=="aurora" and k>0
    for _,curtain in curtains do
        for _,beam in curtain.beams do beam.Enabled=auroraOn beam.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.25,lerpNum(1,.5,k)),NumberSequenceKeypoint.new(.75,lerpNum(1,.5,k)),NumberSequenceKeypoint.new(1,1)}) end
        if auroraOn and root then
            local now=os.clock()
            for i,point in curtain.points do
                local u=(i-5.5)/4.5
                point.WorldPosition=root+Vector3.new(u*210+math.sin(now*.2+curtain.phase)*26,curtain.height+math.sin(now*.55+i*.7+curtain.phase)*14,-curtain.dist+math.cos(now*.3+i*.5+curtain.phase)*22)
            end
        end
    end
    -- transient effects
    for i=#transient,1,-1 do if not transient[i].update(dt) then table.remove(transient,i) end end
    if shake>.01 and Theme.MotionEnabled then shake=math.max(0,shake-dt*(if activeId=="quake" then .5 else 1.1)) end
    if not Theme.MotionEnabled then shake=0 end
end)
-- camera shake is applied after the camera script each frame, so it never fights the game's own camera offset
RunService:BindToRenderStep("WeatherShake",Enum.RenderPriority.Camera.Value+1,function()
    local camera=workspace.CurrentCamera
    if not camera or shake<=.01 or not Theme.MotionEnabled then return end
    local n=os.clock()*38
    camera.CFrame*=CFrame.new(math.sin(n*1.3)*shake*.45,math.cos(n*1.7)*shake*.4,0)*CFrame.Angles(0,0,math.sin(n*.9)*shake*.012)
end)
