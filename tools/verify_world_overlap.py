"""BD-410 offline OVERLAP gate for the island world kit (docs/114 s8.1 item 5), generalising tools/verify_cave_overlap.py.

Runs the real placement grammar (same harness as estimate_world_budget.py) for the playtest profile, then intersects the SOLID footprints
pairwise: every kit collider box (trees: trunk, rocks: body boxes, landmarks: base boxes), scaled by the prop scale, rotated by the
prop yaw, in the XZ plane. Canopies and foliage may interleave (a forest); solid-vs-solid may not. Fails above the recorded cap.
Soft-prop (shrub/groundcover) vs solid overlaps are reported as information. Usage: python tools/verify_world_overlap.py --runner luau.exe [--list]
"""
from pathlib import Path
import argparse, math, subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_world_budget as est

DUMP = r'''
for _,p in a do print(string.format("P\t%s\t%s\t%.3f\t%.3f\t%.4f\t%.4f", p.layer, p.id, p.x, p.z, p.yaw, p.scale)) end
for id,d in Kit do
 for _,c in d.colliders do print(string.format("C\t%s\t%.3f\t%.3f\t%.3f\t%.3f\t%.4f", id, c[1], c[3], c[4], c[6], c[7])) end
 print(string.format("E\t%s\t%s\t%.3f\t%.3f\t%.3f", id, d.kind, d.extent[1], d.extent[2], d.extent[3]))
end
'''
SOLID_LAYERS = {'tree', 'colossal', 'rock', 'landmark'}
MAX_PAIRS = 0  # recorded cap of solid/solid footprint intersections (island, playtest profile)


def dump(runner):
    est.DUMP = DUMP
    text = (est.ROOT / 'src/shared/Config.luau').read_text()
    cfg = est.release_profiles.apply_profile(text, 'playtest')[0]
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'o.luau'
        p.write_text(est.luau_script(cfg, True))
        out = subprocess.run([runner, str(p)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-1500:] + out.stderr)
    props, cols, ext = [], {}, {}
    for l in out.stdout.splitlines():
        f = l.split('\t')
        if f[0] == 'P':
            props.append(dict(layer=f[1], id=f[2], x=float(f[3]), z=float(f[4]), yaw=float(f[5]), scale=float(f[6])))
        elif f[0] == 'C':
            cols.setdefault(f[1], []).append(tuple(float(v) for v in f[2:]))
        elif f[0] == 'E':
            ext[f[1]] = (f[2],) + tuple(float(v) for v in f[3:])
    return props, cols, ext


def boxes(p, cols):
    """World OBBs (x, z, w, d, yaw) of one prop's colliders. The model yaw rotates local +x toward -z (Roblox CFrame.Angles(0, yaw, 0))."""
    out = []
    c, s = math.cos(p['yaw']), math.sin(p['yaw'])
    for ox, oz, w, d, cy in cols:
        ox, oz = ox * p['scale'], oz * p['scale']
        out.append((p['x'] + ox * c + oz * s, p['z'] - ox * s + oz * c, w * p['scale'], d * p['scale'], p['yaw'] + cy))
    return out


def corners(b):
    x, z, w, d, yaw = b
    c, s = math.cos(yaw), math.sin(yaw)
    ax, az = (c, -s), (s, c)
    return [(x + ax[0] * i * w / 2 + az[0] * j * d / 2, z + ax[1] * i * w / 2 + az[1] * j * d / 2) for i in (-1, 1) for j in (-1, 1)], (ax, az)


def overlap(a, b, shrink=0.2):
    a, b = (a[0], a[1], max(a[2] - shrink, .01), max(a[3] - shrink, .01), a[4]), (b[0], b[1], max(b[2] - shrink, .01), max(b[3] - shrink, .01), b[4])
    ca, aa = corners(a)
    cb, ab = corners(b)
    for axis in aa + ab:
        pa = [p[0] * axis[0] + p[1] * axis[1] for p in ca]
        pb = [p[0] * axis[0] + p[1] * axis[1] for p in cb]
        if max(pa) <= min(pb) or max(pb) <= min(pa):
            return False
    return True


def find_overlaps(props, cols, ext):
    items = []
    for i, p in enumerate(props):
        if p['layer'] in SOLID_LAYERS and p['id'] in cols:
            bs = boxes(p, cols[p['id']])
            reach = max(max(b[2], b[3]) for b in bs) + max(math.hypot(b[0] - p['x'], b[1] - p['z']) for b in bs)
            items.append((i, p, bs, reach))
    grid = {}
    for it in items:
        grid.setdefault((int(it[1]['x'] // 40), int(it[1]['z'] // 40)), []).append(it)
    pairs = []
    for (gx, gz), cell in grid.items():
        near = [it for dx in (-1, 0, 1) for dz in (-1, 0, 1) for it in grid.get((gx + dx, gz + dz), [])]
        for a in cell:
            for b in near:
                if b[0] <= a[0] or math.hypot(a[1]['x'] - b[1]['x'], a[1]['z'] - b[1]['z']) > a[3] + b[3]:
                    continue
                if any(overlap(x, y) for x in a[2] for y in b[2]):
                    pairs.append((a[1], b[1]))
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()
    props, cols, ext = dump(args.runner)
    pairs = find_overlaps(props, cols, ext)
    kinds = {}
    for a, b in pairs:
        k = ' x '.join(sorted((a['layer'], b['layer'])))
        kinds[k] = kinds.get(k, 0) + 1
    print('island solid props %d, solid/solid footprint overlaps %d (cap %d) %s' % (
        sum(1 for p in props if p['layer'] in SOLID_LAYERS), len(pairs), MAX_PAIRS, kinds))
    if args.list:
        for a, b in pairs[:80]:
            print('  %s (%.0f,%.0f) x %s (%.0f,%.0f)' % (a['id'], a['x'], a['z'], b['id'], b['x'], b['z']))
    if len(pairs) > MAX_PAIRS:
        raise SystemExit('island overlap FAIL: %d > %d' % (len(pairs), MAX_PAIRS))
    print('island overlap ok')


if __name__ == '__main__':
    main()
