"""BD-288 / BD-292 offline check of the Cave hub client rules (docs/104 s7, s8, s15.1).

Runs the real HubTravelClientRules, CaveHubLayout and SettingsModel in Luau: button -> station mapping against the layout
rail keys, flag-off identity (every input answers "open"), in-run dimming (DINOS/EGGS/FUSION/SHOP only, "At home"),
Settings never travels, the teleportShops toggle, refusal copy, fade timing and the Back-to-the-middle chip rule. Static
checks cover the wiring (Bootstrap hooks are bare statements, no new top-level local; the client module is a no-op while
Config.CaveHub is false). Not Studio evidence: the live fade, remote round trip and phone layout are BD-293.
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text() + '\nend)()'

LUAU = r'''
local R=HubTravelClientRules
local L=CaveHubLayout
-- ---- button -> station: every mapped station exists and its rail key is the button's destination
local dests={"collection","eggs","fusion","auras","potions","settings"}
for dest,station in R.Stations do
 assert(L.get().byId[station],"station exists: "..station)
 assert(L.get().byId[station].rail==dest,"rail key matches for "..dest)
end
assert(R.stationFor("collection")=="index" and R.stationFor("eggs")=="nests" and R.stationFor("fusion")=="fusion")
assert(R.stationFor("auras")=="style" and R.stationFor("potions")=="potions")
assert(R.stationFor("settings")==nil and R.stationFor("nope")==nil and R.stationFor(5)==nil and R.stationFor(nil)==nil)
assert(L.get().byId[R.HeartStation],"heart exists")

local function decide(over)
 local i={caveHub=true,destination="eggs",runState="Sanctuary",teleportShops=true,remote=true,busy=false}
 for k,v in over or {} do i[k]=v end
 return R.decide(i)
end
-- ---- flag off: whatever the input, plain open (behaviour unchanged), nothing dimmed, no chip
for _,d in dests do for _,rs in {"Sanctuary","Active","Ending","Settled","",5} do for _,ts in {true,false} do for _,rem in {true,false} do
 local r=decide({caveHub=false,destination=d,runState=rs,teleportShops=ts,remote=rem,busy=true})
 assert(r.kind=="open" and r.station==nil and r.toast==nil,"flag off opens: "..d)
 assert(not R.dimmed(d,false,rs),"flag off never dims")
end end end end
assert(R.decide(nil).kind=="open" and R.decide("x").kind=="open" and R.decide({}).kind=="open")
assert(not R.chipVisible(false,"Sanctuary","nests",false) and not R.chipVisible(nil,"Sanctuary","nests",false))

-- ---- at home with teleport on: the five shop buttons travel, Settings is a plain open
for dest,station in R.Stations do
 local r=decide({destination=dest})
 assert(r.kind=="travel" and r.station==station,"travel "..dest)
end
assert(decide({destination="settings"}).kind=="open","settings never teleports")
-- teleportShops off or the remote missing: just open the menu
for dest in R.Stations do
 local g=decide({destination=dest,teleportShops=false})
 assert(g.kind=="guide" and g.station==R.Stations[dest],"toggle off walks there (BD-289) "..dest)
 assert(decide({destination=dest,remote=false}).kind=="open","no remote opens "..dest)
end
-- loading (no RunState yet) counts as home, not a run
assert(decide({runState=NIL}).kind=="travel" and decide({runState=""}).kind=="travel")
-- a trip in progress swallows taps quietly
local b=decide({busy=true}) assert(b.kind=="blocked" and b.toast==nil)

-- ---- in a run: four dimmed with "At home", POTIONS and SETTINGS as today
for _,rs in {"Active","Ending","Settled"} do
 for _,d in {"collection","eggs","fusion","auras"} do
  local r=decide({destination=d,runState=rs})
  assert(r.kind=="blocked" and r.toast=="At home","blocked in run: "..d.." "..rs)
  assert(R.dimmed(d,true,rs),"dimmed "..d)
 end
 for _,d in {"potions","settings"} do
  assert(decide({destination=d,runState=rs}).kind=="open","usable in run: "..d)
  assert(not R.dimmed(d,true,rs),"not dimmed "..d)
 end
 for _,d in dests do assert(not R.dimmed(d,true,"Sanctuary"),"nothing dimmed at home") end
end
assert(R.HomeHint=="At home" and R.MinTarget==44)

-- ---- refusal copy: calm, short, never raw codes
for _,reason in {"rate_limited","busy","not_home","outside","no_dino","dead","not_loaded","flag_off","unknown","settings","bad_request","error",5,NIL} do
 local text=R.refusal(reason)
 assert(typeof(text)=="string" and #text>0 and #text<=26,"short copy for "..tostring(reason))
 assert(not text:find("_") and not text:lower():find("error") and not text:find("!"),"nothing scary: "..text)
end
assert(R.refusal("unheard_of")==R.Generic)

-- ---- fade timing
local n,c=R.fade(false),R.fade(true)
assert(n.inSeconds==0.18 and n.outSeconds==0.18 and n.cue==true)
assert(c.inSeconds==0.08 and c.outSeconds==0.08 and c.cue==false and c.cameraTurn==false,"Reduce Motion: 0.08 s dissolve, no cue, no camera turn")
assert(R.fade(nil).cue==true and R.fade("yes").cue==true,"only calm == true quiets it")

-- ---- ack reading
local ok,why=R.readAck({ok=true,station="nests"},"nests") assert(ok and why==nil)
ok,why=R.readAck({ok=false,reason="not_home"},"nests") assert(not ok and why=="not_home")
ok,why=R.readAck({ok=true,station="potions"},"nests") assert(not ok,"ack for another station is not an arrival")
ok,why=R.readAck(nil,"nests") assert(not ok and why=="error")
ok,why=R.readAck("junk","nests") assert(not ok and why=="error")
ok,why=R.readAck({ok=false},"nests") assert(not ok and why=="error")

-- ---- Back to the middle chip: only at home, only at a non-heart station, not mid-trip
assert(R.chipVisible(true,"Sanctuary","nests",false))
assert(not R.chipVisible(true,"Sanctuary","heart",false) and not R.chipVisible(true,"Sanctuary","",false) and not R.chipVisible(true,"Sanctuary",nil,false))
assert(not R.chipVisible(true,"Active","nests",false) and not R.chipVisible(true,"Sanctuary","nests",true))

-- ---- settings: Teleport to shops defaults ON, old profiles stay ON, only an explicit false turns it off, roundtrips
local S=SettingsModel
assert(S.Defaults.teleportShops==true and S.normalize(nil).teleportShops==true and S.normalize({}).teleportShops==true)
assert(S.normalize({teleportShops="no"}).teleportShops==true and S.normalize({teleportShops=false}).teleportShops==false)
local off=S.normalize({teleportShops=false})
assert(S.toStore(off).teleportShops==false and S.fromStore(S.toStore(off)).teleportShops==false)
assert(not S.equal(off,S.normalize(nil)),"teleportShops takes part in equality")
assert(S.teleportShops()==true) S.set("teleportShops",false) assert(S.teleportShops()==false) S.set("teleportShops",true) assert(S.teleportShops()==true)
S.set("teleportShops","junk") assert(S.teleportShops()==false,"junk is not true") S.reset() assert(S.teleportShops()==true)
print("hub travel client: mapping, flag-off identity, dimming, toggle, copy, fade, chip, setting ok")
'''

def script():
    return ('local NIL=nil\n'
            + 'local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau')
            + '\nlocal SettingsModel=' + wrapped('src/shared/SettingsModel.luau')
            + '\nlocal HubTravelClientRules=' + wrapped('src/shared/HubTravelClientRules.luau') + '\n' + LUAU)

def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_hub_travel_client.luau'; path.write_text(script())
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    rules = (ROOT / 'src/shared/HubTravelClientRules.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'Vector3', 'workspace', 'os.clock', 'task.', 'require('):
        assert banned not in rules, 'HubTravelClientRules stays pure: ' + banned
    client = (ROOT / 'src/client/HubTravelClient.luau').read_text()
    attach = client[client.index('function Client.attach'):]
    assert 'Config.CaveHub ~= true' in attach.splitlines()[1], 'attach is a no-op with the flag off'
    press = client[client.index('function Client.press'):]
    assert 'Config.CaveHub ~= true then return false end' in press.splitlines()[1], 'press answers false with the flag off'
    assert 'InvokeServer' in client and 'pcall(function() return (fn :: RemoteFunction):InvokeServer' in client, 'HubTravel is called inside pcall'
    assert 'Sfx.play' in client and 'if timing.cue then' in client, 'cue only when the fade plan has one'
    assert 'settings' not in re.findall(r'Stations = table.freeze\(\{[^}]*\}\)', rules)[0], 'Settings is not a travel destination'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text()
    hook = [l for l in boot.splitlines() if l.startswith('require(script.Parent.HubTravelClient).attach(')]
    assert len(hook) == 1, 'one statement-level attach hook in client Bootstrap'
    assert 'local HubTravel' not in boot, 'no new top-level local in client Bootstrap'
    assert boot.count('HubTravelClient).press(') == 2, 'rail loop and results OPEN EGGS call press'
    menu = (ROOT / 'src/client/SettingsMenu.luau').read_text()
    assert '"Teleport to shops"' in menu and 'CaveHub' in menu, 'Controls tab toggle, shown only with the hub on'
    top = [l for l in boot.splitlines() if re.match(r'^local\s', l)]
    assert len(top) <= 195, 'client Bootstrap top-level locals stay at or below 195 (limit 200): %d' % len(top)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    print(run(args.runner))
