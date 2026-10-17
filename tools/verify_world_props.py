"""BD-463 / BD-464 step 2 offline gate: the Blender plants and ground props appear the moment their asset ids are pasted, and NOT before.

Runs the real placement grammar (same harness as estimate_world_budget.py, playtest profile, density 1.25, seed 1404) with three id sets:
  EMPTY  every WorldGeneratedMeshes.Props assetId blank (what ships today). Must be byte-identical to the grammar before BD-463: the placement
         list is pinned by a digest (LEGACY below, taken from origin/main before this change), and equals the run with options.props = nil
         and the run with invalid ids (typos, short numbers).
  FAKE   every id filled with a made-up numeric id (never written to a file). The new props must appear (all 16 keys), REPLACE small clutter
         (fewer placements and parts, about 6 old grass placements per tuft, 8 old flowers per cluster), the phone triangle estimate must not
         go up (worst spot of the estimator AND the maximum over a 32 stud grid, at the low / mid / high generated-mesh estimates), and every new
         prop keeps the lanes: routes, keep-outs, spawn clear radius, water, arena edge, sanctuary, clearings (solid ones), ground contact and the
         BD-473 height bands. The same fake-id placement is also run through verify_vegetation_layers.py and verify_world_overlap.py (--fake-ids).
  PARTIAL  only one plant and only one ground prop live: only those keys appear and the budget still does not go up.
Not Studio evidence and not a phone measurement. Usage: python tools/verify_world_props.py --runner luau.exe
"""
from pathlib import Path
import argparse, hashlib, math, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_world_budget as est

# sha256 of the placement dump ("D" lines, %.4f) of the grammar WITHOUT BD-463/464 (origin/main 212f704), per profile, and the placement count.
# If a later change to BiomePlacement alters the old grammar ON PURPOSE, re-run this verifier, check the diff is intended and update these pins.
LEGACY = {
    'default': (2859, 'cfe3e3eecaa76a691e17cdcb460e0d60e3cdeeba4c2b7f33c31f9c6ba4efba61'),
    'playtest': (3569, 'f49e9cf96ea0798c5b3913a679a28ca14c0e7632d2bcb38195294616e7d4097c'),
}
GEN_LEVELS = {'low': est.GEN_LOW, 'mid': est.GEN_TRIS, 'high': est.GEN_HIGH}
PLANT_KEYS = ['plant_grass_broad_v3', 'plant_grass_arch_v3', 'plant_grass_low_v3', 'plant_jungle_leaf_v3', 'plant_flowers_daisy_v3',
              'plant_flowers_yellow_v3', 'plant_flowers_red_v3', 'plant_fern_arch_v3']
GROUND_KEYS = ['ground_rock_small_v3', 'ground_rock_medium_v3', 'ground_rock_mossy_v3', 'ground_log_fallen_v3', 'ground_stump_roots_v3',
               'ground_mushrooms_v3', 'ground_bush_round_v3', 'ground_bush_berry_v3']
ALL_KEYS = PLANT_KEYS + GROUND_KEYS
SMALL = (4.0, 12.0)  # BD-473 Small band
SPAWN_CLEAR = 34.0   # BiomePlacement.SmallBand.spawnClear

DUMP = r'''
local Clears=Biome.clearings({seed=Config.WorldArtSeed,density=DENSITY,extent=Config.ArenaHalfWidth,height=Layout.height,kit=Kit,meshes=Meshes,map=BiomeMap,layout=Layout})
local SR=Biome.Sanctuary
local G=Biome.Ground
for _,p in a do
 print(string.format("P %s %s %.2f %.2f %s",p.layer,p.id,p.x,p.z,p.biome))
 print(string.format("D %s %s %.4f %.4f %.4f %.4f %.4f %.4f %.4f %s",p.layer,p.id,p.x,p.y,p.z,p.yaw,p.roll,p.scale,p.radius,p.biome))
 local spec=Biome.NewProps[p.id]
 if spec then
  local d=Kit[p.id]
  local ground=Layout.height(p.x,p.z)
  local groundOk=1
  if G.Raised[p.layer] and d.kind~="rock" then
   local hs={}
   for _,pt in G.samplePoints(p.x,p.z,G.trunkRadius(d,p.scale,p.radius*.5)) do table.insert(hs,Layout.height(pt[1],pt[2])) end
   local hi=-math.huge for _,h in hs do hi=math.max(hi,h) end
   if G.submerged(p.y,hs,1e-6) or p.y-hi>G.Clearance+1e-6 or math.abs(p.y-G.restY(p.layer,hs,d.extent[2],p.scale))>1e-6 then groundOk=0 end
  else
   if p.y>ground+1e-6 or ground-p.y>math.max(2.5,d.extent[2]*p.scale*.42) then groundOk=0 end
  end
  local half=p.radius
  local sanct=if p.x+half<SR.minX or p.x-half>SR.maxX or p.z+half<SR.minZ or p.z-half>SR.maxZ then 0 else 1
  print(string.format("Q\t%s\t%s\t%.3f\t%.3f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%d\t%.3f\t%d\t%d\t%.3f\t%d\t%d\t%d",p.id,p.layer,p.x,p.z,p.radius,d.extent[2]*p.scale,
   Biome.pathClearance(p.x,p.z),Biome.keepOutClearance(p.x,p.z,true),Biome.keepOutClearance(p.x,p.z,false),
   if Layout.inPool(p.x,p.z,0) then 1 else 0,math.sqrt(p.x^2+(p.z-30)^2),if Layout.inPool(p.x,p.z,1) then 1 else 0,
   if Biome.inClearing(Clears,p.x,p.z,0) then 1 else 0,math.max(math.abs(p.x),math.abs(p.z))+p.radius,sanct,groundOk,#d.colliders))
 end
end
for id,d in Kit do
 local gen=(Generated.KitMap[id]~=nil or Generated.BareIds[id]~=nil)
 print(string.format("K %s %d %d %d",id,d.triangles,#d.colliders,if gen then 1 else 0))
end
'''


def run(runner, ids, profile='playtest', only=None, props_nil=False, invalid=False):
    """-> dict(props=[est props], kit, digest, count, q=[new-prop detail rows])."""
    est.PROPS_IDS = ids
    est.DUMP = DUMP
    text = (est.ROOT / 'src/shared/Config.luau').read_text()
    cfg = est.release_profiles.apply_profile(text, 'playtest')[0] if profile == 'playtest' else text
    src = est.luau_script(cfg, profile == 'playtest')
    if only is not None:  # fake ids for these keys only, every other id blank
        keys = ','.join('["%s"]=true' % k for k in only)
        src = src.replace('Kit=Biome.withProps', 'for k,e in Generated.Props do if not ({%s})[k] then e.assetId="" end end\nKit=Biome.withProps' % keys, 1)
    if props_nil:
        src = src.replace('Kit=Biome.withProps(Kit,Generated.Props)\nMeshes=Biome.propMeshes(Meshes,Generated.Props)\n', '').replace(',props=Generated.Props', '')
    if invalid:  # typos / too short / leading zero / not a string: none is a valid asset id
        src = src.replace('Kit=Biome.withProps', 'do local bad={"abc","12345","0123456789","1234567890123456789","12 345 6789"} local i=0 for _,e in Generated.Props do i+=1 e.assetId=bad[i%5+1] end end\nKit=Biome.withProps', 1)
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'props.luau'
        p.write_text(src)
        out = subprocess.run([str(runner), str(p)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-1800:] + out.stderr)
    props, kit, dlines, q = [], {}, [], []
    for line in out.stdout.splitlines():
        if line.startswith('Q\t'):
            f = line.split('\t')
            q.append(dict(id=f[1], layer=f[2], x=float(f[3]), z=float(f[4]), radius=float(f[5]), height=float(f[6]), path=float(f[7]),
                          keep_solid=float(f[8]), keep_soft=float(f[9]), pool=int(f[10]), spawn=float(f[11]), pool1=int(f[12]), clearing=int(f[13]),
                          edge=float(f[14]), sanct=int(f[15]), ground=int(f[16]), colliders=int(f[17])))
            continue
        f = line.split()
        if not f:
            continue
        if f[0] == 'P':
            props.append(dict(layer=f[1], id=f[2], x=float(f[3]), z=float(f[4]), biome=f[5]))
        elif f[0] == 'K':
            kit[f[1]] = dict(tris=int(f[2]), colliders=int(f[3]), gen=f[4] == '1')
        elif f[0] == 'D':
            dlines.append(line)
    return dict(props=props, kit=kit, count=len(props), digest=hashlib.sha256('\n'.join(dlines).encode()).hexdigest(), q=q)


def grid_peak(r, cls):
    """Peak over a 32 stud grid of the phone triangle estimate at the low/mid/high generated-mesh sizes, and of the kept part count."""
    c = r['cull'][cls]
    peak = {k: 0 for k in GEN_LEVELS}
    parts = 0
    for gx in range(-est.HALF, est.HALF + 1, 32):
        for gz in range(-est.HALF, est.HALF + 1, 32):
            within, kept, _, gen, fixed = est.culling(r['props'], r['kit'], c['radius'], c['budget'], r['hyst'], (gx, gz))
            parts = max(parts, kept)
            for k, g in GEN_LEVELS.items():
                peak[k] = max(peak[k], fixed + gen * g)
    return peak, parts


def count(props, ids=None, layer=None):
    return sum(1 for p in props if (ids is None or p['id'] in ids) and (layer is None or p['layer'] == layer))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--pin', action='store_true', help='print the digests of the EMPTY run (to update LEGACY on purpose)')
    ap.add_argument('--no-sub', action='store_true', help='skip the vegetation / overlap sub-verifiers')
    args = ap.parse_args()
    runner = args.runner
    fails = []

    def check(ok, msg):
        if not ok:
            fails.append(msg)

    # ---- 1. empty ids == the grammar before BD-463 ------------------------------------------------------------------------------------------
    empty = {}
    for prof in ('default', 'playtest'):
        e = run(runner, 'empty', prof)
        empty[prof] = e
        if args.pin:
            print("    '%s': (%d, '%s')," % (prof, e['count'], e['digest']))
        n, digest = LEGACY[prof]
        check(e['count'] == n and e['digest'] == digest, '%s profile, EMPTY ids: %d placements digest %s... differs from the pre-BD-463 grammar (%d, %s...)' % (prof, e['count'], e['digest'][:12], n, digest[:12]))
        check(not e['q'], '%s profile, EMPTY ids placed %d new props' % (prof, len(e['q'])))
        for label, kw in (('options.props = nil', dict(props_nil=True)), ('invalid ids', dict(invalid=True))):
            other = run(runner, 'empty', prof, **kw)
            check(other['digest'] == e['digest'] and other['count'] == e['count'], '%s profile: %s must equal the empty-id run' % (prof, label))
    shipped = run(runner, 'shipped', 'playtest')
    print('1. EMPTY ids: default %d and playtest %d placements, identical to the pre-BD-463 grammar (also with options.props = nil and with invalid ids); shipped ids %s' % (
        empty['default']['count'], empty['playtest']['count'], 'all empty (nothing new in the game)' if shipped['digest'] == empty['playtest']['digest'] else 'FILLED (placement is live)'))

    E = empty['playtest']
    F = run(runner, 'fake', 'playtest')
    F2 = run(runner, 'fake', 'playtest')
    check(F['digest'] == F2['digest'], 'fake-id placement is not deterministic')

    # ---- 2. the new props appear and REPLACE clutter -----------------------------------------------------------------------------------------
    newn = {k: count(F['props'], {k}) for k in ALL_KEYS}
    print('2. FAKE ids: placements %d (EMPTY %d); new props: %s' % (F['count'], E['count'], ' '.join('%s=%d' % (k.replace('_v3', ''), v) for k, v in newn.items())))
    for k, v in newn.items():
        check(v >= 5, '%s is placed only %d times with a fake id' % (k, v))
    check(F['count'] <= E['count'], 'placements went up: %d > %d' % (F['count'], E['count']))
    tufts = sum(newn[k] for k in PLANT_KEYS[:3])
    clusters = sum(newn[k] for k in PLANT_KEYS[4:7])
    old_grass = count(E['props'], {'world_grass_a', 'world_grass_b'}) - count(F['props'], {'world_grass_a', 'world_grass_b'})
    old_flowers = count(E['props'], {'world_flowers_a'}) - count(F['props'], {'world_flowers_a'})
    old_ferns = count(E['props'], {'world_fern_a', 'world_fern_b'}) - count(F['props'], {'world_fern_a', 'world_fern_b'})
    ratio_g, ratio_f = old_grass / max(1, tufts), old_flowers / max(1, clusters)
    print('   replacement: %d old grass placements -> %d tufts (%.1f per tuft), %d old flowers -> %d clusters (%.1f per cluster), %d old ferns -> %d fern plants' % (
        old_grass, tufts, ratio_g, old_flowers, clusters, ratio_f, old_ferns, newn['plant_fern_arch_v3']))
    check(5.0 <= ratio_g <= 8.0, 'old grass placements replaced per tuft %.1f outside 5-8' % ratio_g)
    check(6.0 <= ratio_f <= 10.0, 'old flower placements replaced per cluster %.1f outside 6-10' % ratio_f)
    check(old_ferns >= 2 * newn['plant_fern_arch_v3'], 'fern plants do not replace old ferns (%d old removed for %d plants)' % (old_ferns, newn['plant_fern_arch_v3']))
    ground_n = sum(newn[k] for k in GROUND_KEYS)
    gone = {i: count(E['props'], {i}) - count(F['props'], {i}) for i in ('world_boulder_bare_s', 'world_boulder_mossy_s', 'world_bush_a', 'world_bush_b', 'world_mushrooms_a')}
    print('   %d ground props + %d jungle plants replaced small clutter that is gone: %s' % (ground_n, newn['plant_jungle_leaf_v3'], ' '.join('%s -%d' % (k.replace('world_', ''), v) for k, v in gone.items())))
    check(all(v >= 0 for v in gone.values()), 'payer clutter went UP: %s' % gone)
    check(sum(gone.values()) >= 0.8 * (ground_n + newn['plant_jungle_leaf_v3']) * 0.55, 'too little clutter dropped for the new ground props: %s' % gone)
    for layer in ('tree', 'colossal', 'log', 'landmark'):
        a, b = count(E['props'], layer=layer), count(F['props'], layer=layer)
        check(abs(a - b) <= max(3, round(.1 * a)), 'the %s layer changed: %d -> %d' % (layer, a, b))

    # ---- 3. budget: phone worst spot, 32 stud grid peak, totals --------------------------------------------------------------------------
    est.PROPS_IDS = 'empty'; est.DUMP = DUMP
    rE = est.estimate(runner)
    est.PROPS_IDS = 'fake'
    rF = est.estimate(runner)
    est.PROPS_IDS = 'shipped'
    pE, pF = rE['profiles']['playtest'], rF['profiles']['playtest']
    print('3. phone triangle estimate (generated meshes at %d / %d / %d tris):' % tuple(GEN_LEVELS.values()))
    for key in ('world_tris_low', 'world_tris_mid', 'world_tris_high'):
        a, b = pE['phone_scene'][key], pF['phone_scene'][key]
        print('   estimator worst spot %-15s %9s -> %9s (%+.1f%%)' % (key, '{:,}'.format(a), '{:,}'.format(b), 100 * (b - a) / a))
        check(b <= a, 'phone worst-spot %s went up: %d -> %d' % (key, a, b))
    check(pF['phone_scene']['world_parts_lowpoly'] <= pE['phone_scene']['world_parts_lowpoly'], 'phone scene parts went up')
    # grid peaks need the props: rerun the dumps once with the cull settings
    for r, ids in ((rE, E), (rF, F)):
        r['props'], r['kit'] = ids['props'], ids['kit']
        r['cull'] = rE['cull']
        r['hyst'] = rE['hysteresis']
    peakE, partsE = grid_peak(rE, 'Phone')
    peakF, partsF = grid_peak(rF, 'Phone')
    for k in GEN_LEVELS:
        print('   phone grid peak (32 studs) %-4s %9s -> %9s (%+.1f%%)' % (k, '{:,}'.format(peakE[k]), '{:,}'.format(peakF[k]), 100 * (peakF[k] - peakE[k]) / peakE[k]))
        check(peakF[k] <= peakE[k], 'phone grid-peak triangles (%s) went up: %d -> %d' % (k, peakE[k], peakF[k]))
    check(partsF <= partsE, 'phone grid-peak kept props went up: %d -> %d' % (partsE, partsF))
    check(pF['kit_parts_total'] <= pE['kit_parts_total'], 'world parts went up: %d -> %d' % (pE['kit_parts_total'], pF['kit_parts_total']))
    check(pF['tris_total'] <= pE['tris_total'], 'island triangles (mid estimate) went up: %d -> %d' % (pE['tris_total'], pF['tris_total']))
    fixedE = sum(est.tris_of(p, E['kit']) for p in E['props'] if not E['kit'][p['id']]['gen'])
    fixedF = sum(est.tris_of(p, F['kit']) for p in F['props'] if not F['kit'][p['id']]['gen'])
    genE = sum(1 for p in E['props'] if E['kit'][p['id']]['gen'])
    genF = sum(1 for p in F['props'] if F['kit'][p['id']]['gen'])
    breakeven = (fixedF - fixedE) / max(1, genE - genF)
    print('   island: measured-mesh tris %s -> %s (%+d), generated-mesh props %d -> %d (%+d); the island is lighter whenever a generated bush/boulder/tree mesh is over %d tris'
          % ('{:,}'.format(fixedE), '{:,}'.format(fixedF), fixedF - fixedE, genE, genF, genF - genE, math.ceil(breakeven)))
    check(breakeven <= est.GEN_LOW, 'break-even generated-mesh size %.0f is above the LOW estimate %d' % (breakeven, est.GEN_LOW))

    # ---- 4. lanes, keep-outs, water, edge, bands, ground contact ---------------------------------------------------------------------------
    q = F['q']
    check(len(q) == sum(newn.values()), 'detail rows %d != new placements %d' % (len(q), sum(newn.values())))
    bad = {k: [] for k in ('lane', 'keepout', 'water', 'edge', 'sanctuary', 'spawn', 'clearing', 'ground', 'band', 'collider')}
    for r in q:
        solid = r['layer'] == 'rock'
        lane = (0.7 * r['radius']) if solid else max(1.0, .55 * r['radius'])
        if r['path'] < lane - 1e-6:
            bad['lane'].append(r)
        if (r['keep_solid'] < .5 * r['radius'] - 1e-6) if solid else (r['keep_soft'] < -1e-6):
            bad['keepout'].append(r)
        if r['pool'] or (not solid and r['pool1']):
            bad['water'].append(r)
        if r['edge'] > est.HALF + 1e-6:
            bad['edge'].append(r)
        if r['sanct']:
            bad['sanctuary'].append(r)
        if r['layer'] == 'shrub' and r['spawn'] < SPAWN_CLEAR - 1e-6:
            bad['spawn'].append(r)
        if solid and r['clearing']:
            bad['clearing'].append(r)
        if not r['ground']:
            bad['ground'].append(r)
        h = r['height']
        if (r['layer'] == 'shrub' and not (SMALL[0] - 1e-6 <= h <= SMALL[1] + 1e-6)) or (r['layer'] == 'groundcover' and h > 6.0) or (r['layer'] == 'rock' and h > 8.0) or h >= 42:
            bad['band'].append(r)
        want = r['id'] in ('ground_rock_medium_v3', 'ground_rock_mossy_v3', 'ground_log_fallen_v3', 'ground_stump_roots_v3')
        if (r['colliders'] > 0) != want:
            bad['collider'].append(r)
    soft_in_clear = sum(1 for r in q if r['layer'] == 'shrub' and r['clearing'])
    print('4. %d new placements checked: %s; %d Small-band plants stand in a clearing (the old shrub rule allows them at 35%%)' % (
        len(q), ', '.join('%s %d' % (k, len(v)) for k, v in bad.items()), soft_in_clear))
    for k, v in bad.items():
        check(not v, '%d new props break the %s rule (e.g. %s at %.0f, %.0f)' % (len(v), k, v[0]['id'] if v else '', v[0]['x'] if v else 0, v[0]['z'] if v else 0))
    heights = {}
    for r in q:
        heights.setdefault(r['layer'], []).append(r['height'])
    print('   heights: ' + '; '.join('%s %d props %.1f-%.1f studs' % (k, len(v), min(v), max(v)) for k, v in sorted(heights.items())))

    # ---- 5. partial ids ---------------------------------------------------------------------------------------------------------------------
    for label, keys in (('one plant (plant_grass_broad_v3)', ['plant_grass_broad_v3']), ('one ground prop (ground_rock_small_v3)', ['ground_rock_small_v3']),
                        ('jungle plant + stump', ['plant_jungle_leaf_v3', 'ground_stump_roots_v3'])):
        part = run(runner, 'fake', 'playtest', only=keys)
        used = {p['id'] for p in part['props'] if p['id'] in ALL_KEYS}
        check(used and used <= set(keys), 'partial ids %s placed %s' % (keys, sorted(used)))
        check(part['count'] <= E['count'], 'partial ids %s: placements went up %d -> %d' % (keys, E['count'], part['count']))
        rP = dict(rE, props=part['props'], kit=part['kit'])
        peakP, _ = grid_peak(rP, 'Phone')
        tris_e = sum(est.tris_of(p, E['kit']) for p in E['props'])
        tris_p = sum(est.tris_of(p, part['kit']) for p in part['props'])
        check(tris_p <= tris_e, 'partial ids %s: island triangles (mid estimate) went up %d -> %d' % (keys, tris_e, tris_p))
        for k in GEN_LEVELS:
            # a single-shape partial set can differ by one or two tufts at the peak spot (random local variance): 0.5 percent tolerance there, none island-wide
            check(peakP[k] <= peakE[k] * 1.005, 'partial ids %s: phone grid-peak triangles (%s) went up %d -> %d' % (keys, k, peakE[k], peakP[k]))
        print('5. partial ids, %s: new props %s, placements %d' % (label, {k: count(part["props"], {k}) for k in sorted(used)}, part['count']))

    # ---- 6. the sub-verifiers on the fake-id placement -------------------------------------------------------------------------------------
    if not args.no_sub:
        for tool in ('verify_vegetation_layers.py', 'verify_world_overlap.py'):
            res = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / tool), '--runner', str(runner), '--fake-ids'], capture_output=True, text=True)
            tail = (res.stdout.strip().splitlines() or [''])[-1]
            print('6. %s --fake-ids: %s' % (tool, tail if res.returncode == 0 else 'FAILED'))
            check(res.returncode == 0, '%s --fake-ids failed:\n%s' % (tool, (res.stdout + res.stderr)[-1500:]))

    if fails:
        raise SystemExit('world props FAIL:\n  ' + '\n  '.join(fails))
    print('world props ok (offline placement preview with fake ids; empty ids change nothing; not a Studio or phone measurement)')


if __name__ == '__main__':
    main()
