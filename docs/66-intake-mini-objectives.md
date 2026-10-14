# 66 - Intake: mini objectives

Template: [64](64-feature-intake-template.md). Status: **Proposal**, nothing built; all numbers PROVISIONAL. Tasks BD-072 to BD-078 (Backlog).

## 1-3. Intention, new vs extension, fit
- **Intention:** teach the loop in the first 15 minutes, then give veterans small reasons to try leap, potions, fusion without a grind wall. Loop moments: run, hatch, shop, collection, fusion.
- **Extension (Seen):** `src/shared/NextGoal.luau` shows one HUD line (best fusion progress, else level XP). Potion shop windows derive from the server clock (`ProgressionConfig.PotionShop`, `floor(unixSeconds/PeriodSeconds)`); `ProfileRepository` has `recentOperations` for idempotency. **New:** `ObjectiveService` + `ObjectiveConfig`.
- **Events needed (all exist server-side):** egg hatched, food eaten, run ended, potion bought, event egg caught, fusion, new species, leap, level up.

## 4. Where on screen (Proposal)
Collapsed pill under the goal line (top-right): trophy icon + "2/3". Tap opens a panel about 300x220 on the right, below crystals, clear of thumbstick and jump zones; max 40% width on phones; auto-collapses 5 s after a run starts. Completion triggers a doc 65 card (key `objective`). Claim is a manual button (min 44 px) for a small reward moment.

## 5. Catalogue (20; rewards in Crystals, PROVISIONAL)
Scale (Seen in `ProgressionConfig`): a 40-egg run gives 30 Crystals, common potions cost 20-25, a random egg 150, first condition upgrade 100.

| # | Group | Objective | Goal | Reward |
|---|---|---|---|---|
| T1 | Tutorial | Eat 10 food | 10 | 10 |
| T2 | Tutorial | Finish your first run (go Home) | 1 | 20 |
| T3 | Tutorial | Hatch 3 eggs | 3 | 15 |
| T4 | Tutorial | Equip a dino in the Index | 1 | 10 |
| T5 | Tutorial | Use leap once | 1 | 10 |
| T6 | Tutorial | Buy a potion | 1 | 25 |
| T7 | Tutorial | Reach level 3 | 1 | 20 |
| T8 | Tutorial | Collect a second species | 1 | 30 |
| T9 | Tutorial | Open the Fusion menu | 1 | 20 |
| S1 | Short | Hatch 10 eggs | 10 | 15 |
| S2 | Short | Eat 40 food | 40 | 10 |
| S3 | Short | Finish a run | 1 | 15 |
| S4 | Short | Use leap 3 times | 3 | 10 |
| S5 | Short | Catch an event egg | 1 | 25 |
| D1 | Daily | Hatch 60 eggs | 60 | 50 |
| D2 | Daily | Finish 3 runs | 3 | 40 |
| D3 | Daily | Buy any potion | 1 | 30 |
| D4 | Daily | Collect a new species | 1 | 60 |
| D5 | Daily | Add a dino toward a fusion step | 1 | 40 |
| D6 | Daily | Hatch a Rare or better | 1 | 50 |

Tutorial total 160 Crystals (about 5 runs, one random egg): a gentle gift.

## 6. Cadence and flow (Proposal)
- Tutorial: 1 shown at a time, ordered, one-time. Short: 3 active, reset every 30 min. Daily: 3 active, reset at UTC midnight. After the tutorial at most 6 rows visible.
- Short goals fit one run (about 5 min); Dailies need about 20-30 min. Expected income at 2 h of play: roughly 150 Daily + 100-200 Short, about one random egg per hour, under the run income so objectives never replace play.
- Pools roll 3 entries per window from the window number (same seed for all servers). Unfinished goals vanish (no backlog guilt); completed-unclaimed can be claimed until one window after reset. One "resets in 12m" line, no timer per row.

## 7. Server authority and persistence (Proposal)
- Progress only from server events; the client sends only `ClaimObjective {id, token}`.
- Additive profile field `objectives`: tutorial claimed bitmask, short/daily window numbers, 6 progress counts, claimed flags. About 120 bytes. Old profiles get defaults.
- Idempotent: progress keyed by event id (`egg:<outcomeId>`, `run:<runId>`); claim uses `recentOperations` token; grant and claimed flag in one profile mutation.
- Reset from the server clock window number like the potion shop; on mismatch regenerate that group and clear progress.
- Anti-abuse: counters per window capped at 2x goal; fixed structure limits claims; small amounts; `MaxCrystals` clamp; no Robux link.

## 8. NextGoal feed
`NextGoal` shows the first unclaimed objective (Tutorial first, else the closest to done): "Goal  Hatch 3 eggs: 1/3". Falls back to current fusion/level logic when none.

## 9. Visuals, icons, animations, audio
- Visuals (reuse): popup-body panel, header-blue, card-common rows, progress-track bars, button-green Claim, button-dark pill, reward-burst on claim. None new.
- Icons: reuse trophy, egg, leap, dinos, fusion, home, lock, `scalable/check`, `scalable/clock`, potion. New (4): chevron toggle, tutorial arrow, crystal and star (crystal and star shared with doc 65).
- Animations: bar fill 0.2 s; row pulse and check pop on complete; claim burst 0.4 s; panel expand 0.15 s. Motion off: instant.
- Audio (existing): shop_buy on claim, pickup_hi on complete, ui_click on toggle. No new sounds.

## 10-13. Performance, metrics, acceptance
At most 7 pooled rows updated on events, never per frame. Metrics: percentage finishing T7, leap and potion use per session, quits before the first run end. Acceptance: offline tests for window rollover, idempotent claim, catalogue schema; Studio server-clock rollover and rejoin; Android: panel never covers thumbstick or jump; motion off works.

## 14. Tasks
| ID | Size | Role | Task | Deps |
|---|---|---|---|---|
| BD-072 | S | design | `ObjectiveConfig` catalogue and rewards + schema tests | none |
| BD-073 | L | server | `ObjectiveService`, profile migration, windows, claim remote | BD-072 |
| BD-074 | M | server | Event hooks (hatch, eat, run, potion, event egg, fusion, species, leap, level) | BD-073 |
| BD-075 | L | UI | Collapsible panel, rows, claim, pill, phone layout | BD-073 |
| BD-076 | S | UI | NextGoal integration | BD-075 |
| BD-077 | M | art | 4 new icons, owner upload and bind | none |
| BD-078 | S | QA | Studio + Android acceptance | all |

## 15. Owner questions
1. Daily reset at UTC midnight instead of local time? Recommended: yes, simplest and cheat-resistant.
2. Tutorial gift of about 160 Crystals acceptable? Recommended: yes.
3. Streak bonus for dailies? Recommended: no for now.
