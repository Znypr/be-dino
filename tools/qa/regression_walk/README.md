# First-session regression walk as scripts (BD-541, docs/145 s9)

Label: **TOOLING (offline-built, NOT yet run in Studio).** The 13-step first-session walk of [docs/145](../../../docs/145-session1-readiness-2026-10-17.md) s9 as Studio `execute_luau` snippets, so one lead session can run it in minutes once a Studio window renders again. Nothing here was run in Studio, on a phone or on a published server; `tools/verify_regression_walk.py` only proves the scripts parse, keep the step order and judge a mock game correctly.

How it works: every step does what a player does. It **taps the real buttons** with `VirtualInputManager` and **fires the very remotes** those buttons fire (`RequestStartRun`, `RequestEndRun`, `RequestLeap`, `ClaimChest` through OPEN, `EquipSpecies`, `ProgressionAction`, `SetRevealSkip`, the admin panel's `AdminAction`). It never sets a profile value, an egg, a crystal or a run state. Then it checks the result (attributes, which menu is open, button and label text, `AbsolutePosition` / `AbsoluteSize` of the HUD rectangles, the log) and prints one line:

```
WALK 06 PASS Go home and Run Complete :: settled and back at home | end reason ManualExit | ...
CAPTURE 06 screen_capture now: the Run Complete card | cam (0,26,605) looking at (0,26,575) | dino 29 studs away | viewport 1156x783
```

`PASS` = every check held. `FAIL` = a check broke (the FAIL parts come first in the line). `ODD` = something could not be judged (a tap was not possible, nothing to test, a flag is off); the reason is in the line. `CONTINUE` = the step is not finished, run the same snippet again (it resumes; execute_luau calls are short).

## Setup (the lead, not scripted)

1. `python tools/build.py --profile playtest`, close other Studio windows, File > Open from File on `build/BeDino-Build<NNN>-playtest.rbxlx`. **Unpublished copy only** (memory profile, everyone is admin). The walk buys a potion, hatches eggs and equips another dino, so never run it on a published place or a real profile (step 1 says so if `game.GameId` is not 0).
2. Press Play (F5), single player, desktop-size window (at least 1000 x 600). If `Camera.ViewportSize` is 1 x 1 or `RenderStepped` does not fire, step 1 FAILs with exactly that: it is the blocker of docs/145 s9, not a game bug.
3. Do not touch the game while a snippet runs. The walk uses the admin panel's remote (Food worth x10, rain), so F2 values you set by hand are overwritten; step 13 resets them.

## Call order

Each snippet is one file: send its whole text to `execute_luau` on the datamodel named below. The CLIENT snippets share state through `shared.BDWalk` between calls.

| # | Datamodel | File | What | Expect |
| --- | --- | --- | --- | --- |
| 1 | **Client** | `00-lib.client.luau` | installs helpers, probes taps | `WALK lib ready | VirtualInputManager works ...` |
| 2 | **Server** | `40-checkpoints.server.luau` | baseline (checkpoint 0) | `WALKS 0 PASS checkpoint baseline` |
| 3 | **Client** | `10-steps-1-4.client.luau` | steps 1 to 4. Repeat while it prints `CONTINUE` (step 3 usually needs 2 to 4 calls) | `WALK 01..04`, then `SUMMARY` |
| 4 | **Server** | `40-checkpoints.server.luau` | checkpoint 1 (run still active, eggs counted, leap not rejected) | `WALKS 1 PASS` |
| 5 | **Client** | `20-steps-5-8.client.luau` | steps 5 to 8 (repeat on `CONTINUE`; step 7 usually needs 2 calls) | `WALK 05..08` |
| 6 | **Server** | `40-checkpoints.server.luau` | checkpoint 2 (settled once, copies saved, equipped, 1x in the hub) | `WALKS 2 PASS` |
| 7 | **Client** | `30-steps-9-13.client.luau` | steps 9 to 13 (repeat on `CONTINUE`; step 13 usually needs 3 to 5 calls) | `WALK 09..13` |
| 8 | **Server** | `40-checkpoints.server.luau` | checkpoint 3 (second run settled, settings saved, admin reset) | `WALKS 3 PASS` |

Then paste the `WALK` / `WALKS` lines into the BD-317 row and save the captures under `docs/evidence/<date>-regression-walk/`. A FAIL becomes a new BD row (`python tools/next_bd_id.py`), never a silent fix. The server snippet counts its own calls (baseline, 1, 2, 3); to force one put `shared.BDWalkCP = 2;` in front.

### Where to capture

Each step prints a `CAPTURE` line when it ends. The chunks run several steps in one call, so by the time you see the line the game has moved on. For **evidence images** run one step per call: put `shared.BDWalkOnly = 6;` in front of the snippet text (the chunk file of that step), read the `CAPTURE` line, then `screen_capture` at once. The steps depend on each other, so run them in order (1, 2, 3, ...); `BDWalkOnly` just selects which one runs. For the **fast pass** run the chunks as they are and capture only at the end of each chunk. The camera position in the line is where the game camera is (it follows the dino); you cannot place it, so the note says what to look at.

### If a tap does not work

* `WALK lib ready ... NOT usable (...)` or a step line `ODD ... cannot click <button>`: the Studio script context may not allow `VirtualInputManager` (not verified). The step stops, prints `NEEDS click <button> at viewport (x,y), then re-run the step` and lists it again as `NEEDS ...`. Click that spot with `user_mouse_input` (the position is in the game viewport; add the viewport's offset inside the Studio window), then send the same snippet again with `shared.BDWalkOnly = <step>;`. Every step is safe to repeat: it first checks whether the state it wants already holds and taps only if not.
* `ODD ... clicked X but nothing changed`: the tap reached the viewport but not the button (coordinates or a window that is not in front). Same hand-click remedy.
* Steps that fire a remote instead of a tap say so in the line (for example "fired RequestEndRun instead"): the server side is still exercised, the button face is not.

### If `shared` does not survive between calls

If a chunk fails with `run 00-lib.client.luau first`, `execute_luau` is not keeping `shared`. Then send **lib + chunk in one call** (paste the lib text, a blank line, then the chunk text; the lib ends with `return "lib ready"`, so delete that last line when you concatenate). Step 13 needs steps 2, 3 and 6 loaded, so send chunk 1, chunk 2 and chunk 3 in one call too, or keep one persistent Studio session.

### Call budget

A call stops after `shared.BDWalkBudget` seconds of work (default 24) and says `CONTINUE`. If `execute_luau` times out earlier, put `shared.BDWalkBudget = 12;` in front.

## The 13 steps and what each one asserts

| # | Step (how it acts) | Assertions |
| --- | --- | --- |
| 1 | **Welcome and first screen.** Waits for the profile, taps LET'S PLAY, closes the menu | viewport above 100 x 100 and `RenderStepped` fires at least 5 times in 0.5 s; unpublished copy; profile Loaded and `RunState` Sanctuary; build badge shows `Config.Build`; the welcome card opens by itself and LET'S PLAY opens the Sanctuary card; `MenuOpen` false after closing; HomeButton not "SAVING..."; rail and crystal plate on screen; no HUD rectangle (rail, crystals, EGGS plate, SIZE bar, goal hint, next goal, timers, "Tell us!", home) overlaps another by more than 4 px or leaves the screen; no new log errors |
| 2 | **Leave through the gate.** Walks the dino (`Humanoid:MoveTo`) into the Island Gate zone (`CaveGateRules.zone()`) and waits for the 1.5 s dwell; without `CaveHub` taps EXPLORE ISLAND | `RunState` Active; `Location` Island; the dino is outside the hub (`SpawnGeometry.inHub`); HomeButton reads HOME; SIZE bar visible; no HUD overlap in the run; no new errors. A blocked walk (35 s) moves the dino into the arch and says so (ODD) |
| 3 | **Eat until eggs are caught.** Admin "Food worth x10" through `AdminAction`, then walks to the best visible food (`workspace.Food`) until 6 eggs | `CatchScore` reaches 6; the EGGS plate text shows the same number; `GrowthScore` above 0; no new errors |
| 4 | **Leap.** Taps the LEAP button (else key E, else fires `RequestLeap`) | server accepted (`LeapReadyAt` rose); `LastLeapStatus` leaping; `LeapRejectCount` unchanged; apex at least 3 studs and 8 studs forward (ODD when only the remote was fired); the button shows a cooldown; cooldown running |
| 5 | **Start weather by the admin remote.** `AdminAction startWeather rain 90` | answered true; `WeatherId` rain; ends in over 45 s; the weather tile counts down "Rain ..."; `WeatherLootMultiplier` above 1 on the character; a "started" toast (ODD if missed). ODD when the player is not admin |
| 6 | **Go home and Run Complete.** Taps HOME, then GO HOME (else fires `RequestEndRun`) | back at home and ProfileState Loaded; `LastRunEndReason` ManualExit; `LastRunCatchScore` equals the eggs seen (up to +3); Run Complete shows that number; `LastRunEggCount` equals the catches (cap 150); a new `LastRunId`; BACK TO SANCTUARY and OPEN EGGS buttons; a crystals row; no new errors |
| 7 | **Eggs screen OPEN, hatch party, auto-open.** Opens Eggs from OPEN EGGS, taps OPEN, taps through 3 eggs, closes; Settings > Help puts Common on AUTO, OPEN again, then restores Common (`SetRevealSkip`) | Eggs screen open; `NestStorageCapacity` nest slots drawn; OPEN button; "Eggs waiting: N" equals active plus banked eggs; OPEN starts the hatch screen; 3 eggs claimed one at a time (`LastClaimedChestId`); "Skip the rest" present while eggs remain; dino copies went up; with Common on AUTO the "Auto-opened eggs" summary appears or the reveal stops at a non-Common egg; Common restored |
| 8 | **Equip another species, size and camera.** `EquipSpecies` with another owned species | `EquippedSpeciesId` and `LastEquipStatus` equipped; the new `LocalMeshVisual` is built; `VisualScale` is 1 (hub size); model box changed; `CameraMinZoomDistance` equals `CameraFit.minZoom`; camera distance inside the zoom limits; all 8 corners of the dino box on screen. ODD with one species or the legacy visual |
| 9 | **Potion buy and use.** Opens POTIONS; `ProgressionAction buyPotion id@window` then `usePotion` | shop list drawn; an offer with stock; buy answered ok; owned count +1; crystals fell by the price (ODD if the test wallet resets them); use answered ok; the buff is running; the HUD lists "<kind> potion m:ss" |
| 10 | **Crystal Shop tabs.** Opens SHOP, taps every tab the level shows | CONDITIONS tab hidden exactly below `FtueP1.ConditionsTabLevel`; each tab opens (blue) and its page text differs from every other page; Eggs tab has Random Egg and a buy button; Crystals tab shows the balance |
| 11 | **Fusion menu opens (no fusing).** Opens FUSION, closes with the menu's own close, opens again for the capture | the menu opens; FusionPanel visible; Browse, Ingredients and Result columns exist; panel starts right of the rail (not judged on phone-size windows); it closes again. ODD when the old Fusion card or "coming soon" shows. It never calls `FusionAction` with `fuse` |
| 12 | **Settings tabs and Reduce Motion.** Opens SETTINGS, taps the four tabs, switches Calm motion on | each tab shows its marker text (`SettingsMenu.tab()` agrees); `SettingsModel.calm()` true; `UITheme.MotionEnabled` false; the toggle reads ON; `SettingsJson` saved with `calm = true`. Reduce Motion stays ON for the capture |
| 13 | **A second run.** Calm off again, then steps 2, 3 (3 eggs) and 6 again | every check of those steps; the new run starts at 0 eggs with the EGGS plate 0 and growth near 0; the run summary counts only run 2; a new run id; the egg queue grew; admin values reset; weather clear |

Server checkpoints (`40-checkpoints.server.luau`, read only): 0 baseline (player, profile, food, terrain, admin, flags); 1 run Active, Island, caught eggs, food x10, leap accepted and not rejected, no movement rejects; 2 home, end reason, run score, banked eggs equal catches, one settlement recorded, copies went up, equipped species changed, 1x in the hub, auto-open back to none; 3 second run own id and settlement, `SettingsJson` calm false, admin reset, weather clear, no leap or movement rejections in the whole walk. Each also fails on any server log error since the baseline.

## What the walk changes (all in the memory-only unpublished copy)

Food worth x10 and the rain weather (reset in step 13), one potion bought and used, a few eggs hatched and copies added, the equipped species (step 8 leaves the other species equipped), Reduce Motion on then off, Common auto-open on then off. The walk closes menus through the documented client hook `DemoCloseModal` (Bootstrap's own `close()`); that hook sets nothing else.

## Offline self-test (CI)

`python tools/verify_regression_walk.py --runner <luau>` (in the workflow):

1. **Contract.** Every game name the scripts use (remote, attribute, GUI name, screen title, button text, module function) must still exist in `src/`; a rename fails CI with the name.
2. **Run.** The real scripts run in README order against `selftest/sim.luau`, a Roblox mock with a small Be Dino simulation (same remote, attribute, button and title names; the real pure modules from `src/shared` are loaded). The happy path must print 13 PASS lines once each in step order, a CAPTURE line per step, a CONTINUE round trip and four PASS server checkpoints.
3. **Judge.** Five broken scenarios must NOT pass: no input service (ODD with click positions), a window that does not render (FAIL), overlapping HUD rectangles (FAIL), a logged error (FAIL), a dino cut off by the camera (FAIL).

Not proven offline: that `VirtualInputManager` is allowed in the Studio script context, that `shared` and module state persist between `execute_luau` calls, the exact click coordinates, real timings, and anything visual. Treat the first Studio run as the test of the scripts themselves; fix the scripts, not the game, when a step's own mechanics are wrong.
