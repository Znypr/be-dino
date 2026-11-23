# BD-1311 tree variety (2026-11-23)

Owner 2026-11-23: "we need more trees more variations and remodel some current trees that look too geometric".
World V3 playtest island (WorldV3Enabled + ToonWorldEnabled + VegetationV2Enabled, `playtest` profile), my own test Studio window.

## Before (main + PR #662, build/BeDino-treevar-before.rbxlx)
- `before-<meadow|forest|pine|beach|volcano>.jpg`: one camera per zone (camera 150 studs out on the zone's middle angle, 35 studs up, looking at the grove ring 270 studs out; positions in the table below). Same cameras for every after picture.
- 254 trees in 8 looks: palm coconut 42, palm flower 39, pine a 45, pine b 28, twisty 28 (all the colossal broadleaf), fruit 23, flower 20, burnt kit tree 29.
- Geometric offenders (picked from the pictures):
  1. **Pines a/b** (`before-pine.jpg`, `before-close-pine.jpg`): hard stacked cones, pale tips read as plain cones from afar. Fixed in slice 1.
  2. **Burnt kit tree** `tree_burnt` (`before-beach.jpg`, right; `before-forest.jpg`, stumps): flat-shaded faceted trunk with a lava stripe, up to about 110 studs as a colossal. Slice 2.
  3. **Twisty tree as a colossal** (`before-forest.jpg`, big tree): a 2,500-triangle mesh blown up to 80-140 studs, the crown turns faceted. Slice 3.

| zone | camera | look at |
|---|---|---|
| meadow | 144, 40, -8 | 268, 16, 6 |
| forest | 51, 48, 170 | 46, 19, 295 |
| pine | -122, 46, 116 | -244, 60, 144 |
| beach | -122, 40, -56 | -190, 15, -160 |
| volcano | 13, 40, -119 | 69, 40, -230 |

## Slice 1 (this PR): soft pines + oak
- Route: Roblox Studio `generate_mesh` (free), text prompts in the approved vegetation v2 sheet's style, published to the owner's account by the generator. No ChatGPT sheet this slice (the approved 2026-11-16 sheet sets the style; the owner saves ChatGPT pictures, so it would block); references are crops of Studio pictures of each mesh (`refs/`).
- `pines-round1-rejected.jpg`: first try. Rejected: dull faceted fir (82591327398755), blue ball spruce (112889306890314). Kept: the "umbrella pine", which came out as a fine broadleaf oak.
- `pines-old-left-new-right.jpg`, `pines-new-close.jpg`: old pine b, old pine a, then the new **fir** (121078729284419, 1,200 tris), **cypress** (94010378329800, 1,000), **bonsai pine** (71668823008966, 1,200).
- Pines a/b are retired (registry lines marked superseded). Conifers pick fir / cypress / bonsai (about 45 / 40 / 15 for small, 40 / 35 / 25 for medium and large); broadleaf gets the oak as a fourth look (also a share of the colossal broadleaf).
- In game (`after1-*.jpg`, `compare-pine-before-top-after-bottom.jpg`, `compare-forest-before-top-after-bottom.jpg`): 254 trees in 10 looks: fir 34, cypress 25, bonsai 14, oak 21, twisty 20, flower 16, fruit 14, palms 42 + 39, burnt 29.
- Triangles: the new pines are 1,000-1,200 against 900 for the old ones (+300 per pine at most; Studio PC, no phone check).

## Variant plan (next slices, one PR each)
| family | now | target | new looks |
|---|---|---|---|
| broadleaf | flower, fruit, twisty, oak | 5 | pink blossom tree (meadow) |
| pine | fir, cypress, bonsai | 3 | done |
| palm | coconut, flower | 4 | twin curved palm, short fan palm |
| dead / burnt | faceted kit `tree_burnt` | 3 soft | mossy bare old tree, hollow stump with mushrooms, charred volcano tree with soft ember cracks |
| colossal broadleaf | twisty x 80-140 studs | 1 landmark | a higher-detail giant (about 5,000 tris, colossal layer only) |

**Jungle slice (owner 2026-11-23: "also more terrains like more jungle features and assets"), ON HOLD until the lead sends the jungle biome brief (biome overhaul plan on the Design Board, so the art matches):** a readable jungle
part of the broadleaf forest (biome `fern`, or a jungle sub-zone in `WorldV3.Zones`): dense canopy, buttress-root trees, vines/lianas,
big-leaf plants and ferns, mossy rocks or ruins, a small stream or waterfall pool, and darker varied jungle ground (terrain materials and
colours in `src/server/IslandTerrain.luau`, `WorldV3.surface` / `weights`). Art from generate_mesh or Blender/Hunyuan; plan with pictures
to the owner first; phone part budget; food maps regenerated if placements change. Keep #662's path softening in mind: stronger relief
failed the food spread rule.

More trees: raise the tree layer (chance and cap) by about 25%, most in the meadow and the beach, after the remodels, within `BiomePlacement.PartBudget` and the `verify_world_art` triangle checks.

## Cohesion rule (owner 2026-11-23)
"Make sure the maps / biomes and vegetation look realistic and cohesive for the game we are building, like a plant pot wouldn't make any
sense, unless it's part of a shop decoration." Every kit piece is checked close up in Studio before it is wired: it must grow from the
ground or sit on it, with no pots, stands, base plates or foreign objects, and it must match its biome kit's palette and chunkiness.
Rejected for this rule so far: the potted elephant ear (100877600173393), the rock like a cake pot (118201682667163) and the fern on
a dirt bulb (99395664937835), none of them used.
