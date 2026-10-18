# 191 Kanban rows as files: one file per task (BD-1061)

Written 2026-10-18. Label: **CURRENT BUILD** tooling (no game code, no Studio, no `src/` change). Owner approved the change on 2026-10-18 ("you can do that if it saves a lot of time ... higher quality, less problems"). The task board used to be one big table inside [07-kanban.md](07-kanban.md) that almost every PR edited. The work log ([168](168-work-log-and-retrospectives.md)) showed what that cost: merge conflicts took about 89 minutes of helper time, 13 of 35 helper tasks needed a redo, and every time one PR merged, the other PRs started their 11 minute CI again.

## 1. The new layout

- **Each task is one file:** `docs/kanban/rows/BD-NNNN.md`. The number is padded to 4 digits so the names sort like the numbers (BD-0004.md, BD-1061.md). A bigger number just has more digits.
- **The file holds the old table-row line and one newline**, nothing else, plain LF line endings (`.gitattributes` forces LF):
  `| BD-1061 | Status | P1 | Task text | Dependencies |`
- **[07-kanban.md](07-kanban.md) stays** as the entry page (intro, owner decision logs, notes). It has a short "how the board works" section where the table used to be. **It must hold no task rows.** Many documents link to it, so the file name did not change.
- The marker file `docs/kanban/CUTOVER` says "this checkout uses row files". Tools use it to tell the new layout from the old one (a table inside 07). Do not delete it.
- **The board view is generated, never committed:** `python tools/kanban.py render > build/kanban.md` gives the old full table, sorted by number. The old file was not in number order (79 places where a lower number comes after a higher one); nothing read the order, so no order file is kept.

## 2. Daily use

```
python tools/kanban.py list --status "Review / test" --priority P1 --text fusion
python tools/kanban.py show BD-123
python tools/kanban.py board                      # counts, same numbers as tools/board_summary.py
python tools/kanban.py set-status BD-123 "Review / test" --note "Built; Studio not checked."
python tools/kanban.py add --title "Short title" --priority P1 [--deps "BD-1, BD-2"]
```

- `set-status` edits **only that row's file**: the status changes, the title stays, `--note` is added to the **end of the task text** (before the dependencies column), as the old rule said. "Done" needs a `--note` (evidence).
- `add` takes the next free number from `tools/next_bd_id.py` (or `--id` for one you reserved) and **refuses to overwrite** a file.
- You can still edit a row file by hand. Keep it to one line.

## 3. What git does now

- Two PRs that change **different rows** never conflict. A new row is a new file.
- Two PRs that change the **same row** conflict in that one file. `python tools/merge_main_into_pr.py <PR>` (and the merge train) merge the two edits with the rule of [166](166-merge-helper.md) section 3a: main's text stays, the PR's new outcome text is added. A row deleted on one side and edited on the other, or the same new number used for two different tasks, stops for a human.
- The old accident "an older copy of a row was put back" cannot happen any more, because git merges each row on its own.
- Text-only changes to 07 (the decision logs) behave like docs/115: when both sides only add text at the same place, the helper keeps both.

## 4. Checks (CI)

| Check | What it stops |
| --- | --- |
| `tools/verify_kanban_rows.py` (every push and PR) | A file not named `BD-NNNN.md`, two files for one number, a name that does not match the row inside, more or less than one line, CR characters, a folder, task rows left in 07 |
| `tools/verify_kanban_merge.py` (PRs) | A new number that main already gave to another task; a row removed by accident (rows are never deleted: set Superseded; on purpose: a commit line `Kanban-Remove: BD-n`); a PR that still edits the old table after the cutover |
| `tools/verify_doc_ids.py` | A repeated BD number |

CI time stays flat: these are read-only checks of 600 small files (under a second). The new test file `tests/test_kanban_rows.py` runs about 45 seconds, in the existing "unit tests" step.

## 5. The cutover (for the lead) and old PRs

A PR made **before** the cutover still has its row changes in the old table of 07. After the cutover those PRs would conflict on 07. Two tools take care of that:

- `python tools/kanban_migrate_pr.py <PR number or branch>` merges main into the PR (in a throwaway worktree, like `merge_main_into_pr.py`) and **replays** the PR's row changes: a new row becomes a new file, an edited row becomes the changed file; if main changed the same row, both edits are merged. 07 becomes main's version (a text edit of the PR on that page is merged with a 3-way merge; a clash goes to a human). A row the PR removed from the old table is only reported. Dry run by default, `--push` pushes (never forced).
- `merge_main_into_pr.py` and `merge_train.py` **do this by themselves** when they see the cutover (main has `docs/kanban/CUTOVER`, the PR branch does not). Helpers keep using the same command.

`python tools/kanban_migrate.py` is the one-time converter. `--verify` proves the round trip (every old row equals the row read back from its file, same id, status, priority, text and dependencies, and `render` gives back the same set of rows). `--apply` writes the files and strips the table. It is **idempotent**; with `--from-ref origin/main` it re-reads the newest rows from main. **`--resync`** does the cutover catch-up in one command: in the branch that carries the cutover it fetches, merges `origin/main` (only docs/07-kanban.md may conflict; anything else aborts and changes nothing), re-reads the newest rows and page text from main, and commits.

Cutover steps (lead):
1. Say "no merges to main" (helpers may keep pushing branches; only merging pauses, about 15 minutes: the CI of this PR is about 11 minutes).
2. In the worktree of the cutover branch: `python tools/kanban_migrate.py --resync`, then `python tools/verify_kanban_rows.py` and `python tools/verify_kanban_merge.py --base origin/main --head HEAD`, then `git push`.
3. When CI is green, merge the PR. If main moved in the meantime, run step 2 again (it takes seconds).
4. Tell the helpers: "run `python tools/merge_main_into_pr.py <your PR> --push`; it moves your row changes into row files". Or land the waiting PRs with `python tools/merge_train.py <numbers> --push`.

## 6. What was not verified

- Windows and Linux both ran the tests (Windows here, Linux in CI). A real push of a migrated PR branch was **not** done (dry runs only, as asked).
- The 7 stray ` |` lines inside the old table (left behind by earlier edits, not rows) are dropped by the converter. Nothing else is dropped.
- The old table code paths in the merge tools stay for now so old branches and the old tests keep working. When no PR made before the cutover is open, a clean-up task can remove them.
