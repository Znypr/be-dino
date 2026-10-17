# Identity and fusion flags review, 2026-10-17 (BD-577)

Label: **CURRENT BUILD BEHAVIOR**, offline verifiers plus one single-player desktop Studio pass. Origin/main `54c812c4` at start. No game code and no release flag was changed. Verdicts are in [docs/145 s6](../../145-session1-readiness-2026-10-17.md) and the BD-577 row of [07 kanban](../../07-kanban.md).

Question from the session-1 pass (PR #411 (still open when this was written), `docs/evidence/2026-10-17-s1-pass/README.md` s4): `IdentityPersistentEnabled` and `IdentityFusionPreviewEnabled` are `true` in the playtest profile (`tools/release_profiles.py` lines 148 to 149) and nothing backed them. What do they change, can the rollback target still load the save, and does it work?

## 1. Offline verifiers (all passed, pinned Luau runner)

| Verifier | Result |
| --- | --- |
| `verify_identity` | passed (migration/rollback, 3,000-copy ceiling, owner isolation, 150 eggs / 300 copies, reconnect, explicit fusion boundary); 150-egg reconcile 0.09 s |
| `verify_fusion` | passed (happy path, invalid donors, consent, idempotency, rollback, lineage, storage, odds parity 200,000 samples, ladder chain 6 Base -> 2 Emerald -> Diamond) |
| `verify_rollback` | passed, 357 checks (Build 020 frozen reader vs current code with both flags ON, sample profile 87 hatched + 1 fusion) |
| `verify_multiplayer_sim` | passed, 684 / 684 checks |
| `verify_session1_smoke` | passed, 132 / 132 checks (runs the PLAYTEST profile, so both flags are ON in it) |
| `verify_load --gate-playtest` | passed (12 players, playtest flags, 48 % of the request budget) |
| `verify_doc_ids`, `verify_kanban_merge`, `verify_sources` | see the PR description |

Extra measurements made for this review (scripts in this folder, not part of CI):

* `bench-identity-cpu.luau`: sidecar cost per write. About 765 bytes per hatched dino. 1,000 dinos = 0.76 MB, 3,000 (the cap) = 2.3 MB. Per write: `encodedSize` + `reconcile` = 24 ms at 1,000 dinos, 76 ms at 3,000 (native Luau, so Roblox is slower but the same order). Not a frame problem (server only, inside `UpdateAsync`).
* `load-identity-on-off.py`: reruns the `verify_load` egg-burst scenarios with the playtest overrides on and off. Result: no difference (profile max 471 KB on, 489 KB off; 3.3 vs 3.6 MB per minute on the hottest key). So **the load harness does not grow the sidecar and says nothing about identity write volume**; the section 3 numbers below are arithmetic, not a measured run.

## 2. Pictures (Studio, `IdentityFlagsPass.rbxlx` = `build.py --profile playtest`, unpublished, one player, memory profile)

Opened 13:28, closed 13:41:27 (window PID 616, NOTOPMOST, minimised, only that process ended). Fresh profile, three short scripted runs (21 + 18 + 36 eggs, no admin boosts), eggs opened with OPEN and "Skip the rest".

| Picture | What it shows |
| --- | --- |
| `01-join.png` | Playtest build joined, `ProfileMode` "Studio preview (not saved)", `Config.ReleaseProfile` playtest, `IdentityPersistentEnabled` and `IdentityFusionPreviewEnabled` both true, store name `BeDino_Playtest_M1_v1` |
| `02-run-complete.png` | Run Complete: 21 eggs, +45 crystals |
| `03-hatch.png` | First egg hatching one at a time ("Egg 1 of 21", Dimorphodon) |
| `04-hatch-summary.png` | Auto-opened 19: 1 Epic, 11 Uncommon, 7 Common, 7 cracked |
| `05-dino-details-original-egg.png` | **Dino Details with ORIGINAL EGG** ("Hatched from: Blank, Cream, Run Egg"), prestige "Natural hatch", cosmetics "this dino only" (identity sidecar read through the `FusionAction` remote) |
| `06-fusion-preview-odds.png` | Fusion menu, Gold tab, 6 of 6 Raptors filled ("Fill for me"): guaranteed Gold, Colour 1 / Colour 2 / Shiny odds shown before FUSE |

Read back through the same remote (`list`, `details`): after the first run 14 dinos (13 `origin.kind = hatch`, 1 `legacy_unknown` = the starter Compy); after all three runs 25 dinos. The details of a hatched dino carried the full `originalEgg` snapshot (egg id `run:<runId>:1`, genes, reward config version 3) and an empty `cosmetics` block. No script error in the Output window (only the known UIBlox "FoundationProvider" warnings).

**Not done in Studio, and why:**

* **No fusion was committed.** The FUSE click was refused by the tool permission layer in this session, and I did not try another way around it. Commit, replay, consent and rollback are proven offline (`verify_fusion`).
* **No rejoin.** A single Studio Play session has one server and one player; leaving ends the session and the memory profile with it. Reload of identities after release/load is proven offline (`verify_progression`, `verify_fusion` "reload", `verify_rollback`), not live.
* **The persistent path was never run.** `ProfileRepository` sets `localPreview` (Studio, `GameId == 0`) before it looks at `IdentityPersistentEnabled`, so every Studio run takes the memory path that has always written the sidecar. **No unpublished Studio run can test `IdentityPersistentEnabled = true` against the real DataStore.** The first honest test of the flag is a published private server (docs/145 blocker 4).
