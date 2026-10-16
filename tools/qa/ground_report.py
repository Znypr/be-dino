"""BD-409 GROUNDING gate (docs/114 s8.1 item 4): applies the thresholds to the output of tools/qa/ground_probe.server.luau.

1. In your own temp Studio copy (Play mode, CaveHub = true) run ground_probe.server.luau with execute_luau (Server); save the text.
2. python tools/qa/ground_report.py [--input saved.tsv]   (default: the committed probe of the current main build)
Rules (studs): nothing may be BELOW the terrain (probe SUNK threshold 0.3 for plants and cave props; island rocks and landmarks get the
RockSink embed of 12% of their height) or FLOAT above it by more than 0.3 (BD-417). Documented exception: cave rim pieces are placed 0.5 stud in
the wall on purpose (design allowance 0.6). Anything else fails, with the per-kind counts and the worst offenders. Lying logs are not graded (listed as LYING).
"""
from pathlib import Path
import argparse
ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'tools/qa/data/ground_probe_2026-10-16.tsv'
RIM = {'cave_wall_pillar', 'cave_wall_arch_small', 'cave_wall_boulder_l'}
SUNK_ROCK_MAX = 0.0   # BD-416: nothing on the island may be deeper than its RockSink allowance (the probe already adds it); was 6.0
FLOAT_PLANT_MAX = 0.3  # BD-417: roots meet the ground within 0.3 stud; was 1.2 (probe FLOAT is 0.3 as well)


def evaluate(text):
    kinds, worst, places = [], [], {}
    for l in text.splitlines():
        f = l.split('\t')
        if f[0] == 'PLACE':
            places[f[1]] = (int(f[2]), int(f[3]) if len(f) > 3 else 0)
        elif f[0] == 'KIND':
            kinds.append(dict(place=f[1], kind=f[2], n=int(f[3]), sunk=int(f[4]), float=int(f[5]), worst_sunk=float(f[6]), worst_float=float(f[7])))
        elif f[0] == 'WORST':
            worst.append(l)
    errors = []
    for k in kinds:
        rim = k['kind'] in RIM
        rocky = k['place'] == 'island' and any(t in k['kind'] for t in ('boulder', 'rocks_', 'landmark'))
        if k['sunk'] and not (rim and k['worst_sunk'] <= 0.6) and not (rocky and k['worst_sunk'] <= SUNK_ROCK_MAX):
            errors.append('%s/%s: %d of %d below the terrain, worst %.2f' % (k['place'], k['kind'], k['sunk'], k['n'], k['worst_sunk']))
        if k['float'] and k['worst_float'] > FLOAT_PLANT_MAX:
            errors.append('%s/%s: %d floating, worst %.2f' % (k['place'], k['kind'], k['float'], k['worst_float']))
    return kinds, worst, places, errors


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default=str(DEFAULT))
    args = ap.parse_args()
    kinds, worst, places, errors = evaluate(Path(args.input).read_text())
    for p, (n, lying) in places.items():
        s = sum(k['sunk'] for k in kinds if k['place'] == p or k['place'].startswith(p))
        fl = sum(k['float'] for k in kinds if k['place'] == p or k['place'].startswith(p))
        print('%s: %d props probed (%d lying logs not graded), %d below the terrain (> threshold), %d floating (> 0.3)' % (p, n, lying, s, fl))
    for k in sorted(kinds, key=lambda k: -(k['sunk'] + k['float']))[:12]:
        print('  %-34s %s n=%d sunk=%d (worst %.2f) float=%d (worst %.2f)' % (k['kind'], k['place'], k['n'], k['sunk'], k['worst_sunk'], k['float'], k['worst_float']))
    for w in worst[:6]:
        print('  ' + w.replace('\t', ' '))
    if errors:
        raise SystemExit('grounding FAIL:\n  ' + '\n  '.join(errors))
    print('grounding gate ok (documented slope allowances only)')
