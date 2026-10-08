# Egg Outcomes: Reconciled Contract

**Reconciled 2026-10-08 against GitHub main Build 020.** This contract separates **implemented source behavior**, **owner-directed target changes** and **archived earlier proposals**. [Main integration checklist](44-main-integration-checklist.md) and [22-creature integration](43-creature-runtime-integration.md) supersede the initial six-species / seven-color snapshot; [art vision](39-egg-appearance-shared-vision.md) governs unapproved artistic choices, and [Kanban](07-kanban.md) governs current task status. No paid-random launch or physical-device certification is implied.

**Build 020 implemented:** 22 species, nine palette colors, eight patterns, uniform mixed 1–99% gene coverage, matching-color 100% primary, and configurable current condition distributions. The owner-target 50/30/15/4.5/0.5 starting condition distribution and one egg per catch are **NOT implemented**. Historic earlier `3793653` / `14afd6e` review numbers remain in version-control history and in the earlier [acceptance record](39-crystal-shops-and-genetics-acceptance.md), not today's runtime authority.

## Owner target versus Build 020 runtime (2026-10-08)

**The owner now wants each catch earned during the run to produce one individual run egg to hatch.** Examples: 500 **food** points -> 15 catches -> 15 run eggs (e.g. 11 Common, 4 Uncommon), plus crystals and 1 separate bonus egg nest; 5,000 **food** points -> 150 run eggs (e.g. 80 Common, 50 Uncommon, 17 Rare, 3 Epic), 220 illustrative crystals and 6 offered nests, at most 5 claimable with five free nest slots. See [target reward economy](09-reward-economy.md) and [BD-044](07-kanban.md). This count mapping is **not implemented**; never answer future reward examples by adding 15 guaranteed direct Compys to 1-3 threshold eggs. Ordinary run eggs and separate bonus nests are distinct systems.

The outcome tables and mechanics **below** document current/legacy **per-egg** behavior, including 1/2/3 copy awards, Cracked failures, batch rarity boosts and purchase odds. The owner has **not** approved changing those independently from the catch->egg migration. Keep immutable saved outcomes and exact-current paid-random disclosure consistent with actual runtime until a versioned change is tested and approved.

## Committed Runtime Outcomes

One egg is one immutable award, not one dinosaur copy. A successful egg awards
1/2/3 copies of the same species with the same saved traits, with probabilities
70/25/5%. These are not independent hatch rolls for each copy. A failed Cracked
egg awards zero copies, consumes that egg and grants no crystal refund or
consolation. This is the provisional default already implemented, not an open rule.
Never subtract existing owned dinosaurs when an egg fails.

**Species catalog note:** the six-row Compy/Raptor/Triceratops/Stegosaurus/T-Rex/Ankylosaurus weighting table from the older Build 019 snapshot is **no longer a complete current odds table**. Build 020 uses the 22-species weights in [`src/shared/Config.luau`](../src/shared/Config.luau), enumerated dynamically by `EggOutcomeOdds`, and three implemented species tiers: **Common / Rare / Legendary**. The owner's reward examples additionally name **Uncommon / Epic**, which are **future progression requirements**, not current tier IDs. Reconcile taxonomy as part of [BD-044](07-kanban.md) before advertising those outcomes.

Purchased eggs cost 150 crystals, use the same ordered queue and have no run-batch
boost, event mutation or Shiny roll. They still roll condition, colors/blend,
quantity and 10% BIG. Queue-full or failed transactions must not debit the wallet.
Purchased eggs do not inherit the currently visible weather event.

Earned run batches boost species rarity, not copy count or color rarity. For N eggs
in that run batch, `B = 1 + (clamp(N,1,15)-1)*0.25`; multiply Common species weights
by 1, Rare weights by B and Legendary weights by B squared, then normalize. N is
the granted batch size, not lifetime eggs, wallet balance or eggs left after a claim.
The same batch boost applies to its eggs; hatching does not progressively reroll odds.
See `RewardMath.computeChestReward`. Direct run copies are a separate **legacy** reward route, not the intended egg-per-catch target. The 22-species distribution and three-tier rarity mapping are current Build 020 behavior, not the original six-species table.

> **Owner-directed future change (2026-10-08, BD-045; not yet implemented):** New **tier-0** condition odds must be **Cracked 50%, Dirty 30%, Normal 15%, Rainbow 4.5%, Astra 0.5%**. Total 100%. This supersedes the tier-0 odds below **as product intent**, not as implemented code. Existing six upgrade levels and tier-6 distribution below need an explicit monotonic retune/owner approval rather than pretending the old table is consistent with the new base. Keep Cracked's **20% hatch-success** rule separate from its **50% condition-selection probability**: unupgraded effective failure is **40% per egg** if the existing 80% Cracked failure stays. Existing eggs retain their committed immutable outcomes. Purchased random egg disclosure and exact server config must agree before a new version is live. [Implementation details](45-owner-feedback-shop-hud-world-weather-tasks.md#A-egg-conditions-and-game-economy--bd-045).

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

## Build 020 genes, patterns and historical authoring weights

**Verified against `ProgressionConfig.luau`, `EggGenetics.luau` and [Build 020 creature integration](43-creature-runtime-integration.md):** the current palette includes **nine** colors; weighted selection is per gene slot. Mixed pairs roll a **uniform integer 1–99%** primary share; matching pairs retain 100% of that family. All **eight** authored pattern IDs are implemented (Blank, Islands, Round Spots, Bold Patches, Horizontal Bands, Wavy Stripes, Diamond Scales, Freckles). The earlier seven-color / uniform 0–100% blend and clamped endpoints are **legacy schemas**, not the current default.

| Stored ID | Current display | Current weight per slot |
| --- | --- | ---: |
| `white` | Cream | 5000 |
| `blue` | Blue | 2600 |
| `green` | Green | 1200 |
| `pink` | Pink | 500 |
| `teal` | Teal | 400 |
| `gold` | Amber | 250 |
| `violet` | Purple | 45 |
| `red` | Red | 4 |
| `black` | Black | 1 |
| **Total** | | **10000** |

For a matching Black/Black pair the current weight is `(1/10000)^2 = 1 in 100 million` and it is a genuinely black-family pair without mixed-endpoint shortcuts. That is a **per-egg pair probability given the current private-test weights**, not a public odds promise. Display coverage uses saved distinct color regions and pattern-dependent UV maps in Build 020, rather than one average tint. Verify rendered source vs fallback path on each target device.

The **415-total palette** (100/100/100/40/40/15/15/4/1) and associated **1 in 172,225** pure-black example in [the shared egg art vision](39-egg-appearance-shared-vision.md) were an **earlier authoring draft**, not current implementation. Preserve as a visual/balance proposal; do not substitute it for `ProgressionConfig.EggColors` or reuse its odds in paid-item disclosure. Future tuning must version outcomes, retain earlier saved genes and update the exact final-outcome enumerator.

## Persistence And Reveal Contract

> **Downstream collector requirement (2026-10-08; BD-060/062):** once a successful egg grants one or more dinosaur copies, each customized/fused dinosaur must be persistently identifiable (stable instance ID or safe lazy stack-split) and traceable to the **immutable source egg** (pattern, colors/coverage, condition, Shiny/BIG and event info). Do **not** destroy or reroll this history when fusing Gold → Emerald → Diamond or purchasing aura/trail loadouts. True natural hatch probability is separate from deterministic earned fusion-stage prestige; **purchased cosmetics never factor into total rarity**. The current grouped-copy storage is not certified for this yet. [Full new system and migration](46-pattern-fusion-dino-identity-and-cosmetic-progression.md).



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

For purchased Build 020 eggs, an individual **successful** outcome has probability:

`P(species) * P(copy count) * P(condition) * P(hatch success | condition)`
`* P(primary color) * P(secondary color) * P(saved share | gene pair)`
`* P(pattern) * P(size)`

The saved-share factor is **1/99 for each mixed-gene share 1–99**, or 1 for 100%-matching gene pairs; pattern weight is 1/8 in current code. These replace the obsolete seven-color `1/101` / no-pattern formula. Shiny/event mutation are absent for purchased eggs in the current policy-gated flow. Aggregate hatch failure is `P(Cracked)*0.8`. Sum all successful outcomes plus failure to exactly 100% before rounding. Build 020's implemented disclosure page reported **37,683,361 enumerated final entries** in its bounded Studio test ([integration evidence](44-main-integration-checklist.md)); the earlier 890,820-entry v1 figure is historical.

Provide a searchable/paginated pre-purchase Details view with itemized final
outcomes and numeric percentages, not only factor tables or a multiplication
instruction. Identical-probability items can be grouped only with their per-item
odds and an explicit item list; do not confuse group odds with per-item odds.
The **implemented** nine-color/eight-pattern version must be enumerated according to its actual 1-versus-99 gene-pair share possibilities. Any future change to color weights, conditions, patterns or trait odds requires fresh disclosure, no stale cached legacy odds.

Use enough decimal precision for rare outcomes, a rounding notice and tests for
normalization, every tier, lowest nonzero probabilities and conditional hatch risk.
Display next-tier distributions before condition upgrades; reject stale confirmation
if the player's tier/distribution changed. `EggOutcomeOdds.luau` now lazily enumerates
final outcomes and `EggOutcomeView.luau` exposes numeric per-outcome percentages,
filters and page selection through FINAL OUTCOME DETAILS before purchases. The
condition-upgrade confirmation links to the next tier, rather than current odds.
Filters retain unconditional probabilities and hide the aggregate failure row;
clearing filters restores it. Factorized ShopOdds remains supplementary.

The enumerator supports historical **legacy** 0–100 and **clamped** 1–99 gene modes for backward compatibility. Current `EggGenetics.BlendMode="uniform"` is **already set in Build 020**. Current Config, condition, color, pattern and quantity tables drive enumeration; no hardcoded six-species list or generated multi-million-row asset is required.

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

- Validate current 22-species / nine-color / eight-pattern migration and deterministic saved outcomes, including any explicit next schema version, without changing old saved awards.
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
