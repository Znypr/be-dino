[Download Build 019](build/BeDino-Build019.rbxlx). The in-game badge must show `BUILD redesign-019`. [Exact Studio handoff and adjustment guide](docs/34-studio-handoff.md).

Build 019 completes layered artwork wiring, E leap, food catches, Diamond fusion, a six-species collection, isolated Studio test currency/10-second eggs, sequential egg reveals and current build automation. Roblox uploads and Studio acceptance remain pending. Use the `redesign/resources-and-core-fixes` branch.

## Build 017: rebuilt UI and reliable resource delivery

- [Original UI v2 assets](resources/ui/v2/README.md)
- [Steal an Egg reference gallery and analysis](resources/references/steal-an-egg/README.md)
- [Individual screen/model task list and engine checks](docs/28-ui-overhaul.md)

Build 017 packages native triangle resource Models, replaces the UI, corrects terrain food placement checks, and adds a separate sanctuary with explicit exploration entry. Local checks pass; Studio gameplay, visual and mobile performance verification remains required. Production MeshPart imports and full-resolution uploaded UI image bindings are documented.

# Be Dino!
An original Roblox dinosaur growth-and-collection arena inspired by Be Fish.

**Stage:** Build 019 repository work complete; Studio acceptance pending. **Updated:** 2026-10-08.
**Owner:** Znypr's Roblox account. **Studio:** installed. **Budget:** €0.
**First milestone:** private community test with a small complete progression loop.

## Try the prototype
Download [BeDino-Build019.rbxlx](build/BeDino-Build019.rbxlx), open it in Studio, and use the current private test experience. No plugin is required.

For the current build, use [Build 019 handoff](docs/34-studio-handoff.md) and [mesh/icon import guide](resources/README.md). The general Studio workflow remains in [Studio quickstart](docs/10-studio-quickstart.md).

## Start here
- [Project brief and roles](docs/01-project-brief.md)
- [Reference research](docs/02-reference-research.md)
- [Game design](docs/03-game-design.md)
- [Architecture](docs/04-architecture.md)
- [Assets, UI and audio](docs/05-asset-pipeline.md)
- [Roadmap and release gates](docs/06-roadmap-and-testing.md)
- [Canonical Kanban](docs/07-kanban.md)
- [Decisions and risks](docs/08-decisions-and-risks.md)
- [Reward economy specification](docs/09-reward-economy.md)
- [Persistence and remote contracts](docs/13-persistence-remote-contracts.md)

## Confirmed loop
Collect food, grow, eat smaller dinosaurs, then end the run or get eaten.
Award collection dinosaurs immediately, plus additional chests with separate loot.
Higher catch scores give more copies overall; progressively rarer tiers contain fewer copies. Duplicate species stack.
Catch score is distinct from growth score. Exact balancing remains proposed.

## Current verified progress
- Build 003: desktop movement/camera and two-client replication passed.
- Build 004: food/growth passed.
- Build 005: PvP, spawn safety and run ending passed.
- Build 006: DataStore save/rejoin, fail-closed loading and idempotent settlement passed.
- Build 007: lease contention/stale-writer verification and restart persistence passed in the new private test experience.
- Build 008: collection/equip tests 1–8 passed.
- Build 009: earned chest queue tests 1–8 passed.
- Build 010: Gold mutation tests 1–8 passed.
- Build 011: core UI tests 1–8 passed, including phone-landscape emulator.
- Build 012: security/multiplayer regression tests 1–8 passed.
- Build 013: original procedural dinosaur/map kit ready for visual runtime verification.
- Mobile/touch remains pending.

## Planned expansion: crystal shops and egg genetics

[Crystal/egg design specification](docs/36-crystal-shops-egg-genetics-and-progression.md) · [BD-035–041 in canonical Kanban](docs/07-kanban.md).

Future work includes end-of-run and map crystals plus Robux crystal packs, random crystal-purchased eggs, ten increasingly fast level-gated trails, a 5-minute Speed Potion, condition probability upgrades, rare two-colour eggs with inherited dinosaur colours, Normal/Big sizes, shiny sparkles and production-quality Blender-rendered modular egg artwork. All are **Todo**, not Build 019 acceptance claims. Numerical balancing and purchase/odds rules need review before release.

## Working agreement
GitHub is the single source of truth for plans and code. `docs/07-kanban.md` is the live tracker.
Use original assets, free tools and server-owned gameplay state.
Three species validate the first progression loop; a larger catalog follows after testing.

## Next action
Open the new build, follow [Build 015 checks](docs/27-mountain-island.md), and import [mesh resources](resources/README.md).

## Build 014 redesign
- Explicit growing torso collision; solid trees/rocks, non-solid foliage and pickups.
- 64 map-wide sectors with small randomized berry/fruit/amber clusters and per-type values.
- Early loading overlay with actionable failures; unpublished Studio uses disposable profiles only.
- Layered animated modal/buttons and 3D collection previews.
- `resources/` contains 10 original OBJ/MTL meshes, six reusable SVG/PNG icons and a real mesh render.

Mesh files must be imported through Studio; the base place uses fallback primitives until import. Studio physics, multiplayer, mobile and upload-permission verification remain pending. The screenshots show a newer local map/lobby build than the committed baseline; uncommitted local code is not included here.

## Current Build 015
[Inspect all 2D assets](resources/ui/README.md), [mountain-island direction](resources/concepts/mountain-island.png) and [verification details](docs/27-mountain-island.md). The large terrain, jump mechanic and crystal/egg food are implemented. Original mesh/icon data is embedded for client-local Mesh/Image API rendering with explicit permission-aware fallback. Runtime Studio playtesting remains required.

## Current fixes and next systems

[Build 017 completion and progression roadmap](docs/30-build017-and-progression-roadmap.md): popup cropping, missing eggs, larger dinosaur previews, sharp icons, crystal currency, Aura Shop, 60-second leap, random-weather timers and Potion Shop. Open task status: [Kanban](docs/07-kanban.md).

[Build 018 features and acceptance checks](docs/31-build018-progression-test.md) · [20 individual sharp icons](resources/ui/v2/scalable/README.md). Crystal wallet, Aura Shop, 60-second leap, random weather and Potion Shop are implemented for private testing. Studio acceptance remains open.
