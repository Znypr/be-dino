#!/usr/bin/env python3
"""Move the task table of docs/07-kanban.md into one file per row (BD-1061, docs/191). Re-runnable, lossless.

  python tools/kanban_migrate.py                    # report only: what would be written (changes nothing)
  python tools/kanban_migrate.py --verify           # prove the round trip: old rows == rows read back from the new files
  python tools/kanban_migrate.py --apply            # do it in this checkout: write docs/kanban/rows/BD-NNNN.md, take the
                                                    # table out of docs/07-kanban.md, write docs/kanban/CUTOVER
  python tools/kanban_migrate.py --apply --from-ref origin/main
                                                    # same, but read the OLD table and prose from a git ref (use this at the
                                                    # cutover: it re-syncs with whatever main has right now)

  python tools/kanban_migrate.py --resync           # in the cutover branch: fetch, merge origin/main, re-read rows from it, commit

Idempotent: a second --apply changes nothing. If docs/07-kanban.md has no rows left it says "nothing to move".
Row files hold the old row line unchanged (plus one newline, LF); nothing is reformatted. The 7 stray ` |` lines inside the
old table (left over from edits) are dropped; they were not rows. Row ORDER is not stored: `python tools/kanban.py render`
sorts by number, and the old file was not in number order (nothing reads the order).
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import kanban_lib as kl  # noqa: E402

ROOT = TOOLS.parent
MARKER_TEXT = """Rows of the kanban board live in docs/kanban/rows/, one file per task (BD-1061, docs/191).
This file's presence is the cutover marker: tools check for it to tell the new layout from the old one
(a table inside docs/07-kanban.md). Do not delete it.
"""

SECTION = """\
- One file per task: `docs/kanban/rows/BD-NNNN.md` (number padded to 4 digits). A file holds exactly one table-row line:
  `| BD-NNN | Status | P1 | Task text | Dependencies |`. Do not put task rows back into this page.
- Read the board with the tool, nothing is committed for it: `python tools/kanban.py list --status "Review / test" --priority P1`,
  `show BD-123`, `board` (counts, same as `tools/board_summary.py`), `render > build/kanban.md` (the old full table, sorted by number).
- Change a row: `python tools/kanban.py set-status BD-123 "Review / test" --note "what was done and what is unverified"`
  (it edits only that row's file and appends the outcome to the END of the task text). Keep titles unchanged.
- New row: `python tools/kanban.py add --priority P1 --status Backlog --title "..." [--deps "BD-1, BD-2"]`; it takes the next free
  number from `tools/next_bd_id.py` and creates the file.
- Because every row is its own file, git merges rows by itself. Two PRs conflict only when they edit the SAME row; then
  `python tools/merge_main_into_pr.py <PR>` merges both edits ([166](166-merge-helper.md)).
- Branch still edits rows in this page (made before the cutover)? `python tools/kanban_migrate_pr.py <PR or branch>`
  merges main in and moves your row changes into row files. Details: [191](191-kanban-rows.md).
"""

PROSE_PATCHES = [
    ("Updated 2026-10-14. This file is the canonical task tracker.",
     "Updated 2026-10-18. This page is the entry to the canonical task tracker. **The task rows are NOT in this page any more: "
     "one file per task in `docs/kanban/rows/` ([191](191-kanban-rows.md)).** Intro, owner decision logs and notes stay here."),
    ("The board below is the only source of truth: each row has its own status and priority.",
     "The board (the row files in `docs/kanban/rows/`) is the only source of truth: each row has its own status and priority."),
]
PICKING_OLD = re.compile(r"Two CI checks guard the file:.*?puts back an older copy of a row.*?take `main`'s version of every row you did not change yourself\.", re.S)
PICKING_NEW = ("CI checks: `tools/verify_doc_ids.py` (no duplicate ids) and `tools/verify_kanban_merge.py` (row ids unique, "
               "one file per id, file name matches the id, no row file removed by accident, an id `main` already gave to a "
               "different task is not reused). Rows are files now, so git merges them by itself; nothing to hand-pick.")


def build_new_text(old_text):
    """-> (new docs/07-kanban.md text, rows). The table goes, the 'how the board works' section takes its place."""
    rows, prose, first = kl.split_legacy(old_text)
    eol = "\r\n" if "\r\n" in old_text else "\n"
    if first is None:
        first = len(prose)
    section = ["", "Rows are files. How the board works:", ""] + SECTION.rstrip("\n").split("\n") + [""]
    section = [l + ("\r" if eol == "\r\n" else "") for l in section]
    new = prose[:first] + section + prose[first:]
    text = "\n".join(new)
    for old, repl in PROSE_PATCHES:
        text = text.replace(old, repl)
    text = PICKING_OLD.sub(lambda m: PICKING_NEW, text)
    return text, rows


def unique_rows(rows):
    """-> (OrderedDict id -> line, list of problems). A repeated id with different text is a problem, an exact repeat is dropped."""
    out, problems = {}, []
    for rid, line in rows:
        if rid in out and out[rid] != line:
            problems.append("%s appears twice with different text; fix the old table first" % rid)
        out.setdefault(rid, line)
    return kl.sort_rows(out), problems


def roundtrip(rows):
    """Write the rows into a temp folder, read them back, compare. -> list of problems (empty = identical)."""
    tmp = Path(tempfile.mkdtemp(prefix="kanban-rt-"))
    try:
        for rid, line in rows.items():
            kl.write_row_file(tmp, rid, line)
        back = kl.read_rows(tmp)
        problems = []
        if list(back) != list(rows):
            problems.append("ids differ: %d written, %d read back" % (len(rows), len(back)))
        for rid, line in rows.items():
            got = back.get(rid)
            if got != line:
                problems.append("%s: text differs after the round trip" % rid)
                continue
            a, b = kl.parse_row(line), kl.parse_row(got)
            if a is None or [a[k] for k in ("id", "status", "priority", "text", "deps")] != \
                    [b[k] for k in ("id", "status", "priority", "text", "deps")]:
                problems.append("%s: columns differ" % rid)
        old_set = {line.rstrip() for line in rows.values()}
        rendered = {l.rstrip() for l in kl.render(back).split("\n")[2:] if l.strip()}
        if rendered != old_set:
            problems.append("render() does not give back the same set of rows")
        return problems
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def read_old(root, ref):
    if ref:
        return kl.git(root, "show", "%s:%s" % (ref, kl.LEGACY), binary=True).decode("utf-8")
    return (Path(root) / kl.LEGACY).read_bytes().decode("utf-8")


def apply(root, ref=None, write=True):
    """-> (message, exit code)."""
    root = Path(root)
    old = read_old(root, ref)
    new_text, row_list = build_new_text(old)
    rows, problems = unique_rows(row_list)
    raw_count = len(re.findall(r"^\| ?BD-\d+ ?\|", old, re.M))  # independent count: a plain grep of the old file
    if raw_count != len(row_list):
        problems.append("the old file has %d `| BD-n |` lines but the parser found %d rows" % (raw_count, len(row_list)))
    if problems:
        return "\n".join("PROBLEM: " + p for p in problems), 1
    rt = roundtrip(rows)
    if rt:
        return "ROUND TRIP FAILED:\n" + "\n".join("  " + p for p in rt[:20]), 1
    if not rows:
        marker_ok = (root / kl.CUTOVER).exists()
        return "nothing to move: %s has no task rows%s." % (kl.LEGACY, "" if marker_ok else " (CUTOVER marker is missing!)"), \
            0 if marker_ok else 1
    same = sum(1 for rid, line in rows.items()
               if (root / kl.row_path(rid)).is_file() and (root / kl.row_path(rid)).read_bytes() == (line + "\n").encode("utf-8"))
    if write:
        for rid, line in rows.items():
            kl.write_row_file(root, rid, line)
        legacy = root / kl.LEGACY
        data = new_text.encode("utf-8")
        if not legacy.exists() or legacy.read_bytes() != data:
            legacy.write_bytes(data)
        marker = root / kl.CUTOVER
        marker.parent.mkdir(parents=True, exist_ok=True)
        if not marker.exists():
            marker.write_bytes(MARKER_TEXT.encode("utf-8"))
    return ("%s: %d task rows -> %d new/changed row file(s) in %s (%d already identical); %s lost its table; round trip ok"
            % ("applied" if write else "dry run (nothing written)", len(rows), len(rows) - same, kl.ROWS_DIR, same, kl.LEGACY)), 0


def resync(root, remote="origin", main_branch="main"):
    """Cutover helper, run inside the branch that carries the cutover: fetch, merge origin/main (only docs/07-kanban.md may
    conflict), re-read the newest rows from main, stage and commit. -> (message, exit code). Needs a clean working tree."""
    root = Path(root)
    ref = "%s/%s" % (remote, main_branch)
    if kl.git(root, "status", "--porcelain", "--untracked-files=no").strip():
        return "the working tree has uncommitted changes: commit or set them aside first", 2
    kl.git(root, "fetch", remote, main_branch)
    contained = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", ref, "HEAD"], capture_output=True).returncode == 0
    if not contained:
        p = subprocess.run(["git", "-C", str(root), "merge", "--no-commit", "--no-ff", ref], capture_output=True)
        unmerged = [l for l in kl.git(root, "diff", "--name-only", "--diff-filter=U").splitlines() if l]
        other = [u for u in unmerged if u != kl.LEGACY]
        if other or (p.returncode and not unmerged):
            subprocess.run(["git", "-C", str(root), "merge", "--abort"], capture_output=True)
            return ("the merge of %s needs a human (%s); nothing changed" % (ref, ", ".join(other) or p.stderr.decode("utf-8", "replace").strip())), 1
    msg, rc = apply(root, ref, write=True)
    if rc:
        return msg, rc
    kl.git(root, "add", "-A", "--", kl.LEGACY, "docs/kanban")
    merging = (root / ".git").exists() and subprocess.run(
        ["git", "-C", str(root), "rev-parse", "-q", "--verify", "MERGE_HEAD"], capture_output=True).returncode == 0
    if merging or kl.git(root, "diff", "--cached", "--name-only").strip():
        kl.git(root, "commit", "-q", "-m",
               "Cutover re-sync: merge %s, rows re-read from main\n\nDone with tools/kanban_migrate.py --resync (docs/191).\n\n"
               "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" % ref)
        msg += "; committed"
    else:
        msg += "; already up to date, nothing to commit"
    return msg, 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the row files, strip the table, write the CUTOVER marker")
    ap.add_argument("--verify", action="store_true", help="only prove the round trip (writes nothing)")
    ap.add_argument("--from-ref", metavar="REF", help="read the old docs/07-kanban.md from this git ref (for example origin/main)")
    ap.add_argument("--resync", action="store_true", help="in the cutover branch: git fetch, merge origin/main, apply from it, commit")
    ap.add_argument("--root", default=str(ROOT), help="the checkout to work in (default: this one)")
    a = ap.parse_args(argv)
    try:
        if a.resync:
            msg, rc = resync(a.root)
        else:
            msg, rc = apply(a.root, a.from_ref, write=a.apply and not a.verify)
    except (RuntimeError, OSError) as e:
        print("kanban_migrate: %s" % e)
        return 2
    print(msg)
    return rc


if __name__ == "__main__":
    sys.exit(main())
