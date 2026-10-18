# Studio round 5: verification of what merged on 2026-10-18 (docs/197)

Label: **STUDIO EVIDENCE**. Playtest build of `origin/main` `c677239c`, the label on screen read **BUILD redesign-020 c677239c** (`playtest_freshness.py`: up to date). One player, unpublished copy, memory profile, in-game crystals only. Window: the viewport was **500 x 465** for the whole session (Studio was placed on the virtual monitor by `monitor4.py`; the tools have no resize call). Copies of the pictures are in `docs/evidence/review-2026-10-17/` (same file names, numbers 330 to 357; numbers above 316 were chosen to stay clear of pictures other open PRs add).

Tool quirk learned: the mouse tool takes **GUI coordinates** (the position `AbsolutePosition` gives), not the numbers you read off a screenshot (the picture includes a 58 px top inset). My first clicks missed their buttons and landed on the dark backdrop, which closes menus. All clicks after that used the GUI numbers.

| File | What it shows | Verdict |
| --- | --- | --- |
| 330 | Home HUD | fine |
| 331 | Run HUD: the Admin button (QA only) sits on HOME, the hint text lies over the weather card | small window, see BD-1097 |
| 332 | "Golden Drumstick!" toast covers the rail icons | small window, BD-1097 |
| 333 | Run Complete card (32 eggs earlier, 20 here) | fine |
| 334 | Eggs screen: five nests, "Egg 1 of 20", OPEN EGG whole | PASS at 500 x 465 on main |
| 356 | Hatch start: steel bucket with blue paint, one flat egg | PASS (bucket small but reads) |
| 335 | Reveal card: "Egg 1 of 20" in the header, dino head visible, class chip "Ground" over the name "Raptor" | layout PASS, chip over name = BD-1097 |
| 336 | Ribbons "New pattern!" / "New colour!" and the "Blue / Dots / Boost 1 of 5" line | PASS |
| 337 | Teal bucket, chip "Teal RARE" with a teal square | PASS (chip colour = 22,170,151 = the table value) |
| 338 | Same egg, same size, painted teal | PASS (one egg size) |
| 339 | Second chip (blue) cut by the right window edge | small window, BD-1097 |
| 340 | Reveal of the teal Raptor ("Teal / Plain / Boost 1 of 5") | PASS |
| 341 | Cream chip with a cream square, pattern chip "Freckles" | PASS |
| 342 | BIG ribbon, tag "BIG! Skip stops here" left of the dino | PASS |
| 343 | Skip summary: a toast lies over COLLECTION and DONE | BD-1097 |
| 344 | Red dot on the DINOS button (18 px, corner) | PASS |
| 345 | Dino Index, Dinos tab: no class icon | BD-1099 (question) |
| 346 | My dinos, Raptor page: no class icon | BD-1099 |
| 347, 348 | Goals and Tasks panels over each other | defect BD-1095 |
| 349 | Starter goal "Find 3 patterns" with CLAIM | PASS |
| 350 | Tap on the Patterns tab opened the Eggs screen instead (rail button under the tab) | defect BD-1083 (confirmed real) |
| 351 | Colours tab 6 / 9, pips, boost lines | PASS |
| 352 | Colour detail box (Teal: Rare, Boost 2 of 5, accent hint, Found on) | PASS |
| 353 | After a tap beside the box the whole Index is gone | question, see below |
| 354 | My dinos page with a Plain Raptor selected | fine |
| 355 | Run HUD on grass, "You found an egg!" | fine |
| 357 | Player stuck in Ending after the run (SAVING...) | BD-1096 |

## Verdicts

1. **Hatch polish: PASS** (Rainbow and Astra not seen in 19 eggs; not forced). Steel bucket with the real colour, chip square = named colour (teal 22,170,151, blue 36,132,211 read from the GUI), one egg size (about 105 px wide in the flat and the 3D stage), chunky chips, "Egg N of M" in the header, head visible, "BIG! Skip stops here" tag. The bucket is small at 500 px. Not judged: motion, sound.
2. **Small windows: BLOCKED**. PR #526 was open, so the build had no BD-1067 fix. Only the "before" at 500 x 465 was seen (no resize tool). Eggs screen header and OPEN EGG are fine there; other overlaps are in BD-1097.
3. **Class icons: PARTIAL**. The icon shows on the reveal card (335 etc.). The code builds it only there, so Dino Index and My dinos show none (BD-1099). The console had no asset warning (only the UIBlox noise).
4. **Starter goals: PASS**. After Hatch 3 eggs: Find 3 patterns, Find 3 colours, Find all Common patterns, each CLAIM paid once (crystals 1,000,174 to 1,000,189 and on to 1,000,224). Numbers match the Index (colours 6 / 9; patterns 4 found = the four pattern names in My dinos). The Patterns tab itself could not be tapped (BD-1083). Detail box: X closes. A tap beside the box closed the whole Index.
5. **Food map and respawn: PASS** with notes. 3,600 foods; 8 x 8 cells hold 35 to 73 foods (mean 56, sd 7). None float (3,549 sit 0 to 2 studs above the ground; the other 51 have a collider box above them, see the list). 60 overlap a collider box (below). Berry came back after 8.1 s. The amber stayed hidden at 69 s and 125 s and was seen again about 235 s after the first pick-up, which is two 120 s cycles (I was standing on it, so the first return at 120 s was eaten at once). Config on the server: berry 8, fruit 12, egg 40, amber 120, golden drumstick 150.
6. **Gene boost: PASS**. Equipped Plain Raptor (Teal main colour, 2 pips, blue accent, blank pattern): `GeneBoostPoints` 1.4 (2 x 0.7), `GrowthMultiplier` 1.014 (+0.5 percent a point), `Humanoid.WalkSpeed` 22.154 (22 x 1.007, half the growth bonus). Matches the earlier check.

## Foods that overlap a world collider box (60 of 3,600; x, y, z)

egg -288,33,-351 | berry -292,32,-348 | amber -288,32.8,-347 | berry -320,29.5,-308 | berry -310,40.5,221 | berry -254,63.5,-245 | fruit -211,66,-224 | berry -224,34.5,369 | berry -149,32.9,392 | berry -75,14.3,-265 | berry -43,12.1,-206 | fruit -67,4.9,225 | berry -68,4.6,228 | egg -30,10.2,-137 | berry -37,6.8,-112 | berry -35,6.5,-110 | berry -38,4.5,-91 | berry 76,21.8,-188 | berry 79,21.9,-186 | fruit 76,21.1,-185 | golden_drumstick 99,23.6,-297 | berry 91,31.1,381 | berry 147,46.5,-271 | berry 136,28.8,-109 | berry 139,28.9,-108 | fruit 122,16.7,149 | fruit 157,36,206 | fruit 144,27.6,343 | fruit 170,16.1,116 | berry 216,45.3,-330 | berry 214,45.6,-328 | amber 225,82.8,-202 | berry 229,55.4,197 | berry 234,48.2,290 | berry 238,48.5,289 | fruit 209,44.9,291 | berry 233,41,367 | berry 233,40.8,370 | berry 255,70.2,-258 | berry 254,78.6,-191 | berry 249,62.4,-138 | berry 247,62.2,-137 | berry 250,60.9,-135 | fruit 259,45.1,-107 | berry 262,43.2,-106 | berry 258,42.9,-103 | berry 261,42.3,-102 | berry 281,14.6,-12 | berry 280,56.5,240 | fruit 276,57,244 | berry 254,55,266 | egg 312,20.4,3 | berry 352,34.9,-330 | fruit 348,34.8,-329 | berry 337,51.7,-262 | berry 339,52.2,-259 | berry 362,52.1,-179 | berry 351,29.4,348 | egg 389,51.1,-172 | berry 385,35.7,70

The colliders are boxes, so a few of these may only touch a box corner. Method: `GetPartBoundsInBox` at 90 percent of each food's size, collider parts only (Food folder, characters and NPCs excluded); floating test: a ray from 40 studs above each food down to the first part or terrain.
