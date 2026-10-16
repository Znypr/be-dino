"""Offline mobile budget guard (BD-321, docs/107). Fails when the playtest world grows past a cap.

Caps are the numbers tools/estimate_world_budget.py produced on 2026-10-16 plus about 20 percent headroom. Exceeding one means
a placement/density/culling change made the phone scene heavier: re-run the estimate, read docs/107, then raise the cap on
purpose (and re-check on a phone, BD-085). Rule-of-thumb phone guidance overruns are printed as WARN, never as failures.
Usage: python tools/verify_world_budget.py --runner luau.exe
"""
from pathlib import Path
import argparse, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_world_budget as est

PT = lambda r: r['profiles']['playtest']
# name -> (cap, getter). Measured value in the comment (2026-10-16, main 60699c8 + this branch).
CAPS = {
    'playtest MeshPart props': (4300, lambda r: PT(r)['mesh_parts']),  # 3,551
    'playtest kit parts incl. colliders': (5550, lambda r: PT(r)['kit_parts_total']),  # 4,625
    'playtest parts loaded at join': (9150, lambda r: PT(r)['join_parts']),  # 7,625
    'phone props kept at spawn': (820, lambda r: PT(r)['cull']['Phone']['spawn'][1]),  # 683
    'phone props kept, worst spot': (1090, lambda r: PT(r)['cull']['Phone']['worst'][1]),  # 905
    'phone scene parts, worst spot': (3980, lambda r: PT(r)['phone_scene']['world_parts_lowpoly']),  # 3,312
    'phone scene tris (est), worst spot': (660_000, lambda r: PT(r)['phone_scene']['world_tris_mid']),  # 551,290
    'low-poly dino parts, 12 players + NPCs': (145, lambda r: r['dinos']['low_parts_peak']),  # 119
    'low-poly dino images MiB at cap': (24, lambda r: r['dinos']['img_mib_cap']),  # 19.2 of the 80 MiB budget
    'combat HP replication KB/s, worst': (2.5, lambda r: r['combat']['worst_kbs']),  # 2.04
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    r = est.estimate(args.runner)
    bad = []
    for name, (cap, get) in CAPS.items():
        v = get(r)
        print(f"{'OK  ' if v <= cap else 'FAIL'} {name}: {v:,} <= {cap:,}")
        if v > cap:
            bad.append(name)
    g, ps = r['guidance'], PT(r)['phone_scene']
    for label, v, key in (('phone scene parts', ps['world_parts_lowpoly'], 'attached_parts'),
                          ('phone scene triangles (est)', ps['world_tris_mid'], 'triangles'),
                          ('parts loaded at join', PT(r)['join_parts'], 'attached_parts')):
        if v > g[key]:
            print(f"WARN {label} {v:,} is over the phone rule of thumb {g[key]:,} (docs/107; measure on a phone, BD-085)")
    if bad:
        raise SystemExit('budget exceeded: ' + ', '.join(bad))
    print('world budget OK (offline estimate, not a phone measurement)')


if __name__ == '__main__':
    main()
