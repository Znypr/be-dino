#!/usr/bin/env python3
"""Bring a PR up to date with main in one safe command (BD-646, docs/166).

  python tools/merge_main_into_pr.py 458                  # dry run: do everything locally, print what would be pushed
  python tools/merge_main_into_pr.py bd-637-audio-report  # a branch name works too
  python tools/merge_main_into_pr.py 458 --push           # also `git push origin HEAD:<branch>` (never forced)
  python tools/merge_main_into_pr.py 458 --push --auto-merge   # also `gh pr merge 458 --squash --auto`

What it does, in order (it never rebases, never force-pushes and never touches another worktree):
  1. `git fetch origin main <branch>`; makes a throwaway DETACHED worktree of the PR head in the temp folder.
  2. `git merge origin/main` there (no commit yet).
  3. docs/07-kanban.md conflicts are fixed row by row: a BD row keeps the PR's text ONLY if the PR changed that
     row versus the merge base, otherwise main's text. If BOTH changed it the two edits are MERGED: main's text
     plus the PR's new outcome text (tools/kanban_merge_lib.py; prints a MERGED line, never drops either side).
     Duplicate BD rows are dropped (the PR's edit wins, else
     the longest). Hunks with no BD row take main's side. Then `tools/board_summary.py` prints the counts.
  4. Any OTHER conflicted file: stop and show the hunks, unless the allowlist applies (below). The worktree
     stays so a human can finish: fix, `git add`, `git commit`, run the verifiers, push.
  5. Runs `verify_doc_ids` and `verify_handbook`; commits the merge (message ends with the Co-Authored-By
     line); THEN runs `verify_kanban_merge --base origin/main --head HEAD` (it reads committed state).
  6. Only with --push does it push; only with --push --auto-merge does it ask GitHub for auto-merge.

Allowlist for non-kanban conflicts (the exact rule): a file `docs/<name>.md` whose every conflict hunk is
made only of markdown table rows (lines that start with `|`, no `|---|` separator lines), where each row has a
unique first cell (its key) inside each side of the hunk, and for every key at most ONE side changed the row
versus the merge base (a row added on one side, edited on one side, or removed on one side is fine). A key
that BOTH sides added or both edited differently is not allowed: the whole file then goes to a human.
Result: main's rows in main's order, then the PR's extra rows. Nothing else is ever auto-resolved.

Append-only logs (BD-1060, 2026-10-18): docs/retro/work-log.jsonl is merged as a union of both sides' lines;
docs/168 (generated from it) takes main's copy and is regenerated with `tools/retro_log.py render`; docs/115 and docs/116
conflicts are resolved when BOTH sides only added text at the same place (main's block first, then the PR's).

Exit codes: 0 done, 1 a check failed, 2 usage or git problem, 3 a human must resolve conflicts.
"""
import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import verify_kanban_merge as vkm  # noqa: E402  (row parsing and the post-commit check are shared, not copied)
import kanban_merge_lib as kml  # noqa: E402  (merging two edits of one row, docs/166 section 3)
import verify_no_conflict_markers as vncm  # noqa: E402  (refuse to commit leftover conflict markers)

KANBAN = vkm.KANBAN
REPO_SLUG = "Znypr/be-dino"
TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
CONFLICT = re.compile(
    r"^<<<<<<< [^\n]*\n(.*?)(?:^\|\|\|\|\|\|\| [^\n]*\n(.*?))?^=======\n(.*?)^>>>>>>> [^\n]*(?:\n|\Z)",
    re.S | re.M)
SEPARATOR = re.compile(r"^\|[\s:|-]*\|?\s*$")


class GitError(RuntimeError):
    pass


class NeedsHuman(Exception):
    """A file cannot be resolved by the rules; message says why."""


def git(cwd, *args, check=True):
    p = subprocess.run(["git", "-C", str(cwd), "-c", "core.quotepath=off", "-c", "core.longpaths=true", *args],
                       capture_output=True)
    out, err = p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    if check and p.returncode:
        raise GitError("git %s failed: %s" % (" ".join(args), (err or out).strip()))
    return p.returncode, out, err


# ---------------------------------------------------------------- text helpers (CRLF safe)

def read_text(path):
    """(text with LF only, eol used by the file)."""
    raw = Path(path).read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), eol


def write_text(path, text, eol):
    Path(path).write_bytes(text.replace("\n", eol).encode("utf-8"))


def lines_of(block):
    if not block:
        return []
    return block.split("\n")[:-1] if block.endswith("\n") else block.split("\n")


def row_key(line):
    m = vkm.ROW.match(line)
    return m.group(1) if m else None


def hunks_of(text):
    return list(CONFLICT.finditer(text))


# ---------------------------------------------------------------- kanban: per-row resolution

class KanbanReport:
    def __init__(self):
        self.kept_pr, self.took_main, self.both_changed = [], [], []
        self.pr_only, self.deduped, self.dropped_text = [], [], []
        self.nonrow_hunks = 0
        self.warnings = []
        self.merged = []  # (row id, mode, notes): both sides edited the row and the two edits were MERGED
        self.pr_label = "the PR"


def merge_both(out, k, base, main_line, pr_line, rep):
    """Main AND the PR changed row k: keep main's text and add the PR's new outcome text (tools/kanban_merge_lib.py)."""
    merged, mode, notes = kml.merge_row(base, main_line.rstrip(), pr_line.rstrip(), rep.pr_label)
    out.append(merged)
    rep.both_changed.append(k)
    rep.merged.append((k, mode, notes))


def resolve_kanban_hunk(ours, theirs, base_rows, rep):
    """ours = PR side, theirs = main side (lists of lines). Returns the lines to keep."""
    if not any(row_key(l) for l in ours + theirs):
        rep.nonrow_hunks += 1
        extra = [l for l in ours if l.strip() and l not in theirs]
        if extra:
            rep.dropped_text.append(extra)
        return list(theirs)
    ours_by = {}
    for l in ours:
        k = row_key(l)
        if k and k not in ours_by:
            ours_by[k] = l.rstrip()
    out, seen = [], set()
    for line in theirs:
        k = row_key(line)
        if not k:
            out.append(line)
            continue
        seen.add(k)
        mine = ours_by.get(k)
        if mine is None or mine == line.rstrip():
            out.append(line)
            continue
        base = base_rows.get(k)
        if base is None:
            if vkm.title(mine) != vkm.title(line):
                raise NeedsHuman("%s was added on both sides with different titles: an id collision. Keep main's "
                                 "row and give the PR's row a new number (`python tools/next_bd_id.py`)." % k)
            merge_both(out, k, None, line, mine, rep)  # same task added twice with different tails
        elif mine == base:
            out.append(line)
            rep.took_main.append(k)
        else:
            if line.rstrip() != base:
                merge_both(out, k, base, line, mine, rep)
            else:
                out.append(mine)
                rep.kept_pr.append(k)
    for l in ours:  # rows only on the PR's side of the hunk
        k = row_key(l)
        if not k or k in seen:
            continue
        seen.add(k)
        if k in base_rows and l.rstrip() == base_rows[k]:
            continue  # untouched by the PR; main has it elsewhere (or removed it): main's side
        out.append(l)
        rep.pr_only.append(k)
    return out


def dedupe_rows(text, main_rows_text, base_rows, rep):
    """Drop repeated BD rows that are not repeated on main. The PR's own edit wins, else the longest copy."""
    main_count = {}
    for l in main_rows_text.splitlines():
        k = row_key(l)
        if k:
            main_count[k] = main_count.get(k, 0) + 1
    main_rows = vkm.rows_of(main_rows_text)
    lines = text.split("\n")
    copies = {}
    for i, l in enumerate(lines):
        k = row_key(l)
        if k:
            copies.setdefault(k, []).append(i)
    drop = set()
    for k, idx in copies.items():
        if len(idx) < 2 or main_count.get(k, 0) > 1:
            continue
        edits = [i for i in idx if lines[i].rstrip() not in (main_rows.get(k), base_rows.get(k))]
        pool = edits or idx
        keep = max(pool, key=lambda i: len(lines[i]))
        drop.update(i for i in idx if i != keep)
        rep.deduped.append(k)
    return "\n".join(l for i, l in enumerate(lines) if i not in drop)


def title_warnings(final_text, main_rows, mb_rows):
    out = []
    for rid, row in vkm.rows_of(final_text).items():
        if rid in main_rows and title_differs(row, main_rows[rid]):
            if rid not in mb_rows:
                out.append("%s: main already has this id with a different title, so `verify_kanban_merge` will read "
                           "it as an id collision. Same task? Put main's title text back at the front of the row and "
                           "append your outcome at the END of the row. Different task? Take a new number with "
                           "`python tools/next_bd_id.py`." % rid)
            elif title_differs(row, mb_rows[rid]):
                out.append("%s: the PR changed the title of an existing row (and the check can read it as an id "
                           "collision). Keep the ORIGINAL title and append the outcome at the END of the row." % rid)
    return out


def title_differs(a, b):
    return vkm.title(a) != vkm.title(b)


def resolve_kanban_file(path, base_rows, main_text, swap=False, pr_label="the PR"):
    """Resolve every hunk in `path` (a conflicted docs/07-kanban.md). Returns a KanbanReport.

    Normally HEAD is the PR and the merged-in side is main. `swap=True` is for a merge TRAIN (tools/merge_train.py,
    docs/172): HEAD is the train (main's side of the rule) and the merged-in side is the PR."""
    text, eol = read_text(path)
    rep = KanbanReport()
    rep.pr_label = pr_label

    def repl(m):
        ours, theirs = lines_of(m.group(1)), lines_of(m.group(3))
        if swap:
            ours, theirs = theirs, ours
        res = resolve_kanban_hunk(ours, theirs, base_rows, rep)
        return "".join(l + "\n" for l in res)

    text = CONFLICT.sub(repl, text)
    if vncm.scan_text(text):  # line-start markers only: a row may quote the words in backticks
        raise NeedsHuman("conflict markers are still in the kanban after the rules ran")
    text = dedupe_rows(text, main_text, base_rows, rep)
    write_text(path, text, eol)
    return rep


# ---------------------------------------------------------------- allowlist: markdown table rows, different rows

def table_key(line):
    cells = line.split("|")
    return cells[1].strip() if len(cells) > 2 else ""


def _rows_by_key(lines, what):
    out = {}
    for l in lines:
        if not l.strip():
            continue
        if not l.startswith("|") or SEPARATOR.match(l):
            raise NeedsHuman("a %s line is not a plain table row: %s" % (what, l[:80]))
        k = table_key(l)
        if not k or k in out:
            raise NeedsHuman("a %s table row has an empty or repeated first cell: %s" % (what, l[:80]))
        out[k] = l.rstrip()
    return out


def resolve_table_hunk(ours, base, theirs):
    if base is None:
        raise NeedsHuman("no merge-base text in the hunk")
    o, b, t = (_rows_by_key(ours, "PR"), _rows_by_key(base, "base"), _rows_by_key(theirs, "main"))
    res = {}
    for k in list(t) + [k for k in o if k not in t]:
        ov, bv, tv = o.get(k), b.get(k), t.get(k)
        if ov == tv:
            val = ov
        elif ov == bv:
            val = tv
        elif tv == bv:
            val = ov
        else:
            raise NeedsHuman("both sides changed row '%s' differently" % k)
        if val is not None:
            res[k] = val
    return list(res.values())


def resolve_table_file(path):
    text, eol = read_text(path)
    found = hunks_of(text)
    if not found:
        raise NeedsHuman("no conflict hunks found in the file")

    def repl(m):
        base = lines_of(m.group(2)) if m.group(2) is not None else None
        return "".join(l + "\n" for l in resolve_table_hunk(lines_of(m.group(1)), base, lines_of(m.group(3))))

    new = CONFLICT.sub(repl, text)
    write_text(path, new, eol)
    return len(found)


WORKLOG_JSONL = "docs/retro/work-log.jsonl"
WORKLOG_DOC = "docs/168-work-log-and-retrospectives.md"


def union_lines(main_text, pr_text):
    """Append-only log merge: main's lines in order, then the PR's lines that main does not have. Returns (text, n_from_pr)."""
    main_lines = [l for l in main_text.splitlines() if l.strip()]
    seen = set(main_lines)
    extra = []
    for l in pr_text.splitlines():
        if l.strip() and l not in seen:
            seen.add(l)
            extra.append(l)
    return chr(10).join(main_lines + extra) + chr(10), len(extra)


def resolve_worklog_jsonl(wt, full):
    """Both sides only append entries to docs/retro/work-log.jsonl: keep every line of both (stage 2 = the PR, stage 3 = main)."""
    pr_text = git(wt, "show", ":2:%s" % WORKLOG_JSONL)[1]
    main_text = git(wt, "show", ":3:%s" % WORKLOG_JSONL)[1]
    text, n = union_lines(main_text, pr_text)
    Path(full).write_text(text, encoding="utf-8", newline=chr(10))
    return n


APPEND_ONLY_DOCS = ("docs/115-decisions-log.md", "docs/116-handbook-conflicts.md")
HUNK3 = re.compile(r"^<<<<<<< [^\n]*\n(.*?)^\|\|\|\|\|\|\| [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n", re.S | re.M)


def resolve_append_only_doc(path):
    """docs/115 and docs/116 are logs: when BOTH sides only added text at the same place (the shared base part of the hunk
    is empty), keep both blocks, main's first. Any hunk where the base text was edited or removed needs a human."""
    text, eol = read_text(path)
    count = 0

    def repl(m):
        nonlocal count
        pr_side, base, main_side = m.group(1), m.group(2), m.group(3)
        if base.strip():
            raise NeedsHuman("a hunk edits text that already existed (not append-only)")
        count += 1
        if main_side and not main_side.endswith("\n"):
            main_side += "\n"
        return main_side + pr_side

    new = HUNK3.sub(repl, text)
    if re.search(r"^(<<<<<<<|=======|>>>>>>>)", new, re.M):
        raise NeedsHuman("conflict markers are still there (not diff3 style?)")
    write_text(path, new, eol)
    return count


def show_hunks(path, limit=3, width=150):
    text, _ = read_text(path)
    out = []
    for n, m in enumerate(hunks_of(text)[:limit], 1):
        out.append("  hunk %d" % n)
        for tag, block in (("PR  ", m.group(1)), ("main", m.group(3))):
            ls = lines_of(block)
            for l in ls[:12]:
                out.append("    %s| %s" % (tag, l[:width]))
            if len(ls) > 12:
                out.append("    %s| ... %d more line(s)" % (tag, len(ls) - 12))
    if len(hunks_of(text)) > limit:
        out.append("  ... %d more hunk(s)" % (len(hunks_of(text)) - limit))
    return out


# ---------------------------------------------------------------- orchestration

def say(msg=""):
    print(msg)
    sys.stdout.flush()


def lookup_branch(target, slug):
    """('number or None', branch name)."""
    if not target.isdigit():
        return None, target
    p = subprocess.run(["gh", "pr", "view", target, "--repo", slug, "--json",
                        "headRefName,isCrossRepository,state"], capture_output=True)
    if p.returncode:
        raise GitError("gh pr view %s failed: %s" % (target, p.stderr.decode("utf-8", "replace").strip()))
    import json
    info = json.loads(p.stdout.decode("utf-8"))
    if info.get("isCrossRepository"):
        raise GitError("PR %s comes from a fork; this helper only pushes to branches of %s" % (target, slug))
    if info.get("state") != "OPEN":
        raise GitError("PR %s is %s, not OPEN" % (target, info.get("state")))
    return target, info["headRefName"]


def run_tool(wt, name, *extra):
    script = Path(wt) / "tools" / name
    if not script.exists():
        say("  %s: not in this tree, skipped" % name)
        return 0
    p = subprocess.run([sys.executable, str(script), *extra], cwd=str(wt), capture_output=True)
    out = (p.stdout + p.stderr).decode("utf-8", "replace").strip()
    tail = out.splitlines()[-12:]
    say("  %s: %s" % (name, "ok" if p.returncode == 0 else "FAILED (exit %d)" % p.returncode))
    for l in tail:
        say("      " + l[:200])
    return p.returncode


def kanban_check(wt, remote_main):
    """verify_kanban_merge against committed state: the worktree's own copy when it has one, else ours."""
    script = Path(wt) / "tools" / "verify_kanban_merge.py"
    args = ["--base", remote_main, "--head", "HEAD"]
    if script.exists():
        return run_tool(wt, "verify_kanban_merge.py", *args)
    old_root, old_argv = vkm.ROOT, sys.argv
    vkm.ROOT, sys.argv = Path(wt), ["verify_kanban_merge.py", *args]
    try:
        rc = vkm.main()
    finally:
        vkm.ROOT, sys.argv = old_root, old_argv
    say("  verify_kanban_merge (built-in copy): %s" % ("ok" if rc == 0 else "FAILED (exit %d)" % rc))
    return rc


def merged_line(k, mode, notes):
    what = {"appended": "main's text kept, the PR's new outcome text appended",
            "fallback": "CHECK: main's text kept, the PR's whole text appended as '(from PR, check)'",
            "main": "main's text kept (the PR added nothing new)",
            "pr-only": "the PR's text taken (main left the description alone)",
            "plain": "CHECK: could not split the row, the PR's row was kept; make sure main's edit is not lost"}[mode]
    return "  MERGED %s: main AND the PR both edited this row; %s%s" % (k, what, ("; " + "; ".join(notes)) if notes else "")


def check_markers(wt):
    """Scan the tracked files of the worktree for leftover conflict markers. -> number of hits (printed)."""
    try:
        hits = vncm.scan(wt)
    except RuntimeError as e:
        say("  verify_no_conflict_markers could not run: %s" % e)
        return 1
    for name, number, line, hint in hits[:20]:
        say("  %s:%d: %s   <- %s" % (name, number, line[:60], hint))
    if len(hits) > 20:
        say("  ... %d more" % (len(hits) - 20))
    say("  verify_no_conflict_markers: %s" % ("ok" if not hits else "FAILED (%d marker line(s))" % len(hits)))
    return len(hits)


def commit_message(branch, rep):
    lines = ["Merge origin/main into %s" % branch, ""]
    if rep is not None:
        if rep.kept_pr:
            lines.append("Kanban: kept the PR's copy of %s (the PR changed them)." % ", ".join(sorted(set(rep.kept_pr))))
        if rep.took_main:
            lines.append("Kanban: took main's copy of %s (the PR did not change them)." % ", ".join(sorted(set(rep.took_main))))
        if rep.merged:
            lines.append("Kanban: both sides edited %s; main's text kept and the PR's new text added."
                         % ", ".join(sorted({m[0] for m in rep.merged})))
        if rep.deduped:
            lines.append("Kanban: dropped duplicate rows %s." % ", ".join(sorted(set(rep.deduped))))
        if rep.nonrow_hunks:
            lines.append("Kanban: %d non-row hunk(s) took main's side." % rep.nonrow_hunks)
        if len(lines) > 2:
            lines.append("")
    lines += ["Done with tools/merge_main_into_pr.py (docs/166).", "", TRAILER, ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="PR number or branch name")
    ap.add_argument("--push", action="store_true", help="push the merge commit to the PR branch (never forced)")
    ap.add_argument("--auto-merge", action="store_true", help="after --push: gh pr merge N --squash --auto")
    ap.add_argument("--keep", action="store_true", help="keep the throwaway worktree even after a push")
    ap.add_argument("--repo", default=str(TOOLS.parent), help="the checkout whose .git is used (default: this one)")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--main-branch", default="main")
    ap.add_argument("--slug", default=REPO_SLUG, help="GitHub owner/name for gh (default %s)" % REPO_SLUG)
    a = ap.parse_args(argv)
    if a.auto_merge and not a.push:
        say("--auto-merge needs --push (GitHub can only auto-merge what is pushed).")
        return 2
    repo = Path(a.repo)
    remote_main = "%s/%s" % (a.remote, a.main_branch)
    try:
        number, branch = lookup_branch(a.target, a.slug)
        if a.auto_merge and not number:
            say("--auto-merge needs the PR number, not a branch name.")
            return 2
        say("PR %s: branch %s" % (number or "(by branch)", branch))
        git(repo, "fetch", a.remote,
            "+refs/heads/%s:refs/remotes/%s" % (a.main_branch, remote_main),
            "+refs/heads/%s:refs/remotes/%s/%s" % (branch, a.remote, branch))
        head_ref = "%s/%s" % (a.remote, branch)
        parent = Path(tempfile.mkdtemp(prefix="merge-pr-"))
        wt = parent / "wt"
        git(repo, "worktree", "add", "--detach", str(wt), head_ref)
    except (GitError, OSError) as e:
        say("cannot start: %s" % e)
        return 2
    say("throwaway worktree: %s (detached at %s)" % (wt, head_ref))

    def cleanup():
        git(repo, "worktree", "remove", "--force", str(wt), check=False)
        shutil.rmtree(parent, ignore_errors=True)

    def keep_note():
        say("worktree kept at %s ; remove it later with: git worktree remove --force \"%s\"" % (wt, wt))

    try:
        if git(wt, "merge-base", "--is-ancestor", remote_main, "HEAD", check=False)[0] == 0:
            say("%s already contains %s: nothing to merge." % (branch, remote_main))
            cleanup()
            return 0
        mb = git(wt, "merge-base", remote_main, "HEAD")[1].strip()
        rc, out, err = git(wt, "-c", "merge.conflictstyle=diff3", "merge", "--no-commit", "--no-ff", remote_main,
                           check=False)
        unmerged = [p for p in git(wt, "diff", "--name-only", "--diff-filter=U")[1].splitlines() if p]
        if rc and not unmerged:
            say("git merge failed: %s" % (err or out).strip())
            keep_note()
            return 2
        say("merge of %s: %s" % (remote_main, ("%d conflicted file(s)" % len(unmerged)) if unmerged else "clean"))

        rep, stuck, needs_render = None, [], False
        for path in unmerged:
            stages = {l.split()[2] for l in git(wt, "ls-files", "-u", "--", path)[1].splitlines() if l.strip()}
            full = Path(wt) / path
            try:
                if stages != {"1", "2", "3"}:
                    raise NeedsHuman("added/deleted on one side, not a plain edit conflict")
                if path == KANBAN:
                    base_rows = vkm.rows_of(git(wt, "show", "%s:%s" % (mb, KANBAN))[1])
                    main_text = git(wt, "show", "%s:%s" % (remote_main, KANBAN))[1]
                    rep = resolve_kanban_file(full, base_rows, main_text, pr_label=("PR #%s" % number) if number else "the PR")
                    say("  %s: resolved per row" % path)
                elif path == WORKLOG_JSONL:
                    n = resolve_worklog_jsonl(wt, full)
                    say("  %s: union of both sides (append-only log), %d line(s) taken from the PR" % (path, n))
                    needs_render = True
                elif path in APPEND_ONLY_DOCS:
                    n = resolve_append_only_doc(full)
                    say("  %s: append-only log, both sides added text: %d hunk(s) kept from both sides (main first)" % (path, n))
                elif path.startswith("docs/catalog/"):
                    git(wt, "checkout", "--theirs", "--", path)  # generated team catalogue: main's copy, refreshed by the lead later
                    say("  %s: generated catalogue, took main's copy (BD-1052)" % path)
                elif path == WORKLOG_DOC:
                    git(wt, "checkout", "--theirs", "--", path)  # main's copy; the table is regenerated from the log below
                    say("  %s: took main's copy, the table is regenerated from the log" % path)
                    needs_render = True
                elif fnmatch.fnmatchcase(path, "docs/*.md"):
                    n = resolve_table_file(full)
                    say("  %s: allowlist (table rows, each side changed different rows): %d hunk(s) merged" % (path, n))
                else:
                    raise NeedsHuman("not on the allowlist")
                git(wt, "add", "--", path)
            except NeedsHuman as e:
                stuck.append((path, str(e)))
        if stuck:
            say("")
            say("STOP: a human must resolve %d file(s) (the merge is left half done in the worktree):" % len(stuck))
            for path, why in stuck:
                say("- %s: %s" % (path, why))
                for l in show_hunks(Path(wt) / path):
                    say(l)
            say("")
            say("To finish by hand: cd \"%s\" ; fix the files ; git add <files> ; git commit ; run" % wt)
            say("  python tools/verify_doc_ids.py ; python tools/verify_handbook.py ;")
            say("  python tools/verify_kanban_merge.py --base %s --head HEAD ; git push %s HEAD:%s" % (remote_main, a.remote, branch))
            return 3

        if needs_render or (Path(wt) / WORKLOG_JSONL).exists() and Path(wt, WORKLOG_DOC).exists() and                 run_tool(wt, "retro_log.py", "render", "--check"):
            if run_tool(wt, "retro_log.py", "render"):
                say("STOP: tools/retro_log.py render failed after the work-log merge.")
                keep_note()
                return 1
            git(wt, "add", "--", WORKLOG_DOC)
            say("work log: docs/168 table regenerated from docs/retro/work-log.jsonl")

        # Kanban: dedupe and warn even when git merged it cleanly.
        kb = Path(wt) / KANBAN
        if kb.exists():
            main_text = git(wt, "show", "%s:%s" % (remote_main, KANBAN))[1]
            base_rows = vkm.rows_of(git(wt, "show", "%s:%s" % (mb, KANBAN))[1])
            if rep is None:
                rep = KanbanReport()
                text, eol = read_text(kb)
                new = dedupe_rows(text, main_text, base_rows, rep)
                if new != text:
                    write_text(kb, new, eol)
                    git(wt, "add", "--", KANBAN)
            text, _ = read_text(kb)
            rep.warnings = title_warnings(text, vkm.rows_of(main_text), base_rows)
            say("kanban: kept PR's copy of %d row(s), took main's for %d, dropped %d duplicate(s), %d non-row hunk(s) -> main"
                % (len(set(rep.kept_pr)), len(set(rep.took_main)), len(set(rep.deduped)), rep.nonrow_hunks))
            for k, what in (("kept PR's", rep.kept_pr), ("duplicates dropped", rep.deduped)):
                if what:
                    say("  %s: %s" % (k, ", ".join(sorted(set(what)))))
            for k, mode, notes in rep.merged:
                say(merged_line(k, mode, notes))
            for block in rep.dropped_text:
                say("  NOTE: PR-side non-row text dropped (main's side wins): " + " / ".join(l[:80] for l in block[:3]))
            for w in rep.warnings:
                say("  WARNING " + w)
            if os.path.exists(Path(wt) / "tools" / "board_summary.py"):
                say("board counts after the merge:")
                p = subprocess.run([sys.executable, str(Path(wt) / "tools" / "board_summary.py")], cwd=str(wt),
                                   capture_output=True)
                for l in p.stdout.decode("utf-8", "replace").splitlines():
                    say("  " + l)

        say("checks before the commit:")
        failed = [n for n in ("verify_doc_ids.py", "verify_handbook.py") if run_tool(wt, n)]
        if check_markers(wt):
            failed.append("verify_no_conflict_markers.py")
        if failed:
            say("STOP: %s failed; nothing was committed. Fix in the worktree, then commit and push by hand." % ", ".join(failed))
            keep_note()
            return 1

        msg = parent / "msg.txt"
        msg.write_text(commit_message(branch, rep), encoding="utf-8", newline="\n")
        git(wt, "commit", "-q", "-F", str(msg))
        sha = git(wt, "rev-parse", "--short", "HEAD")[1].strip()
        say("committed merge %s" % sha)
        say("check on committed state:")
        if kanban_check(wt, remote_main):
            say("STOP: the kanban check failed (see above). Not pushing.")
            keep_note()
            return 1

        ahead = git(wt, "rev-list", "--count", "%s..HEAD" % head_ref)[1].strip()
        push_cmd = "git push %s HEAD:%s" % (a.remote, branch)
        if not a.push:
            say("")
            say("DRY RUN: merge %s is committed in the worktree only (%s commit(s) ahead of %s)." % (sha, ahead, head_ref))
            say("Would run: cd \"%s\" && %s" % (wt, push_cmd))
            keep_note()
            return 0
        git(wt, "push", a.remote, "HEAD:%s" % branch)
        say("pushed: %s" % push_cmd)
        if a.auto_merge:
            p = subprocess.run(["gh", "pr", "merge", number, "--repo", a.slug, "--squash", "--auto"], capture_output=True)
            say("auto-merge: %s" % ("on" if p.returncode == 0 else "FAILED: " + p.stderr.decode("utf-8", "replace").strip()))
            if p.returncode:
                keep_note()
                return 1
        if a.keep:
            keep_note()
        else:
            cleanup()
        return 0
    except GitError as e:
        say("git problem: %s" % e)
        keep_note()
        return 2


if __name__ == "__main__":
    sys.exit(main())
