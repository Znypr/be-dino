# 89 Catch rate 4 per 500 food (BD-165, owner 2026-10-15)

Status: **HISTORICAL, superseded 2026-10-16 by [docs/119](119-catch-rate-15-per-run.md) (12/500)**. Was: **Review / test** (offline verifiers pass; Studio and phone checks pending). Supersedes [docs/59](59-egg-rate-40.md).

**Owner:** after 3-4 minutes and about 700 growth the owner got 52 catches and expected about 5. The conversion is now `FoodCatchRate = 4/500` (PROVISIONAL): **500 food -> 4 run eggs, 5,000 food -> 40**. Still one egg per catch and one dinosaur per hatched egg. Base species odds are unchanged.

## What changed
| Setting | Was (docs/59) | Now | Why |
| --- | --- | --- | --- |
| `Config.FoodCatchRate` | 40/500 | **4/500** | owner decision |
| `Config.RunEggMaxPerRun` | 500 | **50** (= 6,250 food) | a 5,000-food run (40 eggs) is not truncated |
| `Config.SpeciesRunBoost` | {1, 1.9, 4.7, 4.5, 4} | **{1, 1, 1.1, 1.1, 1.1}** | docs/88: rares must not get easier; adjacent tier ratios stay 0.33 / 0.15 / 0.22 / 0.14 |
| `Config.EggRarityBoostMaxEggs` | 400 | **40** | full boost at 5,000 food |
| `NestLuckTiers[1].rarityBoostEggs` | 200 | **40** | stays at full boost (now a mild effect by design) |
| `Config.NestMinCatches` / `NestEggsPerExtraNest` | 8 / 100 | **1 / 10** | same nest counts per run as before (4 eggs -> 1 nest, 40 eggs -> 3 = cap) |
| Crystals (`ProgressionConfig.RunCrystal*`) | 0.75/egg to 40, then 0.53 | **7.5/egg to 4, then 5.3** | per-run outputs unchanged: 4 eggs -> 30, 40 -> 220, 50 -> 273 |
| Account XP per run egg (`RewardMath.computeRunReward`) | 1 | **10** | per-run XP unchanged (500 food -> 40 XP) |
| `HatchPageSize`, `HatchRevealSeconds`, `RunEggBankCapacity`, `NestMaxPerRun` | 10, 1 s, 1000, 3 | unchanged | bank capacity left alone so existing saves cannot exceed it |

Side effect: a 1-egg run now gives 7 crystals (it gave 0).

## Simulation (100,000 runs each, the real species weights)
Expected eggs per run by tier, Common / Uncommon / Rare / Epic / Legendary:
| Run | Eggs | C | U | R | E | L | P(at least one Rare+) | P(Legendary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 food | 4 | 2.88 | 0.96 | 0.13 | 0.03 | 0.004 | 15.2% | 0.43% |
| 5,000 food | 40 | 28.7 | 9.55 | 1.40 | 0.31 | 0.044 | 83.1% | 4.3% |
Previous 40/500 rate for comparison: 500 food gave 2.1 Rare+ eggs (now 0.16); 5,000 food gave 54.6 (now 1.74). docs/88 target "below about 30% for a normal 5-egg run" is met (15%).

## Honest caveats
* **Fusion pacing is now 10x slower** (Gold = 15 Base of the same species + pattern). `tools/simulate_fusion_ladder.py` defaults were updated to 4 / 40 eggs per run; the ladder or egg sources need an owner review.
* Rare chance per egg is at most about 10% higher than the base odds at full boost. A smaller boost cannot make a short run "meaningful" without making rares easier; the owner decides if a different feel is wanted (docs/88 open questions).
* The old docs/09 sample of 213/133/45/9 for a big run is no longer reachable with 40 eggs; the 40-egg mix is about 29 / 10 / 1.4 / 0.3 / 0.04.
* The Eggs screen batch sizes and the Studio/phone feel are not verified.
