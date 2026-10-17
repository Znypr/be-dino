# 146 Phone forecast: what a phone carries once everything is uploaded (BD-085, BD-322, 2026-10-17)

Label: **ESTIMATE from source and offline tools, NOT a measurement.** No phone, no Studio, no asset id written (the fake ids live only in memory). It answers one question before the owner uploads the pile of new art that is wired behind empty ids: if every id were filled today, which phone budget would break, by how much, and what is the cheapest fix? Reproduce every table with one command:

`python tools/qa/phone_forecast.py --runner luau.exe` (about 15 s; add `--check` for the CI mode, section 5).

Inputs: the real placement grammar (`IslandLayout`, `BiomeMap`, `BiomePlacement`, same harness as [107](107-offline-mobile-budget.md)) via `tools/estimate_world_budget.py`, now with a mode `PROPS_IDS = 'all'` that fills the ids of the 16 Blender plants and ground props, the 3 V3 trees and (through `ColossalRules`, as in [142](142-colossal-lod-budget.md)) the 6 colossal meshes; `CaveHubLayout.budgetTable()` and `CaveLightingRules` for the cave; `tools/asset_slots.json` for the images; `tools/fx_budget_report.py` for particles, beams, trails and lights; budgets in `tools/qa/phone_budgets.json` (one file, now also holding the [107](107-offline-mobile-budget.md) s1 rules: parts 3,000, triangles 250,000, memory 1,200 MB, plus a PROPOSED `textureMib` 200). Labels: **MEASURED** (read from a repo file or a Blender report), **ESTIMATE** (arithmetic on an assumption, can be 2x off), **PROPOSAL** (a number I chose, owner or BD-085 can overrule). Playtest profile (`CaveHub` and `LowPolyDinos` ON, density 1.25, seed 1404), Phone class (radius 190, budget 1,400, hysteresis 1.15), 12 players + 5 NPCs.

## 0. Headline (one screen)

1. **Uploading the world art makes the phone island lighter, not heavier.** Worst-spot triangles **452,134 today -> 253,480** with every id filled (-44%; the range is 141,610 to 389,110 for generated meshes of 500 to 3,000 triangles each), worst-spot parts **3,434 -> 3,142**, parts loaded at join **8,640 -> 7,061**. The 16 plants and ground props REPLACE about 1,740 small-clutter placements (3,569 -> 1,829 MeshPart props), and the V3 trees (462 to 726 triangles, measured in Blender) replace generated trees. Still 1.0x the 250 k triangle rule and 1.05x the 3,000-part rule at the worst spot, and 2.4x the part rule at join.
2. **The cave rock forms and arch are not a risk**: the whole cave (every layout row, the 13 rows that place nothing today included) is **218 parts / 221,584 triangles** against the hub budget of 410 / 730,000. The cave's problem is **lights**: 30 (29 fills + the new arch light), 26 of them within reach of one station, and 46 with the cosmetic cap, against a phone budget of 16.
3. **The biggest memory item is shipped art, not the upload.** Six distinct low-poly species are **224 MiB** of dino textures at RGBA8 (7 parts x 1024 px each, docs/105, 448 MiB at 12 species). All 138 image slots together are **288 MiB**, of which the **55 still-empty slots are 199 MiB** only because the spec asks for 1024 px badges and icons that show at 32 to 96 px. A typical scene totals **364 to 437 MiB** at RGBA8 (91 to 109 MiB if the phone GPU-compresses textures, which nobody knows), against a PROPOSED 200 MiB.
4. **Draw calls are not the issue**: 135 to 609 at the worst spot (instanced lower bound to one call per part).
5. **CI**: `phone_forecast.py --check` is wired into the workflow; it FAILS only on a clear breach with fake ids (section 5) and prints the over-budget findings above as WARN.

## 1. World (island), Phone class

Worst spot = the 64-stud grid point with the most triangles; the colossal row swaps stand-ins for LOD0/LOD1 ancient trees at the default radius (LOD0 slot cap 1).

| Metric | Today (ids empty) | Everything uploaded | Delta | Phone budget |
| --- | ---: | ---: | ---: | ---: |
| Parts loaded at join | 8,640 | 7,061 | -18% | 3,000 |
| Parts in scene, worst-parts spot (-224, 224) | 3,434 | 3,142 | -9% | 3,000 |
| Triangles, worst-triangles spot (-160, -160), 1,630 per generated mesh | 452,134 | 253,480 | -44% | 250,000 |
| same, generated meshes at 500 triangles | 152,684 | 141,610 | -7% | 250,000 |
| same, generated meshes at 3,000 triangles | 815,184 | 389,110 | -52% | 250,000 |
| Triangles at spawn (0, 30) | 315,764 | 195,914 | -38% | 250,000 |
| Props kept in range, worst-triangles spot | 922 | 430 | -53% | |
| Unique visual meshes in range (instanced draw-call lower bound) | 20 | 33 | +65% | |
| Draw calls, instanced .. one per part (6 species on screen, 60 fixed) | 122 .. 1,101 | 135 .. 609 | | |

- MeshPart props placed: 3,569 -> 1,829; generated-mesh props (the 1,630 ESTIMATE applies to these): 1,011 -> 433; 7 kit ids switch to a V3 tree. Colossal ancient trees (22 of the 31 placements; 9 dead trees stay stand-ins): +66 parts at join (a LOD1 part and two more trunk colliders each, docs/142), at most **+1.8 k triangles** over the stand-ins at any phone spot and **+11 k** at the ceiling radius 420 (worst spot 11,320 vs 11,681): small next to the 253 k.
- **The uncertainty is the generated meshes.** 433 props still use Roblox-generated meshes whose face counts nobody recorded (bushes, rocks, birch, jungle giant, burnt trees, statue). The "uploading is lighter" result holds even at 500 triangles each (-7%), so it is robust in sign, not in size.
- **Parts are dominated by things the upload does not touch**: 3,600 food pickups + 966 invisible colliders + about 600 other parts + 119 low-poly dino parts. They are never culled, so culling radius does not move them.

Levers at the worst-triangles spot (everything uploaded):

| Lever | Triangles | Parts | Props kept |
| --- | ---: | ---: | ---: |
| radius 190 (today) | 253,480 | 3,103 | 430 |
| radius 160 | 194,143 | 2,981 | 308 |
| radius 140 | 156,277 | 2,915 | 242 |
| radius 120 | 123,768 | 2,856 | 183 |
| shrub + groundcover x0.75 | 235,891 | 3,013 | 340 |
| shrub + groundcover x0.50 | 215,538 | 2,949 | 276 |

Parts levers (everything uploaded):

| Lever | Parts at the worst-parts spot | Parts loaded at join |
| --- | ---: | ---: |
| as is | 3,142 | 7,061 |
| cull the invisible colliders with their props (client side; 213 of 966 are in range) | 2,389 | 7,061 |
| food pickups exist only within the radius, pooled around the player (922 of 3,600 visible) | 3,142 | 4,383 |
| both | 2,389 | 4,383 |

## 2. Cave hub

`CaveHubLayout.budgetTable()` counts every layout row whether or not an id is pasted, so it already IS the "everything uploaded" number. Nothing at all changes about the island by the cave uploads.

| Group | Parts | Triangles | Cap parts | Cap triangles |
| --- | ---: | ---: | ---: | ---: |
| rocks (forms, dressing, scatter) | 123 | 123,828 | 190 | 400,000 |
| station | 37 | 80,056 | 120 | 300,000 |
| lava | 12 | 15,800 | 12 | 20,000 |
| lights (pads, prompts, signs) | 29 | 1,900 | 48 | 10,000 |
| colliders | 17 | 0 | 60 | 0 |
| **total** | **218** | **221,584** | **410** | **730,000** |

- Rows that place nothing today (empty ids): 13 parts, 4,177 triangles: the 9 rock-form rows, the gate arch frame, 1 fallen-log row and 2 stump rows. They are 1.9% of the cave's triangles; the 7 cave FBX (308 to 456 triangles each) cannot hurt.
- **Lights: 29 fills + 1 arch light (only once the arch id exists) = 30 = `MaxLights`**; 4 cast shadows; the largest number whose range reaches one station is **26** (range + 70 studs). Plus the cosmetic budget `EffectsLod.Live.phone.lights` = 16 for the players' auras, so up to **46** against the phone budget **16**. Beams: 8 shaft beams + 24 cosmetic = **32** against 24. Particles: about **30 per second** on a phone (lava 10 + shaft motes 16 + gate glow 4), about 120 alive (ESTIMATE, 4 s lifetime), far under 300.
- The cave's own 16-light cap ([104](104-cave-hub-design.md) s3, s7) was raised to 30 on 2026-10-16 by the owner's brighten pass ("light cap 16 to 30"); the phone budget stayed 16 (handbook 8.1 item 8). The committed Studio probe `tools/qa/data/budget_probe_2026-10-16.tsv` (lights 16, `tools/qa/budget_report.py`) was taken before that and is stale for the cave.

## 3. Textures

Rules used: an image slot costs `width x height x 4` bytes (RGBA8), capped at 1024 px per side (**ASSUMPTION**: bigger uploads are scaled down), plus one third for mips on 3D textures and particle sheets (not on GUI images). Size comes from the repo PNG when the file exists (66 slots, **MEASURED** header), else from the spec in [120](120-pending-owner-uploads-checklist.md) (72 slots; these include the not-yet-made badges at 1024 px). "GPU-compressed" divides by 4 (**ASSUMPTION**, Roblox mobile may or may not do it; this is the first thing to measure).

| Group | Slots | RGBA8 at 1024 | at 512 | at 256 | of it still empty (at 1024) |
| --- | ---: | ---: | ---: | ---: | ---: |
| FX sheets (particles, weather, hatch) | 44 | 68.0 | 44.8 | 13.4 | 33.7 |
| UI icons, badges, eggs, potions, shop | 91 | 203.7 | 66.1 | 18.7 | 165.2 |
| Terrain material maps (meadow v2) | 3 | 16.0 | 4.0 | 1.0 | 0 |
| **all 138 image slots** | **138** | **287.7** | **114.9** | **33.1** | **198.9 (55 slots)** |

Typical scenes (MiB, RGBA8). "New art" = every image slot that scene uses, bound or empty (island run: 25 FX sheets + the worst single weather set, blizzard 2.7 MiB, + HUD icons + grass maps; hatch reveal: the same FX + the whole hatch UI of 5 condition eggs, stage, paint set, confetti, 6 rarity, 3 tier and 7 mutation badges; cave hub: lava crust, shafts, one open shop tab: 12 potion icons + 4 tab icons). Generated-mesh textures are an **ESTIMATE** (assumed 1024 px each: 14 placed textured meshes on the island, 11 once V3 trees replace three; 27 distinct in the cave). Dino textures are **SHIPPED art, MEASURED fact** (docs/105: every low-poly part has its own 1024 px texture), 6 distinct species in view:

| Scene | New art | of it still empty | Generated-mesh textures (island today / with V3) | Dino textures (6 species) | Total | If GPU-compressed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| island run | 81.8 | 37.6 | 75 / 59 | 224 | 364 | 91 |
| hatch reveal | 154.3 | 88.3 | 75 / 59 | 224 | 437 | 109 |
| cave hub | 21.2 | 5.3 | 144 / 144 | 224 | 389 | 97 |

Dino textures by number of distinct species in view: 4 = 149, 8 = 299, 12 = 448 MiB RGBA8. If every cave shop tab were built at once the UI images add 119.6 MiB (build tabs on open). All weather textures in a whole session: 12.4 MiB (no issue).

## 4. FX peaks, Phone class

`tools/fx_budget_report.py` model (same recipes, `EffectsLod`, weather rigs; phone weather density 0.5), plus the static cave lights of section 2.

| Scene | Live particles (3D) | Big sprites | Beams | Trails | Lights |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hatch reveal + worst weather (blizzard) + 12 players with aura, trail, mutation | 2,704 | 88 | 17 | 13 | 13 |
| Open world, same | 2,704 | 88 | 17 | 13 | 13 |
| Aura party, clear sky | 168 | 0 | 17 | 13 | 13 |
| Cave hub (static + cosmetics at their caps) | about 30/s | 0 | 8 + 24 = 32 | 14 | 30 + 16 = 46 |
| **Phone budget** | 3,300 | 120 | 24 | 14 | 16 |

Weather is **2,536 of the 2,704** particles in the open-world moment (blizzard, 5,073 at full density). **Reconciled 2026-10-17 (section 10, [115](115-decisions-log.md) PB1):** the 3,300 in `fx_budget_report.py` is the WHOLE-scene live count (weather included, Rate x mean Lifetime), the "about 300" of [107](107-offline-mobile-budget.md) s1 is the COSMETIC figure (auras, trails, mutations; model 168 above). They are two measures, not two values of one budget. The table above shows the weather at the guarded density 0.25 (BD-497); section 10 has the 0.5 numbers beside it. Both stay PROVISIONAL until BD-085 reads the real count on a phone.

## 5. Top 5 risks, with numbers and mitigations

| # | Risk (label) | Number | Mitigation (cheapest first) |
| --- | --- | --- | --- |
| 1 | **Texture memory, led by shipped dino textures** (ESTIMATE for sizes; no phone has been asked) | 224 MiB for 6 species (448 for 12) + 59 to 75 MiB island meshes + 144 MiB cave meshes + 288 MiB all image slots = **364 to 437 MiB per scene** vs 200 proposed (91 to 109 if GPU-compressed) | (a) Upload the 55 empty images at the size they are shown: 512 px = 56 MiB (-143), 256 px = 14 MiB (-185); the badge, notify and class icons are small in the UI (docs/120 asks for "readable at 32 px"). Free, owner-side, before the upload. (b) Dino part textures at 512 px for the phone class: 6 species 56 MiB (-168), 12 species 112 MiB (-336); needs a second texture set or the EditableImage bake source, tech-artist task. (c) Limit how many distinct species may be in view at full texture (docs/105 only frees the baked overlays beyond 160 studs; the species textures stay loaded while their meshes exist). (d) Build shop tabs on open (-120 MiB if all were built). |
| 2 | **Parts loaded at join and never culled** (ESTIMATE of the join; the pool/collider split is MEASURED from the placement) | 7,061 at join (2.4x the 3,000 rule), 3,142 in scene at the worst spot; food 3,600 + colliders 966 + other 600 = 5,166 of them never culled | (a) Food pickups pooled around the player (922 visible of 3,600): join 7,061 -> 4,383. (b) Cull the invisible colliders with their props: worst-spot scene 3,142 -> 2,389 (colliders are 213 of 966 in range). **BUILT on phones in s10 (BD-496); (a) food pooling is NOT built: kanban BD-498.** (c) Both: 4,383 at join, 2,389 in scene, under the rule at the worst spot. Alternative: `StreamingEnabled` (docs/107 s5 item 4). |
| 3 | **Cave hub lights and beams** (MEASURED count from the layout, budget PROVISIONAL) | 30 lights (+16 cosmetic = 46) vs 16; 8 + 24 = 32 beams vs 24; 4 shadow lights | (a) Phone: enable only the 12 nearest cave lights (client toggles `Enabled`, the layout is unchanged) and 0 shadow lights. (b) No cosmetic lights inside the hub on phones (cosmetic cap 16 -> 0 there). (c) 4 shaft beams instead of 8 on phones. Each is a small client rule; none changes the cave art. **(a) nearest 12 lights, (b) no cosmetic lights in the hub and (c) 4 beams are BUILT in s10 (BD-495); the cosmetic beam cap inside the hub (24 -> 20, so the hub total is 24) is built in BD-507; 0 shadow lights is not.** Frame cost of a light on phone is exactly the unknown: measure first. |
| 4 | **Island triangles sit on the 250 k rule and rest on an unmeasured number** (ESTIMATE) | 253,480 at 1,630 per generated mesh; range 141,610 (500) to 389,110 (3,000); 433 generated props remain | (a) Phone radius 190 -> 160 = 194,143 (-23%), 140 = 156,277 (-38%); costs view distance only, no art change. (b) Shrub + groundcover x0.75 = 235,891 (-7%). (c) Count the real faces of the 14 placed island + 27 cave generated meshes with `EditableMesh` in Studio, as docs/105 did for the dinos (154,660 faces), then replace the heaviest kinds with Blender V3 meshes. (d) Keep the colossal ceiling radius (420) OFF until a phone run: +6 k at the worst spot. |
| 5 | **Weather dominates the particle peak** (model; the two budgets measure different things, s10) | 2,536 of 2,704 particles from one blizzard at phone density 0.5; trails 13 of 14; big sprites 88 of 120; and 107 says 300 particles, not 3,300 | (a) Phone weather density 0.5 -> 0.25 cuts about 1,270 particles (2,704 -> 1,436). **BUILT in s10 (BD-497).** (b) Pause or halve weather particles while the 15-egg reveal plays. (c) Lowest-cost proof: the `fx_probe.client.luau` moment TSV on the phone (docs/117) replaces this model. |

Not in the top 5 (checked): draw calls (135 to 609), colossal LOD (+1.8 k triangles at the default radius), the cave FBX uploads (+4,177 triangles, 13 parts), network (docs/107 s4: 2 KB/s combat, join replication is risk 2), weather texture bytes (12.4 MiB for all).

## 6. CI check (light, fake ids)

`python tools/qa/phone_forecast.py --runner luau --check` runs in the workflow next to `verify_world_budget.py`. It computes everything above with fake ids and **FAILS only when**:

- a cap with about 25% headroom is crossed: worst-spot triangles 320,000 (now 253,480), worst-spot parts 3,950 (3,142), parts at join 9,150 (7,061), cave parts 410 and triangles 730,000 (218 / 221,584), hatch scene image MiB 270 (213), all image slots 360 MiB (288), cave lights 46 (46: `MaxLights` 30 + cosmetic 16);
- uploading everything would add more than 5% triangles or 100 parts at the phone worst spot compared with the empty-id world (it can only get lighter today);
- a cave light/beam count exceeds 3x / 2x its phone budget.
- (BD-495, BD-497; s10) the guarded hub (nearest cave lights + cosmetic lights in the hub) exceeds the phone light budget, or the guard weather density is above 0.25, or the guard shaft beams above 4. `tools/verify_phone_guards.py` checks the guards themselves.

It prints **WARN** (never fails) for everything over the documented phone budget: triangles 253,480 > 250,000; parts 3,142 and 7,061 > 3,000; cave lights 46 > 16 and beams 32 > 24; every scene's total image memory > 200 MiB. These are the known findings of section 5, not regressions. A real breach means a placement, density, culling or asset change made the uploaded phone scene clearly heavier: re-run the command, read this doc, then raise the cap on purpose.

## 7. What to measure first on a real phone (BD-085, BD-322)

Use the playtest build, Phone class, the QA overlay and `python tools/qa/phone_report.py` (docs/127). Record the device model, RAM and graphics quality. In order of how much each replaces in this forecast:

1. **Memory by texture group** (Developer Console, F9, Memory tab: GraphicsTexture / PlaceMemory / Mesh): join the hub with 1, then 6, then 12 distinct species on screen; read the delta per species. Answers: are dino textures 37 MiB each or about 9 MiB (GPU compression), and does the phone survive 12 species? Risk 1.
2. **Studio, no phone, 10 minutes:** the real pixel size of one generated-mesh texture (`AssetService:CreateEditableImageAsync` on a `TextureID`) and the face count of the 14 placed island + 27 cave generated meshes (`CreateEditableMeshAsync`, as docs/105 did). Replaces `WORLD_TEX_PX` 1024 and `GEN_TRIS` 1,630 in this tool and `estimate_world_budget.py`. Risks 1 and 4.
3. **Join time and join memory** with the full 8.6 k parts (7.1 k after the upload): time to a controllable dino, memory jump, load gate (BD-210). Risk 2.
4. **Frame time at spawn and at the SW corner** (-160, -160) and NE (-224, 224) with Stats (Triangles, Draw Calls, FPS) and the admin F2 "World parts" readout; repeat with radius 160 if under 30 fps. Risk 4.
5. **Cave hub with 12 players**: FPS and Triangles at the Heart, then with the 12 nearest lights only (risk 3 lever a). Count `Enabled` lights with `tools/qa/budget_probe.server.luau` (re-run: its committed 2026-10-16 output shows 16 lights and is stale).
6. **Particles in a blizzard hatch reveal** with 6 aura dinos: Stats particle count and FPS against 300 and 3,300 (the conflict in section 4).
7. After the images are uploaded: **UI only** pass (shop tabs, potion menu, hatch reveal) watching Memory for texture spikes; compare with the 154 MiB hatch number.
8. Feed the numbers back: `GEN_TRIS`, `WORLD_TEX_PX`, `TEX_CAP`, `GPU_COMPRESS` in the tools, the caps in `verify_world_budget.py` / `phone_forecast.py`, and `tools/qa/phone_budgets.json`.

## 8. Honest limits

- Every texture figure assumes decoded RGBA8 at the capped size. Roblox mobile may compress, downscale on low quality levels, or evict unreferenced assets: that is the 4x spread in the tables, and nobody has measured it.
- Draw calls are a range, not a model of the Roblox renderer.
- Fake ids test placement and arithmetic only. No mesh was loaded, no orientation, scale or look was checked, nothing was uploaded.
- Only the Phone class is forecast; the tablet and desktop columns of [107](107-offline-mobile-budget.md) and [142](142-colossal-lod-budget.md) are unchanged.
- The `textureMib` budget (200) is a PROPOSAL of this document, not an owner decision.

## 9. Handbook check (docs/114)

- 8.1 item 8 (budget): the figures it lists (3,000 parts, 250 k triangles, hub 410 / 730 k, 16 lights, about 300 particles, 12 players + 5 NPCs) are what the check compares against; the cave's 30 lights breach the handbook's 16 and are reported, not hidden (the brighten pass of 2026-10-16 was an owner decision, docs/104 s17).
- 8.1 item 10 and AGENTS.md: no asset id invented or written; fake ids are in-memory only. No art added, so no docs/77 line. No game code changed; `Config`, release profiles and all flags are untouched.
- AGENTS.md "Flag-off-by-default" and "no phone evidence": this document claims no phone measurement and does not close BD-085 or BD-322.

## 10. Phone guards built for risks 2, 3 and 5 (BD-495 .. BD-497, 2026-10-17; BD-498 food pooling plan, BD-499 particle wording)

Label: **CLIENT CODE + OFFLINE MODEL, not a phone measurement.** Three cheap guards, each PHONE-ONLY. Desktop and tablet behave exactly as before (same properties, same values, same code paths; the verifier below asserts it). The rules are pure data in `src/shared/PhoneGuards.luau`, mirrored in `tools/qa/phone_budgets.json` (`guards`), checked by `python tools/verify_phone_guards.py --runner luau.exe` (CI) and printed before / after by `phone_forecast.py` section 5. Device class: phone = `FxRecipes.deviceClass` (touch, no mouse, short side under 700; what `FxRig` / `EffectsLod` use) for the cave lights and the cosmetic lights, WeatherVisuals' own test (touch and no mouse, then the `Phone` class: short side under 600, the same cut as WorldCulling) for the weather density, and WorldCulling's `Phone` class for the colliders, so each guard uses the classifier of the system it sits in.

| Guard | What it does | Where | Before | After |
| --- | --- | --- | --- | --- |
| **BD-495 cave lights, hub glow lights and beams** (risk 3) | Of the 30 cave point lights only the 12 nearest to the camera are `Enabled`; re-evaluated every 0.5 s; a light that is off replaces an on light only if it is 1.25x nearer (no flicker). Of the 8 shaft beams only the wide haze beam of each hole stays (4). The server still builds all of them; only this client's copy is toggled. On a phone no aura / mutation glow light shines while its owner is inside the hub (the own dino under Reduce Motion keeps its one soft light: it is its whole look). | `client/CavePhoneGuard`, called by `CaveAtmosphere.step` behind `Config.CaveHub`; `FxRig` + `CosmeticVisuals` (feeds `CaveAtmosphere.inside()`; BD-507 beam cap through `EffectsLod.fit`) | 30 lights, 8 shaft beams, cosmetic cap 16 lights and 24 beams in the hub | 12 lights, 4 beams, 0 cosmetic lights, at most 20 cosmetic beams (BD-507) in the hub |
| **BD-496 invisible colliders** (risk 2) | On a phone the invisible `*Collider` parts of the island props leave the world beyond the prop cull radius (190, outer 218) and return inside it. | `WorldCulling` | 966 colliders always loaded | 213 of 966 near the worst-parts spot |
| **BD-497 weather density** (risk 5) | Phone weather emitter density 0.5 -> 0.25 (a touch-only tablet stays 0.5, desktop 1). Reduce Motion still emits nothing, Weather Lite still halves it again. | `WeatherVisuals` through `PhoneGuards.weatherDensity` | 0.5 | 0.25 |

Before / after, Phone class, everything uploaded (from `phone_forecast.py`, same model as sections 1 to 4):

| Metric | Before | After | Phone budget |
| --- | ---: | ---: | ---: |
| Enabled lights in the hub (static + cosmetic) | 30 + 16 = 46 | 12 + 0 = **12** | 16 |
| Enabled beams in the hub (shaft + cosmetic cap) | 8 + 24 = 32 | 4 + 20 = **24** (BD-507: cosmetic cap 24 -> 20 inside the hub on a phone) | 24 |
| Live particles, hatch reveal or open world in a blizzard, 12 players | 2,704 | **1,436** | 3,300 whole scene |
| of which weather (blizzard) | 2,536 | 1,268 | |
| Big sprites, same moment | 88 | 44 | 120 |
| Parts in scene at the worst-parts spot (-224, 224) | 3,142 | **2,389** | 3,000 |
| Parts loaded at join | 7,061 | 7,061 (unchanged: the parts still exist, the phone only stops keeping the far colliders) | 3,000 |

**BD-505 correction (2026-10-17):** until this fix the guard never ran in any build: `CavePhoneGuard` and `CaveAtmosphere` looked for `Sanctuary` in Workspace, but the hub lives under `Workspace.BeDinoArena` (found by the docs/147 streaming experiment: 8 shaft beams stayed on with the phone class forced). Both now look under `BeDinoArena`. Measured in Studio play with the phone class forced in a private copy: 8 shaft beams, 4 enabled, 12 of the 30 lights on. The tables above are the model, and the model now matches that run.

What the numbers do NOT show: the real frame cost of a light or a particle on a phone (BD-085); the cosmetic beam cap of 20 is checked as a rule (`EffectsLod.fits` with a beam cap, 3-beam and 1-beam rigs fill it to 18 and 20, never past it), not by looking at it in Studio, and a rig whose look cannot fit simply steps down to its lite look or is dropped (the own dino and mutation cues keep their lite floor, 1 to 3 beams, so the hub total is 24 in the model and could exceed it by that floor); and the nearest-12 choice is checked on the walk gate -> Heart with the real 30 lights (9 steps, always 12 of 30 on, 8 flips against 10 for the plain nearest-12 rule, no light flips more than once) and on a jittering camera (0 flips), not by looking at it in Studio. The cave art, the server, the shadows (4 shadow lights stay; "0 shadow lights" of risk 3 (a) is not built) and every tablet and desktop value are untouched.

### Colliders: what they do, and why the far ones may go (BD-496)

Read before culling (2026-10-17): the 966 colliders are `<id>Collider` parts that `Arena.kitProp` puts as direct children of `Workspace.BeDinoArena.WorldKit` next to each prop (trunks of trees and colossal trees, boulders, logs, the four landmarks): anchored, `CanCollide` true, `CanTouch` false, `CanQuery` true, `Transparency` 1. What they do: **block the local dino from walking through a trunk or a rock.** What they do not do: hold the ground up (the ground is voxel Terrain, and `WorldReady` waits for rays against Terrain only), trigger anything, mark a gameplay zone or take part in server logic. No server script reads them (what the server simulates uses server parts, which this does not touch), and the only client readers by name are `WorldCulling` (skips them) and `CameraOcclusion` (skips them), asserted by `verify_phone_guards.py`, so a new reader fails CI until reviewed. A client-side removal changes only that client's physics. The local dino cannot be within 190 studs of a culled one; a collider returns at 190 studs (checked every 0.4 s and at every 6 studs of movement), so crossing the gap in one interval needs more than 470 studs per second. The one exposure is a teleport or respawn: for up to 0.4 s a collider next to the arrival point can still be absent; nothing falls (Terrain), a trunk is passable for that instant. Colliders inside the radius stay even when the part budget hides their prop (as today). The hub's 17 colliders and the cave props live under `Sanctuary`, not `WorldKit`, and are untouched. **Result: none of the 966 is gameplay-critical at range, so the cull was built and nothing was left out.** Food pooling around the player is the larger change (kanban BD-498).

### Decided not to build here

- **Food pooling around the player** (3,600 -> 922 pickups, join 7,061 -> 4,383): written up as kanban BD-498 with a plan. It changes how pickups replicate, collect and glow, so it needs its own design and a Studio pass.
- **0 shadow lights in the hub** (risk 3 (a) said "and 0 shadow lights"; the task asked for 12 lights, no cosmetic lights and 4 beams): left at 4. Cheap to add later in `CavePhoneGuard` by also clearing `Shadows` on a phone.
- ~~**Cosmetic beams in the hub** stay at their global cap of 24 (the hub total is therefore 28 against 24).~~ **Built in BD-507 (2026-10-17):** on a phone inside the hub `PhoneGuards.cosmeticBeamCap` lowers the cosmetic beam ceiling of the scene-wide FX budget to 24 - 4 = 20, so shaft + cosmetic beams = 24 (budget 24). `CosmeticVisuals` passes it to `EffectsLod.fit` and rebuilds a phone's rigs once when it enters or leaves the hub (the same `CaveAtmosphere.inside()` flag as the glow lights, which has hysteresis). Tablet, desktop and the phone outside the hub keep the cap of 24 (72 / 160 elsewhere). `phone_forecast.py` section 5 and the OK line `hub beams 4 shaft + 20 cosmetic cap = 24` read it back; `verify_phone_guards.py` asserts the rule and the wiring.
- **`particleLive` in the QA overlay** (Rate x mean Lifetime, the same quantity as the 3,300): follow-up BD-499 ([115](115-decisions-log.md) PB2).
