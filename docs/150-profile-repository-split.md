# 150 ProfileRepository split into focused modules (BD-607)

Status: **Review / test** (offline proof only; no Studio run, no publish, no stored-data change). Owner: LEAD (engineering hygiene, owner delegated). Date: 2026-10-18.

## Why

`src/server/ProfileRepository.luau` grew with every feature (objectives, gifts, skins, secret species, telemetry hooks): 144,793 bytes and 2,668 lines on `origin/main` (72cfde77). The offline harnesses embed server modules as text, and `tools/verify_load.py` had to raise `MAX_EMBED_BYTES` twice in one day (120k, 140k, 155k) so `verify_multiplayer_sim`, `verify_private_state` and `verify_session1_smoke` could still embed it. One more `local` in the main chunk also brings it closer to the Luau 200-register limit (`tools/verify_local_budget.py`).

## What changed (pure moves)

The transaction groups moved, **unchanged**, into sibling modules. Each module is `return function(ProfileRepository, shared) ... end`: it installs its `function ProfileRepository.<name>` bodies on the SAME table, so the public API, the function names, the error codes, the key and field names, the ordering and the rate limits are exactly what they were, and no caller changed.

| Module | Bytes (LF) | What it holds |
| --- | ---: | --- |
| `ProfileRepository.luau` | 54,269 | the one place for: store wrappers (identity reconcile, request counting), lease (`ownSession`, `handleLeaseLost`), `retry` / `retrySettlement`, `admit` / `coalesce` write budget, `adopt`, profile defaults, migration and `isValidProfile`, `syncAttributes`, the chest / bank / nest queue helpers, `load`, `prepareEgg`, `progression`, `renew`, `release`, `start`, and the install block |
| `ProfileEggs` | 31,129 | `commitRunSettlement`, `claimNest`, `claimChest` (+ `applyHatch`, `publishHatch`), `pendingReveals` |
| `ProfileTestGrants` | 12,719 | flag-gated `grantCollectionTestSpecies`, `grantChestTest`, `setMutationTestCopies` and the Studio-only `demo*` triggers |
| `ProfileFusion` | 12,092 | `dinosaurDetails`, `fusionStatus`, `listDinosaurs`, `fusionDetails`, `quoteFusion`, `fuseDinosaurs`, `setFusionTestRoller` |
| `ProfileObjectives` | 10,439 | `objectiveRecord`, `objectiveSeen`, `objectiveView`, `objectiveFlush`, `objectiveClaim` |
| `ProfileCollection` | 8,547 | `equipSpecies`, `mutateSpecies` |
| `ProfileShop` | 8,328 | `progressionAction` (potions, auras, trails, perks, egg, condition upgrade), `purchase` (Robux receipt credit) |
| `ProfileSkins` | 7,949 | `skinView`, `applySkin` |
| `ProfileGifts` | 7,163 | `applyGifts` |
| `ProfilePrefs` | 5,818 | `setRevealSkip`, `writeRevealSkip`, `setSettings`, `writeSettings` and their coalescing registration |

Largest module: 54,269 bytes (was 144,793). The sum is larger than the old file (158,453 bytes) because each part names its shared helpers once (`local adopt = shared.adopt`), about 25 short lines per part. Nothing else was added.

### The contract between the main file and a part

`ProfileRepository.luau` ends with `local shared = {...}` (the helpers and tables the parts use: `store`, `retry`, `admit`, `adopt`, `keyFor`, `isValidProfile`, `ownSession`, `handleLeaseLost`, `syncAttributes`, `profiles`, `revealBuffer`, ..., the required modules) and then `require(script.Parent.<Part>)(ProfileRepository, shared)` for each part. Rules:

1. The install block comes after the store wrappers and after every helper it hands over, because `store` is passed by value (it is never reassigned after that point).
2. Shared state is shared by identity (the `profiles`, `coalesced`, `revealBuffer`, `pendingSettlements`, `objectivePending` tables are the same tables). State only one group uses lives in that group (`fusionTestRoller` is in `ProfileFusion`).
3. The lease-checked `store:UpdateAsync` wrapper, `retry`, the profile load / migration and the save path (`renew`, `release`) stay in `ProfileRepository.luau` on purpose: that is the code every transaction must trust, so it stays in one place.
4. A part calls other repository functions through `ProfileRepository.<name>` exactly as before, so a test that replaces a function still sees the replacement.
5. The main file keeps `local ProfileRepository: any = {}`: the functions are added by the parts, so the old inferred table type is gone (types only, no behaviour). Callers are unchanged.

To add a transaction: put it in the part that owns its feature (or add a new `ProfileXxx.luau` and one `require(script.Parent.ProfileXxx)(ProfileRepository, shared)` line), add any helper it needs to `shared`, and keep the file under the size limit below.

## Proof that nothing changed

* **Golden session** (`tools/verify_profile_golden.py`, `tools/profile_golden.luau`, fixture `tools/fixtures/profile_golden.json`, in CI): one long scripted session on the virtual clock, seeded `Random` and mocked DataStore of `tools/verify_load.py`: load; run settlements (replayed, bad); hatching in pages; preferences with a coalescing burst; bonus nests; equip; test grants; the crystal shop (potion, aura, trail, perk, egg, upgrade); objectives; gifts; Gold mutation; identity fusion; dino skins; a Robux receipt and the paid-random gate; lease renew and release; a second session; the Studio preview with the demo triggers; a store outage with a recovered settlement; a lost lease. After EVERY one of its 181 steps it fingerprints the stored profile (canonical JSON with sorted keys), the step's own return values and the player's owner-only state. The fixture was recorded from the code BEFORE the split (`origin/main` 72cfde77); `--compare-root <old checkout>` runs the old and the new tree and compares every byte (32,060,306 bytes of canonical text agree). A one-character change to a moved transaction (`revision += 2`) fails it at the first step that runs the function. A later PR that changes stored data on purpose records a new fixture with `--record` and says so.
* **Every verifier that touches profiles** passes before and after on the same machine (list in the PR): rollback, progression, rewards, potion shop and purchase, gifts, gift UI, skins, secret species, objectives, objective hooks, fusion, identity, multiplayer sim, load, private state, Session 1 smoke, gameplay, server scaling, release, plus the unit tests.
* Static verifiers that looked for a function or a string in `ProfileRepository.luau` now read `tools/profile_sources.py` (`repository_text()` = the main file followed by every part, found through the install block). The function bodies are verbatim, so every pattern they check is still checked. Harnesses that embed the module as text use `profile_sources.module(path)`, which hands the parts to `require(script.Parent.<Part>)` without extra stubs. `tools/verify_release.py` accepts `local localPreview = shared.localPreview` in a part (the guarded definition in `ProfileRepository.luau` is still checked).

## Size guard

* `tools/verify_server_module_size.py` (CI, with `--selftest`) fails when any hand-written file under `src/` (server, client AND shared, since BD-623) is over **120,000 bytes** (LF) and warns above 90,000. Split by feature before it gets there. See "Size guard audit" below.
* `tools/verify_load.py` `MAX_EMBED_BYTES` goes back from 140,000 to **100,000**: the largest module any harness embeds is `IconTiles` at 72 KB; the two generated art tables (164 KB, 203 KB) stay out as before.

## Not done, and why

* `load`, `renew`, `release`, the store wrappers, `admit` / `coalesce` and `isValidProfile` were NOT moved: they are the "one place" the task asks to keep, and they share mutable locals (`store`, `renewing`, `settlementRecovered`, `objectiveService`, `secretModule`) that would need accessors, which is behaviour risk for no size gain.
* Types: the module table is `any` now (see rule 5). Restoring a typed interface is a separate cosmetic task.
* No persistent data format, key, field, error code, rate limit or ordering was touched. No Studio run was made (none was needed for a move).

## Size guard audit of the rest of src/ (BD-623, 2026-10-18)

Status: **Review / test** (offline). Measured on `origin/main` e9d3d5c2 (after #436) with `luau-ast` and the byte counts the verifiers use (LF). "Local peak" is the most live local registers in any one function scope, counted by `tools/verify_local_budget.py` (Luau refuses a function above 200; CI fails above 185). Excluded: the generated art / data tables (`IconRaster` 203 KB, `ResourceGeometry` 164 KB, `IconTiles` 72 KB, and the 124 `CreatureGenes/Chunks` and `CreatureData/Chunks` files at 95 KB each, all 1 to 3 lines).

### The 15 largest hand-written files

| # | File | Bytes | Lines | Bytes on 16 Oct | Local peak (scope) | Main chunk locals |
| ---: | --- | ---: | ---: | ---: | --- | ---: |
| 1 | `src/client/Bootstrap.client.luau` | **126,160** | 1,773 | 98,964 | 144 (main chunk; `mountHud` 55) | 144 |
| 2 | `src/client/HatchSequence.luau` | 77,329 | 1,219 | 68,706 | 85 (`play`) | 44 |
| 3 | `src/client/WeatherVisuals.client.luau` | 69,053 | 1,065 | 48,914 | **147** (main chunk) | 147 |
| 4 | `src/shared/BiomePlacement.luau` | 63,673 | 891 | 24,122 | 86 (`generate`) | 8 |
| 5 | `src/shared/CaveHubLayout.luau` | 59,978 | 998 | not in tree | 59 (`get`) | 34 |
| 6 | `src/client/FusionMenu.luau` | 58,149 | 1,030 | 46,010 | 78 (main chunk) | 78 |
| 7 | `src/server/ProfileRepository.luau` | 54,780 | 1,045 | 89,057 | 90 (main chunk) | 90 |
| 8 | `src/shared/FusionSelection.luau` | 52,659 | 973 | 42,558 | 22 (`details`) | 18 |
| 9 | `src/server/GiftService.luau` | 36,760 | 678 | not in tree | 43 (main chunk) | 43 |
| 10 | `src/shared/TouchLayout.luau` | 34,388 | 512 | 10,842 | 40 (`compute`) | 11 |
| 11 | `src/client/DinoIndexPanels.luau` | 32,724 | 582 | 28,996 | 31 (main chunk) | 31 |
| 12 | `src/server/ProfileEggs.luau` | 31,129 | 575 | not in tree (#436) | 46 (anonymous) | 0 |
| 13 | `src/server/Arena.luau` | 29,834 | 452 | 15,594 | 34 (main chunk) | 34 |
| 14 | `src/shared/NpcPredatorRules.luau` | 28,267 | 588 | not in tree | 24 (main chunk) | 24 |
| 15 | `src/shared/Config.luau` | 27,751 | 365 | 17,027 | 0 | 0 |

The highest local peaks (any scope):

| Peak | File and scope | Bytes |
| ---: | --- | ---: |
| 147 | `WeatherVisuals.client.luau` main chunk (110 on 16 Oct) | 69,053 |
| 144 | `Bootstrap.client.luau` main chunk (199 on 16 Oct, before the `mountHud` wrap) | 126,160 |
| 90 | `ProfileRepository.luau` main chunk (62 on 16 Oct; the parts now hold the rest) | 54,780 |
| 86 | `BiomePlacement.luau` `generate` (59 on 16 Oct) | 63,673 |
| 85 | `HatchSequence.luau` `play` (81 on 16 Oct) | 77,329 |
| 78 | `FusionMenu.luau` main chunk (66 on 16 Oct) | 58,149 |
| 61 | `EggsScreen.luau` `render` | 15,138 |
| 59 | `AdminGiftPage.luau` `build`; `CaveHubLayout.luau` `get` | 19,273; 59,978 |
| 58 | `AdminPanel.client.luau` main chunk | 15,664 |
| 49 | `HatchEggV2.luau` `update` | 24,351 |
| 46 | `ProfileEggs.luau` anonymous (`commitRunSettlement`) | 31,129 |
| 43 | `GiftService.luau` main chunk; `HatchPresentation.luau` `add` | 36,760; 14,969 |
| 40 | `FeedbackClient.client.luau` main chunk; `TouchLayout.luau` `compute` | 11,023; 34,388 |

**Above 150 locals: none.** Closest: WeatherVisuals 147 and Bootstrap 144 (compiler limit 200, CI fails at 185). **Above 90 KB: only `Bootstrap.client.luau` (126,160 bytes, over the 120 KB line)**; `HatchSequence` (77 KB) and `WeatherVisuals` (69 KB) are next.

### Growth since 16 Oct (what to watch)

* **`WeatherVisuals.client.luau`: main chunk 110 -> 147 locals and 48.9 -> 69.1 KB in 15 commits.** At that rate it reaches the 185 line within about one more day of weather work. It is the first file to fix.
* `Bootstrap.client.luau`: +27 KB in 63 commits (the `mountHud` wrap cut the main chunk from 199 to 144 locals; the file itself is still the biggest). It is now frozen by a ratchet (below).
* `BiomePlacement.luau` 24 -> 64 KB (data tables 16 KB, `generate` 28 KB, one function at 86 locals), `TouchLayout.luau` 11 -> 34 KB, `Arena.luau` 16 -> 30 KB, `FusionMenu.luau` 46 -> 58 KB, `HatchSequence.luau` 69 -> 77 KB.
* `SettingsMenu.luau` is small (7.9 KB, 16 locals): no split needed.

### What was split: nothing, on purpose

The rule for this task is: split only pure moves with no behaviour risk, proven by a test that runs the moved code. For the client files that is not available:

| Candidate | Why it was NOT split | What a safe split needs |
| --- | --- | --- |
| `Bootstrap.client.luau` (126 KB, 144 locals) | 46 verifiers read its text; `mountHud` (about lines 1,239 to 1,773) and the code above it share a large set of upvalues (`gui`, `label`, `box`, `button`, `open`, `notify`, `active`, `rail`, ...). No verifier executes it (`verify_hud` runs `HudRules` and scans the text; `verify_regression_walk` runs walk scripts against a mock, not this file). | A Roblox-mock harness that runs the whole client script and records every Instance it creates (class, name, parent path, key properties) and every remote call, compared old tree versus new tree like `verify_profile_golden`. Then split along the existing seams: toasts (about 180 to 257), `open` and modal blur (about 144 to 175 and 334 to 366), the tutorial / welcome modal (about 1,190 to 1,235), and `mountHud` by HUD piece (rail, crystal HUD, progression HUD, Home control, layout `scales`), each as `return function(env) ... end` with the shared helpers in one `env` table (the install-block method of #436). The text verifiers then need a `bootstrap_sources.py` like `profile_sources.py`. |
| `WeatherVisuals.client.luau` (69 KB, 147 locals) | No verifier executes it: `verify_weather`, `verify_cave_weather`, `verify_cave_lighting`, `verify_phone_guards` and `verify_settings` only scan its text (`Instance.new` outside pooled paths, cave guards, `SettingsModel` use); `WeatherLooks` (its data and math) is the part that is run. The cleanest seams are already marked in the file: earthquake v2 (about lines 596 to 820, 225 lines), pooled lightning / rings / bursts / bombs (372 to 595), the title card (822 to 869) and the per-event rigs (157 to 322). They share the pools, `root`, `motion` and the `Emitter` helpers, so it is not a verbatim move. | A mock of `Workspace`, `Lighting`, `Camera`, `Debris`, `RunService.Heartbeat` and `Player` that steps the script on a virtual clock for each WeatherId (clear, rain, blizzard, volcano, aurora, quake, blood moon), then fingerprints the created Instances (class, name, count per tick), the Lighting / Atmosphere values after N ticks and the emitter rates. Old and new tree must agree byte for byte. Until then new weather work goes into a NEW module (`WeatherQuake`, ...) required by the main chunk, not into its main chunk. |
| `FusionMenu.luau` (58 KB, 78 locals) | `verify_fusion_ui` runs `FusionSelection` (pure logic) only; its docstring says UI Instances are not executed. | The same Instance-recording mock, plus the retry-token and reveal-wheel calls. |
| `HatchSequence.luau` (77 KB) | Scanned by `verify_hatch_sequence`, not executed. `play` is one 85-local function, so a verbatim move would not lower it. | A mock-driven golden of one full hatch (instances per frame and timing). |
| `BiomePlacement.luau`, `CaveHubLayout.luau` (pure, deterministic) | These CAN be proven with a golden (`generate` for a few seeds and options hashed old versus new; ten verifiers already run them), but the gain is small today: peaks of 86 and 59 locals, 64 and 60 KB, data tables 16 KB. `generate` is one function, so splitting it needs a rewrite, not a move. | If either passes 90 KB: `tools/verify_biome_golden.py` hashing `generate` for 6 seeds x the Small / Colossal options and the cave layout rectangles, then move the data tables into `BiomeKit.luau` with the install-block method. |
| `FusionSelection.luau`, `TouchLayout.luau` (pure) | Run by `verify_fusion_ui` and `verify_movement_mobile`, but at 53 KB and 34 KB with peaks of 22 and 40 locals they are not at risk. | Nothing yet; split by feature (filters / odds / details; phone / tablet / desktop rects) at 90 KB. |
| `SettingsMenu.luau` | 7.9 KB, 16 locals. | Nothing. |

So no source file was touched in this change. The server module that mattered was done in #436.

### Guards added (BD-623)

* `tools/verify_server_module_size.py` (CI step already exists, with `--selftest`) now scans **all of `src/`** (was `src/server` only): fails above **120,000 bytes**, warns above 90,000. Generated tables (`IconRaster`, `ResourceGeometry`, `IconTiles`, `*/Chunks/*`) are skipped only while they have 5 lines or fewer, so hand-written code cannot hide behind a generated name (the selftest proves it).
* **Ratchet for `src/client/Bootstrap.client.luau`**: it was already 126,160 bytes, so it gets a ceiling of **127,000** (`KNOWN_OVER`) instead of the general limit. It cannot grow by more than 840 bytes, and CI prints a warning on every run until code is moved out and the ceiling is lowered. New client features go into their own module.
* `tools/verify_local_budget.py` already scanned **all of `src/`** (server, client, shared) and fails above **185 of 200** live locals in any function scope, main chunk included, so the local-register headroom was already enforced for client and shared. Only the warning line moved from 170 to **140**, so the log names `WeatherVisuals.client` (147) and `Bootstrap.client` (144) on every run before they get close.
* `tools/verify_load.py` `MAX_EMBED_BYTES` stays at 100,000.
