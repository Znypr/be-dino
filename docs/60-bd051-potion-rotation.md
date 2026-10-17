# BD-051: rotating Potion Shop (2-minute restock)

Status: Review / test. Studio and phone evidence pending. **Owner-approved 2026-10-14:** the shop restocks every **2 minutes** (this replaces the five-minute figure in [45 section D](45-owner-feedback-shop-hud-world-weather-tasks.md)).

## Rules (all PROVISIONAL, one block: `ProgressionConfig.PotionShop`)
| Setting | Value |
| --- | --- |
| `PeriodSeconds` | 120 |
| `OfferCount` | 3 distinct potions per window |
| `RarityWeights` | Common 60, Rare 30, Legendary 10 (relative; applied per draw without replacement) |
| `StockWeights` | stock 1/2/3 with weights 60/30/10 |
| Price | unchanged crystal price per potion; crystals only, no Robux, offers and stock are disclosed |

## Design
- **Window** = `floor(unixSeconds / PeriodSeconds)`. `ProgressionRules.shopOffers(window)` is a pure function (Park-Miller generator seeded from the window), so every server and every reconnect sees the same offers; nothing is stored or rerolled. This is the same shared-clock idea as `WeatherClock`, but stateless.
- **Stock is per player per window**, stored in `progression.shop = {window, bought={potionId=count}}` and validated by `Rules.valid`. A new window replaces the record, so stock resets without migration (additive field).
- **Purchase** reuses the `buyPotion` action with id `"<potionId>@<window>"`. Inside the existing `UpdateAsync` transaction (`ProfileRepository.progressionAction`) the server checks the window equals the current one (`stale_window`), the potion is offered (`not_offered`), stock remains (`sold_out`), inventory and crystals, then increments `bought`, debits crystals and adds the potion atomically. The idempotency token is the existing operation log: a replayed token returns `duplicate` without a second debit or stock use. A bare potion id is refused (`window_required`).
- **Owned potions and buffs are untouched by rotation**; "Your potions" lists everything owned for use even when it is not on offer.
- **Client** (`Bootstrap.client.luau`, potions panel only): derives the displayed offers from the shared rules and `workspace:GetServerTimeNow()`, shows "N left"/"Sold Out", a `Restock in M:SS` countdown, and a single "Potion Shop refreshed" toast when the open panel crosses a window. The server is authoritative; a purchase raced against a boundary gets `stale_window`.

## Tests
- `tools/verify_potion_shop.py` (CI): window math, determinism and rotation, distinct offers, stock bounds 1-3, stock and rarity weight ordering over 30,000 windows, every potion reachable, sold out, not offered, stale/future window, window reset, insufficient crystals/inventory not consuming stock, owned use independent of offers, persistence validation.
- `tools/verify_potion_purchase.py` (CI): the real `ProgressionAction` handler plus the unpublished-Studio memory profile, driven with the exact request the confirm button sends (`<potion>@<window>`): purchased / busy / duplicate token / stale window / sold out / use, ProgressionJson potions and shop stock change, the 1,000,000 test wallet stays pinned after a spend (by design: an unchanged counter in Studio is NOT a failed buy), every catalog potion buyable, ids within the 40 character remote limit; plus source checks that the BUY POTION handler calls `transact` before leaving the modal and that the result and ProgressionJson listeners re-render the shop (2026-10-17 lead Studio check).
- `tools/verify_progression.py`: repository-level duplicate token, stale window, bare id, sold out, and reconnect keeping stock. `tools/verify_load.py` and `tools/qa/shop-multiplayer.server.luau` use windowed ids.

## Risks and open items
- The server uses `os.time()` and the client `GetServerTimeNow()`; a tiny skew near a boundary can show a just-expired offer (rejected as `stale_window`, shop re-renders).
- A purchase at the exact boundary in the load/progression tests uses real time; a two-minute rollover mid-test could in theory flake.
- Weights, offer count and stock are placeholders pending balance review. Phone layout of the offers row plus owned-potion buttons needs Studio/device evidence.

## 2026-10-14 update: 12-potion catalog, 6 offers (docs/68)
`PotionShop` now has `OfferCount=6`, `MaxStock=3`, five rarities with `RarityWeights` Common 50 / Uncommon 28 / Rare 14 / Epic 6 / Legendary 2, and per-rarity `StockWeights` (Epic/Legendary stock is always 1). `Potions` grew from 6 to 12 (a new loot family); old ids and data are unchanged. Each slot rolls a rarity then a distinct potion; unrolled potions are `not_offered` that window. Window ids, `stale_window`/`not_offered`/`sold_out` and exactly-once purchase logic are unchanged. The rows above that list 3 offers, weights 60/30/10 and stock weights 60/30/10 are superseded by docs/68.
