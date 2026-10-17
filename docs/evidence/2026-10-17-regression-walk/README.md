# First-session regression walk, Studio run (BD-541, docs/145 s9), 2026-10-17

Label: **STUDIO EVIDENCE, CURRENT BUILD BEHAVIOR.** Playtest build `redesign-020` from `python tools/build.py --profile playtest` on origin/main `ab0da09` plus the BD-541 scripts of PR #388. One Studio window of its own (closed 11:49:47), unpublished copy (GameId 0, "STUDIO PREVIEW, progress not saved, test currency"), Play mode, one player (admin). The window rendered: RenderStepped 44 per second in the 2 s probe (60 per second in step 1), `Camera.ViewportSize` 1140 x 785. This is a desktop-size window, **not a phone**: nothing here is phone-verified.

## How it was run

The README call order of `tools/qa/regression_walk/` with `shared.BDWalkOnly = N` so each step stops with its own screen. Facts learned about the tooling:

| Fact | Consequence |
| --- | --- |
| `shared` survives between `execute_luau` calls. | The chunks install once; later calls only run a step. |
| `VirtualInputManager` is **blocked** in the script context ("The current thread cannot call SendMouseMoveEvent"). | Every tap became a printed `NEEDS click ... at viewport (x,y)`. Each was clicked by hand with `user_mouse_input` (Client) at exactly those numbers (they are GUI-space, no extra offset; a click 58 px too low hit the scrim). The leap used `user_keyboard_input` E. |
| `require(...)` of a game module from the script gives a **second copy** (own Lua VM): `FusionMenu.close()`, `SettingsMenu.tab()`, `SettingsModel.calm()`, `UITheme.MotionEnabled` and the server `PrivateState` store are NOT the game's. | Steps 11, 12, 13 and the server checkpoints were rewritten to read what the player sees and the saved `SettingsJson` (see "Script fixes"). |
| `execute_luau` leaves the camera on `Fixed` (it logs "changed camera type" each call). | The walk sets `CameraType = Custom` at the start of a call; every capture was taken after setting it back to Custom. |

## The 13 steps

PASS = every check held. ODD = a check could not be judged by the script (all ODDs here are the blocked tap, or a module copy), the game did what it should. `after fix` = the script said FAIL, the cause was the script, the fixed script / a hand check shows the game right. No step ended as a game FAIL.

| # | Step | Verdict | What happened | Image |
| --- | --- | --- | --- | --- |
| 1 | Welcome and first screen | **ODD** (tap) | Viewport 1140 x 785, 30 frames in 0.5 s, profile Loaded, hub, build badge `BUILD redesign-020`, welcome card opened by itself. LET'S PLAY hand-clicked: the card closed, the hub shows (HOME button "TAP TO GO!"), rail and crystal plate on screen, no HUD rectangles overlap or leave the screen, no new errors. (The Sanctuary card did not open after LET'S PLAY: my first click was 58 px low and hit the scrim, which closes the card; not re-tested, see Not checked.) | `01a-welcome-card.jpg`, `01-welcome-first-screen.jpg` |
| 2 | Leave through the gate | **PASS** | Walked into the Island Gate arch, run Active, Location Island, dino outside the hub, HOME button reads HOME, SIZE bar shown, no HUD overlap. | `02-leave-through-gate.jpg` |
| 3 | Eat until eggs are caught | **PASS** | Admin Food worth x10 answered; 12 eggs in 1 s; EGGS plate "EGGS 12"; growth 50. | `03-eat-until-eggs.jpg` |
| 4 | Leap | **PASS** (key E) | The script's own leap went by the remote only (ODD: server accepted, cooldown 60 s, not launched). Pressed E for real after the cooldown: apex +10.2 studs, 51 studs forward, `LastLeapStatus` leaping, no reject, button "LEAP 1 min". | `04-leap.jpg` |
| 5 | Weather by the admin remote | **PASS** | `startWeather rain 90` answered true, WeatherId rain, 90 s, tile "Rain ...", loot multiplier 1.4, toast "Rain started!", the RAIN! card shown. (A natural Thunderstorm had already shown in step 4.) | `05-weather-rain.jpg` |
| 6 | Go home and Run Complete | **ODD** (tap), checks PASS | HOME and GO HOME were hand-clicked and worked (card "Go home? You found 34 eggs, Growth 122"). Back at home, end reason ManualExit, run score 34 = the 34 eggs seen, Run Complete shows 34 and "+68 Crystals", "+2 nests", BACK TO SANCTUARY and OPEN EGGS. The script also fired `RequestEndRun` because my GO HOME click raced it. | `06a-go-home-card.jpg`, `06-go-home-run-complete.jpg` |
| 7 | Eggs screen, hatch party, auto-open | **PASS after fix** (taps by hand) | OPEN EGGS: "Nests 2/5", 5 nest slots, "Eggs waiting: 34", OPEN; OPEN starts the hatch screen ("Egg 1 of 34"), eggs claimed one at a time, "Skip the rest" present. The script said FAIL "copies 1 -> 1": script bug (copies are in `variants[].count`); counted properly the copies went 1 -> 8. Settings > Help > Common AUTO, then OPEN: Common eggs opened by themselves and it stopped at a Rainbow egg "Always shown". Common set back to SHOW (`SetRevealSkip`). | `07a`, `07b`, `07c`, `07-auto-open-stops-at-rainbow.jpg` |
| 8 | Equip another dino, size, camera | **PASS after fix** | Equipped dimorphodon (also compy and back): `LastEquipStatus` equipped, model built, `VisualScale` 1, model box 6.6 x 7.8 -> 5.1 x 5.8, minimum zoom 12.0 = expected 12.0, camera 17.5 studs (limits 12 to 110), 8 of 8 box corners on screen. First try said 0 of 8: the tool had left the camera on Fixed (82.7 studs away). | `08-equip-other-dino.jpg` |
| 9 | Potion buy and use | **ODD** (wallet) | Buy Growth Sip answered true/purchased, owned 0 -> 1, use answered true/activated, buff running 299 s, HUD lists "Growth potion 5 min / Growth +26%". Crystals 1000000 -> 1000000: the Studio test wallet resets to `StudioTestCrystals` on every action (ODD, by design). First try FAILed with use "busy" (server rate limit 0.4 s, script too fast). | `09-potion-buy-use.jpg` |
| 10 | Crystal Shop tabs | **PASS** (tabs by hand) | Landing tile opens the tabs; AURAS, TRAILS, EGGS, CRYSTALS each open with a page different from the others; CONDITIONS hidden at level 2; Crystals tab "You have 1000000 Crystals". Eggs tab shows Random Egg 150 Crystals, ODDS / DETAILS and COMING SOON (BD-532, intended): the script wanted a buy button (fixed). | `10-crystal-shop-tabs.jpg`, `10a-eggs-tab-coming-soon.jpg` |
| 11 | Fusion menu (open only) | **PASS after fix** | Opens ("Make a Gold dino", GOLD 6 Base), FusionPanel on screen right of the rail (x=199, rail ends x=183), Browse / Ingredients / Result columns. The script's `close()` did nothing (module copy); the menu's own X closes it and FUSION opens it again (hand-checked). Nothing fused. | `11-fusion-menu-open.jpg` |
| 12 | Settings tabs and Reduce Motion | **ODD** (module copy) | SOUND ("Hatch sound"), LOOK ("Calm motion"), CONTROLS ("Camera"), HELP ("HOW TO PLAY") each show their page; Calm motion toggled ON (reads ON), `SettingsJson` saved `calm = true`. `UITheme.MotionEnabled` cannot be read from the script (own copy): ODD. | `12-settings-reduce-motion.jpg` |
| 13 | A second run | **PASS after fix** | Calm off again (saved), gate, new run starts at 0 eggs with EGGS 0 and growth 0, 12 eggs, HOME, Run Complete counts only run 2 (12 eggs, +30 Crystals), new run id, egg queue 24 -> 36, admin values reset, weather clear, Food x1. First try FAILed "home button says EXPLORE ISLAND": the label turns HOME 0.14 s after RunState is Active, the script read it at once (fixed). Second run ended by `RequestEndRun` in the call, then once more by hand (HOME, GO HOME) for the image. | `13-second-run-complete.jpg` |

Server checkpoints (`40-checkpoints.server.luau`): 0 PASS (food 3573, terrain, admin, CaveHub=true, LowPolyDinos=true, ClassMovement=true, profile playtest, mode Studio preview); 1 PASS (run Active, Island, 12 eggs counted, Food x10, leap accepted, 0 leap and movement rejects); 2 and 3 **ODD** because every owner-only value reads empty from the script's own PrivateState copy (the same facts were checked from the client in steps 6, 7, 12, 13); the readable parts passed (end reason ManualExit, run score 12 covers eggs, equipped species compy -> dimorphodon, VisualScale 1, second run id, weather clear, Food x1, no leap or movement rejection in the whole walk, no server errors since the baseline).

## Output errors

Game: **none.** Server `LogService` errors and warnings other than UIBlox since the baseline: 0. Client: 0 errors; the only non-UIBlox lines are 21 warnings "The execute_luau changed camera type. Resetting ..." from the Studio MCP tool itself (not the game). UIBlox `FoundationProvider not found` warnings fill the boot log (known, studio-only, not a game script). No script or line errors from `src/`.

## Script fixes made in this PR (tools/qa/regression_walk)

* `ownedCount()` counts `variants[].count` (steps 7, 8, server `copies()`).
* Step 2 waits up to 3 s for the HOME label.
* Step 8 sets the camera to Custom before it measures.
* Step 9 retries on `busy` and accepts the Studio test wallet reset.
* Step 10 resumes tab by tab (a hand-click round per tab), accepts COMING SOON (BD-532); steps 9, 10, 12 no longer close the menu a hand click just opened.
* Steps 11, 12, 13 and the server checkpoint read what the player sees and `SettingsJson` instead of module copies; private-value checks degrade to ODD when the store is not readable.
* The mock game got the Fusion menu X button; `verify_regression_walk` knows "Coming soon" upper-cased.

## Game fix made in this PR

`WeatherVisuals.client.luau`: after the RAIN! card faded out, `titleBig` stayed true, so walking into the cave called `softenTitle()` which put the faded title back at 35 percent opacity for good (visible in `08-equip-other-dino.jpg`, "RAIN!" in the hub). `titleBig=false` once the fade starts; `verify_cave_weather` checks it. Verified by the verifier only; the live window was not rerun after the fix.

## Odd, not fixed, tracked

* BD-546: menu cards (left edge x=140) cover the left rail (right edge x=183) at 1140 x 785 (images 06, 07a, 12: "DINOS" is cut); the Crystals tab shows R$ buttons under "Coming soon!" (confirm inert).
* Nest timers read "2 h 59 min" (docs/72 says no "5m 0s" style for children): not changed.

## Not checked

The Sanctuary card after LET'S PLAY (see step 1), a tap by `VirtualInputManager`, a phone, a published server, Studio with more than one player.
