# 145 Are we ready for friends session 1? Offline audit on main b616687 (BD-317, 2026-10-17); status updated at end of day and again in the evening

Label: **CURRENT BUILD BEHAVIOR** audit, offline only. Nothing here was run in Studio, on a published server or on a phone, and no game code was changed. It refreshes [125 go / no-go](125-friends-playtest-go-no-go.md) and walks the items of [106](106-friends-playtest-readiness.md) and [129](129-owner-studio-smoke-checklist.md) against what is merged today. Sources: [AGENTS.md](../AGENTS.md), [55 runbook](55-playtest-release-runbook.md), [111 multiplayer](111-multiplayer-audit.md), [115 decisions](115-decisions-log.md), [120 uploads](120-pending-owner-uploads-checklist.md), [141 Studio scripts](141-board-hygiene-stuck-rows.md), `tools/release_profiles.py`, the kanban rows BD-317, BD-085, BD-322, BD-020, BD-019, BD-004, BD-319, BD-364, BD-293.

> **Reading order (evening of 2026-10-17).** Start with **"Status update, 2026-10-17 evening"**, the current go / no-go. Next comes **"Status at end of 2026-10-17"**, the earlier go / no-go, kept as history (its closing notes say which parts later PRs overtook). Everything after the line "Morning baseline" is the audit on main b616687 (PR #346), also history. Nothing was deleted.

## Status update, 2026-10-17 evening

Label: **CURRENT BUILD BEHAVIOR** status on main `fc53fd14` (CI "Build generated Roblox place" green on that commit; merged PRs #381 to #415, the last ones being #410 to #415). Docs only: nothing was run in Studio or on a phone for this section; every number below is copied from the evidence it names. "Done" here means "a file on main shows it", and "merged" is still not "checked". The section "Status at end of 2026-10-17" after this one is kept as history; where the two differ, this one wins.

**Verdict: still NO-GO for friends session 1, and the reason has not changed.** No code blocker is known. The lead's single-player desktop Studio pass is now mostly done (blocker 5). What is left needs the owner: an experience answer, a publish, a second account, a second client, and (only if phones may join) a phone.

### 1. GO / NO-GO table (refreshed)

| # | Blocker | Open? | Who must act | Evidence / where |
| --- | --- | --- | --- | --- |
| 1 | Which experience is the playtest one, and can a non-owner join it (BD-004) | **OPEN, NO-GO** | **Owner** (2 min) | `tools/release_ids.json` is still all `null`; Config ids unchanged; BD-004 row (Blocked). [148](148-publish-runbook.md) step 1 |
| 2 | Creator Hub settings and the first publish | **OPEN, NO-GO** | **Owner** publishes; lead runs `python tools/release_playtest.py` first (it refuses while step 1 is unanswered) | [148](148-publish-runbook.md) steps 2 and 3; release record still empty; nothing published, nothing tagged |
| 3 | Rollback drill (BD-020, BD-320; hard stop of [125](125-friends-playtest-go-no-go.md)) | **OPEN, NO-GO** | **Owner** | [148](148-publish-runbook.md) step 5; rule RB1 in [115](115-decisions-log.md); offline `verify_rollback` 357 checks, [111](111-rollback-drill.md) |
| 4 | Non-owner view of the published place (no admin panel, assets load, settings and identities survive a rejoin, `ProfileMode` Persistent) | **OPEN, NO-GO** | **Owner** with an alt account | [148](148-publish-runbook.md) step 4; this is also the only live test of the identity pair ([BD-577](evidence/2026-10-17-identity/README.md): the DataStore path has never run) |
| 5 | Lead Studio pass | **MOSTLY DONE for single-player desktop Studio; the rest is listed below the table** | Lead / agent | Done: session-1 pass ([s1-pass](evidence/2026-10-17-s1-pass/README.md): 5-minute run, 7 of 7 cave weather events clean, memory read, flag decision); 13-step regression walk, no game FAIL, 19 images ([regression-walk](evidence/2026-10-17-regression-walk/README.md)); identity and fusion review with 6 pictures ([identity](evidence/2026-10-17-identity/README.md)); phone-size HUD at 836 x 390 and 667 x 375 ([phone-fit](evidence/2026-10-17-phone-fit/README.md)); BIG camera and egg toast ([big-cam-toast](evidence/2026-10-17-big-cam-toast/README.md)); Egg Odds panel ([egg-odds](evidence/2026-10-17-egg-odds/README.md)); first look at the jump / leap / land / surge poses ([poses](evidence/2026-10-17-poses/README.md)) |
| 6 | Multiplayer live (BD-319, BD-364, BD-502 gate 2) | **OPEN, NO-GO** | **Owner** (second client) | [111](111-multiplayer-audit.md) s5.6; offline simulation only (684 checks) |
| 7 | Phone (BD-085, BD-322, BD-293, BD-502 gate 1) | **OPEN**; stops being a blocker only if Devices is set to Computer only | **Owner** (Android) | [146](146-phone-forecast-2026-10-17.md) (an estimate), [147](147-streaming-experiment-2026-10-17.md) s9; `StreamingEnabled` stays OFF |
| 8 | Food pace / egg count of a normal run (BD-575, BD-418, BD-527) | **OPEN; not a blocker for the join, it is an economy decision** | **Owner** plays one run | Scripted walker: 97 eggs against the target of 15 ([s1-pass](evidence/2026-10-17-s1-pass/README.md) s1); a script is an upper bound, so a human number is missing |
| 9 | Phone-size HUD (BD-531, BD-538) | **Window-size part DONE in Studio; touch part open** (matters only with phones) | Phone (owner) | 836 x 390 PASS; 667 x 375 residuals fixed in #389 and re-checked, see the BD-538 row and [phone-fit](evidence/2026-10-17-phone-fit/README.md); resizing a window is layout only (no touch, memory or heat) |
| 10 | Images and sounds | Images **CLOSED**; sounds mostly unbound and unheard, not a blocker | Owner (ears) | [120](120-pending-owner-uploads-checklist.md) |
| 11 | Code and offline checks | **CLOSED as far as known** | Lead | CI green on `fc53fd14`; telemetry now logs real raw food (#414, offline only) |
| 12 | Fusion for testers (BD-577): may testers do an irreversible fusion on PROVISIONAL odds that the menu shows as exact? | **OPEN, owner decision; not a code blocker** | **Owner** | Section 6 below ("Identity and fusion flags"), [identity](evidence/2026-10-17-identity/README.md); no fuse-only switch exists (that is a code change) |

**Blocker 5, what is still missing.** None of it needs the owner's hands; it is Studio work, or needs a phone or a published place:

* The feedback send ("Tell us!" button is there; a send was never tried).
* ~~A Fly or Water dino in a real run.~~ **Done in numbers, 2026-10-17 late ([rewalk](evidence/2026-10-17-rewalk/README.md)):** Pteranodon and Mosasaurus equipped through `EquipSpecies`, class speeds and jump power match, eating works, 1 catch = 1 egg for both, the Water dash moved 14.5 studs by the real Space key. **Found: the Fly glide and hover cap never acted** (the client owns the character, so the server velocity write does nothing; fall 45 to 58 studs/s with the glide held, cap 12). The glide is fixed on the client in BD-593; the hover cap is left off on purpose (design call). Still open: a re-measure of the glide with the fix, and the Studio look at the Water surge after #409 (BD-556) and at the calm jumps of #405 (no pictures: display asleep).
* ~~A pattern dino (the EditableImage path).~~ **Done in numbers, 2026-10-17 late ([rewalk](evidence/2026-10-17-rewalk/README.md)):** Raptor Freckles and Mosasaurus diamond scales: all parts `LPLod = texture`, body is a 256x256 `EditableImage`, `LowPolyImagesMiB` 4.88 (42 images) and 2.44, 0 denied. No picture yet.
* A fusion commit and a rejoin in Studio (the FUSE click was refused by the tool layer; one Play session cannot rejoin). Proven offline only.
* The hall away from the Heart, the Sanctuary card after LET'S PLAY (not re-tested), the quake camera rumble, Reduce Motion together with weather, any sound.
* ~~The Dino Index and the Potion Shop buy after the Bootstrap split of BD-543 (#392).~~ **Done 2026-10-17 late ([rewalk](evidence/2026-10-17-rewalk/README.md)), on main `1dc02fba`:** walk steps 1, 7, 8, 9, 12 PASS, every HUD rectangle present and not overlapping, Dino Index lists 22 species, Dino Details opens, Potion Shop buy and use works, no game error in Output. Studio prints about 40 `Failed to upload TexturePack` errors at Play start (38 PBR `SurfaceAppearance` under `Resources`, HTTP 429); not a game error, cause not found. No pictures (display asleep).
* A human 5-minute run (BD-575).

### 2. Owner steps, in order

Send every answer to the **inbox session** (the owner inbox), one line each. Times are estimates. Steps 1 to 4 gate session 1 (about 40 minutes in total); step 6 only if phones may join.

1. **BD-004, which experience (2 min).** Creator Hub, Creations; for the playtest experience write `name, universe id, place id, new or legacy` ([148](148-publish-runbook.md) step 1). Send it to the inbox session.
2. **Publish with the runbook (13 min: settings 8, publish 5).** [148](148-publish-runbook.md) steps 2 and 3, after the lead says the build and tag are ready. Send the Roblox version number.
3. **Alt-account smoke (15 min).** [148](148-publish-runbook.md) step 4: can the alt join, no admin panel, assets load, a save survives a rejoin. Send `pass` or `fail` per line, plus a screenshot of anything wrong.
4. **Rollback drill (10 min).** [148](148-publish-runbook.md) step 5: publish r1, restore r0, roll forward. Send both version numbers and "profile loaded both times: yes or no".
5. **2-player run (15 min).** Studio Test > Local Server with 4 players ([111](111-multiplayer-audit.md) s5.6, 10 min), then 5 minutes with 2 clients on the streaming-on copy ([147](147-streaming-experiment-2026-10-17.md) s9.4). Send the output lines it asks for.
6. **Phone run (45 min; only if phones may join).** [146](146-phone-forecast-2026-10-17.md) s7 and [55](55-playtest-release-runbook.md) s3, plus 10 minutes of walking on each streaming copy, radius pair 256/128 against 256/192 ([147](147-streaming-experiment-2026-10-17.md) s9.3). Send memory, part count and fps for each.
7. **ONE normal 5-minute run (8 min; BD-575).** Studio, playtest build, play like a child: no scripts, no admin values. Send the Run Complete "Eggs found" number, whether a weather event came, and the `[BD-TELEMETRY] run_end` line (it now carries real `food_raw`). The target is about 15; the scripted walker made 97.
8. **Fusion for testers (2 min; BD-577).** Keep both identity flags on (the lead recommends it), turn both off, or ask for a fuse-only switch (a code change). Send one word.
9. **Grass pick, A / B / C (2 min; BD-528).** Look at `docs/evidence/2026-10-17-grass-ab/contact-sheet-A-B-C.jpg`; the lead recommends A. Send the letter.
10. **Swimmer LEAP pick (2 min; BD-569, owner question C-46 / Q20).** [101](101-hp-combat-classes-animations.md) s19: A keep the ordinary leap, B long low dash (the lead's proposal), C dash only in water. Send the letter.
11. **VFX packs lab walk (10 min).** `C:/Users/znypr/dtmp/VFXLab-Packs.rbxlx` (outside the repo); questions in [144](144-vfx-packs-trial.md) s8. Send go or no-go for BD-493 and whether the puff id looks right.
12. **V3 Compy file location (1 min).** No doc or kanban row names where it lives. Send the folder or Studio place. Not needed for session 1.

### 3. Built but switched off

All four are off in `Config`. Objectives and gifting are pinned off in `tools/release_profiles.py` (`verify_release` fails a build that flips one); streaming ON in a shipped profile needs a gate field with an evidence file; `FoodPickupAtMouth` is only warned about by `tools/release_playtest.py` (it is not a `release_profiles.py` rule).

| Feature | Rows | Flag (value today) | The one condition to switch it on |
| --- | --- | --- | --- |
| Objectives | BD-072 to BD-077, BD-561, BD-562 | `ObjectivesEnabled` (false) | A Studio pass with the flag on in a private copy that follows one real event to a claimed reward (the hooks of BD-074 and the goal line of BD-076 have no Studio evidence; the panel has desktop and 836 x 390 pictures in [objectives-panel](evidence/2026-10-17-objectives-panel/README.md)), then the owner accepts the PROVISIONAL rewards ([66](66-intake-mini-objectives.md)). The icons (BD-077) are art only and not needed |
| Gifting | BD-451 core is merged; BD-452 (admin page) and BD-570 (player UI) are not built | `GiftClaimEnabled`, `AdminGiftsEnabled`, `GiftingEnabled` (all false) | The owner signs the go-live list of [134](134-gifting-spec.md) s12 (blocked-ids call checked in Studio, policy read, copy check, one audited test gift, PROVISIONAL numbers). The free admin path needs BD-452 built first and a published place for the first live test of the inbox; Robux gifting also needs BD-453. Offline only so far (`verify_gifts`) |
| Eating at the mouth | BD-515, BD-521, BD-522, BD-527 (MR6 in [115](115-decisions-log.md)) | `FoodPickupAtMouth` (false) | Two real 5-minute Compy runs in Studio, flag off then on, read from `LastRunFood` or the telemetry line: under about 10% lift and the lead turns it on; otherwise the owner picks an option in BD-527 (the offline simulation says +18% to +37% Compy food per minute, [food-reach](evidence/2026-10-17-food-reach/README.md)) |
| Streaming | BD-502 (ST1 and ST4 in [115](115-decisions-log.md)) | `StreamingEnabled` (not set, off) | Gate 1 (a phone run reading memory and parts after 10 minutes, 256/128 against 256/192) and gate 2 (a 2-client run) both pass; gates 3, 4 and 5 are done ([147](147-streaming-experiment-2026-10-17.md) s9). Then its own one-line PR |

### 4. Today's key numbers

Each line says what it is and what it is not. All Studio numbers are desktop, one player, no phone, no published server.

| Number | Value | Evidence | Read it as |
| --- | --- | --- | --- |
| Scripted 5-minute run | **97 eggs at 5:00** (99 at the end) against the target of **about 15**; about 3,710 real food (docs/119 expects 600 to 700), +183 crystals, +4 nests; 89 eggs in clear weather | [s1-pass](evidence/2026-10-17-s1-pass/README.md) s1, `docs/evidence/2026-10-17-s1-pass/raw-numbers.txt` | An upper bound: a walker never stops. The conversion itself (`FoodCatchRate` 12/500) is exact. A human run (step 7) is what answers the pace question |
| Water dash delivery (BD-572) | **1.1 studs before, 14.2 studs after** (14 to 15 on flat ground in 3 headings and on 12, 18 and 25 degree slopes; nominal 16.8; a tree collider stops it at 3.8) | [water-dash](evidence/2026-10-17-water-dash/README.md) | The Water class was forced onto the Compy model; keyboard and phone input were not used; no speed number changed |
| BIG camera fill (BD-513) | Screen height filled at scale 4.8: Spinosaurus **72% to 56.3%**, T-Rex **51% to 45.7%**, Ankylosaurus **49% to 42.3%** (camera cap 75 to 90) | [big-cam-toast](evidence/2026-10-17-big-cam-toast/README.md), [camfit](evidence/2026-10-17-camfit/README.md) | Computed from the real model box and camera at 1140 x 785; the Spinosaurus sail clears the 160 px HUD line (box top 161 px) |
| Main-chunk local variables of `Bootstrap.client.luau` (BD-543) | **198 to 144** (Luau refuses 200; the verifier warns above 170 and fails above 185) | BD-543 row in [07](07-kanban.md), `tools/verify_local_budget.py` (in CI); no evidence folder | Offline verifier, plus the s1 pass showing the HUD alive after the split; the Dino Index and Potion Shop were not re-walked after it |
| Phone forecast (an estimate, not a measurement) | With every id filled: worst-spot triangles **452,134 to 253,480** (rule 250,000); worst-spot parts **3,434 to 3,142** (rule 3,000); parts at join **8,640 to 7,061**; cave **218 parts / 221,584 triangles** against 410 / 730,000, but **30 lights (46 with player auras) against a phone budget of 16**; textures **364 to 437 MiB at RGBA8** against a PROPOSED 200 | [146](146-phone-forecast-2026-10-17.md) s0 to s3 | Arithmetic on assumptions, can be 2x off; the generated-mesh triangle counts and the GPU compression are guesses. Desktop Studio read for comparison: 6,387 parts at join, `GraphicsTexture` 60 to 136 MB over one session ([s1-pass](evidence/2026-10-17-s1-pass/README.md) s3; the Studio total contains the editor, so no verdict) |

### 5. Not verified

* **Phone:** nothing measured. The 836 x 390 and 667 x 375 checks are window resizes with a mouse: layout only, no touch, memory, heat or touch-only code paths.
* **Published server:** never published, no tag, no rollback, no non-owner asset load, no real DataStore timing; the `ProfileMode` Persistent path and the identity sidecar on the real store never ran.
* **Multi-player:** offline simulation only; no live second client, no streaming-on 2-client run.
* **Real saves:** no existing profile was migrated or reloaded; the playtest store is fresh by design; fusion persistence, nest timers and settings across a rejoin are checked against mocks only.
* Also not seen: a human 5-minute run, a Fly or Water dino in a run, the pattern path, a fusion commit in Studio, eating at the mouth with a human walk (flag off), the Water surge and the calm jumps after #405 and #409, any sound by ear.

**What this evening's merges overtook in the earlier section.** Its telemetry warning ("`food` is derived and overstates in weather") is fixed offline by #414 (`food_raw`, `eggs_food`, `weather_s`; `verify_telemetry`, no Studio). Its blocker 9 (phone-size HUD) is now Studio-checked at window size. Its owner steps 1 to 4 became the numbered steps of [148](148-publish-runbook.md); its step 5 (BD-527 two-run pace check) is folded into step 7 above plus the mouth-eating condition in section 3. The fusion ladder in section 6 below is 6 / 3 / 2 (D4 and L2 in [115](115-decisions-log.md)); the 15 / 4 / 2 figures in AGENTS.md are older.

## Status at end of 2026-10-17

> History: written earlier on 2026-10-17. Where it differs from "Status update, 2026-10-17 evening" above, the evening update wins.

Label: **CURRENT BUILD BEHAVIOR** status on main `4a9685c` (PR #379). Docs only; nothing was run in Studio or on a phone for this section. Sources: `git log origin/main` (PRs #347 to #379 merged after the 145 baseline; #374 and #291 still open), the row statuses in [07 kanban](07-kanban.md), the LEAD decisions in [115](115-decisions-log.md), [141](141-board-hygiene-stuck-rows.md) s7, [146](146-phone-forecast-2026-10-17.md) and [147](147-streaming-experiment-2026-10-17.md). CI was green on main `aba6a29` (workflow "Build generated Roblox place", `gh run list`; the run for #379 was not checked); the offline numbers of s2 below were taken on b616687 and were not re-run here. Nothing here is called Done without its evidence path, and "merged" is still not "checked".

**Verdict: still NO-GO for friends session 1.** No code blocker is known, and the lead's single-player Studio checks of today passed or found and fixed what they found. Every remaining blocker needs the owner (experience, publish, a second client, a phone) or a lead Studio pass that has not been done as a whole.

### 1. GO / NO-GO table for session 1

| # | Blocker | Open? | Who must act | Evidence / where |
| --- | --- | --- | --- | --- |
| 1 | Which experience is the playtest one, and can a non-owner join it (BD-004) | **OPEN, NO-GO** | **Owner** (2 min in Creator Hub); then lead writes the ids into Config | BD-004 row (Blocked); `src/shared/Config.luau` lines 108-109 unchanged since 2026-10-14; the only alt join said "not available" ([40](40-mesh-access-verification.md)) |
| 2 | Creator Hub settings and the first publish (private, named playtesters, Computer only or accept phones, 4 players, no products, Allow Mesh & Image APIs ON); if BD-004 is the legacy experience, clear `DeveloperProducts` first | **OPEN, NO-GO** | **Owner** publishes; lead prepares the tag and build | [55](55-playtest-release-runbook.md) s4, 145 s6 items 2 to 4; release record empty |
| 3 | Rollback drill (BD-020, BD-320): publish r1, restore r0, roll forward | **OPEN, NO-GO** (hard stop of [125](125-friends-playtest-go-no-go.md)) | **Owner** | Rule decided: RB1 in [115](115-decisions-log.md) (roll back only to the previous playtest tag, never to Build 020 after an Epic/Legendary); the offline drill is green ([111 rollback](111-rollback-drill.md)) |
| 4 | Non-owner view of the published place: no admin panel, all images, models and sounds load, settings and a fusion survive a rejoin | **OPEN, NO-GO** | **Owner** with an alt account | 106 S1 to S3, S12, S14; live-only |
| 5 | Lead Studio pass of 145 s5 (15 steps) | **DONE for single-player desktop Studio (s1 pass, late 2026-10-17); phone, published server and second player still open** | **Lead / agent** for the rest | Done today in single-player Studio: Eggs screen and OPEN loop (BD-148, BD-170, BD-371), first eggs never Cracked (BD-365), unseeded mutation catch (BD-154 Done), shops at 0 crystals (BD-445), potion icons (BD-101), one-tap travel (BD-382 Done), more than five nests (BD-420 Done), equip swap (BD-146 Done), cave dressing renders (BD-490), egg reveal fixes (BD-519, BD-525), HUD and Tell us! fixes (BD-507, BD-524); folders listed in s5. **Done in the s1 pass ([evidence](evidence/2026-10-17-s1-pass/README.md), one Studio window, playtest build, one player, desktop):** the 5-minute stopwatch run (step 1: scripted walker, no boosts, **97 eggs at 5:00 and about 3,710 food, +183 crystals, +4 nests**; the 12/500 conversion is exact, but a script is 5 to 6 times faster than the docs/119 estimate, so the egg pace is an upper bound and a human run is still needed: BD-418, new BD-575); the cave weather-leak cycle (all 7 events started by the admin remote: nothing leaks into the hall, every event returns outside; BD-383, BD-398); the memory read (step 11: desktop Studio only, `GraphicsTexture` 60 to 136 MB over the session, `LowPolyImagesMiB` never set because no EditableImage was created); the flag decision (step 15: no flag is wrong on today's evidence; the identity / fusion pair has no evidence at all and `ClassMovementEnabled` was not felt by a Fly or Water class). **Still not done:** the feedback send (step 10; the "Tell us!" button is there), Fly or Water movement in a run, a pattern dino, the hall away from the Heart, and everything that needs a phone, a second player or a publish. A partial walk in the owner checkout (`docs/evidence/2026-10-17-session1-studio/`) is not on main and is not counted |
| 6 | Multiplayer live (BD-319, BD-364, BD-502 gate 2): the 4-player Local Server script, then 2 clients on the streaming-on copy | **OPEN, NO-GO** | **Owner** runs it (needs a second client); lead prepares | [111](111-multiplayer-audit.md) s5.6; only the offline 2/4/8-player simulation exists (145 s2) |
| 7 | Phone (BD-085, BD-322, BD-293, BD-502 gate 1): measure the build and the streaming pair 256/128 against 256/192 | **OPEN**; stops being a blocker only if Devices is set to Computer only | **Owner** (Android) | [146](146-phone-forecast-2026-10-17.md) s7; guards BD-495 to BD-497 are built but unmeasured; `StreamingEnabled` stays OFF ([115](115-decisions-log.md) ST1, ST4) |
| 8 | Food pace with eating at the mouth (BD-527, BD-522) | **OPEN, not a blocker while OFF** | **Owner** picks; lead flips the flag only after | `Config.FoodPickupAtMouth = false` ([115](115-decisions-log.md) MR6); the simulation says +18% to +37% Compy food per minute if it were on; the two Studio runs are not done |
| 9 | Phone-size HUD (BD-531): EGGS plate missing in a run at 836 x 390, hub HUD overlaps | **OPEN** (matters only with phones) | **Agent** | BD-531 row; [evidence](evidence/2026-10-17-stuck-BD-148/README.md) |
| 10 | The 16 unbound images; sounds | Images **CLOSED** (bound by #349); sounds still mostly unbound and unheard, not a blocker | Owner (ears) for sounds | `python tools/upload_batch.py --list` to confirm; [120](120-pending-owner-uploads-checklist.md), [136](136-owner-art-and-sound-quick-prompts.md) |
| 11 | Code and offline checks | **CLOSED as far as known** | Lead | CI green on `aba6a29` (not re-checked for #379); s2 and s8 below |

### 2. Owner hands-on steps, in order

Times are estimates. Steps 1 to 3 gate session 1 (step 4 too if phones may join); 5 to 8 do not.

1. **BD-004, which experience (2 min).** Why: the ids in Config may be the legacy experience and the join never worked. Where: Creator Hub > Creations; write down name and id (the universe is in the address bar), then the start place id; tell the lead. Text in the BD-004 row.
2. **Publish the playtest build (about 25 min, plus 10 min for the rollback drill).** Why: nothing has been published or tagged, and blockers 2 to 4 need it. Where: Creator Hub settings and publish steps in [55](55-playtest-release-runbook.md) s4 and 145 s6 items 2 to 6 (join check and smoke with an alt account; rollback drill = publish r1, restore r0, roll forward, record both version numbers). The lead builds `python tools/build.py --profile playtest` first.
3. **2-player run (about 15 min).** Why: replication, what another client sees, a real second client (BD-364, BD-502 gate 2). Where: Studio Test > Local Server with 4 players, script [111](111-multiplayer-audit.md) s5.6 (10 min); then 5 min with 2 clients on the streaming-on copy (`python tools/build.py --profile playtest-streaming`, [147](147-streaming-experiment-2026-10-17.md) s9.4). Paste the output lines it asks for into BD-364.
4. **Phone run (about 45 min); needed only if phones may join session 1.** Why: BD-085 and BD-322 are unmeasured, and BD-502 gate 1 compares the streaming pair 256/128 with 256/192. Where: Android, [55](55-playtest-release-runbook.md) s3 and [146](146-phone-forecast-2026-10-17.md) s7 (20 min, 3 runs), then 10 min of walking on each of the two streaming copies the lead builds with `tools/qa/streaming_variants.py` ([147](147-streaming-experiment-2026-10-17.md) s9.3); read memory and part count.
5. **BD-527 two-run pace check (about 15 min).** Why: decide if eating at the mouth changes the egg count. Where: Studio, two 5-minute Compy runs with `FoodPickupAtMouth` off then on, read `LastRunFood` ([119](119-catch-rate-15-per-run.md), [115](115-decisions-log.md) MR6, BD-527 row). The lead flips the flag in a scratch config that is never committed.
6. **Grass pick, A / B / C (2 min).** Why: BD-528 waits for you. Where: `docs/evidence/2026-10-17-grass-ab/contact-sheet-A-B-C.jpg` and its README (the lead recommends A).
7. **VFX packs lab walk (about 10 min).** Why: go / no-go on adapting Pack 1 for fire auras and trails (BD-493) and a check of the puff upload id. Where: `C:/Users/znypr/dtmp/VFXLab-Packs.rbxlx` (outside the repo); questions in [144](144-vfx-packs-trial.md) s8; images `docs/evidence/review-2026-10-17/33-vfx-packs-*`.
8. **Tell the lead where the V3 Compy file lives (1 min).** Why: no doc or kanban row names its location (searched 2026-10-17), so nobody can pick it up. Where: reply in the owner inbox with the folder or Studio place. Not needed for session 1.

### 3. What agents can do without the owner (next 5 Backlog rows by priority)

1. **BD-531** (P1) phone-size HUD: EGGS plate, hub overlaps, Eggs screen scroll. Check at 836 x 390 with the window-resize stand-in ([141](141-board-hygiene-stuck-rows.md) s7); touch-only parts wait for the phone.
2. **BD-167** (P1) world density v3: new Blender kit pieces (rocks, trees, bushes, flowers, reeds, food kinds) inside the part budget; BD-199 (contact sheet, then in-game) gates each batch.
3. **BD-055** (P1) weather sky, cloud and particle completion (code and Blender textures; weather sounds stay with the owner, BD-132).
4. **BD-035** (P1) modular Blender egg, pattern, condition and mutation render passes.
5. **BD-048** (P1) Blender world VFX and the six trail rarity categories (the ten trail icons are BD-178, Review / test).

Also agent-sized, lower priority: BD-532 (BUY EGG can never succeed in the playtest, P2), BD-504 (P3), and Studio checks not yet run: the BD-372 level-3 Conditions tab, the BD-148 "Some eggs can crack!" line, BD-164 / BD-255 camera rattle (needs a quiet machine). BD-503 shipped in #365 but its row reads Backlog until open PR #374 restores it. The P0 Backlog rows (BD-021, BD-085, BD-293, BD-317, BD-322) all wait on the owner, a publish or a phone.

### 4. Not verified

- **Phone:** nothing measured. Resizing the Studio window checks layout only (no touch, memory or heat). The guards BD-495 to BD-497, BD-531 and the streaming minimum-radius risk ([115](115-decisions-log.md) ST4) are reasoned or Studio-only.
- **Published server:** never published, no tag, no rollback, no non-owner asset load, no real DataStore timing, no `ProfileMode` Persistent check.
- **Multi-player:** offline simulation only (681 checks, 145 s2); no live second client, no streaming-on 2-client run.
- **Real saves:** no existing profile was migrated or reloaded in this audit; the playtest store is fresh by design (`BeDino_Playtest_M1_v1`). Fusion persistence, nest timers and settings across a rejoin are checked against mocks only.
- Also not seen: eating at the mouth with a real human walk (flag OFF), fliers and swimmers in a real run, server hit sizes in a bite (combat flag OFF), and any sound by ear.

### 5. What merged on 2026-10-17 since the 145 baseline (PRs #347 to #379; statuses follow the kanban)

| Area | PRs and rows | Status and evidence |
| --- | --- | --- |
| Readiness doc and findings | #348 (this doc), #351 (BD-317 findings) | Docs and verifier only; s8 below |
| Assets | #349 binds 16 images; #350 cave wall rock forms and gate arch; #347 Creator Store VFX packs lab (BD-493) | Review / test; ids for plants, colossal trees and cave meshes are still empty ([146](146-phone-forecast-2026-10-17.md)); the "16 files still empty" line of s3 is superseded |
| Phone forecast and guards | BD-494 #354, BD-495..499 #359 | The forecast is an estimate ([146](146-phone-forecast-2026-10-17.md)); guards are Review / test, offline model only |
| Streaming experiment and prep | BD-498 #362, BD-503 #365, BD-502 gates 3 and 5 #370 | `StreamingEnabled` OFF in every shipped profile; gates 3, 4, 5 done in desktop Studio, gates 1 (phone) and 2 (2 clients) open: [147](147-streaming-experiment-2026-10-17.md), `docs/evidence/2026-10-17-streaming/`, `2026-10-17-stream-prep/`, `2026-10-17-stream-radius/` |
| Species size, camera, hit size | BD-500 #360, camfit #366, BD-514 #377, BD-407 #356, BD-471 #358 | Review / test; [species-sizes](evidence/2026-10-17-species-sizes/README.md), [camfit](evidence/2026-10-17-camfit/README.md); hit sizes are offline only (combat OFF) |
| Mouth reach | BD-515 #367, BD-521 #368, BD-522 #372 | Built, **OFF** per MR6; simulation in [food-reach](evidence/2026-10-17-food-reach/README.md); owner choice BD-527 |
| Mutation tint | BD-518 #369 | Review / test; [ember-tint](evidence/2026-10-17-ember-tint/README.md) |
| Eggs and hatch | BD-154 #364 (Done), BD-519 and BD-525 #375, BD-381 #353 | BD-154 Done with [evidence](evidence/2026-10-17-bd154-unseeded/README.md); [egg-reveal-fixes](evidence/2026-10-17-egg-reveal-fixes/README.md) |
| UI and HUD | BD-501 UI floor sweep #361, BD-507 #363, BD-524 #371, BD-408 `verify_handbook` #357, BD-508 toast and BD-513 BIG camera cap #379 (Studio images in `docs/evidence/2026-10-17-big-cam-toast/`) | Review / test; [ui-floor](evidence/2026-10-17-ui-floor/README.md), [hud-fix](evidence/2026-10-17-hud-fix/README.md), folder `docs/evidence/2026-10-17-bd524/` |
| Shop | BD-529 and BD-530 in #378, potion end-to-end verifier #352 | Review / test; [BD-445](evidence/2026-10-17-stuck-BD-445/README.md), folder `docs/evidence/2026-10-17-shop/` |
| Stuck rows, rounds 1 and 2 | #369, #378 | Done, each with its evidence folder ([141](141-board-hygiene-stuck-rows.md) s7): BD-170, 440, 442, 169, 094, 371, 382, 420, 146. BD-148, 365, 445, 101, 289, 490 stay Review / test with their remaining items listed there |
| Decisions | #355 (RB1 rollback rule, TX1 512 px uploads), #333 (gifting to anyone) | [115](115-decisions-log.md) |
| Board tooling | #376 `tools/next_bd_id.py`, `tools/verify_kanban_merge.py` | Run both before adding or merging kanban rows (AGENTS.md "Picking numbers") |

**What the older sections of this doc look like now.** Section 1 (verdict and top-5): blocker 2 (nobody has walked the loop) is PARTLY DONE, see blocker 5 above; the other four stand. Section 3: the "16 files still empty" is closed by #349. Sections 4 and 5: the item table and the 15-step list are still the right checklist, with the steps named in blocker 5 done in part. Section 6: replaced by the numbered list above (same steps; the rollback drill is folded into step 2; the 2-player run, BD-527, grass, VFX and V3 Compy steps did not exist this morning). Section 7 and 8: unchanged.

### 6. Identity and fusion flags: what they change and the verdict (BD-577, 2026-10-17)

Label: **CURRENT BUILD BEHAVIOR**, offline verifiers plus a single-player Studio pass. Evidence and numbers: [docs/evidence/2026-10-17-identity/](evidence/2026-10-17-identity/README.md). No flag was changed; flipping one is the owner's call (one `Rule(...)` line in `tools/release_profiles.py`, one PR, rebuild, republish; never a hot fix).

**The two flags are not independent.** Read from `src/server/ProfileRepository.luau`:

| `IdentityPersistentEnabled` | `IdentityFusionPreviewEnabled` | On a published server |
| --- | --- | --- |
| true | true | **Playtest profile today.** Sidecar written, Dino Details / My dinos / goal line / Fusion menu work, fusion commits |
| true | false | Sidecar is still written on every save, but `fusionEnabled()` is false, so `list`, `details`, `quote` and `fuse` all answer `fusion_disabled`: the player sees nothing for it. All cost, no benefit. Do not ship this combination |
| false | true | `fusionEnabled()` needs the persistent flag on a published server, so same as both off |
| false | false | Build 020 behaviour: no sidecar, no per-dino list, Fusion rail says "Fusion is coming soon", Dino Details lose the original-egg lines, the Next Goal line falls back to level XP (it asks the same remote) |

**What `IdentityPersistentEnabled` changes in the saved profile (published servers only; Studio always runs the memory path):**

* Every `UpdateAsync` of the profile (load, 30 s lease renew, crystal pickup, hatch page, run settlement, equip, settings) is wrapped by `persistentIdentityTransform`. It rebuilds `profile.dinosaurIdentity` from the grouped `collection` in the same transaction, then checks the whole profile against 3.8 MB (`IdentityProfileHardLimitBytes`).
* Fields written: `dinosaurIdentity` = `{version, ownerKey, nextId, instances{id -> species, stage, genes, big, shiny, mutationId, origin, cosmetics}, eggs{eggId -> original egg snapshot}, fusions{ledger with parentIds / parentEggIds}, suspendedReason}`. The first write for a new player creates it with one `legacy_unknown` instance (the starter Compy). A hatch adds one instance and one egg snapshot per hatched (not Cracked) egg, about 765 bytes together.
* A fusion also changes `collection[species].gold / emerald / diamond` (and removes six), appends a `recentOperations` entry of kind `identity_fusion`, and adds the result to `progression.discovered`.
* Failure behaviour is fail-closed for identity only: over 3,000 dinos (`identity_capacity`), a grouped/sidecar mismatch, a wrong owner or the byte limit sets `suspendedReason` and keeps the last good sidecar; the player keeps playing, hatching and saving, but Dino Details, My dinos and Fusion answer "unavailable". The only case that cancels a write is a profile that is still over 3.8 MB without any identity growth, which the egg bank (about 0.5 MB for 1,000 eggs) cannot reach.

**What `IdentityFusionPreviewEnabled` changes for the player:** it turns on the `FusionAction` remote answers (list / details / quote / fuse). Fusion consumes six same-species Base dinos (Gold), 3 Gold (Emerald), 2 Emerald (Diamond) for one NEW dino with freshly rolled traits using the PROVISIONAL `fusion-odds-provisional-v2` roller; the odds are shown before FUSE (picture 06) and the roll is committed once. It is blocked when `CrystalPacksEnabled` is on or the profile ever spent Robux (`paidRandomBlocked`); both are off in the playtest, so nothing blocks it there.

**Can the rollback target still load a session-1 save? Yes, and no P0 was found.**

* **RB1 target = the previous playtest tag.** None exists yet (nothing is published); when r1 follows r0 it reads the same store `BeDino_Playtest_M1_v1`. `verify_rollback` (357 checks, both flags ON): the Build 020 reader loads a profile with sidecar, ledger, settings, nests and bank, keeps every unknown field byte for byte through load, claim, renew and release, and a later roll forward reconciles the sidecar. Same code with both flags turned OFF: loads, sidecar and ledger untouched; turned ON again: reconciled. A corrupt or oversize sidecar never fails profile validation (`isValidProfile` does not read it).
* **Build 020 itself** uses a different store (`BeDino_PrivateTest_v1`), so it would not see any session-1 save at all (everyone looks reset; nothing is deleted or unreadable). If someone pointed it at the playtest store, the sidecar and `emerald` counters are ignored and kept. What locks Build 020 out of that store is **not these flags**: `metrics.rarest` 4 or 5 (an Epic or Legendary catch) and newer potion ids, which the playtest profile writes with both flags OFF too. Picture 04 shows a real Epic hatching in a one-minute run, so any rollback to Build 020 after session 1 starts is already ruled out by RB1.
* **Residual rollback risk:** a Build 020 session that hatches or fuses desyncs the sidecar; the current code reconciles it, but a larger desync (for example a Build 020 Gold decrement of a protected fused dino) suspends identity for that player until the counts match. Only reachable by rolling back to Build 020, which RB1 forbids.

**Findings (none is a blocker for session 1):**

1. **No evidence of the real persistent path exists, and none can exist offline or in unpublished Studio.** `localPreview` wins over the flag in Studio, so Studio exercised only the memory path (works: 25 dinos, original-egg details, fusion preview with exact odds, no errors). The DataStore path is covered by mocks only (`verify_load`, `verify_rollback`, `verify_progression`, `verify_session1_smoke`: 2,145 writes, 0 throttled).
2. **Per-key write volume grows with the sidecar and no test models it.** Every save rewrites the whole profile. The existing worst case already reaches about 3.5 to 4.0 MB per minute on one key with a 0.5 MB profile ([59](59-egg-rate-40.md) risk 1, limit 4 MB per minute as cited there, not re-verified against the current Roblox page). The sidecar adds about 0.77 MB per 1,000 dinos. Arithmetic, not measured: a profile of 1,000 dinos written 9 times a minute is about 7 MB per minute during a big reveal, and renews plus crystal pickups alone are about 3 to 5 MB per minute. A scripted 99-egg run hatches about 60 dinos, so 1,000 dinos is about 17 hard runs; a child at the docs/119 pace (about 15 eggs per run) needs far more. Not a session-1 risk; a later-weeks one (the 3,000 cap, 2.3 MB, is reached after about 50 hard runs).
3. **The identity cost is small in CPU:** 24 ms (1,000 dinos) to 76 ms (3,000) per write, server only.
4. **The fusion odds are shown as exact but are PROVISIONAL** (`fusion-odds-provisional-v2`); the menu does not say "test odds". Fusion is destructive (six dinos gone) and was not committed in Studio (the click was blocked by the tool permission layer; commit, replay, consent and rollback are proven offline).
5. **No rejoin evidence:** one Studio Play session cannot rejoin. Identities surviving release and load are proven offline only. This is the live check of blocker 4 above.

**Verdicts for session 1 (recommendations; the owner decides):**

| Flag | Verdict | Why | Condition / how to undo |
| --- | --- | --- | --- |
| `IdentityPersistentEnabled` | **Keep on** | Offline evidence is strong (357 rollback checks, 684 multiplayer checks, 132 smoke checks, all additive, previous-tag rollback loads). Turning it off removes Dino Details, My dinos, the goal line list and fusion for everyone, and the playtest exists to test them. The damage it could do is bounded: a fresh private store, extra bytes, an unavailable menu, recovery by store rotation | **Gate:** the first non-owner join must show `ProfileMode` "Persistent", a fusion-menu list that returns dinos, and the same identities after leaving and rejoining (blocker 4). If any of the three fails: remove the one `Rule` line, rebuild, republish, rotate the store if a profile was damaged |
| `IdentityFusionPreviewEnabled` | **Needs owner** (lead recommendation: keep on) | It is the switch for all per-dino screens, not only fusion, so "off" is a bigger product change than it sounds. What the owner should decide is whether session 1 testers may do an irreversible six-for-one fusion on provisional odds that the menu shows as exact. The paid-random policy is not triggered while Robux features stay off | If the owner says no to fusion but yes to the per-dino screens, that needs a code change (a fuse-only gate), not a flag flip; there is no such switch today |

If the owner wants the smallest possible risk for session 1 and accepts losing those screens, turn **both** off together (never one: Persistent on with Preview off writes the sidecar for nothing).

---

## Morning baseline below (2026-10-17, main b616687), kept as history

## 1. Summary (one screen) - HISTORICAL, morning of 2026-10-17

Superseded in part by "Status at end of 2026-10-17" above: use its GO / NO-GO table. The verdict and the five blockers below are kept as written.

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

_Update end of 2026-10-17: the flag table still matches the playtest profile; `StreamingEnabled` and `FoodPickupAtMouth` are OFF in both profiles, and the "16 files still empty" line below was closed by #349._

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

## 6. Owner steps (publish, phone, friends) - HISTORICAL

Replaced by the numbered list in "Status at end of 2026-10-17" section 2 (same steps in the same spirit, plus the new ones).

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

**Update (BD-541, offline):** the 13 steps now exist as Studio scripts with a call order, per-step assertions and capture points: [tools/qa/regression_walk/README.md](../tools/qa/regression_walk/README.md). They are checked offline by `tools/verify_regression_walk.py` against a mock game; the first real run in a rendering Studio window is still owed, and BD-317 stays open until then.

**Update (BD-541, Studio run 2026-10-17, closed 11:49:47):** the walk was run in one rendering Studio window (viewport 1140 x 785, RenderStepped 44 per second) on the playtest build `redesign-020`, unpublished copy. All 13 steps ran; **0 game FAIL: 5 PASS (2, 3, 4, 5, 10), 4 PASS after a script fix (7, 8, 11, 13), 4 ODD (1, 6, 9, 12)** (ODD = a tap the script could not make or a module copy it could not read; the game did what it should). Table, 19 images and every output line: [docs/evidence/2026-10-17-regression-walk/README.md](evidence/2026-10-17-regression-walk/README.md). Output errors from `src/`: none (server log clean since the baseline; the only client warnings are the Studio tool's own camera notice and the UIBlox boot warnings). Label: **STUDIO EVIDENCE on a desktop-size window, not a phone.**

* The scripts needed fixes, made in the same PR: hatched copies live in `variants[].count`; the HOME label flips 0.15 s after RunState; potion actions are rate limited to 0.4 s and the Studio test wallet resets on every action; the Random Egg is COMING SOON (BD-532); `require` of a game module from a snippet is a second copy of its state (Fusion, Settings, UITheme, server PrivateState), so those checks read the screen and `SettingsJson`. `VirtualInputManager` is blocked in `execute_luau`: every tap was a printed `NEEDS click x,y` clicked by hand.
* One game bug found and fixed: the RAIN! weather card came back half visible in the hub after it had faded (`titleBig` not cleared; `verify_cave_weather` now checks it). Not re-run live.
* One finding left open: **BD-546** (menu cards cover the left rail by 43 px at 1140 wide; Crystals tab shows R$ buttons under Coming soon, confirm inert).
* Still owed: a phone-size run, a published server, more than one player. BD-317 may take the lines; BD-541 is Review / test with this evidence.
