# 145 Are we ready for friends session 1? Offline audit on main b616687 (BD-317, 2026-10-17)

Label: **CURRENT BUILD BEHAVIOR** audit, offline only. Nothing here was run in Studio, on a published server or on a phone, and no game code was changed. It refreshes [125 go / no-go](125-friends-playtest-go-no-go.md) and walks the items of [106](106-friends-playtest-readiness.md) and [129](129-owner-studio-smoke-checklist.md) against what is merged today. Sources: [AGENTS.md](../AGENTS.md), [55 runbook](55-playtest-release-runbook.md), [111 multiplayer](111-multiplayer-audit.md), [115 decisions](115-decisions-log.md), [120 uploads](120-pending-owner-uploads-checklist.md), [141 Studio scripts](141-board-hygiene-stuck-rows.md), `tools/release_profiles.py`, the kanban rows BD-317, BD-085, BD-322, BD-020, BD-019, BD-004, BD-319, BD-364, BD-293.

## 1. Summary (one screen)

**Verdict: NOT READY today. No code blocker turned up offline (every check below passes), but nobody has looked at the current build, and two owner facts are unresolved.** It becomes ready after a lead Studio pass (section 5, about 35 minutes) and the owner steps (section 6). Wording for friends: private test, desktop, 4 players, progress may reset, no Robux, economy numbers are placeholders.

Top 5 blockers, in the order to clear them:

1. **Friends may not be able to join at all (owner, 2 minutes + settings).** BD-004 is still Blocked: `Config` points at universe 10769812255 / place 111259822927673, which docs/55 s2 calls the LEGACY experience, and the owner is not sure which it is. The only alt-account join attempt ever made ([40](40-mesh-access-verification.md)) hit "This experience is currently not available" before any client loaded, and that cause was never found. Non-owner asset loading (FBX, textures, sounds, meshes) has never been verified live (docs/55 D4).
2. **The current playtest loop has not been walked in Studio since 2026-10-16.** About 140 commits landed since midday on 2026-10-16 (26 today: cave organic rooms and dim pass, moss and strata, 1x hub scale, nest weather, plants and props wiring, colossal LOD, BD-433 moments, potion icons, 55 bound textures, egg-page art, admin x10). The only Studio images dated 2026-10-17 are plant, colossal-tree and VFX-lab trials; there is no walk of the hub, cave, run, hatch or shops. The playtest profile turns ON the three riskiest systems (`CaveHub`, `LowPolyDinos`, `ClassMovementEnabled`). 129 has 20 BLOCKS lines and none is ticked.
3. **No real publish, no tag, no rollback drill (BD-020, BD-320).** The release record in docs/55 s6 is empty. Offline drills pass ([111 rollback](111-rollback-drill.md), `verify_rollback.py`), but "publish r1, restore r0, roll forward" has never been done, and docs/125 made it a hard stop.
4. **Multiplayer has never run live on this main (BD-319, BD-364), and session 1 puts the cave hub (BD-293 still Backlog) in front of 4 players.** The offline 2, 4 and 8 player simulation passes (681 checks), but replication, what another client sees, real DataStore timing and the non-admin side of the admin panel are live-only.
5. **Phones are unmeasured (BD-085, BD-322) while the playtest experience is set up for Computer and Phone.** Decision needed: set Devices to Computer only for session 1, or accept that a phone friend is the first measurement. LowPoly dinos need "Allow Mesh & Image APIs" and an 80 MiB EditableImage budget that has never been tried on a phone or a published server.

Also open, not top-5: the 5-minute / about 15 egg claim has never been stopwatched (BD-418); most sounds are unbound or unheard (weather beds, cave bed, cracked/nest/hatch cues, rare fanfare are `pending` slots); 16 UI images are still unbound, so shop tiles, tab icons and the Eggs-page stage use their code fallbacks.

## 2. Offline results (main b616687, Windows, 2026-10-17)

| Check | Result |
| --- | --- |
| `python tools/build.py` (default) | PASS: 416 scripts, 33,885,174 bytes |
| `python tools/build.py --profile playtest` | PASS: 416 scripts, 33,885,166 bytes; one expected warning (`DeveloperProducts` still lists Robux ids, inert while both paid flags are false) |
| `verify_release.py` (default) | PASS: 29 keys enforced, Studio-only guards intact |
| `verify_release.py --profile playtest --place build/BeDino-Build020-playtest.rbxlx` | PASS: 27 keys enforced, same warning |
| All 110 other `tools/verify_*.py`, Luau runner `--runner`, `verify_sources.py --compiler` | PASS 110 of 110. Includes `verify_multiplayer_sim` 681/681 checks, `verify_session1_smoke` 135/135, `verify_load` (8 and 12 players), `verify_doc_ids` (141 doc prefixes, 422 BD ids), `verify_sources` (416 Luau sources compile). First pass showed 4 failures (`verify_combat_state`, `_stats`, `_teamup`, `verify_npc_predators`) that were only my runner script not passing `--runner`; rerun with it: PASS |
| CI-only extras: `verify_load --gate-playtest`, `measure_identity_storage --check`, `simulate_fusion_ladder --check`, `generate_sfx --check`, all `bind_*.py --check`, `verify_robux_line --selftest` | PASS |
| `python -m unittest discover -s tests` | PASS 105 tests with `LUAU_RUNNER` set and numpy available. Without them: 4 import errors (`numpy` not installed in this local Python; CI installs Pillow and numpy) and 3 skips (no runner). Not a repo bug |

Every `verify_*.py` is wired into CI (`comm` of the workflow against `tools/` is empty). Offline checks prove rules, ordering and budgets against mocks. They do not prove how anything looks, sounds, feels or performs.

## 3. Release flags: what session 1 actually runs

The playtest profile (`tools/release_profiles.py`) changes these from the default build (diff computed by applying the profile to `Config.luau`):

| Flag | Default build | Playtest build | Risk note |
| --- | --- | --- | --- |
| `ReleaseProfile` / store | development / `BeDino_PrivateTest_v1` | playtest / `BeDino_Playtest_M1_v1` | fresh isolated store; rotate `_vN` to reset |
| `CaveHub` | false (verifier-required) | **true** (owner 2026-10-16) | BD-293 phone and 12-player test not done; look changed a lot since the last walk (6/10 on 2026-10-16) |
| `LowPolyDinos` | false (verifier-required) | **true** | EditableImage/Mesh patterns, 80 MiB per client, needs "Allow Mesh & Image APIs" and owner-owned assets; never proven live; legacy visual is the fallback |
| `ClassMovementEnabled` | false | **true** | Fly glide and Water dash never felt on a server. 129 s10 still says "effectively off": stale |
| `WorldArtMode` / `FoodArtMode` / `WorldArtDensity` | Legacy / Legacy / 1 | BiomeKit / Kit / 1.25 | about 1,250 props, budget <= 8,000 parts offline; culling 190 studs / 1,400 parts on phone unmeasured |
| `IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled` | false | **true** | fusion writes real (test) profiles; odds PROVISIONAL; recovery is store rotation |
| `RunTelemetryEnabled`, `PlaytestFeedbackEnabled` | false | **true** | log lines only; the owner must export the server log the same day |

Left OFF in both (all verifier-checked unless noted): `CombatEnabled` (instant bigger-eats-smaller stays; the Bite remote does not exist), `NpcPredatorsEnabled` is true but inert without combat, `SpecialFoodsEnabled`, `PerDinoCosmeticsEnabled`, `HatchV2`, `HatchV2Preview`, `QaOverlayEnabled`, `DemoDirectorEnabled`, `PaidRandomItemsEnabled`, `CrystalPacksEnabled`, all test grants and harnesses, `FastTravelPerk` (not enforced by any profile, see findings). Always on in both: `AdminPanelEnabled` (creator only when published; every player is an admin in an unpublished Studio copy), `StudioLocalProfilesEnabled` and `StudioTestWalletEnabled` (guarded by `IsStudio()` and `GameId == 0`), camera occlusion, world culling, `WorldGeneratedMeshes`.

The default build is a development build, not a public one: it keeps the old store, Legacy art and everything above off, but it must not be published. There is no public profile yet.

### Assets and the "71 newly bound ids" question
- On main b616687 **55 slots are bound** by #339 (10 trail icons, 7 mutation badges, 35 FX textures, 3 meadow-grass maps; the grass stays an unbound MaterialVariant) plus **12 potion icons** (#340). `python tools/upload_batch.py --list` shows **16 files still empty**: 4 Crystal Shop tab icons, 5 landing tiles, the green-spotted egg, the Eggs-page stage JPG and 5 condition eggs. If the lead has bound those 16 in a local tree, they are not on main yet; re-run this check after they land.
- Size of what is bound: the 68 bound FX, trail, badge and potion files are all 512 px or smaller (38 at 512x512, 18 at 128, 7 at 256). Even if every one were resident at once that is under about 56 MiB uncompressed with mips (upper bound, they load per effect, never measured). The 16 pending files include **five 1024x1024 condition eggs** (about 27 MiB uncompressed if all five are on screen). They are drawn small: upload them at 512 px before binding.
- The 21 UI icons that were already bound before today (`UIIconAssets.luau`) are 1024 to 1254 px sources; weather and egg icons stay resident in menus. Unmeasured on a phone; part of BD-085.
- "Large art PNGs": 92 of 288 repo PNGs are >= 1024 px (106 MB in `resources/`), but they are repo sources, references and concepts. The built place embeds none of them (33.9 MB place, mostly 16,672 WedgeParts and scripts). They load only when a bound `rbxassetid` points at an uploaded copy.
- The plants, ground props and colossal trees from today (BD-463, BD-464, BD-474, BD-475) have **empty ids** (`WorldGeneratedMeshes.luau`, 28 empty entries). Friends will not see them; they are not a risk or a feature in session 1. Same for the shock dome, light shaft and aura shell meshes of BD-433/431 (`pending` mesh slots): the moment rim and banner sweep work, the mesh shells do not.
- 9 sounds are bound; 14 other cue slots, 11 weather beds and `cave_bed` are `pending`, so those are silent or fall back. Nobody has listened to the bound ones either (docs/110).

## 4. Item table

Status key. **CODE-DONE**: merged and a named verifier checks the rule, and no human look is needed to answer the item. **NEEDS-STUDIO**: the lead can check it in an unpublished Studio copy of the playtest build (offline evidence listed, but "merged" is not "checked"). **NEEDS-OWNER**: needs publishing, a phone, a non-owner account or friends. **BROKEN/MISSING**: a real gap. Every PR number is on main.

### 4a. docs/106 owner checklist (publish steps)

| # | Item | Status | Evidence / note |
| --- | --- | --- | --- |
| 106-O1 | Merge, tag `playtest-m1-bNNN-rK`, build and verify the playtest place | NEEDS-OWNER | Build and `verify_release --profile playtest` pass locally (section 2); CI uploads `BeDino-playtest-build`. No tag exists; release record (docs/55 s6) has only a `_pending_` row |
| 106-O2 | Close extra Studio windows, open only the new place | NEEDS-OWNER | Three open Studios gave 15 fps earlier |
| 106-O3 | Publish to the existing playtest experience and start place | **BROKEN/MISSING** | BD-004 Blocked: the ids in Config may be the legacy experience (docs/55 s2 vs docs/125 s5). Owner must open Creator Hub and confirm name and ids (docs/141 s5) |
| 106-O4 | Creator Hub: private/limited to named playtesters, maturity questionnaire, devices, max players, no products, HTTP off | NEEDS-OWNER | Never done. Last alt join said "currently not available" (docs/40). 129 and 125 say max 4 players for session 1; docs/55 says 8 |
| 106-O5 | "Allow Mesh & Image APIs" ON, publish under the same owner account | NEEDS-OWNER | Needed for generated world meshes and for LowPoly patterns (docs/105 s7). Not checkable offline |
| 106-O6 | Asset permissions as a non-owner alt | NEEDS-OWNER | Never verified (docs/55 D4); if the alt cannot even join, this stops here |
| 106-O7 | Pending uploads with working fallbacks | NEEDS-OWNER | 16 images unbound, sounds mostly unbound (section 3); nothing blocks. Lead can run `upload_batch.py` then `bind_assets.py --batch` |
| 106-O8 | Restart servers after publishing | NEEDS-OWNER | |
| 106-O9 | Tell friends (private, may reset, no Robux, desktop) | NEEDS-OWNER | Wording in section 1 |

### 4b. docs/106 section 4 smoke script (published place, owner plus one alt)

| # | Step | Status | Evidence / note |
| --- | --- | --- | --- |
| 106-S1 | Owner joins: version label, `ProfileMode` Persistent, empty profile | NEEDS-OWNER | Persistent mode exists only when published. `verify_release` guards the `IsStudio()` fallbacks |
| 106-S2 | Alt: no admin panel, no FOOD counter, no Studio wallet, all images and models load | NEEDS-OWNER | `verify_admin` checks the rule; the non-admin view is live-only (docs/111 s6). Unpublished Studio makes everyone admin |
| 106-S3 | Settings persist across rejoin (sound, Calm motion, Weather) | NEEDS-OWNER | `verify_settings`, `verify_private_state` pass; additive `profile.settings` field; real DataStore never run |
| 106-S4 | 60 s walk on flat and hilly ground: camera, pickups, HUD | NEEDS-STUDIO | `verify_camera_occlusion`, `verify_movement_mobile`, `verify_hud`; BD-164/BD-255 camera rattle still unproven |
| 106-S5 | fps, prop pop-in at cull edge, props fading behind trees | NEEDS-STUDIO | `verify_world_art`, `verify_world_budget` (<= 8,000 parts); only Studio numbers exist |
| 106-S6 | Old instant predation with an alt (no health bars, no Bite) | NEEDS-STUDIO | `CombatEnabled` false verifier-required; two clients needed (Test > Local Server). Peaceful was removed (docs/115) |
| 106-S7 | Home during a run: confirmed return, no error toast | NEEDS-STUDIO | `verify_run_end_eggs`, `verify_session1_smoke` settle exactly once |
| 106-S8 | End a 2-minute run: summary, crystals, nest drop, reward cue | NEEDS-STUDIO | `verify_rewards`, `verify_nests` (overflow to crystals), `verify_session1_smoke` |
| 106-S9 | Eggs page and batch reveal, Cracked splat, Skip all | NEEDS-STUDIO | `verify_hatch_sequence`, `verify_eggs_screen`; docs/141 script A |
| 106-S10 | Odds / Details panel and Index percentages add up | NEEDS-STUDIO | `verify_odds_copy`, `verify_rarity`; layout and overflow need eyes |
| 106-S11 | Aura and trail bought with earned crystals; no Robux prompt anywhere | CODE-DONE for "no Robux" (`verify_robux_line`, `verify_release`, `verify_shop_crystals`); NEEDS-STUDIO for the purchase flow | |
| 106-S12 | Fusion on the playtest profile, result persists after rejoin | NEEDS-OWNER | `verify_fusion`, `verify_identity`, `verify_cosmetic_ownership` pass; persistence only on a published place. Fusion needs many dinos of one kind; use admin tools or accept "menu opens" in Studio |
| 106-S13 | Two clients, 5 minutes, watch for `SaveFailed`, throttle, schema warnings | NEEDS-STUDIO then NEEDS-OWNER | Offline: `verify_multiplayer_sim` 2/4/8 players; live Local Server script is docs/111 s5.6 (BD-319, BD-364) |
| 106-S14 | Leave and rejoin both; inventory, settings, nest timers | NEEDS-OWNER | `verify_session1_smoke` covers rejoin against mocks only |
| 106-S15 | Optional Android repeat of 4, 5, 8 | NEEDS-OWNER | BD-085 / BD-322 |

### 4c. docs/106 risks and "NOT ready" list, refreshed

| Item | Status now |
| --- | --- |
| Phone performance never measured (BD-085, 168, 097, 322) | NEEDS-OWNER; unchanged, now with more art and the cave in the build |
| Multiplayer untested live (BD-019, 319, 364) | NEEDS-STUDIO (Local Server) then NEEDS-OWNER; offline sim extended and green |
| DataStore profile and rollback (BD-020, BD-320) | NEEDS-OWNER; offline drill green, real publish revert never done |
| EditableImage memory (LowPoly) | **Changed since 106: no longer dormant.** `LowPolyDinos` is ON in the playtest build. NEEDS-STUDIO (`LowPolyImagesMiB` attribute, F9 memory), NEEDS-OWNER (published) |
| Camera rattle (BD-255) | NEEDS-STUDIO |
| Paid-random policy | CODE-DONE: flags false in every profile, `verify_robux_line`; the experience must still hold zero products (NEEDS-OWNER; if BD-004 resolves to the legacy experience it may own six real developer products) |
| Sound, art, balance unjudged | NEEDS-OWNER (ears and eyes); sounds mostly unbound |
| Admin panel exposure | NEEDS-OWNER (non-admin view is live-only) |
| NOT ready list: HP combat, NPC predators | CODE-DONE as off (verifier-required in default; playtest leaves it unset, see findings) |
| NOT ready list: cave hub, low-poly dinos | **No longer true.** Both are ON in the playtest profile by owner decision; treated above as risks, not as exclusions |
| NOT ready list: Robux packs, public release, 12 players, tablets, consoles | Still excluded; `CrystalPacksEnabled` and `PaidRandomItemsEnabled` false in source |

### 4d. docs/129 Studio smoke checklist (every line)

| 129 | BD / PR | Level | Status | Offline evidence / what is left |
| --- | --- | --- | --- | --- |
| 1 Welcome card, first-run copy, first egg in about 60 s | BD-377, 365..368; #200 #203 #205 #206 | BLOCKS | NEEDS-STUDIO | `verify_ftue_copy`, `verify_ftue_rules`, `verify_ftue_p1`. Copy rules pass; clipping and the 60 s first egg (12/500 rate) need a stopwatch |
| 1 Sanctuary dino is the low-poly one after a new hatch | BD-389 | BLOCKS | NEEDS-STUDIO | `verify_lowpoly_dinos`. Live asset load is NEEDS-OWNER |
| 1 Text outline readable | BD-390 | BLOCKS | NEEDS-STUDIO | `verify_text_style` |
| 1 Eaten keeps eggs, copy says so | BD-422; #244 #264 #267 | BLOCKS | CODE-DONE (rule) | `verify_run_end_eggs`, `verify_session1_smoke` (eaten player keeps eggs). Copy line is a 10-second look |
| 2 Pedestal height, dino stands on top | #251 | BLOCKS | NEEDS-STUDIO | Merged bc93dd8, but cave was reworked after (#286 organic rooms, #314, #323, #327) |
| 2 Lamp flicker slow and soft, Reduce Motion stops it | #251 | BLOCKS | NEEDS-STUDIO | `verify_cave_lighting` |
| 2 Signs readable at 10 studs | BD-292; #172 #232 | BLOCKS | NEEDS-STUDIO | `verify_hub_travel_client`, `verify_hub_walk_there` |
| 2 Overall light dim but colourful, no rain/snow/storm inside | BD-399, 383, 398, 296; #212 #323 | BLOCKS | NEEDS-STUDIO | `verify_cave_lighting`, `verify_cave_weather`, `verify_cave_overlap`; dim pass measured 0.30 luminance in #323, eyeball and a weather cycle still needed |
| 2 One tap travels between stations | BD-382; #208 | BLOCKS | NEEDS-STUDIO | `verify_hub_travel_client` |
| 2 Crystals amber in shops and HUD | BD-401, 400; #213 #227 | NICE | CODE-DONE | `verify_shop_crystals` |
| 2 (new today) Dino is exactly 1x inside the hub, island size restored on leaving | BD-480; #324 | not in 129 | NEEDS-STUDIO | `verify_hub_scale`, multiplayer sim (hub 1x for the player inside only) |
| 3 Run starts fast, camera smooth, no panic copy | BD-366 | BLOCKS | NEEDS-STUDIO | `verify_ftue_rules` |
| 3 "Follow the glow" visible in daylight | BD-396 | NICE | NEEDS-STUDIO | `verify_hub_walk_there`, `verify_owner_feedback_p1` |
| 4 Growth about 5x slower, size bar moves visibly | BD-386; #211 | BLOCKS | NEEDS-STUDIO | Rule: `verify_gameplay`, `verify_hud`. Feel is a look |
| 4 Food density and look, steady frame rate | BD-387, 167; #298 | BLOCKS | NEEDS-STUDIO | `verify_world_art`, `verify_gameplay`. Frame rate is phone-unproven |
| 4 Trees, rocks, bushes grounded on slopes | BD-395, 416, 417; #218 | NICE | NEEDS-STUDIO | `verify_owner_feedback_p1`, `verify_world_art` |
| 4 Low-poly dino: eyes and nostrils fixed while walking | BD-388 | BLOCKS | NEEDS-STUDIO | `verify_lowpoly_dinos`, `verify_dino_motion` |
| 4 Stopwatch a 5-minute run: about 15 eggs | BD-418; #226 #231 | BLOCKS | NEEDS-STUDIO | `verify_eggs`, `verify_progression`, `verify_rewards`; the sim uses the docs/119 rate, not measured food per minute |
| 5 Reveal order of 12 to 15 eggs, 1 s each, Skip all | BD-044, 437; #260 | BLOCKS | NEEDS-STUDIO | `verify_hatch_sequence`, `verify_progression` |
| 5 Hatch v2 (flag off) | BD-397 | NICE | CODE-DONE (stays off) | `verify_hatch_v2`, `HatchV2` verifier-required false |
| 5 Mutation hatch soft burst and calm loop | BD-162; #240 #321 | NICE | NEEDS-STUDIO | `verify_mutation_reveal`, `verify_hatch_fx`; textures now bound |
| 5 Nests beyond five spots become crystals, toast "Nests full!" | BD-420; #235 | NICE | CODE-DONE (rule) | `verify_nests`, session 1 smoke; toast wording NEEDS-STUDIO |
| 5 First two eggs never Cracked, Cracked later gentle and funny | BD-365 | BLOCKS | CODE-DONE (rule) | `verify_ftue_rules` (`SafeEggs`); splat sequence look is NEEDS-STUDIO |
| 6 Rare hatch banner, confetti, `shiny_bang`, one short banner for others | BD-428; #243 | NICE for session 1 | NEEDS-STUDIO | `verify_rare_hatch`, session 1 smoke. The line says "use the test grant", but test grants are verifier-forbidden: use docs/141 script B (Blood Moon + Mutation x10) instead. Confetti sheet and fanfare are unbound, so tinted sparkle and `shiny_bang` play |
| 6 Reduce Motion / Effects Off: banner and sound, no confetti | BD-428 | NICE | NEEDS-STUDIO | `test_effects_lod`, `verify_fx_moments` |
| 7 Egg odds wording "Cracked is X%" vs "hatches Y%" | BD-430; #259 | BLOCKS | CODE-DONE (numbers) | `verify_odds_copy` ties text to config; layout NEEDS-STUDIO |
| 7 Crystals tab: price on each pack or "Price soon" / "Coming soon!" | BD-430 | BLOCKS | NEEDS-STUDIO | `verify_shop_crystals`; packs are off, so the "Coming soon!" state is what friends see |
| 7 Aura and Trail shops show "For: <dino>" | BD-393 | NICE | NEEDS-STUDIO | `verify_owner_feedback_p1` |
| 7 Conditions shop eggs large and readable | BD-394 | NICE | NEEDS-OWNER | Stage JPG and five condition egg images are unbound, so the code tile-floor fallback shows (see findings on upload size) |
| 7 Fast travel perk (flag off) | BD-405, 391 | NICE | CODE-DONE (off) | `FastTravelPerk` false; not profile-enforced |
| 8 Settings > Sound sliders work, never loud or sharp | BD-081; #253 | BLOCKS | NEEDS-STUDIO | `verify_audio`, `verify_settings`; ears required |
| 8 Effects and Reduce Motion toggles | n/a | NICE | NEEDS-STUDIO | `test_effects_lod`, `verify_fx` |
| 9 Goals panel: three lines, counts match, fits one screen | BD-427; #245 #248 #256 | BLOCKS | NEEDS-STUDIO | `verify_goals` |
| 10 Dino page class line and picker | BD-423; #250 | NICE | NEEDS-STUDIO | `verify_class_picker` |
| 10 Fly glide and Water dash | BD-246; #234 #236 | NICE (stale) | NEEDS-STUDIO, raise to BLOCKS | `ClassMovementEnabled` is ON in the playtest profile, so 129's "effectively off" is wrong. `verify_class_movement`, `verify_classes` only |
| 11 Sound Lab: keep or change each cue, nothing harsh | BD-081, 343 | NICE | NEEDS-OWNER | `verify_sound_lab`; judging sound is the owner's ears |
| 12 Feedback button easy to find, 44 px, sends without lag | #261, docs/128 | BLOCKS if wanted | NEEDS-STUDIO | `verify_feedback`; output is a server log line, so reading it is NEEDS-OWNER |

Counts: the 37 lines of 129 split into 7 CODE-DONE (for the rule they test), 28 NEEDS-STUDIO, 2 NEEDS-OWNER and 0 BROKEN/MISSING. Of the 106 owner steps, 1 is BROKEN/MISSING (106-O3, the BD-004 experience question).

## 5. Lead Studio check list (15 steps, about 35 minutes)

Setup (not a step): `python tools/build.py --profile playtest`, close every other Studio window, File > Open from File on `build/BeDino-Build020-playtest.rbxlx` (unpublished, memory profile, everyone is admin). Do not edit Config. Keep Output and F9 > Log open, filter on `[Be Dino]`, warnings and errors. Report format: `<BD id> <place> <what you saw>` (docs/129). Write PASS or the failing step; failures become new BD rows, not silent fixes.

1. **Run A, 5 minutes with a stopwatch** (129 s1, s3, s4; 106 S4 S5): LET'S PLAY, read the welcome and run hint, note the time of the first egg and the EGGS number at 5:00 (expect about 15), size bar movement, 60 s over a hill for camera rattle, food density, props grounded, props fading behind trees, fps with Shift+F3.
2. **Low-poly dino while walking** (BD-388, BD-389): eyes and nostrils fixed; if Fly or Water class, try glide and dash (BD-246, now on).
3. **HOME, confirm** (106 S7, S8): immediate return, run summary, crystals, nest drop, one reward cue, no error toast.
4. **Eggs page, 5 minutes** (docs/141 script A trimmed): nest slots, OPEN one egg, open a batch of 12 to 15, check order (ordinary first), 1 s each, Cracked splat copy, Skip all, "Nests full!" if you have more than five.
5. **Mutation and rare hatch, 3 minutes** (docs/141 script B shortened): F2, Blood Moon, Food x10, Mutation x10, catch about 15 food, open the mutated egg: toast, card badge, ribbon, soft burst, rare banner (BD-428), then Reduce Motion once.
6. **Odds and shops, 3 minutes** (129 s7): Odds / Details panel and Index percentages sum, "Cracked is X%" wording, Crystals tab price text, buy an aura and a trail with earned crystals, "For: <dino>" header, no Robux prompt anywhere.
7. **Cave walk, 5 minutes** (129 s2, BD-480): pedestal feet touch, lamp breathing (and Reduce Motion stops it), signs readable at 10 studs, dim but colourful, one-tap rail travel, start Rain then Blizzard from F2 and confirm nothing leaks into the cave, dino is the same size as on the island's smallest state (1x), no overlapping props, glow guide visible.
8. **Settings and Sound Lab, 2 minutes** (129 s8, s11): sliders, Effects Full/Lite/Off, Reduce Motion, Weather options, play the five hatch rarity cues and `shiny_bang`; mark harsh ones.
9. **Goals and Fusion menu, 1 minute** (129 s9): three goal lines, counts, fits the screen; open the Fusion menu and check it opens and filters (a full fuse needs a persistent profile, owner step).
10. **Feedback button, 1 minute** (129 s12): find it, 44 px, send one entry, confirm a single `[BD-FEEDBACK]` line in Output.
11. **Memory and errors, 1 minute**: after steps 1 to 10, F9 > Memory total and Mesh, `workspace` attributes `LowPolyImagesMiB` (must stay under 80), count red lines in Log. Screenshot for BD-322.
12. **Predation with a second player, 3 minutes** (106 S6, BD-422): Test > Local Server with 2 players; the bigger eats the smaller, no health bars, no Bite; the eaten player keeps eggs and the copy says so.
13. **Four-player Local Server, 10 minutes** (docs/111 s5.6, BD-319 / BD-364): steps 1 to 10 of that script (private-state scan, hub 1x, same-second settle, rejoin, per-client caps, weather nests, shutdown). This is the one step that can be cut if time runs out; then say so in BD-364.
14. **Write the result**: a PASS or FAIL per 129 BLOCKS line and the step 11 numbers in BD-317, with screenshots in `docs/evidence/2026-10-NN-session1-studio/`.
15. **Decide the flags with the owner** from what you saw: if the cave, low-poly dinos or class movement look wrong, remove the `Rule(...)` lines in `release_profiles.py` for that flag (one PR), not a hot fix. That is the rollback lever before publishing.

## 6. Owner steps (publish, phone, friends)

1. **Fix BD-004 first (2 minutes).** Creator Hub > Creations: open each experience, write down name and id, and tell the lead which one is the playtest experience. If it is a new one, its ids replace `PlaytestUniverseId` and `PlaytestPlaceId` in Config (docs/55 s2). If it is the legacy one, check whether it owns the six Robux products; session 1 needs none.
2. **Creator Hub settings (docs/55 s4)**: Private or Limited with the named friends as playtesters (Play, not Edit); complete the maturity questionnaire; Devices Computer only unless you accept a phone friend; Max players 4; no products, passes or subscriptions; HTTP off; **Allow Mesh & Image APIs ON**; publish from the same owner account.
3. **Join check before anything else**: with an alt account (or one friend) confirm it can open the experience page and press Play. The last attempt said "currently not available" and the reason was never found.
4. **Tag, build, verify, publish**: `playtest-m1-bNNN-r1` on a green main commit; `python tools/build.py --profile playtest`; `verify_release.py --profile playtest --place ...`; close all other Studio windows; publish; note the version number; Restart servers; fill the release record row.
5. **Rollback drill (BD-020, BD-320, about 10 minutes)**: publish r1, restore the previous version in Version History, confirm the version label changed, roll forward again, record both version numbers.
6. **Smoke with the alt (106 s4)**: steps S1, S2, S3, S12, S14: version label and `ProfileMode` Persistent, no admin panel, no FOOD counter, no Robux, every image/model/sound loads, settings and a fusion survive a rejoin. Paste the server log lines for `SaveFailed`, `LeaseLost`, `SchemaError`.
7. **Phone (not needed for session 1 if Devices is Computer only)**: one Android pass, 20 minutes, 3 runs, a 15-egg reveal, fps, memory and heat (docs/55 s3, docs/127 QA kit). Until it is done, phones are NO-GO.
8. **Friends session**: 4 players max, 1 to 2 hours. Send the short note (private test, may reset, no Robux, desktop, placeholder numbers) first; ask the five questions after (docs/125 s6); export the server log the same day and run `python tools/telemetry_report.py server.log` and `python tools/feedback_report.py server.log`.
9. **Optional art**: lead runs the 16-file upload batch (docs/120), condition eggs at 512 px; sounds are the owner's job (docs/136).

## 7. Findings (small; items 1 to 4 fixed 2026-10-17, see the follow-up note below)

1. **129 s10 is stale**: it says class movement is effectively off; the playtest profile sets `ClassMovementEnabled` true. 129 s6 says to use the test grant, but test grants are forbidden by `verify_release`; docs/141 script B is the working route.
2. **Playtest profile does not require the off flags**: `CombatEnabled`, `SpecialFoodsEnabled`, `PerDinoCosmeticsEnabled` and `FastTravelPerk` are not `require`d false in the playtest rules (default requires the first three; `FastTravelPerk` is in no profile). CI builds both from the same source, so a flip is caught on the default build, but a local edit before a playtest build is not. A four-line `_flag_off` addition would close it.
3. **`verify_session1_smoke.py` forces `FastTravelPerk = true`**, which the playtest build does not enable, so the smoke covers perk purchase and fast travel that friends will not see. It also does not model `LowPolyDinos` or `ClassMovementEnabled`.
4. **docs/106 and docs/125 are partly stale** (106: `CaveHub` false, `LowPolyDinos` false, rate 4/500, max 8 players; 125 s1 NO-GO for the cave is overridden by its own addendum). This doc and 129 are the current pair. The BD-317 row still points at 106's 14-step script.
5. **Tests need numpy**: 4 import errors locally without it. CI installs it; a line in the tests README would save time.
6. **Hard stop that is easy to miss**: `DeveloperProducts` lists six Robux ids and `verify_release` only warns. If BD-004 resolves to the legacy experience, those products may really exist there.
   **Before publishing: if the playtest experience turns out to be the LEGACY one that owns real Robux developer products, the product ids in `Config.DeveloperProducts` must be cleared (or the products removed from that experience) before the playtest is published.** The flags `CrystalPacksEnabled` and `PaidRandomItemsEnabled` hide the prompts, but a real product in a friends experience is still a paid-random and no-Robux-line breach (docs/43, AGENTS.md). Do not change any id until the owner answers BD-004; this is a pre-publish checklist item, not a code change.
7. **Condition egg sources are 1024 px** and about 450 KB each; the Eggs page draws them small. Upload at 512 px.
8. **Feedback and telemetry are log-only**: Roblox keeps server logs for a short time; export the same day or the data is gone.
9. **Board hygiene**: about 320 of about 420 rows are `Review / test` and 20 are Done; 69 non-Done rows are P0. None of this changes with this audit; do not mark anything Done without the Studio or phone evidence this doc lists.

## 8. Follow-up 2026-10-17 (small findings 1 to 4 and 6 fixed)
Found above, fixed in the follow-up PR (docs, verifier and profile only; no game code and no id was changed):
- Finding 1: docs/129 s6 now points at docs/141 script B instead of the test grant; s10 now says `ClassMovementEnabled` is ON in the playtest profile.
- Finding 2: `tools/release_profiles.py` playtest rules now `require` `CombatEnabled`, `SpecialFoodsEnabled`, `PerDinoCosmeticsEnabled` and `FastTravelPerk` to be false (`_flag_off`, the same pattern `verify_release` uses). `FastTravelPerk` is false in the playtest build: it is checked, not set. `verify_release.py --profile playtest` and `tests/test_release.py` (`PlaytestOffFlagTests`) cover it.
- Finding 3: `verify_session1_smoke.py` no longer forces `FastTravelPerk = true`. It uses the real playtest values, so with the perk off it now checks that the perk purchase is refused and that rail travel is free for everyone (132 checks instead of 135). It still cannot model `LowPolyDinos` or `ClassMovementEnabled`: its output now says they are NOT MODELLED, so s5 steps 2 and 7 stay the only check of them.
- Finding 4: docs/106 and docs/125 carry a "partly superseded" banner and per-section notes pointing here; the BD-317 row points at this doc. History was not rewritten.
- Finding 6: the pre-publish warning about legacy Robux developer product ids is in finding 6 above and on the BD-004 row. No id was changed.
Not touched: findings 5, 7, 8, 9.

## Handbook check
Vibe and tone ([114](114-handbook.md)): the friends note keeps the test private, small, kid-safe and Robux-free; no copy was changed. Owner decisions of 2026-10-16 and 2026-10-17 ([115](115-decisions-log.md)) are respected: cave hub and 4 players in session 1, no Peaceful, hunting stays on, food alone must progress, admin Mutation x10 per player. Statuses use the rule that "merged" is not "checked": nothing is claimed Studio-verified or phone-verified. Docs only; no source, config or flag was changed. Doc number 145 is free on origin/main and in open PRs (144 is #347).

## 9. 2026-10-17 regression walk: BLOCKED, no Studio render (agent attempt)
Label: **CURRENT BUILD BEHAVIOR / tooling finding.** The planned end-to-end child walk of main `9a80c9b` (playtest profile, 13 steps) could **not** be done: no step was walked, no image was taken, and no PASS / FAIL is claimed for any step. Nothing in the game was found broken or fixed. The blocker is the Studio window, not the game.

What was tried (two fresh Studio windows on `regress.rbxlx`, the second after ending the first; both closed, last one at 10:54 local):
- `screen_capture` timed out on every call (Edit and Play, window maximised, topmost and on top of the z-order, even moved to screen 1). `CaptureService:CaptureScreenshot` never called back.
- Client and Edit DataModels both showed `Camera.ViewportSize` = 1 x 1 and `RenderStepped` fired 0 times in 3 s while `Heartbeat` ran at 60/s. The game itself loaded fine (`[Be Dino] redesign-020 ready`, ScreenGuis 1156 x 783, no errors or warnings other than the UIBlox `FoundationProvider` warnings in the boot log).
- Window facts read with plain Win32 and UI Automation (no screenshots): the main Studio window was **disabled** (`IsWindowEnabled` false) the whole time; a hidden, disabled 416 x 169 "Roblox Studio" dialog (a message box, no readable children) was owned by it; and the 3D viewport (`RBX::Studio::QEngineWidget`) was a separate 366 x 40 top-level window floating at the screen centre instead of docked in the main window, so the viewport stayed 350 x 1. `Escape` and `Enter` sent to it did nothing. The older `VFXLab-Packs` Studio, which renders, has the same hidden dialogs but its main window is enabled. The phone-fit agent's `phonefit.rbxlx` window shows the same disabled-main plus floating-viewport pattern as mine.
- Not the cause: z-order (mine was topmost and first), foreground (mine held it), monitor (screen 1 and 3 behave the same), cloaking, a second modal that was visible.
- Side find: `SetWindowPos(HWND_TOPMOST)` returned success but did not set `WS_EX_TOPMOST` on a fresh Studio window until the window had been minimised and restored once (`ShowWindow` 6 then 9, then `SetWindowPos` flags `0x40`).

Next try for whoever repeats it: open the playtest place in a Studio started by hand (so a person can dismiss the hidden start-up dialog), or find which start-up message box blocks the main window (suspect: a place-open prompt such as the Lighting technology migration, which VFXLab's window shows as already answered). Once the viewport reports a size above 100, run the 13-step walk from the task list with `docs/129` and `docs/141` scripts A and B. The walk and its images are still owed; keep BD-317 open.
