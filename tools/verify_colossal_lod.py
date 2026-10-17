"""BD-475 (docs/142) offline verifier: the colossal ancient trees (BD-474) are safe to switch on once their ids are pasted.

Runs the REAL shared code (ColossalRules, WorldGeneratedMeshes, Config.WorldCulling, the placement grammar) in the Luau runner and checks:
  A. EMPTY IDS = TODAY'S WORLD: every id is empty, colossalFor() is nil for every colossal placement, the client never sees a colossal
     model (no ColossalKey attribute is ever set without a pair), the default colossal radius is the normal cull radius, and the
     Arena / WorldCulling source only reaches the new code through that attribute or a filled pair.
  B. FAKE IDS (every entry treated as uploaded): the LOD swap thresholds (with hysteresis) per device class, the LOD1 pivot compensation
     (the two trunks coincide; without it the swap jumps up to ~5 studs), the LOD0 cap and the triangle budget across the whole arena,
     the radius clamp (default = today, ceiling 420 on phone), the distance fade, trunk colliders that match the stored trunk widths for
     every real colossal placement, and grounding on the lowest of nine footprint rays.
  C. BUDGET: the phone worst-spot triangle estimate with fake ids is not above today's (estimate_world_budget.py, stand-in = 1,630 tris).
Not Studio evidence and not a phone measurement. Usage: python tools/verify_colossal_lod.py --runner luau.exe
"""
from pathlib import Path
import argparse, math, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_world_budget as est
import verify_world_art as vwa
import verify_world_overlap as vwo

ROOT = est.ROOT

LUAU = r'''
local Generated=@GENERATED@
local Rules=@RULES@
local a=Biome.generate({seed=Config.WorldArtSeed,density=Config.WorldArtDensity,extent=Config.ArenaHalfWidth,height=Layout.height,kit=Kit,meshes=Meshes,map=BiomeMap,layout=Layout})
local WC=Config.WorldCulling
local CLASSES={"Phone","Tablet","Desktop"}
local function near(x,y,eps,msg) assert(math.abs(x-y)<=(eps or 1e-6),msg.." "..x.." vs "..y) end

-- ===================================================================== A. empty ids = today's world
local filled=0
for _,e in Generated.Colossal do if e.assetId~="" then filled+=1 end end
assert(filled==0,"the repo must ship with empty colossal ids (the owner pastes them): "..filled)
local colossalPlacements,withMesh,standInOnly=0,0,0
for _,p in a do
 if p.layer=="colossal" then
  colossalPlacements+=1
  assert(Generated.colossalFor(p.id)==nil,"empty ids must keep the stand-in: "..p.id)
 end
end
assert(colossalPlacements>=20,"colossal placements exist: "..colossalPlacements)
for _,class in CLASSES do
 local s=Rules.settings(WC,class)
 assert(s.radius==WC[class].radius,"default colossal radius must equal the normal cull radius (today's behaviour): "..class)
 assert(s.ceiling>=s.radius)
end
print("A ok: "..colossalPlacements.." colossal placements, "..filled.." ids filled, default colossal radius = normal radius")

-- ===================================================================== B. fake ids
-- B1 LOD swap thresholds (hysteresis, per device class)
for _,class in CLASSES do
 local s=Rules.settings(WC,class) local H=WC.Hysteresis
 local function one(d,state) local out=Rules.assign({{d=d,state=state,tris0=4000,tris1=900}},s,H,10) return out[1] end
 assert(one(s.lod0-1,"off")=="lod0","just inside the swap distance is LOD0: "..class)
 assert(one(s.lod0+1,"off")=="lod1","just outside the swap distance is LOD1: "..class)
 assert(one(s.lod0*H-1,"lod0")=="lod0","LOD0 holds inside the hysteresis band (no flicker): "..class)
 assert(one(s.lod0*H-1,"lod1")=="lod1","LOD1 does not flip back inside the band: "..class)
 assert(one(s.lod0*H+1,"lod0")=="lod1","LOD0 lets go beyond the band: "..class)
 assert(one(s.radius-1,"off")=="lod1","inside the radius a tree is shown: "..class)
 assert(one(s.radius+1,"off")=="off","outside the radius it is culled: "..class)
 assert(one(s.radius*H-1,"lod1")=="lod1","a shown tree stays through the hysteresis band: "..class)
 assert(one(s.radius*H+1,"lod1")=="off","and goes beyond it: "..class)
 assert(s.lod0<s.radius,"the swap distance is inside the radius: "..class)
end
-- B2 radius: a config value, clamped to [normal radius, ceiling] (docs/139 Q12: phone ceiling 420)
assert(Rules.settings(WC,"Phone").ceiling==420 and Rules.settings(WC,"Tablet").ceiling==560 and Rules.settings(WC,"Desktop").ceiling==800,"ceilings 420 / 560 / 800")
for _,class in CLASSES do
 local function with(r) local w={Colossal={Fade=.2,[class]={lod0=100,lod0Max=1,triBudget=1e5,ceiling=WC.Colossal[class].ceiling,radius=r}},[class]=WC[class]} return Rules.settings(w,class).radius end
 assert(with(99999)==WC.Colossal[class].ceiling,"radius never above the ceiling: "..class)
 assert(with(1)==WC[class].radius,"radius never below the normal radius: "..class)
 assert(with(WC.Colossal[class].ceiling-5)==WC.Colossal[class].ceiling-5,"a radius in range is used as set: "..class)
end
-- B3 fade
near(Rules.fadeAlpha(0,190,.2),0,1e-9,"solid at the player") near(Rules.fadeAlpha(190*.8,190,.2),0,1e-9,"solid up to the fade start")
near(Rules.fadeAlpha(190,190,.2),1,1e-9,"gone AT the radius") near(Rules.fadeAlpha(500,190,.2),1,1e-9,"gone beyond")
assert(Rules.fadeAlpha(170,190,.2)>0 and Rules.fadeAlpha(170,190,.2)<1 and Rules.fadeAlpha(160,190,.2)<Rules.fadeAlpha(180,190,.2),"smooth ramp")
assert(Rules.fadeAlpha(189,190,0)==0,"fade 0 = today's plain pop")
-- B4 pivot compensation: the LOD1 trunk lands on the LOD0 trunk
local worstJump,worstFixed=0,0
for key,e0 in Generated.Colossal do
 if e0.lod==0 then
  local e1=Generated.Colossal[key.."_lod1"]
  assert(e1 and e1.kit==e0.kit,"every LOD0 has its LOD1: "..key)
  for _,h in {80,104,139} do
   local s0,s1=h/e0.size[3],h/e1.size[3]
   local tx0,tz0=Rules.trunkOffset(e0,h) -- LOD0 trunk base in the pivot frame
   local dx,dz=Rules.lod1Offset(e0,e1,h) -- LOD1 centre
   local tx1,tz1=dx+e1.base[1]*s1,dz+Rules.BlenderYToStudZ*e1.base[2]*s1
   near(tx1,tx0,1e-9,"LOD1 trunk x "..key) near(tz1,tz0,1e-9,"LOD1 trunk z "..key)
   worstFixed=math.max(worstFixed,math.sqrt((tx1-tx0)^2+(tz1-tz0)^2))
   -- without the shift both centres sit at 0: the trunk would jump by |base1*s1 - base0*s0|
   local jump=math.sqrt((e1.base[1]*s1-e0.base[1]*s0)^2+(e1.base[2]*s1-e0.base[2]*s0)^2)
   worstJump=math.max(worstJump,jump)
  end
 end
end
assert(worstJump>4 and worstJump<8,"the uncompensated jump is the ~5 stud one from docs/140: "..worstJump)
print(string.format("B4 ok: LOD swap jump without compensation up to %.2f studs, with it %.1e",worstJump,worstFixed))
-- B5 LOD0 cap and triangle budget, synthetic worst cases and the whole arena
for _,class in CLASSES do
 local s=Rules.settings(WC,class)
 for _,count in {1,5,31,200} do
  local items={} for i=1,count do items[i]={d=5+i*.01,state="off",tris0=4154,tris1=925} end
  local states,st=Rules.assign(items,s,WC.Hysteresis,1e9)
  assert(st.lod0<=s.lod0Max,"LOD0 cap: "..class.." "..st.lod0)
  assert(st.tris<=s.triBudget,"triangle budget: "..class.." "..st.tris)
  assert(st.lod0+st.lod1==st.parts and st.parts<=count)
  if count==1 then assert(states[1]=="lod0","a lone near tree is LOD0") end
  for i=2,#items do assert(not(states[i]=="lod0" and states[i-1]~="lod0"),"LOD0 goes to the NEAREST trees") end
 end
 local _,st=Rules.assign({{d=10,state="off",tris0=4000,tris1=900},{d=11,state="off",tris0=4000,tris1=900}},s,WC.Hysteresis,1)
 assert(st.parts==1,"the part budget bounds the trees: "..class)
 local _,st2=Rules.assign({{d=10,state="off",tris0=4000,tris1=900}},s,WC.Hysteresis,0)
 assert(st2.parts==0 and st2.off==1,"no part budget left = culled")
end
-- B6 trunk colliders re-fitted from the stored trunk widths, for every real colossal placement
local nColl,widest,thinner=0,0,0
local function fitted(p)
 local data=Kit[p.id]
 local e0=nil for _,e in Generated.Colossal do if e.lod==0 and e.kit==p.id then e0=e end end
 if not e0 then return nil end
 local ext=data.extent
 -- Arena.generatedProp: Size = mesh size * min(extentY / sizeY, max(extentX, extentZ) * 1.15 / max(sizeX, sizeZ)), then ScaleTo(p.scale)
 local sx,sy,sz=e0.size[1],e0.size[3],e0.size[2] -- Roblox Size = (Blender x, z, y)
 local fit=math.min(ext[2]/sy,math.max(ext[1],ext[3])*1.15/math.max(sx,sz))
 return e0,sy*fit*p.scale
end
for _,p in a do
 if p.layer=="colossal" then
  local e0,h=fitted(p)
  if e0 then
   nColl+=1
   local s=h/e0.size[3]
   local diam=e0.trunk[1]*s
   local cs=Rules.colliders(e0,h)
   assert(#cs==3,"three trunk boxes")
   local cx,cz=Rules.trunkOffset(e0,h)
   local top=0
   for i,c in cs do
    near(c[1],cx,1e-9,"collider on the trunk x") near(c[3],cz,1e-9,"collider on the trunk z")
    near(c[4],diam*Rules.Collider.tiers[i].width,1e-9,"box width = trunk diameter x tier") near(c[6],c[4],1e-9,"square")
    assert(c[4]>=diam*.9-1e-9,"no box thinner than 0.9 x the trunk")
    near(c[2]-c[5]/2,top,1e-9,"boxes stack from the floor") top+=c[5]
    widest=math.max(widest,c[4])
   end
   assert(cs[1][4]>=diam,"the base box is at least the trunk diameter (a dino cannot walk into the trunk)")
   near(top,math.clamp(e0.trunk[2]*s,Rules.Collider.minHeight,Rules.Collider.maxHeight),1e-9,"collider height")
   assert(top<=45+1e-9,"colliders stop at the first branch height 45")
   -- today's kit collider is thinner than the new trunk: this is the walk-through the task fixes
   local kc=Kit[p.id].colliders[1]
   if math.max(kc[4],kc[6])*p.scale<diam then thinner+=1 end
   local cx0,cz0=Rules.trunkOffset(e0,h)
   print(string.format("N	%.4f	%.4f	%.5f	%.4f	%.4f	%.4f	%.4f",p.x,p.z,p.yaw,cx0,cz0,cs[1][4],p.radius))
  end
 end
end
assert(nColl>=15,"colossal placements with an ancient mesh: "..nColl)
assert(thinner==nColl,"every ancient trunk is thicker than today's kit collider (the walk-through): "..thinner.."/"..nColl)
print(string.format("B6 ok: %d colossal placements re-fitted (today's kit collider is thinner than the trunk in %d), widest box %.1f studs",nColl,thinner,widest))
-- data for the Python geometry checks (solid footprints, corridors)
for _,p in a do if p.layer=="tree" or p.layer=="colossal" or p.layer=="rock" or p.layer=="landmark" then print(string.format("S	%s	%s	%.3f	%.3f	%.4f	%.4f",p.layer,p.id,p.x,p.z,p.yaw,p.scale)) end end
for id,d in Kit do for _,c in d.colliders do print(string.format("K	%s	%.3f	%.3f	%.3f	%.3f	%.4f",id,c[1],c[3],c[4],c[6],c[7])) end end
for _,path in Biome.Paths do
 local pts={} for _,pt in path.points do table.insert(pts,string.format("%.2f,%.2f",pt[1],pt[2])) end
 print("L	"..path.width.."	"..table.concat(pts,";"))
end
-- B7 grounding: nine rays under the trunk, the LOWEST wins
do
 local e0=Generated.Colossal.tree_colossal_broadleaf_v3
 local h=104
 local pts=Rules.groundPoints(100,-50,.7,e0,h)
 assert(#pts==9,"nine rays")
 local cx,cz=Rules.trunkOffset(e0,h)
 local wx,wz=Rules.toWorld(100,-50,.7,cx,cz)
 near(pts[1][1],wx,1e-9,"centre ray on the trunk base") near(pts[1][2],wz,1e-9,"centre ray z")
 local r=e0.trunk[1]*h/e0.size[3]/2
 for i=2,9 do near(math.sqrt((pts[i][1]-wx)^2+(pts[i][2]-wz)^2),r,1e-9,"ring ray at the trunk radius") end
 assert(r>8,"the footprint is the real trunk, not the 1 stud centre ray: "..r)
 -- a 20 degree slope falling toward +x: terrain y = 30 - tan(20) * (x - 100)
 local slope=math.tan(math.rad(20))
 local hits={} local hi,lo=-1/0,1/0
 for i,pt in pts do local y=30-slope*(pt[1]-100) hits[i]=y hi=math.max(hi,y) lo=math.min(lo,y) end
 local y=Rules.groundY
 local ground=Rules.groundY(30,hits)
 near(ground,lo-Rules.RootSink,1e-9,"the bottom sits on the lowest ray")
 for _,hh in hits do assert(hh>=ground,"no ray is below the bottom (nothing floats on the downhill side)") end
 assert(hi-lo>5,"the slope matters: "..(hi-lo).." studs of relief under the trunk (the old highest-ray rule would float the downhill side by that much)")
 assert(Rules.groundY(30,{30,nil,nil,nil,nil,nil,nil,nil,nil})==30,"too few hits keeps the layout height")
 assert(Rules.groundY(30,{80,80,80,80,80,80,80,80,80})==30,"a wild answer keeps the layout height")
 near(Rules.RootSink,Biome.Ground.RootSink,0,"same root sink as BiomePlacement.Ground")
end
print("B7 ok: nine footprint rays, lowest wins")

-- ===================================================================== B8 the config the game ships with
for _,class in CLASSES do
 local s=Rules.settings(WC,class)
 assert(s.lod0Max>=1 and s.lod0Max<=4,"LOD0 cap sane: "..class)
 assert(s.triBudget>=4154+925*2,"the triangle budget fits at least one LOD0 tree and a few LOD1: "..class)
 assert(s.fade>0 and s.fade<=.5,"fade on by default")
end
assert(WC.Colossal.Phone.lod0Max==1,"phone: one LOD0 tree at a time (docs/139 s9: 1 at LOD0 + 5 at LOD1)")
print("B8 ok")
'''


def luau_text(cfg):
    head = vwa.script(False, cfg, False)
    pre = head[:head.index('local PLAYTEST=')]
    return (pre + LUAU.replace('@GENERATED@', vwa.wrapped('src/shared/WorldGeneratedMeshes.luau'))
            .replace('@RULES@', vwa.wrapped('src/shared/ColossalRules.luau')))


def run_luau(runner):
    text = (ROOT / 'src/shared/Config.luau').read_text()
    cfg = est.release_profiles.apply_profile(text, 'playtest')[0]
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'colossal_lod.luau'
        p.write_text(luau_text(cfg))
        out = subprocess.run([runner, str(p)], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(out.stdout[-2500:] + out.stderr)
    data = {'N': [], 'S': [], 'K': {}, 'L': []}
    for line in out.stdout.splitlines():
        f = line.split('	')
        if f[0] in data:
            if f[0] == 'K':
                data['K'].setdefault(f[1], []).append(tuple(float(v) for v in f[2:]))
            else:
                data[f[0]].append(f[1:])
        else:
            print(line)
    return data


MAX_NEW_OVERLAPS = 1     # solid/solid overlaps with the re-fitted trunks (today 0, verify_world_overlap). The 1 = a small conifer at (-360, 124) beside the colossal conifer at (-348, 116):
                         # the placement grammar keeps colossal trees clear by the OLD thin collider; keeping them clear by the real trunk needs a BiomePlacement version bump (docs/142 follow-up)
MAX_CORRIDOR_BITE = 8.0  # studs a re-fitted trunk box may reach into a path corridor (the placement keeps the trunk centre >= 14 studs clear)


def seg_dist(px, pz, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (pz - a[1]) * dz) / (dx * dx + dz * dz)))
    return math.hypot(px - (a[0] + t * dx), pz - (a[1] + t * dz))


def geometry_checks(data):
    """The re-fitted trunks are thicker than the kit colliders: they must not overlap another solid, nor bite far into a path corridor."""
    props = [dict(layer=r[0], id=r[1], x=float(r[2]), z=float(r[3]), yaw=float(r[4]), scale=float(r[5])) for r in data['S']]
    fitted = {(round(float(n[0]), 2), round(float(n[1]), 2)): n for n in data['N']}
    items, bites = [], []
    paths = [(float(w), [tuple(float(v) for v in pt.split(',')) for pt in pts.split(';')]) for w, pts in data['L']]
    for i, p in enumerate(props):
        key = (round(p['x'], 2), round(p['z'], 2))
        if p['layer'] == 'colossal' and key in fitted:
            n = fitted[key]
            cx, cz, w = float(n[3]), float(n[4]), float(n[5])
            c, s = math.cos(p['yaw']), math.sin(p['yaw'])
            boxes = [(p['x'] + cx * c + cz * s, p['z'] - cx * s + cz * c, w, w, p['yaw'])]
            for bx, bz, bw, bd, byaw in boxes:  # corridor bite: sample the box outline
                cc, ss = math.cos(byaw), math.sin(byaw)
                for k in range(-10, 11):
                    for edge in ((k / 10, 1), (k / 10, -1), (1, k / 10), (-1, k / 10)):
                        ex, ez = edge[0] * bw / 2, edge[1] * bd / 2
                        wx, wz = bx + ex * cc + ez * ss, bz - ex * ss + ez * cc
                        for width, pts in paths:
                            for a, b in zip(pts, pts[1:]):
                                bites.append(width - seg_dist(wx, wz, a, b))
        elif p['id'] in data['K']:
            boxes = vwo.boxes(p, data['K'][p['id']])
        else:
            continue
        reach = max(max(b[2], b[3]) for b in boxes) + max(math.hypot(b[0] - p['x'], b[1] - p['z']) for b in boxes)
        items.append((i, p, boxes, reach))
    grid = {}
    for it in items:
        grid.setdefault((int(it[1]['x'] // 40), int(it[1]['z'] // 40)), []).append(it)
    pairs = 0
    for (gx, gz), cell in grid.items():
        near = [it for dx in (-1, 0, 1) for dz in (-1, 0, 1) for it in grid.get((gx + dx, gz + dz), [])]
        for a in cell:
            for b in near:
                if b[0] <= a[0] or math.hypot(a[1]['x'] - b[1]['x'], a[1]['z'] - b[1]['z']) > a[3] + b[3]:
                    continue
                if any(vwo.overlap(x, y) for x in a[2] for y in b[2]):
                    pairs += 1
                    print('  overlap', a[1]['layer'], a[1]['id'], round(a[1]['x']), round(a[1]['z']), a[2][0], 'x', b[1]['layer'], b[1]['id'], round(b[1]['x']), round(b[1]['z']), b[2][0])
    bite = max(bites) if bites else 0.0
    print(f"B9 geometry: {len(fitted)} re-fitted trunks, solid/solid overlaps {pairs} (cap {MAX_NEW_OVERLAPS}), deepest bite into a path corridor {max(bite, 0):.2f} studs (cap {MAX_CORRIDOR_BITE})")
    assert pairs <= MAX_NEW_OVERLAPS, 're-fitted trunks overlap another solid prop'
    assert bite <= MAX_CORRIDOR_BITE, 'a re-fitted trunk reaches too far into a path corridor'


def static_checks():
    arena = (ROOT / 'src/server/Arena.luau').read_text()
    cull = (ROOT / 'src/client/WorldCulling.client.luau').read_text()
    meshes = (ROOT / 'src/shared/WorldGeneratedMeshes.luau').read_text()
    # A: the new server code is only reached for a colossal pair (empty ids = colossalFor nil = no pair = no ColossalKey = no new path)
    assert 'local colossalKey = if layer == "colossal" then Generated.colossalFor(id) else nil' in arena
    assert 'if near and near:IsA("MeshPart") and far and far:IsA("MeshPart") then' in arena, 'the ancient tree is only used as a LOD0 + LOD1 pair'
    assert arena.count('model:SetAttribute("ColossalKey", key)') == 1 and 'if lodTemplate and lodTemplate:IsA("MeshPart") then' in arena
    assert 'local ancient = if made then Generated.Colossal[made:GetAttribute("ColossalKey") :: any] else nil' in arena
    assert 'else Ground.samplePoints(p.x, p.z, Ground.footprintRadius(rayLayer, size.X, size.Z))' in arena, 'other props keep the 5-ray rule'
    assert 'else Ground.corrected(p.y, hits, rayLayer, size.Y, 1)' in arena, 'other props keep the corrected() rule'
    assert 'ColossalRules.groundPoints(' in arena and 'ColossalRules.groundY(' in arena and 'ColossalRules.colliders(' in arena and 'ColossalRules.lod1Offset(' in arena
    assert 'made, ancientColliders(made))' in arena and 'if fitted then' in arena and 'for _, c in KitData[id].colliders do' in arena, 'kit colliders stay for every other prop'
    # client: colossal models are separate, ordinary props are untouched
    assert 'item:IsA("Model") and item:GetAttribute("ColossalKey") ~= nil and addColossal(folder, item, tries)' in cull
    assert 'ColossalRules.assign(items, colossalSettings, settings.Hysteresis, budget - used)' in cull and 'if colossalSettings and #colossals > 0 then' in cull
    fade_code = chr(10).join(l for l in cull.split('BD-475: colossal trees fade out')[1].split('local last: Vector3')[0].splitlines() if not l.strip().startswith('--'))
    assert 'ColossalRules.fadeAlpha(' in cull and 'LocalTransparencyModifier' not in fade_code, 'the fade must not use the property camera occlusion owns'
    assert 'lod1.Parent = nil' in cull and 'hidden.Parent = nil' in cull, 'exactly one LOD mesh is parented at a time'
    assert 'table.insert(props, {item = item, folder = folder, pos = first.Position' in cull, 'the ordinary prop path is unchanged'
    # data
    assert meshes.count('assetId = ""') >= 6 + 3 + 8 + 8 and 'size = {' in meshes
    ci = (ROOT / '.github/workflows/build-generated-place.yml').read_text()
    assert 'tools/verify_colossal_lod.py' in ci, 'CI must run this verifier'


def budget_checks(runner):
    r = est.estimate(runner)
    P = r['profiles']['playtest']
    print('C budget (playtest, estimate; stand-in = %s tris per colossal tree):' % est.GEN_TRIS)
    for cls, c in P['colossal'].items():
        d, k, b = c['default'], c['ceiling'], c['bound']
        assert b['max_tris'] <= c['standin_all_tris'], f'{cls}: even with every LOD0 slot full the colossal triangles stay below the stand-ins in total'
        print(f"  {cls:8s} {c['ancient_trees']} ancient-mesh trees, all as stand-ins {c['standin_all_tris']:,} tris | worst spot {c['worst_at']}: stand-ins {c['standin_n']} = {c['standin_tris']:,}, "
              f"fake ids default radius {d['lod0']} LOD0 + {d['lod1']} LOD1 = {d['tris']:,}, ceiling radius {k['lod0']} + {k['lod1']} = {k['tris']:,} | LOD0 slots always full {b['tris']:,} (any spot max {b['max_tris']:,}) | any spot max {d['max_tris']:,} / {k['max_tris']:,}, most LOD0 {max(d['max_lod0'], k['max_lod0'])}")
        cfg = (ROOT / 'src/shared/Config.luau').read_text()
        assert d['max_lod0'] <= 4 and k['max_lod0'] <= 4
        assert d['max_tris'] <= c['standin_all_tris'] and k['max_tris'] <= c['standin_all_tris'], f'{cls}: colossal triangles with fake ids must not pass the stand-ins ({c["standin_all_tris"]:,})'
    ps = P['phone_scene']
    print(f"  phone worst-spot scene tris (estimate): today {ps['world_tris_mid']:,} | fake ids default radius {ps['world_tris_mid_fake_default']:,} "
          f"(LOD0 slot always full: {ps['world_tris_mid_fake_bound']:,}) | fake ids ceiling radius {ps['world_tris_mid_fake_ceiling']:,}")
    assert ps['world_tris_mid_fake_default'] <= ps['world_tris_mid'], 'phone worst-spot triangles with fake ids must not exceed today'
    for cls, c in P['colossal'].items():
        assert c['default']['tris'] <= c['standin_tris'], f'{cls}: at the worst spot the fake-id colossal triangles must not exceed the stand-ins'
    # the phone numbers are what docs/139 s9 asked for: at most 1 tree at LOD0
    assert P['colossal']['Phone']['default']['max_lod0'] <= 1 and P['colossal']['Phone']['ceiling']['max_lod0'] <= 1
    # an unbounded phone radius (ceiling) stays inside the triangle budget
    cfg = (ROOT / 'src/shared/Config.luau').read_text()
    tri_phone = int(est.re.search(r'Phone = \{lod0 = \d+, lod0Max = \d+, triBudget = (\d+)', cfg).group(1))
    assert P['colossal']['Phone']['ceiling']['max_tris'] <= tri_phone <= P['colossal']['Phone']['standin_all_tris']
    # parts: every ancient tree adds a LOD1 part and 2 more collider boxes at join (kit trees have 1 collider, the re-fit has 3); colliders are never culled
    import verify_world_budget as vwb
    n = P['colossal']['Phone']['ancient_trees']
    join_fake = P['join_parts'] + n * 3
    phone_fake = ps['world_parts_lowpoly'] + n * 2 + (P['colossal']['Phone']['ceiling']['max_parts'] - P['colossal']['Phone']['standin_n'])
    cap_join, cap_phone = vwb.CAPS['playtest parts loaded at join'][0], vwb.CAPS['phone scene parts, worst spot'][0]
    print(f"  parts with fake ids: loaded at join {P['join_parts']:,} -> {join_fake:,} (cap {cap_join:,}); phone worst-spot scene {ps['world_parts_lowpoly']:,} -> {phone_fake:,} even at the ceiling radius (cap {cap_phone:,})")
    assert join_fake <= cap_join and phone_fake <= cap_phone, 'parts with fake ids must stay inside the recorded caps'
    print('C ok: fake ids are not heavier than the stand-ins at the worst spot, nor in total')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    static_checks()
    geometry_checks(run_luau(args.runner))
    budget_checks(args.runner)
    print('colossal LOD OK (offline; not a Studio or phone measurement)')
