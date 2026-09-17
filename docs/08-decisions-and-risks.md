# Decisions, open questions and risks
Updated 2026-09-17.

## Decisions
| ID | State | Decision | Rationale |
|---|---|---|---|
| D01 | Chosen for this setup | GitHub is planning/code source of truth | Faster versioning and review; no duplicated Drive tracker |
| D02 | Approved by Znypr | Private community test first | Learn before public release |
| D03 | Approved by Znypr | Cute simple ground arena | Lower animation/map scope |
| D04 | Approved by Znypr | Small complete collection loop, no paid shop | Three dinos, earned rewards, egg queue, one mutation |
| D05 | Implemented bootstrap; Rojo pending | Luau + dependency-free Python packager, one local place file | Direct Studio opening now; optional Rojo live-sync later |
| D06 | Approved by Znypr | Immediate run dinosaurs plus separate chest loot | Death/manual exit pays run loot immediately; chests are additional |
| D07 | Proposed | 60-second private-test egg timer | Exercise whole loop during showcase |
| D08 | Proposed | 10% PvP score margin and exit channel | Reduce ambiguous collisions/instant escape |
| D09 | Proposed | Three species and equal initial speeds | Variety without major veteran speed advantage |

| D10 | Approved by Znypr | €0 budget; personal account; Studio installed | Use free tools and original procedural assets |
| D11 | Approved by Znypr | More catch score gives more copies; rarer tiers receive fewer copies; duplicates stack | Large-catalog examples are directional, not fixed tuning |
| D12 | Proposed | Three-species test before catalog expansion | Prove mechanics before content production |

## Remaining questions and resolved setup
1. Setup resolved: Znypr's account; Studio installed. Still record the actual test experience/place IDs and verify a build can run.
2. Budget resolved: €0. Target is ASAP; calendar test date remains unset and does not block the prototype.
3. Reward relationship resolved: immediate dinosaur copies plus separate chest loot. Higher catch scores mean more total copies; quantities decrease exponentially across higher rarity tiers; repeated species stack.
4. Is a 60-second egg timer acceptable for the private test, and should test progress later reset? Keep production data separate regardless.
5. Do you accept a 10% eating margin and short vulnerable exit channel, or want strict higher-score contact eating and instant manual exit?
6. What phone should we use as the minimum real-device target? Are controller/console controls necessary now?
7. Does upgrading consume all 50 copies, and may it consume the last base copy currently equipped?

## Risks and responses
| Risk | Severity | Response / owner |
|---|---|---|
| Ground movement/large models snag | High | Early one-dino spike, capped visuals, simple terrain / ARCH+DEV |
| Progress duplicates or disappears | Critical | Idempotent operations, session ownership, failure tests / ARCH+QA |
| Rare-stat snowball makes new players helpless | High | Small capped advantages, safe spawn and playtest / GD |
| Too much content delays first play | High | Three species and one mutation; explicit deferred list / PO |
| AI models look good but fail to rig/import | Medium | Procedural fallback and timeboxed spike / ART |
| Timer hides collection during test | Medium | Fast isolated test config / GD |
| Account/Studio actions unavailable to Codex | High | Small documented human handoffs / REL+Znypr |
| Public repo exposes private test information | Medium | Store aggregate findings; no tester personal data or credentials / PO |
| Source observations mistaken for rules | Medium | Evidence labels and short targeted gameplay capture / GD |

## Change discipline
A new feature must identify which launch task it replaces or why it does not extend the critical path.
Update this log when an owner answers; propagate to design and acceptance criteria.
Keep proposed balancing reversible in config. Keep durable data contracts deliberate.

## Reversible working defaults to avoid blocking early development
Use separate disposable test data, 60-second test chest timers, the existing proposed 10% eating margin and 3-second exit channel only as configurable prototypes. These are not owner-approved final rules. Preserve one usable equipped copy when proposing mutation behavior; resolve exact consume/equip semantics before BD-014 acceptance. Desktop plus touch remain targets; name and test a real phone before release.
Do not assume a strict reward cap is compatible with 'higher catch always means more loot': define a supported catch-score range and a run-ending limit instead of silently flattening rewards.

## Movement prototype status
Generated build and quickstart are committed. No test experience/place IDs exist in project records yet. Znypr must open the build locally and perform the first Studio checks; no remote Studio-control capability is available here. No data stores are used, so this build cannot write production progression. Size stations are prototype-only and must not ship as public progression controls.
