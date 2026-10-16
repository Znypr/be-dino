"""BD-413 BUDGET gate (docs/107, handbook 8.1 item 8): applies the part / light caps to the output of tools/qa/budget_probe.server.luau.

Caps: island world kit parts <= 5,550 and parts loaded at join <= 9,150 (tools/verify_world_budget.py caps); cave hub parts <= 410 and
lights <= 16 (docs/104, docs/107 CaveHubLayout budget). Usage: python tools/qa/budget_report.py [--input probe.tsv]
Default input: the committed probe of the current main build. The offline triangle estimate stays in tools/verify_world_budget.py.
"""
from pathlib import Path
import argparse
ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'tools/qa/data/budget_probe_2026-10-16.tsv'
CAPS = [('island_world_kit', 'parts', 2, 5550), ('cave_hub', 'parts', 2, 410), ('workspace_total', 'parts at join', 2, 9150),
        ('workspace_total', 'lights (whole scene)', 4, 16)]


def check(text):
    rows = {}
    for l in text.splitlines():
        f = l.split('\t')
        if f[0] == 'BUD':
            rows[f[1]] = [int(v) for v in f[2:]]
    out, bad = [], 0
    for place, label, col, cap in CAPS:
        if place not in rows:
            out.append('MISS %s: not in the probe output' % place)
            bad += 1
            continue
        v = rows[place][col - 2]
        ok = v <= cap
        bad += 0 if ok else 1
        out.append('%s %s %s: %d <= %d' % ('OK  ' if ok else 'FAIL', place, label, v, cap))
    return out, bad


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default=str(DEFAULT))
    args = ap.parse_args()
    lines, bad = check(Path(args.input).read_text())
    print('\n'.join(lines))
    if bad:
        raise SystemExit('budget FAIL: %d cap(s) exceeded' % bad)
    print('budget ok (parts/lights measured in Studio; triangles: tools/verify_world_budget.py estimate)')
