# 139 Tree asset-quality test: broadleaf, conifer, palm (BD-462)

**Status 2026-10-16: test assets baked in Blender, NOT uploaded, NOT placed, no asset IDs.** The owner picks per family; nothing in the game changed.

## Why
Owner feedback on the live island: round trees read as spheres on cylinders, pines are regular stacked layers, palms are symmetrical with flat leaves and straight trunks; grass is thin triangles; too few substantial ground props. Wanted: asymmetric foliage clusters, tapered trunks, visible branches and roots, varied proportions, a curved palm trunk with overlapping, slightly drooping fronds; keep the chunky cartoon low-poly Be Dino look.

## What was made
Three redesigns, one mesh and ONE material each (flat per-face vertex colours, no texture; same `Col` attribute and FBX settings as fbx_v2, so the existing upload flow applies). Foliage greens are the handbook grass family pulled slightly towards mint and a little less saturated than the in-game greens ([114](114-handbook.md) s5.8).

| File (`assets/blender/world/fbx_v3/`) | Tris | Size X x Y x Z (studs) | Features |
| --- | ---: | --- | --- |
| `world_tree_broad_v3.fbx` | 726 | 11.2 x 8.7 x 13.4 | tapered, leaning, flared trunk; 3 roots; 5 branches; 6 uneven foliage clumps with flat undersides and sky gaps |
| `world_tree_pine_v3.fbx` | 462 | 10.6 x 8.8 x 16.2 | curved trunk with roots and snapped lower stubs; 7 drooping scalloped skirts, each its own size, rotation, tilt and offset; spiky leader |
| `world_tree_palm_v3.fbx` | 700 | 12.4 x 11.8 x 12.1 | curved ringed trunk with flared base and roots; 12 arched two-sided fronds of unequal length and droop (3 young upright ones); coconuts |

Pivot: bbox bottom centre, lowest point z=0 (docs/56 convention). The palm leans, so its trunk base sits about 2 studs off the placement centre; BiomePlacement and the collider would need a trunk-offset note if it is picked. Editable source: `assets/blender/world/WorldKitV3_Trees.blend`; scripts `tools/blender/build_trees_v3.py` (headless: `-- export` / `-- render <absolute out dir>`) and `tools/blender/compose_trees_v3.py` (Pillow sheets).

**3D model rule flag (AGENTS.md, owner 2026-10-15):** these are scripted in Blender (hand-placed branch paths, cluster centres and frond curves; no scatter, no generators). The owner called scripted modelling "3D Microsoft Paint" and the code-built V2 kit PLACEHOLDER. These meshes are a quality TEST for the owner to judge beside the Roblox-generated meshes; if the owner rejects scripted models, they are dropped. "Current" in the renders is an APPROXIMATION (the generated meshes 137262237243889 / 123860208068220 / 115520379209668 have no repo file); it is built to match the owner's description and screenshots, so differences from the real meshes are possible.

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

## Next
BD-462 (this test) needs the owner pick per family; BD-463 (grass and plant families) and BD-464 (ground props) are spec-only follow-ups. The small/medium/colossal layering waits for its spec.
