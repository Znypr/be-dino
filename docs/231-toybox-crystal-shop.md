# 231 Toybox Crystal Shop (BD-1178), 2026-11-14

Status: **Review / test**. The code and the offline tests are done. **Not seen in Studio, not seen on a phone, nobody has looked at it in the game.** The six card pictures are **not bound yet** (the lead binds them after the upload), so today the flag changes nothing in the shop.

Why: [228](228-ui-toybox-proposal.md) board 3 (Crystal Shop), built on the kit of [230](230-toybox-ui-kit.md) and on the price-on-button card of BD-1118 / BD-1144 (docs/202 R3, docs/213).

Labels: everything below is **CURRENT BUILD BEHAVIOR of the playtest profile once the card ids are bound**. The default build is unchanged.

## 1. The switch and the fallback

No new flag: the shop follows `Config.ToyboxUIEnabled` (default false, playtest true). The Toybox card is drawn only when the flag is on AND all six `toybox_card_*` ids are bound (`Theme.Toybox` exists and `ToyboxKit.ready(Slots.Images, "card")`, the group pattern of `ToyboxSkin`). Otherwise `Cards.build` falls through to today's code (the price card or the old card, whichever the other flag says). Client presentation only: no server, save, price, Robux or economy change; the price still only opens the confirm page.

## 2. What the card is (flag on, ids bound)

`src/client/ShopToyboxCard.luau` (drawing), `src/shared/ToyboxShop.luau` (pure rules), data from `ShopPreview.priceCard`:

- The whole card is the picture of its tier (`toybox_card_{common,uncommon,rare,epic,legendary,mythic}`, 9-slice rect of docs/230 s2, slice scale from `ToyboxKit.sliceScale`). An unknown rarity is Common.
- Name (white, 25 px) and the **Info** word (44 px target on screen, kept so the read-only details page stays reachable); under the name the rarity word in its tier colour on a small cream pill (a colour on the same colour would not read).
- A cream **art box** (clipped) with the item art; **slow rays** behind the art: three copies of the existing `shaftGradient` texture (`EffectAssets`), the fan turning once in 40 s, still under Reduce Motion, **left out while that texture is not uploaded** (no fallback drawing).
- The **benefit band** along the bottom of the art box ("Growth +15%", "Faster"); the **one wide button** (price with crystal icon / EQUIP / UNEQUIP / LEVEL n / SOLD OUT). Colours as BD-1144; the skin turns them into gloss buttons.
- The **equipped** card keeps its gold ring and gets a soft gold glow image behind it (existing `glowPlate`, only while uploaded).
- A **locked Legendary (or Mythic)** shows a "?" instead of the art and a short hint ("Reach level 30") in the band instead of the benefit. Only locked cards do this; an owned or buyable Legendary shows its picture. Today only trails can be locked (by account level); no real item is a locked Legendary, so the "?" is proven with a test item.
- The **confirm page** ("Buy X?"): the title is "Buy <name>?" and the cancel button says "NOT NOW"; price and balance lines, the BUY button and its action are unchanged. Same gate as the card (flag and bound ids), so the existing smokes see no change.

## 3. Not done, and why (OWNER QUESTION in docs/116 C-59)

- **Right-side tabs.** docs/228 shows the tabs on the right. The shop body is a fixed 824 x 402 box and every other page (Eggs, Conditions, Crystals, odds) is laid out over its full width, so a side column would overlap them; moving it needs a re-layout of all five pages. LEAD decision: the tabs stay in the top row (they already carry the existing tab icons and become gloss buttons through the skin). A follow-up row can re-lay-out the pages.
- **"Nests" tab.** The game has no Nests shop tab (tabs: Auras, Trails, Eggs, Conditions, Crystals; nests are claimed elsewhere and overflow into crystals, docs/72). Not invented.
- **"Find it in Volcano" hint.** There is no data saying where a Legendary comes from; the hint says only what the code knows (the account level a trail needs).
- **Real Legendary aura art** is an art task (the row says so); the card uses whatever `aura_<id>` / trail art exists.
- The card is 264 x (270 or the phone height) design px as today, with 10 px margins; the picture is a 256 x 320 render sliced to that box.

## 4. Tests

`python tools/verify_toybox_shop.py --runner <luau.exe>` (in CI): source guards (flag untouched, hook lines, the new files pure or presentation only, allowed instance classes, no asset id written), then the real `ShopScreens`, `ShopCards`, `ShopToyboxCard`, `ToyboxShop`, `ShopPreview`, `RarityWord`, `EffectAssets` in the geometry mock at the 12 window sizes, mouse and touch, Auras and Trails; flag off / ids unbound / one id missing = the old card and CANCEL; the question mark; the popup; 32 mutants. **Offline only: nothing is drawn.** Also run: `verify_toybox_ui`, `verify_shop_card_price`, `verify_menu_layout`, `verify_text_style`, `verify_small_window`.
