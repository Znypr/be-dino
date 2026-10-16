"""Summarise playtest feedback lines ("[BD-FEEDBACK] {json}", docs/128) from exported server logs.

    python tools/feedback_report.py server.log [more.log ...] [--json]

Ratings are 1-3: fun and looks 1 sad / 2 ok / 3 happy; level 1 too easy / 2 just right / 3 too hard. 0 = not answered.
Prints counts, averages (answered only), a split by hub/run and the filtered comments. Lines are already filtered server-side.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PREFIX = "[BD-FEEDBACK] "
KEYS = ("fun", "level", "looks")


def parse(lines):
    out = []
    for line in lines:
        at = line.find(PREFIX)
        if at < 0:
            continue
        try:
            event = json.loads(line[at + len(PREFIX):])
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("event") == "feedback":
            out.append(event)
    return out


def summarize(events):
    out = {"count": len(events)}
    for key in KEYS:
        answered = [e[key] for e in events if e.get(key, 0) in (1, 2, 3)]
        out[key] = {
            "answered": len(answered),
            "average": round(sum(answered) / len(answered), 2) if answered else None,
            "counts": {str(n): answered.count(n) for n in (1, 2, 3)},
        }
    out["by_location"] = dict(Counter(e.get("location", "Hub") for e in events))
    out["comments"] = [
        {"location": e.get("location"), "species": e.get("species"), "runs": e.get("runs"), "text": e["text"]}
        for e in events if e.get("text")
    ]
    return out


def render(summary):
    lines = [f"feedback entries: {summary['count']}"]
    names = {"fun": "fun (1 sad, 3 happy)", "level": "level (1 too easy, 3 too hard)", "looks": "looks (1 sad, 3 happy)"}
    for key in KEYS:
        s = summary[key]
        avg = "no data" if s["average"] is None else s["average"]
        lines.append(f"{names[key]}: average {avg} from {s['answered']} (1: {s['counts']['1']}, 2: {s['counts']['2']}, 3: {s['counts']['3']})")
    lines.append("where: " + (", ".join(f"{k} {v}" for k, v in sorted(summary["by_location"].items())) or "none"))
    lines.append("comments:")
    for c in summary["comments"]:
        lines.append(f"  [{c['location']}, {c['species']}, run {c['runs']}] {c['text']}")
    if not summary["comments"]:
        lines.append("  none")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    lines = []
    for path in args.logs:
        lines.extend(Path(path).read_text(encoding="utf-8", errors="replace").splitlines())
    summary = summarize(parse(lines))
    print(json.dumps(summary, indent=2, ensure_ascii=False) if args.json else render(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
