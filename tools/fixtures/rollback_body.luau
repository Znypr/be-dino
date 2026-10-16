-- BD-320 rollback drill body. Appended to the verify_rewards mocked-DataStore prefix by tools/verify_rollback.py.
-- Shared state from the prefix: data (the ONE DataStore), store, copy, same, Random, http, GameConfig, failMode.

local function newUser(id)
 local u={Parent=true,UserId=id,Name="P"..id,attrs={}}
 function u:SetAttribute(k,v) self.attrs[k]=v end
 function u:GetAttribute(k) return self.attrs[k] end
 return u
end
local function key(id) return "u:"..tostring(id) end

-- ===== OLD world: frozen Build 020 reader (git a9edf8e) on the same DataStore =====
local function makeOld()
 local mods={}
 local names=setmetatable({},{__index=function(_,k) return k end})
 local script={Parent=names}
 local require=function(id) return assert(mods[id],"old module "..tostring(id)) end
 mods.Config=@@OLD_CONFIG@@
 mods.ProgressionConfig=@@OLD_PROGRESSION_CONFIG@@
 mods.EggGenetics=@@OLD_GENETICS@@
 mods.ProgressionRules=@@OLD_RULES@@
 mods.EggTraits=@@OLD_TRAITS@@
 local oldConfig=mods.Config
 local storage={Shared=names}
 local services={DataStoreService={GetDataStore=function() return store end},HttpService=http,ReplicatedStorage=storage,RunService={IsStudio=function() return false end}}
 local game={GameId=1,JobId="old-build-020",GetService=function(_,id) return services[id] end}
 local task={wait=function() end,spawn=function() end}
 local warn=function() end
 mods.RewardMath=@@OLD_REWARD_MATH@@
 return @@OLD_REPO@@, oldConfig
end
local OldRepo,OldConfig=makeOld()

-- ===== NEW world: current ProfileRepository with the playtest-profile flags (persistent identity + fusion) =====
local baseConfig=GameConfig
GameConfig=table.clone(baseConfig)
GameConfig.IdentityPersistentEnabled=true
GameConfig.IdentityFusionPreviewEnabled=true
local PlaytestConfig=GameConfig
local NewRepo=@@REPO_MODULE@@
GameConfig=baseConfig

local function claimAll(repo,u)
 local ids={}
 for _,chest in u.attrs.ChestQueueJson or {} do
  local ok,h=repo.claimChest(u,chest.id)
  if ok and h.instanceIds then for _,id in h.instanceIds do table.insert(ids,id) end end
 end
 return ids
end

-- Build a rich profile with the CURRENT code: eggs, bank, nests, hatches, a fusion, settings.
local RICH=5001
local richUser=newUser(RICH)
assert(NewRepo.load(richUser))
local hatchedIds={}
for round=1,30 do
 assert(NewRepo.commitRunSettlement(richUser,"rich-"..round,10,nil,300))
 for _,id in claimAll(NewRepo,richUser) do table.insert(hatchedIds,id) end
end
local sidecar=data[key(RICH)].dinosaurIdentity
assert(sidecar and #hatchedIds>=50,"hatches credited identities")
local bySpecies={}
for _,id in hatchedIds do
 local inst=sidecar.instances[id]
 if inst then bySpecies[inst.speciesId]=bySpecies[inst.speciesId] or {} table.insert(bySpecies[inst.speciesId],id) end
end
local donors for _,list in bySpecies do if #list>=6 and not donors then donors={table.unpack(list,1,6)} end end
local fused=false
if donors then
 local quote=assert(NewRepo.quoteFusion(richUser,"gold",donors))
 local okF,committed,status=NewRepo.fuseDinosaurs(richUser,{token="rich-fuse",targetStage="gold",donorIds=donors,quoteDigest=quote.quoteDigest,consentDigest=quote.consentDigest})
 fused=okF and status=="fused"
end
print("rich profile: hatched="..#hatchedIds.." fused="..tostring(fused))
assert(NewRepo.setSettings(richUser,{v=1,sound={master=0.5,sfx=0.4,ambience=0.3},effects="lite",weather="off",calm=true,jumpSize="big",peaceful=true,teleportShops=false}))
-- A big banked run for the queue/bank/nest shapes (cap lifted like the stress tests).
GameConfig.RunEggMaxPerRun=500
PlaytestConfig.RunEggMaxPerRun=500
assert(NewRepo.commitRunSettlement(richUser,"rich-big",400,nil,600))
NewRepo.release(richUser)
local rich=copy(data[key(RICH)])
local keys={} for k in rich do table.insert(keys,k) end table.sort(keys)
print("rich keys: "..table.concat(keys,","))
print("nests="..#(rich.eggNests or {}).." bank="..#(rich.runEggBank or {}).." eggs="..#rich.eggs.." rarest="..rich.metrics.rarest)


local checks=0
local function check(cond,msg) checks+=1 assert(cond,msg) end
local function put(id,profile) data[key(id)]=if profile==nil then nil else copy(profile) return key(id) end
local function fresh(profile,id)
 local p=copy(profile) p.session=nil
 put(id,p)
 return newUser(id)
end
-- Fields that legitimately change on load/release (lease, revision counter, play-time metric).
local VOLATILE={session=true,revision=true}
local function sameData(a,b,ignore)
 for k,v in a do if not (ignore and ignore[k]) and not same(v,b[k]) then return false,k end end
 for k in b do if not (ignore and ignore[k]) and a[k]==nil then return false,k end end
 return true
end
local function metricsKeep(a,b) return a.rarest==b.rarest and a.robux==b.robux end

------------------------------------------------------------------ (1) CURRENT-written profile read by the OLD Build 020 reader
check(rich.settings.teleportShops==false,"rich profile carries the new settings")
check(rich.dinosaurIdentity~=nil and next(rich.dinosaurIdentity.fusions or {})~=nil,"rich profile carries a fusion ledger with parent ids")
local ledger for _,entry in rich.dinosaurIdentity.fusions do ledger=entry end
check(ledger and #ledger.parentIds==6 and ledger.parentEggIds~=nil,"fusion lineage: parent ids")
check(#rich.eggNests>=1 and #rich.runEggBank>=1 and #rich.eggs>=1 and rich.settledRuns~=nil and rich.rarityScale==5,"nest queue, bank, eggs, settled runs, rarityScale written")
local u1=newUser(RICH) put(RICH,rich)
check(OldRepo.load(u1) and u1.attrs.ProfileState=="Loaded","Build 020 loads a current profile that has settings, nests, bank, identity sidecar and fusion ledger")
local afterLoad=copy(data[key(RICH)])
local okSame,diffKey=sameData(rich,afterLoad,VOLATILE)
check(okSame,"old load keeps every field incl. unknown ones; differing field: "..tostring(diffKey))
for _,unknown in {"settings","dinosaurIdentity","eggNests","runEggBank","settledRuns","rarityScale"} do check(same(rich[unknown],afterLoad[unknown]),"unknown field preserved: "..unknown) end
-- Old code operating on the new profile: settle a run, hatch via the OLD claim path, renew, release.
check(OldRepo.renew(u1),"old renew on a new-format profile")
local oldEggBefore=#afterLoad.eggs
local oldQueue=u1.attrs.ChestQueueJson
local claimedOld=false
if oldQueue and oldQueue[1] then
 local okC,res=OldRepo.claimChest(u1,oldQueue[1].id)
 claimedOld=okC
end
OldRepo.release(u1)
local afterOld=copy(data[key(RICH)])
check(afterOld.session==nil,"old release clears its lease")
for _,unknown in {"settings","dinosaurIdentity","eggNests","runEggBank","settledRuns","rarityScale"} do check(same(rich[unknown],afterOld[unknown]),"unknown field still preserved after old operations: "..unknown) end
check(afterOld.settings.teleportShops==false,"settings survive the old build")
-- BD-436: the discovery log is an additive progression field; Build 020 never reads or rewrites it.
local richLog=rich.progression.discovered
check(type(richLog)=="table" and next(richLog.colours)~=nil and next(richLog.patterns)~=nil,"current code wrote a discovery log for the rich profile")
check(same(richLog,afterOld.progression.discovered),"discovery log preserved byte-for-byte after Build 020 load, claim, renew and release")
print("old claimChest on a new-format queue: "..tostring(claimedOld).." (queue "..oldEggBefore.." -> "..#afterOld.eggs..")")
-- ...then roll FORWARD: current code loads what the old build wrote; the sidecar may be stale but is never deleted.
local sidecarBefore=copy(rich.dinosaurIdentity)
local u2=newUser(RICH)
check(NewRepo.load(u2) and u2.attrs.ProfileState=="Loaded","current code loads a profile after a Build 020 session")
local sidecarAfter=data[key(RICH)].dinosaurIdentity
local keptAll=true
for id in sidecarBefore.instances do if sidecarAfter.instances[id]==nil then keptAll=false end end
local reason=sidecarAfter.suspendedReason
check(keptAll or reason~=nil,"identity instances survive roll-forward (or identity is suspended, never silently emptied)")
check(data[key(RICH)].settings.teleportShops==false,"settings still stored after roll-forward")
local logAfter=data[key(RICH)].progression.discovered
local logKept=true
for _,kind in {"colours","patterns","mutations"} do for id in richLog[kind] do if logAfter[kind][id]~=true then logKept=false end end end
check(logKept,"roll-forward keeps every discovered id (add-only)")
print("roll-forward after an old claim: identity "..(if reason then "suspended ("..tostring(reason)..")" else "reconciled").." instances kept="..tostring(keptAll))
NewRepo.release(u2)

------------------------------------------------------------------ (1a) Flag rollback: same code, IdentityPersistentEnabled/IdentityFusionPreviewEnabled back to false
do
 local id=5200
 local u=fresh(rich,id)
 check(Repository.load(u) and u.attrs.ProfileState=="Loaded","current code with the identity flags OFF loads a profile that has a sidecar")
 check(not Repository.fusionStatus(u),"fusion reports disabled with the flags off")
 Repository.renew(u) Repository.release(u)
 local after=data[key(id)]
 check(same(rich.dinosaurIdentity,after.dinosaurIdentity) and same(rich.settings,after.settings),"identity sidecar, fusion ledger and settings are preserved untouched while the flags are off")
 local un=newUser(id)
 check(NewRepo.load(un) and data[key(id)].dinosaurIdentity.instances~=nil,"flags back ON: the sidecar is reconciled again")
 NewRepo.release(un)
end

------------------------------------------------------------------ (1b) Known lock-out classes: Build 020 FAILS CLOSED on values it cannot validate
-- fail-closed = ProfileState "SchemaError", the stored profile is byte-identical afterwards, current code still loads it.
local function oldRejects(label,mutate)
 local p=copy(rich) mutate(p)
 local id=6000+checks
 local u=fresh(p,id)
 local before=copy(data[key(id)])
 local loaded=OldRepo.load(u)
 check(not loaded and u.attrs.ProfileState=="SchemaError","old reader fails closed: "..label)
 check(same(before,data[key(id)]),"old reader wrote nothing: "..label)
 -- Every write path of the old build is also inert for that player.
 OldRepo.renew(u) OldRepo.release(u)
 check(same(before,data[key(id)]),"old build writes nothing after SchemaError: "..label)
 local un=newUser(id)
 check(NewRepo.load(un) and un.attrs.ProfileState=="Loaded","current code loads it (roll-forward is the recovery): "..label)
 NewRepo.release(un)
end
-- Epic (4) / Legendary (5) species catches: metrics.rarest is stored on the new five-tier scale; Build 020 caps it at 3.
oldRejects("metrics.rarest 4 (Epic caught)",function(p) p.metrics.rarest=4 end)
oldRejects("metrics.rarest 5 (Legendary caught)",function(p) p.metrics.rarest=5 end)
-- Potions added after Build 020.
oldRejects("owned potion added after Build 020",function(p) p.progression.potions.loot_common=2 end)
oldRejects("active loot buff",function(p) p.progression.buffs.loot={id="loot_common",expiresAt=os.time()+500} end)
-- Fields Build 020 does not know about are harmless.
local function oldAccepts(label,mutate)
 local p=copy(rich) mutate(p)
 local id=6000+checks
 local u=fresh(p,id)
 check(OldRepo.load(u) and u.attrs.ProfileState=="Loaded","old reader accepts: "..label)
 OldRepo.release(u)
 check(same(data[key(id)].settings,p.settings) and same(data[key(id)].eggNests,p.eggNests),"old release keeps unknown fields: "..label)
end
oldAccepts("emerald counters and rotating potion-shop state",function(p)
 p.collection.compy.emerald=3
 p.progression.shop={window=12345,bought={speed_rare=1}}
end)
oldAccepts("progression.discovered (BD-436 discovery log)",function(p) p.progression.discovered={colours={green=true},patterns={},mutations={}} end)
oldAccepts("revealSkip on the five-tier scale (Build 020 has no such field)",function(p) p.revealSkip={1,5} end)
oldAccepts("future additive settings keys",function(p) p.settings.futureOption=true p.settings.v=2 end)
oldAccepts("nest with weatherId and unknown nest fields",function(p) p.eggNests[1].weatherId="rain" p.eggNests[1].futureField={1,2,3} end)
print("lock-out classes asserted: rarest>3 and post-Build-020 potions are rejected by Build 020; additive fields are kept")

------------------------------------------------------------------ (2b) BD-436: lazy backfill of the discovery log from owned dinos
do
 local p=copy(rich)
 p.progression.discovered=nil -- a profile saved before the log existed
 local id=6900
 local u=fresh(p,id)
 check(NewRepo.load(u) and u.attrs.ProfileState=="Loaded","current code loads a profile without a discovery log")
 local log=data[key(id)].progression.discovered
 check(type(log)=="table" and next(log.colours)~=nil and next(log.patterns)~=nil,"discovery log backfilled from owned dinos on load")
 local firstColour for c in log.colours do firstColour=c break end
 local counts=u.attrs.DiscoveryJson -- the mocked JSONEncode returns the table
 check(counts.colours>=1 and counts.patterns>=1,"owner-only DiscoveryJson carries counts")
 NewRepo.release(u)
 -- idempotent and add-only: a second load keeps the same log; extra ids already stored are never removed
 local stored=copy(data[key(id)])
 stored.session=nil
 stored.progression.discovered.colours["legacy_removed_colour"]=true
 put(id,stored)
 local u2=newUser(id)
 check(NewRepo.load(u2),"reload")
 local log2=data[key(id)].progression.discovered
 check(log2.colours.legacy_removed_colour==true and log2.colours[firstColour]==true,"backfill never removes a stored discovery (fused-away colour stays)")
 NewRepo.release(u2)
 -- junk in the optional field never locks the player out
 local junk=copy(rich) junk.progression.discovered="junk"
 local u3=fresh(junk,id+1)
 check(NewRepo.load(u3) and u3.attrs.ProfileState=="Loaded","a corrupt discovery field loads (replaced by a fresh log)")
 NewRepo.release(u3)
end
print("discovery log: backfill, add-only, corrupt-field tolerance asserted")

------------------------------------------------------------------ (3) OLD-written profile read by CURRENT code (settings, identity absent)
local OLDER=5100
local oldUser=newUser(OLDER)
check(OldRepo.load(oldUser),"old build creates a profile")
check(OldRepo.commitRunSettlement(oldUser,"old-run-1",25),"old build settles a run")
local oq=oldUser.attrs.ChestQueueJson
for i=1,2 do if oq and oq[i] then OldRepo.claimChest(oldUser,oq[i].id) end end
OldRepo.release(oldUser)
local legacy=copy(data[key(OLDER)])
check(legacy.settings==nil and legacy.dinosaurIdentity==nil and legacy.rarityScale==nil and legacy.eggNests==nil and legacy.runEggBank==nil,"old profile has none of the new fields")
local function legacyLoad(label,repo)
 put(OLDER,legacy)
 local u=newUser(OLDER)
 check(repo.load(u) and u.attrs.ProfileState=="Loaded","current code loads a Build 020 profile: "..label)
 local settings=u.attrs.SettingsJson
 check(settings.teleportShops==true and settings.effects=="full" and settings.sound.master==0.8,"absent settings (incl. teleportShops) read as defaults: "..label)
 repo.release(u)
 local after=data[key(OLDER)]
 check(after.settings==nil,"load never writes a defaults settings field: "..label)
 for species,entry in legacy.collection do for _,f in {"base","gold","diamond"} do check(entry[f]==after.collection[species][f],"collection count kept: "..species.."."..f) end end
 check(same(legacy.progression.auras,after.progression.auras) and legacy.progression.crystals==after.progression.crystals,"crystals/auras kept")
 check(same(legacy.eggs,after.eggs) and same(legacy.recentOperations,after.recentOperations) and legacy.pendingChestGrants==after.pendingChestGrants,"queued eggs and operation log kept")
 check(after.metrics.robux==legacy.metrics.robux and after.rarityScale==5,"metrics kept, rarityScale added once")
end
legacyLoad("identity off",Repository)
legacyLoad("playtest flags (identity sidecar created from the grouped collection)",NewRepo)
check(data[key(OLDER)].dinosaurIdentity~=nil and data[key(OLDER)].dinosaurIdentity.instances~=nil,"sidecar built on first persistent load")

------------------------------------------------------------------ (4) Failure modes: fallback without overwriting unreadable data
local function untouched(snapshot,id) return same(snapshot,data[key(id)]) and (snapshot~=nil or data[key(id)]==nil) end
local function noWrite(label,repo,id,stored,expectState)
 put(id,stored)
 local snapshot=if stored==nil then nil else copy(data[key(id)])
 local u=newUser(id)
 local loaded=repo.load(u)
 check(not loaded and u.attrs.ProfileState==expectState,label.." -> "..tostring(u.attrs.ProfileState).." (expected "..expectState..")")
 check(untouched(snapshot,id),label.." left the stored value untouched")
 -- Normal save paths must not treat the unloaded player as writable either.
 repo.commitRunSettlement(u,"x-"..id,10)
 if repo.setSettings then repo.setSettings(u,{v=1}) end
 repo.renew(u) repo.release(u)
 check(untouched(snapshot,id),label.." still untouched after settlement, setSettings, renew and release")
end
local base=copy(rich) base.session=nil
local function variant(f) local p=copy(base) f(p) return p end
for _,pair in {{"NEW",NewRepo},{"OLD",OldRepo}} do
 local name,repo=pair[1],pair[2]
 local n=7000+(if name=="OLD" then 100 else 0)
 noWrite(name.." future schemaVersion 2",repo,n+1,variant(function(p) p.schemaVersion=2 end),"SchemaError")
 noWrite(name.." schemaVersion missing",repo,n+2,variant(function(p) p.schemaVersion=nil end),"SchemaError")
 noWrite(name.." partial write: collection missing",repo,n+3,variant(function(p) p.collection=nil end),"SchemaError")
 noWrite(name.." partial write: recentOperations missing",repo,n+4,variant(function(p) p.recentOperations=nil end),"SchemaError")
 noWrite(name.." partial write: eggs is a string",repo,n+5,variant(function(p) p.eggs="{trunc" end),"SchemaError")
 noWrite(name.." partial write: metrics missing keys",repo,n+6,variant(function(p) p.metrics={playSeconds=1} end),"SchemaError")
 noWrite(name.." negative revision",repo,n+7,variant(function(p) p.revision=-5 end),"SchemaError")
 noWrite(name.." whole value is a truncated JSON string",repo,n+8,"{\"schemaVersion\":1,\"collection\":{","SchemaError")
 noWrite(name.." whole value is a number",repo,n+9,12345,"SchemaError")
 noWrite(name.." whole value is boolean false",repo,n+10,false,"SchemaError")
 noWrite(name.." unknown equipped species",repo,n+11,variant(function(p) p.equippedSpeciesId="not_a_dino" end),"SchemaError")
 noWrite(name.." negative crystals",repo,n+12,variant(function(p) p.progression.crystals=-1 end),"SchemaError")
 if name=="NEW" then
  noWrite(name.." huge arrays: eggNests over the structural ceiling",repo,n+13,variant(function(p) p.eggNests={} for i=1,60 do p.eggNests[i]={nestId="n"..i,droppedFromRun="r",size=3,luck=1,state="waiting"} end end),"SchemaError")
  noWrite(name.." huge arrays: runEggBank 5001 eggs",repo,n+14,variant(function(p) p.runEggBank={} for i=1,5001 do p.runEggBank[i]=copy(base.runEggBank[1]) p.runEggBank[i].eggId="e"..i end end),"SchemaError")
  noWrite(name.." huge arrays: pendingNests 1001",repo,n+15,variant(function(p) p.pendingNests={} for i=1,1001 do p.pendingNests[i]={nestId="n"..i,eggs={}} end end),"SchemaError")
 end
end
-- Corrupted settings: cosmetic data must never lock a player out (BD-320 fix) nor be overwritten by a load/renew.
for i,junk in {"garbage",12345,true,{1,2,3},{sound="x",effects=99,calm="yes",peaceful={},teleportShops={},jumpSize=false},{sound={master=1e308,sfx=-7,ambience="loud"}}} do
 for _,pair in {{"NEW",NewRepo},{"OLD",OldRepo}} do
  local repo=pair[2]
  local id=7200+i*2+(if pair[1]=="OLD" then 1 else 0)
  local p=variant(function(p) p.settings=junk end)
  put(id,p)
  local u=newUser(id)
  check(repo.load(u) and u.attrs.ProfileState=="Loaded",pair[1].." loads a profile whose settings are corrupted ("..typeof(junk)..")")
  if pair[1]=="NEW" then
   local s=u.attrs.SettingsJson
   check(s.sound.master>=0 and s.sound.master<=1 and s.sound.sfx>=0 and s.sound.sfx<=1 and (s.effects=="full" or s.effects=="lite" or s.effects=="off") and type(s.calm)=="boolean" and type(s.teleportShops)=="boolean","corrupt settings fall back to valid values/defaults (case "..i..")")
  end
  repo.renew(u)
  check(same(junk,data[key(id)].settings),pair[1].." load/renew keep the stored settings value as it was (case "..i..")")
  if pair[1]=="NEW" then
   check(NewRepo.setSettings(u,{v=1,sound={master=0.2,sfx=0.2,ambience=0.2},effects="off",weather="off",calm=false,jumpSize="small",peaceful=false,teleportShops=true}) and data[key(id)].settings.v==1,"the next normal settings save replaces the corrupt value")
  end
  repo.release(u)
 end
end
-- DataStore errors: nothing is written, state is LoadFailed, and a NEW player is not given a defaults profile.
for _,pair in {{"NEW",NewRepo},{"OLD",OldRepo}} do
 local repo=pair[2]
 local id=7300+(if pair[1]=="OLD" then 1 else 0)
 data[key(id)]=nil
 failMode="all"
 local u=newUser(id)
 check(not repo.load(u) and u.attrs.ProfileState=="LoadFailed" and data[key(id)]==nil,pair[1].." DataStore outage on a new player: LoadFailed, no defaults written")
 failMode=nil
 local stored=variant(function() end) put(id,stored)
 local snapshot=copy(data[key(id)])
 failMode="all"
 u=newUser(id)
 check(not repo.load(u) and u.attrs.ProfileState=="LoadFailed" and untouched(snapshot,id),pair[1].." DataStore outage on an existing player: LoadFailed, stored profile untouched")
 failMode=nil
 check(repo.load(u) and u.attrs.ProfileState=="Loaded","recovers when the DataStore returns")
 -- A save that fails mid-session leaves the previous committed profile intact.
 failMode="all"
 local before=copy(data[key(id)])
 repo.commitRunSettlement(u,"outage-run",10)
 if repo.setSettings then repo.setSettings(u,{v=1}) end
 failMode=nil
 check(same(before,data[key(id)]),pair[1].." failed saves left the committed profile unchanged")
 repo.release(u)
end
-- Live lease on a profile: a second server never overwrites it either (rollback while players are still online).
do
 local id=7400
 local p=variant(function(p) p.session={leaseId="other-server",jobId="x",expiresAt=os.time()+80,metricsAt=os.time()} end)
 put(id,p)
 local snapshot=copy(data[key(id)])
 local uo=newUser(id)
 check(not OldRepo.load(uo) and uo.attrs.ProfileState=="SessionBusy" and untouched(snapshot,id),"old build respects a live lease from another server (SessionBusy, no write)")
 local un=newUser(id)
 check(not NewRepo.load(un) and un.attrs.ProfileState=="SessionBusy" and untouched(snapshot,id),"current build respects a live lease from another server")
 data[key(id)].session.expiresAt=os.time()-1
 check(OldRepo.load(newUser(id)),"an expired lease from the other build is taken over (no permanent lock-out)")
end

print(string.format("Rollback drill verified (offline Luau, mocked DataStore): %d checks. Studio, real DataStore versioning and a real publish revert are NOT covered (BD-320 stays open for the owner).",checks))
