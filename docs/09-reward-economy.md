# Reward economy: owner-approved target and historical prototype

**Owner clarification: 2026-10-08; owner decisions 2026-10-13.** This target supersedes the older 2026-09-17 private-alpha reward *design*. Build 020 on main still uses the historical direct-copy and 1/2/3-egg thresholds; the BD-044/BD-045 branch below replaces them and is in **Review / test** (offline evidence only, **Studio verification pending**). Historical simulation tables are retained below to explain those tests, not to drive future product decisions. See [AI instructions](../AGENTS.md), [game design](03-game-design.md), and [canonical task BD-044](07-kanban.md).

## Implementation status (2026-10-13, BD-044 + BD-045, Review / test)

Implemented on `claude/bd-044-reward-loop` (details, data shape and evidence: [50-bd044-reward-loop.md](50-bd044-reward-loop.md)). **Implemented in code, offline-tested, NOT Studio-verified, NOT released.**

| Topic | Implemented behavior | Status |
| --- | --- | --- |
| Catches -> eggs | Every earned catch = one banked run egg (`FoodCatchRate 12/500` since owner decision 2026-10-16, BD-418: 500 food -> 12, 5,000 -> 120, a normal 5-minute run about 15, see [119](119-catch-rate-15-per-run.md); HISTORICAL 4/500 of 2026-10-15 [89](89-catch-rate-4.md), 40/500, 15/150); per-run cap 150 (PROVISIONAL) | Implemented, offline-tested |
| Direct copies / thresholds | `N(c)=c` settlement copies and 10/100/500 threshold eggs removed | Implemented |
| Dinosaurs per egg | Owner decision 2026-10-13: exactly 1 per successful hatch; failed Cracked = 0; old saved 2-3-copy eggs keep their committed count | Implemented |
| Reveal | Ordered reveal now 1 s/egg (owner 2026-10-13, PROVISIONAL `HatchRevealSeconds`); 5-slot queue refilled from a server-side ordered run-egg bank (1,000, PROVISIONAL; was 600); exactly-once via `settledRuns` + operation log | Implemented; 150-egg pacing UX still an owner decision |
| Run crystals | PROVISIONAL deterministic `min(300, floor((250*min(n,12) + 176*max(0,n-12))/100))`: 12 eggs -> 30, 120 -> 220 (BD-418; was 750/4/530) (unchanged per-run outputs; 2026-10-15 rescale of the 2026-10-13 40 -> 30, 400 -> 220); random crystal box retired | Implemented, needs balance sign-off |
| Bonus nests | Separate 5 nest slots + visible pending list; PROVISIONAL 12 eggs -> 1 nest, +1 per 30 further eggs (BD-418 rescale of the 2026-10-15 +1 per 10; no per-run cap since 2026-10-16 (BD-420): nests beyond the 5 free spots become crystals (`NestOverflowCrystals` 50, PROVISIONAL); the old owner example of 6 offered is not yet implemented); 3 bonus eggs per nest, 300 s incubation; new runs blocked rather than losing eggs/nests when storage is near capacity | Implemented, needs balance/UX sign-off |
| Condition odds (BD-045) | Tier 0 = 50/30/15/4.5/0.5 (`bd045-conditions-v1`, integer weights /10,000), PROVISIONAL monotonic tiers 1-6, Cracked 20% hatch success, versioned disclosure | Implemented; 40% tier-0 failure is a playtest risk |
| Five species tiers | Common/Uncommon/Rare/Epic/Legendary, PROVISIONAL weights and a gentle run-size boost (2026-10-15: gains {1,1,1.1,1.1,1.1}, full at 40 eggs; 4 eggs ~ 2.9/1.0/0.16 Rare+; 40 eggs ~ 28.7/9.6/1.4/0.3/0.04), saved-value migration ([82](82-species-rarity-tiers.md)) | Implemented; Studio pending |

Milestone 1 is a private playtest in a new private place with fresh saves; all Robux/paid flags stay off.

## Owner-approved target reward loop

A run accumulates **raw food/growth points**, producing a **catch count**, representing the number of **run eggs** collected. Each catch is **one egg to reveal after the run**, sequentially and separately. Those eggs are the central collection payout, not merely thresholds into an additional one-to-three egg reward. The player also gets **crystals** and potentially **bonus egg nests**, each a distinct reward. Gameplay time alone does not determine rewards.

1. **Collect food / hunt in the run** -> gain growth/food points and catches. Prototype conversion `500 raw food points = 40 catches` (owner 2026-10-13; superseded 15) is a provisional rate; it is **not** a final economy curve.
2. **Settle the run** -> a 15-catch run produces **15 run eggs**, not 15 automatic Base Compys plus an extra single egg. Server snapshots each egg's persistent identity, species/rarity, condition, colors, traits and event eligibility/outcome (as supported by a versioned implementation), preventing rerolls or double grants.
3. **Reveal run eggs one at a time** to see the discoveries. The reveal pace is now 1 second/egg (owner decision 2026-10-13; earlier prototype 5 s) and ascending rarity ordering are useful prototype behaviors. For 15 eggs this is ~15 seconds; for 150 it is ~2.5 minutes at that speed, **a pacing/UX issue to solve**, not a claim that current UI supports it. Closing should preserve unclaimed eggs, with bounded storage.
4. **Crystals** are earned from the run separately, possibly through a crystal reveal, and can also be found on the map. The precise run payout rule is **unapproved**.
5. **Bonus egg nests** are a **separate kind of loot**, not the same as the caught eggs. Players can claim nests into **up to five available nest spots**. Define their hatch timing, contents, claim/overflow policy and how this coexists with the legacy five-slot egg queue before changing code.

### Examples: intended outcomes, not deterministic rarity probabilities

| Scenario | Food score | Catches = run eggs | Example egg rarity composition | Run crystals | Bonus nests |
| --- | ---: | ---: | --- | ---: | --- |
| **5-minute run** | **500** | **4** (superseded 2026-10-15 by owner BD-165: was 40, before that 15) | **3 Common + 1 Uncommon (illustrative; expected 2.9 / 1.0 / 0.16 Rare+)** | **30 illustrative ONLY** | **1** |
| **Longer/higher-scoring run** | **5,000** | **40** (superseded 2026-10-15 by owner BD-165: was 400, before that 150) | **29 Common + 10 Uncommon + 1 Rare (illustrative; expected 28.7 / 9.6 / 1.4 / 0.3 / 0.04)** | **220 in owner's example; final formula TBD** | **6 offered, at most 5 claimed if all 5 spots free** |

**Rarity implementation gap (closed in code 2026-10-14, see [82](82-species-rarity-tiers.md)):** Build 020 had only **Common, Rare, Legendary** species tiers. The owner's examples require additional **Uncommon and Epic** tiers, including catalog classification, unlock thresholds, saved metadata, UI rarity ordering and weighted random rewards. This is a specific [BD-044](07-kanban.md) implementation subtask, not an assertion these tiers already exist.

The rarity counts describe **15/150 individual eggs revealed**, not extra guaranteed immediate dinosaur copies. Egg hatch success and resulting copies remain separate outcome questions; the current per-egg 1/2/3-copy probability and 20% Cracked hatch success are **existing provisional mechanics**. Do not present every run egg as guaranteed to hatch successfully, and do not compound its results with `N(c)=c` automatic copies. The examples do **not** approve specific species odds, number of crystals, or nests-per-point thresholds. A five-minute run need not attain 500 points, and a 5,000-**food**-point run is not the historical 5,000-**catch**-score case.

### Design/implementation decisions still open
- Rarity probabilities and eligibility/gating across 15-egg and 150-egg batches; species catalog and trait odds remain data-driven. These two distributions are sample outcomes, not fixed tier weights.
- Exact conversion from food/PvP to earned eggs (current `15/500` is an example-compatible starting point), crystal rewards, and nest milestone formula.
- ~~Whether successful individual eggs continue to grant 1/2/3 copies or one dinosaur~~ **Decided 2026-10-13: exactly one dinosaur per successful egg** (failed Cracked = 0, no consolation yet). Existing saved eggs keep their committed outcomes.
- Five separate **nest slots** versus current five ordinary-egg queue slots. In the six-nest example, only five can be claimed with five empty nest spots; sixth must be shown as unavailable or pending under an explicit policy, never silently discarded.
- Batch UI for 150 eggs; user-controlled fast reveal/skip or summary options need owner design while retaining individually inspectable results and atomic persistence.
- Migration of existing earned direct dinosaur copies, saved eggs, rewards and legacy `ChestThresholds` without duplication, regressions, or paid-egg bypasses.

---

## Historical alpha calculations

The September 17 private-alpha specified **immediate dinosaur copies `N(c) = c`**, 0.25 rarity weighting and separate 1/2/3 chest or egg grants at catch-score thresholds 10/100/500. That was implemented and tested to verify mechanics, **not** accepted as the long-term collection economy. It is incompatible with the current owner's instruction that each earned catch represents **one individual run egg**. Do not use this older model when producing future reward examples or balancing the new implementation.

The **complete legacy test parameters, 25–5000 score simulation table, chest rules, anti-farming safeguards, Gold pacing and verification evidence** remain in [BD-010 historical economy simulation](15-economy-simulation.md). Its old `c` is catch score, **not** raw food points. The current runtime and migration requirements are separately documented in [Build 020 integration](44-main-integration-checklist.md), [egg outcomes contract](41-egg-outcomes-contract.md) and [BD-044](07-kanban.md).



## Update 2026-10-13: owner raised eggs per run

Owner decision: catches (= run eggs) per 500 food rise from 15 to **40** so hatching many eggs is normal. All 15/150 numbers above in this document are the earlier example, kept as history; the 40/400 figures and all re-tuned dependants (run cap 500, bank 1,000, crystals 30/220, nests 1/6, run-start gates) are in [59-egg-rate-40.md](59-egg-rate-40.md).


## Update 2026-10-15: owner cut eggs per run 10x (BD-165)

Catches (= run eggs) per 500 food fall from 40 to **4** (5,000 food -> 40). Crystals, nests and account XP keep their per-run outputs; the species run-boost is gentler so rares do not get easier. All 40/400 numbers above are history; see [89-catch-rate-4.md](89-catch-rate-4.md).
