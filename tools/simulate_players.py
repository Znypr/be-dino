#!/usr/bin/env python3
"""BD-1200 layer 1: simulate persona kids playing Be Dino! for 30 days, with the game's real egg numbers.

    python tools/simulate_players.py                  # every persona, 400 players each, 30 days
    python tools/simulate_players.py --days 60 --players 1000 --seed 7
    python tools/simulate_players.py --streak         # what-if: a daily-streak reward that counts as "something new" on days 3 and 7 (BD-1197)
    python tools/simulate_players.py --play-again     # what-if: the PLAY AGAIN button (BD-1199, docs/239): +1 run a session, a run streak 3 / 5 counts as a small "new" moment
    python tools/simulate_players.py --play-again --streak-first-only   # same, but only the FIRST time a kid ever reaches run streak 3 and 5 is "new" (the cautious reading)

What it reads from src/shared/Config.luau (through tools/simulate_species_timing.py): the species weights, the rarity tiers and the
run-size boost; FoodCatchRate (eggs per food) and RunEggMaxPerRun. What it ASSUMES (PROVISIONAL, written here, not data): the
personas below, food per run, sessions per day, and a simple quit rule: a kid quits after `patience` sessions in a row in which
nothing new happened (no new species, no first-of-a-tier, no first Gold). Cracked-egg failures, mutations, nests and crystals
are left out (they only add "new" moments, so the real game should do a little better than this).

It answers: when does each kind of kid get the first Rare / Epic / Legendary / Gold, how many species by day 7 and 30, how long
is the longest stretch with nothing new, and how many are still playing on day 1 / 7 / 30. It is a design tool, not a
prediction of real retention (only real players give that, docs/235).
"""
from __future__ import annotations

import argparse
import random
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulate_species_timing as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src/shared/Config.luau"
GOLD_INPUTS = 6  # docs/90: 6 Base of one species make a Gold


@dataclass
class Persona:
    name: str
    about: str
    days_per_week: float  # chance per day = days_per_week / 7
    sessions_per_day: int
    runs_per_session: int
    food_per_run: int  # skill: food eaten in one run
    patience: int  # sessions in a row with nothing new before quitting


PERSONAS = [
    Persona("Noah", "6, new to Roblox, slow learner, short visits", 3, 1, 2, 300, 2),
    Persona("Mia", "7, casual, loves Adopt Me, cute collector", 4, 1, 3, 500, 3),
    Persona("Ava", "8, collector, fills every Index page", 5, 1, 4, 650, 4),
    Persona("Sam", "9, explorer, plays a few runs then wanders", 4, 1, 3, 600, 3),
    Persona("Leo", "11, grinder, Pet Simulator 99 veteran", 6, 2, 5, 900, 5),
]


def load(path: Path = CONFIG) -> dict:
    cfg = st.load_config(path)
    text = path.read_text(encoding="utf-8")
    num, den = re.search(r"FoodCatchRate\s*=\s*([\d.]+)\s*/\s*([\d.]+)", text).groups()
    cfg["catch"] = float(num) / float(den)
    cfg["cap"] = int(re.search(r"RunEggMaxPerRun\s*=\s*(\d+)", text).group(1))
    by_tier: dict[int, list[tuple[str, float]]] = {}
    for sid, w in cfg["weights"]:
        by_tier.setdefault(cfg["tiers"].get(sid, 1), []).append((sid, w))
    cfg["by_tier"] = by_tier
    return cfg


def eggs_for(cfg: dict, food: int, rng: random.Random) -> int:
    food = max(0, int(rng.gauss(food, food * 0.2)))  # runs vary
    return min(cfg["cap"], int(food * cfg["catch"]))


def hatch(cfg: dict, run_size: int, rng: random.Random) -> tuple[str, int]:
    chances = st.tier_chances(cfg, run_size)
    r, tier = rng.random(), 1
    for i, p in enumerate(chances):
        r -= p
        if r <= 0:
            tier = i + 1
            break
    pool = cfg["by_tier"].get(tier) or cfg["by_tier"][1]
    total = sum(w for _, w in pool)
    r = rng.random() * total
    for sid, w in pool:
        r -= w
        if r <= 0:
            return sid, tier
    return pool[-1][0], tier


def play(cfg: dict, p: Persona, days: int, rng: random.Random, streak: bool, again: str = "") -> dict:
    owned: dict[str, int] = {}
    tiers_seen: set[int] = set()
    first: dict[str, float] = {}
    quiet = longest = 0
    last_day = 0
    gold = False
    streak_days = 0
    run_milestones: set[int] = set()  # BD-1199: run streaks 3 and 5 already seen (first-only reading)
    species_at = {}
    for day in range(1, days + 1):
        if rng.random() > p.days_per_week / 7:
            streak_days = 0
            continue
        streak_days += 1
        last_day = day
        for _ in range(p.sessions_per_day):
            new = False
            runs = p.runs_per_session + (1 if again else 0)  # BD-1199: the button makes the next run one tap away (ASSUMPTION: +1 run a session)
            for run_no in range(1, runs + 1):
                if again and run_no in (3, 5) and (again == "every" or run_no not in run_milestones):
                    run_milestones.add(run_no)  # run streak 3 / 5: the soft "Run streak 3!" and its crystals, a small new moment
                    new = True
                n = eggs_for(cfg, p.food_per_run, rng)
                for _ in range(n):
                    sid, tier = hatch(cfg, n, rng)
                    if sid not in owned:
                        new = True
                    owned[sid] = owned.get(sid, 0) + 1
                    if tier not in tiers_seen:
                        tiers_seen.add(tier)
                        new = True
                        name = st.TIERS[tier - 1] if tier - 1 < len(st.TIERS) else str(tier)
                        first.setdefault(name, day)
                    if not gold and owned[sid] >= GOLD_INPUTS:
                        gold = True
                        new = True
                        first.setdefault("Gold", day)
            if streak and streak_days in (3, 7):
                new = True
            quiet = 0 if new else quiet + 1
            longest = max(longest, quiet)
            if quiet >= p.patience:
                return {"first": first, "species": len(owned), "species_at": species_at, "longest": longest, "quit": day}
        species_at[day] = len(owned)
    return {"first": first, "species": len(owned), "species_at": species_at, "longest": longest, "quit": None, "last": last_day}


def summarize(cfg: dict, p: Persona, players: int, days: int, seed: int, streak: bool, again: str = "") -> dict:
    rng = random.Random(f"{seed}-{p.name}-{streak}")  # the same seed with and without --play-again: only the what-if differs
    res = [play(cfg, p, days, rng, streak, again) for _ in range(players)]
    def still(d):  # still playing on day d (has not quit before it)
        return sum(1 for r in res if r["quit"] is None or r["quit"] > d) / players
    def med_first(k):
        v = [r["first"][k] for r in res if k in r["first"]]
        return (statistics.median(v), len(v) / players) if v else (None, 0.0)
    def sp_at(d):
        v = [max([n for dd, n in r["species_at"].items() if dd <= d], default=0) for r in res]
        return statistics.median(v)
    return {"persona": p, "d1": still(1), "d7": still(7), "d30": still(min(30, days)),
            "rare": med_first("Rare"), "epic": med_first("Epic"), "legendary": med_first("Legendary"), "gold": med_first("Gold"),
            "sp7": sp_at(7), "sp30": sp_at(min(30, days)), "longest": statistics.median(r["longest"] for r in res)}


def fmt_first(v):
    day, share = v
    return "never" if day is None else f"day {day:g} ({share:.0%})"


def render(rows: list[dict], cfg: dict, days: int, players: int, streak: bool, again: str = "") -> str:
    out = [f"Be Dino! player simulation (BD-1200), {players} players per persona, {days} days, catch {cfg['catch']*500:.0f} eggs per 500 food"
           + (", WITH daily streak (days 3 and 7 count as new)" if streak else "")
           + (", WITH PLAY AGAIN (+1 run a session; run streak 3 and 5 count as new" + (" every session)" if again == "every" else ", first time only)") if again else ""),
           "Still playing = has not quit by that day (quit = `patience` sessions in a row with nothing new). PROVISIONAL personas.", ""]
    out.append(f"{'persona':<7} {'still D1':>8} {'D7':>5} {'D30':>5}  {'first Rare':<16} {'first Epic':<16} {'first Legendary':<16} {'first Gold':<16} {'species D7/D30':>14} {'longest quiet':>13}")
    for r in rows:
        p = r["persona"]
        out.append(f"{p.name:<7} {r['d1']:>8.0%} {r['d7']:>5.0%} {r['d30']:>5.0%}  {fmt_first(r['rare']):<16} {fmt_first(r['epic']):<16} "
                   f"{fmt_first(r['legendary']):<16} {fmt_first(r['gold']):<16} {r['sp7']:>6g}/{r['sp30']:<7g} {r['longest']:>13g}")
    out.append("")
    for r in rows:
        p = r["persona"]
        out.append(f"  {p.name}: {p.about}; {p.days_per_week:g} days a week, {p.sessions_per_day} visit(s), {p.runs_per_session} runs, ~{p.food_per_run} food a run, patience {p.patience}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--players", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1200)
    ap.add_argument("--streak", action="store_true", help="what-if: daily streak reward on days 3 and 7 (BD-1197)")
    ap.add_argument("--play-again", action="store_true", help="what-if: PLAY AGAIN button, +1 run a session, run streak 3 and 5 are a small new moment (BD-1199, docs/239)")
    ap.add_argument("--streak-first-only", action="store_true", help="with --play-again: only the first time a kid reaches run streak 3 and 5 counts as new")
    a = ap.parse_args(argv)
    cfg = load()
    again = ("first" if a.streak_first_only else "every") if a.play_again else ""
    rows = [summarize(cfg, p, a.players, a.days, a.seed, a.streak, again) for p in PERSONAS]
    print(render(rows, cfg, a.days, a.players, a.streak, again))
    return 0


if __name__ == "__main__":
    sys.exit(main())
