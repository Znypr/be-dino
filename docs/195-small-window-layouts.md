# 195 Small-window layouts: Eggs screen, hatch card, reveal (BD-1067)

Written 2026-10-18. Label: **CURRENT BUILD** after this change, proved **offline only** (a layout mock, no Studio, no phone). Source of the defects: Studio QA round 4, pictures 268 to 271 in `docs/evidence/review-2026-10-17/` ([192](192-studio-round4-qa-close-paths-walkthrough-hatch-audit.md) part C). Release flags do not matter here: these are the normal screens.

## What the owner saw (plain words)

In a small window (848 x 481, 423 high usable):

1. The Eggs screen: "Nests 5/5" sat behind the nest slots and OPEN EGG was half cut off.
2. The egg that is hatching: the egg sat off centre and the lower things were cut.
3. The dinosaur reveal: the "tap for next egg" line was cut and the dino's head went over the title.

## What was really wrong (four causes, found with the layout mock)

| # | Cause | Seen as |
| --- | --- | --- |
| 1 | The small-window code (`ModalCompact`) put the screen's body back at the **desktop spot** only when a menu opened. If the window became small while a menu was open (a window dragged, a phone turned), the body kept the desktop spot and sat **98 px too low** inside the small window. | Picture 268 and 269: a blank gap above "Nests", OPEN EGG pushed down and cut. |
| 2 | The rule that keeps buttons 44 px and text 14 px **made them bigger for good**. A window that was narrow for one moment (any drag) left every button and text bigger afterwards, and the screen was never drawn again for the new size. | Nest slots 138 px tall that moved up over the header (picture 268). |
| 3 | The hatch screen **always assumed the desktop spot** for the camera moves: in the small window the whole card was pushed 98 px down and its effects (rings, sparks) sat at the desktop spot too. A card that is 389 px tall also cannot fit 357 px of room. | Pictures 270 and 271: card cut at the bottom, tap line gone. |
| 4 | Text that shrinks to fit (the little tags on the Eggs screen) was not raised to 14 px on screen, and in a very narrow, tall window the AUTO button grew into OPEN EGG. | Tag text under 14 px at 667 wide; buttons touching at 500 wide. |

## What changed

* `src/client/ModalCompact.luau`: the body goes to the small-window home when the window **turns** small; the floor rule remembers each design size and is **reversible** (a desktop-sized window puts everything back exactly).
* `src/client/EggsScreen.luau`: draws itself again when the window size changes (what it drew is replaced, the timer refresh keeps working); in a tall narrow window it uses the room it has; tag text and AUTO / OPEN keep their 44 px / 14 px floors. **Desktop numbers are unchanged** (checked: nest 96, OPEN 80, AUTO 52 design px).
* `src/client/HatchSequence.luau`: the card sits where the screen put it (desktop or small window), **shrinks from its top-left corner to fit** the visible room (never below half), and its effect layers sit exactly over the card. Desktop: the same numbers as before (fit 1).
* `src/client/Bootstrap.client.luau` is **not touched** (another helper is slimming it). Its resize handler still only re-lays the panel; the Eggs screen now redraws itself, and the hatch card is measured when each egg starts. Other screens that draw once are safe from cause 2 and cause 1 but are **not** redrawn when the window changes (that would need a Bootstrap change: follow-up).

## Checks (offline)

`python tools/verify_small_window.py --runner luau.exe` (in CI): the REAL `ModalCompact`, `PhoneScale`, `EggsScreen` and `HatchSequence` run in the geometry mock of the close-path smoke (`tools/small_window_smoke.luau`) at 11 window sizes: **848 x 423, 848 x 481, 844 x 390, 844 x 354, 667 x 375, 667 x 339, 500 x 465, 500 x 400, 740 x 340** and the desktop 1156 x 793 and 1445 x 841 (the "x 339 / 354" ones are the phone sizes with the top bar taken off).

* Eggs screen, three states (plain egg, cracked egg with hint and chips, nothing waiting): every part fully inside the visible body (nothing cut, nothing to scroll), the "Nests" header and the hint line never touch a nest slot, OPEN EGG and AUTO never touch each other or the status row, buttons 44 px or more, text 14 px or more on screen, desktop sizes unchanged.
* Hatch, four moments (egg and colour chips, dino and tap line, last egg with buttons, cracked egg splat), with and without Reduce Motion: the whole card inside the visible body, every name, tag, hint and button inside it, "Skip the rest" inside the window, the effect layers exactly over the card.
* Resizes while a screen is open (desktop to a very narrow window to 848 x 423, 848 to 320 and back, phone to desktop and back, 848 x 481 to 844 x 390): the result is **exactly** what a fresh drawing at the final size gives, for the Eggs screen and for a screen that does not redraw itself.
* 12 mutants (each old defect put back) must fail the check.

## Not verified (needs Studio)

* **Nothing here is a Studio or phone picture.** The mock proves rectangles and numbers only. A real look at 848 x 423, 667 x 375, 844 x 390 and a dragged window is still needed (row BD-1085).
* The mock drew no real font: tag text that is longer than the tag is shrunk by the engine, and only its largest size was judged.
* Other screens that draw once (shops, Dino Index, settings) were **not** re-checked at these sizes here; they only got the two general fixes (cause 1 and cause 2).
