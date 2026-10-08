-- Standalone client adapter. Upload BeDino_Soft_Smoke_256.png first.
-- Caller owns player-distance selection and calls Destroy on unequip/despawn.
local RunService = game:GetService("RunService")
local Effects = {}
local activeCount = 0
local colors = {
 dewdrop = {Color3.fromRGB(43,154,111),Color3.fromRGB(112,244,191)},
 charged = {Color3.fromRGB(56,66,87),Color3.fromRGB(255,207,72)},
 frost = {Color3.fromRGB(112,184,211),Color3.fromRGB(175,235,255)},
 seismic = {Color3.fromRGB(133,97,62),Color3.fromRGB(210,173,113)},
 ember = {Color3.fromRGB(99,54,34),Color3.fromRGB(255,144,51)},
 aurora = {Color3.fromRGB(109,65,150),Color3.fromRGB(81,233,187)},
 bloodmoon = {Color3.fromRGB(122,26,46),Color3.fromRGB(250,67,102)},
}
local function anchor(parent)
 local p=Instance.new("Part");p.Name="MutationFXAnchor";p.Size=Vector3.new(.1,.1,.1)
 p.Transparency=1;p.Anchored=true;p.CanCollide=false;p.CanTouch=false;p.CanQuery=false;p.CastShadow=false;p.Parent=parent
 return p
end
function Effects.Create(model: Model, mutationId: string, smokeTexture: string, reducedEffects: boolean?)
 local palette=colors[mutationId]
 if not palette or not model.Parent or reducedEffects or activeCount>=8 then return nil end
 assert(type(smokeTexture)=="string" and smokeTexture:match("^rbxassetid://%d+$"),"Supply uploaded BeDino smoke texture asset ID")
 local folder=Instance.new("Folder");folder.Name="BeDinoMutation_"..mutationId;folder.Parent=workspace
 local center=anchor(folder);local attachments={};local beams={};local particles={};local fragments={}
 for i=1,4 do
  local a=Instance.new("Attachment");a.Parent=center;local b=Instance.new("Attachment");b.Parent=center
  local beam=Instance.new("Beam");beam.Attachment0=a;beam.Attachment1=b;beam.FaceCamera=true;beam.Segments=8
  beam.Color=ColorSequence.new(mutationId=="aurora" and ({Color3.fromRGB(81,233,187),Color3.fromRGB(101,176,255),Color3.fromRGB(189,104,240),palette[2]})[i] or palette[2])
  beam.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.25,.55),NumberSequenceKeypoint.new(.7,.6),NumberSequenceKeypoint.new(1,1)})
  beam.LightEmission=.55;beam.Parent=center;table.insert(attachments,{a,b});table.insert(beams,beam)
  local emit=Instance.new("ParticleEmitter");emit.Name="SoftMist";emit.Texture=smokeTexture
  emit.Color=ColorSequence.new(palette[1]);emit.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.25,.55),NumberSequenceKeypoint.new(.7,.72),NumberSequenceKeypoint.new(1,1)})
  emit.Lifetime=NumberRange.new(.7,1.2);emit.Rate=4;emit.Speed=NumberRange.new(.25,.6);emit.SpreadAngle=Vector2.new(25,25)
  emit.Rotation=NumberRange.new(-180,180);emit.RotSpeed=NumberRange.new(-20,20);emit.LightEmission=.12;emit.LockedToPart=false;emit.Parent=a;table.insert(particles,emit)
 end
 for i=1,(mutationId=="bloodmoon" and 1 or 4) do
  local p=Instance.new("Part");p.Name="ElementalDetail";p.Anchored=true;p.CanCollide=false;p.CanTouch=false;p.CanQuery=false;p.CastShadow=false
  p.Color=palette[2];p.Material=Enum.Material.SmoothPlastic
  if mutationId=="dewdrop" or mutationId=="bloodmoon" then p.Shape=Enum.PartType.Ball end
  if mutationId=="ember" then p.Color=Color3.fromRGB(65,43,32) end
  if mutationId=="charged" then p.Material=Enum.Material.Neon end
  p.Parent=folder;table.insert(fragments,p)
 end
 activeCount+=1
 local alive=true;local elapsed=0;local accumulator=0;local connection;local lastHeight=0
 local function destroy()
  if not alive then return end;alive=false;activeCount-=1
  if connection then connection:Disconnect() end;folder:Destroy()
 end
 local function update(dt)
  if not model.Parent then destroy();return end
  elapsed+=dt;accumulator+=dt;if accumulator<1/30 then return end;accumulator=0
  -- GetBoundingBox only reads the dinosaur; the FX folder is outside its bounds.
  local cf,size=model:GetBoundingBox();local rx=math.max(.8,size.X*.6);local ry=math.max(.8,size.Z*.6);local h=math.max(1,size.Y)
  center.CFrame=cf*CFrame.new(0,-size.Y*.5+.1,0)
  local resized=math.abs(h-lastHeight)>.02
  for i,pair in attachments do
   local angle=(i-1)*math.pi*.5+elapsed*.65
   local start=Vector3.new(math.cos(angle)*rx,.12*h,math.sin(angle)*ry)
   local finish=Vector3.new(math.cos(angle+2.1)*rx,.85*h,math.sin(angle+2.1)*ry)
   pair[1].CFrame=CFrame.new(start)*CFrame.Angles(0,-angle,math.pi*.5)
   pair[2].CFrame=CFrame.new(finish)*CFrame.Angles(0,-angle-2.1,math.pi*.5)
   if resized then beams[i].Width0=math.clamp(h*.065,.05,.28);beams[i].Width1=.01 end
   beams[i].CurveSize0=math.max(rx,ry)*.7;beams[i].CurveSize1=-math.max(rx,ry)*.55
   if resized then
    local s=math.clamp(h*.28,.25,1.25)
    particles[i].Size=NumberSequence.new({NumberSequenceKeypoint.new(0,s*.45),NumberSequenceKeypoint.new(.6,s),NumberSequenceKeypoint.new(1,s*1.3)})
   end
  end
  lastHeight=h
  for i,p in fragments do
   local a=i*math.pi*.5+elapsed*.45;local scale=math.clamp(h*.045,.06,.22)
   p.Size=mutationId=="bloodmoon" and Vector3.one*scale*2.5 or Vector3.new(scale,scale*(mutationId=="frost" and 2 or 1),scale)
   if mutationId=="charged" then p.Size=Vector3.new(scale*.22,scale*3,scale*.22) end
   local pos=mutationId=="bloodmoon" and Vector3.new(rx*.7,h,ry*.5) or Vector3.new(math.cos(a)*rx,(.25+i*.12)*h+math.sin(elapsed*1.2+i)*h*.035,math.sin(a)*ry)
   p.CFrame=center.CFrame*CFrame.new(pos)*CFrame.Angles(elapsed*.3,i,elapsed*.2)
  end
 end
 update(1/30);connection=RunService.Heartbeat:Connect(update)
 return {Destroy=destroy, SetReducedEffects=function(value: boolean) if value then destroy() end end}
end
return Effects
