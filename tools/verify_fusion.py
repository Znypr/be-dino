"""Execute the BD-057 Phase 1 identity fusion transaction with the pinned Luau runtime.
Pure module only: no DataStore, Studio, RNG odds or UI. Controlled test rollers stand in
for the unapproved BD-064 trait formula.
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
        + 'local F=' + module('src/server/IdentityFusion.luau') + '\n' + r'''
local function count(t) local n=0 for _ in t do n+=1 end return n end
local same=function(a,b) return F.canonical(a)==F.canonical(b) end
local OWNER="u:1"
local function genes(pattern,primary) return {patternId=pattern,primaryColorId=primary or "green",secondaryColorId="blue",blend=20,conditionId="normal",hatchSuccess=true} end

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
 for _,qty in {3,3,3,1} do hatch("compy","wavyA",genes("06_wavy_stripes"),qty) end -- egg-1..4: 10 plain
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
 assert(summary.donorCount==10 and summary.speciesId=="compy")
 for k,v in summary do assert(type(k)=="string" and not string.find(k,"prob") and not string.find(k,"odds")) end
 return {big=false,shiny=true,mutationId="",genes={patternId=patternId,primaryColorId="gold",secondaryColorId="blue",conditionId="rainbow",blend=55}}
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
assert(#plain==10)
local snapshot=F.canonical(profile)
local nextBefore=profile.dinosaurIdentity.nextId
local livingBefore=count(profile.dinosaurIdentity.instances)
local quote,outcome,request=prepare(profile,"tok-1",plain)
assert(quote.consentRequired==false and #quote.lossManifest==0)
assert(quote.speciesId=="compy" and quote.patternId=="06_wavy_stripes" and quote.recipeVersion=="gold-same-species-pattern-10-v1")
assert(rolls==1 and outcome.oddsVersion=="test-fixed-v1" and outcome.targetStage=="gold")
local fused,status,result=F.apply(profile,OWNER,request,outcome,1234)
assert(fused and status=="fused",tostring(status))
assert(F.canonical(profile)==snapshot,"input profile mutated")
local state=fused.dinosaurIdentity
local resultId=OWNER.."/d:"..nextBefore
assert(result.resultId==resultId and state.nextId==nextBefore+1)
assert(count(state.instances)==livingBefore-10+1)
for _,id in plain do assert(state.instances[id]==nil) end
local gold=state.instances[resultId]
assert(gold.stage=="gold" and gold.speciesId=="compy" and gold.bucketKey=="compy/gold")
assert(gold.genes.patternId=="06_wavy_stripes" and gold.genes.primaryColorId=="gold" and gold.shiny==true)
assert(next(gold.cosmetics.ownedAuraIds)==nil and next(gold.cosmetics.ownedTrailIds)==nil and gold.cosmetics.equippedAuraId=="")
assert(gold.origin.kind=="fusion" and gold.origin.operationId=="fusion:tok-1" and #gold.origin.parents==10)
assert(gold.origin.recipeVersion==quote.recipeVersion and gold.origin.oddsVersion=="test-fixed-v1")
for _,p in gold.origin.parents do assert(p.cosmetics==nil and p.origin.kind=="hatch") end
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
assert(#entry.parentEggIds==4,"parent eggs should be distinct")
for i=1,4 do assert(state.eggs["egg-"..i] and table.find(entry.parentEggIds,"egg-"..i)) end
local lineage=assert(F.lineage(state,"fusion:tok-1"))
assert(lineage.resultId==resultId and #lineage.parentIds==10 and count(lineage.parentEggs)==4)
assert(lineage.parentEggs["egg-1"].genes.patternId=="06_wavy_stripes")
-- Reload: saved state reconciles unchanged; fused record and nextId stay.
local reloaded=assert(I.reconcile(fused.collection,I.copy(state),OWNER))
assert(same(reloaded,state))
print("Fusion happy path passed: 10 consumed, one new server ID, nextId+1, guaranteed Gold, empty cosmetics, untouched input, grouped projection, ledger, parent eggs and reload")

-- ===== Invalid donors (all fail before any write) =====
local p=fixture()
local A=idsIn(p,"compy/variant/wavyA")
local st=p.dinosaurIdentity
local function bad(donors,expected,stage,owner)
 local q,reason=F.quote(st,owner or OWNER,stage or "gold",donors)
 assert(q==nil and reason==expected,expected..": got "..tostring(reason))
end
bad(take(A,9),"wrong_donor_count")
bad(concat(A,idsIn(p,"compy/variant/wavyB")),"wrong_donor_count")
local extra=I.copy(A) extra.note="x" bad(extra,"wrong_donor_count")
bad("u:1/d:1","wrong_donor_count")
local dup=take(A,9) table.insert(dup,A[1]) bad(dup,"duplicate_donor")
local missing=take(A,9) table.insert(missing,OWNER.."/d:9999") bad(missing,"donor_missing")
local foreign=take(A,9) table.insert(foreign,"u:2/d:1") bad(foreign,"wrong_owner")
local numeric=take(A,9) table.insert(numeric,42) bad(numeric,"invalid_donor_id")
local plainBase=take(A,9) table.insert(plainBase,idsIn(p,"compy/base")[1]) bad(plainBase,"missing_pattern")
local wrongStage=take(A,9) table.insert(wrongStage,idsIn(p,"compy/gold")[1]) bad(wrongStage,"wrong_stage")
local species=take(A,9) table.insert(species,idsIn(p,"raptor/variant/wavyR")[1]) bad(species,"species_mismatch")
local pattern=take(A,9) table.insert(pattern,idsIn(p,"compy/variant/spots")[1]) bad(pattern,"pattern_mismatch")
st.instances[A[3]].locked=true bad(A,"donor_locked") st.instances[A[3]].locked=nil
st.instances[A[4]].favorited=true bad(A,"donor_locked") st.instances[A[4]].favorited=nil
bad(A,"wrong_owner","gold","u:2")
bad(A,"recipe_not_approved","emerald")
bad(A,"recipe_not_approved","diamond")
bad(A,"unknown_stage","base")
bad(A,"unknown_stage","platinum")
bad(A,"unknown_stage",5)
assert(F.quote(nil,OWNER,"gold",A)==nil)
-- Same rejections inside apply leave the profile untouched.
local _,o1,r1=prepare(p,"inv",A)
local r9=I.copy(r1) r9.donorIds=take(A,9) rejects(p,r9,o1,"wrong_donor_count")
local rs=I.copy(r1) rs.donorIds=species rejects(p,rs,o1,"species_mismatch")
local rt=I.copy(r1) rt.token="" rejects(p,rt,o1,"invalid_token")
rt.token=string.rep("x",F.MaxTokenLength+1) rejects(p,rt,o1,"invalid_token")
rt.token=7 rejects(p,rt,o1,"invalid_token")
local ws=F.apply(p,"u:2",r1,o1) assert(ws==nil)
print("Invalid donors passed: 9/11/non-list, duplicate, missing, foreign, non-string, no pattern, wrong stage/species/pattern, locked/favorited, wrong owner, unapproved Emerald/Diamond, unknown stage, bad token")

-- ===== Consent: valuable traits and purchased cosmetics =====
p=fixture()
A=idsIn(p,"compy/variant/wavyA")
local B=idsIn(p,"compy/variant/wavyB")
local mixed=concat(take(A,8),B)
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
local q3=assert(F.quote(p.dinosaurIdentity,OWNER,"gold",concat(take(A,9),idsIn(p,"compy/variant/wavyC"))))
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
local conflict=I.copy(r5) conflict.donorIds=concat(take(A,8),idsIn(c1,"compy/variant/wavyB"))
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
local overlap=concat(take(A,8),B)
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
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function(_,pt) return {big=false,shiny=false,mutationId="",stage="diamond",genes={patternId=pt,primaryColorId="a",secondaryColorId="b",conditionId="normal",blend=1}} end}))=="invalid_outcome")
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function() return {big=false,shiny=false,mutationId="",genes={patternId="02_spots",primaryColorId="a",secondaryColorId="b",conditionId="normal",blend=1}} end}))=="invalid_outcome")
assert(select(2,F.prepareOutcome(q7,{version="v",roll=function(_,pt) return {big=false,shiny=false,mutationId="",genes={patternId=pt,primaryColorId="a",secondaryColorId="b",conditionId="normal",blend=101}} end}))=="invalid_outcome")
assert(select(2,F.prepareOutcome(q7,roller,function() return false end))=="invalid_outcome")
-- Roller summaries are copies; mutation cannot affect the quote.
assert(F.prepareOutcome(q7,{version="v",roll=function(s,pt) s.speciesId="trex" return roller.roll({donorCount=10,speciesId="compy"},pt) end}))
assert(q7.summary.speciesId=="compy")
rejects(p,r7,nil,"invalid_outcome","no outcome")
local tampered=I.copy(o7) tampered.traits.genes.patternId="02_spots" rejects(p,r7,tampered,"invalid_outcome","pattern not locked")
tampered=I.copy(o7) tampered.targetStage="diamond" rejects(p,r7,tampered,"invalid_outcome","stage from outcome")
tampered=I.copy(o7) tampered.requestDigest="x" rejects(p,r7,tampered,"invalid_outcome","outcome for another request")
-- Grouped/identity mismatch: projection cannot cover the consumption.
local mismatch=I.copy(p) mismatch.collection.compy.variants.wavyA.count=9 rejects(mismatch,r7,o7,"grouped_mismatch")
mismatch=I.copy(p) mismatch.collection.compy=nil rejects(mismatch,r7,o7,"grouped_mismatch","missing species entry")
-- Corrupt ledger / identity.
local corrupt=I.copy(p) corrupt.dinosaurIdentity.fusions="bad" rejects(corrupt,r7,o7,"invalid_fusion_ledger")
corrupt=I.copy(p) corrupt.dinosaurIdentity=nil rejects(corrupt,r7,o7,"identity_unavailable")
-- Fail-closed: an approved-looking Emerald recipe still has no grouped projection.
local emerald=F.Recipes.emerald
F.Recipes.emerald={targetStage="emerald",sourceStage="base",donorCount=10,version="test-only"}
local qe=assert(F.quote(p.dinosaurIdentity,OWNER,"emerald",A))
local oe=assert(F.prepareOutcome(qe,roller))
rejects(p,{token="em",targetStage="emerald",donorIds=A,quoteDigest=qe.quoteDigest},oe,"projection_unsupported")
F.Recipes.emerald=emerald
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
for i=1,4 do assert(s8.eggs["egg-"..i]) end
local lin=assert(F.lineage(s8,"fusion:lineage"))
assert(count(lin.parentEggs)==4 and lin.parentEggs["egg-2"].eggId=="egg-2")
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
 for k=1,10 do
  local ek=I.copy(e) ek.eggId=e.eggId.."-"..k
  v.count+=1 p.collection.compy.variants.bulk=v
  I.hatch(p.dinosaurIdentity,ek,"compy",1,key)
 end
 p.dinosaurIdentity=assert(I.reconcile(p.collection,p.dinosaurIdentity,OWNER))
 local donors=idsIn(p,key)
 assert(#donors==10)
 local _,ob2,rb2=prepare(p,"bulk-"..round,donors)
 local nextP,stt=F.apply(p,OWNER,rb2,ob2,round)
 assert(stt=="fused",tostring(stt))
 p=nextP
 sizes[round]=F.encodedSize(p.dinosaurIdentity)
end
assert(count(p.dinosaurIdentity.fusions)==20 and p.collection.compy.gold==21)
assert(count(p.dinosaurIdentity.eggs)>=200,"all 200 parent eggs archived")
local perFusion=(sizes[20]-sizes[10])/10
assert(perFusion>0 and perFusion<20000,"per-fusion growth "..perFusion)
print(string.format("Storage passed: 20 sequential fusions, 200 archived parent eggs, ~%d bytes per fusion (estimate), preflight ceiling %d bytes", perFusion, F.MaxSidecarBytes))
-- The 3,000-identity ceiling still applies to the reconciled post-fusion state.
local big=fixture()
big.collection.compy.base=I.MaxInstances
local _,obg,rbg=prepare(fixture(),"cap",idsIn(fixture(),"compy/variant/wavyA"))
rejects(big,rbg,obg,"identity_capacity")
print("Fusion verified: validation, consent, atomic copy-on-write commit, idempotency, rollback, lineage and storage bounds (controlled test roller; no live odds)")
''')
if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--runner',required=True); args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'fusion.luau'; path.write_text(script())
        subprocess.run([args.runner,str(path)],check=True)
