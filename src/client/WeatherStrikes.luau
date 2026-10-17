--!strict
-- Weather one-shots (BD-627, docs/153): pooled lightning bolts, shock rings, lava impact bursts and lava bombs, moved unchanged out of
-- WeatherVisuals.client.luau. The screen flash / camera shake / light pulse the main loop reads live in the shared fx table.
local Shared=game:GetService("ReplicatedStorage").Shared
local WL=require(Shared.WeatherLooks)
local WS=require(Shared.WeatherSounds)
local Assets=require(Shared.EffectAssets)
local WT=require(Shared.WeatherTextures)
type Emitter={e:ParticleEmitter,rate:number,fixed:boolean}
return function(ctx:any)
local folder:Folder=ctx.folder
local random:Random=ctx.random
local DENSITY:number=ctx.DENSITY
local fx:{flash:number,shake:number,pulse:number}=ctx.fx
local kit=ctx.kit
local seq,tex,rateOf,burstEmitter,groundAt,worldAttachment=kit.seq,kit.tex,kit.rateOf,kit.burstEmitter,kit.groundAt,kit.worldAttachment
local c3,PARKED,TEX_SMOKE,TEX_SPARK,TEX_FIRE=kit.c3,kit.PARKED,kit.TEX_SMOKE,kit.TEX_SPARK,kit.TEX_FIRE

-- lightning bolts: WeatherLooks.Budget.bolts slots, each 10 trunk attachments, 2 glow layers per segment and 2 forks
type BoltSlot={points:{Attachment},ends:{Attachment},beams:{Beam},forks:{Beam},trunk:Beam?,active:boolean,age:number,flickered:boolean}
local bolts:{BoltSlot}={}
-- BD-131: with a lightningBolt texture each bolt is ONE textured trunk beam (the strip tiles along it) plus the 2 forks, instead of 18 segment beams
local BOLT_TRUNK=WT.plan(Assets,"lightningBolt","trunk")
local BOLT_FORK=WT.plan(Assets,"lightningBolt","fork")
local function textureBeam(beam:Beam,plan:WT.Plan,width0:number,width1:number)
    local tune=plan.tune
    beam.Texture,beam.TextureMode,beam.TextureLength,beam.TextureSpeed=plan.texture,Enum.TextureMode.Wrap,tune.width*tune.tile,0
    beam.Width0,beam.Width1=width0,width1
    beam.Color=ColorSequence.new(c3(tune.color)) beam.Transparency=NumberSequence.new(tune.transparency) beam.LightEmission=tune.lightEmission
end
for _=1,WL.Budget.bolts do
    local points:{Attachment}={} local ends:{Attachment}={} local beams:{Beam}={} local forks:{Beam}={}
    for i=1,10 do points[i]=worldAttachment() end
    for i=1,2 do ends[i]=worldAttachment() end
    for i=2,(if BOLT_TRUNK then 1 else 10) do
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
        if BOLT_FORK then textureBeam(fork,BOLT_FORK,BOLT_FORK.tune.width,BOLT_FORK.tune.width*.4) end
        table.insert(forks,fork)
    end
    local trunk:Beam?=nil
    if BOLT_TRUNK then
        local beam=Instance.new("Beam") beam.Attachment0,beam.Attachment1=points[1],points[10]
        beam.FaceCamera,beam.LightInfluence,beam.Segments=true,0,BOLT_TRUNK.tune.segments
        textureBeam(beam,BOLT_TRUNK,BOLT_TRUNK.tune.width,BOLT_TRUNK.tune.width*.8)
        beam.Enabled=false beam.Parent=folder trunk=beam
    end
    table.insert(bolts,{points=points,ends=ends,beams=beams,forks=forks,trunk=trunk,active=false,age=0,flickered=false})
end
local function setBolt(slot:BoltSlot,on:boolean)
    for _,b in slot.beams do b.Enabled=on end
    for _,b in slot.forks do b.Enabled=on end
    if slot.trunk then slot.trunk.Enabled=on end
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
    if slot.trunk and BOLT_TRUNK then
        local curve=BOLT_TRUNK.tune.curve
        slot.trunk.CurveSize0,slot.trunk.CurveSize1=random:NextNumber(-curve,curve),random:NextNumber(-curve,curve)
    end
    slot.active,slot.age,slot.flickered=true,0,false setBolt(slot,true)
    WS.fire("strike")
    fx.flash=math.max(fx.flash,.8) fx.shake=math.max(fx.shake,if dist<120 then .7 else .45)
    return true
end
local function updateBolts(dt:number)
    for _,slot in bolts do
        if slot.active then
            slot.age+=dt
            if slot.age>.09 and slot.age<.17 then setBolt(slot,false)
            elseif slot.age>=.17 and slot.age<=.5 then
                setBolt(slot,true)
                if not slot.flickered then slot.flickered=true fx.flash=math.max(fx.flash,.55) end
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
local SPARK_SCALE=rateOf("emberSpark","sparks") -- 1 while the emberSpark slot is empty (same emit counts as before)
for _=1,WL.Budget.bombs do
    local holder=Instance.new("Part") holder.Name="LavaImpact" holder.Size,holder.Transparency=Vector3.one,1
    holder.Anchored,holder.CanCollide,holder.CanTouch,holder.CanQuery=true,false,false,false holder.Position=PARKED holder.Parent=folder
    local sparks=burstEmitter(holder,tex("emberSpark","sparks",{Texture=TEX_SPARK,Lifetime=NumberRange.new(.8,1.6),Speed=NumberRange.new(30,75),EmissionDirection=Enum.NormalId.Top,
        Acceleration=Vector3.new(0,-70,0),Size=seq(1.5,.9,0),Transparency=seq(0,0,1),LightEmission=1,SpreadAngle=Vector2.new(70,70),
        Color=ColorSequence.new(Color3.fromRGB(255,225,110),Color3.fromRGB(255,90,20))}))
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
            slot.sparks.e:Emit(math.floor((if strong then 70 else 40)*SPARK_SCALE+.5)) slot.puffs.e:Emit(if strong then 16 else 9) slot.smoke.e:Emit(7)
            slot.light.Brightness=8
            ring(position,Color3.fromRGB(255,150,60),if strong then 52 else 32,.7)
            fx.pulse=math.max(fx.pulse,.35)
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
                if near<60 then fx.shake=math.max(fx.shake,.8*(1-near/70)+.2) end
            end
        end
    end
end
local function stopOneShots()
    for _,slot in bolts do slot.active=false setBolt(slot,false) end
    for _,slot in bombSlots do slot.active=false slot.trail.Enabled=false slot.tail.e.Enabled=false slot.glow.Brightness=0 slot.part.Position=PARKED end
end
return {bolt=bolt,lavaBomb=lavaBomb,updateBolts=updateBolts,updateRings=updateRings,updateBursts=updateBursts,updateBombs=updateBombs,stopOneShots=stopOneShots}
end
