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

Gates for BD-502: (1) a phone run on a streaming-on copy (`tools/qa/streaming_variants.py`) reading Developer Console memory and the part count after 10 minutes of walking, to see if the engine unloads; (2) a 2-client Studio run (remote players, BD-319 / BD-364); (3) a desktop look at the far view with radius 256 (terrain and food beyond it should not be drawn, EXPECTED and not captured here; fog hides it only if the clear fog is inside 256); (4) a build option that sets the Workspace property for the profile (today `build.py` writes no Workspace properties; `verify_release` has no rule for it); (5) the radius pair chosen from the phone run (160 / 96 is the aggressive option, 256 / 128 the cautious one).

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

