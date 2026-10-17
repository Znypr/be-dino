"""Execute actual FoodService and RunLifecycle with deterministic engine stubs.
Checks placement filters, real lifecycle transitions and settlement idempotency.
Does not substitute for Studio raycasting/physics/replication testing.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def wrapped(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 return 'local Config='+wrapped('src/shared/Config.luau')+'\nlocal CaveHubLayout='+wrapped('src/shared/CaveHubLayout.luau')+'\nlocal script={Parent={Config="Config",FallRecovery="FallRecovery",CaveHubLayout="CaveHubLayout",PrivateState="PrivateState",RewardMath="RewardMath"}}\nlocal require=function(id)if id=="CaveHubLayout" then return CaveHubLayout end return Config end\nlocal FoodCatchRules='+wrapped('src/shared/FoodCatchRules.luau')+'\nlocal Layout='+wrapped('src/shared/IslandLayout.luau')+'\nlocal PointGrid='+wrapped('src/shared/PointGrid.luau')+'\nlocal ScaleLadder='+wrapped('src/shared/ScaleLadder.luau')+'\nlocal SpecialFoods=(function() local script={Parent={Config="Config",ScaleLadder="ScaleLadder"}} local require=function(id)if id=="ScaleLadder" then return ScaleLadder end return Config end return '+wrapped('src/shared/SpecialFoods.luau')+' end)()'+'\nlocal MouthReach=(function() local script={Parent={Config="Config",ScaleLadder="ScaleLadder"}} local require=function(id)if id=="ScaleLadder" then return ScaleLadder end return Config end return '+wrapped('src/shared/MouthReach.luau')+' end)()'+'\n'+'''
local whole,carry=FoodCatchRules.award(500,0,1)
assert(whole==12 and carry<1e-8)
local accumulated,total=0,0
for _=1,500 do local earned,nextCarry=FoodCatchRules.award(1,accumulated,1) total+=earned accumulated=nextCarry end
assert(total==12 and accumulated<1e-8)
local weather=FoodCatchRules.award(500,0,2)
assert(weather==24)
assert(FoodCatchRules.award(0,0,1)==0 and FoodCatchRules.award(0/0,0,1)==0)
print("Food catches passed: 500 points = 12 catches, identical fractional pickup totals, weather bonus and invalid input")
local function vector(x,y,z)
 local v={X=x,Y=y,Z=z or 0}
 return setmetatable(v,{__unm=function(a)return vector(-a.X,-a.Y,-a.Z)end,__add=function(a,b)return vector(a.X+b.X,a.Y+b.Y,a.Z+b.Z)end,__sub=function(a,b)return vector(a.X-b.X,a.Y-b.Y,a.Z-b.Z)end,__mul=function(a,b)if type(a)=="number" then a,b=b,a end return vector(a.X*b,a.Y*b,a.Z*b)end,__index=function(t,k)if k=="Magnitude" then return math.sqrt(t.X*t.X+t.Y*t.Y+t.Z*t.Z)end end})
end
local RewardMath,ProgressionConfig -- BD-479: the real RewardMath is wired in before RunLifecycle loads
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
local nowSeconds=100 -- BD-479: the nest-weather test moves the server clock
function Workspace:GetServerTimeNow()return nowSeconds end
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
local AdminMutationScale='''+wrapped('src/shared/AdminMutationScale.luau')+'''
local Storage={Shared={AdminMutationScale="AdminMutationScale",Config="Config",FoodCatchRules="FoodCatchRules",MovementEnvelope="Envelope",ResourceModels="Resources",IslandLayout="Layout",SpawnGeometry="SpawnGeometry",PointGrid="PointGrid",SpecialFoods="SpecialFoods",MouthReach="MouthReach",ScaleLadder="ScaleLadder",ProgressionConfig="ProgressionConfig"}}
function Storage:FindFirstChild(name)return if name=="BeDinoRemotes" then Remotes else nil end
local guid=0
local Http={GenerateGUID=function()guid+=1 return tostring(guid)end}
local game={GetService=function(self,name)return ({Players=Players,ReplicatedStorage=Storage,HttpService=Http})[name]end}
local require=function(id)if id=="AdminMutationScale" then return AdminMutationScale elseif id=="PrivateState" then return {get=function(p,k)return p.attrs[k] end,set=function(p,k,v)p.attrs[k]=v end} elseif id=="Config" then return Config elseif id=="FoodCatchRules" then return FoodCatchRules elseif id=="Layout" then return Layout elseif id=="SpawnGeometry" then return SpawnGeometry elseif id=="PointGrid" then return PointGrid elseif id=="SpecialFoods" then return SpecialFoods elseif id=="MouthReach" then return MouthReach elseif id=="ScaleLadder" then return ScaleLadder elseif id=="ProgressionConfig" then return ProgressionConfig elseif id=="RewardMath" then return RewardMath elseif id=="FallRecovery" then return {teleport=function(_,c,cf)c:PivotTo(cf)end} elseif id=="Resources" then return {clone=function()if artFailure then error("art failure") end return nil end} else return {plausible=function()return true end} end end
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
local delayed={}
local task={spawn=function(fn)table.insert(scheduled,fn)end,wait=function()end,delay=function(seconds,fn)table.insert(delayed,{seconds=seconds,fn=fn})end}
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
ProgressionConfig='''+wrapped('src/shared/ProgressionConfig.luau')+'\nRewardMath='+wrapped('src/server/RewardMath.luau')+'\n'+ 'local Lifecycle='+wrapped('src/server/RunLifecycle.luau')+'\n'+'''
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
assert(Config.GrowthPerFood==0.1 and Config.PredationGrowthPoints==2.5 and Config.FoodCatchRate==12/500,"growth pace")
print("Growth pace passed: GrowthPerFood 0.1 (500 food -> 50 growth, was 250; BD-386), predation 2.5, eggs on raw food, GrowthCap semantics unchanged")
-- BD-207: special foods are off by default, never roll while off, and leave FoodCatchRate alone.
assert(Config.SpecialFoodsEnabled==false and not SpecialFoods.rolls(0) and Config.FoodCatchRate==12/500,"special foods off")
assert(SpecialFoods.points()==Config.SpecialFoodPoints and Config.SpecialFoodChance>0 and Config.SpecialFoodChance<=0.05,"special food provisional numbers")
print("Special foods passed: flag false by default, no roll while off, PROVISIONAL points explicit, FoodCatchRate untouched")
-- BD-439 (owner 2026-10-16): a player kill = 0.25 run egg with carry, at most 3 per run.
assert(Config.PredationEggPerKill==0.25 and Config.PredationEggMaxPerRun==3,"kill egg config")
do
 local fromKills,carry,eggs=0,0,0
 local seq={}
 for k=1,4 do local w,c,t=FoodCatchRules.awardKill(fromKills,carry) carry,fromKills=c,t eggs+=w seq[k]=w end
 assert(eggs==1 and seq[4]==1 and seq[1]==0 and seq[3]==0,"four kills carry into exactly one egg")
 fromKills,carry,eggs=0,0,0
 for _=1,100 do local w,c,t=FoodCatchRules.awardKill(fromKills,carry) carry,fromKills=c,t eggs+=w end
 assert(eggs==3 and fromKills==3 and carry==0,"100 kills still stop at 3 bonus eggs")
 local w,c,t=FoodCatchRules.awardKill(3,0.75) assert(w==0 and c==0 and t==3,"at the cap nothing is paid or carried")
 local w2,c2,t2=FoodCatchRules.awardKill(2,0.75) assert(w2==1 and c2==0 and t2==3,"the last egg lands exactly on the cap")
end
print("Predation egg bonus passed: 0.25 per player kill with carry, capped at 3 per run")
-- BD-479 (owner BD-235, 2026-10-16): a nest carries the weather when it was FOUND, not at settlement.
do
 assert(Config.NestMinRunSeconds==120 and Config.NestMinCatches==1 and Config.NestEggsPerExtraNest==30,"nest gate changed: update this test")
 local captured
 local settled=0
 Lifecycle.configureSettlement(function(_,runId,catchScore,_,eggEvents,runSeconds,nestWeather)
  settled+=1 captured={runId=runId,catches=catchScore,events=eggEvents,seconds=runSeconds,weather=nestWeather} return true
 end)
 local function flush(character) -- the minimum-run-time timer(s) of this character's run (task.delay is captured, not slept)
  for _,job in delayed do if job.character==character then job.fn() end end
 end
 local function startRun(weatherId)
  Workspace.attrs.WeatherId=weatherId
  local before=#delayed
  local p=newPlayer()
  assert(#delayed==before+1 and delayed[#delayed].seconds>=Config.NestMinRunSeconds,"begin must schedule the minimum-time mark")
  delayed[#delayed].character=p.Character
  return p,p.Character
 end
 local function catch(character,total) character:SetAttribute("CatchScore",total) Lifecycle.noteNestWeather(character) end

 -- nest A found in rain (the minimum time passes while it rains, 1 catch already made), nest B found in clear, settled in blizzard
 nowSeconds=1000
 local p,c=startRun("clear")
 nowSeconds=1010 Workspace.attrs.WeatherId="rain"
 catch(c,1) -- before the minimum time: no nest yet, nothing recorded
 nowSeconds=1121 flush(c) -- 121 s in, still raining: nest A is found now
 nowSeconds=1200 Workspace.attrs.WeatherId="clear"
 catch(c,12) -- no new nest (needs 31 catches)
 nowSeconds=1300
 catch(c,31) -- nest B: 1 + (31-1)//30 = 2 nests, found in clear weather
 nowSeconds=1400 Workspace.attrs.WeatherId="blizzard"
 catch(c,35) -- more catches, no new nest, now snowing
 assert(Lifecycle.tryEnd(p,c,"ManualExit") and settled==1)
 assert(captured.catches==35 and RewardMath.nestCount(captured.catches,captured.seconds)==2 and captured.seconds==400)
 assert(#captured.weather==2 and captured.weather[1]=="rain" and captured.weather[2]=="clear","each nest keeps the weather it was found in, never the settlement weather: "..table.concat(captured.weather,","))
 assert(RewardMath.nestWeatherId(captured.weather,1)=="rain" and RewardMath.nestWeatherId(captured.weather,2)==nil and RewardMath.nestWeatherId(captured.weather,3)==nil)
 flush(c) -- the timer firing after the run ended must do nothing (and not error)

 -- no nest noted while running (e.g. a missed hook): the snapshot falls back to the weather at settlement, exactly the old behaviour
 nowSeconds=2000
 local p2,c2=startRun("rain")
 c2:SetAttribute("CatchScore",31)
 nowSeconds=2200 Workspace.attrs.WeatherId="thunder"
 assert(Lifecycle.tryEnd(p2,c2,"Death") and settled==2)
 assert(#captured.weather==2 and captured.weather[1]=="thunder" and captured.weather[2]=="thunder","unrecorded nests fall back to the settlement weather")

 -- too short or too few catches: no nest, empty ledger; a second run does not inherit the first run's ledger
 nowSeconds=3000
 local p3,c3=startRun("rain")
 catch(c3,5) nowSeconds=3050
 assert(Lifecycle.tryEnd(p3,c3,"ManualExit") and #captured.weather==0,"a 50 s run earns no nest")
 nowSeconds=4000
 local p4,c4=startRun("quake")
 nowSeconds=4130 catch(c4,3) -- time already passed, first catch finds nest 1 in the quake
 nowSeconds=4140 Workspace.attrs.WeatherId="clear"
 assert(Lifecycle.endForDisconnect(p4)=="settled" and settled==4)
 assert(#captured.weather==1 and captured.weather[1]=="quake","disconnect settles with the weather the nest was found in")
 Workspace.attrs.WeatherId=nil
end
print("Nest weather passed: nests keep the weather active when each was found (rain, clear) while settling in blizzard; unrecorded nests fall back to settlement weather; short runs and disconnects covered")
'''
if __name__=='__main__':
 src=(ROOT/'src/server/FoodService.luau').read_text(encoding='utf-8')
 psrc=(ROOT/'src/server/PredationService.luau').read_text(encoding='utf-8')
 assert 'FoodCatchRules.awardKill(' in psrc and 'Config.PredationGrowthPoints' in psrc, 'kill egg bonus, growth unchanged'
 assert 'dinosaur.addGrowth(c, candidate.gained * Config.GrowthPerFood)' in src and 'FoodCatchRules.award(candidate.gained,' in src, 'growth halved but catches use raw food'
 p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
 with tempfile.TemporaryDirectory() as temp:
  path=Path(temp)/'verify.luau';path.write_text(script().replace('@SPAWN@',wrapped('src/shared/SpawnGeometry.luau')));subprocess.run([args.runner,str(path)],check=True)
