-- Cosmetic-only Shiny adapter. BIG scaling remains owned by Dinosaur/Config.
local Effects = {}
local active = 0
function Effects.Create(model: Model, textureId: string, reducedEffects: boolean?)
 if reducedEffects or active>=8 or not model.Parent then return nil end
 assert(textureId:match("^rbxassetid://%d+$"),"Supply uploaded BeDino_Shiny_Glint_256.png asset ID")
 local root=model.PrimaryPart or model:FindFirstChildWhichIsA("BasePart",true)
 if not root then return nil end
 local cf,size=model:GetBoundingBox()
 local attachments={}
 local points={{-.25,.35,-.45},{.35,.05,-.48},{-.3,-.2,-.45},{.1,.2,.4}}
 for i,point in points do
  local a=Instance.new("Attachment");a.Name="BeDinoShinyGlint";a.Position=root.CFrame:PointToObjectSpace(cf:PointToWorldSpace(Vector3.new(point[1]*size.X,point[2]*size.Y,point[3]*size.Z)));a.Parent=root
  local e=Instance.new("ParticleEmitter");e.Name="WarmWhiteGlint";e.Texture=textureId
  e.Color=ColorSequence.new(Color3.fromRGB(255,250,220),Color3.fromRGB(255,255,250));e.LightEmission=1
  e.Lifetime=NumberRange.new(.35,.6);e.Rate=1.5;e.Speed=NumberRange.new(0,0);e.LockedToPart=true
  e.Rotation=NumberRange.new(-12,12);e.RotSpeed=NumberRange.new(-15,15)
  local s=math.clamp(math.min(size.X,size.Y,size.Z)*.192,.192,.6)
  e.Size=NumberSequence.new({NumberSequenceKeypoint.new(0,0),NumberSequenceKeypoint.new(.45,s),NumberSequenceKeypoint.new(1,0)})
  e.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,1),NumberSequenceKeypoint.new(.3,.05),NumberSequenceKeypoint.new(1,1)})
  e.Parent=a;table.insert(attachments,a)
 end
 active+=1;local alive=true;local connection
 local function resize()
  if not alive or not model.Parent then return end
  local bounds,dimensions=model:GetBoundingBox()
  for i,a in attachments do
   local point=points[i]
   a.Position=root.CFrame:PointToObjectSpace(bounds:PointToWorldSpace(Vector3.new(point[1]*dimensions.X,point[2]*dimensions.Y,point[3]*dimensions.Z)))
   local size=math.clamp(math.min(dimensions.X,dimensions.Y,dimensions.Z)*.192,.192,.6)
   a.WarmWhiteGlint.Size=NumberSequence.new({NumberSequenceKeypoint.new(0,0),NumberSequenceKeypoint.new(.45,size),NumberSequenceKeypoint.new(1,0)})
  end
 end
 local function destroy()
  if not alive then return end;alive=false;active-=1
  if connection then connection:Disconnect() end
  for _,a in attachments do a:Destroy() end
 end
 connection=model.Destroying:Connect(destroy)
 return {Destroy=destroy,Resize=resize,SetReducedEffects=function(value: boolean) if value then destroy() end end}
end
return Effects
