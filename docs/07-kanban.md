# Kanban and task specifications
Updated 2026-10-08. This file is the canonical task tracker.

Build 005 PvP/run-ending tests 1–9 passed. Build 006 persistence tests 1–10 passed. Build 007 lease/stale-writer verification and restart persistence passed in the new private test experience. BD-011 is Done. Build 008 collection/equip passed all 8 runtime tests. BD-012 is Done. Build 009 earned chest queue passed all 8 runtime tests. BD-013 is Done. Build 010 Gold mutation passed all 8 runtime tests. BD-014 is Done. Build 011 core UI passed all 8 desktop/phone-emulator tests. BD-015 is Done. Build 012 security/multiplayer regression passed all 8 runtime tests. BD-018 is Done. Build 013 original visual kit is ready for testing. Mobile remains untested.

## Board
| Backlog | Ready | In progress | Review / test | Blocked | Done |
|---|---|---|---|---|---|
| BD-017; BD-019–022 | BD-027 | None | BD-006 mobile; BD-016 visual kit; BD-023–026; BD-028–033 | BD-004 private-place record | BD-001, BD-002, BD-003, BD-005, BD-007, BD-008, BD-009, BD-010, BD-011, BD-012, BD-013, BD-014, BD-015, BD-018 |

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
| BD-007 | Done | P1 | Specify original asset kit and visual sample | BD-002 |
| BD-008 | Done | P0 | Implement food and growth | BD-005, BD-006 |
| BD-009 | Done | P0 | Implement PvP, spawn safety and run ending | BD-005, BD-008 |
| BD-010 | Done | P0 | Define and simulate alpha economy | BD-003 |
| BD-011 | Done | P0 | Build profile storage and idempotent settlement | BD-005, BD-009, BD-010 |
| BD-012 | Done | P0 | Build collection and equip | BD-011 |
| BD-013 | Done | P0 | Build earned egg queue | BD-010, BD-011 |
| BD-014 | Done | P0 | Build Gold mutation | BD-012 |
| BD-015 | Done | P0 | Implement core UI and first-session guidance | BD-006, BD-012, BD-013, BD-014 |
| BD-016 | Review / test | P1 | Produce and integrate dinosaur/map kit | BD-006, BD-007 |
| BD-017 | Backlog | P1 | Integrate minimal sound feedback | BD-004, BD-008, BD-013 |
| BD-018 | Done | P0 | Run multiplayer, security and persistence suite | BD-011–015 |
| BD-019 | Backlog | P0 | Run device/load and published-asset checks | BD-015–017 |
| BD-020 | Backlog | P0 | Prepare private test release and rollback | BD-018, BD-019 |
| BD-021 | Backlog | P0 | Observe community test and triage | BD-020 |
| BD-022 | Backlog | P1 | Decide public alpha scope after test | BD-021 |

| BD-023 | Review / test | P1 | Fix cropped popups and responsive margins | Build 017 |
| BD-024 | Review / test | P1 | Restore visible egg previews | Build 017 |
| BD-025 | Review / test | P1 | Enlarge centered dinosaur previews | Build 017 |
| BD-026 | Review / test | P1 | Replace pixelated UI icon rendering everywhere | Build 017 |
| BD-027 | Ready | P0 | Verify visible floor food and close Build 017 regressions | BD-023–026 |
| BD-028 | Review / test | P1 | Persistent crystal currency and random map pickups | BD-027, BD-011 |
| BD-029 | Review / test | P1 | Aura shop, ownership/equip and eating-growth effects | BD-028 |
| BD-030 | Review / test | P1 | Forward leap with 60-second cooldown and HUD | BD-027, BD-006 |
| BD-031 | Review / test | P1 | Random weather, rarity bonuses and bottom-right timers | BD-027 |
| BD-032 | Review / test | P1 | Crystal potion shop, timed buffs and inventory | BD-028, BD-031 |
| BD-033 | Review / test | P1 | Matching aura, potion, leap, weather and currency icons | BD-026 |

## Build 017 and next features

[Detailed requirements, screen list, icon backlog and acceptance checks](30-build017-and-progression-roadmap.md). [Build 018 implementation and recorded local checks](31-build018-progression-test.md). Build 017 source/UI corrections and an isolated final export are prepared; progression systems are now integrated in Build 018. BD-027 and Studio acceptance remain open before release. Earlier Done records apply to their tested historical builds; they do not certify the redesigned Build 017.

## Acceptance and current evidence

### Build 019 MCP acceptance, 2026-10-08

Connected instance: `newbuild`, Studio ID `c91d2e6f-2da9-4457-afa0-4fe028f1a83f`.
Config and rendered badge both confirm `redesign-019`. Place `111259822927673`,
experience `10769812255`, owner User `znyprs` / `7285577648`. This is a published
Studio session, not the disposable unpublished preview requested in the handoff.
`ProfileMode=Persistent`, normal wallet (0 crystals), one Base Compy and no eggs
were observed. Experience privacy/access settings are not verified by these tools.

| Check | Actual evidence | Status |
|---|---|---|
| Startup / food | Profile loaded, packaged Compy attached, Food Ready / 1536, terrain ready, empty startup error | Pass for this single-client session |
| Gameplay / catches | Normal start remote changed Sanctuary to Active; MCP navigation moved the character; fruit awarded 4 growth and 0.12 carry; live server FoodCatchRules returned 15 catches / zero carry for 500 raw points; zero-catch manual exit committed revision 4 and returned to Sanctuary at (0, 9.5, 365) | Partial: rewarded banking, long walking routes, terrain edges and two-client pickup races remain |
| E leap | Keyboard E moved Z from 30 to about 10.82; LastLeapStatus=leaping, MovementSecurityStatus=OK, LeapReadyAt set 60 seconds ahead | Pass for desktop activation; touch and multiplayer physics remain |
| Six dinosaurs | Collection JSON has all six; screenshots show both rows with distinct rendered previews; not-owned species display Not discovered; live Raptor equip returned locked and retained Compy | Preview / locked rejection pass; all six actual equip/run paths remain |
| Aura / potion shops | Screenshots show three assembled aura rings and both bottle bases with native emblems; prices and counts visible | Visual pass; successful live purchases/equip/use/replacement remain (normal wallet is empty) |
| Gold / Diamond | Screenshots show both colored dinosaur previews, uploaded badges and 50 Base / 50 Gold prices; live Diamond request returned insufficient_copies with unchanged inventory | Visual / rejection pass; live atomic conversion remains (insufficient copies) |
| Sequential hatching | Persistent queue is empty | Pending live claim / reveal / NEXT EGG; offline harness is separate evidence |
| Responsive UI | iPhone 17 Pro landscape screenshot confirmed ~26px navigation targets and joystick overlap; final phone HUD screenshots show horizontal 44px navigation, relocated HUD/action/timers and no overlap; desktop screenshot verifies restored layout | Pass for tested HUD layouts; real touch interaction, other phones and scaled modal target ergonomics remain |
| Nine PNG uploads | MCP upload returned nine actual image IDs; GetProductInfo verified all image creators match the experience owner; client PreloadAsync returned Success and all nine rendered probe ImageLabels reported IsLoaded=true | Pass in owner Studio; non-owner published client remains |
| Console | Initial gameplay and shop/collection/fusion passes showed only the build-ready message; rapid stop/start produced SessionBusy and blocked character spawn; after lease expiry restart loaded normally; final console contains only the build-ready message | Pass for tested sessions; rapid restart must allow lease expiry |

Uploaded IDs and owner metadata are in `resources/ui/v2/layers/upload-bindings.json`.
`ArtworkAssets` was regenerated and synced to Studio; revised client source was synced
in Edit mode. Screenshots were inspected through MCP with capture IDs
`019-baseline`, `019-collection-settled`, `019-lower-three-dinosaurs`,
`019-aura-loaded`, `019-potions-loaded`, `019-gold-fusion`, `019-diamond-fusion`,
`019-phone-fixed-tutorial`, `019-phone-retested`, `019-phone-active-retested`,
and `019-desktop-restored`. These are conversation captures, not archived PNG files.

Repository validation: 42 Luau sources compile with 0.741; gameplay, progression,
layout/geometry, six-species camera and artwork harnesses pass; 21 Python tests pass;
bindings check and deterministic Build 019 packaging pass. The artwork verifier now
explicitly empties its test mapping to test fallback after real IDs are recorded.
This does not certify engine physics, live saves/fusion/hatching or device performance.
BD-023 through BD-033 retain their existing review/test status; BD-019 remains open.

### BD-001 — research
Done. Initial screenshot/source research and planning documents were completed on 2026-09-17.

### BD-002 — direction
Done. Znypr selected a private test, cute/simple ground arena and small complete progression loop.

### BD-003 — setup/design blockers
Done. Personal account, Studio installed, €0 target budget, immediate run dinosaur loot plus separate chest loot, increasing total copy rewards and stacked duplicates are confirmed.

### BD-004 — reproducible project/private place
**Done when:** source mapping/build is reproducible and the actual private test experience/place is recorded with isolated test data.

Source mapping, dependency-free Python packager and generated `.rbxlx` are working. A separate private test experience is now being used for DataStore testing, but the repository still does not record its experience/place IDs. That remains the blocker for closing BD-004.

### BD-005 — persistence and remote contracts
Done as a specification. `docs/13-persistence-remote-contracts.md` chooses a project-owned `DataStoreService`/`UpdateAsync` repository with leases, revisions, immutable operation outcomes and explicit remote validation. Durable implementation remains BD-011.

### BD-006 — controller/camera
**Done when:** desktop and touch movement work, min/max visual-size behavior is usable and two clients replicate correctly.

Desktop evidence passed: movement, camera, dinosaur visibility, size behavior, reset isolation and two-client replication. Mobile/touch is still untested, so the task remains `Review / test`.

### BD-007 — asset kit
**Done when:** one original dinosaur silhouette/palette, manifest template and procedural fallback are reviewable.

Done. `docs/23-original-asset-manifest.md` records the original procedural silhouettes, palettes, Gold treatment, arena kit, rights/source and zero external-asset dependency used by Build 013.

### BD-008 — food/growth
Done. Znypr reported all Build 004 checklist cases working: pickup, growth, respawn, simultaneous ownership, remote growth replication and reset. The implementation remains bounded and server-owned; tuning is temporary.

### BD-009 — PvP/spawn safety/run ending
Done for desktop multiplayer. Znypr reported Build 005 tests 1–9 all working: spawn protection, standing-still exit, movement cancellation, equal-size safety, bigger-eats-smaller, protection after respawn, replication, exit-vs-predation race and Reset Character. The shared terminal guard produced no reported duplicate endings.

### BD-010 — alpha economy
Done for private mechanics testing. `tools/economy_sim.py`, `tests/test_economy.py` and `docs/15-economy-simulation.md` define and verify the 0–5000 catch range, exact increasing copy totals, exponential rarity allocation, eligibility thresholds, independent chest grants, repeat-victim anti-farm proposal and 50-copy mutation risk.

Important finding: one Common alpha species reaches 50 copies at catch score 62. The 50-copy mutation cost is therefore a mechanics-test value, not accepted public progression balance.

### BD-011 — persistence/settlement
**Done when:** rejoin, load failures, duplicate settlement, stale sessions and competing servers preserve committed inventory and immutable run outcomes.

Build 006 runtime tests 1–10 passed. Confirmed: load/save/rejoin, exact +1 reward settlement, deliberate duplicate settlement does not double-grant, Reset Character settles the run, repeat-victim protection behaves as designed, disabling Studio API access fails closed with no playable dinosaur, and re-enabling access restores the prior profile. Znypr also confirmed Compy copies can increase above 3; the earlier apparent stop was the 60-second anti-farm window rather than a cap.

Build 007 completed the final acceptance case. Znypr confirmed the lease test passed in a new private test experience, earned copies persisted through a full restart, and the probe did not corrupt player progression. BD-011 is Done. The temporary lease probe is removed from normal runtime in Build 008.

### BD-012 — collection/equip
**Done when:** three species definitions, owned/locked counts and equip survive reconnect; invalid equip is rejected.

Build 008 passed all eight runtime checks. Owned/locked counts, server rejection of locked T-Rex, one-time Triceratops test unlock, visual switching, Reset Character persistence and full reconnect persistence all worked. BD-012 is Done.

### BD-013 — earned chest queue
**Done when:** server timestamps, offline elapsed time, duplicate claims and capacity/overflow policy pass. Chest loot remains independent from immediate run loot.

Build 009 passed all eight runtime checks. The five-slot active queue, two-item overflow case, absolute offline timestamps, claim persistence, duplicate-claim protection and duplicate test-grant protection all worked. BD-013 is Done.

### BD-014 — Gold mutation
**Done when:** atomic 50-copy conversion handles 49/50/51 copies, duplicate requests and equipped-copy semantics without negative counts.

Build 010 passed all eight runtime checks. The 49-copy rejection, exact 50 and 51 conversions, duplicate mutation replay, equipped Gold-only semantics, Gold visual and reconnect persistence all worked. BD-014 is Done.

### BD-015 — core UI
**Done when:** lobby, HUD, run summary, collection and chest queue are usable on desktop/touch and large duplicate stacks render as grouped counts rather than hundreds of cards.

Build 011 passed all eight checks. Tutorial, compact HUD, grouped collection rows, chest UI, Home, run summary and phone-landscape emulator layout/actions all worked, with development grant/setup controls absent. BD-015 is Done.

### BD-016 — dinosaur/map kit
**Done when:** three distinct original dinosaurs, one arena and Gold treatment pass collision/camera/permission checks. Procedural fallback is acceptable for the private test.

Build 013 integrates the original procedural Compy, Triceratops, T-Rex, Gold treatment and meadow/nest environment kit. All decorative props are non-colliding and no external asset permissions are required. See `docs/24-visual-kit-test.md`.

### BD-017 — audio
**Done when:** minimal effects work for a non-owner published tester with independent mute/volume behavior. Ambience is optional.

### BD-018 — multiplayer/security/persistence suite
Execute the verification matrix from `docs/06-roadmap-and-testing.md`. Source inspection is not runtime evidence.

Build 012 passed all eight runtime checks. Malformed/flooded remotes, impossible movement correction, normal gameplay after attacks, two-client isolation, equal-size safety, one predation outcome, end-run-vs-predation terminal race and post-restart inventory persistence all passed. BD-018 is Done.

### BD-019 — device/load/published assets
Requires a real target phone plus the agreed multiplayer/pickup load test and non-owner asset checks.

### BD-020 — private release/rollback
Requires a known-good commit/build, private access settings, no public debug grants, known issues and a tested rollback.

### BD-021 — observed community test
Run the small invited session only after BD-020. Capture friction, repeat-run behavior and defects separately from suggestions.

### BD-022 — public-alpha decision
Public scope is an evidence-based later decision. Passing code generation alone never triggers launch.

## Session log
- 2026-09-18: Znypr reported Build 012 tests 1–8 passing; per-run Growth/Size/Catches correctly reset while persistent inventory remained. BD-018 moved to Done. BD-007 asset specification completed and Build 013 visual kit prepared for BD-016 testing.
- 2026-09-18: Znypr reported all Build 011 core UI tests passing, including phone-landscape emulator interaction. BD-015 moved to Done. Build 012 security/multiplayer regression prepared for BD-018.
- 2026-09-18: Znypr reported all Build 010 Gold mutation tests passing. BD-014 moved to Done. Build 011 core UI prepared for desktop and phone-landscape emulator verification.
- 2026-09-18: Znypr reported all Build 009 chest queue tests passing. BD-013 moved to Done. Build 010 Gold mutation prepared for BD-014 runtime verification.
- 2026-09-18: Znypr reported all Build 008 collection/equip tests passing. BD-012 moved to Done. Build 009 chest queue implemented for BD-013 runtime verification.
- 2026-09-18: Znypr reported Build 007 checks passing in a new private test experience: Profile Loaded, fresh starter state, lease test PASS, reward gain, full restart and persisted copy count. BD-011 moved to Done. Build 008 collection/equip prepared for runtime verification.
- 2026-09-17: Build 007 prepared for final BD-011 runtime verification. Added a temporary DataStore lease/stale-writer probe and HUD `Lease test` status. Final Build 007 CI passed and generated the test artifact.
- 2026-09-17: Znypr reported Build 006 tests 1–10 passing. Rejoin persistence, duplicate settlement, Reset Character settlement, anti-farm behavior and fail-closed API/DataStore behavior passed. Compy copies were confirmed to continue above 3. BD-011 moved to Review / test pending the competing-session/stale-lease case.
- 2026-09-17: Znypr reported Build 005 tests 1–9 all passing. BD-009 moved to Done for desktop multiplayer.
- 2026-09-17: BD-010 economy simulation completed. Six deterministic tests pass across catch scores 0–5000. Private-test thresholds and chest grants are recorded in `docs/15-economy-simulation.md`; 50-copy Gold is flagged as intentionally fast test pacing.
- 2026-09-17: Build 005 prepared. BD-005 specification completed. Added `RunLifecycle` and `PredationService`, one no-payload/rate-limited `RequestEndRun` remote, spawn protection, score-gated PvP, deterministic victim claim, temporary catch score, manual exit channel and a shared terminal guard. Generated build packages 8 scripts.
- 2026-09-17: Znypr reported all Build 004 food/growth checklist cases working. BD-008 moved to Done.
- 2026-09-17: Znypr reported all v003 desktop single-player checks and four two-client checks passed. Mobile remains untested, so BD-006 remains `Review / test`.
- 2026-09-17: Build 003 fixed the character-parenting race after earlier dinosaur/pad failures.
- 2026-09-17: Build 002 removed the protected Workspace startup assignment after Build 001 failed at server startup.
- 2026-09-17: Initial source/build bootstrap, planning, direction and reward relationship were established.

## Deferred objectives
Paid products/gems, trading, auto-farm, daily/group rewards, global leaderboards, extra maps, more mutations, advanced combat, console certification and realistic art. Reassess after BD-021.

## Redesign request, 2026-10-04
BD-023 (Review / test): startup/collision/food fixes and resource-based visual redesign. User feedback supersedes acceptance of the procedural fallback as finished art. Build 013 is the repository baseline; screenshot shows newer local work. See docs/25-redesign.md.

- 2026-10-04: Build 014 source fixes, shared dimensional UI, mesh-aware rendering and resources prepared. Automated checks recorded in docs/26-redesign-test.md; Studio import/runtime remains pending. BD-023 moved to Review / test, not Done.

- 2026-10-04: Build 015 incorporates the user-selected mountainous island direction, jumping, +50 crystal/+15 egg food, large terrain and complete inspectable 2D exports. Client-local mesh/icon generation added with explicit permission-aware fallback. Source/numeric checks pass; Studio verification pending. BD-023 remains Review / test. See docs/27-mountain-island.md.
