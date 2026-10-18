"""BD-1033 / docs/186 s4: how long until a player sees a rarer pattern? Plain numbers for the owner.

Reads the REAL pattern table (ProgressionConfig.EggPatterns) and rolls the REAL Genetics.roll in Luau, so the printed
numbers cannot drift from the game. A model, not measured play: one pattern per egg, eggs independent, and
EGGS_PER_MINUTE eggs a minute while running (docs/186 s1: about 3, PROVISIONAL, BD-1043 measures it).

  python tools/simulate_pattern_timing.py --runner C:/.../luau.exe            # table + exact waits + seeded check
  python tools/simulate_pattern_timing.py --runner ... --rolls 200000          # more rolls in the seeded check
"""
from pathlib import Path
import argparse, math, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
EGGS_PER_MINUTE = 3
TIERS = ('Common', 'Uncommon', 'Rare', 'Epic', 'Legendary', 'Mythic')


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


DUMP = r'''
for _, p in PC.EggPatterns do print("ROW|" .. p.id .. "|" .. p.name .. "|" .. p.rarity .. "|" .. p.weight) end
print("SCALE|" .. PC.PatternWeightScale)
local counts = {}
math.randomseed(SEED) -- Luau's own generator (PCG): same seed, same numbers; a hand-made LCG would correlate the 6 draws per egg
local rng = {NextNumber = function() return math.random() end}
for _ = 1, ROLLS do local g = G.roll(0, rng) counts[g.patternId] = (counts[g.patternId] or 0) + 1 end
for id, n in counts do print("MC|" .. id .. "|" .. n) end
print("ROLLS|" .. ROLLS)
'''


def run(runner, rolls, seed):
    src = ('local PC=' + module('src/shared/ProgressionConfig.luau') + '\n'
           'local script={Parent={ProgressionConfig=PC}}\nlocal require=function() return PC end\n'
           'local G=' + module('src/shared/EggGenetics.luau') + '\n'
           f'local SEED, ROLLS = {seed}, {rolls}\n' + DUMP)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'sim.luau'
        path.write_text(src, encoding='utf-8')
        r = subprocess.run([runner, str(path)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    rows, mc, scale, n = [], {}, 0, 0
    for line in r.stdout.splitlines():
        parts = line.split('|')
        if parts[0] == 'ROW': rows.append((parts[1], parts[2], parts[3], int(parts[4])))
        elif parts[0] == 'SCALE': scale = int(parts[1])
        elif parts[0] == 'MC': mc[parts[1]] = int(parts[2])
        elif parts[0] == 'ROLLS': n = int(parts[1])
    return rows, scale, mc, n


def wait(p):
    """Mean and median eggs, and eggs for a 90% chance, until the first egg with chance p per egg."""
    return 1 / p, math.ceil(math.log(0.5) / math.log(1 - p)), math.ceil(math.log(0.1) / math.log(1 - p))


def report(rows, scale, mc, n):
    total = sum(w for *_, w in rows)
    out = [f'Patterns: {len(rows)} (weights total {total} of {scale}); {EGGS_PER_MINUTE} eggs a minute (PROVISIONAL)', '']
    out.append(f'{"Pattern":<10}{"Tier":<11}{"Per egg":>10}{"Seeded":>10}')
    for pid, name, tier, w in rows:
        out.append(f'{name:<10}{tier:<11}{100 * w / total:>9.3f}%{100 * mc.get(pid, 0) / n:>9.3f}%')
    out += ['', 'Wait for the FIRST pattern of at least this tier (eggs, then minutes at the pace above):',
            f'{"Tier or better":<16}{"Per egg":>9}{"Mean":>9}{"Median":>9}{"9 in 10":>9}{"Median min":>12}']
    for tier in TIERS[1:]:
        k = TIERS.index(tier)
        p = sum(w for _, _, t, w in rows if TIERS.index(t) >= k) / total
        if p <= 0: continue
        mean, med, p90 = wait(p)
        out.append(f'{tier:<16}{100 * p:>8.3f}%{mean:>9.1f}{med:>9d}{p90:>9d}{med / EGGS_PER_MINUTE:>12.1f}')
    out += ['', 'Wait for one SPECIFIC pattern (eggs, median):']
    for pid, name, tier, w in rows:
        mean, med, _ = wait(w / total)
        out.append(f'  {name:<10}{tier:<11}mean {mean:>7.1f}   median {med:>5d}   ({med / EGGS_PER_MINUTE:.0f} min)')
    return '\n'.join(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--rolls', type=int, default=100000)
    ap.add_argument('--seed', type=int, default=20261018)
    a = ap.parse_args()
    print(report(*run(a.runner, a.rolls, a.seed)))
