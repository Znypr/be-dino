# 85 Drop odds: dinosaurs, patterns and colors

Generated 2026-10-14 from the repo (`Config.ChestSpeciesWeights`, `EggGenetics`, `ProgressionConfig.EggColors`).
All numbers are **provisional** and show the odds of **one purchased egg** (no run-size boost; bigger runs and nests shift odds toward higher rarities, see [82](82-species-rarity-tiers.md)).

## Dinosaurs (22 species)

**Now** = current `main`. **Proposed** = Compy dominant (pending owner decision, because it speeds up fusion; see the fusion pacing note below).

| # | Dinosaur | Rarity | Now % | Proposed % |
|---:|---|---|---:|---:|
| 1 | Compy | Common | 26% | 40% |
| 2 | Raptor | Common | 22% | 14% |
| 3 | Gallimimus | Common | 9% | 7% |
| 4 | Microraptor | Common | 8% | 6% |
| 5 | Dimorphodon | Common | 7% | 5% |
| 6 | Archaeopteryx | Uncommon | 6% | 6% |
| 7 | Stegosaurus | Uncommon | 6% | 6% |
| 8 | Parasaurolophus | Uncommon | 5% | 5% |
| 9 | Pachycephalosaurus | Uncommon | 4% | 4% |
| 10 | Pteranodon | Uncommon | 3% | 3% |
| 11 | Triceratops | Rare | 1% | 1% |
| 12 | Brachiosaurus | Rare | 0.7% | 0.7% |
| 13 | Baryonyx | Rare | 0.5% | 0.5% |
| 14 | Ichthyosaurus | Rare | 0.5% | 0.5% |
| 15 | Plesiosaurus | Rare | 0.5% | 0.5% |
| 16 | Ankylosaurus | Epic | 0.2% | 0.2% |
| 17 | Elasmosaurus | Epic | 0.2% | 0.2% |
| 18 | Therizinosaurus | Epic | 0.15% | 0.15% |
| 19 | Quetzalcoatlus | Epic | 0.15% | 0.15% |
| 20 | T-Rex | Legendary | 0.04% | 0.04% |
| 21 | Spinosaurus | Legendary | 0.03% | 0.03% |
| 22 | Mosasaurus | Legendary | 0.03% | 0.03% |

| Rarity | Species | Now % total | Proposed % total |
|---|---:|---:|---:|
| Common | 5 | 72% | 72% |
| Uncommon | 5 | 24% | 24% |
| Rare | 5 | 3.2% | 3.2% |
| Epic | 4 | 0.7% | 0.7% |
| Legendary | 3 | 0.1% | 0.1% |

## Patterns (8, eggs and the dinosaurs hatched from them)

Every egg rolls one pattern; the hatched dinosaur keeps it. **Now** all 8 are equally likely. **Proposed** gives plain patterns the most weight.

| # | Pattern | Rarity (proposed) | Now % | Proposed % |
|---:|---|---|---:|---:|
| 1 | Blank | Common | 12.5% | 30% |
| 2 | Freckles | Common | 12.5% | 20% |
| 3 | Round spots | Common | 12.5% | 17% |
| 4 | Horizontal bands | Uncommon | 12.5% | 12% |
| 5 | Bold patches | Uncommon | 12.5% | 9% |
| 6 | Wavy stripes | Rare | 12.5% | 6% |
| 7 | Emerald islands | Epic | 12.5% | 4% |
| 8 | Diamond scales | Legendary | 12.5% | 2% |

## Colors (9, eggs and the dinosaurs hatched from them)

Each egg has **two** color slots (primary and secondary), rolled independently with these odds. Matching slots make a solid color; otherwise a blend share is rolled.

| # | Color | Rarity | % per slot | Both slots this color |
|---:|---|---|---:|---:|
| 1 | Cream | Common | 50% | 25% |
| 2 | Blue | Common | 26% | 6.76% |
| 3 | Green | Uncommon | 12% | 1.44% |
| 4 | Pink | Uncommon | 5% | 0.25% |
| 5 | Teal | Uncommon | 4% | 0.16% |
| 6 | Amber | Rare | 2.5% | 0.062% |
| 7 | Purple | Epic | 0.45% | 0.002% |
| 8 | Red | Legendary | 0.04% | 0% |
| 9 | Black | Legendary | 0.01% | 0% |

Rarity for colors is a label from the percentage: Common 25%+, Uncommon 4%+, Rare 1%+, Epic 0.1%+, Legendary below that.

## Fusion pacing note

Fusion needs the same species **and** the same pattern. Making Compy and the plain pattern much more common makes those matches much easier:

| Odds | First Gold (best cell, median heavy play) | Owner target |
|---|---:|---:|
| Compy 26%, uniform patterns | about 1.7 h | 1.7 h |
| Compy 40%, uniform patterns | about 1.1 h | 1.3 to 2.2 h |
| Compy 40%, weighted patterns | about 0.6 h | 1.3 to 2.2 h |

Decision pending (see Kanban). Until then `main` keeps the **Now** columns.
