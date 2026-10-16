# 106 Friends playtest readiness audit (main at 3e3e932, 2026-10-16)

Label: **CURRENT BUILD BEHAVIOR** audit, read from code and tool output. Nothing here was run on a published server or a phone. Method: read `src/shared/Config.luau`, `tools/release_profiles.py`, the consumers of each flag, docs 55, 95, 102, 105, and the kanban rows BD-004/019/020/021/085/097/168. `python tools/verify_release.py` passes for **default** (20 keys) and **playtest** (18 keys; one warning: `DeveloperProducts` still lists Robux ids, inert while the paid flags are false and no products exist in the playtest experience).

## Verdict
**GO for a small, private, owner-supervised friends playtest on desktop, after the owner steps in section 2 and one clean smoke run (section 4). NO-GO for phones, for more than about 4 players, and for any of the "not ready" items (section 5).** Phone performance and multiplayer have never been measured on the current main, so a friends playtest is also the first real data point. Say so to the friends.

## 1. Runtime flags and shipped defaults
Playtest profile changes (`release_profiles.py`): `ReleaseProfile="playtest"`, store `BeDino_Playtest_M1_v1`, `IdentityPersistentEnabled=true`, `IdentityFusionPreviewEnabled=true`, `WorldArtMode="BiomeKit"`, `FoodArtMode="Kit"`, `WorldArtDensity=1.25`. Every other row is identical in both profiles. Universe 10769812255 and place 111259822927673 are recorded (BD-004 data is in Config).

| Flag (default / playtest) | What flipping it does (read in code) |
| --- | --- |
| `CombatEnabled` false / false | true: `CombatService`, Bite remote, `CombatHud` health bars start; `PredationService` stops its instant bigger-eats-smaller. Off = no instances, no remote. Unproven on phones (BD-252/316: no two-player test). **Verifier now enforces false in the default profile** (this PR). |
| `NpcPredatorsEnabled` true / true | Only effective when `CombatEnabled` is true (`NpcPredatorService` returns first). Harmless today. |
| `CaveHub` false / false | true: cave shell terrain, cave lighting and atmosphere, Island Gate, hub travel remote, walk-up and guide clients (BD-280..293). Off: every one of those modules returns at once. Acceptance BD-293 not done. Now verifier-enforced false in default. |
| `LowPolyDinos` false / false | true: `LowPolyDinoLoader` loads 22 generated dino models; client bakes EditableImage/EditableMesh patterns (80 MiB budget). Needs "Allow Mesh & Image APIs" and owner-owned assets (docs/105 s7). Now verifier-enforced false in default. |
| `WorldArtMode` Legacy / **BiomeKit** | BiomeKit places the Blender/generated kit props (about 1,250 props at density 1.25). |
| `FoodArtMode` Legacy / **Kit** | Food variants; at most `FoodKitVisualCap` (12) native kit models, rest stay light balls. |
| `WorldGeneratedMeshes` true / true | Roblox-generated MeshParts for mapped kit props (`Arena`, `ImportedResources.loadGeneratedWorld`). Only runs with BiomeKit. A failed load keeps the kit model. Needs the experience to own the meshes. |
| `WorldArtDensity` 1 / 1.25 | Prop count multiplier. Part budget enforced offline by `verify_world_art.py` (<= 8,000). |
| `WorldCulling.Enabled` true | Client distance culling per device class (Phone 190 studs / 1,400 parts). On in both. Never measured on a phone. |
| `CameraOcclusion.Enabled` true | Props between camera and dino fade (BD-253). On in both. |
| `PaidRandomItemsEnabled` false, `CrystalPacksEnabled` false | Gate Robux crystal packs and random paid crystal items. `require false` in every profile. Do not create developer products. |
| `IdentityPersistentEnabled` false / **true**, `IdentityFusionPreviewEnabled` false / **true** | Persistent identity sidecar and the Fusion remote on real profiles. The Fusion odds roller is PROVISIONAL. |
| `StudioLocalProfilesEnabled`, `StudioTestWalletEnabled` true / true | Honoured only when `RunService:IsStudio()` and `game.GameId == 0`; `verify_release` checks the guards stay in source. Inert on a published server. |
| `CollectionTestGrantEnabled`, `ChestTestGrantEnabled`, `MutationTestSetupEnabled`, `SecurityTestHarnessEnabled`, `ArtTestHarnessEnabled`, `DuplicateSettlementProbe` all false | Test grants and harnesses; `require false` in every profile and build. |
| `AdminPanelEnabled` true / true | Admin panel for the creator user, rank 255 of the creator group, `AdminUserIds`, or unpublished Studio. Friends are not admins (verify with a non-owner in the smoke script). It can start weather and set multipliers, so do not add friends to `AdminUserIds`. Runtime only, never saved. |
| `AutoOpenRequiresPass` false | Auto-open is free for everyone. |
| `ProfileDataStoreName` | Playtest store is isolated from `BeDino_PrivateTest_v1`. Rotate `_vN` to reset (docs/55 s9). |

### Does main with defaults still behave like the previously playtested build?
**No, not exactly.** The risky, large systems (combat, cave hub, low-poly dinos, paid items) are off, and the old hub, instant predation and legacy art are unchanged. But these changes are ON by default since the last build the owner played:
- Settings menu v2 with four tabs and a new saved per-player `settings` profile field (BD-263..266).
- Odds / Details panel, shop card state, Index percent bar and paging (BD-267..270); odds text from one source (BD-300..304).
- HUD rework: EGGS plate, SIZE bar, no Island/Sanctuary text (BD-080). FOOD debug counter is Studio/admin only.
- Camera occlusion fade (BD-253), camera vertical follow smoothing .18 s (BD-164, rattle not proven), softer run-end and reward cues (BD-166/BD-257).
- Weather softening: softer volcano (BD-256), fog cap and clear-weather haze (BD-213), weather options in Settings.
- Economy retunes: `FoodCatchRate` 4/500, `GrowthPerFood` 0.5, nests 6..12 eggs, `HatchRevealSeconds` 1, exponential rarity (docs/88/89). The numbers friends see are not Build 020's.
- Eggs page v2 with five nest slots and one Next egg card, auto-open, mutation toasts and badges (BD-152/154).
- Calm-motion toggle, Fast/Calm effect settings, client distance culling, "no more cubes" fixes for eggs and dinos.
- Movement tuning (JumpPower 50, forward carry, TurnRate 16, Gravity 250).
In the playtest profile add: BiomeKit world, food kit, persistent fusion and identities, 1.25 density.

## 2. Owner checklist (agents never publish)
1. Merge this PR and the pending ones, then build from a tagged commit: `python tools/build.py --profile playtest`, then `python tools/verify_release.py --profile playtest --place <rbxlx>` (docs/55 s3, s6, tag `playtest-m1-bNNN-rK`).
2. Close extra Studio windows first (QA saw three open give 15 fps and a black 3D view when minimised). Close every old Build 016-020 window so you do not publish the wrong file; open only the freshly built playtest place.
3. Publish to the **existing** playtest experience and start place from the recorded IDs, not the legacy experience (docs/55 s4). Record the version number.
4. Creator Hub settings: access Private or Limited to named playtesters; maturity questionnaire completed; devices Computer and Phone (phone is untested, see risks); max players 8 or fewer, start at 4; no products, passes or subscriptions; HTTP requests off.
5. **Game Settings > Security > "Allow Mesh & Image APIs" = ON.** Needed for the generated world meshes, and for low-poly if it is ever switched on (docs/105 s7). Publish under the **same owner account** that generated and owns the meshes; a group-owned experience loses them. Without it the world meshes fall back to the kit models, nothing breaks.
6. Check asset permissions as a **non-owner** (alt account): uploaded FBX models, effect textures, UI images and sounds all load.
7. Uploads still pending, all with working fallbacks: trail icons (BD-178) and the ribbon texture; egg stage and five condition eggs on the published place (the old "BD-218" label has no kanban row, now BD-318); mutation badge icons (BD-190); the rest of docs/95 section D. Add each id to docs/77 as uploaded. Do not hand-write asset ids.
8. Restart servers for updates after publishing, then run section 4.
9. Tell friends: private test, progress may be reset (store rotation), no Robux, phone is experimental.

## 3. Risks, ranked
1. **Phone performance never measured (BD-085, BD-168, BD-097).** World kit at 1.25 density, the culling budget (1,400 parts) and the whole new UI have only Studio-desktop numbers (and those at about 15 fps with three Studios open). A phone friend may get low fps or a crash. Mitigation: desktop testers first; owner records one Android pass (docs/55 s5).
2. **Multiplayer untested on this main (BD-019 Studio 2/4/8-client rows not run).** Offline `verify_load.py` passed for 8 and 12 simulated players, but it is not a live DataStore. Tracked as BD-319.
3. **DataStore profile and migration.** The playtest store is fresh, so no legacy migration. New `profile.settings` is an additive optional field (the loader accepts a missing one and normalises bad values), but a rollback to code that rejects it, or any `ProfileSchemaVersion` bump, could lose data or lock players out (docs/55 s8). Offline rollback drill done 2026-10-16 ([111](111-rollback-drill.md)); the real publish revert is still not done (BD-320). Persistent identity and fusion are on in this profile and the odds are PROVISIONAL.
4. **EditableImage memory (80 MiB per client).** Only relevant if `LowPolyDinos` is switched on. It is off in both profiles and now verifier-enforced in default, so this risk is dormant. Do not enable it for the first session.
5. **Camera rattle unproven (BD-255).** The smoothing fix exists but the QA run could not show it works. Friends on hilly biomes may report shaking.
6. **Paid-random policy.** Gates are off and verifier-enforced; the playtest experience must keep zero products. Fusion with Robux-linked inputs is a policy question before any public release (AGENTS.md).
7. **Sound, art and balance unjudged.** Nobody has heard the sounds (docs/102); several icons are placeholders; economy numbers are PROVISIONAL.
8. **Admin panel exposure.** Creator-only by design; check as a non-owner that it is absent.

## 4. Smoke test script (fresh published private place, owner plus one alt)
1. Join as owner. Confirm the version label, that `ProfileMode` is Persistent and the profile is empty.
2. Join with a non-owner alt. Confirm no admin panel, no FOOD debug counter, no Studio wallet crystals, and every image and model loads (no grey boxes or cubes).
3. Open Settings. Change a sound level, Calm motion and Weather; rejoin and confirm they persisted.
4. Start a run. Walk 60 s over flat and hilly ground; check camera steadiness, food pickup, HUD (EGGS plate, SIZE bar).
5. Note desktop fps (Shift+F5 stats). Look for prop pop-in at the cull edge and props fading when the camera is behind trees.
6. With the alt, eat or be eaten: confirm the old instant predation works (no health bars, no Bite button).
7. Press Home during a run; confirm the confirmed immediate return and no error toast.
8. End a run of at least 2 minutes with a few catches; check run summary, crystals, nest drop and one reward cue.
9. Open the Eggs page and the batch; watch the one-at-a-time reveal at about 1 s each, a Cracked splat, Skip all.
10. Open the Odds / Details panel and the Index; confirm percentages add up and nothing overflows.
11. Shops: buy an aura and a trail with earned crystals only; confirm no Robux prompts anywhere.
12. Fusion (playtest profile): fuse a legal set, confirm the result and that consumed dinos vanish; rejoin and confirm it persisted.
13. With both clients in one server, run 5 minutes; watch server output for `SaveFailed`, throttle or schema warnings.
14. Leave and rejoin both; confirm inventory, settings and nest timers. Record fps, errors and the output in the release record (docs/55 s6).
15. (Optional, owner Android) repeat 4, 5 and 8 on a phone and record fps and any crash.

## 5. Explicitly NOT ready
- HP combat, NPC predators, Bite, Peaceful mode (BD-243..252, BD-316).
- Cave Sanctuary and hub travel (BD-280..293).
- Low-poly generated dinos and their EditableImage patterns on a published server (BD-225, BD-306..309).
- Robux crystal packs, paid random items, any monetization (BD-140, docs/43).
- Public release, phones as a supported device, 12-player servers, tablets and consoles.
- Final sound, final icons, final economy numbers, the rarity/odds disclosure review.
- A performed rollback drill and the completed BD-019/BD-020 evidence.

## 6. Changes made in this PR
- `tools/release_profiles.py`: the default profile now `require`s `CombatEnabled`, `CaveHub` and `LowPolyDinos` to be false. A flipped flag fails CI; checked locally by setting `CombatEnabled = true`, which failed with a clear error. The playtest profile is deliberately left free so the owner can trial them there.
- `src/shared/Config.luau`: corrected a stale comment about the playtest density (said 0.35; it is 1.25).
- Kanban BD-317..BD-320 added.
