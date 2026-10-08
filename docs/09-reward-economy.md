# Reward economy: owner-approved target and historical prototype

**Owner clarification: 2026-10-08.** This target supersedes the older 2026-09-17 private-alpha reward *design*, but **is not yet implemented in the Build 020 source**, which continues to use the historical direct-copy and 1/2/3-egg thresholds. Historical simulation tables are retained below to explain those tests, not to drive future product decisions. See [AI instructions](../AGENTS.md), [game design](03-game-design.md), and [canonical task BD-044](07-kanban.md).

## Owner-approved target reward loop

A run accumulates **raw food/growth points**, producing a **catch count**, representing the number of **run eggs** collected. Each catch is **one egg to reveal after the run**, sequentially and separately. Those eggs are the central collection payout, not merely thresholds into an additional one-to-three egg reward. The player also gets **crystals** and potentially **bonus egg nests**, each a distinct reward. Gameplay time alone does not determine rewards.

1. **Collect food / hunt in the run** -> gain growth/food points and catches. Prototype conversion `500 raw food points = 15 catches` is an existing test rate; it is **not** a final economy curve.
2. **Settle the run** -> a 15-catch run produces **15 run eggs**, not 15 automatic Base Compys plus an extra single egg. Server snapshots each egg's persistent identity, species/rarity, condition, colors, traits and event eligibility/outcome (as supported by a versioned implementation), preventing rerolls or double grants.
3. **Reveal run eggs one at a time** to see the discoveries. The current ~5 seconds/egg and ascending rarity ordering are useful prototype behaviors. For 15 eggs this is ~75 seconds; for 150 it would be ~12.5 minutes at that speed, **a pacing/UX issue to solve**, not a claim that current UI supports it. Closing should preserve unclaimed eggs, with bounded storage.
4. **Crystals** are earned from the run separately, possibly through a crystal reveal, and can also be found on the map. The precise run payout rule is **unapproved**.
5. **Bonus egg nests** are a **separate kind of loot**, not the same as the caught eggs. Players can claim nests into **up to five available nest spots**. Define their hatch timing, contents, claim/overflow policy and how this coexists with the legacy five-slot egg queue before changing code.

### Examples: intended outcomes, not deterministic rarity probabilities

| Scenario | Food score | Catches = run eggs | Example egg rarity composition | Run crystals | Bonus nests |
| --- | ---: | ---: | --- | ---: | --- |
| **5-minute run** | **500** | **15** | **11 Common + 4 Uncommon** | **30 illustrative ONLY** | **1** |
| **Longer/higher-scoring run** | **5,000** | **150** | **80 Common + 50 Uncommon + 17 Rare + 3 Epic** | **220 in owner's example; final formula TBD** | **6 offered, at most 5 claimed if all 5 spots free** |

The rarity counts describe **15/150 individual eggs revealed**, not extra guaranteed immediate dinosaur copies. Egg hatch success and resulting copies remain separate outcome questions; the current per-egg 1/2/3-copy probability and 20% Cracked hatch success are **existing provisional mechanics**. Do not present every run egg as guaranteed to hatch successfully, and do not compound its results with `N(c)=c` automatic copies. The examples do **not** approve specific species odds, number of crystals, or nests-per-point thresholds. A five-minute run need not attain 500 points, and a 5,000-**food**-point run is not the historical 5,000-**catch**-score case.

### Design/implementation decisions still open
- Rarity probabilities and eligibility/gating across 15-egg and 150-egg batches; species catalog and trait odds remain data-driven. These two distributions are sample outcomes, not fixed tier weights.
- Exact conversion from food/PvP to earned eggs (current `15/500` is an example-compatible starting point), crystal rewards, and nest milestone formula.
- Whether successful individual eggs continue to grant 1/2/3 copies or one dinosaur, and how failed Cracked reveals/consolation are handled. Keep the existing immutable outcome rules until deliberately migrated.
- Five separate **nest slots** versus current five ordinary-egg queue slots. In the six-nest example, only five can be claimed with five empty nest spots; sixth must be shown as unavailable or pending under an explicit policy, never silently discarded.
- Batch UI for 150 eggs; user-controlled fast reveal/skip or summary options need owner design while retaining individually inspectable results and atomic persistence.
- Migration of existing earned direct dinosaur copies, saved eggs, rewards and legacy `ChestThresholds` without duplication, regressions, or paid-egg bypasses.

---

## Archived private-alpha reward specification (historical, *not* target vision)

Everything below is the **implemented/tested historical model**. Its use of "Confirmed" applies to the *old* alpha design, **not** the owner's clarified 2026-10-08 target.

### Original specification title: Reward economy specification
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
The current test mutation cost remains 50 base copies. Build 010 implements this as one atomic `-50 base, +1 Gold` profile mutation.

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
