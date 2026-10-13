# BD-061 fusion visual prototype

Current candidate: **Fusion finish v2**, a continuous glossy coating with no
ornaments or attached crystals. Open `BD061_FusionFinish_Daylight_v2.blend` for
the daylight game-style clearing and fourteen editable treatment objects, or
append from `BD061_FusionFinish_Library_v2.blend` for the isolated shader library.
Both Subtle and Medium add zero geometry and zero fusion particles.

Rebuild v2 with Blender's `--background --python tools/blender/build_fusion_finish.py`.
The earlier v1 sources below are retained as the rejected historical study.

Editable Blender 5.1 sources for the Gold, Emerald and Diamond additive
surface study. This is an art prototype only; it does not alter the live place,
gameplay, fusion RNG, persistence, schemas or economy.

## Files

- `BD061_FusionVisualPrototype.blend`: Compy and Triceratops Base/Subtle/Medium
  comparison scene using the repository OBJ meshes.
- `BD061_FusionStackTests.blend`: isolated BIG, Shiny, Frost mutation, aura and
  trail layer tests.
- `BD061_FusionMaterialLibrary.blend`: appendable material/node-group source.
- `bd061-fusion-material-manifest.json`: measured source geometry and layer
  inventory.

All stage materials use the shared `BD061_FusionOverlay_v1` shader group. The
group keeps Primary/Secondary genetic colors as the base and introduces stage
color only through a selective mask. Subtle uses intensity `0.34`; Medium uses
`0.62` plus a single optional 60-triangle accent mesh.

Rebuild the sources and review renders from the repository root:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --python tools/blender/build_fusion_visuals.py
```

Roblox Studio import, owner-bound asset upload and physical-device profiling
remain intentionally unperformed.
