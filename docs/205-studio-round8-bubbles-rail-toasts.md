# 205 Studio round 8: stall bubble, rail in a run, toasts, small windows, food vs colliders (BD-1018, 1105, 1106, 1107, 1108, 1112)

Label: **STUDIO EVIDENCE**, written 2026-10-19 by the Studio QA helper. Playtest build of `origin/main` `1f78c38b` (screen label **BUILD redesign-020 1f78c38b**, `playtest_freshness.py`: up to date), in-game crystals only, nothing published, nothing forced, no Robux, keyboard and mouse only (no gamepad, no phone). Pictures 421 to 456 in `docs/evidence/review-2026-10-17/`; list and verdicts in [evidence/2026-10-18-studio-r8/README.md](evidence/2026-10-18-studio-r8/README.md).

## 1. Viewport sizes

| When | `CurrentCamera.ViewportSize` |
| --- | --- |
| Start (Studio maximised on the 1280 x 720 virtual monitor) | **516 x 481** (same as docs/200) |
| About 25 minutes in the window was on a 1080p screen by itself | **1156 x 841** (pictures 423 to 433) |
| Later, not maximised on the virtual monitor | 296 x 472 (no pictures; `monitor4.py place --maximize` fixed it) |
| After that | **516 x 481** (pictures 434 to 456) |

Nobody was running `monitor4 watch`; as in docs/200 the window changed size without a call from this task.

## 2. Pass or fail (plain words)

| Item | Verdict |
| --- | --- |
| 1 Stall bubble (BD-1018) | **PASS on desktop with the keyboard, one defect in a small window.** Nests, Potions, Fuse, Shop, Dinos and the Heart: the bubble shows only inside 10 studs (Heart 9), one bubble at a time (the count of live bubbles was 1 everywhere), "name / warm line / E Open" fits (pictures 423 to 432), nothing opens by walking. One E opened the window (checked on Nests, Shop, Dinos, Heart; Potions and Fuse press not repeated), E again closed it (Nests, Shop, Dinos; once the second E on Dinos did not close the Index, three repeats all closed it). While a window is open the bubble does not exist, it is back about 0.3 s after closing. Soft fade: in 0.15 s (alpha 1.0, 0.32, 0.01) and out in about 0.15 s; with Calm motion ON it is instant (alpha 0 at once). E at home does not leap (the dino did not move, LEAP stayed ready); E in a run leaps (LEAP 1 min cooldown, dino jumped). The Heart bubble plus E steps the dino onto the pedestal. **At 516 x 481 the bubble is under the rail and the weather plate** (421): BD-1128. Not done: 640 x 360 phone view, real phone, gamepad (X). |
| 2 Rail in a run (BD-1105) | **PASS.** In a run only Potions and Settings, side by side with no gap, no MENU chip (433, 435); at home all six (422). Five enter and leave cycles (one at 1156 x 841, four at 516 x 481): no stuck state. Logged per frame: at each run end the two buttons first jump to their home slots and the other four appear 0.06 to 0.13 s later (a very short jump, behind the Run Complete card). |
| 3 Shop tabs, toasts, Calm motion, Fusion, class icons, wording (BD-1106) | **PARTIAL PASS.** Shop Auras, Trails, Eggs tabs: PASS at 1156 x 841 (427 to 429); not photographed at 516. Toasts: with no menu open the toast sits below the rail and clear (439); with the Potion Shop open ONE slim card along the bottom, never over X, the tab row or the first row (437), it lies slightly over the USE row. Calm motion: OFF the toast slides 8 px in 0.07 s, ON it appears in place. **Fusion tab names are still cut at 516 (EMERAL, DIAMON, 440)** and Admin plus Tell us! lie over the Fusion menu. Class icon: My dinos details icon plus the word (456), Index cards icon only (455). "Found on Raptor" on one line (454), "Boost N of 5" (442, 454). |
| 4 Rainbow reveal and Goals sheet (BD-1107, 1108) | **Both defects CONFIRMED.** A Rainbow egg came naturally (egg 16 of 17, a 17-egg run, auto-open for Common and Uncommon): the ribbon "Rainbow egg!" is cut at the left edge, "Skip stops here" lies on it, the title touches "Egg 16 of 17" (451). BIG and Dewdrop reveals show the same chip stack (449, 450). The open Goals sheet hides the Settings rail button and parts of Fusion and Potions (443). |
| 5 Foods vs colliders (BD-1112) | **PASS.** FoodCount 3600, FoodLayerPlanned 3600, **FoodLayerRelocated 5, FoodLayerDropped 0**. Method below: **0 of 3600 foods overlap a collider box.** 177 foods have a collider box within 1.5 studs (box test, 3D), which the offline model counts differently (see below). |

### Method for item 5 (execute_luau, Client datamodel, loops yield)

1. Colliders: every `BasePart` in `workspace` whose name ends in `Collider` or is `ArchPillar`, `ArchTop`, `JumpStone` (951 parts, the rock, boulder, tree, landmark colliders of the WorldKit).
2. `OverlapParams` with `FilterType = Include` on those 951 parts.
3. For each of the 3,600 parts in `workspace.Food`: `workspace:GetPartBoundsInBox(food.CFrame, food.Size * 0.9, params)`; a hit means overlap. 0 hits.
4. Closer test: the same with `food.Size + (3, 3, 3)` (1.5 studs on every side) and no hit in step 3: 177 foods. The tally shows mostly boulder colliders (`world_boulder_*Collider`) with the food height inside the collider's height. The offline model (`tools/world_colliders.py`) says 0 closer than 1.5: it measures a flat distance and uses its own colliders, so the numbers differ by method; nothing is inside a collider.

## 3. Defect table

| # | Defect | Picture | Severity | Row | Suggested fix |
| --- | --- | --- | --- | --- | --- |
| 1 | Stall bubble hidden behind the HUD rail and weather plate at 516 x 481 | 421 | P2 | BD-1128 (new) | keep the bubble clear of the HUD (clamp to a free screen rect) or draw it in a ScreenGui above the HUD |
| 2 | Heart bubble button says "Open" for Show off; Trails tile "1 yours"; "Sold out. Back" cut | 432, 426, 437 | P3 | BD-1129 (new) | "Show off", "You own 1", shorter sold-out line |
| 3 | Tell us! and Admin cover Explore, HOME and the Fusion menu at 516 | 434, 435, 440 | P2 | BD-1130 (new) | move Tell us! to a free corner, hide Admin and Tell us! while a menu is open |
| 4 | Fusion tabs EMERAL / DIAMON cut; "Put", "You need 6 Base dinos of one kind. You" cut; Fill and Clear overlap | 440 | P2 | BD-1131 (new) | same floors as the shop pages; short tab words |
| 5 | Settings Look rows crowd each other; weather title over the Potions button; Index DEWDROP chip cut, badge without word, half the panel empty; My dinos second Species line hidden; AUTO opens the last Settings tab, not Help | 438, 447, 455, 441, 456, 448 | P3 | BD-1132 (new) | lay out with the floors, open Help directly |
| 6 | Rainbow ribbon cut, chips overlap, class chip over name | 449 to 451 | P2 | BD-1107, BD-1097 (notes) | ribbon inside the card, chips on separate lines |
| 7 | Open Goals sheet over the Settings button | 443 | P3 | BD-1108 (note) | open Goals below the rail |
| 8 | Rail jumps for about 0.1 s at run end | log | P3 | BD-1105 (note) | hide the two buttons until the four are ready |

Looks, judged against docs/114 section 4 and the vibe words (calm, bubbly): at 1156 x 841 the bubble reads calm and friendly: a dark soft card, a small gold title, one warm line and a wide yellow button with a dark key chip; the words fit and nothing is cut. It is small compared with the stall sign (248 x 116 px); that is fine for calm. It is not "bubbly" in shape (a square card with small corners, not a round speech bubble) and has no tail pointing to the stall: a suggestion only.

## 4. Not verified, and tool notes

* Phone: 640 x 360 view, real phone, "Tap to open" text; gamepad X glyph; Reduce Motion in the real operating system (only the Calm motion setting was tested). The other games' prompt pictures of BD-1018 were not taken.
* The Studio screenshot tool does not draw billboards (same as docs/141): the bubble pictures are an exact copy in a temporary ScreenGui under the HUD (see the README). A real picture of the billboard on a phone or a clean Studio capture is still wanted.
* Not reached: Calm motion with the Eggs screen and a toast over the Explore button (BD-1102 earlier), 848 x 423 and 667 x 375, a Legendary reveal, the Fusion wheel.
* Lessons: the mouse tool takes the GUI coordinates (`AbsolutePosition`, the screenshot y minus about 57); a click on HOME within about 2.5 s of a run start did nothing once; a long polling loop in `execute_luau` (110 s) times out the request, keep loops under 30 s per call; a hand-written bot must skip foods whose `Transparency` is 1 (eaten) or it stands still.
