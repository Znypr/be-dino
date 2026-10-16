"""BD-287 offline check of the Cave hub travel rules (docs/104 s7, s15.1). Runs the real CaveHubLayout and HubTravelRules in
Luau: every refusal reason, the 0.8 s rate limit, arrival-spot selection with occupied spots, flag-off identity, junk input
and exploit attempts. Static checks cover HubTravelService (remote only with the flag, moves only via FallRecovery.teleport,
Bootstrap hook is one statement). Not Studio evidence: the live remote, teleport and client fade are BD-288 / BD-293.
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local R=HubTravelRules
local NIL={} -- stands for an explicit nil in a state override
local L=CaveHubLayout
local function state(over)
 local s={caveHub=true,profileState="Loaded",runState="Sanctuary",dinoAttached=true,alive=true,inHub=true,now=100,lastAt=nil,occupied={}}
 for k,v in over or {} do if v==NIL then s[k]=nil else s[k]=v end end
 return s
end
local function expect(request,over,reason,label)
 local ok,why=R.validate(request,state(over))
 assert(ok==(reason==nil) and why==reason,label..": expected "..tostring(reason).." got "..tostring(why))
end
local req={station="nests"}

-- ---- the happy path and every refusal reason
expect(req,nil,nil,"valid")
expect("potions",nil,nil,"bare string key also accepted")
for _,id in {"heart","gate","nests","potions","fusion","style","index","fame"} do expect({station=id},nil,nil,"station "..id) end
expect(req,{caveHub=false},"flag_off","flag off")
expect(req,{caveHub=NIL},"flag_off","flag missing")
expect(req,{profileState="Loading"},"not_loaded","profile loading")
expect(req,{profileState=NIL},"not_loaded","profile nil")
for _,rs in {"Active","Ending","Settled",false,NIL,5} do expect(req,{runState=rs},"not_home","runState "..tostring(rs)) end
expect(req,{dinoAttached=false},"no_dino","no dino")
expect(req,{dinoAttached=NIL},"no_dino","dino nil")
expect(req,{alive=false},"dead","dead")
expect(req,{inHub=false},"outside","outside hub")
expect({station="atlantis"},nil,"unknown","unknown station")
expect({station="settings"},nil,"settings","settings never teleports")
assert(L.get().byId.settings.rail=="settings","the settings station keeps rail == settings")
-- the "heart" is the Back-to-the-middle target and has no rail: allowed
expect({station="heart"},nil,nil,"heart allowed")

-- ---- rate limit 0.8 s
expect(req,{now=100,lastAt=99.5},"rate_limited","0.5 s after")
expect(req,{now=100,lastAt=99.21},"rate_limited","0.79 s after")
expect(req,{now=101,lastAt=100.0},nil,"just over 0.8 s after")
expect(req,{now=100,lastAt=50},nil,"long after")
local session={}
local a1,t1=R.process(session,req,state({now=10}))
assert(a1.ok and a1.station=="nests" and t1,"first request ok")
local a2,t2=R.process(session,req,state({now=10.3}))
assert(not a2.ok and a2.reason=="rate_limited" and t2==nil,"0.3 s later refused")
local a3=R.process(session,req,state({now=10.7}))
assert(a3.reason=="rate_limited","still 0.7 s after the first (refused tries do not reset the clock)")
local a4,t4=R.process(session,req,state({now=10.875}))
assert(a4.ok and t4,"0.85 s after the last accepted try is allowed")
-- spamming: 100 requests 0.05 s apart never get through twice per 0.8 s
local spam,accepted,lastAcc={},0,-1e9
for i=0,199 do
 local ack=R.process(spam,req,state({now=200+i*0.05}))
 if ack.ok then accepted+=1 assert(200+i*0.05-lastAcc>=0.8-1e-9,"spam accepted too early") lastAcc=200+i*0.05 end
end
assert(accepted<=13 and accepted>=12,"spam of 200 requests in 10 s accepted "..accepted)
-- a refused request that is not rate limited (e.g. in a run) still stamps, so run-time spam cannot be followed by an instant hop
local s2={}
R.process(s2,req,state({now=300,runState="Active"}))
local a5=R.process(s2,req,state({now=300.2}))
assert(a5.reason=="rate_limited","a refusal stamps the clock")

-- ---- exploit attempts: each returns an ack, never a spot
for _,case in {
 {"travel during a run",{runState="Active"},"not_home"},
 {"travel while Ending",{runState="Ending"},"not_home"},
 {"travel when Settled",{runState="Settled"},"not_home"},
 {"travel while dead",{alive=false},"dead"},
 {"travel from the island",{inHub=false},"outside"},
 {"travel before profile load",{profileState="Loading"},"not_loaded"},
 {"travel with the flag off",{caveHub=false},"flag_off"},
 {"travel without a dino",{dinoAttached=false},"no_dino"},
} do
 local ack,spot=R.process({},req,state(case[2]))
 assert(not ack.ok and ack.reason==case[3] and spot==nil,case[1])
end

-- ---- junk input: no throw, always refused with a reason
local junk={nil,false,true,0,-1,1/0,-1/0,0/0,"",string.rep("x",200),{},{station=nil},{station=5},{station={}},{station=true},{station=0/0},{station=string.rep("n",25)},{station="nests\0"},{station="NESTS"},{station=" nests"},{[1]="nests"},function() end}
for i=1,#junk+1 do
 local r=junk[i]
 local ok,ack,spot=pcall(R.process,{},r,state())
 assert(ok,"junk input must not throw: "..tostring(r))
 assert(ack.ok==false and type(ack.reason)=="string" and spot==nil,"junk refused: "..tostring(r))
end
for _,bad in {0/0,1/0,-1/0,"now",true,{}} do
 local ack=R.process({},req,state({now=bad}))
 assert(not ack.ok and ack.reason=="bad_request","non-finite or non-number clock refused: "..tostring(bad))
end
for _,st in {nil,false,5,"x"} do
 local ack=R.process({},req,st)
 assert(not ack.ok and ack.reason=="flag_off","junk state refused")
end
local ack=R.process({lastAt=0/0},req,state())
assert(ack.ok,"a NaN lastAt cannot lock a player out")
assert(R.pickSpot("atlantis",{})==nil and R.pickSpot(nil :: any,{})==nil,"pickSpot unknown station")
local sp=R.pickSpot("nests",{5,"x",{x=0/0,z=1},{x=1},false})
assert(sp and sp.index==1,"junk occupied entries are ignored")

-- ---- arrival spot selection
for _,id in {"heart","gate","nests","potions","fusion","style","index","fame"} do
 local spots=L.arrivalSpots(id)
 assert(#spots==L.ArrivalSpotsPerStation and #spots==6,"six arrival spots: "..id)
 local first=R.pickSpot(id,{})
 assert(first.index==1 and first.x==spots[1].x and first.z==spots[1].z and first.y==spots[1].y and first.yaw==spots[1].yaw,"empty station picks spot 1: "..id)
 -- occupy spots 1..k one by one; the pick is always the first free one
 local occupied={}
 for k=1,6 do
  local pick=R.pickSpot(id,occupied)
  assert(pick.index==k,id.." spot "..k.." chosen when 1.."..(k-1).." are taken, got "..pick.index)
  occupied[#occupied+1]={x=spots[k].x+1.0,z=spots[k].z-1.0} -- someone standing ~1.4 studs from the spot
 end
 -- all six taken: deterministic fallback, same answer every time, a valid spot
 local f1,f2=R.pickSpot(id,occupied),R.pickSpot(id,occupied)
 assert(f1.index==f2.index and f1.index>=1 and f1.index<=6 and f1.x==f2.x,"fallback deterministic: "..id)
 -- a player just outside the radius does not block the spot, just inside does
 local near=R.OccupiedRadius
 assert(R.pickSpot(id,{{x=spots[1].x+near-0.01,z=spots[1].z}}).index~=1,"inside the radius blocks")
 assert(R.pickSpot(id,{{x=spots[1].x+near+0.01,z=spots[1].z}}).index==1,"outside the radius does not block")
end
-- fallback: when everything is taken pick the spot farthest from the nearest person
do
 local spots=L.arrivalSpots("nests")
 local occupied={}
 for k=1,6 do occupied[k]={x=spots[k].x,z=spots[k].z} end
 occupied[4]={x=spots[4].x+2.0,z=spots[4].z} -- spot 4 is the least crowded (nearest person 2 studs away)
 assert(R.pickSpot("nests",occupied).index==4,"fallback picks the roomiest spot")
end
-- twelve players hop onto one station one after another: they spread over the six spots (then repeat deterministically)
do
 local occupied,seen={},{}
 for i=1,12 do
  local pick=R.pickSpot("fusion",occupied)
  seen[pick.index]=(seen[pick.index] or 0)+1
  occupied[#occupied+1]={x=pick.x,z=pick.z}
 end
 for i=1,6 do assert(seen[i]>=1,"spot "..i.." used when 12 players arrive") end
end
-- picking never mutates the layout or the occupied list
local before=#L.arrivalSpots("nests")
local occ={{x=1,z=2}}
R.pickSpot("nests",occ)
assert(#occ==1 and occ[1].x==1 and #L.arrivalSpots("nests")==before,"pickSpot is pure")

-- ---- flag-off identity: with Config.CaveHub false nothing is ever accepted, whatever the state
assert(Config.CaveHub==false or Config.CaveHub==true)
for _,id in {"heart","nests","potions","fusion","style","index","fame","gate","settings","nope"} do
 local ack,spot=R.process({},{station=id},state({caveHub=false}))
 assert(ack.ok==false and ack.reason=="flag_off" and spot==nil,"flag off refuses "..id)
end
-- BD-391/405: perk flag on = only owners travel; flag off = unchanged
expect(req,{fastTravelPerk=true,fastTravelOwned=false},"not_owned","perk flag on, not bought")
expect(req,{fastTravelPerk=true},"not_owned","perk flag on, owned field missing")
expect(req,{fastTravelPerk=true,fastTravelOwned=true},nil,"perk bought")
expect(req,{fastTravelPerk=false,fastTravelOwned=false},nil,"perk flag off: legacy behaviour")
expect(req,{fastTravelPerk=true,fastTravelOwned="yes"},"not_owned","junk owned value")
local pa,ps=R.process({},req,state({fastTravelPerk=true,fastTravelOwned=false}))
assert(pa.ok==false and pa.reason=="not_owned" and ps==nil,"no move without the perk")
print("hub travel: validate, rate limit, spots, junk, exploits ok")
'''

def script(config):
    return ('local Config=(function()\n' + config + '\nend)()'
            + '\nlocal CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau')
            + '\nlocal script={Parent={CaveHubLayout="CaveHubLayout"}}\nlocal require=function() return CaveHubLayout end'
            + '\nlocal HubTravelRules=' + wrapped('src/shared/HubTravelRules.luau') + '\n' + LUAU)

def run(runner, config):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_hub_travel.luau'; path.write_text(script(config))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    assert 'FastTravelPerk = false' in cfg, 'Config.FastTravelPerk ships false'
    rules = (ROOT / 'src/shared/HubTravelRules.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'Vector3', 'CFrame', 'workspace', 'os.clock', 'task.'):
        assert banned not in rules, 'HubTravelRules stays pure: ' + banned
    svc = (ROOT / 'src/server/HubTravelService.luau').read_text()
    start = svc[svc.index('function HubTravelService.start'):]
    assert start.index('Config.CaveHub ~= true then return end') < start.index('Instance.new'), 'remote is created only after the flag check'
    assert svc.count('Instance.new') == 2 and svc.count('RemoteFunction') >= 1
    assert 'FallRecovery.teleport(' in svc, 'moves only via FallRecovery.teleport'
    for banned in ('PivotTo', 'SetPrimaryPartCFrame', '.CFrame =', 'MoveTo', 'AssemblyLinearVelocity', 'DataStore'):
        assert banned not in svc, 'HubTravelService must not move or save by itself: ' + banned
    assert 'Rules.process(' in svc, 'rules decide, the service only applies'
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text()
    hooks = [l for l in boot.splitlines() if 'HubTravelService' in l]
    assert len(hooks) == 1 and hooks[0].startswith('require(script.Parent.HubTravelService).start()'), 'one statement-level Bootstrap hook'
    assert 'local HubTravel' not in boot, 'no new top-level local in Bootstrap'

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    print(run(args.runner, (ROOT / 'src/shared/Config.luau').read_text()))
