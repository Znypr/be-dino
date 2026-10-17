# Objectives end-to-end check (BD-078), 2026-10-17: PREP ONLY, NOT RUN

Label: **PREP, no Studio evidence yet.** The owner paused all Studio work before the pass started, so no step below has a result. Nothing here changes game code or any flag (`ObjectivesEnabled` stays `false` in source).

## What is ready
- Local playtest build `C:/Users/znypr/dtmp/objectives-e2e.rbxlx` (outside the repo): `python tools/build.py --profile playtest` from origin/main `2094ffd1`, then `sed` flipped `ObjectivesEnabled = false` to `true` in that output file only (verified 1 true, 0 false).
- [read-gui.client.luau](read-gui.client.luau): a read-only Client probe that prints the panel texts, CLAIM buttons, the goal line and the rects. For NUMBERS-ONLY mode.
- Baseline on origin/main (before any change): `verify_doc_ids`, `verify_objectives`, `verify_objective_hooks`, `verify_objectives_panel`, `verify_kanban_merge`, `verify_sources` all pass.

## Plan (no debug hooks; real events through the remotes and handlers the UI uses)
| # | Step | What to read |
| --- | --- | --- |
| 1 | Fresh profile (a new Play session in the playtest build is memory-only) | `ObjectiveAction {action="view"}`: tutorial row T1 at 0/10 |
| 2 | Real run: walk through the gate, eat food (T1 via the FoodService hook), 30 s or more and at least 1 food, then `RequestEndRun` (HOME) | `view` progress for T1 and T2; OB1 counts the run |
| 3 | Panel shows progress and CLAIM; goal line reads "Done! Claim in Tasks" | `read-gui.client.luau` |
| 4 | `ObjectiveAction {action="claim", id, token}`: wallet (`Crystals`) rises by exactly the reward; same token again = `duplicate`, new token = `already_claimed` | wallet before and after |
| 5 | Open the Fusion menu (click FUSION): T9 completes once via `{action="seen", id="fusion_menu"}` | `view`, second open = no change |
| 6 | Hatch (`ClaimChest`, as `hatchState.next` does): T3 counts it; a head egg with `LastChestFailed=true` counts too (compare the progress delta with the queue shrink) | `ChestQueueJson`, `LastChestFailed` |
| 7 | Instant run (start, then HOME at once) does not count: T2 (or D2 if rolled) unchanged | `view` before and after |
| 8 | 30-minute window text ("New tasks in N min") against `os.time()` | panel header text, `shortResetsIn` |
| 9 | Output has no errors | `get_console_output` |

Not started: no Studio window was opened, no pass/fail exists. Resume when the lead says "Studio free".
