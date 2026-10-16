"""BD-044/BD-045 reward-loop verification in pinned Luau.

Executes the real RewardMath, FoodCatchRules, EggGenetics, EggTraits, ProgressionRules,
DinosaurIdentity and ProfileRepository against a mocked DataStore that replays every
UpdateAsync transform (probe + commit), injects outages and lease loss, and simulates
reconnects. Mocks validate transaction logic only, not Studio replication or UI.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


HARNESS = r'''
local ProgressionConfig=@@PROGRESSION_CONFIG@@
local GameConfig=@@GAME_CONFIG@@
local script={Parent={Config="Config"}}
local require=function(_) return GameConfig end
local FoodCatchRules=@@FOOD_RULES@@
local script={Parent={ProgressionConfig="ProgressionConfig"}}
local require=function(_) return ProgressionConfig end
local Genetics=@@GENETICS@@
local script={Parent={Config="Config",EggGenetics="Genetics"}}
local require=function(id) return if id=="Genetics" then Genetics else GameConfig end
local EggTraits=@@EGG_TRAITS@@
local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}
local require=function(id) return if id=="Genetics" then Genetics else ProgressionConfig end
local Rules=@@RULES@@

local function copy(t)
 if type(t)~="table" then return t end
 local result={} for k,v in t do result[k]=copy(v) end return result
end
local function same(a,b)
 if type(a)~=type(b) then return false end
 if type(a)~="table" then return a==b end
 for k,v in a do if not same(v,b[k]) then return false end end
 for k in b do if a[k]==nil then return false end end
 return true
end
-- Deterministic server-seeded PRNG (Park-Miller); every Random.new() gets its own stream.
local seedCounter=1
local Random={new=function()
 seedCounter+=7919
 local state=seedCounter%2147483646+1
 local function nextValue() state=(state*48271)%2147483647 return (state-1)/2147483646 end
 return {NextNumber=function(_,low,high) local v=nextValue() if low then return low+v*(high-low) end return v end}
end}

local data={}
local failMode=nil -- nil | "all" | "once"
local transforms=0
local store={UpdateAsync=function(_,key,fn)
 if failMode=="all" then error("injected outage") end
 if failMode=="once" then failMode=nil error("injected transient outage") end
 transforms+=1
 -- Roblox may run a transform more than once; only the final result commits.
 local probe=copy(data[key]) fn(probe)
 local updated=fn(copy(data[key]))
 if updated==nil then return nil end
 data[key]=copy(updated)
 -- "ack_lost": the write commits but the caller sees an error (lost response) and retries.
 if failMode=="ack_lost" then failMode=nil error("injected lost acknowledgement") end
 return copy(updated)
end}
local http={GenerateGUID=function() return "guid-"..tostring(math.random(1,1e9)) end,JSONEncode=function(_,v) return copy(v) end,JSONDecode=function(_,v) return copy(v) end}
local mutableConfig=table.clone(GameConfig)
mutableConfig.WriteBudgetEnabled=false -- BD-358: these offline tests run hundreds of claims in zero time; the write budget is proven in verify_multiplayer_sim
GameConfig=mutableConfig
local storage={Shared={Config="Config",ProgressionRules="Rules",EggTraits="EggTraits",EggGenetics="Genetics",NestQueue="NestQueue",FtueRules="FtueRules",ProgressionConfig="ProgressionConfig",SettingsModel="SettingsModel"}}
local services={DataStoreService={GetDataStore=function() return store end},HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function() return false end}}
local game={GameId=1,JobId="test",GetService=function(_,id) return services[id] end}
local task={wait=function() end,spawn=function() end}
local warn=function() end
local script={Parent={}}
local require=function(id)
 if id=="Config" then return GameConfig elseif id=="ProgressionConfig" then return ProgressionConfig end
 error("unexpected module "..tostring(id))
end
local NestQueue=@@NEST_QUEUE@@
local FtueRules=@@FTUE_RULES@@
local SettingsModel=@@SETTINGS_MODEL@@
local Rewards=@@REWARD_MATH@@
local Identity=@@IDENTITY_MODULE@@
local script={Parent={DinosaurIdentity="Identity"}}
local require=function(id) assert(id=="Identity") return Identity end
local IdentityFusion=@@IDENTITY_FUSION_MODULE@@
local script={Parent={Config="Config"}}
local require=function(id) if id=="Identity" then return Identity end return GameConfig end
local FusionOdds=@@FUSION_ODDS@@
local PrivateStateStub={set=function(p,k,v) p.attrs[k]=v end,get=function(p,k) return p.attrs[k] end,forget=function() end} -- BD-360: the real module is tested by verify_private_state; here owner-only values land in attrs
local script={Parent={RewardMath="Rewards",DinosaurIdentity="Identity",IdentityFusion="IdentityFusion",FusionOdds="FusionOdds",PrivateState="PrivateState"}}
local require=function(id)
 if id=="PrivateState" then return PrivateStateStub end
 if id=="FusionOdds" then return FusionOdds end
 if id=="IdentityFusion" then return IdentityFusion elseif id=="Identity" then return Identity elseif id=="Genetics" then return Genetics
 elseif id=="EggTraits" then return EggTraits elseif id=="ProgressionConfig" then return ProgressionConfig elseif id=="Config" then return GameConfig
 elseif id=="Rules" then return Rules elseif id=="Rewards" then return Rewards elseif id=="NestQueue" then return NestQueue elseif id=="FtueRules" then return FtueRules elseif id=="SettingsModel" then return SettingsModel end
 error("unexpected module "..tostring(id))
end
local Repository=@@REPO_MODULE@@

local function user(id)
 local u={Parent=true,UserId=id,attrs={}}
 function u:SetAttribute(k,v) self.attrs[k]=v end
 function u:GetAttribute(k) return self.attrs[k] end
 return u
end
local function key(u) return "u:"..tostring(u.UserId) end
local function bankCount(u) return #(data[key(u)].runEggBank or {}) end
local function totalCopies(profile)
 local n=0
 for _,entry in profile.collection do
  n+=entry.base
  for _,count in entry.events or {} do n+=count end
  for _,variant in entry.variants or {} do n+=variant.count end
 end
 return n
end
-- Reveal order = queue then bank (what the player will hatch, in order).
local function revealLine(u)
 local line={}
 for _,egg in data[key(u)].eggs do table.insert(line,egg) end
 for _,egg in data[key(u)].runEggBank or {} do table.insert(line,egg) end
 return line
end

------------------------------------------------------------------ RewardMath
assert(Rewards.runEggCount(0)==0 and Rewards.runEggCount(-5)==0 and Rewards.runEggCount(0/0)==0)
assert(Rewards.runEggCount(-math.huge)==0 and Rewards.runEggCount(math.huge)==GameConfig.RunEggMaxPerRun)
assert(GameConfig.RunEggMaxPerRun==50 and Rewards.runEggCount(1e308)==50 and Rewards.runEggCount(51)==50 and Rewards.runEggCount(50)==50)
assert(Rewards.runEggCount("15")==0 and Rewards.runEggCount(nil)==0 and Rewards.runEggCount(14.7)==14)
assert(Rewards.runEggCount(40)==40 and Rewards.runEggCount(400)==50)
local catches,carry=FoodCatchRules.award(500,0,1)
assert(catches==4 and Rewards.runEggCount(catches)==4,"500 food -> 4 run eggs")
catches=FoodCatchRules.award(5000,0,1)
assert(catches==40 and Rewards.runEggCount(catches)==40,"5,000 food -> 40 run eggs")
assert(Rewards.runCrystals(0)==0 and Rewards.runCrystals(4)==30 and Rewards.runCrystals(40)==220 and Rewards.runCrystals(50)==273)
assert(Rewards.runCrystals(0/0)==0 and Rewards.runCrystals(-1)==0 and Rewards.runCrystals(math.huge)==273)
assert(Rewards.nestCount(4)==0 and Rewards.nestCount(40)==0,"no run time -> never a nest")
assert(Rewards.nestCount(0,600)==0 and Rewards.nestCount(1,119)==0 and Rewards.nestCount(1,120)==1)
assert(Rewards.nestCount(4,200)==1 and Rewards.nestCount(11,200)==2 and Rewards.nestCount(40,200)==GameConfig.NestMaxPerRun)
assert(Rewards.nestCount(50,200)==GameConfig.NestMaxPerRun and Rewards.nestCount(math.huge,math.huge)==GameConfig.NestMaxPerRun)
assert(Rewards.nestCount(4,0/0)==0 and Rewards.nestCount(4,"200")==0 and Rewards.nestCount(4,-5)==0)
local zero=Rewards.computeRunReward(0/0)
assert(zero.eggCount==0 and zero.crystals==0 and zero.nestCount==0 and zero.accountXP==0)
local previous=-1
for n=0,50 do local c=Rewards.runCrystals(n) assert(c>=previous) previous=c end
assert(#Rewards.runEggId(string.rep("x",64),50)<=80 and #(Rewards.nestId(string.rep("x",64),11)..":3")<=80)
print("Reward math passed: 0/negative/NaN/inf/huge/non-number scores, 500->4 and 5,000->40 eggs, 30/220 crystals, hidden nest gate (run time + catches) with capped extras, bounded IDs")

------------------------------------------------------------------ 4-egg run (500 food)
local now=os.time()
local a=user(101)
assert(Repository.load(a))
local beforeCopies=totalCopies(data[key(a)])
local ok,outcome,status=Repository.commitRunSettlement(a,"run-4",4,nil,200)
assert(ok and status=="committed" and outcome.eggCount==4 and outcome.crystals==30 and outcome.nestCount==1)
assert(totalCopies(data[key(a)])==beforeCopies,"settlement must not grant direct dinosaur copies")
assert(#data[key(a)].eggs==4 and bankCount(a)==0 and data[key(a)].pendingChestGrants==0)
assert(data[key(a)].progression.crystals==30 and data[key(a)].progression.accountXP==40)
local aNest=data[key(a)].eggNests[1]
assert(#data[key(a)].eggNests==1 and aNest.state=="incubating" and aNest.readyAt>=now+GameConfig.NestIncubationSeconds and aNest.eggs==nil)
assert(aNest.size>=GameConfig.NestMinSize and aNest.size<=GameConfig.NestMaxSize and aNest.luck==1 and aNest.droppedFromRun=="run-4")
local ids={}
local lastRarity=0
for _,egg in revealLine(a) do
 assert(not ids[egg.eggId]) ids[egg.eggId]=true
 assert(string.match(egg.eggId,"^run:run%-4:%d+$") and egg.reward.count==1 and egg.kind=="run_egg")
 assert(Genetics.valid(egg.genes) and egg.traitRollVersion=="bd045-genes-v2" and egg.source.kind=="run")
 local rarity=GameConfig.SpeciesRarities[egg.reward.speciesId]
 assert(rarity>=lastRarity,"run batch must reveal in increasing rarity") lastRarity=rarity
end
assert(a.attrs.LastRewardText=="4 eggs + 1 nest" and a.attrs.LastRunCrystals==30 and a.attrs.LastRunCrystalBox==0)
assert(a.attrs.BankedRunEggCount==0 and a.attrs.QueuedEggsWaiting==0 and a.attrs.RunStartBlocked=="")
-- Exactly once: replays (cached and uncached) change nothing.
local snapshot=copy(data[key(a)])
local dupOk,_,dupStatus=Repository.commitRunSettlement(a,"run-4",40)
assert(dupOk and dupStatus=="duplicate" and same(snapshot,data[key(a)]))
Repository.release(a) assert(Repository.load(a))
snapshot=copy(data[key(a)])
dupOk,_,dupStatus=Repository.commitRunSettlement(a,"run-4",40)
assert(dupOk and dupStatus=="duplicate" and same(snapshot,data[key(a)]),"replay with a different score must not re-settle")
print("4-egg run passed: 4 queued eggs (500 food), no direct copies, 30 crystals, 1 incubating nest, ascending rarity, exactly-once replays")

-- Bulk-path stress tests below use run sizes far above the new per-run cap (BD-165), so lift the cap here.
GameConfig.RunEggMaxPerRun=500
------------------------------------------------------------------ 150-egg run, reveal, reconnect
local b=user(102)
assert(Repository.load(b))
local copiesBefore=totalCopies(data[key(b)])
assert(Repository.commitRunSettlement(b,"run-400",400,nil,600))
assert(#data[key(b)].eggs==5 and bankCount(b)==395)
assert(#data[key(b)].eggNests==GameConfig.NestMaxPerRun and #b.attrs.NestsJson==GameConfig.NestMaxPerRun and data[key(b)].progression.crystals==Rewards.runCrystals(400))
assert(data[key(b)].eggNests[1].state=="incubating" and data[key(b)].eggNests[2].state=="waiting")
local line=revealLine(b)
assert(#line==400)
local committedIds={} for i,egg in line do committedIds[i]=egg.eggId end
local committedGenes={} for i,egg in line do committedGenes[i]=copy(egg.genes) end
local byId={} for _,egg in line do byId[egg.eggId]=egg end
local expectedSuccess=0 for _,g in committedGenes do if g.hatchSuccess then expectedSuccess+=1 end end
local successes,failures,revealed=0,0,0
local claimTransforms=transforms
-- Client behaviour: reveal whatever NextChestId names, one egg per call (~1 s apart in game).
local function revealNext(u)
 local id=u.attrs.NextChestId
 local egg=byId[id]
 local claimOk,result,claimStatus=Repository.claimChest(u,id)
 assert(claimOk and claimStatus=="claimed",tostring(claimStatus))
 if result.failed then
  assert(result.count==0 and egg.genes.conditionId=="cracked","only Cracked eggs fail and they give 0 dinosaurs")
  failures+=1
 else
  assert(result.count==1,"exactly one dinosaur per successful egg") successes+=1
 end
 revealed+=1
 return egg
end
lastRarity=0
for i=1,42 do
 local egg=revealNext(b)
 assert(egg.eggId==committedIds[i] and same(egg.genes,committedGenes[i]),"reveal order or genes changed")
 local rarity=GameConfig.SpeciesRarities[egg.reward.speciesId]
 assert(rarity>=lastRarity) lastRarity=rarity
end
-- 5 pages of 10 are committed (50 eggs credited); the 8 unrevealed page eggs are already credited.
local pageSize=GameConfig.HatchPageSize assert(pageSize==10)
assert(#data[key(b)].eggs==5 and bankCount(b)==345 and transforms-claimTransforms<=2*5,"one claim transaction per hatch page")
local copiesMid=totalCopies(data[key(b)])
local again,_,againStatus=Repository.claimChest(b,committedIds[42])
assert(again and againStatus=="duplicate" and totalCopies(data[key(b)])==copiesMid)
-- Reconnect mid-page: nothing is re-hatched or lost; only the 8 pending animations are skipped.
Repository.release(b)
assert(Repository.load(b))
assert(b.attrs.NextChestId==committedIds[51] and totalCopies(data[key(b)])==copiesMid)
line=revealLine(b)
assert(#line==350)
for i,egg in line do assert(egg.eggId==committedIds[50+i] and same(egg.genes,committedGenes[50+i])) end
for i=51,400 do
 local egg=revealNext(b)
 assert(egg.eggId==committedIds[i])
 local rarity=GameConfig.SpeciesRarities[egg.reward.speciesId]
 assert(rarity>=lastRarity) lastRarity=rarity
end
assert(revealed==392 and #data[key(b)].eggs==0 and bankCount(b)==0)
assert(totalCopies(data[key(b)])==copiesBefore+expectedSuccess,"one dinosaur per successful egg, none for failures, none lost by the reconnect")
assert(failures>0,"expected some failed Cracked eggs at BD-045 tier 0")
local claimRequests=transforms-claimTransforms
assert(claimRequests<=2*40+2,"400 eggs must need ~40 claim transactions, got "..claimRequests)
-- Replaying settlement after 150 claims trimmed it out of recentOperations is still a no-op.
local found=false for _,entry in data[key(b)].recentOperations do if entry.id=="run:run-150" then found=true end end
assert(not found,"fixture expects the run operation to be trimmed")
snapshot=copy(data[key(b)])
dupOk,_,dupStatus=Repository.commitRunSettlement(b,"run-400",400)
assert(dupOk and dupStatus=="duplicate" and same(snapshot,data[key(b)]),"settledRuns ledger must block re-settlement")
print(string.format("400-egg run passed: 400 eggs credited in 40 hatch-page transactions (%d transforms incl. probes), revealed in committed ascending order, reconnect mid-page loses no credit; %d hatched total, trimmed-ledger replay blocked", claimRequests, expectedSuccess))

------------------------------------------------------------------ Conservation across hatch pages, leave and rejoin
-- settled == credited + queued + banked, where "credited" is judged from collection growth and
-- committed egg outcomes (not from reveal counts), at every step including a leave mid-page.
do
 local u=user(110)
 assert(Repository.load(u))
 local before=totalCopies(data[key(u)])
 assert(Repository.commitRunSettlement(u,"conserve",150))
 local all={} for _,egg in revealLine(u) do all[egg.eggId]=egg end
 assert(#revealLine(u)==150)
 local function check(label)
  local live={}
  for _,egg in revealLine(u) do assert(not live[egg.eggId],"duplicate live egg "..label) live[egg.eggId]=true end
  local credited,successes=0,0
  for id,egg in all do
   if not live[id] then credited+=1 if egg.genes.hatchSuccess then successes+=1 end end
  end
  assert(credited+#revealLine(u)==150,"conservation "..label)
  assert(totalCopies(data[key(u)])==before+successes,"collection growth != credited successes "..label)
  return credited
 end
 check("settled")
 for i=1,37 do assert(Repository.claimChest(u,u.attrs.NextChestId)) end
 local creditedMid=check("mid-page")
 assert(creditedMid==40 and Repository.pendingReveals(u)==3,"37 revealed, page of 40 credited, 3 buffered: "..creditedMid)
 Repository.release(u) -- leave with 3 credited-but-unrevealed eggs
 assert(Repository.pendingReveals(u)==0)
 assert(Repository.load(u))
 assert(check("after rejoin")==40,"rejoin must neither re-credit nor drop the buffered eggs")
 -- A stale client id for an already-credited egg is a harmless duplicate or unknown, never a second credit.
 local copies=totalCopies(data[key(u)])
 for id,egg in all do
  if not string.find(id,"nope") and #revealLine(u)>0 then
   local okStale,_,stale=Repository.claimChest(u,id)
   assert(totalCopies(data[key(u)])==copies,"stale id must not credit "..tostring(stale))
   break
  end
 end
 while u.attrs.NextChestId~="" do assert(Repository.claimChest(u,u.attrs.NextChestId)) end
 assert(check("drained")==150 and #revealLine(u)==0)
end
print("Conservation passed: settled == credited + queued + banked at settlement, mid-page, after leave/rejoin with 3 buffered eggs, and fully drained; stale ids never double-credit")

------------------------------------------------------------------ Outage, transient failure, lease loss
local c=user(103)
assert(Repository.load(c))
snapshot=copy(data[key(c)])
failMode="all"
local failed,_,failedStatus=Repository.commitRunSettlement(c,"outage-run",40)
failMode=nil
assert(not failed and failedStatus=="save_failed" and same(snapshot,data[key(c)]),"outage must not partially write")
-- Recovery = rejoin after the outage; the same run then settles.
Repository.release(c) assert(Repository.load(c))
failMode="once"
local retried,_,retriedStatus=Repository.commitRunSettlement(c,"outage-run",40)
assert(retried and retriedStatus=="committed" and #revealLine(c)==40,"transient outage retried inside the repository")
assert(data[key(c)].progression.crystals==Rewards.runCrystals(40))
assert(select(3,Repository.commitRunSettlement(c,"outage-run",40))=="duplicate" and #revealLine(c)==40)
-- Lost acknowledgement: the first write commits, the retry finds it and reports duplicate.
failMode="ack_lost"
local acked,_,ackStatus=Repository.commitRunSettlement(c,"ack-run",40)
assert(acked and ackStatus=="duplicate" and #revealLine(c)==80 and data[key(c)].progression.crystals==2*Rewards.runCrystals(40),"lost ack must not double-settle")
data[key(c)].session.leaseId="other-server"
snapshot=copy(data[key(c)])
local lost,_,lostStatus=Repository.commitRunSettlement(c,"lease-run",40)
assert(not lost and lostStatus=="lease_lost" and same(snapshot,data[key(c)]) and c.attrs.ProfileState=="LeaseLost")
local lostClaim,_,lostClaimStatus=Repository.claimChest(c,data[key(c)].eggs[1].eggId)
assert(not lostClaim and lostClaimStatus=="profile_not_loaded" and same(snapshot,data[key(c)]))
-- The new owner (session freed) settles the same run exactly once.
data[key(c)].session=nil
Repository.release(c)
assert(Repository.load(c))
assert(Repository.commitRunSettlement(c,"lease-run",40) and #revealLine(c)==120)
assert(select(3,Repository.commitRunSettlement(c,"lease-run",40))=="duplicate" and #revealLine(c)==120)
print("Failure handling passed: full outage writes nothing, transient outage commits once, lost acknowledgement retried as duplicate, lease loss blocks settlement/claims, retry after recovery is exactly-once")

-- Nest queue, storage, drop gate, luck and migration: tools/verify_nests.py (same harness).

------------------------------------------------------------------ Legacy save compatibility
local l=user(105)
assert(Repository.load(l))
Repository.release(l)
local legacy=data[key(l)]
legacy.runEggBank=nil legacy.nests=nil legacy.pendingNests=nil legacy.settledRuns=nil
legacy.eggs={}
for i=1,5 do table.insert(legacy.eggs,{eggId="legacy-"..i,kind="alpha_chest",readyAt=0,eventId="clear",mutationId="",reward={speciesId="triceratops",count=3}}) end
legacy.pendingChestGrants=2
legacy.pendingEggEvents={{eventId="clear",mutationId="",reward={speciesId="stegosaurus",count=2}},{eventId="clear",mutationId=""}}
table.insert(legacy.recentOperations,{id="run:old-build020-run",kind="run",outcome={rewardConfigVersion=1,catchScore=12,stacks={{speciesId="compy",mutationId="base",count=12}},chestCount=1,crystals=24}})
assert(Repository.load(l),"Build 020 save without BD-044 fields must load")
assert(select(3,Repository.commitRunSettlement(l,"old-build020-run",12))=="duplicate","legacy run replay blocked")
assert(Repository.commitRunSettlement(l,"new-run",3))
assert(#data[key(l)].eggs==5 and data[key(l)].pendingChestGrants==2 and bankCount(l)==3,"new eggs wait behind legacy overflow")
local tri=data[key(l)].collection.triceratops.base
for i=1,5 do
 local claimOk,result=Repository.claimChest(l,data[key(l)].eggs[1].eggId)
 assert(claimOk and result.speciesId=="triceratops" and result.count==3,"legacy queued eggs keep their committed 3 copies")
end
assert(data[key(l)].collection.triceratops.base==tri+15)
local claimOk,result=Repository.claimChest(l,data[key(l)].eggs[1].eggId)
assert(claimOk and result.speciesId=="stegosaurus" and result.count==2)
claimOk,result=Repository.claimChest(l,data[key(l)].eggs[1].eggId)
assert(claimOk and result.count==1,"legacy metadata without a reward rolls once with the new 1-dinosaur rule")
assert(data[key(l)].pendingChestGrants==0 and #data[key(l)].eggs==3 and bankCount(l)==0)
for _,egg in data[key(l)].eggs do assert(string.match(egg.eggId,"^run:new%-run:")) end
print("Legacy saves passed: Build 020 profile loads additively, old queued 3-copy/2-copy eggs claim as committed, new run eggs wait behind legacy overflow, old run replay blocked")

------------------------------------------------------------------ Event tags
local e=user(106)
assert(Repository.load(e))
local tags={{eventId="volcano",mutationId="ember",n=7},{eventId="aurora",mutationId="",n=3},{eventId="rain",mutationId=""}}
assert(Repository.commitRunSettlement(e,"tag-run",10,tags))
local byOrdinal={}
for _,egg in revealLine(e) do byOrdinal[egg.source.ordinal]=egg end
assert(byOrdinal[7].eventId=="volcano" and byOrdinal[7].mutationId=="ember")
assert(byOrdinal[3].eventId=="aurora" and byOrdinal[1].eventId=="rain" and byOrdinal[2].eventId=="clear")
assert(select(3,Repository.commitRunSettlement(e,"too-many-tags",1,tags))=="invalid_egg_events")
assert(select(3,Repository.commitRunSettlement(e,"bad-tag",5,{{eventId="volcano",mutationId="frost"}}))=="invalid_egg_events")
assert(select(3,Repository.commitRunSettlement(e,string.rep("r",65),5))=="invalid_run_id")
local empty,emptyOutcome=Repository.commitRunSettlement(e,"zero-run",0)
assert(empty and emptyOutcome.eggCount==0 and e.attrs.LastRewardText=="no eggs")
print("Event tags passed: catch-ordinal weather/mutation tags land on the right eggs; invalid/oversized tags and run IDs rejected; zero-catch run")

------------------------------------------------------------------ Storage bound
local function jsonSize(v)
 local t=type(v)
 if t=="string" then return #v+2 elseif t=="number" then return #tostring(v) elseif t=="boolean" then return if v then 4 else 5 end
 if t~="table" then return 4 end
 local size=2 local isArray=#v>0
 for k,child in v do size+=jsonSize(child)+1+(if isArray then 0 else #tostring(k)+3) end
 return size
end
local s=user(107)
assert(Repository.load(s))
local r=0
while bankCount(s)+#data[key(s)].eggs<GameConfig.RunEggBankCapacity do
 r+=1 assert(Repository.commitRunSettlement(s,"storage-"..r,500))
end
local bytes=jsonSize(data[key(s)])
assert(bytes<900000,"profile with a full egg bank must stay well under the 4 MB DataStore limit: "..bytes)
print(string.format("Storage passed: %d banked eggs + %d nests ~ %d bytes (%.1f%% of 4 MiB)", bankCount(s)+#data[key(s)].eggs, #(data[key(s)].eggNests or {}), bytes, bytes/4194304*100))

------------------------------------------------------------------ Identity crediting (memory-only Studio profiles)
game.GameId=0 services.RunService.IsStudio=function() return true end
local LocalRepository=@@REPO_MODULE@@
local i=user(108)
assert(LocalRepository.load(i))
assert(LocalRepository.commitRunSettlement(i,"identity-run",15))
local identities,hatched,failedHatches=0,0,0
for _=1,15 do
 local head={id=i.attrs.NextChestId}
 local claimOk,h=LocalRepository.claimChest(i,head.id)
 assert(claimOk)
 if h.failed then
  failedHatches+=1 assert(h.instanceIds==nil or #h.instanceIds==0)
 else
  hatched+=1 assert(#h.instanceIds==1,"one identity per hatched dinosaur")
  local d=LocalRepository.dinosaurDetails(i,h.instanceIds[1])
  assert(d.origin.kind=="hatch" and d.originalEgg.eggId==head.id and d.originalEgg.source.kind=="run")
  identities+=1
 end
end
assert(hatched+failedHatches==15 and identities==hatched and #i.attrs.ChestQueueJson==0 and i.attrs.NextChestId=="")
print(string.format("Identity passed: 15-egg run -> %d identities for %d hatched eggs, %d failed Cracked eggs create none", identities, hatched, failedHatches))

------------------------------------------------------------------ Reveal skipping (pure module + preference field)
local RevealSkip=@@REVEAL_SKIP@@
local plain={big=false,shiny=false,eventMutationId="",genes={conditionId="normal"},failed=false}
assert(#RevealSkip.normalize({3,1,1,2,0,6,-1,1.5,"x",5})==4 and RevealSkip.normalize({3,1,1})[1]==1 and #RevealSkip.normalize(nil)==0 and #RevealSkip.normalize("1")==0)
assert(not RevealSkip.shouldSkip({},1,plain) and not RevealSkip.shouldSkip(nil,1,plain),"default skips nothing")
assert(RevealSkip.shouldSkip({1,2},1,plain) and RevealSkip.shouldSkip({1,2},2,plain) and not RevealSkip.shouldSkip({1,2},3,plain) and not RevealSkip.shouldSkip({1,2,3,4},5,plain),"Legendary is never skipped unless chosen")
assert(same(RevealSkip.Names,GameConfig.SpeciesRarityNames) and #RevealSkip.Rarities==GameConfig.SpeciesRarityScale,"skip names follow Config")
local cracked=table.clone(plain) cracked.failed=true cracked.genes={conditionId="cracked"}
assert(RevealSkip.shouldSkip({1},1,cracked),"cracked failures may be skipped (counted in the summary)")
for _,notable in {{shiny=true},{big=true},{eventMutationId="ember"},{genes={conditionId="rainbow"}},{genes={conditionId="astra"}}} do
 local o=table.clone(plain) for k,v in notable do o[k]=v end
 assert(RevealSkip.isNotable(o) and not RevealSkip.shouldSkip({1,2,3},1,o),"notable finds are never skipped")
end
assert(RevealSkip.isNotable(nil) and not RevealSkip.shouldSkip({1,2,3},1,nil),"unknown data is never hidden")
local toggled=RevealSkip.toggle({1},2) assert(#toggled==2 and toggled[1]==1 and toggled[2]==2)
toggled=RevealSkip.toggle(toggled,1) assert(#toggled==1 and toggled[1]==2)
assert(#RevealSkip.toggle({},9)==0 and #RevealSkip.toggle({},0)==0)
local summary=RevealSkip.summarize({{rarity=1,outcome=plain},{rarity=1,outcome=cracked},{rarity=2,outcome=plain},{rarity=3,outcome=plain},{rarity=5,outcome={shiny=true}}})
assert(summary.total==5 and summary.byRarity[1]==2 and summary.byRarity[2]==1 and summary.byRarity[3]==1 and summary.byRarity[4]==0 and summary.byRarity[5]==1 and summary.failed==1 and summary.hatched==4 and #summary.notable==1)
local lines=RevealSkip.lines(summary)
assert(lines[1]=="5 eggs skipped (4 hatched, 1 cracked)" and lines[2]=="2 Common  |  1 Uncommon  |  1 Rare  |  1 Legendary")
-- Preference field: validated, additive, persisted, never touches rewards.
local sk=user(109)
assert(Repository.load(sk) and sk.attrs.RevealSkipJson[1]==nil)
assert(Repository.commitRunSettlement(sk,"skip-run",15))
local before=totalCopies(data[key(sk)])
local queueBefore=copy(data[key(sk)].eggs)
assert(Repository.setRevealSkip(sk,{2,1}) and same(data[key(sk)].revealSkip,{1,2}) and sk.attrs.RevealSkipJson[2]==2)
assert(totalCopies(data[key(sk)])==before and same(data[key(sk)].eggs,queueBefore),"preference never changes eggs or collection")
assert(Repository.setRevealSkip(sk,{4,5}) and same(data[key(sk)].revealSkip,{4,5}))
assert(Repository.setRevealSkip(sk,{2,1}))
for _,bad in {{6},{0},{1,1},{1.5},{1,2,3,4,5,5},"x",{{}},{"1"}} do
 local okBad,reasonBad=Repository.setRevealSkip(sk,bad)
 assert(not okBad and reasonBad=="invalid_selection" and same(data[key(sk)].revealSkip,{1,2}))
end
Repository.release(sk) assert(Repository.load(sk) and sk.attrs.RevealSkipJson[1]==1)
assert(Repository.setRevealSkip(sk,{}) and #data[key(sk)].revealSkip==0)
-- BD-264 settings v2: profile without the field reads as defaults; save, bad values normalize, survive rejoin, eggs untouched.
assert(data[key(sk)].settings==nil and sk.attrs.SettingsJson.effects=="full" and sk.attrs.SettingsJson.calm==false and sk.attrs.SettingsJson.sound.master==0.8,"old profile: defaults")
assert(Repository.setSettings(sk,{sound={master=0.3,sfx=9,ambience="x"},effects="lite",weather="off",calm=true,jumpSize="huge"}))
local saved=data[key(sk)].settings
assert(saved.sound.master==0.3 and saved.sound.sfx==1 and saved.sound.ambience==0.6 and saved.effects=="lite" and saved.weather=="off" and saved.calm==true and saved.jumpSize=="normal","server normalizes")
assert(totalCopies(data[key(sk)])==before and same(data[key(sk)].eggs,queueBefore),"settings never change eggs or collection")
local okS,reasonS=Repository.setSettings(sk,"x") assert(not okS and reasonS=="invalid_settings")
Repository.release(sk) assert(Repository.load(sk) and sk.attrs.SettingsJson.weather=="off" and sk.attrs.SettingsJson.sound.master==0.3,"survives rejoin")
-- Skipped eggs are still credited exactly once: claim the whole run without any animation.
local hatchedSkipped=0
while sk.attrs.NextChestId~="" do
 local claimOk,res=Repository.claimChest(sk,sk.attrs.NextChestId) assert(claimOk) hatchedSkipped+=1
end
assert(hatchedSkipped==15 and #data[key(sk)].eggs==0 and bankCount(sk)==0)
print("Reveal skip passed: rarity selection, notable finds never skipped, Legendary default shown, toggle/normalize/summary lines, validated additive preference that cannot affect rewards, all 15 eggs still credited")

------------------------------------------------------------------ Five species rarity tiers (BD-044)
local tierCount={0,0,0,0,0}
local weighted={}
local weightSum=0
for _,row in GameConfig.ChestSpeciesWeights do weighted[row.speciesId]=true weightSum+=row.weight end
assert(math.abs(weightSum-100)<1e-9,"base species weights sum to 100")
assert(#GameConfig.SpeciesRarityNames==5 and GameConfig.SpeciesRarityScale==5 and #GameConfig.SpeciesRunBoost==5)
for _,id in GameConfig.SpeciesOrder do
 local tier=GameConfig.SpeciesRarities[id]
 assert(tier and tier>=1 and tier<=5 and tier%1==0 and weighted[id],"every species has a tier and a weight: "..id)
 tierCount[tier]+=1
 assert(GameConfig.LegacySpeciesRarities[id],"legacy tier known for migration: "..id)
end
for tier=1,5 do assert(tierCount[tier]>=3,"every tier has species") end
local function tierShares(eggs)
 local w={0,0,0,0,0} local total=0
 for _,row in Rewards.speciesWeights(eggs) do local t=GameConfig.SpeciesRarities[row.speciesId] w[t]+=row.weight total+=row.weight end
 for t=1,5 do w[t]/=total end
 return w
end
local base=tierShares(1)
assert(math.abs(base[1]-.72)<1e-9 and math.abs(base[5]-.001)<1e-9,"one egg = base odds (shop eggs disclose these)")
local previous=nil
for _,n in {1,4,10,20,40,100} do
 local sh=tierShares(n)
 for t=1,4 do
  assert(sh[t]>sh[t+1],"rarer tiers are always less likely")
  local ratio=sh[t+1]/sh[t]
  assert(ratio<=1/3+1e-9 and ratio>=1/8,"exponential: adjacent tier ratio stays within [1/8, 1/3], tier "..t.." n="..n)
 end
 if previous then assert(sh[1]<=previous[1]+1e-12 and sh[3]>=previous[3]-1e-12 and sh[5]>=previous[5]-1e-12,"bigger runs expose rarer tiers") end
 for t=3,5 do assert(sh[t]/base[t]<=1.1+1e-9,"BD-165: the run boost never makes a Rare+ tier more than 10% easier, tier "..t) end
 previous=sh
end
assert(same(tierShares(40),tierShares(1000)),"boost capped at EggRarityBoostMaxEggs (40 eggs = 5,000 food)")
-- Expected mixes at the owner's two sizes (BD-165: 500 food = 4 eggs, 5,000 food = 40 eggs).
local s4,s40=tierShares(4),tierShares(40)
assert(4*s4[1]>=2.8 and 40*s40[1]>=27 and 40*(s40[3]+s40[4]+s40[5])<=2.6,"40-egg mix stays common-heavy with few rares")
local pRare4=1-(1-(s4[3]+s4[4]+s4[5]))^4
assert(pRare4<=.2,"docs/88 target: a 4-egg run holds a Rare+ egg well under 30% of the time: "..pRare4)
-- Seeded rolls through the real computeChestReward agree with the analytic shares.
local drawsT=40000 local seen={0,0,0,0,0}
local tierRng=Random.new()
for _=1,drawsT do local r=Rewards.computeChestReward(tierRng,40) seen[GameConfig.SpeciesRarities[r.speciesId]]+=1 end
for t=1,5 do assert(math.abs(seen[t]/drawsT-s40[t])<=4*math.sqrt(s40[t]*(1-s40[t])/drawsT)+1e-4,"seeded tier "..t) end
-- Saved values from the three-tier scale migrate once, additively, never overclaiming.
local function legacyProfile(id,rarest,skip,owned)
 local u=user(id) assert(Repository.load(u)) Repository.release(u)
 local p=data[key(u)]
 p.rarityScale=nil p.metrics.rarest=rarest p.revealSkip=skip
 for species,count in owned do p.collection[species].base=count end
 return u
end
local cases={
 {0,nil,{},0,nil},
 {1,{1},{},1,{1}},
 {1,nil,{archaeopteryx=2},2,nil}, -- old Common archaeopteryx is Uncommon now
 {2,{1,2},{},2,{1,2,3}}, -- old Rare without an owned Rare-now species stays at Uncommon
 {2,nil,{triceratops=1,tyrannosaurus=1},3,nil}, -- owned T. rex is outside the old Rare band: no overclaim
 {3,{3},{},4,{4,5}},
 {3,{1,2,3},{spinosaurus=1},5,{1,2,3,4,5}},
}
for i,case in cases do
 local u=legacyProfile(2000+i,case[1],case[2],case[3])
 assert(Repository.load(u),"legacy rarity profile loads "..i)
 local p=data[key(u)]
 assert(p.rarityScale==5 and p.metrics.rarest==case[4] and u.attrs.RarestCaught==case[4],"migrated rarest "..i)
 assert(same(p.revealSkip,case[5]),"migrated reveal skip "..i)
 Repository.release(u) assert(Repository.load(u) and data[key(u)].metrics.rarest==case[4] and same(data[key(u)].revealSkip,case[5]),"migration is idempotent "..i)
end
local broken=legacyProfile(2100,4,nil,{}) -- 4 was never valid on the old scale
assert(not Repository.load(broken) and data[key(broken)].rarityScale==nil,"malformed legacy rarest is rejected, not rewritten")
local fresh=user(2101) assert(Repository.load(fresh) and data[key(fresh)].rarityScale==5)
print(string.format("Species tiers passed: 22 species in 5 tiers (%d/%d/%d/%d/%d); 4 eggs -> %.2f C / %.2f U / %.2f R+; 40 eggs -> %.1f / %.1f / %.2f / %.2f / %.3f; %d seeded rolls; legacy rarest/skip migration (%d cases) idempotent, malformed rejected",
 tierCount[1],tierCount[2],tierCount[3],tierCount[4],tierCount[5],4*s4[1],4*s4[2],4*(s4[3]+s4[4]+s4[5]),
 40*s40[1],40*s40[2],40*s40[3],40*s40[4],40*s40[5],drawsT,#cases))

------------------------------------------------------------------ Seeded condition draws (BD-045)
local counts={} local failedDraws=0
local rng=Random.new()
local draws=20000
for _=1,draws do
 local g=Genetics.roll(0,rng)
 counts[g.conditionId]=(counts[g.conditionId] or 0)+1
 if not g.hatchSuccess then failedDraws+=1 end
end
local weights=ProgressionConfig.ConditionWeights[1]
for k,condition in ProgressionConfig.Conditions do
 local observed=(counts[condition.id] or 0)/draws
 local expected=weights[k]/ProgressionConfig.ConditionWeightScale
 assert(math.abs(observed-expected)<.012,condition.id..": "..observed.." vs "..expected)
end
assert(math.abs(failedDraws/draws-.4)<.012,"tier-0 failure should be ~40%")
print(string.format("Seeded draws passed: %d tier-0 rolls Cracked %.2f%% Dirty %.2f%% Normal %.2f%% Rainbow %.2f%% Astra %.2f%%; failed %.2f%%",
 draws,100*counts.cracked/draws,100*counts.dirty/draws,100*counts.normal/draws,100*counts.rainbow/draws,100*(counts.astra or 0)/draws,100*failedDraws/draws))
print("BD-044/BD-045 reward loop verified (offline Luau; Studio verification pending)")
'''


def script():
    s = HARNESS
    for token, path in [
        ('@@PROGRESSION_CONFIG@@', 'src/shared/ProgressionConfig.luau'),
        ('@@GAME_CONFIG@@', 'src/shared/Config.luau'),
        ('@@FOOD_RULES@@', 'src/shared/FoodCatchRules.luau'),
        ('@@GENETICS@@', 'src/shared/EggGenetics.luau'),
        ('@@EGG_TRAITS@@', 'src/shared/EggTraits.luau'),
        ('@@RULES@@', 'src/shared/ProgressionRules.luau'),
        ('@@FUSION_ODDS@@', 'src/server/FusionOdds.luau'),
        ('@@REVEAL_SKIP@@', 'src/shared/RevealSkip.luau'),
        ('@@NEST_QUEUE@@', 'src/shared/NestQueue.luau'),
        ('@@FTUE_RULES@@', 'src/shared/FtueRules.luau'),
        ('@@SETTINGS_MODEL@@', 'src/shared/SettingsModel.luau'),
        ('@@REWARD_MATH@@', 'src/server/RewardMath.luau'),
        ('@@IDENTITY_FUSION_MODULE@@', 'src/server/IdentityFusion.luau'),
        ('@@IDENTITY_MODULE@@', 'src/server/DinosaurIdentity.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        s = s.replace(token, module(path))
    return s


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'rewards.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
