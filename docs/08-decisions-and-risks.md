# Decisions, open questions and risks
Updated 2026-09-17.

## Decisions
| ID | State | Decision | Rationale |
|---|---|---|---|
| D01 | Chosen for this setup | GitHub is planning/code source of truth | Faster versioning and review; no duplicated Drive tracker |
| D02 | Approved by Znypr | Private community test first | Learn before public release |
| D03 | Approved by Znypr | Cute simple ground arena | Lower animation/map scope |
| D04 | Approved by Znypr | Small complete collection loop, no paid shop | Three dinos, earned rewards, egg queue, one mutation |
| D05 | Proposed | Luau + Rojo, one place | Simple AI-editable source workflow |
| D06 | Proposed | Immediate collection rewards plus bonus eggs | Needs confirmation of intended reward relationship |
| D07 | Proposed | 60-second private-test egg timer | Exercise whole loop during showcase |
| D08 | Proposed | 10% PvP score margin and exit channel | Reduce ambiguous collisions/instant escape |
| D09 | Proposed | Three species and equal initial speeds | Variety without major veteran speed advantage |

## Questions needed before affected implementation
1. Who owns the Roblox experience: Znypr personally or an existing group? Is Studio installed and can you perform import/publish and device test steps?
2. What is the target date for the private test, and the total asset/tool budget? No paid purchases are assumed.
3. Should run dinosaurs be awarded immediately with eggs as bonus, or should all collection rewards wait for eggs? Reference behavior is not fully established.
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
