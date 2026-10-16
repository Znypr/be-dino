# 119 About 15 run eggs per normal 5-minute run (BD-418, owner 2026-10-16)

Status: **Review / test. PROVISIONAL: the food-per-minute figure is an estimate and needs a Studio measurement.** Supersedes [docs/89](89-catch-rate-4.md) (4/500, now HISTORICAL; 40/500 of [docs/59](59-egg-rate-40.md) is also HISTORICAL).

**OWNER DECISION:** a normal 5-minute run should give about 15 run eggs. `GrowthPerFood` (dino size only, BD-386) is unrelated and untouched; eggs still use raw food points.

## 1. Estimate: food per minute for a normal player (PROVISIONAL)
Inputs from source and docs: 22 studs/s walk speed, pickup radius 2.25, 8 pickups per cluster (radius 7), 400 clusters = 3,200 pickups, 8 s respawn; docs/90 assumed about 600 food per 5 minutes before the food boost; PR #223 (reported by the owner's lead) raised average points per pickup to 4.05 and pickups by 12.5%.

Method (rough, not measured):
1. A player who heads for the next cluster spends about 12 s per cluster (travel plus sweeping 8 pickups). That is about 5 clusters/min, about 40 pickups/min.
2. 40 pickups/min x 4.05 points = about 160 food/min if the player never stops.
3. Real play includes fleeing, fighting, menus and wandering. Take 75-85% efficiency: about 120-135 food/min.
4. Cross-check against docs/90: 600 per 5 min x 1.125 (more pickups) x about 1.0-1.1 (richer mix) = 675-745 per 5 min = 135-150 food/min.

Working figure: **about 600-700 food per 5 minutes (about 120-140 food/min)**. A fast, focused player may reach 800+; an idle one 300. **Measure in Studio** (log `LastRunFood` over several real 5-minute runs) and retune.

## 2. Rate
Target 15 eggs at about 650 food gives 15/650 = 2.3 per 100 food. Chosen: **`FoodCatchRate = 12/500` (0.024 per food)**: 600 food -> 14.4, 650 -> 15.6, 700 -> 16.8. Rounded to a clean 12 per 500; 500 food -> 12, 5,000 -> 120.

## 3. What was rescaled so everything else stays about the same per food
| Setting | Was (docs/89) | Now | Why |
| --- | --- | --- | --- |
| `FoodCatchRate` | 4/500 | **12/500** | owner decision |
| `RunEggMaxPerRun` | 50 | **150** (= 6,250 food) | a 5,000-food run (120 eggs) is not truncated; bank capacity 1000 still leaves 850 free for the start gate |
| `NestEggsPerExtraNest` | 10 | **30** | 30 eggs = 1,250 food, the same as 10 eggs before: nests per food unchanged (12 eggs -> 1 nest, 120 -> 3 = cap) |
| `EggRarityBoostMaxEggs`, nest `rarityBoostEggs` | 40 | **120** | full run-size boost still at 5,000 food |
| Crystals | 7.5/egg to 4, then 5.3 | **2.5/egg to 12, then 1.76** | per-run outputs unchanged: 12 eggs -> 30, 120 -> 220, 150 -> 272 |
| Account XP per egg | 10 | **10/3 (floor)** | 12 eggs -> 40 XP (500 food = 40 XP, unchanged) |
UI: the Home guide text "Eat 500 food to earn %d eggs" reads the rate, so it now says 12.

## 4. Consequences the owner should know
* Per-egg species odds are unchanged, so Rare+ eggs per run triple: a 12-egg run holds a Rare+ egg about 40% of the time (was about 15%; docs/88 aimed under 30% at 4 eggs). Per-egg rarity can be made harder later if wanted.
* Fusion pacing ([docs/90](90-fusion-ladder-v2.md)) gets about 3x faster per run; `tools/simulate_fusion_ladder.py` defaults (4 eggs per run) were not re-tuned and need an owner review.
* One run now yields 12+ eggs against a queue of 5: the rest go to the run egg bank (up to 1000), revealed one at a time; reveal time and UI for 12-15 eggs need a Studio/phone check.
* Existing saves are not rewritten.
