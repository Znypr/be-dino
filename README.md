# Be Dino!
An original Roblox dinosaur growth-and-collection arena inspired by Be Fish.

**Stage:** persistence + collection/equip accepted; Build 009 chest queue ready for Studio testing. **Updated:** 2026-09-18.
**Owner:** Znypr's Roblox account. **Studio:** installed. **Budget:** €0.
**First milestone:** private community test with a small complete progression loop.

## Try the prototype
Download [BeDino-Prototype.rbxlx](build/BeDino-Prototype.rbxlx), open it in Studio, and use the current private test experience. No plugin is required.

For the current build, use [Build 009 chest queue test](docs/19-chest-queue-test.md). The general Studio workflow remains in [Studio quickstart](docs/10-studio-quickstart.md).

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
- Build 009: earned chest queue implementation ready for runtime verification.
- Mobile/touch remains pending.

## Working agreement
GitHub is the single source of truth for plans and code. `docs/07-kanban.md` is the live tracker.
Use original assets, free tools and server-owned gameplay state.
Three species validate the first progression loop; a larger catalog follows after testing.

## Next action
Run the Build 009 checks in [docs/19-chest-queue-test.md](docs/19-chest-queue-test.md).
