"""BD-480 offline check of the OWNER rule 2026-10-16: every dinosaur is exactly 1x in the cave hub, whatever its BIG trait,
potions or growth (docs/104 s2.4, docs/115). Runs the REAL HubScaleRules, SpawnGeometry, CaveHubLayout and src/server/Dinosaur.luau
in Luau against a mocked character (attributes + root position; DinosaurVisual.render is a recorder that writes VisualScale
exactly like the real one). Cases: BIG dino in the hub = 1; potion-boosted / high-growth dino in the hub = 1; the island size is
restored when it goes back; island behaviour is unchanged (every score x BIG, flag on and off); the legacy hub with the flag off
keeps its old size. Static checks: every VisualScale writer / render caller is known, the run-state and gate hooks exist, potions
(GrowthMultiplier) are never touched by the hub code. Not Studio evidence: see docs/07-kanban.md BD-480.
"""
from pathlib import Path
import argparse, re, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
def wrapped(path): return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'

LUAU = r'''
local function near(a,b,e) return math.abs(a-b)<=(e or 1e-9) end
local H=HubScaleRules
local function old(score,big) return math.min(4,math.sqrt(1+math.max(0,score)/50))*(if big then 1.2 else 1) end -- the pre-BD-480 formula

-- ---- pure rules
assert(H.HubScale==1 and H.MaxGrowthScale==4)
assert(near(H.growthScale(0),1) and near(H.growthScale(50),math.sqrt(2)) and near(H.growthScale(1e9),4) and near(H.growthScale(-5),1))
assert(H.growthScale(0/0)==1 and H.growthScale(math.huge)==1 and H.growthScale("x")==1 and H.growthScale(nil)==1,"junk score is 1")
for _,sc in {0,1,10,50,100,1500,7500,1e6} do for _,big in {true,false} do
 assert(near(H.islandScale(sc,big,1.2),old(sc,big)),"island formula unchanged "..sc.." "..tostring(big))
 assert(H.scale({caveHub=true,inHub=true,score=sc,big=big,bigMultiplier=1.2})==1,"hub is 1 at "..sc.." "..tostring(big))
 assert(near(H.scale({caveHub=true,inHub=false,score=sc,big=big,bigMultiplier=1.2}),old(sc,big)),"island "..sc)
 assert(near(H.scale({caveHub=false,inHub=true,score=sc,big=big,bigMultiplier=1.2}),old(sc,big)),"flag off keeps the legacy hub size")
 assert(near(H.scale({caveHub=false,inHub=false,score=sc,big=big,bigMultiplier=1.2}),old(sc,big)))
end end
assert(near(H.islandScale(0,true,1.2),1.2),"BIG is 1.2 even at score 0 (island)")
assert(H.islandScale(100,true,nil)==H.growthScale(100) and H.islandScale(100,"yes",1.2)==H.growthScale(100),"BIG needs a real true and a number")
assert(H.scale(nil)==1 and H.scale("x")==1 and H.scale({})==H.growthScale(0),"junk state")
assert(H.scale({caveHub=1,inHub=true,score=500,big=true,bigMultiplier=1.2})>1,"caveHub must be a real true")
assert(H.scale({caveHub=true,inHub="yes",score=500})>1,"inHub must be a real true")

-- ---- the REAL Dinosaur.luau on a mocked character
local function makeWorld(cfg)
 local w={calls={}}
 local names=setmetatable({},{__index=function(_,n) return n end})
 local RS=setmetatable({},{__index=function() return names end})
 local services={ReplicatedStorage=RS,RunService={},
  PhysicsService={IsCollisionGroupRegistered=function() return true end,RegisterCollisionGroup=function() end,CollisionGroupSetCollidable=function() end},
  HttpService={JSONDecode=function() return {} end}}
 local mods={PrivateState={get=function() return nil end},Config=cfg,MovementEnvelope={collider=function() return 1,1,1,0 end},
  HubScaleRules=HubScaleRules,SpawnGeometry=SpawnGeometry,CaveHubLayout=CaveHubLayout}
 mods.DinosaurVisual={render=function(character,scale,species,mutation)
  w.calls[#w.calls+1]={scale=scale,mutation=mutation}
  character:SetAttribute("VisualScale",scale)
  character:SetAttribute("MutationVisual",if mutation==true then "gold" elseif mutation then mutation else "base") -- same as the real render
 end}
 local game={GetService=function(_,n) return services[n] end}
 local script={Parent=names}
 local require=function(n) return mods[n] end
 w.Dino=(function(game,script,require)
@@DINOSAUR@@
 end)(game,script,require)
 return w
end
local function newChar(pos)
 local attrs={}
 local root={Position=pos,IsA=function(_,n) return n=="BasePart" end}
 local c={root=root,attrs=attrs}
 function c:GetAttribute(k) return attrs[k] end
 function c:SetAttribute(k,v) attrs[k]=v end
 function c:FindFirstChild(n) if n=="HumanoidRootPart" then return root end return nil end
 function c:FindFirstChildOfClass() return nil end
 return c
end
local function newPlayer(big)
 local a={EquippedSpeciesId="compy",EquippedBig=big}
 return {GetAttribute=function(_,k) return a[k] end}
end
local cfgOn=table.clone(Config) cfgOn.CaveHub=true
local cfgOff=table.clone(Config) cfgOff.CaveHub=false
local hubOn=SpawnGeometry.hubPoint(cfgOn)
local islandPos={X=0,Y=20,Z=-100}
local hubPos={X=hubOn.X,Y=hubOn.Y,Z=hubOn.Z}
assert(SpawnGeometry.inHub(cfgOn,hubPos.X,hubPos.Z) and not SpawnGeometry.inHub(cfgOn,islandPos.X,islandPos.Z),"test positions are hub / island")

-- Case 1: a BIG dino arriving in the hub (respawn / join) renders at 1 (one render call, scale 1)
do
 local w=makeWorld(cfgOn)
 local c=newChar(hubPos)
 w.Dino.refreshForPlayer(c,newPlayer(true))
 assert(c:GetAttribute("BigDinosaur")==true,"the BIG trait is kept")
 assert(c:GetAttribute("VisualScale")==1 and w.calls[#w.calls].scale==1,"BIG in the hub renders at 1, got "..tostring(c:GetAttribute("VisualScale")))
 -- same dino, same state, island: 1.2 (BIG at growth 0)
 c.root.Position=islandPos
 assert(w.Dino.syncScale(c)==false,"syncScale needs DinoAttached")
 c:SetAttribute("DinoAttached",true)
 assert(w.Dino.syncScale(c)==true and near(c:GetAttribute("VisualScale"),1.2),"BIG on the island is 1.2")
end

-- Case 2: potion-boosted dino in the hub: GrowthMultiplier 2 (Titan Tonic), a big carried GrowthScore, BIG -> still 1
do
 local w=makeWorld(cfgOn)
 local c=newChar(hubPos)
 c:SetAttribute("GrowthMultiplier",2) c:SetAttribute("GrowthScore",7500) c:SetAttribute("DinoAttached",true)
 w.Dino.refreshForPlayer(c,newPlayer(true))
 assert(c:GetAttribute("VisualScale")==1,"potion + growth + BIG in the hub is 1")
 -- growth that arrives while standing in the hub (impossible in play: addGrowth needs Active) still draws 1
 c:SetAttribute("RunState","Active")
 w.Dino.addGrowth(c,100)
 assert(c:GetAttribute("VisualScale")==1,"addGrowth in the hub keeps 1")
 assert(c:GetAttribute("GrowthMultiplier")==2,"the potion multiplier is untouched by the hub")
 assert(c:GetAttribute("GrowthScore")>7500,"growth still counts (nothing is lost in the hub)")
end

-- Case 3: leaving the hub restores the island size exactly; going back sets 1 again; the run values are never touched
do
 local w=makeWorld(cfgOn)
 local c=newChar(islandPos)
 c:SetAttribute("RunState","Active") c:SetAttribute("DinoAttached",true) c:SetAttribute("GrowthMultiplier",1.6)
 w.Dino.refreshForPlayer(c,newPlayer(true)) -- equip refresh on the island at score 0: BIG 1.2
 assert(near(c:GetAttribute("VisualScale"),1.2))
 for i=1,40 do w.Dino.addGrowth(c,20) end
 local score=c:GetAttribute("GrowthScore")
 local before=c:GetAttribute("VisualScale")
 assert(near(before,old(score,true)) and before>1.2,"island growth follows the old curve "..before)
 c.root.Position=hubPos -- moved into the hub (any path)
 assert(w.Dino.syncScale(c)==true and c:GetAttribute("VisualScale")==1,"in the hub: 1")
 assert(c:GetAttribute("GrowthScore")==score and c:GetAttribute("BigDinosaur")==true and c:GetAttribute("GrowthMultiplier")==1.6,"score, BIG and potion multiplier untouched")
 assert(w.Dino.syncScale(c)==false,"already 1: no second render")
 c.root.Position=islandPos
 assert(w.Dino.syncScale(c)==true and c:GetAttribute("VisualScale")==before,"back on the island: the prior scale is restored exactly")
 assert(w.Dino.syncScale(c)==false,"already right: no render")
end

-- Case 4: island behaviour unchanged (equip refresh + growth), flag on and off, every score x BIG; flag off in the legacy hub keeps BIG 1.2
for _,cfg in {cfgOn,cfgOff} do for _,big in {true,false} do for _,sc in {0,10,100,1500,7500,100000} do
 local w=makeWorld(cfg)
 local c=newChar(islandPos)
 c:SetAttribute("RunState","Active") c:SetAttribute("DinoAttached",true) c:SetAttribute("GrowthScore",sc)
 w.Dino.refreshForPlayer(c,newPlayer(big))
 assert(near(c:GetAttribute("VisualScale"),old(sc,big)),"island refresh "..sc.." "..tostring(big))
 c:SetAttribute("GrowthMultiplier",1)
 w.Dino.addGrowth(c,10)
 assert(near(c:GetAttribute("VisualScale"),old(c:GetAttribute("GrowthScore"),big)),"island growth "..sc.." "..tostring(big))
end end end
do
 local w=makeWorld(cfgOff)
 local legacy=newChar({X=0,Y=9,Z=cfgOff.SanctuaryCenterZ})
 w.Dino.refreshForPlayer(legacy,newPlayer(true))
 assert(near(legacy:GetAttribute("VisualScale"),1.2),"flag off: the legacy hub keeps the old BIG size")
 legacy:SetAttribute("DinoAttached",true)
 assert(w.Dino.syncScale(legacy)==false,"flag off: syncScale never changes anything")
end

-- Case 5: addGrowth on the island still refuses outside a run (unchanged)
do
 local w=makeWorld(cfgOn)
 local c=newChar(islandPos) c:SetAttribute("RunState","Sanctuary")
 w.Dino.addGrowth(c,50)
 assert(c:GetAttribute("GrowthScore")==nil,"no growth outside an Active run")
end
print("hub scale: BIG, potion, growth, restore on the island, island and flag-off unchanged ok")
'''

def script():
    dino = (ROOT / 'src/server/Dinosaur.luau').read_text(encoding='utf-8')
    return ('local mods={}\n'
            + 'local Vector3={new=function(x,y,z) return {X=x,Y=y,Z=z} end}\n'
            + 'local script={Parent={CaveHubLayout="CaveHubLayout"}}\n'
            + 'local require=function(name) return mods[name] end\n'
            + 'local CaveHubLayout=' + wrapped('src/shared/CaveHubLayout.luau') + '\nmods.CaveHubLayout=CaveHubLayout\n'
            + 'local SpawnGeometry=' + wrapped('src/shared/SpawnGeometry.luau') + '\nmods.SpawnGeometry=SpawnGeometry\n'
            + 'local HubScaleRules=' + wrapped('src/shared/HubScaleRules.luau') + '\nmods.HubScaleRules=HubScaleRules\n'
            + 'local Config=' + wrapped('src/shared/Config.luau') + '\n'
            + LUAU.replace('@@DINOSAUR@@', dino))

def run(runner):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_hub_scale.luau'; path.write_text(script())
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def src(path): return (ROOT / path).read_text(encoding='utf-8')

def static_checks():
    cfg = src('src/shared/Config.luau')
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false: the hub size rule does nothing by default'
    rules = src('src/shared/HubScaleRules.luau')
    for banned in ('Instance.new', 'game:GetService', 'Vector3', 'CFrame', 'workspace', 'os.clock', 'task.', 'require('):
        assert banned not in rules, 'HubScaleRules stays pure: ' + banned
    # Every place a character's VisualScale is written, and every caller of the render functions, is known. A new one fails here
    # so it has to go through Dinosaur.desiredScale (the hub rule) first.
    writers = []
    for p in sorted((ROOT / 'src').rglob('*.luau')):
        text = p.read_text(encoding='utf-8')
        if re.search(r'SetAttribute\(\s*"VisualScale"', text): writers.append(p.relative_to(ROOT).as_posix())
    assert writers == ['src/shared/DinosaurVisual.luau'], 'only DinosaurVisual.render writes VisualScale: %s' % writers
    callers = []
    for p in sorted((ROOT / 'src/server').rglob('*.luau')):
        text = p.read_text(encoding='utf-8')
        if re.search(r'\b(Dinosaur|Visual)\.render\(', text): callers.append(p.name)
    assert callers == ['Dinosaur.luau', 'NpcPredatorService.luau'], 'render callers: players via Dinosaur.luau, NPC predators (never in the hub): %s' % callers
    dino = src('src/server/Dinosaur.luau')
    assert dino.count('Config.BigScaleMultiplier') == 1 and 'scaleForScore' not in dino, 'one place decides the size (desiredScale)'
    assert dino.count('desiredScale(character)') == 3, 'refresh, growth and sync all use desiredScale'
    assert 'GetAttributeChangedSignal("RunState")' in dino and 'Dinosaur.syncScale(character)' in dino, 'entering the island restores the size at once'
    assert dino.count('SetAttribute("GrowthMultiplier"') == 0, 'Dinosaur never writes the potion multiplier'
    gate = src('src/server/HubGateService.luau')
    assert 'Dinosaur.syncScale(character)' in gate, 'the hub tick is the safety net for the size'
    # Potions: the multiplier is computed from the profile every second wherever the player is; the hub code has no say.
    prog = src('src/server/ProgressionService.luau')
    assert 'c:SetAttribute("GrowthMultiplier",growth)' in prog, 'GrowthMultiplier is published from the profile (potion timers persist)'
    assert 'HubScale' not in prog and 'inHub' not in prog, 'potion/progression code does not depend on the hub'
    for name in ('src/shared/DinosaurVisual.luau', 'src/client/Bootstrap.client.luau', 'src/client/ContactShadow.client.luau'):
        assert 'HubScale' not in src(name), name + ': the client and the renderer just follow the replicated VisualScale'
    for name in ('src/client/Bootstrap.client.luau', 'src/client/ContactShadow.client.luau', 'src/client/CombatHud.luau', 'src/client/ResourceVisuals.client.luau'):
        assert 'GetAttribute("VisualScale")' in src(name), name + ' follows VisualScale (camera min zoom, shadow, bars, model)'
    assert 'MovementEnvelope.collider(scale' in dino, 'the collider is re-fitted on every render (HubDinos group included)'

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    print(run(args.runner))
