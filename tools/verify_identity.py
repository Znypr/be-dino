"""Execute the identity data contract with the pinned Luau runtime."""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
def script():
    return 'local I=(function()\n' + (ROOT/'src/server/DinosaurIdentity.luau').read_text() + '\nend)()\n' + r'''
local function count(t) local n=0 for _ in t do n+=1 end return n end
local genes={patternId="06_wavy_stripes",conditionId="rainbow",primaryColorId="green",secondaryColorId="blue",blend=20,hatchSuccess=true}
local variant={count=3,genes=genes,big=true,shiny=true,mutationId="ember"}
local collection={compy={base=2,gold=1,diamond=1,events={frost=2},variants={striped=variant}}}
local legacy=assert(I.reconcile(collection,nil,"u:123"))
assert(count(legacy.instances)==9 and collection.compy.base==2)
assert(count(legacy.eggs)==0)
local again=assert(I.reconcile(collection,legacy,"u:123"))
assert(again.nextId==legacy.nextId)
for id, d in legacy.instances do
 assert(again.instances[id].instanceId==id and d.origin.kind=="legacy_unknown")
 if d.genes then assert(d.genes.blend==20 and d.big and d.shiny and d.mutationId=="ember") end
end
assert(I.reconcile(collection,legacy,"u:456")==nil)
local corrupt=I.copy(legacy)
corrupt.instances['u:123/d:1'].speciesId="trex"
assert(I.reconcile(collection,corrupt,"u:123")==nil)
local maxed=assert(I.reconcile({compy={base=I.MaxInstances,gold=0,diamond=0}},nil,"u:max"))
assert(count(maxed.instances)==I.MaxInstances)
local tooMany={compy={base=I.MaxInstances+1,gold=0,diamond=0}}
local rejected, capacityReason=I.reconcile(tooMany,nil,"u:max")
assert(rejected==nil and capacityReason=="identity_capacity" and tooMany.compy.base==I.MaxInstances+1)
assert(I.reconcile({compy={base=0/0,gold=0,diamond=0}},nil)==nil)
local plain={compy={base=2,gold=0,diamond=0}}
local protected=assert(I.reconcile(plain,nil,"u:123"))
protected.instances['u:123/d:2'].cosmetics.ownedAuraIds.meadow=true
protected.instances['u:123/d:2'].cosmetics.ownedAuraIds.tidal=true
plain.compy.base=1
local protectedNext=protected.nextId
local protectedCount=count(protected.instances)
local protectedResult, protectedReason=I.reconcile(plain,protected,"u:123")
assert(protectedResult==nil and protectedReason=="protected_identity")
assert(protected.nextId==protectedNext and count(protected.instances)==protectedCount)
assert(protected.instances['u:123/d:2'].cosmetics.ownedAuraIds.tidal)
local originalNext=legacy.nextId
local started=os.clock()
local state=I.copy(legacy)
local bucket='compy/variant/striped'
for n=1,150 do
 local qty=1+(n%3)
 local egg={eggId='egg-'..n,kind='alpha_chest',eventId='rain',mutationId='ember',big=true,shiny=true,genes=I.copy(genes),readyAt=100,reward={speciesId='compy',count=qty}}
 local ids=I.hatch(state,egg,'compy',qty,bucket)
 assert(#ids==qty)
 collection.compy.variants.striped.count+=qty
 egg.genes.blend=99
 assert(state.eggs[egg.eggId].genes.blend==20)
 state=assert(I.reconcile(collection,state,"u:123"))
end
assert(count(state.instances)==309 and count(state.eggs)==150)
local reconnected=assert(I.reconcile(collection,I.copy(state),"u:123"))
assert(reconnected.nextId==state.nextId)
for id,d in state.instances do assert(reconnected.instances[id].origin.kind==d.origin.kind) end
local before=state.nextId
assert(#I.hatch(state,{eggId='failed'},'compy',0,bucket)==0 and state.nextId==before and state.eggs.failed==nil)
assert(not pcall(I.hatch,state,{eggId='egg-1'},'compy',2,bucket))
local parents={state.instances['u:123/d:'..originalNext],state.instances['u:123/d:'..(originalNext+1)]}
parents[1].cosmetics.ownedAuraIds.meadow=true
parents[1].cosmetics.ownedTrailIds.fern=true
local fresh=I.copy(variant) fresh.speciesId='compy' fresh.stage='gold' fresh.genes.blend=75
local result=I.fusionRecord('u:123/d:1000',fresh,parents,'fusion-op','recipe-v1','odds-v1')
assert(result.genes.blend==75 and parents[1].genes.blend==20)
assert(result.origin.kind=='fusion' and #result.origin.parents==2)
assert(result.origin.parents[1].origin.eggId=='egg-1')
assert(next(result.cosmetics.ownedAuraIds)==nil and next(result.cosmetics.ownedTrailIds)==nil)
assert(result.origin.parents[1].cosmetics==nil)
local pending=I.copy(state)
pending.instances[result.instanceId]=I.copy(result)
local unsupported, fusionReason=I.reconcile(collection,pending,"u:123")
-- BD-057: a fusion record is only accepted when backed by a durable ledger entry.
assert(unsupported==nil and fusionReason=="missing_fusion_ledger")
assert(state.instances[result.instanceId]==nil)
assert(not pcall(I.fusionRecord,'new',fresh,{parents[1],parents[1]},'op','r','v'))
-- Nested ancestry is referenced, never copied recursively.
local higher=I.fusionRecord('higher',fresh,{result,parents[2]},'op2','r','v')
assert(higher.origin.parents[1].origin.operationId=='fusion-op')
assert(higher.origin.parents[1].origin.parents==nil)
print('150-egg reconciliation seconds:', os.clock()-started)
print('Identity passed: migration/rollback, 3,000-copy ceiling, owner isolation, immutable shared egg snapshots, 150 eggs/300 copies, reconnect, failures, explicit fusion boundary, bounded lineage and no cosmetic transfer')
'''
if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--runner',required=True); args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'identity.luau'; path.write_text(script())
        subprocess.run([args.runner,str(path)],check=True)
