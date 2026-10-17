#!/usr/bin/env python3
"""Print the board counts (task totals by status and priority) from docs/07-kanban.md.

The counts are NOT stored in the kanban any more: a generated table inside a file that every PR edits
conflicted on almost every merge, and the bot that refreshed it could not push to the protected main.
Nothing is written. CI appends this output to each run's job summary; run it by hand to look.

  python tools/board_summary.py                        # markdown table on stdout
  python tools/board_summary.py >> "$GITHUB_STEP_SUMMARY"
"""
import re
import sys
from pathlib import Path

KANBAN = Path(__file__).resolve().parent.parent / "docs" / "07-kanban.md"
CRLF, LF = chr(13) + chr(10), chr(10)
# "Review / test" must be tried before the bare legacy "Review".
STATUSES = ["Backlog", "Ready", "In progress", "In review", "Review / test", "Review", "Blocked", "Done",
            "Superseded", "Parked", "Spike"]
PRIOS = ["P0", "P1", "P2", "P3"]
ROW = re.compile(r"^\| (BD-\d+) \| ([^|]*?) \| (P\d)\b")


def normalise(raw):
    s = raw.strip().lower()
    for name in STATUSES:
        if s.startswith(name.lower()):
            return "Review / test" if name == "Review" else name
    return "Other"


def count(text):
    seen, table = set(), {}
    for line in text.splitlines():
        m = ROW.match(line)
        if not m or m[1] in seen:
            continue
        seen.add(m[1])
        key = (normalise(m[2]), m[3])
        table[key] = table.get(key, 0) + 1
    return len(seen), table


def block(text):
    total, table = count(text)
    order = [s for s in STATUSES if s != "Review"] + ["Other"]
    out = ["**Board summary (docs/07-kanban.md, counts only):** %d tasks." % total, "",
           "| Status | " + " | ".join(PRIOS) + " | Total |", "|---|" + "---:|" * (len(PRIOS) + 1)]
    for st in order:
        cells = [table.get((st, p), 0) for p in PRIOS]
        if sum(cells):
            out.append("| %s | %s | %d |" % (st, " | ".join(map(str, cells)), sum(cells)))
    col = [sum(v for k, v in table.items() if k[1] == p) for p in PRIOS]
    out.append("| **Total** | %s | %d |" % (" | ".join(map(str, col)), total))
    return LF.join(out)


def main():
    text = KANBAN.read_bytes().decode("utf-8").replace(CRLF, LF)
    print(block(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
