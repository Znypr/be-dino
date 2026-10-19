# Studio round 10 (2026-10-19): hatch tags, rail with words, weather title, Calm motion

Playtest build of `origin/main` `89960c76` (on screen: **BUILD redesign-020 89960c76**; `playtest_freshness.py`: up to date). Window: **516 x 481**. Report: [docs/217](../../217-studio-round10-hatch-tags-rail-words-weather.md). Copies of every picture are in `docs/evidence/review-2026-10-17/` with the same file name.

| # | Picture (file name after the number) | Verdict |
| --- | --- | --- |
| 540 | tutorial-516x481 | PASS: title, red square X |
| 541 | home-rail-with-words-516x481 | PASS: DINOS, EGGS, FUSION, SHOP, POTIONS (14 px) in 3 x 2 plus the shield gear |
| 542, 543 | key-C-dinos-index, key-B-eggs | PASS: C and B open the screens |
| 544 | key-G-at-home-nothing | G does nothing (stall key is E with the bubble) |
| 545 | run-rail-potions-gear | PASS: only Potions and the gear in a run |
| 546 | run-complete-45-eggs | PASS |
| 547 | hatching-chips-teal-rare-cream-common | DEFECT: "Cream" lies under the COMMON chip |
| 548, 549, 551 | reveal ... new-ribbons-N-cut | **FAIL**: New pattern! / New colour! ribbons show "N..." in huge letters (TextSize 100) |
| 550 | splat-next-egg-button-touches-line | small: NEXT EGG touches the yellow line |
| 552 | hatching-chip-Green-cut-by-UNCOMMON | DEFECT: "Gree" + UNCOMMON |
| 553 | reveal-natural-Rainbow-tag-huge-cut | **FAIL**: natural Rainbow tag "Ra..." over "Sk..." |
| 554, 555 | reveal-natural-BIG ... | **FAIL**: "BIG!" over "Sk...", purple ribbon only "..." |
| 556, 568 | auto-opened-summary ... white-words | DEFECT: summary line plain white (BD-1147) |
| 557 | home-objective-pill-title-cut-to-dots | DEFECT: pill title only "..." |
| 558, 573 | toast ... over-weather-plate | small: toasts over the weather plate |
| 559 | fuse-stall-bubble-E-Open | PASS: bubble clear of rail; key E |
| 560 | fusion-menu-X-60x44-Put-wraps-odds-cut | DEFECT: X 60 x 44, "Pu t", odds line cut (BD-1146) |
| 561 | goals-sheet-covered-by-fuse-bubble | DEFECT: bubble covers Goals text (BD-1148) |
| 562, 570 | weather ... plate | PASS: plate readable (Rain, Volcanic Bloom) |
| 563 | gear-opens-settings-sound | PASS |
| 564 | settings-look-calm-motion-on | PASS: Calm motion ON |
| 565, 566, 567 | calm-motion-reveal ... | **FAIL**: Dewdrop, Rainbow, BIG tags broken with Calm motion too |
| 569, 574 | run2 / run3 run-complete | PASS (38 and 76 eggs) |
| 571 | run-goals-line-Done-Claim-in-cut | DEFECT: "Done! Claim in..." cut |
| 572 | weather-title-BLIZZARD-in-run | PASS: 40 px title, 17 px line; lies over the SIZE bar for 3 s |
| 573 | rail-Dinos-click-guide | rail click starts the walking guide |

Numbers read live in the CLIENT datamodel: every hatch tag label TextSize **100** (StopTag 106 x 15 px, Ribbon 88 to 95 x 23 px), label attributes CmBaseText 100 and CmText 229112335 (cause: `ModalCompact.floorPass` divides by a UIScale of 0). Rail words 14 px. Fusion X 60 x 44. Weather title in a run 309 x 40 (text 175 x 40), sub line 17 px; soft line at home 103 x 16 px (no picture).

Not seen in 159 eggs: Blood Moon and Shiny tags (not forced). Not reached: 848 x 423, 667 x 339, 1156 x 841, phone, gamepad, Escape.
