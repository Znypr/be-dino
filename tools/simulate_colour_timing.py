"""BD-1036 / docs/186 s5: how long until a player hatches a dino with a rarer COLOUR? Plain numbers for the owner.

A dino has two colours; the colour rarity it shows is the rarer of the two (docs/186 s5, ColourBonus.rarity). Reads the REAL
colour table (ProgressionConfig.EggColors) and rolls the REAL Genetics.roll in Luau, so the numbers cannot drift from the game.
A model, not measured play: eggs are independent and EGGS_PER_MINUTE eggs a minute while running (docs/186 s1: about 3, PROVISIONAL).

  python tools/simulate_colour_timing.py --runner C:/.../luau.exe            # table + exact waits + seeded check
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import simulate_pattern_timing as base  # noqa: E402  (wait(), module(), TIERS, EGGS_PER_MINUTE)

DUMP = r'''
for _, c in PC.EggColors do print("ROW|" .. c.id .. "|" .. c.name .. "|" .. c.rarity .. "|" .. c.weight) end
print("SCALE|" .. PC.EggColorWeightScale)
local rarityOf = {} for _, c in PC.EggColors do rarityOf[c.id] = c.rarity end
local counts = {}
math.randomseed(SEED) -- Luau's own generator: same seed, same numbers
local rng = {NextNumber = function() return math.random() end}
for _ = 1, ROLLS do
    local g = G.roll(0, rng)
    local shown = Curve.rarer(rarityOf[g.primaryColorId], rarityOf[g.secondaryColorId])
    counts[shown] = (counts[shown] or 0) + 1
end
for tier, n in counts do print("MC|" .. tier .. "|" .. n) end
print("ROLLS|" .. ROLLS)
'''


def run(runner, rolls, seed):
    m = base.module
    src = ('local Curve=' + m('src/shared/RarityCurve.luau') + '\n'
           'local PC=' + m('src/shared/ProgressionConfig.luau') + '\n'
           'local script={Parent={ProgressionConfig=PC}}\nlocal require=function() return PC end\n'
           'local G=' + m('src/shared/EggGenetics.luau') + '\n'
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


def per_slot(rows, scale):
    """Chance of one colour slot being each tier (index = tier)."""
    out = {t: 0.0 for t in base.TIERS}
    for _, _, tier, w in rows: out[tier] += w / scale
    return out


def dino_tier(rows, scale):
    """Chance that the RARER of two independent colour slots is exactly each tier."""
    slot = per_slot(rows, scale)
    out, below = {}, 0.0
    for t in base.TIERS:
        upto = below + slot[t]
        out[t] = upto ** 2 - below ** 2
        below = upto
    return out


def report(rows, scale, mc, n):
    slot, dino = per_slot(rows, scale), dino_tier(rows, scale)
    out = [f'Colours: {len(rows)} (weights total {sum(w for *_, w in rows)} of {scale}); {base.EGGS_PER_MINUTE} eggs a minute (PROVISIONAL)', '',
           f'{"Tier":<11}{"Colours":>9}{"One slot":>10}{"Dino shows":>12}{"Seeded":>9}']
    for t in base.TIERS:
        names = [name for _, name, tier, _ in rows if tier == t]
        out.append(f'{t:<11}{len(names):>9}{100 * slot[t]:>9.3f}%{100 * dino[t]:>11.3f}%{100 * mc.get(t, 0) / n:>8.3f}%   {", ".join(names)}')
    out += ['', 'Wait for the FIRST dino whose colour rarity (the rarer of its two colours) is at least this tier:',
            f'{"Tier or better":<16}{"Per egg":>9}{"Mean":>9}{"Median":>9}{"9 in 10":>9}{"Median min":>12}']
    for tier in base.TIERS[1:]:
        k = base.TIERS.index(tier)
        p = sum(dino[t] for t in base.TIERS[k:])
        mean, med, p90 = base.wait(p)
        out.append(f'{tier:<16}{100 * p:>8.3f}%{mean:>9.1f}{med:>9d}{p90:>9d}{med / base.EGGS_PER_MINUTE:>12.1f}')
    return '\n'.join(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    ap.add_argument('--rolls', type=int, default=200000)
    ap.add_argument('--seed', type=int, default=20261018)
    a = ap.parse_args()
    print(report(*run(a.runner, a.rolls, a.seed)))
