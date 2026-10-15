> **Updated 2026-10-15 (BD-165):** the boost below was re-tuned for 4 / 40 eggs per run: `SpeciesRunBoost = {1,1,1.1,1.1,1.1}`, full at 40 eggs, nest luck `rarityBoostEggs = 40`. The 40 / 400-egg rows and the owner example mixes are history; see [docs/89](89-catch-rate-4.md).

# 82 Five species rarity tiers (BD-044 taxonomy), 2026-10-14

Status: **Review / test**. Code, offline tests and simulation are done; Studio and phone checks are pending.

## What changed
The game had 3 species tiers (Common, Rare, Legendary). The owner's reward examples (docs/09)
need 5. Species are now **Common, Uncommon, Rare, Epic, Legendary** (`Config.SpeciesRarityNames`).

### Tier mapping (lead decision, PROVISIONAL)
| Tier | Species | Base weight (sum 100) |
| --- | --- | ---: |
| Common | compy 26, raptor 22, gallimimus 9, microraptor 8, dimorphodon 7 | 72 |
| Uncommon | archaeopteryx 6, stegosaurus 6, parasaurolophus 5, pachycephalosaurus 4, pteranodon 3 | 24 |
| Rare | triceratops 1, brachiosaurus 0.7, baryonyx 0.5, ichthyosaurus 0.5, plesiosaurus 0.5 | 3.2 |
| Epic | ankylosaurus 0.2, elasmosaurus 0.2, therizinosaurus 0.15, quetzalcoatlus 0.15 | 0.7 |
| Legendary | tyrannosaurus 0.04, spinosaurus 0.03, mosasaurus 0.03 | 0.1 |

Big, famous predators sit at the top (T. rex, Spinosaurus, Mosasaurus), so the rarest pull is also the
most exciting one for children.

### Run-size boost (replaces the old 15-egg cap)
The old boost `B = 1 + 0.25*(min(N,15)-1)`, raised to the tier index, reached its cap at 15 eggs. At
the owner's 40 eggs per 500 food, **every** run was at full boost: only about 25% Common and 28%
Legendary, the opposite of "common-heavy". It is replaced by a per-tier gain that grows linearly up
to 400 eggs:

`weight(tier) = base * (1 + s * (SpeciesRunBoost[tier] - 1))`, `s = (clamp(N,1,400) - 1) / 399`,
`SpeciesRunBoost = {1, 1.9, 4.7, 4.5, 4}`.

| Run | Common | Uncommon | Rare | Epic | Legendary | Owner example |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 egg (shop) | 72% | 24% | 3.2% | 0.7% | 0.1% | n/a |
| 40 eggs (500 food) | 27.8 | 10.1 | 1.7 | 0.4 | 0.05 | 29 / 11 |
| 400 eggs (5,000 food) | 211 | 134 | 44 | 9.3 | 1.2 | 213 / 133 / 45 / 9 |

Nest luck tier 1 now uses `rarityBoostEggs = 200` (it was 15, the old maximum), so nest eggs stay
luckier than a short run. Shop eggs (one egg) use base odds, which is what `ShopOdds` discloses.
`RunRewardConfigVersion` is 3 for new rewards. Already banked eggs keep their committed species.

## Saved data
- `metrics.rarest` and `revealSkip` held values on the old 1..3 scale. Profiles get an additive
  `rarityScale = 5` field and are migrated once on load (no DataStore-wide rewrite):
  - rarest: old Common becomes 1..2, old Rare 2..3, old Legendary 4..5. It starts at the lowest new
    tier and rises only to the best species the player owns *inside that old band*, so it never
    overclaims.
  - reveal skip: old Common becomes {Common}, old Rare {Uncommon, Rare}, old Legendary {Epic, Legendary}.
  - malformed old values are still rejected unchanged, as before.
- The rarest leaderboard reads and writes a new ordered store `<ProfileDataStoreName>_rarest_v2`;
  players refill it from their migrated profile on the next publish. `_v1` is left untouched.

## Client
- One rarity colour set (`Theme.RarityColors`): grey, green, blue, purple, gold. It is shared by species
  cards, the hatch reveal and the potion shop.
- Settings: five reveal-skip buttons (name over SHOW/SKIP).
- Hatch sounds: Common/Uncommon use the common sound, Rare the rare one, Epic/Legendary the big one.
- Food guide copy now reads the live catch rate ("Eat 500 food to earn 40 eggs").

## Evidence
`tools/verify_rewards.py` "Species tiers" section, run in CI. It checks that every species has a tier
and a weight, that the weights sum to 100, that each tier has 3 or more species, and that rarer tiers
are always less likely. Bigger runs expose rarer tiers, the boost is capped at 400, the 40- and 400-egg
mixes sit within tolerance of the owner examples, and 40,000 seeded draws through `computeChestReward`
match the analytic shares. It also covers 7 legacy migration cases (rarest and skip, idempotent on
reload), rejection of a malformed old value, and new profiles starting on scale 5. The reveal-skip and
Sfx tests were updated for five tiers. The full CI command list passed locally.

## Not verified
Studio layout of the five skip buttons and the grey Common cards, the leaderboard store switch on a
real DataStore, and the phone. Balance numbers are provisional.
