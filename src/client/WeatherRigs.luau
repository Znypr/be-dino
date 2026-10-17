--!strict
-- Weather particle rigs (BD-627, docs/153): the rain / thunder / blizzard / volcano / aurora / quake / blood moon emitters and the distance fog banks,
-- moved unchanged out of WeatherVisuals.client.luau. Returns the rig tables the main loop drives plus the volcano columns and the aurora curtain emitter.
local Shared=game:GetService("ReplicatedStorage").Shared
local Assets=require(Shared.EffectAssets)
local WT=require(Shared.WeatherTextures)
type Emitter={e:ParticleEmitter,rate:number,fixed:boolean}
return function(ctx:any)
local kit=ctx.kit
local seq,tex,rateOf,volume,emitter=kit.seq,kit.tex,kit.rateOf,kit.volume,kit.emitter
local TEX_SMOKE,TEX_SPARK,TEX_FIRE,DUST_FX=kit.TEX_SMOKE,kit.TEX_SPARK,kit.TEX_FIRE,kit.DUST_FX

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
    local streaks=emitter(sky,id,"streaks",tex("rainStreak","streaks",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(95,115),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(if heavy then 34 else 12,-70,0),Orientation=Enum.ParticleOrientation.VelocityParallel,
        Size=seq(if heavy then .7 else .56,.5),Squash=seq(-20,-20),Transparency=seq(.22,.06),LightEmission=.6,
        Color=ColorSequence.new(Color3.fromRGB(190,220,255),Color3.fromRGB(140,185,240)),SpreadAngle=Vector2.new(4,4),
    }),rateOf("rainStreak","streaks"))
    -- BD-348: long bright streaks right in front of the camera (a small volume above the dino, no distance fade)
    local nearSky=volume(Vector3.new(26,1,26))
    local nearStreaks=emitter(nearSky,id,"near",tex("rainStreak","near",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(70,90),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(if heavy then 30 else 10,-60,0),Orientation=Enum.ParticleOrientation.VelocityParallel,
        Size=seq(.9,.7),Squash=seq(-26,-26),Transparency=seq(.18,.05),LightEmission=.7,
        Color=ColorSequence.new(Color3.fromRGB(215,236,255),Color3.fromRGB(165,205,250)),SpreadAngle=Vector2.new(3,3),
    }),rateOf("rainStreak","near"),true)
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
    local snow=emitter(sky,"blizzard","snow",tex("snowFlakeSheet","snow",{
        Texture=TEX_SPARK,Speed=NumberRange.new(10,22),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(-46,-6,14),Size=seq(.5,.8),Transparency=seq(.05,.1,.5),LightEmission=.35,Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-90,90),
        Color=ColorSequence.new(Color3.new(1,1,1),Color3.fromRGB(205,230,255)),SpreadAngle=Vector2.new(18,18),
    }),rateOf("snowFlakeSheet","snow"))
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
    local ash=emitter(sky,"volcano","ash",tex("ashFlake","ash",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(4,9),EmissionDirection=Enum.NormalId.Bottom,
        Acceleration=Vector3.new(7,-4,3),Size=seq(.8,1.4),Transparency=seq(.5,.3,.9),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-60,60),
        Color=ColorSequence.new(Color3.fromRGB(70,64,68),Color3.fromRGB(38,34,36)),
    }),rateOf("ashFlake","ash"))
    local low=volume(Vector3.new(70,2,70))
    local embers=emitter(low,"volcano","embers",tex("emberSpark","embers",{
        Texture=TEX_SPARK,Speed=NumberRange.new(4,10),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(3,5,0),Size=seq(.55,.4,0),Transparency=seq(0,0,1),LightEmission=1,
        Color=ColorSequence.new({ColorSequenceKeypoint.new(0,Color3.fromRGB(255,235,120)),ColorSequenceKeypoint.new(.5,Color3.fromRGB(255,120,30)),ColorSequenceKeypoint.new(1,Color3.fromRGB(180,30,10))}),
        SpreadAngle=Vector2.new(45,45),
    }),rateOf("emberSpark","embers"))
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
local curtainEmit:Emitter?=nil -- BD-131: the textured sky curtain, built only while EffectAssets auroraCurtain holds an id
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
    if WT.plan(Assets,"auroraCurtain","curtain") then
        local skyBand=volume(Vector3.new(420,30,420))
        local curtain=emitter(skyBand,"aurora","curtain",tex("auroraCurtain","curtain",{
            Speed=NumberRange.new(0,.6),EmissionDirection=Enum.NormalId.Top,Size=seq(120,170,210),Transparency=seq(1,.8,1),LightEmission=1,
            Color=ColorSequence.new(Color3.fromRGB(110,255,190),Color3.fromRGB(190,150,255)),
        }),rateOf("auroraCurtain","curtain"),true)
        curtainEmit=curtain
        addRig("aurora",skyBand,Vector3.new(0,70,0),{curtain})
    end
    fogBanks("aurora",ColorSequence.new(Color3.fromRGB(80,230,200),Color3.fromRGB(170,120,255)),{Transparency=seq(1,.72,1),LightEmission=1})
end
-- QUAKE (light ground dust + dust haze; cracks, rocks and tremors are world one-shots below)
do
    local ground=volume(Vector3.new(70,.2,70))
    local dust=emitter(ground,"quake","dust",tex("dustSand","dust",{
        Texture=DUST_FX.Texture,FlipbookLayout=DUST_FX.FlipbookLayout,FlipbookMode=DUST_FX.FlipbookMode,Speed=NumberRange.new(3,9),EmissionDirection=Enum.NormalId.Top,
        Size=seq(10,24,34),Transparency=seq(.82,.7,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-14,14),
        Color=ColorSequence.new(Color3.fromRGB(196,170,128),Color3.fromRGB(160,138,104)),SpreadAngle=Vector2.new(30,30),
    }),rateOf("dustSand","dust"))
    addRig("quake",ground,FEET,{dust})
    fogBanks("quake",ColorSequence.new(Color3.fromRGB(190,158,116),Color3.fromRGB(150,124,92)),{Transparency=seq(1,.88,1)})
end
-- BLOOD MOON (red motes, ground fog, red fog walls)
do
    local air=volume(Vector3.new(80,14,80))
    local motes=emitter(air,"bloodmoon","motes",tex("bloodMoonMotes","motes",{
        Texture=TEX_SPARK,Speed=NumberRange.new(.5,2.5),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,1.2,0),Size=seq(0,.9,0),Transparency=seq(1,.05,1),LightEmission=1,Rotation=NumberRange.new(0,360),
        Color=ColorSequence.new(Color3.fromRGB(255,60,90),Color3.fromRGB(255,150,170)),
    }),rateOf("bloodMoonMotes","motes"))
    local ground=volume(Vector3.new(90,.2,90))
    local fogBank=emitter(ground,"bloodmoon","fog",{
        Texture=TEX_SMOKE,Speed=NumberRange.new(1,3),EmissionDirection=Enum.NormalId.Top,
        Size=seq(34,56),Transparency=seq(1,.88,1),Color=ColorSequence.new(Color3.fromRGB(150,16,40)),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-5,5),
    })
    addRig("bloodmoon",air,Vector3.new(0,6,0),{motes})
    addRig("bloodmoon",ground,FEET,{fogBank})
    fogBanks("bloodmoon",ColorSequence.new(Color3.fromRGB(170,18,44),Color3.fromRGB(90,8,28)),{Transparency=seq(1,.88,1),Size=seq(90,130,170)})
end
return {rig=rig,rigParts=rigParts,columns=columns,COLUMN_OFFSETS=COLUMN_OFFSETS,curtainEmit=curtainEmit}
end
