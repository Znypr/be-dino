#!/usr/bin/env python3
"""Monte Carlo model of the Base -> Gold -> Emerald -> Diamond fusion ladder (BD-057/BD-058).

CURRENT LADDER (owner 2026-10-15, docs/90): Gold = 6 Base of one species (ANY pattern, the Gold keeps the
plurality pattern), Emerald = 3 Gold and Diamond = 2 Emerald (same species + pattern), at 4 eggs per run.
The default run (`python tools/simulate_fusion_ladder.py`) prints the docs/90 table with the v2 model below
(`ladder_v2`). Everything after this paragraph describes the OLDER same-pattern model, kept for comparison
(`--legacy`).

MODEL, NOT MEASURED GAMEPLAY. DEFAULT scenario = the owner-approved ladder (2026-10-14):
Gold = 15 Base, Emerald = 4 Gold, Diamond = 2 Emerald, at 4 eggs per 500 food (BD-165; was 40) (supersedes
50/10/3 of 2026-10-13). The old candidates remain as a comparison: pass `--gold-donors 50
--emerald-donors 10 --diamond-donors 3` (previous ladder) or `--gold-donors 10 --emerald-donors
2 3 4 5 --diamond-donors 2 3 4 --eggs-small 15 --eggs-big 150`. See docs/57-fusion-ladder-options.md.
`--hours` prints median hours of heavy play to the FIRST Gold / Emerald / Diamond of any one
species+pattern at an assumed 180 hatched dinos per hour (1 h = 180 dinos).

Model (numbers read from the repo):
  * One egg -> hatch success ps = 1 - P(cracked) * (1 - 0.2) at the chosen condition-upgrade
    tier (ProgressionConfig.ConditionWeights / Conditions). Tier 0 => 60%.
  * A successful egg yields exactly ONE dino (owner decision 2026-10-13).
  * Species by Config.ChestSpeciesWeights (22 species, sum 100); pattern uniform over 8.
  * Every fusion needs same species AND same pattern, and the output keeps that cell, so a
    recipe with d Gold donors (Emerald) and e Emerald donors (Diamond) costs exactly
    G*d*e Base dinos of ONE species+pattern (G = Gold donors, 15 by default) "cell" (176 cells).
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
GOLD_DONORS = 15  # owner decision 2026-10-14 (50 on 2026-10-13; the oldest candidates used 10)
DINOS_PER_HOUR = 180  # planning assumption: 1 h of heavy play = 180 hatched dinos


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


def hours_to_cells(res, dinos_per_hour=DINOS_PER_HOUR):
    """Median hours (p50 of the any-cell race) per Base-count, from eggs via hatch success."""
    ps = hatch_success(0)
    return {b: s["p50"] * ps / dinos_per_hour for b, s in res.items()}


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


V2_RECIPE = (6, 3, 2)  # Gold = 6 Base (any pattern), Emerald = 3 Gold, Diamond = 2 Emerald (same pattern)
RUNS_PER_HOUR = 15  # a 4-minute run


def ladder_v2(species, gold=6, emerald=3, diamond=2, rule="plurality", seed=1, eggs=4, ps=0.6, cap=8000):
    """First run index at which each (species, stage) exists for one simulated casual player.
    rule: 'plurality' (Gold any pattern, Emerald/Diamond same pattern), 'same' (old: same pattern everywhere).
    The player is assumed to pick donors well: the pattern with the most stock is fused first.
    Returns {(speciesId, 'g'|'e'|'d'): run}; missing key = not reached within `cap` runs."""
    rng = random.Random(seed)
    names = [n for n, _ in species]
    weights = [w for _, w in species]
    base, gold_s, em_s, first = {}, {}, {}, {}
    for run_no in range(1, cap):
        for _ in range(eggs):
            if rng.random() > ps:
                continue
            s = rng.choices(names, weights)[0]
            p = rng.randrange(PATTERNS)
            b = base.setdefault(s, [0] * PATTERNS)
            b[p] += 1
            while (max(b) >= gold) if rule == "same" else (sum(b) >= gold):
                pm = max(range(PATTERNS), key=lambda i: b[i])
                need = gold
                for i in [pm] + sorted((j for j in range(PATTERNS) if j != pm), key=lambda j: b[j]):
                    t = min(b[i], need)
                    b[i] -= t
                    need -= t
                gold_s.setdefault(s, [0] * PATTERNS)[pm] += 1
                first.setdefault((s, "g"), run_no)
            g = gold_s.get(s)
            while g and max(g) >= emerald:
                pm = max(range(PATTERNS), key=lambda i: g[i])
                g[pm] -= emerald
                em_s.setdefault(s, [0] * PATTERNS)[pm] += 1
                first.setdefault((s, "e"), run_no)
            e = em_s.get(s)
            if e and max(e) >= diamond:
                first.setdefault((s, "d"), run_no)
    return first


def v2_table(trials=40, cap=8000, seed=90, targets=("compy", "stegosaurus", "triceratops"), recipe=V2_RECIPE, rule="plurality", eggs=4):
    species = load_species_weights()
    res = {(t_, st): [] for t_ in targets for st in "ged"}
    anyc = {st: [] for st in "ged"}
    commons = [n for n, _ in species[:5]]  # the five Common species
    for k in range(trials):
        f = ladder_v2(species, *recipe, rule=rule, seed=seed + k, cap=cap, eggs=eggs)
        for key in res:
            res[key].append(f.get(key, cap))
        for st in "ged":
            hit = [f[(s, st)] for s in commons if (s, st) in f]
            anyc[st].append(min(hit) if hit else cap)
    return res, anyc


def render_v2(trials, cap, recipe=V2_RECIPE, rule="plurality", eggs=4):
    res, anyc = v2_table(trials, cap, recipe=recipe, rule=rule, eggs=eggs)
    med = lambda v: sorted(v)[len(v) // 2]
    out = [f"Ladder {recipe[0]}/{recipe[1]}/{recipe[2]} ({rule}), {eggs} eggs per step (a step is one 4-minute run when eggs = 4), hatch success 60%, {RUNS_PER_HOUR} steps/h, "
           f"{trials} players, cap {cap} runs (a value at the cap means NOT reached)",
           "| Target | Gold runs p50 (h) | Emerald runs p50 (h) | Diamond runs p50 (h) |", "|---|---:|---:|---:|"]

    def cell(v):
        m = med(v)
        return f">{cap} (>{cap / RUNS_PER_HOUR:.0f} h)" if m >= cap else f"{m} ({m / RUNS_PER_HOUR:.1f} h)"
    out.append("| any Common species | " + " | ".join(cell(anyc[s]) for s in "ged") + " |")
    for tgt in sorted({k[0] for k in res}):
        out.append(f"| {tgt} | " + " | ".join(cell(res[(tgt, s)]) for s in "ged") + " |")
    return "\n".join(out)


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
    fusion = (ROOT / "src/server/IdentityFusion.luau").read_text(encoding="utf-8")
    counts = [int(x) for x in re.findall(r"donorCount = (\d+),", fusion)]
    assert counts == list(V2_RECIPE), f"IdentityFusion recipes must be 6/3/2, got {counts}"
    assert "anyPattern = true" in fusion.split("emerald =")[0], "Gold must be the any-pattern recipe"
    # v2 pacing sanity (docs/90): first Gold of any Common in ~5-10 casual runs, Common Diamond within a few hundred runs.
    res, anyc = v2_table(trials=12, cap=1500, targets=("compy",))
    med = lambda v: sorted(v)[len(v) // 2]
    assert 4 <= med(anyc["g"]) <= 12, f"any-Common first Gold p50 {med(anyc['g'])} runs, outside 4-12"
    assert med(res[("compy", "g")]) <= 20 and med(res[("compy", "g")]) < med(res[("compy", "e")]) < med(res[("compy", "d")]), "ladder must be monotone"
    assert med(res[("compy", "d")]) < 1500, "Common Diamond must be reachable"
    old = v2_table(trials=6, cap=1500, targets=("compy",), recipe=(6, 3, 2), rule="same")[0]
    assert med(old[("compy", "d")]) > med(res[("compy", "d")]), "same-pattern-everywhere must be slower than the chosen ladder"
    cfg = (ROOT / "src/shared/Config.luau").read_text(encoding="utf-8")
    assert re.search(r"FoodCatchRate = 12 / 500", cfg), "owner decision 2026-10-16: 12 catches per 500 food (BD-418)"
    assert targeted([10], q, 200, 3) == targeted([10], q, 200, 3), "not deterministic"
    assert ladder_v2(species, seed=3, cap=200) == ladder_v2(species, seed=3, cap=200), "v2 not deterministic"
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
    ap.add_argument("--emerald-donors", type=int, nargs="*", default=[4])
    ap.add_argument("--diamond-donors", type=int, nargs="*", default=[2])
    ap.add_argument("--gold-donors", type=int, default=GOLD_DONORS)
    ap.add_argument("--eggs-small", type=int, default=4)
    ap.add_argument("--eggs-big", type=int, default=40)
    ap.add_argument("--casual-runs", type=int, default=3, help="runs/day, all small")
    ap.add_argument("--heavy-runs", type=int, default=10, help="runs/day")
    ap.add_argument("--heavy-big-runs", type=int, default=3, help="of the heavy runs, how many are big (5,000-food, 40-egg) runs")
    ap.add_argument("--hours", action="store_true", help="print median hours to first Gold/Emerald/Diamond (any one species+pattern) at 180 dinos/h")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--legacy", action="store_true", help="run the older same-pattern model (docs/57) instead of the docs/90 table")
    ap.add_argument("--v2-trials", type=int, default=40)
    ap.add_argument("--v2-cap", type=int, default=8000, help="max runs simulated per player")
    ap.add_argument("--v2-recipe", type=int, nargs=3, default=list(V2_RECIPE), metavar=("GOLD", "EMERALD", "DIAMOND"))
    ap.add_argument("--v2-eggs", type=int, default=4, help="eggs per step (4 = one run; 13 = a run plus a 9-egg nest)")
    ap.add_argument("--v2-rule", choices=("plurality", "same"), default="plurality")
    a = ap.parse_args(argv)
    if a.check:
        check()
        return 0
    if not a.legacy and not a.hours:
        print(render_v2(a.v2_trials, a.v2_cap, tuple(a.v2_recipe), a.v2_rule, a.v2_eggs))
        return 0
    if a.hours:
        species = load_species_weights()
        bs = sorted({b for _, b in recipes(a)})
        hrs = hours_to_cells(any_cell(bs, cell_probs(species), hatch_success(a.tier), max(a.any_trials, 1000), a.seed + 1))
        for label, b in recipes(a):
            print(f"{label}: {b} Base, median {hrs[b]:.1f} h at {DINOS_PER_HOUR} dinos/h")
        return 0
    r = run(a)
    print(json.dumps(r, indent=1) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
