--!strict
-- Weather sky props (BD-627, docs/153): the blood moon (core, halos, optional textured disc) and the aurora curtain ribbons, with their per-frame updates,
-- moved unchanged out of WeatherVisuals.client.luau. updateAurora / updateMoon take the ramp k from the main loop as a parameter.
local Shared=game:GetService("ReplicatedStorage").Shared
local WL=require(Shared.WeatherLooks)
local Assets=require(Shared.EffectAssets)
local WT=require(Shared.WeatherTextures)
type Emitter={e:ParticleEmitter,rate:number,fixed:boolean}
return function(ctx:any)
local folder:Folder=ctx.folder
local random:Random=ctx.random
local fx:{flash:number,shake:number,pulse:number}=ctx.fx
local c3=ctx.kit.c3
local curtainEmit:Emitter?=ctx.curtainEmit
local lerpNum=WL.lerp

local moonCore=Instance.new("Part") moonCore.Name="EventMoon" moonCore.Shape=Enum.PartType.Ball
moonCore.Anchored,moonCore.CanCollide,moonCore.CanTouch,moonCore.CanQuery,moonCore.CastShadow=true,false,false,false,false
moonCore.Size,moonCore.Material,moonCore.Color,moonCore.Transparency,moonCore.Parent=Vector3.one*WL.Moon.core,Enum.Material.Neon,Color3.fromRGB(255,96,64),1,folder
local halos:{Part}={}
for i,size in WL.Moon.halos do
    local halo=moonCore:Clone() halo.Name="EventMoonHalo"..i halo.Size=Vector3.one*size halo.Transparency=1 halo.Color=Color3.fromRGB(255,70,50) halo.Parent=folder
    table.insert(halos,halo)
end
local HALO_ALPHA={.84,.93,.97}
-- BD-131: with a bloodMoonDisc texture the Neon ball is hidden and a billboard disc (craters, crimson tint) takes its place; the halos stay.
local MOON_DISC=WT.plan(Assets,"bloodMoonDisc","disc")
local moonBoard:BillboardGui?=nil
local moonImage:ImageLabel?=nil
if MOON_DISC then
    local size=WL.Moon.core*MOON_DISC.tune.scale
    local board=Instance.new("BillboardGui") board.Name="EventMoonDisc" board.Adornee=moonCore board.AlwaysOnTop=false board.LightInfluence=0
    board.Size=UDim2.fromScale(size,size) board.Enabled=false board.Parent=moonCore
    local image=Instance.new("ImageLabel") image.Name="Disc" image.BackgroundTransparency=1 image.Size=UDim2.fromScale(1,1) image.Image=MOON_DISC.texture
    image.ImageColor3=c3(MOON_DISC.tune.color) image.ImageTransparency=1 image.Parent=board
    moonBoard,moonImage=board,image
end
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

local nextPulse=0
local auroraWasOn=false
local function seqColor(a:{number},b:{number},c:{number}):ColorSequence
    return ColorSequence.new({ColorSequenceKeypoint.new(0,c3(a)),ColorSequenceKeypoint.new(.5,c3(b)),ColorSequenceKeypoint.new(1,c3(c))})
end

local function updateAurora(root:Vector3,now:number,on:boolean,recolor:boolean,k:number)
    if on~=auroraWasOn then
        auroraWasOn=on
        for _,r in curtainRays do r.beam.Enabled=on end
    end
    if not on then return end
    if curtainEmit and recolor then curtainEmit.e.Color=seqColor(WL.aurora(now,.2),WL.aurora(now+5,.5),WL.aurora(now+10,.8)) end
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

local function updateMoon(root:Vector3?,now:number,moonOn:boolean,k:number)
    if moonOn and root then
        local base=root+MOON_DIR*WL.Moon.distance
        moonCore.Position=base moonCore.Transparency=if moonImage then 1 else lerpNum(1,.04,k)
        local beat=1+math.sin(now*.7)*(if MOON_DISC then MOON_DISC.tune.beat else .05)
        moonCore.Size=Vector3.one*WL.Moon.core*beat
        if moonBoard and moonImage and MOON_DISC then
            local size=WL.Moon.core*MOON_DISC.tune.scale*beat
            moonBoard.Size=UDim2.fromScale(size,size) moonBoard.Enabled=true
            moonImage.ImageTransparency=lerpNum(1,MOON_DISC.tune.transparency,k)
        end
        for i,halo in halos do halo.Position=base halo.Transparency=lerpNum(1,HALO_ALPHA[i],k) end
        if now>=nextPulse then nextPulse=now+random:NextNumber(6,11) fx.pulse=1 end
    else
        moonCore.Transparency=1 for _,halo in halos do halo.Transparency=1 end
        if moonBoard then moonBoard.Enabled=false end
    end
end
return {updateAurora=updateAurora,updateMoon=updateMoon}
end
