# Kanban and task specifications
Updated 2026-10-08. This file is the canonical task tracker.

Build 020 and UI-motion history are integrated for promotion to GitHub main.
[Main integration checklist](44-main-integration-checklist.md) records what is new
since main's Build 013, current bounded acceptance and open release gates. It is
an integration snapshot, not a second task board. GitHub promotion does not publish
Roblox or certify devices, persistent profiles or paid purchases.

Build 005 PvP/run-ending tests 1–9 passed. Build 006 persistence tests 1–10 passed. Build 007 lease/stale-writer verification and restart persistence passed in the new private test experience. BD-011 is Done. Build 008 collection/equip passed all 8 runtime tests. BD-012 is Done. Build 009 earned chest queue passed all 8 runtime tests. BD-013 is Done. Build 010 Gold mutation passed all 8 runtime tests. BD-014 is Done. Build 011 core UI passed all 8 desktop/phone-emulator tests. BD-015 is Done. Build 012 security/multiplayer regression passed all 8 runtime tests. BD-018 is Done. Build 013 original visual kit is ready for testing. Mobile remains untested.

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
| BD-017; BD-019–022; BD-035; **BD-044–056** | BD-027 | BD-043 | BD-006 mobile; BD-016 visual kit; BD-023–026; BD-028–034; BD-036–042 | BD-004 private-place record | BD-001, BD-002, BD-003, BD-005, BD-007, BD-008, BD-009, BD-010, BD-011, BD-012, BD-013, BD-014, BD-015, BD-018 |

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
| BD-034 | Review / test | P1 | Event-mutated eggs, cosmetic trails and textured visual upgrade | BD-028, BD-031 |
| BD-035 | Backlog | P1 | High-quality modular Blender egg/pattern/condition/mutation render passes | BD-024, BD-034 |
| BD-036 | Review / test | P1 | Run-end crystal rewards, crystal unboxing and Robux crystal packs | BD-028, BD-011 |
| BD-037 | Review / test | P1 | Crystal-priced random eggs feeding the existing hatching queue | BD-036, BD-013 |
| BD-038 | Review / test | P1 | Persistent account levels and ten level-gated speed/VFX trails | BD-028, BD-029, BD-034 |
| BD-039 | Review / test | P1 | Crystal-priced five-minute Speed Potion integration | BD-032, BD-036 |
| BD-040 | Review / test | P1 | Escalating Condition Shop, weighted egg conditions and stat/hatch effects | BD-036, BD-037 |
| BD-041 | Review / test | P1 | Two-colour egg genetics, Normal/Big eggs and independent shiny sparkle | BD-035, BD-037 |
| BD-042 | Review / test | P1 | Five-second ordered hatches, Shiny/BIG and map leaderboards | BD-013, BD-034 |
| BD-043 | In progress | P1 | UI animation, feedback, loading and preview performance | BD-015, BD-042 |
| BD-044 | Backlog | P0 | Replace direct-copy rewards with caught-run-egg hatching, crystal payout and separate five-slot egg nests | BD-011, BD-013, BD-036, BD-042 |
| BD-045 | Backlog | P0 | Rebalance condition odds to new owner starting distribution and update condition-upgrade/disclosure flow | BD-040, BD-044 |
| BD-046 | Backlog | P1 | Rename Auras nav entry to Shop with crystal icon; crystal HUD opens same Shop | BD-029, BD-036, BD-043 |
| BD-047 | Backlog | P1 | Illustrated Crystal Shop category tiles, green-spotted egg icon, larger aura previews and leading tab icons | BD-046, BD-035 |
| BD-048 | Backlog | P1 | Trail icon art, Blender world VFX and six rarity categories across ten trails | BD-038, BD-034 |
| BD-049 | Backlog | P1 | Blender trees, vegetation, rock variants, map landmarks and optimized biome placement | BD-016, BD-053 |
| BD-050 | Backlog | P1 | Blender pickup/food model variants with intact food rewards and server validation | BD-008, BD-049 |
| BD-051 | Backlog | P1 | Rotating five-minute Potion Shop offers, rarity-weighted selection and 1–3 limited stock | BD-032, BD-039 |
| BD-052 | Backlog | P1 | Single bottom-center Home with confirmation and no three-second exit channel | BD-009, BD-044 |
| BD-053 | Backlog | P0 | Fix sliding and hill-climb movement on mountainous terrain | BD-006, BD-008 |
| BD-054 | Backlog | P0 | Responsive phone/tablet touch-zone navigation/control placement and safe insets | BD-052, BD-046, BD-056 |
| BD-055 | Backlog | P1 | Complete sky, atmosphere, cloud, particle and audio effects for all weather events | BD-031, BD-034 |
| BD-056 | Backlog | P1 | Top-center growth metric and bottom-left egg-icon catches-only HUD | BD-044, BD-054 |

### BD-044: Owner-approved reward-loop correction (2026-10-08)

**Status: Backlog; design confirmed, runtime NOT changed. P0 before economy/public release.**
The newer owner's reward intent supersedes the 2026-09-17 test economy's `N(c)=c` immediate dinosaur copies and the 10/100/500 catches -> 1/2/3 extra-egg thresholds. [Canonical target and illustrated distributions](09-reward-economy.md) and [AI/contributor instructions](../AGENTS.md) define the intended behavior; [actual Build 020](44-main-integration-checklist.md) is the separate implementation record.

**Acceptance checklist (do not check off from documentation alone):**

- [ ] 500 **food** points -> example 15 catches -> **15 banked eggs** (NOT 15 guaranteed Compy copies + 1/2 threshold eggs). 5,000 **food** points -> example 150 catches -> **150 run eggs**; distinguish from historical 5,000 catch-score cap and test 0/negative/overflow values.
- [ ] Run return/death/disconnect settle each egg exactly once, with immutable random species/rarity/condition/genetic/trait outcomes, saved batches, correct event provenance, Cracked failure and legacy data migration. No direct-copy double credit or preserved duplicate exploit.
- [ ] Hatch every run egg individually in increasing species rarity, at ~5 seconds/egg in initial prototype. 15-egg and 150-egg cases: clear progress, close/skip/resume, mobile responsiveness, cancellation and performance. Define 150-egg pacing alternative with owner before launch.
- [ ] 15-egg illustrative species rarity result can include 11 Common/4 Uncommon; 150-egg illustrative result can include 80 Common/50 Uncommon/17 Rare/3 Epic. These **are not mandatory quotas or fixed odds**; eligibility/distribution must be configurable and fair.
- [ ] Grant crystals independently from catches and map pickups; prototype example **30** run crystals at 500 food is assistant illustrative ONLY, **220** at 5,000 food is the owner's illustrative example. Define/approve actual earning and crystal-box rules separately.
- [ ] Model **bonus nests** as separate rewards from individual caught eggs, with **five nest inventory/claim spots**, not the existing ordinary egg queue capacity. Example: 1 nest from 500 food; 6 nests offered from 5,000 food, only 5 claimable if all five slots are free. Explicitly resolve where the sixth offered nest goes (pending/blocked/expiry) and prevent silent reward loss; define nest timing/content.
- [ ] Retune and test quantity (currently 1/2/3 copies per egg), species odds, egg outcomes/disclosure, fusion pacing, 150+ egg batch payloads and reward caps. Old `tools/economy_sim.py`, `tests/test_economy.py`, Config thresholds and Studio fixtures remain **historical tests** until deliberately replaced.
- [ ] End-to-end multiplayer/rejoin/persistence, queue limits, migration, real-device interaction, UI and no paid-random regression verified with evidence before marking done. Do not touch persistent profiles or enable paid random items without a separate release review.

### BD-045–BD-056: Owner UI, economy, terrain, artwork and weather feedback (2026-10-08)

**All tasks below are Backlog/TODO, not shipped or acceptance-tested.** Detailed research, source documents, implementation notes, individual subtasks, dependencies and measurable acceptance are in [the canonical feature specification](45-owner-feedback-shop-hud-world-weather-tasks.md). This task board remains the single source of task **status**. Existing BD-028–043 functionality is useful foundation, not evidence these refinements have shipped.

#### Economy and randomized shops

- [ ] **BD-045 — condition odds (P0).** Starting odds **Cracked 50%, Dirty 30%, Normal 15%, Rainbow 4.5%, Astra 0.5%**, sum 100. Subtasks: config/integer weights; redo six upgrades with owner-reviewable current/next values; preserve 20% Cracked hatch success and saved egg results; update paid-odds disclosure/enumeration and 15/150-egg tests. At tier 0, **40% expected egg failure**, which needs explicit playtest review, not silent balance changes.
- [ ] **BD-051 — rotating Potion Shop (P1).** Subtasks: every **300 seconds** server-set subset of available potions; rarity-weighted selection; each potion **1–3 purchasable units/player with 1 most likely** (numeric probability TBD); atomic purchases, stock/offer version and reconnect safety; **next-refresh countdown** and **“Potion Shop refreshed”** popup; preserve owned potion inventory, live buffs and paid-random restrictions.

#### Shop navigation and presentation

- [ ] **BD-046 — Shop entry (P1).** Subtasks: replace misleading **AURAS** navigation label with **SHOP**; replace nav image with **existing crystal icon**; keep AURAS internal category; make top-right wallet counter open same shop; test nav/history/modal, touch and controller.
- [ ] **BD-047 — Shop artwork & layout (P1).** Subtasks: Crystal Shop **landing tiles with unique images**, not a horizontal category row; preserve in-shop Auras/Trails/Eggs/Conditions/Crystals tabs; put **small leading icons** on tabs and identify needed new icon masters; replace Egg Shop product icon with approved **green-spotted egg** art (verify new asset, upload, bind); enlarge/center aura card previews with the existing reusable layered ring/fossil assembler; QA prices and item states on phone/tablet/desktop.

#### Trail, world and collectible assets

- [ ] **BD-048 — trail rarity/render/art (P1).** Subtasks: audit existing TEN trails and THREE current rarity names; propose six rarity classes across ten products for approval; make original icons and consistent six-tier borders; Blender editable motion/ribbon/particle effect assets and per-trail previews; integrate optimized world trails, preserve level/speed and owned IDs; performance and reduced-effects QA.
- [ ] **BD-049 — map variation (P1).** Subtasks: Blender multiple tree silhouettes/sizes, ground vegetation, ferns, bushes, boulders and rock forms; authored landmarks/statues/nests/arches; repeatable biome-aware seeds/placement and wide walkable corridors; colliders/LOD and owned mesh imports; actual Studio + device load.
- [ ] **BD-050 — food props (P1).** Subtasks: Blender food berries, fruit, food egg, amber and variants; shared source meshes/materials and IDs; readable world-size scaling and placements; **preserve +1/+4/+15/+50 values and distinction between amber food vs wallet crystals**; server pickup/respawn/multiplayer and mobile tests.

#### Traversal, home and HUD

- [ ] **BD-053 — slope movement (P0).** Subtasks: reproduce slide/hill-climb failure with recorded coordinates; investigate controller/friction/slope (prototype **MaxSlopeAngle 46°**), root collider and animation pivot; repair traversable terrain/traction without PvP or movement exploit; test incline/decline, jump/leap, buffs, BIG, terrain types and server reconciliation.
- [ ] **BD-052 — Home return (P1).** Subtasks: consolidate duplicated buttons to one **middle-bottom home icon**, keep it outside touch controls; clear **Return to Sanctuary / Cancel** confirmation; remove old **three-second** exit channel after confirmation; preserve server-authoritative death/exit ordering and exactly-once rewards; test in-run/sanctuary/phone/controller.
- [ ] **BD-054 — phone/tablet (P0).** Subtasks: research thumb/reach zones and documented Roblox device safe insets; restructure controls away from inaccessible absolute bottom and joystick/jump areas; independent landscape phone/tablet layouts, 44–48px target, correct PreferredInput/gamepad transitions, screenshots with hitboxes and physical-touch tests. Refer to [Roblox UI guidance](https://create.roblox.com/docs/ui/position-and-size) and [mobile input](https://create.roblox.com/docs/input/mobile).
- [ ] **BD-056 — live HUD (P1).** Subtasks: show **Growth/Size only at top center**; bottom left shows **egg icon + Eggs Caught N only**, outside thumbstick safe area; remove duplicated Growth readout; reconcile displayed eggs with BD-044 actual earned-egg count, preserve event bonuses and 0/15/150+ cases, test camera/modal overlap.

#### Weather visuals and world ambience

- [ ] **BD-055 — full weather environment (P1).** Subtasks: map all seven current events plus Clear to reusable **Lighting, Atmosphere, Terrain.Clouds, Sky/ColorCorrection** visual presets, tween/restore safely; camera-local bounded rain, storm lightning, snow, volcano ash/orange sky, aurora curtains, earthquake dust and blood-moon visuals with audio where appropriate; preserve server weather/RNG/mutation tags; join/exit/respawn/reduced-effects and 8–12-player/mobile QA. Icons/timers are already present and alone are insufficient.

**Scope rule:** New tasks must not be marked Done from written specifications, AI renders, a working Build 020 feature with a similar name, or unverified Roblox model IDs. All status changes require evidence in this board.

### Crystal Shops and Genetics, 2026-10-08 (BD-036–041)

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

**In progress — UI-motion history/evidence reconciled into Build 020; latest device checks pending.**
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

### New proposed shop/egg systems, 2026-10-08 (BD-035–041)

**Shared visual reference:** [Egg appearance vision](39-egg-appearance-shared-vision.md) consolidates the owner review and archives pattern/color/condition/aura previews. Matte shell, tile/grass grounding and reusable Cracked/Dirty overlays are accepted directions; exact art-authoring weights are provisional; latest seven engulfing smoke/anime auras are review drafts. Rainbow/Astra rework resumed and the owner accepted Astra's brighter curved-vertical opal direction. [Combined-condition review evidence](evidence/2026-10-08-egg-condition-combinations/README.md) tests selected patterned/color/condition/Magma stacks. Local 1024-to-512 RGBA/alpha and camera/mesh checks are authoring evidence only; they do not close missing authored-runtime layers, uploads or Studio/device acceptance. Existing gameplay acceptance is recorded separately above.

- [ ] **BD-035:** Replace draft/Microsoft-Paint-quality egg art with a high-quality Blender master, fixed mesh and camera; export true transparent 512x512 RGBA base, patterns, conditions and separate mutation passes. Prove matching masks/preview alignment, then test in Studio. No finished art is claimed.
- [ ] **BD-036:** Add crystals awarded/unboxed at run end alongside map pickups; design Robux crystal packs with server-authoritative idempotent receipt grants, persistence and purchase restrictions. Crystal award quantities remain configurable.
- [ ] **BD-037:** Let players buy random eggs with crystals to join sequential hatching without losing purchases on full queues. Validate random-paid-item policy/disclosure before monetized release.
- [ ] **BD-038:** Replace/extend three cosmetic trails with **ten** crystal-priced tiered coloured walking trails, from free normal white to highest **Astra glitter**. Prices, speed buffs and required **persistent account levels** increase by tier; cap aggregate speed and migrate existing ownership.
- [ ] **BD-039:** Crystal-priced 5-minute Speed Potion, reusing the existing potion inventory/expiry and server multipliers; avoid duplicate shops.
- [ ] **BD-040:** Condition Shop progressively reduces Cracked odds/increases Rainbow/Astra odds with escalating level and crystal gates. User-confirmed 2026-10-08: Cracked **20% hatch success** and **80% speed/growth** if successful; Dirty 80%; Normal 100%; Rainbow 120%; Astra 180%. Factors affect **both movement speed and growth intake**, before final shared caps. Implementation, failed-hatch consolation and interaction tests remain Todo; this specification confirmation is not an acceptance pass.
- [ ] **BD-041:** Two server-selected rarity-weighted egg colors and saved random visible coverage share, inherited by dinosaur; preserve tonal pattern contrast for matching genes. Vivid red is rare and pure black exceptionally rare. Reconcile percentage endpoints with that hierarchy; the shared art draft uses 1–99% for mixed genes and 100% for matching pairs, not approved public odds. Independent Normal/Big eggs (Big visuals 1.2x proposed, same stats), Shiny sparkle and immutable persistence remain in scope; see the existing tested BIG baseline before changing scale.

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
