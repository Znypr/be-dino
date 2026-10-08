# Pattern-specific fusion, durable dinosaur identity and per-dino cosmetics

**Owner decisions: 2026-10-08. Status: TARGET / PLANNED, NOT IN BUILD 020.** This specification covers **BD-057–BD-062**. [Task status](07-kanban.md) is canonical; current implementation is [Build 020](44-main-integration-checklist.md). Read [egg provenance and outcome contract](41-egg-outcomes-contract.md), [22-creature appearance](43-creature-runtime-integration.md), [shop/genetics spec](36-crystal-shops-egg-genetics-and-progression.md), [original layered egg art direction](39-egg-appearance-shared-vision.md) and [BD-044 egg-per-catch migration](09-reward-economy.md).

## Vision and settled owner rules

Every dinosaur is a **persisted collectible individual or identifiable batch of interchangeable individuals**, with a natural egg-derived genome, player-earned fusion stage, persistent paid-for-that-dino appearance collection and one currently equipped visual loadout. Progress means **grinding toward a targeted, recognizable upgraded dinosaur**, not waiting forever for a single lucky hatch. Each added layer increases aesthetic sophistication without obscuring the originating species, colors, stripe/spot pattern or egg. Multiple combinations create a large reusable appearance space, **not** a promise of literally infinite unique high-resolution Blender meshes.

Owner decisions:
- **Fusion order** begins **Base → Gold → Emerald → Diamond**. More stages may be added only after playable balance/art review. The old **Base 50→Gold, Gold 50→Diamond** is historical current Build 020 behavior to be migrated, **not** the new target.
- First playable **Gold recipe costs 10 qualifying dinosaurs**, not 50, and **matches species + saved egg pattern**. Example: **ten Compies with Wavy Stripes → one Gold Wavy-Stripes Compy**. This is the owner-requested prototype threshold, **not** permission to require identical colors, conditions or Shiny to craft Gold.
- Fusion stages are the **main deterministic, earned source of permanent stat upgrades**. Lucky conditions/event traits remain special; buying cosmetics is not the primary way to become strong.
- Gold/Emerald/Diamond material/Blender effects must be **additive**, preserving individual color mix, markings, face, species identity and condition, and supporting Shiny + event mutation + equipped aura + equipped trail simultaneously. **Compare subtle and medium fusion-surface overlays** at gameplay and collection distances; do not force an approved intensity before testing.
- Auras and trails can be purchased **repeatedly for different dinosaurs**. Every purchased product is **bound to its recipient dinosaur**; there is **no free transfer** to another dinosaur. A particular dinosaur may own **multiple aura and trail options** and can **equip/switch/downgrade freely among its own purchased options** for appearance.
- The dino selection/detail UI must show **species, pattern, two colors and coverage, condition, mutation, BIG/Shiny, fusion stage, owned/equipped aura and trail, individual rarity labels, egg-of-origin preview, natural hatch odds and total earned rarity/prestige**. Bought cosmetics must **never influence natural/total rarity**.
- **Rarity truth**: fusion stage is deterministic earned progress, not an independent drop event. Count fusion stage in the overall **earned rarity/prestige descriptor**, but do not multiply a fictitious “Gold hatch %” into probability of natural egg traits. Separate actual **natural hatch odds** from **achievement/fusion prestige**.

## 1. Tier ladder and recipe decisions — BD-057

**Confirmed order and first recipe:** Base → Gold → Emerald → Diamond; Gold uses 10 same-species, same-pattern dinosaurs in the first prototype.

**Suggested future extension for exploration**, not approved tiers or shipping promise:

| Order | Stage | Visual identity | Function |
| --- | --- | --- | --- |
| 0 | Base | Natural egg genetics and species pattern | Hatch baseline |
| 1 | **Gold** | Warm metallic highlights, selective glossy trim following scales/pattern contours | First recognizable targeted grind |
| 2 | **Emerald** | Deep green gemstone edges, restrained crystalline facets, bright specular accents | Midgame identity; comes before Diamond |
| 3 | **Diamond** | Cool opalescent glass/crystal facets, high-frequency highlights, patterned refractions | Major late-game milestone |
| 4 | *Obsidian* | Dark glass with selective iridescent fracture seams and gold/teal edges | Optional later extension; avoid turning underlying colors black |
| 5 | *Celestial* | Polished antique iridescent mineral, tiny luminous etched relief and restrained star contours | Optional endgame extension; keep separate from **Astra condition** and **Astra trail** |

**Pattern-specific branches:** preserve one of the eight current `EggGenetics.Patterns` IDs, including Blank. E.g. “Gold Wavy-Stripes Compy”, “Emerald Wavy-Stripes Compy”, “Gold Freckles Raptor”. The saved title/display order can use short patterns (“Gold Striped Compy”) but persistent recipes use canonical IDs, **not substring names or tint guesses**. Colors can vary among recipe ingredients. Do **not** accidentally make a 20% blue / 80% green requirement unless later balancing explicitly creates advanced optional color-masteries.

**Fusion target/ingredient rules, to prototype/test:**
1. A player selects an **owned target dinosaur** with a stable instance ID and a particular species/pattern. The target becomes the new stage; **its own** colors (both genes + 1–99 share), original egg, condition, mutation, BIG/Shiny and bound cosmetics remain. It is not rerolled.
2. For **Base → Gold**, count **10 matching Base dinosaurs including the chosen target**; consume **9 additional** *unequipped/unlocked* matching donors, and evolve the chosen target in place. This is a **proposed exact consumption mechanic** interpreting “10 copies”; review before coding if users expect ten donors *in addition to* their hero.
3. Give exact donor selection, disambiguate genetically distinct copies with the same species/pattern, and show consumed preview/quantity. **Never silently spend** a Shiny, rare-color, mutated, BIG, already fused, favorited, locked, purchased-cosmetic-owning or currently active other dinosaur. Protected donors may only be included after a separate deliberate confirmation, or prohibit outright by default. Prefer ordinary spare donors.
4. For **Gold → Emerald → Diamond**, retain **pattern matching as the branch identity**, but **higher-tier costs must be balanced from real earned eggs/hour and conversion rates**. Do NOT hardcode 10 prior-stage donors per step without simulation. At 10-per-tier, Diamond requires approximately **1,000 matching Base dinosaurs** (10 Base/Gold × 10 Gold/Emerald × 10 Emerald/Diamond) before accounting for hatch failure and other constraints. This is potentially an excessive grind in a 22-species, eight-pattern pool. **Candidate prototype to test**: 10 Base → Gold; **3 Gold → Emerald; 2 Emerald → Diamond**, with optional *earned-only* milestone/quest materials instead of extreme exponential copies. The 3/2 counts and quest inputs are **recommendations pending owner approval**, not locked gameplay.
5. Subsequent stages, any “prestige reset,” duplicate refunds, higher-stage stat modifiers and material/shard requirements require separate owner approval and economy simulation. **No random chance of fusion failure**. Late-game rewards should require time/mastery, never delete fully earned trophies due to an unadvertised gamble.
6. Each stage upgrades **the SAME hero instance**. UI shows previous and next material preview, pattern-specific name, gained stats, costs/missing donors, protection warnings and exact remaining balances. Receipts are not Roblox currency purchases; all server inventory mutations stay atomic/idempotent and persisted.

**Weeks-long retention without punishing grind:** Combine deterministic recipes, visible donor progress 0/10, repeatable species/pattern mastery, earned seasonal/event objectives and eventual endgame optional cosmetics. Not every rare gene/condition should be mandatory fusion fodder. Use measured **successful eggs/hour, target species+pattern/hour, acquisition after Cracked failures, runs/day, weeks to each stage, PvP fairness and speed cap** to tune costs. Provide goals at short session, few-day and multi-week horizons. No daily login mandate or speculative odds/power promises. Demonstrate casual and heavy play paths using 15-/150-egg sample runs (not guaranteed per five minutes). Keep playability without Robux and high-priced crystals.

## 2. Stats and meaningful deterministic progress — BD-058

- A fusion stage supplies a **server-authoritative permanent movement speed, food-growth efficiency and/or non-PvP ability modifier**, with a clear before/after comparison; start from conservative **illustrative** bonuses (not owner-locked), apply existing condition penalties, weather/mutation/potion interactions and hard caps in `ProgressionConfig`. Current safety starting caps are **2.2x speed / 8x growth**.
- **Equipped cosmetic appearance must not force a player to use a visually disliked aura/trail for maximum stats.** Existing Build 020 auras grant growth bonuses and trails grant speed. As the owner shifts primary power to fusion, evaluate either **purely visual appearance selection** with fusion as the main stat source or **unlock-based perks independent of the selected visual skin**. Don't silently delete already paid-for benefits or abruptly nerf saved accounts; define an additive migration/compensation policy first.
- Stat mods are based on **current dinosaur instance's fused stage** and preserved hatch traits, not a universal account-wide multiplier. Independently track persistent account level requirements from trail-shop catalog so it does not accidentally transfer cosmetics. Keep PvP and run matching fair and measurable at all stages; avoid paid purchase becoming a direct shortcut to the main fusion booster.
- Include a predictable stat formula/stacking order (base species, condition, earned stage, event mutation, potion/weather and any explicitly approved unlocked passive; final clamp) and bound movement validation so a mutated BIG high-stage dinosaur cannot outrun anti-cheat or clip impossible slopes. BIG remains size-only.

## 3. Per-dino aura/trail inventory and purchase rules — BD-059

- **Recipient is a stable dinosaur instance**, not just `speciesId`, `patternId`, account-wide `ownedAuras` or the global equipped species. Two distinct Compies must be allowed to own different purchases, even if genetically identical. Each instance stores **ownedAuraIds set**, **ownedTrailIds set**, `equippedAuraId?` and `equippedTrailId?`; no transfer between dino instances and no account-wide unlock by default.
- Buying **Fern Drift for Compy A** does **not** grant Fern to Compy B. The owner can later also buy Tidal Wake for Compy A, and freely switch A between Fern and Tidal or None/Normal White without paying again. B can buy Fern separately at the usual price. Same item re-purchase on the *same* dino should be idempotently rejected or labelled Owned, not charge twice.
- Shop clearly shows the currently targeted/equipped dinosaur's **picture/name/instance identity**, with “Buy for this Dino” and recipient pinned in server purchase request + confirmation. If the player switches dino while the shop is open, require refresh/re-confirm. Server rejects stale recipient IDs, non-owned recipient and inventory/price/level-gate bypass.
- On evolving/fusing target, its purchased cosmetics follow **the same stable instance ID**. Donor dinosaurs carrying paid/bound cosmetics are protected from automatic consumption; deliberate sacrifice policy is an unresolved owner decision. On trading/deleting dinos in a later feature, keep bound items with their owner or block deleting until confirmation, never silently refund/transfer.
- Preserve existing global-account catalog ownership and equip values through a **documented migration**: old unlocks can be kept in a nontransferable legacy grant or assigned to the currently equipped hero with explicit owner-visible disclosure; neither retroactively confiscate purchases nor grant unlimited items to all dinos by accident. Save schema version, idempotent ownership transactions, session lock/retry, remote bounds and reconnect. Default-free trail semantics remain free if approved.
- In detail/pick menu, display **currently equipped** aura/trail, all **owned alternatives** and their rarity, plus None and intentional visual downgrades. Shop and collection use the same per-dino inventory source and do not fake shared account ownership.

## 4. Stable copy identity, original egg and lifecycle — BD-060

**This is a prerequisite for BD-057/059/061.** Existing Build 020 stores grouped count/variant progression and equipped species; the earliest profile contract stored `collection[speciesId].base/gold` and catalog equipment. Direct per-instance cosmetic allocation and origin history must not be bolted onto one species count without an additive migration.

Suggested durable model (schema illustration, not final serializer):

```text
DinoInstance {
  instanceId: server UUID / bounded unique id; ownerId; speciesId;
  currentFusionStage; fusionBranchPatternId; favorited/locked;
  origin { eggId, eggSource, earnedRunId?, acquiredAt?,
           originalEggVisualSnapshot: {patternId, color1, color2, share,
               conditionId, eventId?, sizeTrait, shiny}, chanceTableVersion };
  bornGenes { conditionId, hatchSuccess, color1, color2, share, patternId,
              big, shiny, eventMutationId? };
  ownedAuraIds: validated deduplicated set; ownedTrailIds: set;
  equippedAuraId?; equippedTrailId?;
  currentStats; displayVersion; ...
}
```

- **Origin egg is immutable**: retain a compact versioned egg recipe/snapshot sufficient to reconstruct original model/render in dino detail. If the egg metadata already exists in pending queues, carry it into the granted dinosaur **when it hatches**. Do not reconstruct from current stage, swap colors, or fake old acquisition dates. If a single successful egg gives 2–3 copies, create **distinct instanceIds** but link them to the **same origin eggId and immutable origin traits**; preserve quantity, no double-credit.
- Legacy grouped stacks need an **efficient hybrid batch+unique-instance strategy** to avoid expensive full per-egg data for 150+ egg run batches and 22 species. Keep lazy materialization/stack splitting when a dino is equipped, fused, protected or customized; preserve copy counts and variant keys; don't manufacture unique historical egg origins for old saves. Show **“Legacy origin unavailable”** with safe default/approximate preview for older collection copies.
- Avoid UUID collisions, cross-account aliasing, inventory bloat/DataStore budget violations, variant merging across genotypes, double claims, stale writer races or accidental cosmetic grants. Compression/splitting and transaction versioning must be testable and reversible without changing actual published profiles during development.

## 5. Modular premium appearance, Blender deliverables — BD-057 + BD-061

**Art pipeline:** authored **Blender source models, surface masks, normal/roughness/metalness texture treatments and optional small accessory meshes**, not brute-force duplicating all 22 species × 8 patterns × 9 color families × stages × mutations. Same rig/silhouette/camera rules across tiers. Roblox implementation may require baked composite texture layers, authored SurfaceAppearance templates and/or small rig-attached accents; confirm what the actual editable runtime renderer supports rather than assuming arbitrary alpha-stacked PBR layers. Prevent duplicate overlay mesh z-fighting and material loss from runtime gene recoloring. Do not overwrite the underlying saved gene texture.

**Two mandatory A/B art variants, each stage:**

| Surface level | Design goal | Acceptance |
| --- | --- | --- |
| **Subtle** | Recognizable metallic/mineral gloss and selective species-anatomy accents; texture and colored pattern remain dominant | The egg's stripe/spot pattern and both colors are legible at a glance |
| **Medium** | More complex polished trim, gemstone facet relief, additional highlights along pattern boundaries, horn/claw/ridge accents | Higher prestige without solid covering or washing out DNA/patterns |

**Suggested additive stack:** authored base rig/face/shape → saved two-gene color coverage → saved pattern → condition-related local visual if applicable → fusion **surface material/mask/detail** → surrounding event mutation smoke/wisps → Shiny glints → dino-bound aura orbit → dino-bound trail from motion. BIG scales the coordinated assembly without changing stats. Tier 3 must look premium even with all optional layers disabled.

**Testing matrix at minimum:** six original + selected new dino body types (quadruped/horned, feathered, large long-neck, pterosaur, aquatic); each with stripes, spots and blank; contrasting and nearly black/monochrome color genes; Gold/Emerald/Diamond with **Subtle and Medium**; normal vs BIG; Shiny on/off; event mutation ember/frost/aurora; light/dark ambient weather; with/without aura and trail; running/still, world/camera/UI previews, at default and max growth. Prioritize readability and silhouette, masking/UV consistency, render order, particle clutter, UI crop, skin-tone conservation, phone performance, reduced effects. Visually compare **Base vs Gold vs Emerald vs Diamond** using the *same identical* color/pattern/genome so fusion improvements are measurable rather than random dino differences.

Art sources/assets required: versioned .blend masters (not only PNG screenshots), material-node libraries/masks, exportable optimized meshes or reusable accent meshes, original transparent preview PNGs, manifest with logical IDs/owner-bound uploaded IDs, screenshots/short videos and measurable draw-call/triangle/particle costs. **No final overlay choice approved until owner reviews subtle vs medium stacks.** Consider a user-adjustable effect-intensity slider only after measuring if it is affordable (optional, not requested).

## 6. Dino picker, egg origin and truthful rarity — BD-062

**Information architecture:** compact species/variant cards may show fusion-stage border, egg pattern mark, natural rarity badge, BIG/Shiny, mutation badge, equipped aura and trail icons. Open a **Dino Details** panel for full traits, exact two color genes and percentage, egg model/origin, condition, acquired status, fusion recipe/progress, rarity breakdown, owned/equipped cosmetics and stats. Avoid trying to fit every label on a touch-sized grid. The small cards must expose essential distinguishing traits without 12 competing badges; tooltips and accessible text labels rather than color-only coding.

**Two separate measures:**
1. **Natural hatch rarity**, a mathematically defensible percentage/“1 in X” if and only if derived from the **correct versioned source and conditional distributions** for species, pattern, two gene colors and coverage, successful condition, BIG/Shiny, event mutation given its event/time, etc. *Do not* multiply marginal chances as though correlated conditions/events were independent. Account for failed Cracked outcomes and paid vs free egg sources, and don't compare different event contexts without labeling them. For combinations not calculable from preserved versions, show **Unknown / estimated**, not a made-up numeric probability.
2. **Total earned rarity/prestige**, which **includes** the natural traits **plus the crafted fusion stage** and other *earned, nonpurchased* progression; explicitly label a craft stage as **Earned / Crafted**, not as a random hatch %. **Exclude** purchased trails/auras, their prices, player Robux spent and current equipped cosmetic selection. If a single combined number is desired, use a **separately defined index or descriptive tier** with a published score methodology, **not** an invented joint random percentage. E.g., `Natural: 1 in X conditional on Rain egg; Crafted: Emerald Wavy-Stripes Compy; Overall prestige: [earned tier]`.

**Rarity UI example:**
- **Emerald Wavy-Stripes Compy** / BIG / Shiny / Ember; paired gene colors **Green 20% • Blue 80%**; original egg mini-preview shows Cracked/Dirty/Normal/Rainbow/Astra condition and source. Natural rarity has a versioned calculation or “Not available” if unknown. `Fusion: Emerald (earned)`.
- `Aura: Meadow (owned by this dino; other options selectable)`; `Trail: Fern Drift (owned by this dino; Tidal Wake available if separately bought)`. Their product rarity labels are **not included** in Natural or Overall prestige.
- Tap to view a **breakdown by earned source** and fusion recipe. Display a combined `0.0005%` only when a real valid probability model supports the event; no fake fusion/chance multiplication.

**UI/QA:** sorting/filter by species, pattern, stage, natural traits, origin egg and equipped effects; no merging visually distinct egg genotypes; count verification across old stacks, 1/2/3-copy hatches and new 150-egg batches; full mobile/tablet/desktop controls and 8–12 player performance. When two dinos have identical species/pattern but different origin/purchases, both must remain individually selectable. Unavailable legacy original egg must show a truthful fallback without inventing traits.

## 7. Acceptance and priority gates

| Task | Priority | Prerequisite | Acceptance evidence |
| --- | --- | --- | --- |
| **BD-057** Pattern-matched fusion + Emerald ladder | **P0** | BD-012, BD-060 | 10-copy Gold recipe; preserve target genes; stage order and donor safety; no double-debit; high-tier simulation |
| **BD-058** Fusion stats, safety and economy | **P0** | BD-057 | Deterministic boosts, visible progress/caps, no exploit across buffs, weeks-long pacing analysis |
| **BD-059** Per-dino cosmetic ownership/equipment | P1 | BD-060, BD-029, BD-038 | Repeat buy for different dinos; same-dino multiple loadouts; no free exchange; stable purchase target |
| **BD-060** Unique identity, storage and egg origin | **P0** | BD-011, BD-012, BD-041 | safe migration; preserved egg/genetic identity; variant counts; 2–3 copy and 150-egg scalability |
| **BD-061** Blender fusion surfaces and stacks | P1 | BD-057, BD-035 | subtle/medium comparisons for Gold/Emerald/Diamond; unaltered patterns, all layers coexist; FPS/device |
| **BD-062** Dino detail UI and rarity math | P1 | BD-059, BD-060, BD-057 | clear compact card/detail, origin display, earned-vs-natural breakdown, nonfabricated odds |

**Cross-cutting dependencies:** BD-044 new run eggs feeds individualized hatch origins; BD-045 condition rebalance affects true natural-odds calculation and fusion resource pacing. BD-048 ten-trail assets and BD-047 Shop art integrate with per-dino recipient and picker previews. Cosmetics must never be treated as independent RNG or counted in natural rarity. **No Build 020 scripts, profile data or existing purchases have been migrated as a result of this planning spec.**

## Next prototype experiments

- Model the **same Wavy-Stripes Compy, 20/80 green/blue, Shiny + Ember** at Base, Gold, Emerald and Diamond, **subtle vs medium**, with and without auras/trails; use screenshots of the actual Blender/Roblox output, not generated mockups asserted as engine evidence.
- Simulate a player earning 15 eggs after 500 food points and another earning 150 eggs after 5,000, using plausible species/pattern/Cracked-failure odds. Measure **eligible Wavy-Stripes Compies per run** and hours to each fusion, rather than assuming 15 catches means 15 copies of Compy.
- Test A buying Meadow + Fern + Tidal and switching between their purchased appearances, versus identical B who owns none. Fuse A to Gold and verify its cosmetics, genes and egg history remain while unpurchased B stays unchanged.
- Force one failed Cracked egg, one 3-copy successful hatch, one rare-color double-matched dino and concurrent donor fusion attempts, checking identity, idempotency, preview correctness and no paid-cosmetic loss.
