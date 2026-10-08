"""Execute real catalog, economy rules, profile transactions and leap handler in Luau.
Mocks validate logic/transactions, not Studio physics or rendering.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 s='local ProgressionConfig='+module('src/shared/ProgressionConfig.luau')+'\nlocal GameConfig='+module('src/shared/Config.luau')+'\n'
 s+='local script={Parent={ProgressionConfig="ProgressionConfig"}}\nlocal require=function(_)return ProgressionConfig end\nlocal Genetics='+module('src/shared/EggGenetics.luau')+'\n'
 s+='local script={Parent={Config="Config",EggGenetics="Genetics"}}\nlocal require=function(id)return if id=="Genetics" then Genetics else GameConfig end\nlocal EggTraits='+module('src/shared/EggTraits.luau')+'\n'
 s+='local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}\nlocal require=function(id)return if id=="Genetics" then Genetics else ProgressionConfig end\nlocal Rules='+module('src/shared/ProgressionRules.luau')+'\n'
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
local legacy={progression={crystals=700,auras={meadow=true},equippedAura="meadow",potions={},buffs={}}}
assert(Rules.valid(legacy.progression))
local migrated=Rules.upgrade(legacy)
assert(migrated.crystals==700 and migrated.auras.meadow and migrated.equippedTrail=="white")
assert(not Rules.apply(legacy,"equipTrail","nova",0,false))
assert(not Rules.apply(legacy,"buyTrail","nova",0,false))
migrated.accountXP=193600 migrated.crystals=5600
assert(Rules.apply(legacy,"buyTrail","nova",0,false) and migrated.crystals==100)
assert(not Rules.apply(legacy,"buyTrail","nova",0,false) and migrated.crystals==100)
assert(Rules.apply(legacy,"equipTrail","nova",0,false))
assert(Rules.apply(legacy,"equipTrail","",0,false))
assert(not Rules.valid({crystals=0,auras={},equippedAura="",potions={},buffs={},trails={fake=true},equippedTrail=""}))
for _,event in ProgressionConfig.Weather do
 local tagged=Rules.eventEgg(event.id,0)
 assert(tagged.mutationId==event.mutation and Rules.validEgg(tagged))
 assert(Rules.eventEgg(event.id,1).mutationId=="")
 assert(event.chance>0 and event.chance<.1 and event.weight>0)
end
assert(not Rules.validEgg({eventId="clear",mutationId="ember"}))
assert(not Rules.validEgg({eventId="volcano",mutationId="frost"}))
assert(Rules.validEvents({ember=2}) and not Rules.validEvents({ember=-1}) and not Rules.validEvents({fake=1}))
assert(Rules.eventMutation({events={ember=1}}).id=="ember")
print("Trail/event rules passed: additive migration, prices, ownership, equip/unequip, mutation chances and metadata validation")
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
local guid=0
local http={GenerateGUID=function()guid+=1 return "test-"..guid end,JSONEncode=function(_,v)return copy(v) end,JSONDecode=function(_,v)return copy(v) end}
local mutableConfig=table.clone(GameConfig)
mutableConfig.DeveloperProducts={[456]=20} -- Mock product, never shipped in Config.
GameConfig=mutableConfig
local storage={Shared={Config="Config",ProgressionRules="Rules",EggTraits="EggTraits",EggGenetics="Genetics",ProgressionConfig="ProgressionConfig"}}
local datastores={GetDataStore=function()return store end}
local services={DataStoreService=datastores,HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function()return false end}}
local game={GameId=1,JobId="test",GetService=function(_,id)return services[id] end}
local task={wait=function()end,spawn=function()end}
local warn=function()end
local script={Parent={RewardMath="Rewards"}}
local rewardSpecies=nil
local require=function(id)
 if id=="Genetics" then return Genetics elseif id=="EggTraits" then return EggTraits elseif id=="ProgressionConfig" then return ProgressionConfig elseif id=="Config" then return GameConfig elseif id=="Rules" then return Rules elseif id=="Rewards" then return {computeRunReward=function()return {stacks={},chestCount=2}end,computeChestReward=function()return {speciesId=if rewardSpecies then table.remove(rewardSpecies,1) else "raptor",count=2,mutationId="base"}end} end
 error("unexpected module "..tostring(id))
end
local traitRoll=1
local Random={new=function()return {NextNumber=function()return traitRoll end}end}
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
Repository.release(player)
-- Historical v1 balances survive additive catalog and Diamond migration.
for _,id in {"raptor","stegosaurus","ankylosaurus"} do data['u:123'].collection[id]=nil end
for _,entry in data['u:123'].collection do entry.diamond=nil end
data['u:123'].collection.compy.base=150
data['u:123'].collection.compy.gold=49
assert(Repository.load(player))
assert(data['u:123'].collection.compy.base==150 and data['u:123'].collection.compy.gold==49)
for _,id in GameConfig.SpeciesOrder do assert(data['u:123'].collection[id].diamond==0) end
local insufficient,_,reason=Repository.mutateSpecies(player,"compy","diamond","too-soon")
assert(not insufficient and reason=="insufficient_copies")
assert(Repository.mutateSpecies(player,"compy","gold","gold1"))
assert(data['u:123'].collection.compy.base==100 and data['u:123'].collection.compy.gold==50)
assert(Repository.mutateSpecies(player,"compy","gold","gold1"))
assert(data['u:123'].collection.compy.base==100 and data['u:123'].collection.compy.gold==50)
local conflict,_,reason=Repository.mutateSpecies(player,"compy","diamond","gold1")
assert(not conflict and reason=="token_conflict")
assert(Repository.mutateSpecies(player,"compy","diamond","diamond1"))
assert(Repository.mutateSpecies(player,"compy","diamond","diamond1"))
assert(data['u:123'].collection.compy.gold==0 and data['u:123'].collection.compy.diamond==1)
Repository.release(player)
assert(Repository.load(player))
assert(data['u:123'].collection.compy.diamond==1)
assert(Repository.equipSpecies(player,"compy"))
assert(Repository.commitRunSettlement(player,"timer-live",10))
assert(data['u:123'].eggs[2].readyAt-data['u:123'].eggs[1].readyAt==0)
print("Migration/fusion passed: preserved v1 balances, six catalog entries, exact costs, idempotency and immediately ready new eggs")
local before=copy(data['u:123'])
local eventUser={Parent=true,UserId=888,attrs={}}
function eventUser:SetAttribute(k,v)self.attrs[k]=v end
function eventUser:GetAttribute(k)return self.attrs[k]end
assert(Repository.load(eventUser))
Repository.release(eventUser)
for i=1,4 do table.insert(data['u:888'].eggs,{eggId="fixture-"..i,kind="alpha_chest",readyAt=1}) end
assert(Repository.load(eventUser))
local genes={conditionId="normal",hatchSuccess=true,primaryColorId="white",secondaryColorId="blue",blend=80}
local tags={{eventId="volcano",mutationId="ember",genes=genes,shiny=false,big=false},{eventId="aurora",mutationId="aurora",genes=genes,shiny=false,big=false}}
local emberKey=EggTraits.key("ember",false,false,genes)
assert(Repository.commitRunSettlement(eventUser,"event-run",10,tags))
assert(Repository.commitRunSettlement(eventUser,"event-run",10,tags))
assert(#data['u:888'].eggs==5 and data['u:888'].pendingChestGrants==1)
assert(data['u:888'].eggs[5].mutationId=="ember" and data['u:888'].pendingEggEvents[1].mutationId=="aurora")
Repository.release(eventUser)
data['u:888'].eggs[5].readyAt=1
local emberId=data['u:888'].eggs[5].eggId
assert(Repository.load(eventUser))
assert(not Repository.claimChest(eventUser,emberId))
for i=1,4 do assert(Repository.claimChest(eventUser,"fixture-"..i)) end
local claimed,reward=Repository.claimChest(eventUser,emberId)
assert(claimed and reward.eventMutationId=="ember")
assert(Repository.claimChest(eventUser,emberId))
assert(data['u:888'].collection.raptor.variants[emberKey].count==2 and data['u:888'].collection.raptor.base==8)
assert(data['u:888'].pendingChestGrants==0 and #data['u:888'].pendingEggEvents==0)
assert(data['u:888'].eggs[1].mutationId=="aurora")
assert(Repository.equipSpecies(eventUser,"raptor") and eventUser.attrs.EquippedEventMutation=="ember")
assert(not Repository.commitRunSettlement(eventUser,"bad-event",10,{{eventId="volcano",mutationId="frost"}}))
Repository.release(eventUser)
assert(Repository.load(eventUser) and eventUser.attrs.EquippedEventMutation=="ember")
print("Event transactions passed: repeated settlement transforms, overflow FIFO, mutated hatch, no Base duplication, duplicate claim, equip and rejoin")
assert(Repository.claimChest(eventUser,data['u:888'].eggs[1].eggId))
traitRoll=0
local stackedTags=copy(tags) for _,tag in stackedTags do tag.shiny=true tag.big=true end
assert(Repository.commitRunSettlement(eventUser,"stacked-traits",10,stackedTags))
local stackedId=data['u:888'].eggs[1].eggId
local success,stacked=Repository.claimChest(eventUser,stackedId)
assert(success and stacked.shiny and stacked.big)
assert(Repository.claimChest(eventUser,stackedId))
assert(data['u:888'].collection.raptor.variants[EggTraits.key("ember",true,true,genes)].count==2)
assert(data['u:888'].collection.raptor.variants[emberKey].count==2 and data['u:888'].collection.raptor.base==8)
Repository.release(eventUser)
assert(Repository.load(eventUser) and eventUser.attrs.EquippedBig and eventUser.attrs.EquippedShiny)
assert(eventUser.attrs.RarestCaught==1)
local metricBefore=data['u:888'].metrics.playSeconds
data['u:888'].session.metricsAt=os.time()-45
assert(Repository.renew(eventUser))
assert(data['u:888'].metrics.playSeconds>=metricBefore+45)
assert(Repository.renew(eventUser) and data['u:888'].metrics.playSeconds<metricBefore+47)
local receipt={ProductId=456,PlayerId=888,PurchaseId="real-callback-fixture",CurrencySpent=7}
assert(Repository.purchase(eventUser,receipt))
assert(Repository.purchase(eventUser,receipt))
assert(data['u:888'].metrics.robux==7)
assert(not Repository.purchase(eventUser,{ProductId=999,PlayerId=888,PurchaseId="unknown",CurrencySpent=50}))
assert(not Repository.purchase(eventUser,{ProductId=456,PlayerId=123,PurchaseId="wrong-owner",CurrencySpent=50}))
assert(data['u:888'].metrics.robux==7)
traitRoll=1
print("Traits/metrics passed: stacked variants, no fusion duplication, rejoin, playtime checkpoints and receipt retry deduplication")
local sortedUser={Parent=true,UserId=880,attrs={}}
function sortedUser:SetAttribute(k,v)self.attrs[k]=v end
function sortedUser:GetAttribute(k)return self.attrs[k]end
assert(Repository.load(sortedUser))
rewardSpecies={"ankylosaurus","raptor"}
assert(Repository.commitRunSettlement(sortedUser,"sorted-run",100,tags))
rewardSpecies=nil
local first,second=data['u:880'].eggs[1],data['u:880'].eggs[2]
assert(first.reward.speciesId=="raptor" and first.mutationId=="aurora")
assert(second.reward.speciesId=="ankylosaurus" and second.mutationId=="ember")
assert(not Repository.claimChest(sortedUser,second.eggId))
assert(Repository.claimChest(sortedUser,first.eggId))
Repository.release(sortedUser)
assert(Repository.load(sortedUser))
local ok,legend=Repository.claimChest(sortedUser,second.eggId)
assert(ok and legend.speciesId=="ankylosaurus" and sortedUser.attrs.RarestCaught==3)
assert(Repository.claimChest(sortedUser,second.eggId))
assert(data['u:880'].collection.ankylosaurus.variants[emberKey].count==2)
print("Ordering passed: low-to-high committed outcomes, matching event metadata, out-of-order rejection and no reroll across rejoin")
-- New economy behavior uses real rules and repository transactions, including repeated transforms.
local shopper={Parent=true,UserId=991,attrs={}}
function shopper:SetAttribute(k,v)self.attrs[k]=v end
function shopper:GetAttribute(k)return self.attrs[k]end
assert(Repository.load(shopper))
local wallet=Repository.progression(shopper)
assert(wallet.trails.white and shopper.attrs.AccountLevel==1)
assert(Repository.progressionAction(shopper,"grant","crystal","shop-fund",false,100))
assert(not Repository.progressionAction(shopper,"buyTrail","fern","locked-trail",false))
assert(wallet.accountXP==0)
assert(Repository.commitRunSettlement(shopper,"xp-run",400))
local balance=Repository.progression(shopper).crystals
assert(balance==650 and shopper.attrs.AccountLevel==3) -- 100 + capped 500 + 50 box
assert(Repository.commitRunSettlement(shopper,"xp-run",400))
assert(Repository.progression(shopper).crystals==balance and Repository.progression(shopper).accountXP==400)
assert(Repository.progressionAction(shopper,"buyTrail","fern","buy-fern",false))
assert(Repository.progressionAction(shopper,"buyTrail","fern","buy-fern",false))
assert(Repository.progression(shopper).crystals==550)
assert(Repository.progressionAction(shopper,"equipTrail","fern","equip-fern",false))
local growth,speed=Rules.multipliers(Repository.progression(shopper),"compy",nil,0,"dirty")
assert(math.abs(growth-.8)<1e-8 and math.abs(speed-.816)<1e-8)
assert(Repository.progressionAction(shopper,"upgradeCondition","1","policy-block",false)==false)
mutableConfig.DeveloperProducts={} -- No Robux-buyable currency: earned-only path.
assert(Repository.progressionAction(shopper,"upgradeCondition","1","condition-1",false))
assert(Repository.progressionAction(shopper,"upgradeCondition","1","condition-1",false))
assert(Repository.progression(shopper).conditionLevel==1 and Repository.progression(shopper).crystals==450)
local oldGenes=copy(data['u:991'].eggs[1].genes)
assert(oldGenes.conditionId==data['u:991'].eggs[1].genes.conditionId)
assert(Repository.progressionAction(shopper,"buyEgg","random","egg-buy-1",false))
local boughtId=data['u:991'].eggs[#data['u:991'].eggs].eggId
local queueCount=#data['u:991'].eggs
assert(Repository.progressionAction(shopper,"buyEgg","random","egg-buy-1",false))
assert(#data['u:991'].eggs==queueCount and Repository.progression(shopper).crystals==300)
assert(data['u:991'].eggs[1].genes.conditionId==oldGenes.conditionId)
Repository.release(shopper)
assert(Repository.load(shopper) and data['u:991'].eggs[#data['u:991'].eggs].eggId==boughtId)
for _,egg in copy(data['u:991'].eggs) do assert(Repository.claimChest(shopper,egg.eggId)) end
-- Force an already committed failed Cracked egg; replay/rejoin never creates a dinosaur.
Repository.release(shopper)
data['u:991'].eggs={{eggId="failed-cracked",readyAt=0,eventId="clear",mutationId="",reward={speciesId="ankylosaurus",count=3},genes={conditionId="cracked",hatchSuccess=false,primaryColorId="black",secondaryColorId="black",blend=100}}}
assert(Repository.load(shopper))
local beforeRarest=shopper.attrs.RarestCaught
local ok,failedEgg=Repository.claimChest(shopper,"failed-cracked")
assert(ok and failedEgg.failed and failedEgg.count==0 and shopper.attrs.LastChestFailed)
assert(shopper.attrs.RarestCaught==beforeRarest and next(data['u:991'].collection.ankylosaurus.variants)==nil)
assert(Repository.claimChest(shopper,"failed-cracked"))
Repository.release(shopper)
data['u:991'].eggs={}
for i=1,GameConfig.ChestQueueCapacity do table.insert(data['u:991'].eggs,{eggId="full-"..i,readyAt=0}) end
data['u:991'].pendingChestGrants=GameConfig.ChestOverflowCapacity
data['u:991'].pendingEggEvents={}
for i=1,GameConfig.ChestOverflowCapacity do table.insert(data['u:991'].pendingEggEvents,{eventId="clear",mutationId=""}) end
assert(Repository.load(shopper))
local beforeWallet=Repository.progression(shopper).crystals
local ok,reason=Repository.progressionAction(shopper,"buyEgg","random","full-purchase",false)
assert(not ok and reason=="queue_full" and Repository.progression(shopper).crystals==beforeWallet)
mutableConfig.DeveloperProducts={[456]=20}
shopper.attrs.PaidRandomEligible=true
assert(not Repository.progressionAction(shopper,"buyEgg","random","release-disabled",false))
mutableConfig.PaidRandomItemsEnabled=true
shopper.attrs.PaidRandomEligible=false
assert(not Repository.progressionAction(shopper,"upgradeCondition","2","restricted",false))
shopper.attrs.PaidRandomEligible=nil
assert(not Repository.progressionAction(shopper,"buyEgg","random","unknown-policy",false))
mutableConfig.PaidRandomItemsEnabled=false
print("Crystal shops passed: atomic run crystals/XP, duplicate settlement, level gates, ten-trail migration, condition debuffs, future-only odds, egg purchases/rejoin, failed hatches, queue-full rollback and fail-closed paid policy")
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
assert(data['u:123'].progression.crystals==before.progression.crystals)
game.GameId=0 services.RunService.IsStudio=function()return true end
local LocalRepository=REPO_MODULE
local localUser={Parent=true,UserId=999,attrs={}}
function localUser:SetAttribute(k,v)self.attrs[k]=v end
function localUser:GetAttribute(k)return self.attrs[k]end
local persistentCalls=transforms
assert(LocalRepository.load(localUser))
assert(localUser.attrs.StudioTestWallet==true and LocalRepository.progression(localUser).crystals==1000000)
assert(LocalRepository.progressionAction(localUser,"buyPotion","speed_legendary","test-purchase",false))
assert(LocalRepository.progression(localUser).crystals==1000000)
assert(LocalRepository.commitRunSettlement(localUser,"timer-local",10))
assert(localUser.attrs.ChestQueueJson[2].readyAt-localUser.attrs.ChestQueueJson[1].readyAt==0)
assert(transforms==persistentCalls and data['u:999']==nil)
LocalRepository.release(localUser)
-- A published Studio place still uses persistent storage and ordinary currency/timers.
game.GameId=1
local PublishedRepository=REPO_MODULE
local published={Parent=true,UserId=777,attrs={}}
function published:SetAttribute(k,v)self.attrs[k]=v end
function published:GetAttribute(k)return self.attrs[k]end
assert(PublishedRepository.load(published))
assert(published.attrs.StudioTestWallet==false and PublishedRepository.progression(published).crystals==0)
assert(data['u:777']~=nil)
print("Studio isolation passed: local test wallet replenishes, immediately ready eggs, zero persistent calls; published Studio retains normal wallet")
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
