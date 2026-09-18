# Reward economy specification
Updated 2026-09-17. Confirmed reward intent plus the private-alpha mechanics-test configuration. Public launch balance remains intentionally unapproved.

## Confirmed
- Growth score and catch score are different. Catch score determines collection rewards.
- Manual ending or being eaten awards run dinosaurs immediately.
- Chests are additional and have a separate loot table.
- More catch score means more total copies. Higher rarity tiers award progressively fewer copies.
- The same species can appear many times; combine duplicates into one stack.
- Large-run examples can include many Common species with double-digit duplicate stacks. That is directional, not a guaranteed distribution.
- The diminishing pattern is across rarity tiers, not a required saturating chance curve per awarded dinosaur.

## Private-alpha run-reward configuration
For mechanics testing, let `c` be an integer catch score from 0 through 5000.

- Total immediate copies: `N(c) = c`.
- Reaching 5000 should end/settle the run rather than flatten rewards.
- Rarity weights: `w(r) = 0.25^r`.
- Eligibility thresholds: Common 1, Uncommon 25, Rare 100, Epic 400, Legendary 1600.
- Allocate `N(c)` seats sequentially using the largest value of `w(r)/(allocated(r)+1)`, breaking ties toward lower rarity.
- The exact total therefore remains `N(c)`, and aggregate quantities decline by rarity.
- The three-species alpha only has real species for the first three tiers. Epic/Legendary rows are synthetic fixtures until matching catalog entries exist.
- Species allocation occurs only among configured eligible species, with server RNG, then duplicate species/mutation keys are aggregated before persistence/UI.

This is not a promise that one catch should equal one copy at public launch. It is a deliberately transparent test conversion.

## Deterministic examples
| Catch score | Tier allocation |
|---:|---|
| 25 | 20 Common, 5 Uncommon |
| 62 | 50 Common, 12 Uncommon |
| 100 | 77 Common, 19 Uncommon, 4 Rare |
| 400 | 303 Common, 75 Uncommon, 18 Rare, 4 Epic |
| 1000 | 754 Common, 188 Uncommon, 47 Rare, 11 Epic |
| 1600 | 1203 Common, 300 Uncommon, 75 Rare, 18 Epic, 4 Legendary |
| 5000 | 3756 Common, 938 Uncommon, 234 Rare, 58 Epic, 14 Legendary |

## Repeat-victim handling
Private-alpha proposal: the same attacker/victim pair can contribute catch score once per 60-second window. Predation may still end the victim run during that window, but repeated farming does not keep adding reward score.

The repeat-pair ledger must be bounded and server-owned. It is temporary session state, not client input.

## Separate chest contract
`ChestRewardConfig` is independent from the run-reward table.

- Catch 0–9: 0 chests.
- Catch 10–99: 1 chest.
- Catch 100–499: 2 chests.
- Catch 500+: 3 chests, capped at 3 per run.
- Planned private-test timer: 60 seconds per chest, sequential. Build 009 temporarily accelerates this to 10 seconds solely for runtime verification of queue/offline behavior.
- One chest yields one species stack using its own species weights.
- Test quantity distribution: 1 copy 70%, 2 copies 25%, 3 copies 5%.
- Active queue capacity: 5, with a bounded pending overflow list. If both are full, prevent another reward-bearing run rather than discard an earned chest.
- Chest outcome is generated server-side once and stored by operation ID. Retries never reroll.

Changing chest tables must never alter immediate run-copy totals.

## Mutation pacing result
The current test mutation cost remains 50 base copies.

With one Common species in the three-species alpha, the deterministic run allocation reaches 50 Common copies at catch score 62. Therefore 50 copies is suitable for demonstrating Gold mutation during the private test but is not accepted long-term progression pacing.

A larger catalog spreads duplicates across more species. At catch score 500, the simulation allocates 378 Common copies; evenly split over 12 Common species this averages about 31.5 copies each. At 1000 it averages about 62.8 each, so public score-to-copy conversion will likely require retuning if scores of that size are routine.

## Numeric and payload limits
- Catch score: integer 0–5000.
- Counts: nonnegative validated integers.
- Never instantiate one object/card per rewarded copy. Use bounded `{speciesId, mutationId, count}` stacks.
- Unknown or ineligible species IDs are rejected.
- Reward randomness is server-owned.
- Persist an immutable result keyed by run/operation ID before presenting it as committed.

## Verification
`tools/economy_sim.py` and `tests/test_economy.py` execute the private-alpha math.

The tests verify:
1. exact total quantity for every catch score 0–5000;
2. strictly increasing totals;
3. nonincreasing rarity quantities;
4. eligibility-boundary outcomes;
5. the 50-copy mutation point;
6. chest independence;
7. invalid score rejection.

Detailed results are recorded in `docs/15-economy-simulation.md`.

Public balance remains a later playtest decision. BD-010 is closed only for the private mechanics-test configuration.
