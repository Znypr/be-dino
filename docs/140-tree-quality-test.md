# 140 Tree asset-quality test: broadleaf, conifer, palm (BD-462)

**Status 2026-10-16: OWNER DECISION: use V3 for all three families.** The meshes are baked in Blender but NOT uploaded: no asset IDs exist yet and the game still shows the current generated meshes. The code is prepared so that pasting three ids switches the trees (see Wiring and the BD-462 row).

## Why
Owner feedback on the live island: round trees read as spheres on cylinders, pines are regular stacked layers, palms are symmetrical with flat leaves and straight trunks; grass is thin triangles; too few substantial ground props. Wanted: asymmetric foliage clusters, tapered trunks, visible branches and roots, varied proportions, a curved palm trunk with overlapping, slightly drooping fronds; keep the chunky cartoon low-poly Be Dino look.

## What was made
Three redesigns, one mesh and ONE material each (flat per-face vertex colours, no texture; same `Col` attribute and FBX settings as fbx_v2, so the existing upload flow applies). Foliage greens are the handbook grass family pulled slightly towards mint and a little less saturated than the in-game greens ([114](114-handbook.md) s5.8).

| File (`assets/blender/world/fbx_v3/`) | Tris | Size X x Y x Z (studs) | Features |
| --- | ---: | --- | --- |
| `world_tree_broad_v3.fbx` | 726 | 11.2 x 8.7 x 13.4 | tapered, leaning, flared trunk; 3 roots; 5 branches; 6 uneven foliage clumps with flat undersides and sky gaps |
| `world_tree_pine_v3.fbx` | 462 | 10.6 x 8.8 x 16.2 | curved trunk with roots and snapped lower stubs; 7 drooping scalloped skirts, each its own size, rotation, tilt and offset; spiky leader |
| `world_tree_palm_v3.fbx` | 700 | 12.4 x 11.8 x 12.1 | curved ringed trunk with flared base and roots; 12 arched two-sided fronds of unequal length and droop (3 young upright ones); coconuts |

Pivot: bbox bottom centre, lowest point z=0 (docs/56 convention, and what `Arena.generatedProp` uses). Trunk offset (trunk base minus bbox centre, Blender X/Y, studs, measured by the export): broadleaf (0.59, -0.04), conifer (-0.26, -0.07), palm (-0.10, -0.60). The palm lean was reduced and the fronds on the side away from the lean lengthened so the palm's offset is also under 1 stud: the trunk base stands within 0.6 stud of the placement point, so BiomePlacement and the invisible box colliders need NO code offset. Editable source: `assets/blender/world/WorldKitV3_Trees.blend`; scripts `tools/blender/build_trees_v3.py` (headless: `-- export` / `-- render <absolute out dir>`) and `tools/blender/compose_trees_v3.py` (Pillow sheets).

**Scoped owner exception to the 3D model rule (owner 2026-10-16):** these are scripted in Blender (hand-placed branch paths, cluster centres and frond curves; no scatter, no generators). The owner called scripted modelling "3D Microsoft Paint" on 2026-10-15 and the code-built V2 kit PLACEHOLDER, but after seeing the grove and gameplay-distance renders, and being told they are script-built, chose V3 for all three families. The exception covers ONLY `world_tree_broad_v3`, `world_tree_pine_v3` and `world_tree_palm_v3`; it is not a general permission (docs/115, AGENTS.md, docs/07 owner log). The owner also allows Blender for world and colossal-tree art. "Current" in the renders is an APPROXIMATION (the generated meshes 137262237243889 / 123860208068220 / 115520379209668 have no repo file); it is built to match the owner's description and screenshots, so differences from the real meshes are possible.

## Evidence (`docs/evidence/2026-10-16-trees/`)
Sheets `<family>-<shot>.png`, left to right CURRENT (approx.) / V2 kit / V3 redesign, flat green ground, bright daytime sun, 70 degree vertical FOV camera slightly above the ground:
- `play`: tree at 32 studs (the real gameplay camera range) with a spawn-size dino silhouette.
- `grove`: five trees (rotated, scaled 0.75 to 1.1) at 34 studs.
- `scale`: side-on lineup, spawn-size dino (orange) / tree / max-size dino (purple), to show height layers.
- `close`: 17 studs, detail check only.
The sheets are crops of 1600x900 renders (the uncropped frames are not committed; rerun `build_trees_v3.py -- render` then `compose_trees_v3.py` to regenerate them). Triangle counts per variant are in `tris.txt`.

## Real dino sizes used (from code)
`scaleForScore = min(4, sqrt(1 + growth/50))` (`DinosaurVisual.luau`, `HudRules.MaxSize = 4`); compy model 4.4 studs tall x 8.5 long (`resources/models/compy.obj`). Spawn = scale 1 = 4.4 tall. Max run size = scale 4 = 17.6 tall, 34 long (BIG x1.2 = 21 tall). A compy is taller than the tree at growth about 358 (broadleaf, 13.4), about 315 (palm, 12.1) and about 640 (conifer, 16.2). So every family is MEDIUM layer at best (palm borderline small) and is outgrown before max size; none is a colossal tree (that needs well above 21 studs). Colossal ancient trees stay a separate spec and are not built here.

## Verdict (honest, at gameplay distance)
- **Palm: clear win.** The curved trunk and overlapping drooping fronds read at 32 studs; current is a straight pole with a flat star; V2 is a thin sheared umbrella. The trunk base is chunky and the colour slightly cool.
- **Conifer: win, but a style change.** Irregular, drooping, offset skirts and roots break the stacked-cone look in groves; it is spikier and less chunky than current, and the teal reads cooler than the current dark green. The owner should check whether the spikiness fits the cartoon style.
- **Broadleaf: modest win.** Asymmetric clumps, visible branches, flared roots and sky gaps are noticeable at 32 studs and in groves, but the clumps are still faceted blobs and the mint is a little paler than the island greens. Closer to the wanted look, not a transformation.

## Wiring (prepared 2026-10-16, still nothing uploaded)
- `src/shared/WorldGeneratedMeshes.luau`: new `Generated.Replacements` with `tree_broadleaf_v3`, `tree_pine_v3`, `tree_palm_v3`, each `assetId = ""` for now, plus `replacementFor(key)` that returns the V3 key only when its id is filled in.
- `src/server/ImportedResources.luau` `loadGeneratedWorld` loads non-empty replacement ids exactly like the other generated meshes (first MeshPart of the Model) and skips empty ones silently.
- `src/server/Arena.luau` `generatedProp` tries the V3 mesh first and falls back to the current generated mesh, then to the kit model, so a failed or empty id never leaves a hole. Sizing is unchanged: the mesh is fitted into the kit id's extent box, so colliders still match.
- Scope: `tree_broadleaf` (kit `world_tree_canopy_m`), `tree_pine` (`world_tree_conifer_s/m/l`) and `tree_palm` (`world_tree_cycad_s/m/l`). Birch (`canopy_s`) and the jungle giant (`canopy_l`) keep their current meshes; whether the broadleaf V3 should also cover those is an open owner question.
- Test: `tests/test_world_generated_meshes.py` (replacement keys, empty-or-numeric ids, fallback and loader wiring, FBX and registry rows). Studio and phone verification are still pending the upload; triangle budget (`tools/estimate_world_budget.py`) was not re-run with the V3 counts.

## Next
Owner uploads the three FBX files (click-by-click steps are in the BD-462 row of docs/07 and docs/120), pastes the ids, then a Studio + phone check. BD-463 (grass and plant families) and BD-464 (ground props) are spec-only follow-ups. The small/medium/colossal layering waits for its spec.

## Ground props (BD-464 step 1, art only, baked 2026-10-16, NOT uploaded)

**LEAD decision 2026-10-16 (owner delegated):** BD-464 moved from spec to build; this is step 1, the art. Placement (step 2) waits for the owner upload and pick. Eight hand-shaped Blender props in the V3 style (chunky cartoon low-poly, warm matte vertex colours, V3 foliage greens, ONE material each, `Col` attribute, pivot bbox bottom centre with the lowest point at z=0, same FBX settings as `fbx_v3`; reimport check: every file has min z 0.0, centre 0.0, 1 material). Same scoped Blender exception as the trees (world art; hand-placed shapes, no scatter, no generators).

| File (`assets/blender/world/fbx_v3/`) | Tris | Size X x Y x Z (studs) | How it is shaped |
| --- | ---: | --- | --- |
| `ground_rock_small_v3.fbx` | 68 | 2.8 x 2.4 x 1.2 | lumped low icosphere, three chisel planes, leaning top |
| `ground_rock_medium_v3.fbx` | 278 | 4.9 x 4.0 x 2.3 | seven chisel planes (flat facets), sloped top, a small second stone leaning on it |
| `ground_rock_mossy_v3.fbx` | 262 | 5.6 x 4.5 x 3.2 | seven chisel planes, noise-driven moss colour on up-facing faces, a moss cap and a moss skirt |
| `ground_log_fallen_v3.fbx` | 199 | 7.9 x 2.8 x 3.0 | six uneven rings with a bend, flat sit, carved-in cut end with growth rings, jagged broken end, snapped branch stub, two moss patches |
| `ground_stump_roots_v3.fbx` | 199 | 7.1 x 5.9 x 3.0 | flared bark trunk, tilted dished top with growth rings, four arching roots of different length and thickness diving into the ground, moss tuft |
| `ground_mushrooms_v3.fbx` | 303 | 5.3 x 4.1 x 2.9 | five stalks (curved, tapered) with hand-lathed caps of different size and lean, red with cream spots and honey, darker gill side, moss mound |
| `ground_bush_round_v3.fbx` | 340 | 6.0 x 4.2 x 2.7 | four unequal lumpy clumps (tall back, two sides, low front), flat undersides, one twig |
| `ground_bush_berry_v3.fbx` | 304 | 6.3 x 4.1 x 2.1 | three flat wide clumps in a warmer green, eight faceted berries |

Palette: stones warm grey (not the cool Rock slate of the terrain), moss `#4E7E3A` to `#88B050`, wood `#A67A46` to `#E6C894`, bark from the V3 trees, caps `#C24E34` to `#F2905A` and `#C98B2E` to `#F6CF74`, berries `#D9505E`, bushes the V3 leaf family and a warmer green `#3F8F4E` to `#92CB6C`. Source: `assets/blender/world/WorldKitV3_GroundProps.blend`; scripts `tools/blender/build_ground_props_v3.py` (headless `-- export` / `-- render <absolute out dir> [shots]`) and `tools/blender/compose_ground_props_v3.py` (Pillow sheets).

**Evidence (`docs/evidence/2026-10-16-props/`):** `props-play25-spawn.png`, `props-play25-big.png`, `props-play40-spawn.png`, `props-play40-big.png` (left version 1, right version 2; V3 broadleaf tree at the origin, flat green 132,166,68 ground, bright daytime sun, 70 degree FOV camera at 25 or 40 studs, spawn-size dino 4.4 tall or a 1.5x one as an orange silhouette), `props-lineup.png` (close lineup), `tris.txt` (total prop tris of each grouping). Version 1 is an APPROXIMATION of the props around a tree today (round cool grey-green boulders, smooth mint puff bushes, the 60-tri kit mushroom clump `world_mushrooms_a.fbx`); the generated meshes have no repo file, so the real ones can differ. Version 1 has no logs and no stumps because the game has none. Honest note on the numbers: version 1 shows 6 props (600 tris), version 2 shows 10 (2,324 tris), so the new look is richer AND heavier; step 2 must replace small clutter so the real count and triangle budget stay flat, it is not a free upgrade.

**Verdict (honest, at 25-40 studs, flat lighting only, nothing seen in Roblox yet):**
- **Stump, log and mushrooms are a clear win.** They add silhouette types the island does not have at all; the stump with roots, the log with a branch stub and the orange mushroom cluster read at 40 studs with either dino size.
- **Rocks: a real but moderate win.** Warm grey, irregular and chiselled, they read as stones instead of pale low-poly gems; the medium and mossy ones hold up at 40 studs. The small rock is only 68 tris (under the 80 target) and is a pebble-sized accent. Moss reads as neon green patches up close.
- **Bushes: modest.** Chunky and tree-base sized, but the round bush is the same mint family as the V3 crown, so in shade it blends into the tree; the berry bush is the better one, yet its berries are tiny at 40 studs.
- **Weak spots:** stump roots are a little peg-like; the mushroom cluster is the heaviest per stud of size (303 tris for about 5 studs); the grouping layout in the render is hand-set, not the placement grammar, which is step 2.
- **Not checked:** Roblox lighting and tone, camera occlusion, slope grounding, colliders, phone triangle budget. All of that belongs to step 2.

**Wiring (prepared, empty):** `WorldGeneratedMeshes.Props` has eight entries with `assetId = ""` and `placed = false` (new kinds, not replacements), `ImportedResources.loadGeneratedWorld` loads a non-empty id into `ReplicatedStorage.GeneratedWorld` like the others, slots `ground_*_v3` are in `tools/asset_slots.json` (`python tools/bind_assets.py ground_rock_small_v3=<id> ...`). `Arena` and `BiomePlacement` are untouched: nothing is placed.
