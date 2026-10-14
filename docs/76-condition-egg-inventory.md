# 76 Condition egg inventory and wiring (BD-103)

No art was drawn or redrawn. Accepted looks: docs/39 "Conditions preserve the underlying shell" and the Rainbow/Astra paragraphs; evidence in `docs/evidence/2026-10-08-egg-condition-combinations/` and `2026-10-08-crystal-shops-genetics/`.

## Inventory (main at b980e71; the BD-104..109 concept drafts were reverted)
| Condition | Authored art today | In repo as texture/code | Roblox asset ID | Runtime renderer before | Now |
|---|---|---|---|---|---|
| Normal | clean shell (no layer) | n/a | n/a | plain | wired: clean layer, SmoothPlastic |
| Cracked | dark non-glowing fracture layer (Blender 512 RGBA, 9.31% coverage) | evidence renders only; layer PNG is local in Premium_Egg | none | ignored (only hatch cutscene crack) | wired with fallback; needs upload |
| Dirty | matte earthy smudge layer (38.45%) | evidence renders only; local | none | ignored | wired with fallback; needs upload |
| Rainbow | prismatic flank + multicolor stars, no outlines (21.90%) | evidence renders only; local | none | ignored | wired with fallback; needs upload |
| Astra | five bright curved opal streaks, three hero stars, medium outlines, violet halos (29.06%) | evidence renders only; local | none | ignored | wired with fallback; needs upload |

Searched: resources/, EggAppearance, EggPreview, GeneTextures, GeneTextureAssets, EggGenetics, PatternGenes, HatchPresentation, resources/genetics (only creature neutral textures, no egg condition layers), git history 2026-10-08..10 (only docs/evidence PNG/JPG and the reverted drafts). `layer-validation.json` confirms four 512 RGBA layers with transparent corners exist locally; they were never uploaded or committed.

## Wiring
`src/shared/ConditionOverlays.luau` holds one entry per condition (`layer`, `assetId`, fallback material/reflectance). `EggAppearance.apply` now reads `genes.conditionId` and applies the overlay on the largest part (shell) after tint/pattern, so hatch reveal, Caught Eggs slots, Nests and Condition Shop swatches (all use `EggAppearance`) differ. With `assetId=""` a non-art fallback is used (Plastic matte for Cracked/Dirty, small reflectance for Rainbow/Astra). When the owner binds an ID, a transparent `Decal` named `ConditionOverlay` is added over the shell. IDs are never invented. `tools/verify_ui_format.py` now asserts all five condition signatures differ.

## Owner uploads needed (Roblox Decal/Image, 512x512 RGBA PNG, transparent background)
Source: Blender pack `Premium_Egg/Full_Combination_Review/BeDino_Full_Combination_Review.blend` (local, not in repo); export the four effect layers.
- `BeDino_Cond_Cracked.png`, 512x512, "Condition Cracked overlay"
- `BeDino_Cond_Dirty.png`, 512x512, "Condition Dirty overlay"
- `BeDino_Cond_Rainbow.png`, 512x512, "Condition Rainbow overlay"
- `BeDino_Cond_Astra.png`, 512x512, "Condition Astra overlay"
Then set `assetId` per condition in `ConditionOverlays.luau`. Normal needs no upload. Also check the layers' UV orientation against the egg mesh (Decal face) in Studio.
