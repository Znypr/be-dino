"""Execute actual FoodService and RunLifecycle with deterministic engine stubs.
Checks placement filters, real lifecycle transitions and settlement idempotency.
Does not substitute for Studio raycasting/physics/replication testing.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def wrapped(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 return 'local Config='+wrapped('src/shared/Config.luau')+'\n'+'''
local function vector(x,y,z)
 local v={X=x,Y=y,Z=z or 0}
 return setmetatable(v,{__unm=function(a)return vector(-a.X,-a.Y,-a.Z)end,__add=function(a,b)return vector(a.X+b.X,a.Y+b.Y,a.Z+b.Z)end,__sub=function(a,b)return vector(a.X-b.X,a.Y-b.Y,a.Z-b.Z)end,__mul=function(a,b)if type(a)=="number" then a,b=b,a end return vector(a.X*b,a.Y*b,a.Z*b)end,__index=function(t,k)if k=="Magnitude" then return math.sqrt(t.X*t.X+t.Y*t.Y+t.Z*t.Z)end end})
end
local Vector3={new=vector,one=vector(1,1,1),xAxis=vector(1,0,0),zAxis=vector(0,0,1)}
local Vector2={new=vector}
local CFrame={new=vector}
local Color3={fromRGB=function(...)return {...}end}
local Enum={RaycastFilterType={Include="Include"},Material={Water="Water",Grass="Grass",SmoothPlastic="SmoothPlastic"},PartType={Ball="Ball"}}
local RaycastParams={new=function()return {}end}
local Random={new=function(seed)
 math.randomseed(seed)
 return {NextNumber=function(_,low,high)low=low or 0 high=high or 1 return low+math.random()*(high-low)end,NextInteger=function(_,low,high)return math.random(low,high)end}
end}
local noop={Connect=function(self,fn)self.callback=fn end}
local Players={PlayerRemoving=noop,GetPlayers=function()return {}end}
local Remotes={children={}}
function Remotes:FindFirstChild(name)return self.children[name]end
local Workspace={BeDinoArena={},Terrain={},attrs={}}
function Workspace:SetAttribute(k,v)self.attrs[k]=v end
function Workspace:GetServerTimeNow()return 100 end
local rays=0
function Workspace:Raycast(origin,direction,params)
 rays+=1
 if direction.Y<0 then
  assert(params.FilterDescendantsInstances[2]==self.Terrain,"ground ray must include terrain")
  return {Instance=self.Terrain,Position=vector(origin.X,0,origin.Z),Normal=vector(0,1,0),Material="Grass"}
 end
 assert(params.FilterDescendantsInstances[2]==nil,"placement obstacle rays must exclude terrain")
 return nil
end
local workspace=Workspace
local Storage={Shared={Config="Config",MovementEnvelope="Envelope",ResourceModels="Resources"}}
function Storage:FindFirstChild(name)return if name=="BeDinoRemotes" then Remotes else nil end
local guid=0
local Http={GenerateGUID=function()guid+=1 return tostring(guid)end}
local game={GetService=function(self,name)return ({Players=Players,ReplicatedStorage=Storage,HttpService=Http})[name]end}
local require=function(id)if id=="Config" then return Config elseif id=="Resources" then return {clone=function()return nil end} else return {plausible=function()return true end} end end
local Instance={new=function(kind)
 local o={attrs={},Name="",kind=kind,OnServerEvent={Connect=function(self,fn)self.callback=fn end}}
 function o:SetAttribute(k,v)self.attrs[k]=v end
 function o:GetAttribute(k)return self.attrs[k]end
 function o:Destroy()self.destroyed=true end
 function o:IsA(k)return self.kind==k end
 setmetatable(o,{__newindex=function(t,k,v)rawset(t,k,v)if k=="Parent" and v==Remotes then Remotes.children[t.Name]=t end end})
 return o
end}
local scheduled={}
local task={spawn=function(fn)table.insert(scheduled,fn)end,wait=function()end}
local warnings={}
local warn=function(s)table.insert(warnings,s)end
'''+ 'local Food='+wrapped('src/server/FoodService.luau')+'\n'+'''
Food.start({})
assert(Workspace.attrs.FoodCount>1400,"food generation produced too few pickups")
assert(Workspace.attrs.FoodSpawnStatus=="Ready")
assert(rays>5000 and #warnings==0)
print("Food startup passed: "..Workspace.attrs.FoodCount.." pickups, terrain excluded from placement obstacle rays")
task.spawn=function(fn)fn()end
'''+ 'local Lifecycle='+wrapped('src/server/RunLifecycle.luau')+'\n'+'''
local function character()
 local c={attrs={},humanoid={Health=100,Died={Connect=function()end}},root={kind="BasePart",Position=vector(0,5,0)}}
 function c:SetAttribute(k,v)self.attrs[k]=v end
 function c:GetAttribute(k)return self.attrs[k]end
 function c:FindFirstChildOfClass(k)return if k=="Humanoid" then self.humanoid else nil end
 function c:FindFirstChild(k)return if k=="HumanoidRootPart" then self.root else nil end
 function c:WaitForChild(k)return self:FindFirstChildOfClass(k)end
 function c:PivotTo(cf)self.root.Position=cf end
 function c.root:IsA(k)return k==self.kind end
 return c
end
local player={Parent=true,attrs={ProfileState="Loaded"}}
function player:GetAttribute(k)return self.attrs[k]end
function player:SetAttribute(k,v)self.attrs[k]=v end
function player:LoadCharacterAsync()self.Character=character()Lifecycle.prepareSanctuary(self,self.Character)self.Character:SetAttribute("DinoAttached",true)end
local spawn={CFrame=vector(0,0,30),IsA=function(_,kind)return kind=="BasePart"end}
function Workspace.BeDinoArena:FindFirstChild(name)return if name=="PrototypeSpawn" then spawn else nil end
local settlements=0
Lifecycle.configureSettlement(function()settlements+=1 return true end)
Lifecycle.start()
player:LoadCharacterAsync()
assert(player.Character:GetAttribute("RunState")=="Sanctuary")
local start=Remotes.children.RequestStartRun.OnServerEvent.callback
start(player,"extra")
assert(player.Character:GetAttribute("RunState")=="Sanctuary","malformed request accepted")
start(player)
local first=player.Character
assert(first:GetAttribute("RunState")=="Active" and player:GetAttribute("Location")=="Island")
local runId=first:GetAttribute("RunId")
start(player)
assert(first:GetAttribute("RunId")==runId,"duplicate start changed run")
assert(Lifecycle.tryEnd(player,first,"ManualExit"))
assert(settlements==1)
assert(player.Character~=first and player.Character:GetAttribute("RunState")=="Sanctuary")
assert(player:GetAttribute("Location")=="Sanctuary")
assert(not Lifecycle.tryEnd(player,first,"ManualExit"))
assert(settlements==1,"duplicate settlement")
start(player)
assert(player.Character:GetAttribute("RunState")=="Active")
print("Lifecycle passed: sanctuary -> active -> one settlement -> sanctuary; malformed/duplicate requests rejected")
'''
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
 with tempfile.TemporaryDirectory() as temp:
  path=Path(temp)/'verify.luau';path.write_text(script());subprocess.run([args.runner,str(path)],check=True)
