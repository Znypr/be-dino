# 85 Drop odds: every rarity table (generated)

Generated from the repo by `python tools/generate_drop_odds.py --runner <luau.exe>` (`RarityCurve`, `Config`, `ProgressionConfig`). Do not edit by hand.
All numbers are **provisional**. Rarity follows the **exponential ladder** of [88](88-exponential-rarity.md) (BD-184): each tier is 5 times rarer than the one below. Dinosaur species tier totals stay at 72 / 24 / 3.2 / 0.7 / 0.1 ([82](82-species-rarity-tiers.md)). Odds below are for **one purchased egg** (no run-size boost).

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
| 1 | Compy | Common | 26% |
| 2 | Raptor | Common | 22% |
| 3 | Gallimimus | Common | 9% |
| 4 | Microraptor | Common | 8% |
| 5 | Dimorphodon | Common | 7% |
| 6 | Archaeopteryx | Uncommon | 6% |
| 7 | Stegosaurus | Uncommon | 6% |
| 8 | Parasaurolophus | Uncommon | 5% |
| 9 | Pachycephalosaurus | Uncommon | 4% |
| 10 | Pteranodon | Uncommon | 3% |
| 11 | Triceratops | Rare | 1% |
| 12 | Brachiosaurus | Rare | 0.7% |
| 13 | Baryonyx | Rare | 0.5% |
| 14 | Ichthyosaurus | Rare | 0.5% |
| 15 | Plesiosaurus | Rare | 0.5% |
| 16 | Ankylosaurus | Epic | 0.2% |
| 17 | Elasmosaurus | Epic | 0.2% |
| 18 | Therizinosaurus | Epic | 0.15% |
| 19 | Quetzalcoatlus | Epic | 0.15% |
| 20 | T-Rex | Legendary | 0.04% |
| 21 | Spinosaurus | Legendary | 0.03% |
| 22 | Mosasaurus | Legendary | 0.03% |

| Rarity | Species | % total |
|---|---:|---:|
| Common | 5 | 72% |
| Uncommon | 5 | 24% |
| Rare | 5 | 3.2% |
| Epic | 4 | 0.7% |
| Legendary | 3 | 0.1% |

## Patterns (8, eggs and the dinosaurs hatched from them)

All 8 are equally likely (owner 2026-10-15: fusion needs the same species and pattern, so odds stay uniform for now).

| # | Pattern | Label | % |
|---:|---|---|---:|
| 1 | Blank | Common | 12.5% |
| 2 | Freckles | Common | 12.5% |
| 3 | Round spots | Common | 12.5% |
| 4 | Horizontal bands | Uncommon | 12.5% |
| 5 | Bold patches | Uncommon | 12.5% |
| 6 | Wavy stripes | Rare | 12.5% |
| 7 | Emerald islands | Epic | 12.5% |
| 8 | Diamond scales | Legendary | 12.5% |

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
