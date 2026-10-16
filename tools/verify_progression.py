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
-- BD-391/405 Fast travel perk
do
 local q={} local qp=Rules.upgrade(q)
 assert(not Rules.hasPerk(qp,"fastTravel") and Rules.valid(qp) and qp.perks==nil,"old profile: nothing owned, no new field")
 assert(not Rules.apply(q,"buyPerk","fastTravel",100,false) and qp.crystals==0,"too poor")
 assert(not Rules.apply(q,"buyPerk","nope",100,false),"unknown perk")
 qp.crystals=ProgressionConfig.FastTravelPrice
 assert(Rules.apply(q,"buyPerk","fastTravel",100,false) and qp.crystals==0 and Rules.hasPerk(qp,"fastTravel") and Rules.valid(qp))
 assert(not Rules.apply(q,"buyPerk","fastTravel",100,false),"already owned")
 qp.perks.bogus=true assert(not Rules.valid(qp),"unknown perk key invalid")
end
assert(not Rules.apply(p,"equipAura","royal",100,false))
progress.potions.growth_common=2 -- purchases are covered by tools/verify_potion_shop.py
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
-- docs/68: 12-potion catalog; every potion is usable once owned, applies its buff kind, and buff kinds are validated.
assert(#ProgressionConfig.Potions==12)
for _,item in ProgressionConfig.Potions do
 local fresh={} local freshProgress=Rules.upgrade(fresh)
 freshProgress.potions[item.id]=1
 assert(Rules.valid(freshProgress) and Rules.apply(fresh,"usePotion",item.id,100,false) and freshProgress.buffs[item.kind].id==item.id and Rules.valid(freshProgress))
 local g,s,l=Rules.multipliers(freshProgress,"compy",nil,101)
 assert((if item.kind=="growth" then g elseif item.kind=="speed" then s else l)==item.multiplier,"buff applies "..item.id)
end
assert(not Rules.valid({crystals=0,auras={},potions={},equippedAura="",buffs={loot={id="speed_common",expiresAt=5}}}),"buff kind must match potion")
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
migrated.accountXP=193600 migrated.crystals=6200
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
mutableConfig.WriteBudgetEnabled=false -- BD-358: these offline tests run hundreds of claims in zero time; the write budget is proven in verify_multiplayer_sim
mutableConfig.DeveloperProducts={[456]=20} -- Mock product, never shipped in Config.
GameConfig=mutableConfig
local storage={Shared={Config="Config",ProgressionRules="Rules",EggTraits="EggTraits",EggGenetics="Genetics",NestQueue="NestQueue",FtueRules="FtueRules",ProgressionConfig="ProgressionConfig",SettingsModel="SettingsModel"}}
local datastores={GetDataStore=function()return store end}
local services={DataStoreService=datastores,HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function()return false end}}
local game={GameId=1,JobId="test",GetService=function(_,id)return services[id] end}
local task={wait=function()end,spawn=function()end}
local warn=function()end
local os={time=function()return 1700000030 end,clock=os.clock,date=os.date} -- fixed injected clock: shop window never rolls mid-test
local Identity=IDENTITY_MODULE
local script={Parent={DinosaurIdentity="Identity"}}
local require=function(id) assert(id=="Identity") return Identity end
local IdentityFusion=IDENTITY_FUSION_MODULE
local FusionOdds=FUSION_ODDS_MODULE
local PrivateStateStub={set=function(p,k,v) p.attrs[k]=v end,get=function(p,k) return p.attrs[k] end,forget=function() end} -- BD-360: the real module is tested by verify_private_state; here owner-only values land in attrs
local script={Parent={RewardMath="Rewards",DinosaurIdentity="Identity",IdentityFusion="IdentityFusion",FusionOdds="FusionOdds",PrivateState="PrivateState"}}
local rewardSpecies=nil
local NestQueue=NEST_QUEUE_MODULE
local FtueRules=FTUE_RULES_MODULE
local SettingsModel=SETTINGS_MODEL_MODULE
local Rewards=nil
local require=function(id)
 if id=="PrivateState" then return PrivateStateStub end
 if id=="FusionOdds" then return FusionOdds end
 if id=="IdentityFusion" then return IdentityFusion elseif id=="Identity" then return Identity elseif id=="Genetics" then return Genetics elseif id=="EggTraits" then return EggTraits elseif id=="ProgressionConfig" then return ProgressionConfig elseif id=="Config" then return GameConfig elseif id=="Rules" then return Rules elseif id=="Rewards" then return Rewards elseif id=="NestQueue" then return NestQueue elseif id=="FtueRules" then return FtueRules elseif id=="SettingsModel" then return SettingsModel end
 error("unexpected module "..tostring(id))
end
local traitRoll=1
local Random={new=function()return {NextNumber=function()return traitRoll end}end}
-- Real BD-044 RewardMath (egg count, crystals, nests, IDs); species rolls are fixture-controlled.
local RealRewards=REWARDS_MODULE
Rewards=setmetatable({computeChestReward=function()return {speciesId=if rewardSpecies then table.remove(rewardSpecies,1) else "raptor",count=1,mutationId="base"}end},{__index=RealRewards})
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
local conflict,conflictStatus=action("buyPotion","speed_common@0","buy1",false)
assert(not conflict and conflictStatus=="token_conflict")
for g=1,3 do assert(action("grant","crystal","shop-grant"..g,false,100)) end
local shopWindow=Rules.shopWindow(os.time())
local shopOffer=Rules.shopOffers(shopWindow)[1]
local shopItem=Rules.item(ProgressionConfig.Potions,shopOffer.id)
local shopId=shopOffer.id.."@"..shopWindow
assert(action("buyPotion",shopId,"potion1",false))
assert(action("usePotion",shopOffer.id,"use1",false))
assert(action("usePotion",shopOffer.id,"use1",false))
assert(Repository.progression(player).potions[shopOffer.id]==0)
local expiry=Repository.progression(player).buffs[shopItem.kind].expiresAt
Repository.release(player)
assert(Repository.load(player))
assert(Repository.progression(player).crystals==440-shopItem.price and Repository.progression(player).auras.meadow)
assert(Repository.progression(player).buffs[shopItem.kind].expiresAt==expiry)
-- BD-051: stock is per player per window, survives reconnect, and every purchase is idempotent by token.
do
 local shopState=Repository.progression(player).shop
 assert(shopState.window==shopWindow and shopState.bought[shopOffer.id]==1)
 local crystalsBefore=Repository.progression(player).crystals
 local dupOk,dupStatus=action("buyPotion",shopId,"potion1",false)
 assert(dupOk and dupStatus=="duplicate" and Repository.progression(player).crystals==crystalsBefore)
 assert(Repository.progression(player).shop.bought[shopOffer.id]==1)
 local stale,staleStatus=action("buyPotion",shopOffer.id.."@"..(shopWindow-1),"stale1",false)
 assert(not stale and staleStatus=="stale_window")
 local bare,bareStatus=action("buyPotion",shopOffer.id,"bare1",false)
 assert(not bare and bareStatus=="window_required")
 local extra=0
 for i=1,shopOffer.stock+1 do
  local bought,why=action("buyPotion",shopId,"stock"..i,false)
  if bought then extra+=1 else assert(why=="sold_out") end
 end
 assert(extra==shopOffer.stock-1 and Repository.progression(player).shop.bought[shopOffer.id]==shopOffer.stock)
 local out,outStatus=action("buyPotion",shopId,"stock-final",false)
 assert(not out and outStatus=="sold_out")
 Repository.release(player)
 assert(Repository.load(player))
 local soldAfterRejoin,soldStatus=action("buyPotion",shopId,"stock-rejoin",false)
 assert(not soldAfterRejoin and soldStatus=="sold_out")
 assert(Repository.progression(player).shop.bought[shopOffer.id]==shopOffer.stock)
 print("Potion shop transactions passed: idempotent token, stale window, bare id, sold out, reconnect keeps stock")
end
Repository.release(player)
-- Historical v1 balances survive additive catalog and Diamond migration.
for i,id in GameConfig.SpeciesOrder do if i>3 then data['u:123'].collection[id]=nil end end
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
print("Migration/fusion passed: preserved v1 balances, 22 catalog entries, exact costs, idempotency and immediately ready new eggs")
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
assert(Repository.commitRunSettlement(eventUser,"event-run",2,tags))
assert(Repository.commitRunSettlement(eventUser,"event-run",2,tags))
-- BD-044: the 2 catches bank exactly 2 run eggs; the one beyond the 5-slot queue waits in the bank.
assert(#data['u:888'].eggs==5 and data['u:888'].pendingChestGrants==0 and #data['u:888'].runEggBank==1)
assert(data['u:888'].eggs[5].mutationId=="ember" and data['u:888'].runEggBank[1].mutationId=="aurora")
Repository.release(eventUser)
data['u:888'].eggs[5].readyAt=1
local emberId=data['u:888'].eggs[5].eggId
assert(Repository.load(eventUser))
assert(not Repository.claimChest(eventUser,emberId))
for i=1,4 do assert(Repository.claimChest(eventUser,"fixture-"..i)) end
local claimed,reward=Repository.claimChest(eventUser,emberId)
assert(claimed and reward.eventMutationId=="ember")
assert(Repository.claimChest(eventUser,emberId))
assert(data['u:888'].collection.raptor.variants[emberKey].count==1 and data['u:888'].collection.raptor.base==4)
assert(data['u:888'].pendingChestGrants==0 and #data['u:888'].runEggBank==0)
-- BD-044 hatch page: the next queued run egg (aurora) committed in the same transaction and waits to be revealed.
assert(#data['u:888'].eggs==0 and eventUser.attrs.NextChestId==data['u:888'].recentOperations[#data['u:888'].recentOperations].outcome.eggId)
assert(Repository.equipSpecies(eventUser,"raptor") and eventUser.attrs.EquippedEventMutation=="aurora")
assert(not Repository.commitRunSettlement(eventUser,"bad-event",10,{{eventId="volcano",mutationId="frost"}}))
Repository.release(eventUser)
assert(Repository.load(eventUser) and eventUser.attrs.EquippedEventMutation=="aurora")
print("Event transactions passed: repeated settlement transforms, overflow FIFO, mutated hatch, no Base duplication, duplicate claim, equip and rejoin")
traitRoll=0
local stackedTags=copy(tags) for _,tag in stackedTags do tag.shiny=true tag.big=true end
assert(Repository.commitRunSettlement(eventUser,"stacked-traits",2,stackedTags))
local stackedId=data['u:888'].eggs[1].eggId
local success,stacked=Repository.claimChest(eventUser,stackedId)
assert(success and stacked.shiny and stacked.big)
assert(Repository.claimChest(eventUser,stackedId))
assert(data['u:888'].collection.raptor.variants[EggTraits.key("ember",true,true,genes)].count==1)
assert(data['u:888'].collection.raptor.variants[emberKey].count==1 and data['u:888'].collection.raptor.base==4)
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
assert(Repository.commitRunSettlement(sortedUser,"sorted-run",2,tags))
rewardSpecies=nil
local first,second=data['u:880'].eggs[1],data['u:880'].eggs[2]
assert(first.reward.speciesId=="raptor" and first.mutationId=="aurora")
assert(second.reward.speciesId=="ankylosaurus" and second.mutationId=="ember")
assert(not Repository.claimChest(sortedUser,second.eggId))
assert(Repository.claimChest(sortedUser,first.eggId))
Repository.release(sortedUser)
assert(Repository.load(sortedUser))
local ok,legend=Repository.claimChest(sortedUser,second.eggId)
assert(ok and legend.speciesId=="ankylosaurus" and sortedUser.attrs.RarestCaught==4)
assert(Repository.claimChest(sortedUser,second.eggId))
assert(data['u:880'].collection.ankylosaurus.variants[emberKey].count==1)
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
-- BD-044/165: 600 catches clamp to the 50-egg run cap; XP = 10 per run egg; deterministic PROVISIONAL crystals.
local bankCapacity=mutableConfig.RunEggBankCapacity mutableConfig.RunEggBankCapacity=100 -- small bank so the full-bank gate is reachable
assert(Repository.commitRunSettlement(shopper,"xp-run",600))
assert(Repository.progression(shopper).crystals==373 and shopper.attrs.AccountLevel>=2) -- 100 + 273
assert(Repository.commitRunSettlement(shopper,"xp-run-2",10))
local balance=Repository.progression(shopper).crystals
assert(balance==434 and shopper.attrs.AccountLevel>=3) -- + 61
assert(Repository.commitRunSettlement(shopper,"xp-run",600))
assert(Repository.progression(shopper).crystals==balance and Repository.progression(shopper).accountXP==600)
assert(#data['u:991'].eggs==5 and #data['u:991'].runEggBank==55 and #(data['u:991'].eggNests or {})==0,"no run time given -> no nest")
assert(shopper.attrs.RunStartBlocked=="egg_bank_full" and shopper.attrs.BankedRunEggCount==55)
-- Fixture reset so the purchase checks below start from an empty queue.
mutableConfig.RunEggBankCapacity=bankCapacity
Repository.release(shopper)
data['u:991'].eggs={} data['u:991'].runEggBank={} data['u:991'].eggNests={}
assert(Repository.load(shopper) and shopper.attrs.RunStartBlocked=="")
assert(Repository.commitRunSettlement(shopper,"genes-run",1)) -- one queued egg (7 crystals at 7.5/egg)
assert(#data['u:991'].eggs==1 and data['u:991'].eggs[1].traitRollVersion=="bd045-genes-v2")
assert(Repository.progressionAction(shopper,"buyTrail","fern","buy-fern",false))
assert(Repository.progressionAction(shopper,"buyTrail","fern","buy-fern",false))
assert(Repository.progression(shopper).crystals==341)
assert(Repository.progressionAction(shopper,"equipTrail","fern","equip-fern",false))
local growth,speed=Rules.multipliers(Repository.progression(shopper),"compy",nil,0)
assert(math.abs(growth-1)<1e-8 and math.abs(speed-1.02)<1e-8) -- BD-185: stored egg condition never changes dino stats
do -- BD-181/185: a legacy dino conditionId (profile, dino or extra argument) is ignored by stat code
  local base={Rules.multipliers(Repository.progression(shopper),"compy",nil,0)}
  for _,id in {"cracked","dirty","normal","rainbow","astra"} do
    local legacy=table.clone(Repository.progression(shopper)) legacy.conditionId=id legacy.equippedCondition=id
    legacy.dinosaurs={{instanceId="legacy",speciesId="compy",genes={conditionId=id}}}
    local got={(Rules.multipliers :: any)(legacy,"compy",nil,0,nil,id)}
    for i=1,#base do assert(math.abs(got[i]-base[i])<1e-12,"legacy dino condition "..id.." changed stat "..i) end
  end
  assert(data['u:991'].eggs[1].genes.conditionId~=nil,"egg condition stays on the egg")
end
assert(Repository.progressionAction(shopper,"upgradeCondition","1","policy-block",false)==false)
mutableConfig.DeveloperProducts={} -- No Robux-buyable currency: earned-only path.
assert(Repository.progressionAction(shopper,"upgradeCondition","1","condition-1",false))
assert(Repository.progressionAction(shopper,"upgradeCondition","1","condition-1",false))
assert(Repository.progression(shopper).conditionLevel==1 and Repository.progression(shopper).crystals==241)
local oldGenes=copy(data['u:991'].eggs[1].genes)
assert(oldGenes.conditionId==data['u:991'].eggs[1].genes.conditionId)
assert(Repository.progressionAction(shopper,"buyEgg","random","egg-buy-1",false))
local boughtId=data['u:991'].eggs[#data['u:991'].eggs].eggId
local queueCount=#data['u:991'].eggs
assert(Repository.progressionAction(shopper,"buyEgg","random","egg-buy-1",false))
assert(#data['u:991'].eggs==queueCount and Repository.progression(shopper).crystals==91)
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
local failed,failedStatus=action("buyPotion",shopId,"outage",false)
assert(not failed and failedStatus=="save_failed")
assert(data['u:123'].progression.crystals==before.progression.crystals)
assert(player:GetAttribute("ProfileState")=="SaveFailed")
fail=false
Repository.release(player)
assert(Repository.load(player))
data['u:123'].session.leaseId="other"
local lost,lostStatus=action("buyPotion",shopId,"lease",false)
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
assert(LocalRepository.progressionAction(localUser,"buyPotion",shopId,"test-purchase",false))
assert(LocalRepository.progression(localUser).crystals==1000000)
assert(LocalRepository.commitRunSettlement(localUser,"timer-local",10))
assert(localUser.attrs.ChestQueueJson[2].readyAt-localUser.attrs.ChestQueueJson[1].readyAt==0)
assert(transforms==persistentCalls and data['u:999']==nil)
local chestId = localUser.attrs.ChestQueueJson[1].id
local claimed, hatch = LocalRepository.claimChest(localUser, chestId)
assert(claimed and #hatch.instanceIds == 1) -- BD-044: exactly one dinosaur identity per hatched egg
local first = LocalRepository.dinosaurDetails(localUser, hatch.instanceIds[1])
assert(first.origin.kind == "hatch" and first.originalEgg.eggId == chestId)
assert(first.originalEgg.source.kind == "run" and first.originalEgg.source.originalEggId == chestId)
first.originalEgg.eventId = "tampered"
assert(LocalRepository.dinosaurDetails(localUser, hatch.instanceIds[1]).originalEgg.eventId ~= "tampered")
local replayed, replay = LocalRepository.claimChest(localUser, chestId)
assert(replayed and replay.instanceIds[1] == hatch.instanceIds[1])
LocalRepository.release(localUser)
assert(LocalRepository.load(localUser))
assert(LocalRepository.dinosaurDetails(localUser, hatch.instanceIds[1]).originalEgg.eggId == chestId)
assert(LocalRepository.dinosaurDetails(localUser, "u:999/d:1").origin.kind == "legacy_unknown")
assert(transforms==persistentCalls and data['u:999']==nil)
-- BD-057 Phase 1: fusion through the real repository, memory profiles only.
local function claimAll(user, repo)
 local ids={}
 for _,chest in user.attrs.ChestQueueJson or {} do
  local ok,h=repo.claimChest(user,chest.id)
  if ok and h.instanceIds then for _,id in h.instanceIds do table.insert(ids,id) end end
 end
 return ids
end
local byBucket={}
local donors=nil
-- Gold = 6 Base donors of one species (any pattern; owner decision 2026-10-15), taken here from one bucket.
for round=1,200 do
 assert(LocalRepository.commitRunSettlement(localUser,"fusion-run-"..round,10))
 for _,id in claimAll(localUser,LocalRepository) do
  local d=LocalRepository.dinosaurDetails(localUser,id)
  byBucket[d.bucketKey]=byBucket[d.bucketKey] or {}
  table.insert(byBucket[d.bucketKey],id)
 end
 for key,list in byBucket do if #list>=6 and string.find(key,"/variant/") and not donors then donors={table.unpack(list,1,6)} end end
 if donors then break end
end
assert(donors,"expected 6 same-bucket hatched donors")
local donorDetails=LocalRepository.dinosaurDetails(localUser,donors[1])
assert(donorDetails.traitsKnown and donorDetails.genes.patternId~=nil)
local fusionSpecies=donorDetails.speciesId
local function goldCount() return localUser.attrs.CollectionJson[fusionSpecies].gold end -- mock JSONEncode returns a table copy
-- Default-off flag: no quote, no fusion.
assert(GameConfig.IdentityFusionPreviewEnabled==false)
assert(select(2,LocalRepository.quoteFusion(localUser,"gold",donors))=="fusion_disabled")
assert(select(3,LocalRepository.fuseDinosaurs(localUser,{token="off"}))=="fusion_disabled")
assert(LocalRepository.setFusionTestRoller({})==false)
mutableConfig.IdentityFusionPreviewEnabled=true
local quote=assert(LocalRepository.quoteFusion(localUser,"gold",donors))
assert(quote.consentRequired==(donorDetails.shiny or donorDetails.big or donorDetails.mutationId~=""))
local request={token="repo-fuse-1",targetStage="gold",donorIds=donors,quoteDigest=quote.quoteDigest,consentDigest=quote.consentDigest}
-- The production PROVISIONAL roller quotes exact odds; an invalid injected roller is
-- refused before any write.
assert(quote.oddsVersion=="fusion-odds-provisional-v2" and quote.odds.shiny==(if donorDetails.shiny then 0.5 else 0))
assert(LocalRepository.setFusionTestRoller({}))
local okNoOdds,_,noOdds=LocalRepository.fuseDinosaurs(localUser,request)
assert(not okNoOdds and noOdds=="odds_not_approved" and LocalRepository.dinosaurDetails(localUser,donors[1]))
local rolls=0
assert(LocalRepository.setFusionTestRoller({version="repo-test-v1",roll=function(_,patternId)
 rolls+=1
 -- Controlled test outcome: schema-valid genes with a distinguishable blend, no odds.
 local g=table.clone(donorDetails.genes) g.patternId=patternId g.conditionId=nil g.blend=(g.blend+37)%100
 return {big=false,shiny=false,mutationId="",genes=g}
end}))
-- Client-supplied stale digest and wrong-owner IDs are refused.
local staleRequest=table.clone(request) staleRequest.quoteDigest="stale"
assert(select(3,LocalRepository.fuseDinosaurs(localUser,staleRequest))=="stale_quote")
local foreign=table.clone(donors) foreign[6]="u:123/d:1"
assert(select(2,LocalRepository.quoteFusion(localUser,"gold",foreign))=="wrong_owner")
assert(select(3,LocalRepository.fuseDinosaurs(localUser,{token=string.rep("x",81)}))=="invalid_token")
-- Write outage: every attempt fails at the memory write; nothing is consumed.
local realEncode=http.JSONEncode
local encodes=0
http.JSONEncode=function(self,v) encodes+=1 if encodes%2==0 then error("injected write failure") end return realEncode(self,v) end
local okOutage,_,outage=LocalRepository.fuseDinosaurs(localUser,request)
http.JSONEncode=realEncode
assert(not okOutage and outage=="save_failed" and localUser.attrs.ProfileState=="SaveFailed")
LocalRepository.release(localUser)
assert(LocalRepository.load(localUser))
for _,id in donors do assert(LocalRepository.dinosaurDetails(localUser,id)) end
-- Lease lost mid-transaction: rejected, nothing consumed.
local realDecode=http.JSONDecode
http.JSONDecode=function(self,v) local r=realDecode(self,v) if type(r)=="table" and r.session then r.session.leaseId="other-server" end return r end
local okLease,_,lease=LocalRepository.fuseDinosaurs(localUser,request)
http.JSONDecode=realDecode
assert(not okLease and lease=="lease_lost" and localUser.attrs.ProfileState=="LeaseLost")
LocalRepository.release(localUser)
assert(LocalRepository.load(localUser))
for _,id in donors do assert(LocalRepository.dinosaurDetails(localUser,id)) end
-- Success: one new Gold, donors consumed, grouped projection synced.
local goldBefore=goldCount()
rolls=0
local fusedOk,committed,fusedStatus=LocalRepository.fuseDinosaurs(localUser,request)
assert(fusedOk and fusedStatus=="fused" and rolls==1,tostring(fusedStatus))
assert(goldCount()==goldBefore+1)
for _,id in donors do assert(LocalRepository.dinosaurDetails(localUser,id)==nil) end
local gold=assert(LocalRepository.dinosaurDetails(localUser,committed.resultId))
assert(gold.stage=="gold" and gold.origin.kind=="fusion" and gold.genes.blend==(donorDetails.genes.blend+37)%100)
assert(gold.genes.patternId==donorDetails.genes.patternId and next(gold.cosmetics.ownedAuraIds)==nil)
assert(#gold.lineage.parentIds==6 and next(gold.lineage.parentEggs)~=nil)
for _,egg in gold.lineage.parentEggs do assert(egg.genes.patternId==donorDetails.genes.patternId) end
assert(gold.genes.conditionId==nil,"fused dinosaur stores no condition")
for _,egg in gold.lineage.parentEggs do assert(egg.genes.conditionId~=nil,"parent egg condition stays retrievable") end
-- Duplicate confirm: same result, no reroll, no second consumption.
local dupOk,dupResult,dupStatus=LocalRepository.fuseDinosaurs(localUser,request)
assert(dupOk and dupStatus=="duplicate" and dupResult.resultId==committed.resultId and rolls==1 and goldCount()==goldBefore+1)
local conflictRequest=table.clone(request) conflictRequest.donorIds=table.clone(donors) conflictRequest.donorIds[1]=gold.instanceId
assert(select(3,LocalRepository.fuseDinosaurs(localUser,conflictRequest))=="token_conflict")
-- A second fusion reusing consumed donors fails cleanly.
local reuse=table.clone(request) reuse.token="repo-fuse-2"
assert(select(3,LocalRepository.fuseDinosaurs(localUser,reuse))=="donor_missing")
-- Reload keeps the result, lineage and replay.
LocalRepository.release(localUser)
assert(LocalRepository.load(localUser))
local reloaded=assert(LocalRepository.dinosaurDetails(localUser,committed.resultId))
assert(reloaded.origin.operationId=="fusion:repo-fuse-1" and #reloaded.lineage.parentIds==6)
local replayOk,replayResult,replayStatus=LocalRepository.fuseDinosaurs(localUser,request)
assert(replayOk and replayStatus=="duplicate" and replayResult.resultId==committed.resultId and rolls==1)
assert(transforms==persistentCalls and data['u:999']==nil)
print("Repository fusion passed: default-off flag, no-odds refusal, stale/foreign/invalid requests, write outage and lease loss rollback, one new Gold with lineage, duplicate confirm, token conflict, reload and zero persistent calls")
LocalRepository.release(localUser)
-- A published Studio place still uses persistent storage and ordinary currency/timers.
game.GameId=1
local PublishedRepository=REPO_MODULE
local published={Parent=true,UserId=777,attrs={}}
function published:SetAttribute(k,v)self.attrs[k]=v end
function published:GetAttribute(k)return self.attrs[k]end
assert(PublishedRepository.load(published))
assert(published.attrs.StudioTestWallet==false and PublishedRepository.progression(published).crystals==0)
assert(data['u:777']~=nil and data['u:777'].dinosaurIdentity==nil)
assert(PublishedRepository.setFusionTestRoller({version="x",roll=function()end})==false)
assert(select(2,PublishedRepository.quoteFusion(published,"gold",{}))=="fusion_disabled")
assert(select(3,PublishedRepository.fuseDinosaurs(published,{token="published"}))=="fusion_disabled")
mutableConfig.IdentityFusionPreviewEnabled=false
print("Studio isolation passed: local test wallet replenishes, immediately ready eggs, zero persistent calls; published Studio retains normal wallet")
-- ===== BD-064: persistent identity mode (Milestone 1 playtest flag) =====
-- Own function scope: the main chunk is close to the 200-local register limit.
;(function()
assert(GameConfig.IdentityPersistentEnabled==false,"committed default must stay off")
assert(GameConfig.IdentityFusionPreviewEnabled==false)
mutableConfig.IdentityPersistentEnabled=true
mutableConfig.IdentityFusionPreviewEnabled=true
game.GameId=1 services.RunService.IsStudio=function()return false end
local PersistentRepository=REPO_MODULE
local function newUser(id)
 local u={Parent=true,UserId=id,Name="P"..id,attrs={}}
 function u:SetAttribute(k,v)self.attrs[k]=v end
 function u:GetAttribute(k)return self.attrs[k]end
 return u
end
local KEY="u:4242"
-- BD-044 hatch pages: reveal any committed page entries (no write), then claim the real queue head (one transaction).
local function claimHead(u)
 while u.attrs.NextChestId~="" and u.attrs.NextChestId~=u.attrs.ChestQueueJson[1].id do assert(PersistentRepository.claimChest(u,u.attrs.NextChestId)) end
 return PersistentRepository.claimChest(u,u.attrs.ChestQueueJson[1].id)
end
local pu=newUser(4242)
local callsBefore=transforms
-- Fresh profile: sidecar created in the same load transform.
assert(PersistentRepository.load(pu) and pu.attrs.ProfileMode=="Persistent")
assert(transforms>callsBefore,"persistent store used")
local sidecar=data[KEY].dinosaurIdentity
assert(sidecar and sidecar.ownerKey==KEY and sidecar.suspendedReason==nil and sidecar.nextId==2)
assert(sidecar.instances[KEY.."/d:1"].origin.kind=="legacy_unknown")
assert(PersistentRepository.fusionStatus(pu))
-- Hatches credit identities in the persisted sidecar (same UpdateAsync transform).
traitRoll=0.5
local hatched={}
for round=1,20 do
 assert(PersistentRepository.commitRunSettlement(pu,"persist-run-"..round,10))
 for _,chest in pu.attrs.ChestQueueJson do
  local ok,h=PersistentRepository.claimChest(pu,chest.id)
  assert(ok and #h.instanceIds==1,"hatch credited one identity (BD-044)")
  for _,id in h.instanceIds do table.insert(hatched,id) end
 end
end
assert(#hatched==100) -- BD-044: 5 queued eggs claimed per 10-egg run, one identity each
for _,id in hatched do
 local stored=data[KEY].dinosaurIdentity.instances[id]
 assert(stored and stored.origin.kind=="hatch" and data[KEY].dinosaurIdentity.eggs[stored.origin.eggId])
end
local donors={table.unpack(hatched,1,6)}
local donors2={table.unpack(hatched,7,12)}
local quote=assert(PersistentRepository.quoteFusion(pu,"gold",donors))
assert(quote.oddsVersion=="fusion-odds-provisional-v2" and quote.odds.primaryColor[quote.summary.colors[1].primaryColorId]==1)
local request={token="persist-1",targetStage="gold",donorIds=donors,quoteDigest=quote.quoteDigest,consentDigest=quote.consentDigest}
local function donorsIntact(list) for _,id in list do if not data[KEY].dinosaurIdentity.instances[id] then return false end end return true end
-- Outage: nothing consumed, ProfileState SaveFailed; recover by reload.
fail=true
local okO,_,outage=PersistentRepository.fuseDinosaurs(pu,request)
fail=false
assert(not okO and outage=="save_failed" and pu.attrs.ProfileState=="SaveFailed" and donorsIntact(donors))
PersistentRepository.release(pu) assert(PersistentRepository.load(pu))
-- Lease loss: another server owns the session; nothing consumed.
local lease=data[KEY].session.leaseId
data[KEY].session.leaseId="other-server"
local okL,_,lost=PersistentRepository.fuseDinosaurs(pu,request)
assert(not okL and lost=="lease_lost" and pu.attrs.ProfileState=="LeaseLost" and donorsIntact(donors))
data[KEY].session.leaseId=lease
PersistentRepository.release(pu) assert(PersistentRepository.load(pu))
-- Whole-profile byte preflight: a fusion that would exceed the budget is rejected.
local budget=mutableConfig.IdentityFusionProfileBudgetBytes
mutableConfig.IdentityFusionProfileBudgetBytes=math.floor(IdentityFusion.encodedSize(data[KEY])/2) -- below the post-fusion size (6 donors shrink the sidecar a little)
local okB,_,bytes=PersistentRepository.fuseDinosaurs(pu,request)
mutableConfig.IdentityFusionProfileBudgetBytes=budget
assert(not okB and bytes=="storage_limit" and donorsIntact(donors) and pu.attrs.ProfileState=="Loaded")
assert(data[KEY].dinosaurIdentity.fusions==nil)
-- Success with the production PROVISIONAL roller (mocked Random): deterministic traits.
local goldBefore=data[KEY].collection.raptor.gold
local okF,committed,status=PersistentRepository.fuseDinosaurs(pu,request)
assert(okF and status=="fused" and committed.oddsVersion=="fusion-odds-provisional-v2",tostring(status))
assert(data[KEY].collection.raptor.gold==goldBefore+1)
for _,id in donors do assert(data[KEY].dinosaurIdentity.instances[id]==nil) end
local stored=data[KEY].dinosaurIdentity.instances[committed.resultId]
assert(stored and stored.stage=="gold" and stored.origin.oddsVersion=="fusion-odds-provisional-v2")
assert(stored.genes.hatchSuccess==true and stored.genes.patternId==quote.patternId and stored.shiny==false)
assert(data[KEY].dinosaurIdentity.fusions["fusion:persist-1"].outcome.resultId==committed.resultId)
local dupOk,dup,dupStatus=PersistentRepository.fuseDinosaurs(pu,request)
assert(dupOk and dupStatus=="duplicate" and dup.resultId==committed.resultId and data[KEY].collection.raptor.gold==goldBefore+1)
-- Reload: result, lineage and replay survive in the persistent store.
PersistentRepository.release(pu)
assert(PersistentRepository.load(pu))
local reloaded=assert(PersistentRepository.dinosaurDetails(pu,committed.resultId))
assert(reloaded.lineage and #reloaded.lineage.parentIds==6 and next(reloaded.lineage.parentEggs)~=nil)
assert(select(3,PersistentRepository.fuseDinosaurs(pu,request))=="duplicate")
-- Reconcile failure (over the 3,000-identity guard) suspends identity, never deletes it,
-- and keeps the profile writable; recovering the grouped counts resumes identity.
local compyBase=data[KEY].collection.compy.base
data[KEY].collection.compy.base=3500
assert(PersistentRepository.renew(pu) and pu.attrs.ProfileState=="Loaded")
assert(data[KEY].dinosaurIdentity.suspendedReason=="identity_capacity")
assert(data[KEY].dinosaurIdentity.instances[committed.resultId],"fused result kept while suspended")
assert(select(2,PersistentRepository.fusionStatus(pu))=="identity_unavailable")
assert(select(2,PersistentRepository.quoteFusion(pu,"gold",donors2))=="identity_unavailable")
assert(select(3,PersistentRepository.fuseDinosaurs(pu,{token="suspended",targetStage="gold",donorIds=donors2,quoteDigest="x"}))=="identity_unavailable")
-- A hatch while suspended still credits the grouped collection and skips identities.
assert(PersistentRepository.commitRunSettlement(pu,"persist-suspended",10))
local okS,hs=claimHead(pu)
assert(okS and hs.instanceIds==nil and data[KEY].dinosaurIdentity.suspendedReason=="identity_capacity")
data[KEY].collection.compy.base=compyBase
assert(PersistentRepository.renew(pu))
assert(data[KEY].dinosaurIdentity.suspendedReason==nil and data[KEY].dinosaurIdentity.instances[committed.resultId])
assert(claimHead(pu))
assert(PersistentRepository.fusionStatus(pu))
-- Hard byte ceiling: identity growth is dropped (suspended) before the profile write is,
-- and a write that is still too large aborts with the stored profile unchanged.
local hard=mutableConfig.IdentityProfileHardLimitBytes
assert(PersistentRepository.commitRunSettlement(pu,"persist-hard",10))
local sizeBefore=IdentityFusion.encodedSize(data[KEY])
mutableConfig.IdentityProfileHardLimitBytes=sizeBefore+200
local hatchesBefore=data[KEY].dinosaurIdentity.nextId
local okH,hh=claimHead(pu)
assert(okH and data[KEY].dinosaurIdentity.suspendedReason=="storage_limit" and data[KEY].dinosaurIdentity.nextId==hatchesBefore)
assert(IdentityFusion.encodedSize(data[KEY])<=sizeBefore+200)
mutableConfig.IdentityProfileHardLimitBytes=1000
local frozen=IdentityFusion.encodedSize(data[KEY])
assert(not PersistentRepository.renew(pu) and IdentityFusion.encodedSize(data[KEY])==frozen)
mutableConfig.IdentityProfileHardLimitBytes=hard
PersistentRepository.release(pu) assert(PersistentRepository.load(pu))
assert(data[KEY].dinosaurIdentity.suspendedReason==nil,"identity resumes under the ceiling")
-- Legacy profiles keep loading: over capacity -> no sidecar, identity features closed.
local legacy=newUser(5151)
data['u:5151']=copy(data[KEY]) data['u:5151'].session=nil data['u:5151'].dinosaurIdentity=nil
data['u:5151'].collection.compy.base=5000
assert(PersistentRepository.load(legacy) and legacy.attrs.ProfileState=="Loaded")
assert(data['u:5151'].dinosaurIdentity==nil and data['u:5151'].collection.compy.base==5000)
assert(select(2,PersistentRepository.fusionStatus(legacy))=="identity_unavailable")
assert(PersistentRepository.commitRunSettlement(legacy,"legacy-run",10),"legacy profile still writable")
PersistentRepository.release(legacy)
-- Legacy profile under capacity migrates on first load (fresh playtest stores have none).
local small=newUser(5252)
data['u:5252']=copy(data['u:5151']) data['u:5252'].collection.compy.base=3 data['u:5252'].eggs={} data['u:5252'].pendingChestGrants=0 data['u:5252'].pendingEggEvents=nil
assert(PersistentRepository.load(small) and data['u:5252'].dinosaurIdentity.ownerKey=="u:5252")
-- Paid-random gate: a profile that spent Robux needs the release gate + policy check.
data['u:5252'].metrics.robux=100
PersistentRepository.release(small) assert(PersistentRepository.load(small))
assert(select(2,PersistentRepository.fusionStatus(small))=="random_items_unavailable")
PersistentRepository.release(small)
print("Persistent identity passed: fresh sidecar, hatch credit, outage/lease-loss/byte-preflight rollback, provisional-odds fusion, duplicate, reload with lineage, capacity suspension without deletion, hard byte ceiling, legacy over-capacity login, paid-random gate")

-- ===== FusionService (FusionAction RemoteFunction) with mocked remotes =====
local folderChildren={}
local remoteFolder={}
function remoteFolder:FindFirstChild(n) return folderChildren[n] end
local fusionStorage={Shared={Config="Config"},BeDinoRemotes=remoteFolder}
function fusionStorage:FindFirstChild(n) return if n=="BeDinoRemotes" then remoteFolder else nil end
local removing=nil
local fusionPlayers={PlayerRemoving={Connect=function(_,fn) removing=fn end}}
local game={GetService=function(_,id) return ({Players=fusionPlayers,ReplicatedStorage=fusionStorage})[id] end}
local Instance={new=function(kind)
 local o={ClassName=kind}
 function o:IsA(k) return k==kind end
 return setmetatable(o,{__newindex=function(t,k,v) rawset(t,k,v) if k=="Parent" and v==remoteFolder then folderChildren[t.Name]=t end end})
end}
local require=function(id) assert(id=="Config") return GameConfig end
local FusionService=FUSION_SERVICE_MODULE
assert(FusionService.handle(pu,{action="list"}).reason=="fusion_disabled","not started")
local remote=FusionService.start(PersistentRepository)
assert(folderChildren.FusionAction==remote and remote.ClassName=="RemoteFunction" and type(remote.OnServerInvoke)=="function")
local now=0
FusionService.setClock(function() return now end)
local function invoke(...) now+=1000 return remote.OnServerInvoke(pu,...) end -- fresh window per call
assert(PersistentRepository.load(pu))
-- Contract keys.
local function keys(t) local r={} for k in t do table.insert(r,k) end table.sort(r) return table.concat(r,",") end
local list=invoke({action="list",limit=200}) -- 6-donor Gold leaves more than the default page of 100 owned dinos
assert(list.ok and #list.dinosaurs>=10 and list.nextCursor==nil)
local prev=0
for _,d in list.dinosaurs do
 local seq=tonumber(string.match(d.instanceId,"/d:(%d+)$")) assert(seq>prev) prev=seq
 -- genes is nil only for legacy copies whose DNA was never saved (plain buckets).
 assert(d.genes~=nil or d.originKind=="legacy_unknown")
 local withGenes=table.clone(d) withGenes.genes=withGenes.genes or {}
 assert(keys(withGenes)=="auraCount,big,equippedAuraId,equippedTrailId,favorited,genes,instanceId,locked,mutationId,originKind,shiny,speciesId,stage,trailCount")
end
local page1=invoke({action="list",limit=3})
assert(#page1.dinosaurs==3 and page1.nextCursor)
local page2=invoke({action="list",limit=3,cursor=page1.nextCursor})
assert(page2.dinosaurs[1].instanceId==list.dinosaurs[4].instanceId)
local details=invoke({action="details",instanceId=donors2[1]})
assert(details.ok and details.dinosaur.instanceId==donors2[1] and details.dinosaur.originalEgg)
local fusedDetails=invoke({action="details",instanceId=committed.resultId})
assert(fusedDetails.ok and fusedDetails.dinosaur.lineage)
assert(invoke({action="details",instanceId="u:1/d:1"}).reason=="donor_missing")
local q=invoke({action="quote",targetStage="gold",donorIds=donors2})
assert(q.ok and keys(q)=="ok,quote")
assert(keys(q.quote)=="consentDigest,consentRequired,donorIds,lossManifest,odds,oddsVersion,patternId,quoteDigest,recipeVersion,speciesId,targetStage")
assert(keys(q.quote.odds)=="big,mutation,noMutation,primaryColor,secondaryColor,shiny")
assert(q.quote.oddsVersion=="fusion-odds-provisional-v2" and q.quote.odds.noMutation==1)
local foreignIds=table.clone(donors2) foreignIds[1]="u:1/d:1"
assert(invoke({action="quote",targetStage="gold",donorIds=foreignIds}).reason=="wrong_owner")
assert(invoke({action="quote",targetStage="emerald",donorIds=donors2}).reason=="wrong_donor_count") -- Emerald is approved: 3 Gold, not 6 Base
assert(invoke({action="quote",targetStage="platinum",donorIds=donors2}).reason=="unknown_stage")
assert(invoke({action="quote",targetStage="gold",donorIds=table.move(donors2,1,5,1,{})}).reason=="wrong_donor_count")
local fuseReq={action="fuse",token="remote-1",targetStage="gold",donorIds=donors2,quoteDigest=q.quote.quoteDigest,consentDigest=q.quote.consentDigest}
assert(invoke({action="fuse",token="remote-0",targetStage="gold",donorIds=donors2,quoteDigest="stale"}).reason=="stale_quote")
local fused=invoke(fuseReq)
assert(fused.ok and fused.status=="fused" and keys(fused)=="ok,result,status")
assert(keys(fused.result)=="oddsVersion,patternId,resultId,speciesId,targetStage,traits")
assert(keys(fused.result.traits)=="big,genes,mutationId,shiny" and fused.result.oddsVersion=="fusion-odds-provisional-v2")
local again=invoke(fuseReq)
assert(again.ok and again.status=="duplicate" and again.result.resultId==fused.result.resultId)
local reuse=table.clone(fuseReq) reuse.token="remote-2"
assert(invoke(reuse).reason=="donor_missing")
-- Client-supplied traits/odds/result IDs are not part of the contract.
local forged=table.clone(fuseReq) forged.token="remote-3" forged.traits={shiny=true}
assert(invoke(forged).reason=="bad_request")
local forgedId=table.clone(fuseReq) forgedId.resultId="u:4242/d:1"
assert(invoke(forgedId).reason=="bad_request")
-- Argument fuzzing: every malformed shape is bad_request and never throws.
local badRequests={1,"list",true,{},{action=5},{action="nope"},{action="list",cursor=-1},{action="list",cursor=1.5},
 {action="list",cursor=0/0},{action="list",limit=0},{action="list",limit=201},{action="list",limit="5"},{action="list",extra=1},
 {action="details"},{action="details",instanceId=""},{action="details",instanceId=string.rep("x",121)},{action="details",instanceId=7},
 {action="quote",targetStage="gold"},{action="quote",targetStage="gold",donorIds={}},{action="quote",targetStage=1,donorIds=donors2},
 {action="quote",targetStage="gold",donorIds={a="u:4242/d:2"}},{action="quote",targetStage="gold",donorIds={1,2}},
 {action="quote",targetStage="gold",donorIds={[1]="u:4242/d:2",[3]="u:4242/d:3"}},
 {action="quote",targetStage=string.rep("g",17),donorIds=donors2},
 {action="fuse",targetStage="gold",donorIds=donors2,quoteDigest="d"},{action="fuse",token="",targetStage="gold",donorIds=donors2,quoteDigest="d"},
 {action="fuse",token=string.rep("t",81),targetStage="gold",donorIds=donors2,quoteDigest="d"},
 {action="fuse",token="t",targetStage="gold",donorIds=donors2},{action="fuse",token="t",targetStage="gold",donorIds=donors2,quoteDigest="d",consentDigest=5},
 {[1]="list"},{action="list",[2]=true}}
local tooMany={} for i=1,7 do tooMany[i]="u:4242/d:"..i end -- one above the largest recipe (6)
table.insert(badRequests,{action="quote",targetStage="gold",donorIds=tooMany})
assert(invoke(nil).reason=="bad_request" and invoke().reason=="bad_request")
for i=1,#badRequests do
 local response=invoke(badRequests[i])
 assert(type(response)=="table" and response.ok==false and response.reason=="bad_request","bad request "..i)
end
assert(invoke({action="list"},"extra").reason=="bad_request","extra remote arguments")
math.randomseed(64)
local pool={true,false,0,-1,1.5,2^60,0/0,"","gold","list","details","quote","fuse",string.rep("z",300),{}, {1,2,3},{a=1},donors2}
local fields={"action","cursor","limit","instanceId","targetStage","donorIds","token","quoteDigest","consentDigest","traits"}
for _=1,2000 do
 local request={}
 for _,field in fields do if math.random()<0.5 then request[field]=pool[math.random(1,#pool)] end end
 local ok,response=pcall(invoke,request)
 assert(ok and type(response)=="table" and type(response.ok)=="boolean")
 assert(response.ok==false or request.action=="list" or request.action=="details" or request.action=="quote","fuzzed fuse must not succeed")
end
-- Per-player rate limit (PROVISIONAL Config: requests per window).
FusionService.setClock(function() return now end)
now=0
local limit=mutableConfig.FusionRequestsPerWindow
for i=1,limit do assert(remote.OnServerInvoke(pu,{action="list",limit=1}).ok,"within limit "..i) end
assert(remote.OnServerInvoke(pu,{action="list",limit=1}).reason=="rate_limited")
assert(remote.OnServerInvoke(pu,"garbage").reason=="rate_limited","malformed requests also count")
local other=newUser(6161)
assert(remote.OnServerInvoke(other,{action="list"}).reason~="rate_limited","limit is per player")
now=mutableConfig.FusionRateWindowSeconds
assert(remote.OnServerInvoke(pu,{action="list",limit=1}).ok,"window resets")
removing(pu)
-- Disabled flag: every action answers fusion_disabled.
mutableConfig.IdentityFusionPreviewEnabled=false
now+=1000
assert(remote.OnServerInvoke(pu,{action="list"}).reason=="fusion_disabled")
assert(remote.OnServerInvoke(pu,{action="quote",targetStage="gold",donorIds=donors2}).reason=="fusion_disabled")
PersistentRepository.release(pu)
mutableConfig.IdentityPersistentEnabled=false
print("FusionService passed: FusionAction RemoteFunction contract keys, sorted paging, details/lineage, quote odds, fuse/duplicate/reuse, forged traits/IDs refused, 2,000 fuzzed requests, per-player rate limit and disabled flag")
end)()
print("Profile transactions passed: repeated transforms, duplicate grants/purchases/use, token conflicts, rejoin, outage rollback and lease loss")
'''
 s+=r"""
local script={Parent={ProgressionConfig="ProgressionConfig"}}
local require=function()return ProgressionConfig end
local Clock=CLOCK_MODULE
local choiceCount=0
local function choose()choiceCount+=1 return ProgressionConfig.Weather[2]end
local clock=Clock.new(100)
assert(not Clock.step(clock,399,choose) and choiceCount==0 and clock.current==nil)
assert(Clock.step(clock,400,choose) and choiceCount==1 and clock.endsAt==580)
assert(not Clock.step(clock,579,choose) and choiceCount==1)
assert(Clock.step(clock,580,choose) and clock.current==nil and clock.nextAt==880)
assert(Clock.step(clock,880,choose) and choiceCount==2)
print("Weather clock passed: hidden choice until start, 300s clear interval, 180s event and end cleanup")
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
local warnings=0
local warn=function() warnings+=1 end
local workspace={Terrain={},BeDinoArena={},Gravity=250,GetAttribute=function()return nil end,GetServerTimeNow=function()return leapNow end,Blockcast=function()return if blocked then {} else nil end}
local storage={Shared={ProgressionConfig=true},BeDinoRemotes={}}
local game={GetService=function(_,id)return ({Players={PlayerRemoving=removal},ReplicatedStorage=storage,RunService={Heartbeat=heartbeat}})[id]end}
local require=function()return ProgressionConfig end
CFrame.new=function(p)return {Position=p}end
local Leap=LEAP_MODULE
local h={Health=100,FloorMaterial="grass",WalkSpeed=22,ChangeState=function()end}
local home=vec(0,5,0)
local function cf(pos)return {LookVector=vec(0,0,-1),Position=pos}end
local root={Parent=true,Position=home,Size=vec(2,2,1),CFrame=cf(home),AssemblyLinearVelocity=vec(0,0,0)}
local ownerChanges=0
function root:IsA(id)return id=="BasePart"end
function root:SetNetworkOwner(_)ownerChanges+=1 end
function root:SetNetworkOwnershipAuto()ownerChanges+=1 end
local c={attrs={RunState="Active"}}
function c:GetAttribute(k)return self.attrs[k]end
function c:SetAttribute(k,v)self.attrs[k]=v end
function c:FindFirstChild(k)return if k=="HumanoidRootPart" then root else nil end
function c:FindFirstChildOfClass(k)return if k=="Humanoid" then h else nil end
local user={Name="Tester",UserId=777,Character=c,attrs={ProfileState="Loaded",MovementSecurityStatus="OK"}}
function user:GetAttribute(k)return self.attrs[k]end
function user:SetAttribute(k,v)self.attrs[k]=v end
-- Pure envelope: a leap that follows the launch numbers is valid; every kind of cheat is named.
local cfg=ProgressionConfig
local start=vec(0,5,0)
assert(Leap.violation(cfg,250,start,vec(0,9,-40),vec(0,10,-70),.6)==nil,"honest leap")
assert(Leap.violation(cfg,250,start,vec(0,9,-400),vec(0,10,-70),.6)=="distance","too far")
assert(Leap.violation(cfg,250,start,vec(0,200,-20),vec(0,10,-70),.6)=="height","too high")
assert(Leap.violation(cfg,250,start,vec(0,9,-40),vec(0,10,-400),.6)=="speed","too fast")
assert(Leap.violation(cfg,250,start,vec(0,9,-40),vec(0,500,-70),.6)=="lift","too much lift")
assert(Leap.violation(cfg,250,start,vec(0,5,-50),vec(0,0,-70),0)=="distance","teleport at takeoff")
Leap.start()
local activate=remotes.RequestLeap.OnServerEvent.fn
activate(user,"bad") assert(user.attrs.LeapReadyAt==nil)
activate(user) assert(user.attrs.LeapReadyAt==60 and user.attrs.LastLeapStatus=="leaping" and ownerChanges==0 and c.attrs.MovementSpeedLimit==cfg.LeapHorizontalSpeed)
assert(root.AssemblyLinearVelocity.Y==0,"server must not set velocity: the client owns the leap")
leapNow=.4 activate(user) assert(user.attrs.LeapReadyAt==60)
-- an honest client path inside the envelope keeps the leap alive and updates the last valid position
leapNow=.2 root.Position=vec(0,9,-14) root.CFrame=cf(vec(0,9,-14)) root.AssemblyLinearVelocity=vec(0,10,-70) heartbeat.fn()
assert(user.attrs.LeapRejectCount==nil and user.attrs.LastLeapStatus=="leaping")
leapNow=.8 heartbeat.fn() assert(c.attrs.LeapUntil==0 and c.attrs.MovementSpeedLimit==nil and ownerChanges==0)
-- cheat: a client that teleports far away mid-leap is rolled back with a 30 s penalty and a warning
root.Position=home root.CFrame=cf(home) root.AssemblyLinearVelocity=vec(0,0,0)
leapNow=60 activate(user) assert(user.attrs.LeapReadyAt==120)
leapNow=60.2 root.Position=vec(0,9,-500) root.CFrame=cf(vec(0,9,-500)) root.AssemblyLinearVelocity=vec(0,10,-70) heartbeat.fn()
assert(user.attrs.LeapRejectCount==1 and user.attrs.LastLeapStatus=="rejected" and warnings==1 and user.attrs.LeapReadyAt==150)
assert(root.CFrame.Position.Z==0 and root.CFrame.Position.Y==5,"rolled back to the last valid position (the takeoff spot)")
assert(root.AssemblyLinearVelocity.Magnitude==0 and c.attrs.LeapUntil==0)
-- cheat: leaping through a wall is rolled back too
root.Position=vec(0,5,0) root.CFrame=cf(vec(0,5,0))
leapNow=150 activate(user) assert(user.attrs.LeapReadyAt==210)
blocked=true leapNow=150.2 root.Position=vec(0,9,-14) root.CFrame=cf(vec(0,9,-14)) heartbeat.fn() blocked=false
assert(user.attrs.LeapRejectCount==2 and user.attrs.LastLeapStatus=="rejected")
leapNow=240 blocked=true activate(user) assert(user.attrs.LastLeapStatus=="blocked" and user.attrs.LeapReadyAt==240,"a wall right ahead refuses the leap and costs no extra cooldown (240 = 210 + the 30 s penalty already served)")
blocked=false
leapNow=300 h.FloorMaterial="air" local before=user.attrs.LeapReadyAt activate(user) assert(user.attrs.LeapReadyAt==before,"no leap from the air")
print("Leap handler passed: client-owned leap (no ownership change, no server velocity), envelope distance/height/speed/lift, wall rollback, 30s penalty, cooldown and air rejection")
"""
 return s.replace('FTUE_RULES_MODULE',module('src/shared/FtueRules.luau')).replace('FUSION_ODDS_MODULE',module('src/server/FusionOdds.luau')).replace('FUSION_SERVICE_MODULE',module('src/server/FusionService.luau')).replace('IDENTITY_FUSION_MODULE',module('src/server/IdentityFusion.luau')).replace('IDENTITY_MODULE',module('src/server/DinosaurIdentity.luau')).replace('NEST_QUEUE_MODULE',module('src/shared/NestQueue.luau')).replace('SETTINGS_MODEL_MODULE',module('src/shared/SettingsModel.luau')).replace('REWARDS_MODULE',module('src/server/RewardMath.luau')).replace('REPO_MODULE',module('src/server/ProfileRepository.luau')).replace('CLOCK_MODULE',module('src/shared/WeatherClock.luau')).replace('LEAP_MODULE',module('src/server/LeapService.luau'))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/'progression.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
