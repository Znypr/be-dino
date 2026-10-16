"""BD-285 / BD-292 offline check of the Cave lava falls polish (docs/104 s5, s6). Runs the real CaveHubLayout, CaveHubProps,
CaveLavaRules, HubSignCopy and EffectAssets in Luau (pure numbers, never Studio):
 * BD-385 no tiled rectangle: the falls are particle strands (irregular lip, flameSheet puffs), no Layers / scroll / tile API in the rules;
 * emitter budget: total rate <= 25 per second on desktop, <= 10 on phones, 0 under Reduce Motion; every rate has an emitter rule;
 * strands use only the existing flameSheet alpha upload;
 * Fame boards: an arc east of the Fame pad, inside the floor, clear of every pad, nowhere near the lava line of sight (no nearby station
   centre sees the falls or the basin through a board) and on the far side of the pad from the lava; the old row beside the falls
   is kept as a negative control;
 * sign text: HubSignCopy.forRow gives the station word for sign_stone / sign_arrow rows only, never for the Heart, within the
   14 character cap, child-safe, and the sign rows never exceed Props.MaxSignGuis;
 * warm recolour table only names real placed keys and warm colours.
 Static checks: the lava FX has NO Texture / SurfaceGui / ImageLabel / TileSize / StudsPerTile / ScaleType.Tile and an invisible carrier, the client preloads with
 ContentProvider:PreloadAsync and honours Calm motion, CaveProps puts text on the front face with FredokaOne / TextScaled, the Fame boards
 use CaveHubLayout.boardSpots, no new locals in Bootstrap.client.
Not Studio evidence: see docs/evidence/2026-10-16-cave-lava/ and the BD-285 kanban row.
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles
ROOT = Path(__file__).resolve().parents[1]

LUAU = r'''
assert(Config.CaveHub==false,"CaveHub ships off")
local C=CaveHubLayout
local L=C.get()
local R=LavaRules
local F,P=C.Fall,C.Pool

-- ---- emitter budget
local total=R.totalRate()
assert(total<=R.FxBudget.desktop,"desktop emitters "..total.." <= 25")
assert(R.FxBudget.desktop==25 and R.FxBudget.phone==10,"budgets are 25 / 10")
local phoneTotal,desktopTotal,calmTotal=0,0,0
for name,_ in R.Rates do
 desktopTotal+=R.rate(name,false,false)
 phoneTotal+=R.rate(name,true,false)
 calmTotal+=R.rate(name,false,true)+R.rate(name,true,true)
 assert(R.rate(name,true,false)<=R.rate(name,false,false),"phone never above desktop: "..name)
end
assert(math.abs(desktopTotal-total)<1e-9 and desktopTotal<=25,"desktop total")
assert(phoneTotal<=10+1e-9 and phoneTotal>0,"phone total "..phoneTotal.." <= 10")
assert(calmTotal==0,"Reduce Motion: no particles")
assert(R.rate("nope",false,false)==0,"unknown emitter rule = 0")
assert(R.phoneScale()<=1 and R.phoneScale()>0)

-- ---- BD-385: strands, not a tiled sheet
assert(R.Layers==nil and R.scroll==nil and R.stripY==nil and R.tilePx==nil and R.CanvasPxPerStud==nil and R.edgeFade==nil,"no scrolling tile API left")
assert(#R.Strands>=6 and #R.Strands<=9,"6-9 strands")
local dxs,dys,sizes={}, {}, {}
local lastDx=-1e9
for i,s in R.Strands do
 assert(s.dx>lastDx and math.abs(s.dx)<=(F.width-2)/2,"strand inside the falls width, ordered: "..i)
 assert(s.size>=5 and s.size<=10 and s.life>=3 and s.life<=5 and s.fall>0 and s.rate>0 and s.dy>=0 and s.dy<=5,"strand sane "..i)
 assert(0.5*s.fall*s.life*s.life>=F.height*0.4,"strand falls far enough "..i)
 if i>1 then
  local gap=s.dx-lastDx
  assert(gap<=s.size+2,"neighbouring strands overlap so no gap or grid shows: "..i)
  dxs[string.format("%.2f",gap)]=true
 end
 dys[s.dy]=true sizes[s.size]=true
 lastDx=s.dx
 assert(R.Rates["strand"..i]==s.rate,"every strand has an emitter rule")
end
local function count(t) local n=0 for _ in t do n+=1 end return n end
assert(count(dxs)>=4,"strand spacing is irregular (no regular grid)")
assert(count(dys)>=4 and count(sizes)>=4,"lip height and puff size vary (ragged silhouette)")
assert(R.StillBurst>=10 and R.StillBurst<=30,"Reduce Motion static burst")
assert(Assets.isReal("flameSheet") and Assets.HasAlpha.flameSheet,"strands use the existing flameSheet alpha upload")

-- ---- Fame boards away from the lava line
local B=C.Boards
local spots=C.boardSpots()
assert(#spots==3,"three boards")
local fame=L.byId.fame
local lavaX,lavaZ=(F.x+P.x)/2,(F.z+P.z)/2
local function endpoints(s)
 local hw=B.width/2
 -- the board's width axis is the part's local X; yaw rotates it (CFrame.Angles(0,yaw,0): x axis = (cos yaw, 0, -sin yaw))
 local dx,dz=math.cos(s.yaw)*hw,-math.sin(s.yaw)*hw
 return s.x-dx,s.z-dz,s.x+dx,s.z+dz
end
local function segCross(ax,az,bx,bz,cx,cz,dx,dz)
 local function o(px,pz,qx,qz,rx,rz) return (qx-px)*(rz-pz)-(qz-pz)*(rx-px) end
 local d1,d2,d3,d4=o(cx,cz,dx,dz,ax,az),o(cx,cz,dx,dz,bx,bz),o(ax,az,bx,bz,cx,cz),o(ax,az,bx,bz,dx,dz)
 return d1*d2<0 and d3*d4<0
end
local fallLeft,fallRight=F.x-F.width/2,F.x+F.width/2
for i,s in spots do
 local x1,z1,x2,z2=endpoints(s)
 assert(C.insideFloor(s.x,s.z+C.CenterZ,2),"board centre inside the floor "..i)
 assert(C.insideFloor(x1,z1+C.CenterZ,0) and C.insideFloor(x2,z2+C.CenterZ,0),"board ends inside the floor "..i)
 local d=math.sqrt((s.x-fame.x)^2+(s.z-fame.z)^2)
 assert(math.abs(d-B.radius)<1e-6 and d>fame.r+B.width/2-6,"board stands outside the Fame pad "..i)
 for _,st in L.stations do
  if st.id~="fame" then
   local dd=math.sqrt((s.x-st.x)^2+(s.z-st.z)^2)
   assert(dd>=st.r+4,"board clear of the "..st.id.." pad (dist "..string.format("%.1f",dd)..")")
  end
 end
 -- far side from the lava: the board is not between the Fame pad and the lava
 local dot=(s.x-fame.x)*(lavaX-fame.x)+(s.z-fame.z)*(lavaZ-fame.z)
 assert(dot<0,"board is on the far side of Fame from the lava "..i)
 assert(math.min(x1,x2)>=fallRight+20,"board stays 20+ studs east of the falls edge "..i..": "..math.min(x1,x2).." vs "..(fallRight+20))
 -- no station centre looks at the falls / the basin through a board
 local targets={{P.x,P.z},{fallLeft,F.z},{F.x,F.z},{fallRight,F.z},{P.x-P.r,P.z},{P.x+P.r,P.z}}
 for _,st in L.stations do
  -- viewpoints within 95 studs of the basin (the Heart, Fame, Fusion, Settings, Index ...); the far Style / Nests / Gate / Potions
  -- stations are 100+ studs away and see the basin only as a distant glow
  if math.sqrt((st.x-P.x)^2+(st.z-P.z)^2)<=95 then
  for _,t in targets do
   assert(not segCross(st.x,st.z,t[1],t[2],x1,z1,x2,z2),"board "..i.." blocks the view from "..st.id.." to the lava")
  end
  end
 end
 assert(s.z>=0 and s.z<=F.z,"board in front of the back wall")
 -- faces the Fame pad centre: front (-Z rotated by yaw) points at the pad
 local fx,fz=-math.sin(s.yaw),-math.cos(s.yaw)
 local tx,tz=fame.x-s.x,fame.z-s.z
 local tl=math.sqrt(tx*tx+tz*tz)
 assert((fx*tx+fz*tz)/tl>0.999,"board faces the Fame pad "..i)
end
-- negative control: the OLD row (centre x = fame.x+10 -> 31 / 58 / 85, z = fame.z+10) hugged the falls
local oldMinX=fame.x+10-27-B.width/2
assert(oldMinX<fallRight+20,"the old board row stood within 20 studs of the falls edge (this is the QA problem)")
-- the arc order is stable (left to right on the screen of a player facing the pad from the Heart)
assert(spots[1].z<spots[2].z and spots[2].z<spots[3].z,"boards ordered by z")

-- ---- sign text
local sc=SignCopy
local rows=0
for _,p in L.props do
 if p.key=="hub_sign_stone" or p.key=="hub_sign_arrow" then
  rows+=1
  local text=sc.forRow(p.key,p.owner)
  if p.owner=="heart" then assert(text==nil,"the Heart has no sign text") else
   assert(text~=nil and #text<=sc.MaxLength and sc.acceptable(text),"sign text for "..p.owner)
   assert(text==sc.Signs[p.owner],"text is the copy table word")
  end
 end
end
assert(rows>=8 and rows<=Props.MaxSignGuis,"sign rows "..rows.." within the sign gui cap "..Props.MaxSignGuis)
assert(sc.forRow("cave_rock_round","nests")==nil and sc.forRow("hub_sign_stone","nowhere")==nil and sc.forRow("hub_sign_stone","heart")==nil and sc.forRow("hub_sign_stone",5)==nil,"no text for other keys / stations")
assert(Props.SignLightInfluence==0 and Props.SignBrightness>=1.5,"signs self-lit and boosted for the dim cave")
for key,cfg in Props.SignText do
 assert(Props.Assets[key] and cfg.face=="Front" and cfg.inset>=0 and cfg.inset<0.4,"sign text config "..key)
end

-- ---- warm recolour
for key,w in Props.Warm do
 assert(Props.Assets[key] and not Props.NotMeshes[key],"warm key is a placed mesh: "..key)
 assert(w.color[1]>=w.color[3]+30 and w.color[1]>=w.color[2],"warm colour (red-brown) "..key)
 assert(w.material=="Slate" or w.material=="Plastic","matte material")
end
assert(Props.Warm.cave_lava_rim_rock and Props.Warm.cave_stepping_stone,"rim rocks and stepping stones recoloured")

-- ---- budgets unchanged (300 / 410 parts)
local budget=C.budgetTable()
assert(budget.total.parts<=C.Budget.total.parts,"hub parts "..budget.total.parts.." <= "..C.Budget.total.parts)
assert(Props.Lava.fxPartBudget==1+#R.Glow+1 and Props.Lava.fxPartBudget<=7,"lava FX parts: 1 invisible carrier + glow discs + pool disc")
assert(Props.Lava.sheetTransparency==1,"the carrier part is invisible")
assert(#R.Glow>=3,"a stepped glow")
for i=2,#R.Glow do assert(R.Glow[i].diameter<R.Glow[i-1].diameter and R.Glow[i].transparency<R.Glow[i-1].transparency,"glow brighter toward the middle") end
assert(R.Glow[1].transparency>=0.75,"outer glow ring is faint (no hard rim)")
print(string.format("cave lava ok: emitters %d/s desktop, %.1f/s phone, %d strands, boards min x %.0f vs falls edge %.0f, %d sign rows, parts %d/%d",total,phoneTotal,#R.Strands,math.min(endpoints(spots[1])),fallRight,rows,budget.total.parts,C.Budget.total.parts))
'''

def module(name, parent=''):
    return 'local script={Parent={' + parent + '}}\n' + (ROOT / name).read_text()

def script(config):
    return ('local Config=(function()\n' + config + '\nend)()\n'
            + 'local require=function(x) return x end\n'
            + 'local CaveHubLayout=(function()\n' + module('src/shared/CaveHubLayout.luau') + '\nend)()\n'
            + 'local Props=(function()\n' + module('src/shared/CaveHubProps.luau') + '\nend)()\n'
            + 'local LavaRules=(function()\n' + module('src/shared/CaveLavaRules.luau') + '\nend)()\n'
            + 'local SignCopy=(function()\n' + module('src/shared/HubSignCopy.luau') + '\nend)()\n'
            + 'local Assets=(function()\n' + module('src/shared/EffectAssets.luau') + '\nend)()\n'
            + LUAU)

def run(runner, config):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_cave_lava.luau'; path.write_text(script(config))
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()

def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    assert 'CaveHub = false' in cfg, 'Config.CaveHub ships false'
    fx = (ROOT / 'src/server/CaveLavaFx.luau').read_text()
    assert 'for i, strand in Rules.Strands do' in fx and 'Rules.Glow' in fx and '"flameSheet"' in fx, 'BD-385 particle strands from the flame sheet and a glow pool'
    for banned in ('Instance.new("Texture")', 'Instance.new("SurfaceGui")', 'Instance.new("ImageLabel")', 'Instance.new("CanvasGroup")', 'Instance.new("Beam")',
                   'TileSize', 'StudsPerTile', 'ScaleType', 'buildLayer', 'Rules.Layers', 'stripY'):
        assert banned not in fx, 'no tiled rectangle / grid on the lava (BD-385): ' + banned
    assert 'Enum.PartType.Block, orange, 1)' in fx, 'the carrier part is fully transparent'
    assert 'StillGlow' in fx, 'static Reduce Motion variant exists (frozen by the client)'
    assert 'TweenService' not in fx and 'task.spawn' not in fx, 'no server-side animation loop (Reduce Motion lives on the client)'
    assert 'LoadAsset' not in fx and 'MeshPart' not in fx, 'the chunky generated block is still not used (no mesh in the lava FX)'
    rules = (ROOT / 'src/shared/CaveLavaRules.luau').read_text()
    for banned in ('Instance.new', 'game:GetService', 'Vector3', 'workspace', 'Config', 'require('):
        assert banned not in rules, 'CaveLavaRules stays pure: ' + banned
    client = (ROOT / 'src/client/CaveLavaClient.luau').read_text()
    assert 'ContentProvider:PreloadAsync' in client and 'AssetFetchStatus.Success' in client and 'Assets.Builtin.spark' in client, \
        'client preloads the lava textures and falls back to the built-in sprite'
    assert 'Rules.rate(' in client and 'calm' in client and 'TimeScale = 0' in client and 'Rules.stripY' not in client, 'client honours Reduce Motion and phone rates'
    assert 'if not calm then seconds += dt end' in client, 'the animation clock stops under Reduce Motion'
    atmo = (ROOT / 'src/client/CaveAtmosphere.luau').read_text()
    assert 'Lava.step(dt, calm)' in atmo and atmo.index('if not Config.CaveHub then return end') < atmo.index('Lava.step(dt, calm)'), \
        'lava client runs only after the flag check and only while inside'
    props = (ROOT / 'src/server/CaveProps.luau').read_text()
    assert 'FredokaOne' in props and 'TextScaled = true' in props and 'SignCopy.forRow' in props and 'signGuis < Props.MaxSignGuis' in props, \
        'sign text: copy table word, FredokaOne, TextScaled, capped'
    assert 'gui.LightInfluence = Props.SignLightInfluence' in props and 'gui.Brightness = Props.SignBrightness' in props, 'sign text is self-lit (readable in the dim cave)'
    assert props.count('Instance.new("SurfaceGui")') == 1 and 'gui.Face = ' in props, 'one SurfaceGui, one face (front only)'
    assert 'Props.Warm' in props and 'SurfaceAppearance' in props, 'warm recolour strips the SurfaceAppearance'
    lead = (ROOT / 'src/server/Leaderboards.luau').read_text()
    assert 'CaveHubLayout.boardSpots()' in lead and 'fame.x+10' not in lead, 'Fame boards use the pure board spots'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text()
    assert 'CaveLava' not in boot, 'no new locals in Bootstrap.client'

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    source = (ROOT / 'src/shared/Config.luau').read_text()
    print('Default: ' + run(args.runner, source))
    rewritten, _ = release_profiles.apply_profile(source, 'playtest')
    print('Playtest: ' + run(args.runner, rewritten)[:70])
