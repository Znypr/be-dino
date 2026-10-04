## Build 016: rebuilt UI and reliable resource delivery

- [Original UI v2 assets](resources/ui/v2/README.md)
- [Steal an Egg reference gallery and analysis](resources/references/steal-an-egg/README.md)
- [Individual screen/model task list and engine checks](docs/28-ui-overhaul.md)

Build 016 packages native triangle resource Models, replaces the UI, corrects terrain food placement checks, and adds a separate sanctuary with explicit exploration entry. Local checks pass; Studio gameplay, visual and mobile performance verification remains required. Production MeshPart imports and full-resolution uploaded UI image bindings are documented.

# Be Dino!
An original Roblox dinosaur growth-and-collection arena inspired by Be Fish.

**Stage:** Build 015 mountain island, jumping and reusable art ready for Studio verification. **Updated:** 2026-10-04.
**Owner:** Znypr's Roblox account. **Studio:** installed. **Budget:** €0.
**First milestone:** private community test with a small complete progression loop.

## Try the prototype
Download [BeDino-Prototype.rbxlx](build/BeDino-Prototype.rbxlx), open it in Studio, and use the current private test experience. No plugin is required.

For the current build, use [Build 015 checks](docs/27-mountain-island.md) and [mesh/icon import guide](resources/README.md). The general Studio workflow remains in [Studio quickstart](docs/10-studio-quickstart.md).

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
