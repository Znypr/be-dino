# BD-049 / BD-050 world props and food kit

**2026-10-13, branch `claude/bd-049-050-world-art`. Status: source + offline tests only. Studio, multiplayer and physical Android verification are PENDING.** All geometry is original, generated from primitives by script; no third-party models or textures. Tuning values are **PROVISIONAL**.

## What was made

- Generator: `tools/blender/build_world_kit.py` (Blender 5.1 headless, fixed seed, reruns reproduce identical OBJs).
- Editable masters: `assets/blender/world/BD049_WorldKit.blend`, `BD050_FoodKit.blend` (one object per logical ID, shared `BD049_*` palette materials, collider proxies as empties in a hidden `Colliders` collection).
- Exports: `resources/models/world/<id>.obj/.mtl` (Roblox space, Y up, studs, closed triangle meshes), `assets/blender/world/fbx/<id>.fbx` (single mesh with per-face vertex colours, for owner MeshPart upload).
- Manifest: `assets/blender/world/world-kit-manifest.json` (triangles, budget, bounds, pivot, colliders, materials, food points).
- Native fallback: `tools/bake_world_kit.py` bakes `resources/worldkit/*.rbxmx` (two WedgeParts per triangle, the same permission-free technique as `bake_models.py`) into `ReplicatedStorage.WorldKit`, and writes `src/shared/WorldKitData.luau`.
- Renders: `docs/evidence/2026-10-13-bd049-050-world-art/` (`bd049-trees.png`, `bd049-rocks.png`, `bd049-foliage.png`, `bd049-landmarks.png`, `bd049-biome-vignette.png`, `bd049-placement-plan.png`, `bd050-food-kit.png`, `bd050-food-gameplay-scale.png`).

Conventions: pivot = bounding-box bottom centre (what `ResourceModels.clone` normalises to); front faces Roblox -Z; 1 unit = 1 stud. Only foliage and food are noncolliding; trees, rocks and landmarks carry simplified box collider proxies.

## Assets (41, 2646 triangles total)

| ID | Kind | Triangles / budget | Size X x Y x Z (studs) | Colliders |
| --- | --- | ---: | --- | ---: |
| `world_tree_conifer_s` | tree | 52 / 80 | 5.9 x 10.2 x 6.0 | 1 |
| `world_tree_conifer_m` | tree | 58 / 120 | 11.3 x 16.9 x 10.1 | 1 |
| `world_tree_conifer_l` | tree | 76 / 160 | 15.8 x 26.2 x 15.8 | 1 |
| `world_tree_canopy_s` | tree | 66 / 80 | 6.4 x 8.2 x 5.4 | 1 |
| `world_tree_canopy_m` | tree | 92 / 120 | 13.2 x 13.1 x 8.5 | 1 |
| `world_tree_canopy_l` | tree | 112 / 160 | 17.9 x 19.4 x 16.7 | 1 |
| `world_tree_cycad_s` | tree | 72 / 80 | 5.7 x 5.2 x 4.9 | 1 |
| `world_tree_cycad_m` | tree | 112 / 120 | 9.2 x 8.8 x 9.2 | 1 |
| `world_tree_cycad_l` | tree | 136 / 160 | 14.1 x 12.7 x 14.3 | 1 |
| `world_tree_dead_s` | tree | 44 / 80 | 1.6 x 8.0 x 2.5 | 1 |
| `world_tree_dead_m` | tree | 50 / 120 | 5.2 x 12.3 x 4.0 | 1 |
| `world_tree_dead_l` | tree | 68 / 160 | 7.0 x 17.5 x 6.2 | 1 |
| `world_bush_a` | shrub | 60 / 60 | 3.7 x 1.9 x 2.5 | 0 |
| `world_fern_a` | shrub | 48 / 60 | 3.3 x 1.2 x 2.9 | 0 |
| `world_grass_a` | groundcover | 20 / 40 | 0.7 x 1.4 x 0.7 | 0 |
| `world_bush_b` | shrub | 56 / 60 | 3.1 x 2.0 x 2.5 | 0 |
| `world_fern_b` | shrub | 52 / 60 | 3.5 x 1.5 x 3.5 | 0 |
| `world_grass_b` | groundcover | 16 / 40 | 0.7 x 1.6 x 0.7 | 0 |
| `world_flowers_a` | groundcover | 36 / 40 | 0.6 x 1.2 x 0.6 | 0 |
| `world_horsetail_a` | shrub | 56 / 60 | 1.3 x 4.4 x 1.6 | 0 |
| `world_mushrooms_a` | shrub | 60 / 60 | 2.3 x 2.0 x 1.8 | 0 |
| `world_boulder_mossy_s` | rock | 20 / 24 | 2.3 x 2.1 x 2.7 | 1 |
| `world_boulder_mossy_m` | rock | 40 / 48 | 6.2 x 3.5 x 5.4 | 2 |
| `world_boulder_mossy_l` | rock | 60 / 72 | 12.0 x 5.9 x 9.2 | 3 |
| `world_boulder_bare_s` | rock | 20 / 24 | 2.9 x 2.0 x 2.9 | 1 |
| `world_boulder_bare_m` | rock | 40 / 48 | 6.4 x 3.7 x 5.5 | 2 |
| `world_boulder_bare_l` | rock | 60 / 72 | 11.5 x 5.7 x 9.2 | 3 |
| `world_rocks_spires` | rock | 104 / 120 | 8.7 x 14.2 x 7.1 | 4 |
| `world_rocks_ledge` | rock | 68 / 120 | 10.6 x 7.9 x 6.8 | 4 |
| `world_landmark_dino_statue` | landmark | 124 / 300 | 9.0 x 14.2 x 18.1 | 3 |
| `world_landmark_fossil_display` | landmark | 152 / 300 | 7.0 x 6.7 x 17.3 | 2 |
| `world_landmark_stone_arch` | landmark | 100 / 300 | 24.7 x 18.5 x 7.7 | 3 |
| `world_landmark_ruins_altar` | landmark | 152 / 300 | 15.0 x 9.0 x 15.1 | 6 |
| `food_berry_a` | food | 32 / 32 | 0.7 x 1.0 x 0.9 | 0 |
| `food_berry_b` | food | 28 / 32 | 0.7 x 0.8 x 0.6 | 0 |
| `food_fruit_a` | food | 32 / 40 | 0.8 x 1.2 x 0.8 | 0 |
| `food_fruit_b` | food | 40 / 40 | 1.0 x 1.2 x 0.9 | 0 |
| `food_egg_a` | food | 56 / 60 | 1.9 x 1.6 x 2.0 | 0 |
| `food_egg_b` | food | 60 / 60 | 1.5 x 1.5 x 1.4 | 0 |
| `food_amber_a` | food | 56 / 64 | 1.1 x 2.0 x 1.0 | 0 |
| `food_amber_b` | food | 60 / 64 | 1.1 x 1.4 x 0.9 | 0 |

Food keeps the authoritative values **+1 / +4 / +15 / +50** (berry / fruit / egg / amber) and the existing server validation. Value is read by silhouette: taller and more complex per tier; amber is a warm resin drop on a dark rock, not crystal currency.

## Budgets (PROVISIONAL, single authored LOD)

Per asset: tree s/m/l 80/120/160, shrub 60, ground cover 40, prehistoric plants 60, boulder s/m/l 24/48/72, formation 120, landmark 300, food 32/40/60/64. Placement total at density 1 is capped at **9,000 triangles** (currently 8,990 over 188 placements). The native fallback costs two parts per triangle (about 18k anchored noncolliding parts), comparable to the current legacy props; uploaded MeshParts reduce each prop to one part and are the recommended phone path.

## Integration status

- `Config.WorldArtMode = "Legacy"` (default, current look unchanged). `"BiomeKit"` makes `Arena.build` replace the legacy groves/scattered ferns with `BiomePlacement.generate` output: kit visuals from `ReplicatedStorage.WorldKit` plus invisible box colliders. Boundary, spawn, arch, spring, jump stones and Sanctuary are untouched; terrain shape and heights are not changed.
- `src/shared/BiomePlacement.luau`: deterministic grammar (seed, density, slope limit per layer, elevation/wetness family choice, grove clustering, path corridors, keep-outs for spawn meadow / arch / spring / Sanctuary approach, spacing hash, flattest-site search for 4 landmarks, running triangle budget). Keys: `WorldArtSeed`, `WorldArtDensity`.
- `Config.FoodArtMode = "Legacy"` (default). `"Kit"` sets a deterministic `ArtId` variant per pickup and uses the kit egg/amber models as server visuals. Berry/fruit kit models are **not** placed natively (1,300+ copies would be too heavy); they need the MeshPart upload. Points, pickup parts, respawn and validation are unchanged.
- `ResourceModels.clone` falls back to `ReplicatedStorage.WorldKit` after overrides and Resources, so an uploaded override with the same ID wins automatically.
- Tests: `tools/verify_world_art.py` (runs the real Luau grammar: determinism, seed sensitivity, no prop in paths/keep-outs/Sanctuary/boundary, ground contact, density bounds, budget, collider rules; added to CI), `tools/bake_world_kit.py --check`, `tests/test_world_kit.py`.

## Owner upload steps (optional, recommended for phones)

1. Import each `assets/blender/world/fbx/<id>.fbx` in Studio (3D Importer, vertex colours on) under the experience owner.
2. Publish as a Model; add the ID under the same logical ID through the existing `ResourceMeshAssets` binding flow (`tools/bind_visual_assets.py`). `ImportedResources` then loads it into `ResourceOverrides`, which `ResourceModels.clone` prefers. Then berry/fruit Kit visuals can be enabled.
3. No asset IDs were invented or uploaded by this work.

## Pending verification

Studio run with `WorldArtMode = "BiomeKit"` and `FoodArtMode = "Kit"`: collider fit, foot clipping on slopes, BIG-scale clearance through paths and the stone arch, food visibility among foliage, 8-12 player frame time, physical Android phone and landscape tablet. Risks: wedge part count on low-end phones, possible food hidden inside bushes (foliage has no query proxy), amber silhouette needs owner art approval, landmark sites are PROVISIONAL.

Performance budget and distance culling for these props: see [docs/89](91-world-performance-culling.md) (BD-168).
