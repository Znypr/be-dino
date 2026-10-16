"""BD-085 / BD-322 phone QA report (docs/127).

Turns the "[BD-QA] {json}" lines that the owner-only QA overlay (src/client/QaOverlay.client.luau, src/server/QaService.luau) prints
into a table against the phone budgets of docs/107 section 1 and the FX ceilings of docs/123 / EffectsLod.

Usage:
  python tools/qa/phone_report.py server.log            # a Roblox Studio / server log, or any text containing [BD-QA] lines
  python tools/qa/phone_report.py server.log --md       # markdown table (paste into docs/127 section 6 or the PR)
  python tools/qa/phone_report.py --selftest            # runs on an embedded sample (CI)
Exit code is 0 unless --strict is given and a mark is OVER budget. A budget miss is a finding, not a build failure.
Every budget is a PROVISIONAL planning number (docs/107 s1: "replace them with what BD-085 measures"), not a Roblox limit.
"""
from pathlib import Path
import argparse
import json
import re
import sys

TAG = "[BD-QA]"
# (field, label, limit, direction, source). direction "max": value must be <= limit; "min": value must be >= limit.
BUDGETS = [
    ("fps", "fps", 30, "min", "docs/107 playable floor (PROVISIONAL, owner: 30 fps on a low-end phone)"),
    ("memMb", "memory MB", 1200, "max", "docs/107 s1 total client memory"),
    ("parts", "parts", 3000, "max", "docs/107 s1 parts attached and in range (whole workspace here, so a strict reading)"),
    ("emitters", "emitters", 40, "max", "PROVISIONAL, about 300 live particles / 8 per emitter (docs/107 s1, docs/123 T1)"),
    ("particleRate", "particles/s", 300, "max", "docs/107 s1 live particles about 300 (lifetimes 0.5-1 s, so rate ~ live)"),
    ("beams", "beams", 24, "max", "docs/123 T3: 3-4 beams per dino, EffectsLod Lite 6 dinos (PROVISIONAL)"),
    ("lights", "lights", 16, "max", "docs/107 s1 dynamic lights, docs/104"),
    ("editableMiB", "EditableImage MiB", 24, "max", "tools/verify_world_budget.py cap (of the 80 MiB engine budget, docs/105)"),
    ("pingMs", "ping ms", 250, "max", "PROVISIONAL assumption, no number in docs/107 (round trip)"),
]


def _load_shared_budgets():
    """Limits in tools/qa/phone_budgets.json (the single phone-budget file) override the local rows above."""
    path = Path(__file__).with_name("phone_budgets.json")
    try:
        shared = json.loads(path.read_text(encoding="utf-8")).get("phone", {})
    except (OSError, ValueError):
        return
    for i, row in enumerate(BUDGETS):
        entry = shared.get(row[0])
        if isinstance(entry, dict) and isinstance(entry.get("value"), (int, float)):
            BUDGETS[i] = (row[0], row[1], entry["value"], row[3], "tools/qa/phone_budgets.json: " + str(entry.get("why", row[4])))


_load_shared_budgets()
# Marks the tour (docs/127 s3) must produce, in order. Missing ones are listed, never failed.
TOUR = ["start_hub", "run_start", "food_field", "egg_reveal_15", "rare_hatch", "goals_panel", "peaceful_button",
        "settings", "sound_lab", "class_picker", "shops", "end"]


def parse(text):
    """Every [BD-QA] json object in the text (Roblox log timestamps before the tag are ignored). Bad json is skipped and counted."""
    marks, bad = [], 0
    for line in text.splitlines():
        i = line.find(TAG)
        if i < 0:
            continue
        try:
            obj = json.loads(line[i + len(TAG):].strip())
        except ValueError:
            bad += 1
            continue
        if isinstance(obj, dict):
            marks.append(obj)
        else:
            bad += 1
    return marks, bad


def verdict(mark):
    """[(label, value or None, limit, ok or None)] per budget; ok None = field missing."""
    rows = []
    for key, label, limit, direction, _src in BUDGETS:
        value = mark.get(key)
        if not isinstance(value, (int, float)):
            rows.append((label, None, limit, None, direction))
            continue
        ok = value <= limit if direction == "max" else value >= limit
        rows.append((label, value, limit, ok, direction))
    return rows


def fmt(v):
    return "?" if v is None else ("%d" % v if float(v).is_integer() else "%.1f" % v)


def table(marks, md):
    head = ["#", "label", "players", "touch"] + [b[1] for b in BUDGETS] + ["status"]
    out, over_total = [], 0
    for index, mark in enumerate(marks, 1):
        rows = verdict(mark)
        over = [r[0] for r in rows if r[3] is False]
        over_total += len(over)
        cells = [str(index), str(mark.get("label", "?")), fmt(mark.get("players")), "y" if mark.get("touch") else "n"]
        for label, value, limit, ok, direction in rows:
            cells.append(fmt(value) + ("" if ok is None else (" ok" if ok else " OVER")))
        cells.append("OVER: " + ", ".join(over) if over else "within budget")
        out.append(cells)
    if md:
        lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
        lines += ["| " + " | ".join(c) + " |" for c in out]
    else:
        widths = [max(len(head[i]), *(len(r[i]) for r in out)) for i in range(len(head))] if out else [len(h) for h in head]
        fmt_row = lambda r: "  ".join(c.ljust(widths[i]) for i, c in enumerate(r))
        lines = [fmt_row(head), fmt_row(["-" * w for w in widths])] + [fmt_row(r) for r in out]
    return lines, over_total


def report(text, md=False):
    marks, bad = parse(text)
    lines, over = table(marks, md)
    seen = [m.get("label") for m in marks]
    missing = [s for s in TOUR if s not in seen]
    lines.append("")
    lines.append("%d marks, %d unreadable lines, %d budget misses." % (len(marks), bad, over))
    if missing:
        lines.append("Tour steps with no mark: " + ", ".join(missing))
    worst = {}
    for mark in marks:
        for label, value, limit, ok, direction in verdict(mark):
            if value is None:
                continue
            best = worst.get(label)
            if best is None or (value > best if direction == "max" else value < best):
                worst[label] = value
    if worst:
        lines.append("Worst over all marks: " + ", ".join("%s %s" % (k, fmt(v)) for k, v in worst.items()))
    lines.append("Budgets: " + "; ".join("%s %s %s" % (b[1], "<=" if b[3] == "max" else ">=", b[2]) for b in BUDGETS) + " (all PROVISIONAL, docs/107 s1, docs/123).")
    return lines, over, len(marks)


SAMPLE = """\
12:00:01.100 [Be Dino] Build ready.
12:00:09.250  [BD-QA] {"label":"start_hub","fps":58.2,"memMb":610,"instances":9120,"parts":2200,"emitters":4,"particleRate":40,"beams":0,"lights":3,"editableMiB":9.6,"editableLive":12,"pingMs":80,"dinos":1,"viewW":844,"viewH":390,"touch":true,"seq":1,"players":1,"serverTime":1}
12:01:15.000  [BD-QA] {"label":"egg_reveal_15","fps":24.4,"memMb":1310,"instances":20100,"parts":7600,"emitters":60,"particleRate":420,"beams":6,"lights":9,"editableMiB":19.2,"editableLive":24,"pingMs":120,"dinos":3,"touch":true,"seq":2,"players":2}
not json [BD-QA] {broken
"""


def selftest():
    marks, bad = parse(SAMPLE)
    assert len(marks) == 2 and bad == 1, (len(marks), bad)
    lines, over, count = report(SAMPLE)
    text = "\n".join(lines)
    assert count == 2 and over == 5, (over, text)
    assert "start_hub" in text and "egg_reveal_15" in text and "Tour steps with no mark" in text and "run_start" in text
    md, _, _ = report(SAMPLE, md=True)
    assert md[0].startswith("| # | label") and md[1].startswith("|---")
    empty, o, c = report("nothing here\n")
    assert c == 0 and o == 0
    print("phone_report selftest passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?")
    ap.add_argument("--md", action="store_true", help="markdown table")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any mark is over budget")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        sys.exit(0)
    if not args.log:
        ap.error("give a log file or --selftest")
    result, over, count = report(Path(args.log).read_text(encoding="utf-8", errors="replace"), args.md)
    print("\n".join(result))
    sys.exit(1 if args.strict and over else 0)
