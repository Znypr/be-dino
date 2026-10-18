# 194 The Studio test bot and the first measured pace (BD-1048, BD-575, BD-1076) and the Index check (BD-1063)

Label: **STUDIO EVIDENCE** (desktop Studio, one player, unpublished copy, memory profile, test wallet, player is admin), 2026-10-18. Nothing was published, no flag changed, no chance forced, nothing bought with Robux. The bot is a **script, not a person**: it is a clean upper bound for a player who knows where the food is, never the pace of a child. Pictures: `docs/evidence/2026-10-18-index-check/` (copies in `docs/evidence/review-2026-10-17/`, files 300 to 316).

## 1. The bot (BD-1048)

`tools/studio/player_bot.luau` (plain Luau, **not shipped, not under src/**, no remote of its own) plus `tools/studio/run_player_bot.py` (prints the snippet to paste into `execute_luau`, like `render_insert_snippet.py`; tests in `tests/test_player_bot_snippets.py`).

What it does, in order, every 0.1 s:

1. Reads the real `workspace.Food` (position, `Points`, eaten = `Transparency` 1) every 0.2 s.
2. Picks the next food by **value per walking time**: `points / ((flat distance + 2 x height difference) / walkSpeed + 0.25 s)`. The 0.25 s is a fixed "eating" cost. Foods blacklisted, more than 11 studs higher or lower, outside the **view radius**, or within **34 studs of a wild predator** are skipped.
3. Walks with `Humanoid:MoveTo`. **Stuck** (moved less than a third of what the walk speed allows in 1.4 s): jump once, then `PathfindingService` waypoints; stuck again after a path: every food within 15 studs of the target is ignored for 100 s (a pocket in a rock, the arena edge).
4. A wild predator within 34 studs: walk 50 studs straight away from it (aggro range is 26, chase speed 11, player 22).
5. Starts the run with the same remote the EXPLORE button fires (`RequestStartRun`) and ends it with the one GO HOME fires (`RequestEndRun`), at the stop condition (seconds since the run began, or estimated food).
6. Reads the Run Complete card text and prints where to click for OPEN EGGS (`Bot.buttons()`). It cannot click for you (a script cannot press a GUI button in Studio); the mouse tool does that.
7. **One log line per event** (`target`, `eat`, `skip`, `stuck`, `path`, `flee`, `stop`, `end`, `card`, `done`) with time, food kind, points, running `food_raw` and eggs. The `target` line holds the decision: id, points, distance, score and the second best. There is **no random move**.

### How to run it (Play session running, studio id from `list_roblox_studios`)

```
python tools/studio/run_player_bot.py install            # paste the output into execute_luau, datamodel_type Client (once per Play session)
python tools/studio/run_player_bot.py start --seconds 300                       # sees 170 studs, no pause: the "knows the map" player
python tools/studio/run_player_bot.py start --seconds 300 --max-distance 60 --think 0.4   # sees what is on screen, looks around for 0.4 s
python tools/studio/run_player_bot.py status             # one line (call it every minute; each call takes a second)
python tools/studio/run_player_bot.py report             # totals, a table per 30 s, every event except single eats
python tools/studio/run_player_bot.py log --from 1 --to 80   # raw lines, eats included
python tools/studio/run_player_bot.py buttons            # the open buttons and where to click
python tools/studio/run_player_bot.py stop
```

The loop runs in its own thread (`task.spawn`), so `execute_luau` returns at once and every poll is a separate call. **Every loop waits**, so Studio never freezes (docs/192). A `status` call that waits more than about 60 s times out in the tool (the bot goes on). The estimate of `food_raw` (foods that vanished within 10 studs of the player) matched the server telemetry within 0.1 to 1.6 percent in all five runs.

### What is unreliable (read before quoting a number)

* It is **not a person**: it never gets lost, never misreads the screen, never stops to look at a menu. The "view radius" and "think" settings are **assumptions**, not measurements of a child.
* Single runs. Weather, the random predator walks and the respawn timing make two runs differ by a few percent. No run was repeated.
* `food_raw` in the bot is an estimate (the telemetry line is the real number, taken from the Studio console after the run).
* About 15 percent of targets end in "reached but not eaten": the food is on a ledge or behind a rock (the server needs a clear line from the mouth). The bot ignores that food for 25 s. Stuck spots cost one run about 45 seconds before the area rule was added.
* The bot loops the same high-value foods again after the 8 s respawn (for example `golden_drumstick@(-331,368)` at 278.6 s and again at 288.7 s). A person may do the same once they know; a child who does not will not.
* The window was 500 x 465 (then 296 x 464 after the runs); the bot does not care, but all UI checks were made at that size.

## 2. Five-minute pace (BD-575, BD-1076)

CURRENT BUILD: main `3ced659f` (**old sector placement**: 20 x 20 sectors, one jittered bundle of 9 each; `FoodLayerEnabled` is not in this build) and, for the map, a **throwaway** build of PR #518 (`bd1047-food-layer` merged with main, flag `FoodLayerEnabled` true as the playtest profile sets it, 3,600 foods planned, 52 moved, 0 dropped; stamp `bee8bc25*`, nothing committed). Playtest profile, `FoodCatchRate` 0.024 (12 per 500), no admin values, no forced chances.

| # | Layout | Bot (sees, pause) | Length | food_raw (server) | per minute | Eggs | eggs from food at x1 | Eggs per 500 food (food only) | Weather |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | old bundles | 170 studs, 0 s | 40 s | 1,282 | 1,922 | 43 | 31 | 12.1 | 40 s |
| 2 | old bundles | 60 studs, 0.4 s | 300 s | **4,149** | 830 | 113 | 100 | 12.0 | 45 s |
| 3 | old bundles | 170 studs, 0 s | 300 s | **6,558** | 1,312 | 150 (the per-run cap) | 157 | 12.0 | 40 s |
| 4 | designed map | 60 studs, 0.4 s | 300 s | **4,262** | 852 | 108 | 102 | 12.0 | 43 s |
| 5 | designed map | 170 studs, 0 s | 300 s | **5,358** | 1,072 | 143 | 129 | 12.0 | 84 s |

Telemetry lines (copied from the Studio console, `[BD-TELEMETRY]`): run 2 `{"event":"run_end","duration_s":300,"reason":"ManualExit","food":4708,"food_is_estimate":true,"food_raw":4149,"eggs_food":100,"weather_s":45,"eggs":113,"nests":4,"crystals":207}`; run 3 `{"duration_s":300,"food":6250,"food_raw":6558,"eggs_food":157,"weather_s":40,"eggs":150,"nests":1,"crystals":272}`; run 4 `{"duration_s":300,"food":4500,"food_raw":4262,"eggs_food":102,"weather_s":43,"eggs":108,"nests":4,"crystals":198}`; run 5 `{"duration_s":300,"food":5958,"food_raw":5358,"eggs_food":129,"weather_s":84,"eggs":143,"nests":1,"crystals":260}`.

What the numbers say (plain words):

* **The egg rate itself is right.** Every run gives 12.0 eggs per 500 food (`eggs_food` / `food_raw` x 500); weather adds about 10 percent on top. The food-to-egg conversion is not the problem.
* **The food pace of a bot is 6 to 11 times the docs/119 target** (600 to 700 food, about 15 eggs in 5 minutes): 4,100 to 6,600 food and 108 to 150 eggs. The slow script of round 3b (570 food, 13 eggs) was the other end. A person sits between them; no person was measured.
* **Most points come from two rare kinds.** Run 3: amber 72 x 50 = 3,600 and golden drumstick 31 x 60 = 1,860 are **83 percent** of 6,538 points, although they are 3 and 1 percent of the foods; berries gave 294. Run 5 (map): 77 percent, run 4: 66 percent. They **respawn after 8 seconds** (`FoodRespawnSeconds`) and a walker comes back to the same spot.
* The 150-egg per-run cap (`RunEggMaxPerRun`) was reached between 210 and 240 s in run 3; `eggs_food` shows the uncapped 157.
* **BD-1076, designed food map vs today's bundles.** The bot that sees only what is on screen got the **same** food (4,262 vs 4,149, +3 percent, inside the noise of one run). The bot that sees the whole map got **18 percent less** (5,358 vs 6,558). That matches the offline walker model's "15 to 18 percent fewer" (docs/187 G) and is **less** than the offline "greedy best-per-second" estimate of 36 percent fewer (4,660 vs 7,270). Old bundles gave a fast first 30 s (937 to 975 food: ambers and drumsticks close to the start) and then 150 to 600 per 30 s; the map gave a steady 330 to 680 per 30 s (compare the per-30-second tables in the evidence README). Nothing wrong was seen with the map in Studio (no drops; 52 of 3,600 foods were moved a few studs by the ground check).
* The bot's old-bundle full-view run (6,558 points) is 90 percent of the offline greedy model (7,270): the offline model is a fair upper bound.

Not decided here (owner / LEAD): whether 12 per 500 stays, whether the amber / golden drumstick respawn should be slower. New row BD-1081 holds the pace question; BD-575 stays open for a **human** run.

## 3. Pattern and Colour Index in Studio (BD-1063)

Window 500 x 465 (the window the tools got; no phone, no 844 x 390). Build `3ced659f`, flag `PatternColourIndexEnabled` true, `GeneBoostEnabled` true.

| Check | Result | Picture |
| --- | --- | --- |
| Tabs Dinos / Patterns / Colours in the header, 44 px tall | PASS (127 x 44 each, X 64 x 44) | 300 |
| Fresh player: Patterns "0 / 8", Colours "0 / 9", grey "?" "???" cards, dim rarity border, pips, "Boost N of 5" / "No boost", "Not found yet" | PASS | 301, 302 |
| Last tab remembered (close, open again with C: Patterns / Colours returns) | PASS | 311, 313 |
| X closes | PASS | |
| Backdrop tap (3 px strip left of the card) closes | PASS | |
| C key twice closes | PASS (opens on press 1, closes on press 2) | |
| Escape | NOT TESTABLE (the tool's Escape never reaches the game, docs/192) | |
| Gamepad B | not tested (no gamepad) | |
| Hatch: "New pattern!" and "New colour!" ribbons on a first find | PASS | 304 |
| Hatch: already found = no ribbon | PASS | 306 |
| Hatch: only a new pattern = only "New pattern!" (next to the BIG tag) | PASS | 307 |
| Hatch: a mutation-only find keeps the old "NEW!" ribbon | PASS (as coded) | 308 |
| Hatch card line "Boost 1 of 5" (Green Freckles Raptor, Teal Patches Compy) | PASS | 305, 309 |
| Found card: colour tile, "Found on: ..." line, pips | PASS, but the "Found on" line is **cut after the first species** at this width | 311 |
| Colours tab: coloured circles | PASS | 313 |
| Red dot on the DINOS button after a new find; gone after opening a tab | PASS for the dot appearing and clearing; **DEFECT found and fixed**: the dot was 36 px and sat at the icon spot, not as a small corner dot (see below) | 310 |
| Dino Index card says the boost | PASS, wording "Boost: 1 of 5" (colon) vs the hatch card "Boost 1 of 5"; at 500 px it sits below the fold of the detail text | 315 |
| Server numbers for the equipped Teal Patches Compy (boost 1 pip) | PASS: 2.4 boost points, growth x1.024, walk x1.012; `Humanoid.WalkSpeed` 22.264 vs base 22 (= 22 x 1.012); character attribute `GeneBoostPoints` 2.4 | read by script |

**Defect fixed in this change:** `Bootstrap.client.luau` re-laid every child of a rail button (except `ActiveTab`) as the button's icon, so the Index dot became a 36 x 36 disc at the icon position instead of an 18 px dot in the top right corner. The rule now skips `IndexDot`. Verified in a Studio copy: dot `{1,-4},{0,4}`, 18 x 18. The default build is unchanged (the dot only exists with the flag on).

Open (new rows): the "Found on" line and the Boost line are cut at small widths; at 500 px the HUD rail buttons lie under the Index tabs and a click on the Patterns tab **also** pressed the rail EGGS button and closed the Index (the engine's hit test puts the tab on top, so this is probably the Studio click tool and not a real defect; check with a real mouse). Gamepad B and Escape stay untested. Equipped genes said `conditionId` "astra" (a 0.5 percent condition) while the card showed none: not verified, row opened.

## 4. Respawn by food kind (BD-1081): the same bot, before and after

STUDIO EVIDENCE, 2026-10-18, desktop Studio, one player, unpublished playtest build of main `38cdbb3c` (designed food map on, `FoodRespawnTiersEnabled` on), memory profile, no admin values, no forced chances. "Before" = the same session with the respawn table set to 8 s for every kind (`FoodRespawnByKind` is not frozen, so it can be changed from a Server `execute_luau`; this is exactly what the flag off does). "After" = the committed table (berry 8, fruit 12, egg 40, amber 120, golden drumstick 150 s). Single runs of 300 s, weather as it came. Estimates are the bot's own count (`Bot.summary()`); run 1 also has the server line `food_raw` 3,432, `eggs_food` 82, eggs 88 (the bot said 3,418).

| # | Walker | Respawn | food (est) | per minute | eggs | amber + drumstick share | points from a food eaten a second time |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | sees 60 studs, looks 0.4 s | table | 3,418 | 684 | 88 | 58 % | not counted (the run had no id in the eat lines) |
| docs/194 s2 run 4 | same | 8 s (old) | 4,262 | 852 | 108 | 66 % | not counted |
| 2 | sees 170 studs, no pause | table | **4,367** | 873 | 123 | 70 % | **65 (1.5 %)** |
| 3 | same | 8 s | **4,879** | 976 | 134 | 72 % | **497 (10 %)** |
| docs/194 s2 run 5 | same | 8 s (old) | 5,358 | 1,072 | 143 | 77 % | not counted |
| 4 | casual walker | 8 s | 963 | 193 | 26 | 32 % | 34 |
| 5 | casual walker | table | 1,523 | 305 | 41 | 45 % | 78 |
| 6 | casual walker | table | 1,230 | 246 | 40 | 42 % | not counted |

What the numbers say (plain words):

* **The loop is gone, the pace is not.** Points from a food the walker had already eaten once fell from 497 (10 percent) to 65 (1.5 percent). But the whole run only fell by about 10 percent (4,879 to 4,367; and by 18 to 20 percent against the older single runs of section 2). The bot still gets 4,400 food (6 to 7 times the docs/119 target of 600 to 700) because it walks to **each** of the map's about 108 ambers and about 36 golden drumsticks **once**: 44 ambers and 14 drumsticks were eaten for the first time in run 2, that is 3,040 points. Respawn time cannot touch that. The numbers that would: how many rich foods exist, what they give, or a per-run cap. A child does not walk to 44 ambers in 5 minutes, so this is a design question for the owner (new row BD-1093), not a bug.
* **The casual (slow) walker is not hurt.** Before 963, after 1,523 and 1,230. These three runs differ by chance (how many ambers the random walk met: 5 vs 10 vs 8), so the honest reading is "no sign of a drop, noise of about plus or minus 30 percent", not "the table helped". The 80 percent line of the brief (a slow walker must keep at least 80 percent) holds. This walker is faster than the round-3b script (570 food): the map puts food closer together (297 to 335 eats in 5 minutes). It is a stand-in for a casual player, **not a person**.
* Eggs (15 points, 40 s) still give 19 to 29 percent of the bot's points because there are about 250 of them; the table keeps them at 40 s on purpose.
* Not measured: a real child, a phone, the effect on the cluster relocation (the map keeps foods in place), servers with more than one player (each food is shared; slower respawn matters more there).

New in the bot (tools/studio): `start --casual --max-distance 90` (the casual walker above) and `summary` (points by kind, the amber + drumstick share, points from a second eat).
