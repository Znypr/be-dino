# Crystal shops, egg genetics and progression

**Requested:** 2026-10-08. **Status:** Implemented for isolated private testing; not public balance or monetization approval. See [implementation and actual acceptance](39-crystal-shops-and-genetics-acceptance.md). Sections below retain the original requested design; the implementation record supersedes their Todo/proposal status.
**Canonical status:** [BD-035–041 in Kanban](07-kanban.md). **Existing systems:** [Build 018 progression](31-build018-progression-test.md), [Build 019 events and cosmetics](35-event-mutations-and-visual-upgrade.md).

**Reconciled outcome decisions:** [Egg outcome contract](41-egg-outcomes-contract.md)
now fills the missing provisional pattern distribution, next palette/blend rules,
failure/copy semantics, migration requirements and full-disclosure acceptance.
Its current-versus-next-build distinctions supersede older Todo/unspecified wording
below. The proposed palette/pattern version is not implemented or public balance approval.

**Visual decision reference:** [Shared egg appearance vision](39-egg-appearance-shared-vision.md) consolidates the subsequent Blender review: eight patterns, two-color coverage and exceptional pure-color rarity, matte shell, reusable damage/condition overlays, and engulfing anime-like mutation smoke. Rainbow/Astra rework resumed; the owner accepted bright Astra opal highlights as curved vertical streaks, while Rainbow keeps multicolored unoutlined stars. Their authored-layer integration remains open. Exact authoring weights and latest aura renders remain provisional; this does not certify gameplay implementation.

Concurrent gameplay baseline: [BD-042 hatching/traits/leaderboards](37-hatching-traits-and-leaderboards.md)
implements five-second run-ordered reveals, 5% event Shiny and 10% independent
BIG. The shop/genetics integration now uses **1.2x BIG**, world/preview sparkles,
immutable conditions/colors, ten trails and earned-crystal random eggs. Robux
packs have six verified real IDs; prompts remain unavailable until disclosure,
policy and receipt release checks pass. [Catalog and icons](../resources/monetization/product-icons/README.md).

> **Owner's clarified rewards direction, 2026-10-08:** The run's **catches become individual hatchable run eggs** (15 catches = 15 run eggs in the 500-food example), with crystals and separate bonus **egg nests**. Five nest spots are intended; six offered nests allow at most five claims into five empty slots. This supersedes the old direct-copy + one-to-three threshold-egg design as product intent, **not yet as runtime implementation**. See [reward economy](09-reward-economy.md), [AI instructions](../AGENTS.md) and [BD-044](07-kanban.md). Crystal amounts and nest grants remain unapproved formulas.

## Player loop

> **Latest progression/Shop direction, 2026-10-08:** [Advanced fusion and individual dino cosmetics](46-pattern-fusion-dino-identity-and-cosmetic-progression.md) supersedes the old globally shared look inventory as **future owner design**, not current Build 020 source. A living dino may **purchase multiple aura/trail appearances and switch between them**, but **on fusion all selected input dinosaurs and ALL their owned cosmetics are consumed; the NEW output inherits neither**. Gold requires ten same-species/same-pattern inputs; Emerald then Diamond follow. Guaranteed tier/stat progression is separate from **fresh ingredient-weighted output traits** and future wheel reveals. Fusion recipient selection, source lineage, paid purchase loss warnings/migration and conditional odds require [BD-057–065](07-kanban.md). Current code and legacy purchases remain untouched.



1. Play a run, catch food, and earn eggs and **crystals** when the run settles. End-of-run rewards may also contain a crystal reward to **unbox/reveal**. Crystals are also scattered across the live map for players to pick up. Define earned crystal quantities, crystal containers and drop odds in configurable server tables.
2. Optionally purchase crystal packs with **Robux** in the Crystal Shop. Receipts grant the currency exactly once through a server-owned purchase pipeline.
3. Spend crystals on **random eggs**, **trail unlocks**, **temporary potions**, and **Condition Shop upgrades**.
4. Earn persistent account levels through play. Account levels unlock progressively stronger trails and higher condition-upgrade tiers; purchasing crystals alone does not bypass those gates.
5. New eggs receive immutable attributes (pattern, condition, two weighted colours and blend, size, shiny flag, and any event mutation eligibility). The egg preview is a composition of reusable layers. Eggs are hatched from the existing sequential queue, with the server committing the outcome once.
6. Hatched dinosaurs inherit the egg's chosen blended colours, their allowed condition stat modifier, visual size, shiny status and any successfully rolled mutation. A failed hatch is possible only for the **Cracked condition**, with **20% hatch success** (80% failure). Failed-hatch consolation remains unspecified.

**Separation of systems:** Pattern is cosmetic shell art; **condition** sets hatch risk/stat strength; **event mutation** is a separate chance/perk/VFX result; **shiny** is an independent sparkle trait; **size** is independent of stats; **colour genes** are cosmetic. Do not conflate event eligibility with guaranteed mutation.

## Crystals: earning, purchase and spending

- **Earned:** random validated map pickups (already exists), run-end rewards, and possibly a separate crystal reveal/unbox reward. Do not let one food pickup grant unintended duplicate currency; the exact run formula and reward packaging are Todo.
- **Purchased:** Robux crystal packs, with storefront confirmation and idempotent receipt processing. No client-authoritative balance, and no paid-only gameplay resource.
- **Spent:** random egg rolls that join the existing pending hatch queue; permanent trail products; consumable speed/growth potions; repeatable escalating Condition Shop levels.
- **Persistence:** single wallet ledger, atomic server-side debit/credit with unique transaction IDs, replay/receipt protection, profile migration, and failure-safe settlement. Audit currency earning rate versus catalog prices.
- **Fairness/compliance:** because Robux buys crystals which can buy **random-result eggs**, review Roblox's current paid-random-item rules, odds disclosure and relevant regional/age restrictions before shipping. If needed, separate bought-currency eligibility from paid-random purchases or provide a compliant alternative. Do not launch or advertise an unverified policy flow.

## Trail Shop: ten account-level-gated tiers

Replace/extend the existing **three cosmetic trails** (Fern Drift, Tidal Wake, Nova Ribbon) with a **ten-tier catalog**; migrate owned/equipped items without deleting or silently downgrading them. All trails have coloured walking/running VFX behind the dinosaur. **Normal White** is the free default. **Astra** is the highest tier, with multicolour glow and glitter particles. The **current Build 020 test catalog** increases crystal price, required level and movement speed by trail tier. The owner now wants fusion to be the **main stat booster**, and trail/aura purchases **per dinosaur with freely interchangeable owned styles**. How legacy paid trail stats are preserved or decoupled from appearance requires a separate migration decision under BD-058/059; do not silently change existing player benefits.

**Provisional illustrative balance, not approved:**

| Tier | Trail | Colour/effect when walking | Account level | Crystals | Speed |
|---:|---|---|---:|---:|---:|
| 1 | Normal White | Simple white trail | 1 | 0 | 1.00x |
| 2 | Fern Drift | Green leaf motes | 3 | 100 | 1.02x |
| 3 | Tidal Wake | Blue water ribbon | 6 | 250 | 1.04x |
| 4 | Ember Trail | Orange sparks | 10 | 500 | 1.06x |
| 5 | Violet Pulse | Purple glowing wake | 15 | 900 | 1.08x |
| 6 | Electric Arc | Cyan electric sparks | 21 | 1,500 | 1.10x |
| 7 | Frost Comet | Pale-blue crystal mist | 28 | 2,400 | 1.12x |
| 8 | Solar Flare | Golden star streak | 36 | 3,600 | 1.14x |
| 9 | Cosmic Prism | Prismatic star dust | 45 | 5,500 | 1.16x |
| 10 | **Astra** | Iridescent trail and glitter particles | 60 | 8,500 | 1.18x |

Level means a **persistent account progression level**, **not** temporary run growth/catches. How account XP is earned, actual price curve, final speed curve and total speed cap require balancing before release. Server verifies level and ownership, applies a bounded speed multiplier and validates movement. Test interactions with speed potions, weather and condition bonuses; high tiers must not create unavoidable chases or immediate pay-to-win purchases. Reduced-effects mode suppresses VFX, not authorized stats.

## Potions

- Crystals purchase consumable potion inventory through the existing Potion Shop. Include a **5-minute Speed Potion**, with displayed speed multiplier and expiration. Growth Potion variants may remain from the current shop.
- The server owns duration and buffs. Same-type replacement, expiry during offline time, duplicate purchase/use protection, buff caps and synchronization with weather/trails/conditions must be verified.
- Prices, strengths, stack rules and rarity variants remain configurable; reuse the current potion infrastructure rather than creating a second purchase system.

> **New owner target (2026-10-08, BD-045):** Starting condition distribution **50% Cracked, 30% Dirty, 15% Normal, 4.5% Rainbow, 0.5% Astra**. The unchanged prototype Cracked-success rule would imply **40% overall failed eggs** at this starting tier; verify this user experience during balancing. Six upgrade-tier probabilities need redesign, with live odds/disclosure kept aligned with server version. This does not assert the current Build 020 weights were changed; see [detailed task specification](45-owner-feedback-shop-hud-world-weather-tasks.md) and [current-vs-target contract](41-egg-outcomes-contract.md).

## Egg Condition Shop: permanent odds upgrades

The **condition is assigned when an egg is earned or purchased**, not on opening the hatching UI. A Condition Shop permanently improves the player's odds of drawing good conditions for **future new eggs**. Each upgrade level costs more crystals and requires a higher persistent account level. Existing eggs do not reroll when the shop upgrades.

| Egg condition | Hatch result | Resulting dinosaur's base stats |
|---|---|---:|
| **Cracked** | **20%** chance to hatch a dinosaur; **80%** failure | **80%** if it hatches |
| **Dirty** | Dinosaur hatches | **80%** |
| **Normal** | Dinosaur hatches | **100%** |
| **Rainbow** | Dinosaur hatches | **120%** |
| **Astra** | Dinosaur hatches | **180%** |

- **Confirmed by the user on 2026-10-08:** Cracked hatch success is **20%**, and condition factors affect **both movement speed and growth intake**. Persist the success/failure outcome once on the server; retries and reconnects must not reroll it. Failed-hatch consolation is still unspecified and must not be described as an implemented reward.
- The shop raises probability of Rainbow/Astra and lowers Cracked/Dirty odds as upgrade levels increase. Do not guarantee Astra at a finite tier unless separately approved. Each tier's full distribution must sum to 100% and be fixed/configurable, testable and disclosed when necessary.
- Apply the **0.8/1.0/1.2/1.8 factors to movement speed and growth intake**, before the final shared speed/growth caps. Cracked and Dirty must genuinely permit 0.8x values; a minimum-1 multiplier clamp would incorrectly remove their penalty. Keep condition factors independent of size, shiny and cosmetic colour. The existing 2.2x speed and 8x growth caps remain the starting safety limits, pending interaction tests with trails, weather, mutations and potions.
- **Condition `Cracked` is a separate condition field**, not one of the eight selected shell patterns. If legacy code has a cosmetic `cracked` pattern, reconcile its ID/migration deliberately; do not conflate it with condition damage.
- Existing visual conditions such as Frosted, Mossy and Shiny are **not** part of these five stat-bearing condition tiers. Retain them as cosmetic modifiers or migrate deliberately, never silently give them implied 80–180% stats.

## Egg colours, sizes and shiny

- **Two colour slots per egg:** `primaryColorId` and `secondaryColorId`, drawn independently from a configurable weighted rarity palette. Example anchors: **white = ordinary**, **blue = common**, **black = exceptionally rare**. Complete palette, actual relative weights and rarity names are Todo.
- **Random blend proportion:** server stores one saved color share; define explicitly whether the production field uses 0–1 or integer percentages. The newer art direction uses visible two-color coverage (for example 20% green/80% blue), not only an averaged uniform RGB tint. The authoring draft uses 1–99% for different colors and 100% for matching genes, preserving exceptional pure-black rarity and tonal pattern contrast. Exact production distribution/endpoints remain a reconciliation task; the earlier generic 0–100% proposal is not final. Egg and dinosaur use the **same saved colors and share**; do not reroll at hatch. See the shared vision for provisional weights and deterministic placement requirements.
- **Two egg sizes only:** **Normal** and **Big**. A Big egg produces a dinosaur with **1.20x visual model scale**, but **no extra base gameplay stats or speed from size**. This supersedes the earlier small/medium/big idea. Validate collider/range fairness and keep the shared egg art aligned; size can be a UI scale property.
- **Shiny** is an independent random property/flag, not a condition tier. It adds visible sparkling effects to the hatched **dinosaur** and its **collection/preview image** (and to the egg preview where practical). No stat bonus is specified. Odds remain Todo.
- Persist all assigned traits and the resulting hatch exactly once. UI can preview an earned egg's stored attributes, but cannot draw or reroll them.

## Modular egg artwork and Blender pipeline

Source model is one locked `Egg_Master` mesh, fixed camera, floor tile and lighting. Prepare high-quality source materials and VFX via Blender MCP; **do not** treat a generated contact sheet as a shippable sprite pack.

- Render a background separately (opaque), floor tile (transparent outside), and one base egg (transparent outside).
- Export pattern markings and condition surface passes **with the exact same egg silhouette mask**, no opaque duplicate eggs. Shiny sparkle belongs in its separate effect pass; size is applied as a shared scale.
- Render event mutations as surrounding, engulfing smoke/energy/particles in reusable transparent layers, not painted shell marks. Foreground wisps may overlap the lower shell; preserve the underlying color/pattern identity. A mutation's display on the unhatched egg can indicate event eligibility; it does not promise a mutated hatch unless already settled by server.
- Export at 1024px or higher and downsample to **512 x 512 RGBA PNG**. Verify exact image dimensions, true alpha, mask identity, camera alignment, edge bleed and small mobile previews automatically.
- The Blender review now has eight authored patterns, color-mix examples, Cracked/Dirty overlays and seven smoke-aura drafts, inspected with the retained tile and grassy backdrop. Magma styling maps to existing Ember. The owner accepted Astra's brighter curved-vertical opal direction after resumed Rainbow/Astra rework; selected combination renders and alpha checks are recorded in the shared vision. These are authoring results, not uploaded/integrated runtime acceptance. Keep editable `.blend` sources and produce an upload/Roblox asset-ID manifest; validate combinations, performance and visible quality on target devices.

## Implementation / acceptance breakdown

- **BD-035 | Egg render pipeline:** lock mesh/camera/mask; produce truly aligned, high-quality 512px RGBA assets and verify layered stacking in Studio.
- **BD-036 | Crystal economy:** award on completed runs and crystal reveals in addition to map pickups, implement/verify Robux pack receipts and wallet accounting, clarify compliance restrictions.
- **BD-037 | Crystal random eggs:** crystal purchase, weighted species/egg outcome, queued hatching, disclosure and idempotency; queue-full behavior must not destroy purchases.
- **BD-038 | Ten trails / account levels:** account XP/level progression, gated escalating crystal prices, 10 VFX + speed tiers, migration from 3 trails and speed-cap/multiplayer checks.
- **BD-039 | Potion integration:** crystal-priced five-minute Speed Potion; preserve existing variants and expiry logic.
- **BD-040 | Condition Shop:** weighted assignment, 5 condition tiers, Cracked hatch failure, shop-level odds progression, persistence, caps and tests.
- **BD-041 | Egg genetics:** weighted two-slot colour/blend, Normal/Big 1.2x visual size and independent shiny effect; persist/replicate through hatch and collection.

## Remaining Release Decisions

1. Run-end crystal formula, whether end-of-run crystals are direct, unboxed, or both; crystal box odds.
2. Failed-egg consolation; Cracked **20% success** is confirmed.
3. Interaction balancing for 1.8x Astra; condition-adjusted stats are confirmed as **movement speed and growth intake**.
4. Full level XP curve, ten trail prices/speed values (table above is a suggested starting point) and shop-upgrade gates.
5. Palette weights, blend distribution, shiny rate, Normal/Big odds, whether colours are visible before hatch.
6. Rules for random egg purchases using Robux-purchasable crystals: odds display, player eligibility and policy-safe alternatives.

Most original choices now have configurable provisional values in ProgressionConfig;
they still need balance approval. Failed Cracked eggs currently grant no dinosaur
or crystal refund, as disclosed before purchase. No Robux products were invented.
Published persistent profiles were not modified. See the newer acceptance record
for the exact evidence and remaining device/persistence/compliance gates.
New visual palette/pattern/coverage decisions are documented separately in the
outcome contract and still require versioned implementation; they are not implied
by the older seven-color uniform-tint runtime.
