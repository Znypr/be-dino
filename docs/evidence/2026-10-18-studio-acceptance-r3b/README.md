# Studio acceptance round 3b, 2026-10-18: the Studio tools work now (BD-575, BD-1000 to BD-1003, BD-1015)

Label: **STUDIO EVIDENCE, desktop Studio, one player, unpublished copy (memory profile, test wallet, the player is admin).** Game viewport **1156 x 793 for the first 85 minutes, then it shrank to 296 x 304** (see "What went wrong"). Round 3 (blocked, [../2026-10-18-studio-acceptance-r3/README.md](../2026-10-18-studio-acceptance-r3/README.md)) did nothing because the permission checker refused the mouse, keyboard and console tools; this round the owner's allow rules were in place and **nothing was refused**.

Build: `python tools/build.py --profile playtest` on `origin/main` `84001c99` (secret roster of nine, BD-1000 to BD-1003 fixes in it), `python tools/verify_release.py --profile playtest --place ...` passed (40 keys), copied to `C:/Users/znypr/dtmp/playtest-build4.rbxlx` and opened by launching Studio with it (studio id `cfcd0154-...`, killed after a hang, then `dbe9941b-dd75-4d42-a40f-c8f0ffa825bc`). `Config` read in Edit mode: `Build` redesign-020, `ReleaseProfile` playtest, `SecretSpeciesEnabled` true, `CrystalPacksEnabled` false, `PaidRandomItemsEnabled` false, `QaOverlayEnabled` false, `RunTelemetryEnabled` true, `ObjectivesEnabled`, `CombatEnabled`, `SpecialFoodsEnabled`, `PerDinoCosmeticsEnabled`, `FastTravelPerk` true, `FoodCatchRate` 0.024 (12 per 500). I did not change any rule, flag or chance; the old playtest-build3 Studio was stopped (no state worth keeping).

## Which tools worked (the plain answer)

| Tool | Result this round |
| --- | --- |
| `user_mouse_input` (`moveTo`, `mouseButtonClick` with `mouse_button` left, `wait` with `wait_time_ms`) | **Worked** for about 85 minutes: Welcome "Let's play", Tap to go, HOME, GO HOME, X buttons, hatch, Skip the rest, Dinos EQUIP, Settings, Admin sliders, Fusion Fill / FUSE. **Then it stopped doing anything** (no click reached the game, the tool still said "Success"). Not a permission refusal: the window had been shrunk to 296 x 304 and ran at 15 frames a second (window in the background), see below |
| `user_keyboard_input` (`keyDown` / `keyUp` with `key_code`, `wait`) | Worked (G opens a hub station, Escape). Stopped together with the mouse |
| `get_console_output` | Worked, always returns the whole log (about 40 lines of Roblox's own UIBlox warning first) |
| `execute_luau` (Edit, Client, Server) | Worked. **A script loop that never waits froze the whole Studio** (my mistake, see below) |
| `start_stop_play` (`is_start`), `get_studio_state`, `character_navigation` (`x`, `y`, `z`, finds a path) | Worked |
| `screen_capture` | Works but needs a `capture_id` text; it ignores `scale` |
| Anything refused by the permission checker | **None** |

Coordinates: a click at (x, y) lands on the GUI element whose `AbsolutePosition` rectangle holds (x, y); the picture is 58 pixels lower (picture y = click y + 58).

## What went wrong in the run (so the next agent does not repeat it)

1. **I froze Studio once.** My first "walk to the nearest food" script had a loop path with no `task.wait` (the food was 2 to 2.5 studs away and the loop spun at once). Every Studio tool then timed out, including `start_stop_play`. After about 25 minutes I stopped my own Studio process and launched `playtest-build4.rbxlx` again. Rule for scripts: **every loop iteration must wait**.
2. **The game window shrank and stopped taking input.** About 85 minutes in, the Studio window was 656 x 559 and the game view 296 x 304, the frame rate fell from 60 to 15 a second and clicks and keys did nothing (the Claude app was the foreground window). I did not move, focus or resize anything. Pictures 191 to 193 are the only ones at that size. **Not seen at 1156 x 793 because of this:** the fusion roll bar (BD-1003, checked by numbers instead), X on the Fusion screen and the Shop, the Dino Index "secrets found" line.
3. A Humanoid `MoveTo` in the cave hub gets stuck on the nest and sign props (a script problem, a player steers round them); `character_navigation` walks there fine.

## Results

| # | Item | Result | Exact observation | Picture |
| --- | --- | --- | --- | --- |
| 1 | BD-1000 plain Compy equip, toast whole | **PASS** | Dino Index, Compy x 5 (Plain, Horizontal Bands, Emerald Islands, Bold Patches, Freckles). EQUIP on each card in turn: `EquippedGenesJson` became that card's pattern every time (`08_freckles`, `04_bold_patches`, `02_emerald_islands`, `05_horizontal_bands`) and **`null` for Plain** (the starter look), `LastEquipStatus` equipped each time. Back to Plain from another Compy works. EQUIP on the already equipped card gives a calm gold "Already equipped"; the toasts "Equipping..." and "Already equipped" are whole | 181, 182, 183 |
| 2 | BD-1001 Skip the rest does not stop on cracked eggs | **PASS for the cracked egg, but the acceptance sentence "one tap" is NOT met** | 13-egg batch: one tap on Skip the rest after egg 7 ended on "Auto-opened: 6 / 1 Rare, 1 Uncommon, 1 Common, 3 eggs did not hatch" (6 = 1+1+1+3). 150-egg batch: the summary came out as "Auto-opened: 132 / 1 Epic, 3 Rare, 18 Uncommon, 53 Common, 57 eggs did not hatch" (132 = 1+3+18+53+57, with 18 more eggs shown by hand before). **It still stopped about 20 times**, each time on a Rainbow, Astra or BIG egg ("Tap for next egg"): eggs 43, 62, 69, 73, 77, 80, 100, 103, 108, 109, 113, 117, 119, 128, 140 and three more. That is the designed "never skip a notable egg" rule (`RevealSkip.isNotable`), not the cracked-egg bug, but it is about 20 taps instead of the 80 of round 2 and not "at most one". The one-by-one splat still plays ("Oops! Splat!", "This cracked egg did not hatch") | 179, 180, 189, 194 |
| 3 | BD-1002 Golden Drumstick toast | **PASS** | Walking onto a `golden_drumstick` (nearest of 33, Points 60): growth went from 244 to 310 (admin food x9.5 was on), and a toast "Golden Drumstick!" with "A giant tasty snack!" under it showed. No such toast for the ordinary berries eaten before it in the same run | 186 |
| 4 | BD-1003 fusion roll marker | **PASS by numbers, not seen at 1156 x 793** | In the live roll (Colour 2 and Colour 3 steps) the reel strip is 70 px high (y 104 to 174). The marker is now two notches of 14 x 9 px, one at the top edge (y 104 to 113) and one at the bottom edge (y 165 to 174), at x 142 to 156. The labels ("Cream 33.3%", "Green 16.7%", "Blue 50%") are two centred 18 px lines in the strip, so the two notches never touch the text; no full-height pointer frame exists. The window had shrunk before I could take the picture at a readable size (picture 193 is the result screen at 296 x 304) | 192, 193 |
| 5 | Two fusions (6 Compy each) | PASS | Confirm "Fuse 6 Compy?" lists the six, "Guaranteed: Gold Compy!"; 6 rolls; "Ta-da!" with "Gold Compy, NEW FRECKLES COMPY! Gold stage: guaranteed. Made by you." and "Colours: Green 4% / Blue 96%", then "Gold Wavy Stripes Compy" (Cream 85% / Blue 15%). X closed the first result screen | 193 |
| 6 | X (and tap outside) on the screens | **FAIL on the hatch reveal**, PASS elsewhere | **Hatch reveal ("An egg is hatching..." and "You hatched a dinosaur!"): X does nothing**; during the wobbling-egg phase a click on X or on the dark area outside counts as a tap and moves to the next egg (eggs 2 to 6 moved by my X and outside clicks); in the dino phase X and Escape do nothing. Go home (X and outside tap), Dino Index card (X), Settings (X), Auto-opened summary (X), Eggs screen (X), Fusion result (X, once): all close. Escape did not close the hatch reveal or a Fusion result | 178 |
| 7 | Run Complete "OPEN EGGS" | **FAIL (new)** | The button does not open the eggs. It shows a "Follow the glow" toast (and a glow trail on the floor) and the Run Complete card stays open. The Eggs screen opens only when the player walks to the nest station (89 studs, the sign is behind the nest props) and presses G (10 studs). The rail buttons DINOS and EGGS in the cave do the same ("Follow the glow") unless Fast travel (500 crystals) is owned. This is the BD-289 design, but the one button a child presses right after a run does nothing visible | 176, 184, 185 |
| 8 | Egg Odds / cracked share | note | 13 eggs: 6 did not hatch; 150 eggs: 57 did not hatch (38 percent; default Cracked 50 percent with 1 in 5 hatching, about 40 percent of eggs fail by the docs). The hatch reveal says "Cracked hatches 1 in 5" | 179 |
| 9 | Secret dinos (nine) | **NOT TESTED, no PASS or FAIL** | 163 eggs hatched in two batches (13 and 150, about 96 of them not cracked); no "Secret find" banner appeared and no secret card was seen. The real chance is 0.5 percent per free egg (docs/173), so about 0.5 secrets were expected; I did not force it. By reading the source: `EggsLogic.shouldAutoOpen` and `RevealSkip.isNotable` know nothing about secrets, so a secret hatched under "Skip the rest" would be opened silently (row BD-1057) | |
| 10 | Console | PASS | No error and no warning from the game. Server lines: `[Be Dino] redesign-020 ready`, `[Be Dino admin] znyprs set foodMultiplier = 10`, the telemetry lines below. Only Roblox's own UIBlox "FoundationProvider not found" warning (5 times at start) | |

## BD-575: the five-minute run (a script walked, not a person)

How it was walked: a client script chose the next berry among the six nearest within 90 studs (12 percent of the time a random heading), walked 2.5 to 5 seconds at the normal walk speed (22), then stopped for 0.3 to 1.6 seconds, with a 2 to 4 second look-around about every 25 to 35 seconds, and jumped when stuck: about **60 percent of full speed, no beelining, no admin values** (food worth x1). It is a lower bound of a clean player, **not a human**. The Rain weather event came by itself.

| What | Value |
| --- | --- |
| Run length (telemetry) | **322 s** (5 min 22 s; I pressed HOME at about 305 s, the "Go home?" window and its countdown took the rest) |
| Food, real raw points (`food_raw`) | **570** (the derived `food` field says 542) |
| Eggs | **13** (`eggs_food` 14 before rounding and weather); Run Complete "Eggs found 13" |
| Crystals, nests, growth | +31 crystals, +1 nest, growth 59 |
| Weather during the run | Rain, 61 seconds (`weather_s`), "Growth +25%, Eggs +10%" |
| Rate | about 106 food a minute, 2.4 eggs a minute |
| Against the docs/119 target (600 to 700 food, about 15 eggs in 5 minutes) | 570 food is 81 to 95 percent, 13 eggs is 87 percent, for a deliberately casual walker. A person who steers to clusters will be a little above that, so **12 per 500 looks about right**; the keep-or-lower decision is still the owner's |
| Telemetry line | `[BD-TELEMETRY] {"event":"run_end","duration_s":322,"reason":"ManualExit","food":542,"food_is_estimate":true,"food_raw":570,"eggs_food":14,"weather_s":61,"eggs":13,"nests":1,"crystals":31}` |

Second run, only to get a big batch (admin "Food worth" slider at its top, **x9.5**, a greedy nearest-berry walker, so NOT a pace number): `{"event":"run_end","duration_s":303,"reason":"ManualExit","food":6250,"food_is_estimate":true,"food_raw":968,"eggs_food":232,"weather_s":31,"eggs":150,"nests":5,"crystals":272}`. The run **stopped adding eggs at 150** (`RunEggMaxPerRun`; `eggs_food` says 232 would have been earned): Run Complete "Eggs found 150, +272 Crystals, +5 nests, Growth 994, Level 3". Hatch counts logged: `hatches` 109 and 41 (the 150 eggs in two server calls).

## Numbers

| What | Value |
| --- | --- |
| Viewport | 1156 x 793 (first 85 minutes), then 296 x 304 |
| Frame rate | 60 a second at first, 15 a second after the window went to the background (Heartbeat/RenderStepped count) |
| Studio memory | about 4.3 GB |
| Telemetry | see above; no errors in the server log |

## Defects (new rows in docs/07-kanban.md)

| Row | P | What |
| --- | --- | --- |
| BD-1054 | P1 | X, tap outside and Escape do nothing on the egg hatch reveal (a click on X moves to the next egg while the egg wobbles) |
| BD-1055 | P1 | Run Complete "OPEN EGGS" does not open the eggs (only "Follow the glow", the card stays open) |
| BD-1056 | P2 | "Skip the rest" still needs about 20 taps for 150 eggs because every Rainbow, Astra and BIG egg stops it |
| BD-1057 | P2 | "Skip the rest" would silently open a Secret (or Legendary) find; by source only, not seen |
| BD-1058 | P3 | Studio agent notes: loops without a wait freeze Studio, input stops when the window loses focus, tool call shapes |

## Not tested and why

* Secret dinos (scale, feet, Index card, banner, equip, walk): the 0.5 percent roll did not hit in 163 eggs and the forced route is not allowed.
* Fusion roll bar picture at 1156 x 793 and 640 x 360, X on the Fusion menu after the first result, X on Shop and Potions, the Dino Index "secrets found" line: the window shrank and stopped taking input.
* A human five-minute run. The 322 s number above is a slow script.
* Phone, two clients, published server, sounds.

## Files

Pictures 175 to 194 are in this folder and in `docs/evidence/review-2026-10-17/` (also copied into the main checkout folder): 175 run in the rain (camera inside a tree), 176 Run Complete 13 eggs, 177 Eggs screen, 178 X does not close the reveal, 179 splat one by one, 180 Skip the rest summary (13 eggs), 181 to 183 Compy stack, equip Plain and "Already equipped", 184 DINOS "Follow the glow", 185 hub nest station, 186 Golden Drumstick toast, 187 Run Complete 150 eggs, 188 Eggs screen 150, 189 and 194 Skip the rest stopping on Rainbow eggs, 191 summary cut off at 296 x 304, 192 and 193 fusion at 296 x 304. Studio `playtest-build4.rbxlx` (studio id above) is left open; Play is stopped.
