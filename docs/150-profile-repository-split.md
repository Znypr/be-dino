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

* `tools/verify_server_module_size.py` (CI, with `--selftest`) fails when any file under `src/server` is over **120,000 bytes** (LF) and warns above 90,000. Split by feature before it gets there.
* `tools/verify_load.py` `MAX_EMBED_BYTES` goes back from 140,000 to **100,000**: the largest module any harness embeds is `IconTiles` at 72 KB; the two generated art tables (164 KB, 203 KB) stay out as before.

## Not done, and why

* `load`, `renew`, `release`, the store wrappers, `admit` / `coalesce` and `isValidProfile` were NOT moved: they are the "one place" the task asks to keep, and they share mutable locals (`store`, `renewing`, `settlementRecovered`, `objectiveService`, `secretModule`) that would need accessors, which is behaviour risk for no size gain.
* Types: the module table is `any` now (see rule 5). Restoring a typed interface is a separate cosmetic task.
* No persistent data format, key, field, error code, rate limit or ordering was touched. No Studio run was made (none was needed for a move).
