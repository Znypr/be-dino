"""Execute actual FoodService and RunLifecycle with deterministic engine stubs.
Checks placement filters, real lifecycle transitions and settlement idempotency.
Does not substitute for Studio raycasting/physics/replication testing.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def wrapped(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 return 'local Config='+wrapped('src/shared/Config.luau')+'\nlocal CaveHubLayout='+wrapped('src/shared/CaveHubLayout.luau')+'\nlocal script={Parent={Config="Config",FallRecovery="FallRecovery",CaveHubLayout="CaveHubLayout",PrivateState="PrivateState"}}\nlocal require=function(id)if id=="CaveHubLayout" then return CaveHubLayout end return Config end\nlocal FoodCatchRules='+wrapped('src/shared/FoodCatchRules.luau')+'\nlocal Layout='+wrapped('src/shared/IslandLayout.luau')+'\nlocal PointGrid='+wrapped('src/shared/PointGrid.luau')+'\n'+'''
local whole,carry=FoodCatchRules.award(500,0,1)
assert(whole==4 and carry<1e-8)
local accumulated,total=0,0
for _=1,500 do local earned,nextCarry=FoodCatchRules.award(1,accumulated,1) total+=earned accumulated=nextCarry end
assert(total==4 and accumulated<1e-8)
local weather=FoodCatchRules.award(500,0,2)
assert(weather==8)
assert(FoodCatchRules.award(0,0,1)==0 and FoodCatchRules.award(0/0,0,1)==0)
print("Food catches passed: 500 points = 4 catches, identical fractional pickup totals, weather bonus and invalid input")
local function vector(x,y,z)
 local v={X=x,Y=y,Z=z or 0}
 return setmetatable(v,{__unm=function(a)return vector(-a.X,-a.Y,-a.Z)end,__add=function(a,b)return vector(a.X+b.X,a.Y+b.Y,a.Z+b.Z)end,__sub=function(a,b)return vector(a.X-b.X,a.Y-b.Y,a.Z-b.Z)end,__mul=function(a,b)if type(a)=="number" then a,b=b,a end return vector(a.X*b,a.Y*b,a.Z*b)end,__index=function(t,k)if k=="Magnitude" then return math.sqrt(t.X*t.X+t.Y*t.Y+t.Z*t.Z)end end})
end
local Vector3={new=vector,one=vector(1,1,1),xAxis=vector(1,0,0),zAxis=vector(0,0,1)}
local Vector2={new=vector}
local CFrame={new=function(x,y,z)if type(x)=='table' then return x end return vector(x,y,z)end}
local SpawnGeometry=@SPAWN@
local Color3={fromRGB=function(...)return {...}end,new=function(...)return {...}end}
local UDim2={fromOffset=function(...)return {...}end,fromScale=function(...)return {...}end}
local Enum={RaycastFilterType={Include="Include"},Material={Water="Water",Grass="Grass",SmoothPlastic="SmoothPlastic"},PartType={Ball="Ball"},Font={FredokaOne="FredokaOne"}}
local RaycastParams={new=function()return {}end}
local Random={new=function(seed)
 math.randomseed(seed or 123)
 return {NextNumber=function(_,low,high)low=low or 0 high=high or 1 return low+math.random()*(high-low)end,NextInteger=function(_,low,high)return math.random(low,high)end}
end}
local noop={Connect=function(self,fn)self.callback=fn end}
local Players={PlayerRemoving=noop,PlayerAdded={Connect=function()end},GetPlayers=function()return {}end}
local Remotes={children={}}
function Remotes:FindFirstChild(name)return self.children[name]end
local Workspace={BeDinoArena={},Terrain={},attrs={}}
function Workspace:SetAttribute(k,v)self.attrs[k]=v end
function Workspace:GetServerTimeNow()return 100 end
function Workspace:GetAttribute(k)return self.attrs[k]end
local rays=0
local missingTerrain=false
local artFailure=false
function Workspace:Raycast(origin,direction,params)
 rays+=1
 if direction.Y<0 then
  assert(params.FilterDescendantsInstances[1]==self.Terrain and params.FilterDescendantsInstances[2]==nil,"ground ray must query terrain independently of props")
  if missingTerrain then return nil end
  return {Instance=self.Terrain,Position=vector(origin.X,0,origin.Z),Normal=vector(0,1,0),Material="Grass"}
 end
 assert(params.FilterDescendantsInstances[2]==nil,"placement obstacle rays must exclude terrain")
 return nil
end
local workspace=Workspace
local Storage={Shared={Config="Config",FoodCatchRules="FoodCatchRules",MovementEnvelope="Envelope",ResourceModels="Resources",IslandLayout="Layout",SpawnGeometry="SpawnGeometry",PointGrid="PointGrid"}}
function Storage:FindFirstChild(name)return if name=="BeDinoRemotes" then Remotes else nil end
local guid=0
local Http={GenerateGUID=function()guid+=1 return tostring(guid)end}
local game={GetService=function(self,name)return ({Players=Players,ReplicatedStorage=Storage,HttpService=Http})[name]end}
local require=function(id)if id=="PrivateState" then return {get=function(p,k)return p.attrs[k] end,set=function(p,k,v)p.attrs[k]=v end} elseif id=="Config" then return Config elseif id=="FoodCatchRules" then return FoodCatchRules elseif id=="Layout" then return Layout elseif id=="SpawnGeometry" then return SpawnGeometry elseif id=="PointGrid" then return PointGrid elseif id=="FallRecovery" then return {teleport=function(_,c,cf)c:PivotTo(cf)end} elseif id=="Resources" then return {clone=function()if artFailure then error("art failure") end return nil end} else return {plausible=function()return true end} end end
local created={}
local Instance={new=function(kind)
 local o={attrs={},Name="",kind=kind,OnServerEvent={Connect=function(self,fn)self.callback=fn end}}
 table.insert(created,o)
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
local starter=0
for _,item in created do
 if item.kind=="Part" and item.attrs.StarterFood and item.Position then -- BD-387: a starter item that found no ground was destroyed before being placed
  starter+=1
  assert((vector(item.Position.X,0,item.Position.Z)-vector(0,0,30)).Magnitude<25,"starter food too far from entry")
 end
end
assert(starter>=12 and starter<=2*Config.FoodClusterItems,"two entrance clusters must survive placement (BD-387: up to 9 items each, at least the old 6)")
missingTerrain=true
Food.start({})
assert(Workspace.attrs.FoodCount>1400 and Workspace.attrs.FoodPlacementFallbacks>0,"heightfield fallback produced an empty map")
missingTerrain=false artFailure=true
Food.start({})
assert(Workspace.attrs.FoodCount>1400,"broken art must not remove food")
print("Food startup passed: terrain-only placement, 12 nearby starter pickups, missing-ray fallback and broken-art survival")
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
-- BD-210 gate: no run start before the server terrain is built and this client reported its local terrain.
Remotes.children.RequestStartRun.OnServerEvent.callback(player)
assert(player.Character:GetAttribute("RunState")=="Sanctuary" and player:GetAttribute("LastRunStartStatus")=="WorldLoading","run started before terrain")
Workspace.attrs.IslandTerrainReady=true
Remotes.children.RequestStartRun.OnServerEvent.callback(player)
assert(player.Character:GetAttribute("RunState")=="Sanctuary","run started before the client terrain handshake")
Remotes.children.ClientWorldReady.OnServerEvent.callback(player,"junk")
assert(player:GetAttribute("WorldReady")==nil,"malformed ready accepted")
Remotes.children.ClientWorldReady.OnServerEvent.callback(player)
assert(player:GetAttribute("WorldReady")==true)
player:SetAttribute("LastRunStartStatus",nil)
print("Spawn gate passed: run start waits for server terrain and the client terrain handshake")
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
-- BD-052 Home: one confirmed request ends the run at once through the idempotent tryEnd path.
local home=Remotes.children.RequestEndRun.OnServerEvent.callback
local running=player.Character
home(player,"extra")
assert(running:GetAttribute("RunState")=="Active" and settlements==1,"malformed Home accepted")
home(player)
assert(settlements==2 and running:GetAttribute("RunState")=="Settled","Home must settle immediately (no stay-still channel)")
assert(player:GetAttribute("LastRunEndReason")=="ManualExit" and player:GetAttribute("LastExitStatus")=="returning")
assert(player.Character~=running and player.Character:GetAttribute("RunState")=="Sanctuary")
home(player)
assert(settlements==2,"Home in sanctuary must not settle")
assert(not Lifecycle.tryEnd(player,running,"Death") and settlements==2,"death after Home settled twice")
local function newPlayer()
 local p={Parent=true,attrs={ProfileState="Loaded",WorldReady=true}}
 p.GetAttribute,p.SetAttribute,p.LoadCharacterAsync=player.GetAttribute,player.SetAttribute,player.LoadCharacterAsync
 p:LoadCharacterAsync() start(p)
 p.Character:SetAttribute("SpawnProtectionEndsAt",0)
 return p
end
local prey,hunter,small=newPlayer(),newPlayer(),newPlayer()
prey.Character:SetAttribute("GrowthScore",10) hunter.Character:SetAttribute("GrowthScore",100) small.Character:SetAttribute("GrowthScore",10.5)
prey.Character.root.Position=vector(0,5,0) hunter.Character.root.Position=vector(0,5,Config.HomeThreatRadius-1) small.Character.root.Position=vector(1,5,0)
Players.GetPlayers=function()return {prey,hunter,small}end
local before=settlements
home(prey)
assert(prey.Character:GetAttribute("RunState")=="Active" and settlements==before and prey:GetAttribute("LastExitStatus")=="predator_nearby","Home escaped a nearby predator")
hunter.Character.root.Position=vector(0,5,Config.HomeThreatRadius+5)
local waitUntil=os.clock()+Config.ExitRequestCooldownSeconds+0.05 repeat until os.clock()>waitUntil
home(prey)
assert(settlements==before+1 and prey:GetAttribute("LastRunEndReason")=="ManualExit","Home blocked by a distant or same-size dinosaur")
Players.GetPlayers=function()return {}end
print("Home passed: immediate single settlement, sanctuary/duplicate/death no-ops, refused only while a bigger dinosaur is within HomeThreatRadius")
-- Owner 2026-10-15: growth gained per food point is halved; catches/eggs still use RAW food (FoodCatchRules.award).
assert(Config.GrowthPerFood==0.1 and Config.PredationGrowthPoints==2.5 and Config.FoodCatchRate==4/500,"growth pace")
print("Growth pace passed: GrowthPerFood 0.1 (500 food -> 50 growth, was 250; BD-386), predation 2.5, eggs on raw food, GrowthCap semantics unchanged")
'''
if __name__=='__main__':
 src=(ROOT/'src/server/FoodService.luau').read_text(encoding='utf-8')
 assert 'dinosaur.addGrowth(c, candidate.gained * Config.GrowthPerFood)' in src and 'FoodCatchRules.award(candidate.gained,' in src, 'growth halved but catches use raw food'
 p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
 with tempfile.TemporaryDirectory() as temp:
  path=Path(temp)/'verify.luau';path.write_text(script().replace('@SPAWN@',wrapped('src/shared/SpawnGeometry.luau')));subprocess.run([args.runner,str(path)],check=True)
