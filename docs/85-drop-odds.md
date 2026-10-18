# 85 Drop odds: every rarity table (generated)

Generated from the repo by `python tools/generate_drop_odds.py --runner <luau.exe>` (`RarityCurve`, `Config`, `ProgressionConfig`). Do not edit by hand.
All numbers are **provisional**. Rarity follows the **exponential ladder** of [88](88-exponential-rarity.md) (BD-184): each tier is 5 times rarer than the one below. **Exception, dinosaur species (BD-1032, owner 2026-10-18):** species are steeper at the top so new kinds take time; tier totals are 91 / 8.5 / 0.42 / 0.07 / 0.01 ([82](82-species-rarity-tiers.md), [186](186-pattern-colour-indexes-and-slower-species.md) section 3, handbook conflict C-54 in [116](116-handbook-conflicts.md)). Odds below are for **one purchased egg** (no run-size boost).

## The shared ladder (`src/shared/RarityCurve.luau`)

| Tier | Chance | About 1 in | Aura price (base 60) | Trail price (base 100) |
|---|---:|---:|---:|---:|
| Common | 80.01% | 1.25 | 60 | 100 |
| Uncommon | 16% | 6.25 | 170 | 280 |
| Rare | 3.2% | 31 | 470 | 780 |
| Epic | 0.64% | 156 | 1,300 | 2,200 |
| Legendary | 0.128% | 781 | 3,700 | 6,100 |
| Mythic | 0.0256% | 3,906 | 10,000 | 17,000 |

Systems with fewer tiers use the first N rows and renormalise (five tiers: 80.02 / 16 / 3.2 / 0.64 / 0.128). Prices grow x2.8 per tier, rounded to two figures. Species stop at Legendary.

## Dinosaurs (22 species)

| # | Dinosaur | Rarity | % |
|---:|---|---|---:|
| 1 | Compy | Common | 36.4% |
| 2 | Raptor | Common | 26% |
| 3 | Gallimimus | Common | 12% |
| 4 | Microraptor | Common | 9.6% |
| 5 | Dimorphodon | Common | 7% |
| 6 | Archaeopteryx | Uncommon | 2.2% |
| 7 | Stegosaurus | Uncommon | 2.2% |
| 8 | Parasaurolophus | Uncommon | 1.7% |
| 9 | Pachycephalosaurus | Uncommon | 1.3% |
| 10 | Pteranodon | Uncommon | 1.1% |
| 11 | Triceratops | Rare | 0.13% |
| 12 | Brachiosaurus | Rare | 0.09% |
| 13 | Baryonyx | Rare | 0.07% |
| 14 | Ichthyosaurus | Rare | 0.065% |
| 15 | Plesiosaurus | Rare | 0.065% |
| 16 | Ankylosaurus | Epic | 0.02% |
| 17 | Elasmosaurus | Epic | 0.02% |
| 18 | Therizinosaurus | Epic | 0.015% |
| 19 | Quetzalcoatlus | Epic | 0.015% |
| 20 | T-Rex | Legendary | 0.004% |
| 21 | Spinosaurus | Legendary | 0.003% |
| 22 | Mosasaurus | Legendary | 0.003% |

| Rarity | Species | % total |
|---|---:|---:|
| Common | 5 | 91% |
| Uncommon | 5 | 8.5% |
| Rare | 5 | 0.42% |
| Epic | 4 | 0.07% |
| Legendary | 3 | 0.01% |

Run and nest eggs: a run of up to 15 eggs (a normal 5 minute run) and a single bought egg use the odds above. Above 15 eggs the Rare, Epic and Legendary rows rise step by step to **2x** at 120 eggs (and for a nest); Common and Uncommon are not lifted (`EggRarityBoostFreeEggs`, `EggRarityBoostMaxEggs`, `SpeciesRunBoost`). At 3 eggs a minute the first Uncommon comes after about 3 minutes and the first Rare or better after about 46 minutes (median); run `python tools/simulate_species_timing.py` for the table.

## Patterns (8, by tier; eggs and the dinosaurs hatched from them)

BD-1033 (owner 2026-10-18, [186](186-pattern-colour-indexes-and-slower-species.md)): patterns have tiers of the shared ladder (five tiers, renormalised: 80.02 / 16 / 3.2 / 0.64 / 0.13) split equally inside a tier. One table: `ProgressionConfig.EggPatterns`. Fusion rules ([90](90-fusion-ladder-v2.md)) are unchanged. A pattern rolls once per egg, independent of the colours.

| # | Pattern (id) | Name shown | Tier | % per egg | About 1 egg in |
|---:|---|---|---|---:|---:|
| 1 | 01_blank | Plain | Common | 26.68% | 3.75 |
| 2 | 02_emerald_islands | Islands | Epic | 0.6402% | 156 |
| 3 | 03_round_spots | Dots | Common | 26.68% | 3.75 |
| 4 | 04_bold_patches | Patches | Uncommon | 8.003% | 12 |
| 5 | 05_horizontal_bands | Bands | Uncommon | 8.003% | 12 |
| 6 | 06_wavy_stripes | Waves | Rare | 3.201% | 31 |
| 7 | 07_diamond_scales | Diamonds | Legendary | 0.128% | 781 |
| 8 | 08_freckles | Freckles | Common | 26.68% | 3.75 |

| Tier | Patterns | % per egg |
|---|---:|---:|
| Common | 3 | 80.03% |
| Uncommon | 2 | 16.01% |
| Rare | 1 | 3.201% |
| Epic | 1 | 0.6402% |
| Legendary | 1 | 0.128% |

## Colors (9, tiers of the ladder)

Each egg has **two** color slots rolled independently. Tier chances come from the ladder (six tiers, renormalised) and split inside a tier by the old weights.

| # | Color | Tier | % per slot | Both slots this color |
|---:|---|---|---:|---:|
| 1 | Cream | Common | 52.63% | 1 in 3.61 |
| 2 | Blue | Common | 27.37% | 1 in 13 |
| 3 | Green | Uncommon | 16% | 1 in 39 |
| 4 | Teal | Rare | 1.422% | 1 in 4,943 |
| 5 | Pink | Rare | 1.778% | 1 in 3,164 |
| 6 | Amber | Epic | 0.64% | 1 in 24,411 |
| 7 | Purple | Legendary | 0.128% | 1 in 610,256 |
| 8 | Red | Mythic | 0.02048% | 1 in 23,841,858 |
| 9 | Black | Mythic | 0.00512% | 1 in 381,469,727 |

## Mutations

| Mutation | Tier | Chance | In a nest (lucky) |
|---|---|---:|---:|
| BIG (size 1.2x) | Rare | 3% | 6% |
| Shiny (earned eggs, irregular weather only) | Epic | 0.6% | 1.5% |

## Weather events (how often each is chosen)

A new event starts after `WeatherInterval` 300 s of clear sky and lasts `WeatherDuration` 180 s: one event every 480 s = **7.5 events per hour** (3.8 in a 30 minute session). **Weather is an exception to the ladder** (weather is a show, not loot): labels follow the tiers and a higher tier is always rarer, but the weights are flat enough that every event is seen regularly (docs/88).

| Event | Tier | Chance per event | About one every |
|---|---|---:|---:|
| Rain | Common | 24% | 33 min |
| Thunderstorm | Common | 22% | 36 min |
| Blizzard | Uncommon | 15% | 53 min |
| Volcanic Bloom | Rare | 10% | 80 min |
| Northern Lights | Legendary | 6% | 2 hours |
| Earthquake | Uncommon | 15% | 53 min |
| Blood Moon | Epic | 8% | 100 min |

## Potion shop (rarity of each offer slot)

| Tier | Chance |
|---|---:|
| Common | 80.02% |
| Uncommon | 16% |
| Rare | 3.201% |
| Epic | 0.6402% |
| Legendary | 0.13% |

## Aura prices (crystals)

| Aura | Tier | Price |
|---|---|---:|
| Meadow Glow | Common | 60 |
| Tidal Halo | Rare | 470 |
| Royal Nova | Legendary | 3,700 |

## Trail prices (crystals)

| Trail | Tier | Price |
|---|---|---:|
| Normal White | Common | 0 |
| Fern Drift | Common | 100 |
| Tidal Wake | Uncommon | 280 |
| Ember Trail | Uncommon | 390 |
| Violet Pulse | Rare | 780 |
| Electric Arc | Rare | 1,100 |
| Frost Comet | Epic | 2,200 |
| Solar Flare | Epic | 3,100 |
| Nova Ribbon | Legendary | 6,100 |
| Astra | Mythic | 17,000 |
