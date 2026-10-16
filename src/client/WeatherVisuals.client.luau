--!strict
-- Weather v3 (docs/84): client-local mood. Per event: Lighting grade, Atmosphere fog/haze, sky colour shift, bloom, depth of field,
-- distance fog banks, particle rigs that follow the player, pooled lightning, lava bombs, shock rings, quake ground cracks,
-- a full-sky aurora (rays + arcs + hue-cycling sky), blood moon with halos and a title card.
-- Data and math live in Shared/WeatherLooks (offline-checked by tools/verify_weather.py).
-- Nothing here is authoritative or collides; the server only publishes WeatherId / WeatherName.
local Lighting=game:GetService("Lighting")
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local TweenService=game:GetService("TweenService")
local UserInputService=game:GetService("UserInputService")
local Shared=game:GetService("ReplicatedStorage").Shared
local Theme=require(Shared.UITheme)
local WL=require(Shared.WeatherLooks)
local WS=require(Shared.WeatherSounds)
local Cave=require(script.Parent.CaveAtmosphere) -- BD-286: cave-only look and weather stays outside (no-op while Config.CaveHub is false)
local player=Players.LocalPlayer
local random=Random.new()
local phone=UserInputService.TouchEnabled and not UserInputService.MouseEnabled
local DENSITY=if phone then .5 else 1
local TEX_SMOKE="rbxasset://textures/particles/smoke_main.dds"
local TEX_SPARK="rbxasset://textures/particles/sparkles_main.dds"
local TEX_FIRE="rbxasset://textures/particles/fire_main.dds"
-- Quake dust puffs use the FX v3 anime smoke flipbook (docs/77 fx3_smoke-anime): 16 cells played in order over each puff's life.
local DUST_FX=(function()
    local Assets=require(Shared.EffectAssets)
    -- dust is a soft tan haze, so it needs the alpha upload (EffectAssets.HasAlpha); additive black-backed smoke would glow
    local sheet=Assets.isSheet("smokeSheet") and not Assets.isAdditive("smokeSheet")
    return {Texture=if sheet then Assets.resolve("smokeSheet") else Assets.Builtin.smoke,FlipbookLayout=if sheet then Enum.ParticleFlipbookLayout.Grid4x4 else Enum.ParticleFlipbookLayout.None,
        FlipbookMode=Enum.ParticleFlipbookMode.OneShot}
end)()

local folder=Instance.new("Folder") folder.Name="LocalWeatherFX" folder.Parent=workspace
local function c3(c:{number}):Color3 return Color3.fromRGB(c[1],c[2],c[3]) end

local TITLE_COLOR:{[string]:Color3}={
    rain=Color3.fromRGB(110,200,255),thunder=Color3.fromRGB(190,170,255),blizzard=Color3.fromRGB(190,235,255),
    volcano=Color3.fromRGB(255,150,60),aurora=Color3.fromRGB(110,255,200),quake=Color3.fromRGB(235,190,120),bloodmoon=Color3.fromRGB(255,70,100),
}

-- ---------------------------------------------------------------- post effects, atmosphere, sky
local grade=Instance.new("ColorCorrectionEffect") grade.Name="WeatherGrade" grade.Parent=Lighting
local bloom=Instance.new("BloomEffect") bloom.Name="WeatherBloom" bloom.Intensity,bloom.Size,bloom.Threshold=0,24,.9 bloom.Parent=Lighting
local rays=Instance.new("SunRaysEffect") rays.Name="WeatherRays" rays.Intensity,rays.Spread=0,.6 rays.Parent=Lighting
local dof=Instance.new("DepthOfFieldEffect") dof.Name="WeatherDof" dof.FarIntensity,dof.NearIntensity,dof.InFocusRadius,dof.FocusDistance=0,0,30,200
dof.Enabled=not phone dof.Parent=Lighting
local atmosphere=Lighting:FindFirstChildOfClass("Atmosphere")
if not atmosphere then
    atmosphere=Instance.new("Atmosphere") atmosphere.Density,atmosphere.Offset,atmosphere.Glare,atmosphere.Haze=0,0,0,0
    atmosphere.Name="WeatherAtmosphere" atmosphere.Parent=Lighting
end
local sky:Sky?=Lighting:FindFirstChildOfClass("Sky")
local baseAmbient,baseOutdoor=Lighting.Ambient,Lighting.OutdoorAmbient
local baseShiftTop,baseShiftBottom,baseExposure=Lighting.ColorShift_Top,Lighting.ColorShift_Bottom,Lighting.ExposureCompensation
-- BD-055 cloud cover: Terrain.Clouds follows the event look (cover, density, colour) with the same ramp as the grade. No texture is needed;
-- a place without Clouds gets one that starts invisible (cover 0), so clear weather looks exactly as before.
local clouds:Clouds=workspace.Terrain:FindFirstChildOfClass("Clouds") or Instance.new("Clouds")
if not clouds.Parent then clouds.Name="WeatherClouds" clouds.Cover,clouds.Density=0,.5 clouds.Parent=workspace.Terrain end
local baseCloud={cover=clouds.Cover,density=clouds.Density,color=clouds.Color}
local baseStars=if sky then sky.StarCount else 0
-- BD-213 soft visibility: clear weather keeps a gentle haze, and FogEnd stays inside this device's prop cull radius
-- (same device classes as WorldCulling.client.luau), so culled props are already lost in the haze and never pop.
local CLEAR=WL.Looks.clear
local fogCap=(function():number
    local culling=require(Shared.Config).WorldCulling
    if not culling or not culling.Enabled then return WL.fogCap(nil) end
    local size=workspace.CurrentCamera.ViewportSize
    local class=if not UserInputService.TouchEnabled then "Desktop" elseif math.min(size.X,size.Y)>=600 then "Tablet" else "Phone"
    return WL.fogCap(culling[class].radius)
end)()
local baseAtmo={density=atmosphere.Density,offset=atmosphere.Offset,haze=atmosphere.Haze,glare=atmosphere.Glare,color=atmosphere.Color,decay=atmosphere.Decay}

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
type Emitter={e:ParticleEmitter,rate:number,fixed:boolean}
-- rate and lifetime come from WeatherLooks.Rigs so the offline budget check sees exactly what is built; share = this emitter's part of the group rate
local function emitter(parent:Instance,id:string,name:string,props:{[string]:any},share:number?,fixed:boolean?):Emitter
    local spec=WL.Rigs[id][name]
    local e=Instance.new("ParticleEmitter") e.Name="WeatherParticles"
    e.Rate,e.Enabled=0,false e.LockedToPart=false e.LightInfluence=0
    e.Lifetime=NumberRange.new(spec.life[1],spec.life[2])
    local any:any=e
    for key,value in props do any[key]=value end
    e.Parent=parent
    return {e=e,rate=spec.rate*(share or 1)*DENSITY,fixed=fixed==true}
end
local rig:{[string]:{Emitter}}={}
local rigParts:{[string]:{{part:Part,offset:Vector3,base:Vector3}}}={}
local function addRig(id:string,part:Part,offset:Vector3,list:{Emitter})
    rig[id]=rig[id] or {} rigParts[id]=rigParts[id] or {}
    for _,item in list do table.insert(rig[id],item) end
    table.insert(rigParts[id],{part=part,offset=offset,base=part.Size})
end
local WIDE=Vector3.new(90,1,90)
local FEET=Vector3.new(0,-2.8,0)
-- distance fog: four large soft smoke volumes in a ring around the player (60 to 250 studs); the middle stays empty so the near play area is clear
local RING={Vector3.new(125,-1,0),Vector3.new(-125,-1,0),Vector3.new(0,-1,125),Vector3.new(0,-1,-125)}
-- BD-055: soft cloud sprite for the fog banks once the owner uploads one (docs/120 weatherCloud); until then the built-in smoke
local BANK_TEX=(function()
    local Assets=require(Shared.EffectAssets)
    return if Assets.isReal("weatherCloud") then Assets.resolve("weatherCloud") else TEX_SMOKE
end)()
local function fogBanks(id:string,color:ColorSequence,props:{[string]:any}?)
    for _,offset in RING do
        local part=volume(Vector3.new(150,10,150))
        local p:{[string]:any}={
            Texture=BANK_TEX,Speed=NumberRange.new(2,6),EmissionDirection=Enum.NormalId.Top,SpreadAngle=Vector2.new(180,180),Size=seq(80,120,150),
            Transparency=seq(1,.84,1),Color=color,Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-4,4),Drag=.4,
        }
        if props then for key,value in props do p[key]=value end end
        addRig(id,part,offset,{emitter(part,id,"bank",p,1/#RING,true)})
    end
end
local function colorOf(r:number,g:number,b:number):ColorSequence return ColorSequence.new(Color3.fromRGB(r,g,b)) end

-- RAIN + THUNDER
for _,id in {"rain","thunder"} do
    local heavy=id=="thunder"
    local sky=volume(WIDE)
    local streaks=emitter(sky,id,"streaks",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(95,115),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(if heavy then 34 else 12,-70,0),Orientation=Enum.ParticleOrientation.VelocityParallel,
        Size=seq(if heavy then .7 else .56,.5),Squash=seq(-20,-20),Transparency=seq(.22,.06),LightEmission=.6,
        Color=ColorSequence.new(Color3.fromRGB(190,220,255),Color3.fromRGB(140,185,240)),SpreadAngle=Vector2.new(4,4),
    })
    -- BD-348: long bright streaks right in front of the camera (a small volume above the dino, no distance fade)
    local nearSky=volume(Vector3.new(26,1,26))
    local nearStreaks=emitter(nearSky,id,"near",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(70,90),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(if heavy then 30 else 10,-60,0),Orientation=Enum.ParticleOrientation.VelocityParallel,
        Size=seq(.9,.7),Squash=seq(-26,-26),Transparency=seq(.18,.05),LightEmission=.7,
        Color=ColorSequence.new(Color3.fromRGB(215,236,255),Color3.fromRGB(165,205,250)),SpreadAngle=Vector2.new(3,3),
    },1,true)
    addRig(id,nearSky,Vector3.new(0,16,0),{nearStreaks})
    local ground=volume(Vector3.new(60,.2,60))
    local splash=emitter(ground,id,"splash",{
        Texture=TEX_SPARK,Speed=NumberRange.new(3,8),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,-24,0),Size=seq(.3,1.6,0),Transparency=seq(.1,.4,1),LightEmission=.4,
        Color=ColorSequence.new(Color3.fromRGB(215,236,255)),SpreadAngle=Vector2.new(40,40),
    })
    local mist=emitter(ground,id,"mist",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(1,3),EmissionDirection=Enum.NormalId.Top,
        Size=seq(20,38),Transparency=seq(1,.8,1),Color=ColorSequence.new(Color3.fromRGB(150,165,185)),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-8,8),
    })
    -- rain curtains in the distance: tall pale sheets falling from four sides
    local sheets:{Emitter}={}
    for _,offset in RING do
        local part=volume(Vector3.new(140,2,140))
        local curtain=emitter(part,id,"curtain",{
            Texture=TEX_SMOKE,Speed=NumberRange.new(70,95),EmissionDirection=Enum.NormalId.Bottom,Orientation=Enum.ParticleOrientation.VelocityParallel,
            Size=seq(26,36),Squash=seq(-5,-5),Transparency=seq(.9,.74,1),Color=ColorSequence.new(Color3.fromRGB(160,178,204)),
        },1/#RING,true)
        addRig(id,part,Vector3.new(offset.X*1.1,52,offset.Z*1.1),{curtain})
    end
    addRig(id,sky,Vector3.new(0,40,0),{streaks})
    addRig(id,ground,FEET,{splash,mist})
    fogBanks(id,if heavy then colorOf(78,88,124) else colorOf(128,142,164))
end
-- BLIZZARD
do
    local sky=volume(WIDE)
    local snow=emitter(sky,"blizzard","snow",{
        Texture=TEX_SPARK,Speed=NumberRange.new(10,22),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(-46,-6,14),Size=seq(.5,.8),Transparency=seq(.05,.1,.5),LightEmission=.35,Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-90,90),
        Color=ColorSequence.new(Color3.new(1,1,1),Color3.fromRGB(205,230,255)),SpreadAngle=Vector2.new(18,18),
    })
    local side=volume(Vector3.new(2,40,110))
    local gust=emitter(side,"blizzard","gust",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(60,85),EmissionDirection=Enum.NormalId.Right,
        Orientation=Enum.ParticleOrientation.VelocityParallel,Size=seq(2.4,3),Squash=seq(-10,-10),Transparency=seq(.9,.6,1),
        Color=ColorSequence.new(Color3.fromRGB(235,244,255)),
    })
    local flurry=emitter(side,"blizzard","flurry",{
        Texture=TEX_SPARK,Speed=NumberRange.new(70,100),EmissionDirection=Enum.NormalId.Right,Orientation=Enum.ParticleOrientation.VelocityParallel,
        Size=seq(.9,1.1),Squash=seq(-6,-6),Transparency=seq(.15,.3,1),LightEmission=.5,Color=ColorSequence.new(Color3.new(1,1,1)),
    })
    local drift=emitter(side,"blizzard","drift",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(22,34),EmissionDirection=Enum.NormalId.Right,
        Size=seq(34,54),Transparency=seq(1,.88,1),Color=ColorSequence.new(Color3.fromRGB(238,246,255)),Rotation=NumberRange.new(0,360),
    })
    addRig("blizzard",sky,Vector3.new(0,36,0),{snow})
    addRig("blizzard",side,Vector3.new(-70,12,0),{gust,flurry,drift})
    fogBanks("blizzard",colorOf(240,246,255),{Speed=NumberRange.new(10,22),Acceleration=Vector3.new(30,0,8)})
end
-- VOLCANO (ash fall, embers, three distant eruption columns, ash ceiling, red fog banks, lava bombs below)
local COLUMN_OFFSETS={Vector3.new(-190,-10,-280),Vector3.new(260,-10,-240),Vector3.new(-30,-10,-400)}
local columns:{Part}={}
do
    local sky=volume(WIDE)
    local ash=emitter(sky,"volcano","ash",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(4,9),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(7,-4,3),Size=seq(.8,1.4),Transparency=seq(.5,.3,.9),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-60,60),
        Color=ColorSequence.new(Color3.fromRGB(70,64,68),Color3.fromRGB(38,34,36)),
    })
    local low=volume(Vector3.new(70,2,70))
    local embers=emitter(low,"volcano","embers",{
        Texture=TEX_SPARK,Speed=NumberRange.new(4,10),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(3,5,0),Size=seq(.55,.4,0),Transparency=seq(0,0,1),LightEmission=1,
        Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(255,235,120)),ColorSequenceKeypoint.new(.5,Color3.fromRGB(255,120,30)),ColorSequenceKeypoint.new(1,Color3.fromRGB(180,30,10))}),
        SpreadAngle=Vector2.new(45,45),
    })
    local ceiling=volume(Vector3.new(420,4,420))
    local haze=emitter(ceiling,"volcano","haze",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(2,6),EmissionDirection=Enum.NormalId.Bottom,Size=seq(160,230,300),Transparency=seq(1,.82,1),
        Color=ColorSequence.new(Color3.fromRGB(52,38,36),Color3.fromRGB(88,40,28)),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-3,3),
    },1,true)
    addRig("volcano",sky,Vector3.new(0,40,0),{ash})
    addRig("volcano",low,FEET,{embers})
    addRig("volcano",ceiling,Vector3.new(0,150,0),{haze})
    for _=1,#COLUMN_OFFSETS do
        local part=volume(Vector3.new(40,2,40)) table.insert(columns,part)
        local plume=emitter(part,"volcano","plume",{
            Texture=TEX_FIRE,Speed=NumberRange.new(70,110),EmissionDirection=Enum.NormalId.Top,
            Size=seq(55,120,180),Transparency=seq(.15,.35,1),LightEmission=1,Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-20,20),
            Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(255,240,150)),ColorSequenceKeypoint.new(.35,Color3.fromRGB(255,120,30)),ColorSequenceKeypoint.new(1,Color3.fromRGB(70,20,10))}),
            SpreadAngle=Vector2.new(12,12),
        },1/#COLUMN_OFFSETS,true)
        local smoke=emitter(part,"volcano","smoke",{
            Texture=TEX_SMOKE,Speed=NumberRange.new(40,70),EmissionDirection=Enum.NormalId.Top,
            Size=seq(130,270,400),Transparency=seq(.3,.45,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-8,8),
            Color=ColorSequence.new(Color3.fromRGB(46,38,38),Color3.fromRGB(28,24,26)),SpreadAngle=Vector2.new(18,18),
        },1/#COLUMN_OFFSETS,true)
        rig.volcano=rig.volcano or {} for _,item in {plume,smoke} do table.insert(rig.volcano,item) end
    end
    fogBanks("volcano",ColorSequence.new(Color3.fromRGB(130,76,52),Color3.fromRGB(58,46,42)),{Transparency=seq(1,.9,1)})
end
-- AURORA (full-sky curtains below) + drifting motes, twinkling sky sparkle, low teal mist
do
    local air=volume(Vector3.new(70,16,70))
    local motes=emitter(air,"aurora","motes",{
        Texture=TEX_SPARK,Speed=NumberRange.new(.5,2),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,1.6,0),Size=seq(0,.8,0),Transparency=seq(1,.1,1),LightEmission=1,Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(110,255,190)),ColorSequenceKeypoint.new(.5,Color3.fromRGB(120,190,255)),ColorSequenceKeypoint.new(1,Color3.fromRGB(220,130,255))}),
    })
    local dome=volume(Vector3.new(520,40,520))
    local stars=emitter(dome,"aurora","stars",{
        Texture=TEX_SPARK,Speed=NumberRange.new(0,.5),EmissionDirection=Enum.NormalId.Top,Size=seq(0,3.2,0),Transparency=seq(1,.05,1),LightEmission=1,Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(150,255,200)),ColorSequenceKeypoint.new(.5,Color3.fromRGB(255,255,255)),ColorSequenceKeypoint.new(1,Color3.fromRGB(230,150,255))}),
    },1,true)
    addRig("aurora",air,Vector3.new(0,8,0),{motes})
    addRig("aurora",dome,Vector3.new(0,170,0),{stars})
    fogBanks("aurora",ColorSequence.new(Color3.fromRGB(80,230,200),Color3.fromRGB(170,120,255)),{Transparency=seq(1,.72,1),LightEmission=1})
end
-- QUAKE (light ground dust + dust haze; cracks, rocks and tremors are world one-shots below)
do
    local ground=volume(Vector3.new(70,.2,70))
    local dust=emitter(ground,"quake","dust",{
        Texture=DUST_FX.Texture,FlipbookLayout=DUST_FX.FlipbookLayout,FlipbookMode=DUST_FX.FlipbookMode,Speed=NumberRange.new(3,9),EmissionDirection=Enum.NormalId.Top,
        Size=seq(10,24,34),Transparency=seq(.82,.7,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-14,14),
        Color=ColorSequence.new(Color3.fromRGB(196,170,128),Color3.fromRGB(160,138,104)),SpreadAngle=Vector2.new(30,30),
    })
    addRig("quake",ground,FEET,{dust})
    fogBanks("quake",ColorSequence.new(Color3.fromRGB(190,158,116),Color3.fromRGB(150,124,92)),{Transparency=seq(1,.88,1)})
end
-- BLOOD MOON (red motes, ground fog, red fog walls)
do
    local air=volume(Vector3.new(80,14,80))
    local motes=emitter(air,"bloodmoon","motes",{
        Texture=TEX_SPARK,Speed=NumberRange.new(.5,2.5),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,1.2,0),Size=seq(0,.9,0),Transparency=seq(1,.05,1),LightEmission=1,Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new(Color3.fromRGB(255,60,90),Color3.fromRGB(255,150,170)),
    })
    local ground=volume(Vector3.new(90,.2,90))
    local fogBank=emitter(ground,"bloodmoon","fog",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(1,3),EmissionDirection=Enum.NormalId.Top,
        Size=seq(34,56),Transparency=seq(1,.88,1),Color=ColorSequence.new(Color3.fromRGB(150,16,40)),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-5,5),
    })
    addRig("bloodmoon",air,Vector3.new(0,6,0),{motes})
    addRig("bloodmoon",ground,FEET,{fogBank})
    fogBanks("bloodmoon",ColorSequence.new(Color3.fromRGB(170,18,44),Color3.fromRGB(90,8,28)),{Transparency=seq(1,.88,1),Size=seq(90,130,170)})
end

-- ---------------------------------------------------------------- lights that keep the near area bright and carry the event colour
local lampPart=volume(Vector3.one)
local lamp=Instance.new("PointLight") lamp.Name="WeatherLamp" lamp.Color,lamp.Range,lamp.Brightness,lamp.Shadows=Color3.fromRGB(255,244,226),32,0,false lamp.Parent=lampPart
local glow=Instance.new("PointLight") glow.Name="WeatherGlow" glow.Range,glow.Brightness,glow.Shadows=40,0,false glow.Parent=lampPart

-- ---------------------------------------------------------------- sky props: blood moon, aurora curtains, fog-coloured sky box
local moonCore=Instance.new("Part") moonCore.Name="EventMoon" moonCore.Shape=Enum.PartType.Ball
moonCore.Anchored,moonCore.CanCollide,moonCore.CanTouch,moonCore.CanQuery,moonCore.CastShadow=true,false,false,false,false
moonCore.Size,moonCore.Material,moonCore.Color,moonCore.Transparency,moonCore.Parent=Vector3.one*WL.Moon.core,Enum.Material.Neon,Color3.fromRGB(255,96,64),1,folder
local halos:{Part}={}
for i,size in WL.Moon.halos do
    local halo=moonCore:Clone() halo.Name="EventMoonHalo"..i halo.Size=Vector3.one*size halo.Transparency=1 halo.Color=Color3.fromRGB(255,70,50) halo.Parent=folder
    table.insert(halos,halo)
end
local HALO_ALPHA={.84,.93,.97}
local MOON_DIR=Vector3.new(-.32,.62,-.8).Unit

-- BD-213: no fog-coloured sky box. A box inside FogEnd read as a flat opaque wall and cut the view short; the far view now
-- dissolves through the classic fog ramp and the Atmosphere haze tints the sky (event sun and moon are hidden below).

-- aurora curtains: three high arcs of vertical ribbons (14 each) far out in the sky, swaying and hue-shifting, no beams near the dino
local CURTAINS,CURTAIN_RAYS=3,14
type CurtainRay={bottom:Attachment,top:Attachment,beam:Beam,curtain:number,index:number}
local curtainRays:{CurtainRay}={}
for c=1,CURTAINS do
    for i=1,CURTAIN_RAYS do
        local bottom=Instance.new("Attachment") bottom.Parent=workspace.Terrain
        local top=Instance.new("Attachment") top.Parent=workspace.Terrain
        local beam=Instance.new("Beam") beam.Attachment0,beam.Attachment1=bottom,top
        beam.FaceCamera,beam.LightEmission,beam.LightInfluence,beam.Segments=true,1,0,12
        beam.Width0,beam.Width1=70+c*14,110+c*20
        beam.Enabled=false beam.Parent=folder
        table.insert(curtainRays,{bottom=bottom,top=top,beam=beam,curtain=c,index=i})
    end
end

-- ---------------------------------------------------------------- pooled one-shot effects (all Instances are created here, once)
local flash=0
local shake=0
local pulse=0
local rayParams=RaycastParams.new() rayParams.FilterType=Enum.RaycastFilterType.Exclude rayParams.FilterDescendantsInstances={folder}
local function groundAt(position:Vector3):Vector3
    rayParams.FilterDescendantsInstances={folder,player.Character or folder}
    local hit=workspace:Raycast(position+Vector3.new(0,260,0),Vector3.new(0,-600,0),rayParams)
    return if hit then hit.Position else Vector3.new(position.X,position.Y-3,position.Z)
end
local PARKED=Vector3.new(0,-4000,0)
local function worldAttachment():Attachment
    local a=Instance.new("Attachment") a.Parent=workspace.Terrain return a
end

-- lightning bolts: WeatherLooks.Budget.bolts slots, each 10 trunk attachments, 2 glow layers per segment and 2 forks
type BoltSlot={points:{Attachment},ends:{Attachment},beams:{Beam},forks:{Beam},active:boolean,age:number,flickered:boolean}
local bolts:{BoltSlot}={}
for _=1,WL.Budget.bolts do
    local points:{Attachment}={} local ends:{Attachment}={} local beams:{Beam}={} local forks:{Beam}={}
    for i=1,10 do points[i]=worldAttachment() end
    for i=1,2 do ends[i]=worldAttachment() end
    for i=2,10 do
        for layer=1,2 do
            local beam=Instance.new("Beam") beam.Attachment0,beam.Attachment1=points[i-1],points[i]
            beam.FaceCamera,beam.LightEmission,beam.LightInfluence,beam.Segments=true,1,0,1
            beam.Width0,beam.Width1=if layer==1 then 13 else 3,if layer==1 then 9 else 2
            beam.Color=ColorSequence.new(if layer==1 then Color3.fromRGB(150,130,255) else Color3.new(1,1,1))
            beam.Transparency=NumberSequence.new(if layer==1 then .45 else 0)
            beam.Enabled=false beam.Parent=folder table.insert(beams,beam)
        end
    end
    for i=1,2 do
        local fork=Instance.new("Beam") fork.Attachment0,fork.Attachment1=points[3],ends[i] fork.FaceCamera,fork.LightEmission,fork.LightInfluence=true,1,0
        fork.Width0,fork.Width1=4.5,.8 fork.Color=ColorSequence.new(Color3.fromRGB(225,215,255)) fork.Segments=6 fork.Enabled=false fork.Parent=folder
        table.insert(forks,fork)
    end
    table.insert(bolts,{points=points,ends=ends,beams=beams,forks=forks,active=false,age=0,flickered=false})
end
local function setBolt(slot:BoltSlot,on:boolean)
    for _,b in slot.beams do b.Enabled=on end
    for _,b in slot.forks do b.Enabled=on end
end
local function bolt(root:Vector3):boolean
    local slot:BoltSlot?=nil
    for _,s in bolts do if not s.active then slot=s break end end
    if not slot then return false end
    local angle=random:NextNumber(0,math.pi*2) local dist=random:NextNumber(50,300)
    local top=root+Vector3.new(math.cos(angle)*dist,210,math.sin(angle)*dist)
    local bottom=groundAt(Vector3.new(top.X,root.Y,top.Z))
    for i=1,10 do
        local p=top:Lerp(bottom,(i-1)/9)
        if i>1 and i<10 then p+=Vector3.new(random:NextNumber(-18,18),0,random:NextNumber(-18,18)) end
        slot.points[i].WorldPosition=p
    end
    for i,fork in slot.forks do
        local from=slot.points[random:NextInteger(3,7)]
        fork.Attachment0=from
        slot.ends[i].WorldPosition=from.WorldPosition+Vector3.new(random:NextNumber(-70,70),-random:NextNumber(40,90),random:NextNumber(-70,70))
        fork.CurveSize0=random:NextNumber(-10,10)
    end
    slot.active,slot.age,slot.flickered=true,0,false setBolt(slot,true)
    WS.fire("strike")
    flash=math.max(flash,.8) shake=math.max(shake,if dist<120 then .7 else .45)
    return true
end
local function updateBolts(dt:number)
    for _,slot in bolts do
        if slot.active then
            slot.age+=dt
            if slot.age>.09 and slot.age<.17 then setBolt(slot,false)
            elseif slot.age>=.17 and slot.age<=.5 then
                setBolt(slot,true)
                if not slot.flickered then slot.flickered=true flash=math.max(flash,.55) end
            end
            if slot.age>.5 then slot.active=false setBolt(slot,false) end
        end
    end
end

-- shock rings (lava impact)
type RingSlot={part:Part,active:boolean,age:number,seconds:number,size:number}
local ringSlots:{RingSlot}={}
for _=1,6 do
    local part=Instance.new("Part") part.Name="ShockRing" part.Shape=Enum.PartType.Cylinder
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Material,part.Size,part.Transparency=Enum.Material.Neon,Vector3.new(.5,2,2),1 part.Position=PARKED part.Parent=folder
    table.insert(ringSlots,{part=part,active=false,age=0,seconds=1,size=1})
end
local function ring(position:Vector3,color:Color3,maxSize:number,seconds:number)
    for _,slot in ringSlots do
        if not slot.active then
            slot.active,slot.age,slot.seconds,slot.size=true,0,seconds,maxSize
            slot.part.Color=color slot.part.CFrame=CFrame.new(position+Vector3.new(0,.4,0))*CFrame.Angles(0,0,math.pi/2)
            return
        end
    end
end
local function updateRings(dt:number)
    for _,slot in ringSlots do
        if slot.active then
            slot.age+=dt local t=math.min(1,slot.age/slot.seconds)
            local d=2+slot.size*(1-(1-t)^3)
            slot.part.Size=Vector3.new(.5,d,d) slot.part.Transparency=.2+.8*t
            if t>=1 then slot.active=false slot.part.Position=PARKED slot.part.Transparency=1 end
        end
    end
end

-- lava impact bursts (sparks, fire puffs, smoke, flash light, ring)
type BurstSlot={holder:Part,sparks:Emitter,puffs:Emitter,smoke:Emitter,light:PointLight,active:boolean,age:number}
local burstSlots:{BurstSlot}={}
local function burstEmitter(parent:Part,props:{[string]:any}):Emitter
    local e=Instance.new("ParticleEmitter") e.Name="WeatherParticles" e.Rate,e.Enabled,e.LockedToPart,e.LightInfluence=0,false,false,0
    local any:any=e for key,value in props do any[key]=value end e.Parent=parent
    return {e=e,rate=0,fixed=true}
end
for _=1,WL.Budget.bombs do
    local holder=Instance.new("Part") holder.Name="LavaImpact" holder.Size,holder.Transparency=Vector3.one,1
    holder.Anchored,holder.CanCollide,holder.CanTouch,holder.CanQuery=true,false,false,false holder.Position=PARKED holder.Parent=folder
    local sparks=burstEmitter(holder,{Texture=TEX_SPARK,Lifetime=NumberRange.new(.8,1.6),Speed=NumberRange.new(30,75),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,-70,0),Size=seq(1.5,.9,0),Transparency=seq(0,0,1),LightEmission=1,SpreadAngle=Vector2.new(70,70),
        Color=ColorSequence.new(Color3.fromRGB(255,225,110),Color3.fromRGB(255,90,20))})
    local puffs=burstEmitter(holder,{Texture=TEX_FIRE,Lifetime=NumberRange.new(.9,1.5),Speed=NumberRange.new(8,24),EmissionDirection=Enum.NormalId.Top,
        Size=seq(8,18,22),Transparency=seq(.1,.4,1),LightEmission=1,SpreadAngle=Vector2.new(60,60),Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new(Color3.fromRGB(255,190,80),Color3.fromRGB(110,30,16))})
    local smoke=burstEmitter(holder,{Texture=TEX_SMOKE,Lifetime=NumberRange.new(2,3),Speed=NumberRange.new(5,14),EmissionDirection=Enum.NormalId.Top,
        Size=seq(12,30),Transparency=seq(.4,.65,1),SpreadAngle=Vector2.new(40,40),Color=ColorSequence.new(Color3.fromRGB(50,42,42))})
    local light=Instance.new("PointLight") light.Color,light.Range,light.Brightness,light.Shadows=Color3.fromRGB(255,130,50),46,0,false light.Parent=holder
    table.insert(burstSlots,{holder=holder,sparks=sparks,puffs=puffs,smoke=smoke,light=light,active=false,age=0})
end
local function burst(position:Vector3,strong:boolean)
    for _,slot in burstSlots do
        if not slot.active then
            slot.active,slot.age=true,0 slot.holder.Position=position
            slot.sparks.e:Emit(if strong then 70 else 40) slot.puffs.e:Emit(if strong then 16 else 9) slot.smoke.e:Emit(7)
            slot.light.Brightness=8
            ring(position,Color3.fromRGB(255,150,60),if strong then 52 else 32,.7)
            pulse=math.max(pulse,.35)
            return
        end
    end
end
local function updateBursts(dt:number)
    for _,slot in burstSlots do
        if slot.active then
            slot.age+=dt
            slot.light.Brightness=math.max(0,8*(1-slot.age/.9))
            if slot.age>4 then slot.active=false slot.holder.Position=PARKED slot.light.Brightness=0 end
        end
    end
end

-- lava bombs: WeatherLooks.Budget.bombs pooled glowing balls with a trail and a smoke tail
type BombSlot={part:Part,trail:Trail,tail:Emitter,glow:PointLight,active:boolean,age:number,flight:number,start:Vector3,v:Vector3,target:Vector3}
local bombSlots:{BombSlot}={}
local BOMB_TAIL={Texture=TEX_SMOKE,Lifetime=NumberRange.new(1.4,2),Speed=NumberRange.new(0,2),Size=seq(8,16),Transparency=seq(.45,.7,1),
    Color=ColorSequence.new(Color3.fromRGB(60,48,46)),Rotation=NumberRange.new(0,360)}
for _=1,WL.Budget.bombs do
    local part=Instance.new("Part") part.Name="LavaBomb" part.Shape=Enum.PartType.Ball part.Size=Vector3.one*4
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Material,part.Color=Enum.Material.Neon,Color3.fromRGB(255,120,30) part.Position=PARKED part.Parent=folder
    local a0=Instance.new("Attachment") a0.Position=Vector3.new(0,1.6,0) a0.Parent=part
    local a1=Instance.new("Attachment") a1.Position=Vector3.new(0,-1.6,0) a1.Parent=part
    local trail=Instance.new("Trail") trail.Attachment0,trail.Attachment1=a0,a1 trail.Lifetime,trail.LightEmission,trail.FaceCamera=.9,1,true
    trail.Color=ColorSequence.new(Color3.fromRGB(255,220,120),Color3.fromRGB(255,70,20)) trail.Transparency=NumberSequence.new(.1,1) trail.WidthScale=NumberSequence.new(1,0)
    trail.Enabled=false trail.Parent=part
    local tail=burstEmitter(part,BOMB_TAIL) tail.e.Rate=70*DENSITY
    local light=Instance.new("PointLight") light.Color,light.Range,light.Brightness,light.Shadows=Color3.fromRGB(255,120,40),40,0,false light.Parent=part
    table.insert(bombSlots,{part=part,trail=trail,tail=tail,glow=light,active=false,age=0,flight=2,start=PARKED,v=Vector3.zero,target=PARKED})
end
local function lavaBomb(root:Vector3)
    local slot:BombSlot?=nil
    for _,s in bombSlots do if not s.active then slot=s break end end
    if not slot then return end
    local angle=random:NextNumber(0,math.pi*2) local radius=random:NextNumber(24,100)
    local target=groundAt(root+Vector3.new(math.cos(angle)*radius,0,math.sin(angle)*radius))
    local from=random:NextNumber(0,math.pi*2)
    local start=target+Vector3.new(math.cos(from)*210,230,math.sin(from)*210)
    local flight=random:NextNumber(2,2.7) local g=Vector3.new(0,-workspace.Gravity*.5,0)
    slot.v=(target-start-.5*g*flight*flight)/flight
    slot.part.Size=Vector3.one*random:NextNumber(3.4,6)
    slot.start,slot.target,slot.flight,slot.age,slot.active=start,target,flight,0,true
    slot.part.Position=start slot.trail.Enabled=true slot.tail.e.Enabled=true slot.glow.Brightness=5
end
local function updateBombs(dt:number,root:Vector3?)
    local g=Vector3.new(0,-workspace.Gravity*.5,0)
    for _,slot in bombSlots do
        if slot.active then
            slot.age+=dt local t=math.min(slot.age,slot.flight)
            slot.part.Position=slot.start+slot.v*t+g*t*t
            if slot.age>=slot.flight then
                slot.active=false slot.trail.Enabled=false slot.tail.e.Enabled=false slot.glow.Brightness=0 slot.part.Position=PARKED
                local near=if root then (slot.target-root).Magnitude else 999
                burst(slot.target,near<70)
                if near<160 then WS.fire("eruption") end
                if near<60 then shake=math.max(shake,.8*(1-near/70)+.2) end
            end
        end
    end
end
-- earthquake v2 (owner 2026-10-15): a WORLD event, not an aura around the dino. Pooled ground cracks open at random spots in view
-- (never under the dino): each is a jagged chain of flat, tapered wedge diamonds with a faint amber glow in its depth, a dust puff and
-- a few bouncing rock chunks, then it closes. Tremor pulses rumble the camera gently and wobble nearby small props.
-- Reduce Motion: cracks appear and fade in place; no shake, dust, rocks or wobble. Caps: WL.Budget.cracks (cracksPhone on phones).
local QK=WL.Quake
type CrackSeg={wedges:{BasePart},glow:BasePart,frame:CFrame,len:number,width:number,appear:number}
type Crack={segs:{CrackSeg},holder:Part,dust:Emitter,active:boolean,age:number,life:number,static:boolean}
type Rock={part:BasePart,active:boolean,age:number,v:Vector3,floor:number,bounces:number}
type Wobble={part:BasePart,base:CFrame,last:CFrame,age:number,axis:Vector3}
local cracks:{Crack}={}
local rocks:{Rock}={}
local wobbles:{Wobble}={}
-- wedge layout of one diamond in the segment frame (-Z = along the crack, Y = ground normal): {x sign, z sign, wedge right, wedge up}
local WEDGE_AXES={{1,1,Vector3.yAxis,Vector3.xAxis},{-1,1,-Vector3.yAxis,-Vector3.xAxis},{1,-1,-Vector3.yAxis,Vector3.xAxis},{-1,-1,Vector3.yAxis,-Vector3.xAxis}}
local function quakePart(part:BasePart,name:string,color:Color3,material:Enum.Material):BasePart
    part.Name=name part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Material,part.Color,part.Transparency=material,color,1 part.Position=PARKED part.Parent=folder
    return part
end
for _=1,if phone then WL.Budget.cracksPhone else WL.Budget.cracks do
    local segs:{CrackSeg}={}
    for _=1,QK.segments do
        local wedges:{BasePart}={}
        for i=1,4 do wedges[i]=quakePart(Instance.new("WedgePart"),"QuakeCrack",Color3.fromRGB(44,34,28),Enum.Material.Slate) end
        local glowPart=quakePart(Instance.new("Part"),"QuakeCrackGlow",Color3.fromRGB(150,76,24),Enum.Material.Neon)
        table.insert(segs,{wedges=wedges,glow=glowPart,frame=CFrame.new(PARKED),len=1,width=1,appear=0})
    end
    local holder=volume(Vector3.new(4,.4,12)) holder.Name="QuakeDust" holder.Position=PARKED
    local dust=burstEmitter(holder,{Texture=DUST_FX.Texture,FlipbookLayout=DUST_FX.FlipbookLayout,FlipbookMode=DUST_FX.FlipbookMode,Lifetime=NumberRange.new(1.6,2.4),Speed=NumberRange.new(3,8),EmissionDirection=Enum.NormalId.Top,
        SpreadAngle=Vector2.new(35,35),Size=seq(4,9,12),Transparency=seq(.55,.72,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-20,20),Drag=1.5,
        Acceleration=Vector3.new(0,1,0),Color=ColorSequence.new(Color3.fromRGB(196,172,136),Color3.fromRGB(160,138,108))})
    table.insert(cracks,{segs=segs,holder=holder,dust=dust,active=false,age=0,life=4,static=false})
    for _=1,WL.Budget.rocksPerCrack do
        local rockPart=Instance.new("Part") rockPart.Shape=Enum.PartType.Ball
        table.insert(rocks,{part=quakePart(rockPart,"QuakeRock",Color3.fromRGB(104,88,74),Enum.Material.Slate),active=false,age=0,v=Vector3.zero,floor=0,bounces=0})
    end
end
-- BD-348: dust puff at the dino's feet and a flat crack decal a few studs ahead (fx3 "rays" alpha texture, tinted dark brown)
local feetHolder=volume(Vector3.new(3,.4,3)) feetHolder.Name="QuakeFeetDust" feetHolder.Position=PARKED
local feetPuff=burstEmitter(feetHolder,{Texture=DUST_FX.Texture,FlipbookLayout=DUST_FX.FlipbookLayout,FlipbookMode=DUST_FX.FlipbookMode,Lifetime=NumberRange.new(1.2,1.8),Speed=NumberRange.new(2,5),
    EmissionDirection=Enum.NormalId.Top,SpreadAngle=Vector2.new(60,60),Size=seq(2,4,5),Transparency=seq(.5,.7,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-20,20),Drag=1.5,
    Acceleration=Vector3.new(0,1,0),Color=ColorSequence.new(Color3.fromRGB(205,180,140),Color3.fromRGB(165,142,110))})
local decalPart=quakePart(Instance.new("Part"),"QuakeDecal",Color3.fromRGB(60,44,34),Enum.Material.SmoothPlastic)
decalPart.Size=Vector3.new(QK.decalSize,.1,QK.decalSize) decalPart.Transparency=1
local decal=Instance.new("Decal") decal.Name="QuakeCrackDecal" decal.Face=Enum.NormalId.Top decal.Color3=Color3.fromRGB(30,20,14) decal.Transparency=1
decal.Texture=require(Shared.EffectAssets).resolve("rays") decal.Parent=decalPart
local decalAge=-1
local function quakeGround(position:Vector3):(Vector3?,Vector3)
    rayParams.FilterDescendantsInstances={folder,player.Character or folder}
    local hit=workspace:Raycast(position+Vector3.new(0,120,0),Vector3.new(0,-300,0),rayParams)
    if not hit then return nil,Vector3.yAxis end
    return hit.Position,(if hit.Normal.Y>.6 then hit.Normal else Vector3.yAxis)
end
-- size and place one segment: g = open amount 0..1 (length and width), fade = 0..1 transparency
local function layoutSeg(seg:CrackSeg,g:number,fade:number)
    local h,w=math.max(.05,seg.len*.5*g),math.max(.05,seg.width*.5*math.sqrt(g)*(1-fade*.6))
    for i,wedge in seg.wedges do
        local a=WEDGE_AXES[i]
        wedge.Size=Vector3.new(.3,w,h)
        wedge.CFrame=seg.frame*CFrame.fromMatrix(Vector3.new(a[1]*w/2,0,a[2]*h/2),a[3],a[4])
        wedge.Transparency=.04+.96*fade
    end
    seg.glow.Size=Vector3.new(math.max(.05,w*.55),.05,math.max(.05,h*1.5))
    seg.glow.CFrame=seg.frame*CFrame.new(0,.16,0) seg.glow.Transparency=.55+.45*fade
end
local function parkCrack(crack:Crack)
    crack.active=false crack.holder.Position=PARKED
    for _,seg in crack.segs do
        for _,wedge in seg.wedges do wedge.Position=PARKED wedge.Transparency=1 end
        seg.glow.Position=PARKED seg.glow.Transparency=1
    end
end
local function throwRock(from:Vector3,floor:number)
    for _,rock in rocks do
        if not rock.active then
            local a=random:NextNumber(0,math.pi*2) local side=random:NextNumber(2,6)
            rock.v=Vector3.new(math.cos(a)*side,random:NextNumber(10,17),math.sin(a)*side)
            rock.active,rock.age,rock.floor,rock.bounces=true,0,floor,0
            rock.part.Size=Vector3.one*random:NextNumber(.5,1.1) rock.part.Position=from+Vector3.new(0,.4,0) rock.part.Transparency=0
            return
        end
    end
end
-- a few random tries in front of the camera, minDist..maxDist from the dino, every segment clear of the dino
local function openCrack(root:Vector3,static:boolean)
    local crack:Crack?=nil
    for _,c in cracks do if not c.active then crack=c break end end
    if not crack then return end
    local cam=workspace.CurrentCamera
    local look=if cam then cam.CFrame.LookVector*Vector3.new(1,0,1) else Vector3.zAxis
    local heading=if look.Magnitude>.01 then math.atan2(look.Z,look.X) else 0
    for _=1,5 do
        local a=heading+math.rad(random:NextNumber(-QK.viewCone,QK.viewCone)) local dist=random:NextNumber(QK.minDist,QK.maxDist)
        local p=root+Vector3.new(math.cos(a)*dist,0,math.sin(a)*dist)
        local dirAngle=random:NextNumber(0,math.pi*2)
        local total=random:NextNumber(QK.length[1],QK.length[2]) local segLen=total/QK.segments
        local width=random:NextNumber(QK.width[1],QK.width[2])
        local frames:{CFrame}={} local floor=math.huge local ok=true
        for i=1,QK.segments do
            dirAngle+=math.rad(random:NextNumber(-28,28))
            local dir=Vector3.new(math.cos(dirAngle),0,math.sin(dirAngle))
            local hit,up=quakeGround(p+dir*(segLen/2))
            if not hit or ((hit-root)*Vector3.new(1,0,1)).Magnitude<QK.clearOfDino then ok=false break end
            local forward=(dir-up*dir:Dot(up)).Unit
            frames[i]=CFrame.fromMatrix(hit+up*.06,forward:Cross(up).Unit,up)
            floor=math.min(floor,hit.Y) p+=dir*segLen
        end
        if ok then
            crack.active,crack.age,crack.static=true,0,static
            crack.life=random:NextNumber(QK.life[1],QK.life[2])
            for i,seg in crack.segs do
                seg.frame=frames[i] seg.len=segLen*1.35
                seg.width=width*(.35+.65*math.sin(math.pi*(i-.5)/QK.segments))
                seg.appear=(i-1)/QK.segments*QK.grow
                layoutSeg(seg,if static then 1 else 0,0)
            end
            crack.holder.CFrame=frames[math.ceil(QK.segments/2)] crack.holder.Size=Vector3.new(width*1.5,.4,total)
            if not static then
                crack.dust.e:Emit(if phone then 4 else 8)
                for _=1,WL.Budget.rocksPerCrack do throwRock(frames[random:NextInteger(1,#frames)].Position,floor) end
            end
            return
        end
    end
end
local wobbleParams=OverlapParams.new() wobbleParams.FilterType=Enum.RaycastFilterType.Exclude wobbleParams.MaxParts=60
local function wobbleProps(root:Vector3)
    wobbleParams.FilterDescendantsInstances={folder,player.Character or folder}
    local count=#wobbles
    for _,part in workspace:GetPartBoundsInRadius(root,QK.wobbleRadius,wobbleParams) do
        if count>=QK.wobbleMax then break end
        local s=part.Size
        if part.Anchored and not part:IsA("Terrain") and math.max(s.X,s.Y,s.Z)<=QK.propMaxSize and part.Transparency<1 then
            local model=part:FindFirstAncestorWhichIsA("Model")
            local busy=model~=nil and model:FindFirstChildWhichIsA("Humanoid")~=nil
            for _,w in wobbles do if w.part==part then busy=true break end end
            if not busy then
                count+=1
                local a=random:NextNumber(0,math.pi*2)
                table.insert(wobbles,{part=part,base=part.CFrame,last=part.CFrame,age=0,axis=Vector3.new(math.cos(a),0,math.sin(a))})
            end
        end
    end
end
local function quakePulse(root:Vector3,motion:boolean)
    local ground,up=quakeGround(root)
    if ground then
        if motion then feetHolder.CFrame=CFrame.new(ground+up*.3) feetPuff.e:Emit(if phone then QK.feetPuffPhone else QK.feetPuff) end
        local cam=workspace.CurrentCamera
        local look=if cam then cam.CFrame.LookVector*Vector3.new(1,0,1) else Vector3.zAxis
        local ahead=if look.Magnitude>.01 then look.Unit else Vector3.zAxis
        local spot,n2=quakeGround(root+ahead*random:NextNumber(QK.decalAhead[1],QK.decalAhead[2]))
        if spot then
            decalPart.CFrame=CFrame.fromMatrix(spot+n2*.08,ahead:Cross(n2).Unit,n2)*CFrame.Angles(0,random:NextNumber(0,math.pi*2),0)
            decalAge=0
        end
    end
    openCrack(root,not motion)
    if random:NextNumber()<.4 then openCrack(root,not motion) end
    if motion then
        for _,crack in cracks do if crack.active and crack.age>QK.grow then crack.dust.e:Emit(if phone then 2 else 4) end end
        wobbleProps(root)
    end
    WS.fire("quake")
end
local function updateQuake(dt:number)
    if decalAge>=0 then
        decalAge+=dt
        local a=if decalAge<.25 then decalAge/.25 elseif decalAge>QK.decalLife-.8 then math.max(0,(QK.decalLife-decalAge)/.8) else 1
        decal.Transparency=1-.95*a
        if decalAge>=QK.decalLife then decalAge=-1 decal.Transparency=1 decalPart.Position=PARKED end
    end
    for _,crack in cracks do
        if crack.active then
            crack.age+=dt
            local closing=math.clamp((crack.age-crack.life)/QK.close,0,1)
            if closing>=1 then
                parkCrack(crack)
            elseif crack.static then
                if closing>0 then for _,seg in crack.segs do layoutSeg(seg,1,closing) end end
            elseif crack.age<QK.grow*1.6 or closing>0 then
                for _,seg in crack.segs do
                    local g=math.clamp((crack.age-seg.appear)/(QK.grow/QK.segments*1.6),0,1)
                    layoutSeg(seg,(1-(1-g)^2)*(1-closing),closing)
                end
            end
        end
    end
    local gravity=Vector3.new(0,-70,0)
    for _,rock in rocks do
        if rock.active then
            rock.age+=dt rock.v+=gravity*dt
            local pos=rock.part.Position+rock.v*dt
            local radius=rock.part.Size.Y/2
            if pos.Y<rock.floor+radius and rock.v.Y<0 then
                pos=Vector3.new(pos.X,rock.floor+radius,pos.Z) rock.bounces+=1
                rock.v=if rock.bounces>2 then Vector3.zero else Vector3.new(rock.v.X*.55,-rock.v.Y*.38,rock.v.Z*.55)
            end
            rock.part.Position=pos
            rock.part.Transparency=math.clamp((rock.age-2.2)/.7,0,1)
            if rock.age>2.9 then rock.active=false rock.part.Position=PARKED rock.part.Transparency=1 end
        end
    end
    for i=#wobbles,1,-1 do
        local w=wobbles[i]
        w.age+=dt
        if w.part.Parent==nil or w.part.CFrame~=w.last then table.remove(wobbles,i) -- moved by something else: leave it alone
        elseif w.age>=QK.pulseSeconds then w.part.CFrame=w.base table.remove(wobbles,i)
        else
            local swing=math.sin(w.age*22)*(1-w.age/QK.pulseSeconds)*math.rad(QK.wobbleDegrees)
            w.last=w.base*CFrame.fromAxisAngle(w.axis,swing) w.part.CFrame=w.last
        end
    end
end
local function stopQuake()
    decalAge=-1 decal.Transparency=1 decalPart.Position=PARKED
    for _,crack in cracks do if crack.active then parkCrack(crack) end end
    for _,rock in rocks do if rock.active then rock.active=false rock.part.Position=PARKED rock.part.Transparency=1 end end
    for _,w in wobbles do if w.part.Parent and w.part.CFrame==w.last then w.part.CFrame=w.base end end
    table.clear(wobbles)
end
local function stopOneShots()
    for _,slot in bolts do slot.active=false setBolt(slot,false) end
    for _,slot in bombSlots do slot.active=false slot.trail.Enabled=false slot.tail.e.Enabled=false slot.glow.Brightness=0 slot.part.Position=PARKED end
end

-- ---------------------------------------------------------------- title card
local gui=Instance.new("ScreenGui") gui.Name="WeatherTitle" gui.ResetOnSpawn=false gui.IgnoreGuiInset=true gui.DisplayOrder=40
gui.Parent=player:WaitForChild("PlayerGui")
local title=Instance.new("TextLabel") title.Name="Title" title.AnchorPoint=Vector2.new(.5,.5) title.Position=UDim2.fromScale(.5,WL.Title.y) title.Size=UDim2.fromScale(WL.Title.width,WL.Title.height)
title.BackgroundTransparency=1 title.Font=Enum.Font.FredokaOne title.TextScaled=true title.TextTransparency=1 title.Text="" title.ZIndex=5 title.Parent=gui
local stroke=Instance.new("UIStroke") stroke.Thickness=5 stroke.Color=Color3.fromRGB(14,20,34) stroke.Transparency=1 stroke.Parent=title
local titleScale=Instance.new("UIScale") titleScale.Parent=title
local sub=Instance.new("TextLabel") sub.Name="Sub" sub.AnchorPoint=Vector2.new(.5,0) sub.Position=UDim2.fromScale(.5,1) sub.Size=UDim2.fromScale(.7,.42)
sub.BackgroundTransparency=1 sub.Font=Enum.Font.FredokaOne sub.TextScaled=true sub.TextTransparency=1 sub.TextColor3=Color3.new(1,1,1) sub.Text="Special eggs can drop!" sub.ZIndex=5 sub.Parent=title
local subStroke=Instance.new("UIStroke") subStroke.Thickness=3 subStroke.Color=Color3.fromRGB(14,20,34) subStroke.Transparency=1 subStroke.Parent=sub
local titleToken=0
-- BD-328: the big title card never draws over an open menu: it waits (up to 20 s) for the menu to close, then plays.
local function menuOpen():boolean return player:GetAttribute("MenuOpen")==true end
player:GetAttributeChangedSignal("MenuOpen"):Connect(function() gui.Enabled=not menuOpen() end) -- a menu opened mid-card hides it
local titleBig=false -- true while the big card (with the bonus line) is showing
local function inHall():boolean return Cave.inside() or Cave.amount()>.01 end
-- BD-403: walking into the cave while the big card is up turns it into the small soft toast at once (no bonus line).
local function softenTitle()
    if not titleBig then return end
    titleBig=false
    titleScale.Scale=.4
    title.TextTransparency,stroke.Transparency,sub.TextTransparency,subStroke.Transparency=.35,.5,1,1
end
local function showTitle(id:string,name:string,soft:boolean?)
    titleToken+=1 local mine=titleToken
    soft=soft or inHall() -- re-checked here: the cave may have been entered since the weather changed
    titleBig=not soft
    if menuOpen() then
        task.spawn(function()
            local waited=0
            while menuOpen() and waited<20 do task.wait(.25) waited+=.25 end
            if mine==titleToken and not menuOpen() then showTitle(id,name,soft or inHall()) end
        end)
        return
    end
    title.Text=if soft then name else string.upper(name).."!" title.TextColor3=TITLE_COLOR[id] or Color3.new(1,1,1)
    titleScale.Scale=if soft then .4 elseif Theme.MotionEnabled then 2.2 else 1
    title.TextTransparency,stroke.Transparency,sub.TextTransparency,subStroke.Transparency=if soft then .35 else 0,if soft then .5 else 0,1,1
    if not soft then sub.TextTransparency,subStroke.Transparency=0,0 end
    if Theme.MotionEnabled and not soft then TweenService:Create(titleScale,TweenInfo.new(.45,Enum.EasingStyle.Back,Enum.EasingDirection.Out),{Scale=1}):Play() end
    task.delay(if soft then 1.8 else 3.2,function()
        if mine~=titleToken then return end
        local info=TweenInfo.new(.8)
        TweenService:Create(title,info,{TextTransparency=1}):Play() TweenService:Create(stroke,info,{Transparency=1}):Play()
        TweenService:Create(sub,info,{TextTransparency=1}):Play() TweenService:Create(subStroke,info,{Transparency=1}):Play()
    end)
end

-- ---------------------------------------------------------------- main loop
local activeId="clear" local k=0 local shownId="clear"
local nextBolt=0 local nextDouble=0 local nextFar=0 local nextBomb=0 local nextQuakeBurst=0 local quakeUntil=0 local nextPulse=0
local columnAnchors:{Vector3}?=nil
local colorClock=0 local auroraWasOn=false local starsSet=-1
local WHITE:{number}={255,255,255}
local lerpNum=WL.lerp
local function shiftOf(base:Color3,rgb:{number}):Color3
    if rgb[1]+rgb[2]+rgb[3]==0 then return base end
    return c3(rgb)
end
local function seqColor(a:{number},b:{number},c:{number}):ColorSequence
    return ColorSequence.new({ColorSequenceKeypoint.new(0,c3(a)),ColorSequenceKeypoint.new(.5,c3(b)),ColorSequenceKeypoint.new(1,c3(c))})
end

local function updateAurora(root:Vector3,now:number,on:boolean,recolor:boolean)
    if on~=auroraWasOn then
        auroraWasOn=on
        for _,r in curtainRays do r.beam.Enabled=on end
    end
    if not on then return end
    for _,r in curtainRays do
        local c,i=r.curtain,r.index
        local center=c*2.1+now*.012*(if c%2==0 then 1 else -1)
        local a=center+(i-(CURTAIN_RAYS+1)/2)/CURTAIN_RAYS*2.3+math.sin(now*.2+i*.5)*.035
        local radius=150+c*22+math.sin(i*.9+now*.3+c)*12
        local baseY=root.Y+WL.Aurora.baseY+c*WL.Aurora.step
        local x,z=root.X+math.cos(a)*radius,root.Z+math.sin(a)*radius
        r.bottom.WorldPosition=Vector3.new(x,baseY,z)
        r.top.WorldPosition=Vector3.new(x+math.sin(now*.3+i)*8,baseY+170+math.sin(now*.4+i*.6+c)*45,z)
        if recolor then
            local hue=i/CURTAIN_RAYS*.55+c*.21
            local c0=WL.aurora(now,hue) local c1=WL.aurora(now+5,hue+.12) local c2=WL.aurora(now+10,hue+.3)
            r.beam.Color=seqColor(c0,c1,WL.scale(c2,.7))
            local a1=lerpNum(1,WL.Aurora.alpha+.08*math.sin(now*1.3+i*1.9),k)
            r.beam.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.12,math.min(1,a1+.1)),NumberSequenceKeypoint.new(.5,a1),NumberSequenceKeypoint.new(.8,math.min(1,a1+.2)),NumberSequenceKeypoint.new(1,1)})
        end
    end
end

RunService.Heartbeat:Connect(function(dt)
    local now=os.clock()
    local id=workspace:GetAttribute("WeatherId") or "clear"
    local c=player.Character
    local rootPart=if c then c:FindFirstChild("HumanoidRootPart") else nil
    local root:Vector3?=if rootPart and rootPart:IsA("BasePart") then (rootPart::BasePart).Position else nil
    -- BD-398: inside the cave hall weather is nearly invisible: no rigs, bolts, bombs, cracks, moon, aurora, shake or title card
    local hall=Cave.inside() or Cave.amount()>.01
    if hall then softenTitle() end
    local motion=Theme.MotionEnabled and root~=nil and not hall
    -- fade current weather out, then switch; ramp the new one in
    if id==activeId then k=math.min(1,k+dt/2.4) else k=math.max(0,k-dt/1.1) if k<=0 then activeId=id columnAnchors=nil end end
    if activeId~=shownId and id==activeId and id~="clear" then
        shownId=activeId
        showTitle(id,workspace:GetAttribute("WeatherName") or id,hall) -- inside the cave only the small soft toast (text, not an effect; BD-398)
    elseif id=="clear" then shownId="clear" end

    local look=WL.Looks[activeId] or WL.Looks.clear
    local outside=1-Cave.amount() -- BD-383: weather grade, bloom, rays, haze, exposure and lamps fade to nothing inside the cave hall
    local t=WL.strength(k,Theme.MotionEnabled)*outside
    local animT=if Theme.MotionEnabled then now else 0
    flash=math.max(0,flash-dt*2.2) pulse=math.max(0,pulse-dt*.9)
    -- aurora recolours the whole sky from the hue cycle; every other event uses its fixed look
    local tint,fog,decay,shiftTop,shiftBottom,amb,glowRgb=look.tint,look.fog,look.decay,look.shiftTop,look.shiftBottom,look.amb,look.glow
    if activeId=="aurora" then
        fog=WL.scale(WL.aurora(animT,0),.3) decay=WL.scale(WL.aurora(animT,.45),.85)
        shiftTop=WL.scale(WL.aurora(animT,.25),.7) shiftBottom=WL.scale(WL.aurora(animT,.6),WL.Aurora.horizonGlow)
        amb=WL.scale(WL.aurora(animT,.1),.55) tint=WL.mix(WHITE,WL.aurora(animT,.35),.5) glowRgb=WL.aurora(animT,.7)
    end
    grade.TintColor=c3(WL.mix(WHITE,tint,t))
    grade.Saturation=lerpNum(0,look.sat,t) grade.Contrast=lerpNum(0,look.contrast,t)
    grade.Brightness=lerpNum(0,look.bright,t)+(flash*.5+pulse*.12)*outside
    bloom.Intensity=lerpNum(0,look.bloom,t)+flash*1.5*outside
    bloom.Threshold=lerpNum(.95,.72,t) bloom.Size=lerpNum(24,40,t)
    rays.Intensity=lerpNum(0,look.rays,t) rays.Spread=.7
    dof.FarIntensity=lerpNum(0,look.dof,t) dof.FocusDistance=lerpNum(250,look.dofFocus,t) dof.InFocusRadius=lerpNum(100,35,t)
    atmosphere.Density=lerpNum(baseAtmo.density,math.max(baseAtmo.density,look.density),t)
    atmosphere.Offset=lerpNum(baseAtmo.offset,look.offset,t)
    atmosphere.Haze=lerpNum(baseAtmo.haze,math.max(baseAtmo.haze,look.haze),t)
    atmosphere.Glare=lerpNum(baseAtmo.glare,math.max(baseAtmo.glare,look.glare),t)
    local fogStart,fogEnd=WL.fog(look,t,CLEAR,fogCap)
    local fogColor=c3(CLEAR.fog):Lerp(c3(fog),t)
    Lighting.FogStart,Lighting.FogEnd=fogStart,fogEnd Lighting.FogColor=fogColor
    atmosphere.Color=baseAtmo.color:Lerp(c3(fog),t)
    atmosphere.Decay=baseAtmo.decay:Lerp(c3(decay),t)
    -- sky treatment: colour shift on the sky dome and horizon, darker exposure, more stars
    Lighting.ColorShift_Top=baseShiftTop:Lerp(shiftOf(baseShiftTop,shiftTop),t)
    Lighting.ColorShift_Bottom=baseShiftBottom:Lerp(shiftOf(baseShiftBottom,shiftBottom),t)
    Lighting.ExposureCompensation=baseExposure+lerpNum(0,look.exposure,t)+flash*.9*outside
    if look.cloudCover>=0 then
        clouds.Cover=lerpNum(baseCloud.cover,look.cloudCover,t) clouds.Density=lerpNum(baseCloud.density,look.cloudDensity,t)
        clouds.Color=baseCloud.color:Lerp(c3(look.cloudColor),t)
    else clouds.Cover,clouds.Density,clouds.Color=baseCloud.cover,baseCloud.density,baseCloud.color end
    if sky then sky.CelestialBodiesShown=activeId=="clear" or k<=0 or hall end
    if sky and look.stars>=0 then
        local want=math.floor(lerpNum(baseStars,look.stars,t)/100)*100
        if want~=starsSet then starsSet=want sky.StarCount=want end
    elseif sky and starsSet~=-1 then starsSet=-1 sky.StarCount=baseStars end
    -- world-wide light tint, so the whole scene (not just near the player) takes on the event mood
    local ambient=if amb then c3(amb) else baseAmbient
    Lighting.Ambient=baseAmbient:Lerp(ambient,t*.8) Lighting.OutdoorAmbient=baseOutdoor:Lerp(ambient,t)
    -- zoomed-out cameras see further: grow the particle volumes and keep their density
    local cam=workspace.CurrentCamera
    local zoom=if cam and root then math.clamp((cam.CFrame.Position-root).Magnitude/16,1,6) else 1
    -- near-area lamp (keeps the dino and food within about 25 studs bright) and the event-coloured glow
    if root then
        lampPart.Position=root+Vector3.new(0,7,0)
        lamp.Brightness=look.lamp*t
        glow.Color=c3(glowRgb) glow.Range=look.glowRange
        glow.Brightness=(look.glowBright*t+(if activeId=="thunder" then flash*3*outside else 0))*(if Theme.MotionEnabled then 1 else .4)
    else lamp.Brightness=0 glow.Brightness=0 end

    -- particle rigs follow the player; only the active weather emits (BD-265: Settings Weather Full / Lite / Off; haze, light and title stay)
    local weatherFactor=require(Shared.SettingsModel).factor(require(Shared.SettingsModel).weather())
    for weatherId,list in rig do
        local on=motion and weatherId==activeId and k>0
        local scaleRate=math.min(zoom*zoom,5)
        for _,item in list do
            item.e.Enabled=on and weatherFactor>0 item.e.Rate=item.rate*k*weatherFactor*(if item.fixed then 1 else scaleRate)
        end
        if on and root then
            local parts=rigParts[weatherId]
            if parts then for _,p in parts do p.part.Size=Vector3.new(p.base.X*zoom,p.base.Y,p.base.Z*zoom) p.part.Position=root+p.offset end end
        end
    end
    local live=motion and root~=nil and not hall
    if not live then stopOneShots() end
    -- volcano: three far eruption columns + lava bombs
    if live and root and activeId=="volcano" and k>.3 then
        if not columnAnchors then
            local anchors:{Vector3}={}
            for i,offset in COLUMN_OFFSETS do anchors[i]=groundAt(root+offset) columns[i].Position=anchors[i] end
            columnAnchors=anchors
        end
        if now>=nextBomb then nextBomb=now+random:NextNumber(.45,1.1) lavaBomb(root) end
        shake=math.max(shake,.18)
    end
    -- thunder: forked bolts, double strikes and sheet-lightning flashes
    if live and root and activeId=="thunder" and k>.4 then
        if now>=nextBolt then
            nextBolt=now+random:NextNumber(2.2,5)
            if bolt(root) and random:NextNumber()<.35 then nextDouble=now+random:NextNumber(.15,.35) end
        end
        if nextDouble>0 and now>=nextDouble then nextDouble=0 bolt(root) end
        if now>=nextFar then nextFar=now+random:NextNumber(1.2,3) flash=math.max(flash,.3) end
    end
    -- thunder with Reduce Motion: no bolts or flashes, only a slow soft swell of light (never a strobe)
    if not Theme.MotionEnabled and not hall and activeId=="thunder" and k>.4 then
        flash=math.max(flash,WL.Swell.peak*(1+math.sin(now*WL.Swell.rate))/2)
    end
    -- quake: tremor pulses open ground cracks in view, with a gentle rumble synced to each pulse (none with Reduce Motion)
    if root and not hall and activeId=="quake" and k>.3 then
        if now>=nextQuakeBurst then
            nextQuakeBurst=now+random:NextNumber(WL.Quake.pulseEvery[1],WL.Quake.pulseEvery[2]) quakeUntil=now+WL.Quake.pulseSeconds
            quakePulse(root,Theme.MotionEnabled)
        end
        if motion and now<quakeUntil then shake=math.max(shake,WL.Quake.shake*math.sin(math.pi*(1-(quakeUntil-now)/WL.Quake.pulseSeconds))) end
    elseif activeId~="quake" or not root or hall then stopQuake() end
    -- blood moon sky props
    local moonOn=live and activeId=="bloodmoon" and k>0
    if moonOn and root then
        local base=root+MOON_DIR*WL.Moon.distance
        moonCore.Position=base moonCore.Transparency=lerpNum(1,.04,k)
        local beat=1+math.sin(now*.7)*.05
        moonCore.Size=Vector3.one*WL.Moon.core*beat
        for i,halo in halos do halo.Position=base halo.Transparency=lerpNum(1,HALO_ALPHA[i],k) end
        if now>=nextPulse then nextPulse=now+random:NextNumber(6,11) pulse=1 end
    else
        moonCore.Transparency=1 for _,halo in halos do halo.Transparency=1 end
    end
    -- aurora: full-sky rays and arcs, ground ring (hue colours refreshed 10 times a second)
    colorClock+=dt local recolor=colorClock>=.1 if recolor then colorClock=0 end
    local auroraOn=live and activeId=="aurora" and k>0
    updateAurora(root or Vector3.zero,now,auroraOn,recolor)
    -- pooled one-shot effects
    updateBolts(dt) updateRings(dt) updateBursts(dt) updateBombs(dt,root) updateQuake(dt)
    if hall then shake=0 end -- BD-403: weather never touches the cave interior, not even a faint quake rumble
    if shake>.01 and Theme.MotionEnabled then shake=math.max(0,shake-dt*1.1) end
    if not Theme.MotionEnabled then shake=0 end
    Cave.step(dt) -- last: the cave look is written after the weather values above
end)
-- camera shake is applied after the camera script each frame, so it never fights the game's own camera offset
RunService:BindToRenderStep("WeatherShake",Enum.RenderPriority.Camera.Value+1,function()
    local camera=workspace.CurrentCamera
    if not camera or shake<=.01 or not Theme.MotionEnabled then return end
    local n=os.clock()*38
    camera.CFrame*=CFrame.new(math.sin(n*1.3)*shake*.45,math.cos(n*1.7)*shake*.4,0)*CFrame.Angles(0,0,math.sin(n*.9)*shake*.012)
end)
