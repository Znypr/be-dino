# 128 Food-only progression audit (owner correction 2026-10-16)

**OWNER CORRECTION:** "PvP is an optional side" means hunting other players is each player's own choice and **food alone must give enough progression** (growth, eggs, crystals). It did NOT mean a Peaceful opt-out; Peaceful (BD-421) is removed, see [115](115-decisions-log.md). Hunting stays on for everyone.

Status: audit of CURRENT BUILD BEHAVIOR, numbers read from `src/shared/Config.luau`, `ProgressionConfig.luau`, `RewardMath.luau`, `PredationService.luau`. Proposals below are PROVISIONAL and NOT applied.

## 1. What food gives (current)
| Item | Value | Source |
| --- | --- | --- |
| Eggs per food | `FoodCatchRate = 12/500` = 0.024 egg per food point (1 egg = about 42 food) | Config, docs/119 |
| Growth per food | `GrowthPerFood = 0.1` | Config (BD-386) |
| Normal 5-minute run | 600-700 food = about 15 eggs, about 65 growth | docs/119 |
| Crystals per run | 2.5 per egg up to 12 eggs, then 1.76 per egg, cap 300 (15 eggs = 35) | RewardMath.runCrystals |
| Nests | 1 qualified nest, +1 per 30 further eggs | `NestEggsPerExtraNest` |

## 2. What eating a player gives (current, legacy instant eat rule, `CombatEnabled=false`)
- **+1 run egg** per eaten player (`awardCatch`, multiplied by the weather loot multiplier, at least 1), limited only by the 60 s repeat-victim cooldown per victim. One egg is worth about **42 food points**.
- **+2.5 growth** (`PredationGrowthPoints`), the same as about 25 food points of growth.
- Crystals and nests follow the egg count, so one kill adds about 2.5 crystals (1.76 past 12 eggs) and pushes toward the next nest.
- No kill gives crystals or items directly. NPC predator defeats (combat flag) give only growth: at most 5% of the killer's own growth, 3 rewards per 5 minutes, the same slot not again for 120 s. That is fine and not outsized.

## 3. Verdict
- **A food-only player is fine.** Growth, eggs, crystals and nests all come from food (15 eggs, 35 crystals, 1 nest in a normal run). Nothing is locked behind kills.
- **Kills are outsized for eggs.** One kill is worth about 42 food, about 20 seconds of a normal 130-food-per-minute pace. 5 kills add about a third more eggs, 15 kills double a run (the cap is 150 eggs, `RunEggMaxPerRun`). Growth from a kill is small next to food (2.5 against about 65 per run) and is not the problem.
- The eaten player keeps all their eggs (BD-422), so a kill is a pure bonus for the hunter.

## 4. Proposal (provisional, NOT applied, owner to confirm; BD-438)
Pick one:
- **A (preferred):** kills give growth only (`PredationGrowthPoints` stays 2.5, no egg). Hunting stays fun for size, food is the one egg source.
- **B:** kills give a small egg share: `PredationCatchEggs = 0.25` egg per kill (about 10 food) using the same carry idea as `FoodCatchRules`, capped at **3 kill eggs per run** (about 20% of a 15-egg run).

Either way, keep the weather loot multiplier off kills, keep the 60 s repeat-victim cooldown, and re-measure with a Studio food-per-minute run before locking. Do not change `FoodCatchRate`, nests or crystal formulas for this.
