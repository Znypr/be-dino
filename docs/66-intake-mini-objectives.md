# 66 - Intake: mini objectives

Template: [64](64-feature-intake-template.md). Status: **BD-072/BD-073 built behind `ObjectivesEnabled=false` (2026-10-17, offline-tested only, Studio pending, see section 17); BD-075 panel built behind the same flag (offline-tested, Studio pictures pending, see section 18)**; BD-074 and BD-076 to BD-078 are Backlog (no gameplay hooks). All numbers PROVISIONAL.

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
`NextGoal` shows the first unclaimed objective (Tutorial first, else the closest to done): "Goal  Hatch 3 eggs: 1/3". Falls back to current fusion/level logic when none. **Built as BD-076, with the priority table of section 19 (the fusion goal beats an unfinished task).**

## 9. Visuals, icons, animations, audio
- Visuals (reuse): popup-body panel, header-blue, card-common rows, progress-track bars, button-green Claim, button-dark pill, reward-burst on claim. None new.
- Icons: reuse trophy, egg, leap, dinos, fusion, home, lock, `scalable/check`, `scalable/clock`, potion. New (4): chevron toggle, tutorial arrow, crystal and star (crystal and star shared with doc 65). **Art brief (BD-077, 2026-10-17): [109](109-owner-art-prompt-pack.md) section 9 gives purpose, place, size, palette, ChatGPT prompt and Blender note for each of the four; the panel reads the ids through new empty-id slots (BD-561), so an empty id keeps today's trophy-only panel.**
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

## 16. Step 0 overlap check with the existing Goals (2026-10-17)
Question: do the docs/66 mini objectives duplicate the Goals panel / goal line, so that building them would be a second goals system?

| Existing piece | What it is | Overlap with docs/66 |
| --- | --- | --- |
| `NextGoal` (HUD line, BD-076 will feed it) | Pure client text: best fusion progress, else level XP. Derived from data the client already has; no storage. | None of the 20 objectives. Only a *display slot*: docs/66 section 8 already says objectives feed this line. |
| `GoalsRules` + `GoalsPanel` (BD-427) | Three permanent long-term lines (collect, perfect a favourite, play new dinos), derived from the Index/fusion list. Promises no reward. | Loose thematic overlap with T8/D4 (new species) and D5 (toward a fusion step). Those objectives still need counters and rewards that the derived lines cannot give. |
| Any stored goal state | None. Nothing in the profile, no counters, windows, claims or Crystal rewards. | docs/66 is almost all of it: event counters, server-clock windows, claim-once, rewards, anti-abuse caps. |

**Verdict: the existing goals cover about 3 of 20 objectives in spirit and none of the mechanics. BUILD SEPARATELY** (`ObjectiveConfig`, `ObjectiveRules`, `ObjectiveService`) and merge only at the display layer later: BD-076 shows the top objective on the existing goal line, and BD-075's panel sits beside the Goals panel (the Goals panel stays the long-term compass; objectives are the small near-term steps). Merging objectives *into* the derived Goals lines was rejected: it would put persistent, server-owned, rewarded state behind a client-derived pure module. Overlap to watch in BD-075/076: do not show T8 "second species" and the long-term PLAY line as two competing species nudges at once.

## 17. Implementation status BD-072/BD-073 (2026-10-17, offline only)
**All of this is OFF.** `Config.ObjectivesEnabled = false`, pinned by `tools/release_profiles.py` (`COMMON_RULES`, so both the default and the playtest profile require false; `verify_release` enforces it on source and built places). The owner flips it only after Studio evidence.

| Piece | File | Notes |
| --- | --- | --- |
| Catalogue (BD-072) | `src/shared/ObjectiveConfig.luau` | The 20 rows of section 5, Crystals/XP only, never Robux, never random items, eggs, nests or species. **PROVISIONAL:** every reward, `MaxClaimCrystals` 100, `MaxClaimXP` 50, `WindowCrystalCapPerDay` 600 (Short + Daily crystals per UTC day; a claim past it is clamped to what is left, not refused), counter cap 2 x goal. Not owner-approved balance (docs/09). |
| Rules | `src/shared/ObjectiveRules.luau` | Pure: window rollover, picks, counters, replay protection, claim, migration/sanitising, read-only view. No Instances, services or clock reads (`now` is passed in). |
| Server | `src/server/ObjectiveService.luau`, `ProfileRepository.objectiveRecord / objectiveView / objectiveFlush / objectiveClaim` | `ObjectiveAction` RemoteFunction exists only while the flag is on. Requests: `{action="view"}` and `{action="claim", id, token}`, strict shapes, 10 requests per 10 s per player (PROVISIONAL), then `rate_limited`. The client never sends progress or amounts. |
| Hook API for BD-074 | `ObjectiveService.record(player, kind, amount?, eventId?, value?)` | A no-op returning false while the flag is off. Kinds: `food_eaten, run_end, egg_hatched, dino_equipped, leap_used, potion_bought, level_reached (value = level), species_new, fusion_menu_opened, event_egg_caught, fusion_step_added, rare_hatched`. Use ids like `egg:<outcomeId>` / `run:<runId>` for replay safety. |

**Profile field (additive, lazy).** `profile.objectives = {v=1, tutorial={progress,claimed}, short/daily={window, ids, progress, claimed, carry?}, earned={day,crystals}, seen={event ids, 48 max}, flush=<last batch id>}`. About 0.5 KB. Never created by `load`, never created or read while the flag is off, created by the first mutation while on. A corrupt value reads as empty and is replaced by the first real write (a bad value in this one field must not lock a player out, docs/111). A value with `v` newer than this build is never read, written or reordered (`newer_version`, rollback safe; Build 020 keeps unknown fields byte for byte). `schemaVersion` is unchanged.

**Windows (server clock, `os.time()` UTC).** Short = `floor(t/1800)`, Daily = `floor(t/86400)` (resets at UTC midnight, owner question 1, still unanswered). Each window rolls 3 distinct entries from its pool with the window number as seed, the same on every server, so a rejoin never rerolls. A finished-but-unclaimed row carries into exactly the next window and can be claimed there; older ones vanish. A stored window ahead of the clock (clock moved back) is left alone. The tutorial is ordered, one-time, and counts progress for every unclaimed entry (the UI will show the first unclaimed).

**Claim exactly once.** The claim transaction (one `UpdateAsync`) checks the lease, finds the token in `recentOperations` (`objective:<token>`; the same token and id again answers `duplicate` with nothing granted, the same token for another id is `token_conflict`), applies queued progress, flips the claimed flag and credits `progression.crystals` (clamped to `MaxCrystals`) in the same write; a denied claim writes nothing, not even the events it carried. A new token for a finished claim answers `already_claimed`, so exactly-once survives the 50-entry operation trim. Statuses: `claimed, claimed_capped, duplicate, already_claimed, not_done, not_active, unknown_objective, invalid_token, token_conflict, rate_limited, newer_version, lease_lost, save_failed, disabled, profile_not_loaded`.

**Reconnect safety.** Gameplay progress is queued in server memory (bounded 64, same-kind events merge) and committed in batches: every 30 s by the service, inside every claim, and inside the lease release. A lost acknowledgement cannot double count: the last batch id is stored (`flush`) and a claim is idempotent by its operation record. Only a hard crash can lose up to 30 s of progress.

**Not done here (separate tasks).** UI and pill (BD-075), NextGoal feed (BD-076), the nine real event hooks (BD-074), icons (BD-077), Studio server-clock rollover and Android acceptance (BD-078).

**Evidence.** `python tools/verify_objectives.py --runner <luau>` (CI step added): runs the real modules and the real `ProfileRepository` against the mocked store. It covers schema and docs/66 parity, picks, rollover and carry, counters and caps, claim-once, migration (nil / corrupt / newer), flag-off identity (not one store request, no field created, an existing field left byte-identical), reconnect, lost acknowledgements, outage, wallet clamp, write budget and the rate-limited remote. Offline only: no Studio, no real DataStore, no phone.

## 18. Implementation status BD-075: the objectives panel (2026-10-17, offline only, behind `ObjectivesEnabled`)
**All of this is OFF** with the flag (default false, pinned by `release_profiles`): `GoalHud` only requires `ObjectivesPanel` inside `if Config.ObjectivesEnabled==true`, `Bootstrap` passes `objectives=false` to the layout and publishes no rect, so with the flag off the HUD layout is byte-for-byte the old one (`verify_movement_mobile` compares 68 canvases against the previous `TouchLayout`) and no remote is looked up or called.

| Piece | File | Notes |
| --- | --- | --- |
| Pure panel rules | `src/shared/ObjectivePanelRules.luau` | Which (at most 3) rows to show, the folded one-liner, the "New tasks soon" words, claim answers, token reuse, copy check. No Instances, no clock, no reward maths. |
| Panel (client only) | `src/client/ObjectivesPanel.luau` | GoalsPanel pattern. Reads the SERVER view through `ObjectiveAction {action="view"}` (on first show, on open, every 20 s while shown, after a claim answer); sends only `{action="claim", id, token}`. Existing UI parts only: `Theme.decorate` plates, the registered `trophy` icon, no new art, no asset ids. |
| Layout | `TouchLayout.OBJECTIVES`, `compute{objectives=true}`, `objectives` / `objectivesOpen` rects | Bootstrap publishes them as the `ObjectivesRect` / `ObjectivesOpenRect` attributes (only under the flag). |
| Wiring | `GoalHud.luau` | Attaches the panel; feeds it the Goals PLAY state. |

**What the player sees.** Folded: ONE 44 px line: trophy, the nearest task ("Hatch 3 eggs"), a chip "1/3" (or "Done!" in green when something is ready). Open: header "TASKS" with "New tasks in 20 min" (docs/72: "New tasks soon" under a minute, never "5m 0s"), then the 3 active tasks, each with name, progress bar, "1/3" and "+10 crystals"; a finished task shows a 100 x 44 **CLAIM** button instead. Tap sends the claim; "..." while the answer is out; the answer shows in the header for 2.5 s ("+10 crystals", "Already got it!", "Try again"). A lost answer is retried with the SAME token (claim-once), a definite answer frees the id for a new token.

**Which 3 tasks.** Finished tasks first (tutorial, carried, short, daily), then the tutorial task, then short and daily in turns, closest to done first, so a Daily is never starved by the 30 minute Shorts. Claimed tasks leave the list. Hidden: an UNFINISHED **T8 "Collect a second species"** while the Goals panel PLAY line is on screen and not finished (docs/66 s16 watch item: one species nudge, not two). A finished T8 is a reward, so it is shown to claim. D4 "Collect a new species" is kept (it is a daily reward, not a first-session nudge).

**Where.** Hub only: hidden during a run and until the Goals panel appears (after the first egg, BD-440), exactly like the Goals panel; so the first screen and every run HUD are untouched. (docs/66 s4 "auto-collapses 5 s after a run starts" is therefore not needed: it is simply not shown in a run. Showing a folded line in a run is a later decision, it needs a spot on the crowded run HUD.)
- **Desktop** (height 500 px or more): straight LEFT of the Goals panel, same top edge, 300 px wide; clear of the rail and of the OPEN Goals panel too.
- **Phone / tablet touch and short canvases** (the TouchLayout phone layout): a new rect under the rail, between the thumbstick zone (or the egg plate / build badge) and the Goals header, 190 to 300 px wide; the weather column starts under it when they would touch. The folded rect is clear of EVERY HUD piece at 8 phones, 6 tablets and the 836 x 390 / 667 x 375 sizes minus 0/36/44/58 px of top bar. **The OPEN sheet on a phone** grows right and down from the pill and, because a phone has no free room for 3 tasks, may cover exactly three hub pieces while the player has it open: the Goals header, the weather column and the "Back to the middle" chip. It never covers the egg plate, wallet, goal line, rail, Home, Tell us!, Admin, the thumbstick zone or the jump corner; where it is shorter than 3 rows it scrolls.
- Text is 14 px or more and every button is 44 px or more at 1:1 (the panel carries no UIScale).

**Not done here.** Rewards stay the server's (`ObjectiveService`); NextGoal feed (BD-076); the real event hooks (BD-074: until then `record` is never called, so progress only moves in tests); the claim-burst, check-pop and row-pulse animations and the audio cues of s9 (no new art or sound without an asset task); the four new icons (BD-077; the panel uses the existing `trophy`); Studio pictures and Android acceptance (BD-078).

**Evidence.** `python tools/verify_objectives_panel.py --runner <luau>` (pure rules, then the REAL `ObjectivesPanel.luau` on a GUI mock fed by the REAL `ObjectiveRules` view: folded/open/claimable states, claim request shape, waiting state, same-token retry, silent in a run and before the first egg, copy rules), plus the extended `verify_movement_mobile.py` / `verify_hud.py` (panel rect versus every HUD piece). Studio pictures (folded, open, claimable at desktop and 836 x 390) go to `docs/evidence/2026-10-17-objectives-panel/` once the lead frees Studio.

## 19. Implementation status BD-076: the top objective on the one-line goal (2026-10-17, offline only, behind `ObjectivesEnabled`)
**Priority rule (one rule, highest first).** The line under the Crystals plate shows the FIRST thing in this list that exists:

| # | Shown | Example | Why |
| --- | --- | --- | --- |
| 1 | a **claimable objective** | `Done! Claim in Tasks` | free Crystals are waiting, it beats everything, even a ready fusion |
| 2 | the **fusion goal** (best in-progress or ready recipe) | `Gold: 5/6 Compy` | the long-term compass beats an unfinished small task |
| 3 | an **unfinished objective** (the panel's top row) | `Hatch 10 eggs: 3/10` | any active task is more useful than a bare XP bar |
| 4 | the **level XP fallback** | `Level 3: 50/500 XP` | only when nothing above exists |

Full 3 x 3 table (objective none / unfinished / claimable against fusion none / in progress / ready), the winner: none+none = level, none+progress = fusion, none+ready = fusion, unfinished+none = objective, unfinished+progress = fusion, unfinished+ready = fusion, claimable+anything = objective. `tools/verify_objectives_panel.py` asserts all nine.

**Which objective.** The panel's own choice (`ObjectivePanelRules.select`, the same rows the panel shows): finished first (tutorial, carried, short, daily), else the tutorial row, else short and daily in turns. **T8 watch item kept:** the goal line asks with the same `playGoalActive` flag as the panel, so an unfinished "Collect a second species" never reaches the line while the Goals PLAY line is on screen and not finished; a finished T8 is a reward and does show. Nothing is shown (the old line stays) until the server has answered once.

**Flag off.** `GoalHud` passes `objective = nil` unless `Config.ObjectivesEnabled`; `NextGoal.pick` without an objective is exactly the old `fusion or level` (checked field for field on 15 inputs), `NextGoal` knows nothing about the flag, and the text is still `prefix .. goal.text`. The line is byte-identical to Build 020.

**Copy and width (docs/72).** Short, plain, no clock, no multiplier. A finished task says `Done! Claim ...`; an unfinished one says `Name: 3/10`, and a one-step task shows only its name (`0/1` says nothing). The line is 244 design px wide; on a phone it is drawn at a fixed `floorText(17)` size (always >= 14 px on screen) and on a desktop it scales between 14 and 17 px behind a `Goal  ` prefix. Words are fitted with a conservative width estimate (`ObjectivePanelRules.textWidth`: em table for the HUD font plus 8 % slack, at the SMALLEST size Bootstrap draws the line, minus the prefix), so the line never leans on the engine cutting a word:
- finished: the longest of `Done! Claim at the objectives panel` / `Done! Claim in Tasks` / `Done! Claim it` / `Done!` that fits. The longest phrase is about 350 px at 17 px, so it never fits a 244 px line and `Done! Claim in Tasks` is what players see on all 56 checked canvases; the long phrase is kept only so a wider line would use it.
- unfinished: the whole `Name: 3/10` if it fits; else whole words are dropped from the end of the name (and a dangling `a` / `toward` / `the`) and `...` marks the cut (`Add a dino...`, `Collect a second...`), the count stays; a single over-long word becomes `Task 3/10`.
- The line re-fits whenever Bootstrap restyles it (resize, mouse/touch switch) and wakes up only when the top row changes, not on every 20 s poll.

**Evidence.** `python tools/verify_objectives_panel.py --runner <luau>` now also runs: the priority table, flag-off identity, copy and width for every catalogue task (at progress 0 and goal - 1) on 56 canvases (8 phones, 6 tablets, desktops, 667 x 317, and 836 x 390 / 667 x 375 minus 0/36/44/58 px of top bar, each as mouse and touch), the T8 versus PLAY case, and the real panel's `goalLine` / `onTopChanged` on the GUI mock. Static: `objectives` stays nil outside the flag block, `goalLine` is called only inside `if objectives then`, `NextGoal` has no flag or Roblox service. **Not proven offline:** the real on-screen width (the estimate is deliberately wide; a Studio `TextService` measurement and pictures of the line at desktop and 667 x 375 stay with BD-078).
