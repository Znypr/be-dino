"""BD-426: summarize exported server logs (lines starting "[BD-TELEMETRY] {json}") into the docs/119 numbers.

    python tools/telemetry_report.py server.log [more.log ...] [--json]

Reads run_end and session_end events only; every other line is ignored. Prints runs, median run length, food per minute,
eggs per 5 minutes (aggregate and median run), end reasons, nests/crystals per run and session shape (runs per session,
hub vs run time). Runs shorter than --min-seconds (default 20) are listed but excluded from per-minute rates because a
run that ended in seconds says nothing about pace. Food is an estimate (eggs / FoodCatchRate) when food_is_estimate is true.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

PREFIX = "[BD-TELEMETRY] "


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


def summarize(runs, sessions, min_seconds=20):
    rated = [r for r in runs if r.get("duration_s", 0) >= min_seconds]
    seconds = sum(r["duration_s"] for r in rated)
    out = {
        "runs": len(runs),
        "runs_rated": len(rated),
        "median_run_s": _median([r["duration_s"] for r in runs]),
        "end_reasons": dict(Counter(r.get("reason", "Other") for r in runs)),
        "food_is_estimate": any(r.get("food_is_estimate") for r in rated),
        "food_per_min": round(sum(r["food"] for r in rated) * 60 / seconds, 1) if seconds else None,
        "eggs_per_5min": round(sum(r["eggs"] for r in rated) * 300 / seconds, 2) if seconds else None,
        "eggs_per_5min_median_run": _median([r["eggs"] * 300 / r["duration_s"] for r in rated]),
        "median_eggs_per_run": _median([r["eggs"] for r in runs]),
        "nests_per_run": round(sum(r["nests"] for r in runs) / len(runs), 2) if runs else None,
        "crystals_per_run": round(sum(r["crystals"] for r in runs) / len(runs), 1) if runs else None,
        "sessions": len(sessions),
        "runs_per_session": round(statistics.mean(s["runs"] for s in sessions), 2) if sessions else None,
        "median_session_s": _median([s["total_s"] for s in sessions]),
        "hub_share": None,
    }
    time_total = sum(s["hub_s"] + s["run_s"] for s in sessions)
    if time_total:
        out["hub_share"] = round(sum(s["hub_s"] for s in sessions) / time_total, 3)
    return out


def render(summary):
    def f(key, label, unit=""):
        value = summary[key]
        return f"{label}: {'no data' if value is None else str(value) + unit}"
    note = " (estimate: eggs / FoodCatchRate)" if summary["food_is_estimate"] else ""
    return "\n".join([
        f"runs: {summary['runs']} ({summary['runs_rated']} long enough to rate)",
        f("median_run_s", "median run length", " s"),
        f("food_per_min", "food per minute" + note) + "   (docs/119 estimate: about 120-140)",
        f("eggs_per_5min", "eggs per 5 minutes (all rated runs)") + "   (owner target: about 15)",
        f("eggs_per_5min_median_run", "eggs per 5 minutes (median run)"),
        f("median_eggs_per_run", "median eggs per run"),
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
