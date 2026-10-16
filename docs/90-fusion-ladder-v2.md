# 90 Fusion ladder v2, growth pace and nest size (owner decisions 2026-10-15)

Status: **Review / test** (offline verifiers pass; Studio and phone checks pending). OWNER TARGET is the owner's list of 2026-10-15; every number is PROVISIONAL and labelled. Supersedes the ladder of [docs/58](58-fusion-ladder-50-10-3.md) (15 / 4 / 2) and the options in [docs/57](57-fusion-ladder-options.md).

## 1. Why the old ladder broke
After the catch-rate change ([docs/89](89-catch-rate-4.md): 4 eggs per 500 food) a casual run gives about 4 eggs, about 2.4 dinosaurs (60% hatch success). The old Gold (15 Base of the **same species and same pattern**, 22 species x 8 patterns = 176 cells) needed a **median of about 123 casual runs** for the first Gold of any Common cell and about 3,200 runs for a Rare species; Diamond was out of reach.

## 2. New ladder (implemented)
| Step | Recipe | Same species | Same pattern |
| --- | --- | --- | --- |
| Gold | **6 Base** | yes | **no (any pattern)** |
| Emerald | **3 Gold** | yes | yes |
| Diamond | **2 Emerald** | yes | yes |

* The first step is relaxed because patterns multiply the cells by 8. **Pattern of the Gold = the most common pattern among the 6 donors; ties go to the smallest pattern id** (deterministic, no RNG; the quote shows it, the client says "the most common pattern among your dinos"). The Gold's pattern is then fixed for Emerald and Diamond, so collecting the same pattern still matters at the upper steps.
* Everything else is unchanged: all donors are consumed into ONE NEW instance, the stage is guaranteed, colours / Shiny / BIG / mutation are freshly rolled, no cosmetics survive, itemized loss warnings and consent, quote at exactly N donors.
* **Odds stay honest:** `FusionOdds` already normalizes by the actual donor count N (Shiny = 0.5 x shinyDonors / N, etc.), so with N = 6 / 3 / 2 each valuable donor moves the odds more (1 Shiny of 6 = 8.33%, of 3 = 16.7%, of 2 = 25%). The quoted numbers still come from the same function that rolls the result; verifiers check sampling parity. Still PROVISIONAL (owner may want the 0.5 coefficient lowered because each donor now matters more).
* Lineage: a Gold stores one snapshot per parent; a parent whose pattern differs from the Gold's keeps its own `genes.patternId` in the snapshot (others rely on the shared pattern), so ancestry stays truthful.
* Code: `IdentityFusion.Recipes` (`anyPattern = true` for Gold; versions `gold-same-species-6-v2`, `emerald-same-species-pattern-3-v2`, `diamond-same-species-pattern-2-v2`; `Version = bd057-ladder-6-3-2`; `MaxDonorCount = 6`), `FusionService.MaxDonorIds = 6`, `Identity.MaxFusionParents = 6`, client `FusionSelection.Stages` / `NextGoal.Stages` (the HUD goal line counts Gold per species), Fusion Menu copy. Old-recipe quotes cannot be replayed (version strings changed); the playtest store has none.

## 3. Simulation (`python tools/simulate_fusion_ladder.py`, model not measured gameplay)
Model: casual player, 4 eggs per run, hatch success 60%, 22 species by `Config.ChestSpeciesWeights`, 8 equally likely patterns, 15 runs per hour (4 minutes each), greedy donor choice (the best-stocked pattern is fused first), no trading, no nests, no pattern research. Median over 60 simulated players, cap 12,000 runs.

**Ladder 6 / 3 / 2 (implemented), median runs (hours of 4-minute runs):**
| Target | First Gold | First Emerald | First Diamond |
| --- | ---: | ---: | ---: |
| any one of the 5 Common species | 8 (0.5 h) | 67 (4.5 h) | 190 (12.7 h) |
| Compy (Common, 26%) | 10 (0.7 h) | 73 (4.9 h) | 202 (13.5 h) |
| Stegosaurus (Uncommon, 6%) | 38 (2.5 h) | 359 (24 h) | 928 (62 h) |
| Triceratops (Rare, 1%) | 253 (17 h) | 2,063 (138 h) | 5,612 (374 h) |

Targets met: first Gold of a Common in about 5-10 casual runs (8 / 10); Common Diamond in about 13 hours of pure run time, which is roughly a day or two of real playing time once menus and waiting are included; rarer species are proportionally slower and still reachable (Rare Gold in about 17 h, Rare Diamond is a long-term goal of hundreds of hours without nests). Legendary species (weight under 0.2%) are practically only reachable through nest luck, purchases or future sources.

**Comparison (same tool, 30 players):**
| Ladder | any Common Gold / Emerald / Diamond (runs) | Triceratops Gold / Emerald / Diamond (runs) |
| --- | --- | --- |
| 15 / 4 / 2 same pattern (old) | 123 / 631 / 1,356 | 3,176 / over 12,000 / over 12,000 |
| 6 / 3 / 2 same pattern at every step | 34 / 162 / 349 | 1,003 / 4,067 / 9,105 |
| 6 / 4 / 2, any-pattern Gold | 8 / 115 / 286 | 260 / 3,177 / 8,175 |
| **6 / 3 / 2, any-pattern Gold (chosen)** | **8 / 67 / 190** | **253 / 2,063 / 5,612** |

Option for the owner: **6 / 4 / 2** makes Common Diamond about 19 hours instead of 13 (roughly 20-25 percent more effort at Emerald); it is a three-number change (`IdentityFusion.Recipes`, `FusionSelection.Stages`, `NextGoal.Stages`) plus the tests.

**With nests (not in the table above):** a nest adds 6-12 eggs (section 5). Simulating one step as "a run plus one 9-egg nest" (13 eggs per step, about 3 steps a day) gives a median of 3 / 21 / 59 steps for Common Gold / Emerald / Diamond, i.e. about 1 day / 1 week / 3 weeks, and 12 / 111 / 286 steps for Stegosaurus. This is the realistic pace for a player who returns to open nests; the owner may want the nest egg count or the ladder tuned if that feels too fast.

**What could not be verified:** real players do not pick donors greedily (so they are slower), do not play exactly 4 eggs per run (a longer or better run gives more), nest luck and Shiny/BIG duplicates are ignored, patterns are assumed uniform, and no Studio or phone session has exercised the new Gold UI (6 slots, any pattern). The model is Monte Carlo with fixed seeds (`--check` pins the key numbers).

## 4. Growth pace (owner: dinos grow too big too fast)
`Config.GrowthPerFood = 0.5` (new): `FoodService` now calls `addGrowth(candidate.gained * GrowthPerFood)`; `Config.PredationGrowthPoints` 25 -> 12.5. **Catches and eggs still use raw food** (`FoodCatchRules.award(candidate.gained, ...)`), so the run reward (4 eggs per 500 food) is unchanged. A typical 4-minute run that ended near 700 growth now ends near 350 (the owner asked for about 300; the factor is exactly half, a single number to tune further). Size curve `scale = min(4, sqrt(1 + growth / 50))` is unchanged and continuous: 350 growth is scale about 2.8 (was the cap of 4 at 750 growth); the cap now needs about 1,500 food. Growth multipliers (potions, weather, admin) still multiply the halved value; `GrowthCap = 8` is the cap on those multipliers and keeps its meaning. Predator-versus-prey size comparison uses growth on both sides, so it stays consistent. Checked by `verify_gameplay.py` (config values and that eggs still use raw food) and `verify_visual_growth.py` (scale changes are smooth). The HUD "+n" pickup pop shows the halved number.

## 5. Nests (owner: nests may out-produce run eggs because they wait hours)
`NestMinSize/NestMaxSize` 10-15 -> **6-12** (average 9). Kept: 5 storage slots, 3 hours each, one incubating at a time, drop gate (120 s and 1 catch), up to 3 nests per run. A run gives 4 eggs, a nest gives about 9, so over a day a returning player gets far more eggs from nests (3 openings = about 27 eggs) than from 3 runs (about 12), which is what the owner wants as a reason to come back; the 5-slot / 3-hour cap bounds it to at most about 8 nests (about 72 eggs) a day. Luck is unchanged (+2 condition levels on the egg, Shiny 3%, BIG 20%, full run-size species boost) and stays mild on species rarity: with `SpeciesRunBoost = {1, 1, 1.1, 1.1, 1.1}` the species odds are barely lifted so the exponential tiers of [docs/88](88-exponential-rarity.md) are not flattened; a stronger nest-specific rarity bump belongs to the `RarityCurve` work (BD-184) and was deliberately not touched here. See [docs/71](71-egg-nests-v2.md).

## 6. Not changed on purpose
Weather, species / colour / potion odds (RarityCurve work), crystals, bank capacity, Cracked eggs (still 50% at tier 0 with 20% hatch success: a Kanban row asks for a real feel test in a normal unboosted run).

## 7. Tests and tools
`tools/verify_fusion.py` (6/3/2 chain, wrong counts, mixed-pattern Gold plurality / tie / lineage, species and pattern mismatches at Emerald and Diamond, consent, rollback, odds N), `verify_fusion_ui.py` and `fusion_ui_smoke.luau` (6 slots, auto-fill ignoring pattern for Gold only, recipe parity), `verify_next_goal.py`, `verify_progression.py`, `verify_nests.py` (6-12), `verify_gameplay.py` (growth pace), `tools/simulate_fusion_ladder.py --check` (recipe parity with the code and pacing bands).


## 6. Growth 5x slower (BD-386, owner playtest 2026-10-16)
`Config.GrowthPerFood` 0.5 -> **0.1** and `Config.PredationGrowthPoints` 12.5 -> **2.5**. Eggs are untouched: `FoodCatchRules.award` still uses raw food points (4 eggs per 500), so eggs per run do not change (`verify_gameplay.py` asserts `FoodCatchRate == 4/500` and the raw-food call). Colour/growth multipliers still multiply the new number, so tiers stay relative. The size curve `scale = min(4, sqrt(1 + growth / 50))` is unchanged.

| Food eaten | Growth before | Scale before | Growth now | Scale now |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 50 | 1.41 | 10 | 1.10 |
| 500 (a normal 5 minute run) | 250 | 2.45 | 50 | 1.41 |
| 1,000 | 500 | 3.32 | 100 | 1.73 |
| size cap 4.0 | 750 growth = 1,500 food | | 750 growth = 7,500 food | |

The HUD SIZE bar (`HudRules.barFill`) is now measured against `BarFullGrowth = 60` (about 600 food, a normal 5 minute run) instead of the 4x cap, otherwise it would sit near empty all run; the dino body still follows `sizeFor`. Phone budget is unaffected (smaller dinos are cheaper). Food density went up in BD-387 (+33% pickups), which also raises food per minute and so eggs per minute slightly; that is the owner's "more food" request, not a rate change.
