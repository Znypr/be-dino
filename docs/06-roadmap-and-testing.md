# Roadmap and release gates
Estimates are effort ranges for planning, not a delivery promise. Studio is installed on Znypr's account; budget is €0. Implementation has not started. Estimates depend on integration and feedback availability.

| Phase | Indicative effort | Outcome | Exit gate |
|---|---|---|---|
| 0: Decisions and setup | 0.5-1 working day | Private test place, reproducible source workflow | One client runs the synced build; ownership/data isolation recorded |
| 1: Core arena | 1-2 days | One dino, food, growth, PvP, run restart | Two real clients finish multiple runs without conflicting outcomes |
| 2: Persistent loop | 1.5-3 days | Three dinos, stacked immediate rewards, separate chest loot/queue, Gold | Reconnect and duplicate-request tests pass |
| 3: Presentation and hardening | 1-2 days | Original art/UI/audio and touch support | Device/performance/security gates pass |
| 4: Invited community test | 0.5-1 day plus fixes | Small observed play session | Findings triaged, severe defects fixed before widening access |

Approximate total: 4.5-9 working days of effort, with material uncertainty around movement, saving and asset import. AI speeds implementation but does not remove live testing and moderation delays.
Do not announce a launch date until Phase 1 passes. If behind, cut polish, leaderboard, audio ambience and extra species detail before cutting persistence/security tests.

## Critical path
Ownership/toolchain -> controller spike -> food/growth/PvP -> run settlement -> persistence/rewards -> collection/eggs/mutation -> live test.
Asset and UI preparation can proceed alongside stable interfaces, but do not block the controller on polished art.

## Verification matrix
| Area | Required scenario | Pass evidence |
|---|---|---|
| Movement | Ground, obstacle edges, min/max size, touch camera | Recorded device/build; no stuck or unusable states |
| Food | Two players claim same pickup; distant/flooded claim | Exactly one grant; invalid requests rejected |
| PvP | Equal score, protected spawn, simultaneous predation | Rule consistent; each victim ends once |
| Run settlement | End-run/death/disconnect race; duplicate requests | One immutable result and grant |
| Saving | Load failure, retry, rejoin, competing session, stale write | No default overwrite; committed inventory preserved |
| Egg queue | Before/after readyAt, offline time, two claims, full queue | Correct readiness and exactly-once reward |
| Mutation | 49/50/51 copies, double click, equipped species | Valid deduction/output; no negative counts |
| Security | Invalid IDs/types/NaN, remote flood, impossible movement | Rejected without state corruption or expensive work |
| UI | Phone landscape, narrow viewport, empty/error/loading states | All core actions reachable and legible |
| Load | Agreed device, 8 players, 300 pickups, 20 minutes | Logged frame/memory behavior meets agreed budget |
| Release | Published private place, asset permissions, rollback | Assets load for non-owner; known-good build recoverable |

Use Studio's client/server and multiplayer testing, then actual clients/devices: [official testing documentation](https://create.roblox.com/docs/studio/testing-modes).
Pure-function checks cover reward math and rules; they cannot prove networking, animation or persistence behavior.

## First test protocol
Invite a proposed 5-8 people after the 2-client gate. Znypr owns invitations; this plan does not send any.
Give one instruction and observe 10-20 minutes. Record where players get stuck, early deaths, whether they notice growth, whether they claim/equip, and whether they choose another run.
Ask: 'What did you think you were trying to do?', 'What felt unfair?', 'What would make you play again?'
Do not infer broad retention from a friendly creator-community sample.
Log defects separately from suggestions. P0 data loss/duplication/security or inability to play blocks the test; P1 core failures block expansion; cosmetic issues may remain.

## Release checklist
- Required tasks accepted; known issues documented.
- Test and production data isolated; no debug grants in public.
- Experience owner, access settings, supported devices and content metadata reviewed in Roblox.
- Published build matches recorded commit; asset permissions verified by a non-owner.
- Save/error telemetry accessible; rollback procedure tested.
- Public launch is a later decision after private results, not automatic upon code completion.

## Current execution order
1. BD-004: establish source/build workflow and private test place. Codex prepares source and instructions; Znypr performs unavailable Studio/account actions.
2. BD-005 and BD-006: review data contracts, then prove one dinosaur moves correctly with two clients. Use placeholder art.
3. BD-010: simulate catch-score quantity, exponential tier allocation, duplicate stacks and 50-copy mutation pacing before integrating rewards.
4. BD-008–014: complete food, PvP, durable immediate rewards, collection, independent chests and mutation.
5. BD-015–020: finish usable UI and original assets, test failure cases and devices, then prepare the private release.
6. BD-021: observe the community test. Expand species and rarity breadth only after this loop works.

## Additional reward gates
Verify increasing total quantities across catch scores, tier-boundary behavior, grouped species quantities, large-reward rendering and independent chest outcomes. Test hundreds/thousands of awarded copies without spawning hundreds/thousands of UI cards.
The 50-copy mutation threshold and high duplicate quantities may accelerate progression sharply; BD-010 must measure this before rewards are accepted.

## Scheduling and ownership
No firm launch date is set. ASAP means the earliest build that passes the stated gates, not skipping saving or multiplayer verification. No paid service is on the critical path.
The next reviewable deliverable is a reproducible placeholder build, not a polished catalog. A native GitHub Projects board is not configured; the linked Markdown Kanban is the current task board.
