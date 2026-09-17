# Be Dino!
An original Roblox dinosaur growth-and-collection arena inspired by Be Fish.

**Stage:** desktop core loop accepted; Build 006 persistence tests 1–10 passed; Build 007 persistence lease verification ready. **Updated:** 2026-09-17.
**Owner:** Znypr's Roblox account. **Studio:** installed. **Budget:** €0.
**First milestone:** private community test with a small complete progression loop.

## Try the prototype
Download [BeDino-Prototype.rbxlx](build/BeDino-Prototype.rbxlx) with GitHub's raw download button, open it in Studio, and use the separate private test experience. No plugin is required.

For the current build, use [Build 007 persistence lease test](docs/17-persistence-lease-test.md). The general Studio workflow remains in [Studio quickstart](docs/10-studio-quickstart.md).

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
- Build 003: desktop movement, camera, dinosaur visibility, size behavior, reset isolation and two-client replication passed.
- Build 004: food pickup, growth, respawn, simultaneous ownership, other-player growth replication and reset passed.
- Build 005: PvP, spawn safety, manual ending and terminal-race tests 1–9 passed.
- Build 006: persistence tests 1–10 passed, including rejoin persistence, duplicate-settlement protection, fail-closed DataStore loading, Reset Character settlement and repeat-victim anti-farm behavior.
- Build 007: DataStore lease/stale-writer self-test implemented and CI/build checks passed; Studio runtime acceptance is pending.
- Mobile/touch remains pending.

## Working agreement
GitHub is the single source of truth for plans and code. `docs/07-kanban.md` is the live tracker.
Use original assets, free tools and server-owned gameplay state. Packaging tests run automatically in CI.
Three species validate the first progression loop; a larger catalog follows after testing.

## Next action
Publish Build 007 over the existing private test place and run [the four persistence lease checks](docs/17-persistence-lease-test.md).
