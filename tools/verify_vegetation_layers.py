"""BD-473 (docs/139 s5-s6, scope cut) offline band verifier for the island vegetation.

Runs the real placement grammar (same harness as estimate_world_budget.py: playtest profile, density 1.25, seed 1404) and asserts the
HEIGHT DISTRIBUTION of the vegetation (height = kit extent x placed scale, an upper bound for the fitted generated meshes):
  * the Small band: every shrub is 4-12 studs, the Small band (all vegetation 4-12 studs, shrubs plus the small trees and palms) has
    at least 2 plants per canopy-class tree (12 studs and up) and most of it is taller than a spawn Compy (6.6 studs);
  * no vegetation is placed in the 42-80 stud gap; the colossal layer (renamed from giant) is 80-140 studs, 4-10 percent of the
    canopy-class, and stays 150+ studs from the spawn;
  * clearings cover 20-30 percent of the eligible forest area, never touch a route, keep-out or pool, and hold no tree, colossal
    tree or fallen log; no Small-band plant stands within the spawn clear radius.
Prints the histogram. Not Studio evidence. Usage: python tools/verify_vegetation_layers.py --runner luau.exe [--list]
"""
from pathlib import Path
import argparse, math, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_world_budget as est

DUMP = r'''
print("V\t"..tostring(Biome.Version))
for _,p in a do print(string.format("P\t%s\t%s\t%.3f\t%.3f\t%.5f\t%s", p.layer, p.id, p.x, p.z, p.scale, p.biome)) end
for id,d in Kit do print(string.format("E\t%s\t%s\t%.4f\t%.4f\t%.4f", id, d.kind, d.extent[1], d.extent[2], d.extent[3])) end
local clears = if Biome.clearings then Biome.clearings({seed=Config.WorldArtSeed,density=DENSITY,extent=Config.ArenaHalfWidth,height=Layout.height,kit=Kit,meshes=Meshes,map=BiomeMap,layout=Layout}) else {}
for _,c in clears do
 print(string.format("C\t%.3f\t%.3f\t%.3f\t%.1f\t%.1f", c.x, c.z, c.r, Biome.pathClearance(c.x,c.z), Biome.keepOutClearance(c.x,c.z,true)))
 print(string.format("W\t%d", if Layout.inPool(c.x,c.z,c.r) then 1 else 0))
end
local FOREST={fern=true,conifer=true,marsh=true}
local eligible,covered=0,0
for x=-404,404,8 do for z=-404,404,8 do
 local h=Layout.height(x,z)
 local _,dom=BiomeMap.weights(x,z,h,Config.WorldArtSeed)
 if FOREST[dom] and Biome.pathClearance(x,z)>0 and Biome.keepOutClearance(x,z,true)>0 and not Layout.inPool(x,z,0) then
  eligible+=1
  if Biome.inClearing and Biome.inClearing(clears,x,z,0) then covered+=1 end
 end
end end
print(string.format("A\t%d\t%d", eligible, covered))
'''
SPAWN = (0.0, 30.0)
COMPY = 6.6          # MEASURED spawn Compy height (docs/139 s3.1)
SMALL = (4.0, 12.0)  # Small band (docs/139 s5)
GAP = (42.0, 80.0)   # nothing vegetated is placed here
COLOSSAL = (80.0, 140.0)
CANOPY = 12.0        # canopy-class = vegetation of 12 studs and up
VEG = {'tree', 'colossal', 'shrub'}  # groundcover is G0 (texture), rocks and logs are not vegetation heights


def dump(runner):
    est.DUMP = DUMP
    text = (est.ROOT / 'src/shared/Config.luau').read_text()
    cfg = est.release_profiles.apply_profile(text, 'playtest')[0]
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'veg.luau'
        p.write_text(est.luau_script(cfg, True))
        out = subprocess.run([runner, str(p)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-1500:] + out.stderr)
    res = dict(version=None, props=[], ext={}, clear=[], area=(0, 0))
    last = None
    for l in out.stdout.splitlines():
        f = l.split('\t')
        if f[0] == 'V':
            res['version'] = int(f[1])
        elif f[0] == 'P':
            res['props'].append(dict(layer=f[1], id=f[2], x=float(f[3]), z=float(f[4]), scale=float(f[5]), biome=f[6]))
        elif f[0] == 'E':
            res['ext'][f[1]] = (f[2],) + tuple(float(v) for v in f[3:])
        elif f[0] == 'C':
            last = dict(x=float(f[1]), z=float(f[2]), r=float(f[3]), path=float(f[4]), keep=float(f[5]), water=0)
            res['clear'].append(last)
        elif f[0] == 'W' and last is not None:
            last['water'] = int(f[1])
        elif f[0] == 'A':
            res['area'] = (int(f[1]), int(f[2]))
    return res


def height(p, ext):
    return ext[p['id']][2] * p['scale']


def pct(values, q):
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))] if v else 0.0


def analyse(res):
    ext = res['ext']
    veg = [(p, height(p, ext)) for p in res['props'] if p['layer'] in VEG and ext[p['id']][0] in ('tree', 'shrub')]
    out = dict(veg=veg)
    out['shrub'] = [h for p, h in veg if p['layer'] == 'shrub']
    out['tree'] = [h for p, h in veg if p['layer'] == 'tree']
    out['colossal'] = [h for p, h in veg if p['layer'] == 'colossal']
    out['small'] = [h for p, h in veg if SMALL[0] <= h < SMALL[1]]
    out['canopy'] = [h for p, h in veg if h >= CANOPY]
    out['gap'] = [(p, h) for p, h in veg if GAP[0] < h < GAP[1]]
    out['below'] = [(p, h) for p, h in veg if h < SMALL[0]]
    return out


def histogram(veg):
    edges = [4, 6.6, 8, 12, 20, 26, 42, 80, 100, 140]
    labels = ['<4'] + ['%g-%g' % (a, b) for a, b in zip(edges, edges[1:])] + ['>=140']
    counts = [0] * len(labels)
    for _, h in veg:
        i = sum(1 for e in edges if h >= e)
        counts[i] += 1
    return list(zip(labels, counts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()
    res = dump(args.runner)
    a = analyse(res)
    ext, props = res['ext'], res['props']
    fails = []

    def check(ok, msg):
        if not ok:
            fails.append(msg)

    print('BiomePlacement.Version %s, seed 1404 playtest density: %d placements, %d vegetation (tree, colossal, shrub)' % (res['version'], len(props), len(a['veg'])))
    print('height histogram (studs, kit extent x scale):')
    for label, n in histogram(a['veg']):
        print('  %-8s %5d %s' % (label, n, '#' * (n // 20)))
    for name in ('shrub', 'tree', 'colossal'):
        v = a[name]
        if v:
            print('  %-9s n=%4d  min %.1f  p10 %.1f  p50 %.1f  p90 %.1f  max %.1f' % (name, len(v), min(v), pct(v, .1), pct(v, .5), pct(v, .9), max(v)))
    small, canopy = a['small'], a['canopy']
    ratio = len(small) / max(1, len(canopy))
    taller = sum(1 for h in small if h > COMPY) / max(1, len(small))
    share = len(a['colossal']) / max(1, len(canopy))
    print('Small band (4-12): %d plants, canopy-class (12+): %d, ratio %.2f per canopy tree, %.0f%% taller than a spawn Compy (%.1f)' % (len(small), len(canopy), ratio, 100 * taller, COMPY))
    print('colossal share of the canopy-class: %.1f%% (%d)' % (100 * share, len(a['colossal'])))

    check(res['version'] == 3, 'BiomePlacement.Version must be 3, got %s' % res['version'])
    check(not any(p['layer'] == 'giant' for p in props), 'the giant layer is renamed to colossal')
    # Small band
    check(len(a['shrub']) >= 600, 'Small band shrubs: %d (floor 600)' % len(a['shrub']))
    check(all(SMALL[0] <= h <= SMALL[1] + 1e-6 for h in a['shrub']), 'every shrub is 4-12 studs: min %.2f max %.2f' % (min(a['shrub'] or [0]), max(a['shrub'] or [0])))
    check(not a['below'], '%d vegetation placements under 4 studs (ground cover is the only layer below the band)' % len(a['below']))
    check(ratio >= 2.0, 'Small band has %.2f plants per canopy-class tree (need 2.0)' % ratio)
    check(taller >= .45, 'only %.0f%% of the Small band is taller than a spawn Compy (need 45%%)' % (100 * taller))
    check(5.5 <= pct(a['shrub'], .5) <= 9.5, 'Small band shrub median %.1f outside 5.5-9.5' % pct(a['shrub'], .5))
    # gap and colossal
    check(not a['gap'], 'vegetation in the 42-80 stud gap: %d (e.g. %s %.1f)' % (len(a['gap']), a['gap'][0][0]['id'] if a['gap'] else '', a['gap'][0][1] if a['gap'] else 0))
    col = a['colossal']
    check(len(col) >= 20, 'colossal trees: %d (floor 20)' % len(col))
    check(all(COLOSSAL[0] <= h <= COLOSSAL[1] + 1e-6 for h in col), 'every colossal tree is 80-140 studs: min %.1f max %.1f' % (min(col or [0]), max(col or [0])))
    check(.04 <= share <= .10, 'colossal share of the canopy-class %.1f%% outside 4-10%%' % (100 * share))
    near = [p for p in props if p['layer'] == 'colossal' and math.hypot(p['x'] - SPAWN[0], p['z'] - SPAWN[1]) < 150]
    check(not near, 'colossal trees within 150 studs of the spawn: %d' % len(near))
    check(all(ext[p['id']][0] == 'tree' for p in props if p['layer'] == 'colossal'), 'colossal trees only (no rock spires)')
    check(max(a['tree'] or [0]) < GAP[0], 'tree layer tops at %.2f studs (limit 42)' % max(a['tree'] or [0]))
    # spawn: no Small-band plant close to the spawn point
    close = [p for p in props if p['layer'] == 'shrub' and math.hypot(p['x'] - SPAWN[0], p['z'] - SPAWN[1]) < 30]
    check(not close, 'Small band plants within 30 studs of the spawn: %d' % len(close))
    # clearings
    eligible, covered = res['area']
    frac = covered / max(1, eligible)
    print('clearings: %d discs (r %.0f-%.0f), %.1f%% of the eligible forest area (%d of %d samples)' % (
        len(res['clear']), min([c['r'] for c in res['clear']] or [0]), max([c['r'] for c in res['clear']] or [0]), 100 * frac, covered, eligible))
    check(len(res['clear']) >= 8, 'clearings: %d (floor 8)' % len(res['clear']))
    check(.20 <= frac <= .30, 'clearings cover %.1f%% of the forest area (need about 25%%: 20-30%%)' % (100 * frac))
    for c in res['clear']:
        check(c['path'] >= c['r'], 'clearing at (%.0f, %.0f) touches a route (clearance %.1f < r %.1f)' % (c['x'], c['z'], c['path'], c['r']))
        check(c['keep'] >= c['r'], 'clearing at (%.0f, %.0f) touches a keep-out or the spawn meadow (clearance %.1f < r %.1f)' % (c['x'], c['z'], c['keep'], c['r']))
        check(not c['water'], 'clearing at (%.0f, %.0f) touches water' % (c['x'], c['z']))
    inside = [p for p in props if p['layer'] in ('tree', 'colossal', 'log') and any(math.hypot(p['x'] - c['x'], p['z'] - c['z']) < c['r'] * .86 for c in res['clear'])]
    check(not inside, '%d trees, colossal trees or logs stand inside a clearing (e.g. %s at %.0f, %.0f)' % (len(inside), inside[0]['id'] if inside else '', inside[0]['x'] if inside else 0, inside[0]['z'] if inside else 0))
    if args.list:
        for c in res['clear']:
            print('  clearing (%.0f, %.0f) r %.0f' % (c['x'], c['z'], c['r']))
    if fails:
        raise SystemExit('vegetation layers FAIL:\n  ' + '\n  '.join(fails))
    print('vegetation layers ok')


if __name__ == '__main__':
    main()
