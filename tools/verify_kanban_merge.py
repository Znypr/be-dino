#!/usr/bin/env python3
"""PR check for docs/07-kanban.md: catch the two merge accidents that keep happening with parallel agents.

  python tools/verify_kanban_merge.py --base origin/main --head <PR head sha>

Compares three versions of the board: BASE (tip of the target branch, normally origin/main), HEAD (the PR
head) and MB (their merge base), row by row (a row is a line starting `| BD-nnn |`).

  (a) FAIL if the PR adds a row whose id is not in MB but IS on BASE with a different title:
      two agents picked the same number. Renumber yours (python tools/next_bd_id.py).
  (b) FAIL if the PR carries an OLDER version of a row than BASE has: HEAD's row differs from BASE's and
      equals some earlier version of that row in BASE's history (and is not the merge-base text either).
      That is a stale copy put back by a merge resolution or rebase. The PR's own legitimate edits are
      NEW text that never existed on BASE, so they never trip this.
      A PR that is merely behind (HEAD row == MB row, BASE newer, row untouched) merges cleanly on
      GitHub, so that is only listed as a note, not a failure.

  python tools/verify_kanban_merge.py --base origin/main --head HEAD --fix
      rewrites the offending rows in your working copy of docs/07-kanban.md with BASE's version.

If an old value is restored on purpose, change the row text (for example add a short "Board audit" note)
so it is no longer identical to an old version.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KANBAN = "docs/07-kanban.md"
ROW = re.compile(r"^\|\s*(BD-\d+)\s*\|")


def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotepath=off", *args], capture_output=True)
    if p.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout.decode("utf-8", "replace")


def rows_of(text):
    """id -> first row line (CRLF-safe, trailing space trimmed)."""
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = line.rstrip()
    return out


def rows_at(ref):
    return rows_of(git("show", "%s:%s" % (ref, KANBAN)))


def title(row):
    cells = row.split("|")
    desc = cells[4] if len(cells) > 4 else row
    return re.sub(r"\s+", " ", desc).strip().lower()[:70]


def history_versions(base):
    """id -> every text the row has ever had on `base` (from `git log -p`)."""
    log = git("log", "-p", "-U0", "--no-color", "--format=", base, "--", KANBAN)
    seen = {}
    for line in log.splitlines():
        if line[:1] in "+-" and ROW.match(line[1:]):
            row = line[1:].rstrip()
            seen.setdefault(ROW.match(row).group(1), set()).add(row)
    return seen


def check(base_ref, head_ref):
    mb = git("merge-base", base_ref, head_ref).strip()
    base, head, mbase = rows_at(base_ref), rows_at(head_ref), rows_at(mb)
    hist = history_versions(base_ref)
    dupes, stale, notes = [], [], []
    for rid, hrow in head.items():
        if rid not in mbase and rid in base and title(hrow) != title(base[rid]):
            dupes.append((rid, hrow, base[rid]))
        elif rid in base and rid in mbase and hrow != base[rid]:
            if hrow in hist.get(rid, ()) and hrow != mbase[rid]:
                stale.append((rid, hrow, base[rid]))
            elif hrow == mbase[rid]:
                notes.append(rid)
    return mb, dupes, stale, notes


def short(row, other=None, n=110):
    """Row text, cut to n chars; with `other`, cut around the first place the two rows differ."""
    start = 0
    if other is not None:
        while start < min(len(row), len(other)) and row[start] == other[start]:
            start += 1
        start = max(0, start - 30)
    cut = row[start:start + n]
    return ("..." if start else "") + cut + ("..." if start + n < len(row) else "")


def apply_fix(base_ref, stale):
    path = ROOT / KANBAN
    raw = path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")
    fixed = {rid: base for rid, _, base in stale}
    done = set()
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if m and m.group(1) in fixed and m.group(1) not in done:
            lines[i] = fixed[m.group(1)]
            done.add(m.group(1))
    path.write_bytes(eol.join(lines).encode("utf-8"))
    return sorted(done)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/main", help="target branch ref (default origin/main)")
    ap.add_argument("--head", default="HEAD", help="PR head ref or sha (default HEAD)")
    ap.add_argument("--fix", action="store_true", help="rewrite stale rows in the working copy from --base")
    a = ap.parse_args()
    try:
        mb, dupes, stale, notes = check(a.base, a.head)
    except RuntimeError as e:
        print("verify_kanban_merge: cannot compare (%s).\nThe CI checkout needs full history (fetch-depth: 0)." % e)
        return 2
    if notes:
        print("note: %d row(s) are older than %s but unchanged by this PR; GitHub merges that cleanly: %s" % (
            len(notes), a.base, ", ".join(sorted(notes)[:12]) + (" ..." if len(notes) > 12 else "")))
    if not (dupes or stale):
        print("kanban merge check ok (merge base %s)" % mb[:9])
        return 0
    if dupes:
        print("FAIL (a): these BD ids were added by this PR but %s already has them with a different title:" % a.base)
        for rid, hrow, brow in dupes:
            print("  %s  yours: %s" % (rid, short(hrow, brow)))
            print("  %s  main : %s" % (" " * len(rid), short(brow, hrow)))
        print("  -> keep main's row, give YOUR row a new number: run `python tools/next_bd_id.py` and renumber it\n"
              "     (also in other docs, the PR title and branch name that mention it).")
    if stale:
        print("FAIL (b): these rows were NOT changed by this PR but carry an OLDER version than %s (a stale copy"
              " put back by a merge or rebase):" % a.base)
        for rid, hrow, brow in stale:
            print("  %s  yours: %s" % (rid, short(hrow, brow)))
            print("  %s  main : %s" % (" " * len(rid), short(brow, hrow)))
        print("  -> take these rows from main: %s" % ", ".join(r for r, _, _ in stale))
        print("     Fix: `git fetch origin && python tools/verify_kanban_merge.py --base %s --fix`, then commit."
              % a.base)
        print("     (Restoring an old value on purpose? Edit the row text so it is not identical to the old one.)")
    if a.fix and stale:
        print("fixed in working copy: " + ", ".join(apply_fix(a.base, stale)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
