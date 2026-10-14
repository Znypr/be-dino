#!/usr/bin/env python3
"""Monte Carlo model of the Base -> Gold -> Emerald -> Diamond fusion ladder (BD-057/BD-058).

MODEL, NOT MEASURED GAMEPLAY. DEFAULT scenario = the owner-chosen ladder (2026-10-13):
Gold = 50 Base, Emerald = 10 Gold, Diamond = 3 Emerald, at 40 eggs per 500 food. The old
10-Base-Gold candidates remain as a comparison: pass `--gold-donors 10 --emerald-donors 2 3 4 5
--diamond-donors 2 3 4 --eggs-small 15 --eggs-big 150`. See docs/57-fusion-ladder-options.md.

Model (numbers read from the repo):
  * One egg -> hatch success ps = 1 - P(cracked) * (1 - 0.2) at the chosen condition-upgrade
    tier (ProgressionConfig.ConditionWeights / Conditions). Tier 0 => 60%.
  * A successful egg yields exactly ONE dino (owner decision 2026-10-13).
  * Species by Config.ChestSpeciesWeights (22 species, sum 100); pattern uniform over 8.
  * Every fusion needs same species AND same pattern, and the output keeps that cell, so a
    recipe with d Gold donors (Emerald) and e Emerald donors (Diamond) costs exactly
    G*d*e Base dinos of ONE species+pattern (G = Gold donors, 50 by default) "cell" (176 cells).
  * No pattern research, no Robux, no trading, no donors lost to protection rules.
Pure standard library, deterministic seeds.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = 8
GOLD_DONORS = 50  # owner decision 2026-10-13 (the old candidates used 10)


def load_species_weights(path=None):
    text = (path or ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    block = re.search(r"ChestSpeciesWeights\s*=\s*\{(.*?)\n\s*\},", text, re.S).group(1)
    return [(m[0], float(m[1])) for m in re.findall(r'speciesId = "(\w+)", weight = ([\d.]+)', block)]


def load_conditions(path=None):
    text = (path or ROOT / "src/shared/ProgressionConfig.luau").read_text(encoding="utf-8")
    block = re.search(r"ConditionWeights=\{(.*?)\n    \},", text, re.S).group(1)
    rows = [[int(x) for x in r.split(",")] for r in re.findall(r"\{([\d,]+)\}", block)]
    cracked = float(re.search(r'id="cracked".*?hatchChance=([\d.]+)', text).group(1))
    return rows, cracked


def hatch_success(tier, rows=None, cracked_hatch=None):
    if rows is None:
        rows, cracked_hatch = load_conditions()
    w = rows[tier]
    return 1 - (w[0] / sum(w)) * (1 - cracked_hatch)


def cell_probs(species):
    total = sum(w for _, w in species)
    return [w / total / PATTERNS for _, w in species for _ in range(PATTERNS)]


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(p * len(sorted_vals)))]


def summarize(vals):
    s = sorted(vals)
    return {"mean": sum(s) / len(s), "p10": pct(s, .10), "p50": pct(s, .50), "p90": pct(s, .90)}


def geometric(rng, q):
    """Trials until first success (>=1) with success probability q."""
    if q >= 1:
        return 1
    return 1 + int(math.log(1.0 - rng.random()) / math.log(1.0 - q))


def targeted(bs, q, trials, seed):
    """Eggs until a SPECIFIC cell holds B base dinos, for every B, with common random
    numbers across B (results are monotone in B). q = P(one egg yields that cell)."""
    rng = random.Random(seed)
    bmax = max(bs)
    want = set(bs)
    out = {b: [] for b in bs}
    for _ in range(trials):
        eggs = 0
        for k in range(1, bmax + 1):
            eggs += geometric(rng, q)
            if k in want:
                out[k].append(eggs)
    return {b: summarize(v) for b, v in out.items()}


def any_cell(bs, probs, ps, trials, seed):
    """Eggs until ANY cell holds B base dinos (first to reach). Exact discrete simulation;
    all B are read off the same stream (monotone in B)."""
    rng = random.Random(seed)
    cum = list(itertools.accumulate(probs))
    n = len(probs)
    bmax = max(bs)
    want = set(bs)
    out = {b: [] for b in bs}
    lg = math.log(1.0 - ps) if ps < 1 else None
    rn = range(n)
    for _ in range(trials):
        counts = [0] * n
        top = 0
        eggs = 0
        while top < bmax:
            for c in rng.choices(rn, cum_weights=cum, k=512):
                eggs += 1 if lg is None else 1 + int(math.log(1.0 - rng.random()) / lg)
                v = counts[c] + 1
                counts[c] = v
                if v > top:
                    top = v
                    if v in want:
                        out[v].append(eggs)
                    if v >= bmax:
                        break
    return {b: summarize(v) for b, v in out.items()}


def player_profiles(a):
    casual = a.casual_runs * a.eggs_small
    heavy = (a.heavy_runs - a.heavy_big_runs) * a.eggs_small + a.heavy_big_runs * a.eggs_big
    return {
        "casual": {"eggs_day": casual, "runs_day": a.casual_runs, "eggs_run": casual / a.casual_runs},
        "heavy": {"eggs_day": heavy, "runs_day": a.heavy_runs, "eggs_run": heavy / a.heavy_runs},
    }


def recipes(a):
    g = a.gold_donors
    rows = [(f"Gold = {g} Base", g)]
    for d in a.emerald_donors:
        rows.append((f"Emerald = {d} Gold", g * d))
    for d in a.emerald_donors:
        for e in a.diamond_donors:
            rows.append((f"Diamond = {e} Emerald (Emerald = {d} Gold)", g * d * e))
    return rows


def run(a):
    species = load_species_weights()
    ps = hatch_success(a.tier)
    rows = recipes(a)
    bs = sorted({b for _, b in rows})
    total = sum(w for _, w in species)
    sp = dict(species)
    res = {"ps": ps, "profiles": player_profiles(a), "targets": {}, "recipes": rows, "seed": a.seed}
    for sid in a.targets:
        q = sp[sid] / total / PATTERNS * ps
        res["targets"][sid] = {"q": q, "res": targeted(bs, q, a.trials, a.seed)}
    res["any"] = any_cell(bs, cell_probs(species), ps, a.any_trials, a.seed + 1) if a.any_trials else {}
    return res


def fmt_days(eggs, per_day):
    d = eggs / per_day
    return f"{d:.1f}" if d < 10 else f"{d:.0f}"


def render(r):
    p = r["profiles"]
    L = [f"Hatch success ps={r['ps']:.3f}; casual {p['casual']['eggs_day']:.0f} eggs/day, heavy {p['heavy']['eggs_day']:.0f} eggs/day"]
    views = [(f"target {t}", r["targets"][t]["res"]) for t in r["targets"]]
    if r["any"]:
        views.append(("ANY one species+pattern", r["any"]))
    for name, res in views:
        L.append(f"\n## {name}")
        L.append("| Recipe | Base needed | eggs p10 | p50 | p90 | mean | runs p50 (casual) | days p50 casual | days p50 heavy | days p10-p90 casual |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for label, b in r["recipes"]:
            s = res[b]
            L.append(
                f"| {label} | {b} | {s['p10']:.0f} | {s['p50']:.0f} | {s['p90']:.0f} | {s['mean']:.0f} | "
                f"{s['p50'] / p['casual']['eggs_run']:.0f} | {fmt_days(s['p50'], p['casual']['eggs_day'])} | "
                f"{fmt_days(s['p50'], p['heavy']['eggs_day'])} | "
                f"{fmt_days(s['p10'], p['casual']['eggs_day'])}-{fmt_days(s['p90'], p['casual']['eggs_day'])} |")
    return "\n".join(L)


def check():
    """CI-safe: seeded 2k-trial run, monotonicity and sanity asserts. Must take < 10 s."""
    t0 = time.time()
    species = load_species_weights()
    assert len(species) == 22 and abs(sum(w for _, w in species) - 100) < 1e-9, "species weights"
    ps0 = hatch_success(0)
    assert abs(ps0 - 0.6) < 1e-9, f"tier-0 hatch success should be 0.6, got {ps0}"
    rows, ch = load_conditions()
    assert all(hatch_success(t, rows, ch) <= hatch_success(t + 1, rows, ch) for t in range(len(rows) - 1)), \
        "condition upgrades must not lower hatch success"
    bs = [10, 20, 30, 40, 60]
    q = 25 / 100 / PATTERNS * ps0
    tg = targeted(bs, q, 2000, 7)
    an = any_cell(bs, cell_probs(species), ps0, 2000, 8)
    for name, res in (("targeted", tg), ("any", an)):
        for lo, hi in zip(bs, bs[1:]):
            for k in ("mean", "p10", "p50", "p90"):
                assert res[lo][k] <= res[hi][k], f"{name}: B={hi} cheaper than B={lo} at {k}"
    for b in bs:
        assert an[b]["mean"] <= tg[b]["mean"], "any-cell must not be slower than a fixed cell"
    assert abs(tg[10]["mean"] / (10 / q) - 1) < 0.06, "targeted MC mean off analytic B/q"
    own = [50, 500, 1500]
    og = targeted(own, q, 300, 5)
    assert og[50]["p50"] < og[500]["p50"] < og[1500]["p50"], "owner ladder must be monotone"
    assert abs(og[50]["mean"] / (50 / q) - 1) < 0.15, "owner Gold targeted mean off analytic B/q"
    cfg = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    assert re.search(r"FoodCatchRate = 40 / 500", cfg), "owner decision 2026-10-13: 40 catches per 500 food"
    assert targeted([10], q, 200, 3) == targeted([10], q, 200, 3), "not deterministic"
    dt = time.time() - t0
    assert dt < 10, f"check too slow: {dt:.1f}s"
    print(f"fusion ladder sim check OK in {dt:.1f}s (any-cell Gold p50={an[10]['p50']} eggs; "
          f"compy-cell Gold mean={tg[10]['mean']:.0f} eggs)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="BD-057/058 fusion ladder Monte Carlo (model, not measured)")
    ap.add_argument("--check", action="store_true", help="fast CI-safe monotonicity/sanity check")
    ap.add_argument("--seed", type=int, default=57)
    ap.add_argument("--trials", type=int, default=5000, help="targeted Monte Carlo trials")
    ap.add_argument("--any-trials", type=int, default=300, help="any-cell Monte Carlo trials (slower)")
    ap.add_argument("--tier", type=int, default=0, help="condition upgrade tier 0-6")
    ap.add_argument("--targets", nargs="*", default=["compy", "triceratops", "tyrannosaurus"])
    ap.add_argument("--emerald-donors", type=int, nargs="*", default=[10])
    ap.add_argument("--diamond-donors", type=int, nargs="*", default=[3])
    ap.add_argument("--gold-donors", type=int, default=GOLD_DONORS)
    ap.add_argument("--eggs-small", type=int, default=40)
    ap.add_argument("--eggs-big", type=int, default=400)
    ap.add_argument("--casual-runs", type=int, default=3, help="runs/day, all small")
    ap.add_argument("--heavy-runs", type=int, default=10, help="runs/day")
    ap.add_argument("--heavy-big-runs", type=int, default=3, help="of the heavy runs, how many are big (5,000-food, 400-egg) runs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        check()
        return 0
    r = run(a)
    print(json.dumps(r, indent=1) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
