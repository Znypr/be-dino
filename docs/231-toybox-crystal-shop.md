# 231 Toybox Crystal Shop (BD-1178), 2026-11-14

Status: **Review / test**. The code and the offline tests are done. **Not seen in Studio, not seen on a phone, nobody has looked at it in the game.** Reworked on 2026-11-14 to the owner target (section 2).

Why: [228](228-ui-toybox-proposal.md) board 3 (Crystal Shop), built on the kit of [230](230-toybox-ui-kit.md) and on the price-on-button card of BD-1118 / BD-1144 (docs/202 R3, docs/213).

Labels: everything below is **CURRENT BUILD BEHAVIOR of the playtest profile once the card ids are bound**. The default build is unchanged.

## 1. The switch and the fallback

No new flag: the shop follows `Config.ToyboxUIEnabled` (default false, playtest true). The Toybox card is drawn only when the flag is on AND all six `toybox_card_*` ids are bound (`Theme.Toybox` exists and `ToyboxKit.ready(Slots.Images, "card")`, the group pattern of `ToyboxSkin`). Otherwise `Cards.build` falls through to today's code (the price card or the old card, whichever the other flag says). Client presentation only: no server, save, price, Robux or economy change; the price still only opens the confirm page.

## 2. What the page and the card are (flag on, ids bound) - REWORKED to the owner target 2026-11-14 (shop-target-mock.html)

**Page** (`src/client/ShopToyboxPage.luau`, rules in `src/shared/ToyboxShop.luau`, wired in `ShopScreens`; flat cream boxes, no picture drawn in code):

- Title "Crystal Shop". In the header, left of the X: the **crystal wallet pill** (crystal icon + the number with commas, "12,450"). It leaves with the body when another screen opens.
- **Cream tab chips** (Auras / Trails / Eggs / Conditions after level 3 / Crystals), the selected one amber; on Auras and Trails the **"Styling: <dino>" chip** at the right (replaces the long "Switch dinos in Dinos..." bar; a tap opens Dinos, where the dino is switched). When the chips have no room (small window) the Styling chip drops to a row of its own.
- **Card grid fills the whole body width**: 4 equal columns when a cell is at least 170 px on screen, else 3; fewer cards than columns (the 3 Auras) share the whole width; 12 px gaps, 4 px pad, the 8 px scroll-bar strip on the right (no bare stud strip). Rows below the first scroll inside the grid. No page arrows and no footer line any more (the wallet is in the header; the "no crystals yet" hint is a cream note above the grid).
- **Eggs / Conditions / Crystals** keep their content but sit on one cream panel in the same window; the Buy popup sits on a cream panel too (dark words, NOT NOW grey, BUY green).

**Card** (`src/client/ShopToyboxCard.luau`), whole card = picture of its tier (`toybox_card_<tier>`), parts top to bottom, 16 px side inset:

- name (outlined white), the rarity word in its tier colour on a cream pill, a **cream art box** (warm gradient, dark outline, clipped) with **slow rays** behind the art (three copies of the existing `shaftGradient`, one turn per 40 s, still under Reduce Motion, left out while not uploaded);
- a **cream benefit band** with dark text ("Growth +15%", "Faster"), then **ONE wide button** at the foot: green with the crystal icon and the number ("60", "3,700": icon and number are one group, `PriceGroup`, BD-1192, so they never overlap, also with the skin's word label), grey UNEQUIP on the equipped card (gold ring + soft glow), grey LOCKED on a locked secret card;
- a **locked Legendary / Mythic** is a secret: name "???", a "?" in the art box, a short hint ("Reach level 30") in the band, LOCKED. A locked trail of a lower tier keeps its picture and says LEVEL n;
- the old **Info** word is gone from the card (not in the target); a **tap on the art box** opens the same read-only details page.
- The page is drawn again when the window is resized while it is open (ModalCompact.onLayout). Cream outlines use ApplyStrokeMode Border so they never stroke the words.
- Art in the box today: the bound aura picture (the v2 ring alone, `AuraRing`, centred) / the trail icon; tab and Styling chip words are dark ink (#3A2F1E) on their own label, no outline. A live 3D preview of the player's dino wearing the aura is NOT done here (row BD-1203).

## 3. Not done, and why (OWNER QUESTION in docs/116 C-59)

- **Right-side tabs.** (HISTORICAL, replaced by the cream tab chips on top of the 2026-11-14 target.) docs/228 shows the tabs on the right. The shop body is a fixed 824 x 402 box and every other page (Eggs, Conditions, Crystals, odds) is laid out over its full width, so a side column would overlap them; moving it needs a re-layout of all five pages. LEAD decision: the tabs stay in the top row (they already carry the existing tab icons and become gloss buttons through the skin). A follow-up row can re-lay-out the pages.
- **"Nests" tab.** The game has no Nests shop tab (tabs: Auras, Trails, Eggs, Conditions, Crystals; nests are claimed elsewhere and overflow into crystals, docs/72). Not invented.
- **"Find it in Volcano" hint.** There is no data saying where a Legendary comes from; the hint says only what the code knows (the account level a trail needs).
- **Real Legendary aura art** is an art task (the row says so); the card uses whatever `aura_<id>` / trail art exists.
- The card is 264 x (270 or the phone height) design px as today, with 10 px margins; the picture is a 256 x 320 render sliced to that box.

## 4. Tests

`python tools/verify_toybox_shop.py --runner <luau.exe>` (in CI): source guards (flag untouched, hook lines, the new files presentation only, allowed instance classes, no asset id written); the pure rules (layout order, columns, grid fills the width, wallet commas, tab words); then the real `ShopScreens`, `ShopCards`, `ShopToyboxCard`, `ShopToyboxPage`, `ToyboxShop`, `PriceGroup`... in the geometry mock at the 12 window sizes plus 1280x720, 1274x481 and 1920x1080, mouse and touch, Auras and Trails: the wallet and tab chips, the grid fills the body (right edge within 16 px, equal cells, 12 px gaps, 4 columns at 1280x720 and 3 at 667x375 on Trails), nothing below the body, every word at least 14 px, icon and number do not overlap, one button per card and only green or grey, the secret card, the cream panels of the other tabs, the popup; flag off / ids unbound / one id missing = the old card; 42 mutants. **Offline only: nothing is drawn.**
