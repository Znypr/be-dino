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

**Rarity implementation gap:** Current Build 020 has only **Common, Rare, Legendary** species tiers. The owner's examples require additional **Uncommon and Epic** tiers, including catalog classification, unlock thresholds, saved metadata, UI rarity ordering and weighted random rewards. This is a specific [BD-044](07-kanban.md) implementation subtask, not an assertion these tiers already exist.

The rarity counts describe **15/150 individual eggs revealed**, not extra guaranteed immediate dinosaur copies. Egg hatch success and resulting copies remain separate outcome questions; the current per-egg 1/2/3-copy probability and 20% Cracked hatch success are **existing provisional mechanics**. Do not present every run egg as guaranteed to hatch successfully, and do not compound its results with `N(c)=c` automatic copies. The examples do **not** approve specific species odds, number of crystals, or nests-per-point thresholds. A five-minute run need not attain 500 points, and a 5,000-**food**-point run is not the historical 5,000-**catch**-score case.

### Design/implementation decisions still open
- Rarity probabilities and eligibility/gating across 15-egg and 150-egg batches; species catalog and trait odds remain data-driven. These two distributions are sample outcomes, not fixed tier weights.
- Exact conversion from food/PvP to earned eggs (current `15/500` is an example-compatible starting point), crystal rewards, and nest milestone formula.
- Whether successful individual eggs continue to grant 1/2/3 copies or one dinosaur, and how failed Cracked reveals/consolation are handled. Keep the existing immutable outcome rules until deliberately migrated.
- Five separate **nest slots** versus current five ordinary-egg queue slots. In the six-nest example, only five can be claimed with five empty nest spots; sixth must be shown as unavailable or pending under an explicit policy, never silently discarded.
- Batch UI for 150 eggs; user-controlled fast reveal/skip or summary options need owner design while retaining individually inspectable results and atomic persistence.
- Migration of existing earned direct dinosaur copies, saved eggs, rewards and legacy `ChestThresholds` without duplication, regressions, or paid-egg bypasses.

---

## Historical alpha calculations

The September 17 private-alpha specified **immediate dinosaur copies `N(c) = c`**, 0.25 rarity weighting and separate 1/2/3 chest or egg grants at catch-score thresholds 10/100/500. That was implemented and tested to verify mechanics, **not** accepted as the long-term collection economy. It is incompatible with the current owner's instruction that each earned catch represents **one individual run egg**. Do not use this older model when producing future reward examples or balancing the new implementation.

The **complete legacy test parameters, 25–5000 score simulation table, chest rules, anti-farming safeguards, Gold pacing and verification evidence** remain in [BD-010 historical economy simulation](15-economy-simulation.md). Its old `c` is catch score, **not** raw food points. The current runtime and migration requirements are separately documented in [Build 020 integration](44-main-integration-checklist.md), [egg outcomes contract](41-egg-outcomes-contract.md) and [BD-044](07-kanban.md).

