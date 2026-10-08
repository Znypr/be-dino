--!strict
-- Cosmetic-only geometry. Server-published equipment selects bounded client-local effects.
local Effects={}
local function color(rgb) return Color3.fromRGB(rgb[1],rgb[2],rgb[3]) end
function Effects.create(root: BasePart,aura,trail,mutation)
    local state={objects={},orbits={},emitters={},beams={},trails={}}
    local function make(class,name)
        local object=Instance.new(class)
        object.Name,object.Parent=name,root
        table.insert(state.objects,object)
        return object
    end
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
        for _,entry in self.trails do
            entry.a.Position=Vector3.new(entry.side*1.1,-.6,1.3)*scale
            entry.b.Position=entry.a.Position+Vector3.new(0,-entry.width*scale,0)
            if not enabled and entry.ribbon.Enabled then entry.ribbon:Clear() end
            entry.ribbon.Enabled=enabled
        end
    end
    function state:destroy() for _,object in self.objects do object:Destroy() end end
    return state
end
return Effects
