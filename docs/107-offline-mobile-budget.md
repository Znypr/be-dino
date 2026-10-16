# 107 Offline mobile budget estimate (2026-10-16, BD-321, BD-322)

Label: **ESTIMATE from source and offline tools, NOT a measurement.** No phone was used. It tells the owner where to look first when BD-085 is run; every number can be wrong by 2x. Reproduce with `python tools/estimate_world_budget.py --runner luau.exe` (prints everything below); `tools/verify_world_budget.py` (in CI) fails when a cap in section 6 is exceeded. Inputs: `Config.luau` (`WorldCulling`, density), the real placement grammar (`BiomePlacement`, `BiomeMap`, `IslandLayout`, same harness as `verify_world_art.py`), `WorldGeneratedMeshes`, `CaveHubProps`, docs 89, 104, 105, 106, `CombatConfig`, `NpcPredatorRules`, `LowPolyTexture`.

## 1. Rules of thumb used (not Roblox limits)
Low-end Android phone (about 3 GB RAM, 2019-2021 class). These are community-style planning numbers; replace them with what BD-085 measures.

| Item | Rule of thumb used |
| --- | --- |
| Parts attached and in range | about 3,000 |
| Triangles in the scene | about 250,000 |
| Total client memory | about 1,200 MB (crashes start near 1.5 GB on 3 GB devices) |
| Network receive | about 30 KB/s sustained |
| Live particles | about 300 |
| Dynamic lights | 16 (docs/104) |

## 2. What the world places (playtest profile = BiomeKit, density 1.25; default = legacy art)
Placement output at seed 1404, density 1.25. Colliders are invisible parts that are never culled. **Triangles are the weakest number:** 1,175 of 3,551 playtest props use Roblox-generated meshes (`WorldGeneratedMeshes`) whose face counts are not recorded anywhere; I use 1,630 each (the cave hub's own provisional average, `CaveHubLayout`), range 500 to 3,000. The other props use the measured Blender kit counts.

| Kind | props | colliders | tris (est, 1,630 per generated mesh) |
| --- | ---: | ---: | ---: |
| tree | 614 | 614 | 1,000,820 |
| giant tree/rock | 48 | 54 | 78,240 |
| log | 56 | 56 | 91,280 |
| rock | 187 | 336 | 304,810 |
| shrub | 1,125 | 0 | 483,862 |
| groundcover | 1,517 | 0 | 32,980 |
| landmark | 4 | 14 | 2,034 |
| **Total** | **3,551** | **1,074** | **about 1.99 M** |

| Biome (playtest) | props | colliders | tris (est) |
| --- | ---: | ---: | ---: |
| fern (33% of area) | 1,638 | 399 | 853,522 |
| conifer (24%) | 974 | 350 | 646,740 |
| meadow (14%) | 432 | 64 | 168,490 |
| badlands (10%) | 188 | 127 | 161,828 |
| marsh (8%) | 246 | 30 | 68,666 |
| volcanic (11%) | 73 | 104 | 94,780 |

Default profile (kit off, `WorldArtMode = "Legacy"`): the old baked models, about **15,762 world parts plus about 8,320 legacy food parts**, no culling of those (culling only tracks `WorldKit`). If the kit were on at density 1: 2,800 props, 900 colliders, about 1.6 M tris (est).

Always loaded, never culled: 2,400 food pickups (hidden by `LocalTransparencyModifier` only), about 600 other parts (`verify_world_art` residual), the cave hub (**300 parts, about 410,800 tris provisional**, docs/104; hub budget limit 410 / 730 k).

## 3. Distance culling effect (Config.WorldCulling, docs/89)
Prop MeshParts parented within the radius x 1.15 hysteresis, nearest first, capped by the budget. Worst spot = worst centre on a 64-stud grid over the arena.

| Class (radius / budget) | at spawn (0, 30): props | tris (est) | worst spot: props | tris (est, range at 500..3,000 per mesh) | food visible (of 2,400) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Phone (190 / 1,400) | 683 | 328 k | 905 at (-160,-160) | 551 k (182 k .. 999 k) | about 614 |
| Tablet (280 / 2,400) | 1,632 | 865 k | 1,769 | 917 k | about 1,334 |
| Desktop (440 / 5,000) | 3,408 | 1.94 M | 3,419 | 1.92 M | all |

The phone budget (1,400) is never reached with radius 190; the radius does the work, so a smaller radius is the lever, not the budget. Culling removes render cost only: **culled props stay in memory** and **all parts replicate at join** (no StreamingEnabled), so "parts loaded at join" stays **about 7,625** (3,551 + 1,074 colliders + 2,400 food + 600) in the playtest profile and about 24,700 in the default profile.

Phone scene at the worst spot with low-poly dinos on: 905 props + 1,074 colliders + 614 food + 600 other + 119 dino parts = **about 3,312 parts**, **about 551 k triangles (est)** plus dinos.

## 4. Dinos, particles, network
Peak 12 players + 5 NPCs (`NpcPredatorRules`: 2 + (12 - 1) // 3) = **17 dinos in one server**.

| Item | Legacy dinos (default AND playtest: `LowPolyDinos = false`) | Low-poly dinos (flag on) |
| --- | --- | --- |
| Parts per dino | 1,424 (compy, tyrannosaurus) to 2,400 (ankylosaurus) (resource models, 6 species counted) | 7 (docs/105) |
| Peak parts, 17 dinos | **24,208 to 40,800** | 119 |
| Peak triangles | about 194 k to 326 k (8 per wedge, ESTIMATE) | about 120 k (7,030 faces per species average, measured total 154,660 / 22) |
| EditableImage | n/a | 0.8 MiB per distinct dino, cap 24 distinct = 19.2 MiB of the 80 MiB budget (12 distinct = 9.6 MiB, measured) |

Legacy dinos dwarf the whole world (24 k to 41 k parts vs 7.6 k for props, colliders and food together). This is the largest single risk for any 12-player phone test, and **the playtest profile ships with legacy dinos**. Other species with no baked model in `resources/roblox` may differ.

Particles per second: cave 25 desktop / 10 phone (docs/104, flag off by default), cosmetics up to about 32 per dino (aura 8 to 12, trail ESTIMATE 20) x 17 = about 544/s if every dino wears both, weather concurrent cap 6,000 with phone density 0.5 (client). Lifetimes of 0.5 to 1 s put cosmetic live particles near 300, at the phone rule of thumb.

Combat replication (`CombatEnabled` is off in both profiles): HP is one byte per dino, `HpSendHz = 5`, sent as an attribute change (ESTIMATE 24 bytes each with overhead). Worst case 17 dinos all changing = 17 x 5 x 24 = **2.0 KB/s**; a typical fight of 6 = 0.7 KB/s. Far under 30 KB/s; combat is not a bandwidth risk. Join replication of 7.6 k parts is the real network load.

## 5. Top 5 things to measure first on the phone (BD-085, BD-322)
Use the playtest build, Phone class (short side under 600 px). Record device model, Android version, RAM, graphics quality setting.

1. **Dino cost with 2, 6 and 12 dinos on screen (flag off vs on).** Stats (Shift+F3 / in-game Performance Stats): Instances, Primitives, FPS; MicroProfiler (Ctrl+F6, on a phone: Settings > Performance) Render and Physics rows. Capture 10 s per count. Question: do legacy dinos (1.4 k to 2.4 k parts each) alone drop below 30 fps? Repeat with `LowPolyDinos` true.
2. **Frame time and triangles at the worst spot.** Stand at the spawn (0, 30) and at the SW conifer corner (about -160, -160); Stats: Triangles, Draw Calls, FPS, plus the admin F2 "World parts" readout (visible props / budget / radius). Capture MicroProfiler Render for 10 s. Compare with section 3: if fps is under 30 at 330 k tris, the generated-mesh triangle estimate (1,630) is too low; read real face counts then and lower the Phone radius.
3. **Memory.** Developer Console (F9, Memory tab): Total, `PlaceMemory`, Mesh and Texture parts, `GraphicsMeshParts`; at join, after 10 minutes, after 20 hatches and after fusion. Read `LowPolyImagesLive`, `LowPolyImagesMiB`, `LowPolyCacheDenied` attributes on workspace. Culling does not free RAM; this is the number that crashes 3 GB phones.
4. **Join time and join memory.** Time from tap to controllable character, the memory jump during load, whether the load gate (BD-210) times out. All 7.6 k parts replicate at join. If slow, StreamingEnabled or fewer colliders (1,074 invisible parts) is the next lever.
5. **Cave hub (flag on) and effects.** In the hub with 12 players: Triangles (hub est. 410 k, provisional) and lights; then Developer Console Network (Data Receive KB/s) during a fight (`CombatEnabled` true) and with auras/trails and weather on, plus particle count in Stats. Thresholds are in section 1.

## 6. Caps in CI and honesty
`verify_world_budget.py` caps (value now / cap, about +20%): playtest props 3,551 / 4,300; kit parts with colliders 4,625 / 5,550; parts loaded at join 7,625 / 9,150; phone props at spawn 683 / 820; phone props worst spot 905 / 1,090; phone scene parts 3,312 / 3,980; phone scene triangles (est) 551 k / 660 k; low-poly dino parts 119 / 145; low-poly image MiB 19.2 / 24; combat KB/s 2.04 / 2.5. It also prints WARN (never fails) when the phone scene is over the section 1 rules of thumb: **all three currently warn** (3,312 parts vs 3,000; about 551 k tris vs 250 k; 7,625 parts at join vs 3,000). So by these rules of thumb the playtest world is **likely too heavy for a low-end phone**, which agrees with docs/106 (NO-GO for phones). The most likely fixes if BD-085 confirms it: smaller Phone radius, generated-mesh face reduction, `StreamingEnabled`, culling colliders, and switching on low-poly dinos after BD-309.
