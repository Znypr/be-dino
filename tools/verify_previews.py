"""Execute real PreviewCamera and project every source vertex into its resulting frustum."""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def script():
 geometry=(ROOT/'src/shared/ResourceGeometry.luau').read_text()
 camera=(ROOT/'src/shared/PreviewCamera.luau').read_text()
 return '''
local function v(x,y,z)
 return setmetatable({X=x,Y=y,Z=z},{__add=function(a,b)return v(a.X+b.X,a.Y+b.Y,a.Z+b.Z)end,__sub=function(a,b)return v(a.X-b.X,a.Y-b.Y,a.Z-b.Z)end,__mul=function(a,b)return v(a.X*b,a.Y*b,a.Z*b)end,__div=function(a,b)return v(a.X/b,a.Y/b,a.Z/b)end,__index=function(a,k)
 if k=="Magnitude" then return math.sqrt(a.X*a.X+a.Y*a.Y+a.Z*a.Z) elseif k=="Unit" then return a/a.Magnitude
 elseif k=="Dot" then return function(a,b)return a.X*b.X+a.Y*b.Y+a.Z*b.Z end
 elseif k=="Cross" then return function(a,b)return v(a.Y*b.Z-a.Z*b.Y,a.Z*b.X-a.X*b.Z,a.X*b.Y-a.Y*b.X)end
 elseif k=="Min" then return function(a,b)return v(math.min(a.X,b.X),math.min(a.Y,b.Y),math.min(a.Z,b.Z))end
 elseif k=="Max" then return function(a,b)return v(math.max(a.X,b.X),math.max(a.Y,b.Y),math.max(a.Z,b.Z))end end end})
end
local Vector3={new=v,zero=v(0,0,0)}
local CFrame={}
function CFrame.lookAt(position,target)
 local z=(position-target).Unit
 local x=v(0,1,0):Cross(z).Unit
 local y=z:Cross(x)
 return {Position=position,XVector=x,YVector=y,ZVector=z}
end
local identity={Position=v(0,0,0),PointToWorldSpace=function(_,p)return p end}
local signal={Connect=function()return {Disconnect=function()end}end}
local game={GetService=function()return {RenderStepped=signal}end}
local Instance={new=function()return {}end}
local Geometry=(function()
'''+geometry+'''\nend)()
local script={Parent={UITheme="Theme",ResourceGeometry="Geometry"}}
local require=function(id)return if id=="Theme" then {MotionEnabled=true} else Geometry end
local PreviewCamera=(function()
'''+camera+'''\nend)()
for _,id in {"compy","triceratops","tyrannosaurus"} do
 for _,size in {{250,172},{274,230},{380,280},{120,146}} do
  local viewport={AbsoluteSize={X=size[1],Y=size[2]},Destroying=signal,GetPropertyChangedSignal=function()return signal end}
  local model={GetBoundingBox=function()return identity,v(100,100,100)end,GetAttribute=function()return Vector3.zero end,GetPivot=function()return identity end}
  PreviewCamera.bind(viewport,model,id)
  local cam=viewport.CurrentCamera
  local basis=cam.CFrame
  local tan=math.tan(math.rad(cam.FieldOfView/2))
  local maxX,maxY=0,0
  for _,vertex in Geometry[id].vertices do
   local point=v(vertex[1],vertex[2],vertex[3])-basis.Position
   local depth=-point:Dot(basis.ZVector)
   assert(depth>0,"geometry behind camera")
   local x=math.abs(point:Dot(basis.XVector)/(depth*tan*size[1]/size[2]))
   local y=math.abs(point:Dot(basis.YVector)/(depth*tan))
   assert(x<1 and y<1,"preview cropped")
   maxX=math.max(maxX,x) maxY=math.max(maxY,y)
  end
  assert(math.max(maxX,maxY)>.85,"preview wastes card space")
 end
end
print("Preview camera passed: all vertices visible with tight framing for 3 dinos across 4 card aspect ratios")
'''
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
 with tempfile.TemporaryDirectory() as d:
  f=Path(d)/'previews.luau';f.write_text(script());r=subprocess.run([args.runner,str(f)],capture_output=True,text=True)
  print(r.stdout,end='');print(r.stderr,end='');raise SystemExit(r.returncode)
