# Index check and smart bot runs, 2026-10-18 (BD-1063, BD-1048, BD-575, BD-1076)

Label: **STUDIO EVIDENCE**, desktop Studio on the virtual monitor, unpublished copy, memory profile, test wallet. Written up in [docs/194](../../194-studio-test-bot-and-pace-numbers.md). Copies of the pictures are in `docs/evidence/review-2026-10-17/` (same file names).

* Studio 1: `python tools/build.py --profile playtest` on `origin/main` `3ced659f`, `playtest_freshness.py` said "up to date", the stamp on screen read `BUILD redesign-020`, `Config.Build` = `redesign-020 3ced659f`. Window 500 x 465 for the whole session (no phone-size 844 x 390 was possible, the tools cannot resize the window). `FoodLayerEnabled` is **not** in this build (old sector bundles).
* Studio 2 (throwaway, closed afterwards): PR #518 branch merged with main (`bee8bc25*`, flag on) plus the one-line dot fix. Window 500 x 465, then 296 x 464 after the runs. Both Studios were started with `python tools/monitor4.py launch studio ...` and only my own processes were stopped. The owner's `Place1` window was not running and was never touched.

## Pictures

| File | What |
| --- | --- |
| 300 | Dino Index, Dinos tab, tabs in the header |
| 301 | Patterns tab, 0 / 8, grey "?" cards, dim rarity borders, Boost pips, "Not found yet" |
| 302 | Colours tab, 0 / 9 |
| 303 | After a click on the Patterns tab: the Index is closed and the rail EGGS button was pressed (see BD-1083, probably the click tool) |
| 304 | Hatch card with both ribbons "New pattern!" and "New colour!" |
| 305, 309 | Hatch card "Boost 1 of 5" (Green Freckles Raptor, Teal Patches Compy) |
| 306 | Already found: no ribbon |
| 307 | BIG Compy with only "New pattern!" |
| 308 | Mutant (charged) find keeps the old "NEW!" ribbon |
| 310 | Red dot on the DINOS button after the hatches (the old disc, before the fix) |
| 311 | Patterns 6 / 8, found cards; the "Found on" line is cut after the first species |
| 312 | Patterns scrolled: Epic and Legendary still "Not found yet" |
| 313 | Colours 4 / 9 with coloured circles |
| 314, 315 | Dino species page and the Teal Patches Compy card (its detail says "Boost: 1 of 5") |
| 316 | Run Complete card at 296 x 464 after the bot's run on the food-map build |

## Bot runs (per 30 s, food points eaten, bot clock; telemetry lines are in docs/194)

Old bundles (`3ced659f`), sees 60 studs and pauses 0.4 s (run 2): 763, 321, 588, 187, 257, 318, 40, 510, 523, 575 = 4,082 (estimate; server 4,149), eggs at the end of each window 18, 27, 41, 45, 52, 59, 60, 72, 89, 113. Eaten: amber 44, berry 223, egg 25, fruit 81, golden drumstick 16. Events: target 121, skip 66, stuck 21, path 13.

Old bundles, sees 170 studs, no pause (run 3): 937, 995, 917, 598, 149, 593, 670, 509, 651, 519 = 6,538 (server 6,558), eggs 39, 69, 91, 106, 109, 123, 140, 150, 150, 150 (the cap). Eaten: amber 72, berry 294, egg 28, fruit 91, golden drumstick 31. The low window 120 to 150 s (149 food, 9 foods) in this run was not looked at in the log, so its cause is not known (probably a stuck spell). In run 2 the low windows 180 to 210 s (40 food) and 90 to 120 s are the bot stuck at the rock pocket near (-380, 234) (three foods and two paths, about 45 seconds, lines 110 to 130 and 174 to 197 of the log); the area rule (every food within 15 studs ignored for 100 s) was added after run 2.

Designed map (`bee8bc25*`), 60 studs and 0.4 s (run 4): 429, 530, 409, 427, 463, 379, 335, 386, 402, 494 = 4,255 (server 4,262), eggs 10, 23, 32, 43, 54, 63, 71, 80, 92, 108. Eaten: amber 38, berry 154, egg 71, fruit 59, golden drumstick 15. Events: target 136, skip 72, stuck 9, path 8.

Designed map, 170 studs, no pause (run 5): 597, 495, 484, 555, 556, 678, 384, 616, 500, 486 = 5,357 (server 5,358), eggs 20, 36, 53, 66, 79, 96, 106, 120, 132, 143. Eaten: amber 51, berry 154, egg 59, fruit 52, golden drumstick 26. During this run a weather event "aurora" was started through the admin remote by the player `znyprs` (server log: "started weather aurora for 180s", then "stopped the weather"); the bot never calls any admin remote, so someone else clicked in that window. Weather changes eggs (+11 percent here) but not `food_raw`.

First 70 non-eat lines of run 2 (the decision log, one line per event):

```
   0.6  target  amber@(18,69) 50pt d=43.2 score=21.12  (2nd: egg@(-1,41) 15pt d=11.9 score=15.64)  walkSpeed 22
   2.7  skip    amber@(18,69) reached but not eaten, ignored
   3.2  target  amber@(18,99) 50pt d=31.1 score=27.58  (2nd: amber@(50,100) 50pt d=45.2 score=20.65)  walkSpeed 22
   5.3  target  amber@(50,100) 50pt d=31.3 score=28.21  (2nd: golden_drumstick@(4,138) 60pt d=41.7 score=27.04)
   7.4  target  golden_drumstick@(56,144) 60pt d=44.4 score=23.43  (2nd: golden_drumstick@(7,141) 60pt d=58.8 score=19.62)
  13.3  target  golden_drumstick@(7,141) 60pt d=4.9 score=106.00  (2nd: golden_drumstick@(4,138) 60pt d=8.4 score=84.47)
  15.1  target  fruit@(-12,149) 4pt d=19.7 score=3.05
 110.0  stuck   moved 9.6 studs in 1.4 s on the way to golden_drumstick@(-378,234)
 110.1  path    2 waypoints to golden_drumstick@(-378,234)
 115.2  skip    golden_drumstick@(-378,234) stuck again after a path, ignored
278.6  target  golden_drumstick@(-331,368) 60pt d=7.0 score=77.72   <- the same spot again at 288.7 s (8 s respawn)
```

(The full log of a run stays in Studio memory: `shared.PlayerBot.log`; read it with `python tools/studio/run_player_bot.py log --from 1 --to 700`.)
