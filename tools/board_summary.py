#!/usr/bin/env python3
"""Print the board counts (task totals by status and priority) from the kanban rows (docs/kanban/rows/, BD-1061; before
the cutover: the table in docs/07-kanban.md).

The counts are NOT stored in the kanban any more: a generated table inside a file that every PR edits
conflicted on almost every merge, and the bot that refreshed it could not push to the protected main.
Nothing is written. CI appends this output to each run's job summary; run it by hand to look.

  python tools/board_summary.py                        # markdown table on stdout
  python tools/board_summary.py >> "$GITHUB_STEP_SUMMARY"
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kanban_lib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LF = chr(10)
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


def count(lines):
    """lines: row lines (a str is split into lines first). -> (number of tasks, {(status, priority): n})."""
    seen, table = set(), {}
    for line in (lines.splitlines() if isinstance(lines, str) else lines):
        m = ROW.match(line)
        if not m or m[1] in seen:
            continue
        seen.add(m[1])
        key = (normalise(m[2]), m[3])
        table[key] = table.get(key, 0) + 1
    return len(seen), table


def block(lines):
    total, table = count(lines)
    order = [s for s in STATUSES if s != "Review"] + ["Other"]
    out = ["**Board summary (kanban rows, counts only):** %d tasks." % total, "",
           "| Status | " + " | ".join(PRIOS) + " | Total |", "|---|" + "---:|" * (len(PRIOS) + 1)]
    for st in order:
        cells = [table.get((st, p), 0) for p in PRIOS]
        if sum(cells):
            out.append("| %s | %s | %d |" % (st, " | ".join(map(str, cells)), sum(cells)))
    col = [sum(v for k, v in table.items() if k[1] == p) for p in PRIOS]
    out.append("| **Total** | %s | %d |" % (" | ".join(map(str, col)), total))
    return LF.join(out)


def main():
    print(block(list(kanban_lib.read_rows(ROOT).values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
