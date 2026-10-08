# Be Dino! documentation guide and source of truth

**Reviewed 2026-10-08 against GitHub main Build 020.** Use this navigation first when interpreting Be Dino's current rules or asking AI agents to work on the game. There are three separate meanings of "current": **owner-approved goal**, **committed code**, and **verified Studio/release acceptance**. They are not interchangeable. Do not promote a dated build/test record to active authority just because its own heading says "current".

## Authority order (by question)

| What are you trying to learn or change? | Canonical place | Ground truth / scope |
| --- | --- | --- |
| Overall player experience and long-term goals | [README](../README.md), [game design](03-game-design.md), [reward target](09-reward-economy.md) | Latest owner intent, **not** proof of implementation |
| AI/contributor behavior | [AGENTS.md](../AGENTS.md) | Read before planning or editing |
| Tasks, priorities, dependencies and **status** | **[07-kanban.md](07-kanban.md)** | The **single live task board**; never maintain a competing board |
| Detailed owner feedback: UI, shops, 3D assets, movement, weather | [45-owner-feedback-shop-hud-world-weather-tasks.md](45-owner-feedback-shop-hud-world-weather-tasks.md) | Acceptance details for **BD-045–056**; do not mirror status here |
| Food/catch -> egg rewards | [09-reward-economy.md](09-reward-economy.md) and **BD-044** in Kanban | **Intended** egg-per-catch model, not yet coded |
| Implementation and release verification | [44-main-integration-checklist.md](44-main-integration-checklist.md) | **Build 020** bounded test evidence and remaining gates; does not supersede Kanban statuses |
| Current Studio instructions | [34-studio-handoff.md](34-studio-handoff.md) | Begin with its **Build 020 workflow**, not archived Build 019 steps |
| Game balance/tunables and current data IDs | [`src/shared/Config.luau`](../src/shared/Config.luau), [`ProgressionConfig.luau`](../src/shared/ProgressionConfig.luau), current Luau source | Actual committed implementation. Confirm runtime and migration separately |
| Actual Build 020 eggs, genes, species and rendering | [43-creature-runtime-integration.md](43-creature-runtime-integration.md), [41-egg-outcomes-contract.md](41-egg-outcomes-contract.md) | Source + tests over historical six-species/seven-color examples |
| Artwork direction | [39-egg-appearance-shared-vision.md](39-egg-appearance-shared-vision.md), [32-artwork-guide-and-todo.md](32-artwork-guide-and-todo.md) | Aspirational asset quality and approved appearance, not automatic uploaded/runtime art |
| Shops/levels/condition mechanics | [36-crystal-shops-egg-genetics-and-progression.md](36-crystal-shops-egg-genetics-and-progression.md), [41-egg-outcomes-contract.md](41-egg-outcomes-contract.md) | Owner design vs Build 020 configuration. New condition starting odds **50/30/15/4.5/0.5** remain BD-045 |
| Security, release and paid-random restrictions | [43-player-access-and-paid-random-policy.md](43-player-access-and-paid-random-policy.md), [44-main-integration-checklist.md](44-main-integration-checklist.md), [06-roadmap-and-testing.md](06-roadmap-and-testing.md) | Keep paid flags disabled until regulatory/runtime acceptance |

## What is implemented, what is only planned?

- **Build 020 committed**: 22 prehistoric playable/collectible models, 8 egg patterns, 9 color families, uniform mixed-color 1–99% shares, 5 conditions, ten level-gated trails, six potions, event/weather systems, server-committed run rewards, 5-second ordered hatches and current three species rarity categories **Common/Rare/Legendary**. Current tier-0 condition odds are **20/25/45/9/1**, not the new owner request.
- **Owner targets NOT yet in Build 020**: one caught egg per catch (15 eggs for a 500-food example; 150 for 5,000 food), separate five-slot bonus egg nests, six-species-rarity-style examples with **Uncommon/Epic** (tier taxonomy not implemented), new tier-0 conditions **50/30/15/4.5/0.5**, five-minute rotating limited-stock potion offers, unified Shop/category tiles/art, six-category trail presentation/art, richer environment/food, hill traction, streamlined Home, touch/HUD repositioning and richer atmospheric weather. Track via BD-044–056.
- **Verified vs unverified**: earlier disposable Studio sessions and offline tests do **not** establish newest real paid receipts, published non-owner asset access, physical phone FPS/touch, full latest multiplayer/load or persistent profile migration. Refer to the integration checklist for precise bounds.

## Historical documents: keep for traceability, not as active instructions

Do **not** delete build snapshots or test evidence just to make them look current. Retain their specific facts and outputs, with clear historical notices. Older strings like "this is the current build", "persistence is not implemented", "GitHub main is Build 013", "three-species only" and "60-second newly earned egg timing" are scoped to their original dates/builds.

| Historical grouping | Main documents | Why retained |
| --- | --- | --- |
| Initial September scope, architecture and alpha simulation | [01-project-brief](01-project-brief.md), [04-architecture](04-architecture.md), [05-asset-pipeline](05-asset-pipeline.md), [13-persistence contracts](13-persistence-remote-contracts.md), [15-economy simulation](15-economy-simulation.md) | Earlier owner/test decisions and security/math evidence |
| Early procedural/redesign/builds 013–016 | [23-original asset manifest](23-original-asset-manifest.md), [24-visual kit](24-visual-kit-test.md), [25-redesign](25-redesign.md), [26-build014](26-redesign-test.md), [27-build015](27-mountain-island.md), [28-build016](28-ui-overhaul.md) | Audit/source lineage, no longer current art or UX requirements |
| Builds 017–019 handoffs and feature acceptance | [30-build017](30-build017-and-progression-roadmap.md), [31-build018](31-build018-progression-test.md), [35-events](35-event-mutations-and-visual-upgrade.md), [37-hatching](37-hatching-traits-and-leaderboards.md), [38-motion](38-ui-motion-and-performance.md), [39-shops acceptance](39-crystal-shops-and-genetics-acceptance.md), [42-multiplayer](42-live-multiplayer-test.md) | Dated test results and implementation history, not proof new work is done |
| Build 020 snapshot | [44-main integration](44-main-integration-checklist.md), [43-creature integration](43-creature-runtime-integration.md) | The **current reviewed** GitHub build snapshot; advance on a new build rather than overwriting older evidence |

## Duplication policy

- **One status board**: `07-kanban.md`. Keep detailed checklists in their specialized spec and link them; do not duplicate 12-item acceptance lists in the board.
- **One owner-target reward document**: `09-reward-economy.md`. Historical direct-copy `N(c)=c` arithmetic lives in `15-economy-simulation.md`; it must never be silently reinstated.
- **One consolidated egg appearance guide**: `39-egg-appearance-shared-vision.md`; the general artwork production guide `32` covers export/asset workflow. `41` covers **mechanical** probabilities, saved outcomes and paid-random disclosure, not art taste.
- **One active Studio entry point**: current section of `34-studio-handoff.md`; older build steps stay in marked historical subsections.
- **Use config/source for shipped mechanics**; use owner-target specs for intent; use Studio evidence for acceptance. If contradictory, raise or record the conflict and update the appropriate source of truth rather than copying a new value into every document.

## Maintenance checklist

1. Record date, branch/commit/build and whether a statement means **implemented**, **proposed** or **verified**.
2. When altering current balance, update actual source, saved-version migrations, outcome disclosure and tests **before** calling a target live.
3. If a newer build replaces Build 020, refresh README + this guide + current handoff + integration checklist together.
4. Update the task status **only** in Kanban, including evidence link; older milestones keep historical snapshots.
5. For shop art and Blender assets, source/render, approved preview, uploaded owner-bound IDs, integration and device verification are different stages.
