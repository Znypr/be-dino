# 147 StreamingEnabled experiment for phones (BD-498, 2026-10-17)

Label: **STUDIO MEASUREMENT on a desktop PC, NOT a phone.** Question from BD-498 / [146](146-phone-forecast-2026-10-17.md) risk 2: should phones get fewer food parts through (A) `StreamingEnabled` (or a streaming-friendly setup) or (B) a client-side pooled food visual? Playtest profile built twice (streaming OFF, streaming ON), opened in separate Studio windows, played on the client, numbers read with `execute_luau` on the Client datamodel. `StreamingEnabled` stays **OFF** in every shipped profile; nothing here turns it on.

**Result in one screen**

1. StreamingEnabled with default models does **not** work as is: the first run start is blocked **19 s** (client `WorldReady` can never fire from the cave), `WorldCulling` and `CameraOcclusion` miss every prop that streams in after the first look, and at the far corner a phone holds **more** parts than without streaming (6,399 vs 5,174).
2. With **three small fixes** (all in this PR, all inert while streaming is off, 17 added lines in 4 files + one 20-line module) the whole core loop works with streaming on and the phone numbers are good at join: parts at join about **4,250 vs 8,539 (-50%)**, run start **1.0 s**, 0 script errors or warnings.
3. Streaming does not unload anything in Studio (plenty of RAM), so parts accumulate while the player walks: at the far corner the saving is only about 1,400 parts. Whether a real phone unloads under memory pressure is **not measured** here.
4. **Recommendation: A (food, colliders, crystals and terrain stream; every Model Persistent), not B.** Flipping it on is a separate decision (BD-502) behind a phone run and a desktop view-range check. See s6 and the LEAD decision in [115](115-decisions-log.md) (ST1 to ST3).

## 1. What was built and measured

| Variant | File (scratch, not committed) | Workspace | What differs |
| --- | --- | --- | --- |
| off | `C:\Users\znypr\dtmp\stream-off.rbxlx` | StreamingEnabled false | `build.py --profile playtest` + the probe script |
| on | `stream-on.rbxlx` | true, target 256, min 128 | same + radii written as `<bool>` / `<int>` properties in the .rbxlx |
| off / on, forced phone | `stream-off-phone.rbxlx`, `stream-on-phone.rbxlx` | as above | the device classifiers of `WorldCulling`, `ContactShadow`, `CavePhoneGuard`, `WeatherVisuals` return Phone (Studio on a PC cannot emulate touch) |
| on, small radius | `stream-on-phone-r160.rbxlx` | true, target 160, min 96 | forced phone, radius sweep |
| on, fixed | `fix-on-phone.rbxlx` | true, 256 / 128 | the build of THIS PR (3 fixes), forced phone |

Reproduce: `python tools/build.py --profile playtest --output X.rbxlx`, then `python tools/qa/streaming_variants.py X.rbxlx Y.rbxlx [--off] [--phone] --target 256 --min 128` (new, `tools/qa/streaming_variants.py`; the probe is `tools/qa/streaming_probe.client.luau`). The default and playtest profiles are unchanged. `Workspace.StreamingTargetRadius` and `StreamingMinRadius` cannot be read or set by a Studio script (not scriptable), so they are written into the place file; they are confirmed by behaviour, the part counts follow the radius (s3).

Setup honesty: other agents' Studio windows were running on the same PC, Studio's own process dominates the memory total, the server and the client share the process, a local join has no download. So **times and total MB are rough**, part and instance counts are exact for that moment. No MicroProfiler, no frame time, no network KB/s. One client only: remote players were not tested.

## 2. Numbers

Parts = `BasePart` descendants of Workspace on the client. "Join" = hub, 8 to 24 s after Play (steady). Spawn = island (0, 30). Corner = (-160, -160) after walking from the spawn. The server has **8,539 parts** (13,011 instances): all of them replicate when streaming is off; `WorldCulling` only detaches the far props on the client, they stay in memory.

### 2.1 Desktop class (Studio as is), default models

| | off | on 256 / 128 |
| --- | ---: | ---: |
| parts / instances at join (hub) | 6,387 / 8,871 | **1,119 / 5,550** |
| parts at the island spawn | 8,404 | 5,043 |
| parts at the corner (-160, -160) | 7,823 | 7,031 |
| food parts in `Workspace.Food` (hub / spawn / corner) | 3,573 / 3,573 / 3,573 | 279 / 2,050 / 2,980 |
| `BaseParts` MB / `GraphicsParts` MB / `GraphicsTerrain` MB at the hub | 51.9 / 6.1 / 48.2 | 38.4 / 1.9 / 42.5 |
| `Stats:GetTotalMemoryUsageMb()` at the hub (whole Studio process) | 3,346 | 3,303 |
| join time to playable (character + profile + HUD) | 5.29 s | 5.38 s, but `WorldReady` never fires |
| first run start after the first tap | at once | **blocked 19.2 s** (`LastRunStartStatus` = `WorldLoading`, Active at 25.6 s of game time) |

### 2.2 Phone class (forced), parts in Workspace

| | off | on 256 / 128, default models | on 160 / 96, default models | **on 256 / 128, THIS PR (Persistent models + fixes)** |
| --- | ---: | ---: | ---: | ---: |
| join (hub) | 4,283 | 714 | 356 | **4,211** (at 6 s, props not yet culled) |
| island spawn | 4,856 | 4,331 | 1,504 | **3,601** |
| corner (-160, -160) | 5,174 | **6,399** | 3,097 | **5,080** |
| food in `Workspace.Food` (hub / spawn / corner) | 3,573 / 3,573 / 3,573 | 279 / 2,050 / 2,980 | 0 / 557 / 1,252 | 279 / 2,050 / 2,980 |
| `WorldCulling` registry (visible / known props) at hub, spawn, corner | 30, 532, 759 of 3,569 | 30 / 332, **1 / 332, 1 / 332** | 0 / 1 | 532, 762 of 3,569 |
| collider cull (kept / known), hub, spawn, corner | 10, 81, 172 of 871 | 10 / 78, 134 / 485, 172 / 735 (registry of a moving set) | 0 / 1, 69 / 72, 172 / 254 | cull skipped, the engine streams them |
| cave lights `Enabled` in the hub (Terrain attachments) | 12 of 29 | 12 of 29 | not read | 12 of 29 |
| `BaseParts` MB / `GraphicsParts` MB at the hub | 52.1 / 4.6 | 39.5 / 1.7 | 39.3 / 1.2 | not read |

- **Parts the client has to hold** (not just in Workspace, culled props stay in memory): off **8,539**. THIS PR with streaming on: about **4,250** at join (ESTIMATE = 8,539 minus the 3,573 food, 871 colliders and 200 crystal pickups that stream, plus about 280 food and 80 colliders that are near; the measured 4,211 at 6 s agrees). That is **-50%** and equals the BD-498 pool target (7,061 -> 4,383 with every id filled) without a pool.
- **Streaming does not unload in Studio.** The parts only grow with the walk (hub 4,211 -> spawn -> corner food 279 -> 2,050 -> 2,980; the hub stayed loaded 740 studs away). At the corner the Persistent variant holds about 7,100 parts (3,900 persistent + 2,980 food + 254 colliders) against 8,539: only **-17%**. As far as I know the engine only unloads outside the radius when memory is short (not re-read in the docs this session); a real phone must show it (BD-085). Not claimed here.
- Radius effect (default models): 256 -> 160 takes the hub from 714 to 356, the spawn from 4,331 to 1,504 and the corner from 6,399 to 3,097. The island is about 800 studs across, so only a radius of about 256 or less saves anything; a desktop-sized 440 would load almost the whole island.
- Join time: off 5.29 s, default streaming 5.38 s (character; `WorldReady` never), fixed 5.44 s (and the run starts after 1.0 s). A local join downloads nothing, so the real saving (fewer parts to send at join) is **not** visible in these seconds.

## 3. What was checked under streaming (core loop)

All with streaming on. No Lua error or warning in the client or server `LogService` history of the streaming-on sessions that were checked (desktop on: client and server; phone on 256; fixed build).

| Check | Result |
| --- | --- |
| Eat food (server proximity pickup) | works: growth rises, `GrowthScore` 1.5 -> 4.2 and an egg after 11.7 s in the fixed build; HUD `EGGS` counter 1, 2 |
| `FoodGlow` | works: 56 of 56 slots filled, halos on the food ([image](evidence/2026-10-17-streaming/on-desktop-island-rain-foodglow.jpg)); `ChildAdded` / `ChildRemoved` on `Workspace.Food` re-track pickups that stream in and out |
| HUD food count | works ("FOOD: 3573 Ready", EGGS) |
| Egg-catch toast | works: "You found an egg!" ([image](evidence/2026-10-17-streaming/on-desktop-egg-toast.jpg)); Run Complete card with eggs, crystals, nest ([image](evidence/2026-10-17-streaming/on-desktop-run-complete.jpg)) |
| Hub (cave) | works after going HOME: `Sanctuary` model 345 instances / 186 parts, the show-off `ProximityPrompt`, 29 `CaveLight_*` attachments (they live under `Terrain` and always replicate), 8 nest-named parts ([hub](evidence/2026-10-17-streaming/on-desktop-hub.jpg), [gate](evidence/2026-10-17-streaming/on-desktop-gate.jpg)) |
| Cave lights guard (`CavePhoneGuard`, forced phone) | works: 12 of 29 lights on at the hub, after returning from the island, and in the fixed build ([hub](evidence/2026-10-17-streaming/fixed-phone-hub-12-lights.jpg), [gate](evidence/2026-10-17-streaming/fixed-phone-gate.jpg)) |
| Weather | works: Volcanic Bloom (streaming off), Rain (on), "RAIN!" banner in the hub but no rain inside the cave |
| `WorldCulling` / `CavePhoneGuard` errors on parts not streamed in | **no error**, but `WorldCulling` is wrong with default models (s4 item 2) |
| Second run start / fall through the world | fixed build: Active after 0.1 s, standing at y 5.05 on a mesh part, no fall |
| Remote players, real stream-out under memory pressure, teleport into an UNLOADED hub, published server, phone | **not tested** |

## 4. What broke, and the cost to fix each

The client code was grepped for `WaitForChild` and `FindFirstChild` chains on world parts. Every `WaitForChild` of a world instance already has a timeout (BD-330 pass: `BeDinoArena` 60 s, `WorldKit` 20 s, `Food` 60 s, `Humanoid` / `HumanoidRootPart` 10 s), so nothing yields forever; the problems are logic, not yields.

| # | Where | What breaks with default models | Cost | Done in this PR |
| --- | --- | --- | --- | --- |
| 1 | `WorldReady.client.luau` (the `terrainLoaded` raycast loop) with `RunLifecycle.worldReady` (server gate, `WorldReadyTimeoutSeconds` 20) | the client waits for terrain at the island spawn, which is not streamed in while the player is in the hub, so it never answers; the first Explore / gate start returns `WorldLoading` for 19 s | 3 files, 16 lines | **yes**: the server skips the gate while streaming and calls `player:RequestStreamAroundAsync(spawn, 8)` before the teleport (re-checks the player and state after the wait, one guard against double entry); the client answers at once |
| 2 | `WorldCulling.client.luau` `addProp` (lines 73 to 97) | a Model streams in as an EMPTY shell first (1,591 of 3,569 shells empty at the spawn); `addProp` retries 8 x 0.5 s then forgets it forever, so **3,237 props were never registered**: no radius, no part budget, no phone cull (corner 6,399 vs 5,174); the registry never forgets props that stream out and later re-parents a dead instance | Persistent models: 1 module of 20 lines + 1 line in Bootstrap; a real fix of the registry (DescendantAdded, prune) is 25 to 40 lines and needs a Studio pass | **yes, by design**: `StreamingSetup.luau` makes every Model of `BeDinoArena` Persistent, so a prop arrives whole at join as before (inert with streaming off) |
| 3 | `WorldCulling` collider cull (`PhoneGuards.cullColliders`, BD-496) | the loose collider parts stream by distance; re-parenting a streamed-out part would bring it back (registry 78 -> 485 -> 735 of a set that is really 871) | 1 line | **yes**: skipped while streaming (the engine does it) |
| 4 | `CameraOcclusion.client.luau` `register` (lines 27 to 41) | `if #parts == 0 then return end` before `known[item]`, and it is never retried: a prop that streams in later never fades when the camera is behind it | none once models are Persistent; with default models 10 to 20 lines (register on `DescendantAdded`) | covered by item 2 |
| 5 | Teleports other than the run start (home after settle, `HubTravelService`, `FallRecovery`, respawn) | with a hub or island region unloaded by the engine, the dino could land on empty terrain (`IslandTerrain` / `CaveTerrain` voxels are not in a Model; the hub model itself is Persistent). Not reproducible here because Studio never unloaded | 3 call sites, about 15 lines, `RequestStreamAroundAsync` each | no: BD-503 |
| 6 | `CaveAtmosphere.luau:41` and `CavePhoneGuard.luau:61` `workspace:FindFirstChild("Sanctuary")` | **not streaming**: `Sanctuary` lives under `BeDinoArena`, so this is nil in every build. The cave dust emitters are never collected, and the BD-495 shaft-beam guard never runs (8 shaft beams stay on a phone, verified in Studio: 8 on, not 4) | 2 lines (`workspace.BeDinoArena:FindFirstChild`); changes the dust and beams on a phone, so a look first | no: BD-505 |
| 7 | `CaveLavaClient.luau:32` `FindFirstChild("LavaFalls", true)`, `NpcMotion:46`, `LowPolyAnimator:229`, `CombatHud:237` (`BeDinoNpcs`), `HudV2:167`, `ResourceVisuals:188, 217`, `FoodGlow:176` | fine in the test: the lava folder is inside the Persistent `Sanctuary`, the NPC and food folders are always present, the food loops use `ChildAdded` / `ChildRemoved`; a far NPC or pickup simply disappears | 0 | no change |

Other gotchas found, for a later switch-on: the **desktop view range** shrinks to the radius for terrain and food (the place has ONE radius, `WorldCulling` has 190 / 280 / 440 per device), `StreamingMinRadius` is a promise to the engine (a phone may get the minimum), `StreamingIntegrityMode` was not tried, and remote players' characters stream too (BD-364 two-client run).

## 5. Why A and not B

- **B has no mechanism of its own.** BD-498 step 4 ("stop replicating the real food parts to phone clients") cannot be done per device in Roblox. The server's 3,573 food parts replicate to everyone unless `StreamingEnabled` is on; a client pool on top of unchanged replication still holds all 3,573. B only works if food stops being server parts for EVERY device (server data only, clients build local visuals), which changes desktop and tablet, `FoodGlow`, `WorldCulling`, `HudV2`, `ResourceVisuals` and the core loop.
- **A is already built and measured**: -50% parts at join (4,250 vs 8,539) with 20 + 17 lines, the loop, hub, weather and toast working, food and colliders stream, the hub is Persistent.
- A and B can combine later; B is the answer only if a phone run shows streaming does not unload.
- A is **not free**: place-wide radius (s4), unmeasured unload (s2), remote players and teleports untested. That is why the flip is a separate row.

## 6. Recommendation and rows

**A: StreamingEnabled with every Model Persistent, radius 256 / 128 (PROPOSAL), flag OFF.** Rows (Backlog, [07](07-kanban.md)): **BD-506** (Review / test) the three code fixes of this PR; **BD-502** (P1) the flip, with the gates below; **BD-503** (P2) `RequestStreamAroundAsync` before the other teleports; **BD-504** (P3) harden the prop registries for non-Persistent models; **BD-505** (P2) the `Sanctuary` lookup of s4 item 6; **BD-498** updated with this result (stays P2, B parked).

Gates for BD-502 (gate 4 done in s8, gates 3 and 5 done in s9): (1) a phone run on a streaming-on copy (`tools/qa/streaming_variants.py`) reading Developer Console memory and the part count after 10 minutes of walking, to see if the engine unloads; (2) a 2-client Studio run (remote players, BD-319 / BD-364); (3) a desktop look at the far view with radius 256 (terrain and food beyond it should not be drawn, EXPECTED and not captured here; fog hides it only if the clear fog is inside 256); (4) a build option that sets the Workspace property for the profile (today `build.py` writes no Workspace properties; `verify_release` has no rule for it); (5) the radius pair chosen from the phone run (160 / 96 is the aggressive option, 256 / 128 the cautious one).

## 7. Honest limits

- Studio on a PC, not a phone and not a published server: no real join size, no download time, no unload under memory pressure, no frame time.
- Forced-phone copies change only the device classifiers; touch input, screen size and real memory are not emulated.
- Part counts are exact at the time of the call; "parts the client holds" for the off case is the server count (8,539), for the on case an ESTIMATE from it.
- Total MB is the whole Studio process (client and server together plus Studio, about 3.3 GB of which `Internal`, `LuaHeap` and `Script` are about 2.9 GB). Per-tag changes (BaseParts -13 MB, GraphicsParts -2 to -4 MB, GraphicsTerrain -6 MB at the hub) are real but small; do not read them as phone savings.
- Evidence images: [evidence/2026-10-17-streaming/](evidence/2026-10-17-streaming/) (client views, streaming on: island with rain and food glow, egg toast, run complete, hub and gate on desktop; island spawn, hub with 12 lights and gate on forced phone with the fixes).

## 8. Addendum 2026-10-17 (BD-503 PR): gate 4 and the teleports

- **Gate 4 done:** `python tools/build.py --profile playtest-streaming --output X.rbxlx` writes `Workspace.StreamingEnabled = true`, `StreamingTargetRadius = 256`, `StreamingMinRadius = 128`, `StreamingIntegrityMode = Default` (enum values read in Studio: Default 0, Disabled 1, MinimumRadiusPause 2, PauseOutsideLoadedArea 3). The profile is a scratch one (never published, never uploaded by CI); `default` and `playtest` write nothing and `verify_release` fails a shipped profile with streaming ON unless it carries a `BD-502:docs/<evidence file>` gate field. `tools/qa/streaming_variants.py` starts from that build instead of hand-editing the place. Studio read back `StreamingEnabled = true`; the radii are not scriptable, as before.
- **BD-503 teleports:** all server teleports ask the client to stream the target first (s4 item 5 is now built, see the BD-503 row). Studio on a PC, streaming ON: run start 1.6 s, home at the hub on Terrain, hub travel on Terrain, 0 errors; no unload happens there, so the real effect stays for the phone run (BD-502 gate 1). Images: [island](evidence/2026-10-17-stream-prep/run-start-island-streaming-on.jpg), [hub station](evidence/2026-10-17-stream-prep/hub-travel-nests-streaming-on.jpg).
- Note for Studio sessions driven by the MCP `execute_luau`: it resets `CameraType` to Fixed after each call (console line "The execute_luau changed camera type"), so a screenshot right after a teleport can show the old camera position; set the camera to Custom again before capturing.


## 9. BD-502 gates 3 and 5: desktop far view and the radius pair (2026-10-17)

Label: **STUDIO MEASUREMENT on a desktop PC (Studio, one client), NOT a phone.** Images: [evidence/2026-10-17-stream-radius/](evidence/2026-10-17-stream-radius/) (`off-*` = streaming OFF reference, `r256-*`, `r320-*`, `r440-*` = target radius of the pair). Builds: `python tools/build.py --profile playtest-streaming` plus `python tools/qa/streaming_variants.py ... --target T --min M` for 256 / 128, 320 / 160 and 440 / 200, and `--profile playtest` + `--off` as the reference (scratch files `sr-*.rbxlx` in the owner's `dtmp` folder, not committed). Each build was opened in its own new Studio window (1920 x 1040, play mode, real `RequestStartRun`), the dino placed with `RequestStreamAroundAsync` + `PivotTo` while the run state was paused, the camera at the default gameplay offset (13 studs behind and 4.7 up, Custom type; `CameraMaxZoom` is 110 for the zoomed-out views), weather cleared. 0 server errors or warnings in every session; client errors 0 (client warnings: 5 in OFF, 256 and 440, 9 in the 320 session, not inspected).

**Result in one screen**

1. **Props never pop in.** Every Model is Persistent (BD-506), so at every pair all 3,067 props within the desktop `WorldCulling` radius (440) are in the client from the start, exactly as with streaming OFF. What streams by distance is only Terrain, food, loose colliders and crystals.
2. **What is bare is terrain, beyond a ring that is about 1.3 x the target radius.** At the spawn the client has terrain on 36 of 36 probe points per ring up to 260 studs and on 33 / 23 / 13 / 9 of 36 at 300 / 340 / 380 / 420 for 256 / 128 (the server has 36 up to 380); 320 / 160 reaches about 380; 440 / 200 matches the server out to 420. Persistent props beyond that ring stand without ground: 37% of the props within 440 at the spawn (256), 16% (320), 1% (440); 8 of the 19 colossal-size trees in the client (336 to 427 studs away) have no ground under them at 256 / 128.
3. **Gate 3 answer: that gap is not visible at the default gameplay camera.** In the three required desktop views, plus a look-back, a 110-stud zoom-out, a far plateau view and a colossal-tree view, the picture of 256 / 128 differs from the streaming-OFF picture by 0.1 to 1.8% of the 3D area, the same as the 440 / 200 build (which loads everything) differs from OFF (1.2 to 1.35%: food glow, particles, the dino's pose). The missing ground is 330 to 430 studs away behind persistent trees in the haze (`FogStart` 220, `FogEnd` 1100, Atmosphere density 0.1, haze 0.3: fog alone does not hide it, the trees do). In the 110-stud zoom-out only 16 of 168 downward rays miss terrain at 256, against 14 on the server (the island edge). **What a desktop does lose at 256 / 128:** food beyond about 330 studs (the client holds 2,050 of 3,573 food parts at the spawn, desktop `WorldCulling` would show food to 550) and the far terrain ring; nothing else that could be seen.
4. **Gate 5 answer: no single pair is better for both, but 256 / 128 costs the desktop nothing visible, so it stays the pair (LEAD decision ST4 in [115](115-decisions-log.md)).** 320 / 160 and 440 / 200 give back far food and terrain that nobody could see in the default camera, and give up the saving (table below: at the island it falls from -24% to -13% to -2%). The risk is the phone, not the desktop (s9.3).

### 9.1 Table (Studio desktop, no unload; Parts = `BasePart` descendants of Workspace on the client)

| View (what, position) | Build | Parts | Instances | Food parts (within 550) | Terrain probes of 377 within 440 | Props within 440 with no terrain under | Parts vs OFF |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hub at join (cave, 0, 580) | OFF | 6,387 | 8,871 | 3,573 | n/a | n/a | n/a |
| | 256 / 128 | 2,039 | 4,151 | 279 | n/a | n/a | -68% |
| | 320 / 160 | 2,445 | 4,597 | 593 | n/a | n/a | -62% |
| | 440 / 200 | 2,857 | 5,037 | 887 | n/a | n/a | -55% |
| V1 island spawn looking inland (0, 30) | OFF | 8,374 | 12,845 | 3,573 (3,540) | 366 | 0 of 3,071 | n/a |
| | 256 / 128 | 6,327 | 10,654 | 2,050 (2,050) | 253 | 1,133 of 3,067 | -24% |
| | 320 / 160 | 7,286 | 11,689 | 2,782 (2,782) | 312 | 495 of 3,067 | -13% |
| | 440 / 200 | 8,186 | 12,649 | 3,431 (3,425) | 365 | 28 of 3,067 | -2% |
| V2 high ground toward the colossal trees (200, 140) | OFF | 7,565 | 11,227 | 3,573 (2,900) | 274 | 0 of 1,997 | n/a |
| | 256 / 128 | 5,834 | 9,376 | 2,290 (2,261) | 258 | 106 of 1,997 | -23% |
| | 320 / 160 | 6,566 | 10,168 | 2,838 (2,685) | 273 | 6 of 1,997 | -13% |
| | 440 / 200 | 7,381 | 11,039 | 3,431 (2,860) | 274 | 0 of 1,997 | -2% |
| V3 cave gate (0, 500) | OFF | 6,653 | 9,403 | 3,573 (1,757) | 186 | 0 of 1,216 | n/a |
| | 256 / 128 | 4,922 | 7,552 | 2,290 (1,474) | 165 | 192 of 1,216 | -26% |
| | 320 / 160 | 5,654 | 8,344 | 2,838 (1,591) | 178 | 84 of 1,216 | -15% |
| | 440 / 200 | 6,469 | 9,215 | 3,431 (1,757) | 186 | 0 of 1,216 | -3% |

Food parts: the whole `Workspace.Food` folder in the client (the number within 550 studs, the desktop food radius, in brackets). The hub row is the client right after the join (8 s). Images: V1 `*-v1-spawn.jpg`, V2 `*-v2-highground.jpg`, V3 `*-v3-gate.jpg`; extra views `*-v4-zoomout.jpg` (camera at -41, 45, -61, looking at the spawn area), `*-v5-lookback.jpg` (from the high ground back at the spawn), `*-v7-east.jpg`, `*-v9-far.jpg` (far plateau, camera low), `*-v10-maxzoom.jpg` (110 studs zoom), `*-v11-colossal.jpg`.

Memory: `Stats:GetTotalMemoryUsageMb()` read 3,277 to 3,457 MB in every row and does NOT follow the radius (it is the whole Studio process, client and server together, with other windows open, so the order is noise). `GraphicsParts` MB is weakly ordered (hub 2.8 / 3.1 / 3.4 against 6.1 for OFF, spawn 6.1 / 3.8 / 3.4 against 7.6): do not read it as phone savings. The part counts are the honest signal. Run start took 0.2 s in all builds (no `WorldLoading`).

Pixel check (3D area of the screenshot, 650 x 510 px; share of pixels that differ from the OFF picture by more than 40 of 255):

| View | 256 / 128 | 320 / 160 | 440 / 200 |
| --- | ---: | ---: | ---: |
| V1 spawn | 1.38% | 1.92% | 1.35% |
| V2 high ground | 1.36% | 1.46% | 1.20% |
| V4 zoom-out | 0.19% | 0.28% | 0.16% |
| V5 look-back | 1.80% | 0.82% | 0.88% |
| V9 far plateau / V10 max zoom / V11 colossal | 0.17% / 0.09% / 0.98% | not taken | not taken |
| V3 gate (cave) | not comparable: the cave dust is random per frame | | |

The noise floor is the 440 / 200 column (it loads everything): about 1.2 to 1.35%, the dynamic food glow and particles. So no pair shows a measurable bare-terrain difference in these views. Limits: one camera per view and no sweep of directions; a probe of 36 points per ring is coarse (ring counts can be off by a point or two); the cave gate is a glowing portal inside the enclosed cave (`FX_GateGlow`, 18 x 12 studs at z 488), there is no outside view from it, so V3 only shows that the hub looks the same.

### 9.2 Colossal trees and landmarks (the fallback asked for in the task)

The suggested fallback, `ModelStreamingMode` Persistent for the colossal trees and landmarks, **is already the setting**: `StreamingSetup` makes every Model of `BeDinoArena` Persistent, so the colossal-size trees within 440 (19 in the client at the spawn) and the landmarks (dino statue, fossil display) are in the client at every pair and show in the far view. What cannot be Persistent is the ground under them (Terrain voxels are not in a Model). Under 8 of the 19 that ground is missing at 256 / 128 (the trees are 336 to 427 studs from the spawn), under none at 440. In the colossal view V11 the trees look identical to OFF. If a later look shows a floating base, the fixes in order of cost are: raise the pair to 320 / 160, a low hidden ground skirt under the far trees (an art task, not built), or a Persistent ground part under each colossal (adds parts). None is needed now.

### 9.3 Phone (reasoned, NOT measured)

- `StreamingTargetRadius` is a target. Under memory pressure the engine shrinks it towards `StreamingMinRadius`; Studio on a PC never shrinks, so that cannot be seen here (gate 1 is the phone run).
- **The pair's phone effect lives in the minimum, not in the target.** The phone `WorldCulling` radius is 190 studs and the phone keeps props to there (all Persistent), but the guaranteed terrain is the minimum, 128 studs in the proposed pair: after a shrink, props between 128 and 190 studs would stand over unloaded ground. The A/B for the phone run is therefore 256 / 128 against **256 / 192** (minimum = the phone cull radius). It is not the default, because it is untested here; `streaming_variants.py --target 256 --min 192` builds it.
- The saving is biggest where the phone spends its time: in the hub, streaming holds 2,039 parts against 6,387 (-68%) at 256 / 128, and the radius barely matters there (2,445 and 2,857 for the larger pairs); on the island the saving depends on the radius (-24% / -13% / -2%) and, with the engine unloading, would grow on a phone.
- One observation for the phone run: after a hand-rolled `PivotTo` from the island to the hub (no `RequestStreamAroundAsync`) the hub rendered half unrendered in the three captures that followed ([image](evidence/2026-10-17-stream-radius/r256-glitch-hub-half-unrendered.jpg)); the real HOME flow and `FallRecovery.teleport` (which asks for the stream, BD-503) did not show it. It supports the BD-503 design (always ask first) but was not reproduced, so it is not claimed as a bug.

### 9.4 Method notes for the next streaming session

- `Workspace.StreamingTargetRadius` and `StreamingMinRadius` are not scriptable; the builds carry them, and the effect is read as terrain probes (raycast with a Terrain-only include list) and part counts. Terrain is loaded to about 1.3 x the target radius, in cells.
- Moving the dino from a test script: the server `MovementGuard` snaps a client-side teleport back, so use the server (`RunState` attribute `Paused`, `RequestStreamAroundAsync`, `PivotTo`, back to `Active`). The camera stays Custom when the script does not touch the camera type; the screenshot tool's `camera_position` / `look_at_position` is the reliable way to frame a view.
- The `Welcome to Be Dino!` panel and the Run Complete card sit on top of the 3D view: hide them before capturing.
