# 2026-10-08 owner review: economy, shops, HUD, assets, weather and movement

**Status: OWNER REQUEST / TODO SPEC, not implemented or accepted.** [Canonical task index and acceptance](07-kanban.md), BD-045–BD-056. This file adds **implementation detail and subtask acceptance**, not a separate Kanban. New requests supersede earlier conflicting design preferences but DO NOT retroactively change Build 020 behavior or earlier test evidence. Reuse modular original assets and avoid changes to real persistent user profiles, monetized rollout, or multiplayer state without explicit acceptance.

## Audit of existing systems and source documents

- [Existing Build 020 integration](44-main-integration-checklist.md): ten level-gated trails with runtime ribbons, six potion items, five stat-bearing egg conditions, crystal shop tabs, weather, viewport previews and mobile HUD are coded; these are **not** proof that the newly requested UI/art/gameplay exists.
- [ProgressionConfig.luau](../src/shared/ProgressionConfig.luau): baseline condition weights, 6 upgrades, trail names/prices/speed/rarities, six potions, seven nonclear weather events, 600-second interval / 180-second event duration.
- [Egg outcomes contract](41-egg-outcomes-contract.md): tier-0 condition 20/25/45/9/1 and tier-6 2/12/51/25/10 are **historical/current**. Cracked succeeds 20%, other conditions 100%; successful Cracked/Dirty grant .8x speed & growth, Rainbow 1.2x, Astra 1.8x; a failed Cracked egg yields no dinosaur. Existing outcomes must not reroll on reload.
- [Shops/genetics acceptance](39-crystal-shops-and-genetics-acceptance.md): potion products (three speed, three growth), purchases/inventory and conditions were private-test verified; rotating offers are **new**, not done.
- [Artwork guide](32-artwork-guide-and-todo.md) / [shared egg appearance](39-egg-appearance-shared-vision.md): illustration, transparent/layered art, egg patterns including spots, tint genes, reusable Blender masters. Existing `resources/ui/v2/icons/egg.png` is the historical egg icon; **no confirmed uploaded green-spotted shop egg-icon binding yet**. Verify the owner's intended new egg master/spot treatment and its runtime export rather than replacing unrelated icons blindly.
- [Weather/event doc](35-event-mutations-and-visual-upgrade.md): server weather logic, timer, mutation eligibility and first-pass effects already exist. Environment-wide visual treatment is not validated as complete. [Main handoff](34-studio-handoff.md) notes the four illustrated Clear/Rain/Thunder/Blizzard weather icons are uploaded/verified; others remain TODO.
- [Redesign](25-redesign.md), [Build 016 UI/model spec](28-ui-overhaul.md), [terrain/island](27-mountain-island.md), [creature runtime](43-creature-runtime-integration.md): original compact meadow grew into a large mountainous island, native world props/food, independent visual/collision geometry, current walk/jump/leap and viewport constraints. Procedural/embedded geometry is not equivalent to an approved optimized Blender prop set.
- [Reward vision](09-reward-economy.md) / [BD-044](07-kanban.md): catches are supposed to be **earned hatchable run eggs**. Make HUD labels match target; do not claim that the current direct-copy reward path is fixed.

## A. Egg conditions and game economy — BD-045

**Approved requested base (upgrade level 0) probabilities**, each newly earned/purchased egg independently receives exactly one condition:

| Condition | New starting probability | Existing condition effect, unchanged unless explicitly redesigned |
| --- | ---: | --- |
| Cracked | **50%** | 20% hatch success, 80% failure; .8x speed/growth if hatched |
| Dirty | **30%** | 100% hatch success; .8x speed/growth |
| Normal | **15%** | 100% hatch success; 1.0x speed/growth |
| Rainbow | **4.5%** | 100% hatch success; 1.2x speed/growth |
| Astra | **0.5%** | 100% hatch success; 1.8x speed/growth |
| **Total** | **100%** | |

**Critical balancing implication**: at unupgraded condition level 0, 50% Cracked × 80% failure = **40% failed hatches**, before other mechanics. For 15 eggs the **expected** failures are six; this is a statistical mean, not a guaranteed result. This potentially makes early runs much less rewarding. Owner-requested percentages take precedence, but explicitly flag the cost of this design in playtesting before public release. Do not confuse a 50% probability of Cracked with a 50% cracked-egg hatch chance: cracked **hatch success stays 20%**.

Subtasks:
1. Replace tier-0 condition weighting in the authoritative config/server; handle half-percent with integer weights (e.g., 5000/3000/1500/450/50 out of 10,000), avoid rounding.
2. Recalculate six upgrade tiers so each distribution totals exactly 100%, Cracked/Dirty diminish and Rainbow/Astra increase with upgrades; **intermediate odds, final-tier odds, prices and level gates are NOT newly approved**. Retain old tier table as historical until chosen, and show current/next tier comparisons in the Condition Shop.
3. Apply only to **new** eggs after versioned change; preserve assigned outcomes, historical egg metadata, purchased-egg odds view, immutable Cracked failure, saved genetics and paid-random eligibility gates.
4. Update disclosure/enumerator/UI tests to match actual currently deployed config, with precision for 0.5%, upgrade tiers, 100% normalization and failed-outcome aggregation.
5. Run 10k+ server-seeded draws, reconnect/purchase/retry tests, and test natural 15-egg/150-egg run pacing and failed-hatch UX without secretly improving failure odds.

## B. Unified Crystal Shop and navigation — BD-046, BD-047

**BD-046 navigation:**
- Change the **navigation entry** currently labeled **AURAS** to **SHOP** and use the **already owned/uploaded crystal/amber icon** instead of the aura composition. Preserve **AURAS** as an internal shop tab, with TRAILS, EGGS, CONDITIONS and CRYSTALS. Do not rename the aura product category.
- Tapping/clicking the top-right crystal **balance counter**, including its image where suitable, opens the same Crystal Shop landing page. Avoid two independently implemented shop surfaces. Insufficient-currency calls may deep-link into the shop while honoring paid-item restrictions.
- Preserve navigation popup history, keyboard/gamepad selection, hide/close behavior and responsive layouts.

**BD-047 shop presentation and art:**
1. **Main Crystal Shop landing**: replace the current horizontally packed row of shop category choices with **separate responsive illustrated tiles** (Auras, Trails, Eggs, Conditions, Crystals) with image, title and short live subtitle/status. Tiles navigate into categories; **retain category tabs** after entry for fast switching.
2. Internal tabs use **small leading icon + readable text**; identify reusables vs missing before generating: AURAS = already assembled Meadow aura art; TRAILS = requires custom trail-art ID; EGGS = newly approved *green-spotted* egg illustration (not an unreviewed generic egg); CONDITIONS = icon based on modular condition-shell/rainbow art (new if current egg master unreadable); CRYSTALS = existing amber/currency icon. Consider a separate SHOP header icon only if reuse does not read clearly. Avoid duplicating one asset for every rarity.
3. For the shop **EGGS product** tile/card, use the new **green-spotted egg icon**. Confirm whether a matching approved green-spotted Blender shell/transparent UI render already exists; if not, add a source/export/upload/binding subtask; do not misidentify the existing generic egg.png as the new asset. Keep *icon*, *model*, and *egg pattern/genetic outcome* distinct: this is a shop presentation choice, not a guarantee of green genes/species.
4. Rework **aura product previews**: the animated ring and fossil center should occupy the usable preview frame, aligned/centered in X and Y with aspect-preserving bounds, predictable padding, size across desktop/phone/tablet. Prefer changes to shared `Artwork.build`, `ArtworkLayout`, preview camera, viewport bounds and reusable shop card component; retain foreground/background clipped aura layers, effects and native fallback. Check actual viewport clipping before hardcoding enlargement.
5. Tiles/cards keep native live buttons, prices/level locks, rarity, Buy/Owned/Equip, currency balance and confirmation. Never bake UI words/prices into images. Keep paid egg and Robux release gates disabled.
6. Follow art pipeline: separate high-res RGBA per asset, source under `resources/ui/v2/`, versioned manifests/prompts, upload under verified owner, bind in shared `NavigationArtwork` / `UIIconAssets` / shop components, inspect on desktop + landscape phone/tablet; don't fabricate Roblox IDs.

## C. Trail assets and rarity system — BD-048

**Preserve the existing catalog of TEN trails**, with free **Normal White** and top **Astra**. The owner's request for “six total rarities” is interpreted as **six visual/shop rarity classes for these ten trails**, not cutting the catalog from ten items down to six. This interpretation requires explicit owner review before production balance is locked.

1. Inventory existing `TrailArtwork`, `ProgressionConfig.Trails`, rendered ribbon geometry, ownership migration, screenshot evidence and missing final art. Existing ten trails use just **Common / Rare / Legendary** labels; six-category target needs **three extra tier classifications** (provisional taxonomy: Common, Uncommon, Rare, Epic, Legendary, Mythic; final names/order per owner).
2. Produce a per-trail **illustrated UI icon** and larger card render at consistent 3/4 camera, contour and lighting, using reusable source pieces / gradients/colors rather than ten unrelated assets. Build a six-rarity reusable frame/badge suite; show trail identity and rarity distinctly from speed multiplier and persistent account level.
3. Author and export **real Blender trail VFX masters** for walking/running dinosaurs: soft textured ribbon, particles/embers/frost/electricity/glitter by identity and shared animation/texture presets, not only static icon pictures. Match live speed and dinosaur scale, attach to moving rig without float/streak discontinuity, and use GPU/particle budgets; provide fallback native trail visuals.
4. Ensure each of ten trails maps to exactly one of six rarity tiers after approval, preserve level/price/speed gates and old owned/equipped IDs; never grant new speed automatically because rarity name changes.
5. Evidence: original .blend/source + exported transparent PNG/UI, texture/sprite/trail assets, binding manifest, in-game 3D previews and world effects; compare at 48/64/128px, 22 dinos, 8–12 player simulated load, BIG+max growth, phone FPS/thermal and reduced-effects setting.

## D. Potion Shop rotation — BD-051

Current Build 020 exposes **all six** potion products (3 speed + 3 growth) and persists bought consumables. **New target** is a rotating **limited-stock store**:
- Server-authoritative featured offers change **every 300 seconds (five minutes)**. Only a **random subset** of configured potions appears per refresh, not all six. Keep odds and number of slots configurable (e.g. *three distinct items is a design starting point, not approved quantity*).
- Higher rarity types have lower draw probability. Use existing potion rarities initially, extend after separate approval; selection must not guarantee rare products.
- Each shown potion has **per-player available stock randomly rolled from 1–3 units**, with **1 more likely than 2, and 2 more likely than 3**. Weights are TBD, not assumed live. Purchases decrement exact stock atomically on the server and maintain existing crystal debit/consumable inventory rules. Avoid a global shared stock consumed by one player unless expressly approved.
- Refresh stock and offers at synchronized five-minute boundaries; derive remaining time from **server time**. Prevent reopening/rejoining/remote spam from rerolling choices, bypassing quantity limits or getting free potions. Explicitly decide global cross-server versus per-server offer consistency during implementation; at minimum all players on the same server see the same offers and each player's own remaining stock.
- Show a visible **next refresh MM:SS timer**, “X left” stock on each offer, Sold Out state, and non-spamming **“Potion Shop refreshed”** toast upon real rotation. Toast must not interrupt combat, modal confirmations, or reduced-motion settings. Reconcile purchase at the refresh boundary (purchase against the active stock/version only).
- Active potion buffs/inventory remain intact through rotations; ownership/use expiry already exists, so rotation must change **store availability**, not arbitrarily remove owned items. Test concurrent requests, reconnect, mobile UI, time drift and insufficient crystals.

## E. Map props and traversal — BD-049, BD-050, BD-053

**BD-049 varied reusable map set:**
- Blender collection of **multiple tree families** (e.g. conifer, wide-canopy, palm/cycad, dead tree), small/medium/large variants, bushes, ferns, grasses, flowers, vines, mushroom/prehistoric plants, mossy/bare boulders and rock formations; create **landmarks** (ancient dinosaur statue, fossil display, nest grove, stone arch, ruins/altar, lake overlook) with distinct silhouettes.
- Build a biome/placement grammar (slope, height, wetness, distance to paths and sanctuary, density), deterministic seeds and art variants. Break up repeated props without random clutter, preserve navigation sightlines and readable dinosaur scale.
- All editable Blender masters with consistent pivot, logical ID, bounding box, collider proxy/LOD decisions, material palette and exported MeshParts/optimized geometry. Reuse shared mesh/texture/material assets; avoid hundreds of unoptimized WedgeParts or requiring unapproved EditableMesh live permissions.
- Food pickups and ambient foliage generally noncolliding; trees/large rocks use simplified aligned colliders; reserve enough space for BIG/max-size and prevent foot clipping.
- Deploy progressive densities and test 8–12 players, physical phone and landscape tablet, with stable frame times and foliage visibility. Existing original procedural props remain fallbacks until imports are verified.

**BD-050 richer food kit:**
- Create new **Blender food pickup models** for berry, fruit, food egg, amber/high-value food plus additional visually distinct variants/tiers as approved. Keep existing authoritative values **+1/+4/+15/+50** until rebalanced; don't conflate amber **food score** with wallet **crystals**.
- Consistent readability at small world size, clear higher-value silhouettes, pickup bob/glint with reduced effects. Use common placement/pickup configuration and existing server validation/sector respawn; variants should not silently change score or grant crystal currency twice.
- Test pickup visibility among foliage, raycast/surface offsets on slopes, no clipping, two-player contention and camera view at ordinary/BIG scale. Preserve origin/source files and attribution/binding manifests.

**BD-053 terrain movement bug:**
- Reproduce reported **dino sliding and failure to climb hills** on current mountainous terrain; measure angle/friction/contact geometry vs `Config.MaxSlopeAngle = 46`, Humanoid/rig locomotion mode, controller velocity constraints, root-part collider, ground snap, animation/visual pivot and jump/leap.
- Record representative slope coordinates, input and observed displacement, separate visual sliding/animation drift from actual physical slide. Diagnose rather than simply increasing speed/angle globally.
- Rework walkable paths/slope grading and/or server-authoritative traction/ground logic to allow intended climbs without climbing near-vertical walls, flying, infinite jump or bypassing anti-speed/teleport validations. Avoid performance-costly per-frame corrective raycasts on every dino unless measured.
- Test downhill idle stability, uphill movement, sideways traversal, jumps/leap, terrain material/friction, obstacles, all species, size/condition/trail/speed potion boosts, server/client disagreement and multiplayer. Keep fair PvP escape routes and BIG colliders.

## F. Home/return, touch UI and HUD — BD-052, BD-054, BD-056

**BD-052 return:**
- Replace duplicated Menu Home and bottom-right Home with **one clear Home icon near middle-bottom** (within a mobile-safe reachable area, not on top of joystick or Roblox core UI). Position responds to touch vs keyboard/controller.
- Tapping prompts **“Return to Sanctuary? Your current run will end and rewards will be banked.”** with **Return / Cancel** and reward implications. **Remove the historical 3-second hold/channel** on confirmation for voluntary exit. The confirmation is not a shield from PvP: define server ordering so death and confirmation cannot duplicate rewards or let players escape unfairly. Existing server cooldown/idempotency remains.
- If called already in Sanctuary, Home should not end another run or grant another reward. Ensure real Cancel closes modal without action, Escape/back are coherent, and jump/leap controls do not click through.

**BD-054 mobile/tablet control audit:**
- Study [Roblox official UI thumb zones / reserved zones](https://create.roblox.com/docs/ui/position-and-size) and [mobile input](https://create.roblox.com/docs/input/mobile), plus existing [Be Dino reference images](../resources/references/steal-an-egg/README.md), [Pet Simulator 99 / RIVALS rationale](25-redesign.md), to design ***original*** touch placements. Reference patterns, never extract another game's assets.
- **Do not pin all actions to the physical screen bottom**. Reserve the bottom-left for joystick and bottom-right for jump/core actions, place secondary action rail on easy-to-reach right-middle / upper-right and center-bottom Home only if unobstructed. Tablet has wider thumb travel than phone; avoid using one hardcoded 16:9 layout for everything.
- Use `ScreenGui.ScreenInsets` and `GuiService.TopbarInset` to respect devices, notches/Roblox controls; `UserInputService.PreferredInput` or Input Action System for touch/keyboard/gamepad. Design scale-aware UDim2 anchors; minimum **44–48 effective-pixel target** is a provisional QA goal, verify physical touch usability rather than mistaking emulator pixels for DPI.
- Test representative landscape small phone, large phone/tablet, desktop, controller, safe-area orientation, modal open, keyboard opened, bottom navigation OS bar, top-right wallet, shop tiles, leap button, hatching and Home. Include screenshot overlays/hit boxes and non-overlap evidence.
- Official precedent: [Roblox safe area reference](https://create.roblox.com/docs/reference/engine/classes/ScreenGui) explains clipping and ScreenInsets. [GuiService](https://create.roblox.com/docs/reference/engine/classes/GuiService) exposes safe/topbar insets. Reviews of Fisch/other Roblox layouts illustrate keeping always-used actions near reach, but native in-game controls and screen states vary; they are not prescriptive exact pixels.

**BD-056 gameplay HUD redesign:**
- **Top center:** the only necessary live growth/survival numeric readout, large/legible, no competing catch text. Label plainly **GROWTH** or **SIZE** and display live validated gameplay value. Check threats and timer/HUD overlap, notch and other core UI.
- **Bottom left (above/away from joystick):** **egg icon + Eggs caught: N** as a minimal single metric; use approved reusable spotted/generic egg art as appropriate and make number prominent. Target caught egg count equals run egg reward count under **BD-044**, not old bonus 1/2/3 egg thresholds; avoid misleading UI until economy migration.
- Remove redundant growth number from bottom left; balance icon size, hierarchy and animation vs performance; preserve optional weather, leap and currency HUD elsewhere. Test zero, 15, 150, >999 values, rapid pickups, event bonuses and returning to sanctuary.

## G. Full atmospheric weather — BD-055

Server already chooses events and computes perks/mutation eligibility. **Do not recreate event RNG or alter reward calculations while implementing visuals.** Add an event **environment-preset system** with a Clear baseline and explicit restore/tween, keyed by the existing weather IDs: rain, thunder, blizzard, volcano, aurora, quake, bloodmoon. Implement *world-visible weather*, not just HUD icons.

**Roblox primitives to use (and evaluate in Studio):**
- `Lighting`: `ClockTime`, `Brightness`, `ExposureCompensation`, `Ambient`, `OutdoorAmbient`; separate `ColorCorrectionEffect` tint/saturation/contrast and optional `BloomEffect`/sunrays. [Official lighting](https://create.roblox.com/docs/environment/lighting), [post effects](https://create.roblox.com/docs/environment/post-processing-effects).
- `Lighting.Atmosphere`: `Density`, `Color`, `Decay`, `Haze`, `Glare`, `Offset` for sky horizon and storm haze. [Official atmosphere](https://create.roblox.com/docs/environment/atmosphere).
- `Terrain.Clouds`: `Cover`, `Density`, `Color`, and optionally `Workspace.GlobalWind` (wind influences grass/clouds); `Sky` only for explicitly authored skybox variants when cloud/Atmosphere settings aren't enough. [Environment](https://create.roblox.com/docs/environment), [global wind](https://create.roblox.com/docs/environment/global-wind). Keep clear-sky return and shared baseline.
- `ParticleEmitter` on local camera/region-following lightweight emission systems for falling rain/snow/ash (not blanket emitters across an entire island). Integrate audio loops/lightning flashes/ground splash or lightning strike where relevant, with bounded spawn budgets and reduced-effects behavior. [Official emitter](https://create.roblox.com/docs/reference/engine/classes/ParticleEmitter).
- Use time-limited **tweens** for lighting/cloud/postfx transitions while synchronizing start/end from the authoritative weather event; prevent competing tween instances, late join ghost effects, stale emitters and permanently tinted Clear.

**Per-weather concept/implementation subtests:**
| State | Sky/lighting | Local particles/world detail |
| --- | --- | --- |
| Clear | Bright warm daylight, lighter sparse clouds, neutral tint | Baseline ambience and cleanup |
| Rain | Cooler gray-blue overcast, denser dark clouds, dimmer indirect light/haze | Raindrops/splashes/puddles (cosmetic), rain audio |
| Thunderstorm | Dark storm sky, higher contrast, brief synchronized lightning/exposure flashes | Stronger rain, lightning bolts/thunder delay; avoid intense photosensitive flashes |
| Blizzard | Pale desaturated cold sky, near-white haze, softer/darker distant contrast | Wind-driven snowfall, snow fog, windy ambience and visibility bounds |
| Volcano | Warm burnt-orange sky with smoke-haze and darkened sun | Black ash fallout, sparse orange embers, volcanic plume and distant glow, no damaging lava unless separately approved |
| Northern Lights | Night/dusk deep blue sky, vivid teal/purple luminous bands | Layered animated aurora curtain with controlled bloom, optional stars |
| Earthquake | Dusty muted sky / temporary haze, not necessarily night | Ground dust, subtle camera shake scaled by accessibility, no actual deformation unless separately approved |
| Blood Moon | Dark red-purple dusk/night, visible red moon sky/mesh | Rare fog particles and restrained red atmospheric treatment |

**Acceptance:** switch into all 8 states and back to Clear without tint/audio/particle leaks. Late join, rapid event change, respawn, sanctuary, different graphics quality, 8–12 players, mobile FPS/memory, camera indoors/underground and color readability all covered. Do not apply atmospheric tint to UI/egg previews in a way that misrepresents stored genes or purchased-item artwork. Confirm event-time loot tags still come from the authoritative server event, not client-local appearance.

## Dependencies, priorities and signoff

| Task | Priority | Dependencies | Completion is NOT |
| --- | --- | --- | --- |
| BD-045 condition odds | P0 | BD-040 | Editing weights without shop disclosure/testing |
| BD-046 shop entry/wallet | P1 | BD-029, BD-036, BD-043 | Renaming one string without route parity |
| BD-047 shop UI/art | P1 | BD-046 | Mockup without new egg icon/upload/real component test |
| BD-048 trail rarities/art/VFX | P1 | BD-038, BD-034 | Recoloring current two native ribbons |
| BD-049 world props | P1 | BD-016 | One repeated generic tree everywhere |
| BD-050 food assets | P1 | BD-008 | New render with changed server pickup values |
| BD-051 rotating potion stock | P1 | BD-032, BD-039 | Client-side timer or rerollable inventory |
| BD-052 Home return | P1 | BD-009 | Instant client teleport or unprotected duplicate rewards |
| BD-053 terrain movement | **P0** | BD-006, BD-008 | Arbitrarily raising max slope angle without validation |
| BD-054 touch layout | **P0** | BD-052, BD-046 | Desktop screenshots only |
| BD-055 atmospheric weather | P1 | BD-031, BD-034 | Weather HUD icon/timer only |
| BD-056 HUD labels | P1 | BD-044, BD-054 | Calling legacy catches `eggs` before counting is true |

**Dependencies are hard blockers only.** BD-045 odds/config can be implemented on the current egg pipeline and later tested alongside BD-044's new run rewards; BD-052 can use the current settlement idempotency without waiting for BD-044; BD-047 UI mockups can begin before BD-035's final Blender layers. BD-049/050 Blender asset creation can progress independently of the terrain bug, but final placement/navigation acceptance must retest BD-053. **Suggested work order:** fix slipping/climbing and reward correctness; then layout/navigation/HUD, rotating shop and condition disclosure; parallelize original Blender prop/food/trail artwork and environment-preset authoring. Keep only one implementation task in-progress per the canonical board; unrelated asset production may prepare drafts concurrently. Mark as Done only with commit/build + physical/mobile and Studio evidence per existing gates.
