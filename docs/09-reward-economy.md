# Reward economy specification
Updated 2026-09-17. Confirmed intent plus a reversible implementation proposal; no balance simulation has run yet.

## Confirmed
- Growth score and catch score are different. Catch score determines collection rewards.
- Manual ending or being eaten awards run dinosaurs immediately.
- Chests are additional and have a separate loot table.
- More catch score means more total copies. Higher rarity tiers award progressively fewer copies.
- The same species can appear many times; combine duplicates into one stack.
- Large-run examples can include 12 common species, each with roughly 12–50 copies. This is illustrative, not a guaranteed distribution or final catalog requirement.
- The desired diminishing pattern is across rarity tiers, not a required saturating chance curve per awarded dinosaur.

## Proposed calculation
Let c be a nonnegative integer catch score.
For the first simulation, N(c) = c: each additional catch guarantees one additional total dinosaur copy. c=0 yields no earned copies; the starter unlock is separate.
This conversion is a candidate, not an approved balance value. If one catch means many food pickups, tune catch accrual rather than confusing growth points with rewards.
Define maximum supported catch score and numeric bounds. A configured automatic run settlement at the limit is preferable to continuing play with a flat reward cap.

For eligible rarity tier r starting at zero, use weight w(r) = q^r, with trial q=0.25.
Eligibility thresholds are configuration, to be selected in BD-010. Higher tiers can become eligible at larger catch scores.
To guarantee nondecreasing per-tier quantities for a fixed eligible set, allocate N seats sequentially using largest w(r)/(allocated(r)+1), breaking ties toward lower rarity. This produces an approximately exponential tier distribution while preserving exact total quantity.
When eligibility changes, compare boundary outcomes explicitly. Total copies remain increasing, but individual tier counts need not.
For each tier, allocate its copies among eligible species using configurable species weights and server RNG. Aggregate identical species/mutation keys.

This approach fixes the tier budget for a given score/config and randomizes species allocation. If randomized tier counts are desired later, use a constrained method preserving total quantity and agreed tier ordering.
There is no hardcoded promise of a legendary at any specific score yet.

## Arithmetic example, not tuned gameplay
For N=1000 with five tiers already eligible, an approximately exponential budget is:
| Tier | Total copies |
|---|---:|
| Common | 751 |
| Uncommon | 187 |
| Rare | 47 |
| Epic | 12 |
| Legendary | 3 |
| Total | 1000 |

The common budget can be split across many species; a single result could include 56× Common X and 47× Common Y.
This is separate from the owner's illustrative 12-species range. The numbers above are not a prediction for a run with 1000 growth points.

## Three-species test and later expansion
Use three initial tiers/species to validate collection mechanics. Test large-stack UI with synthetic catalog fixtures, clearly marked test-only.
After the core loop works, expand catalog and eligible tiers through config and the asset manifest. Do not invent unseen species rewards to fill a table.

## Chest contract
Use independent ChestRewardConfig: chest types, grant-count distribution by catch score, contents, quantities, duration and capacity policy.
Do not assume the run table, example weights, or score conversion apply to chest contents.
The chest-count distribution is unresolved tuning, not a blocker for controller development.
Chest outcomes are generated once and stored with an operation ID, either on award or first valid claim; choose one in BD-005 and preserve it through retries.

## Mutation pacing risk
At 50 copies per upgrade, stacks of 12–50 copies can make a mutation attainable in one good run. This follows from the proposed numbers and must be intentional.
Simulate copies per species per hour and mutations per session before setting catch accrual. Do not silently change the 50-copy rule to compensate.
Higher rarity and mutation stats should remain bounded so starter players retain counterplay.

## Required verification, owned by GD and reviewed by QA
1. Integer nonnegative counts and exact sum of all stacks equals N(c).
2. For every supported adjacent score, N(c+1)>N(c); test eligibility boundaries separately.
3. Aggregate quantities decrease across rarity tiers in the intended design; top tiers remain scarce.
4. Seeded runs reproduce outcomes; retries of an operation return the stored outcome.
5. Unknown/ineligible species cannot drop; no empty tier divides by zero.
6. Multiple identical species aggregate correctly; large rewards have bounded payloads and UI work.
7. Simulate short/medium/long runs and report unlock/mutation pacing with assumptions.
8. Separate chest table demonstrably changes chest outcomes without changing run rewards.
9. No balance result or Roblox test is marked passed until executed and recorded.
