# Kanban and task specifications
Updated 2026-09-17. This file is the canonical task tracker.

Desktop movement/two-client replication and Build 004 food/growth have been accepted by Znypr. Mobile remains untested. Build 005 now implements the first PvP/run-ending slice and is awaiting Studio verification.

## Board
| Backlog | Ready | In progress | Review / test | Blocked | Done |
|---|---|---|---|---|---|
| BD-011–022 | BD-007 art brief; BD-010 economy | None | BD-006 mobile; BD-009 PvP/run ending | BD-004 private-place record | BD-001, BD-002, BD-003, BD-005, BD-008 |

Backlog means dependencies are not yet satisfied. `Review / test` means code exists but acceptance evidence is still required. `Done` requires a recorded artifact, decision or live test result. Keep at most one implementation task active at a time.

## Operating rules
- Preserve task IDs and record the commit/build or actual test evidence used for completion.
- Server authority and persistence safety are P0. Do not trade these for polish.
- Proposed balance stays configurable until Znypr approves it.
- Znypr performs Studio/account/device actions unavailable to this environment.
- Do not maintain a second conflicting task board.

## Task index
| ID | Status | Priority | Task | Dependencies |
|---|---|---|---|---|
| BD-001 | Done | P0 | Research and initial project documents | None |
| BD-002 | Done | P0 | Choose first-test direction | BD-001 |
| BD-003 | Done | P0 | Resolve setup and design blockers | BD-002 |
| BD-004 | Blocked | P0 | Bootstrap reproducible project and private test place | BD-003 |
| BD-005 | Done | P0 | Specify persistence and remote contracts | BD-003 |
| BD-006 | Review / test | P0 | Prototype one dinosaur controller and camera | BD-004 |
| BD-007 | Ready | P1 | Specify original asset kit and visual sample | BD-002 |
| BD-008 | Done | P0 | Implement food and growth | BD-005, BD-006 |
| BD-009 | Review / test | P0 | Implement PvP, spawn safety and run ending | BD-005, BD-008 |
| BD-010 | Ready | P0 | Define and simulate alpha economy | BD-003 |
| BD-011 | Backlog | P0 | Build profile storage and idempotent settlement | BD-005, BD-009, BD-010 |
| BD-012 | Backlog | P0 | Build collection and equip | BD-011 |
| BD-013 | Backlog | P0 | Build earned egg queue | BD-010, BD-011 |
| BD-014 | Backlog | P0 | Build Gold mutation | BD-012 |
| BD-015 | Backlog | P0 | Implement core UI and first-session guidance | BD-006, BD-012, BD-013, BD-014 |
| BD-016 | Backlog | P1 | Produce and integrate dinosaur/map kit | BD-006, BD-007 |
| BD-017 | Backlog | P1 | Integrate minimal sound feedback | BD-004, BD-008, BD-013 |
| BD-018 | Backlog | P0 | Run multiplayer, security and persistence suite | BD-011–015 |
| BD-019 | Backlog | P0 | Run device/load and published-asset checks | BD-015–017 |
| BD-020 | Backlog | P0 | Prepare private test release and rollback | BD-018, BD-019 |
| BD-021 | Backlog | P0 | Observe community test and triage | BD-020 |
| BD-022 | Backlog | P1 | Decide public alpha scope after test | BD-021 |

## Acceptance and current evidence

### BD-001 — research
Done. Initial screenshot/source research and planning documents were completed on 2026-09-17.

### BD-002 — direction
Done. Znypr selected a private test, cute/simple ground arena and small complete progression loop.

### BD-003 — setup/design blockers
Done. Personal account, Studio installed, €0 target budget, immediate run dinosaur loot plus separate chest loot, increasing total copy rewards and stacked duplicates are confirmed.

### BD-004 — reproducible project/private place
**Done when:** source mapping/build is reproducible and the actual private test experience/place is recorded with isolated test data.

Source mapping, dependency-free Python packager and generated `.rbxlx` are working. Local Studio builds have been opened and tested, but the project still does not record the private test place/experience IDs or isolated data namespace. That remains the blocker.

### BD-005 — persistence and remote contracts
Done as a specification. `docs/13-persistence-remote-contracts.md` chooses a project-owned `DataStoreService`/`UpdateAsync` repository with leases, revisions, immutable operation outcomes and explicit remote validation. Durable implementation remains BD-011.

### BD-006 — controller/camera
**Done when:** desktop and touch movement work, min/max visual-size behavior is usable and two clients replicate correctly.

Desktop evidence passed: movement, camera, dinosaur visibility, size behavior, reset isolation and two-client replication. Mobile/touch is still untested, so the task remains `Review / test`.

### BD-007 — asset kit
**Done when:** one original dinosaur silhouette/palette, manifest template and procedural fallback are reviewable.

Ready and non-blocking. Do not polish the whole catalog before the loop works.

### BD-008 — food/growth
Done. Znypr reported all Build 004 checklist cases working: pickup, growth, respawn, simultaneous ownership, remote growth replication and reset. The implementation remains bounded and server-owned; tuning is temporary.

### BD-009 — PvP/spawn safety/run ending
**Done when:** size eligibility, spawn protection, predation, manual exit and terminal-event races behave correctly with multiplayer evidence and only one terminal transition per victim.

Build 005 implements: 5-second protection, configurable 10% score margin, server proximity/occlusion checks, deterministic victim claim, temporary catch score, +25 PvP growth, 3-second movement-cancelable exit and a shared terminal guard for predation/manual exit/death. See `docs/14-pvp-run-test.md`. Studio verification is next.

### BD-010 — alpha economy
**Done when:** catch-to-copy math, rarity quantities, eligibility, species allocation, independent chest table, limits, repeat-victim behavior and mutation pacing are simulated and reviewed.

Ready. `docs/09-reward-economy.md` is still candidate tuning, not accepted balance.

### BD-011 — persistence/settlement
**Done when:** rejoin, load failures, duplicate settlement, stale sessions and competing servers preserve committed inventory and immutable run outcomes.

Use the BD-005 contract. Never overwrite a failed load with defaults.

### BD-012 — collection/equip
**Done when:** three species definitions, owned/locked counts and equip survive reconnect; invalid equip is rejected.

Placeholder art is allowed.

### BD-013 — earned chest queue
**Done when:** server timestamps, offline elapsed time, duplicate claims and capacity/overflow policy pass. Chest loot remains independent from immediate run loot.

### BD-014 — Gold mutation
**Done when:** atomic 50-copy conversion handles 49/50/51 copies, duplicate requests and equipped-copy semantics without negative counts.

### BD-015 — core UI
**Done when:** lobby, HUD, run summary, collection and chest queue are usable on desktop/touch and large duplicate stacks render as grouped counts rather than hundreds of cards.

### BD-016 — dinosaur/map kit
**Done when:** three distinct original dinosaurs, one arena and Gold treatment pass collision/camera/permission checks. Procedural fallback is acceptable for the private test.

### BD-017 — audio
**Done when:** minimal effects work for a non-owner published tester with independent mute/volume behavior. Ambience is optional.

### BD-018 — multiplayer/security/persistence suite
Execute the verification matrix from `docs/06-roadmap-and-testing.md`. Source inspection is not runtime evidence.

### BD-019 — device/load/published assets
Requires a real target phone plus the agreed multiplayer/pickup load test and non-owner asset checks.

### BD-020 — private release/rollback
Requires a known-good commit/build, private access settings, no public debug grants, known issues and a tested rollback.

### BD-021 — observed community test
Run the small invited session only after BD-020. Capture friction, repeat-run behavior and defects separately from suggestions.

### BD-022 — public-alpha decision
Public scope is an evidence-based later decision. Passing code generation alone never triggers launch.

## Session log
- 2026-09-17: Build 005 prepared. BD-005 specification completed. Added `RunLifecycle` and `PredationService`, one no-payload/rate-limited `RequestEndRun` remote, spawn protection, score-gated PvP, deterministic victim claim, temporary catch score, manual exit channel and a shared terminal guard. Generated build now packages 8 scripts; 5/5 Python packaging tests pass. BD-009 moved to `Review / test`; next action is `docs/14-pvp-run-test.md` in Studio.
- 2026-09-17: Znypr reported all Build 004 food/growth checklist cases working. BD-008 moved to Done.
- 2026-09-17: Znypr reported all v003 desktop single-player checks and four two-client checks passed (visibility, movement replication, independent size changes, reset isolation). Mobile remains untested, so BD-006 remains `Review / test`.
- 2026-09-17: Build 003 fixed the character-parenting race after earlier dinosaur/pad failures.
- 2026-09-17: Build 002 removed the protected Workspace startup assignment after Build 001 failed at server startup.
- 2026-09-17: Initial source/build bootstrap, planning, direction and reward relationship were established.

## Deferred objectives
Paid products/gems, trading, auto-farm, daily/group rewards, global leaderboards, extra maps, more mutations, advanced combat, console certification and realistic art. Reassess after BD-021.
