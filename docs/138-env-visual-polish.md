# 138 Island environment visual polish (BD-460, 2026-10-16)

Owner feedback on a screenshot of the island in Realistic (Future) lighting at max quality: the grass shows strong repeating dark waves that out-shout the dinosaur, the greens are over-saturated, some treetops clip and some ground is near black, and the dino blends into the green. Built on top of PR #302 (clear daylight, no haze); nothing here adds haze. Labels: **CODE** = what this PR changes, **STUDIO** = result seen by the lead.

## 1. Root cause of the grass striping (confirmed in Studio)
`MaterialService.GrassName = BeDino_Meadow` replaced the terrain Grass look with an AI-generated PBR set (colour 94202355146046, normal 102603392874381, roughness 82962110810713, metalness 94175885618888, 20 studs per tile). Its **colour map itself** carries large dark baked shadow blotches (prompt: "muted cool shadows") that repeat every tile; that is the dark wave.

- **Round 1 (wrong lever, STUDIO: not fixed):** unbinding the normal, roughness and metalness maps and shrinking the tile to 12 left the waves unchanged (`docs/evidence/2026-10-16-env/2-after-pr303.jpg`).
- **Control (STUDIO):** `MaterialService:SetBaseMaterialOverride(Grass, "")` (Roblox's built-in Grass): the waves vanish completely and the dino reads much better (`3-builtin-grass-control.jpg`). So the cause is the BeDino_Meadow colour map. `Terrain.Decoration` cannot be read or written from a script (even in Edit), so it is not a lever and is no longer a suspect.
- **Owner decision 2026-10-16: use the built-in Grass now, make a new one later.** CODE: `GrassName` is no longer set. The `BeDino_Meadow` variant stays packaged in `MaterialService` (all four map IDs and the original 20-stud tile) but is **unbound** (`"bound": false` in `resources/visual-upgrade-bindings.json`, `tools/bind_visual_assets.py`). To use it again: set `bound` to true, or `SetBaseMaterialOverride(Grass, "BeDino_Meadow")`. The replacement texture is BD-461 (section 5, and `TODO_meadow_grass_texture_v2` in [77](77-asset-registry.md)).

## 2. Built-in grass is pale and grey-green: colour candidates for the Studio A/B
The terrain colour (`BiomeMap.Colors`, `SetMaterialColor`) multiplies the base albedo. The built-in Grass albedo is pale and grey-green, so the multiplier has to be rich and warm: **a low blue channel is what removes the grey** (round 1 used 138,164,98, R and B only 40 apart: grey). Old (before BD-460): Grass 132,170,84.

| Candidate | RGB | S / V | Why |
|---|---|---|---|
| A | 118,164,72 | .56 / .64 | Lush warm yellow-green: blue pulled to 72, green clearly leads, brightness a little below the old 170 because the built-in albedo is lighter than the dark Meadow map. |
| B | 102,150,60 | .60 / .59 | Deeper and richer; best if A still looks bright or minty next to the trees, and best for dino contrast. |
| **C (owner pick 2026-10-16, in code)** | 132,166,68 | .59 / .65 | Sunnier, closest to the old look (132,170,84) but with the grey taken out. |

Studio A/B (lead, 2026-10-16, Future lighting, quality 21, clear weather, same camera): built-in Grass removes the dark waves in all three candidates. Evidence: docs/evidence/2026-10-16-env/ (1-before, 2-after-pr303 round 1, 3-builtin-grass-control, 4/5/6 = A/B/C).

LeafyGrass (used in patches near the spawn meadow; it showed as dark teal): default 88,132,62 (S .53, V .52), alternatives 76,124,60 (deeper) and 100,138,66 (lighter). Quick A/B in Studio: `workspace.Terrain:SetMaterialColor(Enum.Material.Grass, Color3.fromRGB(...))`. Once chosen, change only `BiomeMap.Colors` (and the asserts in `tools/verify_env_polish.py`).

Because the ground now needs to read lush, part of the round 1 desaturation was undone: **clear grade saturation +0.08 -> +0.04** (round 1 had +0.02). Collectibles are not recoloured and get a touch more saturation, so they stay vivid.

## 3. All changes (old -> new)
| Area | Property | Old | New |
|---|---|---|---|
| Grass material | MaterialService GrassName | BeDino_Meadow | unset (built-in Grass); variant kept, unbound |
| Terrain colour | `BiomeMap.Colors.Grass` | 132,170,84 | 132,166,68 (candidate C, owner pick) |
| Terrain colour | `BiomeMap.Colors.LeafyGrass` | 62,124,78 | 88,132,62 |
| Foliage | `WorldGeneratedMeshes.Tone` (SurfaceAppearance.Color, once per mesh template) | none (white) | broadleaf, birch, jungle giant 0.94/0.92/0.80; palm 0.95/0.93/0.84; pine 0.95/0.94/0.86; bush 0.94/0.92/0.82 |
| Foliage (kit meshes) | `BiomePlacement.BiomeWarmth` meadow / fern | 1,1,.95 / .95,1,.95 | 1,.97,.93 / .96,.98,.93 |
| Foliage (native fallback) | Arena tree Canopy / fern leaf colour | 64,144,112 / 106,180,125 | 76,138,100 / 112,164,116 |
| Grade | clear `WeatherGrade` saturation / contrast | +0.08 / +0.04 | +0.04 / 0 |
| Light | `Config.IslandLight.Brightness` (clear) | 2 | 1.8 |
| Light | Lighting.Ambient | 130,143,148 | 146,155,158 |
| Light | Lighting.OutdoorAmbient | place default | 140,150,153 |
| Placement | spawn meadow keep-out radius (non-blocking props only) | 56 | 64 |
| Placement | main path half-widths | 16 and 14 | 18 and 16 |
| Dino | contact shadow | none | 3 stacked flat discs under each dino (client only) |

Contact shadow round 2: round 1 was invisible at about 25 studs in Studio (footprint 2.2 studs, narrower than the 3.5-stud body, centre darkness .33). Now: footprint 5.4 studs across by 7.6 along at start size (grows with the dino, capped 18), disc alpha .20/.24/.30 (centre darkness .57, the rim still fades in three steps), colour 12,20,16. Still 3 parts for the local dino, at most 2 / 4 / 6 others (Phone / Tablet / Desktop), Lite halves, Off drops others, no textures.

Unchanged on purpose: Atmosphere density .1 / haze .3 / glare 0, fog distances, bloom 0, DoF 0, sun rays 0, weather looks, the cave, collectibles.

## 4. Rules kept
- **No haze** (owner 2026-10-16, [115](115-decisions-log.md)): a "subtle distance haze" suggestion from the feedback was **skipped**. `tools/verify_env_polish.py` asserts the atmosphere numbers and that the clear look adds no density, haze, bloom, DoF or rays.
- **Phone cost not worse:** world changes are data only; the shadow is 3 parts for the local dino plus at most 2 others on a phone. The Effects setting is respected through `ContactShadowRules.maxOthers`.
- **Luminance band** island 0.35 to 0.75 ([114](114-handbook.md) s6.1): re-measure with `tools/qa/luminance.py` after choosing the grass colour (built-in grass is lighter than the old map).
- Vibe words ([114](114-handbook.md) s0): lush, calm, colourful.

## 5. BD-461: new meadow grass texture (follow-up)
Made in Blender (no code-drawn art): seamless matte colour map, mid-green, soft low-contrast blade-scale variation, **no large baked shadow blotches, no hair streaks**, 1024 px, about 12 studs per tile, optional very soft normal. It replaces the colour map of the unbound `BeDino_Meadow` variant and is bound **only if it beats the built-in grass side by side at gameplay distance in Studio** (same camera, Future lighting, quality 21, with the dino and collectibles in frame); otherwise built-in Grass stays.

## 6. Evidence
Offline: `python tools/verify_env_polish.py --runner <luau>`, `verify_world_art`, `verify_weather`, `tests/test_build.py`. Studio: `docs/evidence/2026-10-16-env/` (before, after round 1, built-in control); round 2 A/B pending (lead).
