# 225 Starter run: the first 3 minutes of a brand-new player (BD-1163 spec)

Label: **OWNER TARGET (decision 2026-11-10, docs/115) + LEAD spec**, 2026-11-11. Numbers are PROVISIONAL. Builds on the first-time audit ([112](112-first-time-player-audit.md)) and its fixes (BD-365 safe first eggs, BD-440 hidden goals), the research ([221](221-po-plan-team-and-research-2026-11-10.md) C2) and the watch sheet ([222](222-playtest-watch-sheet.md)).

## 1. Why

Roblox counts a player who leaves within 60 s or 180 s as a bounce, and that hurts Home ranking. Today a bot needs about 4 minutes to find its first egg and longer to see a hatch (docs/112). The payoff of Be Dino is the hatch, so a new player must see one inside about 3 minutes.

## 2. The owner decision

Only the **first run of a brand-new profile** is short and generous: guided food nearby, it ends at about 2 to 3 minutes, a few guaranteed eggs, first hatch within about 3 minutes of joining. From run 2 the normal economy applies.

## 3. Player journey (target times from joining)

| Time | What the child sees | Rule |
| --- | --- | --- |
| 0:00-0:10 | Spawns in the run, no lecture modal. One soft arrow points at a glowing food trail. | Starter run starts by itself for a new profile (no EXPLORE press needed). The welcome cards move to Settings > HOW TO PLAY. |
| 0:10-1:30 | Eats along the trail; each egg-food on it gives a visible "Egg!" pop. | The trail is a short path of food placed near spawn, only for this player (client-visible, server-validated pickups like all food). Enough egg-value food for `StarterRunEggs` eggs. |
| ~1:30 | When `StarterRunEggs` eggs are caught: a big happy card "You found 3 eggs! Take them home!" with ONE button. | The button ends the run directly (no "Return to Sanctuary?" confirm on the starter run). |
| ~1:45 | Run Complete, then straight into the hatch. | OPEN EGGS is the only big button on the starter run. |
| ~2:00-2:30 | Three eggs hatch, rising rarity, none Cracked. | `SafeEggs` 2 -> 3 so every starter egg hatches. |
| after | "Run again to find new dinos!" and the Index silhouettes. | Normal economy from run 2. Goals panel appears (BD-440 rule). |

If the child ignores the trail, nothing breaks: the run is a normal run, and the starter card still appears when `StarterRunEggs` eggs are reached. If they die, the run settles normally and the eggs they caught still count (the floor below applies).

## 4. Rules (server-authoritative)

- **Who:** a profile with zero settled runs (derived from existing data; no new stored field if a run counter already exists, otherwise one additive field, checked by the profile golden and rollback gates).
- **Egg floor:** the starter run settles at least `StarterRunMinEggs` (3, PROVISIONAL) eggs if the player reached the starter card or caught at least one egg; settlement stays exactly once.
- **Never twice:** a second join with the run unfinished does not restart the starter run unless no run was ever settled.
- **Flag:** `StarterRunEnabled`, false in Config and default profile, true in the playtest profile (docs/157), in the rehearsal list.
- **Telemetry:** BD-1166 already records first bite, first run end, first hatch and bounce; add `starter=true` on the first `run_end` so the report can compare.
- **Copy** (docs/72): "Follow the shiny food!", "You found 3 eggs!", "Take them home!", "Run again to find new dinos!". No numbers with units, no jargon.
- **Art:** the trail glow uses an existing effect or a registered texture; no code-drawn final art (art rule). If none fits, ship with plain food and a kanban row for the effect.

## 5. Tests

Pure rule tests (who gets it, floor, never twice, flag off = old behaviour), a settlement test with the floor (exactly once, retry, reconnect), a bot run in Studio measuring join-to-first-hatch (target under 3:00), then the watch sheet with real children. Not done until a person has played it (owner testing).

## 6. Open

- The trail's exact food values and length are tuned in Studio with the smart bot (docs/194).
- Whether the starter card should also appear for players returning after a long break: no, not now.

## 7. Implemented (BD-1163, 2026-11-11)

Status: **Review / test**. Code and offline tests are done. **Not seen in Studio, not on a phone, no child has played it. The food trail is NOT built (BD-1175), so the 3-minute first hatch is not reached yet.**
Labels: everything below is **CURRENT BUILD BEHAVIOR of the playtest profile only** (`StarterRunEnabled`). The default build is unchanged (flag off). Every number is **PROVISIONAL**.

### 7.1 What is built

| Spec point | Built | Where |
| --- | --- | --- |
| Who | A save with **zero settled runs**, read from data the save already has: no settled run id, empty settled-run ledger, no run or hatch operation, no egg hatched or waiting, no nest, no account XP. Anything unreadable = not new. **No new stored field.** | `FtueRules.starterQualifies` |
| Auto-start | When the dinosaur stands ready in the hub, the server starts the first run through the one run-start path (`RunLifecycle.requestStart`: save loaded, world ready, room for the eggs). Once per join, tried for at most 90 s. | `src/server/StarterRunService.luau` |
| No lecture | The welcome cards do not open for a starter; they stay under Settings > Help > How to play (already there). | `StarterRunClient` |
| Starter card | At `StarterRunEggs` = 3 eggs caught: "Great job!" / "You found 3 eggs!" / one button **"Take them home!"**. The button asks the server to end the run through the existing `RequestEndRun` remote, with no "Go home?" confirm. The X still closes the card (a child is never trapped); once per run. If the server refuses because a bigger dinosaur is close, the card comes back after 6 s. | `StarterRunClient`, screen name `starter` in `SmallScreens` |
| Egg floor | The starter run settles at least `StarterRunMinEggs` = 3 eggs **when it caught one or more** (reaching the card means 3 caught, so that case is covered). A run with no egg stays empty and the save stays a starter. Crystals, XP and nests are those of the real catches. | `ProfileEggs.commitRunSettlement`, `FtueRules.starterEggFloor` |
| Exactly once | The floor is part of the run settlement, which is exactly-once by run id (settled-run ledger and operation record). After it the save has a settled run, so it can never qualify again. The stored save is checked again inside the transaction: if it already settled a run, only the eggs really caught are banked. | same |
| Safe eggs | On the starter run the first `StarterRunSafeEggs` = 3 eggs are never Cracked (normal rule: 2). `ProgressionConfig.SafeEggs` and `FtueRules.SafeEggs` stay 2, so the default build and every later run are unchanged. | `FtueRules.starterSafeEggs` |
| Run Complete | On the starter run **OPEN EGGS is the only big button** ("Eggs found 3" shows the eggs really given). While the eggs are still being saved there is no Back home to press by mistake. | `RunComplete.luau`, `StarterRunClient.resultsMode` |
| After the hatch | One toast card **"Run again to find new dinos!"** when nothing is left to open (held back while a menu or the hatch is open, like every big-moment card). | `StarterRunClient` |
| Telemetry | `starter: true` on the `run_end` line of a starter run only (docs/122). | `RunTelemetry.runEnd`, `TelemetryService` |
| Flag | `StarterRunEnabled`: false in Config and the default profile, true in the playtest profile, in the rehearsal list. | `Config`, `tools/release_profiles.py` |

The client is told with one owner-only value, `StarterRun` (1 while the save has no settled run, else 0; never set with the flag off). The client only shows; the server decides who qualifies, starts the run and gives the eggs. The client Bootstrap was not touched (the card hangs on `SmallScreens`); the server Bootstrap got one line.

### 7.2 Not built

- **The food trail (section 3, rows 0:00 to 1:30): kanban row BD-1175.** `FoodService` builds every pickup inside one `start()` closure as shared workspace parts with no owner, and no offline test runs its ground raycasts, so a per-player trail could not be proven safe without Studio. **Effect: without the trail a new player needs about 125 food points for the card (3 eggs at 12/500), which takes minutes.** The floor still helps (one egg caught and Home pressed gives 3 eggs), but the target "first hatch inside 3 minutes" needs the trail. The line "Follow the shiny food!" exists in `FtueCopy` and is not shown anywhere yet.
- The soft arrow at spawn (needs an art asset; none registered).

### 7.3 Known edges (accepted, LEAD)

- The Egg Odds page says "Your first 2 eggs from runs are always safe." For a starter 3 are safe. The sentence promises less than the player gets; changing it means making `ProgressionConfig.SafeEggs` depend on the flag (many verifiers pin the 2).
- A starter run that caught nothing writes nothing (BD-615), so the next run is a starter run again and its `run_end` line also says `starter: true`.
- A first run with no egg that is written anyway (only after an earlier failed save) ends the starter state without the floor.
- A save that got a dinosaur or an egg before its first run (gift, test grant) is not a starter.
- The HOME button keeps its "Go home?" confirm on the starter run; only the card's button skips it.
- No new sound: the card opens at the third egg, where the egg-found cue already plays.

### 7.4 Evidence (offline only)

`python tools/verify_starter_run.py --runner <luau.exe>` (in CI): the pure rules, the words, the telemetry field; the real `StarterRunService` on mocked services (flag off = nothing; once per join; bounded retries; never a veteran); the real `ProfileRepository` on the mocked DataStore (floor paid once across retry, outage, lost acknowledgement and reconnect; empty run; big run; run 2 normal; stale cached save; 40 saves x 3 starter eggs never Cracked while run 2 has the normal odds; flag off = old settlement, nothing set; same stored fields); the wiring; mutants.

### 7.5 Not verified

- **Studio:** the auto-start next to the loading screen (does the run begin before the child can see?), the card on screen, the button ending the run, Run Complete with one button, the toast, the cave-hub path.
- **Phone:** the card layout in landscape (the numbers are computed from the visible body height but were never drawn).
- **A child:** nobody has played it; the watch sheet (docs/222) and the bot run (join to first hatch) are still to do.
- **Real DataStore:** only the mocked store was run.
