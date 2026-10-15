"""Execute the BD-057 Phase 1 identity fusion transaction with the pinned Luau runtime.
Pure modules only: no DataStore, Studio or UI. Controlled test rollers exercise the
transaction; FusionOdds (BD-064 PROVISIONAL formula) is checked for normalization,
sampling parity and deterministic committed outcomes.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
def module(path):
    return '(function()\n' + (ROOT/path).read_text() + '\nend)()'
def script():
    return ('local I=' + module('src/server/DinosaurIdentity.luau') + '\n'
        + 'local script={Parent={DinosaurIdentity="Identity"}}\n'
        + 'local require=function(id) assert(id=="Identity") return I end\n'
        + 'local F=' + module('src/server/IdentityFusion.luau') + '\n'
        + 'local PC=' + module('src/shared/ProgressionConfig.luau') + '\n'
        + 'local script={Parent={ProgressionConfig="PC"}}\n'
        + 'local require=function(id) assert(id=="PC") return PC end\n'
        + 'local G=' + module('src/shared/EggGenetics.luau') + '\n'
        + 'local O=' + module('src/server/FusionOdds.luau') + '\n' + r'''
local function count(t) local n=0 for _ in t do n+=1 end return n end
local same=function(a,b) return F.canonical(a)==F.canonical(b) end
local OWNER="u:1"
local function genes(pattern,primary) return {patternId=pattern,primaryColorId=primary or "green",secondaryColorId="blue",blend=20,hatchSuccess=true} end

-- Fixture: grouped collection + reconciled identity sidecar built through the real
-- BD-060 hatch/reconcile path (variants carry saved egg patterns; plain buckets do not).
local function fixture()
 local profile={collection={
  compy={base=3,gold=1,diamond=0,events={frost=1},variants={}},
  raptor={base=0,gold=0,diamond=0,events={},variants={}},
 }}
 profile.dinosaurIdentity=assert(I.reconcile(profile.collection,nil,OWNER))
 local n=0
 local function hatch(species,key,g,qty,traits)
  n+=1
  local egg={eggId="egg-"..n,kind="alpha_chest",eventId="clear",mutationId=traits and traits.mutationId or "",
   big=traits and traits.big or false,shiny=traits and traits.shiny or false,genes=I.copy(g),readyAt=0,reward={speciesId=species,count=qty}}
  local entry=profile.collection[species]
  local v=entry.variants[key] or {count=0,genes=I.copy(g),big=egg.big,shiny=egg.shiny,mutationId=egg.mutationId}
  v.count+=qty entry.variants[key]=v
  I.hatch(profile.dinosaurIdentity,egg,species,qty,species.."/variant/"..key)
  profile.dinosaurIdentity=assert(I.reconcile(profile.collection,profile.dinosaurIdentity,OWNER))
 end
 for _=1,15 do hatch("compy","wavyA",genes("06_wavy_stripes"),1) end -- egg-1..15: 15 plain (1 dino per egg)
 hatch("compy","wavyB",genes("06_wavy_stripes","red"),2,{shiny=true})             -- egg-5: 2 Shiny
 hatch("compy","wavyC",genes("06_wavy_stripes","teal"),1,{big=true,mutationId="ember"}) -- egg-6
 hatch("compy","spots",genes("02_spots"),1)                                       -- egg-7
 hatch("raptor","wavyR",genes("06_wavy_stripes"),1)                               -- egg-8
 return profile
end
local function idsIn(profile,bucketKey)
 local list={}
 for id,d in profile.dinosaurIdentity.instances do if d.bucketKey==bucketKey then table.insert(list,id) end end
 table.sort(list) return list
end
local function concat(...) local r={} for _,t in {...} do for _,v in t do table.insert(r,v) end end return r end
local function take(t,n) local r={} for i=1,n do r[i]=t[i] end return r end

local rolls=0
local roller={version="test-fixed-v1",roll=function(summary,patternId)
 rolls+=1
 assert(summary.donorCount==F.Recipes[summary.targetStage or "gold"].donorCount and type(summary.speciesId)=="string")
 for k,v in summary do assert(type(k)=="string" and not string.find(k,"prob") and not string.find(k,"odds")) end
 return {big=false,shiny=true,mutationId="",genes={patternId=patternId,primaryColorId="gold",secondaryColorId="blue",blend=55}}
end}

-- Full prepare path used by callers: quote -> outcome once -> apply inside the transform.
local function prepare(profile,token,donors,stage,consent)
 local quote=assert(F.quote(profile.dinosaurIdentity,OWNER,stage or "gold",donors))
 local outcome=assert(F.prepareOutcome(quote,roller))
 local request={token=token,targetStage=stage or "gold",donorIds=donors,quoteDigest=quote.quoteDigest,
  consentDigest=if consent then quote.consentDigest else nil}
 return quote,outcome,request
end
local function rejects(profile,request,outcome,expected,label)
 local before=F.canonical(profile)
 local result,reason=F.apply(profile,OWNER,request,outcome,10)
 assert(result==nil and reason==expected,(label or expected)..": got "..tostring(reason))
 assert(F.canonical(profile)==before,(label or expected)..": input mutated")
end

-- ===== Happy path =====
local profile=fixture()
local plain=idsIn(profile,"compy/variant/wavyA")
assert(#plain==15)
local snapshot=F.canonical(profile)
local nextBefore=profile.dinosaurIdentity.nextId
local livingBefore=count(profile.dinosaurIdentity.instances)
local quote,outcome,request=prepare(profile,"tok-1",plain)
assert(quote.consentRequired==false and #quote.lossManifest==0)
assert(quote.speciesId=="compy" and quote.patternId=="06_wavy_stripes" and quote.recipeVersion=="gold-same-species-pattern-15-v1")
assert(rolls==1 and outcome.oddsVersion=="test-fixed-v1" and outcome.targetStage=="gold")
local fused,status,result=F.apply(profile,OWNER,request,outcome,1234)
assert(fused and status=="fused",tostring(status))
assert(F.canonical(profile)==snapshot,"input profile mutated")
local state=fused.dinosaurIdentity
local resultId=OWNER.."/d:"..nextBefore
assert(result.resultId==resultId and state.nextId==nextBefore+1)
assert(count(state.instances)==livingBefore-15+1)
for _,id in plain do assert(state.instances[id]==nil) end
local gold=state.instances[resultId]
assert(gold.stage=="gold" and gold.speciesId=="compy" and gold.bucketKey=="compy/gold")
assert(gold.genes.patternId=="06_wavy_stripes" and gold.genes.primaryColorId=="gold" and gold.shiny==true)
assert(next(gold.cosmetics.ownedAuraIds)==nil and next(gold.cosmetics.ownedTrailIds)==nil and gold.cosmetics.equippedAuraId=="")
assert(gold.origin.kind=="fusion" and gold.origin.operationId=="fusion:tok-1" and #gold.origin.parents==15 and gold.origin.parentStage=="base")
assert(gold.origin.recipeVersion==quote.recipeVersion and gold.origin.oddsVersion=="test-fixed-v1")
for _,p in gold.origin.parents do assert(p.cosmetics==nil and p.origin.kind=="hatch" and p.speciesId==nil and p.genes.patternId==nil) end
-- Grouped projection: wavyA removed, Gold +1, every other bucket unchanged.
local before=profile.collection
local after=fused.collection
assert(after.compy.variants.wavyA==nil and after.compy.gold==before.compy.gold+1)
assert(after.compy.base==before.compy.base and after.compy.diamond==before.compy.diamond)
assert(same(after.compy.events,before.compy.events) and same(after.raptor,before.raptor))
for _,key in {"wavyB","wavyC","spots"} do assert(same(after.compy.variants[key],before.compy.variants[key])) end
-- Durable ledger + archived parent eggs.
local entry=state.fusions["fusion:tok-1"]
assert(entry.resultId==resultId and entry.committedAt==1234 and same(entry.parentIds,quote.donorIds))
assert(#entry.parentEggIds==15,"parent eggs should be distinct")
for i=1,15 do assert(state.eggs["egg-"..i] and table.find(entry.parentEggIds,"egg-"..i)) end
local lineage=assert(F.lineage(state,"fusion:tok-1"))
assert(lineage.resultId==resultId and #lineage.parentIds==15 and count(lineage.parentEggs)==15)
assert(lineage.parentEggs["egg-1"].genes.patternId=="06_wavy_stripes")
-- Reload: saved state reconciles unchanged; fused record and nextId stay.
local reloaded=assert(I.reconcile(fused.collection,I.copy(state),OWNER))
assert(same(reloaded,state))
print("Fusion happy path passed: 15 consumed, one new server ID, nextId+1, guaranteed Gold, empty cosmetics, untouched input, grouped projection, ledger, parent eggs and reload")

-- ===== Invalid donors (all fail before any write) =====
local p=fixture()
local A=idsIn(p,"compy/variant/wavyA")
local st=p.dinosaurIdentity
local function bad(donors,expected,stage,owner)
 local q,reason=F.quote(st,owner or OWNER,stage or "gold",donors)
 assert(q==nil and reason==expected,expected..": got "..tostring(reason))
end
bad(take(A,14),"wrong_donor_count")
bad(concat(A,idsIn(p,"compy/variant/wavyB")),"wrong_donor_count")
local extra=I.copy(A) extra.note="x" bad(extra,"wrong_donor_count")
bad("u:1/d:1","wrong_donor_count")
local dup=take(A,14) table.insert(dup,A[1]) bad(dup,"duplicate_donor")
local missing=take(A,14) table.insert(missing,OWNER.."/d:9999") bad(missing,"donor_missing")
local foreign=take(A,14) table.insert(foreign,"u:2/d:1") bad(foreign,"wrong_owner")
local numeric=take(A,14) table.insert(numeric,42) bad(numeric,"invalid_donor_id")
local plainBase=take(A,14) table.insert(plainBase,idsIn(p,"compy/base")[1]) bad(plainBase,"missing_pattern")
local wrongStage=take(A,14) table.insert(wrongStage,idsIn(p,"compy/gold")[1]) bad(wrongStage,"wrong_stage")
local species=take(A,14) table.insert(species,idsIn(p,"raptor/variant/wavyR")[1]) bad(species,"species_mismatch")
local pattern=take(A,14) table.insert(pattern,idsIn(p,"compy/variant/spots")[1]) bad(pattern,"pattern_mismatch")
st.instances[A[3]].locked=true bad(A,"donor_locked") st.instances[A[3]].locked=nil
st.instances[A[4]].favorited=true bad(A,"donor_locked") st.instances[A[4]].favorited=nil
bad(A,"wrong_owner","gold","u:2")
bad(take(A,4),"wrong_stage","emerald")
bad(take(A,2),"wrong_stage","diamond")
bad(A,"wrong_donor_count","emerald")
bad(A,"wrong_donor_count","diamond")
do local saved=F.Recipes.emerald.donorCount F.Recipes.emerald.donorCount=nil bad(take(A,4),"recipe_not_approved","emerald") F.Recipes.emerald.donorCount=saved end
bad(A,"unknown_stage","base")
bad(A,"unknown_stage","platinum")
bad(A,"unknown_stage",5)
assert(F.quote(nil,OWNER,"gold",A)==nil)
-- Same rejections inside apply leave the profile untouched.
local _,o1,r1=prepare(p,"inv",A)
local r9=I.copy(r1) r9.donorIds=take(A,14) rejects(p,r9,o1,"wrong_donor_count")
local rs=I.copy(r1) rs.donorIds=species rejects(p,rs,o1,"species_mismatch")
local rt=I.copy(r1) rt.token="" rejects(p,rt,o1,"invalid_token")
rt.token=string.rep("x",F.MaxTokenLength+1) rejects(p,rt,o1,"invalid_token")
rt.token=7 rejects(p,rt,o1,"invalid_token")
local ws=F.apply(p,"u:2",r1,o1) assert(ws==nil)
print("Invalid donors passed: 14/16/non-list, duplicate, missing, foreign, non-string, no pattern, wrong stage/species/pattern, locked/favorited, wrong owner, Base donors for Emerald/Diamond, unapproved recipe, unknown stage, bad token")

-- ===== Consent: valuable traits and purchased cosmetics =====
p=fixture()
A=idsIn(p,"compy/variant/wavyA")
local B=idsIn(p,"compy/variant/wavyB")
local mixed=concat(take(A,13),B)
p.dinosaurIdentity.instances[A[1]].cosmetics.ownedAuraIds.meadow=true
p.dinosaurIdentity.instances[A[1]].cosmetics.ownedTrailIds.fern=true
p.dinosaurIdentity.instances[A[1]].cosmetics.equippedAuraId="meadow"
local q2,o2,r2=prepare(p,"consent",mixed)
assert(q2.consentRequired and #q2.lossManifest==3)
local loss={} for _,l in q2.lossManifest do loss[l.instanceId]=l end
assert(loss[A[1]].auraIds[1]=="meadow" and loss[A[1]].trailIds[1]=="fern" and loss[A[1]].equippedAuraId=="meadow")
assert(loss[B[1]].shiny and loss[B[2]].shiny)
rejects(p,r2,o2,"consent_required","missing consent")
local wrong=I.copy(r2) wrong.consentDigest="deadbeef" rejects(p,wrong,o2,"consent_required","wrong consent")
r2.consentDigest=q2.consentDigest
local consented,cs=F.apply(p,OWNER,r2,o2,1)
assert(cs=="fused")
local out=consented.dinosaurIdentity.instances[consented.dinosaurIdentity.fusions["fusion:consent"].resultId]
assert(next(out.cosmetics.ownedAuraIds)==nil and next(out.cosmetics.ownedTrailIds)==nil and out.cosmetics.equippedAuraId=="")
for _,parent in out.origin.parents do assert(parent.cosmetics==nil) end
assert(consented.collection.compy.variants.wavyA.count==2 and consented.collection.compy.variants.wavyB==nil)
-- Big+mutation donor alone is also itemized.
local q3=assert(F.quote(p.dinosaurIdentity,OWNER,"gold",concat(take(A,14),idsIn(p,"compy/variant/wavyC"))))
assert(q3.consentRequired and q3.lossManifest[#q3.lossManifest].big and q3.lossManifest[#q3.lossManifest].mutationId=="ember")
-- Consent digest is bound to the exact loss set.
p.dinosaurIdentity.instances[A[1]].cosmetics.ownedAuraIds.tidal=true
local q4=assert(F.quote(p.dinosaurIdentity,OWNER,"gold",mixed))
assert(q4.consentDigest~=q2.consentDigest)
print("Consent passed: itemized aura/trail/equipped and Shiny/BIG/mutation losses, missing/wrong digest rollback, no cosmetic transfer")

-- ===== Idempotency, retries, conflicts, stale writers and concurrency =====
p=fixture()
A=idsIn(p,"compy/variant/wavyA")
local q5,o5,r5=prepare(p,"retry",A)
local c1,s1,res1=F.apply(p,OWNER,r5,o5,1)
assert(s1=="fused")
-- Commit-then-throw: the retried transform sees the committed value and replays.
local c2,s2,res2=F.apply(c1,OWNER,r5,o5,2)
assert(s2=="duplicate" and c2==c1 and same(res1,res2))
-- Retry with a different (rerolled) outcome still returns the committed traits.
local reroll=I.copy(o5) reroll.traits.genes.primaryColorId="black"
local c3,s3,res3=F.apply(c1,OWNER,r5,reroll,3)
assert(s3=="duplicate" and c3==c1 and res3.traits.genes.primaryColorId=="gold")
-- Donor order is not part of request identity.
local reversed=I.copy(r5) reversed.donorIds={} for i=#A,1,-1 do table.insert(reversed.donorIds,A[i]) end
local _,s4=F.apply(c1,OWNER,reversed,nil) assert(s4=="duplicate")
-- Same token, different request -> conflict, no write.
local conflict=I.copy(r5) conflict.donorIds=concat(take(A,13),idsIn(c1,"compy/variant/wavyB"))
rejects(c1,conflict,o5,"token_conflict")
-- Duplicate replay needs no odds/outcome.
local _,s5=F.apply(c1,OWNER,r5,nil) assert(s5=="duplicate")
-- Stale quote: a donor changes after quoting.
p=fixture()
A=idsIn(p,"compy/variant/wavyA")
local _,o6,r6=prepare(p,"stale",A)
p.dinosaurIdentity.instances[A[2]].cosmetics.ownedTrailIds.nova=true
rejects(p,r6,o6,"stale_quote","donor changed")
p.dinosaurIdentity.instances[A[2]].cosmetics.ownedTrailIds.nova=nil
local forged=I.copy(r6) forged.quoteDigest="0" rejects(p,forged,o6,"stale_quote","forged quote digest")
local forgedOutcome=I.copy(o6) forgedOutcome.quoteDigest="0" rejects(p,r6,forgedOutcome,"stale_quote","outcome from old quote")
-- Overlapping concurrent fusions quoted from the same snapshot: second loses cleanly.
p=fixture()
A=idsIn(p,"compy/variant/wavyA")
B=idsIn(p,"compy/variant/wavyB")
local _,oa,ra=prepare(p,"first",A)
local overlap=concat(take(A,13),B)
local _,ob,rb=prepare(p,"second",overlap,nil,true)
local afterFirst=assert(F.apply(p,OWNER,ra,oa,1))
rejects(afterFirst,rb,ob,"donor_missing","overlapping fusion")
assert(afterFirst.dinosaurIdentity.fusions["fusion:second"]==nil)
print("Idempotency passed: commit-then-throw replay, no reroll on retry, order-insensitive token, token conflict, stale quote/digests, overlapping concurrent fusion")

-- ===== Rollback on every failure class =====
p=fixture()
A=idsIn(p,"compy/variant/wavyA")
local q7,o7,r7=prepare(p,"rollback",A)
local limit=F.MaxSidecarBytes
F.MaxSidecarBytes=100
rejects(p,r7,o7,"storage_limit")
F.MaxSidecarBytes=limit
assert(F.encodedSize({a=1,b={1,2},c="x\"y",d=true})==#'{"a":1,"b":[1,2],"c":"x\\"y","d":true}')
assert(F.encodedSize(p.dinosaurIdentity)<F.MaxSidecarBytes)
assert(F.prepareOutcome(q7,nil)==nil)
assert(select(2,F.prepareOutcome(q7,nil))=="odds_not_approved")
assert(select(2,F.prepareOutcome(q7,{version="",roll=roller.roll}))=="odds_not_approved")
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function() error("boom") end}))=="invalid_outcome")
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function(_,pt) return {big=false,shiny=false,mutationId="",stage="diamond",genes={patternId=pt,primaryColorId="a",secondaryColorId="b",blend=1}} end}))=="invalid_outcome")
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function() return {big=false,shiny=false,mutationId="",genes={patternId="02_spots",primaryColorId="a",secondaryColorId="b",blend=1}} end}))=="invalid_outcome")
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function(_,pt) return {big=false,shiny=false,mutationId="",genes={patternId=pt,primaryColorId="a",secondaryColorId="b",blend=101}} end}))=="invalid_outcome")
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function(_,pt) return {big=false,shiny=false,mutationId="",genes={patternId=pt,primaryColorId="a",secondaryColorId="b",conditionId="normal",blend=1}} end}))=="invalid_outcome","a rolled condition on a dinosaur is rejected")
assert(select(2,F.prepareOutcome(q7,roller,function() return false end))=="invalid_outcome")
-- Roller summaries are copies; mutation cannot affect the quote.
assert(F.prepareOutcome(q7,{version="v",roll=function(s,pt) s.speciesId="trex" return roller.roll({donorCount=15,speciesId="compy"},pt) end}))
assert(q7.summary.speciesId=="compy")
rejects(p,r7,nil,"invalid_outcome","no outcome")
local tampered=I.copy(o7) tampered.traits.genes.patternId="02_spots" rejects(p,r7,tampered,"invalid_outcome","pattern not locked")
tampered=I.copy(o7) tampered.targetStage="diamond" rejects(p,r7,tampered,"invalid_outcome","stage from outcome")
tampered=I.copy(o7) tampered.requestDigest="x" rejects(p,r7,tampered,"invalid_outcome","outcome for another request")
-- Grouped/identity mismatch: projection cannot cover the consumption.
local mismatch=I.copy(p) mismatch.collection.compy.variants.wavyA.count=14 rejects(mismatch,r7,o7,"grouped_mismatch")
mismatch=I.copy(p) mismatch.collection.compy=nil rejects(mismatch,r7,o7,"grouped_mismatch","missing species entry")
-- Corrupt ledger / identity.
local corrupt=I.copy(p) corrupt.dinosaurIdentity.fusions="bad" rejects(corrupt,r7,o7,"invalid_fusion_ledger")
corrupt=I.copy(p) corrupt.dinosaurIdentity=nil rejects(corrupt,r7,o7,"identity_unavailable")
-- Fail-closed: a stage without a grouped projection never commits.
local emerald=F.Recipes.emerald
F.Recipes.emerald={targetStage="emerald",sourceStage="base",donorCount=15,version="test-only"}
F.GroupedProjection.emerald=nil
local qe=assert(F.quote(p.dinosaurIdentity,OWNER,"emerald",A))
local oe=assert(F.prepareOutcome(qe,roller))
rejects(p,{token="em",targetStage="emerald",donorIds=A,quoteDigest=qe.quoteDigest},oe,"projection_unsupported")
F.Recipes.emerald=emerald F.GroupedProjection.emerald=true
assert(F.quote(p.dinosaurIdentity,OWNER,"emerald",A)==nil)
-- A valid commit still succeeds after all the rejected attempts.
assert(select(2,F.apply(p,OWNER,r7,o7,1))=="fused")
print("Rollback passed: storage_limit, odds_not_approved, invalid/forged outcomes, grouped mismatch, corrupt ledger, Emerald projection gate; input byte-identical after every failure")

-- ===== Lineage integrity and reconciliation safety =====
p=fixture()
A=idsIn(p,"compy/variant/wavyA")
local _,o8,r8=prepare(p,"lineage",A)
local f8=assert(F.apply(p,OWNER,r8,o8,1))
local s8=f8.dinosaurIdentity
local rid=s8.fusions["fusion:lineage"].resultId
-- Later hatches and reconciles keep the fused record and archived parent eggs.
local egg={eggId="egg-later",kind="alpha_chest",genes=genes("02_spots"),reward={speciesId="compy",count=2}}
f8.collection.compy.variants.spots.count+=2
I.hatch(s8,egg,"compy",2,"compy/variant/spots")
s8=assert(I.reconcile(f8.collection,s8,OWNER))
f8.collection.compy.base+=5
s8=assert(I.reconcile(f8.collection,s8,OWNER))
assert(s8.instances[rid].origin.kind=="fusion")
for i=1,15 do assert(s8.eggs["egg-"..i]) end
local lin=assert(F.lineage(s8,"fusion:lineage"))
assert(count(lin.parentEggs)==15 and lin.parentEggs["egg-2"].eggId=="egg-2")
lin.parentEggs["egg-2"].eventId="tampered" assert(s8.eggs["egg-2"].eventId~="tampered")
assert(F.lineage(s8,"fusion:none")==nil)
-- Legacy Build 020 Gold->Diamond decrement spends the legacy Gold, keeps the fused one.
assert(f8.collection.compy.gold==2)
f8.collection.compy.gold=1 f8.collection.compy.diamond=1
local spent=assert(I.reconcile(f8.collection,s8,OWNER))
assert(spent.instances[rid] and #idsIn({dinosaurIdentity=spent},"compy/gold")==1)
-- Removing the last Gold would delete the crafted result: fail closed instead.
f8.collection.compy.gold=0
local none,why=I.reconcile(f8.collection,spent,OWNER)
assert(none==nil and why=="protected_identity" and spent.instances[rid])
f8.collection.compy.gold=1
-- A fusion record without its ledger entry (or with a mismatched one) is rejected.
local noLedger=I.copy(spent) noLedger.fusions["fusion:lineage"]=nil
assert(select(2,I.reconcile(f8.collection,noLedger,OWNER))=="missing_fusion_ledger")
local wrongLedger=I.copy(spent) wrongLedger.fusions["fusion:lineage"].resultId=OWNER.."/d:1"
assert(select(2,I.reconcile(f8.collection,wrongLedger,OWNER))=="missing_fusion_ledger")
local badRecord=I.copy(spent) badRecord.instances[rid].bucketKey="fusion/"..rid
assert(select(2,I.reconcile(f8.collection,badRecord,OWNER))=="invalid_instance")
local futureId=I.copy(spent) futureId.nextId=1
assert(I.reconcile(f8.collection,futureId,OWNER)==nil)
-- The ledger is retained so a replay after reload still resolves.
assert(select(2,F.apply({collection=f8.collection,dinosaurIdentity=spent},OWNER,r8,nil))=="duplicate")
print("Lineage passed: parent eggs survive consumption, later hatches and grants; legacy Gold decrement keeps fused result or fails closed; ledgerless/mismatched records rejected")

-- ===== Storage and capacity limits =====
-- Many sequential fusions grow the ledger linearly and never exceed the preflight.
p=fixture()
local key="compy/variant/bulk"
local bulk=genes("06_wavy_stripes","bulk")
local sizes={}
for round=1,20 do
 local e={eggId="bulk-"..round,kind="alpha_chest",genes=I.copy(bulk),reward={speciesId="compy",count=1}}
 local v=p.collection.compy.variants.bulk or {count=0,genes=I.copy(bulk),big=false,shiny=false,mutationId=""}
 for k=1,15 do
  local ek=I.copy(e) ek.eggId=e.eggId.."-"..k
  v.count+=1 p.collection.compy.variants.bulk=v
  I.hatch(p.dinosaurIdentity,ek,"compy",1,key)
 end
 p.dinosaurIdentity=assert(I.reconcile(p.collection,p.dinosaurIdentity,OWNER))
 local donors=idsIn(p,key)
 assert(#donors==15)
 local _,ob2,rb2=prepare(p,"bulk-"..round,donors)
 local nextP,stt=F.apply(p,OWNER,rb2,ob2,round)
 assert(stt=="fused",tostring(stt))
 p=nextP
 sizes[round]=F.encodedSize(p.dinosaurIdentity)
end
assert(count(p.dinosaurIdentity.fusions)==20 and p.collection.compy.gold==21)
assert(count(p.dinosaurIdentity.eggs)>=300,"all 300 parent eggs archived")
local perFusion=(sizes[20]-sizes[10])/10
assert(perFusion>0 and perFusion<60000,"per-fusion growth "..perFusion)
print(string.format("Storage passed: 20 sequential 15-donor fusions, 300 archived parent eggs, ~%d bytes per fusion (estimate), preflight ceiling %d bytes", perFusion, F.MaxSidecarBytes))
-- The 3,000-identity ceiling still applies to the reconciled post-fusion state.
local big=fixture()
big.collection.compy.base=I.MaxInstances
local _,obg,rbg=prepare(fixture(),"cap",idsIn(fixture(),"compy/variant/wavyA"))
rejects(big,rbg,obg,"identity_capacity")
-- ===== BD-064 PROVISIONAL odds (FusionOdds) =====
assert(O.Version=="fusion-odds-provisional-v2")
local function near(a,b,eps) return math.abs(a-b)<=(eps or 1e-12) end
local function sum(t) local s=0 for _,v in t do s+=v end return s end
-- Summary builder in IdentityFusion's neutral shape.
local function summaryOf(spec)
 local s={speciesId="compy",patternId="06_wavy_stripes",targetStage="gold",donorCount=10,shinyCount=spec.shiny or 0,
  bigCount=spec.big or 0,mutationCounts=spec.mutations or {},colors={}}
 for i=1,10 do
  local c=(spec.colors or {})[i] or {"green","blue"}
  table.insert(s.colors,{primaryColorId=c[1],secondaryColorId=c[2],blend=20})
 end
 return s
end
local function checkNormalized(d)
 assert(d.shiny>=0 and d.shiny<=1 and d.big>=0 and d.big<=1)
 assert(near(sum(d.mutation)+d.noMutation,1),"mutation wheel sums to 1")
 assert(d.condition==nil,"dinosaurs have no condition wheel")
 assert(near(sum(d.primaryColor),1) and near(sum(d.secondaryColor),1))
 assert(near(sum(O.mutationWheel(d)),1))
end
-- Shiny 0/2/10 donors and BIG.
for _,case in {{0,0},{1,0.05},{2,0.1},{5,0.25},{10,0.5}} do
 local d=assert(O.distribution(summaryOf({shiny=case[1],big=case[1]})))
 checkNormalized(d)
 assert(near(d.shiny,case[2]) and near(d.big,case[2]),"shiny "..case[1])
end
-- Mutations: P(any) = 0.5 x mutated/10, specific proportional to donor counts.
local mixedSpec={shiny=2,big=1,mutations={ember=2,frost=1},
 colors={{"green","blue"},{"green","blue"},{"green","green"},{"red","blue"},{"green","white"},{"green","blue"},{"teal","blue"},{"green","blue"},{"green","blue"},{"green","blue"}}}
local mixed=assert(O.distribution(summaryOf(mixedSpec)))
checkNormalized(mixed)
assert(near(mixed.mutation.ember,0.1) and near(mixed.mutation.frost,0.05) and near(mixed.noMutation,0.85))
assert(near(mixed.primaryColor.green,0.8) and near(mixed.primaryColor.red,0.1) and near(mixed.primaryColor.teal,0.1))
assert(near(mixed.secondaryColor.blue,0.8) and near(mixed.secondaryColor.green,0.1) and near(mixed.secondaryColor.white,0.1))
assert(mixed.primaryColor.black==nil and mixed.secondaryColor.black==nil,"no color from 0% ancestry")
local allMutated=assert(O.distribution(summaryOf({mutations={ember=10}})))
assert(near(allMutated.mutation.ember,0.5) and near(allMutated.noMutation,0.5))
local none=assert(O.distribution(summaryOf({})))
assert(next(none.mutation)==nil and none.noMutation==1 and none.shiny==0 and none.big==0)
-- Malformed summaries fail closed.
assert(O.distribution(nil)==nil)
local broken=summaryOf({}) broken.donorCount=0 assert(O.distribution(broken)==nil)
broken=summaryOf({}) broken.shinyCount=11 assert(O.distribution(broken)==nil)
broken=summaryOf({}) broken.mutationCounts={ember=11} assert(O.distribution(broken)==nil)
broken=summaryOf({}) table.remove(broken.colors) assert(O.distribution(broken)==nil)
print("Odds normalization passed: 0/1/2/5/10 Shiny -> 0/5/10/25/50%, BIG, proportional mutations/no-mutation, color wheels sum to 1, no 0%-ancestry outcomes")

-- Parity: sampling the roll function reproduces the quoted distribution.
-- Luau's seeded math.random (PCG32) gives reproducible uniforms in [0, 1).
local function seededUniform(seed)
 math.randomseed(seed)
 return function() return math.random() end
end
local N=200000
local next01=seededUniform(20261013)
local counts={shiny=0,big=0,mutation={},primary={},secondary={}}
local blendMin,blendMax,blendSum,equalBlend=1000,-1,0,0
for _=1,N do
 local t=O.rollWith(summaryOf(mixedSpec),"06_wavy_stripes",next01)
 assert(G.valid(t.genes),"rolled genes must satisfy EggGenetics.valid")
 if t.shiny then counts.shiny+=1 end
 if t.big then counts.big+=1 end
 counts.mutation[t.mutationId]=(counts.mutation[t.mutationId] or 0)+1
 assert(t.genes.conditionId==nil,"rolled dinosaur genes never carry a condition")
 counts.primary[t.genes.primaryColorId]=(counts.primary[t.genes.primaryColorId] or 0)+1
 counts.secondary[t.genes.secondaryColorId]=(counts.secondary[t.genes.secondaryColorId] or 0)+1
 if t.genes.primaryColorId==t.genes.secondaryColorId then
  assert(t.genes.blend==100) equalBlend+=1
 else
  blendMin=math.min(blendMin,t.genes.blend) blendMax=math.max(blendMax,t.genes.blend) blendSum+=t.genes.blend
 end
end
-- 5 standard errors of a binomial proportion: deterministic seed, generous bound.
local function parity(observed,p,label)
 local tolerance=5*math.sqrt(math.max(p*(1-p),1e-9)/N)+1e-9
 assert(math.abs(observed/N-p)<=tolerance,string.format("%s observed %.5f expected %.5f",label,observed/N,p))
end
parity(counts.shiny,mixed.shiny,"shiny") parity(counts.big,mixed.big,"big")
for id,p in O.mutationWheel(mixed) do parity(counts.mutation[id] or 0,p,"mutation "..id) end
for id in counts.mutation do assert(O.mutationWheel(mixed)[id],"unquoted mutation "..id) end
for id,p in mixed.primaryColor do parity(counts.primary[id] or 0,p,"primary "..id) end
for id in counts.primary do assert(mixed.primaryColor[id],"unquoted primary "..id) end
for id,p in mixed.secondaryColor do parity(counts.secondary[id] or 0,p,"secondary "..id) end
for id in counts.secondary do assert(mixed.secondaryColor[id],"unquoted secondary "..id) end
local pEqual=0 for id,p in mixed.primaryColor do pEqual+=p*(mixed.secondaryColor[id] or 0) end
parity(equalBlend,pEqual,"equal colors -> blend 100")
assert(blendMin==1 and blendMax==99,"blend range 1..99")
assert(math.abs(blendSum/(N-equalBlend)-50)<0.5,"blend uniform mean")
-- Zero-Shiny donors never yield Shiny; ten Shiny donors give about 50%.
local zero,ten=0,0
for _=1,20000 do
 if O.rollWith(summaryOf({}),"06_wavy_stripes",next01).shiny then zero+=1 end
 if O.rollWith(summaryOf({shiny=10}),"06_wavy_stripes",next01).shiny then ten+=1 end
end
assert(zero==0 and math.abs(ten/20000-0.5)<0.02)
-- Edge uniforms stay inside the wheels (Random:NextNumber edge values).
local edge=O.rollWith(summaryOf(mixedSpec),"06_wavy_stripes",function() return 1 end)
assert(G.valid(edge.genes) and edge.mutationId=="frost" and edge.shiny==false)
local low=O.rollWith(summaryOf(mixedSpec),"06_wavy_stripes",function() return 0 end)
assert(low.shiny and low.big and low.mutationId=="" and G.valid(low.genes))
print(string.format("Odds parity passed: %d samples match the quoted distribution within 5 SE for Shiny, BIG, mutations, both colors; blend uniform 1-99, equal colors -> 100; genes pass EggGenetics.valid",N))

-- Determinism: a seeded roller yields the same traits; the committed outcome is fixed.
local function seededRoller(seed)
 return O.roller(function() local f=seededUniform(seed) return {NextNumber=function() return f() end} end)
end
local p9=fixture()
local A9=idsIn(p9,"compy/variant/wavyA")
local q9=assert(F.quote(p9.dinosaurIdentity,OWNER,"gold",A9))
local r1=assert(F.prepareOutcome(q9,seededRoller(7),G.valid))
local r2=assert(F.prepareOutcome(q9,seededRoller(7),G.valid))
assert(same(r1,r2) and r1.oddsVersion==O.Version,"same seed, same outcome")
local d9=assert(O.distribution(q9.summary))
assert(d9.primaryColor.green==1 and d9.secondaryColor.blue==1)
assert(r1.traits.genes.conditionId==nil and r1.traits.genes.primaryColorId=="green" and r1.traits.genes.secondaryColorId=="blue" and r1.traits.genes.patternId=="06_wavy_stripes")
assert(r1.traits.shiny==false and r1.traits.big==false and r1.traits.mutationId=="","plain donors cannot yield Shiny/BIG/mutation")
local req9={token="odds-1",targetStage="gold",donorIds=A9,quoteDigest=q9.quoteDigest}
local f9,s9,res9=F.apply(p9,OWNER,req9,r1,1)
assert(s9=="fused" and same(res9.traits,r1.traits) and res9.oddsVersion==O.Version)
assert(f9.dinosaurIdentity.instances[res9.resultId].origin.oddsVersion==O.Version)
assert(f9.dinosaurIdentity.fusions["fusion:odds-1"].oddsVersion==O.Version)
-- A retried transform with a different seed cannot change the committed traits.
local other=assert(F.prepareOutcome(q9,seededRoller(99),G.valid))
local _,sx,resx=F.apply(f9,OWNER,req9,other,2)
assert(sx=="duplicate" and same(resx.traits,r1.traits))
-- Consent-bearing mixed donors: a production-roller fusion is schema-valid and versioned.
local pm=fixture()
local mixedDonors=concat(take(idsIn(pm,"compy/variant/wavyA"),12),idsIn(pm,"compy/variant/wavyB"),idsIn(pm,"compy/variant/wavyC"))
local qm=assert(F.quote(pm.dinosaurIdentity,OWNER,"gold",mixedDonors))
local dm=assert(O.distribution(qm.summary))
assert(near(dm.shiny,1/15) and near(dm.big,1/30) and near(dm.mutation.ember,1/30) and near(dm.noMutation,1-1/30))
local om=assert(F.prepareOutcome(qm,seededRoller(3),G.valid))
local fm,sm=F.apply(pm,OWNER,{token="odds-mixed",targetStage="gold",donorIds=mixedDonors,quoteDigest=qm.quoteDigest,consentDigest=qm.consentDigest},om,1)
assert(sm=="fused" and fm)
print("Odds determinism passed: seeded roller reproducible, ledger/result carry fusion-odds-provisional-v2, retries replay the committed traits; 2 Shiny/1 BIG/1 Ember of 15 donors quote 6.67%/3.33%/3.33%")
local function ladderChain()
-- ===== Ladder 15/4/2: Base -> Gold -> Emerald -> Diamond chain (owner decision 2026-10-14) =====
assert(F.Recipes.gold.donorCount==15 and F.Recipes.gold.sourceStage=="base" and F.Recipes.gold.version=="gold-same-species-pattern-15-v1")
assert(F.Recipes.emerald.donorCount==4 and F.Recipes.emerald.sourceStage=="gold" and F.Recipes.emerald.version=="emerald-same-species-pattern-4-v1")
assert(F.Recipes.diamond.donorCount==2 and F.Recipes.diamond.sourceStage=="emerald" and F.Recipes.diamond.version=="diamond-same-species-pattern-2-v1")
assert(F.MaxDonorCount==15 and I.MaxFusionParents==15 and F.GroupedProjection.emerald==true)
local chain=fixture()
local chainEgg=0
local function makeGold(species,pattern,token)
 local key="ladder-"..species.."-"..pattern
 for _=1,15 do
  chainEgg+=1
  local g=genes(pattern)
  local e={eggId="ladder-"..chainEgg,kind="alpha_chest",genes=I.copy(g),reward={speciesId=species,count=1}}
  local entry=chain.collection[species]
  local v=entry.variants[key] or {count=0,genes=I.copy(g),big=false,shiny=false,mutationId=""}
  v.count+=1 entry.variants[key]=v
  I.hatch(chain.dinosaurIdentity,e,species,1,species.."/variant/"..key)
 end
 chain.dinosaurIdentity=assert(I.reconcile(chain.collection,chain.dinosaurIdentity,OWNER))
 local _,o,r=prepare(chain,token,idsIn(chain,species.."/variant/"..key),"gold")
 local nextP,st,res=F.apply(chain,OWNER,r,o,1)
 assert(st=="fused",tostring(st))
 chain=nextP
 return res.resultId
end
local function fuse(stage,token,donors)
 local q,o,r=prepare(chain,token,donors,stage,true) -- test roller makes Shiny results, so consent applies
 local nextP,st,res=F.apply(chain,OWNER,r,o,1)
 assert(st=="fused",stage..": "..tostring(st))
 chain=nextP
 return res.resultId,q
end
local legacyGold=chain.collection.compy.gold -- 1 legacy Build 020 Gold (no genes, never a donor)
local golds={}
for i=1,4 do table.insert(golds,makeGold("compy","06_wavy_stripes","g"..i)) end
local goldBytes=F.encodedSize(chain.dinosaurIdentity.instances[golds[1]])
local goldLedgerBytes=F.encodedSize(chain.dinosaurIdentity.fusions["fusion:g1"])
local eggBytes=F.encodedSize(chain.dinosaurIdentity.eggs["ladder-1"])
assert(chain.collection.compy.gold==legacyGold+4)
-- Higher-tier validation: wrong count, wrong stage, mixed species/pattern, legacy Gold.
local spotsGold=makeGold("compy","02_spots","gs")
local raptorGold=makeGold("raptor","06_wavy_stripes","gr")
local function badChain(stage,donors,expected)
 local q,reason=F.quote(chain.dinosaurIdentity,OWNER,stage,donors)
 assert(q==nil and reason==expected,stage.." expected "..expected.." got "..tostring(reason))
end
badChain("emerald",take(golds,3),"wrong_donor_count")
badChain("emerald",concat(golds,{spotsGold}),"wrong_donor_count")
badChain("emerald",concat(take(golds,3),{spotsGold}),"pattern_mismatch")
badChain("emerald",concat(take(golds,3),{raptorGold}),"species_mismatch")
badChain("emerald",concat(take(golds,3),{idsIn(chain,"compy/variant/spots")[1]}),"wrong_stage")
local legacyGoldId=nil
for id,d in chain.dinosaurIdentity.instances do if d.bucketKey=="compy/gold" and d.origin.kind=="legacy_unknown" then legacyGoldId=id end end
badChain("emerald",concat(take(golds,3),{legacyGoldId}),"missing_pattern")
badChain("diamond",take(golds,2),"wrong_stage")
-- Emerald 1: consumes 4 fused Golds, ledger records parentOperationIds.
local emerald1,qe1=fuse("emerald","e1",golds)
local em=chain.dinosaurIdentity.instances[emerald1]
assert(em.stage=="emerald" and em.bucketKey=="compy/emerald" and em.genes.patternId=="06_wavy_stripes")
assert(#em.origin.parents==4 and em.origin.parentStage=="gold" and em.origin.recipeVersion=="emerald-same-species-pattern-4-v1")
for _,par in em.origin.parents do assert(par.origin.kind=="fusion" and par.origin.operationId and par.origin.parents==nil,"bounded, non-recursive") end
local le=chain.dinosaurIdentity.fusions["fusion:e1"]
assert(#le.parentOperationIds==4 and #le.parentEggIds==0)
for i=1,4 do assert(table.find(le.parentOperationIds,"fusion:g"..i)) end
assert(chain.collection.compy.gold==legacyGold+1 and chain.collection.compy.emerald==1)
local emeraldBytes=F.encodedSize(em)
local emeraldLedgerBytes=F.encodedSize(le)
-- Ancestry by operation id: each Gold ledger still resolves its 15 parent eggs.
for i=1,4 do local lin=assert(F.lineage(chain.dinosaurIdentity,"fusion:g"..i)) assert(count(lin.parentEggs)==15) end
-- Reload reconciles unchanged with the additive Emerald counter.
assert(same(assert(I.reconcile(chain.collection,I.copy(chain.dinosaurIdentity),OWNER)),chain.dinosaurIdentity))
-- One more Emerald.
local emeralds={emerald1}
for e=2,2 do
 local gs={}
 for i=1,4 do table.insert(gs,makeGold("compy","06_wavy_stripes","g"..e.."-"..i)) end
 table.insert(emeralds,(fuse("emerald","e"..e,gs)))
end
assert(chain.collection.compy.emerald==2)
badChain("diamond",take(emeralds,1),"wrong_donor_count")
-- Stale quote at a higher tier: a donor Emerald changes after quoting.
local qd,od,rd=prepare(chain,"d1",emeralds,"diamond",true)
local staleChain=I.copy(chain) staleChain.dinosaurIdentity.instances[emeralds[2]].cosmetics.ownedAuraIds.x=true
rejects(staleChain,rd,od,"stale_quote","stale emerald donor")
-- Consent: purchased FX on an Emerald donor requires the itemized consent digest.
local consentChain=I.copy(chain) consentChain.dinosaurIdentity.instances[emeralds[1]].cosmetics.ownedTrailIds.fern=true
local qc=assert(F.quote(consentChain.dinosaurIdentity,OWNER,"diamond",emeralds))
local fernLoss=nil for _,l in qc.lossManifest do if l.instanceId==emeralds[1] then fernLoss=l end end
assert(qc.consentRequired and qc.consentDigest~=qd.consentDigest and fernLoss and fernLoss.trailIds[1]=="fern")
local oc=assert(F.prepareOutcome(qc,roller))
rejects(consentChain,{token="dc",targetStage="diamond",donorIds=emeralds,quoteDigest=qc.quoteDigest},oc,"consent_required")
-- Rollback: projection mismatch at Emerald stage leaves the input untouched.
local mis=I.copy(chain) mis.collection.compy.emerald=1 rejects(mis,rd,od,"grouped_mismatch")
-- Diamond: consumes 2 Emeralds.
local diamondsBefore=chain.collection.compy.diamond
local nd,sd,resd=F.apply(chain,OWNER,rd,od,9)
assert(sd=="fused") chain=nd
local dia=chain.dinosaurIdentity.instances[resd.resultId]
assert(dia.stage=="diamond" and dia.bucketKey=="compy/diamond" and #dia.origin.parents==2 and dia.origin.parentStage=="emerald")
assert(chain.collection.compy.emerald==0 and chain.collection.compy.diamond==diamondsBefore+1)
local ld=chain.dinosaurIdentity.fusions["fusion:d1"]
assert(#ld.parentOperationIds==2 and table.find(ld.parentOperationIds,"fusion:e1"))
-- Idempotent replay of the Diamond after reload.
local reloadedChain={collection=I.copy(chain.collection),dinosaurIdentity=assert(I.reconcile(chain.collection,I.copy(chain.dinosaurIdentity),OWNER))}
assert(same(reloadedChain.dinosaurIdentity,chain.dinosaurIdentity))
assert(select(2,F.apply(reloadedChain,OWNER,rd,nil))=="duplicate")
-- Full ancestry walk by operation id: Diamond -> 2 Emeralds -> 8 Golds -> 120 eggs.
local eggsSeen,ops={},{"fusion:d1"}
local goldOps=0
while #ops>0 do
 local op=table.remove(ops)
 local l=chain.dinosaurIdentity.fusions[op]
 if l.targetStage=="gold" then goldOps+=1 end
 for _,e in l.parentEggIds do eggsSeen[e]=true end
 for _,parentOp in l.parentOperationIds do table.insert(ops,parentOp) end
end
assert(goldOps==8 and count(eggsSeen)==120)
-- Legacy Build 020 Gold -> Diamond grouped decrement is unchanged: spends the legacy Gold.
local legacy=I.copy(chain) legacy.collection.compy.gold-=1 legacy.collection.compy.diamond+=1
local spentLegacy=assert(I.reconcile(legacy.collection,legacy.dinosaurIdentity,OWNER))
assert(spentLegacy.instances[spotsGold] and spentLegacy.instances[legacyGoldId]==nil)
-- A grouped Diamond decrement that would erase the crafted Diamond fails closed.
local erase=I.copy(chain) erase.collection.compy.diamond=0
assert(select(2,I.reconcile(erase.collection,erase.dinosaurIdentity,OWNER))=="protected_identity")
local diaBytes=F.encodedSize(dia)
local sidecar=F.encodedSize(chain.dinosaurIdentity)
assert(sidecar<F.MaxSidecarBytes)
print("Ladder chain passed: 8x Gold(15 Base) -> 2x Emerald(4 Gold) -> Diamond(2 Emerald); wrong counts, wrong stage, mixed species/pattern, legacy Gold, stale quote, consent, rollback, reload, replay, ancestry by operation id (8 Gold ledgers, 120 eggs), legacy Gold->Diamond unchanged")
print(string.format("Ladder bytes: Gold record %d, Gold ledger %d, archived egg %d (x15 per Gold), Emerald record %d, Emerald ledger %d, Diamond record %d, chain sidecar %d of %d",
 goldBytes,goldLedgerBytes,eggBytes,emeraldBytes,emeraldLedgerBytes,diaBytes,sidecar,F.MaxSidecarBytes))

-- Storage limit at 15-donor ledger size: fails closed with nothing consumed.
local sp=fixture()
local _,so,sr=prepare(sp,"cap15",idsIn(sp,"compy/variant/wavyA"))
local okSize=F.encodedSize(assert(F.apply(sp,OWNER,sr,so,1)).dinosaurIdentity)
local savedLimit=F.MaxSidecarBytes
F.MaxSidecarBytes=okSize-1 rejects(sp,sr,so,"storage_limit","15-donor ledger over ceiling")
F.MaxSidecarBytes=okSize assert(select(2,F.apply(sp,OWNER,sr,so,1))=="fused")
F.MaxSidecarBytes=savedLimit
print("Storage limit passed at 15-donor ledger size: ceiling-1 byte rejects, exact ceiling commits")

-- Odds normalization uses the ACTUAL donor count N (15 / 4 / 2), never /10.
local function summaryN(n,shiny,big,ember)
 local s={speciesId="compy",patternId="06_wavy_stripes",targetStage="gold",donorCount=n,shinyCount=shiny,bigCount=big,
  mutationCounts=if ember>0 then {ember=ember} else {},colors={}}
 for _=1,n do table.insert(s.colors,{primaryColorId="green",secondaryColorId="blue",blend=20}) end
 return s
end
for _,n in {15,4,2} do
 for _,k in {0,1,n} do
  local d=assert(O.distribution(summaryN(n,k,k,k)))
  assert(near(d.shiny,0.5*k/n) and near(d.big,0.5*k/n) and near(d.noMutation,1-0.5*k/n))
  assert(near(sum(d.primaryColor),1))
 end
end
assert(O.distribution(summaryN(15,16,0,0))==nil,"shiny count above N rejected")
assert(qe1.summary.donorCount==4 and qd.summary.donorCount==2)
print("Odds N passed: Shiny/BIG/mutation = 0.5 x donors/N for N=15/4/2 (1 Shiny of 15 = 3.33%, of 4 = 12.5%, of 2 = 25%)")
end
ladderChain()
print("Fusion verified: validation, consent, atomic copy-on-write commit, idempotency, rollback, lineage, storage bounds and BD-064 provisional odds (normalization, sampling parity, determinism)")
''')
if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--runner',required=True); args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'fusion.luau'; path.write_text(script())
        subprocess.run([args.runner,str(path)],check=True)
