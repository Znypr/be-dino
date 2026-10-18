# 200 Studio round 7: the fixes of 2026-10-18 re-checked, and what viewport size we can really get (BD-995)

Label: **STUDIO EVIDENCE**, written 2026-10-18 by the Studio QA helper. Playtest build of `origin/main` `6114e456` (screen label **BUILD redesign-020 6114e456**, `playtest_freshness.py`: up to date), in-game crystals only, nothing published, nothing forced, no Robux. Pictures 380 to 420 in `docs/evidence/review-2026-10-17/`; list and verdicts in [evidence/2026-10-18-studio-r7/README.md](evidence/2026-10-18-studio-r7/README.md).

## 1. Viewport sizes (BD-995)

`tools/monitor4.py` now has `--maximize` (PR #537): `launch studio` maximises the new Studio window on the virtual monitor by default (`--no-maximize` keeps it small), `place --maximize` does it for windows already there. Only Studio and Blender windows, never Place1, never Edge, no topmost, no focus steal.

| Situation | Game view (`CurrentCamera.ViewportSize`) |
| --- | --- |
| Studio maximised on the 1280 x 720 virtual monitor | **516 x 481** (Studio's own panels use about 764 x 240 px) |
| Same window, not maximised, on the virtual monitor | **498 x 463** (before: 500 x 465 / 296 x 304) |
| Same window found maximised on a 1920 x 1080 screen | **1156 x 841** |

So maximising on the virtual monitor barely helps (516 x 481 instead of 498 x 463): the docked Studio panels take the room, and the tools cannot hide or undock them. A real-size check needs a bigger screen (1920 x 1080 gives 1156 x 841) or the owner hiding the panels once by hand. During this round the window changed by itself twice (virtual monitor, then a 1080p screen, then back, not maximised); no `monitor4` process was running, so it was the owner or Windows. The launch helper also moved the small Studio splash window first; it now skips the splash and waits for the real window.

## 2. Results

| Item | Verdict |
| --- | --- |
| 1 Index tab taps (Patterns, Colours) stay in the Index; shop tabs (Auras, Trails, Eggs) stay in the shop (BD-1100, BD-1083, BD-1101) | **PASS** at 516 x 481 (pictures 383, 384, 388, 389). BD-1101 had the same cause as BD-1083 and is fixed by PR #534. Not tested: a tap on the bare dark area while a menu is open (should still travel), 848 x 423 |
| 2 Goals and Tasks panels never overlap (BD-1095) | **PASS** (390 to 393): opening one hides the other. New small defect: the open Goals sheet lies over part of the HUD rail (BD-1108) |
| 3 Runs end cleanly (BD-1096) | **PASS**: four runs (60, 90, 90, 90 seconds) each went Active to Settled in 0.2 s, never stuck in Ending, four `run_end` telemetry lines, no "Script timeout" in the console. The run card is 395 and 419 |
| 4 Eggs screen, hatch card, reveal (BD-1085, BD-1067) | **PARTIAL PASS**: at 516 x 481 and 498 x 463 the header is clear of the nests, OPEN EGG is whole, the hatch and the splat fit (396 to 399, 414, 417). Still wrong: the class chip lies over the dino name (398, 416; same as docs/197 and pictures 270 and 271, BD-1097), and on a Rainbow egg the "Rainbow egg!" ribbon is cut at the left edge and the chips overlap (416, new row BD-1107). The 1156 x 841 hatch looks fine (411 to 413). Not done: 848 x 423, 667 x 375, a drag from big to small while the Eggs screen is open |
| 5 Toast, potion and shop gaps (BD-1089) | **PASS** for Calm motion (OFF: the toast slides in over about 0.1 s; ON: it appears in place; pictures 401, 402), potion replace confirm (408), restock (the offers changed and the line "Potion shop restocked" showed, 409), buy, cancel-free confirm, USE. **DEFECT** (BD-1102 confirmed): a toast lies over the second potion row (405, 406) and over the Explore button on the Eggs screen (418). Not reached: a purchase that stays pending |
| 6 Close paths (BD-1027) | Escape does **not** close the Index through the keyboard tool (410), same as docs/192: the tool's Escape does not reach the game, so the question stays open. C closes it. Legendary stop: no Legendary appeared (not forced). A Rainbow egg stopped "Skip the rest" as designed (415, 416) |

## 3. Defect table

| # | Defect | Picture | Severity | Row | Suggested fix |
| --- | --- | --- | --- | --- | --- |
| 1 | Class chip over the dino name on the reveal card | 398, 416 | P3 | BD-1097 (note added) | give the chip its own line above the name or shrink the name |
| 2 | Rainbow reveal: ribbon cut at the left edge, "Skip stops here" chip over it | 416 | P2 | BD-1107 (new) | anchor the ribbon inside the card with a minimum margin |
| 3 | Toasts lie over menu content (potion row, Explore button, shop tabs) | 405, 406, 418 | P2 | BD-1102 (note added) | toasts below the rail and never over an open menu, or show them inside the menu |
| 4 | Open Goals sheet covers part of the HUD rail | 391, 393 | P3 | BD-1108 (new) | open Goals below the rail or to the left |
| 5 | Studio panels leave only 516 x 481 on the virtual monitor | 380 | P2 | BD-1109 (new) | owner hides panels once, or use a 1080p screen for UI checks |
| 6 | Potion Shop hint line over the second row at 516 | 403 | P3 | BD-1103 (note added) | move the hint under the rows |

Lessons: the mouse tool takes GUI coordinates (screenshot y minus about 58); the rail Shop button only opens the shop when the player stands within 10 studs of the SHOP prompt, otherwise it shows "Follow the glow"; a small hand-written test bot (start, walk to the nearest food, end after N seconds) was enough because `execute_luau` cannot read files or use HTTP.
