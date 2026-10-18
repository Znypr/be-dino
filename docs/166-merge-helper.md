# 166 Merge helper: bring a PR up to date with main in one command (BD-646)

Written 2026-10-18. Label: **CURRENT BUILD** tooling (no game code, no Studio, no `src/` change). Owner request, tool 1 of 8: the lead merged `origin/main` into stale PR branches by hand about ten times, and every time the same fight happened in `docs/07-kanban.md`. `tools/merge_main_into_pr.py` does the same steps, the same way, every time. The rules it follows are the ones in [160](160-agent-brief.md) section 3 ("Conflict rule for docs/07-kanban.md, per row").

## 1. What it does

1. Asks GitHub for the PR's branch (or you give the branch name), then `git fetch origin main <branch>`.
2. Makes a **throwaway worktree** of the PR head in the temp folder (detached, so no branch is moved). No other worktree is touched, yours included.
3. `git merge origin/main` in that worktree. **Never a rebase. Never a force-push.**
4. Fixes `docs/07-kanban.md` conflicts row by row (section 3).
5. Runs `tools/board_summary.py` (it only prints the counts; nothing is stored in the board any more).
6. Runs `verify_doc_ids` and `verify_handbook`. If one fails it stops before the commit.
7. Commits the merge. The message ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
8. **Then** runs `verify_kanban_merge --base origin/main --head HEAD` (that check reads commits, so it has to come after the commit).
9. Pushes only if you said `--push`. Asks for auto-merge only if you said `--push --auto-merge`.

## 2. How to run it

```
python tools/merge_main_into_pr.py 458                       # dry run: all local, prints what it would push
python tools/merge_main_into_pr.py bd-637-audio-report       # a branch name works too
python tools/merge_main_into_pr.py 458 --push                # push the merge commit to the PR branch (not forced)
python tools/merge_main_into_pr.py 458 --push --auto-merge   # and run: gh pr merge 458 --repo Znypr/be-dino --squash --auto
python tools/merge_main_into_pr.py 458 --push --keep         # keep the throwaway worktree after the push
```

- A dry run keeps the worktree and prints it: look at the result there, then either run again with `--push`, or `cd` into it and run the printed `git push origin HEAD:<branch>`. Clean up later with `git worktree remove --force "<path>"`.
- After a successful `--push` the worktree is removed (unless `--keep`).
- `--auto-merge` needs `--push` and a PR **number**. CI must still be green before GitHub merges.
- If the PR already contains `origin/main` it says so and does nothing.
- Exit codes: 0 done, 1 a check failed, 2 usage or git problem, 3 a person must resolve conflicts.

## 3. The kanban rule (per BD row)

A row is one line that starts with `| BD-nnn |`. For each row inside a conflict:

| Situation | Result |
| --- | --- |
| The PR changed the row versus the merge base | The PR's copy stays. |
| The PR did not change the row | Main's copy. |
| Both changed it | The PR's copy stays, and the helper prints `CHECK BD-nnn`: look that main's edit is not lost. |
| A row only the PR has (a new task) | Kept. |
| A row only main has | Kept. |
| The same BD id twice after the merge | One copy stays: the PR's own edit if there is one, else the longest. Listed as "duplicates dropped". |
| A hunk with no BD row (text, headings) | Main's side. Non-empty PR text that is dropped this way is printed as a NOTE. |

It reads the file as bytes and keeps whatever line ending the file had (CRLF or LF), so the merge never leaves a mix.

## 4. When it stops (a person must act)

It stops, leaves the half-done merge in the worktree, prints the hunks (PR side and main side) and the next commands, when:

- **Any other file conflicts** and it is not on the allowlist below. Code, scripts, binary files, a file added or deleted on one side: always a person.
- **The same BD id was added on both sides with different titles.** That is an id collision. Keep main's row and give yours a new number with `python tools/next_bd_id.py`.
- `verify_doc_ids` or `verify_handbook` fails (it does not commit).
- `verify_kanban_merge` fails after the commit (it does not push).

**Allowlist (the exact rule).** A file `docs/<name>.md` is merged by the helper only if every conflict hunk is made only of markdown table rows (lines that start with `|`, no `|---|` separator line inside the hunk), every row has a unique first cell inside each side (that cell is the row's key, like `F3` in [151](151-remote-audit-2026-10-17.md)), and for every key at most one side changed the row versus the merge base. That covers a row added on one side, edited on one side or removed on one side. If both sides edited the same key differently, or both added the same key differently, the whole file goes to a person. The result is main's rows in main's order, then the PR's extra rows. Nothing outside `docs/*.md` is ever merged by the helper, and the kanban uses its own rule (section 3).

## 5. Warnings it prints (they do not stop the run)

- **Title changed on an existing row.** `verify_kanban_merge` compares the start of the task text. If the title changed, the check can read it as "two agents picked the same number". The fix: keep the **original** title and append your outcome at the **end** of the row. The same warning appears when main already has the id with a different title and the PR's row is new: same task, put main's title back; different task, take a new number.
- **CHECK BD-nnn** (both sides edited the row): see section 3.

## 6. What it never does

No rebase, no force-push, no `git stash`, no change in the checkout you run it from, no edit of another worktree, no push unless `--push`, no auto-merge unless `--push --auto-merge`. It does not fix titles for you: it tells you the fix.

## 7. Tests

`python -m unittest tests.test_merge_main_into_pr` builds a bare "origin", a developer clone and a tool clone in a temp folder (with its own git config, so your settings do not matter) and covers: both sides add rows, the PR edits a row main did not, main edits a row the PR did not, duplicate rows, CRLF files, a clean git merge, a title change, an id collision, a file outside the allowlist (stops, shows hunks, commits nothing), table rows on the allowlist, a table row both sides edited (stops), `--push` and the dry run.

**Not verified:** a run with `--auto-merge` against GitHub (the test does not call `gh`); a conflicted real PR with a long kanban conflict (the real-PR dry run in the PR description was a clean merge).
