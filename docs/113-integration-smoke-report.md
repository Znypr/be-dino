# 113: Integration smoke report, 2026-10-16

Status: CURRENT BUILD BEHAVIOR evidence. Build: `python tools/build.py --profile playtest` from origin/main f16854e (after PrivateState #201, write budget #202, FTUE P0 #203, HudV2 private-state fix #204), own temp Studio copy, FRESH Play session (Studio preview: the profile is not saved), one local player (admin, because it is Studio). Screens: [docs/evidence/2026-10-16-integration-smoke/](evidence/2026-10-16-integration-smoke/). Script: the 15 steps of [docs/106](106-friends-playtest-readiness.md) section 4, extended with FTUE and PrivateState checks.

Method notes. Only my own Studio window was brought forward. Screens were taken with `PrintWindow`, which is not affected by other windows: plain screen grabs twice showed another agent's Studio instead of mine, so those shots were retaken. Walking: a client background loop of `Humanoid:MoveTo` towards the nearest food (a real run, no cheats). The machine ran three Studio instances, so the measured 14 fps is NOT representative. No sound was heard.

## Result table
Rating: PASS, PASS with notes, NOT RUN (cannot be done in one Studio Play session). No step FAILED.

| # | Step | Result | Evidence / numbers |
| - | --- | --- | --- |
| 1 | Welcome (new child) | PASS with notes | 01: three plain cards (Eat & grow / Jump & explore / Save & hatch), LET'S PLAY. HUD shows 1000000 Studio test crystals (expected in Studio). |
| 2 | Sanctuary card | PASS with notes | 02: the card still said "food clusters" and "Bank catches" (not covered by BD-370). FIXED in this PR (BD-377). |
| 3 | First run: hint and collapsed menu (BD-366, BD-368) | PASS | 03: hint "Eat food to grow. Bigger dinos find eggs!", SIZE bar, menu collapsed to MENU / POTIONS / SETTINGS, HOME button. |
| 4 | Eat until the first egg | PASS | First egg at growth about 90, 3 eggs at growth 249 (about 125 per egg, matches 4 per 500). 04. |
| 5 | Egg-found moment (BD-367) | PASS with notes | 04b / 05: toasts "You found an egg!" and "Frost egg caught! Hatch it at Home" (two stacked toasts cover Crystals and XP for about 3 s, BD-378). The soft pop was not heard. |
| 6 | HOME confirm and run end | PASS with notes | 05: "You found 3 eggs - Growth 276", RETURN works, no error. Title still "Return to Sanctuary?" (BD-375); a floating "+2.8" draws over the modal (BD-379). |
| 7 | Run summary | PASS with notes | 06: Growth 316, Eggs found 4, "4 run eggs / 1 egg nest" (BD-373), +30 crystals, nest toast "Ready in 2 h 59 min" (BD-369). All values arrived (PrivateState `LastRun*`). HUD EGGS reset to 0. |
| 8 | Eggs screen | PASS | 07: Nests 1/5 with five slots, "Eggs waiting: 3" beside a READY egg (BD-369: 4 eggs in total, the count excludes the shown one), Common / Normal chips. Empty state "No eggs yet / NO EGGS" after hatching (10). |
| 9 | FIRST HATCH is not Cracked (BD-365) | PASS | Eggs 1 and 2 hatched as Common Compy (Cream, Freckles) and Uncommon (08, 08b). Egg 3 was Cracked ("Oops! Splat!", 09), egg 4 an Archaeopteryx. So the 2 safe eggs hold and Cracked starts at egg 3. UI text log: `Common 26% of eggs`, `Uncommon 6% of eggs`, `Cracked hatches 1 in 5`. Note: after the first reveal the prompt said "Tap for next egg (1 left)" with 3 eggs still to open (BD-380). Skip all works. |
| 10 | Second run | PASS | 11: Growth 131, 2 eggs, +15 crystals, wallet 1000030 to 1000045. |
| 11 | Index and My dinos | PASS | 12: Dino Index with the Compy card (Common, 26% of eggs, Special variant), "???" silhouettes, "Collected 2 of 22 (9%)", FUSION shortcut. There is no separate "My dinos" page: DINOS opens the Index. |
| 12 | Shop | PASS | 13: Auras Meadow Glow 60 / Tidal Halo 470 / Royal Nova 3700, tabs Auras, Trails, Eggs, Conditions, Crystals, "Level 1 - 1000045 Crystals". No Robux prompt. Nothing bought (Studio does not persist). |
| 13 | Fusion menu | PASS with notes | 14: Gold tab "Put in 6 Base, 0 of 6", "Guaranteed: Gold!", "Pick 6 more to see your chances", donor list from the real collection (data arrived), starter card "Older dino / can't". Not a true empty state because hatched dinos exist. |
| 14 | Settings tabs and persistence | PASS | 15 / 16: SOUND, LOOK, CONTROLS, HELP. Set Everything to 40% and Weather to Lite. A listener on the server's `SetSettings` remote received `{"sound":{"master":0.4,...},"weather":"lite",...}` and the server echoed it as a PrivateState delta (`SettingsJson`, `ProfileRevision` 29) 0.8 s later: the server stored it in memory. (Studio cannot rejoin with saved data.) |
| 15 | Potion shop | PASS | 17: six offers (Treasure Draught 230, Growth Sip 25, Swift Sip 20, Lucky Sip, Hearty Brew 71, Trail Blazer 56), "New offers in 1 min", "Your potions (tap to use)". |
| 16 | Weather via admin panel | PASS with notes | 18: Admin panel (creator only), Thunderstorm 3 min started: dark sky, rain, banner "Thunderstorm 2 min", buff "Speed +15% - Growth +10% - Loot +40%" ("Loot" is jargon, BD-376). Server log "[Be Dino admin] ... started weather thunder for 180s". |
| 17 | Console | PASS | Only Roblox-core `UIBlox ... FoundationProvider not found` warnings (repeated) and the game's info lines (`redesign-020 ready`, admin weather). No game error or warning, no `Infinite yield`, no `SaveFailed`. |
| 18 | PrivateState snapshot arrival | PASS | Every menu got data: Crystals, XP, queues, nests, run summary, collection (Index, Fusion donors), settings, potions. The live client Player has 24 public attributes (no `CollectionJson`, `Crystals`, `NestsJson`). Static: `verify_private_state.py` passes (182 runtime checks, 0 static problems); no `GetAttribute` read of a private name in `src/client` (only variable-name reads on workspace and motion attributes). |
| 19 | HUD counters | PASS | EGGS plate 0 / 1 / 2 / 4 matched the character `CatchScore` read at the same time and reset to 0 after the run. The SIZE bar filled in proportion to growth (about 20 percent at growth 90). |
| 20 | Memory, parts, instances, heartbeat | PASS with notes | Workspace instances 11,582; BaseParts 7,359 server / 7,244 client; total memory 3,322 MB (Studio session, includes the editor); Instances 195 MB, Script 270 MB, GraphicsTexture 142 MB. Cull: CullParts 3,179 of 5,000, props 3,179 / 3,551. Server heartbeat: 180 frames in 3 s, avg 16.7 ms, max 20.6 ms. Client about 14 fps (three Studios on one PC: not representative). |
| 21 | Non-owner alt: no admin panel, no FOOD counter | NOT RUN | One local player only (the Studio MCP cannot start a second client). The FOOD line and Admin button were visible here (admin). Owner: docs/106 step 2. |
| 22 | Alt predation, 12-player play | NOT RUN | Needs two clients; the offline sim (`verify_multiplayer_sim.py`) passes. |
| 23 | Rejoin persistence of inventory and nests | NOT RUN | Studio preview does not persist. Covered offline by the write-budget and settlement tests. Owner: docs/106 step 14 on the published place. |
| 24 | Phone run | NOT RUN | Owner Android (docs/106 step 15). |

## Offline checks
`python tools/build.py` and `--profile playtest`: OK (358 scripts). All 71 `tools/verify_*.py` pass with the Luau runner, `verify_sources.py --compiler` compiles 358 sources, unittest discover 77 tests OK (the copy fix only touches `FtueCopy`, two client label calls and `verify_ftue_copy.py`).

## Problems found (kanban BD-377..BD-381)
1. FIXED here (BD-377): Sanctuary card text with "food clusters" and "Bank catches" (jargon, docs/72). New strings in `FtueCopy`, checked by `verify_ftue_copy.py`. Not re-screenshotted (needs a new Studio run).
2. BD-378 (P2): the egg-found moment is two toasts stacked over the Crystals/XP plate for about 3 s; "Frost egg" is unexplained to a child.
3. BD-379 (P3): the floating growth text ("+2.8") draws over the Return confirm text.
4. BD-380 (P2): reveal prompt "Tap for next egg (1 left)" after the first of 4 eggs.
5. BD-381 (P2): the Sanctuary dino renders as a blocky legacy model while the island dino is low-poly; Fusion shows an "Older dino / can't" card for the starter.
Known and still open, seen again: BD-369 (Eggs waiting count, 3 h nest), BD-373 (run eggs wording), BD-375 (Return to Sanctuary), BD-376 (Loot jargon, small text).

## Top problems for the owner
1. The first minute is readable and the safe first eggs work, but the first egg moment is noisy (two toasts) and the first-run copy is only partly clean (BD-377 fixed, BD-369/373/375 open).
2. This pass could not prove rejoin persistence, a second client or phones: do docs/106 steps 2, 6, 13, 14 and 15 on the published place.
3. Tooling: other agents' Studio windows steal the foreground; use `PrintWindow` for captures.
