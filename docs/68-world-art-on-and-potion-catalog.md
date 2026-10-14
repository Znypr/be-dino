# 68: new world art ON in the playtest, and a 12-potion rotating catalog

Date: 2026-10-14. All numbers PROVISIONAL. Studio and phone evidence pending (the lead verifies live).

## 1. World and food art on in the playtest
The BD-049/050 kit (docs/56) was off by default, so the map still showed the old trees, ferns, rocks and food. `tools/release_profiles.py` now makes the **playtest** profile set `WorldArtMode="BiomeKit"`, `FoodArtMode="Kit"`, `WorldArtDensity=0.35`. The **default** profile now *requires* `Legacy`/`Legacy` (so a committed dev build cannot ship the kit by accident); `tools/verify_release.py`, `tests/test_release.py` and `tests/test_world_kit.py` check both.

### Part budget (native fallback = 2 wedge parts per triangle, plus invisible collider boxes)
| Scene | Parts |
| --- | --- |
| Legacy world props (34 trees x217, 72 rocks x41, 97 ferns x56) | ~15,800 |
| Legacy egg/amber food models (~77 eggs x100, ~31 amber x20) | ~8,300 |
| Kit at density 1 (188 placements, 8,990 tris) | 18,093 (the audit's ~18k phone risk) |
| **Kit at playtest density 0.35** (53 placements: 14 trees, 11 rocks, 17 shrubs, 7 cover, 4 landmarks; 3,144 tris) | **6,337** |
| Kit food models (cap 12 x <=120 parts) | <= 1,440 |
| **Kit total** | **7,777 (<= 8,000)** |
| Residual legacy dressing kept in kit mode: 16 boundary rocks (every third), 2 hub trees | ~1,100 |

Justification: the budget is about 1/3 of the old world+food parts, comfortably under the ~8,000 phone target, while the four landmarks and every tree/rock/shrub/cover family are still placed, so the old look is clearly replaced. Density only thins counts (grammar, clearances and seeds unchanged); MeshPart uploads remain the real fix.

### Food
Kit variants `food_{berry,fruit,egg,amber}_{a,b}` all exist and set the pickup `ArtId`. Berry/fruit keep their visible ball pickup (kit meshes need uploads); egg/amber get a kit model only on a deterministic stride (amber 1/4, egg 1/20) up to `Config.FoodKitVisualCap=12`, so no pickup is ever hidden without a visible replacement. +1/+4/+15/+50 and all server validation are unchanged (tests assert them).

### Tests
`tools/verify_world_art.py` now also runs the grammar against the playtest-rewritten Config: modes, density < 1, tree/rock/shrub/cover minimums, world parts <= 6,500, food parts <= 1,500, total <= 8,000, all 8 food variants present, plus static checks (egg/amber only, capped; food values; source default Legacy). It prints the legacy vs kit part counts.

## 2. Potion catalog: 12 potions, 5 rarities, 6 of 12 per restock
One config block: `ProgressionConfig.PotionShop` + `Potions`.

| Rarity | Potions (id: price, minutes, multiplier) | Slot weight | Stock |
| --- | --- | --- | --- |
| Common | speed 20/5/1.2, growth 25/5/1.25, loot 30/5/1.1 | 50 | 1-3 (60/30/10) |
| Uncommon | speed 38/7.5/1.3, growth 48/7.5/1.4 | 28 | 1-3 |
| Rare | speed 65/10/1.45, growth 80/10/1.6, loot 95/10/1.25 | 14 | 1-3 |
| Epic | growth 135/12.5/1.8, loot 170/12.5/1.4 | 6 | 1 |
| Legendary | speed 180/15/1.75, growth 220/15/2.0 | 2 | 1 |

- Price bands never overlap (max of a rarity < min of the next) and rise with duration and power in each family. The loot family is new: it multiplies the same loot value as weather (`Rules.multipliers`), so it increases food-catch eggs; balance is unreviewed.
- **Design choice:** six slots, each rolls a rarity from the weights (rarities with no potions left are skipped), then a distinct potion of that rarity. The other six potions are simply *not offered* that window (server answers `not_offered`), instead of dimmed placeholder cards: the grid stays full and clear. A hint reads "Rarer potions appear less often. Six of twelve are offered each restock." A sold-out offer still shows a dimmed "Sold Out - back later" card.
- Unchanged from docs/60: window = `floor(time/120)`, id `potion@window`, `stale_window`, `not_offered`, `sold_out`, `window_required`, exactly-once via the operation log, per-player-per-window stock in `progression.shop`.
- **Migration:** no data rewrite is needed. The six old ids (`speed|growth` x `common|rare|legendary`) keep their ids, rarities and stats, so owned potions, active buffs and an old `shop` record stay valid (`bought` count limit is `MaxStock=3`). Tests cover an old profile.
- **Client** (potions panel only): 3x2 rarity-tinted cards (Common grey, Uncommon green, Rare blue, Epic purple, Legendary gold), inside one scroll frame together with the hint and the owned-potion list, so it fits the 860x520 panel at phone-landscape scale and on desktop. Loot potions reuse the growth bottle art until a loot bottle exists.

Tests: `tools/verify_potion_shop.py` (catalog validity, naming, price ordering, determinism, 30,000-window rarity/per-potion frequency, legendary window rate between 2% and 20%, stock bounds with epic/legendary = 1, 6 distinct offers, purchase rules, migration, loot buff) and `tools/verify_progression.py` (every potion usable and buff kind validated).

## Studio checks to run
1. Playtest place: output `WorldKitMissing=0`, `WorldKitPlacements=53`, `WorldKitTriangles=3144`; count BaseParts under `BeDinoArena` and `Food` (expect roughly 8-9k including terrain-less props) and watch frame rate and memory on a real phone.
2. Walk all 6 paths and the starter area: no kit prop blocks a path; collision boxes match; spawn meadow clear.
3. Confirm berries/fruit still visible and collectable, +1/+4/+15/+50 awarded, eggs/amber show kit models and respawn.
4. Potion Shop on phone landscape and desktop: 6 cards visible/scroll, hint readable, owned list scrolls, buy each rarity, sold out card, restock toast; use a loot potion and check the HUD Loot value.
5. Load a profile saved before this change and check owned potions and an active buff.

## Risks
- Density 0.35 is sparse (14 trees on a 460-wide map); raise it once MeshParts are uploaded.
- The legacy part counts are static estimates, not a Studio measurement.
- Loot potions and the new prices are untuned; native part total still excludes terrain and hub.
