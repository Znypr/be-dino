# 236 Toybox layout on the Potion Shop, Settings and the HUD buttons (BD-1205), 2026-11-14

Status: **Review / test**. Code and offline tests done. **Not seen in Studio, not seen on a phone.** Label: CURRENT BUILD BEHAVIOR of the playtest profile only; `Config.ToyboxUIEnabled` stays false by default, so the default build is unchanged.

Why: findings P-d0e74b, P-6bd182, P-33416f, P-1b265a (Potion Shop), P-54d840 (Settings) and P-476117 (HUD buttons) of the polish loop (docs/234), on the layout rules of docs/232 (bright cream panels, 12 px gutter, one button height, dark ink without outline on cream).

## 1. Potion Shop (`src/client/PotionToyboxPage.luau`, rects `Kit.potionLayout`)

- Info row: a cream restock chip ("New in 56 s", `TimerWords.restockIn`) left, "Rarer potions show up less often." as dark text right. The crystal wallet is in the window header (the shop's wallet pill), so the chip never repeats it.
- Six offers as equal cream cards that fill the body width (3 columns, 2 when a card would be under 230 px on screen), 12 px gaps, the 8 px scroll-bar strip on the right. At 1280x720 all six cards and the owned row show without scrolling; a small window scrolls the page.
- A card: icon tile (rarity colour ring), name, effect, "2 left", ONE full-width buy button: green with the crystal icon (`PriceGroup`, never overlapping), grey only for sold out ("SOLD OUT") and for "cannot afford" (still opens the confirm page, which explains).
- A missing or never-loading potion icon (finding P-6bd182, Prime Feast) falls back to the generic bottle (`Kit.potionIconSlot`: own icon, else the common icon of its kind, else the speed bottle), and when even that fails to load, to the code-drawn flask. Never a blank tile.
- "Your potions": one cream panel under the cards, title left and one row of cream use chips right (scrolls sideways). The buy / replace confirm pages sit on a cream panel with dark words, CANCEL grey instead of red.
- No remote, price, stock or save change: the buy and use callbacks are the old ones.

## 2. Settings (`SettingsMenu`, rects `Kit.settingsLayout`)

- Four cream tab chips (selected amber, dark ink on their own label with no outline: `Layout.tabChip`), one button height, then ONE cream panel. Rows: label left | control column; a slider row is label | slider | value on one row; ON/OFF toggles green/grey, a chosen option amber; RESET SOUND, RESET and the other buttons grey. The Help tab (drawn by SmallScreens) is put inside the panel through `helpHost` / `inkHelp`.
- SOUND LAB is hidden unless `RunService:IsStudio()` or the player's `IsAdmin` attribute is true (`Kit.soundLabVisible`); the lab page itself keeps its old look.

## 3. HUD (`src/client/HudToybox.luau`, `Kit.Hud`)

- LEAP, CHOMP and the weather pill: the same 60 px height and 14 px corners, an icon on the left (40 px), ONE word (LEAP, or its countdown while it recharges; CHOMP), the key hint ("E", "F") as a small round cream badge in the top-right corner (desktop only), the weather pill a flat cream chip with dark ink. HOME is grey while in a run (red is for the X only). No button is moved or resized, so TouchLayout and the BD-1193 rail fix keep their numbers; 60 px at the smallest column scale (0.75) is 45 px on screen.

## 4. Tests

`python tools/verify_toybox_layout.py --runner luau.exe` (in CI): Potion Shop, Settings and the HUD numbers at 1280x720, 1274x481, 667x375, 1920x1080 and a 0.56 scale window (cards equal / 12 px apart / fill the width, owned panel under the cards, parts never overlap, buttons never under 44 px on screen, chips and panel 12 px apart, control column holds ON + RESET SOUND, no blank icon, one-word HUD labels, SOUND LAB rule, chip word is dark ink without outline), the flag-off lines kept, the flag-on modules loaded only behind `Theme.Toybox`, and 17 new mutants.

## 5. Not done / not verified

Nothing drawn: no Studio picture, no phone. The potion page and the HUD restyle are checked by rules and source guards, not by running the real `ShopScreens` / `Bootstrap` in the geometry mock. The HUD icon box is found as "the first Frame child" of the LEAP button. CHOMP gets the owner's `hud_bite` picture only where that slot is bound.
