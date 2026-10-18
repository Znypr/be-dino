#!/usr/bin/env python3
"""PR check for the kanban board: catch the merge accidents that keep happening with parallel agents.

  python tools/verify_kanban_merge.py --base origin/main --head <PR head sha>

Rows are one file each (docs/kanban/rows/BD-NNNN.md, BD-1061, docs/191), so git merges them per file and the old
"an older copy of a row was put back" accident cannot happen any more. What is still checked (BASE = tip of the target
branch, HEAD = the PR head, MB = their merge base):

  (a) FAIL if the PR adds a row whose id is not in MB but IS on BASE with a different title: two agents picked the
      same number. Renumber yours (python tools/next_bd_id.py).
  (c) FAIL if the row files on HEAD break a rule: one file per id, the file name matches the id (BD-0061.md for
      BD-61), exactly one row line + newline, LF endings, no folders, no task rows left in docs/07-kanban.md.
  (d) FAIL if the PR removes a row that MB had, unless one of its commit messages says `Kanban-Remove: BD-nnn`.
      (Rows are never deleted in normal work: set the status to Superseded instead.)
  (e) FAIL if BASE already uses row files but the PR still edits rows in the OLD table of docs/07-kanban.md:
      run `python tools/kanban_migrate_pr.py <PR or branch>` (it merges main in and moves your row changes).

Before the cutover (BASE and HEAD both still use the table in docs/07-kanban.md) the old check (b) also runs:
  (b) FAIL if the PR carries an OLDER version of a row than BASE has (a stale copy put back by a merge). A PR that is
      merely behind is only listed as a note.
`--fix` rewrites such stale rows from BASE in the old table; with row files there is nothing to fix.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import kanban_lib as kl  # noqa: E402

ROOT = TOOLS.parent
KANBAN = kl.LEGACY
ROW = re.compile(r"^\|\s*(BD-\d+)\s*\|")


def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotepath=off", *args], capture_output=True)
    if p.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout.decode("utf-8", "replace")


def rows_of(text):
    """id -> first row line of the OLD table text (CRLF-safe, trailing space trimmed)."""
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = line.rstrip()
    return out


def rows_at(ref):
    """id -> row line at a git ref, whichever layout the ref has (row files or the old table)."""
    return dict(kl.rows_at(ROOT, ref))


def legacy_rows_at(ref):
    """id -> row line in the OLD table at a git ref ({} when the file is missing)."""
    p = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (ref, KANBAN)], capture_output=True)
    return rows_of(p.stdout.decode("utf-8", "replace")) if p.returncode == 0 else {}


def title(row):
    cells = row.split("|")
    desc = cells[4] if len(cells) > 4 else row
    return re.sub(r"\s+", " ", desc).strip().lower()[:70]


def by_number(rows):
    return {kl.number(k): (k, v) for k, v in rows.items()}


def history_versions(base):
    """id -> every text the row has ever had in the OLD table on `base` (from `git log -p`)."""
    log = git("log", "-p", "-U0", "--no-color", "--format=", base, "--", KANBAN)
    seen = {}
    for line in log.splitlines():
        if line[:1] in "+-" and ROW.match(line[1:]):
            row = line[1:].rstrip()
            seen.setdefault(ROW.match(row).group(1), set()).add(row)
    return seen


def check(base_ref, head_ref):
    """The id-collision and stale-copy checks. -> (merge base, dupes, stale, notes)."""
    mb = git("merge-base", base_ref, head_ref).strip()
    base, head, mbase = by_number(rows_at(base_ref)), by_number(rows_at(head_ref)), by_number(rows_at(mb))
    hist = None  # the history of the old table is read only if a row looks changed (it is slow and only matters before the cutover)
    dupes, stale, notes = [], [], []
    for n, (rid, hrow) in head.items():
        if n not in mbase and n in base and title(hrow) != title(base[n][1]):
            dupes.append((rid, hrow, base[n][1]))
        elif n in base and n in mbase and hrow != base[n][1]:
            if hrow != mbase[n][1] and hist is None:
                hist = history_versions(base_ref)
            if hrow != mbase[n][1] and hrow in hist.get(rid, ()):
                stale.append((rid, hrow, base[n][1]))
            elif hrow == mbase[n][1]:
                notes.append(rid)
    return mb, dupes, stale, notes


def check_files(base_ref, head_ref, mb):
    """Row-file rules. -> list of problems (plain words)."""
    problems = []
    head_blobs = kl.ref_row_blobs(ROOT, head_ref)
    head_has_files = bool(head_blobs)
    if head_has_files:
        entries = [(path.rsplit("/", 1)[-1], raw) for path, raw in head_blobs.items()]
        problems += kl.check_row_entries(entries)
        if kl.ref_has_cutover(ROOT, head_ref):
            legacy = legacy_rows_at(head_ref)
            if legacy:
                problems.append(kl.stray_message(list(legacy)))
        mbase = by_number(rows_at(mb))
        head = by_number(rows_at(head_ref))
        gone = sorted(n for n in mbase if n not in head)
        if gone:
            allowed = set()
            for msg in git("log", "--format=%B", "%s..%s" % (mb, head_ref)).splitlines():
                m = re.match(r"\s*Kanban-Remove:\s*(.+)", msg)
                if m:
                    allowed |= {int(x) for x in re.findall(r"BD-(\d+)", m.group(1))}
            lost = [n for n in gone if n not in allowed]
            if lost:
                problems.append("this PR removes row(s) %s. Rows are not deleted: set the status to Superseded instead "
                                "(`python tools/kanban.py set-status BD-n Superseded --note \"why\"`). Removing on purpose? Put "
                                "`Kanban-Remove: BD-n` on its own line in a commit message."
                                % ", ".join(mbase[n][0] for n in lost[:12]))
    elif kl.ref_has_cutover(ROOT, base_ref) or bool(kl.ref_row_blobs(ROOT, base_ref)):
        old = legacy_rows_at(mb)
        changed = sorted(rid for rid, row in legacy_rows_at(head_ref).items() if old.get(rid) != row)
        if changed:
            problems.append("main now keeps one file per row in %s, but this PR still edits rows in the old table of %s "
                            "(%s%s). Run `python tools/kanban_migrate_pr.py <PR number or branch>`: it merges main in and "
                            "moves your row changes into row files." % (kl.ROWS_DIR, KANBAN, ", ".join(changed[:6]),
                                                                         " ..." if len(changed) > 6 else ""))
    return problems


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
    ap.add_argument("--fix", action="store_true", help="rewrite stale rows in the OLD table from --base (row files need no fix)")
    a = ap.parse_args()
    try:
        mb, dupes, stale, notes = check(a.base, a.head)
        file_problems = check_files(a.base, a.head, mb)
    except RuntimeError as e:
        print("verify_kanban_merge: cannot compare (%s).\nThe CI checkout needs full history (fetch-depth: 0)." % e)
        return 2
    if notes:
        print("note: %d row(s) are older than %s but unchanged by this PR; GitHub merges that cleanly: %s" % (
            len(notes), a.base, ", ".join(sorted(notes)[:12]) + (" ..." if len(notes) > 12 else "")))
    if not (dupes or stale or file_problems):
        print("kanban merge check ok (merge base %s)" % mb[:9])
        return 0
    if dupes:
        print("FAIL (a): these BD ids were added by this PR but %s already has them with a different title:" % a.base)
        for rid, hrow, brow in dupes:
            print("  %s  yours: %s" % (rid, short(hrow, brow)))
            print("  %s  main : %s" % (" " * len(rid), short(brow, hrow)))
        print("  -> keep main's row, give YOUR row a new number: run `python tools/next_bd_id.py` and renumber it\n"
              "     (also in other docs, the PR title and branch name that mention it; rename the row file too).")
    if file_problems:
        print("FAIL (c/d/e): the kanban row files are not in order:")
        for p in file_problems:
            print("  - " + p)
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
