# 88 Exponential rarity principle (owner, 2026-10-15)

**Owner:** rarity progression must be **exponential** everywhere: each step up is much harder than the last. In playtest 2 rare dinos came too easily. The rule applies to dinosaurs, eggs and egg conditions, colours, patterns, mutations, weather events, potions, and the **price** of trails and auras.

All numbers here are PROPOSALS for owner review. Reward formulas stay in [AGENTS.md](../AGENTS.md) and [docs/09](09-reward-economy.md); feel rules in [docs/87](87-vision-and-feel-guide.md).

## The rule
For tiers `k = 0 (Common) ... n` the chance of a tier is proportional to `r^k` with a common ratio **r between 1/4 and 1/6** (each tier is 4-6 times rarer than the previous one). Values and prices go the other way: **price (or effort) per tier grows about x2.5-x3**, so the rarest item costs about 100-200x a Common one.

Example for 5 tiers with r = 1/4: Common 75%, Uncommon 19%, Rare 4.7%, Epic 1.2%, Legendary 0.3% (before any run bonus). With r = 1/5: 80 / 16 / 3.2 / 0.64 / 0.13.

## What is wrong today (audit of [docs/85](85-drop-odds.md) and [docs/82](82-species-rarity-tiers.md))
- **Species base odds** are already close to exponential: 72 / 24 / 3.2 / 0.7 / 0.1 %. Good.
- **Run-size boost** (`SpeciesRunBoost = {1, 1.9, 4.7, 4.5, 4}` and a 40-eggs-per-500-food rate) flattens the curve: with 50+ eggs per run the higher tiers get a 4-5x multiplier and Rare+ appears often. This is the main reason rares feel easy. With the planned 10x fewer eggs (BD-165) each egg must be rarer to feel special, but the boost must not erase the exponential shape: boosts must scale **tier weights by r-compatible factors** and be capped so the ratio between adjacent tiers never drops below about 1/3.
- **Colours** use "uniform mixed-colour 1-99% shares": not exponential. Needs a tiered colour table (Cream/Blue Common up to Black/Double Black Mythic, see BD-171/172).
- **Patterns** are uniform (12.5% each). Owner may keep patterns uniform for fusion reasons (docs/58); decision pending (dashboard d25). If rarity patterns are wanted, group them in tiers and keep fusion recipes unaffected.
- **Conditions** (Cracked 50, Dirty 30, Normal 15, Rainbow 4.5, Astra 0.5): steps are roughly exponential at the top. Check Rainbow/Astra against r.
- **Mutations, weather events, potions, trail/aura prices:** need a tier table, probability or price per tier following the rule, and a visible rarity colour.

## Implementation plan (BD-184)
1. One shared pure module (for example `RarityCurve.luau`): `weight(tier, r)`, `price(tier, base, g)`, helpers for boost with a floor on adjacent-tier ratio. All systems read it so a single owner tweak (r and g) rebalances everything.
2. Audit and port each system: species tiers, colours, patterns (if tiered), conditions, mutations, weather event frequency, potions, auras, trails (prices), nest luck.
3. Verifiers: for every table, assert strictly decreasing probabilities, adjacent ratio within [1/6, 1/3], total = 100%, prices strictly increasing at about the g factor. Simulation test: probability of at least one Rare+ in an average run stays low (target below about 30% for a normal 5-egg run, owner to confirm).
4. Regenerate docs/85 with the new tables, and show rarity colours and percentages in the UI.
5. Keep paid-random disclosure rules ([docs/43](43-player-access-and-paid-random-policy.md)): published odds must match the code.

## Open questions for the owner
- Preferred ratio r (1/4 steep-ish, 1/5 steeper, 1/6 very steep)?
- Should patterns stay uniform (fusion simplicity) or get tiers?
- Target rarity of "Legendary within a normal 5-egg run" (about 1.5% suggested).
