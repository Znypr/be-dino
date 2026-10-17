"""BD-495 (cave lights, beams, hub cosmetic lights), BD-496 (colliders) and BD-497 (weather density): offline check of the cheap phone guards (docs/146 s10, risks 3, 2 and 5 of the phone forecast).

Runs the real Shared/PhoneGuards (pure rules) in Luau, together with the real CaveHubLayout / CaveLightingRules (the 30 real cave lights) and
WeatherTextures, and checks the client wiring statically. Never Studio, never a phone.
  * cave lights (risk 3): on a phone at most 12 of the 30 real cave lights are on, always the nearest ones (with hysteresis) while a camera walks the hub from the
    gate to the Heart; a camera that jitters by a stud or two never flips a light; tablet / desktop / unknown devices get NO cap (every light, exactly as today);
    shaft beams: 4 on a phone (one per hole), 8 elsewhere; no cosmetic glow light inside the hub on a phone (own dino under Reduce Motion excepted), always elsewhere;
  * weather (risk 5): density phone 0.25, tablet 0.5, desktop 1 (and 1 for anything unknown); the textured emit rate scales by it and Reduce Motion still
    emits nothing; the fx budget report reads the same number;
  * colliders (risk 2): only a phone culls colliders, beyond the cull radius, with the same hysteresis as the props; tablet / desktop keep every collider; static
    audit that the invisible colliders have no other reader (so culling the far ones cannot change anything but physics near the player, and the ground is Terrain);
  * the numbers in src/shared/PhoneGuards.luau equal tools/qa/phone_budgets.json "guards" (one source of truth), the module is pure, and the client wiring is
    phone-gated (CavePhoneGuard / FxRig / WeatherVisuals / WorldCulling) and sits behind the existing CaveHub flag.
Not Studio evidence: nothing here ran on a phone (BD-085)."""
from pathlib import Path
import argparse, json, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]


def wrapped(path, parent=''):
    return '(function()\nlocal script={Parent={' + parent + '}}\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


LUAU = r'''
local G=PhoneGuards
local T=G.Phone
local function approx(a,b) return math.abs(a-b)<1e-9 end

-- ---- numbers (printed so Python can compare them with phone_budgets.json)
print(string.format("GUARDS %d %d %d %g",T.caveLights,T.caveBeams,T.hubCosmeticLights,T.weatherDensity))

-- ---- device names: any case, unknown = desktop
for _,d in {"phone","Phone","PHONE"} do assert(G.isPhone(d),d) end
for _,d in {"tablet","Tablet","desktop","Desktop","",nil,"watch"} do assert(not G.isPhone(d)) end

-- ---- weather density (risk 5)
assert(approx(G.weatherDensity("phone"),.25) and approx(G.weatherDensity("Phone"),.25),"phone weather density 0.25")
assert(approx(G.weatherDensity("tablet"),.5) and approx(G.weatherDensity("Tablet"),.5),"tablet keeps today's 0.5")
for _,d in {"desktop","Desktop","",nil,"watch"} do assert(G.weatherDensity(d)==1,"desktop weather density stays 1: "..tostring(d)) end
assert(G.weatherDensity("phone")<=.25,"phone density is at most a quarter (was a half)")
-- the emit rate follows the density, and Reduce Motion keeps its own, stricter rule (nothing at all)
assert(approx(WT.emitRate(1000,nil,1,G.weatherDensity("phone"),true),250),"1,000/s becomes 250/s on a phone")
assert(approx(WT.emitRate(1000,nil,1,G.weatherDensity("desktop"),true),1000),"desktop rate unchanged")
assert(approx(WT.emitRate(1000,nil,.5,G.weatherDensity("phone"),true),125),"Weather Lite halves it again")
assert(WT.emitRate(1000,nil,1,G.weatherDensity("phone"),false)==0 and WT.emitRate(1000,nil,1,G.weatherDensity("desktop"),false)==0,"Reduce Motion emits nothing, whatever the density")
local blizzardPhone=0
for _,spec in W.Rigs.blizzard do blizzardPhone+=spec.rate*(spec.life[1]+spec.life[2])/2*G.weatherDensity("phone") end
local blizzardDesktop=0
for _,spec in W.Rigs.blizzard do blizzardDesktop+=spec.rate*(spec.life[1]+spec.life[2])/2 end
assert(approx(blizzardPhone,blizzardDesktop*.25),"a blizzard on a phone is a quarter of the desktop count")
print(string.format("WEATHER blizzard live particles desktop %.0f phone %.0f (before the guard %.0f)",blizzardDesktop,blizzardPhone,blizzardDesktop*.5))

-- ---- caps: phone only
assert(G.caveLightCap("phone")==12 and G.caveLightCap("Phone")==12)
for _,d in {"tablet","Tablet","desktop","Desktop",nil,"x"} do assert(G.caveLightCap(d)==nil and G.caveBeamCap(d)==nil,"no cap off the phone: "..tostring(d)) end
assert(G.caveBeamCap("phone")==4)
assert(G.beamsPerShaft("phone",4,2)==1 and G.beamsPerShaft("phone",4,2)*4<=G.caveBeamCap("phone"),"phone: one beam per hole, 4 in total")
assert(G.beamsPerShaft("desktop",4,2)==2 and G.beamsPerShaft("tablet",4,2)==2,"desktop and tablet keep both beams of every hole")
assert(G.beamsPerShaft("phone",0,2)==2,"no shafts, nothing to cap")

-- ---- cosmetic glow lights inside the hub (risk 3)
for _,d in {"desktop","Desktop","tablet","phone"} do
    for _,reduced in {false,true} do for _,own in {false,true} do
        assert(G.cosmeticLightWanted(d,false,reduced,own),"outside the hub every device keeps its glow light: "..d)
    end end
end
for _,d in {"desktop","Desktop","tablet","Tablet"} do
    for _,reduced in {false,true} do for _,own in {false,true} do assert(G.cosmeticLightWanted(d,true,reduced,own),"inside the hub desktop / tablet keep it: "..d) end end
end
assert(not G.cosmeticLightWanted("phone",true,false,false) and not G.cosmeticLightWanted("phone",true,false,true) and not G.cosmeticLightWanted("phone",true,true,false),"phone, in the hub: no cosmetic light")
assert(G.cosmeticLightWanted("phone",true,true,true),"the own dino under Reduce Motion keeps its one soft light (13 of 16)")

-- ---- selectLights on synthetic distances
do
    local d={}
    for i=1,30 do d[i]=i*3 end
    local on=G.selectLights(12,d,nil,nil)
    local n=0 for i=1,30 do if on[i] then n+=1 assert(i<=12,"the 12 nearest are on: "..i) end end
    assert(n==12)
    local all=G.selectLights(nil,d,nil,nil) local m=0 for _ in all do m+=1 end assert(m==30,"no cap = every light on")
    local few=G.selectLights(12,{1,2,3},nil,nil) local k=0 for _ in few do k+=1 end assert(k==3,"fewer lights than the cap: all on")
    -- the cap shrinks: keep the nearest incumbents
    local was={} for i=1,30 do was[i]=i>18 end
    local on2=G.selectLights(12,d,was,1.25) local c2=0 for i=1,30 do if on2[i] then c2+=1 end end assert(c2==12)
end

-- ---- the REAL cave: 30 lights, a camera walking the hub (gate -> Heart), and jitter
local C=CaveHubLayout
local lights=Rules.get().lights
local arch=Rules.archLight()
local all={}
for _,l in lights do table.insert(all,{x=l.x,y=l.y,z=l.z}) end
if arch then table.insert(all,{x=arch.x,y=arch.y,z=arch.z}) end
assert(#all==C.MaxLights,"the real hub has "..C.MaxLights.." lights, got "..#all)
local function distsFrom(x,y,z)
    local d={}
    for i,l in all do d[i]=math.sqrt((l.x-x)^2+(l.y-y)^2+(l.z-z)^2) end
    return d
end
local function count(on) local n=0 for _ in on do n+=1 end return n end
local gate,heart=C.get().byId.gate,C.get().byId.heart
local sx,sz=gate.x,gate.z+C.CenterZ
local ex,ez=heart.x,heart.z+C.CenterZ
local eyeY=C.FloorY+8
local steps=math.max(2,math.floor(math.sqrt((ex-sx)^2+(ez-sz)^2)/10)) -- 20 studs/s, one evaluation per 0.5 s = 10 studs
local was,toggles,lastOn,maxOn,swaps={},{},{},0,0
local wasNoHyst,swapsNoHyst,lastNo={},0,{}
for s=0,steps do
    local t=s/steps
    local d=distsFrom(sx+(ex-sx)*t,eyeY,sz+(ez-sz)*t)
    local on=G.selectLights(12,d,was,T.lightMargin)
    assert(count(on)==12,"exactly 12 cave lights on a phone at step "..s)
    maxOn=math.max(maxOn,count(on))
    -- everything that is on is no farther than 1.25 x the 12th nearest (the hysteresis never keeps a really far light)
    local sorted=table.clone(d) table.sort(sorted)
    for i in on do assert(d[i]<=sorted[12]*T.lightMargin+1e-6,"a far light stays on at step "..s) end
    for i=1,#all do if (on[i]==true)~=(lastOn[i]==true) and s>0 then toggles[i]=(toggles[i] or 0)+1 swaps+=1 end lastOn[i]=on[i] end
    was=on
    local plain=G.selectLights(12,d,wasNoHyst,1)
    for i=1,#all do if (plain[i]==true)~=(lastNo[i]==true) and s>0 then swapsNoHyst+=1 end lastNo[i]=plain[i] end
    wasNoHyst=plain
end
local worst=0 for _,n in toggles do worst=math.max(worst,n) end
assert(worst<=2,"no cave light flips more than twice (on, off) on the walk, got "..worst)
assert(swaps<=swapsNoHyst,"hysteresis never flips more than the plain nearest-12 rule: "..swaps.." vs "..swapsNoHyst)
print(string.format("CAVE walk gate->Heart: %d steps, always 12 of %d lights on, %d flips (plain nearest-12: %d), worst light flips %d",steps+1,#all,swaps,swapsNoHyst,worst))
-- jitter: a camera trembling by 1 to 2 studs around many spots never flips a light once settled
local flips=0
for sp=0,steps do
    local t=sp/steps
    local bx,bz=sx+(ex-sx)*t,sz+(ez-sz)*t
    local was2=G.selectLights(12,distsFrom(bx,eyeY,bz),nil,nil)
    for j=1,40 do
        local jx,jz=bx+math.sin(j*1.7)*1.5,bz+math.cos(j*2.3)*1.5
        local on=G.selectLights(12,distsFrom(jx,eyeY,jz),was2,T.lightMargin)
        for i=1,#all do if (on[i]==true)~=(was2[i]==true) then flips+=1 end end
        was2=on
    end
end
assert(flips==0,"a jittering camera flips "..flips.." lights")
-- far from the hub (the island): still exactly 12 on, no error
local far=G.selectLights(12,distsFrom(0,50,0),nil,nil) assert(count(far)==12)
-- a teleport into the hub from far away: the 12 nearest are chosen at once
local tp=G.selectLights(12,distsFrom(ex,eyeY,ez),far,T.lightMargin) assert(count(tp)==12)
local nearest=distsFrom(ex,eyeY,ez) local sorted=table.clone(nearest) table.sort(sorted)
for i in tp do assert(nearest[i]<=sorted[12]*T.lightMargin+1e-6) end

-- ---- colliders (risk 2)
for _,d in {"desktop","Desktop","tablet","Tablet",nil,"x"} do
    assert(not G.cullColliders(d),"only the phone culls colliders: "..tostring(d))
    for _,shown in {true,false} do for _,dist in {0,100,189,191,500,5000} do
        assert(G.colliderWanted(d,shown,dist,190,1.15)==true,"colliders are always kept off the phone")
    end end
end
assert(G.cullColliders("phone") and G.cullColliders("Phone"))
assert(G.colliderWanted("Phone",true,0,190,1.15) and G.colliderWanted("Phone",true,189,190,1.15) and G.colliderWanted("Phone",false,189,190,1.15),"inside the radius: kept")
assert(not G.colliderWanted("Phone",false,191,190,1.15) and not G.colliderWanted("Phone",true,190*1.15+.01,190,1.15),"beyond the radius: culled")
assert(G.colliderWanted("Phone",true,200,190,1.15) and not G.colliderWanted("Phone",false,200,190,1.15),"hysteresis: a kept one stays to 1.15 x radius, a culled one returns at the radius")
assert(G.colliderWanted("Phone",false,0,190,1.15),"a collider next to the dino is never culled")
print("phone guards: caps, density, cosmetic lights, colliders and hysteresis ok")
'''


def script():
    cave = ('local require=function(x) return x end\n'
            'local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau') + '\n'
            'local Rules=' + wrapped('src/shared/CaveLightingRules.luau', 'CaveHubLayout=CaveHubLayout') + '\n')
    return (cave + 'local PhoneGuards=' + wrapped('src/shared/PhoneGuards.luau') + '\n'
            'local WT=' + wrapped('src/shared/WeatherTextures.luau') + '\n'
            'local W=' + wrapped('src/shared/WeatherLooks.luau') + '\n' + LUAU)


def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_phone_guards.luau'
        path.write_text(script(), encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-3000:] + out.stderr[-3000:])
        return out.stdout.strip()


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def static_checks(printed):
    guards = json.loads(read('tools/qa/phone_budgets.json'))['guards']
    m = re.search(r'^GUARDS (\d+) (\d+) (\d+) ([\d.]+)$', printed, re.M)
    assert m, 'the Luau run printed no GUARDS line'
    lights, beams, hub, density = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
    assert (lights, beams, hub, density) == (guards['caveLights']['value'], guards['caveBeams']['value'], guards['hubCosmeticLights']['value'],
                                             guards['weatherDensity']['value']), 'PhoneGuards.luau and tools/qa/phone_budgets.json "guards" disagree'
    phone = json.loads(read('tools/qa/phone_budgets.json'))['phone']
    assert lights + hub <= phone['lights']['value'], 'the guarded hub (nearest lights + cosmetic) must fit the phone light budget'
    sys.path.insert(0, str(ROOT / 'tools'))
    import fx_budget_report as fxr
    assert fxr.PHONE_WEATHER_DENSITY == density and fxr.PHONE_WEATHER_DENSITY_BEFORE == 0.5, 'fx_budget_report reads the guard density'

    pure = read('src/shared/PhoneGuards.luau')
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'require(', 'task.', 'os.clock', 'Vector3'):
        assert banned not in pure, 'PhoneGuards stays pure: ' + banned

    # cave lights and beams: client only, phone gated, behind the CaveHub flag
    guard = read('src/client/CavePhoneGuard.luau')
    assert 'if not Guards.isPhone(dev) then return end' in guard, 'off the phone CavePhoneGuard.step returns before touching anything'
    assert 'Guards.Phone.evalSeconds' in guard and 'Guards.selectLights(' in guard, 'calm interval and hysteresis rule'
    assert '.Enabled = want' in guard and 'Destroy' not in guard and ':Remove' not in guard and 'Parent =' not in guard, 'only Enabled is flipped, nothing is destroyed or moved'
    atmosphere = read('src/client/CaveAtmosphere.luau')
    step = atmosphere.split('function Cave.step(dt: number)', 1)[1]
    assert step.lstrip().startswith('if not Config.CaveHub then return end\n    PhoneGuard.step(dt)') or \
        step.lstrip().startswith('if not Config.CaveHub then return end\r\n    PhoneGuard.step(dt)'), 'the guard runs only behind the CaveHub flag'
    assert 'CaveLighting' not in read('src/client/CavePhoneGuard.luau').replace('"CaveLighting"', ''), 'the guard finds the cave folder by name only'
    server = read('src/server/CaveLighting.luau')
    assert 'Enabled' not in server.replace('IsLightingFx', ''), 'the server still builds every light and beam enabled (the guard is client side)'

    # cosmetic glow lights
    rig = read('src/client/FxRig.luau')
    assert 'Guards.cosmeticLightWanted(self.device, true, reduced,' in rig and 'if hubInside and Guards.isPhone(self.device) then' in rig and 'function Rig.setInHub' in rig, 'FxRig asks PhoneGuards for its glow lights'
    cos = read('src/client/CosmeticVisuals.client.luau')
    assert 'Rig.setInHub(Cave.inside())' in cos, 'CosmeticVisuals feeds the hub flag'

    # weather
    weather = read('src/client/WeatherVisuals.client.luau')
    assert 'local DENSITY=if phone then Guards.weatherDensity(deviceClass) else 1' in weather, 'weather density comes from PhoneGuards (phone only)'
    assert 'then .5 else 1' not in weather, 'the old fixed phone density .5 is gone'
    assert weather.index('local DENSITY=') > weather.index('local deviceClass=') and weather.index('local DENSITY=') < weather.index('rate=spec.rate*(share or 1)*DENSITY'), 'DENSITY is defined after the device class and before the emitters use it'

    # colliders
    cull = read('src/client/WorldCulling.client.luau')
    assert 'PhoneGuards.cullColliders(class)' in cull and 'PhoneGuards.colliderWanted(class,' in cull, 'WorldCulling asks PhoneGuards'
    assert cull.count('c.part.Parent = if want then c.folder else nil') == 1, 'colliders are re-parented in exactly one place'
    assert cull.split('if cullColliders then', 2)[1].count('c.part.Parent') == 1, 'and only inside the phone-gated block'
    assert 'if cullColliders and not known[item] and item:IsA("BasePart") then' in cull, 'colliders are only collected on the phone class'
    # the only readers of *Collider parts by name are these; a new one must be reviewed before the far ones may be culled on a phone
    readers = set()
    for path in sorted((ROOT / 'src').rglob('*.luau')):
        text = path.read_text(encoding='utf-8')
        if re.search(r'-\s*8\s*\)\s*==\s*"Collider"|(?:find|match|endsWith|EndsWith|FindFirstChild|FindFirstDescendant)\([^)]*(?<!Dino)Collider(?!Weld)', text):
            readers.add(path.relative_to(ROOT).as_posix())
    allowed = {'src/client/WorldCulling.client.luau', 'src/client/CameraOcclusion.client.luau'}
    assert readers <= allowed, 'a new reader of the invisible *Collider parts appeared (review phone collider culling, docs/146 s10): ' + str(sorted(readers - allowed))
    arena = read('src/server/Arena.luau')
    assert "p.Anchored, p.CanCollide, p.CanTouch, p.CanQuery = true, solid, false, solid" in arena, 'prop colliders are anchored, solid, not touch-triggers'
    # the ground the dino stands on is Terrain: the island and the arena floor are terrain, the run-start check (WorldReady) rays only Terrain
    ready = read('src/client/WorldReady.client.luau')
    assert 'FilterDescendantsInstances = {workspace.Terrain}' in ready, 'run start waits for Terrain, not for colliders'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    printed = run(args.runner)
    print(printed)
    static_checks(printed)
    print('phone guards verified (offline; no phone, no Studio)')
