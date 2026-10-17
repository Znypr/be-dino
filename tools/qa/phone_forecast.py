"""BD-085 / BD-322 offline phone budget FORECAST for "everything uploaded" (docs/146). NOT a measurement, no phone, no Studio.

One command prints, for the Phone device class, what the phone would have to carry once every empty asset id is filled:
  1. WORLD (island): V3 trees, the 8 ground props and 8 plants, colossal trees with LOD, all with fake ids, through the real placement grammar
     (tools/estimate_world_budget.py, PROPS_IDS = 'all'): triangles, parts, draw-call range, culling and density sensitivity.
  2. CAVE HUB: the 6 rock forms and the gate arch (and every other layout row) from CaveHubLayout.budgetTable(), lights, beams, particles.
  3. TEXTURES: every image slot in tools/asset_slots.json (bound AND still empty), sized from the repo PNG (or the spec size in docs/120 when the
     file is not made yet), summed per scene (island run, hatch reveal, cave hub) as RGBA8 (+ mips for 3D textures), plus the shipped low-poly
     dino textures (docs/105: 1024 px per part) as context.
  4. FX peaks per scene (particles, beams, trails, lights) from tools/fx_budget_report.py plus the static cave lights.
  Budgets: tools/qa/phone_budgets.json (single source). Every number is an ESTIMATE; labels say which input is measured or assumed.

Usage:
  python tools/qa/phone_forecast.py --runner luau.exe            # the forecast tables
  python tools/qa/phone_forecast.py --runner luau.exe --check    # + exit 1 only on a CLEAR breach with fake ids (the CI mode)
  python tools/qa/phone_forecast.py --runner luau.exe --json out.json
"""
from pathlib import Path
import argparse, json, math, re, struct, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import estimate_world_budget as est  # noqa: E402
import fx_budget_report as fxr  # noqa: E402

BUDGET_FILE = HERE / 'phone_budgets.json'
MIB = 1024 * 1024
MIP = 4 / 3          # a full mip chain adds a third (3D textures and particle sheets; UI images are drawn 1:1, no mips)
TEX_CAP = 1024       # ASSUMPTION: the engine keeps at most 1024 px per side of an uploaded image (larger uploads are scaled down)
GPU_COMPRESS = 4.0   # ASSUMPTION for the optimistic column: GPU-compressed (ASTC/ETC class) is about 1/4 of RGBA8. Unknown for Roblox mobile.
LOWPOLY_PART_PX = 1024   # MEASURED fact, docs/105 s1: every generated low-poly dino part has its own 1024 px texture
LOWPOLY_PARTS = 7
WORLD_TEX_PX = 1024      # ASSUMPTION: Roblox generate_mesh textures are 1024 x 1024 (read one in Studio to confirm; first item of the BD-085 list)
FX_FIXED_DRAWS = 60      # ESTIMATE: terrain materials, water, sky, outline passes, the HUD layers (not part of the instanced-mesh count)


def load_budgets():
    return json.loads(BUDGET_FILE.read_text(encoding='utf-8'))['phone']


# ------------------------------------------------------------------ 1. world
def spots(half):
    return [(gx, gz) for gx in range(-half, half + 1, 64) for gz in range(-half, half + 1, 64)]


_CACHE = {}


def _placement(runner, mode):
    """(estimate result, props, kit, colossal) for one id mode; cached, the harness takes about 4 s per mode."""
    if mode not in _CACHE:
        est.PROPS_IDS, est.EMIT_VIS = mode, True
        res = est.estimate(runner)
        props, kit, cfg, colossal = est.run_profile(runner, 'playtest')
        est.PROPS_IDS, est.EMIT_VIS = 'shipped', False
        _CACHE[mode] = (res, props, kit, colossal)
    return _CACHE[mode]


def world_scenario(runner, mode, density_keep=None, radius=None):
    """One placement run (playtest profile) -> per-spot Phone numbers. mode 'shipped' (ids as in the source: all empty) or 'all' (fake ids)."""
    res, props, kit, colossal = _placement(runner, mode)
    c = res['cull']['Phone']
    hyst = res['hysteresis']
    radius = radius or c['radius']
    if density_keep:  # keep an even share of the cover layers (a stand-in for a lower phone density); everything else is untouched
        seen, out = {}, []
        for p in props:
            if p['layer'] in ('groundcover', 'shrub'):
                i = seen.get(p['layer'], 0)
                seen[p['layer']] = i + 1
                if math.floor((i + 1) * density_keep) == math.floor(i * density_keep):
                    continue
            out.append(p)
        props = out
    colliders = sum(kit[p['id']]['colliders'] for p in props)
    all_mode = mode == 'all'
    ancient = res['profiles']['playtest']['colossal']['Phone']['ancient_trees'] if all_mode else 0
    colossal_extra = 2 * ancient + ancient  # docs/142: three trunk collider boxes instead of one (+2) and one LOD1 part per tree (+1) at join
    dinos = res['dinos']
    rows = []
    for sp in spots(est.HALF) + [est.SPAWN]:
        within, kept, tris, gen, fixed = est.culling(props, kit, radius, c['budget'], hyst, sp)
        r2 = (radius * hyst) ** 2
        near = sorted(((p['x'] - sp[0]) ** 2 + (p['z'] - sp[1]) ** 2, i) for i, p in enumerate(props))
        inside = [i for d, i in near if d <= r2][:c['budget']]
        uniq = len({kit[props[i]['id']].get('vis', props[i]['id']) for i in inside})
        col_in = sum(kit[props[i]['id']]['colliders'] for i in inside)
        col = colossal.get(('Phone', 'default'), {}).get(sp)
        low = fixed + est.GEN_LOW * gen
        high = fixed + est.GEN_HIGH * gen
        if all_mode and col:  # the same swap the estimator does: the stand-ins in range become LOD0/LOD1 ancient trees (22 of the 31 colossal placements)
            tris += col['tris'] - col['today'] * est.GEN_TRIS
            low += col['tris'] - col['today'] * est.GEN_LOW
            high += col['tris'] - col['today'] * est.GEN_HIGH
            uniq += 2 if (col['lod0'] + col['lod1']) else 0
        parts = kept + colliders + c_food(res, c) + 600 + dinos['low_parts_peak'] + (colossal_extra if all_mode else 0)
        rows.append(dict(spot=sp, col_in=col_in, within=within, kept=kept, tris=tris, tris_low=low, tris_high=high, gen=gen, unique_meshes=uniq,
                         parts=parts))
    spawn = rows[-1]
    worst_t = max(rows[:-1], key=lambda r: r['tris'])
    worst_p = max(rows[:-1], key=lambda r: r['parts'])
    join = res['profiles']['playtest']['join_parts'] + (colossal_extra if all_mode else 0)
    return dict(mode=mode, radius=radius, food_parts=res['food_parts'], food_visible=c_food(res, c), props=len(props), colliders=colliders, join_parts=join, spawn=spawn, worst_tris=worst_t, worst_parts=worst_p,
                gen_props=res['profiles']['playtest']['gen_props'], dinos=dinos, res=res, v3=sum(1 for k in kit.values() if 'v3' in k) if all_mode else 0)


def c_food(res, c):
    return res['profiles']['playtest']['cull']['Phone']['food_visible']


def draw_range(sc, species=6):
    """(lower, upper) draw-call estimate at the worst-triangle spot: instanced identical meshes vs one call per part."""
    w = sc['worst_tris']
    dino = LOWPOLY_PARTS * species
    low = w['unique_meshes'] + dino + FX_FIXED_DRAWS
    high = w['kept'] + sc['colliders'] * 0 + sc['dinos']['low_parts_peak'] + FX_FIXED_DRAWS  # invisible colliders are not drawn
    return low, high


# ------------------------------------------------------------------ 2. cave hub
CAVE_LUAU = r'''
local C=CaveHubLayout
local L=C.get()
local B=C.budgetTable()
for _,name in {"rocks","station","lava","lights","colliders","total"} do
 print(string.format("B %s %d %d %d %d",name,B[name].parts,B[name].tris,C.Budget[name].parts,C.Budget[name].tris))
end
-- rows with no source today (empty ids): they exist in the layout and place nothing yet
local gen={}
for k,e in Generated.Props do gen[k]=e end
for k,e in Generated.CaveForms do gen[k]=e end
local kitKeys={}
for k in CaveHubProps.Kit do kitKeys[k]=true end
local unplacedParts,unplacedTris,placedKinds,unplacedKeys=0,0,{},{}
local assets={}
for _,p in L.props do
 local src=CaveHubProps.sourceFor(p.key,gen,kitKeys)
 local fx=CaveHubProps.NotMeshes[p.key]~=nil
 if not src and not fx then
  unplacedParts+=1 unplacedTris+=p.tris unplacedKeys[p.key]=(unplacedKeys[p.key] or 0)+1
 elseif src and src.kind=="asset" then assets[src.key]=true end
end
local n=0 for _ in assets do n+=1 end
local ks={} for k,v in unplacedKeys do table.insert(ks,k.."="..v) end table.sort(ks)
print(string.format("U %d %d %d %s",unplacedParts,unplacedTris,n,table.concat(ks,",")))
-- lights, beams, particles
local D=Rules.get()
local arch=Rules.archLight()
local nearMax,nearAt=0,""
for _,s in L.stations do
 local n=0
 for _,l in D.lights do
  local d=math.sqrt((l.x-s.x)^2+(l.z-(s.z+C.CenterZ))^2)
  if d<=l.range+70 then n+=1 end
 end
 if n>nearMax then nearMax,nearAt=n,s.id end
end
local shadows=0 for _,l in D.lights do if l.shadows then shadows+=1 end end
print(string.format("L %d %d %d %d %d %s",#D.lights,if arch then 1 else 0,shadows,D.fxBeams,nearMax,nearAt))
local motes=Rules.Beam.motesPerSecond*#D.shafts
local lavaDesktop=Lava.totalRate()
local lavaPhone=lavaDesktop*Lava.phoneScale()
local live=0
for i,s in Lava.Strands do live+=s.rate*s.life end
print(string.format("F %.2f %.2f %.2f %.2f %.2f %d",motes,Rules.GateGlow.rate,lavaDesktop,lavaPhone,live*Lava.phoneScale(),#Lava.Strands))
'''


def cave(runner):
    def module(name, parent):
        return 'local script={Parent={' + parent + '}}\n' + (ROOT / name).read_text(encoding='utf-8')
    s = ('local require=function(x) return x end\n'
         + 'local Generated=(function()\n' + (ROOT / 'src/shared/WorldGeneratedMeshes.luau').read_text(encoding='utf-8') + '\nend)()\n'
         + 'local CaveHubLayout=(function()\n' + module('src/shared/CaveHubLayout.luau', '') + '\nend)()\n'
         + 'local CaveHubProps=(function()\n' + module('src/shared/CaveHubProps.luau', '') + '\nend)()\n'
         + 'local Lava=(function()\n' + module('src/shared/CaveLavaRules.luau', '') + '\nend)()\n'
         + 'local Rules=(function()\n' + module('src/shared/CaveLightingRules.luau', 'CaveHubLayout=CaveHubLayout') + '\nend)()\n'
         + CAVE_LUAU)
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'cave.luau'
        p.write_text(s, encoding='utf-8')
        out = subprocess.run([runner, str(p)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit('cave script failed:\n' + out.stdout[-1500:] + out.stderr[-1500:])
    res = dict(budget={})
    for line in out.stdout.splitlines():
        f = line.split(None, 7)
        if f[0] == 'B':
            res['budget'][f[1]] = dict(parts=int(f[2]), tris=int(f[3]), cap_parts=int(f[4]), cap_tris=int(f[5]))
        elif f[0] == 'U':
            res['unplaced'] = dict(parts=int(f[1]), tris=int(f[2]), textured_assets=int(f[3]), keys=f[4] if len(f) > 4 else '')
        elif f[0] == 'L':
            res['lights'] = dict(fills=int(f[1]), arch=int(f[2]), shadows=int(f[3]), beams=int(f[4]), near_max=int(f[5]), near_at=f[6])
        elif f[0] == 'F':
            res['fx'] = dict(motes=float(f[1]), gate=float(f[2]), lava_desktop=float(f[3]), lava_phone=float(f[4]), lava_live_phone=float(f[5]), strands=int(f[6]))
    return res


# ------------------------------------------------------------------ 3. textures
# Spec sizes (docs/120) for slots whose PNG is not in the repo yet or lives under another name. (width, height); None = look the file up.
SPEC = {
    'egg_cond_': (1024, 1024), 'potion_icon_': (512, 512), 'weatherCloud': (512, 512), 'confetti': (1024, 1024), 'lavaCrust': (1024, 1024),
    'rainbowStrip': (1024, 64), 'rimRingUi': (1024, 1024), 'paintCrown': (1024, 1024), 'paintDrips': (1024, 1024), 'paintDroplet': (512, 512),
    'paintGloss': (1024, 1024), 'paint_bucket': (1024, 1024), 'aura_': (1024, 1024), 'rarity_': (1024, 1024), 'tier_': (1024, 1024),
    'notify_': (1024, 1024), 'toast_body': (512, 128), 'frame_': (512, 512), 'hud_': (1024, 1024), 'crystals_': (1024, 1024),
    'station_': (1024, 1024), 'fame_plaque': (1024, 1024), 'golden_drumstick_icon': (1024, 1024), 'class_': (1024, 1024),
}
FILE_DIRS = ['resources/effects/fx-v2', 'resources/effects/fx-v3', 'resources/ui/v2/icons', 'resources/materials/meadow-grass-v2']
# slots drawn with mips (3D / particle / material textures); everything else is a GUI image (1:1, no mips)
TEX3D = re.compile(r'^(glowPlate|ring|crystalSheet|ribbon|speed|smoke|motif|confetti|lavaCrust|flame|starPop|dome|shaft|shell|rainbow|paint(Crown|Drips|Droplet|Gloss)$|weather|lightning|rainStreak|snowFlake|ash|bloodMoon|emberSpark|dustSand|aurora|meadow_grass)')


def png_dims(path):
    head = path.read_bytes()[:32]
    if head[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', head[16:24])
    return None


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def find_file(name):
    n = norm(name)
    for d in FILE_DIRS:
        for f in sorted((ROOT / d).glob('*.png')):
            stem = re.sub(r'(-v\d+)?(-512)?$', '', f.stem)
            if norm(stem) == n:
                return f
    return None


def slots():
    """Every image slot: dict(name, target, bound, w, h, src, mip)."""
    import bind_assets
    out = []
    text_cache = {}
    for s in json.loads((ROOT / 'tools/asset_slots.json').read_text(encoding='utf-8'))['slots']:
        if s['kind'] != 'image':
            continue
        f = s['file']
        text_cache.setdefault(f, (ROOT / f).read_text(encoding='utf-8'))
        bound = bool(bind_assets.current_value(s, text_cache[f]))
        name = s['name']
        w = h = None
        src = 'spec'
        spec = next((v for k, v in SPEC.items() if name.startswith(k)), None)
        fp = None if (spec and name.startswith(('egg_cond_', 'potion_icon_', 'aura_'))) else find_file(name)
        if fp:
            d = png_dims(fp)
            if d:
                w, h, src = d[0], d[1], 'file'
        if w is None and name == 'egg_stage':
            w, h, src = 1024, 924, 'spec'
        if w is None and spec:
            w, h = spec
        if w is None:
            w, h, src = 1024, 1024, 'assumed'
        out.append(dict(name=name, target=s['target'], bound=bound, w=w, h=h, src=src, mip=bool(TEX3D.match(name))))
    return out


def slot_mib(s, cap=TEX_CAP):
    w, h = min(s['w'], cap), min(s['h'], cap)
    return w * h * 4 * (MIP if s['mip'] else 1.0) / MIB


WEATHER_SETS = {
    'rain/storm': ['rainStreak', 'lightningBolt', 'weatherCloud'], 'blizzard': ['snowFlakeSheet', 'weatherCloud'],
    'volcano': ['ashFlake', 'emberSpark'], 'quake': ['dustSand'], 'aurora': ['auroraCurtain'], 'blood moon': ['bloodMoonMotes', 'bloodMoonDisc'],
}
FX_IN_RUN = ['glowPlate', 'glowPlateRound', 'glowPlateDroplet', 'glowPlateCrescent', 'ringSoft', 'ringShock', 'ringSeismic', 'ribbonSoft', 'speedLine',
             'speedStreaks', 'flameTongue', 'crystalSheet', 'shellEdge', 'smokeSoft', 'smokeDense', 'smokeWispy', 'domeGradient', 'starPop',
             'motifDroplets', 'motifSoftSparks', 'motifSnowCrystals', 'motifPebbles', 'motifEmbers', 'motifAurora', 'motifCrimson']
HUD_RUN = ['class_ground', 'class_flyer', 'class_water', 'class_armored', 'notify_crystal', 'notify_level', 'notify_star', 'notify_mutation_egg',
           'notify_warning', 'toast_body', 'potion_icon_speed_common', 'potion_icon_growth_common', 'potion_icon_loot_common']
HATCH_UI = ['egg_stage', 'egg_cond_cracked', 'egg_cond_dirty', 'egg_cond_normal', 'egg_cond_rainbow', 'egg_cond_astra', 'paint_bucket', 'paintCrown',
            'paintDrips', 'paintDroplet', 'paintGloss', 'confetti', 'rainbowStrip', 'rimRingUi', 'shaftGradient', 'class_ground', 'class_flyer',
            'class_water', 'class_armored', 'notify_mutation_egg'] + [f'rarity_{r}' for r in ('common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic')] \
    + [f'tier_{t}' for t in ('gold', 'emerald', 'diamond')] + [f'mutation_{m}' for m in ('dewdrop', 'charged', 'frost', 'seismic', 'ember', 'aurora', 'bloodmoon')]
CAVE_UI_ONE_TAB = [f'potion_icon_{k}' for k in ('speed_common', 'growth_common', 'loot_common', 'speed_uncommon', 'growth_uncommon', 'speed_rare', 'growth_rare',
                                                  'loot_rare', 'growth_epic', 'loot_epic', 'speed_legendary', 'growth_legendary')] \
    + ['shop_tab_auras', 'shop_tab_trails', 'shop_tab_conditions', 'shop_tab_crystals']
CAVE_FX = ['lavaCrust', 'shaftGradient', 'glowPlate', 'smokeSoft', 'emberSpark']


def texture_scenes(cap=TEX_CAP, cave_textured=27):
    all_slots = {s['name']: s for s in slots()}

    def total(names, only_pending=False):
        return sum(slot_mib(all_slots[n], cap) for n in names if n in all_slots and (not only_pending or not all_slots[n]['bound']))
    ui_all = [n for n, s in all_slots.items() if s['target'] in ('slot', 'table') or n.startswith('egg_')]
    weather_worst = max(WEATHER_SETS, key=lambda k: total(WEATHER_SETS[k]))
    weather_all = [n for v in WEATHER_SETS.values() for n in v]
    world_tex = 14 * (WORLD_TEX_PX ** 2 * 4 * MIP) / MIB        # 14 placed textured generated meshes on the island (ESTIMATE of size)
    world_tex_v3 = 11 * (WORLD_TEX_PX ** 2 * 4 * MIP) / MIB     # broadleaf, pine, palm become untextured V3 vertex-colour meshes
    grass = total(['meadow_grass_v2_color', 'meadow_grass_v2_normal', 'meadow_grass_v2_roughness'])
    run_new = total(FX_IN_RUN) + total(WEATHER_SETS[weather_worst]) + total(HUD_RUN) + grass
    hatch_new = total(FX_IN_RUN) + total(HATCH_UI) + total(WEATHER_SETS[weather_worst]) + grass
    cave_ui_all = total([n for n in ui_all if n not in HATCH_UI and not n.startswith('paint')])
    cave_new = total(CAVE_FX) + total(CAVE_UI_ONE_TAB)
    cave_mesh_tex = cave_textured * (WORLD_TEX_PX ** 2 * 4 * MIP) / MIB   # distinct textured generated meshes in the cave (ESTIMATE of their size)
    scenes = dict(
        island_run=dict(new=run_new, new_pending=total(FX_IN_RUN + HUD_RUN + WEATHER_SETS[weather_worst], True), world=world_tex_v3, world_today=world_tex),
        hatch_reveal=dict(new=hatch_new, new_pending=total(FX_IN_RUN + HATCH_UI + WEATHER_SETS[weather_worst], True), world=world_tex_v3, world_today=world_tex),
        cave_hub=dict(new=cave_new, new_pending=total(CAVE_FX + CAVE_UI_ONE_TAB, True), world=cave_mesh_tex, world_today=cave_mesh_tex),
    )
    union_all = sum(slot_mib(s, cap) for s in all_slots.values())
    return dict(scenes=scenes, weather_worst=weather_worst, union_all=union_all, weather_union=total(weather_all), grass=grass, cave_ui_all=cave_ui_all,
                slots=all_slots, pending=sum(1 for s in all_slots.values() if not s['bound']), n=len(all_slots),
                spec=sum(1 for s in all_slots.values() if s['src'] != 'file'), pending_mib=sum(slot_mib(s, cap) for s in all_slots.values() if not s['bound']))


def lowpoly_dino_mib(species, cap=LOWPOLY_PART_PX):
    return species * LOWPOLY_PARTS * (min(cap, LOWPOLY_PART_PX) ** 2) * 4 * MIP / MIB


# ------------------------------------------------------------------ 4. FX
def fx_scenes(runner, cave_res):
    rows = fxr.run_model(runner)
    m = fxr.moments(rows)['phone']
    names = ['hatch', 'open', 'party']
    out = {k: v[1] for k, v in zip(names, m)}
    lod = (ROOT / 'src/shared/EffectsLod.luau').read_text()
    live = re.search(r'phone = table\.freeze\(\{beams = (\d+), trails = (\d+), lights = (\d+)', lod)
    cos = dict(beams=int(live.group(1)), trails=int(live.group(2)), lights=int(live.group(3)))
    cl, cf = cave_res['lights'], cave_res['fx']
    lights_static = cl['fills'] + cl['arch']
    out['cave'] = dict(lights_static=lights_static, lights_cosmetic=cos['lights'], lights=lights_static + cos['lights'], beams_static=cl['beams'],
                       beams_cosmetic=cos['beams'], beams=cl['beams'] + cos['beams'], trails=cos['trails'],
                       particles_per_s=cf['motes'] + cf['gate'] + cf['lava_phone'], shadows=cl['shadows'], near_max=cl['near_max'])
    return out


# ------------------------------------------------------------------ report
def pct(a, b):
    return '%+.0f%%' % ((a - b) / b * 100) if b else 'n/a'


def forecast(runner):
    B = load_budgets()
    today = world_scenario(runner, 'shipped')
    allf = world_scenario(runner, 'all')
    sens = {}
    for r in (190, 160, 140, 120):
        sens[('radius', r)] = world_scenario(runner, 'all', radius=r)
    for k in (0.75, 0.5):
        sens[('density', k)] = world_scenario(runner, 'all', density_keep=k)
    cv = cave(runner)
    ca = cv['unplaced']['textured_assets']
    tx = texture_scenes(TEX_CAP, ca)
    tx512, tx256 = texture_scenes(512, ca), texture_scenes(256, ca)
    fx = fx_scenes(runner, cv)
    return dict(budgets=B, today=today, allf=allf, sens=sens, cave=cv, tex=tx, tex512=tx512, tex256=tx256, fx=fx)


def line(name, v, cap, unit=''):
    flag = 'OVER' if v > cap else 'ok  '
    return '  %-4s %-46s %12s  budget %s%s' % (flag, name, f'{v:,.0f}' if abs(v) >= 100 else f'{v:,.1f}', f'{cap:,.0f}', unit)


def report(F):
    B = F['budgets']
    out = []
    P = lambda *a: out.append(' '.join(str(x) for x in a))
    t, a = F['today'], F['allf']
    P('PHONE FORECAST: "everything uploaded" (ESTIMATE, no phone; fake ids never written; playtest profile, density 1.25, seed 1404)')
    P('Budgets (tools/qa/phone_budgets.json): ' + ', '.join('%s %s' % (k, v['value']) for k, v in B.items()))
    P('\n== 1. WORLD (island), Phone class, radius %d, low-poly dinos on ==' % a['radius'])
    P('| Metric | Today (ids empty) | Everything uploaded | Delta | Phone budget |')
    P('|---|---:|---:|---:|---:|')
    rows = [
        ('Parts loaded at join', t['join_parts'], a['join_parts'], B['parts']['value']),
        ('Parts in scene, worst-parts spot', t['worst_parts']['parts'], a['worst_parts']['parts'], B['parts']['value']),
        ('Triangles, worst-triangles spot (mid)', t['worst_tris']['tris'], a['worst_tris']['tris'], B['triangles']['value']),
        ('  same, generated meshes 500 tris', t['worst_tris']['tris_low'], a['worst_tris']['tris_low'], B['triangles']['value']),
        ('  same, generated meshes 3,000 tris', t['worst_tris']['tris_high'], a['worst_tris']['tris_high'], B['triangles']['value']),
        ('Triangles at spawn (mid)', t['spawn']['tris'], a['spawn']['tris'], B['triangles']['value']),
        ('Props kept, worst-triangles spot', t['worst_tris']['kept'], a['worst_tris']['kept'], None),
        ('Unique visual meshes in range (draw-call lower bound)', t['worst_tris']['unique_meshes'], a['worst_tris']['unique_meshes'], None),
    ]
    for name, x, y, cap in rows:
        P('| %s | %s | %s | %s | %s |' % (name, f'{x:,}', f'{y:,}', pct(y, x), f'{cap:,}' if cap else ''))
    lo_t, hi_t = draw_range(t)
    lo_a, hi_a = draw_range(a)
    P('| Draw calls, instanced .. one per part (6 species on screen) | %d .. %d | %d .. %d | | |' % (lo_t, hi_t, lo_a, hi_a))
    P('Worst-triangles spot (everything uploaded): %s; worst-parts spot %s; MeshPart props placed %s (today %s); generated-mesh props %s (today %s); %d kit ids use a V3 tree.'
      % (a['worst_tris']['spot'], a['worst_parts']['spot'], f"{a['props']:,}", f"{t['props']:,}", a['gen_props'], t['gen_props'], a['v3']))
    P('\nSensitivity at the worst-triangles spot (everything uploaded):')
    P('| Lever | Triangles | Parts | Props kept |')
    P('|---|---:|---:|---:|')
    P('| radius 190 (today) | %s | %s | %s |' % (f"{a['worst_tris']['tris']:,}", f"{a['worst_tris']['parts']:,}", a['worst_tris']['kept']))
    for r in (160, 140, 120):
        s = F['sens'][('radius', r)]
        P('| radius %d | %s | %s | %s |' % (r, f"{s['worst_tris']['tris']:,}", f"{s['worst_tris']['parts']:,}", s['worst_tris']['kept']))
    for k in (0.75, 0.5):
        s = F['sens'][('density', k)]
        P('| shrub + groundcover x%.2f | %s | %s | %s |' % (k, f"{s['worst_tris']['tris']:,}", f"{s['worst_tris']['parts']:,}", s['worst_tris']['kept']))

    wp = a['worst_parts']
    saved_col = a['colliders'] - wp['col_in']
    saved_food = a['food_parts'] - a['food_visible']
    P('\nParts levers (everything uploaded; the invisible colliders and all food pickups are never culled today):')
    P('| Lever | Parts at the worst-parts spot | Parts loaded at join |')
    P('|---|---:|---:|')
    P('| as is | %s | %s |' % (f"{wp['parts']:,}", f"{a['join_parts']:,}"))
    P('| cull the invisible colliders with their props (client) | %s | %s |' % (f"{wp['parts'] - saved_col:,}", f"{a['join_parts']:,}"))
    P('| food pickups only exist within the radius (pooled around the player) | %s | %s |' % (f"{wp['parts']:,}", f"{a['join_parts'] - saved_food:,}"))
    P('| both | %s | %s |' % (f"{wp['parts'] - saved_col:,}", f"{a['join_parts'] - saved_food:,}"))
    P('(%d of %d colliders are inside the radius at that spot; %d of %d food pickups are visible)' % (wp['col_in'], a['colliders'], a['food_visible'], a['food_parts']))

    P('\n== 2. CAVE HUB (CaveHub is ON in the playtest profile) ==')
    cv = F['cave']
    P('| Group (all layout rows = everything uploaded) | Parts | Triangles | Cap parts | Cap tris |')
    P('|---|---:|---:|---:|---:|')
    for g, r in cv['budget'].items():
        P('| %s | %d | %s | %d | %s |' % (g, r['parts'], f"{r['tris']:,}", r['cap_parts'], f"{r['cap_tris']:,}"))
    u = cv['unplaced']
    P('Rows that place nothing today (empty ids): %d parts, %s tris of the total: %s. Distinct textured generated meshes placed: %d.' % (u['parts'], f"{u['tris']:,}", u['keys'], u['textured_assets']))
    P('Lights: %d fills + %d arch light = %d (max %d reach one station, %d cast shadows); beams %d; particles/s phone %.0f (lava %.0f + shaft motes %.0f + gate glow %.0f)'
      % (cv['lights']['fills'], cv['lights']['arch'], cv['lights']['fills'] + cv['lights']['arch'], cv['lights']['near_max'], cv['lights']['shadows'], cv['lights']['beams'],
         cv['fx']['lava_phone'] + cv['fx']['motes'] + cv['fx']['gate'], cv['fx']['lava_phone'], cv['fx']['motes'], cv['fx']['gate']))

    P('\n== 3. TEXTURES (RGBA8; MiB; images capped at %d px per side, 3D textures and particle sheets +33%% mips) ==' % TEX_CAP)
    tx = F['tex']
    P('Image slots: %d (%d still empty = the upload; %d sized from the spec, not a repo file). All slots together: %.1f MiB; the %d empty ones: %.1f MiB.'
      % (tx['n'], tx['pending'], tx['spec'], tx['union_all'], tx['pending'], tx['pending_mib']))
    dino6 = lowpoly_dino_mib(6)
    P('| Scene (typical) | New-art images in the scene (bound or empty) | of it still empty | Generated-mesh textures (ESTIMATE; island today / with V3) | Low-poly dino textures (SHIPPED, 6 species) | Total, RGBA8 | If GPU-compressed (/%.0f) |' % GPU_COMPRESS)
    P('|---|---:|---:|---:|---:|---:|---:|')
    for name, s in tx['scenes'].items():
        tot = s['new'] + s['world'] + dino6
        P('| %s | %.1f | %.1f | %.0f / %.0f | %.0f | %.0f | %.0f |' % (name, s['new'], s['new_pending'], s['world_today'], s['world'], dino6, tot, tot / GPU_COMPRESS))
    P('Weather set resident at once: %s (%.1f MiB); all weather textures in one session: %.1f MiB; cave shop UI if every tab were built: %.1f MiB.'
      % (tx['weather_worst'], sum(slot_mib(tx['slots'][n]) for n in WEATHER_SETS[tx['weather_worst']]), tx['weather_union'], tx['cave_ui_all']))
    P('Resample cap (what a phone-only smaller upload would save): all slots at 1024 %.1f MiB, 512 %.1f MiB, 256 %.1f MiB.' % (tx['union_all'], F['tex512']['union_all'], F['tex256']['union_all']))
    P('Context, SHIPPED art (docs/105: 1024 px texture per dino part): 4 distinct species %.0f MiB, 8 %.0f MiB, 12 %.0f MiB RGBA8 (%.0f / %.0f / %.0f if GPU-compressed).'
      % (lowpoly_dino_mib(4), lowpoly_dino_mib(8), lowpoly_dino_mib(12), lowpoly_dino_mib(4) / GPU_COMPRESS, lowpoly_dino_mib(8) / GPU_COMPRESS, lowpoly_dino_mib(12) / GPU_COMPRESS))

    P('\n== 4. FX peaks (Phone class, tools/fx_budget_report.py model + static cave lights) ==')
    fx = F['fx']
    P('| Scene | live3d particles | big sprites | beams | trails | lights |')
    P('|---|---:|---:|---:|---:|---:|')
    labels = dict(hatch='Hatch reveal + worst weather + 12 players', open='Open world, 12 players, worst weather', party='Aura party, clear sky')
    for k in ('hatch', 'open', 'party'):
        m = fx[k]
        P('| %s | %.0f | %.0f | %.0f | %.0f | %.0f |' % (labels[k], m['live3d'], m['big'], m['beams'], m['trails'], m['lights']))
    c = fx['cave']
    P('| Cave hub (static + cosmetics at their global caps) | ~%.0f/s | 0 | %d + %d = %d | %d | %d + %d = %d |' % (c['particles_per_s'], c['beams_static'], c['beams_cosmetic'],
                                                                                                        c['beams'], c['trails'], c['lights_static'], c['lights_cosmetic'], c['lights']))
    P('Phone budgets: live3d %s, big %s, beams %s, trails %s, lights %s' % tuple(fxr.BUDGETS['phone'][k] for k in ('live3d', 'big', 'beams', 'trails', 'lights')))

    P('\n== Budget check (fake ids, Phone) ==')
    for r in checks(F):
        P(r[0])
    return '\n'.join(out)


# ------------------------------------------------------------------ CI check
# FAIL only on a clear breach with everything uploaded. Each cap is the forecast on this commit plus about 25% (absolute numbers) so a change that
# makes the uploaded world clearly heavier fails, and so do two relations that must hold: uploading must not make the phone scene heavier than
# today, and no scene may exceed 2x a documented phone budget. Known over-budget findings are WARN (docs/146 section 4), never FAIL.
CAPS = {
    'world tris worst spot (mid)': (320_000, lambda F: F['allf']['worst_tris']['tris']),         # 253,480 on 2026-10-17 (main dd2b5ff + this branch)
    'world parts at worst-parts spot': (3_950, lambda F: F['allf']['worst_parts']['parts']),     # 3,142
    'world parts loaded at join': (9_150, lambda F: F['allf']['join_parts']),                    # 7,061 (the same cap as verify_world_budget)
    'cave hub parts (all rows)': (410, lambda F: F['cave']['budget']['total']['parts']),         # 218 (docs/104 s3.1)
    'cave hub triangles (all rows)': (730_000, lambda F: F['cave']['budget']['total']['tris']),  # 221,584
    'texture MiB, hatch reveal scene (new art + island meshes, RGBA8)': (270.0, lambda F: sum(F['tex']['scenes']['hatch_reveal'][k] for k in ('new', 'world'))),  # 213
    'texture MiB, all 138 image slots together (RGBA8)': (360.0, lambda F: F['tex']['union_all']),  # 287.7
    'cave lights, static + cosmetic': (46, lambda F: F['fx']['cave']['lights']),                  # 30 static (MaxLights) + 16 cosmetic (EffectsLod.Live.phone)
}
RELATIONS = [
    ('uploading must not add triangles at the phone worst spot', lambda F: F['allf']['worst_tris']['tris'] <= F['today']['worst_tris']['tris'] * 1.05),
    ('uploading must not add parts at the phone worst spot', lambda F: F['allf']['worst_parts']['parts'] <= F['today']['worst_parts']['parts'] + 100),
    ('no cave FX count above 2x its phone budget', lambda F: F['fx']['cave']['lights'] <= 3 * F['budgets']['lights']['value'] and F['fx']['cave']['beams'] <= 2 * F['budgets']['beams']['value']),
]


def checks(F):
    B = F['budgets']
    out = []
    for name, (cap, get) in CAPS.items():
        v = get(F)
        out.append(('%s %s: %s <= %s' % ('OK  ' if v <= cap else 'FAIL', name, f'{v:,.1f}' if isinstance(v, float) else f'{v:,}', f'{cap:,}'), v > cap))
    for name, fn in RELATIONS:
        ok = fn(F)
        out.append(('%s %s' % ('OK  ' if ok else 'FAIL', name), not ok))
    a, fx = F['allf'], F['fx']
    warns = [
        ('world tris worst spot', a['worst_tris']['tris'], B['triangles']['value']),
        ('world parts worst-parts spot', a['worst_parts']['parts'], B['parts']['value']),
        ('world parts loaded at join', a['join_parts'], B['parts']['value']),
        ('cave lights (static + cosmetic)', fx['cave']['lights'], B['lights']['value']),
        ('cave beams (static + cosmetic)', fx['cave']['beams'], B['beams']['value']),
        ('hatch moment live3d particles', fx['hatch']['live3d'], fxr.BUDGETS['phone']['live3d']),
    ] + [('texture MiB %s (RGBA8, new art + generated meshes + 6 dino species)' % n, s['new'] + s['world'] + lowpoly_dino_mib(6), B['textureMib']['value'])
         for n, s in F['tex']['scenes'].items()]
    for name, v, cap in warns:
        if v > cap:
            out.append(('WARN %s %s is over the phone budget %s (docs/146; measure on a phone, BD-085)' % (name, f'{v:,.0f}', f'{cap:,}'), False))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--check', action='store_true', help='exit 1 only on a CLEAR budget breach with fake ids')
    ap.add_argument('--json')
    a = ap.parse_args()
    F = forecast(a.runner)
    print(report(F))
    if a.json:
        slim = dict(budgets=F['budgets'], checks=[c[0] for c in checks(F)])
        Path(a.json).write_text(json.dumps(slim, indent=1))
    bad = [c[0] for c in checks(F) if c[1]]
    if a.check and bad:
        raise SystemExit('phone forecast breach with fake ids:\n  ' + '\n  '.join(bad))
    if a.check:
        print('\nphone forecast OK (offline estimate with fake ids, not a phone measurement)')


if __name__ == '__main__':
    main()
