"""BD-411 PALETTE gate (docs/114 s5). Applies src/shared/AssetPalette.luau to the output of tools/qa/colour_probe.server.luau.

1. In your own temp Studio copy (Play mode, CaveHub = true) run colour_probe.server.luau with execute_luau (Server) and save the text.
2. python tools/qa/palette_report.py --runner luau.exe [--input saved.tsv]   (default: the committed probe of the current main build)
Fails when a prop is outside its zone rule and is not listed in KNOWN (an open kanban row). A KNOWN prop that now passes is printed
as FIXED so the row can be closed. Not an art review: only dominant hue buckets of the colour texture are measured.
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'tools/qa/data/colour_probe_2026-10-16.tsv'
# (place, key) -> (open kanban row, flag). Remove the entry when the prop is regenerated / recoloured.
# Flag column (2nd tuple item): PENDING = the OWNER has not yet decided whether blue-grey stone is acceptable (docs/117 s6 question 2).
# These are NOT to be recoloured or regenerated until that decision; the flag is only recorded here and printed in the report.
PENDING = 'OWNER-DECISION-PENDING'
KNOWN = {
    ('cave', 'hub_counter_stone'): ('BD-414', PENDING), ('cave', 'hub_bench_stone'): ('BD-414', PENDING), ('cave', 'cave_stalagmite_l'): ('BD-414', PENDING),
    ('cave', 'cave_stalagmite_s'): ('BD-414', PENDING), ('cave', 'cave_rock_round'): ('BD-414', PENDING), ('cave', 'cave_stalactite'): ('BD-414', PENDING),
    ('cave', 'cave_stalagmite_cluster'): ('BD-414', PENDING), ('cave', 'hub_lantern_post'): ('BD-414', PENDING), ('cave', 'hub_lectern_book'): ('BD-414', PENDING),
    ('cave', 'hub_gong'): ('BD-414', PENDING), ('cave', 'hub_cauldron'): ('BD-414', PENDING),
    ('cave', 'rock_mossy_boulder'): ('BD-414', PENDING), ('cave', 'cave_rock_flat'): ('BD-414', PENDING),
    ('island', 'rock_pillar'): ('BD-415', PENDING),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--input', default=str(DEFAULT))
    args = ap.parse_args()
    rows = []
    for l in Path(args.input).read_text().splitlines():
        f = l.split('\t')
        if f[0] == 'COL':
            rows.append((f[1], f[2], f[3], [int(v) for v in f[8].split(',')]))
        elif f[0] == 'ERR':
            raise SystemExit('probe error: ' + l)
    src = ('local script={Parent={}}\nlocal AP=(function()\n' + (ROOT / 'src/shared/AssetPalette.luau').read_text() + '\nend)()\n')
    for place, key, source, hist in rows:
        src += 'print(AP.zoneOf(%r,%r), %r, %r, AP.check(%r,%r,{%s}))\n' % (place, key, place, key, place, key, ','.join(map(str, hist)))
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'pal.luau'
        p.write_text(src)
        out = subprocess.run([args.runner, str(p)], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(out.stdout[-1500:] + out.stderr)
    new, known, fixed = [], [], []
    for l in out.stdout.splitlines():
        zone, place, key, ok, reason = l.split('\t')
        k = (place, key)
        if ok == 'false':
            (known if k in KNOWN else new).append((zone, place, key, reason))
        elif k in KNOWN:
            fixed.append(k)
    print('palette: %d props measured, %d offenders (%d known, %d new)' % (len(rows), len(known) + len(new), len(known), len(new)))
    by = {}
    for zone, place, key, reason in known + new:
        by.setdefault(zone, []).append('%s/%s %s [%s]' % (place, key, reason, ' '.join(KNOWN.get((place, key), ('NEW',)))))
    for zone, items in by.items():
        print(' zone %s: %d' % (zone, len(items)))
        for i in items:
            print('   ' + i)
    for k in fixed:
        print('FIXED (close %s): %s/%s' % (KNOWN[k][0], k[0], k[1]))
    if new:
        raise SystemExit('palette FAIL: %d new offenders (fix the asset or add a kanban row and a KNOWN entry)' % len(new))
    print('palette gate ok (known offenders are tracked in the kanban)')


if __name__ == '__main__':
    main()
