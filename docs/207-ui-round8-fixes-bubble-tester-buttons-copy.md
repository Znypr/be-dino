# 207 UI round 8 fixes: stall bubble, tester buttons, copy slips, Settings (BD-1128, 1129, 1130, 1132)

Written 2026-10-19. Label: **CURRENT BUILD** after this change, proved **offline only** (a layout mock and pure rules, no Studio, no phone, no gamepad). Source of the defects: Studio round 8 ([205](205-studio-round8-bubbles-rail-toasts.md), pictures 421, 426, 432, 434, 435, 437, 438, 440, 447, 448 in `docs/evidence/review-2026-10-17/`). The Studio re-check is a new row (see the end). Nothing was published, no flag was changed, no profile was touched.

## What the owner saw (plain words)

1. A small window (516 px): the stall message bubble was hidden behind the rail and the weather plate.
2. The "Tell us!" and "Admin" buttons lay over Explore, over HOME in a run and over the bottom of the Fusion menu.
3. The Heart bubble said "Open" for "Show off"; the Trails tile said "1 yours"; the sold-out potion card said "Sold out. Back" and was cut.
4. Settings, Look tab: the rows touched each other and the tab row. The weather name lay over the Potions button. The AUTO button on the Eggs screen opened Settings on whatever tab was used last, not on Help.

## BD-1128 (P2): the stall bubble above the HUD, clear of it

**Cause.** The bubble was a 3D billboard. A billboard is always drawn under every screen layer, so any HUD piece at the same spot hid it.

**LEAD decision (owner delegated 2026-10-16).** Both: the bubble is drawn in a screen layer **above** the HUD (`HubPromptBubbleUI`, DisplayOrder 10; the Fusion menu is 20, Admin 30, Tell us! 40) **and** placed **clear** of the HUD pieces, because on top of the HUD it would cover the rail, Home or LEAP. Options not picked: only raise the layer (covers buttons), only shift the billboard (still under the HUD, and the camera moves each frame). To overturn: put the `BillboardGui` back in `HubPromptBubble.show` and drop the placing.

**How it works.** Each frame the client projects the stall point onto the screen (`WorldToViewportPoint`) and `HubPromptBubbleRules.place` slides the bubble onto the screen and off every HUD rectangle (6 px gap), taking the nearest free spot; it glides there (jumps with Reduce Motion). HARD pieces (rail, weather and LEAP column, Home/Explore, egg plate, Crystals block, Tell us!, Admin) are never covered when a free spot exists; SOFT pieces (build badge, Studio notice, the "Back to the middle" chip) are avoided while a spot also clears the hard ones. If the big bubble has no room the small one (220 x 100) is tried. The rectangles come from `TouchLayout.hudRects` (published by `HudV2.layout`) plus the rail, Tell us!, Admin and chip rectangles that were already published. Behind the camera the bubble is hidden (the key still works).

**Proved (offline).** `python tools/verify_shop_prompt_bubble.py --runner luau.exe`: the real `TouchLayout` rectangles at 13 widths (440 to 1920) x 11 heights x mouse and touch x run / hub / hub with objectives; 858 canvases and about 26,000 stall positions: the bubble stays on the screen and touches no hard piece at every window 500 px wide or more, except 3 tight desktop-layout windows with the objectives pill (about 500 to 600 px wide, no free spot exists; it then covers the least). The real client module in a mock Roblox: layer above the HUD, no billboard, centred on the projected point, offset by the layer origin, moved off a HUD rectangle, back on the screen, hidden behind the camera, glides / jumps, one per-frame update only while it shows. 50 mutants (each defect put back) all fail the check.

**Not verified.** Studio, a phone, how the bubble feels moving. Two engine facts are assumed, not seen: `WorldToViewportPoint` is relative to the full screen and `ScreenGui.AbsolutePosition` carries the top-bar offset (the same assumption `FeedbackClient` already makes). Windows under 440 px wide were not checked (the whole HUD is a last resort there).

## BD-1130 (P2): Tell us! and Admin never cover Explore, HOME or a menu

**Causes (two).** (1) The two buttons sit side by side in the bottom-left corner, 256 px in all; Home starts at x 222 in a 516 px window, so Admin lay over it (any window under about 620 px wide). (2) Both should hide while a menu is open, but the Fusion menu is a screen layer (`BeDinoFusionUI`) made the first time it opens; the old code looked it up once at start-up (a 30 s wait that timed out, and held the other hook back).

**Fix.** `TouchLayout`: Admin shrinks to fit between Tell us! and Home (at least 72 px, still a 44 px target), stacks above Tell us! when even that does not fit, and the chip rises above them; on the desktop layout in a window under about 520 px wide the build badge lay over Admin's old top-left spot, so Admin takes the first free spot. A new small module `MenuWatch` hooks `PlayerGui.ChildAdded`, so the Fusion menu is seen however late it is made; Admin hides for any open menu, Tell us! hides for the Fusion menu at every size (and for the other menus on a short window, as BD-538 decided; on a desktop window the centred menus leave the corner free: unchanged).

**Proved (offline).** `python tools/verify_hud_clearance.py --runner luau.exe`: the real layout at 20 widths (440 to 1920) x 16 heights x mouse and touch x 3 modes (1,920 canvases): both buttons are on the canvas, 44 px or more and touch no other piece (egg plate, wallet, goal line, Goals header, objectives pill, weather, LEAP, Home/Explore, every rail button, badge, chip, SIZE bar) and not each other; where the old spot was clear nothing moved (800 x 360 phone, wide desktops); `MenuWatch` in a mock PlayerGui sees a Fusion menu that is made after start-up; 10 mutants fail. Below 440 px wide is out of scope. **Not verified:** Studio (the picture 434, 435 and 440 spots).

## BD-1129 (P3): copy

* Heart bubble button: **"Show off"** (phone: "Tap to show off"); the stalls still say "Open" / "Tap to open" (`HubPromptBubbleRules.buttonWords`).
* Shop landing tiles (Auras, Trails): **"You have 2"** instead of "2 yours" (`ShopArt.subtitle`).
* Sold-out card caption: **"Back later!"** instead of "Sold out. Back later!" (the button already says SOLD OUT; the long line was cut at 516 px) (`ShopCardState`).
* `python tools/lint_kid_text.py --baseline`: 0 new problems. Not changed: "1000000" without separators in the Index list (a test-currency value, low).

## BD-1132 (P3): what the mocks could prove

Fixed and proved: **(1) Settings rows.** The cause was the floor pass: the body is drawn at 0.57 at 516 px, so a 48 design px control is only 27 px and each was grown to 44 px around its middle, into its neighbours. `SettingsMenu` now works out its control height, pitch and first row from the scale really drawn (44 px on screen, 8 px gap; a desktop window keeps 48 / 56 / 64). The Look and Controls tabs at 12 window sizes, mouse and touch: no text over text, no tab cut at the top, 4 mutants fail (`verify_menu_layout.py`). **(2) AUTO opens Help.** The Eggs screen asks for the Help tab (`openSettings("help")`; Bootstrap's hook takes an optional tab, one line). **(3) Weather title.** The small soft line at home slid clear of the HUD (`WeatherTitleSlot`; the title layer ignores the top bar, the rectangles are offset for it): clear at every window 500 px wide or more, three top-bar sizes, 3 mutants fail.

**Not fixed (needs a screen harness that does not exist yet, then Studio):** the Dino Index card (DEWDROP chip cut by the secrets line, class badge icon only with no word, the card area using two rows and leaving half the panel empty, a tab cut at the left edge, picture 441 and 455) and the My dinos details (the second Species line hidden under EQUIP and BACK, picture 456). They need the Index and details screens mounted in the geometry mock.

## Not changed

Bootstrap: one line (the `openSettings` hook). Release flags, profiles, saves, remotes: nothing. The Rainbow reveal chips, the Goals sheet over the rail and the Fusion tab names (BD-1107, 1108, 1131) belong to another helper.
