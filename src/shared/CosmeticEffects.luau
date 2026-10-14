--!strict
-- Cosmetic-only geometry. Server-published equipment selects bounded client-local effects.
-- v1 = thin beam/strip effects (Build 020). v2 = Mythic Glow (BD-110/111, docs/81), used only when
-- every EffectAssets texture has an uploaded ID; layers come from the pure AuraTrailStyle plan.
local Style=require(script.Parent.AuraTrailStyle)
local Assets=require(script.Parent.EffectAssets)
local Effects={}
local function color(rgb) return Color3.fromRGB(rgb[1],rgb[2],rgb[3]) end
local function createV1(root: BasePart,aura,trail,mutation,shiny: boolean?)
    local state={objects={},orbits={},emitters={},beams={},trails={},walkingEmitters={}}
    local function make(class,name)
        local object=Instance.new(class)
        object.Name,object.Parent=name,root
        table.insert(state.objects,object)
        return object
    end
    local function particles(name,primary,accent,rate,walking)
        local attachment=make("Attachment",name.."Anchor")
        attachment.Position=Vector3.new(0,-.8,1.3)
        local emitter=Instance.new("ParticleEmitter")
        emitter.Name,emitter.Parent=name,attachment
        emitter.Texture="rbxasset://textures/particles/sparkles_main.dds"
        emitter.Color=ColorSequence.new(primary,accent)
        emitter.Rate,emitter.LightEmission=rate,1
        emitter.Lifetime,emitter.Speed=NumberRange.new(.5,1),NumberRange.new(.2,.8)
        emitter.SpreadAngle=Vector2.new(180,180)
        emitter.Size=NumberSequence.new({NumberSequenceKeypoint.new(0,.15),NumberSequenceKeypoint.new(.3,.22),NumberSequenceKeypoint.new(1,0)})
        emitter.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,.1),NumberSequenceKeypoint.new(1,1)})
        table.insert(if walking then state.walkingEmitters else state.emitters,emitter)
    end
    if shiny then particles("LocalShinySparkles",Color3.fromRGB(255,239,142),Color3.new(1,1,1),8,false) end
    if not aura and mutation then aura={id="event",color=mutation.color} end
    if mutation then
        local attachment=make("Attachment","LocalMutationGlow")
        local light=Instance.new("PointLight")
        light.Color,light.Brightness,light.Range,light.Shadows,light.Parent=color(mutation.color),.65,7,false,attachment
        table.insert(state.emitters,light)
    end
    if aura then
        local primary=color(aura.color)
        local accent=if aura.id=="royal" then Color3.fromRGB(255,215,115) else primary:Lerp(Color3.new(1,1,1),.65)
        for ring=1,2 do
            local points={}
            for i=1,4 do
                local attachment=make("Attachment","LocalAuraOrbit")
                table.insert(points,attachment)
                table.insert(state.orbits,{attachment=attachment,angle=(i-1)*math.pi/2,ring=ring})
            end
            for i=1,4 do
                local beam=make("Beam","LocalAuraRibbon")
                beam.Attachment0,beam.Attachment1=points[i],points[i%4+1]
                beam.Color=ColorSequence.new(primary,accent)
                beam.Transparency=NumberSequence.new(if ring==1 then .22 else .65)
                beam.LightEmission,beam.FaceCamera,beam.Segments=1,true,12
                table.insert(state.beams,{beam=beam,ring=ring})
            end
        end
        local center=make("Attachment","LocalAuraMotes")
        local emitter=Instance.new("ParticleEmitter")
        emitter.Name,emitter.Parent="LocalAuraParticles",center
        emitter.Texture="rbxasset://textures/particles/sparkles_main.dds"
        emitter.Color=ColorSequence.new(primary,accent)
        emitter.LightEmission,emitter.Rate= .85,if aura.id=="royal" then 12 else 8
        emitter.Lifetime,emitter.Speed=NumberRange.new(.8,1.3),NumberRange.new(.4,1.2)
        emitter.SpreadAngle=Vector2.new(180,180)
        emitter.Size=NumberSequence.new({NumberSequenceKeypoint.new(0,.08),NumberSequenceKeypoint.new(.4,.2),NumberSequenceKeypoint.new(1,0)})
        emitter.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.2,.2),NumberSequenceKeypoint.new(1,1)})
        table.insert(state.emitters,emitter)
    end
    if trail then
        local primary,accent=color(trail.color),color(trail.accent)
        if trail.particles then particles("LocalTrailGlitter",primary,accent,trail.particles,true) end
        for side=-1,1,2 do
            local a=make("Attachment","LocalTrailEdge")
            local b=make("Attachment","LocalTrailEdge")
            local ribbon=make("Trail","LocalCosmeticTrail")
            ribbon.Attachment0,ribbon.Attachment1=a,b
            ribbon.Color=ColorSequence.new(primary,accent)
            ribbon.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,.12),NumberSequenceKeypoint.new(.7,.55),NumberSequenceKeypoint.new(1,1)})
            ribbon.WidthScale=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(1,0)})
            ribbon.Lifetime,ribbon.MinLength,ribbon.FaceCamera,ribbon.LightEmission=trail.lifetime,.12,true,.8
            table.insert(state.trails,{ribbon=ribbon,a=a,b=b,side=side,width=trail.width})
        end
    end
    function state:update(scale: number,time: number,enabled: boolean)
        for _,orbit in self.orbits do
            local angle=orbit.angle+time*(if orbit.ring==1 then .45 else -.3)
            local radius=(if orbit.ring==1 then 2.1 else 1.6)*scale
            local position=Vector3.new(math.cos(angle)*radius,(if orbit.ring==1 then -1.65 else -.7)*scale,math.sin(angle)*radius)
            local tangent=Vector3.new(-math.sin(angle),0,math.cos(angle))
            orbit.attachment.CFrame=CFrame.fromMatrix(position,tangent,Vector3.yAxis,tangent:Cross(Vector3.yAxis))
        end
        for _,entry in self.beams do
            entry.beam.Enabled=enabled
            local radius=(if entry.ring==1 then 2.1 else 1.6)*scale
            entry.beam.CurveSize0,entry.beam.CurveSize1=.5523*radius,.5523*radius
            entry.beam.Width0,entry.beam.Width1=.1*scale,.1*scale
        end
        for _,emitter in self.emitters do emitter.Enabled=enabled end
        local walking=enabled and Vector3.new(root.AssemblyLinearVelocity.X,0,root.AssemblyLinearVelocity.Z).Magnitude>1
        for _,emitter in self.walkingEmitters do emitter.Enabled=walking end
        for _,entry in self.trails do
            entry.a.Position=Vector3.new(entry.side*1.1,-.6,1.3)*scale
            entry.b.Position=entry.a.Position+Vector3.new(0,-entry.width*scale,0)
            if not enabled and entry.ribbon.Enabled then entry.ribbon:Clear() end
            entry.ribbon.Enabled=walking
        end
    end
    function state:destroy() for _,object in self.objects do object:Destroy() end end
    return state
end

local NAVY=Color3.fromRGB(20,32,53)
local function rainbow(): ColorSequence
    local keys={}
    for i=0,6 do table.insert(keys,ColorSequenceKeypoint.new(i/6,Color3.fromHSV(i/6*.9,.6,1))) end
    return ColorSequence.new(keys)
end
local function fade(a: number,b: number): NumberSequence
    return NumberSequence.new({NumberSequenceKeypoint.new(0,a),NumberSequenceKeypoint.new(1,b)})
end
local function localFolder(): Instance
    local folder=workspace:FindFirstChild("LocalCosmetics")
    if not folder then
        folder=Instance.new("Folder")
        folder.Name,folder.Parent="LocalCosmetics",workspace
    end
    return folder
end

local function createV2(root: BasePart,aura,trail,quality: string)
    local state={objects={},discs={},comets={},pillars={},halos={},emitters={},walkingEmitters={},trails={}}
    local layers=Style.plan(aura,trail,quality)
    local auraColor=if aura then color(aura.color) else Color3.new(1,1,1)
    local auraAccent=if aura and aura.id=="royal" then Color3.fromRGB(255,215,115) else auraColor:Lerp(Color3.new(1,1,1),.6)
    local trailColor=if trail then color(trail.color) else auraColor
    local trailAccent=if trail and trail.accent then color(trail.accent) else trailColor:Lerp(Color3.new(1,1,1),.6)
    local function make(class: string,name: string,parent: Instance?): Instance
        local object=Instance.new(class)
        object.Name,object.Parent=name,parent or root
        table.insert(state.objects,object)
        return object
    end
    for _,layer in layers do
        local texture=Assets[layer.texture]
        if layer.kind=="disc" then
            local disc=make("Part","LocalAuraSigil",localFolder()) :: Part
            disc.Anchored,disc.CanCollide,disc.CanQuery,disc.CanTouch,disc.CastShadow=true,false,false,false,false
            disc.Transparency,disc.Size=1,Vector3.new(1,.05,1)
            if layer.under then -- navy under-glow so the light sigil reads on bright grass
                local shadow=Instance.new("Decal")
                shadow.Face,shadow.Texture,shadow.Color3,shadow.Transparency,shadow.Parent=Enum.NormalId.Top,Assets["glow-dot"],NAVY,.45,disc
            end
            local decal=Instance.new("Decal")
            decal.Face,decal.Texture,decal.Color3,decal.Transparency,decal.Parent=Enum.NormalId.Top,texture,if layer.under then auraColor else auraAccent,.1,disc
            table.insert(state.discs,{part=disc,layer=layer})
        elseif layer.kind=="emitter" then
            local anchor=make("Attachment","LocalEffectAnchor") :: Attachment
            local emitter=Instance.new("ParticleEmitter")
            emitter.Name,emitter.Texture,emitter.Parent="LocalEffect_"..layer.role,texture,anchor
            local primary,accent=if layer.walking then trailColor else auraColor,if layer.walking then trailAccent else auraAccent
            emitter.Color=if layer.walking and trail and Style.trailClass(trail)>=6 then rainbow() else ColorSequence.new(primary,accent)
            emitter.LightEmission,emitter.LightInfluence,emitter.Rate=1,0,layer.rate
            emitter.Lifetime=NumberRange.new(.9,1.5)
            emitter.Speed=NumberRange.new((layer.rise or .3)*.6,layer.rise or .3)
            emitter.EmissionDirection,emitter.SpreadAngle=Enum.NormalId.Top,Vector2.new(if layer.walking then 60 else 35,if layer.walking then 60 else 35)
            emitter.Size=NumberSequence.new({NumberSequenceKeypoint.new(0,0),NumberSequenceKeypoint.new(.25,layer.size),NumberSequenceKeypoint.new(1,layer.size*.6)})
            emitter.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.2,.1),NumberSequenceKeypoint.new(1,1)})
            if layer.flipbook then
                emitter.FlipbookLayout=Enum.ParticleFlipbookLayout.Grid4x4
                emitter.FlipbookMode=if layer.flipbook=="Random" then Enum.ParticleFlipbookMode.Random else Enum.ParticleFlipbookMode.OneShot
            end
            table.insert(if layer.walking then state.walkingEmitters else state.emitters,{emitter=emitter,anchor=anchor,layer=layer})
        elseif layer.kind=="comets" then
            for i=1,layer.count do
                local head=make("Attachment","LocalCometHead") :: Attachment
                local tail=make("Attachment","LocalCometTail") :: Attachment
                local beam=make("Beam","LocalComet") :: Beam
                beam.Attachment0,beam.Attachment1,beam.Texture=head,tail,texture
                beam.TextureMode,beam.TextureLength,beam.TextureSpeed=Enum.TextureMode.Stretch,1,1.5
                beam.Color=ColorSequence.new(auraAccent,auraColor)
                beam.Transparency=fade(0,1)
                beam.LightEmission,beam.LightInfluence,beam.FaceCamera,beam.Segments=1,0,true,10
                table.insert(state.comets,{head=head,tail=tail,beam=beam,phase=(i-1)/layer.count,dir=if i%2==1 then 1 else -1,lift=(i-1)*.35})
            end
        elseif layer.kind=="pillar" then
            local bottom=make("Attachment","LocalPillarBottom") :: Attachment
            local top=make("Attachment","LocalPillarTop") :: Attachment
            local beam=make("Beam","LocalAuraPillar") :: Beam
            beam.Attachment0,beam.Attachment1,beam.Texture=bottom,top,texture
            beam.TextureMode,beam.TextureLength=Enum.TextureMode.Stretch,1
            beam.Color=ColorSequence.new(auraAccent,auraColor)
            beam.LightEmission,beam.LightInfluence,beam.FaceCamera=1,0,true
            table.insert(state.pillars,{bottom=bottom,top=top,beam=beam,width=layer.width})
        elseif layer.kind=="halo" then
            local anchor=make("Attachment","LocalHaloAnchor") :: Attachment
            local gui=Instance.new("BillboardGui")
            gui.Name,gui.Adornee,gui.LightInfluence,gui.MaxDistance,gui.Parent="LocalHalo",anchor,0,80,anchor
            local image=Instance.new("ImageLabel")
            image.BackgroundTransparency,image.Image,image.ImageColor3,image.Size,image.Parent=1,texture,auraAccent,UDim2.fromScale(1,1),gui
            table.insert(state.halos,{anchor=anchor,gui=gui,image=image,size=layer.size})
        elseif layer.kind=="trail" then
            local a=make("Attachment","LocalTrailTop") :: Attachment
            local b=make("Attachment","LocalTrailBottom") :: Attachment
            local ribbon=make("Trail","LocalCosmeticTrail") :: Trail
            ribbon.Attachment0,ribbon.Attachment1,ribbon.Texture=a,b,texture
            ribbon.TextureMode,ribbon.TextureLength=Enum.TextureMode.Wrap,4
            ribbon.FaceCamera,ribbon.MinLength=true,.12
            ribbon.Lifetime=if trail and trail.lifetime then trail.lifetime*1.2 else 1
            ribbon.WidthScale=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(1,.15)})
            if layer.role=="under" then
                ribbon.Color,ribbon.LightEmission,ribbon.Transparency=ColorSequence.new(NAVY),0,fade(.5,1)
            else
                ribbon.Color=if layer.rainbow then rainbow() elseif layer.role=="main" then ColorSequence.new(trailAccent,trailColor) else ColorSequence.new(trailColor,trailAccent)
                ribbon.LightEmission,ribbon.LightInfluence,ribbon.Transparency=1,0,fade(if layer.role=="main" then 0 else .2,1)
            end
            local class=Style.trailClass(trail)
            table.insert(state.trails,{ribbon=ribbon,a=a,b=b,layer=layer,width=(.55+.12*class)*layer.widthScale})
        end
    end
    function state:update(scale: number,time: number,enabled: boolean)
        local base=root.Position
        for _,entry in self.discs do
            local r=entry.layer.radius*scale
            entry.part.Size=Vector3.new(2*r,.05,2*r)
            entry.part.CFrame=CFrame.new(base+Vector3.new(0,entry.layer.height*scale,0))*CFrame.Angles(0,if enabled then time*entry.layer.spin else 0,0)
            for _,decal in entry.part:GetChildren() do if decal:IsA("Decal") then decal.Transparency=if enabled then (if decal.Color3==NAVY then .45 else .1) else 1 end end
        end
        for _,entry in self.comets do
            local radius,height=2.3*scale,(-.2+entry.lift)*scale
            local headAngle=entry.dir*time*1.4+entry.phase*math.pi*2
            local tailAngle=headAngle-entry.dir*1.1
            for _,pair in {{entry.head,headAngle},{entry.tail,tailAngle}} do
                local angle=pair[2]
                local position=Vector3.new(math.cos(angle)*radius,height+math.sin(angle*2)*.25*scale,math.sin(angle)*radius)
                local tangent=Vector3.new(-math.sin(angle),0,math.cos(angle))*entry.dir
                pair[1].CFrame=CFrame.fromMatrix(position,tangent,Vector3.yAxis,tangent:Cross(Vector3.yAxis))
            end
            entry.beam.CurveSize0,entry.beam.CurveSize1=-.55*radius,.55*radius
            entry.beam.Width0,entry.beam.Width1=.45*scale,.05*scale
            entry.beam.Enabled=enabled
        end
        for _,entry in self.pillars do
            entry.bottom.Position,entry.top.Position=Vector3.new(0,-1.8*scale,0),Vector3.new(0,3.2*scale,0)
            local pulse=.25+.15*math.sin(time*3)
            entry.beam.Width0,entry.beam.Width1=entry.width*scale,entry.width*scale*.7
            entry.beam.Transparency=fade(pulse,1)
            entry.beam.Enabled=enabled
        end
        for _,entry in self.halos do
            entry.anchor.Position=Vector3.new(0,2.6*scale,0)
            entry.gui.Size=UDim2.fromScale(entry.size*scale,entry.size*scale*.32)
            entry.image.ImageTransparency=if enabled then .1+.15*math.sin(time*2) else 1
        end
        for _,entry in self.emitters do
            entry.anchor.Position=Vector3.new(0,(if entry.layer.role=="runes" then -1.5 else -1)*scale,0)
            entry.emitter.Enabled=enabled
        end
        local walking=enabled and Vector3.new(root.AssemblyLinearVelocity.X,0,root.AssemblyLinearVelocity.Z).Magnitude>1
        for _,entry in self.walkingEmitters do
            entry.anchor.Position=Vector3.new(0,-.6*scale,1.4*scale)
            entry.emitter.Enabled=walking
        end
        for _,entry in self.trails do
            local offset=entry.layer.offset or 0
            local wobble=if offset~=0 then math.sin(time*4+offset*9)*offset else 0
            local center=Vector3.new(wobble,-.55,1.4)*scale
            local half=entry.width*scale/2
            entry.a.Position,entry.b.Position=center+Vector3.new(0,half,0),center-Vector3.new(0,half,0)
            if not enabled and entry.ribbon.Enabled then entry.ribbon:Clear() end
            entry.ribbon.Enabled=walking
        end
    end
    function state:destroy() for _,object in self.objects do object:Destroy() end end
    return state
end

-- quality: "full" | "lite" | "off" (AuraTrailStyle.quality). v1 has no lite mode: it shows as before.
function Effects.create(root: BasePart,aura,trail,mutation,shiny: boolean?,quality: string?)
    if Style.ready(Assets) and not mutation and not shiny then return createV2(root,aura,trail,quality or "full") end
    if quality=="off" then return createV1(root,nil,nil,nil,false) end
    return createV1(root,aura,trail,mutation,shiny)
end
Effects.v2Ready=function(): boolean return Style.ready(Assets) end
return Effects
