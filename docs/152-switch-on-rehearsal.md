# 152 Switch-on rehearsal: every built-but-off flag ON at once, offline (BD-624, BD-625, BD-626)

Label: **CURRENT BUILD BEHAVIOR** check, offline only (written 2026-10-18 on main `72cfde77` plus this PR). Nothing here ran in Studio, on a phone, on a published server or against a real DataStore, and no game flag changed: `src/shared/Config.luau` is untouched and every shipped profile (`default`, `playtest`) still pins all of these flags off. The features were each tested alone before; this is the first time the offline suites ran against all of them together. Sources: [145](145-session1-readiness-2026-10-17.md) s3, [115](115-decisions-log.md), [111](111-multiplayer-audit.md), `tools/release_profiles.py`, `tools/run_rehearsal.py`, `tools/measure_switch_on_cost.py`, `tools/verify_switch_on.py`.

## 1. What was built

| Piece | What it does |
| --- | --- |
| Profile `all-on-rehearsal` ([tools/release_profiles.py](../tools/release_profiles.py)) | The `playtest` profile plus every built-but-off gameplay flag ON: `REHEARSAL_ON` lists them. A **scratch** profile like `playtest-streaming`: `Streaming(enabled=True, scratch=True)`, so `release_playtest.shipped_profiles()` and the shipped-profile hard stops skip it, it is never uploaded, and `build/*-all-on-rehearsal.*` is git-ignored. `CrystalPacksEnabled` and `PaidRandomItemsEnabled` stay **required false** by rule, and so do the test, demo, QA and preview switches. `verify_release.py --profile all-on-rehearsal` passes (with the SCRATCH warning). The rules of `default` and `playtest` are unchanged: both still refuse a Config with the rehearsal values (`tests/test_rehearsal.py`). |
| Runner [tools/run_rehearsal.py](../tools/run_rehearsal.py) | `python tools/run_rehearsal.py --runner luau.exe --compiler luau-compile.exe [--profile all-on-rehearsal \| playtest \| none] [--only name,name]` copies `src/`, `tools/`, `tests/` and the workflow into a scratch directory (docs, assets and most of `resources/` are linked, never written), rewrites only the **scratch** Config, and runs every `python tools/...` command of the CI job there, in parallel (about 90 s). The committed Config is never edited. See s2 for how the Config reaches the harnesses. |
| [tools/rehearsal_expected.json](../tools/rehearsal_expected.json) | **Empty since BD-626 (s9).** It listed the 16 verifiers that failed on purpose because they pin the committed OFF state of a flag; they now run their flag-on sections through `tools/rehearsal_env.py`. The mechanism stays for a future verifier that cannot do that. The runner calls a failure expected only when its output carries the entry's signature and no other failing line; anything else is an `INTERACTION`. An entry that now passes is reported as stale. |
| [tools/rehearsal_env.py](../tools/rehearsal_env.py) and profile `all-on-no-combat` (BD-626) | `run_rehearsal.py` sets `BD_REHEARSAL` for every verifier it starts in the scratch tree (and only there); `rehearsal_env.pin()` swaps a verifier's "the committed Config has the flag off" line for one that puts THAT flag into its off state in the verifier's own copy of the Config. `all-on-no-combat` is the all-on scratch profile with `CombatEnabled` off, so `PredationAtMouth` can act. Details and results in s9. |
| [tools/verify_switch_on.py](../tools/verify_switch_on.py) (in CI) | Static guards: the profile is scratch and the paid line is closed; **every Config boolean that is false is either turned on by the rehearsal or excluded here with a reason** (a new built-but-off flag, such as `SecretSpeciesEnabled` and `DinoSkinsEnabled` which landed while this was written, fails the build until it is rehearsed); remote names are unique across `src/server`; every `Config.X` read exists in `Config.luau`; every `require(script.Parent.X)` resolves; and the flag-order rules of s4. |
| [tools/measure_switch_on_cost.py](../tools/measure_switch_on_cost.py) | The 12-player cost table of s5. |

## 2. How the all-on values reach the suites

Most verifiers read `src/shared/Config.luau` twice: embedded into a Luau harness (the value matters) and as text, to prove a wiring rule such as "`CombatEnabled = false` ships in source" (the committed state matters). A plain rewrite of the Config lines broke the second kind for reasons that say nothing about behaviour, so the scratch Config keeps every original line and turns the file into `local BaseConfig = table.freeze({ ... })` followed by a tail that clones it, overrides exactly the keys `apply_profile` changes (25 keys, printed by the runner) and returns the frozen clone. Static text checks still see the committed lines, harnesses see the all-on values. The 25 keys are the 13 rehearsal flags, the playtest set (`CaveHub`, `ClassMovementEnabled`, `LowPolyDinos`, both identity flags, telemetry, feedback, `ReleaseProfile`, the playtest store name, `WorldArtMode`, `FoodArtMode`, `WorldArtDensity`) (the two flags that landed on main during the work, `SecretSpeciesEnabled` and `DinoSkinsEnabled`, are among the 13).

Not every suite takes its Config from the file. Some stub it (`verify_objective_hooks`, `verify_gift_ui` and others clone it and flip the flag themselves); those prove the flag-on behaviour in plain CI too. The rehearsal adds what no single-feature suite could: the **rest** of the system running with the flag on while the suite's own subject is on.

## 3. Result of the run

Committed Config through the runner (`--profile none`): **150 of 150 pass**, so the copy of the tree behaves like the real one. All-on-rehearsal: **134 of 150 pass, 16 fail, and all 16 are the expected pins** below. No failure is unexplained.

| Verifier | Why it fails under all-on (expected) | What it still proved before it stopped |
| --- | --- | --- |
| `verify_world_art`, `verify_gameplay` | Pin `WorldArtMode/FoodArtMode = Legacy` and `SpecialFoodsEnabled = false` at runtime | The Kit-mode food start (new check, s6 finding 1) and everything before the pin |
| `verify_objectives`, `verify_objective_hooks`, `verify_progression`, `verify_gifts`, `verify_gift_ui`, `verify_skins`, `verify_secret_species` (part A), `verify_class_picker`, `verify_mouth_reach` | "The committed Config has the flag off" (one assertion or `check` each) | Their static checks, the pure rules and (secret species part B) 2,113 flag-on checks of settlement, nests, shop, fusion and rollback; `verify_mouth_reach` ran all its numeric checks |
| `verify_profile_golden` | Records the stored bytes of a scripted session under the committed Config (BD-607); the 'outage' server takes the Config as it comes, so the all-on fields change them from step 168 (378 bytes). Steps 1 to 167 are byte-identical | A pure move of the repository is still guarded in CI |
| `verify_rollback` | The drill is about a build with the flags OFF reading data a flags-ON build wrote | 360 checks pass with the flags off, as designed |
| `verify_spawn` | Builds its own default and playtest variants from the Config text and expects CaveHub false in the default one | The cave-hub spawn geometry |
| `verify_multiplayer_sim`, `verify_private_state` | The three scenario families that assert the OFF state (perk refused, no objective hook, hub size rule off): 11 of 684 checks | **673 of 684 checks pass with every flag on**: settlement exactly once, no duplicated egg, leases, join storm, outage and flaky-store recovery, spam protection |
| `verify_session1_smoke` | passes (132 of 132 checks) | |

Everything else passes with the flags on, including `verify_streaming_teleports`, `verify_fusion`, `verify_fusion_ui`, `verify_eggs`, `verify_rewards`, `verify_nests`, `verify_potion_purchase`, `verify_load`, `verify_server_scaling`, `verify_class_movement`, `verify_combat_*`, `verify_npc_predators`, `verify_hatch_v2`, `verify_telemetry`, `verify_feedback`, `verify_local_budget` (Bootstrap client: highest scope **147 of 200** locals) and `verify_sources` (447 sources compile).

**What the pins hid (fixed by BD-626, s9).** A suite that stopped at "the committed Config has the flag off" did not run what follows it with the flag on. Its flag-on tests ran in plain CI against a clone, so nothing was untested, but the *combination* was not exercised in those files. This section is the result BEFORE BD-626; the table above is the first run.

## 4. Failures and odd interactions found

| # | Finding | Root cause | Action |
| --- | --- | --- | --- |
| 1 | **A food mesh whose clone raises stops the whole food spawn** (playtest profile, `FoodArtMode = "Kit"`). `verify_gameplay` died with "attempt to call missing method 'Destroy' of string". | `src/server/FoodService.luau`: `local ok, model = pcall(Resources.clone, artId)` leaves the error string in `model` when the clone raises, and the loop then called `model:Destroy()` on it. Legacy mode never takes this branch, so no verifier ever ran it. Real `ResourceModels.clone` returns nil for a missing id, so only a raising clone triggers it (rare, but one bad mesh means no food at all). | **Fixed** (`if not ok then model = nil end`). `verify_gameplay` now starts the food in Kit mode with a raising clone (fails without the fix, passes with it); `verify_switch_on` guards the line. |
| 2 | **`verify_load` never hatched an egg since BD-360.** No `claim` operation ran in any scenario, so the 12-player request numbers left out the hatch pages. | The harness read `NextChestId` from Player attributes; BD-360 moved it to `PrivateState`. | **Fixed** (reads `PrivateState.get`). The gate now fails a scenario with no hatch claim. The honest base numbers with hatching are in s5; the gate still passes (peak 49 to 53 percent of the budget). |
| 3 | **Six harnesses could not run with `ObjectivesEnabled` or `SecretSpeciesEnabled` on** ("unexpected module nil" on the first settlement): `verify_rewards` (and so rollback, nests, egg toast count, skins) and `verify_potion_purchase`; `fusion_ui_smoke` lacked `ObjectiveSeen`. | The repository requires `ObjectiveService` and `SecretSpeciesConfig` lazily, the harness stubs did not carry them (documented in `ProfileRepository.luau` as intended while the flag is off). | **Fixed**: a no-op `ObjectiveService` spy, the real pure `SecretSpeciesConfig`, an `ObjectiveSeen` stub. `verify_secret_species` now swaps the module through a proxy instead of three string patches. |
| 4 | **Objectives add 36 percent to the DataStore request volume** (s5). | `ObjectiveService` flushes every 30 s while its queue is not empty, and `food_eaten` keeps it non-empty for the whole run, so every player writes twice a minute on top of the lease renew (also every 30 s). The panel does not need the flush (`objectiveView` merges the unflushed queue); it is only crash durability. | **BD-625** (P2, not data loss). **Done (Review / test, offline):** the batch now rides the renew write, the 30 s flush loop is gone; `+ObjectivesEnabled` measures 64.6 requests a minute (was 87.8) and the peak window 49 percent (was 63). The s5 table below is the measurement BEFORE this fix. |
| 5 | `PredationAtMouth` does nothing while `CombatEnabled` is on. | `PredationService` returns at once under combat (instant predation is replaced), so the all-on build cannot prove the mouth rule for predation; combat has its own hit radius (`HitRadius`, `HitSize`). | Documented; guarded by `verify_switch_on`. **Done (BD-626):** the second scratch profile `all-on-no-combat` runs the whole list with combat off (s9). It also showed that nothing offline runs the `PredationService` loop at all: **BD-632**. |

Reviewed and found sound (no change): **objective hooks and gifts never share a transaction** (`applyGifts` is its own `UpdateAsync` and never calls the objectives; hooks run after their own commit; static guard); **remote names**: 31 distinct names, no duplicate (a duplicate would silently destroy the other feature's remote through `getRemote`); **two features writing one profile field**: the only shared field is the wallet (`progression.crystals`), written by gifts, objectives, potions, perk, run settlement, each inside its own revisioned `UpdateAsync` with the `MaxCrystals` clamp; `ownedSkins` is written by gifts and read by skins (revocation falls back to the Base skin in `SkinCatalog`); **mouth reach with class movement**: the reach is measured from the root and the facing, the class speed only changes pace (`tools/simulate_food_reach.py` already sweeps pace), a gliding flier is more than the 6 stud vertical limit above the food and cannot eat, by design; **streaming teleports with fall recovery**: every server teleport goes through `FallRecovery.teleport`, the stream wait is `pcall`'d, `checking[player]` stops a second recovery during the wait, `MovementGuard` ignores any character that is not `Active` and the run start waits (up to 8 s) while the dino is still in the Sanctuary state; **Bootstrap local budget**: 147 of 200, and it is a compile-time count, so the flags change nothing.

## 5. Server cost with every flag on (12 players, 15 minutes, offline)

`python tools/measure_switch_on_cost.py` runs the 12-player load harness of `tools/verify_load.py` (real `ProfileRepository`, mocked DataStore with the per-server budget of 60 + 10 x players requests a minute, 900 virtual seconds, 3 seeds averaged, the same seeds for every row) once per variant. Row 1 is the playtest; every other row adds ONE feature; the last rows add all of them. Numbers are for the whole server per minute. Noise between rows of the same seeds is about 1 request a minute for the totals, but a row that changes the economy moves the random pickup timing too, so read the per-operation column, not only the total.

| Variant | Requests a minute | vs playtest | Repository calls a minute (remote proxy) | Peak 60 s window of the budget | Main operations (requests a minute) |
| --- | ---: | ---: | ---: | ---: | --- |
| playtest (base) | 64.6 | 0 | 91.2 | 49% | crystal pickups 27.5, lease renew 25.4, hatch pages 7.0, settle 2.5 |
| + `ObjectivesEnabled` | **87.8** | **+35.8%** | 115.5 | 63% | **objective flush 23.4**, the rest unchanged |
| + three gift flags | 64.7 | +0.1% | 92.8 | 49% | the harness cannot run `GiftService`; derived below |
| + `PerDinoCosmeticsEnabled` | 64.7 | 0 | 92.1 | 50% | same purchase write as before |
| + `FastTravelPerk` + `CaveHub` | 64.3 | -0.6% | 91.4 | 50% | one `buyPerk` write per player, ever (not played by the harness) |
| + mouth eating, 1.18 times the eggs | 62.7 | -3.1% (noise) | 95.5 | 50% | hatch pages 7.6 (+9%) |
| + mouth eating, 1.37 times the eggs | 63.3 | -2.1% (noise) | 101.7 | 51% | hatch pages 8.4 (+20%); the pickup timing noise hides it in the total |
| + `CombatEnabled`, runs half as long | 64.5 | -0.2% | 87.4 | 50% | settlements 4.2 (+68%), offset by fewer pickups |
| **all flags on** (1.37 eggs, runs half as long) | **85.9** | **+32.9%** | 119.8 | 63% | objective flush 23.0 |
| burst: 12 players reveal 400 eggs, playtest | 57.7 | 0 | 136.8 | 50% | hatch pages 12.2 |
| burst, all flags on | **73.8** | **+27.8%** | 159.1 | 64% | objective flush 24.0 |

Server tick: the offline harness has no frame time. The one measured piece is the `FoodService` pickup work for 12 players (point, radius, grid query, exact test; Luau CPU on this PC, no raycasts): **root rule 11.8 microseconds a tick, mouth rule 28.2** (2.4 times), against the 80 ms between ticks (0.035 percent). The mouth rule asks 2.8 foods a tick for a raycast against 6.4 for the root rule (positions spread over the arena, not clustered). Combat, NPC and movement loops were not timed.

Derived, not simulated: `GiftService` polls its own Gifts store every `ClaimSeconds` = 60 s per player, **12 `GetAsync` a minute** for 12 players, 6.7 percent of the per-server read budget of 180; with objectives on the profile requests are 88 a minute, so the read budget (which `UpdateAsync` also uses) is at about 56 percent for both together, 64 percent at the peak window. All of it stays under the budget with no throttling.

**One feature adds more than 10 percent: `ObjectivesEnabled` (+36 percent requests, +36 percent writes).** It is BD-625. Everything else is within the noise or below +10 percent of the requests; hatching writes grow in proportion to eggs (+9 and +20 percent of the hatch-page requests at 1.18 and 1.37 times the eggs, +1 to +2 percent of the total).

## 6. Every flag: what the owner needs, what this proved, what it cannot

"Needs" is copied from [145](145-session1-readiness-2026-10-17.md) s3, the kanban rows and the flag comments; nothing was changed by this PR.

| Flag(s) | Needs before the owner switches it on | The rehearsal proved | It cannot prove |
| --- | --- | --- | --- |
| `ObjectivesEnabled` (BD-072..077, BD-561/562) | A Studio pass in a private copy that follows one real event to a claimed reward; the owner accepts the PROVISIONAL rewards ([66](66-intake-mini-objectives.md)); decide BD-625 (flush cost) | Hooks fire after their commit in settlement, hatch, equip, potion and fusion with everything else on; replays count once; 673 sim checks pass; the load harness with flush loops stays under the budget | The panel on a phone, real flush timing, the event hooks of `LeapService` and `FoodService` in a real run |
| `GiftClaimEnabled`, `AdminGiftsEnabled`, `GiftingEnabled` (BD-451, BD-452, BD-570) | The owner signs the go-live list of [134](134-gifting-spec.md) s12; BD-452 admin page; BD-453 for a Robux sender (not built: the flag has no sender behind it yet) | The claim is a separate lease-checked transaction; no remote clash; flag-on cases of `verify_gifts` (54,846 checks) and `verify_gift_ui` pass except the pin; the inbox poll costs 12 reads a minute | The real Gifts store, the blocked-ids call, policy review, a live gift |
| `FoodPickupAtMouth`, `PredationAtMouth` (BD-515, 521, 522, 527) | Two real 5-minute Compy runs, flag off then on, under about 10 percent lift; else the owner picks an option in BD-527 | The tick work is 28.5 against 11.9 microseconds for 12 players; hatch pages grow with the eggs (s5); `PredationAtMouth` is inert under combat | The Raycast cost, the real food pace, a human walk |
| `StreamingEnabled` (build option, BD-502) | Gate 1 (phone, radii 256/128 against 256/192) and gate 2 (2 clients) | The scratch place carries the Workspace properties; teleports, run start and fall recovery are written for it (finding list s4); `verify_streaming_teleports` passes | Anything the engine does while streaming |
| `SecretSpeciesEnabled` (BD-604, BD-606) | Filled model slots, the owner's decision | Part B (2,113 checks) with the flag on; the rewards-family harnesses now run with it on | The Index cards, the hatch line, any model |
| `DinoSkinsEnabled` (BD-456) | Skin models (BD-455, 458), UI (BD-457, 459) | Static rules, `SkinCatalog`, gifts-skins sharing `ownedSkins` | Any equip in a client |
| `CombatEnabled` (BD-243..252) | The BD-252 phone test | Rules, state, stats, team-up, NPC and hit-size suites (their only failure is the pin); no profile writes of its own | The phone, 12 players in a fight, balance |
| `SpecialFoodsEnabled` (BD-207) | An owner playtest (food alone must progress) | Rules and the Kit food start (finding 1) | Economy |
| `PerDinoCosmeticsEnabled` (BD-059, [121](121-per-dino-cosmetics-migration.md)) | The owner's Studio check of the phase 2 shop wiring | Ownership rules and migration suites; same purchase write as the account-wide one | Shop UI, legacy purchase migration on real saves |
| `FastTravelPerk` + `CaveHub` (BD-391, 405, D22) | An owner decision that fast travel is a crystal perk; CaveHub already on in the playtest | `buyPerk` is refused unless both are on; one `HubTravel` remote; teleports through `FallRecovery.teleport` | Phone, the 12-player cave (BD-293) |
| `HatchV2` (BD-397) | Owner assets and [118](118-hatch-redesign.md) evidence | The v2 wiring and the per-egg fallback (static) | The visuals |
| Already on in the playtest and kept on: `CaveHub`, `ClassMovementEnabled`, `LowPolyDinos`, `IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled`, `RunTelemetryEnabled`, `PlaytestFeedbackEnabled`, `WorldArtMode = BiomeKit`, `FoodArtMode = Kit` | Unchanged ([145](145-session1-readiness-2026-10-17.md)) | Same suites, now together with the above | Same |
| Excluded on purpose (`verify_switch_on.py` `EXCLUDED`): `CrystalPacksEnabled`, `PaidRandomItemsEnabled`, `CollectionTestGrantEnabled`, `ChestTestGrantEnabled`, `MutationTestSetupEnabled`, `SecurityTestHarnessEnabled`, `ArtTestHarnessEnabled`, `QaOverlayEnabled`, `DemoDirectorEnabled`, `HatchV2Preview`, `DuplicateSettlementProbe`, `AutoOpenRequiresPass` | Paid line: the owner and the paid-random review; the rest are test switches | | |

## 7. What this cannot prove

* **Phone:** nothing. No touch, memory, heat or frame time; the rehearsal never rendered a pixel.
* **Published server:** no tag, no rollback, no non-owner join, no real latency, no BindToClose, no second server hop with a real lease.
* **Real DataStore:** the store is a mock with the right request budget and failure injection. The Gifts store and OrderedDataStore leaderboards are not modelled (the Gifts cost is derived, s5).
* **Server tick:** there is no frame time offline. The one measured piece is the pure pickup work (microseconds of Luau on this PC); combat, NPC and movement loops were only checked for correctness.
* **Real play:** the harness players are scripted (crystals every 8 to 20 s, 8 catches a minute); the economy flags are shown as multipliers, not as measured behaviour.
* **Rollback of data a flags-on build wrote:** `verify_rollback` proves the frozen Build 020 reader keeps unknown fields for the features that existed when it was written; it does not exist for the newest flags under the all-on Config (see the pin above).

## 8. Reproduce

```
python tools/verify_switch_on.py
python tools/verify_release.py --profile all-on-rehearsal
python tools/run_rehearsal.py --runner C:/.../luau.exe --compiler C:/.../luau-compile.exe          # all flags on, exit 0 (153 of 153 since BD-626)
python tools/run_rehearsal.py --runner ... --profile all-on-no-combat                               # same, CombatEnabled off (BD-626)
python tools/run_rehearsal.py --runner ... --profile none                                           # the control: 153 of 153
python tools/measure_switch_on_cost.py --runner ... --seeds 3                                       # about 2.5 minutes
```

## 9. BD-626: the pinned verifiers now run their flag-on tests in the rehearsal

Label: **CURRENT BUILD BEHAVIOR** check, offline only (2026-10-18). No Studio, no phone, no real DataStore, no `src/` behaviour change and no committed flag changed (`git diff` touches `tools/`, `tests/`, `docs/`, `.gitignore` only).

**What changed.**

* `tools/run_rehearsal.py` sets the environment variable `BD_REHEARSAL=<profile>` for every command it starts in the scratch tree, and removes it for `--profile none`. Plain CI and manual runs never set it, so every verifier behaves exactly as before there.
* `tools/rehearsal_env.py` is the one place a verifier reads it. `pin(text, old, new)` returns the harness text unchanged in CI and with `old` replaced by `new` in the rehearsal; `old` must occur exactly once in BOTH modes, so a drifting pin fails CI and not only the rehearsal. `committed_config(text)` is the exact inverse of the runner's Config overlay, for the verifiers that need their own DEFAULT variant (Legacy look, no cave hub).
* A pin line no longer stops the file. Where the verifier owns a mutable copy of the Config, the replacement puts THAT ONE flag (or the two or three the section needs) into its off state, so the off-state section still runs for real (with every other flag still on) and the sections after it run with the flag on, as they do in CI. Where the line was only a statement about the committed file (`verify_class_picker`, `verify_mouth_reach`) it is accepted or dropped in the rehearsal.
* Second scratch profile **`all-on-no-combat`** (`tools/release_profiles.py`): the same rules as `all-on-rehearsal` with `CombatEnabled` kept off by a `require` rule (`NO_COMBAT_OFF`). Scratch like the first (never shipped, never uploaded, `build/*-all-on-no-combat.*` git-ignored), `CrystalPacksEnabled` and `PaidRandomItemsEnabled` still required false. `verify_switch_on` checks it differs from the first in `CombatEnabled` only and has `PredationAtMouth` and `FoodPickupAtMouth` on; the rule that every off flag is rehearsed or excluded with a reason is unchanged and still checks `all-on-rehearsal`. `verify_release --profile all-on-no-combat` passes with the SCRATCH warning.

**Result (this PC, pinned Luau).** `--profile none`: **153 of 153**. `--profile all-on-rehearsal`: **153 of 153**, no expected failure left. `--profile all-on-no-combat`: **153 of 153**. (Before: 134 of 150 with 16 expected pins; the list grew to 153 commands on main since.)

| Verifier | What the rehearsal does now | Runs flag-on that never ran in the combined build |
| --- | --- | --- |
| `verify_objectives`, `verify_objective_hooks` | section A (flag-off identity) with `ObjectivesEnabled` forced off in the harness Config | section B onward: claims, tokens, rollover, outage, renew piggyback, all hook sites |
| `verify_gifts`, `verify_gift_ui` | the three gift flags forced off for the identity section; the Gifts store name is compared with `ProfileDataStoreName .. "_Gifts"` (the rehearsal carries the playtest store name) | 59,495 gift checks and 2,030 UI checks |
| `verify_skins` | `DinoSkinsEnabled` off in both Config copies of the harness for the off section | the skin transactions, the picker, fusion and Build 020 rollback (723 checks) |
| `verify_secret_species` | part A runs on a private Config copy with `SecretSpeciesEnabled` off (golden hash of the flag-off draws); its wiring sub-trees now copy `rehearsal_env.py` | part A's rules plus part B (2,113 checks) in one pass |
| `verify_progression` | `ObjectivesEnabled` off from the start, `IdentityFusionPreviewEnabled` and `PerDinoCosmeticsEnabled` off for the off-state fusion section, `IdentityPersistentEnabled` off for the one published-Studio repository | repository fusion, persistent identity mode, the leap handler and everything after the old stop |
| `verify_class_picker` | the pin is dropped | picker, badge and class-movement wiring checks |
| `verify_gameplay` | the "special foods off" line runs against a private flag-off copy of the Config and a `SpecialFoods` module bound to it | predation egg bonus and nest weather with special foods ON |
| `verify_mouth_reach` | accepts true / true in the rehearsal | all its numeric checks, as before (they never depended on the flags) |
| `verify_world_art`, `verify_spawn` | the DEFAULT variant is built from `committed_config()`; the PLAYTEST variant runs against the rehearsal Config itself | both variants; the playtest one now with every other flag on |
| `verify_rollback` | the harness' default repository is built with the two identity flags off (the drill is a flags-OFF build reading flags-ON data); the flags-ON build is its own `PlaytestConfig` clone | 360 checks with all other flags on |
| `verify_profile_golden` | the byte fixture is compared against the COMMITTED Config (as in CI); the all-on session then must finish, play the same 181 steps, and give identical fingerprints twice | 14 fingerprints differ from the committed fixture by design, first at step 168 |
| `verify_multiplayer_sim`, `verify_private_state` | `feature-remotes-flags-off` and `hub-scale-off` run with `FastTravelPerk` / `CaveHub` off through the scenario's own override; the objective-off proof is a session of its own with `ObjectivesEnabled` off and the probe counters reset | 686 of 686 checks (11 of them are those off-state checks) |
| `verify_remote_fuzz` (new on main since the first run) | the `published-pins` scenario runs with the rehearsal flags back at the playtest value; the cross-player "profile never changed" list leaves out `objectives` | 291 checks with every other scenario running on the all-on Config |

**New failures (real interactions): none.** Every stop was a verifier assumption, not a product defect. Three assumptions the rehearsal exposed, all fixed in the verifiers, none touches `src/`:

1. `ProfileRepository` chooses its identity store wrapper (`identityPersistent()`) when the MODULE is built, not per call. A harness that flips `IdentityPersistentEnabled` after building a repository changes nothing for that repository. Harmless in the game (the Config is frozen), but two verifiers had to build the repository with the flag already off. Recorded here, no row.
2. `verify_remote_fuzz` (BD-608, landed after the first rehearsal) pins the PUBLISHED PLAYTEST remote inventory and compares a victim's "wealth" fields before and after an attacker's calls. With objectives on, the victim's OWN queued events are written by his own lease renew (BD-625), so the field moves while the attacker sleeps; the list now leaves `objectives` out in the rehearsal. That leaves a coverage hole: **BD-631**.
3. `verify_gifts` expected the committed profile store name in the Gifts store name; the rehearsal carries the playtest name.

**Findings with a task row (not hidden, not product bugs).**

* **BD-631 (P3).** No offline check proves an attacker cannot change a victim's `objectives` field: the isolation checks of `verify_remote_fuzz` exclude it (above), the objective suites test one account at a time.
* **BD-632 (P2).** No verifier executes the `PredationService` loop. Searching `tools/` shows only text scans (`verify_gameplay`, `verify_mutations`, `verify_class_movement`), one call that imitates it (`session1_smoke`, `multiplayer_sim`) and the pure rule of `verify_mouth_reach`. So the new `all-on-no-combat` profile makes `PredationAtMouth` reachable, but nothing runs a kill through the mouth branch: the rule itself (`MouthReach`) is proved, its wiring in the tick (`speciesId` only read while the flag and `LowPolyDinos` are on, the victim lookup, kill eggs) is not.

**Limits.** The golden session has no byte fixture for the all-on Config (it would need re-recording in every PR that changes stored data on purpose, and only the rehearsal could check it): the all-on run proves "finishes, same steps, deterministic" and prints how many fingerprints differ. Reading a flag-on section as "proved" still means offline mocks only, see s7.
