# Kanban and task specifications
Updated 2026-09-17. This file is the canonical task tracker. No implementation has started.

## Board
| Backlog | Ready | In progress | Review / test | Blocked | Done |
|---|---|---|---|---|---|
| BD-004–006, BD-008–022 | BD-003 decisions; BD-007 art brief | None | None | None | BD-001 research; BD-002 direction |

Backlog tasks with unmet dependencies are not executable yet. Move to Blocked only when started work encounters an obstacle; record the obstacle and person/action needed.
Ready means actionable now. Done means acceptance evidence exists, not merely code generated.
The two completed items are planning work, not game features. In-progress limit: one implementation task.

## Operating rules
- Preserve stable task IDs. Record a commit, artifact or actual test result for completion.
- A task has one accountable lead role; combined roles indicate collaboration, with the first role accountable.
- Review roles are review passes, not claims of independent staff. Identify an actual reviewer when one participates.
- Update board columns and task status together. Record date, blocker and next action every session.
- P0 is required for the private-test gate; P1 is planned quality work with fallback options.
- The board can later migrate to GitHub Issues/Projects, but do not maintain two conflicting status sources.

## Task index
| ID | Status | Priority | Accountable role | Reviewer | Task | Dependencies |
|---|---|---|---|---|---|---|
| BD-001 | Done | P0 | PO | PO review | Research and initial project documents | None |
| BD-002 | Done | P0 | PO | Znypr | Choose first-test direction | BD-001 |
| BD-003 | Ready | P0 | PO | Znypr | Resolve setup and design blockers | BD-002 |
| BD-004 | Backlog | P0 | REL | DEV | Bootstrap reproducible project and private test place | BD-003 |
| BD-005 | Backlog | P0 | ARCH | QA | Specify persistence and remote contracts | BD-003, BD-004 |
| BD-006 | Backlog | P0 | DEV | QA | Prototype one dinosaur controller and camera | BD-004 |
| BD-007 | Ready | P1 | ART | Znypr | Specify original asset kit and visual sample | BD-002 |
| BD-008 | Backlog | P0 | DEV | QA | Implement food and growth | BD-005, BD-006 |
| BD-009 | Backlog | P0 | DEV | QA | Implement PvP, spawn safety and run ending | BD-005, BD-008 |
| BD-010 | Backlog | P0 | GD | PO | Define and simulate alpha economy | BD-003 |
| BD-011 | Backlog | P0 | DEV | QA | Build profile storage and idempotent settlement | BD-005, BD-009, BD-010 |
| BD-012 | Backlog | P0 | DEV | QA | Build collection and equip | BD-011 |
| BD-013 | Backlog | P0 | DEV | QA | Build earned egg queue | BD-010, BD-011 |
| BD-014 | Backlog | P0 | DEV | QA | Build Gold mutation | BD-012 |
| BD-015 | Backlog | P0 | ART + DEV | QA | Implement core UI and first-session guidance | BD-006, BD-012, BD-013, BD-014 |
| BD-016 | Backlog | P1 | ART | QA + Znypr | Produce and integrate dinosaur/map kit | BD-006, BD-007 |
| BD-017 | Backlog | P1 | AUDIO | QA | Integrate minimal sound feedback | BD-004, BD-008, BD-013 |
| BD-018 | Backlog | P0 | QA | ARCH | Run multiplayer, security and persistence suite | BD-011, BD-012, BD-013, BD-014, BD-015 |
| BD-019 | Backlog | P0 | QA | REL | Run device/load and published-asset checks | BD-015, BD-016, BD-017 |
| BD-020 | Backlog | P0 | REL | Znypr | Prepare private test release and rollback | BD-018, BD-019 |
| BD-021 | Backlog | P0 | PO + QA | Znypr | Observe community test and triage | BD-020 |
| BD-022 | Backlog | P1 | PO | Znypr | Decide public alpha scope after test | BD-021 |

## Acceptance and next actions

### BD-001: Research and initial project documents
**Done when:** Evidence ledger covers all ten screenshots; observed, reported and proposed rules separated.

**Evidence / next action:** Completed 2026-09-17: screenshot inspection and linked primary documentation; no live gameplay verification.

### BD-002: Choose first-test direction
**Done when:** Owner selects audience/access, visual direction and progression scope.

**Evidence / next action:** Completed: private test, cute ground arena, small complete loop selected by Znypr.

### BD-003: Resolve setup and design blockers
**Done when:** Record Roblox owner, Studio availability, deadline, budget, reward/egg relationship and test reset policy in decision log.

**Evidence / next action:** Ask owner; questions are listed in docs/08-decisions-and-risks.md.

### BD-004: Bootstrap reproducible project and private test place
**Done when:** Pin toolchain, define source mapping, sync/build a minimal place, document one-command build and Studio handoff; isolate test data.

**Evidence / next action:** Needs account/Studio operator; no tool versions or place IDs invented.

### BD-005: Specify persistence and remote contracts
**Done when:** Choose reviewed persistence approach; define session ownership, failure behavior, operation IDs, schema and remote validation matrix.

**Evidence / next action:** Review save races and client-owned physics explicitly.

### BD-006: Prototype one dinosaur controller and camera
**Done when:** Desktop and touch movement work; min/max visual size passes ground and obstacle tests; second client sees stable motion.

**Evidence / next action:** Timebox art; fixed collider is an experiment, not a proven solution.

### BD-007: Specify original asset kit and visual sample
**Done when:** One dinosaur silhouette/palette proposal, asset manifest template and procedural fallback are reviewable.

**Evidence / next action:** No purchased services assumed; do not polish all models first.

### BD-008: Implement food and growth
**Done when:** Validated pickup grants once, respawns correctly, score and visual size follow bounded config; simultaneous/distant claims tested.

**Evidence / next action:** Use bounded spawn count and spatial lookup.

### BD-009: Implement PvP, spawn safety and run ending
**Done when:** Agreed size rule, spawn protection, exit and death races behave correctly with two clients; one terminal transition per run.

**Evidence / next action:** Owner resolves margin/exit rules first.

### BD-010: Define and simulate alpha economy
**Done when:** Config specifies score/reward conversion, weights, caps, repeated-victim handling and mutation cost; simulate rolls and estimate unlock time.

**Evidence / next action:** Trial 80/18/2 weights are not final; inspect early progress and snowballing.

### BD-011: Build profile storage and idempotent settlement
**Done when:** Rejoin, save failures, duplicate settlement and stale-session tests preserve committed inventory; immutable run reward outcome.

**Evidence / next action:** No defaults overwrite on failed load; record checkpoint-loss boundary.

### BD-012: Build collection and equip
**Done when:** Three species definitions, owned/locked inventory and equip persist; unknown/unowned equip rejected; death preserves collection.

**Evidence / next action:** Placeholder art allowed until BD-016.

### BD-013: Build earned egg queue
**Done when:** Queue uses server timestamps; sequential/offline behavior, duplicate claims and capacity overflow pass; test timer isolated.

**Evidence / next action:** Owner confirms immediate rewards versus chest-gated rewards.

### BD-014: Build Gold mutation
**Done when:** Atomic conversion handles 49/50/51 copies, double request and equipped-copy edge case; visual/stat config updated.

**Evidence / next action:** Test grants exist only in isolated environment.

### BD-015: Implement core UI and first-session guidance
**Done when:** Lobby, HUD, summary, collection and eggs usable on desktop/touch with empty/loading/error states; Play Again completes loop.

**Evidence / next action:** Integrate incrementally; completion requires all core screens.

### BD-016: Produce and integrate dinosaur/map kit
**Done when:** Three distinct original dinosaurs, minimal animation, one arena and Gold treatment pass collision/camera/permission checks.

**Evidence / next action:** Use procedural fallback if polished import blocks milestone.

### BD-017: Integrate minimal sound feedback
**Done when:** Seven effects documented in manifest, audible for non-owner in published test, independent volume/mute works.

**Evidence / next action:** Ambience optional; check permissions.

### BD-018: Run multiplayer, security and persistence suite
**Done when:** Execute roadmap matrix; record build, observed outcomes and defects; no open critical exploit/data-loss issue.

**Evidence / next action:** Code inspection does not count as executed Studio tests.

### BD-019: Run device/load and published-asset checks
**Done when:** Real target phone and 8-player/300-pickup test evidence; no stuck controls or inaccessible actions; asset access works.

**Evidence / next action:** If target not met, reduce budget then rerun affected checks.

### BD-020: Prepare private test release and rollback
**Done when:** Known-good commit/build, access settings, reset policy, no public debug grants, tested rollback, known issues.

**Evidence / next action:** Private access only; public release is a later decision.

### BD-021: Observe community test and triage
**Done when:** 5-8 invited players proposed; capture friction, repeat-run behavior and errors; prioritize fixes and decide next scope.

**Evidence / next action:** Znypr handles invitations and real-device participation.

### BD-022: Decide public alpha scope after test
**Done when:** Evidence-backed go/no-go, remaining blockers, final timer and progression reset policy documented.

**Evidence / next action:** No automatic public launch and no monetization dependency.

## Session log
- 2026-09-17: Initial research and planning completed. Znypr selected private test, cute ground arena, small full progression loop. Implementation and all live Roblox checks remain unstarted.

## Deferred objectives
Paid products/gems, trading, auto-farm, daily/group rewards, global leaderboards, additional maps, more mutations, advanced combat, console certification and realistic art. Reassess after BD-021 rather than silently adding them to the first release.
