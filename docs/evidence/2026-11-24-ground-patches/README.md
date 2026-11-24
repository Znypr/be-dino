# BD-1320 ground patches (2026-11-24)

Owner 2026-11-24: "Yes, start BD-1320" (docs/251 s8 step 1: ground variation, ChatGPT critique #1 "one flat neon-green ground").
World V3 playtest island (`playtest` profile: WorldV3, ToonWorld, VegetationV2, GroundDetail, BiomeRotation on), my own test Studio window
(`build/BeDino-ground-test.rbxlx`), biome pinned with the Studio-only `BiomeTestOffset` attribute. Before = origin/main 8dfb7b69.

## What changed (terrain only, 0 parts, behind GroundDetailEnabled)
- `src/shared/GroundPatches.luau`, called by `IslandTerrain` before the BD-1245 grass blotches, only in the meadow, forest and pine zones:
  - **worn soil** (Ground) where each spoke meets the ring road and at the clearing each spoke ends in;
  - **grove floor**: bare earth in the core of each grove (WorldV3.Groves), a ring of the deeper green around it;
  - **slope rock** where the hillside is steep over a +-8 stud footprint (it continues the pine hill's rock band).
- `WorldToon.Palette.LeafyGrass` #69D94B -> **#50BE3E**: the old value was almost the same as Grass (#6EE342), so the forest floor and the BD-1245 blotches never showed. Now the forest reads darker than the meadow and the open grass has two-tone dapples.
- The biome rotation recolours the same materials (BiomeRotation.Terrain): the patches turn into terracotta soil in the desert and grey earth in the tundra with no extra work.
- Tried and dropped: beach "sand fingers" (the World V3 beach band already reaches the grass; the mask made 2 patches on the whole island) and a noisy rock threshold (it broke the slope band into one-voxel specks).

## Pictures (cameras from docs/evidence/2026-11-23-tree-variety; top = before, bottom = after)
- `compare-meadow.jpg`: worn soil in the clearing at the fossil statue; darker green dapples in the open grass.
- `compare-forest.jpg`: worn soil at the ring-road junction; darker forest floor.
- `compare-pine.jpg`: slope rock on the steep flank continues the existing rock band.
- `compare-aerial.jpg`: the two greens read from above (forest darker, meadow lighter, dapples).
- `compare-forest-desert.jpg`: the same patches in Desert Canyon (after picture from the second build: same greens and grove rule; the worn edge and the rock rule were calmed after it).
- `after-meadow-tundra.jpg`: Frozen Tundra: faint grey earth where the paths meet; snow stays mostly even.

## Checks
- `python tools/verify_ground_patches.py --runner <luau>`: patches cover 4.0 % (meadow), 16.7 % (forest), 20.3 % (pine, rock 13.0 %) of the grass; worn 12 patches (11 bigger than 2 cells), floor 13 (10), shade 20 (15), rock 7 (6).
- Terrain build time in Studio 0.8-1.1 s (the same as main).

## Not verified
- Phone (terrain only, no part change; no phone run).
- Owner look OK. The 4-stud voxel grid gives the patch edges a stepped outline (the same as the path edges today).
