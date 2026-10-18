# 201 Menus in small windows: shop tabs, toasts, the rail in a run, class icons (BD-1101, 1102, 1103, 1105, 1099, 1082)

Written 2026-10-19. Label: **CURRENT BUILD** after this change, proved **offline only** (a layout mock, no Studio, no phone). Source of the defects: Studio round 6 ([199](199-studio-round6-shop-toasts-check.md), pictures 360 to 379) and Studio round 5 ([197](197-studio-round5-verification.md)), plus the owner's picture 115 (the rail on the island). The Studio re-check is BD-1106.

## What the owner saw (plain words)

1. At 500 px the HUD buttons (Dinos, Eggs, ...) lie over the shop's tab row. A tap on TRAILS opened the shop's first page, a tap on EGGS closed the shop.
2. A toast ("Follow the glow", "Done!") covered the whole row of HUD buttons, and with a menu open it covered the tab row and the first prices.
3. Small slips in the shop at 500 px: the price line under BUY, "Uncommon" cut, "You have ..." cut, the Potion Shop hint over the second row of cards, BUY and CANCEL touching.
4. On the island the four HUD buttons Dinos, Eggs, Fusion, Shop all just say "At home" ("confusing, maybe just dont show it in the island").
5. Class icons only on the reveal card; the Found on line cut; Boost worded two ways.

## What was really wrong, and the fix

| # | Cause | Fix |
| --- | --- | --- |
| 1 | Two causes. (a) A raw tap was sent to the HUD button under the menu (the BD-1083 cause; the fix is in `HubTravelClient.routeTap`, asking `ModalClose.onBackdrop`). (b) The shop laid its tabs and cards out for the panel scale (0.8), but at 500 px the body is drawn smaller again to fit the width (0.57 in all). The 44 px floor then grew every button from its middle: the tabs grew up over the heading strip and down over the cards. | `ShopScreens` asks `ModalCompact.bodyScale()` (the scale really drawn) and uses the phone layout in every compact window, also with a mouse. Card height, header strip, footer follow the room. |
| 2 | The toast rule only knew the Crystals plate. | New pure rule `src/shared/ToastSlot.luau`, used by `Toasts.luau`: see below. |
| 3 | Fixed design heights (a 24 px text box, a 132 px potion card, 44 px buttons 19 px apart) while the floor makes text and buttons bigger. | Heights follow the floors (`textPx`, `fitH`, `buttonH` in `ShopScreens`); the rarity chip is as wide as its word. On a desktop window every number is the old one (checked). |
| 4 | `HubTravelClient.applyDimming` relabelled four buttons "At home". | They are hidden in a run (`RailRun`); the rail closes up. |
| 5 | The class badge was built only in `HatchSequence`. | `ClassRow` puts it on Index cards, My dinos details and the inspect details. |

## The toast rule (BD-1102)

* **No menu open:** the stack (3 cards) stays at the old spot (80 px from the top) when it is clear of the Crystals plate, the goal line and the HUD rail; else it slides sideways to the nearest free spot, else it drops under the blockers. `HudV2.layout` publishes the rail as the `RailRect` attribute (Bootstrap is untouched for this).
* **Menu open:** **one** card (the newest). Above the menu when there is room (a desktop window), else below it, else a **slim** card (0.7 scale, text 14.7 px) along the bottom edge. Along the bottom edge a tap goes **through** to the menu (the card's tap button is switched off), so nothing is blocked. A toast never takes the top of the menu: the heading, X, the tab row and the top 60 percent of the first row stay free.
* LEAD decision (owner delegated 2026-10-16), options not picked: "below the rail on the right" (a 440 px card cannot sit right of the rail at 500 px) and "always above the menu" (a small window has no room above). To overturn: `ToastSlot.place`.

## The rail in a run (BD-1105)

LEAD decision: with the Cave hub on, in a run (any state that is not Sanctuary) the four buttons that would say "At home" are **hidden**; POTIONS and SETTINGS stay. The rail is laid out again for the buttons that are left (`TouchLayout.compute` gets the count, each button takes the next free slot). At home all six show, in the old slots. With the hub off nothing changes. Hiding is immediate (no fade), so Calm motion needs nothing and nothing flickers at the start of a run. The first-run MENU chip (FtueRail) is not shown when the hub rule hides buttons (it would open nothing). The keys (C, B, G) and the "At home" toast of a pressed key are unchanged. **To overturn:** one constant, `HubTravelClientRules.HideDimmedInRun = false` (they are dimmed again with the words "At home").

## Checks (offline)

`python tools/verify_menu_layout.py --runner luau.exe` (in CI): the REAL `ShopScreens`, `Toasts`, `ToastSlot`, `RailRun`, `ClassRow`, `TouchLayout`, `ModalCompact` and `PhoneScale` in the geometry mock of `tools/close_paths_smoke.luau`, at the 11 window sizes of [195](195-small-window-layouts.md), with a mouse and with touch:

* every shop tab and X is the top thing at its centre; the raw-tap route never sends it to the rail button below (8 sizes really have a tab over a rail button);
* toasts: no card over the rail, the Crystals plate, the goal line (also with a rail 40 percent of the window high); with a menu open exactly one card, never over X, the heading, the tab row or the top of the first row; an edge card lets taps through; a normal card takes the tap;
* the shop pages (Auras, Trails, Eggs, Crystals, the confirm pages, Egg Chances, the Potion Shop): no text over text, no text that cannot fit its box (0.5 em per letter estimate), nothing sideways out of the body; a desktop window keeps the old design numbers;
* the rail: all six at home in the old slots; in a run (Active, Ending, Dead) exactly Dinos, Eggs, Fusion, Shop hidden, the two left take slots 1 and 2, are 44 px, do not overlap, are not covered by toasts; hub off hides nothing;
* class icon inside the card, not over the name, the rarity line or the detail line;
* 25 mutants (each defect put back) must fail the check.

## Not verified (needs Studio, BD-1106)

* Nothing here is a picture from Studio or a phone. The mock does not draw: text widths are an estimate, a real font may differ.
* Calm motion on and off, the real run start and end, the slim toast along the bottom edge, a toast during the Fusion menu (its own screen, not counted as a menu here).
* **Not fixed:** the Fusion menu tab names "EMERA / DIAMO" (cut at 500 px) need a look at the real Fusion layout.
