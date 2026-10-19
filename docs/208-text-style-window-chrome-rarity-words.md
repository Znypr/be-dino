# 208 One text style, window title and X, coloured rarity words, rare-find banner (BD-1119, BD-1117, BD-1120, BD-1121)

Written 2026-10-19. Four small, system-wide style rules from [docs/202](202-ui-standards-from-steal-an-egg-and-ride-a-dino.md) (R2, R4, R5, R6), built and checked **offline** (geometry mock, pure checks, mutants). **No Studio, no phone, no screenshot.** Labels: **OWNER TARGET** (docs/202), **CURRENT BUILD** (what the source does now). The default build (Build 020 mirror) is unchanged except where a line below says so.

## 1. What a player sees (CURRENT BUILD)

| Rule | Before | Now | Where |
| --- | --- | --- | --- |
| Window title (BD-1119, BD-1117) | 40 px (desktop) or 32 px (small window) times the window scale; could fall under 22 px on a narrow desktop window | At least **22 px on screen** in every window size, white, dark outline 3 px, marked as a title | `Shared/TextStyle` (`outlined(label, "title")`), `PhoneScale.titleSize`, `ModalCompact` |
| Red X (BD-1117) | 80 x 62 bar (desktop), 44 px tall bar (small window) | A red **square**, at least **48 px** on screen, top right, inside the header; the small-window header is a little taller (up to 14 design px) so it fits; the title box ends before it | `PhoneScale.closeSide / headerHeight`, `ModalCompact` |
| Card text (BD-1119) | 14 or 15 px in places | **16 px** on a desktop window for card text (potion cards, aura tag line, Index status line, dev labels). A small (phone-size) window keeps the docs/72 floor of **14 px** for now. Fine print (Eggs captions, toast second line, potion hint) is marked a *note*: 14 px | `TextStyle.Floors`, `ShopScreens`, `DinoIndexScreens`, `EggsScreen`, `Toasts` |
| One outlined style (BD-1119) | `Theme.TextStyle.apply` on most labels | The same outline, now through `TextStyle.outlined(label, kind)` for the shared label helpers (Bootstrap, HUD, Fusion, Pattern cards): kind `title`, `card` or `note`, size never under the floor of its kind | `TextStyle.outlined` |
| Rarity words (BD-1120) | White word on a chip, a few coloured by hand, a second palette in the shop preview | `RarityWord(tier)` gives the word and its colour (`Theme.RarityColors`, docs/114 s5.2, **palette unchanged**). Mixed text ("Best: Legendary Compy", "Auto-open: Common, Uncommon", odds lines, trait lines, hatch odds line) paints every whole tier word. Chips and cards that are **filled** with the tier colour keep a white word (colour and word both show) | `Shared/RarityWord`, `Toasts`, `EggsScreen`, `ShopScreens`, `DinoDetails`, `DinoIndexPanels`, pattern cards |
| Shop rarity chip colour | `ShopPreview.RarityColors` (a second table, other numbers: Common was 160,168,180) | The chip uses `Theme.RarityColors` through `RarityWord` (Common is 128,142,158). `ShopPreview.RarityColors` is gone. **A visible but small colour change on the aura and trail cards** | `ShopCards`, `ShopPreview` |
| Rare-find announcement (BD-1121) | A dark purple strip: "Sam hatched a Legendary Compy!" | With `RareFindBannerEnabled`: **no panel**, a huge white outlined title "RARE FIND!" and one sentence "A Legendary Compy was found!" with the rarity word in its colour, fades in and out (no fade with Reduce Motion), **no player name**. A secret says "SECRET FIND!" / "A secret dino was found!" and never its species. Flag off: the strip exactly as before | `RareFindBanner`, `RareHatch.findLine`, `RareHatchService`, `RareHatchClient` |

The server rules of BD-428 are untouched and still checked: best egg per 3 s window, 45 s quiet per hatcher, 4 announcements per 10 s per server, Cracked never rare, each egg once. With the flag on the server only adds the tier number, the species display name and two yes/no fields to the message (never a secret's name); the client checks them again and falls back to the old strip when anything is wrong.

## 2. The numbers

| Thing | Value | Source |
| --- | --- | --- |
| Title floor | 22 px on screen, every window size | `TextStyle.Floors.title`, `PhoneScale.MinTitle` |
| Card text floor | 16 px on a desktop window; 14 px on a small window | `TextStyle.Floors.card`, `tools/text_style_allow.json` (`compact`) |
| Note floor | 14 px | `TextStyle.Floors.note` |
| X | square, at least 48 px (every other button stays at 44 px) | `PhoneScale.MinClose`, `ModalCloseRules.MinClose` |
| Desktop X | 64 design px square (header is 78) | `PhoneScale.CloseDesktop` |
| Small-window header | `max(48, ceil(48 / scale) + 2)` design px; the body only moves down when that reaches it (at scale 0.8: header 62, body starts 64 instead of 56) | `PhoneScale.headerHeight` |
| Banner time | fade in 0.3 s, stay 3.6 s, fade out 0.6 s (Reduce Motion: 0 / 3.6 / 0) | `RareHatch.FindFade` |

## 3. How it is checked (all in CI)

- `tools/verify_text_style.py` (extended): pure floor tests; the **text-floor smoke** (`tools/text_floor_smoke.luau`, the real ModalCompact, PhoneScale, ShopScreens on every page and EggsScreen in the geometry mock of docs/201, 11 window sizes, mouse and touch, about 5,900 texts): title 22 px, X square 48 px inside the header and clear of the title, card text 16 px (desktop) or 14 px (small window), notes 14 px. 17 mutants. `tools/text_style_allow.json` holds the exceptions (none in the mocked pages; the small-window tier; the count of small literal label sizes, which can only go down) and every entry needs a reason.
- `tools/verify_rarity_words.py` (new): `RarityWord` pure tests with the docs/114 palette (hex round trip, whole words, "Uncommon" is one word, "Rarer" is not "Rare", markup escaped), no colour literal in the helper, no second palette, a **grep** of every place in `src/client` that prints a tier word (it must use `RarityWord` or be listed in `tools/rarity_words_allow.json` with a reason: a tier fill carries the colour, or the text is built here and painted where it is shown), the real Toasts and EggsScreen painting the words in the mock. 11 mutants.
- `tools/verify_rare_find_banner.py` (new) and `tools/verify_rare_hatch.py` (extended): the words and payload checks, two lines and no background anywhere, huge outlined title, coloured word, no name, secret hidden, bad payloads draw nothing, fades only with motion, goes away, one at a time, flag off everywhere except the playtest profile. 12 mutants.
- `tools/verify_close_paths.py`: the X rule (48 px) with a mutant; the close paths of docs/181 are unchanged and green. `verify_small_window.py`, `verify_menu_layout.py`, `verify_phone_scale.py`: green at all sizes with the taller small-window header.

## 4. NOT verified (no Studio, no phone)

How the outline and the coloured RichText really draw (the mock has no font); whether 16 px card text and the 48 px square X look right at 516 x 481, 848 x 423 and a real phone; whether the aura and trail chip colours (now the docs/114 palette) look good; the banner fade and position next to the toast stack and the own-hatch banner; Reduce Motion in the real game. Follow-up row: Studio re-check of all of this (see the board). Small-window card text stays at 14 px until that look.

## 5. LEAD decisions (owner delegated 2026-10-16), also in [115](115-decisions-log.md)

1. **Card floor 16 px on desktop windows, 14 px on small windows.** Option not taken: 16 px everywhere. Why: the small-window layouts (Eggs, shops) are measured at 14 px and have no room for 16 without a Studio look. Overturn: set `compact.cardMinPx` to 16 in `tools/text_style_allow.json` and `PhoneScale.MinText` to 16, then fix what the checks list.
2. **The X is a 48 px square and the small-window header grows to hold it** (the body moves down 6 px at most at the 0.8 scale floor). Option not taken: let the X hang over the body. Overturn: `PhoneScale.MinClose`.
3. **One rarity palette.** The aura and trail chip colours now come from `Theme.RarityColors`; the second table in `ShopPreview` is removed. Palette values unchanged. Overturn: restore the table and `ShopCards` colour line.
4. **Filled chips and cards keep a white rarity word** (colour and word both show). Painting the word in the same colour as its fill would hide it.
5. **New flag `RareFindBannerEnabled`** (there was no flag for the old banner). Default false, true in the playtest profile (docs/157 standing rule), in the rehearsal list. Overturn: set the playtest rule to false (one line in `tools/release_profiles.py`).
6. **No player name** in the new announcement (docs/202 section 6), although the old rule allowed cut display names.
