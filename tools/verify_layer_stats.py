#!/usr/bin/env python3
"""BD-1049: tests for tools/layer_stats.py (spread numbers, targets, pictures) and tools/dump_food_layout.py.

Synthetic point sets with a known shape must get the right verdict: clumped > 1, random about 1, evenly spaced < 1.
  python tools/verify_layer_stats.py [--runner luau.exe]    # --runner also checks the offline food placement dump
"""
from pathlib import Path
import argparse
import json
import math
import random
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import layer_stats as ls  # noqa: E402

HALF = 416.0
N = 3600
failures = []


def check(ok, message):
    if not ok:
        failures.append(message)
        print('FAIL', message)


def pts(coords, kind='food'):
    return [(x, z, kind) for x, z in coords]


def random_set(seed=3):
    rng = random.Random(seed)
    return pts((rng.uniform(-HALF, HALF), rng.uniform(-HALF, HALF)) for _ in range(N))


def even_set(seed=3):
    rng = random.Random(seed)
    side = int(math.sqrt(N))
    step = 2 * HALF / side
    return pts((-HALF + (i + 0.5) * step + rng.uniform(-1, 1), -HALF + (j + 0.5) * step + rng.uniform(-1, 1)) for i in range(side) for j in range(side))


def clumped_set(seed=3):
    rng = random.Random(seed)
    centres = [(rng.uniform(-HALF + 20, HALF - 20), rng.uniform(-HALF + 20, HALF - 20)) for _ in range(60)]
    return pts((cx + rng.gauss(0, 6), cz + rng.gauss(0, 6)) for cx, cz in centres for _ in range(N // 60))


def spread(points, block):
    r = ls.analyse(points, HALF, 256, (block,), None, baseline_draws=3, walk_samples=200)
    return r, r['blocks'][block]['kinds']['all']


def test_shapes():
    for block in (10, 20, 30):
        _, rand = spread(random_set(), block)
        _, even = spread(even_set(), block)
        _, clump = spread(clumped_set(), block)
        check(0.7 < rand['spread'] < 1.4, f'random set at {block}: spread {rand["spread"]:.2f} should be about 1')
        check(rand['verdict'] == 'like random', f'random set at {block}: verdict {rand["verdict"]}')
        check(even['spread'] < 0.5, f'even set at {block}: spread {even["spread"]:.2f} should be below 0.5')
        check(even['verdict'] == 'EVEN', f'even set at {block}: verdict {even["verdict"]}')
        check(clump['spread'] > 3, f'clumped set at {block}: spread {clump["spread"]:.2f} should be above 3')
        check(clump['verdict'] == 'CLUMPED', f'clumped set at {block}: verdict {clump["verdict"]}')
    r, s = spread(clumped_set(), 20)
    check(s['empty_share'] > 0.3, f'clumped set should leave many empty blocks, got {s["empty_share"]:.2f}')
    check(s['crowded_blocks'] > 0, 'clumped set should have crowded blocks')
    r, s = spread(even_set(), 20)
    check(s['empty_share'] == 0 and s['crowded_blocks'] == 0, 'even set has no empty or crowded blocks')
    # block sizes: 20 cells of 3.25 studs = 65 studs, 12 full blocks of 832
    check(r['blocks'][20]['n'] == 12 and abs(r['blocks'][20]['studs'] - 65.0) < 1e-9, 'block size geometry')


def test_nearest_and_walk():
    r = ls.analyse(even_set(), HALF, 256, (20,), None, baseline_draws=2, walk_samples=300)
    step = 2 * HALF / 60
    med = r['nn']['all']['nn_median']
    check(abs(med - step) < 2.5, f'even lattice nearest-neighbour median {med:.1f} should be about {step:.1f}')
    check(r['walk']['all']['walk_max'] < step, 'every spot of a lattice is within one step of a point')
    rc = ls.analyse(clumped_set(), HALF, 256, (20,), None, baseline_draws=2, walk_samples=300)
    check(rc['nn']['all']['nn_median'] < 4, 'clump members are close to each other')
    check(rc['walk']['all']['walk_p95'] > r['walk']['all']['walk_p95'] * 2, 'clumped set leaves longer walks than the even one')


def test_empty_zone():
    rng = random.Random(5)
    east = pts((rng.uniform(0, HALF), rng.uniform(-HALF, HALF)) for _ in range(2000))
    r = ls.analyse(east, HALF, 256, (20,), None, baseline_draws=2, walk_samples=200, empty_radius=30)
    e = r['empty']
    check(e['count'] >= 1 and e['zones'][0]['area'] > 50000, f'empty west half should be one big zone, got {e["count"]} zones')
    check(e['zones'][0]['x'] < -100, 'empty zone should sit in the west')
    full = ls.analyse(even_set(), HALF, 256, (20,), None, baseline_draws=2, walk_samples=100, empty_radius=30)
    check(full['empty']['count'] == 0, 'even set has no empty zone at 30 studs')
    # a mask turns water into non-walkable: an empty west half marked as water is no zone any more
    rows = ['0' * 104 + '1' * 104 for _ in range(208)]
    masked = ls.analyse(east, HALF, 256, (20,), {'cell': 4, 'rows': rows}, baseline_draws=2, walk_samples=100, empty_radius=30)
    check(masked['empty']['count'] == 0, 'water must not count as an empty zone')
    check(abs(masked['walkable_share'] - 0.5) < 1e-9, 'walkable share from the mask')


def test_kinds_and_grid():
    rows = [[0] * 16 for _ in range(16)]
    rows[2][3], rows[9][9], rows[15][0] = 1, 2, 2
    p = ls.points_from_grid(rows, 416.0, {'1': 'berry', '2': 'fruit'})
    check(sorted(k for _, _, k in p) == ['berry', 'fruit', 'fruit'], 'grid cells become points with kind names')
    x, z, _ = p[0]
    check(abs(x - (-416 + 3.5 * 52)) < 1e-9 and abs(z - (-416 + 2.5 * 52)) < 1e-9, 'grid cell centre in studs')
    mixed = pts([(0, 0), (10, 10)], 'berry') + pts([(100, 100)], 'amber')
    r = ls.analyse(mixed, HALF, 256, (10,), None, baseline_draws=1, walk_samples=50)
    check(r['kinds'] == ['all', 'berry', 'amber'] and r['totals'] == {'all': 3, 'berry': 2, 'amber': 1}, 'kinds are listed in game order')


def test_targets_and_cli():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / 'points.json'
        src.write_text(json.dumps({'points': [[x, z, k] for x, z, k in clumped_set()], 'arena': HALF}), encoding='utf-8')
        good = tmp / 'good.json'
        good.write_text(json.dumps({'rules': [{'kind': 'all', 'block': 20, 'metric': 'spread', 'min': 2}]}), encoding='utf-8')
        bad = tmp / 'bad.json'
        bad.write_text(json.dumps({'rules': [{'kind': 'all', 'block': 20, 'metric': 'spread', 'max': 1.5},
                                             {'kind': 'all', 'block': 30, 'metric': 'empty_share', 'max': 0.0},
                                             {'kind': 'all', 'metric': 'nn_median', 'min': 1}]}), encoding='utf-8')
        out = tmp / 'pics'
        out.mkdir()
        (out / '7-old.png').write_bytes(b'x')
        (out / 'notes.txt').write_text('x')
        args = ['--points', str(src), '--png-dir', str(out), '--name', 'test', '--blocks', '20,30', '--targets']
        check(ls.main(args + [str(good)]) == 0, 'a met target exits 0')
        check(ls.main(args + [str(bad)]) == 1, 'a broken target exits non-zero')
        names = sorted(p.name for p in out.glob('*.png'))
        check('8-test-spread-20x20-blocks.png' in names and '9-test-spread-30x30-blocks.png' in names, f'pictures continue the numbering after 7: {names}')
        check(any(n.endswith('dots-and-empty-zones.png') for n in names), 'dot map written')
        check(all((out / n).stat().st_size > 5000 for n in names if n != '7-old.png'), 'pictures are not empty')
        broken = ls.check_targets(ls.analyse(clumped_set(), HALF, 256, (20, 30), None, baseline_draws=1, walk_samples=50),
                                  json.loads(bad.read_text()))
        check(len(broken) == 2, f'two of three rules broken, got {broken}')
        grid = tmp / 'grid.json'
        grid.write_text(json.dumps({'half': 416, 'rows': [[1 if (i * 7 + j * 3) % 11 == 0 else 0 for i in range(64)] for j in range(64)]}), encoding='utf-8')
        check(ls.main(['--grid', str(grid), '--blocks', '8']) == 0, '--grid works')


def test_dump(runner):
    import dump_food_layout as dump
    one = dump.dump(runner, 2)
    seeds = sorted(one)
    check(len(seeds) == 2 and seeds[1] == seeds[0] + 1, 'two consecutive seeds')
    p = one[seeds[0]]['points']
    check(3400 <= len(p) <= 3600, f'food count {len(p)} should be near 3,600 (a few fail to find ground)')
    kinds = {k: sum(1 for _, _, kk in p if kk == k) for k in ('berry', 'fruit', 'egg', 'amber')}
    check(0.62 < kinds['berry'] / len(p) < 0.78 and 0.14 < kinds['fruit'] / len(p) < 0.26, f'kind mix off: {kinds}')
    check(all(abs(x) < 416 and abs(z) < 416 for x, z, _ in p), 'foods inside the arena')
    check(all(math.hypot(x, z - 30) >= 11 for x, z, _ in p), 'safe spawn disc stays clear')
    check(dump.dump(runner, 1)[seeds[0]]['points'] == p, 'same seed gives the same layout')
    check(one[seeds[0]]['points'] != one[seeds[1]]['points'], 'a different seed gives a different layout')
    m = one[seeds[0]]['mask']
    check(len(m['rows']) == 208 and len(m['rows'][0]) == 208, 'mask is 208 x 208 cells of 4 studs')
    ground = ls.Ground(416.0, m)
    share = sum(1 for x, z, _ in p if ground.ok(x, z)) / len(p)
    check(share > 0.97, f'foods lie on walkable ground (the 4-stud mask is coarser than the exact rule): {share:.3f}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', help='luau.exe: also check tools/dump_food_layout.py')
    args = ap.parse_args()
    test_shapes()
    test_nearest_and_walk()
    test_empty_zone()
    test_kinds_and_grid()
    test_targets_and_cli()
    if args.runner:
        test_dump(args.runner)
    if failures:
        print(f'{len(failures)} check(s) failed')
        return 1
    print('layer stats OK' + (' (with food dump)' if args.runner else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
