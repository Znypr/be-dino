# 125 Friends playtest go / no-go (BD-317, written 2026-10-16 on main 73442de)

Label: **CURRENT BUILD BEHAVIOR** readiness audit, read from code, tools and docs. Nothing here was run on a published server or a phone. It **refreshes [106](106-friends-playtest-readiness.md)** (written at main 3e3e932): 106 stays as history for the flag table and the 15-step smoke script; this doc is the current go / no-go. Sources: [AGENTS.md](../AGENTS.md), [114](114-handbook.md) (section 1.1 is in open PR #242), [115](115-decisions-log.md), [55](55-playtest-release-runbook.md), [107](107-offline-mobile-budget.md), [111 audit](111-multiplayer-audit.md) and [111 rollback](111-rollback-drill.md), `tools/release_profiles.py`.

PR state used below (checked with `gh pr list` at writing time): **merged** #244 (Peaceful), #245 (Goals panel), #249 (Robux line guard), #234 (class movement wiring), #235 (nests unlimited), #241 (special foods, flag off), #240 (mutation reveal). **Open** #239 (multiplayer audit, checklist s7.1), #242 (vision answers, handbook 1.1), #243 (rare hatch celebration), #247 (telemetry, docs/122), #248, #250 (class feel), #251 (cave cosy pass), #236. Anything "open" is NOT in a build made from main today.

## 1. Recommendation (read this first)
- **GO** for a small, private, owner-supervised friends playtest of the **playtest profile on desktop**: owner plus 1 to 3 friends (4 players max for the first session), 1 to 2 hours, no Robux, progress disposable. Scope = the core loop: run, eggs, hatch party, nests, shops with earned crystals, Peaceful choice, fusion on persistent profiles, goals panel.
- **GO, second session, only after the first is clean:** up to 8 players, and after merging #243 and #247 so the rare-hatch moment and the telemetry numbers are available.
- **NO-GO** for: phones (never measured, BD-085/168/322); more than 8 players; the cave hub (`CaveHub` off, BD-293 device test pending); HP combat and Bite (`CombatEnabled` off, BD-252/316 no two-player test); low-poly gameplay claims beyond "it loads" (BD-097/309); Robux packs, paid random items, any product; public or unsupervised play; balance judgements (everything economic is PROVISIONAL).
- Tell friends: private test, progress may be reset, no Robux, phone is experimental, the economy numbers are placeholders.
- Hard stop before inviting anyone: the **rollback drill on the real place** (section 7) and the **owner smoke run** (section 6 steps 8 to 10). Without a published rollback you cannot undo a bad build.

## 2. What the playtest profile contains
`python tools/build.py --profile playtest` (`tools/release_profiles.py`). Flags are `Config.luau` constants baked in per build; none can be flipped at runtime.

| Flag | Default build | Playtest build |
| --- | --- | --- |
| `ReleaseProfile` | development | **playtest** |
| `ProfileDataStoreName` | `BeDino_PrivateTest_v1` | **`BeDino_Playtest_M1_v1`** (fresh, isolated; rotate `_vN` to reset) |
| `IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled` | false | **true** (fusion on real profiles; odds roller PROVISIONAL) |
| `WorldArtMode`, `FoodArtMode`, `WorldArtDensity` | Legacy, Legacy, 1 | **BiomeKit, Kit, 1.25** (about 3.5k props, under the 8,000 part cap) |
| `LowPolyDinos` | false | **true** (docs/107 part budget; each species falls back to the legacy visual on a failed load) |
| `CombatEnabled` | false (verifier requires) | false (not set: **off**) |
| `CaveHub` | false (verifier requires) | false (not set: **off**) |
| `SpecialFoodsEnabled` (#241) | false (verifier requires) | false |
| `PerDinoCosmeticsEnabled` | false (verifier requires) | false |
| `FastTravelPerk` | false | false |
| `PaidRandomItemsEnabled`, `CrystalPacksEnabled` | false (required in every profile) | false (required) |
| Test grants and harnesses (`CollectionTestGrant`, `ChestTestGrant`, `MutationTestSetup`, `SecurityTestHarness`, `ArtTestHarness`, `DuplicateSettlementProbe`) | false | false (required) |
| `RunTelemetryEnabled` (#247, open) | false (will be required) | **true once #247 merges** |
| `ClassMovementEnabled` (#250, open) | false | **true once #250 merges** (today class movement on main is gated by `CombatEnabled`, so off) |

Notes: `AdminPanelEnabled` is true in both (creator-only; never add friends to `AdminUserIds`). `StudioLocalProfilesEnabled`/`StudioTestWalletEnabled` are honoured only in unpublished Studio. `verify_release` warns that `DeveloperProducts` still lists Robux IDs; they are inert while the paid flags are false, and the playtest experience must own no products.

## 3. What friends will experience (and how it matches the owner vision)
| Topic | Today on main | Source |
| --- | --- | --- |
| **Owner vision (114 s1.1, PR #242)** | PvP is optional, runs of about 5 minutes then a hatch party, several runs per session, equal mix of collection / favourite to Diamond / new dinos, eggs always kept when eaten, Robux = looks plus convenience only. Not yet on main as text until #242 merges; the code mostly follows it (below). | 114 s1.1, 115 |
| **Egg rate** | `FoodCatchRate = 12/500` (PROVISIONAL): a normal 5-minute run (about 600-700 food) should give about 15 eggs; 500 food = 12 eggs. **Needs a food-per-minute measurement** (telemetry #247 provides it). 12-plus eggs against a queue of 5 means the bank (up to 1000) and the reveal UI for 15 eggs are unverified on a phone. | docs/119 |
| **Nests** | Unlimited nests per run: each opens into 6-12 eggs; nests beyond the five slots become crystals (merged #235). A nest drop needs a run of at least 120 s and 8 catches (hidden gate); 3 h one-at-a-time queue. Overflow UX is owner-unconfirmed. | #235, docs/71, AGENTS.md |
| **Peaceful** | Merged #244: one-tap Peaceful in the Sanctuary and Settings, snapshotted at run start. The legacy bigger-eats-smaller rule (`PredationService`) honours it, so PvP is optional even with combat off. Eggs are always kept (regression test, BD-422). Needs a two-player check that a Peaceful player truly cannot be eaten. | #244, BD-421/422 |
| **Rare hatch celebration** | **Not on main** (#243 open): confetti, fanfare, server-wide announcement for Legendary / Shiny / mutation hatches. Today there are only the older gold fireworks and Shiny shimmer. Merge it before the second session; the announcement is rate-limited and has never run on a real server. | #243, BD-424/428 |
| **Class feel** | **Partly on main** (#234 wiring, gated by `CombatEnabled`, so effectively off); #250 (open) adds the `ClassMovementEnabled` flag, class label and feel hint in the picker. Fly glide and Water dash are unproven on a real server or phone. Treat as "all dinos may feel the same" in session 1. | #234, #250, BD-246/423 |
| **Cave hub** | Still **off** in both profiles (verifier-enforced in default). #251 (open) only adds cosy props behind the same flag. Friends see the old hub. | BD-280..296, docs/104 |
| **Goals panel** | Merged #245 (#248 open): three long-term goal lines. Check the copy reads clearly. | BD-427 |
| **Robux line** | Merged #249: CI guard that no Robux product maps to exclusive power. No products exist anyway. | BD-425 |
| **Hatch** | Mutation reveal burst and calm loop (#240), paint-bucket reveal, one egg at a time, Skip all, first two eggs always safe (`SafeEggs = 2`), Cracked 50% from the third egg. | BD-162, 170, 171, 365 |
| **Fusion** | Ladder 6 Base / 3 Gold / 2 Emerald; precommitted server result; odds roller PROVISIONAL; destroys the ingredients (itemised warning). On persistent profiles in playtest: a fusion bug can mutate real test profiles (rollback: store rotation). | docs/90, 53, 55 s8 |

## 4. Telemetry: how to read it (PR #247 / docs/122, once merged)
Anonymous, server-side, off in the default build, on in the playtest profile. Each `run_end` and `session_end` is printed as `[BD-TELEMETRY] {json}` in the server log and sent as an `AnalyticsService` custom event (log-only if the API is missing). No UserId, name or profile data is logged.
1. During or after the session: Creator Hub > the experience > server logs, or Studio Output for a Local Server. Filter on `[BD-TELEMETRY]` and copy the lines into a text file `server.log`. Roblox keeps server logs only for a limited time, so export the same day.
2. Run `python tools/telemetry_report.py server.log` (add `--json` for machine output).
3. It prints runs, median run length, food per minute (estimate from eggs / rate; docs/119 expects about 120-140), eggs per 5 minutes (target about 15), end reasons, nests and crystals per run, runs per session, and the share of session time in the hub. Runs under 20 s are excluded from rates.
4. Use it to answer the owner-vision questions: is a run about 5 minutes, is the first egg about 60 s, are there several runs per session, does hatch plus return to a new run stay under about 30 s of menus. Food is an estimate; say so in any report.
Until #247 merges, take these numbers by hand (stopwatch, a screenshot of the EGGS plate) and record them in the release record.

## 5. Risks and unproven items (no Studio or phone evidence)
Ranked. "No evidence" means the kanban row is `Review / test` with owner Studio or phone verification still pending (about 236 Review / test rows exist in [07](07-kanban.md); the families that matter for a friends session are below).
1. **Phones never measured.** BD-085, BD-168, BD-097, BD-321/322 ([107](107-offline-mobile-budget.md) s5 lists the top 5 measurements). World kit at 1.25 density, culling budget (1,400 parts), low-poly dinos and the whole new UI have only Studio-desktop numbers (about 15 fps with three Studios open). Touch zones and safe insets (BD-054) and phone-size menus are unverified.
2. **Multiplayer untested on this main.** BD-019 live 2/4/8-client rows, BD-319 (checklist 111 s7.1, in open #239), BD-364 (record the result). Offline `verify_load` and the 12-player simulation pass; a live DataStore never ran with the settings, perk, leaderboard and nest-overflow features. Watch for `SessionBusy`, `LeaseLost`, `save_failed`.
3. **Rollback never performed for real.** BD-020 and BD-320: the offline drill is done; publish r1 then restore r0 has not been done.
4. **Economy numbers.** The 12/500 egg rate needs measurement (BD-418); about 15 eggs against a 5-slot queue and a 1000-egg bank (reveal pacing, UI scale); nest overflow crystals; crystal curve; fusion pacing about 3x faster than docs/90 assumed. All PROVISIONAL.
5. **Hatch experience unjudged on device.** BD-162, BD-170, BD-171, BD-152 (one egg at a time), rare celebration (#243): no owner eyes and no sound check (docs/102, 110: nobody has judged the sounds).
6. **Movement and camera.** BD-164/255 camera rattle unproven; BD-053 sliding on slopes; BD-210 spawn fall (fixed in code, needs a published check); class movement (BD-246) unproven.
7. **World art.** BD-049/050/195-198/206 world kit and food meshes need "Allow Mesh & Image APIs" and the owner account as publisher; fallback models load if not. Floating/sunk props were fixed offline (BD-417) and need owner eyes.
8. **Fusion and identity on persistent profiles** (BD-057/060/064/065): offline only. A bug would be a profile bug; recovery is store rotation (loses all test progress).
9. **Paid-random policy.** Gates off and verifier-enforced; the experience must keep zero products, passes and subscriptions.
10. **Asset ids pending** ([120](120-pending-owner-uploads-checklist.md)): trail icons, egg stage and condition eggs, mutation badges, FX textures. All have fallbacks; do not hand-write ids.
11. **Admin panel exposure**: creator-only; verify absence with a non-owner.

## 6. Owner checklist, in order (agents never publish)
Build and publish ([55](55-playtest-release-runbook.md) s3, s4, s6):
1. Merge what you want in the session (#239, #242, #243, #247, #248, #250 are the useful ones; #251 is optional, flag off). Let CI pass on main.
2. Tag the commit `playtest-m1-bNNN-rK` and build: `python tools/build.py --profile playtest`, then `python tools/verify_release.py --profile playtest --place <rbxlx>`. Check the manifest `place_sha256` and that the flags match section 2. (Build files are CI artifacts or local; they are not tracked in git since BD-419.)
3. Close every other Studio window and every old Build 016-020 window (three open Studios gave 15 fps and a black view); open only the new playtest place.
4. **Creator Hub setup** (once): Private or Limited to named playtesters; maturity questionnaire done; Devices Computer and Phone; max players 4 for session 1 (8 for session 2); no products, passes or subscriptions; HTTP requests off; **Allow Mesh & Image APIs = ON**; publish under the same owner account that owns the generated meshes.
5. Publish to the **existing** playtest experience and start place recorded in `Config.luau` (universe 10769812255, place 111259822927673), not the legacy experience. Record the version number. Then **Restart servers for updates**.
6. As a non-owner alt, check that every image, model and sound loads and that no admin panel, FOOD counter or Robux prompt appears.
7. Fill in the release record ([55](55-playtest-release-runbook.md) s6): tag, commit, `place_sha256`, version number, known issues.
8. **Rollback drill on the real place BEFORE inviting (BD-020):** publish r1, then restore the previous version in Creator Hub > Places > Version History, confirm the version label changed, roll forward again. Record both version numbers ([55](55-playtest-release-runbook.md) s8 item 6, [111 rollback](111-rollback-drill.md) s3).
9. **Smoke run** with owner plus one alt: the script in [106](106-friends-playtest-readiness.md) s4 (steps 1 to 14), plus a Peaceful check: the alt turns Peaceful on and the owner (bigger) cannot eat the alt.
10. **Two-player checklist** (Studio Local Server, 2 players, about 15 minutes): [111 audit](111-multiplayer-audit.md) s7.1 (added in open #239; merge it first or read it from that PR). It covers private settings, perk per player, hub station marker, odds panel, egg-origin popup, effects LOD, leaderboard writes and nest-overflow crystals. The perk and hub steps need `CaveHub` and `FastTravelPerk` true **in your own Studio copy only**, never in the published playtest build. The four-client core flow is in [111 audit](111-multiplayer-audit.md) s5.2. Paste pass/fail per step and any `[Be Dino]` or Warning line into BD-364.
11. If steps 8 to 10 pass: invite 1 to 3 named friends.

What to watch during the session (owner on a second window if possible):
- Server log: `SaveFailed`, `LeaseLost`, `SessionBusy`, `SchemaError`, `settlement failed`, throttle and schema warnings, bursts of `leaderboard publish failed`, `[BD-TELEMETRY]` lines.
- Developer Console (F9): Log (client errors) and Memory (Total, `PlaceMemory`, Mesh, `LowPolyImagesLive`); Shift+F3 stats for fps.
- Player reports of: eggs per run (should feel like about 15 per 5 minutes), first egg time (about 60 s), reveal pacing for 15 eggs, camera shaking, falling through the world, sliding on slopes, grey boxes or cubes, black or cut-off view in weather, sounds too loud or sharp, text too small, any Robux or purchase prompt (there must be none).
- Fusion results and persistence after rejoin; a Peaceful player being eaten (a bug).

How to collect feedback:
1. Before the session send friends one short note (what the build is, no Robux, progress may reset, phone is experimental).
2. During: ask each friend to call out "confusing", "boring" or "wow" moments; the owner notes a timestamp and the screen.
3. After (10 minutes): five questions: did you know what to do in the first minute, how long did a run feel, what was the best moment, what was the most confusing screen, would you play again. One screenshot or clip of any bug.
4. Same day: export the server log, run `python tools/telemetry_report.py server.log`, and record in BD-317 / BD-364 / BD-418: runs, median run length, eggs per 5 minutes, errors, device and fps per player. File each bug as a kanban row with the build tag. Do not mark any `Review / test` row Done without recorded evidence.

## 7. Rollback
**Decide fast:** roll back on any P0, any `SchemaError` or `SaveFailed` spike, or a fusion/identity bug that mutates profiles ([55](55-playtest-release-runbook.md) s8).
1. **Stop the damage:** set the experience to Private, or Shut down all servers.
2. **Republish the previous known-good playtest tag**, not Build 020 (Build 020 uses a different store and cannot read newer profiles): Creator Hub > Places > Version History > **Restore** the version in the release record, or `git checkout <prev tag>`, `python tools/build.py --profile playtest`, check `place_sha256`, publish. Then **Shut down all servers** so none runs the bad build.
3. **Flags** (`IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled`, paid flags) are baked into the build: to turn fusion off, change the profile rule in a PR, rebuild, republish. Never turn paid flags on during a rollback.
4. **Check:** join with a test account (`ProfileState = Loaded` on the previous tag); count `attempt N failed`, `SchemaError`, `SaveFailed`, `LeaseLost` in the log; confirm the version label and hash; add a **rollback** row to the release record.
5. **Players locked out (`SchemaError`)?** Prefer rolling forward to a fixed build. Otherwise **rotate the store**: increment `PlaytestProfileDataStoreName` (`_v1` to `_v2`), commit, CI, tag, build, verify, publish ([55](55-playtest-release-runbook.md) s8 item 4, s9). Everyone restarts fresh; the old store stays as evidence.
6. **Restoring one key** is a last resort for one tester and an explicit owner decision ([111 rollback](111-rollback-drill.md) s3 item 6: list versions, write to a different key first, restore with `UpdateAsync`, never `RemoveAsync`).
7. Roll forward after the fix and append the record row. Data policy: playtest progress is disposable and never migrated to a public experience ([55](55-playtest-release-runbook.md) s9).

## 8. Gate to close BD-317
Done requires recorded evidence for: the real rollback drill (BD-020), one clean smoke run (section 6 step 9), the two-player checklist (step 10), and one friends session with telemetry or a hand-written egg-rate record. Phone acceptance is a separate gate (BD-085) and is NOT part of the first session.

## Handbook check
- Vision and tone ([114](114-handbook.md) s0, s1, s2): the recommendation keeps the playtest private, small and supervised; friends are told the economy is placeholder and progress may reset; no Robux anywhere; copy rules are not changed.
- Owner vision of 2026-10-16 ([115](115-decisions-log.md), 114 s1.1 in #242): Peaceful (BD-421), eggs-always-kept (BD-422), class feel (BD-423), rare hatch (BD-424/428), Robux line (BD-425), telemetry (BD-426), goals (BD-427) are each stated with their real status (merged versus open), not as shipped.
- Egg rate: 12/500 and about 15 eggs per 5 minutes ([119](119-catch-rate-15-per-run.md)); 4/500 and 40/500 treated as historical. Fusion ladder 6/3/2, five species tiers, Cracked 50% from the third egg, `SafeEggs = 2` as in 115. AGENTS.md rules respected: eggs stay distinct from nests, crystals and XP; nothing claimed Studio-verified or phone-verified.
- Doc 106 is superseded for the verdict but kept as history; its smoke script is referenced, not copied. Doc number 123 is free on origin/main and in open PRs (122 is #247; 120 is on main and in #243/#251).
- Docs only: no source, config, flag, build or kanban status changed besides a pointer in the BD-317 row; verifier tools were not re-run for this doc.
- Open items for the owner: confirm the 4-player cap for session 1, whether to merge #243/#247/#250 before session 1 or after, and whether the cave hub should enter session 2 (needs BD-293 first).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
