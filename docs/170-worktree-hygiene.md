# 170 Worktree hygiene: one folder, remove yours, weekly clean

Written 2026-10-18 (BD-660). Status: tool and rule are new (Review / test). Tool: `tools/worktree_hygiene.py`. Tests: `tests/test_worktree_hygiene.py`. Evidence: [audit of this PC](evidence/2026-10-18-worktree-hygiene/audit.md).

## 1. What happened

A git worktree is a second, full copy of the project that shares one history. Helper agents make one for every task. On 2026-10-18 the owner found about **248 GB** of these copies lying around in `C:/Users/znypr/Documents`. Nobody had removed them after their pull requests were merged. The lead checked them one by one and removed the **395 that were clean** (nothing unsaved, everything pushed). That freed **205 GB**.

Why each copy is big (0.5 to 0.8 GB): it is a full copy of the files, not just the changes. In one copy: `docs/` 381 MB (mostly evidence pictures), `build/` 166 MB (the committed `.rbxlx` builds), `resources/` 132 MB (art), the rest 50 MB. There are 3,096 tracked files. So ten copies are about 7 GB.

## 2. The rule

1. **One folder.** Worktrees live in `<repo>/.claude/worktrees` (agents get theirs there automatically), or in the session scratchpad. **Never** make a worktree as a sibling folder in `Documents` (or in `dtmp` or anywhere else). The tool marks everything else `LOOSE`.
2. **A helper removes its own worktree after its pull request is merged.** From any folder:

   ```
   git -C C:/Users/znypr/Documents/be-dino worktree remove <path-of-your-worktree>
   ```

   Do not add `--force`. If git refuses, something is unsaved: save it (commit and push) or tell the lead. If your tools block the command, say "worktree left: <path>" in your report and the lead's weekly clean will take it.
3. **The lead runs the weekly clean:**

   ```
   python tools/worktree_hygiene.py audit               # look first
   python tools/worktree_hygiene.py clean               # dry run: shows what would go
   python tools/worktree_hygiene.py clean --fetch --go  # really removes the safe ones
   ```

4. **Nobody** deletes a worktree folder by hand (that leaves a stale record; `prune-report` shows those) and nobody deletes branches as part of cleaning.

## 3. What the tool does (and never does)

| Command | What it does |
| --- | --- |
| `audit` | Read-only. One line per worktree: size, branch, unsaved files, pushed or not, locked, time since the last activity, allowed folder or `LOOSE`, and whether `clean` could remove it. Totals at the end. Also lists folders that have a `.git` but are not registered worktrees (it never removes those). `--md file` writes the same as markdown. |
| `clean` | **Dry run unless `--go`.** Removes only worktrees that are clean (no modified, staged or untracked files), whose commits all exist on a remote ref, that are not locked, are not the main checkout, and whose last activity is older than `--min-age-hours` (default 6). It checks for unsaved files again right before each removal. It uses plain `git worktree remove <path>`, no `--force`. `--keep text` protects any path containing the text. |
| `prune-report` | Shows what `git worktree prune` would clean up (records of folders that are gone). It never runs the real prune. |

It never touches the main checkout, never deletes a branch, never runs a recursive delete of its own, never changes git config. Files that git ignores (build output) are not "unsaved" for git and are removed along with a clean worktree; `clean` says how many. Remote refs are as of the last fetch; use `--fetch` before a real `--go`.

One thing it cannot know: a pull request that was squash-merged and whose branch was then deleted on GitHub leaves commits that exist on no remote ref. `clean` keeps such a worktree (it shows as `UNPUSHED`). That is the safe side. This is why rule 2 matters: the helper knows its PR merged and removes its own copy.

Agent worktrees made by Claude Code are **locked** by the harness while their session lives (`audit` shows `locked`). `clean` leaves locked ones alone; they go when the session ends or the lead unlocks them.

## 4. The 13 worktrees left because of unsaved files (owner decides)

Snapshot from `audit` on this PC, 2026-10-18. "Unsaved" means git sees changes or new files that are not committed. Nothing was removed or moved by this task. Tell the lead per row: **keep**, **save it** (commit and push, then it can be cleaned), or **throw away**.

| # | Folder | What is unsaved | Last activity |
| ---: | --- | --- | --- |
| 1 | `Documents/bd-batch-upload` (loose) | one new file, `build/uploaded.json` (the list of uploaded assets) | 25 h |
| 2 | `Documents/bd-tier-pbr` (loose, branch `tier-pbr-maps`) | 7 changed files, among them `docs/120-pending-owner-uploads-checklist.md`, `docs/77-asset-registry.md`, `src/shared/LowPolyTier.luau`, `tools/tier_coat.py`; 28 new picture files `resources/effects/tiers/raptor-*-v2-*.png`. 35 lines in all | 25 h |
| 3 | `Documents/bd-vfx-lab` (loose) | one new file, `tools/blender/vfx_lab_fire_v1.blend` (a Blender fire test) | 25 h |
| 4 | `Documents/be-dino-tier` (loose, branch `tier-art`) | new folder `assets/blender/creatures/lowpoly/` (raptor mesh files) | 30 h |
| 5 | `C:/Users/znypr/dtmp/demo-trailer` (loose) | 2 changed files: `src/shared/Config.luau`, `tools/release_profiles.py` | 32 h |
| 6 | `C:/Users/znypr/dtmp/wt-pr346` (loose) | one new file, `build/uploaded.json` | 22 h |
| 7 | `.claude/worktrees/agent-a050c6b0cdd3258ce` (`claude/cave-acceptance`) | new folder `docs/evidence/2026-10-16-cave-acceptance/` (cave test pictures) | 40 h |
| 8 | `.claude/worktrees/agent-a43a3fd1ef8771843` (`claude/phone-budget-offline`) | `docs/07-kanban.md` changed | 43 h |
| 9 | `.claude/worktrees/agent-a7f8f7c069828146e` (`bd352`) | 2 rebuilt files, `build/BeDino-Build020.manifest.json` and `.rbxlx` (made by the build tool, probably safe to throw away) | 34 h |
| 10 | `.claude/worktrees/agent-acdf146ae3027631e` (`bd292-cave-signs`) | the same 2 rebuilt `build/` files | 34 h |
| 11 | `.claude/worktrees/agent-aab71075c6159d9f6` (`claude/sanctuary-polish`) | an unfinished merge: about 710 staged lines and 2 files in conflict (`docs/07-kanban.md`, `src/server/Arena.luau`) | 48 h |
| 12 | scratchpad `wt437` | unfinished merge (61 lines, `docs/07-kanban.md` in conflict); the lead's own session | 3 h |
| 13 | scratchpad `wt439` | unfinished merge (46 lines, `docs/07-kanban.md` in conflict); the lead's own session | 3 h |

Easy wins: rows 1, 6, 9 and 10 only hold rebuilt or upload-list files. Rows 3 and 4 hold files that may exist nowhere else (a Blender file, mesh files): keep them, or copy them somewhere safe first. Rows 2 and 5 are real edits: check them before anything is thrown away.

Also on this PC, not worktrees: `Documents/Codex` (1.9 GB) and `Documents/Znypr-Studio` (2.3 GB) are folders with their own `.git`. They look like other projects. The tool lists them and leaves them alone.

## 5. What is on the disk now

See the [audit](evidence/2026-10-18-worktree-hygiene/audit.md): 66 worktrees, about 43.8 GB, of which 13 are `LOOSE` (8.3 GB). `clean` could remove only 1 of them at that moment (about 0.7 GB), because most of the rest were used within the last 6 hours (many agents were working that day), are locked by a running session, or hold unsaved files (15). The 66 include the agents working right now, including the one that wrote this page. Run `clean` again in a day or two; it will find many more once those PRs are merged and the sessions have ended. The numbers change by the hour, so run `audit` for the live picture.
