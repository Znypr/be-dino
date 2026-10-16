"""BD-059 phase 1 (docs/121): per-dino cosmetic ownership, legacy grandfathering, fusion loss notice. Pinned Luau runtime."""
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
        + 'local C=' + module('src/server/CosmeticOwnership.luau') + '\n' + r'''
local OWNER="u:1"
local function genes() return {patternId="06_wavy_stripes",primaryColorId="green",secondaryColorId="blue",blend=20,hatchSuccess=true} end
local profile={collection={compy={base=0,gold=0,diamond=0,events={},variants={}}},
  progression={crystals=0,auras={meadow=true},trails={white=true},equippedAura="meadow",equippedTrail="white",potions={},buffs={}}}
profile.dinosaurIdentity=assert(I.reconcile(profile.collection,nil,OWNER))
local ids={}
for n=1,F.Recipes.gold.donorCount do
 local egg={eggId="egg-"..n,kind="alpha_chest",eventId="clear",mutationId="",big=false,shiny=false,genes=genes(),readyAt=0,reward={speciesId="compy",count=1}}
 local v=profile.collection.compy.variants.wavy or {count=0,genes=genes(),big=false,shiny=false,mutationId=""}
 v.count+=1 profile.collection.compy.variants.wavy=v
 for _,id in I.hatch(profile.dinosaurIdentity,egg,"compy",1,"compy/variant/wavy") do table.insert(ids,id) end
 profile.dinosaurIdentity=assert(I.reconcile(profile.collection,profile.dinosaurIdentity,OWNER))
end
table.sort(ids)
local before=F.canonical(profile)

-- Flag off: legacy account-wide behaviour, per-dino grants refused, nothing mutated.
local off=C.usable(profile.progression,profile.dinosaurIdentity.instances[ids[1]],false)
assert(#off.auraIds==1 and off.auraIds[1]=="meadow" and #off.ownAuraIds==0)
assert(C.canEquip(profile.progression,nil,"aura","meadow",false) and not C.canEquip(profile.progression,nil,"aura","tidal",false))
local g,reason=C.grant(profile.dinosaurIdentity,ids[1],"aura","tidal",false)
assert(g==nil and reason=="per_dino_disabled")

-- Flag on: legacy grandfathered (usable by every dino), grants are per dino, idempotent, copy-on-write.
local s1,r1=C.grant(profile.dinosaurIdentity,ids[1],"aura","tidal",true)
assert(s1 and r1=="granted" and F.canonical(profile)==before,"input mutated")
local s1b,r1b=C.grant(s1,ids[1],"aura","tidal",true)
assert(r1b=="already_owned" and s1b==s1)
local a=C.usable(profile.progression,s1.instances[ids[1]],true)
local b=C.usable(profile.progression,s1.instances[ids[2]],true)
assert(#a.auraIds==2 and #a.ownAuraIds==1 and #b.auraIds==1 and b.auraIds[1]=="meadow" and #b.trailIds==1)
assert(C.canEquip(profile.progression,s1.instances[ids[1]],"aura","tidal",true))
assert(not C.canEquip(profile.progression,s1.instances[ids[2]],"aura","tidal",true))
assert(C.canEquip(profile.progression,s1.instances[ids[2]],"aura","meadow",true))
assert(select(2,C.grant(s1,"u:1/d:999","aura","x",true))=="unknown_instance")
assert(select(2,C.grant(s1,ids[1],"wing","x",true))=="invalid_request")
-- Rollback: flag off again sees the same legacy sets and the per-dino purchase stays stored, untouched.
assert(#C.usable(profile.progression,s1.instances[ids[1]],false).auraIds==1)
assert(s1.instances[ids[1]].cosmetics.ownedAuraIds.tidal==true)
assert(I.reconcile(profile.collection,s1,OWNER)~=nil,"sidecar with a per-dino purchase reconciles")

-- Fusion: donor with a per-dino purchase needs consent, notice itemizes it and states legacy is kept; result has none.
local withBuy=profile
withBuy.dinosaurIdentity=s1
local quote=assert(F.quote(withBuy.dinosaurIdentity,OWNER,"gold",ids))
assert(quote.consentRequired)
local n=C.fusionNotice(quote,withBuy.progression,true)
assert(n.irreversible and #n.lostAuraIds==1 and n.lostAuraIds[1]=="tidal" and n.legacyKept and n.legacyAuraIds[1]=="meadow")
local n2=C.fusionNotice(quote,withBuy.progression,false)
assert(n2.legacyKept==false)
local roller={version="t",roll=function(_,p) return {big=false,shiny=false,mutationId="",genes={patternId=p,primaryColorId="green",secondaryColorId="blue",blend=1}} end}
local outcome=assert(F.prepareOutcome(quote,roller))
local request={token="tok",targetStage="gold",donorIds=ids,quoteDigest=quote.quoteDigest}
local snap=F.canonical(withBuy)
local bad,why=F.apply(withBuy,OWNER,request,outcome,10)
assert(bad==nil and why=="consent_required" and F.canonical(withBuy)==snap)
request.consentDigest=quote.consentDigest
local fused,status=F.apply(withBuy,OWNER,request,outcome,10)
assert(fused and status=="fused")
local fusedState=fused.dinosaurIdentity
for _,d in fusedState.instances do
 assert(next(d.cosmetics.ownedAuraIds)==nil and next(d.cosmetics.ownedTrailIds)==nil,"fusion output carries no cosmetics")
end
assert(fused.progression.auras.meadow==true and fused.progression.trails.white==true,"legacy account purchases untouched")

-- Phase 2: apply() on a live profile (stub rules: the real ProgressionRules run in verify_progression/verify_rollback).
local cfg={Auras={{id="meadow",price=60},{id="tidal",price=470},{id="royal",price=3700}},Trails={{id="white",price=0,level=1},{id="fern",price=50,level=3}}}
local rules={item=function(cat,id) for _,i in cat do if i.id==id then return i end end return nil end,
 level=function(p) return p.level or 1 end,upgrade=function(pr) return pr.progression end}
local function live()
 local pr={equippedSpeciesId="compy",equippedVariantKey="wavy",progression={crystals=500,level=1,auras={meadow=true},trails={white=true},equippedAura="",equippedTrail="white",potions={},buffs={}}}
 return pr
end
local lp=live()
lp.dinosaurIdentity=s1
local ctx={rules=rules,config=cfg,identityOk=true}
-- equipped instance = lowest sequence of the equipped stack
local eq=C.equippedInstanceId(lp.dinosaurIdentity,"compy","wavy")
assert(eq==ids[1] and C.equippedInstanceId(lp.dinosaurIdentity,"compy","nope")==nil and C.equippedInstanceId(lp.dinosaurIdentity,"rex",nil)==nil)
local ok,status,bound=C.apply(lp,"buyAura","tidal",ctx)
assert(not ok and status=="already_owned","tidal already granted to dino 1 in the grant test")
ok,status,bound=C.apply(lp,"buyTrail","white",ctx) assert(not ok and status=="already_owned","legacy item is not re-bought")
ok,status=C.apply(lp,"buyTrail","fern",ctx) assert(not ok and status=="level_locked")
lp.progression.level=3
local lp2=live() lp2.dinosaurIdentity=profile.dinosaurIdentity lp2.progression.level=3
ok,status,bound=C.apply(lp2,"buyTrail","fern",ctx)
assert(ok and status=="purchased" and bound==ids[1] and lp2.progression.crystals==450)
assert(lp2.progression.trails.fern==nil,"account-wide trails untouched")
assert(lp2.dinosaurIdentity.instances[ids[1]].cosmetics.ownedTrailIds.fern==true and lp2.dinosaurIdentity.instances[ids[2]].cosmetics.ownedTrailIds.fern==nil)
assert(profile.dinosaurIdentity.instances[ids[1]].cosmetics.ownedTrailIds.fern==nil,"original sidecar copy untouched")
lp2.progression.crystals=10
ok,status=C.apply(lp2,"buyAura","royal",ctx) assert(not ok and status=="insufficient_crystals" and lp2.progression.crystals==10)
ok,status=C.apply(lp2,"equipTrail","fern",ctx) assert(ok and status=="equipped")
assert(lp2.dinosaurIdentity.instances[ids[1]].cosmetics.equippedTrailId=="fern" and lp2.progression.equippedTrail=="white")
local v=C.view(lp2.progression,lp2.dinosaurIdentity,"compy","wavy")
assert(v.equippedTrail=="fern" and v.trails.fern==true and v.trails.white==true and lp2.progression.trails.fern==nil)
ok,status=C.apply(lp2,"equipAura","royal",ctx) assert(not ok and status=="not_owned")
ok,status=C.apply(lp2,"equipTrail","white",ctx) assert(ok and lp2.dinosaurIdentity.instances[ids[1]].cosmetics.equippedTrailId=="" and C.view(lp2.progression,lp2.dinosaurIdentity,"compy","wavy").equippedTrail=="white")
ok,status=C.apply(lp2,"equipTrail","",ctx) assert(ok and lp2.progression.equippedTrail=="")
-- Another dino of the same stack is unaffected; no instance / identity off = refused, nothing changed.
lp2.equippedVariantKey=nil lp2.equippedSpeciesId="rex"
ok,status=C.apply(lp2,"buyAura","meadow",ctx) assert(not ok and status=="no_dino_instance")
ctx.identityOk=false lp2.equippedSpeciesId="compy" lp2.equippedVariantKey="wavy"
ok,status=C.apply(lp2,"buyAura","tidal",ctx) assert(not ok and status=="no_dino_instance")
assert(C.view(lp2.progression,lp2.dinosaurIdentity,"rex",nil)==lp2.progression)
local qn=C.fusionNotice(assert(F.quote(lp2.dinosaurIdentity,OWNER,"gold",ids)),lp2.progression,true)
assert(qn.irreversible and qn.lostTrailIds[1]=="fern" and qn.lostAuraIds[1]=="tidal" and qn.legacyKept)
print("Cosmetic ownership verified: flag-off parity, phase 2 apply/view (buy bound to equipped dino, equip own+legacy only, refusals), per-dino grants (idempotent, copy-on-write), legacy grandfathered, rollback view, fusion notice and consent, legacy kept")
''')
if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--runner',required=True); args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'cosmetics.luau'; path.write_text(script())
        subprocess.run([args.runner,str(path)],check=True)
