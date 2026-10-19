# 213 The shop card with the price on the button (BD-1118 / BD-1144, R3 of docs/202)

Written 2026-10-19. Label: **CURRENT BUILD behind a flag**, proved **offline only** (a layout mock and pure words, no Studio, no phone). Source: [docs/202](202-ui-standards-from-steal-an-egg-and-ride-a-dino.md) section 4 and R3 ("card = art, name, ONE benefit line, ONE wide button with the price written on it; details and odds behind an Info word; sold out is a grey button"). The Studio look is the new row BD-1160. The default build is unchanged.

## 1. What a player sees (flag on = the playtest build)

Only the Aura and Trail cards of the Crystal Shops change. The Eggs, Conditions, Crystals and Potion pages are as before.

| | Before (flag off, Build 020 look) | Now (`ShopCardPriceButtonEnabled` on) |
| --- | --- | --- |
| Top row | name, then two chips (rarity, tier or level) | **the name in its rarity colour** (grey, green, blue, purple, gold: the one palette of docs/114) and an **Info** button |
| Picture | a stage about a third of the card | the stage takes **more than half the card** on a desktop window; the benefit ("Growth +15%", "Faster") sits as a **dark band along its bottom** |
| Under the picture | the benefit line, then a price caption ("470 Crystals" / "Owned" / "Equipped") | nothing: the price moved onto the button |
| Button | BUY / EQUIP / UNEQUIP / LEVEL 3, 240 px wide | **one button as wide as the card**: **"470 Crystals"** with the crystal icon while it can be bought (green); **EQUIP** (green) when owned; **UNEQUIP** (card colour) on the equipped one; **LEVEL 3** (grey) on a locked trail, no price; SOLD OUT (grey) |
| Details | on the card (chips) | behind **Info**: a read-only page with the name in its rarity colour, the benefit, "Rare aura" (the rarity word coloured), "Needs level 3" for a trail, then "470 Crystals" / "You own this" / "On your dino now", and a **BACK** button. **No buy button there.** |
| Equipped ring | gold ring around the card | unchanged |

What a tap does is unchanged: the price button opens the **same confirm page** ("Buy Aura?" with BUY AURA and CANCEL) and nothing is sent to the server before BUY there. EQUIP / UNEQUIP still send the equip action. A locked trail still answers with the level note. No Robux and no crystal-pack change.

## 2. Where it lives

| Thing | File |
| --- | --- |
| The words and the button state (pure, no Instances) | `src/shared/ShopPreview.luau`: `P.priceCard(data, item, isTrail)` -> name, rarity, benefit, button {text, tone, active}; `P.infoLines(item, isTrail, info, growthText)` -> the lines of the details page; `P.InfoWord` |
| The card | `src/client/ShopCards.luau`: `Cards.buildPrice`; `Cards.build` hands over to it when the flag is on |
| The details page | `src/client/ShopScreens.luau`: page `auraInfo` (in `Shop.names`); the card spec gains `onInfo` |
| The flag | `Config.ShopCardPriceButtonEnabled`: false in Config and in the default profile, true in the playtest profile ([157](157-playtest-profile-newest-features.md)), in the rehearsal list |

Sizes: the Info button is at least 44 px on screen (it grows with the window scale like the other buttons of BD-1103); the one wide button keeps the height the shop already computes (`targetHeight`); the name is 25 px, the Info word 20 px, the benefit 20 px (all at or above the 16 px card floor of docs/202 R4 on a desktop window, 14 px in a small window). The crystal icon on the price button is the existing `amber` art; a `UIPadding` keeps the price text off the icon.

## 3. Evidence (offline, not Studio)

- `tools/verify_shop_preview.py`: the pure rules (price / EQUIP / UNEQUIP / LEVEL n / SOLD OUT, the info lines, kid words).
- `tools/verify_shop_card_price.py` (`tools/shop_card_price_smoke.luau`): the real ShopScreens, ShopCards, ShopCard, ShopPreview, RarityWord, ModalCompact and PhoneScale in the geometry mock at the 12 window sizes of the small-window check, mouse and touch, Auras and Trails: no chips, name in its tier colour, Info >= 44 px, stage > half the card (desktop) and never under the button, the benefit band with the real words, one button as wide as the card with the right text and colour, no price caption; the tap paths (price -> confirm page, nothing sent; BUY -> one `buyAura`; Info -> read-only page with no buy button; BACK; a locked trail stays). 21 mutants put each defect back and are caught.
- `tools/verify_menu_layout.py` runs its sweep a third time with the flag on (tabs, toasts, first rows); `tools/verify_text_style.py` runs the text-floor smoke with the flag on too and covers the `auraInfo` page.
- `tests/test_release.py`, `tests/test_rehearsal.py`: the flag is off in the default build and on in the playtest build.

NOT checked: how it draws in Studio (the icon on the button, the band over a real preview, the name at real size), a phone. Row BD-1160.

## 4. Open and follow-ups

- Eggs and Potions cards (BD-1118 says "one component for Auras, Trails, Eggs, Potions"): not in this change; the potion card keeps its BD-1103 layout. A follow-up can reuse `P.priceCard` once the potion stock ("3 left") has a place on the button or the band.
- The old card stays in code for the default build; remove it after the Studio look and the owner's OK.
- To overturn: set the playtest rule of `ShopCardPriceButtonEnabled` to false (one line in `tools/release_profiles.py`).
