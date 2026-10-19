# 212 The HUD rail with a word on every button, at most five buttons (BD-1116, R1 of docs/202)

Written 2026-10-19. Label: **CURRENT BUILD behind a flag**, proved **offline only** (a layout mock and pure numbers, no Studio, no phone). Source: [docs/202](202-ui-standards-from-steal-an-egg-and-ride-a-dino.md) section 4.6 and R1 ("2 to 3 big buttons with icon and word, never more than five on the HUD"). The Studio look is the new row BD-1143. The default build is unchanged.

## 1. What a player sees (flag on = the playtest build)

| | Before (flag off, Build 020 look) | Now (`HudRailWordsEnabled` on) |
| --- | --- | --- |
| Buttons at home | six: Dinos, Eggs, Fusion, Shop, Potions, Settings | **five with a word**: Dinos, Eggs, Fusion, Shop, Potions, and **Settings as a small gear** at the end of the rail (not counted as a button) |
| Buttons in a run | Potions, Settings | Potions and the gear (the four home buttons stay hidden: BD-1105) |
| Word on a button | desktop: shrinks with the window (about 10 px at 516 px wide); phone: hidden on narrow windows | **desktop 16 px or more** (20 px at full size), **phone 14 px or more**; the word is **never hidden** on a word button |
| Button size | shrinks with a small desktop window (28 px high at 516 px wide) | **44 px or more** everywhere (56 x 176 design px on a desktop, 52 px high on a phone) |
| Gear | (was a button with the word SETTINGS) | a square of **48 px or more** on a desktop, a grid slot on a phone; icon only (the existing Settings picture) |

Unchanged: the keys C, B and G, the "At home" rule (the four home buttons are hidden in a run), the glow trail and the walking guide (they start from the same `press`), the first-run MENU chip, the red dot on Dinos, the gold marker on the open screen's button, Calm motion (nothing moves), the Settings screen itself (the gear opens it).

## 2. The numbers (`TouchLayout.RAILWORDS`)

| Thing | Value |
| --- | --- |
| Desktop cell | 176 x 56 design px, 4 px gap, icon 44 on the left, word 20 design px |
| Desktop scale | the window scale, **never under 0.8** (so the word is 16 px or more) and never over 1 |
| Desktop gear | square, `max(48, ceil(48 / scale))` design px (48 px or more on screen), under the five cells |
| Desktop place | left edge 14 px; vertically centred, but never above 64 px (under Admin) and never lower than the space that leaves Tell us! above the egg plate |
| Phone cell | at least 60 px wide (room for POTIONS at 14 px), 52 px high (44 px with a 2 px gap in a 339 px tall window); the five buttons and the gear take one row, else a 2-row grid (the gear is the last slot) |
| Word floors | desktop layout 16 px, phone layout 14 px (docs/208) |
| Toast stack beside the rail | shrinks to at most 0.7 so it fits right of the rail in a narrow desktop window |

Samples (desktop layout = a mouse and a tall window; phone layout = a touch screen or a window under 500 px high): 1156 x 841 desktop home: rail 184 x 356 at scale 1; 1280 x 720: scale 0.9, word 18 px; 600 x 600: scale 0.8, 294 px high, word 16 px; 516 x 481 phone home: 3 columns x 2 rows, cells 65 x 52, word 14 px; 848 x 423 phone home: one row of five plus the gear; in a run the rail is Potions and the gear only.

## 3. When the words do not fit (fallback)

If the rail with words would touch another HUD piece (the egg plate, the wallet, the weather column, Home, Tell us!, Admin, the SIZE bar, the "Back to the middle" chip) or leave the window, `TouchLayout.compute` answers with the **old rail** (six buttons, Settings an ordinary sixth button, `railWordsFallback = true`). In the sweep this happens only in windows **under 500 px wide with a phone layout and under 600 px wide with a desktop layout** (for example 516 x 500 with a mouse). Nothing overlaps there either; the buttons are just as small as before.

## 4. LEAD decisions (owner delegated 2026-10-16)

1. **Five word buttons plus a gear, not six buttons, not a hidden Settings.** The studied games keep two or three big buttons and never more than five in total; Settings is not a destination players use often. Options not taken: six buttons with words (more than five, and six wide buttons do not fit a 516 px phone window); Settings inside the Shop or the Dinos screen (a screen should not hide a basic control; kids look for a gear); fold Fusion into Dinos (Fusion has its own key G and station). Overturn: set `HudRailWordsEnabled` false in the playtest rule of `tools/release_profiles.py` (one line), or make `RailRun.isGear` return false and pass `navCount + 1` (Settings becomes a sixth word button).
2. **The existing Settings button is the gear** (same button, same marker, same tap routing), not a new button. It is resized by `RailRun.place`. The gear uses the existing Settings picture (a shield): a real gear picture is an art task (no new art in this change).
3. **The rail stops shrinking under 0.8 on a desktop**, because the word must stay 16 px. The price is a bigger rail in a small window (294 px high at scale 0.8); a window that cannot hold it falls back (section 3).
4. **The cells stay left of the screen** (the rail did not move to the right or bottom).
5. **Flag** `HudRailWordsEnabled`: false in Config and in the default profile, true in the playtest profile (standing rule [157](157-playtest-profile-newest-features.md)), in the rehearsal list. Free, no Robux.

## 5. Where the code is

* `src/shared/TouchLayout.luau`: `RAILWORDS`, the desktop words rail, the phone words grid, `railFits`, the fallback in `compute`. `compute` takes `railWords` (nil / false = the rail exactly as before). `rail.gear` and `rail.gearCell` are new; `positions` has one entry per word button.
* `src/client/RailRun.luau`: `isGear`, `count` (the gear is not counted), `position`, and **`place`** (the loop that placed the rail buttons moved here from `Bootstrap.client.luau`, which got 920 bytes smaller; the ceiling is lowered).
* `Bootstrap.client.luau`: passes `railWords` to the layout and calls `RailRun.place`. `HudV2.layout` still publishes `RailRect` (it now includes the gear), so the panels (`HudPanelStack.clearRail`), the toasts and the stall bubble need no change.

## 6. How it is checked (offline, in CI)

* `python tools/verify_rail_words.py --runner luau.exe` (new): the real `TouchLayout`, `PhoneScale`, `Config`, `RailRun`, `HudPanelStack`, `ToastSlot` in the geometry mock of docs/201. **1,920 layouts** (20 widths x 16 heights x mouse and touch x run / home / home with the objectives pill): at most five word buttons, 44 px or more, inside the window and the rail frame, no two overlap, none lies over any other HUD piece, the word is 16 px (desktop layout) or 14 px (phone layout), the longest word fits its box (an estimate of 0.6 em a letter, wider than the real face), the icon and the word do not overlap, the gear is 48 px on a desktop; the flag off is the old rail; **64 rails placed by the real `RailRun.place`**: five words and the gear at home, Potions and the gear in a run, the gear has no word, the fallback shows six buttons; open panels clear the rail; the toast stack is as clear of the rail as it was of the old one (400 cases). 18 mutants (each defect put back) fail the check.
* The earlier checks also run with the words rail: `verify_hud_clearance.py` (3,840 layouts, Tell us! and Admin clear of every rail button and the gear), `verify_hud_panel_stack.py` (464 states, four rails), `verify_shop_prompt_bubble.py` (the whole sweep a second time), `verify_menu_layout.py` (the shop tab row and toasts, a second run with the flag on).
* `tools/verify_server_module_size.py`: the Bootstrap ceiling is lowered to match.

## 7. NOT verified (needs Studio, row BD-1143)

How the words, the 56 px cells and the gear look at 516 x 481, 848 x 423, 1156 x 841 and on a real phone; whether five words plus a gear is clear to a child; whether the shield picture reads as "settings"; that the glow trail and the first-run MENU chip look right with the new cells; Reduce Motion in the real game; the real font width of POTIONS and FUSION; the fallback at 516 x 500 with a mouse. Nothing here is a picture.
