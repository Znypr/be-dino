#!/usr/bin/env python3
"""Static check of the kanban row files in this checkout (BD-1061, docs/191). Runs in CI on every push and PR.

Rules: every file in docs/kanban/rows/ is named BD-NNNN.md (number zero-padded to 4 digits), holds exactly one table-row
line plus one newline (LF), and the row inside has the same number as the file name; no two files share a number; no
folders; and once docs/kanban/CUTOVER exists, docs/07-kanban.md holds no task rows any more.
Before the cutover (no docs/kanban/rows yet) there is nothing to check and it says so.

  python tools/verify_kanban_rows.py
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import kanban_lib as kl  # noqa: E402

ROOT = TOOLS.parent


def main():
    if not kl.has_row_files(ROOT):
        print("kanban rows: no %s yet (the board is still the table in %s); nothing to check" % (kl.ROWS_DIR, kl.LEGACY))
        return 0
    problems = kl.check_rows_dir(ROOT)
    for p in problems:
        print("FAIL:", p)
    if problems:
        print("Fix the row files (one row per file, name = BD-NNNN.md) or run `python tools/kanban.py show BD-n`; see docs/191-kanban-rows.md.")
        return 1
    print("kanban rows ok: %d row files" % len(kl.read_rows(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
