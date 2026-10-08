# Egg Outcomes: Reconciled Contract

Updated 2026-10-08 after checking GitHub through `14afd6e`, including the accepted
Astra/combination review in `224f0d7`. This fills missing design decisions using
provisional defaults authorized by the owner. It does not change gameplay code,
approve public balance, certify paid-random compliance or complete Studio artwork.
The [shared appearance vision](39-egg-appearance-shared-vision.md) governs visuals;
the [acceptance record](39-crystal-shops-and-genetics-acceptance.md) governs actual passes.
Keep current implementation and next-build targets distinct.

Runtime numbers below describe committed gameplay baseline `3793653`, not an
assertion about concurrent uncommitted creature/genetics edits. During this review,
new local work adds patterns/coverage and expands the species catalog; it is left
untouched and needs its own migration, odds and Studio acceptance evidence.

## Committed Runtime Outcomes

One egg is one immutable award, not one dinosaur copy. A successful egg awards
1/2/3 copies of the same species with the same saved traits, with probabilities
70/25/5%. These are not independent hatch rolls for each copy. A failed Cracked
egg awards zero copies, consumes that egg and grants no crystal refund or
consolation. This is the provisional default already implemented, not an open rule.
Never subtract existing owned dinosaurs when an egg fails.

| Species | Purchased / one-egg base odds | Species rarity |
| --- | ---: | --- |
| Compy | 40% | Common |
| Raptor | 30% | Common |
| Triceratops | 15% | Rare |
| Stegosaurus | 10% | Rare |
| T-Rex (`tyrannosaurus`) | 3% | Legendary |
| Ankylosaurus | 2% | Legendary |

Purchased eggs cost 150 crystals, use the same ordered queue and have no run-batch
boost, event mutation or Shiny roll. They still roll condition, colors/blend,
quantity and 10% BIG. Queue-full or failed transactions must not debit the wallet.
Purchased eggs do not inherit the currently visible weather event.

Earned run batches boost species rarity, not copy count or color rarity. For N eggs
in that run batch, `B = 1 + (clamp(N,1,15)-1)*0.25`; multiply Common species weights
by 1, Rare weights by B and Legendary weights by B squared, then normalize. N is
the granted batch size, not lifetime eggs, wallet balance or eggs left after a claim.
The same batch boost applies to its eggs; hatching does not progressively reroll odds.
See `RewardMath.computeChestReward`. Direct run reward tiers are a separate legacy
reward route and must not be advertised as this six-species egg distribution.

## Conditions And Upgrade Distributions

Exactly one condition is assigned using the player's condition-upgrade level when
the new egg is prepared. Upgrades never alter existing queued/overflow eggs.
Cracked succeeds 20%; every other condition succeeds 100%. Successful Cracked
and Dirty apply 0.8x speed AND growth, Normal 1x, Rainbow 1.2x, Astra 1.8x.
These factors compose with authorized buffs before shared caps of 2.2x speed and
8x growth. BIG, Shiny, colors and shell patterns add no stats.

| Upgrade | Account level / crystal cost | Cracked | Dirty | Normal | Rainbow | Astra | Overall failed egg |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | Starting odds | 20% | 25% | 45% | 9% | 1% | 16% |
| 1 | 3 / 100 | 17% | 23% | 47% | 11% | 2% | 13.6% |
| 2 | 8 / 300 | 14% | 21% | 48% | 14% | 3% | 11.2% |
| 3 | 16 / 800 | 11% | 19% | 49% | 17% | 4% | 8.8% |
| 4 | 28 / 1800 | 8% | 17% | 50% | 20% | 5% | 6.4% |
| 5 | 45 / 4000 | 5% | 15% | 51% | 22% | 7% | 4% |
| 6 | 60 / 8500 | 2% | 12% | 51% | 25% | 10% | 1.6% |

Each condition distribution totals 100%. Failure is contained within Cracked,
not an additional condition probability. At tier 0, successful Cracked is 4% and
failure 16%; at tier 6, successful Cracked is 0.4% and failure 1.6%.
Purchasing an upgrade must show the current and next distributions numerically,
including changed overall hatch failure, before confirmation.

## Independent Size, Shiny And Weather Mutation

Normal size is 90%, BIG 10%, in every weather. BIG adds 20% visual size, not speed,
growth or reward quantity. Preserve collider/range fairness rather than treating
visual enlargement as permission to increase collision or catch reach.

Earned eggs have 5% Shiny during Volcano, Northern Lights, Earthquake and Blood
Moon; otherwise 0%. Shiny and BIG roll independently. In an eligible irregular
event: plain/normal 85.5%, plain/BIG 9.5%, Shiny/normal 4.5%, Shiny/BIG 0.5%.
Shiny changes sparkle presentation, not condition or stats. These probabilities
describe egg traits, not guaranteed successful dinosaur awards from Cracked eggs.

| Catch-time weather | Eligible mutation | Chance per eligible egg | Mutation speed / growth |
| --- | --- | ---: | --- |
| Clear | None | 0% | 1x / 1x |
| Rain | Dewdrop | 2% | 1x / 1.08x |
| Thunderstorm | Charged | 4% | 1.10x / 1x |
| Blizzard | Frost | 4% | 1x / 1.12x |
| Earthquake | Seismic | 5% | 1x / 1.15x |
| Volcanic Bloom | Ember, visually Magma | 7% | 1.04x / 1.18x |
| Northern Lights | Aurora | 7% | 1.08x / 1.12x |
| Blood Moon | Blood Moon | 8% | 1.12x / 1.10x |

Use stored catch-event metadata, not the event active at hatch. A mutation effect
on a pending egg means the mutation was committed, not merely eligible. Only one
event mutation is assigned; it can coexist with condition, BIG, Shiny and colors.
Failure still awards no dinosaur even if that egg has a mutation or Shiny.
Event perk/roll values remain provisional balance. Do not add Cosmic/Eclipse IDs
merely because they appeared in visual references. Gold/Diamond fusion materials,
purchased auras and the Astra trail are separate systems.

## Current Colors Versus The Next Build

Current `EggGenetics` independently draws White/Blue/Green/Pink/Gold/Violet/Black
with weights 5000/3000/1200/500/250/49/1 out of 10000 per slot. It saves a primary
share from 0 through 100 uniformly (101 outcomes), including matching pairs.
The current renderer averages the colors into one tint. Two visibly separate color
regions and the eight independently rolled patterns are NOT integrated yet.

Current Black/Black genes have probability 0.000001% (1 in 100 million). This is
not the current probability of a visually pure-black egg: mixed-pair 0/100 endpoints
can also look pure black. Do not advertise those two different events as equivalent.
The newer vision intentionally excludes mixed endpoints to prevent that shortcut.

### Provisional Next-Build Defaults

Use these explicit defaults until owner tuning, preserving the newer hierarchy:

| Stored color ID | Display family | Weight per slot |
| --- | --- | ---: |
| `white` | Cream / ivory | 100 |
| `green` | Green | 100 |
| `blue` | Blue | 100 |
| `teal` | Teal | 40 |
| `pink` | Pink | 40 |
| `violet` | Purple | 15 |
| `gold` | Amber | 15 |
| `red` | Vivid red | 4 |
| `black` | Black / charcoal | 1 |

Total weight 415. Existing IDs white/violet/gold are retained; display names do
not introduce competing neutral IDs or change Gold fusion. New teal/red IDs need
palette, validation, renderer and migration support before any production roll.
Matching genes use 100% primary; differing genes uniformly use integer 1-99%.
Generate mixed shares directly from 99 equally likely values (for example
`1 + floor(U*99)` with U in [0,1)); do not clamp a 0-100 roll to 1-99, which doubles
the endpoint probabilities. A clamped distribution must never be disclosed as uniform.
Pure Black/Black is 1 in 172225; pure Red/Red is 16/172225, about 1 in 10764.
This is a deliberate provisional rebalance, not today's live/private-test odds.

Roll each of the eight canonical patterns with equal 1/8 weight (12.5%) for now:
Blank, Islands, Round Spots, Bold Patches, Horizontal Bands, Wavy Stripes,
Diamond Scales and Freckles. Pattern does not affect species, condition or stats.
Store its ID once. Use the authoring IDs in the shared vision as the mapping contract.
This closes the missing pattern probability decision without claiming implementation.

Render saved shares as visible color coverage, not uniform tint. Matching pairs
retain tonal contrast, especially double black, without becoming a second color
gene. Use deterministic masks/seeds for stable egg-to-dinosaur inheritance.
The eight-pattern design, accepted Astra streaks and mutation smoke retain separate
layers; Rainbow runtime review and mutation draft approval remain open.

## Persistence And Reveal Contract

New-version target: save an explicit genetics/distribution version with condition,
hatch success, pattern ID, two color IDs and integer share. Save species, quantity,
event/mutation, Shiny, BIG, batch identifier and stable order in the same immutable
reward metadata. These are next-build schema requirements, not current fields.

Existing saved eggs/dinosaurs retain their exact v1 genes, 0/100 endpoints, palette,
success and rewards; never reroll, rename stored IDs or recompute their old odds.
Treat missing version as legacy v1. Assign a missing pattern a deterministic legacy
fallback, not a random new pattern. Update variant keys without losing quantities
or merging distinct earned traits. Unknown IDs must not silently grant better stats.

Reveal one egg at a time for five seconds, ascending species rarity within its
run batch. Stable ties retain original order. BIG, color rarity, condition and Shiny
do not change this species-rarity sorting rule for now. Closing/rejoining resumes
the unclaimed queue without rerolling or double granting; overflow preserves metadata.
Cracked failure still receives its reveal interval and a clear no-dinosaur result.

## Complete Outcome Disclosure: Implemented, Acceptance Still Open

For purchased eggs today, a successful joint outcome's probability is:

`P(species) * P(copy count) * P(condition) * P(hatch success | condition)`
`* P(primary color) * P(secondary color) * (1/101) * P(size)`

Shiny/event mutation are guaranteed absent and must be stated. Failure can be
one aggregate final outcome with probability `P(Cracked)*0.8`, since no dinosaur
is awarded regardless of its other rolled metadata. Sum all successful outcomes
and this aggregate failure to exactly 100% before rounding. The current v1 variant
key space has 890820 successful combinations plus that failure outcome.

Provide a searchable/paginated pre-purchase Details view with itemized final
outcomes and numeric percentages, not only factor tables or a multiplication
instruction. Identical-probability items can be grouped only with their per-item
odds and an explicit item list; do not confuse group odds with per-item odds.
The next palette/pattern version needs its own enumeration, including the 1 versus
99 share outcomes for matching versus differing genes. Never reuse v1 disclosure.

Use enough decimal precision for rare outcomes, a rounding notice and tests for
normalization, every tier, lowest nonzero probabilities and conditional hatch risk.
Display next-tier distributions before condition upgrades; reject stale confirmation
if the player's tier/distribution changed. `EggOutcomeOdds.luau` now lazily enumerates
final outcomes and `EggOutcomeView.luau` exposes numeric per-outcome percentages,
filters and page selection through FINAL OUTCOME DETAILS before purchases. The
condition-upgrade confirmation links to the next tier, rather than current odds.
Filters retain unconditional probabilities and hide the aggregate failure row;
clearing filters restores it. Factorized ShopOdds remains supplementary.

The enumerator supports committed legacy shares, the concurrent pattern generator's
clamped endpoint distribution (1/99 endpoints each 2/101, interior each 1/101), and
an explicit future `EggGenetics.BlendMode="uniform"` contract. It does not silently
claim the proposed uniform distribution is already implemented. Current Config,
condition, color, pattern and quantity tables drive enumeration; no hardcoded
six-species list or generated multi-million-row asset is required.

Offline execution validates complete normalization, actual blend-roll parity,
every upgrade tier, filtering, page boundaries and nonzero rare precision. Owner
Studio navigation and Black/Black rows were captured before the test instance
closed. Final rounding-notice/row-height tweaks, next-tier navigation, desktop and
phone emulator acceptance remain unverified in Studio. See the bounded
[evidence record](evidence/2026-10-08-egg-outcome-details/README.md).

Latest integration acceptance: Build 020 now passes actual current/next-tier GUI
navigation and visible widget text-fit checks, including the final rounding notice.
The next-tier view shows 13.6% failure without upgrading the tier-0 profile. Page
clamping passes a FocusLost helper, but real typed page interaction and desktop/
phone acceptance remain open. See [main integration evidence](evidence/2026-10-08-main-integration/README.md).

Keep server PolicyService eligibility fail-closed, and keep `CrystalPacksEnabled`
and `PaidRandomItemsEnabled` false until disclosure, restrictions and payment tests
are accepted. Earned free-run eggs remain the non-paid route; one fungible wallet
does not establish whether a particular balance was earned. No new paid bypass or
trading feature is authorized here. See the current
[Roblox paid-random-item policy](https://create.roblox.com/docs/production/monetization/paid-random-items).

## Next Acceptance Work

- Integrate versioned palette/pattern/coverage without changing old saved outcomes.
- Complete Studio current/next-tier interaction and desktop/phone acceptance of the
  implemented final-outcome disclosure, then obtain paid-policy acceptance.
- Upload/bind granular shell/pattern/condition/mutation layers; verify combinations,
  Shiny/BIG and reduced effects on desktop, phone emulator and physical target phone.
- Verify real receipt delivery, retries, restriction handling and spending leaderboard
  in a controlled private experience; do not touch existing persistent player data.
- Retest saved-profile restart, non-owner assets and multiplayer/load; retain partial
  statuses until actual evidence exists. The existing two-client shop pass is bounded.
  The latest published non-owner join attempt is blocked by experience access,
  not proof of failed mesh permissions; see [access verification](40-mesh-access-verification.md).
