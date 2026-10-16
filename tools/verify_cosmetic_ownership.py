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
print("Cosmetic ownership verified: flag-off parity, per-dino grants (idempotent, copy-on-write), legacy grandfathered, rollback view, fusion notice and consent, legacy kept")
''')
if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--runner',required=True); args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'cosmetics.luau'; path.write_text(script())
        subprocess.run([args.runner,str(path)],check=True)
