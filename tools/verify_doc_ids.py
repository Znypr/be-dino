#!/usr/bin/env python3
"""Fail on NEW duplicate docs/ numeric prefixes or NEW duplicate BD ids in docs/07-kanban.md.
Existing historical duplicates are allow-listed. See AGENTS.md 'Picking numbers'."""
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DOC_PREFIXES = {"13", "39", "43", "85", "86", "93", "111", "112"}
ALLOWED_BD = {"BD-065"}


def main():
    bad = []
    by = defaultdict(list)
    for f in sorted((ROOT / "docs").iterdir()):
        m = re.match(r"(\d+)-", f.name)
        if m and f.is_file():
            by[m.group(1)].append(f.name)
    for k, v in by.items():
        if len(v) > 1 and k not in ALLOWED_DOC_PREFIXES:
            bad.append("docs prefix %s used by: %s" % (k, ", ".join(v)))
    ids = defaultdict(int)
    for line in (ROOT / "docs" / "07-kanban.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(BD-\d+)\s*\|", line)
        if m:
            ids[m.group(1)] += 1
    for k, n in ids.items():
        if n > 1 and k not in ALLOWED_BD:
            bad.append("kanban id %s has %d rows" % (k, n))
    for b in bad:
        print("FAIL:", b)
    if bad:
        print("Pick a free number with `python tools/next_bd_id.py` (BD id) or `python tools/next_bd_id.py --doc` (docs/NN); see AGENTS.md 'Picking numbers'.")
        return 1
    print("doc ids ok: %d prefixes, %d BD ids" % (len(by), len(ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
