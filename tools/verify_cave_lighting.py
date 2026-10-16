"""BD-286 / BD-295 / BD-296 offline check of the Cave lighting and the lava-fall fit (docs/104 s4, s5). Runs the real
CaveHubLayout, CaveTerrainRules and CaveLightingRules in Luau (pure numbers, never Studio):
 * light budget: the light list equals the layout's, never above CaveHubLayout.MaxLights (16), every light inside the hall and
   under the ceiling, one fill per station, the gate arch light is the strongest fill; FX parts (beams + dust volumes + gate glow)
   stay tiny and the whole hub stays under the 410 part budget (lights use Attachments, no extra Parts);
 * shaft alignment: one shaft per ceiling hole, centred on it, narrower than the hole, standing in AIR from just above the floor to
   inside the open hole (checked against the terrain voxel rules), neutral colour and ~0.9 transparency;
 * lava falls: the sheet top is under the lowest ceiling along its width, the lava_pool_disc prop is smaller than the basin and is
   not walkable (BD-295);
 * cave look: inside/outside hysteresis, blend maths, ranges;
 * flag-off identity (static): Config.CaveHub stays false, CaveLighting.build is only called in Arena's cave branch, the client look
   returns before touching anything when the flag is off, CaveLightingRules is pure.
Not Studio evidence: see docs/evidence/2026-10-16-cave-lighting/ and the BD-286 kanban row.
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles
ROOT = Path(__file__).resolve().parents[1]

LUAU = r'''
local C=CaveHubLayout
local L=C.get()
local R=Rules
local T=Terrain
local FY,CZ=C.FloorY,C.CenterZ
local D=R.get()
assert(Config.CaveHub==false,"CaveHub ships off")
local function dist(ax,az,bx,bz) return math.sqrt((ax-bx)^2+(az-bz)^2) end

-- ---- lights: counts and placement
assert(#D.lights==#L.lights,"the light list is the layout's light list")
assert(#D.lights<=C.MaxLights,"<= 16 lights: "..#D.lights)
local owners={}
for _,l in D.lights do owners[l.owner]=(owners[l.owner] or 0)+1 end
assert(owners.heart==2 and owners.lava==3 and owners.crystal==2 and owners.forge==1,"heart 2, lava 3, crystal 2, forge 1")
for _,s in L.stations do if s.id~="heart" then assert(owners[s.id]==1,"one fill light at "..s.id) end end
local archBrightness,maxFill=0,0
for _,l in D.lights do
 assert(C.insideFloor(l.x,l.z,0),"light inside the floor blob: "..l.owner)
 local ceil=C.ceilingY(l.x,l.z)
 assert(l.y>C.floorHeight(l.x,l.z) and l.y<ceil-4,"light between floor and ceiling: "..l.owner)
 assert(l.range>=14 and l.range<=48 and l.brightness>0.25 and (l.arch or l.brightness<=1.0) and l.brightness<=2.4,"calm light values: "..l.owner)
 assert(l.color[1]>=190 and l.color[3]>=70,"no cold or dark light colour: "..l.owner)
 if l.arch then archBrightness=l.brightness else maxFill=math.max(maxFill,l.brightness) end
end
local shadowN=0
for _,l in D.lights do if l.shadows then shadowN+=1 end end
assert(shadowN==4,"PointLight.Shadows on exactly the 4 strongest lights: "..shadowN)
local look=R.Look
assert(look.ambient[1]<=80 and look.ambient[2]<=70 and look.brightness>=1.2 and look.brightness<=1.5,"BD-398 cave ambient warm-dim, Brightness 1.2-1.5")
assert(look.grade.brightness<=-0.08 and look.grade.brightness>=-0.12 and look.grade.contrast>=0.1,"BD-398 grade darker with contrast")
-- the blend ramps to exactly 1 inside within blendSeconds (and in half that with Reduce Motion)
local a=0
for _=1,math.ceil(look.blendSeconds*60)+1 do a=R.blend(a,1,1/60,false) end
assert(a==1,"BD-398 cave amount reaches 1 inside: "..a)
a=0
for _=1,math.ceil(look.blendSeconds*30)+1 do a=R.blend(a,1,1/60,true) end
assert(a==1,"BD-398 reduce motion ramps in half the time")
-- hall boundary: floor points at 90 percent of the floor edge count as inside; high above or far away is outside
for deg=0,350,10 do
 local th=math.rad(deg)
 local x,z=math.cos(th)*C.BaseX*0.9,CZ+math.sin(th)*C.BaseZ*0.9
 assert(R.insideAt(x,FY+3,z,false),"inside at 90 percent of the floor edge, angle "..deg)
end
assert(not R.insideAt(0,FY+120,CZ,false) and not R.insideAt(0,FY+3,CZ+400,false),"outside the hall is not inside")
assert(archBrightness>maxFill,"the gate arch light is the strongest light so the doorway reads")
local gate=L.byId.gate
local arch
for _,l in D.lights do if l.arch then arch=l end end
assert(arch and dist(arch.x,arch.z-CZ,gate.x,gate.z)<=8,"arch light stands at the gate")
assert(D.gate.z-CZ<gate.z and math.abs(D.gate.x-gate.x)<1,"gate glow sits in the gate mouth, on its centre line")
assert(R.GateGlow.alpha>=0.65,"gate glow is soft (very transparent)")
for _,l in D.lights do if l.owner=="lava" then assert(l.color[1]>=240 and l.color[3]<=90,"lava glow is orange") end end

-- ---- FX parts and budgets
assert(#D.shafts*3+1==D.fxParts and D.fxParts<=R.FxPartBudget,"FX parts tiny: "..D.fxParts)
local B=C.budgetTable()
assert(B.total.parts+D.fxParts<=C.Budget.total.parts,"hub parts incl. FX under the 410 budget: "..(B.total.parts+D.fxParts))
assert(B.lights.parts+D.fxParts<=C.Budget.lights.parts+16,"lights group stays near its 48 parts")

-- ---- shafts: aligned with the holes, narrower, standing in air, open to the sky at the top
assert(#D.shafts==4 and #L.holes==4,"four shafts, four holes")
for i,h in L.holes do
 local s=D.shafts[i]
 assert(s.station==h.station,"shaft order follows the holes")
 assert(math.abs(s.x-L.byId[h.station].x)<1e-6 and math.abs(s.z-(L.byId[h.station].z+CZ))<1e-6,"shaft centred on its hole: "..h.station)
 assert(s.outerRadius<h.radius and s.coreRadius<s.outerRadius and s.coreRadius>1,"shaft narrower than the hole: "..h.station)
 assert(s.top>=h.ceilingY and s.top<=h.ceilingY+R.Beam.topAbove+1e-6,"shaft top just above the ceiling, inside the hole")
 assert(s.bottom>=FY and s.bottom-FY<=1 and s.height>=35,"shaft stands on the floor: "..h.station)
 for y=s.bottom+0.5,s.top,2 do
  for a=0,7 do
   local x=s.x+math.cos(a*math.pi/4)*s.outerRadius
   local z=s.z+math.sin(a*math.pi/4)*s.outerRadius
   local _,occ=T.cell(x,y,z)
   assert(occ==0,string.format("shaft beam clear of rock at %s y=%.1f angle %d (occ %.2f)",h.station,y,a,occ))
  end
 end
 local _,topOcc=T.cell(s.x,s.top+4,s.z)
 assert(topOcc==0,"hole open to the sky above the shaft: "..h.station)
end
assert(R.Beam.outerAlpha>=0.9 and R.Beam.coreAlpha>=0.88 and R.Beam.coreAlpha<R.Beam.outerAlpha,"beams ~0.9 transparent, core a little brighter")
assert(R.BeamColor[1]>=240 and R.BeamColor[3]>=150 and R.BeamColor[3]<=230,"warm cream beam, neutral")
assert(R.Beam.motesPerSecond<=6,"dust motes are sparse")

-- ---- BD-295: lava falls fit under the back-wall ceiling, disc smaller than the basin and not walkable
local F,P=C.Fall,C.Pool
local lowest=math.huge
for x=F.x-F.width/2,F.x+F.width/2,2 do
 for dz=F.z-1,F.z+7,2 do
  lowest=math.min(lowest,C.ceilingY(x,dz+CZ)-T.CeilingRough)
 end
end
assert(FY+F.height<=lowest-2,"lava sheet top "..(FY+F.height).." fits under the lowest ceiling "..lowest)
assert(F.crackHeight<F.height,"crack band under the sheet top")
assert(C.Kinds.cave_lava_fall[2]==F.height,"lava fall prop height = the layout sheet height")
local disc=C.Kinds.lava_pool_disc
assert(disc[1]<=P.r*2-2 and disc[3]<=P.r*2-2,"lava disc "..disc[1].." smaller than the basin "..(P.r*2))
assert(disc.walk~=true,"lava disc is not walkable")
for _,p in L.props do if p.key=="lava_pool_disc" then assert(not p.walk and p.w<P.r*2 and p.d<P.r*2,"placed disc smaller than the basin and blocked") end end

-- ---- BD-296 wall material: Limestone is the only cave-only wall material (Sandstone / Slate / Rock colours are the island's, set globally)
local Col=Terrain.Colors
assert(Col.Limestone and Col.Limestone[1]>=140 and Col.Limestone[1]<=175 and Col.Limestone[1]-Col.Limestone[3]<=12,"BD-384: soft cool grey Limestone walls (the warm lamps carry the colour)")
for _,m in {"Sandstone","Slate","Rock","Basalt","Grass","LeafyGrass","Mud","Ground","Sand"} do assert(Col[m]==nil,"cave never recolours the island material "..m) end

-- ---- cave look
local Look=R.Look
for _,k in {"ambient","outdoorAmbient","colorShiftTop","fogColor"} do for i=1,3 do assert(Look[k][i]>=0 and Look[k][i]<=255) end end
assert(Look.ambient[1]>Look.ambient[3],"warm ambient (more red than blue)")
assert(Look.grade.saturation<=0.2 and math.abs(Look.grade.contrast)<=0.12 and math.abs(Look.grade.brightness)<=0.12 and Look.grade.saturation>=-0.2,"gentle grade")
assert(Look.fogEnd>=400 and Look.atmosphere.density<=0.3,"light haze, the hall stays readable")
assert(R.insideAt(0,FY+5,CZ,false) and R.insideAt(0,FY+5,CZ+95,false),"inside at the Heart and near the lava")
assert(R.insideAt(gate.x,FY+5,CZ+gate.z-12,true),"inside in the gate mouth")
assert(not R.insideAt(0,FY+5,300,false) and not R.insideAt(0,FY+5,300,true),"outside on the island")
local edgeX=C.BaseX*1.06
assert(not R.insideAt(edgeX,FY+5,CZ,false) and R.insideAt(edgeX,FY+5,CZ,true),"hysteresis: stays inside a little beyond the edge, does not enter there")
assert(not R.insideAt(0,FY+200,CZ,true),"not inside high above")
local v=0
for _=1,100 do local n=R.blend(v,1,0.05,false) assert(n>=v and n<=1) v=n end
assert(v==1,"blend reaches 1")
for _=1,100 do local n=R.blend(v,0,0.05,true) assert(n<=v and n>=0) v=n end
assert(v==0,"blend returns to 0")
assert(R.blend(0,1,0.1,true)>R.blend(0,1,0.1,false),"Reduce Motion blends faster (no slow fade)")
print("cave lighting ok: lights "..#D.lights.."/"..C.MaxLights..", fx parts "..D.fxParts..", fall top "..(FY+F.height).." < "..string.format("%.1f",lowest))
'''

def module(name, parent):
    return 'local script={Parent={' + parent + '}}\n' + (ROOT / name).read_text()

def script(config):
    return ('local Config=(function()\n' + config + '\nend)()\n'
            + 'local require=function(x) return x end\n'
            + 'local CaveHubLayout=(function()\n' + module('src/shared/CaveHubLayout.luau', '') + '\nend)()\n'
            + 'local Terrain=(function()\n' + module('src/shared/CaveTerrainRules.luau', 'CaveHubLayout=CaveHubLayout') + '\nend)()\n'
            + 'local Rules=(function()\n' + module('src/shared/CaveLightingRules.luau', 'CaveHubLayout=CaveHubLayout') + '\nend)()\n'
            + LUAU)

def run(runner, config):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_cave_lighting.luau'; path.write_text(script(config))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    arena = (ROOT / 'src/server/Arena.luau').read_text()
    assert arena.count('CaveLighting.build(') == 1, 'built exactly once'
    on, off = arena.split('if caveHub.enabled then', 1)[1].split('    else\n        local hub = Instance.new("Model")', 1)
    assert 'CaveLighting.build(hub)' in on and 'CaveLighting' not in off, 'only the flag-on cave branch builds lighting'
    server = (ROOT / 'src/server/CaveLighting.luau').read_text()
    assert 'Enum.Material.Neon' not in server, 'beams never use Neon'
    assert 'CastShadow' in server and 'IsLightingFx' in server, 'beams are marked lighting FX, no shadows'
    assert 'SpecialMesh' not in server and 'MeshPart' not in server, 'no mesh (code-built model art) in the lighting FX'
    client = (ROOT / 'src/client/CaveAtmosphere.luau').read_text()
    step = client.split('function Cave.step(dt: number)', 1)[1]
    assert step.lstrip().startswith('if not Config.CaveHub then return end'), 'flag off: the client look returns before touching anything'
    assert 'ColorCorrectionEffect' in client and 'grade:Destroy()' in client, 'ColorCorrection only while inside, destroyed on leaving'
    assert 'WeatherDof' in client and 'dof.Enabled = false' in client and 's.dof ~= nil' in client, 'weather DepthOfField off in the cave, restored outside'
    weather = (ROOT / 'src/client/WeatherVisuals.client.luau').read_text()
    assert 'Cave.step(dt)' in weather and 'local hall=Cave.inside() or Cave.amount()>.01' in weather, 'weather calls the cave look last and keeps its rigs outside'
    # BD-383: every additive weather effect (WeatherGrade / Bloom / Rays / haze / exposure / lamps) scales by the weather strength t,
    # and t is multiplied by (1 - Cave.amount()), so inside the hall the weather writes neutral values (grey Blizzard cave).
    assert 'local t=WL.strength(k,Theme.MotionEnabled)*outside' in weather and 'outside=1-Cave.amount()' in weather, 'BD-383 weather strength fades out in the cave'
    for needle in ('grade.TintColor=c3(WL.mix(WHITE,tint,t))', 'bloom.Intensity=lerpNum(0,look.bloom,t)', 'rays.Intensity=lerpNum(0,look.rays,t)', 'lamp.Brightness=look.lamp*t'):
        assert needle in weather, 'BD-383 effect still driven by the faded t: ' + needle
    assert '*outside' in weather.split('grade.Brightness=', 1)[1].split(chr(10), 1)[0], 'BD-383 flash/pulse scaled too'
    assert 'flash*.9*outside' in weather, 'BD-383 flash exposure scaled'
    # BD-398: inside the hall no weather rigs, bolts, bombs, cracks, moon, aurora or shake, a soft toast instead of the title card
    assert 'local motion=Theme.MotionEnabled and root~=nil and not hall' in weather, 'BD-398 rigs/one-shots off inside'
    assert 'local live=motion and root~=nil and not hall' in weather and 'not hall and activeId=="quake"' in weather, 'BD-398 live effects off inside'
    assert 'showTitle(id,workspace:GetAttribute("WeatherName") or id,hall)' in weather and 'if soft then name' in weather, 'BD-398 soft toast inside'
    assert 'if hall then shake=' in weather, 'BD-398 shake only a faint quake rumble inside'
    assert 'Lighting.Brightness = saved.brightness' in client and 'Lighting.ShadowSoftness' in client, 'BD-398 cave brightness and shadow softness, restored'
    assert 'spec.shadows == true' in server, 'BD-398 shadows only on flagged lights'
    assert 'CastShadow = not p.walk' in (ROOT / 'src/server/CaveProps.luau').read_text(), 'BD-398 props cast shadows'
    rules = (ROOT / 'src/shared/CaveLightingRules.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'Vector3', 'workspace', 'Config'):
        assert banned not in rules, 'CaveLightingRules stays pure: ' + banned
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text()
    assert 'CaveAtmosphere' not in boot and 'CaveLighting' not in boot, 'no new locals in Bootstrap.client'

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    source = (ROOT / 'src/shared/Config.luau').read_text()
    print('Default: ' + run(args.runner, source))
    rewritten, _ = release_profiles.apply_profile(source, 'playtest')
    print('Playtest: ' + run(args.runner, rewritten)[:70])
