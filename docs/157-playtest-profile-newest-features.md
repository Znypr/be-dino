# 157 The playtest profile uses our newest features (BD-657, 2026-10-18)

Label: **CURRENT BUILD BEHAVIOR** of the *playtest* release profile after this change; the *default* profile (which mirrors Build 020) is **unchanged** and still pins every one of these flags off. **Offline evidence only**: nothing was run in Studio, on a phone, on a published server or against a real DataStore, and nothing was published. Sources: [152](152-switch-on-rehearsal.md) (the per-flag table of needs / proved / cannot prove), [155](155-fusion-ladder-source-vs-docs-audit.md) s6, [145](145-session1-readiness-2026-10-17.md), [115](115-decisions-log.md), [43](43-player-access-and-paid-random-policy.md), `tools/release_profiles.py`.

**Rule (OWNER DIRECTIVE 2026-10-18):** "always use our newest features in testbuilds including fusion, food models, dino models, vegetation, map, etc". It authorises turning *built* features ON in the **test / playtest build profile only**. It does not touch the default profile, Robux or paid lines, test/QA/demo switches, or features whose final art does not exist.

## 1. What changed

| Piece | Change |
| --- | --- |
| `tools/release_profiles.py` | The `playtest` profile now **sets** five more flags to true: `ObjectivesEnabled`, `CombatEnabled`, `SpecialFoodsEnabled`, `PerDinoCosmeticsEnabled`, `FastTravelPerk`. The `default` profile requires all five false (two new default rules: `ObjectivesEnabled`, which left the shared list, and `FastTravelPerk`, which no profile pinned). The playtest also **requires false**, with a reason on each rule, the flags below that stay off. |
| `src/server/MutationService.luau` | **Old 50-copy `MutateSpecies` closed while the identity fusion path is on** ([155](155-fusion-ladder-source-vs-docs-audit.md) s6 item 1). With `IdentityFusionPreviewEnabled` true the handler answers `LastMutationStatus = "fusion_moved"` and returns before it reads anything. With the flag false (the default build, Build 020) it is byte-for-byte as before. The old client page was already unreachable in the playtest (`FusionSelection.navTarget` returns `menu` or `unavailable`, never `legacy`, for a non-development profile), so nothing needed hiding. |
| `src/shared/Config.luau` | Two comments only (Objectives, Combat): they said "pinned off in the playtest". No value changed; the committed source still has every flag false. |
| Verifiers and tests | `verify_remote_fuzz` (inventory now includes `CombatBite` and `ObjectiveAction`; new check that `MutateSpecies` is refused with `fusion_moved` and spends nothing; new self-test mutant; `objectives` compared by claims and paid crystals, not by the owner's own queued progress; the "hostile did not gain value" bound is also relative to the account's value at the start of the storm, because the refused `MutateSpecies` no longer burns copies), `verify_objectives` (default pins off, playtest sets on), `release_playtest` (the manifest flag table lists all decisions), `tests/test_release.py` (`PlaytestOnFlagTests`, `PlaytestStayOffTests`, `OldMutatePathClosedTests`), `tests/test_rehearsal.py`, and a small fix in `tools/run_rehearsal.py` (a script that runs twice, `verify_remote_fuzz.py` and its `--selftest`, was reported "stale" when only one of the two passed). |

## 2. Every flag: ON or STAY OFF in the playtest

"Before" is the playtest profile on main `11e2eacf`. "Now" is after this change. `WorldArtMode`, `FoodArtMode`, `WorldArtDensity`, `LowPolyDinos`, `CaveHub`, `ClassMovementEnabled`, the identity pair and telemetry/feedback were already ON and stay ON.

| Flag | Before | Now | Why |
| --- | --- | --- | --- |
| `IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled` | on | **on** | Fusion with persistent identities: the new 6 Base / 3 Gold / 2 Emerald ladder (`FusionAction`, Fusion Menu). Odds PROVISIONAL, unchanged. |
| old `MutateSpecies` (50 copies, no flag) | live | **refused while fusion is on** | No Emerald step, no odds, no consent, no lineage; a hand-fired remote could still use it ([155](155-fusion-ladder-source-vs-docs-audit.md) s5). One early return, tested by `verify_remote_fuzz` (+ a mutant) and `OldMutatePathClosedTests`. |
| `WorldArtMode = BiomeKit`, `WorldArtDensity = 1.25`, `FoodArtMode = Kit` | on | **on** | World kit, vegetation and food models; part budget under 8,000 (`verify_world_art`). |
| `LowPolyDinos`, `CaveHub`, `ClassMovementEnabled` | on | **on** | Dino models, the cave hub, class feel. Legacy visual is still the per-species fallback. |
| `RunTelemetryEnabled`, `PlaytestFeedbackEnabled` | on | **on** | Log-only evidence for the test. |
| **`ObjectivesEnabled`** | off | **ON** | Built and complete: rules, `ObjectiveAction`, panel and hooks. BD-625 made the write cost small (the batch rides the lease renew: 64.6 requests a minute for 12 players, same as without objectives). Rewards are PROVISIONAL and free (crystals, XP); no Robux. |
| **`CombatEnabled`** | off | **ON** | HP combat with bite, health bars, team-up and calm NPC predators. All combat, hit-size and NPC suites pass; the open items (BD-252 12-player phone test, BD-316 two-player test) are exactly what a test build is for. Reversible by deleting one rule. **Risk to watch:** it replaces the instant bigger-eats-smaller rule, so a broken bite input would remove predation for testers. |
| **`SpecialFoodsEnabled`** | off | **ON** | Rare Golden Drumsticks etc. (PROVISIONAL points); runs with `FoodArtMode = Kit` (the Kit food start has a test since [152](152-switch-on-rehearsal.md) finding 1). |
| **`PerDinoCosmeticsEnabled`** | off | **ON** | Auras and trails bound to one dino, with the itemised loss notice in the fusion confirm ([121](121-per-dino-cosmetics-migration.md) phase 2). The playtest store is fresh, so the open "legacy purchases" migration question does not arise; fusion consent for donors with cosmetics is required by the server. |
| **`FastTravelPerk`** | off | **ON** | Owner decision D22 ([115](115-decisions-log.md)): fast travel is a crystal perk (price PROVISIONAL, no Robux). Needs `CaveHub`, which is on. `verify_session1_smoke` now models the perk purchase with the real playtest values. |
| `FoodPickupAtMouth`, `PredationAtMouth` | off | **STAY OFF** (now `require`d false) | Eating at the mouth lifts the egg count by about 18 to 37 percent. The owner said to keep the pacing until a real `LastRunFood` log exists (docs/115 MR6, BD-527), and `PredationAtMouth` does nothing while combat is on ([152](152-switch-on-rehearsal.md) finding 5). |
| `HatchV2` | off | **STAY OFF** | The paint-bucket model is a placeholder (`HatchV2Assets`, a hub barrel stands in) and the [118](118-hatch-redesign.md) owner evidence is missing: final assets missing. |
| `HatchV2Preview` | off | **STAY OFF** | Studio-only preview toggle for the owner's own Studio. |
| `SecretSpeciesEnabled` | off | ~~STAY OFF~~ **ON since 2026-10-18 (update below)** | Was off because all seven model slots were empty. Now ONE slot (the Foxosaurus) holds a real published model id, so the playtest sets the flag: only a species with a filled slot can drop (SS6). Update 2026-10-18: all nine slots (the seven of the first roster plus the Cockatoosaurus and the Eaglesaurus, [115](115-decisions-log.md) SS14) are filled, so a secret hit can be any of the nine. Rule SS1 to SS9 (secrets only from free run and nest eggs, never shop or paid eggs, [43](43-player-access-and-paid-random-policy.md)) is proven by `verify_secret_species`, now also with the shipped roster. [173](173-secret-roster-bind.md) lists every id and what is missing. |
| `DinoSkinsEnabled` | off | **STAY OFF** | No skin model exists (`SkinCatalog.Models` is empty); only the Base look could be equipped. |
| `GiftClaimEnabled`, `GiftingEnabled`, `AdminGiftsEnabled` | off | **STAY OFF** | `GiftingEnabled` is the Robux gifting line and its sender is not built ([134](134-gifting-spec.md) s12, BD-453); `AdminGiftsEnabled` is an admin switch; the claim path alone has nothing to claim and would only poll the Gifts store (12 reads a minute for 12 players). No free player-to-player sender exists to test. |
| `CrystalPacksEnabled`, `PaidRandomItemsEnabled` | off | **STAY OFF, always** | Robux and paid-random line ([43](43-player-access-and-paid-random-policy.md)); also the BD-612 Creator Hub check is still open. Required false in every profile including the rehearsals. |
| `AutoOpenRequiresPass` | off | **STAY OFF** (new playtest rule) | Locks auto-open behind a game pass: a Robux line. |
| `ChestTestGrantEnabled`, `CollectionTestGrantEnabled`, `MutationTestSetupEnabled`, `SecurityTestHarnessEnabled`, `ArtTestHarnessEnabled`, `QaOverlayEnabled`, `DemoDirectorEnabled`, `DuplicateSettlementProbe` | off | **STAY OFF** | Debug, test, demo and QA switches; free grants would corrupt a real test. `QaOverlayEnabled` is flipped locally for a measurement build, never committed. |
| `MovementGuardWindowEnabled` | on | **untouched** | Not a release rule; BD-611. No profile mentions it (`PlaytestStayOffTests` checks that). |
| `StreamingEnabled` | off | **STAY OFF** | Shipped profiles keep it off until the BD-502 gates ([147](147-streaming-experiment-2026-10-17.md)). |

A new rule keeps this honest: `PlaytestStayOffTests.test_every_false_boolean_is_decided` fails when a Config flag is false and the playtest profile has no rule for it.

## 3. Offline proof

All on Windows with the pinned Luau runner, on main `11e2eacf` plus this change.

| Check | Result |
| --- | --- |
| `python tools/run_rehearsal.py --profile none` (the committed Config, every CI verifier) | 155 of 155 pass |
| `--profile playtest` (the playtest Config through every verifier, with `BD_REHEARSAL` pins) | 155 of 155 pass |
| `--profile all-on-rehearsal` and `--profile all-on-no-combat` | 155 of 155 pass each |
| `python tools/build.py --profile playtest` + `verify_release.py --profile playtest` | builds; every rule holds (the only message is "manifest git_dirty" until the change is committed, and the `DeveloperProducts` warning that already existed) |
| `python tools/build.py` + `verify_release.py --profile default` | pass: the default build is unchanged |
| `python tools/verify_load.py --gate-playtest` | passes; the 12-player playtest-flags scenario peaks at 49 percent of the budget (was 49 percent in [152](152-switch-on-rehearsal.md)); nothing throttled |
| `verify_rollback.py` | passes: Build 020 profiles and the flags-off reader still load |
| `verify_remote_fuzz.py` and `--selftest` | pass (307 checks; 8 mutants caught, including the new one) |
| `python -m unittest discover -s tests` with `LUAU_RUNNER` | all pass |
| `verify_kanban_merge`, `verify_doc_ids`, `verify_handbook` | see the PR |

## 4. Not verified

* Nothing ran in Studio, on a phone, on a published server or against a real DataStore. The five new flags have been exercised **only by mocks**.
* **Combat** and **Objectives** are the two with the widest effect on how the game plays. The offline suites cannot tell whether the bite works on a touch screen or whether the objectives panel is readable on a phone (BD-252, BD-075 Studio checks).
* A tester who finds a fusion or a cosmetic purchase wrong cannot be helped by rollback: the recovery is rotating the playtest store name (`_vN`), as in [145](145-session1-readiness-2026-10-17.md).
* Fusion odds, objective rewards, special food points and the fast travel price are all PROVISIONAL numbers.
* The flags that stay off each keep their own kanban row (BD-527 pace, BD-397 hatch v2, BD-604 and BD-606 secrets, BD-456 skins, BD-451 to BD-453 gifts, BD-612 packs); this change does not create new ones.
* **Update 2026-10-18 (BD-617, [115](115-decisions-log.md) NF4 to NF6):** the `fusion_moved` guard above was replaced by removal: `MutateSpecies` no longer exists in any profile, the old Bootstrap pages are deleted, and `DinosaurIdentity.reconcile` protects locked and favourited dinosaurs. What testers see in the playtest profile is unchanged (the new Fusion menu). The default profile now says "Fusion is coming soon" on the FUSION button instead of opening the old 50-copy page. `GoldMutationCost` / `DiamondMutationCost` and the repository function remain as unreachable legacy code.

## 5. How to undo one flag

Delete or edit that one `Rule(...)` line in the playtest list in `tools/release_profiles.py` (change `"set", True` to `_flag_off(...)`). `tests/test_release.py` names the lists (`PlaytestOnFlagTests.ON`, `PlaytestStayOffTests.OFF`); move the flag between them in the same change. Nothing else needs editing; the rehearsal profiles are derived from the playtest.
* **Update 2026-10-18 (BD-606, [115](115-decisions-log.md) SS10 to SS12, [173](173-secret-roster-bind.md)):** `SecretSpeciesEnabled` moved from the "stay off" list to the "on" list. The playtest profile sets it (the default profile still requires it off); `PlaytestOnFlagTests.ON` lists it and `PlaytestStayOffTests.OFF` no longer does. Reason: the owner directive plus one real, bound model; the other six secrets wait for their model ids and boxes.

## 6. Build stamp and freshness check (BD-1043, 2026-10-18)

Label: **CURRENT BUILD BEHAVIOR** of the playtest profile; the default profile output is unchanged (byte for byte). Offline evidence only: not seen in Studio or on a phone.

- **On-screen stamp.** The game already shows a small label at the top middle ("BUILD redesign-020", 15 px, blue, `BuildBadge`). In the **playtest** build `tools/build.py --profile playtest` adds the short id of the commit the file was built from, so it reads "BUILD redesign-020 1b5576fd". A trailing `*` means the build had uncommitted changes. No new UI was added, so nothing new can cover anything; `src/client/Bootstrap.client.luau` is untouched. The id is written into `Config.Build` at build time only; the committed `Config.luau` and the default build still say "redesign-020". Without git the id is empty and the label is the old one.
- **Manifest.** The playtest manifest records `git_commit`, `git_dirty` and the exact `build_label`.
- **Check.** `python tools/playtest_freshness.py build/BeDino-Build020-playtest.rbxlx` prints "up to date" or "N commits behind origin/main" and lists the newest merged feature rows (git log subjects that name a BD- row). Exit 0 up to date, 1 behind, 2 cannot tell; `--warn-only` always exits 0, `--fetch` runs `git fetch origin` first. It reads the manifest next to the file, or the stamp inside the `.rbxlx`.
- **Build time warning.** `tools/build.py --profile playtest` prints a warning when the checkout is behind the local `origin/main` ref. Rule: build a playtest from a fresh `origin/main` (`git fetch origin` first).
- **Tests.** `tests/test_playtest_freshness.py`.
