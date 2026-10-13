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
GameConfig=mutableConfig
local storage={Shared={Config="Config",ProgressionRules="Rules",EggTraits="EggTraits",EggGenetics="Genetics",ProgressionConfig="ProgressionConfig"}}
local services={DataStoreService={GetDataStore=function() return store end},HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function() return false end}}
local game={GameId=1,JobId="test",GetService=function(_,id) return services[id] end}
local task={wait=function() end,spawn=function() end}
local warn=function() end
local script={Parent={}}
local require=function(id)
 if id=="Config" then return GameConfig elseif id=="ProgressionConfig" then return ProgressionConfig end
 error("unexpected module "..tostring(id))
end
local Rewards=@@REWARD_MATH@@
local Identity=@@IDENTITY_MODULE@@
local script={Parent={DinosaurIdentity="Identity"}}
local require=function(id) assert(id=="Identity") return Identity end
local IdentityFusion=@@IDENTITY_FUSION_MODULE@@
local script={Parent={Config="Config"}}
local require=function(id) if id=="Identity" then return Identity end return GameConfig end
local FusionOdds=@@FUSION_ODDS@@
local script={Parent={RewardMath="Rewards",DinosaurIdentity="Identity",IdentityFusion="IdentityFusion",FusionOdds="FusionOdds"}}
local require=function(id)
 if id=="FusionOdds" then return FusionOdds end
 if id=="IdentityFusion" then return IdentityFusion elseif id=="Identity" then return Identity elseif id=="Genetics" then return Genetics
 elseif id=="EggTraits" then return EggTraits elseif id=="ProgressionConfig" then return ProgressionConfig elseif id=="Config" then return GameConfig
 elseif id=="Rules" then return Rules elseif id=="Rewards" then return Rewards end
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
assert(Rewards.runEggCount(1e308)==300 and Rewards.runEggCount(301)==300 and Rewards.runEggCount(300)==300)
assert(Rewards.runEggCount("15")==0 and Rewards.runEggCount(nil)==0 and Rewards.runEggCount(14.7)==14)
assert(Rewards.runEggCount(15)==15 and Rewards.runEggCount(150)==150)
local catches,carry=FoodCatchRules.award(500,0,1)
assert(catches==15 and Rewards.runEggCount(catches)==15,"500 food -> 15 run eggs")
catches=FoodCatchRules.award(5000,0,1)
assert(catches==150 and Rewards.runEggCount(catches)==150,"5,000 food -> 150 run eggs")
assert(Rewards.runCrystals(0)==0 and Rewards.runCrystals(15)==30 and Rewards.runCrystals(150)==219 and Rewards.runCrystals(300)==429)
assert(Rewards.runCrystals(0/0)==0 and Rewards.runCrystals(-1)==0 and Rewards.runCrystals(math.huge)==429)
assert(Rewards.nestCount(14)==0 and Rewards.nestCount(15)==1 and Rewards.nestCount(150)==6)
assert(Rewards.nestCount(300)==GameConfig.NestMaxPerRun and Rewards.nestCount(math.huge)==GameConfig.NestMaxPerRun)
local zero=Rewards.computeRunReward(0/0)
assert(zero.eggCount==0 and zero.crystals==0 and zero.nestCount==0 and zero.accountXP==0)
local previous=-1
for n=0,300 do local c=Rewards.runCrystals(n) assert(c>=previous) previous=c end
assert(#Rewards.runEggId(string.rep("x",64),300)<=80 and #(Rewards.nestId(string.rep("x",64),11)..":3")<=80)
print("Reward math passed: 0/negative/NaN/inf/huge/non-number scores, 500->15 and 5,000->150 eggs, 30/219 crystals, 1/6 nests, bounded IDs")

------------------------------------------------------------------ 15-egg run
local now=os.time()
local a=user(101)
assert(Repository.load(a))
local beforeCopies=totalCopies(data[key(a)])
local ok,outcome,status=Repository.commitRunSettlement(a,"run-15",15)
assert(ok and status=="committed" and outcome.eggCount==15 and outcome.crystals==30 and outcome.nestCount==1)
assert(totalCopies(data[key(a)])==beforeCopies,"settlement must not grant direct dinosaur copies")
assert(#data[key(a)].eggs==5 and bankCount(a)==10 and data[key(a)].pendingChestGrants==0)
assert(data[key(a)].progression.crystals==30 and data[key(a)].progression.accountXP==15)
assert(#data[key(a)].nests==1 and #data[key(a)].pendingNests==0 and data[key(a)].nests[1].readyAt>=now+GameConfig.NestIncubationSeconds)
assert(#data[key(a)].nests[1].eggs==GameConfig.NestEggCount)
local ids={}
local lastRarity=0
for _,egg in revealLine(a) do
 assert(not ids[egg.eggId]) ids[egg.eggId]=true
 assert(string.match(egg.eggId,"^run:run%-15:%d+$") and egg.reward.count==1 and egg.kind=="run_egg")
 assert(Genetics.valid(egg.genes) and egg.traitRollVersion=="bd045-genes-v2" and egg.source.kind=="run")
 local rarity=GameConfig.SpeciesRarities[egg.reward.speciesId]
 assert(rarity>=lastRarity,"run batch must reveal in increasing rarity") lastRarity=rarity
end
assert(a.attrs.LastRewardText=="15 run eggs | 1 bonus nest" and a.attrs.LastRunCrystals==30 and a.attrs.LastRunCrystalBox==0)
assert(a.attrs.BankedRunEggCount==10 and a.attrs.QueuedEggsWaiting==10 and a.attrs.RunStartBlocked=="")
-- Exactly once: replays (cached and uncached) change nothing.
local snapshot=copy(data[key(a)])
local dupOk,_,dupStatus=Repository.commitRunSettlement(a,"run-15",15)
assert(dupOk and dupStatus=="duplicate" and same(snapshot,data[key(a)]))
Repository.release(a) assert(Repository.load(a))
snapshot=copy(data[key(a)])
dupOk,_,dupStatus=Repository.commitRunSettlement(a,"run-15",150)
assert(dupOk and dupStatus=="duplicate" and same(snapshot,data[key(a)]),"replay with a different score must not re-settle")
print("15-egg run passed: 15 banked eggs (5 queue + 10 bank), no direct copies, 30 crystals, 1 slotted nest, ascending rarity, exactly-once replays")

------------------------------------------------------------------ 150-egg run, reveal, reconnect
local b=user(102)
assert(Repository.load(b))
local copiesBefore=totalCopies(data[key(b)])
assert(Repository.commitRunSettlement(b,"run-150",150))
assert(#data[key(b)].eggs==5 and bankCount(b)==145)
assert(#data[key(b)].nests==5 and #data[key(b)].pendingNests==1,"6 nests: 5 slotted, 1 capacity-blocked pending")
assert(b.attrs.PendingNestCount==1 and #b.attrs.NestsJson==5 and data[key(b)].progression.crystals==219)
local line=revealLine(b)
assert(#line==150)
local committedIds={} for i,egg in line do committedIds[i]=egg.eggId end
local committedGenes={} for i,egg in line do committedGenes[i]=copy(egg.genes) end
local successes,failures,claimed=0,0,0
local function claimNext(u)
 local egg=data[key(u)].eggs[1]
 local claimOk,result,claimStatus=Repository.claimChest(u,egg.eggId)
 assert(claimOk and claimStatus=="claimed",tostring(claimStatus))
 if result.failed then
  assert(result.count==0 and egg.genes.conditionId=="cracked","only Cracked eggs fail and they give 0 dinosaurs")
  failures+=1
 else
  assert(result.count==1,"exactly one dinosaur per successful egg") successes+=1
 end
 claimed+=1
 return egg
end
lastRarity=0
for i=1,40 do
 local egg=claimNext(b)
 assert(egg.eggId==committedIds[i] and same(egg.genes,committedGenes[i]),"reveal order or genes changed")
 local rarity=GameConfig.SpeciesRarities[egg.reward.speciesId]
 assert(rarity>=lastRarity) lastRarity=rarity
end
assert(#data[key(b)].eggs==5 and bankCount(b)==105,"queue refills from the bank after each claim")
-- Duplicate claim of an already hatched egg never double-credits.
local copiesMid=totalCopies(data[key(b)])
local again,_,againStatus=Repository.claimChest(b,committedIds[40])
assert(again and againStatus=="duplicate" and totalCopies(data[key(b)])==copiesMid)
-- Reconnect mid-batch: the remaining 110 eggs return identically, no reroll, no loss.
Repository.release(b)
assert(Repository.load(b))
line=revealLine(b)
assert(#line==110)
for i,egg in line do assert(egg.eggId==committedIds[40+i] and same(egg.genes,committedGenes[40+i])) end
-- Out-of-order claim is refused.
local skip,_,skipStatus=Repository.claimChest(b,data[key(b)].eggs[2].eggId)
assert(not skip and skipStatus=="missing")
for i=41,150 do
 local egg=claimNext(b)
 assert(egg.eggId==committedIds[i])
 local rarity=GameConfig.SpeciesRarities[egg.reward.speciesId]
 assert(rarity>=lastRarity) lastRarity=rarity
end
assert(claimed==150 and successes+failures==150 and #data[key(b)].eggs==0 and bankCount(b)==0)
assert(totalCopies(data[key(b)])==copiesBefore+successes,"one dinosaur per successful egg, none for failures")
assert(failures>0,"expected some failed Cracked eggs at BD-045 tier 0")
-- Replaying settlement after 150 claims trimmed it out of recentOperations is still a no-op.
local found=false for _,entry in data[key(b)].recentOperations do if entry.id=="run:run-150" then found=true end end
assert(not found,"fixture expects the run operation to be trimmed")
snapshot=copy(data[key(b)])
dupOk,_,dupStatus=Repository.commitRunSettlement(b,"run-150",150)
assert(dupOk and dupStatus=="duplicate" and same(snapshot,data[key(b)]),"settledRuns ledger must block re-settlement")
print(string.format("150-egg run passed: 150 eggs revealed in committed ascending order across reconnect; %d hatched, %d Cracked failures; trimmed-ledger replay blocked", successes, failures))

------------------------------------------------------------------ Outage, transient failure, lease loss
local c=user(103)
assert(Repository.load(c))
snapshot=copy(data[key(c)])
failMode="all"
local failed,_,failedStatus=Repository.commitRunSettlement(c,"outage-run",15)
failMode=nil
assert(not failed and failedStatus=="save_failed" and same(snapshot,data[key(c)]),"outage must not partially write")
-- Recovery = rejoin after the outage; the same run then settles.
Repository.release(c) assert(Repository.load(c))
failMode="once"
local retried,_,retriedStatus=Repository.commitRunSettlement(c,"outage-run",15)
assert(retried and retriedStatus=="committed" and #revealLine(c)==15,"transient outage retried inside the repository")
assert(data[key(c)].progression.crystals==30)
assert(select(3,Repository.commitRunSettlement(c,"outage-run",15))=="duplicate" and #revealLine(c)==15)
-- Lost acknowledgement: the first write commits, the retry finds it and reports duplicate.
failMode="ack_lost"
local acked,_,ackStatus=Repository.commitRunSettlement(c,"ack-run",15)
assert(acked and ackStatus=="duplicate" and #revealLine(c)==30 and data[key(c)].progression.crystals==60,"lost ack must not double-settle")
data[key(c)].session.leaseId="other-server"
snapshot=copy(data[key(c)])
local lost,_,lostStatus=Repository.commitRunSettlement(c,"lease-run",15)
assert(not lost and lostStatus=="lease_lost" and same(snapshot,data[key(c)]) and c.attrs.ProfileState=="LeaseLost")
local lostClaim,_,lostClaimStatus=Repository.claimChest(c,data[key(c)].eggs[1].eggId)
assert(not lostClaim and lostClaimStatus=="profile_not_loaded" and same(snapshot,data[key(c)]))
-- The new owner (session freed) settles the same run exactly once.
data[key(c)].session=nil
Repository.release(c)
assert(Repository.load(c))
assert(Repository.commitRunSettlement(c,"lease-run",15) and #revealLine(c)==45)
assert(select(3,Repository.commitRunSettlement(c,"lease-run",15))=="duplicate" and #revealLine(c)==45)
print("Failure handling passed: full outage writes nothing, transient outage commits once, lost acknowledgement retried as duplicate, lease loss blocks settlement/claims, retry after recovery is exactly-once")

------------------------------------------------------------------ Nests: capacity, pending, opening
local n=user(104)
assert(Repository.load(n))
assert(Repository.commitRunSettlement(n,"nest-a",150)) -- 6 nests
assert(#data[key(n)].nests==5 and #data[key(n)].pendingNests==1)
local pendingId=data[key(n)].pendingNests[1].nestId
local slotId=data[key(n)].nests[1].nestId
assert(select(3,Repository.claimNest(n,slotId))=="not_ready")
assert(select(3,Repository.claimNest(n,pendingId))=="nest_pending")
assert(select(3,Repository.claimNest(n,"nest:missing:1"))=="missing")
assert(select(3,Repository.claimNest(n,string.rep("x",81)))=="invalid_nest_id")
-- Fast-forward incubation through a reload fixture.
Repository.release(n)
for _,nest in data[key(n)].nests do nest.readyAt=0 end
assert(Repository.load(n))
local queueHead=data[key(n)].eggs[1].eggId
local bankBefore=bankCount(n)
local nestEggs=copy(data[key(n)].nests[1].eggs)
local opened,nestOutcome,openStatus=Repository.claimNest(n,slotId)
assert(opened and openStatus=="opened" and nestOutcome.eggCount==GameConfig.NestEggCount)
assert(bankCount(n)==bankBefore+GameConfig.NestEggCount and data[key(n)].eggs[1].eggId==queueHead)
for i,egg in nestEggs do
 assert(data[key(n)].runEggBank[i].eggId==egg.eggId and same(data[key(n)].runEggBank[i].genes,egg.genes),"nest eggs are next in line, unchanged")
 assert(egg.source.kind=="nest" and egg.reward.count==1 and egg.kind=="nest_egg")
end
assert(#data[key(n)].nests==5 and #data[key(n)].pendingNests==0,"pending nest promoted into the freed slot")
local promoted=data[key(n)].nests[5]
assert(promoted.nestId==pendingId and promoted.readyAt>=now+GameConfig.NestIncubationSeconds)
assert(select(3,Repository.claimNest(n,slotId))=="duplicate" and bankCount(n)==bankBefore+GameConfig.NestEggCount)
-- Pending nests are never dropped; once pending exceeds headroom for a max run, runs are blocked.
local totalNests=#data[key(n)].nests+#data[key(n)].pendingNests
-- Isolate the nest gate from the egg-bank gate (fixture: empty queue/bank).
Repository.release(n) data[key(n)].runEggBank={} data[key(n)].eggs={} assert(Repository.load(n))
local runs=0
while n.attrs.RunStartBlocked~="nests_pending_full" do
 runs+=1
 assert(Repository.commitRunSettlement(n,"nest-fill-"..runs,15))
 totalNests+=1
 assert(#data[key(n)].nests+#data[key(n)].pendingNests==totalNests,"a nest was lost")
 assert(runs<100)
end
assert(#data[key(n)].pendingNests==GameConfig.NestPendingCapacity-GameConfig.NestMaxPerRun+1)
-- Even a settlement while blocked (run started before the block) keeps every nest.
assert(Repository.commitRunSettlement(n,"nest-overflow",300))
assert(#data[key(n)].nests+#data[key(n)].pendingNests==totalNests+GameConfig.NestMaxPerRun)
-- Bank-full refusal keeps the nest intact.
Repository.release(n)
data[key(n)].nests[1].readyAt=0
while #data[key(n)].runEggBank<GameConfig.RunEggBankCapacity-1 do table.insert(data[key(n)].runEggBank,copy(data[key(n)].runEggBank[1])) end
assert(Repository.load(n) and n.attrs.RunStartBlocked=="egg_bank_full")
local fullId=data[key(n)].nests[1].nestId
assert(select(3,Repository.claimNest(n,fullId))=="bank_full" and data[key(n)].nests[1].nestId==fullId)
print(string.format("Nests passed: 5 slots + pending, incubation, pending/missing/invalid refusals, opening puts 3 eggs next in line, promotion, duplicate, %d runs to nests_pending_full gate, no nest ever lost, bank_full refusal", runs))

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
assert(empty and emptyOutcome.eggCount==0 and e.attrs.LastRewardText=="no run eggs")
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
 r+=1 assert(Repository.commitRunSettlement(s,"storage-"..r,300))
end
local bytes=jsonSize(data[key(s)])
assert(bytes<1500000,"profile with a full egg bank must stay well under the 4 MB DataStore limit: "..bytes)
print(string.format("Storage passed: %d banked eggs + %d nests/pending ~ %d bytes (%.1f%% of 4 MiB)", bankCount(s)+#data[key(s)].eggs, #data[key(s)].nests+#data[key(s)].pendingNests, bytes, bytes/4194304*100))

------------------------------------------------------------------ Identity crediting (memory-only Studio profiles)
game.GameId=0 services.RunService.IsStudio=function() return true end
local LocalRepository=@@REPO_MODULE@@
local i=user(108)
assert(LocalRepository.load(i))
assert(LocalRepository.commitRunSettlement(i,"identity-run",15))
local identities,hatched,failedHatches=0,0,0
for _=1,15 do
 local head=i.attrs.ChestQueueJson[1]
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
assert(hatched+failedHatches==15 and identities==hatched and #i.attrs.ChestQueueJson==0)
print(string.format("Identity passed: 15-egg run -> %d identities for %d hatched eggs, %d failed Cracked eggs create none", identities, hatched, failedHatches))

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
