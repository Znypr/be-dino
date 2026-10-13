"""Exercise real nest transactions using the existing repeated-transform datastore harness."""
from pathlib import Path
import argparse
import subprocess
import tempfile
import verify_progression

CHECKS=r'''
local nestUser={Parent=true,UserId=997,attrs={}}
function nestUser:SetAttribute(k,v)self.attrs[k]=v end
function nestUser:GetAttribute(k)return self.attrs[k]end
assert(Repository.load(nestUser))
assert(#data['u:997'].nests==0)
assert(Repository.commitRunSettlement(nestUser,"nest-run",10))
local p=data['u:997']
assert(#p.nests==2 and #p.eggs==2 and nestUser.attrs.LastRunEggNests==2)
local nestId=p.nests[1].id
local firstContents=copy(p.nests[1].contents)
assert(#firstContents>=3 and #firstContents<=6)
assert(p.nests[2].readyAt-p.nests[1].readyAt==GameConfig.EggNestTimerSeconds)
local ok,status=Repository.openEggNest(nestUser,nestId)
assert(not ok and status=="not_ready" and #data['u:997'].nests==2)
assert(Repository.commitRunSettlement(nestUser,"nest-run",10))
assert(#data['u:997'].nests==2 and data['u:997'].nests[1].contents[1].eggId==firstContents[1].eggId)
Repository.release(nestUser)
data['u:997'].nests[1].readyAt=os.time()-1 -- simulate elapsed offline time
assert(Repository.load(nestUser))
assert(Repository.openEggNest(nestUser,nestId))
assert(#data['u:997'].nests==1)
local queued=#data['u:997'].eggs+data['u:997'].pendingChestGrants
assert(queued==2+#firstContents)
assert(Repository.openEggNest(nestUser,nestId))
assert(#data['u:997'].eggs+data['u:997'].pendingChestGrants==queued)
Repository.release(nestUser)
assert(Repository.load(nestUser))
assert(Repository.openEggNest(nestUser,nestId))
assert(#data['u:997'].eggs+data['u:997'].pendingChestGrants==queued)
-- Every precommitted egg is retained, including overflow, and grants only once.
for _=1,queued do
    local id=data['u:997'].eggs[1].eggId
    assert(Repository.claimChest(nestUser,id))
    local before=copy(data['u:997'].collection)
    assert(Repository.claimChest(nestUser,id))
    for species,entry in before do assert(data['u:997'].collection[species].base==entry.base) end
end
assert(#data['u:997'].eggs==0 and data['u:997'].pendingChestGrants==0)
-- A full reveal queue leaves the ready nest and its original contents intact.
Repository.release(nestUser)
p=data['u:997']
p.nests[1].readyAt=os.time()-1
for i=1,GameConfig.ChestQueueCapacity do table.insert(p.eggs,{eggId="nest-full-"..i,readyAt=0}) end
p.pendingChestGrants=GameConfig.ChestOverflowCapacity
p.pendingEggEvents={}
for _=1,p.pendingChestGrants do table.insert(p.pendingEggEvents,{eventId="clear",mutationId=""}) end
assert(Repository.load(nestUser))
local keptId=p.nests[1].id
local revision=data['u:997'].revision
local ok,status=Repository.openEggNest(nestUser,keptId)
assert(not ok and status=="queue_full" and data['u:997'].revision==revision and #data['u:997'].nests==1)
-- Failed datastore writes leave the nest and egg queue untouched.
Repository.release(nestUser)
p=data['u:997']; p.eggs={}; p.pendingEggEvents={}; p.pendingChestGrants=0
assert(Repository.load(nestUser))
fail=true
assert(not Repository.openEggNest(nestUser,keptId))
assert(#data['u:997'].nests==1 and #data['u:997'].eggs==0)
fail=false
Repository.release(nestUser)
assert(Repository.load(nestUser) and Repository.openEggNest(nestUser,keptId))
nestSizeRoll=6
local sixUser={Parent=true,UserId=998,attrs={}}
function sixUser:SetAttribute(k,v)self.attrs[k]=v end
function sixUser:GetAttribute(k)return self.attrs[k]end
assert(Repository.load(sixUser) and Repository.commitRunSettlement(sixUser,"six-egg-run",10))
assert(#data['u:998'].nests[1].contents==6)
Repository.release(sixUser)
data['u:998'].nests[1].readyAt=os.time()-1
assert(Repository.load(sixUser) and Repository.openEggNest(sixUser,data['u:998'].nests[1].id))
assert(#data['u:998'].eggs==5 and data['u:998'].pendingChestGrants==3)
nestSizeRoll=3
print("Egg Nests passed: separate immediate eggs/timed nests, 3-6 committed contents, FIFO timers, offline readiness, repeated transforms, duplicate settlement/open/claim, rejoin, overflow and outage rollback")
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--runner',required=True)
    args=parser.parse_args()
    script=verify_progression.script()
    marker='fail=true\nlocal failed,failedStatus=action('
    assert marker in script
    script=script.replace(marker,CHECKS+'\n'+marker,1)
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'nests.luau'
        path.write_text(script,encoding='utf-8')
        subprocess.run([args.runner,str(path)],check=True)
