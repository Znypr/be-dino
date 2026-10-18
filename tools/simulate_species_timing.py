#!/usr/bin/env python3
"""BD-1032: how long until a new kind of dinosaur shows up? Reads the real species odds from src/shared/Config.luau.

    python tools/simulate_species_timing.py                       # 3 eggs a minute, runs of 15 eggs
    python tools/simulate_species_timing.py --eggs-per-minute 4 --run-size 40
    python tools/simulate_species_timing.py --trials 0            # exact table only, no sampled check

Prints, for "first Uncommon / Rare / Epic / Legendary (or better)", the median and 90th percentile of the wait in eggs and in
minutes, and the chance of a Rare-or-better in the first 12 and 90 eggs (--within). "Median" means half of all players have
their first one by then; "90th percentile" means nine in ten do.

The table is exact (a geometric wait: every egg is an independent draw, boost fixed by the run size). The sampled check hatches
real eggs one by one with a seeded random generator and must agree with it. PROVISIONAL numbers (docs/186 s3); no Studio or
player data behind them. The boost formula mirrors RewardMath.speciesWeights (the verifiers keep them equal).
"""
from __future__ import annotations

import argparse
import math
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src/shared/Config.luau"
TIERS = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]


def load_config(path: Path = CONFIG) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    block = re.search(r"ChestSpeciesWeights\s*=\s*\{(.*?)\n\s*\},", text, re.S).group(1)
    weights = [(m[0], float(m[1])) for m in re.findall(r'speciesId = "(\w+)", weight = ([\d.]+)', block)]
    rar_block = re.search(r"SpeciesRarities\s*=\s*\{(.*?)\n    \},", text, re.S).group(1)
    tiers = {k: int(v) for k, v in re.findall(r"(\w+) = (\d)", rar_block)}
    boost = [float(x) for x in re.search(r"SpeciesRunBoost\s*=\s*\{([^}]*)\}", text).group(1).split(",")]
    free = re.search(r"EggRarityBoostFreeEggs\s*=\s*(\d+)", text)
    return {"weights": weights, "tiers": tiers, "boost": boost,
            "free": int(free.group(1)) if free else 1,
            "max": int(re.search(r"EggRarityBoostMaxEggs\s*=\s*(\d+)", text).group(1))}


def tier_chances(cfg: dict, run_size: int = 1) -> list[float]:
    """Chance per egg of each tier (Common..Legendary) for an egg from a batch of `run_size` eggs; a single shop egg is run_size 1."""
    free, top = cfg["free"], cfg["max"]
    s = min(1.0, max(0.0, (run_size - free) / max(1, top - free)))
    out = [0.0] * len(TIERS)
    for species, weight in cfg["weights"]:
        tier = cfg["tiers"][species]
        out[tier - 1] += weight * (1 + s * (cfg["boost"][tier - 1] - 1))
    total = sum(out)
    return [x / total for x in out]


def p_at_least(chances: list[float], tier_index: int) -> float:
    """Chance per egg of tier `tier_index` (0 = Common) or better."""
    return sum(chances[tier_index:])


def eggs_to_quantile(p: float, q: float) -> int:
    """Smallest number of eggs n with P(first success within n eggs) >= q."""
    if p >= 1:
        return 1
    return max(1, math.ceil(math.log(1 - q) / math.log(1 - p)))


def chance_within(p: float, eggs: int) -> float:
    return 1 - (1 - p) ** eggs


def table(cfg: dict, eggs_per_minute: float, run_size: int, within=(12, 90)) -> dict:
    chances = tier_chances(cfg, run_size)
    rows = []
    for index in range(1, len(TIERS)):
        p = p_at_least(chances, index)
        med, p90 = eggs_to_quantile(p, 0.5), eggs_to_quantile(p, 0.9)
        rows.append({"tier": TIERS[index], "p": p, "median_eggs": med, "median_min": med / eggs_per_minute,
                     "p90_eggs": p90, "p90_min": p90 / eggs_per_minute})
    rare = p_at_least(chances, 2)
    return {"chances": chances, "rows": rows, "rare_within": {n: chance_within(rare, n) for n in within}}


def sample(cfg: dict, run_size: int, trials: int, seed: int = 1018) -> dict:
    """Hatch eggs one by one until a Legendary has appeared; returns the sampled median eggs to the first Uncommon+/Rare+/Epic+/Legendary."""
    chances = tier_chances(cfg, run_size)
    cum, acc = [], 0.0
    for c in chances:
        acc += c
        cum.append(acc)
    rng = random.Random(seed)
    firsts = {i: [] for i in range(1, len(TIERS))}
    for _ in range(trials):
        seen = {}
        n = 0
        while len(seen) < len(TIERS) - 1:
            n += 1
            u = rng.random()
            tier = next((i for i, c in enumerate(cum) if u <= c), len(cum) - 1)
            for i in range(1, tier + 1):
                seen.setdefault(i, n)
        for i, v in seen.items():
            firsts[i].append(v)
    return {TIERS[i]: sorted(v)[len(v) // 2] for i, v in firsts.items()}


def render(cfg: dict, eggs_per_minute: float, run_size: int, within=(12, 90), trials: int = 0) -> str:
    t = table(cfg, eggs_per_minute, run_size, within)
    lines = [f"Species timing: {eggs_per_minute:g} eggs a minute, every egg from a run of {run_size} eggs (PROVISIONAL, docs/186 s3)",
             "Per egg: " + "  ".join(f"{name} {c * 100:.3g}%" for name, c in zip(TIERS, t["chances"])),
             "",
             "| First one of this kind or better | Chance per egg | Median wait | 90th percentile wait |",
             "|---|---:|---:|---:|"]
    for r in t["rows"]:
        lines.append(f"| {r['tier']} | {r['p'] * 100:.3g}% | {r['median_eggs']} eggs, {r['median_min']:.1f} min | {r['p90_eggs']} eggs, {r['p90_min']:.1f} min |")
    lines.append("")
    for n, chance in t["rare_within"].items():
        lines.append(f"Chance of a Rare or better in the first {n} eggs ({n / eggs_per_minute:.0f} min): {chance * 100:.1f}%")
    if trials > 0:
        s = sample(cfg, run_size, trials)
        lines.append("")
        lines.append(f"Sampled check ({trials} seeded players, median eggs): " + ", ".join(f"{k} {v}" for k, v in s.items()))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--eggs-per-minute", type=float, default=3.0, help="eggs hatched a minute (default 3: a 5 minute run is about 15 eggs)")
    parser.add_argument("--run-size", type=int, default=15, help="size of the batch each egg comes from (default 15, a normal run)")
    parser.add_argument("--within", type=int, nargs="+", default=[12, 90], help="egg counts for the 'Rare or better within' lines")
    parser.add_argument("--trials", type=int, default=1000, help="seeded players for the sampled check (0 = skip)")
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args(argv)
    print(render(load_config(args.config), args.eggs_per_minute, args.run_size, tuple(args.within), args.trials))
    return 0


if __name__ == "__main__":
    sys.exit(main())
