# Be Dino! documentation guide and source of truth

**Reviewed 2026-10-08 against GitHub main Build 020.** Use this navigation first when interpreting Be Dino's current rules or asking AI agents to work on the game. There are three separate meanings of "current": **owner-approved goal**, **committed code**, and **verified Studio/release acceptance**. They are not interchangeable. Do not promote a dated build/test record to active authority just because its own heading says "current".

> **Handbook first:** [114 Handbook](114-handbook.md) is the single fact-check reference (vision, feel, design language, palette, lighting, sound, asset/UI/FX quality bars, economy cheat sheet, PR checklist). Dated owner decisions: [115](115-decisions-log.md). Open conflicts and owner questions: [116](116-handbook-conflicts.md).
>
> **Helper agents:** start with the [160 Agent brief](160-agent-brief.md) (read order, decisions, git/PR workflow, safety, evidence rules, tools, reporting).
>
> **Work log:** [168 Work log and retrospectives](168-work-log-and-retrospectives.md) records how long each task took, what went wrong and the rules learned (`tools/retro_log.py`).

## Authority order (by question)

| What are you trying to learn or change? | Canonical place | Ground truth / scope |
| --- | --- | --- |
| Overall player experience and long-term goals | [README](../README.md), [game design](03-game-design.md), [reward target](09-reward-economy.md) | Latest owner intent, **not** proof of implementation |
| Feel, tone, sound, look and motion rules | [87-vision-and-feel-guide.md](87-vision-and-feel-guide.md) | Owner vision: calm, bubbly, friendly; applies to everything players see/hear |
| AI/contributor behavior | [AGENTS.md](../AGENTS.md) | Read before planning or editing |
| Tasks, priorities, dependencies and **status** | **[07-kanban.md](07-kanban.md)** | The **single live task board**; never maintain a competing board |
| Detailed owner feedback: UI, shops, 3D assets, movement, weather | [45-owner-feedback-shop-hud-world-weather-tasks.md](45-owner-feedback-shop-hud-world-weather-tasks.md) | Acceptance details for **BD-045–056**; do not mirror status here |
| Food/catch -> egg rewards | [09-reward-economy.md](09-reward-economy.md), **BD-044** in Kanban, [50-bd044-reward-loop.md](50-bd044-reward-loop.md) | Egg-per-catch + BD-045 odds implemented on the BD-044 branch (Review / test, Studio pending); not in Build 020 main |
| Implementation and release verification | [44-main-integration-checklist.md](44-main-integration-checklist.md) | **Build 020** bounded test evidence and remaining gates; does not supersede Kanban statuses |
| Current Studio instructions | [34-studio-handoff.md](34-studio-handoff.md) | Begin with its **Build 020 workflow**, not archived Build 019 steps |
| Game balance/tunables and current data IDs | [`src/shared/Config.luau`](../src/shared/Config.luau), [`ProgressionConfig.luau`](../src/shared/ProgressionConfig.luau), current Luau source | Actual committed implementation. Confirm runtime and migration separately |
| Actual Build 020 eggs, genes, species and rendering | [43-creature-runtime-integration.md](43-creature-runtime-integration.md), [41-egg-outcomes-contract.md](41-egg-outcomes-contract.md) | Source + tests over historical six-species/seven-color examples |
| Which flags the test / playtest build turns ON (newest features) and which stay off, and why | [157-playtest-profile-newest-features.md](157-playtest-profile-newest-features.md) | Owner directive 2026-10-18; `tools/release_profiles.py` is the truth; the default profile is unchanged; offline evidence only |
| Rolling back a publish, profile compatibility with Build 020, DataStore restore | [111-rollback-drill.md](111-rollback-drill.md) | Offline evidence only; real drill is owner-run (BD-320) |
| Hatch v2 (paint-bucket reveal on a 3D egg, BD-397): beat sheet, asset prompts, bake design, flag and fallbacks | [118-hatch-redesign.md](118-hatch-redesign.md) | Behind `Config.HatchV2` (false); v1 ([86](86-hatch-sequence.md)) ships |
| Every art item the owner still has to make or upload (prompts, sizes, binding) | [109-owner-art-prompt-pack.md](109-owner-art-prompt-pack.md) | Current deduplicated checklist; tracked by BD-336 |
| Checking player text is short and plain; comparing two screenshots | [162-kid-text-lint-and-screenshot-diff.md](162-kid-text-lint-and-screenshot-diff.md) | Offline tools `tools/lint_kid_text.py` (CI, baseline mode) and `tools/compare_screenshots.py` (on demand); BD-655, BD-656 |
| Artwork direction | [39-egg-appearance-shared-vision.md](39-egg-appearance-shared-vision.md), [32-artwork-guide-and-todo.md](32-artwork-guide-and-todo.md) | Aspirational asset quality and approved appearance, not automatic uploaded/runtime art |
| Shops/levels/condition mechanics | [36-crystal-shops-egg-genetics-and-progression.md](36-crystal-shops-egg-genetics-and-progression.md), [41-egg-outcomes-contract.md](41-egg-outcomes-contract.md) | Owner design vs Build 020 configuration. New condition starting odds **50/30/15/4.5/0.5** remain BD-045 |
| Security, release and paid-random restrictions | [43-player-access-and-paid-random-policy.md](43-player-access-and-paid-random-policy.md), [44-main-integration-checklist.md](44-main-integration-checklist.md), [06-roadmap-and-testing.md](06-roadmap-and-testing.md) | Keep paid flags disabled until regulatory/runtime acceptance |

## What is implemented, what is only planned?

> **New owner progression authority:** [Advanced fusion, individual dino identity and Fusion Menu](46-pattern-fusion-dino-identity-and-cosmetic-progression.md), **BD-057–065**. Ten matching inputs produce a **NEW guaranteed Gold** with **fresh donor-weighted traits**; Emerald and Diamond follow. Auras/trails bought on any consumed donor are lost, never transferred. Dedicated filtered Fusion Menu and staged reveal wheels are planned. Build 020 remains unchanged until safe code/data migration.



- **Build 020 committed**: 22 prehistoric playable/collectible models, 8 egg patterns, 9 color families, uniform mixed-color 1–99% shares, 5 conditions, ten level-gated trails, six potions, event/weather systems, server-committed run rewards, 5-second ordered hatches and current three species rarity categories **Common/Rare/Legendary**. Current tier-0 condition odds are **20/25/45/9/1**, not the new owner request.
- **Owner targets NOT yet in Build 020**: one caught egg per catch (15 eggs for a 500-food example; 150 for 5,000 food), separate five-slot bonus egg nests, five species tiers with **Uncommon/Epic** (in code since 2026-10-14, [82](82-species-rarity-tiers.md); Studio pending), new tier-0 conditions **50/30/15/4.5/0.5**, five-minute rotating limited-stock potion offers, unified Shop/category tiles/art, six-category trail presentation/art, richer environment/food, hill traction, streamlined Home, touch/HUD repositioning and richer atmospheric weather. Track via BD-044–056.
- **Verified vs unverified**: earlier disposable Studio sessions and offline tests do **not** establish newest real paid receipts, published non-owner asset access, physical phone FPS/touch, full latest multiplayer/load or persistent profile migration. Refer to the integration checklist for precise bounds.

## BD-060 foundation work

[Identity implementation and verification](47-dinosaur-identity-foundation.md)
describes the additive source foundation and unpublished memory-only integration.
This is not persistent migration or new fusion-gameplay acceptance; use Kanban for status.

## BD-057 Phase 1 fusion transaction

[Identity fusion Phase 1](49-identity-fusion-phase1.md) adds a disabled,
unpublished-memory-only 10 → 1 Gold transaction over the BD-060 sidecar, with
offline tests only. No trait odds, UI, Studio acceptance or persistent rollout.

## Where the profile transactions live (BD-607)

[ProfileRepository split](150-profile-repository-split.md): `src/server/ProfileRepository.luau` keeps the store, lease, retry, write budget, load / migration and save path, and installs the transaction groups from `ProfileEggs`, `ProfileFusion`, `ProfileObjectives`, `ProfileGifts`, `ProfileSkins`, `ProfileShop`, `ProfileCollection`, `ProfilePrefs` and `ProfileTestGrants` (same public API, function bodies unchanged). Verifiers that read the source use `tools/profile_sources.py`; `tools/verify_profile_golden.py` proves the stored profile did not change. The same document holds the size audit of the rest of `src/` (15 largest files, locals, the module size guard over server, client and shared, BD-623).

## Where the client weather code lives (BD-627)

[WeatherVisuals split](153-weather-visuals-split.md): `src/client/WeatherVisuals.client.luau` keeps the Lighting grade, atmosphere, clouds, lamp, main loop and camera shake and builds `WeatherKit`, `WeatherRigs`, `WeatherSky`, `WeatherStrikes`, `WeatherQuake` and `WeatherTitle` (same code, moved). Verifiers that read it as text use `tools/weather_sources.py`.

## Where Studio renders and how the phone is tested (BD-635)

[Virtual display and phone emulator](158-virtual-display-and-phone-emulator.md): research and owner-run steps for a screen that never sleeps (software virtual monitor, dummy plug as fallback), the free power-setting fix, a 10-minute acceptance test for the lead, and what the Studio Device Simulator, an Android emulator and a cheap real phone can and cannot prove. Nothing is installed yet; install steps are owner actions.

## Where git worktrees may live and how they are cleaned (BD-660)

[Worktree hygiene](170-worktree-hygiene.md): worktrees only in `.claude/worktrees` (or the session scratchpad), a helper removes its own after its PR merged, the lead runs `python tools/worktree_hygiene.py clean --go` weekly. The same document lists the 13 worktrees left because of unsaved files, for the owner to decide.

## Historical documents: keep for traceability, not as active instructions

Do **not** delete build snapshots or test evidence just to make them look current. Retain their specific facts and outputs, with clear historical notices. Older strings like "this is the current build", "persistence is not implemented", "GitHub main is Build 013", "three-species only" and "60-second newly earned egg timing" are scoped to their original dates/builds.

| Historical grouping | Main documents | Why retained |
| --- | --- | --- |
| Initial September scope, architecture and alpha simulation | [01-project-brief](01-project-brief.md), [04-architecture](04-architecture.md), [05-asset-pipeline](05-asset-pipeline.md), [13-persistence contracts](13-persistence-remote-contracts.md), [15-economy simulation](15-economy-simulation.md) | Earlier owner/test decisions and security/math evidence |
| Early procedural/redesign/builds 013–016 | [23-original asset manifest](23-original-asset-manifest.md), [24-visual kit](24-visual-kit-test.md), [25-redesign](25-redesign.md), [26-build014](26-redesign-test.md), [27-build015](27-mountain-island.md), [28-build016](28-ui-overhaul.md) | Audit/source lineage, no longer current art or UX requirements |
| Builds 017–019 handoffs and feature acceptance | [30-build017](30-build017-and-progression-roadmap.md), [31-build018](31-build018-progression-test.md), [35-events](35-event-mutations-and-visual-upgrade.md), [37-hatching](37-hatching-traits-and-leaderboards.md), [38-motion](38-ui-motion-and-performance.md), [39-shops acceptance](39-crystal-shops-and-genetics-acceptance.md), [42-multiplayer](42-live-multiplayer-test.md) | Dated test results and implementation history, not proof new work is done |
| Build 020 snapshot | [44-main integration](44-main-integration-checklist.md), [43-creature integration](43-creature-runtime-integration.md) | The **current reviewed** GitHub build snapshot; advance on a new build rather than overwriting older evidence |

## Duplication policy

- **One advanced fusion/individual-dino specification**: [`46-pattern-fusion-dino-identity-and-cosmetic-progression.md`](46-pattern-fusion-dino-identity-and-cosmetic-progression.md), BD-057–065, including pattern research, ingredient-weighted trait RNG and wheel presentation. Keep the older 50/50 Build 020 recipe as a historical/current implementation description, not the approved new goal.


- **One status board**: `07-kanban.md`. Keep detailed checklists in their specialized spec and link them; do not duplicate 12-item acceptance lists in the board.
- **One owner-target reward document**: `09-reward-economy.md`. Historical direct-copy `N(c)=c` arithmetic lives in `15-economy-simulation.md`; it must never be silently reinstated.
- **One consolidated egg appearance guide**: `39-egg-appearance-shared-vision.md`; the general artwork production guide `32` covers export/asset workflow. `41` covers **mechanical** probabilities, saved outcomes and paid-random disclosure, not art taste.
- **One active Studio entry point**: current section of `34-studio-handoff.md`; older build steps stay in marked historical subsections.
- **Use config/source for shipped mechanics**; use owner-target specs for intent; use Studio evidence for acceptance. If contradictory, raise or record the conflict and update the appropriate source of truth rather than copying a new value into every document.

## Maintenance checklist

1. Record date, branch/commit/build and whether a statement means **implemented**, **proposed** or **verified**.
2. When altering current balance, update actual source, saved-version migrations, outcome disclosure and tests **before** calling a target live.
3. If a newer build replaces Build 020, refresh README + this guide + current handoff + integration checklist together.
4. Update the task status **only** in Kanban, including evidence link; older milestones keep historical snapshots.
5. For shop art and Blender assets, source/render, approved preview, uploaded owner-bound IDs, integration and device verification are different stages.
- [61 Release-readiness audit](61-release-readiness-audit.md): R/Y/G verdicts, ranked polish tasks, audio plan and live Studio checklist for the private playtest.
- [64 Feature intake template](64-feature-intake-template.md), [65 notifications](65-intake-notifications.md), [66 mini objectives](66-intake-mini-objectives.md): pre-build checklist and two applied proposals (BD-066 to BD-078, Backlog).
- [70 Aura and trail concepts](70-aura-trail-concepts.md): three style directions with draft boards (`docs/evidence/2026-10-14-aura-trail-concepts`), Roblox feasibility, effect budget and BD-086 to BD-098 (Backlog).
- [79 Owner admin panel](79-admin-panel.md): owner-only runtime sliders (food worth, growth, run speed) and weather controls for playtests (BD-120).
- [77 Asset registry](77-asset-registry.md): every runtime art asset with repo file, Roblox ID, user and status; archive location of older revisions.
- [104 Cave hub design](104-cave-hub-design.md): owner target (2026-10-16) for the Sanctuary as a big cave with physical shops and teleport-to-station menus; layout, build method, lighting, lava FX, teleport rules, asset prompts, migration flag and BD-279 to BD-294 (design only, nothing built).
- [95 Owner upload guide](95-owner-upload-guide.md): how the owner uploads art and meshes to Roblox. Status: current.
- [96 Fusion Menu v2](96-fusion-menu-v2.md): big cards, tappable slots, one FUSE button (PR #116). Status: built, Review / test (BD-217/BD-065), Studio/phone pending.
- [97 Dino skins](97-dino-skins.md): owner decisions for base look plus Plushy/Clay/Bricks skins. Status: decisions recorded, implementation not started (BD-224).
- [98 No more cubes](98-no-more-cubes.md): live EditableMesh templates, mesh guard, 2D fallbacks (PR #117). Status: built, Review / test.
- [99 Mutation audit](99-mutation-audit.md): event mutation audit and gaps G1-G5. Status: audit done, follow-ups BD-235..237 Backlog.
- [100 Species visual reference](100-species-visual-reference.md): look, class and mesh-generator prompts per species. Status: current reference (BD-238).
- [101 HP, combat, classes, animations](101-hp-combat-classes-animations.md): current source of truth for combat. Status: pure modules, server and placeholder HUD built behind `Config.CombatEnabled=false`; offline tests only, nothing playtested.
- [102 QA playtest pass 2026-10-16](102-qa-playtest-pass-2026-10-16.md): findings BD-253..262, evidence in `docs/evidence/2026-10-16-qa-pass`, `2026-10-16-qa-p2`. Status: findings; fixes Review / test.
- [103 UI research](103-ui-research-popular-games.md): settings spec and BD-263..274. Status: partly built (settings v2, shop card, odds button), Review / test.
- Evidence folders added since 95 (all under `docs/evidence/`, 2026-10-16): `fusion-menu-v2`, `no-more-cubes`, `egg-preview-light`, `lowpoly-spike`, `combat-wiring`, `cave-shell`, `cave-lighting`, `menu-fixes`, `menu-screenshots` (BD-300..304), `qa-pass`, `qa-p2`; plus 2026-10-15 kit renders `food-kit-v2.png`, `landmarks-kit-v2.png`, `trees-kit-v2.png`. Status: evidence snapshots, not acceptance on their own.
- **Superseded**: the BD-254 "calm, bubbly Sanctuary" polish in `07-kanban.md` (open PR #147, never merged) is superseded by [104](104-cave-hub-design.md). Do not merge or extend it.
- [105 Low-poly dinos: gene patterns and fused-tier looks](105-lowpoly-patterns-and-tiers.md): 3D procedural pattern bake per part, image budget, Gold/Emerald/Diamond on low-poly (flag off), Studio contact sheet and critique (2026-10-16).

## Session log 2026-10-16

PRs #123..#174 by theme (all flag-off or docs; none is playtest acceptance):
- FX and textures: #118, #119, #120, #122 (FX v3 flipbooks and binds); #124, #125, #128 (shop card FX, condition eggs, aura cards); #123 (potion icons).
- No more cubes and fusion UI: #117 (live mesh templates), #116 (Fusion Menu v2), #121, #115 (dino skins docs).
- World meshes: #139 (generated meshes in biome placement).
- Combat and classes: #129..#131, #135 (design), #138, #140, #143, #157, #168, #170 (pure modules, server, HUD, NPCs, QA).
- Low-poly dinos: #134, #142, #145, #149, #152, #165, #169, #171.
- QA and menus: #141, #144, #146, #153, #155, #162, #164, #166, #167.
- Reward and mutation audits: #126, #127, #132, #133, #136, #137.
- Research and cave design: #148, #150, #151, #173 (friends playtest audit).
- Cave hub build (Config.CaveHub off): #154, #156, #158, #159, #160, #161, #163, #172, #174.
