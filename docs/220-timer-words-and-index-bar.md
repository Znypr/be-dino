# 220 Short timer words, potion drain bars and the big Index count bar (BD-1124, R11 and R12 of docs/202)

Written 2026-10-19. Label: **CURRENT BUILD behind a flag**, proved **offline only** (pure words and static wiring, no Studio, no phone). Source: [docs/202](202-ui-standards-from-steal-an-egg-and-ride-a-dino.md) R11 ("timers become icon + number chips bottom right; growth and potion timers get a drain bar with the time in it") and R12 ("big count bar 'Found 1/22'"). The Studio look is the new row BD-1161. The default build is unchanged. (Doc 219 is the session handoff note outside the repo.)

## 1. What a player sees (flag on = the playtest build)

The bottom-right HUD stack was already bottom right (the `timers` frame of `TouchLayout`), so nothing moves. The words get shorter and the picture does the talking.

| Place | Before (flag off, Build 020 look) | Now (`TimerChipsEnabled` on) |
| --- | --- | --- |
| Weather tile, clear sky | weather icon + "Weather in 4 min" | weather icon + **"Next: 4 min"** |
| Weather tile, during an event | rain icon + "Rain 2 min" | rain icon + **"Rain: 2 min"** (the toast "Rain started!" and its soft sound are unchanged) |
| Active potions (lines under the tile) | "Speed potion 3 min", a potion chip at the right | **"Speed: 3 min"**, the same chip, and a **thin amber drain bar under the chip** that empties as the potion runs out |
| Boost line ("Speed +20%") | unchanged | unchanged |
| Potion Shop top line | "Crystals: 123  •  New offers in 25 s" | "Crystals: 123  •  **New in 25 s**" |
| Dino Index bar | 34 px bar, "Collected 1 of 22  (4%)" in 20 px | **44 px bar (as tall as the buttons beside it), "Found 1/22" in 24 px**; the milestone marks move down with it |
| Floating "+N" on pickups | already exists (the pickup pop in Bootstrap) | unchanged |

Time words stay the docs/72 ones ("5 min", "40 s", "2 h"), from `UIFormat.duration`. The secrets line ("2 / 7 secrets found") and the Eggs screen "Ready in 3 h" are unchanged.

## 2. Where it lives

| Thing | File |
| --- | --- |
| The words (pure) | `src/shared/TimerWords.luau`: `weather`, `potion`, `potionLines`, `restock`, `found`, `drain`; with `short = false` each returns exactly the Build 020 sentence |
| The HUD block | `src/client/HudTimers.luau` (new): the weather tile, the toast and sound on a new event, the potion lines, the call to `PotionChips.update`. **Moved out of `Bootstrap.client.luau` unchanged** (Bootstrap was 61 bytes under its size ceiling); Bootstrap now calls `attach` once and `refresh` each HUD tick. Bootstrap 72,239 -> 70,879 bytes, ceiling ratcheted to 70,900 (`tools/verify_server_module_size.py`) |
| Drain bars | `src/client/PotionChips.luau`: a 26 x 4 px track and fill under each chip, refreshed every tick; only for a potion whose catalog entry has a duration |
| The Index bar | `src/client/DinoIndexScreens.luau` (`meter` takes a height and a text size), `src/shared/IndexProgress.luau` (`summary().short`) |
| The restock line | `src/client/ShopScreens.luau` |
| The flag | `Config.TimerChipsEnabled`: false in Config and in the default profile, true in the playtest profile ([157](157-playtest-profile-newest-features.md)), in the rehearsal list |

## 3. Evidence (offline, not Studio)

- `tools/verify_timer_words.py`: the pure rules with the pinned Luau runtime (flag-off sentences unchanged, short words, sorted potion lines, expired ones dropped, drain clamped 0..1 and none without a duration, "Found 1/22", kid words), static wiring (Bootstrap hands the block to HudTimers and writes no weather sentence itself; PotionChips reads the flag and refreshes the bar; the Index and the shop read the flag), 16 mutants caught.
- `verify_sources`, `verify_server_module_size` (new ceiling), `verify_local_budget`, `verify_phone_scale`, `verify_odds_copy`, `verify_secret_species` (guard updated to the new Index line), `verify_menu_layout`, `verify_text_style`, `verify_close_paths`, `verify_class_picker`, `verify_pattern_colour_index`, `verify_potion_purchase`, `verify_potion_shop`, `verify_hud_clearance`, `verify_hud_panel_stack`, `verify_small_window`, `verify_shop_card_price`: pass.
- `tests/test_release.py`, `tests/test_rehearsal.py`: the flag is off in the default build and on in the playtest build.

NOT checked: how the drain bar sits under a real potion chip, the weather tile with a long name ("Northern Lights: 10 min" may wrap to two lines in the 62 px tile, as the old sentence did), the big Index bar next to the page arrows, a phone. Row BD-1161.

## 4. Not in this change (follow-ups)

- A book icon on the Index bar (R12): no such icon exists and no code-drawn art is allowed; it needs an art task (docs/72 flow) before it can be bound.
- Per-area Index bars with a small reward (R12): a design question (which areas, what reward); not started.
- A drain bar on the growth timer (R11): there is no growth timer on the HUD today.
- To overturn: set the playtest rule of `TimerChipsEnabled` to false (one line in `tools/release_profiles.py`).
