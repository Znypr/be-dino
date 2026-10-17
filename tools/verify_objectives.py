"""BD-072/BD-073 mini objectives (docs/66): offline verifier in pinned Luau.

Runs the REAL src/shared/ObjectiveConfig.luau, src/shared/ObjectiveRules.luau, src/server/ObjectiveService.luau and the REAL
src/server/ProfileRepository.luau (against the mocked DataStore of tools/verify_rewards.py, like tools/verify_rollback.py).
Covers: catalogue schema and docs/66 table parity, crystal/XP-only rewards and caps, deterministic windows, server-clock
rollover (short 30 min, daily UTC midnight, one-window carry), counters and replay protection, claim-once with tokens,
additive migration (nil / corrupt / newer-version), flag-off identity (no read, no write, no store traffic), reconnect and
lost-acknowledgement safety, and the rate-limited ObjectiveAction remote. Offline only: no Studio, no real DataStore.

  python tools/verify_objectives.py --runner C:/path/to/luau.exe
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release_profiles  # noqa: E402
import verify_rewards  # noqa: E402  (reuses the mocked DataStore prefix)


sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402


def module(path: str) -> str:
    return profile_sources.module(path)  # docs/150: ProfileRepository plus the parts it installs


def doc_rows() -> list[tuple[str, str, int, int]]:
    """(id, group, goal, reward) from the docs/66 catalogue table."""
    text = (ROOT / 'docs' / '66-intake-mini-objectives.md').read_text(encoding='utf-8')
    rows = []
    for m in re.finditer(r'^\| ([TSD]\d) \| (Tutorial|Short|Daily) \| [^|]+ \| (\d+) \| (\d+) \|$', text, re.M):
        rows.append((m.group(1), m.group(2).lower(), int(m.group(3)), int(m.group(4))))
    return rows


def static_errors() -> list[str]:
    errors: list[str] = []
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    entries = release_profiles.config_entries(config)
    found = entries.get('ObjectivesEnabled')
    if not found or found[-1][1] is not False:
        errors.append('Config.ObjectivesEnabled must exist and be false in source')
    for profile in ('default', 'playtest'):
        rules = [r for r in release_profiles.rules_for(profile) if r.key == 'ObjectivesEnabled']
        if not rules or any(r.mode != 'require' or r.value is not False for r in rules):
            errors.append(f'release profile {profile!r} must pin ObjectivesEnabled to false (mode require)')
    for path in ('src/shared/ObjectiveConfig.luau', 'src/shared/ObjectiveRules.luau', 'src/server/ObjectiveService.luau'):
        text = re.sub(r'--.*$', '', (ROOT / path).read_text(encoding='utf-8'), flags=re.M)
        for word in ('MarketplaceService', 'PromptProductPurchase', 'PromptGamePassPurchase', 'DeveloperProducts', 'Robux'):
            if word in text:
                errors.append(f'{path} mentions {word}: objectives must never touch Robux')
    for path in ('src/shared/ObjectiveConfig.luau', 'src/shared/ObjectiveRules.luau'):
        text = re.sub(r'--.*$', '', (ROOT / path).read_text(encoding='utf-8'), flags=re.M)
        for word in ('Instance.new', 'game:GetService', 'os.time', 'os.clock', 'DataStore', 'RemoteEvent', 'RemoteFunction'):
            if word in text:
                errors.append(f'{path} must stay pure, found {word}')
    return errors


PURE = r'''
local ObjectiveConfig=@@OBJ_CONFIG@@
local script={Parent={ObjectiveConfig="ObjectiveConfig"}}
local require=function(_) return ObjectiveConfig end
local Rules=@@OBJ_RULES@@

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
local C=ObjectiveConfig
local DAY0=20833*86400 -- a UTC midnight (1799971200); short windows (1800 s) are aligned to it
local function newState(now) local s=Rules.fresh() Rules.advance(s,now) return s end
local function finish(s,group,i) -- drive the i-th active row of a window group to its goal through the real event path
 local entry=C.ById[s[group].ids[i]]
 Rules.applyEvents(s,{{kind=entry.event,amount=entry.goal,value=entry.minValue}},DAY0+100)
 return entry
end

------------------------------------------------------------------ BD-072 catalogue
assert(#C.Catalogue==20 and C.SchemaVersion==1)
local groups={tutorial=0,short=0,daily=0}
local tutorialTotal=0
local seenIds={}
for _,e in C.Catalogue do
 assert(not seenIds[e.id],"duplicate id "..e.id) seenIds[e.id]=true
 assert(groups[e.group]~=nil,e.id) groups[e.group]+=1
 assert(string.match(e.id,"^[TSD]%d$") and string.sub(e.id,1,1)==string.upper(string.sub(e.group,1,1)),e.id)
 assert(type(e.name)=="string" and #e.name>=3 and #e.name<=40,e.id.." name is short, plain copy (docs/72)")
 assert(C.EventKinds[e.event]==true,e.id.." event")
 assert(e.goal%1==0 and e.goal>=1 and e.goal<=1000,e.id.." goal")
 assert(C.ById[e.id]==e)
 for k,v in e.reward do
  assert(k=="crystals" or k=="xp",e.id.." reward may only be crystals or xp, found "..tostring(k))
  assert(type(v)=="number" and v%1==0 and v>=0,e.id)
 end
 assert((e.reward.crystals or 0)>=1 and e.reward.crystals<=C.MaxClaimCrystals,e.id.." crystal reward within the per-claim cap")
 assert((e.reward.xp or 0)<=C.MaxClaimXP)
 assert(e.minValue==nil or e.id=="T7","only T7 has a threshold")
 if e.group=="tutorial" then tutorialTotal+=e.reward.crystals end
end
assert(groups.tutorial==9 and groups.short==5 and groups.daily==6)
assert(tutorialTotal==160,"tutorial gift is 160 Crystals (docs/66): "..tutorialTotal)
assert(C.Windows.short.seconds==1800 and C.Windows.daily.seconds==86400 and C.Windows.short.active==3 and C.Windows.daily.active==3)
for _,k in {"MaxClaimCrystals","MaxClaimXP","WindowCrystalCapPerDay","SeenMax","PendingMax","ProgressCapMultiplier","RequestsPerWindow"} do
 assert(type(C[k])=="number" and C[k]>0,k)
end
assert(C.WindowCrystalCapPerDay>=C.MaxClaimCrystals)
for _,doc in @@DOC_ROWS@@ do
 local e=C.ById[doc[1]]
 assert(e and e.group==doc[2] and e.goal==doc[3] and e.reward.crystals==doc[4],"docs/66 row "..doc[1].." differs from ObjectiveConfig")
end
assert(@@DOC_COUNT@@==20,"docs/66 table must list the 20 objectives")
print("BD-072 catalogue passed: 20 objectives, crystal/xp rewards only, caps, docs/66 parity, tutorial 160")

------------------------------------------------------------------ deterministic picks
for w=1,300 do
 for group,prefix in {short="S",daily="D"} do
  local ids=Rules.pick(group,w)
  assert(#ids==3,"3 active")
  local set={}
  for _,id in ids do assert(string.sub(id,1,1)==prefix and not set[id] and C.ById[id]) set[id]=true end
  assert(same(ids,Rules.pick(group,w)),"same window, same pick")
 end
end
local coverage={short={},daily={}}
local variety={}
for w=1,300 do
 for group in coverage do for _,id in Rules.pick(group,w) do coverage[group][id]=true end end
 variety[table.concat(Rules.pick("short",w),",")]=true
end
for _,id in {"S1","S2","S3","S4","S5","D1","D2","D3","D4","D5","D6"} do assert(coverage.short[id] or coverage.daily[id],id.." is reachable") end
local varietyCount=0 for _ in variety do varietyCount+=1 end
assert(varietyCount>=8,"windows differ")
print("Picks passed: 3 distinct per window, deterministic, every pool entry reachable")

------------------------------------------------------------------ window rollover (server clock)
assert(Rules.windowNumber("short",DAY0+1799)==Rules.windowNumber("short",DAY0) and Rules.windowNumber("short",DAY0+1800)==Rules.windowNumber("short",DAY0)+1)
assert(Rules.windowNumber("daily",DAY0+86399)==DAY0//86400 and Rules.windowNumber("daily",DAY0+86400)==DAY0//86400+1,"daily resets at UTC midnight")
assert(Rules.windowNumber("short",-5)==0)
local s=newState(DAY0+100)
assert(s.short.window==(DAY0+100)//1800 and s.daily.window==DAY0//86400 and #s.short.ids==3 and #s.daily.ids==3)
-- same instant twice = no change; progress survives inside the window
finish(s,"short",1)
local snap=copy(s) Rules.advance(s,DAY0+1799) assert(same(s,snap),"inside the window nothing changes")
-- find a window where the finished row's id does not come back, so the carry claim is unambiguous
local finishedId=s.short.ids[1]
-- next window: finished-but-unclaimed row carries for ONE window
Rules.advance(s,DAY0+1800+5)
assert(s.short.window==(DAY0+1805)//1800 and same(s.short.ids,Rules.pick("short",s.short.window)))
for i=1,3 do assert(s.short.progress[i]==0 and s.short.claimed[i]==false,"new window starts empty") end
assert(s.short.carry and s.short.carry.window==(DAY0+100)//1800 and table.find(s.short.carry.ids,finishedId))
for _,id in s.short.carry.ids do assert(C.ById[id].group=="short") end
-- an unfinished row never carries
local cids=s.short.carry.ids
assert(#cids==1,"only the finished row carries, got "..#cids)
-- two windows later the carry is gone
local s2=newState(DAY0+100) finish(s2,"short",1) Rules.advance(s2,DAY0+3600+5)
assert(s2.short.carry==nil,"older than one window = vanished (no backlog guilt)")
-- clock moving backwards never wipes progress
local s3=newState(DAY0+3700) finish(s3,"short",2) local before=copy(s3) Rules.advance(s3,DAY0+100)
assert(same(s3,before),"a stored window ahead of the clock is left alone")
-- daily: carry across midnight, earned counter resets by UTC day
local d=newState(DAY0+86000) finish(d,"daily",1)
Rules.advance(d,DAY0+86400+1)
assert(d.daily.window==DAY0//86400+1 and d.daily.carry and #d.daily.carry.ids==1)
d.earned.crystals=77 Rules.advance(d,DAY0+86400+50) assert(d.earned.crystals==77,"same day keeps the counter")
Rules.advance(d,DAY0+2*86400+1) assert(d.earned.crystals==0 and d.earned.day==DAY0//86400+2 and d.daily.carry==nil)
print("Rollover passed: 30 min short windows, UTC-midnight daily, one-window carry, clock-back safe, daily cap day reset")

------------------------------------------------------------------ counters and replay protection
local c=newState(DAY0+100)
local junk={false,{},{kind="nope"},{kind="run_end",amount=0},{kind="run_end",amount=1.5},{kind="run_end",amount="3"},{kind="run_end",id=string.rep("x",81)},
 {kind="run_end",id=""},{kind="run_end",value=0/0},{kind="run_end",amount=100001},5,"x"}
assert(Rules.applyEvents(c,junk,DAY0+100)==0,"junk events are ignored")
assert(c.tutorial.progress.T2==nil)
assert(Rules.applyEvents(c,{{kind="run_end"}},DAY0+100)==1 and c.tutorial.progress.T2==1)
-- cap: never above 2 x goal
Rules.applyEvents(c,{{kind="food_eaten",amount=100000}},DAY0+100)
assert(c.tutorial.progress.T1==C.ById.T1.goal*C.ProgressCapMultiplier,"counter cap 2 x goal")
-- threshold objective
Rules.applyEvents(c,{{kind="level_reached",value=2}},DAY0+100) assert((c.tutorial.progress.T7 or 0)==0)
Rules.applyEvents(c,{{kind="level_reached"}},DAY0+100) assert((c.tutorial.progress.T7 or 0)==0,"no value, no credit")
Rules.applyEvents(c,{{kind="level_reached",value=3}},DAY0+100) assert(c.tutorial.progress.T7==1)
-- replay
local r=newState(DAY0+100)
Rules.applyEvents(r,{{kind="egg_hatched",id="egg:a"},{kind="egg_hatched",id="egg:a"},{kind="egg_hatched",id="egg:b"}},DAY0+100)
assert(r.tutorial.progress.T3==2,"a replayed event id counts once")
Rules.applyEvents(r,{{kind="egg_hatched",id="egg:a"}},DAY0+100) assert(r.tutorial.progress.T3==2)
for i=1,C.SeenMax+30 do Rules.applyEvents(r,{{kind="food_eaten",id="food:"..i}},DAY0+100) end
assert(#r.seen==C.SeenMax,"seen ring is bounded")
-- claimed rows stop counting
local k=newState(DAY0+100)
Rules.applyEvents(k,{{kind="food_eaten",amount=10}},DAY0+100)
assert(Rules.claim(k,"T1",DAY0+100,nil))
Rules.applyEvents(k,{{kind="food_eaten",amount=5}},DAY0+100) assert(k.tutorial.progress.T1==10)
-- queue
local q={}
assert(Rules.queue(q,{kind="food_eaten",amount=2}) and Rules.queue(q,{kind="food_eaten",amount=3,value=7}) and #q==1 and q[1].amount==5 and q[1].value==7,"id-less events of a kind merge")
assert(not Rules.queue(q,{kind="nope"}) and not Rules.queue(q,5))
for i=1,C.PendingMax+10 do Rules.queue(q,{kind="egg_hatched",id="e"..i}) end
assert(#q==C.PendingMax,"pending queue is bounded")
print("Counters passed: junk ignored, 2x goal cap, threshold, replay-once, bounded ring and queue")

------------------------------------------------------------------ claim once, wallet, caps
local w={crystals=5,accountXP=0}
local n=newState(DAY0+100)
Rules.applyEvents(n,{{kind="food_eaten",amount=10}},DAY0+100)
local ok,status,grant=Rules.claim(n,"T1",DAY0+100,w,2000000000)
assert(ok and status=="claimed" and grant.crystals==10 and grant.xp==0 and w.crystals==15)
local ok2,status2,grant2=Rules.claim(n,"T1",DAY0+100,w,2000000000)
assert(not ok2 and status2=="already_claimed" and grant2==nil and w.crystals==15,"claim exactly once")
assert(select(2,Rules.claim(n,"T2",DAY0+100,w))=="not_done" and w.crystals==15)
assert(select(2,Rules.claim(n,"ZZ",DAY0+100,w))=="unknown_objective" and select(2,Rules.claim(n,5,DAY0+100,w))=="unknown_objective" and select(2,Rules.claim(n,nil,DAY0+100,w))=="unknown_objective")
local inactive for _,id in {"S1","S2","S3","S4","S5"} do if not table.find(n.short.ids,id) then inactive=id break end end
assert(select(2,Rules.claim(n,inactive,DAY0+100,w))=="not_active","a pool entry that is not one of the 3 active rows cannot be claimed")
local w2={crystals=1999999995}
local n2=newState(DAY0+100) Rules.applyEvents(n2,{{kind="food_eaten",amount=10}},DAY0+100)
Rules.claim(n2,"T1",DAY0+100,w2,2000000000) assert(w2.crystals==2000000000,"wallet clamps to MaxCrystals")
-- carry claim: finish, roll, claim once from the carry
for off=1,200 do -- find a window whose next window does not repeat the row, so the carry claim is unambiguous
 local now=DAY0+100+1800*(off-1)
 local t=newState(now) local e=finish(t,"short",1) Rules.advance(t,now+1800)
 if not table.find(t.short.ids,e.id) then
  local wallet={crystals=0}
  local cok,cst=Rules.claim(t,e.id,now+1800,wallet)
  assert(cok and cst=="claimed" and wallet.crystals==e.reward.crystals,"carried row claims from the window after")
  assert(select(2,Rules.claim(t,e.id,now+1800,wallet))=="already_claimed" and wallet.crystals==e.reward.crystals)
  local gone=newState(now) finish(gone,"short",1) Rules.advance(gone,now+3600+10)
  assert(select(2,Rules.claim(gone,e.id,now+3600+10,{crystals=0}))~="claimed" or table.find(gone.short.ids,e.id),"carry expired after one window")
  break
 end
end
-- synthetic catalogue: per-claim cap, xp, daily cap
local cfg=table.clone(C)
cfg.WindowCrystalCapPerDay=20
local cat={{id="T1",group="tutorial",name="Test",event="run_end",goal=1,reward={crystals=500,xp=999}}}
for i=1,3 do
 table.insert(cat,{id="S"..i,group="short",name="Short",event="run_end",goal=1,reward={crystals=15}})
 table.insert(cat,{id="D"..i,group="daily",name="Daily",event="run_end",goal=1,reward={crystals=15}})
end
local byId={} for _,e in cat do byId[e.id]=e end
cfg.Catalogue,cfg.ById=cat,byId
local R=Rules.with(cfg)
local sy=R.fresh() R.advance(sy,DAY0+100)
R.applyEvents(sy,{{kind="run_end",amount=3}},DAY0+100)
local wallet={crystals=0,accountXP=0}
local _,st,g=R.claim(sy,"T1",DAY0+100,wallet,2000000000)
assert(st=="claimed" and g.crystals==C.MaxClaimCrystals and g.xp==C.MaxClaimXP and wallet.crystals==100 and wallet.accountXP==50,"per-claim caps clamp a huge catalogue reward")
_,st,g=R.claim(sy,"S1",DAY0+100,wallet) assert(st=="claimed" and g.crystals==15)
_,st,g=R.claim(sy,"S2",DAY0+100,wallet) assert(st=="claimed_capped" and g.crystals==5,"daily cap clamps the claim to what is left")
_,st,g=R.claim(sy,"D1",DAY0+100,wallet) assert(st=="claimed_capped" and g.crystals==0 and sy.earned.crystals==20)
assert(wallet.crystals==120,"never more than cap + tutorial")
R.advance(sy,DAY0+86400+10) R.applyEvents(sy,{{kind="run_end",amount=3}},DAY0+86400+10)
_,st,g=R.claim(sy,"S1",DAY0+86400+10,wallet) assert(st=="claimed" and g.crystals==15,"the cap resets with the UTC day")
-- the shipped catalogue can never beat the shipped cap in ONE window pair
local maxShort,maxDaily=0,0
for _,e in C.Catalogue do
 if e.group=="short" then maxShort=math.max(maxShort,e.reward.crystals) elseif e.group=="daily" then maxDaily=math.max(maxDaily,e.reward.crystals) end
end
assert(3*maxDaily<=C.WindowCrystalCapPerDay,"a day of Dailies fits under the daily cap")
print("Claim passed: exactly once, not_done/not_active/unknown, MaxCrystals clamp, carry claim, per-claim and daily caps, xp")

------------------------------------------------------------------ migration
local function fresh1() return Rules.fresh() end
for _,bad in {"x",5,true,{},{v=0},{v=1.5},{v=0/0},{v="1"},{v=-1}} do
 local st,status=Rules.load(bad) assert(st and status=="created" and same(st,fresh1()),"corrupt/unknown objectives read as empty")
end
local st0,status0=Rules.load(nil) assert(status0=="created" and same(st0,fresh1()))
local newer={v=2,keep="me",tutorial={claimed={T1=true}}}
local newerCopy=copy(newer)
local ns,nstatus=Rules.load(newer) assert(ns==nil and nstatus=="newer_version" and same(newer,newerCopy))
local profile={objectives=newer,progression={crystals=3}}
local pok,pstatus=Rules.applyToProfile(profile,{{kind="run_end"}},DAY0,"b1")
assert(not pok and pstatus=="newer_version" and same(profile.objectives,newerCopy) and profile.progression.crystals==3,"a newer build's field is never touched")
local cok2,cstatus2=Rules.claimOnProfile(profile,profile.progression,"T1",{},DAY0,2000000000)
assert(not cok2 and cstatus2=="newer_version" and profile.progression.crystals==3 and same(profile.objectives,newerCopy))
assert(select(2,Rules.view(newer,DAY0))=="newer_version" and same(newer,newerCopy))
-- a well-formed state round-trips unchanged (idempotent migration)
local good=newState(DAY0+100) finish(good,"short",1) finish(good,"daily",2)
Rules.applyEvents(good,{{kind="food_eaten",amount=10,id="food:1"},{kind="run_end"}},DAY0+100)
Rules.claim(good,"T1",DAY0+100,{crystals=0})
Rules.advance(good,DAY0+1800+3)
local loaded=Rules.load(good) assert(same(loaded,good),"load(well-formed) == itself")
assert(same(Rules.load(loaded),loaded))
-- sanitising
local dirty={v=1,tutorial={progress={T1=-5,T2=1e12,ZZ=3,T3="x"},claimed={T1=true,ZZ=true,T2="yes"}},
 short={window=5,ids={"D1","S1"},progress={1,1},claimed={false,false}},daily={window=-1,ids={"D1"}},
 earned={day=-4,crystals=1e15},seen={5,"ok",string.rep("x",200)},flush=17}
local dirtyCopy=copy(dirty)
local cleaned=Rules.load(dirty)
assert(same(dirty,dirtyCopy),"load never mutates its input")
assert(cleaned.tutorial.claimed.T1==true and cleaned.tutorial.claimed.ZZ==nil and cleaned.tutorial.claimed.T2==nil)
assert(cleaned.tutorial.progress.T1==nil and cleaned.tutorial.progress.T2==C.ById.T2.goal*C.ProgressCapMultiplier and cleaned.tutorial.progress.ZZ==nil and cleaned.tutorial.progress.T3==nil)
assert(Rules.load({v=1,tutorial={progress={T4=0/0}}}).tutorial.progress.T4==nil,"NaN counters are dropped")
assert(cleaned.short==nil and cleaned.daily==nil,"a group with an unknown/foreign id is rolled afresh, not trusted")
assert(cleaned.earned.day==0 and cleaned.earned.crystals==2000000000 and #cleaned.seen==1 and cleaned.seen[1]=="ok" and cleaned.flush==nil)
local cleanedProfile={objectives=dirty}
assert(Rules.applyToProfile(cleanedProfile,{},DAY0+100)) assert(cleanedProfile.objectives.short and cleanedProfile.objectives.daily)
-- batch ids make a retried batch idempotent
local bp={}
assert(select(2,Rules.applyToProfile(bp,{{kind="run_end"}},DAY0+100,"batch-1"))=="created" and bp.objectives.tutorial.progress.T2==1)
assert(select(2,Rules.applyToProfile(bp,{{kind="run_end"}},DAY0+100,"batch-1"))=="duplicate" and bp.objectives.tutorial.progress.T2==1,"same batch id twice counts once")
assert(select(2,Rules.applyToProfile(bp,{{kind="run_end"}},DAY0+100,"batch-2"))=="ok" and bp.objectives.tutorial.progress.T2==2)
-- a failed claim leaves the profile and wallet untouched
local cp={objectives=nil,progression={crystals=9}}
local before2=copy(cp)
assert(not Rules.claimOnProfile(cp,cp.progression,"T1",{{kind="food_eaten",amount=3}},DAY0+100,2000000000))
assert(same(cp,before2),"a denied claim writes nothing, not even the events it carried")
cp.objectives=nil
assert(Rules.claimOnProfile(cp,cp.progression,"T1",{{kind="food_eaten",amount=10}},DAY0+100,2000000000) and cp.progression.crystals==19 and cp.objectives.tutorial.claimed.T1)
-- view is read-only and complete
local raw=nil
local view=Rules.view(raw,DAY0+100,{{kind="food_eaten",amount=4}})
assert(raw==nil and view.tutorialDone==false and view.tutorial.id=="T1" and view.tutorial.progress==4 and view.tutorial.goal==10 and view.tutorial.done==false)
assert(#view.short==3 and #view.daily==3 and view.shortResetsIn==1700 and view.dailyResetsIn==86300 and view.crystalsLeftToday==C.WindowCrystalCapPerDay and #view.carry==0)
local allDone=newState(DAY0+100)
for _,id in Rules.TutorialOrder do local e=C.ById[id] allDone.tutorial.claimed[id]=true end
assert(Rules.view(allDone,DAY0+100).tutorialDone==true and Rules.view(allDone,DAY0+100).tutorial==nil)
-- OB1: which runs count (pure): >= RunMinSeconds AND >= RunMinFood, nothing else
assert(C.RunMinSeconds==30 and C.RunMinFood==1)
assert(Rules.runCounts(30,1)==true and Rules.runCounts(300,50)==true)
assert(Rules.runCounts(29.9,1)==false and Rules.runCounts(5,3)==false and Rules.runCounts(0,0)==false and Rules.runCounts(300,0)==false)
for _,junk in {"x",{},0/0,-1} do assert(Rules.runCounts(junk,1)==false and Rules.runCounts(60,junk)==false,"junk never counts") end
assert(Rules.runCounts(nil,1)==false and Rules.runCounts(60,nil)==false)
-- OB3: the one catalogue row whose copy says "hatch" tells the player a failed Cracked egg counts; short, docs/72 length
for _,entry in C.Catalogue do
 if entry.note~=nil then assert(entry.id=="T3" and entry.note=="Cracked eggs count too" and #entry.note<=30,"only T3 carries a note") end
end
assert(C.ById.T3.note~=nil,"T3 says hatch, so it carries the Cracked note")
assert(Rules.view(newState(DAY0+100),DAY0+100).tutorial.id=="T1")
do local s=newState(DAY0+100) for _,id in {"T1","T2"} do s.tutorial.claimed[id]=true end
 local v=Rules.view(s,DAY0+100) assert(v.tutorial.id=="T3" and v.tutorial.note=="Cracked eggs count too","the view carries the note") end
-- OB2: a "seen" report is accepted only for a catalogue row that declares it (T9 "fusion_menu"); the rest is the server's
assert(Rules.seenEntry("fusion_menu")==C.ById.T9 and C.ById.T9.event=="fusion_menu_opened")
for _,forged in {"T9","D5","fusion","index","",5,{},false} do assert(Rules.seenEntry(forged)==nil,"forged seen id") end
local seenCount=0 for _,entry in C.Catalogue do if entry.seen~=nil then seenCount+=1 assert(entry.group=="tutorial","seen objectives are tutorial steps") end end
assert(seenCount==1,"exactly one seen objective today")
do
 local s=newState(DAY0+100)
 local done,status=Rules.seenDone(s,"fusion_menu",DAY0+100,{})
 assert(done==false and status=="ok","fresh: not seen yet")
 assert(select(2,Rules.seenDone(s,"index",DAY0+100,{}))=="unknown_objective")
 assert((Rules.seenDone(s,"fusion_menu",DAY0+100,{{kind="fusion_menu_opened",amount=1,id=Rules.seenEventId("fusion_menu")}})),"a pending report counts as seen")
 assert(Rules.seenEventId("fusion_menu")=="seen:fusion_menu")
 Rules.applyEvents(s,{{kind="fusion_menu_opened",amount=1,id=Rules.seenEventId("fusion_menu")}},DAY0+100)
 assert(s.tutorial.progress.T9==1 and (Rules.seenDone(s,"fusion_menu",DAY0+100,{})),"stored progress = seen")
 Rules.applyEvents(s,{{kind="fusion_menu_opened",amount=1,id=Rules.seenEventId("fusion_menu")}},DAY0+100)
 assert(s.tutorial.progress.T9==1,"the same event id counts once")
 local c=newState(DAY0+100) c.tutorial.claimed.T9=true
 assert((Rules.seenDone(c,"fusion_menu",DAY0+100,{})),"a claimed T9 is seen")
 assert(select(2,Rules.seenDone({v=C.SchemaVersion+1},"fusion_menu",DAY0+100,{}))=="newer_version")
end
print("Migration passed: nil/corrupt -> empty, newer version untouched, round-trip identity, sanitising, idempotent batches, atomic denied claim, read-only view")
'''

SERVICE = r'''
------------------------------------------------------------------ ObjectiveService (rate-limited remote, no-op record)
do
 local servicesFake={}
 local instances={}
 local function newInstance(class)
  local inst={ClassName=class,children={}}
  function inst:IsA(name) return name==self.ClassName end
  function inst:Destroy() end
  function inst:FindFirstChild(name) return self.children[name] end
  return inst
 end
 local rsFake=newInstance("Folder")
 rsFake.Shared={Config="GameConfig",ObjectiveConfig="ObjectiveConfig",ObjectiveRules="ObjectiveRules"}
 servicesFake.ReplicatedStorage=rsFake
 local players={}
 servicesFake.Players={GetPlayers=function() return players end,PlayerRemoving={Connect=function() end}}
 local touched=false
 local gameFake={GetService=function(_,name) return servicesFake[name] end}
 local Instance={new=function(class)
  touched=true
  local inst=newInstance(class)
  return setmetatable(inst,{__newindex=function(t,k,v)
   rawset(t,k,v)
   if k=="Parent" and v and v.children then v.children[rawget(t,"Name") or "?"]=t end
  end})
 end}
 local svcConfig={ObjectivesEnabled=false}
 local script={Parent={}}
 local require=function(id) if id=="GameConfig" then return svcConfig elseif id=="ObjectiveConfig" then return ObjectiveConfig elseif id=="ObjectiveRules" then return Rules end error("unexpected "..tostring(id)) end
 local game=gameFake
 local task={spawn=function() end,wait=function() end}
 local warn=function() end
 local Service=@@OBJ_SERVICE@@
 local player={}
 -- flag off: nothing exists, nothing runs
 assert(Service.start({})==nil and touched==false,"flag off: start() returns at once and creates no remote")
 assert(Service.record(player,"run_end")==false)
 Service.noteMenuUse(player,"fusion_menu") -- BD-616: flag off = no-op, so it cannot pre-open the menu for later (checked by the "not_opened" assert below)
 local off=Service.handle(player,{action="view"}) assert(off.ok==false and off.reason=="disabled")
 -- flag on, with a fake repository
 svcConfig.ObjectivesEnabled=true
 local recorded={}
 local failing=false
 local repo={
  isLoaded=function() return true end,
  objectiveView=function() return {tutorial={id="T1"}},"ok" end,
  objectiveClaim=function(_,id,token) if failing then error("boom") end return true,"claimed",{id=id,status="claimed",crystals=10,xp=0} end,
  objectiveRecord=function(_,event) table.insert(recorded,event) return true end,
  objectiveSeen=function(_,seenId) if seenId=="fusion_menu" then return true,"seen" end return false,"unknown_objective" end,
  objectiveFlush=function() return true,"nothing" end,
 }
 local remote=Service.start(repo)
 assert(remote and remote.Name=="ObjectiveAction" and type(remote.OnServerInvoke)=="function" and rsFake.children.BeDinoRemotes.children.ObjectiveAction==remote)
 local now=100
 Service.setClock(function() return now end)
 local function call(request,...) return remote.OnServerInvoke(player,request,...) end
 local viewResponse=call({action="view"}) assert(viewResponse.ok==true and viewResponse.view.tutorial.id=="T1")
 local claimResponse=call({action="claim",id="T1",token="abc"})
 assert(claimResponse.ok==true and claimResponse.status=="claimed" and claimResponse.grant.crystals==10 and claimResponse.view~=nil)
 local function reset() Service.setClock(function() return now end) end
 for _,bad in {5,"x",{},{action="nope"},{action="claim"},{action="claim",id=5,token="t"},{action="claim",id="T1"},{action="claim",id="",token="t"},
   {action="claim",id=string.rep("x",9),token="t"},{action="claim",id="T1",token=string.rep("x",81)},{action="claim",id="T1",token="t",amount=999},
   {action="view",crystals=5},{action="claim",id="T1",token="t",reward=100}} do
  reset()
  local response=Service.handle(player,bad) assert(response.ok==false and response.reason=="bad_request",tostring(bad))
 end
 reset()
 assert(Service.handle(player,{action="view"},"extra").reason=="bad_request","extra arguments are rejected")
 -- OB2: the "seen" request has its own strict shape: {action, id} and nothing else
 reset()
 -- BD-616 (T9): the client's statement alone earns nothing; the server must have answered that menu's own request first
 local seenCalls=0
 local realSeen=repo.objectiveSeen
 repo.objectiveSeen=function(...) seenCalls+=1 return realSeen(...) end
 local early=Service.handle(player,{action="seen",id="fusion_menu"}) assert(early.ok==false and early.reason=="not_opened" and seenCalls==0,"BD-616: a seen report before the menu's own request is refused ("..tostring(early.reason)..")")
 Service.noteMenuUse(player,"fusion_menu")
 local stranger={} reset()
 local strangerSeen=Service.handle(stranger,{action="seen",id="fusion_menu"}) assert(strangerSeen.ok==false and strangerSeen.reason=="not_opened" and seenCalls==0,"BD-616: another player's menu use does not count")
 reset()
 local seenResponse=Service.handle(player,{action="seen",id="fusion_menu"}) assert(seenResponse.ok==true and seenResponse.status=="seen" and seenResponse.view~=nil and seenCalls==1)
 reset()
 local forgedSeen=Service.handle(player,{action="seen",id="T9"}) assert(forgedSeen.ok==false and forgedSeen.reason=="unknown_objective")
 for _,bad in {{action="seen"},{action="seen",id=5},{action="seen",id=""},{action="seen",id=string.rep("x",33)},{action="seen",id="fusion_menu",amount=1},{action="seen",id="fusion_menu",token="t"},{action="seen",id="fusion_menu",objective="T9"}} do
  reset()
  local response=Service.handle(player,bad) assert(response.ok==false and response.reason=="bad_request","seen shape: "..tostring(bad.id))
 end
 reset()
 assert(Service.handle(player,{action="seen",id="fusion_menu"},"extra").reason=="bad_request")
 -- the limiter: RequestsPerWindow per RateWindowSeconds, then it opens again
 now=1000 Service.setClock(function() return now end)
 local okCount=0 local limited=0
 for _=1,C.RequestsPerWindow+5 do local response=call({action="view"}) if response.ok then okCount+=1 elseif response.reason=="rate_limited" then limited+=1 end end
 assert(okCount==C.RequestsPerWindow and limited==5,"rate limit "..okCount.."/"..limited)
 now+=C.RateWindowSeconds assert(call({action="view"}).ok==true,"window passed: allowed again")
 -- errors never reach the client as a throw
 now+=C.RateWindowSeconds failing=true
 local errored=call({action="claim",id="T1",token="boom"}) assert(errored.ok==false and errored.reason=="save_failed")
 failing=false
 -- record API forwards only while on
 assert(Service.record(player,"run_end",1,"run:1") and recorded[1].kind=="run_end" and recorded[1].id=="run:1")
 svcConfig.ObjectivesEnabled=false
 assert(Service.record(player,"run_end")==false and #recorded==1,"flag turned off at runtime: record is a no-op")
 assert(call({action="view"}).reason=="disabled")
end
print("Service passed: flag-off start is inert, strict request shapes, rate limit, no throw, record is a no-op while off")
'''

REPO = r'''
------------------------------------------------------------------ ProfileRepository (real transactions, mocked DataStore)
local function user(id)
 local u={Parent=true,UserId=id,attrs={}}
 function u:SetAttribute(k,v) self.attrs[k]=v end
 function u:GetAttribute(k) return self.attrs[k] end
 return u
end
local function key(u) return "u:"..tostring(u.UserId) end
local DAY0=20833*86400
fakeNow=DAY0+100
local C=ObjectiveConfigM
local function crystals(u) return data[key(u)].progression.crystals end

-- A. flag OFF: identity. No read, no write, no store traffic, whatever the profile holds.
assert(GameConfig.ObjectivesEnabled==false,"the committed Config has the flag off")
local a=user(901) assert(Repository.load(a))
local snapshotA=copy(data[key(a)])
local transformsA=transforms
assert(Repository.objectiveRecord(a,{kind="run_end"})==false)
local offView,offStatus=Repository.objectiveView(a) assert(offView==nil and offStatus=="disabled")
local offFlush,offFlushStatus=Repository.objectiveFlush(a) assert(offFlush==false and offFlushStatus=="disabled")
local offClaim,offClaimStatus=Repository.objectiveClaim(a,"T1","t1") assert(offClaim==false and offClaimStatus=="disabled")
assert(transforms==transformsA,"flag off: not one DataStore request")
assert(same(snapshotA,data[key(a)]) and data[key(a)].objectives==nil,"flag off: the profile is byte-identical and has no objectives field")
Repository.release(a)
assert(data[key(a)].objectives==nil,"flag off: release adds nothing")
-- a profile that ALREADY carries an objectives field (from a flag-on session or a newer build) is left alone while off
data[key(a)].objectives={v=1,tutorial={progress={T1=4},claimed={}},keep="exactly"}
local keepCopy=copy(data[key(a)].objectives)
assert(Repository.load(a))
Repository.objectiveRecord(a,{kind="food_eaten",amount=3}) Repository.objectiveFlush(a) Repository.objectiveClaim(a,"T1","off-1")
Repository.release(a)
assert(same(data[key(a)].objectives,keepCopy),"flag off: an existing objectives field is not normalised, migrated or rewritten")
print("Flag-off identity passed: no store traffic, no field created, an existing field is left byte-identical")

-- B. flag ON
GameConfig.ObjectivesEnabled=true
local p=user(902) assert(Repository.load(p))
assert(data[key(p)].objectives==nil,"load never creates the field (migration is lazy and additive)")
local profileKeys={} for k in data[key(p)] do profileKeys[k]=true end
local view=Repository.objectiveView(p)
assert(view.tutorial.id=="T1" and view.tutorial.progress==0 and #view.short==3 and #view.daily==3 and data[key(p)].objectives==nil,"view is read-only")
assert(Repository.objectiveRecord(p,{kind="food_eaten",amount=10}))
view=Repository.objectiveView(p) assert(view.tutorial.progress==10 and view.tutorial.done and data[key(p)].objectives==nil,"the view includes unflushed progress; still no write")
local wallet0=crystals(p)
local ok,status,outcome=Repository.objectiveClaim(p,"T1","tok-1")
assert(ok and status=="claimed" and outcome.crystals==10 and crystals(p)==wallet0+10,"claim grants exactly the catalogue crystals")
local stored=data[key(p)].objectives
assert(stored.v==1 and stored.tutorial.claimed.T1==true and stored.tutorial.progress.T1==10 and stored.short and stored.daily)
local ops=data[key(p)].recentOperations assert(ops[#ops].id=="objective:tok-1" and ops[#ops].kind=="objective" and ops[#ops].outcome.id=="T1")
-- idempotent token, fresh token, conflicting token
local dOk,dStatus,dOut=Repository.objectiveClaim(p,"T1","tok-1") assert(dOk and dStatus=="duplicate" and dOut.id=="T1" and crystals(p)==wallet0+10,"same token twice grants once")
local rOk,rStatus=Repository.objectiveClaim(p,"T1","tok-2") assert(not rOk and rStatus=="already_claimed" and crystals(p)==wallet0+10)
local cOk,cStatus=Repository.objectiveClaim(p,"T2","tok-1") assert(not cOk and cStatus=="token_conflict" and crystals(p)==wallet0+10)
for _,case in {{"T1",""},{"T1",string.rep("x",81)},{"T1",5},{"T1",nil}} do
 local bok,bstatus=Repository.objectiveClaim(p,case[1],case[2]) assert(not bok and bstatus=="invalid_token")
end
for _,id in {"nope",5,false,"S9"} do local bok,bstatus=Repository.objectiveClaim(p,id,"tok-x") assert(not bok and bstatus=="unknown_objective") end
local nd,ndStatus=Repository.objectiveClaim(p,"T2","tok-3") assert(not nd and ndStatus=="not_done" and crystals(p)==wallet0+10)

-- reconnect: unflushed progress rides the lease release; claimed flags and counters persist
assert(Repository.objectiveRecord(p,{kind="run_end"}))
assert(data[key(p)].objectives.tutorial.progress.T2==nil,"queued in memory, not yet written")
Repository.release(p)
assert(data[key(p)].objectives.tutorial.progress.T2==1,"the lease release committed the queued progress")
assert(Repository.load(p))
view=Repository.objectiveView(p) assert(view.tutorial.id=="T2" and view.tutorial.done==true,"T1 stays claimed after a rejoin")
local again,againStatus=Repository.objectiveClaim(p,"T1","tok-after-rejoin") assert(not again and againStatus=="already_claimed")
ok,status,outcome=Repository.objectiveClaim(p,"T2","tok-4") assert(ok and status=="claimed" and outcome.crystals==20 and crystals(p)==wallet0+30)

-- flush: batched, idempotent under a lost acknowledgement, "nothing" when empty
assert(select(2,Repository.objectiveFlush(p))=="nothing")
assert(Repository.objectiveRecord(p,{kind="egg_hatched",amount=3}))
failMode="ack_lost"
local fOk,fStatus=Repository.objectiveFlush(p)
assert(fOk and fStatus=="flushed" and data[key(p)].objectives.tutorial.progress.T3==3,"a lost acknowledgement must not double count id-less events: "..tostring(data[key(p)].objectives.tutorial.progress.T3))
-- lost acknowledgement on a CLAIM: granted once, reported as the claim it was
assert(Repository.objectiveRecord(p,{kind="potion_bought"}))
failMode="ack_lost"
local before3=crystals(p)
ok,status,outcome=Repository.objectiveClaim(p,"T3","tok-ack")
assert(ok and status=="claimed" and crystals(p)==before3+15,"lost ack on claim: one grant")
assert(data[key(p)].objectives.tutorial.progress.T6==1,"events carried by a claim whose ack was lost count once")
ok,status=Repository.objectiveClaim(p,"T3","tok-ack") assert(ok and status=="duplicate" and crystals(p)==before3+15)
-- failed saves keep the queue
assert(Repository.objectiveRecord(p,{kind="leap_used"}))
failMode="all"
fOk,fStatus=Repository.objectiveFlush(p) assert(fOk==false and fStatus=="save_failed")
failMode=nil p.attrs.ProfileState="Loaded"
fOk,fStatus=Repository.objectiveFlush(p) assert(fOk and fStatus=="flushed" and data[key(p)].objectives.tutorial.progress.T5==1,"the batch survived the outage")

-- BD-625: the lease renew commits the queue inside its OWN write (no flush request, no timer)
local rn=user(908) assert(Repository.load(rn))
assert(select(2,Repository.objectiveFlush(rn))=="nothing")
local rnObjectivesBefore=copy(data[key(rn)].objectives)
local t0=transforms
assert(Repository.renew(rn),"bd625 step 2")
assert(transforms==t0+1,"an empty queue renews with exactly the one lease write")
assert(same(data[key(rn)].objectives,rnObjectivesBefore),"an empty queue never touches the objectives field")
assert(Repository.objectiveRecord(rn,{kind="food_eaten",amount=1}) and Repository.objectiveRecord(rn,{kind="food_eaten",amount=2}),"bd625 step 5")
local function rnT1() local o=data[key(rn)].objectives return o and o.tutorial.progress.T1 or 0 end
local rn0=rnT1()
t0=transforms
local revisionBefore=data[key(rn)].revision
assert(Repository.renew(rn),"bd625 step 6")
assert(transforms==t0+1,"the queue rides the renew write: one UpdateAsync, no extra request")
assert(data[key(rn)].revision==revisionBefore+1,"one revision for lease and progress together")
assert(rnT1()==rn0+3,"the renew committed the queued food progress")
assert(select(2,Repository.objectiveFlush(rn))=="nothing" and rn.attrs.ProfileState=="Loaded","the queue is empty after the renew")
-- lost acknowledgement on the renew: the retry sees the same batch id, so id-less events count once
assert(Repository.objectiveRecord(rn,{kind="food_eaten",amount=2}),"bd625 step 11")
failMode="ack_lost"
assert(Repository.renew(rn),"bd625 step 12")
assert(rnT1()==rn0+5,"a lost renew acknowledgement must not double count: "..tostring(rnT1()),"bd625 step 13")
-- outage: the renew fails, the batch stays queued, the next renew (or the release) commits it
assert(Repository.objectiveRecord(rn,{kind="food_eaten",amount=4}),"bd625 step 14")
failMode="all"
assert(Repository.renew(rn)==false and rn.attrs.ProfileState=="SaveFailed")
failMode=nil
assert(rnT1()==rn0+5,"nothing committed during the outage")
assert(Repository.renew(rn) and rn.attrs.ProfileState=="Loaded")
assert(rnT1()==rn0+9,"the outage batch committed with the next renew, once")
-- progress queued after the last renew rides the lease release (leave, shutdown)
assert(Repository.objectiveRecord(rn,{kind="food_eaten",amount=6}),"bd625 step 20")
failMode="all"
assert(Repository.renew(rn)==false,"bd625 step 21")
failMode=nil
Repository.release(rn)
assert(rnT1()==rn0+15,"a failed renew's batch survives to the lease release")
assert(data[key(rn)].session==nil,"released")
-- a newer build's field: the renew still renews the lease, never reads, writes or reorders the field
local rnv=user(909) assert(Repository.load(rnv)) Repository.release(rnv)
data[key(rnv)].objectives={v=2,future={"data"},tutorial={claimed={T1=true}}}
assert(Repository.load(rnv),"bd625 step 24")
local rnvCopy=copy(data[key(rnv)].objectives)
assert(Repository.objectiveRecord(rnv,{kind="food_eaten",amount=10}),"bd625 step 25")
local rnvRevision=data[key(rnv)].revision
assert(Repository.renew(rnv) and data[key(rnv)].revision==rnvRevision+1,"the lease renew still goes through")
assert(same(data[key(rnv)].objectives,rnvCopy),"a newer build's objectives field is untouched by the renew")
-- lease lost during a renew: the player is flagged, the batch is not written
local rll=user(910) assert(Repository.load(rll))
assert(Repository.objectiveRecord(rll,{kind="food_eaten",amount=10}),"bd625 step 28")
local rllProgress=copy(data[key(rll)].objectives)
data[key(rll)].session.leaseId="other-server"
assert(Repository.renew(rll)==false and rll.attrs.ProfileState=="LeaseLost")
assert(same(data[key(rll)].objectives,rllProgress),"a lost lease writes nothing")

-- window rollover through the real server-clock path
local wprofile=user(903) assert(Repository.load(wprofile))
fakeNow=DAY0+100
Repository.objectiveRecord(wprofile,{kind="run_end",amount=3}) Repository.objectiveRecord(wprofile,{kind="food_eaten",amount=100})
Repository.objectiveRecord(wprofile,{kind="egg_hatched",amount=100}) Repository.objectiveRecord(wprofile,{kind="leap_used",amount=10})
Repository.objectiveRecord(wprofile,{kind="event_egg_caught",amount=2})
assert(select(2,Repository.objectiveFlush(wprofile))=="flushed")
local st=data[key(wprofile)].objectives
local finishedShort for i,id in st.short.ids do if st.short.progress[i]>=C.ById[id].goal then finishedShort=id end end
assert(finishedShort,"at least one short row finished from the broad event set")
local nextWindowRepeats=false
fakeNow=DAY0+100+1800
view=Repository.objectiveView(wprofile)
assert(view.shortResetsIn==1700,"resets-in is derived from the server clock: "..tostring(view.shortResetsIn))
local carryHas=false for _,row in view.carry do if row.id==finishedShort then carryHas=true end end
assert(carryHas,"finished-unclaimed row is offered as a carry in the next window")
assert(data[key(wprofile)].objectives.short.window==(DAY0+100)//1800,"viewing never writes the rolled window")
local walletBefore=crystals(wprofile)
ok,status,outcome=Repository.objectiveClaim(wprofile,finishedShort,"carry-1")
assert(ok and (status=="claimed" or status=="claimed_capped") and crystals(wprofile)==walletBefore+outcome.crystals and outcome.crystals==C.ById[finishedShort].reward.crystals)
assert(data[key(wprofile)].objectives.short.window==(DAY0+1900)//1800,"the claim transaction persisted the rolled window")
fakeNow=DAY0+100

-- newer-version field: never read, written or reordered, even by flush, claim and release
local nv=user(904) assert(Repository.load(nv)) Repository.release(nv)
data[key(nv)].objectives={v=2,future={"data"},tutorial={claimed={T1=true}}}
assert(Repository.load(nv))
local nvCopy=copy(data[key(nv)].objectives)
local nvWallet=crystals(nv)
assert(Repository.objectiveRecord(nv,{kind="food_eaten",amount=10}))
local nvView,nvViewStatus=Repository.objectiveView(nv) assert(nvView==nil and nvViewStatus=="newer_version")
fOk,fStatus=Repository.objectiveFlush(nv) assert(fOk==false and fStatus=="newer_version")
ok,status=Repository.objectiveClaim(nv,"T1","nv-1") assert(not ok and status=="newer_version" and crystals(nv)==nvWallet)
Repository.objectiveRecord(nv,{kind="food_eaten"})
Repository.release(nv)
assert(same(data[key(nv)].objectives,nvCopy),"a newer build's objectives field survives untouched")

-- corrupt field: loads, reads as empty, healed by the first real mutation
local cr=user(905) assert(Repository.load(cr)) Repository.release(cr)
data[key(cr)].objectives="garbage"
assert(Repository.load(cr))
view=Repository.objectiveView(cr) assert(view and view.tutorial.id=="T1")
assert(select(2,Repository.objectiveClaim(cr,"T1","cr-1"))=="not_done" and data[key(cr)].objectives=="garbage","a denied claim does not touch it")
Repository.objectiveRecord(cr,{kind="food_eaten",amount=10}) assert(select(2,Repository.objectiveFlush(cr))=="flushed")
assert(type(data[key(cr)].objectives)=="table" and data[key(cr)].objectives.v==1)

-- wallet clamp at MaxCrystals
local cap=user(906) assert(Repository.load(cap)) Repository.release(cap)
data[key(cap)].progression.crystals=ProgressionConfig.MaxCrystals-3
assert(Repository.load(cap))
Repository.objectiveRecord(cap,{kind="food_eaten",amount=10})
ok,status,outcome=Repository.objectiveClaim(cap,"T1","cap-1") assert(ok and crystals(cap)==ProgressionConfig.MaxCrystals)

-- rate-limited writes keep the queue (the routine write budget, BD-358)
local rl=user(907) assert(Repository.load(rl))
GameConfig.WriteBudgetEnabled=true GameConfig.WriteBurst=1 GameConfig.WriteRefillPerSecond=0 GameConfig.WriteBudgetReserve=-1000 -- the shared 60 s request window already holds hundreds of earlier test requests; only the per-player bucket is under test
Repository.objectiveRecord(rl,{kind="run_end"})
assert(select(2,Repository.objectiveFlush(rl))=="flushed")
Repository.objectiveRecord(rl,{kind="food_eaten",amount=10})
local lOk,lStatus=Repository.objectiveClaim(rl,"T1","rl-1") assert(not lOk and lStatus=="rate_limited")
lOk,lStatus=Repository.objectiveFlush(rl) assert(not lOk and lStatus=="rate_limited")
GameConfig.WriteBudgetEnabled=false
lOk,lStatus=Repository.objectiveClaim(rl,"T1","rl-2") assert(lOk and lStatus=="claimed","the queued progress survived the rate limit")

-- the feature adds no other profile keys, and rewards touch only the wallet
local extra={} for k in data[key(p)] do if not profileKeys[k] then table.insert(extra,k) end end
table.sort(extra)
assert(table.concat(extra,",")=="objectives","the only new profile key is objectives, got "..table.concat(extra,","))
-- the flag off again: a profile with progress is left alone
GameConfig.ObjectivesEnabled=false
local pSnapshot=copy(data[key(p)])
Repository.release(p)
local afterOff=copy(data[key(p)])
assert(same(pSnapshot.objectives,afterOff.objectives) and same(pSnapshot.progression,afterOff.progression),"flag off again: objectives and wallet untouched")
print("Repository passed: flag-off identity, renew piggyback, lazy additive field, claim once + tokens, reconnect, lost acks, outage, rollover, newer version, corrupt field, clamp, write budget")
'''


def harness_prefix() -> str:
    """The mocked-DataStore ProfileRepository harness of tools/verify_rewards.py plus the objective modules (shared with
    tools/verify_objective_hooks.py). Tokens (@@...@@) are filled by fill()."""
    prefix = verify_rewards.HARNESS.split('local function user(id)')[0]
    # Let the real repository find the objective modules (it requires ObjectiveRules lazily) and give it a controllable clock.
    needle = 'local PrivateStateStub='
    assert prefix.count(needle) == 1
    prefix = prefix.replace(needle,
        'local ObjectiveConfigM=@@OBJ_CONFIG@@\nlocal script={Parent={ObjectiveConfig="ObjectiveConfig"}}\n'
        'local require=function(_) return ObjectiveConfigM end\nlocal ObjectiveRulesM=@@OBJ_RULES@@\n' + needle)
    needle = 'PaidRandomGate="PaidRandomGate"}}'
    assert prefix.count(needle) == 1
    prefix = prefix.replace(needle, 'PaidRandomGate="PaidRandomGate",ObjectiveRules="ObjectiveRules"}}')
    needle = ' if id=="PrivateState" then return PrivateStateStub end'
    assert prefix.count(needle) == 1
    prefix = prefix.replace(needle, ' if id=="ObjectiveRules" then return ObjectiveRulesM end\n' + needle)
    needle = 'local Repository=@@REPO_MODULE@@'
    assert prefix.count(needle) == 1
    prefix = prefix.replace(needle,
        'local fakeNow=0\nlocal realOs=os\nlocal os=setmetatable({time=function() return fakeNow end},{__index=realOs})\n' + needle)
    return prefix


def fill(text: str) -> str:
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
        ('@@PAID_RANDOM_GATE@@', 'src/shared/PaidRandomGate.luau'),
        ('@@REWARD_MATH@@', 'src/server/RewardMath.luau'),
        ('@@IDENTITY_FUSION_MODULE@@', 'src/server/IdentityFusion.luau'),
        ('@@IDENTITY_MODULE@@', 'src/server/DinosaurIdentity.luau'),
        ('@@COSMETIC_OWNERSHIP@@', 'src/server/CosmeticOwnership.luau'),
        ('@@OBJ_CONFIG@@', 'src/shared/ObjectiveConfig.luau'),
        ('@@OBJ_RULES@@', 'src/shared/ObjectiveRules.luau'),
        ('@@OBJ_SERVICE@@', 'src/server/ObjectiveService.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        text = text.replace(token, module(path))
    return text


def script() -> str:
    prefix = harness_prefix()
    rows = doc_rows()
    doc_literal = '{' + ','.join('{"%s","%s",%d,%d}' % r for r in rows) + '}'
    pure = PURE.replace('@@DOC_ROWS@@', doc_literal).replace('@@DOC_COUNT@@', str(len(rows)))
    # The pure part and the service part run in their own `do` scopes of the same chunk so locals do not leak into the repository run.
    body = 'do\n' + pure + '\n' + SERVICE + '\nend\n' + REPO
    return fill(prefix + '\n' + body)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args(argv)
    errors = static_errors()
    if not doc_rows():
        errors.append('docs/66 catalogue table not found')
    for error in errors:
        print('FAIL:', error)
    if errors:
        return 1
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'objectives.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        print(result.stderr, end='')
        if result.returncode == 0 and 'Repository passed' in result.stdout:
            print('Objectives verification passed (BD-072/BD-073).')
            return 0
        return result.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())
