# Project brief and responsibilities
Draft v0.2 • 2026-09-17

## Objective
Build a small, reliable Roblox game that Znypr can play with an invited community group, learn from, and later launch publicly. Players become dinosaurs, collect food, grow, avoid larger players, and turn runs into persistent dinosaur collection progress.

## Agreed direction
Znypr selected a private community test, cute/simple ground arena, and a small complete loop: three dinosaurs, earned rewards, one egg queue, one mutation tier, no paid shop.
This establishes direction, not approval of every tuning value below.

## Success criteria for the first test
- A new player can start a run, collect food and understand who can eat whom without live coaching.
- Two or more actual clients can eat, be eaten, settle rewards, equip an unlocked dinosaur and start again.
- An earned egg can be queued and claimed; a mutation can be demonstrated using isolated test data.
- Saved inventory and queue survive rejoining; duplicate claims do not grant twice.
- The test completes without a blocker, confirmed item duplication, or confirmed permanent progress loss.
- Record time to first food, first run completion, next-run start, death cause, errors and device performance. These are diagnostic observations, not claimed retention results.

## Scope boundary
Include one small arena and safe lobby in one place; desktop and touch controls; simple camera; three species; food and growth; score-based contact eating; run summary; inventory/equip; earned egg queue; one mutation tier; saving; basic sound and feedback.
Defer paid products, gems, trading, auto-farm, daily rewards, global leaderboards, multiple maps, elaborate abilities, realistic rigs and additional mutation tiers.
A session leaderboard is optional after the core loop works. Console is deferred unless Znypr requests it.

## Roles
These are accountability and review perspectives performed by Codex unless a human dependency is explicit. Role labels are not claims of independent personnel or independent verification.

| Role | Responsibility | Deliverable / authority |
|---|---|---|
| Product Owner (PO, Codex) | Translate goals into small tasks, prioritize and prevent scope creep | Acceptance criteria, current board, proposed tradeoffs |
| Creative owner / publisher (Znypr) | Decide audience experience, budget and release timing | Approves look/feel, owns Roblox account/group, conducts community test |
| Game Designer (GD, Codex) | Rules, progression, fairness and first-session flow | Configurable tuning and balance rationale |
| Senior Game Architect (ARCH, Codex) | Boundaries, data lifecycle, dependency choices | Lightweight architecture and threat review |
| Experienced Game Developer (DEV, Codex) | Luau implementation and integration | Small reviewable commits and reproducible build |
| Technical Artist / UI Designer (ART, Codex + Studio operator) | Coherent models, animation, UI and import pipeline | Approved asset manifest and playable visuals |
| Audio Designer (AUDIO, Codex + Studio operator) | Source/create and integrate effects | Permission-tested sound set |
| QA Engineer (QA, Codex + Znypr for live devices) | Adversarial tests and evidence | Test results with device/build; blocks release on severe defects |
| Release Engineer (REL, Codex + Znypr) | Build, test environment, publishing and rollback | Release checklist, known-good version, change notes |

## AI execution contract
PO defines acceptance; ARCH reviews risky state/security work; DEV implements; QA checks against requirements and failure cases.
Use a separate review pass, but describe it honestly as self-review unless another reviewer actually participated.
AI writes code, procedural asset generators, configuration, tests and documentation. Znypr supplies account-level actions and real Studio/device feedback when those capabilities are unavailable here.
Never label Studio, multiplayer or device tests passed based on code inspection alone.
At each work session: read board and decisions, select one Ready task, move to In progress, implement, review/test, record evidence, update status and next action.
Limit implementation work in progress to one task initially. Avoid a framework or automation platform larger than this game.

## Confirmed setup and reward updates
Znypr owns the Roblox account and has Studio installed. Target spend is €0; paid tools, assets, contractors and advertising are outside this plan. Studio installation does not establish remote Studio control from Codex.
Immediate run dinosaur rewards and separate chest loot are confirmed. Copies stack by species/mutation, with exponentially declining quantities across rarity tiers. Catch score remains separate from growth score.
Three species is a validation slice, not the final collection size. Support a larger catalog in data definitions without making dozens of finished models a first-test dependency.
