--!strict
-- Weather particle kit (BD-627, docs/153): the helpers every weather part shares, moved unchanged out of WeatherVisuals.client.luau.
-- texture reader (BD-131), volume parts, emitter builders, ground ray. Built once by WeatherVisuals with its context table.
local Shared=game:GetService("ReplicatedStorage").Shared
local WL=require(Shared.WeatherLooks)
type Emitter={e:ParticleEmitter,rate:number,fixed:boolean}
return function(ctx:any)
local folder:Folder=ctx.folder
local player:Player=ctx.player
local DENSITY:number=ctx.DENSITY
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
local function c3(c:{number}):Color3 return Color3.fromRGB(c[1],c[2],c[3]) end

-- ---------------------------------------------------------------- particle helpers
local function seq(a:number,b:number,c:number?):NumberSequence
    if c then return NumberSequence.new({NumberSequenceKeypoint.new(0,a),NumberSequenceKeypoint.new(.5,b),NumberSequenceKeypoint.new(1,c)}) end
    return NumberSequence.new(a,b)
end
-- BD-131 texture reader. tex() returns props untouched while the slot is empty; otherwise it adds the texture, the flipbook layout / mode
-- and the per-texture tuning (WeatherTextures.Tuning). rateOf() is the matching rate multiplier (1 while empty).
local Assets=require(Shared.EffectAssets)
local WT=require(Shared.WeatherTextures)
local function scaleSeq(s:NumberSequence,k:number):NumberSequence
    local points:{NumberSequenceKeypoint}={}
    for i,kp in s.Keypoints do points[i]=NumberSequenceKeypoint.new(kp.Time,kp.Value*k,kp.Envelope*k) end
    return NumberSequence.new(points)
end
local function tex(key:string,rigName:string,props:{[string]:any}):{[string]:any}
    local plan=WT.plan(Assets,key,rigName)
    if not plan then return props end
    local tune=plan.tune
    props.Texture=plan.texture
    props.FlipbookLayout=(Enum.ParticleFlipbookLayout::any)[plan.layout]
    if plan.mode then
        props.FlipbookMode=(Enum.ParticleFlipbookMode::any)[plan.mode]
        props.FlipbookStartRandom=plan.startRandom
        if plan.framerate then props.FlipbookFramerate=NumberRange.new(plan.framerate) end
    end
    if tune.sizeScale and props.Size then props.Size=scaleSeq(props.Size,tune.sizeScale) end
    if tune.size then props.Size=seq(tune.size[1],tune.size[2],tune.size[3]) end
    if tune.squash then props.Squash=seq(tune.squash[1],tune.squash[2]) end
    if tune.transparency then props.Transparency=seq(tune.transparency[1],tune.transparency[2],tune.transparency[3]) end
    if tune.lightEmission then props.LightEmission=tune.lightEmission end
    return props
end
local function rateOf(key:string,rigName:string):number return WT.rate(WT.plan(Assets,key,rigName)) end
local function volume(size:Vector3):Part
    local part=Instance.new("Part") part.Name="WeatherVolume" part.Size,part.Transparency=size,1
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Parent=folder return part
end
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
local function burstEmitter(parent:Part,props:{[string]:any}):Emitter
    local e=Instance.new("ParticleEmitter") e.Name="WeatherParticles" e.Rate,e.Enabled,e.LockedToPart,e.LightInfluence=0,false,false,0
    local any:any=e for key,value in props do any[key]=value end e.Parent=parent
    return {e=e,rate=0,fixed=true}
end
return {c3=c3,seq=seq,tex=tex,rateOf=rateOf,volume=volume,emitter=emitter,burstEmitter=burstEmitter,groundAt=groundAt,worldAttachment=worldAttachment,
    rayParams=rayParams,PARKED=PARKED,Assets=Assets,WT=WT,DUST_FX=DUST_FX,TEX_SMOKE=TEX_SMOKE,TEX_SPARK=TEX_SPARK,TEX_FIRE=TEX_FIRE}
end
