"""BD-426: summarize exported server logs (lines starting "[BD-TELEMETRY] {json}") into the docs/119 numbers.

    python tools/telemetry_report.py server.log [more.log ...] [--json]

Reads run_end and session_end events only; every other line is ignored. Prints a per-run table (food/min, eggs/min,
eggs per 500 food, minutes in weather and a "vs target (15 eggs / 5 min)" column), then runs, median run length, food per
minute, eggs per 5 minutes (aggregate and median run), end reasons, nests/crystals per run and session shape (runs per
session, hub vs run time). Runs shorter than --min-seconds (default 20) are listed but excluded from per-minute rates because
a run that ended in seconds says nothing about pace.

BD-575: `food_raw` is the REAL raw food points eaten (summed from the server pickups) and `eggs_food` the eggs the food alone
earned before the weather and potion multipliers. The older `food` field is DERIVED (eggs / FoodCatchRate), so a weather
run (thunder x1.4) overstates it; it is still read for comparison and for logs written before BD-575, and every figure
that falls back to it is marked "derived".
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

PREFIX = "[BD-TELEMETRY] "
TARGET_EGGS = 15      # owner target (docs/119): about 15 run eggs ...
TARGET_SECONDS = 300  # ... in a normal 5-minute run


def parse(lines):
    runs, sessions = [], []
    for line in lines:
        at = line.find(PREFIX)
        if at < 0:
            continue
        try:
            event = json.loads(line[at + len(PREFIX):])
        except ValueError:
            continue
        if event.get("event") == "run_end":
            runs.append(event)
        elif event.get("event") == "session_end":
            sessions.append(event)
    return runs, sessions


def _median(values):
    return round(statistics.median(values), 2) if values else None


def run_metrics(run):
    """Per-run figures. Food is the real food_raw when logged (BD-575), else the derived eggs / rate `food` (marked)."""
    seconds = run.get("duration_s", 0)
    real = isinstance(run.get("food_raw"), (int, float))
    food = run["food_raw"] if real else run.get("food", 0)
    eggs = run.get("eggs", 0)
    out = {
        "seconds": seconds,
        "food": food,
        "food_real": real,
        "eggs": eggs,
        "eggs_food": run.get("eggs_food"),
        "weather_min": round(run["weather_s"] / 60, 2) if isinstance(run.get("weather_s"), (int, float)) else None,
        "food_per_min": round(food * 60 / seconds, 1) if seconds else None,
        "eggs_per_min": round(eggs * 60 / seconds, 2) if seconds else None,
        "eggs_per_500_food": round(eggs * 500 / food, 2) if food else None,
        "eggs_per_5min": round(eggs * TARGET_SECONDS / seconds, 2) if seconds else None,
        "vs_target": round(eggs * TARGET_SECONDS / seconds / TARGET_EGGS, 2) if seconds else None,
        "vs_target_food_only": None,
    }
    if seconds and isinstance(run.get("eggs_food"), (int, float)):
        out["vs_target_food_only"] = round(run["eggs_food"] * TARGET_SECONDS / seconds / TARGET_EGGS, 2)
    return out


def summarize(runs, sessions, min_seconds=20):
    rated = [r for r in runs if r.get("duration_s", 0) >= min_seconds]
    seconds = sum(r["duration_s"] for r in rated)
    out = {
        "runs": len(runs),
        "runs_rated": len(rated),
        "median_run_s": _median([r["duration_s"] for r in runs]),
        "end_reasons": dict(Counter(r.get("reason", "Other") for r in runs)),
        "food_is_estimate": any(r.get("food_is_estimate") for r in rated),
        "runs_with_real_food": sum(1 for r in rated if isinstance(r.get("food_raw"), (int, float))),
        # real raw food per minute where food_raw was logged, derived (eggs / rate) for older lines; food_source says which
        "food_per_min": round(sum(run_metrics(r)["food"] for r in rated) * 60 / seconds, 1) if seconds else None,
        # the old derived figure, always computed from `food`, kept so the two can be compared
        "food_per_min_derived": round(sum(r["food"] for r in rated) * 60 / seconds, 1) if seconds else None,
        "eggs_per_500_food": (round(sum(r["eggs"] for r in rated) * 500 / sum(run_metrics(r)["food"] for r in rated), 2)
                              if rated and sum(run_metrics(r)["food"] for r in rated) else None),
        "weather_share": (round(sum(r["weather_s"] for r in rated) / seconds, 3)
                          if seconds and all(isinstance(r.get("weather_s"), (int, float)) for r in rated) else None),
        "eggs_per_5min": round(sum(r["eggs"] for r in rated) * 300 / seconds, 2) if seconds else None,
        "vs_target": round(sum(r["eggs"] for r in rated) * TARGET_SECONDS / seconds / TARGET_EGGS, 2) if seconds else None,
        "eggs_per_5min_median_run": _median([r["eggs"] * 300 / r["duration_s"] for r in rated]),
        "median_eggs_per_run": _median([r["eggs"] for r in runs]),
        "nests_per_run": round(sum(r["nests"] for r in runs) / len(runs), 2) if runs else None,
        "crystals_per_run": round(sum(r["crystals"] for r in runs) / len(runs), 1) if runs else None,
        "per_run": [dict(run_metrics(r), rated=r.get("duration_s", 0) >= min_seconds, reason=r.get("reason", "Other")) for r in runs],
        "sessions": len(sessions),
        "runs_per_session": round(statistics.mean(s["runs"] for s in sessions), 2) if sessions else None,
        "median_session_s": _median([s["total_s"] for s in sessions]),
        "hub_share": None,
    }
    if rated:
        source = {bool(run_metrics(r)["food_real"]) for r in rated}
        out["food_source"] = "real" if source == {True} else "derived" if source == {False} else "mixed"
    else:
        out["food_source"] = None
    time_total = sum(s["hub_s"] + s["run_s"] for s in sessions)
    if time_total:
        out["hub_share"] = round(sum(s["hub_s"] for s in sessions) / time_total, 3)
    return out


def _cell(value, fmt="{}", missing="n/a"):
    return missing if value is None else fmt.format(value)


def render_runs(per_run):
    """One row per run. Food shows `~` when it is the derived eggs / rate figure instead of the real food_raw."""
    head = ["#", "secs", "weather min", "food", "food/min", "eggs", "eggs/min", "eggs/500 food", "food-only eggs",
            "vs target (15 eggs / 5 min)", "food-only vs target"]
    rows = []
    for number, run in enumerate(per_run, 1):
        food = _cell(run["food"], "{}" if run["food_real"] else "~{}")
        per_min = _cell(run["food_per_min"], "{}" if run["food_real"] else "~{}")
        rows.append([
            f"{number}{'' if run['rated'] else '*'}", str(run["seconds"]), _cell(run["weather_min"], "{:.1f}"), food, per_min,
            str(run["eggs"]), _cell(run["eggs_per_min"], "{:.2f}"), _cell(run["eggs_per_500_food"], "{:.1f}"),
            _cell(run["eggs_food"]), _cell(run["vs_target"], "{:.2f}x"), _cell(run["vs_target_food_only"], "{:.2f}x"),
        ])
    widths = [max(len(head[i]), *(len(r[i]) for r in rows)) if rows else len(head[i]) for i in range(len(head))]
    fmt = lambda cells: "  ".join(c.rjust(w) for c, w in zip(cells, widths))
    lines = [fmt(head)] + [fmt(r) for r in rows]
    lines.append("~ = derived food (eggs / FoodCatchRate, weather and potions inflate it); no mark = real food_raw from the pickups. "
                 "* = shorter than the rating minimum, not used in the totals.")
    return "\n".join(lines)


def render(summary):
    def f(key, label, unit=""):
        value = summary[key]
        return f"{label}: {'no data' if value is None else str(value) + unit}"
    source = summary.get("food_source")
    note = {"real": " (real: raw pickups)", "derived": " (DERIVED: eggs / FoodCatchRate, weather inflates it)",
            "mixed": " (mixed: real where logged, derived for older lines)"}.get(source, "")
    return "\n".join([
        render_runs(summary["per_run"]) if summary["per_run"] else "no run_end events",
        "",
        f"runs: {summary['runs']} ({summary['runs_rated']} long enough to rate, {summary['runs_with_real_food']} with real food)",
        f("median_run_s", "median run length", " s"),
        f("food_per_min", "food per minute" + note) + "   (docs/119 estimate: about 120-140)",
        f("food_per_min_derived", "food per minute, derived field (eggs / rate)"),
        f("eggs_per_500_food", "eggs per 500 food") + "   (FoodCatchRate 12/500 = 12 before weather and kills)",
        f("eggs_per_5min", "eggs per 5 minutes (all rated runs)") + "   (owner target: about 15)",
        f("vs_target", "vs target (15 eggs / 5 min), ratio"),
        f("eggs_per_5min_median_run", "eggs per 5 minutes (median run)"),
        f("median_eggs_per_run", "median eggs per run"),
        f("weather_share", "share of run time in weather"),
        f("nests_per_run", "nests per run"),
        f("crystals_per_run", "crystals per run"),
        "end reasons: " + (", ".join(f"{k} {v}" for k, v in sorted(summary["end_reasons"].items())) or "none"),
        f"sessions: {summary['sessions']}",
        f("runs_per_session", "runs per session"),
        f("median_session_s", "median session length", " s"),
        f("hub_share", "share of session time in the hub"),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-seconds", type=int, default=20)
    args = ap.parse_args(argv)
    lines = []
    for path in args.logs:
        lines.extend(Path(path).read_text(encoding="utf-8", errors="replace").splitlines())
    summary = summarize(*parse(lines), min_seconds=args.min_seconds)
    print(json.dumps(summary, indent=2) if args.json else render(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
