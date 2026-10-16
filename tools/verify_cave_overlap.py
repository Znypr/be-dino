"""BD-399 offline overlap check of the Cave hub layout (docs/104 s14): world-space footprints (position, size x scale, yaw) of every
prop row, built with the same rule the server uses (CaveProps.place scales each mesh uniformly by CaveHubProps.fitFactor).
Fails when two SOLID/large props intersect, or when a solid scatter prop overlaps a path, a pad, the lava basin or its fence.
Small clutter (walk-over pieces, moss, pebbles, crates, hanging pieces) may overlap grass/moss and each other. Pure Luau numbers,
never Studio.
"""
from pathlib import Path
import argparse, math, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]

LUAU = r'''
local C=CaveHubLayout
local L=C.get()
for _,p in L.props do
 local a=(Props.Assets::any)[p.key] or {}
 local n=a.native or {0,0,0}
 local w,h,d=p.w,p.h,p.d
 if a.native then
  local f=Props.fitFactor(n,{p.w,p.h,p.d})
  w,h,d=n[1]*f,n[2]*f,n[3]*f
 end
 print(string.format("P\t%s\t%s\t%.3f\t%.3f\t%.4f\t%.3f\t%.3f\t%.3f\t%d\t%d\t%d",p.key,p.owner,p.x,p.z,p.yaw,w,h,d,p.walk and 1 or 0,p.hang and 1 or 0,((Props.Solid::any)[p.key] or p.collider) and 1 or 0))
end
for _,q in L.paths do print(string.format("S\t%s\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f",q.id,q.ax,q.az,q.bx,q.bz,q.half)) end
for _,s in L.stations do print(string.format("T\t%s\t%.3f\t%.3f\t%.3f",s.id,s.x,s.z,s.r)) end
print(string.format("L\t%.3f\t%.3f\t%.3f\t%.3f",C.Pool.x,C.Pool.z,C.Pool.r,C.Fall.z))
'''

NEVER = {'cave_light_cone', 'cave_lava_fall', 'lava_pool_disc', 'potion_model'}  # FX / not placed as footprints
CLUTTER_KEYS = {'cave_moss_patch', 'rock_pebbles', 'nest', 'hub_straw_mat'}
SMALL = 3.2  # longest side under this (or flat) = clutter


def module(name, parent):
    return 'local script={Parent={' + parent + '}}\n' + (ROOT / name).read_text()


def luau_dump(runner):
    src = ('local require=function(x) return x end\n'
           + 'local CaveHubLayout=(function()\n' + module('src/shared/CaveHubLayout.luau', '') + '\nend)()\n'
           + 'local Props=(function()\n' + module('src/shared/CaveHubProps.luau', 'CaveHubLayout=CaveHubLayout') + '\nend)()\n' + LUAU)
    with tempfile.TemporaryDirectory() as t:
        path = Path(t) / 'dump.luau'
        path.write_text(src)
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-2000:] + out.stderr)
        return out.stdout.splitlines()


def corners(x, z, yaw, w, d):
    c, s = math.cos(yaw), math.sin(yaw)
    ax, az = (c, -s), (s, c)  # local x / z axes in world (CaveHubLayout.boxDist convention)
    pts = [(x + ax[0] * sx * w / 2 + az[0] * sz * d / 2, z + ax[1] * sx * w / 2 + az[1] * sz * d / 2) for sx in (-1, 1) for sz in (-1, 1)]
    return pts, (ax, az)


def obb_overlap(a, b, shrink=0.0):
    ca, aa = corners(a['x'], a['z'], a['yaw'], a['w'] - shrink, a['d'] - shrink)
    cb, ab = corners(b['x'], b['z'], b['yaw'], b['w'] - shrink, b['d'] - shrink)
    for axis in aa + ab:
        pa = [p[0] * axis[0] + p[1] * axis[1] for p in ca]
        pb = [p[0] * axis[0] + p[1] * axis[1] for p in cb]
        if max(pa) <= min(pb) or max(pb) <= min(pa):
            return False
    return True


def obb_point_dist(b, px, pz):
    dx, dz = px - b['x'], pz - b['z']
    c, s = math.cos(b['yaw']), math.sin(b['yaw'])
    lx, lz = dx * c - dz * s, dx * s + dz * c
    return math.hypot(max(abs(lx) - b['w'] / 2, 0), max(abs(lz) - b['d'] / 2, 0))


def seg_dist_box(b, s):
    return min(obb_point_dist(b, s['ax'] + (s['bx'] - s['ax']) * i / 40, s['az'] + (s['bz'] - s['az']) * i / 40) for i in range(41))


def load(runner):
    props, paths, stations, lava = [], [], {}, None
    for line in luau_dump(runner):
        f = line.split('\t')
        if f[0] == 'P':
            p = dict(key=f[1], owner=f[2], x=float(f[3]), z=float(f[4]), yaw=float(f[5]), w=float(f[6]), h=float(f[7]), d=float(f[8]),
                     walk=f[9] == '1', hang=f[10] == '1', solid=f[11] == '1')
            if p['key'] in NEVER or p['hang']:
                continue
            p['clutter'] = p['walk'] or (not p['solid'] and (max(p['w'], p['d']) < SMALL or p['h'] < 1.2 or p['key'] in CLUTTER_KEYS))
            props.append(p)
        elif f[0] == 'S':
            paths.append(dict(id=f[1], ax=float(f[2]), az=float(f[3]), bx=float(f[4]), bz=float(f[5]), half=float(f[6])))
        elif f[0] == 'T':
            stations[f[1]] = (float(f[2]), float(f[3]), float(f[4]))
        elif f[0] == 'L':
            lava = tuple(float(v) for v in f[1:])
    return props, paths, stations, lava


def check(runner, report=False):
    props, paths, stations, lava = load(runner)
    errors = []
    solid = [p for p in props if not p['clutter']]
    for i, a in enumerate(solid):
        for b in solid[i + 1:]:
            if math.hypot(a['x'] - b['x'], a['z'] - b['z']) > (max(a['w'], a['d']) + max(b['w'], b['d'])) * 0.75:
                continue
            if obb_overlap(a, b, 0.2):
                errors.append('overlap %s(%s %.1f,%.1f) x %s(%s %.1f,%.1f)' % (a['key'], a['owner'], a['x'], a['z'], b['key'], b['owner'], b['x'], b['z']))
    px, pz, pr, _ = lava
    for a in solid:
        if a['owner'] != 'scatter':
            continue
        for s in paths:
            if seg_dist_box(a, s) < s['half'] + 0.5:
                errors.append('%s (%.1f,%.1f) overlaps path %s' % (a['key'], a['x'], a['z'], s['id']))
        for sid, (sx, sz, sr) in stations.items():
            if obb_point_dist(a, sx, sz) < sr - 1.0:
                errors.append('%s (%.1f,%.1f) overlaps pad %s' % (a['key'], a['x'], a['z'], sid))
        if obb_point_dist(a, px, pz) < pr + 4:
            errors.append('%s (%.1f,%.1f) overlaps the lava basin / fence' % (a['key'], a['x'], a['z']))
    # BD-296 dressing pass (clear lanes): EVERY dress footprint, clutter included (ferns, mushrooms, moss clumps, crystals), stays off the walking
    # lanes: off every path, off every pad, away from the lava basin and out of the gate lane. Wall-hung vines are not floor footprints.
    dress = [p for p in props if p['owner'] == 'dress']
    gate = stations['gate']
    for a in dress:
        for sg in paths:
            if seg_dist_box(a, sg) < sg['half'] + 0.3:
                errors.append('dress %s (%.1f,%.1f) on path %s' % (a['key'], a['x'], a['z'], sg['id']))
        for sid, (sx, sz, sr) in stations.items():
            if obb_point_dist(a, sx, sz) < sr:
                errors.append('dress %s (%.1f,%.1f) on pad %s' % (a['key'], a['x'], a['z'], sid))
        if obb_point_dist(a, px, pz) < pr + 3:
            errors.append('dress %s (%.1f,%.1f) in the lava basin zone' % (a['key'], a['x'], a['z']))
        if a['z'] < gate[1] - 16 and abs(a['x']) < 24:
            errors.append('dress %s (%.1f,%.1f) in the gate lane' % (a['key'], a['x'], a['z']))
    if report:
        print('solid props %d, clutter %d, paths %d, dress footprints %d' % (len(solid), len(props) - len(solid), len(paths), len(dress)))
    return errors, len(props)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    assert 'CaveHub = false' in (ROOT / 'src/shared/Config.luau').read_text(), 'Config.CaveHub ships false'
    errs, n = check(args.runner, True)
    if errs:
        raise SystemExit('cave overlap FAIL (%d):\n  ' % len(errs) + '\n  '.join(errs[:60]))
    print('cave overlap ok: %d footprints, no solid/solid, path, pad or basin overlap' % n)
