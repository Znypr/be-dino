# Kanban and task specifications
Updated 2026-10-14. This file is the canonical task tracker.

**Current scope: GitHub main Build 020.** Use [the documentation authority guide](00-documentation-guide.md) to distinguish owner targets, committed source, historical build evidence and Studio/release acceptance. [Build 020 integration checklist](44-main-integration-checklist.md) records bounded passes and remaining gates, but **this file alone owns task statuses**. GitHub integration does not publish Roblox or certify paid items, physical-device performance or newest persistent migration.

**Historical milestone summary:** Builds 005â€“013 established PvP, storage, collection, old direct-copy reward tests, earned chests, Gold and original procedural visuals. Those older checks are *not* proof the latest reward vision is implemented. For actual per-build acceptance consult the dated sections and historical evidence below. Physical-phone/mobile acceptance remains open, though earlier phone-emulator checks passed.

## Board

2026-10-08 multiplayer retry: disposable Build 019 Studio tests with 2 and 5
clients passed profile/character loading, reward isolation, duplicate settlement,
locked equip and memory reload. Znyprr joined and reconnected to published Build
019; six collection previews were visible. Real multi-device play, earned-reward
DataStore persistence, mobile/load and latest-asset release tests remain pending.
Evidence and limits: [multiplayer results](42-live-multiplayer-test.md).
Maximum player access/policy work remains in progress:
[paid-random access plan](43-player-access-and-paid-random-policy.md).

| Backlog | Ready | In progress | Review / test | Blocked | Done |
|---|---|---|---|---|---|
| BD-017; BD-021â€“022; BD-035; **BD-044â€“056, BD-058â€“059, BD-061â€“065** | BD-027 | BD-043; BD-019 device/load (owner publish pending) | BD-006 mobile; BD-016 visual kit; BD-020 release/rollback (owner publish pending); BD-023â€“026; BD-028â€“034; BD-036â€“042; **BD-057 Phase 1; BD-060** | BD-004 private-place record (IDs pending) | BD-001, BD-002, BD-003, BD-005, BD-007, BD-008, BD-009, BD-010, BD-011, BD-012, BD-013, BD-014, BD-015, BD-018 |

Backlog means dependencies are not yet satisfied. `Review / test` means code exists but acceptance evidence is still required. `Done` requires a recorded artifact, decision or live test result. Keep at most one implementation task active at a time.

### Studio check of merged main â€” 2026-10-13

Unpublished copy of `main` (`9a9b1ee`, GameId/PlaceId 0), Studio Play, one player. Floor food built
(1,536 pickups, status Ready); a run started; 3 of 3 pickups eaten with growth 0 â†’ 7; an eaten pickup
respawned after the 8 s configured delay; the Home request returned the dino to the Sanctuary.
BD-027 stays Review / test pending phone and multi-client evidence. With the fusion flag on in that
copy only, the real `FusionAction` remote answered over a real client connection: list, details,
`wrong_donor_count`, `bad_request` for unknown actions and extra fields, and Emerald refusal.
Not yet checked: Fusion Menu on screen, 1 s reveal and rarity-skip UI, Android layout, hill traction,
world-art mode, a real 10-donor fusion through the game's own repository instance.

### Milestone 1 owner decisions â€” 2026-10-13

Znypr set the first milestone and handed project lead to Claude:
- **Milestone 1 = private playtest including fusion** (10 â†’ Gold with odds, Fusion Menu,
  persistent identities). Public launch is a later, evidence-based decision (BD-022).
- **BD-044: exactly one dinosaur per successfully hatched egg**; the 1â€“3 copy split is retired
  for new eggs. Failed Cracked eggs still yield nothing.
- **Unapproved numbers** (run crystals, bonus nests, fusion trait odds, caps) may use
  provisional defaults, kept in config and labelled `PROVISIONAL` for later tuning.
- **Playtest place:** a new private experience with a fresh, empty DataStore (IDs pending
  from Znypr; closes BD-004 when recorded). No legacy save migration is needed there.
- **All Robux / paid-random features stay off** for the playtest.
- **Devices:** desktop plus one Android phone; iOS and tablet are untested.

Parallel workstreams (one branch and PR each): BD-044/045 reward loop; BD-052/053/054
movement and mobile; BD-064 fusion server, odds and persistence; BD-062/065 Fusion Menu
and Dino Details. Studio/Blender verification is run centrally.

### BD-060 foundation â€” updated 2026-10-13

Implemented on `codex/bd-060-dinosaur-identity` from latest main `ad5245c`;
**Review / test, not Done**. [Implementation and verification](47-dinosaur-identity-foundation.md).
Offline identity/transaction tests cover migration, 1/2/3-copy hatches, identical
instances, duplicate claims, reconnects, original eggs, cosmetic isolation and a
150-egg batch. Unpublished Studio acceptance passed 17 created identities, duplicate
claims, multi-copy hatches, failed hatches and memory reconnect. A separate private
test experience passed isolated DataStore write/full-Play-restart/read for 53 migrated
copies plus a three-copy egg; no configured profile store or player key was used.
Roblox JSON sizing measured 468,320 / 938,806 / 4,722,389 / 9,472,285 bytes at
500 / 1,000 / 5,000 / 10,000 identities. The fail-closed ceiling is now 3,000;
large-profile compaction/sharding, final migration rollout/rollback approval and
competing-session verification remain open. `fusionRecord()` is explicitly rejected
by reconciliation until BD-057 adds the atomic identity-aware inventory transaction.
Persistent rollout remains disabled; no real profiles were accessed or migrated.
Actual fusion RNG and per-instance shop/selector integration remain separate tasks.
**2026-10-13 (BD-064 branch):** a default-off `IdentityPersistentEnabled` flag now runs
the sidecar, hatch credit and reconcile inside the same persistent `UpdateAsync`
transform for the Milestone 1 private playtest (fresh DataStore), with a whole-profile
byte preflight and fail-closed suspension for legacy/over-capacity profiles
([53](53-bd064-fusion-server.md)). Offline-tested only; Studio/DataStore pending.

### BD-057 Phase 1 â€” updated 2026-10-13

**2026-10-15 ladder v2 (owner, replaces 15/4/2 which became unreachable at 4 eggs per run):** Gold = 6 Base of one species (any pattern, plurality pattern kept), Emerald = 3 Gold, Diamond = 2 Emerald (same species + pattern) ([90](90-fusion-ladder-v2.md)); Studio verification pending. History: 15/4/2 of 2026-10-14 ([58](58-fusion-ladder-50-10-3.md)).

Implemented on `claude/be-dino-development` from `50116b8`; **Review / test, not Done**.
[Implementation and verification](49-identity-fusion-phase1.md). A disabled,
memory-only transaction fuses 10 same-species/same-pattern Base identities into one
NEW Gold with a server ID, consent-gated loss manifest, durable ledger, parent egg
lineage, idempotent replay and full rollback. Offline harnesses (`verify_fusion.py`,
repository section of `verify_progression.py`) pass, and an unpublished Studio
memory-profile check passed 20/20 with Roblox `JSONEncode` matching the byte estimate.
**No published-place, DataStore or production verification was performed.** Trait odds (BD-064), Emerald/Diamond costs,
UI/remote (BD-065) and persistent rollout remain open. Consent for Shiny/BIG/mutation
donors and the hard lock/favorite block are working defaults awaiting owner approval.
**2026-10-13:** BD-064 adds the PROVISIONAL production roller, the `FusionAction`
remote and a persistent-playtest flag on top of this transaction (below).

### BD-064 server â€” updated 2026-10-13

**2026-10-13 ladder:** odds normalize by actual donor count N; remote accepts up to 15 donors (was 50; [58](58-fusion-ladder-50-10-3.md)).

Implemented on `claude/bd-064-fusion-server` from main `18856b4`; **Review / test, not Done**.
[Implementation and evidence](53-bd064-fusion-server.md); [remote contract](52-fusion-remote-contract.md)
for the BD-065 UI. `FusionOdds` `fusion-odds-provisional-v1` (PROVISIONAL: Shiny/BIG
`0.5 Ã— donors/10`, mutation `0.5 Ã— mutated/10` split by donor counts, condition and
colors proportional to donors, blend uniform 1â€“99 or 100, pattern locked) exposes the
exact quote distribution and a consistent roll; `FusionAction` RemoteFunction
(`list/details/quote/fuse`) validates every argument, rate-limits per player and never
accepts client traits; `IdentityPersistentEnabled` enables identities + fusion on
persistent profiles for the Milestone 1 private playtest (fresh DataStore, Robux off).
Offline evidence: normalization, 200,000-sample parity, determinism, persistent
fresh/hatch/fuse/reload/outage/lease loss/byte preflight/legacy login, remote fuzzing
and rate limit. Both flags are false in committed source. **Pending:** Studio and
private-place DataStore acceptance, owner sign-off on PROVISIONAL coefficients/budgets,
ledger compaction before public release.

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
| BD-004 | Blocked | P0 | Bootstrap reproducible project and private test place (Milestone 1 playtest IDs pending from owner) | BD-003 |
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
| BD-018 | Done | P0 | Run multiplayer, security and persistence suite | BD-011â€“015 |
| BD-019 | In progress | P0 | Run device/load and published-asset checks (offline load harness done; owner publish pending) | BD-015â€“017 |
| BD-020 | Review / test | P0 | Prepare private test release and rollback (tooling + runbook ready; owner publish pending) | BD-018, BD-019 |
| BD-021 | Backlog | P0 | Observe community test and triage | BD-020 |
| BD-022 | Backlog | P1 | Decide public alpha scope after test | BD-021 |

| BD-023 | Review / test | P1 | Fix cropped popups and responsive margins | Build 017 |
| BD-024 | Review / test | P1 | Restore visible egg previews | Build 017 |
| BD-025 | Review / test | P1 | Enlarge centered dinosaur previews | Build 017 |
| BD-026 | Review / test | P1 | Replace pixelated UI icon rendering everywhere | Build 017 |
| BD-027 | Review / test | P0 | Verify visible floor food and close Build 017 regressions | BD-023â€“026 |
| BD-028 | Review / test | P1 | Persistent crystal currency and random map pickups | BD-027, BD-011 |
| BD-029 | Review / test | P1 | Aura shop, ownership/equip and eating-growth effects | BD-028 |
| BD-030 | Review / test | P1 | Forward leap with 60-second cooldown and HUD | BD-027, BD-006 |
| BD-031 | Review / test | P1 | Random weather, rarity bonuses and bottom-right timers | BD-027 |
| BD-032 | Review / test | P1 | Crystal potion shop, timed buffs and inventory | BD-028, BD-031 |
| BD-033 | Review / test | P1 | Matching aura, potion, leap, weather and currency icons | BD-026 |
| BD-034 | Review / test | P1 | Event-mutated eggs, cosmetic trails and textured visual upgrade | BD-028, BD-031 |
| BD-035 | Backlog | P1 | High-quality modular Blender egg/pattern/condition/mutation render passes | BD-024, BD-034 |
| BD-036 | Review / test | P1 | Run-end crystal rewards, crystal unboxing and Robux crystal packs | BD-028, BD-011 |
| BD-037 | Review / test | P1 | Crystal-priced random eggs feeding the existing hatching queue | BD-036, BD-013 |
| BD-038 | Review / test | P1 | Persistent account levels and ten level-gated speed/VFX trails | BD-028, BD-029, BD-034 |
| BD-039 | Review / test | P1 | Crystal-priced five-minute Speed Potion integration | BD-032, BD-036 |
| BD-040 | Review / test | P1 | Escalating Condition Shop, weighted egg conditions and stat/hatch effects | BD-036, BD-037 |
| BD-041 | Review / test | P1 | Two-colour egg genetics, Normal/Big eggs and independent shiny sparkle | BD-035, BD-037 |
| BD-042 | Review / test | P1 | Five-second ordered hatches, Shiny/BIG and map leaderboards | BD-013, BD-034 |
| BD-043 | In progress | P1 | UI animation, feedback, loading and preview performance | BD-015, BD-042 | Polish pass (SFX hooks, goal line, reveal juice): [62](62-polish-sfx-goal-juice.md).
| BD-044 | Review / test | P0 | Replace direct-copy rewards with caught-run-egg hatching, crystal payout and separate five-slot egg nests ([evidence](50-bd044-reward-loop.md); Studio pending). **Owner 2026-10-13: 40 eggs per 500 food (was 15); values/evidence: [59](59-egg-rate-40.md)** **2026-10-14: five species tiers Common/Uncommon/Rare/Epic/Legendary, run-size boost to 400 eggs, saved-value migration ([82](82-species-rarity-tiers.md)); Studio pending.** | BD-011, BD-013, BD-036, BD-042 |
| BD-045 | Review / test | P0 | Rebalance condition odds to new owner starting distribution and update condition-upgrade/disclosure flow ([evidence](50-bd044-reward-loop.md#bd-045-condition-odds-bd045-conditions-v1); Studio pending) | BD-040 |
| BD-046 | Backlog | P1 | Rename Auras nav entry to Shop with crystal icon; crystal HUD opens same Shop | BD-029, BD-036, BD-043 |
| BD-047 | Backlog | P1 | Illustrated Crystal Shop category tiles, green-spotted egg icon, larger aura previews and leading tab icons | BD-046 |
| BD-048 | Backlog | P1 | Trail icon art, Blender world VFX and six rarity categories across ten trails | BD-038, BD-034 |
| BD-049 | Review / test | P1 | Blender trees, vegetation, rock variants, map landmarks and optimized biome placement; kit + flagged grammar in [56](56-bd049-050-world-art.md), Studio/Android pending | BD-016 |
| BD-050 | Review / test | P1 | Blender pickup/food model variants with intact food rewards and server validation; kit in [56](56-bd049-050-world-art.md), berry/fruit need MeshPart upload | BD-008 |
| BD-051 | Review / test | P1 | Rotating Potion Shop offers every **2 minutes** (owner 2026-10-14; was five), rarity-weighted selection and 1â€“3 limited per-player stock ([60](60-bd051-potion-rotation.md); Studio/phone pending) | BD-032, BD-039 |
| BD-052 | Review / test | P1 | Single bottom-center Home with confirmation and no three-second exit channel ([51](51-bd053-054-movement-mobile.md)) | BD-009 |
| BD-053 | Review / test | P0 | Fix sliding and hill-climb movement on mountainous terrain ([51](51-bd053-054-movement-mobile.md)) | BD-006, BD-008 |
| BD-054 | Review / test | P0 | Responsive phone/tablet touch-zone navigation/control placement and safe insets ([51](51-bd053-054-movement-mobile.md)) | BD-052, BD-046 |
| BD-055 | Backlog | P1 | Complete sky, atmosphere, cloud, particle and audio effects for all weather events | BD-031, BD-034 |
| BD-056 | Backlog | P1 | Top-center growth metric and bottom-left egg-icon catches-only HUD | BD-044, BD-054 |
| BD-057 | Review / test | P0 | [Emerald/Diamond cost options: 57](57-fusion-ladder-options.md). Consume 10 same-species/same-pattern Base dinos to create ONE NEW Gold, then Emerald before Diamond; guaranteed stage, freshly rolled traits (Gold transaction; provisional odds/remote via BD-064; Emerald/Diamond unapproved) **Owner 2026-10-14: ladder fixed at Gold 15 Base / Emerald 4 Gold / Diamond 2 Emerald (was 50/10/3); pacing at 40 eggs per 500 food: [57 sections 11-12](57-fusion-ladder-options.md), [59](59-egg-rate-40.md).** | BD-012, BD-060  |
| BD-058 | Backlog | P0 | [Recipe pacing options sim: 57](57-fusion-ladder-options.md). Earned fusion stages as main permanent stat progression, fair caps, weekly grind and recipe pacing simulation **Owner 2026-10-14: ladder fixed at Gold 15 Base / Emerald 4 Gold / Diamond 2 Emerald (was 50/10/3); pacing at 40 eggs per 500 food: [57 sections 11-12](57-fusion-ladder-options.md), [59](59-egg-rate-40.md).** | BD-057  |
| BD-059 | Backlog | P1 | Buy and switch multiple aura/trail styles per individual dino; ALL purchased ingredient cosmetics are lost at fusion, never transfer to result | BD-060, BD-029, BD-038 |
| BD-060 | Review / test | P0 | Unique dinosaur identity, hatched egg records, fused NEW instance lineage/parent egg history, safe profile migration (persistent playtest flag, default off: [53](53-bd064-fusion-server.md)) | BD-011, BD-012, BD-041 |
| BD-061 | Backlog | P1 | Blender Gold/Emerald/Diamond additive surfaces, subtle/medium overlay A/B, stack every trait/effect | BD-057, BD-035 |
| BD-062 | Review / test | P1 | Dino picker/details hatch egg or fused parent lineage, trait/cosmetic badges, hatch rarity vs conditional fusion odds/prestige. Client Dino Details built ([54](54-bd065-fusion-menu.md)); natural hatch odds math, Studio/Android verification pending | BD-059, BD-060, BD-057 |
| BD-063 | Backlog | P1 | Pattern research/duplicate sink: deterministic earned-only progress toward species-pattern fusion donors | BD-057 |
| BD-065 | Review / test | P1 | Dedicated Fusion Menu: species/trait filters, manual 15/4/2-donor selection, odds preview, loss warnings and staged wheel reveals. Client built against the `FusionAction` contract ([54](54-bd065-fusion-menu.md)); offline logic + mock UI smoke pass, Studio/Android verification pending | BD-057, BD-060, BD-064 **2026-10-14 owner ladder: 15/4/2 (was 50/10/3), see [58](58-fusion-ladder-50-10-3.md); Studio pending.** |
| BD-064 | Review / test | P0 | Ingredient-influenced fusion trait RNG (2/10 Shiny â†’ proposed 10%), versioned true odds, paid-random gate and atomic NEW result â€” PROVISIONAL `fusion-odds-provisional-v1` + `FusionAction` remote ([53](53-bd064-fusion-server.md)) | BD-057, BD-060 **2026-10-14 owner ladder: 15/4/2 (was 50/10/3), see [58](58-fusion-ladder-50-10-3.md); Studio pending.** |
| BD-065 | Backlog | P1 | Dedicated Fusion Menu: species/trait filters, manual 15/4/2-donor selection, odds preview, loss warnings and staged wheel reveals | BD-057, BD-060, BD-064 **2026-10-14 owner ladder: 15/4/2 (was 50/10/3), see [58](58-fusion-ladder-50-10-3.md); Studio pending.** |

### BD-044: Owner-approved reward-loop correction (2026-10-08)

**Status: Review / test (2026-10-13). Implemented on `claude/bd-044-reward-loop`; offline Luau evidence only, Studio verification pending. P0 before economy/public release.**

**Implementation 2026-10-13** ([details and evidence](50-bd044-reward-loop.md)): owner decisions of 2026-10-13 applied: one banked run egg per catch (15/150 at 500/5,000 food), exactly one dinosaur per successful egg, no `N(c)=c` copies or threshold eggs; server-side ordered run-egg bank behind the five-slot queue with exactly-once settlement (`settledRuns` + operation log, deterministic egg IDs, precommitted outcomes); PROVISIONAL deterministic run crystals (30/219); separate five bonus-nest slots with visible pending nests and a run-start gate instead of loss; additive schema, old queued eggs still claimable. New `tools/verify_rewards.py` in CI. Still open: Studio/device/multiplayer acceptance, 150-egg pacing UX, Uncommon/Epic taxonomy, balance sign-off. Checklist items below stay unchecked until Studio evidence exists.
The newer owner's reward intent supersedes the 2026-09-17 test economy's `N(c)=c` immediate dinosaur copies and the 10/100/500 catches -> 1/2/3 extra-egg thresholds. [Canonical target and illustrated distributions](09-reward-economy.md) and [AI/contributor instructions](../AGENTS.md) define the intended behavior; [actual Build 020](44-main-integration-checklist.md) is the separate implementation record.

**Acceptance checklist (do not check off from documentation alone):**

- [ ] 500 **food** points -> example 15 catches -> **15 banked eggs** (NOT 15 guaranteed Compy copies + 1/2 threshold eggs). 5,000 **food** points -> example 150 catches -> **150 run eggs**; distinguish from historical 5,000 catch-score cap and test 0/negative/overflow values.
- [ ] Run return/death/disconnect settle each egg exactly once, with immutable random species/rarity/condition/genetic/trait outcomes, saved batches, correct event provenance, Cracked failure and legacy data migration. No direct-copy double credit or preserved duplicate exploit.
- [ ] Hatch every run egg individually in increasing species rarity, at 1 second/egg (owner decision 2026-10-13, was ~5 s in the first prototype). 15-egg and 150-egg cases: clear progress, close/skip/resume, mobile responsiveness, cancellation and performance. Define 150-egg pacing alternative with owner before launch.
- [ ] **Rarity taxonomy migration** (code + offline tests done 2026-10-14, [82](82-species-rarity-tiers.md); Studio/phone pending): current species tiers are only Common/Rare/Legendary; owner examples need Uncommon/Epic as distinct species rarity categories. Design tier mapping, eligible catalog species, data/UI color names, saved rarity ordering, rewards, leaderboards and tests before promising the examples. The sample 15-egg result can be 11 Common/4 Uncommon; the 150-egg result can be 80 Common/50 Uncommon/17 Rare/3 Epic. These **are not mandatory quotas or fixed odds**; eligibility/distribution must be configurable and fair.
- [ ] Grant crystals independently from catches and map pickups; prototype example **30** run crystals at 500 food is assistant illustrative ONLY, **220** at 5,000 food is the owner's illustrative example. Define/approve actual earning and crystal-box rules separately.
- [ ] Model **bonus nests** as separate rewards from individual caught eggs, with **five nest inventory/claim spots**, not the existing ordinary egg queue capacity. Example: 1 nest from 500 food; 6 nests offered from 5,000 food, only 5 claimable if all five slots are free. Explicitly resolve where the sixth offered nest goes (pending/blocked/expiry) and prevent silent reward loss; define nest timing/content.
- [ ] Retune and test quantity (currently 1/2/3 copies per egg), species odds, egg outcomes/disclosure, fusion pacing, 150+ egg batch payloads and reward caps. Old `tools/economy_sim.py`, `tests/test_economy.py`, Config thresholds and Studio fixtures remain **historical tests** until deliberately replaced.
- [ ] End-to-end multiplayer/rejoin/persistence, queue limits, migration, real-device interaction, UI and no paid-random regression verified with evidence before marking done. Do not touch persistent profiles or enable paid random items without a separate release review.

### BD-045â€“BD-056: Owner feedback implementation (2026-10-08)

**Status:** all Backlog/TODO. The **task index above is authoritative** for status, priority, dependencies and ownership. Rather than duplicate every subtask here, use the detailed [categorized owner feedback specification](45-owner-feedback-shop-hud-world-weather-tasks.md) for acceptance checklists, source references and design constraints.

- **BD-045 status (2026-10-13): Review / test.** Tier 0 = 50/30/15/4.5/0.5 as integer weights /10,000 (`bd045-conditions-v1`), PROVISIONAL monotonic tiers 1-6, Cracked 20% hatch success kept, new eggs versioned `bd045-genes-v2`, disclosure (`EggOutcomeOdds`/`ShopOdds`, Condition Shop) normalized and tested offline. Studio verification pending. [Evidence](50-bd044-reward-loop.md#bd-045-condition-odds-bd045-conditions-v1).
- **Economy/shops:** BD-045 conditions (new starting odds **50/30/15/4.5/0.5**), BD-046 Shop entry, BD-047 category cards/icons and aura previews, BD-051 five-minute randomized potion offers.
- **Art/world:** BD-048 ten trail assets and six proposed rarity classes, BD-049 reusable world props and landmarks, BD-050 food models, BD-055 environment-wide weather.
- **Movement/UX:** BD-052 return confirmation, BD-053 terrain/sliding defect, BD-054 mobile/tablet touch placement, BD-056 growth and caught-egg HUD.
- **Update 2026-10-13 â€” BD-052/053/054 are `Review / test`** ([implementation and evidence](51-bd053-054-movement-mobile.md)): root cause of sliding was the low torso collider wedging into slopes (now slope-clearance lifted, guard envelope shares `MaxSlopeAngle`); touch layout moved to `shared/TouchLayout` with safe insets and Roblox thumbstick/jump reserved zones; one bottom-center Home with Return/Cancel settles immediately through idempotent `tryEnd` (provisional predator-nearby refusal). Offline tests only; Studio checks and the owner Android checklist in doc 51 are the remaining gates. BD-054 dependency BD-046 (Shop entry) is not required for this layout pass.
- **Critical interaction:** BD-044 egg-per-catch target is not shipped. Do not label old catches/threshold eggs as equivalent, or unlock paid random items. New **Cracked 50%** selection combined with existing **80% failure on cracked** implies **40% total failed eggs at tier 0**, a high-risk balancing review.
- **Completion gate:** each task requires its own code/assets, Studio/device/runtime acceptance and evidence. Neither planning text nor a similarly named pre-existing Build 020 feature closes it.

### BD-057â€“BD-065: Pattern fusion, permanent dinosaur identity and earned prestige (2026-10-08)

**OWNER TARGET; only the disabled BD-057 Phase 1 transaction foundation exists ([49](49-identity-fusion-phase1.md)); task index above controls status.** Gold consumes **10 same-species + same-egg-pattern dinosaur instances** (example ten Wavy-Stripes Compies) and guarantees **ONE NEW Gold Wavy-Stripes Compy**; it **does NOT preserve the traits of a selected hero**. The new result's colors, condition, Shiny, event mutation and BIG are **rolled from versioned ingredient-dependent probabilities**. Pattern remains fixed by the same-pattern recipe. **Emerald comes after Gold and before Diamond**; higher-stage costs, additional materials and Obsidian/Celestial are proposals. Fusion always grants the guaranteed higher stage/stat improvement, never a random chance to lose all ingredients with nothing.

Each hatched dinosaur keeps **its immutable originating egg record**, but the **NEW fusion output** instead stores **a parent-dino/source-egg lineage** and freshly rolled traits. A living dino can purchase many aura/trail options and switch between them; on fusion **all input dinos and their aura/trail purchases are consumed, with explicit loss confirmation**, and no bought cosmetics transfer to the new result. A dedicated **Fusion Menu** must sort/filter by species, Shiny, mutation, colors, pattern, condition and other traits, display selected ingredients, exact chances and input loss, then reveal each **server-committed trait** via entertaining, skippable wheel animations. **2/10 Shiny ingredients â†’ 10% Shiny on result** is a **proposed formula**, not approved balance. Show true **hatch odds only for hatched dinos** versus **conditional fusion-outcome odds for fused ones**; earned tier is not a random drop %. Bought cosmetics are excluded. Blender Gold/Emerald/Diamond subtle/medium surfaces must preserve **the newly rolled output** DNA and support stacked new effects.

Complete ownership, recipes, safe handling of valuable donors/purchased cosmetics, **ingredient-dependent RNG and transparent wheel reveal (BD-064â€“065)**, deterministic duplicate-sink proposal (BD-063), lineage/migration, earned stats, Blender materials, multi-week balancing and tests are specified **only** in [the advanced fusion specification](46-pattern-fusion-dino-identity-and-cosmetic-progression.md). Roblox [paid-random rules](https://create.roblox.com/docs/production/monetization/paid-random-items) can cover synthesis when ingredients are Robux-linked; trace and restrict eligible inputs and keep paid flags disabled until approved. Build 020's 50/50 fusion remains current code, not new owner goal.

### Crystal Shops and Genetics, 2026-10-08 (BD-036â€“041)

Implemented/private-test acceptance; not release certification. Full record:
[shop/genetics acceptance](39-crystal-shops-and-genetics-acceptance.md),
[screenshots and observations](evidence/2026-10-08-crystal-shops-genetics/README.md).
Only unpublished Build 019 VisualUpgrade / GameId=PlaceId=0 was modified.

- [x] Run-end crystal credit and reveal, atomic settlement and no duplicate grant.
- [x] Earned-crystal 150-price random egg UI, same ordered hatch queue, capacity rollback.
- [x] Persistent catch XP/account levels; ten escalating trail gates, prices, speed and VFX.
- [x] All nine paid trails/six condition tiers purchased with ordinary disposable wallet.
- [x] 20-crystal Speed Common purchase/use, 300-second duration and server expiry rules.
- [x] Five conditions, confirmed 20% Cracked success and .8/1/1.2/1.8 speed/growth.
- [x] Failed/successful Cracked, future-only upgrades, immutable hatch retry/rejoin tests.
- [x] Independent weighted colors/blend; egg-to-dino inheritance, size-only BIG 1.2x.
- [x] Independent Shiny preview/world sparkles; walking Astra ribbons/glitter on phone.
- [x] 38 neutral masters uploaded under verified owner; real reusable IDs, authored PBR
  templates, owner-client loading and native/original-texture fallbacks.
- [x] Desktop/phone shop, queue and colored reveal captures; clean final gameplay console.
- [x] Temporary acceptance fixture removed; Studio stopped/default viewport restored.
- [x] Six real crystal DeveloperProducts created under verified owner, 49-4999 Robux;
  reusable manifest/bindings and Marketplace product lookup verified. No real charge.
- [x] Actual two-client disposable-profile shop isolation, level locks, unauthorized
  grant rejection and duplicate-request single debit; [evidence](evidence/2026-10-08-pending-gates/README.md).
- [x] Premium hatch missing-image native fallback and reveal cleanup in owner client.
- [ ] Creator Hub crystal product images: file chooser/upload tooling blocked.
- [ ] Successful paid receipt delivery and Robux-spending leaderboard integration test.
- [ ] Complete paid-random disclosure/policy review; release flag remains disabled.
  [Reconciled outcome contract](41-egg-outcomes-contract.md) fills provisional
  pattern/palette/migration decisions. Complete in-game outcome enumeration, filtering,
  paging and next-tier links are implemented; [bounded evidence](evidence/2026-10-08-egg-outcome-details/README.md)
  records offline passes and owner-widget captures. Final Studio interaction and
  desktop/phone acceptance remain pending; this is not paid-release approval.
  Five reusable [amber pack PNGs](../resources/monetization/product-icons/README.md)
  are archived with prompts/hashes; Creator Hub upload/moderation remains open.
- [ ] Published private saved-profile restart, broader multiplayer/load, non-owner assets,
  physical phone/load verification, approved economy balance and modular egg art.

### UI motion and responsiveness, 2026-10-08 (BD-043)

**In progress â€” UI-motion history/evidence reconciled into Build 020; latest device checks pending.**
Merge `1799536` preserves newer genes, failure handling, authored previews and four
Shiny glints. The shared theme/loading/preview motion had already been incorporated.
See [main integration evidence](evidence/2026-10-08-main-integration/README.md).
UI owner: this UI-motion chat. Other agents: preserve this work when integrating
crystal shops/genetics; do not replace whole client files with older copies.

- [x] Cancellable shared tween helper; 90ms mouse/touch/controller button feedback.
- [x] Modal scrim/blur/slide transitions, content entry, toast slides, HUD pulses.
- [x] Progress fills, rarity reveal outline/pop, existing egg wobble/fracture/confetti retained.
- [x] Animated crystal counter and gain toast; active navigation indicators.
- [x] Immediate processing/equip feedback; existing server success/error and retry tokens retained.
- [x] Startup stage bar and fade only after character and main UI are ready.
- [x] Cached collection/queue/progression JSON and coalesced panel refreshes.
- [x] Preview camera orbit capped at 30Hz; shiny glints at 20Hz; hidden/disabled
  screens pause visual updates and destruction disconnects callbacks.
- [x] Responsive crystal HUD scaling; existing phone navigation/hatch target sizing retained.
- [x] Local validation: 57 Luau sources compile; six-species preview geometry and
  imported bounding-box framing pass across four aspect ratios.
- [x] UI-only code published in [draft PR #2](https://github.com/Znypr/be-dino/pull/2)
  on `codex/ui-motion-polish`; [implementation/acceptance notes](https://github.com/Znypr/be-dino/blob/codex/ui-motion-polish/docs/38-ui-motion-and-performance.md).
- [x] Owner rejected primitive hatch/cracks; replaced with matched 512px premium blank-egg
  and branching-fracture PNGs, attached shake/squash and 240ms shell split/fade.
  Navigation now uses the same premium shell. Both uploads verified owner 7285577648.
  [Crack screenshot](https://github.com/Znypr/be-dino/blob/codex/ui-motion-polish/docs/evidence/2026-10-08-ui-motion/premium-cracks.png)
  and source/checksum bindings are included in PR #2. Actual UI buy/claim -> 2x Raptor;
  queue empty, new navigation image IsLoaded=true, clean console. Owner art approval
  and non-owner published image access remain pending.
- [x] Hatch v3: three crack-growth stages and timed shakes, still beat before release,
  seven jagged fragments with cap-first rotation/gravity/fade, rarity halo/rays and delayed confetti.
  Five-second total unchanged. Separate hatch sound toggle; loaded free ProSoundEffects
  crunch/chime assets recorded with provenance. Failed Cracked eggs suppress success effects.
- [x] Native fragment coverage/budget harness passes (217 temporary crop strips); 61
  current sources compile; framing checks pass. Reduced-motion and early-close helper probes pass.
  [v3 observations](https://github.com/Znypr/be-dino/blob/codex/ui-motion-polish/docs/evidence/2026-10-08-ui-motion/hatch-v3-observations.json)
  distinguish helper screenshots from real purchase/claim evidence.
- [x] Mesh fetch failures reproduced in owner Studio; static actual-model thumbnail
  fallback prevents blank discoveries. Compy fallback IsLoaded=true and renders after real claim.
- [x] Latest Studio owner mesh verification: typed MeshPart preload applied; all six
  imported species render as 3D models with no thumbnail fallback. Native window
  evidence is required: MCP screen_capture omitted ViewportFrame content.
  See [mesh verification](40-mesh-access-verification.md).
- [ ] Published non-owner mesh permissions and physical-phone frame-time/memory remain open.
  Znyprr now has saved Playtest access (user-authorized, no Edit grant).
  Retry reaches newbuild, but Roblox still disables Play with "This experience
  is currently not available". Resolve remaining availability before mesh testing.
  Owner accepts current hatching effects for now; no further hatch polish requested.
  Integration note: shop/genetics commit `2d3b637` changes mesh preload to typed
  MeshPart instances and proves colored imported hatch models in VisualUpgrade.
  This is not non-owner published asset certification or a retest of Latest Studio.
- [ ] Review/merge PR #2 alongside concurrent shop changes, resolve client overlap and rebuild.
- [x] User selected **BeDino-Latest.rbxlx**, Studio `65d0a77a-6006-4d4c-80b3-4fa62fce67cc`.
  Verified GameId/PlaceId 0; backed up scripts and synced 57 current sources; left stopped in Edit.
- [x] Phone-emulator startup/loading success, seven active navigation tabs, 8 reduced-effects
  and 10 normal-effects close/reopen cycles, hidden-camera pause/resume and actual UI egg purchase/claim/reveal.
- [x] Fixed initial wallet text at 0 and verified animated currency intermediate/final values.
  Counter fixture was client-only and restored; not a server currency grant.
- [x] Bounded panel texture density: collection descendants **3752 -> 1974** at the same
  750x323 viewport. Final console only build-ready message. This is not an FPS result.
- [x] [Runtime observations](https://github.com/Znypr/be-dino/blob/codex/ui-motion-polish/docs/evidence/2026-10-08-ui-motion/runtime-observations.json)
  and [phone screenshot](https://github.com/Znypr/be-dino/blob/codex/ui-motion-polish/docs/evidence/2026-10-08-ui-motion/phone-final.png) archived in PR #2.
- [ ] Physical mouse/touch/controller activation, early-close hatch regression,
  loading-failure/slow-server transitions and delayed/error shop results.
  Return selection drove tests; injected ButtonA did not activate.
- [ ] Real phone safe-area/touch ergonomics, measured frame time/memory and
  repeated panel open/close connection counts. Existing emulator evidence is historical.
- [ ] Further preview pooling/reuse only after measurements justify it; runtime
  mesh templates already cache geometry. No unbounded pool is added.

This is UI presentation work, not proof of frame-rate improvement or completion of
BD-019. Studio tests used an unpublished in-memory preview profile; no persistent profiles
or published place were changed. The Studio snapshot includes other agents' local shop/genetics
work excluded from this UI-only PR. A concurrent GeneTextures module appeared after the
57-script sync and is not certified by these tests.

### Hatching, traits and leaderboards, 2026-10-08

Current mechanics supersede the old 60-second/10-second new-egg incubation.
Existing saved eggs retain their readyAt; new eggs are ready immediately.
Only the verified unpublished Build 019 copy was modified/tested in Studio.

- [x] Per-run rewards committed before hatching, sorted Common -> Rare -> Legendary.
  No client rolls. Metadata/outcomes survive overflow, repeated transforms and rejoin.
- [x] Actual automatic post-run hatching waits for sanctuary respawn. Phone trace:
  Raptor -> Stegosaurus -> Ankylosaurus, intervals 5.059 and 5.066 seconds.
  Desktop also revealed Compy -> Triceratops -> T-Rex, completing all six species.
- [x] Native 3D egg shake/fracture/reveal with existing textured dinosaur models.
  Closing during the first reveal left two unclaimed eggs after six seconds.
- [x] Exact independent 1/20 Shiny on four irregular events and 1/10 BIG in all
  conditions, including clear. Offline exhaustive roll grid verifies 0.5% stacking.
  Runtime fixtures are deterministic, not observed natural drop-frequency evidence.
- [x] Shiny-only and stacked previews checked. BIG measured 1.0 -> 1.3 scale and
  collider 3.38 x 2.4 x 4.16. Separate trait copies never become fusion fodder.
- [x] Increasing rare/legendary odds for 1-15 eggs checked; current thresholds
  still grant 1/2/3 eggs. No change to the existing food/catch conversion.
- [x] Three sanctuary boards render on desktop and phone emulator. Real unsaved
  session rarity/playtime populate; Robux board stays empty without verified purchases.
- [x] Offline receipt retry deduplication, unknown-product/player rejection and
  playtime checkpoints pass. No synthetic purchase reached Roblox/persistent data.
- [x] Final phone hatch controls measured >=44 pixels; screenshots archived.
  Final runtime console had no game script errors. Studio stopped/reset to default.
- [ ] Verified paid product IDs/grants and real purchase receipt test. Catalog is
  intentionally empty; passes/historical spend are not covered by developer receipts.
- [ ] Published cross-server OrderedDataStore rankings and persistent migration/
  rejoin, physical phones, multiplayer and maximum-growth BIG collision/performance.
  These release checks remain deferred; no published place/player data was touched.

Mechanics: [current hatching notes](37-hatching-traits-and-leaderboards.md).
Evidence: [screenshots and fixture boundaries](evidence/2026-10-08-hatching-and-leaderboards/README.md).
BD-042 remains Review / test. The concurrently added BD-035-041 planning tasks
retain their IDs and scope; this local gameplay pass does not complete those plans.

### New proposed shop/egg systems, 2026-10-08 (BD-035â€“041)

**Shared visual reference:** [Egg appearance vision](39-egg-appearance-shared-vision.md) consolidates the owner review and archives pattern/color/condition/aura previews. Matte shell, tile/grass grounding and reusable Cracked/Dirty overlays are accepted directions; exact art-authoring weights are provisional; latest seven engulfing smoke/anime auras are review drafts. Rainbow/Astra rework resumed and the owner accepted Astra's brighter curved-vertical opal direction. [Combined-condition review evidence](evidence/2026-10-08-egg-condition-combinations/README.md) tests selected patterned/color/condition/Magma stacks. Local 1024-to-512 RGBA/alpha and camera/mesh checks are authoring evidence only; they do not close missing authored-runtime layers, uploads or Studio/device acceptance. Existing gameplay acceptance is recorded separately above.

- [ ] **BD-035:** Replace draft/Microsoft-Paint-quality egg art with a high-quality Blender master, fixed mesh and camera; export true transparent 512x512 RGBA base, patterns, conditions and separate mutation passes. Prove matching masks/preview alignment, then test in Studio. No finished art is claimed.
- [ ] **BD-036:** Add crystals awarded/unboxed at run end alongside map pickups; design Robux crystal packs with server-authoritative idempotent receipt grants, persistence and purchase restrictions. Crystal award quantities remain configurable.
- [ ] **BD-037:** Let players buy random eggs with crystals to join sequential hatching without losing purchases on full queues. Validate random-paid-item policy/disclosure before monetized release.
- [ ] **BD-038:** Replace/extend three cosmetic trails with **ten** crystal-priced tiered coloured walking trails, from free normal white to highest **Astra glitter**. Prices, speed buffs and required **persistent account levels** increase by tier; cap aggregate speed and migrate existing ownership.
- [ ] **BD-039:** Crystal-priced 5-minute Speed Potion, reusing the existing potion inventory/expiry and server multipliers; avoid duplicate shops.
- [ ] **BD-040:** Condition Shop progressively reduces Cracked odds/increases Rainbow/Astra odds with escalating level and crystal gates. User-confirmed 2026-10-08: Cracked **20% hatch success** and **80% speed/growth** if successful; Dirty 80%; Normal 100%; Rainbow 120%; Astra 180%. Factors affect **both movement speed and growth intake**, before final shared caps. Implementation, failed-hatch consolation and interaction tests remain Todo; this specification confirmation is not an acceptance pass.
- [ ] **BD-041:** Two server-selected rarity-weighted egg colors and saved random visible coverage share, inherited by dinosaur; preserve tonal pattern contrast for matching genes. Vivid red is rare and pure black exceptionally rare. Reconcile percentage endpoints with that hierarchy; the shared art draft uses 1â€“99% for mixed genes and 100% for matching pairs, not approved public odds. Independent Normal/Big eggs (Big visuals 1.2x proposed, same stats), Shiny sparkle and immutable persistence remain in scope; see the existing tested BIG baseline before changing scale.

These are **planned**, not implemented or approved public balance. The earlier three-size proposal is superseded by **Normal and Big only**; shiny is not a stat condition. Existing BD-028/029/032/034 test evidence remains historical and does not certify these additions. [Detailed mechanics, proposed starting trail catalog, unresolved decisions and acceptance criteria](36-crystal-shops-egg-genetics-and-progression.md).

### Weather, trails and visual upgrade, 2026-10-08

Current scope supersedes the earlier next-step list: the user deferred non-owner
published assets, physical-phone and multiplayer/persistence release checks.
They remain open, not passed. No published experience or persistent player
profile was changed. Work used a separate unpublished Build 019 copy.

- [x] Seven weighted weather events configured, including Volcanic Bloom,
  Northern Lights, Earthquake and Blood Moon. Actual server event transitions,
  lighting and loot multipliers tested through a disposable clock fixture.
- [x] Real food pickup crossed 9 to 10 catches under volcanic weather and created
  an Ember-tagged egg. The mutation roll was deterministic in the disposable
  fixture; no claim of observed natural drop frequency.
- [x] Additive trail/event migration, owned/equip validation, metadata integrity,
  overflow FIFO, duplicate settlement/claim and rejoin pass offline transactions.
- [x] Ember, Aurora and Blood Moon eggs hatch in order through actual UI, retain
  their mutations, and show correct perks. Server applies Blood Moon speed 1.12x
  and growth 1.87x with Royal Nova in clear weather.
- [x] Aura/trail shop previews, permanent purchases/equip and moving tapered
  trails engine checked. Reduced-effects fixture disables all cosmetic/weather
  effects. Desktop and phone-emulator captures archived.
- [x] Six actual owner-created textured models load and render in the index.
  Imported camera clipping fixed and regression tested; native models retained.
- [x] Twelve selected grass/rock/bark map creators match verified owner
  7285577648. Authored MaterialService is packaged; protected runtime material
  creation removed after detecting the startup failure.
- [x] Reusable manifest and binding generator recorded. New native event symbols
  and assembled trail previews are NOT completed illustrated PNGs.
- [ ] Art approval, refined event VFX/custom textures, environment mesh upgrades
  and measured performance. Three environment-generation jobs failed.
- [ ] Authored Rainbow/Astra layer integration: rework resumed; owner accepted
  Astra's bright five curved vertical opal streaks and three hero stars. Rainbow
  retains multicolored stars without black outlines. Earlier recolors, bold-star
  and crossing-streak variants remain backups. Combination renders are authoring
  evidence; Roblox upload/runtime/phone checks remain open.
- [ ] All phone modal targets/readability and physical-device performance.
  Cosmetic shop targets were enlarged; this is not whole-app phone acceptance.
- [ ] Non-owner published permissions, multiplayer load and persistent-data
  migration/rejoin release tests: deferred by user.

Design/configuration: [event and visual notes](35-event-mutations-and-visual-upgrade.md).
Exact fixture boundaries and screenshots: [evidence](evidence/2026-10-08-events-and-cosmetics/README.md).
BD-034 stays Review / test, not Done.

## Build 017 and next features

[Detailed requirements, screen list, icon backlog and acceptance checks](30-build017-and-progression-roadmap.md). [Build 018 implementation and recorded local checks](31-build018-progression-test.md). Build 017 source/UI corrections and an isolated final export are prepared; progression systems are now integrated in Build 018. BD-027 and Studio acceptance remain open before release. Earlier Done records apply to their tested historical builds; they do not certify the redesigned Build 017.

## Acceptance and current evidence

### Build 019 leap/weather illustration integration, 2026-10-08

Pulled `6831ffd` and followed the five-master handoff. This supersedes the draft
upload/integration/Studio-pending entries below, not the remaining release gates.

- [x] Uploaded all five original masters via MCP; every GetProductInfo creator is
  User `znyprs` / `7285577648`, matching the verified published place owner.
  Actual IDs and metadata recorded in `icons/upload-bindings.json`; original seven
  bindings preserved. Generator now strictly validates all twelve logical keys.
- [x] `UIIconLayout` centers leap at .80 and weather keys at .84. Logical slots,
  native geometry, live timers/labels and existing Clear-to-weather mapping remain.
- [x] Synced the connected unpublished Build 019 copy (GameId=0 / PlaceId=0).
  Desktop and iPhone 17 Pro landscape: Clear, Rain, Thunderstorm and Blizzard all
  load and remain distinct; leap ready/cooldown loads in both layouts. Actual E
  leap set a 60-second cooldown, and READY returned on natural expiry.
- [x] All five native empty-binding fallbacks engine-verified independently;
  48/64px visual inspection passed. [Eleven screenshots and runtime evidence](evidence/2026-10-08-weather-and-leap/README.md)
  archived. Game console clean; play stopped, simulator reset, fixtures discarded.
- [x] Build 019 regenerated, 45 Luau sources compile, artwork harness and binding
  checks pass; 25 Python tests pass, including new binding validation and exact
  five-master decoding/hash checks.

Weather attributes were temporary server fixtures to exercise UI state transitions,
not proof of random scheduling/bonuses. No persistent player data changed and no
experience was published. The published Studio instance was not connected in this
pass; only the connected local copy was synced. BD-033 remains Review / test for
non-owner published permissions and physical-phone checks; BD-019 remains open.

### Weather artwork drafts, 2026-10-08

All four separate weather PNG masters are generated: Clear/default, Rain, Thunderstorm and Blizzard. Each has a sibling prompt/integrity/review manifest in `resources/ui/v2/icons/`. Full RGBA decoding, transparent/opaque alpha checks and exact SHA-256 verification pass. Generation requested 14% margins but actual margins are tighter; start at centered UI scale 0.84 and inspect at 48/64px. These results supersede the weather Todo statement in the earlier leap entry below. Roblox uploads, expanded icon bindings, desktop/phone Studio screenshots and non-owner loading remain pending. No runtime sources or build changed. [Exact integration handoff](../resources/ui/v2/icons/weather-and-leap-handoff.md).

### Leap artwork draft, 2026-10-08

`resources/ui/v2/icons/leap-v1.png` is generated as a separate reusable RGBA master, matching the existing illustrated dinosaur style. Full PNG decode and alpha checks pass; exact prompt, SHA-256 and margin limitation are recorded in `leap-v1.manifest.json`. Generated does not mean uploaded or integrated. Use a centered inset around 0.80 and verify small-size readability/edge fringe in Studio before acceptance. The native leap symbol remains active. Clear, Rain, Thunderstorm and Blizzard illustrations remain Todo. No runtime sources, build or persistent data changed.


### Build 019 shared navigation compositions, 2026-10-08

Continued from `91aac96`. Shared configurable `NavigationArtwork` maps AURAS to
`aura_meadow` and POTIONS to `potion_speed`, using the existing shop assembler,
layer bindings/layout and native fallbacks. No new uploads or flattened PNGs.

- [x] Synced repository changes in Edit to both verified Build 019 instances.
- [x] Desktop and iPhone 17 Pro landscape emulator: reused compositions visible,
  all PNG layers loaded, separate ring clips/fossil and bottle/native speed emblem
  preserved. Navigation label/icon bounds remain clean; phone buttons are 82x44.
- [x] Archived and inspected [desktop/phone screenshots and exact evidence](evidence/2026-10-08-navigation-compositions/README.md).
- [x] Unpublished GameId=0 / PlaceId=0 copy only for play; persistent data untouched.
  Clean game console, play stopped and simulator reset to default.
- [x] 44 sources compile; shared mapping/assembly/fallback harness, binding checks
  and 21 Python tests pass. Build 019 regenerated.
- [ ] Illustrated leap and all implemented weather states: Clear/default, Rain,
  Thunderstorm and Blizzard. Native symbols do not complete these assets; see
  the separate new-artwork table in `docs/32-artwork-guide-and-todo.md`.

BD-033 remains Review / test for those illustrations and unverified release gates.
This emulator pass does not close real-phone touch/performance or non-owner
published permissions. Earlier gameplay evidence below remains unchanged.

### Build 019 MCP acceptance, 2026-10-08

Initial pass at `7caf41a`; the separate unpublished follow-up below supersedes its
pending single-client purchases, fusion, hatching and all-species cases.

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

### Build 019 illustrated icons and disposable acceptance follow-up

Continued from `7caf41a` on 2026-10-08. Seven existing illustrated originals
(trophy, dinos, egg, home, fusion, shield and amber) were uploaded through MCP.
Every GetProductInfo creator is User `znyprs` / `7285577648`, matching the experience
owner. Real IDs live in `resources/ui/v2/icons/upload-bindings.json`; the generator
`tools/bind_ui_icons.py` produces `UIIconAssets.luau`, consumed by UITheme.
Navigation uses the illustrated fusion icon; mutation footprint badges retain their
separate meaning. Leaf, speed, leap, weather, locks and other small utility graphics
remain native. All seven ImageLabels reported IsLoaded=true. Empty-binding native
fallbacks were exercised separately: all seven produced nonempty graphics and no
ImageLabels (amber retains the actual crystal-model viewport).

The original published `newbuild` instance was only edited/synced, never played in
this follow-up. Persistent player data was not read, granted, reset or written.
A rebuilt file was copied to `%TEMP%/BeDino-019-DisposableAcceptance.rbxlx` and opened
as a separate Studio instance `83a530b4-df1c-44ca-b216-3367e97119c0`.
Before fixtures, MCP confirmed GameId=0 and PlaceId=0. ProfileMode was
`Studio preview (not saved)`, with the existing local 1,000,000-crystal wallet.
Only that copy's default in-memory profile source was changed: Compy 50 Base / 50
Gold and one Base of each other species. A synthetic 500-catch active run supplied
three eggs through normal return/settlement. These fixtures are not in repository
runtime source or the rebuilt deliverable, and must never be published.

| Acceptance case | Runtime evidence | Result |
|---|---|---|
| Aura purchase/equip | Actual BUY -> BUY AURA -> EQUIP buttons; meadow owned/equipped; GrowthMultiplier=1.15 | Pass in disposable engine session |
| Potion purchase/use/replace | Actual 20 Crystals -> BUY POTION -> USE; speed_common consumed to zero; SpeedMultiplier=1.2; another purchase/use prompted REPLACE & USE and advanced expiresAt | Pass in disposable engine session |
| Gold fusion | Actual FUSE SELECTED DINO -> CONFIRM FUSION; Compy 50 Base / 50 Gold -> 0 Base / 51 Gold; status mutated; character gold | Pass |
| Diamond fusion | Actual DIAMOND -> FUSE -> CONFIRM; Compy 0 Base / 51 Gold -> 0 Base / 1 Gold / 1 Diamond; status mutated; character diamond | Pass |
| Sequential hatching | HATCH NEXT EGG then NEXT EGG; three distinct committed IDs; queue 3 -> 2 -> 1 -> 0; rewards 2 Triceratops, 2 Raptor, 1 Stegosaurus; final NEXT returned to Growing Eggs | Pass; server claims, not fabricated client reveals |
| Six playable species | Each equip/start succeeded, DinoAttached=true, correct SpeciesId and packaged visual; W/Space moved each 28.77-30.93 studs; all six returned to Sanctuary | Pass for single-client short movement runs |
| Disposable reset | Stop/start recreated Compy 50 Base / 50 Gold, empty egg queue and local wallet | Pass; no persistent lease/data path |
| Desktop/phone icon audit | Archived screenshots show illustrated trophy, navigation and currency loading; iPhone 17 Pro landscape and desktop layouts inspected | Pass for tested layouts; small modal touch targets remain an ergonomics limitation |
| UI regressions | Claimed-egg success toast covered the preview: suppressed redundant toast; growth pulse targeted navigation scale: now restores HUD's own responsive base; real phone-emulated food pickup yielded 5 growth with HUD scale 0.47625 / rail 1 | Fixed, synced and retested |

Screenshot PNGs and structured runtime traces are archived in
[`docs/evidence/2026-10-08-icons-and-acceptance/`](evidence/2026-10-08-icons-and-acceptance/README.md).
Species screenshots show actual equipped models in Sanctuary after their movement
runs; they use a temporary inspection camera. Initial hatch captures preserve the
toast defect, and the final hatch capture verifies its correction. Keyboard selection
activated UI buttons; Escape is blocked by Studio VirtualInput, so close buttons were
used instead. This is not proof of real finger interaction.

Validation: 43 Luau sources compile, all 21 Python tests pass, binding checks and
artwork assembly pass, and the standard build/source round-trip succeeds. No gameplay
script errors were observed; Assistant camera-reset messages are tool diagnostics.
Still unverified: real target-phone performance/touch ergonomics, two-client interaction
and races/load, published non-owner permissions, production persistence/rejoin of the
new transactions and experience privacy/access settings. Historical Done entries are
not extended to those cases; BD-019 and the larger device/multiplayer gates stay open.
Both instances were left stopped; default viewport restored. The disposable source
fixture was removed after testing. Fourteen archived PNGs passed image verification.

### BD-001 â€” research
Done. Initial screenshot/source research and planning documents were completed on 2026-09-17.

### BD-002 â€” direction
Done. Znypr selected a private test, cute/simple ground arena and small complete progression loop.

### BD-003 â€” setup/design blockers
Done. Personal account, Studio installed, â‚¬0 target budget, immediate run dinosaur loot plus separate chest loot, increasing total copy rewards and stacked duplicates are confirmed.

### BD-004 â€” reproducible project/private place
**Done when:** source mapping/build is reproducible and the actual private test experience/place is recorded with isolated test data.

Source mapping, dependency-free Python packager and generated `.rbxlx` are working. A separate private test experience is now being used for DataStore testing, but the repository still does not record its experience/place IDs. That remains the blocker for closing BD-004.

2026-10-13 (Milestone 1): the playtest uses a **new** private experience with a fresh DataStore; IDs are pending from Znypr. Record them in `PlaytestUniverseId` / `PlaytestPlaceId` in `src/shared/Config.luau` (placeholders marked `TODO(BD-004)`, right after `ProfileDataStoreName`) and in the release record of the [playtest runbook](55-playtest-release-runbook.md) Â§2/Â§6. `tools/verify_release.py --profile playtest` and `tools/build.py --profile playtest` fail until both are positive. Move to Done when that commit lands.

### BD-005 â€” persistence and remote contracts
Done as a specification. `docs/13-persistence-remote-contracts.md` chooses a project-owned `DataStoreService`/`UpdateAsync` repository with leases, revisions, immutable operation outcomes and explicit remote validation. Durable implementation remains BD-011.

### BD-006 â€” controller/camera
**Done when:** desktop and touch movement work, min/max visual-size behavior is usable and two clients replicate correctly.

Desktop evidence passed: movement, camera, dinosaur visibility, size behavior, reset isolation and two-client replication. Mobile/touch is still untested, so the task remains `Review / test`.

2026-10-13 note: the touch HUD/control layout (BD-054), hill traction (BD-053) and Home (BD-052) changes in [51](51-bd053-054-movement-mobile.md) include the owner Android checklist that can also supply BD-006 mobile evidence.

### BD-007 â€” asset kit
**Done when:** one original dinosaur silhouette/palette, manifest template and procedural fallback are reviewable.

Done. `docs/23-original-asset-manifest.md` records the original procedural silhouettes, palettes, Gold treatment, arena kit, rights/source and zero external-asset dependency used by Build 013.

### BD-008 â€” food/growth
Done. Znypr reported all Build 004 checklist cases working: pickup, growth, respawn, simultaneous ownership, remote growth replication and reset. The implementation remains bounded and server-owned; tuning is temporary.

### BD-009 â€” PvP/spawn safety/run ending
Done for desktop multiplayer. Znypr reported Build 005 tests 1â€“9 all working: spawn protection, standing-still exit, movement cancellation, equal-size safety, bigger-eats-smaller, protection after respawn, replication, exit-vs-predation race and Reset Character. The shared terminal guard produced no reported duplicate endings.

### BD-010 â€” alpha economy
Done for private mechanics testing. `tools/economy_sim.py`, `tests/test_economy.py` and `docs/15-economy-simulation.md` define and verify the 0â€“5000 catch range, exact increasing copy totals, exponential rarity allocation, eligibility thresholds, independent chest grants, repeat-victim anti-farm proposal and 50-copy mutation risk.

Important finding: one Common alpha species reaches 50 copies at catch score 62. The 50-copy mutation cost is therefore a mechanics-test value, not accepted public progression balance.

### BD-011 â€” persistence/settlement
**Done when:** rejoin, load failures, duplicate settlement, stale sessions and competing servers preserve committed inventory and immutable run outcomes.

Build 006 runtime tests 1â€“10 passed. Confirmed: load/save/rejoin, exact +1 reward settlement, deliberate duplicate settlement does not double-grant, Reset Character settles the run, repeat-victim protection behaves as designed, disabling Studio API access fails closed with no playable dinosaur, and re-enabling access restores the prior profile. Znypr also confirmed Compy copies can increase above 3; the earlier apparent stop was the 60-second anti-farm window rather than a cap.

Build 007 completed the final acceptance case. Znypr confirmed the lease test passed in a new private test experience, earned copies persisted through a full restart, and the probe did not corrupt player progression. BD-011 is Done. The temporary lease probe is removed from normal runtime in Build 008.

### BD-012 â€” collection/equip
**Done when:** three species definitions, owned/locked counts and equip survive reconnect; invalid equip is rejected.

Build 008 passed all eight runtime checks. Owned/locked counts, server rejection of locked T-Rex, one-time Triceratops test unlock, visual switching, Reset Character persistence and full reconnect persistence all worked. BD-012 is Done.

### BD-013 â€” earned chest queue
**Done when:** server timestamps, offline elapsed time, duplicate claims and capacity/overflow policy pass. Chest loot remains independent from immediate run loot.

Build 009 passed all eight runtime checks. The five-slot active queue, two-item overflow case, absolute offline timestamps, claim persistence, duplicate-claim protection and duplicate test-grant protection all worked. BD-013 is Done.

### BD-014 â€” Gold mutation
**Done when:** atomic 50-copy conversion handles 49/50/51 copies, duplicate requests and equipped-copy semantics without negative counts.

Build 010 passed all eight runtime checks. The 49-copy rejection, exact 50 and 51 conversions, duplicate mutation replay, equipped Gold-only semantics, Gold visual and reconnect persistence all worked. BD-014 is Done.

### BD-015 â€” core UI
**Done when:** lobby, HUD, run summary, collection and chest queue are usable on desktop/touch and large duplicate stacks render as grouped counts rather than hundreds of cards.

Build 011 passed all eight checks. Tutorial, compact HUD, grouped collection rows, chest UI, Home, run summary and phone-landscape emulator layout/actions all worked, with development grant/setup controls absent. BD-015 is Done.

### BD-016 â€” dinosaur/map kit
**Done when:** three distinct original dinosaurs, one arena and Gold treatment pass collision/camera/permission checks. Procedural fallback is acceptable for the private test.

Build 013 integrates the original procedural Compy, Triceratops, T-Rex, Gold treatment and meadow/nest environment kit. All decorative props are non-colliding and no external asset permissions are required. See `docs/24-visual-kit-test.md`.

### BD-017 â€” audio
**Done when:** minimal effects work for a non-owner published tester with independent mute/volume behavior. Ambience is optional.

### BD-018 â€” multiplayer/security/persistence suite
Execute the verification matrix from `docs/06-roadmap-and-testing.md`. Source inspection is not runtime evidence.

Build 012 passed all eight runtime checks. Malformed/flooded remotes, impossible movement correction, normal gameplay after attacks, two-client isolation, equal-size safety, one predation outcome, end-run-vs-predation terminal race and post-restart inventory persistence all passed. BD-018 is Done.

### BD-019 â€” device/load/published assets
Requires a real target phone plus the agreed multiplayer/pickup load test and non-owner asset checks.

2026-10-13 â€” **In progress, owner publish pending.** `tools/verify_load.py` (in CI) runs the real ProfileRepository with a mocked, latency/throttle-modelled DataStore: 8 and 12 simulated players over 15 min pass with zero failed operations, no throttling and peak 55â€“57% of the 60 + 10Ã—players/min budget. Report-only: a BD-044 150-egg simultaneous reveal sits at ~100% of budget and one equip-spamming client uses ~60% of an 8-player server's budget; batching egg claims and a per-player write budget are recommended. The Studio 2/4/8-client, desktop + Android and non-owner rows of the [runbook matrix](55-playtest-release-runbook.md) Â§5 remain to be executed after publish. Offline results are not device or live-DataStore evidence.

### BD-020 â€” private release/rollback
Requires a known-good commit/build, private access settings, no public debug grants, known issues and a tested rollback.

2026-10-13 â€” **Review / test, owner publish pending.** `python tools/build.py --profile playtest` produces a reproducible playtest place (playtest store name, `ReleaseProfile = "playtest"`, manifest with commit/dirty flag) and `tools/verify_release.py` enforces paid/test/debug flags off (default profile in CI). [Playtest runbook](55-playtest-release-runbook.md) holds gates, owner Studio publish steps, tagging (`playtest-m1-bNNN-rK`), release record, known-issues template, rollback/store-rotation and data-reset policy. Done requires the actual private publish, the recorded release row and a performed rollback drill.

### BD-021 â€” observed community test
Run the small invited session only after BD-020. Capture friction, repeat-run behavior and defects separately from suggestions.

### BD-022 â€” public-alpha decision
Public scope is an evidence-based later decision. Passing code generation alone never triggers launch.

## Session log
- 2026-09-18: Znypr reported Build 012 tests 1â€“8 passing; per-run Growth/Size/Catches correctly reset while persistent inventory remained. BD-018 moved to Done. BD-007 asset specification completed and Build 013 visual kit prepared for BD-016 testing.
- 2026-09-18: Znypr reported all Build 011 core UI tests passing, including phone-landscape emulator interaction. BD-015 moved to Done. Build 012 security/multiplayer regression prepared for BD-018.
- 2026-09-18: Znypr reported all Build 010 Gold mutation tests passing. BD-014 moved to Done. Build 011 core UI prepared for desktop and phone-landscape emulator verification.
- 2026-09-18: Znypr reported all Build 009 chest queue tests passing. BD-013 moved to Done. Build 010 Gold mutation prepared for BD-014 runtime verification.
- 2026-09-18: Znypr reported all Build 008 collection/equip tests passing. BD-012 moved to Done. Build 009 chest queue implemented for BD-013 runtime verification.
- 2026-09-18: Znypr reported Build 007 checks passing in a new private test experience: Profile Loaded, fresh starter state, lease test PASS, reward gain, full restart and persisted copy count. BD-011 moved to Done. Build 008 collection/equip prepared for runtime verification.
- 2026-09-17: Build 007 prepared for final BD-011 runtime verification. Added a temporary DataStore lease/stale-writer probe and HUD `Lease test` status. Final Build 007 CI passed and generated the test artifact.
- 2026-09-17: Znypr reported Build 006 tests 1â€“10 passing. Rejoin persistence, duplicate settlement, Reset Character settlement, anti-farm behavior and fail-closed API/DataStore behavior passed. Compy copies were confirmed to continue above 3. BD-011 moved to Review / test pending the competing-session/stale-lease case.
- 2026-09-17: Znypr reported Build 005 tests 1â€“9 all passing. BD-009 moved to Done for desktop multiplayer.
- 2026-09-17: BD-010 economy simulation completed. Six deterministic tests pass across catch scores 0â€“5000. Private-test thresholds and chest grants are recorded in `docs/15-economy-simulation.md`; 50-copy Gold is flagged as intentionally fast test pacing.
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

### Proposed: notification system and mini objectives (2026-10-14, Backlog)
Feature-intake analysis only; nothing built. See [65](65-intake-notifications.md) and [66](66-intake-mini-objectives.md).

| ID | Status | Pri | Task | Depends on |
| --- | --- | --- | --- | --- |
| BD-066 | Review / test | P1 | NotifyQueue pure module: priority, dedupe, throttle, cap ([65](65-intake-notifications.md)); built + `tools/verify_notify.py` ([80](80-notifications.md)) | none |
| BD-067 | Review / test | P1 | Toast v2 renderer, 3 pooled cards, rarity tints, motion-off ([80](80-notifications.md); Studio pending) | BD-066 |
| BD-068 | Backlog | P2 | Notification icons (5) + toast plate, owner upload | none |
| BD-069 | Review / test | P1 | Wire popup events and hatch-batch summary ([80](80-notifications.md); new-species and fusion cards not yet) | BD-067 |
| BD-070 | Backlog | P3 | Notification Sfx mapping | BD-069 |
| BD-071 | Backlog | P2 | Notification Studio/Android acceptance | BD-066-070 |
| BD-072 | Backlog | P2 | ObjectiveConfig catalogue and rewards ([66](66-intake-mini-objectives.md)) | none |
| BD-073 | Backlog | P2 | ObjectiveService, additive profile field, server-clock windows, claim | BD-072 |
| BD-074 | Backlog | P2 | Objective event hooks | BD-073 |
| BD-075 | Backlog | P2 | Collapsible objectives panel, phone-safe | BD-073 |
| BD-076 | Backlog | P3 | NextGoal shows top objective | BD-075 |
| BD-077 | Backlog | P3 | Objective icons (4 new) | none |
| BD-078 | Backlog | P2 | Objectives Studio/Android acceptance | BD-072-077 |
| BD-079 | Review / test | P1 | Dino action animations (procedural, all species): eat, leap/jump stretch+land, death/eaten, bite lunge, turn lean; dust/munch effects reuse SFX; real Blender clips later. Roles: gameplay eng (hooks), tech artist (motion), audio (reuse pack) | BD-043 |
| BD-086 | Backlog | P1 | Pick aura/trail style, freeze spec (doc 70) | none |
| BD-087 | Backlog | P1 | Aura/trail sprite sheets and textures | BD-086 |
| BD-088 | Backlog | P2 | Ribbon textures and ground-disc decals | BD-086 |
| BD-089 | Backlog | P1 | Studio spike: trail + aura per tier, ground sigil | BD-086 |
| BD-110 | Backlog | P1 | CosmeticEffects v2 auras (tiers, orbit beams) | BD-087, BD-089 |
| BD-111 | Backlog | P1 | Trail v2 textured, six-class complexity | BD-087, BD-088, BD-089 |
| BD-112 | Backlog | P2 | Config: trail class, aura tier, 3 new auras | BD-086 |
| BD-113 | Backlog | P2 | Shop icons (16) and rarity badges (6) | BD-112 |
| BD-114 | Backlog | P2 | Shop previews use real effect sprites | BD-111, BD-113 |
| BD-120 | Review / test | P1 | Owner-only admin panel for private playtests: food worth / growth / run speed sliders, start or stop any weather, runtime-only, server-authorized ([79](79-admin-panel.md); offline checks pass, Studio pending) | BD-031 |
| BD-154 | Backlog | P0 | Mutation audit, end to end. Owner 2026-10-15: "not sure mutations work yet: 1 visible, 2 gettable". Prove or fix: (gettable) earned eggs picked up during Volcano, Thunderstorm, Blizzard, Earthquake, Northern Lights and Blood Moon roll the weather mutation at the configured chance (ProgressionConfig.Weather chance 2-8%), the egg keeps it through claim, hatch and save; (visible) the mutation shows on the egg card, in the hatch reveal ribbon, on the Dino Index card and Dino Details, and as a visible effect on the dino in the world and in previews (MutationEffects: color tint, glow, particles per mutation). Offline checks plus a Studio walk-through with the admin panel (start weather, Food worth x10) and fresh playtest build | BD-044, BD-130 |
| BD-153 | Backlog | P1 | Auto-open by rarity (settings, premium-ready). Per rarity the player picks Show every reveal or Auto-open: auto-opened eggs hatch instantly, are credited and listed in a tidy "Auto-opened" summary (counts per rarity, best find on top); Uncommon and up can stay manual. Shiny, BIG and mutations are never auto-opened. The server rules stay untouched (a UI preference only). Build it behind a flag (Config.AutoOpenRequiresPass, off for the playtest so everyone has it) so it can later sit behind a Robux gamepass without rework; the Settings screen shows a clear lock state when gated. Extends the existing RevealSkip (BD-044) | BD-044 |
| BD-152 | Backlog | P0 | Caught Eggs screen shows ONE egg at a time. After a run the player is never forced into hatching: the Eggs screen shows a single large "Next egg" card (real egg with its genes look, condition, weather and mutation badges, READY/Growing timer) with one clear OPEN button, "Eggs waiting: 81", and the Auto-open settings shortcut; opening one egg runs the hatch sequence, then returns to the card for the next. Merged with the Nests row (BD-148) into one screen: nests on top (five slots, 3 h timers), next caught egg below. Remove the five-slot caught-egg strip | BD-148, BD-153 |
| BD-155 | Review / test | P1 | Mutation visuals gap (audit 2026-10-15): event mutations only show as the aura-style mist/beams on the EQUIPPED dino in the world. Missing: (a) a model tint/material cue on the dino itself, (b) mutation look in Dino Index/species hero previews and "My dinos" cards (only a text line today), (c) mutation tint on genes-egg cards in the Eggs screen (label only), (d) previews never use MutationEffects. Add one shared tint helper used by world, previews and cards. **2026-10-15 (claude/mutation-visuals):** `src/shared/MutationLook.luau` is the shared look table (tint, rim, glow, matte material, palettes); the world dino (CosmeticVisuals), Dino Index / My dinos / details previews and the hatch dino (via PreviewTraits + DinosaurPreview), the Eggs-card colour dot and the mist all use it; `tools/verify_mutation_look.py` in CI. NOT verified on a phone or by an owner screenshot | BD-150 |
| BD-156 | Review / test | P2 | Nest eggs never roll event mutations: ProfileRepository.rollNestEggs hardcodes eventId clear. Decide (owner) whether nests dropped during weather should carry the weather tag; if yes store weatherId on the nest at drop and roll ProgressionRules.eventEgg at claim. No odds change made in the audit. **2026-10-15 (claude/mutation-visuals, lead decision):** a nest dropped during weather stores `weatherId` (additive field, set at settlement from the server `WeatherId`; only known non-clear weather is kept) and claiming rolls `ProgressionRules.eventEgg` per nest egg with the SAME event chance as run eggs (nest luck for Shiny/BIG unchanged and mild); legacy/clear nests roll nothing; `tools/verify_nests.py` covers tag, forged tag, rate and exactly-once. Disclosed in docs/85 | BD-090 |
| BD-151 | Review | P1 | Dino Index "Sort and filter" menu: one button next to the species page tabs opens a compact sheet (chips, 44 px targets, one row per group) to filter by color, pattern, mutation, Shiny, BIG, stage (Base/Gold/Emerald/Diamond), condition, and sort by Rarest, Newest, Color, Pattern, Species. Reuse the proven FusionSelection filter and sort model (FilterFields/SortKeys) so Fusion and the Index never disagree; show the active filters as removable chips and a plain "No dinos match, clear filters" empty state. Chip labels are short words, colors show their swatch, patterns their mini texture. Filters apply to the "My dinos" list (BD-150) and to the species grid | BD-150, BD-149 |
| BD-150 | Review | P0 | Dino Index species page: "My dinos" list. Opening a species (e.g. Compy) shows every copy the player owns as a scrolling grid of cards (mini 3D preview with its real pattern and colors, stage badge, Shiny/BIG/mutation ribbons, size), with the count in the header ("Compy x 14"). Tapping a card selects it: the big preview, the traits and the percent lines switch to that exact dino (Dino Details data), and EQUIP then equips that copy, not just the species. Equipped copy shows an "Equipped" tag; the first card is the best copy by default. Large collections page or virtualize (cap rendered previews, reuse BD-149 loader rules so no cube fallbacks). Empty species keep the silhouette + "Not discovered yet" | BD-149, BD-044 |
| BD-149 | Review | P0 | Inspect any dino: drag to rotate. In the hatch reveal (after the dino pops in, before TAP for the next egg) and on the Dino Index / Dino Details preview the player can spin the dino 360 degrees with a finger or mouse drag, inertia on release, a slow idle auto-spin until first touch, a small "Drag to turn" hint that disappears after the first drag, and a reset-view button; optional pinch / wheel zoom between limits. Tapping outside the dino or the TAP hint still advances the hatch, so rotation must not eat the continue tap (drag threshold about 12 px). Reduce Motion: no auto-spin, rotation by drag only. Works in ViewportFrame previews on phone (320 px) without extra per-frame instance creation | PR hatch-sequence, BD-145 |
| BD-160 | Parked | P3 | Monetization ideas, no code: auto-open pass, weather radar, shared Weather Call, nest warmer, hatch styles, mythic cosmetics, capacity upgrades. Principles: sell time, information and looks, never power or randomness for Robux ([86](86-monetization-ideas.md)). Owner 2026-10-15, not high priority | BD-153 |
| BD-148 | In review (claude/eggs-screen: one Eggs screen, single next-egg card, auto-open by rarity, AutoOpenRequiresPass flag, no forced hatching; no new art) | P0 | Merge the Eggs and Nests menus: the left-rail "Eggs" button opens the Egg Nests screen (nest-first). Layout: five nest slots in a row, each with the egg-nest icon (docs/77 egg_nest, empty slots show a dim empty nest), a 3 h timer on the one being opened, "Queued" on the others, tap a READY nest to open it (reveal sequence, PR hatch-sequence). Header keeps "Nests 2/5" and the luck line. Remove the separate NESTS rail button; leftover banked run eggs stay as an "Eggs waiting: N" row with the HATCH button below the nests so nothing is lost. Owner 2026-10-14 | BD-090, BD-147 |
| BD-147 | Backlog | P0 | Run rewards are nest-first: every finished run gives one egg nest, big runs give more (tiered by food: e.g. 1 nest at 500 food, 2 at 2,000, 3 at 5,000; numbers PROVISIONAL, balance in docs/71), capped by the 5-slot storage; each nest opens on a 3 h timer, one at a time, so a full set is 15 h. A run that would overflow storage shows "Nest storage full" and keeps the extra as a banked egg reward instead of losing it. Add the economy check (verify_nests.py) and a kid-short result line on the run summary: "+2 Egg Nests!". Needs Znypr to confirm the nest tiers | BD-090 |
| BD-146 | Backlog | P0 | Selecting a new dino spawns it with the old primitive "balloon" visual on top (two visuals stacked). Remove the old DinoVisual before the new one attaches, never draw the procedural fallback when a real model is loading (show nothing or a short fade until it is ready), and recheck after the mesh-budget fix (PR #49). Owner screenshot 2026-10-14 | BD-044 **2026-10-15 note:** cause not reproduced or fixed (suspects: server DinoVisual shell vs client LocalMeshVisual in ResourceVisuals.client.luau when the client mesh clone fails); needs a Studio repro |
| BD-145 | Review / test | P1 | Dino Index placeholders for undiscovered dinos render as a black box instead of the species silhouette. Show the real species shape, dark and soft-edged, with "???" so kids can guess what is coming; works for the 17 authored-mesh species and the 6 packaged meshes | BD-146 **2026-10-15:** code already renders dark silhouette viewports with "???" name/rarity (FusionSelection.indexCard) on Index cards and species page; not visually re-verified this pass (no screenshot tool for in-game GUI) |
| BD-144 | Backlog | P1 | Potion button icon in the main menu is still the small code-drawn bottle and looks broken at menu size. Replace it with a proper illustrated potion icon (docs/83 item 21, ChatGPT kit style), sized and centred like the other menu icons (docs/72: 48/64 px readable) | docs/83 |
| BD-143 | Backlog | P1 | Trail shop: full rework. Cards show a tiny white swoosh. Each trail gets a big animated preview (the real trail behind a running dino silhouette, or the Mythic Glow v2 ribbon looping), its class colour and rarity badge (6 classes), level requirement and speed stat in kid-short copy; locked trails show the preview dimmed with "Level 6". Uses the v2 textures and shop icons | BD-111, BD-113 |
| BD-142 | Backlog | P1 | Aura shop: cards are boring and the icon is too small. Rework with a large live preview (dino on the rotating sigil, halo and pillar per tier), tier badge (T1/T2/T3), growth bonus as "Growth +35%", and owned or equipped state; should sell the "mythic" fantasy at first glance | BD-110, BD-087 |
| BD-141 | Backlog | P1 | Condition shop displays are bugged: the five condition tiles show plain cream boxes instead of eggs with the accepted condition looks (Cracked, Dirty, Normal, Rainbow, Astra overlays, docs/39 and docs/77 IDs). Render the real egg with its overlay per tile, keep the percent line, check phone size | BD-039 **2026-10-15 note:** conditions tab now builds ModelPreview eggs per tile (Bootstrap ~line 486); not visually verified |
| BD-140 | Backlog | P2 | Crystal shop: one card per crystal pack (art that grows with pack size, crystal amount, price, bonus tag) instead of the plain row list. Robux packs are off for the playtest, so keep the tab clearly "Coming soon" or hide it there | BD-004 |
| BD-130 | In progress | P0 | Weather v2: per-event lighting grade, haze, bloom, particle rigs, bolts, lava bombs, quake shake, aurora curtains, blood moon, title card ([84](84-weather-events-v2.md)); owner feedback "weak, boring" | BD-120 |
| BD-131 | Backlog | P1 | Weather particle textures from Blender (smoke, bolt, rain, snow, ember, dust, ring, curtain flipbooks) | BD-130 |
| BD-132 | Backlog | P1 | Weather sounds: thunder, rumble, wind, lava impact | BD-130, sfx upload |
| BD-095 | Backlog | P1 | Effects Full/Lite/Off setting and distance LOD | BD-090 |
| BD-096 | Backlog | P3 | Equip shimmer audio | none |
| BD-097 | Backlog | P2 | 12-player phone perf + Studio/Android acceptance | BD-090-095 |
| BD-098 | Backlog | P3 | Prices and gates for 3 new auras | BD-092 |
| BD-080 | Backlog | P1 | Growth/Eggs HUD rework (BD-056 spec): bottom-left egg icon + EGGS N with pop, top-center slim SIZE bar; remove Island/Sanctuary text; replace three-bar icon with growth/dino icon. Roles: UI designer, gameplay eng | BD-044 |
| BD-081 | Backlog | P1 | Sound style guide + Sound lab page: listen to the 17 sounds, 2-3 variants for hatch/Shiny/fusion/shop/level-up, owner picks by ear; owner uploads, IDs filled in Sfx.luau. Roles: audio, UI (lab page) | BD-063 sfx pack |
| BD-082 | Review / test | P1 | Potion catalog 12 potions / 5 rarities, 6 offers per 2-minute window, not all available | BD-051 |
| BD-083 | Backlog | P2 | Fusion Menu density: larger text, clearer ingredient grid, readable at 1080x720 and phone landscape. Roles: UI designer | BD-065 |
| BD-084 | Backlog | P2 | Aura/trail shop: distinct aura icons and in-world previews; equipped-state feedback. Roles: UI designer, 3D artist | BD-029 |
| BD-085 | Backlog | P0 | Phone measurement pass (frame time, part counts, world art kit on) before the friends playtest. Roles: QA, tech artist; needs owner Android device | BD-019 |
| BD-090 | Review / test | P0 | Egg Nests v2 server: separate nest loot, 3 h one-at-a-time queue on server time, storage 5, luck on open, Build 020 migration (docs/71) | BD-044 |
| BD-091 | Review / test | P0 | Hidden nest drop gate: server-measured run length >= 120 s and >= 8 catches, never shown in UI (docs/71) | BD-090 |
| BD-092 | Review / test | P0 | Nests menu (7th nav button), cards with state/countdown/progress, OPEN, drop toast, run-end line; nest UI removed from Caught Eggs | BD-090 |
| BD-093 | Review / test | P1 | tools/verify_nests.py in CI: gate, exactly-once, 15 h queue, offline, cap, luck bounds, migration, budget | BD-090 |
| BD-094 | Backlog | P1 | Egg-nest icon as real art: bind resources/ui/v2/icons/egg-nest-v1.png after owner upload (replaces PLACEHOLDER code-drawn nest). Roles: UI artist, owner upload | BD-092 |
| BD-100 | Review / test | P1 | UI copy pass (docs/72): one shared time/percent formatter, remove '5m 0s' and 'x' multipliers everywhere (shops, potions, buffs, nests, weather, HUD), short child-friendly lines. Roles: UI writer, gameplay eng | BD-043 |
| BD-101 | Backlog | P1 | Potion icons as real art (replace code-drawn bottles, PLACEHOLDER): 12 potions, 5 rarity frames; brief, 2D drafts, pick, final export, owner upload. Roles: UI artist, art director | BD-082 |
| BD-102 | Review / test | P1 | UI asset production pipeline: brief template, draft/review/final/upload checklist, naming, QA at 64 px and phone size; audit existing code-drawn icons (growth tile, nest sprite, hud icons) and list which are PLACEHOLDER. Roles: art director, tech artist Registry: [docs/77](77-asset-registry.md). | BD-047 |
| BD-103 | Review / test (wired, art IDs pending) | P1 | Condition eggs in game: wire the OWNER-ACCEPTED condition looks (docs/39: Cracked dark fractures, Dirty matte smudges, Rainbow prismatic flank + stars, Astra five opal streaks + stars; transparent overlays over shell/pattern) into EggAppearance/EggPreview and the Condition Shop; first inventory which authored overlay textures exist and need upload. Do NOT redraw. Roles: tech artist, UI eng Owner uploads needed: 4 PNG overlays (Cracked, Dirty, Rainbow, Astra; 512x512 RGBA) per docs/76; renderer uses a safe fallback until IDs are bound. | BD-041 |
| BD-161 | Backlog | P1 | Anime-style 3D FX research and plan (owner priority, long-term): study how anime renders auras, speed trails, power-ups and transformations (layered smoke, rim light, shock rings, motion lines, colour grading) and adapt to Be Dino! kid-friendly look. Output: docs/87 FX direction, tech budget per effect (mobile), prototype in Studio. Roles: VFX lead, art director |
| BD-162 | Backlog | P1 | Mutation reveal animations: eggs and dinos in menus (Eggs screen, Index, My dinos, hatch reveal) play a colourful 3D mutation animation (glow, smoke, particles, depth) per mutation type; same mutation also visible on the in-game 3D dino. Depends on BD-155/156 |
| BD-163 | Review / test | P1 | Aura and trail 3D animations v3: anime-style, very colourful, depth (layered smoke, particles, ribbons, rings) for every aura/trail; shop previews animated; scales with rarity; needs particle and part budget per device. Builds on Mythic Glow v2 (#45) |
| BD-164 | Backlog | P0 | Playtest 2 (2026-10-15): camera rattles while walking over terrain. Likely the camera follows the physics-jittering root over the new bumpy terrain and hills. Fix: smooth/decouple camera target (spring or damped follow of a filtered root position), check terrain roughness and Humanoid hip height, compare flat vs hilly. Acceptance: no visible camera shake when walking on any biome at 60 and 30 fps |
| BD-165 | Review / test | P0 | Catch count 10x too high (owner 2026-10-15): about 52 catches after 3-4 min and ~700 growth, owner expects about 5. Supersedes the 2026-10-13 40/500 rate (docs/59): new target about FoodCatchRate = 4/500 (500 food -> ~4-5 eggs, 5,000 food -> ~40-50), egg-value and rarity weighting must be rebalanced upward so fewer eggs still feel special. Update AGENTS.md examples, docs/59, tests and the Eggs screen batch sizes (47 waiting). **Done in branch claude/catch-rate-matte (docs/89): FoodCatchRate 4/500, run cap 50, gentler boost, crystals/nests/XP keep per-run outputs; fusion pacing now 10x slower; Studio/phone and the Eggs screen batch sizes not verified.** |
| BD-166 | Backlog | P0 | Loud sharp sound at run end (probably crystal reward or run_end cue) feels annoying and does not fit. Identify which cue fires (run_end, shop_buy, level_up, crystal pickup), reduce, soften and shorten, replace with a gentle reward chime (BD-081 real sound pass), add a per-category volume and a mute in Settings. Related: global Sfx gain already halved in #70 |
| BD-167 | Backlog | P1 | World density v3 (owner): even more vegetation, more food items, more types of stones, trees and bushes. Needs new Blender kit pieces (3+ rock variants per biome, 4+ tree species incl. birch/palm/dead/pine variants, more bushes, flowers, mushrooms, reeds) plus food variety (more fruit/berry/mushroom kinds), within the part budget and phone limits (World v2 is already ~7,400 parts). Pair with BD-168 |
| BD-169 | Review / test | P0 | Eggs page redesign (owner): replace the plain white ellipse with the official Blender egg render shown on its tile-floor background; use the single-egg nest PNG (egg-nest-single-v1) in the same page. Layout: big hero egg on tile floor, nest strip, rarity/condition chips, OPEN and AUTO. Needs a drafted brief per docs/72 (ChatGPT/Blender art), then a UI pass. **2026-10-15 (claude/eggs-page-v2):** Eggs page rebuilt: hero = official Blender egg PNG (premium-egg-normal, tinted + condition overlay) on a code-built tile floor (PLACEHOLDER, real tile-floor render still needed), egg_nest_single nest slots, rarity/condition chips, timer pills. Studio screenshot not yet taken |
| BD-168 | Review / test | P1 | Performance budget for the bigger world: measure parts, memory and fps on a real phone/low-end PC; add streaming/distance culling for props and food if needed before adding BD-167 volume. **Implemented (docs/89): client distance culling, per-device `Config.WorldCulling` budget, admin readout; desktop Studio numbers only, real phone still to measure** |
| BD-170 | Review / test | P0 | Hatch flow bugs (owner): (1) clicking Open first shows a dino cycling through patterns, which is misleading and must not exist: Open starts the egg opening animation immediately; (2) the cube egg is still shown, use the real egg model or Blender image; (3) tapping Next egg drops the player back to the Eggs screen instead of staying in the opening sequence until the batch ends or the player exits |
| BD-171 | Review / test | P0 | Paint-bucket colour reveal (owner design): the egg starts colourless and without pattern; a bucket on the left splashes and colours the whole egg (shows the colour name and its rarity tier, e.g. Mythic); a bucket on the right splashes and reveals the pattern (name and rarity); each bucket opens quickly. Gives colour and pattern more weight in the hatch. Sound cue per splash, tier-coloured bursts. Depends on BD-170 and the pure HatchTimeline |
| BD-172 | Review / test | P1 | Colour growth bonus (owner proposal): colour gives a small permanent growth factor, about 1-5% by colour rarity (black 5%, double black 10%). Needs the colour rarity ladder, stacking rule with potions/fusion, display in the Index, balance against GrowthCap and server-side validation. PROVISIONAL numbers **2026-10-15:** implemented, PROVISIONAL: +1% per colour tier (Common 0 .. Mythic 5), primary + secondary summed, cap +10%, multiplies gained growth server-side after GrowthCap from EquippedGenesJson; shown in Dino Details / My dinos ("Colour bonus +N% growth"), paint-bucket chip and Index card; docs/94, tools/verify_colour_bonus.py. Owner still to confirm numbers and fusion stacking |
| BD-173 | Review / test | P1 | Dino material: dinos currently look slightly glossy and should be matte. Gloss/metal is reserved for fused tiers (Gold, Emerald, Diamond). Set material/roughness per species mesh and pattern texture, keep Mythic Glow separate |
| BD-174 | Review / test | P0 | Egg condition shown on the dino (owner): condition (Cracked, Dirty, Rainbow, Astra...) must not appear on the dino. It only changes hatch odds, stats and how the EGG looks. Remove condition visuals/labels from dino models, Index cards and hero views; keep them on egg visuals and egg cards only. Review BD-103 wiring |
| BD-175 | Review / test | P1 | Dino Index remembers its original egg (owner): each hatched copy keeps its egg metadata (condition, nest/run, time, colours); in the dino detail screen a small egg button shows the original egg (egg picture with condition look and facts). Needs a small egg icon asset, data already planned in AGENTS (egg lineage), older copies show "unknown egg". **2026-10-15:** egg button in My dinos detail opens a popup (EggOrigin view model, verify_egg_origin.py); older copies show Unknown egg; fused dinos say they have no single egg |
| BD-176 | Review / test | P1 | Main menu icons: Eggs button must show the egg with green spots (not the plain one); Potions button shows a potion icon with a second small potion on it (bug), fix to a single clean icon. Needs the correct upload and UIIconAssets binding. **2026-10-15 (claude/ui-shop-polish):** potion double icon fixed: the menu used the composed id `potion_speed`, which draws the uploaded bottle PNG plus a native "speed" symbol on top (the second small potion); it now uses the single vector bottle `potion_speed_Rare`. **2026-10-15 update: egg_green uploaded (107129283312327) and bound to the Eggs menu button.** (older note:) `resources/ui/v2/icons/egg-green-v1.png` exists but is not uploaded or bound in UIIconAssets (no asset id), so the menu keeps the plain premium egg until the owner uploads it |
| BD-177 | Review / test | P1 | Auras shop polish: aura effect icons are too small, enlarge and give them real art; rename the menu button from "Auras" to "Shop" (or "Style Shop") since it holds auras and trails; pair with BD-143/144. **2026-10-15:** menu button renamed "SHOP"; aura card icons enlarged to fill the card (layout only, existing art). Real aura art still open (BD-142/143) |
| BD-178 | Backlog | P1 | New trail icons in the trail shop (one distinct icon per trail, 64 px readable), brief and drafts per docs/72, owner upload, bind |
| BD-179 | Review / test | P1 | Crystal shop as separate tiles/cards, one card per offer (icon, amount, price, bonus tag, hover state) instead of a vertical list; consistent with the potion shop. Replaces BD-140 scope if duplicate. **2026-10-15:** Crystals tab is a 3-wide card grid (icon grows with pack size, amount, price button, "+N% extra" tag from marketplace prices vs the smallest pack); stays "Coming soon" while CrystalPacksEnabled=false. Needs owner look on desktop and phone |
| BD-180 | Review / test | P1 | Dino Index "view dino" preview is cut off in the preview images (frame crops head/tail): fix camera framing and FOV fitting per species size, leave padding, test every species and big/small. **2026-10-15:** PreviewCamera now frames the live model's real box when it differs from the stored mesh (BIG, gene scale, small species) and pads 12% (was 4.5%); offline fit test for scaled models added. In-Studio check of every species still pending |
| BD-182 | Backlog | P2 | Project name and identity (owner 2026-10-15): choose a proper name for the whole project (game, brand, tone of voice) that fits docs/87 (calm, bubbly, friendly). Roles: creative director, lead. Shortlist 5-8 names with logo-style direction, owner picks; then update README, docs and UI title. Working title stays "Be Dino!" until then |
| BD-183 | Review / test | P1 | Vision and feel guide (docs/87) written and linked from AGENTS.md and the documentation guide; sound docs 62/63 carry the soft-sound rule. Follow-ups: audit all current Sfx entries against the guide (BD-081 real sounds), weather audio beds quiet loops, effect readability budgets in BD-161 |
| BD-181 | Backlog | P0 | Owner decision 2026-10-15: dinos have NO condition at all. Purpose of conditions (owner): make eggs look better and more complex, and limit how many dinos are given out (Cracked failure, odds); they are never a dino trait. Condition (Cracked, Dirty, Normal, Rainbow, Astra) belongs to the EGG only (hatch odds, stats, egg look). Remove it from every dino surface: My dinos "Condition" filter chip, Index cards and hero, dino details, fusion picker, fusion confirm/reveal lines and odds wheel, and stop fusion from rolling or storing a condition on the output dino (update the server trait roll, FusionService, versioned odds disclosure and tests; keep egg lineage so the original egg's condition is still visible via the Index egg button, BD-175). Keep existing saves loadable: ignore the stored dino condition field. Update AGENTS.md fusion text and docs/46 accordingly |
| BD-184 | Review / test (implemented in PR claude/rarity-curve-impl: RarityCurve.luau, tools/verify_rarity.py, tools/generate_drop_odds.py; Studio/phone playtest NOT done; owner to confirm Aurora frequency, docs/88 section Implementation status) | P0 | Exponential rarity everywhere (owner 2026-10-15, docs/88): rare dinos are too easy. One shared RarityCurve module (tier chance proportional to r^k, r about 1/4-1/6; prices grow about x2.5-3 per tier) applied to species, eggs/conditions, colours, patterns (decision pending), mutations, weather event frequency, potions, aura and trail prices, nest luck; cap run-size boost so adjacent tier ratio stays above 1/6; verifiers and a simulation test; regenerate docs/85; show rarity colour and percent in UI. Depends on BD-165 (catch count) because both change how rare a run feels |
| BD-185 | Backlog | P1 | Follow-up to BD-181: gameplay stat multipliers in ProgressionService/ProfileRepository still read the equipped hatched dino's stored egg condition (EquippedCondition attribute). Lead decision (vision: conditions only make eggs richer and limit dino supply): remove dino-side condition multipliers; conditions affect egg odds, hatch success and egg look only. Keep saves loadable (ignore the field); move any needed balance into potions/fusion tiers/colour growth (BD-172). Update docs/41, docs/43, BD-057 wording |
| BD-195 | Review / test (batch 1 exported to assets/blender/world/fbx_v2: 4 berries, 4 fruits, 2 nuts, 2 amber; mushrooms still to fix; owner must Bulk Import then bind) | P1 | World kit v2, phase 1 FOOD: hand-model more and better food (owner: too geometric, want more): 4 berry types, 4 fruits, 3 mushrooms, amber/crystal seeds, nuts, leafy shoots; organic shapes, 150-300 tris each, vertex-colour palette, soft matte look per docs/87; same names for existing ids (re-export) plus new ids; export FBX to assets/blender/world/fbx, owner Bulk Imports, bind via resources/worldkit-meshes/mesh-bindings.json + tools/bind_worldkit_meshes.py. Part of BD-167 |
| BD-200 | Review / test | P0 | Balance pass (owner 2026-10-15, docs/90): (1) growth per food halved (`Config.GrowthPerFood` 0.5, predation 12.5; eggs still use raw food; 4-minute run about 350 growth instead of about 700). (2) Fusion ladder v2: Gold = 6 Base of one species with ANY pattern (plurality pattern kept, ties -> smallest id), Emerald = 3 Gold, Diamond = 2 Emerald (same pattern); `tools/simulate_fusion_ladder.py` table in docs/90 (any Common first Gold p50 8 runs, Common Diamond about 13 h of runs). (3) Nests 6-12 eggs (was 10-15), 5 slots, 3 h. Offline verifiers pass; Studio/phone feel (size of dinos at 350 growth, 6-slot Gold UI, nest openings) NOT verified; owner may prefer 6/4/2. |
| BD-201 | Backlog | P2 | Test Cracked eggs in a normal unboosted run (owner wants a real feel later): play several 4-egg runs with the 50% Cracked / 20% hatch success rule and report how many dinosaurs a casual run really yields (model says about 2.4 per 4 eggs) and whether it feels fair; decide whether Cracked stays, softens or moves to nests/boosts only. |
| BD-186 | Backlog | P1 | Soft glow plates (docs/92 batch 1): neutral radial glow 256 px plus round, droplet and crescent variants, white on alpha, tinted at runtime from MutationLook. Blender render, Studio upload, asset-registry line. Roles: VFX artist (Claude, Blender) | BD-161, BD-162, BD-155 |
| BD-187 | Backlog | P1 | Smoke puff flipbooks (docs/92 batch 2): layered soft smoke 512 px 4x4 sheet, denser variant for ember/seismic, wispy breath variant for frost. Roles: VFX artist (Claude, Blender) | BD-161, BD-162, BD-155 |
| BD-188 | Backlog | P1 | Rings (docs/92 batch 3): soft rim ring and thin shock ring 256 px, thicker round variant for seismic. Roles: VFX artist (Claude, Blender) | BD-161, BD-162, BD-155 |
| BD-189 | Backlog | P1 | Sparkle and motif sheets (docs/92 batch 4): droplets, soft sparks, snow crystals, pebbles/dust, embers, aurora ribbons (coloured), crimson motes, 512 px sheets. Roles: VFX artist (Claude, Blender) | BD-161, BD-162, BD-155 |
| BD-190 | Backlog | P1 | Mutation badge icons (docs/92 batch 5): 7 icons 128 px (drop, bolt, snowflake, pebble, flame, ribbon, moon), readable at 64 px, replace the plain colour dot. Roles: VFX artist (Claude, Blender) | BD-161, BD-162, BD-155 |
| BD-196 | Review / test (rocks batch exported: 12 FBX in assets/blender/world/fbx_v2 world_*; bushes and ground cover still to do) | P1 | World kit v2, phase 2 ROCKS and BUSHES: 5+ rock variants per biome (boulders, slabs, basalt columns, sandstone, lava rock, crystal clusters), bushes (berry bush, flowering shrub, ferns, reeds/cattails, marsh plants), ground cover (6 flowers, clover, grass tufts). Same pipeline as BD-195, tri budget 100-400 |
| BD-197 | Backlog (lead, Blender) | P1 | World kit v2, phase 3 TREES: broadleaf, birch, palm, willow/marsh, conifer variants, baobab-style giants, burnt volcanic, dead trees; less blobby canopies, trunk flare, bark colour variation; 400-1,200 tris; giant class scaled in BiomePlacement. Pipeline as BD-195 |
| BD-198 | Backlog (lead, Blender) | P2 | World kit v2, phase 4 LANDMARKS and STATUES: dino stone statues, totems, ruined pillars, fossil rib arch, giant egg monument, obelisk, ancient arch variants; placed as rare landmarks per biome; 1,000-3,000 tris, matte stone palette |
| BD-202 | Review / test | P1 | Settings audio mixer (Everything/Sounds/Weather SoundGroups, session-only), admin panel UX (grouped, 7-event picker, Start/Stop), toast stacking and length clamp ([93](93-settings-audio-admin.md)); `tools/verify_audio.py` | none |
| BD-199 | Backlog | P1 | Phase gate for BD-195..198: each batch reviewed on a contact sheet (lead), then in-game at dino scale in a fresh playtest build, then part-budget check after BD-168 culling (phone radius). Placement and biome distribution of new ids go to BiomePlacement via a separate agent task after the owner has imported the meshes |
| BD-203 | Review | P0 | Pattern atlas: patterns and colours on ALL dinos on screen within the ~32 EditableImage cap. New pure `PatternAtlasCache` (shared per owner+genes, ref counted, warm LRU, hard cap 30), all-or-nothing per model, flat matte colour LOD when the cap is hit or the dino is far (>160 studs), maintenance loop upgrades nearest flat dinos as slots free, counters on workspace attributes `PatternImagesLive/Pinned`, `PatternCacheHits/Misses/Evictions/Denied`. Verified offline (tools/verify_pattern_atlas.py); Studio measurement in the PR | BD-150 |
