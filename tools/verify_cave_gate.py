"""BD-290 / BD-291 / BD-289 (first part) offline check of the Cave hub Island Gate, HubDinos collisions and station walk-up
(docs/104 s2.3, s8, s9). Runs the real CaveHubLayout, CaveGateRules, HubWalkUpRules, HubTravelClientRules and
HubTravelRules in Luau: zone inclusion edges, the 1.5 s dwell, cancel on leaving, exactly-once start (and the retry after a
refused start), the Reduce Motion bar steps, the HubDinos collision-group assignment table, the walk-up dwell/once logic,
six arrival spots under load (HubTravelRules.pickSpot) and flag-off identity. Static checks cover the wiring: one start
path (RunLifecycle.requestStart used by the remote and the gate), the service and clients are no-ops with the flag off,
the new client code adds no top-level local to client Bootstrap. Not Studio evidence: see docs/07-kanban.md BD-290/291.
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local G=CaveGateRules
local W=HubWalkUpRules
local L=CaveHubLayout
local function near(a,b,e) return math.abs(a-b)<=(e or 1e-6) end
local z=G.zone()
-- world point at (along, lateral) from the arch
local function at(along,lateral) return z.sx+along*z.ux-lateral*z.uz, z.sz+along*z.uz+lateral*z.ux end
local function inz(along,lateral,y) local x,zz=at(along,lateral) return G.inZone(x,zz,y) end

-- ---- the zone sits at the layout's gate and is walkable (inside the floor blob, outside the lava)
local gate=L.get().byId.gate
assert(near(z.sx,gate.signX) and near(z.sz,gate.signZ+L.CenterZ),"zone is at the gate sign")
assert(near(z.ux,0,1e-9) and near(z.uz,-1,1e-9),"outward points to the island (-z)")
for _,c in {{G.AlongMin,-G.LateralMax},{G.AlongMin,G.LateralMax},{G.AlongMax,-G.LateralMax},{G.AlongMax,G.LateralMax},{5,0}} do
 local x,zz=at(c[1],c[2])
 assert(L.insideFloor(x,zz,0),"zone corner stands on the cave floor: "..c[1]..","..c[2])
end
-- ---- zone inclusion edges (inclusive on every side, one hair outside is out)
local E=1e-6 -- float slack: the comparisons in inZone are inclusive (<=), the layout angle gives ~1e-15 of noise
assert(inz(E,0) and inz(G.AlongMax-E,0) and inz(5,G.LateralMax-E) and inz(5,-G.LateralMax+E),"edges are inside")
assert(inz(G.AlongMax-E,G.LateralMax-E) and inz(G.AlongMin+E,-G.LateralMax+E),"corners are inside")
assert(G.inZone(z.sx,z.sz),"the arch centre itself is inside")
assert(not inz(-0.01,0) and not inz(G.AlongMax+0.01,0),"just outside along")
assert(not inz(5,G.LateralMax+0.01) and not inz(5,-G.LateralMax-0.01),"just outside lateral")
assert(not G.inZone(0,L.CenterZ) and not G.inZone(60,L.CenterZ-40),"the heart and other stations are not the gate")
local x0,z0=at(5,0)
assert(G.inZone(x0,z0,L.FloorY+3) and G.inZone(x0,z0,G.zone().floorY+G.HeightMax),"standing / small jump inside")
assert(not G.inZone(x0,z0,G.zone().floorY+G.HeightMax+0.1),"a jump over the arch is outside")
assert(not G.inZone(0/0,z0) and not G.inZone(x0,math.huge) and not G.inZone(x0,z0,0/0) and not G.inZone("a",1) and not G.inZone(nil,nil),"junk is outside")

-- ---- eligibility: the same gates as RequestStartRun plus "in the cave"
local function st(over)
 local s={caveHub=true,profileState="Loaded",runState="Sanctuary",dinoAttached=true,alive=true,inHub=true}
 for k,v in over or {} do s[k]=v end
 return s
end
assert(G.eligible(st()),"eligible")
for k,v in {caveHub=false,profileState="Loading",runState="Active",dinoAttached=false,alive=false,inHub=false} do assert(not G.eligible(st({[k]=v})),"not eligible: "..k) end
assert(not G.eligible(st({runState="Ending"})) and not G.eligible(st({runState="Settled"})) and not G.eligible(nil) and not G.eligible("x"))

-- ---- dwell: 1.5 s, progress is monotone, cancel resets, exactly once
local s=G.newSession()
local p,f=G.step(s,true,true,10)
assert(p==0 and not f,"starts at 0")
p,f=G.step(s,true,true,10.75) assert(near(p,0.5) and not f,"half way at 0.75 s")
p,f=G.step(s,true,true,11.49) assert(p<1 and not f,"not yet at 1.49 s")
p,f=G.step(s,true,true,11.5) assert(p==1 and f,"fires at 1.5 s")
for i=1,50 do p,f=G.step(s,true,true,11.5+i*0.1) assert(p==1 and not f,"never fires twice while standing there") end
p,f=G.step(s,false,true,17) assert(p==0 and not f,"leaving resets")
p,f=G.step(s,true,true,17.1) assert(p==0 and not f,"re-entering starts a fresh dwell")
p,f=G.step(s,true,true,18.5) assert(p<1 and not f,"1.4 s after re-entering is not enough")
p,f=G.step(s,true,true,18.6) assert(f,"fires once more after a fresh 1.5 s")
-- cancel half way, then come back: no fire from the old dwell
s=G.newSession()
G.step(s,true,true,0) G.step(s,true,true,1.0) p,f=G.step(s,false,true,1.2) assert(p==0 and not f,"cancelled")
p,f=G.step(s,true,true,1.25) G.step(s,true,true,2.4) p,f=G.step(s,true,true,2.7) assert(not f,"old dwell did not carry over")
p,f=G.step(s,true,true,2.75) assert(f,"fires 1.5 s after the second entry")
-- stops being eligible mid-dwell (a run began elsewhere, death, profile) cancels
s=G.newSession() G.step(s,true,true,0) p,f=G.step(s,true,false,1.4) assert(p==0 and not f,"ineligible cancels")
p,f=G.step(s,true,true,1.5) assert(not f,"dwell restarted after ineligible")
-- many players do not share state; a spammed 100 Hz stream fires once per stay
s=G.newSession() local fires=0
for i=0,600 do local _,fire=G.step(s,true,true,i*0.01) if fire then fires+=1 end end
assert(fires==1,"6 s in the arch fires exactly once, got "..fires)
-- refused start (island loading) waits another full dwell and still fires once per attempt
s=G.newSession() G.step(s,true,true,0) p,f=G.step(s,true,true,1.5) assert(f)
G.retry(s,1.5)
p,f=G.step(s,true,true,2.9) assert(not f,"retry waits again")
p,f=G.step(s,true,true,3.0) assert(f,"retry fires after another 1.5 s")
-- bad clock values never fire
s=G.newSession() p,f=G.step(s,true,true,0/0) assert(p==0 and not f)

-- ---- bar fill: smooth normally, quarter steps in Reduce Motion, no numbers (a fraction only)
assert(near(G.barFraction(0.3,false),0.3) and near(G.barFraction(2,false),1) and near(G.barFraction(-1,false),0) and G.barFraction(0/0,false)==0 and G.barFraction("x",false)==0)
assert(G.barFraction(0.24,true)==0 and G.barFraction(0.25,true)==0.25 and G.barFraction(0.74,true)==0.5 and G.barFraction(1,true)==1)
local seen={}
for i=0,100 do seen[G.barFraction(i/100,true)]=true end
local n=0 for _ in seen do n+=1 end
assert(n==G.BarSteps+1,"Reduce Motion shows only whole steps")
assert(not string.find(G.BarText,"%d") and G.BarText=="Leaving...","bar words carry no digits")

-- ---- HubDinos collision group assignment table (flag off, run states, hub / island)
local table_={}
for _,hub in {true,false} do for _,rs in {"Sanctuary","Active","Ending","Settled",""} do for _,inHub in {true,false} do
 local want=if hub and rs=="Sanctuary" and inHub then "HubDinos" else nil
 assert(G.groupFor({caveHub=hub,runState=rs,inHub=inHub})==want,"group "..tostring(hub).." "..rs.." "..tostring(inHub))
end end end
assert(G.groupFor(nil)==nil and G.groupFor({})==nil and G.groupFor({caveHub=1,runState="Sanctuary",inHub=true})==nil,"junk gets no group")
assert(G.GroupName=="HubDinos")

-- ---- walk-up: stations with a menu, pads, dwell, once, leave
local ids={} for _,s2 in W.stations() do ids[#ids+1]=s2.id end
table.sort(ids)
assert(table.concat(ids,",")=="fusion,index,nests,potions,style","menu stations get prompts (not heart, gate, settings, fame): "..table.concat(ids,","))
assert(W.destination("nests")=="eggs" and W.destination("index")=="collection" and W.destination("fusion")=="fusion" and W.destination("style")=="auras" and W.destination("potions")=="potions")
assert(W.destination("settings")==nil and W.destination("gate")==nil and W.destination("heart")==nil and W.destination(5)==nil)
for _,s2 in W.stations() do
 assert(W.padAt(s2.x,L.CenterZ+s2.z)==s2.id,"pad centre "..s2.id)
 assert(W.padAt(s2.x+s2.r,L.CenterZ+s2.z)==s2.id,"pad rim inclusive "..s2.id)
 assert(W.padAt(s2.x+s2.r+0.05,L.CenterZ+s2.z)==nil,"just off the pad "..s2.id)
 assert(near(math.sqrt((s2.signX-s2.x)^2+(s2.signZ-s2.z)^2),s2.r*0.78),"sign sits on its own pad")
end
assert(W.padAt(0,L.CenterZ)==nil,"the heart opens nothing")
assert(W.padAt(0/0,1)==nil and W.padAt(nil,nil)==nil)
-- pads never overlap (so at most one station per position)
for _,a in W.stations() do for _,b in W.stations() do if a~=b then assert(math.sqrt((a.x-b.x)^2+(a.z-b.z)^2)>a.r+b.r,"pads apart") end end end

-- OWNER 2026-10-16: a station never opens by walking up: no step / dwell exists, only trigger() (a prompt press)
assert(W.step==nil and W.DwellSeconds==nil,"no dwell auto-open API remains")
assert(W.PromptKey=="G" and W.PromptKey~="E","prompt key is not LEAP [E]")
local ws=W.newState()
-- arriving by teleport: note() debounces a prompt press in the same instant
ws=W.newState() W.note(ws,"style",0)
assert(W.trigger(ws,"style",true,0.1)==false,"a press right after a teleport arrival does not double open")
-- ProximityPrompt: once, debounced, only menu stations, only when it can open
ws=W.newState()
assert(W.trigger(ws,"nests",true,10)==true,"first prompt opens")
assert(W.trigger(ws,"nests",true,10.1)==false and W.trigger(ws,"nests",true,10.4)==false,"hammering the prompt opens once")
assert(W.trigger(ws,"potions",true,10.2)==false,"debounce between any two opens")
assert(W.trigger(ws,"potions",true,10.6)==true,"another station after the gap")
assert(W.trigger(ws,"settings",true,20)==false and W.trigger(ws,"gate",true,20)==false and W.trigger(ws,5,true,20)==false,"non-menu signs never open")
assert(W.trigger(ws,"nests",false,30)==false,"cannot open while blocked")
assert(W.trigger(ws,"nests",true,40)==true,"the prompt keeps working on later visits")

-- ---- six arrival spots under load (docs/104 s9): HubTravelRules.pickSpot is the only spacing logic
local P=HubTravelRules
for _,id in {"heart","nests","potions","fusion","style","index","fame"} do
 local spots=L.arrivalSpots(id)
 assert(#spots==6,"six spots at "..id)
 local used,people={},{}
 for i=1,6 do -- six players arrive one after another, each at a free spot
  local sp=P.pickSpot(id,people)
  assert(not used[sp.index],"spot "..sp.index.." reused at "..id.." with free spots left")
  used[sp.index]=true
  people[#people+1]={x=sp.x,z=sp.z}
 end
 for i=1,#spots do for j=i+1,#spots do assert((spots[i].x-spots[j].x)^2+(spots[i].z-spots[j].z)^2>=P.OccupiedRadius^2,"spots are apart at "..id) end end
 -- twelve players: the seventh and later pick the least crowded spot, never nil, deterministic, always one of the six
 for i=7,12 do
  local sp=P.pickSpot(id,people)
  assert(sp and sp.index>=1 and sp.index<=6,"overflow still picks a spot")
  local again=P.pickSpot(id,people)
  assert(again.index==sp.index,"deterministic")
  people[#people+1]={x=sp.x,z=sp.z}
 end
end

-- ---- flag-off identity: with the flag false nothing is eligible, no group, no hub
for _,rs in {"Sanctuary","Active"} do
 for _,ih in {true,false} do
  assert(G.groupFor({caveHub=false,runState=rs,inHub=ih})==nil)
  assert(not G.eligible(st({caveHub=false,runState=rs,inHub=ih})))
 end
end
local hubOff=L.hub({CaveHub=false,SanctuaryCenterZ=1200})
assert(hubOff.enabled==false and hubOff.centerZ==1200,"layout hub unchanged with the flag off")
print("cave gate: zone, dwell, exactly-once, bar, HubDinos table, walk-up, spots ok")
'''

def script():
    return ('local mods={}\n'
            + 'local script={Parent={CaveHubLayout="CaveHubLayout",HubTravelClientRules="HubTravelClientRules"}}\n'
            + 'local require=function(name) return mods[name] end\n'
            + 'local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau') + '\nmods.CaveHubLayout=CaveHubLayout\n'
            + 'local HubTravelClientRules=' + wrapped('src/shared/HubTravelClientRules.luau') + '\nmods.HubTravelClientRules=HubTravelClientRules\n'
            + 'local CaveGateRules=' + wrapped('src/shared/CaveGateRules.luau') + '\n'
            + 'local HubWalkUpRules=' + wrapped('src/shared/HubWalkUpRules.luau') + '\n'
            + 'local HubTravelRules=' + wrapped('src/shared/HubTravelRules.luau') + '\n' + LUAU)

def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_cave_gate.luau'; path.write_text(script())
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    for name in ('CaveGateRules', 'HubWalkUpRules'):
        text = (ROOT / f'src/shared/{name}.luau').read_text()
        for banned in ('Instance.new', 'game:GetService', 'Vector3', 'CFrame', 'workspace', 'os.clock', 'task.'):
            assert banned not in text, f'{name} stays pure: {banned}'
    run_life = (ROOT / 'src/server/RunLifecycle.luau').read_text()
    assert run_life.count('function RunLifecycle.requestStart(') == 1, 'one run-start function'
    start = run_life[run_life.index('function RunLifecycle.start()'):]
    handler = start[start.index('startRemote.OnServerEvent'):start.index('local readyRemote')]
    assert 'RunLifecycle.requestStart(player)' in handler and 'RunLifecycle.begin' not in handler, 'the remote only calls requestStart'
    assert run_life.count('RunLifecycle.begin(player, character)') == 1, 'begin() is called from exactly one place'
    svc = (ROOT / 'src/server/HubGateService.luau').read_text()
    body = svc[svc.index('function HubGateService.start'):]
    assert body.index('Config.CaveHub ~= true then return end') < body.index('RegisterCollisionGroup') < body.index('Heartbeat'), 'flag check first'
    assert svc.count('RunLifecycle.requestStart(player)') == 1 and 'RunLifecycle.begin' not in svc, 'the gate starts a run only through requestStart'
    for banned in ('FallRecovery', 'PivotTo', 'SetPrimaryPartCFrame', 'MoveTo', 'CFrame', 'DataStore', 'RemoteEvent', 'RemoteFunction'):
        assert banned not in svc, 'HubGateService moves, saves and listens to nothing itself: ' + banned
    assert 'Rules.step(' in svc and 'Rules.groupFor(' in svc, 'rules decide, the service only applies'
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text()
    hooks = [l for l in boot.splitlines() if 'HubGateService' in l]
    assert len(hooks) == 1 and hooks[0].startswith('require(script.Parent.HubGateService).start()'), 'one statement-level server Bootstrap hook'
    assert 'local HubGate' not in boot, 'no new top-level local in server Bootstrap'
    for name in ('HubGateClient', 'HubWalkUpClient'):
        client = (ROOT / f'src/client/{name}.luau').read_text()
        first = client[client.index('function Client.attach'):].splitlines()[1]
        assert 'Config.CaveHub ~= true' in first, name + ' attach is a no-op with the flag off'
    assert 'FireServer' not in (ROOT / 'src/client/HubGateClient.luau').read_text(), 'the gate bar is feedback only'
    travel = (ROOT / 'src/client/HubTravelClient.luau').read_text()
    assert 'WalkUp.attach(' in travel and 'GateBar.attach(' in travel and 'walkUp.note(station)' in travel
    walk = (ROOT / 'src/client/HubWalkUpClient.luau').read_text()
    assert 'Heartbeat' not in walk and 'padAt' not in walk, 'no pad dwell: nothing opens without a prompt press'
    assert 'KeyboardKeyCode' in walk and 'Rules.PromptKey' in walk and 'GamepadKeyCode' in walk, 'prompt has its own key and gamepad key'
    assert walk.count('openStation(') == 2, 'openStation is only called from the prompt Triggered handler (one def, one call)'
    boot_c = (ROOT / 'src/client/Bootstrap.client.luau').read_text()
    assert 'HubGateClient' not in boot_c and 'HubWalkUpClient' not in boot_c, 'client Bootstrap is untouched (no new locals)'
    top = [l for l in boot_c.splitlines() if re.match(r'^local\s', l)]
    assert len(top) <= 195, 'client Bootstrap top-level locals stay at or below 195 (limit 200): %d' % len(top)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    print(run(args.runner))
