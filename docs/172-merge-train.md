# 172 Merge train: land many PRs with one CI run (BD-993)

Written 2026-10-18. Label: **CURRENT BUILD** tooling (no game code, no Studio, no `src/` change). The lead did this by hand with a throwaway script and landed PRs #466, #468 and #470 in one combined PR (#476). This page is the permanent, tested version: `tools/merge_train.py`, tests in `tests/test_merge_train.py` (offline: temporary git repos, a local bare `origin`, a fake `gh`).

## 1. Why

Every time one PR is squash-merged, all other open PRs fall behind `main`, most of them conflict in `docs/07-kanban.md`, and their CI (about 11 minutes) starts again. With N waiting PRs that is N CI runs. A **train** puts all of them on one branch and runs CI **once**. Merge helper for a single PR: [166](166-merge-helper.md).

## 2. How to run it

```
python tools/merge_train.py 466 468 470                    # dry run: builds the train in a throwaway worktree, pushes nothing
python tools/merge_train.py --auto-select --hold 474 480   # every open PR except drafts, --exclude, --hold
python tools/merge_train.py 466 468 470 --push             # push train/<stamp>, open ONE PR, gh pr merge N --merge --auto
python tools/merge_train.py --after 476                    # after the train PR merged: which originals are still OPEN?
```

- **Dry run is the default.** The worktree is in the temp folder (never inside the repo checkout) and is removed afterwards; `--keep` leaves it so you can look at the result.
- `--auto-select` takes all open PRs **except**: drafts, forks, earlier `train/*` PRs, `--exclude N ...` (never take these) and `--hold N ...` (the agent is still working on it). PRs whose base is not `main` are skipped with a message, also when named by hand.
- The tool never rebases, never force-pushes (the branch name `train/<stamp>` gets a `-2` if taken), never touches another worktree and never moves a PR branch or `main`.

## 3. What happens

1. `git fetch origin main` and every PR branch; a detached worktree of `origin/main`.
2. PRs in number order: `git merge --no-ff --no-commit origin/<branch>`, one merge commit per PR (trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`).
3. **Kanban conflicts** use the same resolver as the merge helper (`resolve_kanban_file(..., swap=True)` in `tools/merge_main_into_pr.py`, not a copy): a BD row takes the PR's text only if the PR changed it versus the merge base, otherwise the train's text; **if both changed it the two edits are merged** (the train's text plus the PR's new outcome text, `MERGED BD-nnn` line, see [166](166-merge-helper.md) section 3a); rows only on one side are kept; duplicates are dropped. Rule text: [160](160-agent-brief.md) section 3.
4. **Any other conflicted file:** that PR is skipped, its merge is aborted (nothing half-merged stays) and the summary names the files. Fix that PR with `python tools/merge_main_into_pr.py <N> --push` and put it on the next train.
5. After each PR's merge (before its commit) `verify_no_conflict_markers` ([166](166-merge-helper.md) section 8): a PR that leaves markers is skipped and its merge aborted. Then `verify_doc_ids`, `verify_handbook`, the marker check again, then (on the committed result) `verify_kanban_merge --base origin/main --head HEAD`. If one fails nothing is pushed and the worktree is kept.
6. Only with `--push`: `git push origin HEAD:refs/heads/train/<stamp>`, `gh pr create` (body has the line `Train-PRs: 466, 468, 470` and the skipped list), then `gh pr merge N --merge --auto`.

**Why a merge commit and not squash:** the original PR heads become ancestors of `main`, so GitHub marks the original PRs **merged** by itself. A squash merge would leave them open and they would conflict again.

## 4. After the train PR merged

`python tools/merge_train.py --after <train PR>` reads the `Train-PRs:` line, asks GitHub for the state of each original and lists any that are **still OPEN** (there should be none). Usual causes: the PR got new commits after the train was cut (those are not in `main`), or the train PR was squashed. The hint says what to do (`merge_main_into_pr.py` to see what is left, or close it with a comment that points to the train PR).

## 5. Final summary

Always printed at the end, plain text: `merged:`, `skipped:` (one line each with the reason), and `PR:` (the link, or "dry run").

Exit codes: 0 done, 1 a check failed or nothing could be merged, 2 usage or git problem.

## 6. Evidence

16 offline tests in `tests/test_merge_train.py`: two PRs with different kanban rows (no PR touched, PR 11 only, PR 12 only), a non-kanban conflict skipped and named with nothing left behind, push (one PR, `--merge --auto`, originals are ancestors of the train branch, main and PR branches unmoved), dry run pushes nothing and removes its worktree, `--keep`, nothing mergeable, `gh pr create` failing, a taken branch name, an already-merged PR, `--auto-select` filters (draft, excluded, held, train PR, fork, other base), `--after` (all merged, one still open, train not merged). The first real use was the lead's throwaway version on 2026-10-18 (#476).
