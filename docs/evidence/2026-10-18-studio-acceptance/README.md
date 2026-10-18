# Studio acceptance for the friends-playtest build, 2026-10-18 (BD-663)

Label: **STUDIO EVIDENCE, desktop Studio only, one player, unpublished copy (memory profile, everyone is admin).** Build: `python tools/build.py --profile playtest` on main `77f03e31`, file `playtest-build.rbxlx` (the lead's copy of `build/BeDino-Build020-playtest.rbxlx`), Studio id `83a5d97b-...`, `Config.Build` = `redesign-020`, `ReleaseProfile` = `playtest`, `GameId` 0. Not a phone, not a published server, not more than one player. Nothing was saved; Studio was left in Edit mode.

History of this task: the first attempt (earlier PR text) was BLOCKED because the MCP tools cannot open a file (BD-663). The lead then launched a second Studio with the .rbxlx as a command-line argument (that is the documented way now, docs/160 section 6) and this is the real run.

## Read this first

1. **The Studio viewport was tiny: 296 x 304 (GUI 296 x 246).** The Studio window itself is 1280 x 720, but the docked panels leave only that little viewport, and I may not resize or move windows. Every UI picture below is therefore phone-portrait-narrow or smaller. Clipped words ("Welcome to Be...", "Tap HOME to save your...") and HUD pieces on top of each other are **not proof of a bug at real sizes**; they are listed as "needs a real-size look" (BD-995).
2. **The playtest build from main 77f03e31 has these OFF:** `ObjectivesEnabled`, `CombatEnabled`, `SpecialFoodsEnabled`, `PerDinoCosmeticsEnabled`, `FastTravelPerk` (read from the open place's `Config`). PR #466 (docs/157, not merged) turns them ON. The task text said Objectives is on; on main it is not. So Combat, Objectives, fast travel, special foods and per-dino cosmetics could **not** be tested as shipped. I tried to flip the flags in the unsaved Studio copy to test them anyway; the permission system **denied** that call and I did not retry or work around it (BD-996).
3. **Frame time was a flat 15 fps in Studio** (66.7 ms, p95 69 ms) in the hub and on the island, with the server at 60 per second and 0 server errors. The first measurement in the Sanctuary was 40 per second. A flat 66.7 ms looks like Studio throttling a window on the virtual monitor, not the game. "Studio desktop numbers only"; no phone number can come from this.

## Results (PASS / FAIL / NOT TESTED)

| # | Feature | Result | Exact observation | Picture |
| --- | --- | --- | --- | --- |
| 1 | Place is Be Dino, playtest profile | PASS | `ReplicatedStorage.Shared.Config`: `Build` redesign-020, `ReleaseProfile` playtest, `ProfileDataStoreName` BeDino_Playtest_M1_v1, `CrystalPacksEnabled` false, `PaidRandomItemsEnabled` false, `QaOverlayEnabled` false, `StudioLocalProfilesEnabled` true (Studio only), ProfileMode "Studio preview (not saved)" | |
| 2 | Edit-mode world | PASS (limited) | Workspace in Edit mode holds only Terrain and Camera: the island is built by the server at Play, so there is nothing to capture in Edit mode. One Edit capture shows a rendered sky (Studio draws). The world pictures are Play-mode captures (the Edit-mode sky capture was not kept). | see 113, 114, 118 |
| 3 | Spawn, loading | PASS | Character spawns at the Sanctuary (0, 6.5, 580), `ProfileState` Loaded, `WorldReady` true, console line `[Be Dino] redesign-020 ready`, welcome card then Sanctuary card shown | 119 (HUD) |
| 4 | Movement, leaving through the gate | PASS | Walked to (0, 8, 482): after the dwell `RunState` Active, `Location` Island, teleported to (0, 5, 30). Walk speed 22 (25.3 with the class feel) | |
| 5 | Eating food and growth | PASS | Walking onto food raised `GrowthScore` 0 -> 22 and `VisualScale` 1.0 -> 1.15 in about 2 min at 15 fps; `CatchScore` (eggs) 6. With admin Food worth x10: 38 eggs in about 90 s, scale 1.87. Island has 3,573 food items (the debug line "FOOD: 3573" shows only to Studio or admin by design, `HudRules.showFoodDebug`) | 113, 114 |
| 6 | Leap (E key) | PASS | After E: `LastLeapStatus` leaping, Y 4.9 -> 12.5 -> 4.9, no reject counters | |
| 7 | Weather | PASS | All seven started with the admin remote and gave the right loot multiplier: Rain 1.1, Blizzard 1.25, Thunder 1.4, Volcano 1.65, Quake 1.4, Aurora 1.5, Blood Moon 1.75. Title card and particles seen for Rain, Blizzard, Blood Moon (pictures). Thunder, Volcano, Quake and Aurora looked at only by number (not pictured). Camera shake and sounds not judged. | 115, 116, 117 |
| 8 | Run end, settlement, Run Complete | PASS | HOME asks "Go home?" ("Your run ends and your eggs are saved. You found 38 eggs"); GO HOME -> Run Complete: Eggs found 38, +75 crystals; run 1: 6 eggs, +15 crystals, +1 nest. `LastRunEndReason` ManualExit. An empty run (0 eggs) settles without error | 120 |
| 9 | Run end exactly once (reconnect-safe, part) | PASS | Fired `RequestEndRun` 3 more times after the first settlement: crystals stayed 1,000,015 (one +15), same `LastRunId`. A real rejoin or disconnect mid-run needs a second client: NOT TESTED | |
| 10 | Egg hatch reveal | PASS | Eggs screen: nest slot 2 h 59, 4 empty, "Eggs waiting: 6", OPEN. OPEN shows "Egg 1 of 6", then "You hatched a Compy, Common, 26% of eggs, Cream, Horizontal Bands, NEW!". Tap for next egg works. "Skip the rest" auto-opens the ordinary ones: summary "Auto-opened 4: 2 Uncommon, 2 Common, 1 cracked", toast "5 dinos hatched, best Uncommon Stegosaurus". Collection afterwards: compy, stegosaurus, raptor as shown | 121, 122, 123 |
| 11 | Cracked egg | PASS | "Oops! Splat! This cracked egg did not hatch. Cracked eggs hatch 1 time in 5." and a NEXT EGG button; the reveal waits for a tap there (cracked eggs also stopped Skip). In a 38-egg batch 18 dinos hatched (half cracked at the default 50% weight) | 124 |
| 12 | Dinos menu (Dino Index) | PASS | "Collected 3 of 22 (13%)", Compy, Raptor, Stegosaurus shown, others "???". A "FUSION" button is on the page | 125 |
| 13 | Fusion menu (6 Base to Gold) | PASS | Opens from the rail (travels to the Fusion station). Title "Make a Gold dino"; ladder strip **GOLD 6 Base, EMERALD 3 Gold, DIAMOND 2 Emerald** (matches AGENTS.md 6/3/2). With 3 Compy: "You need 6 Compy to make a Gold Compy. You have 3". With 9 Compy "Fill for me" fills 6 slots: shows "NEW GOLD Gold Compy, Guaranteed: Gold!", Colour 1 Cream 83.3% / Blue 16.7%, Colour 2 Cream 50% / Green 33.3% / Blue 16.7%, Pattern Emerald Islands (locked), Shiny 0%, Event None 100%, BIG 0%, "Odds are shown before you fuse". Older dinos listed as "Older dino / Hatch new dinos to fuse"; other species "Different dino" | 126, 127 |
| 14 | Fusion commit | PASS | FUSE! opens "Fuse 6 Compy? All 6 dinos go away. You get 1 new Gold Compy" with an itemised list; confirm -> "Rolling 1 of 6" ... "Rolling 6 of 6" (pattern, colours, shiny, BIG) -> "Ta-da! NEW GOLD Gold Compy, Not shiny, Not BIG, Pattern Emerald Islands". Server collection after: compy base 1, gold 1 (9 -> 3 plus 1 Gold). Goal strip then reads "Gold ready: fuse Raptor" (7 Raptor). A rejoin after a fusion was not tested | 128, 129 |
| 15 | Old 50-copy fusion path | NOT TESTED | With 3 Compy the remote cannot be exercised; docs/155 and BD-617 say it is live in this build (PR #466 closes it) | |
| 16 | Shop (packs OFF) | PASS | Crystal Shops tiles: Auras (Glow), Trails (1 yours), Eggs (Coming soon), Crystals (You have 1000090). The Crystals tab says "Coming soon! Crystal packs are on the way." No price, no R$ and no buy button; a search of the whole PlayerGui for "R$", "robux" and "buy pack" found nothing. Auras, Trails and potion buying not clicked through | 130 |
| 17 | Cave hub teleport and return | PASS | Rail buttons log `hub travel znyprs -> nests / style / fusion / heart (spot 1)`; the "Back to the middle" chip shows away from the heart; Island Gate walk-through starts the run | 118 |
| 18 | Dino swap in a run (BD-613) | PASS | `EquipSpecies stegosaurus` mid-run answered `LastEquipStatus` next_run; model and walk speed unchanged (25.3). At home `EquipSpecies raptor` -> equipped, model raptor, scale 1 | |
| 19 | Movement guard (BD-611) | PASS (no lag) | After walking, 5 weather changes, a leap and 3 runs: `MovementRejectCount` and `LeapRejectCount` never set. This is one client without simulated lag; the lag check of BD-611 is NOT TESTED | |
| 20 | Goals panel (old goals list) | PASS | "GOALS (tap)" opens: COLLECT 18 of 46 found, Find a weather mutation, FAVOURITE Gold ready, PLAY 1 dino to play. This is not the new Objectives panel | |
| 21 | Objectives panel | NOT TESTED | `ObjectivesEnabled` is false in this build (see above) | |
| 22 | Combat (bite), health bars | NOT TESTED | `CombatEnabled` false in this build | |
| 23 | Fast travel perk | NOT TESTED | `FastTravelPerk` false in this build; the walk-with-guide path was the one used | |
| 24 | Special foods, per-dino auras and trails | NOT TESTED | flags false in this build | |
| 25 | Potion buy and use, Settings tabs, Reduce Motion | NOT TESTED | not clicked through this run (the 2026-10-17 walk did them) | |
| 26 | Phone, several players, published server, rejoin | NOT TESTED | needs a phone, a second client or the owner | |

## Console

Client log, whole session: 5 `UIBlox - Warning: FoundationProvider not found` (Roblox's own boot warning, as in docs/145 section 9) and 9 `The execute_luau changed camera type` notices (this tool's own). **0 errors.** Server log: **0 errors, 0 warnings**; game lines: `[Be Dino] redesign-020 ready`, the admin weather starts, one `[BD-TELEMETRY] run_end` line (`duration_s` 360, `food_raw` 207, `eggs` 6, `crystals` 15) and the `hub travel` lines. A `get_studio_state` call and a flag edit were refused by the permission system (see item 2 above).

## Numbers (Studio desktop only)

| What | Value |
| --- | --- |
| Viewport | 296 x 304 |
| Client RenderStepped | first read 40 per second (hub), then flat 15.0 per second (p50 66.7 ms, p95 69.5 ms, max 74 ms) in hub and island, UI hidden or not |
| Server Heartbeat | 60.0 per second, p50 17.0 ms, p95 17.4 ms |
| Studio memory | 3,645 to 3,654 MB (`Stats:GetTotalMemoryUsageMb`) |
| Workspace descendants | 12,831 on the island |
| Eggs per run | 6 eggs in a 6 min run with little food (food_raw 207); 38 eggs with Food worth x10 in about 90 s |

## What I did not do and why

* The 13-step `tools/qa/regression_walk` was not run as scripts: it needs about 80 KB of snippets pasted through `execute_luau`, its HUD overlap checks would fail only because of the 296 px viewport, and every tap needs a hand click anyway. I covered the same flows by hand with the mouse tool and short checks instead (steps 1 to 8, 10, 11 and 13 of that list). Steps 9 (potions) and 12 (settings tabs) were skipped.
* Taps: the mouse tool clicks in GUI coordinates (`AbsolutePosition`), not in picture coordinates; the screenshot is shifted about 58 px down against the GUI.
* Screenshots are Play-mode `screen_capture` (it works in Play). `camera_position` in Play does not move the camera (the same picture came back); to see the world I hid the ScreenGuis on the client (not saved).

## Files

Pictures 113 to 130 are also in `docs/evidence/review-2026-10-17/` (main checkout), named `NNN-studio-accept-...jpg`, and copied next to this file.
