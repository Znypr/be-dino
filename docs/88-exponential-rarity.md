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

## Owner decisions (2026-10-15)
- Steepness: **r = 1/5** (each tier 5 times rarer). Owner left 4/5/6 to the lead; 5 is the vision-compatible middle.
- **Patterns stay equally likely** for now (fusion recipes need it). Revisit later. **HISTORICAL: replaced 2026-10-18 by the owner (BD-1033, [186](186-pattern-colour-indexes-and-slower-species.md)); fusion keys on the pattern id only, so it did not need equal odds.**
- One **shared six-tier ladder** for every system, below.

## The tier ladder (PROPOSED, all systems use it)
| # | Tier | Chance of this tier (r = 1/5) | About 1 in | Price / effort factor (x2.8 per tier) |
|---:|---|---:|---:|---:|
| 0 | Common | 80.0% | 1.25 | 1 |
| 1 | Uncommon | 16.0% | 6 | 2.8 |
| 2 | Rare | 3.2% | 31 | 7.8 |
| 3 | Epic | 0.64% | 156 | 22 |
| 4 | Legendary | 0.128% | 781 | 61 |
| 5 | Mythic | 0.0256% | 3,906 | 172 |

Systems with fewer than six tiers use the first N rows and renormalise (for example five tiers: 80.1 / 16.0 / 3.2 / 0.64 / 0.13). **Mythic is the top tier for colours, mutations, auras, trails and potions; dinosaur species stop at Legendary** (as today).
A "normal" 5-egg run therefore has about a 0.6% chance of containing one Legendary dino from base odds alone (5 x 0.128%), and the run-size boost may lift that only slightly (target at most about 1.5%).

## Table: where every system stands today and what it becomes
| System | Today (code) | Proposed | Status |
|---|---|---|---|
| Dinosaur species (22) | Common 72%, Uncommon 24%, Rare 3.2%, Epic 0.7%, Legendary 0.1% (docs/85) | Already close; keep the five tier totals, check each species inside its tier. Legendary 0.1% = 3 species | OK, keep |
| Run-size boost | Rare and above x4-4.7 at full boost; 40 eggs per 500 food | Cap so adjacent tier ratio never falls below 1/6; eggs per run 10x fewer (BD-165) | Change (BD-184) |
| Egg colours (9) | Cream 50%, Blue 26%, Green 12%, Pink 5%, Teal 4%, Amber 2.5%, Purple 0.45%, Red 0.04%, Black 0.01% | Group: Common = Cream, Blue; Uncommon = Green; Rare = Pink, Teal; Epic = Amber; Legendary = Purple; Mythic = Red, Black. Tier chances from the ladder, split inside a tier. Colour growth bonus 1-5% rises by tier (BD-172) | Done (BD-184) |
| Patterns (8) | 12.5% each | Superseded 2026-10-18 (owner, BD-1033): 3 Common / 2 Uncommon / 1 Rare / 1 Epic / 1 Legendary on the five-tier ladder, `ProgressionConfig.EggPatterns` | Done (BD-1033) |
| Egg conditions (5) | Cracked 50%, Dirty 30%, Normal 15%, Rainbow 4.5%, Astra 0.5% (owner-approved 2026-10-08) | Keep for now (they limit dinos, owner design); Rainbow and Astra are Epic and Legendary-like top steps. Revisit with a 5-step r = 1/3.5 curve if owner wants strict exponential | Owner call later |
| Mutations: BIG | 10% | Rare tier: about 3% (nest luck up to 6%) | Done (BD-184) |
| Mutations: Shiny (weather only) | 5% during irregular weather | Epic tier: about 0.6% (up to 1.5% in nests/weather) | Done (BD-184) |
| Event mutations (per weather event) | event-bound | Ordered by event rarity below | Review |
| Weather events (7) | every event can start with the same frequency | Frequency ladder: Rain, Thunder = Common; Quake, Blizzard = Uncommon; Volcano = Rare; Blood Moon = Epic; Aurora = Legendary. Duration unchanged | Done (BD-184) |
| Potions (12, 5 rarity frames) | Shop weights Common 50, Uncommon 28, Rare 14, Epic 6, Legendary 2 | 80 / 16 / 3.2 / 0.64 / 0.13 (five tiers); price factor x2.8 per tier | Done (BD-184) |
| Auras (3 today) | Meadow 60 (Common), Tidal 240 (Rare), Royal 900 (Legendary) | Price by tier: 60 / 170 / 470 / 1,300 / 3,700 / 10,000 for Common to Mythic; add tiers over time | Done (BD-184) |
| Trails (10 today) | 0, 100, 250, 500, 900, 1,500, 2,400, 3,600, 5,500, 8,500 crystals (Common to Legendary) | Re-map to 6 tiers with prices 100 / 280 / 780 / 2,200 / 6,100 / 17,000; Mythic trails are new | Done (BD-184) |
| Nest luck | boost up to 200 eggs, big 20%, shiny 3% | Scale with the ladder (keep nests lucky but not flat) | Done (BD-184) |

All "Proposed" values are provisional until the owner approves the table; the code must read them from one place (`RarityCurve`, BD-184) and `docs/85-drop-odds.md` is regenerated from it.

## Implementation status (BD-184, 2026-10-15, branch claude/rarity-curve-impl)
Implemented in code, offline-verified only (Luau runner and Python tests; **no Studio or phone playtest**).
- `src/shared/RarityCurve.luau`: six-tier ladder, `weights(count)` with renormalisation, `price(tier, base)` (x2.8, two significant figures), `boost()` that never lets an adjacent ratio exceed 1/3 (each tier at least 3x rarer; the shipped `SpeciesRunBoost = {1,1,1.1,1.1,1.1}` is untouched and already inside the cap). Config files keep literal numbers (the offline verifiers inline them); `tools/verify_rarity.py` fails if any literal drifts from the module. `docs/85` is regenerated by `tools/generate_drop_odds.py` (`--check` detects a stale doc).
- Ported: egg colours (tiers Common Cream+Blue, Uncommon Green, Rare Pink+Teal, Epic Amber, Legendary Purple, Mythic Red+Black; weights now out of `EggColorWeightScale` 10,000,000), BIG 3% (nest 6%), Shiny 0.6% (nest 1.5%), potion shop weights 80 / 16 / 3.2 / 0.64 / 0.13, aura and trail prices, weather event frequency, nest luck. Species tier totals (72 / 24 / 3.2 / 0.7 / 0.1), patterns, conditions, Cracked, growth, fusion and nest egg counts are unchanged.
- Tier changes: aura Tidal Halo (Rare, 240 -> 470) and Royal Nova (Legendary, 900 -> 3,700); trails Tidal Wake Common -> Uncommon (250 -> 280), Ember Uncommon (500 -> 390), Violet Pulse Rare (900 -> 780), Electric Arc Rare (1,500 -> 1,100), Frost Comet Epic (2,400 -> 2,200), Solar Flare Epic (3,600 -> 3,100), Nova Ribbon Legendary (5,500 -> 6,100), Astra Mythic (8,500 -> 17,000). Fern Drift (100) and Normal White (free) stay Common. Existing owners keep what they bought.
- Weather (**documented exception to the ladder**, lead decision 2026-10-15): weather is a show, not loot, so every event must be seen regularly. Tier labels stay (Rain and Thunder Common, Quake and Blizzard Uncommon, Volcano Rare, Blood Moon Epic, Aurora Legendary) and a higher tier is always rarer, but scheduler weights are Rain 24, Thunder 22, Quake 15, Blizzard 15, Volcano 10, Blood Moon 8, Aurora 6 (total 100). `WeatherInterval` is 300 s (was 600) with duration 180 s: 7.5 events/hour, 3.8 in 30 minutes; Aurora about every 2.2 hours, Blood Moon about every 1.7 hours, Volcano about every 1.3 hours. Strict ladder odds would have made Aurora once per 104 hours.
- Potion prices follow the ladder: cheapest potion of tier k costs 20 x 2.8^k (two significant figures), others in the tier keep their old relative price (Common 20/25/30, Uncommon 56/71, Rare 160/200/230, Epic 440/550, Legendary 1,200/1,500). Run crystals are 30 (4 eggs) to 220 (40 eggs), so a Legendary potion is about 5-7 big runs of crystals and is offered at 0.13% per slot.
- Not changed: UI beyond the egg odds text (colour tier names, BIG/Shiny percent are read from config) and a Mythic rarity colour (red) in `UITheme`.


## Nest eggs and weather (BD-156)
A nest dropped while a weather event is active remembers that weather. When it is claimed, **each of its eggs** rolls the same event-mutation chance as a run egg caught in that weather (Rain 2%, Thunderstorm 4%, Blizzard 4%, Earthquake 5%, Volcanic Bloom 7%, Northern Lights 7%, Blood Moon 8%; the table in `ProgressionConfig.Weather` is the source), so nests are never luckier for mutations than a run. Nests dropped in clear weather roll no mutation. Nest luck for Shiny and BIG is separate and unchanged (3% and 20%, `Config.NestLuckTiers`). These numbers are provisional and will move with the exponential rarity rework (BD-184).
