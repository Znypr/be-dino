# Studio round 9 (2026-10-19): window chrome, coloured words, rare-find banner, stall bubble, hatch tags

Playtest build of `origin/main` `71fec69f` (on screen: **BUILD redesign-020 71fec69f**; `playtest_freshness.py`: up to date). Report: [docs/215](../../215-studio-round9-chrome-words-banner-bubble-tags.md). Copies of every picture are in `docs/evidence/review-2026-10-17/` with the same number and the prefix `-studio-r9-`.

Window sizes (`CurrentCamera.ViewportSize`): **1156 x 793** first (pictures 457 to 478), then 296 x 304 by itself (no pictures), then **516 x 481** after `monitor4.py place --maximize` (pictures 479 to 517). The rare-find banner pictures (513 to 516) come from a test call of the server remote, not from a real hatch by another player.

| # | Picture (file name) | Verdict |
| --- | --- | --- |
| 457 | tutorial 1156 | PASS: outlined title, red square X, build stamp 71fec69f |
| 458 | home 1156 | PASS: Admin top left, rail with words |
| 459 | Index Dinos tab 1156 | PASS: tab titles 24 px, X |
| 460 | Nests bubble 1156 | PASS: screen frame, clear of rail |
| 461 | Eggs window 1156 | PASS |
| 462 | Fuse bubble 1156 | PASS |
| 463 | Fusion menu 1156 | PASS for tab names, Admin and Tell us! hidden; X is 60 x 44 (BD-1146) |
| 464, 465 | Shop bubble, shop landing 1156 | PASS: "You have 1" |
| 466, 467 | Auras, Trails 1156 | PASS: rarity chips filled and whole, Common chip darker grey |
| 468, 469 | Eggs tab, Egg Chances 1156 | PASS (no tier words on the chances page) |
| 470, 471 | Potions bubble, potion shop 1156 | PASS; Common grey potion names faint (BD-1147) |
| 472, 473 | Dinos bubble, Heart bubble 1156 | PASS: Heart says "Show off" |
| 474 to 477 | Settings Sound, Look, Controls, Help 1156 | PASS |
| 478 | run start 1156 | PASS: only Potions and Settings in a run |
| 479 | run 516 | PASS: Admin beside HOME, clear |
| 480 | Go home screen 516 | PASS: title 32 px x 0.7, X 48 x 48 |
| 481 | Run Complete 516 | PASS: 48 eggs, +93 Crystals, +2 nests, toast below the buttons |
| 482 | Eggs screen 516 | PASS: header clear of the nests |
| 483 | AUTO button | PASS: opens Settings on Help |
| 484 | Help, AUTO state 516 | words white, not coloured (BD-1147) |
| 485 | home 516 | PASS: Tell us!, Admin, Explore clear; "Level 2!" toast lies over the weather plate for a moment |
| 486 | Eggs auto-open line 516 | PASS: "Common" grey, "Uncommon" green |
| 487 | own-hatch banner 516 | DEFECT: covers the window title and X (BD-1148) |
| 488, 490, 493 | reveal with tags 516 | **DEFECT**: tag words are TextSize 100 in 15 px boxes, cut to B..., Sk..., N... (BD-1145) |
| 489 | hatching 516 | DEFECT: "Cream" cut by the COMMON chip (BD-1145) |
| 491, 492 | natural Rainbow egg 516 | title "Rainbow egg! Always shown" whole in the header (better); tags still broken; class badge sits left of the name (ok) |
| 493 | natural BIG Raptor 516 | DEFECT as 488 |
| 494 | batch summary 516 | title and X ok; tier words white (BD-1147) |
| 495, 496 | Index Dinos, My dinos details 516 | BD-1134 still there (empty bottom third, hidden Species and Boost lines, BLOOD M chips cut) |
| 497, 498 | Index Patterns, Colours 516 | PASS: tier words coloured (Common grey, Uncommon green, Rare blue, Epic purple) |
| 499, 501, 505 | Fuse, Shop, Potions bubble 516 | PASS: clear of rail, weather, Tell us!, Admin, Explore |
| 500 | Fusion 516 | tab names whole (BD-1103 PASS); DEFECT: "Pu t", odds line cut, X 62 x 45 (BD-1146) |
| 502 to 504 | Shop pages 516 | PASS |
| 506 to 508 | Potion shop, confirm, Done toast 516 | PASS: toast along the bottom, clear of X and tabs |
| 509 to 511 | Settings 516 | PASS: Look and Controls rows spaced (BD-1132); tab row touches the header |
| 512 | Goals sheet 516 | PASS: opens under the rail (BD-1108); DEFECT: the Potions bubble covers its left text |
| 513 to 516 | rare-find banner, TEST CALL | PASS: huge outlined "RARE FIND!", one sentence, rarity word coloured (Legendary gold, Epic purple), no panel, no name; secret says "A secret dino was found!"; gone after about 4 s |
| 517 | home 516 | weather title had faded before the picture: not captured |

Close paths tried: X (Tutorial, Index, Fusion, Food guide, Settings, Go home), tap outside (Index at 1156 and 516), C twice, E at the stall (Nests, Potions, Shop), B twice. **Escape does nothing through the key tool** (tested in the Tutorial and the Index), so it is not judged. G did nothing visible.
Console (`get_console_output`): no error from game scripts. Only Studio's own UIBlox warning "FoundationProvider not found" (repeated) and "The execute_luau changed camera type" lines.
