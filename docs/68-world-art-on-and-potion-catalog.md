# 68: new world art ON in the playtest, and a 12-potion rotating catalog

Date: 2026-10-14. All numbers PROVISIONAL. Studio and phone evidence pending (the lead verifies live).

## 1. World and food art on in the playtest
The BD-049/050 kit (docs/56) was off by default, so the map still showed the old trees, ferns, rocks and food. `tools/release_profiles.py` now makes the **playtest** profile set `WorldArtMode="BiomeKit"`, `FoodArtMode="Kit"`, `WorldArtDensity=0.35`. The **default** profile now *requires* `Legacy`/`Legacy` (so a committed dev build cannot ship the kit by accident); `tools/verify_release.py`, `tests/test_release.py` and `tests/test_world_kit.py` check both.

### Part budget, MeshPart era (2026-10-15, supersedes the native-fallback numbers)
The 40 uploaded kit meshes (`resources/worldkit-meshes/mesh-bindings.json` -> `src/shared/WorldKitMeshAssets.luau` via `tools/bind_worldkit_meshes.py`) load at server start as real MeshParts (`AssetService:CreateMeshPartAsync`, size = imported size x scale, white colour so the mesh vertex colours show the kit palette, anchored, no collision). One prop = 1 part (+ its invisible collider boxes). `world_tree_dead_m` is not uploaded: it is swapped for another dead-tree size, and an id without a mesh would cost the native fallback (2 wedges per triangle) in the budget. Food pickups in Kit mode are the berry/fruit/egg/amber MeshParts themselves (replace the ball, no extra part).

| Scene (playtest, density 1.25) | Parts |
| --- | --- |
| Kit props: 1,257 placements (162 trees, 100 rocks, 475 shrubs, 516 cover, 4 landmarks) + colliders | 1,608 |
| Food pickups (16 x 16 sectors x 6, one MeshPart each) | 1,536 |
| Legacy dressing kept in kit mode (boundary rocks, hub trees) | ~1,100 |
| **Total (phone ceiling 8,000 kept)** | **~4,244** (Studio play measured 5,632 BaseParts incl. hub, terrain props and weather) |

`BiomePlacement.PartBudget = 3200` at density 1 replaces `TriangleBudget` (it scales with density; layer caps are 130 trees, 80 rocks, 380 shrubs, 620 cover at density 1). Before this change the playtest placed ~45 props at density 0.35. `tools/verify_world_art.py` (now in CI) enforces prop minimums, world parts <= 4,500, total <= 8,000, and that with no meshes loaded the budget thins the world instead of exploding.

### Food
All eight `food_{berry,fruit,egg,amber}_{a,b}` variants are used. Each pickup is the MeshPart scaled so its longest side equals the old ball diameter; +1/+4/+15/+50, server validation and hidden/respawn mirroring are unchanged. If a mesh is missing the old ball (and capped native egg/amber model) is used.

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
- **Client** (potions panel only): 3x2 rarity-tinted cards (Common grey, Uncommon green, Rare blue, Epic purple, Legendary gold), inside one scroll frame together with the hint and the owned-potion list, so it fits the 860x520 panel at phone-landscape scale and on desktop. Potion icons are native vector bottles (`src/shared/PotionArt.luau`, id `potion_<kind>_<Rarity>`) with no symbol overlay on the glass: speed = tall slim cyan flask, growth = round green flask, loot = wide amber jar; rarity = cork and trim colour, glow plate strength (none for Common, rim for Epic/Legendary) and 1-5 pips under the bottle. The old `potion_speed`/`potion_growth` navigation tile art is untouched. `tools/verify_artwork.py` asserts all 12 icons build with no native symbol call and are pairwise distinct. Needs a Studio look at 64 px and phone size.

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

## World v2 (2026-10-15, owner feedback: trim vegetation, patchy looping grass, tiny trees, small map)
All numbers PROVISIONAL. Branch `claude/world-v2`.
- **Map:** `ArenaHalfWidth` 260 -> **416** (832 x 832, 1.6x wide, 2.56x area). `IslandLayout.Scale = 1.6` scales peaks, meadow and edge ramp (gentler slopes; steepest authored slope still < 46 deg); added rolling hills and marsh basins with decorative water discs (`IslandLayout.Pools`). Food: 20 x 20 sectors x 6 = 2,400 pickups (was 16 x 16). Crystal pickups 64 -> 100 over the full island, now one MeshPart each (the legacy amber model was 21 parts x 64). Hub moved to `Config.SanctuaryCenterZ` = 521.
- **Sub-biomes** (`src/shared/BiomeMap.luau`, seeded by `WorldArtSeed`, warped blobs + per-biome noise, sharpened weights; terrain and props dither between biomes by weight so borders are mixed bands): Meadow (13%), Fern Forest (33%), Conifer Highlands (24%), Marsh (8%), Rocky Badlands (10%), Volcanic Slopes (11%). Each has its own terrain materials/colours (Grass, LeafyGrass, Mud, Ground, Sand, Sandstone, Slate, Basalt, CrackedLava veins) and kit mix.
- **Scale classes:** trees 0.95-1.5x, **giants 2.4-4x** (conifer_l up to 105 studs; canopy/cycad/dead; giant boulders and spires in the badlands/volcano), only >= 150 studs from spawn, colliders scale with the mesh. Measured: a compy at max growth (x4) is ~22 studs tall, the old tallest tree ~26-29.
- **Density:** playtest `WorldArtDensity` 1.25 keeps; layers tree/giant/log/rock/shrub/groundcover; 3,551 placements (614 trees, 48 giants, 56 fallen logs (dead trees on their side), 187 rocks, 1,125 shrubs, 1,517 cover) = 4,625 kit parts (`PartBudget` 3,700 at density 1).
- **Grass:** terrain no longer one Grass colour (material mix + colours by biome, dappled by 2-octave noise); Terrain Decoration on; ground cover is clustered by a patch noise field with 1-2 companions per tuft, flower meadows from a bloom field, random yaw/scale 1.7-2.9x, no grid.
- **Budget (Studio measured, playtest):** ~7,384 BaseParts client side (4,625 kit + 2,375 food + ~400 other) under the 8,000 ceiling. `verify_world_art.py` asserts world <= 5,000, food <= 2,600, total <= 8,000 with 600 other.
- **Haze:** server creates a gentle `WorldHaze` Atmosphere (density .22, haze 1.15); WeatherVisuals adopts it as its base.
