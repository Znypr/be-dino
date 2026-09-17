# BD-010: private-alpha economy simulation

Status: specified and simulated for mechanics testing. These values are not public-launch balance.

## Test configuration

Run rewards use `catchScore` only. Growth score remains temporary arena power.

- Supported catch score: 0–5000. Reaching 5000 should end the run rather than flatten rewards.
- Total immediate dinosaur copies: `N(c) = c`.
- Rarity allocation uses sequential highest-averages with weights `0.25^tier`.
- Eligibility thresholds: Common 1, Uncommon 25, Rare 100, Epic 400, Legendary 1600.
- The three-species alpha enables only the first three real catalog tiers. Epic/Legendary are synthetic simulation fixtures until matching species exist.
- Duplicate species/mutation keys are aggregated into count stacks before persistence or UI.
- Same attacker/victim repeat catches should award catch score once per 60-second pair window; repeated predation can still end the victim run but does not become the best farming source.
- Gold mutation test cost remains 50 base copies. This is deliberately easy to exercise in the private test and must be retuned before public progression if retained.

## Separate chest configuration

Chests remain independent from immediate run dinosaur rewards.

- Catch 0–9: 0 chests.
- Catch 10–99: 1 chest.
- Catch 100–499: 2 chests.
- Catch 500+: 3 chests, capped at 3 per run.
- Private-test timer: 60 seconds per chest, sequential.
- Chest content is one species stack using an independent chest table. Test quantity distribution: 1 copy 70%, 2 copies 25%, 3 copies 5%.
- Active queue capacity: 5. Additional earned chests go to a bounded pending list. If both active and pending capacity are full, block starting another reward-bearing run rather than discard an earned chest.
- Chest randomness is generated server-side once and persisted by operation ID. Retrying a claim never rerolls.

Exact species weights for chest contents stay in `ChestRewardConfig` and must not reuse the run rarity allocation.

## Deterministic simulation results

| Catch score | Eligible allocation | Chests |
|---:|---|---:|
| 1 | 1 Common | 0 |
| 25 | 20 Common, 5 Uncommon | 1 |
| 62 | 50 Common, 12 Uncommon | 1 |
| 100 | 77 Common, 19 Uncommon, 4 Rare | 2 |
| 400 | 303 Common, 75 Uncommon, 18 Rare, 4 Epic | 2 |
| 1000 | 754 Common, 188 Uncommon, 47 Rare, 11 Epic | 3 |
| 1600 | 1203 Common, 300 Uncommon, 75 Rare, 18 Epic, 4 Legendary | 3 |
| 5000 | 3756 Common, 938 Uncommon, 234 Rare, 58 Epic, 14 Legendary | 3 |

The exact total always equals catch score and therefore strictly increases by one copy for every +1 catch in the supported range.

## Mutation pacing finding

With one Common species in the three-species alpha, a single run reaches the current 50-copy Gold requirement at catch score 62. Therefore 50 copies is suitable only for demonstrating mutation mechanics, not as evidence of healthy long-term progression.

Synthetic examples make the same point: if a player averaged 10 catches per run, five such runs already contain enough Common copies for one Gold conversion. Real runs/hour are not known yet, so no public pacing claim is made.

With a much larger catalog, duplicates spread across more species and mutation pacing slows. For example, 500 catch score produces 378 Common copies; split evenly across 12 Common species that is about 31.5 copies each. At 1000, the same 12-species assumption averages about 62.8 each, so the eventual public score-to-copy conversion will likely need retuning if those score magnitudes are common.

## Verification

`tools/economy_sim.py` is deterministic and `tests/test_economy.py` checks:

1. exact total quantity for every supported score;
2. strict total increase from score 0 through 5000;
3. rarity counts remain nonincreasing within each eligible set;
4. tier-boundary outcomes;
5. the measured 50-copy mutation point;
6. chest grants do not alter run-copy totals;
7. invalid/noninteger scores are rejected.

This closes BD-010 for the private mechanics test. BD-011 may consume this config, but launch balance remains a later playtest decision.
