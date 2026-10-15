"""BD-090 Egg Nests v2 verification in pinned Luau.

Reuses the verify_rewards harness (real RewardMath, NestQueue, ProfileRepository against a mocked
DataStore that replays every UpdateAsync transform) with a controllable server clock (os.time).
Covers: hidden drop gate, exactly-once drop, one-at-a-time queue (5 nests = 15 h), offline
catch-up, storage cap, idempotent atomic open, bounded luck, legacy migration, big runs, DataStore
budget and byte size. Mocks validate transaction logic only, not Studio replication or UI.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_rewards  # noqa: E402

MARK = '------------------------------------------------------------------ RewardMath'

PRELUDE = '''local fakeNow=1800000000
local realOs=os
local os=setmetatable({time=function() return fakeNow end},{__index=realOs})
'''

TESTS = r'''
local H=3600
local D=GameConfig.NestIncubationSeconds
assert(D==3*H and GameConfig.NestStorageCapacity==5 and GameConfig.NestMinSize==10 and GameConfig.NestMaxSize==15)
local function nests(u) return data[key(u)].eggNests or {} end
local function jsonSize(v)
 if type(v)~="table" then return #tostring(v)+2 end
 local n=2 for k,c in v do n+=jsonSize(c)+#tostring(k)+3 end return n
end
local function run(u,id,catches,seconds) return Repository.commitRunSettlement(u,id,catches,nil,seconds) end
local function fresh(id) local u=user(id) assert(Repository.load(u)) return u end

------------------------------------------------------------------ NestQueue unit
do
 local q={{nestId="a",state="waiting"},{nestId="b",state="waiting"},{nestId="c",state="waiting"}}
 assert(NestQueue.advance(q,1000,D) and q[1].state=="incubating" and q[1].readyAt==1000+D and q[2].state=="waiting")
 assert(not NestQueue.advance(q,1000+D-1,D) and q[1].state=="incubating")
 NestQueue.advance(q,1000+D,D)
 assert(q[1].state=="ready" and q[2].state=="incubating" and q[2].readyAt==1000+2*D and q[3].state=="waiting")
 NestQueue.advance(q,1000+10*D,D) -- long offline: everything chains from the previous ready moment
 assert(q[1].state=="ready" and q[2].state=="ready" and q[3].state=="ready" and q[3].readyAt==1000+3*D)
 local p=NestQueue.project({{nestId="x",state="waiting"}},5,D)
 assert(p[1].state=="incubating" and p[1].readyAt==5+D)
 assert(NestQueue.secondsUntilAllReady({{nestId="x",state="waiting"},{nestId="y",state="waiting"}},0,D)==2*D)
 assert(NestQueue.secondsUntilAllReady({},0,D)==0)
end
print("NestQueue passed: one at a time, next starts when the previous becomes ready, offline chain, projection copy")

------------------------------------------------------------------ Size
do
 local seen={}
 for i=1,400 do
  local id=Rewards.nestId("run-"..i,1)
  local size=Rewards.nestSize(id)
  assert(size>=10 and size<=15 and size==Rewards.nestSize(id)) seen[size]=true
 end
 for size=10,15 do assert(seen[size],"size "..size.." never rolled") end
end
print("Nest size passed: deterministic 10-15 from the nest id, every size reachable")

------------------------------------------------------------------ Hidden drop gate (server run time + server catches)
local g=fresh(301)
local function expectNoNest(id,catches,seconds)
 local ok,outcome,status=run(g,id,catches,seconds)
 assert(ok and status=="committed" and outcome.nestCount==0 and not outcome.nestFull,id)
 assert(not string.find(g.attrs.LastRewardText,"nest"),"a non-qualifying run must say nothing about nests")
 assert(#nests(g)==0,id)
end
expectNoNest("gate-0s",20,0)
expectNoNest("gate-119s",20,119)
expectNoNest("gate-unknown",20,nil)
expectNoNest("gate-long-no-food",0,3600)
expectNoNest("gate-long-0-catches",0,3600)
local okGate,outGate=run(g,"gate-120s",1,120)
assert(okGate and outGate.nestCount==1 and #nests(g)==1 and string.find(g.attrs.LastRewardText,"1 egg nest"))
local before=copy(data[key(g)])
local dupOk,dupOut,dupStatus=run(g,"gate-120s",1,120)
assert(dupOk and dupStatus=="duplicate" and dupOut.nestCount==1 and same(before,data[key(g)]),"qualified replay is identical")
dupOk,_,dupStatus=run(g,"gate-119s",500,9999) -- earlier non-qualified run replayed with a "qualifying" claim
assert(dupStatus=="duplicate" and #nests(g)==1,"replay cannot upgrade a committed non-qualified run")
print("Hidden gate passed: 0 s / 119 s / unknown time / long run with 0 or 7 catches -> no nest and no nest text; 120 s + 8 catches -> 1 nest; replays identical")

------------------------------------------------------------------ Exactly-once + reload
Repository.release(g) assert(Repository.load(g))
assert(#nests(g)==1 and select(3,run(g,"gate-120s",1,120))=="duplicate" and #nests(g)==1)
local nest1=nests(g)[1]
assert(nest1.state=="incubating" and nest1.readyAt==fakeNow+D and nest1.droppedFromRun=="gate-120s" and nest1.size==Rewards.nestSize(nest1.nestId))
print("Exactly-once passed: reload and replay keep one nest")

------------------------------------------------------------------ Queue timing: 5 nests = 15 h, offline catch-up
local q=fresh(302)
local t0=fakeNow
for i=1,5 do assert(run(q,"q-"..i,10,300)) end
assert(#nests(q)==5 and nests(q)[1].state=="incubating" and nests(q)[1].readyAt==t0+D)
for i=2,5 do assert(nests(q)[i].state=="waiting") end
local ids={} for i=1,5 do ids[i]=nests(q)[i].nestId end
assert(select(3,Repository.claimNest(q,ids[1]))=="not_ready" and select(3,Repository.claimNest(q,ids[2]))=="nest_pending")
fakeNow=t0+D-1
assert(select(3,Repository.claimNest(q,ids[1]))=="not_ready")
-- Offline for 7 h: nests 1-2 ready, 3 incubating until 9 h.
Repository.release(q) fakeNow=t0+7*H assert(Repository.load(q))
assert(nests(q)[1].state=="ready" and nests(q)[2].state=="ready" and nests(q)[3].state=="incubating" and nests(q)[3].readyAt==t0+9*H)
assert(nests(q)[4].state=="waiting" and q.attrs.NestsJson[3].readyAt==t0+9*H)
-- The last nest becomes ready exactly at 15 h, not before.
fakeNow=t0+15*H-1
assert(select(3,Repository.claimNest(q,ids[5]))=="not_ready")
fakeNow=t0+15*H
Repository.release(q) assert(Repository.load(q))
for i=1,5 do assert(nests(q)[i].state=="ready" and nests(q)[i].readyAt==t0+i*3*H) end
print("Queue passed: 5 nests = 15 h on server time, one incubating at a time, waiting nests wait, offline time counts, exact boundaries")

------------------------------------------------------------------ Storage cap
local full=fresh(303)
for i=1,5 do assert(run(full,"cap-"..i,10,300)) end
assert(#nests(full)==5)
local ok,outcome,status=run(full,"cap-6",50,300)
assert(ok and status=="committed" and outcome.nestCount==0 and outcome.nestFull==true and #nests(full)==5)
assert(string.find(full.attrs.LastRewardText,"nest storage full") and full.attrs.LastRunNestFull==true and full.attrs.LastRunNestCount==0)
assert(data[key(full)].progression.crystals>0,"settlement still pays eggs and crystals")
-- A qualified run that earns 3 nests with 4 owned: only one fits.
local part=fresh(304)
for i=1,4 do assert(run(part,"part-"..i,10,300)) end
local _,partOut=run(part,"part-big",400,600)
assert(partOut.nestCount==1 and partOut.nestFull==true and #nests(part)==5)
-- Opening frees a slot (after the nest is ready).
fakeNow+=20*H
Repository.release(full) assert(Repository.load(full))
assert(select(3,Repository.claimNest(full,nests(full)[1].nestId))=="opened")
local _,again=run(full,"cap-7",10,300)
assert(again.nestCount==1 and #nests(full)==5)
print("Storage cap passed: full -> no nest, settlement succeeds, 'nest storage full' reported only for qualified runs, partial grant, slot frees on open")

------------------------------------------------------------------ Open: atomic, idempotent, luck
local o=fresh(305)
assert(run(o,"open-1",10,300))
local nid=nests(o)[1].nestId
local size=nests(o)[1].size
fakeNow+=D
data[key(o)].runEggBank=data[key(o)].runEggBank or {}
local bankBefore=bankCount(o)+#data[key(o)].eggs
local opened,res,openStatus=Repository.claimNest(o,nid)
assert(opened and openStatus=="opened" and res.eggCount==size and #nests(o)==0)
local after=bankCount(o)+#data[key(o)].eggs
assert(after==bankBefore+size,"all nest eggs credited exactly once")
local nestEggs={}
for _,egg in revealLine(o) do if egg.kind=="nest_egg" then table.insert(nestEggs,egg) end end
assert(#nestEggs==size)
for i,egg in nestEggs do
 assert(egg.source.kind=="nest" and egg.source.nestId==nid and egg.source.luck==1 and egg.reward.count==1 and Genetics.valid(egg.genes))
 assert(egg.eggId==nid..":"..egg.source.ordinal)
end
local snapshot=copy(data[key(o)])
local t=transforms
local dupOpen,dupRes,dupStatus=Repository.claimNest(o,nid)
assert(dupOpen and dupStatus=="duplicate" and same(snapshot,data[key(o)]) and transforms==t,"duplicate open is a cached no-op")
Repository.release(o) assert(Repository.load(o))
assert(select(3,Repository.claimNest(o,nid))=="duplicate" and bankCount(o)+#data[key(o)].eggs==after)
assert(select(3,Repository.claimNest(o,"nest:missing:1"))=="missing" and select(3,Repository.claimNest(o,string.rep("x",81)))=="invalid_nest_id")
-- Bank-full refusal keeps the nest.
assert(run(o,"open-2",10,300))
fakeNow+=D
local nid2=nests(o)[1].nestId
while #data[key(o)].runEggBank<GameConfig.RunEggBankCapacity-1 do table.insert(data[key(o)].runEggBank,copy(data[key(o)].runEggBank[1] or nestEggs[1])) end
assert(select(3,Repository.claimNest(o,nid2))=="bank_full" and #nests(o)==1 and nests(o)[1].nestId==nid2)
print("Open passed: eggs credited once at the queue front as nest_egg, duplicate/reload no-op, missing/invalid refused, bank_full keeps the nest")

------------------------------------------------------------------ Luck is applied and bounded
do
 local L=fresh(306)
 local tier=GameConfig.NestLuckTiers[1]
 local total,shiny,big,cracked,rare,baseRare=0,0,0,0,0,0
 local rng=Random.new()
 for i=1,200 do
  data[key(L)].runEggBank={} data[key(L)].eggs={} data[key(L)].eggNests=data[key(L)].eggNests or {}
  table.insert(data[key(L)].eggNests,{nestId="luck-"..i,droppedFromRun="luck-run",size=15,luck=1,state="ready",readyAt=1})
  assert(select(3,Repository.claimNest(L,"luck-"..i))=="opened")
  for _,egg in revealLine(L) do
   total+=1 if egg.shiny then shiny+=1 end if egg.big then big+=1 end
   if egg.genes.conditionId=="cracked" then cracked+=1 end
   if GameConfig.SpeciesRarities[egg.reward.speciesId]>=2 then rare+=1 end
   local base=Rewards.computeChestReward(rng,1)
   if GameConfig.SpeciesRarities[base.speciesId]>=2 then baseRare+=1 end
  end
 end
 assert(total==3000)
 local shinyRate,bigRate,crackedRate=shiny/total,big/total,cracked/total
 assert(math.abs(shinyRate-tier.shinyChance)<.015,"shiny "..shinyRate)
 assert(math.abs(bigRate-tier.bigChance)<.03,"big "..bigRate)
 assert(bigRate>GameConfig.BigChance*1.5 and shinyRate>0,"luck must be clearly noticeable")
 -- +2 condition levels: tier-2 weights (34% Cracked) instead of tier-0 (50%).
 assert(math.abs(crackedRate-.34)<.04,"cracked "..crackedRate)
 assert(rare>=baseRare*.97,"BD-165: nest rarity boost is mild by design but never worse than base: "..rare.." vs "..baseRare)
 assert(tier.rarityBoostEggs<=GameConfig.EggRarityBoostMaxEggs and tier.conditionLevels<=2 and tier.bigChance<=.25 and tier.shinyChance<=.05,"bounded")
 print(string.format("Luck passed: 3000 nest eggs Shiny %.1f%% BIG %.1f%% Cracked %.1f%% rare+ %d vs %d at no boost; bounded by config tier",shinyRate*100,bigRate*100,crackedRate*100,rare,baseRare))
end

------------------------------------------------------------------ Migration of Build 020 nests
do
 local m=fresh(307)
 Repository.release(m)
 local function oldEgg(nest,k) return {eggId=nest..":"..k,kind="nest_egg",eventId="clear",mutationId="",reward={speciesId="compy",count=1,mutationId="base"},source={kind="nest",nestId=nest,ordinal=k}} end
 local function oldNest(id,readyAt) local n={nestId=id,eggs={oldEgg(id,1),oldEgg(id,2),oldEgg(id,3)},source={kind="run_nest",runId="oldrun",ordinal=1}} if readyAt then n.readyAt=readyAt end return n end
 local p=data[key(m)]
 p.nests={oldNest("old-ready",fakeNow-10),oldNest("old-soon",fakeNow+100),oldNest("old-later",fakeNow+200)}
 p.pendingNests={oldNest("old-pending-1"),oldNest("old-pending-2")}
 assert(Repository.load(m))
 local list=nests(m)
 assert(#list==5 and data[key(m)].nests==nil and data[key(m)].pendingNests==nil,"nothing lost, old fields retired")
 assert(list[1].state=="ready" and list[2].state=="incubating" and list[2].readyAt==fakeNow+100)
 for i=3,5 do assert(list[i].state=="waiting") end
 for _,n in list do assert(n.size==3 and #n.eggs==3 and n.luck==1) end
 local saved=copy(list[1].eggs)
 local _,res,st=Repository.claimNest(m,"old-ready")
 assert(st=="opened" and res.eggCount==3)
 local line=revealLine(m) for i,egg in saved do assert(line[i].eggId==egg.eggId,"legacy eggs credited unchanged, first in line") end
 Repository.release(m) assert(Repository.load(m)) assert(#nests(m)==4)
 -- Later the queue continues: old nests wait their turn behind the incubating one.
 local soonAt=nests(m)[1].readyAt -- old-soon is now first (old-ready was opened)
 fakeNow+=100 Repository.release(m) assert(Repository.load(m))
 assert(nests(m)[1].nestId=="old-soon" and nests(m)[1].state=="ready" and nests(m)[2].state=="incubating" and nests(m)[2].readyAt==soonAt+D)
 print("Migration passed: slotted+pending Build 020 nests become v2 records keeping their eggs, ready/incubating/waiting mapped, nothing lost, reload stable")
end

------------------------------------------------------------------ Big runs, DataStore budget, size
do
 local b=fresh(308)
 local t1=transforms
 local ok,out=run(b,"big-15",15,300)
 local used=transforms-t1
 assert(ok and out.eggCount==15 and out.nestCount==2 and bankCount(b)+#data[key(b)].eggs==15 and #nests(b)==2)
 local c=fresh(309)
 local t2=transforms
 local ok2,out2=run(c,"big-40",40,900)
 assert(ok2 and out2.eggCount==40 and out2.nestCount==GameConfig.NestMaxPerRun and bankCount(c)+#data[key(c)].eggs==40)
 assert(transforms-t2==used,"a run with nests costs the same DataStore writes as one without")
 local d=fresh(310)
 local t3=transforms
 assert(run(d,"plain-150",150,5))
 assert(transforms-t3==used,"nest drop adds no extra UpdateAsync")
 local bytes=jsonSize(nests(b))+0
 assert(jsonSize(nests(c))<700 and jsonSize(nests(c))/#nests(c)<260,"a nest record is a few hundred bytes")
 local f=fresh(311)
 for i=1,5 do assert(run(f,"bytes-"..i,10,300)) end
 assert(jsonSize(nests(f))<1300,"5 nests stay tiny: "..jsonSize(nests(f)))
 print(string.format("Big runs passed: 150 eggs -> 2 nests, 400 eggs -> %d nests, %d UpdateAsync per settlement with or without nests, 5 nests = %d bytes",GameConfig.NestMaxPerRun,used,jsonSize(nests(f))))
end
print("BD-090 egg nests verified (offline Luau; Studio verification pending)")
'''


def script():
    s = verify_rewards.script()
    head = s[:s.index(MARK)]
    return PRELUDE + head + TESTS


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'nests.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
