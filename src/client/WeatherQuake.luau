--!strict
-- Weather earthquake (BD-627, docs/153): pooled ground cracks, bouncing rocks, prop wobble, feet dust and the crack decal, moved unchanged out of
-- WeatherVisuals.client.luau. The main loop calls pulse (a tremor), update (every frame) and stop.
local Shared=game:GetService("ReplicatedStorage").Shared
local WL=require(Shared.WeatherLooks)
local WS=require(Shared.WeatherSounds)
type Emitter={e:ParticleEmitter,rate:number,fixed:boolean}
return function(ctx:any)
local folder:Folder=ctx.folder
local player:Player=ctx.player
local random:Random=ctx.random
local phone:boolean=ctx.phone
local kit=ctx.kit
local seq,tex,volume,burstEmitter=kit.seq,kit.tex,kit.volume,kit.burstEmitter
local rayParams,PARKED,DUST_FX=kit.rayParams,kit.PARKED,kit.DUST_FX

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
    local dust=burstEmitter(holder,tex("dustSand","crackDust",{Texture=DUST_FX.Texture,FlipbookLayout=DUST_FX.FlipbookLayout,FlipbookMode=DUST_FX.FlipbookMode,Lifetime=NumberRange.new(1.6,2.4),Speed=NumberRange.new(3,8),EmissionDirection=Enum.NormalId.Top,
        SpreadAngle=Vector2.new(35,35),Size=seq(4,9,12),Transparency=seq(.55,.72,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-20,20),Drag=1.5,
        Acceleration=Vector3.new(0,1,0),Color=ColorSequence.new(Color3.fromRGB(196,172,136),Color3.fromRGB(160,138,108))}))
    table.insert(cracks,{segs=segs,holder=holder,dust=dust,active=false,age=0,life=4,static=false})
    for _=1,WL.Budget.rocksPerCrack do
        local rockPart=Instance.new("Part") rockPart.Shape=Enum.PartType.Ball
        table.insert(rocks,{part=quakePart(rockPart,"QuakeRock",Color3.fromRGB(104,88,74),Enum.Material.Slate),active=false,age=0,v=Vector3.zero,floor=0,bounces=0})
    end
end
-- BD-348: dust puff at the dino's feet and a flat crack decal a few studs ahead (fx3 "rays" alpha texture, tinted dark brown)
local feetHolder=volume(Vector3.new(3,.4,3)) feetHolder.Name="QuakeFeetDust" feetHolder.Position=PARKED
local feetPuff=burstEmitter(feetHolder,tex("dustSand","feetPuff",{Texture=DUST_FX.Texture,FlipbookLayout=DUST_FX.FlipbookLayout,FlipbookMode=DUST_FX.FlipbookMode,Lifetime=NumberRange.new(1.2,1.8),Speed=NumberRange.new(2,5),
    EmissionDirection=Enum.NormalId.Top,SpreadAngle=Vector2.new(60,60),Size=seq(2,4,5),Transparency=seq(.5,.7,1),Rotation=NumberRange.new(0,360),RotSpeed=NumberRange.new(-20,20),Drag=1.5,
    Acceleration=Vector3.new(0,1,0),Color=ColorSequence.new(Color3.fromRGB(205,180,140),Color3.fromRGB(165,142,110))}))
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
return {pulse=quakePulse,update=updateQuake,stop=stopQuake}
end
