# Island grass A/B/C (BD-528, 2026-10-17)

Owner pick pending: **contact sheet [contact-sheet-A-B-C.jpg](contact-sheet-A-B-C.jpg)** (A | B | C per row; rows = spawn, wide meadow, close ground, zoomed out). Nothing is bound for players: the shipped look stays **A**.

## Method (Studio, scratch place only)
- Place built from origin/main (`tools/build.py` -> `C:\Users\znypr\dtmp\grassab.rbxlx`), own Studio window, Play mode, Realistic lighting as shipped, clear weather, UI hidden, `CameraType` Custom.
- Same four camera positions for every variant (`screen_capture` camera_position / look_at):
  1. spawn, default gameplay camera: (0, 9.8, 42.1) -> (0, 7.2, 32.4), the local Compy at (0, 5.1, 30);
  2. wide meadow: (0, 28, 62) -> (0, 3, -30);
  3. close ground: (-6, 4.2, 26) -> (-14, 2.1, 14);
  4. zoomed out (about the 110-stud camera max): (0, 70, 112) -> (0, 5, 30).
- **A** = what ships: Roblox built-in Grass (no MaterialService override), terrain Grass colour 132,166,68.
- **B** = Blender `meadow_grass_v2` COLOUR MAP ONLY (id 85444193168969; no normal, no roughness) as a scratch `MaterialVariant` on Grass, `StudsPerTile` 12, applied with `MaterialService:SetBaseMaterialOverride`; terrain Grass colour **212,182,197**.
- **C** = B with a warmer, sunnier tint: terrain Grass colour **228,204,200**.
- Scratch variants lived only in the Studio session. No repo file changes bind them.

## Finding that matters: the terrain colour is a MULTIPLIER on the colour map
With a variant bound, `Terrain:SetMaterialColor(Grass, ...)` multiplies the texture. The shipped 132,166,68 would double-tint the (already green, mean 133,169,71) Blender map to a dark olive. Untinted (255,255,255) the map renders as a loud lime (`probe-B-untinted-white-tint.jpg`; mean about 133,175,53 vs A 111,125,41 in the spawn foreground). So B/C need a different `BiomeMap.Colors.Grass` at the same time as the variant is bound; B's tint was picked to match A's average colour (luminance matched), C is brighter and yellower. First frames after setting a variant are white until the asset loads (a few seconds); captures were taken after load.

## Ratings (honest)
| | Repeating pattern | Waves / stripes (old BeDino_Meadow bug) | Dino read | Overall |
|---|---|---|---|---|
| **A** built-in | none seen | none | good (dark contact shadow, mid-contrast) | **Best look**: natural large-scale light/dark mottling (block-mean luma spread 5.0 in the spawn foreground), reads as real meadow. A bit pale/olive in places. |
| **B** Blender, matched colour | none seen at gameplay or zoomed-out distance; at the grazing close view a faint herringbone leaf pattern shows at mid-distance (12 studs per tile) but no waves | none | good, about the same as A | Clean and crisp small blades up close, but **flat like a carpet** (block-mean luma spread 1.2): no macro variation, so the island loses its natural mottling. Olive tone is dull. The sharp-detail Grass also contrasts hard with the untextured-by-us LeafyGrass patches. |
| **C** Blender, warmer | same as B | none | **slightly better than A and B**: the brighter yellow-green ground separates the green dino most | Same flat-carpet issue as B, more cheerful and sunnier, but a touch loud/lime; at max zoom-out it reads as a uniform lime sheet. |

The Blender map fixes the original bug (no large baked blotches, no waves, no visible tiling at 12 studs) but it has no low-frequency variation at all, which is exactly what makes A feel organic.

## Recommendation
**Keep A (built-in Grass, 132,166,68).** B/C are not wrong, they are not better: flatter, with a LeafyGrass seam that gets more obvious. If the owner wants the crisper blades up close anyway, take **C**. A better B/C would need a second, larger-scale (30 to 60 studs) low-contrast variation layer, which a single Terrain MaterialVariant cannot give (tile is one repeat), so that would mean more terrain material patches in `BiomeMap`, not a better texture.

## How to switch (owner picks B or C; not done here)
The empty-id gate already exists: `tools/bind_visual_assets.py` writes a `MaterialVariant` only when `color` is non-empty and sets the base-material override only when `bound` is true. `BeDino_MeadowV2` already has its IDs (variant packaged, `bound: false`).
1. `resources/visual-upgrade-bindings.json` -> `BeDino_MeadowV2`: `"bound": true`, `"normal": ""`, `"roughness": ""` (colour map only, as tested), keep `"tile": 12`.
2. `src/shared/BiomeMap.luau` -> `Colors.Grass = {212, 182, 197}` (B) or `{228, 204, 200}` (C).
3. `python tools/bind_visual_assets.py`, update the asserts in `tools/verify_env_polish.py` (GrassName unset), run the verifiers, then re-measure luminance (`tools/qa/luminance.py`, band 0.35 to 0.75).
Step 2 is mandatory: binding without it darkens the whole meadow.

## Files
`A|B|C-{1-spawn,2-wide,3-close,4-zoomout}.jpg` (1140x785 Studio captures), `contact-sheet-A-B-C.jpg`, `probe-B-untinted-white-tint.jpg` (B variant at tint 255,255,255, shows the multiplier effect).
