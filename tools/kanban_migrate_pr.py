#!/usr/bin/env python3
"""Move a PR that still edits rows in docs/07-kanban.md onto the one-file-per-row board (BD-1061, docs/191).

  python tools/kanban_migrate_pr.py 458                  # dry run: merge main into the PR in a throwaway worktree, replay its rows
  python tools/kanban_migrate_pr.py my-branch --push     # and push the merge commit to the PR branch (never forced)

Use it on a branch made BEFORE the cutover (main has docs/kanban/CUTOVER, the branch does not). It does exactly what
`python tools/merge_main_into_pr.py <PR>` does (merge origin/main, safe resolutions, checks, commit, optional push; see
docs/166) and, because it sees the cutover, also this:

  1. Compares the branch's old table with the table at the merge base: every row the PR ADDED or EDITED is replayed
     into docs/kanban/rows/BD-NNNN.md (a new file for a new row; for an edited row the PR's text, or, if main changed
     that row too, both edits merged with tools/kanban_merge_lib.py: main's text plus the PR's new outcome text).
  2. docs/07-kanban.md becomes main's version (the table is gone there). If the PR also edited the TEXT of that page
     (not the rows), that edit is merged into main's version with a 3-way merge; a clash goes to a human.
  3. A row the PR REMOVED from the old table is only reported (rows are never deleted; set Superseded instead).
  4. Same BD number added by the PR and by main with a different title: stops (an id collision), nothing is guessed.

merge_main_into_pr.py and merge_train.py call `replay()` themselves when they see the cutover, so helpers can simply keep
using them. Exit codes as merge_main_into_pr.py: 0 done, 1 a check failed, 2 usage or git problem, 3 a human is needed.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import kanban_lib as kl  # noqa: E402
import kanban_merge_lib as kml  # noqa: E402


class NeedsHuman(Exception):
    """A step cannot be done by the rules; the message says why."""


class Replay:
    def __init__(self):
        self.added, self.replaced, self.merged, self.same, self.removed = [], [], [], [], []
        self.prose = "main's version"
        self.paths = []


def needs_migration(repo, main_ref, pr_ref):
    """True when main already uses row files and the PR branch has never seen the cutover."""
    return kl.ref_has_cutover(repo, main_ref) and not kl.ref_has_cutover(repo, pr_ref)


def legacy_text(repo, ref):
    """Bytes of the old docs/07-kanban.md at a ref (b'' if there is none)."""
    p = subprocess.run(["git", "-C", str(repo), "show", "%s:%s" % (ref, kl.LEGACY)], capture_output=True)
    return p.stdout if p.returncode == 0 else b""


def _git(wt, *args, check=True):
    p = subprocess.run(["git", "-C", str(wt), "-c", "core.quotepath=off", *args], capture_output=True)
    if check and p.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()))
    return p


def _prose(raw):
    """The page text without any table rows (see kanban_lib.split_legacy), as bytes with the original line endings."""
    _, prose, _ = kl.split_legacy(raw.decode("utf-8"))
    return "\n".join(prose).encode("utf-8")


def merge_page_text(wt, mb, pr_ref, target_ref):
    """3-way merge of the NON-row text of docs/07-kanban.md. -> (bytes for the new page, description)."""
    main_raw = _git(wt, "show", "%s:%s" % (target_ref, kl.LEGACY)).stdout
    base_prose, pr_prose = _prose(legacy_text(wt, mb)), _prose(legacy_text(wt, pr_ref))
    if base_prose == pr_prose:
        return main_raw, "main's version (the PR did not edit the page text)"
    with tempfile.TemporaryDirectory(prefix="kanban-prose-") as d:
        files = []
        for name, data in (("pr", pr_prose), ("base", base_prose), ("main", main_raw)):
            f = Path(d) / name
            f.write_bytes(data)
            files.append(str(f))
        p = subprocess.run(["git", "merge-file", "-p", "-L", "PR", "-L", "base", "-L", "main", *files], capture_output=True)
    if p.returncode != 0:
        raise NeedsHuman("the PR edited the text of %s and the edit clashes with main's version of the page (%s). The rows "
                         "themselves are fine. Merge by hand: take main's page and re-apply your text change."
                         % (kl.LEGACY, "error" if p.returncode < 0 else "%d clash(es)" % p.returncode))
    return p.stdout, "main's version plus the PR's edit of the page text (3-way merge)"


def replay(wt, mb, pr_ref, target_ref, label="the PR"):
    """Move the PR's row changes into row files inside the merge being built in worktree `wt`.

    mb: merge base commit. pr_ref: the PR's own commit (its old table is read from here). target_ref: the commit that
    carries main's current pages (origin/main for a PR catching up, HEAD for a merge train). The merge may be
    in progress (uncommitted). Writes and stages the row files and docs/07-kanban.md. -> Replay. Raises NeedsHuman."""
    rep = Replay()
    if not mb:
        raise NeedsHuman("this branch shares no history with main, so its row changes cannot be compared")
    old_mb = kl.read_legacy_rows(legacy_text(wt, mb).decode("utf-8"))
    old_pr = kl.read_legacy_rows(legacy_text(wt, pr_ref).decode("utf-8"))
    current = {kl.number(k): (k, v) for k, v in kl.read_rows(wt).items()}
    old_by_n = {kl.number(k): v for k, v in old_mb.items()}
    for rid, pr_row in old_pr.items():
        n = kl.number(rid)
        base = old_by_n.get(n)
        if base == pr_row:
            continue  # the PR did not touch this row
        main_id, main_row = current.get(n, (rid, None))
        if main_row is None:
            new, bucket = pr_row, rep.added
        elif main_row == pr_row:
            rep.same.append(rid)
            continue
        elif base is None:
            from verify_kanban_merge import title  # same title rule as the CI check
            if title(pr_row) != title(main_row):
                raise NeedsHuman("%s was added by the PR and by main with different titles: an id collision. Keep main's "
                                 "row and give the PR's row a new number (`python tools/next_bd_id.py`), then run this "
                                 "again." % rid)
            new, mode, notes = kml.merge_row(None, main_row, pr_row, label)
            rep.merged.append((rid, mode, notes))
            bucket = None
        elif base == main_row:
            new, bucket = pr_row, rep.replaced  # main left it alone: the PR's text
        else:
            new, mode, notes = kml.merge_row(base, main_row, pr_row, label)  # both changed it
            rep.merged.append((rid, mode, notes))
            bucket = None
        if bucket is not None:
            bucket.append(rid)
        kl.write_row_file(wt, main_id if main_row is not None else rid, new)
        path = kl.row_path(main_id if main_row is not None else rid)
        _git(wt, "add", "--", path)
        rep.paths.append(path)
    rep.removed = sorted(rid for rid in old_mb if kl.number(rid) not in {kl.number(r) for r in old_pr})
    page, rep.prose = merge_page_text(wt, mb, pr_ref, target_ref)
    (Path(wt) / kl.LEGACY).write_bytes(page)
    _git(wt, "add", "--", kl.LEGACY)
    return rep


def describe(rep):
    """Plain lines for the console."""
    out = ["kanban cutover: moved the PR's row changes into %s" % kl.ROWS_DIR]
    out.append("  new rows: %s" % (", ".join(rep.added) or "none"))
    out.append("  edited rows (PR's text, main had not changed them): %s" % (", ".join(rep.replaced) or "none"))
    if rep.same:
        out.append("  rows main already had in the same form: %s" % ", ".join(rep.same))
    if rep.removed:
        out.append("  NOTE: the PR removed %s from the old table. Nothing was deleted (rows are not deleted: set the status "
                   "to Superseded)." % ", ".join(rep.removed))
    out.append("  %s: %s" % (kl.LEGACY, rep.prose))
    return out


def main(argv=None):
    import argparse
    import merge_main_into_pr as mm
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, add_help=True)
    ap.add_argument("target", help="PR number or branch name")
    ap.add_argument("--push", action="store_true", help="push the merge commit to the PR branch (never forced)")
    ap.add_argument("--keep", action="store_true", help="keep the throwaway worktree even after a push")
    ap.add_argument("--repo", default=str(TOOLS.parent))
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--main-branch", default="main")
    ap.add_argument("--slug", default=mm.REPO_SLUG)
    a = ap.parse_args(argv)
    repo = Path(a.repo)
    try:
        number, branch = mm.lookup_branch(a.target, a.slug)
        mm.git(repo, "fetch", a.remote, "+refs/heads/%s:refs/remotes/%s/%s" % (a.main_branch, a.remote, a.main_branch),
               "+refs/heads/%s:refs/remotes/%s/%s" % (branch, a.remote, branch))
    except (mm.GitError, OSError) as e:
        print("cannot start: %s" % e)
        return 2
    main_ref, pr_ref = "%s/%s" % (a.remote, a.main_branch), "%s/%s" % (a.remote, branch)
    if not kl.ref_has_cutover(repo, main_ref):
        print("%s has no %s yet: the board is still the table in %s, nothing to migrate." % (main_ref, kl.CUTOVER, kl.LEGACY))
        return 0
    if kl.ref_has_cutover(repo, pr_ref):
        print("%s already contains the cutover (it has the row files); running the normal merge helper." % branch)
    else:
        print("%s was made before the cutover: its row changes will be moved into row files." % branch)
    args = [a.target]
    if a.push:
        args.append("--push")
    if a.keep:
        args.append("--keep")
    args += ["--repo", a.repo, "--remote", a.remote, "--main-branch", a.main_branch, "--slug", a.slug]
    return mm.main(args)


if __name__ == "__main__":
    sys.exit(main())
