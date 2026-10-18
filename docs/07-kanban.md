# Kanban and task specifications
Updated 2026-10-18. This page is the entry to the canonical task tracker. **The task rows are NOT in this page any more: one file per task in `docs/kanban/rows/` ([191](191-kanban-rows.md)).** Intro, owner decision logs and notes stay here.

**Current scope: GitHub main Build 020.** Use [the documentation authority guide](00-documentation-guide.md) to distinguish owner targets, committed source, historical build evidence and Studio/release acceptance. [Build 020 integration checklist](44-main-integration-checklist.md) records bounded passes and remaining gates, but **this file alone owns task statuses**. GitHub integration does not publish Roblox or certify paid items, physical-device performance or newest persistent migration.

**Historical milestone summary:** Builds 005â€“013 established PvP, storage, collection, old direct-copy reward tests, earned chests, Gold and original procedural visuals. Those older checks are *not* proof the latest reward vision is implemented. For actual per-build acceptance consult the dated sections and historical evidence below. Physical-phone/mobile acceptance remains open, though earlier phone-emulator checks passed.

## Board counts

Task counts are **not stored here**. A generated table inside the one file every PR edits conflicted on almost every merge, and the refresh bot could not push to the protected `main`. Run `python tools/board_summary.py` for the live table; CI also prints it in each run's job summary. Never paste counts into this file.

**Next 10 P0/P1 Backlog items (hand-ordered 2026-10-16).** Order follows the owner vision ([114](114-handbook.md) s1.1: food, eggs, growing; short runs plus a hatch party; cosy cave hub) and the session-1 readiness list ([125](125-friends-playtest-go-no-go.md)). New gifting rows BD-450..453 (open PR #288) and the cave rework (open PR #286) are not on main yet; add them here once merged.

1. **BD-317** (P0) Friends playtest gate: owner publish, rollback drill, smoke run, two-player check.
2. **BD-085** (P0) Phone measurement pass, the biggest unmeasured risk in 125.
3. **BD-322** (P0) docs/107 s5 phone checklist, run together with BD-085.
4. **BD-293** (P0) Cave acceptance on a phone and with 12 players (the cave hub is on in the playtest profile).
5. **BD-441** (P0) Playtest feedback button hidden until the first run ends.
6. **BD-364** (P1) Owner runs the multi-client script (docs/111 s5) and records the result.
7. **BD-319** (P1) Re-test multiplayer after the settings, odds panel, culling and mesh changes.
8. **BD-208** (P1) Eggs page uses the official egg art (first-session screen).
9. **BD-296** (P1) Cave look pass against docs/87 (calm, bubbly, readable); revisit after cave rework #286.
10. **BD-021** (P0) Observe the community test and triage (follows BD-317).

## Owner decisions log 2026-10-16

Dated decisions from this session (sources in brackets). "Lead decision" means made on the owner's behalf; the owner may overrule. Everything below is OFF by default behind flags and is **Review / test or Backlog, never Done**: no phone, 12-player or owner-playtest evidence exists yet.

- **Low-poly base dinos** (BD-224, BD-225, BD-232): one faceted low-poly base look per species from Roblox's mesh generator, split into parts; first spike Compy/Raptor/Triceratops, registry now covers all 22 species. Flag off. Skins (Plushy, Clay, Bricks) are a later paid cosmetic layer with gentle defeat animations ([97](97-dino-skins.md)).
- **Generated meshes only**: no code-built 3D models as final art; 2D art from Blender or the owner ([87](87-vision-and-feel-guide.md), [72](72-ui-copy-and-asset-standards.md)). **Scoped exception (owner 2026-10-16, BD-462, [140](140-tree-quality-test.md)):** the three Blender-scripted V3 trees (broadleaf, conifer, palm) are approved as final world art after the owner saw the renders; the exception covers ONLY those three meshes and is not a general permission. The owner also allows Blender for world and colossal-tree art.
- **Classes** Ground / Fly / Water plus a fourth, Armored (Ankylosaurus, Sauropelta, Styracosaurus; Triceratops/Stegosaurus stay Ground) (BD-231, BD-232; [101](101-hp-combat-classes-animations.md) s16). Roster target 5 Fly + 5 Water + 5 more Ground.
- **Secret silly bird dinos** (Chickosaurus, Pigeon, Dodo, Duck, Penguin) stay hidden secrets (BD-228); more silly ones are paused. Compy stays the first dino.
- **HP combat** replaces instant "bigger eats smaller" (BD-230): hearts/bars only, no damage numbers, PvP on in the arena for everyone (~~Peaceful option~~ SUPERSEDED 2026-10-16, docs/115), no revive in v1, defeat keeps everything earned, assist bonus only (docs/101 s16). `Config.CombatEnabled=false`.
- **Cave hub**: Sanctuary becomes a big cave (260 x 220) with physical shops, teleport-to-station menus (default ON, Settings toggle to walk), in-run rail dims DINOS/EGGS/FUSION/SHOP, POTIONS/SETTINGS stay usable, lava scenic only, existing 2D hatch reveal kept ([104](104-cave-hub-design.md) s15.1/16). `Config.CaveHub=false`. BD-254 / PR #147 (never merged, still open) is superseded by docs/104.
- **UI research** ([103](103-ui-research-popular-games.md)): settings menu v2, shared shop card, odds buttons, Index progress (BD-263..274).
- **Process**: keep 3-4 agents running; QA agents must not touch Place1.rbxl; flag-off-by-default for combat, cave and low-poly.
- **Giant dinos vs jungle** (docs/139, owner answers 2026-10-16): Q1 KEEP current growth pacing (a normal 5-minute run stays at size 1.5; gigantic is a rare long-run reward); Q2 AWE ONLY (size, footsteps, shadow, camera framing; no fear mechanics, no small-dino reactions); Q5 Blender is ALLOWED for colossal and redesigned tree art (V3 broadleaf/conifer/palm approved as a scoped exception, docs/140-tree-quality-test.md). Q3, Q4, Q6-Q12 were later decided by the LEAD (next bullet). BD-470..BD-478 re-prioritised: no P1 left, camera, colossal art, LOD, giant collision and test pass are P3.
- **LEAD decisions, owner delegated ("just merge, take full autonomy, do decisions for me")** (docs/115 "LEAD decisions 2026-10-16 (owner delegated)"; the owner may overrule; Robux items are decided in principle, enabling needs the owner go-ahead and all flags stay off): **Skins** (docs/137 s15) one purchase per style for the whole account, equip per dino plus an account default, Anime/Movie crystals only and later, all four Robux skins one price tier (amount set by the owner), a skin survives fusion, tier look is an overlay on any skin, order Compy then Raptor/Triceratops then one per class, a style is sold only once one species per class has it, Balloon is a treatment of the generated Base mesh, admin may revoke, per-skin sounds only after the owner listens, others see your skin (nearest 8 full), no extra free or seasonal skin, Compy pilot may run in parallel. **Gifting** (docs/134 s10) ~~friends only (Settings "From friends / Nobody")~~ **(friends-only OVERTURNED by the owner 2026-10-17, see "Owner decisions log 2026-10-17" below: anyone can be gifted)**, skins first, same price, sender name shown, preset messages only, "from the Be Dino team" admin label, products only when BD-453 starts. **Giant dinos** (docs/139 Q3, Q4, Q6-Q12) only a long-run giant outgrows ordinary trees, mix 68 / 27 / 5 start, trample only if a giant wedges, camera distance/aim/FOV first, fill 38% to 55%, fog from the dino when zoomed out, scale table folded into BD-471, hills stay, larger colossal radius only if the phone numbers pass. BD-450, BD-454 and BD-470 are Done; BD-224 and BD-455 P1 -> P2; BD-453 also waits for BD-459.
- **Mutation audit decisions** (BD-235, owner 2026-10-16, [115](115-decisions-log.md)): (a) a Cracked egg that fails to hatch during weather gives NOTHING, its weather mutation is simply gone, no consolation (code already does this, [99](99-mutation-audit.md) G2); (b) a nest carries the weather from the moment it was FOUND during the run. The owner believed this was current behaviour, but the code uses the weather at SETTLEMENT (`Bootstrap.server.luau` passes `workspace.WeatherId` to `commitRunSettlement`), so the code change is BD-479.
- **BD-004 playtest experience** (owner 2026-10-16): the owner is NOT sure whether experience 10769812255 / place 111259822927673 is the new playtest experience or the legacy one. BD-004 stays Blocked on that; no id was changed. How to check is in the BD-004 row.

## Owner decisions log 2026-10-17

- **Gifting to ANYONE** (owner 2026-10-17, overturns the LEAD's docs/134 Q1 "friends only"; [115](115-decisions-log.md) "OWNER decision 2026-10-17: gifting to anyone", [134](134-gifting-spec.md) s10 Q1): a player can gift any Roblox user, in the lobby, online elsewhere, offline by username, or someone who has never played Be Dino. Recipient picker = server players plus a username search (`Players:GetUserIdFromNameAsync`, display name + avatar confirm before paying). Offline delivery = server-side Gifts inbox claimed on next join, exactly once and idempotent; a never-played recipient's gift waits with no expiry (LEAD recommendation). Safety recheck for strangers (docs/134 s2.1): preset messages only, recipient setting "Gifts from: Everyone (default) / Friends / Nobody" with an easy off (Settings, popup, Mute sender), blocked users cannot gift, rate limits, sender display name shown (no anonymity), receipt-idempotent gift product, admin Revoke for refunds, audit by UserId. **All Robux flags stay off; enabling needs the owner's explicit go-ahead** (docs/134 s12 go-live list). Rows BD-451, BD-452, BD-453 updated; priorities unchanged (P2, P2, P3).

## Board

2026-10-08 multiplayer retry: disposable Build 019 Studio tests with 2 and 5
clients passed profile/character loading, reward isolation, duplicate settlement,
locked equip and memory reload. Znyprr joined and reconnected to published Build
019; six collection previews were visible. Real multi-device play, earned-reward
DataStore persistence, mobile/load and latest-asset release tests remain pending.
Evidence and limits: [multiplayer results](42-live-multiplayer-test.md).
Maximum player access/policy work remains in progress:
[paid-random access plan](43-player-access-and-paid-random-policy.md).

The old hand-kept ID-list table (Backlog / Ready / In progress / Review / test / Blocked / Done) was removed on 2026-10-17: it listed only BD-001 to BD-065 from 2026-10-16 and had been stale for weeks. The board (the row files in `docs/kanban/rows/`) is the only source of truth: each row has its own status and priority. For counts run `python tools/board_summary.py`. No board rows were deleted.

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
- **Picking numbers (parallel agents).** Before you add a row, run `python tools/next_bd_id.py` (several rows: `--reserve N`) and use exactly the id it prints. It looks at `origin/main`, every open PR branch and the other worktrees on this machine, and reserves the id for 48 hours, so two agents cannot get the same one. Same for docs: `python tools/next_bd_id.py --doc`. Do not guess "highest + 1" from your own copy. CI checks: `tools/verify_doc_ids.py` (no duplicate ids) and `tools/verify_kanban_merge.py` (row ids unique, one file per id, file name matches the id, no row file removed by accident, an id `main` already gave to a different task is not reused). Rows are files now, so git merges them by itself; nothing to hand-pick.

## Task index

Rows are files. How the board works:

- One file per task: `docs/kanban/rows/BD-NNNN.md` (number padded to 4 digits). A file holds exactly one table-row line:
  `| BD-NNN | Status | P1 | Task text | Dependencies |`. Do not put task rows back into this page.
- Read the board with the tool, nothing is committed for it: `python tools/kanban.py list --status "Review / test" --priority P1`,
  `show BD-123`, `board` (counts, same as `tools/board_summary.py`), `render > build/kanban.md` (the old full table, sorted by number).
- Change a row: `python tools/kanban.py set-status BD-123 "Review / test" --note "what was done and what is unverified"`
  (it edits only that row's file and appends the outcome to the END of the task text). Keep titles unchanged.
- New row: `python tools/kanban.py add --priority P1 --status Backlog --title "..." [--deps "BD-1, BD-2"]`; it takes the next free
  number from `tools/next_bd_id.py` and creates the file.
- Because every row is its own file, git merges rows by itself. Two PRs conflict only when they edit the SAME row; then
  `python tools/merge_main_into_pr.py <PR>` merges both edits ([166](166-merge-helper.md)).
- Branch still edits rows in this page (made before the cutover)? `python tools/kanban_migrate_pr.py <PR or branch>`
  merges main in and moves your row changes into row files. Details: [191](191-kanban-rows.md).


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

**Review / test (was In progress; see [141](141-board-hygiene-stuck-rows.md)) â€” UI-motion history/evidence reconciled into Build 020; latest device checks pending.**
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
- 2026-10-16 (claude/lowpoly-clickthrough): low-poly click-through QA of the playtest build in an own Studio window (BD-323/BD-325 to Review / test, new rows BD-326..BD-332). Screenshots in `docs/evidence/2026-10-16-lowpoly-clickthrough/`. Shop/Fusion findings predate PR #181. No game code changed.
- 2026-10-16: BD-216 / BD-219 (cube eggs and cube dinos): root cause proven in Studio and fixed on `claude/no-more-cubes` ([docs/96](98-no-more-cubes.md)). `CreateMeshPartAsync(Content.fromObject)` keeps a live link to the EditableMesh; destroying it after the build made every authored part and clone render as a box of the right size (size-only MeshSanity passed). Now: one persistent template mesh per species, clones per instance, a content-level loaded guard, 2D egg/dino picture fallbacks in every preview, a repair watchdog, and an empty uploaded-mesh binding table (`CreatureMeshAssets`) for the FBX exports. Before: 9/9 authored previews were cubes; after: 0/16. Not verified: published place / phone budgets, full hand click-through of the hatch screen.
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
