"""Execute real catalog, economy rules, profile transactions and leap handler in Luau.
Mocks validate logic/transactions, not Studio physics or rendering.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 s='local ProgressionConfig='+module('src/shared/ProgressionConfig.luau')+'\nlocal GameConfig='+module('src/shared/Config.luau')+'\n'
 s+='local script={Parent={ProgressionConfig="ProgressionConfig"}}\nlocal require=function(_)return ProgressionConfig end\nlocal Rules='+module('src/shared/ProgressionRules.luau')+'\n'
 s+='''
local p={}
local progress=Rules.upgrade(p)
assert(progress.crystals==0 and Rules.valid(progress))
assert(not Rules.apply(p,"buyAura","meadow",100,false))
for _=1,30 do assert(Rules.apply(p,"grant","crystal",100,false,100)) end
assert(Rules.apply(p,"buyAura","meadow",100,false))
assert(progress.crystals==2940)
assert(not Rules.apply(p,"buyAura","meadow",100,false))
assert(Rules.apply(p,"equipAura","meadow",100,false))
assert(not Rules.apply(p,"equipAura","royal",100,false))
assert(Rules.apply(p,"buyPotion","growth_common",100,false))
assert(Rules.apply(p,"buyPotion","growth_common",100,false))
assert(Rules.apply(p,"usePotion","growth_common",100,false))
assert(progress.buffs.growth.expiresAt==400 and progress.potions.growth_common==1)
local ok,status=Rules.apply(p,"usePotion","growth_common",110,false)
assert(not ok and status=="replace_confirmation_required" and progress.potions.growth_common==1)
assert(Rules.apply(p,"usePotion","growth_common",110,true))
assert(progress.buffs.growth.expiresAt==410 and progress.potions.growth_common==0)
local common,commonSpeed,commonLoot=Rules.multipliers(progress,"compy",ProgressionConfig.Weather[1],120)
local rare,rareSpeed,rareLoot=Rules.multipliers(progress,"triceratops",ProgressionConfig.Weather[1],120)
local legend,legendSpeed,legendLoot=Rules.multipliers(progress,"tyrannosaurus",ProgressionConfig.Weather[1],120)
assert(common<rare and rare<legend and commonLoot<rareLoot and rareLoot<legendLoot)
local expired=Rules.multipliers(progress,"compy",nil,411)
assert(math.abs(expired-1.15)<.000001)
for _,item in ProgressionConfig.Potions do
 assert(item.duration>=300 and item.price>0 and item.multiplier>1)
end
assert(not Rules.valid({crystals=0/0,auras={},potions={},buffs={},equippedAura=""}))
assert(not Rules.apply(p,"grant","crystal",100,false,0/0))
assert(not Rules.apply(p,"grant","crystal",100,false,1000))
assert(not Rules.apply(p,"buyPotion","fake",100,false))
print("Progression rules passed: prices, ownership, consumption, replacement, expiry, rarity bonuses and invalid data")
local function copy(t)
 if type(t)~="table" then return t end
 local result={} for k,v in t do result[k]=copy(v) end return result
end
local data={}
local fail=false
local transforms=0
local store={UpdateAsync=function(_,key,fn)
 if fail then error("injected outage") end
 transforms+=1
 -- Emulate repeated transforms; only final transform commits.
 local probe=copy(data[key]);fn(probe)
 local updated=fn(copy(data[key]))
 if updated==nil then return nil end
 data[key]=copy(updated)
 return copy(updated)
end}
local http={GenerateGUID=function()return "test-lease" end,JSONEncode=function(_,v)return "json" end}
local storage={Shared={Config="Config",ProgressionRules="Rules"}}
local datastores={GetDataStore=function()return store end}
local services={DataStoreService=datastores,HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function()return false end}}
local game={GameId=1,JobId="test",GetService=function(_,id)return services[id] end}
local task={wait=function()end,spawn=function()end}
local warn=function()end
local script={Parent={RewardMath="Rewards"}}
local require=function(id)
 if id=="Config" then return GameConfig elseif id=="Rules" then return Rules elseif id=="Rewards" then return {} end
 error("unexpected module "..tostring(id))
end
local Repository=REPO_MODULE
local player={Parent=true,UserId=123,Name="Test",attrs={}}
function player:SetAttribute(k,v)self.attrs[k]=v end
function player:GetAttribute(k)return self.attrs[k]end
assert(Repository.load(player))
assert(Repository.progression(player).crystals==0)
local function action(a,id,token,replace,amount)return Repository.progressionAction(player,a,id,token,replace,amount)end
assert(action("grant","crystal","grant1",false,100))
assert(action("grant","crystal","grant2",false,100))
assert(Repository.progression(player).crystals==200)
local success,duplicate=action("grant","crystal","grant1",false,100)
assert(success and duplicate=="duplicate" and Repository.progression(player).crystals==200)
assert(action("buyAura","meadow","buy1",false))
assert(Repository.progression(player).crystals==140)
assert(action("buyAura","meadow","buy1",false))
assert(Repository.progression(player).crystals==140)
local conflict,conflictStatus=action("buyPotion","speed_common","buy1",false)
assert(not conflict and conflictStatus=="token_conflict")
assert(action("buyPotion","speed_common","potion1",false))
assert(action("usePotion","speed_common","use1",false))
assert(action("usePotion","speed_common","use1",false))
assert(Repository.progression(player).potions.speed_common==0)
local expiry=Repository.progression(player).buffs.speed.expiresAt
Repository.release(player)
assert(Repository.load(player))
assert(Repository.progression(player).crystals==120 and Repository.progression(player).auras.meadow)
assert(Repository.progression(player).buffs.speed.expiresAt==expiry)
local before=copy(data['u:123'])
fail=true
local failed,failedStatus=action("buyPotion","speed_common","outage",false)
assert(not failed and failedStatus=="save_failed")
assert(data['u:123'].progression.crystals==before.progression.crystals)
assert(player:GetAttribute("ProfileState")=="SaveFailed")
fail=false
Repository.release(player)
assert(Repository.load(player))
data['u:123'].session.leaseId="other"
local lost,lostStatus=action("buyPotion","speed_common","lease",false)
assert(not lost and lostStatus=="lease_lost")
assert(data['u:123'].progression.crystals==120)
print("Profile transactions passed: repeated transforms, duplicate grants/purchases/use, token conflicts, rejoin, outage rollback and lease loss")
'''
 s+=r"""
local script={Parent={ProgressionConfig="ProgressionConfig"}}
local require=function()return ProgressionConfig end
local Clock=CLOCK_MODULE
local choiceCount=0
local function choose()choiceCount+=1 return ProgressionConfig.Weather[2]end
local clock=Clock.new(100)
assert(not Clock.step(clock,699,choose) and choiceCount==0 and clock.current==nil)
assert(Clock.step(clock,700,choose) and choiceCount==1 and clock.endsAt==880)
assert(not Clock.step(clock,879,choose) and choiceCount==1)
assert(Clock.step(clock,880,choose) and clock.current==nil and clock.nextAt==1480)
assert(Clock.step(clock,1480,choose) and choiceCount==2)
print("Weather clock passed: hidden choice until start, 600s clear interval, 180s event and end cleanup")
local function vec(x,y,z)
 return setmetatable({X=x,Y=y,Z=z},{__add=function(a,b)return vec(a.X+b.X,a.Y+b.Y,a.Z+b.Z)end,__sub=function(a,b)return vec(a.X-b.X,a.Y-b.Y,a.Z-b.Z)end,__mul=function(a,b)return vec(a.X*b,a.Y*b,a.Z*b)end,__index=function(a,k)if k=="Magnitude" then return math.sqrt(a.X*a.X+a.Y*a.Y+a.Z*a.Z)elseif k=="Unit" then return vec(a.X/a.Magnitude,a.Y/a.Magnitude,a.Z/a.Magnitude)end end})
end
local Vector3={new=vec,zero=vec(0,0,0)}
local Enum={RaycastFilterType={Include=true},Material={Air="air",Grass="grass"},HumanoidStateType={Jumping="jump"}}
local CFrame={new=function(p)return {Position=p}end}
local RaycastParams={new=function()return {}end}
local Color3={fromRGB=function(...)return {...}end,new=function(...)return {...}end}
local ColorSequence={new=function(...)return {...}end}
local signal=function()return {Connect=function(self,fn)self.fn=fn end}end
local heartbeat=signal()
local removal=signal()
local remotes={}
local Instance={new=function(kind)
 local o={OnServerEvent=signal(),kind=kind}
 function o:Destroy()self.destroyed=true end
 return setmetatable(o,{__newindex=function(t,k,v)rawset(t,k,v)if k=="Name" and kind=="RemoteEvent" then remotes[v]=o end end})
end}
local leapNow=0
local blocked=false
local workspace={Terrain={},BeDinoArena={},GetServerTimeNow=function()return leapNow end,Blockcast=function()return if blocked then {} else nil end}
local storage={Shared={ProgressionConfig=true},BeDinoRemotes={}}
local game={GetService=function(_,id)return ({Players={PlayerRemoving=removal},ReplicatedStorage=storage,RunService={Heartbeat=heartbeat}})[id]end}
local require=function()return ProgressionConfig end
local Leap=LEAP_MODULE
local h={Health=100,FloorMaterial="grass",WalkSpeed=22,ChangeState=function()end}
local root={Parent=true,Position=vec(0,5,0),Size=vec(2,2,1),CFrame={LookVector=vec(0,0,-1)},AssemblyLinearVelocity=vec(0,0,0)}
local ownerChanges=0 local ownerFailure=false
function root:IsA(id)return id=="BasePart"end
function root:SetNetworkOwner(_)if ownerFailure then error("cannot own")end ownerChanges+=1 end
function root:SetNetworkOwnershipAuto()self.restored=true end
local c={attrs={RunState="Active"}}
function c:GetAttribute(k)return self.attrs[k]end
function c:SetAttribute(k,v)self.attrs[k]=v end
function c:FindFirstChild(k)return if k=="HumanoidRootPart" then root else nil end
function c:FindFirstChildOfClass(k)return if k=="Humanoid" then h else nil end
local user={Character=c,attrs={ProfileState="Loaded",MovementSecurityStatus="OK"}}
function user:GetAttribute(k)return self.attrs[k]end
function user:SetAttribute(k,v)self.attrs[k]=v end
Leap.start()
local activate=remotes.RequestLeap.OnServerEvent.fn
activate(user,"bad") assert(ownerChanges==0)
activate(user) assert(ownerChanges==1 and user.attrs.LeapReadyAt==60 and root.AssemblyLinearVelocity.Y==62)
leapNow=.4 activate(user) assert(ownerChanges==1 and user.attrs.LeapReadyAt==60)
leapNow=.8 heartbeat.fn() assert(root.restored and c.attrs.LeapUntil==0 and c.attrs.MovementSpeedLimit==nil)
assert(root.AssemblyLinearVelocity.Magnitude<70)
leapNow=60 blocked=true activate(user) assert(ownerChanges==1 and user.attrs.LeapReadyAt==60)
leapNow=61 blocked=false h.FloorMaterial="air" activate(user) assert(ownerChanges==1)
leapNow=62 h.FloorMaterial="grass" ownerFailure=true activate(user) assert(user.attrs.LeapReadyAt==60)
leapNow=63 ownerFailure=false activate(user) assert(ownerChanges==2 and user.attrs.LeapReadyAt==123)
print("Leap handler passed: malformed requests, exact 60s cooldown, wall/air rejection, failed ownership and cleanup")
"""
 return s.replace('REPO_MODULE',module('src/server/ProfileRepository.luau')).replace('CLOCK_MODULE',module('src/shared/WeatherClock.luau')).replace('LEAP_MODULE',module('src/server/LeapService.luau'))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/'progression.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
