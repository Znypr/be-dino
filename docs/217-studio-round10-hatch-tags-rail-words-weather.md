# 217 Studio round 10: hatch tags (BD-1145 still broken, real cause found), rail with words, weather title, Calm motion

Label: **STUDIO EVIDENCE**, written 2026-10-19 by the Studio QA helper. Playtest build of `origin/main` `89960c76` (screen label **BUILD redesign-020 89960c76**, `playtest_freshness.py`: up to date). It holds #554 (HUD rail with words), #556 (hatch tag size cap, BD-1145) and #557 (art batch 2, no game change). In-game crystals only, nothing published, no chance or flag forced (the test walker only walks to food and fires the same start and end remotes as Explore and Go home). Pictures 540 to 574 in `docs/evidence/review-2026-10-17/` (file names contain `-r10-`), list and verdicts in [evidence/2026-10-19-studio-r10/README.md](evidence/2026-10-19-studio-r10/README.md).

## 1. Window size

**516 x 481** (`CurrentCamera.ViewportSize`) after `monitor4.py launch studio` and `place --maximize`: the small (phone-layout) window. 848 x 423, 667 x 339 and 1156 x 841 were not reachable (no resize tool; nothing was denied, so nothing was retried).

## 2. Pass or fail

| Item | Verdict |
| --- | --- |
| 1 Hatch tags (BD-1145, P1) | **FAIL. #556 did not fix it.** 159 eggs in three runs (45, 38, 76). Natural **Rainbow** (several times), **BIG** (3 times), **Dewdrop** mutation, **New pattern! / New colour!** and a first-find **NEW!** all came; **Blood Moon and Shiny: not seen** (not forced). Every tag word is still **TextSize 100** in a label 106 x 15 px (Ribbon 94 x 23), cut to "Ra...", "Sk...", "BIG!" over "Sk...", "N...", "D..." (pictures 548 to 555, 565 to 567). Numbers read live on the CLIENT: StopTag "Rainbow egg!" ts=100 106 x 15, "Skip stops here" ts=100 106 x 15, Ribbon "New pattern!" ts=100 95 x 23, "New colour!" ts=100 88 x 23, "BIG" ts=100, "DEWDROP" ts=100 94 x 23. Same with Calm motion on. The colour chips in the egg wobble are still cut by the rarity chip: **"Cream" + COMMON, "Gree" + UNCOMMON** (547, 552). A chip whose rarity word fits ("Clay COMMON", "Teal RARE", "Blue COMMON") is whole. Rainbow title is in the header again and the card text (name, Common 36.4% of eggs, trait line) is fine. |
| 2 Rail with words (BD-1143 / BD-1116) | **PASS at 516 x 481** (phone layout). Home: **DINOS, EGGS, FUSION, SHOP, POTIONS in a 3 x 2 grid plus the shield gear** in the sixth cell (541). Word size read live: **14 px** (phone layout floor in docs/212; the 16 px desktop words could not be tried at this window). In a run only **Potions and the gear** (545, 571). Keys **C** and **B** open and close Dinos and Eggs (542, 543). The gear opens Settings (563). **G does nothing**: with the stall bubble on, the stall key is **E** (559; `HubWalkUpRules.PromptKeyBubble`), G is only the old flag-off key; docs/212 and the code comment still say G. A rail click at home starts the walking guide (Follow the glow, 573), it does not open the screen. Nothing overlaps the egg plate, Crystals, toasts, stall bubble, open panels, Tell us! or Admin; the small objectives pill sits only 2 px under the rail. Not checked: other window sizes, the fallback under 500 px, the first-run MENU chip. |
| 3 Fusion X, white rarity words, banner and bubble | **Fusion X (BD-1146): still there**, 60 x 44 (not a square), "Put 0 of 6" wraps to "Pu t", the odds line is cut (560). **BD-1147: still there**: the Auto-opened summary line "2 Rare \| 16 Common \| 15 eggs did not hatch" is plain white, RichText off (556, 568); the Best line under it is coloured. Common grey on dark: the Common word in the hatch odds line is still dim on the teal bar. **BD-1148**: the Fuse stall bubble covers the left text of the Goals sheet, as the Potions bubble did (561). The own-hatch banner over the title and X and the rare-find banner over the rail: not seen this round. |
| 4 Round 9 leftovers (BD-1149) | **Weather title: seen.** In a run the big card "BLIZZARD!" with "Special eggs can drop!" (572): text 40 px and 17 px, readable, lies over the SIZE bar for about 3 s. At home in the cave the soft line "Volcanic Bloom" was measured (text 103 x 16 px, 1.8 s, under the weather plate); no picture because screen capture timed out at the moment the weather started (twice). **Calm motion** (Settings, Look): ON works, the tags stay as broken (565 to 567). **G key**: nothing (see 2). Not reached: 848 x 423, 667 x 339, phone, gamepad, Escape, a natural rare banner from a second player, Shiny and Blood Moon hatch. |

## 3. Cause of BD-1145 (read live in the CLIENT datamodel)

The tag label attributes after a Rainbow reveal: `CmBaseText = 100`, `CmText = 229112335`. `ModalCompact.floorPass` (src/client/ModalCompact.luau) raises every label in the body to 14 px on screen: `PhoneScale.floorSize(base, ancestorScale(d, panel) * scalePanel, 14)` = `ceil(14 / scale)`. `ancestorScale` multiplies **every UIScale between the label and the panel**, and a hatch ribbon or stop tag is created with its own `UIScale` at 0 and pops in. With a scale near 0 the floor is huge (14 / 6e-8), the engine clamps TextSize to 100, and `designValue` then reads the clamped 100 as the new design size, so it never comes back. The #556 change (`TagFit.MinScale`) only guards `HatchTagLayout.plan`: I ran `HatchTagLayout.plan` in the client with scales 1, 0.59, 0.3, 0.14, 0.05 and 0, and it answers 26 or 28 every time, so the layout is right and the floor pass wrecks it afterwards.

Suggested fix (row BD-1153): in `ancestorScale` skip any UIScale under 0.5 (the same rule as `TagFit.MinScale`), clamp `want` to a sane maximum, never store a clamped value as the design size, and add a UIScale-0 case to the text-floor smoke (the mock has no pop-in, which is why the offline check was green).

## 4. Defects

| # | Defect | Picture | Severity | Row |
| --- | --- | --- | --- | --- |
| 1 | Hatch tag words TextSize 100, cut to Ra..., Sk..., N..., D... (cause in section 3) | 548 to 555, 565 to 567 | **P1** | BD-1153 (BD-1145) |
| 2 | Colour chip word cut by the rarity chip (Cream, Gree) | 547, 552 | P2 | BD-1154 |
| 3 | Fusion X 60 x 44, Pu t, odds line cut | 560 | P3 | BD-1146 |
| 4 | Auto-opened summary line white | 556, 568 | P3 | BD-1147 |
| 5 | Fuse (and Potions) bubble covers Goals text | 561 | P3 | BD-1148 |
| 6 | Objectives pill title is only "..." at home; Goals line "Done! Claim in..." in a run | 557, 571 | P3 | BD-1155 |
| 7 | Toasts over the weather plate; weather card over the SIZE bar; NEXT EGG button touches its line; stall key doc says G, bubble says E | 558, 573, 572, 550, 559 | P3 | BD-1156 |

## 5. Not verified

Shiny and Blood Moon tags (none in 159 eggs), 848 x 423, 667 x 339, 1156 x 841, phone, gamepad, Escape, the rail fallback under 500 px, 16 px desktop rail words, the MENU chip, a rare-find banner from another player, Dewdrop reveal art. Looks judged against docs/114 section 4 and docs/72: the rail with words is clear and calm; the hatch tags are ugly and unreadable.

Tool notes: single clicks need move near, wait, move onto the button, wait, down, wait, up (worked every time). `screen_capture` timed out twice exactly when a weather started (particles); a retry a few seconds later worked. Studio showed no script errors in the console (only the Studio UIBlox "FoundationProvider not found" warning). The test Studio was closed at the end (a save prompt on the throwaway build was discarded by ending its process).
