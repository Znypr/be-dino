#!/usr/bin/env python3
"""Merge train: land many open PRs with ONE CI run instead of one PR at a time (BD-993, docs/172).

  python tools/merge_train.py 466 468 470                   # dry run: builds the train in a throwaway worktree
  python tools/merge_train.py --auto-select --hold 474      # every open PR except drafts, --exclude, --hold
  python tools/merge_train.py 466 468 470 --push            # push train/<stamp>, open ONE PR, ask for auto-merge
  python tools/merge_train.py --after 476                   # once the train PR is merged: any original still OPEN?

Why: every squash-merge of one PR makes all other open PRs conflict on docs/07-kanban.md and restarts their ~11
minute CI (N PRs = N CI runs). The train merges them all into one branch and runs CI once.

What it does (it never rebases, never force-pushes and never touches another worktree):
  1. `git fetch origin main` and every PR branch; a DETACHED worktree of origin/main in the temp folder (outside
     the repo checkout).
  2. Per PR, in number order: `git merge --no-ff --no-commit origin/<branch>`. A docs/07-kanban.md conflict is
     fixed with the same per-row rule as tools/merge_main_into_pr.py (docs/166): a BD row takes the PR's text only
     if the PR changed it versus the merge base, else the train's text; if both changed it the edits are merged. ANY other conflicted file: that PR is
     skipped (merge aborted) and listed with the files. Then one merge commit per PR.
  3. verify_doc_ids and verify_handbook; then, on the committed result, verify_kanban_merge --base origin/main.
  4. Dry run (default) stops there and prints what would be pushed. `--push` pushes `train/<stamp>` (never
     forced), opens ONE PR and runs `gh pr merge N --merge --auto`. A MERGE COMMIT is essential: the original PR
     heads become ancestors of main, so GitHub marks them merged by itself. (Squash would leave them open.)

--auto-select takes all open PRs except drafts, forks, earlier train PRs, --exclude N and --hold N (PRs whose
agent is still working). PRs whose base is not main are skipped with a message.

Exit codes: 0 done, 1 a check failed or nothing could be merged, 2 usage or git problem.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import merge_main_into_pr as mm  # noqa: E402  (the kanban resolver is shared, not copied)

vkm = mm.vkm
KANBAN = mm.KANBAN
TRAILER = mm.TRAILER
FOOTER = "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)"
LIST_FIELDS = "number,title,headRefName,baseRefName,isDraft,isCrossRepository,state"
BODY_TAG = "Train-PRs:"


def say(msg=""):
    print(msg)
    sys.stdout.flush()


def real_gh(args):
    """Run `gh <args>`; returns (returncode, stdout, stderr). Tests inject a fake with the same signature."""
    p = subprocess.run(["gh", *args], capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def gh_json(gh, args):
    rc, out, err = gh(args)
    if rc:
        raise mm.GitError("gh %s failed: %s" % (" ".join(args[:3]), (err or out).strip()))
    return json.loads(out)


# ---------------------------------------------------------------- choosing the PRs

def pick_prs(gh, slug, numbers, auto, exclude, hold, main_branch):
    """-> (list of PR info dicts in number order, list of (number, why) skipped before any git work)."""
    infos, skipped = {}, []
    if auto:
        for j in gh_json(gh, ["pr", "list", "--repo", slug, "--state", "open", "--limit", "200", "--json", LIST_FIELDS]):
            if j["isDraft"]:
                skipped.append((j["number"], "draft"))
            elif j["headRefName"].startswith("train/"):
                skipped.append((j["number"], "an earlier merge train PR"))
            else:
                infos[j["number"]] = j
    for n in numbers:
        if n not in infos:
            infos[n] = gh_json(gh, ["pr", "view", str(n), "--repo", slug, "--json", LIST_FIELDS])
            infos[n]["number"] = n
    picked = []
    for n in sorted(infos):
        j = infos[n]
        if n in exclude:
            skipped.append((n, "excluded (--exclude)"))
        elif n in hold:
            skipped.append((n, "held: its agent is still working (--hold)"))
        elif j.get("state", "OPEN") != "OPEN":
            skipped.append((n, "not open (%s)" % j.get("state")))
        elif j.get("baseRefName", main_branch) != main_branch:
            skipped.append((n, "its base is %s, not %s; merge it on its own" % (j["baseRefName"], main_branch)))
        elif j.get("isCrossRepository"):
            skipped.append((n, "comes from a fork"))
        else:
            picked.append(j)
    return picked, sorted(skipped)


# ---------------------------------------------------------------- one PR into the train

def merge_one(wt, remote, info):
    """Merge one PR head into the train worktree. -> (status, detail): status is 'merged', 'contained' or 'skipped'."""
    n, head = info["number"], "%s/%s" % (remote, info["headRefName"])
    if mm.git(wt, "merge-base", "--is-ancestor", head, "HEAD", check=False)[0] == 0:
        return "contained", "its branch is already part of the train / main"
    mb = mm.git(wt, "merge-base", "HEAD", head, check=False)[1].strip()
    rc, out, err = mm.git(wt, "-c", "merge.conflictstyle=diff3", "merge", "--no-ff", "--no-commit", head, check=False)
    unmerged = [p for p in mm.git(wt, "diff", "--name-only", "--diff-filter=U")[1].splitlines() if p]
    if rc and not unmerged:
        mm.git(wt, "merge", "--abort", check=False)
        return "skipped", "git could not merge it: %s" % ((err or out).strip().splitlines() or ["?"])[-1][:160]
    others = [p for p in unmerged if p != KANBAN]
    if others:
        mm.git(wt, "merge", "--abort", check=False)
        return "skipped", "needs a human, conflicting files: " + ", ".join(others)
    kb = Path(wt) / KANBAN
    try:
        if unmerged:
            stages = {l.split()[2] for l in mm.git(wt, "ls-files", "-u", "--", KANBAN)[1].splitlines() if l.strip()}
            if stages != {"1", "2", "3"}:
                raise mm.NeedsHuman("the kanban was added or deleted on one side")
            base_rows = vkm.rows_of(mm.git(wt, "show", "%s:%s" % (mb, KANBAN))[1]) if mb else {}
            main_text = mm.git(wt, "show", "HEAD:%s" % KANBAN)[1]
            rep = mm.resolve_kanban_file(kb, base_rows, main_text, swap=True, pr_label="PR #%d" % n)
            mm.git(wt, "add", "--", KANBAN)
            for k, mode, notes in rep.merged:
                say(mm.merged_line(k, mode, notes))
            return "merged", ("kanban fixed per row (kept the PR's copy of %d row(s), merged both edits of %d)"
                              % (len(set(rep.kept_pr)), len(rep.merged)))
        if kb.exists() and mb:  # a clean git merge can still repeat a BD row
            base_rows = vkm.rows_of(mm.git(wt, "show", "%s:%s" % (mb, KANBAN))[1])
            main_text = mm.git(wt, "show", "HEAD:%s" % KANBAN)[1]
            text, eol = mm.read_text(kb)
            new = mm.dedupe_rows(text, main_text, base_rows, mm.KanbanReport())
            if new != text:
                mm.write_text(kb, new, eol)
                mm.git(wt, "add", "--", KANBAN)
    except mm.NeedsHuman as e:
        mm.git(wt, "merge", "--abort", check=False)
        return "skipped", "kanban needs a human: %s" % e
    return "merged", "clean"


def commit_merge(wt, info):
    msg = "Merge PR #%d into the train (%s)\n\nBranch %s.\n\n%s\n" % (info["number"], info["title"][:80],
                                                                  info["headRefName"], TRAILER)
    mm.git(wt, "commit", "-q", "-m", msg)


# ---------------------------------------------------------------- the original PRs after the train merged

def after_report(gh, slug, train_pr):
    """Print which original PRs GitHub still shows OPEN after the train PR merged. Returns an exit code."""
    j = gh_json(gh, ["pr", "view", str(train_pr), "--repo", slug, "--json", "state,body,number"])
    if j["state"] != "MERGED":
        say("Train PR #%s is %s, not MERGED yet: check again after it merges." % (train_pr, j["state"]))
        return 0
    m = re.search(r"^%s\s*([0-9, ]+)$" % re.escape(BODY_TAG), j.get("body") or "", re.M)
    originals = [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []
    if not originals:
        say("Train PR #%s has no '%s' line in its body, so I do not know the original PRs." % (train_pr, BODY_TAG))
        return 1
    still = []
    for n in originals:
        s = gh_json(gh, ["pr", "view", str(n), "--repo", slug, "--json", "state"])["state"]
        if s == "OPEN":
            still.append(n)
    say("Train PR #%s is merged. Original PRs: %s." % (train_pr, " ".join("#%d" % n for n in originals)))
    if not still:
        say("None of them is still open: GitHub marked them all merged.")
        return 0
    say("Still OPEN on GitHub: %s" % " ".join("#%d" % n for n in still))
    say("Hint: that normally means the PR got new commits after the train was cut (they are NOT in main), or the train")
    say("PR was squashed instead of merged with a merge commit. Run `python tools/merge_main_into_pr.py <N>` to see what")
    say("is left of it; if nothing, close it with a comment that points to the train PR.")
    return 1


# ---------------------------------------------------------------- orchestration

def unique_branch(repo, remote, stamp):
    name, n = "train/%s" % stamp, 1
    taken = mm.git(repo, "ls-remote", "--heads", remote, "refs/heads/train/*", check=False)[1]
    while "refs/heads/%s\n" % name in taken + "\n":
        n += 1
        name = "train/%s-%d" % (stamp, n)
    return name


def summary(merged, skipped, link, dry):
    say("")
    say("SUMMARY")
    say("merged:  %s" % (", ".join("#%d" % i["number"] for i in merged) or "none"))
    if skipped:
        say("skipped:")
        for n, why in skipped:
            say("  #%d: %s" % (n, why))
    else:
        say("skipped: none")
    say(("dry run, nothing was pushed. " if dry else "") + "PR: %s" % link)


def main(argv=None, gh=real_gh):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prs", nargs="*", type=int, help="PR numbers to land together")
    ap.add_argument("--auto-select", action="store_true", help="all open PRs except drafts, --exclude and --hold")
    ap.add_argument("--exclude", nargs="+", type=int, default=[], metavar="N", help="never take these PRs")
    ap.add_argument("--hold", nargs="+", type=int, default=[], metavar="N", help="PRs whose agent is still working")
    ap.add_argument("--push", action="store_true", help="push train/<stamp>, open ONE PR, ask for auto-merge")
    ap.add_argument("--after", type=int, metavar="TRAIN_PR", help="after the train PR merged: list original PRs still OPEN")
    ap.add_argument("--keep", action="store_true", help="keep the throwaway worktree (always kept when something failed)")
    ap.add_argument("--repo", default=str(TOOLS.parent), help="the checkout whose .git is used (default: this one)")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--main-branch", default="main")
    ap.add_argument("--slug", default=mm.REPO_SLUG, help="GitHub owner/name for gh (default %s)" % mm.REPO_SLUG)
    ap.add_argument("--stamp", default=None, help="branch suffix (default: month-day-hour-minute)")
    a = ap.parse_args(argv)
    try:
        if a.after:
            return after_report(gh, a.slug, a.after)
        if not a.prs and not a.auto_select:
            say("Give PR numbers or --auto-select.")
            return 2
        picked, skipped = pick_prs(gh, a.slug, a.prs, a.auto_select, set(a.exclude), set(a.hold), a.main_branch)
    except (mm.GitError, ValueError, KeyError) as e:
        say("cannot ask GitHub: %s" % e)
        return 2
    if not picked:
        summary([], skipped, "none (no PR to merge)", True)
        return 1
    repo = Path(a.repo)
    remote_main = "%s/%s" % (a.remote, a.main_branch)
    stamp = a.stamp or time.strftime("%m%d-%H%M")
    parent = None
    try:
        refspecs = ["+refs/heads/%s:refs/remotes/%s" % (a.main_branch, remote_main)]
        for i in picked:
            refspecs.append("+refs/heads/%s:refs/remotes/%s/%s" % ((i["headRefName"], a.remote, i["headRefName"])))
        mm.git(repo, "fetch", "-q", a.remote, *refspecs)
        branch = unique_branch(repo, a.remote, stamp)
        parent = Path(tempfile.mkdtemp(prefix="merge-train-"))
        wt = parent / "wt"
        mm.git(repo, "worktree", "add", "--detach", str(wt), remote_main)
    except (mm.GitError, OSError) as e:
        say("cannot start: %s" % e)
        if parent:
            shutil.rmtree(parent, ignore_errors=True)
        return 2
    say("train %s: %d PR(s) to try: %s" % (branch, len(picked), " ".join("#%d" % i["number"] for i in picked)))
    say("throwaway worktree: %s (detached at %s)" % (wt, remote_main))

    def cleanup():
        mm.git(repo, "worktree", "remove", "--force", str(wt), check=False)
        shutil.rmtree(parent, ignore_errors=True)

    merged = []
    try:
        for info in picked:
            status, detail = merge_one(wt, a.remote, info)
            if status == "merged" and mm.check_markers(wt):  # never commit leftover conflict markers
                mm.git(wt, "merge", "--abort", check=False)
                status, detail = "skipped", "conflict markers were left in the merge result (see above); fix it with merge_main_into_pr.py"
            if status == "merged":
                commit_merge(wt, info)
                merged.append(info)
                say("  #%d merged (%s)" % (info["number"], detail))
            else:
                skipped.append((info["number"], detail))
                say("  #%d skipped: %s" % (info["number"], detail))
        skipped.sort()
        if not merged:
            summary(merged, skipped, "none (nothing could be merged)", True)
            cleanup()
            return 1
        say("checks on the train:")
        failed = [n for n in ("verify_doc_ids.py", "verify_handbook.py") if mm.run_tool(wt, n)]
        if mm.check_markers(wt):
            failed.append("verify_no_conflict_markers.py")
        if not failed and mm.kanban_check(wt, remote_main):
            failed.append("verify_kanban_merge.py")
        if failed:
            say("STOP: %s failed. Nothing was pushed. The worktree is kept at %s" % (", ".join(failed), wt))
            summary(merged, skipped, "none (checks failed)", True)
            return 1
        log = mm.git(wt, "log", "--oneline", "%s..HEAD" % remote_main)[1].strip().splitlines()
        sha = mm.git(wt, "rev-parse", "--short", "HEAD")[1].strip()
        numbers = " ".join("#%d" % i["number"] for i in merged)
        if not a.push:
            say("")
            say("DRY RUN: the train (%d commit(s), tip %s) exists only in the worktree. Would push:" % (len(log), sha))
            say("  git push %s HEAD:refs/heads/%s" % (a.remote, branch))
            for l in log:
                say("    " + l[:120])
            say("  then: gh pr create --base %s --head %s ; gh pr merge <N> --merge --auto" % (a.main_branch, branch))
            summary(merged, skipped, "none (dry run)", True)
            if a.keep:
                say("worktree kept at %s" % wt)
                return 0
            cleanup()
            return 0
        mm.git(wt, "push", a.remote, "HEAD:refs/heads/%s" % branch)
        say("pushed: git push %s HEAD:refs/heads/%s" % (a.remote, branch))
        body = ["Merge train: lands %s with ONE CI run. Merge-commit merge, so the original PRs become merged." % numbers,
                "", "%s %s" % (BODY_TAG, ", ".join(str(i["number"]) for i in merged)), ""]
        if skipped:
            body += ["Skipped:"] + ["- #%d: %s" % s for s in skipped] + [""]
        body += ["Made with tools/merge_train.py (docs/172).", "", FOOTER]
        rc, out, err = gh(["pr", "create", "--repo", a.slug, "--base", a.main_branch, "--head", branch,
                           "--title", "Merge train %s: %s" % (stamp, numbers), "--body", "\n".join(body)])
        link = out.strip().splitlines()[-1] if out.strip() else ""
        if rc or not link:
            say("The branch is pushed but the PR was not opened: %s" % (err or out).strip())
            summary(merged, skipped, "branch %s pushed, open the PR by hand" % branch, False)
            return 1
        rc, out, err = gh(["pr", "merge", link.rstrip("/").split("/")[-1], "--repo", a.slug, "--merge", "--auto"])
        say("auto-merge (merge commit): %s" % ("on" if rc == 0 else "FAILED: " + (err or out).strip()))
        summary(merged, skipped, link, False)
        say("After it merges: python tools/merge_train.py --after %s" % link.rstrip("/").split("/")[-1])
        if a.keep:
            say("worktree kept at %s" % wt)
        else:
            cleanup()
        return 0 if rc == 0 else 1
    except mm.GitError as e:
        say("git problem: %s (worktree kept at %s)" % (e, wt))
        return 2


if __name__ == "__main__":
    sys.exit(main())
