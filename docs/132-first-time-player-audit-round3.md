# 132 First-time player audit, round 3 (code-level, playtest profile, 2026-10-16)

Label: **CURRENT BUILD BEHAVIOR**, read from code on main 4615a71 (no Studio run, no phone, no child). Follows [112](112-first-time-player-audit.md) rounds 1 and 2 (P0 fixes: safe first eggs, hint, egg moment, collapsed menu). Rules: [72](72-ui-copy-and-asset-standards.md), [114](114-handbook.md) s1.1, [125](125-friends-playtest-go-no-go.md). Playtest profile: `CaveHub` on, `CombatEnabled` off, `FastTravelPerk` off, low-poly dinos on.

## Count of on-screen controls per step (code reading)
| Step | Visible controls | Notes |
| --- | --- | --- |
| Welcome modal | 1 big button + 3 cards | copy fixed in round 1 |
| Spawn in cave hub (before this PR) | 6 menu buttons, LEAP, weather, EGGS counter, EXPLORE ISLAND / gate, Crystals, **goal line + Goals header** = about 12 | the goal line "Goal Level 1: 0/100 XP" and "Goals (tap)" are new clutter and say nothing to a child with no dinos yet |
| Spawn (after this PR) | same minus goal line and Goals header = about 10 | BD-440 |
| First run, before first egg | POTIONS, SETTINGS, MENU chip, hint chip, LEAP, HOME, size bar, EGGS counter = 8 | good (round 2); goal line was still showing: now hidden |
| After first egg | menu returns after the run; goal line and Goals panel appear | fine, a goal now makes sense |
| First hatch | tap target, "Skip all" | 15 eggs at about 5 s is about 76 s; Skip all exists from egg 1 |
| First shop visit | 5 tabs, prices, 0 crystals until the first run pays | see rows below |

## Fixed in this PR (small, safe)
- BD-440: the NextGoal line and the Goals panel (which follows its Visible) stay hidden until the profile has found its first egg (`FtueRules.showGoals`, `GoalHud`). No economy change, no new Bootstrap local. Test: `tools/verify_ftue_rules.py`.

## Findings left as kanban rows (BD-441 to BD-447)
1. BD-441 (P0 before merge of #261): the playtest feedback button (PR #261, not on main yet) must follow the same rule: hidden until the first run ends, then small and in a corner (a child on minute zero should not meet a feedback form).
2. BD-442 (P1): the cave hub spawn has the new gate walk-up, the old EXPLORE ISLAND button and the 6-button rail together; confirm in Studio that only one "go" affordance is obvious and point at it (round 1 asked for an arrow; still open).
3. BD-443 (P1): class picker line (BD-423) is 22 px under the picker; check the picker text length on a phone and that it fits one line for the longest class text.
4. BD-444 (P1): 15-egg hatch party is about 76 s: add a visible "egg 3 of 15" counter and offer Skip all more prominently after the first 3 eggs (do not remove the reveal; round 1 and owner vision say it is the payoff).
5. BD-445 (P1): the first shop visit still has 0 crystals before the first run settles; show a one-line "Earn crystals on runs" under the tabs while the wallet is under the cheapest price, and hide CONDITIONS until level 3 (BD-372 still open).
6. BD-446 (P2): "Discovery NEW!" ribbon and the kill egg bonus (#267) add text on the hatch and run-complete screens; re-check line count and length of both against docs/72 after they merge.
7. BD-447 (P2): fast-travel perk (`FastTravelPerk`, off) must not show its menu entry in the first 10 minutes when turned on.

## Handbook check
See the PR body.
